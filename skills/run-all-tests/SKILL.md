---
name: run-all-tests
description: Confirm a change hasn't broken anything by getting the repo's entire test suite green, picking the fastest route (local, parallel, or CI) and fixing failures yourself. Use after a non-trivial change before considering it done, or when the user asks you to run the tests, run the suite, or check that nothing is broken.
---

# Run all tests

Run the full test suite for the current repo and fix any failures. This is often a slow process, so you must be smart about choosing the fastest method to start tests.

## Identify the test runner

First figure out the test runner. Look for a test directory (usually `features`, `spec` or `test`), a config or dependency manifest (e.g. `Gemfile`, `package.json`, `pyproject.toml`, `go.mod`), and any test scripts or CI config. Match the runner to the toolchain rather than assuming one.
For Ruby on Rails apps this is usually RSpec, sometimes Cucumber, sometimes Minitest, and sometimes a combination of these.

## Choose how to run the suite

Check the size of the test suite, usually in the features, spec or test folders.

Small test suites can be run locally.

Large test suites may take a long time to run locally. Especially end-to-end tests (E2E tests) are slow, and this project may have many of them.
Luckily, there are ways to shorten the wait:

- A project may use parallel_tests gem to run tests in multiple parallel processes. It exposes rake tasks like `rake parallel:spec` or `rake parallel:cucumber`. Expect heavy CPU load while this is running.
- If the repo is hosted on GitHub, you may be able to create a pull request and monitor CI there. Check `git remote -v` for a github.com remote. CI config is usually in `.github/workflows/`. Also check if the `gh` CLI tool is configured to work with the remote (check `gh pr list`).
- If the repo is hosted on GitLab, you may be able to create a merge request and monitor CI there. Check `git remote -v` for a gitlab.com or code.makandra.de (self-hosted GitLab) remote. CI config is usually in `.gitlab-ci.yml`. Check if the `glab` CLI tool is configured to work with the remote (`glab mr list`).

Make sure you see the full output of the test suite, so you get a full list of eventual failures. Avoid running test suites with `head` or `tail`, as this might cut off vital information and necessitate another slow run.

## Handle failures

Check failures from the test run.

Try to address test failures autonomously, and only involve the human when you run into true blockers that you cannot resolve on your own (e.g. E2E tests fail to start at all and you don't know why).

If the test suite mostly passed, and you only encountered individual failures, verify fixes by re-running only those specs locally.
When a large part of the full suite failed, address all failures in a batch edit, then re-run the entire suite.
Large-scale failures are often caused by bugs in factories or shared test setup, which can affect a large number of tests.

## Begin your work

Now find the best way to run the test suite, and drive it to green.

