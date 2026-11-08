import copy, json, pathlib, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "console"))
from decision_console.core import (DecisionLog, DecisionError, project_owner_decisions, project_register_md,
                                   project_qson_events, sha256_hex, md_escape, MODULE_UNIVERSE, validate_catalog)

SYN = json.loads((ROOT / "console/fixtures/synthetic_catalog.json").read_text())
REAL = json.loads((ROOT / "console/fixtures/catalog.v2.json").read_text())
REAL_EVENTS = [json.loads(l) for l in (ROOT / "console/fixtures/events.v2.jsonl").read_text().splitlines() if l]
O, T = "owner-synthetic", "2026-01-01T00:00:00Z"
INCOMPLETE_REAL = {"D4", "D6", "D11", "D13", "D14", "D15", "D16"}


def rehash(e):
    e = dict(e); e.pop("event_id", None); return dict(e, event_id=sha256_hex(e))


class Core(unittest.TestCase):
    def log(self): return DecisionLog.new(copy.deepcopy(SYN))

    def test_defaults_pending(self):
        l = self.log()
        self.assertTrue(all(l.state(d["id"]) == "PENDING" for d in SYN["decisions"]))
        self.assertTrue(all(d["value"] is None for d in project_owner_decisions(l)["decisions"]))

    def test_bulk_skips_incomplete_and_exceptions(self):
        l = self.log()
        r = l.approve_all_recommended(owner=O, timestamp=T, exceptions=["S2"])
        self.assertEqual([e["decision_id"] for e in r["events"]], ["S1", "S4"])  # SH (historical) excluded
        self.assertEqual(r["skipped_incomplete"], ["S3"])
        for e in r["events"]:
            self.assertEqual(e["bulk_exceptions"], ["S2"]); self.assertEqual(e["bulk_skipped_incomplete"], ["S3"])
        self.assertEqual(l.state("S2"), "PENDING"); self.assertEqual(l.state("S3"), "PENDING")

    def test_cannot_approve_incomplete_recommendation(self):
        l = self.log()
        with self.assertRaises(DecisionError): l.record("S3", "APPROVE_RECOMMENDATION", owner=O, timestamp=T)
        e = rehash({"schema": "mg8.decision-event.v1", "seq": 0, "decision_id": "S3", "action": "APPROVE_RECOMMENDATION",
                    "state": "APPROVED", "value": {"known": "x", "open": "guess"}, "owner": O, "timestamp": T, "rationale": "",
                    "note": "", "supersedes": None, "bulk_id": None, "bulk_exceptions": [], "bulk_skipped_incomplete": [],
                    "catalog_digest": sha256_hex(SYN), "prev_event_digest": None})
        with self.assertRaises(DecisionError): DecisionLog.load(copy.deepcopy(SYN), [e])

    def test_explicit_owner_choice_can_complete(self):
        l = self.log(); l.record("S3", "CHOOSE_OTHER", value={"known": "x", "open": "owner says z"}, owner=O, timestamp=T)
        self.assertEqual(l.state("S3"), "APPROVED")

    def test_product_constraint(self):
        l = self.log()
        with self.assertRaises(DecisionError): l.record("S2", "CHOOSE_OTHER", value={"a": 4, "b": 32, "w": 100}, owner=O, timestamp=T)
        l.record("S2", "CHOOSE_OTHER", value={"a": 2, "b": 64, "w": 128}, owner=O, timestamp=T)

    def test_real_d8_constraint(self):
        d8 = [d for d in REAL["decisions"] if d["id"] == "D8"][0]
        self.assertEqual(d8["constraints"][0]["target"], "model_width")
        l = DecisionLog.load(copy.deepcopy(REAL), REAL_EVENTS)
        bad = dict(heads=4, head_width=32, model_width=96, layers=2, mask="causal", kv_cache="none_in_reference")
        with self.assertRaises(DecisionError): l.record("D8", "CHOOSE_OTHER", value=bad, owner=O, timestamp=T)

    def test_catalog_rejects_guessed_owner_value(self):
        c = copy.deepcopy(SYN); c["decisions"][2]["contract"]["open"]["recommended"] = "guess"
        with self.assertRaises(DecisionError): validate_catalog(c)

    def test_value_validation(self):
        l = self.log()
        for did, v in [("S1", {"colour": "green"}), ("S1", "red"), ("S1", {"colour": "red", "x": 1}), ("S1", {}),
                       ("S2", {"a": True, "b": 32, "w": 32}), ("S2", {"a": 4.0, "b": 32, "w": 128}), ("S2", {"a": 0, "b": 32, "w": 0}),
                       ("S3", {"known": "  ", "open": "z"})]:
            with self.assertRaises(DecisionError, msg=(did, v)): l.record(did, "CHOOSE_OTHER", value=v, owner=O, timestamp=T)
        self.assertEqual(l.events, [])

    def test_type_validation_record(self):
        l = self.log()
        for kw in [dict(owner={"x": 1}), dict(owner=""), dict(timestamp=5), dict(timestamp="yesterday"),
                   dict(note={"a": 1}), dict(rationale=["r"]), dict(note="x" * 5000)]:
            args = dict(owner=O, timestamp=T); args.update(kw)
            with self.assertRaises(DecisionError, msg=kw): l.record("S1", "REJECT", **args)
        with self.assertRaises(DecisionError): l.record("S1", "REJECT", owner=O, timestamp=T, value={"colour": "red"})
        with self.assertRaises(DecisionError): l.record("S1", "NOPE", owner=O, timestamp=T)
        self.assertEqual(l.events, [])

    def test_type_validation_load(self):
        l = self.log(); good = l.record("S1", "REJECT", owner=O, timestamp=T)
        for k, v in [("owner", {"x": 1}), ("timestamp", 1), ("note", {"a": 1}), ("rationale", ["r"]), ("seq", "0"),
                     ("seq", True), ("bulk_exceptions", "S2"), ("bulk_exceptions", ["S2"]), ("supersedes", "abc")]:
            bad = rehash(dict(good, **{k: v}))
            with self.assertRaises(DecisionError, msg=k): DecisionLog.load(copy.deepcopy(SYN), [bad])

    def test_supersession_immutable(self):
        l = self.log(); a = l.record("S1", "APPROVE_RECOMMENDATION", owner=O, timestamp=T)
        b = l.record("S1", "CHOOSE_OTHER", value={"colour": "blue"}, owner=O, timestamp=T)
        self.assertEqual(l.events[0], a); self.assertEqual(b["supersedes"], a["event_id"])
        self.assertEqual(l.event_state(a["event_id"]), "SUPERSEDED")
        hist = project_owner_decisions(l)["decisions"][0]["history"]
        self.assertEqual([h["state"] for h in hist], ["SUPERSEDED", "APPROVED"])

    def test_encapsulation(self):
        l = self.log(); e = l.record("S1", "APPROVE_RECOMMENDATION", owner=O, timestamp=T)
        before = project_owner_decisions(l)
        e["value"]["colour"] = "blue"
        l.events[0]["value"]["colour"] = "blue"
        l.catalog["decisions"][0]["title"] = "hacked"
        l.catalogs[0]["decisions"].clear()
        with self.assertRaises(AttributeError): l.events = []
        self.assertEqual(project_owner_decisions(l), before)
        src = copy.deepcopy(SYN); l2 = DecisionLog.new(src); src["decisions"].clear()
        self.assertEqual(len(l2.catalog["decisions"]), 5)

    def test_private_state_tamper_caught_on_export(self):
        l = self.log(); l.record("S1", "APPROVE_RECOMMENDATION", owner=O, timestamp=T)
        l._DecisionLog__events[0]["value"] = {"colour": "blue"}
        with self.assertRaises(DecisionError): project_owner_decisions(l)

    def test_tamper_detection(self):
        l = self.log(); l.approve_all_recommended(owner=O, timestamp=T)
        evs = l.events
        for mut in [lambda e: e[0].__setitem__("value", {"colour": "blue"}), lambda e: e.reverse(), lambda e: e.pop(0),
                    lambda e: e[1].__setitem__("prev_event_digest", None), lambda e: e[0].__setitem__("state", "REJECTED"),
                    lambda e: e[0].__setitem__("extra", 1)]:
            bad = copy.deepcopy(evs); mut(bad)
            with self.assertRaises(DecisionError): DecisionLog.load(copy.deepcopy(SYN), bad)
        DecisionLog.load(copy.deepcopy(SYN), evs)

    def test_truncation_needs_external_head(self):
        l = self.log(); l.approve_all_recommended(owner=O, timestamp=T)
        evs, head = l.events, l.head()
        DecisionLog.load(copy.deepcopy(SYN), evs[:-1])  # undetectable without trusted head (documented)
        with self.assertRaises(DecisionError): DecisionLog.load(copy.deepcopy(SYN), evs[:-1], expected_head=head)
        with self.assertRaises(DecisionError): DecisionLog.load(copy.deepcopy(SYN), evs[:-1], expected_count=len(evs))
        DecisionLog.load(copy.deepcopy(SYN), evs, expected_head=head, expected_count=len(evs))

    def test_historical_minting_blocked(self):
        l = self.log()
        with self.assertRaises(DecisionError): l.record("S1", "HISTORICAL_APPROVAL", owner=O, timestamp=T, value={"colour": "red"})
        with self.assertRaises(DecisionError): l.import_historical("S1", timestamp=T, rationale="r")  # not declared
        l.import_historical("SH", timestamp=T, rationale="r")
        with self.assertRaises(DecisionError): l.import_historical("SH", timestamp=T, rationale="r")  # only once
        forged = rehash({"schema": "mg8.decision-event.v1", "seq": 0, "decision_id": "S1", "action": "HISTORICAL_APPROVAL",
                         "state": "APPROVED", "value": {"colour": "blue"}, "owner": O, "timestamp": T, "rationale": "", "note": "",
                         "supersedes": None, "bulk_id": None, "bulk_exceptions": [], "bulk_skipped_incomplete": [],
                         "catalog_digest": sha256_hex(SYN), "prev_event_digest": None})
        with self.assertRaises(DecisionError): DecisionLog.load(copy.deepcopy(SYN), [forged])

    def test_catalog_snapshots(self):
        l = self.log(); l.record("S1", "APPROVE_RECOMMENDATION", owner=O, timestamp=T)
        c2 = copy.deepcopy(SYN); c2["catalog_version"] = "synthetic-2"; c2["decisions"][0]["contract"]["colour"]["options"].append("green")
        with self.assertRaises(DecisionError): DecisionLog.load(c2, l.events)  # history not silently reinterpreted
        l2 = DecisionLog.load([copy.deepcopy(SYN), c2], l.events)
        p = {d["id"]: d for d in project_owner_decisions(l2)["decisions"]}
        self.assertEqual(p["S1"]["state"], "APPROVED"); self.assertFalse(p["S1"]["recorded_against_current_definition"])
        self.assertIn("S1", l2.readiness()["blocked"]["B7"])  # changed definition must be reconfirmed
        self.assertEqual(l2.events, l.events)
        l2.record("S1", "APPROVE_RECOMMENDATION", owner=O, timestamp=T)
        self.assertEqual(l2.events[-1]["catalog_digest"], sha256_hex(c2))
        with self.assertRaises(DecisionError): DecisionLog.load([c2, copy.deepcopy(SYN)], l2.events)  # backwards

    def test_forbidden_keys_tripwire(self):
        l = self.log()
        with self.assertRaisesRegex(DecisionError, "forbidden key"):
            l.record("S3", "CHOOSE_OTHER", value={"known": "x", "open": "z", "prompt": "p"}, owner=O, timestamp=T)
        c = copy.deepcopy(SYN); c["decisions"][0]["prompt"] = "p"
        with self.assertRaises(DecisionError): validate_catalog(c)

    def test_determinism_and_digest_sensitivity(self):
        def build(ts):
            l = self.log(); l.approve_all_recommended(owner=O, timestamp=ts); return l
        a, b, c = build(T), build(T), build("2026-01-02T00:00:00Z")
        self.assertEqual(project_owner_decisions(a), project_owner_decisions(b))
        self.assertEqual(project_register_md(a), project_register_md(b))
        self.assertNotEqual(project_owner_decisions(a)["decision_set_digest"], project_owner_decisions(c)["decision_set_digest"])

    def test_readiness_conservative(self):
        l = self.log()
        r = l.readiness()
        self.assertFalse(r["readiness_authoritative"])
        self.assertEqual(set(r["blocked"]) | set(r["unblocked_advisory"]), set(MODULE_UNIVERSE))
        for m in ("B1", "B2", "B3"):
            self.assertIn("CONTRACT_NOT_MODELED_IN_CONSOLE", r["blocked"][m])
        for m in MODULE_UNIVERSE:
            self.assertIn("S4", r["blocked"][m])  # ALL is global
        l.approve_all_recommended(owner=O, timestamp=T); l.import_historical("SH", timestamp=T, rationale="r")
        r = l.readiness()
        self.assertIn("S3", r["blocked"]["B9"])  # incomplete stays blocking
        self.assertIn("B7", r["unblocked_advisory"]); self.assertIn("B8", r["unblocked_advisory"])
        self.assertIn("B1", r["blocked"])

    def test_dependency_blocking(self):
        l = self.log(); l.record("S4", "APPROVE_RECOMMENDATION", owner=O, timestamp=T)
        l.record("S2", "APPROVE_RECOMMENDATION", owner=O, timestamp=T)
        self.assertEqual(l.readiness()["blocked"]["B8"], ["S1"])

    def test_qson_metadata_only(self):
        l = self.log(); l.record("S1", "APPROVE_RECOMMENDATION", note="n", rationale="r", owner=O, timestamp=T)
        q = project_qson_events(l)[0]
        for k in ("value", "note", "rationale"): self.assertNotIn(k, q)

    def test_markdown_escaping(self):
        self.assertEqual(md_escape("a|b\nc`d"), "a\\|b c\\`d")
        l = self.log(); l.record("S3", "CHOOSE_OTHER", value={"known": "x", "open": "p|q\n| X | APPROVED |"}, owner=O, timestamp=T)
        md = project_register_md(l)
        row = [x for x in md.splitlines() if x.startswith("| S3 ")][0]
        self.assertNotIn("\n| X", md)
        self.assertEqual(row.replace("\\|", "").count("|"), 8)


