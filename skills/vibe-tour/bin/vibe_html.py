"""Fragments + numbered hunks -> one self-contained HTML page.

Imported by vibe-hunks.py for `--assemble`; not a script of its own.

Workers write plain fragments: <h2> per topic, <h3> per beat, <p> prose, and a
`<!-- hunk h17 -->` placeholder where a hunk belongs (`<!-- hunk h17 fishy: why -->`
when it feels off). Everything else on the page is mechanical and happens here:
chapter numbers, ids, the meta line, the two-column layout, the figures with the
real diff bytes, syntax highlighting, the sidebar. Nothing in this file decides
anything about the tour; it only lays out what the workers wrote.

Standard library only. Works on Python 3.8+.
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

PLACEHOLDER = re.compile(r'<!--\s*hunk\s+(h\d+)(?:\s+fishy\b\s*:?\s*(.*?))?\s*-->', re.S | re.I)
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
    """One beat: its own prose, then (hunk id, fishy reason, note prose) items."""
    parts = PLACEHOLDER.split(raw)
    items = []
    for i in range(1, len(parts), 3):
        reason = parts[i + 1]
        items.append((parts[i], reason.strip() if reason is not None else None, _prose(parts[i + 2])))
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
            if not title:
                title = m.group(1).strip()
            text = text[:m.start()] + text[m.end():]
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


def figure(h, ident, reason):
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
    fishy = reason is not None
    if fishy:
        tags.append('<span class="tag fishy">fishy</span>')
    out = ['<figure class="hunk%s%s" id="%s" data-key="%s">'
           % (' fishy' if fishy else '', ' file' if not h.body else '', ident, _key(h)),
           '<figcaption><span class="where">%s</span><span class="tools">%s</span></figcaption>'
           % (where, ''.join(tags))]
    if fishy:
        out.append('<aside class="fishy"><p>%s</p></aside>'
                   % (html.escape(reason) if reason else 'Please check this change.'))
    if h.body:
        out.append('<pre class="diff"><code class="language-diff-%s diff-highlight">%s\n</code></pre>'
                   % (language_of(h.path, h.body), html.escape('\n'.join(h.body))))
    else:
        out.append('<div class="binary">%s</div>' % NO_BODY[kind])
    out.append('</figure>')
    return '\n'.join(out)


# ---------------------------------------------------------------------- page

STANDFIRST = (
    'A fast, narrated tour through one change, for a human reviewing code they did not '
    'write. It groups the diff into topics and shows every hunk. A hunk marked '
    '<b>fishy</b> felt off on a first read; nothing was verified, and the judgement is yours.')


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


def render(hunks, texts, git_args):
    """-> (page html, report dict with placed / missing / unknown / duplicate ids)."""
    title, summary, chapters = parse_fragments(texts)
    by_id = dict((h.id, h) for h in hunks)
    seen, unknown, dupes = {}, [], []

    def fig(hid, reason):
        if hid not in by_id:
            unknown.append(hid)
            return '<p class="missing"><strong>Unknown hunk %s</strong></p>' % html.escape(hid)
        n = seen.get(hid, 0) + 1
        seen[hid] = n
        if n > 1:
            dupes.append(hid)
        return figure(by_id[hid], hid if n == 1 else '%s-%d' % (hid, n), reason)

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
                    % '\n'.join(fig(h.id, None) for h in missing))
        body.append('</section>')

    top = _git('rev-parse', '--show-toplevel')
    repo = os.path.basename(top) if top else ''
    source = ' '.join(a for a in git_args if a) or 'working tree'
    uid = hashlib.md5((top + '\0' + source).encode('utf-8')).hexdigest()[:10]
    title = title or 'Vibe tour'
    head = ['<h1>%s</h1>' % title,
            '<p class="meta">%s</p>' % _meta(hunks, repo, source),
            '<p class="standfirst">%s</p>' % STANDFIRST]
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
    for hid, reason, note in beat['items']:
        if note:
            show.append('<div class="note">%s</div>' % note)
        show.append(fig(hid, reason))
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
