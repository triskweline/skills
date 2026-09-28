---
name: trim-code
description: >-
  Make a working change simpler and smaller, with fewer concepts for a reader to
  understand. Two fresh sub-agents gather ideas, one for missing structure (the same thing
  built twice, steps repeated with one difference, mechanisms more general than their
  uses, existing code that could serve the change) and one for local waste (checks nothing
  can trigger, wrappers that only forward). Apply the trims that keep the behavior and stay
  in proportion; bring larger refactorings of existing code and behavior cuts (unlikely
  edge cases, extras nobody asked for) to the human for approval. Use after implementing a
  change that works but is too much code for what it does, or when asked to trim, slim down
  or simplify a change.
---

# Trim code

Agent-written code often works but carries more concepts than its job needs: two
representations of the same thing, steps repeated with one difference, mechanisms more
general than their uses, checks nothing can trigger, options nobody asked for. The task
is to find what the diff can do without.

The measure is concepts a reader must understand first, lines of logic second. A diff can
lose whole concepts and barely get shorter; that is still the win. Count honestly: count
the concepts that disappear and the ones that appear, and go by the net. A new object,
representation or protocol is a concept. So is a **mode**: anything an abstraction
branches on so it can serve one more use, like a flag, an option or a type check. A mode
is worth it when it removes more than it adds, and not when it trades a small deletion for
a unit that is hard to reason about.

The large restructurings are the reason this skill exists, and existing code is in scope:
often the biggest win is existing code that now does the diff's work, or one abstraction
for the old and the new use instead of a second one next to it. Cleaning up existing code
the diff doesn't need is out of scope.

## Terms

- **The diff** is the code change you are trimming: a commit range or uncommitted work, as
  it was before trimming began.
- **Existing code** is code that existed before the diff: every line the diff neither adds
  nor modifies.
- **Intended behavior** is what the requirements, specifications or docs ask for, what
  tests pin down, and what code in this codebase uses. Anything else a piece of code does
  is free to change, including behavior that is clearly wrong. A detail nobody could
  sensibly rely on doesn't count either, even where a test happens to pin it down: the
  order of keys in a JSON object, whitespace, a typo in a message. A changed error type, a
  different error winning, or new keys in a response are not such details.
- **The obstruction sentence** ties an idea that touches existing code to the diff: "The
  diff needed X because existing code does, lacks or is shaped as Y; this idea makes one
  of them unnecessary by Z." X is concrete code in the diff: files and lines. The idea may
  delete either side, X or its counterpart in existing code, whichever fits the result
  worse. An idea without such an X is cleanup.

Five numbers describe what an idea costs and saves, as rough estimates in round numbers:

- **Diff savings:** the lines of logic the idea deletes from the diff.
- **Existing savings:** the lines of logic it deletes in existing code.
- **Total savings:** diff savings plus existing savings.
- **Existing churn:** the lines of existing code it modifies or adds to. Every line counts,
  including renames and updated call sites. Code the idea writes inside the diff doesn't
  count: the human reviews the result anyway.
- **Concept gain:** the concepts it removes, minus the ones it adds (see the intro).

**The ratio** limits how much existing code an idea pulls into the diff: its existing churn
may be at most about twice its diff savings. An idea earns its place among the trims by
shrinking the diff, so existing savings don't count toward the ratio; everywhere else they
count as part of total savings. Clearly more is over the ratio; close is within it.

## Three lists

Every idea ends up on one of three lists, or is killed.

- **L1 trims** keep the intended behavior, verifiably. They either touch no existing code,
  or touch it within the ratio and with an obstruction sentence. A bug fix is a trim when
  it is certain: a concrete input violates a requirement you can quote, and the fix is
  local in the diff. Trims are always applied, without asking.
- **L2 refactorings** keep the intended behavior, verifiably, but touch existing code
  beyond the ratio. They cost the human more review than they spare. They need the
  human's approval, given after the report.
- **L3 behavior cuts** need a decision beyond review. They change intended behavior, or
  can't be shown to keep it, or add a dependency, or change a data schema. Uncertain bug
  fixes belong here too. They need the human's approval, given after the report.

## Steps

1. Brief the sub-agents (main agent).
2. Gather ideas (sub-agents).
3. Groom and sort the ideas (main agent).
4. Execute the L1 trims (main agent).
5. Report (main agent).
6. Approve (human).
7. Execute the approved ideas (main agent).

## 1. Brief the sub-agents (main agent)

Use two fresh sub-agents, a structure pass and a local pass, not forks of your context:
they should see the code, not your justifications for it. Run them in parallel. Give both
the same brief:

- **Requirements:** what you know about them, without your reasoning about how you built
  the diff. Quote the ticket or the human's own words where you can: one paraphrased word
  can steer the findings.
