---
name: work-in-branch
---

Ensure that you are on a feature branch, not `master`, `main`, `dev` or `production`. If not, ask the user to make one.

Our default branch naming convention is `initials/ticket-slug`, e.g. `hk/123-sso-auth` for a user "Henning Koch", a linear issue ID `123` and a requirement like "Implement SSO authentication".
Branch naming conventions may differe between projects. Check precedence by looking at older branches with `git branch`.
Propose a branch name, ask the human for confirmation.

Ask the human whether to push the new feature branch to the remote. This is useful when we plan to later open a pull request for code reviews or CI tests.
