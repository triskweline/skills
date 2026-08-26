#!/usr/bin/env python3
"""Tests for everything between the narration file and the HTML.

    python3 tests/test_difftour.py

Standard library only, like the code under test. Clustering and narration are
judgement and are not testable here; everything after them is a pure function of
two files on disk, which is the seam these tests sit on:

    patch + narration  ->  parse  ->  AST  ->  render  ->  HTML
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib'))
from difftour import code, narration, patch, prose, render   # noqa: E402


def tour(*lines):
    """A minimal well-formed narration file, with `lines` spliced into a cluster."""
    head = ['%report T', '%intro Overview', '%beat What it does', 'Prose.',
            '%chapter The cluster', 'An intro paragraph.', '%blast narrow', 'Evidence.']
    tail = ['%closing Wrap-up', '%beat What to check', 'Prose.']
    return '\n'.join(head + list(lines) + tail)


def problems(text, p, root='.'):
    rep, probs = narration.parse(text)
    probs += narration.resolve(rep, p, root)
    return rep, [str(x) for x in probs if x.fatal], [str(x) for x in probs if not x.fatal]


# --------------------------------------------------------------------- patch.py

SIMPLE = '''diff --git a/src/deep/a.js b/src/deep/a.js
index 111..222 100644
--- a/src/deep/a.js
+++ b/src/deep/a.js
@@ -10,6 +10,7 @@ function outer() {
 keep one
 keep two
-gone
+added one
+added two
 keep three
 keep four
'''


class TestPatch(unittest.TestCase):
    def test_paths_keep_every_segment(self):
        p = patch.parse(SIMPLE)
        self.assertEqual([f.path for f in p.files], ['src/deep/a.js'])

    def test_hunk_key_and_body(self):
        h = patch.parse(SIMPLE).hunks[0]
        self.assertEqual(h.key, '10')
        self.assertEqual(len(h.lines), 7)
        self.assertEqual(h.changed_offsets, [3, 4, 5])
        self.assertEqual(h.heading, 'function outer() {')

    def test_line_numbers(self):
        h = patch.parse(SIMPLE).hunks[0]
        old = [(l.kind, l.old) for l in h.lines]
        new = [(l.kind, l.new) for l in h.lines]
        self.assertEqual(old, [(' ', 10), (' ', 11), ('-', 12), ('+', None),
                               ('+', None), (' ', 13), (' ', 14)])
        self.assertEqual(new, [(' ', 10), (' ', 11), ('-', None), ('+', 12),
                               ('+', 13), (' ', 14), (' ', 15)])

    def test_deletion_gets_the_position_it_sits_before(self):
        h = patch.parse(SIMPLE).hunks[0]
        self.assertEqual(h.lines[2].new_pos, 12)
        self.assertEqual(h.start_line(3, 3), 12)

    def test_fragment_slicing_and_wholeness(self):
        h = patch.parse(SIMPLE).hunks[0]
        self.assertEqual([l.text for l in h.body(3, 4)], ['gone', 'added one'])
        self.assertTrue(h.is_whole())
        self.assertFalse(h.is_whole(3, 4))
        self.assertEqual(h.slice(0, 999), (1, 7))       # clamped

    def test_hunk_header_without_counts(self):
        p = patch.parse('diff --git a/a b/a\n--- a/a\n+++ b/a\n@@ -1 +1 @@\n-x\n+y\n')
        h = p.hunks[0]
        self.assertEqual((h.old_count, h.new_count), (1, 1))
        self.assertEqual(h.changed_offsets, [1, 2])

    def test_added_deleted_renamed_binary_and_mode(self):
        p = patch.parse(
            'diff --git a/new.js b/new.js\nnew file mode 100644\n--- /dev/null\n'
            '+++ b/new.js\n@@ -0,0 +1,1 @@\n+hello\n'
            'diff --git a/gone.js b/gone.js\ndeleted file mode 100644\n--- a/gone.js\n'
            '+++ /dev/null\n@@ -1,1 +0,0 @@\n-bye\n'
            'diff --git a/old/n.js b/new/n.js\nsimilarity index 100%\n'
            'rename from old/n.js\nrename to new/n.js\n'
            'diff --git a/l.png b/l.png\nindex 1..2 100644\n'
            'Binary files a/l.png and b/l.png differ\n'
            'diff --git a/bin/run b/bin/run\nold mode 100644\nnew mode 100755\n')
        got = [(f.path, f.kind, f.binary, f.old_path, len(f.hunks)) for f in p.files]
        self.assertEqual(got, [
            ('new.js', 'added', False, None, 1),
            ('gone.js', 'deleted', False, None, 1),
            ('new/n.js', 'moved', False, 'old/n.js', 0),
            ('l.png', 'changed', True, None, 0),
            ('bin/run', 'changed', False, None, 0),
        ])

    def test_a_mode_change_survives_alongside_content_hunks(self):
        # A script gaining +x while being edited: invisible unless the mode is kept.
        p = patch.parse('diff --git a/bin/run b/bin/run\nold mode 100644\n'
                        'new mode 100755\n--- a/bin/run\n+++ b/bin/run\n'
                        '@@ -1,1 +1,2 @@\n keep\n+added\n')
        f = p.files[0]
        self.assertEqual(f.mode, ('100644', '100755'))
        self.assertEqual(len(f.hunks), 1)

    def test_a_file_with_no_mode_change_has_no_mode(self):
        self.assertIsNone(patch.parse(SIMPLE).files[0].mode)

    def test_a_no_prefix_patch_keeps_every_path_segment(self):
        # git diff --no-prefix, or a patch from someone with diff.noprefix set.
        p = patch.parse('diff --git src/deep/a.js src/deep/a.js\n'
                        '--- src/deep/a.js\n+++ src/deep/a.js\n'
                        '@@ -1,1 +1,2 @@\n keep\n+added\n')
        self.assertEqual([f.path for f in p.files], ['src/deep/a.js'])

    def test_mnemonic_prefixes_are_stripped_like_a_and_b(self):
        p = patch.parse('diff --git i/src/a.js w/src/a.js\n--- i/src/a.js\n'
                        '+++ w/src/a.js\n@@ -1,1 +1,2 @@\n keep\n+added\n')
        self.assertEqual([f.path for f in p.files], ['src/a.js'])

    def test_a_directory_actually_named_a_is_not_mistaken_for_a_prefix(self):
        p = patch.parse('diff --git a/a/b.js b/a/b.js\n--- a/a/b.js\n+++ b/a/b.js\n'
                        '@@ -1,1 +1,2 @@\n keep\n+added\n')
        self.assertEqual([f.path for f in p.files], ['a/b.js'])

    def test_only_a_newline_ends_a_line(self):
        # splitlines() also breaks on U+2028, form feed and U+0085, which silently
        # truncates a diff line. Byte-exactness is the whole promise.
        for ch in (' ', '\x0c', '\x85', ' '):
            p = patch.parse('diff --git a/a.js b/a.js\n--- a/a.js\n+++ b/a.js\n'
                            '@@ -1,1 +1,1 @@\n-old\n+let s = "a%sb"\n' % ch)
            self.assertEqual(len(p.hunks[0].lines), 2)
            self.assertEqual(p.hunks[0].lines[1].text, 'let s = "a%sb"' % ch)

    def test_no_newline_marker_attaches_to_the_line_above(self):
        p = patch.parse('diff --git a/a b/a\n--- a/a\n+++ b/a\n@@ -1,1 +1,1 @@\n'
                        '-old\n\\ No newline at end of file\n+new\n')
        self.assertEqual(len(p.hunks[0].lines), 2)
        self.assertTrue(p.hunks[0].lines[0].no_newline)

    def test_combined_diff_does_not_pollute_the_previous_file(self):
        p = patch.parse(SIMPLE +
                        'diff --cc merged.js\nindex 1,2..3\n--- a/merged.js\n'
                        '+++ b/merged.js\n@@@ -1,2 -1,2 +1,3 @@@\n  ctx\n++both\n')
        self.assertEqual([f.path for f in p.files], ['src/deep/a.js'])
        self.assertEqual(len(p.hunks[0].lines), 7)

    def test_quoted_non_ascii_path(self):
        p = patch.parse('diff --git "a/s\\303\\244ge.js" "b/s\\303\\244ge.js"\n'
                        '--- "a/s\\303\\244ge.js"\n+++ "b/s\\303\\244ge.js"\n'
                        '@@ -1,1 +1,1 @@\n-a\n+b\n')
        self.assertEqual(p.files[0].path, 'säge.js')

    def test_stats(self):
        self.assertEqual(patch.parse(SIMPLE).stats(),
                         dict(files=1, added=2, removed=1, hunks=1, binaries=0))


# ---------------------------------------------------------------------- code.py

class TestBodySizeEstimate(unittest.TestCase):
    """The KB figure decides how wide a --body read can be before it truncates.

    Nothing pinned a number, so an arithmetic slip understated every read by two bytes
    a line — in the direction that walks into the truncation it exists to prevent.
    """

    def test_the_estimate_matches_what_body_actually_prints(self):
        p = patch.parse(SIMPLE)
        h = p.files[0].hunks[0]
        # Reproduce tour-hunks.py's own line format, exactly.
        printed = ''.join('%5d %s%s\n' % (i, l.kind, l.text)
                          for i, l in enumerate(h.lines, 1))
        self.assertEqual(len(printed) + 80, h.bytes_of_body())


class TestLanguages(unittest.TestCase):
    def lang(self, path, lines=()):
        fc = patch.FileChange(path=path)
        if lines:
            h = patch.Hunk(fc, 1, 1, 1, 1, '')
            h.lines = [patch.Line('+', t, None, i, i) for i, t in enumerate(lines, 1)]
            fc.hunks.append(h)
        return code.language_of(fc)

    def test_by_suffix_and_alias(self):
        self.assertEqual(self.lang('a/b.js'), 'javascript')
        self.assertEqual(self.lang('a/b.yml'), 'yaml')
        self.assertEqual(self.lang('a/schema.sql.erb'), 'erb')

    def test_by_name_and_shebang(self):
        self.assertEqual(self.lang('Dockerfile'), 'docker')
        self.assertEqual(self.lang('bin/run', ['#!/usr/bin/env node', 'x']), 'javascript')
        self.assertEqual(self.lang('bin/run', ['#!/bin/bash']), 'bash')

    def test_unknown_is_none_not_a_guess(self):
        self.assertIsNone(self.lang('a/b.xyz'))
        self.assertIsNone(self.lang('.gitignore'))

    def test_the_bundle_is_complete_ordered_and_manual(self):
        js, missing = code.bundle()
        self.assertEqual(missing, [])
        self.assertIn('manual = true', js)
        self.assertGreater(len(js), 50000)
        # GRAMMARS is a hand-kept topological order of Prism's require graph, so a
        # grammar that extends another has to come after it. These are the pairs that
        # matter; a reordering that breaks one of them fails silently in a browser.
        for dep, lang in [('clike', 'javascript'), ('clike', 'ruby'), ('clike', 'java'),
                          ('clike', 'c'), ('c', 'cpp'), ('javascript', 'typescript'),
                          ('javascript', 'coffeescript'), ('markup', 'markdown'),
                          ('markup', 'markup-templating'), ('markup-templating', 'php'),
                          ('markup-templating', 'erb'), ('ruby', 'erb'),
                          ('ruby', 'haml'), ('css', 'scss'), ('css', 'less'),
                          ('java', 'scala'), ('jsx', 'tsx'), ('typescript', 'tsx'),
                          ('markup', 'jsx'), ('javascript', 'jsx')]:
            self.assertLess(code.GRAMMARS.index(dep), code.GRAMMARS.index(lang),
                            '%s must load before %s' % (dep, lang))

    def test_every_mapped_language_is_vendored(self):
        for lang in set(code.BY_SUFFIX.values()) | set(code.BY_NAME.values()):
            self.assertIn(lang, code.GRAMMARS, lang)


# --------------------------------------------------------------------- prose.py

class TestProse(unittest.TestCase):
    def test_escaping_is_total(self):
        self.assertEqual(prose.esc('a & b < c > d "q"'),
                         'a &amp; b &lt; c &gt; d &quot;q&quot;')
        self.assertEqual(prose.inline('`</script>`'), '<code>&lt;/script&gt;</code>')

    def test_inline_marks(self):
        self.assertEqual(prose.inline('**b** and *i* and `c`'),
                         '<strong>b</strong> and <em>i</em> and <code>c</code>')
        self.assertEqual(prose.inline('2*3*4'), '2*3*4')
        self.assertEqual(prose.inline('**bold with `code`**'),
                         '<strong>bold with <code>code</code></strong>')

    def test_links_are_scheme_filtered(self):
        self.assertEqual(prose.inline('[a](#3.2)'), '<a href="#3.2">a</a>')
        self.assertEqual(prose.inline('[a](https://x)'), '<a href="https://x">a</a>')
        self.assertNotIn('<a', prose.inline('[a](javascript:alert1)'))

    def test_paragraphs_and_lists(self):
        self.assertEqual(prose.render(['one', 'two', '', 'three']),
                         '<p>one two</p>\n<p>three</p>')
        self.assertEqual(prose.render(['- a', '  wrapped', '- b']),
                         '<ul><li>a wrapped</li><li>b</li></ul>')
        self.assertEqual(prose.render(['1. a', '2. b']),
                         '<ol><li>a</li><li>b</li></ol>')

    def test_an_ordered_list_keeps_the_number_it_starts_at(self):
        # The overview numbers its chapter list from 2. Renumbering from 1 silently
        # contradicts the sidebar and every heading.
        self.assertEqual(prose.render(['2. two', '3. three']),
                         '<ol start="2"><li>two</li><li>three</li></ol>')
        self.assertEqual(prose.render(['1. one']), '<ol><li>one</li></ol>')

    def test_a_list_switching_kind_starts_a_new_list(self):
        self.assertEqual(prose.render(['- a', '1. b']),
                         '<ul><li>a</li></ul>\n<ol><li>b</li></ol>')


# ----------------------------------------------------------------- narration.py

class TestNarrationStructure(unittest.TestCase):
    def setUp(self):
        self.p = patch.parse(SIMPLE)

    def test_a_well_formed_file_has_no_problems(self):
        rep, fatal, warn = problems(tour(
            '%beat A beat', 'Prose.', '%hunk src/deep/a.js:10 = the whole hunk'), self.p)
        self.assertEqual((fatal, warn), ([], []))
        self.assertEqual([c.kind for c in rep.chapters],
                         ['intro', 'chapter', 'closing'])
        self.assertEqual(rep.title, 'T')

    def test_codes_come_from_position(self):
        rep, _, _ = problems(tour(
            '%beat A', 'P.', '%hunk src/deep/a.js:10 #3-3 = one',
            '%beat B', 'P.', '%hunk src/deep/a.js:10 #4-5 = two'), self.p)
        self.assertEqual([c.code for c in rep.chapters[1].components], ['2.1', '2.2'])

    def test_a_quote_earns_no_code(self):
        rep, _, _ = problems(tour(
            '%beat A', 'P.', '%code sh = a snippet', 'ls', '%end',
            '%hunk src/deep/a.js:10 = real'), self.p)
        self.assertEqual([c.code for c in rep.chapters[1].components], ['', '2.1'])

    def test_indented_prose_belongs_to_the_block_above_it(self):
        rep, fatal, _ = problems(tour(
            '%beat A', 'Beat prose.',
            '%hunk src/deep/a.js:10 #3-3 @h1 = x', '  About h1.',
            '%hunk src/deep/a.js:10 #4-5 @h2 = y', '  About h2.'), self.p)
        self.assertEqual(fatal, [])
        beat = rep.chapters[1].beats[0]
        self.assertEqual(beat.prose, ['Beat prose.'])
        self.assertEqual([(c.label, c.lead) for c in beat.items],
                         [('h1', ['About h1.']), ('h2', ['About h2.'])])

    def test_a_blocks_prose_travels_with_it_when_it_moves(self):
        # The whole reason it lives inside the block: swapping two blocks as units
        # cannot leave their prose behind describing the wrong diff.
        a = ['%hunk src/deep/a.js:10 #3-3 @h1 = first', '  About the first.']
        b = ['%hunk src/deep/a.js:10 #4-5 @h2 = second', '  About the second.']
        head = ['%beat A', 'Narration.']
        one = problems(tour(*(head + a + b)), self.p)[0]
        two = problems(tour(*(head + b + a)), self.p)[0]
        self.assertEqual([(c.code, c.lead[0]) for c in one.chapters[1].components],
                         [('2.1', 'About the first.'), ('2.2', 'About the second.')])
        self.assertEqual([(c.code, c.lead[0]) for c in two.chapters[1].components],
                         [('2.1', 'About the second.'), ('2.2', 'About the first.')])

    def test_a_blocks_prose_may_run_to_several_paragraphs(self):
        rep, fatal, _ = problems(tour(
            '%beat A', 'Narration.', '%hunk src/deep/a.js:10 @h1 = x',
            '  One paragraph.', '', '  And another.'), self.p)
        self.assertEqual(fatal, [])
        self.assertEqual(rep.components[0].lead, ['One paragraph.', '', 'And another.'])

    def test_all_expands_to_one_component_per_hunk(self):
        p = patch.parse(SIMPLE + 'diff --git a/src/deep/a.js b/src/deep/a.js\n'
                        '--- a/src/deep/a.js\n+++ b/src/deep/a.js\n'
                        '@@ -40,1 +41,1 @@\n-x\n+y\n')
        rep, fatal, _ = problems(tour('%beat A', 'P.',
                                      '%hunk src/deep/a.js:all = every hunk'), p)
        self.assertEqual(fatal, [])
        self.assertEqual([(c.key, c.code) for c in rep.chapters[1].components],
                         [('10', '2.1'), ('41', '2.2')])

    def test_fragments_of_one_hunk_cross_link(self):
        rep, _, _ = problems(tour(
            '%beat A', 'P.', '%hunk src/deep/a.js:10 #3-3 = one',
            '%beat B', 'P.', '%hunk src/deep/a.js:10 #4-5 = two'), self.p)
        a, b = rep.chapters[1].components
        self.assertEqual((a.siblings, b.siblings), (['2.2'], ['2.1']))

    def test_a_label_survives_a_reorder_but_its_code_does_not(self):
        before = problems(tour(
            '%beat A', 'P.', '%hunk src/deep/a.js:10 #3-3 @h1 = first',
            '%hunk src/deep/a.js:10 #4-5 @h2 = second'), self.p)[0]
        after = problems(tour(
            '%beat A', 'P.', '%hunk src/deep/a.js:10 #4-5 @h2 = second',
            '%hunk src/deep/a.js:10 #3-3 @h1 = first'), self.p)[0]
        self.assertEqual(before.refs, {'h1': '2.1', 'h2': '2.2'})
        self.assertEqual(after.refs, {'h2': '2.1', 'h1': '2.2'})

    def test_a_key_is_content_not_position(self):
        one = problems(tour('%beat A', 'P.', '%hunk src/deep/a.js:10 = x'), self.p)[0]
        two = problems(tour('%beat Z', 'Q.', '%beat A', 'P.',
                            '%hunk src/deep/a.js:10 = renamed caption'), self.p)[0]
        self.assertEqual(one.components[0].key_hash, two.components[0].key_hash)

    def test_percent_escape_and_comments(self):
        rep, fatal, _ = problems(tour('%beat A', '%%s is a literal percent.',
                                      '%# a comment',
                                      '%hunk src/deep/a.js:10 = x'), self.p)
        self.assertEqual(fatal, [])
        self.assertEqual(rep.chapters[1].beats[0].prose, ['%s is a literal percent.'])

    def test_a_caption_may_contain_an_equals_sign(self):
        rep, fatal, _ = problems(tour('%beat A', 'P.',
                                      '%hunk src/deep/a.js:10 = why a = b now'), self.p)
        self.assertEqual(fatal, [])
        self.assertEqual(rep.components[0].caption, 'why a = b now')


class TestNarrationRejects(unittest.TestCase):
    def setUp(self):
        self.p = patch.parse(SIMPLE)

    def assertRejects(self, needle, *lines):
        _, fatal, _ = problems(tour(*lines), self.p)
        self.assertTrue(any(needle in f for f in fatal),
                        'expected %r among %r' % (needle, fatal))

    def test_a_code_fence_in_prose_is_refused(self):
        self.assertRejects('a code fence in prose', '%beat A', 'Prose:', '```js')

    def test_indented_prose_cannot_attach_to_an_all_directive(self):
        p = patch.parse(SIMPLE + 'diff --git a/src/deep/a.js b/src/deep/a.js\n'
                        '--- a/src/deep/a.js\n+++ b/src/deep/a.js\n'
                        '@@ -40,1 +41,1 @@\n-x\n+y\n')
        _, fatal, _ = problems(tour('%beat A', 'Narration.',
                                    '%hunk src/deep/a.js:all = the sweep',
                                    '  This would be silently dropped.'), p)
        self.assertTrue(any('cannot attach to' in f for f in fatal), fatal)

    def test_a_reference_to_no_label(self):
        self.assertRejects('[[hzz]] names nothing',
                           '%beat A', 'See [[hzz]].', '%hunk src/deep/a.js:10 = x')

    def test_two_blocks_cannot_share_a_label(self):
        self.assertRejects('already used',
                           '%beat A', 'P.', '%hunk src/deep/a.js:10 #3-3 @h1 = a',
                           '%hunk src/deep/a.js:10 #4-5 @h1 = b')

    def test_a_quote_cannot_be_referenced(self):
        """Refused at the label now, which says why rather than only that."""
        here = os.path.dirname(os.path.abspath(__file__))
        _, fatal, _ = problems(tour(
            '%beat A', 'See [[q1]].',
            '%quote test_difftour.py:1-2 @q1 = the top',
            '%hunk src/deep/a.js:10 = x'), self.p, root=here)
        self.assertTrue(any('cannot take a label' in f for f in fatal), fatal)
        self.assertTrue(any('[[q1]] names nothing' in f for f in fatal), fatal)

    def test_a_link_to_a_positional_code_is_refused(self):
        self.assertRejects('reference the block by its @label',
                           '%beat A', 'See [it](#2.1).', '%hunk src/deep/a.js:10 = x')

    def test_an_at_sign_in_a_path_is_part_of_the_path(self):
        # Scoped packages and @types directories are everywhere; an @ with no space
        # before it is never a label.
        p = patch.parse(
            'diff --git a/src/@types/a.ts b/src/@types/a.ts\n--- a/src/@types/a.ts\n'
            '+++ b/src/@types/a.ts\n@@ -1,1 +1,2 @@\n keep\n+added\n'
            'diff --git a/x/logo@2x.png b/x/logo@2x.png\n'
            'Binary files a/x/logo@2x.png and b/x/logo@2x.png differ\n')
        rep, fatal, _ = problems(tour(
            '%beat A', 'P.', '%hunk src/@types/a.ts:1 @h1 = the types file',
            '%file x/logo@2x.png @h2 = the retina asset'), p)
        self.assertEqual(fatal, [])
        self.assertEqual([c.path for c in rep.components],
                         ['src/@types/a.ts', 'x/logo@2x.png'])
        self.assertEqual([c.label for c in rep.components], ['h1', 'h2'])

    def test_a_label_may_not_impersonate_a_chapter(self):
        self.assertRejects('already means chapter 3',
                           '%beat A', 'P.', '%hunk src/deep/a.js:10 @ch3 = x')

    def test_unindented_prose_after_a_block_belongs_nowhere(self):
        self.assertRejects('not attached to anything',
                           '%beat A', 'Narration.', '%hunk src/deep/a.js:10 = x',
                           'Which block is this about?')

    def test_unknown_directive(self):
        self.assertRejects('unknown directive %beet', '%beet A', 'P.')

    def test_fold_is_no_longer_a_directive(self):
        self.assertRejects('unknown directive %fold',
                           '%beat A', 'P.', '%fold', '%hunk src/deep/a.js:10 = x')

    def test_component_outside_a_beat(self):
        self.assertRejects('outside a beat', '%hunk src/deep/a.js:10 = x')

    def test_beat_without_prose(self):
        self.assertRejects('no prose', '%beat A', '%hunk src/deep/a.js:10 = x')

    def test_missing_caption(self):
        self.assertRejects('no caption', '%beat A', 'P.', '%hunk src/deep/a.js:10')
        self.assertRejects('no caption', '%beat A', 'P.', '%code sh', 'ls', '%end')

    def test_unknown_hunk_names_the_real_starts(self):
        self.assertRejects('Its hunks start at 10',
                           '%beat A', 'P.', '%hunk src/deep/a.js:999 = x')

    def test_unknown_file_suggests_a_near_match(self):
        self.assertRejects('Did you mean src/deep/a.js?',
                           '%beat A', 'P.', '%hunk src/shallow/a.js:10 = x')

    def test_fragment_out_of_range(self):
        self.assertRejects('outside this hunk',
                           '%beat A', 'P.', '%hunk src/deep/a.js:10 #1-99 = x')

    def test_context_only_fragment(self):
        self.assertRejects('all context and changes nothing',
                           '%beat A', 'P.', '%hunk src/deep/a.js:10 #1-2 = x')

    def test_backwards_fragment(self):
        self.assertRejects('runs backwards',
                           '%beat A', 'P.', '%hunk src/deep/a.js:10 #5-3 = x')

    def test_all_cannot_take_a_fragment(self):
        self.assertRejects('cannot take a #1-3 fragment',
                           '%beat A', 'P.', '%hunk src/deep/a.js:all #1-3 = x')

    def test_file_needs_a_bodyless_change(self):
        self.assertRejects('%file is for a change with no diff body',
                           '%beat A', 'P.', '%file src/deep/a.js = x')

    def test_hunk_refuses_a_bodyless_change(self):
        p = patch.parse('diff --git a/l.png b/l.png\n'
                        'Binary files a/l.png and b/l.png differ\n')
        _, fatal, _ = problems(tour('%beat A', 'P.', '%hunk l.png:1 = x'), p)
        self.assertTrue(any('use %file' in f for f in fatal), fatal)

    def test_a_code_left_open_at_the_end_of_the_file(self):
        _, fatal, _ = problems('\n'.join(
            ['%report T', '%intro O', '%beat B', 'P.', '%code sh = x', 'ls']),
            self.p)
        self.assertTrue(any('never closed' in f for f in fatal), fatal)

    def test_a_code_left_open_before_a_directive_is_caught_there(self):
        self.assertRejects('forgotten %end', '%beat A', 'P.', '%code sh = x', 'ls')

    def test_a_forgotten_end_is_caught_at_the_swallowed_line(self):
        self.assertRejects('forgotten %end', '%beat A', 'P.', '%code sh = x', 'ls',
                           '%hunk src/deep/a.js:10 = would be swallowed')

    def test_heading_in_prose(self):
        self.assertRejects('markdown heading in prose', '%beat A', '### nope')

    def test_bad_blast_level(self):
        self.assertRejects('%blast wants one of', '%beat A', 'P.', '%blast severe')

    def test_blast_outside_a_cluster_chapter(self):
        _, fatal, _ = problems(
            '\n'.join(['%report T', '%intro O', '%blast wide', '%beat B', 'P.',
                       '%closing W', '%beat W', 'P.']), self.p)
        self.assertTrue(any('not to intro' in f for f in fatal), fatal)

    def test_the_plus_spelling_tour_hunks_prints_is_accepted(self):
        _, fatal, _ = problems(tour('%beat A', 'P.',
                                    '%hunk src/deep/a.js:+10 = x'), self.p)
        self.assertEqual(fatal, [])

    def test_a_quote_out_of_range(self):
        here = os.path.dirname(os.path.abspath(__file__))
        _, fatal, _ = problems(tour('%beat A', 'P.',
                                    '%quote test_difftour.py:1-999999 = x'),
                               self.p, root=here)
        self.assertTrue(any('out of range' in f for f in fatal), fatal)

    def test_a_quote_of_a_file_that_is_not_there(self):
        _, fatal, _ = problems(tour('%beat A', 'P.',
                                    '%quote nope/nope.js:1-2 = x'), self.p)
        self.assertTrue(any('cannot read' in f for f in fatal), fatal)


    def test_a_label_on_a_quote_or_a_snippet_is_refused(self):
        """Dead surface: the skeleton never mints one and nothing may reference it."""
        for line in ('%quote src/deep/a.js:1-2 @q1 = the old shape',
                     '%code sh @c1 = how to check'):
            rep, problems = narration.parse(tour('%beat A', 'P.', line, '%end'))
            self.assertTrue(any('cannot take a label' in p.text for p in problems),
                            line)

    def test_an_at_sign_inside_a_quoted_path_is_not_a_label(self):
        rep, problems = narration.parse(
            tour('%beat A', 'P.', '%quote src/@types/a.js:1-2 = typings'))
        self.assertFalse(any('cannot take a label' in p.text for p in problems),
                         [str(p) for p in problems])


class TestNarrationWarns(unittest.TestCase):
    def setUp(self):
        self.p = patch.parse(SIMPLE)

    def test_shape_problems_are_warnings_so_a_draft_still_builds(self):
        _, fatal, warn = problems('\n'.join(
            ['%report T', '%intro O', '%beat B', 'Prose.']), self.p)
        self.assertEqual(fatal, [])
        self.assertTrue(any('no %closing' in w for w in warn), warn)

    def test_a_missing_blast_is_premature_not_wrong(self):
        # A blast level is a claim about reach, which needs the caller index Step G
        # gathers per chapter — so a skeleton legitimately has none, and the commands
        # that run before the prose exists must not complain about it.
        _, probs = narration.parse('\n'.join(
            ['%report T', '%intro O', '%beat B', '%chapter C', '%beat B',
             '%hunk src/deep/a.js:10 = x', '%closing W', '%beat W']))
        blast = [x for x in probs if 'no %blast' in x.text]
        self.assertEqual(len(blast), 1, [str(x) for x in probs])
        self.assertTrue(blast[0].premature)

    def test_a_cluster_chapter_without_a_blast_warns(self):
        _, fatal, warn = problems('\n'.join(
            ['%report T', '%intro O', '%beat B', 'P.', '%chapter C', 'Intro.',
             '%beat B', 'P.', '%closing W', '%beat W', 'P.']), self.p)
        self.assertEqual(fatal, [])
        self.assertTrue(any('no %blast' in w for w in warn), warn)

    def test_a_cluster_chapter_without_an_intro_paragraph_warns(self):
        _, fatal, warn = problems('\n'.join(
            ['%report T', '%intro O', '%beat B', 'P.', '%chapter C', '%blast narrow',
             'E.', '%beat B', 'P.', '%closing W', '%beat W', 'P.']), self.p)
        self.assertEqual(fatal, [])
        self.assertTrue(any('introductory paragraph' in w for w in warn), warn)

    def test_two_whole_copies_of_one_hunk_warn(self):
        _, fatal, warn = problems(tour(
            '%beat A', 'P.', '%hunk src/deep/a.js:10 = once',
            '%beat B', 'P.', '%hunk src/deep/a.js:10 = twice'), self.p)
        self.assertEqual(fatal, [])
        self.assertTrue(any('overlaps' in w for w in warn), warn)

    def test_a_backticked_code_in_prose_warns(self):
        _, fatal, warn = problems(tour(
            '%beat A', 'The guard in `2.1` matters.',
            '%hunk src/deep/a.js:10 @h1 = x'), self.p)
        self.assertEqual(fatal, [])
        self.assertTrue(any('is a position, not a name' in w for w in warn), warn)

    def test_a_bracketed_code_in_prose_warns(self):
        _, fatal, warn = problems(tour(
            '%beat A', 'The guard in [[2.1]] matters.',
            '%hunk src/deep/a.js:10 @h1 = x'), self.p)
        self.assertEqual(fatal, [])
        self.assertTrue(any('is a position, not a name' in w for w in warn), warn)

    def test_overlapping_fragments_warn(self):
        _, fatal, warn = problems(tour(
            '%beat A', 'P.', '%hunk src/deep/a.js:10 #3-4 = one',
            '%beat B', 'P.', '%hunk src/deep/a.js:10 #4-5 = two'), self.p)
        self.assertEqual(fatal, [])
        self.assertTrue(any('overlaps' in w for w in warn), warn)

    def test_a_blank_line_after_a_block_is_harmless(self):
        _, fatal, warn = problems(tour(
            '%beat A', 'Beat prose.', '%hunk src/deep/a.js:10 = x', '',
            '%beat B', 'More prose.'), self.p)
        self.assertEqual((fatal, warn), ([], []))

    def test_a_label_reference_resolves_and_does_not_warn(self):
        rep, fatal, warn = problems(tour(
            '%beat A', 'See [[h1]] and [the guard](#h1).',
            '%hunk src/deep/a.js:10 @h1 = x'), self.p)
        self.assertEqual((fatal, warn), ([], []))
        self.assertEqual(rep.refs, {'h1': '2.1'})


# --------------------------------------------------------------------- coverage

BODYLESS = (SIMPLE +
            'diff --git a/l.png b/l.png\nindex 1..2 100644\n'
            'Binary files a/l.png and b/l.png differ\n')


class TestAllGroupOverlap(unittest.TestCase):
    """`path:all` expands to one block per hunk, so it shares the overlap check.

    A review claimed a hunk shown by both `:all` and an explicit selector rendered twice
    with no warning. It does warn, in either order — pinned here because the claim was
    plausible and the consequence (a change silently shown twice) is the kind this skill
    exists to prevent.
    """

    P = patch.parse(
        'diff --git a/a.js b/a.js\nindex 1..2 100644\n--- a/a.js\n+++ b/a.js\n'
        '@@ -8,3 +8,4 @@ function f() {\n ctx\n-old\n+new\n+more\n ctx2\n'
        '@@ -40,3 +40,3 @@ function g() {\n c\n-x\n+y\n c2\n')

    def warnings_for(self, first, second):
        doc = '\n'.join(
            ['%report T', '%intro O', '%beat W', 'Prose.',
             '%chapter One', 'Premise.', '%blast narrow', 'E.', '%beat A', 'Prose.',
             first,
             '%chapter Two', 'Premise.', '%blast narrow', 'E.', '%beat B', 'Prose.',
             second,
             '%closing W', '%beat C', 'Prose.'])
        rep, problems = narration.parse(doc)
        problems += narration.resolve(rep, self.P, '.')
        return [str(x) for x in problems]

    def test_all_then_explicit_warns(self):
        w = self.warnings_for('%hunk a.js:all = the file', '%hunk a.js:8 = just one')
        self.assertTrue(any('overlaps' in x for x in w), w)

    def test_explicit_then_all_warns(self):
        w = self.warnings_for('%hunk a.js:8 = just one', '%hunk a.js:all = the file')
        self.assertTrue(any('overlaps' in x for x in w), w)

    def test_a_fragment_inside_an_all_group_warns(self):
        w = self.warnings_for('%hunk a.js:all = the file',
                              '%hunk a.js:8 #2-3 = part of one')
        self.assertTrue(any('overlaps' in x for x in w), w)

    def test_all_alone_does_not_warn(self):
        w = self.warnings_for('%hunk a.js:all = the file', '%quote a.js:1-1 = x')
        self.assertFalse(any('overlaps' in x for x in w), w)


class TestCoverage(unittest.TestCase):
    def cov(self, p, *lines):
        rep, fatal, _ = problems(tour(*lines), p)
        self.assertEqual(fatal, [])
        return narration.coverage(rep, p)

    def test_a_whole_hunk_covers_everything(self):
        p = patch.parse(SIMPLE)
        self.assertEqual(self.cov(p, '%beat A', 'P.',
                                  '%hunk src/deep/a.js:10 = all of it'),
                         (3, 3, []))

    def test_a_fragment_leaves_the_rest_as_a_gap(self):
        p = patch.parse(SIMPLE)
        shown, total, gaps = self.cov(
            p, '%beat A', 'P.', '%hunk src/deep/a.js:10 #3-3 = only the deletion')
        self.assertEqual((shown, total), (1, 3))
        self.assertEqual(gaps, [('src/deep/a.js', '10', 4, 5, '2.1')])

    def test_a_shown_line_between_two_misses_breaks_the_run(self):
        p = patch.parse(SIMPLE)
        shown, total, gaps = self.cov(
            p, '%beat A', 'P.', '%hunk src/deep/a.js:10 #4-4 = the middle one')
        self.assertEqual((shown, total), (1, 3))
        self.assertEqual([(g[2], g[3]) for g in gaps], [(3, 3), (5, 5)])

    def test_two_fragments_together_can_cover_a_hunk(self):
        p = patch.parse(SIMPLE)
        self.assertEqual(self.cov(p, '%beat A', 'P.',
                                  '%hunk src/deep/a.js:10 #3-3 = a',
                                  '%beat B', 'P.',
                                  '%hunk src/deep/a.js:10 #4-5 = b'),
                         (3, 3, []))

    def test_a_bodyless_change_is_a_coverage_item(self):
        p = patch.parse(BODYLESS)
        shown, total, gaps = self.cov(p, '%beat A', 'P.',
                                      '%hunk src/deep/a.js:10 = the code')
        self.assertEqual((shown, total), (3, 4))
        self.assertEqual(gaps, [('l.png', None, None, None, None)])

    def test_naming_the_binary_closes_it(self):
        p = patch.parse(BODYLESS)
        self.assertEqual(self.cov(p, '%beat A', 'P.',
                                  '%hunk src/deep/a.js:10 = the code',
                                  '%file l.png = the logo'),
                         (4, 4, []))

    def test_context_lines_are_never_a_gap(self):
        p = patch.parse(SIMPLE)
        _, total, _ = self.cov(p, '%beat A', 'P.', '%hunk src/deep/a.js:10 = x')
        self.assertEqual(total, 3)          # 3 changed lines, not 7 body lines

    def test_coverage_is_linear(self):
        # A lockfile refresh is one enormous hunk, and coverage runs on every build.
        big = ['diff --git a/lock b/lock', '--- a/lock', '+++ b/lock',
               '@@ -1,1 +1,20001 @@', ' ctx']
        big += ['+line %d' % i for i in range(20000)]
        p = patch.parse('\n'.join(big) + '\n')
        rep, fatal, _ = problems(tour('%beat A', 'P.',
                                      '%hunk lock:1 #2-100 = the head of it'), p)
        self.assertEqual(fatal, [])
        started = time.time()
        shown, total, gaps = narration.coverage(rep, p)
        self.assertLess(time.time() - started, 1.0)
        self.assertEqual((shown, total, len(gaps)), (99, 20000, 1))


# --------------------------------------------------------------------- render.py

class TestRender(unittest.TestCase):
    def build(self, text, src=SIMPLE, root='.'):
        p = patch.parse(src)
        rep, probs = narration.parse(text)
        probs += narration.resolve(rep, p, root)
        self.assertEqual([str(x) for x in probs if x.fatal], [])
        html, missing = render.page(rep, p.stats(), 'a..b', '2026-01-01', 'uid')
        self.assertEqual(missing, [])
        return html

    def test_the_page_is_self_contained(self):
        import re
        html = self.build(tour('%beat A', 'P.', '%hunk src/deep/a.js:10 = x'))
        self.assertEqual(re.findall(r'(?:src|href)="([^"#]+)"', html), [])
        self.assertIn('<style>', html)
        self.assertIn('window.Prism', html)

    def test_the_fixtures_own_explanation_is_not_shipped(self):
        html = self.build(tour('%beat A', 'P.', '%hunk src/deep/a.js:10 = x'))
        self.assertNotIn('the page shell', html)

    def test_diff_text_is_escaped_not_interpreted(self):
        evil = ('diff --git a/a.js b/a.js\n--- a/a.js\n+++ b/a.js\n@@ -1,1 +1,1 @@\n'
                '-old\n+</code></pre><script>alert(1)</script>\n')
        html = self.build(tour('%beat A', 'P.', '%hunk a.js:1 = evil'), src=evil)
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)

    def test_a_caption_is_escaped_too(self):
        html = self.build(tour('%beat A', 'P.',
                               '%hunk src/deep/a.js:10 = a <script>x</script> caption'))
        self.assertNotIn('<script>x</script>', html)

    def test_a_title_is_never_a_regex_replacement(self):
        html = self.build(tour('%beat A', 'P.', '%hunk src/deep/a.js:10 = x')
                          .replace('%report T', r'%report Handle \d and \g<0>'))
        self.assertIn(r'<title>Handle \d and \g&lt;0&gt;</title>', html)

    def test_a_hunks_id_is_its_code(self):
        html = self.build(tour('%beat A', 'P.', '%hunk src/deep/a.js:10 = x'))
        self.assertIn('id="2.1"', html)
        self.assertIn('data-code="2.1"', html)

    def test_a_fragment_says_what_it_is_a_fragment_of(self):
        html = self.build(tour('%beat A', 'P.',
                               '%hunk src/deep/a.js:10 #4-5 = the added pair'))
        self.assertIn('lines 4–5 of 7', html)
        self.assertIn('3 more lines above', html)
        self.assertIn('2 more lines below', html)
        self.assertIn('src/deep/a.js:12', html)      # the new-file line it starts at

    def test_a_pure_deletion_shows_the_old_files_line(self):
        html = self.build(tour('%beat A', 'P.',
                               '%hunk src/deep/a.js:10 #3-3 = the removal'))
        self.assertIn('src/deep/a.js:12', html)

    def test_line_counts_are_in_the_caption(self):
        html = self.build(tour('%beat A', 'P.', '%hunk src/deep/a.js:10 = x'))
        self.assertIn('+2 −1', html)

    def test_a_mode_flip_is_surfaced_on_the_blocks_of_that_file(self):
        src = ('diff --git a/bin/run b/bin/run\nold mode 100644\nnew mode 100755\n'
               '--- a/bin/run\n+++ b/bin/run\n@@ -1,1 +1,2 @@\n keep\n+added\n')
        html = self.build(tour('%beat A', 'P.', '%hunk bin/run:1 = the edit'), src=src)
        self.assertIn('mode 100644 → 100755', html)

    def test_a_renamed_and_edited_file_says_where_it_came_from(self):
        src = ('diff --git a/old/n.js b/new/n.js\nsimilarity index 80%\n'
               'rename from old/n.js\nrename to new/n.js\n'
               '--- a/old/n.js\n+++ b/new/n.js\n@@ -1,1 +1,1 @@\n-a\n+b\n')
        html = self.build(tour('%beat A', 'P.', '%hunk new/n.js:1 = moved and edited'),
                          src=src)
        self.assertIn('was <code>old/n.js</code>', html)
        self.assertIn('tag moved', html)

    def test_bodyless_kinds_are_stated_from_the_diff(self):
        src = ('diff --git a/l.png b/l.png\nBinary files a/l.png and b/l.png differ\n'
               'diff --git a/o.js b/n.js\nrename from o.js\nrename to n.js\n'
               'diff --git a/e.js b/e.js\nnew file mode 100644\n'
               'diff --git a/m b/m\nold mode 100644\nnew mode 100755\n')
        html = self.build(tour('%beat A', 'P.', '%file l.png = a', '%file n.js = b',
                               '%file e.js = c', '%file m = d'), src=src)
        self.assertIn('This binary file changed.', html)
        self.assertIn('Renamed from <code>o.js</code>', html)
        self.assertIn('A new empty file.', html)
        self.assertIn('mode changed from <code>100644</code> to <code>100755</code>', html)

    def test_a_no_newline_change_is_visible(self):
        src = ('diff --git a/a b/a\n--- a/a\n+++ b/a\n@@ -1,1 +1,1 @@\n'
               '-old\n\\ No newline at end of file\n+new\n')
        html = self.build(tour('%beat A', 'P.', '%hunk a:1 = x'), src=src)
        self.assertIn('no newline at end of file', html)

    def test_nothing_in_a_fresh_report_starts_collapsed(self):
        # The reader decides what to put away; the author does not pre-hide anything.
        # (The word appears in the inlined CSS and JS, so check the markup only.)
        html = self.build(tour('%beat A', 'P.', '%hunk src/deep/a.js:10 = x'))
        body = html[html.index('<!--REPORT-->'):html.index('<!--/REPORT-->')]
        self.assertNotIn('collapsed', body)
        self.assertNotIn('fold', body)

    def test_a_beat_with_no_blocks_is_full_width(self):
        self.assertIn('class="beat solo"', self.build(tour('%beat A', 'Only prose.')))

    def test_a_blocks_own_prose_renders_above_its_diff(self):
        html = self.build(tour('%beat A', 'Beat prose.',
                               '%hunk src/deep/a.js:10 #3-3 = first',
                               '  About the first.',
                               '%hunk src/deep/a.js:10 #4-5 = second',
                               '  About the second.'))
        show = html[html.index('<div class="show">'):]
        order = re.findall(r'class="note"|id="2\.\d"', show)
        self.assertEqual(order[:4], ['class="note"', 'id="2.1"',
                                     'class="note"', 'id="2.2"'])
        self.assertIn('<p>About the first.</p>', html)

    def test_the_language_class_comes_from_the_files_extension(self):
        html = self.build(tour('%beat A', 'P.', '%hunk src/deep/a.js:10 = x'))
        self.assertIn('class="language-diff-javascript diff-highlight"', html)

    def test_an_unknown_extension_still_renders_a_diff(self):
        src = ('diff --git a/a.xyz b/a.xyz\n--- a/a.xyz\n+++ b/a.xyz\n'
               '@@ -1,1 +1,1 @@\n-a\n+b\n')
        html = self.build(tour('%beat A', 'P.', '%hunk a.xyz:1 = x'), src=src)
        self.assertIn('class="language-diff-none diff-highlight"', html)

    def test_a_quote_reads_the_file_rather_than_being_retyped(self):
        here = os.path.dirname(os.path.abspath(__file__))
        html = self.build(tour('%beat A', 'P.',
                               '%quote test_difftour.py:1-2 = the top of this file'),
                          root=here)
        self.assertIn('#!/usr/bin/env python3', html)
        self.assertIn('class="hunk quote"', html)

    def test_two_identical_quotes_do_not_share_an_id(self):
        here = os.path.dirname(os.path.abspath(__file__))
        html = self.build(tour('%beat A', 'P.',
                               '%quote test_difftour.py:1-2 = once',
                               '%quote test_difftour.py:1-2 = twice'), root=here)
        import re
        ids = re.findall(r'<figure class="hunk quote" id="([^"]+)"', html)
        self.assertEqual(len(ids), len(set(ids)))

    def test_a_snippet_says_it_was_not_taken_from_the_change(self):
        # It is the only code in the report nobody verified, so the line where every
        # other block states its provenance has to state this one's too.
        html = self.build(tour('%beat A', 'P.', '%hunk src/deep/a.js:10 = real',
                               '%code sh = how to check', 'grep -rn x src/', '%end'))
        self.assertIn('written for this report, not taken from the change', html)
        # and it must not be mistaken for a numbered block of the change
        self.assertIn('<span class="code">snippet</span>', html)

    def test_a_snippet_language_goes_through_the_alias_table(self):
        html = self.build(tour('%beat A', 'P.', '%code sh = how to run it',
                               'bin/test', '%end'))
        self.assertIn('class="language-bash"', html)
        html = self.build(tour('%beat A', 'P.', '%code nosuchlang = x', 'y', '%end'))
        self.assertIn('class="language-none"', html)

    def test_the_header_names_the_repo_and_branch_when_given(self):
        p = patch.parse(SIMPLE)
        rep, _ = narration.parse(tour('%beat A', 'P.', '%hunk src/deep/a.js:10 = x'))
        narration.resolve(rep, p, '.')
        html, _ = render.page(rep, p.stats(), 'a..b', '2026-01-01', 'uid',
                              repo='billing-api', branch='hk/cache-key')
        self.assertIn('<b>billing-api</b>', html)
        self.assertIn('<b>hk/cache-key</b>', html)
        self.assertNotIn('/home/', html)

    def test_the_header_omits_repo_and_branch_when_unknown(self):
        html = self.build(tour('%beat A', 'P.', '%hunk src/deep/a.js:10 = x'))
        meta = html[html.index('<p class="meta">'):html.index('</p>')]
        self.assertTrue(meta.strip().startswith('<p class="meta"><b>1</b> file'), meta)

    def test_the_standfirst_says_what_the_document_is(self):
        html = self.build(tour('%beat A', 'P.', '%hunk src/deep/a.js:10 = x'))
        self.assertIn('class="standfirst"', html)
        self.assertIn('not an automated code review', html)

    def test_the_metadata_line_reports_the_patch_not_the_report(self):
        html = self.build(tour('%beat A', 'P.',
                               '%hunk src/deep/a.js:10 #3-3 = part of it'))
        self.assertIn('<b>1</b> file ', html)
        # The counts are coloured, and the reader is told "change", not "hunk".
        self.assertIn('<b class="added">+2</b> <b class="removed">−1</b>', html)
        self.assertIn('<b>1</b> change', html)
        self.assertNotIn('hunk', html[html.index('<p class="meta">'):html.index('</p>')])

    def test_chapters_are_numbered_from_position(self):
        html = self.build(tour('%beat A', 'P.', '%hunk src/deep/a.js:10 = x'))
        self.assertIn('<section class="chapter" id="ch1">', html)
        self.assertIn('<section class="chapter" id="ch3">', html)
        self.assertIn('<span class="n">2</span>', html)

    def test_the_blast_level_reaches_the_markup(self):
        html = self.build(tour('%beat A', 'P.', '%hunk src/deep/a.js:10 = x'))
        self.assertIn('<aside class="blast narrow" data-level="narrow">', html)


# ------------------------------------------------------------------ the commands

class TestHunksCommand(unittest.TestCase):
    """bin/tour-hunks.py is the read Step D is built on, so its filtering matters."""

    def setUp(self):
        import subprocess, tempfile
        self.bin = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), 'bin', 'tour-hunks.py')
        self.patch = tempfile.NamedTemporaryFile('w', suffix='.patch', delete=False)
        self.patch.write(
            SIMPLE +
            'diff --git a/src/deep/b.js b/src/deep/b.js\n--- a/src/deep/b.js\n'
            '+++ b/src/deep/b.js\n@@ -1,1 +1,2 @@\n keep\n+added\n'
            'diff --git a/other/c.js b/other/c.js\n--- a/other/c.js\n'
            '+++ b/other/c.js\n@@ -1,1 +1,2 @@\n keep\n+added\n')
        self.patch.close()
        self.run = lambda *a: subprocess.run(
            [sys.executable, self.bin, self.patch.name] + list(a),
            capture_output=True, text=True)

    def tearDown(self):
        os.unlink(self.patch.name)

    def test_a_prefix_selects_a_subtree(self):
        out = self.run('src/deep').stdout
        self.assertIn('src/deep/a.js', out)
        self.assertIn('src/deep/b.js', out)
        self.assertNotIn('other/c.js', out)

    def test_not_excludes_what_a_prefix_would_have_included(self):
        out = self.run('src/deep', '--not', 'src/deep/a.js').stdout
        self.assertNotIn('src/deep/a.js', out)
        self.assertIn('src/deep/b.js', out)

    def test_not_works_without_any_prefix(self):
        out = self.run('-x', 'src/deep').stdout
        self.assertIn('other/c.js', out)
        self.assertNotIn('src/deep', out)

    def test_not_needs_a_value(self):
        r = self.run('--not')
        self.assertEqual(r.returncode, 2)
        self.assertIn('needs a path', r.stderr)

    def test_the_list_states_what_reading_a_file_would_cost(self):
        out = self.run('src/deep/a.js').stdout
        self.assertIn('1 hunk · 7 body lines, 3 changed', out)

    def test_the_list_carries_no_diff_body(self):
        # The point of the cheap read: it says what is there without quoting it. The
        # size ratio only holds at scale, so assert the invariant instead.
        out = self.run().stdout
        self.assertNotIn('added one', out)
        self.assertNotIn('gone', out)
        self.assertIn('@10', out)
        self.assertIn('added one', self.run('--body').stdout)

    def test_the_list_gives_fragment_boundaries_without_a_body_read(self):
        # A hunk of several runs is several ideas; the runs are where a fragment
        # begins and ends, so a caller should not have to count them by hand.
        out = self.run('src/deep/a.js').stdout
        self.assertNotIn('runs:', out)          # one run, nothing to say
        with open(self.patch.name, 'a') as f:
            f.write('diff --git a/src/many.js b/src/many.js\n--- a/src/many.js\n'
                    '+++ b/src/many.js\n@@ -1,9 +1,9 @@\n'
                    ' ctx\n-a\n+A\n ctx\n ctx\n-b\n+B\n ctx\n')
        out = self.run('src/many.js').stdout
        self.assertIn('2 runs: 2-3, 6-7', out)

    def test_the_list_says_what_a_full_read_would_cost(self):
        self.assertRegex(self.run('src/deep/a.js').stdout, r'\d+\.\d KB to read')

    def test_renames_groups_only_swaps_that_repeat(self):
        with open(self.patch.name, 'a') as f:
            for n in (1, 2, 3):
                f.write('diff --git a/src/r%d.js b/src/r%d.js\n--- a/src/r%d.js\n'
                        '+++ b/src/r%d.js\n@@ -1,2 +1,2 @@\n ctx\n'
                        '-use(links_to_content)\n+use(external_link_enabled)\n'
                        % (n, n, n, n))
        r = self.run('--renames')
        self.assertIn("'links_to_content'  ->  'external_link_enabled'    (3 hunks)",
                      r.stdout)
        self.assertIn('3 hunks in 1 sweep', r.stderr)
        # the one-off changes in SIMPLE are changes, not a sweep
        self.assertNotIn('src/deep/a.js', r.stdout)

    def test_renames_reports_a_greppable_identifier(self):
        # The character-minimal swap for `call(oldName)` -> `call(newName)` is
        # old -> new, and the next instruction is to grep the old name for
        # stragglers — where `old` also matches `older` and `bold`. The needle has to
        # be the identifier.
        with open(self.patch.name, 'a') as f:
            for n in (1, 2):
                f.write('diff --git a/src/s%d.js b/src/s%d.js\n--- a/src/s%d.js\n'
                        '+++ b/src/s%d.js\n@@ -1,2 +1,2 @@\n ctx\n'
                        '-call(oldName)\n+call(newName)\n' % (n, n, n, n))
        self.assertIn("'oldName'  ->  'newName'    (2 hunks)",
                      self.run('--renames').stdout)

    def test_renames_widens_through_an_underscore(self):
        with open(self.patch.name, 'a') as f:
            for n in (1, 2):
                f.write('diff --git a/src/u%d.rb b/src/u%d.rb\n--- a/src/u%d.rb\n'
                        '+++ b/src/u%d.rb\n@@ -1,2 +1,2 @@\n ctx\n'
                        '-use(links_to_content)\n+use(links_to_media)\n'
                        % (n, n, n, n))
        self.assertIn("'links_to_content'  ->  'links_to_media'",
                      self.run('--renames').stdout)

    def test_renames_ignores_a_hunk_that_is_not_a_clean_swap(self):
        with open(self.patch.name, 'a') as f:
            for n in (1, 2):
                f.write('diff --git a/src/m%d.js b/src/m%d.js\n--- a/src/m%d.js\n'
                        '+++ b/src/m%d.js\n@@ -1,3 +1,3 @@\n ctx\n'
                        '-one(a)\n+two(b)\n-three(c)\n+four(d)\n' % (n, n, n, n))
        self.assertNotIn('src/m1.js', self.run('--renames').stdout)

    def test_renames_says_so_when_there_is_no_mechanical_tier(self):
        r = self.run('--renames')
        self.assertIn('no swap repeats across hunks', r.stderr)

    def test_body_prints_offsets_a_fragment_selector_can_use(self):
        out = self.run('--body', 'src/deep/a.js').stdout
        self.assertIn('    3 -gone', out)
        self.assertIn('    4 +added one', out)


class TestFetch(unittest.TestCase):
    """bin/tour-fetch.sh is the most environment-dependent piece and had no tests."""

    def setUp(self):
        import subprocess, tempfile
        self.sub = subprocess
        self.root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.cmd = os.path.join(self.root, 'bin', 'tour-fetch.sh')
        self.dir = tempfile.mkdtemp()
        self.repo = os.path.join(self.dir, 'repo')
        os.makedirs(self.repo)
        self.g('init', '-q', '-b', 'main')
        self._commit('base.js', 'one\n')
        self.g('checkout', '-q', '-b', 'feature')
        self._commit('src/added.js', 'new\n')
        self._commit('docs/guide.md', 'doc\n')

    def tearDown(self):
        import shutil
        shutil.rmtree(self.dir, ignore_errors=True)

    def g(self, *args):
        return self.sub.run(['git', '-C', self.repo, '-c', 'user.email=t@t',
                             '-c', 'user.name=t'] + list(args),
                            capture_output=True, text=True)

    def _commit(self, path, body):
        full = os.path.join(self.repo, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'w') as f:
            f.write(body)
        self.g('add', path)
        self.g('commit', '-qm', 'add ' + path)

    def fetch(self, *args):
        out = os.path.join(self.dir, 'p.patch')
        env = dict(os.environ, TOUR_REPO=self.repo)
        r = self.sub.run(['bash', self.cmd, out] + list(args),
                         capture_output=True, text=True, env=env)
        body = ''
        if os.path.exists(out):
            with open(out) as f:
                body = f.read()
        return r, out, body

    def test_a_range_resolves(self):
        r, _, body = self.fetch('main..feature')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('src/added.js', body)
        self.assertIn('docs/guide.md', body)

    def test_a_branch_is_compared_against_the_default_with_three_dots(self):
        r, _, body = self.fetch('feature')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('src/added.js', body)

    def test_one_commit_is_that_commit_alone(self):
        r, _, body = self.fetch('HEAD')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('docs/guide.md', body)
        self.assertNotIn('src/added.js', body)

    def test_a_pathspec_narrows_the_patch_and_says_so(self):
        r, _, body = self.fetch('main..feature', '--', 'src/')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('src/added.js', body)
        self.assertNotIn('docs/guide.md', body)
        self.assertIn('narrowed to src/', r.stderr)

    def test_it_records_the_head_the_diff_ends_at(self):
        r, out, _ = self.fetch('main..feature')
        with open(out + '.head') as f:
            recorded = f.read().strip()
        self.assertEqual(recorded, self.g('rev-parse', 'feature').stdout.strip())

    def test_an_unresolvable_target_fails_loudly(self):
        r, _, _ = self.fetch('no-such-ref')
        self.assertEqual(r.returncode, 3)
        self.assertIn('cannot resolve target', r.stderr)

    def test_an_empty_diff_is_refused_rather_than_toured(self):
        r, _, _ = self.fetch('feature..feature')
        self.assertEqual(r.returncode, 3)
        self.assertIn('the diff is empty', r.stderr)

    def test_a_patch_file_is_copied_through(self):
        src = os.path.join(self.dir, 'given.patch')
        with open(src, 'w') as f:
            f.write(SIMPLE)
        r, _, body = self.fetch(src)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(body, SIMPLE)


class TestSkeletonCommand(unittest.TestCase):
    """bin/tour-skeleton.py is the only command that edits the narration file."""

    def setUp(self):
        import subprocess, tempfile
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.cmd = os.path.join(root, 'bin', 'tour-skeleton.py')
        self.dir = tempfile.mkdtemp()
        self.patch = os.path.join(self.dir, 'p.patch')
        with open(self.patch, 'w') as f:
            f.write(SIMPLE +
                    'diff --git a/src/deep/b.js b/src/deep/b.js\n--- a/src/deep/b.js\n'
                    '+++ b/src/deep/b.js\n@@ -1,1 +1,3 @@\n keep\n+one\n+two\n')
        self.doc = os.path.join(self.dir, 'n.tour')
        self._run = lambda: subprocess.run(
            [sys.executable, self.cmd, self.patch, self.doc],
            capture_output=True, text=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.dir, ignore_errors=True)

    def write(self, *lines):
        with open(self.doc, 'w') as f:
            f.write(tour(*lines))

    def raw(self, text):
        with open(self.doc, 'w') as f:
            f.write(text)

    def read(self):
        with open(self.doc) as f:
            return f.read()

    def test_it_labels_every_block_that_lacks_one(self):
        self.write('%beat A', '%hunk src/deep/a.js:10 = the swap',
                   '%hunk src/deep/b.js:1 = the other')
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('%hunk src/deep/a.js:10 @h1 = the swap', self.read())
        self.assertIn('%hunk src/deep/b.js:1 @h2 = the other', self.read())
        self.assertIn('labelled 2 blocks', r.stderr)

    def test_it_leaves_an_existing_label_alone_and_does_not_collide(self):
        self.write('%beat A', '%hunk src/deep/a.js:10 @h1 = kept',
                   '%hunk src/deep/b.js:1 = minted')
        self.assertEqual(self._run().returncode, 0)
        body = self.read()
        self.assertIn('@h1 = kept', body)
        self.assertIn('@h2 = minted', body)

    def test_it_is_idempotent(self):
        self.write('%beat A', '%hunk src/deep/a.js:10 = x')
        self._run()
        once = self.read()
        r = self._run()
        self.assertEqual(self.read(), once)
        self.assertNotIn('labelled', r.stderr)

    def test_it_does_not_label_an_all_directive(self):
        self.write('%beat A', '%hunk src/deep/a.js:all = every hunk',
                   '%hunk src/deep/b.js:1 = the other')
        self.assertEqual(self._run().returncode, 0)
        self.assertIn('%hunk src/deep/a.js:all = every hunk', self.read())
        self.assertIn('src/deep/b.js:1 @h1 =', self.read())

    def test_the_table_pairs_labels_with_the_codes_they_resolve_to(self):
        self.write('%beat A', '%hunk src/deep/a.js:10 = the swap',
                   '%hunk src/deep/b.js:1 = the other')
        out = self._run().stdout
        # One line, so a table that pairs them wrongly cannot pass.
        row = [l for l in out.split('\n') if 'the swap' in l]
        self.assertEqual(len(row), 1, out)
        self.assertRegex(row[0], r'\[\[h1\]\]\s+2\.1\s+the swap\s+src/deep/a\.js:10')

    def test_the_table_states_each_chapters_block_count(self):
        # Step G packs forks from these numbers, so they are printed rather than
        # left to be counted off the rows.
        self.write('%beat A', '%hunk src/deep/a.js:10 = one',
                   '%hunk src/deep/b.js:1 = two')
        out = self._run().stdout
        self.assertIn('2 · The cluster · 2 blocks', out)
        self.assertIn('1 · Overview  (intro) · 0 blocks', out)

    def _packing(self, sizes):
        import importlib.util
        spec = importlib.util.spec_from_file_location('sk', self.cmd)
        sk = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sk)
        rep = narration.Report(title='T')
        for i, n in enumerate(sizes, 2):
            ch = narration.Chapter('chapter', 'C', 1, number=i)
            b = narration.Beat('b', 1)
            b.items = [narration.Component('hunk', 1, 'c') for _ in range(n)]
            ch.beats.append(b)
            rep.chapters.append(ch)
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            sk._suggest_forks(rep)
        return buf.getvalue()

    def test_the_packing_never_exceeds_the_biggest_chapter(self):
        # That size is the floor on wall clock however many forks you spawn, so a
        # fork bigger than it would make the report slower, not faster.
        import re
        out = self._packing([30, 17, 12, 10, 5, 5, 4, 4, 3, 3, 2, 2, 2, 2, 1, 1, 1])
        loads = [int(n) for n in re.findall(r'(\d+) blocks', out)]
        self.assertEqual(max(loads[1:]), 30)     # first is the cap in the preamble
        self.assertEqual(sum(loads[1:]), 104)    # every chapter placed exactly once
        self.assertEqual(out.count('fork '), 4)

    def test_many_small_chapters_do_not_get_a_fork_each(self):
        """First-fit-decreasing on uniform chapters degenerates to one fork per chapter,
        which contradicts the skill's own "past five or six, ask what it buys"."""
        out = self._packing([1] * 12)
        forks = [l for l in out.split('\n') if l.strip().startswith('fork')]
        self.assertLessEqual(len(forks), 6, out)
        self.assertGreater(len(forks), 1, out)

    def test_one_dominant_chapter_packs_into_two(self):
        out = self._packing([40, 2, 2, 2, 1, 1, 1, 1, 1])
        self.assertEqual(out.count('fork '), 2)

    def test_even_chapters_get_a_fork_each(self):
        self.assertEqual(self._packing([8, 8, 8, 8, 8]).count('fork '), 5)

    def test_a_single_chapter_suggests_nothing(self):
        self.assertEqual(self._packing([12]), '')

    def test_an_at_sign_in_a_caption_does_not_pass_for_a_label(self):
        self.write('%beat A', '%hunk src/deep/a.js:10 = strip the @media hack',
                   '%hunk src/deep/b.js:1 = the other')
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('@h1 = strip the @media hack', self.read())

    def test_it_labels_a_file_directive_and_a_fragment(self):
        with open(self.patch, 'a') as f:
            f.write('diff --git a/l.png b/l.png\n'
                    'Binary files a/l.png and b/l.png differ\n')
        self.write('%beat A', '%hunk src/deep/a.js:10 #3-3 = a fragment',
                   '%hunk src/deep/a.js:10 #4-5 = the rest',
                   '%hunk src/deep/b.js:1 = whole', '%file l.png = the asset')
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stderr)
        body = self.read()
        self.assertIn('#3-3 @h1 = a fragment', body)
        self.assertIn('#4-5 @h2 = the rest', body)
        self.assertIn('%file l.png @h4 = the asset', body)

    def test_a_directive_inside_a_code_body_is_refused_as_a_missing_end(self):
        # A deliberate limitation: a snippet cannot contain a line that opens a
        # directive, because a forgotten %end is the far likelier reading. The
        # refusal is what keeps the labeller from ever seeing such a line.
        self.write('%beat A', '%code sh = how to run it',
                   '%hunk not/a/real.js:1 = a snippet line', '%end',
                   '%hunk src/deep/a.js:10 = a', '%hunk src/deep/b.js:1 = b')
        r = self._run()
        self.assertEqual(r.returncode, 6)
        self.assertIn('forgotten %end', r.stderr)

    def test_a_code_body_line_that_merely_starts_like_a_directive_is_untouched(self):
        # `%hunkish` passes validation (the recovery is word-bounded) but would be
        # labelled by a prefix match, so the labeller tracks %code bodies itself.
        self.write('%beat A', '%code sh = how to run it', '%hunkish --flag', '%end',
                   '%hunk src/deep/a.js:10 = a', '%hunk src/deep/b.js:1 = b')
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('%hunkish --flag', self.read())
        self.assertNotIn('%hunkish --flag @', self.read())

    def test_missing_prose_is_expected_and_not_an_error(self):
        self.write('%beat A', '%hunk src/deep/a.js:10 = x',
                   '%hunk src/deep/b.js:1 = y')
        r = self._run()
        self.assertEqual(r.returncode, 0)
        self.assertNotIn('no prose', r.stderr)
        self.assertIn('still need prose', r.stderr)

    def test_a_reference_does_not_deadlock_the_command_that_mints_labels(self):
        # Writing [[h1]] before the labels exist must not stop the command that
        # creates them, or there is no way out.
        self.raw('\n'.join(['%report T', '%intro O', '%beat B', '%chapter C',
                            '%blast narrow', '%beat B', 'See [[h1]] for the swap.',
                            '%hunk src/deep/a.js:10 = a',
                            '%hunk src/deep/b.js:1 = b',
                            '%closing W', '%beat W']))
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('@h1 = a', self.read())

    def test_it_says_when_a_reference_still_will_not_resolve(self):
        self.raw('\n'.join(['%report T', '%intro O', '%beat B', '%chapter C',
                            '%blast narrow', '%beat B', 'See [[hzz]].',
                            '%hunk src/deep/a.js:10 = a',
                            '%hunk src/deep/b.js:1 = b',
                            '%closing W', '%beat W']))
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('reference does not resolve yet', r.stderr)

    def test_a_structural_error_stops_it_and_writes_nothing(self):
        self.write('%beat A', '%hunk src/deep/a.js:999 = nope')
        before = self.read()
        r = self._run()
        self.assertEqual(r.returncode, 6)
        self.assertIn('no hunk at +999', r.stderr)
        self.assertEqual(self.read(), before)

    def test_incomplete_coverage_exits_1_and_says_so(self):
        self.write('%beat A', '%hunk src/deep/a.js:10 = only this one')
        r = self._run()
        self.assertEqual(r.returncode, 1)
        self.assertIn('still unplaced', r.stderr)

    def test_complete_coverage_exits_0(self):
        self.write('%beat A', '%hunk src/deep/a.js:10 = one',
                   '%hunk src/deep/b.js:1 = two')
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('Coverage is settled', r.stderr)


