"""Stream Wikipedia pages into private n-gram counts, batched on disk.

No dump or article text is retained. Page text is hashed and discarded, and
markup is stripped before counting (see ``wikitext.py``). Train pages are
counted in batches: each batch becomes one sorted, gzip-compressed run file,
runs are merged in tiers so disk use stays bounded, and the final sorted run
is loaded into SQLite once. MKN statistics are computed by streaming passes
over the sorted runs, so rows pruned by the owner-chosen singleton rule never
reach SQLite. Probabilities use the owner-approved D2
smoothing, ``chen-goodman-mkn-interpolated-v1`` (see ``smoothing.py``). If it
cannot be computed, the build stops and writes no manifest.

Interpreted plumbing: schema version, compendium id, tokenizer and normalizer
version strings, context-key JSON, the separate SQLite file, the provenance
table, the curid URL, storing per-page rows in SQLite instead of inline in
the manifest, the level-0 unigram rows and page-start table that MKN needs,
WITHOUT ROWID tables, the run-file format, batch size, merge fan-in, worker
count, and excluding a page whose markup cannot be parsed.
"""
from __future__ import annotations

import bz2
import gzip
import hashlib
import heapq
import json
import multiprocessing
import shutil
import sqlite3
import xml.etree.ElementTree as ET
from collections import deque
from pathlib import Path

from nych_compendium.keyboards import LAYOUT_VERSION, LAYOUTS
from nych_compendium.smoothing import (
    CREATE_ADJUSTED,
    CREATE_BACKOFF,
    LEVELS,
    PRUNE_SINGLETON_LEVELS,
    SMOOTHING_ID,
    SMOOTHING_VERSION,
    SmoothingUnavailable,
    context_key,
    context_statistics,
    discount_table,
    fill_probabilities,
    is_pruned,
    suffix_key,
    write_discounts,
)
from nych_compendium.split import SNAPSHOT_ID, bucket, split_name
from nych_compendium.wikitext import EXTRACTION_VERSION, plain_text
from nych_smoke.tokenize import tokenize

SCHEMA_VERSION = "mg8.statistical-compendium.v1"
COMPENDIUM_ID = "nych-d2-enwiki-20261001"
TOKENIZER_VERSION = "b2-whitespace-spans-v1"
NORMALIZER_VERSION = "identity-v1"
LICENSE_REFERENCE = "CC BY-SA 4.0 and GFDL; page-level exceptions were not identified in this stream"
ORDERS = (1, 2, 3)
BATCH_PAGES = 500
MERGE_FAN_IN = 32
INSERT_CHUNK = 50_000
CONTINUATION_CHUNK = 2_000_000
PROVENANCE_COMMIT_PAGES = 5_000

CREATE_COUNTS = """
CREATE TABLE ngram_counts (
    order_n INTEGER NOT NULL,
    context_key TEXT NOT NULL,
    candidate_token TEXT NOT NULL,
    count INTEGER NOT NULL,
    context_total INTEGER NOT NULL,
    probability REAL,
    log_probability REAL,
    PRIMARY KEY (order_n, context_key, candidate_token)
) WITHOUT ROWID
"""

CREATE_PAGES = """
CREATE TABLE page_provenance (
    snapshot_id TEXT NOT NULL,
    page_id TEXT NOT NULL,
    revision_id TEXT,
    title TEXT,
    page_url TEXT,
    namespace_id TEXT,
    page_text_sha256 TEXT NOT NULL,
    license_basis TEXT NOT NULL,
    excluded_reason TEXT,
    extraction_version TEXT NOT NULL,
    included_in_compendium INTEGER NOT NULL,
    compendium_build_id TEXT NOT NULL,
    bucket INTEGER,
    split_name TEXT,
    PRIMARY KEY (snapshot_id, page_id)
)
"""

