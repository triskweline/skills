#!/usr/bin/env python3
"""Number the hunks of a git diff, set up a tour, and assemble one from fragments.

  vibe-hunks.py --setup <target>
      Resolve a tour target (dirty, staged, uncommitted, branch, <range>, <commit>,
      <branch>, <PR/MR number>, <PR/MR URL>), create the working directory with its
      topic folders, and write the numbered diff into it. Prints WORK=, ARGS= (to paste
      into --assemble), the commit list, the stat, TOPICS= (the folder names) and DIFF=. Exit 3 with one line
      saying what went wrong when the target cannot be resolved.

  vibe-hunks.py --assemble OUT.html [--untracked] -- <git diff args> ++ FRAGMENT|DIR...
      Lay the fragments out, in order (a directory means every .html under it, in
      path order, minus OUT.html itself), as one self-contained HTML page: sidebar,
      two-column beats, syntax highlighting. Every `<!-- hunk h17 -->` placeholder
      becomes the real hunk, escaped; `<!-- hunk h17 fishy: why -->` marks it fishy.
      Hunks nobody placed are appended in an "Unsorted hunks" chapter and listed on
      stderr, so the page always shows every hunk. Exit status is 0 either way;
      2 on a broken invocation. The layout itself lives in vibe_html.py.

  vibe-hunks.py [--untracked] -- <git diff args>
      Print the diff with a marker line before every hunk:  ### h17  path:line
      This is what --setup writes to diff.txt. Read that file, not `git diff`.

  vibe-hunks.py --ids [--untracked] -- <git diff args>
      Only the marker lines. For tests and for checking a tour by hand.

  vibe-hunks.py --only h17,h20 [--untracked] -- <git diff args>
      Only those hunks, with their file headers. For a worker that lost a hunk from
      its context, and for tests.

`--untracked` adds files git does not track yet, as additions. --setup passes it for
the `dirty` and `uncommitted` targets, where `git diff` alone would miss them.

A file with no text hunk (binary, mode change, pure rename) gets one marker of its
own, so it is shown too.

Standard library only. Works on Python 3.10+.
"""

import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vibe_html  # noqa: E402

class Hunk:
    def __init__(self, hid, path, line, header, body):
        self.id = hid
        self.path = path
        self.line = line          # starting line in the new file, or None
        self.header = header      # the file's diff header lines
        self.body = body          # the hunk lines, starting with the @@ line

    def marker(self):
        where = self.path if self.line is None else '%s:%d' % (self.path, self.line)
        note = '' if self.body else '  (no text hunk: binary, mode or rename)'
        return '### %s  %s%s' % (self.id, where, note)

    def text(self):
        return '\n'.join(self.header + [self.marker()] + self.body) + '\n'


def run_git(args):
    cmd = ['git', 'diff', '--no-color', '--no-ext-diff'] + args
    out = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if out.returncode not in (0, 1):
        sys.stderr.write(out.stderr.decode('utf-8', 'replace'))
        sys.exit(2)
    return out.stdout.decode('utf-8', 'replace')


def untracked_diff():
    ls = subprocess.run(['git', 'ls-files', '--others', '--exclude-standard'],
                        stdout=subprocess.PIPE, check=True)
    parts = []
    for path in ls.stdout.decode('utf-8', 'replace').splitlines():
        # A tour living in the repository's tmp/ must never number its own files.
        if not path or '/vibe-tour.' in '/' + path:
            continue
        out = subprocess.run(['git', 'diff', '--no-color', '--no-ext-diff', '--no-index',
                              '--', '/dev/null', path], stdout=subprocess.PIPE)
        text = out.stdout.decode('utf-8', 'replace')
        # Make the header look like an ordinary addition so the parser sees one path.
        text = text.replace('diff --git a//dev/null b/', 'diff --git a/%s b/' % path, 1)
        parts.append(text)
    return ''.join(parts)


