---
name: work-in-branch
description: Make sure your work lands on a private feature branch and avoid breaking a protected branch like `main` or `master`. Use before you start making changes for a non-trivial task, or whenever you notice you're about to commit unreviewed work directly onto a protected branch.
---

# Work in a branch

Ensure that you are on a feature branch, not `master`, `main`, `dev` or `production`.
If not, ask the human whether to create one. If they agree, you create the branch yourself.

## Branch naming convention

Branch naming conventions may differ between projects. Check the project's house style by looking at older branches with `git branch -a`. Past branch naming may not be fully consistent, but you will usually see a predominant naming convention.
Our fallback branch naming convention is `initials/ticket-slug`, e.g. `hk/123-sso-auth` for a user "Henning Koch", a linear issue ID `123` and a requirement like "Implement SSO authentication".
Project house style wins over fallback convention.

Propose a branch name, ask the human for confirmation, then create the branch.

## Local or remote branch

Ask the human whether to push the new feature branch to the remote.
This is useful when we plan to later open a pull request for code reviews or CI tests.

## Begin your work

Now check whether we need a branch, and create one if needed.
