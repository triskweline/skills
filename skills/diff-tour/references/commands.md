# The commands

Everything `bin/` does, so none of it has to be guessed. The procedure in
[SKILL.md](../SKILL.md) says *when* to reach for each one; this says exactly what each takes,
what it prints, what it changes on disk, and what its exit code means.

Two conventions hold everywhere:

- **`<patch> <narration>` come first, in that order**, in every command that takes them, so
  one invocation can be retyped from another.
- **stdout is the answer, stderr is the commentary.** What a command is *for* goes to stdout
  and can be piped or pasted; counts, warnings and advice go to stderr. `2>/dev/null` gives
  you the answer alone.

Every command prints its own usage to stderr and exits 2 when called wrongly, so `--help` is
never needed — a wrong call tells you the right one.

---

## `bin/tour-fetch.sh` — any target → a patch file

    bin/tour-fetch.sh <out-file> [<target>] [-- <pathspec> …]

**Run it from inside the repository you are touring.** It resolves a git target against the
current directory unless `TOUR_REPO` names another, so running it elsewhere silently produces
a patch of the wrong repository, or an empty one.

| Target | What you get |
|---|---|
| *omitted* | this branch since its branch point, plus uncommitted work |
| `a..b`, `a...b` | that range |
| `abc123`, `HEAD`, `HEAD~2` | that one commit |
| `some-branch` | the branch against the default branch, three dots |
| `807` | PR or MR number in this repo — tries `gh`, then `glab` |
| `https://…/pull/807` | that GitHub pull request |
| `https://…/-/merge_requests/42` | that GitLab merge request |
| `/tmp/x.patch`, `*.diff` | copied through unchanged |

`-- <pathspec> …` narrows the diff to those paths. Use it when the reader asked for part of a
range: the patch itself becomes the smaller thing, so coverage still means "all of it".
**Never narrow to make a tour cheaper** — that hides work behind a guarantee that no longer
reaches it.

**Writes** `<out-file>`, and `<out-file>.head` with the commit the diff ends at when there is
one (including for a PR or MR by number or URL, via `gh` / `glab`). That file is what
`tour-checkout.sh` matches a checkout to, and what `tour-build.py` reads to decide whether it
can name a branch and whether `%quote` is reading the right checkout. Only a patch file from
elsewhere has no head recorded.

**Prints** the out-file path to stdout. To stderr: the hunk and file count, the base it chose
when there was no target, a note if uncommitted work was folded in, a list of untracked files
that are therefore *not* in the diff (the first 20, then how many more), and the pathspec if
one was given. Say the base and the untracked list to the reader — a wrong guess should be
visible.

**It refuses rather than guessing when it cannot tell which branch is the default** — no
`origin/HEAD`, and no `main`, `master` or `trunk`. Interpolating an empty branch name there
produced a raw git error for the default target and, for a branch target, an *empty diff* that
looked like a real answer.

