import bz2
import hashlib
import json
import math
import random
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

from nych_compendium.build import DumpChecksumError, build_compendium, counts_digest, official_sha1
from nych_compendium.gate import automatic_correction_allowed, category_report, lower_bound
from nych_compendium.keyboards import layouts_agree
from nych_compendium.smoothing import SMOOTHING_ID, SmoothingUnavailable, discounts, probability
from nych_compendium.wikitext import plain_text
from nych_compendium.split import bucket, split_name
from nych_smoke.pipeline import run_text

TRAIN_TEXT = "the cat sat the cat sat"
TEST_TEXT = "the uniqtesttoken sat"
# Synthetic train vocabulary: a Zipf-like head plus a rare tail, so every MKN
# level has counts-of-counts n1..n4 above zero.
VOCAB = ["the", "cat", "sat"] + [f"w{i:02d}" for i in range(1, 31)] + [f"r{i:02d}" for i in range(1, 41)]
WEIGHTS = [1.0 / rank for rank in range(1, 34)] + [0.004] * 40


def _ids():
    found = {}
    page_id = 1
    while set(found) != {"train", "validation", "test"}:
        found.setdefault(split_name(page_id), page_id)
        page_id += 1
    return found


def _train_ids(count):
    found = []
    page_id = 1
    while len(found) < count:
        if split_name(page_id) == "train":
            found.append(page_id)
        page_id += 1
    return found


def _train_pages():
    rng = random.Random(20261112)
    return [["the", "cat", "sat"] + rng.choices(VOCAB, WEIGHTS, k=400) for _ in range(6)]


def _reference_mkn(pages, top=3):
    """Independent dict-based interpolated MKN, used only to check the SQL build."""
    raw = [Counter() for _ in range(top + 1)]
    starts = [set() for _ in range(top)]
    for words in pages:
        for i, word in enumerate(words):
            for k in range(top + 1):
                if i < k:
                    continue
                gram = (tuple(words[i - k : i]), word)
                raw[k][gram] += 1
                if k < top and i == k:
                    starts[k].add(gram)
    adjusted = [None] * (top + 1)
    adjusted[top] = dict(raw[top])
    for k in range(top - 1, -1, -1):
        level = Counter()
        for context, word in raw[k + 1]:
            level[(context[1:], word)] += 1
        for gram in starts[k]:
            level[gram] += 1
        adjusted[k] = dict(level)
    vocabulary = len(raw[0])
    probs = [{} for _ in range(top + 1)]
    for k in range(top + 1):
        coc = Counter(adjusted[k].values())
        d1, d2, d3 = discounts(k, coc[1], coc[2], coc[3], coc[4])
        table = {1: d1, 2: d2, 3: d3}
        totals = Counter()
        mass = Counter()
        for (context, word), a in adjusted[k].items():
            totals[context] += a
            mass[context] += table[min(a, 3)]
            if k in (2, 3) and raw[k][(context, word)] == 1:
                # Owner-chosen pruning: the row is dropped and its mass goes to the weight.
                mass[context] += max(a - table[min(a, 3)], 0)
        for (context, word), a in adjusted[k].items():
            if k in (2, 3) and raw[k][(context, word)] == 1:
                continue
            gamma = mass[context] / totals[context]
            lower = 1.0 / vocabulary if k == 0 else probs[k - 1][(context[1:], word)]
            probs[k][(context, word)] = max(a - table[min(a, 3)], 0) * 1.0 / totals[context] + gamma * lower
    return probs


def _page(page_id, namespace, text, title):
    return (
        "<page>"
        f"<title>{title}</title><ns>{namespace}</ns><id>{page_id}</id>"
        f"<revision><id>{page_id}0</id><text>{text}</text></revision>"
        "</page>"
    )


def _wiki_page(page_id, text, title, redirect=None):
    marker = f'<redirect title="{escape(redirect)}" />' if redirect else ""
    return (
        "<page>"
        f"<title>{escape(title)}</title><ns>0</ns><id>{page_id}</id>{marker}"
        f"<revision><id>{page_id}0</id><text>{escape(text)}</text></revision>"
        "</page>"
    )


MARKUP_PAGE = (
    "{{Infobox settlement|name=Zorvik}}'''Zorvik''' is a [[harbour town|harbourtown]] in [[Qelland]]."
    "<ref>{{cite web|url=http://example.org|title=Refonly}}</ref> See https://example.org/zz today.\n"
    "[[File:Zorvik.jpg|thumb|Captiononly view]]\n== Heritage ==\n"
    "<!-- commentonly --> E=<math>mcsquared</math> [[Category:Townsonly]] &amp; more"
)


