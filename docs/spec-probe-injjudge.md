<!--
  D-INJJUDGE -- judging the filed "injector-check is still a TEXT classifier"
  residual. Structure follows docs/spec-audit-citations-negation.md:
  §0 question, §1 denominator, §2 falsify by measuring, §3 design,
  §4 predicted GREEN at exact values, §5 predicted RED with knives, §6 as-built.
  Predicted sets are fixed BEFORE any change to tools/.
-->

# D-INJJUDGE — the split literal, judged; and the tree the gate never walked

Apparatus slice. **Touches no `basic/`, no `sub/`, no `disk/`, no `tape/` source**
— one checker and its documentation — so no ROM sign-off gate applies. It is
nevertheless proved ROM-neutral by hash (§4).

Judges the `TODO.md` §"Open — standing residuals" entry:

> ⚠️ **`injector-check` IS STILL A TEXT CLASSIFIER, and D-INJSINK narrowed that
> without closing it** (`docs/spec-probe-injsink.md` §6). What passes, measured on
> the shipped gate rather than assumed: a **split literal**
> (`"debug write" + f" memory {G} 0"` → `CLEAN`), and any body that reaches the
> cursors by a spelling neither rule knows. Neither is a careless-author shape —
> the six real copies were all verbatim — so this is a stated limit, not a filed
> defect.

Companions: [`spec-probe-lastinj.md`](spec-probe-lastinj.md) (rule (a), the gate's
design), [`spec-probe-injsink.md`](spec-probe-injsink.md) (rule (b)),
[`spec-probe-latch.md`](spec-probe-latch.md) and
[`spec-probe-latch2.md`](spec-probe-latch2.md) (the delivery race the gate exists
for).

---

## 0. The question

The filed item is a **property of the tooling**: the classifier concatenates the
module's string literals with `"\n"` and asks whether `debug write memory` is a
substring, so a body split across two adjacent expressions is not seen. That is
true. [[correct-claim-can-be-the-wrong-question]] says such properties are almost
always true and almost always decide nothing, and the arc's score is now
twenty-three filed justifications checked, eleven wrong. So the question this
slice asks is not *"can the classifier be fooled?"* but:

> **Q1.** Has a split literal — or anything else the shipped predicate cannot see
> — **ever actually landed** in this tree, in any commit of its subject's life?
> And if a stronger predicate is proposed, what does it cost on the real corpus?

> **Q2.** The gate's own headline is *"ALL PASS — one injector in the tree."*
> **Is that sentence true?**

> **Q3.** What does a **dead subject** score [[gate-whose-answer-is-an-error-passes-a-dead-subject]]
> — does this gate have a vacuity floor at all, on its walk **and** on its
> self-test?

Q2 is the one that turned out to matter, and it is not about the classifier at
all.

---

## 1. The denominator

### 1.1 What `injector-check` actually scans

`tools/check_probe_injectors.py` hard-codes

    SCAN_DIRS = ("probes", "tools", "tests")

and `_sources()` walks those three directories for `*.py`. At `6270177`:

| where | `.py` files | scanned |
|---|---:|---:|
| `probes/` | 169 | ✅ |
| `tests/`  | 63  | ✅ |
| `tools/`  | 26  | ✅ |
| **in scope** | **258** | |
| `scratchpad/` | 62 | ❌ |
| `tape/` | 5 | ❌ |
| **out of scope** | **67** | |
| **tracked `.py` in the tree** | **325** | **79.4 %** |

`SCAN_DIRS` has no recorded justification. `spec-probe-lastinj.md` §3.4 calls the
tool *"the denominator gate"* and names the three directories in the same breath,
without asking what is outside them. D-CITEJUDGE asked exactly that question of
`audit_citations.py` and moved its floor from 49 files to 116; nobody has asked it
here.

⚠️ `audit_citations.py` **does** exclude `scratchpad/` (`SWEEP_SKIP`), so
"scratchpad is out of scope" is a house convention with a precedent — but it is a
precedent from a **citation** gate, whose subject is provenance prose. This gate's
subject is an executable body. [[a-borrowed-window-inherits-its-corpus]]: the same
exclusion in a different check is a new, unmeasured rule.

