---
name: vibe-tour
description: >-
  A fast, narrated tour of a code change for a human reviewer, tuned for generation speed over
  depth. Clusters the diff into topics and narration beats, shows every hunk, and gives each hunk
  a gut-feel heat level, from "skip" through "fishy" to "hot", instead of a verified finding. Use
  when someone says "vibe-tour this branch", wants a quick walkthrough of a large or vibe-coded
  change, or finds diff-tour too slow for the change at hand. Not a code review: it points, the
  human judges.
metadata:
  version: 2.0.0
disable-model-invocation: true
---

# Vibe Tour

This skill has five parts. Part 1 is background for everyone. Parts 2 to 4 are the orchestrator's steps, in order. Part 5 is the workers' instructions. The words **orchestrator**, **worker** and **fan-out** are defined in Part 1; the part titles are how you find your place.

# Part 1: Background and rules for everyone

## Your basic job

Oh no! Your human just received a ton of vibe-coded changes to this repository. They are tasked to review that code and take responsibility for it.

What a thankless job! Luckily, they have you. You will provide the human with a narrated tour through that steaming pile of code, marking the places that deserve a closer look.

**Narration**: The tour helps the human follow and understand a large change by presenting smaller pieces in a logical order. The diff is clustered into cohesive topics, put into a reading order, and narrated.

**Heat**: Every hunk gets a heat level, from "a tool could have written this, skip it" through "this may be wrong" to "a mistake here would be silent or irreversible, read every line". A level is a first-read feeling, a "Spidey sense", and is worth exactly a second look. This is not a code review! Nothing is verified, that would take way too long. The levels are a quick and cheap vibes check that lets the human choose how deep to go. If a level is wrong, no worries: verification and judgement remain with the human. The five levels are defined in *Give each hunk a heat level* in Part 5.

### What is NOT your job

**You are not the reviewer**. You share feelings and suspicions; the human makes the final judgement.

**You are not a code review skill**. You learn only a shallow understanding of the diff, enough for orientation, narration and heat levels. Other skills (like `/code-review`) verify changes deeply.

**You are not a teacher**. The human has basic competence in this repository, its language and frameworks, and understands most of the pre-existing functionality. They will understand this change once you have turned an alphabetically ordered wall of diff into a narrated tour.

## Who does what: orchestrator, workers, fan-out

The **orchestrator** is the agent the human invoked. It resolves the target, reads the diff, clusters it into topics, and then **fans out**: it forks one **worker** agent per topic (or per group of small topics). Each worker narrates its topic into one HTML fragment and exits. While the workers run, the orchestrator writes the tour summary. When all workers have returned, the orchestrator assembles the fragments into the tour and hands the human a URL.

A forked worker inherits the orchestrator's whole context, including this skill. Its prompt begins with a fixed sentence that tells it it is a worker. Part 1 applies to both roles. Parts 2 to 4 are the orchestrator's alone. Part 5 is the workers' alone.

**The orchestrator may fork agents without asking the human. Workers never fork or spawn anything.**

## Tour generation needs to be lightning fast

A regular git diff prints in a second. Your tour is only useful to the human when you can generate it in a few minutes at most.

**Generation speed is the most important consideration in your work**, more important than narration quality and verification depth. You take shortcuts, make compromises, limit tool calls and ration reasoning hops to deliver the tour faster.

The one rule we don't compromise on: every hunk of the diff is shown somewhere in the tour. A script enforces this at the end, so nobody has to re-read the diff to check.

### The three budgets

Every tool call is a full model turn, so tool calls are budgeted. There are three budgets, and every mention of a budget in this skill refers to one of them by name:

- **Clustering budget**: 10 tool calls, for the orchestrator. Starts after the setup command and the Read of the diff file. Stops when the workers are forked.
- **Spectrum budget**: 10 tool calls and about 3 minutes of reasoning, for the orchestrator. Starts when the workers are forked. Stops when the tour summary is written.
- **Worker budget**: 5 tool calls, per worker. Starts when the worker begins. Stops when it writes its fragment.

## Tour format is HTML

The tour is *not* printed to this session. It is one self-contained HTML file, opened in a browser.

The file is assembled from **fragments**: each worker writes a plain HTML fragment for its topic into its own directory, the orchestrator writes the opening fragment with the tour summary, and a script lays them out. Nobody ever re-reads a fragment, and nobody ever types out a diff hunk: fragments name hunks by id, and the script splices the real diff bytes in when assembling.

Everything that makes the page pleasant is mechanical and costs no agent tokens: the script numbers the chapters, puts a beat's prose beside its hunks in two columns, highlights the diffs, and adds viewed marks and a theme switch. From the level in each placeholder, the page's own JavaScript draws a **heat strip** per chapter in the sidebar, one coloured square per hunk in reading order, and gives the legend a **mark viewed** button for skip, read and note, so a reader can fold away whole levels and be left with fishy and hot.

## The helper script

The skill ships one script, `bin/vibe-hunks.py` in the skill directory (the directory this SKILL.md lives in, called `<skill dir>` below), with the page layout beside it in `bin/vibe_html.py`, `assets/` and the vendored `vendor/prism`. It needs only git and python3.

A run uses two modes:

```
vibe-hunks.py --setup <target>                                        Part 2: resolve the target, create the working directory, write the numbered diff
vibe-hunks.py --assemble OUT.html <ARGS from setup> ++ <working dir>  Part 4: lay the fragments out as the tour
```

Three more modes exist for tests, for checking a tour by hand, and for a worker that has lost a hunk from its context. A normal run never calls them:

```
vibe-hunks.py [--untracked] -- <git diff args>          the numbered diff, what --setup writes to diff.txt
vibe-hunks.py --ids [--untracked] -- <git diff args>    one marker line per hunk
vibe-hunks.py --only h17,h20 -- <git diff args>         just those hunks
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
+ shared_hunks: Map<HunkId, TopicId>  # hunks of this topic that another topic also shows

Beat # One narration beat within a topic
+ title: string
+ prose: html        # always present
+ beat_hunks: Hunk[]

Hunk # One annotated diff hunk
+ id: string                 # h17, minted by the script
+ sentence: html             # always present, in a <p>; one sentence, up to three for note/fishy/hot
+ heat_level: 'skip' | none | 'note' | 'fishy' | 'hot'  # one word in the placeholder
+ heat_reason: text          # required for note, fishy and hot; lives in the placeholder
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
vibe-tour — a narrated walkthrough of a code change

Usage: /vibe-tour [target]

Target:
  dirty         All unstaged and untracked changes
  staged        All staged changes
  uncommitted   All dirty and staged changes
  branch        The current branch vs its branch point off the default branch
  <git range>   e.g. main..HEAD, abc123..def456
  <commit>      e.g. HEAD~1, or a commit SHA
  <branch>      compared against the repo's default branch
  <number>      a PR or MR in this repo
  <PR/MR URL>   a GitHub pull request or GitLab merge request

The report is one self-contained HTML file.

Needs git and python3 (3.10+). Nothing to install.
```

## One setup command

Everything mechanical before the clustering happens in **one script call**, run from inside the repository:

```
<skill dir>/bin/vibe-hunks.py --setup <target>
```

It resolves the target exactly as the help text lists them (a branch is compared against the default branch from its merge base; a PR or MR is fetched from the origin remote into a local ref, never checked out, so local changes are safe), creates the working directory with twelve empty topic folders in it, and writes the numbered diff. The working directory is a uniquely named folder inside the repository's `tmp/` if it has one (Rails apps do), otherwise in the system temp dir; two tours never share a folder, and a tour never numbers its own files. It prints:

```
WORK=/home/me/app/tmp/vibe-tour.sLxCWm          the working directory; fragments and the tour go here
ARGS=-- 9b1f3c2a7e4d..feature/x                 paste this into --assemble in Part 4, verbatim
COMMITS:                                        the commit list, or "(none: working tree)"
...
STAT:                                           git diff --stat
...
DIFF=/tmp/vibe-tour.sLxCWm/diff.txt  (1527 lines, 61 hunks)
```

The script covers the common cases and can fail at the edges: a branch name that does not exist, a PR number the origin remote does not serve, a repository with no default branch, an empty diff. It then prints one line saying what went wrong and exits non-zero. **Make one attempt to fix what that line names, then run the command again. If it fails a second time, stop and ask the human.** Do not resolve targets by hand, and do not run `git diff` yourself.

The commit list is a hint, not the plan. In a perfect world, commits would already tell a narrated story, but often we see something different:

- There might be random "WIP"-style commits without a coherent topic
- There might be a giant mother of all commits, mixing all sorts of topics
- There might be dozens of micro commits that are too fine-grained to tell a digestible story
- A commit might be topic-pure, but the topic is too large to ingest in one gulp for a human
- There might be a mix of good and bad commit styles

So glance at the commit list in case it does give a good signal. The final selection of topics is deferred to a scan of the entire diff.

## Read the full diff

The numbered diff is in `$WORK/diff.txt`. **Read that file with the Read tool**, not by printing it in a shell: a shell result is capped and a long diff would be truncated, saved elsewhere and read back in pieces, which is three calls where one will do. The Read tool takes up to 2000 lines per call; the `DIFF=` line told you how many calls that is. If it is more than one, read with an offset, back to back, nothing in between.

Every hunk has a marker line `### h17  path:line` before it. From here on, everybody refers to hunks by that id. Binary files show up as a marker with no diff body. For those you only need to know that they were added, changed, removed or moved, which the file header tells you.

## Generate a list of topics

Now that you have seen the commits and the full diff, you probably have some ideas what kind of work happened there. Turn this into a list of thematically cohesive topics ("bodies of work") that covers the diff.

Don't do a deep analysis. The **clustering budget** (10 tool calls, from now until the workers are forked) is for understanding concepts you need in order to cluster; spend it on key questions only, and work on intuition for the rest.

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

For each hunk, *quickly* guess which topic it belongs to, and assign it to the topic with the most apparent affinity. A hunk can belong to several topics (when one code range was touched by several bodies of work); it is then shown once per topic, and the worker is told so.

A hunk that fits no topic in a glance goes to the **loose ends** topic: the last topic in reading order, holding whatever remains after honest clustering. It gets a worker like any other topic. Leave it out entirely if it is empty. Do not spend a call or invent a topic to avoid it.

Write the assignment down as ids, one line per topic, in reading order, loose ends last. This is what the workers get, so keep it compact:

```
1. Thread the tenant id into the cache key: h3 h4 h9 h10 h11 h17
2. Drop the legacy CSV export: h1 h2 h5-h8
3. Loose ends: h12 h40
```

Don't do a deep analysis to assign hunks. In particular, don't pay tool calls to better understand the codebase. When unsure, assign on intuition.

## Fork the workers (the fan-out)

Fork one worker per topic. Large topics get a dedicated worker. Several small topics can go to one worker; that worker writes them into one fragment, in reading order.

Every worker gets its own directory, `<working dir>/topic-<NN>/`, one of the twelve the setup command created, numbered by the first topic the worker holds and zero-padded so the shell sorts them in reading order. If a tour has more than twelve topics, create the missing directories in one `mkdir` before forking. The worker writes exactly one file there, `fragment.html`, and never looks anywhere else. Workers cannot see each other's output, so they have nothing to react to.

Forks inherit your context, so a worker already holds the numbered diff. Do not paste hunks into the fork prompt. The prompt is short and always has the same shape. Its first line is fixed; it is what tells the fork that it is a worker and that *Part 5: Worker, during fan-out* is its instruction set:

```
You are a vibe-tour worker. Your instructions are Part 1 and Part 5 of the vibe-tour skill.

Topic 3: Thread the tenant id into the cache key
Beat ideas: the key builder; the two call sites; the backfill migration
Hunks: h3 h4 h9 h10 h11 h17
Shared with topic 5: h9 h11
Write your fragment to: /tmp/vibe-tour.sLxCWm/topic-03/fragment.html
```

For a worker holding several topics, repeat the block from "Topic N" through "Shared with" once per topic, in reading order, under one "Write your fragment to" line; the directory is named after the first topic. That is the whole briefing. Nothing about assembling, nothing about other topics, no path other than the worker's own file.

What a worker does with this briefing is described in *Part 5: Worker, during fan-out*. Fork all workers in one message, then go straight on to Part 3 without waiting for them.

# Part 3: Orchestrator, during fan-out

You read this part if you are the orchestrator and the workers are running.

## Write the tour summary while the workers run

The workers need two to three minutes. You are idle for all of it, so this is when you write the opening fragment, `<working dir>/00-intro.html`: the `<h1>` headline and the tour summary. It is the widest zoom level of the tour and the one piece of prose that puts the whole change in context.

**The whole summary is under 400 words.** The last tour's ran to 944 and read as a wall of text; a reader spent four minutes on it before the first chapter. Short paragraphs, and a `<ul>` with one line per item where you would otherwise write "first, second, third" inside a paragraph. `<strong>` may open a list item. No other markup, no emojis.

**The enumeration guard applies here too, and matters most here**, because at this zoom level the reader has no diff beside the prose to anchor names to. Describe what a solution or a mechanism changes about the system, never the classes, methods or files it would touch. "Trusted devices become records instead of a cookie" is a mechanism; a list of the six classes that would change is not.

The fragment has this shape. It is the only fragment with an `<h1>`, and that is how the script recognises it; its headings never become chapters. **The headings are fixed text, copy them verbatim**: the script adds a one-line byline under the spectrum heading and under each of the three solutions, the same on every tour, so a returning reader knows the labels at a glance. You write only the paragraphs.

```html
<h1>Tour headline</h1>

<h2>What this change achieves</h2>
<p>...</p>

<h2>How it was built</h2>
<p>...</p>
<ul><li><strong>Mechanism.</strong> ...</li>...</ul>

<h2>The spectrum of solutions</h2>

<h3>The minimal solution</h3>
<p>...</p>

<h3>The maximal solution</h3>
<p>...</p>

<h3>The evaporating solution</h3>
<p>...</p>

<h3>Where this change sits</h3>
<p>...</p>
```

### What this change achieves

At most 80 words. What is better after this change than before it, in the terms of whoever benefits. For a user-facing change, what a user can now do. For a refactoring, what became simpler, safer or faster to work on, and for whom. For a performance change, what got faster and where that shows. If the change has no benefit you can name, say so; that is a finding.

### How it was built

At most 100 words. The two or three mechanisms that carry the change and how they fit together, one list item each: the mental model a reader needs before the chapters make sense. Not a list of what was touched; the shape of the solution.

### The spectrum of solutions

The most useful thing a tour can give a reviewer is a sense of where this solution sits among the solutions that were possible. This part is worth real thought, and it has its own budget, the **spectrum budget**: up to 10 tool calls and about 3 minutes of reasoning, from the fork until the summary is written. The tool calls are for looking at how this repository does things today, so the alternatives are grounded in this codebase rather than generic.

The budget is the limit, not the workers. If they return before you are done, finish the spectrum within the budget, then assemble. Never hand the reader a partial spectrum; two solutions and a missing third reads as a judgement that there is no third.

