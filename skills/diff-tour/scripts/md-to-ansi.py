#!/usr/bin/env python3
"""Render the tour's narration to ANSI for a terminal document.

The mirror of ansi-to-html.py: that one turns delta's ANSI into HTML for the export
document, this one turns the narration's markdown into ANSI for the same purpose. Hunks
need no conversion in this direction — delta already emits ANSI, so they are inserted
verbatim by tour-ansi.sh.

Works in blocks, not lines: consecutive text lines are one paragraph and are reflowed to
the full width, so the narration's own hard wrapping does not cap the document's.

Usage:  md-to-ansi.py [--width N] < narration.md      (default width 120)
"""
import re
import sys
import textwrap

R = "\x1b[0m"
# The page already carries delta's syntax highlighting and its yellow hunk caption. So the
# headings spend almost no colour: one blue badge for the chapter mark, and otherwise
# weight, capitals and grey rules. Hierarchy comes from structure, not hue.
BADGE = "\x1b[48;5;25m\x1b[38;5;231m\x1b[1m"   # the chapter mark, e.g. " 3/9 "
TITLE = "\x1b[1;38;5;231m"                     # bold white, no background
H3 = "\x1b[1;38;5;231m"                        # subheading: bold white, nothing else
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
ITAL = "\x1b[3m"
CODE = "\x1b[38;5;215m"                         # tinted inline code
RULE = "\x1b[38;5;240m"
QUOTE = "\x1b[38;5;245m"

INLINE = [
    (re.compile(r"`([^`]+)`"), lambda m: CODE + m.group(1) + R),
    (re.compile(r"\*\*([^*]+)\*\*"), lambda m: BOLD + m.group(1) + R),
    (re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)"), lambda m: ITAL + m.group(1) + R),
]

HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
BULLET = re.compile(r"^(\s*)[-*]\s+(.*)$")
QUOTED = re.compile(r"^>\s?(.*)$")
HRULE = re.compile(r"^(-{3,}|\*{3,}|_{3,})$")


def inline(text):
    for pattern, repl in INLINE:
        text = pattern.sub(repl, text)
    return text


CHAPTER_MARK = re.compile(r"^\s*(\d+\s*/\s*\d+)\s*·\s*(.*)$")


def render_heading(level, text, width):
    # Both rules are single lines; the difference is weight of colour. A chapter title is
    # underlined in white, delta underlines a hunk caption in grey. The report title needs
    # neither, since its box carries it.
    rule = RULE + "─" * width + R
    bright = "\x1b[38;5;231m" + "─" * width + R
    if level == 1:
        # The report title in a double-line box, so it cannot be mistaken for a chapter
        # title. Wraps inside the box rather than truncating, since a change's one-line
        # title can be long.
        inner = max(10, width - 4)
        body = textwrap.wrap(text.upper(), inner) or [""]
        top = RULE + "╔" + "═" * (inner + 2) + "╗" + R
        bottom = RULE + "╚" + "═" * (inner + 2) + "╝" + R
        side = RULE + "║" + R
        out = [top]
        for row in body:
            out.append(side + " " + TITLE + row.ljust(inner) + R + " " + side)
        out.append(bottom)
        return out
    if level == 2:
        # " 3/9 " as a badge, then the title in capitals with no background, then a rule.
        m = CHAPTER_MARK.match(text)
        if m:
            head = BADGE + " " + m.group(1).replace(" ", "") + " " + R + " " + TITLE + m.group(2).upper() + R
        else:
            head = TITLE + text.upper() + R
        return [head, bright]
    return [H3 + inline(text) + R]


def blocks(lines):
    """Group the source into (kind, payload) blocks. A paragraph is consecutive text."""
    para = []
    for raw in lines:
        line = raw.rstrip("\n")
        m = HEADING.match(line)
        if m or HRULE.match(line.strip()) or BULLET.match(line) or QUOTED.match(line) or not line.strip():
            if para:
                yield ("para", " ".join(para))
                para = []
        if not line.strip():
            continue
        if m:
            yield ("heading", (len(m.group(1)), m.group(2)))
        elif HRULE.match(line.strip()):
            yield ("rule", None)
        elif BULLET.match(line):
            yield ("bullet", BULLET.match(line))
        elif QUOTED.match(line):
            yield ("quote", QUOTED.match(line).group(1))
        else:
            para.append(line.strip())
    if para:
        yield ("para", " ".join(para))


def main():
    width = 120
    if "--width" in sys.argv:
        width = int(sys.argv[sys.argv.index("--width") + 1])

    out = []
    for kind, payload in blocks(sys.stdin):
        if out:
            # Two blank lines before a heading, one between anything else, so a heading
            # reads as the start of something rather than the next paragraph.
            out.extend(["", ""] if kind == "heading" else [""])
        if kind == "heading":
            out.extend(render_heading(payload[0], payload[1], width))
        elif kind == "rule":
            out.append(RULE + "─" * width + R)
        elif kind == "bullet":
            indent = payload.group(1)
            body = textwrap.wrap(payload.group(2), max(20, width - len(indent) - 2)) or [""]
            out.append(f"{indent}{DIM}·{R} " + inline(body[0]))
            out.extend(" " * (len(indent) + 2) + inline(b) for b in body[1:])
        elif kind == "quote":
            for w in textwrap.wrap(payload, max(20, width - 2)) or [""]:
                out.append(QUOTE + "▏ " + inline(w) + R)
        else:
            out.extend(inline(w) for w in textwrap.wrap(payload, width) or [""])
    print("\n".join(out))


if __name__ == "__main__":
    main()
