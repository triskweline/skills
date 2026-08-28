#!/usr/bin/env python3
"""Tests for the SKILL.md frontmatter check.

    python3 tests/test_frontmatter.py

Standard library only, like the code under test, and it must pass on both the
oldest Python anyone here runs and the newest one CI happens to have. PyYAML is
therefore never required: the strict-parse tests skip themselves when it is
missing, so the suite behaves the same on a laptop that has it and a runner that
does not.

Two halves, and the second is the one that earns its keep:

  * The hazard lint flags prose that ends a plain YAML scalar early. A bug here
    means a broken skill ships.
  * The lint must NOT flag prose that is already safe -- quoted values, and the
    continuation lines of a block scalar, which are free text and may contain
    anything. A false positive here is worse than no lint at all, because it
    trains you to ignore the check.
"""

import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'bin'))
import check_frontmatter   # noqa: E402


def problems_for(frontmatter, skill='demo'):
    """Run the lint over a frontmatter body, in a directory named `skill`.

    The body is placed between --- markers, so line 1 of `frontmatter` is line 2
    of the file -- the same offset a real SKILL.md has.
    """
    tmp = tempfile.mkdtemp()
    directory = os.path.join(tmp, skill)
    os.makedirs(directory)
    path = os.path.join(directory, 'SKILL.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('---\n' + frontmatter.strip('\n') + '\n---\n\n# Demo\n')
    return check_frontmatter.check(path)


def one_problem(frontmatter, skill='demo'):
    return one_problem_of(problems_for(frontmatter, skill))


def one_problem_of(problems):
    """Assert the lint found exactly one thing, and return it.

    Exactly one, because a check that reports a real problem plus two spurious
    ones is a check nobody reads.
    """
    assert len(problems) == 1, 'expected exactly one problem, got %r' % (problems,)
    return problems[0]


VALID = 'name: demo\ndescription: Plain prose with no YAML punctuation in it at all.'


class TestTheLintCatchesWhatBrokeAUser(unittest.TestCase):
    """The reported bug and its siblings: prose that ends a plain scalar early."""

    def test_colon_space_in_an_unquoted_description(self):
        """The bug that shipped: `or commit: "walk me through this"`."""
        problem = one_problem(
            'name: demo\n'
            'description: Use this when someone says, of a commit: "walk me through it".')
        self.assertIn('colon-space', problem)
        self.assertIn('description', problem)

    def test_the_reported_column_points_at_the_colon(self):
        """A user reports a column; it has to land on the offending character."""
        problem = one_problem('name: demo\ndescription: One two: three.')
        # 'description: One two' is 20 characters, so the colon is at column 21.
        self.assertIn('column 21', problem)

    def test_the_reported_line_counts_from_the_top_of_the_file(self):
        """Line 1 is the opening ---, so the first key is line 2."""
        problem = one_problem('name: demo\ndescription: One two: three.')
        self.assertIn('SKILL.md:3:', problem)

    def test_a_description_ending_in_a_colon(self):
        problem = one_problem('name: demo\ndescription: Use when the user says:')
        self.assertIn('ends with ":"', problem)

    def test_a_hash_that_starts_a_yaml_comment(self):
        """PyYAML accepts this and silently truncates the value, so only the
        lint can catch it. That is the whole argument for having a lint."""
        problem = one_problem('name: demo\ndescription: Use this for C #tags and such.')
        self.assertIn('comment', problem)

    def test_a_value_that_opens_with_flow_syntax(self):
        problem = one_problem('name: demo\ndescription: [not a list, just prose')
        self.assertIn('starts with', problem)

    def test_a_tab_in_a_value(self):
        problem = one_problem('name: demo\ndescription: Prose with\ta tab in it.')
        self.assertIn('tab', problem)


class TestTheLintLeavesSafeProseAlone(unittest.TestCase):
    """False positives train you to ignore the check, so they are the priority."""

    def test_the_repository_is_clean(self):
        """The lint must be quiet on prose that is merely long and comma-heavy."""
        self.assertEqual([], problems_for(VALID))

    def test_a_block_scalar_may_contain_anything(self):
        """This is how diff-tour's own description is written, and it contains
        two colon-spaces. Flagging its continuation lines would be the bug."""
        self.assertEqual([], problems_for(
            'name: demo\n'
            'description: >-\n'
            '  Use this when someone says, of a commit: "walk me through it", and\n'
            '  also when this: that. Not an automated bug hunt: it only explains.\n'))

    def test_every_block_scalar_spelling(self):
        """`>-` is what we use, but the check must not depend on that choice."""
        for indicator in ('|', '>', '|-', '>-', '|+', '>+', '|2', '>2-'):
            self.assertEqual([], problems_for(
                'name: demo\ndescription: %s\n  colon: space in here\n' % indicator),
                'block scalar %r was linted as a plain scalar' % indicator)

    def test_a_quoted_value_may_contain_a_colon(self):
        for value in ('"Use this, of a commit: walk me through it."',
                      "'Use this, of a commit: walk me through it.'"):
            self.assertEqual([], problems_for(
                'name: demo\ndescription: %s' % value),
                'quoted value was linted: %s' % value)

    def test_a_blank_line_inside_a_block_scalar(self):
        """A paragraph break does not end the block scalar."""
        self.assertEqual([], problems_for(
            'name: demo\n'
            'description: >-\n'
            '  First paragraph, of a commit: like so.\n'
            '\n'
            '  Second paragraph: also fine.\n'))

    def test_a_key_after_a_block_scalar_is_linted_again(self):
        """Leaving block-scalar mode matters: the next plain value is prose too."""
        problem = one_problem(
            'name: demo\n'
            'description: >-\n'
            '  Safe in here: yes.\n'
            'summary: Not safe out here: no.\n')
        self.assertIn('summary', problem)

    def test_nested_keys_are_not_required_to_be_top_level(self):
        self.assertEqual([], problems_for(
            VALID + '\nmetadata:\n  version: 2.0.0\n'))


class TestTheStructuralChecks(unittest.TestCase):

    def test_a_file_with_no_frontmatter(self):
        tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(tmp, 'demo'))
        path = os.path.join(tmp, 'demo', 'SKILL.md')
        with open(path, 'w', encoding='utf-8') as f:
            f.write('# Demo\n\nNo frontmatter at all.\n')
        self.assertIn('no frontmatter', one_problem_of(check_frontmatter.check(path)))

    def test_unterminated_frontmatter(self):
        tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(tmp, 'demo'))
        path = os.path.join(tmp, 'demo', 'SKILL.md')
        with open(path, 'w', encoding='utf-8') as f:
            f.write('---\nname: demo\ndescription: Never closed.\n')
        self.assertIn('no frontmatter', one_problem_of(check_frontmatter.check(path)))

    def test_a_missing_description(self):
        self.assertIn('no top-level description', one_problem('name: demo'))

    def test_a_missing_name(self):
        problems = problems_for('description: Prose with no name key above it.')
        self.assertTrue(any('no top-level name' in p for p in problems), problems)

    def test_a_name_that_disagrees_with_its_directory(self):
        """Installers address a skill by directory; a mismatch renames it."""
        problem = one_problem(
            'name: something-else\ndescription: Prose.', skill='demo')
        self.assertIn("but the directory is 'demo'", problem)

    def test_a_quoted_name_still_matches_its_directory(self):
        self.assertEqual([], problems_for('name: "demo"\ndescription: Prose.'))


class TestTheRealSkills(unittest.TestCase):
    """The data check: what bin/check_frontmatter.py reports in anger."""

    def skills(self):
        skills_dir = os.path.join(ROOT, 'skills')
        paths = sorted(os.path.join(skills_dir, name, 'SKILL.md')
                       for name in os.listdir(skills_dir)
                       if os.path.isfile(os.path.join(skills_dir, name, 'SKILL.md')))
        self.assertTrue(paths, 'found no skills under skills/*/SKILL.md')
        return paths

    def test_every_skill_passes_the_lint(self):
        for path in self.skills():
            self.assertEqual([], check_frontmatter.check(path),
                             os.path.relpath(path, ROOT))

    def test_every_skill_parses_under_a_strict_parser(self):
        """Skipped where PyYAML is absent -- the lint above is the guarantee."""
        try:
            import yaml   # noqa: F401
        except ImportError:
            raise unittest.SkipTest('PyYAML is not installed')
        for path in self.skills():
            self.assertEqual([], check_frontmatter.strict_parse(path),
                             os.path.relpath(path, ROOT))


if __name__ == '__main__':
    unittest.main(verbosity=2)
