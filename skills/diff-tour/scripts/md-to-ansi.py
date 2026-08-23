#!/usr/bin/env python3
"""Render the tour's narration to ANSI for a terminal document.

The mirror of ansi-to-html.py: that one turns delta's ANSI into HTML for the export
document, this one turns the narration's markdown into ANSI for the same purpose. Hunks
need no conversion in this direction — delta already emits ANSI, so they are inserted
verbatim by tour-ansi.sh.

Handles the subset the narration actually uses: headings, bold, italic, inline code,
bullets, block quotes, rules. Reads stdin, writes stdout.

Usage:  md-to-ansi.py [--width N] < narration.md
"""
import re
import sys
import textwrap

R = "\x1b[0m"
H1 = "\x1b[1;38;5;231m"      # near-white bold
H2 = "\x1b[1;38;5;117m"      # bold blue
H3 = "\x1b[1;38;5;150m"      # bold green
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
ITAL = "\x1b[3m"
CODE = "\x1b[38;5;215m"      # tinted inline code
RULE = "\x1b[38;5;240m"
QUOTE = "\x1b[38;5;245m"

INLINE = [
    (re.compile(r"`([^`]+)`"), lambda m: CODE + m.group(1) + R),
    (re.compile(r"\*\*([^*]+)\*\*"), lambda m: BOLD + m.group(1) + R),
    (re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)"), lambda m: ITAL + m.group(1) + R),
]


def inline(text):
    for pattern, repl in INLINE:
        text = pattern.sub(repl, text)
    return text


def visible_len(text):
    return len(re.sub(r"\x1b\[[0-9;]*m", "", text))


def emit(line, width):
    """One markdown line -> zero or more ANSI lines."""
    if not line.strip():
        return [""]
    if re.match(r"^(-{3,}|\*{3,}|_{3,})$", line.strip()):
        return [RULE + "─" * min(width, 78) + R]
    m = re.match(r"^(#{1,6})\s+(.*)$", line)
    if m:
        level, text = len(m.group(1)), inline(m.group(2))
        colour = {1: H1, 2: H2}.get(level, H3)
        out = ["", colour + text + R]
        if level <= 2:
            out.append(RULE + "─" * min(width, visible_len(text)) + R)
        return out
    m = re.match(r"^(\s*)[-*]\s+(.*)$", line)
    if m:
        indent = m.group(1)
        body = textwrap.wrap(m.group(2), max(20, width - len(indent) - 2)) or [""]
        first = f"{indent}{DIM}·{R} " + inline(body[0])
        rest = [" " * (len(indent) + 2) + inline(b) for b in body[1:]]
        return [first] + rest
    m = re.match(r"^>\s?(.*)$", line)
    if m:
        return [QUOTE + "▏ " + inline(m.group(1)) + R]
    # A plain paragraph line. Wrap on the source line, not the whole paragraph, so the
    # narration's own line breaks are respected.
    wrapped = textwrap.wrap(line, max(20, width)) or [""]
    return [inline(w) for w in wrapped]


def main():
    width = 96
    if "--width" in sys.argv:
        width = int(sys.argv[sys.argv.index("--width") + 1])
    for raw in sys.stdin:
        for out in emit(raw.rstrip("\n"), width):
            print(out)


if __name__ == "__main__":
    main()
