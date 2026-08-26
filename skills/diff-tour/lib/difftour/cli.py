"""What every bin/ command does the same way.

A patch is loaded by five commands, and each one has to refuse the same two kinds of
unusable patch. That block was copy-pasted five times, which means a sixth command
would forget it and a fix to one would not reach the others — so it lives here.
"""

from . import patch as patchmod


def load_patch(path, prog, out):
    """(patch, exit_code). A non-None exit code means: print nothing more, return it.

    Both refusals are about a patch that cannot support the guarantee the report makes.
    A tour's whole claim is that every changed line is either shown or reported, and
    that claim is computed over the *parsed* patch — so a patch the parser cannot trust
    has to be refused here rather than quietly narrowing what "every line" means.
    """
    p = patchmod.load(path)

    dupes = p.duplicate_keys()
    if dupes:
        print('%s: this patch has two hunks at the same line in one file, so one of '
              'them could never be selected and coverage would credit its lines to the '
              'other:' % prog, file=out)
        for path_, key in dupes[:10]:
            print('  %s at +%s' % (path_, key), file=out)
        print('%s: it looks hand-assembled. Regenerate it with bin/tour-fetch.sh.'
              % prog, file=out)
        return p, 2

    # Every @@ header states how many lines its hunk holds. A patch truncated in
    # transit, or whose context lines lost their leading space, parses as a shorter
    # hunk — and nothing downstream can notice, because coverage only ever sees the
    # lines that were parsed. Comparing the two is the only place the parse can be
    # checked against what the patch says about itself.
    miscounted = p.miscounted()
    if miscounted:
        print('%s: %d hunk%s do not hold the number of lines their @@ header declares, '
              'so this patch was truncated or its context lines were mangled in '
              'transit:' % (prog, len(miscounted), '' if len(miscounted) == 1 else 's'),
              file=out)
        for path_, key, ((do, ao), (dn, an)) in miscounted[:10]:
            print('  %s at +%s: declares -%d +%d, holds -%d +%d'
                  % (path_, key, do, dn, ao, an), file=out)
        print('%s: coverage is computed over the lines that parsed, so it would report '
              '"everything shown" about a hunk missing lines. Regenerate the patch with '
              'bin/tour-fetch.sh, or re-download it.' % prog, file=out)
        return p, 2

    return p, None
