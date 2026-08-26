#!/usr/bin/env python3
"""Build the report: a narration file plus a patch -> one self-contained .html.

  tour-build.py <patch> <narration> <out.html> [--root DIR] [--source LABEL]

Every command in bin/ takes <patch> <narration> in that order, so they can be
retyped from one another without thinking about it.

    --root    the checkout %quote reads context from (default: the current directory)
    --source  what the metadata line calls the diff (default: the patch's name)

The model writes narration and names hunks; this script splices them. That is
what keeps every diff byte exact without trusting a copy-paste, and it is why a
hundred-hunk report costs about as much to write as a ten-hunk one: the model
never emits diff bytes.

It validates first and writes nothing if the narration is wrong, reporting every
problem at once — a narration file for a large change is tens of thousands of
tokens, so one edit round has to be enough.

Coverage is printed on every build. It is a pure function of the patch and the
narration, so there is no ledger to go stale: run tour-rest.py for the detail.
"""

import datetime
import hashlib
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib'))
PROG = 'tour-build'

from difftour import narration, patch as patchmod, render   # noqa: E402


def _head_of(patch_path):
    try:
        with open(patch_path + '.head', encoding='utf-8') as f:
            return f.read().strip() or None
    except OSError:
        return None


def _repo_and_branch(root, want_head=None):
    """The checkout's folder name and branch, for the report's header.

    The folder name, never the path: a reader wants to know which project this is,
    not where it sat on the machine that built the report.

    Both are stated only when they are true of *this diff*. Touring someone else's
    pull request from a checkout that sits on `master` must not print "master" in
    the header — that is a confident wrong fact in the most trusted line of the
    page. So the branch appears only when the checkout is actually at the commit
    the patch ends at, and the folder only when --root is a git repository at all.
    """
    import subprocess

    def git(*args):
        try:
            out = subprocess.run(['git', '-C', root] + list(args),
                                 capture_output=True, text=True, timeout=10)
            return out.stdout.strip() if out.returncode == 0 else None
        except Exception:
            return None

    top = git('rev-parse', '--show-toplevel')
    if not top:
        return None, None                       # not a checkout; claim nothing
    folder = os.path.basename(top) or None

    branch = git('rev-parse', '--abbrev-ref', 'HEAD')
    if branch == 'HEAD':
        branch = None                           # detached: there is no branch name
    if branch and want_head:
        here = git('rev-parse', 'HEAD')
        if here != want_head:
            branch = None                       # this checkout is not this diff
    return folder, branch


def _head_of_checkout(root):
    import subprocess
    try:
        out = subprocess.run(['git', '-C', root, 'rev-parse', 'HEAD'],
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or None if out.returncode == 0 else None
    except Exception:
        return None


def main(argv):
    args, opts = [], {}
    i = 0
    while i < len(argv):
        if argv[i] in ('--root', '--source', '--date'):
            if i + 1 >= len(argv):
                print('tour-build: %s needs a value' % argv[i], file=sys.stderr)
                return 2
            opts[argv[i][2:]] = argv[i + 1]
            i += 2
        else:
            args.append(argv[i])
            i += 1
    if len(args) != 3:
        print(__doc__.strip(), file=sys.stderr)
        return 2

    src, doc, out = args
    for path, what in ((src, 'patch file'), (doc, 'narration file')):
        if not os.path.isfile(path):
            print('tour-build: no such %s: %s' % (what, path), file=sys.stderr)
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
    with open(doc, encoding='utf-8') as f:
        text = f.read()

    root = opts.get('root', '.')
    rep, problems = narration.parse(text)
    problems += narration.resolve(rep, p, root)

    # %quote reads from the checkout, so the checkout has to be at the diff's head or
    # the quote is byte-exact from the wrong version of the file — the most convincing
    # way this tool could mislead a reader.
    if any(c.kind == 'quote' for c in rep.components):
        want = _head_of(src)
        have = _head_of_checkout(root)
        if want and have and want != have:
            print('tour-build: the diff ends at %s but %s is at %s. %%quote reads the '
                  'checkout, so its context lines are from the wrong version. Point '
                  '--root at a checkout of %s, or drop the quotes.'
                  % (want[:9], os.path.abspath(root), have[:9], want[:9]), file=sys.stderr)

    # A document is meant to be built after every chapter is appended, so most builds
    # happen while later chapters are still bare skeletons. Missing prose is therefore
    # premature rather than wrong here too — it just has to be gone by Step J, which
    # refuses to hand over a report with any warning at all.
    fatal = [x for x in problems if x.fatal and not x.premature]
    warn = [x for x in problems if not x.fatal]
    pending = [x for x in problems if x.premature]
    for x in sorted(problems, key=lambda x: (not x.fatal, x.line)):
        if not x.premature:
            print(x, file=sys.stderr)
    if fatal:
        print('\ntour-build: %d problem%s in %s. Nothing written.'
              % (len(fatal), '' if len(fatal) == 1 else 's', doc), file=sys.stderr)
        return 6

    uid = hashlib.sha1(os.path.abspath(out).encode()).hexdigest()[:10]
    repo, branch = _repo_and_branch(root, _head_of(src))
    html, missing = render.page(
        rep, p.stats(),
        opts.get('source', os.path.basename(src)),
        opts.get('date', datetime.date.today().isoformat()),
        uid, repo=repo, branch=branch)

    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)

    if missing:
        print('tour-build: vendored Prism is incomplete (%s) — those languages '
              'render as plain text' % ', '.join(missing), file=sys.stderr)

    shown, total, gaps = narration.coverage(rep, p)
    print('tour-build: %d chapters, %d components, %s KB'
          % (len(rep.chapters), len(rep.components), '{:,}'.format(len(html) // 1024)),
          file=sys.stderr)
    if gaps:
        print('tour-build: %d of %d changed lines shown. %d place%s still unshown — '
              'bin/tour-rest.py lists them.'
              % (shown, total, len(gaps), '' if len(gaps) == 1 else 's'), file=sys.stderr)
    else:
        print('tour-build: all %d changed lines shown.' % total, file=sys.stderr)
    if pending:
        print('tour-build: %d place%s still without prose — expected while chapters are '
              'still skeletons, but not in the report you hand over.'
              % (len(pending), '' if len(pending) == 1 else 's'), file=sys.stderr)
    if warn:
        print('tour-build: %d warning%s above.'
              % (len(warn), '' if len(warn) == 1 else 's'), file=sys.stderr)

    print(os.path.abspath(out))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
