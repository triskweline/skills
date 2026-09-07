"""Fragments + numbered hunks -> one self-contained HTML page.

Imported by difftour.py for `--assemble`; not a script of its own.

Workers write plain fragments: <h2> per topic, <h3> per beat, <p> prose, and a
`<!-- hunk h17 -->` placeholder where a hunk belongs. The placeholder may carry the
hunk's attention level: `<!-- hunk h17 skip -->`, `<!-- hunk h17 note: why -->`,
`<!-- hunk h17 fishy: why -->`, `<!-- hunk h17 hot: why -->`. Everything else on the
page is mechanical and happens here: chapter numbers, ids, the meta line, the
two-column layout, the figures with the real diff bytes, syntax highlighting, the
sidebar with its heat strips. Nothing in this file decides anything about the tour;
it only lays out what the workers wrote.

Standard library only. Works on Python 3.10+.
"""

import datetime
import hashlib
import html
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
ASSETS = os.path.join(SKILL, 'assets')
VENDOR = os.path.join(SKILL, 'vendor', 'prism')

# ------------------------------------------------------------------ languages

# Prism 1.30.0 grammars, in require order. All of them are inlined into every page;
# subsetting would save ~85 KB on a page that is already hundreds of KB.
GRAMMARS = [
    'bash', 'clike', 'c', 'javascript', 'coffeescript', 'cpp', 'csharp', 'css', 'diff',
    'docker', 'elixir', 'ruby', 'markup', 'markup-templating', 'erb', 'go', 'graphql',
    'groovy', 'haml', 'handlebars', 'hcl', 'http', 'ini', 'java', 'json', 'jsx', 'kotlin',
    'less', 'liquid', 'lua', 'makefile', 'markdown', 'nginx', 'perl', 'php', 'powershell',
    'protobuf', 'python', 'r', 'regex', 'rust', 'scala', 'scss', 'sql', 'swift', 'toml',
    'typescript', 'tsx', 'twig', 'yaml',
]

BY_SUFFIX = {
    'js': 'javascript', 'mjs': 'javascript', 'cjs': 'javascript',
    'jsx': 'jsx', 'ts': 'typescript', 'tsx': 'tsx', 'mts': 'typescript',
    'coffee': 'coffeescript',
    'html': 'markup', 'htm': 'markup', 'xml': 'markup', 'svg': 'markup',
    'vue': 'markup', 'xhtml': 'markup', 'plist': 'markup', 'xsd': 'markup',
    'css': 'css', 'scss': 'scss', 'sass': 'scss', 'less': 'less',
    'rb': 'ruby', 'rake': 'ruby', 'gemspec': 'ruby', 'ru': 'ruby',
    'erb': 'erb', 'haml': 'haml',
    'py': 'python', 'pyi': 'python',
    'php': 'php', 'java': 'java', 'kt': 'kotlin', 'kts': 'kotlin',
    'swift': 'swift', 'scala': 'scala', 'sbt': 'scala',
    'groovy': 'groovy', 'gradle': 'groovy',
    'go': 'go', 'rs': 'rust',
    'c': 'c', 'h': 'c', 'cpp': 'cpp', 'cc': 'cpp', 'cxx': 'cpp',
    'hpp': 'cpp', 'hh': 'cpp', 'cs': 'csharp',
    'lua': 'lua', 'pl': 'perl', 'pm': 'perl', 'r': 'r',
    'ex': 'elixir', 'exs': 'elixir',
    'sql': 'sql', 'graphql': 'graphql', 'gql': 'graphql',
    'sh': 'bash', 'bash': 'bash', 'zsh': 'bash', 'ksh': 'bash',
    'ps1': 'powershell', 'psm1': 'powershell',
    'json': 'json', 'jsonc': 'json', 'json5': 'json', 'geojson': 'json',
    'yaml': 'yaml', 'yml': 'yaml', 'toml': 'toml',
    'ini': 'ini', 'cfg': 'ini', 'conf': 'ini', 'properties': 'ini',
    'tf': 'hcl', 'tfvars': 'hcl', 'hcl': 'hcl', 'proto': 'protobuf',
    'md': 'markdown', 'markdown': 'markdown', 'mdx': 'markdown',
    'hbs': 'handlebars', 'twig': 'twig', 'liquid': 'liquid',
    'http': 'http', 'diff': 'diff', 'patch': 'diff',
}

