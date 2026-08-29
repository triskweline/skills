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

# Emphasis needs flanking rules, which is the one part of markdown that is genuinely
# hard and the one this format kept getting wrong. Without them, any pair of asterisks
# in prose was eaten and the span between them italicised: "n * backoff * 2", "*.js and
# *.css", "**/*.js and **/*.css". That is the only channel through which a finished
# report showed the reader text the narrator did not write — captions included.
#
# The rule, from CommonMark: emphasis cannot open before whitespace, and cannot close
# after it. Content therefore begins and ends with a non-space character. That leaves
# exactly one ambiguity nothing can resolve — `**/node_modules/**` is character for
# character what bold around `/node_modules/` looks like — and for that there are two
# escapes: put the glob in backticks, which is where code belongs anyway, or write \*.
INLINE = re.compile(
    r'\\(?P<esc>[*`\[\]\\])'
    r'|`(?P<code>[^`]+)`'
    r'|\[\[(?P<ref>[A-Za-z][A-Za-z0-9_-]*)\]\]'
    r'|\[(?P<text>[^\]]+)\]\((?P<href>[^)\s]+)\)'
    r'|\*\*(?P<bold>[^\s*](?:[^*]|\*(?!\*))*?[^\s*]|[^\s*])\*\*'
    r'|(?<![\w*])\*(?P<em>[^\s*][^*\n]*?[^\s*]|[^\s*])\*(?![\w*])'
)

BULLET = re.compile(r'^\s*[-*+]\s+(.*)$')
NUMBER = re.compile(r'^\s*(\d+)[.)]\s+(.*)$')


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
    if re.match(r'^b\d+-\d+$', name):
        # A beat, so the overview can point at the part that earned a level rather than
        # at the chapter around it.
        return '#' + name, 'chapter ' + name[1:].split('-')[0]
    return None, None


def inline(text, refs=None):
    out, pos = [], 0
    for m in INLINE.finditer(text):
        out.append(esc(text[pos:m.start()]))
        if m.group('esc') is not None:
            # A backslashed marker is that character, literally.
            out.append(esc(m.group('esc')))
        elif m.group('code') is not None:
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
    start = None            # the first numeral of an ordered list
    para = []

    def flush_para():
        if para:
            out.append('<p>%s</p>' % inline(' '.join(para).strip(), refs))
            del para[:]

    def flush_list():
        nonlocal items, start
        if items:
            tag, entries = items
            # An ordered list that starts at 3 means it. Renumbering from 1 silently
            # contradicts whatever the author was numbering — chapters, most likely.
            attr = ' start="%d"' % start if tag == 'ol' and start not in (None, 1) else ''
            out.append('<%s%s>%s</%s>' % (tag, attr, ''.join(
                '<li>%s</li>' % inline(' '.join(e).strip(), refs) for e in entries), tag))
            items = None
            start = None

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
                if n:
                    start = int(n.group(1))
            items[1].append([b.group(1) if b else n.group(2)])
            continue
        if items:
            # A hard-wrapped list item continues on the next line, indented or not.
            items[1][-1].append(line.strip())
            continue
        para.append(line.strip())
    flush_para(); flush_list()
    return '\n'.join(out)
