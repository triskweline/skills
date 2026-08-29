# diff-tour — field report

From one real run on 2026-08-29: `master..HEAD` in the Unpoly repo — 52 files, 100 hunks,
3,097 changed lines, two unrelated bodies of work. Produced 18 chapters / 144 components /
495 KB, narrated by 6 forks costing ~1.45M subagent tokens. The report was good and the
procedure held up; everything below is what got in the way.

Ordered by how much it costs to leave alone.

---

## 1. Confirmed defects

### 1.1 `tour-fetch.sh` prints a spurious "narrowed to" line on every range target

Observed, on a plain `master..HEAD` with no pathspec:

```
tour-fetch: 100 hunks, 52 files -> tmp/difftour-master-HEAD/tour.patch
tour-fetch: narrowed to  — say so in the overview
```

`NARROWED=1` is set unconditionally on every code path that *accepts* a pathspec
(`bin/tour-fetch.sh:115,117,126,129,164`), not on the paths where one was actually given.
Line 53's own comment states the intent — `# set only where the pathspec was actually
applied` — and the code does not honour it.

**Why it matters.** This fires on the most common target form. It instructs the model to
tell the reader the diff was narrowed, when it was not. Step C explicitly says to relay
`tour-fetch`'s output to the reader, so the natural failure is a tour that opens by
announcing a restriction that does not exist. I caught it only because the path list was
visibly empty.

**Fix.** Gate on the array, not the flag: `[ ${#PATHS[@]} -eq 0 ] || echo "tour-fetch:
narrowed to ..."`. Or set `NARROWED` only when `${#PATHS[@]} -gt 0`.

### 1.2 Step J describes one refusal; `tour-build.py` has two, and they behave differently

SKILL.md:1295–1298 says:

> It writes the file, says on stderr what is wrong, prints **nothing on stdout**, and exits
> 1. […] the path in a refusal message is there so you can open the file

That is true of the `--final` gate (gaps / pending / warnings), which writes the HTML and
names its path (`bin/tour-build.py:231-235`). It is **not** true of a fatal problem — a
dangling label, an unresolvable spec — which returns at `bin/tour-build.py:186` with
`Nothing written.` and exit **6**, before rendering.

I hit the fatal path on my final build. The doc told me a file existed at a path; nothing
did, and the exit code was not 1.

**Why it matters.** These are the two states a model reasons about at hand-over, and the
doc collapses them. A model that trusts Step J will tell the user "the report is at X, but
it has a problem" when there is no X.

**Fix.** Two sentences in Step J, one per refusal kind, with their exit codes:

- fatal (a spec or reference that cannot resolve) → nothing written, exit 6, fix and rebuild;
- `--final` gate (unshown lines, pending prose, warnings) → written and named, exit 1, so
  you can look at it before fixing.

### 1.3 `](#anything)` is claimed as a label reference, so a report cannot quote an anchor

`REF` in `lib/difftour/narration.py:135` is:

```python
REF = re.compile(r'\[\[([A-Za-z][A-Za-z0-9_-]*)\]\]|\]\(#([A-Za-z][A-Za-z0-9_-]*)\)')
```

Any `[text](#anchor)` whose anchor starts with a letter is treated as a block reference and
refused if it does not name a label. A fork writing chapter 12 — a chapter *about* markdown
anchors in the repo's own guides — wrote:

```
The link the paragraph above it gains, `[Leave it to the minifier](#leave-it-to-the-minifier)`,
is a same-file anchor
```

and the final build refused with `[[leave-it-to-the-minifier]] names nothing`. Note it was
already inside backticks, which did not help: the check runs over raw prose.

**Why it matters.** This is not exotic. Any tour touching documentation, HTML, or a
generated table of contents will want to quote a real `#anchor`, and there is no documented
escape. The failure surfaces at *your* final build, in prose a fork wrote and you will not
read — the worst place for it.

**Fix, in order of preference.**

1. Narrow the regex to what the skill actually mints: `#(h\d+|ch\d+)`. Everything else falls
   through to the existing "link the report cannot follow" advisory, which is the correct
   diagnosis and is already non-fatal.
2. Failing that, skip inline-code spans before scanning — the backticked form is exactly how
   `references/narration.md` tells you to disambiguate everywhere else, so it ought to work
   here.
3. At minimum, document it in `narration.md` beside the asterisk-escaping section, and give
   the error message an escape to suggest.

---

## 2. Rules that misfired

### 2.1 "One file each" reads as one file per fork — 6 out of 6 forks hit the refusal

SKILL.md tells a fork to write

> into `<narration>.ch<n>`, beside the narration file. One file each, so nothing races.

and, higher up, "It writes one file per chapter it owns". The rule is stated correctly,
twice. I still briefed all six forks to put their two or three chapters in one file, and all
six independently hit `tour-splice.py`'s refusal ("One file per chapter: this would replace
one chapter with all of them and duplicate the rest"), corrected themselves, and reported
the deviation back with visible irritation.

The misreading is easy to see in hindsight: "One file each" sits in a bullet whose subject is
*the fork*, immediately after a sentence about what a fork writes, and "so nothing races" is
a per-fork rationale. The `<n>` in `<narration>.ch<n>` is never said to be the chapter
number.

**Why it matters.** It cost every fork a round trip, and the recovery was only automatic
because `--check` catches it. A fork that skipped the self-check would have handed me a file
the splice then rejected in bulk.

**Fix.** Make the packing paragraph carry the filename rule, not the fork bullet:

> A fork may own several chapters. It writes **one file per chapter**, named
> `<narration>.ch<N>` where `N` is the chapter's number — never one file holding several
> chapters, which the splice refuses.

And in the fork bullet, "one file per chapter it owns, so nothing races".

### 2.2 The blast levels stopped discriminating: 9 of 16 chapters came out `wide`

Final distribution: **wide 9, moderate 1, narrow 6.** Every chapter of the primary body of
work except one was `wide`.

That is not the forks being lazy — it follows from the rule. "A new error or refusal on a
path that previously succeeded is always wide", plus "public API, or behavior observable
outside the codebase", catches nearly everything in a diff to a *library*. Ten of the
CHANGELOG's entries were marked breaking; the rule was working as designed.

But Step I then says to rank the overview's "where to be careful" pointers "by `%blast` and
then by evidence", and with nine chapters tied at the top the level sorts almost nothing. I
ended up ranking by hand on reach and on how server-visible the change was — which is the
right answer, and is not what the rule says to do.

**Why it matters.** The overview's three pointers are the highest-leverage paragraph in the
report, and the documented procedure for producing them degrades exactly on the diffs big
enough to need a tour.

**Fix.** Keep the three levels — they are honest — but make Step I's tie-break explicit and
first-class, since it will almost always be the operative one:

> Rank by `%blast`, then — and this is usually the real sort, because a library diff makes
> most chapters wide — by reach evidence: how many call sites, how many of them this diff
> does not touch, and whether the change is observable outside the process (on the wire, in
> the database, in a rendered page) rather than only to callers.

Optionally, tell forks that a `wide` level needs the *number* in its evidence prose, so the
orchestrator has something comparable to sort on without reading the chapters.

### 2.3 A fork's cohesion verdict arrives after it can be acted on

The five-item report asks each fork "whether its chapter is really one idea". Two said no:

- ch10 (*A validation is not a submission*) held two unrelated edits that happened to sit in
  one hunk;
- ch12 (*Generating those tables of contents*) held the generator and a separate
  documentation change about the guides' own conventions.

The skill's answer is: don't re-cluster, say it in the overview. I did, and the overview is
better for it. But those four ideas would have made four better chapters, and the fork that
noticed is the only entity that read the material closely enough to know.

**Why it matters.** This is the one quality signal in the whole procedure that is
deliberately discarded. The stated reason — siblings are working from a frozen skeleton — is
real, but it only forbids moving blocks *between* chapters. A fork splitting its own chapter
moves nothing anyone else can see.

**Fix.** Allow a fork to split a chapter it wholly owns, since the constraint that motivates
the freeze does not apply:

- the fork keeps the original `%chapter` title on the first half (the splice matches on
  title) and gives the second half a new title;
- it writes two files and reports the new title;
- `tour-splice.py` accepts a file whose first chapter matches an existing title and whose
  subsequent chapters are new, inserting them after it.

That last is a real change to the splice. If it is too much, a cheaper version: let the fork
*propose* the split in its report, and add a line to Step G saying the orchestrator may
perform it after all forks return — the same window in which misfiled blocks may already be
moved.

---

## 3. Ergonomics that cost real time

### 3.1 `--body` has no sub-file selector

`spec/unpoly/classes/params_spec.js` is 28.1 KB of diff in three hunks. There is no way to
ask for one of them: the path argument is a prefix, and `--not` also takes paths. I read it
as `--body <file> | head -400` and `--body <file> | sed -n '400,760p'` — i.e. I rendered
28 KB twice to see it in two pieces, and the second call's output has no header.

Eleven `--body` calls total, two of which were the same file.

**Fix.** Accept the same spec syntax `%hunk` already uses: `--body params_spec.js:687` for
one hunk, `--body params_spec.js:687 #1-120` for a slice. The parser exists.

### 3.2 Fragment boundaries are hand-counted, and that is where the errors would be

Splitting the 553-line hunk seventeen ways meant reading the `--body` output and manually
tracking offsets — `1-64` to chapter 9, `65-124` to chapter 4, `125-137` to chapter 8, and so
on. `runs:` on the hunk line helps find *where* to cut, but not *what number* to write, and a
one-off error would put a spec in the wrong chapter with nothing to catch it (coverage is
satisfied either way).

**Fix.** Two cheap options, either would do:

- a `--outline <file>:<start>` mode printing only the structural lines with their offsets —
  for a spec file, every `describe(` / `it(` and its offset, which is a two-line summary of a
  553-line hunk and exactly what a cut is made on;
- accept `#run3` as a selector meaning "the third run of changed lines plus the context
  around it", resolved by the same code that prints `runs:`.

### 3.3 Step I needs a label lookup, not a 150-line table

Step I correctly insists on re-running `tour-skeleton.py` and checking a caption before
citing its label. With 124 labels across 17 chapters, the table is long enough that I
grepped it for the dozen labels I wanted (`grep -E "h9[123]\]\]|h4[157]\]\]|…"`) — which
works, but a model that does not think to do that will page through the table or, worse,
cite from memory. Citing from memory is precisely the failure Step I is written to prevent.

**Fix.** `bin/tour-skeleton.py --labels h39,h70,h115` printing just those rows.

---

## 4. Smaller notes

**An empty Leftovers chapter is a success, and the skill does not say so.** Every hunk in
this diff belonged to a named topic, so I omitted `%leftovers` entirely. That is allowed
("at most one"), but Step H reads as though the chapter is expected, and I spent a moment
checking whether omitting it would trip the final build. One clause in Step H — "an empty
Leftovers means the clustering worked; omit the directive" — closes it.

**A beat with no blocks is legal and useful; say whether that is intended.** A fork added a
beat to chapter 3 carrying no blocks of its own, pointing forward at chapter 4's blocks for
the evidence. It builds, it renders, and it is the right way to signpost a consequence whose
evidence lives elsewhere. Nothing in `narration.md` says whether this is sanctioned or
tolerated.

**Step B does not say where to put the tour directory.** It says not a scratch directory a
session cleans up, and to name it `difftour-<something>`. I chose the project's own
gitignored `tmp/`, which was ideal here and would have polluted the working tree of a repo
without one. Worth a sentence: prefer a gitignored directory inside the repo, else somewhere
under the user's home; never the session scratchpad.

**Step D is described as thin and is not, on a diff this size.** "The procedure below is thin
on purpose" is about the SKILL text, but Step D's own framing ("Three things: what changed,
roughly where it sits, and what the author says they were doing") reads as cheap. Reading
~180 KB of patch was the second-largest cost of the run after narration, and it had to be
serial. That is the right trade — the clustering depended on all of it — but a model looking
for somewhere to economise will look here, and the doc currently invites that. Saying "on a
hundred-hunk diff this is the second-largest cost in the tour, and it is not the place to
save" would help.

**`--renames` was subsumed by reading, and the ladder implies otherwise.** This diff had a
textbook rename sweep (`genericButtonSelectors` → `anyButtonSelectors`) and I never ran
`--renames`, because by the time I would have, I had read every hunk. The ladder presents it
as a step between the list and `--body`; in practice it earns its place only when you intend
*not* to read something in full. Worth saying that.

**Six forks was right; the packing suggestion is good.** `tour-skeleton.py` proposed six
forks at ≤23 blocks each and I took it unchanged. Wall-clock was ~6 minutes against a serial
estimate several times that. No complaint — recording it because the packing heuristic is
the kind of thing that gets tuned without evidence.

---

## 5. What worked, and should not be traded away

- **Coverage settles before the prose exists.** `tour-skeleton.py` reporting "all 3,097
  changed lines placed" before a word was narrated is the single best structural decision in
  the skill. Re-checking after the splice caught nothing this time, which is the point.

- **The five-item fork report.** Asking for admissions *as finished sentences I can paste*
  is what makes the wrap-up honest: every admission in the final report is the fork's own
  wording, from the entity that actually read the code. I rewrote none of them. Without that
  instruction I would have paraphrased twenty findings I had not verified.

- **"Never write a code."** Labels survived a splice that renumbered most of the report, and
  reordering inside chapters cost nothing. No reference broke.

- **"A caption states what you read, never what you assume."** This is what stopped me
  captioning a 553-line hunk from its filename. It is also the rule most likely to be quietly
  dropped under budget pressure, so it deserves the emphasis it has.

- **The `--final` gate.** Refusing a report with one bad reference, after fifteen green
  intermediate builds, is exactly the behaviour that makes the other guarantees worth
  anything. (See 1.2 — the gate is right, only its documentation is wrong.)

- **Announce-and-go on subagents.** The instruction to state the fork plan in Step C rather
  than ask resolved a genuine conflict with a standing "do not spawn subagents unless the
  user requested it" instruction, without stalling. Worth noting that it *is* a conflict the
  skill resolves in its own favour, and that a reader of the skill should know that is what
  is happening — the current phrasing is confident enough that a model might not notice it is
  overriding anything.
