"""Stream one Wikipedia page at a time into private n-gram counts.

No dump or article text is retained. Page text is hashed and discarded.
Smoothing is a required argument with no default. ``None`` builds counts and
leaves probability columns null. Any other value is refused, because the owner
has not named a smoothing method.

Interpreted plumbing: schema version, compendium id, tokenizer and normalizer
version strings, context-key JSON, the separate SQLite file, the provenance
table, the curid URL, and storing per-page rows in SQLite instead of inline
in the manifest so the full dump can stay inside about 4 GB of RAM.
"""
from __future__ import annotations

import bz2
import hashlib
import json
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

from nych_compendium.keyboards import LAYOUT_VERSION, LAYOUTS
from nych_compendium.split import SNAPSHOT_ID, bucket, split_name
from nych_smoke.tokenize import tokenize

SCHEMA_VERSION = "mg8.statistical-compendium.v1"
COMPENDIUM_ID = "nych-d2-enwiki-20261001"
TOKENIZER_VERSION = "b2-whitespace-spans-v1"
NORMALIZER_VERSION = "identity-v1"
EXTRACTION_VERSION = "nych-compendium-stream-v1"
LICENSE_REFERENCE = "CC BY-SA 4.0 and GFDL; page-level exceptions were not identified in this stream"
ORDERS = (1, 2, 3)

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
)
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


class SmoothingRefused(RuntimeError):
    """Raised when a smoothing method is named but not owner-chosen."""


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


def official_sha1(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    token = ""
    for char in text.lower():
        if char in "0123456789abcdef":
            token += char
            if len(token) == 40:
                return token
        else:
            token = ""
    raise DumpChecksumError("official checksum file has no SHA-1")


def context_key(words: list[str]) -> str:
    return json.dumps(words, ensure_ascii=False, separators=(",", ":"))


def counts_digest(connection: sqlite3.Connection) -> str:
    rows = connection.execute(
        """
        SELECT order_n, context_key, candidate_token, count, context_total
        FROM ngram_counts
        ORDER BY order_n, context_key, candidate_token
        """
    ).fetchall()
    body = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(body).hexdigest()


def provenance_digest(connection: sqlite3.Connection) -> str:
    rows = connection.execute(
        """
        SELECT snapshot_id, page_id, revision_id, title, page_url, namespace_id,
               page_text_sha256, license_basis, excluded_reason, extraction_version,
               included_in_compendium, compendium_build_id, bucket, split_name
        FROM page_provenance
        ORDER BY snapshot_id, page_id
        """
    ).fetchall()
    body = json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(body).hexdigest()


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


def _count_page(connection: sqlite3.Connection, words: list[str]) -> None:
    for index, candidate in enumerate(words):
        for order in ORDERS:
            if index < order:
                continue
            key = context_key(words[index - order : index])
            connection.execute(
                """
                INSERT INTO ngram_counts (
                    order_n, context_key, candidate_token, count, context_total,
                    probability, log_probability
                ) VALUES (?, ?, ?, 1, 0, NULL, NULL)
                ON CONFLICT(order_n, context_key, candidate_token)
                DO UPDATE SET count = count + 1
                """,
                (order, key, candidate),
            )


def _page_fields(elem: ET.Element) -> dict:
    title = ""
    namespace = None
    page_id = None
    revision_id = None
    text = None
    for child in list(elem):
        name = _local(child.tag)
        if name == "title":
            title = child.text or ""
        elif name == "ns":
            namespace = child.text
        elif name == "id" and page_id is None:
            page_id = child.text
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


def _fill_context_totals(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        UPDATE ngram_counts
        SET context_total = (
            SELECT SUM(other.count)
            FROM ngram_counts AS other
            WHERE other.order_n = ngram_counts.order_n
              AND other.context_key = ngram_counts.context_key
        )
        """
    )


def build_compendium(
    dump_path: Path,
    sqlite_path: Path,
    manifest_path: Path,
    sha1_path: Path,
    *,
    smoothing: str | None,
    snapshot_id: str = SNAPSHOT_ID,
) -> dict:
    """Build counts. ``smoothing`` must be passed. Only ``None`` is accepted."""
    if smoothing is not None:
        raise SmoothingRefused(
            "no owner-chosen smoothing method is recorded; refusing to compute probabilities"
        )
    dump_path = Path(dump_path)
    sqlite_path = Path(sqlite_path)
    manifest_path = Path(manifest_path)
    expected = official_sha1(Path(sha1_path))
    actual_sha1, corpus_sha256 = hash_file(dump_path)
    if actual_sha1 != expected:
        raise DumpChecksumError("official SHA-1 does not match the dump")
    if sqlite_path.exists():
        sqlite_path.unlink()
    connection = sqlite3.connect(sqlite_path)
    try:
        connection.execute(CREATE_COUNTS)
        connection.execute(CREATE_PAGES)
        counts = {"train": 0, "validation": 0, "test": 0, "excluded": 0}
        for page in iter_pages(dump_path):
            text = page["text"] if page["text"] is not None else ""
            text_sha = _sha256(text.encode("utf-8"))
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
            else:
                page_bucket = bucket(int(page["page_id"]), snapshot_id)
                which = split_name(int(page["page_id"]), snapshot_id)
                included = which == "train"
            if included:
                _count_page(connection, _words(text))
            counts["excluded" if reason else which] += 1
            page_id = page["page_id"] or ""
            connection.execute(
                """
                INSERT INTO page_provenance (
                    snapshot_id, page_id, revision_id, title, page_url, namespace_id,
                    page_text_sha256, license_basis, excluded_reason, extraction_version,
                    included_in_compendium, compendium_build_id, bucket, split_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    page_id,
                    page["revision_id"],
                    page["title"],
                    f"https://en.wikipedia.org/?curid={page_id}" if page_id else None,
                    page["namespace"],
                    text_sha,
                    LICENSE_REFERENCE,
                    reason,
                    EXTRACTION_VERSION,
                    1 if included else 0,
                    COMPENDIUM_ID,
                    page_bucket,
                    which,
                ),
            )
            del text
            connection.commit()
        _fill_context_totals(connection)
        connection.commit()
        artifact = counts_digest(connection)
        pages = provenance_digest(connection)
    finally:
        connection.close()
    official = dump_path.name == "enwiki-20261001-pages-articles-multistream.xml.bz2"
    manifest = {
        "artifact_digest": artifact,
        "build_code_version": _build_code_version(),
        "compendium_id": COMPENDIUM_ID,
        "corpus_id": snapshot_id,
        "corpus_sha256": "sha256:" + corpus_sha256,
        "interpreted_fields": [
            "compendium_id",
            "context_key_json",
            "extraction_version",
            "normalizer_version",
            "page_url_template",
            "schema_version",
            "tokenizer_version",
        ],
        "keyboard_layout_map_ids": [
            {"id": name, "version": LAYOUT_VERSION} for name in sorted(LAYOUTS)
        ],
        "license_reference": LICENSE_REFERENCE,
        "ngram_order": list(ORDERS),
        "normalizer_version": NORMALIZER_VERSION,
        "official_dump": official,
        "official_sha1": "sha1:" + actual_sha1,
        "page_counts": counts,
        "page_provenance_digest": pages,
        "page_provenance_table": "page_provenance",
        "probabilities": "refused",
        "schema_version": SCHEMA_VERSION,
        "smoothing_method": None,
        "smoothing_version": None,
        "tokenizer_version": TOKENIZER_VERSION,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest
