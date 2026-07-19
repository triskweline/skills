---
name: implement-autonomously
description: Carry a set of requirements all the way to a tested, self-reviewed implementation that's ready to hand back, deciding open questions on your own and only interrupting for true showstoppers. Use when the user asks you to implement a feature, task, or ticket autonomously, end-to-end, or with minimal supervision — e.g. "build this on your own", "implement the whole thing", "go ahead and ship it".
---

Ensure your requirements are complete. There must be no undecided questions that would block you from implementing the requirements without further user input.
If you just ran the `/agree-on-everything` skill, you already know everything you will need for an autonomous implementation.
If you are still unsure about anything, use the `/agree-on-everything` skill to fully align with your human.

Prefer working in a feature branch, using the `/work-in-branch` skill.

Implement your entire requirements autonomously. Avoid stopping for user input if possible.
You might encounter new questions while implementing, try to answer and decide for yourself first. Only ask the user when you encounter true showstoppers, or when choosing wrong on a hard decision would waste a large portion of follow-up work.

Verify *any* change by running possibly related tests (e.g. tests that mention the code identifiers, screens or UI elements you worked with). If you're unsure if a test is related, run it.
Add tests for everything you do or change. For Ruby on Rails apps, use the `/effective-rails-testing` skill.
Also fix existing tests that broke because of behavior changes.
  
Any non-trivial change must additionally be verified by running the full test suite. Use the `/run-all-tests` skill.
The full test suite is slow. Only run the full test suite *after* possibly related tests (fast) already pass.

Review your work by a sub-agent, using the `/self-review` skill.

Only when your implementation is complete, verified and reviewed, hand off your work to the human:

- Recap your work (implementation, verification, self-review)
- Point out any decision that you are unsure about
- Point out code locations that should get a thorough human review
- Flag anything that took you a long time to find out you think is worth adding to AGENTS.md or CLAUDE.md.
  Global agent instructions must apply to most work in this repo, so don't recommend additions that are overly niche or feature-specific.
