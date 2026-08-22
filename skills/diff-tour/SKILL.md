---
name: diff-tour
description: Walks a reader through a code change cluster by cluster, showing the real diff hunks with +/- markers inline and explaining each cluster before moving to the next, pausing for the reader between clusters. Starts with an overview of the change and the new behaviors, then tours the clusters. Use this whenever the user wants to be *walked through*, *toured*, *guided through*, or *led through* a diff, PR, branch, or commit — phrases like "walk me through these changes", "show me the diff with explanations", "explain this PR hunk by hunk", "review this change with me", "tour this branch", "show me the actual code as you explain it" — and also whenever a user asking to "explain a diff" wants to see the code itself rather than a prose summary. Prefer this over a summary-only explainer any time the user says "show me" about a change.
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
2. **One chapter at a time.** Stop and let the reader say `next`. A tour that dumps
   everything at once is a long document, and the reader loses the thread by chapter three.

## Clusters and chapters

Two numbering schemes, deliberately different so they can never be confused:

- **Steps A–I are lettered.** They are this skill's procedure — what you do, in
  order. The reader never sees them.
- **Chapters are numbered.** They are what the reader navigates with `next` and
  `go <n>`. Hunk codes are `<chapter>.<hunk>`, so `3.2` is the second hunk of
  chapter 3.

A **hunk cluster** is a set of thematically cohesive hunks — the unit Step E
produces. A **chapter** is a unit of navigation. Most chapters carry one cluster;
three do not:

