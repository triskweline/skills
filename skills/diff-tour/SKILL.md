---
name: diff-tour
description: >-
  Helps a human understand a code change they did not write but must review and take
  responsibility for. Useful to screen large changes by colleagues or AI agents. Narrates the
  diff as a tour: chapters in a reading order that builds
  understanding step by step, every hunk shown beside prose that says what it is for and how it
  connects to the rest, and a mark on each hunk saying how carefully it deserves to be read, so
  the reviewer can move quickly through the routine parts and slow down where a mistake would
  hurt. Opens with the problem, what changes, and how it was built. Fast enough for large changes.
  Use when someone wants to be walked through a diff, branch, commit, pull request or merge
  request, or asks for help understanding or reviewing one: "tour this branch", "walk me through
  this PR", "diff-tour main..HEAD", "help me review these changes". Not a code review: it
  leaves the judgement to the human.
metadata:
  version: 2.0.0
---

# Diff Tour

This skill has five parts. Part 1 is background for everyone. Parts 2 to 4 are the orchestrator's steps, in order. Part 5 is the workers' instructions. The words **orchestrator**, **worker** and **fan-out** are defined in Part 1; the part titles are how you find your place.

# Part 1: Background and rules for everyone

## Your basic job

Oh no! Your human just received a ton of vibe-coded changes to this repository. They are tasked to review that code and take responsibility for it.

What a thankless job! Luckily, they have you. You will provide the human with a narrated tour through that steaming pile of code, marking the places that deserve a closer look.

The changes were mostly written by agents, so they rarely contain typos, formatting slips or simple local bugs. What the reader looks for instead:

1. A misunderstanding or wrong assumption that many consistent changes follow.
2. Code in the wrong place, a module stretched past its purpose, a missed extraction.
3. An implementation more complicated or longer than the job needs.
4. Code for edge cases that may not be worth their lines.
5. A style of solution with no precedent in this repository, and not common in the ecosystem.
6. A different approach that would have avoided the verbose code, or made the edge cases disappear.

Your tour helps them find these. You point at them; they judge them.

**Narration**: The tour helps the human follow and understand a large change by presenting smaller pieces in a logical order. The diff is clustered into cohesive topics, put into a reading order, and narrated.

**Heat**: Every hunk gets a heat level, from "nothing to decide or fear, skip it" through "you have a decision to make" and "something here does not add up" to "this hunk decides something costly, read every line". A level is your judgement of how carefully the human should read the hunk. The five levels are defined in *Give each hunk a heat level* in Part 5.

### How you read

You are the colleague who reads the change first. You walk the human through it and tell them what you understood, what you doubt and what you could not check.

You read with curiosity and doubt. Names, comments, tests, commit messages, framework conventions and your own first reading are claims about the code, not facts. Every doubt ends in one of two ways: you check it, or you state it as a doubt. Never let a doubt quietly become a fact.

Pick your battles. The human is waiting for the tour, and you cannot check everything in a few minutes. Check where a wrong statement would mislead the reader most: a hot or fishy hunk, a motivation, a claim about behaviour outside the diff. Read the mechanical parts quickly. Some steps are marked **This step is an investment**; those are where your checks belong. Tool calls are budgeted: each such step states its own budget, and a step without one makes no lookups. Whatever you did not check, say so: "the diff does not show whether…", or "not checked in the time available". An honest gap never harms the reader; a confident guess can.

### What is NOT your job

**You are not the reviewer.** The change has usually been reviewed by agents before it reaches you, and the human is reviewing it right now, with your tour. So you investigate to understand and to point, not to judge. Your one judgement is about attention: a heat level says how carefully to read a hunk, never whether the change is right. You may offer an opinion or a possible fix, such as where the code could live instead, held loosely and said as such. You give no verdict and no approval: the human decides.

**You are not a teacher**. The human has basic competence in this repository, its language and frameworks, and understands most of the pre-existing functionality. They will understand this change once you have turned an alphabetically ordered wall of diff into a narrated tour.

## Writing the tour

These rules hold for every piece of prose in the tour, the summary and the chapters alike. Each slot adds its own rules where it is described; those come on top of these.

**Every sentence earns its place.** It either speeds up the reader's understanding, or it lets them skip something. If a sentence were gone and the reader would lose neither, cut it. Length is a cost: every sentence you add is one more the reader has to get through.

**Short is right when little happens.** The limits in this skill are ceilings, not targets. The reader saves the most time where you write the least.

**Outer layers summarise their inner layers.** The tour's prose is nested in layers: a chapter's summary, the prose of its beats, and for each hunk its sentence and, where it has one, its heat explanation. A reader moves inwards only as far as they need to. So an outer layer says what its inner layers hold, well enough for the reader to decide whether to open them at all.

**Never list what the code shows.** Not the columns a migration adds, not the keys of a settings block, not the methods of a trait, not the cases a test runs through. The diff sits one glance below; a list of its contents makes the reader read the change twice. List only when a list is the clearest way to say something the diff does not show.

**Say why only when you have seen or researched the reason.** A motivation may come from anything you have actually seen: a comment or a commit message, a test name, a constraint removed elsewhere in the diff, something a tool call returned. State those plainly. When you are connecting dots instead, say so in the sentence: "presumably to let the admin form reopen a booking; the diff does not say." When you have neither, name the gap: "the diff does not say why the indexes go." A reason stated as fact that nothing supports is the one thing a summary must never contain; a reviewer trusts the summary instead of reading, and a wrong reason on the riskiest chapter sends them the wrong way.

**A doubt takes one clause, attached to its claim.** "The old guard presumably blocked destroy; not checked", not a separate sentence of hedging, and never several hedges in one sentence.

**Say what you found, never how you looked**: no tool names, no `SRC`, no "I checked" or "a search found". Where it matters how solid a statement is, say so in a word: confirmed, or not checked. Don't turn a doubt into a task for the reader, such as "worth confirming that X". State it as a doubt: "X is not checked". Which doubts to check is decided when you explore, not when you write.

## Who does what: orchestrator, workers, fan-out

The **orchestrator** is the agent the human invoked. It resolves the target, reads the diff, clusters it into topics, and then **fans out**: it forks one **worker** agent per topic (or per group of small topics). Each worker narrates its topic into one HTML fragment and exits. While the workers run, the orchestrator writes the tour summary. When all workers have returned, the orchestrator assembles the fragments into the tour and hands the human a URL.

