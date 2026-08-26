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
lets the reader skip, and a dull chapter is cheap to scroll past. Nothing in the report
starts hidden; the reader collapses what they have read. What you may compress is the
*narration* — one
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
  on the *same* lines, show the overlapping fragment in both. The builder prints a **note**,
  not a warning: only you can tell a deliberate overlap from an off-by-one, so it says so
  once and does not hold up the report. Read it, satisfy yourself it was deliberate, move on.
- **Don't split what is one idea.** Fragmenting a coherent hunk to make chapters look
  tidier costs the reader the context that made it legible.

Other shaping:

- **Merge nothing.** Two adjacent hunks that are one idea are two blocks in one beat, with
  one caption each. There is no reason left to glue them together.
- **Repetitive hunks** — the identical mechanical change in eight call sites — all get
  shown, in the same chapter as the one you explained, never deferred to Leftovers. Explain
  the pattern once in the beat's prose and give each block a one-line caption.
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
formatting-only hunks aside as one leftover group, note the line count, and tour the
substantive diff.

**New files** — show the whole file. It is all new code, and none of it has been reviewed
before. Say how long it is, and lead the narration with its shape — exported names, entry
points — so the reader knows what they are scrolling through. `%hunk <path>:all` takes the
whole thing in one directive.

**Deleted files** — show the whole file. Every line of a deleted file
is a changed line, so showing only the signatures would leave the body uncovered and the
completeness check would be right to complain. The reader can collapse it in one click; what
the narration owes them is the only question that matters — what capability disappeared, and
who used it.

**Binary files** — never show a diff. `%file` renders one line naming the file and what
happened to it, deriving the kind from the diff so it cannot be stated wrongly. A binary
needs no explanation of its own, so one beat can hold a list of them.

**Lockfiles and generated code** — one `%hunk <path>:all` each in a leftover group.

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

