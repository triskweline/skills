# Rendering hunks

Contents:
- [Trimming context](#trimming-context)
- [Splitting and grouping hunks](#splitting-and-grouping-hunks)
- [Special cases](#special-cases)
- [Explanation quality](#explanation-quality)
- [HTML output](#html-output)

The goal throughout: the reader should be able to trust that a `diff` block shows what is actually in the change, and should never have to skim. Those two goals pull against each other on big hunks, which is what most of this file is about.

## Trimming context

`git diff` gives three lines of context on each side. That's usually right. Trim only when a hunk is long enough that the changed lines get lost in it.

**Rules:**

- Keep every `+` and `-` line. These are never trimmed, ever. A tour that hides changed lines is worse than no tour.
- Keep context that carries meaning: the enclosing `def`/`function`/`class` line, a guard clause the change depends on, the `if` whose branch was modified.
- Replace dropped context with a bare `…` on its own line, indented to match. Never drop lines silently.
- Below ~25 lines, don't trim at all — the trimming costs more attention than it saves.
- With `--full`, never trim.

**Example.** A hunk with 40 lines of untouched setup before a two-line change becomes:

```diff
@@ -88,34 +88,35 @@ class PriceResolver:
     def resolve(self, order, tenant):
         …
-        cached = self.cache.get(f"price:{order.sku}")
+        cached = self.cache.get(f"price:{tenant.id}:{order.sku}")
         if cached is not None:
             return cached
```

The `…` tells the reader lines were skipped; the `@@` header tells them where they are.

## Splitting and grouping hunks

- **One `diff` block per idea.** If a single `git diff` hunk contains two unrelated changes, split it into two blocks with a line of framing each, keeping each block's lines verbatim. Repeating the `@@` header on both is fine.
- **Merge adjacent hunks** from the same file when they're the same idea and close together, using `…` between them.
- **Repetitive hunks** — the identical mechanical change in eight call sites — still all get shown, because the one that is subtly different is exactly the thing a tour exists to catch, and you cannot know which it is without looking. Explain the pattern once against the first block, then let the rest follow with a one-line caption each, or move them to the [Leftovers chapter](../SKILL.md#every-hunk-gets-shown). Never write "and the same change in seven more files" in place of the hunks.
- **Order within a cluster** follows the explanation, not the filesystem. Lead with the hunk that carries the idea, then the ones that follow from it.

## Special cases

**Pure renames** — `git diff` shows these as `rename from` / `rename to` with no body. Report them as a line of prose, not a `diff` block. If the rename came with edits, show only the edits.

**Moved code** — a block deleted in one file and added in another shows up as a large `-` run and a large `+` run, which reads as a rewrite. Run `git diff --color-moved=zebra` (or diff the two regions) to confirm it's a move. If it is, say so and show only the lines that actually changed during the move, or a short excerpt of the moved block with a note about its size. Pasting 200 identical lines twice is the worst possible output.

**Whitespace-only or reformatting churn** — compare against `git diff -w`. Set formatting-only hunks aside, note the line count, and tour the substantive diff.

**New files** — don't paste the whole file. Show its shape (exported names, entry points), then the 10–30 lines that matter most, with `…` for the rest, and say how long the file is.

**Deleted files** — show the signatures or behavior being removed, not the full body. The question the reader needs answered is what capability disappeared and who used it.

**Many sibling definitions added at once** — a hunk that adds a dozen tests, methods,
cases or config entries. The information is in the lines that *name* them, not in the
bodies: keep every naming line — the signature, the declaration, the case label, the
string a test is named by — and trim each body to `…`. Then show one or two bodies in
full where the setup is the interesting part. A reader who sees twenty names knows the
shape of what was added; a reader who sees three full bodies knows three of them.

This is the most common cause of an unreadable chapter, because test files grow in
exactly this shape.

**Binary files, lockfiles, generated code** — one line each, no blocks.

**Very large single hunks** (rewritten file) — split by function or logical section into sub-steps within the cluster, each with its own block and explanation.

## Explanation quality

The explanation after each block is where the value is. Some tests for whether it's pulling its weight:

- Does it say what the code did **before**? A description of the new code alone leaves the reader to reverse-engineer the delta they were just shown.
- Does it explain **why this approach** rather than only what it does? "The tenant id goes in the key rather than in the value because entries expire independently" is worth ten lines of restating the code.
- Would the reader **notice something they'd have missed** skimming the diff? Cross-file consequences, a removed invariant, an implicit assumption, an ordering dependency.
- Does it avoid **narrating the syntax**? "This adds a parameter called `tenant`" is visible in the block and wastes the reader's attention.

When a cluster genuinely has nothing beyond the obvious — a version bump, a typo fix — one sentence is the correct output.

## HTML output

`html` mode carries the whole tour — narration and diffs interwoven — not a companion to a chat tour. In a session that renders HTML, stream the document. In a terminal session, write one self-contained file to `/tmp/YYYY-MM-DD-difftour-<slug>.html` using today's real date, then tell the reader the path and ask them to open it; don't also re-narrate the tour in the chat.

All CSS and JS inline, no external requests of any kind — it's opened from disk and must work offline.

Structure:

- Header with the change title, the what/why paragraph, the new-behavior list, and the scope line.
- A sticky sidebar (or, on narrow screens, a top list) with the chapter list, highlighting the chapter currently in view.
- One section per cluster: heading, purpose sentence, then alternating annotated hunks and explanation prose.
- Hunks in a monospace block with per-line background colors — added lines green-tinted, removed red-tinted, context neutral, `@@` headers dimmed — and the file path as a small label above each block. Keep the `+`/`-` characters visible; don't rely on color alone, since the reader may print or copy it. Delta drops the marker column by default, so `--keep-plus-minus-markers` is required, not optional.
- **For syntax highlighting on top of those backgrounds, reuse delta rather than writing spans yourself.** Delta emits per-token foreground colors and per-line diff backgrounds in one ANSI stream, and `scripts/ansi-to-html.py` translates that to inline-styled HTML: diff state becomes the row's `background`, syntax becomes `color` on `<span>`s inside it. The two never fight, because they are different CSS properties.

      delta --paging=never --line-numbers --width 160 --hunk-header-style 'bold yellow' \
        --keep-plus-minus-markers --file-style omit \
        < one-hunk.diff | python3 scripts/ansi-to-html.py > one-hunk.html

  Run that pipeline **once per hunk**, not once per tour: `ansi-to-html.py` wraps
  everything it is given in a single `<div class="diff">`, so a whole tour through it
  is one undivided blob and the two-column layout below becomes impossible. Write a
  one-hunk patch, convert it, and splice each `<div class="diff">` into its own row of
  the grid. `--file-style omit` drops delta's own file banner, which would otherwise
  duplicate the section heading.

  Inline styles only — no stylesheet, script or font — which is what a strict CSP needs. Never hand-author the token spans: that is retyping code, and the [fidelity rules](../SKILL.md#fidelity-rules) forbid it.

  The converter emits `<div class="r">` rows of escaped text and sets no layout, so **style `.diff` with `white-space: pre`, a monospace `font-family` and `overflow-x: auto`** — without `pre` every indent collapses and the output looks broken.
- Explanations sit **beside** hunks on wide viewports (two-column: diff left, prose right, aligned to the top of the hunk) and **below** them under ~900px. This side-by-side layout is the main thing the HTML gives over the terminal tour.
- A wrap-up section at the end with the recap and open questions.
- Every hunk labelled with its [hunk code](../SKILL.md#hunk-codes) so the prose can refer to it.
- Restrained styling: system font stack for prose, plenty of line height, a max width around 1400px, works in light and dark via `prefers-color-scheme`.

Tell the user the file path when it's written.