BY_NAME = {
    'dockerfile': 'docker', 'containerfile': 'docker',
    'makefile': 'makefile', 'gnumakefile': 'makefile', 'rakefile': 'ruby',
    'gemfile': 'ruby', 'guardfile': 'ruby', 'brewfile': 'ruby',
    'vagrantfile': 'ruby', 'podfile': 'ruby', 'capfile': 'ruby',
    'nginx.conf': 'nginx',
}

SHEBANG = re.compile(r'^[+ ]?#!.*?\b(bash|sh|zsh|ruby|python[\d.]*|node|perl|lua)\b')
SHEBANG_LANG = {'sh': 'bash', 'zsh': 'bash', 'bash': 'bash', 'ruby': 'ruby',
                'node': 'javascript', 'perl': 'perl', 'lua': 'lua'}


def language_of(path, body):
    """The Prism language for a path, or 'none'. `body` is the hunk's lines, for a shebang."""
    name = path.rsplit('/', 1)[-1].lower()
    if name in BY_NAME:
        return BY_NAME[name]
    if '.' in name:
        for part in reversed(name.split('.')):
            if part in BY_SUFFIX:
                return BY_SUFFIX[part]
        return 'none'
    for line in body[1:4]:
        m = SHEBANG.match(line)
        if m:
            word = m.group(1)
            return SHEBANG_LANG.get(word, 'python' if word.startswith('python') else 'none')
    return 'none'


def prism_bundle():
    parts = ['window.Prism = window.Prism || {}; window.Prism.manual = true;']
    for name in ['core'] + GRAMMARS + ['diff-highlight']:
        path = os.path.join(VENDOR, 'prism-%s.min.js' % name)
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                parts.append(f.read().rstrip())
    return '\n'.join(parts)


# ------------------------------------------------------------------ fragments

PLACEHOLDER = re.compile(
    r'<!--\s*hunk\s+(h\d+)(?:\s+(skip|note|fishy|hot)\b\s*:?\s*(.*?))?\s*-->', re.S | re.I)

# Attention levels, low to high. The number is what the page sorts and filters by.
LEVELS = {'skip': 0, None: 1, 'note': 2, 'fishy': 3, 'hot': 4}
WRAPPERS = re.compile(r'</?(?:section|article|main|body|html|head|div)\b[^>]*>|<!doctype[^>]*>', re.I)
NUMBERING = re.compile(r'^\s*\d+(?:\.\d+)*[.):]?\s+')
H1 = re.compile(r'<h1[^>]*>(.*?)</h1>', re.S | re.I)
H2 = re.compile(r'<h2[^>]*>(.*?)</h2>', re.S | re.I)
H3 = re.compile(r'<h3[^>]*>(.*?)</h3>', re.S | re.I)


def _title(raw):
    return NUMBERING.sub('', raw.strip(), count=1).strip()


def _prose(raw):
    """Worker prose, passed through. A worker that wrote bare paragraphs instead of
    <p> still gets paragraphs."""
    text = raw.strip()
    if not text:
        return ''
    if not re.search(r'<(p|ul|ol|pre|blockquote|table|h\d)\b', text, re.I):
        text = '\n'.join('<p>%s</p>' % para.strip()
                         for para in re.split(r'\n\s*\n', text) if para.strip())
    return text


# A line mark: `<!-- focus: ...lines... -->` or `<!-- dim @9: ...lines... -->`, written
# directly after a hunk placeholder. The block is the quoted lines of the hunk to mark;
# `@N` is an optional guess at the first line's number, used only to break a tie. A block
# cannot contain "<!--": a mark that seems to is one that was never closed.
MARK = re.compile(r'<!--\s*(focus|dim)(?:\s*@\s*(\d+))?\s*:((?:(?!<!--).)*?)-->', re.S | re.I)
SENTINEL = re.compile(r'<!--mark:(\d+)-->')
_MARKS = {}      # sentinel number -> (kind, hint, block), or ('invalid', None, message)
_PROBLEMS = []   # mark problems found where no hunk can own them (the intro fragment)


