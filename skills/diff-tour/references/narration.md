# The narration file

The narration file is the only thing you write. It is markdown prose with directive lines,
and it contains **no diff bytes**: a directive names a hunk and the builder splices it in,
byte-exact. That is what makes fidelity mechanical instead of a promise, and it is why a
hundred-hunk report costs about as much to write as a ten-hunk one.

A directive is a line starting with `%` in column 0. Everything else is prose. `%%` at the
start of a prose line is a literal `%`.

**An unknown directive is an error, not prose.** A mistyped `%beat` would otherwise merge
two beats silently and nothing would catch it. `%# …` is a comment and renders nothing,
which is what `tour-rest.py` uses so its output can be pasted whole.

## Example

    %report Thread the tenant id through the cache key

    %intro Overview
    %beat What it does
    Cache entries were keyed by resource id alone, so two tenants asking for
    resource `7` shared one entry.

    %chapter Thread the tenant through every key
    The premise of the chapter, in a sentence or two, before any code.
    %blast moderate
    Reaches the four call sites in `billing/` that the caller index found; this
    diff changes two of them.

    %beat Why the key is built in one place now
    The old code assembled the key at each call site, which is how the tenant
    came to be missing from one of them. [[h1]] moves that into `cacheKey()`.
    %hunk src/cache.js:88 @h1 = the key builder, and its one caller
      The `??` is doing precise work: an explicit `null` tenant is a real value
      and has to survive.
    %hunk src/cache.js:140 #12-26 @h2 = the read path, same shape
    %quote src/cache.js:41-48 = what the old key looked like
    %code sh = how to check for stragglers
    grep -rn 'cacheKey(' src/
    %end

    %leftovers Leftovers
    %beat Dependency bumps
    Nothing in the change would lose these if it were reverted.
    %hunk package-lock.json:all = a lockfile refresh, 812 lines
    %file assets/logo@2x.png @h3 = the retina asset, replaced

    %closing Wrap-up
    %beat What you still need to check yourself
    - [[h2]] — I could not find what reads the value it writes.
    - I did not run the tests.

## Directives

| Directive | What it does |
|---|---|
| `%report <title>` | the report's title. Required, once, before the first chapter. |
| `%intro <title>` | the overview chapter. Exactly one, first. |
| `%chapter <title>` | a cluster chapter. One per cluster. |
| `%leftovers <title>` | the leftovers chapter. At most one, immediately before `%closing`. |
| `%closing <title>` | the wrap-up chapter. Exactly one, last. |
| `%blast narrow\|moderate\|wide` | the blast-radius judgement. Required in a `%chapter`, not allowed in the other three. Prose under it is its evidence. |
| `%beat <subtitle>` | a beat: one idea, its prose, and its blocks. |
| `%hunk <spec> [@<label>] = <caption>` | one diff block. |
| `%file <path> [@<label>] = <caption>` | a change with no diff body: binary, pure rename, mode change. |
| `%quote <path>:<from>-<to> = <caption>` | those lines of that file, read from the checkout. |
| `%code [<lang>] = <caption>` … `%end` | a literal snippet with no home in the tree — a command to run, a sketch of an alternative. The only code in the report that is not read from the diff or the checkout, and it is labelled as such. |
| `%# <anything>` | a comment. Renders nothing. |

### `%hunk` specs

    %hunk src/cache.js:88 = <caption>              the whole hunk starting at +88
    %hunk src/cache.js:88 #12-26 = <caption>       body lines 12..26 of it
    %hunk src/cache.js:all = <caption>             every hunk of the file, one block each

`+start` and the body-line offsets both come from `bin/tour-hunks.py --body`, which
prints the patch with an offset in the left margin of every hunk. Read the patch through it
in Step D and the numbers arrive with the content.

Body offsets count **every** line of the hunk body, context included, from 1.

The caption starts after the first `=`, so a caption may contain `=` freely. Captions are
required, and inline code renders in them.

