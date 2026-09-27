---
name: trim-code
description: >-
  Make a working change simpler and smaller, with fewer concepts for a reader to
  understand. Two fresh sub-agents look for ideas, one for missing structure (the same
  thing built twice, steps repeated with one difference, mechanisms more general than
  their uses, existing code that could serve the change) and one for local waste (checks
  nothing can trigger, wrappers that only forward). Apply the ideas that keep the behavior
  and stay in proportion to the change. Report the rest to the human: behavior cuts
  (unlikely edge cases, extras nobody asked for) and larger rewrites of code outside the
  change. Use
  after implementing a change that works but is too much code for what it
  does, or when asked to trim, slim down or simplify a change.
---

# Trim code

Agent-written code often works but carries more concepts than its job needs: two
representations of the same thing, steps repeated with one difference, mechanisms more
general than their uses, checks nothing can trigger, options nobody asked for. The task
is to find what a change can do without.

The measure is concepts a reader must understand first, lines of logic second. A change
can lose whole concepts and barely get shorter; that is still the win. Count honestly:
count the concepts that disappear and the ones that appear, and go by the net. A new
object, representation or protocol is a concept. So is a **mode**: anything an
abstraction branches on so it can serve one more use, like a flag, an option or a type
check. A mode is worth it when it removes more than it adds, and not when it trades a
small deletion for a unit that is hard to reason about.

The large restructurings are the reason this skill exists, and code outside the change
is in scope. **Code outside the change** is every line the diff neither adds nor changes.
An idea serves this change when it removes concepts from the change itself, or reshapes
code outside it so that the change needs less: code that now does the change's work, or
one abstraction for the old and the new use instead of a second one next to it. Cleaning
up code outside the change that the change doesn't need is out of scope.

Changing code outside the change adds review load the human didn't ask for, so an idea
that does it must pay for itself:

- **The obstruction sentence:** "The change needed X because code outside it does, lacks
  or is shaped as Y; this idea makes one of them unnecessary by Z." X is concrete
  code in the diff: files and lines. An idea without such an X is cleanup. The idea may
  delete either side, X or its counterpart outside the change, whichever fits the result
  worse.
- **The ratio:** the human has to review what the idea writes and what it changes
  outside the change, and is spared what it deletes, wherever that code lives. The logic it
  writes and changes may be at most about twice the logic it deletes. Clearly more is over
  the ratio; close is within it. Every line counts, including renames and updated call
  sites.

That way the diff the human reviews grows only in proportion to what an idea applied
unasked spares them. The ratio is waived when the human has explicitly asked for
ambitious trimming. The obstruction sentence always applies.

Every idea ends up as one of three kinds:

- A **trim** meets all of these, and is applied directly:
  - it keeps the behavior on every input, inside and outside the change,
  - it serves this change,
  - it doesn't change an interface used outside this codebase (an API, a URL, a
    library's public methods), a data schema, or the dependencies,
  - if it touches code outside the change, it has an obstruction sentence and stays
    within the ratio.
- A **proposal** is any other idea, including one that changes behavior only on inputs
  that are very unlikely, and a behavior-preserving refactoring over the ratio. Proposals
  are reported; only the human accepts them.
- A **bug** is a concrete input on which the code violates a requirement you can quote.
  If it lies in the change's code and the fix is local, it is fixed, together with a test
  that would have caught it. Other bugs are reported.

## Steps

1. Brief two sub-agents, a structure pass and a local pass, and run them in parallel.
2. Check their findings.
3. Sort the findings into trims and proposals.
4. Apply the trims and fix the bugs.
5. Report.
6. Apply the proposals the human accepts, if any.

Sections 1 to 6 are yours. Sections 7 to 10 are the sub-agents' instructions.

## 1. Brief two sub-agents

Use two fresh sub-agents, not forks of your context: they should see the code, not your
justifications for it. Give both the same brief:

- **Requirements:** what you know about them, without technical details from the
  implementation. Quote the ticket or the human's own words where you can: one
  paraphrased word can steer the findings.
- **Decisions already made:** what the human decided, stated as what, not why. Design
  principles count if the human asked for them, or if they are stated in code or project
  docs that existed before the change. Your own design choices don't count, even where
  you wrote them into the code.
