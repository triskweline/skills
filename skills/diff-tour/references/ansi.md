# The ansi document

One text file, narration and hunks interwoven, styled with ANSI escapes and read in a pager.
It exists so a terminal reader gets syntax highlighting and a clear heading hierarchy
without leaving the terminal, and without the markdown renderer flattening the levels.

Nothing is converted on the way in: `delta` already emits ANSI, so hunks are inserted
verbatim. Only the narration needs rendering, and `scripts/md-to-ansi.py` does that — the
mirror of `ansi-to-html.py`, which does the same job in the other direction for `html`.

## Building it

Write the narration as markdown, with one placeholder line wherever a hunk belongs:

    %%hunk <path>:<+start>[=<caption>]

Then:

    scripts/tour-ansi.sh /tmp/tour.ansi /tmp/change.patch /tmp/narration.md

Everything that is not a placeholder goes through `md-to-ansi.py`. Every placeholder is
replaced by that hunk, byte-exact from the patch and rendered by `delta`. The script prints
one command as its last line; that command is what you hand the reader.

The builder refuses a document where a hunk has no narration above it — a heading does not
count as framing. Fix it by adding the sentence, not by moving the placeholder.

Two things to get right in the narration itself, both covered in
[Captions carry the story on their own](../SKILL.md#captions-carry-the-story-on-their-own):
the chapter heading is already on screen, so a caption should describe its own hunk rather
than restate the chapter; and prose between two hunks is read as commentary on the one
above, so name a hunk by its code when you mean to introduce it.

The chapter number comes from the narration's own headings — a line like `## 3/8 · <name>`
sets it, so codes come out `3.1`, `3.2`. Hunks are recorded in the same ledger
`tour-set.sh` keeps, so the completeness check works exactly as elsewhere: run
`tour-set.sh <out>.hunk.diff <source> <n> rest` when the document is built.

## What it needs

`delta`, `less` and `python3`. No fonts, no browser, no second window.

## Handing it over

The last line the script prints is the command to hand over:

    less -R /tmp/tour.ansi

`-R` passes the escapes through. Deliberately no `--mouse`: it captures drag events, which
stops the terminal selecting text to copy, and most terminals translate the wheel to arrow
keys anyway.

Before that line, tell the reader the conversation is still open — they can ask about
anything as they read, and quote a hunk code like `3.2` to point at one. Then print the
command last, with nothing after it.
