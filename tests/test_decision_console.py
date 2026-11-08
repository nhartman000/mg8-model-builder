import copy, json, pathlib, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "console"))
from decision_console.core import (DecisionLog, DecisionError, project_owner_decisions, project_register_md,
                                   project_qson_events, sha256_hex, md_escape, MODULE_UNIVERSE, validate_catalog)

SYN = json.loads((ROOT / "console/fixtures/synthetic_catalog.json").read_text())
REAL = json.loads((ROOT / "console/fixtures/catalog.v2.json").read_text())
REAL3 = json.loads((ROOT / "console/fixtures/catalog.v3.json").read_text())
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
        l = DecisionLog.load([copy.deepcopy(REAL), copy.deepcopy(REAL3)], REAL_EVENTS)
        out = ROOT / "console/out"
        self.assertEqual((out / "DECISION_REGISTER.generated.md").read_text("utf-8"), project_register_md(l))
        self.assertEqual(json.loads((out / "owner-decisions.v1.json").read_text("utf-8")), project_owner_decisions(l))
        qson = "".join(json.dumps(q, sort_keys=True) + "\n" for q in project_qson_events(l))
        self.assertEqual((out / "qson-decision-events.jsonl").read_text("utf-8"), qson)


D5_EVENT = "sha256:68384464cd519cb5d360b28ecd3f4d150a6d7e794fa3095f94489386726276aa"
D5_V2_DIGEST = "sha256:b14b97c7ee8be12cdaad05be1db3dcc0555ef5d557f05c32fb0168608aade330"
D5_ADDED = {
    "gst_scope": "request-scoped",
    "gst_schema_path": "nych-language-model/schemas/gst-context-v1.schema.json",
    "gst_source_of_truth": "nych-language-model/src/nych_language_model/pipeline/gst_context.py",
    "existing_db_migration_002": "deferred; not applied to an existing database",
    "migration_002_conformance_tests": "deferred; not run",
}


def _bounds_of(cat):
    out = {}
    for d in cat["decisions"]:
        for name, f in d["contract"].items():
            if f["kind"] in ("integer", "number"):
                out[(d["id"], name)] = (f["minimum"], f["maximum"], f["step"])
    return out


def _rec(cat, did):
    d = next(x for x in cat["decisions"] if x["id"] == did)
    return {k: f["recommended"] for k, f in d["contract"].items()}


def _stack():
    return DecisionLog.load([copy.deepcopy(REAL), copy.deepcopy(REAL3)], REAL_EVENTS)


def _int_field(rec, minimum=0, maximum=None, step=1):
    return {"kind": "integer", "recommended": rec, "owner_input_required": False, "unit": None,
            "minimum": minimum, "maximum": maximum, "step": step}


def _pair(a=4, b=4, cross=True, **kw):
    cons = [{"kind": "equals", "left": {"decision": "A", "field": "n"},
             "right": {"decision": "B", "field": "n"}}] if cross else []
    def dec(did, rec, depends=()):
        return {"id": did, "title": did, "question": "q", "modules": ["B7"], "depends_on": list(depends),
                "round": "r", "contract": {"n": _int_field(rec, **kw)}, "constraints": [],
                "historical_approval": None, "sources": ["icm/MG8PK/DECISION_REGISTER.md"]}
    return {"schema": "mg8.decision-catalog.v3", "catalog_version": "t", "cross_constraints": cons,
            "decisions": [dec("A", a), dec("B", b, ("A",))]}