INSERT_PAGE = """
INSERT INTO page_provenance (
    snapshot_id, page_id, revision_id, title, page_url, namespace_id,
    page_text_sha256, license_basis, excluded_reason, extraction_version,
    included_in_compendium, compendium_build_id, bucket, split_name
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


class DumpChecksumError(RuntimeError):
    """Raised when the official SHA-1 does not match the file."""


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _sha256(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def hash_file(path: Path) -> tuple[str, str]:
    """Stream SHA-1 and SHA-256. The dump is not loaded whole."""
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            sha1.update(chunk)
            sha256.update(chunk)
    return sha1.hexdigest(), sha256.hexdigest()


def _is_sha1(value: str) -> bool:
    return len(value) == 40 and all(char in "0123456789abcdef" for char in value)


def official_sha1(path: Path, dump_name: str | None = None) -> str:
    """SHA-1 for ``dump_name`` from a sha1sums list, or the only SHA-1 in the file."""
    found = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) >= 2 and _is_sha1(parts[0].lower()):
            if dump_name is not None and parts[-1].lstrip("*") == dump_name:
                return parts[0].lower()
            found.append(parts[0].lower())
        elif len(parts) == 1 and _is_sha1(parts[0].lower()):
            found.append(parts[0].lower())
    if len(found) == 1:
        return found[0]
    if found:
        raise DumpChecksumError(f"checksum file lists {len(found)} files and none is {dump_name}")
    raise DumpChecksumError("official checksum file has no SHA-1")


def _digest_rows(hasher, rows) -> None:
    """Hash rows as the bytes of one compact JSON list, without holding them all."""
    hasher.update(b"[")
    first = True
    for row in rows:
        if not first:
            hasher.update(b",")
        hasher.update(json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        first = False
    hasher.update(b"]")


def counts_digest(connection: sqlite3.Connection) -> str:
    hasher = hashlib.sha256()
    _digest_rows(
        hasher,
        connection.execute(
            """
            SELECT order_n, context_key, candidate_token, count, context_total
            FROM ngram_counts
            ORDER BY order_n, context_key, candidate_token
            """
        ),
    )
    return "sha256:" + hasher.hexdigest()


def model_digest(connection: sqlite3.Connection) -> str:
    """Digest of counts, probabilities, interpolation weights and discounts."""
    hasher = hashlib.sha256()
    for query in (
        """
        SELECT order_n, context_key, candidate_token, count, context_total,
               probability, log_probability
        FROM ngram_counts
        ORDER BY order_n, context_key, candidate_token
        """,
        """
        SELECT order_n, context_key, adjusted_total, backoff_weight
        FROM context_backoff
        ORDER BY order_n, context_key
        """,
        "SELECT * FROM mkn_discounts ORDER BY order_n",
    ):
        _digest_rows(hasher, connection.execute(query))
        hasher.update(b"\x00")
    return "sha256:" + hasher.hexdigest()


def provenance_digest(connection: sqlite3.Connection) -> str:
    hasher = hashlib.sha256()
    _digest_rows(
        hasher,
        connection.execute(
            """
            SELECT snapshot_id, page_id, revision_id, title, page_url, namespace_id,
                   page_text_sha256, license_basis, excluded_reason, extraction_version,
                   included_in_compendium, compendium_build_id, bucket, split_name
            FROM page_provenance
            ORDER BY snapshot_id, page_id
            """
        ),
    )
    return "sha256:" + hasher.hexdigest()


def _build_code_version() -> str:
    hasher = hashlib.sha256()
    root = Path(__file__).resolve().parent
    for path in sorted(root.glob("*.py")):
        hasher.update(path.name.encode("utf-8"))
        hasher.update(b"\x00")
        hasher.update(path.read_bytes())
    return "sha256:" + hasher.hexdigest()


def _words(text: str) -> list[str]:
    _raw, tokens = tokenize(text)
    return [token.text for token in tokens if token.kind == "word"]


# A run line is "order\tcontext_key\tcandidate\tcount\tpage_start". Word tokens
# hold no tab or newline, so sorting the first three fields as one string
# matches the (order_n, context_key, candidate_token) primary-key order.

def _write_run(path: Path, rows) -> None:
    with gzip.open(path, "wt", encoding="utf-8", newline="\n", compresslevel=1) as handle:
        for key, count, start in rows:
            handle.write(f"{key}\t{count}\t{start}\n")


def _read_run(path: Path):
    with gzip.open(path, "rt", encoding="utf-8", newline="\n") as handle:
        for line in handle:
            key, count, start = line.rstrip("\n").rsplit("\t", 2)
            yield key, int(count), int(start)


def _merged(paths: list[Path]):
    """Merge sorted runs, summing counts and keeping any page-start flag."""
    current = None
    for key, count, start in heapq.merge(*(_read_run(path) for path in paths)):
        if current is not None and current[0] == key:
            current[1] += count
            current[2] |= start
            continue
        if current is not None:
            yield tuple(current)
        current = [key, count, start]
    if current is not None:
        yield tuple(current)


def count_batch(task: tuple[str, int, list[tuple[str, str]]]) -> tuple[str, list[str]]:
    """Strip, tokenize and count one batch of train pages into a sorted run."""
    run_dir, index, pages = task
    counts: dict[str, int] = {}
    starts: set[str] = set()
    failed = []
    top = LEVELS[-1]
    for page_id, wikitext in pages:
        try:
            words = _words(plain_text(wikitext))
        except Exception:  # recorded as an excluded page, not skipped silently
            failed.append(page_id)
            continue
        for position, candidate in enumerate(words):
            for order in LEVELS:
                if position < order:
                    continue
                key = f"{order}\t{context_key(words[position - order : position])}\t{candidate}"
                counts[key] = counts.get(key, 0) + 1
                if position == order and order < top:
                    starts.add(key)
    path = Path(run_dir) / f"batch-{index:09d}.tsv.gz"
    _write_run(path, ((key, counts[key], 1 if key in starts else 0) for key in sorted(counts)))
    return str(path), failed


class _Runs:
    """Tiered merge: every MERGE_FAN_IN runs in a tier become one run in the next."""

    def __init__(self, directory: Path, fan_in: int):
        self.directory = directory
        self.fan_in = fan_in
        self.tiers: list[list[Path]] = [[]]
        self.made = 0

    def add(self, path: Path) -> None:
        self.tiers[0].append(path)
        tier = 0
        while len(self.tiers[tier]) >= self.fan_in:
            if tier + 1 == len(self.tiers):
                self.tiers.append([])
            self.tiers[tier + 1].append(self._merge(self.tiers[tier]))
            self.tiers[tier] = []
            tier += 1

    def _merge(self, paths: list[Path]) -> Path:
        self.made += 1
        target = self.directory / f"merge-{self.made:09d}.tsv.gz"
        _write_run(target, _merged(paths))
        for path in paths:
            path.unlink()
        return target

    def final(self) -> Path | None:
        paths = [path for tier in self.tiers for path in tier]
        if not paths:
            return None
        return paths[0] if len(paths) == 1 else self._merge(paths)


def _continuation_run(final: Path, directory: Path, fan_in: int) -> Path | None:
    """Sorted continuation counts for levels below the top.

    Each top-down row (v + context, word) adds one left extension to
    (context, word); a page-start row adds one more. Equal keys are summed when
    runs merge.
    """
    directory.mkdir()
    runs = _Runs(directory, fan_in)
    top = LEVELS[-1]
    buffer: dict[str, int] = {}
    made = 0

    def flush() -> None:
        nonlocal made
        if buffer:
            path = directory / f"continuation-{made:09d}.tsv.gz"
            made += 1
            _write_run(path, ((key, buffer[key], 0) for key in sorted(buffer)))
            buffer.clear()
            runs.add(path)

    for key, _raw, start in _read_run(final):
        level = int(key[0])
        if level >= 1:
            _order, context, word = key.split("\t")
            lower = f"{level - 1}\t{suffix_key(context)}\t{word}"
            buffer[lower] = buffer.get(lower, 0) + 1
        if start and level < top:
            buffer[key] = buffer.get(key, 0) + 1
        if len(buffer) >= CONTINUATION_CHUNK:
            flush()
    flush()
    return runs.final()


def _joined(final: Path | None, continuation: Path | None):
    """Yield (key, level, raw count, adjusted count) for every counted row."""
    if final is None:
        return
    top = LEVELS[-1]
    lower = _read_run(continuation) if continuation is not None else iter(())
    pending = next(lower, None)
    for key, raw, _start in _read_run(final):
        level = int(key[0])
        if level == top:
            yield key, level, raw, raw
            continue
        if pending is None or pending[0] != key:
            raise SmoothingUnavailable(f"level {level}: a counted n-gram has no continuation count")
        yield key, level, raw, pending[1]
        pending = next(lower, None)
    if pending is not None:
        raise SmoothingUnavailable("a continuation count has no counted n-gram")


def _write_stats(path: Path, stats) -> None:
    with gzip.open(path, "wt", encoding="utf-8", newline="\n", compresslevel=1) as handle:
        for context, raw_total, total, weight, kept in stats:
            handle.write(f"{context}\t{raw_total}\t{total}\t{weight!r}\t{kept}\n")


def _read_stats(path: Path):
    with gzip.open(path, "rt", encoding="utf-8", newline="\n") as handle:
        for line in handle:
            context, raw_total, total, weight, kept = line.rstrip("\n").rsplit("\t", 4)
            yield context, int(raw_total), int(total), float(weight), int(kept)


def _load_kept(connection: sqlite3.Connection, rows, stats) -> dict:
    """Insert kept rows, their continuation counts and their contexts' weights."""
    counted: list = []
    adjusted_rows: list = []
    weights: list = []
    report = {str(level): {"kept": 0, "pruned": 0} for level in LEVELS}
    current = None
    raw_total = 0
    for key, level, raw, adjusted in rows:
        context, word = key.rsplit("\t", 1)
        if context != current:
            current, raw_total, total, weight, kept = next(stats)
            if current != context:
                raise RuntimeError("context statistics are out of step with the counts")
            if kept:
                weights.append((level, context.split("\t", 1)[1], total, weight))
        if is_pruned(level, raw):
            report[str(level)]["pruned"] += 1
            continue
        report[str(level)]["kept"] += 1
        context_json = context.split("\t", 1)[1]
        counted.append((level, context_json, word, raw, raw_total))
        adjusted_rows.append((level, context_json, word, adjusted))
        if len(counted) >= INSERT_CHUNK:
            _flush(connection, counted, adjusted_rows, weights)
    _flush(connection, counted, adjusted_rows, weights)
    return report


