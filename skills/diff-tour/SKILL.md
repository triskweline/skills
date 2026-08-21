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

## Step 0: Help

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

While touring, reply with:
  next / n      go to the next cluster
  back / b      re-show the previous cluster
  zoom          expand the current cluster: full hunks, surrounding
                code, callers, tests
  why           more on the reasoning behind this cluster
  skip          jump past this cluster
  map           re-show the cluster map and where you are in it
  go <n>        jump to cluster n
  done          end the tour with a wrap-up
```

## Step 1: Acquire the diff

- **No target**: `git diff @{upstream}...HEAD` (fall back to `git diff main...HEAD`, then `git diff HEAD~1`). If the working tree is dirty or that range is empty, also run `git diff HEAD` and fold the working-tree changes in.
- **PR number**: `gh pr view <n>` for title and description, `gh pr diff <n>` for the diff.
- **Range / commit / branch**: `git diff <range>`, plus `git log` over the range — commit messages carry stated intent.
- **Path**: restrict any of the above to that path.

Keep the raw diff text available for the whole tour. Every hunk shown later must be copied from it, not reconstructed from memory.

Note but exclude from the narrative: lockfiles, generated code, vendored directories, and pure-formatting churn. Say what was excluded and how many lines, so the reader knows the tour covers the whole change.

If the diff is empty, report exactly what was compared and stop. Don't invent a tour.

## Step 2: Understand before writing

The tour is only as good as this step, and it happens before any output.

1. **Read every hunk, then the enclosing function or class for each.** Behavior usually lives in the unchanged lines around a change — a two-line diff inside a retry loop means something different than the same two lines in a constructor.
2. **Read stated intent**: commit messages, PR description, linked issues if cheap. Keep stated intent separate from inferred intent when writing.
3. **Trace outward**: grep callers of changed symbols, find the tests covering this area, check config or schema the change depends on. This is what lets a cluster explanation say "and that's why the three call sites in `billing/` needed updating" instead of just describing lines.
4. **Establish before-and-after behavior.** For each meaningful change, know what the code did before and what it does now. That contrast is the substance of every cluster explanation.

Scale effort to the diff. A 30-line change needs a few minutes here; a 3,000-line one needs real exploration but should still stay at cluster granularity.

## Step 3: Cluster the hunks

A cluster is a **unit of intent**, not a file. Hunks from four files belong in one cluster if they exist for the same reason; two hunks in one file belong in different clusters if they don't.

Good cluster names describe a change: "thread the tenant id into the cache key", "make the retry budget configurable", "backfill script for existing rows". Bad ones name locations: "changes to cache.py", "misc".

Aim for **3–7 clusters**. Fewer means the tour isn't decomposing anything; more means the reader loses the thread. Very large diffs get 5–7 clusters with sub-steps inside, not 15 clusters.

**Order them so each one is understandable given only its predecessors.** That's usually: data model or types → core logic → call sites and adapters → tests → config, migrations, docs. Where a dependency order exists, follow it; the reader should never need a later cluster to understand an earlier one. If cluster 4 is only comprehensible after cluster 6, reorder.

Every hunk lands in exactly one cluster. If some hunks are genuinely trivial (renames, import shuffling), collect them in a final "mechanical fallout" cluster rather than pretending they're interesting.

## Step 4: Print the overview and the map

Before touring, give the reader orientation in roughly a screen:

```
# <one-line title of the change>

**What it does** — 2–4 sentences: the problem and the approach taken.

**New behavior** — bullets, only things observably different for a
user, caller, API consumer, or the data. "None — internal refactor" is
a valid and useful answer.

**Scope** — N files, +X/−Y lines, across M clusters. Note anything
excluded (lockfiles, generated code).

**Where to be careful** — up to 3 ranked pointers at where risk
concentrates, each naming the cluster it lives in. These are attention
pointers, not verified bugs.

## The tour
1. <cluster name> — <half-line> · `path/one.py`, `path/two.py`
2. ...

Say `next` to start, or `go <n>` to jump in.
```

Then stop and wait, unless `--all` was passed.

## Presenting the diff

How the hunks reach the reader is a separate decision from how the tour is
clustered and narrated. There are three modes. Settle on one before printing
cluster 1 and say which you're using.

**`inline`** — narration and diffs interwoven in your own messages, diffs as
fenced diff blocks, as Step 5 describes. No syntax highlighting; accept that.
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

## Step 5: Tour one cluster at a time

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
`next` · `zoom` · `why` · `map`   (cluster <n> of <total>)
~~~~

Repeat for every hunk in the cluster that carries meaning — several small `diff` blocks with a line of framing each read far better than one giant block. A cluster spanning many files leads with the hunks that carry the idea and lets the repetitive ones follow with short captions — it does not summarize them away (see [Every hunk gets shown](#every-hunk-gets-shown)).

`references/rendering.md` has the rules for trimming context, handling renames, moved code, whitespace-only changes, and very large hunks. **Read it before printing the first cluster** — the trimming rules are what keep a tour readable, and getting them wrong is the most common way this skill produces a wall of text.

In paired-viewer mode the shape is the same minus the `diff` blocks: push the chapter's hunks to the viewer, then narrate against their [hunk codes](#hunk-codes) — one framing line and one explanation per code, in the same order the viewer shows them. Never narrate a hunk the reader cannot see: if a code is not on their screen, either push it or paste it inline.

## Step 6: Wrap up

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
