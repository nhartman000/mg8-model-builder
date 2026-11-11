"""Interpreted CLI: python -m nych_compendium build.

The intended later invocation on OMARCHY13 is:

python -m nych_compendium build \\
  --dump ~/nych-data/enwiki-20261001/enwiki-20261001-pages-articles-multistream.xml.bz2 \\
  --sha1 ~/nych-data/enwiki-20261001/enwiki-20261001-pages-articles-multistream.xml.bz2.sha1 \\
  --sqlite ~/nych-data/enwiki-20261001/ngram_counts.sqlite3 \\
  --manifest ~/nych-data/enwiki-20261001/compendium-manifest.json \\
  --smoothing none

``--smoothing`` is required. The token ``none`` means counts only. It is not a
smoothing algorithm. Any other token is refused.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from nych_compendium.build import SmoothingRefused, build_compendium


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m nych_compendium")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--dump", required=True, type=Path)
    build.add_argument("--sha1", required=True, type=Path)
    build.add_argument("--sqlite", required=True, type=Path)
    build.add_argument("--manifest", required=True, type=Path)
    build.add_argument("--smoothing", required=True)
    args = parser.parse_args(argv)
    smoothing = None if args.smoothing == "none" else args.smoothing
    try:
        manifest = build_compendium(
            args.dump,
            args.sqlite,
            args.manifest,
            args.sha1,
            smoothing=smoothing,
        )
    except SmoothingRefused as err:
        print(str(err), file=sys.stderr)
        return 2
    print(manifest["artifact_digest"])
    print(manifest["probabilities"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
