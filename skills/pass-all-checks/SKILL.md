---
name: pass-all-checks
description: Confirm a change hasn't broken any current or past feature by running every check the repo has, which means enumerating its test runners and linters first (from CI config and project docs, so no linter is forgotten), then running the whole suite by the fastest route (local, parallel, or CI) and fixing failures yourself. This is the slow, exhaustive check for the whole codebase. Use after a non-trivial change before considering it done, when the user asks you to run the tests, run the suite, run linters, or check that nothing is broken, or when you need to find out which test and lint commands a project uses.
---

# Pass all checks

Run the repo's entire test suite and all linters, and fix any failures. This is a full, exhaustive check of the whole codebase — covering current and past features, not just what you changed — so it is often slow. Be smart about choosing the fastest method to start tests.

## Enumerate every check

"All tests and linters" means every check the project runs, not the ones you happen to remember. Agents rarely miss the test runner, but they routinely forget the smaller tools: a style linter, a security scanner, a dependency audit, an autoload check. Build the full list before you run anything.

### Check what you already know

Many projects document their test and lint commands for agents in `AGENTS.md` or `CLAUDE.md`, sometimes in the `README.md`. When such instructions exist and are detailed, believe them: they are the project's own rules, and rediscovering everything from scratch wastes time and risks running a tool the project has deliberately left out. Use the documented commands as your list and skip the discovery below.

Start discovery when no such instructions exist, when they name a tool but not how to run it, or when a documented command fails or turns out to be incomplete.

### Where to discover tools

The CI config is the definition of what must pass. Read every job and note its commands; if CI runs it, so do you.

- GitHub Actions: `.github/workflows/`
- GitLab CI: `.gitlab-ci.yml`
- Rails apps since 8.1 may define their checks in `config/ci.rb`, a DSL that lists each step and its command, and run them all with `bin/ci`. That file is the list; `bin/ci` runs it in one go.

When there is no CI config, derive the list from the source. The test directory (often `features`, `spec` or `test`) shows the test runner in use. The dependency manifest (e.g. `Gemfile`, `package.json`, `pyproject.toml`, `go.mod`) shows which runners and linters are installed, including the small ones that never appear in a test directory.

For a Ruby on Rails app, `references/rails-tools.md` lists the tools that commonly appear and their commands. Use it to recognize what you find in the manifest, not as a substitute for looking.

### Things to watch for

These hold whether you took the commands from the docs or discovered them yourself:

- Linters are sometimes called directly with their own runner. Sometimes a linter is called by a test, which then fails if the linter reports an issue.
- Likewise, JavaScript tests are sometimes called from an end-to-end (E2E) test that points a headless Chrome instance to a browser-based JavaScript test runner.
- A supporting library may allow running a large test suite in parallel processes instead of sequentially. These libraries usually wrap an existing test runner, e.g. `rake parallel:spec` for RSpec.
- In a Ruby app, gem-provided CLI tools often need to be called with `bundle exec`, e.g. `bundle exec rspec`.
- Projects occasionally define wrapper scripts that call the test runner with additional configuration, e.g. a `bin/test` script, a Rake task or an npm script. This would be visible in the README or CI config.

## Run linters before tests

Before you run the full test suite (slow!), run every linter from your list.
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

Running a large, full test suite via CI is generally favorable over using `parallel_tests`.

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

Now enumerate every check the project runs, find the fastest way to run the test suite, then make sure all tests and linters pass.
