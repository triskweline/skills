"""Parse a unified diff into files, hunks and body lines.

The whole pipeline reads a patch file, never a git range, so a branch moving
mid-tour cannot shift the line numbers under a half-written narration.

Body lines are numbered from 1 within their hunk. That number is what a
narration file uses to select a *fragment* of a hunk, so it has to be stable
and easy for a human or a model to read off a listing: it counts every line of
the body, context included, and nothing else. A "\\ No newline at end of file"
marker is a property of the line above it, not a line of its own.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

HUNK_RE = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@ ?(.*)$')


def _unprefix(p):
    """Strip git's a/ b/ from a --- or +++ path, and unquote it."""
    if p.startswith('"') and p.endswith('"'):
        # git octal-escapes the *bytes* of a non-ASCII path, so decode the escapes
        # back to bytes before reading them as UTF-8. Going straight through
        # unicode_escape gives mojibake.
        p = p[1:-1].encode('latin-1', 'replace').decode('unicode_escape')
        p = p.encode('latin-1', 'replace').decode('utf-8', 'replace')
    if p == '/dev/null':
        return None
    p = p.split('\t', 1)[0]
    return p.split('/', 1)[1] if '/' in p else p


@dataclass
class Line:
    kind: str           # ' ' context, '+' added, '-' deleted
    text: str           # without the marker, without the newline
    old: int | None     # its line number in the old file
    new: int | None     # its line number in the new file
    new_pos: int        # where it sits in the new file (a deletion: before this line)
    no_newline: bool = False

    @property
    def changed(self):
        return self.kind in '+-'

    def raw(self):
        return self.kind + self.text


@dataclass
class Hunk:
    file: 'FileChange'
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    heading: str                        # git's own trailing context text
    lines: list[Line] = field(default_factory=list)

    @property
    def key(self):
        """How a narration file names this hunk: the +start of its @@ header."""
        return str(self.new_start)

    @property
    def changed_offsets(self):
        return [i for i, l in enumerate(self.lines, 1) if l.changed]

    def slice(self, lo=None, hi=None):
        """A fragment as (lo, hi) inclusive 1-based body offsets, clamped to the hunk."""
        lo = 1 if lo is None else max(1, lo)
        hi = len(self.lines) if hi is None else min(len(self.lines), hi)
        return lo, hi

    def body(self, lo=None, hi=None):
        lo, hi = self.slice(lo, hi)
        return self.lines[lo - 1:hi]

    def start_line(self, lo=None, hi=None):
        """The new-file line the fragment starts at — what the caption shows."""
        lo, hi = self.slice(lo, hi)
        return self.lines[lo - 1].new_pos if self.lines else self.new_start

    def is_whole(self, lo=None, hi=None):
        lo, hi = self.slice(lo, hi)
        return lo == 1 and hi == len(self.lines)


@dataclass
class FileChange:
    path: str                           # the new path; for a deletion, the old one
    old_path: str | None = None
    kind: str = 'changed'               # added | deleted | moved | copied | changed
    binary: bool = False
    hunks: list[Hunk] = field(default_factory=list)

    @property
    def suffix(self):
        name = self.path.rsplit('/', 1)[-1]
        return name.rsplit('.', 1)[1].lower() if '.' in name else name.lower()

    @property
    def keys(self):
        """Everything selectable in this file: each hunk's +start, or "bin"."""
        return ['bin'] if self.binary else [h.key for h in self.hunks]


class Patch:
    def __init__(self, files):
        self.files = files

    @property
    def hunks(self):
        return [h for f in self.files for h in f.hunks]

    def file(self, path):
        for f in self.files:
            if f.path == path:
                return f
        return None

    def hunk(self, path, key):
        f = self.file(path)
        if not f:
            return None
        for h in f.hunks:
            if h.key == key:
                return h
        return None

    def stats(self):
        add = sum(1 for h in self.hunks for l in h.lines if l.kind == '+')
        rem = sum(1 for h in self.hunks for l in h.lines if l.kind == '-')
        return dict(files=len(self.files), added=add, removed=rem,
                    hunks=len(self.hunks),
                    binaries=sum(1 for f in self.files if f.binary))

    def suffixes(self):
        return sorted({f.suffix for f in self.files if f.suffix})