A forked worker inherits the orchestrator's whole context, including this skill. Its prompt begins with a fixed sentence that tells it it is a worker. Part 1 applies to both roles. Parts 2 to 4 are the orchestrator's alone. Part 5 is the workers' alone.

**The orchestrator may fork agents without asking the human. Workers never fork or spawn anything.**

## Completeness

The one rule we don't compromise on: every hunk of the diff is shown somewhere in the tour. A script enforces this at the end, so nobody has to re-read the diff to check.

## Code outside the diff is read under SRC

The repository on disk is not always the code the tour describes: it may sit on a later branch, or hold edits the tour does not show. So whenever any role reads code outside the diff, with Read, Grep or a shell, it reads under the `SRC=` path the setup command printed, never in the repository itself. For a commit, branch, range or PR that path is a copy of the toured code; for `staged` it is a copy of the index; for `dirty` and `uncommitted` it is the repository, because the working tree is what those tours show. The copy is removed as the tour's last step, after every assemble.

## Tour format is HTML

The tour is *not* printed to this session. It is one self-contained HTML file, opened in a browser.

The file is assembled from **fragments**: each worker writes a plain HTML fragment for its topic into its own directory, the orchestrator writes the opening fragment with the tour summary, and a script lays them out. Nobody ever re-reads a fragment, and nobody ever types out a diff hunk: fragments name hunks by id, and the script splices the real diff bytes in when assembling.

Everything that makes the page pleasant is mechanical and costs no agent tokens: the script numbers the chapters, puts a beat's prose beside its hunks in two columns, highlights the diffs, and adds viewed marks and a theme switch. From the level in each placeholder, the page's own JavaScript draws a **heat strip** per chapter in the sidebar, one coloured square per hunk in reading order, and gives the legend a **mark viewed** button for skip, read and note, so a reader can fold away whole levels and be left with fishy and hot.

## The helper script

The skill ships one script, `bin/difftour.py` in the skill directory (the directory this SKILL.md lives in, called `<skill dir>` below), with the page layout beside it in `bin/difftour_html.py`, `assets/` and the vendored `vendor/prism`. It needs only git and python3.

A run uses three modes:

```
difftour.py --setup <target>                                        Part 2: resolve the target, create the working directory, write the numbered diff
difftour.py --assemble OUT.html <ARGS from setup> ++ <working dir>  Part 4: lay the fragments out as the tour
difftour.py --cleanup <working dir>                                 Part 4: remove the copy of the toured code, as the last step
```

Three more modes exist for tests, for checking a tour by hand, and for a worker that has lost a hunk from its context. A normal run never calls them:

```
difftour.py [--untracked] -- <git diff args>          the numbered diff, what --setup writes to diff.txt
difftour.py --ids [--untracked] -- <git diff args>    one marker line per hunk
difftour.py --only h17,h20 -- <git diff args>         just those hunks
```

In the numbered diff, every hunk gets a marker line `### h17  path/to/file.rb:42` right before its `@@` line. A file without a text hunk (binary, mode change, pure rename) gets one marker of its own. From then on, everybody refers to hunks by their id.

## The target tour structure

Keep this in your head at all times, in every role. It describes the shape of the finished document. It is not a data structure that travels between agents: the orchestrator hands out topic titles, beat ideas and hunk ids, and gets back HTML fragments.

A **topic** is the unit the orchestrator makes and a worker narrates. On the page, each topic is rendered as a **chapter**; the tour summary and the loose ends are chapters too. Orchestrator and workers say "topic"; the page and the reader say "chapter".

```
Tour # The entire tour report, one HTML file
+ headline: string   # written by the orchestrator
+ summary: html      # written by the orchestrator, while the workers run
+ topics: Topic[]    # in reading order; each becomes one chapter

Topic # One cohesive topic or "body of work" in the diff range. One fragment file.
+ title: string
+ summary: html      # one paragraph, see "Narrate for a reader who zooms" in Part 5
+ beat_ideas: string[]  # drafted by the orchestrator, refined by the worker
+ beats: Beat[]
+ topic_hunks: HunkId[]
+ shared_hunks: Set<HunkId>  # hunks of this topic that another topic also shows; no direction, both show it

Beat # One narration beat within a topic
+ title: string
+ prose: html        # always present
+ beat_hunks: Hunk[]

Hunk # One annotated diff hunk
+ id: string                 # h17, minted by the script
+ sentence: html             # always present, in a <p>; one sentence
+ heat_level: 'skip' | none | 'note' | 'fishy' | 'hot'  # one word in the placeholder
+ heat_reason: text          # the heat explanation; required for note, fishy and hot; lives in the placeholder
+ focus: text[]              # rare: quoted blocks of lines a reader must not miss; comments after the placeholder
+ dim: text[]                # rare: quoted blocks of lines a reader of this topic can pass over
+ diff_content: text         # spliced in by the script, never typed by an agent
+ path: string
+ starting_line_number: integer
```

Prose is HTML: a paragraph is `<p>`, inline code is `<code>`. Markdown is not rendered.

# Part 2: Orchestrator, from input to fan-out

You read this part if you are the orchestrator. Do the steps in order.

## The human must provide the diff range

If the human did not specify what diff to tour, or if the arguments are exactly `help`, `--help` or `-h`, print this block verbatim and then exit.

```
diff-tour — a narrated walkthrough of a code change

Usage: /diff-tour [target]

Target:
  dirty         All unstaged and untracked changes
  staged        All staged changes
  uncommitted   All dirty and staged changes
  branch        The current branch vs its branch point off origin's default branch
  <git range>   e.g. main..HEAD, abc123..def456
  <commit>      e.g. HEAD~1, or a commit SHA
  <branch>      compared against origin's default branch
  <number>      a PR or MR in this repo
  <PR/MR URL>   a GitHub pull request or GitLab merge request

The report is one self-contained HTML file.

Needs git and python3 (3.10+). Nothing to install.
```

## One setup command

Everything mechanical before the clustering happens in **one script call**, run from inside the repository:

```
<skill dir>/bin/difftour.py --setup <target>
```

