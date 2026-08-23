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
YELLOW = "\x1b[38;5;179m"                      # the report title and its heavy rule
BOLD_ON = "\x1b[1m"
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
BULLET = re.compile(r"^(\s*)([-*]|\d{1,3}[.)])\s+(.*)$")
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
        # The report title: yellow capitals over a heavy yellow rule. The weight of the
        # rule is what separates it from a chapter title's light one, and yellow is the
        # only place the narration uses it, so the top of the document is unmistakable.
        rows = textwrap.wrap(text.upper(), width) or [""]
        out = [YELLOW + BOLD_ON + row + R for row in rows]
        out.append(YELLOW + "━" * width + R)
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
    """Group the source into (kind, payload) blocks. Consecutive text lines are one
    paragraph and consecutive list items are one list, so neither gets a blank line
    inserted inside it. Only a block *boundary* flushes — never a continuation."""
    para, items = [], []

    def flush():
        out = []
        if para:
            out.append(("para", " ".join(para)))
            para.clear()
        if items:
            out.append(("list", list(items)))
            items.clear()
        return out

    for raw in lines:
        line = raw.rstrip("\n")
        heading = HEADING.match(line)
        bullet = BULLET.match(line)

        if bullet:                        # continues a list, or starts one
            yield from flush() if para else ()
            items.append(bullet)
            continue
        if not line.strip():              # blank ends whatever was open
            yield from flush()
            continue
        if heading:
            yield from flush()
            yield ("heading", (len(heading.group(1)), heading.group(2)))
            continue
        if HRULE.match(line.strip()):
            yield from flush()
            yield ("rule", None)
            continue
        if QUOTED.match(line):
            yield from flush()
            yield ("quote", QUOTED.match(line).group(1))
            continue
        if items:                         # text after a list ends the list
            yield from flush()
        para.append(line.strip())         # continuation: accumulate, do not flush

    yield from flush()


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
        elif kind == "list":
            for item in payload:
                indent, marker, text = item.group(1), item.group(2), item.group(3)
                # Keep a numbered marker as written — the overview's chapter list is
                # numbered, and its numbers are the chapter numbers.
                lead = "·" if marker in ("-", "*") else marker
                body = textwrap.wrap(text, max(20, width - len(indent) - len(lead) - 1)) or [""]
                out.append(f"{indent}{DIM}{lead}{R} " + inline(body[0]))
                out.extend(" " * (len(indent) + len(lead) + 1) + inline(b) for b in body[1:])
        elif kind == "quote":
            for w in textwrap.wrap(payload, max(20, width - 2)) or [""]:
                out.append(QUOTE + "▏ " + inline(w) + R)
        else:
            out.extend(inline(w) for w in textwrap.wrap(payload, width) or [""])
    print("\n".join(out))


if __name__ == "__main__":
    main()
