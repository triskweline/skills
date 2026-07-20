---
name: find-verification-tools
description: Discover which test runners and linters a project uses, and the exact CLI commands to run them, so you can verify code changes. Use when you need to run or locate a project's tests or linters but don't already know the commands.
---

# Find verification tools

Identify testing frameworks and linters that an agent can use to verify code changes.

## Detecting tools

Check if the project has existing guidance for running tests or linters, often documented in a `README.md`, `AGENTS.md` or `CLAUDE.md`.

You can also check the source code for traces:

- Check the CI config (e.g. `.gitlab-ci.yml`, `.github/workflows/`).
  This is often the best source for CLI commands you *know* must run successfully.
- Look for a test directory (often `features`, `spec` or `test`).
- Look for a config or dependency manifest (e.g. `Gemfile`, `package.json`, `pyproject.toml`, `go.mod`).

Projects often use multiple test runners or linters for different purposes.

## Identify CLI commands

You will need to know the exact CLI commands needed to run tests.
Derive that from the tools you discovered, e.g. RSpec is usually called using the `rspec` command.
We also provide an example of widely used tools and their commands below.

There are some peculiarities when running tests:

- Linters are sometimes called directly with their own runner. Sometimes the linter is called by a test, which then fails if the linter reports an issue.
- Likewise, JavaScript tests are sometimes called from an end-to-end (E2E) test that points a headless Chrome instance to a browser-based JavaScript test runner.
- Sometimes a supporting library allows running a large test suite using parallel processes instead of sequentially. These libraries usually wrap an existing test runner.
  E.g. RSpec tests can often be run in parallel using the `rake parallel:spec` command.
- In a Ruby app, gem-provided CLI tools often need to be called with `bundle exec`, e.g. `bundle exec rspec`.
- Projects will occasionally define wrapper scripts that call the test runner with additional configuration, e.g. `bin/test` script, a Rake task or an npm script.
  This would be visible in the README or CI config.

## Examples of widely used tools

In a Ruby on Rails application, some combination of following testing tools and linters are commonly used:

| Name           | CLI command                                         | Purpose                                                    |
|----------------|-----------------------------------------------------|------------------------------------------------------------|
| RSpec          | `rspec`                                             | Run all types of tests (unit tests, E2E tests, ...)        |
| Cucumber       | `cucumber`                                          | Often used for E2E tests                                   |
| Minitest       | `rake test` or `bin/rails test`                     | Run all types of tests (unit tests, E2E tests, ...)        |
| RuboCop        | `rubocop`                                           | Enforce consistent coding style in Ruby files              |
| Zeitwerk check | `rake zeitwerk:check` or `bin/rails zeitwerk:check` | Ensure all Ruby files can be auto-loaded                   |
| Brakeman       | `brakeman`                                          | Check for security issues in code (like XSS)               |
| bundler-audit  | `bundle-audit`                                      | Check for vulnerable Ruby dependencies                     |
| ESLint         | `eslint` or `pnpm run lint`                         | Ensure consistent coding style in JavaScript files         |
| Vitest         | `vitest` or `pnpm run test`                         | Tests for JavaScript modules and client-side UI components |
| Jasmine        | Often called from E2E test                          | Tests for JavaScript modules and client-side UI components |

## Now identify

Now identify test and linter commands, using the instructions above.
