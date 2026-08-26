"""Components -> HTML, and the HTML -> one self-contained file.

Nothing here decides anything about the report. It renders what narration.py
resolved, which is why it can be trusted to be byte-exact: a diff body is the
patch's own lines, escaped once, and nothing else.

The markup is deliberately thin. Every control on the page — the chapter nav,
the viewed toggles, the theme switch — is injected by report.js, so the only
place with any structure is a diff block, and there the structure is Prism's.
"""

from __future__ import annotations

import os
import re

from . import code as codemod
from .prose import esc, inline, render as prose

# lib/difftour/render.py -> lib/difftour -> lib -> the skill root
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS = os.path.join(ROOT, 'assets')

BINARY_TEXT = {
    'added': 'A new binary file.',
    'deleted': 'This binary file was deleted.',
    'moved': 'This binary file moved.',
    'copied': 'This binary file was copied.',
    'changed': 'This binary file changed.',
}


def _lang_class(fc):
    lang = codemod.language_of(fc) or 'none'
    return 'language-diff-%s diff-highlight' % lang


def _where(comp):
    """The metadata line under a caption: where this block is, and what it is part of."""
    bits = []
    if comp.kind == 'hunk':
        h = comp.hunk
        # A block that only removes lines has no position in the new file, and
        # ":0" on a deleted file is noise. Give the old file's line instead.
        body = h.body(*h.slice(comp.lo, comp.hi))
        if body and all(l.kind == '-' for l in body):
            start = body[0].old
        else:
            start = h.start_line(comp.lo, comp.hi)
        bits.append('<a href="#%s">%s:%d</a>' % (esc(comp.code), esc(comp.path), start))
        lo, hi = h.slice(comp.lo, comp.hi)
        if not h.is_whole(comp.lo, comp.hi):
            bits.append('lines %d–%d of %d' % (lo, hi, len(h.lines)))
        if h.file.old_path:
            bits.append('was <code>%s</code>' % esc(h.file.old_path))
        if h.file.mode:
            # A mode flip riding along with edits is a change a reviewer should see,
            # and the model never has to remember to mention it.
            bits.append('mode %s → %s' % (esc(h.file.mode[0]), esc(h.file.mode[1])))
        add = sum(1 for l in h.body(lo, hi) if l.kind == '+')
        rem = sum(1 for l in h.body(lo, hi) if l.kind == '-')
        # A collapsed hunk still says how big it is, so folding never hides scale.
        bits.append('<span class="sz">%s%s</span>' % (
            '+%d ' % add if add else '', '−%d' % rem if rem else ''))
    elif comp.kind == 'file':
        bits.append(esc(comp.path))
    elif comp.kind == 'quote':
        bits.append('%s:%d–%d' % (esc(comp.path), comp.lo, comp.hi))
    elif comp.kind == 'code':
        # Every other block states where its bytes came from. This one came from the
        # narration, so it says so rather than leaving the line blank and letting the
        # reader assume it was read from something.
        bits.append('written for this report, not taken from the change')
    if comp.siblings:
        bits.append('also ' + ', '.join('<a href="#%s">%s</a>' % (esc(s), esc(s))
                                        for s in comp.siblings))
    return ' · '.join(bits)


class _Named:
    """Just enough of a FileChange for language_of() to read a path."""
    hunks = ()

    def __init__(self, path):
        self.path = path


def _snippet_lang(comp):
    """A %code language is whatever the model typed, so it goes through the same
    alias table as a file suffix — `sh` is Prism's `bash`, and an unknown name is
    plain text rather than a class Prism will never match."""
    if comp.lang:
        name = comp.lang.strip().lower().lstrip('.')
        return codemod.BY_SUFFIX.get(name, name if name in codemod.GRAMMARS else 'none')
    return codemod.language_of(_Named(comp.path)) or 'none'


