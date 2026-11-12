"""Interpreted CLI: python -m nych_compendium build.

The intended later invocation on OMARCHY13 is:

python -m nych_compendium build \\
  --dump ~/nych-data/enwiki-20261001/enwiki-20261001-pages-articles-multistream.xml.bz2 \\
  --sha1 ~/nych-data/enwiki-20261001/enwiki-20261001-pages-articles-multistream.xml.bz2.sha1 \\
  --sqlite ~/nych-data/enwiki-20261001/ngram_counts.sqlite3 \\
  --manifest ~/nych-data/enwiki-20261001/compendium-manifest.json

Smoothing is always ``chen-goodman-mkn-interpolated-v1``. If it cannot be
computed, the command exits 2 and writes no manifest.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from nych_compendium.build import build_compendium
from nych_compendium.smoothing import SmoothingUnavailable


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m nych_compendium")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--dump", required=True, type=Path)
    build.add_argument("--sha1", required=True, type=Path)
    build.add_argument("--sqlite", required=True, type=Path)
    build.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        manifest = build_compendium(args.dump, args.sqlite, args.manifest, args.sha1)
    except SmoothingUnavailable as err:
        print(str(err), file=sys.stderr)
        return 2
    print(manifest["artifact_digest"])
    print(manifest["probabilities"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
