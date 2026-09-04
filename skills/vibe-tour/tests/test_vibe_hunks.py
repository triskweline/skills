#!/usr/bin/env python3
"""Tests for bin/vibe-hunks.py. Run from the skill directory: python3 tests/test_vibe_hunks.py"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(SKILL, 'bin', 'vibe-hunks.py')


def sh(cwd, *cmd, **kw):
    return subprocess.run(list(cmd), cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, **kw)


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def hunks(cwd, *args):
    r = sh(cwd, sys.executable, SCRIPT, *args)
    return r.returncode, r.stdout, r.stderr


class Repo(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='vibe-hunks-')
        d = self.dir
        sh(d, 'git', 'init', '-q', '-b', 'main')
        sh(d, 'git', 'config', 'user.email', 't@example.com')
        sh(d, 'git', 'config', 'user.name', 'T')
        self.write('a.py', 'line1\nline2\nline3\nline4\nline5\nline6\nline7\nline8\nline9\nline10\n')
        self.write('b.txt', 'hello\n')
        self.write('bin.dat', b'\x00\x01\x02')
        sh(d, 'git', 'add', '.')
        sh(d, 'git', 'commit', '-q', '-m', 'base')
        # Two hunks in a.py, one in b.txt, a binary change, an untracked file.
        self.write('a.py', 'line1\nCHANGED <b>&\nline3\nline4\nline5\nline6\nline7\nline8\nline9\nline10 tail\n')
        self.write('b.txt', 'hello world\n')
        self.write('bin.dat', b'\x00\x01\x03')
        self.write('new.txt', 'brand new\n')

    def tearDown(self):
        shutil.rmtree(self.dir)

    def write(self, name, content):
        mode = 'wb' if isinstance(content, bytes) else 'w'
        with open(os.path.join(self.dir, name), mode) as f:
            f.write(content)

    def test_full_read_numbers_every_hunk_and_binary_file(self):
        code, out, err = hunks(self.dir, '--', 'HEAD')
        self.assertEqual(code, 0, err)
        markers = re.findall(r'^### (h\d+)  (\S+)(.*)$', out, re.M)
        self.assertEqual([m[0] for m in markers], ['h1', 'h2', 'h3', 'h4'])
        self.assertEqual(markers[0][1], 'a.py:1')
        self.assertEqual(markers[1][1], 'a.py:7')
        self.assertEqual(markers[2][1], 'b.txt:1')
        self.assertEqual(markers[3][1], 'bin.dat')
        self.assertIn('no text hunk', markers[3][2])
        self.assertIn('+CHANGED <b>&', out)
        # The file header appears once per file, not once per hunk.
        self.assertEqual(out.count('diff --git a/a.py b/a.py'), 1)

    def test_ids_prints_only_markers(self):
        code, out, err = hunks(self.dir, '--ids', '--', 'HEAD')
        self.assertEqual(code, 0, err)
        lines = out.strip().splitlines()
        self.assertEqual(len(lines), 4)
        self.assertTrue(all(l.startswith('### h') for l in lines))

    def test_untracked_files_are_numbered_as_additions(self):
        code, out, err = hunks(self.dir, '--ids', '--untracked', '--', 'HEAD')
        self.assertEqual(code, 0, err)
        self.assertIn('### h5  new.txt:1', out)
        code, out, err = hunks(self.dir, '--only', 'h5', '--untracked', '--', 'HEAD')
        self.assertIn('+brand new', out)
        self.assertIn('diff --git a/new.txt b/new.txt', out)

    def test_only_selects_hunks_with_their_file_header(self):
        code, out, err = hunks(self.dir, '--only', 'h2,h3', '--', 'HEAD')
        self.assertEqual(code, 0, err)
        self.assertIn('### h2', out)
        self.assertIn('### h3', out)
        self.assertNotIn('### h1', out)
        self.assertIn('+line10 tail', out)
        self.assertNotIn('+CHANGED', out)
        self.assertIn('diff --git a/b.txt b/b.txt', out)

    def test_staged_diff_uses_git_diff_arguments_verbatim(self):
        sh(self.dir, 'git', 'add', 'b.txt')
        code, out, err = hunks(self.dir, '--ids', '--', '--cached')
        self.assertEqual(code, 0, err)
        self.assertEqual(out.strip().splitlines(), ['### h1  b.txt:1'])

    def assemble(self, *frags):
        paths = []
        for n, body in enumerate(frags):
            path = os.path.join(self.dir, 't%d.html' % n)
            with open(path, 'w') as f:
                f.write(body)
            paths.append(path)
        out_path = os.path.join(self.dir, 'tour.html')
        code, out, err = hunks(self.dir, '--assemble', out_path, '--', 'HEAD', '++', *paths)
        self.assertEqual(code, 0, err)
        return read(out_path), out, err

    def test_assemble_lays_out_chapters_beats_and_escaped_hunks(self):
        page, out, err = self.assemble(
            '<h1>Tour <code>x</code></h1>\n<p>The summary.</p>\n',
            '<section id="topic-1">\n<h2>1. Topic one</h2>\n<p>Chapter intro.</p>\n'
            '<h3>1.1 First beat</h3>\n<p>Beat prose.</p>\n'
            '<p>Desc of h1.</p>\n<!-- hunk h1 -->\n'
            '<!-- hunk h3 fishy: the greeting lost its exclamation -->\n<p>Desc of h3.</p>\n'
            '</section>\n')
        self.assertTrue(page.startswith('<!doctype html>'))
        self.assertIn('<title>Tour x</title>', page)
        self.assertIn('<h1>Tour <code>x</code></h1>', page)
        self.assertIn('<div class="summary"><p>The summary.</p></div>', page)
        self.assertIn('<h2><span class="n">1</span><span class="t">Topic one</span></h2>', page)
        self.assertIn('<div class="intro"><p>Chapter intro.</p></div>', page)
        self.assertIn('<h3>First beat</h3>', page)
        self.assertIn('<p>Beat prose.</p>', page)
        # Prose before a placeholder belongs to the beat; prose after it is the hunk's note.
        self.assertRegex(page, r'(?s)<div class="say">[^<]*<h3>First beat</h3>.*Beat prose.*Desc of h1.*</div><div class="show">')
        self.assertIn('<div class="note"><p>Desc of h3.</p></div>\n<figure class="hunk lvl-fishy" id="h3"', page)
        self.assertIn('data-level="3" data-reason="the greeting lost its exclamation"', page)
        self.assertIn('<figcaption><span class="lvl">fishy</span><span class="where">b.txt:1', page)
        self.assertIn('<aside class="flag fishy"><p>the greeting lost its exclamation</p></aside>', page)
        self.assertIn('<figure class="hunk lvl-plain" id="h1" data-key="', page)
        self.assertIn('data-level="1"', page)
        self.assertIn('<figcaption><span class="lvl">read</span><span class="where">a.py:1', page)
        self.assertIn('language-diff-python diff-highlight', page)
        self.assertIn('+CHANGED &lt;b&gt;&amp;', page)
        self.assertNotIn('<!-- hunk h1 -->', page)
        self.assertNotIn('<section id="topic-1">', page)
        # The rest of the diff is appended so nothing is hidden, and it is reported.
        self.assertIn('<span class="t">Unsorted hunks</span>', page)
        self.assertIn('id="h2"', page)
        self.assertIn('class="hunk lvl-plain file" id="h4"', page)
        self.assertIn('A binary file', page)
        self.assertIn('h2 h4', err)
        self.assertIn('(4 hunks, 2 placed by fragments, 2 appended)', out)
        self.assertTrue(out.startswith('file:///'), out)
        self.assertIn(out_path if False else 'tour.html', out)
        # Assets are inlined: no external requests.
        self.assertIn('window.Prism', page)
        self.assertIn('.heat .sq', page)
        self.assertNotIn('src="../vendor', page)
        self.assertNotIn('the page shell', page)

    def test_meta_line_counts_the_diff(self):
        page, out, err = self.assemble('<h1>T</h1>', '<h2>A</h2><!-- hunk h1 --><!-- hunk h2 --><!-- hunk h3 --><!-- hunk h4 -->')
        self.assertRegex(page, r'(?s)<p class="meta">.*<b>3</b> files.*<b class="added">\+3</b> <b class="removed">−3</b>.*<b>4</b> hunks.*<code>HEAD</code>')
        self.assertEqual(err, '')
        self.assertNotIn('Unsorted hunks', page)

    def test_unknown_and_duplicate_placeholders_are_reported(self):
        page, out, err = self.assemble(
            '<h2>A</h2><!-- hunk h1 --><!--hunk h99-->',
            '<h2>B</h2><!-- hunk h1 --><!-- hunk h2 --><!-- hunk h3 --><!-- hunk h4 -->')
        self.assertIn('Unknown hunk h99', page)
        self.assertIn('h99', err)
        self.assertIn('placed more than once', err)
        self.assertIn('id="h1"', page)
        self.assertIn('id="h1-2"', page)
        self.assertLess(page.index('<span class="t">A</span>'), page.index('<span class="t">B</span>'))

    def test_worker_shortcuts_are_tolerated(self):
        # No <h2>, bare paragraphs, hunks before any <h3>.
        page, out, err = self.assemble(
            'Intro line.\n\n<!-- hunk h1 -->\nabout h1\n<h3>Later</h3>\n<!-- hunk h2 --><!-- hunk h3 --><!-- hunk h4 -->')
        self.assertIn('<span class="t">Topic 1</span>', page)
        self.assertIn('<div class="intro"><p>Intro line.</p></div>', page)
        self.assertIn('<div class="note"><p>about h1</p></div>', page)
        self.assertIn('<h3>Later</h3>', page)

    def test_a_directory_expands_to_its_fragments_in_path_order(self):
        work = os.path.join(self.dir, 'work')
        os.makedirs(os.path.join(work, 'topic-01'))
        os.makedirs(os.path.join(work, 'topic-02'))
        with open(os.path.join(work, '00-intro.html'), 'w') as f:
            f.write('<h1>Dir tour</h1><p>Sum.</p>')
        with open(os.path.join(work, 'topic-02', 'fragment.html'), 'w') as f:
            f.write('<h2>Second</h2><!-- hunk h3 --><!-- hunk h4 -->')
        with open(os.path.join(work, 'topic-01', 'fragment.html'), 'w') as f:
            f.write('<h2>First</h2><!-- hunk h1 --><!-- hunk h2 -->')
        out_path = os.path.join(work, 'vibe-tour.html')
        for _ in range(2):   # the second run must not ingest the first run's output
            code, out, err = hunks(self.dir, '--assemble', out_path, '--', 'HEAD', '++', work)
            self.assertEqual(code, 0, err)
            self.assertEqual(err, '')
        page = read(out_path)
        self.assertIn('<h1>Dir tour</h1>', page)
        self.assertLess(page.index('<span class="t">First</span>'), page.index('<span class="t">Second</span>'))
        self.assertEqual(page.count('<h1>'), 1)

    def test_function_context_becomes_a_row_above_the_diff(self):
        # A change below a declaration: git puts the declaration after the second @@.
        self.write('m.py', 'def alpha():\n    a = 1\n    b = 2\n    c = 3\n    d = 4\n    e = 5\n    f = 6\n    return a\n')
        sh(self.dir, 'git', 'add', 'm.py')
        sh(self.dir, 'git', 'commit', '-q', '-m', 'm')
        self.write('m.py', 'def alpha():\n    a = 1\n    b = 2\n    c = 3\n    d = 4\n    e = 55\n    f = 6\n    return a\n')
        code, out, err = hunks(self.dir, '--ids', '--', 'HEAD', '--', 'm.py')
        self.assertEqual(out.strip(), '### h1  m.py:3', err)
        frag = os.path.join(self.dir, 'f.html')
        with open(frag, 'w') as f:
            f.write('<h2>A</h2><!-- hunk h1 -->')
        out_path = os.path.join(self.dir, 'tour.html')
        code, out, err = hunks(self.dir, '--assemble', out_path, '--', 'HEAD', '--', 'm.py', '++', frag)
        self.assertEqual(code, 0, err)
        page = read(out_path)
        self.assertIn('<div class="ctx">def alpha():</div>\n<pre class="diff">', page)
        # The @@ line itself is not shown; the diff starts with the first context line.
        self.assertNotIn('@@ -3,6', page)
        self.assertIn('diff-highlight">     b = 2\n', page)
        # A hunk starting at line 1 has no declaration above it and gets no row; the
        # second hunk in the same file does (git's default heuristic picks "line6").
        page, out, err = self.assemble('<h2>A</h2><!-- hunk h1 --><!-- hunk h2 --><!-- hunk h3 --><!-- hunk h4 -->')
        self.assertNotIn('@@ -1,3', page)
        h1 = re.search(r'<figure class="hunk lvl-plain" id="h1".*?</figure>', page, re.S).group(0)
        self.assertNotIn('<div class="ctx">', h1)
        h2 = re.search(r'<figure class="hunk lvl-plain" id="h2".*?</figure>', page, re.S).group(0)
        self.assertIn('<div class="ctx">line6</div>', h2)

    def test_each_tour_gets_its_own_uid_for_viewed_marks(self):
        frag = os.path.join(self.dir, 'f.html')
        with open(frag, 'w') as f:
            f.write('<h2>A</h2><!-- hunk h1 --><!-- hunk h2 --><!-- hunk h3 --><!-- hunk h4 -->')
        uids = []
        for name in ('one', 'two', 'one'):
            out_path = os.path.join(self.dir, name, 'vibe-tour.html')
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            code, out, err = hunks(self.dir, '--assemble', out_path, '--', 'HEAD', '++', frag)
            self.assertEqual(code, 0, err)
            uids.append(re.search(r'data-uid="([0-9a-f]+)"', read(out_path)).group(1))
        self.assertNotEqual(uids[0], uids[1])   # a different tour, different marks
        self.assertEqual(uids[0], uids[2])      # the same tour re-assembled keeps its marks
        self.assertNotEqual(uids[0], 'fixture')

    def test_fishy_without_reason_gets_a_default(self):
        page, out, err = self.assemble('<h2>A</h2><!-- hunk h1 fishy --><!-- hunk h2 --><!-- hunk h3 --><!-- hunk h4 -->')
        self.assertIn('<aside class="flag fishy"><p>Please check this change.</p></aside>', page)

    def test_all_five_levels_render(self):
        page, out, err = self.assemble(
            '<h2>A</h2>\n<!-- hunk h1 skip -->\n<!-- hunk h2 note: a default worth a conscious yes -->\n'
            '<!-- hunk h3 HOT: verification runs on every request -->\n<!-- hunk h4 -->')
        self.assertEqual(err, '')
        self.assertIn('<figure class="hunk lvl-skip" id="h1" data-key="', page)
        self.assertIn('data-level="0"', page)
        self.assertIn('<span class="lvl">skip</span>', page)
        self.assertNotIn('<aside class="flag skip"', page)
        self.assertIn('<figure class="hunk lvl-note" id="h2"', page)
        self.assertIn('<aside class="flag note"><p>a default worth a conscious yes</p></aside>', page)
        self.assertIn('<figure class="hunk lvl-hot" id="h3"', page)
        self.assertIn('data-level="4" data-reason="verification runs on every request"', page)
        self.assertIn('<aside class="flag hot"><p>verification runs on every request</p></aside>', page)
        self.assertIn('<figure class="hunk lvl-plain file" id="h4"', page)
        # Reasons are escaped into the attribute and the aside alike.
        page, out, err = self.assemble('<h2>A</h2><!-- hunk h1 note: uses <b> & "quotes" --><!-- hunk h2 --><!-- hunk h3 --><!-- hunk h4 -->')
        self.assertIn('data-reason="uses &lt;b&gt; &amp; &quot;quotes&quot;"', page)
        self.assertIn('<p>uses &lt;b&gt; &amp; &quot;quotes&quot;</p>', page)

    def test_missing_double_dash_prints_usage(self):
        code, out, err = hunks(self.dir, 'HEAD')
        self.assertEqual(code, 2)
        self.assertIn('vibe-hunks.py', err)


if __name__ == '__main__':
    unittest.main()
