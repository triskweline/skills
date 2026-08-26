#!/bin/bash
# Resolve any tour target to a patch file, and print the path.
#
#   Usage: tour-fetch.sh <out-file> [<target>] [-- <pathspec> …]
#
#     A trailing "-- <pathspec>" narrows the diff to those paths. Use it when the
#     reader asked for part of a range: the patch itself becomes the smaller thing, so
#     coverage still means "all of it" and the report can say honestly what was left
#     out. Never narrow to make a tour cheaper — that hides work behind a guarantee
#     that no longer covers it.
#
#     <target> forms, autodetected:
#       (omitted)                    this branch since its branch point, plus uncommitted work
#       a..b  a...b                  a git range
#       <sha> <tag> <branch>         one commit, or a branch against the default branch
#       <n>                          PR/MR number in the current repo (tries gh, then glab)
#       https://…/pull/<n>           a GitHub pull request
#       https://…/merge_requests/<n> a GitLab merge request
#       <path>.patch  <path>.diff    an existing patch file, copied through
#
# Everything downstream — tour-hunks.py, tour-build.py, tour-rest.py — consumes the
# patch file, never the target. That is what makes a tour immune to the branch moving
# under it, and it is why every source type only has to be understood here.
#
# It also writes <out-file>.head with the commit the diff ends at, when there is one.
# tour-build.py compares that against the checkout it reads %quote context from, so a
# tour of someone else's PR cannot quote the wrong version of a file.
#
# If a host has an MCP server for GitHub or GitLab, fetching the diff through that and
# saving it to <out-file> is equivalent — this script is a convenience, not a gate.
set -euo pipefail

# A patch's *shape* must not depend on whoever ran this. diff.noprefix drops the a/ b/
# that every path parser downstream relies on, diff.context changes how much unchanged
# text a hunk carries, and an external diff driver replaces the output wholesale. Pin
# the first two by config; the third has no config that unsets it, so a "diff" argument
# gets --no-ext-diff. (Setting diff.external to the empty string makes git try to *run*
# it, which is a different and much louder failure.)
git() {
  local args=() a
  for a in "$@"; do
    args+=("$a")
    [ "$a" = diff ] && args+=(--no-ext-diff)
  done
  command git -c diff.noprefix=false -c diff.mnemonicPrefix=false -c diff.context=3 \
              "${args[@]}"
}