def parse(diff_text):
    """Split a unified diff into numbered Hunks, in the order they appear."""
    hunks, header, body, path, line = [], [], None, None, None
    n = [0]

    def path_of(header_lines):
        for h in header_lines:
            if h.startswith('+++ b/'):
                return h[6:]
            if h.startswith('rename to '):
                return h[10:]
        for h in header_lines:
            if h.startswith('--- a/'):
                return h[6:]
        m = re.match(r'diff --git a/(.*?) b/(.*)$', header_lines[0])
        return m.group(2) if m else header_lines[0]

    def flush_hunk():
        if body is not None:
            n[0] += 1
            hunks.append(Hunk('h%d' % n[0], path, line, header, body))

    def flush_file():
        if header and body is None:          # a file with no text hunk at all
            n[0] += 1
            hunks.append(Hunk('h%d' % n[0], path, None, header, []))

    for raw in diff_text.split('\n'):
        if raw.startswith('diff --git '):
            flush_hunk(); flush_file()
            header, body, path, line = [raw], None, None, None
            continue
        if header is None:
            continue                          # noise before the first file
        if raw.startswith('@@'):
            flush_hunk()
            if path is None:
                path = path_of(header)
            m = re.match(r'@@ -\S+ \+(\d+)', raw)
            line = int(m.group(1)) if m else None
            body = [raw]
            continue
        if body is None:
            header.append(raw)
        else:
            body.append(raw)
    flush_hunk(); flush_file()
    for h in hunks:                            # drop the trailing blank from split()
        while h.body and h.body[-1] == '':
            h.body.pop()
        while h.header and h.header[-1] == '':
            h.header.pop()
        if h.path is None:
            h.path = path_of(h.header)
    return hunks


def expand_fragments(args, out_path):
    """A directory stands for every .html file under it, in path order, so the intro
    (00-intro.html) comes first and topic-NN/fragment.html follow in reading order.
    The output file is skipped, so re-assembling into the same directory is safe."""
    skip = os.path.abspath(out_path) if out_path else None
    files = []
    for a in args:
        if os.path.isdir(a):
            found = []
            for root, dirs, names in os.walk(a):
                dirs.sort()
                for n in sorted(names):
                    if n.endswith('.html'):
                        found.append(os.path.join(root, n))
            files.extend(sorted(found))
        else:
            files.append(a)
    return [f for f in files if os.path.abspath(f) != skip]


def assemble(out_path, hunks, fragments, git_args):
    texts = []
    for frag in fragments:
        with open(frag, encoding='utf-8') as f:
            texts.append(f.read())
    page, report = vibe_html.render(hunks, texts, git_args, out_path)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(page)
    missing, unknown, dupes = report['missing'], report['unknown'], report['dupes']
    if missing:
        sys.stderr.write('%d hunk(s) were not placed and were appended as "Unsorted hunks": %s\n'
                         % (len(missing), ' '.join(h.id for h in missing)))
    if unknown:
        sys.stderr.write('%d placeholder(s) name a hunk that does not exist: %s\n'
                         % (len(unknown), ' '.join(unknown)))
    if dupes:
        sys.stderr.write('%d hunk(s) were placed more than once (fine if shared between topics): %s\n'
                         % (len(dupes), ' '.join(dupes)))
    # A file:// URL, not a path: terminals make it clickable, and the orchestrator hands
    # this line to the human verbatim.
    from urllib.request import pathname2url
    print('file://%s  (%d hunks, %d placed by fragments, %d appended)'
          % (pathname2url(os.path.abspath(out_path)), len(hunks), report['placed'], len(missing)))


def full_text(hunks):
    """The numbered read: file headers once, then a marker line and the body per hunk."""
    out, last_header = [], None
    for h in hunks:
        if h.header is not last_header:
            out.append('\n'.join(h.header))
            last_header = h.header
        out.append('\n'.join([h.marker()] + h.body))
    return '\n'.join(out) + ('\n' if out else '')


class SetupError(Exception):
    pass


