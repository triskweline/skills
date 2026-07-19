---
name: self-review
---

Ask a sub-agent to review your work, briefing it with our requirements only. Leave out technical details that you discovered during the implementation.

Sub-agent review focus should be:
- Correctness: Does the new code fulfill requirements?
- Simplicity: Is there a simpler or more concise way to implement this functionality?
- Modularity: Was new code placed in the right modules (or classes)? Do changed models still have good cohesion and few responsibilities? If we overly diluted responsibilities, should we extract new modules?
- Readability: Did we use self-descriptive names for new functions, variables, modules, etc.? Is new control flow easy to follow for a human?
- Regressions: Does the new code conflict or damage behavior that existed before the change?
- Tests: Did we add test coverage for the new or changed functionality?

Analyze any issues the sub-agent reports and reconcile them with your own knowledge and opinions.
When you agree with a clear issue or obvious improvement, implement it directly, without asking the human.
Dismiss a sub-agent review item that is clearly invalid, or that you strongly disagree with.
Flag to the humans when decisions are truly hard or would have huge impact.
