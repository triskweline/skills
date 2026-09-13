# Verification tools common in Ruby on Rails apps

A Rails project usually runs some combination of these. Confirm against the project's CI
config before relying on any of them; the table is a hint about what to look for, not a
statement about this project.

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

Gem-provided tools usually need `bundle exec`, e.g. `bundle exec rspec`.
