#!/usr/bin/env bash
# Download the crossword substitute if it is not already present and matches.
# The SCOWL list is committed. Peter Broda's list is not fetched: it has no license.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/nych_inventory/dictionary/spreadthewordlist.txt"
URL="https://www.spreadthewordlist.com/downloads/spreadthewordlist.txt"
EXPECT="e631489d99e222efd2b99bc730cc3c2c515832280f88d842558378fd0694e9c7"
SCOWL="$ROOT/nych_inventory/dictionary/scowl-en-us-70.txt"
SCOWL_EXPECT="b667e192289f9f0a6350fc0b1b228bee60db8aef21299ecf7b5c7171940fd092"

scowl_hash="$(sha256sum "$SCOWL" | awk '{print $1}')"
if [[ "$scowl_hash" != "$SCOWL_EXPECT" ]]; then
  echo "SCOWL hash mismatch: $scowl_hash" >&2
  exit 1
fi

if [[ -f "$DEST" ]]; then
  have="$(sha256sum "$DEST" | awk '{print $1}')"
  if [[ "$have" == "$EXPECT" ]]; then
    echo "crossword list already present"
    exit 0
  fi
  echo "replacing crossword list with a hash mismatch" >&2
fi

curl -fL --retry 3 --max-time 120 -o "$DEST.partial" "$URL"
have="$(sha256sum "$DEST.partial" | awk '{print $1}')"
if [[ "$have" != "$EXPECT" ]]; then
  echo "crossword download hash mismatch: $have" >&2
  rm -f "$DEST.partial"
  exit 1
fi
mv "$DEST.partial" "$DEST"
echo "crossword list fetched"