def _extract_marks(text):
    """Replace every mark with a sentinel before the fragment is split at headings and
    placeholders, so a quoted line that looks like a heading or a placeholder cannot
    derail the parse. Badly formed marks become 'invalid' sentinels, which are reported
    and never shown."""
    def store(entry):
        n = len(_MARKS) + 1
        _MARKS[n] = entry
        return '<!--mark:%d-->' % n

    text = MARK.sub(lambda m: store((m.group(1).lower(), int(m.group(2)) if m.group(2) else None, m.group(3))), text)
    # A block that contained "-->" ended there; what followed it up to the real "-->" now
    # sits in the open, right after the sentinel.
    text = re.sub(r'(<!--mark:\d+-->)([^<]*?-->)',
                  lambda m: m.group(1) + store(('invalid', None,
                      'a quoted line contained "-->", which ends the comment early; the mark covers only the lines before it')),
                  text)
    # What is left of "<!-- focus" or "<!-- dim" is a closed comment without a colon, or a
    # comment never closed. The latter would swallow the page up to the layout's own
    # closing marker, so it is cut at the next placeholder or heading.
    def stray(m):
        if m.group(1) is not None:
            return store(('invalid', None, 'a focus/dim comment without a colon was ignored'))
        return store(('invalid', None,
                      'a focus/dim comment was never closed with -->; it and the text after it, up to the next placeholder or heading, were dropped'))
    text = re.sub(r'<!--\s*(?:focus|dim)\b(?:(?:(?!<!--).)*?(-->)|.*?(?=<!--\s*hunk|<h[23]\b|\Z))', stray, text, flags=re.S | re.I)
    return text


def _take_marks(text):
    """-> (text without sentinels, the marks they stood for)."""
    marks = [_MARKS[int(n)] for n in SENTINEL.findall(text)]
    return SENTINEL.sub('', text), marks


def _beat(title, raw):
    """One beat: its own prose, then (hunk id, level, reason, note prose, marks) items."""
    parts = PLACEHOLDER.split(raw)
    items = []
    for i in range(1, len(parts), 4):
        level = parts[i + 1].lower() if parts[i + 1] else None
        reason = (parts[i + 2] or '').strip() if level else ''
        rest, marks = _take_marks(parts[i + 3])
        items.append((parts[i], level, reason, _prose(rest), marks))
    say, strays = _take_marks(parts[0])
    if strays:
        # A mark before the first placeholder belongs to no hunk: reported, not shown.
        items.insert(0, (None, None, '', '', [('invalid', None, 'a focus/dim comment stood before any placeholder and was ignored')]))
    return {'title': _title(title) if title else '', 'say': _prose(say), 'items': items}


def _norm(line):
    return ' '.join(line.split())


def resolve_marks(h, marks):
    """Turn quoted blocks into hunk-relative line ranges: {'focus': [(a, b)], 'dim': [...]}.
    Body lines are compared without their diff prefix and with whitespace collapsed; a
    quoted line may carry the prefix or not. A block that matches once is that range. A
    block that matches several times takes the match nearest the `@N` hint, or is dropped
    when there is no hint. A block that matches nowhere is dropped. Dropped marks are
    returned as messages so the assembler can report them."""
    # The "\\ No newline at end of file" marker is a body line too; it is matched by any
    # quoted line that starts with a backslash, since nobody types it out exactly.
    body = ['\\' if l.startswith('\\') else _norm(l[1:]) for l in h.body[1:]]
    ranges, problems = {'focus': [], 'dim': []}, []
    for kind, hint, block in marks:
        if kind == 'invalid':
            problems.append('%s: %s' % (h.id, block))
            continue
        quoted = [l for l in block.split('\n')]
        while quoted and not quoted[0].strip():
            quoted.pop(0)
        while quoted and not quoted[-1].strip():
            quoted.pop()
        if not quoted:
            problems.append('%s in %s: empty block' % (kind, h.id))
            continue
        # Two passes: the block as quoted, then with a leading diff column stripped. Only
        # the second pass tolerates a worker copying the +/- column; trying both at once
        # made a YAML "- item" match the body line "item" as well.
        n = len(quoted)
        if n >= len(body) and len(body) > 0:
            problems.append('%s in %s: the quoted block covers the whole hunk; a mark needs unmarked lines beside it, dropped'
                            % (kind, h.id))
            continue
        exact = [{'\\'} if q.strip().startswith('\\') else {_norm(q), _norm(html.unescape(q))} for q in quoted]
        stripped = [{_norm(q[1:]), _norm(html.unescape(q[1:]))} if q[:1] in '+- ' and not q.strip().startswith('\\') else set(forms)
                    for q, forms in zip(quoted, exact)]
        def windows(forms):
            return [w for w in range(0, len(body) - n + 1)
                    if all(body[w + k] in forms[k] for k in range(n))]
        starts = windows(exact) or windows(stripped)
        if not starts:
            problems.append('%s in %s: quoted block not found (%d line%s, starts "%s")'
                            % (kind, h.id, n, '' if n == 1 else 's', quoted[0].strip()[:40]))
            continue
        if len(starts) > 1:
            if hint is None:
                problems.append('%s in %s: quoted block matches %d times at lines %s and carries no @N; dropped'
                                % (kind, h.id, len(starts), ', '.join(str(w + 1) for w in starts)))
                continue
            w = min(starts, key=lambda w: abs(w + 1 - hint))
        else:
            w = starts[0]
        ranges[kind].append((w + 1, w + n))
    # Where a dim range overlaps a focus range, focus wins: the dimmed part is trimmed.
    focused = set()
    for a, b in ranges['focus']:
        focused.update(range(a, b + 1))
    if focused and ranges['dim']:
        trimmed, cut = [], False
        for a, b in ranges['dim']:
            run = None
            for line in range(a, b + 1):
                if line in focused:
                    cut = True
                    if run: trimmed.append(run); run = None
                elif run: run = (run[0], line)
                else: run = (line, line)
            if run: trimmed.append(run)
        if cut:
            problems.append('%s: a dim block overlaps a focus block; focus wins on the shared lines' % h.id)
        ranges['dim'] = trimmed
    return ranges, problems


def _chapter(title, raw):
    parts = H3.split(raw)
    beats = []
    intro = parts[0]
    # Hunks placed before the first <h3> become an untitled beat; the prose before
    # the first of them stays the chapter's introduction.
    m = PLACEHOLDER.search(intro)
    if m:
        beats.append(_beat('', intro[m.start():]))
        intro = intro[:m.start()]
    for i in range(1, len(parts), 2):
        beats.append(_beat(parts[i], parts[i + 1]))
    intro, strays = _take_marks(intro)
    problems = ['a focus/dim comment stood before any placeholder and was ignored'] if strays else []
    return {'title': _title(title), 'intro': _prose(intro), 'beats': beats, 'problems': problems}


# Fixed lines under the intro's fixed headings, emitted here so they read identically on
# every tour and the orchestrator writes only the paragraphs. Keyed by heading text.
BYLINES = {
    'the spectrum of solutions':
        'Three other ways this could have been built, so you can see the room the author '
        'was standing in. Then where this change sits.',
    'the minimal solution':
        'The smallest patch that gets by: least blast radius, possibly incomplete, possibly not pretty.',
    'the maximal solution':
        'The thorough fix: solves the problem completely, restructuring whatever stands in the way.',
    'the evaporating solution':
        'Make the problem not arise here at all, by changing something elsewhere.',
}
HEADING = re.compile(r'(<h([23])[^>]*>(.*?)</h\2>)', re.S | re.I)


ROW = re.compile(r'<tr[^>]*>(.*?)</tr>', re.S | re.I)
CELL = re.compile(r'(<t[dh]\b[^>]*>.*?</t[dh]>)', re.S | re.I)


def _arrow_column(summary_html):
    """A before/after table is written with two cells per row; the page shows an arrow
    between them, as a column of its own so the two sides stay aligned."""
    def row(m):
        cells = CELL.findall(m.group(1))
        if len(cells) != 2:
            return m.group(0)
        arrow = '<th class="arrow"></th>' if cells[0].lower().startswith('<th') else '<td class="arrow">→</td>'
        return m.group(0).replace(m.group(1), cells[0] + arrow + cells[1], 1)
    return ROW.sub(row, summary_html)