def _dump(path: Path, pages: list[str]) -> str:
    raw = ("<mediawiki>" + "".join(pages) + "</mediawiki>").encode("utf-8")
    path.write_bytes(bz2.compress(raw))
    digest = hashlib.sha1(path.read_bytes()).hexdigest()
    path.with_suffix(path.suffix + ".sha1").write_text(digest + "  " + path.name + "\n", encoding="utf-8")
    return digest


class TypoCompendium(unittest.TestCase):
    def test_markup_is_stripped_before_counting(self):
        text = plain_text(MARKUP_PAGE)
        for kept in ("Zorvik is a harbourtown in Qelland.", "Heritage", "today", "& more"):
            self.assertIn(kept, text)
        for dropped in ("Infobox", "cite", "Refonly", "http", "example", "thumb", "Captiononly",
                        "commentonly", "mcsquared", "Category", "Townsonly", "[[", "{{", "''", "=="):
            self.assertNotIn(dropped, text)
        self.assertEqual(plain_text("see [[:Category:Towns]]"), "see :Category:Towns")

    def test_official_sha1_picks_the_dump_line_from_a_list(self):
        with tempfile.TemporaryDirectory() as directory:
            listing = Path(directory) / "sha1sums.txt"
            listing.write_text("a" * 40 + "  other.xml.bz2\n" + "b" * 40 + "  dump.xml.bz2\n", encoding="utf-8")
            self.assertEqual(official_sha1(listing, "dump.xml.bz2"), "b" * 40)
            with self.assertRaises(DumpChecksumError):
                official_sha1(listing, "missing.xml.bz2")
            single = Path(directory) / "one.sha1"
            single.write_text("c" * 40 + "  anything\n", encoding="utf-8")
            self.assertEqual(official_sha1(single, "dump.xml.bz2"), "c" * 40)

    def test_markup_redirects_and_batched_parallel_build(self):
        train_pages = _train_pages()
        ids = _train_ids(len(train_pages) + 2)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dump = root / "markup.xml.bz2"
            _dump(
                dump,
                [_page(page_id, 0, " ".join(words), f"Train {page_id}") for page_id, words in zip(ids, train_pages)]
                + [
                    _wiki_page(ids[-2], MARKUP_PAGE, "Zorvik"),
                    _wiki_page(ids[-1], "#REDIRECT [[Redirectonly]]", "Old Zorvik", redirect="Redirectonly"),
                ],
            )
            sha1 = dump.with_suffix(dump.suffix + ".sha1")
            single = build_compendium(dump, root / "one.sqlite3", root / "one.json", sha1)
            batched = build_compendium(
                dump,
                root / "many.sqlite3",
                root / "many.json",
                sha1,
                workers=2,
                batch_pages=1,
                merge_fan_in=2,
            )
            self.assertEqual(batched["artifact_digest"], single["artifact_digest"])
            self.assertEqual(batched["counts_digest"], single["counts_digest"])
            self.assertEqual(batched["page_provenance_digest"], single["page_provenance_digest"])
            self.assertEqual(single["page_counts"]["train"], len(train_pages) + 1)
            self.assertFalse((root / "many.sqlite3.runs").exists())
            connection = sqlite3.connect(root / "many.sqlite3")
            words = {row[0] for row in connection.execute("SELECT candidate_token FROM ngram_counts WHERE order_n = 0")}
            self.assertTrue({"Zorvik", "harbourtown", "Qelland", "Heritage", "today"} <= words)
            for dropped in ("Infobox", "cite", "Refonly", "https", "thumb", "Captiononly", "commentonly",
                            "mcsquared", "Townsonly", "Redirectonly", "REDIRECT"):
                self.assertNotIn(dropped, words)
            reason = connection.execute(
                "SELECT excluded_reason, included_in_compendium FROM page_provenance WHERE page_id = ?",
                (str(ids[-1]),),
            ).fetchone()
            self.assertEqual(reason, ("redirect", 0))
            connection.close()

    def test_buckets_are_stable_and_cover_the_approved_ranges(self):
        ids = _ids()
        self.assertEqual(bucket(ids["train"]), bucket(ids["train"]))
        self.assertLessEqual(bucket(ids["train"]), 89)
        self.assertGreaterEqual(bucket(ids["validation"]), 90)
        self.assertLessEqual(bucket(ids["validation"]), 94)
        self.assertGreaterEqual(bucket(ids["test"]), 95)
        self.assertEqual(split_name(ids["test"]), "test")

    def test_gate_threshold_categories_and_keyboard_agreement(self):
        self.assertFalse(automatic_correction_allowed(298, 298))
        self.assertTrue(automatic_correction_allowed(299, 299))
        self.assertAlmostEqual(lower_bound(299, 299), 0.05 ** (1.0 / 299))
        self.assertAlmostEqual(lower_bound(1, 2), 1.0 - math.sqrt(0.95), places=6)
        self.assertEqual(lower_bound(0, 5), 0.0)
        report = category_report(
            [
                {"category": "proper_names", "layout": "us-qwerty", "corrected": True, "false_correction": False},
                {"category": "scientific_terms", "layout": "uk-qwerty", "corrected": True, "false_correction": True},
                {"category": "coherent_rare_words", "layout": "azerty", "corrected": False, "false_correction": False},
                {"category": "ambiguous_candidates", "layout": "qwertz", "corrected": False, "false_correction": False},
            ]
        )
        self.assertEqual(report["categories"]["proper_names"]["precision"], 1.0)
        self.assertEqual(report["categories"]["scientific_terms"]["false_correction_rate"], 1.0)
        self.assertEqual(report["layouts"]["azerty"]["precision"], None)
        self.assertTrue(layouts_agree("thr", "the", None))
        self.assertFalse(layouts_agree("w", "x", None))
        self.assertTrue(layouts_agree("w", "x", "azerty"))

    def test_sparse_counts_stop_the_build_without_a_manifest(self):
        ids = _ids()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dump = root / "sparse.xml.bz2"
            _dump(dump, [_page(ids["train"], 0, TRAIN_TEXT, "Train")])
            with self.assertRaises(SmoothingUnavailable):
                build_compendium(dump, root / "a.sqlite3", root / "a.json", dump.with_suffix(dump.suffix + ".sha1"))
            self.assertFalse((root / "a.json").exists())
            connection = sqlite3.connect(root / "a.sqlite3")
            filled = connection.execute("SELECT COUNT(*) FROM ngram_counts WHERE probability IS NOT NULL").fetchone()
            connection.close()
            self.assertEqual(filled[0], 0)
            refused = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nych_compendium",
                    "build",
                    "--dump",
                    str(dump),
                    "--sha1",
                    str(dump.with_suffix(dump.suffix + ".sha1")),
                    "--sqlite",
                    str(root / "refused.sqlite3"),
                    "--manifest",
                    str(root / "refused.json"),
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(refused.returncode, 2)
            self.assertIn("Chen-Goodman", refused.stderr)
            self.assertFalse((root / "refused.json").exists())

    def test_discount_bounds_are_enforced(self):
        d1, d2, d3 = discounts(0, 1, 1, 1, 1)
        self.assertAlmostEqual(d1, 1 / 3)
        self.assertAlmostEqual(d2, 1.0)
        self.assertAlmostEqual(d3, 5 / 3)
        with self.assertRaises(SmoothingUnavailable):
            discounts(0, 5, 0, 3, 1)
        with self.assertRaises(SmoothingUnavailable):
            discounts(0, 100, 1, 10, 1)

    def test_synthetic_dump_counts_manifest_and_pipeline(self):
        ids = _ids()
        train_pages = _train_pages()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dump = root / "synthetic.xml.bz2"
            _dump(
                dump,
                [
                    _page(page_id, 0, " ".join(words), f"Train {page_id}")
                    for page_id, words in zip(_train_ids(len(train_pages)), train_pages)
                ]
                + [
                    _page(ids["validation"], 0, "the validonly sat", "Validation"),
                    _page(ids["test"], 0, TEST_TEXT, "Test"),
                    _page(999999, 1, "the talkpage sat", "Talk"),
                ],
            )
            manifest = build_compendium(
                dump,
                root / "counts.sqlite3",
                root / "manifest.json",
                dump.with_suffix(dump.suffix + ".sha1"),
            )
            for field in (
                "schema_version",
                "compendium_id",
                "corpus_id",
                "license_reference",
                "corpus_sha256",
                "tokenizer_version",
                "normalizer_version",
                "ngram_order",
                "smoothing_method",
                "smoothing_version",
                "build_code_version",
                "artifact_digest",
                "counts_digest",
                "keyboard_layout_map_ids",
                "official_sha1",
            ):
                self.assertIn(field, manifest)
            self.assertEqual(manifest["smoothing_method"], SMOOTHING_ID)
            self.assertEqual(manifest["smoothing_method"], "chen-goodman-mkn-interpolated-v1")
            self.assertEqual(manifest["probabilities"], "computed")
            self.assertEqual(manifest["ngram_order"], [1, 2, 3])
            self.assertEqual(manifest["mkn"]["levels"], [0, 1, 2, 3])
            self.assertEqual(manifest["pruning"]["levels"], [2, 3])
            for level in ("2", "3"):
                self.assertGreater(manifest["mkn"]["rows"][level]["pruned"], 0)
                self.assertGreater(manifest["mkn"]["rows"][level]["kept"], 0)
            for level in ("0", "1"):
                self.assertEqual(manifest["mkn"]["rows"][level]["pruned"], 0)
            self.assertNotIn(TRAIN_TEXT, (root / "manifest.json").read_text(encoding="utf-8"))
            self.assertNotIn(TEST_TEXT, (root / "manifest.json").read_text(encoding="utf-8"))
            connection = sqlite3.connect(root / "counts.sqlite3")
            columns = [row[1] for row in connection.execute("PRAGMA table_info(ngram_counts)")]
            self.assertEqual(
                columns,
                ["order_n", "context_key", "candidate_token", "count", "context_total", "probability", "log_probability"],
            )
            singletons = connection.execute(
                "SELECT COUNT(*) FROM ngram_counts WHERE order_n IN (2, 3) AND count = 1"
            ).fetchone()
            self.assertEqual(singletons[0], 0)
            missing = connection.execute(
                "SELECT COUNT(*) FROM ngram_counts WHERE probability IS NULL OR log_probability IS NULL"
            ).fetchone()
            self.assertEqual(missing[0], 0)
            reference = _reference_mkn(train_pages)
            rows = connection.execute(
                "SELECT order_n, context_key, candidate_token, probability, log_probability FROM ngram_counts"
            ).fetchall()
            self.assertEqual(len(rows), sum(len(level) for level in reference))
            for order, key, word, prob, log_prob in rows:
                expected = reference[order][(tuple(json.loads(key)), word)]
                self.assertAlmostEqual(prob, expected, places=12)
                self.assertAlmostEqual(log_prob, math.log(expected), places=9)
            vocabulary = [row[0] for row in connection.execute(
                "SELECT candidate_token FROM ngram_counts WHERE order_n = 0 ORDER BY candidate_token"
            )]
            self.assertEqual(len(vocabulary), manifest["mkn"]["vocabulary_size"])
            for context in ([], ["the"], ["the", "cat"], ["the", "cat", "sat"], ["w01", "w02", "w03"], ["notaword"]):
                total = sum(probability(connection, context, word) for word in vocabulary)
                self.assertAlmostEqual(total, 1.0, places=9, msg=context)
            self.assertIsNone(probability(connection, ["the"], "uniqtesttoken"))
            before_model = manifest["artifact_digest"]
            leaked = connection.execute(
                "SELECT COUNT(*) FROM ngram_counts WHERE candidate_token = ?",
                ("uniqtesttoken",),
            ).fetchone()
            self.assertEqual(leaked[0], 0)
            valid = connection.execute(
                "SELECT COUNT(*) FROM ngram_counts WHERE candidate_token = ?",
                ("validonly",),
            ).fetchone()
            self.assertEqual(valid[0], 0)
            counted = connection.execute(
                "SELECT COUNT(*) FROM ngram_counts WHERE candidate_token = ?",
                ("cat",),
            ).fetchone()
            self.assertGreater(counted[0], 0)
            page_columns = [row[1] for row in connection.execute("PRAGMA table_info(page_provenance)")]
            self.assertNotIn("text", page_columns)
            self.assertNotIn("page_text", page_columns)
            before = counts_digest(connection)
            self.assertEqual(before, manifest["counts_digest"])
            connection.execute("UPDATE ngram_counts SET count = count + 1 WHERE candidate_token = 'cat'")
            connection.commit()
            self.assertNotEqual(counts_digest(connection), before)
            connection.close()
            self.assertTrue(before_model.startswith("sha256:"))
            low = run_text(
                b"the car sat",
                request_id="typo-low",
                received_at="2026-11-10T00:00:00Z",
                typo_sqlite=root / "counts.sqlite3",
                typo_gate=(297, 297),
            )
            self.assertEqual([token["text"] for token in low["tokens"] if token["kind"] == "word"], ["the", "car", "sat"])
            self.assertEqual(low["typo"]["automatic_replacements"], 0)
            self.assertEqual(low["typo"]["automatic_hypotheses"], 0)
            high = run_text(
                b"the car sat",
                request_id="typo-high",
                received_at="2026-11-10T00:00:00Z",
                typo_sqlite=root / "counts.sqlite3",
                typo_gate=(299, 299),
            )
            self.assertEqual([token["text"] for token in high["tokens"] if token["kind"] == "word"], ["the", "car", "sat"])
            self.assertEqual(high["typo"]["automatic_replacements"], 0)
            self.assertEqual(high["typo"]["automatic_hypotheses"], 1)
            self.assertEqual(high["typo"]["hypotheses"][1]["surface"], "car")
            self.assertEqual(high["typo"]["hypotheses"][1]["candidate"], "cat")
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nych_compendium",
                    "build",
                    "--dump",
                    str(dump),
                    "--sha1",
                    str(dump.with_suffix(dump.suffix + ".sha1")),
                    "--sqlite",
                    str(root / "cli.sqlite3"),
                    "--manifest",
                    str(root / "cli.json"),
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stdout.splitlines()[0], before_model)


if __name__ == "__main__":
    unittest.main()
