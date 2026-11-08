"""CLI (offline export only; never launches builds):
python -m decision_console <events.jsonl> <outdir> <oldest_catalog.json> [<newer_snapshot.json> ...]
Optional env MG8_EXPECTED_HEAD / MG8_EXPECTED_COUNT: externally trusted completeness check."""
import json, os, sys, pathlib
from .core import DecisionLog, project_owner_decisions, project_register_md, project_qson_events, canonical_json

def main(argv):
    if len(argv) < 3:
        sys.exit(__doc__)
    p = pathlib.Path(argv[0])
    cats = [json.loads(pathlib.Path(a).read_text("utf-8")) for a in argv[2:]]
    events = [json.loads(l) for l in p.read_text("utf-8").splitlines() if l.strip()] if p.exists() else []
    cnt = os.environ.get("MG8_EXPECTED_COUNT")
    log = DecisionLog.load(cats, events, expected_head=os.environ.get("MG8_EXPECTED_HEAD") or None,
                           expected_count=int(cnt) if cnt else None)
    out = pathlib.Path(argv[1]); out.mkdir(parents=True, exist_ok=True)
    (out / "owner-decisions.v1.json").write_bytes(canonical_json(project_owner_decisions(log)) + b"\n")
    (out / "DECISION_REGISTER.generated.md").write_text(project_register_md(log), "utf-8")
    (out / "qson-decision-events.jsonl").write_text("".join(json.dumps(q, sort_keys=True) + "\n" for q in project_qson_events(log)), "utf-8")
    print(f"ok events={len(log.events)} head={log.head()}")

if __name__ == "__main__":
    main(sys.argv[1:])