PROBLEM_H2 = re.compile(r'(<h2[^>]*>\s*the problem\s*</h2>)(.*?)(?=<h2\b|$)', re.S | re.I)


def _problem_block(summary_html):
    """The problem is the one part of the summary whose job is to make the reader care, so
    it is set larger than body copy; wrapping it lets the stylesheet find it."""
    return PROBLEM_H2.sub(lambda m: m.group(1) + '\n<div class="problem">' + m.group(2).strip() + '</div>\n',
                          summary_html, count=1)


def _with_bylines(summary_html):
    def add(m):
        key = re.sub(r'<[^>]+>', '', m.group(3)).strip().lower().rstrip('.')
        line = BYLINES.get(key)
        return m.group(1) + ('\n<p class="byline">%s</p>' % line if line else '')
    return _spectrum_rows(_arrow_column(_problem_block(HEADING.sub(add, summary_html))))


SPECTRUM_H2 = re.compile(r'<h2[^>]*>\s*the spectrum of solutions\s*</h2>', re.I)
H3_SPLIT = re.compile(r'(<h3[^>]*>.*?</h3>)', re.S | re.I)
BYLINE_P = re.compile(r'^\s*(<p class="byline">.*?</p>)', re.S)
# The two fixed labels inside a solution's paragraph. Each label and the text after it, up
# to the next label or the end of the paragraph, is wrapped so the page can tint it.
WEIGHS = re.compile(r'(<(?:strong|b)>\s*(buys|costs)\s*:?\s*</(?:strong|b)>.*?)(?=\s*<(?:strong|b)>\s*(?:buys|costs)\s*:?\s*</(?:strong|b)>|\s*</p>)', re.I | re.S)


def _spectrum_rows(summary_html):
    """Lay the spectrum's four blocks out as rows of two columns: label and byline on the
    left, the orchestrator's prose on the right."""
    m = SPECTRUM_H2.search(summary_html)
    if not m:
        return summary_html
    head = summary_html[:m.end()]
    rest = summary_html[m.end():]
    nxt = re.search(r'<h2\b', rest, re.I)
    section, tail = (rest[:nxt.start()], rest[nxt.start():]) if nxt else (rest, '')
    parts = H3_SPLIT.split(section)
    if len(parts) < 3:
        return summary_html
    rows = []
    for i in range(1, len(parts), 2):
        heading, body = parts[i], parts[i + 1]
        bm = BYLINE_P.match(body)
        byline, prose = (bm.group(1), body[bm.end():]) if bm else ('', body)
        prose = WEIGHS.sub(lambda w: '<span class="%s">%s</span>' % (w.group(2).lower(), w.group(1)), prose)
        rows.append('<div class="row"><div class="lbl">%s\n%s</div><div class="prose">%s</div></div>'
                    % (heading, byline, prose.strip()))
    return head + parts[0] + '<div class="spectrum">\n' + '\n'.join(rows) + '\n</div>\n' + tail


def parse_fragments(texts):
    """-> (title html, summary html, chapters). `texts` are fragment bodies in page order."""
    title, summary, chapters = '', [], []
    _MARKS.clear()
    del _PROBLEMS[:]
    for text in texts:
        text = _extract_marks(WRAPPERS.sub('', text))
        m = H1.search(text)
        if m:
            # The fragment with the <h1> is the intro. Everything else in it is the tour
            # summary, whatever headings it uses; only fragments without an <h1> hold
            # chapters.
            if not title:
                title = m.group(1).strip()
            rest, strays = _take_marks(text[:m.start()] + text[m.end():])
            if strays:
                _PROBLEMS.append('a focus/dim comment stood in the intro fragment and was ignored')
            if rest.strip():
                summary.append(_with_bylines(_prose(rest)))
            continue
        parts = H2.split(text)
        lead = parts[0]
        if PLACEHOLDER.search(lead):
            # A fragment that forgot its <h2> is still a topic.
            chapters.append(_chapter('Topic %d' % (len(chapters) + 1), lead))
        elif lead.strip():
            summary.append(_prose(lead))
        for i in range(1, len(parts), 2):
            chapters.append(_chapter(parts[i], parts[i + 1]))
    return title, '\n'.join(summary), chapters


