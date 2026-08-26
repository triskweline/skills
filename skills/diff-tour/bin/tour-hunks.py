#!/usr/bin/env python3
"""List what a patch offers, and where its body lines are.

  tour-hunks.py [--body] <patch> [<path-prefix> …] [--not <path-prefix> …]

    --body            print the diff too, with a body offset in the left margin
    --not, -x         skip these paths. Repeatable, and it wins over a prefix.

Without --body this is the cheap read: one line per file saying how much it
holds, then one line per hunk. Use it to decide what is worth reading in full.

`--body` is the expensive read, and the offsets in its left margin are what a
narration file uses to select a *fragment* of a hunk — so they arrive with content
you were going to read anyway rather than costing a second pass.

**Reading narrow, then wide, re-prints the narrow part**, because a path argument
is a prefix: `--body <patch> src/forms/a.js` and then `--body <patch> src/forms`
prints a.js twice. That is what `--not` is for:

    tour-hunks.py --body p.patch src/forms --not src/forms/a.js

Selectors, ready to paste:
    %hunk <path>:<start> = <caption>              the whole hunk
    %hunk <path>:<start> #<lo>-<hi> = <caption>   body lines lo..hi of it
    %file <path> = <caption>                      a change with no diff body
"""

import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib'))
PROG = 'tour-hunks'

from difftour import patch as patchmod   # noqa: E402


def main(argv):
    body = False
    rest, skip = [], []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ('--body', '-b'):
            body = True
        elif a in ('--not', '-x'):
            if i + 1 >= len(argv):
                print('tour-hunks: %s needs a path' % a, file=sys.stderr)
                return 2
            skip.append(argv[i + 1])
            i += 1
        else:
            rest.append(a)
        i += 1
    if not rest:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    src, prefixes = rest[0], rest[1:]
    if not os.path.isfile(src):
        print('tour-hunks: no such patch file: %s' % src, file=sys.stderr)
        return 2
    p = patchmod.load(src)
    dupes = p.duplicate_keys()
    if dupes:
        print('%s: this patch has two hunks at the same line in one file, so one of '
              'them could never be selected and coverage would credit its lines to the '
              'other:' % PROG, file=sys.stderr)
        for path, key in dupes[:10]:
            print('  %s at +%s' % (path, key), file=sys.stderr)
        print('%s: it looks hand-assembled. Regenerate it with bin/tour-fetch.sh.'
              % PROG, file=sys.stderr)
        return 2

    files = [f for f in p.files
             if (not prefixes or any(f.path.startswith(x) for x in prefixes))
             and not any(f.path.startswith(x) for x in skip)]
    if not files:
        print('tour-hunks: nothing in the patch matches %s'
              % (' '.join(prefixes) or '(the whole patch)'), file=sys.stderr)
        return 3

    for fc in files:
        note = fc.kind
        if fc.binary:
            note += ' · binary, no diff body — select it with %file'
        elif not fc.hunks:
            note += ' · no diff body — select it with %file'
        else:
            # What reading this file in full would cost, so the choice can be made
            # before making it rather than after.
            lines = sum(len(h.lines) for h in fc.hunks)
            changed = sum(len(h.changed_offsets) for h in fc.hunks)
            note += ' · %d hunk%s · %d body lines, %d changed' % (
                len(fc.hunks), '' if len(fc.hunks) == 1 else 's', lines, changed)
        if fc.old_path:
            note += ' · was %s' % fc.old_path
        print('\n■ %s · %s' % (fc.path, note))
        for h in fc.hunks:
            print('  @%s · %d body line%s · %s'
                  % (h.key, len(h.lines), '' if len(h.lines) == 1 else 's', h.heading))
            if body:
                for i, line in enumerate(h.lines, 1):
                    print('%5d %s%s' % (i, line.kind, line.text))

    s = p.stats()
    print('\n%d files, %d hunks, %d changed lines%s'
          % (s['files'], s['hunks'], s['added'] + s['removed'],
             ', %d binary' % s['binaries'] if s['binaries'] else ''), file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
