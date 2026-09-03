---
name: vibe-tour
description: >-
  A fast, narrated tour of a code change for a human reviewer, tuned for generation speed over
  depth. Clusters the diff into topics and narration beats, shows every hunk, and tags each hunk
  with a gut-feel "fishiness" badge instead of a verified finding. Use when someone says
  "vibe-tour this branch", wants a quick walkthrough of a large or vibe-coded change, or finds
  diff-tour too slow for the change at hand. Not a code review: it points, the human judges.
metadata:
  version: 1.0.0
disable-model-invocation: true
---

# Vibe Tour

## Your basic job

Oh no! Your human just received a ton of vibe-coded changes to this repository. They are tasked to review that code and take responsibility for it.

What a thankless job! Luckily, they have you. You will provide the human with a narrated tour through that steaming pile of code, highlighting some possible fishy changes in the process.

**Narration**: Your tour must help the human follow and understand a large change by presenting smaller pieces in a logical order. For this you will cluster the hunks of a provided diff range into cohesive topics, find a human-friendly reading order and add some narration prose.

**Fishiness:** You will give each diff hunk an attention level, from "a tool could have written this, skip it" through "this may be wrong" to "a mistake here would be silent or irreversible, read every line". This is just your feeling / "Spidey sense" on a first read, and is worth exactly a second look. This is not a code review! You will not verify your suspicion, that would take way too long. The levels are a quick and cheap vibes check that lets the human choose how deep to go. If we print a wrong level, no worries: Verification and judgement remains with the human.

### What is NOT your job

**You are not the reviewer**. While you will share your own feelings and suspicions during the narration ("fishiness"), final judgement will be made by the human.

**You are not a code review skill**. You will only learn a shallow understanding of the diff, only enough to provide orientation, narration and fishiness tags. There are other skills (like `/code-review`) who are better at verifying changes deeply.

**You are not a teacher**. You can assume that the human has basic competence in this repository, its programming language and frameworks, and understands most of the pre-existing functionality. The human will also understand this new change once you transformed an alphabetically ordered wall of diff into a narrated tour.

## Tour generation needs to be lightning fast

A regular git diff prints in a second. Your tour is only useful to the human when you can generate it in a few minutes at most.

**Generation speed is the most important consideration in your work**, more important than narration quality and verification depth. You will take shortcuts, make compromises, limit tool calls and ration reasoning hops to provide the tour faster.

The only rule where we don't compromise is: Every hunk of the diff must be shown somewhere in the tour. A script enforces this at the end, so you never have to re-read the diff to check.

This skill uses parallel agents aggressively to cut down generation time. The **orchestrating agent** (the one the human invoked) may fork agents and spawn sub-agents without asking the human. The instructions below define the exact moments when it does. **Workers never fork or spawn anything.**

## Tour format is HTML

The tour will *not* be printed to this session.
Instead you deliver the tour as one self-contained HTML file.

The file is assembled from **fragments**: each worker writes a plain HTML fragment for its topic into its own file, the orchestrating agent writes the opening fragment, and a script lays them out. Nobody ever re-reads a fragment, and nobody ever types out a diff hunk: fragments name hunks by id, and the script splices the real diff bytes in when assembling.

Everything that makes the page pleasant is mechanical and costs no agent tokens: the script numbers the chapters, puts a beat's prose beside its hunks in two columns, highlights the diffs, and adds viewed marks and a theme switch. From the one word you put in each placeholder, the page's own JavaScript draws a **heat strip** per chapter, one coloured square per hunk in reading order, in the sidebar and under the chapter heading, and offers the reader a **scrutiny dial** that collapses hunks below the level they care about. Fragments use only `<h2>`, `<h3>`, `<p>`, `<code>` and the hunk placeholder. Nothing else, no styling, no ids, no numbers.

## The helper script

The skill ships one script, `bin/vibe-hunks.py` in the skill directory, with the page layout beside it in `bin/vibe_html.py`, `assets/` and the vendored `vendor/prism`. It needs only git and python3. It has four modes, all taking the same `git diff` arguments after a `--`:

```
vibe-hunks.py [--untracked] -- <git diff args>           the full diff, every hunk numbered
vibe-hunks.py --ids [--untracked] -- <git diff args>     one marker line per hunk
vibe-hunks.py --only h17,h20 -- <git diff args>          just those hunks
vibe-hunks.py --assemble OUT.html -- <git diff args> ++ FRAGMENT...
```

The numbered read is the *only* full read of the diff you do. Every hunk gets a marker line `### h17  path/to/file.rb:42` right before its `@@` line. A file without a text hunk (binary, mode change, pure rename) gets one marker of its own. From then on, everybody refers to hunks by their id.

Pass `--untracked` for the `dirty` and `uncommitted` targets, so files git does not track yet are numbered as additions.

## The target tour structure

Keep this in your head at all times. It describes the shape of the finished document. It is not a data structure that travels between agents: the orchestrating agent hands out topic titles, beat ideas and hunk ids, and gets back HTML fragments.

```
Tour # The entire tour report, one HTML file
+ headline: string   # written by the orchestrating agent
+ summary: markdown  # written by the orchestrating agent, from the topic summaries
+ topics: Topic[]

Topic # One cohesive topic or "body of work" in the diff range. One fragment file.
+ title: string
+ summary: markdown
+ beat_ideas: string[]  # drafted by the orchestrating agent, refined by the worker
+ beats: Beat[]
+ topic_hunks: HunkId[]
+ shared_hunks: Map<HunkId, TopicId>  # hunks of this topic that another topic also shows

Beat # One narration beat within a topic
+ title: string
+ summary: markdown
+ beat_hunks: Hunk[]

Hunk # One annotated diff hunk
+ id: string                 # h17, minted by the script
+ description: markdown      # describes what is done in that hunk
+ attention_level: 'skip' | none | 'note' | 'fishy' | 'hot'  # one word in the placeholder
+ attention_reason: text     # required for note, fishy and hot; lives in the placeholder
+ diff_content: text         # spliced in by the script, never typed by an agent
+ path: string
+ starting_line_number: integer
```

## The human must provide the diff range

If the human did not specify what diff to tour, or if the arguments are exactly `help`, `--help` or `-h` print this block verbatim and then exit.

```
vibe-tour — a narrated walkthrough of a code change

Usage: /vibe-tour [target]

Target:
  dirty         All unstaged and untracked changes
  staged        All staged changes
  uncommitted   All dirty and staged changes
  branch        Branch diff vs its branch point
  <git range>   e.g. main..HEAD, abc123..def456
  <commit>      e.g. HEAD~1, or a commit SHA
  <branch>      compared against the repo's default branch
  <number>      a PR or MR in this repo
  <PR/MR URL>   a GitHub pull request or GitLab merge request

The report is one self-contained HTML file.

Needs git and python3 (3.10+). Nothing to install.
```

## Ensure local access to the diff range

Make sure the provided diff range is available in a git repository on the local filesystem.

If the diff range is remote (e.g. GitHub PR), you might need to fetch or check out a branch. Abort when this would destroy local changes.

Translate the target into `git diff` arguments once, and use the same arguments for every script call:

| Target | git diff arguments |
|---|---|
| `dirty` | `--untracked --` (nothing after the dashes) |
| `staged` | `-- --cached` |
| `uncommitted` | `--untracked -- HEAD` |
| `branch`, `<branch>` | `-- <merge-base>..<tip>` |
| `<git range>` | `-- <range>` |
| `<commit>` | `-- <commit>~1..<commit>` |
| PR / MR | fetch, then as a range |

## One setup command: working directory, overview, numbered diff

Everything mechanical before the clustering happens in **one shell call**. Each separate call costs a full model turn, and the trial runs spent close to a minute on six calls whose commands took seven seconds together.

```
WORK=$(mktemp -d -t vibe-tour.XXXXXX) && echo "WORK=$WORK" \
  && git log --oneline <range> \
  && git diff --stat <git diff args> \
  && <skill dir>/bin/vibe-hunks.py [--untracked] -- <git diff args> > "$WORK/diff.txt" \
  && wc -l "$WORK/diff.txt"
```

Remember the working directory; every fragment and the finished tour go in there, and the workers need the path. It is outside the repository on purpose, so a `dirty` tour never numbers its own output.

The commit list is a hint, not the plan. In a perfect world, commits would already tell a narrated story, but often we see something different:

- There might be random "WIP"-style commits without a coherent topic
- There might be a giant mother of all commits, mixing all sorts of topics
- There might be dozens of micro commits that are too fine-grained to tell a digestible story
- A commit might be topic-pure, but the topic is too large to ingest in one gulp for a human
- There might be a mix of good and bad commit styles

So we glance at the commit log in case it does give a good signal. But our final selection of `Topic`s is deferred to a scan of the entire diff.

## Read the full diff

The numbered diff is in `$WORK/diff.txt`. **Read that file with the Read tool**, not by printing it in a shell: a shell result is capped and a long diff would be truncated, saved elsewhere and read back in pieces, which is three calls where one will do. The Read tool takes up to 2000 lines per call; `wc -l` told you how many calls that is. If it is more than one, read with an offset, back to back, nothing in between.

Do not run a plain `git diff` as well. You will eventually need to hold the entire diff in your context, so there is no point in doing a partial diff.

Every hunk has a marker line `### h17  path:line` before it. From here on, everybody refers to hunks by that id. Binary files show up as a marker with no diff body. For those we only need to know that they were added, changed, removed or moved, which the file header tells you.

## Generate a list of topics

Now that you've seen the commits and the full diff, you probably have some ideas what kind of work happened there.
Turn this into a list of thematically cohesive topics ("clusters", "stories", "body of work") that categorizes most of the diff.

Don't do a deep analysis to generate the list of topics.
You have a maximum budget of 10 tool calls to understand any of the concepts changed in the diff. The setup command and the Read calls for the numbered diff do not count against it. Everything after that counts, including any further git command. Focus on key questions you have, and only ask for the purpose of clustering hunks into topics. Don't stress if open questions remain, just work on intuition for those.

For each topic, list some sub-topics or content examples or significant edit motions that make up that topic. These will be the idea seed for the "beat generation" in the next step. Remember these sub-topics with the topic (`topic.beat_ideas`).

### On finding topics

1. A topic is a reason, not a place. Changes in four files belong together if they exist for the same reason. Two changes in one file belong apart if they don't.
2. Name it as a change, not a location. Good: "thread the tenant id into the cache key". Bad: "changes to cache.py", "misc", "backend".
3. Assign by this test: if this topic were reverted, would this line disappear from the diff? If yes, it belongs to that topic. Do not ask "does my explanation mention it" — a topic's explanation can be finished while twenty of its changes are still unassigned.
4. Never group by file type, directory, or tests-vs-code. A test belongs with the behaviour it tests. A doc belongs with the change it describes.
5. Do not take topics from commit messages. Read them for hints, then verify against the diff. Commit boundaries are usually wrong.
6. If a change fits no topic, you have missed a topic. Name the missing one. Do not create a "miscellaneous" bucket.
7. Never split a topic to make it shorter. Twelve changes that only make sense together are one topic of twelve.


## Assign hunks to topics

For each hunk, *quickly* guess which topic it belongs to.

Assign the hunk to the topic with the most apparent affinity or cohesion.
Every hunk must be assigned to at least one topic. A hunk can be assigned to multiple topics (e.g. when one code range was touched multiple times by several topics). It will then be shown once per topic, which is fine; a worker seeing a hunk that also belongs elsewhere says so in one sentence.

Write the assignment down as ids, one line per topic, in reading order. This is what the workers get, so keep it compact:

```
1. Thread the tenant id into the cache key: h3 h4 h9 h10 h11 h17
2. Drop the legacy CSV export: h1 h2 h5-h8
```

Don't do a deep analysis to assign hunks to topics. In particular, don't pay additional tool calls to better understand the codebase. When you're unsure, assign based on intuition.

## Fork agent workers to process topics in parallel

Fork multiple agents (called "workers" from here on). Each worker will narrate a topic.

Large topics should get a dedicated worker. Multiple small topics can be grouped into a single worker; that worker writes them into one fragment, in reading order.

Every worker gets its own directory, `<working dir>/topic-<NN>/`, numbered by the first topic it holds and zero-padded so the shell sorts them in reading order. Create it before forking. The worker writes exactly one file there, `fragment.html`, and never looks anywhere else. Workers cannot see each other's output, so they have nothing to react to.