Lay out three alternatives, an exercise borrowed from [Caleb Porzio's deconstructed pull requests](https://calebporzio.com/), under the three fixed headings above, **at most 60 words each**: what the alternative changes about the system, what it buys, what it costs.

- **The minimal solution.** The smallest patch that gets by: minimal blast radius, possibly incomplete scope, possibly code nobody would be proud of.
- **The maximal solution.** The pure, fundamental fix that solves the problem completely, restructuring other parts of the system where they stand in the way, to leave a thorough and harmonious new world.
- **The evaporating solution.** A change somewhere else in the system that makes the problem not arise in the first place.

Each of the three has to be a realistic, workable change to *this* repository, one a competent colleague could propose in a design meeting. Not a strawman: the maximal solution may be heavy and risky, but it does not rewrite the codebase in another language, and the evaporating solution has to name the actual place the problem would evaporate from.

Then, under **Where this change sits**, at most 80 words: which of the three the toured change is closest to, where it deviates, and what that position means for the reviewer. A minimal change invites the question "what did it leave out"; a maximal one invites "was all of this necessary"; a change that sits between them invites both, at the seams. It comes last because it refers to the three the reader has just met.

The spectrum is context, not judgement. You are not saying the author chose wrong. You are giving the reviewer the room the author was standing in when they chose.

# Part 4: Orchestrator, after fan-out

You read this part if you are the orchestrator, the tour summary is written, and you are waiting for or have received the workers' returns.

## Collect the workers

Wait for every worker. A worker returns its fragment path when it is done. Trust that return: a worker that returned a path has written its file. A worker that errored out, or returned without a path, is replaced by forking one new worker for its topic with the same briefing; do not touch the other workers' directories.

## Assemble the tour

Assemble in one command, pasting the `ARGS=` value from the setup command verbatim:

```
<skill dir>/bin/vibe-hunks.py --assemble <working dir>/vibe-tour.html <ARGS> ++ <working dir>
```

Given the working directory, the script takes every `.html` file under it in path order, which puts `00-intro.html` first and the workers' `topic-NN/fragment.html` after it in reading order; the output file itself is skipped. The script splices every placeholder, and appends any hunk no fragment placed in a final "Unsorted hunks" chapter, listing those ids on stderr. That is the completeness rule, enforced without anyone re-reading the diff. It also lists placeholders that name no hunk, and hunks placed more than once; the latter is expected for shared hunks.

A few unplaced hunks are acceptable for speed: they are shown. If the unplaced list is long and its hunks all belong to one topic, that worker's fragment is missing; fork a replacement for that topic and assemble again. Never edit a fragment by hand.

## Hand over the tour

Your final message is two lines, three at most, in this order:

```
<one or two sentences, only if something exceptional happened during the run>
Say the word and I will open it in your browser.
file:///tmp/vibe-tour.sLxCWm/vibe-tour.html
```

The first line exists only for the exceptional: trouble obtaining the diff, a worker that had to be replaced, hunks that ended up unsorted. The message does **not** summarise the tour and does **not** point at code worth a closer look; the page does both, with far better presentation, and every extra line makes the URL harder to find. In the normal case the message is the offer and the URL.

**Always a `file://` URL, never a bare path.** A URL is what the terminal turns into a link the human can click; a path is not. The assemble command prints the URL in exactly this form as the first thing on its result line; copy it from there. The URL is the last line of the message, alone, with nothing after it.

**Do not open the tour yourself.** Wait for the human to say yes; then run the platform's opener (`xdg-open` on Linux, `open` on macOS, `start` on Windows) on the URL. That is the end of the tour.

# Part 5: Worker, during fan-out

**You are a worker if, and only if, your prompt begins with "You are a vibe-tour worker."** Then Part 1 and this part are your entire instruction set. Parts 2 to 4 describe the orchestrator's steps and are not yours; the only thing you take from them is the numbered diff you already hold in your context.

What a worker never does, no matter what it notices:

- It does not fork or spawn any agent. There is no situation in which a worker needs help.
- It does not list, read or write anything outside its own directory. Other workers' directories and the working directory itself are not its business.
- It does not re-read the diff, does not cluster topics, does not reassign hunks, does not renumber anything.
- It does not assemble the tour, does not run the helper script's `--assemble` mode, and does not fix what it thinks other workers got wrong.
- It does not write more than one file.

If your briefing seems wrong (a hunk id that is not in the diff, a topic that does not fit), narrate what you can and say so in one sentence in your return message. Do not go looking for the answer.

The steps below are in the order you do them. Read them once, then work.

## Get a cursory understanding of your hunks

Your **worker budget** is 5 tool calls, from now until you write your fragment. Every tool call counts, including git. Use them only for a cursory, shallow understanding of what changed in this topic, and only where it makes the narration better. Focus on key questions; work on intuition for everything else.

You already have every hunk in context from the numbered diff. Do not spend a tool call re-reading it.

## Form the narration beats

Form a list of narration beats that help the human understand the topic in smaller portions. The beat ideas in your briefing are a draft from the orchestrator; refine them, do not feel bound by them.

A good beat is a group of the topic's hunks that represents a (rather) self-contained idea, edit motion or programmer intent. Separate preparatory work from the main change. Separate clean-up work from the main change. Do not group by location or file type. Assign each of your hunks to exactly one beat.

Don't do a deep analysis to form beats. Don't pay tool calls to understand the codebase for this. When unsure, decide on intuition.

## Narrate for a reader who zooms

The tour has three layers of prose, chapter, beat and hunk, and they are zoom levels. A hurried reader reads the chapter summaries and stops. A careful one opens the beats. Only the most careful opens hunks, and reading a hunk always costs more than reading a sentence about it. Every layer has the same job: **tell the reader what they would find one level down, well enough to decide whether to go there.** The layers overlap, and that is fine; a reader who zooms in expects to meet the same thing again, closer up.

What no layer does is spell the code out in prose: naming each column a migration adds, each key a settings block sets, each method a trait defines, each step a test takes. That is the diff again, only harder to read, and the real diff sits one glance below. The test for a sentence: after reading it, would the reader still want to open the diff? Good. Would they no longer need to? Then the sentence is doing the diff's job. Cut it.

**Chapter summary** (the paragraph under your `<h2>`). One paragraph. What this body of work achieves and the one decision in it, so a reader who stops here still knows what changed. Say which kind of work it is when that matters: preparation for a later chapter, clean-up after an earlier one, or unrelated to the main change. End with where the weight lies: the beat to open if they open only one.

**Beat prose** (the paragraph under your `<h3>`). Always present. What these hunks do together and why they are one step; how this step follows from the previous beat when it does. Give the gist of what the hunks would show, and say "nothing surprising below" when that is true. This is where a reader decides whether to open the hunks.

**Hunk sentence** (the paragraph after each placeholder). Always present, also on skip hunks. It says what the hunk is about so the reader knows what they would be opening, and for note, fishy and hot it says what to look for beyond the badge reason. If your briefing says a hunk is shared with another topic, say so here, in a few words.

Length follows the level. Skip and read: one sentence. Note, fishy and hot: up to three sentences, because the reader has been told to stop here and this is where you tell them why.

Whatever the length, never list what the hunk contains. Not the columns a migration adds, not the keys of a settings block, not the methods of a trait, not the steps of a test, not the sections of a template. "The migration adding the three 2FA columns", not the three column names and their types. "The four knobs that configure the feature", not the four keys in order. The reader has the diff one glance below; a sentence that lists its contents makes them read the change twice. For note, fishy and hot, the badge already carries the reason; do not repeat it, add to it if there is more.

## Give each hunk a heat level

Every hunk gets one of five heat levels. The scale is not "how suspicious" but **how carefully the human should read this**, and it has room for two things suspicion cannot express: code that looks fine but everything stands on, and code a tool wrote that nobody needs to read.

| Level | Written as | The reviewer | Your one question |
|---|---|---|---|
| skip | `<!-- hunk h17 skip -->` | trusts your sentence, does not read the diff | Could a tool have written this, or is it pure fallout of another hunk? |
| (none) | `<!-- hunk h17 -->` | reads once at normal speed | the default when no other question is a yes |
| note | `<!-- hunk h17 note: why -->` | reads, then consciously decides; your phrase says what | Is there a choice or a nit here the reviewer should knowingly accept? |
| fishy | `<!-- hunk h17 fishy: why -->` | verifies before approving | Can I name a specific way this is wrong? |
| hot | `<!-- hunk h17 hot: why -->` | reads line by line, however it looks | If this were subtly wrong, would the mistake be impossible to undo, or go unnoticed while affecting everyone? |

**Classify as a cascade, top down, and stop at the first yes: hot, fishy, note, skip, else no level.** Every question is answered from the hunk itself and what you already know. Most hunks fall through in a glance.

Hot is about the cost of a mistake, not about how important or how public the code is. A broken public method fails loudly and a revert fixes it; that is fishy at most, and if the method is rarely used it gets no level. Hot is an auth or permission check that would fail open silently, a verification that would accept bad input without complaint, a gate on every request, a data rewrite, a delete, a payment, a sent email. Do not classify by file type or by category of code; ask the question.

Note collects three things that all get the same reviewer action: nitpicks (naming, a hardcoded string, a stray comment, an unused dependency), decisions the author made that the reviewer must accept knowingly (a default that changes behaviour for everyone, a deliberately omitted exemption, an input limit), and missing coverage for something significant.

Skip is lockfiles, schema dumps, renames, `include` lines, locale strings, path helpers, and any hunk that exists only because another hunk exists. It is the one level that saves the reader time, so use it freely where it is true.

This is not a code review! You do not verify anything; work on intuition and what you already know about the code base. If a level is wrong, no worries: the judgement remains with the human.

**Note, fishy and hot each need a reason**, one phrase or one sentence, written into the placeholder after the colon. No reason, no badge. For hot the reason names what a mistake would cost: `hot: the gate on every request`. A hunk that is both hot and fishy is hot, and the reason carries the suspicion. Plain text, no HTML, no `--` inside. Skip never has a reason.

## Write the topic fragment

Write the whole topic as one HTML fragment to the path you were given. One `Write`, no re-reading. The content of every paragraph follows *Narrate for a reader who zooms*; the placeholders follow *Give each hunk a heat level*. This is the shape:

```html
<h2>Topic title</h2>
<p>Chapter summary.</p>

<h3>Beat title</h3>
<p>Beat prose.</p>

<!-- hunk h3 -->
<p>One sentence.</p>

<!-- hunk h4 fishy: what feels off, in one phrase or sentence -->
<p>One to three sentences.</p>

<!-- hunk h5 skip -->
<p>One sentence.</p>

<!-- hunk h6 hot: the gate on every request -->
<p>One to three sentences.</p>

<h3>Next beat</h3>
...
```

A fragment holds only `<h2>`, `<h3>`, `<p>`, `<code>` and hunk placeholders. No numbers in headings, no `<section>`, no ids, no styling, nothing else: the script numbers chapters by fragment order and builds the sidebar, and anything you add there is stripped or, worse, disagrees with it.

- **Never type out a diff.** Put the placeholder where the hunk belongs. The assembler replaces it with the real, escaped, highlighted diff and its `path:line`. Typing the hunk yourself is slower, and a `<` in the code would break the page.
- Every hunk id you were given appears exactly once as a placeholder.
- The paragraph **after** a placeholder is that hunk's sentence, rendered right above its diff. The prose **before** the first placeholder of a beat is the beat's prose and sits beside the hunks.
- A worker holding several topics writes one `<h2>` block per topic, in the order of its briefing, into the same fragment.

## You are done

Once `fragment.html` is written, you are done. Return to the orchestrator with the fragment path, plus one sentence only if your briefing seemed wrong. Then exit. Do not wait for other workers, do not check on them, do not verify the assembly, do not start anything else. The fragment is the deliverable and the orchestrator takes it from here.
