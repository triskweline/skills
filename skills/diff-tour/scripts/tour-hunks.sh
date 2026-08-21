#!/bin/bash
# List the selectable hunks of a diff, with the +start line that tour-set.sh wants.
#
#   Usage: tour-hunks.sh <range> [<path> …]
#   e.g.:  tour-hunks.sh master..HEAD src/ spec/
#
# Output: one line per hunk —  <+start>  <path>  <git's own context text>
# Feed the +start values to tour-set.sh. They change whenever the branch moves, so
# re-run this after any commit rather than reusing numbers from earlier in a session.
set -euo pipefail

[ $# -ge 1 ] || { echo "usage: tour-hunks.sh <range> [<path> …]" >&2; exit 2; }
range="$1"; shift

git -C "${TOUR_REPO:-$PWD}" diff "$range" -- "$@" | awk '
  # Take the path from "+++ b/…" rather than "diff --git": $NF breaks on a filename with
  # a space, and the a/ b/ prefixes are configurable (diff.mnemonicPrefix, diff.noprefix).
  /^\+\+\+ / { path = substr($0, 5); sub(/^[^\/]*\//, "", path); sub(/\t.*$/, "", path); next }
  /^@@/ {
    match($0, /\+[0-9]+/); start = substr($0, RSTART + 1, RLENGTH - 1)
    ctx = $0; sub(/^@@[^@]*@@ ?/, "", ctx)
    printf "%-8s %-44s %s\n", start, path, ctx
  }
'
