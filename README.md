# triskweline/skills

A personal collection of [Agent Skills](https://docs.claude.com/en/docs/claude-code/skills) for use with Claude Code and other agent tools.

## Software development lifecycle

A comprehensive set of skills to move software requirements from idea to deployment,
with strong human direction but minimal context switches. Each skill hands off to the
next, and every skill also works on its own.

### 🧭 [`/explore-solutions`](skills/explore-solutions/SKILL.md)

> Explores the solution space for a requirement before planning: scans the codebase, generates
> genuinely different approaches, compares their trade-offs from a bird's-eye view, and narrows
> down to a primary candidate and its fallbacks. Ends with candidates, not a plan.

<details>
<summary>Install this skill</summary>

> ```bash
> npx skills add triskweline/skills --global --skill explore-solutions
> ```
>
> Drop `--global` to install into the current project instead of your user account.

</details>

### 🤝 [`/agree-on-everything`](skills/agree-on-everything/SKILL.md)

> Turns a requirement with a settled approach into a plan an agent can execute without further
> questions. Walks through the future implementation, surfaces every decision, edge case and
> blocker, and settles each one with you before any code is written.

<details>
<summary>Install this skill</summary>

> ```bash
> npx skills add triskweline/skills --global --skill agree-on-everything
> ```
>
> Drop `--global` to install into the current project instead of your user account.

</details>

### 🏗️ [`/build-alone`](skills/build-alone/SKILL.md)

> Carries a set of requirements all the way to a tested, self-reviewed implementation that is
> ready to hand back. Confirms requirements, branches, tests, verifies and self-reviews on its
> own, interrupting you only for true showstoppers.

<details>
<summary>Install this skill</summary>

> ```bash
> npx skills add triskweline/skills --global --skill build-alone \
>   agree-on-everything \
>   work-in-branch \
>   pass-all-checks \
>   self-review
> ```
>
> The first name is the skill itself, the rest are the skills it uses for single steps of its
> process. They are optional: leave any of them out and the agent tells you in one line what
> is missing and what it does instead. Drop `--global` to install into the current project instead
> of your user account.

</details>

### 🗺️ [`/diff-tour`](skills/diff-tour/SKILL.md)

> Walks you through a diff you did not write but must review and take responsibility for.
> Produces one self-contained HTML report that narrates the change as a tour: chapters in a
> reading order that builds understanding, every hunk beside prose that says what it is for,
> and a mark on each hunk saying how carefully it deserves to be read.

<details>
<summary>Install this skill</summary>

> ```bash
> npx skills add triskweline/skills --global --skill diff-tour
> ```
>
> Drop `--global` to install into the current project instead of your user account.

</details>

## Utility skills

Smaller skills that do one job well. The lifecycle skills above use them for single steps of
their process.

You can install a skill without the skills it uses. It will then tell you in one line what
is missing and what it does instead: either a skill of yours that fills the same role, or
the step done by hand. If you would rather have the original, add its name to the `--skill` list
of the install command, which takes any number of skill names.

### 🌿 [`/work-in-branch`](skills/work-in-branch/SKILL.md)

> Makes sure work happens on a properly named feature branch, following the repo's naming
> convention, instead of landing unreviewed on a protected branch like `main`.

<details>
<summary>Install this skill</summary>

> ```bash
> npx skills add triskweline/skills --global --skill work-in-branch
> ```
>
> Drop `--global` to install into the current project instead of your user account.

</details>

### ✅ [`/pass-all-checks`](skills/pass-all-checks/SKILL.md)

> Enumerates every check the project runs, from its CI config and docs, so that no linter is
> forgotten. Then runs the entire test suite by the fastest route (local, parallel, or CI) and
> fixes every failure. The slow, exhaustive check across current and past features.

<details>
<summary>Install this skill</summary>

> ```bash
> npx skills add triskweline/skills --global --skill pass-all-checks
> ```
>
> Drop `--global` to install into the current project instead of your user account.

</details>

### 🔍 [`/self-review`](skills/self-review/SKILL.md)

> Has a sub-agent review your changes against the requirements for correctness, simplicity,
> regressions and missing tests, then reconciles the feedback and applies what is valid.

<details>
<summary>Install this skill</summary>

> ```bash
> npx skills add triskweline/skills --global --skill self-review
> ```
>
> Drop `--global` to install into the current project instead of your user account.

</details>

### 💎 [`/effective-rails-testing`](skills/effective-rails-testing/SKILL.md)

> Decides what kind of test to write for a change in a Ruby on Rails app: unit specs for logic,
> a few end-to-end feature specs for frontend behavior, request specs for APIs.

<details>
<summary>Install this skill</summary>

> ```bash
> npx skills add triskweline/skills --global --skill effective-rails-testing
> ```
>
> Drop `--global` to install into the current project instead of your user account.

</details>

## Development

### Installing all skills for your user (symlink)

If you maintain this repo locally and want every skill change immediately available in **all** your Claude Code sessions, symlink each one into `~/.claude/skills`:

```bash
bin/link-all.sh
```

This syncs `~/.claude/skills/` to mirror this repo: it creates one symlink per `skills/*` folder, and it prunes stale links for skills that were renamed or removed.

To link into a different directory:

```bash
SKILLS_DIR=~/.codex/skills bin/link-all.sh
```


### Adding a new skill

1. Create `skills/<name>/SKILL.md`.
2. Add YAML frontmatter with a `name` (matching the folder name) and a descriptive `description` so agents can discover it:

   ```yaml
   ---
   name: my-skill
   description: What the skill does and when an agent should use it.
   ---
   ```

3. Write the instructions below the frontmatter.
4. Run `bin/link-all.sh` to link it into `~/.claude/skills`.

## License

[MIT](LICENSE)
