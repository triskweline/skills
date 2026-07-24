---
name: full-verification
description: Confirm a change hasn't broken any current or past feature by running the repo's entire test suite and all linters, picking the fastest route (local, parallel, or CI) and fixing failures yourself. This is the slow, exhaustive check for the whole codebase. Use after a non-trivial change before considering it done, or when the user asks you to run the tests, run the suite, run linters, or check that nothing is broken.
---

# Full verification

Run the repo's entire test suite and all linters, and fix any failures. This is a full, exhaustive check of the whole codebase — covering current and past features, not just what you changed — so it is often slow. Be smart about choosing the fastest method to start tests.

## Check which tools are available

If you are unsure what testing and linting tools are used in this project, use the `/find-verification-tools` skill.

## Run linters before tests

Before you run the full test suite (slow!), run the linter tools you discovered.
Linter tools are a fast pre-check. This will let you avoid failing a full CI run due to a formatting nitpick detected by Rubocop (or other linters).

Make sure you see the full output of the linter, so you get a full list of eventual failures.
Avoid running linters with `head` or `tail`, as this might cut off vital information and require another run just to discover what's wrong.

Fix any reported linter issues.
Linter complaints are often easy to fix. Some linters even offer a way to do it automatically, e.g. `bundle exec rubocop -A`.
When you have fixed a linting issue, re-run the linter tool that complained.
Never run the entire test suite (slow!) only to verify a fix for a linting issue.

## Run the full test suite

### Discover the fastest route

Check the size of the test suite. Test files are usually in the `features`, `spec` or `test` folders.

**Small test suites** can be run by starting the test runner process locally.

**Large test suites** may take a long time to run locally. Especially end-to-end tests (E2E tests) are slow, and this project may have many of them.
Luckily, there are ways to shorten the wait:

- A project may use `parallel_tests` gem to run tests in multiple parallel processes. It exposes rake tasks like `rake parallel:spec` or `rake parallel:cucumber`. Expect heavy CPU load while this is running.
- If the repo is hosted on GitHub, you may be able to create a pull request and monitor CI there. Check `git remote -v` for a github.com remote. CI config is usually in `.github/workflows/`. Also check if the `gh` CLI tool is configured to work with the remote (using `gh pr list`).
- If the repo is hosted on GitLab, you may be able to create a merge request and monitor CI there. Check `git remote -v` for a gitlab.com or code.makandra.de (self-hosted GitLab) remote. CI config is usually in `.gitlab-ci.yml`. Check if the `glab` CLI tool is configured to work with the remote (using `glab mr list`).

### Start the test run

Now start the full test suite, using the fastest route you discovered earlier (local, parallel, or CI).

Make sure you see the full output of the test suite, so you get a full list of eventual failures.
Avoid running test suites with `head` or `tail`, as this might cut off vital information and require another slow run just to discover what's wrong.

### Handle failures

Check failures from the test run.

Try to address test failures autonomously, and only involve the human when you run into true blockers that you cannot resolve on your own (e.g. E2E tests fail to start at all and you don't know why).

If the test suite mostly passed, and you only encountered individual failures, verify fixes by re-running only those specs locally.
When a large part of the full suite failed, address all failures in a batch edit, then re-run the entire suite.
Large-scale failures are often caused by bugs in factories or shared test setup, which can affect a large number of tests.

## Begin your work

Now find the best way to run the test suite, then make sure all tests and linters pass.