# ------------------------------------------------------------------- figures

def _binary(h):
    head = '\n'.join(h.header)
    return 'GIT binary patch' in head or '\nBinary files ' in head


def _kind(h):
    """How the file changed: added, deleted, moved, mode, or changed. Independent of
    whether it is binary; a binary file can be any of these."""
    head = '\n'.join(h.header)
    if '\nnew file mode' in head:
        return 'added'
    if '\ndeleted file mode' in head:
        return 'deleted'
    if '\nrename from ' in head:
        return 'moved'
    if '\nold mode ' in head:
        return 'mode'
    return 'changed'


NO_BODY = {
    'binary': 'A binary file. A diff of bytes tells a reviewer nothing, so it is named, not shown.',
    'added': 'A new empty file.',
    'deleted': 'An empty file, deleted.',
    'moved': 'Renamed, with no change to its contents.',
    'mode': 'The file mode changed, with no change to its contents.',
    'changed': 'A change with no diff body.',
}


def _key(h):
    return hashlib.md5(('\n'.join(h.body) or (h.path + '\n'.join(h.header))).encode('utf-8')).hexdigest()[:10]


FLAG_LABEL = {
    'note': 'A choice to accept knowingly',
    'fishy': 'May be wrong',
    'hot': 'Silent or irreversible if wrong',
}


def figure(h, ident, level, reason, note='', ranges=None):
    """One hunk: its sentence with the level badge in front, the level's reason if any,
    then the diff card. The whole thing is one figure with the level as its left edge, so
    the hunks of a beat form a vertical line striped by attention level."""
    kind = _kind(h)
    binary = _binary(h)
    add = sum(1 for l in h.body[1:] if l.startswith('+'))
    rem = sum(1 for l in h.body[1:] if l.startswith('-'))
    where = html.escape(h.path)
    if h.line is not None:
        where += ':%d' % h.line
    if add or rem:
        where += ' · <span class="sz">%s%s</span>' % ('+%d ' % add if add else '', '−%d' % rem if rem else '')
    # The kind of file change sits with the path and the size, where the eye reads the
    # hunk's facts; the tools area on the right is for controls only.
    if kind in ('added', 'deleted', 'moved'):
        where += ' <span class="tag %s">%s</span>' % (kind, kind)
    if binary:
        where += ' <span class="tag binary">binary</span>'
    name = level or 'plain'
    badge = '<span class="lvl">%s</span>' % (level if level else 'read')
    # The badge opens the hunk's sentence, so the level is the first thing the eye meets
    # and the sentence reads as "FISHY: what this hunk is about".
    note = note or '<p></p>'
    note = re.sub(r'<p\b[^>]*>', lambda m: m.group(0) + badge, note, count=1)
    attrs = ''
    if reason:
        attrs += ' data-reason="%s"' % html.escape(reason, quote=True)
    for mark in ('focus', 'dim'):
        if ranges and ranges.get(mark):
            attrs += ' data-%s="%s"' % (mark, ','.join('%d-%d' % r for r in ranges[mark]))
    out = ['<figure class="hunk lvl-%s%s" id="%s" data-key="%s" data-level="%d"%s>'
           % (name, ' file' if not h.body else '', ident, _key(h), LEVELS[level], attrs),
           '<div class="note">%s</div>' % note]
    if level in ('note', 'fishy', 'hot'):
        out.append('<p class="flag %s"><b>%s:</b> %s</p>'
                   % (level, FLAG_LABEL[level],
                      html.escape(reason) if reason else 'please check this change'))
    out.append('<div class="card">')
    out.append('<figcaption><span class="where">%s</span><span class="tools"></span></figcaption>' % where)
    if h.body:
        # The @@ line is not shown: its numbers are in the header bar already. Git's
        # function context after the second @@, the nearest declaration above the hunk,
        # is code and stays in the code column, set apart so it reads as "somewhere
        # above", not as the line before the first context line.
        m = re.match(r'@@ [^@]*@@ ?(.*)$', h.body[0])
        if m and m.group(1).strip():
            out.append('<div class="ctx">%s</div>' % html.escape(m.group(1).rstrip()))
        out.append('<pre class="diff"><code class="language-diff-%s diff-highlight">%s\n</code></pre>'
                   % (language_of(h.path, h.body), html.escape('\n'.join(h.body[1:]))))
    else:
        out.append('<div class="binary">%s</div>' % NO_BODY['binary' if binary else kind])
    out.append('</div>')
    out.append('</figure>')
    return '\n'.join(out)


