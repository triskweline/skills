#!/bin/bash
# Build the report from a narration file. One builder, three renderings.
#
#   Usage: tour-report.sh <out-file> <source> <narration-file> [md|ansi|html]
#
#     <source>          a git range or a patch file, as tour-set.sh takes
#     <narration-file>  markdown, with one placeholder line per hunk:
#                         %%hunk <path>:<+start>[@<code>][=<caption>]
#     format            md (default) | ansi | html
#
# The model writes narration and placeholders; this script splices the hunks. That is what
# keeps hunks byte-exact without trusting anyone's copy-paste, and it means the model never
# emits diff bytes as output — which is most of the cost of a large report.
#
# Hunks are recorded in the ledger beside <out-file>, so the completeness check is unchanged:
#     tour-set.sh <out-file>.hunk.diff <source> <n> rest
set -euo pipefail

[ $# -ge 3 ] || { echo "usage: tour-report.sh <out-file> <source> <narration-file> [md|ansi|html]" >&2; exit 2; }
OUT="$1"; SOURCE="$2"; DOC="$3"; FMT="${4:-md}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="$OUT.hunk.diff"
WIDTH="${TOUR_WIDTH:-120}"

case "$FMT" in md|ansi|html) ;; *) echo "tour-report: unknown format: $FMT" >&2; exit 2 ;; esac
[ -f "$DOC" ] || { echo "tour-report: no such narration file: $DOC" >&2; exit 2; }
# Catch a bad source here rather than letting git say "fatal: bad revision" from inside a
# hunk extraction, which reads as a script bug rather than a wrong argument.
if [ ! -f "$SOURCE" ] && ! git rev-parse --quiet --verify "${SOURCE%%..*}" >/dev/null 2>&1; then
  echo "tour-report: <source> is neither a patch file nor a git range: $SOURCE" >&2
  exit 2
fi
need() { command -v "$1" >/dev/null || { echo "tour-report: needs $1 for --format $FMT" >&2; exit 1; }; }
case "$FMT" in ansi|html) need delta; need python3 ;; esac

mkdir -p "$(dirname "$OUT")"

# ---- pass 1: validate. Every problem is reported, so one edit round fixes the document.
problems=0; framed=; sawchapter=; lineno=0; infence=; frame=
while IFS= read -r line || [ -n "$line" ]; do
  lineno=$((lineno + 1))
  case "$line" in
    '```'*) if [ -n "$infence" ]; then infence=; else infence=1; fi; continue ;;
  esac
  [ -n "$infence" ] && continue     # a code quote is not a framing sentence
  case "$line" in
    '%%hunk '*)
      if [ -z "$sawchapter" ]; then
        echo "line $lineno: no numbered chapter heading yet — codes would all start at 1" >&2
        echo "             $line" >&2; problems=$((problems + 1))
      elif [ -z "$framed" ]; then
        echo "line $lineno: no narration above this hunk in this chapter" >&2
        echo "             $line" >&2; problems=$((problems + 1))
      else
        # A single-sentence frame introduces the hunk, so it ends with a colon. Count real
        # sentence boundaries — a terminator followed by space and a capital — so an internal
        # period like "form.elements" or "e.g." does not read as two sentences.
        breaks=$(printf '%s' "$frame" | { grep -oE '[.!?][[:space:]]+[A-Z(]' || true; } | wc -l)
        ends=$(printf '%s' "$frame" | grep -cE '\.$' || true)
        if [ "$breaks" -eq 0 ] && [ "$ends" -eq 1 ]; then
          echo "line $lineno: the single sentence above this hunk ends with '.' — use ':'" >&2
          echo "             $frame" >&2; problems=$((problems + 1))
        fi
      fi
      framed=; frame= ;;
    '#'*)
      # A heading closes the previous chapter, so prose above it cannot frame a hunk below.
      framed=
      frame=
      printf '%s' "$line" | grep -qE '^#{1,6}[[:space:]]*[0-9]+[/ ]' && sawchapter=1 ;;
    '') ;;
    *) framed=1; frame="${frame:+$frame }$line" ;;
  esac
