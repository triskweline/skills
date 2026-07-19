---
name: implement-autonomously
---

Ensure that you understand your requirements completely, using the `/agree-on-everything` skill (unless you already used it on your current requirements).

Prefer working in a feature branch, using the `/work-in-branch` kill.

Implement your entire requirements autonomously. Avoid stopping for user input if possible. You might encounter new questions while implementing, try to answer and decide for yourself first. Only ask the user when you encounter true showstoppers, or when choosing wrong on a hard decision would waste a large portion of follow-up work.

Add tests for everything you do or change, using the `/effective-tests` skill.
Also fix existing tests that broke because of behavior changes.
  
Any non-trivial change must be verified by running the full test suite. Use the `/run-all-tests` skill.

Review your work by a sub-agent, using the `/self-review` skill.

Only when your implementation is complete, verified and reviewed, hand off your work to the human:

- Recap your work (implementation, verification, self-review)
- Point out any decision that you are unsure about
- Point out code locations that should get a thorough human review
- Flag anything that took you a long time to find out you think is worth adding to AGENTS.md or CLAUDE.md.
  Global agent instructions must apply to most work in this repo, so don't recommend additions that are overly niche or feature-specific.
