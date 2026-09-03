---
name: vibe-tour
description: >-
  Helps a human review a code change they did not write.
metadata:
  version: 1.0.0
disable-model-invocation: true
---

# Vibe Tour

## Your basic job

Oh no! Your human just received a ton vibe-coded changes to this repository. They are tasked to review that code and take responsibility for it.

What a thankless job! Luckily, they have you. You will provide the human with a narrated tour through that steaming pile of code, highlighting some possible fishy changes in the process.

**Narration**: Your tour must help the human follow and understand a large change by presenting smaller pieces in a logical order. For this you will cluster the hunks of a provided diff range into cohesive topics, find a human-friendly reading order and add some narration prose.

**Fishiness:** You will tag each diff hunk with a "fishiness" factor. This is just your feeling / "Spidey sense" whether something *might* be wrong with this diff, and is worth a second look. This is not a code review! You will not verify your suspicion, that would take way too long. The fishiness badge is a quick and cheap vibes check to let the human know to take a closer look. If we print a wrong fishiness badge, no worries: Verification and judgement remains with the human.

### What is NOT your job

**You are not the reviewer**. While you will share your own feelings and suspicions during the narration ("fishiness"), final judgement will be made by the human.

**You are not a code review skill**. You will only learn a shallow understanding of the diff, only enough to provide orientation, narration and fishiness tags. There are other skills (like `/code-review`) who are better at verifying changes deeply.

**You are not a teacher**. You can assume that the human has basic competence in this repository, its programming language and frameworks, and understand most of the pre-existing functionality. The human will also understand this new chance once you transformed an alphabetically ordered wall of diff into a narrated tour.

## Tour generation needs to be lightning fast

A regular git diff prints in a second. Your tour is only useful to the human when you can generate it in a few minutes at most.

**Generation speed is the most important consideration in your work**, more important than narration quality and verification depth. You will take shortcuts, make compromises, limit tool calls and ration reasoning hops to provide the tour faster.

The only rule where we don't compromise is: Every hunk of the diff must be shown somewhere in the tour.

This skill works best in a fast model. In Claude Code this would be Sonnet, not Opus. If you can detect the current model and it's not fast, ask the human if they want to switch models, or run this skill in a sub-agent with a different model. If the human insists on keeping a strong but slow model, you let them.

This skill uses parallel agents aggressively to cut down generation time. This skill explicitly allows you to fork agents and spawn sub-agents, you don't need the humans permissions for this. The instructions below define the exact moments when we fork or spawn other agents.

## Tour format is HTML

The tour will *not* be printed to this session.
Instead you deliver the tour as self-contained HTML file.

## The target tour structure

Keep this in your head at all times. The tour will at first be a skeleton, with more and more properties being filled as the process continues.

```
Tour # Container for the entire tour report, will be converted to HTML
+ headline: string
+ summary: markdown
+ topics: Topic[]

Topic # One cohesive topic or "body of work" in the diff range
+ summary: markdown
+ beat_idea: string[]
+ beats: Beat[]
+ topic_hunks: Hunk[]

Beat # One narration beat within a topic
+ summary: markdown
+ beat_hunks: Hunk[]

Hunk # One annotated diff hunk
+ description: markdown # describes what is done in that hunk
+ fishiness_level: 'low' | 'medium' | 'high'
+ fishiness_reason: markdown # only for high fishiness
+ diff_content: text # in diff patch format or similiar
+ path: string
+ starting_line_number: integer
```

## The human must provide the diff range

If the human did not specificy what diff to tour, or if the arguments are exactly `help`, `--help` or `-h` print this block verbatim and then exit.

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

## Ensure need local access to the diff range

Make sure the provided diff range is available in a git repository on the local filesystem.

If the diff range is remote (e.g. GitHub PR), you might need to fetch or check out a branch. Abort when this would destroy local changes.

## Get an overview

Before we ingest the full diff, let's get some initial overview.

List all commits in the diff range, in a single command, but don't trust it completely.
In a perfect world, commits would already tell a narrated story, but often we see something different:

- There might be random "WIP"-style commits without a coherent topic
- There might a giant mother of all commits, mixing all sorts of topics
- There might be dozens of micro commits that are too fine-grained to tell a digestable story
- A commit might be topic-pure, but the topic is too large to ingest in one gulp for a human
- There might be a mix of good and bad commit styles

So we check the commit log in case it does give a good signal. But our final selection of `Topic`s is deferred to a scan of the entire diff.

Also retrieve a list of all changed files, in a single command, e.g. `git diff --stat BASE HEAD`.

## Read the full diff