# ---------------------------------------------------------------------- page

STANDFIRST = (
    'A fast, narrated tour through one change, for a human reviewing code they did not '
    'write. It groups the diff into topics and shows every hunk, each with a first-read '
    'attention level. Nothing was verified, and the judgement is yours.')

# The legend, once, at the top: the level's square on the left, what it asks of the
# reader on the right, and for the three lower levels a button that marks every hunk
# of that level viewed, which is how a reader chooses how deep to go.
LEGEND = [
    (0, 'skip', 'A tool could have written it, or it is fallout of another hunk. Trust the description.', True),
    (1, 'read', 'Ordinary hand-written code. Read it once.', True),
    (2, 'note', 'A choice or a nit to accept knowingly. The phrase says what to decide.', True),
    (3, 'fishy', 'It may be wrong. Verify before approving.', False),
    (4, 'hot', 'A mistake here would be silent or irreversible. Read every line, however it looks.', False),
]


def legend():
    rows = []
    for lvl, name, text, button in LEGEND:
        rows.append('<div class="row"><span class="sq l%d"></span><b>%s</b><span>%s</span>%s</div>'
                    % (lvl, name, text,
                       ('<button type="button" class="seen level" data-level="%d">Mark viewed</button>' % lvl)
                       if button else '<span></span>'))
    return '<h2 class="legend-title">How to read this tour</h2>\n<div class="legend">%s</div>' % ''.join(rows)


