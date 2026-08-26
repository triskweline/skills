#!/usr/bin/env python3
"""Build the report: a narration file plus a patch -> one self-contained .html.

  tour-build.py <patch> <narration> <out.html> [--root DIR] [--source LABEL] [--final]

Every command in bin/ takes <patch> <narration> in that order, so they can be
retyped from one another without thinking about it.

    --root    the checkout %quote reads context from (default: the current directory)
    --source  what the metadata line calls the diff (default: the patch's name)
    --final   refuse to call the report finished while anything is unshown, pending
              or warned about. Build with it before handing a path to anyone.

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

from difftour import cli, narration, render   # noqa: E402


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

    Both are stated only when they are true of *this diff*, and both are therefore
    gated on the same thing: that this checkout is at the commit the patch ends at.
    Touring someone else's pull request from a checkout sitting on `master` must not
    print "master" — and running without --root from an unrelated repository must not
    print that repository's name. Either would be a confident wrong fact in the line
    of the page a reader trusts most.

    The folder is read from the *main* worktree, not from --root itself: the ordinary
    PR flow points --root at a detached worktree under /tmp, whose directory name is
    a temp name and not the project.
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

    # --git-common-dir is the *shared* .git: `.git` in a normal checkout, and the main
    # repository's .git in a linked worktree. Its parent is the project either way, so
    # a worktree reports the project rather than /tmp/difftour-<sha>.
    common = git('rev-parse', '--git-common-dir') or '.git'
    if not os.path.isabs(common):
        common = os.path.join(top, common)
    folder = os.path.basename(os.path.dirname(os.path.abspath(common))) or None

    branch = git('rev-parse', '--abbrev-ref', 'HEAD')
    if branch == 'HEAD':
        branch = None                           # detached: a worktree has no branch

    # No proof that this checkout is this diff means no claim about either — not the
    # branch, and not the project. tour-fetch.sh records a head for everything it
    # resolves itself, PR numbers included; only a patch file from elsewhere has none.
    if not want_head or git('rev-parse', 'HEAD') != want_head:
        return None, None
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
        if argv[i] == '--final':
            opts['final'] = True
            i += 1
            continue
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

    p, bad = cli.load_patch(src, PROG, sys.stderr)
    if bad:
        return bad
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
            # A real problem, not a bare print: this is the one way wrong *content* can
            # reach a reader through a build that otherwise passes, so --final has to
            # refuse it. bin/tour-checkout.sh exists to make it impossible upstream;
            # this is the backstop for a run that skipped it.
            line = min((c.line for c in rep.components if c.kind == 'quote'), default=1)
            problems.append(narration.Problem(
                line,
                'the diff ends at %s but %s is at %s, so every %%quote reads its lines '
                'from the wrong version of the file. Run bin/tour-checkout.sh and pass '
                'what it prints as --root, or drop the quotes.'
                % (want[:9], os.path.abspath(root), have[:9]),
                fatal=False))

    # A document is meant to be built after every chapter is appended, so most builds
    # happen while later chapters are still bare skeletons: missing prose does not stop
    # the build. But it is printed, with its line, because Step J's gate is "no
    # warnings and nothing pending" and a gate cannot be held against something
    # invisible. A dangling [[label]] is *not* deferred here — the labels exist by the
    # time anything is built, so a reference that does not resolve is simply wrong.
    fatal = [x for x in problems if x.fatal and not x.premature]
    warn = [x for x in problems
            if not x.fatal and not x.premature and not x.advisory]
    # Printed like everything else, but never a reason to refuse: see Problem.advisory.
    notes = [x for x in problems if x.advisory and not x.premature]
    pending = [x for x in problems if x.premature]
    for x in sorted(problems, key=lambda x: (x.premature, not x.fatal, x.line)):
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
        print('tour-build: %d thing%s still pending above — expected while chapters are '
              'still skeletons, and not allowed in the report you hand over.'
              % (len(pending), '' if len(pending) == 1 else 's'), file=sys.stderr)
    if warn:
        print('tour-build: %d warning%s above.'
              % (len(warn), '' if len(warn) == 1 else 's'), file=sys.stderr)
    if notes:
        print('tour-build: %d note%s above — worth one look each, and not something a '
              'finished report has to be free of.'
              % (len(notes), '' if len(notes) == 1 else 's'), file=sys.stderr)

    # Every fidelity property in this skill is mechanical except the last one: whether
    # the report being handed over is actually finished. --final is that check. Without
    # it a pipeline of skeleton(0) → splice(0) → build(0) runs all green over a report
    # that a fork left a hole in, because each of those exits 0 by design.
    if opts.get('final') and (gaps or pending or warn):
        print('\ntour-build: this is not a report to hand over — %s. It is written, at '
              '%s, so you can look at it; fix the above and build again.'
              % (', '.join(filter(None, [
                  '%d unshown place%s' % (len(gaps), '' if len(gaps) == 1 else 's')
                  if gaps else '',
                  '%d pending' % len(pending) if pending else '',
                  '%d warning%s' % (len(warn), '' if len(warn) == 1 else 's')
                  if warn else ''])), os.path.abspath(out)), file=sys.stderr)
        return 1

    print(os.path.abspath(out))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
