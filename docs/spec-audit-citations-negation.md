<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# D-NEGJUDGE — check 3's exemption rule: the filed negation window, measured

**Subject.** `tools/audit_citations.py` check 3 (the advisory section-citation
rule) exempts a header on any occurrence of a `CITATION` token, in any polarity
and any sense. Check 1 has a `NEGATION` window; check 3 has none. Filed by
D-REVJUDGE as a standing residual in `TODO.md`, detail
[`docs/spec-audit-citations-review.md`](spec-audit-citations-review.md) §2.6.

**Result in one line.** The filed fix is **DECLINED on a measurement**: over all
981 commits a negation window produces **38** findings the shipped rule does not,
and **0 of the 38** lack a document citation — precision **0**. The defect the
residual was filed for is real, but its mechanism is **vocabulary, not polarity**,
and one token carries all of it: removing `VDP` from `CITATION` produces **9**
extra findings over the same 981 commits, **9 of 9** genuine, all of them one
header. That one token is what shipped. A second, unrelated defect was measured
on the way and also shipped: **all four self-test tables print `0/0` and exit 0
when emptied**.

---

## 0. The question

The residual names a property of the tooling — *check 3 has no negation window*.
[[correct-claim-can-be-the-wrong-question]] says such properties are usually true
and usually decide nothing. The load-bearing question is not whether the window is
absent. It is:

> **Would a negation window ever have caught a header that is genuinely
> uncited — and if not, is there something else that would?**

Both halves are answerable exactly, by walking check 3's rule and each candidate
variant over every commit in the repository and asking, of each finding a variant
adds, whether that header's own comment block carries a document reference
anywhere.

Three subordinate questions, all from the residual:

* **Q1** — is *"3 of 48 exempt headers rest on a weak or negated token"* true?
* **Q2** — is *"all three are substantively attested, so the class has 0 real
  members today"* true? The second half is a **judgement**, not a measurement.
* **Q3** — `map.grauw.nl` is cited by two of the three and is not in `CITATION`'s
  vocabulary at all. Does adding it change anything, ever?

---

## 1. The denominator

### 1.1 What check 3 actually scans

`INLINE_CITE_TARGETS = {"disk"}`, so check 3's corpus is `TARGETS["disk"]` =
`disk/*.asm` + `disk/*.inc` — **8 files** at `d1cf70c`. Every number below is over
that corpus. Widening beyond it was measured and declined by D-REVJUDGE (348
findings vs 3); this slice does not revisit it.

Section headers in those 8 files, by verdict — measured with the shipped
`section_findings`, imported, never re-implemented:

| verdict | count |
|---|---:|
| `on-header` (citation on the header line) | 28 |
| `cited` (citation in the header's own block) | 20 |
| **exempt = on-header + cited** | **48** |
| `structural` | 5 |
| `REVIEW` (the advisory findings) | 3 |

**48 exempt confirms Q1's denominator exactly.**

### 1.2 The walk

981 commits (`git rev-list HEAD`), `git ls-tree -r` + `git cat-file` with a
per-blob analysis cache. For each commit and each variant, the `[REVIEW]` set;
and for every header a variant flags that the shipped rule does not, whether that
header's block carries a **strong** reference anywhere — a `§`, a spec filename,
`PROVENANCE`, a named datasheet / handbook / standard, or the `map.grauw.nl` URL.
A variant-extra whose block *does* carry one is a false positive by construction.

The rule loop is imported from the shipped tool and the variants are installed by
swapping the module-global `CITATION` for a shim. A negation window needs to know
*where* a line sits, so the file's lines are handed to `section_findings` as an
index-carrying `str` subclass — every path in the shipped loop (`.lstrip`,
`.strip`, the regexes) works on it unchanged. **The walker and the gate are one
rule**, which is why `section_findings` was extracted in the first place.

### 1.3 Files this slice ADDS, checked against the sweep's own filter

`SWEEP_EXTS = (".md", ".asm", ".inc", ".py", ".tcl", ".txt", ".bas", ".yml")`,
`SWEEP_SKIP` does not contain `docs`.

| file | ext | in `SWEEP_EXTS`? | swept? |
|---|---|---|---|
| `docs/spec-audit-citations-negation.md` (**new**) | `.md` | yes | **+1** |
| `tools/audit_citations.py` (modified) | `.py` | yes | already counted |
| `tools/citations-advisory-allow.txt` (modified) | `.txt` | yes | already counted |
| `TODO.md`, `docs/spec-audit-citations-review.md` (modified) | `.md` | yes | already counted |

⇒ swept files **696 → 697**. (D-DOCJUDGE and D-BYTEJUDGE both got this wrong by
not writing the table out.)

---

## 2. Falsify by measuring

### 2.1 The variants

| id | rule |
|---|---|
| **V0** | shipped |
| **V1** | + `NEGATION` window, 3 lines — check 1's window, borrowed verbatim |
| V1b | + `NEGATION` window, 1 line |
| **V2** | + `map.grauw.nl` in `CITATION` |
| V3 / V3b | V1 + V2 (with / without the URL immune to the window) |
| V4 | − the four bare hardware nouns (`Z80`, `TMS9918`, `PSG`, `VDP`) |
| V6 | − `VDP`, − `PSG` |
| **V7** | **− `VDP`** |
| V8 | − `PSG` |
| V9 | − `oracle`, − `VDP`, + `map.grauw.nl` |
| V10 | − `oracle` |

### 2.2 🔴 The answer: the filed fix has precision 0 over the whole history

| variant | `[REVIEW]` at HEAD | commits differing from shipped | extra headers **ever** | of which genuinely uncited |
|---|---:|---:|---:|---:|
| V0 shipped | 3 | 0 | — | — |
| **V1 negation, 3-line** | **11** | **760** | **38** | **0** |
| V1b negation, 1-line | 8 | 708 | 11 | 0 |
| V2 `+map.grauw.nl` | 3 | **0** | 0 | 0 |
| V3 V1+V2 | 6 | 760 | 27 | 0 |
| V3b V1+V2, not immune | 11 | 760 | 38 | 0 |
| V4 − 4 hardware nouns | 4 | 708 | 9 | **9** |
| V6 − `VDP`,`PSG` | 4 | 708 | 9 | **9** |
| **V7 − `VDP`** | **4** | **708** | **9** | **9** |
| V8 − `PSG` | 3 | **0** | 0 | 0 |
| V9 − `oracle`,− `VDP`,+ URL | 4 | 708 | 9 | **9** |
| V10 − `oracle` | 5 | 604 | 4 | 0 |

**A negation window would never have caught anything.** Not once in 981 commits.
It would have disagreed with the shipped rule in **760** of them, and every single
one of the 38 headers it adds carries a document citation in its own block.

### 2.3 🔴 WHY it fails, and it is not a tuning problem

The eight headers V1 adds at HEAD, with the citation the shipped rule exempted on
and the negation token that kills it:

| header | the citation the window discards | killed by |
|---|---|---|
| `kernel.asm:441` `_GDATE entry` | `docs/tier2-gdate-spec.md`, on the block's last line | `no` in *"no stock bytes"*, two lines earlier |
| `runtime.asm:8` `page-0 helpers` | `MSX2 TH ch.2/2.4` | **`CLEAN-ROOM`**, same line |
| `runtime.asm:167` `dirio_in_body` | `§5.3`, `§5.2` | `no` in *"no echo"* |
| `runtime.asm:197` `const_body` | `map.grauw.nl` | **`CLEAN-ROOM`**, same line |
| `runtime.asm:222` `conin_body` | `map.grauw.nl` | **`CLEAN-ROOM`**, same line |
| `runtime.asm:279` `login_body` | `§5.3` | `rather than` |
| `runtime.asm:323` `verify_body` | `§5.3`, `§5.4` | **`NO`** — matched inside **`NO-OP`** |
| `kernel.asm:221` `console entries` | `tier2-m22-cpmver-spec.md §4.5` | `instead` |

Two mechanisms, both structural:

🔴 **`CLEAN-ROOM` is a `NEGATION` token, and it is also the prefix of this
project's citation convention.** The house style for a cited section is

> `; CLEAN-ROOM: published CONST contract (map.grauw.nl) + CHSNS; no oracle bytes.`

— attestation keyword, then the citation, then what was *not* used, on one line.
A negation window borrowed from check 1 therefore **discards the citation on
every header that follows the convention**. It is not that the window is too wide;
it is that in check 3's corpus the negation and the citation are deliberately
adjacent.

🔴 **`\bno\b` matches inside `NO-OP`.** `verify_body`'s `§5.3` is thrown away by
the hyphen in a phrase that is not a negation at all. This is
[[reword-the-subject-or-teach-the-rule]] and the `byte[- ]?cop` lookbehind, one
check over again: a lexical boundary the rule cannot see.

### 2.4 The model being copied — check 1's window, knifed

Check 1's window is what the residual proposed borrowing, so it is measured
before being borrowed. Over the full 116-file scanned corpus at `d1cf70c`:

| | count |
|---|---:|
| `FORBIDDEN` token hits | **109** |
| suppressed by `NEGATION` | **109** |
| … negation on the matched line | 83 |
| … negation only in the two preceding lines | **26** |
| affirmative (findings) | **0** |

The 26 lookback-only suppressions were read individually. **All 26 are genuine
attestation sentences wrapped across a comment break** — *"Nothing here is derived
from a reference-ROM / disassembly."* The lookback is doing exactly the job its
comment claims. Suppressing token: `clean-room` 43, `no` 41, `not` 8, `never` 8,
`nothing` 7, `rather than` 1, `instead` 1.

⇒ **check 1's window is sound, and that is precisely why it does not transfer.**
Check 1's vocabulary is rare and appears in this corpus *only* inside
attestations, so a negation context is nearly a certainty. Check 3's vocabulary is
common and appears in ordinary prose, next to the attestation keyword by
convention. Same window, opposite corpus. The `clean-room` row is the tell: 43 of
check 1's 109 suppressions come from the very token that, in check 3, sits in
front of the citation.

### 2.5 🔴 Q2 — "all three substantively attested" is 2 of 3, and the third is
the one the filed fix cannot catch

The three weak-token exemptions, re-read in full:

| header | exempt on | verdict |
|---|---|---|
| `runtime.asm:197` `const_body` | `oracle` in *"no oracle bytes"* | **attested** — the same line reads *"published CONST contract (map.grauw.nl)"*. A URL to a public artifact is a document reference; `CITATION` simply does not carry it. |
| `runtime.asm:222` `conin_body` | `oracle` in *"no oracle bytes"* | **attested** — *"published CONIN contract (map.grauw.nl)"*, same shape. |
| `runtime.asm:423` `int_h_body` | **`VDP`** in *"A bare VDP ack is not enough"* | 🔴 **prose, not a citation.** |

On the third: the block's provenance claim is *"the MSX1 standard,
BIOS-agnostic"*. That names a standard but no document — no `§`, no spec
filename, no URL, no datasheet. `§8.75` appears further down, on a **code** line
outside the block. The token that exempts it, `VDP`, is a subsystem abbreviation
used as an ordinary noun in a sentence about what an implementation must do.
**This is a citation-less header, and it is a review candidate.**

It is also the same class as `kernel.asm:65`, which the 2026-07-04 human triage
and D-REVJUDGE §2.5 both deliberately **kept** as a review candidate despite a
12-line attestation: *what counts as a citation is a judgement this tool declines
to make*. `int_h_body` attests less richly than that one. Treating it as a finding
is the consistent call, not a new bar.

**And the finding it should cite exists.** `disk/docs/provider-oracle-scope.md`
**§8.70** documents this handler directly — O-2, the KEYINT chaining contract,
naming the stock `$0038` handler, the main-ROM KEYINT body, and the H.KEYI /
H.TIMI hooks, all from black-box probe runs. The header block restates §8.70's
content without ever naming it. Its own name once carried the reference —
*"(A-2/8.70)"*, a bare number the rule cannot match either — and lost it in the
A-3 rename (`71b1096`). **The rule's blind spot is why nobody noticed.**

⇒ **Q2 is wrong on 1 of 3.** The class does not have 0 real members; it has one,
and it has had one for **708 commits**.

### 2.6 🔴 The filed fix does not catch the one real member

`int_h_body` appears in **no** negation variant's extra set — V1, V1b, V3, V3b all
leave it exempt. The sentence that exempts it, *"A bare VDP ack is not enough"*,
contains `not`, but the loop does not stop there: it keeps scanning and finds
`VDP` again five lines later in *"(KEYINT does its own VDP ack)"*, whose 3-line
window carries no negation token.

So the filed fix is wrong in **both** directions at once: it flags the two headers
that *should* be exempt and misses the one that should not.

### 2.7 Q3 — `map.grauw.nl` changes nothing, ever

**0 commits out of 981.** Adding the URL to `CITATION` changes no verdict at any
point in the repository's history, because both headers that cite it are already
exempt on `oracle` in the same sentence. A rule change with no observable effect
is [[gate-can-be-green-while-measuring-nothing]] in its purest form.

The tempting repair — *drop `oracle`, add `map.grauw.nl`, so those two stay exempt
for the **right** reason* — is **V9, and V9 is byte-for-byte identical to V7 at
every one of the 981 commits.** The two edits cancel exactly. Measured, not
argued. Dropping `oracle` on its own (V10) costs 4 false positives and finds 0.

### 2.8 The instrument sweep that settled the design

The vocabulary axis, swept the way D-REVJUDGE swept the distance axis: remove one
alternative from `CITATION` at a time and count. **22 of the 25 alternatives are
carrying no exemption at all.** Only three are load-bearing:

| removed | `[REVIEW]` | headers it alone was exempting |
|---|---:|---|
| `§` | 8 | `kernel.asm:43`, `runtime.asm:270`, `:279`, `:323`, `:336` |
| `oracle` | 5 | `runtime.asm:197`, `:222` |
| **`VDP`** | **4** | **`runtime.asm:423`** |
| each of the other 22 | 3 | — |

`PSG` never exempted anything, in any commit. `Z80` and `TMS9918` likewise — and
both are part numbers whose datasheets *are* chain-terminating sources per
`docs/clean-room-audit.md`, so they belong in the vocabulary. `VDP` and `PSG` are
subsystem abbreviations, ordinary English in this corpus. Only `VDP` has ever cost
anything, so only `VDP` is removed: **the smallest edit with a measured effect,
and its effect is 9 of 9.**

### 2.9 🔴 A second defect, found by asking what a dead subject scores

`SECTION_SELFTEST` emptied to `[]`, everything else untouched:

```
rule self-test 10/10, listing self-test 11/11, dump self-test 12/12, section self-test 0/0
CLEAN (gating checks).            rc 0
```

**`0/0` prints and the tool exits 0.** All four self-test tables have this hole —
there is no floor on any of them. This is the *"0/0 tally printed ALL CONVERGED"*
shape ([[apparatus-is-part-of-the-measurement]]), live in the instrument this arc
has spent six slices hardening, and it is exactly the failure D-CITEJUDGE closed
one level out with `MIN_FILES`: **a collapsed denominator reads as success.**

It is not caught by the allowlist, because emptying the table blinds the
*control*, not the *rule* — the findings are unchanged, so the list still matches.
The next rule change is the one that would go unnoticed.

---

## 3. Design

Two changes to `tools/audit_citations.py`, one to the acknowledged list. **No
`.asm` file is edited**, so ROM-neutrality is true by construction and proved by
hash anyway.

### 3.1 `CITATION` loses `VDP`

One alternative removed, with the measurement written beside it. `datasheet`,
`hardware fact`, `Z80`, `TMS9918`, `WD2793` and the rest are untouched: a header
that cites a real hardware document still exempts on the document, which is the
point.

### 3.2 The acknowledged list gains its 4th entry

`disk/runtime.asm`, digest `d8340dfd8ba4`, for
`int_h_body - the OLD page-1 $0038 handler (A-2/A-2b) — SUPERSEDED by A-3`. The
reason records what §2.5 measured: the block attests in prose, cites no document,
and the finding it restates is `provider-oracle-scope.md` §8.70 — so the human's
remedy is to name §8.70 in the block, or to remove the dead body the header
describes. The tool does not make that call.

⚠️ The digest is `sha256("<path>|<header name>")[:12]`, so **renaming this header
or citing it invalidates the entry and exits 2** — which is the intended
behaviour, not a hazard: it is how the list stays a control rather than a
suppression list.

### 3.3 Two new self-test vectors — the class pin

`SECTION_SELFTEST` 12 → 14:

* a header whose only citation-shaped word is a bare subsystem abbreviation in
  ordinary prose → **`REVIEW`**. This is the pin: re-adding `VDP` fails it.
* a header citing a real hardware datasheet → **`cited`**. This is the
  counter-pin: it fails if the removal is over-applied to `datasheet`.

Both synthetic, per §3.2 of the review spec — check 3 refuses a *property*, not a
*kind of text*, so a positive vector is only a header with nothing to cite.

### 3.4 A floor on every self-test table

`MIN_SELFTEST_ROWS = 8`, plus a polarity requirement: each table must contain at
least one vector of each sense (for check 3, at least one expecting `REVIEW` and
at least one expecting `cited`). A table below either bar exits **2** —
instrument, not tree.

**What it does not catch, stated:** trimming 14 vectors to 9 still passes. The
failure mode being closed is a *blinded* control reading as green, not vector
attrition. The tables' real defence against attrition is that every vector is
there because a knife or a measurement put it there.

### 3.5 The record

`docs/spec-audit-citations-review.md` §2.6 gets a closure note pointing here, and
`TODO.md`'s residual is marked ✅ in place.

---

## 4. Predicted GREEN, at exact values — fixed BEFORE the change

| # | measurement | predicted |
|---|---|---|
| G1 | `python3 tools/audit_citations.py` | **rc 0** |
| G2 | files scanned | disk **8**, basic **107**, tape **1** |
| G3 | `[FORBIDDEN]` / `[NO-ATTEST]` / `[PRIVATE-REF]` | **0 / 0 / 0** |
| G4 | provenance-bearing | **97 / 181 / 15** |
| G5 | `[REVIEW]` advisory | **4**, all acknowledged |
| G6 | the 4th is | `disk/runtime.asm:423` `int_h_body …` (`d8340dfd8ba4`) |
| G7 | self-tests | **10/10, 11/11, 12/12, 14/14** |
| G8 | files swept | **697**, 2 listing-allowlisted, 1 dump-allowlisted |
| G9 | `sha256 build/disk.rom` | `2c630d3dfeec727b5ec87c3c3140cfa5fdedc6b6a144d346467e6142b6e33c27` |
| G10 | `sha256 build/sub.rom` | `b2935188963eda429d61fc6ded6350a8067f1ccc09b5d4a9edc4713da2697e5e` |
| G11 | `sha256 build/basic-reloc.rom` | `3f1cd5866314270e3ae325b56f8707e62f26b7d65210f1c1d64510b7c48594af` |
| G12 | `sha256 build/zerobas-main-eu.rom` | `d061cd58ad4cede795221fef1c0b0c9ae2c0d0c7a090f6a2b8fcef1154d9e28e` |
| G13 | walls, from CLEAN | low **23 B**, page 1 **356 B**, sub p0 **3869 B**, sub p1 **2324 B** |
| G14 | closure walks | abi **122+4**, `--page0` **718+15**, `--page1` **522+41** |
| G15 | dead code | main **1551**/**285** → 0, sub **1451**/**102** → 0 (+1 allowlisted) |
| G16 | `kwtable` | **1041 B** |
| G17 | corpus | **19/19** |

**G15 is the one to watch.** `check_dead_code.py`'s `external_names` roots are
`['sub','tools']` and it reads comments — so prose added to
`tools/audit_citations.py` can seed a label. `disk/` is not a root and neither
`int_h_body` nor `pg0_mainrom_in` exists in `basic/` or `sub/` (checked), and the
`.txt` allowlist is invisible to the sweep entirely (`.asm`/`.inc`/`.py` only).
**Any movement in 285/102 is a finding about this slice's own prose.**

---

## 5. Predicted RED, with knives

Each run **twice**. The restore point is a scratchpad snapshot taken **before the
first cut**, never `git checkout --` ([[knife-cleanup-restores-from-head]]); the
runner refuses to start unless its subject is green.

| # | cut | predicted |
|---|---|---|
| K1 | put `VDP` back in `CITATION` | **rc 2** — advisory 3, entry `d8340dfd8ba4` stale |
| K1c | control: no cut | **rc 0**, advisory 4 |
| K2 | `section_findings` returns `[]` (rule fully blind) | **rc 2** — self-test misclassifies *and* 4 entries stale |
| K3 | `SECTION_SELFTEST = []` | **rc 2** via §3.4 — **was rc 0 before this slice** |
| K4 | drop every `REVIEW`-expecting vector from `SECTION_SELFTEST` | **rc 2** via the polarity bar |
| K5 | delete the `d8340dfd8ba4` line from the allowlist | **rc 2** — unacknowledged finding |
| K6 | delete `tools/citations-advisory-allow.txt` | **rc 2** |
| K7 | plant a header in `disk/runtime.asm` whose only citation-shaped word is a bare `VDP` in prose | **rc 2** — advisory 5, the class pin firing on the tree |
| K8 | plant a header with no citation-shaped word at all | **rc 2** — advisory 5 |
| K9a | dead subject: **delete** all 8 `disk/*.asm\|inc` | **rc 2** via `MIN_FILES` — the glob collapses |
| K9b | dead subject: **truncate** all 8 to empty | **rc 2** via 4 stale allowlist entries — the glob does **not** collapse, so `MIN_FILES` cannot see this one |
| K10 | `make basic-reloc` with K1 in place, run twice | **fails both times** (PHONY) |

⚠️ **K7 and K8 must be checked for having CUT.** D-REVJUDGE's K3 came back green
twice because its plant contained the word `PROVENANCE` and exempted itself
([[knife-aimed-at-the-wrong-gate]]). Every plant's text is asserted against
`CITATION` before the knife is believed.

---

## 6. As-built

### 6.1 Predictions, scored

**17 of 17 GREEN predictions hit, first try.** ROM-neutral, proved by hash: all
four images byte-identical to `d1cf70c` (`disk.rom` `2c630d3d…`, `sub.rom`
`b2935188…`, `basic-reloc.rom` `3f1cd586…`, `zerobas-main-eu.rom` `d061cd58…`).
Walls from clean **23 / 356 / 3869 / 2324**; closure **122+4 / 718+15 / 522+41**;
dead code main **1551**/**285** → 0, sub **1451**/**102** → 0 (+1 allowlisted);
`kwtable` **1041 B**. Advisory **4**, all acknowledged; self-tests **10/10, 11/11,
12/12, 14/14**; swept files **697**, exactly as §1.3's extension table predicted.

**G15 held.** ~120 new prose lines went into `tools/audit_citations.py`, an
`external_names` root that is read *including comments*, and the seed counts did
not move. `int_h_body` and `pg0_mainrom_in` were checked for collisions in
`basic/` and `sub/` before being written; the long justification went into the
`.txt`, which the sweep cannot see at all.

### 6.2 Knives — 11 rows, each run twice, 22 runs, 0 misses

| # | cut | predicted | got | what actually caught it |
|---|---|---|---|---|
| K1 | `VDP` back in `CITATION` | rc 2 | **rc 2** | the new §3.3 self-test vector, which runs first |
| K1b | K1 **and** both new vectors removed | rc 2 | **rc 2** | the allowlist — `d8340dfd8ba4` no longer reported, self-test a clean 12/12 |
| K2 | `section_findings` returns `[]` | rc 2 | **rc 2** | self-test (and 4 stale entries behind it) |
| K3 | `SECTION_SELFTEST = []` | rc 2 | **rc 2** | the new table floor — **this was rc 0 before this slice** |
| K4 | only one sense left in the table | rc 2 | **rc 2** | the new polarity bar |
| K5 | drop the `d8340dfd8ba4` entry | rc 2 | **rc 2** | unacknowledged finding |
| K6 | delete the allowlist file | rc 2 | **rc 2** | all 4 unacknowledged |
| K7 | plant: exempt-on-bare-`VDP` header | rc 2 | **rc 2** | the class pin, firing on the tree |
| K8 | plant: header with no citation word | rc 2 | **rc 2** | the base rule |
| K9a | dead subject: disk sources **deleted** | rc 2 | **rc 2** | `MIN_FILES` — the glob collapsed |
| K9b | dead subject: disk sources **emptied** | rc 2 | **rc 2** | 4 stale entries; `MIN_FILES` cannot see this one |
| K10 | `make basic-reloc` with K1 in place, ×2 | fails both | **rc 2, rc 2** | PHONY, so re-running does not defeat it |

**K1b is the row that matters.** It proves the two controls are independent in the
direction D-REVJUDGE could not test: with the rule reverted *and* the new vectors
gone, the self-test reports a clean **12/12** and the **allowlist** is what exits
2. Either control alone catches a reverted rule; the pair is what makes a silent
`rc 0` need both removed.

⚠️ **Both plants were asserted to CUT before their results were believed** — the
runner checks each plant's text against `CITATION` and `STRUCTURAL_HDR` and
refuses to run if either matches. That check exists because D-REVJUDGE's K3 came
back green twice on a plant containing the word `PROVENANCE`
([[knife-aimed-at-the-wrong-gate]]). The restore point was a scratchpad snapshot
taken after the change and before the first cut, never `git checkout --`
([[knife-cleanup-restores-from-head]]), and the runner refuses to start unless
its subject is green.

### 6.3 Corpus

**19/19 green**, sequential, one at a time, each log captured whole with
`> file 2>&1`, from `rm -rf build`. `basic-reloc` · `repack-machine` ·
`unit-test` · `audit-citations` · `preflight-check` · `injector-check` ·
`latch-check` · `dexp5-pin` · `linemax-acceptance` · `lnblank-acceptance
REPEAT=2` · `subrom-acceptance` · `subrom-inttest` · `graphics-floor-acceptance`
· `graphics-acceptance` · `probe` · `fat-error-acceptance` ·
`diskbasic-acceptance` · `bdos-acceptance` · `lof-acceptance`.

`lof-acceptance` captured whole (59 lines): **45 cases, 0 unfiled divergences, 0
oracle drift, 0 mangled** — **no sighting 3**, the ninth consecutive slice
without one.

### 6.4 What this slice did NOT do

* **No negation window anywhere in check 3.** Declined on the measurement in §2.2,
  not on cost. Re-open bar is in §6.5.
* **`map.grauw.nl` not added.** 0 changed verdicts in 981 commits (§2.7).
* **`oracle` not removed.** 4 false positives, 0 real (§2.8) — and paired with the
  URL it is exactly a no-op (V9 ≡ V7 at all 981 commits).
* **`PSG`, `Z80`, `TMS9918` kept.** `PSG` has never exempted anything; the other
  two are part numbers whose datasheets are chain-terminating sources.
* **No `.asm` edited.** `runtime.asm:423` is *acknowledged*, not fixed: whether to
  cite §8.70 or delete the dead body is a human judgement, filed in `TODO.md`.
* **Check 3 stays advisory and disk-only.** Promotion (red in 918 of 980 commits)
  and widening (348 findings) were measured and declined by D-REVJUDGE.

### 6.5 Re-open bars

**For a negation window:** a discriminator that (a) leaves `runtime.asm:8`,
`:167`, `:197`, `:222`, `:279`, `:323`, `kernel.asm:221` and `:441` exempt — the
eight house-style headers a 3-line window discards — (b) still flags a header
whose *only* citation-shaped word is negated, and (c) scores at least one genuine
finding across the 981-commit walk that the shipped rule misses. The corpus for
(a) is `disk/*.asm|inc` at `d1cf70c`; the walk is ~4 minutes to reproduce.

**For `map.grauw.nl` or any other vocabulary widening:** a commit, anywhere in the
walk, whose verdict it changes. Adding vocabulary that changes nothing is
[[gate-can-be-green-while-measuring-nothing]] by definition.

**For the self-test floor:** it does not catch vector *attrition* (14 → 9 passes).
Closing that needs an argument for pinning exact table lengths, which makes every
deliberate vector addition a two-place edit — a real cost, not obviously worth
paying.

### 6.6 Filed-claim score

D-REVJUDGE filed three claims in §2.6. **1 right, 1 right-but-misdirected, 1
wrong.**

| filed | measured |
|---|---|
| *"3 of the 48 exempt rest on a weak or negated match"* | **right** — 48 exempt, exactly 3 with no strong reference in their block |
| *"check 1 has a negation window; check 3 does not"* | **right, and misdirected** — true, and the wrong axis: the fix it implies has precision 0 over 981 commits, while the vocabulary axis it does not name has 9 of 9 ([[correct-claim-can-be-the-wrong-question]]) |
| *"all three are substantively attested … 0 real members today"* | **WRONG on 1 of 3** — `runtime.asm:423` names a standard, not a document; the class has had **1** member for **708** commits, and the filed fix does not catch it |

Arc running total: **twenty-three checked — eleven wrong, five right-but-
misdirected, seven right** ([[filed-justification-is-a-claim]]).