def _flush(connection: sqlite3.Connection, counted: list, adjusted_rows: list, weights: list) -> None:
    connection.executemany(
        """
        INSERT INTO ngram_counts (
            order_n, context_key, candidate_token, count, context_total, probability, log_probability
        ) VALUES (?, ?, ?, ?, ?, NULL, NULL)
        """,
        counted,
    )
    connection.executemany(
        "INSERT INTO mkn_adjusted (order_n, context_key, candidate_token, adjusted) VALUES (?, ?, ?, ?)",
        adjusted_rows,
    )
    connection.executemany(
        "INSERT INTO context_backoff (order_n, context_key, adjusted_total, backoff_weight) VALUES (?, ?, ?, ?)",
        weights,
    )
    counted.clear()
    adjusted_rows.clear()
    weights.clear()


def _page_fields(elem: ET.Element) -> dict:
    title = ""
    namespace = None
    page_id = None
    revision_id = None
    text = None
    redirect = False
    for child in list(elem):
        name = _local(child.tag)
        if name == "title":
            title = child.text or ""
        elif name == "ns":
            namespace = child.text
        elif name == "id" and page_id is None:
            page_id = child.text
        elif name == "redirect":
            redirect = True
        elif name == "revision":
            for sub in list(child):
                sub_name = _local(sub.tag)
                if sub_name == "id" and revision_id is None:
                    revision_id = sub.text or ""
                elif sub_name == "text":
                    text = sub.text or ""
                sub.text = None
                sub.tail = None
        child.text = None
        child.tail = None
    return {
        "namespace": namespace,
        "page_id": page_id,
        "redirect": redirect,
        "revision_id": revision_id,
        "text": text,
        "title": title,
    }