class CrossBoundsAndD5(unittest.TestCase):
    def test_catalog_v3_constraints_and_bounds_are_explicit(self):
        self.assertEqual(REAL3["schema"], "mg8.decision-catalog.v3")
        self.assertEqual(REAL3["cross_constraints"], [
            {"kind": "equals", "left": {"decision": "D1-context", "field": "window_tokens"},
             "right": {"decision": "D7", "field": "position_limit"}},
            {"kind": "equals", "left": {"decision": "D7", "field": "d_model"},
             "right": {"decision": "D8", "field": "model_width"}},
        ])
        self.assertEqual(_bounds_of(REAL3), {
            ("D1-context", "window_tokens"): (1, None, 1),
            ("D4", "confidence_threshold"): (0, 1, None),
            ("D5", "user_version"): (2, 2, 1),
            ("D7", "d_model"): (1, None, 1),
            ("D7", "position_limit"): (1, None, 1),
            ("D8", "layers"): (1, None, 1),
            ("D8", "heads"): (1, None, 1),
            ("D8", "head_width"): (1, None, 1),
            ("D8", "model_width"): (1, None, 1),
            ("D9", "ffn_hidden_width"): (1, None, 1),
            ("D9", "dropout_training"): (0, 1, None),
            ("D9", "dropout_inference"): (0, 1, None),
            ("D13", "max_bytes_exclusive"): (1, 500000, 1),
        })
        # user_version 2 and layers 2 are the same number with different meanings.
        dup = {}
        for d in REAL3["decisions"]:
            for name, f in d["contract"].items():
                if f["kind"] in ("integer", "number") and f["recommended"] is not None:
                    dup.setdefault(f["recommended"], []).append(f"{d['id']}.{name}")
        self.assertEqual(dup[2], ["D5.user_version", "D8.layers"])
        linked = {(c["left"]["field"], c["right"]["field"]) for c in REAL3["cross_constraints"]}
        self.assertNotIn(("user_version", "layers"), linked)

    def test_cross_and_bound_defs_rejected(self):
        with self.assertRaisesRegex(DecisionError, "recommendations"):
            validate_catalog(_pair(1, 2))
        validate_catalog(_pair(4, 4))
        validate_catalog(_pair(cross=False))
        with self.assertRaises(DecisionError):
            validate_catalog(_pair(3, 3, minimum=0, maximum=8, step=2))
        with self.assertRaises(DecisionError):
            validate_catalog(_pair(1, 1, minimum=5, maximum=1, step=1))
        c = _pair()
        del c["decisions"][0]["contract"]["n"]["step"]
        with self.assertRaises(DecisionError):
            validate_catalog(c)
        c = _pair()
        c["cross_constraints"][0]["right"]["field"] = "missing"
        with self.assertRaises(DecisionError):
            validate_catalog(c)
        c = _pair()
        c["cross_constraints"].append({"kind": "equals", "left": {"decision": "B", "field": "n"},
                                       "right": {"decision": "A", "field": "n"}})
        with self.assertRaisesRegex(DecisionError, "duplicate"):
            validate_catalog(c)
        c = _pair()
        c["cross_constraints"] = [{"kind": "equals", "left": {"decision": "A", "field": "n"},
                                   "right": {"decision": "A", "field": "n"}}]
        with self.assertRaises(DecisionError):
            validate_catalog(c)
        syn = copy.deepcopy(SYN)
        syn["decisions"][1]["contract"]["a"]["maximum"] = 10
        with self.assertRaises(DecisionError):
            validate_catalog(syn)

    def test_cross_decision_approvals_rejected(self):
        l = DecisionLog.new(_pair())
        l.record("A", "CHOOSE_OTHER", value={"n": 2}, owner=O, timestamp=T)
        with self.assertRaisesRegex(DecisionError, "cross-decision"):
            l.record("B", "APPROVE_RECOMMENDATION", owner=O, timestamp=T)
        self.assertEqual(l.state("B"), "PENDING")
        l.record("B", "CHOOSE_OTHER", value={"n": 2}, owner=O, timestamp=T)
        self.assertEqual(l.state("B"), "APPROVED")

        c = _pair(4, 4, minimum=0, maximum=8, step=2)
        l = DecisionLog.new(c)
        for bad in (3, 10, -2):
            with self.assertRaises(DecisionError):
                l.record("A", "CHOOSE_OTHER", value={"n": bad}, owner=O, timestamp=T)
        l.record("A", "CHOOSE_OTHER", value={"n": 6}, owner=O, timestamp=T)
        self.assertEqual(l.events[-1]["value"], {"n": 6})

        l = DecisionLog.new(_pair(1, 1, minimum=1, maximum=None, step=1))
        l.record("A", "CHOOSE_OTHER", value={"n": 10 ** 9}, owner=O, timestamp=T)
        with self.assertRaisesRegex(DecisionError, "cross-decision"):
            l.record("B", "APPROVE_RECOMMENDATION", owner=O, timestamp=T)

    def test_stale_peer_does_not_constrain_until_reconfirmed(self):
        a = _pair(1, 1)
        l = DecisionLog.new(a)
        l.record("A", "APPROVE_RECOMMENDATION", owner=O, timestamp=T)
        l.record("B", "APPROVE_RECOMMENDATION", owner=O, timestamp=T)
        b = _pair(2, 2)
        b["decisions"][0]["title"] = "A revised"
        b["decisions"][1]["title"] = "B revised"
        l2 = DecisionLog.load([a, b], l.events)
        l2.record("A", "CHOOSE_OTHER", value={"n": 5}, owner=O, timestamp=T)
        with self.assertRaisesRegex(DecisionError, "cross-decision"):
            l2.record("B", "CHOOSE_OTHER", value={"n": 6}, owner=O, timestamp=T)
        l2.record("B", "CHOOSE_OTHER", value={"n": 5}, owner=O, timestamp=T)

    def test_real_width_and_context_equalities(self):
        l = _stack()
        wide = _rec(REAL3, "D8")
        wide.update(heads=8, head_width=32, model_width=256)
        l.record("D8", "CHOOSE_OTHER", value=wide, owner=O, timestamp=T)  # D7 still pending
        with self.assertRaisesRegex(DecisionError, "cross-decision"):
            l.record("D7", "APPROVE_RECOMMENDATION", owner=O, timestamp=T)
        matched = _rec(REAL3, "D7")
        matched["d_model"] = 256
        l.record("D7", "CHOOSE_OTHER", value=matched, owner=O, timestamp=T)

        l = _stack()
        l.record("D7", "APPROVE_RECOMMENDATION", owner=O, timestamp=T)
        narrow = _rec(REAL3, "D8")
        narrow.update(heads=2, head_width=32, model_width=64)
        with self.assertRaisesRegex(DecisionError, "cross-decision"):
            l.record("D8", "CHOOSE_OTHER", value=narrow, owner=O, timestamp=T)
        broken = _rec(REAL3, "D8")
        broken["model_width"] = 100
        with self.assertRaises(DecisionError):
            l.record("D8", "CHOOSE_OTHER", value=broken, owner=O, timestamp=T)
        l.record("D8", "APPROVE_RECOMMENDATION", owner=O, timestamp=T)
        self.assertEqual(l.events[-1]["value"]["model_width"], 128)

        l = _stack()
        window = _rec(REAL3, "D1-context")
        window["window_tokens"] = 2048
        l.record("D1-context", "CHOOSE_OTHER", value=window, owner=O, timestamp=T)
        with self.assertRaisesRegex(DecisionError, "cross-decision"):
            l.record("D7", "APPROVE_RECOMMENDATION", owner=O, timestamp=T)
        pos = _rec(REAL3, "D7")
        pos["position_limit"] = 2048
        l.record("D7", "CHOOSE_OTHER", value=pos, owner=O, timestamp=T)
        self.assertEqual(l.events[-1]["value"]["position_limit"], 2048)

    def test_stack_bulk_keeps_recommendations_consistent(self):
        l = _stack()
        r = l.approve_all_recommended(owner=O, timestamp=T)
        self.assertEqual(set(r["skipped_incomplete"]), INCOMPLETE_REAL)
        self.assertNotIn("D5", [e["decision_id"] for e in r["events"]])
        self.assertEqual(l.events[0]["event_id"], D5_EVENT)
        vals = {e["decision_id"]: e["value"] for e in r["events"]}
        self.assertEqual(vals["D7"]["d_model"], vals["D8"]["model_width"])
        self.assertEqual(vals["D1-context"]["window_tokens"], vals["D7"]["position_limit"])
        self.assertFalse(l.readiness()["readiness_authoritative"])
        for did in INCOMPLETE_REAL:
            self.assertEqual(l.state(did), "PENDING")

    def test_bulk_conflict_writes_nothing(self):
        l = _stack()
        odd = _rec(REAL3, "D7")
        odd["d_model"] = 64
        l.record("D7", "CHOOSE_OTHER", value=odd, owner=O, timestamp=T)
        n = len(l.events)
        with self.assertRaisesRegex(DecisionError, "cross-decision"):
            l.approve_all_recommended(owner=O, timestamp=T)
        self.assertEqual(len(l.events), n)
        self.assertEqual(l.state("D0"), "PENDING")
        self.assertEqual(l.state("D8"), "PENDING")

    def test_real_numeric_bounds(self):
        l = _stack()
        d9 = _rec(REAL3, "D9")
        for bad in (1.1, -0.01):
            v = dict(d9, dropout_training=bad)
            with self.assertRaises(DecisionError):
                l.record("D9", "CHOOSE_OTHER", value=v, owner=O, timestamp=T)
        l.record("D9", "CHOOSE_OTHER", value=dict(d9, dropout_training=0.05, dropout_inference=1), owner=O, timestamp=T)
        huge = _rec(REAL3, "D7")
        huge["d_model"] = 10 ** 6  # no documented architecture cap; equality is the cross-check
        l.record("D7", "CHOOSE_OTHER", value=huge, owner=O, timestamp=T)
        with self.assertRaisesRegex(DecisionError, "cross-decision"):
            l.record("D8", "APPROVE_RECOMMENDATION", owner=O, timestamp=T)

        d4 = _rec(REAL3, "D4")
        self.assertIsNone(d4["confidence_threshold"])
        base = dict(d4, seed_lexicon="owner-seed", tie_policy="owner-tie")
        with self.assertRaises(DecisionError):
            l.record("D4", "CHOOSE_OTHER", value=dict(base, confidence_threshold=1.5), owner=O, timestamp=T)
        l.record("D4", "CHOOSE_OTHER", value=dict(base, confidence_threshold=0.25), owner=O, timestamp=T)

        d13 = _rec(REAL3, "D13")
        body = dict(d13, schema_validator_runtime="owner-validator")
        for bad in (0, 500001):
            with self.assertRaises(DecisionError):
                l.record("D13", "CHOOSE_OTHER", value=dict(body, max_bytes_exclusive=bad), owner=O, timestamp=T)
        l.record("D13", "CHOOSE_OTHER", value=dict(body, max_bytes_exclusive=500000), owner=O, timestamp=T)

        d5 = _rec(REAL3, "D5")
        before = l.events[0]
        for bad in (1, 3):
            with self.assertRaises(DecisionError):
                l.record("D5", "CHOOSE_OTHER", value=dict(d5, user_version=bad), owner=O, timestamp=T)
        self.assertEqual(l.events[0], before)

        d14 = next(d for d in REAL3["decisions"] if d["id"] == "D14")
        self.assertEqual(set(d14["contract"]), {"parameter_band", "memory_latency_target", "training_hardware"})
        for f in d14["contract"].values():
            self.assertEqual(f["kind"], "text")
            self.assertTrue(f["owner_input_required"])
            self.assertIsNone(f["recommended"])
            self.assertNotIn("minimum", f)
        fresh = _stack()
        for did in INCOMPLETE_REAL:
            with self.assertRaises(DecisionError):
                fresh.record(did, "APPROVE_RECOMMENDATION", owner=O, timestamp=T)
        self.assertEqual(len(fresh.events), 1)

    def test_d5_expansion_keeps_historical_event(self):
        self.assertEqual(REAL_EVENTS[0]["event_id"], D5_EVENT)
        self.assertEqual(REAL_EVENTS[0]["catalog_digest"], D5_V2_DIGEST)
        self.assertEqual(sha256_hex(REAL), D5_V2_DIGEST)
        self.assertNotEqual(sha256_hex(REAL3), D5_V2_DIGEST)
        self.assertEqual(len(REAL_EVENTS), 1)
        old = next(d for d in REAL["decisions"] if d["id"] == "D5")["historical_approval"]["value"]
        new = next(d for d in REAL3["decisions"] if d["id"] == "D5")
        self.assertIsNone(new["historical_approval"])
        rec = {k: f["recommended"] for k, f in new["contract"].items()}
        for k, v in old.items():
            self.assertEqual(rec[k], v)
        self.assertEqual({k: rec[k] for k in D5_ADDED}, D5_ADDED)

        l = _stack()
        self.assertEqual(l.events[0]["event_id"], D5_EVENT)
        self.assertEqual(l.events[0]["action"], "HISTORICAL_APPROVAL")
        self.assertEqual(l.events[0]["value"], old)
        p = {d["id"]: d for d in project_owner_decisions(l)["decisions"]}
        self.assertEqual(p["D5"]["state"], "APPROVED")
        self.assertFalse(p["D5"]["recorded_against_current_definition"])
        self.assertEqual(p["D5"]["value"], old)
        self.assertEqual(p["D5"]["recommended"], rec)
        self.assertTrue(all(d["state"] == "PENDING" and d["recorded_against_current_definition"]
                            for i, d in p.items() if i != "D5"))
        self.assertIn("D5", l.readiness()["blocked"]["B5"])
        self.assertFalse(l.readiness()["readiness_authoritative"])
        with self.assertRaises(DecisionError):
            l.import_historical("D5", timestamp=T, rationale="do not mint")
        self.assertEqual(len(l.events), 1)
        with self.assertRaises(DecisionError):
            DecisionLog.load(copy.deepcopy(REAL3), REAL_EVENTS)
        with self.assertRaises(DecisionError):
            DecisionLog.load([copy.deepcopy(REAL3), copy.deepcopy(REAL)], REAL_EVENTS)
        v2_only = DecisionLog.load(copy.deepcopy(REAL), REAL_EVENTS)
        d5 = {d["id"]: d for d in project_owner_decisions(v2_only)["decisions"]}["D5"]
        self.assertTrue(d5["recorded_against_current_definition"])
        self.assertEqual(d5["value"], d5["recommended"])

        md = project_register_md(_stack())
        d5row = [x for x in md.splitlines() if x.startswith("| D5 ")][0]
        self.assertIn("definition changed; reconfirm", d5row)
        self.assertIn("D1-context.window_tokens = D7.position_limit", md)
        self.assertIn("D7.d_model = D8.model_width", md)
        for row in md.splitlines():
            if row.startswith("| D") and not row.startswith("| D5 "):
                self.assertNotIn("definition changed", row)
        qson = json.dumps(project_qson_events(_stack()))
        for secret in ("request-scoped", "gst_context.py", "gst-context-v1", "deferred"):
            self.assertNotIn(secret, qson)

        # Owner reconfirm is a new event. The historical event stays event 0.
        l = _stack()
        first = copy.deepcopy(l.events[0])
        e = l.record("D5", "APPROVE_RECOMMENDATION", owner=O, timestamp=T)
        self.assertEqual(l.events[0], first)
        self.assertEqual(e["supersedes"], first["event_id"])
        self.assertEqual(e["action"], "APPROVE_RECOMMENDATION")
        self.assertEqual(e["catalog_digest"], sha256_hex(REAL3))
        self.assertNotEqual(e["value"], first["value"])
        self.assertEqual(e["value"]["gst_scope"], "request-scoped")
        self.assertEqual(e["value"]["user_version"], 2)
        after = {d["id"]: d for d in project_owner_decisions(l)["decisions"]}["D5"]
        self.assertTrue(after["recorded_against_current_definition"])
        self.assertEqual(len(REAL_EVENTS), 1)  # fixture log was not rewritten


if __name__ == "__main__":
    unittest.main()
