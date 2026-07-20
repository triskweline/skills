---
name: agree-on-everything
description: Turn software requirements into an autonomously executable implementation plan with no open questions or surprising edge cases, by resolving every decision with the user before any code is written. Use before implementation whenever the user wants to plan, think through, hash out, align on, pin down, de-risk, or stress-test requirements or a design, or says things like "let's plan this", "grill me on the requirements", or "let's agree on everything".
---

# Agree on everything

The human wants to plan a major change that may affect many parts of the codebase.
Analyze the code base to discover any question, blocker or decision required to later implement the requirements autonomously without further human input.
To discover the required decisions, walk through the future implementation in your mind and imagine the required steps, such as:

- Changes to models and classes that encapsulate business logic and guarantee data integrity
- Changes to the database schema
- Changes to frontend screens (often view templates that render HTML, either server-side or client-side)
- Reuse or change of the frontend component library (e.g. buttons, cards)
- Changes to the routing and controllers (that find and call the model)
- Tensions with existing functionality that would be affected by this change

Then talk to the human until you agree on every single decision.

## Tracking decision state

Track a table of open decisions, which you update and extend as the discussion progresses.
Give each decision a unique number (`1`, `2`, `3`). Sometimes decisions will split into sub-decisions during your discussion, number those like `2.1`, `2.2`, `2.3`.
The human will have trouble keeping decisions apart. Always include decision numbers when referring to a decision.

For each decision, track the resolution state. E.g. whether the item still needs to be discussed, has already been agreed upon, or is awaiting another decision.
Use colors or emojis to differentiate the resolution state of each decision visually.

Print the initial table as soon as you start the discussion.
Re-print the whole table whenever there's a change.
Always print the table *first*, then recaps and follow-up questions *after* the table. Assume any text you print *before* a table scrolls out of view and will easily be overlooked by the human.

When writing ordered lists into the chat, and you're not talking about decision numbers, avoid using integer-numbered bullets. The human will confuse your list items with the numbers from the decision table.
For enumerations in prose text, prefer lower-cased letters (`a.`, `b.`, `c.`) or unordered lists instead.

## Explicit agreement

Only lock a decision when the human agrees explicitly.
When you make a counter-proposal to the human's input, or answer the human's question, ask again whether you are in agreement.
Be patient, help the human understand consequences and trade-offs, and allow a full discussion. Never push the human into making an uninformed decision, even when the discussion drags on.

## Recommendations

When you ask the human for a decision, also make a recommendation.
For simple decisions, a single recommendation is enough.
For non-trivial decisions with significant trade-offs, propose at least 2 approaches. E.g. one approach that requires the least changes to existing code, and another that is more work, but also more correct, flexible, performant or canonical.
Give each recommendation a shorthand code for quick human choices, e.g. 3A and 3B for two recommendations for decision 3.
Also assign a shorthand code when you only propose a single recommendation, e.g. 5A.
The human will have trouble keeping recommendations apart. Always include recommendation codes when referring to a recommendation.

## Order of discussion

Discuss each decision item separately.
Avoid batching questions. In particular, any non-trivial decision should always be discussed on its own.
It can be OK to batch small items that are closely related, or where a single answer will likely resolve them all.

Start with the decisions that appear key to the requirements, e.g. when many other decisions depend on it or follow from it.

## Free discussion, not multiple-choice

Keep this a free-form discussion in prose. Do not present decisions through a multiple-choice UI (no `AskUserQuestion`-style widget).
The shorthand codes are a convenience for quick replies, not a wizard: the human should always feel free to think out loud, push back, or propose something you didn't list.
Explain to the human that they can freely choose any other approach by typing prose into chat.

## Finishing up

When everything is agreed and no open question or edge case remains:
- Print the final table
- Ask whether to write a detailed execution plan. If yes, put it where the project keeps plans (e.g. `doc/plans`, or `plans/`)
- Ask whether the human wants you to fully implement the requirements, now that you are in full alignment. If yes, use `/implement-autonomously`.

## Begin your work

Now start analyzing the code base and then discuss every open question.
