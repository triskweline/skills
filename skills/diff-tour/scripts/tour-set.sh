#!/bin/bash
# Extract one chapter's hunks. They come byte-exact from the diff;
# only the free text after the second @@ is rewritten, into "<chapter>.<n> · <caption>".
#
#   Usage: tour-set.sh <tour-file> <source> <chapter> <spec> [<spec> …]
#
#     <source> = a git range (master..HEAD, HEAD~1..HEAD) resolved against $PWD or
#                $TOUR_REPO — or a path to a patch file, for anything git cannot name:
#                `gh pr diff 807 > /tmp/pr.patch`, `git diff HEAD > /tmp/wip.patch`.
#     <spec>   = <path>:<item>[;<item>…]   one or more per file, merged
#                <path>:all[=<caption>]    every hunk in that file, one shared caption
#                rest                      every hunk not shown in an earlier chapter
#                rest:<path>=<caption>     ...and what that group is. <path> may be a
#                                          prefix (rest:docs/=...) to cover a whole subtree,
#                                          e.g. rest:src/form.js="the same accessor swap
#                                          as 2.2, in six more call sites"
#     <item>   = <+start>[=<caption>]      +start comes from tour-hunks.sh
#
#   Captions may contain commas and "·" but not semicolons, tabs or newlines, and are
#   never truncated. Hunks are emitted and numbered in the order you list them, so
#   narration order, screen order and codes agree. `all` and `rest` use file order.
#
#   Set TOUR_NEW=1 on the first chapter of a tour: it starts a fresh coverage ledger
#   (<tour-file>.used), which is what makes `rest` and the coverage count meaningful.
#
#   Prints the assigned codes and what is still unshown. Quote the codes in the narration.
#   Exits 3 if a requested hunk does not exist, 4 if its own output disagrees with itself.
#   `rest` with nothing left prints "all hunks already shown" and exits 0 — run it once
#   before the wrap-up chapter, in every mode, as the tour's completeness check.
set -euo pipefail

