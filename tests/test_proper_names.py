import unittest

from nych_smoke.proper_names import classify_names


class ProvisionalProperNames(unittest.TestCase):
    def test_mid_sentence_capital_is_an_interpreted_name(self):
        rows = {row["text"]: row for row in classify_names("Zanzibar asked Rose. NASA stayed.")}
        self.assertEqual(rows["asked"]["verdict"], "not-capitalized")
        self.assertEqual(rows["stayed"]["verdict"], "not-capitalized")
        rose = rows["Rose"]
        self.assertEqual(rose["verdict"], "name")
        self.assertTrue(rose["interpreted"])
        self.assertFalse(rose["approved"])
        self.assertEqual(rose["surface_form"], "Rose")
        self.assertEqual(rose["flags"], ["mid-sentence-capital"])
        self.assertEqual(rows["Zanzibar"]["verdict"], "undecided")
        self.assertIn("sentence-initial", rows["Zanzibar"]["flags"])
        self.assertIn("dictionary-unknown", rows["Zanzibar"]["flags"])
        nasa = rows["NASA"]
        self.assertEqual(nasa["verdict"], "acronym")
        self.assertTrue(nasa["interpreted"])
        self.assertFalse(nasa["approved"])
        self.assertEqual(nasa["surface_form"], "NASA")
        self.assertEqual(nasa["gestalt"], "excluded")
        self.assertEqual(nasa["flags"], ["all-caps"])

    def test_sentence_initial_common_word_is_not_decided(self):
        rows = {row["text"]: row for row in classify_names("Bill met Apple at the start. I saw NASA.")}
        self.assertEqual(rows["Bill"]["verdict"], "undecided")
        self.assertIn("sentence-initial", rows["Bill"]["flags"])
        self.assertEqual(rows["Bill"]["surface_form"], "Bill")
        apple = rows["Apple"]
        self.assertEqual(apple["verdict"], "name")
        self.assertTrue(apple["interpreted"])
        self.assertEqual(apple["surface_form"], "Apple")
        nasa = rows["NASA"]
        self.assertEqual(nasa["verdict"], "acronym")
        self.assertEqual(nasa["gestalt"], "excluded")
        self.assertEqual(nasa["surface_form"], "NASA")
        self.assertNotIn("sentence-initial", nasa["flags"])

    def test_acronym_is_not_gestalted(self):
        from nych_smoke.pipeline import run_text

        report = run_text("NASA stayed")
        nasa = next(row for row in report["gestalts"] if row["surface"] == ["NASA"])
        self.assertEqual(nasa["status"], "acronym-excluded")
        self.assertIsNone(nasa["abbrev"])
        stayed = next(row for row in report["gestalts"] if row["surface"] == ["stayed"])
        self.assertEqual(stayed["status"], "abbreviated")


if __name__ == "__main__":
    unittest.main()