Read the complete diff top to bottom. You will eventually need to hold the entirely diff in your context, so no point of doing a partial diff. Only do batches if there is a hard technical limitation that prevents you from digesting the entire diff in one go.

We can excempt binary files from the full diff reading.
For binary files we only need to know that they were added, changed, removed or moved.

## Generate a list of topics

Now that you've seen the commits and the full diff, you probably have some ideas what kind of work happened there.
Turn this into a list of thematically cohesive topics ("clusters", "stories", "body of work") that categorizes most of the diff.

Don't do a deep analysis to generate the list of topics.
You have a maximum budget of 10 tool calls to understand any of concepts changed in the diff. Focus on key questions you have, and only ask for the purpose of clustering hunks into topics. Don't stress if open questions remain, just work on intuition for those.

For each topic, list some sub-topics or content examples or signficant edit motions that make up that topic. These will be the idea seed for the "beat generation" in the next step. Remember these sub-topics with the topic (`topic.beat_ideas`).

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
Every hunk must be assigned to at least one topic. A hunk can be assigned to multiple topics (e.g. when one code range was touched multiple times by several topics).

Don't do a deep analysis to assign hunks to topics. In particular, don't pay additional tool calls to better understand the codebase. When you're unsure, assign based on intuition.

## Fork agent workers to process topics in parallel

Fork multiple agents (called "workers" from here on). Each worker will narrate a topic.

Large topics should get a dedicated worker. Multiple small topics can be grouped into a single worker.

## Worker instructions per topic

Every forked worker starts with a topic that contains:

- A topic title
- Some ideas for narration beats
- A list of hunks assigned to this topic

### Get a cursory understanding of your hunks

A worker has a maximum budget of 5 tool calls to better understand a topic's hunks.
Use these tool calls only to get a cursory, shallow understanding of what was changed in this topic, and only for the purpose of providing a better narration. Use the limited budget wisely, and focus on key questions. Work on intuition for everything else.

### Finalize narration beats

Start by finalizing a list of "narration beats" that will help the human understand the topic diff in smaller portions. You can use the provided beat ideas as a starting point, but know that they were only a draft from a previous step. Now that we're in a parallelized worker, we can take a little more time to refine the beat and improve readability.

To find a good narration beat, try to find groups of topic hunks that represent (rather) self-contained ideas, edit motions or programmer intents.
Separate preparatory work from the main change. Separate clean up work from the main change. Do not group by location or file type.

Assign each topic hunk to exactly one narration beat.

Don't do a deep analysis to assign hunks to beats. In particular, don't pay additional tool calls to better understand the codebase. When you're unsure, assign based on intuition.

### Narrate each beat

Narrate each beat like this:

````
### Beat title

Summary of what happens in this beat, across all hunks.

Hunk1 description:

    Diff of hunk1
    
Hunk2 description:

    Diff of hunk2

...
    
Hunk_N description:

    Diff of hunk_N
```

### Tag each hunk with fishiness factor

Tag each diff hunk with a "fishiness" level, which is one of:

- "low": Probably OK
- "medium": Some bad vibes, but nothing concrete
- "high": Doesn't feel great, please have a closer look, human

This is not a code review! This is a quick and cheap "Spidey sense" whether something *might* be wrong with this diff. The fishiness badge is a quick and cheap vibes check to let the human know to take a closer look.

Do not verify any of your suspician, work on intuition and what you already know about the code base.

If we print a wrong fishiness badge, no worries: Verification and judgement remains with the human.

Examples for "low" fishiness:

- An internal method was renamed. We may assume that an agent or human as adapted callers.
- A test for another code change (we assume it passes).
- Any changes clearly downstream of another change.
- Trivial preparatory work or clean-up work.

Examples for "high" fishiness:

- Code changes that doesn't seem to fit with what you learned so far about this code base
- Clear typos
- A public and commonly used API was changed in a backwards incompatible way, and unless all callers were adjusted, consequences would be high
- Shaped like vulnerable code (e.g. XSS injections)
- Significant changes for which you have seen no test coverage so far

Examples for "medium" fishiness:

- Anything between low and high

Only when you tag "high" fishiness, you also generate a short explanation what it is that feels off. If you can't say, just say "Please check this change".


### Add summaries

The beat summary is the summary of all its hunks.

The topic summary is the summary of all its beats.


### Return topic to the orchestrating agent

Now that you have finished narrating and tagging all topic hunks, return the completed topic back to the orchestrating agent.


## Print the tour

Once all workers have terminated, the orchestrating agent now prints the tour as a simple HTML file.

At this stage of this skill, the HTML file is super simple. Use only built-in HTML elements, no CSS styling, no syntax highlighting, no JavaScript.


