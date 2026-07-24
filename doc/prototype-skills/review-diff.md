Your human is an overworked developer who needs to review lots of agent-generated code. Because the human is often switching between agents, projects and branches, it is hard for them to reload enough context into their brain so they can make a good review.

Help your human by explaining the current diff to them (everything that is not committed; including unstaged, staged and untracked changes; excluding git-ignored files).

Don't just go through the diff top to bottom. Instead, cluster all changes in thematical groups. Ideally each group forms a coherent, independent change (just for the purpose of explanation, it's OK if there is some dependencies between groups).

Start by listing each group, with only capation and a short explanation.

Then go through each group and explain it to the human:
 
- Print a loud header that captions this group
- Explain what part of the requirements is implement by this group
- Give a recap of how this group is implemented
- Explain what you changed.
- Show the diff of group-related changes, deletions and additions (can affect multiple files).
  - You can break apart a long diff into multiple sub-groups with their own explanations.
  - Every diff line must be printed somewhere. You cannot skip diff parts, even when you find them trivial.
  - Don't compress diffs in any ways to save screen space. Show the diff verbatim, including all comments, blank lines and other whitespace.
- When a group involves many files, start with the file that is the entry point for any user or caller, then follow the control flow to its leaves. E.g. when we have a new screen, the control flow is usually routing => controller => models => views => frontend assets (JS and CSS).
- Explain What requirements lead you to make this change.
- Why the shown group diff fulfills that requirement.
- If you did anything complex or uncommon, what lead you to that choice.
- Explain how this group contributes to the greater diff.

When you talk about a group (or a piece of a group), you must always print the diff next to your explanation.

After explaining a group, ask the human if they want to move on to the next group, or if they'd like to request any changes. Track any change requests for later, don't implement them yet.

If you find any small left-over changes that cannot be clustered into a group, explain all of that in a single go, with out short explanations.

Once you have explained the entire change, check if you have tracked any change request from your human. If there a change requests, repeat them to the human. Ask the human whether you should implement them now. After you implemented change requests, recap the changes to your human, showing diffs if needed. If the human had substantial change requests that caused you to rework a major part of your change, ask them if they would like to re-review the entire change again, or if the recap was enough.

When done, suggest a commit message and ask the human whether you should commit for them.