### 1.2 The walk

The house method: `git ls-tree -r` + `git cat-file --batch` with a per-blob cache,
over **all 982 commits**. The walk **imports** `tools/check_probe_injectors.py`
and monkeypatches exactly one of two seams per variant —

* `CPI._sources` — the **denominator** (which files are handed to the walk),
* `CPI._emitted_strings` — the **predicate** (what counts as an emitted string),

— so `classify`, `walk`, `frozen_registry`, `EXEMPT` and the `HANDLES` check are
in every case the shipped code path, not a re-implementation. A self-test against
a re-implementation proves nothing.

Variants:

| # | denominator | predicate | what it tests |
|---|---|---|---|
| **V0** | shipped 3 dirs | shipped | the baseline |
| **V1** | **every `.py` in the tree** | shipped | Q2 — the denominator |
| **V2** | shipped 3 dirs | **folds `+` / f-string / `%` / `.join`** | Q1 — the filed fix |
| **V3** | every `.py` | folded | both |
| **V4** | shipped 3 dirs | **literal soup** (all literals glued, whitespace stripped) | the eager text bound |
| **V5** | shipped 3 dirs | **raw file text** (comments count) | the crude grep the AST walk replaced |

Scored per commit: the offender set. Reported per variant: commits whose set
differs from V0, every extra finding with its commit count, and every V0 finding
the variant **loses**.

### 1.3 Files this slice ADDS, checked against the sweep's own filter

`tools/audit_citations.py`: `SWEEP_EXTS = (".md", ".asm", ".inc", ".py", ".tcl",
".txt", ".bas", ".yml")`, `SWEEP_SKIP = {build, scratchpad, .git, .claude,
__pycache__, .vscode}`.

| file | ext | in `SWEEP_EXTS`? | in a skipped dir? | counts |
|---|---|---|---|---|
| `docs/spec-probe-injjudge.md` | `.md` | ✅ | no | **+1** |
| `tools/injector-record-allow.txt` | `.txt` | ✅ | no | **+1** |
| the knife runner | `.py` | ✅ | **`scratchpad/`** | 0 |
| edits to `tools/check_probe_injectors.py`, `TODO.md` | — | already counted | | 0 |

⇒ swept files **697 → 699**. (D-DOCJUDGE and D-BYTEJUDGE both mispredicted this
by not writing the table out.)

---

## 2. Falsify by measuring

### 2.1 The walk, over all 982 commits

| variant | offenders at HEAD | commits differing from V0 | distinct extra findings ever | genuine | V0 findings lost |
|---|---:|---:|---:|---:|---:|
| **V0 shipped** | 0 / 258 | — | — | — | — |
| **V1 widened** | **3** / 325 | **252** | **3** | **3** | 0 |
| **V2 folded** (the filed fix) | 0 / 258 | **0** | **0** | — | 0 |
| **V3 folded + widened** | 3 / 325 | 252 | 3 | 3 | 0 |
| **V4 soup** (eager bound) | 0 / 258 | **0** | **0** | — | 0 |
| **V5 rawtext** (comments count) | **12** / 258 | **486** | **12** | **1** | 0 |

### 2.2 🔴 Q1 — the filed fix finds nothing, and nothing text-level ever will

**V2 differs from the shipped rule in ZERO of 982 commits.** A split literal has
never landed. That on its own would only say the hole is unexercised *so far*; the
result that settles it is **V4**.

V4 is the eager bound on the whole class the residual names — *"any body that
reaches the cursors by a spelling neither rule knows"*. It glues **every** string
literal in a module together with nothing between them and strips all whitespace,
so `"debug write" + " memory"`, `"deb" "ug write memory"`, a list of fragments, a
`%`-template assembled from parts and a body built across three statements all
collapse into the same soup. It is the most permissive text predicate that can be
written without leaving the file's literals.

**V4 also differs from the shipped rule in ZERO of 982 commits.**

