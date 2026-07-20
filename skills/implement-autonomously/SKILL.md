---
name: implement-autonomously
description: Carry a set of requirements all the way to a tested, self-reviewed implementation that's ready to hand back, deciding open questions on your own and only interrupting for true showstoppers. Use when the user asks you to implement a feature, task, or ticket autonomously, end-to-end, or with minimal supervision — e.g. "build this on your own", "implement the whole thing", "go ahead and ship it".
---

# Implement autonomously

Your task is to implement requirements on your own, without further human input.

## Preparing your autonomous run

Before you begin changing code, there is a small window where you can still access the human to ask questions and resolve blockers.
Use this window to pull everything you need from the human, so you can work independently later.
After the preparatory window, the human will be away for a long time. When the human returns, they expect you to be ready to hand-off a high-quality implementation with no major issues.

First, ensure you have access to all the slash-command skills mentioned in this document, especially the `/agree-on-everything` skill.
If any required skill is missing, ask the human to install it or provide alternatives. For example, the project's `AGENTS.md` might contain instructions for running tests.

The most important preparation is ensuring your requirements are complete. There must be no undecided questions that would block you from implementing the requirements without further user input.
If you just ran the `/agree-on-everything` skill, you already know everything you will need for an autonomous implementation.
If you are still unsure about anything, use the `/agree-on-everything` skill to fully align with your human.

Non-trivial requirements should be implemented in a feature branch, using the `/work-in-branch` skill.

## Implement everything autonomously

Implement your entire requirements autonomously. Avoid stopping for user input if possible.
You might encounter new questions while implementing, try to answer and decide for yourself first.
Only ask the user when you encounter true showstoppers, or when choosing wrong on a hard decision would waste a large portion of follow-up work.

## Verify with tests

Most projects will come heavily tested and linted. Tests are a great way to check if new code fulfills requirements, or if you broke existing functionality.
If you are unsure what testing and linting tools are used in this project, use the `/find-verification-tools` skill.
Assume all checks were passing before you started your changes.

Verify *any* change by running possibly related tests (e.g. tests that mention the code identifiers, screens or UI elements you worked with). If you're unsure if a test is related, run it.
Tests can be useful before your implementation is complete. Consider verifying incremental work by getting quick feedback from individual test files, or even individual test cases (test with line number, e.g. `foo_spec:23`).

Add tests for everything you do or change. For Ruby on Rails apps, use the `/effective-rails-testing` skill.
Also fix existing tests that broke because of behavior changes.

Any non-trivial change must *additionally* be verified by running the *full* test suite and linters. Use the `/full-verification` skill.
The full test suite is slow. Only run the full test suite *after* possibly related tests (fast) already pass.

## Self-review

A review pass will meaningfully improve the quality of your changes, reducing the burden on a human code review to find all faults.

Review your work using a sub-agent, using the `/self-review` skill.

## Hand-off to the human

Only when your implementation is complete, verified and reviewed, hand off your work to the human:

- Recap your work (implementation, verification, self-review).
- Point out any decision that you are unsure about.
- Point out code locations that should get a thorough human review.
- Flag anything that took you a long time to find out you think is worth adding to AGENTS.md or CLAUDE.md.
  Global agent instructions must apply to most work in this repo, so don't recommend additions that are overly niche or feature-specific.

## Begin your work

Now implement the requirements end-to-end: verify with tests, self-review, and only then hand off to the human.
