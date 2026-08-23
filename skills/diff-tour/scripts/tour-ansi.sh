#!/bin/bash
# Assemble the ansi report: narration and hunks interwoven in one text file,
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
WIDTH="${TOUR_WIDTH:-120}"

for t in delta python3; do command -v "$t" >/dev/null || { echo "tour-ansi: needs $t" >&2; exit 1; }; done
[ -f "$DOC" ] || { echo "tour-ansi: no such narration file: $DOC" >&2; exit 2; }

mkdir -p "$(dirname "$OUT")"
: > "$OUT"
prose=$(mktemp); trap 'rm -f "$prose"' EXIT
first=1
chapter=1; hunkno=0; framed=; sawchapter=   # `framed` tracks prose since the last hunk
                       # updated from headings like "## 3/8 · <name>", so codes come out 3.1, 3.2, …

# Strip leading and trailing blank lines. Both the narration and delta bring their own,
# and stacked they read as a gap rather than a separator.
trim_blanks() {
  awk '
    {
      line[++n] = $0
      bare = $0; gsub(/\033\[[0-9;]*m/, "", bare)
      empty[n] = (bare == "")   # spaces on a coloured background are structure, not blank
    }
    END {
      s = 1; while (s <= n && empty[s]) s++
      e = n; while (e >= s && empty[e]) e--
      for (i = s; i <= e; i++) print line[i]
    }
  '
}

flush_prose() {
  [ -s "$prose" ] || return 0
  # A heading gets two blank lines above it wherever it lands, including straight after a
  # hunk — md-to-ansi does that between its own blocks, but cannot see across a hunk.
  if [ -s "$OUT" ] && grep -qm1 '^#' <(grep -m1 '[^[:space:]]' "$prose"); then
    printf '\n' >> "$OUT"
  fi
  python3 "$HERE/md-to-ansi.py" --width "$WIDTH" < "$prose" | trim_blanks >> "$OUT"
  : > "$prose"
}

while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in
    '%%hunk '*)
      # A hunk must never open a chapter or sit straight under a heading: the reader needs
      # a sentence saying what it is for before they meet the code. A heading is not that
      # sentence.
      if [ -z "$framed" ]; then
        echo "tour-ansi: no narration above this hunk — say what it is for first:" >&2
        echo "  ${line}" >&2
        echo "tour-ansi: a heading does not count. One sentence is enough." >&2
        exit 6
      fi
      if [ -z "$sawchapter" ]; then
        echo "tour-ansi: no numbered chapter heading above this hunk — codes would all start" >&2
        echo "  at 1. Give the chapter a heading like '## 3/9 · <name>' first." >&2
        exit 7
      fi
      framed=
      flush_prose
      spec="${line#'%%hunk '}"
      if [ -n "$first" ]; then
        TOUR_NEW=1 TOUR_CODE_OFFSET="$hunkno" bash "$HERE/tour-set.sh" "$WORK" "$SOURCE" "$chapter" "$spec" >/dev/null; first=
      else
        TOUR_CODE_OFFSET="$hunkno" bash "$HERE/tour-set.sh" "$WORK" "$SOURCE" "$chapter" "$spec" >/dev/null
      fi
      # A placeholder may resolve to several hunks (a `;` list, `all`, `rest`), so advance
      # by what was emitted. Counting placeholders gives two hunks the same code.
      hunkno=$((hunkno + $(grep -c '^@@' "$WORK")))
      # Exactly one blank line on each side of a hunk.
      if [ -s "$OUT" ]; then printf '\n' >> "$OUT"; fi
      # No yellow, no box, no bold: the caption is plain text over a grey underline, the
      # same shape as a chapter title one level down. Delta's default box and blue path
      # competed with every heading.
      delta --paging=never --line-numbers --width "$WIDTH" \
            --keep-plus-minus-markers --file-style omit \
            --hunk-header-style 'file' \
            --hunk-header-file-style '244' \
            --hunk-header-decoration-style '238 ul' \
            < "$WORK" | trim_blanks >> "$OUT"
      printf '\n' >> "$OUT"
      ;;
    *)
      case "$line" in
        \#*) # "## 3/9 · name" or "## 3 · name" — the number is what matters.
             n=$(printf '%s' "$line" | sed -n 's|^#\{1,6\}[[:space:]]*\([0-9]\{1,\}\)[/ ].*|\1|p')
             if [ -n "$n" ] && [ "$n" != "$chapter" ]; then chapter="$n"; hunkno=0; sawchapter=1; fi ;;
      esac
      case "$line" in
        '#'*|'') ;;                      # headings and blanks do not frame a hunk
        *) framed=1 ;;
      esac
      printf '%s\n' "$line" >> "$prose" ;;
  esac
done < "$DOC"
flush_prose

echo "tour-ansi: $(grep -c $'\033' "$OUT" || true) styled lines" >&2
echo
# No --mouse: it captures drag events, which stops the terminal selecting text for copy.
# Most terminals translate the wheel to arrow keys anyway, so scrolling still works.
echo "less -R $OUT"