- **Decisions already made:** what the human decided, stated as what, not why. Design
  principles count if the human asked for them, or if they are stated in code or project
  docs that existed before the diff. Your own design choices don't count, even where you
  wrote them into the code.
- **Questions the human asked** about the structure, quoted.
- **The diff:** a commit range, or a diff against the base branch that includes
  uncommitted work. Tell them to search the whole codebase, not just the diff; reuse
  findings depend on it.

Then pass the **structure pass** the intro, the terms, the three lists and sections 2.1,
2.2 and 2.4 of this skill, verbatim. Pass the **local pass** the same with 2.3 instead of
2.2.

## 2. Gather ideas (sub-agents)

### 2.1 Rules for both passes

You report; you don't edit any file.

Keep your analysis shallow: enough to describe each idea, name its intent and estimate its
size. Don't research evidence or write detailed plans. The main agent does that later, and
only for the ideas it executes.

Report every idea you find, small or large: small trims add up, and large ones are the
biggest lever. Don't leave out an idea because it is small, because it would change
behavior, or because it reshapes a lot of existing code. Leave out only ideas that
contradict a decision in your brief. Work from the largest structures and the most-used
paths down.

Each pass has its own list of ideas that cut behavior, under "Cut behavior". For each such
idea, say whether a requirement asks for that behavior, and quote it if one does.

#### What doesn't count as simpler

- Shorter but denser doesn't count. No packing several statements into one line, no
  deleting blank lines, no metaprogramming or generic mechanisms where two explicit cases
  would do.
- After the idea, each abstraction must still be describable in one sentence without "and"
  or "unless". A mode it needs to serve both uses counts as a concept (see the intro).
- Don't lose intent or move knowledge. A function whose name says what the code means
  stays, even with one caller. A rule stays where the project keeps that kind of rule: an
  authorization rule used by a single controller still belongs with the other
  authorization rules, not in the controller.
- A check against hostile input (authorization, tampering, injection, limits on what a
  client may send) is not an edge case. Leave it, even when it can't fail today: defense
  in depth is deliberate. Don't report dropping it.
- Don't merge two things that mean different things just because they're handled the same
  or used together today. Two concerns are different when one could be needed without the
  other, or when they change for different reasons: booking a desk and booking lunch stay
  separate, even if every caller does both. If callers repeat the pair, a third
  abstraction that calls both is fine.
- Don't add types or structure that only add boilerplate.
- Don't trim tests for their own sake. Repetition in tests is often deliberate:
  overlapping coverage across layers, or independent setup instead of shared hooks. When
  code is deleted or inlined, its tests are deleted or moved with it. Code that only a
  test reaches, a single branch included, is dead code and goes with its test.
- Stay on concepts and size. Naming and style are for other reviews.

### 2.2 The structure pass

You look for missing structure. The local pass covers local waste like dead checks; if
local waste is part of a structural idea, include it in that idea.

#### Map first

Write down, as a short table:

- the structures and derived values the diff builds or touches: records, hashes, trees,
  query results, view models, parsed forms, values computed per item. Facts a consumer
  derives for itself from the raw input count too, with the consumer as their builder,
- existing structures that hold the same or similar information,
- for each of them: who builds it, from what, and who consumes it.

A consumer is an endpoint, job, command, tool, operation or output format. If the diff
builds no such structures, say so in one line and go on to "Then look at the diff as a
whole".

#### Look for these in the map

- Two entries built from the same source. They are the first thing to look at.
- The same structure built more than once, or in two shapes, e.g. one for reading and one
  for writing, or a new one next to an existing one. Find the one representation both
  could use, and make the others views of it.
- Several consumers each deriving the same facts from the raw input. Name the one
  representation they would all consume. Each consumer must use it whole: if consumers
  need different parts, that is two representations, not one with optional fields.
- Work that is computed and then thrown away on some path.
- Two paths running the same steps, differing in one. Make it one sequence that takes the
  differing step as input: as a callback or an object, not a flag it branches on. The shared
  sequence takes only that one step from its callers. Everything else it needs comes in as
  arguments, and what it produces goes out as its return value; it never calls back into
  its caller for anything else.
- An argument threaded through a recursion or a chain of calls. It often means a missing
  object: a view, a context.
- A side channel: state one method sets so another can read it. It usually means a missing
  argument or object.
- Two copies of the same code. Before extracting a helper, ask why the copies exist. If a
  missing representation would make both unnecessary, that is the idea.

#### Then look at the diff as a whole

- A mechanism more general than its uses: a base class with one subclass, a registry or
  lookup with two entries, a strategy with one strategy, a layer that only forwards.
  Replace it with the concrete cases.
- Do conditionals on the same question show up in several places, or in code unrelated to
  the feature? A long if/case chain in one place? Both usually mean a missing model.
