# The ansi-export document

One text file, narration and hunks interwoven, styled with ANSI escapes and read in a pager.
It exists because `viewer` mode splits narration and diff across two windows, and
correlating them turns out to be the hard part.

Nothing is converted on the way in: `delta` already emits ANSI, so hunks are inserted
verbatim. Only the narration needs rendering, and `scripts/md-to-ansi.py` does that — the
mirror of `ansi-to-html.py`, which does the same job in the other direction for `export`.

## Building it

Write the narration as markdown, with one placeholder line wherever a hunk belongs:

    %%hunk <path>:<+start>[=<caption>]

Then:

    scripts/tour-ansi.sh /tmp/tour.ansi /tmp/change.patch /tmp/narration.md

Everything that is not a placeholder goes through `md-to-ansi.py`. Every placeholder is
replaced by that hunk, byte-exact from the patch and rendered by `delta`. The script prints
one command as its last line; that command is what you hand the reader.

The chapter number comes from the narration's own headings — a line like `## 3/8 · <name>`
sets it, so codes come out `3.1`, `3.2`. Hunks are recorded in the same ledger
`tour-set.sh` keeps, so the completeness check works exactly as elsewhere: run
`tour-set.sh <out>.hunk.diff <source> <n> rest` when the document is built.

## What it needs

`delta`, `less` and `python3`. No fonts, no browser, no second window.

## Handing it over

The last line the script prints is the whole handover:

    less -R --mouse /tmp/tour.ansi

`-R` passes the escapes through, `--mouse` gives wheel scrolling. Print it on its own line
and stop — a command with commentary after it is a command the reader has to hunt for.