done < "$DOC"

if [ "$problems" -gt 0 ]; then
  echo >&2
  echo "tour-report: $problems hunk(s) with nothing above them. Every hunk needs a sentence" >&2
  echo "  saying what it is for, in its own chapter. A heading is not that sentence, and" >&2
  echo "  neither is the hunk's own caption. A single-sentence frame ends with a colon," >&2
  echo "  since it introduces what follows. Nothing written." >&2
  exit 6
fi

# ---- rendering, per format -----------------------------------------------------------
trim_blanks() {
  awk '
    { line[++n] = $0; bare = $0; gsub(/\033\[[0-9;]*m/, "", bare); empty[n] = (bare == "") }
    END { s = 1; while (s <= n && empty[s]) s++
          e = n; while (e >= s && empty[e]) e--
          for (i = s; i <= e; i++) print line[i] }
  '
}

render_prose() {           # stdin: markdown -> stdout: this format
  case "$FMT" in
    md)   cat ;;
    ansi) python3 "$HERE/md-to-ansi.py" --width "$WIDTH" | trim_blanks ;;
    html) python3 "$HERE/md-to-ansi.py" --width "$WIDTH" | python3 "$HERE/ansi-to-html.py" ;;
  esac
}

render_quote() {           # $QUOTE holds the code, $QINFO the fence info string
  # "```path/to/file.js:520 · caption", or "```js", or bare. A path gives delta the language
  # and real line numbers; anything else becomes quote.<lang>.
  local info="$QINFO" cap path start lang n
  cap=${info#* · }; [ "$cap" = "$info" ] && cap=
  info=${info%% · *}
  start=1
  case "$info" in
    *:[0-9]*) start=${info##*:}; info=${info%:*} ;;
  esac
  case "$info" in
    ''|*[!a-zA-Z0-9]*) path="$info" ;;
    *) path="quote.$info" ;;                       # a bare language name
  esac
  [ -n "$path" ] || path=quote.txt
  n=$(wc -l < "$QUOTE")
  case "$FMT" in
    md)
      lang=${path##*.}
      printf '`%s`\n\n```%s\n' "${info:-code}" "$lang"; cat "$QUOTE"; printf '```\n' ;;
    ansi|html)
      { printf 'diff --git a/%s b/%s\n--- a/%s\n+++ b/%s\n' "$path" "$path" "$path" "$path"
        printf '@@ -%s,%s +%s,%s @@ %s\n' "$start" "$n" "$start" "$n" "${cap:-quoted from $info}"
        sed 's/^/ /' "$QUOTE"; } | delta --paging=never --line-numbers --width "$WIDTH" \
            --keep-plus-minus-markers --file-style omit \
            --hunk-header-style 'file' --hunk-header-file-style '244' \
            --hunk-header-decoration-style '238 ul' \
        | { [ "$FMT" = html ] && python3 "$HERE/ansi-to-html.py" || trim_blanks; } ;;
  esac
}

render_hunk() {            # $WORK holds one chapter's hunks -> stdout
  case "$FMT" in
    md)   printf '```diff\n'; cat "$WORK"; printf '```\n' ;;
    ansi|html)
      delta --paging=never --line-numbers --width "$WIDTH" \
            --keep-plus-minus-markers --file-style omit \
            --hunk-header-style 'file' --hunk-header-file-style '244' \
            --hunk-header-decoration-style '238 ul' \
            < "$WORK" | { [ "$FMT" = html ] && python3 "$HERE/ansi-to-html.py" || trim_blanks; } ;;
  esac
}

# ---- pass 2: build ------------------------------------------------------------------
: > "$OUT"
prose=$(mktemp)
first=1; chapter=1; hunkno=0