class _CommandCase(unittest.TestCase):
    """A patch and a narration file on disk, and the commands run against them."""

    EXTRA = ''

    def setUp(self):
        import subprocess, tempfile
        self.root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.dir = tempfile.mkdtemp()
        self.patch = os.path.join(self.dir, 'p.patch')
        with open(self.patch, 'w') as f:
            f.write(SIMPLE +
                    'diff --git a/src/deep/b.js b/src/deep/b.js\n--- a/src/deep/b.js\n'
                    '+++ b/src/deep/b.js\n@@ -1,1 +1,3 @@\n keep\n+one\n+two\n'
                    + self.EXTRA)
        self.doc = os.path.join(self.dir, 'n.tour')
        self.out = os.path.join(self.dir, 'r.html')
        self.sub = subprocess

    def tearDown(self):
        import shutil
        shutil.rmtree(self.dir, ignore_errors=True)

    def write(self, *lines):
        with open(self.doc, 'w') as f:
            f.write(tour(*lines))

    def raw(self, text):
        with open(self.doc, 'w') as f:
            f.write(text)

    def read(self):
        with open(self.doc) as f:
            return f.read()

    def build(self, *extra):
        return self.run_cmd('tour-build.py', self.out, *extra)

    def run_cmd(self, name, *extra):
        return self.sub.run(
            [sys.executable, os.path.join(self.root, 'bin', name),
             self.patch, self.doc] + list(extra),
            capture_output=True, text=True)