def _body(comp):
    if comp.kind == 'hunk':
        h = comp.hunk
        lo, hi = h.slice(comp.lo, comp.hi)
        out = []
        # A fragment says at its edges how much of the hunk it is not showing, so it
        # can never be read as the whole thing.
        if lo > 1:
            out.append('<span class="gap">⋯ %d more line%s above</span>'
                       % (lo - 1, '' if lo == 2 else 's'))
        out.append('<pre class="diff"><code class="%s">%s\n</code></pre>'
                   % (_lang_class(h.file),
                      esc('\n'.join(l.raw() for l in h.body(lo, hi)))))
        if hi < len(h.lines):
            out.append('<span class="gap">⋯ %d more line%s below</span>'
                       % (len(h.lines) - hi, '' if len(h.lines) - hi == 1 else 's'))
        # git records this as its own marker line, which is not part of any side's
        # text — but gaining or losing a trailing newline is a change like any other.
        for line in h.body(lo, hi):
            if line.no_newline:
                out.append('<span class="gap">\\ no newline at end of file</span>')
                break
        return '\n'.join(out)

    if comp.kind == 'file':
        fc = comp.fc
        if fc.binary:
            text = BINARY_TEXT.get(fc.kind, BINARY_TEXT['changed'])
            text += ' A diff of bytes tells a reviewer nothing, so it is named, not shown.'
        elif fc.old_path:
            text = ('%s from <code>%s</code>, with no change to its contents.'
                    % ('Copied' if fc.kind == 'copied' else 'Renamed', esc(fc.old_path)))
        elif fc.kind == 'added':
            text = 'A new empty file.'
        elif fc.kind == 'deleted':
            text = 'An empty file, deleted.'
        elif fc.mode:
            text = ('The file mode changed from <code>%s</code> to <code>%s</code>, with '
                    'no change to its contents.' % (esc(fc.mode[0]), esc(fc.mode[1])))
        else:
            text = 'A change with no diff body.'
        return '<div class="binary">%s</div>' % text

    return '<pre class="code"><code class="language-%s">%s</code></pre>' % (
        esc(_snippet_lang(comp)), esc('\n'.join(comp.body)))


def component(comp, seq=0, refs=None):
    kind = {'hunk': '', 'file': ' file', 'quote': ' quote', 'code': ' quote'}[comp.kind]
    # A coded block is addressed by its code; an uncoded one needs some id to be
    # linkable, and two identical quotes would otherwise collide on their content hash.
    ident = comp.code or ('q%d-%s' % (seq, comp.key_hash))
    tag = ''
    if comp.kind in ('hunk', 'file'):
        fc = comp.fc or (comp.hunk.file if comp.hunk else None)
        if fc:
            tag = '<span class="tag %s">%s</span>' % (esc(fc.kind), esc(fc.kind))
    return (
        '<figure class="hunk%s" id="%s" %sdata-key="%s">\n'
        '  <figcaption>\n'
        '    <span class="code">%s</span>\n'
        '    <span class="cap">%s</span>\n'
        '    <span class="where">%s</span>\n'
        '    <span class="tools">%s</span>\n'
        '  </figcaption>\n%s\n</figure>'
    ) % (kind, esc(ident),
         ('data-code="%s" ' % esc(comp.code)) if comp.code else '',
         esc(comp.key_hash),
         esc(comp.code) if comp.code else ('quote' if comp.kind != 'code' else 'snippet'),
         inline(comp.caption, refs), _where(comp), tag, _body(comp))


def beat(b, ch, refs=None):
    ident = 'b%d-%d' % (ch.number, ch.beats.index(b) + 1)
    say = ['<h3 id="%s">%s</h3>' % (ident, inline(b.subtitle, refs))]
    if b.prose:
        say.append(prose(b.prose, refs))
    # A block's own prose is part of the block, so it is emitted with it — above the
    # diff, the way its caption is. There is nothing to guess about which block a
    # paragraph belongs to.
    show = []
    for n, item in enumerate(b.items, 1):
        lead = prose(item.lead, refs)
        show.append(('<div class="note">%s</div>' % lead if lead else '')
                    + component(item, seq=n, refs=refs))
    cls = 'beat' if show else 'beat solo'
    out = ['<section class="%s">' % cls,
           '<div class="say">%s</div>' % '\n'.join(say)]
    if show:
        out.append('<div class="show">%s</div>' % '\n'.join(show))
    out.append('</section>')
    return '\n'.join(out)


