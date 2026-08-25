"""Parse and validate a narration file.

The narration file is the only thing the model writes. It is markdown prose with
directive lines, and it holds no diff bytes: a component names a hunk and the
builder splices it. That is what keeps hunks byte-exact without trusting a
copy-paste, and it is most of the cost of a large report.

Everything here reports *every* problem it finds and writes nothing, because a
narration file for a large change is tens of thousands of tokens and a rewrite
is the single most expensive mistake available. One edit round should fix it.

`resolve()` mutates the report it is given — it expands `path:all` in place — so
it runs once per parse. A command that needs a fresh view re-parses.

An unrecognised directive is an error rather than prose. A mistyped %beat would
otherwise merge two beats silently, and no other check would see it.

Two different things are deliberately not the same here:

  a label  @h17   names one block, forever. It is written into the directive, so
                  it travels with the block when the block moves.
  a code    2.9   is where that block currently sits, computed from position at
                  build time and never written by anyone.

Prose references a label, `[[h17]]`, and the builder renders whatever code that
label resolves to. That is what lets a chapter be reordered while it is being
narrated without invalidating a reference some other chapter already wrote.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

DIRECTIVES = {'report', 'intro', 'chapter', 'leftovers', 'closing', 'blast',
              'beat', 'fold', 'hunk', 'file', 'quote', 'code', 'end', '#'}
BLAST_LEVELS = ('narrow', 'moderate', 'wide')
CHAPTER_KINDS = {'intro', 'chapter', 'leftovers', 'closing'}


@dataclass
class Problem:
    line: int
    text: str
    fatal: bool = True

    def __str__(self):
        return '%s line %d: %s' % ('error' if self.fatal else 'warning', self.line, self.text)

    @property
    def prose_gap(self):
        """Missing prose, which is expected while a skeleton is still a skeleton.

        Defined once, because two commands run before the prose exists and both
        have to agree about which complaints are premature rather than wrong.
        """
        return 'no prose' in self.text or 'introductory paragraph' in self.text


@dataclass
class Component:
    """A code block in the right-hand column."""
    kind: str                       # hunk | file | quote | code
    line: int                       # where it was declared, for error messages
    caption: str = ''
    path: str = ''
    key: str = ''                   # a hunk's @@ +start
    lo: int | None = None
    hi: int | None = None
    body: list = field(default_factory=list)   # %code only
    lang: str = ''
    label: str = ''                 # "h17", written by bin/tour-skeleton.py
    code: str = ''                  # "3.2", assigned by the builder
    hunk: object = None             # resolved patch.Hunk
    fc: object = None               # resolved patch.FileChange
    siblings: list = field(default_factory=list)   # codes of this hunk's other fragments

    @property
    def coded(self):
        """Only real diff content earns a 3.2 code; a quote illustrates, it is not
        part of the change and must never look like a piece of it."""
        return self.kind in ('hunk', 'file')


@dataclass
class Beat:
    subtitle: str
    line: int
    prose: list = field(default_factory=list)      # markdown lines, left column
    fold: bool = False
    items: list = field(default_factory=list)      # Component | ('note', [lines])


@dataclass
class Chapter:
    kind: str                       # intro | chapter | leftovers | closing
    title: str
    line: int
    number: int = 0
    intro: list = field(default_factory=list)
    blast_level: str = ''
    blast: list = field(default_factory=list)
    beats: list = field(default_factory=list)

    @property
    def components(self):
        return [i for b in self.beats for i in b.items if isinstance(i, Component)]


@dataclass
class Report:
    title: str = ''
    chapters: list = field(default_factory=list)
    refs: dict = field(default_factory=dict)    # label -> the code it resolves to

    @property
    def components(self):
        return [c for ch in self.chapters for c in ch.components]


SPEC_FRAG = re.compile(r'^\s*#\s*(\d+)\s*-\s*(\d+)\s*$')
RANGE = re.compile(r'^\s*(\d+)\s*-\s*(\d+)\s*$')
# A label is its own whitespace-delimited token. Anchoring it that way is what keeps
# an @ inside a path — `src/@types/a.ts`, `node_modules/@babel/core`, `logo@2x.png` —
# from being mistaken for one.
LABEL = re.compile(r'(?:(?<=\s)|^)@([A-Za-z][A-Za-z0-9_-]*)(?=\s|$)')
# A reference in prose: [[h17]] on its own, or [prose label](#h17).
REF = re.compile(r'\[\[([A-Za-z][A-Za-z0-9_-]*)\]\]|\]\(#([A-Za-z][A-Za-z0-9_-]*)\)')


def _take_label(spec):
    """Pull an @label out of a spec, and return (spec-without-it, label)."""
    m = LABEL.search(spec)
    if not m:
        return spec.strip(), ''
    return (spec[:m.start()] + spec[m.end():]).strip(), m.group(1)


def _split_caption(rest):
    """`spec = caption` on the first `=`. A caption may then contain `=` freely,
    and no spec ever does."""
    if '=' in rest:
        spec, cap = rest.split('=', 1)
        return spec.strip(), cap.strip()
    return rest.strip(), ''


def _parse_hunk_spec(spec):
    """`path:key` or `path:key #lo-hi` -> (path, key, lo, hi) or None."""
    lo = hi = None
    if '#' in spec:
        base, frag = spec.split('#', 1)
        m = SPEC_FRAG.match('#' + frag)
        if not m:
            return None
        lo, hi = int(m.group(1)), int(m.group(2))
    else:
        base = spec
    base = base.strip()
    if ':' not in base:
        return None
    path, key = base.rsplit(':', 1)
    key = key.strip().lstrip('+')      # tour-hunks.py prints "+233"; accept either
    if not path or not key:
        return None
    return path.strip(), key, lo, hi


def parse(text):
    """Narration text -> (Report, [Problem]). Structure only; hunks are resolved
    against a patch by resolve()."""
    rep = Report()
    problems = []
    chapter = beat = None
    sink = None                 # where loose prose goes right now
    in_code = None              # an open %code component
    seen_report = False

    def err(n, msg, fatal=True):
        problems.append(Problem(n, msg, fatal))

    def prose_target(create=True):
        """Where a line of prose goes right now.

        `create=False` asks without opening a new note, which is what a blank line
        needs: a blank line after a block must not conjure an empty annotation, or
        every beat that ends with a block looks like it has trailing prose.
        """
        if beat is not None:
            if beat.items:
                last = beat.items[-1]
                if isinstance(last, tuple):
                    return last[1]
                if not create:
                    return None
                note = ('note', [])
                beat.items.append(note)
                return note[1]
            return beat.prose
        if chapter is not None:
            return chapter.blast if chapter.blast_level else chapter.intro
        return None

    lines = text.split('\n')
    for i, raw in enumerate(lines, 1):
        line = raw.rstrip('\n')

        if in_code is not None:
            if line.strip() == '%end':
                in_code = None
                continue
            # A structural directive inside a snippet means the %end was forgotten.
            # Say so where the reader can act on it, and carry on parsing structure,
            # rather than swallowing the rest of the report and reporting the damage
            # somewhere else.
            if re.match(r'^%(report|intro|chapter|leftovers|closing|beat|blast|fold|hunk|file|quote|code)\b', line):
                err(i, 'this looks like a forgotten %%end — the snippet opened on line %d '
                       'would otherwise swallow the rest of the report' % in_code.line)
                in_code = None
            else:
                in_code.body.append(line)
                continue

        if line.startswith('%%'):
            t = prose_target()
            if t is None:
                err(i, 'prose before the first chapter')
            else:
                t.append(line[1:])
            continue

        if line.startswith('%'):
            m = re.match(r'^%(\S+)\s*(.*)$', line)
            name = m.group(1) if m else ''
            rest = (m.group(2) if m else '').strip()
            if name not in DIRECTIVES:
                err(i, 'unknown directive %%%s — a typo here would silently merge two '
                       'blocks, so it is refused. For a literal %% at the start of a '
                       'prose line, write %%%%.' % name)
                continue

            if name == '#':
                continue

            if name == 'report':
                if seen_report:
                    err(i, '%report appears twice')
                elif rep.chapters:
                    err(i, '%report must come before the first chapter')
                if not rest:
                    err(i, '%report needs a title')
                rep.title = rest or rep.title
                seen_report = True
                continue

            if name in CHAPTER_KINDS:
                if not seen_report:
                    err(i, 'the first directive must be %report')
                    seen_report = True
                if not rest:
                    err(i, '%%%s needs a title' % name)
                chapter = Chapter(name, rest, i, number=len(rep.chapters) + 1)
                rep.chapters.append(chapter)
                beat = None
                continue

            if chapter is None:
                err(i, '%%%s before any chapter' % name)
                continue

            if name == 'blast':
                if chapter.kind != 'chapter':
                    err(i, '%%blast belongs to a cluster chapter, not to %s' % chapter.kind)
                if beat is not None:
                    err(i, '%blast belongs above the beats, right after the chapter intro')
                if rest not in BLAST_LEVELS:
                    err(i, '%%blast wants one of %s, not %r'
                        % (' | '.join(BLAST_LEVELS), rest))
                if chapter.blast_level:
                    err(i, 'this chapter already has a %blast')
                chapter.blast_level = rest if rest in BLAST_LEVELS else 'moderate'
                continue

            if name == 'beat':
                if not rest:
                    err(i, '%beat needs a subtitle')
                beat = Beat(rest, i)
                chapter.beats.append(beat)
                continue

            if name == 'fold':
                if beat is None:
                    err(i, '%fold belongs inside a beat')
                else:
                    beat.fold = True
                continue

            if name == 'end':
                err(i, '%end without an open %code')
                continue

            # ---- components ----
            if beat is None:
                err(i, '%%%s is outside a beat — a hunk needs a beat to be about' % name)
                continue

            spec, cap = _split_caption(rest)
            spec, label = _take_label(spec)
            if name in ('hunk', 'file', 'quote', 'code') and not cap:
                err(i, '%%%s has no caption. The caption is what tells the reader '
                       'what this block is for here' % name)

            if name == 'hunk':
                parsed = _parse_hunk_spec(spec)
                if not parsed:
                    err(i, 'cannot read %r — want path:+start, or path:+start #lo-hi, '
                           'or path:all' % spec)
                    continue
                path, key, lo, hi = parsed
                if lo is not None and lo > hi:
                    err(i, 'fragment #%d-%d runs backwards' % (lo, hi))
                    continue
                if key == 'all' and label:
                    err(i, 'path:all stands for every hunk of the file, so one label '
                           'cannot name them. Name the one hunk you want to reference.')
                    continue
                if key == 'all' and lo is not None:
                    err(i, 'path:all stands for every hunk of the file, so it cannot '
                           'take a #%d-%d fragment. Name the one hunk instead.' % (lo, hi))
                    continue
                beat.items.append(Component('hunk', i, cap, path, key, lo, hi,
                                            label=label))
            elif name == 'file':
                if not spec:
                    err(i, '%file needs a path')
                    continue
                beat.items.append(Component('file', i, cap, spec, label=label))
            elif name == 'quote':
                if ':' not in spec:
                    err(i, 'cannot read %r — want path:from-to' % spec)
                    continue
                path, rng = spec.rsplit(':', 1)
                m = RANGE.match(rng)
                if not m:
                    err(i, 'cannot read %r — want path:from-to, e.g. src/form.js:512-528'
                        % spec)
                    continue
                beat.items.append(Component('quote', i, cap, path.strip(),
                                            lo=int(m.group(1)), hi=int(m.group(2)),
                                            label=label))
            elif name == 'code':
                comp = Component('code', i, cap, lang=spec.strip(), label=label)
                beat.items.append(comp)
                in_code = comp
            continue

        # ---- prose ----
        if not line.strip():
            t = prose_target(create=False)
            if t is not None and t and t[-1].strip():
                t.append('')
            continue
        if line.lstrip().startswith('#') and not line.lstrip().startswith('#!'):
            err(i, 'a markdown heading in prose. Chapters are %chapter and beats are '
                   '%beat, so the report keeps one heading hierarchy')
            continue
        t = prose_target()
        if t is None:
            err(i, 'prose before the first chapter')
            continue
        t.append(line)

    if in_code is not None:
        err(in_code.line, '%code was never closed by a %end line')
    if not seen_report:
        err(1, 'no %report line — the report has no title', fatal=False)

    problems.extend(_check_shape(rep))
    return rep, problems


def _check_shape(rep):
    """Checks about the document's shape.

    These are warnings, not errors. The SKILL tells you to append one chapter and
    build, so a document is *supposed* to be missing its last chapter most of the
    time it is compiled; making that fatal would make the advice unfollowable.
    They still have to be clear by the final build.
    """
    out = []

    def warn(line, msg):
        out.append(Problem(line, msg, fatal=False))

    if not rep.chapters:
        out.append(Problem(1, 'no chapters'))
        return out
    kinds = [c.kind for c in rep.chapters]
    if kinds[0] != 'intro':
        warn(rep.chapters[0].line, 'the first chapter should be %intro')
    if kinds[-1] != 'closing':
        warn(rep.chapters[-1].line, 'no %closing chapter yet')
    for k in ('intro', 'closing', 'leftovers'):
        if kinds.count(k) > 1:
            warn(1, 'more than one %%%s chapter' % k)
    if 'leftovers' in kinds and kinds.index('leftovers') != len(kinds) - 2:
        warn(rep.chapters[kinds.index('leftovers')].line,
             '%leftovers belongs immediately before %closing')
    for ch in rep.chapters:
        if ch.kind != 'chapter':
            continue
        if not ch.blast_level:
            warn(ch.line, 'this cluster chapter has no %blast judgement')
        if not ''.join(ch.intro).strip():
            warn(ch.line, 'a cluster chapter opens with an introductory paragraph, '
                          'before its beats')
    for ch in rep.chapters:
        for b in ch.beats:
            if (b.items and isinstance(b.items[-1], tuple)
                    and ''.join(b.items[-1][1]).strip()):
                warn(b.line, 'the prose after the last block in this beat has nothing '
                             'to introduce. Prose beside the code always introduces the '
                             'block below it, so move this into the beat\'s narration '
                             'or give it the block it is about')
            # Fatal: a beat with no prose is the one defect the two-column layout
            # cannot survive. The prose is the only thing the reader cannot get
            # from the diff, and an empty left column beside code is the report
            # failing at its whole purpose.
            if not ''.join(b.prose).strip():
                out.append(Problem(b.line, 'this beat has no prose. The prose is the only '
                                           'thing the reader cannot get from the diff'))
    return out


# ---------------------------------------------------------------- resolution

import hashlib
import os


def _digest(*parts):
    h = hashlib.sha1()
    for p in parts:
        h.update(p.encode('utf-8', 'replace'))
        h.update(b'\x00')
    return h.hexdigest()[:8]


def resolve(rep, patch, root='.'):
    """Bind every component to the patch, assign codes, cross-link fragments.

    Returns [Problem]. Mutates the report.
    """
    problems = []

    def err(n, msg, fatal=True):
        problems.append(Problem(n, msg, fatal))

    # `path:all` is one directive standing for every hunk of a file, so expand it
    # before anything counts or numbers components.
    for ch in rep.chapters:
        for beat in ch.beats:
            out = []
            for item in beat.items:
                if isinstance(item, Component) and item.kind == 'hunk' and item.key == 'all':
                    fc = patch.file(item.path)
                    if fc is None:
                        err(item.line, 'no file %r in the diff' % item.path)
                        continue
                    if not fc.hunks:
                        err(item.line, '%r has no hunks — it is a %s, so use %%file'
                            % (item.path, 'binary change' if fc.binary else fc.kind))
                        continue
                    for h in fc.hunks:
                        out.append(Component('hunk', item.line, item.caption,
                                             item.path, h.key))
                else:
                    out.append(item)
            beat.items = out

    for ch in rep.chapters:
        n = 0
        for comp in ch.components:
            if comp.kind == 'hunk':
                _resolve_hunk(comp, patch, err)
            elif comp.kind == 'file':
                _resolve_file(comp, patch, err)
            elif comp.kind == 'quote':
                _resolve_quote(comp, root, err)
            if comp.coded:
                n += 1
                comp.code = '%d.%d' % (ch.number, n)

    # Fragments of one hunk cross-link, so a fragment can never be mistaken for the
    # whole. The builder knows all of them; the model never has to keep track.
    groups = {}
    for comp in rep.components:
        if comp.kind == 'hunk' and comp.hunk is not None:
            groups.setdefault((comp.path, comp.key), []).append(comp)
    for (path, key), comps in groups.items():
        if len(comps) > 1:
            for c in comps:
                c.siblings = [o.code for o in comps if o is not c and o.code]
        # An overlap is legitimate when a chapter deliberately re-shows lines another
        # chapter owns, and an off-by-one when it is not. Only the author knows which,
        # so warn. Two whole copies of one hunk overlap too — splitting is supposed to
        # have replaced re-showing, so that is worth saying out loud.
        for i, a in enumerate(comps):
            for b in comps[i + 1:]:
                alo, ahi = a.hunk.slice(a.lo, a.hi)
                blo, bhi = b.hunk.slice(b.lo, b.hi)
                if alo <= bhi and blo <= ahi:
                    err(b.line, 'fragment #%d-%d overlaps #%d-%d of the same hunk '
                                '(%s). Deliberate re-show, or an off-by-one?'
                        % (blo, bhi, alo, ahi, path), fatal=False)

    for comp in rep.components:
        comp.key_hash = _component_key(comp)

    # A label names a block forever; a code says where it currently sits. Prose
    # references the label, so reordering a chapter cannot invalidate a reference
    # another chapter already wrote.
    seen = {}
    for comp in rep.components:
        if not comp.label:
            continue
        if re.match(r'^ch\d+$', comp.label):
            err(comp.line, '@%s cannot be a label: [[%s]] already means chapter %s'
                % (comp.label, comp.label, comp.label[2:]))
            continue
        if comp.label in seen:
            err(comp.line, 'label @%s is already used on line %d. A label names one '
                           'block, so two blocks cannot share one'
                % (comp.label, seen[comp.label]))
            continue
        seen[comp.label] = comp.line
        if comp.code:
            rep.refs[comp.label] = comp.code

    chapters = {'ch%d' % ch.number for ch in rep.chapters}
    # The title is prose too, and a reference in it would otherwise go unchecked.
    everywhere = [(rep.title, 1)]
    for ch in rep.chapters:
        everywhere.extend(_prose_blocks(ch))

    for text, line in everywhere:
        for bad in re.findall(r'\]\(#(\d+\.\d+)\)', text):
            err(line, 'a link points at #%s. A code says where a block sits now, so it '
                      'breaks as soon as anything is reordered — reference the block by '
                      'its @label instead' % bad)
        # `2.9` and [[2.9]] are the same mistake in different clothes: the first
        # renders as a number that quietly stops matching, the second as literal
        # brackets.
        for a, b in re.findall(r'`(\d+\.\d+)`|\[\[(\d+\.\d+)\]\]', text):
            err(line, 'prose says %s, which is a position, not a name. It stops matching '
                      'the moment anything is reordered — write [[<label>]] and let the '
                      'builder print the code' % (a or b), fatal=False)
        for a, b in REF.findall(text):
            name = a or b
            if name in rep.refs or name in chapters:
                continue
            if name in seen:
                err(line, '[[%s]] names a block that has no code — a %%quote or %%code '
                          'illustrates, so nothing can point at it' % name)
            else:
                err(line, '[[%s]] names nothing. Labels come from bin/tour-skeleton.py; '
                          'run it and use the names it prints' % name)
    return problems


def _prose_blocks(ch):
    """Every run of prose in a chapter, with a line to blame."""
    yield ' '.join(ch.intro), ch.line
    yield ' '.join(ch.blast), ch.line
    for b in ch.beats:
        yield b.subtitle + ' ' + ' '.join(b.prose), b.line
        for item in b.items:
            if isinstance(item, tuple):
                yield ' '.join(item[1]), b.line
            else:
                yield item.caption, item.line


def _resolve_hunk(comp, patch, err):
    fc = patch.file(comp.path)
    if fc is None:
        near = [f.path for f in patch.files if comp.path.rsplit('/', 1)[-1] in f.path]
        hint = ('. Did you mean %s?' % near[0]) if near else ''
        err(comp.line, 'no file %r in the diff%s' % (comp.path, hint))
        return
    if fc.binary or not fc.hunks:
        err(comp.line, '%r has no diff body — use %%file' % comp.path)
        return
    hunk = patch.hunk(comp.path, comp.key)
    if hunk is None:
        err(comp.line, 'no hunk at +%s in %s. Its hunks start at %s (bin/tour-hunks.py '
                       'lists them)' % (comp.key, comp.path, ', '.join(fc.keys)))
        return
    comp.hunk, comp.fc = hunk, fc
    n = len(hunk.lines)
    if comp.lo is not None:
        if comp.lo < 1 or comp.hi > n:
            err(comp.line, 'fragment #%d-%d is outside this hunk, which has %d body lines'
                % (comp.lo, comp.hi, n))
            return
        if not any(l.changed for l in hunk.body(comp.lo, comp.hi)):
            err(comp.line, 'fragment #%d-%d is all context and changes nothing. To show '
                           'context, use %%quote' % (comp.lo, comp.hi))


def _resolve_file(comp, patch, err):
    fc = patch.file(comp.path)
    if fc is None:
        err(comp.line, 'no file %r in the diff' % comp.path)
        return
    if fc.hunks:
        err(comp.line, '%r has %d hunks — %%file is for a change with no diff body '
                       '(binary, pure rename, mode change). Use %%hunk.'
            % (comp.path, len(fc.hunks)))
        return
    comp.fc = fc


def _resolve_quote(comp, root, err):
    """A quote is read from the checkout, never retyped by the model. That closes the
    last place where code in the report was not mechanically exact."""
    path = os.path.join(root, comp.path)
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            all_lines = f.read().split('\n')
    except OSError as e:
        err(comp.line, 'cannot read %s: %s' % (comp.path, e.strerror or e))
        return
    if comp.lo < 1 or comp.hi > len(all_lines):
        err(comp.line, '%s has %d lines, so %d-%d is out of range'
            % (comp.path, len(all_lines), comp.lo, comp.hi))
        return
    comp.body = all_lines[comp.lo - 1:comp.hi]


def _component_key(comp):
    """Identity for viewed state: the component's own content, not its 3.2 code, so
    reordering chapters or rewriting narration keeps the reader's marks."""
    if comp.kind == 'hunk' and comp.hunk is not None:
        return _digest(comp.path, *[l.raw() for l in comp.hunk.body(comp.lo, comp.hi)])
    if comp.kind == 'file' and comp.fc is not None:
        return _digest(comp.path, comp.fc.kind, 'binary' if comp.fc.binary else '')
    return _digest(comp.kind, comp.path, str(comp.lo), str(comp.hi), *comp.body)


