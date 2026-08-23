# Rendering the report

One narration file, one builder, three renderings. Read this once you know the format; the
rules that decide *what* the report says are all in SKILL.md and do not vary by format.

## The narration file

Write markdown, with one placeholder line wherever a hunk belongs:

    %%hunk <path>:<+start>[@<code>][=<caption>]

- `<+start>` comes from `scripts/tour-hunks.sh`.
- `@<code>` pins a code instead of assigning the next one — for a chapter re-showing a hunk
  another chapter owns, so the hunk keeps one code across the whole report.
- Several hunks in one placeholder: `path:12=first;48=second`.

**Build it a chapter at a time, appending.** A validation failure then costs an edit rather
than a regeneration — on a large report the narration is tens of thousands of tokens and
rewriting it whole is the single most expensive mistake available.

## Building

    scripts/tour-report.sh <out-file> <source> <narration-file> [md|ansi|html]

Everything that is not a placeholder is rendered as prose. Every placeholder is replaced by
that hunk, byte-exact from the source, so **the model never emits diff bytes as output** —
which is most of the cost of a large report, and it makes byte-exactness mechanical instead
of a promise.

It validates first and writes nothing if the narration is wrong, reporting every problem at
once: a hunk with no framing sentence above it in its chapter, or a hunk before any numbered
chapter heading. Chapter numbers come from the headings themselves (`## 3/8 · <name>`), which
is why that form is required in every format.

Hunks are recorded in the ledger beside the out-file, so the completeness check is unchanged
and format-agnostic:

    scripts/tour-set.sh <out-file>.hunk.diff <source> <n> rest

## What each format produces

**`md`** — prose verbatim, hunks in fenced `diff` blocks. No conversion, nothing installed.
Consumable by another agent, diffable, and the format to hand over when the reader did not
ask for anything.

**`ansi`** — prose through `md-to-ansi.py`, hunks through `delta`. Real syntax highlighting
and a heading hierarchy that a terminal markdown renderer cannot express: the report title in
yellow over a heavy rule, a chapter title as a blue `3/9` badge with white capitals over a
white rule, a section heading in bold, and delta's hunk caption over a grey rule. Read it
with `less -R` — no `--mouse`, so text stays selectable. Needs `delta`, `less`, `python3`.

**`html`** — the same, converted again by `ansi-to-html.py`: diff state becomes a row
background, syntax becomes `color` on spans inside it. Inline styles only, so it works from
disk with no external requests. Needs `delta` and `python3`.

Neither styled format ever puts its own output through the model — the HTML for a
hundred-hunk change is about 1.9 MB, eleven times the patch.

## Handing it over

The builder prints one line: the path, or the command to open it. Print it last, with nothing
after it, and above it invite questions — see [Formats](../SKILL.md#formats).
