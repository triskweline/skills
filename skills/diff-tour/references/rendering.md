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

## Quoting code

The narration often needs to show code that is not a hunk: a few lines of an existing
function, or the two lines of a hunk another chapter owns. Use a fenced block, and put the
file in the fence's info string so it renders like the rest of the report rather than
collapsing into the prose:

    ```src/unpoly/classes/params.js:520 · what fromForm does with it
      static fromForm(form, options = {}) {
        form = e.get(form)
    ```

- `<path>` gives the language and lets `delta` syntax-highlight it; `:<line>` gives real line
  numbers; `· <caption>` becomes the caption above it.
- A bare language (```` ```js ````) works when the code has no home in the tree.
- In `ansi` and `html` the block goes through `delta` as a context-only diff, so it gets the
  same highlighting and the same caption bar as a hunk, with no `+`/`-` tinting — which is
  right, since nothing changed there.

A quoted block is **not** a hunk: it consumes no code, is not recorded in the ledger, and
does not count as the framing sentence a hunk needs above it.

## Building

    scripts/tour-report.sh <out-file> <source> <narration-file> [md|ansi|html]

Everything that is not a placeholder is rendered as prose. Every placeholder is replaced by
that hunk, byte-exact from the source, so **the model never emits diff bytes as output** —
which is most of the cost of a large report, and it makes byte-exactness mechanical instead
of a promise.

It validates first and writes nothing if the narration is wrong, reporting every problem at
once: a hunk with no framing sentence above it in its chapter, a hunk before any numbered
chapter heading, or a single-sentence frame that ends with a full stop instead of a colon. Chapter numbers come from the headings themselves (`## 3/8 · <name>`), which
is why that form is required in every format.

Hunks are recorded in the ledger beside the out-file, so the completeness check is unchanged
and format-agnostic:

    scripts/tour-set.sh <out-file>.hunk.diff <source> <n> rest

## What each format produces

**`md`** — prose verbatim, hunks in fenced `diff` blocks. No conversion, nothing installed.
Consumable by another agent, diffable, and the format to hand over when the reader did not
ask for anything.

A small `md` report prints itself into the session, which is the point of the format. Past
about 35 KB it prints its path instead: tool output is truncated around 40 KB, for the reader
as well as for you, so a partial report would be worse than a path. `TOUR_INLINE_MAX` moves
the line. For scale, a hundred-hunk change comes to roughly 230 KB — that one is always a
file.

**`ansi`** — prose through `md-to-ansi.py`, hunks through `delta`. Real syntax highlighting
and a heading hierarchy that a terminal markdown renderer cannot express: the report title in
yellow over a heavy rule, a chapter title as a blue chapter-number badge with white capitals
over a white rule, and a section heading in bold. Read it with `less -R` — no `--mouse`, so
text stays selectable. Needs `delta`, `less`, `python3`.

Each hunk gets a header the builder assembles itself, rather than delta's:

    4.1 · src/unpoly/classes/form_validator.js:218 · validation is not a submission
    ────────────────────────────────────────────────────────────────────────────────
         let dirtyFields = u.flatMap(dirtyOrigins, up.form.fields)
    -    let dirtyNames = u.uniq(u.map(dirtyFields, 'name'))

Code and caption in white, path and line in light grey, the separating dots light grey too —
a dark dot at that size disappears — and the rule under it dark grey. **No line-number
gutter:** the start line is appended to the path instead, where it is read once rather than
repeated down the left edge, which leaves `+`/`-` and delta's tinting to carry the diff.
Header, rule and code are indented four columns, so a hunk reads as a block inset from the
prose.

**Every `delta` call passes `--no-gitconfig --dark`.** Without it the report inherits whoever
built it — `delta.features = line-numbers` in a personal gitconfig puts the gutter back, and
the same report then looks different to the colleague it was sent to. The appearance is the
builder's to decide, not the environment's.

**`html`** — the same, converted again by `ansi-to-html.py`: diff state becomes a row
background, syntax becomes `color` on spans inside it. Inline styles only, so it works from
disk with no external requests. Needs `delta` and `python3`.

Neither styled format ever puts its own output through the model — the HTML for a
hundred-hunk change is about 1.9 MB, eleven times the patch.

## Handing it over

The builder prints one line: the path, or the command to open it. Print it last, with nothing
after it, and above it invite questions — see [Formats](../SKILL.md#formats).
