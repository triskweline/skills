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

**Fishiness:** You will tag each diff hunk with a "fishiness" factor. This is just your feeling / "Spidey sense" whether something *might* be wrong with this diff, and is worth a second look. This is not a code review! You will not verify your suspicion, that would take way too long. The fishiness badge is a quick and cheap vibes check to let the human know to take a closer look. If we print a wrong fishiness badge, no worries: Verification and judgement remains with the human.

### What is NOT your job

**You are not the reviewer**. While you will share your own feelings and suspicions during the narration ("fishiness"), final judgement will be made by the human.

**You are not a code review skill**. You will only learn a shallow understanding of the diff, only enough to provide orientation, narration and fishiness tags. There are other skills (like `/code-review`) who are better at verifying changes deeply.

**You are not a teacher**. You can assume that the human has basic competence in this repository, its programming language and frameworks, and understands most of the pre-existing functionality. The human will also understand this new change once you transformed an alphabetically ordered wall of diff into a narrated tour.

## Tour generation needs to be lightning fast

A regular git diff prints in a second. Your tour is only useful to the human when you can generate it in a few minutes at most.

**Generation speed is the most important consideration in your work**, more important than narration quality and verification depth. You will take shortcuts, make compromises, limit tool calls and ration reasoning hops to provide the tour faster.

The only rule where we don't compromise is: Every hunk of the diff must be shown somewhere in the tour. A script enforces this at the end, so you never have to re-read the diff to check.

This skill uses parallel agents aggressively to cut down generation time. This skill explicitly allows you to fork agents and spawn sub-agents, you don't need the human's permission for this. The instructions below define the exact moments when we fork or spawn other agents.

### Check the model before you do anything else

This skill is meant to run on a fast model. In Claude Code that is Sonnet, not Opus.

Do this check **first**, before the help text, before any git command. The reason: the workers you fork later inherit the model of the agent that forks them. Once a slow model has read the diff, there is no way to switch the workers to a fast one. The only moment to change the model is now.

Your system prompt names the model you are running on. If it is a fast model, carry on and say nothing. If it is a slow model (in Claude Code: Opus), stop and give the human this choice:

1. **Switch and re-run.** The human switches the session to a fast model (`/model sonnet` in Claude Code) and invokes `/vibe-tour` again. This is the cleanest option.
2. **Delegate the whole skill.** You spawn one sub-agent on a fast model and hand it the entire skill run: the target, the working directory, and these instructions. Its forks inherit the fast model. You wait for it, then relay the path of the finished tour. A sub-agent cannot ask the human anything, so before delegating, you resolve the help text and make sure the diff range is local (see below) yourself.
3. **Stay on the slow model.** If the human insists, you let them, and carry on here.

## Tour format is HTML

The tour will *not* be printed to this session.
Instead you deliver the tour as one self-contained HTML file.

The file is assembled from **fragments**: each worker writes the HTML for its topic into its own file, the orchestrating agent writes the opening fragment, and a script concatenates them. Nobody ever re-reads a fragment, and nobody ever types out a diff hunk: fragments name hunks by id, and the script splices the real diff bytes in when assembling.

At this stage of this skill, the HTML is super simple. Use only built-in HTML elements, no CSS styling, no syntax highlighting, no JavaScript.

## The helper script

The skill ships one script, `bin/vibe-hunks.py` in the skill directory. It needs only git and python3. It has four modes, all taking the same `git diff` arguments after a `--`:

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
+ fishiness_level: 'low' | 'high'
+ fishiness_reason: markdown # required for high, absent for low
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

## Create the working directory

Create one directory for this tour, outside the repository, e.g. `mktemp -d -t vibe-tour.XXXXXX`. Every fragment and the finished tour go in there. Remember the path; the workers need it.

## Get an overview

Before we ingest the full diff, let's get some initial overview.

List all commits in the diff range, in a single command, but don't trust it completely.
In a perfect world, commits would already tell a narrated story, but often we see something different:

- There might be random "WIP"-style commits without a coherent topic
- There might be a giant mother of all commits, mixing all sorts of topics
- There might be dozens of micro commits that are too fine-grained to tell a digestible story
- A commit might be topic-pure, but the topic is too large to ingest in one gulp for a human
- There might be a mix of good and bad commit styles

So we check the commit log in case it does give a good signal. But our final selection of `Topic`s is deferred to a scan of the entire diff.

Also retrieve a list of all changed files, in a single command, e.g. `git diff --stat BASE HEAD`.

## Read the full diff

Read the complete, numbered diff top to bottom in one command:

```
<skill dir>/bin/vibe-hunks.py [--untracked] -- <git diff args>
```

Do not run a plain `git diff` as well. You will eventually need to hold the entire diff in your context, so there is no point in doing a partial diff. Only do batches if there is a hard technical limitation that prevents you from digesting the entire diff in one go.

Binary files show up as a marker with no diff body. For those we only need to know that they were added, changed, removed or moved, which the file header tells you.

## Generate a list of topics