class RealFixture(unittest.TestCase):
    def test_only_d5_approved(self):
        l = DecisionLog.load(copy.deepcopy(REAL), REAL_EVENTS)
        st = {d["id"]: d for d in project_owner_decisions(l)["decisions"]}
        self.assertEqual(st.pop("D5")["state"], "APPROVED")
        self.assertTrue(all(d["state"] == "PENDING" for d in st.values()))
        self.assertEqual({k for k, d in st.items() if not d["contract_complete"]}, INCOMPLETE_REAL)

    def test_bulk_on_real_never_approves_placeholders_or_unblocks_all(self):
        l = DecisionLog.load(copy.deepcopy(REAL), REAL_EVENTS)
        r = l.approve_all_recommended(owner=O, timestamp=T)
        self.assertEqual(set(r["skipped_incomplete"]), INCOMPLETE_REAL)
        for d in INCOMPLETE_REAL: self.assertEqual(l.state(d), "PENDING")
        rd = l.readiness()
        self.assertFalse(rd["readiness_authoritative"])
        for m in ("B1", "B2", "B3", "B4", "B6", "B7", "B11", "INTEGRATION"): self.assertIn(m, rd["blocked"])

    def test_generated_outputs_match_committed(self):
        l = DecisionLog.load(copy.deepcopy(REAL), REAL_EVENTS)
        out = ROOT / "console/out"
        self.assertEqual((out / "DECISION_REGISTER.generated.md").read_text("utf-8"), project_register_md(l))
        self.assertEqual(json.loads((out / "owner-decisions.v1.json").read_text("utf-8")), project_owner_decisions(l))


if __name__ == "__main__":
    unittest.main()