[ $# -ge 4 ] || { echo "usage: tour-set.sh <tour-file> <source> <chapter> <spec> …" >&2; exit 2; }
TOUR="$1"; SOURCE="$2"; CHAPTER="$3"; shift 3
REPO="${TOUR_REPO:-$PWD}"
TMP="$TOUR.tmp"
LEDGER="$TOUR.used"
MAP="$(mktemp)"; trap 'rm -f "$MAP" "$MAP".* "$TMP"' EXIT

mkdir -p "$(dirname "$TOUR")"
[ -n "${TOUR_NEW:-}" ] && rm -f "$LEDGER"
touch "$LEDGER"

# The diff, whatever it came from. A patch file is filtered by path here, since we
# cannot re-ask git for a subset of someone else's patch.
patch_of() {
  if [ -f "$SOURCE" ]; then
    if [ -n "${1:-}" ]; then
      awk -v want="$1" '
        /^diff --git/ { keep = 0; seenhunk = 0; hdr = $0 "\n"; next }
        /^--- / { minus = substr($0, 5); sub(/^[^\/]*\//, "", minus); sub(/\t.*$/, "", minus)
                  hdr = hdr $0 "\n"; next }
        /^\+\+\+ / {
          p = substr($0, 5); sub(/\t.*$/, "", p)
          # A deletion has "+++ /dev/null": the real path is on the --- line.
          if (p == "/dev/null") p = minus; else sub(/^[^\/]*\//, "", p)
          keep = (p == want); hdr = hdr $0 "\n"; next
        }
        # index / mode / rename lines precede +++, so buffer them into the header too.
        !seenhunk && /^(index |new file |deleted file |old mode |new mode |similarity |rename )/ {
          hdr = hdr $0 "\n"; next
        }
        /^@@/ { seenhunk = 1 }
        keep { if (hdr != "") { printf "%s", hdr; hdr = "" } print }
      ' "$SOURCE"
    else
      cat "$SOURCE"
    fi
  else
    git -C "$REPO" diff "$SOURCE" -- ${1:+"$1"}
  fi
}

starts_of() {   # +start lines of one path
  patch_of "$1" | awk '/^@@/ { match($0, /\+[0-9]+/); print substr($0, RSTART + 1, RLENGTH - 1) }'
}

all_pairs() {   # every path<TAB>+start in the whole diff, in diff order
  patch_of "" | awk '
    /^--- / { minus = substr($0, 5); sub(/^[^\/]*\//, "", minus); sub(/\t.*$/, "", minus); next }
    /^\+\+\+ / { p = substr($0, 5); sub(/\t.*$/, "", p)
                 # A deletion has "+++ /dev/null": the real path is on the --- line.
                 if (p == "/dev/null") p = minus; else sub(/^[^\/]*\//, "", p)
                 next }
    /^@@/ { match($0, /\+[0-9]+/); print p "\t" substr($0, RSTART + 1, RLENGTH - 1) }
  '
}

# ---- resolve specs to a path list plus a merged want-string per path ----------------
SPECS="$MAP.specs"; : > "$SPECS"
RESTCAP="$MAP.restcap"; : > "$RESTCAP"
want_rest=

# First collect the leftover group captions, so `rest` can label each file's group with
# what it repeats. Order of arguments does not matter.
for spec in "$@"; do
  case "$spec" in
    rest) want_rest=1 ;;
    rest:*) want_rest=1
            group="${spec#rest:}"
            printf '%s\t%s\n' "${group%%=*}" "${group#*=}" >> "$RESTCAP" ;;
  esac
done

for spec in "$@"; do
  case "$spec" in
    rest|rest:*) ;;
    *) printf '%s\t%s\n' "${spec%%:*}" "${spec#*:}" >> "$SPECS" ;;
  esac
done

if [ -n "$want_rest" ]; then
  all_pairs | while IFS=$'\t' read -r p s; do
    grep -qxF "$p	$s" "$LEDGER" || printf '%s\t%s\n' "$p" "$s"
  done > "$MAP.rest"

  uncaptioned=""
  while IFS=$'\t' read -r p s; do
    # Exact path first, then the longest matching prefix (rest:docs/=... covers a subtree).
    cap=$(awk -F'\t' -v p="$p" '$1 == p { print $2; exit }' "$RESTCAP")
    [ -n "$cap" ] || cap=$(awk -F'\t' -v p="$p" 'index(p, $1) == 1 { if (length($1) > n) { n = length($1); c = $2 } } END { print c }' "$RESTCAP")
    if [ -z "$cap" ]; then
      cap="(leftover) not narrated"
      case "$uncaptioned" in *"|$p|"*) ;; *) uncaptioned="$uncaptioned|$p|" ;; esac
    fi
    printf '%s\t%s=%s\n' "$p" "$s" "$cap" >> "$SPECS"
  done < "$MAP.rest"

  if [ -n "$uncaptioned" ]; then
    echo "tour-set: leftover groups with no caption — say what each one is:" >&2
    printf '%s' "$uncaptioned" | tr '|' '\n' | awk 'NF' | sed 's/^/  rest:/; s/$/=.../' >&2
    # Fatal, and before the ledger is touched: once these hunks are marked shown, a
    # second `rest` reports "all hunks already shown" and the bare captions are baked in.
    # A path prefix caption covers many files at once: rest:docs/=the second body of work
    if [ -z "${TOUR_BARE:-}" ]; then
      echo "tour-set: nothing written. Caption them, or set TOUR_BARE=1 to accept the defaults." >&2
      exit 5
    fi
  fi
fi

paths=$(cut -f1 "$SPECS" | awk 'NF && !seen[$0]++')
if [ -z "$paths" ]; then
  # `rest` with nothing left is the completeness check passing, not a failure.
  if [ -n "$want_rest" ]; then
    echo "tour-set: all hunks already shown — no Leftovers chapter needed"
    exit 0
  fi
  echo "tour-set: nothing to show" >&2
  exit 3
fi

