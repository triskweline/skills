---
name: run-all-tests
---

Run the full test suite for the current repo.

Check the size of the test suite, usually in the features, spec or test folders.

Small test suites can be run locally.

Large test suites may take a long time to run locally. Ways to shorten this time:

- A project may use parallel_tests gem to run tests in multiple parallel processes. It exposes rake tasks like `rake parallel:spec` or `rake parallel:cucumber`. Expect heavy CPU load while this is running.
- If repo is hosted on GitHub, you may be able to create a pull request and monitor CI there. Check `git remote -v` for a github.com remote. CI config is usually in `.github/workflows. Also check if the `gh` CLI tool are configured to work with remote merge requests (check `gh pr list`).
- If repo is hosted on GitLabe, you may be able to create a merge request and monitor CI there. Check `git remote -v` for a gitlab.com or code.makandra.de (self-hosted GitLab) remote. CI config is usually in `.gitlab-ci.yml`. Check if the CLI tools isconfigured to work with remote mergerequests (`gl pr list`).

Check failures from the test run. Try to address test failures autonomously, and only involve the human when you run into true blockers that you cannot resolve on your own (e.g. E2E tests fail to start at all and you don't know why).
If the test suite mostly passed, and you only encountered individual failures, verify fixes by re-running only those specs locally.
When a large part of the full suite failed, you need to re-run the entire suite.
