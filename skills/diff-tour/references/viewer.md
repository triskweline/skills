# The paired viewer

The reader keeps a diff viewer open in a second terminal; you keep narrating in the
first. You never print hunks — you rewrite one file, and their viewer repaints.

Three scripts in `scripts/` do all of it. Don't reinvent the mechanism, and don't
hand the reader a hand-assembled `while` loop.

Contents:
- [Setting it up](#setting-it-up)
- [Driving it](#driving-it)
- [Why it is built this way](#why-it-is-built-this-way)
- [Troubleshooting](#troubleshooting)

## Setting it up

Pick a scratch path for the chapter file — a session scratchpad if the host gives you
one, otherwise `mktemp -d`. Then hand the reader **one line** to paste, with absolute
paths to both the script and the file:

```
bash /abs/path/to/skills/diff-tour/scripts/tour-view.sh /abs/path/to/scratch/tour.diff
```

The script checks its own dependencies before doing anything and names what's missing
with install hints, so you don't have to probe for `delta` yourself. `delta` and `less`
are required; `inotifywait` is optional and it falls back to polling without it.

It clears the screen, waits for the first chapter, then opens each one in a pager at the
top. `q`, `ESC ESC` and `Ctrl-C` all quit. Scrolling is arrows, PgUp/PgDn, mouse wheel,
`g`/`G`, and `/` to search.

Tell the reader it is safe to quit and re-paste at any time — the file is the state, so
a restarted viewer shows the current chapter.

## Driving it

**List the selectable hunks** for the files a chapter touches:

```bash
cd /path/to/the/repo    # or export TOUR_REPO=/path/to/the/repo
/abs/path/to/skills/diff-tour/scripts/tour-hunks.sh /abs/path/change.patch src/unpoly/form.js
```

The first column is the hunk's new-side start line, which is what selects it. Both scripts
resolve paths against `$PWD` unless `TOUR_REPO` is set — run them from the repo, never
from the skill directory, or `git diff` describes the wrong repository.

Expect the third column to be useless on some files: git's hunk context for a module
wrapped in an IIFE is the same outer line on every hunk, so eleven hunks can list
`up.form = (function() {` eleven times. When that happens the listing cannot tell you which
hunks matter — go read the diff.

**Set the chapter.** One or more specs per file; `;` separates hunks within a file; `=`
attaches the caption. Pass `TOUR_NEW=1` on the first chapter so the coverage ledger starts
fresh:

```bash
TOUR_NEW=1 /abs/path/to/skills/diff-tour/scripts/tour-set.sh /abs/path/tour.diff /abs/path/change.patch 2 \
  "src/unpoly/form.js:83=The config doc now points authors at the new guide;155=One new selector, :enabled/:disabled minus every native" \
  "spec/unpoly/form_spec.js:102=The guard spec: everything else :enabled also matches, asserted out"
```

It prints the codes it assigned, and those are what your prose quotes:

```
2.1    src/unpoly/form.js         +83     The config doc now points authors at the new guide
2.2    src/unpoly/form.js         +155    One new selector, :enabled/:disabled minus every native
2.3    spec/unpoly/form_spec.js   +102    The guard spec: everything else :enabled also matches, asserted out
```

It also reports what is still unshown, which is how you know what the Leftovers chapter
will hold:

```
--- chapter 2: 3 hunks · 3/96 of the diff shown so far · /abs/path/tour.diff
--- 93 hunks still unshown; `rest` puts them in a Leftovers chapter
```

Captions may contain commas and `·`; not semicolons, tabs or newlines. They are never
truncated. Several specs may name one file — they get merged, and codes are always
assigned in on-screen order, so `2.1` is always above `2.2`.

**Prefer the patch file Step C saved over a git range.** Both work, but a range is
re-resolved on every call, so a commit landing mid-tour shifts every `+start` and
silently invalidates the ledger — the selectors *and* the coverage count. A saved patch
is immune. A range stays useful for a quick one-chapter look:

```bash
gh pr diff 807 > /tmp/pr.patch        # or: git diff <base>..HEAD > /tmp/change.patch
tour-set.sh /abs/path/tour.diff /tmp/pr.patch 2 "src/form.js:83=the new selector"
```

**Finish with a Leftovers chapter.** The pseudo-spec `rest` selects every hunk no earlier
chapter showed — the hunks no topic claimed, never a topic's own follow-ups. Give each
file's group a line saying what it is and why no topic wanted it; `rest` on its own labels
them `(leftover) not narrated` and warns you about every group you left bare:

```bash
tour-set.sh /abs/path/tour.diff /abs/path/change.patch 7 rest \
  "rest:.gitignore=an unrelated ignore rule for local plan notes" \
  "rest:tooling/toc.mjs=the test-tooling body of work, offered as its own tour"
# 7.72   tooling/toc.mjs   +1   the test-tooling body of work, offered as its own tour
# --- chapter 7: 93 hunks · 96/96 of the diff shown so far
```

Length costs nothing here — the viewport scrolls as far as it needs to, and the reader
decides whether to scroll. See
[Every hunk gets shown](../SKILL.md#nothing-is-hidden).

**Re-run `tour-hunks.sh` for every chapter when you drive from a git range.** Line
numbers are relative to the current tip, and a branch can gain commits mid-session. A
stale selector fails with `no hunk at +682 in …` and exit 3 rather than quietly showing
less than you asked for — if you see that, re-list, don't guess. Driving from a saved
patch avoids the whole problem, which is why it is the default.

`tour-hunks.sh` takes the same `<source>` as `tour-set.sh` — a patch file or a git
range — so both halves of the tour read the same diff.

## Why it is built this way

Four properties are worth preserving if you ever rewrite these scripts.

**Hunks are never retyped.** `tour-set.sh` pipes real `git diff` output and rewrites only
the free text after the second `@@`, leaving the `-x,y +a,b` ranges byte-exact. This is
the skill's fidelity rule enforced mechanically instead of by your care.

**Colored bytes never enter your context.** You write ~4 KB of plain text; `delta` runs
in the reader's terminal. ANSI rendering costs roughly 10× the plain size, so piping
`delta` through your own tool calls would burn context and hit output caps. Here chapter
length is unbounded.

**Updates are atomic.** `tour-set.sh` writes `tour.diff.tmp` and `mv`s it into place, so
the viewer never renders a half-written file. Because `mv` swaps the inode, the watch is
on the *directory* with an `--include` filter on the basename — never on the file itself,
which would go deaf after the first swap. The filter also has to exclude the `.tmp` and
rendered files, or delta's own writes retrigger the watch forever.

**A new chapter interrupts the pager.** A background watcher touches a sentinel file and
`pkill`s `less` when the chapter changes; the loop then re-renders and reopens at the top.
The sentinel — not `less`'s exit status — is what distinguishes the two ways out, because
`less` installs a SIGTERM handler and exits 15 on some builds and 143 on others. Sentinel
present means a new chapter; absent means the reader left. That is why quit keys don't
need enumerating.

**Captions are prose, so they must not be highlighted as code.** Delta's default
`--hunk-header-style` includes its special `syntax` attribute, which colours the hunk
header with the file's language rules — `2.1` comes out as a numeric literal and every
caption word as an identifier, which reads as a rendering fault. The viewer passes
`--hunk-header-style 'bold yellow'` so the caption is one uniform run, and drops the
`line-number` attribute because the code replaces it and `--line-numbers` already numbers
every row.

Two smaller ones: `--width "$(tput cols)"` is recomputed per render because delta can't
detect width when writing to a file — so a terminal resized mid-chapter stays wrapped for
the old width until the next chapter — and `ESC ESC` rather than bare `ESC` quits because
arrow keys transmit as `ESC [ A` and a bare binding fires on every scroll.

## Troubleshooting

**Reader says nothing appeared** — check the file exists and is non-empty. Before the
first `tour-set.sh` the viewer sits on "waiting for the first chapter".

**Reader says it didn't change** — they may be on an older viewer process from before a
script edit. Ask them to quit and re-paste.

**`no hunk at +N`** — the branch moved. Re-run `tour-hunks.sh`.

**Reader wants to keep a chapter while you move on** — they can't; the file is single
state. Paste that hunk inline instead, or wait. This is the viewer's real cost: comparing
chapter 2 against chapter 5 is one of the most valuable things a reviewer does, and this
mode forbids it. If the reader starts doing that, offer `inline` or `export`.

**Quitting wipes the screen** — `finish()` calls `clear`, so the tour leaves no scrollback
in viewer mode. Say so when you offer the mode.

**Reader prefers side-by-side** — `--side-by-side` needs ~160 columns and wraps long
lines badly. Offer it, don't default to it.