# ---- pass 1: assign codes in on-screen order (file order, then line order) ----------
# TOUR_CODE_OFFSET lets a caller that invokes us once per hunk keep one running
# numbering across calls, as tour-ansi.sh does.
n=${TOUR_CODE_OFFSET:-0}
while IFS= read -r path; do
  [ -n "$path" ] || continue
  want=$(awk -F'\t' -v p="$path" '$1 == p { printf "%s;", $2 }' "$SPECS")
  starts=$(starts_of "$path")
  [ -n "$starts" ] || { echo "tour-set: no hunks at all in $path" >&2; exit 3; }

  # "all" may carry a caption of its own, applied to every hunk in the file.
  allcap=$(printf '%s' "$want" | tr ';' '\n' | sed -n 's/^[[:space:]]*all=//p' | head -1)
  case ";$want" in
    *";all;"*|*";all="*) wanted="$starts" ;;
    *) # Deliberately unsorted: hunks appear in the order you list them, so narration
       # order, screen order and code order are the same thing. `all` and `rest` fall
       # back to file order below, since there is no stated order to honour.
       wanted=$(printf '%s' "$want" | tr ';' '\n' | sed 's/=.*//; s/^[[:space:]]*+\?//; s/[[:space:]]*$//' | grep -v '^$' | awk '!seen[$0]++')
       for s in $wanted; do
         grep -qx "$s" <<<"$starts" || { echo "tour-set: no hunk at +$s in $path (try scripts/tour-hunks.sh)" >&2; exit 3; }
       done ;;
  esac

  for s in $wanted; do
    n=$((n + 1))
    caption=$(printf '%s' "$want" | tr ';' '\n' | sed -n "s/^[[:space:]]*+\?$s=//p" | head -1)
    [ -n "$caption" ] || caption="$allcap"
    printf '%s\t%s\t%s.%s\t%s\n' "$path" "$s" "$CHAPTER" "$n" "$caption" >> "$MAP"
  done
done <<< "$paths"

# ---- pass 2: emit the hunks in map order, rewriting only the @@ trailing text --------
: > "$TMP"
lastpath=
while IFS=$'\t' read -r path start code caption; do
  [ -n "$path" ] || continue
  patch_of "$path" | awk -v want="$start" -v code="$code" -v note="$caption" -v samefile="$([ "$path" = "$lastpath" ] && echo 1)" '
    /^diff --git/ { hdr = $0 "\n"; inhunk = 0; inbody = 0; next }
    !inbody && /^(index |--- |\+\+\+ |new file |deleted file |old mode |new mode |similarity |rename )/ {
      hdr = hdr $0 "\n"; next
    }
    /^@@/ {
      inbody = 1
      match($0, /\+[0-9]+/); start = substr($0, RSTART + 1, RLENGTH - 1)
      inhunk = (start == want)
      if (inhunk) {
        # Repeat the file header whenever the previous hunk came from another file, so
        # each block still says which file it is in.
        if (samefile == "") printf "%s", hdr
        match($0, /^@@[^@]*@@/)                       # keep the ranges byte-exact
        ranges = substr($0, RSTART, RLENGTH)
        tail = note != "" ? note : substr($0, RSTART + RLENGTH + 1)
        print (tail != "" ? ranges " " code " · " tail : ranges " " code)
      }
      next
    }
    inhunk { print }
  ' >> "$TMP"
  lastpath="$path"
done < "$MAP"

emitted=$(grep -c '^@@' "$TMP" || true)
assigned=$((n - ${TOUR_CODE_OFFSET:-0}))
[ "$emitted" -eq "$assigned" ] || { echo "tour-set: internal error — assigned $assigned codes but emitted $emitted hunks" >&2; exit 4; }

cut -f1,2 "$MAP" >> "$LEDGER"
sort -u "$LEDGER" -o "$LEDGER"
mv -f "$TMP" "$TOUR"

awk -F'\t' '{ printf "%-6s %-40s +%-6s %s\n", $3, $1, $2, $4 }' "$MAP"
total=$(all_pairs | wc -l | tr -d ' ')
shown=$(wc -l < "$LEDGER" | tr -d ' ')
echo "--- chapter $CHAPTER: $emitted hunks · $shown/$total of the diff shown so far · $TOUR"
[ "$shown" -lt "$total" ] && echo "--- $((total - shown)) hunks still unshown; \`rest\` puts them in a Leftovers chapter" || true
