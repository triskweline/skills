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
one (including for a PR or MR, via `gh` / `glab`). `tour-build.py` reads that file to decide
whether it can name a branch and whether `%quote` is reading the right checkout.

**Prints** the out-file path to stdout. To stderr: the hunk and file count, the base it chose
when there was no target, a note if uncommitted work was folded in, a list of untracked files
that are therefore *not* in the diff, and the pathspec if one was given. Say the base and the
untracked list to the reader — a wrong guess should be visible.

**Pins the diff's shape** with `-c diff.noprefix=false -c diff.mnemonicPrefix=false
-c diff.context=3` and `--no-ext-diff`, so a personal gitconfig cannot change what downstream
parses.

| Exit | Meaning |
|---|---|
| 0 | wrote a patch |
| 2 | bad arguments |
| 3 | target could not be resolved, or the diff is empty |
| 4 | needs `gh` or `glab` for this target and it is not installed |

---

## `bin/tour-hunks.py` — a patch → what it holds

    bin/tour-hunks.py [--body|--renames] <patch> [<path-prefix> …] [--not <path-prefix> …]

A bare path argument is a **prefix**, so `src/` selects a subtree and `src/a.js` one file.

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

    bin/tour-skeleton.py <patch> <narration> [--root DIR]

`--root` is the checkout `%quote` reads from; default is the current directory.

**This is the only command that changes your narration file, and it only ever adds a label.**
It writes an `@hN` into every `%hunk` and `%file` that lacks one, atomically, and never to a
file whose structure is broken. `path:all` is skipped — one directive standing for many
blocks cannot have one name.

**Prints to stdout** the table: chapter, beat, and for each block its label, the code it
currently resolves to, its caption and its location. That table is what a chapter narrated on
its own needs in order to refer to its neighbours.

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

## `bin/tour-build.py` — a narration file → the report

    bin/tour-build.py <patch> <narration> <out.html> [--root DIR] [--source LABEL] [--date YYYY-MM-DD]

| Flag | Effect |
|---|---|
| `--root DIR` | the checkout `%quote` reads from, and whose folder and branch the header names. Default: the current directory. |
| `--source LABEL` | what the header calls the diff, e.g. `main..HEAD`. Default: the patch's filename. |
| `--date` | overrides today's date in the header. For reproducible output; you will not normally want it. |

**Writes** `<out.html>`: one self-contained page, with the CSS, the JavaScript and the
vendored highlighter inlined. Nothing is written when validation fails.

**Prints** the absolute out-file path to stdout — the one thing to hand the reader.

**To stderr:** chapter, block and size counts; the coverage line; how many places still need
prose; and any warning. A warning is not a failure but **a report with any warning is not
finished** — Step J holds that line, not this command.

**Validation reports every problem at once and writes nothing.** Missing prose is deferred,
because most builds happen while later chapters are still skeletons.

| Exit | Meaning |
|---|---|
| 0 | built |
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
as you like. It works on a skeleton as well as a finished narration, since prose has no
bearing on what is covered.

| Exit | Meaning |
|---|---|
| 0 | everything is shown |
| 1 | something is not; it is listed on stdout |
| 2 | bad arguments, or a missing file |
| 6 | the narration does not parse, so coverage cannot be trusted |

---

## What is *not* a command

`lib/difftour/` is the implementation these five share. Nothing in it is run directly.
`assets/layout.html` is the page shell and also opens standalone in a browser as a design
fixture — see its opening comment. `vendor/prism/` is the highlighter, inlined into every
report.

## Tests

    python3 tests/test_difftour.py

Covers everything between the narration file and the HTML, plus the commands themselves from
the outside. Run it after changing anything in `lib/` or `bin/`.
