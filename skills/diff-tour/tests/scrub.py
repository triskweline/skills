#!/usr/bin/env python3
"""Check tour artifacts for anything that should not leave a private repository.

  tests/scrub.py <file-or-directory> …

A tour leaves a patch and a narration file behind, and both are useful as test
fixtures: real narrations contain directive and prose shapes nobody would think to
invent. But a patch embeds real source, so before any of it travels — into a public
repository, into a transcript, into an issue — it gets read by this.

What it looks for is credentials and personal data, not code. Class names, method
names and business logic are not findings: the point is to catch the `.env` line, the
private key, the connection string with a password in it, the customer's email address
that happened to sit in a fixture two lines from a real change.

It is deliberately noisy. A false positive costs you a glance; a false negative costs
you a leaked credential in a public git history, which cannot be taken back. Nothing
it prints contains a full secret — matches are shown with their middle removed, so
running this does not itself copy the secret somewhere new.

Exit: 0 nothing found   1 findings above   2 bad arguments
"""

import os
import re
import sys

# (label, pattern, whether a match is almost certainly real)
RULES = [
    ('private key', r'-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY', True),
    ('certificate', r'-----BEGIN CERTIFICATE-----', False),
    ('ssh public key', r'ssh-(?:rsa|ed25519|dss) AAAA[0-9A-Za-z+/]{20,}', False),
    ('AWS access key id', r'\b(?:AKIA|ASIA)[0-9A-Z]{16}\b', True),
    ('GitHub token', r'\bgh[pousr]_[A-Za-z0-9]{30,}', True),
    ('Slack token', r'\bxox[baprs]-[A-Za-z0-9-]{10,}', True),
    ('Google API key', r'\bAIza[0-9A-Za-z_\-]{35}\b', True),
    ('Stripe live key', r'\b(?:sk|rk)_live_[0-9A-Za-z]{20,}', True),
    ('OpenAI-style key', r'\bsk-[A-Za-z0-9]{32,}', True),
    ('Anthropic-style key', r'\bsk-ant-[A-Za-z0-9_\-]{20,}', True),
    ('JWT', r'\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}', True),
    ('credentials in a URL', r'\b[a-z][a-z0-9+.\-]*://[^/\s:@"\']+:[^/\s@"\']{3,}@', True),
    ('Rails secret_key_base', r'secret_key_base["\']?\s*[:=]\s*["\'][0-9a-f]{32,}', True),
    ('basic auth header', r'Authorization:\s*(?:Basic|Bearer)\s+[A-Za-z0-9+/=._\-]{16,}',
     True),
    # An assignment whose value looks like a real secret rather than a placeholder.
    ('assigned secret',
     r'(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token'
     r'|private[_-]?key|client[_-]?secret)\b["\']?\s*[:=]\s*'
     r'["\'](?![A-Za-z0-9_]*(?:changeme|example|placeholder|redacted|dummy|test|fake'
     r'|xxx|todo|your|secret|password)[A-Za-z0-9_]*["\'])'
     r'[^"\'\s]{8,}["\']', False),
    # .env shape: SHOUTY_NAME=long-value, which is how these files actually leak. The
    # value has to look like a secret and not like configuration — at least one digit,
    # no slashes — or every `PROG=tour-checkout` in a shell script is a finding.
    ('env-style assignment',
     r'^\s*[+\-]?\s*[A-Z][A-Z0-9_]{3,}=(?=[^\s"\'#]*\d)[^\s"\'#/$]{16,}\s*$',
     False),
]

# Paths that are a finding by their name alone, wherever they appear in a diff.
PATHS = [
    ('key or certificate file', r'\.(?:pem|pfx|p12|key|jks|keystore)\b'),
    ('SSH private key', r'(?:^|/)id_(?:rsa|dsa|ecdsa|ed25519)(?:$|[^.\w])'),
    ('environment file', r'(?:^|/)\.env(?:\.|$)'),
    ('Rails master key', r'(?:^|/)(?:master\.key|credentials(?:/[\w.]+)?\.yml\.enc)'),
    ('secrets file', r'(?:^|/)(?:secrets|credentials)\.ya?ml\b'),
    ('htpasswd', r'(?:^|/)\.htpasswd\b'),
]

