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
from difftour import narration, patch as patchmod, render   # noqa: E402


def _head_of(patch_path):
    try:
        with open(patch_path + '.head', encoding='utf-8') as f:
            return f.read().strip() or None
    except OSError:
        return None


def _repo_and_branch(root):
    """The checkout's folder name and branch, for the report's header.

    The folder name, never the path: a reader wants to know which project this is,
    not where it sat on the machine that built the report.
    """
    import subprocess
    folder = os.path.basename(os.path.abspath(root)) or None
    branch = None
    try:
        out = subprocess.run(['git', '-C', root, 'rev-parse', '--abbrev-ref', 'HEAD'],
                             capture_output=True, text=True, timeout=10)
        name = out.stdout.strip()
        # A detached HEAD reports "HEAD", which is not a branch name.
        if out.returncode == 0 and name and name != 'HEAD':
            branch = name
        top = subprocess.run(['git', '-C', root, 'rev-parse', '--show-toplevel'],
                             capture_output=True, text=True, timeout=10)
        if top.returncode == 0 and top.stdout.strip():
            folder = os.path.basename(top.stdout.strip()) or folder
    except Exception:
        pass
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

    fatal = [x for x in problems if x.fatal]
    warn = [x for x in problems if not x.fatal]
    for x in sorted(problems, key=lambda x: (not x.fatal, x.line)):
        print(x, file=sys.stderr)
    if fatal:
        print('\ntour-build: %d problem%s in %s. Nothing written.'
              % (len(fatal), '' if len(fatal) == 1 else 's', doc), file=sys.stderr)
        return 6

    uid = hashlib.sha1(os.path.abspath(out).encode()).hexdigest()[:10]
    repo, branch = _repo_and_branch(root)
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
    if warn:
        print('tour-build: %d warning%s above.'
              % (len(warn), '' if len(warn) == 1 else 's'), file=sys.stderr)

    print(os.path.abspath(out))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
