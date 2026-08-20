---
name: what-will-it-take
description: Use when the user wonders how hard it is to implement a software requirement. How much is already implemented, what could be re-used, what is missing entirely and needs to be added from scratch. 
---

The human might not be fully familiar with the code base. You need to get the human oriented, so they can make informed decisions (rather than mechanically follow our recommended options).
So before you discuss the first decision, get the human on board with a short orientation:

- Explain what parts of the requirements are already implemented in the existing code.
  Where it helps your explanation, you can name key classes,
  functions or UI components that will likely play a role with this new change.
- Explain what is still missing in the code, to meet the requirements.
  Talk abstractly, e.g. "The code doesn't currently have a way to...".
  Avoid talking specifics, because those will only be decided in the discussion that follows.
  The goal of this orientation is to show the human what hole our change needs to fill, but not how we are going to fill it.
  Do not nudge the human in any specific direction here.
- Highlight the most difficult aspect of this change (if one stands out).
- Highlight the most important choice that we must lock in first (if there is one). This should be the key decision on which many other decisions depend.

Now that we have oriented the human, we can discuss decisions.