| Step | Produces |
|---|---|
| A | nothing — prints usage and stops |
| B | nothing — settles the presentation mode, before any slow work |
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
  definitions, not because a chapter is long. Length is managed by navigation, not by
  concealment — see [Nothing is hidden](references/rendering.md#nothing-is-hidden).
- **Keep the `@@` headers.** They give line numbers and enclosing scope for free. In
  `viewer` and `html` mode the ranges stay byte-exact but the scope text is replaced by the
  hunk code and caption; that trade is deliberate, since git's context text for a file like
  an IIFE module is the same useless line on every hunk.
- **Every hunk appears in exactly one chapter**, except the multi-intent hunk described
  under [Clustering](#clustering).
- **Separate stated from inferred intent.** "The PR says…" versus "This looks like…".
- **Suspicions are suspicions.** Say "worth checking whether…", never "this is a bug",
  unless you read the surrounding code and can explain it concretely.
- **Never certify.** You read the diff; you did not verify it. Don't offer a verdict on the
  change as a whole.

**The completeness guarantee.** Every added or changed line appears somewhere in the tour,
and the mechanism is the ledger `tour-set.sh` keeps: chapters go through it in every mode,
and `rest` before the wrap-up reports anything unshown. See [Step H](#step-h-the-leftovers-chapter).

## Clustering

### What a good cluster looks like

A cluster is a **unit of intent**, not a file. Hunks from four files belong in one cluster if they exist for the same reason; two hunks in one file belong in different clusters if they don't.

**Its name describes a change**: "thread the tenant id into the cache key", "make the retry budget configurable", "backfill script for existing rows". Not a location: "changes to cache.py", "misc".

**Its length follows its cohesion.** Never split a cluster to make it shorter. If a change can only be explained through twelve interconnected hunks, that is one chapter of twelve hunks — two chapters of six that each depend on the other are strictly worse, because neither can be understood where it sits. When a cluster is genuinely long, say at the top how many hunks it holds and lead with the ones carrying the idea.

**Many hunks share a cluster, and almost every hunk has exactly one home.** A cluster of one hunk is possible but usually means the clustering is too fine. The exception is the multi-intent hunk: where two rounds of work overwrote the same lines, the surviving hunk genuinely serves two topics, and it may appear in both chapters. The operative gate is in pass 2 below: the other chapter must have no evidence at all without it, not merely be related to it. When you show it twice, say so: name its primary chapter and what the second chapter is looking at in it. A reader who sees the same hunk twice without being told is entitled to think you lost track.

**It is understandable from its predecessors alone.** The reader should never need a later chapter to follow an earlier one. If chapter 4 only makes sense after chapter 6, reorder.

**It is as separate as the diff permits, and no more.** You are reverse-engineering a history from a net result, not writing one: you see only the final state of every line. Where a location was rewritten in several rounds, the surviving hunk carries all of them at once and no clustering can separate it. Perfect separation is not available, and claiming it is a fabrication.

**What a cluster is never:** backend versus frontend. Tests versus code. By file type. By directory. Every one of those cuts across intent and produces chapters that can only be understood by reading a different chapter. **Tests belong with the behavior they pin down** — a spec asserting a new selector goes in the selector cluster. A layer split (schema → API → UI) is a last resort for a change that genuinely is one traversal of the stack, never a default.

### How to find them

Assume the diff is ugly. The commits may be checkpoints, merges and afterthoughts; the file order is alphabetical; the same lines may have been overwritten three times. **Cluster the whole diff as if you were writing the best possible commit history for it** — and derive that history from the diff's content, not from the commits that happen to be in it.

Three passes. Do not skip to assignment: grouping hunks by resemblance is what produces the location-based clusters above, because resemblance correlates with location.

**Pass 1 — extract topics, ignoring hunks.** Read the diff as a whole and name the ideas it contains: the behavior changes, the refactorings, the cleanups. Write them down as ideas, before deciding where any single hunk goes.

One test does most of the work here: **does this change observable behavior?** Behavior-preserving work and behavior-changing work are different topics even when they touch the same lines — it is what separates "the refactoring that made room" from "the change it made room for". Unlike "is this preparatory?", you can answer it from the diff.

Commit messages, PR descriptions and changelog entries are **hypotheses to test against the hunks, never the topic list itself**. Deriving topics from commit subjects smuggles back in the boundaries you were told not to trust.

Expect a range to hold several bodies of work, each with its own rounds of preparation, refactoring and cleanup. Within one body, `preparation → behavior change → cleanup` is a good ordering and a good hint at where a boundary falls. Across bodies it means nothing — don't force one arc onto a range that has three.

**Pass 2 — assign every hunk to the topic it exists for.** The test is counterfactual: **if this topic were reverted, would this hunk disappear from the diff?** Not "would my explanation mention it" — a topic's prose can be complete while a dozen hunks still exist only because of it, and judging by the prose sends all twelve to Leftovers.

- **A topic's chapter carries every hunk that belongs to it**, including the repetitive and inconsequential ones. Never move a topic's own follow-ups to Leftovers: by the time the reader reaches the end they have lost the context that made those hunks legible, and a hunk shown without its topic is worse than useless. Narrate the first one properly, then say the rest follow the same shape and show their diffs after it.
- **Tests and documentation go with the behavior they pin down or describe.** Six specs for one new behavior all belong to that topic, even though the explanation would read fine having quoted only one of them.
- A hunk two topics both claim goes to the one whose explanation would suffer more without it — that is its primary home, and this is where the incompleteness question earns its keep, as a tiebreaker. Show it again in the other chapter only if that chapter would otherwise have no evidence at all; a cross-reference is not enough, because in `viewer` mode the earlier chapter is off the screen.
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

**Be proportional.** Length is signal. A hunk that surprises you deserves several
sentences; an obvious one deserves a clause; a repeat of the hunk above deserves five
words. Uniform paragraphs under every hunk flatten the signal and exhaust the reader — the
variation is how they know where to slow down. This is the single most common way narration
fails.

**Explain what is non-obvious, and let the obvious pass.** Reach for explanation when a
hunk deviates from the idiom around it, does something its name does not suggest, defends
against something invisible in the diff, or takes a deliberate route past an easier one.

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

**Gloss a term once, at first use, in a clause.** Where a project's own concept is
unavoidable, define it in passing and move on. If the tour needs a glossary, the narration
is failing.

## Presentation modes

How the hunks reach the reader is a separate decision from how the tour is
clustered and narrated. There are three modes. Settle on one before printing
cluster 1 and say which you're using.

**`inline`** — narration and diffs interwoven in your own messages, diffs as
fenced diff blocks, as Step G describes. No syntax highlighting; accept that.
Works in every session, needs nothing installed, and stays readable in scrollback
after the session ends.

**`viewer`** — a second terminal running `delta`, which repaints as chapters
advance. Terminal sessions only. Narration stays in the chat and the reader
watches code on the other screen. Setup and the two commands are in
[references/viewer.md](references/viewer.md).

**`html`** — narration and diffs interwoven in a single HTML document, with real
syntax highlighting. In a session that renders HTML, stream it directly. In a
terminal session, write the file and ask the reader to open it. Build it as
described in [references/rendering.md](references/rendering.md).

### Choosing the mode

- **A session that renders HTML: use `html`, without asking.** It is strictly
  better there — highlighting, layout, and no second window to manage.
- **A terminal session: ask the reader**, once, before cluster 1. Name all three
  in a sentence each and let them pick. Don't assume: staying in the terminal
  matters to a lot of developers, and so does not juggling two windows.
- **An explicit `--inline` / `--viewer` / `--html` overrides all of that.** Never
  re-ask when the reader already said.
- **Any diff can drive any mode.** `tour-set.sh` takes either a git range or a
  patch file, so `gh pr diff 807 > /tmp/pr.patch` or
  `git diff HEAD > /tmp/wip.patch` works the same as `master..HEAD`. Nothing about
  the target restricts the mode.

### How the fidelity rules apply per mode

The [Fidelity](#fidelity) rules are absolute about the hunk *content* in
every mode: bytes come from `git diff`, never from you. Two of them are shaped by
the mode, and neither is a licence to loosen the others:

- **"Keep the `@@` headers"** — `inline` keeps them verbatim. `viewer` and `html` both run
  through the extractor, so they keep the ranges byte-exact and replace the
  enclosing-scope text with the hunk code and caption.
- **"Never hide an added or changed line"** — identical in all three modes, and not
  a length tradeoff in any of them. `inline` pastes long hunks whole, and the viewer
  and html both scroll.

### Nothing is hidden, and Leftovers is not a dumping ground

A reader cannot be responsible for code they were never shown, so the tour never hides a
hunk — not the repetitive ones, not the mechanical ones. Never show one hunk as a
representative of several: that hides exactly the case the tour exists to catch, the
seventh call site that differs.

A topic's own hunks stay in that topic's chapter, however dull. Leftovers is for hunks no
topic claimed — see [Step H](#step-h-the-leftovers-chapter).

A reader who scrolls past or leaves early has decided. Don't count it, don't remark on it,
don't withhold the wrap-up over it.

[references/rendering.md](references/rendering.md) covers renames, moved code, new files
and oversized hunks. All of it applies in every mode — none of its rules are about saving
space.

### Hunk codes

Every hunk carries a code so prose and screen can point at
each other. The code is `<chapter>.<hunk>`: `2.1`, `2.2`, `2.3` for the first
chapter's hunks, numbered in the order they appear on screen. No total count in
the code; the chapter header already carries "2/7".

Use them in prose the way you would a figure number: "the `??` in `2.1` is doing
precise work", "`2.3` is the guard on the whole approach". A reader who has
scrolled away can find the hunk again, and a reader reading only your prose still
knows how many hunks the chapter had.

## Reader commands

The overview names the starting commands; print this full list on `help`.
Every command works in every mode.

| Command | What you do |
|---|---|
| `next` / `n` | Print the next chapter. |
| `back` / `b` | Re-print the previous chapter, unchanged. |
| `zoom` | Widen the current chapter: the full enclosing functions, the callers you found in Step D, and the tests covering it. The hunks were already complete, so this adds surrounding code rather than restoring anything. Then return to the same footer so the tour resumes cleanly. |
| `why` | The reasoning behind this cluster: what the commits and comments state, what you inferred, what alternatives lost. Keep stated and inferred separate. |
| `skip` | Print the next chapter's hunks without narrating them, then stop as usual. The hunks stay where clustering put them — `skip` never defers anything to Leftovers, which is a clustering decision, not a navigation one. |
| `map` | Re-print the chapter list with a marker on the current chapter. |
| `go <n>` | Jump to chapter n. Later chapters may assume earlier ones, so say so when a jump lands on one that does. |
| `help` | Re-print the command list. |
| `done` | Stop touring and go straight to the wrap-up chapter. Run Step H's completeness check first; report what they did not see, without remarking on the fact that they left. |

In `viewer` mode, `back` and `go <n>` re-push a chapter, because the tour file is
single state and the viewer follows whatever it holds. Re-pushing is harmless: the
ledger de-duplicates, so the completeness check is unaffected. `zoom` pushes nothing —
the context it adds is not in the diff, so it goes in the chat while the viewer keeps
showing the chapter's hunks.

`references/rendering.md` has the rules for grouping hunks, renames, moved code, new files, whitespace-only changes and very large hunks. **Read it before printing the first chapter** — in particular [Nothing is hidden](references/rendering.md#nothing-is-hidden), which is the rule most easily broken by an agent trying to be concise.

In paired-viewer mode the shape is the same minus the `diff` blocks: push the chapter's hunks to the viewer, then narrate against their [hunk codes](#hunk-codes) — one framing line and one explanation per code, in the same order the viewer shows them. Never narrate a hunk the reader cannot see: if a code is not on their screen, paste it inline. Do not push it — the tour file is single state, so pushing would replace the chapter they are reading.

## Procedure

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

Modes (how the diff reaches you — see "Presenting the diff"):
  inline        Narration and diffs interwoven here in the chat, diffs as
                fenced diff blocks. No syntax highlighting. Works anywhere.
  viewer        A second terminal running delta, refreshing as chapters
                advance. Terminal sessions only.
  html          Narration and diffs interwoven in one HTML document.

  Pass one as a flag to force it: --inline, --viewer, --html.
  Otherwise: HTML-capable sessions use html; terminal sessions ask you.

Flags:
  --all         Print every chapter at once, no pausing
                (inline and html; the viewer shows one at a time)

While touring, reply with:
  next / n      go to the next chapter
  back / b      re-show the previous chapter
  zoom          expand this chapter: the enclosing code, the callers,
                and the tests that cover it
  why           more on the reasoning behind this chapter
  skip          show the next chapter's diffs without narration
  map           re-show the chapter list, marking where you are
  go <n>        jump to chapter n
  help          re-print this list
  done          end early, going straight to the wrap-up chapter
```

## Step B: Settle the presentation mode

Do this **first**, before acquiring the diff — acquiring, reading and clustering a large
change takes real time, and the reader should be able to choose a mode, walk away, and come
back to a finished tour. Asking later strands them: they answer a question instead of
getting chapter 1, and in `viewer` mode they then have to open a second terminal before a
chapter can exist at all.

See [Presentation modes](#presentation-modes) for the three modes and how to choose.

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

Two things it gets right that are easy to get wrong by hand: the no-target base is the
branch point (`git merge-base --fork-point`), never `@{upstream}` — on a pushed branch
that is the same branch on the remote, so the range covers only unpushed commits and
silently tours a fraction of the change. And a branch target uses three dots, because
bare `git diff <branch>` compares the *working tree* against it, which is the wrong
direction and includes local edits.

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
3. **Trace outward**: grep callers of changed symbols, find the tests covering this area, check config or schema the change depends on. This is what lets a cluster explanation say "and that's why the three call sites in `billing/` needed updating" instead of just describing lines.
4. **Establish before-and-after behavior.** For each meaningful change, know what the code did before and what it does now. That contrast is the substance of every cluster explanation.

Scale effort to the diff. A 30-line change needs a few minutes here; a 3,000-line one needs real exploration but should still stay at cluster granularity.

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

**What it does** — 2–4 sentences: the problem and the approach taken.

**New behavior** — bullets, only things observably different for a
user, caller, API consumer, or the data. "None — internal refactor" is
a valid and useful answer.

**Scope** — N files, +X/−Y lines, in M clusters across <M+3> chapters. Note anything excluded (lockfiles, generated code). If a whole
subsystem sits only in Leftovers, say which half of the branch the tour
actually covers.

**Where to be careful** — up to 3 ranked pointers at where risk
concentrates, each naming the cluster it lives in. These are attention
pointers, not verified bugs.

## The tour
2. <cluster name> — <half-line> · `path/one.py`, `path/two.py`
3. <cluster name> — <half-line> · `path/three.py`
4. Leftovers — <N hunks, and in a half-line what they are>
5. Wrap-up — what I verified, what I asserted, open questions

Say `next` to start, `go <n>` to jump in, or `help` for the commands.
```

Then stop and wait, unless `--all` was passed.

## Step G: Tour one cluster per chapter

One chapter per cluster, in order. The protocol is fixed; the prose is yours.

**Fixed:** open with `## <n>/<total> · <cluster name>`. Show every hunk of the cluster,
never retyped: push the chapter through `scripts/tour-set.sh` and take the hunks from the
file it writes — in `inline` mode you paste from that file, which is also where the
code-stamped `@@` headers come from. **Every chapter goes through the script in every
mode**, with `TOUR_NEW=1` on the first. Its ledger is the only thing that makes Step H's
completeness check mean anything; skip it and `rest` will report the whole diff as unshown
after you have already narrated it. Close with a footer naming the commands and the
position: ``next` · `zoom` · `why` · `map` · `help`   (chapter <n> of <total>)``. Then
**stop and wait for the reader.**

Several small blocks with a line of framing each read far better than one giant block, and
a cluster spanning many files leads with the hunks that carry the idea.

Everything else — how much to say, where to say nothing, what to admit, when to name an
alternative — is in [Narration](#narration). There is no template for it, because a
chapter about a one-line guard and a chapter about a rewritten module have nothing in
common but the protocol above.

Where a hunk deserves a specific thing for the reader to check, say it as a question they
can answer by looking, at a named location — not "this may have implications".

## Step H: The Leftovers chapter

**Leftovers are the hunks with no strong affinity to any topic** — not the boring hunks,
and never a topic's own repetitive follow-ups. If a hunk would disappear when a topic was
reverted, it belongs to that topic's chapter no matter how mechanical it looks. What lands
here is the genuinely unaffiliated: a `.gitignore` line, an editor config, a dependency
bump, churn in a subsystem the tour is not about, or a second body of work you named in
the overview and are not touring.

Group them by file, and **give each group one line saying what it is and why no topic
claimed it.** That is what makes a scroll-past an informed decision. It is also the check
on the classification: if you cannot say why a group belongs to no topic, it probably
belongs to one — go back to pass 2.

`tour-set.sh` takes the captions as `rest:<path>=<caption>` and warns about any group you
left bare. Each call reports how many hunks remain, which is how you know what this
chapter will hold. That count is for you, not a score to report to the reader.

**Run the completeness check before you write the wrap-up.** In every mode, call
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

## Examples

**Example 1** — "walk me through this PR"
Fetch the PR and its description, investigate, cluster into 4, print overview plus map, stop. Reader says `next`; print cluster 1 with two `diff` blocks and explanation; stop. Continue on each `next`.

**Example 2** — "/diff-tour main..HEAD --all"
Same clustering and same hunk rendering, printed straight through with no pauses. Useful when the reader wants to scroll or paste it somewhere.

**Example 3** — reader says `zoom` mid-tour
Re-show the current chapter with the full enclosing functions, the call sites found by grep, and the tests that cover it. Then return to the same footer so the tour resumes cleanly.

**Example 4** — "explain this diff, and show me the code"
The "show me the code" is the signal. Run the full tour rather than a prose summary.

## Troubleshooting

**Empty diff** — Report exactly what was compared ("no diff between HEAD and origin/main, working tree clean") and ask what to tour.

**One enormous hunk** (a rewritten file) — Don't paste hundreds of lines. Split it into sub-steps by function or section, show each separately with its own explanation, and say the file was rewritten so the reader knows why the diff looks the way it does.

**Diff is mostly formatting** — Detect with `git diff -w`. If the whitespace-ignoring diff is much smaller, tour *that*, and note upfront that formatting-only changes were set aside.

**`gh` fails** — Say so, suggest `gh auth login`, and offer to tour a local range instead.

**Reader jumps ahead or asks something unrelated mid-tour** — Answer, then offer to resume: "back to cluster 3 of 5?" Never restart the tour from the top unasked.
