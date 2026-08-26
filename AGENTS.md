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

## Never commit a corpus from a private repository

`skills/diff-tour/_examples/` is gitignored on purpose: it holds patches and narrations
from real, private repositories, kept locally so test fixtures can be distilled from
them. The fixtures that land in git are written from the *shapes* those files revealed,
never copied out of them. If you add another corpus directory, gitignore it the same way
and check it with `skills/diff-tour/tests/scrub.py` first.