- **Questions the human asked** about the structure, quoted.
- **The change:** a commit range, or a diff against the base branch that includes
  uncommitted work. Tell them to search the whole codebase, not just the diff; reuse
  findings depend on it.

Determine the **ambition setting** from the human's words, and don't pass it on: the
sub-agents always search ambitiously. The ratio is waived only if the human explicitly
asked for ambitious trimming, in their own words or relayed by a calling skill. A calling
skill never waives it on its own.

Then pass the **structure pass** the intro (the text between the title and "Steps") and
sections 7, 8 and 10 of this skill, verbatim and with their headings. Pass the **local
pass** the intro and sections 7, 9 and 10 the same way.

## 2. Check the findings

Wait for both passes. Then check each idea's evidence: confirm the guarantee, the reused
code or the consumers it names, and check its plan against the requirements. For a new
representation, check that it carries what every consumer needs. A consumer that needs
something it lacks is where the idea fails, or where a mode would sneak in; note which.
For an idea that touches code outside the change, check that its X exists in the diff,
that the plan deletes X or its counterpart, and that the numbers are plausible.

An idea without evidence goes back to its sub-agent, or you verify it yourself if the
sub-agent is gone. Drop it as unverified only if neither works.

Merge ideas the two passes both found. Note which local ideas a structural idea would make
unnecessary; section 4 skips them only once that structural trim is in.

## 3. Sort into trims and proposals

The sub-agents report facts; you decide each idea's kind. An idea that meets the intro's
definition is a trim unless, by your judgment of how the code will read and maintain, it:

- makes control flow harder to follow,
- leaves an abstraction that can't be described in one sentence (section 7),
- loses intent, or moves a rule away from where the project keeps it,
- reshapes code outside the change that no test covers, and you can't first write tests
  that pin down its current behavior.

Reclassify a trim as a proposal only for one of these reasons, and name the code that
gets worse and how. Apart from the ratio, a trim's size, the effort to implement it, or
the amount of code outside the change it touches is never a reason: large trims are what
this skill is for. Decide the ratio here, once for all ideas and before you apply any, from
the sub-agents' estimates. To call an idea over the ratio, quote both numbers and name the
code you counted. Raise a sub-agent's estimate only by naming code it missed. If you
doubt whether a structural trim reads better, apply it and judge the result (section 4).

Drop an idea only for one of these reasons:

- It stays unverified (section 2).
- It contradicts a decision in the brief.
- It cuts behavior the requirements ask for, unless the requirement costs far more code
  than it seems worth; then keep the proposal and state the cost.
- It is a proposal too small to be worth the human's decision: less than a whole concept,
  or less than roughly a few dozen lines of logic once similar findings are grouped.
- It touches code outside the change without an obstruction sentence whose X is concrete
  code in the diff. That is cleanup.
- Another concrete reason that names what is affected: the input that reaches the deleted
  code, or a project convention it breaks (e.g. for security or architecture).

"The current version is fine" is not a reason. Give each remaining proposal your own
recommendation; it may differ from the sub-agent's.

## 4. Apply the trims and fix the bugs

When you revert a trim, undo only the trim. Never discard the change's own uncommitted
work.

Work in this order:

1. The structural trims, one at a time, the largest net loss of concepts first. For each:
   - If code it reshapes outside the change has no tests, first write tests that pin down
     its current behavior.
   - Implement it as planned. If implementing it takes more than its plan (a mode,
     another special case), count again, and revert it if it no longer removes more than
     it adds.
   - Check that the old representation or path is gone. If old and new now coexist, the
     code has more concepts than before: finish the migration, or revert.
   - If you doubted that it reads better, judge the result now, and revert it if it
     reads worse.
2. The local trims, as one batch. Locate them again in the code as it is now, and skip
   those that a structural trim you applied made unnecessary.
3. The fixes for clear bugs, one at a time, each with a test that would have caught it.

After each structural trim, after the batch of local trims, and after each bug fix, run
the tests related to the code you changed, including the tests of code outside the change
you touched. When a test fails, find out why:

- It tested code the trim deleted: delete it with that code. It tested internals the trim
  reshaped: move or rewrite it along with them. A test of behavior that callers can see is
  never changed to make it pass.
