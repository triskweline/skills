#!/bin/bash
# Set the chapter the viewer is showing. Hunks are extracted byte-exact from the diff;
# only the free text after the second @@ is rewritten, into "<chapter>.<n> · <caption>".
#
#   Usage: tour-set.sh <tour-file> <source> <chapter> <spec> [<spec> …]
#
#     <source> = a git range (master..HEAD, HEAD~1..HEAD) resolved against $PWD or
#                $TOUR_REPO — or a path to a patch file, for anything git cannot name:
#                `gh pr diff 807 > /tmp/pr.patch`, `git diff HEAD > /tmp/wip.patch`.
#     <spec>   = <path>:<item>[;<item>…]   one or more per file, merged
#                <path>:all                every hunk in that file
#                rest                      every hunk not shown in an earlier chapter
#                rest:<path>=<caption>     ...and what that file's leftover group repeats,
#                                          e.g. rest:src/form.js="the same accessor swap
#                                          as 2.2, in six more call sites"
#     <item>   = <+start>[=<caption>]      +start comes from tour-hunks.sh
#
#   Captions may contain commas and "·" but not semicolons, tabs or newlines, and are
#   never truncated. Hunks are numbered in on-screen order, so 2.1 is always above 2.2.
#
#   Set TOUR_NEW=1 on the first chapter of a tour: it starts a fresh coverage ledger
#   (<tour-file>.used), which is what makes `rest` and the coverage count meaningful.
#
#   Prints the assigned codes and the running coverage. Quote the codes in the narration.
#   Exits 3 if a requested hunk does not exist, 4 if its own output disagrees with itself.
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
        /^diff --git/ { keep = 0 }
        /^\+\+\+ / { p = substr($0, 5); sub(/^[^\/]*\//, "", p); sub(/\t.*$/, "", p); keep = (p == want) }
        /^diff --git/ { hdr = $0; next }
        keep { if (hdr != "") { print hdr; hdr = "" } print }
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
    /^\+\+\+ / { p = substr($0, 5); sub(/^[^\/]*\//, "", p); sub(/\t.*$/, "", p); next }
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
    cap=$(awk -F'\t' -v p="$p" '$1 == p { print $2; exit }' "$RESTCAP")
    if [ -z "$cap" ]; then
      cap="(leftover) not narrated"
      case "$uncaptioned" in *"|$p|"*) ;; *) uncaptioned="$uncaptioned|$p|" ;; esac
    fi
    printf '%s\t%s=%s\n' "$p" "$s" "$cap" >> "$SPECS"
  done < "$MAP.rest"

  if [ -n "$uncaptioned" ]; then
    echo "tour-set: leftover groups with no caption — say what each repeats:" >&2
    printf '%s' "$uncaptioned" | tr '|' '\n' | awk 'NF' | sed 's/^/  rest:/; s/$/=.../' >&2
  fi
fi

paths=$(cut -f1 "$SPECS" | awk 'NF && !seen[$0]++')
[ -n "$paths" ] || { echo "tour-set: nothing to show (rest is empty?)" >&2; exit 3; }

# ---- pass 1: assign codes in on-screen order (file order, then line order) ----------
n=0
for path in $paths; do
  want=$(awk -F'\t' -v p="$path" '$1 == p { printf "%s;", $2 }' "$SPECS")
  starts=$(starts_of "$path")
  [ -n "$starts" ] || { echo "tour-set: no hunks at all in $path" >&2; exit 3; }

  case ";$want" in
    *";all;"*) wanted="$starts" ;;
    *) wanted=$(printf '%s' "$want" | tr ';' '\n' | sed 's/=.*//; s/^[[:space:]]*+\?//; s/[[:space:]]*$//' | grep -v '^$' | sort -n -u)
       for s in $wanted; do
         grep -qx "$s" <<<"$starts" || { echo "tour-set: no hunk at +$s in $path (try scripts/tour-hunks.sh)" >&2; exit 3; }
       done ;;
  esac

  for s in $wanted; do
    n=$((n + 1))
    caption=$(printf '%s' "$want" | tr ';' '\n' | sed -n "s/^[[:space:]]*+\?$s=//p" | head -1)
    printf '%s\t%s\t%s.%s\t%s\n' "$path" "$s" "$CHAPTER" "$n" "$caption" >> "$MAP"
  done
done

# ---- pass 2: emit the hunks, rewriting only the @@ trailing text --------------------
: > "$TMP"
for path in $paths; do
  awk -F'\t' -v p="$path" '$1 == p { print $2 "\t" $3 "\t" $4 }' "$MAP" > "$MAP.one"
  [ -s "$MAP.one" ] || continue

  patch_of "$path" | awk -v mapfile="$MAP.one" '
    BEGIN {
      FS = "\t"
      while ((getline line < mapfile) > 0) {
        split(line, f, "\t"); sel[f[1]] = 1; code[f[1]] = f[2]; note[f[1]] = f[3]
      }
      FS = " "
    }
    /^diff --git/ { hdr = $0 "\n"; inhunk = 0; emitted = 0; inbody = 0; next }
    !inbody && /^(index |--- |\+\+\+ |new file |deleted file |old mode |new mode |similarity |rename )/ {
      hdr = hdr $0 "\n"; next
    }
    /^@@/ {
      inbody = 1
      match($0, /\+[0-9]+/); start = substr($0, RSTART + 1, RLENGTH - 1)
      inhunk = (start in sel)
      if (inhunk) {
        if (!emitted) { printf "%s", hdr; emitted = 1 }
        match($0, /^@@[^@]*@@/)                       # keep the ranges byte-exact
        ranges = substr($0, RSTART, RLENGTH)
        tail = note[start] != "" ? note[start] : substr($0, RSTART + RLENGTH + 1)
        print (tail != "" ? ranges " " code[start] " · " tail : ranges " " code[start])
      }
      next
    }
    inhunk { print }
  ' >> "$TMP"
done

emitted=$(grep -c '^@@' "$TMP" || true)
[ "$emitted" -eq "$n" ] || { echo "tour-set: internal error — assigned $n codes but emitted $emitted hunks" >&2; exit 4; }

cut -f1,2 "$MAP" >> "$LEDGER"
sort -u "$LEDGER" -o "$LEDGER"
mv -f "$TMP" "$TOUR"

awk -F'\t' '{ printf "%-6s %-40s +%-6s %s\n", $3, $1, $2, $4 }' "$MAP"
total=$(all_pairs | wc -l | tr -d ' ')
shown=$(wc -l < "$LEDGER" | tr -d ' ')
echo "--- chapter $CHAPTER: $emitted hunks · $shown/$total of the diff shown so far · $TOUR"
[ "$shown" -lt "$total" ] && echo "--- $((total - shown)) hunks still unshown; \`rest\` puts them in a Leftovers chapter" || true
