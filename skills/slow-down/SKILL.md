---
name: slow-down
description: >-
  Slows down a conversation where the agent raised more open questions, decisions or
  findings than the user can take in at once. Goes through them one item at a time, each
  explained in plain language with plenty of context, a few clear options and a
  recommendation, and waits for the user's choice before moving on. Use when the agent has
  left the user with several things to settle (review findings it did not dare to apply,
  follow-up questions at the end of a task, trade-offs it flagged) and the user says "slow
  down", "one at a time", "let's go through these" or "I can't answer all of this at once".
  Works through the items already on the table instead of searching for more, and settles
  them without writing an implementation plan.
---

# Slow down

You have presented the human with multiple open items (questions or decisions). The human is having trouble understanding everything you're asking and cannot answer it all at once. So go through the items one by one, with plenty of context, options and recommendations.

Your job is the items already on the table. If re-reading the code shows you something new, add it only when it changes an item under discussion; otherwise mention it once at the end.

## Start with an overview

The human wants to see the shape of what is open before the first item. Number the items before you write the overview (see below), then group them into the big topics that need deciding.

Give each topic a name, and a short abstract:

- A sentence to understand what this is about.
- Your instinctive take on the topic as a whole: how you would approach it, how important you feel it is, or both. This will address several items broadly, and that is fine. A topic is major when it is technically challenging, when it is a one-way door (hard to reverse) or when many other decisions flow from it. A topic is minor when there is a probable answer you just want to align on with the human.
- Every item in the topic, as its number and a short title (two to five words).

Mark the items you have a strong and confident lean on with 🤖 and your decision in one line, in italics, e.g. `7 Inconsistent error class names, *🤖 rename to FooError everywhere*`. The human may accept these without discussing them.

Open the overview with one sentence that counts the items and topics and explains the 🤖 mark, e.g. "There are five items in three topics. 🤖 marks my strong leans, which you can choose to auto-accept."

End the overview by naming the item you'll start with, and wait for a go. Offer two keywords: "go" walks through every item, the 🤖 items included; "auto" accepts all 🤖 decisions and starts with the first remaining item. The human can also accept some 🤖 decisions by number. Accepting them must be the human's conscious choice: never treat "go" as accepting them. The human may first ask for changes or more orientation, but will usually just say go.

You decide the order; the human does not need to sign off on it. Take items that others depend on, and important items, first, even if that breaks the numbering sequence.

## Numbering items

Items have a number for quick identification, like `1`, `2`, `3`. Number them in sequence across all topics.

If discussion splits an item, use numbers like `4.1` or `5.2.1`. Avoid splitting deeper than three levels (e.g. `1.3.1`). If you feel the need to go deeper, ask once whether we're getting lost in details. If the discussion is still valuable, keep discussing under the current third-level number without splitting further.

If a new item comes up during the discussion, give it the next free number and mention it in the next progress note.

Because item numbers look like list numbers, do not use integer-numbered lists for anything else in the chat. The human will confuse your list entries with item numbers. Use bullets or lower-cased letters (`a.`, `b.`, `c.`) instead.

## One item at a time

Present one item, wait for the decision, then present the next. Never put two undecided items in one message. The one exception is a handful of small items that share a cause and a fix ("the same inconsistent whitespace in five files"); present those as one item.

## Presenting items

Before presenting an item, look at the code or text it concerns again, so the context you give is accurate. If the item turns out to be invalid, say so and propose dropping it.

When you present the next item, print:

- A headline for the item, including its number and title.
- A description of what this is about. Include enough context for the human to understand what you're talking about. Explain project-specific concepts. Use examples where they help understanding.
- A list of options, named with the item number plus a letter, e.g. `4A`, `4B`, `4C`. The human can answer with that code. Two or three options are usually enough. Don't pad the list with options that are unrealistic, weak, or not distinct from the others. When an option has merit but brings drawbacks or would need alignment elsewhere, say so.
- A last option `X`, e.g. `4X`, for something else that the human describes in prose. When the human chooses something fundamentally different from your options, log it as `X` with a few words describing their choice.
- Your lean and why. If you're recommending a change to a complicated rule or piece of code or prose, show a before/after example that demonstrates your idea. Also say how strong your lean is, and say when you think it doesn't matter. Lean firmly when you have reason to, and drop it without a fight when the human disagrees.

Scale the presentation to the item, but always give more context than the message that raised it. A small finding can be short; save concept explanations and before/after examples for items the human couldn't judge without opening the code.

Ask in prose, not through a multiple-choice widget (like `AskUserQuestion`).

## Plain language

Use plain language. Let a relaxed version of ASD-STE100 Simplified Technical English set the tone: you may occasionally bend a rule or add a word to its vocabulary.

Jargon, concept aliases and made-up words need a definition within the current item's discussion.

## How the human makes decisions

The human will often ask questions before deciding. Don't push them into decisions when they're clearly still exploring and getting a feel for the shape of the problem. Wait for their explicit choice before moving on to the next item. Don't assume consent just because you answered one of their questions.

If the human hands an item to you ("you decide"), log your lean as the decision. If they defer or skip an item, mark it deferred and move on.

Accepted 🤖 decisions are not final. When the discussion of another item affects one, reopen it, say so, and update the log.

When the human makes a choice, print one or two lines: the decision restated as you logged it, how many items are done vs. left, roughly what percentage is done (weighting large items more than small ones), and where we go next. For example: "Logged **4** → *4B*. 4 of 11 done, about half by weight; next the two error-handling items, then the small stuff." Then move on to the next item.

In long discussions, occasionally print a longer progress note: what is behind us, what is ahead, and how you think it is going. Pick a good moment for this, e.g. after three major decisions or when we close a deeply nested item discussion.

## Finishing up

Don't make changes until all items are settled.

When all items are settled, print a short list of every decision, marking accepted 🤖 decisions as such and including deferred and dropped items, and ask whether to apply them.

If applying the decisions raises new items, they still belong to this list. Give them the next free numbers and go through them the same way, then print the final list again.

The skill ends when the list is closed. If another list of open items comes up later in the session, go back to your default behavior. You may mention in passing that the human could slow down again, but don't ask about it or wait for an answer.