It first fetches origin, which is read-only: it refreshes what the repository knows about origin's branches and moves no local branch and no file. Then it resolves the target exactly as the help text lists them (a branch is compared against **origin's** default branch from its merge base, never against a local main or master that may be stale; a PR or MR is fetched from the origin remote into a local ref, never checked out, so local changes are safe), creates the working directory with twelve empty topic folders in it, and writes the numbered diff. It never pulls, merges, rebases or checks out; those are the human's to do. The working directory is a uniquely named folder inside the repository's `tmp/` if it has one (Rails apps do), otherwise in the system temp dir; two tours never share a folder, and a tour never numbers its own files. It prints:

```
WORK=/home/me/app/tmp/diff-tour.sLxCWm          the working directory; fragments and the tour go here
ARGS=-- 9b1f3c2a7e4d..feature/x                 paste this into --assemble in Part 4, verbatim
BASE=origin/main  (fetched now; local main is 12 behind)      what the branch is compared against
TIP=feature/x  (local; 2 ahead of and 3 behind origin/feature/x)   the branch being toured
SRC=/home/me/app/tmp/diff-tour.sLxCWm/src  (a copy of feature/x)   where code outside the diff is read
COMMITS:                                        the commit list, or "(none: working tree)"
...
STAT:                                           git diff --stat
...
TOPICS=topic-01 topic-02 ... topic-12           the empty topic folders inside WORK
DIFF=/home/me/app/tmp/diff-tour.sLxCWm/diff.txt  (1527 lines, 61 hunks)
ASK: Tour these 7 commits on feature/x against origin/main? Your branch is 2 ahead of and 3 behind origin/feature/x.
OPTION: Tour these 7 commits | the local branch as it is, including 2 unpushed commits
OPTION: Tour origin/feature/x instead | the pushed state, 3 commits you do not have locally => --setup origin/feature/x
OPTION: Stop | pull or rebase first, then start the tour again
```

The script covers the common cases and can fail at the edges: a branch name that does not exist, a PR number the origin remote does not serve, a repository with no default branch, an empty diff. It then prints one line saying what went wrong and exits non-zero. **Make one attempt to fix what that line names, then run the command again. If it fails a second time, stop and ask the human.** Do not resolve targets by hand, and do not run `git diff` yourself.

The commit list is a hint, not the plan. In a perfect world, commits would already tell a narrated story, but often we see something different:

- There might be random "WIP"-style commits without a coherent topic
- There might be a giant mother of all commits, mixing all sorts of topics
- There might be dozens of micro commits that are too fine-grained to tell a digestible story
- A commit might be topic-pure, but the topic is too large to ingest in one gulp for a human
- There might be a mix of good and bad commit styles

So glance at the commit list in case it does give a good signal. The final selection of topics is deferred to a scan of the entire diff.

## Confirm the commits with the human

A tour built on the wrong range costs minutes to generate and then misleads a review, so the range is confirmed before anything else happens. When the setup output contains an `ASK:` line, put that question to the human with the question widget, **before reading the diff**; the question and the wait cost nothing against any budget, the clustering budget starts after the Read: the `ASK:` text followed by the commit list is the question (up to about fifteen commits in full, then "and N more"), and each `OPTION:` line is one choice, the text before `|` its label and the text after it its description. You compose nothing yourself: the script has already worked out which branches differ from origin and what the alternatives are.

Then act on the answer:

- An option that ends in `=> --setup <target>`: run that setup command and treat its output the same way. Its question is normally a one-click confirmation of the commits the human has now seen. Follow at most one such option per tour; if the second run offers another, stop and tell the human what the script found.
- "Tour these N commits": continue with the `WORK` directory of the run that asked.
- "Stop": end with one line saying nothing was generated and why. The human pulls, rebases or pushes at their own pace; you never do any of that for them.

A run that asks and is then abandoned leaves an empty working directory in `tmp/`; leave it. Working-tree targets print no `ASK:` line, since there is no commit list to get wrong; continue straight to the diff.

## Read the full diff

The numbered diff is in `$WORK/diff.txt`. **Read that file with the Read tool**, not by printing it in a shell: a shell result is capped and a long diff would be truncated, saved elsewhere and read back in pieces, which is three calls where one will do. The Read tool's limit is tokens, not lines, and a diff is token-dense: expect roughly one Read per 1000 to 1300 diff lines. The `DIFF=` line gives the line count. Read with offsets, back to back, nothing in between, until you have seen the last line of the file.

Every hunk has a marker line `### h17  path:line` before it. From here on, everybody refers to hunks by that id. A marker ending in `(moved: 30 of 40 lines)` says git found those lines moved from elsewhere in the diff, within the file or from another one; such a hunk is usually preparation or fallout rather than a topic of its own. Binary files show up as a marker with no diff body. For those you only need to know that they were added, changed, removed or moved, which the file header tells you.

## Generate a list of topics

Now that you have seen the commits and the full diff, you probably have some ideas what kind of work happened there. Turn this into a list of thematically cohesive topics ("bodies of work") that covers the diff.

**This step is an investment.** Before you cut topics, explore the concepts the whole change stands on: the models, mechanisms and parts of the architecture that several topics touch, how they are built in this repository and how they fit together. Read them under `SRC`. Your **clustering budget** is 3 tool calls, from the Read of the diff until you fork the workers. Spend it where the diff alone does not show how those concepts work, and none where it does. Every worker inherits what you read here, so explore what is shared once, here, and leave what belongs to one topic to its worker.

For each topic, list some sub-topics, content examples or significant edit motions that make up that topic. These are the seed for the beats a worker will form; remember them with the topic (`topic.beat_ideas`).

### On finding topics

1. A topic is a reason, not a place. Changes in four files belong together if they exist for the same reason. Two changes in one file belong apart if they don't.
2. Name it as a change, not a location. Good: "thread the tenant id into the cache key". Bad: "changes to cache.py", "misc", "backend".
3. Assign by this test: if this topic were reverted, would this line disappear from the diff? If yes, it belongs to that topic. Do not ask "does my explanation mention it": a topic's explanation can be finished while twenty of its changes are still unassigned.
4. Never group by file type, directory, or tests-vs-code. A test belongs with the behaviour it tests. A doc belongs with the change it describes.
5. Do not take topics from commit messages. Read them for hints, then verify against the diff. Commit boundaries are usually wrong.
6. If a change fits no topic, you have probably missed a topic; name the missing one. A "miscellaneous" bucket is never a substitute for clustering. The one exception is the loose-ends topic described under *Assign hunks to topics*, which collects the few hunks that remain after honest clustering.
7. Never split a topic to make it shorter. Twelve changes that only make sense together are one topic of twelve.

