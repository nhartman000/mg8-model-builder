import copy, json, pathlib, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "console"))
from decision_console.core import (DecisionLog, DecisionError, project_owner_decisions, project_register_md,
                                   project_qson_events, sha256_hex, md_escape, MODULE_UNIVERSE, validate_catalog)

SYN = json.loads((ROOT / "console/fixtures/synthetic_catalog.json").read_text())
REAL = json.loads((ROOT / "console/fixtures/catalog.v2.json").read_text())
REAL3 = json.loads((ROOT / "console/fixtures/catalog.v3.json").read_text())
REAL31 = json.loads((ROOT / "console/fixtures/catalog.v3.1.json").read_text())
REAL32 = json.loads((ROOT / "console/fixtures/catalog.v3.2.json").read_text())
REAL33 = json.loads((ROOT / "console/fixtures/catalog.v3.3.json").read_text())
REAL34 = json.loads((ROOT / "console/fixtures/catalog.v3.4.json").read_text())
REAL35 = json.loads((ROOT / "console/fixtures/catalog.v3.5.json").read_text())
REAL36 = json.loads((ROOT / "console/fixtures/catalog.v3.6.json").read_text())
REAL37 = json.loads((ROOT / "console/fixtures/catalog.v3.7.json").read_text())
REAL38 = json.loads((ROOT / "console/fixtures/catalog.v3.8.json").read_text())
REAL39 = json.loads((ROOT / "console/fixtures/catalog.v3.9.json").read_text())
REAL310 = json.loads((ROOT / "console/fixtures/catalog.v3.10.json").read_text())
REAL311 = json.loads((ROOT / "console/fixtures/catalog.v3.11.json").read_text())
REAL312 = json.loads((ROOT / "console/fixtures/catalog.v3.12.json").read_text())
REAL313 = json.loads((ROOT / "console/fixtures/catalog.v3.13.json").read_text())
REAL314 = json.loads((ROOT / "console/fixtures/catalog.v3.14.json").read_text())
REAL315 = json.loads((ROOT / "console/fixtures/catalog.v3.15.json").read_text())
REAL_EVENTS = [json.loads(l) for l in (ROOT / "console/fixtures/events.v2.jsonl").read_text().splitlines() if l]
O, T = "owner-synthetic", "2026-01-01T00:00:00Z"
INCOMPLETE_REAL = set()


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
        l = DecisionLog.load([copy.deepcopy(REAL), copy.deepcopy(REAL3), copy.deepcopy(REAL31), copy.deepcopy(REAL32), copy.deepcopy(REAL33), copy.deepcopy(REAL34), copy.deepcopy(REAL35), copy.deepcopy(REAL36), copy.deepcopy(REAL37), copy.deepcopy(REAL38), copy.deepcopy(REAL39), copy.deepcopy(REAL310), copy.deepcopy(REAL311), copy.deepcopy(REAL312), copy.deepcopy(REAL313), copy.deepcopy(REAL314), copy.deepcopy(REAL315)], REAL_EVENTS)
        bad = _rec(REAL38, "D8")
        bad.update(heads=4, head_width=32, model_width=96)
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
    def test_approved_before_d7_only(self):
        l = DecisionLog.load([copy.deepcopy(REAL), copy.deepcopy(REAL3), copy.deepcopy(REAL31), copy.deepcopy(REAL32), copy.deepcopy(REAL33), copy.deepcopy(REAL34), copy.deepcopy(REAL35), copy.deepcopy(REAL36), copy.deepcopy(REAL37), copy.deepcopy(REAL38), copy.deepcopy(REAL39), copy.deepcopy(REAL310), copy.deepcopy(REAL311), copy.deepcopy(REAL312), copy.deepcopy(REAL313), copy.deepcopy(REAL314), copy.deepcopy(REAL315)], REAL_EVENTS)
        st = {d["id"]: d for d in project_owner_decisions(l)["decisions"]}
        approved = {i for i, d in st.items() if d["state"] == "APPROVED"}
        self.assertEqual(approved, {"D0", "D1-context", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "D11"})
        for i in approved:
            self.assertTrue(st[i]["recorded_against_current_definition"])
            self.assertEqual(st[i]["value"], st[i]["recommended"])
        self.assertEqual(st["D1-context"]["value"]["window_tokens"], 1024)
        self.assertEqual(st["D4"]["state"], "APPROVED")
        self.assertTrue(st["D4"]["recorded_against_current_definition"])
        self.assertEqual(st["D4"]["value"], st["D4"]["recommended"])
        self.assertEqual(st["D4"]["value"]["confidence_threshold"], 0.75)
        self.assertEqual(st["D7"]["state"], "APPROVED")
        self.assertEqual(st["D7"]["value"]["d_model"], 128)
        self.assertEqual(st["D7"]["value"]["position_limit"], 1024)
        self.assertEqual(st["D9"]["state"], "APPROVED")
        self.assertEqual(st["D10"]["state"], "APPROVED")
        self.assertEqual(st["D11"]["state"], "APPROVED")
        self.assertIn("Common Corpus", st["D11"]["value"]["corpus"])
        self.assertIsNone(st["D12"]["value"])
        self.assertEqual({k for k, d in st.items() if not d["contract_complete"]}, INCOMPLETE_REAL)
        self.assertTrue(all(st[i]["state"] == "PENDING" for i in INCOMPLETE_REAL))
        hist = DecisionLog.load(copy.deepcopy(REAL), REAL_EVENTS[:1])
        d5 = {d["id"]: d for d in project_owner_decisions(hist)["decisions"]}["D5"]
        self.assertTrue(d5["recorded_against_current_definition"])
        self.assertEqual(d5["value"], REAL_EVENTS[0]["value"])

    def test_bulk_on_real_never_approves_placeholders_or_unblocks_all(self):
        l = DecisionLog.load([copy.deepcopy(REAL), copy.deepcopy(REAL3), copy.deepcopy(REAL31), copy.deepcopy(REAL32), copy.deepcopy(REAL33), copy.deepcopy(REAL34), copy.deepcopy(REAL35), copy.deepcopy(REAL36), copy.deepcopy(REAL37), copy.deepcopy(REAL38), copy.deepcopy(REAL39), copy.deepcopy(REAL310), copy.deepcopy(REAL311), copy.deepcopy(REAL312), copy.deepcopy(REAL313), copy.deepcopy(REAL314), copy.deepcopy(REAL315)], REAL_EVENTS)
        r = l.approve_all_recommended(owner=O, timestamp=T)
        self.assertEqual(set(r["skipped_incomplete"]), INCOMPLETE_REAL)
        for d in INCOMPLETE_REAL: self.assertEqual(l.state(d), "PENDING")
        rd = l.readiness()
        self.assertFalse(rd["readiness_authoritative"])
        for m in ("B1", "B2", "B3"):
            self.assertIn("CONTRACT_NOT_MODELED_IN_CONSOLE", rd["blocked"][m])
        for m in ("B7", "B11", "INTEGRATION"):
            self.assertNotIn(m, rd["blocked"])
        self.assertIn("D14", [e["decision_id"] for e in r["events"]])
        self.assertNotIn("D11", [e["decision_id"] for e in r["events"]])

    def test_generated_outputs_match_committed(self):
        l = DecisionLog.load([copy.deepcopy(REAL), copy.deepcopy(REAL3), copy.deepcopy(REAL31), copy.deepcopy(REAL32), copy.deepcopy(REAL33), copy.deepcopy(REAL34), copy.deepcopy(REAL35), copy.deepcopy(REAL36), copy.deepcopy(REAL37), copy.deepcopy(REAL38), copy.deepcopy(REAL39), copy.deepcopy(REAL310), copy.deepcopy(REAL311), copy.deepcopy(REAL312), copy.deepcopy(REAL313), copy.deepcopy(REAL314), copy.deepcopy(REAL315)], REAL_EVENTS)
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
    return DecisionLog.load([copy.deepcopy(REAL), copy.deepcopy(REAL3), copy.deepcopy(REAL31), copy.deepcopy(REAL32), copy.deepcopy(REAL33), copy.deepcopy(REAL34), copy.deepcopy(REAL35), copy.deepcopy(REAL36), copy.deepcopy(REAL37), copy.deepcopy(REAL38), copy.deepcopy(REAL39), copy.deepcopy(REAL310), copy.deepcopy(REAL311), copy.deepcopy(REAL312), copy.deepcopy(REAL313), copy.deepcopy(REAL314), copy.deepcopy(REAL315)], REAL_EVENTS)


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
        n = len(l.events)
        wide = _rec(REAL38, "D8")
        wide.update(heads=8, head_width=32, model_width=256)
        with self.assertRaisesRegex(DecisionError, "cross-decision"):
            l.record("D8", "CHOOSE_OTHER", value=wide, owner=O, timestamp=T)
        self.assertEqual(len(l.events), n)

        l = _stack()
        l.record("D7", "APPROVE_RECOMMENDATION", owner=O, timestamp=T)
        narrow = _rec(REAL38, "D8")
        narrow.update(heads=2, head_width=32, model_width=64)
        with self.assertRaisesRegex(DecisionError, "cross-decision"):
            l.record("D8", "CHOOSE_OTHER", value=narrow, owner=O, timestamp=T)
        broken = _rec(REAL38, "D8")
        broken["model_width"] = 100
        with self.assertRaises(DecisionError):
            l.record("D8", "CHOOSE_OTHER", value=broken, owner=O, timestamp=T)
        l.record("D8", "APPROVE_RECOMMENDATION", owner=O, timestamp=T)
        self.assertEqual(l.events[-1]["value"]["model_width"], 128)

        l = _stack()
        n = len(l.events)
        window = _rec(REAL3, "D1-context")
        window["window_tokens"] = 2048
        with self.assertRaisesRegex(DecisionError, "cross-decision"):
            l.record("D1-context", "CHOOSE_OTHER", value=window, owner=O, timestamp=T)
        self.assertEqual(len(l.events), n)
        self.assertEqual(next(e["value"]["position_limit"] for e in reversed(l.events) if e["decision_id"] == "D7"), 1024)

    def test_stack_bulk_keeps_recommendations_consistent(self):
        l = _stack()
        r = l.approve_all_recommended(owner=O, timestamp=T)
        self.assertEqual(set(r["skipped_incomplete"]), INCOMPLETE_REAL)
        ids = [e["decision_id"] for e in r["events"]]
        self.assertNotIn("D0", ids)
        self.assertNotIn("D1-context", ids)
        self.assertNotIn("D5", ids)
        self.assertEqual(l.events[0]["event_id"], D5_EVENT)
        vals = {e["decision_id"]: e["value"] for e in r["events"]}
        d1 = next(e for e in reversed(l.events) if e["decision_id"] == "D1-context")
        d7 = next(e for e in reversed(l.events) if e["decision_id"] == "D7")
        d8 = next(e for e in reversed(l.events) if e["decision_id"] == "D8")
        self.assertNotIn("D7", ids)
        self.assertNotIn("D9", ids)
        self.assertNotIn("D10", ids)
        self.assertEqual(d7["value"]["d_model"], d8["value"]["model_width"])
        self.assertEqual(d1["value"]["window_tokens"], d7["value"]["position_limit"])
        self.assertFalse(l.readiness()["readiness_authoritative"])
        for did in INCOMPLETE_REAL:
            self.assertEqual(l.state(did), "PENDING")

    def test_bulk_conflict_writes_nothing(self):
        l = _stack()
        n = len(l.events)
        odd = _rec(REAL3, "D7")
        odd["d_model"] = 64
        with self.assertRaisesRegex(DecisionError, "cross-decision"):
            l.record("D7", "CHOOSE_OTHER", value=odd, owner=O, timestamp=T)
        self.assertEqual(len(l.events), n)
        self.assertEqual(l.state("D7"), "APPROVED")
        self.assertEqual(l.state("D8"), "APPROVED")
        self.assertEqual(l.state("D12"), "PENDING")

    def test_real_numeric_bounds(self):
        l = _stack()
        d9 = _rec(REAL39, "D9")
        for bad in (1.1, -0.01):
            v = dict(d9, dropout_training=bad)
            with self.assertRaises(DecisionError):
                l.record("D9", "CHOOSE_OTHER", value=v, owner=O, timestamp=T)
        l.record("D9", "CHOOSE_OTHER", value=dict(d9, dropout_training=0.05, dropout_inference=1), owner=O, timestamp=T)
        d7 = next(d for d in REAL38["decisions"] if d["id"] == "D7")
        self.assertIsNone(d7["contract"]["d_model"]["maximum"])
        huge = _rec(REAL3, "D7")
        huge["d_model"] = 10 ** 6
        with self.assertRaisesRegex(DecisionError, "cross-decision"):
            l.record("D7", "CHOOSE_OTHER", value=huge, owner=O, timestamp=T)

        d4 = _rec(REAL35, "D4")
        self.assertEqual(d4["confidence_threshold"], 0.75)
        self.assertIn("do not prune either domain", d4["tie_policy"])
        base = d4
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
        self.assertEqual(len(fresh.events), len(REAL_EVENTS))
        self.assertEqual(fresh.state("D7"), "APPROVED")
        self.assertEqual(fresh.state("D11"), "APPROVED")
        self.assertEqual(fresh.state("D12"), "PENDING")

    def test_d5_expansion_keeps_historical_event(self):
        self.assertEqual(REAL_EVENTS[0]["event_id"], D5_EVENT)
        self.assertEqual(REAL_EVENTS[0]["catalog_digest"], D5_V2_DIGEST)
        self.assertEqual(sha256_hex(REAL), D5_V2_DIGEST)
        self.assertNotEqual(sha256_hex(REAL3), D5_V2_DIGEST)
        self.assertEqual([e["decision_id"] for e in REAL_EVENTS], ["D5", "D0", "D1-context", "D5", "D4", "D6", "D8", "D7", "D9", "D10", "D11"])
        self.assertEqual([e["action"] for e in REAL_EVENTS],
                         ["HISTORICAL_APPROVAL"] + ["APPROVE_RECOMMENDATION"] * 10)
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
        self.assertTrue(p["D5"]["recorded_against_current_definition"])
        self.assertEqual(p["D5"]["value"], rec)
        self.assertEqual(p["D5"]["recommended"], rec)
        self.assertEqual(p["D0"]["state"], "APPROVED")
        self.assertEqual(p["D1-context"]["value"]["window_tokens"], 1024)
        for did in ("D12", "D13", "D14", "D15", "D16"):
            self.assertEqual(p[did]["state"], "PENDING", did)
        self.assertNotIn("D5", l.readiness()["blocked"]["B5"])
        self.assertFalse(l.readiness()["readiness_authoritative"])
        with self.assertRaises(DecisionError):
            l.import_historical("D5", timestamp=T, rationale="do not mint")
        self.assertEqual(len(l.events), 11)
        with self.assertRaises(DecisionError):
            DecisionLog.load(copy.deepcopy(REAL3), REAL_EVENTS)
        with self.assertRaises(DecisionError):
            DecisionLog.load(copy.deepcopy(REAL), REAL_EVENTS)
        with self.assertRaises(DecisionError):
            DecisionLog.load([copy.deepcopy(REAL3), copy.deepcopy(REAL)], REAL_EVENTS)
        v2_only = DecisionLog.load(copy.deepcopy(REAL), [REAL_EVENTS[0]])
        d5 = {d["id"]: d for d in project_owner_decisions(v2_only)["decisions"]}["D5"]
        self.assertTrue(d5["recorded_against_current_definition"])
        self.assertEqual(d5["value"], old)

        reconfirm = next(e for e in l.events if e["decision_id"] == "D5" and e["action"] == "APPROVE_RECOMMENDATION")
        self.assertEqual(reconfirm["decision_id"], "D5")
        self.assertEqual(reconfirm["action"], "APPROVE_RECOMMENDATION")
        self.assertEqual(reconfirm["supersedes"], D5_EVENT)
        self.assertEqual(reconfirm["catalog_digest"], sha256_hex(REAL3))
        self.assertEqual(reconfirm["value"]["gst_scope"], "request-scoped")
        self.assertEqual(reconfirm["value"]["user_version"], 2)
        self.assertEqual(l.event_state(D5_EVENT), "SUPERSEDED")
        md = project_register_md(l)
        d5row = [x for x in md.splitlines() if x.startswith("| D5 ")][0]
        self.assertNotIn("definition changed", d5row)
        self.assertIn("APPROVED", d5row)
        self.assertIn("D1-context.window_tokens = D7.position_limit", md)
        self.assertIn("D7.d_model = D8.model_width", md)
        for row in md.splitlines():
            if row.startswith("| D"):
                self.assertNotIn("definition changed", row)
        qson = json.dumps(project_qson_events(l))
        for secret in ("request-scoped", "gst_context.py", "gst-context-v1", "deferred"):
            self.assertNotIn(secret, qson)

    def test_d6_schema_recorded_not_approved(self):
        old = next(d for d in REAL3["decisions"] if d["id"] == "D6")
        new = next(d for d in REAL31["decisions"] if d["id"] == "D6")
        self.assertEqual(REAL31["schema"], "mg8.decision-catalog.v3")
        self.assertEqual(REAL31["catalog_version"], "3.1")
        for a, b in zip(REAL3["decisions"], REAL31["decisions"]):
            if a["id"] != "D6":
                self.assertEqual(a, b)
        self.assertEqual(new["contract"]["inputs"], old["contract"]["inputs"])
        self.assertEqual(new["contract"]["literal_fallback"], old["contract"]["literal_fallback"])
        self.assertEqual(new["contract"]["endpoint"], old["contract"]["endpoint"])
        self.assertEqual(new["contract"]["tote_write_policy"], old["contract"]["tote_write_policy"])
        field = new["contract"]["request_response_schema"]
        self.assertFalse(field["owner_input_required"])
        text = field["recommended"]
        for phrase in ("fibbonacci sequence", "`FbncSqnc`", "`_wrd`", "`wrdSmth`", "ftbl",
                       "modality operators", "narrative perspective and tense", "time of day if any",
                       "grammatical invariants"):
            self.assertIn(phrase, text)
        l = _stack()
        self.assertEqual([e["decision_id"] for e in l.events], ["D5", "D0", "D1-context", "D5", "D4", "D6", "D8", "D7", "D9", "D10", "D11"])
        p = {d["id"]: d for d in project_owner_decisions(l)["decisions"]}
        self.assertEqual(p["D6"]["state"], "APPROVED")
        self.assertTrue(p["D6"]["contract_complete"])
        self.assertEqual(p["D6"]["value"], p["D6"]["recommended"])
        self.assertEqual(p["D6"]["owner_input_required"], [])
        for did in ("D0", "D1-context", "D5"):
            self.assertEqual(p[did]["state"], "APPROVED")
            self.assertTrue(p[did]["recorded_against_current_definition"])
        d4 = next(d for d in REAL31["decisions"] if d["id"] == "D4")
        for name in ("seed_lexicon", "confidence_threshold", "tie_policy"):
            self.assertIsNone(d4["contract"][name]["recommended"])
            self.assertTrue(d4["contract"][name]["owner_input_required"])
        self.assertEqual(len(l.events), 11)
        self.assertIn("D6", [e["decision_id"] for e in l.events])
        md = project_register_md(l)
        row = [x for x in md.splitlines() if x.startswith("| D6 ")][0]
        self.assertIn("| APPROVED |", row)
        self.assertNotIn("awaiting owner approval", row)
        self.assertIn("| complete |", row)
        self.assertNotIn("INCOMPLETE", row)
        self.assertNotIn("FbncSqnc", json.dumps(project_qson_events(l)))

    def test_d4_lexicon_recorded_not_approved(self):
        self.assertEqual(REAL32["schema"], "mg8.decision-catalog.v3")
        self.assertEqual(REAL32["catalog_version"], "3.2")
        for a, b in zip(REAL31["decisions"], REAL32["decisions"]):
            if a["id"] != "D4":
                self.assertEqual(a, b)
        old = next(d for d in REAL31["decisions"] if d["id"] == "D4")
        new = next(d for d in REAL32["decisions"] if d["id"] == "D4")
        self.assertEqual(new["contract"]["method"], old["contract"]["method"])
        self.assertEqual(new["contract"]["confidence_threshold"], old["contract"]["confidence_threshold"])
        self.assertEqual(new["contract"]["tie_policy"], old["contract"]["tie_policy"])
        path = "icm/MG8PK/lexicons/nych-professional-domain-taxonomy.md"
        lexicon = (ROOT / path).read_text(encoding="utf-8")
        for phrase in ("NYCH Professional Domain Taxonomy — Expanded Draft",
                       "Coverage gaps to consider separately",
                       "NYCH/TOTE ingestion and review notes",
                       "Pasted text (20261108-193332).txt"):
            self.assertIn(phrase, lexicon)
        url = "https://tld-list.com/tld-categories/professional"
        for name in ("seed_lexicon", "scoring_rubric"):
            field = new["contract"][name]
            self.assertEqual(field["kind"], "text")
            self.assertFalse(field["owner_input_required"])
            self.assertIn(url, field["recommended"])
            self.assertIn(path, field["recommended"])
            self.assertIn("is primary", field["recommended"])
            self.assertIn("fall back to the attached NYCH taxonomy lexicon", field["recommended"])
            self.assertIn("updated with every proper NYCH update", field["recommended"])
        for name in ("confidence_threshold", "tie_policy"):
            self.assertIsNone(new["contract"][name]["recommended"])
            self.assertTrue(new["contract"][name]["owner_input_required"])
        l = _stack()
        self.assertEqual([e["decision_id"] for e in l.events], ["D5", "D0", "D1-context", "D5", "D4", "D6", "D8", "D7", "D9", "D10", "D11"])
        p = {d["id"]: d for d in project_owner_decisions(l)["decisions"]}
        self.assertEqual(p["D4"]["state"], "APPROVED")
        self.assertTrue(p["D4"]["contract_complete"])
        self.assertEqual(p["D4"]["value"], p["D4"]["recommended"])
        self.assertEqual(p["D4"]["owner_input_required"], [])
        self.assertEqual(p["D6"]["owner_input_required"], [])
        for did in ("D0", "D1-context", "D5"):
            self.assertEqual(p[did]["state"], "APPROVED")
            self.assertTrue(p[did]["recorded_against_current_definition"])
        self.assertEqual(len(l.events), 11)
        row = [x for x in project_register_md(l).splitlines() if x.startswith("| D4 ")][0]
        self.assertIn("| APPROVED |", row)
        self.assertNotIn("awaiting owner approval", row)
        self.assertIn("| complete |", row)
        self.assertNotIn("INCOMPLETE", row)
        qson = json.dumps(project_qson_events(l))
        self.assertNotIn("tld-list.com", qson)

    def test_d4_unresolved_domain_not_an_approval(self):
        self.assertEqual(REAL33["schema"], "mg8.decision-catalog.v3")
        self.assertEqual(REAL33["catalog_version"], "3.3")
        for a, b in zip(REAL32["decisions"], REAL33["decisions"]):
            if a["id"] != "D4":
                self.assertEqual(a, b)
        old = next(d for d in REAL32["decisions"] if d["id"] == "D4")
        new = next(d for d in REAL33["decisions"] if d["id"] == "D4")
        self.assertEqual(new["contract"]["seed_lexicon"], old["contract"]["seed_lexicon"])
        self.assertEqual(new["contract"]["scoring_rubric"], old["contract"]["scoring_rubric"])
        self.assertEqual(new["contract"]["confidence_threshold"], old["contract"]["confidence_threshold"])
        self.assertEqual(new["contract"]["tie_policy"], old["contract"]["tie_policy"])
        self.assertEqual(new["contract"]["method"]["recommended"],
                         "versioned local associative lexicon; no LLM calls; ranked multi-label evidence; if unresolvable, write unresolved domain; no forced symbol")
        self.assertNotIn("UNKNOWN", new["contract"]["method"]["recommended"])
        note = new["contract"]["rule_module"]
        self.assertFalse(note["owner_input_required"])
        self.assertEqual(note["recommended"],
                         "The actual rules for domain decisions will be an extensive module needing expansion, and will be an entire evening of work one day. For now, the current rule and lists will suffice. If unresolvable, write unresolved domain.")
        l = _stack()
        p = {d["id"]: d for d in project_owner_decisions(l)["decisions"]}
        self.assertEqual(p["D4"]["state"], "APPROVED")
        self.assertEqual(p["D4"]["value"]["tie_policy"], p["D4"]["recommended"]["tie_policy"])
        self.assertEqual(p["D4"]["owner_input_required"], [])
        self.assertEqual(len(l.events), 11)

    def test_d4_confidence_and_d6_endpoint_not_approvals(self):
        self.assertEqual(REAL34["catalog_version"], "3.4")
        for a, b in zip(REAL33["decisions"], REAL34["decisions"]):
            if a["id"] not in ("D4", "D6"):
                self.assertEqual(a, b)
        old4 = next(d for d in REAL33["decisions"] if d["id"] == "D4")
        new4 = next(d for d in REAL34["decisions"] if d["id"] == "D4")
        for name in ("method", "seed_lexicon", "scoring_rubric", "rule_module", "tie_policy"):
            self.assertEqual(new4["contract"][name], old4["contract"][name])
        self.assertEqual(new4["contract"]["confidence_threshold"]["recommended"], 0.75)
        self.assertFalse(new4["contract"]["confidence_threshold"]["owner_input_required"])
        self.assertIsNone(new4["contract"]["tie_policy"]["recommended"])
        self.assertTrue(new4["contract"]["tie_policy"]["owner_input_required"])
        rule = new4["contract"]["confidence_rule"]["recommended"]
        for phrase in ("confidence 10", '"ing"', '"ion"', '"ed"', '"er"', "80–85%", "75% or lower", "unresolved domain"):
            self.assertIn(phrase, rule)
        old6 = next(d for d in REAL33["decisions"] if d["id"] == "D6")
        new6 = next(d for d in REAL34["decisions"] if d["id"] == "D6")
        for name in ("inputs", "literal_fallback", "request_response_schema", "tote_write_policy"):
            self.assertEqual(new6["contract"][name], old6["contract"][name])
        endpoint = new6["contract"]["endpoint"]
        self.assertFalse(endpoint["owner_input_required"])
        self.assertIn("https://unicode.org/emoji/charts/full-emoji-list.html", endpoint["recommended"])
        self.assertIn("https://www.unicode.org/emoji/charts-18.0/", endpoint["recommended"])
        self.assertIn("common emoji library", endpoint["recommended"])
        self.assertIsNone(new6["contract"]["tote_write_policy"]["recommended"])
        l = _stack()
        p = {d["id"]: d for d in project_owner_decisions(l)["decisions"]}
        self.assertEqual(p["D4"]["state"], "APPROVED")
        self.assertEqual(p["D6"]["state"], "APPROVED")
        self.assertEqual(p["D4"]["value"]["confidence_threshold"], 0.75)
        self.assertEqual(p["D6"]["value"], p["D6"]["recommended"])
        self.assertEqual(p["D4"]["owner_input_required"], [])
        self.assertEqual(p["D6"]["owner_input_required"], [])
        self.assertEqual(len(l.events), 11)
        self.assertIn("D6", [e["decision_id"] for e in l.events])

    def test_d6_write_policy_recorded_not_approved(self):
        self.assertEqual(REAL36["catalog_version"], "3.6")
        for a, b in zip(REAL35["decisions"], REAL36["decisions"]):
            if a["id"] != "D6":
                self.assertEqual(a, b)
        old = next(d for d in REAL35["decisions"] if d["id"] == "D6")
        new = next(d for d in REAL36["decisions"] if d["id"] == "D6")
        self.assertEqual(new["question"], old["question"])
        for name, field in old["contract"].items():
            if name != "tote_write_policy":
                self.assertEqual(new["contract"][name], field)
        text = (
            "The modality operator is invariant and symbolic, but the TOTE loop database is inherently not symbolic, "
            "because symbols are chosen by domain. The TOTE loop library is the words organized in cells, rows, and columns: "
            "domain-specific, subdomain, and technique. Then the TOTE loop describes the technique with a minimum of 1 actor, "
            "1 action, 1 object, and 1 modality operator."
        )
        self.assertEqual(new["contract"]["tote_write_policy"]["recommended"], text)
        self.assertFalse(new["contract"]["tote_write_policy"]["owner_input_required"])
        l = _stack()
        p = {d["id"]: d for d in project_owner_decisions(l)["decisions"]}
        self.assertEqual(p["D6"]["state"], "APPROVED")
        self.assertTrue(p["D6"]["contract_complete"])
        self.assertEqual(p["D6"]["value"], p["D6"]["recommended"])
        self.assertTrue(p["D6"]["recommended"]["tote_write_policy"].startswith(text + "\n\n"))
        self.assertEqual(p["D4"]["state"], "APPROVED")
        self.assertEqual([e["decision_id"] for e in l.events], ["D5", "D0", "D1-context", "D5", "D4", "D6", "D8", "D7", "D9", "D10", "D11"])

    def test_d6_chat_local_symbols_appended_not_approved(self):
        self.assertEqual(REAL37["catalog_version"], "3.7")
        for a, b in zip(REAL36["decisions"], REAL37["decisions"]):
            if a["id"] != "D6":
                self.assertEqual(a, b)
        old = next(d for d in REAL36["decisions"] if d["id"] == "D6")
        new = next(d for d in REAL37["decisions"] if d["id"] == "D6")
        self.assertEqual(new["question"], old["question"])
        for name, field in old["contract"].items():
            if name not in ("request_response_schema", "tote_write_policy"):
                self.assertEqual(new["contract"][name], field)
        schema_add = (
            "At the point the LLM call is made to choose the gestalt emoji, NYCH symbols are chosen per word. "
            "This happens after the domain has been identified and the lookup has given subdomains and related structure. "
            "Those symbols are temporary or unique to this chat. They will eventually become normalized because of the legend "
            "and the LLM preference for stability. Per domain there will not be much variance, but some domains will require "
            "the same symbols. For example, computers and word processing may both use the computer-screen gestalt as the best match, "
            "and that symbol will represent something different in each domain. That on-the-fly sharing is the reason for choosing symbols this way."
        )
        write_add = (
            "Word organizing in the database will preserve the domain organization and the TOTE loop sequence, "
            "and allow all but the modality operators to be dynamically chosen."
        )
        for name, extra in (("request_response_schema", schema_add), ("tote_write_policy", write_add)):
            prior = old["contract"][name]["recommended"]
            current = new["contract"][name]["recommended"]
            self.assertTrue(current.startswith(prior + "\n\n"))
            self.assertEqual(current[len(prior) + 2:], extra)
            self.assertEqual(new["contract"][name]["owner_input_required"], old["contract"][name]["owner_input_required"])
        l = _stack()
        p = {d["id"]: d for d in project_owner_decisions(l)["decisions"]}
        self.assertEqual(p["D6"]["state"], "APPROVED")
        self.assertEqual(p["D6"]["value"], p["D6"]["recommended"])
        self.assertIn("D6", [e["decision_id"] for e in l.events])
        for did in ("D0", "D1-context", "D4", "D5"):
            self.assertEqual(p[did]["state"], "APPROVED")
            self.assertTrue(p[did]["recorded_against_current_definition"])

    def test_d4_tie_policy_recorded_and_approved(self):
        self.assertEqual(REAL35["catalog_version"], "3.5")
        for a, b in zip(REAL34["decisions"], REAL35["decisions"]):
            if a["id"] != "D4":
                self.assertEqual(a, b)
        old = next(d for d in REAL34["decisions"] if d["id"] == "D4")
        new = next(d for d in REAL35["decisions"] if d["id"] == "D4")
        for name, field in old["contract"].items():
            if name != "tie_policy":
                self.assertEqual(new["contract"][name], field)
        tie = new["contract"]["tie_policy"]
        self.assertFalse(tie["owner_input_required"])
        self.assertEqual(
            tie["recommended"],
            "In the strange case of matching — a tie, when two or more domains receive the same score — "
            "include both (or all tied domains) and do not prune either domain. "
            "Instead use both as possible root domains and reason within both.",
        )
        l = _stack()
        p = {d["id"]: d for d in project_owner_decisions(l)["decisions"]}
        self.assertEqual(p["D4"]["state"], "APPROVED")
        self.assertTrue(p["D4"]["recorded_against_current_definition"])
        self.assertEqual(p["D4"]["value"]["tie_policy"], tie["recommended"])
        self.assertEqual(p["D4"]["owner_input_required"], [])
        self.assertEqual(p["D4"]["recommended"]["tie_policy"], tie["recommended"])
        d4_event = next(e for e in l.events if e["decision_id"] == "D4")
        self.assertEqual(d4_event["event_id"], "sha256:1d80d3eaa2a1fa41bf855be5cbd2ea3685aeeab31a6d3a4c2705daafbe9032bd")
        self.assertEqual(d4_event["catalog_digest"], sha256_hex(REAL35))
        self.assertEqual(d4_event["action"], "APPROVE_RECOMMENDATION")
        self.assertEqual(p["D6"]["state"], "APPROVED")
        self.assertEqual(p["D6"]["owner_input_required"], [])
        self.assertEqual([e["decision_id"] for e in l.events], ["D5", "D0", "D1-context", "D5", "D4", "D6", "D8", "D7", "D9", "D10", "D11"])

    def test_d8_attention_primacy_approved(self):
        self.assertEqual(REAL38["catalog_version"], "3.8")
        for a, b in zip(REAL37["decisions"], REAL38["decisions"]):
            if a["id"] != "D8":
                self.assertEqual(a, b)
        old = next(d for d in REAL37["decisions"] if d["id"] == "D8")
        new = next(d for d in REAL38["decisions"] if d["id"] == "D8")
        for name in ("layers", "heads", "head_width", "model_width", "mask", "kv_cache"):
            self.assertEqual(new["contract"][name], old["contract"][name])
        self.assertEqual(new["constraints"], old["constraints"])
        self.assertEqual(new["contract"]["layers"]["recommended"], 2)
        self.assertEqual(new["contract"]["heads"]["recommended"], 4)
        self.assertEqual(new["contract"]["head_width"]["recommended"], 32)
        self.assertEqual(new["contract"]["model_width"]["recommended"], 128)
        self.assertEqual(new["contract"]["mask"]["recommended"], "causal")
        self.assertEqual(new["contract"]["kv_cache"]["recommended"], "none_in_reference")
        self.assertEqual(
            new["contract"]["primacy_tradeoff"]["recommended"],
            "Until patterns are recognized from repetition, the abbreviated words appended on the gestalt ID string are primary. "
            "A tradeoff rule determines when the dynamic domain lexicons have stabilized; only then may the switch to symbolic (gestalt) primary be made. "
            "Words are not discarded; they remain appended on the ID string.",
        )
        self.assertEqual(
            new["contract"]["attention_mixture"]["recommended"],
            "Attention weights the current ID and its neighbors as follows, as a starting mix: "
            "30% the current gestalt, 30% the current abbreviated word, 20% neighboring gestalts, and 20% neighboring abbreviated words "
            "(the remaining 40% neighboring signal split 20/20). If that mix does not work, readjust the percentages and ratios. "
            "Adjust until optimal percentages and ratios are obtained through testing on natural language (\"nat lang\"). "
            "The 30% current gestalt / 30% current abbreviated word / 20% neighboring gestalts / 20% neighboring abbreviated words mix is the starting point, not a frozen optimum.",
        )
        self.assertEqual(
            new["contract"]["abbreviation_to_gestalt_training"]["recommended"],
            "Part of training this model is training from word abbreviations to stabilized gestalt dynamics. "
            "This is unique to the NYCH language model.",
        )
        for name in ("primacy_tradeoff", "attention_mixture", "abbreviation_to_gestalt_training"):
            self.assertFalse(new["contract"][name]["owner_input_required"])
        self.assertNotIn("stabilized at", new["contract"]["primacy_tradeoff"]["recommended"])
        l = _stack()
        p = {d["id"]: d for d in project_owner_decisions(l)["decisions"]}
        self.assertEqual(p["D8"]["state"], "APPROVED")
        self.assertTrue(p["D8"]["recorded_against_current_definition"])
        self.assertEqual(p["D8"]["value"], p["D8"]["recommended"])
        self.assertEqual(p["D7"]["state"], "APPROVED")
        self.assertEqual(p["D9"]["state"], "APPROVED")
        self.assertEqual(p["D7"]["value"]["position_limit"], 1024)
        event = next(e for e in l.events if e["decision_id"] == "D8")
        self.assertEqual(event["decision_id"], "D8")
        self.assertEqual(event["action"], "APPROVE_RECOMMENDATION")
        self.assertEqual(event["event_id"], "sha256:2797129d115485f3c20851afdd73b17320f8ed2edd899b5f3095ebcf06105a88")
        self.assertEqual(event["catalog_digest"], sha256_hex(REAL38))
        self.assertEqual(event["owner"], "Nick Hartman")
        self.assertEqual(event["timestamp"], "2026-11-09T01:13:00Z")
        self.assertEqual([e["decision_id"] for e in l.events], ["D5", "D0", "D1-context", "D5", "D4", "D6", "D8", "D7", "D9", "D10", "D11"])

    def test_d9_mixing_console_recorded_not_approved(self):
        self.assertEqual(REAL39["catalog_version"], "3.9")
        for a, b in zip(REAL38["decisions"], REAL39["decisions"]):
            if a["id"] != "D9":
                self.assertEqual(a, b)
        old = next(d for d in REAL38["decisions"] if d["id"] == "D9")
        new = next(d for d in REAL39["decisions"] if d["id"] == "D9")
        for name in ("norm", "residual", "ffn", "ffn_hidden_width", "dropout_training", "dropout_inference"):
            self.assertEqual(new["contract"][name], old["contract"][name])
        self.assertEqual(new["contract"]["norm"]["recommended"], "pre_rmsnorm")
        self.assertEqual(new["contract"]["residual"]["recommended"], "yes")
        self.assertEqual(new["contract"]["ffn"]["recommended"], "SwiGLU")
        self.assertEqual(new["contract"]["ffn_hidden_width"]["recommended"], 512)
        self.assertEqual(new["contract"]["dropout_training"]["recommended"], 0.1)
        self.assertEqual(new["contract"]["dropout_inference"]["recommended"], 0.0)
        self.assertEqual(
            new["contract"]["mixing_console"]["recommended"],
            "A dynamic mixing console adjusts these numbers in real time like an audio mixer and finds the intended balance. "
            "An AI may perform the mixing under human observation. The console does not have to be used to obtain the live parameters at first. "
            "The mix channels being balanced are the current gestalt, the current abbreviated word, neighboring gestalts, and neighboring abbreviated words, "
            "starting from the D8 mix of 30/30/20/20, plus the D9 block numbers (especially feed-forward width and training dropout) that affect how those signals are mixed. "
            "Inference dropout remains 0.0 and is not a mix channel.",
        )
        self.assertEqual(
            new["contract"]["repeatability"]["recommended"],
            "The console must produce repeatable outcomes. The same recipe — operator (human or AI observed), observation seed, "
            "mix-channel values, and D9 block settings — must yield the same mix and the same digest, and the same seed plus starting mix "
            "must replay the same observed AI moves.",
        )
        for name in ("mixing_console", "repeatability"):
            self.assertFalse(new["contract"][name]["owner_input_required"])
        l = _stack()
        p = {d["id"]: d for d in project_owner_decisions(l)["decisions"]}
        self.assertEqual(p["D9"]["state"], "APPROVED")
        self.assertEqual(p["D9"]["value"], p["D9"]["recommended"])
        self.assertTrue(p["D9"]["contract_complete"])
        self.assertIn("D9", [e["decision_id"] for e in l.events])
        self.assertEqual(p["D7"]["state"], "APPROVED")
        self.assertEqual(p["D8"]["state"], "APPROVED")
        self.assertEqual(l.events[-1]["decision_id"], "D11")
        row = [x for x in project_register_md(l).splitlines() if x.startswith("| D9 ")][0]
        self.assertIn("| APPROVED |", row)

    def test_d10_verification_sidecar_recorded_not_approved(self):
        self.assertEqual(REAL310["catalog_version"], "3.10")
        for a, b in zip(REAL39["decisions"], REAL310["decisions"]):
            if a["id"] != "D10":
                self.assertEqual(a, b)
        old = next(d for d in REAL39["decisions"] if d["id"] == "D10")
        new = next(d for d in REAL310["decisions"] if d["id"] == "D10")
        for name in ("tied_embeddings", "logits", "softmax", "loss", "hard_output_constraints"):
            self.assertEqual(new["contract"][name], old["contract"][name])
        self.assertEqual(new["contract"]["tied_embeddings"]["recommended"], "yes")
        self.assertEqual(new["contract"]["logits"]["recommended"], "full_vocabulary")
        self.assertEqual(new["contract"]["softmax"]["recommended"], "numerically_stable")
        self.assertEqual(new["contract"]["loss"]["recommended"], "next_token_cross_entropy")
        self.assertEqual(new["contract"]["hard_output_constraints"]["recommended"], "none_until_specified")
        self.assertEqual(
            new["contract"]["verification_sidecar"]["recommended"],
            "The production D10 path still scores next NYCH tokens — gestalt IDs with the abbreviated word appended on the ID string — not full English words. "
            "To be sure that path is working, a parallel unmodified (\"standard\") version must ride the whole process alongside the abbreviated-word and gestalt mix as a faithfulness check. "
            "The mixed NYCH path should remain faithful if it is running alongside that proper unmodified companion. "
            "Once the D10 step is proven, delete the standard version. "
            "This sidecar is required verification, not an optional extra: it exists so the mixed path can be checked before it is trusted on its own.",
        )
        self.assertFalse(new["contract"]["verification_sidecar"]["owner_input_required"])
        l = _stack()
        p = {d["id"]: d for d in project_owner_decisions(l)["decisions"]}
        self.assertEqual(p["D10"]["state"], "APPROVED")
        self.assertEqual(p["D10"]["value"], p["D10"]["recommended"])
        self.assertTrue(p["D10"]["contract_complete"])
        self.assertIn("D10", [e["decision_id"] for e in l.events])
        self.assertEqual(p["D7"]["state"], "APPROVED")
        self.assertEqual(p["D9"]["state"], "APPROVED")
        self.assertEqual(l.events[-1]["decision_id"], "D11")
        row = [x for x in project_register_md(l).splitlines() if x.startswith("| D10 ")][0]
        self.assertIn("| APPROVED |", row)

    def test_d11_common_corpus_approved(self):
        self.assertEqual(REAL311["catalog_version"], "3.11")
        for a, b in zip(REAL310["decisions"], REAL311["decisions"]):
            if a["id"] != "D11":
                self.assertEqual(a, b)
        old = next(d for d in REAL310["decisions"] if d["id"] == "D11")
        new = next(d for d in REAL311["decisions"] if d["id"] == "D11")
        self.assertEqual(new["contract"]["policy"], old["contract"]["policy"])
        corpus = "Common Corpus (https://huggingface.co/datasets/PleIAs/common_corpus). English text is selected using the dataset's language field. This is the neural-training corpus and must remain distinct from the typo-statistics corpus."
        license_review = (
            "License review of Common Corpus as published on the dataset card: the collection contains only data that is uncopyrighted or freely licensed "
            "(public domain, U.S. federal public domain, CC0, Creative Commons, MIT, French Licence ouverte, and similar). "
            "Each document has a license field. The dataset is multilingual, so English documents must be filtered by that language metadata. "
            "Licensing information is based on available metadata; the per-document license field should be preserved, and documents without a clear open license should be excluded."
        )
        self.assertEqual(new["contract"]["corpus"]["recommended"], corpus)
        self.assertEqual(new["contract"]["license_review"]["recommended"], license_review)
        self.assertFalse(new["contract"]["corpus"]["owner_input_required"])
        self.assertFalse(new["contract"]["license_review"]["owner_input_required"])
        l = _stack()
        p = {d["id"]: d for d in project_owner_decisions(l)["decisions"]}
        self.assertEqual(p["D11"]["state"], "APPROVED")
        self.assertEqual(p["D11"]["value"]["corpus"], corpus)
        self.assertEqual(p["D11"]["value"]["license_review"], license_review)
        self.assertEqual(p["D11"]["owner_input_required"], [])
        for did in ("D12", "D13", "D14", "D15", "D16"):
            self.assertEqual(p[did]["state"], "PENDING")
            self.assertIsNone(p[did]["value"])
        event = l.events[-1]
        self.assertEqual(event["decision_id"], "D11")
        self.assertEqual(event["event_id"], "sha256:b7b4ff2f0e9d95eb399bc4ad1e36124fff66e8491e9776a24c51628d3c684aad")
        self.assertEqual(event["catalog_digest"], sha256_hex(REAL311))
        self.assertEqual(event["timestamp"], "2026-11-09T02:04:00Z")
        row = [x for x in project_register_md(l).splitlines() if x.startswith("| D11 ")][0]
        self.assertIn("| APPROVED |", row)
        self.assertNotIn("INCOMPLETE", row)

    def test_d13_runtime_recorded_and_not_approved(self):
        self.assertEqual(REAL312["catalog_version"], "3.12")
        for a, b in zip(REAL311["decisions"], REAL312["decisions"]):
            if a["id"] != "D13":
                self.assertEqual(a, b)
        old = next(d for d in REAL311["decisions"] if d["id"] == "D13")
        new = next(d for d in REAL312["decisions"] if d["id"] == "D13")
        self.assertEqual(new["question"], old["question"])
        self.assertEqual(new["contract"]["direction"], old["contract"]["direction"])
        self.assertEqual(new["contract"]["max_bytes_exclusive"], old["contract"]["max_bytes_exclusive"])
        runtime = new["contract"]["schema_validator_runtime"]
        self.assertFalse(runtime["owner_input_required"])
        self.assertIn("schemas/gitson-boundary-declaration.v1.schema.json", runtime["recommended"])
        self.assertIn("sha256:4761edfc48d1242ec36d768dde81633cc084877d5c94563ff6f26a28f3115a72", runtime["recommended"])
        self.assertIn("python -m gitson_boundary <declaration.json>", runtime["recommended"])
        self.assertIn("Offline deterministic", runtime["recommended"])
        l = _stack()
        self.assertEqual(len(l.events), 11)
        self.assertFalse(any(e["decision_id"] == "D13" for e in l.events))
        p = {d["id"]: d for d in project_owner_decisions(l)["decisions"]}
        self.assertTrue(p["D13"]["contract_complete"])
        self.assertEqual(p["D13"]["owner_input_required"], [])
        self.assertEqual(p["D13"]["state"], "PENDING")
        self.assertIsNone(p["D13"]["value"])
        self.assertEqual(p["D13"]["recommended"]["schema_validator_runtime"], runtime["recommended"])
        self.assertEqual(p["D13"]["recommended"]["max_bytes_exclusive"], 500000)
        for did in ("D12", "D14", "D15", "D16"):
            self.assertEqual(p[did]["state"], "PENDING")
            self.assertIsNone(p[did]["value"])
        row = [x for x in project_register_md(l).splitlines() if x.startswith("| D13 ")][0]
        self.assertIn("PENDING (Recommended—awaiting owner approval)", row)
        self.assertIn("| complete |", row)
        self.assertNotIn("APPROVED", row)
        self.assertNotIn("INCOMPLETE", row)
        self.assertIn("D13", l.readiness()["blocked"]["INTEGRATION"])

    def test_v313_reference_fields_stay_pending(self):
        self.assertEqual(REAL313["catalog_version"], "3.13")
        for a, b in zip(REAL312["decisions"], REAL313["decisions"]):
            if a["id"] not in {"D14", "D15", "D16"}:
                self.assertEqual(a, b)
        d = 128
        non = 2 * (4 * d * d + 3 * d * 512 + 2 * d) + d
        self.assertEqual(non, 524928)
        self.assertEqual(non + d * 10000, 1804928)
        self.assertEqual(non + d * 50257, 6957824)
        old14 = next(x for x in REAL312["decisions"] if x["id"] == "D14")
        new14 = next(x for x in REAL313["decisions"] if x["id"] == "D14")
        old15 = next(x for x in REAL312["decisions"] if x["id"] == "D15")
        new15 = next(x for x in REAL313["decisions"] if x["id"] == "D15")
        old16 = next(x for x in REAL312["decisions"] if x["id"] == "D16")
        new16 = next(x for x in REAL313["decisions"] if x["id"] == "D16")
        self.assertEqual(new14["question"], old14["question"])
        self.assertEqual(new15["contract"]["reporting"], old15["contract"]["reporting"])
        self.assertEqual(new16["contract"]["visibility"], old16["contract"]["visibility"])
        for dec, names in ((new14, ("parameter_band", "memory_latency_target", "training_hardware")),
                           (new15, ("thresholds",)),
                           (new16, ("format", "runtime_device"))):
            for name in names:
                field = dec["contract"][name]
                self.assertFalse(field["owner_input_required"])
                self.assertIn("Reference-derived", field["recommended"])
                self.assertIn("https://arxiv.org/abs/2305.07759", field["recommended"])
        band = new14["contract"]["parameter_band"]["recommended"]
        self.assertIn("524928", band)
        self.assertIn("1804928", band)
        self.assertIn("6957824", band)
        self.assertIn("10000", band)
        self.assertIn("50257", band)
        memory = new14["contract"]["memory_latency_target"]["recommended"]
        self.assertIn("7219712", memory)
        self.assertIn("27831296", memory)
        self.assertIn("28878848", memory)
        self.assertIn("111325184", memory)
        self.assertIn("single V100", memory)
        self.assertIn("V100", new14["contract"]["training_hardware"]["recommended"])
        rule = new15["contract"]["thresholds"]["recommended"]
        self.assertIn("starting value for owner review", rule)
        self.assertIn("less than or equal to 1.05 times", rule)
        self.assertIn("3 consecutive evaluations", rule)
        self.assertIn("not a cutoff printed in the paper", rule)
        self.assertIn("float32", new16["contract"]["format"]["recommended"])
        self.assertIn("not a GPT-Neo checkpoint", new16["contract"]["format"]["recommended"])
        self.assertIn("no KV cache", new16["contract"]["runtime_device"]["recommended"])
        l = _stack()
        self.assertEqual(len(l.events), len(REAL_EVENTS))
        self.assertFalse(any(e["decision_id"] in {"D12", "D13", "D14", "D15", "D16"} for e in l.events))
        p = {item["id"]: item for item in project_owner_decisions(l)["decisions"]}
        for did in ("D14", "D15", "D16"):
            self.assertTrue(p[did]["contract_complete"])
            self.assertEqual(p[did]["state"], "PENDING")
            self.assertIsNone(p[did]["value"])
            self.assertEqual(p[did]["owner_input_required"], [])
            row = [line for line in project_register_md(l).splitlines() if line.startswith(f"| {did} ")][0]
            self.assertIn("PENDING (Recommended—awaiting owner approval)", row)
            self.assertNotIn("| APPROVED |", row)
        self.assertEqual(p["D12"]["state"], "PENDING")
        self.assertEqual(p["D13"]["state"], "PENDING")
        questions = (ROOT / "icm/MG8PK/OWNER_QUESTIONS.md").read_text("utf-8")
        for module in ("B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10", "B11", "INTEGRATION"):
            self.assertIn(module, questions)

    def test_v314_owner_answers_stay_pending_on_d15(self):
        self.assertEqual(REAL314["catalog_version"], "3.14")
        for a, b in zip(REAL313["decisions"], REAL314["decisions"]):
            if a["id"] != "D15":
                self.assertEqual(a, b)
        old = next(d for d in REAL313["decisions"] if d["id"] == "D15")
        new = next(d for d in REAL314["decisions"] if d["id"] == "D15")
        self.assertEqual(new["contract"]["reporting"], old["contract"]["reporting"])
        self.assertEqual(new["contract"]["thresholds"], old["contract"]["thresholds"])
        abbrev = new["contract"]["gestalt_id_abbreviation"]
        inter = new["contract"]["interlinear_annotation"]
        self.assertFalse(abbrev["owner_input_required"])
        self.assertFalse(inter["owner_input_required"])
        self.assertIn(
            "drop vowels and double consonants keep y and capitalize if compound with a name like Fibonacci sequence gets FbncSqnc or compounded without name gets brick layer to brkLyr or computer programmer to cmptrPrgrmr",
            abbrev["recommended"],
        )
        self.assertIn("flagged as interpretation", abbrev["recommended"])
        self.assertIn("brkLyr", abbrev["recommended"])
        self.assertIn("not wired into any Builder", abbrev["recommended"])
        self.assertIn("Fibonacci alone", abbrev["recommended"])
        self.assertIn(
            "what I would like is a sort of info tree to exist interlinear so before gestalts are picked the nych output is still words but the info exists above in a sub-line interlinear style.",
            inter["recommended"],
        )
        self.assertIn("(domain=building_subdom=carpentry)(modalityOp=kine-int)(past-t)", inter["recommended"])
        self.assertIn("alignment unconfirmed", inter["recommended"])
        self.assertIn("B4 would produce the domain", inter["recommended"])
        self.assertIn("source of tense", inter["recommended"])
        l = _stack()
        self.assertEqual(len(l.events), len(REAL_EVENTS))
        self.assertFalse(any(e["decision_id"] == "D15" for e in l.events))
        p = {item["id"]: item for item in project_owner_decisions(l)["decisions"]}
        self.assertEqual(p["D15"]["state"], "PENDING")
        self.assertIsNone(p["D15"]["value"])
        self.assertTrue(p["D15"]["contract_complete"])
        self.assertEqual(p["D6"]["state"], "APPROVED")
        self.assertEqual(p["D8"]["state"], "APPROVED")
        self.assertEqual(p["D10"]["state"], "APPROVED")
        questions = (ROOT / "icm/MG8PK/OWNER_QUESTIONS.md").read_text("utf-8")
        self.assertIn("Answered, not approved", questions)
        self.assertIn("FbncSqnc", questions)

    def test_v315_q2_addendum_stays_on_same_field(self):
        self.assertEqual(REAL315["catalog_version"], "3.15")
        for a, b in zip(REAL314["decisions"], REAL315["decisions"]):
            if a["id"] != "D15":
                self.assertEqual(a, b)
        old = next(d for d in REAL314["decisions"] if d["id"] == "D15")
        new = next(d for d in REAL315["decisions"] if d["id"] == "D15")
        self.assertEqual(new["contract"]["gestalt_id_abbreviation"], old["contract"]["gestalt_id_abbreviation"])
        self.assertEqual(new["contract"]["thresholds"], old["contract"]["thresholds"])
        self.assertEqual(new["contract"]["reporting"], old["contract"]["reporting"])
        text = new["contract"]["interlinear_annotation"]["recommended"]
        self.assertFalse(new["contract"]["interlinear_annotation"]["owner_input_required"])
        first = "(domain=building_subdom=carpentry)(modalityOp=kine-int)(past-t)"
        second = "(pronoun)(modOp=kine-ext)(object=gestalt)(object_k=gestalt)"
        self.assertLess(text.index(first), text.index(second))
        self.assertIn('"he took the bump of k" also gets tags', text)
        self.assertIn("he took the bump of k\n", text)
        self.assertIn('"he" maps to (pronoun)', text)
        self.assertIn("which spelling is canonical is open", text)
        self.assertIn("whether that is the convention is open", text)
        self.assertNotIn('whether "he took the bump of k" gets tags', text)
        fixtures = json.loads((ROOT / "nych_preview/fixtures/interlinear_examples.json").read_text())
        self.assertEqual(fixtures[0]["id"], "full-sentence")
        self.assertEqual(fixtures[0]["role"], "first")
        self.assertIn(fixtures[0]["annotation"], text)
        self.assertIn(fixtures[0]["base"], text)
        self.assertIn(fixtures[1]["base"], text)
        l = _stack()
        self.assertFalse(any(e["decision_id"] == "D15" for e in l.events))
        p = {item["id"]: item for item in project_owner_decisions(l)["decisions"]}
        self.assertEqual(p["D15"]["state"], "PENDING")
        self.assertIsNone(p["D15"]["value"])


if __name__ == "__main__":
    unittest.main()
