---
name: diff-tour
description: Helps a human review a code change they did not write. Produces one HTML report where the real diff hunks sit beside narration explaining what each change is for, what the code did before it, and where to look closely — and clusters a sprawling diff into a handful of themed chapters, so a reviewer can approve or reject it with understanding rather than by skimming. Use this when someone wants to be walked through, toured, guided through or led through a diff, PR, branch, or commit: "walk me through these changes", "explain this PR hunk by hunk", "review this change with me", "tour this branch", "help me understand what this branch does", "show me the diff with explanations" — and whenever someone asking to "explain a diff" wants to see the code itself rather than a prose summary. It earns its cost on changes too large to hold in your head; a one-line fix needs no tour. This is the reading half of a review, not an automated bug hunt: it explains the change and points at risk, but never rules on it, so pair it with a correctness pass such as /code-review.
metadata:
  version: 2.0.0
---

# Diff Tour

**The diff tour helps a human do a manual code review of a diff they did not write.**
Everything else follows from that sentence.

- **The reader is a reviewer, not a student.** Narration serves review decisions — is this
  correct, does it break callers, is this the right design, do I need to look closer — not
  general edification.
- **They did not write it, so they lack what the author had**: the vocabulary, the reason,
  the shape of the code before. Supplying that is most of the job.
- **The reader supplies the judgement.** You show them the change and what you know about
  it. You never rule on it for them, and you never test whether they were paying
  attention.
- **You are not the review.** An automated bug hunt (`/code-review` in Claude Code) is a
  different tool and a good companion. The tour is the reading half, done well.

Two mechanics make it work, and both are easy to get wrong:

1. **Real hunks, verbatim.** Every chapter shows actual diff lines, spliced in by the
   builder, never retyped. Paraphrased code destroys the whole value of the tour.
2. **Narration and hunks side by side.** A hunk sits next to the prose about it, always. A
   report that puts all the explanation in one place and all the code in another makes the
   reader do the correlating, which is the work the tour exists to do for them.

## The report

One self-contained HTML file. You write a **narration file** — prose plus directives naming
hunks — and `bin/tour-build.py` renders it. **You never emit diff bytes.** That is what
keeps hunks byte-exact without trusting a copy-paste, and it is most of the cost of a large
report: typing out a hundred-hunk diff is tens of thousands of output tokens spent on bytes
you are not thinking about.

The report has four kinds of chapter, in this order:

| Chapter | Directive | How many |
|---|---|---|
| the overview | `%intro` | exactly one, first |
| a topic cluster | `%chapter` | one per cluster |
| the leftovers | `%leftovers` | at most one, second to last |
| the wrap-up | `%closing` | exactly one, last |

A **cluster chapter** is a title, an introductory paragraph, a blast-radius judgement, and
then its **beats**. A **beat** is one idea: a subtitle, the prose explaining it, and the
hunks it is about. The page puts a beat's prose in the left column and its hunks in the
right, and the prose stays beside the code as the reader scrolls a long diff.

Two numbering schemes, deliberately different so they can never be confused:

- **Steps A–J are lettered.** They are this skill's procedure. The reader never sees them.
- **Chapters and blocks are numbered by the builder.** A block's code is
  `<chapter>.<block>` — `3.2` is the second coded block of chapter 3, numbered in the
  order they appear. That number is what the reader sees and quotes back to you.

**You never write a code.** Codes come from position, so nothing you write can disagree
with where a block actually sits. What you write instead is a **label**: `@h17`, minted by
`bin/tour-skeleton.py` and carried in the directive. Prose points at a label —
`[[h17]]` — and the builder renders whatever code that block currently sits at.

That split is what makes a chapter safe to reorder while it is being narrated. A label
names one block forever and moves with it; a code is only ever a position. Reference a block in prose the way you would a figure — "the `??` in `[[h17]]` is doing
precise work" — and let the builder print the number. What you write is always the label.

## Rulesets

The procedure below is thin on purpose; the substance is here.

## Fidelity

What must be true of every hunk you show. These are mechanics, not judgement — variation
here is breakage.

- **Never retype code.** Every block comes from the builder, byte-exact from the diff or —
  for `%quote` — read from the checkout. If a line is too long, let it wrap or scroll;
  don't shorten it.
- **Never fabricate a hunk** to illustrate a point. If the diff doesn't contain it, it
  doesn't get shown.