flush_prose() {
  [ -s "$prose" ] || return 0
  # Keep a heading's blank lines even straight after a hunk: three for a chapter title,
  # two for any other. The hunk separator already contributed one.
  if [ -s "$OUT" ] && [ "$FMT" != html ]; then
    head=$(grep -m1 '[^[:space:]]' "$prose" || true)
    case "$head" in
      '## '*) printf '\n\n' >> "$OUT" ;;
      '#'*)   printf '\n' >> "$OUT" ;;
    esac
  fi
  render_prose < "$prose" >> "$OUT"
  : > "$prose"
}

QUOTE=$(mktemp); QINFO=; infence=
trap 'rm -f "$prose" "$QUOTE"' EXIT

while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in
    '```'*)
      if [ -n "$infence" ]; then
        infence=
        flush_prose
        if [ -s "$OUT" ]; then printf '\n' >> "$OUT"; fi
        render_quote >> "$OUT"
        printf '\n' >> "$OUT"
      else
        infence=1; QINFO="${line#'```'}"; : > "$QUOTE"
      fi
      continue ;;
  esac
  if [ -n "$infence" ]; then printf '%s\n' "$line" >> "$QUOTE"; continue; fi
  case "$line" in
    '%%hunk '*)
      flush_prose
      spec="${line#'%%hunk '}"
      if [ -n "$first" ]; then
        TOUR_NEW=1 TOUR_CODE_OFFSET="$hunkno" bash "$HERE/tour-set.sh" "$WORK" "$SOURCE" "$chapter" "$spec" >/dev/null; first=
      else
        TOUR_CODE_OFFSET="$hunkno" bash "$HERE/tour-set.sh" "$WORK" "$SOURCE" "$chapter" "$spec" >/dev/null
      fi
      hunkno=$((hunkno + $(grep -c '^@@' "$WORK")))
      if [ -s "$OUT" ]; then printf '\n' >> "$OUT"; fi
      render_hunk >> "$OUT"
      printf '\n' >> "$OUT"
      ;;
    *)
      case "$line" in
        \#*) n=$(printf '%s' "$line" | sed -n 's|^#\{1,6\}[[:space:]]*\([0-9]\{1,\}\)[/ ].*|\1|p')
             if [ -n "$n" ] && [ "$n" != "$chapter" ]; then chapter="$n"; hunkno=0; fi ;;
      esac
      printf '%s\n' "$line" >> "$prose" ;;
  esac
done < "$DOC"
flush_prose

if [ "$FMT" = html ]; then
  body=$(cat "$OUT")
  { printf '<!doctype html><meta charset="utf-8"><title>diff tour</title><style>\n'
    printf 'body{background:#1c1c1c;color:#e4e4e4;font:15px/1.6 system-ui,sans-serif;margin:0 auto;max-width:%spx;padding:3rem 1.5rem}\n' "$((WIDTH * 9))"
    printf '.diff{white-space:pre;font-family:ui-monospace,monospace;font-size:13px;overflow-x:auto;margin:1rem 0}\n'
    printf '</style>\n%s\n' "$body"; } > "$OUT"
fi

echo "tour-report: $(grep -c '^@@' "$WORK" 2>/dev/null || echo 0) hunks in the last chapter, format $FMT" >&2
echo
bytes=$(wc -c < "$OUT")
case "$FMT" in
  md)
    # A small report goes straight into the session, which is the point of markdown. A large
    # one cannot: tool output is capped around 40 KB and is truncated past it, for the reader
    # as well as for you. Above the cap, hand over the path.
    if [ "$bytes" -le "${TOUR_INLINE_MAX:-35000}" ]; then
      cat "$OUT"
    else
      printf '%s\n\n' "$OUT"
      printf 'tour-report: %s bytes — too large to print here (tool output is truncated\n' "$bytes"
      printf '  past ~40 KB). Open it with:  less %s\n' "$OUT"
    fi ;;
  ansi) echo "less -R $OUT" ;;
  html) echo "$OUT   (open it in a browser)" ;;
esac