- Can special cases become the normal case? E.g. lists handle one, many and none the same
  way.
- Do several booleans or optional fields together describe one state? Make it one value,
  e.g. an enum, so invalid combinations can't exist and the checks for them go away.
- Do casts, optional values or loose hashes hide a rule that always holds? Make it hold
  where the value is created, and the checks further down go away.
- Is a value stored that could be computed from another one? Compute it, unless a comment
  or measurement justifies the copy. Every copy can disagree with its source.
- Was a class, module or file introduced for a single use, and is it not where that kind
  of rule belongs in this project? Check whether its body reads better at the call site.
- Is there code in the project, or in a library it already depends on (the framework
  included), that does this, or would after a refactoring, however large?
- Would a small new dependency replace a lot of custom code?

#### Cut behavior

- Extras nobody asked for: more options, filters, sorting, formats or friendlier messages
  than the requirements need.
- A requirement that costs far more code than it seems worth. Say how much of the diff it
  accounts for.

### 2.3 The local pass

You look for local waste, one place at a time. The structure pass covers missing
structure.

- For every guard, nil check, rescue and fallback, name the input that would trigger it:
  - The input can't occur, because a type, a database constraint or the code on every
    path to it rules it out: delete the check.
  - It is outside input (params, files, API responses) and not yet checked: check it once
    where it enters, not everywhere it is used.
  - The input can occur, but it is unlikely and the requirements don't ask to handle it:
    that's an edge case, see "Cut behavior" below.
  - Nobody knows: say so in the idea.
- A rescue around code that can't raise goes.
- A wrapper whose name says nothing its body doesn't already say, and that owns no rule,
  gets inlined.
- Parameters, options, hooks or configuration that nothing uses yet go.
- Compatibility code for old callers goes when the diff already updated every caller.
- Hand-written loops and lookups where the language or standard library has the
  operation: list operations, a set for membership checks.
- Logging that only restates what the code does goes.
- Comments that restate or re-explain what the code does go, however long. So do comments
  that tell how the code came to be: earlier versions, or the discussion that led to it
  ("as discussed", "the user asked for", "we tried X first"). Put that history in your
  idea so it can go into a commit message. Comments that say why the code is the way it
  is stay, cut down to the reason, including a measurement behind a value.

#### Cut behavior

- Handling for edge cases that are unlikely and not in the requirements.
- Fallbacks, retries or degraded modes where failing loudly would do.
- A silent fallback like `|| default` that papers over an unclear rule.
- A rescue that turns every error into a default value. Catch the one error that actually
  happens, or none.

### 2.4 What to return

The structure pass starts with its map. Then both passes list their ideas, and group small
ones of one kind into one idea: the pattern, and the files it occurs in. For each idea:

- **where** it is: files, rough location,
- **the idea** in a few sentences: what goes, and what replaces it,
- **its intent:** to keep the intended behavior, or to change it. If it changes it: what
  changes, and whether a requirement asks for that behavior, quoted if one does. If it only
  changes a detail like key order or a typo, say which,
- **whether it touches existing code.** If it does: its obstruction sentence,
- **which concepts** disappear, and which appear,
- **its diff savings** and, if it touches existing code, **its existing savings and
  existing churn** (see the terms),
- the structure pass only: **the map entries** it merges or removes.

Then list the bugs you noticed: the concrete input, the requirement it violates (quoted),
and where. If you found nothing, say so.

## 3. Groom and sort the ideas (main agent)

Wait for both passes. Merge duplicates, and ideas that are alternatives to each other:
keep the stronger one per list. When alternatives land on different lists, keep both; the
report says that the later one would go further.

Number every idea that is left, bugs included: R1, R2, R3, … An idea keeps its code
whatever list it ends up on and whether it is killed later, so the human can refer to it
quickly. Use the codes whenever you talk about an idea, for the rest of the conversation.

Kill an idea only for what its description shows:

- **Not worth it:** it has neither concept gain nor total savings, its concept gain is
  negative, or its existing churn, risk and review time clearly outweigh its total savings
  and concept gain, e.g. rewriting a thousand lines of existing code to save ten lines.
- It touches existing code without an obstruction sentence whose X is concrete code in the
  diff. That is cleanup.
- It contradicts a decision in the brief.
- It is an L2 or L3 idea too small to be worth the human's decision: a concept gain of
  less than one whole concept, and total savings of less than roughly a few dozen lines of
  logic once similar ideas are grouped.
- It is obviously wrong.

Doubt is never a reason to kill in this step; the execution steps judge the real plan.
"The current version is fine", size and effort are never reasons at all.

Sort the rest by their properties. An idea that only changes a detail nobody could
sensibly rely on (see the terms) counts as keeping the behavior; note it for the report.

