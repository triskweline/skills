#!/usr/bin/env bash
#
# Get a checkout of the code the diff ends at, and print its path.
#
#   tour-checkout.sh <patch-file>
#
# Everything in a tour that is not spliced from the patch is read from a checkout:
# %quote reads a file on disk, and Step G's caller index and its "does anything test
# this" greps read the repository. A patch's end commit and your HEAD are two different
# things — touring `HEAD~3..HEAD~1`, or a pull request whose branch you never checked
# out — and on the wrong checkout all of that reads the wrong version of the code. It
# does not fail loudly: a symbol the branch introduces simply is not there, so the
# honest-looking answer to "who calls this" is "nobody".
#
# So this resolves the question once, at the start, while the human is still watching:
#
#   - HEAD is already the diff's end commit -> the repository itself, nothing to do.
#     This is the ordinary case for the default target, where the diff *is* the working
#     tree and uncommitted work belongs in it.
#   - otherwise -> a detached worktree at that commit, in a temp directory.
#
# A worktree rather than a checkout, because switching branches would move the human's
# working tree out from under them and could not be done at all with uncommitted work.
# `git worktree add` touches nothing they can see. It is idempotent here: a second run
# reuses the directory instead of piling up.
#
# Pass what it prints as --root to tour-build.py, and run the greps there.
#
# Exit: 0 printed a usable checkout   3 no recorded head, so none can be established
#       4 the commit is not here and could not be fetched   2 bad arguments

set -u

PROG=tour-checkout
REPO="${TOUR_REPO:-$PWD}"

[ $# -eq 1 ] || { sed -n '3,5p' "$0" | sed 's/^# \?//' >&2; exit 2; }
PATCH="$1"
[ -f "$PATCH" ] || { echo "$PROG: no such patch file: $PATCH" >&2; exit 2; }

git -C "$REPO" rev-parse --git-dir >/dev/null 2>&1 || {
  echo "$PROG: $REPO is not a git repository, so there is no checkout to match. Run this" >&2
  echo "$PROG: from the repository you are touring, or set TOUR_REPO." >&2
  exit 2
}

if [ ! -s "$PATCH.head" ]; then
  echo "$PROG: $PATCH records no end commit, so no checkout can be matched to it. This is" >&2
  echo "$PROG: a patch file from elsewhere. Consequences, both of which belong in the" >&2
  echo "$PROG: handover: do not use %quote at all, and treat every grep of this repository" >&2
  echo "$PROG: as evidence about a possibly different version of the code." >&2
  exit 3
fi

WANT=$(tr -d ' \t\n\r' < "$PATCH.head")
HERE=$(git -C "$REPO" rev-parse HEAD 2>/dev/null || echo none)

if [ "$WANT" = "$HERE" ]; then
  echo "$PROG: the checkout is already at ${WANT:0:9}, the commit this diff ends at." >&2
  cd "$REPO" && pwd
  exit 0
fi

# The commit has to be here before a worktree can point at it. A pull request's head is
# the usual reason it is not.
if ! git -C "$REPO" cat-file -e "$WANT^{commit}" 2>/dev/null; then
  echo "$PROG: ${WANT:0:9} is not in this repository yet; fetching." >&2
  for remote in $(git -C "$REPO" remote); do
    git -C "$REPO" fetch --quiet "$remote" "$WANT" 2>/dev/null
    git -C "$REPO" cat-file -e "$WANT^{commit}" 2>/dev/null && break
    # Servers may refuse to serve a bare sha. Fetching the remote's refs is the fallback.
    git -C "$REPO" fetch --quiet "$remote" 2>/dev/null
    git -C "$REPO" cat-file -e "$WANT^{commit}" 2>/dev/null && break
  done
fi

if ! git -C "$REPO" cat-file -e "$WANT^{commit}" 2>/dev/null; then
  echo "$PROG: commit ${WANT:0:9} is not in this repository and could not be fetched." >&2
  echo "$PROG: Without it, %quote and every grep would read a different version of the" >&2
  echo "$PROG: code. This needs a human: fetch the branch, add the remote, or say to go" >&2
  echo "$PROG: ahead without quotes. Ask now — it is the last moment anyone is watching." >&2
  exit 4
fi

# Named after the project as well as the commit, so a human looking at their temp
# directory can tell which repository a leftover worktree belongs to.
NAME=$(basename "$(cd "$REPO" && git rev-parse --show-toplevel 2>/dev/null || pwd)")
DIR="${TMPDIR:-/tmp}/difftour-$NAME-${WANT:0:12}"

# Reuse an earlier run's worktree when it is still at the right commit, so re-running
# this command is free and never accumulates directories.
if [ -d "$DIR" ] && [ "$(git -C "$DIR" rev-parse HEAD 2>/dev/null || true)" = "$WANT" ]; then
  echo "$PROG: reusing the worktree at $DIR (${WANT:0:9})." >&2
  echo "$DIR"
  exit 0
fi

if [ -e "$DIR" ]; then
  git -C "$REPO" worktree remove --force "$DIR" 2>/dev/null || rm -rf "$DIR"
fi

if ! git -C "$REPO" worktree add --detach --quiet "$DIR" "$WANT" 2>&1; then
  echo "$PROG: could not create a worktree at $DIR." >&2
  exit 4
fi

echo "$PROG: HEAD is at ${HERE:0:9} but this diff ends at ${WANT:0:9}, so quotes and" >&2
echo "$PROG: greps would read the wrong code. Added a worktree at that commit:" >&2
echo "$PROG:   $DIR" >&2
echo "$PROG: Pass it as --root, and grep there. It is a detached worktree, so nothing" >&2
echo "$PROG: about the working tree changed. Remove it when the tour is done with:" >&2
echo "$PROG:   git -C $(cd "$REPO" && pwd) worktree remove $DIR" >&2
echo "$DIR"