class TestRestCommand(_CommandCase):
    """bin/tour-rest.py is where Step F sends you when coverage is short."""

    def test_it_reports_nothing_left_when_everything_is_placed(self):
        self.write('%beat A', 'P.', '%hunk src/deep/a.js:10 = a',
                   '%hunk src/deep/b.js:1 = b')
        r = self.run_cmd('tour-rest.py')
        self.assertEqual(r.returncode, 0)
        self.assertIn('every file accounted for', r.stdout)

    def test_it_defers_an_unresolved_reference_like_it_defers_prose(self):
        self.raw('\n'.join(['%report T', '%intro O', '%beat B', '%chapter C',
                            '%blast narrow', '%beat B', 'See [[h1]].',
                            '%hunk src/deep/a.js:10 = a',
                            '%hunk src/deep/b.js:1 = b',
                            '%closing W', '%beat W']))
        r = self.run_cmd('tour-rest.py')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn('does not parse', r.stderr)

    def test_it_runs_on_a_skeleton_which_has_no_prose_at_all(self):
        # The stage Step F prescribes. Prose has no bearing on coverage, so a
        # skeleton must not be refused here.
        self.raw('\n'.join(['%report T', '%intro O', '%beat B', '%chapter C',
                            '%blast narrow', '%beat B',
                            '%hunk src/deep/a.js:10 = a',
                            '%closing W', '%beat W']))
        r = self.run_cmd('tour-rest.py')
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertNotIn('does not parse', r.stderr)
        self.assertIn('%hunk src/deep/b.js:1 = ', r.stdout)

    def test_it_still_refuses_a_narration_that_does_not_parse(self):
        self.write('%beat A', 'P.', '%hunk src/deep/a.js:999 = nope')
        r = self.run_cmd('tour-rest.py')
        self.assertEqual(r.returncode, 6)
        self.assertIn('does not parse', r.stderr)

    def test_it_names_a_whole_hunk_rather_than_a_slice_of_it(self):
        self.write('%beat A', 'P.', '%hunk src/deep/a.js:10 = a')
        out = self.run_cmd('tour-rest.py').stdout
        self.assertIn('%hunk src/deep/b.js:1 = ', out)
        self.assertNotIn('#', out.split('src/deep/b.js:1')[1].split('\n')[0])

    def test_it_suggests_widening_a_fragment_it_sits_next_to(self):
        self.write('%beat A', 'P.', '%hunk src/deep/a.js:10 #3-3 = part',
                   '%hunk src/deep/b.js:1 = b')
        out = self.run_cmd('tour-rest.py').stdout
        self.assertIn('widen that fragment', out)
        self.assertIn('2.1', out)

    def test_its_output_can_be_pasted_back_without_syntax_errors(self):
        self.write('%beat A', 'P.', '%hunk src/deep/a.js:10 = a')
        out = self.run_cmd('tour-rest.py').stdout
        for line in out.split('\n'):
            if line.strip() and not line.startswith(('%#', '%hunk', '%file')):
                self.fail('not pasteable: %r' % line)


