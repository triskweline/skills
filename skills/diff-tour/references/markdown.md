# The markdown report

The default format: the whole report printed into the session, hunks as fenced `diff`
blocks. No tooling, no conversion, no file. Diffs still come from `scripts/tour-set.sh` and
are pasted from the file it writes, never retyped.

## Headings

Terminal markdown renderers distinguish heading levels poorly — `#`, `##` and `###` often
arrive at the same weight — so **do not rely on the level to convey hierarchy.** Carry it in
the text instead:

- **Report title** — `#`, followed by a `---` rule. The rule is what separates it from what
  follows, since the heading alone may not.
- **Chapter** — `##`, opening with the chapter number: `## 3 · One accessor per field
  question`. The number is the hierarchy signal, and hunk codes depend on it anyway.
- **Section inside a chapter** — `###`, no number. If a renderer flattens it against the
  chapter heading, the absent number still distinguishes them.

Avoid a fourth level. If a chapter needs one, it wants splitting.

## Hunks

A fenced block per hunk, `diff`-tagged, with the code and path on a line above it:

    `3.1` · `src/unpoly/form.js`

    ```diff
    @@ -214,11 +233,72 @@ 3.1 · the four readers and writers
    ```

The `@@` line already carries the code and caption, since `tour-set.sh` puts them there. The
line above it exists because the path is not in the `@@` line for a reader who is scanning.

## What it is good at

It streams, so the reader starts reading as you write rather than waiting for a file. It
survives in scrollback. And another agent can consume it directly — which no other format
manages, since both of the others are styled for eyes.