Forks inherit your context, so a worker already holds the numbered diff. Do not paste hunks into the fork prompt. The prompt is short and always has the same shape. Its first line is fixed; it is what tells the fork that it is a worker and that only the worker section of this skill applies to it:

```
You are a vibe-tour worker. Only the section "Worker instructions per topic" applies to you.

Topic 3: Thread the tenant id into the cache key
Beat ideas: the key builder; the two call sites; the backfill migration
Hunks: h3 h4 h9 h10 h11 h17
Shared with topic 5: h9 h11
Write your fragment to: /tmp/vibe-tour.sLxCWm/topic-03/fragment.html
```

That is the whole briefing. Nothing about assembling, nothing about other topics, no path other than the worker's own file.

Fork all workers, then wait for all of them. If a worker fails or returns without having written its file, fork one replacement for that topic with the same briefing; do not touch the other workers' directories.

## Worker instructions per topic

**You are a worker if, and only if, your prompt begins with "You are a vibe-tour worker."** Then this section, from here to "You are done" below, is your entire instruction set. Everything above it describes the orchestrating agent's job, not yours. You already hold the numbered diff in your context; that is the only thing you take from the steps above.

What a worker never does, no matter what it notices:

- It does not fork or spawn any agent. There is no situation in which a worker needs help.
- It does not list, read or write anything outside its own directory. Other workers' directories and the working directory itself are not its business.
- It does not re-read the diff, does not cluster topics, does not reassign hunks, does not renumber anything.
- It does not assemble the tour, does not run the helper script's `--assemble` mode, and does not fix what it thinks other workers got wrong.
- It does not write more than one file.

If your briefing seems wrong (a hunk id that is not in the diff, a topic that does not fit), narrate what you can and say so in one sentence in your return message. Do not go looking for the answer.

### Get a cursory understanding of your hunks

A worker has a maximum budget of 5 tool calls to better understand a topic's hunks. Every tool call counts, including git.
Use these tool calls only to get a cursory, shallow understanding of what was changed in this topic, and only for the purpose of providing a better narration. Use the limited budget wisely, and focus on key questions. Work on intuition for everything else.

You already have every hunk in context from the numbered read. Do not spend a tool call re-reading it.

### Finalize narration beats

Start by finalizing a list of "narration beats" that will help the human understand the topic diff in smaller portions. You can use the provided beat ideas as a starting point, but know that they were only a draft from a previous step. Now that we're in a parallelized worker, we can take a little more time to refine the beats and improve readability.

To find a good narration beat, try to find groups of topic hunks that represent (rather) self-contained ideas, edit motions or programmer intents.
Separate preparatory work from the main change. Separate clean up work from the main change. Do not group by location or file type.

Assign each topic hunk to exactly one narration beat.

Don't do a deep analysis to assign hunks to beats. In particular, don't pay additional tool calls to better understand the codebase. When you're unsure, assign based on intuition.

### Give each hunk an attention level

Every hunk gets one of five attention levels. The scale is not "how suspicious" but **how carefully the human should read this**. That is the one dimension the reader's scrutiny dial and the heat strips need, and it has room for two things suspicion cannot express: code that looks fine but everything stands on, and code a tool wrote that nobody needs to read.

| Level | Written as | The reviewer | Your one question |
|---|---|---|---|
| skip | `<!-- hunk h17 skip -->` | trusts your description, does not read the diff | Could a tool have written this, or is it pure fallout of another hunk? |
| (none) | `<!-- hunk h17 -->` | reads once at normal speed | the default when no other question is a yes |
| note | `<!-- hunk h17 note: why -->` | reads, then consciously decides; your phrase says what | Is there a choice or a nit here the reviewer should knowingly accept? |
| fishy | `<!-- hunk h17 fishy: why -->` | verifies before approving | Can I name a specific way this is wrong? |
| hot | `<!-- hunk h17 hot: why -->` | reads line by line, however it looks | If this were subtly wrong, would the mistake be impossible to undo, or go unnoticed while affecting everyone? |

**Classify as a cascade, top down, and stop at the first yes: hot, fishy, note, skip, else nothing.** Every question is answered from the hunk itself and what you already know. Most hunks fall through in a glance.

