#!/usr/bin/env bash
# Review loop entry point. Run this (not sync.py alone) at the start of every review round.
# 1) capture the owner's new comments as lessons  2) fail loudly if any lesson still lacks a rule  3) show piece status
set -euo pipefail
cd "$(dirname "$0")"
python3 brain.py pull
if ! python3 brain.py check; then
  echo "STOP: write a generalized rule for each draft lesson (python3 brain.py drafts / set) before revising any piece." >&2
  exit 1
fi
python3 ../review-app/sync.py status
# Refresh the approved-examples library for every week that has a notes file
for notes in approved-examples/notes-*.json; do
  [ -e "$notes" ] || continue
  wk="${notes##*/notes-}"; wk="${wk%.json}"
  python3 export_approved.py "$wk"
done
