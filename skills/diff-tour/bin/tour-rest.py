#!/usr/bin/env python3
"""What the narration does not show yet.

  tour-rest.py <patch> <narration>

Every added or changed line has to appear somewhere in the report, and so does
every change a diff can carry without a body: a binary file, a pure rename, a
mode change. A reader cannot be responsible for code they were never shown.

This is a pure function of the patch and the narration — no ledger, nothing to
go stale, and safe to run as often as you like. It prints directives ready to
paste, and exits 0 when nothing is left. It works on a skeleton as well as on a
finished narration, since prose has no bearing on what is covered.

Where a gap sits next to a fragment you already show, the fix is to widen that
fragment, not to paste an orphan two-line component into Leftovers. It says so
per gap.
"""

import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib'))
PROG = 'tour-rest'

from difftour import cli, narration   # noqa: E402


def main(argv):
    if len(argv) != 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    src, doc = argv
    for path, what in ((src, 'patch file'), (doc, 'narration file')):
        if not os.path.isfile(path):
            print('tour-rest: no such %s: %s' % (what, path), file=sys.stderr)
            return 2

    p, bad = cli.load_patch(src, PROG, sys.stderr)
    if bad:
        return bad
    with open(doc, encoding='utf-8') as f:
        rep, problems = narration.parse(f.read())
    # Coverage never depends on a quote, so this does not read one. Otherwise the
    # command Step G mandates right after the splice would fail on the ordinary PR
    # tour — where the checkout is a worktree and a quote correct there looks
    # out-of-range from here — and it would say "does not parse" about a file that does.
    problems += narration.resolve(rep, p, quotes=False)
    # Missing prose does not affect coverage, and this command's whole job is to be
    # useful on a skeleton — which by definition has none yet.
    fatal = [x for x in problems if x.fatal and not (x.premature or x.needs_labels)]
    if fatal:
        for x in fatal:
            print(x, file=sys.stderr)
        print('\ntour-rest: the narration does not parse, so coverage cannot be '
              'trusted. Fix the above first.', file=sys.stderr)
        return 6

    shown, total, gaps = narration.coverage(rep, p)
    if not gaps:
        print('tour-rest: all %d changed lines shown, and every file accounted for.'
              % total)
        return 0

    # %# is the narration file's comment directive, so this block can be pasted whole.
    print('%%# %d of %d changed lines shown. %d place%s left:\n'
          % (shown, total, len(gaps), '' if len(gaps) == 1 else 's'))
    by_file = {}
    for path, key, lo, hi, near in gaps:
        by_file.setdefault(path, []).append((key, lo, hi, near))
    for path in sorted(by_file):
        print('%# ' + path)
        for key, lo, hi, near in by_file[path]:
            if key is None:
                print('%%file %s = ' % path)
                continue
            hunk = p.hunk(path, key)
            # If the run covers every changed line of the hunk, name the hunk rather
            # than a slice of it: a fragment selector here would be noise, and the
            # point of this output is that it can be pasted.
            whole = hunk is not None and not [o for o in hunk.changed_offsets
                                              if not lo <= o <= hi]
            if near:
                # An adjacent gap is an *edit*, not a new block — so print the edit and
                # not a directive. Printing both said "widen the neighbour" and then
                # offered a pasteable line that does the opposite, and the line it
                # offered had no caption, so pasting it made the build refuse.
                label, code, rlo, rhi = near
                name = ('@%s' % label) if label else ('the block at %s' % code)
                widen = (min(rlo, lo), max(rhi, hi))
                n_lines = hi - lo + 1
                print('%%#   EDIT %s: change #%d-%d to #%d-%d. %s next to it, so '
                      'widening it is the fix — do not add a block for %s.'
                      % (name, rlo, rhi, widen[0], widen[1],
                         'This 1 line sits' if n_lines == 1
                         else 'These %d lines sit' % n_lines,
                         'it' if n_lines == 1 else 'them'))
                continue
            if whole:
                print('%%hunk %s:%s = ' % (path, key))
            else:
                print('%%hunk %s:%s #%d-%d = ' % (path, key, lo, hi))
        print()
    print('%# Every %hunk above needs a caption before this builds. An EDIT line is not')
    print('%# pasteable — it names a fragment to widen in place. A leftover group also')
    print('%# says why no topic claimed it.')
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
