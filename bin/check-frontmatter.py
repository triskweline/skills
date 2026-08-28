#!/usr/bin/env python3
"""Check that every skills/*/SKILL.md frontmatter is valid YAML.

    bin/check-frontmatter.py

Exits non-zero and prints every problem it found, so it can gate a commit.

A skill description is a long paragraph of prose that nobody reads end to end,
which makes it the natural home for a YAML landmine. The one that reached a
user: an unquoted value may not contain ": " (colon-space), because that is the
key/value separator -- so a description that says `or commit: "walk me..."`
fails to parse. Claude Code's own loader is lenient enough to read it anyway,
which is exactly why it went unnoticed until someone's strict parser choked.

So this checks two things:

  * The hazard lint below, always. Stdlib only, like the rest of this repo's
    Python, so it runs anywhere.
  * A real spec-strict parse, when PyYAML is importable. Broader than the lint,
    but optional -- the lint is what guarantees coverage.
"""

import os
import re
import sys

# Sequences that are fine in prose but end a plain (unquoted) YAML scalar early,
# each with the wording to show when it turns up in a value.
HAZARDS = [
    (re.compile(r': '), 'contains ": " (colon-space), which YAML reads as a key/value separator'),
    (re.compile(r':$'), 'ends with ":", which YAML reads as a key with no value'),
    (re.compile(r' #'), 'contains " #", which starts a YAML comment'),
    (re.compile(r'\t'), 'contains a tab, which YAML forbids in indentation'),
]

# A plain scalar may not open with one of these: they introduce flow
# collections, aliases, tags, block scalars, quotes or directives.
LEADING = '[]{},&*!|>\'"%@`'

# Values that are already safe: quoted, or a block scalar (`|`, `>`, with any
# chomping or indentation indicator). These skip the lint entirely.
QUOTED = re.compile(r'''^(".*"|'.*')$''')
BLOCK = re.compile(r'^[|>][+-]?[0-9]*$')

KEY = re.compile(r'^(\s*)([A-Za-z0-9_-]+):(?:\s+(.*))?$')


def frontmatter_lines(text):
    """Yield (line_number, line) for the frontmatter, or None if there is none.

    Line numbers are 1-based and count from the top of the file, so they point
    at what an editor shows.
    """
    lines = text.split('\n')
    if not lines or lines[0].rstrip() != '---':
        return None
    for i, line in enumerate(lines[1:], start=2):
        if line.rstrip() == '---':
            return list(enumerate(lines[1:i - 1], start=2))
    return None


def check(path):
    """Return a list of human-readable problems with one SKILL.md."""
    problems = []
    with open(path, encoding='utf-8') as f:
        text = f.read()

    block = frontmatter_lines(text)
    if block is None:
        return ['no frontmatter: the file must open with --- and close with ---']

    # Indentation of the key whose block scalar we are inside, if any. Its
    # more-indented continuation lines are free text and are not linted.
    block_indent = None
    keys = set()

    for lineno, line in block:
        indent = len(line) - len(line.lstrip())
        if block_indent is not None:
            if not line.strip() or indent > block_indent:
                continue
            block_indent = None

        match = KEY.match(line)
        if not match:
            continue
        leading, key, value = match.group(1), match.group(2), match.group(3) or ''
        if not leading:
            keys.add(key)

        value = value.strip()
        if BLOCK.match(value):
            block_indent = len(leading)
            continue
        if not value or QUOTED.match(value):
            continue

        where = '%s:%d' % (path, lineno)
        if value[0] in LEADING:
            problems.append('%s: unquoted %s starts with %r, which YAML reads as syntax'
                            % (where, key, value[0]))
        for pattern, wording in HAZARDS:
            hit = pattern.search(value)
            if hit:
                problems.append('%s:%d: unquoted %s %s'
                                % (path, lineno, key, wording)
                                + ' (column %d)' % (len(line) - len(value) + hit.start() + 1))

    for required in ('name', 'description'):
        if required not in keys:
            problems.append('%s: frontmatter has no top-level %s' % (path, required))

    return problems


def strict_parse(path):
    """Parse with PyYAML when it is available. Returns a list of problems."""
    try:
        import yaml
    except ImportError:
        return None
    with open(path, encoding='utf-8') as f:
        block = frontmatter_lines(f.read())
    if block is None:
        return []
    try:
        data = yaml.safe_load('\n'.join(line for _, line in block))
    except yaml.YAMLError as e:
        return ['%s: %s' % (path, str(e).replace('\n', ' '))]
    if not isinstance(data, dict):
        return ['%s: frontmatter is not a mapping' % path]
    expected = os.path.basename(os.path.dirname(path))
    if data.get('name') != expected:
        return ['%s: name is %r but the directory is %r'
                % (path, data.get('name'), expected)]
    return []


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    skills = sorted(os.path.join(root, 'skills', name, 'SKILL.md')
                    for name in os.listdir(os.path.join(root, 'skills'))
                    if os.path.isfile(os.path.join(root, 'skills', name, 'SKILL.md')))
    if not skills:
        print('No skills found under skills/*/SKILL.md', file=sys.stderr)
        return 1

    problems = []
    strict_ran = False
    for path in skills:
        rel = os.path.relpath(path, root)
        problems += [p.replace(path, rel) for p in check(path)]
        strict = strict_parse(path)
        if strict is not None:
            strict_ran = True
            problems += [p.replace(path, rel) for p in strict]

    for problem in problems:
        print(problem, file=sys.stderr)

    mode = 'hazard lint + strict parse' if strict_ran else 'hazard lint only (PyYAML not installed)'
    if problems:
        print('\n%d problem(s) in %d skill(s) [%s]' % (len(problems), len(skills), mode),
              file=sys.stderr)
        return 1
    print('%d skill(s) OK [%s]' % (len(skills), mode))
    return 0


if __name__ == '__main__':
    sys.exit(main())