- Your implementation is wrong: fix it.
- The idea itself changes behavior: revert it and make it a proposal.

Stop and revert when you are going in circles, or when the fix grows far beyond what the
trim promised, e.g. a small local trim turning into a large change. A reverted trim, and
a structural trim you didn't get to, becomes a proposal, with what you learned.

Don't commit; leave the changes in the working tree. Don't apply
proposals, and don't ask about them while you work.

## 5. Report

If another skill called you, hand this report back to it. Otherwise give it to the human.

- The proportion: what the passes expected, and how much smaller the change is now, in
  concepts and in lines of logic. If it is still far larger than expected, say where the
  bulk sits and whether a proposal covers it. If the lines barely moved, say that the
  value is in fewer concepts.
- The ambition setting in effect: the ratio, or waived because the human asked for
  ambitious trimming.
- The structural trims: how many the passes suggested, and how many you applied. For each
  one that touched code outside the change: its obstruction sentence, the code it changed
  there, the tests that cover it, and any tests you wrote to pin down its behavior. Then
  the total lines of logic written and changed outside the change.
- The local trims you applied, one line each.
- The bugs you fixed, with their tests, and the bugs you only report.
- Every idea you reclassified, reverted or dropped, and why.
- The proposals, each with your recommendation and what accepting it costs the human in
  review: the code outside the change it would touch, and roughly how many lines of logic
  it writes, changes and deletes. Include the structure pass's map, briefly, when a
  proposal rests on it.
- History taken out of comments, for the commit message.
- Which tests ran: only the related ones, or the full suite.

## 6. Apply accepted proposals

If the human accepts proposals, apply each one as in section 4. An accepted refactoring
keeps the behavior: the ratio no longer applies to it, and tests of behavior stay
unchanged. An accepted behavior cut is meant to change behavior: update the tests that
assert the old behavior, and delete those that only covered it.

## 7. Rules for both passes

You report; you don't edit any file.

Start with proportion: say in one sentence what the change does, and how much logic you'd
expect that to take compared to the change. Count logic only, not comments, docs or
tests. Proportion is a hint, not a gate: even a change of plausible size often gets
simpler when code outside it is rebuilt to serve it.

Report every idea you find, small or large: small trims add up, and large ones are the
biggest lever. Don't leave out an idea because it is small, because it would change
behavior, or because it reshapes a lot of code outside the change. Leave out only
ideas that contradict a decision in your brief.

Research every idea before you return it, and return it with evidence (section 10). Work
from the largest structures and the most-used paths down. Don't return ideas you haven't
checked.

Each pass has its own list of ideas that cut behavior, under "Cut behavior". For each
such idea, say whether a requirement asks for that behavior, and quote it if one does.

### What doesn't count as simpler

- Shorter but denser doesn't count. No packing several statements into one line, no
  deleting blank lines, no metaprogramming or generic mechanisms where two explicit cases
  would do.
- After the change, each abstraction must still be describable in one sentence without
  "and" or "unless". A mode it needs to serve both uses counts as a concept (see the
  intro).
- Don't lose intent or move knowledge. A function whose name says what the code means
  stays, even with one caller. A rule stays where the project keeps that kind of rule: an
  authorization rule used by a single controller still belongs with the other
  authorization rules, not in the controller.
- A check against hostile input (authorization, tampering, injection, limits on what a
  client may send) is not an edge case. Leave it, even when it looks unreachable: defense
  in depth is deliberate. Don't propose dropping it.
- Don't merge two cases that mean different things just because they're handled the same
  today.
- Don't add types or structure that only add boilerplate.
- Don't trim tests for their own sake. Repetition in tests is often deliberate:
  overlapping coverage across layers, or independent setup instead of shared hooks. When
  code is deleted or inlined, its tests are deleted or moved with it. Code that only a
  test uses is dead code and goes with its test.
- Stay on concepts and size. Naming and style are for other reviews.

## 8. The structure pass

You look for missing structure. Another sub-agent covers local waste like dead checks, so
leave that out.

### Map first

After the proportion sentence, write down, as a short table:

- the structures and derived values the change builds or touches: records, hashes, trees,
  query results, view models, parsed forms, values computed per item,
