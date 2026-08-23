#!/bin/bash
# Assemble an ansi-export document: narration and hunks interwoven in one text file,
# styled with ANSI escapes, read with `less -R`.
#
#   Usage: tour-ansi.sh <out-file> <source> <narration-file>
#
#     <source>          a git range or a patch file, as tour-set.sh takes
#     <narration-file>  markdown, with one placeholder line per hunk:
#
#                         %%hunk <path>:<+start>[=<caption>]
#
# Everything that is not a placeholder is rendered by md-to-ansi.py. Every placeholder is
# replaced by that hunk, byte-exact from the source and rendered by delta — so the diff a
# reader sees is never retyped, and the narrated hunk always sits next to its narration.
#
# Hunks are recorded in the same ledger tour-set.sh keeps, so the completeness check still
# works: after building the document, run
#     tour-set.sh <out-file>.hunk.diff <source> <n> rest
# and it reports anything no placeholder showed.
set -euo pipefail

[ $# -ge 3 ] || { echo "usage: tour-ansi.sh <out-file> <source> <narration-file>" >&2; exit 2; }
OUT="$1"; SOURCE="$2"; DOC="$3"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="$OUT.hunk.diff"
WIDTH="${TOUR_WIDTH:-96}"

for t in delta python3; do command -v "$t" >/dev/null || { echo "tour-ansi: needs $t" >&2; exit 1; }; done
[ -f "$DOC" ] || { echo "tour-ansi: no such narration file: $DOC" >&2; exit 2; }

mkdir -p "$(dirname "$OUT")"
: > "$OUT"
prose=$(mktemp); trap 'rm -f "$prose"' EXIT
first=1
chapter=1; hunkno=0    # updated from headings like "## 3/8 · <name>", so codes come out 3.1, 3.2, …

flush_prose() {
  [ -s "$prose" ] || return 0
  python3 "$HERE/md-to-ansi.py" --width "$WIDTH" < "$prose" >> "$OUT"
  : > "$prose"
}

while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in
    '%%hunk '*)
      flush_prose
      spec="${line#'%%hunk '}"
      if [ -n "$first" ]; then
        TOUR_NEW=1 TOUR_CODE_OFFSET="$hunkno" bash "$HERE/tour-set.sh" "$WORK" "$SOURCE" "$chapter" "$spec" >/dev/null; first=
      else
        TOUR_CODE_OFFSET="$hunkno" bash "$HERE/tour-set.sh" "$WORK" "$SOURCE" "$chapter" "$spec" >/dev/null
      fi
      hunkno=$((hunkno + 1))
      printf '\n' >> "$OUT"
      delta --paging=never --line-numbers --width "$WIDTH" \
            --keep-plus-minus-markers --file-style omit \
            --hunk-header-style 'bold yellow' --hunk-header-decoration-style 'yellow box' \
            < "$WORK" >> "$OUT"
      printf '\n' >> "$OUT"
      ;;
    *)
      case "$line" in
        \#*) n=$(printf '%s' "$line" | sed -n 's/^#\{1,6\}[[:space:]]*\([0-9]\{1,\}\)\/.*/\1/p')
             if [ -n "$n" ] && [ "$n" != "$chapter" ]; then chapter="$n"; hunkno=0; fi ;;
      esac
      printf '%s\n' "$line" >> "$prose" ;;
  esac
done < "$DOC"
flush_prose

echo "tour-ansi: $(grep -c $'\033' "$OUT" || true) styled lines" >&2
echo
echo "less -R --mouse $OUT"
