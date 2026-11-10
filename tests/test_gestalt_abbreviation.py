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
        self.assertNotIn("eye", OVERRIDES)
        self.assertEqual(abbreviate_word("fried"), "fryd")
        self.assertEqual(abbreviate_word("died"), "dyd")
        self.assertEqual(abbreviate_word("eye"), "eye")
        self.assertEqual(abbreviate_word("the"), "the")
        self.assertEqual(abbreviate_word("he"), "he")
        self.assertEqual(
            abbreviate_compound(["fried", "apple"], contains_proper_name=False),
            "fryd'Ppl",
        )
        self.assertNotEqual(
            abbreviate_compound(["fried", "apple"], contains_proper_name=False),
            'fryd"ppl',
        )
        self.assertEqual(
            abbreviate_compound(["brick", "apple"], contains_proper_name=False),
            "brck'Ppl",
        )
        self.assertEqual(abbreviate_word("field"), 'f"ld')
        self.assertNotEqual(abbreviate_word("field"), "fld")
        self.assertEqual(abbreviate_word("piece"), 'p"c')
        self.assertNotIn("friend", OVERRIDES)
        self.assertNotIn("science", OVERRIDES)

    def test_open_edges_are_refused(self):
        cases = (
            (["Fibonacci"], True),
            (["apple", "tree"], False),
            (["Ae", "Io"], False),
            (["brick", "layer", "wall"], False),
            (["brick-layer", "course"], False),
        )
        for word in ("yellow",):
            with self.subTest(word=word):
                with self.assertRaises(GestaltAbbrevError):
                    abbreviate_word(word)
        self.assertEqual(
            abbreviate_compound(["hot", "dog"], contains_proper_name=False),
            "htDg",
        )
        for words, named in cases:
            with self.subTest(words=words):
                with self.assertRaises(GestaltAbbrevError):
                    abbreviate_compound(words, contains_proper_name=named)

    def test_owner_compound_list_does_not_guess_pairs(self):
        from nych_preview.gestalt_abbreviation import COMPOUNDS, abbreviate_owner_compound, render_phrase
        self.assertEqual(
            abbreviate_owner_compound(["hot", "dog"], contains_proper_name=False),
            "htDg",
        )
        self.assertEqual(
            abbreviate_owner_compound(["Fibonacci", "sequence"], contains_proper_name=True),
            "FbncSqnc",
        )
        self.assertEqual(
            abbreviate_owner_compound(["fried", "apple"], contains_proper_name=False),
            "fryd'Ppl",
        )
        self.assertEqual(COMPOUNDS[("hot", "dog")]["status"], "owner-stated-under-criterion")
        self.assertEqual(COMPOUNDS[("brick", "layer")]["status"], "given-before-criterion")
        self.assertNotIn(("red", "car"), COMPOUNDS)
        self.assertEqual(render_phrase(["hot", "dog"], as_compound=False), "hot dog")
        self.assertEqual(render_phrase(["hot", "dog"], as_compound=True), "htDg")
        self.assertEqual(render_phrase(["red", "car"], as_compound=False), "red car")


if __name__ == "__main__":
    unittest.main()
