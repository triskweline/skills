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

# ---- pass 1: validate. Every problem is reported, so one edit round fixes the document.
# Dying on the first would make the author rebuild once per mistake.
problems=0
framed=; sawchapter=; lineno=0
while IFS= read -r line || [ -n "$line" ]; do
  lineno=$((lineno + 1))
  case "$line" in
    '%%hunk '*)
      if [ -z "$sawchapter" ]; then
        echo "line $lineno: no numbered chapter heading yet — codes would all start at 1" >&2
        echo "             $line" >&2
        problems=$((problems + 1))
      elif [ -z "$framed" ]; then
        echo "line $lineno: no narration above this hunk in this chapter" >&2
        echo "             $line" >&2
        problems=$((problems + 1))
      fi
      framed= ;;
    '#'*)
      # A heading closes the previous chapter, so prose above it cannot frame a hunk below
      # it. The first hunk of a chapter needs the chapter's own opening sentence.
      framed=
      printf '%s' "$line" | grep -qE '^#{1,6}[[:space:]]*[0-9]+[/ ]' && sawchapter=1 ;;
    '') ;;
    *) framed=1 ;;
  esac
done < "$DOC"

if [ "$problems" -gt 0 ]; then
  echo >&2
  echo "tour-ansi: $problems hunk(s) with nothing above them. Every hunk needs a sentence" >&2
  echo "  saying what it is for, in its own chapter. A heading is not that sentence, and" >&2
  echo "  neither is the hunk's own caption — the reader sees the caption only once they" >&2
  echo "  have reached the code. Nothing written." >&2
  exit 6
fi

: > "$OUT"
prose=$(mktemp); trap 'rm -f "$prose"' EXIT
first=1
chapter=1; hunkno=0

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
  # A heading keeps its blank lines above it even straight after a hunk — md-to-ansi spaces
  # its own blocks but cannot see across one. The hunk already contributed one blank, so
  # top up to three for a chapter title and two for any other heading.
  if [ -s "$OUT" ]; then
    head=$(grep -m1 '[^[:space:]]' "$prose")
    case "$head" in
      '## '*) printf '\n\n' >> "$OUT" ;;
      '#'*)   printf '\n' >> "$OUT" ;;
    esac
  fi
  python3 "$HERE/md-to-ansi.py" --width "$WIDTH" < "$prose" | trim_blanks >> "$OUT"
  : > "$prose"
}

# ---- pass 2: build.
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in
    '%%hunk '*)
      # A hunk must never open a chapter or sit straight under a heading: the reader needs
      # a sentence saying what it is for before they meet the code. A heading is not that
      # sentence.
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
             if [ -n "$n" ] && [ "$n" != "$chapter" ]; then chapter="$n"; hunkno=0; fi ;;
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
