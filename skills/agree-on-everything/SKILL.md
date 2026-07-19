---
name: agree-on-everything
description: Turn software requirements into an autonomously executable implementation plan with no open questions or surprising edge cases, by resolving every decision with the user before any code is written. Use before implementation whenever the user wants to plan, think through, hash out, align on, pin down, de-risk, or stress-test requirements or a design, or says things like "let's plan this", "grill me on the requirements", or "let's agree on everything".
---

Analyze the code base to discover any question, blocker or decision required to later implement the requirements without further user input.
Then talk to the human until you agree on every single decision.

Keep a table of open decisions, which you update and extend as the discussion progresses.
Give each decision a unique number (`1`, `2`, `3`). Sometimes decisions will split into sub-decisions during your discussion, number those like `2.1`, `2.2`, `2.3`.
Print the whole table whenever there's a change, then ask the next open question *below* the table so the user doesn't need to scroll up.

Discuss each item separately.
Avoid batching questions. Only batch small items that are closely related, or where a single answer will likely resolve them all.
Start with the decisions that appear key to the requirements, e.g. when many other decisions depend on it or follow from it.

Only lock a decision when the human agrees explicitly.
When you make a counter-proposal to the human's input, or answer the human's question, ask again whether you are in agreement.
Be patient, help the human understand consequences and trade-offs, and allow a full discussion. Never push the human into making an uninformed decision, even when the discussion drags on.

When you ask the human for a decision, also make a recommendation.
For simple decisions, a single recommendation is enough.
For non-trivial decisions with significant trade-offs, propose at least 2 approaches. E.g. one approach that requires the least changes to existing code, and another that is more work, but also more correct, flexible, performant or canonical.
Give each recommendation a shorthand code for quick human choices, e.g. 3A and 3B for two recommendations for decision 3.
Explain to the human that they can freely choose any other approach by typing prose into chat.

When everything is agreed and no open question or edge case remains:
- Print the final table
- Ask whether to write a detailed execution plan. If yes, put it where the project keeps plans (e.g. `doc/plans`, or `plans/`)
- Ask whether the human wants you to fully implement the requirements, now that you are in full alignment. If yes, use `/implement-autonomously`.

Now start analyzing the code base and then discuss every open question.
