"""Separate typo hypotheses. The surface token and its byte span stay as written.

Interpreted plumbing: word tokens are the context, a longer observed context
wins, and a right-context count breaks an equal left-context count. A tie that
remains is unresolved. Only a single neighboring-key substitution is keyboard
evidence. Other key errors are not guessed. No probability is read or written.
"""
from __future__ import annotations

import sqlite3

from nych_compendium.build import context_key
from nych_compendium.gate import automatic_correction_allowed
from nych_compendium.keyboards import layouts_agree


def _candidates(connection: sqlite3.Connection, order: int, key: str) -> list[tuple[str, int]]:
    return connection.execute(
        """
        SELECT candidate_token, count
        FROM ngram_counts
        WHERE order_n = ? AND context_key = ? AND probability IS NULL
        ORDER BY count DESC, candidate_token ASC
        """,
        (order, key),
    ).fetchall()


def _right_count(connection: sqlite3.Connection, candidate: str, following: str | None) -> int:
    if following is None:
        return 0
    row = connection.execute(
        """
        SELECT count FROM ngram_counts
        WHERE order_n = 1 AND context_key = ? AND candidate_token = ? AND probability IS NULL
        """,
        (context_key([candidate]), following),
    ).fetchone()
    return 0 if row is None else int(row[0])


def hypotheses_for_words(
    words: list[str],
    connection: sqlite3.Connection | None,
    *,
    layout: str | None,
    gate_correct: int | None,
    gate_evaluated: int | None,
) -> dict:
    allowed = False
    gate: dict
    if gate_correct is None or gate_evaluated is None:
        gate = {"automatic": False, "status": "missing-held-out"}
    else:
        allowed = automatic_correction_allowed(gate_correct, gate_evaluated)
        gate = {
            "automatic": allowed,
            "correct": gate_correct,
            "evaluated": gate_evaluated,
            "status": "measured",
        }
    found = []
    if connection is not None:
        for index, surface in enumerate(words):
            ranked: list[tuple[str, int]] | None = None
            used_order = None
            for order in (3, 2, 1):
                if index < order:
                    continue
                rows = _candidates(connection, order, context_key(words[index - order : index]))
                if rows:
                    ranked = rows
                    used_order = order
                    break
            following = words[index + 1] if index + 1 < len(words) else None
            compatible = []
            if ranked:
                for candidate, count in ranked:
                    if candidate == surface:
                        continue
                    if layouts_agree(surface, candidate, layout):
                        compatible.append((candidate, count, _right_count(connection, candidate, following)))
            resolved = None
            if compatible:
                best = max(item[1] for item in compatible)
                top = [item for item in compatible if item[1] == best]
                best_right = max(item[2] for item in top)
                tied = [item for item in top if item[2] == best_right]
                if len(tied) == 1:
                    resolved = tied[0][0]
            found.append(
                {
                    "automatic": bool(allowed and resolved is not None),
                    "candidate": resolved,
                    "confidence": None,
                    "evidence": {
                        "keyboard_layout": layout if layout is not None else "unknown-require-agreement",
                        "order_n": used_order,
                        "probabilities": "refused",
                    },
                    "index": index,
                    "surface": surface,
                }
            )
    return {
        "automatic_hypotheses": sum(1 for row in found if row["automatic"]),
        "automatic_replacements": 0,
        "gate": gate,
        "hypotheses": found,
        "probabilities": "refused",
    }