⇒ the residual's premise (*"the six real copies were all verbatim"*) is not merely
true of the six; it is true of **every `.py` this repository has ever contained, in
every commit**. There is nothing in the corpus for a stronger text predicate to
find. Folding is free, and it buys **0**.

### 2.3 The cost of the crude alternative, measured

V5 is the raw-text grep the AST walk was built to avoid, and the docstring's claim
that it would flag *"every probe that merely explains the mechanism in prose"* had
never been measured. It is now: **12 files, red in 486 of 982 commits — half the
project's life.** Eleven are prose (`HANDLES` on a comment naming a frozen body);
one, `probes/basic/basic_probe_sprite_trap.py`, comes out **`COMPOSES`** — it pokes
trap flags for an ordinary reason and names the cursors in a comment. That is a
hard gate failure on a compliant file. The docstring's reasoning was right and is
now quantified.

### 2.4 🔴 Q2 — the gate's headline sentence is FALSE, and the rule is not at fault

`SCAN_DIRS` never sees 67 of the tree's 325 `.py` files. Three of them compose the
injector:

| file | landed | verdict from the **shipped, unmodified** classifier | commits present |
|---|---|---|---:|
| `scratchpad/g4_hang_probe.py` | `907d5b6`, 2026-07-22 | `COMPOSES` — emits `debug write memory` and names `GETPNT`, `PUTPNT` | **252** |
| `scratchpad/i1_input_char2.py` | `8409408`, 2026-07-23 | `COMPOSES` | **237** |
| `scratchpad/i2_frame.py` | `559e15d`, 2026-07-23 | `COMPOSES` | **229** |

`i2_frame.py`'s `__key` is the pre-D-LATCH body **character-for-character** modulo
whitespace and symbolic-versus-decimal addresses — the same body
`probes/lib/latch_check.py` freezes as `OLD_KEY` and `make latch-check` row A
requires to MANGLE. The other two are the same body with `R.KEYBUF` / `R.GETPNT` /
`R.PUTPNT` substituted; both **import `omsx_repl`** for the addresses and then
compose their own injector anyway.

🔴 **The rule gets all three right the moment it is shown them.** This is not a
classifier blind spot — the classifier is sound and this slice found no way to
improve it. It is a **denominator** blind spot, and it means
`ALL PASS -- one injector in the tree` is a false sentence:
there are four bodies in the tree, and the gate has never looked at three of them.
[[readout-blind-to-its-own-subject]] — the readout fails by AGREEING.

**Precision of the widening is 3/3 over 982 commits.** V1 adds exactly three
distinct findings across the whole history and loses none; there is no third
category to triage.

### 2.5 What actually fails — the D-DSKJUDGE conversion

[[correct-claim-can-be-the-wrong-question]]: *nothing reads them* is a fact about
tooling. The failure question is *what breaks if these three are wrong?*

* **Today: nothing.** No Makefile target dispatches them, no probe imports them,
  and none has been touched since the single commit that introduced it. They are
  one-shot characterization records.
* **The live harm is the sentence**, not the files. A reader of a green
  `injector-check` concludes the class is closed. It is not.
* **The forward harm is promotion, and it is not hypothetical in this tree.**
  `docs/rom-region-structure-review.md:249`: *"This sweep is no longer a scratchpad
  script. It landed as `tools/check_dead_code.py`"* — a hard gate inside
  `make basic-reloc`. A scratchpad script here is a candidate for promotion, and
  promotion carries whatever body it holds. That is precisely how six copies of the
  old injector came to exist.

### 2.6 🔴 And they may NOT be repointed

The obvious close — rewrite the three to call `key_proc()` — is refused, on the
same grounds as D-BYTEJUDGE's decline [[a-policy-that-forbids-by-provenance]].
All three are cited as the apparatus behind landed specs:

* `basic/PROVENANCE.md:3569` and `docs/spec-basic-input-devices.md:18` cite
  `i1_input_char2.py`;
* `docs/spec-basic-input-devices.md:351` and `tape/PROVENANCE.md:88` cite
  `i2_frame.py`;