class TestSpliceCommand(_CommandCase):
    """Putting parallel-narrated chapters back without disturbing anything else."""

    def skeleton(self):
        self.raw('\n'.join(
            ['%report T', '%intro Overview', '%beat What', 'Prose.',
             '%chapter First topic', '%beat A', '%hunk src/deep/a.js:10 = a',
             '%chapter Second topic', '%beat B', '%hunk src/deep/b.js:1 = b',
             '%closing Wrap-up', '%beat Check', 'Prose.']))

    def labelled_skeleton(self):
        """The realistic case: tour-skeleton.py has already minted labels."""
        self.raw('\n'.join(
            ['%report T', '%intro Overview', '%beat What', 'Prose.',
             '%chapter First topic', '%beat A', '%hunk src/deep/a.js:10 @h1 = a',
             '%chapter Second topic', '%beat B', '%hunk src/deep/b.js:1 @h2 = b',
             '%closing Wrap-up', '%beat Check', 'Prose. [[h1]]']))

    def raw_part(self, name, *lines):
        path = os.path.join(self.dir, name)
        with open(path, 'w') as f:
            f.write('\n'.join(lines))
        return path

    def part(self, name, title, hunk, note):
        path = os.path.join(self.dir, name)
        with open(path, 'w') as f:
            f.write('\n'.join(['%chapter ' + title, 'Intro.', '%blast narrow', 'E.',
                               '%beat Beat', note, '%hunk ' + hunk]))
        return path

    def splice(self, *parts):
        return self.sub.run(
            [sys.executable, os.path.join(self.root, 'bin', 'tour-splice.py'),
             self.patch, self.doc] + list(parts), capture_output=True, text=True)

    def check(self, *parts):
        return self.sub.run(
            [sys.executable, os.path.join(self.root, 'bin', 'tour-splice.py'),
             '--check', self.patch, self.doc] + list(parts),
            capture_output=True, text=True)

    def test_order_of_arguments_does_not_matter(self):
        self.skeleton()
        a = self.part('a', 'First topic', 'src/deep/a.js:10 = a', 'About A.')
        b = self.part('b', 'Second topic', 'src/deep/b.js:1 = b', 'About B.')
        r = self.splice(b, a)                       # deliberately reversed
        self.assertEqual(r.returncode, 0, r.stderr)
        body = self.read()
        self.assertLess(body.index('First topic'), body.index('Second topic'))
        self.assertIn('About A.', body)
        self.assertIn('About B.', body)

    def test_the_wrappers_are_left_alone(self):
        self.skeleton()
        r = self.splice(self.part('a', 'First topic', 'src/deep/a.js:10 = a', 'About A.'))
        self.assertEqual(r.returncode, 0, r.stderr)
        body = self.read()
        for d in ('%report T', '%intro Overview', '%closing Wrap-up'):
            self.assertIn(d, body)
        self.assertEqual(body.count('%chapter Second topic'), 1)

    def test_it_names_a_chapter_nobody_narrated(self):
        self.skeleton()
        r = self.splice(self.part('a', 'First topic', 'src/deep/a.js:10 = a', 'About A.'))
        self.assertIn('still un-narrated: Second topic', r.stderr)

    def test_a_labelled_chapter_round_trips_with_its_labels(self):
        self.labelled_skeleton()
        r = self.splice(self.raw_part(
            'a', '%chapter First topic', 'Now narrated.', '%blast narrow', 'E.',
            '%beat A', 'Prose.', '%hunk src/deep/a.js:10 @h1 = a', '  Its own prose.'))
        self.assertEqual(r.returncode, 0, r.stderr)
        body = self.read()
        self.assertIn('@h1', body)
        self.assertIn('[[h1]]', body)          # the closing's reference still has a target

    def test_a_chapter_file_that_dropped_a_label_is_refused(self):
        """A retyped directive loses its @hN, and a sibling's [[h1]] then dangles at
        build time — in prose whoever splices never read. Catch it at the seam."""
        self.labelled_skeleton()
        before = self.read()
        r = self.splice(self.raw_part(
            'a', '%chapter First topic', 'Now narrated.', '%beat A', 'Prose.',
            '%hunk src/deep/a.js:10 = a'))     # label retyped away
        self.assertEqual(r.returncode, 6)
        self.assertIn('drops label @h1', r.stderr)
        self.assertEqual(before, self.read())

    def test_a_chapter_file_that_does_not_parse_is_refused(self):
        self.skeleton()
        before = self.read()
        r = self.splice(self.raw_part(
            'a', '%chapter First topic', 'Intro.', '%beat A', 'Prose.',
            '%hunk src/deep/a.js:10 = a', 'Unindented prose.'))
        self.assertEqual(r.returncode, 6)
        self.assertIn('not attached to anything', r.stderr)
        self.assertIn('line 6', r.stderr)      # the fragment's own numbering
        self.assertEqual(before, self.read())

    def test_check_validates_without_writing(self):
        self.skeleton()
        before = self.read()
        part = self.part('a', 'First topic', 'src/deep/a.js:10 = a', 'About A.')
        r = self.check(part)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('check out', r.stderr)
        self.assertEqual(before, self.read())  # a fork must not write the narration

    def test_check_does_not_hold_whole_document_rules_against_a_fragment(self):
        """A chapter file has no %report and no %closing. That is not its problem."""
        self.skeleton()
        part = self.part('a', 'First topic', 'src/deep/a.js:10 = a', 'About A.')
        r = self.check(part)
        self.assertEqual(r.returncode, 0, r.stderr)
        for word in ('%report', '%closing', '%intro'):
            self.assertNotIn(word, r.stderr)

    def test_two_files_claiming_one_chapter_are_refused(self):
        """Last-wins would discard a fork's whole narration and still report success,
        while Step I is written from both forks' reports."""
        self.skeleton()
        before = self.read()
        a = self.raw_part('a', '%chapter First topic', 'VARIANT ONE.', '%beat A',
                          'Prose.', '%hunk src/deep/a.js:10 = a')
        b = self.raw_part('b', '%chapter First topic', 'VARIANT TWO.', '%beat A',
                          'Prose.', '%hunk src/deep/a.js:10 = a')
        r = self.splice(a, b)
        self.assertEqual(r.returncode, 6)
        self.assertIn('both claim chapter', r.stderr)
        self.assertEqual(before, self.read())

    def test_check_resolves_the_specs_a_fork_writes(self):
        """A fork adds quotes and splits its own hunks, so its specs are the only ones
        that can be wrong — and a parse-only check could not see any of them."""
        self.skeleton()
        for bad, want in (('%hunk src/deep/a.js:999 = no such hunk', 'no hunk at'),
                          ('%hunk src/deep/a.js:10 #1-999 = outside', 'outside this hunk')):
            part = self.raw_part('a', '%chapter First topic', 'Prose.', '%beat A',
                                 'Prose.', bad)
            r = self.check(part)
            self.assertEqual(r.returncode, 6, r.stderr)
            self.assertIn(want, r.stderr)

    def test_check_accepts_a_fork_that_split_its_own_hunk(self):
        self.skeleton()
        part = self.raw_part('a', '%chapter First topic', 'Prose.', '%beat A', 'Prose.',
                             '%hunk src/deep/a.js:10 #3-4 = first part',
                             '%hunk src/deep/a.js:10 #5-5 = second part')
        r = self.check(part)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_a_title_that_matches_nothing_is_refused(self):
        """The title is the splice key, so a wrong one is a content error (6), and it
        is caught before any file is placed rather than partway through."""
        self.skeleton()
        before = self.read()
        r = self.splice(self.part('a', 'Nonexistent', 'src/deep/a.js:10 = a', 'x'))
        self.assertEqual(r.returncode, 6)
        self.assertIn('matches no chapter', r.stderr)
        self.assertEqual(self.read(), before)

    def test_check_refuses_a_title_that_matches_nothing(self):
        """The failure --check existed for and did not catch: a fork that retitles its
        chapter passed its own check and failed at the orchestrator's splice."""
        self.skeleton()
        part = self.part('a', 'A better title', 'src/deep/a.js:10 = a', 'x')
        r = self.check(part)
        self.assertEqual(r.returncode, 6)
        self.assertIn('matches no chapter', r.stderr)

    def test_check_does_not_pass_a_retitled_file_that_also_dropped_labels(self):
        """A wrong title makes the label comparison impossible — there is no chapter to
        compare against — so it used to be skipped and the file reported clean with two
        mistakes in it. Refusing on the title is what stops that."""
        self.labelled_skeleton()
        part = self.raw_part('a', '%chapter Retitled', 'Prose.', '%beat A', 'Prose.',
                             '%hunk src/deep/a.js:10 = a')
        r = self.check(part)
        self.assertEqual(r.returncode, 6)
        self.assertIn('matches no chapter', r.stderr)

    def test_a_file_without_a_chapter_directive_is_refused(self):
        self.skeleton()
        path = os.path.join(self.dir, 'stray')
        with open(path, 'w') as f:
            f.write('%beat Orphan\nProse.\n')
        r = self.splice(path)
        self.assertEqual(r.returncode, 6)
        self.assertIn('does not begin with a chapter directive', r.stderr)

    def test_the_result_builds(self):
        self.skeleton()
        self.splice(self.part('a', 'First topic', 'src/deep/a.js:10 = a', 'About A.'),
                    self.part('b', 'Second topic', 'src/deep/b.js:1 = b', 'About B.'))
        r = self.build()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('all 5 changed lines shown', r.stderr)


