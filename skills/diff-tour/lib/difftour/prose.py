"""A markdown subset, rendered to HTML.

The subset is fixed by the SKILL, not by what happens to be installed: one
renderer, always, so the same narration file produces the same report on every
machine. Paragraphs, `-`/`1.` lists, **bold**, *italic*, `code`, [links](url).

`esc` is the one escaping chokepoint in the whole builder. Diff bodies, captions,
paths and titles all come from a change written by someone else, so a line
containing `</script>` has to be text everywhere, not text in most places.
"""

import re

_ESC = (('&', '&amp;'), ('<', '&lt;'), ('>', '&gt;'), ('"', '&quot;'))

INLINE = re.compile(
    r'`(?P<code>[^`]+)`'
    r'|\[\[(?P<ref>[A-Za-z][A-Za-z0-9_-]*)\]\]'
    r'|\[(?P<text>[^\]]+)\]\((?P<href>[^)\s]+)\)'
    r'|\*\*(?P<bold>(?:[^*]|\*(?!\*))+)\*\*'
    r'|(?<![\w*])\*(?P<em>[^*\n]+)\*(?![\w*])'
)

BULLET = re.compile(r'^\s*[-*+]\s+(.*)$')
NUMBER = re.compile(r'^\s*\d+[.)]\s+(.*)$')


def esc(s):
    for a, b in _ESC:
        s = s.replace(a, b)
    return s


def _target(name, refs):
    """A label or a chapter name -> (href, default link text)."""
    if refs and name in refs:
        return '#' + refs[name], refs[name]
    if re.match(r'^ch\d+$', name):
        return '#' + name, 'chapter ' + name[2:]
    return None, None


def inline(text, refs=None):
    out, pos = [], 0
    for m in INLINE.finditer(text):
        out.append(esc(text[pos:m.start()]))
        if m.group('code') is not None:
            out.append('<code>%s</code>' % esc(m.group('code')))
        elif m.group('ref') is not None:
            # [[h17]] -> a link showing the code that label currently resolves to.
            href, label = _target(m.group('ref'), refs)
            if href:
                out.append('<a class="ref" href="%s"><code>%s</code></a>'
                           % (esc(href), esc(label)))
            else:
                out.append('<code>%s</code>' % esc(m.group('ref')))
        elif m.group('href') is not None:
            href = m.group('href')
            # A fragment may name a label, which resolves to the current code. Any
            # other href is a URL, and only http(s), mailto and fragments pass.
            if href.startswith('#'):
                resolved, _ = _target(href[1:], refs)
                href = resolved or href
            if not re.match(r'^(#|https?://|mailto:)', href):
                out.append(inline(m.group('text'), refs))
            else:
                out.append('<a href="%s">%s</a>'
                           % (esc(href), inline(m.group('text'), refs)))
        elif m.group('bold') is not None:
            out.append('<strong>%s</strong>' % inline(m.group('bold'), refs))
        else:
            out.append('<em>%s</em>' % inline(m.group('em'), refs))
        pos = m.end()
    out.append(esc(text[pos:]))
    return ''.join(out)


def render(lines, refs=None):
    """A list of markdown lines -> HTML block elements."""
    out = []
    items = None            # (tag, [ [line, ...], ... ]) while a list is open
    para = []

    def flush_para():
        if para:
            out.append('<p>%s</p>' % inline(' '.join(para).strip(), refs))
            del para[:]

    def flush_list():
        nonlocal items
        if items:
            tag, entries = items
            out.append('<%s>%s</%s>' % (tag, ''.join(
                '<li>%s</li>' % inline(' '.join(e).strip(), refs) for e in entries), tag))
            items = None

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            flush_para(); flush_list()
            continue
        b, n = BULLET.match(line), NUMBER.match(line)
        if b or n:
            flush_para()
            tag = 'ul' if b else 'ol'
            if items and items[0] != tag:
                flush_list()
            if not items:
                items = (tag, [])
            items[1].append([(b or n).group(1)])
            continue
        if items:
            # A hard-wrapped list item continues on the next line, indented or not.
            items[1][-1].append(line.strip())
            continue
        para.append(line.strip())
    flush_para(); flush_list()
    return '\n'.join(out)