* `docs/spec-basic-graphics-g4.md:191` and `tests/test_graphics.py:879` cite
  `g4_hang_probe.py`.

A provenance record is a statement about **what was run**. Rewriting the injector
inside one makes the file no longer that. Deleting them breaks six citations. So
the three are not a defect to fix; they are a **class to name and to bound**.

### 2.7 🔴 Q3 — what a dead subject scores

Two vacuity holes, both of the shape this arc keeps finding
[[gate-can-be-green-while-measuring-nothing]]:

* **The self-test table can be emptied silently.** `self_test()`'s `rows` is a
  tuple literal inside the function; set it to `()` and the failure list is empty,
  so the gate prints
  `injector-check: self-test PASS  (rows A-D: the frozen pre-D-LATCH body
  COMPOSES, …)` and exits 0. It does not print a count, so unlike D-NEGJUDGE's
  `0/0` there is not even a zero to notice — **the message names four rows it did
  not run.** The registry `PINNED` check does not cover it: emptying the table
  blinds the CONTROL, not the RULE.
* **The walk has no floor but zero.** `if not files:` catches only a totally
  collapsed walk. `PINNED` catches the loss of `probes/lib/`, but deleting
  `probes/disk/` (25 files) or `tests/` (63) leaves a green `ALL PASS` over a
  denominator quietly 10–25 % smaller. Historical range of the widened
  denominator: **1 → 325**.

---

## 3. Design

### 3.1 DECLINED as filed: no change to the predicate

The split-literal fold is **not shipped**. Recall 0 over 982 commits; the eager
bound V4, which subsumes the entire "spelling neither rule knows" class, is also 0.
A rule that has never fired and whose maximal generalisation has never fired is not
a gate, it is a comment. §6.5 records what would re-open it.

### 3.2 The denominator is DERIVED, not listed

`SCAN_DIRS` is replaced by a walk of every `*.py` under the repository root,
skipping `build`, `.git`, `.claude`, `__pycache__`, `.vscode` — the same shape as
`audit_citations.SWEEP_SKIP`, minus `scratchpad`, which is the whole point.
258 → **325** files. D-CITEJUDGE's move: derive the floor rather than hand-list it.

### 3.3 A fourth exemption class, `RECORD`, in an acknowledged list

The three files get `tools/injector-record-allow.txt`, D-REVJUDGE's two-directional
shape — **an unacknowledged composer is a tree fault (rc 1); a stale entry is an
instrument fault (rc 2).** Keyed by path, which is what makes promotion loud: move
the file into `probes/` and its entry goes stale.

`RECORD` states: *a frozen characterization script, cited from a provenance
document, that composed its own body before the class was closed; it is not
dispatched by any target and may not be rewritten without falsifying the record.*
The machine-checked half, mirroring `HANDLES`: **no scanned file may import a
RECORD module.** An import makes the body reachable from live code and the
acknowledgement stops covering it.

### 3.4 The headline stops overclaiming

`ALL PASS -- one injector in the tree` becomes a sentence that counts what is
actually there: one live injector, N acknowledged records, over M files.

### 3.5 Floors

* `MIN_FILES = 300` on the walk (today 325). Below it: `CANNOT JUDGE`, rc 2.
* `MIN_SELFTEST_ROWS = 4` **plus a polarity bar** — the table must contain a row
  expecting each of `COMPOSES`, `HANDLES` and `CLEAN`. And the self-test prints
  `n/n`, so an emptied table cannot print a sentence about rows it never ran.

### 3.6 NOT done, filed instead

`tools/check_probe_preflight.py` carries the **identical** `SCAN_DIRS`, and **6**
out-of-scope `.py` launch openMSX. Same denominator shape, different rule, and its
rule has not been walked. Filed in `TODO.md`, not fixed here.

---

## 4. Predicted GREEN, at exact values — fixed BEFORE the change

