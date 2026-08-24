---
name: diff-tour
description: Writes one long report that walks a reader through a code change, chapter by chapter, with the real diff hunks interwoven with the narration that explains them — so a human can review a diff they did not write. Starts with an overview of the change and its new behaviors, then a chapter per cluster of related hunks, then the leftovers, then what to check yourself. Renders as markdown here, or as a colour terminal file, or as a self-contained HTML page. Use this whenever the user wants to be *walked through*, *toured*, *guided through*, or *led through* a diff, PR, branch, or commit — phrases like "walk me through these changes", "show me the diff with explanations", "explain this PR hunk by hunk", "review this change with me", "tour this branch", "show me the actual code as you explain it" — and also whenever a user asking to "explain a diff" wants to see the code itself rather than a prose summary. Prefer this over a summary-only explainer any time the user says "show me" about a change.
metadata:
  version: 1.1.0
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

1. **Real hunks, verbatim.** Every chapter shows actual diff lines from the extractor,
   never retyped. Paraphrased code destroys the whole value of the tour.
2. **Narration and hunks interwoven.** A hunk sits next to the prose about it, always. A
   report that puts all the explanation in one place and all the code in another makes the
   reader do the correlating, which is the work the tour exists to do for them.

## Clusters and chapters

Two numbering schemes, deliberately different so they can never be confused:

- **Steps A–I are lettered.** They are this skill's procedure — what you do, in
  order. The reader never sees them.
- **Chapters are numbered.** A chapter is a numbered heading in the report — nothing more.
  The number exists so hunks can be coded `<chapter>.<hunk>`: `3.2` is the second hunk of
  chapter 3, and that is how prose points at code. Write a chapter heading as
`<n>/<total> · <name>`, in every format: the builder for `ansi` reads the number from it,
and a reader wants to know how much is left.

A **hunk cluster** is a set of thematically cohesive hunks — the unit Step E
produces. A **chapter** is a unit of the report. Most chapters carry one cluster;
three do not:

| Step | Produces |
|---|---|
| A | nothing — prints usage and stops |
| B | one short note: the format, the alternatives, and that this will take a few minutes |
| C, D, E | nothing — acquire, understand, cluster |
| F | chapter 1, the overview |
| G | one chapter per cluster, chapters 2…n |
| H | the Leftovers chapter |
| I | the wrap-up chapter |

So a tour of five clusters is eight chapters. **The 3–7 budget in Step E counts
clusters, not chapters.**

## Rulesets

The procedure below is thin on purpose; the substance is here.

## Fidelity

What must be true of every hunk you show. These are mechanics, not judgement — variation
here is breakage.

- **Never retype code.** Hunks come from `scripts/tour-set.sh`, which pulls them byte-exact
  from the diff. If a line is too long, let it wrap; don't shorten it.
- **Never fabricate a hunk** to illustrate a point. If the diff doesn't contain it, it
  doesn't get shown.
