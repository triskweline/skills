#!/usr/bin/env python3
"""Check that skills refer to other skills consistently.

    python3 tests/test_skill_references.py

Standard library only, like everything else here, and it must pass on both the
oldest Python anyone runs locally and the newest one CI happens to have.

A skill names another skill as `/name` in backticks. Two things go wrong with
that over time, and this suite catches both:

  * The named skill was renamed or removed. Every rename so far updated every
    referrer by hand; this makes the next one fail loudly instead.
  * The skill's "Dependency check" table (see AGENTS.md) and its body disagree:
    the body started using a skill the table does not list, or the table still
    lists a skill the body no longer uses.

Deliberately small. The template wording of the section and the README's
companion install line are not checked; a grep shows drift there in a second.
"""

import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(ROOT, 'skills')

# Skills that are mentioned as a contrast or an example but do not live in this
# repo. They get no table row.
ALLOWLIST = {'code-review', 'grill-me'}

# Only backticked slash names count. A bare /[a-z-]+ would match paths and HTML.
REFERENCE = re.compile(r'`/([a-z][a-z0-9-]*)`')
SECTION_HEADING = '## Dependency check'
TABLE_ROW = re.compile(r'^\|\s*`/([a-z][a-z0-9-]*)`\s*\|')


def skills():
    return sorted(name for name in os.listdir(SKILLS_DIR)
                  if os.path.isfile(os.path.join(SKILLS_DIR, name, 'SKILL.md')))


def body(skill):
    """The SKILL.md text after the frontmatter."""
    with open(os.path.join(SKILLS_DIR, skill, 'SKILL.md'), encoding='utf-8') as f:
        text = f.read()
    if text.startswith('---\n'):
        end = text.index('\n---\n', 4)
        text = text[end + len('\n---\n'):]
    return text


def split_section(text):
    """Return (section, rest): the Dependency check section, and everything else.

    The section runs from its heading to the next line that starts a heading.
    `section` is '' when the skill has none.
    """
    lines = text.split('\n')
    section, rest, inside = [], [], False
    for line in lines:
        if line.strip() == SECTION_HEADING:
            inside = True
        elif inside and line.startswith('#'):
            inside = False
        (section if inside else rest).append(line)
    return '\n'.join(section), '\n'.join(rest)


def table_skills(section):
    found = set()
    for line in section.split('\n'):
        match = TABLE_ROW.match(line)
        if match:
            found.add(match.group(1))
    return found


class SkillReferences(unittest.TestCase):

    def test_every_reference_resolves(self):
        known = set(skills()) | ALLOWLIST
        for skill in skills():
            for name in REFERENCE.findall(body(skill)):
                self.assertIn(name, known,
                              '%s refers to `/%s`, which is neither a skill in this repo '
                              'nor on the ALLOWLIST in this test' % (skill, name))

    def test_table_matches_body(self):
        repo = set(skills())
        for skill in skills():
            section, rest = split_section(body(skill))
            used = (set(REFERENCE.findall(rest)) & repo) - {skill}
            listed = table_skills(section)
            self.assertEqual(
                used, listed,
                '%s: Dependency check table disagrees with the body. Missing rows: %s. '
                'Rows for skills the body does not use: %s.'
                % (skill, sorted(used - listed) or 'none', sorted(listed - used) or 'none'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