**Pins the diff's shape** with `-c diff.noprefix=false -c diff.mnemonicPrefix=false
-c diff.context=3` and `--no-ext-diff`, so a personal gitconfig cannot change what downstream
parses.

| Exit | Meaning |
|---|---|
| 0 | wrote a patch |
| 2 | bad arguments |
| 3 | target could not be resolved, the default branch could not be determined, or the diff is empty |
| 4 | needs `gh` or `glab` for this target and it is not installed |

---

## `bin/tour-checkout.sh` — a patch → a checkout of the code it ends at

    bin/tour-checkout.sh <patch>

**Prints on stdout the path to pass as `--root` and to grep in.** Hunks come from the patch
and are always exact; everything else a tour reads comes off a disk — `%quote` reads a file,
and Step G's caller index greps a repository — and those have to read the version of the code
*this diff ends at*. Your HEAD is often not that: `HEAD~3..HEAD~1` does not end at HEAD, and
`gh pr diff 807` works whether or not the branch was ever fetched. On the wrong version a
quote shows the wrong lines, and a grep for callers of a symbol the branch introduces finds
nothing — so the report says "no other callers" and means "I looked in a tree without it".
Neither failure announces itself.

What it prints is either **the repository itself**, when HEAD is already the diff's end commit
(the ordinary case for the default target, where the diff *is* the working tree and
uncommitted work belongs in the tour), or **a detached worktree** at that commit under
`$TMPDIR`. It never switches your branch and never touches the working tree, so uncommitted
work is not in its way. It is idempotent: a second run reuses the worktree rather than adding
another.

Run it in [Step B](../SKILL.md#step-b-get-the-diff-and-a-checkout-that-matches-it), while the
human is still watching, because exit 4 is a question only they can answer. A worktree it
created is the tour's own leftover — the removal command is on stderr, and Step J passes it on.

| Exit | Meaning |
|---|---|
| 0 | stdout holds a usable checkout |
| 2 | bad arguments, no such patch, or not a git repository |
| 3 | the patch records no end commit, so none can be matched — don't `%quote`, and treat every grep as evidence about a possibly different version |
| 4 | the commit is not here and could not be fetched — ask the human now |

---

## `bin/tour-hunks.py` — a patch → what it holds

    bin/tour-hunks.py [--body|--renames] <patch> [<path-prefix>|<selector> …] [--not <path-prefix> …]

A bare path argument is a **prefix**, so `src/` selects a subtree and `src/a.js` one file.

**A path argument may also be a selector**, in exactly the syntax a narration uses:
`src/a.js:687` is one hunk, `src/a.js:687#1-120` is a slice of it. That is how you read half
of a 28 KB hunk without printing all of it twice, and it is the only way to give `--body` a
sub-file target — a prefix cannot. An unknown path or hunk exits 3 rather than printing
nothing.

| Flag | Effect |
|---|---|
| *(none)* | the cheap read: one line per file, one per hunk |
| `--body`, `-b` | also print the diff, with a body offset in the left margin |
| `--renames` | group the swaps that repeat across hunks; print nothing else |
| `--not`, `-x` | skip these paths. Repeatable, and it beats a prefix. |

### The cheap read

```
■ src/unpoly/classes/params.js · changed · 7 hunks · 209 body lines, 136 changed · 7.8 KB to read
  @34 · 9 body lines · up.Params = class Params {
  @497 · 62 body lines · 5 runs: 4-5, 10-16, 20-21, 26-53, 57-59 · up.Params = class Params {
```

- `@497` is the **selector** a narration file uses: `%hunk src/unpoly/classes/params.js:497`.
- `7.8 KB to read` is what `--body` on that file would print. **Keep a single `--body` call
  under about 30 KB** — tool output truncates past roughly that, and a truncated read has to
  be redone narrower.
- `runs:` appears when a hunk's changed lines fall in more than one stretch, which usually
  means more than one idea. **Those are the fragment boundaries**, and the context between
  them is where a cut belongs: `%hunk …:497 #26-53`. You do not need a `--body` read to find
  them.
- A file with no diff body says so and tells you to select it with `%file` — a binary, a pure
  rename, a mode change.

### `--body`

The same listing with each hunk's diff under it, every line numbered from 1 within its hunk.
Those numbers are what `#<lo>-<hi>` means. Afterwards it reports to stderr how much it
printed, and says outright when that was over ~30 KB and probably truncated.

**Reading narrow then wide reprints the narrow part**, because a path argument is a prefix.
That is what `--not` is for:

    bin/tour-hunks.py --body p.patch src/forms --not src/forms/a.js

### `--renames`

Groups the hunks where every changed line is the same substitution, and where that
substitution repeats across hunks:

```
'links_to_content'  ->  'external_link_enabled'    (15 hunks)
  app/models/card.rb:88
  …
```

It reports the **minimal** substitution — `call(oldName)` → `call(newName)` is `old` → `new`,
because `Name)` is shared. A swap appearing in one hunk only is a change, not a sweep, and is
not reported. To stderr: how many hunks are in sweeps and how many still need reading.

Those hunks are the mechanical tier — one caption naming the swap, no individual reading — and
**grep the old name afterwards for stragglers**, which is what catches a missed call site.

| Exit | Meaning |
|---|---|
| 0 | printed a listing |
| 2 | bad arguments, or no such patch file |
| 3 | nothing in the patch matches the given paths |

---