Now that you've seen the commits and the full diff, you probably have some ideas what kind of work happened there.
Turn this into a list of thematically cohesive topics ("clusters", "stories", "body of work") that categorizes most of the diff.

Don't do a deep analysis to generate the list of topics.
You have a maximum budget of 10 tool calls to understand any of the concepts changed in the diff. The three initial commands (the commit list, the changed files, the numbered read) do not count against it. Everything after that counts, including any further git command. Focus on key questions you have, and only ask for the purpose of clustering hunks into topics. Don't stress if open questions remain, just work on intuition for those.

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

Large topics should get a dedicated worker. Multiple small topics can be grouped into a single worker.

Forks inherit your context, so a worker already holds the numbered diff. Do not paste hunks into the fork prompt. Give each worker only:

- The topic title and its number in reading order
- Some ideas for narration beats
- The list of hunk ids assigned to this topic
- Which of those hunks another topic also shows, and which one: `Shared with topic 3: h9 h11`. The worker mentions this in one sentence where the hunk appears.
- The fragment path to write: `<working dir>/topic-<NN>.html`, zero-padded so the shell sorts them in reading order

## Worker instructions per topic

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

### Tag each hunk with fishiness factor

Tag each diff hunk with a "fishiness" level, which is one of:

- "low": I would not stop here.
- "high": Stop here, human, and this is why.

There is no middle level on purpose. A badge that asks for attention always says what to look at, and a badge that does not is just "low". When you are torn, ask yourself whether you can name what feels off in one phrase. If you can, it is "high". If you cannot, it is "low".

This is not a code review! This is a quick and cheap "Spidey sense" whether something *might* be wrong with this diff. The fishiness badge is a quick and cheap vibes check to let the human know to take a closer look.

Do not verify any of your suspicion, work on intuition and what you already know about the code base.

If we print a wrong fishiness badge, no worries: Verification and judgement remains with the human.

Examples for "low" fishiness:

- An internal method was renamed. We may assume that an agent or human has adapted callers.
- A test for another code change (we assume it passes).
- Any changes clearly downstream of another change.
- Trivial preparatory work or clean-up work.

Examples for "high" fishiness:

- Code changes that doesn't seem to fit with what you learned so far about this code base
- A typo that can change behaviour: an identifier, a hash key, a config key, a route, a string that something else compares against. Typos in comments and prose are low.
- A public and commonly used API was changed in a backwards incompatible way, and unless all callers were adjusted, consequences would be high
- Shaped like vulnerable code (e.g. XSS injections)
- Significant changes for which you have seen no test coverage so far

Every "high" badge comes with a short explanation what it is that feels off, one phrase or one sentence. No explanation, no "high".

### Write the topic fragment

Write the whole topic as one HTML fragment to the path you were given. One `Write`, no re-reading. This is the shape:

```html
<section id="topic-1">
<h2>1. Topic title</h2>
<p>Topic summary: what this body of work does, across all its beats.</p>

<h3>1.1 Beat title</h3>
<p>Summary of what happens in this beat, across all hunks.</p>

<p>Description of hunk h3.</p>
<!-- hunk h3 -->
<p><strong>Fishiness: low</strong></p>

<p>Description of hunk h4.</p>
<!-- hunk h4 -->
<p><strong>Fishiness: high</strong> — What feels off, in one or two sentences.</p>

<h3>1.2 Next beat</h3>
...
</section>
```

The rules that matter:

- **Never type out a diff.** Put `<!-- hunk h17 -->` where the hunk belongs. The assembler replaces it with the real, escaped diff and its `path:line` caption. Typing the hunk yourself is slower, and a `<` in the code would break the page.
- Every hunk id you were given appears exactly once as a placeholder.
- Each placeholder is preceded by its description and followed by its fishiness line.
- The topic summary is the summary of all its beats. The beat summary is the summary of all its hunks.

Once the file is written, return to the orchestrating agent with two things only: the fragment path, and the topic summary in one or two sentences. Nothing else; the fragment is the deliverable.

## Assemble the tour

Once all workers have returned, write the opening fragment `<working dir>/00-intro.html`: the `<h1>` headline, a summary paragraph built from the topic summaries the workers returned, and a `<ul>` table of contents linking to `#topic-1`, `#topic-2`, and so on in reading order.

Then assemble, in one command:

```
<skill dir>/bin/vibe-hunks.py --assemble <working dir>/vibe-tour.html [--untracked] -- <git diff args> ++ <working dir>/*.html
```

The shell glob puts `00-intro.html` first and the topics after it in reading order. The script splices every placeholder, and appends any hunk no fragment placed in a final "Unsorted hunks" section, listing those ids on stderr. That is the completeness rule, enforced without anyone re-reading the diff.

If the script reports unplaced hunks, that is acceptable for speed: they are shown. Only if the list is long, or the hunks clearly belong to one topic, write them into that topic's fragment with a one-line description each and run the assemble command again.

Tell the human the path of the finished file. That is the end of the tour.
