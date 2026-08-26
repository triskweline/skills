#!/usr/bin/env python3
"""Put narrated chapters back into the narration file.

  tour-splice.py <narration> <chapter-file> [<chapter-file> …]

Step G narrates chapters in parallel, one fork per chapter, each writing only its
own chapter to its own file. Nothing writes the narration file while that happens,
so there is no race — but the chapters then have to go back in, in the right places,
without disturbing `%report`, `%intro`, `%leftovers` or `%closing`.

Doing that by hand is the one unmechanized step in a pipeline that mechanized
everything else, and the failure mode is quiet: a chapter dropped or landing in the
wrong order still *builds*, because a missing `%intro` is only a warning. So this
does it instead.

A chapter file must begin with the chapter directive it replaces, and its title must
match exactly one chapter in the narration. Matching on the title rather than on
position means a fork cannot land its work on the wrong chapter, however the file was
named.

Writes the narration atomically, and prints what it replaced. Then build.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib'))
from difftour import narration   # noqa: E402

CHAPTER = ('%intro', '%chapter', '%leftovers', '%closing')


def _chapters(lines):
    """(index, directive, title) for every chapter-level directive, in order."""
    out, in_code = [], False
    for i, line in enumerate(lines):
        if in_code:
            if line.strip() == '%end':
                in_code = False
            continue
        if line.startswith('%code'):
            in_code = True
            continue
        if line.startswith(CHAPTER):
            head = line.split(None, 1)
            out.append((i, head[0], head[1].strip() if len(head) > 1 else ''))
    return out


def main(argv):
    if len(argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    doc, parts = argv[0], argv[1:]
    for path in [doc] + parts:
        if not os.path.isfile(path):
            print('tour-splice: no such file: %s' % path, file=sys.stderr)
            return 2

    with open(doc, encoding='utf-8') as f:
        lines = f.read().split('\n')

    spliced = []
    for path in parts:
        with open(path, encoding='utf-8') as f:
            new = f.read().rstrip('\n').split('\n')
        while new and not new[0].strip():
            new.pop(0)
        if not new or not new[0].startswith(CHAPTER):
            print('tour-splice: %s does not begin with a chapter directive, so there '
                  'is nothing to say which chapter it replaces' % path, file=sys.stderr)
            return 2
        head = new[0].split(None, 1)
        title = head[1].strip() if len(head) > 1 else ''

        here = _chapters(lines)
        hits = [c for c in here if c[2] == title]
        if not hits:
            print('tour-splice: no chapter titled %r in %s. It has: %s'
                  % (title, doc, ', '.join(repr(c[2]) for c in here)), file=sys.stderr)
            return 2
        if len(hits) > 1:
            print('tour-splice: %s has %d chapters titled %r, so this cannot be placed '
                  'unambiguously' % (doc, len(hits), title), file=sys.stderr)
            return 2

        start = hits[0][0]
        after = [c[0] for c in here if c[0] > start]
        end = after[0] if after else len(lines)
        lines = lines[:start] + new + [''] + lines[end:]
        spliced.append((title, len(new)))

    # One write, atomic, after every part has been placed — a half-spliced narration
    # would be worse than none.
    d = os.path.dirname(os.path.abspath(doc))
    fd, tmp = tempfile.mkstemp(dir=d, prefix='.tour-splice-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        os.replace(tmp, doc)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise

    for title, n in spliced:
        print('spliced %r (%d lines)' % (title, n))

    # Say what is still a skeleton, so a missing fork is visible now rather than as a
    # confusing wall of "no prose" on the next build.
    with open(doc, encoding='utf-8') as f:
        rep, _ = narration.parse(f.read())
    bare = [ch.title for ch in rep.chapters
            if ch.kind == 'chapter' and not ''.join(ch.intro).strip()]
    if bare:
        print('tour-splice: still un-narrated: %s' % ', '.join(bare), file=sys.stderr)
    print('tour-splice: %d chapter%s spliced into %s'
          % (len(spliced), '' if len(spliced) == 1 else 's', doc), file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
