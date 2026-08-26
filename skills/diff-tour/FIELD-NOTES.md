# Field notes — diff-tour

Issues hit while touring a real branch (a Rails/Ruby/Node dependency upgrade plus a
Cucumber→RSpec migration; 23 files, 69 hunks, 2976 changed lines). Written 2026-08-26.

All four items below were reproduced against the shipped code, not inferred from reading it.
Where I guessed and was wrong, that is recorded too — see *Not a bug* at the end.

---

## 1. Warning line numbers point at the wrong line (confirmed bug)

**`lib/difftour/narration.py:176` — `_blame()`**

```python
def _blame(rep, needle, fallback):
    for i, line in enumerate(getattr(rep, 'source_lines', None) or [], 1):
        if needle in line:
            return i
    return fallback
```

It returns the **first line in the whole file** containing `needle` as a substring. For the
code-reference check at line 665–668 the needle passed is `a or b` — the *bare* matched
number, `"8.1"` — not the form that actually matched, `` `8.1` ``.

So the warning is blamed on the first line containing a bare `8.1` anywhere in the document.
A bare `8.1` in prose is **legal** and is not the offense; the backticked one may be two
hundred lines further down.

### Minimal repro

```
%report Repro

%intro Overview

%beat What it does
This app runs Rails 8.1 today.          <-- line 6, legal, NOT the offense

%chapter A chapter

Intro prose.

%blast narrow
Evidence.

%beat A beat
The offender is here on this line: `8.1` inside backticks.   <-- line 16, the offense
%hunk .nvmrc:1 = the node pin

%closing Wrap-up

%beat Done
Nothing.
```

The file is saved beside these notes as `FIELD-NOTES-repro.narration`. Run it against
any patch containing `.nvmrc` (non-final is enough):

```sh
bin/tour-build.py <some>.patch FIELD-NOTES-repro.narration /tmp/out.html --root <repo>
```

Output:

```
warning line 6: prose says 8.1, which is a position, not a name. …
```

**Line 6 is reported. The offending construct is on line 16.**

### Second symptom: duplicates collapse

Because `_blame` always returns the *first* hit, every occurrence reports the same line. On
the real narration I got **17 warnings that all said "line 8"** while the offenders were
spread across lines 8, 17, 22, 30, 56, 64, 71, 73, 76, 229 and 265. There was no way to find
them from the output — I had to grep the narration myself with a hand-written regex.

The one warning that *did* report correctly (`8.2`, line 64) did so only by luck: `8.2`
appeared exactly once in the file, so "first hit" and "the hit" were the same line.

This is doubly unfortunate because `_blame`'s own docstring says it exists precisely so that
"an agent editing by line number" is not sent "to the wrong place" — which is the exact
failure it produces here.

### Suggested fix

- Pass the **matched form including its delimiters** as the needle (`` `8.1` ``, not `8.1`),
  so the search cannot land on legal bare prose.
- Track *which* occurrence is being reported rather than always returning the first — e.g.
  walk occurrences in order and consume them, or resolve the line during parsing when the
  offset is still known.
- The same looseness affects the `REF.findall` call at line 685, where the needle is a bare
  label name: searching for `h17` as a substring will also match `h170`, or the letters `h17`
  occurring inside ordinary prose. Lower severity, same root cause.

---

## 2. No usable escape for a backticked `N.N` (confirmed)

**`lib/difftour/narration.py:665`**

```python
for a, b in re.findall(r'`(\d+\.\d+)`|\[\[(\d+\.\d+)\]\]', text):
```

Any backtick span whose entire content is `\d+\.\d+` is flagged as a block code. That is
correct for `` `3.2` `` meaning chapter 3 block 2. It is wrong for **version numbers**, which
are the single most common `N.N` token in a dependency-upgrade diff — `7.2`, `8.1`, `8.2`,
`3.0`, `4.0` — and which are exactly the sort of token a reader expects in backticks.

Everything I tried:

| Written | Warns? | Renders as |
|---|---|---|
| `` `8.1` `` | yes | `8.1` |
| `` `8\.1` `` | no | `8\.1` — **backslash leaks into the report** |
| `` `v8.1` `` | no | `v8.1` |
| `` `8.1.3` `` | no | `8.1.3` |
| `8.1` (bare) | no | `8.1` |

So the only form that both silences the check and preserves the text is **dropping the
backticks**. The documented escape set (`\*`, `` \` ``, `\[`, `\]`, `\\` in
`references/narration.md`) does not cover `.`, and `\.` is not handled — it silences the
check but ships a visible backslash, which is worse than the warning.

Net effect: a tour *about a version upgrade* cannot code-format its version numbers. That is
a visible degradation of the report in one of the most common diff shapes.

### Suggested fix

Any of these would do:

- Only treat `` `N.N` `` as a code reference when `N.N` **resolves to a block that exists**.
  In my report, chapters 2–10 existed, so `7.2` and `8.1` were live codes — but `1.4`,
  `12.1`, `3.9` would not be, and flagging those is pure noise. This narrows the false
  positives without losing the real catch.
- Or support an explicit escape and document it, so a deliberate version number can opt out.
- Or downgrade to an advisory (like the unfollowable-link check at line 677, which passes
  `advisory=True`) rather than a warning that blocks `--final`.

The second and third are cheap; the first is the one that actually fixes it.

---

## 3. The documentation points the wrong way (docs)

`references/narration.md`, under *Asterisks, and code in prose*:

> **Put code in backticks.** A glob, a path, a symbol or a signature is code, and code in
> backticks is unambiguous, renders as `<code>`, and is what the reader expects to see.

Applied to version numbers — which read as code — this instruction **causes** issue 2. I
followed it and my warning count went from **2 to 18**. The fix was to do the opposite of
what the guide says and strip the backticks.

Worth a sentence in that section naming the exception: bare `N.N` in prose is fine and
backticking it is what triggers the code-reference check.

---

## 4. Process observation: `--final` refuses on advisory-shaped warnings

Both of the above surface as `warning`, and `--final` refuses to hand over a report with any
warning. That is the right default. But because of issue 1 the warnings could not be located
from their own output, and because of issue 2 they could not be silenced without damaging the
prose — so the only route to a clean `--final` was to grep the narration by hand and remove
formatting I wanted.

This is the combination worth fixing: a blocking check whose message misidentifies its
location and whose only remedy degrades the output.

---

## Not a bug (checked and cleared)

- **The skeleton does not rewrite fragment specs.** I wrote `%hunk Gemfile:16 #10-15` and the
  skeleton table displayed `Gemfile:25 #10-15`, which looked like a silent rewrite. It is
  not: the narration file still reads `Gemfile:16 #10-15`, and the table is simply reporting
  where the fragment itself starts. Helpful, not surprising once understood.
- **Coverage, splicing and fragment selection all behaved exactly as documented.** `#lo-hi`
  fragmenting of a hunk carrying two unrelated ideas worked first time, and
  `tour-rest.py` correctly reported full coverage both before and after narration.

---

## What went well, for context on severity

The report itself came out well and the mechanics that matter — byte-exact hunks, coverage
arithmetic, label stability, fragmenting — were sound throughout. Both issues above are in
one narrow place: the code-reference lint and its line attribution. Neither threatened
fidelity; they cost time and one small quality compromise in the finished prose.

One note on the run itself: this session carried a standing instruction against spawning
subagents, so Step G was narrated serially. The skill handles that case explicitly and
correctly (SKILL.md, *When serial is the right answer*) — flagging only that the instruction
came from the session, not from the reader, so nothing was asked and nothing stalled.