def chapter(ch, refs=None):
    out = ['<section class="chapter" id="ch%d">' % ch.number,
           '<h2><span class="n">%d</span><span class="t">%s</span></h2>'
           % (ch.number, inline(ch.title, refs))]
    if ch.intro:
        body = prose(ch.intro, refs)
        if body:
            out.append('<div class="intro">%s</div>' % body)
    if ch.blast_level:
        out.append('<aside class="blast %s" data-level="%s">%s</aside>'
                   % (ch.blast_level, ch.blast_level, prose(ch.blast, refs) or ''))
    for b in ch.beats:
        out.append(beat(b, ch, refs))
    out.append('</section>')
    return '\n'.join(out)


# What the report is, in the report. Fixed text, emitted by the builder rather than
# written each time: it describes the tour itself, so it cannot be allowed to drift,
# and it is not the model's tokens to spend.
STANDFIRST = (
    'A guided tour through one change, for a human reviewing code they did not write. '
    'It says what each change is for, what the code did before, and where to look '
    'closely. It points at risk rather than ruling on the change, and it is not an '
    'automated code review — pair it with one.')


def _meta_line(stats, source, date, repo=None, branch=None):
    bits = []
    if repo:
        bits.append('<b>%s</b>' % esc(repo))
    if branch:
        bits.append('<b>%s</b>' % esc(branch))
    bits.append('<b>%d</b> file%s' % (stats['files'], '' if stats['files'] == 1 else 's'))
    bits.append('<b class="added">+%s</b> <b class="removed">−%s</b>'
                % ('{:,}'.format(stats['added']), '{:,}'.format(stats['removed'])))
    # "hunk" is a git word. The reader is a reviewer, not a git user.
    bits.append('<b>%d</b> change%s' % (stats['hunks'],
                                        '' if stats['hunks'] == 1 else 's'))
    bits.append('<code>%s</code>' % esc(source))
    bits.append(esc(date))
    return ' · '.join(bits)


def _swap(html, mark, content):
    """Replace what sits between <!--MARK--> and <!--/MARK-->."""
    a, b = '<!--%s-->' % mark, '<!--/%s-->' % mark
    if a not in html or b not in html:
        raise SystemExit('tour-build: assets/layout.html has no %s marker pair. The '
                         'builder fills the report in between those markers, so the '
                         'layout cannot be edited away.' % mark)
    i, j = html.index(a), html.index(b)
    return html[:i + len(a)] + content + html[j:]


def page(rep, stats, source, date, uid, layout=None, repo=None, branch=None):
    """The whole report as one self-contained HTML document."""
    path = layout or os.path.join(ASSETS, 'layout.html')
    with open(path, encoding='utf-8') as f:
        html = f.read()
    with open(os.path.join(ASSETS, 'report.css'), encoding='utf-8') as f:
        css = f.read()
    with open(os.path.join(ASSETS, 'report.js'), encoding='utf-8') as f:
        js = f.read()
    prism, missing = codemod.bundle()

    body = ['<h1>%s</h1>' % inline(rep.title, rep.refs),
            '<p class="meta">%s</p>' % _meta_line(stats, source, date, repo, branch),
            '<p class="standfirst">%s</p>' % STANDFIRST]
    body += [chapter(ch, rep.refs) for ch in rep.chapters]

    html = _swap(html, 'PRISM', '\n<script>%s</script>\n' % prism)
    html = _swap(html, 'CSS', '\n<style>\n%s</style>\n' % css)
    html = _swap(html, 'JS', '\n<script>\n%s</script>\n' % js)
    html = _swap(html, 'REPORT', '\n' + '\n\n'.join(body) + '\n')
    html = _swap(html, 'NAVTITLE', esc(rep.title))
    html = html.replace('data-uid="fixture"', 'data-uid="%s"' % esc(uid), 1)
    # A replacement string would read a backslash or \\g<0> in the title as a regex
    # escape, so substitute with a function and let the title stay literal.
    html = re.sub(r'<title>.*?</title>', lambda m: '<title>%s</title>' % esc(rep.title),
                  html, count=1)
    # The fixture's own explanatory comment is for whoever edits the layout, not for
    # a reader of the report.
    html = re.sub(r'<!--\s*\n  diff tour — the page shell.*?-->\n', '', html, count=1, flags=re.S)
    return html, missing