EMAIL = re.compile(r'(?<![\w/@.\-])[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.([A-Za-z]{2,})\b')
# A filename with an @ in it is not an address: `assets/logo@2x.png`, `@babel/core`,
# `src/@types/index.d.ts`. Those are everywhere in a front-end diff, and left in they
# bury the one real address in a hundred lines of noise.
NOT_A_TLD = {
    'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'ico', 'avif', 'woff', 'woff2', 'ttf',
    'js', 'mjs', 'cjs', 'jsx', 'ts', 'tsx', 'css', 'scss', 'sass', 'less', 'html',
    'json', 'yml', 'yaml', 'md', 'txt', 'lock', 'map', 'rb', 'py', 'go', 'rs', 'java',
    'php', 'sh', 'sql', 'xml', 'csv', 'pdf', 'zip', 'gz', 'erb', 'haml', 'slim', 'vue',
}
# Addresses that are not a person: these turn up in code and configuration constantly.
EMAIL_OK = re.compile(r'(?i)@(?:example\.(?:com|org|net)|test|localhost|invalid|'
                      r'\w+\.local|sentry\.io|.*\.internal)$|^(?:noreply|no-reply|'
                      r'postmaster|webmaster|admin|root|support|info|hello)@')

COMPILED = [(label, re.compile(pat, re.M), sure) for label, pat, sure in RULES]
COMPILED_PATHS = [(label, re.compile(pat)) for label, pat in PATHS]


def mask(s):
    """Show enough to recognise the shape, never enough to use."""
    s = s.strip()
    if len(s) <= 12:
        return s[:4] + '…'
    return '%s…%s (%d chars)' % (s[:6], s[-4:], len(s))


def scan(path):
    """[(line number, label, masked excerpt, certain)] for one file."""
    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            lines = f.read().split('\n')
    except OSError as e:
        print('scrub: cannot read %s: %s' % (path, e.strerror or e), file=sys.stderr)
        return []

    out = []
    for n, line in enumerate(lines, 1):
        if len(line) > 4000:            # a minified bundle; scanning it is all noise
            continue
        for label, rx, sure in COMPILED:
            m = rx.search(line)
            if m:
                out.append((n, label, mask(m.group(0)), sure))
        # Only diff header lines name files, so path rules apply there.
        if re.match(r'^(?:diff --git |\+\+\+ |--- |rename (?:from|to) )', line):
            for label, rx in COMPILED_PATHS:
                if rx.search(line):
                    out.append((n, label, line.strip()[:90], True))
        for m in EMAIL.finditer(line):
            if m.group(1).lower() in NOT_A_TLD:
                continue
            if not EMAIL_OK.search(m.group(0)):
                out.append((n, 'email address', mask(m.group(0)), False))
    return out


def main(argv):
    if not argv:
        print(__doc__.strip(), file=sys.stderr)
        return 2

    files = []
    for arg in argv:
        if os.path.isdir(arg):
            for root, _, names in os.walk(arg):
                files.extend(os.path.join(root, n) for n in sorted(names))
        elif os.path.isfile(arg):
            files.append(arg)
        else:
            print('scrub: no such file or directory: %s' % arg, file=sys.stderr)
            return 2

    certain = other = 0
    for path in files:
        found = scan(path)
        if not found:
            continue
        print('\n%s' % path)
        for n, label, excerpt, sure in found:
            print('  %s line %d: %s — %s'
                  % ('!!' if sure else '? ', n, label, excerpt))
            if sure:
                certain += 1
            else:
                other += 1

    print('\nscrub: %d file%s scanned. %d almost certainly real (!!), %d worth a look (?).'
          % (len(files), '' if len(files) == 1 else 's', certain, other),
          file=sys.stderr)
    if certain or other:
        print('scrub: nothing above shows a full secret. Read each one in the file '
              'itself before deciding.', file=sys.stderr)
        return 1
    print('scrub: no credentials or personal data found. Class and method names are '
          'not findings — this says nothing about whether you want the code public.',
          file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