Hot is about the cost of a mistake, not about how important or how public the code is. A broken public method fails loudly and a revert fixes it; that is fishy at most, and if the method is rarely used it is nothing. Hot is an auth or permission check that would fail open silently, a verification that would accept bad input without complaint, a gate on every request, a data rewrite, a delete, a payment, a sent email. Do not classify by file type or by category of code; ask the question.

Note collects three things that all get the same reviewer action: nitpicks (naming, a hardcoded string, a stray comment, an unused dependency), decisions the author made that the reviewer must accept knowingly (a default that changes behaviour for everyone, a deliberately omitted exemption, an input limit), and missing coverage for something significant.

Skip is lockfiles, schema dumps, renames, `include` lines, locale strings, path helpers, and any hunk that exists only because another hunk exists. It is the one level that saves the reader time, so use it freely where it is true.

This is not a code review! You do not verify anything; work on intuition and what you already know about the code base. If a level is wrong, no worries: the judgement remains with the human.

**Note, fishy and hot each need a reason**, one phrase or one sentence, written into the placeholder after the colon. No reason, no badge. For hot the reason names what a mistake would cost: `hot: the gate on every request`. A hunk that is both hot and fishy is hot, and the reason carries the suspicion. Plain text, no HTML, no `--` inside. Skip never has a reason.

### Write the topic fragment

Write the whole topic as one HTML fragment to the path you were given. One `Write`, no re-reading. This is the shape:

```html
<h2>Topic title</h2>
<p>Topic summary: what this body of work does, across all its beats.</p>

<h3>Beat title</h3>
<p>Summary of what happens in this beat, across all hunks.</p>

<!-- hunk h3 -->
<p>Description of hunk h3.</p>

<!-- hunk h4 fishy: what feels off, in one phrase or sentence -->
<p>Description of hunk h4.</p>

<!-- hunk h5 skip -->
<p>The lockfile fallout of h1.</p>

<!-- hunk h6 hot: the gate on every request -->
<p>Description of hunk h6.</p>

<h3>Next beat</h3>
...
```

The rules that matter:

- **Never type out a diff.** Put `<!-- hunk h17 -->` where the hunk belongs. The assembler replaces it with the real, escaped, highlighted diff and its `path:line`. Typing the hunk yourself is slower, and a `<` in the code would break the page.
- Every hunk id you were given appears exactly once as a placeholder.
- The paragraph **after** a placeholder describes that hunk and is rendered right above its diff. The prose **before** the first placeholder of a beat is the beat's narration and sits beside the hunks.
- No numbers in headings, no `<section>`, no ids, no styling. The script numbers chapters by fragment order and builds the sidebar; anything you add there is stripped or, worse, disagrees with it.
- The topic summary is the summary of all its beats. The beat summary is the summary of all its hunks.

### You are done

Once `fragment.html` is written, you are done. Return to the orchestrating agent with two things only: the fragment path, and the topic summary in one or two sentences. Then exit. Do not wait for other workers, do not check on them, do not verify the assembly, do not start anything else. The fragment is the deliverable and the orchestrating agent takes it from here.

## Assemble the tour

Once all workers have returned, write the opening fragment `<working dir>/00-intro.html`: the `<h1>` headline and one or two summary paragraphs built from the topic summaries the workers returned. Nothing else; the script builds the sidebar and the meta line.

Then assemble, in one command:

```
<skill dir>/bin/vibe-hunks.py --assemble <working dir>/vibe-tour.html [--untracked] -- <git diff args> ++ <working dir>
```

Given a directory, the script takes every `.html` file under it in path order, which puts `00-intro.html` first and the workers' `topic-NN/fragment.html` after it in reading order; the output file itself is skipped. The script splices every placeholder, and appends any hunk no fragment placed in a final "Unsorted hunks" chapter, listing those ids on stderr. That is the completeness rule, enforced without anyone re-reading the diff. It also lists placeholders that name no hunk, and hunks placed more than once; the latter is expected for shared hunks.

If the script reports unplaced hunks, that is acceptable for speed: they are shown. Only if the list is long, or the hunks clearly belong to one topic, write them into that topic's fragment with a one-line description each and run the assemble command again.

Tell the human the path of the finished file. That is the end of the tour.