[ $# -ge 1 ] || { echo "usage: tour-fetch.sh <out-file> [<target>] [-- <pathspec> …]" >&2; exit 2; }
OUT="$1"; TARGET="${2:-}"
# Everything after -- is a pathspec, passed to git and reported in the summary.
PATHS=()
if [ $# -gt 2 ]; then
  shift 2
  [ "${1:-}" = -- ] && shift
  PATHS=("$@")
fi
REPO="${TOUR_REPO:-$PWD}"
PR_KIND=       # how a bare-number target resolved: gh, glab or git
mkdir -p "$(dirname "$OUT")"

# Empty output means "I could not tell", and every caller has to treat that as a
# question for the human rather than interpolating it. Interpolating it produced two
# silent wrong answers: a raw `fatal: Not a valid object name ` with exit 128 for the
# default target, and — worse — `HEAD...branch` for a branch target, which is empty
# whenever you are standing on that branch, so the agent told the reader a real branch
# had nothing to tour.
default_branch() {
  local b
  b=$(git -C "$REPO" symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')
  [ -n "$b" ] && { echo "$b"; return 0; }
  for b in main master trunk; do
    git -C "$REPO" show-ref --verify --quiet "refs/heads/$b" && { echo "$b"; return 0; }
  done
  return 1
}

# Sets DB, or exits. Not a command substitution: `exit` inside $( ) leaves only the
# subshell, so the script would print the explanation and then carry on to produce the
# empty diff it was trying to prevent.
require_default_branch() {
  DB=$(default_branch) && [ -n "$DB" ] && return 0
  echo "tour-fetch: cannot tell which branch is this repository's default — there is no" >&2
  echo "tour-fetch: origin/HEAD, and no main, master or trunk. Pass an explicit range" >&2
  echo "tour-fetch: instead, e.g. 'some-branch...$(git -C "$REPO" rev-parse --abbrev-ref HEAD 2>/dev/null || echo HEAD)'." >&2
  exit 3
}

need() { command -v "$1" >/dev/null || { echo "tour-fetch: needs $1 for this target" >&2; exit 4; }; }

# A ref: one commit, or a branch compared against the default branch.
git_ref() {
  git -C "$REPO" rev-parse --verify --quiet "$1^{commit}" >/dev/null || return 1
  # HEAD, @ and anything with ~ or ^ name a commit, never a branch to compare.
  # (origin/HEAD exists as a ref, so the branch test would otherwise claim "HEAD".)
  if [ "$1" != HEAD ] && [ "$1" != @ ] && [ "${1%%[~^]*}" = "$1" ] \
  && { git -C "$REPO" show-ref --verify --quiet "refs/heads/$1" \
    || git -C "$REPO" show-ref --verify --quiet "refs/remotes/origin/$1"; }; then
    require_default_branch
    git -C "$REPO" diff "$DB...$1" -- "${PATHS[@]}" > "$OUT"                      # a branch: three dots
  else
    git -C "$REPO" diff "$1^..$1" -- "${PATHS[@]}" > "$OUT"                      # one commit
  fi
}

case "$TARGET" in
  "")
    require_default_branch
    base=$(git -C "$REPO" merge-base --fork-point "$DB" HEAD 2>/dev/null \
        || git -C "$REPO" merge-base "$DB" HEAD)
    git -C "$REPO" diff "$base..HEAD" -- "${PATHS[@]}" > "$OUT"
    # Uncommitted work is part of "what I am looking at", so fold it in.
    if [ -n "$(git -C "$REPO" status --porcelain --untracked-files=no)" ]; then
      git -C "$REPO" diff "$base" -- "${PATHS[@]}" > "$OUT"       # one coherent diff, base -> working tree
      echo "tour-fetch: included uncommitted changes" >&2
    fi
    # A brand-new file is invisible to `git diff`, so it would be missing from the
    # patch and therefore from coverage, which cannot know what it was never given.
    untracked_all=$(git -C "$REPO" ls-files --others --exclude-standard)
    untracked_n=$(printf '%s' "$untracked_all" | grep -c . || true)
    untracked=$(printf '%s\n' "$untracked_all" | head -20)
    if [ -n "$untracked" ]; then
      echo "tour-fetch: these files are untracked, so they are NOT in the diff:" >&2
      # Indent each line without splitting on spaces — an untracked "my notes.md"
      # is exactly the kind of file a reviewer needs to hear about.
      printf '%s\n' "$untracked" | sed 's/^/  /' >&2
      [ "$untracked_n" -gt 20 ] && echo "  …and $((untracked_n - 20)) more" >&2
      echo "tour-fetch: git add them to include them, or say so in the overview." >&2
    fi
    echo "base $base" >&2
    ;;
  *.patch|*.diff)
    [ -f "$TARGET" ] || { echo "tour-fetch: no such patch file: $TARGET" >&2; exit 3; }
    cp -f "$TARGET" "$OUT" ;;
  *://*/pull/*|*://*/pulls/*)
    need gh
    slug=$(printf '%s' "$TARGET" | sed -E 's|^[a-z]+://[^/]+/([^/]+/[^/]+)/pulls?/([0-9]+).*|\1|')
    num=$(printf '%s' "$TARGET" | sed -E 's|.*/pulls?/([0-9]+).*|\1|')
    gh pr diff "$num" --repo "$slug" > "$OUT" ;;
  *://*/merge_requests/*)
    need glab
    slug=$(printf '%s' "$TARGET" | sed -E 's|^[a-z]+://[^/]+/(.+)/-/merge_requests/[0-9]+.*|\1|')
    num=$(printf '%s' "$TARGET" | sed -E 's|.*/merge_requests/([0-9]+).*|\1|')
    glab mr diff "$num" --repo "$slug" --raw > "$OUT" ;;
  *..*)
    git -C "$REPO" diff "$TARGET" -- "${PATHS[@]}" > "$OUT" ;;
  [0-9]*)
    if [ -n "${TARGET//[0-9]/}" ]; then
      # Digits plus something else — a sha like 9290f61a, not a PR number.
      git_ref "$TARGET" || { echo "tour-fetch: cannot resolve target: $TARGET" >&2; exit 3; }
    else
      # A bare number is a PR or MR in this repo. Try GitHub, then GitLab.
      # An all-digit string can be both a PR number and an abbreviated sha. Say which won.
      if git -C "$REPO" rev-parse --verify --quiet "$TARGET^{commit}" >/dev/null; then
        echo "tour-fetch: $TARGET is also a git object here; using the PR/MR. Pass ${TARGET}^{commit} for the commit." >&2
      fi
      # gh and glab find the repository from the working directory, so they run in
      # $REPO like every git call here. PR_KIND records which one answered, because
      # the .head below has to ask the same forge and cannot re-derive that.
      if command -v gh >/dev/null && (cd "$REPO" && gh pr diff "$TARGET") > "$OUT" 2>/dev/null && [ -s "$OUT" ]; then PR_KIND=gh
      elif command -v glab >/dev/null && (cd "$REPO" && glab mr diff "$TARGET" --raw) > "$OUT" 2>/dev/null && [ -s "$OUT" ]; then PR_KIND=glab
      elif git_ref "$TARGET"; then PR_KIND=git; echo "tour-fetch: no PR/MR $TARGET; treated it as a git object" >&2
      else echo "tour-fetch: $TARGET is neither a PR/MR here nor a git object (tried gh, glab and git)" >&2; exit 3; fi
    fi ;;
  *)
    git_ref "$TARGET" || { echo "tour-fetch: cannot resolve target: $TARGET" >&2; exit 3; } ;;