def iter_pages(path: Path):
    """Yield one page dict at a time from a bz2 multistream dump."""
    with bz2.open(path, "rb") as handle:
        context = ET.iterparse(handle, events=("start", "end"))
        _event, root = next(context)
        for event, elem in context:
            if event != "end" or _local(elem.tag) != "page":
                continue
            yield _page_fields(elem)
            root.remove(elem)
            elem.clear()


def _train_batches(connection, dump_path: Path, snapshot_id: str, counts: dict, batch_pages: int):
    """Record provenance for every page; yield train pages in batches."""
    batch: list[tuple[str, str]] = []
    seen = 0
    for page in iter_pages(dump_path):
        text = page["text"] if page["text"] is not None else ""
        reason = None
        included = False
        page_bucket = None
        which = None
        if page["page_id"] is None or not str(page["page_id"]).isdigit():
            reason = "missing-page-id"
        elif page["namespace"] != "0":
            reason = "namespace"
        elif page["text"] is None:
            reason = "missing-text"
        elif page["redirect"]:
            reason = "redirect"
        else:
            page_bucket = bucket(int(page["page_id"]), snapshot_id)
            which = split_name(int(page["page_id"]), snapshot_id)
            included = which == "train"
        counts["excluded" if reason else which] += 1
        page_id = page["page_id"] or ""
        connection.execute(
            INSERT_PAGE,
            (
                snapshot_id,
                page_id,
                page["revision_id"],
                page["title"],
                f"https://en.wikipedia.org/?curid={page_id}" if page_id else None,
                page["namespace"],
                _sha256(text.encode("utf-8")),
                LICENSE_REFERENCE,
                reason,
                EXTRACTION_VERSION,
                1 if included else 0,
                COMPENDIUM_ID,
                page_bucket,
                which,
            ),
        )
        seen += 1
        if seen % PROVENANCE_COMMIT_PAGES == 0:
            connection.commit()
        if included:
            batch.append((page_id, text))
            if len(batch) >= batch_pages:
                yield batch
                batch = []
        del text
    connection.commit()
    if batch:
        yield batch


