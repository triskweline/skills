---
name: self-review
description: Get an independent second opinion on the code you just wrote — an outside pass for correctness, simplicity, regressions, and missing tests that you're too close to the work to catch — and fold the valid feedback back in. Use after implementing a change and before handing it to the user, or whenever you want to double-check your own work before calling it done.
---

# Self review

Your task is to review a code change you just wrote, and improve your work with the review feedback.
The goal is to meaningfully improve the quality of code that was generated autonomously, reducing the burden on a human code review to find all faults.
Ideally, your review-improved change can be merged by a human with only a cursory manual review and little to no additional changes.

## Tasking a sub-agent

Ask a **sub-agent** to review your work, briefing it with our requirements only. Leave out technical details that you discovered during the implementation, to ensure that the sub-agent's review represents a true secondary opinion.

The sub-agent review should focus on the following quality dimensions:

- **Correctness:** Does the new code fulfill requirements?
- **Simplicity:** Is there a simpler or more concise way to implement this functionality?
- **Modularity:** Was new code placed in the right modules (or classes)? Do changed models still have good cohesion and few responsibilities? If we overly diluted responsibilities, should we extract new modules?
- **Don't Repeat Yourself (DRY):** Does every new piece of knowledge or business rule have a single, authoritative representation within the system? Are there existing code and components we could re-use for our new functionality?
- **Readability:** Did we use self-descriptive names for new functions, variables, modules, etc.? Is new control flow easy to follow for a human?
- **Canonicity:** Does the change follow established patterns in this project?
- **Regressions:** Does the new code conflict or damage behavior that existed before the change?
- **Tests:** Did we add test coverage for the new or changed functionality?
- **Performance:** Does the new code make excessive database queries? Do we process large amounts of data in application code instead of pushing that work off to the database? Should heavy work be moved to an async background job?

For each dimension the sub-agent should return:

1. A list of findings or violations related to the dimension.
   Ideally, each finding is paired with a recommendation or alternative that would improve the quality of the code.
2. An overall status for the dimension: **clean**, **minor issues**, or **significant issues**. For anything other than clean, the findings must justify the status.

It is not the sub-agent's job to reconcile quality dimensions that are in tension with each other.
This is done by you (the main agent) after the sub-agent terminates, in the next step.

## Processing the review results

Understand, verify and judge all findings the sub-agent reports.
Reconcile findings with your own knowledge and opinions.

Sometimes quality dimensions are in tension with each other. For example:

- Code re-use (DRY dimension) can increase coupling between modules (Modularity dimension)
- Highly performant code (Performance dimension) is often convoluted (Simplicity dimension) and less readable (Readability dimension)

It is up to you to balance these goals and pick a trade-off.
Generally it's OK to accept some deviation in one dimension when it strongly serves another.

When you agree with a clear issue or obvious improvement, implement it directly, without asking the human.
Dismiss a sub-agent review finding that is clearly invalid, or that you strongly disagree with.
Flag to the human when decisions are truly hard or would have huge impact.