| # | gate | predicted |
|---|---|---|
| G1 | `sha256 build/disk.rom` | `2c630d3d…` (unchanged) |
| G2 | `sha256 build/sub.rom` | `b2935188…` (unchanged) |
| G3 | `sha256 build/basic-reloc.rom` | `3f1cd586…` (unchanged) |
| G4 | `sha256 build/zerobas-main-eu.rom` | `d061cd58…` (unchanged) |
| G5 | walls | low **23**, page 1 **356**, sub p0 **3869**, sub p1 **2324** |
| G6 | closure | abi 122+4, `--page0` 718+15, `--page1` 522+41 |
| G7 | dead code | main 1551 spans / **285** seeds → 0; sub 1451 / **102** → 0 (+1 allowlisted) |
| G8 | `audit-citations` swept files | 697 → **699** (§1.3) |
| G9 | `audit-citations` verdict | 8/107/1, 97/181/15, self-tests 10/10 11/11 12/12 14/14, 2 listing- + 1 dump-allowlisted, **4 advisory all acknowledged**, rc 0 |
| G10 | `injector-check` files scanned | 258 → **325** |
| G11 | `injector-check` counts | exempt **4**, composes **0**, handles **0**, records **3**, unparseable 0, bad exemption 0, rc 0 |
| G12 | `injector-check` self-test | **4/4**, printed as a count |
| G13 | `unit-test` | **58/58** |
| G14 | `latch-check` | **16/16** |
| G15 | `preflight-check` | **95** guarded, **0** unguarded (unchanged — not widened) |
| G16 | `kwtable` | 1041 B |

---

## 5. Predicted RED, with knives

Every knife runs **twice**, with a GREEN control after each restore. The restore
point is a scratchpad snapshot taken **after** this slice's change and **before**
the first cut — never `git checkout --`, which would revert the slice
[[knife-cleanup-restores-from-head]]. The runner refuses to start unless the
subject is green, and every cut asserts it changed the file before the result is
believed [[knife-aimed-at-the-wrong-gate]].

| # | cut | predicted |
|---|---|---|
| **K1** | revert the denominator to the three hard-coded dirs | 258 files, **0 records**, and the allowlist's 3 entries go **stale** → rc 2 |
| **K2** | delete `tools/injector-record-allow.txt` | 3 unacknowledged composers → rc 1 |
| **K3** | remove one entry from the allowlist | 1 unacknowledged composer → rc 1 |
| **K4** | add a bogus entry for a file that does not compose | stale entry → rc 2 |
| **K5** | empty `self_test()`'s `rows` to `()` | `MIN_SELFTEST_ROWS` → rc 2 (**rc 0 before this slice**) |
| **K6** | drop row C (the `HANDLES` vector) only | polarity bar → rc 2 |
| **K7** | make the walk skip `scratchpad` as well | 263 files < `MIN_FILES` **and** 3 stale entries → rc 2 |
| **K8** | gut `classify` to `return "CLEAN", ""` | self-test rows A and C fail → rc 2 |
| **K9** | plant a fourth composer under `tape/` | 1 unacknowledged composer → rc 1 (**rc 0 before this slice**) |
| **K10** | plant an importer of a RECORD module in `probes/` | RECORD claim refuted → rc 1 |

K5 and K9 are the two that read **rc 0 at `6270177`**: they are the slice's own
justification, not decoration.

---

## 6. As-built

Landed 2026-08-06. `tools/check_probe_injectors.py`, a new
`tools/injector-record-allow.txt`, this document, `TODO.md`. **No `.asm`, no
`.inc`, no probe and no test edited**; all four `build/*.rom` are byte-identical
to `6270177`.

### 6.1 Predictions, scored

| # | predicted | measured |
|---|---|---|
| G1–G4 | four ROM hashes unchanged | ✅ `2c630d3d…` `b2935188…` `3f1cd586…` `d061cd58…` |
| G5 | walls 23 / 356 / 3869 / 2324 | ✅ exact |
| G6 | closure 122+4 / 718+15 / 522+41 | ✅ exact |
| G7 | dead code 285 / 102 seeds → 0 (+1) | ✅ exact, despite ~60 new prose lines in an `external_names` root |
| G8 | swept 697 → **699** | ✅ 699 |
| G9 | audit verdict, 4 advisory acknowledged | ✅ self-tests 10/10 11/11 12/12 14/14, rc 0 |
| G10 | files scanned 258 → **325** | ✅ 325 |
| G11 | exempt 4, records 3, offenders 0 | ✅ exact |
| G12 | self-test printed as **4/4** | ✅ |
| G16 | kwtable 1041 B | ✅ |

