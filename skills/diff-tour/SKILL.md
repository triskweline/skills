---
name: diff-tour
description: Walks a reader through a code change cluster by cluster, showing the real diff hunks with +/- markers inline and explaining each cluster before moving to the next, pausing for the reader between clusters. Starts with an overview of the change and the new behaviors, then tours the clusters. Use this whenever the user wants to be *walked through*, *toured*, *guided through*, or *led through* a diff, PR, branch, or commit — phrases like "walk me through these changes", "show me the diff with explanations", "explain this PR hunk by hunk", "review this change with me", "tour this branch", "show me the actual code as you explain it" — and also whenever a user asking to "explain a diff" wants to see the code itself rather than a prose summary. Prefer this over a summary-only explainer any time the user says "show me" about a change.
metadata:
  version: 1.1.0
---

# Diff Tour

A tour, not a report. The reader wants to end up understanding the change well enough to review or extend it, and they want to see the actual code while that happens — not a prose summary that forces them to open files themselves.

Two things make this skill work, and both are easy to get wrong:

1. **Real hunks, verbatim.** Every cluster shows the actual diff lines with their `+`/`-` markers, copied character-for-character from `git diff`. Paraphrased or retyped code silently destroys the whole value of the tour.
2. **One cluster at a time.** Stop after each cluster and let the reader say `next`. A tour that dumps everything at once is just a long document, and the reader loses the thread by cluster three.

## Clusters and chapters

Two numbering schemes, deliberately different so they can never be confused:

- **Steps A–H are lettered.** They are this skill's procedure — what you do, in
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

## Step A: Help

If the arguments are exactly `help`, `--help`, `-h`, or `?`, print this block verbatim and stop — don't gather a diff.

```
diff-tour — a guided, cluster-by-cluster walkthrough of a code change

Usage: /diff-tour [target] [flags]

Target (optional, defaults to your working diff):
  <empty>       Branch diff vs upstream, plus uncommitted changes
  <PR number>   e.g. 4821 — fetched via `gh pr diff`
  <git range>   e.g. main..HEAD, abc123..def456
  <commit>      e.g. HEAD~1, or a commit SHA
  <branch>      compared against the repo's default branch
  <path>        limit the tour to a file or directory

Modes (how the diff reaches you — see "Presenting the diff"):
  inline        Narration and diffs interwoven here in the chat, diffs as
                fenced diff blocks. No syntax highlighting. Works anywhere.
  viewer        A second terminal running delta, refreshing as chapters
                advance. Terminal sessions only.
  html          Narration and diffs interwoven in one HTML document.

  Pass one as a flag to force it: --inline, --viewer, --html.
  Otherwise: HTML-capable sessions use html; terminal sessions ask you.

Flags:
  --all         Print every cluster at once, no pausing
  --full        Show full hunks with no context trimming

  Both apply to inline and html. The viewer shows one chapter at a
  time and never trims.

While touring, reply with:
  next / n      go to the next chapter
  back / b      re-show the previous chapter
  zoom          expand this chapter: untrimmed hunks, the enclosing
                code, callers, and the tests that cover it
  why           more on the reasoning behind this chapter
  skip          pass over this chapter
  map           re-show the chapter list, marking where you are
  go <n>        jump to chapter n
  help          re-print this list
  done          end early, going straight to the wrap-up chapter
```

## Step B: Settle the presentation mode

Do this **first**, before acquiring the diff — acquiring, reading and clustering a
large change takes real time, and the reader should be able to choose a mode, walk
away, and come back to a finished tour. Asking later strands them: they answer a
question instead of getting chapter 1, and in `viewer` mode they then have to open a
second terminal before a chapter can exist at all.

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