def _git(*args):
    try:
        out = subprocess.run(['git'] + list(args), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        return out.stdout.decode('utf-8', 'replace').strip()
    except OSError:
        return ''


def _swap(page, mark, content):
    a, b = '<!--%s-->' % mark, '<!--/%s-->' % mark
    i, j = page.index(a), page.index(b)
    return page[:i + len(a)] + content + page[j:]


def _read(name):
    with open(os.path.join(ASSETS, name), encoding='utf-8') as f:
        return f.read()


def render(hunks, texts, git_args, out_path=''):
    """-> (page html, report dict with placed / missing / unknown / duplicate ids)."""
    title, summary, chapters = parse_fragments(texts)
    by_id = dict((h.id, h) for h in hunks)
    seen, unknown, dupes, mark_problems = {}, [], [], []

    def fig(hid, level, reason, note='', marks=()):
        if hid is None:
            # Not a hunk: a mark that stood where no hunk was. Report it and render nothing.
            mark_problems.extend(m[2] for m in marks)
            return ''
        if hid not in by_id:
            unknown.append(hid)
            return '<p class="missing"><strong>Unknown hunk %s</strong></p>' % html.escape(hid)
        n = seen.get(hid, 0) + 1
        seen[hid] = n
        if n > 1:
            dupes.append(hid)
        ranges = None
        if marks:
            ranges, problems = resolve_marks(by_id[hid], marks)
            mark_problems.extend(problems)
        return figure(by_id[hid], hid if n == 1 else '%s-%d' % (hid, n), level, reason, note, ranges)

    mark_problems.extend(_PROBLEMS)
    body = []
    for n, ch in enumerate(chapters, 1):
        mark_problems.extend(ch.get('problems', []))
        body.append('<section class="chapter" id="topic-%d">' % n)
        body.append('<h2><span class="n">%d</span><span class="t">%s</span></h2>' % (n, ch['title']))
        if ch['intro']:
            body.append('<div class="intro">%s</div>' % ch['intro'])
        for beat in ch['beats']:
            body.append(_beat_html(beat, fig))
        body.append('</section>')

    missing = [h for h in hunks if h.id not in seen]
    placed = len(seen)
    if missing:
        body.append('<section class="chapter" id="topic-%d">' % (len(chapters) + 1))
        body.append('<h2><span class="n">%d</span><span class="t">Unsorted hunks</span></h2>'
                    % (len(chapters) + 1))
        body.append('<div class="intro"><p>These hunks were not placed in any topic. '
                    'They are shown here so nothing is hidden.</p></div>')
        body.append('<section class="beat"><div class="say"></div><div class="show">%s</div></section>'
                    % '\n'.join(fig(h.id, None, '') for h in missing))
        body.append('</section>')

    top = _git('rev-parse', '--show-toplevel')
    repo = os.path.basename(top) if top else ''
    source = ' '.join(a for a in git_args if a) or 'working tree'
    # The uid scopes the reader's viewed marks in the browser to this one tour. It comes
    # from the output path: the working directory is minted per tour, so two tours never
    # share marks, while re-assembling the same tour keeps them.
    uid = hashlib.md5(os.path.abspath(out_path or 'diff-tour.html').encode('utf-8')).hexdigest()[:10]
    title = title or 'Diff tour'
    head = ['<h1>%s</h1>' % title,
            '<p class="meta">%s</p>' % _meta(hunks, repo, source),
            '<p class="standfirst">%s</p>' % STANDFIRST]
    if summary:
        head.append('<div class="summary">%s</div>' % summary)
    # The legend sits between the summary and the first chapter: the reader meets the
    # story first and the rules just before the first hunk they apply to.
    head.append(legend())

    page = _read('layout.html')
    page = re.sub(r'<!--\s*\n  diff tour — the page shell.*?-->\n', '', page, count=1, flags=re.S)
    page = _swap(page, 'PRISM', '\n<script>%s</script>\n' % prism_bundle())
    page = _swap(page, 'CSS', '\n<style>\n%s</style>\n' % _read('report.css'))
    page = _swap(page, 'JS', '\n<script>\n%s</script>\n' % _read('report.js'))
    page = _swap(page, 'REPORT', '\n' + '\n\n'.join(head + body) + '\n')
    plain = html.escape(re.sub(r'<[^>]+>', '', title))
    page = _swap(page, 'NAVTITLE', plain)
    page = re.sub(r'<title>.*?</title>', lambda m: '<title>%s</title>' % plain, page, count=1)
    page = page.replace('data-uid="fixture"', 'data-uid="%s"' % uid, 1)
    return page, {'placed': placed, 'missing': missing, 'unknown': unknown, 'dupes': dupes,
                  'marks': mark_problems}


def _beat_html(beat, fig):
    say = []
    if beat['title']:
        say.append('<h3>%s</h3>' % beat['title'])
    if beat['say']:
        say.append(beat['say'])
    show = []
    for hid, level, reason, note, marks in beat['items']:
        show.append(fig(hid, level, reason, note, marks))
    show = [piece for piece in show if piece]   # a hunk-less problem item renders nothing
    if not show:
        return '<section class="beat solo"><div class="say">%s</div></section>' % '\n'.join(say)
    return ('<section class="beat"><div class="say">%s</div><div class="show">%s</div></section>'
            % ('\n'.join(say), '\n'.join(show)))


def _meta(hunks, repo, source):
    files = len(set(h.path for h in hunks))
    add = sum(1 for h in hunks for l in h.body[1:] if l.startswith('+'))
    rem = sum(1 for h in hunks for l in h.body[1:] if l.startswith('-'))
    bits = []
    if repo:
        bits.append('<b>%s</b>' % html.escape(repo))
    bits.append('<b>%d</b> file%s' % (files, '' if files == 1 else 's'))
    bits.append('<b class="added">+%s</b> <b class="removed">−%s</b>' % ('{:,}'.format(add), '{:,}'.format(rem)))
    bits.append('<b>%d</b> hunk%s' % (len(hunks), '' if len(hunks) == 1 else 's'))
    bits.append('<code>%s</code>' % html.escape(source))
    bits.append(datetime.date.today().isoformat())
    return ' · '.join(bits)
