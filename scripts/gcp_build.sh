#!/usr/bin/env bash
# Fresh Ubuntu or Deep Learning VM entry point.
# From a machine without the repo:
#   curl -fsSL https://raw.githubusercontent.com/nhartman000/mg8-model-builder/cursor/emoji-inventory-12-675b/scripts/gcp_build.sh | bash
# From a checkout of this branch:
#   bash scripts/gcp_build.sh
set -euo pipefail

BRANCH="${NYCH_BRANCH:-cursor/emoji-inventory-12-675b}"
REPO="${NYCH_REPO:-https://github.com/nhartman000/mg8-model-builder.git}"
SOURCE="${BASH_SOURCE[0]:-}"

if [[ "$SOURCE" == "bash" || "$SOURCE" == "-" || ! -f "$SOURCE" ]]; then
  work="${NYCH_WORKDIR:-$PWD/mg8-model-builder}"
  git clone --branch "$BRANCH" --depth 1 "$REPO" "$work"
  cd "$work"
  exec bash scripts/gcp_build.sh
fi

cd "$(cd "$(dirname "$SOURCE")/.." && pwd)"
mkdir -p build_results
LOG="build_results/build.log"
exec > >(tee -a "$LOG") 2>&1

echo "branch $(git rev-parse --abbrev-ref HEAD) commit $(git rev-parse HEAD)"
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git

if ! python3 -c "import torch" >/dev/null 2>&1; then
  if command -v nvidia-smi >/dev/null 2>&1; then
    python3 -m pip install --upgrade torch
  else
    python3 -m pip install --upgrade torch --index-url https://download.pytorch.org/whl/cpu
  fi
fi

bash scripts/fetch_wordlists.sh | tee build_results/fetch.log

python3 -m unittest discover -s tests | tee build_results/unittest.log

python3 - << 'PY'
import json
from pathlib import Path

from nych_smoke.report import stage_report
from nych_smoke.tiny_train import train_sample

out = Path("build_results")
report = stage_report()
(out / "smoke.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

runnable = {"wired and passing", "provisional"}
stages = []
for name, stage in report["stages"].items():
    status = stage.get("status", "")
    entry = {"stage": name, "status": status}
    if status not in runnable:
        entry["action"] = "skipped"
        print(f"skipped {name}: {status}")
    else:
        entry["action"] = "ran"
        print(f"ran {name}: {status}")
    stages.append(entry)

cpu = train_sample(device="cpu")
(out / "train_cpu.json").write_text(json.dumps(cpu, indent=2), encoding="utf-8")
gpu_action = "skipped"
gpu = None
try:
    import torch
    if torch.cuda.is_available():
        gpu = train_sample(device="cuda")
        gpu_action = "ran"
    else:
        print("skipped gpu training: CUDA is not available")
except Exception as err:
    print(f"skipped gpu training: {err}")
if gpu is not None:
    (out / "train_gpu.json").write_text(json.dumps(gpu, indent=2), encoding="utf-8")
else:
    (out / "train_gpu.json").write_text(json.dumps({"action": "skipped"}, indent=2), encoding="utf-8")

metrics = {
    "commit": __import__("subprocess").check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    "stages": stages,
    "cpu_device": cpu["device"],
    "cpu_losses": cpu["losses"],
    "gpu_action": gpu_action,
    "gpu_losses": None if gpu is None else gpu["losses"],
}
(out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
(out / "stages.json").write_text(json.dumps(stages, indent=2), encoding="utf-8")
PY

echo "results in $(pwd)/build_results"
