import hashlib
import unittest
from pathlib import Path

from nych_inventory.emoji_inventory import TEST_PATH, load_emoji, load_sources
from nych_smoke.tokenize import tokenize

ROOT = Path(__file__).resolve().parents[1]


class EmojiInventory(unittest.TestCase):
    def test_sources_are_recorded_and_not_approved(self):
        sources = load_sources()
        self.assertEqual(sources["status"], "owner-stated-not-approved")
        self.assertEqual(sources["version"], "12.0")
        self.assertEqual(sources["chart_url"], "https://unicode.org/emoji/charts-12.0/full-emoji-list.html")
        self.assertEqual(sources["emoji_test_url"], "https://unicode.org/Public/emoji/12.0/emoji-test.txt")
        self.assertEqual(sources["retrieved"], "2026-11-10")
        digest = hashlib.sha256(TEST_PATH.read_bytes()).hexdigest()
        self.assertEqual(digest, sources["files"]["emoji-test.txt"]["sha256"])
        self.assertEqual(sources["files"]["full-emoji-list.html"]["sha256"], "c186d6f012625f456fb433e68aca1cb3b42823dda49494ffa7f12c10d99dedf4")
        self.assertIn("skin-tone", " ".join(sources["discrepancies"]))
        questions = (ROOT / "icm/MG8PK/OWNER_QUESTIONS.md").read_text(encoding="utf-8")
        register = (ROOT / "icm/MG8PK/DECISION_REGISTER.md").read_text(encoding="utf-8")
        self.assertIn("not an approval", questions)
        self.assertIn("https://unicode.org/emoji/charts-12.0/full-emoji-list.html", register)
        self.assertIn("Owner-stated, not approved", register)

    def test_fully_qualified_count_and_known_rows(self):
        entries = load_emoji()
        self.assertEqual(len(entries), 3010)
        by_name = {entry.name: entry for entry in entries}
        grinning = by_name["grinning face"]
        self.assertEqual(grinning.codepoints, (0x1F600,))
        self.assertEqual(grinning.group, "Smileys & Emotion")
        self.assertEqual(grinning.subgroup, "face-smiling")
        heart = by_name["red heart"]
        self.assertEqual(heart.codepoints, (0x2764, 0xFE0F))
        wave = by_name["waving hand: light skin tone"]
        self.assertEqual(wave.codepoints, (0x1F44B, 0x1F3FB))
        self.assertNotIn("red hair", by_name)
        for entry in entries:
            self.assertFalse(hasattr(entry, "gestalt"))
            self.assertNotIn("nych", entry.name.lower())

    def test_tokenizer_keeps_a_fully_qualified_sequence_atomic(self):
        raw, tokens = tokenize("hi 😀❤️👋🏻")
        self.assertEqual(b"".join(raw[token.start:token.end] for token in tokens), raw)
        emoji = [token for token in tokens if token.kind == "emoji"]
        self.assertEqual([token.text for token in emoji], ["😀", "❤️", "👋🏻"])
        self.assertEqual(emoji[0].emoji_name, "grinning face")
        self.assertEqual(emoji[1].emoji_codepoints, (0x2764, 0xFE0F))
        self.assertEqual(emoji[2].emoji_name, "waving hand: light skin tone")
        bare, bare_tokens = tokenize("❤")
        self.assertEqual([token.kind for token in bare_tokens], ["punct"])
        self.assertEqual(bare.decode("utf-8"), "❤")


if __name__ == "__main__":
    unittest.main()
