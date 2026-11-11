import bz2
import hashlib
import math
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from nych_compendium.build import SmoothingRefused, build_compendium, counts_digest
from nych_compendium.gate import automatic_correction_allowed, category_report, lower_bound
from nych_compendium.keyboards import layouts_agree
from nych_compendium.split import bucket, split_name
from nych_smoke.pipeline import run_text

TRAIN_TEXT = "the cat sat the cat sat"
TEST_TEXT = "the uniqtesttoken sat"


def _ids():
    found = {}
    page_id = 1
    while set(found) != {"train", "validation", "test"}:
        found.setdefault(split_name(page_id), page_id)
        page_id += 1
    return found


def _page(page_id, namespace, text, title):
    return (
        "<page>"
        f"<title>{title}</title><ns>{namespace}</ns><id>{page_id}</id>"
        f"<revision><id>{page_id}0</id><text>{text}</text></revision>"
        "</page>"
    )


def _dump(path: Path, pages: list[str]) -> str:
    raw = ("<mediawiki>" + "".join(pages) + "</mediawiki>").encode("utf-8")
    path.write_bytes(bz2.compress(raw))
    digest = hashlib.sha1(path.read_bytes()).hexdigest()
    path.with_suffix(path.suffix + ".sha1").write_text(digest + "  " + path.name + "\n", encoding="utf-8")
    return digest


class TypoCompendium(unittest.TestCase):
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

    def test_synthetic_dump_counts_manifest_and_pipeline(self):
        ids = _ids()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dump = root / "synthetic.xml.bz2"
            _dump(
                dump,
                [
                    _page(ids["train"], 0, TRAIN_TEXT, "Train"),
                    _page(ids["validation"], 0, "the validonly sat", "Validation"),
                    _page(ids["test"], 0, TEST_TEXT, "Test"),
                    _page(999999, 1, "the talkpage sat", "Talk"),
                ],
            )
            with self.assertRaises(TypeError):
                build_compendium(dump, root / "a.sqlite3", root / "a.json", dump.with_suffix(dump.suffix + ".sha1"))
            with self.assertRaises(SmoothingRefused):
                build_compendium(
                    dump,
                    root / "b.sqlite3",
                    root / "b.json",
                    dump.with_suffix(dump.suffix + ".sha1"),
                    smoothing="laplace",
                )
            self.assertFalse((root / "b.sqlite3").exists())
            manifest = build_compendium(
                dump,
                root / "counts.sqlite3",
                root / "manifest.json",
                dump.with_suffix(dump.suffix + ".sha1"),
                smoothing=None,
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
                "keyboard_layout_map_ids",
                "official_sha1",
            ):
                self.assertIn(field, manifest)
            self.assertIsNone(manifest["smoothing_method"])
            self.assertEqual(manifest["probabilities"], "refused")
            self.assertEqual(manifest["ngram_order"], [1, 2, 3])
            self.assertNotIn(TRAIN_TEXT, (root / "manifest.json").read_text(encoding="utf-8"))
            self.assertNotIn(TEST_TEXT, (root / "manifest.json").read_text(encoding="utf-8"))
            connection = sqlite3.connect(root / "counts.sqlite3")
            columns = [row[1] for row in connection.execute("PRAGMA table_info(ngram_counts)")]
            self.assertEqual(
                columns,
                ["order_n", "context_key", "candidate_token", "count", "context_total", "probability", "log_probability"],
            )
            probabilities = connection.execute("SELECT COUNT(*) FROM ngram_counts WHERE probability IS NOT NULL").fetchone()
            self.assertEqual(probabilities[0], 0)
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
            connection.execute("UPDATE ngram_counts SET count = count + 1 WHERE candidate_token = 'cat'")
            connection.commit()
            self.assertNotEqual(counts_digest(connection), before)
            connection.close()
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
                    "--smoothing",
                    "none",
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
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
                    "--smoothing",
                    "laplace",
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(refused.returncode, 2)
            self.assertIn("refusing", refused.stderr)


if __name__ == "__main__":
    unittest.main()
