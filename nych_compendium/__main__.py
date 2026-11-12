"""Interpreted CLI: python -m nych_compendium build.

The intended later invocation on OMARCHY13 is:

python -m nych_compendium build \\
  --dump ~/nych-data/enwiki-20261001/enwiki-20261001-pages-articles-multistream.xml.bz2 \\
  --sha1 ~/nych-data/enwiki-20261001/enwiki-20261001-sha1sums.txt \\
  --sqlite ~/nych-data/enwiki-20261001/ngram_counts.sqlite3 \\
  --manifest ~/nych-data/enwiki-20261001/compendium-manifest.json \\
  --workers 6

Requires ``pip install mwparserfromhell==0.6.6`` for markup stripping.

Smoothing is always ``chen-goodman-mkn-interpolated-v1``. If it cannot be
computed, the command exits 2 and writes no manifest.

Run files go to ``--work-dir`` (default: next to the SQLite file) and are
removed after a successful build. SQLite temp files go there too, through
``SQLITE_TMPDIR``, unless that is already set, because /tmp may be in RAM.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m nych_compendium")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--dump", required=True, type=Path)
    build.add_argument("--sha1", required=True, type=Path)
    build.add_argument("--sqlite", required=True, type=Path)
    build.add_argument("--manifest", required=True, type=Path)
    build.add_argument("--workers", type=int, default=1)
    build.add_argument("--batch-pages", type=int, default=None)
    build.add_argument("--merge-fan-in", type=int, default=None)
    build.add_argument("--work-dir", type=Path, default=None)
    args = parser.parse_args(argv)
    work_dir = args.work_dir or args.sqlite.with_name(args.sqlite.name + ".runs")
    sqlite_tmp = work_dir.with_name(work_dir.name + ".sqlite-tmp")
    sqlite_tmp.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("SQLITE_TMPDIR", str(sqlite_tmp))

    from nych_compendium import build as builder
    from nych_compendium.smoothing import SmoothingUnavailable

    options = {"workers": args.workers, "work_dir": work_dir}
    if args.batch_pages is not None:
        options["batch_pages"] = args.batch_pages
    if args.merge_fan_in is not None:
        options["merge_fan_in"] = args.merge_fan_in
    try:
        manifest = builder.build_compendium(args.dump, args.sqlite, args.manifest, args.sha1, **options)
    except SmoothingUnavailable as err:
        print(str(err), file=sys.stderr)
        return 2
    print(manifest["artifact_digest"])
    print(manifest["probabilities"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
