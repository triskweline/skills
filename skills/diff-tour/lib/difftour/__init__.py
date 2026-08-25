"""The implementation the bin/ commands share. Nothing here is run directly.

    patch.py       a unified diff -> files, hunks, body lines
    narration.py   the narration file -> a validated report, plus coverage
    prose.py       the markdown subset -> HTML, and the one escaping chokepoint
    code.py        which Prism grammar highlights which file, and the bundle
    render.py      a validated report -> one self-contained HTML page

The split is simply run-vs-import: bin/ holds the four commands the SKILL tells
you to run, lib/ holds what they import.
"""
