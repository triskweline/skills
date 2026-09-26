---
name: trim-code
description: >-
  Make a working change smaller. A fresh sub-agent looks for trims that keep the behavior
  (checks nothing can trigger, wrappers that only forward, special cases a better model
  would absorb) and for behavior the change doesn't need (unlikely edge cases, fallbacks,
  extras nobody asked for). Apply the trims directly and report the behavior cuts to the
  caller. Use after implementing a change that works but is too much code for what it
  does, or when asked to trim, slim down or simplify a change.
---

# Trim code

Agent-written code often works but is far more code than its job needs. The task is to
make a change smaller. There are two levers:

- **Trims** restructure or delete code without changing its behavior. They are applied
  directly.
- **Proposals** change behavior, usually by dropping what the change doesn't need, or
  need approval for another reason. They are reported to the caller. Cutting behavior is
  often the bigger lever, so look for it just as hard.

The goal is fewer concepts a reader must keep in mind. Fewer lines follow from that, but
they are not the goal: denser code that says the same thing is not a trim.

## 1. Brief a sub-agent

Ask a fresh sub-agent to find trims and proposals, not a fork of your context: it should
see the code, not your justifications for it. It reports; it does not edit.

Brief it with what you know about the requirements, but leave out technical details from
the implementation. Tell it how to see the change: a commit range, or a diff against the
base branch that includes uncommitted work. Tell it to search the whole codebase, not just
the diff; reuse findings depend on it. Pass it the intro and sections 2 and 3 of this
skill, verbatim.

## 2. Rules

Start with proportion: say in one sentence what the change does, and how much code you'd
expect that to take compared to the change. The surplus is what you are looking for.

### Restructure

- Is there a restructuring that keeps the behavior and makes whole branches, helpers or
  layers unnecessary? Deleting complexity beats moving it: a refactor that spreads the
  same concepts over more places is no gain.
- Do new conditionals show up in several places, or in code unrelated to the feature? That
  usually means a missing model or helper. A long if/case chain in one place can also mean
  a missing model.
- Can special cases become the normal case? E.g. lists handle one, many and none the same
  way.
- Do several booleans or optional fields together describe one state? Make it one value,
  e.g. an enum, so invalid combinations can't exist and the checks for them go away.
- Do casts, optional values or loose hashes hide a rule that always holds? Make it hold
  where the value is created, and the checks further down go away.
- Is a value stored that could be computed from another one? Compute it. Every copy can
  disagree with its source.
- Was a class, module or file introduced for a single use, and is it not where that kind
  of rule belongs in this project? Check whether its body reads better at the call site.

### Delete code that does nothing

- For every guard, nil check, rescue and fallback, name the input that would trigger it:
  - The input can't occur, because a type, a database constraint or the code on every
    path to it rules it out: delete the check.
  - It is outside input (params, files, API responses) and not yet checked: check it once
    where it enters, not everywhere it is used.
  - The input can occur, but it is unlikely and the requirements don't ask to handle it:
    that's an edge case, see "Cut behavior".
  - Nobody knows: find out. If you can't, it's a proposal.
- A rescue around code that can't raise goes.
- A wrapper whose name says nothing its body doesn't already say, and that owns no rule,
  gets inlined. With more than one caller outside the change, it's a proposal.
- Parameters, options, hooks or configuration that nothing uses yet go.
- Compatibility code for old callers goes when the change already updated every caller.
- Logging and comments that only restate what the code does go. Comments that say why
  stay.

### Use what exists

- Is there code in the project, or in a library it already depends on (the framework
  included), that does this, or would after a small change?
- Does the change use the language and standard library well? E.g. list operations
  instead of hand-written loops, a set for membership checks.
- Would a small new dependency replace a lot of custom code? Propose it.

### Cut behavior

These are all proposals.

