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

failed=0

if bash scripts/fetch_wordlists.sh | tee build_results/fetch.log; then
  echo "ran fetch_wordlists"
else
  echo "failed fetch_wordlists"
  failed=1
fi

if python3 -m unittest discover -s tests | tee build_results/unittest.log; then
  echo "ran unittest"
else
  echo "failed unittest"
  failed=1
fi

if python3 - << 'PY'
import json
import subprocess
import sys
from pathlib import Path

out = Path("build_results")
failed = False

def write(name, payload):
    (out / name).write_text(json.dumps(payload, indent=2), encoding="utf-8")

try:
    from nych_smoke.report import stage_report
    report = stage_report()
    write("smoke.json", report)
    print("ran smoke")
except Exception as err:
    failed = True
    write("smoke.json", {"action": "failed", "error": str(err)})
    print(f"failed smoke: {err}")
    report = {"stages": {}}

runnable = {"wired and passing", "provisional"}
stages = []
for name, stage in report.get("stages", {}).items():
    status = stage.get("status", "")
    entry = {"stage": name, "status": status}
    if status not in runnable:
        entry["action"] = "skipped"
        print(f"skipped {name}: {status}")
    else:
        entry["action"] = "ran"
        print(f"ran {name}: {status}")
    stages.append(entry)

try:
    from nych_smoke.tiny_train import train_sample
    cpu = train_sample(device="cpu")
    cpu["action"] = "ran"
    write("train_cpu.json", cpu)
    print("ran train_cpu")
except Exception as err:
    failed = True
    cpu = None
    write("train_cpu.json", {"action": "failed", "device": "cpu", "error": str(err)})
    print(f"failed train_cpu: {err}")

gpu = None
gpu_action = "skipped"
try:
    import torch
    if torch.cuda.is_available():
        from nych_smoke.tiny_train import train_sample
        gpu = train_sample(device="cuda")
        gpu["action"] = "ran"
        gpu_action = "ran"
        write("train_gpu.json", gpu)
        print("ran train_gpu")
    else:
        write("train_gpu.json", {"action": "skipped", "reason": "CUDA is not available"})
        print("skipped train_gpu: CUDA is not available")
except Exception as err:
    failed = True
    gpu_action = "failed"
    write("train_gpu.json", {"action": "failed", "device": "cuda", "error": str(err)})
    print(f"failed train_gpu: {err}")

commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
metrics = {
    "commit": commit,
    "failed": failed,
    "stages": stages,
    "cpu_device": None if cpu is None else cpu.get("device"),
    "cpu_losses": None if cpu is None else cpu.get("losses"),
    "gpu_action": gpu_action,
    "gpu_losses": None if gpu is None else gpu.get("losses"),
}
write("metrics.json", metrics)
write("stages.json", stages)
sys.exit(1 if failed else 0)
PY
then
  echo "ran smoke and training"
else
  echo "failed smoke or training"
  failed=1
fi

for name in smoke.json train_cpu.json train_gpu.json; do
  if [[ ! -f "build_results/$name" ]]; then
    printf '%s\n' "{\"action\":\"failed\",\"error\":\"$name was not written\"}" > "build_results/$name"
    failed=1
  fi
done

echo "results in $(pwd)/build_results"
exit "$failed"
