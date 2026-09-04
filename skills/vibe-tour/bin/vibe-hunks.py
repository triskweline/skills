#!/usr/bin/env python3
"""Number the hunks of a git diff, and assemble a tour from HTML fragments.

  vibe-hunks.py [--untracked] -- <git diff args>
      Print the diff with a marker line before every hunk:  ### h17  path:line
      This is the one full read of the diff. Read this, not `git diff`.

  vibe-hunks.py --ids [--untracked] -- <git diff args>
      Only the marker lines. Cheap: one line per hunk.

  vibe-hunks.py --only h17,h20 [--untracked] -- <git diff args>
      Only those hunks, with their file headers.

  vibe-hunks.py --assemble OUT.html [--untracked] -- <git diff args> ++ FRAGMENT|DIR...
      Lay the fragments out, in order (a directory means every .html under it, in
      path order, minus OUT.html itself), as one self-contained HTML page: sidebar,
      two-column beats, syntax highlighting. Every `<!-- hunk h17 -->` placeholder
      becomes the real hunk, escaped; `<!-- hunk h17 fishy: why -->` marks it fishy.
      Hunks nobody placed are appended in an "Unsorted hunks" chapter and listed on
      stderr, so the page always shows every hunk. Exit status is 0 either way;
      2 on a broken invocation. The layout itself lives in vibe_html.py.

`--untracked` adds files git does not track yet, as additions. Use it for the
`dirty` and `uncommitted` targets, where `git diff` alone would miss them.

A file with no text hunk (binary, mode change, pure rename) gets one marker
of its own, so it is shown too.

Standard library only. Works on Python 3.8+.
"""

import os
import re
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
        if not path:
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


def main(argv):
    mode, arg, untracked = 'full', None, False
    args = list(argv)
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
        last_header = None
        for h in hunks:
            if h.header is not last_header:
                sys.stdout.write('\n'.join(h.header) + '\n')
                last_header = h.header
            sys.stdout.write('\n'.join([h.marker()] + h.body) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
