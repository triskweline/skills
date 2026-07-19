---
name: agree-on-everything
description: Turn software requirements into an autonomously executable implementation plan with no open questions or surprising edge cases, by resolving every decision with the user before any code is written. Use before implementation whenever the user wants to plan, think through, hash out, align on, pin down, de-risk, or stress-test requirements or a design, or says things like "let's plan this", "grill me on the requirements", or "let's agree on everything".
---
Talk to the human until you agree on every decision required for an agent to autonomously implement the requirements.

Keep a table of open decisions, which you update and extend as the discussion progresses.
Give each decision a unique number (`1`, `2`, `3`). Sometimes decisions will split into sub-decisions during our discussion, number those like `2a`, `2b`, `2c`.
Print the whole table whenever there's a change, then ask the next open question *below* the table so the user doesn't need to scroll up.

Discuss each item separately.
Start with the decisions that appear key to our requirements, e.g when many other decisions depend on or follow from it.
Avoid batching questions. Only batch small items that are closely related, or where a single answer will likely resolve them.

Only lock a decision when you both agree explicitly.
When you make a counter-proposal to the human's input, or answer the human's question, ask again whether you both agree.
Be patient and allow a full discussion, don't push the human into an uninformed decision.

When you ask the human for a decision, also make a recommendation.
For simple decisions, a single recommendation is enough.
For non-trivial decisions with significant trade-offs, propose at least 2 approaches. E.g. one approach that requires the least changes to existing code, and another that is more work, but also more correct, performant or flexible.

When everything is agreed and no open question or edge case remains:
- Print the final table
- Ask whether to write a detailed execution plan. If yes, put it where the project keeps plans (e.g. `doc/` or `plans/`)
- Ask whether to start implementation. If yes, make sure you're on a feature branch (use the `/work-in-branch` skill).
  Ask both questions separately; either may be "not yet".

Now let's go through each open item one by one.
