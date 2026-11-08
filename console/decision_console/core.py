"""MG8 Model Builder Decision Console -- OFFLINE CORE / EXPORT PROTOTYPE.

Scope: an in-process event model plus deterministic file exports. There is
no UI yet, no network, provider, database, or build-launch side effect, and
readiness output is advisory only (``readiness_authoritative`` is always
False in this prototype). Nothing here may be used to launch builders.

Rules (handoff section 6):
- Events are immutable and append-only; a later choice supersedes the prior
  head via a new event. History is never rewritten.
- A decision is approvable only when its catalog contract is structurally
  complete (every field has a recommended value and no field is marked
  owner-input-required). Incomplete decisions stay PENDING; bulk approval
  skips them and lists them visibly. No owner value is ever guessed.
- Catalog v3 adds cross-decision ``equals`` constraints and numeric
  ``maximum`` / ``step`` bounds (either may be null when no bound is
  documented). Recommendations must already satisfy those rules. An
  approval is rejected when it breaks a bound or disagrees with a peer
  already approved against the same definition. D14 stays owner-input
  text; this module does not invent a numeric size for it.
- Snapshots are oldest-first. The shipped D5 historical approval is bound
  to catalog v2. A later snapshot may expand that contract; the historical
  event is not rewritten and does not approve the new definition.
- "Approve all recommended" writes one event per decision; exceptions and
  skipped-incomplete IDs are listed in every event.
- Notes and rationales are free text and are STORED in events and in the
  owner-decisions export (not in QSON). They never change contract values.
  Do not put real prompt text or user examples in them: the forbidden-key
  filter is a tripwire for obvious mistakes, NOT a no-prompt-persistence
  guarantee.

Trust boundary: the hash chain detects modification, reordering, insertion
and deletion *inside* a log, but cannot detect tail truncation, and the
``owner`` field is an unauthenticated label. Completeness and authorship
must be established outside this module: pass an externally trusted
``expected_head`` / ``expected_count`` to ``DecisionLog.load`` and protect
the log with signed commits or equivalent.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from decimal import Decimal
from typing import Any, Iterable

SCHEMA_ID = "mg8.decision-event.v1"
CATALOG_SCHEMA_V2 = "mg8.decision-catalog.v2"
CATALOG_SCHEMA_V3 = "mg8.decision-catalog.v3"
CATALOG_SCHEMA_ID = CATALOG_SCHEMA_V2  # older snapshots; v3 is the current catalog
CATALOG_SCHEMA_IDS = frozenset({CATALOG_SCHEMA_V2, CATALOG_SCHEMA_V3})
_SCHEMA_RANK = {CATALOG_SCHEMA_V2: 2, CATALOG_SCHEMA_V3: 3}
PROJECTION_SCHEMA_ID = "owner-decisions.v1"
STATES = ("PENDING", "APPROVED", "REJECTED", "SUPERSEDED", "BLOCKED")
ACTIONS = ("APPROVE_RECOMMENDATION", "CHOOSE_OTHER", "LEAVE_PENDING", "REJECT", "BLOCK", "HISTORICAL_APPROVAL")
ACTION_TO_STATE = {
    "APPROVE_RECOMMENDATION": "APPROVED", "CHOOSE_OTHER": "APPROVED", "HISTORICAL_APPROVAL": "APPROVED",
    "LEAVE_PENDING": "PENDING", "REJECT": "REJECTED", "BLOCK": "BLOCKED",
}
EVENT_FIELDS = (
    "schema", "event_id", "seq", "decision_id", "action", "state", "value",
    "owner", "timestamp", "rationale", "note", "supersedes", "bulk_id",
    "bulk_exceptions", "bulk_skipped_incomplete", "catalog_digest", "prev_event_digest",
)
FORBIDDEN_KEYS = {"prompt", "raw_prompt", "user_example", "example_prompt"}
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
FIELD_KINDS = ("choice", "integer", "number", "text")
MAX_TEXT = 4000
# Module universe for conservative readiness. B1-B3 contracts (D2/D3 etc.)
# are not modeled in this console catalog, so they are always reported blocked.
MODULE_UNIVERSE = tuple(f"B{i}" for i in range(1, 12)) + ("INTEGRATION",)
UNMODELED_MODULES = frozenset({"B1", "B2", "B3"})  # D2/D3/ingest contracts live outside this catalog


class DecisionError(ValueError):
    pass


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_hex(obj: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(obj)).hexdigest()


def _is_int(v): return isinstance(v, int) and not isinstance(v, bool)
def _is_num(v): return (isinstance(v, (int, float)) and not isinstance(v, bool)) and v == v and v not in (float("inf"), float("-inf"))
def _is_str(v, allow_empty=True, maxlen=MAX_TEXT): return isinstance(v, str) and (allow_empty or v.strip() != "") and len(v) <= maxlen


def _reject_forbidden(obj: Any) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in FORBIDDEN_KEYS:
                raise DecisionError(f"forbidden key {k}")
            _reject_forbidden(v)
    elif isinstance(obj, list):
        for v in obj:
            _reject_forbidden(v)


# ------------------------------------------------------------------ catalog
def validate_catalog(catalog: Any) -> None:
    if not isinstance(catalog, dict) or catalog.get("schema") not in CATALOG_SCHEMA_IDS:
        raise DecisionError("catalog schema mismatch")
    v3 = catalog["schema"] == CATALOG_SCHEMA_V3
    top = {"schema", "catalog_version", "decisions"} | ({"cross_constraints"} if v3 else set())
    if set(catalog) != top:
        raise DecisionError("catalog top-level fields mismatch")
    if not _is_str(catalog["catalog_version"], False) or not isinstance(catalog["decisions"], list):
        raise DecisionError("catalog version/decisions invalid")
    req = {"id", "title", "question", "modules", "depends_on", "round", "contract", "constraints", "historical_approval", "sources"}
    seen = set()
    by_id = {}
    for d in catalog["decisions"]:
        if not isinstance(d, dict) or set(d) != req:
            raise DecisionError(f"decision fields mismatch: {d.get('id') if isinstance(d, dict) else d}")
        if not (_is_str(d["id"], False) and ID_RE.match(d["id"])) or d["id"] in seen:
            raise DecisionError(f"bad or duplicate decision id {d['id']!r}")
        seen.add(d["id"])
        by_id[d["id"]] = d
        for k in ("title", "question", "round"):
            if not _is_str(d[k], False):
                raise DecisionError(f"{d['id']}: {k} must be non-empty string")
        for k in ("modules", "depends_on", "sources"):
            if not isinstance(d[k], list) or not all(_is_str(x, False) for x in d[k]):
                raise DecisionError(f"{d['id']}: {k} must be list of strings")
        for m in d["modules"]:
            if m not in MODULE_UNIVERSE and m != "ALL":
                raise DecisionError(f"{d['id']}: unknown module {m}")
        c = d["contract"]
        if not isinstance(c, dict) or not c:
            raise DecisionError(f"{d['id']}: contract must be non-empty object")
        for fname, f in c.items():
            _validate_field_def(d["id"], fname, f, v3)
        if not isinstance(d["constraints"], list):
            raise DecisionError(f"{d['id']}: constraints must be list")
        for con in d["constraints"]:
            if not (isinstance(con, dict) and con.get("kind") == "product_equals" and set(con) == {"kind", "target", "factors"}
                    and con["target"] in c and isinstance(con["factors"], list) and len(con["factors"]) >= 2
                    and all(x in c and c[x]["kind"] == "integer" for x in con["factors"]) and c[con["target"]]["kind"] == "integer"):
                raise DecisionError(f"{d['id']}: invalid constraint")
        h = d["historical_approval"]
        if h is not None:
            if not (isinstance(h, dict) and set(h) == {"owner", "source_ref", "value"} and _is_str(h["owner"], False) and _is_str(h["source_ref"], False)):
                raise DecisionError(f"{d['id']}: invalid historical_approval")
            _validate_value(d, h["value"])
        _reject_forbidden(d)
    for d in catalog["decisions"]:
        for dep in d["depends_on"]:
            if dep not in seen or dep == d["id"]:
                raise DecisionError(f"{d['id']} depends on unknown/self {dep}")
    if v3:
        _validate_cross_defs(catalog, by_id)


def _validate_cross_defs(catalog: dict, by_id: dict) -> None:
    cons = catalog["cross_constraints"]
    if not isinstance(cons, list):
        raise DecisionError("cross_constraints must be a list")
    seen = set()
    for con in cons:
        if not (isinstance(con, dict) and set(con) == {"kind", "left", "right"} and con["kind"] == "equals"):
            raise DecisionError("invalid cross constraint")
        refs = []
        for side in ("left", "right"):
            ref = con[side]
            if not (isinstance(ref, dict) and set(ref) == {"decision", "field"} and ref["decision"] in by_id
                    and ref["field"] in by_id[ref["decision"]]["contract"]):
                raise DecisionError("cross constraint references unknown decision or field")
            refs.append(ref)
        left, right = refs
        if left["decision"] == right["decision"]:
            raise DecisionError("cross constraint must span two decisions")
        fl = by_id[left["decision"]]["contract"][left["field"]]
        fr = by_id[right["decision"]]["contract"][right["field"]]
        if fl["kind"] != fr["kind"]:
            raise DecisionError("cross constraint fields must share a kind")
        key = tuple(sorted(((left["decision"], left["field"]), (right["decision"], right["field"]))))
        if key in seen:
            raise DecisionError("duplicate cross constraint")
        seen.add(key)
        if fl["recommended"] is not None and fr["recommended"] is not None and fl["recommended"] != fr["recommended"]:
            raise DecisionError(
                f"cross-decision constraint violated by recommendations: "
                f"{left['decision']}.{left['field']} != {right['decision']}.{right['field']}")


def _bound_token_ok(kind: str, name: str, val: Any) -> bool:
    if val is None:
        return True
    if kind == "integer":
        good = _is_int(val)
    else:
        good = _is_num(val)
    if not good:
        return False
    return name != "step" or val > 0


def _validate_field_def(did, fname, f, v3=False):
    if not ID_RE.match(fname) or not isinstance(f, dict):
        raise DecisionError(f"{did}.{fname}: bad field")
    kind = f.get("kind")
    base = {"kind", "recommended", "owner_input_required", "unit"}
    extra = {"choice": {"options"}, "integer": {"minimum"}, "number": {"minimum"}, "text": set()}.get(kind)
    if extra is None:
        raise DecisionError(f"{did}.{fname}: field keys mismatch for kind {kind}")
    if v3 and kind in ("integer", "number"):
        extra = set(extra) | {"maximum", "step"}
    if set(f) != base | extra:
        raise DecisionError(f"{did}.{fname}: field keys mismatch for kind {kind}")
    if not isinstance(f["owner_input_required"], bool) or not (f["unit"] is None or _is_str(f["unit"], False)):
        raise DecisionError(f"{did}.{fname}: bad flags")
    if kind == "choice" and not (isinstance(f["options"], list) and len(f["options"]) >= 1 and all(_is_str(o, False) for o in f["options"])):
        raise DecisionError(f"{did}.{fname}: bad options")
    if kind in ("integer", "number"):
        if v3:
            for name in ("minimum", "maximum", "step"):
                if not _bound_token_ok(kind, name, f[name]):
                    raise DecisionError(f"{did}.{fname}: bad {name}")
            lo, hi = f["minimum"], f["maximum"]
            if lo is not None and hi is not None and lo > hi:
                raise DecisionError(f"{did}.{fname}: minimum exceeds maximum")
        elif not (f["minimum"] is None or _is_num(f["minimum"])):
            raise DecisionError(f"{did}.{fname}: bad minimum")
    if f["owner_input_required"] and f["recommended"] is not None:
        raise DecisionError(f"{did}.{fname}: owner-input field must not carry a guessed recommendation")
    if f["recommended"] is not None:
        _validate_field_value(did, fname, f, f["recommended"])


def _within_bounds(f, v) -> bool:
    lo, hi = f.get("minimum"), f.get("maximum")
    if lo is not None and v < lo:
        return False
    if hi is not None and v > hi:
        return False
    return True


def _on_step(kind, f, v) -> bool:
    step = f.get("step")
    if step is None:
        return True
    origin = f.get("minimum")
    origin = 0 if origin is None else origin
    if kind == "integer":
        return _is_int(step) and step > 0 and (v - origin) % step == 0
    if not (_is_num(step) and step > 0):
        return False
    q = (Decimal(str(v)) - Decimal(str(origin))) / Decimal(str(step))
    return q == q.to_integral_value()


def _validate_field_value(did, fname, f, v):
    k = f["kind"]
    ok = ((k == "choice" and v in f["options"]) or
          (k == "integer" and _is_int(v) and _within_bounds(f, v) and _on_step(k, f, v)) or
          (k == "number" and _is_num(v) and _within_bounds(f, v) and _on_step(k, f, v)) or
          (k == "text" and _is_str(v, False)))
    if not ok:
        raise DecisionError(f"{did}.{fname}: invalid value")


def _assert_cross_consistent(catalog: dict, values_by_id: dict) -> None:
    """Reject a joint assignment that breaks a catalog ``equals`` constraint.

    Sides with no committed value are skipped. Both sides present must match.
    """
    for con in catalog.get("cross_constraints", []):
        left, right = con["left"], con["right"]
        if left["decision"] not in values_by_id or right["decision"] not in values_by_id:
            continue
        lv = values_by_id[left["decision"]][left["field"]]
        rv = values_by_id[right["decision"]][right["field"]]
        if lv != rv:
            raise DecisionError(
                f"cross-decision constraint violated: {left['decision']}.{left['field']} ({lv!r}) "
                f"must equal {right['decision']}.{right['field']} ({rv!r})")


def is_complete(decision: dict) -> bool:
    return all(not f["owner_input_required"] and f["recommended"] is not None for f in decision["contract"].values())


def recommended_value(decision: dict) -> dict | None:
    return {k: f["recommended"] for k, f in decision["contract"].items()} if is_complete(decision) else None


def _validate_value(decision: dict, value: Any) -> None:
    did = decision["id"]
    # CHOOSE_OTHER may fill owner-input fields: that is an explicit owner value, not a guess.
    if not isinstance(value, dict) or set(value) != set(decision["contract"]):
        raise DecisionError(f"{did}: value must be an object with exactly the contract fields")
    for k, f in decision["contract"].items():
        _validate_field_value(did, k, f, value[k])
    for con in decision["constraints"]:
        prod = 1
        for x in con["factors"]:
            prod *= value[x]
        if value[con["target"]] != prod:
            raise DecisionError(f"{did}: constraint {con['target']} = product({','.join(con['factors'])}) violated")
    _reject_forbidden(value)


def catalog_digest(catalog: dict) -> str:
    return sha256_hex(catalog)


def decision_digest(decision: dict) -> str:
    return sha256_hex(decision)


# ------------------------------------------------------------------ events
def _validate_event_shape(e: Any) -> None:
    if not isinstance(e, dict) or set(e) != set(EVENT_FIELDS):
        raise DecisionError("event fields mismatch")
    checks = {
        "schema": e["schema"] == SCHEMA_ID,
        "event_id": isinstance(e["event_id"], str) and bool(DIGEST_RE.match(e["event_id"])),
        "seq": _is_int(e["seq"]) and e["seq"] >= 0,
        "decision_id": _is_str(e["decision_id"], False),
        "action": e["action"] in ACTIONS,
        "state": e["state"] in ("PENDING", "APPROVED", "REJECTED", "BLOCKED"),
        "owner": _is_str(e["owner"], False, 200),
        "timestamp": isinstance(e["timestamp"], str) and bool(TS_RE.match(e["timestamp"])),
        "rationale": _is_str(e["rationale"]),
        "note": _is_str(e["note"]),
        "supersedes": e["supersedes"] is None or (isinstance(e["supersedes"], str) and bool(DIGEST_RE.match(e["supersedes"]))),
        "bulk_id": e["bulk_id"] is None or (isinstance(e["bulk_id"], str) and bool(DIGEST_RE.match(e["bulk_id"]))),
        "bulk_exceptions": isinstance(e["bulk_exceptions"], list) and all(_is_str(x, False) for x in e["bulk_exceptions"]) and e["bulk_exceptions"] == sorted(set(e["bulk_exceptions"])),
        "bulk_skipped_incomplete": isinstance(e["bulk_skipped_incomplete"], list) and all(_is_str(x, False) for x in e["bulk_skipped_incomplete"]) and e["bulk_skipped_incomplete"] == sorted(set(e["bulk_skipped_incomplete"])),
        "catalog_digest": isinstance(e["catalog_digest"], str) and bool(DIGEST_RE.match(e["catalog_digest"])),
        "prev_event_digest": e["prev_event_digest"] is None or (isinstance(e["prev_event_digest"], str) and bool(DIGEST_RE.match(e["prev_event_digest"]))),
    }
    bad = [k for k, ok in checks.items() if not ok]
    if bad:
        raise DecisionError(f"event field types invalid: {bad}")
    if ACTION_TO_STATE[e["action"]] != e["state"]:
        raise DecisionError("action/state mismatch")
    if e["bulk_id"] is None and (e["bulk_exceptions"] or e["bulk_skipped_incomplete"]):
        raise DecisionError("bulk lists require bulk_id")
    _reject_forbidden(e)


class DecisionLog:
    """Encapsulated log. All accessors return deep copies; every export re-verifies."""

    def __init__(self, catalogs: list, _events: list | None = None):
        if not isinstance(catalogs, list) or not catalogs:
            raise DecisionError("catalogs must be a non-empty list of snapshots (oldest first)")
        snaps = [copy.deepcopy(c) for c in catalogs]
        for c in snaps:
            validate_catalog(c)
        digests = [catalog_digest(c) for c in snaps]
        if len(set(digests)) != len(digests):
            raise DecisionError("duplicate catalog snapshot")
        ranks = [_SCHEMA_RANK[c["schema"]] for c in snaps]
        if any(a > b for a, b in zip(ranks, ranks[1:])):
            raise DecisionError("catalog snapshots must be oldest first")
        self.__catalogs = snaps
        self.__digests = digests
        self.__events: list = []

    # -- construction
    @classmethod
    def new(cls, catalog_or_snapshots) -> "DecisionLog":
        return cls(catalog_or_snapshots if isinstance(catalog_or_snapshots, list) else [catalog_or_snapshots])

    @classmethod
    def load(cls, catalog_or_snapshots, events: Iterable[dict], *, expected_head: str | None = None,
             expected_count: int | None = None) -> "DecisionLog":
        log = cls.new(catalog_or_snapshots)
        for e in events:
            log._append(copy.deepcopy(e), allow_historical=True)
        if expected_count is not None and len(log.__events) != expected_count:
            raise DecisionError("event count differs from externally trusted expected_count (truncation?)")
        if expected_head is not None and log.head() != expected_head:
            raise DecisionError("log head differs from externally trusted expected_head (truncation?)")
        return log

    # -- read-only views
    @property
    def catalog(self) -> dict:
        return copy.deepcopy(self.__catalogs[-1])

    @property
    def catalogs(self) -> list:
        return copy.deepcopy(self.__catalogs)

    @property
    def events(self) -> list:
        return copy.deepcopy(self.__events)

    def head(self) -> str | None:
        return self.__events[-1]["event_id"] if self.__events else None

    def _decision(self, did: str, snapshot: int = -1) -> dict:
        for d in self.__catalogs[snapshot]["decisions"]:
            if d["id"] == did:
                return d
        raise DecisionError(f"unknown decision {did} in catalog snapshot")

    def _head_event(self, did: str) -> dict | None:
        superseded = {e["supersedes"] for e in self.__events if e["supersedes"]}
        heads = [e for e in self.__events if e["decision_id"] == did and e["event_id"] not in superseded]
        if len(heads) > 1:
            raise DecisionError("forked decision history")
        return heads[0] if heads else None

    # -- core append
    def _append(self, e: dict, allow_historical: bool) -> None:
        _validate_event_shape(e)
        if e["seq"] != len(self.__events):
            raise DecisionError("sequence gap or reorder")
        if e["prev_event_digest"] != self.head():
            raise DecisionError("hash chain broken")
        if e["catalog_digest"] not in self.__digests:
            raise DecisionError("event references unknown catalog snapshot")
        snap = self.__digests.index(e["catalog_digest"])
        if self.__events and snap < self.__digests.index(self.__events[-1]["catalog_digest"]):
            raise DecisionError("catalog snapshot went backwards")
        d = self._decision(e["decision_id"], snap)
        head = self._head_event(e["decision_id"])
        if e["supersedes"] != (head["event_id"] if head else None):
            raise DecisionError("supersedes must reference current head")
        if e["action"] == "HISTORICAL_APPROVAL":
            h = d["historical_approval"]
            if not allow_historical or h is None or head is not None or e["value"] != h["value"] or e["owner"] != h["owner"] or e["bulk_id"] is not None:
                raise DecisionError("historical approval only importable once, as declared in the catalog")
            self._check_approval_cross(snap, e["decision_id"], e["value"])
        elif e["state"] == "APPROVED":
            _validate_value(d, e["value"])
            self._check_approval_cross(snap, e["decision_id"], e["value"])
            if e["action"] == "APPROVE_RECOMMENDATION":
                rv = recommended_value(d)
                if rv is None:
                    raise DecisionError(f"{d['id']}: contract incomplete; cannot approve recommendation")
                if e["value"] != rv:
                    raise DecisionError("approve-recommendation value differs from recommendation")
        elif e["value"] is not None:
            raise DecisionError("non-approved event must not carry a value")
        if e["bulk_id"] is not None and e["action"] != "APPROVE_RECOMMENDATION":
            raise DecisionError("bulk events must be APPROVE_RECOMMENDATION")
        body = {k: v for k, v in e.items() if k != "event_id"}
        if e["event_id"] != sha256_hex(body):
            raise DecisionError("event digest mismatch")
        self.__events.append(e)

    def _build(self, decision_id, action, owner, timestamp, value, rationale, note, bulk_id=None, exc=(), skipped=()):
        self._decision(decision_id)
        head = self._head_event(decision_id)
        body = {
            "schema": SCHEMA_ID, "seq": len(self.__events), "decision_id": decision_id, "action": action,
            "state": ACTION_TO_STATE.get(action, "?"), "value": copy.deepcopy(value), "owner": owner,
            "timestamp": timestamp, "rationale": rationale, "note": note,
            "supersedes": head["event_id"] if head else None, "bulk_id": bulk_id,
            "bulk_exceptions": sorted(set(exc)), "bulk_skipped_incomplete": sorted(set(skipped)),
            "catalog_digest": self.__digests[-1], "prev_event_digest": self.head(),
        }
        try:
            eid = sha256_hex(body)
        except (TypeError, ValueError) as err:
            raise DecisionError(f"event not JSON-serializable: {err}")
        return dict(body, event_id=eid)

    # -- writers (normal recording cannot mint historical approvals)
    def record(self, decision_id: str, action: str, *, owner: str, timestamp: str, value: Any = None,
               rationale: str = "", note: str = "") -> dict:
        if action == "HISTORICAL_APPROVAL":
            raise DecisionError("use import_historical(); normal recording cannot mint historical approvals")
        if action not in ACTIONS:
            raise DecisionError("unknown action")
        if action == "APPROVE_RECOMMENDATION":
            value = recommended_value(self._decision(decision_id))
            if value is None:
                raise DecisionError(f"{decision_id}: contract incomplete; cannot approve recommendation")
        elif ACTION_TO_STATE[action] != "APPROVED" and value is not None:
            raise DecisionError("value only allowed for approvals")
        e = self._build(decision_id, action, owner, timestamp, value, rationale, note)
        self._append(e, allow_historical=False)
        return copy.deepcopy(e)

    def import_historical(self, decision_id: str, *, timestamp: str, rationale: str) -> dict:
        d = self._decision(decision_id)
        h = d["historical_approval"]
        if h is None:
            raise DecisionError(f"{decision_id}: no historical approval declared in catalog")
        e = self._build(decision_id, "HISTORICAL_APPROVAL", h["owner"], timestamp, h["value"], rationale, "source: " + h["source_ref"])
        self._append(e, allow_historical=True)
        return copy.deepcopy(e)

    def approve_all_recommended(self, *, owner: str, timestamp: str, exceptions: Iterable[str] = (),
                                rationale: str = "bulk approve recommended") -> dict:
        """One event per PENDING, contract-complete decision. Exceptions and
        incomplete decisions stay PENDING and are listed in every event."""
        if isinstance(exceptions, str):
            raise DecisionError("exceptions must be a collection of IDs")
        exc = sorted(set(exceptions))
        for x in exc:
            self._decision(x)
        # Decisions with a declared historical approval are imported via import_historical(), never bulk-approved.
        pend = [d for d in self.__catalogs[-1]["decisions"] if d["id"] not in exc and self.state(d["id"]) == "PENDING"
                and d["historical_approval"] is None]
        skipped = sorted(d["id"] for d in pend if not is_complete(d))
        targets = [d["id"] for d in pend if is_complete(d)]
        planned = {}
        for dec in self.__catalogs[-1]["decisions"]:
            cv = self._committed_value(dec["id"], -1)
            if cv is not None:
                planned[dec["id"]] = cv
        for t in targets:
            planned[t] = recommended_value(self._decision(t))
        _assert_cross_consistent(self.__catalogs[-1], planned)
        bulk_id = sha256_hex({"owner": owner, "timestamp": timestamp, "targets": targets, "exceptions": exc,
                              "skipped": skipped, "head": self.head()})
        made = []
        for t in targets:
            e = self._build(t, "APPROVE_RECOMMENDATION", owner, timestamp, recommended_value(self._decision(t)),
                            rationale, "", bulk_id, exc, skipped)
            self._append(e, allow_historical=False)
            made.append(copy.deepcopy(e))
        return {"events": made, "exceptions": exc, "skipped_incomplete": skipped}

    # -- readers
    def state(self, decision_id: str) -> str:
        self._decision(decision_id)
        h = self._head_event(decision_id)
        return h["state"] if h else "PENDING"

    def _effective(self, did: str) -> dict:
        """State plus whether the head was recorded against the current decision definition."""
        h = self._head_event(did)
        cur = self._decision(did)
        if h is None:
            return {"state": "PENDING", "current_definition": True}
        snap = self.__digests.index(h["catalog_digest"])
        try:
            old = self._decision(did, snap)
        except DecisionError:
            old = None
        return {"state": h["state"], "current_definition": old is not None and decision_digest(old) == decision_digest(cur)}

    def _satisfied(self, did: str) -> bool:
        eff = self._effective(did)
        return eff["state"] == "APPROVED" and eff["current_definition"]

    def _check_approval_cross(self, snap: int, did: str, value: dict) -> None:
        committed = {}
        for dec in self.__catalogs[snap]["decisions"]:
            cv = self._committed_value(dec["id"], snap)
            if cv is not None:
                committed[dec["id"]] = cv
        committed[did] = value
        _assert_cross_consistent(self.__catalogs[snap], committed)

    def _committed_value(self, did: str, snap_index: int):
        """Approved value for ``did`` only when that approval matches the definition at ``snap_index``.

        A stale approval (recorded against an older decision digest) does not constrain new approvals
        and does not count as the current contract. ``None`` means no committed peer value.
        """
        h = self._head_event(did)
        if h is None or h["state"] != "APPROVED" or h["value"] is None:
            return None
        hsnap = self.__digests.index(h["catalog_digest"])
        try:
            old = self._decision(did, hsnap)
            cur = self._decision(did, snap_index)
        except DecisionError:
            return None
        if decision_digest(old) != decision_digest(cur):
            return None
        return h["value"]

    def readiness(self) -> dict:
        """Conservative, NON-AUTHORITATIVE gate. A module is blocked unless
        every decision naming it (or ALL), plus their dependency closure, is
        APPROVED against the current definition, and the module's contracts
        are modeled here at all (B1-B3 are not)."""
        cat = self.__catalogs[-1]["decisions"]
        out = {}
        for m in MODULE_UNIVERSE:
            rel = [d["id"] for d in cat if m in d["modules"] or "ALL" in d["modules"]]
            reasons = set()
            if m in UNMODELED_MODULES or not any(m in d["modules"] for d in cat):
                reasons.add("CONTRACT_NOT_MODELED_IN_CONSOLE")
            for did in rel:
                for x in self._closure(did, set()):
                    if not self._satisfied(x):
                        reasons.add(x)
            out[m] = sorted(reasons)
        return {"readiness_authoritative": False,
                "note": "Advisory only. Do not launch builders from this output.",
                "blocked": {m: r for m, r in out.items() if r},
                "unblocked_advisory": sorted(m for m, r in out.items() if not r)}

    def blocked_builders(self) -> dict:
        return self.readiness()["blocked"]

    def _closure(self, did, seen):
        if did in seen:
            return seen
        seen.add(did)
        for dep in self._decision(did)["depends_on"]:
            self._closure(dep, seen)
        return seen

    def event_state(self, event_id: str) -> str:
        superseded = {e["supersedes"] for e in self.__events if e["supersedes"]}
        for e in self.__events:
            if e["event_id"] == event_id:
                return "SUPERSEDED" if event_id in superseded else e["state"]
        raise DecisionError("unknown event")

    def _reverified(self) -> "DecisionLog":
        return DecisionLog.load(self.catalogs, self.events, expected_head=self.head(), expected_count=len(self.__events))


# ------------------------------------------------------------------ projections
def project_owner_decisions(log: DecisionLog) -> dict:
    v = log._reverified()
    cat = v.catalog
    decisions = []
    for d in cat["decisions"]:
        h = v._head_event(d["id"])
        eff = v._effective(d["id"])
        decisions.append({
            "id": d["id"], "title": d["title"], "modules": d["modules"],
            "contract_complete": is_complete(d),
            "owner_input_required": sorted(k for k, f in d["contract"].items() if f["owner_input_required"]),
            "numeric_bounds": {k: {b: f[b] for b in ("minimum", "maximum", "step") if b in f}
                               for k, f in d["contract"].items() if f["kind"] in ("integer", "number")},
            "state": eff["state"], "recorded_against_current_definition": eff["current_definition"],
            "value": copy.deepcopy(h["value"]) if h else None,
            "recommended": recommended_value(d),
            "head_event": h["event_id"] if h else None,
            "owner_label_unauthenticated": h["owner"] if h else None,
            "timestamp": h["timestamp"] if h else None,
            "rationale": h["rationale"] if h else None,
            "note": h["note"] if h else None,
            "history": [{"event_id": e["event_id"], "state": v.event_state(e["event_id"])}
                        for e in v.events if e["decision_id"] == d["id"]],
        })
    body = {"schema": PROJECTION_SCHEMA_ID, "catalog_digest": catalog_digest(cat),
            "catalog_snapshots": [catalog_digest(c) for c in v.catalogs],
            "cross_constraints": copy.deepcopy(cat.get("cross_constraints", [])),
            "log_head": v.head(), "event_count": len(v.events),
            "decisions": decisions, "readiness": v.readiness()}
    return dict(body, decision_set_digest=sha256_hex(body))


def md_escape(s: Any) -> str:
    s = s if isinstance(s, str) else json.dumps(s, ensure_ascii=False, sort_keys=True)
    s = s.replace("\\", "\\\\").replace("|", "\\|").replace("`", "\\`")
    return re.sub(r"[\r\n\u2028\u2029]+", " ", s)


def project_register_md(log: DecisionLog) -> str:
    p = project_owner_decisions(log)
    lines = ["# Owner Decision Register (generated projection, OFFLINE PROTOTYPE)", "",
             f"Decision-set digest: `{p['decision_set_digest']}`", "",
             "Generated from the decision event log. Do not edit by hand. Readiness below is advisory, not authoritative.", "",
             "| ID | Title | State | Contract | Value | Recommended | Head event |", "|---|---|---|---|---|---|---|"]
    for d in p["decisions"]:
        state = d["state"]
        if state == "PENDING":
            state += " (Recommended—awaiting owner approval)" if d["contract_complete"] else " (owner input required)"
        if not d["recorded_against_current_definition"]:
            state += " [definition changed; reconfirm]"
        contract = "complete" if d["contract_complete"] else "INCOMPLETE: " + ", ".join(d["owner_input_required"])
        val = "" if d["value"] is None else d["value"]
        rec = "" if d["recommended"] is None else d["recommended"]
        lines.append("| " + " | ".join(md_escape(x) for x in [d["id"], d["title"], state, contract, val, rec, (d["head_event"] or "")[:19]]) + " |")
    lines += ["", "## Cross-decision constraints", ""]
    if p["cross_constraints"]:
        for con in p["cross_constraints"]:
            left, right = con["left"], con["right"]
            lines.append(f"- {md_escape(left['decision'])}.{md_escape(left['field'])} = {md_escape(right['decision'])}.{md_escape(right['field'])}")
    else:
        lines.append("- none")
    lines += ["", "## Numeric bounds (current catalog)", ""]
    any_bounds = False
    for d in p["decisions"]:
        for fname, b in d["numeric_bounds"].items():
            any_bounds = True
            parts = [f"{name} {json.dumps(b[name])}" for name in ("minimum", "maximum", "step") if name in b]
            lines.append("- " + md_escape(f"{d['id']}.{fname}: " + ", ".join(parts)))
    if not any_bounds:
        lines.append("- none")
    lines += ["", "## Blocked modules (advisory)", ""]
    for m, ds in p["readiness"]["blocked"].items():
        lines.append(f"- {md_escape(m)}: {md_escape(', '.join(ds))}")
    return "\n".join(lines) + "\n"


def project_qson_events(log: DecisionLog) -> list:
    """Metadata only: no values, notes, rationales, prompts or examples."""
    v = log._reverified()
    return [{"schema": "qson.decision-event.v1", "event_id": e["event_id"], "seq": e["seq"],
             "decision_id": e["decision_id"], "state": e["state"], "owner": e["owner"],
             "timestamp": e["timestamp"], "supersedes": e["supersedes"], "bulk_id": e["bulk_id"]}
            for e in v.events]
