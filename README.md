# triskweline/skills

A personal collection of [Agent Skills](https://docs.claude.com/en/docs/claude-code/skills) for use with Claude Code and other agent tools.

Each skill lives in `skills/<name>/SKILL.md` and encodes a reusable workflow.

## Available skills

| Skill | What it does |
| --- | --- |
| [`agree-on-everything`](skills/agree-on-everything/SKILL.md) | Turn requirements into an autonomously executable plan by resolving every open decision with the user before any code is written. |
| [`implement-autonomously`](skills/implement-autonomously/SKILL.md) | End-to-end workflow for implementing a full set of requirements on your own: confirm requirements, branch, test, verify, self-review, then hand off. |
| [`work-in-branch`](skills/work-in-branch/SKILL.md) | Make sure work happens on a properly named feature branch, following the repo's naming convention. |
| [`effective-rails-test`](skills/effective-rails-test/SKILL.md) | Default testing strategy for Ruby on Rails apps — unit specs for logic, a few E2E feature specs for frontend behavior, request specs for APIs. |
| [`run-all-tests`](skills/run-all-tests/SKILL.md) | Run the full test suite (locally, in parallel, or via CI) and address failures autonomously. |
| [`self-review`](skills/self-review/SKILL.md) | Have a sub-agent review your changes against the requirements, then reconcile and apply valid feedback. |

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
npx skills add https://github.com/triskweline/skills/tree/main/skills/effective-tests
```

By default skills install into the current project.\
Install skills globally using `--global`.

## Installing all skills for your user (symlink)

If you maintain this repo locally and want every skill available in **all** your Claude Code sessions, symlink each one into `~/.claude/skills`:

```bash
bin/link-all.sh
```

This syncs `~/.claude/skills/` to mirror this repo: it creates one symlink per `skills/*` folder, and it prunes stale links for skills that were renamed or removed. It is safe to re-run: existing correct links are left alone, it refuses to overwrite anything that isn't one of its own symlinks, and pruning only ever removes broken links that point back into this repo's `skills/` directory — links to other repos or unrelated files are never touched. Because the skills are symlinked (not copied), edits in this repo take effect immediately.

To link into a different directory:

```bash
SKILLS_DIR=~/.codex/skills bin/link-all.sh
```


## Adding a new skill

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
