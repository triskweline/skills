#!/usr/bin/env python3
"""Put narrated chapters back into the narration file.

  tour-splice.py [--check] [--root DIR] <patch> <narration> <chapter-file> …

`--check` validates the chapter files and writes nothing — that is how a fork verifies
its own work before returning, when a mistake still costs only its own minute. The patch
is what makes that check worth running: it resolves every spec, so a hunk that does not
exist, a fragment outside its hunk and a quote range no file has are caught here rather
than at the orchestrator's build, in prose the orchestrator never read.

Step G narrates chapters in parallel. A fork may own several chapters, and writes
one file per chapter it owns — never the narration file, which only the orchestrator
writes (Leftovers, while the forks work) and forks only read. So there is no race, but
the chapters then have to go back in, in the right places, without disturbing
`%report`, `%intro`, `%leftovers` or `%closing`.

Doing that by hand is the one unmechanized step in a pipeline that mechanized
everything else, and the failure mode is quiet: a chapter dropped or landing in the
wrong order still *builds*, because a missing `%intro` is only a warning. So this
does it instead.

A chapter file must begin with the chapter directive it replaces, and its title must
match exactly one chapter in the narration. Matching on the title rather than on
position means a fork cannot land its work on the wrong chapter, however the file was
named.

Writes the narration atomically, and prints what it replaced. Then build.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib'))
from difftour import cli, narration   # noqa: E402

CHAPTER = ('%intro', '%chapter', '%leftovers', '%closing')


def _chapters(lines):
    """(index, directive, title) for every chapter-level directive, in order."""
    out, in_code = [], False
    for i, line in enumerate(lines):
        if in_code:
            if line.strip() == '%end':
                in_code = False
            continue
        if line.startswith('%code'):
            in_code = True
            continue
        if line.startswith(CHAPTER):
            head = line.split(None, 1)
            out.append((i, head[0], head[1].strip() if len(head) > 1 else ''))
    return out


# A chapter file is the middle of a document, so parsing it alone fails on rules about
# the whole — "the first directive must be %report". Wrapping it in the smallest legal
# envelope lets a fork check its own work, which is the difference between a format error
# costing the fork a minute and costing the orchestrator a debugging round in a chapter it
# never read.
ENVELOPE = '%report check\n%intro Overview\n%beat b\nPlaceholder.\n'
ENVELOPE_LINES = ENVELOPE.count('\n')      # the fragment's line 1 is line 5 of the whole
WHOLE_DOC = ('%closing', '%intro', '%leftovers')


def _fragment_problems(text, patch=None, root='.'):
    """Problems that are really in this chapter, with the fragment's own line numbers.

    With a patch, every spec is resolved too — which is the point: a fork is expected to
    add %quote and to split its own hunks, so the specs it writes are the only ones that
    can be wrong, and they are exactly what a parse-only check cannot see.
    """
    rep, problems = narration.parse(ENVELOPE + text)
    if patch is not None:
        problems += narration.resolve(rep, patch, root)
    out = []
    for x in problems:
        # Complaints about the envelope, or about parts of a document a fragment does not
        # contain, are not this fork's business.
        if x.line <= ENVELOPE_LINES:
            continue
        if not x.fatal and any(w in x.text for w in WHOLE_DOC):
            continue
        x.line -= ENVELOPE_LINES
        out.append(x)
    return out


def _labels_in(lines):
    """Every @label on a block directive in these lines, in order."""
    out, in_code = [], False
    for line in lines:
        if in_code:
            if line.strip() == '%end':
                in_code = False
            continue
        if line.startswith('%code'):
            in_code = True
            continue
        if line.startswith(('%hunk', '%file')):
            m = narration.LABEL.search(line.split('=', 1)[0])
            if m:
                out.append(m.group(1))
    return out


def main(argv):
    check, root, rest = False, '.', []
    i = 0
    while i < len(argv):
        if argv[i] == '--check':
            check = True
            i += 1
        elif argv[i] == '--root':
            if i + 1 >= len(argv):
                print('tour-splice: --root needs a value', file=sys.stderr)
                return 2
            root = argv[i + 1]
            i += 2
        else:
            rest.append(argv[i])
            i += 1
    if len(rest) < 3:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    src, doc, parts = rest[0], rest[1], rest[2:]
    for path in [src, doc] + parts:
        if not os.path.isfile(path):
            print('tour-splice: no such file: %s' % path, file=sys.stderr)
            return 2
    patch, bad = cli.load_patch(src, 'tour-splice', sys.stderr)
    if bad:
        return bad

    with open(doc, encoding='utf-8') as f:
        lines = f.read().split('\n')

    # Validate every part before placing any of them, so a bad file cannot leave the
    # narration half-updated — and so --check can answer without writing.
    bad = 0
    seen_titles = {}
    for path in parts:
        with open(path, encoding='utf-8') as f:
            text = f.read()
        problems = _fragment_problems(text, patch, root)
        fatal = [x for x in problems
                 if x.fatal and not (x.premature or x.needs_labels)]
        for x in problems:
            if not (x.premature or x.needs_labels):
                print('%s: %s' % (path, x), file=sys.stderr)
        # The title is the splice key, so it is checked here and not only at placement.
        # A fork that improves its chapter's title while narrating would otherwise pass
        # its own --check and fail at the orchestrator's splice, after spending its whole
        # budget — and the label comparison below would be skipped in silence too.
        first = text.lstrip('\n').split('\n', 1)[0]
        head = first.split(None, 1)
        title = head[1].strip() if len(head) > 1 else ''
        here = _chapters(lines)
        hits = [c for c in here if c[2] == title]
        # A fork writes one file per chapter it owns. A file holding two would replace
        # one chapter's span with both, leaving the narration with a duplicated chapter
        # and duplicated labels — and then the *sibling* fork's legitimate file is
        # refused for an ambiguous title, an error pointing at the wrong party, after
        # every fork's budget is spent.
        inside = _chapters(text.split('\n'))
        if len(inside) > 1:
            print('tour-splice: %s holds %d chapters (%s). One file per chapter: this '
                  'would replace one chapter with all of them and duplicate the rest, '
                  'and the next fork\'s file would then be refused for a title that '
                  'suddenly matches twice.'
                  % (path, len(inside), ', '.join(repr(c[2]) for c in inside)),
                  file=sys.stderr)
            bad += 1
        elif not first.startswith(CHAPTER):
            print('tour-splice: %s does not begin with a chapter directive, so there is '
                  'nothing to say which chapter it replaces' % path, file=sys.stderr)
            bad += 1
        elif not hits:
            print('tour-splice: %s is titled %r, which matches no chapter in %s. The '
                  'title is how a chapter file finds its place, so it has to be the one '
                  'the skeleton gave it, verbatim. It has: %s'
                  % (path, title, doc, ', '.join(repr(c[2]) for c in here)),
                  file=sys.stderr)
            bad += 1
        elif len(hits) > 1:
            print('tour-splice: %s has %d chapters titled %r, so %s cannot be placed '
                  'unambiguously' % (doc, len(hits), title, path), file=sys.stderr)
            bad += 1
        elif title in seen_titles:
            # Two forks were given the same chapter. Placing both would silently keep
            # only the last, discarding a fork's whole narration — while Step I is
            # written from both forks' reports, so the wrap-up would describe prose
            # that is not on the page.
            print('tour-splice: %s and %s both claim chapter %r. Only one can be it, '
                  'and splicing both would keep whichever came last and drop the '
                  'other silently. Decide which, or the packing gave one chapter to '
                  'two forks.' % (seen_titles[title], path, title), file=sys.stderr)
            bad += 1
        else:
            # A retyped directive loses its @label, and then every [[…]] a sibling
            # chapter wrote at that block dangles at build time — in prose nobody here
            # will read.
            start = hits[0][0]
            after = [c[0] for c in here if c[0] > start]
            was = _labels_in(lines[start:after[0] if after else len(lines)])
            now = _labels_in(text.split('\n'))
            seen_titles[title] = path
            lost = [l for l in was if l not in now]
            if lost:
                print('tour-splice: %s drops label%s %s that the chapter it replaces '
                      'carried. A reference to a dropped label fails at build, in prose '
                      'written elsewhere. Copy the directive lines rather than retyping '
                      'them — and if you split a labelled hunk, keep its label on one of '
                      'the fragments and leave the others bare.'
                      % (path, '' if len(lost) == 1 else 's',
                         ', '.join('@' + l for l in lost)), file=sys.stderr)
                bad += 1
        if fatal:
            bad += 1
    if bad:
        print('tour-splice: %d file%s %s problems above. Nothing written.'
              % (bad, '' if bad == 1 else 's', 'has' if bad == 1 else 'have'),
              file=sys.stderr)
        return 6
    if check:
        print('tour-splice: %d chapter file%s check out; splice when the rest are in.'
              % (len(parts), '' if len(parts) == 1 else 's'), file=sys.stderr)
        return 0

    spliced = []
    for path in parts:
        with open(path, encoding='utf-8') as f:
            new = f.read().rstrip('\n').split('\n')
        while new and not new[0].strip():
            new.pop(0)
        head = new[0].split(None, 1)
        title = head[1].strip() if len(head) > 1 else ''
        here = _chapters(lines)
        hits = [c for c in here if c[2] == title]
        if len(hits) != 1:
            # The loop above already refused every file whose title does not name
            # exactly one chapter, so reaching here means that check and this one
            # disagree — a bug, not a user error. Say which, rather than misplacing.
            print('tour-splice: %s claims chapter %r, which now matches %d chapters in '
                  '%s. This is a bug in this script; nothing further written.'
                  % (path, title, len(hits), doc), file=sys.stderr)
            return 6

        start = hits[0][0]
        after = [c[0] for c in here if c[0] > start]
        end = after[0] if after else len(lines)
        lines = lines[:start] + new + [''] + lines[end:]
        spliced.append((title, len(new)))

    # One write, atomic, after every part has been placed — a half-spliced narration
    # would be worse than none.
    d = os.path.dirname(os.path.abspath(doc))
    fd, tmp = tempfile.mkstemp(dir=d, prefix='.tour-splice-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        os.replace(tmp, doc)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise

    for title, n in spliced:
        print('spliced %r (%d lines)' % (title, n))

    # Say what is still a skeleton, so a missing fork is visible now rather than as a
    # confusing wall of "no prose" on the next build.
    with open(doc, encoding='utf-8') as f:
        rep, _ = narration.parse(f.read())
    bare = [ch.title for ch in rep.chapters
            if ch.kind == 'chapter' and not ''.join(ch.intro).strip()]
    if bare:
        print('tour-splice: still un-narrated: %s' % ', '.join(bare), file=sys.stderr)
    print('tour-splice: %d chapter%s spliced into %s'
          % (len(spliced), '' if len(spliced) == 1 else 's', doc), file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
