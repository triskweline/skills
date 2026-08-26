#!/usr/bin/env python3
"""Put narrated chapters back into the narration file.

  tour-splice.py [--check] <narration> <chapter-file> [<chapter-file> …]

`--check` validates the chapter files and writes nothing — that is how a fork verifies
its own work before returning, when a format error still costs only its own minute.

Step G narrates chapters in parallel. A fork may own several chapters, and writes
one file per chapter it owns. Nothing writes the narration file while that happens,
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


# A chapter file is the middle of a document, so parsing it alone fails on rules about
# the whole — "the first directive must be %report". Wrapping it in the smallest legal
# envelope lets a fork check its own work, which is the difference between a format error
# costing the fork a minute and costing the orchestrator a debugging round in a chapter it
# never read.
ENVELOPE = '%report check\n%intro Overview\n%beat b\nPlaceholder.\n'
ENVELOPE_LINES = ENVELOPE.count('\n')      # the fragment's line 1 is line 5 of the whole
WHOLE_DOC = ('%closing', '%intro', '%leftovers')


def _fragment_problems(text):
    """Problems that are really in this chapter, with the fragment's own line numbers."""
    _, problems = narration.parse(ENVELOPE + text)
    out = []
    for x in problems:
        # Complaints about the envelope, or about parts of a document a fragment does not
        # contain, are not this fork's business.
        if x.line <= ENVELOPE_LINES:
            continue
        if not x.fatal and any(w in x.text for w in WHOLE_DOC):
            continue
        x.line -= ENVELOPE_LINES
        out.append(x)
    return out


def _labels_in(lines):
    """Every @label on a block directive in these lines, in order."""
    out, in_code = [], False
    for line in lines:
        if in_code:
            if line.strip() == '%end':
                in_code = False
            continue
        if line.startswith('%code'):
            in_code = True
            continue
        if line.startswith(('%hunk', '%file')):
            m = narration.LABEL.search(line.split('=', 1)[0])
            if m:
                out.append(m.group(1))
    return out


def main(argv):
    check = False
    if argv and argv[0] == '--check':
        check, argv = True, argv[1:]
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

    # Validate every part before placing any of them, so a bad file cannot leave the
    # narration half-updated — and so --check can answer without writing.
    bad = 0
    for path in parts:
        with open(path, encoding='utf-8') as f:
            text = f.read()
        problems = _fragment_problems(text)
        fatal = [x for x in problems
                 if x.fatal and not (x.premature or x.needs_labels)]
        for x in problems:
            if not (x.premature or x.needs_labels):
                print('%s: %s' % (path, x), file=sys.stderr)
        # A retyped directive loses its @label, and then every [[…]] a sibling chapter
        # wrote at that block dangles at build time — in prose nobody here will read.
        head = text.lstrip('\n').split('\n', 1)[0].split(None, 1)
        title = head[1].strip() if len(head) > 1 else ''
        hits = [c for c in _chapters(lines) if c[2] == title]
        if hits:
            start = hits[0][0]
            after = [c[0] for c in _chapters(lines) if c[0] > start]
            was = _labels_in(lines[start:after[0] if after else len(lines)])
            now = _labels_in(text.split('\n'))
            lost = [l for l in was if l not in now]
            if lost:
                print('tour-splice: %s drops label%s %s that the chapter it replaces '
                      'carried. Copy the directive lines rather than retyping them; a '
                      'reference to a dropped label fails at build, in prose written '
                      'elsewhere.' % (path, '' if len(lost) == 1 else 's',
                                      ', '.join('@' + l for l in lost)),
                      file=sys.stderr)
                bad += 1
        if fatal:
            bad += 1
    if bad:
        print('tour-splice: %d file%s %s problems above. Nothing written.'
              % (bad, '' if bad == 1 else 's', 'has' if bad == 1 else 'have'),
              file=sys.stderr)
        return 6
    if check:
        print('tour-splice: %d chapter file%s check out; splice when the rest are in.'
              % (len(parts), '' if len(parts) == 1 else 's'), file=sys.stderr)
        return 0

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