- **Never hide an added or changed line.** Not for a new file, not for forty peer
  definitions, not because a chapter is long — see [Nothing is hidden](#nothing-is-hidden).
  `markdown` prints long hunks whole; a file scrolls.
- **Keep the `@@` headers.** Every format takes hunks from the extractor, so the ranges stay
  byte-exact and the enclosing-scope text is replaced by the hunk code and caption. That
  trade is deliberate: git's context text for a file like an IIFE module is the same
  useless line on every hunk, while the code is what the narration points at.
- **Every hunk appears in exactly one chapter**, except the multi-intent hunk described
  under [Clustering](#clustering).
- **Separate stated from inferred intent.** "The PR says…" versus "This looks like…".
- **Suspicions are suspicions.** Say "worth checking whether…", never "this is a bug",
  unless you read the surrounding code and can explain it concretely.
- **Never certify.** You read the diff; you did not verify it. Don't offer a verdict on the
  change as a whole.

**The completeness guarantee** is the ledger `tour-set.sh` keeps — see [Step H](#step-h-the-leftovers-chapter).

### Nothing is hidden

**Every added or changed line appears somewhere in the tour. No exceptions.** Not for a
new file, not for a hunk that adds forty peer definitions, not for a rewritten file, not
because a chapter is getting long. A reader cannot be responsible for code they were never
shown.

**Never show one hunk as a representative of several.** That hides precisely the case the
tour exists to catch: the seventh call site that differs.

Length is managed by structure, never by hiding: chapters divide the report, the reader
scrolls, and a dull chapter is cheap to scroll past. What you may compress is the *narration* —
one caption for twenty similar hunks is fine, because the reader can see the twenty hunks
it describes. A topic's own hunks stay in that topic's chapter however dull they are;
Leftovers is only for hunks no topic claimed.

A reader who scrolls past a chapter has decided. Don't remark on it.

Context lines need no management either. `git diff` splits a hunk whenever the gap between
changes exceeds twice the context setting, so the longest run of unchanged lines any hunk
can hold is 6 at the default `-U3`. There is nothing to trim. The only surviving use of `…`
is joining two adjacent hunks merged into one block, below.

### Splitting and grouping hunks

- **One `diff` block per idea.** If a single `git diff` hunk contains two unrelated changes, split it into two blocks with a line of framing each, keeping each block's lines verbatim. Repeating the `@@` header on both is fine.
- **Merge adjacent hunks** from the same file when they're the same idea and close together, using `…` between them.
- **Repetitive hunks** — the identical mechanical change in eight call sites — all get shown, in the same chapter as the one you explained, never deferred to Leftovers. Explain the pattern once against the first block and let the rest follow with a one-line caption each.
- **Order within a cluster** follows the explanation, not the filesystem. Lead with the hunk that carries the idea, then the ones that follow from it. `tour-set.sh` emits hunks in the order you list them and numbers them in that order, so narration order, screen order and hunk codes are the same thing — never tell the reader to start at the bottom of their screen. Only `all` and `rest` fall back to file order, since neither states one.

### Special cases

**Pure renames** — `git diff` shows these as `rename from` / `rename to` with no body. Report them as a line of prose, not a `diff` block. If the rename came with edits, show only the edits.

**Moved code** — a block deleted in one file and added in another shows up as a large `-` run and a large `+` run, which reads as a rewrite. Run `git diff --color-moved=zebra` (or diff the two regions) to confirm it's a move. If it is, say so in the narration and lead with whatever genuinely changed during the move. The added side still gets shown in full — it is code the reader has not reviewed — but one sentence saying "identical to the block removed above, except the two lines called out" saves them from reading it twice.

**Whitespace-only or reformatting churn** — compare against `git diff -w`. Set formatting-only hunks aside, note the line count, and tour the substantive diff.

**New files** — show the whole file. It is all new code, and none of it has been reviewed before. Say how long it is, and lead the narration with its shape — exported names, entry points — so the reader knows what they are scrolling through.

**Deleted files** — show the signatures or behavior being removed, not the full body. The question the reader needs answered is what capability disappeared and who used it.

**Binary files** — never show a diff, in any format. Name the file and what happened to it:
added, changed, deleted or moved. That is the whole of what a reviewer can act on, and a diff
of bytes is noise at best. The builder does this for you: select the change as
`<path>:bin` and it renders one line — `4.3 · assets/logo.png · changed (binary)` — deriving
the kind from the diff, so it cannot be stated wrongly. `tour-hunks.sh` lists binary changes
with `bin` where a line number would be, and they count towards coverage like any other
change: a report that ignores a replaced image is not complete. A binary needs no framing
sentence of its own, so one sentence can introduce a list of them.

**Lockfiles and generated code** — one line each, no blocks.

**Very large single hunks** (rewritten file) — split by function or logical section into sub-steps within the chapter, each with its own block and explanation. Splitting is presentation; every line still appears.

## Clustering

### What a good cluster looks like

A cluster is a **unit of intent**, not a file. Hunks from four files belong in one cluster if they exist for the same reason; two hunks in one file belong in different clusters if they don't.

**Its name describes a change**: "thread the tenant id into the cache key", "make the retry budget configurable", "backfill script for existing rows". Not a location: "changes to cache.py", "misc".

**Its length follows its cohesion.** Never split a cluster to make it shorter. If a change can only be explained through twelve interconnected hunks, that is one chapter of twelve hunks — two chapters of six that each depend on the other are strictly worse, because neither can be understood where it sits. When a cluster is genuinely long, say at the top how many hunks it holds and lead with the ones carrying the idea.

**Many hunks share a cluster, and almost every hunk has exactly one home.** A cluster of one hunk is possible but usually means the clustering is too fine.

The exception is the **multi-topic hunk**, and it is not rare: `git diff` merges changes that sit within a few context lines of each other, so one hunk routinely carries several unrelated additions. Two rounds of work overwriting the same lines does it too. Either way the hunk serves more than one topic, and it may appear in more than one chapter.

The rule for the second and third chapter: **never discuss code the reader has no way to reach, and choose reaching over repeating by size.**

- **A short hunk you re-show.** Under roughly twenty lines it is cheaper to print again than to send the reader hunting, and the hunk sitting under its own framing sentence is worth the duplication. Say which chapter owns it, and **name the lines this chapter is about**. **A re-shown hunk keeps its own code** — the one its owning chapter gave it — because a hunk has exactly one code in the whole report and a second code would make one place look like two. Its caption may differ, since this chapter is looking at it for a different reason. In `tour-set.sh`, pin it: `src/form.js:233@2.3=the guard, from the other side`.
- **A long hunk you cross-reference.** Above that, printing sixty lines three times inflates the report and buries the difference between the three readings. Point at it by code — "the guard is in `2.3`, the `assertFieldsInSameLayer` lines" — and quote the two or three lines this chapter turns on, so the reader has the code in front of them and knows where the rest lives.

The cross-reference works because the report is one document the reader can scroll. It is the whole hunk they cannot afford to meet three times, not the code.

**It is understandable from its predecessors alone.** The reader should never need a later chapter to follow an earlier one. If chapter 4 only makes sense after chapter 6, reorder.

**It is as separate as the diff permits, and no more.** You are reverse-engineering a history from a net result, not writing one: you see only the final state of every line. Where a location was rewritten in several rounds, the surviving hunk carries all of them at once and no clustering can separate it. Perfect separation is not available, and claiming it is a fabrication.

**What a cluster is never:** backend versus frontend. Tests versus code. By file type. By directory. Every one of those cuts across intent and produces chapters that can only be understood by reading a different chapter. **Tests belong with the behavior they pin down** — a spec asserting a new selector goes in the selector cluster. A layer split (schema → API → UI) is a last resort for a change that genuinely is one traversal of the stack, never a default.

### How to find them

Assume the diff is ugly. The commits may be checkpoints, merges and afterthoughts; the file order is alphabetical; the same lines may have been overwritten three times. **Cluster the whole diff as if you were writing the best possible commit history for it** — and derive that history from the diff's content, not from the commits that happen to be in it.

Three passes. Do not skip to assignment: grouping hunks by resemblance is what produces the location-based clusters above, because resemblance correlates with location.

**Pass 1 — extract topics, ignoring hunks.** Read the diff as a whole and name the ideas it contains: the behavior changes, the refactorings, the cleanups. Write them down as ideas, before deciding where any single hunk goes.

One useful test: **does this change observable behavior?** Behavior-preserving work and behavior-changing work are different topics even when they touch the same lines — it is what separates "the refactoring that made room" from "the change it made room for". Unlike "is this preparatory?", you can answer it from the diff. It will not always separate much — on a branch where nearly everything is a behavior change, what actually draws the boundaries is which functions and call sites a hunk owns.

Commit messages, PR descriptions and changelog entries are **hypotheses to test against the hunks, never the topic list itself**. Deriving topics from commit subjects smuggles back in the boundaries you were told not to trust.

Expect a range to hold several bodies of work, each with its own rounds of preparation, refactoring and cleanup. Within one body, `preparation → behavior change → cleanup` is a good ordering and a good hint at where a boundary falls. Across bodies it means nothing — don't force one arc onto a range that has three.

**Pass 2 — assign every hunk to the topic it exists for.** The test is counterfactual: **if this topic were reverted, would this hunk disappear from the diff?** Not "would my explanation mention it" — a topic's prose can be complete while a dozen hunks still exist only because of it, and judging by the prose sends all twelve to Leftovers.

- **A topic's chapter carries every hunk that belongs to it**, including the repetitive and inconsequential ones. Never move a topic's own follow-ups to Leftovers: by the time the reader reaches the end they have lost the context that made those hunks legible, and a hunk shown without its topic is worse than useless. Narrate the first one properly, then say the rest follow the same shape and show their diffs after it.
- **Tests and documentation go with the behavior they pin down or describe.** Six specs for one new behavior all belong to that topic, even though the explanation would read fine having quoted only one of them.
- A hunk several topics claim goes to the one whose explanation would suffer most without it — that is its primary home, and this is where the incompleteness question earns its keep, as a tiebreaker. In the other chapters, re-show it or cross-reference it by size, under the rule above.
- **A hunk that summarises the whole change** — a changelog entry, release notes — is claimed by every topic, because reverting any of them would shrink it. It belongs to the topic that *documents* the change if the diff has one, and is otherwise its own small cluster. Place it early either way and read it as stated intent: it is usually the best account of the author's own understanding in the whole diff.
- A hunk no topic claims is a **leftover** — no idea in the change would lose it if reverted.
- A hunk with no good home may instead be **evidence of a topic you missed**. Check that first. Adding a topic is cheap; misfiling real work as fallout is not.

**Pass 3 — settle.** Merge two topics whose hunks turn out to depend on each other in both directions; mutual dependency means one cluster, while a one-directional dependency is only an ordering constraint. Split a topic whose hunks serve two ideas. Pull a new abstraction and its first consumer together unless the abstraction stands alone.

Then count. **3–7 clusters** is the healthy range, but treat it as a smell check rather than a budget to hit. If the count is far outside it, in this order:

1. **Check whether the range holds more than one unrelated body of work.** Two bodies of six clusters each look like twelve clusters and are not. Say so in the overview, tour the one the reader asked about, and offer the other as its own tour. Both bodies still get Leftovers groups, so coverage stays honest.
2. **Otherwise re-run pass 1.** Too many usually means one topic was found repeatedly under different names; too few usually means the change is smaller than its line count suggests. The defect is in the topic list, not in the boundaries — never redraw a boundary by hand to hit a number.

A range full of leftovers means the same thing: too few topics, or a second body of work you have not named.

## Narration

The prose under a hunk is the only thing the reader cannot get from the diff itself. That
is the whole test for whether a sentence belongs: **could they have read it off the hunk?**
If yes, cut it. A paragraph that restates the diff does more than waste words — it teaches
the reader that your prose is skippable, and they will skip the one that mattered. **A
hunk's own added comments are part of the hunk**, so the test applies to them too: a
well-commented change may deserve less prose than a bare surprising one.

So a mechanical walk ("here we call `foo` with the new argument") is never the job. What
the diff cannot supply is: what the code *meant* before, why this route and not another,
what breaks elsewhere, what invariant appeared or vanished, and what the hunk is *for*.

**Quote code when a sentence needs it**, whether it is in the diff or not — a few lines of
the function a hunk sits in, or the two lines of a hunk another chapter owns. Use a fenced
block with the file path in its info string and it renders like the rest of the report; see
[references/rendering.md](references/rendering.md). Never paste code into a paragraph.

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
that could have been there, and that is what invites a rubber stamp. Naming one real
alternative breaks the spell: *the author chose X; Y was also available, and would have
traded A for B.* No comparative adjective, no recommendation, no verdict — the reader
judges. The bar is that you can **name it, price it, and point at where it already lives**.
Pricing alone is not a guard: a fluent alternative that never existed prices just as
convincingly as a real one. So it has to be something you *saw* — the code this diff
removed (the diff hands you that one for free; the removed lines are literally the road
not taken), a pattern used elsewhere in this codebase, or a route a comment or commit
names. If you cannot point at where it lives, don't offer it.

"This could be one selector instead of four, at the cost of also matching disabled
controls" earns its place. "A cleaner approach may exist" is the shape of a thought
without the content, and is worse than silence.

**Most hunks have no alternative worth naming, and a chapter with none is normal.** A
forced contingency is boilerplate, and boilerplate is what kills this rule first.

**Admit what you do not understand, in the chapter, where the hunk is.** This is the most
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

### Captions

A hunk's caption sits in its header, next to the file path, and is the one line a reader
scanning the report will always read. So it says what *this hunk* does — the chapter heading
is right above it, and restating that wastes the line. `3.1 · the four readers and writers`,
not `3.1 · one accessor per field question`.

A caption that could sit under any hunk in any order is doing nothing. Hunks appear and are
numbered in the order you list them, so what you narrate first is what the reader sees first;
never ask them to start at the bottom.

**A one-sentence frame ends with a colon.** It is introducing what follows, so punctuate it
that way: "The guard walks `form.elements` and nothing else:" — not a full stop, which reads
as a closed thought and leaves the hunk looking unannounced. A frame of two or more sentences
ends normally; by then the paragraph has established itself and the colon would be fussy.
The builder checks the single-sentence case.

**A caption is not framing, and neither is a heading.** Both are things the reader meets
*at* the hunk or above the whole chapter; neither tells them why this hunk is coming. The
framing is prose, in this chapter, above this hunk.

**Every hunk is framed before the reader meets it.** A hunk never opens a chapter and never
sits straight under a heading — there is always a sentence above it saying what it is for.
A heading does not count: `ONE ACCESSOR PER FIELD QUESTION` names the chapter, not this
hunk's purpose. One sentence is enough, and "this is the same swap in the disable path" is
a whole sentence. A reader who meets code before they are told why is reverse-engineering
your intent from a diff, which is the work the tour exists to save them.
This holds in every format. `ansi` is simply the one that can check it —
`tour-report.sh` refuses to build a report where a hunk has no prose above it.

**Prose after a hunk is about that hunk.** That is the default the reader can rely on, and it means a
paragraph sitting between two hunks needs no preamble to be understood: it looks backwards.
When you do want to set up the hunk below instead, **name it by its code** — "`3.4` then
threads the same value through the validator" — so the direction is never something the
reader has to infer from tone. Unnamed prose looks back; prose naming a code looks at that
code.


**Gloss a term once, at first use, in a clause.** Where a project's own concept is
unavoidable, define it in passing and move on. If the tour needs a glossary, the narration
is failing.

## Formats

The report is one document, written once as a narration file and rendered by
`scripts/tour-report.sh`. `--format` chooses the rendering and nothing else. The mechanics
are in [references/rendering.md](references/rendering.md).

**`markdown`** *(default)* — prose and fenced diff blocks. Nothing to install, readable by a
human or another agent, diffable, easy to paste anywhere.

**`ansi`** — a terminal file with real syntax highlighting and a heading hierarchy markdown
cannot express, read with `less -R`.

**`html`** — the same as a self-contained page for a browser.

**A format changes rendering, never content.** The same clusters, the same hunks in the same
order, the same framing sentence above each one, the same admissions. Every rule in
[Narration](#narration) and [Fidelity](#fidelity) applies to all three, and one builder
enforces the same checks for all three.

**You never emit diff bytes.** Write narration with `%%hunk` placeholders and let the builder
splice the hunks. That is what keeps them byte-exact without trusting a copy-paste, and it is
most of the cost of a large report: typing out a hundred-hunk diff is tens of thousands of
output tokens spent on bytes you are not thinking about.

### Choosing the format

**`markdown` is the default.** Use it unless the reader asked for something else with
`--format markdown|ansi|html`. Don't ask: the default works everywhere and the flag is there
for the reader who wants more. Every format writes a file; `markdown` also prints itself into
the session when it is small enough to arrive whole, and prints its path when it is not.

**After the report, invite questions.** This is session output, not part of the report — for
`ansi` and `html` the report is a file and cannot contain it. Say that they can ask about
anything they have just read, and that **every hunk carries a code like `3.2`** they can
quote to point at one. It is the only interactive surface the report has, and a reader
holding a file has no other signal that the conversation is still open.

For `ansi` and `html`, print the command to open the file on its own line, last, with
nothing after it.

### Hunk codes

Every hunk carries exactly one code, however many chapters show it, so prose and screen can point at
each other. The code is `<chapter>.<hunk>`: `2.1`, `2.2`, `2.3` for the first
chapter's hunks, numbered in the order they appear on screen. No total count in
the code; the chapter header already carries "2/7".

Use them in prose the way you would a figure number: "the `??` in `2.1` is doing
precise work", "`2.3` is the guard on the whole approach". A reader who has
scrolled away can find the hunk again, and a reader reading only your prose still
knows how many hunks the chapter had.

## Procedure

**A chapter's contents are specified in exactly one place: its step.** Anything else that
mentions a chapter refers to it by name and number and never restates what is in it. Three
copies of the wrap-up's contents once drifted into three different answers; this is the
rule that prevents the next one.

## Step A: Help

If the arguments are exactly `help`, `--help`, `-h`, or `?`, print this block verbatim and stop — don't gather a diff.

```
diff-tour — a guided, cluster-by-cluster walkthrough of a code change

Usage: /diff-tour [target] [flags]

Target (optional, defaults to your working diff):
  <empty>       Branch diff vs its branch point, plus uncommitted changes
  <git range>   e.g. main..HEAD, abc123..def456
  <commit>      e.g. HEAD~1, or a commit SHA
  <branch>      compared against the repo's default branch
  <number>      a PR or MR in this repo
  <PR/MR URL>   a GitHub pull request or GitLab merge request
  <patch file>  a .patch or .diff you already have

Format (how the report is rendered; the content is identical):
  --format markdown   (default) printed here, fenced diff blocks
  --format ansi       a terminal file with colour, read with less -R
  --format html       a self-contained page for a browser

```

## Step B: Settle the format, and say so

`markdown` unless the reader passed `--format`. See [Formats](#formats). Decide now: it
determines which reference file you will need, and it is the one thing worth telling the
reader before you go quiet.

**Then say three things, in two or three lines, before doing any of the slow work:**

- **Which format you are using**, and that it was the default if it was.
- **What else they could have asked for**, in a clause each — the other two formats and the
  flag that selects them. A reader who does not know `ansi` exists will never ask for it.
- **That this will take a few minutes.** Reading the diff, tracing callers and clustering all
  happen before a single word of the report appears. Without this the reader is watching an
  idle session and wondering whether it is stuck.

Then work. Don't narrate the intermediate steps — there is nothing useful to report between
here and the first chapter, and progress chatter is worse than silence you were warned about.

## Step C: Acquire the diff

**`scripts/tour-fetch.sh <out-file> [<target>]` resolves any target to a patch file.** It
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

Two traps it avoids, which matter if you ever bypass it: the no-target base is the branch
point, never `@{upstream}` (on a pushed branch that covers only unpushed commits); and a
branch target needs three dots, or you diff the working tree against it.

**Everything downstream reads the patch file, never the target.** `tour-hunks.sh` and
`tour-set.sh` both take it as their `<source>`, which is what makes a tour immune to the
branch moving under it: a range is re-resolved on every call, so a commit landing
mid-tour shifts every hunk's start line and invalidates both the selectors and the
coverage ledger.

For every target, read the commit log over the range. It is the cheapest signal you will
get for intent, and for whether the range holds more than one body of work. It is not a
signal for where the cluster boundaries are — see Step E. Skip merge commits when reading
intent.

Note but exclude from the narrative: lockfiles, generated code, vendored directories, and
pure-formatting churn. Excluded means not narrated, never hidden — those hunks still
appear in the Leftovers chapter under one caption naming what they are. Say what was
excluded and how many lines.

If the diff is empty, report exactly what was compared and stop. Don't invent a tour.

## Step D: Understand before writing

The tour is only as good as this step, and it happens before any output.

1. **Read every hunk, then the enclosing function or class for each.** Behavior usually lives in the unchanged lines around a change — a two-line diff inside a retry loop means something different than the same two lines in a constructor.
2. **Read stated intent**: commit messages, PR description, linked issues if cheap. Keep stated intent separate from inferred intent when writing.
3. **Trace outward**: grep callers of changed symbols, find the tests covering this area, check config or schema the change depends on. **When a change replaces an idiom, also grep for surviving uses of the old one** — greping the new symbol finds adopters, not stragglers, and a missed call site is the likeliest bug class in a migration. Report the count in the cluster that introduced the replacement; the reader cannot get it from the diff. This is what lets a cluster explanation say "and that's why the three call sites in `billing/` needed updating" instead of just describing lines.
4. **Establish before-and-after behavior.** For each meaningful change, know what the code did before and what it does now. That contrast is the substance of every cluster explanation.

**Build one caller index, and share it across every chapter.** Grep the symbols this change
adds or alters *at a module boundary* — exports, public API, anything another file can name
— whole-word, and keep the `file:line` hits. It is small, it is reusable, and it is what
lets a chapter say "three callers, all in `billing/`, and this diff changes two of them"
instead of describing lines.

**Scope it to the boundary.** Indexing every identifier the diff declares, locals included,
returns more text than reading the whole repository — measured on one 52-file change:
13 boundary symbols gave 30 call sites; all 118 declarations gave 20,515 hits. A local
`const` has no callers to find, and grepping it drowns the index.

**Don't read whole files for context.** The enclosing function or class of a hunk is already
in git's `@@` header, once per hunk, free. Reading the file to rediscover what the diff told
you is where unbounded cost comes from.

**Don't read at depth what is going to Leftovers.** A second body of work, or churn in a
subsystem the report is not about, needs *identifying*, not comprehending — it ends up as one
`rest` group with one caption. `tour-hunks.sh` lists those hunks in milliseconds; reading
their diffs costs thousands of input tokens to produce about ten words. Read the body you are
touring at depth, and the rest by path only.

**Delegate only when the reading is genuinely large.** If answering a cluster's questions
needs substantially more code than the cluster contains, and several clusters need that
independently, hand those reads to subagents and keep the judgement. Otherwise don't: a
subagent costs more wall clock than the greps it would run. When you do delegate, a
positive finding may be summarized, but **a claim that something does not exist must come
back as the command and its output** — that is the claim a reviewer will lean on.

## Step E: Cluster the hunks

Extract topics, assign every hunk, settle. The rules are in
[Clustering](#clustering) — read them there rather than working from memory, because this
step decides how good the tour can possibly be.

## Step F: Print the overview chapter

Before touring, give the reader everything the later chapters will assume. Length
follows content: enough to make the detail land, and no padding. Don't pad it out
to look thorough, and don't cut orientation to hit a length.

```
# <one-line title of the change>

## 1/<total> · Overview

### What it does

2–4 sentences: the problem and the approach taken.

### New behavior

Bullets, only things observably different for a user, caller, API
consumer, or the data. "None — internal refactor" is a valid and
useful answer.

### Scope

N files, +X/−Y lines, in M clusters across <M+3> chapters. Note
anything excluded (lockfiles, generated code). If a whole subsystem
sits only in Leftovers, say which half of the branch the report
actually covers.

### Where to be careful

Up to 3 ranked pointers at where risk concentrates, each naming the
cluster it lives in. These are attention pointers, not verified bugs.

### The chapters

2. <cluster name> — <half-line> · `path/one.py`, `path/two.py`
3. <cluster name> — <half-line> · `path/three.py`
4. Leftovers — <N hunks, and in a half-line what they are>
5. Wrap-up — what to check yourself, and open questions


```

Then carry straight on into the chapters. There are no pauses; the reader gets the whole
report.

## Step G: One chapter per cluster

Write each cluster as a numbered chapter, in order. Open with the chapter heading, **then
the chapter's premise in a sentence or two — what this cluster is about — before any hunk.**
After that, narrate and show hunks interwoven: framing sentence, hunk, explanation, next
framing sentence. A chapter never goes heading straight to hunk, which is the most common
way this comes out wrong, because the heading feels like it has already said the thing. Every hunk comes from `scripts/tour-set.sh` and is never retyped — push the
chapter through it — always with the same `<tour-file>`, since the ledger lives beside it —
and take the hunks from the file it writes. **Every chapter goes through
the script**, with `TOUR_NEW=1` on the first, because its ledger is the only thing that makes
Step H's completeness check mean anything.

Several small blocks with a framing line each read far better than one giant block, and a
cluster spanning many files leads with the hunks that carry the idea.

**Structure a long chapter with `###` subheadings.** Past three or four hunks, an unbroken
run of prose and diffs gives the reader nowhere to stand and nothing to scroll back to. Each
subheading names the sub-idea the next few hunks share — "why absence and not falseness",
"the one call site that opts out" — and a reader skimming the report gets a second layer of
outline for free. A three-hunk chapter usually needs none; a twelve-hunk chapter always does.
Use bold text for emphasis inside a paragraph, never as a substitute for a heading: bold does
not structure anything.

How much to say, where to say nothing, what to admit, when to name an alternative — all of
that is [Narration](#narration). There is no template, because a chapter about a one-line
guard and a chapter about a rewritten module have nothing in common but the ordering above.

Where a hunk deserves a specific thing for the reader to check, say it as a question they can
answer by looking, at a named location — not "this may have implications".

## Step H: The Leftovers chapter

**Leftovers are the hunks pass 2 assigned to no topic** — not the boring ones, and never a
topic's own follow-ups. What lands here is the genuinely unaffiliated: a `.gitignore` line, an editor config, a dependency
bump, churn in a subsystem the tour is not about, or a second body of work you named in
the overview and are not touring.

Group them by file, and **give each group one line saying what it is and why no topic
claimed it.** That is what makes a scroll-past an informed decision. It is also the check
on the classification: if you cannot say why a group belongs to no topic, it probably
belongs to one — go back to pass 2.

`tour-set.sh` takes the captions as `rest:<path>=<caption>` and warns about any group you
left bare. Each call reports how many hunks remain, which is how you know what this
chapter will hold. That count is for you, not a score to report to the reader.

**Run the completeness check before you write the wrap-up.** In every format, call
`tour-set.sh` with the `rest` spec once. It selects every hunk no earlier chapter used,
and if there are none it prints `all hunks already shown` and exits 0. That is the only
mechanical guarantee the tour has that nothing was dropped — do not print the wrap-up
chapter without it.

If `rest` returns more than a handful, treat it as a finding rather than a chapter: too
many topics went unnamed, or the range holds a second body of work. Say which.

## Step I: The wrap-up chapter

- **Recap** the change as a chain: cluster 1 enabled cluster 2 enabled cluster 3. Three or
  four sentences; the reader should be able to retell the change from this. A causal chain
  is inference by construction, so say so — most of it is your reading, not the code's.
- **What you still need to check yourself.** Collect the admissions you made in the
  chapters: the hunks you could not explain, the ones that looked wrong, the claims you
  took from a commit message or a comment rather than from code, and whether you ran the
  tests. Each with the hunk code, so the reader can go back to it.
  Do **not** list what you did verify. A roster of successful checks reads as a
  certificate, and manufacturing that reassurance is the thing this section exists to
  prevent.
- **Open questions** for the author, if any.
- **Suggested next step** — usually a dedicated correctness pass over the same diff
  (`/code-review` in Claude Code), or a specific file worth reading in full.

## Troubleshooting

**Diff is mostly formatting** — Detect with `git diff -w`, but tour the *full* patch: the ledger counts what it was given, so touring the `-w` diff would leave the formatting hunks unaccounted for and invisible to `rest`. Cluster the substantive hunks and give the formatting churn one `rest` group.

**`gh` fails** — Say so, suggest `gh auth login`, and offer to tour a local range instead.

**Reader interrupts with a question while the report is streaming** — answer it, then continue where you stopped. Never restart from the top unasked.