# ------------------------------------------------------------------ coverage

def coverage(rep, patch):
    """What the narration does not show. Every changed line, plus every file-level
    event a diff can carry without a body, has to appear somewhere: a reader cannot
    be responsible for code they were never shown.

    Returns (shown, total, [gap]) where a gap is
        (path, key, lo, hi, adjacent_code_or_None)
    for a hunk, or (path, None, None, None, None) for a bodyless change.
    """
    covered = {}
    files_seen = set()
    for comp in rep.components:
        if comp.kind == 'hunk' and comp.hunk is not None:
            lo, hi = comp.hunk.slice(comp.lo, comp.hi)
            covered.setdefault((comp.path, comp.key), []).append((lo, hi, comp.code))
        elif comp.kind == 'file' and comp.fc is not None:
            files_seen.add(comp.path)

    shown = total = 0
    gaps = []
    for fc in patch.files:
        if not fc.hunks:
            total += 1
            if fc.path in files_seen:
                shown += 1
            else:
                gaps.append((fc.path, None, None, None, None))
            continue
        for hunk in fc.hunks:
            ranges = covered.get((fc.path, hunk.key), [])
            changed = hunk.changed_offsets
            total += len(changed)
            hit = {o for o in changed for lo, hi, _ in ranges if lo <= o <= hi}
            shown += len(hit)
            missing = [o for o in changed if o not in hit]
            if not missing:
                continue
            # Group the misses into runs, breaking a run wherever a *shown* changed
            # line sits between two misses — that is a real boundary, not a gap.
            # Both lists are sorted, so one walk with a cursor does it; rescanning
            # `changed` per miss costs seconds on a lockfile-sized hunk, and coverage
            # runs on every build.
            runs, run, ci = [], [missing[0]], 0
            for o in missing[1:]:
                prev = run[-1]
                while ci < len(changed) and changed[ci] <= prev:
                    ci += 1
                if ci < len(changed) and changed[ci] < o and changed[ci] in hit:
                    runs.append(run)
                    run = [o]
                else:
                    run.append(o)
            runs.append(run)
            for r in runs:
                lo, hi = r[0], r[-1]
                near = None
                for rlo, rhi, code in ranges:
                    if code and (abs(rhi - lo) <= 4 or abs(rlo - hi) <= 4):
                        near = code
                        break
                gaps.append((fc.path, hunk.key, lo, hi, near))
    return shown, total, gaps