## `bin/tour-skeleton.py` — check a skeleton, label it, print the table

    bin/tour-skeleton.py <patch> <narration> [--root DIR] [--labels h1,h2,…]

`--root` is the checkout `%quote` reads from; default is the current directory.

**This is the only command that changes your narration file, and it only ever adds a label.**
It writes an `@hN` into every `%hunk` and `%file` that lacks one, atomically, and never to a
file whose structure is broken. `path:all` is skipped — one directive standing for many
blocks cannot have one name.

**Prints to stdout** the table: each chapter with **how many blocks it holds** — which is
what Step G's fork packing is decided from — then each beat, and for each block its label,
the code it currently resolves to, its caption and its location.

**The location column says where the block starts, not how you wrote it.** Write
`%hunk app/card.rb:25 #36-50` and the table shows `app/card.rb:59 #36-50`, because line 59 is
where that fragment begins. Your file is untouched — the command only ever adds labels — but
the column is a *report*, not an echo, and two separate runs read it as a silent rewrite. That table is what a chapter narrated on
its own needs in order to refer to its neighbours.

After the table, when there is more than one cluster chapter holding blocks, it prints a
**suggested fork packing** for Step G: the chapters grouped so that no group holds more than
the biggest single chapter, or a sixth of all the blocks, whichever is larger. The first is
the floor on wall clock however many forks you spawn; the second stops a dozen small chapters
from suggesting a dozen forks, each paying a context re-prefill to save almost nothing.

**`--labels h39,h70,h115` prints just those rows** — label, code, caption, location and the
chapter each sits in — instead of the whole table. Step I says to read a label's caption
before citing it; on a report with a hundred labels that check has to be one command, or it
loses to citing from memory. Exit 1 if any label does not exist.

**To stderr:** how many blocks were labelled, whether every changed line is placed, how many
places still need prose, and whether any `[[label]]` does not resolve yet.

Missing prose and unresolved references are **premature** here, not errors — a skeleton has
neither by definition, and refusing a reference would deadlock the command that mints the
labels it names.

| Exit | Meaning |
|---|---|
| 0 | every changed line is placed |
| 1 | some are not — `bin/tour-rest.py` lists them |
| 2 | bad arguments, or the narration cannot be written |
| 6 | the structure is wrong; nothing written |

---

## `bin/tour-splice.py` — narrated chapters → back into the narration

    bin/tour-splice.py [--check] [--root DIR] <patch> <narration> <chapter-file> …

Step G narrates chapters in parallel, each fork writing **one file per chapter it owns**
and nothing else. Forks only ever read the narration file — the orchestrator is the only
writer, adding Leftovers while they work — so there is no race. This puts the chapters back.

A chapter file must begin with the chapter directive it replaces, and its title must match
exactly one chapter in the narration — **matching on the title, not on position or filename**,
so a fork cannot land its work on the wrong chapter and argument order does not matter.
`%report`, `%intro`, `%leftovers` and `%closing` stay where they are.

**The title is therefore frozen**, and checked before anything is placed: a fork that
improves its chapter's title while narrating would otherwise pass its own `--check` and fail
here, after spending its whole budget.

**Every part is validated before any part is placed**, so a malformed chapter file cannot
leave the narration half-updated. A chapter file is the middle of a document, so it is checked
inside a minimal envelope: rules about the whole document — a missing `%report`, no `%closing`
— are not held against it, and the line numbers reported are its own.

It also **compares labels with the chapter it replaces** and refuses a file that dropped one.
A fork that retypes a directive instead of copying it loses its `@hN`, and then every
`[[…]]` a sibling chapter wrote at that block fails at build time, in prose whoever is
splicing never read.

**Every spec is resolved, not just parsed** — a hunk that does not exist, a fragment outside
its hunk, a quote range no file has. Those are the specs a *fork* writes, since forks add
`%quote` and split their own hunks, so they are the only ones that can be wrong. `--root` is
where quotes are read from, as everywhere else.

**`--check` does the validation and writes nothing.** That is how a fork verifies its own
chapter before returning it, when a mistake still costs only its own minute.

**Two files claiming the same chapter are refused.** Splicing both would keep whichever came
last and drop the other silently — a whole fork's narration gone, while the wrap-up is
written from both forks' reports.

