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

    def test_assemble_splices_escaped_hunks_and_appends_unplaced_ones(self):
        frag1 = os.path.join(self.dir, 't1.html')
        frag2 = os.path.join(self.dir, 't2.html')
        with open(frag1, 'w') as f:
            f.write('<h1>Tour</h1>\n<section><h2>Topic one</h2>\n<p>desc</p>\n<!-- hunk h1 -->\n'
                    '<p><strong>Fishiness: high</strong> odd</p>\n<!--hunk h99-->\n</section>\n')
        with open(frag2, 'w') as f:
            f.write('<section><h2>Topic two</h2>\n<!-- hunk h3 -->\n</section>\n')
        out_path = os.path.join(self.dir, 'tour.html')
        code, out, err = hunks(self.dir, '--assemble', out_path, '--', 'HEAD', '++', frag1, frag2)
        self.assertEqual(code, 0, err)
        page = read(out_path)
        self.assertTrue(page.startswith('<!doctype html>'))
        self.assertIn('<h1>Tour</h1>', page)
        self.assertIn('<pre data-hunk="h1">', page)
        self.assertIn('+CHANGED &lt;b&gt;&amp;', page)          # escaped, not raw
        self.assertNotIn('<!-- hunk h1 -->', page)
        self.assertIn('Unknown hunk h99', page)
        self.assertIn('<h2>Unsorted hunks</h2>', page)
        self.assertIn('<pre data-hunk="h2">', page)
        self.assertIn('<pre data-hunk="h4">', page)
        self.assertIn('h2 h4', err)
        self.assertIn('h99', err)
        self.assertIn('(4 hunks, 2 placed by fragments, 2 appended)', out)
        # Topic order follows fragment order.
        self.assertLess(page.index('Topic one'), page.index('Topic two'))
        self.assertLess(page.index('Topic two'), page.index('Unsorted hunks'))

    def test_assemble_without_gaps_is_quiet(self):
        frag = os.path.join(self.dir, 't.html')
        with open(frag, 'w') as f:
            f.write('<!-- hunk h1 --><!-- hunk h2 --><!-- hunk h3 --><!-- hunk h4 -->')
        out_path = os.path.join(self.dir, 'tour.html')
        code, out, err = hunks(self.dir, '--assemble', out_path, '--', 'HEAD', '++', frag)
        self.assertEqual(code, 0, err)
        self.assertEqual(err, '')
        self.assertNotIn('Unsorted hunks', read(out_path))

    def test_missing_double_dash_prints_usage(self):
        code, out, err = hunks(self.dir, 'HEAD')
        self.assertEqual(code, 2)
        self.assertIn('vibe-hunks.py', err)


if __name__ == '__main__':
    unittest.main()
