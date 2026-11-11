"""Interpreted CLI: python -m nych_inspector.

Reads a candidate digest, a contract JSON file, and an evidence JSON file.
Prints the verdict JSON. It does not validate a GitSON declaration.
"""
from __future__ import annotations

import argparse
import json
import sys

from nych_inspector.review import review


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m nych_inspector")
    parser.add_argument("--digest", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--bundle", required=True)
    args = parser.parse_args(argv)
    contract = json.loads(open(args.contract, encoding="utf-8").read())
    bundle = json.loads(open(args.bundle, encoding="utf-8").read())
    json.dump(review(args.digest, contract, bundle), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
