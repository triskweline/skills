"""Which Prism grammar highlights which file, and the vendored bundle.

Prism is vendored in the skill rather than loaded from a CDN, so a report opens
with full colour from a local file with no network.

The whole set is inlined into every report. Subsetting it per report saves about
85 KB against a report that is already hundreds of KB, and costs an extension
scan, a require-chain resolver, and a bug class where the chain is wrong for one
language. GRAMMARS below is that resolution, done once: Prism 1.30.0's own
components.json require graph, topologically sorted. Regenerate it if the
vendored set changes.

A grammar Prism does not have is not an error: the diff plugin falls back to
plain text with the +/- markers intact, and so does JavaScript being switched
off. A diff is readable either way.

Known limitation, and not a bug to chase: a token that opens above the hunk, or
spans a context run and a changed run, colours wrong. The plugin highlights each
run of same-sign lines as its own unit, so it cannot see a template literal or
block comment that began outside the run. Every diff highlighter has this.
"""

import os
import re

# lib/difftour/code.py -> lib/difftour -> lib -> the skill root
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

VENDOR = os.path.join(_ROOT, 'vendor', 'prism')

GRAMMARS = [
    'bash', 'clike', 'c', 'javascript', 'coffeescript', 'cpp', 'csharp', 'css', 'diff',
    'docker', 'elixir', 'ruby', 'markup', 'markup-templating', 'erb', 'go', 'graphql',
    'groovy', 'haml', 'handlebars', 'hcl', 'http', 'ini', 'java', 'json', 'jsx', 'kotlin',
    'less', 'liquid', 'lua', 'makefile', 'markdown', 'nginx', 'perl', 'php', 'powershell',
    'protobuf', 'python', 'r', 'regex', 'rust', 'scala', 'scss', 'sql', 'swift', 'toml',
    'typescript', 'tsx', 'twig', 'yaml',
]

# File suffix (lowercased) -> Prism language. Anything absent gets no grammar,
# which Prism's diff plugin degrades to plain text with the +/- markers intact.
BY_SUFFIX = {
    'js': 'javascript', 'mjs': 'javascript', 'cjs': 'javascript',
    'jsx': 'jsx', 'ts': 'typescript', 'tsx': 'tsx', 'mts': 'typescript',
    'coffee': 'coffeescript',
    'html': 'markup', 'htm': 'markup', 'xml': 'markup', 'svg': 'markup',
    'vue': 'markup', 'xhtml': 'markup', 'plist': 'markup', 'xsd': 'markup',
    'css': 'css', 'scss': 'scss', 'sass': 'scss', 'less': 'less',
    'rb': 'ruby', 'rake': 'ruby', 'gemspec': 'ruby', 'ru': 'ruby',
    'erb': 'erb', 'haml': 'haml',
    'py': 'python', 'pyi': 'python',
    'php': 'php', 'java': 'java', 'kt': 'kotlin', 'kts': 'kotlin',
    'swift': 'swift', 'scala': 'scala', 'sbt': 'scala',
    'groovy': 'groovy', 'gradle': 'groovy',
    'go': 'go', 'rs': 'rust',
    'c': 'c', 'h': 'c', 'cpp': 'cpp', 'cc': 'cpp', 'cxx': 'cpp',
    'hpp': 'cpp', 'hh': 'cpp', 'cs': 'csharp',
    'lua': 'lua', 'pl': 'perl', 'pm': 'perl', 'r': 'r',
    'ex': 'elixir', 'exs': 'elixir',
    'sql': 'sql', 'graphql': 'graphql', 'gql': 'graphql',
    'sh': 'bash', 'bash': 'bash', 'zsh': 'bash', 'ksh': 'bash',
    'ps1': 'powershell', 'psm1': 'powershell',
    'json': 'json', 'jsonc': 'json', 'json5': 'json', 'geojson': 'json',
    'yaml': 'yaml', 'yml': 'yaml', 'toml': 'toml',
    'ini': 'ini', 'cfg': 'ini', 'conf': 'ini', 'properties': 'ini',
    'tf': 'hcl', 'tfvars': 'hcl', 'hcl': 'hcl', 'proto': 'protobuf',
    'md': 'markdown', 'markdown': 'markdown', 'mdx': 'markdown',
    'hbs': 'handlebars', 'twig': 'twig', 'liquid': 'liquid',
    'http': 'http', 'diff': 'diff', 'patch': 'diff',
}

# Extensionless files whose name says what they are.
BY_NAME = {
    'dockerfile': 'docker', 'containerfile': 'docker',
    'makefile': 'makefile', 'gnumakefile': 'makefile', 'rakefile': 'ruby',
    'gemfile': 'ruby', 'guardfile': 'ruby', 'brewfile': 'ruby',
    'vagrantfile': 'ruby', 'podfile': 'ruby', 'capfile': 'ruby',
    'nginx.conf': 'nginx',
}

SHEBANG = re.compile(r'^#!.*?\b(bash|sh|zsh|ruby|python[\d.]*|node|perl|lua)\b')
SHEBANG_LANG = {'sh': 'bash', 'zsh': 'bash', 'bash': 'bash', 'ruby': 'ruby',
                'node': 'javascript', 'perl': 'perl', 'lua': 'lua'}


def language_of(fc):
    """The Prism language for a FileChange, or None if we have no grammar."""
    name = fc.path.rsplit('/', 1)[-1].lower()
    if name in BY_NAME:
        return BY_NAME[name]
    if '.' in name:
        lang = BY_SUFFIX.get(name.rsplit('.', 1)[1])
        if lang:
            return lang
        # A double suffix like schema.sql.erb, or a dotfile like .babelrc.
        for part in reversed(name.split('.')):
            if part in BY_SUFFIX:
                return BY_SUFFIX[part]
        return None
    # No extension: a shebang in the file's own added lines is the best clue,
    # and bin/ scripts are the common case that has one.
    for hunk in fc.hunks:
        for line in hunk.lines[:3]:
            m = SHEBANG.match(line.text)
            if m:
                word = m.group(1)
                return SHEBANG_LANG.get(word, 'python' if word.startswith('python') else None)
    return None

def bundle():
    """The JavaScript to inline: manual mode, core, the grammars, the diff plugin.

    `manual` is set by an assignment rather than a data-manual attribute because
    the result is one concatenated inline script, and currentScript semantics at
    that seam are not worth the risk. Without it Prism highlights everything on
    DOMContentLoaded and the lazy pass in report.js is bypassed.
    """
    parts = ['window.Prism = window.Prism || {}; window.Prism.manual = true;']
    missing = []
    for name in ['core'] + GRAMMARS + ['diff-highlight']:
        path = os.path.join(VENDOR, 'prism-%s.min.js' % name)
        try:
            with open(path, encoding='utf-8') as f:
                parts.append(f.read().rstrip())
        except OSError:
            missing.append(name)
    return '\n'.join(parts), missing
