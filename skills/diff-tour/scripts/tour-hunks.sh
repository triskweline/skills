#!/bin/bash
# List the selectable hunks of a diff, with the +start line that tour-set.sh wants.
#
#   Usage: tour-hunks.sh <source> [<path> …]
#     <source> is a git range or a patch file — the same argument tour-set.sh takes,
#     so a tour driven from a saved patch can list its hunks the same way.
#   e.g.:  tour-hunks.sh /tmp/change.patch src/
#          tour-hunks.sh master..HEAD src/ spec/
#
# Output: one line per hunk —  <+start>  <path>  <git's own context text>
# Feed the +start values to tour-set.sh. They change whenever the branch moves, so
# re-run this after any commit rather than reusing numbers from earlier in a session.
set -euo pipefail

[ $# -ge 1 ] || { echo "usage: tour-hunks.sh <source> [<path> …]" >&2; exit 2; }
source="$1"; shift

if [ -f "$source" ]; then cat "$source"; else git -C "${TOUR_REPO:-$PWD}" diff "$source" -- "$@"; fi \
  | awk -v filter="$*" '
  # Take the path from "+++ b/…" rather than "diff --git": $NF breaks on a filename with
  # a space, and the a/ b/ prefixes are configurable (diff.mnemonicPrefix, diff.noprefix).
  /^--- / { minus = substr($0, 5); sub(/^[^\/]*\//, "", minus); sub(/\t.*$/, "", minus); next }
  /^\+\+\+ / { path = substr($0, 5); sub(/\t.*$/, "", path)
               if (path == "/dev/null") path = minus; else sub(/^[^\/]*\//, "", path)
               next }
  /^@@/ {
    # A patch file was not filtered by git, so honour the path arguments here.
    if (filter != "") {
      keep = 0
      n = split(filter, want, " ")
      for (i = 1; i <= n; i++) if (index(path, want[i]) == 1) keep = 1
      if (!keep) next
    }
    match($0, /\+[0-9]+/); start = substr($0, RSTART + 1, RLENGTH - 1)
    ctx = $0; sub(/^@@[^@]*@@ ?/, "", ctx)
    printf "%-8s %-44s %s\n", start, path, ctx
  }
'
