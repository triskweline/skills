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
import tempfile

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib'))
PROG = 'tour-skeleton'

from difftour import cli, narration   # noqa: E402

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
        # Look for an existing label in the spec only. A caption is prose and may
        # well contain an @ — "strip the @media hack" — and reading that as a label
        # would leave the block permanently unlabelable, silently.
        spec = line.split('=', 1)[0]
        # `path:all` is one directive standing for many blocks, so no single label
        # can name them; those blocks are shown, not discussed individually.
        if (line.startswith(LABELLED) and not narration.LABEL.search(spec)
                and not re.search(r':all\b', spec)):
            # Before the caption if there is one, at the end otherwise.
            if '=' in line:
                spec, cap = line.split('=', 1)
                line = '%s@%s = %s' % (spec.rstrip() + ' ', mint(), cap.strip())
            else:
                line = '%s @%s' % (line.rstrip(), mint())
            n += 1
        out.append(line)

    if n:
        # Replace atomically. Opening the narration for writing in place would
        # truncate someone's half-written report if anything failed mid-write.
        d = os.path.dirname(os.path.abspath(path))
        fd, tmp = tempfile.mkstemp(dir=d, prefix='.tour-skeleton-')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write('\n'.join(out))
            os.replace(tmp, path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
    return n


def _suggest_forks(rep):
    """Group the cluster chapters into forks, so Step G does not have to.

    Wall clock is the longest fork, and the longest fork can never be shorter than
    the biggest single chapter — so that is the bin size, and anything beyond the
    bins it takes to fill buys no time while still paying a context re-prefill each.
    First-fit-decreasing over the block counts, which is a page of arithmetic nobody
    should be spending thinking tokens on.
    """
    chapters = [(len(ch.components), ch.number, ch.title)
                for ch in rep.chapters if ch.kind == 'chapter' and ch.components]
    if len(chapters) < 2:
        return
    chapters.sort(reverse=True)
    # The biggest chapter is the floor on wall clock, so it is the natural bin size —
    # but with many small chapters that degenerates to one fork each, which contradicts
    # the advice a few lines away in SKILL.md and pays a context re-prefill per fork for
    # nothing. So a bin also has to be worth a fork: at most MOST forks, whatever the
    # arithmetic wants.
    MOST = 6
    total = sum(size for size, _, _ in chapters)
    cap = max(chapters[0][0], -(-total // MOST))
    bins = []
    for size, number, _ in chapters:
        for b in bins:
            if b[0] + size <= cap:
                b[0] += size
                b[1].append(number)
                break
        else:
            bins.append([size, [number]])

    print('\nSuggested forks — packed so none holds more than %d block%s: the biggest '
          'chapter,\nor a %dth of the work, whichever is larger. Below the first, forks '
          'cannot go\nfaster; below the second, each one buys less than its own '
          'context costs.' % (cap, '' if cap == 1 else 's', MOST))
    for i, (size, numbers) in enumerate(bins, 1):
        label = 'chapter%s %s' % ('' if len(numbers) == 1 else 's',
                                  ', '.join(str(n) for n in sorted(numbers)))
        print('  fork %2d:  %-44s %3d block%s'
              % (i, label, size, '' if size == 1 else 's'))


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

    p, bad = cli.load_patch(src, PROG, sys.stderr)
    if bad:
        return bad

    def check():
        with open(doc, encoding='utf-8') as f:
            rep, problems = narration.parse(f.read())
        problems += narration.resolve(rep, p, root)
        return rep, problems

    # Validate before touching the file. This is the only command that writes to
    # someone else's narration, so it does not write to a broken one.
    rep, problems = check()
    # A skeleton has no prose and no references yet. Both absences are premature
    # complaints here, not problems — and the reference one has to be deferred or
    # this command deadlocks against itself.
    fatal = [x for x in problems if x.fatal and not (x.premature or x.needs_labels)]
    for x in sorted(problems, key=lambda x: (not x.fatal, x.line)):
        if not (x.premature or x.needs_labels):
            print(x, file=sys.stderr)
    if fatal:
        print('\ntour-skeleton: %d problem%s in %s. Nothing written; fix these '
              'before narrating.' % (len(fatal), '' if len(fatal) == 1 else 's', doc),
              file=sys.stderr)
        return 6

    try:
        added = _label_in_place(doc, [c.label for c in rep.components if c.label])
    except OSError as e:
        print('tour-skeleton: cannot write %s: %s' % (doc, e.strerror or e),
              file=sys.stderr)
        return 2
    if added:
        rep, problems = check()
        # Labelling is additive, so this cannot fail — but printing a table built
        # from a report we just broke would be worse than saying so.
        broke = [x for x in problems if x.fatal and not (x.premature or x.needs_labels)]
        if broke:
            for x in broke:
                print(x, file=sys.stderr)
            print('\ntour-skeleton: labelling %s produced the problems above, which '
                  'is a bug in this script. The labels are written; the report is not '
                  'buildable until they are fixed.' % doc, file=sys.stderr)
            return 6
    pending = [x for x in problems if (x.premature or x.needs_labels)]
    dangling = [x for x in pending if x.needs_labels]

    if added:
        print('tour-skeleton: labelled %d block%s in %s'
              % (added, '' if added == 1 else 's', doc), file=sys.stderr)

    # The table. This is what a chapter narrated on its own needs to see.
    width = max([len(c.caption) for c in rep.components] + [7])
    for ch in rep.chapters:
        # The block count is what Step G's fork packing is decided from, so it is
        # stated rather than left to be counted off the rows.
        n = len(ch.components)
        print('\n%d · %s%s · %d block%s'
              % (ch.number, ch.title,
                 '' if ch.kind == 'chapter' else '  (%s)' % ch.kind,
                 n, '' if n == 1 else 's'))
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

    _suggest_forks(rep)

    # stdout is block-buffered when piped and stderr never is, so without this the
    # summary below lands in the middle of the table above it and the whole thing looks
    # like corrupted output.
    sys.stdout.flush()

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
    prose_pending = [x for x in pending if x not in dangling]
    if prose_pending:
        print('tour-skeleton: %d place%s still need prose, which is the next step.'
              % (len(prose_pending), '' if len(prose_pending) == 1 else 's'),
              file=sys.stderr)
    if dangling:
        print('tour-skeleton: %d reference%s does not resolve yet. Use the labels in '
              'the table above; the build will refuse any that still do not.'
              % (len(dangling), '' if len(dangling) == 1 else 's'), file=sys.stderr)
    return 1 if gaps else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
