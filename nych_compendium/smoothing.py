"""Interpolated Modified Kneser-Ney with Chen-Goodman count-of-counts discounts.

Owner-approved D2 smoothing, manifest id ``chen-goodman-mkn-interpolated-v1``.
Counts and discounts come from train pages only. If a level lacks the counts
the discounts need, or a discount falls outside ``0 <= D_j <= j``, the build
stops with ``SmoothingUnavailable``. No other method is substituted.

Levels are context lengths. The owner stated that orders 1-3 mean context
lengths 1-3 (stated, not approved). Level 0 is the unigram base that the
recursion needs.

Pruning, owner-chosen (stated, not approved): rows seen exactly once at
context lengths 2 and 3 are not stored. Discounts, continuation counts,
context totals and interpolation weights are all computed from the full,
unpruned counts first. A pruned row's discounted mass is added to its
context's interpolation weight, so every context still sums to 1, and a
context whose rows were all pruned has weight 1 and is not stored.

Interpreted plumbing: a page start counts as one left-extension type, so every
lower-level n-gram has a continuation count of at least 1; the recursion ends
in a uniform distribution over the train vocabulary (Chen and Goodman's
0th-order model) with no unknown-word token, so an out-of-vocabulary word has
no probability; natural log; per-context interpolation weights stored in
``context_backoff``; per-level discounts stored in ``mkn_discounts``; pruning
on the raw count, which keeps every stored row's shorter-context suffix.
"""
from __future__ import annotations

import json
import math
import sqlite3

SMOOTHING_ID = "chen-goodman-mkn-interpolated-v1"
SMOOTHING_VERSION = "v1"
LEVELS = (0, 1, 2, 3)
PRUNE_SINGLETON_LEVELS = (2, 3)

CREATE_ADJUSTED = """
CREATE TABLE mkn_adjusted (
    order_n INTEGER NOT NULL,
    context_key TEXT NOT NULL,
    candidate_token TEXT NOT NULL,
    adjusted INTEGER NOT NULL,
    PRIMARY KEY (order_n, context_key, candidate_token)
) WITHOUT ROWID
"""

CREATE_DISCOUNTS = """
CREATE TABLE mkn_discounts (
    order_n INTEGER PRIMARY KEY,
    n1 INTEGER NOT NULL,
    n2 INTEGER NOT NULL,
    n3 INTEGER NOT NULL,
    n4 INTEGER NOT NULL,
    d1 REAL NOT NULL,
    d2 REAL NOT NULL,
    d3_plus REAL NOT NULL
)
"""

CREATE_BACKOFF = """
CREATE TABLE context_backoff (
    order_n INTEGER NOT NULL,
    context_key TEXT NOT NULL,
    adjusted_total INTEGER NOT NULL,
    backoff_weight REAL NOT NULL,
    PRIMARY KEY (order_n, context_key)
) WITHOUT ROWID
"""


class SmoothingUnavailable(RuntimeError):
    """Raised when MKN cannot be computed from the train counts."""


def context_key(words: list[str]) -> str:
    return json.dumps(words, ensure_ascii=False, separators=(",", ":"))


def suffix_key(key: str) -> str:
    """Drop the first word of a context key."""
    if "\\" not in key:
        # Word tokens hold no quote, so the first '","' ends the first word.
        cut = key.find('","')
        return "[]" if cut < 0 else "[" + key[cut + 2 :]
    return context_key(json.loads(key)[1:])


def discounts(level: int, n1: int, n2: int, n3: int, n4: int) -> tuple[float, float, float]:
    """Chen-Goodman estimates of D1, D2 and D3+ from counts-of-counts."""
    if min(n1, n2, n3, n4) <= 0:
        raise SmoothingUnavailable(
            f"level {level}: counts-of-counts n1..n4 = {n1}, {n2}, {n3}, {n4}; "
            "Chen-Goodman discounts need all four"
        )
    y = n1 / (n1 + 2 * n2)
    values = (1 - 2 * y * n2 / n1, 2 - 3 * y * n3 / n2, 3 - 4 * y * n4 / n3)
    for j, value in enumerate(values, start=1):
        if not 0 <= value <= j:
            raise SmoothingUnavailable(f"level {level}: discount D{j} = {value!r} is outside [0, {j}]")
    return values


def discount_table(rows) -> dict[int, dict]:
    """Pass over (level, adjusted) pairs: counts-of-counts and discounts per level."""
    counts = {level: [0, 0, 0, 0] for level in LEVELS}
    for level, adjusted in rows:
        if adjusted <= 4:
            counts[level][adjusted - 1] += 1
    table = {}
    for level in LEVELS:
        n1, n2, n3, n4 = counts[level]
        d1, d2, d3 = discounts(level, n1, n2, n3, n4)
        table[level] = {"n": (n1, n2, n3, n4), "d": (d1, d2, d3)}
    return table


def _discount(d: tuple[float, float, float], adjusted: int) -> float:
    return d[min(adjusted, 3) - 1]


def is_pruned(level: int, raw: int) -> bool:
    return level in PRUNE_SINGLETON_LEVELS and raw == 1