class TestBuildCommand(_CommandCase):

    def test_a_good_narration_builds_and_prints_its_path(self):
        self.write('%beat A', 'P.', '%hunk src/deep/a.js:10 = a',
                   '%hunk src/deep/b.js:1 = b')
        r = self.build()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), os.path.abspath(self.out))
        self.assertTrue(os.path.exists(self.out))
        self.assertIn('all 5 changed lines shown', r.stderr)

    def test_a_half_narrated_document_still_builds(self):
        # Step F says write the whole skeleton first and narration.md says build after
        # every chapter, so most builds happen with later chapters still bare. If that
        # failed, the prescribed workflow would be impossible.
        self.raw('\n'.join(
            ['%report T', '%intro O', '%beat B', 'Prose.',
             '%chapter Narrated', 'Intro.', '%blast narrow', 'Evidence.',
             '%beat Done', 'Prose here.', '%hunk src/deep/a.js:10 = a',
             '%chapter Not yet', '%blast wide', '%beat Skeleton only',
             '%hunk src/deep/b.js:1 = b',
             '%closing W', '%beat W', 'P.']))
        r = self.build()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.exists(self.out))
        # It builds, and it says what is pending *with a line number* — a gate cannot
        # be held against something invisible.
        self.assertIn('still pending above', r.stderr)
        self.assertIn('pending line', r.stderr)
        self.assertIn('has no prose', r.stderr)

    def test_a_bad_narration_writes_nothing_and_exits_6(self):
        self.write('%beat A', 'P.', '%hunk src/deep/a.js:999 = nope')
        r = self.build()
        self.assertEqual(r.returncode, 6)
        self.assertFalse(os.path.exists(self.out))
        self.assertIn('Nothing written', r.stderr)

    def test_it_reports_every_problem_at_once(self):
        self.write('%beat A', 'P.', '%hunk src/deep/a.js:999 = one',
                   '%hunk src/deep/nope.js:1 = two', '%blast severe')
        r = self.build()
        self.assertGreaterEqual(r.stderr.count('error line'), 3, r.stderr)

    def test_it_says_how_much_is_still_unshown(self):
        self.write('%beat A', 'P.', '%hunk src/deep/a.js:10 = a')
        r = self.build()
        self.assertEqual(r.returncode, 0)
        self.assertIn('3 of 5 changed lines shown', r.stderr)
        self.assertIn('tour-rest.py', r.stderr)

    def test_the_header_names_the_project_not_the_worktree(self):
        """The ordinary PR flow points --root at a worktree under /tmp, whose directory
        name is a temp name. The reader's "which project is this" line must not be it."""
        d = self._checkout()
        wt = os.path.join(self.dir, 'difftour-deadbeef')
        head = subprocess.run(['git', '-C', d, 'rev-parse', 'HEAD'],
                              capture_output=True, text=True).stdout.strip()
        subprocess.run(['git', '-C', d, 'worktree', 'add', '--detach', '-q', wt, head],
                       capture_output=True, text=True)
        self.addCleanup(subprocess.run,
                        ['git', '-C', d, 'worktree', 'remove', '--force', wt],
                        capture_output=True)
        with open(self.patch + '.head', 'w') as f:
            f.write(head + '\n')
        self.write('%beat A', 'P.', '%hunk src/deep/a.js:10 = a',
                   '%hunk src/deep/b.js:1 = b')
        r = self.build('--root', wt)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(self.out) as f:
            html = f.read()
        meta = html[html.index('<p class="meta">'):html.index('</p>')]
        self.assertIn('<b>co</b>', meta)             # the repository the worktree is of
        self.assertNotIn('difftour-deadbeef', meta)

    def test_final_refuses_a_report_with_an_unshown_line(self):
        """The last gate. Every other exit code is 0 in this state, by design."""
        self.write('%beat A', 'P.', '%hunk src/deep/a.js:10 = a')   # b.js unshown
        r = self.build('--final')
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn('not a report to hand over', r.stderr)
        self.assertIn('1 unshown place', r.stderr)
        # No path on stdout: the one thing you would hand over must not be there.
        self.assertEqual('', r.stdout.strip())
        # The file is still written, so it can be looked at.
        self.assertTrue(os.path.exists(self.out))

    def test_final_refuses_a_report_with_pending_prose(self):
        self.write('%beat A', '%hunk src/deep/a.js:10 = a',
                   '%hunk src/deep/b.js:1 = b')                     # no beat prose
        r = self.build('--final')
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn('pending', r.stderr)
        self.assertEqual('', r.stdout.strip())

    def test_final_prints_the_path_when_the_report_is_whole(self):
        self.write('%beat A', 'P.', '%hunk src/deep/a.js:10 = a',
                   '%hunk src/deep/b.js:1 = b')
        r = self.build('--final')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(self.out, r.stdout)

    def test_without_final_an_unfinished_report_still_builds(self):
        """Most builds happen mid-narration; refusing them would break the workflow."""
        self.write('%beat A', 'P.', '%hunk src/deep/a.js:10 = a')
        r = self.build()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(self.out, r.stdout)

    def test_the_header_names_no_branch_when_the_checkout_is_not_this_diff(self):
        # Touring someone else's PR from a checkout on master must not print "master".
        d = self._checkout()
        with open(self.patch + '.head', 'w') as f:
            f.write('0' * 40 + '\n')
        self.write('%beat A', 'P.', '%hunk src/deep/a.js:10 = a',
                   '%hunk src/deep/b.js:1 = b')
        r = self.build('--root', d)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(self.out) as f:
            meta = f.read()
        # Neither is claimed: naming an unrelated repository is as wrong as naming its
        # branch, and running from the wrong directory is how that happens.
        self.assertNotIn('<b>co</b>', meta)
        self.assertNotIn('<b>master</b>', meta)
        self.assertNotIn('<b>main</b>', meta)

    def test_the_header_names_no_branch_when_no_head_was_recorded(self):
        """No proof, no claim — the other half of the rule above.

        A patch from elsewhere has no .head, so the checkout's branch is unverifiable
        and must not be printed. This used to print it unconditionally, which is the
        same wrong fact the test above prevents, reached by the other route.
        """
        d = self._checkout()
        if os.path.exists(self.patch + '.head'):
            os.unlink(self.patch + '.head')
        self.write('%beat A', 'P.', '%hunk src/deep/a.js:10 = a',
                   '%hunk src/deep/b.js:1 = b')
        r = self.build('--root', d)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(self.out) as f:
            html = f.read()
        meta = html[html.index('<p class="meta">'):html.index('</p>')]
        self.assertNotIn('<b>co</b>', meta)
        branch = subprocess.run(['git', '-C', d, 'rev-parse', '--abbrev-ref', 'HEAD'],
                                capture_output=True, text=True).stdout.strip()
        self.assertNotIn('<b>%s</b>' % branch, meta)

    def test_the_header_claims_nothing_when_root_is_not_a_repository(self):
        d = os.path.join(self.dir, 'plain')
        os.makedirs(d, exist_ok=True)
        self.write('%beat A', 'P.', '%hunk src/deep/a.js:10 = a',
                   '%hunk src/deep/b.js:1 = b')
        r = self.build('--root', d)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(self.out) as f:
            html = f.read()
        meta = html[html.index('<p class="meta">'):html.index('</p>')]
        self.assertNotIn('plain', meta)

    def test_a_patch_with_two_hunks_at_one_line_is_refused(self):
        with open(self.patch) as f:
            doubled = f.read()
        with open(self.patch, 'w') as f:
            f.write(doubled + doubled)
        self.write('%beat A', 'P.', '%hunk src/deep/a.js:10 = a')
        r = self.build()
        self.assertEqual(r.returncode, 2)
        self.assertIn('same line in one file', r.stderr)

    def test_a_missing_narration_file_is_an_argument_error(self):
        r = self.sub.run(
            [sys.executable, os.path.join(self.root, 'bin', 'tour-build.py'),
             self.patch, os.path.join(self.dir, 'nope.tour'), self.out],
            capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn('no such narration file', r.stderr)

    def _checkout(self):
        """A throwaway git repo to point --root at, so this test does not depend on
        where the skill itself happens to live."""
        d = os.path.join(self.dir, 'co')
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, 'quoted.js'), 'w') as f:
            f.write('line one\nline two\nline three\n')
        for args in (['init', '-q'], ['add', 'quoted.js'],
                     ['-c', 'user.email=t@t', '-c', 'user.name=t',
                      'commit', '-qm', 'x']):
            self.sub.run(['git', '-C', d] + args, capture_output=True)
        return d

    def test_it_warns_when_a_quote_would_read_the_wrong_checkout(self):
        # tour-fetch.sh records the commit a diff ends at; a %quote reads the
        # checkout, so the two disagreeing means the quote is byte-exact from the
        # wrong version of the file.
        with open(self.patch + '.head', 'w') as f:
            f.write('0' * 40 + '\n')
        self.write('%beat A', 'P.', '%hunk src/deep/a.js:10 = a',
                   '%hunk src/deep/b.js:1 = b',
                   '%quote quoted.js:1-2 = the top of the file')
        r = self.build('--root', self._checkout())
        self.assertIn('reads its lines from the wrong version', r.stderr)
        self.assertIn('warning', r.stderr)              # counted, not merely printed

    def test_final_refuses_a_quote_read_from_the_wrong_checkout(self):
        """The one way wrong *content* could reach a reader past a passing build.

        Every other hazard is refused or warned; this one used to print and exit 0, so
        --final called the report whole while its quotes came from another version.
        """
        with open(self.patch + '.head', 'w') as f:
            f.write('0' * 40 + '\n')
        self.write('%beat A', 'P.', '%hunk src/deep/a.js:10 = a',
                   '%hunk src/deep/b.js:1 = b',
                   '%quote quoted.js:1-2 = the top of the file')
        r = self.build('--root', self._checkout(), '--final')
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertEqual('', r.stdout.strip())          # no path to hand over

    def test_it_does_not_warn_when_there_is_no_recorded_head(self):
        self.write('%beat A', 'P.', '%hunk src/deep/a.js:10 = a',
                   '%hunk src/deep/b.js:1 = b',
                   '%quote quoted.js:1-2 = the top of the file')
        r = self.build('--root', self._checkout())
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn('wrong version', r.stderr)


