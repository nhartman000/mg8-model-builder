import json
import unittest
from pathlib import Path

from nych_preview.domain_switch import (
    GLOBAL_TAG,
    DomainSwitchError,
    annotate_tokens,
    check_temporary_pair,
    domain_after_close,
    global_tag,
    parse_tag,
    temporary_close,
    temporary_open,
    temporary_span,
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

    def test_owner_stated_forms_and_fail_closed_questions(self):
        self.assertEqual(temporary_span(12), "dom>12")
        temporary = parse_tag("dom>12")
        self.assertEqual(temporary["status"], "owner-stated")
        self.assertFalse(temporary["interpreted"])
        self.assertEqual(temporary["placement"], "interlinear-where-it-occurs")
        self.assertEqual(temporary["count_direction"], "forward-from-this-point")
        self.assertIn("b", temporary["unresolved"])
        global_form = parse_tag("dom><global")
        self.assertEqual(global_form["status"], "owner-stated")
        self.assertIsNone(global_form["domain"])
        self.assertIn("c", global_form["unresolved"])
        opened = parse_tag("dom>x=food")
        closed = parse_tag("x=12")
        self.assertEqual(opened["status"], "interpreted")
        self.assertTrue(opened["interpreted"])
        self.assertEqual(closed["placement"], "unresolved")
        self.assertEqual(closed["count_direction"], "unresolved")
        self.assertEqual(domain_after_close()["resumes_previous_domain"], "unresolved")
        for text in ("(dom>12)", "(dom><global)", "(dom>x=food)", "dom><global=food", "dom><12", "dom>0"):
            with self.subTest(text=text):
                with self.assertRaises(DomainSwitchError):
                    parse_tag(text)
        overlapped = annotate_tokens(["dom>x=food", "dom>z=food", "x=12"])
        self.assertIn("d", overlapped["unresolved"])
        self.assertEqual(overlapped["resumes_previous_domain"], "unresolved")
        self.assertFalse(overlapped["authorizes_domain"])
        windows = annotate_tokens(["dom>2", "dom>2"])
        self.assertIn("overlap", windows["unresolved"])
        parenthesized = annotate_tokens(["(dom>12)"])
        self.assertIn("parentheses", parenthesized["unresolved"])
        sequential = annotate_tokens(["dom>1", "dom><global"])
        self.assertEqual([tag["status"] for tag in sequential["tags"]], ["owner-stated", "owner-stated"])


if __name__ == "__main__":
    unittest.main()