### Labels and references

`bin/tour-skeleton.py` writes an `@hN` **label** into every `%hunk` and `%file`. A label
names one block forever and travels with it in the directive, so reordering a chapter cannot
invalidate a reference. A **code** — `2.9` — is only where a block currently sits, computed
from position at build time.

    %hunk src/cache.js:88 @h4 = the key builder
    ...
    The `??` in [[h4]] is doing precise work.
    The guard is in [[h4]], and [so is its one caller](#h4).

`[[h4]]` renders as a link showing whatever code `h4` resolves to; `[label](#h4)` is the
same link with your own prose as its text. `[[ch5]]` and `[label](#ch5)` point at a chapter.

**The order matters and only goes one way:** structure and captions → `tour-skeleton.py`
mints the labels and prints them → prose that references them. A skeleton written with
references in it cannot know the right names, so `tour-skeleton.py` defers them, and so does
`tour-rest.py`, whose answer prose has no bearing on. **The build is what refuses a reference
that still does not resolve** — by then the labels exist, so a dangling one is a typo.

**Never write a code.** A link to `#2.9` is refused, because it breaks the moment anything
is reordered. Only `path:all` cannot be labelled — one directive standing for many blocks
cannot have one name.

### Prose placement

- Under `%chapter`: the chapter's introductory paragraph.
- Under `%blast`: the evidence for that level.
- **Unindented under `%beat`**: the beat's narration. Renders in the left column, beside
  the code, and stays there as the reader scrolls.
- **Indented under a block**: that block's own prose — the paragraph version of its
  caption. Renders above that block's diff, in the code column. It is part of the block,
  so moving the block moves it.

        %hunk src/cache.js:88 @h4 = the key builder
          The `??` is doing precise work: an explicit `null` tenant is a real
          value and has to survive.

  Once a beat has a block, unindented prose has nowhere to belong, and the builder says so
  rather than guessing which block you meant.
- Markdown subset: paragraphs, `-` and `1.` lists, `**bold**`, `*italic*`, `` `code` ``,
  `[text](url)`, and `[[<label>]]`. Headings are not allowed in prose — a chapter is
  `%chapter` and a beat is `%beat`, so the report keeps one hierarchy.

Every command, flag and exit code is in **[commands.md](commands.md)**; this page is the
format they consume. The order the commands run in, and why, is
[SKILL.md](../SKILL.md)'s procedure.

## What the page does

- A header naming the repository folder and its branch, the diff's shape, and one fixed
  paragraph saying what the document is. The builder writes all of it — you write only the
  `%report` title.

- Chapters in a fixed sidebar, with a per-chapter viewed count and the current chapter
  marked.
- A viewed mark per block: it collapses the block and gives it a green edge, the way a
  reviewed file behaves on a pull request. Kept in `localStorage` under a key derived from
  the output path, so it survives a rebuild of the same file. Clicking a caption collapses
  without marking. **Nothing starts collapsed** — the reader decides what to put away.
- Light and dark, following the system and overridable.
- Diffs highlighted twice: the file's own language on the text, green and red on the added
  and removed runs.

Everything is inlined — CSS, JavaScript, and the vendored Prism — so the file works from
disk with no network and no server. Expect roughly three times the patch's size, plus 110 KB.

## Tests

    python3 tests/test_difftour.py

The suite covers everything between the narration file and the HTML — the diff parser, this
format and each of its refusals, the coverage arithmetic, the prose subset, the commands, and
the rendered markup. Run it after changing anything in `lib/difftour/` or `bin/`.

## Changing the design

`assets/layout.html` is the page shell **and** a standalone design fixture: it links
`assets/report.css` and `assets/report.js` by relative path and carries one of every
component with sample content. Open it in a browser, edit the CSS, reload. The builder
assembles a report from that same file, so what the fixture shows is what a report looks
like. Its opening comment documents the component set.