The [fidelity rules](#fidelity-rules) are absolute about the hunk *content* in
every mode: bytes come from `git diff`, never from you. Two of them are shaped by
the mode, and neither is a licence to loosen the others:

- **"Keep the `@@` headers"** — `inline` and `html` keep them verbatim. `viewer`
  keeps the `-x,y +a,b` ranges byte-exact but replaces the enclosing-scope text
  with the hunk code and caption. That trade is deliberate: git's context text for
  a file like an IIFE module is the same useless line on every hunk.
- **"Mark every elision"** — `inline` and `html` mark trimmed *context* with `…`.
  No mode ever elides a whole hunk: see "Every hunk gets shown" below.

### Every hunk gets shown

A reader cannot be responsible for code they were never shown. So the tour never
hides a hunk — not the repetitive ones, not the mechanical ones.

- **Never show one hunk as a representative of several.** The old habit of "the
  same substitution in six more call sites, say `zoom` to see them" hides exactly
  the case the tour exists to catch: the seventh site that differs.
- **End with a Leftovers chapter.** After the narrated clusters, one final chapter
  carries every hunk no cluster wanted — repeats, renames, import shuffles,
  generated churn. In `viewer` mode the viewport scrolls as far as it needs to, so
  length costs nothing; in `inline` and `html` mode put it behind a heading the
  reader can skip.
- **Leftovers are grouped and annotated, not dumped.** Each file's leftover group
  gets one line saying what it repeats and how it resembles something already
  explained — "the same accessor swap as 2.2, in nine more places", "the behavior
  changes 1.1 and 1.2 described, in release-note form". That is what makes a
  scroll-past an informed decision rather than a gamble. `tour-set.sh` takes those
  as `rest:<path>=<caption>` and warns about any group you left uncaptioned.
- **Track what is left, for your own sake.** Pass `TOUR_NEW=1` on chapter 1 to
  start the ledger; `rest` then selects every hunk no earlier chapter used, and
  each call reports how many remain. That count is how you build the Leftovers
  chapter — it is not a score to report to the reader.
- **A reader who scrolls past or leaves early has decided.** Don't count it,
  don't remark on it, don't withhold the wrap-up over it.

[references/rendering.md](references/rendering.md) covers trimming, renames, moved
code and oversized hunks. Its trimming rules apply to `inline` and `html`; in
`viewer` mode read it for the rename, moved-code and large-hunk guidance and skip
the trimming section.

### Hunk codes

In `viewer` and `html` mode every hunk carries a code so prose and screen can point at
each other. The code is `<chapter>.<hunk>`: `2.1`, `2.2`, `2.3` for the first
chapter's hunks, numbered in the order they appear on screen. No total count in
the code; the chapter header already carries "2/7".

Use them in prose the way you would a figure number: "the `??` in `2.1` is doing
precise work", "`2.3` is the guard on the whole approach". A reader who has
scrolled away can find the hunk again, and a reader reading only your prose still
knows how many hunks the chapter had.

## Step C: Acquire the diff

- **No target**: diff against the branch point, not the tracking branch. Resolve the base with `git merge-base --fork-point <default> HEAD`, falling back to `git merge-base <default> HEAD`, then `git diff <base>..HEAD`. Never `@{upstream}`: on a pushed branch that is the same branch on the remote, so the range covers only unpushed commits and silently tours a fraction of the change. If the working tree is dirty, also run `git diff HEAD` and fold it in. State which base you used and how many commits and hunks it covered, so a wrong guess is visible to the reader.
- **PR number**: `gh pr view <n>` for title and description, `gh pr diff <n>` for the diff.
- **Range / commit**: `git diff <range>`.
- **Branch**: `git diff <default>...<branch>`. Bare `git diff <branch>` compares the *working tree* against that branch, which is the wrong direction and includes local edits.

For every target, read the commit log over the range. It is the cheapest signal you will get for intent, for where the natural cluster boundaries are, and for whether the range holds more than one body of work. Skip merge commits when reading intent.
- **Path**: restrict any of the above to that path.

Keep the raw diff text available for the whole tour, and also write it to a patch file under a scratch path. Every hunk shown later must come from it, not from memory. `viewer` and `html` both need it on disk, and a saved patch is immune to the branch moving mid-session — which it does.

Note but exclude from the narrative: lockfiles, generated code, vendored directories, and pure-formatting churn. Excluded means not narrated, never hidden — those hunks still appear in the Leftovers chapter under one caption naming what they are. Say what was excluded and how many lines.

If the diff is empty, report exactly what was compared and stop. Don't invent a tour.

## Step D: Understand before writing

The tour is only as good as this step, and it happens before any output.

1. **Read every hunk, then the enclosing function or class for each.** Behavior usually lives in the unchanged lines around a change — a two-line diff inside a retry loop means something different than the same two lines in a constructor.
2. **Read stated intent**: commit messages, PR description, linked issues if cheap. Keep stated intent separate from inferred intent when writing.
3. **Trace outward**: grep callers of changed symbols, find the tests covering this area, check config or schema the change depends on. This is what lets a cluster explanation say "and that's why the three call sites in `billing/` needed updating" instead of just describing lines.
4. **Establish before-and-after behavior.** For each meaningful change, know what the code did before and what it does now. That contrast is the substance of every cluster explanation.

Scale effort to the diff. A 30-line change needs a few minutes here; a 3,000-line one needs real exploration but should still stay at cluster granularity.

## Step E: Cluster the hunks

A cluster is a **unit of intent**, not a file. Hunks from four files belong in one cluster if they exist for the same reason; two hunks in one file belong in different clusters if they don't.

Good cluster names describe a change: "thread the tenant id into the cache key", "make the retry budget configurable", "backfill script for existing rows". Bad ones name locations: "changes to cache.py", "misc".

Aim for **3–7 clusters**. Fewer means the tour isn't decomposing anything; more means the reader loses the thread. Very large diffs get 5–7 clusters with sub-steps inside, not 15 clusters.

**Never split a cluster to make it shorter.** A cluster is as long as its cohesion requires. If a change can only be explained through twelve interconnected hunks, that is one chapter of twelve hunks — two chapters of six that each depend on the other are strictly worse, because neither can be understood where it sits. The 3–7 range counts *ideas the reader tracks*, not length. When a cluster is genuinely long, say at the top how many hunks it holds and order them so the ones carrying the idea come first.

**Order them so each one is understandable given only its predecessors.** That's usually: data model or types → core logic → call sites and adapters → tests → config, migrations, docs. Where a dependency order exists, follow it; the reader should never need a later cluster to understand an earlier one. If cluster 4 is only comprehensible after cluster 6, reorder.

The mapping is many-to-one, in that order: **one chapter holds as many hunks as share its reason — that is the whole point of clustering by intent — and each hunk has exactly one home.** A chapter of one hunk is possible but usually means the clustering is too fine; a chapter of a dozen is fine if a dozen hunks exist for the same reason. The last chapter is always [Leftovers](#every-hunk-gets-shown).

Send a hunk to Leftovers when narrating it would not add understanding: it repeats a change already explained, or it is the mechanical product of one — renames, import shuffles, a regenerated table of contents, the same substitution in nine more call sites.

The test is the caption: you may only defer a hunk if you can say in one line what it repeats or what produced it. If you can't name that, it isn't repetitive, it's unexamined, and it belongs in a narrated cluster. Two things are never deferred: a hunk with an observable consequence, however small it looks, and a hunk you haven't read.

A repeat stays in its cluster when the reader needs it to trust the cluster's claim, and goes to Leftovers when the claim is already complete without it.

Deferring is not a way to hit the 3–7 cluster budget. If most of the diff ends up in Leftovers, either the clustering is lazy or the branch contains two unrelated bodies of work — decide which, and if it's the latter, say so in the overview.

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
4. Leftovers — <N hunks, and in a half-line what they repeat>
5. Wrap-up — what I verified, what I asserted, open questions

Say `next` to start, `go <n>` to jump in, or `help` for the commands.
```

Then stop and wait, unless `--all` was passed.

## Step G: Tour one cluster per chapter

For each cluster, in order, output this shape and then **stop and wait for the reader**:

~~~~
## <n>/<total> · <cluster name>

<1–2 sentences: what this cluster accomplishes and why it exists.>

`path/to/file.ext`  <what this specific hunk does, half a line>

```diff
@@ -142,7 +142,9 @@ def resolve_price(order, tenant):
     cache_key = f"price:{order.sku}"
-    cached = cache.get(cache_key)
+    cache_key = f"price:{tenant.id}:{order.sku}"
+    cached = cache.get(cache_key)
     if cached is not None:
```

<Explanation: what it did before, what it does now, why the change was
made this way. Reference specific lines. Where relevant: what it means
for callers, what it costs, what invariant it establishes or removes.>

<Optional — only when there's something real to say:>
**Watch for** — <a specific thing to verify, phrased as a question the
reader can answer by looking>

---
`next` · `zoom` · `why` · `map` · `help`   (chapter <n> of <total>)
~~~~

Repeat for every hunk in the cluster — several small `diff` blocks with a line of framing each read far better than one giant block. A cluster spanning many files leads with the hunks that carry the idea and lets the repetitive ones follow with short captions — it does not summarize them away (see [Every hunk gets shown](#every-hunk-gets-shown)).

### Reader commands

Print the command list once, in the overview chapter, and re-print it on `help`.
Every command works in every mode.

| Command | What you do |
|---|---|
| `next` / `n` | Print the next chapter. |
| `back` / `b` | Re-print the previous chapter, unchanged. |
| `zoom` | Re-print this chapter with nothing trimmed, plus the enclosing functions, the callers you found in Step D, and the tests covering it. Then return to the same footer so the tour resumes cleanly. |
| `why` | The reasoning behind this cluster: what the commits and comments state, what you inferred, what alternatives lost. Keep stated and inferred separate. |
| `skip` | Move on without narrating. The hunks stay in the tour; they are not deferred to Leftovers, which is a clustering decision, not a navigation one. |
| `map` | Re-print the chapter list with a marker on the current chapter. |
| `go <n>` | Jump to chapter n. Chapters are independent of each other only forward — say so if they land somewhere that assumes an earlier chapter. |
| `help` | Re-print the command list. |
| `done` | Stop touring and go straight to the wrap-up chapter. Run Step H's completeness check first; report what they did not see, without remarking on the fact that they left. |

In `viewer` mode, `back`, `go <n>` and `zoom` all re-push a chapter, because the
tour file is single state and the viewer follows whatever it holds. Re-pushing an
earlier chapter is harmless: the ledger de-duplicates, so the completeness check
is unaffected.

`references/rendering.md` has the rules for trimming context, handling renames, moved code, whitespace-only changes, and very large hunks. **Read it before printing the first cluster** — the trimming rules are what keep a tour readable, and getting them wrong is the most common way this skill produces a wall of text.

In paired-viewer mode the shape is the same minus the `diff` blocks: push the chapter's hunks to the viewer, then narrate against their [hunk codes](#hunk-codes) — one framing line and one explanation per code, in the same order the viewer shows them. Never narrate a hunk the reader cannot see: if a code is not on their screen, paste it inline. Do not push it — the tour file is single state, so pushing would replace the chapter they are reading.

## Step H: The Leftovers chapter

Every hunk no cluster wanted, in one chapter, grouped by file with a caption per
group. The policy is in [Every hunk gets shown](#every-hunk-gets-shown); this is
where it happens.

**Run the completeness check before you write the wrap-up.** In every mode, call
`tour-set.sh` with the `rest` spec once. It selects every hunk no earlier chapter
used, and if there are none it prints `all hunks already shown` and exits 0. That
is the only mechanical guarantee the tour has that nothing was dropped — do not
print the wrap-up chapter without it.

If `rest` returns hunks, they are this chapter. Caption each file's group with what
it repeats, and say plainly that nothing here was explained and scrolling it is the
reader's call.

## Step I: The wrap-up chapter

After the last cluster, or on `done`:

- **Recap** the change as a chain: cluster 1 enabled cluster 2 enabled cluster 3. Three or four sentences. The reader should be able to retell the change from this. Note that a causal chain is inference by construction, so most of it belongs in the asserted list below.
- **What you verified, and what you asserted.** Two lists, no hedging.
  *Verified* — claims where you read the deciding code. Name the action and its
  result: "grepped `resolvePrice`, 3 callers, all in `billing/`", "read the
  enclosing function", "ran the spec". An entry with no action behind it does not
  belong here, however confident the prose was, and reading the diff is never
  verification — the hunk shows what changed, not whether it is right.
  *Asserted* — claims resting on a commit message, a code comment, a plan
  document, or your own inference; say what you relied on. If you did not run the
  tests, say so in those words.
  The second list is the point: fluent narration turns inference into fact, and
  this is where that gets undone.
- **Open questions** for the author, if any.
- **Suggested next step** — usually a dedicated code-review pass to verify the "watch for" items (`/code-review` in Claude Code), or a specific file worth reading in full.

## Fidelity rules

These are what separate this from a prose summary, so hold them tightly:

- **Never retype code.** Copy hunk lines byte-for-byte from the diff output, markers included. If a line is too long, let it wrap — don't shorten it.
- **Never fabricate a hunk** to illustrate a point. If the diff doesn't contain it, it doesn't get a `diff` block.
- **Mark every elision.** Trimmed context becomes a `…` line, never a silent deletion. The reader must be able to trust that what they see is what's there.
- **Keep the `@@` headers.** They give line numbers and enclosing scope for free.
- **Separate stated from inferred intent.** "The PR says…" versus "This looks like…".
- **Suspicions are suspicions.** Say "worth checking whether…", never "this is a bug", unless it has been verified by reading the surrounding code and can be explained concretely.
- **Don't pad.** A cluster whose explanation is one sentence gets one sentence. Empty "watch for" sections are omitted, not filled.

## Examples

**Example 1** — "walk me through this PR"
Fetch the PR and its description, investigate, cluster into 4, print overview plus map, stop. Reader says `next`; print cluster 1 with two `diff` blocks and explanation; stop. Continue on each `next`.

**Example 2** — "/diff-tour main..HEAD --all"
Same clustering and same hunk rendering, printed straight through with no pauses. Useful when the reader wants to scroll or paste it somewhere.

**Example 3** — reader says `zoom` mid-tour
Re-show the current cluster with untrimmed hunks, plus the full enclosing functions, the call sites found by grep, and the tests that cover it. Then return to the same cluster's footer so the tour resumes cleanly.

**Example 4** — "explain this diff, and show me the code"
The "show me the code" is the signal. Run the full tour rather than a prose summary.

## Troubleshooting

**Empty diff** — Report exactly what was compared ("no diff between HEAD and origin/main, working tree clean") and ask what to tour.

**One enormous hunk** (a rewritten file) — Don't paste hundreds of lines. Split it into sub-steps by function or section, show each separately with its own explanation, and say the file was rewritten so the reader knows why the diff looks the way it does.

**Diff is mostly formatting** — Detect with `git diff -w`. If the whitespace-ignoring diff is much smaller, tour *that*, and note upfront that formatting-only changes were set aside.

**`gh` fails** — Say so, suggest `gh auth login`, and offer to tour a local range instead.

**Reader jumps ahead or asks something unrelated mid-tour** — Answer, then offer to resume: "back to cluster 3 of 5?" Never restart the tour from the top unasked.