esac

[ -s "$OUT" ] || { echo "tour-fetch: the diff is empty" >&2; exit 3; }

# The commit the diff ends at, for the %quote check and the header's branch name in
# tour-build.py. A PR is the case both were built for, so ask the forge for its head
# rather than skipping it. A patch file from elsewhere has no such commit here.
rm -f "$OUT.head"
case "$TARGET" in
  *.patch|*.diff) ;;
  *://*/pull/*|*://*/pulls/*)
    gh pr view "$num" --repo "$slug" --json headRefOid -q .headRefOid > "$OUT.head" 2>/dev/null \
      || rm -f "$OUT.head" ;;
  *://*/merge_requests/*)
    glab mr view "$num" --repo "$slug" -F json 2>/dev/null \
      | sed -n 's/.*\"sha\":[[:space:]]*\"\([0-9a-f]*\)\".*/\1/p' | head -1 > "$OUT.head" \
      || rm -f "$OUT.head"
    [ -s "$OUT.head" ] || rm -f "$OUT.head" ;;
  *..*) git -C "$REPO" rev-parse --verify --quiet "${TARGET##*..}^{commit}" > "$OUT.head" 2>/dev/null || rm -f "$OUT.head" ;;
  [0-9]*)
    case "$PR_KIND" in
      gh)   (cd "$REPO" && gh pr view "$TARGET" --json headRefOid -q .headRefOid) > "$OUT.head" 2>/dev/null || rm -f "$OUT.head" ;;
      glab) (cd "$REPO" && glab mr view "$TARGET" -F json) 2>/dev/null \
              | sed -n 's/.*\"sha\":[[:space:]]*\"\([0-9a-f]*\)\".*/\1/p' | head -1 > "$OUT.head" \
              || rm -f "$OUT.head" ;;
      *)    git -C "$REPO" rev-parse --verify --quiet "$TARGET^{commit}" > "$OUT.head" 2>/dev/null || rm -f "$OUT.head" ;;
    esac
    [ -s "$OUT.head" ] || rm -f "$OUT.head" ;;
  "") git -C "$REPO" rev-parse --verify --quiet 'HEAD^{commit}' > "$OUT.head" 2>/dev/null || rm -f "$OUT.head" ;;
  *) git -C "$REPO" rev-parse --verify --quiet "$TARGET^{commit}" > "$OUT.head" 2>/dev/null || rm -f "$OUT.head" ;;
esac

echo "$OUT"
echo "tour-fetch: $(grep -c '^@@' "$OUT") hunks, $(grep -c '^diff --git' "$OUT") files -> $OUT" >&2
[ ${#PATHS[@]} -eq 0 ] || echo "tour-fetch: narrowed to ${PATHS[*]} — say so in the overview" >&2
