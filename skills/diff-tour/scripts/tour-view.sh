#!/bin/bash
# Diff-tour viewer. Renders the narrator's current chapter through delta into a pager,
# and swaps to the next chapter — from the top — the moment the narrator rewrites it.
#
#   Usage: bash tour-view.sh <tour-file>
#
#   Scroll: arrows / PgUp / PgDn / mouse wheel / g / G / "/" to search
#   Quit:   q, ESC ESC, or Ctrl-C
#
# Hand the human ONE line to paste, with an absolute path to both this script and the
# tour file. Everything else is automatic.

TOUR="${1:-}"
[ -n "$TOUR" ] || { echo "usage: bash tour-view.sh <tour-file>" >&2; exit 2; }
PARENT="$(dirname "$TOUR")"
[ -d "$PARENT" ] || { echo "no such directory: $PARENT" >&2; exit 2; }
DIR="$(cd "$PARENT" && pwd)"
BASE="$(basename "$TOUR")"
TOUR="$DIR/$BASE"
RENDER="$DIR/.${BASE}.rendered"
KEYS="$DIR/.${BASE}.lesskey"
FLAG="$DIR/.${BASE}.changed"
WATCHER=

# ---- dependencies ------------------------------------------------------------------
missing=()
command -v delta >/dev/null || missing+=(delta)
command -v less  >/dev/null || missing+=(less)
if [ ${#missing[@]} -gt 0 ]; then
  echo "diff-tour viewer needs: ${missing[*]}" >&2
  echo >&2
  for tool in "${missing[@]}"; do
    case "$tool" in
      delta) echo "  delta  — https://github.com/dandavison/delta" >&2
             echo "           apt: git-delta   brew: git-delta   pacman: git-delta   cargo: git-delta" >&2 ;;
      less)  echo "  less   — apt/brew/pacman: less" >&2 ;;
    esac
  done
  echo >&2
  echo "Install those and paste the command again." >&2
  exit 1
fi

# inotifywait is optional: without it we poll, which costs nothing noticeable.
WATCH=inotify
command -v inotifywait >/dev/null || WATCH=poll
if [ "$WATCH" = poll ]; then
  echo "note: inotifywait not found (apt: inotify-tools) — falling back to polling." >&2
  sleep 2
fi

# ---- viewer ------------------------------------------------------------------------
printf '#command\n\\e\\e quit\n' > "$KEYS"   # ESC alone can't quit: arrows are ESC-prefixed
LESSKEY=()
less --lesskey-src=/dev/null --version >/dev/null 2>&1 && LESSKEY=(--lesskey-src="$KEYS")

# mtime + size, for the polling fallback. GNU and BSD stat disagree on flags, and the
# platform without inotify (macOS) is the one guaranteed to need this path.
if stat -c '%Y %s' . >/dev/null 2>&1; then
  stamp() { [ -e "$TOUR" ] && stat -c '%Y %s' "$TOUR" 2>/dev/null; }
elif stat -f '%m %z' . >/dev/null 2>&1; then
  stamp() { [ -e "$TOUR" ] && stat -f '%m %z' "$TOUR" 2>/dev/null; }
else
  stamp() { [ -e "$TOUR" ] && wc -c < "$TOUR" 2>/dev/null; }   # last resort: size only
fi

watch_once() {
  if [ "$WATCH" = inotify ]; then
    # --include matches the event's FULL PATH, not the basename: a "^name$" anchor can
    # never match. The leading slash pins it to this exact file, and the trailing $ still
    # excludes the siblings (.<base>.rendered, <base>.tmp, .<base>.lesskey, .<base>.changed).
    inotifywait -qq -e close_write,moved_to --include "/${BASE//./\\.}\$" "$DIR" 2>/dev/null && return
  fi
  local was; was="$(stamp)"
  while [ "$(stamp)" = "$was" ]; do sleep 1; done
}

reap() {
  [ -n "$WATCHER" ] || return 0
  pkill -P "$WATCHER" 2>/dev/null           # the inotifywait/sleep inside the subshell
  kill "$WATCHER" 2>/dev/null
  wait "$WATCHER" 2>/dev/null
  WATCHER=
}

finish() { reap; rm -f "$KEYS" "$RENDER" "$FLAG"; clear; exit 0; }
trap finish INT TERM

clear
printf '\033[2mdiff-tour viewer — waiting for the first chapter…\033[0m\n'
while [ ! -s "$TOUR" ]; do watch_once; done

while :; do
  # --hunk-header-style without delta's "syntax" attribute: our captions are prose, and
  # delta would otherwise colour them as source — "2.1" as a numeric literal, each word as
  # an identifier. Dropping "line-number" too: the code replaces it, and --line-numbers
  # already numbers every row.
  delta --paging=never --line-numbers --width "$(tput cols)" \
        --hunk-header-style 'bold yellow' \
        --hunk-header-decoration-style 'yellow box' \
        --keep-plus-minus-markers \
        < "$TOUR" > "$RENDER"

  # A sentinel, not an exit code: less installs a SIGTERM handler and exits 15 on some
  # builds and 143 on others, so the status cannot tell us who ended the pager.
  rm -f "$FLAG"
  ( watch_once; : > "$FLAG"; pkill -P $$ -x less 2>/dev/null ) &
  WATCHER=$!

  less -R -K --mouse "${LESSKEY[@]}" "$RENDER"

  reap
  [ -e "$FLAG" ] || finish     # no sentinel => the reader quit, not a new chapter
done