⚠️ **One movement not predicted, and it is a consequence of the widening:** the
generated frozen-body registry went **5 symbols / 2 modules → 6 / 3**. The new
entry is `i2_frame.HEADER` — `scratchpad/i2_frame.py` binds its injector to a
module-level name, so the derived denominator makes it a frozen body for rule (b)
too. This is the eager direction and it is correct, but it was not foreseen. It
also means the RECORD reachability check of §3.3 is **not** redundant with rule
(b): the other two records bind their bodies inside a function, so only the
explicit check covers them (K10 plants against `i2_frame`, the one case where both
fire).

### 6.2 🔴 The knife runner scored 8 of 11 knives right for the wrong reason

First pass: 22 runs, "6 misses". The three misses were K3, K9 and K10 — every
knife predicting **rc 1**. The cause was in the runner, not the gate:

> **`make` exits 2 for ANY failed recipe.** The runner shelled out to
> `make injector-check`, so the tool's own 1-vs-2 — *tree fault* versus
> *instrument fault*, the distinction this gate is built around — was flattened
> before the runner ever saw it.

Which means the eight knives that "CUT" with `rc=2 want=2` had proved nothing
either: they would have scored identically had the tool returned 1. The runner now
invokes the subject directly. Sibling of *"a pipeline's exit code is `grep`'s, not
`make`'s"* [[apparatus-is-part-of-the-measurement]], one layer up: **a gate's exit
code is not its runner's.**

🔴 **And an earlier measurement was contaminated the same way.** Establishing that
K5 and K9 read `rc 0` on the pre-slice tool, the first attempt copied
`git show HEAD:tools/check_probe_injectors.py` to `tools/_k5_before.py` — **inside
the denominator it was about to measure.** The copy carries `FROZEN_FAULT`, so the
walk flagged the plant and returned 1, which read as "the hole is already closed".
Re-run from `build/` (skipped by both versions, and one level below the repo root
so `REPO` still resolves), the real numbers are below.

### 6.3 Knives — 11 rows, each run twice, 22 runs, 0 misses

| # | cut | predicted | measured |
|---|---|---|---|
| K1 | revert the denominator to three named dirs | rc 2 (stale entries) | **rc 2 — but via `MIN_FILES`**: 258 < 300, `APPARATUS FAILURE`. Right code, **wrong mechanism**, because the floor is checked before the list |
| K2 | delete the RECORD list | rc **1** | **rc 2** — a missing control is `CANNOT JUDGE`, not a tree fault. **Mispredicted.** Same correction D-REVJUDGE's K1c made |
| K3 | remove one RECORD entry | rc 1 | ✅ rc 1, `scratchpad/i2_frame.py` reported unacknowledged |
| K4 | acknowledge a non-composer | rc 2 | ✅ rc 2, stale entry |
| K5 | empty the self-test table | rc 2 | ✅ rc 2 — **rc 0 on the pre-slice tool**, printing `self-test PASS (rows A-D: …)` |
| K6 | drop the `HANDLES` sense | rc 2 | ✅ rc 2, polarity bar |
| K7 | skip `scratchpad` | rc 2 | ✅ rc 2, 263 < 300 |
| K8 | gut `classify()` | rc 2 | ✅ rc 2, frozen self-test rows A and C |
| K9 | plant a composer under `tape/` | rc 1 | ✅ rc 1 at 326 files — **rc 0 / `ALL PASS` on the pre-slice tool at 258** |
| K10 | live probe imports a RECORD | rc 1 | ✅ rc 1, `RECORD IS REACHABLE` |
| K11 | edit a RECORD file | rc 2 | ✅ rc 2, digest `b73bec…` → moved |

