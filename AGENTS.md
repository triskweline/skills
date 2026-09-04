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

## Never commit a corpus from a private repository

Test fixtures are written from the *shapes* that real diffs and tours revealed, never
copied out of them. If you keep patches or generated tours from a private repository
around to study, keep them outside the repository or gitignore the directory, and check
anything derived from them for private content before it is committed.