**So does one policy applied across many surfaces.** A change that threads the same decision
through a controller, a model, four views, a cache and an API version has a chapter per
surface, because that is where a reviewer checks it — one real tour of a single body of work
ran to thirteen chapters and was right to. The range catches a diff carved at arbitrary
joints, not a diff that genuinely touches many places once each. If every chapter answers a
different question, the count is fine however high it is.

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
wrong version of the file — fluently, and byte-exactly.
[Step B](#step-b-get-the-diff-and-a-checkout-that-matches-it) establishes that checkout with
`bin/tour-checkout.sh`; quote from the path it printed, and pass the same path as `--root`.
`tour-build.py` compares the two and refuses a `--final` build when they disagree, so this is
caught rather than trusted. If no such checkout could be established, don't quote at all:
cite the change by its label instead.

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

Distinguish **"I looked and could not find"** from **"I did not look"** — a chapter's
gathering in Step G scales to what the chapter turns on, so both are honest, but they send
the reader to different work. And if admissions pile up in one chapter, look again before
narrating on through hedged mush; if they pile up across all of them, the clustering is the
problem, not the prose.

Carry these forward to the wrap-up chapter, which is the only place they are collected.
Give each one its block's label, so the reader can go back to it.

**Gloss a term once per chapter, at first use, in a clause.** Where a project's own concept
is unavoidable, define it in passing and move on. Once *per chapter*, not once per report,
because chapters are written concurrently and none of them can know what another already
explained — and because a reader who starts at chapter 5 gets the same help as one who
started at chapter 1. If the tour needs a glossary, the narration is failing.

**Say "change", not "hunk".** A hunk is a unit of `git diff` output and the word means
nothing to most readers; this skill uses it throughout because it is talking to you, and the
report does not. In prose and in captions, the things on the page are **changes** — "the
change in `[[h17]]`", "the three changes to the disable path", "this change does not cover
the fourth call site". The same goes for the other words this document needs and a reviewer
does not: no "fragment", no "block", no "cluster", no "coverage" in the report. Chapters and
changes are the only structure the reader has to hold.

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
- **moderate** — reaches other modules, through call sites found by grepping for them
  ([Step G](#step-g-narrate-the-cluster-chapters) calls this the chapter's caller index).
  Name them.
- **wide** — public API, or behavior observable outside the codebase. **A new error or
  refusal on a path that previously succeeded is always wide**, however few lines it took
  and however local its call sites: the people it reaches are users of the library, not
  callers of the function.

The levels are the cheap half of this. The evidence under them is the product, so if the
level is arguable, write the evidence and pick the higher one.

It is **inferred scope, not a verdict** — which is what keeps it clear of "never certify".
It is also the one place a chapter's caller index pays off visibly, so a `moderate` or `wide`
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
| `bin/tour-splice.py` | narrated chapters | them, back in the narration file |
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
diff-tour — a guided, chapter-by-chapter walkthrough of a code change

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
narration that explains them, a chapter sidebar, and a viewed mark per change.
Needs git and python3 (3.10+). Nothing to install.
```

## Step B: Get the diff, and a checkout that matches it

**This is the only step in which you may ask the human anything.** They are watching now and
they will not be in a minute, so everything that might need them happens here, before the
slow work starts. After this step, questions are worse than useless — see the end of
[Step C](#step-c-say-it-will-take-a-while-then-go-quiet).

### The patch

**`bin/tour-fetch.sh <out-file> [<target>]` resolves any target to a patch file.** It
autodetects the form, so you rarely need to know which git command applies. Every target form
it accepts, and what each resolves to, is in
[references/commands.md](references/commands.md) — a git range, one commit, a branch, a PR or
MR number or URL, a patch file, or nothing at all for your working diff.

**Give the tour its own directory, and not a scratch one a session cleans up.** Name the
directory after the target — `difftour-<something-identifying>` — and put three files in it,
named exactly this:

    <dir>/tour.patch      the diff, plus tour.patch.head beside it
    <dir>/tour.tour       the narration
    <dir>/tour.html       the report

Fixed names, because a target like `hk/integration-2026-kw29..HEAD` contains a slash and
makes a poor filename, and because the human needs to be able to find these without asking.
**The header's name for the diff comes from `--source`**, not from the filename, so pass the
real target there and the report still says `hk/integration-2026-kw29..HEAD`.

All three matter. The report is what the reader opens; the other two are the only way anyone
can later see what it was built from, re-run a stage, or turn a real narration into a test
fixture. A tour whose narration was thrown away cannot be diagnosed at all — only re-run from
scratch.

It prints the hunk and file count, the base it chose when there was no target, and any
**untracked files**, which are *not* in the diff. Say all three to the reader. The untracked
list matters more than it looks: coverage guarantees every line of the patch is shown, and an
untracked file is not in the patch — so it is the one omission the guarantee cannot see, and
the only way the reader learns of it is you repeating it. If the host has a GitHub or GitLab MCP
server, fetching the diff through that and saving it to the same path works — **but write the
PR's head SHA to `<out>.patch.head` as well.** Without that file no checkout can be matched to
the diff, which forbids `%quote` for the whole tour and downgrades every Step G grep to
evidence about a possibly different version of the code. The MCP response carries the SHA; the
script is a convenience, not a gate, but the sidecar is not optional.

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

If the diff is empty, report exactly what was compared and stop. Don't invent a tour.

### The checkout

    bin/tour-checkout.sh <patch>            # prints the path to use as --root

**A patch alone is not enough to write a tour from.** Hunks are spliced from the patch and
are always exact, but everything else you will read comes off a disk: `%quote` reads a file,
and [Step G](#step-g-narrate-the-cluster-chapters)'s caller index and its "does anything test
this" greps read a repository. Those have to read *the version of the code this diff ends
at*, and your HEAD is very often not that:

- `HEAD~3..HEAD~1` — an ordinary local range that simply does not end at HEAD;
- a pull request — `gh pr diff 807` hands you the diff whether or not that branch was ever
  fetched;
- someone's branch you are reviewing without checking out.

On the wrong version, a quote shows the wrong lines under a caption that says otherwise, and
a grep for callers of a symbol the branch *introduces* finds nothing — so the report says
"no other callers" and means "I looked in a tree where this does not exist". **Neither
failure announces itself.** That is why this is a step and not a caveat.

`tour-checkout.sh` resolves it once, here. It prints on stdout the path to use as `--root`
and to grep in, which is either the repository itself (when HEAD is already the diff's end
commit — the ordinary case for your working diff, where uncommitted work belongs in the
tour) or a detached worktree at the right commit. It never switches your branch and never
touches the working tree, so uncommitted work is not in its way, and re-running it is free.

**Carry that path through the whole tour.** Pass it as `--root` to **every command that
takes one** — `tour-skeleton.py` and `tour-build.py` — and run Step D's and Step G's greps
there, not in the current directory. `tour-rest.py` needs no root: coverage is a function of
the patch and the directives alone, so it never reads a file from disk.

When it exits non-zero, **this is the moment to ask.** Exit 4 means the commit is not here
and could not be fetched: a human can fetch the branch, add a remote, or tell you to go
ahead without quotes, and it costs them seconds now versus a wasted run later. Exit 3 means
the patch came from elsewhere and records no end commit, so no checkout can be matched to
it — then don't use `%quote` at all, treat every grep as evidence about a possibly different
version of the code, and say so in the handover.

### The log

For every target, read the commit log over the range. It is the cheapest signal you will
get for intent, and for whether the range holds more than one body of work. It is not a
signal for where the cluster boundaries are — see Step E. Skip merge commits when reading
intent.

Note which files are mechanical churn — lockfiles, generated code, vendored directories,
pure formatting. They are not narrated in a chapter, and they are never hidden either;
[Step H](#step-h-narrate-the-leftovers) says what becomes of them. Say what you excluded and
how many lines.

## Step C: Say it will take a while, then go quiet

**Before any of the slow work**, in two or three lines: that the report is a single HTML
file you will hand over a path to at the end, and **that this will take a few minutes** —
reading the diff, clustering it and building the skeleton all happen before a word of
narration exists. Without that the reader is watching an idle session and wondering whether
it is stuck.

This comes *after* Step B so that it can say something worth reading. You now hold the diff
and the log, so "this will take a few minutes" becomes "this range holds two things, an auth
refactor and a lockfile bump; I am touring both" — a warning turned into an orientation.
Announce once, here.

**If the commit log showed the range holds more than one body of work, name them** — and then
tour all of them. Don't ask which they want. They cannot answer yet; they have not seen the
diff, and you have only just seen it yourself.

If the reader *volunteers* that they only want part of a range, don't tour the rest as
leftovers — **narrow the patch**: `bin/tour-fetch.sh <out> <target> -- <paths>`. Then the
diff itself is the smaller thing, coverage still means all of it, and the overview says
plainly what was excluded. Never narrow to make a tour cheaper; that hides work behind a
guarantee that no longer reaches it.

**Ask nothing from here on.** This takes minutes, so the reader is somewhere else by the
second one. A question waiting in a terminal nobody is watching is not a checkpoint, it is a
stall that costs them the whole run — they come back to a prompt and no report. Where the
diff leaves you a real choice, make it, tour everything, and say what you chose in the
overview where they will actually read it. Anything that genuinely needed them was Step B's
business, and Step B is over.

Then work. Don't narrate the intermediate steps — there is nothing useful to report between
here and the finished report, and progress chatter is worse than the silence you warned
about.

## Step D: Understand what changed

**This step establishes what each hunk changes — not whether it is right.** That distinction
is what keeps the serial part of a tour short. Clustering needs to know what a hunk *does*,
because that is what decides which idea it serves. It does not need to know what the code did
before, who else calls it, or whether anything tests it: those are things you say *about* a
cluster once you have one, and they are Step G's work, inside the chapter that needs them.

Getting this wrong in either direction is expensive. Skimp here and the chapter boundaries
are guesses. Go deep here and you do, serially, for all 131 hunks, work that only twelve
chapters will ever consume — and Step G could have done it in parallel.

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
   are the mechanical tier: one caption naming the swap, no individual reading. What the
   command leaves over is the work that actually needs judgement. **Don't grep for
   stragglers yet** — that check is the highest-value one in the tour, and it belongs to
   whoever narrates the chapter that owns the sweep, where its answer becomes a sentence.
   [Step G](#step-g-narrate-the-cluster-chapters) assigns it.

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

2. **Take the enclosing scope from the `@@` header**, which `tour-hunks.py` prints for every
   hunk, free. A two-line diff inside a retry loop means something different than the same
   two lines in a constructor, and the header usually tells you which. Open the file only
   when it genuinely does not.
3. **Read stated intent**: the commit log over the range, the PR description, linked issues
   if cheap. This is where candidate topics come from. Keep stated intent separate from
   inferred intent when writing.

**That is the whole of it.** Three things: what changed, roughly where it sits, and what the
author says they were doing.

**What does *not* belong here**, however tempting, because a single chapter is the only thing
that consumes it and Step G can do it in parallel:

- who calls a changed symbol, and how many call sites this diff did not touch;
- what the code did before, in any detail beyond what the hunk shows;
- whether anything tests a change;
- any question of the form "does X actually do Y" — *does this controller build a plain
  `Card`*, *does that partial guard a nil*, *is this opt-out covered*. Every one of those
  feeds a sentence in one chapter. Ask it there.

**Don't read whole files for context**, and don't build a caller index yet. Reading a file to
rediscover what the diff already told you is where unbounded cost comes from, and an index
built now is built for chapters that do not exist yet.

**Read at depth everything that will get a chapter — including a body of work you did not
come for.** Under [Step H](#step-h-narrate-the-leftovers), substantial work gets chapters
however unrelated it is, and a chapter cannot be written from a file listing. This read is bounded by
the size of the diff — you read each hunk once — which is what keeps it affordable even on a
range with three bodies of work, and it is the cost of the report being worth reading. If the
reader only wants one body they have to have *volunteered* that back in Step C, while they
were still there, and the patch was narrowed then — nobody was asked, and by here nobody is
listening. So this is not a decision you can still make; skimping on it just makes a worse
report of the same diff.

What you may still read by path alone is what Step H's first kind covers: mechanical churn.
A lockfile refresh, generated output, a vendored directory, pure formatting — one
`path:all` group per file, one caption naming the kind. That is where the saving lives, and
it is bounded.

What none of this licenses is a per-hunk caption written from a path. Leftovers is the tail
of the report, the model is tired, and the hunks look boring — which is exactly the
combination that produces "the version" over a line that is not a version. If you are
writing a caption for one specific hunk, read that hunk. A leftover hunk is usually two to
seven lines; the list tells you which, and those are free.

## Step E: Cluster

Extract topics, assign every change, settle. The rules are in
[Clustering](#clustering) — read them there rather than working from memory, because this
step decides how good the tour can possibly be. Decide fragment boundaries here too: which
hunks carry two ideas, and which lines go where.

## Step F: The skeleton

**Write the whole report's structure before any of its prose.** Every chapter, every beat
subtitle, every block with its caption — and not one sentence of narration.

**Give every chapter a title no other chapter has.** The title is how a chapter narrated on
its own finds its place again, so two chapters called "Cleanups" cannot both be spliced back.
`bin/tour-skeleton.py` refuses a duplicate, which is the cheap moment to hear about it: after
[Step G](#step-g-narrate-the-cluster-chapters) starts, titles are frozen, and the collision
surfaces in a fork's own check — where the fork cannot fix it, because only you can retitle.

A skeleton carries **no `%blast` line**. A blast level is a claim about reach, and reach is
what the caller index tells you — which Step G gathers, per chapter. Judging it here would
mean gathering that index serially for every chapter, which is the work this split exists to
move.

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

- **A block stays in its chapter while chapters are being written.** Moving one breaks the
  single assumption a chapter narrated on its own is allowed to make: that its own blocks
  are its own. (Coverage would survive it, since coverage is chapter-agnostic. The reason is
  the assumption, not the arithmetic.) That is why a fork *reports* a misfit rather than
  fixing it — and why the orchestrator may fix it once every fork has returned, in Step G.
- **Chapter order stays as it is.** `[[ch5]]` resolves by position, so moving a chapter
  after any prose exists silently repoints every reference to it. Chapter order is also
  part of the report's argument — "understandable from its predecessors alone" — so a
  reordering here is a clustering change and belongs in Step E.

Write the skeleton for every chapter, in order — `%intro`, the clusters, `%leftovers`,
`%closing` — even though the first and last get their prose last.

## Step G: Narrate the cluster chapters

**This is where the deep work happens, and it is the part that parallelises.** A chapter's
narration needs things Step D deliberately did not gather: what the code did before, who
calls the symbols this chapter changes, whether anything tests them, and the answer to
whatever specific question the chapter turns on. Each chapter needs those for *its own*
hunks, which is why they belong here rather than in a serial pass over the whole diff.

So each chapter's work is: gather its own facts, then write its prose — the chapter's
introductory paragraph, its `%blast` level and the evidence for it, each beat's narration, and
each block's own indented prose. How much to say, where to say nothing, what to admit, when
to name an alternative — all of that is [Narration](#narration) and [Beats](#beats).

**Gathering a chapter's facts**, and none of it for hunks outside the chapter. **Every grep
below runs in the checkout Step B printed**, not in the current directory — on the wrong
version of the code, a grep for callers of a symbol this branch introduces finds nothing, and
"no other callers" is then a confident false statement rather than a missing one:

- **Its caller index.** Grep the symbols this chapter changes *at a module boundary* —
  exports, public API, anything another file can name — whole-word, and keep the `file:line`
  hits. That is what lets the chapter say "three callers, all in `billing/`, and this diff
  changes two of them" instead of describing lines, and it is the evidence `%blast` needs.
  **Scope it to the boundary**: indexing every identifier a diff declares, locals included,
  returns more text than reading the repository — measured on one 52-file change, 13 boundary
  symbols gave 30 call sites while all 118 declarations gave 20,515 hits. A local `const` has
  no callers to find and grepping it drowns the index.
- **The stragglers.** When the chapter replaces an idiom, grep for surviving uses of the *old*
  one. Grepping the new symbol finds adopters, not stragglers, and a missed call site is the
  likeliest bug class in a migration. `bin/tour-hunks.py --renames` names the swap for you.
- **Before-and-after behavior**, for the changes this chapter explains. That contrast is the
  substance of the explanation.
- **Whatever the chapter specifically turns on.** One or two questions with checkable
  answers, asked at the point the sentence needs them.

**Many of these facts are shared, so gather those once — before you fork.** The model
above is per-chapter, and on a real 14-chapter tour that was only half true: the caller
index, the straggler greps and the "is this tested" negatives overlapped so heavily that
they batched into about six calls for the whole diff. Anything several chapters will ask
for is cheaper asked once by you and handed down:

- Run the greps whose answers more than one chapter needs — the symbols at the change's
  centre, the old names of any sweep, the test files that touch any of it.
- Put the results in each fork's briefing, in a few lines, and say they are already
  gathered so nothing re-runs them.

What stays per-chapter is what only that chapter turns on: its own before-and-after, and
the one or two specific questions its sentences need.

**A fact about the world outside the diff is either read from the checkout or hedged.**
Release dates, end-of-life dates, what a library dropped in which version, what is
"maintained until" when — none of that is in the patch, none of it is checkable by the reader
against anything on the page, and it is where an explanation is most likely to be fluent and
wrong. A dependency-upgrade tour leans on such claims heavily, so decide per claim:

- **Read it** from the checkout — a changelog, a gemspec, a comment, the lockfile — and cite
  where, or quote it with `%quote`. Then it is evidence like any other.
- **Or attribute it**: "per the Rails maintenance policy as I understand it", "reportedly".
  A hedged date a reviewer can go and check beats a bare one they cannot.

And **never state a fact about the reader's machine or the author's**. You know what is in the
diff and what is in the checkout you were given. "The pin this branch replaces named a Ruby
that was not installed on the author's machine" is not something you can know — at most it was
not installed on *yours*, which is a different and much less interesting claim.

**A negative has to arrive as evidence.** A positive finding can be summarized — "three
callers, all in `billing/`". But **a claim that something does *not* exist must be backed by
the command and its output**: nothing tests this, nothing else calls that, no other call site
survives. Those are the claims a reviewer leans on hardest, and they are the ones a
plausible-sounding sentence gets wrong. This holds whether you gathered the fact yourself or
a fork reported it to you.

**A lookup is never worth its own round trip.** Whenever you are about to run a grep, put it
in the same message as the next read you were going to make anyway.

### Do this in parallel

**Fork by default. Serial is the exception and needs a reason.** The deep work above is now
the bulk of a tour's cost, it is per-chapter, and chapters do not depend on each other — so
running them one at a time is leaving the largest available saving on the floor.

### "Unless the user requested it" — they did

Many sessions carry a standing instruction of the shape **"do not spawn subagents unless the
user requested it."** Reading that as a flat ban is expensive — it turns every large tour into
the slowest possible run of itself, and the reader did ask for a tour, of which forking is a
documented part. But it is not yours to declare satisfied either: some operators mean exactly
"unless they asked for subagents", and overruling that silently is not a call this document
gets to make on your behalf.

**So say it, in the announcement, and go.** [Step C](#step-c-say-it-will-take-a-while-then-go-quiet)
is the last moment anyone is watching, and this costs it one clause:

> …a few minutes. I'll narrate the chapters in parallel with subagents — say now if you'd
> rather I didn't.

That is a statement, not a question: **do not wait for an answer, and do not stall.** Fork and
carry on. If they object, they are still there to say so, and Step G is early enough that a
serial restart costs one phase rather than the run.

**Serial is right in three cases, and only these:**

- **The host has no subagents at all.** Nothing to decide.
- **The reader said not to use them** — in this session, in their own words, about subagents.
  Not "unless requested"; an actual refusal.
- **The report is small** — a handful of blocks in total, where one pass is already short.

In the first two, write it serially, **don't stop to ask**, and say in the handover that the
report was narrated serially and why. That is a fact for next time, not a question now — the
reader is not watching. In the third, serial is simply correct and needs no note.

### How many

**What the choice is actually between.** Serial costs the sum of every chapter. Forked costs
the *longest fork*. On fourteen chapters where the biggest is a third of the work, that is
one third of the wall clock instead of all of it — a large win, and the normal case. Read the
rest of this section as "how many forks", never as "whether to fork".

**Not one per chapter, though.** Wall clock cannot drop below the biggest single chapter, so
once a fork carries about that much, another fork saves nothing and still costs a full context
re-prefill. Seventeen chapters do not want seventeen forks — they want four or five.

**`bin/tour-skeleton.py` prints a suggested packing** under the table — it knows every
chapter's block count, so the arithmetic is already done and is not yours to spend thinking
on. Take it, or adjust it for something it cannot see.

Three things it cannot see:

- **Whole chapters only.** A fork may own several chapters but never part of one, so the
  no-moving-blocks-between-chapters rule and the splice both stay simple. It writes one file
  per chapter it owns, whichever fork wrote it.
- **Past five or six forks, ask what the sixth is buying.** There is no hard limit, but if the
  packing wants ten, the chapters are probably cut too finely — that is a Step E problem, not
  a spending one.
- **You are not idle while they run.** [Step H](#step-h-narrate-the-leftovers) needs no
  per-chapter facts, so write the leftovers chapter yourself while the forks work. Write it
  straight into the narration file: the splice never touches `%leftovers`, and a fork only
  ever *reads* that file, so your writing and their reading do not collide.

### What to tell each fork

A fork inherits your context, so it already holds the patch reads and the skeleton — there is
nothing to brief it on. **If this host's subagents do not inherit context**, they need that
first: tell each one to read `bin/tour-hunks.py --body <patch> <its files>` and the skeleton
table before anything else, and say which chapter's blocks are its own. Everything below
applies either way. Tell each fork:

- **which chapter or chapters** it owns, and that the skeleton table is how it names a block
  in any other chapter;
- that its fact-gathering is its own, for its own hunks;
- that it may reorder beats and blocks inside its chapter and may not move one out;
- to write **only its own chapter** — its `%chapter` line, its `%blast`, its beats — into
  `<narration>.ch<n>`, beside the narration file. One file each, so nothing races. No
  `%report`, no other chapter;
- to **start from the chapter's directives as they already stand in the narration file and
  keep every `@label` exactly**, along with the `%chapter` title, which is the key the
  splice matches on. A fork that retypes a directive from the skeleton table drops its
  label, and then every `[[…]]` its siblings wrote at that block dangles — a failure that
  surfaces at your build, in prose you did not write and will not read. Copy the lines,
  then add prose around them;
- that **the label, the spec and the chapter title are frozen, but the caption is not**.
  Captions were written in Step F from a deliberately shallow read; the fork is the first
  to read the block properly, and "[a caption states what you read](#captions)" outranks
  the copy. Correcting a caption its reading disproves is the fork's job, not an
  overstep — and it costs nothing, because nothing matches on a caption;
- to **leave any block it adds unlabelled**, and never to mint a label itself. Two forks
  both inventing `@h50` collide, and the collision surfaces as a refused build in chapters
  you never read. Adding `%quote` and `%code` is expected. **If it splits a labelled hunk
  into fragments, the original label stays on one of them** — its first, by convention —
  and the others go in bare; that keeps every `[[…]]` a sibling already wrote pointing at
  real code, which is why the splice refuses a chapter that dropped a label. The bare
  fragments get named by the `tour-skeleton.py` run in [Step I](#step-i-the-overview-and-the-wrap-up);
- to **check its own file before returning**, with

      bin/tour-splice.py --check --root <checkout> <patch> <narration> <its file>

  which validates the fragment and writes nothing. It resolves every spec, so the `%quote`
  and the split fragments the fork just wrote are checked against the real patch and the
  real checkout — those are the only specs that can be wrong, because they are the only new
  ones. A mistake caught by the fork costs the fork a minute; the same mistake caught after
  the splice costs you a debugging round in a chapter you never read;
- to **end its report to you with these five things**, each keyed to a block's label where it has
  one. You will not read the prose it wrote — that is the cost forking paid to avoid — so
  this report is the only thing you get, and Step I is written from it:
  - **its admissions**, already worded as the wrap-up should print them: what it could not
    explain, what looked wrong, what it took from a comment rather than from code. Ask for
    finished sentences, because you will **paste them, not restate them** — you did not read
    the chapter, so rewording an admission can only make it less true;
  - **its risk pointers**: the one or two places in its chapter where a reviewer should look
    hardest, which is what the overview's "where to be careful" is assembled from;
  - **two or three sentences on what its chapter established**, which is what the wrap-up's
    causal chain is assembled from;
  - **any block it believes belongs in another chapter**, with the label. It must not move
    one — its siblings are working from the skeleton as it stands — but it is the first
    entity to read that block at depth, so it is the only one who can notice;
  - **whether its chapter is really one idea**, and whether it overlaps another chapter. A
    fork reads one chapter more closely than you read all of them, so this is the only
    honest check on Step E. Re-clustering after the fact is usually too expensive, so what
    you do with the answer is **say it in the overview**: a chapter that turned out to hold
    two ideas gets a half-line naming both in "The chapters", and two chapters that turned
    out to be one topic get named together there. A reader who is told a chapter covers two
    things can follow it; one who is not told wonders why it does not cohere.

Then put them back:

    bin/tour-splice.py --root <checkout> <patch> <narration> <narration>.ch2 <narration>.ch5 …

It matches each file on its chapter *title*, so a fork cannot land its work on the wrong
chapter and the order you pass them in does not matter. It validates every file before it
places any, and refuses one that dropped a label — so a fork's format error stops here
rather than surfacing at your build, in prose you never read.

**Then check coverage again.** A splice replaces a chapter's directives with whatever the
fork wrote, so the coverage Step F proved is not proof any more: a fork that dropped a block
while rewriting its beats has silently unshown those lines. `bin/tour-rest.py <patch>
<narration>` answers in one call, and it is the only moment where the fix is still cheap.

**Then, and only then, act on any misfit a fork reported.** Once every fork has returned, the
freeze that stopped them moving blocks has nothing left to protect — no sibling is reading
the skeleton any more, coverage is chapter-agnostic, and a label travels with its block, so
every `[[…]]` still resolves. Move the block, fix the two chapters' prose around it, and
rebuild. The freeze exists for the window where chapters are written concurrently; this is
after that window, and it is the cheapest moment the correction will ever be. Do not concatenate the files by hand:
they are the middle of a document, not the whole of one, and a missing `%report` or `%intro`
is only a warning — so a botched merge would build, and quietly. The command also names any
chapter still un-narrated, which is how a fork that failed becomes visible now rather than as
a wall of "no prose" on the next build.

**What forking costs:** each fork re-prefills your context, so N forks buy one pass of the
deep work in exchange for roughly N times the input. Now that the deep work is the expensive
half, that trade is worth making almost whenever it is available — but it is also why the
count is packed rather than one-per-chapter: the prefill is per *fork*, not per chapter.

**What it gives up:** no chapter can see what another chapter *wrote*, only what the skeleton
says it contains. Two chapters can explain the same thing twice and nothing will catch it.
The captions in the skeleton are what keep that rare, which is another reason they are worth
writing properly.

**When one thing is load-bearing across many chapters, state it yourself first.** Some
changes turn on a single mechanism — one access check, one resolver, one policy — that five
or six chapters all depend on. Left alone, every fork re-derives it, and the reader meets the
same explanation six times in six wordings. **That is not a reason to narrate serially**; it
is a reason to spend two sentences before forking:

- **Put the mechanism in the overview**, in the chapter you write yourself, as the thing the
  chapters have in common.
- **Tell every fork it exists, in one line, with the label of the block that introduces it**:
  "the access check is `[[h12]]`; assume the reader has met it, reference it, do not re-derive
  it." A fork cannot see its siblings, but you can tell it what they will assume.

That costs a line per fork and buys the through-line a serial pass would have given you.

A cluster spanning many files leads with the blocks that carry the idea.

Where a hunk deserves a specific thing for the reader to check, say it as a question they can
answer by looking, at a named location — not "this may have implications".

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
makes a scroll-past an informed decision.

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
    Up to 3 ranked pointers at where risk concentrates, each naming the chapter
    it lives in. These are attention pointers, not verified bugs.

    %beat The chapters
    One half-line per chapter, saying what it is about. The sidebar gives their
    names; this gives their purpose, which is how a reader decides what to read.

**Rank those pointers by `%blast` and then by evidence.** Each came from a fork that saw
one chapter; you have seen none of them at depth, so you cannot compare their severity by
reading them. What you do hold is every chapter's blast level — the one judgement made on
comparable terms across the whole tour — so a `wide` chapter's pointer outranks a `narrow`
one's, and within a level the pointer whose fork brought back a call site or a failing case
outranks the one that brought back a feeling.

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
  changes you could not explain, the ones that looked wrong, the claims you took from a
  commit message or a comment rather than from code, and whether you ran the tests. Each
  with its label, so the reader can go back to it.
  Do **not** list what you did verify. A roster of successful checks reads as a
  certificate, and manufacturing that reassurance is the thing this section exists to
  prevent.
- **Open questions** for the author, if any.
- **Suggested next step** — usually a dedicated correctness pass over the same diff
  (`/code-review` in Claude Code), or a specific file worth reading in full.

**Before citing a label anywhere in these two chapters, read that label's caption in the
skeleton table.** A label reference is guaranteed to *resolve*, never to *aim* — nothing
mechanical can tell that `[[h29]]` points at the export list when the explanation is in
`[[h28]]`. The table makes that a one-glance check, and these two chapters are where
misfired citations do the most damage, because they are where a reader decides what to
read.

**Re-run the skeleton command to get a current table**, with the checkout Step B printed:

    bin/tour-skeleton.py <patch> <narration> --root <checkout>

The Step F table is stale by now: blocks moved between chapters after the splice, so the
codes have shifted, and a fork may have corrected a caption. Re-running is safe at any time —
it only ever *adds* labels, never changes or removes one — and this is also where the blocks
a fork added without labels get named. **`--root` is not optional here**: without it the
command reads `%quote` from the current directory, and on a worktree tour a quote that is
correct will be reported as out of range.

## Step J: Hand it over

**Build it one last time with `--final`:**

    bin/tour-build.py <patch> <narration> <out.html> --root <checkout> --final

**A report with an unshown line, a pending item or a single warning is not finished.** An
ordinary build exits 0 in that state on purpose, because most builds happen while later
chapters are still skeletons — so this last one is the build that refuses. **A note is not a
warning**: a note is a check that cannot tell right from wrong (a deliberate re-show looks
exactly like an off-by-one), so it is printed and never refuses. Read the notes; they are
not a gate. It writes the
file, says on stderr what is wrong, prints **nothing on stdout**, and exits 1. Exit 0 with a
path on stdout is the only signal that the report is whole; the path in a refusal message is
there so you can open the file, not so you can hand it over. Fix, rebuild, and only then say
three things and stop:

- **What the page has**, in a clause: chapters in the sidebar, a viewed mark on every change.
- **Invite questions.** They can ask about anything they have just read, and **every change
  carries a number like `3.2`** they can quote to point at one. The report is a file and
  cannot contain this invitation; it is the only interactive surface the conversation has,
  and a reader holding a path has no other signal that you are still here.
- **The directory holding all three files**, in one clause before the path. `tour.patch`
  and `tour.tour` are the tour's source; without them a report that looks wrong can only be
  regenerated, not examined.
- **The path**, on its own line, last, with nothing after it.

If Step B created a worktree, say so in one clause and give the `git worktree remove` line
it printed. It is additive and harmless, but it is yours, not theirs, and they cannot remove
what they were never told about.

## Troubleshooting

**Diff is mostly formatting** — Detect with `git diff -w`, but tour the *full* patch:
coverage counts what it was given, so touring the `-w` diff would leave the formatting
changes unaccounted for. Cluster the substantive hunks and give the churn one leftover
group.

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
