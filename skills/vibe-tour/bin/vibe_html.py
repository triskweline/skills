"""Fragments + numbered hunks -> one self-contained HTML page.

Imported by vibe-hunks.py for `--assemble`; not a script of its own.

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


def _beat(title, raw):
    """One beat: its own prose, then (hunk id, level, reason, note prose) items."""
    parts = PLACEHOLDER.split(raw)
    items = []
    for i in range(1, len(parts), 4):
        level = parts[i + 1].lower() if parts[i + 1] else None
        reason = (parts[i + 2] or '').strip() if level else ''
        items.append((parts[i], level, reason, _prose(parts[i + 3])))
    return {'title': _title(title) if title else '', 'say': _prose(parts[0]), 'items': items}


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
    return {'title': _title(title), 'intro': _prose(intro), 'beats': beats}


def parse_fragments(texts):
    """-> (title html, summary html, chapters). `texts` are fragment bodies in page order."""
    title, summary, chapters = '', [], []
    for text in texts:
        text = WRAPPERS.sub('', text)
        m = H1.search(text)
        if m:
            # The fragment with the <h1> is the intro. Everything else in it is the tour
            # summary, whatever headings it uses; only fragments without an <h1> hold
            # chapters.
            if not title:
                title = m.group(1).strip()
            rest = text[:m.start()] + text[m.end():]
            if rest.strip():
                summary.append(_prose(rest))
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

def _kind(h):
    head = '\n'.join(h.header)
    if 'GIT binary patch' in head or '\nBinary files ' in head:
        return 'binary'
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


def figure(h, ident, level, reason, note=''):
    """One hunk: its sentence with the level badge in front, the level's reason if any,
    then the diff card. The whole thing is one figure with the level as its left edge, so
    the hunks of a beat form a vertical line striped by attention level."""
    kind = _kind(h)
    add = sum(1 for l in h.body[1:] if l.startswith('+'))
    rem = sum(1 for l in h.body[1:] if l.startswith('-'))
    where = html.escape(h.path)
    if h.line is not None:
        where += ':%d' % h.line
    if add or rem:
        where += ' · <span class="sz">%s%s</span>' % ('+%d ' % add if add else '', '−%d' % rem if rem else '')
    tags = []
    if kind in ('added', 'deleted', 'moved'):
        tags.append('<span class="tag %s">%s</span>' % (kind, kind))
    name = level or 'plain'
    badge = '<span class="lvl">%s</span>' % (level if level else 'read')
    # The badge opens the hunk's sentence, so the level is the first thing the eye meets
    # and the sentence reads as "FISHY: what this hunk is about".
    note = note or '<p></p>'
    note = re.sub(r'<p\b[^>]*>', lambda m: m.group(0) + badge, note, count=1)
    out = ['<figure class="hunk lvl-%s%s" id="%s" data-key="%s" data-level="%d"%s>'
           % (name, ' file' if not h.body else '', ident, _key(h), LEVELS[level],
              (' data-reason="%s"' % html.escape(reason, quote=True)) if reason else ''),
           '<div class="note">%s</div>' % note]
    if level in ('note', 'fishy', 'hot'):
        out.append('<p class="flag %s"><b>%s:</b> %s</p>'
                   % (level, FLAG_LABEL[level],
                      html.escape(reason) if reason else 'please check this change'))
    out.append('<div class="card">')
    out.append('<figcaption><span class="where">%s</span><span class="tools">%s</span></figcaption>'
               % (where, ''.join(tags)))
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
        out.append('<div class="binary">%s</div>' % NO_BODY[kind])
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
    return '<div class="legend">%s</div>' % ''.join(rows)


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
    seen, unknown, dupes = {}, [], []

    def fig(hid, level, reason, note=''):
        if hid not in by_id:
            unknown.append(hid)
            return '<p class="missing"><strong>Unknown hunk %s</strong></p>' % html.escape(hid)
        n = seen.get(hid, 0) + 1
        seen[hid] = n
        if n > 1:
            dupes.append(hid)
        return figure(by_id[hid], hid if n == 1 else '%s-%d' % (hid, n), level, reason, note)

    body = []
    for n, ch in enumerate(chapters, 1):
        body.append('<section class="chapter" id="ch%d">' % n)
        body.append('<h2><span class="n">%d</span><span class="t">%s</span></h2>' % (n, ch['title']))
        if ch['intro']:
            body.append('<div class="intro">%s</div>' % ch['intro'])
        for beat in ch['beats']:
            body.append(_beat_html(beat, fig))
        body.append('</section>')

    missing = [h for h in hunks if h.id not in seen]
    placed = len(seen)
    if missing:
        body.append('<section class="chapter" id="ch%d">' % (len(chapters) + 1))
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
    uid = hashlib.md5(os.path.abspath(out_path or 'vibe-tour.html').encode('utf-8')).hexdigest()[:10]
    title = title or 'Vibe tour'
    head = ['<h1>%s</h1>' % title,
            '<p class="meta">%s</p>' % _meta(hunks, repo, source),
            '<p class="standfirst">%s</p>' % STANDFIRST,
            legend()]
    if summary:
        head.append('<div class="summary">%s</div>' % summary)

    page = _read('layout.html')
    page = re.sub(r'<!--\s*\n  vibe tour — the page shell.*?-->\n', '', page, count=1, flags=re.S)
    page = _swap(page, 'PRISM', '\n<script>%s</script>\n' % prism_bundle())
    page = _swap(page, 'CSS', '\n<style>\n%s</style>\n' % _read('report.css'))
    page = _swap(page, 'JS', '\n<script>\n%s</script>\n' % _read('report.js'))
    page = _swap(page, 'REPORT', '\n' + '\n\n'.join(head + body) + '\n')
    plain = html.escape(re.sub(r'<[^>]+>', '', title))
    page = _swap(page, 'NAVTITLE', plain)
    page = re.sub(r'<title>.*?</title>', lambda m: '<title>%s</title>' % plain, page, count=1)
    page = page.replace('data-uid="fixture"', 'data-uid="%s"' % uid, 1)
    return page, {'placed': placed, 'missing': missing, 'unknown': unknown, 'dupes': dupes}


def _beat_html(beat, fig):
    say = []
    if beat['title']:
        say.append('<h3>%s</h3>' % beat['title'])
    if beat['say']:
        say.append(beat['say'])
    show = []
    for hid, level, reason, note in beat['items']:
        show.append(fig(hid, level, reason, note))
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
