#!/bin/bash
# Resolve any tour target to a patch file, and print the path.
#
#   Usage: tour-fetch.sh <out-file> [<target>]
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
# Everything downstream — tour-hunks.sh, tour-set.sh, tour-ansi.sh — consumes the patch
# file, never the target. That is what makes a tour immune to the branch moving under
# it, and it is why every source type only has to be understood here.
#
# If a host has an MCP server for GitHub or GitLab, fetching the diff through that and
# saving it to <out-file> is equivalent — this script is a convenience, not a gate.
set -euo pipefail

[ $# -ge 1 ] || { echo "usage: tour-fetch.sh <out-file> [<target>]" >&2; exit 2; }
OUT="$1"; TARGET="${2:-}"
REPO="${TOUR_REPO:-$PWD}"
mkdir -p "$(dirname "$OUT")"

default_branch() {
  git -C "$REPO" symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||' \
    || for b in main master trunk; do git -C "$REPO" show-ref --verify --quiet "refs/heads/$b" && { echo "$b"; return; }; done
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
    git -C "$REPO" diff "$(default_branch)...$1" > "$OUT"       # a branch: three dots
  else
    git -C "$REPO" diff "$1^..$1" > "$OUT"                      # one commit
  fi
}

case "$TARGET" in
  "")
    base=$(git -C "$REPO" merge-base --fork-point "$(default_branch)" HEAD 2>/dev/null \
        || git -C "$REPO" merge-base "$(default_branch)" HEAD)
    git -C "$REPO" diff "$base..HEAD" > "$OUT"
    # Uncommitted work is part of "what I am looking at", so fold it in.
    if [ -n "$(git -C "$REPO" status --porcelain --untracked-files=no)" ]; then
      git -C "$REPO" diff "$base" > "$OUT"       # one coherent diff, base -> working tree
      echo "tour-fetch: included uncommitted changes" >&2
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
    git -C "$REPO" diff "$TARGET" > "$OUT" ;;
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
      if command -v gh >/dev/null && gh pr diff "$TARGET" > "$OUT" 2>/dev/null && [ -s "$OUT" ]; then :
      elif command -v glab >/dev/null && glab mr diff "$TARGET" --raw > "$OUT" 2>/dev/null && [ -s "$OUT" ]; then :
      elif git_ref "$TARGET"; then echo "tour-fetch: no PR/MR $TARGET; treated it as a git object" >&2
      else echo "tour-fetch: $TARGET is neither a PR/MR here nor a git object (tried gh, glab and git)" >&2; exit 3; fi
    fi ;;
  *)
    git_ref "$TARGET" || { echo "tour-fetch: cannot resolve target: $TARGET" >&2; exit 3; } ;;
esac

[ -s "$OUT" ] || { echo "tour-fetch: the diff is empty" >&2; exit 3; }
echo "$OUT"
echo "tour-fetch: $(grep -c '^@@' "$OUT") hunks, $(grep -c '^diff --git' "$OUT") files -> $OUT" >&2
