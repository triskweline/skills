---
name: work-in-branch
description: Make sure your work lands on a suitable, well-named feature branch instead of a protected one like main or master, following the repo's naming convention. Use before you start making changes for a task, or whenever you notice you're about to commit work directly onto a protected branch.
---

Ensure that you are on a feature branch, not `master`, `main`, `dev` or `production`. If not, ask the user to make one.

Our default branch naming convention is `initials/ticket-slug`, e.g. `hk/123-sso-auth` for a user "Henning Koch", a linear issue ID `123` and a requirement like "Implement SSO authentication".
Branch naming conventions may differ between projects. Check precedence by looking at older branches with `git branch`.
Propose a branch name, ask the human for confirmation.

Ask the human whether to push the new feature branch to the remote. This is useful when we plan to later open a pull request for code reviews or CI tests.
