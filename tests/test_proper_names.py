import unittest

from nych_smoke.proper_names import classify_names


class ProvisionalProperNames(unittest.TestCase):
    def test_lowercase_is_not_a_name_and_capitals_stay_open(self):
        rows = {row["text"]: row for row in classify_names("Zanzibar asked Rose. NASA stayed.")}
        self.assertEqual(rows["asked"]["verdict"], "not-capitalized")
        self.assertEqual(rows["stayed"]["verdict"], "not-capitalized")
        for word in ("Zanzibar", "Rose", "NASA"):
            self.assertEqual(rows[word]["verdict"], "undecided")
            self.assertFalse(rows[word]["approved"])
            self.assertIn("dictionary-unknown", rows[word]["flags"])
            self.assertIn("dictionary-word-case-open", rows[word]["flags"])
        self.assertIn("sentence-initial", rows["Zanzibar"]["flags"])
        self.assertIn("sentence-initial", rows["NASA"]["flags"])
        self.assertNotIn("sentence-initial", rows["Rose"]["flags"])
        self.assertIn("all-caps", rows["NASA"]["flags"])
        self.assertNotIn("all-caps", rows["Rose"]["flags"])
        self.assertNotIn("is_name", rows["Zanzibar"])

    def test_no_row_is_decided_as_a_name(self):
        for row in classify_names("Bill met Apple at the start. I saw NASA."):
            self.assertNotEqual(row["verdict"], "name")
            if row["text"] in {"Bill", "Apple", "NASA"}:
                self.assertEqual(row["verdict"], "undecided")


if __name__ == "__main__":
    unittest.main()