def parse(text):
    """A unified diff -> Patch. Tolerant: anything unrecognised is skipped."""
    files, cur, hunk = [], None, None
    old_n = new_n = 0
    minus = plus = None
    renamed_from = None

    def close_file():
        nonlocal cur, minus, plus, renamed_from
        if cur is not None:
            # +++ and --- are authoritative; the diff --git line is the fallback.
            if plus:
                cur.path = plus
            elif minus:
                cur.path = minus
            if minus and plus and minus != plus and cur.kind == 'changed':
                cur.kind = 'moved'
            if minus and not plus:
                cur.kind = 'deleted'
            if plus and not minus:
                cur.kind = 'added'
            # A pure rename carries no ---/+++ pair at all, only "rename from",
            # so that is the only place its old path exists.
            old = renamed_from or minus
            cur.old_path = old if old and old != cur.path else None
            # A path can appear in more than one section — concatenated patches, or a
            # rename chain. Merge them, or `:all` and coverage would quietly see only
            # the first section's hunks.
            for seen in files:
                if seen.path == cur.path:
                    for h in cur.hunks:
                        h.file = seen
                    seen.hunks.extend(cur.hunks)
                    seen.binary = seen.binary or cur.binary
                    if seen.kind == 'changed' and cur.kind != 'changed':
                        seen.kind = cur.kind
                    seen.old_path = seen.old_path or cur.old_path
                    break
            else:
                files.append(cur)
        cur = None
        minus = plus = renamed_from = None

    for raw in text.split('\n'):
        # Any "diff " line starts a new section, not just "diff --git": a combined
        # diff (diff --cc, from an unresolved merge) has @@@ headers whose body lines
        # would otherwise be appended to the previous file's last hunk.
        if raw.startswith('diff '):
            close_file()
            hunk = None
            if not raw.startswith('diff --git '):
                continue
            m = re.match(r'^diff --git (.+?) (.+)$', raw)
            b = _unprefix(m.group(2)) if m else None
            cur = FileChange(path=b or '?')
            continue
        if cur is None:
            continue

        if hunk is None or not raw or raw[0] not in ' +-\\':
            if raw.startswith('--- '):
                minus = _unprefix(raw[4:]); continue
            if raw.startswith('+++ '):
                plus = _unprefix(raw[4:]); continue
            if raw.startswith('new file mode'):
                cur.kind = 'added'; continue
            if raw.startswith('deleted file mode'):
                cur.kind = 'deleted'; continue
            if raw.startswith('rename from'):
                cur.kind = 'moved'
                renamed_from = raw[len('rename from'):].strip() or None
                continue
            if raw.startswith('rename to'):
                cur.path = raw[len('rename to'):].strip() or cur.path
                continue
            if raw.startswith('copy from'):
                cur.kind = 'copied'
                renamed_from = raw[len('copy from'):].strip() or None
                continue
            if raw.startswith('Binary files') or raw.startswith('GIT binary patch'):
                cur.binary = True; continue

        m = HUNK_RE.match(raw)
        if m:
            old_start = int(m.group(1))
            old_count = int(m.group(2)) if m.group(2) is not None else 1
            new_start = int(m.group(3))
            new_count = int(m.group(4)) if m.group(4) is not None else 1
            hunk = Hunk(cur, old_start, old_count, new_start, new_count, m.group(5))
            cur.hunks.append(hunk)
            old_n, new_n = old_start, new_start
            continue

        if hunk is None or not raw:
            continue
        if raw.startswith('\\'):
            if hunk.lines:
                hunk.lines[-1].no_newline = True
            continue
        mark, text_ = raw[0], raw[1:]
        if mark == ' ':
            hunk.lines.append(Line(' ', text_, old_n, new_n, new_n)); old_n += 1; new_n += 1
        elif mark == '+':
            hunk.lines.append(Line('+', text_, None, new_n, new_n)); new_n += 1
        elif mark == '-':
            hunk.lines.append(Line('-', text_, old_n, None, new_n)); old_n += 1

    close_file()
    return Patch(files)


def load(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return parse(f.read())