- Handling for edge cases that are unlikely and not in the requirements.
- Fallbacks, retries or degraded modes where failing loudly would do.
- A silent fallback like `|| default` that papers over an unclear rule.
- A rescue that turns every error into a default value. Catch the one error that actually
  happens, or none.
- Extras nobody asked for: more options, filters, sorting, formats or friendlier messages
  than the requirements need.
- A requirement that costs far more code than it seems worth. Say how much of the change
  it accounts for.

### Don't overshoot

- Shorter but denser doesn't count. No packing several statements into one line, no
  deleting blank lines, no metaprogramming or generic mechanisms where two explicit cases
  would do.
- Don't lose intent or move knowledge. A function whose name says what the code means
  stays, even with one caller. A rule stays where the project keeps that kind of rule: an
  authorization rule used by a single controller still belongs with the other
  authorization rules, not in the controller.
- A check against hostile input (authorization, tampering, injection, limits on what a
  client may send) is not an edge case. Leave it, and don't propose dropping it.
- Don't merge two cases that mean different things just because they're handled the same
  today.
- Don't add types or structure that only add boilerplate.
- Don't trim tests. Repetition in tests is often deliberate: overlapping coverage across
  layers, or independent setup instead of shared hooks.
- Stay on size and structure. Naming and style are for other reviews.

## 3. What to return

First the one sentence from section 2, and how much code you'd expect compared to the
change. Then two lists. Prefer a few findings that matter over many small ones: group
small deletions of one kind into one finding, and order each list by how much it removes.
If there is nothing to trim, say so.

**Trims** keep the behavior and change little or nothing outside the change. For each:

- where it is,
- what disappears,
- what replaces it, with a code sketch where that is quicker than prose,
- evidence that it keeps the behavior: for a deleted check, what makes it unreachable on
  every path to it, by file and line; for reuse, the existing code by path,
- roughly how much smaller the result is.

**Proposals** are everything else: cuts of behavior, a new dependency, a change to a
public interface or a data schema, a restructuring that changes more than a few lines
outside the change. When unsure whether a finding keeps the behavior, it's a proposal.

Every proposal costs the human a decision, so it has to be worth one. Propose only what
removes a large part of the change, or a whole concept, branch, layer or dependency. Leave
out small behavior changes that save a few lines. For each proposal:

- where it is,
- what behavior is lost and who would notice, or what else the caller is agreeing to,
- what code goes, and what replaces it,
- roughly how much smaller the result is,
- your recommendation.

## 4. Apply the trims

Check each trim's evidence, and read its sketch against the requirements. A trim without
evidence goes back to the sub-agent; dismiss it as unverified only if the sub-agent can't
supply the evidence either. Dismiss a verified trim only for a concrete reason: the input
that reaches the deleted code, the requirement it conflicts with, the named code that
gets harder to follow and why, or the intent a removed name carried or the place a moved
rule belongs. "The current version is fine" is not a reason.

Apply restructurings first; smaller trims often vanish with them. After each
restructuring, and after the batch of small trims, run the tests related to the code you
changed. A test that fails only because it tested code the trim deleted (a guard for an
input that can't occur, an option nothing passes) is deleted with that code. A test that
fails for any other reason means the trim changed behavior: revert the trim, don't fix
the test.

Go through the proposals, but don't apply them, and don't ask about them while you work.
Drop a proposal that falls below the bar in section 3. Drop a proposal for behavior the
requirements ask for, unless the requirement costs far more code than it seems worth; keep
that one, with its cost. Give your own recommendation on the rest; it may differ from the
sub-agent's.

## 5. Report

If another skill called you, hand this report back to it. Otherwise give it to the human.

- The one sentence, and roughly how much smaller the change is now.
- The trims you applied, one line each.
- The trims you dismissed, and why.
- The proposals, each with your recommendation.
- Which tests ran: only the related ones, or the full suite.

If proposals are accepted, apply them, run the related tests, and delete the tests that
only covered the dropped behavior.
