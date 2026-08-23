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
# Headings must outrank delta's hunk caption (bold yellow in a yellow box), and each other
# at a glance. Hierarchy is carried by *height* first — a three-line bar, a one-line bar,
# then plain text — and by hue second, so it survives an unusual colour scheme.
H1_BG = "\x1b[48;5;25m\x1b[38;5;231m\x1b[1m"    # bold white on blue, three lines tall
H2_BG = "\x1b[48;5;54m\x1b[38;5;231m\x1b[1m"    # bold white on purple, one line
H3 = "\x1b[1;4;38;5;80m"                        # bold underlined teal, no bar
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


def bar(text, style, width):
    body = ("  " + text)[:width].ljust(width)
    return style + body + R


def render_heading(level, text, width):
    if level == 1:
        pad = bar("", H1_BG, width)
        return [pad, bar(text, H1_BG, width), pad]
    if level == 2:
        return [bar(text, H2_BG, width)]
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
