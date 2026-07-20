# triskweline/skills

A personal collection of [Agent Skills](https://docs.claude.com/en/docs/claude-code/skills) for use with Claude Code and other agent tools.

Each skill lives in `skills/<name>/SKILL.md` and encodes a reusable workflow.

## Available skills

| Skill | What it does |
| --- | --- |
| [`agree-on-everything`](skills/agree-on-everything/SKILL.md) | Turn requirements into an autonomously executable plan by resolving every open decision with the user before any code is written. |
| [`implement-autonomously`](skills/implement-autonomously/SKILL.md) | End-to-end workflow for implementing a full set of requirements on your own: confirm requirements, branch, test, verify, self-review, then hand off. |
| [`self-review`](skills/self-review/SKILL.md) | Have a sub-agent review your changes against the requirements, then reconcile and apply valid feedback. |
| [`work-in-branch`](skills/work-in-branch/SKILL.md) | Make sure work happens on a properly named feature branch, following the repo's naming convention. |
| [`find-verification-tools`](skills/find-verification-tools/SKILL.md) | Discover which test runners and linters a project uses, and the exact CLI commands to run them. |
| [`full-verification`](skills/full-verification/SKILL.md) | Run the entire test suite and all linters (locally, in parallel, or via CI) and fix every failure — the slow, exhaustive check across current and past features. |
| [`effective-rails-testing`](skills/effective-rails-testing/SKILL.md) | Default testing strategy for Ruby on Rails apps — unit specs for logic, a few E2E feature specs for frontend behavior, request specs for APIs. |

## Installing skills

These commands use the [`skills` CLI](https://github.com/vercel-labs/skills) to install skills straight from this repo — no clone needed.

Open an interactive menu where you can list and install available skills:

```bash
npx skills add triskweline/skills
```

Install everything without prompts (`--all` installs every skill to every detected agent):

```bash
npx skills add triskweline/skills --all
```

Install a single skill by pointing at its directory:

```bash
npx skills add https://github.com/triskweline/skills/tree/main/skills/effective-rails-testing
```

By default skills install into the current project.\
Install skills globally using `--global`.


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
