"""CLI: python -m gitson_boundary <declaration.json>

Exit 0 when the declaration PASSes, 1 when it FAILs, and 2 on usage errors.
python -m gitson_boundary --schema-digest prints the frozen schema digest.
Offline. No network.
"""
from __future__ import annotations

import sys
from pathlib import Path

from .validator import SCHEMA_DIGEST, canonical_json, validate_declaration


def main(argv: list[str]) -> int:
    if argv == ["--schema-digest"]:
        sys.stdout.write(SCHEMA_DIGEST + "\n")
        return 0
    if len(argv) != 1 or argv[0] in ("-h", "--help"):
        sys.stderr.write(__doc__ or "")
        return 2
    path = Path(argv[0])
    try:
        raw = path.read_bytes()
    except OSError as err:
        sys.stderr.write(f"cannot read declaration: {err.strerror}\n")
        return 2
    result = validate_declaration(raw)
    sys.stdout.buffer.write(canonical_json(result) + b"\n")
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
