# Rendering hunks as HTML

Read this only for `--format html`. The other two formats need none of it.

## Hunks

Delta already solves the hard part — it emits per-token foreground colors (syntax) and
per-line backgrounds (diff state) in one ANSI stream, so translating SGR to inline styles
preserves both. `scripts/ansi-to-html.py` does that translation:

    delta --paging=never --line-numbers --width 160 --hunk-header-style 'bold yellow' \
      --keep-plus-minus-markers --file-style omit \
      < one-hunk.diff | python3 scripts/ansi-to-html.py > one-hunk.html

- **Run it once per hunk.** The converter wraps everything it is given in a single
  `<div class="diff">`, so a whole chapter through it is one undivided block and you cannot
  put prose between hunks. Write a one-hunk patch, convert, repeat.
- `--keep-plus-minus-markers` is required, not optional: delta drops the marker column by
  default, and the `+`/`-` characters must stay visible for a reader who prints or copies.
- `--file-style omit` drops delta's own file banner, which would duplicate your framing line.
- **Never hand-author the token spans.** That is retyping code, and
  [Fidelity](../SKILL.md#fidelity) forbids it.
- The converter emits `<div class="r">` rows of escaped text and sets no layout, so style
  `.diff` with **`white-space: pre`**, a monospace `font-family` and `overflow-x: auto`.
  Without `pre` every indent collapses and it looks broken.

## The exported document

Concatenate the chapters in order — chapter 1, the cluster chapters, Leftovers, the wrap-up
— each as written in its step. No sidebar, no two-column layout, no navigation: the reader
scrolls.

What it does need:

- All CSS inline, no external requests of any kind. It is opened from disk and must work
  offline.
- A background that matches delta's palette. The diff rows carry delta's own inline colors,
  which a media query cannot reach, so don't offer a light/dark toggle the diffs won't honor.
- A comfortable measure for the prose, and the diff styling above.
- One document header for optics — a title and a little breathing room. The content of
  chapter 1 already opens the report; this is chrome, not another section.

Write it to `/tmp/YYYY-MM-DD-difftour-<slug>.html` using today's real date, print the path,
and stop. Don't also re-narrate the tour in the chat.