def git_out(*args, ok=(0,)):
    """stdout of a git command, or None when it exits with a code not in `ok`."""
    r = subprocess.run(['git'] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode not in ok:
        return None
    return r.stdout.decode('utf-8', 'replace').strip()


def default_branch():
    head = git_out('symbolic-ref', '-q', 'refs/remotes/origin/HEAD')
    if head:
        return head.replace('refs/remotes/', '', 1)
    for name in ('origin/main', 'origin/master', 'main', 'master'):
        if git_out('rev-parse', '--verify', '-q', name + '^{commit}'):
            return name
    raise SetupError('cannot find the default branch: no origin/HEAD, and no main or master')


def is_branch(name):
    return bool(git_out('show-ref', '--verify', '-q', 'refs/heads/' + name) is not None
                or git_out('show-ref', '--verify', '-q', 'refs/remotes/' + name) is not None
                or git_out('show-ref', '--verify', '-q', 'refs/remotes/origin/' + name) is not None)


def branch_range(tip, label):
    base = default_branch()
    if git_out('rev-parse', tip + '^{commit}') == git_out('rev-parse', base + '^{commit}'):
        raise SetupError('%s is the default branch (%s); there is no branch point to diff against' % (label, base))
    merge_base = git_out('merge-base', base, tip)
    if not merge_base:
        raise SetupError('no merge base between %s and %s' % (label, base))
    return '%s..%s' % (merge_base[:12], tip)


def fetch_pr(number, kind=None):
    """Fetch a pull or merge request head into a local ref and return the ref name.
    `kind` is 'pull' or 'merge-requests' when the URL said which; None asks the remote."""
    candidates = ['refs/pull/%s/head' % number, 'refs/merge-requests/%s/head' % number]
    if kind == 'pull':
        candidates = candidates[:1]
    elif kind == 'merge-requests':
        candidates = candidates[1:]
    if git_out('remote', 'get-url', 'origin') is None:
        raise SetupError('no remote named origin, so PR/MR %s cannot be fetched' % number)
    listed = git_out('ls-remote', 'origin', *candidates)
    if listed is None:
        raise SetupError('git ls-remote origin failed; is the remote reachable?')
    found = [line.split('\t')[1] for line in listed.splitlines() if '\t' in line]
    local = 'refs/vibe-tour/pr-%s' % number
    if found:
        if git_out('fetch', '-q', 'origin', '%s:%s' % (found[0], local)) is None:
            raise SetupError('fetching %s from origin failed' % found[0])
        return local
    # Neither forge ref exists. gh or glab may still know the source branch.
    for tool, args, key in (('gh', ['pr', 'view', number, '--json', 'headRefName', '-q', '.headRefName'], None),
                            ('glab', ['mr', 'view', number, '-F', 'json'], 'source_branch')):
        if shutil.which(tool) is None:
            continue
        r = subprocess.run([tool] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if r.returncode != 0:
            continue
        text = r.stdout.decode('utf-8', 'replace').strip()
        if key:
            m = re.search(r'"%s"\s*:\s*"([^"]+)"' % key, text)
            text = m.group(1) if m else ''
        if text and git_out('fetch', '-q', 'origin', '%s:%s' % (text, local)) is not None:
            return local
    raise SetupError('PR/MR %s: origin lists neither refs/pull/%s/head nor refs/merge-requests/%s/head, '
                     'and gh/glab could not name its branch. Fetch its branch yourself, then run --setup <branch>.'
                     % (number, number, number))


def resolve_target(target):
    """-> (untracked, git diff args, log range or None)."""
    t = target.strip()
    if t == 'dirty':
        return True, [], None
    if t == 'staged':
        return False, ['--cached'], None
    if t == 'uncommitted':
        return True, ['HEAD'], None
    if t == 'branch':
        rng = branch_range('HEAD', 'HEAD')
        return False, [rng], rng
    m = re.search(r'/(pull|pulls)/(\d+)', t) if '://' in t else None
    if m:
        ref = fetch_pr(m.group(2), 'pull')
        rng = branch_range(ref, 'PR ' + m.group(2))
        return False, [rng], rng
    m = re.search(r'/merge_requests/(\d+)', t) if '://' in t else None
    if m:
        ref = fetch_pr(m.group(1), 'merge-requests')
        rng = branch_range(ref, 'MR ' + m.group(1))
        return False, [rng], rng
    if '://' in t:
        raise SetupError('URL %s is not a GitHub pull request or GitLab merge request URL' % t)
    if '..' in t:
        if git_out('rev-list', '-n', '1', t) is None:
            raise SetupError('git does not understand the range %s' % t)
        return False, [t], t
    if t.isdigit() and not is_branch(t) and git_out('rev-parse', '--verify', '-q', t + '^{commit}') is None:
        ref = fetch_pr(t)
        rng = branch_range(ref, 'PR/MR ' + t)
        return False, [rng], rng
    if is_branch(t):
        rng = branch_range(t, 'branch ' + t)
        return False, [rng], rng
    if git_out('rev-parse', '--verify', '-q', t + '^{commit}') is not None:
        rng = '%s~1..%s' % (t, t)
        if git_out('rev-parse', '--verify', '-q', t + '~1^{commit}') is None:
            raise SetupError('%s has no parent to diff against' % t)
        return False, [rng], rng
    import difflib
    names = (git_out('branch', '-a', '--format=%(refname:short)') or '').split()
    close = difflib.get_close_matches(t, names, n=5, cutoff=0.5)
    hint = ('; similar branches: ' + ', '.join(close)) if close else ''
    raise SetupError('%s is not a branch, commit, range, PR/MR number or URL here%s' % (t, hint))


def setup(target):
    import tempfile
    if git_out('rev-parse', '--show-toplevel') is None:
        raise SetupError('not inside a git repository')
    untracked, args, log_range = resolve_target(target)
    text = run_git(args)
    if untracked:
        text += untracked_diff()
    hunks = parse(text)
    if not hunks:
        raise SetupError('the diff for %s is empty; nothing to tour' % target)
    # A repository with a tmp/ folder (Rails apps have one) keeps its tours there, so
    # they sit next to the code they describe; otherwise the system temp dir. mkdtemp
    # makes the folder name unique per tour, so generations never collide.
    top = git_out('rev-parse', '--show-toplevel')
    local_tmp = os.path.join(top, 'tmp')
    work = tempfile.mkdtemp(prefix='vibe-tour.', dir=local_tmp if os.path.isdir(local_tmp) else None)
    for n in range(1, 13):
        os.makedirs(os.path.join(work, 'topic-%02d' % n))
    diff_path = os.path.join(work, 'diff.txt')
    body = full_text(hunks)
    with open(diff_path, 'w', encoding='utf-8') as f:
        f.write(body)
    print('WORK=%s' % work)
    print(('ARGS=%s-- %s' % ('--untracked ' if untracked else '', ' '.join(args))).rstrip())
    print('COMMITS:')
    if log_range:
        print(git_out('log', '--oneline', '--no-decorate', log_range) or '(none)')
    else:
        print('(none: working tree)')
    print('STAT:')
    print(git_out('diff', '--stat', *args) or '(no stat)')
    print('TOPICS=%s' % ' '.join('topic-%02d' % n for n in range(1, 13)))
    print('DIFF=%s  (%d lines, %d hunks)' % (diff_path, body.count('\n'), len(hunks)))


def main(argv):
    mode, arg, untracked = 'full', None, False
    args = list(argv)
    if args[:1] == ['--setup']:
        if len(args) != 2:
            sys.stderr.write('usage: vibe-hunks.py --setup <target>\n')
            return 2
        try:
            setup(args[1])
        except SetupError as e:
            sys.stderr.write('vibe-hunks: %s\n' % e)
            return 3
        return 0
    if '--' not in args:
        sys.stderr.write(__doc__)
        return 2
    opts, rest = args[:args.index('--')], args[args.index('--') + 1:]
    i = 0
    while i < len(opts):
        o = opts[i]
        if o == '--untracked':
            untracked = True
        elif o == '--ids':
            mode = 'ids'
        elif o in ('--only', '--assemble'):
            mode, arg = o[2:], opts[i + 1]
            i += 1
        else:
            sys.stderr.write('unknown option %s\n' % o)
            return 2
        i += 1
    fragments = []
    if '++' in rest:
        rest, fragments = rest[:rest.index('++')], rest[rest.index('++') + 1:]
        fragments = expand_fragments(fragments, arg if mode == 'assemble' else None)

    text = run_git(rest)
    if untracked:
        text += untracked_diff()
    hunks = parse(text)

    if mode == 'ids':
        for h in hunks:
            print(h.marker())
    elif mode == 'only':
        wanted = set(arg.split(','))
        for h in hunks:
            if h.id in wanted:
                sys.stdout.write(h.text())
    elif mode == 'assemble':
        assemble(arg, hunks, fragments, rest)
    else:
        sys.stdout.write(full_text(hunks))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