- existing structures in the codebase that hold the same or similar information,
- for each of them: who builds it, from what, and who consumes it,
- for each consumer (an endpoint, job, command, tool, operation or output format): which
  structures it uses, and what it derives for itself from the raw input instead.

If the change builds no such structures, say so in one line and go on to "Then look at
the change as a whole".

### Look for these in the map

- Two entries built from the same source. They are the first thing to look at.
- The same structure built more than once, or in two shapes, e.g. one for reading and one
  for writing, or a new one next to an existing one. Find the one representation both
  could use, and make the others views of it.
- Several consumers each deriving the same facts from the raw input. Name the one
  representation they would all consume. Each consumer must use it whole: if consumers
  need different parts, that is two representations, not one with optional fields.
- Work that is computed and then thrown away on some path.
- Two paths running the same steps, differing in one. Make it one sequence that takes the
  differing step as input: as a block or an object, not a flag it branches on.
- An argument threaded through a recursion or a chain of calls. It often means a missing
  object: a view, a context.
- A side channel: state one method sets so another can read it. It usually means a missing
  argument or object.
- Two copies of the same code. Before extracting a helper, ask why the copies exist. If a
  missing representation would make both unnecessary, that is the finding.

### Then look at the change as a whole

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
- Would a small new dependency replace a lot of custom code? Report it.

### Cut behavior

- Extras nobody asked for: more options, filters, sorting, formats or friendlier messages
  than the requirements need.
- A requirement that costs far more code than it seems worth. Say how much of the change
  it accounts for.

## 9. The local pass

You look for local waste, one place at a time. Another sub-agent covers missing structure,
so leave that out.

- For every guard, nil check, rescue and fallback, name the input that would trigger it:
  - The input can't occur, because a type, a database constraint or the code on every
    path to it rules it out: delete the check.
  - It is outside input (params, files, API responses) and not yet checked: check it once
    where it enters, not everywhere it is used.
  - The input can occur, but it is unlikely and the requirements don't ask to handle it:
    that's an edge case, see "Cut behavior" below.
  - Nobody knows: find out. If you can't, report it as a possible behavior change.
- A rescue around code that can't raise goes.
- A wrapper whose name says nothing its body doesn't already say, and that owns no rule,
  gets inlined.
- Parameters, options, hooks or configuration that nothing uses yet go.
- Compatibility code for old callers goes when the change already updated every caller.
- Hand-written loops and lookups where the language or standard library has the
  operation: list operations, a set for membership checks.
- Logging that only restates what the code does goes.
- Comments that restate or re-explain what the code does go, however long. So do comments
  that tell how the code came to be: earlier versions, or the discussion that led to it
  ("as discussed", "the user asked for", "we tried X first"). Put that history in your
  finding so it can go into a commit message. Comments that say why the code is the way
  it is stay, cut down to the reason, including a measurement behind a value.

### Cut behavior

- Handling for edge cases that are unlikely and not in the requirements.
- Fallbacks, retries or degraded modes where failing loudly would do.
- A silent fallback like `|| default` that papers over an unclear rule.
- A rescue that turns every error into a default value. Catch the one error that actually
  happens, or none.

## 10. What to return

1. The proportion sentence from section 7.
2. The structure pass only: the map from section 8.
3. Your ideas, ordered by the net number of concepts they remove, then by lines of logic.
   Group small findings of one kind into one idea, e.g. six nil checks nobody can explain.
   For each:
   - where it is,
   - whether it keeps the behavior on every input, with the evidence below; if not, what
     changes, how likely that is, and who would notice,
   - which concepts disappear, which appear, and roughly how many lines of logic go,
   - what replaces it: its plan, in prose, with code where that is quicker,
   - evidence that it works: for a deleted check, what makes it unreachable on every path
     to it, by file and line; for reuse, the reused code by path; for a new
     representation, its shape (name and fields), who builds it, and for each consumer
     what it stops doing itself,
   - the structure pass only: the map entries it merges or removes,
   - if it touches code outside the change: its obstruction sentence with X located (files
     and lines), and a rough estimate in round numbers of the lines of logic the idea
     deletes, and of those it writes and changes,
   - for an idea that cuts behavior: the requirement check from section 7, and whether you
     recommend it.
4. Bugs you noticed along the way: the input, the requirement it violates, and where.

If you found nothing, say so.