- Intent to change behavior, a new dependency, or a data schema change: **L3**. If a
  requirement asks for the behavior, kill the idea, unless the requirement costs far more
  code than it seems worth; then keep it on L3 and state the cost.
- A bug: **L1** if it is certain (see the three lists), otherwise **L3**.
- Intent to keep behavior: **L1** if it touches no existing code, or touches it within the
  ratio. **L2** if it is over the ratio.

Order L1 and L2 by concept gain, largest first.

## 4. Execute the L1 trims (main agent)

Execute every L1 trim, largest first. For each, make a detailed plan against the code as
it is now. If an earlier trim already removed or changed its target, skip it as done, or
plan it anew. The plan says:

- what replaces what,
- for a bug fix: the test that would have caught it,
- for everything else: evidence that the intended behavior is kept. For a deleted check,
  what makes it unreachable on every path to it. For reuse, the reused code. For a new
  representation, its shape and what each consumer stops doing itself; a consumer that
  needs something the representation lacks is where the idea fails, or where a mode would
  sneak in,
- if the code it reshapes has no tests: the pin-down tests you will write first, to capture
  its current behavior. Code counts as tested when a test would fail if its behavior
  changed, whichever layer the test sits in,
- if it touches existing code: its obstruction sentence, and its diff savings and existing
  churn, updated from the plan.

Then check the plan:

- It must not make control flow harder to follow, e.g. make a reader jump back and forth
  between the same two classes more than once to follow one call. It must not leave an
  abstraction that can't be described in one sentence, lose intent, or move a rule away
  from where the project keeps it. If it does, kill it.
- It must still meet the L1 conditions. Over the ratio: move it to L2. The intended
  behavior can't be shown to hold, e.g. untested existing code where no pin-down tests are
  possible: move it to L3. Not worth it once planned (see step 3): kill it.

Then apply it, and run the tests for the files it touched, including files of existing
code. A trim that only edits comments, or deletes code nothing calls, needs no test run.

Once all trims are in, run the related tests once: the tests for every file the trims
changed, the tests that exercise the code calling those files, and the end-to-end tests of
the feature the diff builds. Use the project's fastest way to run them, e.g. a parallel
test runner if available. If this run fails, find the trim that broke it and revert only
that one.

When a test fails, find out why:

- It tested code the trim deleted: delete it with that code. It tested internals the trim
  reshaped: move or rewrite it along with them. It pinned a detail nobody could sensibly
  rely on (see the terms): update it, and name it in the report. A test of intended
  behavior is never changed to make it pass.
- Your implementation is wrong: fix it.
- The idea itself changes intended behavior: revert it and move it to L3.

While you implement:

- If implementing takes more than its plan (a mode, another special case), count again,
  and revert it if it no longer removes more than it adds.
- Check that the old representation or path is gone. If old and new now coexist, the code
  has more concepts than before: finish the migration, or revert.
- Stop and revert when you are going in circles, or when the fix grows far beyond what the
  idea promised.

When you revert, undo only that idea. Never discard the diff's own uncommitted work.
Don't commit, unless the human asks for it.

## 5. Report (main agent)

If another skill called you, hand this report back to it. Otherwise give it to the human.

Name every idea by its code from step 3, and say which list it is on.

- The result, in three separate parts: lines of logic saved in the code, lines saved in
  the tests, and the concepts that disappeared. Fewer concepts is a simplification in its
  own right, even where it barely shows in the line counts.
- The trims you applied, one line each, naming the existing code each one touched.
- The bugs you fixed, each with its test.
- The details nobody could sensibly rely on that you changed, and the tests you updated
  for them.
- Each L2 refactoring and L3 behavior cut that awaits approval:
  - the idea in a sentence or two,
  - its concept gain and total savings,
  - its review effort: which existing code it touches, and its existing churn,
  - for L3: which intended behavior changes and who would notice, or which dependency or
    schema change it needs,
  - your recommendation, weighing taste (does it fit how this codebase does things?),
    churn, risk, review effort and savings. It annotates the idea; it doesn't move it to
    another list.
  Include the structure pass's map, briefly, when an idea rests on it. When two ideas are
  alternatives on different lists, say which one goes further.
- The ideas you killed, and why.
- History taken out of comments, for the commit message.
- Which tests ran: only the related ones, or the full suite.

## 6. Approve (human)

The human approves some, all or none of the waiting L2 and L3 ideas, by their codes.
Nothing is executed until then.

## 7. Execute the approved ideas (main agent)

Execute each approved idea with a detailed plan as in step 4. For an L3 behavior cut, the
plan also says what exactly changes, and which tests assert the old behavior: update
those, and delete the ones that only covered it.

Check the plan for readability as in step 4, and whether it is still worth it. An idea
that turns out weak here is killed and reported; don't ask about it again, and don't move
it to another list.
Apply it as in step 4, with the same rules for tests and reverting.