GREEN control after every restore, rc 0, 11 of 11. The restore point was a
scratchpad snapshot taken after the change and before the first cut; every cut
asserted it had changed the file before its result was read.

**K5 and K9 are the slice's justification**: both read `rc 0`, `ALL PASS` at
`6270177`.

### 6.4 Corpus — 19/19, all rc 0

`basic-reloc` · `repack-machine` · `unit-test` **58/58** · `audit-citations`
(699 swept, self-tests 10/10 11/11 12/12 14/14, 4 advisory acknowledged, re-run
after the `TODO.md` edit) · `preflight-check` **95 guarded / 0 unguarded** ·
`injector-check` **325 files, 3 records, 0 offenders, self-test 4/4** ·
`latch-check` **16/16** · `dexp5-pin` **16 rows vs Philips_VG_8020** ·
`linemax-acceptance` **60/60** · `lnblank-acceptance REPEAT=2` **536/536 gating
rows across vg8020/cf3300/zb, 0 allowlisted** · `subrom-acceptance` ·
`subrom-inttest` · `graphics-floor-acceptance` · `graphics-acceptance` · `probe`
· `fat-error-acceptance` · `diskbasic-acceptance` **ALL CONVERGED** ·
`bdos-acceptance` **ALL CONVERGED byte-for-byte** · `lof-acceptance` **45 cases,
0 unfiled divergences, 0 oracle drift, 0 mangled**, whole log captured (59
lines).

⚠️ **`lof-acceptance` sighting 3 did not occur — the TENTH consecutive slice.**
The two filed `dir` divergences (`rand_put`, `rnd_put_len`) are the known ones.

### 6.5 What this slice did NOT do

* **No change to the predicate.** The filed fold is not shipped (§3.1).
* **The three records were not rewritten or deleted** (§2.6).
* **`tools/check_probe_preflight.py` was not widened.** It carries the identical
  `SCAN_DIRS` and **6** out-of-scope `.py` launch openMSX. Its rule has not been
  walked, and widening it without walking it would be the mistake this whole arc
  keeps recording. Filed in `TODO.md`.
* **No floor was put on `EXEMPT`.** `SHIPS`/`HOLDS` remain unchecked claims, as
  `TODO.md` already records.

### 6.6 Re-open bars

* **The split literal / unknown-spelling class.** Re-open only with a body that a
  folding or soup predicate flags and the shipped rule does not, **and** which is
  not caught by rule (b) — i.e. an actual planted or landed example, not a
  constructed one. The bar is high on purpose: two independent predicates,
  including the maximal text predicate, each found **0** over 982 commits.
* **`MIN_FILES = 300`** is a floor on today's 325, not a measurement of a
  legitimate minimum. A deliberate cleanup that removes 26+ `.py` files will read
  as `APPARATUS FAILURE`; that is an instrument verdict for a human to lower, not
  a defect.
* **`MIN_SELFTEST_ROWS = 4`** is the current table size, so the table cannot
  shrink at all. Stated limit: it does not stop a row being *weakened* in place,
  only removed — K6 catches a sense being dropped, nothing catches a vector being
  made easier.

### 6.7 Filed-claim score

**1 checked — 1 right-but-misdirected.** The residual was accurate, and it
explicitly called itself *"a stated limit, not a filed defect"*, which was the
right classification. What it did was point every reader at the **predicate** of a
gate whose **denominator** was open, for 252 commits, with the gate printing a
false sentence the whole time. Arc total: **twenty-four checked — eleven wrong,
six right-but-misdirected, seven right** [[filed-justification-is-a-claim]].

Related: [[injsink-slice]] · [[lastinj-slice]] · [[latch-trigger-slice]] ·
[[readout-blind-to-its-own-subject]] · [[correct-claim-can-be-the-wrong-question]] ·
[[gate-can-be-green-while-measuring-nothing]] ·
[[a-policy-that-forbids-by-provenance]] · [[knife-aimed-at-the-wrong-gate]] ·
[[apparatus-is-part-of-the-measurement]]