### Reading order

Order the topics so that each one relies only on things the reader has already seen: foundations (settings, data model) before the mechanisms that use them, mechanisms before the surfaces built on them, surfaces before operational edges. The test, applied while you write the list: if the reader must know X to follow topic B, X's topic comes first. The tour summary you write later supplies the top-down motivation, so the topics can afford to be bottom-up.

Three kinds of work have a fixed place in that order, and each topic's summary should name which kind it is, so a reader can decide to skip it:

- **Preparatory work**, refactorings and extractions that exist to make the main change possible, goes immediately before the topic it prepares, so the reader meets the reason one chapter later. If it is small, it is the first beat of the topic it enables rather than a topic of its own.
- **Clean-up work**, removals and simplifications the main change made possible, goes right after the topic that made it dead: as that topic's last beat when small, as the next topic when large.
- **Unrelated changes**, work that shares the diff but not the reason (a typo fix, a dependency bump, a drive-by rename), go after the main body and before the loose ends, and their summary says in its first sentence that they are unrelated. Single unrelated hunks with no siblings are loose ends.

## Assign hunks to topics

For each hunk, decide which topic it belongs to, and assign it to the topic with the most apparent affinity. A hunk can belong to several topics (when one code range was touched by several bodies of work); it is then shown once per topic, and each worker is told so. There is no primary topic: the order in which the topics share it does not matter to anything, both workers show it and both say so. **Above about 60 lines, show a shared hunk once**: assign it to the topic where it matters most, and tell the other topics' workers on their "Shared with" line to link to it rather than place it, `Shared, shown in topic 3, link only: h24`. A 300-line spec printed three times helps nobody.

**The hunk is the floor.** Clustering is by reason, but the assembler cannot split a hunk, so a hunk that serves two reasons goes to the topic whose reason dominates, and the other topic's worker refers to it by link where its own story needs it. Expect a beat now and then that can show only part of what it describes; say so in the beat prose rather than forcing the hunk in twice.

A hunk that fits no topic in a glance goes to the **loose ends** topic: the last topic in reading order, holding whatever remains after honest clustering. It gets a worker like any other topic. Leave it out entirely if it is empty. Do not spend a call or invent a topic to avoid it.

Write the assignment down as ids, one line per topic, in reading order, loose ends last, numbered 1 to N without gaps. The numbers are final: they name the directories, the chapters on the page, and the link targets workers use to refer to each other's topics. This is what the workers get, so keep it compact:

```
1. Thread the tenant id into the cache key: h3 h4 h9 h10 h11 h17
2. Drop the legacy CSV export: h1 h2 h5-h8
3. Loose ends: h12 h40
```

## Fork the workers (the fan-out)

Fork one worker per topic. Large topics get a dedicated worker. Several small topics can go to one worker; that worker writes them into one fragment, in reading order.

Every worker gets its own directory, `<working dir>/topic-<NN>/`, one of the twelve the setup command created and listed on its `TOPICS=` line, numbered by the first topic the worker holds and zero-padded so the shell sorts them in reading order. If a tour has more than twelve topics, create the missing directories in one `mkdir` before forking. The worker writes exactly one file there, `fragment.html`, and never looks anywhere else. Workers cannot see each other's output, so they have nothing to react to.

Forks inherit your context, so a worker already holds the numbered diff. Do not paste hunks into the fork prompt. The prompt is short and always has the same shape. Its first line is fixed; it is what tells the fork that it is a worker and that *Part 5: Worker, during fan-out* is its instruction set:

```
You are a diff-tour worker. Your instructions are Part 1 and Part 5 of the diff-tour skill.

Topics in order: 1 Add the tenant column; 2 Thread the tenant id into the cache key; 3 Drop the legacy CSV export; 4 Loose ends
Topic 2: Thread the tenant id into the cache key
Beat ideas: the key builder; the two call sites; the backfill migration
Hunks: h3 h4 h9 h10 h11 h17
Shared with topic 3: h9 h11
Write your fragment to: /home/me/app/tmp/diff-tour.sLxCWm/topic-02/fragment.html
```

The "Topics in order" line is the same for every worker; it is what lets a worker link to another topic by number.

For a worker holding several topics, repeat the block from "Topic N" through "Shared with" once per topic, in reading order, under one "Write your fragment to" line; the directory is named after the first topic. That does not skew the numbering: the script numbers chapters by `<h2>` order across all fragments, so a fragment in `topic-05/` holding topics 5 and 6 yields chapters 5 and 6, and the directory number only sorts the fragment into place. That is the whole briefing. Nothing about assembling, nothing about other topics, no path other than the worker's own file.

What a worker does with this briefing is described in *Part 5: Worker, during fan-out*. Fork all workers in one message, then go straight on to Part 3 without waiting for them.

# Part 3: Orchestrator, during fan-out

You read this part if you are the orchestrator and the workers are running.

## Write the tour summary while the workers run

**This step is an investment.** It runs while the workers do, so the time you spend here costs the tour nothing until they are done. Before you write, list your doubts: every statement the summary is about to make that you have not grounded, such as why the change was made, what nearby behaviour it leaves alone, or whether the old code did what its names and tests claim. Then check them, one call each, the one that would mislead the reader most first, reading under `SRC`. Keep going while ungrounded doubt remains and your **summary budget** of 5 tool calls lasts; stop early only when nothing ungrounded is left. Doubts the budget did not reach go into the summary as doubts. Then think the spectrum of solutions through before you write it.

The workers need two to three minutes. You are idle for all of it, so this is when you write the opening fragment, `<working dir>/00-intro.html`: the `<h1>` headline and the tour summary. It is the widest zoom level of the tour and the one piece of prose that puts the whole change in context.

**The whole summary is at most 600 words**, the before/after table's cells not counted. It is an optional lead chapter: a reader who wants the context reads it, and one who does not skips straight to the first topic, at the start or half-way through. So every heading stands on its own, and none prepares the next. A summary of 944 words once read as a wall of text; that is the length this limit keeps out. Short paragraphs, and a `<ul>` with one line per item where you would otherwise write "first, second, third" inside a paragraph. `<strong>` may open a list item. The before/after table is a plain `<table>` with `<tr>`, `<th>` and `<td>`. No other markup, no emojis.

