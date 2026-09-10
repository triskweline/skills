# Working in this repository

A personal collection of Agent Skills. Each skill is a self-contained directory under
`skills/<name>/`, with its own `SKILL.md` and whatever references, scripts and tests it
needs.

## Commits

**Prefix the subject with the skill you worked on**, lowercase after the colon:

    diff-tour: pack chapters into forks rather than one fork each
    self-review: ask the reviewer for a verdict, not a summary

The prefix is what makes `git log --oneline` readable in a repo where unrelated skills
sit side by side — you can see at a glance which skill a change belongs to, and
`git log --oneline | grep '^\w* diff-tour:'` is the history of one skill.

**A change that is not about one skill takes no prefix**: repo-wide housekeeping, the
README, this file.

    Ignore Python bytecode caches

Write the subject as an imperative describing the change, not the file touched. Don't
add a body unless the reason genuinely does not fit in the subject.

## A skill's own conventions win

Anything about how a skill works — its procedure, its file layout, how its tests run —
belongs in that skill's own documentation, and that documentation is the authority. This
file only covers what is true across the repository.

Where a skill has tests, run them before committing a change to it. `diff-tour`, for
instance, has `skills/diff-tour/tests/test_difftour.py`.

`bin/test-all.sh` runs everything: the repo-wide suites under `tests/`, then each
skill's own suite. It discovers suites rather than listing them, so a new skill's tests
are picked up with no wiring. GitHub Actions runs that same script
(`.github/workflows/tests.yml`) on every push to main and on every pull request, so
"passes locally" and "passes on CI" are the same command. A branch with no pull request
open gets no CI run, which is the price of never running twice for one push. It needs only `python3`, `git` and `bash` — never add a pip install or a
version manager to either side.

CI deliberately runs a newer Python than this machine, which is the direction that warns
you early instead of flattering you. Keep the Python here compatible with both: standard
library only, no syntax newer than the oldest interpreter in use.

## Frontmatter has to parse for someone else's parser

`bin/check_frontmatter.py` checks every `skills/*/SKILL.md` frontmatter. Run it after
touching any frontmatter.

Claude Code reads frontmatter leniently, so a description that is not valid YAML loads
fine here and fails for whoever installs the skill with a stricter tool. The trap is that
a description is a long paragraph of prose: write `or commit: "walk me through this"` in
an unquoted value and YAML reads the colon-space as a key/value separator. Quote the
value or make it a block scalar (`description: >-`) when the prose needs punctuation that
YAML wants for itself.

## Skills that use other skills declare it in a dependency check

A skill whose instructions tell the agent to use another skill from this repo carries a
`## Dependency check` section directly after its title and intro paragraph, before any
other `##` heading. Its prose is this template, verbatim; only the table rows change:

```markdown
## Dependency check

This skill uses other skills from triskweline/skills. Check which of them are available in
this session by looking at the skills offered to you; do not search the filesystem.

| Skill | Role in this skill |
| --- | --- |
| `/<name>` | <what the skill does in this skill's process, one line> |

If all are available, say nothing about it and go on. For each missing skill, say in one
line that it is missing and what you use instead: another skill you have that fills the
role, or that you do the step yourself. Then continue. Where this skill's instructions name
a missing skill, use your substitute for the rest of this run. Do not ask whether to install
or what to substitute, and never install anything yourself.
```

The table lists exactly the repo skills the body refers to as `/name` in backticks, one row
each. The role column says what the dependency does in *this* skill's process, in this
skill's own words. Do not paste the other skill's description; it would drift.

A mention of a skill that is not in this repo, as a contrast or example like
`/code-review`, gets no row. Add its name to `ALLOWLIST` in the test instead.

Call sites in the body stay bare: "use the `/self-review` skill". Do not add a fallback
procedure at the call site, and do not write your own handling of a missing skill anywhere
else. The one-line role in the table is all the agent needs to substitute, and a how-to at
the call site invites it to skip the installed skill.

When you add, remove or rename a reference to another skill, update the table, and the
companion install line in the README when build-alone is affected.
`tests/test_skill_references.py` fails when a referenced skill does not exist or when a
table and its body disagree. The template wording and the README line are not checked;
keep them in step by hand.

## Never commit a corpus from a private repository

Test fixtures are written from the *shapes* that real diffs and tours revealed, never
copied out of them. If you keep patches or generated tours from a private repository
around to study, keep them outside the repository or gitignore the directory, and check
anything derived from them for private content before it is committed.