def context_statistics(rows, table: dict[int, dict]):
    """Group sorted (context, level, raw, adjusted) rows by context.

    Yields (context, raw_total, adjusted_total, weight, kept_rows) with every
    total taken over the full, unpruned rows.
    """
    current = None
    for context, level, raw, adjusted in rows:
        if context != current:
            if current is not None:
                yield current, raw_total, total, (mass + pruned) / total, kept
            current = context
            d = table[level]["d"]
            raw_total = total = kept = 0
            mass = pruned = 0.0
        raw_total += raw
        total += adjusted
        mass += _discount(d, adjusted)
        if is_pruned(level, raw):
            pruned += max(adjusted - _discount(d, adjusted), 0)
        else:
            kept += 1
    if current is not None:
        yield current, raw_total, total, (mass + pruned) / total, kept


def write_discounts(connection: sqlite3.Connection, table: dict[int, dict]) -> None:
    connection.execute(CREATE_DISCOUNTS)
    for level in LEVELS:
        n1, n2, n3, n4 = table[level]["n"]
        d1, d2, d3 = table[level]["d"]
        connection.execute(
            "INSERT INTO mkn_discounts (order_n, n1, n2, n3, n4, d1, d2, d3_plus) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (level, n1, n2, n3, n4, d1, d2, d3),
        )


def _fill_probabilities(
    connection: sqlite3.Connection, level: int, d1: float, d2: float, d3: float, vocabulary: int
) -> None:
    if level == 0:
        lower = "(1.0 / :vocabulary)"
    else:
        lower = """(
            SELECT low.probability FROM ngram_counts AS low
            WHERE low.order_n = :lower_level
              AND low.context_key = mkn_suffix(ngram_counts.context_key)
              AND low.candidate_token = ngram_counts.candidate_token
        )"""
    connection.execute(
        f"""
        UPDATE ngram_counts SET probability = (
            SELECT MAX(a.adjusted - CASE a.adjusted WHEN 1 THEN :d1 WHEN 2 THEN :d2 ELSE :d3 END, 0)
                   * 1.0 / b.adjusted_total
                   + b.backoff_weight * {lower}
            FROM mkn_adjusted AS a
            JOIN context_backoff AS b ON b.order_n = a.order_n AND b.context_key = a.context_key
            WHERE a.order_n = ngram_counts.order_n
              AND a.context_key = ngram_counts.context_key
              AND a.candidate_token = ngram_counts.candidate_token
        )
        WHERE order_n = :level
        """,
        {"d1": d1, "d2": d2, "d3": d3, "level": level, "lower_level": level - 1, "vocabulary": vocabulary},
    )
    bad = connection.execute(
        "SELECT COUNT(*) FROM ngram_counts WHERE order_n = ? AND (probability IS NULL OR probability <= 0)",
        (level,),
    ).fetchone()[0]
    if bad:
        raise SmoothingUnavailable(f"level {level}: {bad} rows have no positive probability")
    connection.execute(
        "UPDATE ngram_counts SET log_probability = mkn_ln(probability) WHERE order_n = ?",
        (level,),
    )


def fill_probabilities(connection: sqlite3.Connection, table: dict[int, dict]) -> dict:
    """Fill probability and log_probability for the stored rows, level by level."""
    connection.create_function("mkn_suffix", 1, suffix_key, deterministic=True)
    connection.create_function("mkn_ln", 1, math.log, deterministic=True)
    vocabulary = connection.execute("SELECT COUNT(*) FROM ngram_counts WHERE order_n = 0").fetchone()[0]
    report = {}
    for level in LEVELS:
        d1, d2, d3 = table[level]["d"]
        _fill_probabilities(connection, level, d1, d2, d3, vocabulary)
        report[str(level)] = {"d1": d1, "d2": d2, "d3_plus": d3}
    connection.execute("DROP TABLE mkn_adjusted")
    return {
        "discounts": report,
        "levels": list(LEVELS),
        "pruned_singleton_levels": list(PRUNE_SINGLETON_LEVELS),
        "vocabulary_size": vocabulary,
    }


def probability(connection: sqlite3.Connection, context: list[str], word: str) -> float | None:
    """P(word | last three context words). None if word is not in the train vocabulary."""
    known = connection.execute(
        "SELECT 1 FROM ngram_counts WHERE order_n = 0 AND context_key = ? AND candidate_token = ?",
        (context_key([]), word),
    ).fetchone()
    if known is None:
        return None
    return _interpolated(connection, list(context[len(context) - min(len(context), LEVELS[-1]) :]), word)


def _interpolated(connection: sqlite3.Connection, context: list[str], word: str) -> float:
    key = context_key(context)
    row = connection.execute(
        "SELECT probability FROM ngram_counts WHERE order_n = ? AND context_key = ? AND candidate_token = ?",
        (len(context), key, word),
    ).fetchone()
    if row is not None:
        return float(row[0])
    lower = _interpolated(connection, context[1:], word)
    weight = connection.execute(
        "SELECT backoff_weight FROM context_backoff WHERE order_n = ? AND context_key = ?",
        (len(context), key),
    ).fetchone()
    return lower if weight is None else float(weight[0]) * lower
