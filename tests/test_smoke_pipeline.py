import unittest

from nych_preview.gestalt_abbreviation import abbreviate_word
from nych_smoke.pipeline import load_english_sample, run_text
from nych_smoke.report import stage_report
from nych_smoke.tiny_train import D_MODEL, FFN, N_HEAD, N_LAYER, non_embedding_parameters, train_sample
from nych_smoke.tokenize import tokenize
from nych_smoke.trace_id import consonant_suffix, trace_id


class SmokePipeline(unittest.TestCase):
    def test_spans_cover_source_and_keep_internal_marks(self):
        raw, tokens = tokenize("can't red-barn.\n")
        self.assertEqual(b"".join(raw[token.start:token.end] for token in tokens), raw)
        self.assertEqual([token.text for token in tokens], ["can't", "<SPACE>", "red-barn", ".", "<LF>"])
        self.assertEqual(tokens[0].kind, "word")
        self.assertEqual(raw[tokens[2].start:tokens[2].end].decode(), "red-barn")

    def test_trace_ids_differ_by_occurrence(self):
        report = run_text("the the")
        words = [token for token in report["tokens"] if token["kind"] == "word"]
        self.assertEqual(words[0]["suffix"], consonant_suffix("the"))
        self.assertNotEqual(words[0]["trace_id"], words[1]["trace_id"])
        self.assertTrue(words[0]["trace_id"].startswith("sha256:"))
        self.assertTrue(words[0]["trace_id"].endswith("_" + words[0]["suffix"]))
        rebuilt = trace_id(bytes.fromhex(report["input_sha256"].split(":", 1)[1]), 0, words[0]["start"], words[0]["end"], words[0]["suffix"])
        self.assertEqual(rebuilt, words[0]["trace_id"])

    def test_gestalt_helper_is_used_and_open_edges_stay_open(self):
        report = run_text("hot dog yellow")
        self.assertEqual(report["gestalts"][0]["abbrev"], "htDg")
        self.assertEqual(report["gestalts"][0]["status"], "owner-listed-compound")
        self.assertTrue(report["gestalts"][1]["status"].startswith("open:"))
        sample = run_text(load_english_sample()["text"])
        asked = next(row for row in sample["gestalts"] if row["surface"] == ["asked"])
        self.assertEqual(asked["abbrev"], abbreviate_word("asked"))
        hyphen = next(row for row in sample["gestalts"] if row["surface"] == ["co-operative"])
        self.assertTrue(hyphen["status"].startswith("open:"))

    def test_english_sample_and_shape_and_three_cpu_steps(self):
        sample = load_english_sample()
        self.assertEqual(sample["language"], "English")
        self.assertIn("Open Parliament", sample["license"])
        result = train_sample()
        self.assertEqual(result["device"], "cpu")
        self.assertFalse(result["cuda"])
        self.assertFalse(result["v100"])
        self.assertEqual(result["steps"], 3)
        self.assertEqual(len(result["losses"]), 3)
        self.assertTrue(all(loss == loss and loss > 0 for loss in result["losses"]))
        self.assertEqual(result["non_embedding_parameters"], 2 * (4 * D_MODEL * D_MODEL + 3 * D_MODEL * FFN + 2 * D_MODEL) + D_MODEL)
        self.assertEqual(result["non_embedding_parameters"], 524928)
        self.assertEqual(N_LAYER, 2)
        self.assertEqual(N_HEAD, 4)
        self.assertEqual(non_embedding_parameters.__name__, "non_embedding_parameters")

    def test_stage_report_names_what_did_not_run(self):
        report = stage_report()
        stages = report["stages"]
        self.assertEqual(stages["tokenize_spans"]["status"], "wired and passing")
        self.assertEqual(stages["trace_id"]["status"], "wired and passing")
        self.assertEqual(stages["gestalt_abbreviation"]["status"], "wired and passing")
        self.assertEqual(stages["training"]["status"], "wired and passing")
        self.assertFalse(stages["training"]["detail"]["v100"])
        self.assertEqual(stages["gitson_validator"]["validator_verdict"], "PASS")
        self.assertEqual(stages["emoji_inventory"]["status"], "wired and passing")
        self.assertEqual(stages["proper_names"]["status"], "provisional")
        self.assertGreater(stages["proper_names"]["interpreted_names"], 0)
        for name in ("typo_compendium", "inspector", "b1_ingest", "b5_gst", "b6_symbol_call"):
            self.assertEqual(stages[name]["status"], "not runnable here", name)
        self.assertEqual(stages["domain_switch"]["status"], "not wired")
        self.assertGreater(report["open_gestalt_count"], 0)


if __name__ == "__main__":
    unittest.main()
