"""Core event model for the MG8 Model Builder Decision Console.

Rules (handoff section 6):
- Events are immutable and append-only; editing creates a new event that
  supersedes the prior one (never rewrite history).
- Viewing or omitting a decision is never approval; defaults stay PENDING.
- "Approve all recommended" emits one event per decision; exceptions are
  listed visibly in each event and left untouched.
- Free-text notes never change contract values.
- Projections (owner-decisions JSON, register markdown, QSON metadata) are
  deterministic functions of the event log.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable

SCHEMA_ID = "mg8.decision-event.v1"
CATALOG_SCHEMA_ID = "mg8.decision-catalog.v1"
PROJECTION_SCHEMA_ID = "owner-decisions.v1"
STATES = ("PENDING", "APPROVED", "REJECTED", "SUPERSEDED", "BLOCKED")
ACTIONS = ("APPROVE_RECOMMENDATION", "CHOOSE_OTHER", "LEAVE_PENDING", "REJECT", "BLOCK", "HISTORICAL_APPROVAL")
ACTION_TO_STATE = {
    "APPROVE_RECOMMENDATION": "APPROVED",
    "CHOOSE_OTHER": "APPROVED",
    "HISTORICAL_APPROVAL": "APPROVED",
    "LEAVE_PENDING": "PENDING",
    "REJECT": "REJECTED",
    "BLOCK": "BLOCKED",
}
EVENT_FIELDS = (
    "schema", "event_id", "seq", "decision_id", "action", "state", "value",
    "owner", "timestamp", "rationale", "note", "supersedes", "bulk_id",
    "bulk_exceptions", "catalog_digest", "prev_event_digest",
)
FORBIDDEN_KEYS = {"prompt", "raw_prompt", "user_example", "example_prompt"}


class DecisionError(ValueError):
    pass


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def sha256_hex(obj: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(obj)).hexdigest()


# ---------------------------------------------------------------- catalog
def validate_catalog(catalog: dict) -> None:
    if catalog.get("schema") != CATALOG_SCHEMA_ID:
        raise DecisionError("catalog schema mismatch")
    seen = set()
    for d in catalog.get("decisions", []):
        for k in ("id", "title", "question", "modules", "depends_on", "control", "recommended", "round"):
            if k not in d:
                raise DecisionError(f"decision missing {k}: {d.get('id')}")
        if d["id"] in seen:
            raise DecisionError(f"duplicate decision id {d['id']}")
        seen.add(d["id"])
        _validate_value(d, d["recommended"])
        for alt in d.get("alternatives", []):
            _validate_value(d, alt)
    for d in catalog["decisions"]:
        for dep in d["depends_on"]:
            if dep not in seen:
                raise DecisionError(f"{d['id']} depends on unknown {dep}")


def _validate_value(decision: dict, value: Any) -> None:
    c = decision["control"]
    kind = c.get("kind")
    if kind == "choice":
        if value not in c["options"]:
            raise DecisionError(f"{decision['id']}: value not in options")
    elif kind == "numeric":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise DecisionError(f"{decision['id']}: numeric value required")
        lo, hi, step = c["min"], c["max"], c["step"]
        if not (lo <= value <= hi):
            raise DecisionError(f"{decision['id']}: value out of range [{lo},{hi}] {c.get('unit','')}")
        if abs(((value - lo) / step) - round((value - lo) / step)) > 1e-9:
            raise DecisionError(f"{decision['id']}: value not on step {step}")
    elif kind == "text_contract":
        if not isinstance(value, str) or not value.strip():
            raise DecisionError(f"{decision['id']}: contract text required")
    else:
        raise DecisionError(f"{decision['id']}: unknown control kind {kind}")


def catalog_digest(catalog: dict) -> str:
    return sha256_hex(catalog)


# ---------------------------------------------------------------- log
@dataclass
class DecisionLog:
    catalog: dict
    events: list

    @classmethod
    def new(cls, catalog: dict) -> "DecisionLog":
        validate_catalog(catalog)
        return cls(catalog=catalog, events=[])

    @classmethod
    def load(cls, catalog: dict, events: Iterable[dict]) -> "DecisionLog":
        log = cls.new(catalog)
        for e in events:
            log._verify_and_append(dict(e))
        return log

    # -- helpers
    def _decision(self, did: str) -> dict:
        for d in self.catalog["decisions"]:
            if d["id"] == did:
                return d
        raise DecisionError(f"unknown decision {did}")

    def _head(self, did: str) -> dict | None:
        superseded = {e["supersedes"] for e in self.events if e["supersedes"]}
        heads = [e for e in self.events if e["decision_id"] == did and e["event_id"] not in superseded]
        return heads[-1] if heads else None

    def _verify_and_append(self, e: dict) -> None:
        if set(e) != set(EVENT_FIELDS):
            raise DecisionError("event fields mismatch")
        if e["schema"] != SCHEMA_ID:
            raise DecisionError("event schema mismatch")
        if e["seq"] != len(self.events):
            raise DecisionError("sequence gap or reorder")
        expected_prev = self.events[-1]["event_id"] if self.events else None
        if e["prev_event_digest"] != expected_prev:
            raise DecisionError("hash chain broken")
        if e["catalog_digest"] != catalog_digest(self.catalog):
            raise DecisionError("catalog digest mismatch")
        if e["action"] not in ACTIONS or ACTION_TO_STATE[e["action"]] != e["state"]:
            raise DecisionError("action/state mismatch")
        if not e["owner"] or not e["timestamp"]:
            raise DecisionError("owner and timestamp required")
        _reject_forbidden(e)
        d = self._decision(e["decision_id"])
        head = self._head(e["decision_id"])
        if e["supersedes"] != (head["event_id"] if head else None):
            raise DecisionError("supersedes must reference current head")
        if e["state"] == "APPROVED":
            _validate_value(d, e["value"])
            if e["action"] == "APPROVE_RECOMMENDATION" and e["value"] != d["recommended"]:
                raise DecisionError("approve-recommendation value differs from recommendation")
        elif e["value"] is not None:
            raise DecisionError("non-approved event must not carry a value")
        body = {k: v for k, v in e.items() if k != "event_id"}
        if e["event_id"] != sha256_hex(body):
            raise DecisionError("event digest mismatch")
        self.events.append(e)

    # -- writers
    def record(self, decision_id: str, action: str, *, owner: str, timestamp: str,
               value: Any = None, rationale: str = "", note: str = "",
               bulk_id: str | None = None, bulk_exceptions: list | None = None) -> dict:
        d = self._decision(decision_id)
        if action == "APPROVE_RECOMMENDATION":
            value = d["recommended"]
        if ACTION_TO_STATE.get(action) != "APPROVED":
            value = None
        head = self._head(decision_id)
        body = {
            "schema": SCHEMA_ID, "seq": len(self.events), "decision_id": decision_id,
            "action": action, "state": ACTION_TO_STATE.get(action, "?"), "value": value,
            "owner": owner, "timestamp": timestamp, "rationale": rationale, "note": note,
            "supersedes": head["event_id"] if head else None, "bulk_id": bulk_id,
            "bulk_exceptions": sorted(bulk_exceptions or []),
            "catalog_digest": catalog_digest(self.catalog),
            "prev_event_digest": self.events[-1]["event_id"] if self.events else None,
        }
        e = dict(body, event_id=sha256_hex(body))
        self._verify_and_append(e)
        return e

    def approve_all_recommended(self, *, owner: str, timestamp: str, exceptions: Iterable[str] = (),
                                rationale: str = "bulk approve recommended") -> list:
        """One event per currently-PENDING decision; exceptions stay untouched and listed."""
        exc = sorted(set(exceptions))
        for x in exc:
            self._decision(x)
        targets = [d["id"] for d in self.catalog["decisions"]
                   if d["id"] not in exc and self.state(d["id"]) == "PENDING"]
        bulk_id = sha256_hex({"owner": owner, "timestamp": timestamp, "targets": targets, "exceptions": exc})
        return [self.record(t, "APPROVE_RECOMMENDATION", owner=owner, timestamp=timestamp,
                            rationale=rationale, bulk_id=bulk_id, bulk_exceptions=exc) for t in targets]

    # -- readers
    def state(self, decision_id: str) -> str:
        head = self._head(decision_id)
        return head["state"] if head else "PENDING"

    def event_state(self, event: dict) -> str:
        superseded = {e["supersedes"] for e in self.events if e["supersedes"]}
        return "SUPERSEDED" if event["event_id"] in superseded else event["state"]

    def blocked_builders(self) -> dict:
        """Map module -> list of non-approved decisions it depends on."""
        out: dict = {}
        for d in self.catalog["decisions"]:
            chain = self._closure(d["id"])
            open_ = sorted(x for x in chain if self.state(x) != "APPROVED")
            for m in d["modules"]:
                if open_:
                    out.setdefault(m, set()).update(open_)
        return {k: sorted(v) for k, v in sorted(out.items())}

    def _closure(self, did: str, seen=None) -> set:
        seen = set() if seen is None else seen
        if did in seen:
            return seen
        seen.add(did)
        for dep in self._decision(did)["depends_on"]:
            self._closure(dep, seen)
        return seen


def _reject_forbidden(obj: Any) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in FORBIDDEN_KEYS:
                raise DecisionError(f"forbidden key {k}")
            _reject_forbidden(v)
    elif isinstance(obj, list):
        for v in obj:
            _reject_forbidden(v)


# ---------------------------------------------------------------- projections
def project_owner_decisions(log: DecisionLog) -> dict:
    decisions = []
    for d in log.catalog["decisions"]:
        head = log._head(d["id"])
        decisions.append({
            "id": d["id"], "title": d["title"], "modules": d["modules"],
            "state": head["state"] if head else "PENDING",
            "value": head["value"] if head else None,
            "recommended": d["recommended"],
            "head_event": head["event_id"] if head else None,
            "owner": head["owner"] if head else None,
            "timestamp": head["timestamp"] if head else None,
            "history": [{"event_id": e["event_id"], "state": log.event_state(e)}
                        for e in log.events if e["decision_id"] == d["id"]],
        })
    body = {
        "schema": PROJECTION_SCHEMA_ID,
        "catalog_digest": catalog_digest(log.catalog),
        "log_head": log.events[-1]["event_id"] if log.events else None,
        "decisions": decisions,
        "blocked_modules": log.blocked_builders(),
    }
    return dict(body, decision_set_digest=sha256_hex(body))


def project_register_md(log: DecisionLog) -> str:
    p = project_owner_decisions(log)
    lines = ["# Owner Decision Register (generated projection)", "",
             f"Decision-set digest: `{p['decision_set_digest']}`", "",
             "Generated from the decision event log. Do not edit by hand.", "",
             "| ID | Title | State | Value | Recommended | Head event |", "|---|---|---|---|---|---|"]
    for d in p["decisions"]:
        val = "" if d["value"] is None else json.dumps(d["value"], ensure_ascii=False)
        rec = json.dumps(d["recommended"], ensure_ascii=False)
        state = d["state"] if d["state"] != "PENDING" else "PENDING (Recommended—awaiting owner approval)"
        lines.append(f"| {d['id']} | {d['title']} | {state} | {val} | {rec} | {(d['head_event'] or '')[:19]} |")
    lines += ["", "## Blocked modules", ""]
    for m, ds in p["blocked_modules"].items():
        lines.append(f"- {m}: waiting on {', '.join(ds)}")
    return "\n".join(lines) + "\n"


def project_qson_events(log: DecisionLog) -> list:
    """Metadata-only: no values, notes, rationales, prompts, or examples."""
    return [{"schema": "qson.decision-event.v1", "event_id": e["event_id"], "seq": e["seq"],
             "decision_id": e["decision_id"], "state": e["state"], "owner": e["owner"],
             "timestamp": e["timestamp"], "supersedes": e["supersedes"], "bulk_id": e["bulk_id"]}
            for e in log.events]
