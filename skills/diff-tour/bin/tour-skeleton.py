#!/usr/bin/env python3
"""Check a skeleton, label every block, and print the table.

  tour-skeleton.py <patch> <narration> [--root DIR]

A **skeleton** is the narration file with its structure and captions but none of
its prose: every `%chapter`, every `%beat`, every `%hunk` / `%file` with a
caption. Writing it before any prose does three things that are much cheaper here
than later:

  1. **Coverage is proven before a word is written.** In a large tour the prose is
     tens of thousands of tokens; discovering afterwards that a fragment boundary
     was two lines short means editing prose that should never have been written.
  2. **Every block gets a label.** This command writes an `@hN` into any block
     that lacks one, in place. A label names one block forever, so prose can
     reference it as `[[h17]]` and the builder renders whatever code that block
     currently sits at — which is what lets a chapter be reordered while it is
     being narrated.
  3. **It is the table of contents.** The table printed below is what a chapter
     being narrated in isolation needs in order to refer to its neighbours.

This is the only command that edits your file, and it only ever adds a label.

Then narrate: fill in the prose, in place or per chapter, and build. Reordering
beats and blocks *within* a chapter is expected and costs nothing — labels move
with their blocks. Moving a block to another chapter is re-clustering, and it
invalidates the coverage this command just proved.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib'))
from difftour import narration, patch as patchmod   # noqa: E402

LABELLED = ('%hunk', '%file')


def _label_in_place(path, existing):
    """Add @hN to every %hunk / %file that has none. Returns how many were added."""
    with open(path, encoding='utf-8') as f:
        lines = f.read().split('\n')

    used = set(existing)
    n = 0

    def mint():
        i = 1
        while ('h%d' % i) in used:
            i += 1
        used.add('h%d' % i)
        return 'h%d' % i

    out, in_code = [], False
    for line in lines:
        if in_code:
            if line.strip() == '%end':
                in_code = False
            out.append(line)
            continue
        if line.startswith('%code'):
            in_code = True
            out.append(line)
            continue
        # `path:all` is one directive standing for many blocks, so no single label
        # can name them; those blocks are shown, not discussed individually.
        if (line.startswith(LABELLED) and not narration.LABEL.search(line)
                and not re.search(r':all\b', line.split('=')[0])):
            # Before the caption if there is one, at the end otherwise.
            if '=' in line:
                spec, cap = line.split('=', 1)
                line = '%s@%s = %s' % (spec.rstrip() + ' ', mint(), cap.strip())
            else:
                line = '%s @%s' % (line.rstrip(), mint())
            n += 1
        out.append(line)

    if n:
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(out))
    return n


def main(argv):
    args, root = [], '.'
    i = 0
    while i < len(argv):
        if argv[i] == '--root':
            if i + 1 >= len(argv):
                print('tour-skeleton: --root needs a value', file=sys.stderr)
                return 2
            root = argv[i + 1]
            i += 2
        else:
            args.append(argv[i])
            i += 1
    if len(args) != 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2

    src, doc = args
    for path, what in ((src, 'patch file'), (doc, 'narration file')):
        if not os.path.isfile(path):
            print('tour-skeleton: no such %s: %s' % (what, path), file=sys.stderr)
            return 2

    p = patchmod.load(src)

    # A skeleton has no prose yet, so those two complaints are expected here — they
    # are precisely what the next stage is for.
    def is_prose_gap(x):
        return 'no prose' in x.text or 'introductory paragraph' in x.text

    def check():
        with open(doc, encoding='utf-8') as f:
            rep, problems = narration.parse(f.read())
        problems += narration.resolve(rep, p, root)
        return rep, problems

    # Validate before touching the file. This is the only command that writes to
    # someone else's narration, so it does not write to a broken one.
    rep, problems = check()
    fatal = [x for x in problems if x.fatal and not is_prose_gap(x)]
    for x in sorted(problems, key=lambda x: (not x.fatal, x.line)):
        if not is_prose_gap(x):
            print(x, file=sys.stderr)
    if fatal:
        print('\ntour-skeleton: %d problem%s in %s. Nothing written; fix these '
              'before narrating.' % (len(fatal), '' if len(fatal) == 1 else 's', doc),
              file=sys.stderr)
        return 6

    added = _label_in_place(doc, [c.label for c in rep.components if c.label])
    if added:
        rep, problems = check()
    pending = [x for x in problems if is_prose_gap(x)]

    if added:
        print('tour-skeleton: labelled %d block%s in %s'
              % (added, '' if added == 1 else 's', doc), file=sys.stderr)

    # The table. This is what a chapter narrated on its own needs to see.
    width = max([len(c.caption) for c in rep.components] + [7])
    for ch in rep.chapters:
        print('\n%d · %s%s' % (ch.number, ch.title,
                               '' if ch.kind == 'chapter' else '  (%s)' % ch.kind))
        for b in ch.beats:
            print('   %s' % (b.subtitle or '(no subtitle)'))
            for c in b.items:
                if not isinstance(c, narration.Component):
                    continue
                where = c.path
                if c.kind == 'hunk' and c.hunk is not None:
                    where += ':%d' % c.hunk.start_line(c.lo, c.hi)
                    if not c.hunk.is_whole(c.lo, c.hi):
                        lo, hi = c.hunk.slice(c.lo, c.hi)
                        where += ' #%d-%d' % (lo, hi)
                print('      %-5s %-6s %-*s  %s'
                      % ('[[%s]]' % c.label if c.label else '—',
                         c.code or c.kind, width, c.caption, where))

    shown, total, gaps = narration.coverage(rep, p)
    print()
    if gaps:
        print('tour-skeleton: %d of %d changed lines placed. %d place%s still '
              'unplaced — bin/tour-rest.py lists them, and fixing them now costs '
              'nothing.' % (shown, total, len(gaps), '' if len(gaps) == 1 else 's'),
              file=sys.stderr)
    else:
        print('tour-skeleton: all %d changed lines placed. Coverage is settled; '
              'narrate.' % total, file=sys.stderr)
    if pending:
        print('tour-skeleton: %d place%s still need prose, which is the next step.'
              % (len(pending), '' if len(pending) == 1 else 's'), file=sys.stderr)
    return 1 if gaps else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