- **Never hide an added or changed line.** Not for a new file, not for forty peer
  definitions, not because a chapter is long — see [Nothing is hidden](#nothing-is-hidden).
- **Ranges are derived, never written.** You name a hunk by its `+start`; the builder
  computes the file, the line it begins at, how many lines it adds and removes, and — for a
  fragment — which slice of the hunk it is and where the rest lives. There is no `@@` header
  in the report because there is nothing for a reader to parse: the caption says it.
- **Separate stated from inferred intent.** "The PR says…" versus "This looks like…".
- **Suspicions are suspicions.** Say "worth checking whether…", never "this is a bug",
  unless you read the surrounding code and can explain it concretely.
- **Never certify.** You read the diff; you did not verify it. Don't offer a verdict on the
  change as a whole.

**The completeness guarantee** is `bin/tour-rest.py`, and [Step F](#step-f-the-skeleton)
settles it before any prose exists.

### Nothing is hidden

**Every added or changed line appears somewhere in the tour. No exceptions.** Not for a
new file, not for a hunk that adds forty peer definitions, not for a rewritten file, not
because a chapter is getting long. A reader cannot be responsible for code they were never
shown.

**Never show one hunk as a representative of several.** That hides precisely the case the
tour exists to catch: the seventh call site that differs.

Length is managed by structure, never by hiding: chapters divide the report, the sidebar
lets the reader skip, a dull chapter is cheap to scroll past, and `%fold` starts a block
collapsed with its size still on screen. What you may compress is the *narration* — one
caption for twenty similar hunks is fine, because the reader can see the twenty hunks it
describes. A topic's own hunks stay in that topic's chapter however dull they are, and
substantial work gets a chapter however unrelated it is — see
[Step H](#step-h-narrate-the-leftovers) for the two narrow kinds of thing Leftovers is
for.

A reader who scrolls past a chapter has decided. Don't remark on it.

Context lines need no management either. `git diff` splits a hunk whenever the gap between
changes exceeds twice the context setting, so the longest run of unchanged lines any hunk
can hold is 6 — `tour-fetch.sh` pins `diff.context=3` along with the prefix settings, so
that holds whatever the reader's gitconfig says. There is nothing to trim.

**Coverage is line-granular and mechanical.** `tour-rest.py` compares the narration against
the patch and reports every changed line no component shows, plus every change a diff can
carry without a body: a binary file, a pure rename, a mode change. It reads the two files
and nothing else, so it cannot go stale and is safe to run as often as you like.

### Splitting hunks, and fragments

A `git diff` hunk is an accident of proximity: it merges every change within a few context
lines. So one hunk routinely carries two unrelated ideas, and **a hunk is not the unit of
anything except extraction.**

**You may cut a hunk into fragments and send each fragment to the cluster it belongs to.**
Select body lines with `#<lo>-<hi>`, counting every line of the hunk body including
context, from the numbering that `bin/tour-hunks.py --body` prints in the left margin.
Each fragment is its own block with its own code and caption, and the builder says in the
caption which slice it is, how much of the hunk sits above and below, and where the other
fragments are — so a fragment can never be mistaken for a whole hunk.

- **Never split between a `-` run and the `+` run that replaces it.** A chapter that sees
  the deletion without its replacement reads as a removal, which is a different change.
- **A fragment must contain a changed line.** A slice of pure context is `%quote`, not
  `%hunk`, and the builder refuses it.
- **Splitting replaces re-showing.** The old problem — one hunk that several topics need —
  is now solved by sending each topic the lines it is about. Where two topics genuinely turn
  on the *same* lines, show the overlapping fragment in both; the builder warns, because
  only you can tell a deliberate overlap from an off-by-one.
- **Don't split what is one idea.** Fragmenting a coherent hunk to make chapters look
  tidier costs the reader the context that made it legible.

Other shaping:

- **Merge nothing.** Two adjacent hunks that are one idea are two blocks in one beat, with
  one caption each. There is no reason left to glue them together.
- **Repetitive hunks** — the identical mechanical change in eight call sites — all get
  shown, in the same chapter as the one you explained, never deferred to Leftovers. Explain
  the pattern once in the beat's prose, give each block a one-line caption, and `%fold` the
  beat so the reader can open the ones they want.
- **Order follows the explanation, not the filesystem.** Blocks appear and are numbered in
  the order you write them, so narration order, screen order and codes are the same thing.
  Only `:all` falls back to file order, since it states none.

### Special cases

**Pure renames** — `git diff` shows these with no body. Select them with `%file`, which
renders one line naming the file and where it came from. They count towards coverage, so a
rename described only in prose is still reported as unshown.

**Mode changes** with no content change: also `%file`.

**Moved code** — a block deleted in one file and added in another shows up as a large `-`
run and a large `+` run, which reads as a rewrite. Run `git diff --color-moved=zebra` (or
diff the two regions) to confirm it's a move. If it is, say so in the narration and lead
with whatever genuinely changed during the move. The added side still gets shown in full —
it is code the reader has not reviewed — but one sentence saying "identical to the block
removed above, except the two lines called out" saves them from reading it twice.

**Whitespace-only or reformatting churn** — compare against `git diff -w`. Set
formatting-only hunks aside as one folded leftover group, note the line count, and tour the
substantive diff.

**New files** — show the whole file. It is all new code, and none of it has been reviewed
before. Say how long it is, and lead the narration with its shape — exported names, entry
points — so the reader knows what they are scrolling through. `%hunk <path>:all` takes the
whole thing in one directive.

**Deleted files** — show the whole file, in a `%fold`ed beat. Every line of a deleted file
is a changed line, so showing only the signatures would leave the body uncovered and the
completeness check would be right to complain. Folded means the reader is not marched
through a corpse while the guarantee stays absolute. The narration still answers the only
question that matters: what capability disappeared, and who used it.

**Binary files** — never show a diff. `%file` renders one line naming the file and what
happened to it, deriving the kind from the diff so it cannot be stated wrongly. A binary
needs no explanation of its own, so one beat can hold a list of them.

**Lockfiles and generated code** — one `%hunk <path>:all` each in a folded leftover group.

**Very large single hunks** (a rewritten file) — fragment it by function or logical
section, each fragment its own block with its own caption, in as many beats as the ideas
need. Every line still appears.

## Clustering

### What a good cluster looks like

A cluster is a **unit of intent**, not a file. Changes from four files belong in one cluster if
they exist for the same reason; two changes in one file belong in different clusters if they
don't — and because you can fragment a hunk, "in one file" no longer even means "in one
block".

**Its name describes a change**: "thread the tenant id into the cache key", "make the retry
budget configurable", "backfill script for existing rows". Not a location: "changes to
cache.py", "misc".

**Its length follows its cohesion.** Never split a cluster to make it shorter. If a change
can only be explained through twelve interconnected hunks, that is one chapter of twelve
hunks — two chapters of six that each depend on the other are strictly worse, because
neither can be understood where it sits. When a cluster is genuinely long, say at the top
how much it holds and lead with the beats carrying the idea.

**Many changes share a cluster.** A cluster of one hunk is possible but usually means the
clustering is too fine.

**It is understandable from its predecessors alone.** The reader should never need a later
chapter to follow an earlier one. If chapter 4 only makes sense after chapter 6, reorder.

A hub-and-spoke change cannot fully satisfy this, and shouldn't try: when one decision
causes four others, the hub belongs first even though its code touches names the spokes
later define. Name the forward reference and link it — "`assertFieldsInSameLayer` is
[[ch6]]'s subject" — so the reader knows the explanation is coming rather than missing. What
the rule forbids is an *unsignposted* dependency, not an acknowledged one.

**It is as separate as the diff permits, and no more.** You are reverse-engineering a
history from a net result, not writing one: you see only the final state of every line.
Where a location was rewritten in several rounds, the surviving hunk carries all of them at
once and no fragmenting can separate them. Perfect separation is not available, and claiming
it is a fabrication.

**What a cluster is never:** backend versus frontend. Tests versus code. By file type. By
directory. Every one of those cuts across intent and produces chapters that can only be
understood by reading a different chapter. **Tests belong with the behavior they pin down** —
a spec asserting a new selector goes in the selector cluster. A layer split (schema → API →
UI) is a last resort for a change that genuinely is one traversal of the stack, never a
default.

### How to find them

Assume the diff is ugly. The commits may be checkpoints, merges and afterthoughts; the file
order is alphabetical; the same lines may have been overwritten three times. **Cluster the
whole diff as if you were writing the best possible commit history for it** — and derive
that history from the diff's content, not from the commits that happen to be in it.

Three passes. Do not skip to assignment: grouping hunks by resemblance is what produces the
location-based clusters above, because resemblance correlates with location.

**Pass 1 — extract topics, ignoring hunks.** Read the diff as a whole and name the ideas it
contains: the behavior changes, the refactorings, the cleanups. Write them down as ideas,
before deciding where any single change goes.

One useful test: **does this change observable behavior?** Behavior-preserving work and
behavior-changing work are different topics even when they touch the same lines — it is what
separates "the refactoring that made room" from "the change it made room for". Unlike "is
this preparatory?", you can answer it from the diff. It will not always separate much — on a
branch where nearly everything is a behavior change, what actually draws the boundaries is
which functions and call sites a change owns.

Commit messages, PR descriptions and changelog entries are **hypotheses to test against the
hunks, never the topic list itself**. Deriving topics from commit subjects smuggles back in
the boundaries you were told not to trust.

Expect a range to hold several bodies of work, each with its own rounds of preparation,
refactoring and cleanup. Within one body, `preparation → behavior change → cleanup` is a
good ordering and a good hint at where a boundary falls. Across bodies it means nothing —
don't force one arc onto a range that has three.

**Pass 2 — assign every change to the topic it exists for.** The test is counterfactual:
**if this topic were reverted, would this line disappear from the diff?** Not "would my
explanation mention it" — a topic's prose can be complete while a dozen hunks still exist
only because of it, and judging by the prose sends all twelve to Leftovers.

- **A topic's chapter carries every change that belongs to it**, including the repetitive
  and inconsequential ones. Never move a topic's own follow-ups to Leftovers: by the time
  the reader reaches the end they have lost the context that made those hunks legible, and a
  hunk shown without its topic is worse than useless. Narrate the first one properly, then
  say the rest follow the same shape.
- **Tests and documentation go with the behavior they pin down or describe.** Six specs for
  one new behavior all belong to that topic, even though the explanation would read fine
  having quoted only one of them.
- **When one hunk serves two topics, fragment it** and give each topic its lines. That is
  the normal case, not the exception — see [Splitting hunks](#splitting-hunks-and-fragments).
  Only when both topics turn on the very same lines does one of them own it and the other
  show the overlap.
- **A hunk that summarises the whole change** — a changelog entry, release notes — is
  claimed by every topic, because reverting any of them would shrink it. It belongs to the
  topic that *documents* the change if the diff has one, and is otherwise its own small
  cluster. Place it early either way and read it as stated intent: it is usually the best
  account of the author's own understanding in the whole diff.
- A change that no topic claims is **evidence of a topic you have not named yet** — check
  that before anything else. Adding a topic is cheap; filing real work as fallout is not,
  and it is the most common way a tour fails a reader.
- **Being unrelated to the change you came for does not make something a leftover.** A
  range often holds a second substantial body of work — a documentation overhaul, a test
  runner rewritten, a subsystem migrated. That is a topic. It gets a chapter, or several,
  named for what it is. Relegating it to a caption in Leftovers tells the reader that a
  thousand reviewed-by-nobody lines were beneath mention, which is not true and not yours
  to decide.
- Only then, what is genuinely left over: see [Step H](#step-h-narrate-the-leftovers).

**Pass 3 — settle.** Merge two topics whose changes turn out to depend on each other in both
directions; mutual dependency means one cluster, while a one-directional dependency is only
an ordering constraint. Split a topic whose changes serve two ideas. Pull a new abstraction
and its first consumer together unless the abstraction stands alone.

Then count. **3–7 clusters** is the healthy range *per body of work*, and a smell check
rather than a budget to hit.

**A range holding three bodies of work legitimately has more chapters than one holding a
single body.** Don't compress the extra bodies to hit a number. Group each body's chapters
together, in the order the overview announces them, so a reader can read one body and stop.

If the count is far outside the range for a single body, re-run pass 1. Too many usually
means one topic was found repeatedly under different names; too few usually means the change
is smaller than its line count suggests. The defect is in the topic list, not in the
boundaries — never redraw a boundary by hand to hit a number.

A range full of leftovers means the same thing: too few topics, or a second body of work you
have not named.

## Narration

The prose beside a hunk is the only thing the reader cannot get from the diff itself. That
is the whole test for whether a sentence belongs: **could they have read it off the hunk?**
If yes, cut it. A paragraph that restates the diff does more than waste words — it teaches
the reader that your prose is skippable, and they will skip the one that mattered. **A
hunk's own added comments are part of the hunk**, so the test applies to them too: a
well-commented change may deserve less prose than a bare surprising one.

So a mechanical walk ("here we call `foo` with the new argument") is never the job. What
the diff cannot supply is: what the code *meant* before, why this route and not another,
what breaks elsewhere, what invariant appeared or vanished, and what the hunk is *for*.

**Quote code when a sentence needs it**, whether it is in the diff or not — a few lines of
the function a hunk sits in, or two lines of a hunk another chapter owns. `%quote` reads them
from the checkout so they are exact; never paste code into a paragraph.

**`%code` is for the code that has no home** — a command the reader can run, three lines
sketching the alternative you just named. It is the one thing in the report you type
yourself, so nothing can check it, and the report labels it *"written for this report, not
taken from the change"* to keep it from being read as something it isn't. Use it where it
earns that label, and reach for `%quote` whenever the code exists somewhere.

**A quote needs a checkout of the diff's own head.** It reads the file on disk, so touring
someone else's pull request from a working tree that is not at that PR's head quotes the
wrong version of the file — fluently, and byte-exactly. `tour-build.py` compares the two and
says so, and `--root` points it at the right checkout. If there is no such checkout, don't
quote: cite the block by its label instead.

**Say what the code did before.** Describing only the new code leaves the reader to
reverse-engineer the delta they were just shown, which is the expensive half of reviewing
and the half you can do for them.

**Aim at what a skim would miss**, and let the obvious pass. The reliable candidates: a
cross-file consequence, an invariant that disappeared, an assumption the code now makes
implicitly, an ordering dependency — and any hunk that deviates from the idiom around it,
does something its name does not suggest, defends against something invisible in the diff,
or takes a deliberate route past an easier one.

**Be proportional.** Length is signal. A hunk that surprises you deserves several
sentences; an obvious one deserves a clause; a repeat of the hunk above deserves five
words. Uniform paragraphs under every hunk flatten the signal and exhaust the reader — the
variation is how they know where to slow down. This is the single most common way narration
fails.

**Say what a hunk is for** when its purpose is not self-evident: it enables this cluster,
it enables a later one, it pays down something in the way, it buys performance. Do not
label every hunk with a category — that is boilerplate. If you cannot say what a hunk is
for at all, that is a finding, not a gap in your prose.

**Say what a hunk does *not* do** where a reader would assume more: a guard that covers one
branch, a migration that converts one call site, an accessor adopted in three places but
not the fourth. This is visible in the diff and reliably missed.

**Restore contingency.** A diff reads as inevitable — every line looks like the only line
that could have been there, and that is what invites a rubber stamp. Naming one alternative
breaks the spell: *the author chose X; Y was also available, and would have traded A for B.*
No comparative adjective, no recommendation, no verdict — the reader judges.

The alternative is by definition fictional; it is the thing that was *not* done. What must
not be fictional is **what it would be made of.** So the bar is that you can point at the
material:

- **the code this diff removed** — the strongest case, and the one the diff hands you for
  free: a road that demonstrably worked, sitting right there in red;
- **a pattern this codebase already uses somewhere else** — the pattern is real, applying it
  here is the hypothetical part;
- **a platform or library feature that exists** — hand-rolling instead of using it was a
  real fork in the road;
- **a route a comment or a commit names.**

Then say what choosing it would have cost.

That distinction is the whole guard, because pricing is not one: an alternative assembled
from nothing prices just as convincingly as one assembled from something you read. "This
could be one selector instead of four, at the cost of also matching disabled controls" earns
its place because `:enabled` is already in that list. "A cleaner approach may exist" is the
shape of a thought without the content, and is worse than silence.

**Most hunks have no alternative worth naming, and a chapter with none is normal.** A
forced contingency is boilerplate, and boilerplate is what kills this rule first.

**Admit what you do not understand, in the beat, where the hunk is.** This is the most
important rule here. A fluent, plausible, wrong explanation is worse than no tour, because
it manufactures the feeling of having reviewed. A reader can defend themselves against "I
do not know what this does"; they cannot defend themselves against confident invention.
Three cases, and they read very differently:

- **You cannot explain it.** Say what you do know and what exactly is opaque — "this adds a
  `?? false` default on the submitter; I could not find what reads it". Bounded and
  specific. "Unclear" is an abdication.
- **You understand it and it looks wrong.** Say so, with the reason. Do not soften it into
  a hedge — this is the "unless" in [Fidelity](#fidelity)'s suspicion rule: you read the
  surrounding code and can explain it concretely.
- **It looks broken or unfinished as written** — a hunk that cannot be reconciled with the
  code around it. Say that plainly. **Never narrate a broken diff into coherence**; making
  it sound sensible is the worst outcome this skill can produce.

Distinguish **"I looked and could not find"** from **"I did not look"** — Step D scales
effort to the size of the diff, so both are honest, but they send the reader to different
work. And if admissions pile up, the problem is upstream: go back to Step D rather than
narrating on through hedged mush.

Carry these forward to the wrap-up chapter, which is the only place they are collected.
Give each one its block's label, so the reader can go back to it.

**Gloss a term once, at first use, in a clause.** Where a project's own concept is
unavoidable, define it in passing and move on. If the tour needs a glossary, the narration
is failing.

### Beats

**A beat is one idea, and its prose has to cover every block in it.** That is what replaces
the old rule that each hunk needed a framing sentence directly above it: prose and code are
side by side now, so framing is structural — but only if the beat is honestly one idea. One
paragraph followed by six unrelated blocks technically passes the builder's check and fails
the reader.

- **In a multi-block beat, refer to blocks by label** — `[[h17]]`, which renders as that
  block's code. With three diffs beside one paragraph, the code is the only thing that pairs
  a sentence with the diff it is about.
- **A block may carry its own prose.** Indent a paragraph under a `%hunk` and it
  belongs to that block — it is the paragraph version of the caption, and it renders
  above that block's diff. Use it for the thing that is about *this* diff and no other:
  "the reordering here is a real fix and easy to miss". Because it lives inside the
  block, it moves when the block moves, and it can never end up describing the wrong
  diff.
- **The beat's own prose is the unindented paragraph under `%beat`.** That is the left
  column: what the beat is about, the argument that runs across its blocks. Once a beat
  has a block, unindented prose has nowhere to belong and the builder says so.
- **Don't make a beat per hunk.** A subtitle over one obvious hunk is boilerplate; that
  hunk is a caption and, if it needs a word, an annotation under it.
- **Structure a long chapter with beats, not with paragraph breaks.** Past three or four
  blocks, a reader needs somewhere to stand. Each beat's subtitle names the sub-idea its
  blocks share — "why absence and not falseness", "the one call site that opts out" — and a
  reader skimming gets a second layer of outline for free. Use bold text for emphasis inside
  a paragraph, never as a substitute for a subtitle: bold does not structure anything.

### Captions

Every block has a caption. It sits at the top of the block next to the file path, and it is
the one line a reader scanning the report will always read — so **the caption carries the
framing**: it says what *this* block is for, here, in this beat. Not a label for it.

`3.1 · the four readers and writers`, not `3.1 · one accessor per field question` — the
chapter heading is right above and restating it wastes the line. A caption that could sit
under any block in any order is doing nothing.

Inline code renders in a caption, and often should: `` `form.elements`, and nothing else ``.

Captions carry extra weight now that a chapter can be narrated on its own: the skeleton's
captions are all another chapter knows about this one.

**A caption states what you read, never what you assume.** It is the most trusted line in
the report and the least defended: prose can hedge, a caption cannot. So a caption over a
hunk you have not read may name its kind or its provenance — "a lockfile refresh, 812
lines", "part of the guide overhaul" — and may not state its content. The moment you write
what a hunk *says*, you have read it.

### Blast radius

Every cluster chapter states one, above its beats: `%blast narrow`, `moderate`, or `wide`.

- **narrow** — effects confined to files this diff already changes.
- **moderate** — reaches other modules, through call sites the Step D index found. Name them.
- **wide** — public API, or behavior observable outside the codebase. **A new error or
  refusal on a path that previously succeeded is always wide**, however few lines it took
  and however local its call sites: the people it reaches are users of the library, not
  callers of the function.

The levels are the cheap half of this. The evidence under them is the product, so if the
level is arguable, write the evidence and pick the higher one.

It is **inferred scope, not a verdict** — which is what keeps it clear of "never certify".
It is also the one place the caller index pays off visibly, so a `moderate` or `wide`
judgement names its evidence: which callers, in which files, and how many this diff does not
touch. A level with no evidence beside it is the same boilerplate as a forced contingency,
and it will be read as one.

## The narration file

The format is in **[references/narration.md](references/narration.md)** — read it before
Step F. It is short, and you will not guess the directive set. The commands that consume it
are in **[references/commands.md](references/commands.md)**.

## Where things are

`bin/` holds the commands this procedure runs, and `lib/difftour/` holds what they
import. Nothing in `lib/` is ever run directly.

**Every flag, every exit code, and exactly what each command prints and changes is in
[references/commands.md](references/commands.md)** — read it rather than guessing, and rather
than discovering a flag by having a call fail. Two conventions hold throughout: `<patch>
<narration>` come first in that order everywhere, and **stdout is the answer while stderr is
the commentary**, so `2>/dev/null` gives you the answer alone.

| Command | Turns | Into |
|---|---|---|
| `bin/tour-fetch.sh` | any target | a patch file |
| `bin/tour-hunks.py` | a patch file | the hunk list, or the patch with body offsets |
| `bin/tour-skeleton.py` | a narration file | labels in it, and the table of what it holds |
| `bin/tour-build.py` | a narration file | the HTML report |
| `bin/tour-rest.py` | a narration file | what it does not show yet |

`assets/` is the page shell, its CSS and its JavaScript; `vendor/prism/` is the
highlighter; `tests/` covers everything between the narration file and the HTML.

## Procedure

**A chapter's contents are specified in exactly one place: its step.** Anything else that
mentions a chapter refers to it by name and never restates what is in it. Three copies of
the wrap-up's contents once drifted into three different answers; this is the rule that
prevents the next one.

## Step A: Help

If the arguments are exactly `help`, `--help`, `-h`, or `?`, print this block verbatim and
stop — don't gather a diff.

```
diff-tour — a guided, cluster-by-cluster walkthrough of a code change

Usage: /diff-tour [target]

Target (optional, defaults to your working diff):
  <empty>       Branch diff vs its branch point, plus uncommitted changes
  <git range>   e.g. main..HEAD, abc123..def456
  <commit>      e.g. HEAD~1, or a commit SHA
  <branch>      compared against the repo's default branch
  <number>      a PR or MR in this repo
  <PR/MR URL>   a GitHub pull request or GitLab merge request
  <patch file>  a .patch or .diff you already have

The report is one self-contained HTML file: syntax-highlighted diffs beside the
narration that explains them, a chapter sidebar, and a viewed mark per hunk.
Needs git and python3 (3.10+). Nothing to install.
```

## Step B: Say it will take a while, then go quiet

**Before any of the slow work**, in two or three lines: that the report is a single HTML
file you will hand over a path to at the end, and **that this will take a few minutes**.

**If the commit log shows the range holds more than one body of work, name them here** — and
then tour all of them. Don't ask which they want. They cannot answer yet; they have not seen
the diff, and you have only just seen it yourself.

If the reader *volunteers* that they only want part of a range, don't tour the rest as
leftovers — **narrow the patch**: `bin/tour-fetch.sh <out> <target> -- <paths>`. Then the
diff itself is the smaller thing, coverage still means all of it, and the overview says
plainly what was excluded. Never narrow to make a tour cheaper; that hides work behind a
guarantee that no longer reaches it.

**Ask nothing once you have started.** This takes minutes, so the reader is somewhere else
by the second one. A question waiting in a terminal nobody is watching is not a checkpoint,
it is a stall that costs them the whole run — they come back to a prompt and no report.
Where the diff leaves you a real choice, make it, tour everything, and say what you chose in
the overview where they will actually read it.
Reading the diff, tracing callers, clustering and building the skeleton all happen before a
word of narration exists. Without this the reader is watching an idle session and wondering
whether it is stuck.

Then work. Don't narrate the intermediate steps — there is nothing useful to report between
here and the finished report, and progress chatter is worse than the silence you warned
about.

## Step C: Acquire the diff

**`bin/tour-fetch.sh <out-file> [<target>]` resolves any target to a patch file.** It
autodetects the form, so you rarely need to know which git command applies:

| Target | What you get |
|---|---|
| *omitted* | this branch since its branch point, plus uncommitted work |
| `a..b`, `a...b` | that range |
| `abc123`, `HEAD`, `HEAD~2` | that one commit |
| `some-branch` | the branch against the default branch (three dots) |
| `807` | PR or MR number in this repo — tries `gh`, then `glab` |
| `https://…/pull/807` | that GitHub pull request |
| `https://…/-/merge_requests/42` | that GitLab merge request |
| `/tmp/x.patch` | copied through unchanged |

It prints the hunk and file count, and the base it chose when there was no target — say
both to the reader, so a wrong guess is visible. If the host has a GitHub or GitLab MCP
server, fetching the diff through that and saving it to the same path is equivalent; the
script is a convenience, not a gate.

**Run it from inside the repository you are touring.** It resolves a git target against the
current directory unless `TOUR_REPO` says otherwise, so running it from somewhere else
silently produces a patch of the wrong repository — or an empty one, if that directory is
not a checkout at all.

Two traps it avoids, which matter if you ever bypass it: the no-target base is the branch
point, never `@{upstream}` (on a pushed branch that covers only unpushed commits); and a
branch target needs three dots, or you diff the working tree against it.

**Everything downstream reads the patch file, never the target.** That is what makes a tour
immune to the branch moving under it: a range is re-resolved on every call, so a commit
landing mid-tour would shift every hunk's start line and invalidate the whole narration file.

For every target, read the commit log over the range. It is the cheapest signal you will
get for intent, and for whether the range holds more than one body of work. It is not a
signal for where the cluster boundaries are — see Step E. Skip merge commits when reading
intent.

Note but exclude from the narrative: lockfiles, generated code, vendored directories, and
pure-formatting churn. Excluded means not narrated, never hidden — those changes still
appear in the Leftovers chapter under one caption naming what they are. Say what was
excluded and how many lines.

If the diff is empty, report exactly what was compared and stop. Don't invent a tour.

## Step D: Understand before writing

The tour is only as good as this step, and it happens before any output.

1. **Read the patch in stages, cheapest first.**

   `bin/tour-hunks.py <patch>` lists every file with what it holds — hunk count, body
   lines, changed lines, and **how many KB reading it in full would cost** — then every
   hunk with git's own context text. On a hundred-hunk change that is about a twentieth
   of the patch, and it is enough to see the shape of the change and to decide what
   deserves reading in full.

   Two things in that listing save a second pass, so read them before reaching for
   `--body`:

   - **`runs:` on a hunk line gives you its fragment boundaries.** A hunk with several
     runs of changed lines is usually several ideas, and the context between the runs is
     where a cut belongs. You do not have to count body offsets off a `--body` read to
     find them — they are already there.
   - **Keep a single `--body` call under about 30 KB**, using the per-file KB figures.
     Tool output is truncated past roughly that, and a truncated read has to be redone
     narrower, which costs a whole round trip. `--body` tells you afterwards how much it
     printed, so a miss is at least visible.

   Then `bin/tour-hunks.py --renames <patch>` names every swap that repeats across
   hunks — `links_to_content` → `external_link_enabled` in fifteen places. Those hunks
   are the mechanical tier: one caption naming the swap, no individual reading, and
   **grep the old name afterwards for stragglers**, which is the highest-value check in
   the caller index and the one that catches a missed call site. What the command leaves
   over is the work that actually needs judgement.

   Then `--body` the area you are touring, one area at a time. It prints the same bytes
   as `cat` plus a body-line offset in the left margin of every hunk, which is what a
   fragment selector needs — so the offsets arrive with content you were going to read
   anyway. **A path argument is a prefix, so reading narrow and then wide reprints the
   narrow part**; `--not <path>` excludes what you have already read.

   **You must have read, in `--body`, every hunk you write a caption for.** The list says
   a hunk exists and how big it is; it does not say what the code does. A caption written
   from a filename is exactly the fluent, plausible, wrong explanation that
   [Narration](#narration) calls the worst thing this skill can produce — and it is worse
   there than anywhere else, because a caption is the one line every scanning reader
   believes.

   The economy is not "caption without reading". It is **`path:all`**: one caption over
   every hunk of a file, stating what the group *is* rather than what any line says. That
   is how a lockfile refresh or a docs sweep costs ten words. A hunk that gets a caption of
   its own gets read first — and the list prints its changed-line count, so you can see
   that most of them cost nothing.

   On a small diff the ladder collapses to one `--body` of the whole patch, which is
   correct. The staging is for the range that holds more than you are touring.

   **This rung and Step E interleave**, and reading them as strictly sequential is what
   makes the ladder look circular: you cannot know what to read in full until you know what
   you are touring, and you cannot name topics from a list alone. The loop is: read the
   list → name candidate topics from it and from the commit log → `--body` the areas those
   topics live in → let what you read correct the topic list → repeat for anything that
   moved. Step E's three passes are the second half of this, not a stage that begins after
   it.

2. **Read the enclosing function or class for each hunk.** Behavior usually lives in the
   unchanged lines around a change — a two-line diff inside a retry loop means something
   different than the same two lines in a constructor.
3. **Read stated intent**: commit messages, PR description, linked issues if cheap. Keep
   stated intent separate from inferred intent when writing.
4. **Trace outward**: grep callers of changed symbols, find the tests covering this area,
   check config or schema the change depends on. **When a change replaces an idiom, also
   grep for surviving uses of the old one** — grepping the new symbol finds adopters, not
   stragglers, and a missed call site is the likeliest bug class in a migration. Report the
   count in the cluster that introduced the replacement; the reader cannot get it from the
   diff.
5. **Establish before-and-after behavior.** For each meaningful change, know what the code
   did before and what it does now. That contrast is the substance of every cluster
   explanation.

**Build one caller index, and share it across every chapter.** Grep the symbols this change
adds or alters *at a module boundary* — exports, public API, anything another file can name
— whole-word, and keep the `file:line` hits. It is small, it is reusable, and it is what
lets a chapter say "three callers, all in `billing/`, and this diff changes two of them"
instead of describing lines. It is also the evidence a `%blast` judgement needs.

**Scope it to the boundary.** Indexing every identifier the diff declares, locals included,
returns more text than reading the whole repository — measured on one 52-file change:
13 boundary symbols gave 30 call sites; all 118 declarations gave 20,515 hits. A local
`const` has no callers to find, and grepping it drowns the index.

**Don't read whole files for context.** The enclosing function or class of a hunk is already
in git's `@@` header, once per hunk, free — `tour-hunks.py` prints it. Reading the file to
rediscover what the diff told you is where unbounded cost comes from.

**Read at depth everything that will get a chapter — including a body of work you did not
come for.** Under [Step H](#step-h-narrate-the-leftovers), substantial work gets chapters
however unrelated it is, and a chapter cannot be written from a file listing. On a range with
three bodies of work this is the largest cost in the tour, and it is the cost of the report
being worth reading; if the reader only wants one body, that is a decision for them to make
in Step B, not one to make silently by skimping here.

What you may still read by path alone is what Step H's first kind covers: mechanical churn.
A lockfile refresh, generated output, a vendored directory, pure formatting — one
`path:all` group per file, one caption naming the kind. That is where the saving lives, and
it is bounded.

What none of this licenses is a per-hunk caption written from a path. Leftovers is the tail
of the report, the model is tired, and the hunks look boring — which is exactly the
combination that produces "the version" over a line that is not a version. If you are
writing a caption for one specific hunk, read that hunk. A leftover hunk is usually two to
seven lines; the list tells you which, and those are free.

**Delegate only when the reading is genuinely large.** If answering a cluster's questions
needs substantially more code than the cluster contains, and several clusters need that
independently, hand those reads to subagents and keep the judgement. Otherwise don't: a
subagent costs more wall clock than the greps it would run. When you do delegate, a
positive finding may be summarized, but **a claim that something does not exist must come
back as the command and its output** — that is the claim a reviewer will lean on.

## Step E: Cluster

Extract topics, assign every change, settle. The rules are in
[Clustering](#clustering) — read them there rather than working from memory, because this
step decides how good the tour can possibly be. Decide fragment boundaries here too: which
hunks carry two ideas, and which lines go where.

## Step F: The skeleton

**Write the whole report's structure before any of its prose.** Every chapter, every beat
subtitle, every block with its caption — and not one sentence of narration.

Include each cluster chapter's `%blast <level>` line — the level is a Step E judgement and
the skeleton is where structure lives. Its evidence is prose and comes in Step G.

**No `[[label]]` references either**, because the labels do not exist yet: this is the
command that mints them. Writing one here is harmless — the skeleton defers the check and
tells you — but you cannot know the right name until the table is printed. References are
Step G's business.

Then:

    bin/tour-skeleton.py <patch> <narration> [--root DIR]

It labels every block, prints the table of what you have built, and tells you whether every
changed line is placed. Three things are much cheaper here than later:

- **Coverage settles before the expensive part.** On a large change the prose is tens of
  thousands of tokens. Finding out afterwards that a fragment boundary was two lines short
  means editing prose that should never have been written. Fix coverage now, with
  `bin/tour-rest.py`, while it costs nothing.
- **Every block gets a label**, which is the only way prose can point at a block.
- **The table is what a chapter needs in order to know its neighbours** — see Step G.

The skeleton is not gospel. **While narrating a chapter you may reorder its beats and its
blocks freely**, and you should when writing reveals a better order — "order follows the
explanation" is the rule, and you sometimes only find the explanation by writing it. Labels
move with their blocks, so nothing that points at them breaks.

A block is a unit: its directive, and any prose indented under it. Move the unit.

Two things are frozen once the skeleton is checked:

- **A block stays in its chapter.** Moving one is re-clustering — a Step E decision, not a
  narration one — and it breaks the single assumption a chapter narrated on its own is
  allowed to make: that its own blocks are its own. (Coverage would survive it, since
  coverage is chapter-agnostic. The reason is the assumption, not the arithmetic.)
- **Chapter order stays as it is.** `[[ch5]]` resolves by position, so moving a chapter
  after any prose exists silently repoints every reference to it. Chapter order is also
  part of the report's argument — "understandable from its predecessors alone" — so a
  reordering here is a clustering change and belongs in Step E.

Write the skeleton for every chapter, in order — `%intro`, the clusters, `%leftovers`,
`%closing` — even though the first and last get their prose last.

## Step G: Narrate the cluster chapters

Fill in the prose: the chapter's introductory paragraph, its `%blast` evidence, each beat's
narration, and each block's own indented prose. How much to say, where to say nothing, what
to admit, when to name an alternative — all of that is [Narration](#narration) and
[Beats](#beats).

**This is where references get written**, using the labels Step F printed. That ordering is
not a preference: a label is minted by the skeleton, so prose is the first stage that can
name one.

**Narrate the chapters in parallel when there is enough prose to divide and you have an
agent tool that can fork.** A fork inherits your context, so it already holds the patch
reads, the caller index and the skeleton — there is nothing to brief it on. Tell each fork:

- **which chapter** it owns, and that the skeleton table is how it names a block in any
  other chapter;
- that it may reorder beats and blocks inside its chapter and may not move one out;
- to write **only its own chapter** — its `%chapter` line, its `%blast`, its beats — into
  `<narration>.ch<n>`, beside the narration file. One file each, so nothing races. No
  `%report`, no other chapter;
- to **end its report to you with its admissions**: what it could not explain, what looked
  wrong, what it took from a comment rather than from code, each with its block's label.
  Step I has to collect those, and without this you would have to re-read every word the
  forks wrote — which is the cost forking just paid to avoid.

Then **splice each chapter file over its counterpart in the skeleton** — replacing that
chapter's block, keeping `%report`, `%intro`, `%leftovers` and `%closing` where they are.
Do not concatenate the chapter files: they are the middle of a document, not the whole of
one, and a missing `%report` or `%intro` is only a warning, so a botched merge would build.

**Fork the chapters that are worth forking, not the report.** This is not one decision for
the whole run: the skeleton shows you how many blocks each chapter holds, and chapter sizes
are usually lopsided. Fork the three or four fat ones and write the thin ones yourself.
Forking a two-block chapter buys nothing and pays a full context re-prefill for it.

Wall clock is the *longest* chapter, not the sum — so a report with one twenty-block chapter
and eight small ones barely improves however many forks you spawn, and the honest answer
there is to write it serially and spend the effort on Step D instead, which is the larger
half of the clock anyway.

**What it costs:** each fork re-prefills your context, so N forks buy one pass of the output
in exchange for roughly N times the input.

**What it gives up:** no chapter can see what another chapter *wrote*, only what the
skeleton says it contains. Two chapters can explain the same thing twice and nothing will
catch it. The captions in the skeleton are what keep that rare, which is another reason they
are worth writing properly.

**If the host does not allow subagents, write it serially and don't stop to ask.** Some
sessions carry a standing instruction against spawning them, and that outranks this
recommendation. Say in the handover that the report was narrated serially and that allowing
subagents would have divided the narration phase — a fact for next time, not a question
now.

## Step H: Narrate the leftovers

**Leftovers is a small chapter for small things.** Exactly two kinds of change belong here:

1. **Changes too slight, or purely mechanical, to be worth a chapter** — a `.gitignore`
   line, an editor config, a version bump, a lint rule; and a lockfile refresh, generated
   output, a vendored directory or formatting churn **however many lines it runs to**. Each
   is real and each is shown, but a chapter apiece would bury the report's structure under
   its own furniture, and nobody reviews a regenerated lockfile line by line.
2. **Changes you genuinely cannot assign** — you read them, and they belong to no idea you
   can name. Say that plainly; it is a finding, not an embarrassment.

**It is not the bin for everything unrelated to the change you came for.** A second
substantial body of work is a topic and gets its own chapters — see
[pass 2](#how-to-find-them). The test is significance, not connection: a thousand lines of
rewritten documentation is not a leftover just because it has nothing to do with the bug fix
you were asked about.

If this chapter is long, or if it holds anything you would describe as *a body of work*,
that is the signal that pass 1 missed a topic. Go back rather than writing a bigger caption.

**When you cannot tell** — an unrelated sixty-line cleanup across five files — give it a
chapter. A small chapter costs the reader one line in the sidebar; a mis-filed leftover
costs them the chance to review it at all.

Each group needs prose saying **what it is and which of the two kinds it is** — that is what
makes a scroll-past an informed decision. `%fold` them; nobody reads a dependency bump line
by line, and the size stays on screen.

## Step I: The overview and the wrap-up

Both come last, because both are about the whole report, and now you have written it. The
overview is still chapter 1 in the document.

    %intro Overview

    %beat What it does
    2–4 sentences: the problem and the approach taken.

    %beat New behavior
    Bullets, only things observably different for a user, caller, API consumer,
    or the data. "None — internal refactor" is a valid and useful answer.

    %beat Where to be careful
    Up to 3 ranked pointers at where risk concentrates, each naming the cluster
    it lives in. These are attention pointers, not verified bugs.

    %beat The chapters
    One half-line per chapter, saying what it is about. The sidebar gives their
    names; this gives their purpose, which is how a reader decides what to read.

There is no Scope section: the metadata line under the title already gives the file count,
the line counts and the block count, and two places stating the same numbers is how they
come to disagree. Do say here **if the range holds more than one body of work**, name each
one, and say which chapters cover which — that is orientation a reader cannot get anywhere
else, and it is what lets them read one body and stop.

    %closing Wrap-up

- **Recap** the change as a chain: cluster 1 enabled cluster 2 enabled cluster 3. Three or
  four sentences; the reader should be able to retell the change from this. A causal chain
  is inference by construction, so say so — most of it is your reading, not the code's.
- **What you still need to check yourself.** Collect the admissions the chapters made: the
  blocks you could not explain, the ones that looked wrong, the claims you took from a
  commit message or a comment rather than from code, and whether you ran the tests. Each
  with its label, so the reader can go back to it.
  Do **not** list what you did verify. A roster of successful checks reads as a
  certificate, and manufacturing that reassurance is the thing this section exists to
  prevent.
- **Open questions** for the author, if any.

**Before citing a label anywhere in these two chapters, read that label's caption in the
skeleton table.** A label reference is guaranteed to *resolve*, never to *aim* — nothing
mechanical can tell that `[[h29]]` points at the export list when the explanation is in
`[[h28]]`. The table makes that a one-glance check, and these two chapters are where
misfired citations do the most damage, because they are where a reader decides what to
read.
- **Suggested next step** — usually a dedicated correctness pass over the same diff
  (`/code-review` in Claude Code), or a specific file worth reading in full.

## Step J: Hand it over

Build. **A report with an unshown line or a single warning is not finished** — the builder
writes the file either way, so this gate is yours to hold, not its. Fix, rebuild, and only
then say three things and stop:

- **What the page has**, in a clause: chapters in the sidebar, a viewed mark per block.
- **Invite questions.** They can ask about anything they have just read, and **every block
  carries a code like `3.2`** they can quote to point at one. The report is a file and
  cannot contain this invitation; it is the only interactive surface the conversation has,
  and a reader holding a path has no other signal that you are still here.
- **The path**, on its own line, last, with nothing after it.

## Troubleshooting

**Diff is mostly formatting** — Detect with `git diff -w`, but tour the *full* patch:
coverage counts what it was given, so touring the `-w` diff would leave the formatting
changes unaccounted for. Cluster the substantive hunks and give the churn one folded
leftover group.

**`gh` fails** — Say so, suggest `gh auth login`, and offer to tour a local range instead.

**Reader interrupts with a question while you are working** — answer it, then continue where
you stopped. Never restart from the top unasked.

**A hunk's language is not highlighted** — the vendored Prism has no grammar for that
extension. The diff still renders with markers and tinting. Not worth fixing mid-tour.

**A block's colours look wrong** — a token that opens above the hunk (a template literal, a
block comment) cannot be seen by a highlighter that only has the hunk. Every diff
highlighter has this. Don't chase it.

**You changed this skill and want to know what you broke** — `python3 tests/test_difftour.py`
covers everything between the narration file and the HTML: the diff parser, the narration
parser and its refusals, the coverage arithmetic, the prose subset, and the rendered markup.
Clustering and narration are judgement and are not in there.