Like all prose in the tour, the summary follows *Writing the tour* in Part 1; the rules below come on top. **The rule against listing what the code shows matters most here**, because at this zoom level the reader has no diff beside the prose to anchor names to. Describe what a solution or a mechanism changes about the system, never the classes, methods or files it would touch. "Trusted devices become records instead of a cookie" is a mechanism; a list of the six classes that would change is not.

The fragment has this shape. It is the only fragment with an `<h1>`, and that is how the script recognises it; its headings never become chapters. **The headings are fixed text, copy them verbatim**: the script adds a one-line byline under the spectrum heading and under each of the three solutions, the same on every tour, so a returning reader knows the labels at a glance. You write only the paragraphs.

```html
<h1>Tour headline</h1>

<h2>The problem</h2>
<p>...</p>

<h2>What changes</h2>
<table>
  <tr><th>Before</th><th>After</th></tr>
  <tr><td>...</td><td>...</td></tr>
</table>

<h2>Not changed, deliberately</h2>
<ul><li>...</li></ul>

<h2>How it was built</h2>
<ul><li><strong>Mechanism.</strong> ...</li>...</ul>

<h2>The spectrum of solutions</h2>

<h3>The minimal solution</h3>
<p>... <strong>Buys:</strong> ... <strong>Costs:</strong> ...</p>

<h3>The maximal solution</h3>
<p>... <strong>Buys:</strong> ... <strong>Costs:</strong> ...</p>

<h3>The evaporating solution</h3>
<p>... <strong>Buys:</strong> ... <strong>Costs:</strong> ...</p>

<h3>Where this change sits</h3>
<p>...</p>
```

### The problem

One paragraph, at most 80 words, about the world *before* this change: what was wrong or missing, for whom, what it cost them, and what constraint shaped the solution that follows. End it with the one sentence that is the whole change in a breath: "The identity provider, which knew the moment the person left, had no way to tell Cards." The page sets this paragraph larger than body copy; it is the only part of the tour whose job is to make the reader care. For a user-facing change, what a user could not do or had to work around. For a refactoring, what was hard, slow or risky to work on, and for whom. For a performance change, what was slow and where that showed. It never describes the solution; the table under the next heading does that. The test for every sentence: if it could be a row in that table, it is one, and it comes out of this paragraph. If you cannot name a problem the change solves, say so; that is a finding.

### What changes

A **before/after table**: one row per behaviour that a user, an API consumer or the data itself would notice, at most eight rows, each cell a phrase. Rows are behaviours someone can observe ("booking a taken parking spot crashed with a server error" / "rejected with a validation message"), never files, classes or methods. A change nobody outside the code can observe, a pure refactoring, gets the single line "Nothing a user or API sees changes" instead of a table.

### Not changed, deliberately

A bullet list of what the change leaves alone that a reviewer would otherwise wonder about: a notification not sent, a check not applied, a path not touched, a scope the author drew a line around. Each bullet names the thing, then says briefly what still happens there, so the reader learns the prevailing behaviour, not just that it prevails. Use two short sentences rather than one long one with a semicolon: "No Slack notification for an admin booking. The user finds it on their dashboard, as before." One bullet per item, at most six. It answers those questions before the reviewer carries them through nine chapters. Leave the whole heading out if there is nothing to say.

### How it was built

At most 100 words. The mechanisms that carry the change, one list item each, and nothing before the list: no lead sentence. As many as there really are, typically two to four; do not pad to three or merge two real ones to reach three. A change with one mechanism gets one sentence, not a list of one. Tests are never a mechanism: they are expected with every change and belong to the chapter of what they test, so "added tests" or "covered by specs" is not a bullet here. If nothing of substance is left to say, stop; do not invent a bullet to fill the list. "Three mechanisms carry the load" tells the reader what they are about to read instead of reading it, and every such lead has been drivel. If the mechanisms interact in a way the bullets cannot show, say so in one sentence *after* the list, where it has something to point at. This is the mental model a reader needs before the chapters make sense: the shape of the solution, not a list of what was touched.

### The spectrum of solutions

The most useful thing a tour can give a reviewer is a sense of where this solution sits among the solutions that were possible. This part is worth the most thought: before choosing, think through several genuinely different approaches for each heading and discard the weaker ones. Where it helps, look at how this repository does things today, so the alternatives are grounded in this codebase rather than generic; those calls come from the summary budget.

If the workers return before you are done, finish the summary, then assemble. Never hand the reader a partial spectrum; two solutions and a missing third reads as a judgement that there is no third.

