# triskweline/skills

A personal collection of [Agent Skills](https://docs.claude.com/en/docs/claude-code/skills) for use with Claude Code and other agent tools.

Each skill lives in `dev/<name>/SKILL.md` and encodes a reusable workflow — how to implement a feature autonomously, how to write effective tests, how to run the test suite, and so on. Skills are maintained here and made available to Claude Code either by installing them with `npx skills` or by symlinking them into `~/.claude/skills`.

## Available skills

| Skill | What it does |
| --- | --- |
| [`agree-on-everything`](dev/agree-on-everything/SKILL.md) | Turn requirements into an autonomously executable plan by resolving every open decision with the user before any code is written. |
| [`implement-autonomously`](dev/implement-autonomously/SKILL.md) | End-to-end workflow for implementing a full set of requirements on your own: confirm requirements, branch, test, verify, self-review, then hand off. |
| [`work-in-branch`](dev/work-in-branch/SKILL.md) | Make sure work happens on a properly named feature branch, following the repo's naming convention. |
| [`effective-tests`](dev/effective-tests/SKILL.md) | Default testing strategy — unit tests for logic, a few E2E specs for frontend behavior, request specs for APIs. |
| [`run-all-tests`](dev/run-all-tests/SKILL.md) | Run the full test suite (locally, in parallel, or via CI) and address failures autonomously. |
| [`self-review`](dev/self-review/SKILL.md) | Have a sub-agent review your changes against the requirements, then reconcile and apply valid feedback. |

## Installing individual skills

Use the [`skills` CLI](https://github.com/vercel-labs/skills) to install a skill straight from this repo — no clone needed.

List the skills available in this repo:

```bash
npx skills list triskweline/skills
```

Install a specific skill:

```bash
npx skills add triskweline/skills
```

You can also install a single skill by pointing at its directory:

```bash
npx skills add https://github.com/triskweline/skills/tree/main/dev/effective-tests
```

By default skills install into the current project. Consult `npx skills --help` for installing globally or for a specific agent.

## Installing all skills for your user (symlink)

If you maintain this repo locally and want every skill available in **all** your Claude Code sessions, symlink each one into `~/.claude/skills`:

```bash
bin/link-all.sh
```

This creates one symlink per `dev/*` folder inside `~/.claude/skills/`. It is safe to re-run: existing correct links are left alone, and it refuses to overwrite anything that isn't one of its own symlinks. Because the skills are symlinked (not copied), edits in this repo take effect immediately.

To link into a different directory:

```bash
SKILLS_DIR=/path/to/skills bin/link-all.sh
```

## Adding a new skill

1. Create `dev/<name>/SKILL.md`.
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
