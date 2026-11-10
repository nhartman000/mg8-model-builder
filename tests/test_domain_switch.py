import json
import unittest
from pathlib import Path

from nych_preview.domain_switch import (
    GLOBAL_TAG,
    DomainSwitchError,
    check_temporary_pair,
    global_tag,
    temporary_close,
    temporary_open,
)

ROOT = Path(__file__).resolve().parents[1]


class DomainSwitchPreview(unittest.TestCase):
    def test_interpreted_food_example(self):
        self.assertEqual(temporary_open("x", "food"), "dom>x=food")
        self.assertEqual(temporary_open("z", "food"), "dom>z=food")
        self.assertEqual(temporary_close("x", 12), "x=12")
        check_temporary_pair("dom>x=food", "x=12")
        self.assertEqual(global_tag(), "dom><global")
        self.assertEqual(GLOBAL_TAG, "dom><global")

    def test_fixture_is_marked_interpreted(self):
        fixtures = json.loads((ROOT / "nych_preview/fixtures/interlinear_examples.json").read_text())
        example = next(item for item in fixtures if item["id"] == "domain-switch-interpreted")
        self.assertEqual(example["status"], "interpreted-not-owner-confirmed")
        self.assertEqual(example["open"], "dom>x=food")
        self.assertEqual(example["close"], "x=12")
        self.assertEqual(example["global"], GLOBAL_TAG)
        self.assertEqual(fixtures[0]["id"], "full-sentence")
        check_temporary_pair(example["open"], example["close"])

    def test_open_questions_are_refused(self):
        with self.assertRaises(DomainSwitchError):
            check_temporary_pair("dom><global=food", "global=12")
        with self.assertRaises(DomainSwitchError):
            check_temporary_pair("dom>x=food", "z=12")
        with self.assertRaises(DomainSwitchError):
            temporary_open("X", "food")
        with self.assertRaises(DomainSwitchError):
            temporary_close("x", True)
        with self.assertRaises(DomainSwitchError):
            temporary_close("x", 0)


if __name__ == "__main__":
    unittest.main()
