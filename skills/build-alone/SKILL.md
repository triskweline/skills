---
name: build-alone
description: Carry a set of requirements all the way to a tested, self-reviewed implementation that's ready to hand back, deciding open questions on your own and only interrupting for true showstoppers. Use when the user asks you to implement a feature, task, or ticket autonomously, end-to-end, or with minimal supervision — e.g. "build this on your own", "implement the whole thing", "go ahead and ship it".
---

# Build alone

Your task is to implement requirements on your own, without further human input.

## Dependency check

This skill uses other skills from triskweline/skills. Your harness may announce only some
of the installed skills to you, so check which of them are installed by looking in its
standard skill locations. A skill you do not find there is missing.

| Skill | Role in this skill |
| --- | --- |
| `/agree-on-everything` | Settles every open requirement question with the human before the autonomous run starts. |
| `/work-in-branch` | Moves the work onto a properly named feature branch. |
| `/effective-rails-testing` | Picks the kind of test to add for each change when the project is a Rails app. |
| `/trim-code` | Makes the working change smaller; the L2 refactorings and L3 behavior cuts it leaves for approval are kept for the hand-off. |
| `/pass-all-checks` | Runs the whole test suite and all linters at the end and fixes failures. |
| `/self-review` | Has a sub-agent review the finished change; valid findings are folded back in. |

If all are available, say nothing about it and go on. For each missing skill, say in one
line that it is missing and what you use instead: another skill you have that fills the
role, or that you do the step yourself. Then continue. Where this skill's instructions name
a missing skill, use your substitute for the rest of this run. Do not ask whether to install
or what to substitute, and never install anything yourself.

## Preparing your autonomous run

Before you begin changing code, there is a small window where you can still access the human to ask questions, resolve blockers and get permission pre-emptively.
Use this window to pull everything you need from the human, so you can work independently later.
After the preparatory window, the human will be away for a long time. When the human returns, they expect you to be ready to hand-off a high-quality implementation with no major issues.

The most important preparation is ensuring your requirements are complete. There must be no undecided questions that would block you from implementing the requirements without further user input.
If you just ran the `/agree-on-everything` skill, you already know everything you will need for an autonomous implementation.
If you are still unsure about anything, use the `/agree-on-everything` skill to fully align with your human.

Your harness or instructions might require you to ask permission for certain actions during your work, e.g. for pushing a branch or running commands against a remote system. Ask now for the permissions you expect to need, so your run won't stall on a permission prompt while the human is away. Bundle your asks into a single question that explains what you need and why.
Include one more question in that bundle, for trimming with `/trim-code`:

> After implementing, I can simplify the code. The analysis takes extra time. How far should it go?
>
> - (a) Ambitious: also apply larger rewrites of existing code that make the change simpler. This means more code for you to review.
> - (b) Proportionate (default): simplify the change itself and apply only small rewrites of existing code. I'll propose the larger ones to you.
> - (c) None: skip simplifying.

Pass the choice to `/trim-code`: (a) approves its L2 refactorings up front, (b) is its default. Without a clear answer, use (b). With (c), skip the trimming step below.

If during your run you discover more permissions are needed, postpone the affected actions and finish the part of your work you already have permission for. Don't get around a missing permission by other means, and don't complicate your work just to avoid an action it needs. When you can no longer continue, accept the interruption and ask for another permission batch.

Non-trivial requirements should be implemented in a feature branch, using the `/work-in-branch` skill.

## Implement everything autonomously

Implement your entire requirements autonomously. Avoid stopping for user input if possible.
You might encounter new questions while implementing, try to answer and decide for yourself first.
Only ask the user when you encounter true showstoppers, or when choosing wrong on a hard decision would waste a large portion of follow-up work.

## Verify with tests

Most projects will come heavily tested and linted. Tests are a great way to check if new code fulfills requirements, or if you broke existing functionality.
Assume all checks were passing before you started your changes.

Verify *any* change by running possibly related tests (e.g. tests that mention the code identifiers, screens or UI elements you worked with). If you're unsure if a test is related, run it.
Tests can be useful before your implementation is complete. Consider verifying incremental work by getting quick feedback from individual test files, or even individual test cases (test with line number, e.g. `foo_spec:23`).

Add tests for everything you do or change. For Ruby on Rails apps, use the `/effective-rails-testing` skill.
Also fix existing tests that broke because of behavior changes.

## Trim the change

Unless the human chose to skip it, make your change smaller once the related tests pass, using the `/trim-code` skill.
The full test suite runs in the next step anyway, so while trimming, run the related tests `/trim-code` asks for, but not the full suite.
It applies its L1 trims, and its L2 refactorings if the human chose (a). It returns the rest for approval: L2 refactorings otherwise, and L3 behavior cuts always. Don't apply those yourself: they need the human's approval. Keep them for the hand-off.
Its report names the existing code that applied trims and refactorings touched. Point those locations out for a thorough human review in the hand-off.

## Run all checks

Any non-trivial change must *additionally* be verified by running the *full* test suite and linters. Use the `/pass-all-checks` skill.
The full test suite is slow. Only run the full test suite *after* possibly related tests (fast) already pass, and after trimming, if you trimmed.

## Self-review

A review pass will meaningfully improve the quality of your changes, reducing the burden on a human code review to find all faults.

Review your work using a sub-agent, using the `/self-review` skill.

## Hand-off to the human

Only when your implementation is complete, verified and reviewed, hand off your work to the human:

- Recap your work (implementation, trimming, verification, self-review).
- List the L2 refactorings and L3 behavior cuts from trimming that await approval, as `/trim-code` reports them, with their codes (R1, R2, …) and lists: each with the lines it saves, its review effort, for L3 the behavior it changes, and the recommendation. Ask which to apply.
- Point out any decision that you are unsure about.
- Point out code locations that should get a thorough human review.
- Flag anything that took you a long time to find out you think is worth adding to AGENTS.md or CLAUDE.md.
  Global agent instructions must apply to most work in this repo, so don't recommend additions that are overly niche or feature-specific.

## Begin your work

Now implement the requirements end-to-end: verify with tests, trim, self-review, and only then hand off to the human.