Lay out three alternatives, an exercise borrowed from [Caleb Porzio's deconstructed pull requests](https://calebporzio.com/), under the three fixed headings above, **at most 60 words each**: what the alternative changes about the system, what it buys, what it costs.

- **The minimal solution.** The smallest patch that gets by: minimal blast radius, possibly incomplete scope, possibly code nobody would be proud of.
- **The maximal solution.** The pure, fundamental fix that solves the problem completely, restructuring other parts of the system where they stand in the way, to leave a thorough and harmonious new world.
- **The evaporating solution.** A change somewhere else in the system that makes the problem not arise in the first place.

Each of the three has to be a realistic, workable change to *this* repository, one a competent colleague could propose in a design meeting. Not a strawman: the maximal solution may be heavy and risky, but it does not rewrite the codebase in another language, and the evaporating solution has to name the actual place the problem would evaporate from.

**Each solution is one paragraph in three parts**, so the reader can weigh the three against each other at a glance: a description of one to three sentences, then `<strong>Buys:</strong>` with one to three strengths, then `<strong>Costs:</strong>` with one to three weaknesses, all in one flowing paragraph. Strengths and weaknesses are phrases, not sentences: "two lines, no migration" or "every reader still leaks". The page tints the strengths green and the weaknesses red, label included, so the two labels have to be exactly these; the script recognises them.

Then, under **Where this change sits**, at most 80 words: which of the three the toured change is closest to, where it deviates, and what that position means for the reviewer. A minimal change invites the question "what did it leave out"; a maximal one invites "was all of this necessary"; a change that sits between them invites both, at the seams. It comes last because it refers to the three the reader has just met.

The spectrum is context, not judgement. You are not saying the author chose wrong. You are giving the reviewer the room the author was standing in when they chose.

## Then wait, silently

When the summary is written and workers are still running, wait. The harness wakes you when a worker returns; there is nothing to check in between and nothing to report. Do not post progress messages such as "four of seven have returned"; each one is a turn spent on nothing.

# Part 4: Orchestrator, after fan-out

You read this part if you are the orchestrator, the tour summary is written, and you are waiting for or have received the workers' returns.

## Collect the workers

Wait for every worker, silently; the harness wakes you as each one returns. A worker returns its fragment path when it is done. Trust that return: a worker that returned a path has written its file. A worker that errored out, or returned without a path, is replaced by forking one new worker for its topic with the same briefing; do not touch the other workers' directories.

## Assemble the tour

Assemble in one command, pasting the `ARGS=` value from the setup command verbatim:

```
<skill dir>/bin/difftour.py --assemble <working dir>/diff-tour.html <ARGS> ++ <working dir>
```

Given the working directory, the script takes every `.html` file under it in path order, which puts `00-intro.html` first and the workers' `topic-NN/fragment.html` after it in reading order; the output file itself is skipped. The script splices every placeholder, and appends any hunk no fragment placed in a final "Unsorted hunks" chapter, listing those ids on stderr. That is the completeness rule, enforced without anyone re-reading the diff. It also lists placeholders that name no hunk, and hunks placed more than once; the latter is expected for shared hunks.

A few unplaced hunks are acceptable: they are shown at the end, and forking a replacement for them would keep the human waiting. Lines starting `line mark:` are informational: a worker's focus or dim block that the script could not place; the mark is simply absent from the page, and nothing needs doing. If the unplaced list is long and its hunks all belong to one topic, that worker's fragment is missing; fork a replacement for that topic and assemble again. Never edit a fragment by hand.

## Clean up

When the last assemble is done, remove the copy of the toured code:

```
<skill dir>/bin/difftour.py --cleanup <working dir>
```

It removes only the copy the setup made, and does nothing for `dirty` and `uncommitted` tours, which read the repository itself. Run it once, after any replacement and second assemble, and before the hand-over.

## Hand over the tour

Your final message is two lines, three at most, in this order:

```
<one or two sentences, only if something exceptional happened during the run>
Say the word and I will open it in your browser.
file:///tmp/diff-tour.sLxCWm/diff-tour.html
```

The first line exists only for the exceptional: trouble obtaining the diff, a worker that had to be replaced, hunks that ended up unsorted. Unplaced line marks never count. The message does **not** summarise the tour and does **not** point at code worth a closer look; the page does both, with far better presentation, and every extra line makes the URL harder to find. In the normal case the message is the offer and the URL.

**Always a `file://` URL, never a bare path.** A URL is what the terminal turns into a link the human can click; a path is not. The assemble command prints the URL in exactly this form as the first thing on its result line; copy it from there. The URL is the last line of the message, alone, with nothing after it.

**Do not open the tour yourself.** Wait for the human to say yes; then run the platform's opener (`xdg-open` on Linux, `open` on macOS, `start` on Windows) on the URL. That is the end of the tour.

# Part 5: Worker, during fan-out

**You are a worker if, and only if, your prompt begins with "You are a diff-tour worker."** Then Part 1 and this part are your entire instruction set. Parts 2 to 4 describe the orchestrator's steps and are not yours; the only thing you take from them is the numbered diff you already hold in your context.

What a worker never does, no matter what it notices:

- It does not fork or spawn any agent. There is no situation in which a worker needs help.
- It does not list, read or write anything outside its own directory. Other workers' directories and the working directory itself are not its business.
- It does not re-read the diff, does not cluster topics, does not reassign hunks, does not renumber anything.
- It does not assemble the tour, does not run the helper script's `--assemble` mode, and does not fix what it thinks other workers got wrong.
- It does not write more than one file.

If your briefing seems wrong (a hunk id that is not in the diff, a topic that does not fit), narrate what you can and say so in one sentence in your return message. Do not go looking for the answer.

The steps below are in the order you do them. Read them once, then work.

## Explore your topic's concepts

**This step is an investment.** Before you form beats, list your doubts about your topic, such as how a concept works in this repository, why the change does something, or whether the code does what its names and tests claim. The orchestrator's reading is in your context already; do not repeat it. Then check your doubts, one call each, the one that would mislead the reader most first, reading under `SRC`. Keep going while ungrounded doubt remains and your **worker budget** of 3 tool calls lasts; stop early only when nothing ungrounded is left. When there are more doubts than calls, check the most dangerous ones and state the rest as doubts in your prose.

You already have every hunk in context from the numbered diff; never spend a call re-reading it. Once you start forming beats, you make no more calls.

## Form the narration beats

Form a list of narration beats that help the human understand the topic in smaller portions. The beat ideas in your briefing are a draft from the orchestrator; refine them, do not feel bound by them.

A good beat is a group of the topic's hunks that represents a (rather) self-contained idea, edit motion or programmer intent. Separate preparatory work from the main change. Separate clean-up work from the main change. Do not group by location or file type. Assign each of your hunks to exactly one beat.

## Narrate for a reader who zooms

A hurried reader reads the chapter summaries and stops, a careful one opens the beats, and only the most careful opens the hunks. Each slot below follows *Writing the tour* in Part 1, and adds its own rules.

**Chapter summary** (the paragraph under your `<h2>`). At most 60 words. It answers: what does this body of work achieve, what is the one decision in it if there is one, and which beat carries the weight when that is not obvious? A reader who stops here must know what changed and whether to read on. Say which kind of work it is when that helps the reader skip: preparation for a later chapter, clean-up after an earlier one, or unrelated to the main change.

**Beat prose** (the paragraph under your `<h3>`). At most 40 words. It answers: what do these hunks do together, and how does this step follow from the one before? End on whether the hunks need reading: where the weight lies, or that nothing surprising waits below. For a beat of tests: in one clause what they cover, in one clause what they do not.

**Hunk sentence** (the paragraph after each placeholder). Always present, also on skip hunks. One sentence, at most 20 words. It says what the hunk is, so the reader knows what they would be opening: "The migration adding the three 2FA columns", not the three column names. When a hunk is trivial, a phrase is its whole sentence: "The renamed factory trait." When it only follows from another hunk, say that and nothing more: "The call sites of the rename above." If your briefing says a hunk is shared with another topic, say so in a few words. Why a hunk deserves attention is its heat explanation's job, not this sentence's.

**Heat explanation** (the text after a note, fishy or hot level, shown under its label). One or two sentences, at most 40 words. It says why the hunk deserves its level, never what the hunk is; the hunk sentence says that. Its rules are in *Give each hunk a heat level*.

**Refer to other topics and hunks in your own words, as links.** Free prose is better than titles, and a link makes it exact: `<a href="#topic-4">the locking chapter</a>`, `<a href="#h17">the migration</a>`. Topic numbers are on the "Topics in order" line of your briefing; hunk ids are in the diff. A nickname without a link leaves the reader guessing which of eight sidebar entries you meant.

## Give each hunk a heat level

Every hunk gets one of five heat levels. A level is a reading instruction: it tells the human how carefully to read the hunk, not whether the change is right. Readers use it to triage: they skip skip hunks, skim read hunks, and read note, fishy and hot hunks fully. In a hurry they drop note as well, but never fishy or hot.

| Level | Written as | Means |
|---|---|---|
| skip | `<!-- hunk h17 skip -->` | nothing to decide or fear; trust the sentence |
| read | `<!-- hunk h17 -->` | ordinary code; one attentive pass |
| note | `<!-- hunk h17 note: heat explanation -->` | the reader has a decision to make |
| fishy | `<!-- hunk h17 fishy: heat explanation -->` | something here does not add up |
| hot | `<!-- hunk h17 hot: heat explanation -->` | this hunk decides something costly |

Take the highest level whose description fits. A factor lowers a level only when the diff or a check establishes it, never on assumption. Do not classify by file type or by the area of code a hunk sits in; weigh what the hunk itself does.

**Hot: this hunk decides something costly, and a subtle mistake in that decision would be irreversible, or silent and wide.** The hunk must contain the decision itself: the condition that grants access, the query that selects what gets deleted, the amount that gets charged, the list of who receives an email, the filter that decides what leaves the system in an export. Hot is about cost, not suspicion: a correct payment call is still hot. The renamed variable next to it is not, and neither is a moved method, a log line or wiring in payment or auth code; a mistake there fails loudly or does not matter. A broken public method that raises at once is not hot either: the mistake announces itself.

**Fishy: something here does not add up.** The code contradicts itself, its own names or comments, its tests, the goal of the change, or how the framework actually works. A guard whose name says it blocks something that the framework's semantics let through. A test whose title claims more than its assertions prove. Two hunks that expect different things of the same method. An assumption about the codebase that the code around it seems to contradict. Fishy is the one level that may rest on a hunch, when something feels off before you can say why. Its heat explanation always ends with how far you got: checked, not checked, or a hunch.

**Note: the reader has a decision to make.** Either the change takes a decision the reader should accept knowingly, or it raises one of the questions they read for (see *Your basic job*). A note names what is different from before; a property the code already had is not a note.

Its heat explanation first says what the consequence is if nothing more changes, then asks the question the reader decides: "Inactive admins are now erased like everyone else. Should they be kept?" If you cannot put a decision into such a question, it is not a note; use read. A real decision is a non-rhetorical question with several answers a competent colleague could defend. If every answer but one is absurd, the hunk only does the obvious thing; use read. If your own explanation concludes that nothing needs deciding, such as "harmless here", drop the badge. And one decision gets one badge: when several hunks share it, only the hunk where it is taken gets the note, and the others stay read.

Where each of the reader's questions shows, and how to write it:

- **An assumption the change stands on.** The badge goes on the hunk where the belief is decided, and the heat explanation says how far it reaches: "the eight hunks in this chapter follow from it". Note it when the assumption is plausible but decisive; when it looks wrong, it is fishy. The hunks that follow from it stay cool: if the root is right, they are right.
- **Code in the wrong place.** The badge goes on the hunk that puts code where it does not belong or grows a module past its purpose; say where the code belongs or what could be extracted.
- **More code than the job needs.** The badge goes on the verbose hunk; say the proportion: "about 80 lines for what reads like a 20-line job".
- **Edge-case code.** The badge goes on the hunk that handles the case; name the case and when it occurs, so the reader can decide whether it is worth its lines.
- **No precedent.** The badge goes on the hunk that introduces the style; say in one clause what the repository or the ecosystem usually does instead.
- **A better approach.** The badge goes on the hunk where that approach would have applied; say in one clause which approach would have avoided the code or the edge cases.
- **A behaviour decision.** A default that changes behaviour for everyone, a deliberately omitted case, a new limit, a new dependency, an important behaviour no test covers, or a test removed that was the only check of a behaviour. The badge goes on the hunk that takes the decision.

**Skip: nothing to decide or fear, and a reader loses nothing by trusting your sentence.** Lockfiles, schema dumps, generated code, a rename carried through its call sites, `include` lines, locale strings, and any hunk that exists only because another hunk does. Skip saves the reader the most time, so use it wherever it is true, and only there: when in doubt, read.

**Read: ordinary hand-written code that needs one attentive pass.** The default for every hunk that fits none of the descriptions above. A misleading name or a small nit belongs here, with a word in the hunk sentence if it matters.

**Note, fishy and hot each carry a heat explanation**, one or two sentences written into the placeholder after the colon. It says why the hunk deserves this level: what goes wrong if it is wrong, what does not add up, or what the reader has to decide. It does not say what the hunk does; the hunk sentence says that. A second sentence adds a second reason, not detail on the first. When a hot hunk also does not add up, that second reason says what, and how far it was checked. `hot: a missing cast here lets the desk check fail open, and no error or test would show it`, not `hot: the line that switches the check on`. Plain text, no HTML, no `--` inside. Skip and read have no explanation.

## Mark lines inside a hunk

Heat levels help a hurried reader choose which hunks to read. Marks help the same reader inside a hunk they cannot read whole: they say which lines to spend the time on and which to leave out. Every line of a hunk falls into one of three tiers, told apart by what a reader does with it:

- **Focus** is for the reader who can spend only a few lines on this hunk. These lines they must see.
- **Unmarked** is for the reader who reads the hunk but not every line. These lines they need in order to understand what the change does.
- **Dim** is for the reader deciding what to leave out. These lines they can skip and still understand the change, because the name or the shape of the run already tells them what is there.

Marks follow from decisions you have already made, so they cost no tool call and a moment per hunk. Ask once per hunk: would a hurried reader read this whole? A hunk short enough to take in at a glance needs no marks. For every other hunk, whatever its level, place the focus and the dims together. Skip hunks get no marks at all; the reader trusts the sentence.

**Focus marks the essentials.** Ask: if the reader read only these lines, would they get what the change does? Mark the lines that make the answer yes: the line that does the thing, the condition that decides, the new call, the changed value, the assignment that carries the new state. Usually one range of one to five lines. A read hunk gets its focus like any other; the level says how carefully to read the hunk, the focus says where to start. In a note, fishy or hot hunk the focus also covers the lines the reason is about, always, so a badge always comes with a strip in the gutter; when those are not the same lines as the essentials, mark both. A reason about the hunk as a whole, or about an absence, adds no range, and the essentials still get theirs. Never more than three ranges in one hunk, and never a whole hunk.

**Dim marks what can be skipped.** Ask of each run of lines: if the reader skipped this, would they misunderstand the change? Where the answer is no, dim the run. It is no for a helper that does what its name says, a trivial transformation that maps, formats or builds a hash, a URL or a path, setup and teardown, wiring and registration, a thin delegation, a rename or signature change echoed down a file, and the part of a shared hunk that belongs to another topic. Code that merely moved, within a file or between files, is dimmed by the script without your help; a hunk's marker line says how much of it moved, `(moved: 30 of 40 lines)`, and a hunk that is mostly moved code is usually a skip. It is yes wherever the change's behaviour is decided: a condition or guard, a write or a delete, the call that does the thing, error handling that picks an outcome. Those lines stay unmarked, however dull they look. A run of five lines counts as much as a run of fifty, several dims in one hunk are normal, and together they tell the reader: the substance of this hunk is what you can still see. Only closing braces, `end`, blank lines and a lone import are not worth a mark; a programmer scans those without help. A dim covers the whole run or nothing, never a sample of it. It may cover most of a hunk when the rest is the point; a hunk that could be dimmed entirely is a skip. Never dim a whole hunk.

Marks say where to look, not what is right: a dim run is not "fine" and a focus range is not "wrong", the heat reason carries that.

### How to write a mark

A mark is a comment after the hunk's placeholder. Inside it, quote the lines to mark, whole and contiguous, exactly as they stand in the numbered diff and in its order, `-` and `+` lines interleaved as the diff shows them; the `+`/`-` column and the indentation do not matter, and `<` and `&` stay as they are. The script finds the block in the hunk and marks those lines. Given this hunk:

```
### h24 app/models/user.rb:31
@@ -31,5 +31,9 @@ class User
   def validate_authentication_code_with_user
-    totp.verify(authentication_code)
+    totp.verify(
+      authentication_code.delete(" "),
+      drift_behind: 30,
+      drift_ahead: 30,
+    )
   end
```

the mark is:

```html
<!-- hunk h24 hot: the accept-or-reject decision for every code -->
<!-- focus:
+      drift_behind: 30,
+      drift_ahead: 30,
-->
<p>...</p>
```

A dim is written the same way with `dim:`. For a long run, quote its first and last lines with `[...]` alone on a line between them; the script marks everything from the one to the other, so a run of eighty lines costs you two or three quoted lines:

```html
<!-- dim:
  before do
[...]
  end
-->
```

The range is inclusive: the dim covers both quoted ends and everything between them. To dim a group of methods, end on the last method's closing line, never on the first line of the method after it.

A focus inside a dim run is fine: the script cuts the dim around the focused lines, so a long sweep is one dim from its first line to its last, with its essential lines focused inside.

Quoting the lines is all it takes in nearly every case. Only when the very same lines could stand twice in the hunk, a lone `end` or `raise`, a repeated generated line, add `@N` with the line number of your block's first line, counting from 1 at the line below `@@`: in the hunk above `end` is line 8, so `<!-- focus @8: end -->`. Count carefully; the script uses the number only to choose between the matches and takes the nearest. Never quote more lines than you mean to mark: a mark covers exactly the lines quoted.

## Write the topic fragment

Write the whole topic as one HTML fragment to the path you were given. One `Write`, no re-reading. The content of every paragraph follows *Narrate for a reader who zooms*; the placeholders follow *Give each hunk a heat level*. This is the shape:

```html
<h2>Topic title</h2>
<p>Chapter summary.</p>

<h3>Beat title</h3>
<p>Beat prose.</p>

<!-- hunk h3 -->
<p>One sentence.</p>

<!-- hunk h4 fishy: what does not add up, in one or two sentences, ending with how far you checked -->
<p>One sentence.</p>

<!-- hunk h5 skip -->
<p>One sentence.</p>

<!-- hunk h6 hot: a wrong early return here lets every request through unchallenged -->
<!-- focus:
  return unless current_user
  return if exempt?(current_user)
-->
<p>One sentence.</p>

<h3>Next beat</h3>
...
```

A fragment holds only `<h2>`, `<h3>`, `<p>`, `<code>`, links of the form `<a href="#topic-N">` or `<a href="#hNN">`, hunk placeholders, and the focus and dim comments described in *Mark lines inside a hunk*. No numbers in headings, no `<section>`, no ids, no styling, nothing else: the script numbers chapters by fragment order and builds the sidebar, and anything you add there is stripped or, worse, disagrees with it.

- **Never type out a diff.** Put the placeholder where the hunk belongs. The assembler replaces it with the real, escaped, highlighted diff and its `path:line`. Typing the hunk yourself is slower, and a `<` in the code would break the page. The only diff text in a fragment is the few lines quoted inside a focus or dim comment, which the script uses only to find the range.
- Every hunk id you were given appears exactly once as a placeholder.
- The paragraph **after** a placeholder is that hunk's sentence, rendered right above its diff. The prose **before** the first placeholder of a beat is the beat's prose and sits beside the hunks.
- A worker holding several topics writes one `<h2>` block per topic, in the order of its briefing, into the same fragment.

## You are done

Once `fragment.html` is written, you are done. Return to the orchestrator with the fragment path, plus one sentence only if your briefing seemed wrong. Then exit. Do not wait for other workers, do not check on them, do not verify the assembly, do not start anything else. The fragment is the deliverable and the orchestrator takes it from here.
