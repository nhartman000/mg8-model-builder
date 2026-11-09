import unittest

from nych_preview.gestalt_abbreviation import GestaltAbbrevError, abbreviate_compound, abbreviate_word


class GestaltAbbreviationPreview(unittest.TestCase):
    def test_three_owner_examples(self):
        self.assertEqual(
            abbreviate_compound(["Fibonacci", "sequence"], contains_proper_name=True),
            "FbncSqnc",
        )
        brick = abbreviate_compound(["brick", "layer"], contains_proper_name=False)
        self.assertEqual(brick, "brckLyr")
        self.assertNotEqual(brick, "brkLyr")
        self.assertEqual(
            abbreviate_compound(["computer", "programmer"], contains_proper_name=False),
            "cmptrPrgrmr",
        )

    def test_vowel_initial_words(self):
        self.assertEqual(abbreviate_word("apple"), "'ppl")
        self.assertEqual(abbreviate_word("opal"), "'pl")

    def test_ie_becomes_y_by_default(self):
        from nych_preview.gestalt_abbreviation import OVERRIDES
        self.assertNotIn("fried", OVERRIDES)
        self.assertEqual(OVERRIDES["eye"], "'y")
        self.assertEqual(abbreviate_word("fried"), "fryd")
        self.assertEqual(abbreviate_word("died"), "dyd")
        self.assertEqual(abbreviate_word("eye"), "'y")
        self.assertEqual(
            abbreviate_compound(["fried", "apple"], contains_proper_name=False),
            'fryd"ppl',
        )
        self.assertEqual(
            abbreviate_compound(["brick", "apple"], contains_proper_name=False),
            'brck"ppl',
        )
        self.assertNotEqual(
            abbreviate_compound(["fried", "apple"], contains_proper_name=False),
            'frd"ppl',
        )

    def test_open_edges_are_refused(self):
        cases = (
            (["Fibonacci"], True),
            (["apple", "tree"], False),
            (["Ae", "Io"], False),
            (["brick", "layer", "wall"], False),
            (["brick-layer", "course"], False),
        )
        for word in ("yellow", "a", "Io"):
            with self.subTest(word=word):
                with self.assertRaises(GestaltAbbrevError):
                    abbreviate_word(word)
        for words, named in cases:
            with self.subTest(words=words):
                with self.assertRaises(GestaltAbbrevError):
                    abbreviate_compound(words, contains_proper_name=named)


if __name__ == "__main__":
    unittest.main()
