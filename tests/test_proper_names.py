import unittest

from nych_smoke.proper_names import classify_names


class ProvisionalProperNames(unittest.TestCase):
    def test_mid_sentence_capital_is_an_interpreted_name(self):
        rows = {row["text"]: row for row in classify_names("Qwxzq asked Rose. NASA stayed.")}
        self.assertEqual(rows["asked"]["verdict"], "not-capitalized")
        self.assertEqual(rows["stayed"]["verdict"], "not-capitalized")
        rose = rows["Rose"]
        self.assertEqual(rose["verdict"], "name")
        self.assertTrue(rose["interpreted"])
        self.assertFalse(rose["approved"])
        self.assertEqual(rose["surface_form"], "Rose")
        self.assertEqual(rose["flags"], ["mid-sentence-capital"])
        missing = rows["Qwxzq"]
        self.assertEqual(missing["verdict"], "name")
        self.assertTrue(missing["interpreted"])
        self.assertEqual(missing["surface_form"], "Qwxzq")
        self.assertIn("sentence-initial", missing["flags"])
        self.assertIn("not-in-substitute-dictionary", missing["flags"])
        nasa = rows["NASA"]
        self.assertEqual(nasa["verdict"], "acronym")
        self.assertTrue(nasa["interpreted"])
        self.assertFalse(nasa["approved"])
        self.assertEqual(nasa["surface_form"], "NASA")
        self.assertEqual(nasa["gestalt"], "excluded")
        self.assertEqual(nasa["flags"], ["all-caps"])

    def test_sentence_initial_dictionary_word_is_ordinary(self):
        rows = {row["text"]: row for row in classify_names("Bill met Apple at the start. I saw NASA.")}
        bill = rows["Bill"]
        self.assertEqual(bill["verdict"], "ordinary")
        self.assertFalse(bill["interpreted"])
        self.assertIn("sentence-initial", bill["flags"])
        self.assertIn("in-substitute-dictionary", bill["flags"])
        apple = rows["Apple"]
        self.assertEqual(apple["verdict"], "name")
        self.assertTrue(apple["interpreted"])
        self.assertEqual(apple["surface_form"], "Apple")
        nasa = rows["NASA"]
        self.assertEqual(nasa["verdict"], "acronym")
        self.assertEqual(nasa["gestalt"], "excluded")
        self.assertEqual(nasa["surface_form"], "NASA")
        self.assertNotIn("sentence-initial", nasa["flags"])

    def test_crossword_only_word_counts_when_supplied(self):
        rows = {row["text"]: row for row in classify_names("Zzzyx stayed.", dictionary={"zzzyx"})}
        self.assertEqual(rows["Zzzyx"]["verdict"], "ordinary")
        self.assertIn("in-substitute-dictionary", rows["Zzzyx"]["flags"])

    def test_acronym_is_not_gestalted(self):
        from nych_smoke.pipeline import run_text

        report = run_text(
            b"NASA stayed",
            request_id="proper-name-test",
            received_at="2026-01-01T00:00:00Z",
        )
        nasa = next(row for row in report["gestalts"] if row["surface"] == ["NASA"])
        self.assertEqual(nasa["status"], "acronym-excluded")
        self.assertIsNone(nasa["abbrev"])
        stayed = next(row for row in report["gestalts"] if row["surface"] == ["stayed"])
        self.assertEqual(stayed["status"], "abbreviated")


if __name__ == "__main__":
    unittest.main()
