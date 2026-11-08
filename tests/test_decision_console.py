import copy, json, pathlib, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "console"))
from decision_console import *  # noqa
from decision_console.core import DecisionLog, DecisionError, project_owner_decisions, project_register_md, project_qson_events, sha256_hex

SYN = json.loads((ROOT / "console/fixtures/synthetic_catalog.json").read_text())
REAL = json.loads((ROOT / "console/fixtures/catalog.v1.json").read_text())
REAL_EVENTS = [json.loads(l) for l in (ROOT / "console/fixtures/events.v1.jsonl").read_text().splitlines() if l]
O, T = "owner-synthetic", "2026-01-01T00:00:00Z"


class T1(unittest.TestCase):
    def log(self): return DecisionLog.new(copy.deepcopy(SYN))

    def test_defaults_pending_no_events(self):
        l = self.log()
        self.assertEqual([l.state(d["id"]) for d in SYN["decisions"]], ["PENDING"] * 3)
        self.assertTrue(all(d["value"] is None for d in project_owner_decisions(l)["decisions"]))

    def test_bulk_one_event_per_decision_with_exceptions(self):
        l = self.log()
        ev = l.approve_all_recommended(owner=O, timestamp=T, exceptions=["S2"])
        self.assertEqual([e["decision_id"] for e in ev], ["S1", "S3"])
        self.assertTrue(all(e["bulk_exceptions"] == ["S2"] for e in ev))
        self.assertEqual(len({e["bulk_id"] for e in ev}), 1)
        self.assertEqual(l.state("S2"), "PENDING")

    def test_bulk_skips_non_pending(self):
        l = self.log(); l.record("S1", "REJECT", owner=O, timestamp=T)
        ev = l.approve_all_recommended(owner=O, timestamp=T)
        self.assertNotIn("S1", [e["decision_id"] for e in ev]); self.assertEqual(l.state("S1"), "REJECTED")

    def test_bulk_unknown_exception(self):
        with self.assertRaises(DecisionError): self.log().approve_all_recommended(owner=O, timestamp=T, exceptions=["ZZ"])

    def test_supersession_immutable(self):
        l = self.log(); a = l.record("S1", "APPROVE_RECOMMENDATION", owner=O, timestamp=T)
        snap = copy.deepcopy(a)
        b = l.record("S1", "CHOOSE_OTHER", value="blue", owner=O, timestamp=T)
        self.assertEqual(l.events[0], snap); self.assertEqual(b["supersedes"], a["event_id"])
        self.assertEqual(l.event_state(l.events[0]), "SUPERSEDED"); self.assertEqual(l.state("S1"), "APPROVED")
        hist = project_owner_decisions(l)["decisions"][0]["history"]
        self.assertEqual([h["state"] for h in hist], ["SUPERSEDED", "APPROVED"])

    def test_value_validation(self):
        l = self.log()
        for did, v in [("S1", "green"), ("S2", 5), ("S2", 12), ("S2", True), ("S3", "  ")]:
            with self.assertRaises(DecisionError): l.record(did, "CHOOSE_OTHER", value=v, owner=O, timestamp=T)
        self.assertEqual(l.events, [])

    def test_note_never_changes_value(self):
        l = self.log(); e = l.record("S1", "LEAVE_PENDING", note="maybe blue", owner=O, timestamp=T)
        self.assertIsNone(e["value"]); self.assertEqual(l.state("S1"), "PENDING")

    def test_owner_timestamp_required(self):
        with self.assertRaises(DecisionError): self.log().record("S1", "REJECT", owner="", timestamp=T)

    def test_tamper_detection(self):
        l = self.log(); l.approve_all_recommended(owner=O, timestamp=T)
        evs = copy.deepcopy(l.events)
        for mut in [lambda e: e[0].__setitem__("value", "blue"),
                    lambda e: e.reverse(),
                    lambda e: e.pop(0),
                    lambda e: e[1].__setitem__("prev_event_digest", None),
                    lambda e: e[0].__setitem__("state", "REJECTED"),
                    lambda e: e[0].__setitem__("extra", 1)]:
            bad = copy.deepcopy(evs); mut(bad)
            with self.assertRaises(DecisionError): DecisionLog.load(copy.deepcopy(SYN), bad)
        DecisionLog.load(copy.deepcopy(SYN), evs)

    def test_catalog_change_invalidates(self):
        l = self.log(); l.record("S1", "REJECT", owner=O, timestamp=T)
        c2 = copy.deepcopy(SYN); c2["decisions"][0]["recommended"] = "blue"
        with self.assertRaises(DecisionError): DecisionLog.load(c2, l.events)

    def test_forbidden_prompt_keys(self):
        l = self.log()
        with self.assertRaisesRegex(DecisionError, "forbidden key"):
            from decision_console.core import _reject_forbidden
            _reject_forbidden({"note": {"raw_prompt": "secret"}})
        e = l.record("S3", "CHOOSE_OTHER", value="x", owner=O, timestamp=T)
        bad = copy.deepcopy(e); bad["note"] = {"prompt": "secret"}
        with self.assertRaisesRegex(DecisionError, "forbidden key"):
            DecisionLog.load(copy.deepcopy(SYN), [bad])

    def test_determinism_and_digest_sensitivity(self):
        def build(ts):
            l = self.log(); l.approve_all_recommended(owner=O, timestamp=ts); return l
        a, b, c = build(T), build(T), build("2026-01-02T00:00:00Z")
        self.assertEqual(project_owner_decisions(a), project_owner_decisions(b))
        self.assertEqual(project_register_md(a), project_register_md(b))
        self.assertNotEqual(project_owner_decisions(a)["decision_set_digest"], project_owner_decisions(c)["decision_set_digest"])

    def test_blocked_modules_dependency(self):
        l = self.log(); l.record("S2", "APPROVE_RECOMMENDATION", owner=O, timestamp=T)
        self.assertEqual(l.blocked_builders()["MB"], ["S1"])
        l.record("S1", "APPROVE_RECOMMENDATION", owner=O, timestamp=T)
        self.assertNotIn("MB", l.blocked_builders())

    def test_qson_metadata_only(self):
        l = self.log(); l.record("S3", "CHOOSE_OTHER", value="x", note="n", rationale="r", owner=O, timestamp=T)
        q = project_qson_events(l)[0]
        for k in ("value", "note", "rationale"): self.assertNotIn(k, q)


class T2(unittest.TestCase):
    def test_real_catalog_fixture(self):
        l = DecisionLog.load(REAL, REAL_EVENTS)
        p = project_owner_decisions(l)
        st = {d["id"]: d["state"] for d in p["decisions"]}
        self.assertEqual(st.pop("D5"), "APPROVED")  # historical approval preserved
        self.assertTrue(all(s == "PENDING" for s in st.values()))  # nothing else approved
        self.assertIn("B7", p["blocked_modules"])
        self.assertNotIn("B5", p["blocked_modules"])

    def test_generated_outputs_match_committed(self):
        l = DecisionLog.load(REAL, REAL_EVENTS)
        out = ROOT / "console/out"
        self.assertEqual((out / "DECISION_REGISTER.generated.md").read_text("utf-8"), project_register_md(l))


if __name__ == "__main__":
    unittest.main()
