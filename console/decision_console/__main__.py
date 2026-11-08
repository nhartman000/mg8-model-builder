"""CLI: python -m decision_console <catalog.json> <events.jsonl> <outdir>  (offline)."""
import json, sys, pathlib
from .core import DecisionLog, project_owner_decisions, project_register_md, project_qson_events, canonical_json

def main(argv):
    cat = json.loads(pathlib.Path(argv[0]).read_text("utf-8"))
    p = pathlib.Path(argv[1])
    events = [json.loads(l) for l in p.read_text("utf-8").splitlines() if l.strip()] if p.exists() else []
    log = DecisionLog.load(cat, events)
    out = pathlib.Path(argv[2]); out.mkdir(parents=True, exist_ok=True)
    (out / "owner-decisions.v1.json").write_bytes(canonical_json(project_owner_decisions(log)) + b"\n")
    (out / "DECISION_REGISTER.generated.md").write_text(project_register_md(log), "utf-8")
    (out / "qson-decision-events.jsonl").write_text("".join(json.dumps(q, sort_keys=True) + "\n" for q in project_qson_events(log)), "utf-8")
    print(f"ok events={len(log.events)}")

if __name__ == "__main__":
    main(sys.argv[1:])