class TestCheckoutCommand(unittest.TestCase):
    """bin/tour-checkout.sh — the step that stops quotes and greps reading the wrong code.

    Real repositories, because the whole point is what git does with a commit that is not
    HEAD, and a fake cannot be wrong in the way that matters.
    """

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.repo = os.path.join(self.dir, 'r')
        os.makedirs(self.repo)
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.email', 't@t')
        self.git('config', 'user.name', 'T')
        self.commits = []
        for text in ('one\n', 'two\n', 'three\n'):
            with open(os.path.join(self.repo, 'f.txt'), 'w') as f:
                f.write(text)
            self.git('add', '-A')
            self.git('commit', '-q', '-m', text.strip())
            self.commits.append(self.git('rev-parse', 'HEAD').strip())

    def git(self, *args):
        return subprocess.run(['git', '-C', self.repo] + list(args),
                              capture_output=True, text=True).stdout

    def run_it(self, head=None, patch='p.patch'):
        path = os.path.join(self.dir, patch)
        with open(path, 'w') as f:
            f.write('')                     # content is irrelevant; only .head is read
        if head is not None:
            with open(path + '.head', 'w') as f:
                f.write(head + '\n')
        r = subprocess.run(
            ['bash', os.path.join(self.root, 'bin', 'tour-checkout.sh'), path],
            capture_output=True, text=True, cwd=self.repo,
            env=dict(os.environ, TOUR_REPO=self.repo, TMPDIR=self.dir))
        return r

    def test_it_uses_the_repository_when_head_already_matches(self):
        r = self.run_it(self.commits[-1])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(os.path.realpath(self.repo),
                         os.path.realpath(r.stdout.strip()))
        self.assertIn('already at', r.stderr)

    def test_it_makes_a_worktree_at_the_commit_the_diff_ends_at(self):
        """The core case: an ordinary range that does not end at HEAD."""
        r = self.run_it(self.commits[0])
        self.assertEqual(r.returncode, 0, r.stderr)
        out = r.stdout.strip()
        self.assertNotEqual(os.path.realpath(self.repo), os.path.realpath(out))
        at = subprocess.run(['git', '-C', out, 'rev-parse', 'HEAD'],
                            capture_output=True, text=True).stdout.strip()
        self.assertEqual(self.commits[0], at)
        # And the file there is the old version — which is the whole point.
        with open(os.path.join(out, 'f.txt')) as f:
            self.assertEqual('one\n', f.read())

    def test_it_leaves_the_working_tree_and_branch_alone(self):
        before = self.git('rev-parse', 'HEAD').strip()
        branch = self.git('rev-parse', '--abbrev-ref', 'HEAD').strip()
        self.run_it(self.commits[0])
        self.assertEqual(before, self.git('rev-parse', 'HEAD').strip())
        self.assertEqual(branch, self.git('rev-parse', '--abbrev-ref', 'HEAD').strip())
        self.assertEqual('', self.git('status', '--porcelain').strip())

    def test_it_works_with_uncommitted_changes_in_the_way(self):
        """A branch switch could not do this, which is why it is a worktree."""
        with open(os.path.join(self.repo, 'f.txt'), 'w') as f:
            f.write('dirty\n')
        r = self.run_it(self.commits[0])
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(os.path.join(self.repo, 'f.txt')) as f:
            self.assertEqual('dirty\n', f.read())      # still theirs

    def test_it_is_idempotent(self):
        first = self.run_it(self.commits[0]).stdout.strip()
        again = self.run_it(self.commits[0])
        self.assertEqual(first, again.stdout.strip())
        self.assertIn('reusing', again.stderr)

    def test_a_patch_with_no_recorded_head_is_reported_not_guessed(self):
        r = self.run_it(None)
        self.assertEqual(r.returncode, 3)
        self.assertEqual('', r.stdout.strip())          # nothing to carry forward
        self.assertIn('%quote', r.stderr)

    def test_an_unfetchable_commit_asks_for_a_human(self):
        r = self.run_it('0' * 40)
        self.assertEqual(r.returncode, 4)
        self.assertEqual('', r.stdout.strip())
        self.assertIn('needs a human', r.stderr)


