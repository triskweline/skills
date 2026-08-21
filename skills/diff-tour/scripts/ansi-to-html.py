#!/usr/bin/env python3
"""Convert delta's ANSI output into self-contained HTML.

Delta already solves the hard part: it emits per-token foreground colors (syntax
highlighting, via syntect) *and* per-line background colors (diff state) in one
stream. Translating SGR codes to inline styles preserves both, so the page shows
green/red diff rows with real language highlighting inside them — with no external
stylesheet, script or font, which is what a strict CSP needs.

Usage:  delta --paging=never --line-numbers --width 160 < tour.diff | ansi-to-html.py > page.html
"""
import html
import re
import sys

SGR = re.compile(r"\x1b\[([0-9;]*)m")
EL = re.compile(r"\x1b\[[0-9]*K")          # erase-to-end-of-line: delta's row fill
OTHER = re.compile(r"\x1b\[[0-9;]*[^m0-9;]")   # stray escapes, but never SGR ("…m")

BASIC = ["#000000", "#cd3131", "#0dbc79", "#e5e510",
         "#2472c8", "#bc3fbc", "#11a8cd", "#e5e5e5"]


def cube(n):
    if n < 16:
        return BASIC[n % 8]
    if n < 232:
        n -= 16
        r, g, b = n // 36, (n % 36) // 6, n % 6
        f = lambda v: 0 if v == 0 else 55 + 40 * v
        return "#%02x%02x%02x" % (f(r), f(g), f(b))
    v = 8 + (n - 232) * 10
    return "#%02x%02x%02x" % (v, v, v)


def parse(params, state):
    """Apply one SGR sequence to the running style state."""
    codes = [int(c) for c in params.split(";") if c != ""] or [0]
    i = 0
    while i < len(codes):
        c = codes[i]
        if c == 0:
            state.update(fg=None, bg=None, bold=False, dim=False, italic=False, under=False)
        elif c == 1: state["bold"] = True
        elif c == 2: state["dim"] = True
        elif c == 3: state["italic"] = True
        elif c == 4: state["under"] = True
        elif c == 22: state["bold"] = state["dim"] = False
        elif c == 23: state["italic"] = False
        elif c == 24: state["under"] = False
        elif c == 39: state["fg"] = None
        elif c == 49: state["bg"] = None
        elif 30 <= c <= 37: state["fg"] = BASIC[c - 30]
        elif 40 <= c <= 47: state["bg"] = BASIC[c - 40]
        elif 90 <= c <= 97: state["fg"] = BASIC[c - 90]
        elif 100 <= c <= 107: state["bg"] = BASIC[c - 100]
        elif c in (38, 48):
            key = "fg" if c == 38 else "bg"
            mode = codes[i + 1] if i + 1 < len(codes) else None
            if mode == 2 and i + 4 < len(codes):
                state[key] = "#%02x%02x%02x" % tuple(codes[i + 2:i + 5])
                i += 4
            elif mode == 5 and i + 2 < len(codes):
                state[key] = cube(codes[i + 2])
                i += 2
            else:
                break            # truncated or unknown form: stop, don't reinterpret operands
        i += 1
    return state


def style_of(state):
    parts = []
    if state["fg"]: parts.append("color:%s" % state["fg"])
    if state["bg"]: parts.append("background:%s" % state["bg"])
    if state["bold"]: parts.append("font-weight:600")
    if state["dim"]: parts.append("opacity:.65")
    if state["italic"]: parts.append("font-style:italic")
    if state["under"]: parts.append("text-decoration:underline")
    return ";".join(parts)


def convert_line(line, state):
    """One terminal line -> one <div>. The background active where delta erases to
    end of line becomes the row background, which is how a diff row gets filled."""
    row_bg = None
    for m in EL.finditer(line):
        probe = dict(state)
        for sgr in SGR.finditer(line[:m.start()]):
            parse(sgr.group(1), probe)
        row_bg = probe["bg"] or row_bg
    line = EL.sub("", line)
    line = OTHER.sub("", line)

    out, pos = [], 0
    for m in SGR.finditer(line):
        text = line[pos:m.start()]
        if text:
            s = style_of(state)
            out.append('<span style="%s">%s</span>' % (s, html.escape(text)) if s else html.escape(text))
        parse(m.group(1), state)
        pos = m.end()
    tail = line[pos:]
    if tail:
        s = style_of(state)
        out.append('<span style="%s">%s</span>' % (s, html.escape(tail)) if s else html.escape(tail))

    attr = ' style="background:%s"' % row_bg if row_bg else ""
    return '<div class="r"%s>%s</div>' % (attr, "".join(out) or "&nbsp;")


def main():
    state = dict(fg=None, bg=None, bold=False, dim=False, italic=False, under=False)
    rows = [convert_line(l.rstrip("\n"), state) for l in sys.stdin]
    print('<div class="diff">%s</div>' % "\n".join(rows))


if __name__ == "__main__":
    main()