def build_compendium(
    dump_path: Path,
    sqlite_path: Path,
    manifest_path: Path,
    sha1_path: Path,
    *,
    snapshot_id: str = SNAPSHOT_ID,
    workers: int = 1,
    batch_pages: int = BATCH_PAGES,
    merge_fan_in: int = MERGE_FAN_IN,
    work_dir: Path | None = None,
) -> dict:
    """Build counts and MKN probabilities, or raise ``SmoothingUnavailable``."""
    if workers < 1 or batch_pages < 1 or merge_fan_in < 2:
        raise ValueError("workers and batch_pages must be at least 1, merge_fan_in at least 2")
    dump_path = Path(dump_path)
    sqlite_path = Path(sqlite_path)
    manifest_path = Path(manifest_path)
    expected = official_sha1(Path(sha1_path), dump_path.name)
    actual_sha1, corpus_sha256 = hash_file(dump_path)
    if actual_sha1 != expected:
        raise DumpChecksumError("official SHA-1 does not match the dump")
    runs_dir = Path(work_dir) if work_dir is not None else sqlite_path.with_name(sqlite_path.name + ".runs")
    if runs_dir.exists():
        shutil.rmtree(runs_dir)
    runs_dir.mkdir(parents=True)
    if sqlite_path.exists():
        sqlite_path.unlink()
    connection = sqlite3.connect(sqlite_path)
    pool = multiprocessing.get_context("spawn").Pool(workers) if workers > 1 else None
    try:
        connection.execute("PRAGMA synchronous = OFF")
        connection.execute("PRAGMA temp_store = FILE")
        connection.execute(CREATE_COUNTS)
        connection.execute(CREATE_PAGES)
        counts = {"train": 0, "validation": 0, "test": 0, "excluded": 0}
        runs = _Runs(runs_dir, merge_fan_in)

        def collect(result: tuple[str, list[str]]) -> None:
            path, failed = result
            runs.add(Path(path))
            for page_id in failed:
                connection.execute(
                    """
                    UPDATE page_provenance
                    SET included_in_compendium = 0, excluded_reason = 'markup-parse-error'
                    WHERE snapshot_id = ? AND page_id = ?
                    """,
                    (snapshot_id, page_id),
                )
                counts["train"] -= 1
                counts["excluded"] += 1

        pending: deque = deque()
        batches = _train_batches(connection, dump_path, snapshot_id, counts, batch_pages)
        for index, batch in enumerate(batches):
            task = (str(runs_dir), index, batch)
            if pool is None:
                collect(count_batch(task))
                continue
            pending.append(pool.apply_async(count_batch, (task,)))
            while len(pending) >= 2 * workers or (pending and pending[0].ready()):
                collect(pending.popleft().get())
        while pending:
            collect(pending.popleft().get())
        connection.commit()
        final = runs.final()
        continuation = (
            _continuation_run(final, runs_dir / "continuation", merge_fan_in) if final is not None else None
        )
        # Pass A: counts-of-counts and discounts over the full, unpruned counts.
        table = discount_table((level, adjusted) for _key, level, _raw, adjusted in _joined(final, continuation))
        # Pass B: per-context totals and weights, still over the full counts.
        stats_path = runs_dir / "context-stats.tsv.gz"
        _write_stats(
            stats_path,
            context_statistics(
                ((key.rsplit("\t", 1)[0], level, raw, adjusted) for key, level, raw, adjusted in _joined(final, continuation)),
                table,
            ),
        )
        # Pass C: load only the kept rows.
        connection.execute(CREATE_ADJUSTED)
        connection.execute(CREATE_BACKOFF)
        write_discounts(connection, table)
        stored = _load_kept(connection, _joined(final, continuation), _read_stats(stats_path))
        connection.commit()
        try:
            mkn = fill_probabilities(connection, table)
        except SmoothingUnavailable:
            connection.rollback()
            raise
        mkn["rows"] = stored
        connection.commit()
        artifact = model_digest(connection)
        counted = counts_digest(connection)
        pages = provenance_digest(connection)
    finally:
        if pool is not None:
            pool.terminate()
            pool.join()
        connection.close()
    shutil.rmtree(runs_dir)
    official = dump_path.name == "enwiki-20261001-pages-articles-multistream.xml.bz2"
    manifest = {
        "artifact_digest": artifact,
        "build_code_version": _build_code_version(),
        "counts_digest": counted,
        "compendium_id": COMPENDIUM_ID,
        "corpus_id": snapshot_id,
        "corpus_sha256": "sha256:" + corpus_sha256,
        "extraction_version": EXTRACTION_VERSION,
        "interpreted_fields": [
            "compendium_id",
            "context_key_json",
            "extraction_version",
            "markup_stripping",
            "mkn_base_uniform_train_vocabulary",
            "mkn_level_0",
            "mkn_log_base_e",
            "mkn_page_start_left_extension",
            "mkn_pruned_mass_to_interpolation_weight",
            "normalizer_version",
            "page_url_template",
            "redirect_pages_excluded",
            "schema_version",
            "tokenizer_version",
        ],
        "keyboard_layout_map_ids": [
            {"id": name, "version": LAYOUT_VERSION} for name in sorted(LAYOUTS)
        ],
        "license_reference": LICENSE_REFERENCE,
        "mkn": mkn,
        "ngram_order": list(ORDERS),
        "normalizer_version": NORMALIZER_VERSION,
        "official_dump": official,
        "official_sha1": "sha1:" + actual_sha1,
        "page_counts": counts,
        "page_provenance_digest": pages,
        "page_provenance_table": "page_provenance",
        "pruning": {"levels": list(PRUNE_SINGLETON_LEVELS), "rule": "drop rows with raw count 1"},
        "probabilities": "computed",
        "schema_version": SCHEMA_VERSION,
        "smoothing_method": SMOOTHING_ID,
        "smoothing_version": SMOOTHING_VERSION,
        "tokenizer_version": TOKENIZER_VERSION,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest
