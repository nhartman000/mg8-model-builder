import unittest

from nych_preview.gestalt_abbreviation import abbreviate_word
from nych_smoke.pipeline import load_english_sample, run_text
from nych_smoke.upstream import ingest_bytes
from nych_smoke.report import stage_report
from nych_smoke.tiny_train import D_MODEL, FFN, N_HEAD, N_LAYER, non_embedding_parameters, train_sample
from nych_smoke.tokenize import tokenize
from nych_smoke.trace_id import consonant_suffix, input_digest, trace_id


class SmokePipeline(unittest.TestCase):
    def run_bytes(self, text):
        return run_text(
            text.encode("utf-8"),
            request_id="smoke-test",
            received_at="2026-01-01T00:00:00Z",
        )

    def test_spans_cover_source_and_keep_internal_marks(self):
        raw, tokens = tokenize("can't red-barn.\n")
        self.assertEqual(b"".join(raw[token.start:token.end] for token in tokens), raw)
        self.assertEqual([token.text for token in tokens], ["can't", "<SPACE>", "red-barn", ".", "<LF>"])
        self.assertEqual(tokens[0].kind, "word")
        self.assertEqual(raw[tokens[2].start:tokens[2].end].decode(), "red-barn")

    def test_trace_ids_differ_by_occurrence(self):
        raw = b"the the"
        report = run_text(raw, request_id="smoke-test", received_at="2026-01-01T00:00:00Z")
        self.assertEqual(report["ingest"]["raw_sha256"], "sha256:" + input_digest(raw).hex())
        words = [token for token in report["tokens"] if token["kind"] == "word"]
        self.assertEqual(words[0]["suffix"], consonant_suffix("the"))
        self.assertNotEqual(words[0]["trace_id"], words[1]["trace_id"])
        self.assertTrue(words[0]["trace_id"].startswith("sha256:"))
        self.assertTrue(words[0]["trace_id"].endswith("_" + words[0]["suffix"]))
        rebuilt = trace_id(bytes.fromhex(report["input_sha256"].split(":", 1)[1]), 0, words[0]["start"], words[0]["end"], words[0]["suffix"])
        self.assertEqual(rebuilt, words[0]["trace_id"])

    def test_gestalt_helper_is_used_and_open_edges_stay_open(self):
        report = self.run_bytes("hot dog yellow")
        self.assertEqual(report["gestalts"][0]["abbrev"], "htDg")
        self.assertEqual(report["gestalts"][0]["status"], "owner-listed-compound")
        self.assertTrue(report["gestalts"][1]["status"].startswith("open:"))
        sample = self.run_bytes(load_english_sample()["text"])
        asked = next(row for row in sample["gestalts"] if row["surface"] == ["asked"])
        self.assertEqual(asked["abbrev"], abbreviate_word("asked"))
        hyphen = next(row for row in sample["gestalts"] if row["surface"] == ["co-operative"])
        self.assertTrue(hyphen["status"].startswith("open:"))

    def test_b1_accepts_exact_bytes_and_rejects_boundary_failures(self):
        received_at = "2026-01-01T00:00:00Z"
        accepted = ingest_bytes(
            b"x" * 65_536,
            request_id="b1-boundary-test",
            received_at=received_at,
        )
        self.assertEqual(accepted.status, "ACCEPTED")
        self.assertEqual(accepted.byte_length, 65_536)
        self.assertEqual(accepted.text.encode("utf-8"), b"x" * 65_536)
        for raw, code in ((b"", "EMPTY_INPUT"), (b"\xff", "INVALID_UTF8"), (b"x" * 65_537, "INPUT_TOO_LARGE")):
            with self.subTest(code=code):
                rejected = ingest_bytes(raw, request_id="b1-reject-test", received_at=received_at)
                self.assertEqual(rejected.status, "REJECTED")
                self.assertIsNone(rejected.text)
                self.assertEqual(rejected.error_code, code)

    def test_english_sample_and_shape_and_three_cpu_steps(self):
        sample = load_english_sample()
        self.assertEqual(sample["language"], "English")
        self.assertIn("Open Parliament", sample["license"])
        import torch
        result = train_sample(device="cpu")
        self.assertEqual(result["device"], "cpu")
        self.assertEqual(result["cuda"], torch.cuda.is_available())
        self.assertFalse(result["v100"])
        self.assertEqual(result["steps"], 3)
        self.assertEqual(len(result["losses"]), 3)
        self.assertTrue(all(loss == loss and loss > 0 for loss in result["losses"]))
        self.assertEqual(result["non_embedding_parameters"], 2 * (4 * D_MODEL * D_MODEL + 3 * D_MODEL * FFN + 2 * D_MODEL) + D_MODEL)
        self.assertEqual(result["non_embedding_parameters"], 524928)
        self.assertEqual(N_LAYER, 2)
        self.assertEqual(N_HEAD, 4)
        self.assertEqual(non_embedding_parameters.__name__, "non_embedding_parameters")

    def test_rope_stays_on_the_activation_device(self):
        import torch
        from nych_smoke.tiny_train import HEAD_DIM, N_HEAD, SmokeBlock

        block = SmokeBlock()
        states = torch.randn(4, N_HEAD, HEAD_DIM)
        rotated = block._rope(states)
        self.assertEqual(rotated.device, states.device)
        hidden = torch.randn(4, 128)
        output = block(hidden)
        self.assertEqual(output.device.type, "cpu")

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
        for name in ("typo_compendium", "b5_gst", "b6_symbol_call"):
            self.assertEqual(stages[name]["status"], "not runnable here", name)
        self.assertEqual(stages["b1_ingest"]["status"], "wired and passing")
        self.assertEqual(stages["typo_compendium"]["probabilities"], "not-computed-this-run")
        self.assertEqual(stages["typo_compendium"]["smoothing_method"], "chen-goodman-mkn-interpolated-v1")
        self.assertEqual(stages["typo_compendium"]["automatic_replacements"], 0)
        self.assertNotEqual(stages["typo_compendium"]["status"], "wired and passing")
        self.assertEqual(stages["inspector"]["validator_was_the_inspector"], False)
        self.assertFalse(stages["inspector"]["authorizes_wiring"])
        self.assertEqual(stages["inspector"]["verdict"], "PASS")
        self.assertEqual(stages["inspector"]["status"], "wired and passing")
        self.assertEqual(stages["inspector"]["missing_evidence"], [])
        self.assertEqual(stages["inspector"]["defects"], [])
        self.assertEqual(stages["domain_switch"]["status"], "provisional")
        self.assertEqual(stages["domain_switch"]["resumes_previous_domain"], "unresolved")
        self.assertEqual(stages["domain_switch"]["sample_tag_count"], 0)
        self.assertGreater(report["open_gestalt_count"], 0)


if __name__ == "__main__":
    unittest.main()
