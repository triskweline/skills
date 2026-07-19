---
name: effective-tests
description: Default testing strategy to use when the repo or instructions don't specify one. Favors short unit tests in models/classes, a few end-to-end feature/system specs (RSpec + Capybara/Selenium) for frontend behavior, and request specs for API endpoints. Use when deciding how to test new or changed behavior.
---

When you don't see a clear preference for testing style in your instructions or repo, here is an effective default strategy that gives you solid coverage with little code:

Prefer implementing logic in models or classes where they can be tested effectively with short unit tests. Avoid fat controllers and controller tests when possible.

New behavior with frontend impact (e.g. screens are added or changed) should be tested with few end-to-end tests (E2E tests).
These are usually RSpec feature specs or system specs that drive a headless browser using Capybara / Selenium.

But don't add slow E2E tests for every edge case that is already covered by cheap unit tests. For example, when a form has complex validations, the many error states should mostly be tested with unit tests.
It is then enough to have an E2E test for the key scenarios (valid form submits, invalid form shows error messages), without re-iterating every possible error state.

When writing API endpoints (e.g. RESTful JSON API), test your behavior using request specs (instead of E2E tests).