class TestTheDocsAgreeWithTheCode(unittest.TestCase):
    """The documentation is read by every fork, so drift in it is drift in the tour.

    Three times in one day a rule changed and its example did not. These are the two
    places where a doc makes a claim a test can hold it to.
    """

    SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_the_worked_example_in_the_narration_reference_parses(self):
        """The one example every fork imitates has to be a legal narration file.

        It was not: it showed prose unindented under a %hunk, which is fatal. A fork
        copying that shape fails at the orchestrator's build, in prose the
        orchestrator never read — so this asserts the example, not a copy of it.
        """
        with open(os.path.join(self.SKILL, 'references', 'narration.md'),
                  encoding='utf-8') as f:
            doc = f.read()
        body = doc.split('## Example', 1)[1].split('\n##', 1)[0]
        # The example is an indented code block. Take exactly those lines, dedented.
        text = '\n'.join(l[4:] if l.startswith('    ') else l
                          for l in body.split('\n')
                          if not l.strip() or l.startswith('    '))
        self.assertIn('%report', text, 'the example moved; this test cannot find it')
        rep, problems = narration.parse(text)
        real = [str(x) for x in problems
                if x.fatal and not (x.premature or x.needs_labels)]
        self.assertEqual([], real)
        # And it must model the reference style it documents: labels, not codes.
        self.assertIn('[[h1]]', text)
        self.assertNotRegex(text, r'`\d+\.\d+`')

    def test_the_design_fixture_shows_the_real_standfirst(self):
        """layout.html opens standalone and promises it looks like a report."""
        with open(os.path.join(self.SKILL, 'assets', 'layout.html'),
                  encoding='utf-8') as f:
            fixture = f.read()
        shown = re.search(r'<p class="standfirst">(.*?)</p>', fixture, re.S).group(1)
        self.assertEqual(' '.join(render.STANDFIRST.split()),
                         ' '.join(shown.split()))


if __name__ == '__main__':
    unittest.main(verbosity=2)