**Writes** the narration, atomically, once, after every part has been placed. **Prints** what
it replaced. To stderr: how many chapters were spliced, and the title of any cluster chapter
still un-narrated — so a fork that failed is visible now, rather than as a wall of "no prose"
on the next build.

| Exit | Meaning |
|---|---|
| 0 | spliced, or `--check` found nothing wrong |
| 2 | bad arguments, or a missing file |
| 6 | a chapter file does not parse, has a spec that does not resolve, has no chapter directive, names no chapter or several, collides with another part, or drops a label; nothing written |

---

## `bin/tour-build.py` — a narration file → the report

    bin/tour-build.py <patch> <narration> <out.html> [--root DIR] [--source LABEL] [--date YYYY-MM-DD] [--final]

| Flag | Effect |
|---|---|
| `--root DIR` | the checkout `%quote` reads from, and whose folder and branch the header names. Default: the current directory. |
| `--source LABEL` | what the header calls the diff, e.g. `main..HEAD`. Default: the patch's filename. |
| `--date` | overrides today's date in the header. For reproducible output; you will not normally want it. |
| `--final` | exit 1, and print no path on stdout, if anything is unshown, pending or warned about. Notes do not count. |

**Writes** `<out.html>`: one self-contained page, with the CSS, the JavaScript and the
vendored highlighter inlined. Nothing is written when validation fails.

**Prints** the absolute out-file path to stdout — the one thing to hand the reader.

**To stderr:** chapter, block and size counts; the coverage line; how many places still need
prose; and any warning.

**A report with an unshown line, a pending item or a warning is not finished.** An ordinary
build still exits 0 in that state, on purpose: most builds happen while later chapters are
still skeletons. **`--final` is the build that refuses** — it writes the file, says what is
wrong, prints no path on stdout and exits 1. Use it for the last build before you hand a path
to anyone, so that the one property this skill cannot compute for you is the one thing you
have to type.

**A note is not a warning.** Some checks cannot tell right from wrong — a fragment overlapping
another is either a deliberate re-show, which the splitting rules ask for, or an off-by-one,
and nothing mechanical distinguishes them. Those print as `note` and never refuse: a gate that
fires on correct work teaches whoever meets it to route around the gate.

**Validation reports every problem at once and writes nothing.** Missing prose is deferred,
because most builds happen while later chapters are still skeletons.

| Exit | Meaning |
|---|---|
| 0 | built |
| 1 | `--final`, and something is unshown, pending or warned about |
| 2 | bad arguments, a missing file, or a patch whose hunks cannot all be selected |
| 6 | the narration is wrong; nothing written |

---

## `bin/tour-rest.py` — what the narration does not show yet

    bin/tour-rest.py <patch> <narration>

**Prints to stdout** the changed lines and bodyless changes nothing covers, already formatted
as `%hunk` and `%file` directives with `%#` comments, so the whole block can be pasted into
the narration file and then captioned. Where a gap sits next to a fragment you already show,
it says which fragment to widen instead — widening is the fix, not pasting an orphan.

It is a pure function of the two files: no state, nothing to go stale, safe to run as often
as you like, and **it takes no `--root` because it reads nothing from disk** — `%quote` is
skipped, since coverage cannot depend on a quote. That matters on the ordinary PR tour, where
the checkout is a worktree and a quote correct there would look out of range from anywhere
else. It works on a skeleton as well as a finished narration, since prose has no bearing on
what is covered.

| Exit | Meaning |
|---|---|
| 0 | everything is shown |
| 1 | something is not; it is listed on stdout |
| 2 | bad arguments, or a missing file |
| 6 | the narration does not parse, so coverage cannot be trusted |

---

## What is *not* a command

`lib/difftour/` is the implementation these commands share. Nothing in it is run directly.
`assets/layout.html` is the page shell and also opens standalone in a browser as a design
fixture — see its opening comment. `vendor/prism/` is the highlighter, inlined into every
report.

## Tests

    python3 tests/test_difftour.py

Covers everything between the narration file and the HTML, plus the commands themselves from
the outside. Run it after changing anything in `lib/` or `bin/`.
