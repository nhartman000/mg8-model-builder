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
        for word in ("Zanzibar", "NASA"):
            self.assertEqual(rows[word]["verdict"], "undecided")
            self.assertFalse(rows[word]["approved"])
            self.assertIn("dictionary-unknown", rows[word]["flags"])
            self.assertIn("sentence-initial", rows[word]["flags"])
        self.assertIn("all-caps", rows["NASA"]["flags"])
        self.assertNotIn("all-caps", rows["Rose"]["flags"])

    def test_sentence_initial_common_word_is_not_decided(self):
        rows = {row["text"]: row for row in classify_names("Bill met Apple at the start. I saw NASA.")}
        self.assertEqual(rows["Bill"]["verdict"], "undecided")
        self.assertIn("sentence-initial", rows["Bill"]["flags"])
        self.assertEqual(rows["Bill"]["surface_form"], "Bill")
        apple = rows["Apple"]
        self.assertEqual(apple["verdict"], "name")
        self.assertTrue(apple["interpreted"])
        self.assertEqual(apple["surface_form"], "Apple")
        self.assertEqual(rows["NASA"]["verdict"], "undecided")
        self.assertIn("all-caps", rows["NASA"]["flags"])
        self.assertNotIn("sentence-initial", rows["NASA"]["flags"])


if __name__ == "__main__":
    unittest.main()
