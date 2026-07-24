---
name: agree-on-everything
description: Turn software requirements into an autonomously executable implementation plan with no open questions or surprising edge cases, by resolving every decision with the user before any code is written. Use before implementation whenever the user wants to plan, think through, hash out, align on, pin down, de-risk, or stress-test requirements or a design, or says things like "let's plan this", "grill me on the requirements", or "let's agree on everything".
---

# Agree on everything

The human wants to plan a major change that may affect many parts of the codebase.
Analyze the code base to discover any question, blocker or decision required to later implement the requirements autonomously without further human input.

To discover the required decisions, walk through the future implementation in your mind and imagine the required steps, such as:

- Changing models and classes that encapsulate business logic and guarantee data integrity
- Changing routes and controllers (that find and call the model)
- Changing the database schema
- Changing frontend screens (often involving view templates that render HTML, or JSON API endpoints)
- Reusing or changing the frontend component library (e.g. buttons, cards)
- Resolving tensions with existing functionality that would be affected by this change

Then talk to the human until you agree on every single decision.

## Tracking decisions

Track a table of all decisions, which you update and extend as the discussion progresses.

### Decision numbers and slugs

The human will have trouble keeping decisions apart. We can help by clearly identifying each decision:

- Give each decision a unique number (`1`, `2`, `3`).\
  Sometimes decisions will split into sub-decisions during your discussion, number those like `2.1`, `2.2`, `2.3`.
- Also give each decision a slug (1-3 words, like `xss-protection`) that reminds the human what this decision is about. Be brief.

Always include decision numbers and slugs when referring to a decision.\
You can omit the slug if the number is immediately followed by a long-form description, e.g. `Decision 23: XSS protection in welcome messages`.

When you print a decision number or slug, use **bold** formatting, e.g. `**23 (xss-protection)**`.

### Decision states

For each decision, track the resolution state. For example:

- The decision still needs to be discussed.
- The decision is currently being discussed with the human.
- The decision has already been agreed upon and is settled. Include the chosen option's code and slug (see below).
- The decision is no longer relevant (e.g. when the human has withdrawn a requirement, or a previous decision made a problem go away).
- The discussion depends on another decision and is currently waiting.

Use emojis to differentiate the resolution state of each decision visually.

### Printing the decision table

Print the initial decision table as soon as you start the discussion.
Re-print the whole decision table whenever there's a change.
Always print the table *first*, then recaps and follow-up questions *after* the table. Assume any text you print *before* a table scrolls out of view and will easily be overlooked by the human.

### Avoid confusing decision codes with lists

When writing ordered lists into the chat, and you're not talking about decision numbers, avoid using integer-numbered bullets. The human will confuse your list items with the numbers from the decision table.
For enumerations in prose text, prefer lower-cased letters (`a.`, `b.`, `c.`) or unordered lists instead.

## Recommend options

When you ask the human for a decision, also recommend at least two options for possible approaches.
E.g. one approach that requires the least changes to existing code, and another that is more work, but also more correct, clean, flexible, performant, or canonical.
When a decision involves major trade-offs, or has major consequences for the later implementation, you can provide up to four options.
The goal is to make the human think about the solution space, and make a deliberate decision. Don't pressure the human into blindly accepting the first option.

The human will have trouble keeping options apart. We can help by clearly identifying each option:

- Give each option a shorthand code for quick human choices, e.g. `3A` and `3B` for two options for decision `3`.
- Also give each option a slug (1-2 words, like `allow-html`) that distinguishes it from other options for the same decision.\
  The option slug only serves to contrast options, and does not need to also re-identify the decision.
  E.g. when the decision slug is `xss-protection`, the option slug could just be `sanitize` or `escape-everything`.

Always include option codes and slugs when referring to an option.\
You can omit the slug if the shorthand code is immediately followed by a long-form description, e.g. `Option 3A: Sanitize HTML using a strict allow-list of tags and attributes`.

When you print an option code or slug, use *italic* formatting, e.g. `*3B (escape-everything)*`.

When the human accepts an option with minor refinements or amendments, suffix a `+` to the option code, e.g. `3B+`.\
When the human makes a decision that is fundamentally different from the options you recommended, assign a new shorthand code and slug, e.g. `3X (trust-csp)`.

## Explicit agreement

Only lock a decision when the human agrees explicitly.
When you make a counter-proposal to the human's input, or answer the human's question, ask again whether you are in agreement.
Be patient, help the human understand consequences and trade-offs, and allow a full discussion. Never push the human into making an uninformed decision, even when the discussion drags on.

## Order of discussion

Discuss each decision item separately.
Avoid batching questions. In particular, any non-trivial decision should always be discussed on its own.
It can be OK to batch small items that are closely related, or where a single answer will likely resolve them all.

Start with the decisions that appear key to the requirements, e.g. when many other decisions depend on it or follow from it.

## Free discussion, not multiple-choice

Keep this a free-form discussion in prose. Do not present decisions through a multiple-choice UI (no `AskUserQuestion`-style widget).
The shorthand codes (or option slugs) are a convenience for quick replies, not a wizard: the human should always feel free to think out loud, push back, or propose something you didn't list.
Explain to the human that they can freely choose any other approach by typing prose into chat.

## Finishing up

When everything is agreed and no open question or edge case remains:
- Print the final table
- Ask whether to write a detailed execution plan.
  If yes, put it where the project keeps plans (e.g. `doc/plans`, or `plans/`)
- Ask whether the human wants you to fully and autonomously implement the requirements, now that you are in full alignment.
  If yes, use the `/implement-autonomously` skill.

## Begin your work

Now start analyzing the code base and then discuss every open question.
