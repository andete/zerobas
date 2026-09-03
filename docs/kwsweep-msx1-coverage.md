<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# MSX1 BASIC keyword-completeness sweep — the coverage denominator

**Status:** **RE-PINNED 2026-07-27** against a clean-built HEAD · probe
[`probes/basic/basic_probe_kwsweep.py`](../probes/basic/basic_probe_kwsweep.py) ·
gate `make kwsweep` · reference Philips VG-8020 · zerobas
`C-BIOS_MSX1_EU_REPACK_DISK` at `zerobas-main-eu.rom=4ea7a29918df`
(`sub.rom=77c6ac54b405`, `disk.rom=2c630d3dfeec`), `git=e9843c4`

> **The ROM hash is the pin, not the git rev** — and the previous pin is the
> reason that sentence is in this document. The 2026-07-26 sweep ran at
> `git=b531c49` / `zerobas-main-eu.rom=05f43b425e5b`, and the two disagreed **on
> purpose**: the tree was then 14 B over the page-1 ceiling
> ([`spec-traps-t5-interval.md`](spec-traps-t5-interval.md) §4.3), so
> `make basic-reloc` failed and `build/zerobas-main-eu.rom` was the **last
> successful build**, not HEAD.
>
> ✅ **Re-pinned.** The overrun was cleared by `a5a3af2`
> ([`spec-basic-direct-ctrl.md`](spec-basic-direct-ctrl.md) §Cost); this run is
> against a `rm -rf build && make basic-reloc` of `e9843c4` (page-1 free 8 B, low
> region 5 B), so the ROM hash and the git rev now agree. **The main-ROM hash
> moved (`05f43b…` → `4ea7a2…`) and every tally below is unchanged** —
> SILENT-GAP=8, MISSING=6, NO-ORACLE=5 (⚠️ those NO-ORACLE five were a BLIND
> APPARATUS, not an absence of oracle — see the NO-ORACLE section, closed
> 2026-09-03). The findings were not an artifact of the
> stale build. The probe fingerprints the ROMs before and after every run and
> aborts the report if they change mid-flight — the machine XML points straight
> at the project tree, so a concurrent `make` in another session silently changes
> the measurement target.

**The sweep already earned its keep as a regression detector.** The first run
(`664f4898`) flagged `TIME` as a SILENT-GAP; this run picks up `TIME` as
tokenised and SUPPORTED with no edit to the probe — the `time`/`timetick` rows
moved on their own when the feature landed.

## Why this exists

zerobas found two missing keywords **by accident**, six days apart, and both had
the same silent shape — the word parses as an ordinary **variable**, so nothing
errors and the program simply computes the wrong answer:

* **`TIME`** — collateral from the T3 KEY slice (`20e04b4`). Parses as the
  variable `TI`, reads 0 forever, so `IF TIME-T<400 GOTO` never terminates.
* **`TAB(`** — found while auditing coverage for this sweep. Worse: it was
  recorded as *"Already faithful (NO work)"* in
  [`spec-basic-df2-2-intarg-coercion.md`](spec-basic-df2-2-intarg-coercion.md)
  §1.2, because `PRINT TAB(99999)` raises ERR 6 on **both** sides. It does so for
  structurally different reasons — zerobas has no `TAB(`, so `TAB` is an *array*
  and the subscript bound-check produces the same code. **The differential case
  passed; the feature does not exist.**

Two accidental finds is a pattern, not luck. This sweep measures the whole
reserved-word set at once so "complete MSX1 BASIC" has an honest denominator.

## Method — two layers, because one lies

| Layer | Question | How |
|---|---|---|
| **1 CRUNCH** | does zerobas *tokenise* the word? | store `1 <body>`, diff token bytes vs the VG-8020 |
| **2 SUPPORT** | does a *program* observe the right thing? | execute a usage where a variable/array parse gives a **visibly different** answer, compare outcome class |

Neither layer is sufficient alone, and the repo already owns both counter-examples:

* **`INTERVAL`** (the `60e0ab6` retraction) — absent from every MSX1 keyword
  table, because it is not a keyword at all but the compound `INT`+`"ER"`+`VAL`.
  It works. *Layer 1 alone would call it missing.*
* **`TAB(`** — identical error code on both sides. *Layer 2 alone, written
  carelessly, calls it present.*

Layer 2 rows are therefore designed against the failure mode: `PRINT TAB(99999)`
is the in-tree example of how **not** to write one. The probe keeps a deliberately
**WEAK** row (`time`, using `TIME>=T` → `0>=0` → true on a machine with no `TIME`
at all) as a standing demonstration that a passing differential proves nothing
unless the absent-feature parse answers *differently*. It is excluded from the
tally.

## Headline

Of **162** MSX1 reserved words swept: **124 tokenise**, **38 do not**. Of those 38,
**3 work anyway** (`DEFSNG`/`DEFDBL`/`DEFSTR` — no `kwtable.inc` entry by design,
they reach `ex_def_type` as `DEF_TOKEN` + literal ASCII) and **1 is `INTERVAL`**
(needs no token). **34 words are genuinely absent.**

> ✅ **THE `DEFSNG`/`DEFDBL`/`DEFSTR` CLAUSE IS HISTORY — D-DEFTYPETOK
> (2026-08-19).** All three have whole-word `kwtable.inc` rows and single-byte
> tokens of their own now (`$AB`/`$AD`/`$AE`, beside `DEFINT`'s `$AC` from
> D-DEFINTTOK the day before), so they **tokenise**, the `DEF_TOKEN` + literal
> ASCII mechanism is gone, and `ex_def_type` is gone with it (merged into
> `ex_deftype`, basic/usr.asm). D-DEFTYPETOK's own gate run already reports all
> three as **SAME** (crunch) and **SUPPORTED** (execution), so the "3 work
> anyway" bucket is empty and at least three words have moved from the 38 into
> the 124. **Re-run `make kwsweep` before quoting the tally above** rather than
> doing that arithmetic here — the counts stand as taken; only their status
> changed.

> 🏁 **THE SILENT-GAP CLASS IS EMPTY (2026-07-27).** All eight below have
> landed and are gated: `EQV`/`IMP` (`ef098e9`), `TAB(`/`SPC(`/`CSRLIN`/`POS`
> (`99c0f6d`), `FRE`/`BIN$` (`2facfc0`). A re-run of `make kwsweep` confirms it
> independently of those slices' own gates — the summary line no longer has a
> SILENT category, and `bin` and `fre` both read `SUPPORTED match`. The table
> below is kept as the record of what the gap WAS.
>
> ⚠️ The re-run's one `DIVERGENT` is **`csrlin`, and it is a probe artifact**.
> That row (`PRINT:PRINT:PRINT"[";CSRLIN;"]"`) has no `CLS`, so it reports where
> the boot banner and the batch's own scrolling left the cursor: it read ref 4
> vs zb 3 in one batch and **ref 9 vs zb 7 in another** — the reference
> disagreeing with itself is the proof. With `CLS:` both machines answer 2.
> It cannot be pinned in place: this probe's readout anchors on the typed echo,
> which `CLS` erases, so the row would classify UNREADABLE instead (tried).
> `CSRLIN` is correct and gated at a pinned `WIDTH 40` by `cursor-acceptance`
> 67/67. **Read that row as evidence CSRLIN is PRESENT, never about its value.**

### SILENT-GAP — zerobas answers, and the answer is wrong (was 8, now 0)

The worst class: no error, no diagnostic, just a wrong number. Every one of these
is a live `TIME`-shaped landmine in a user program today.

| word | reference | zerobas | absent-parse |
|---|---|---|---|
| `TAB(` | `[    X]` | `[ 0 X]` | array element |
| `SPC(` | `[     X]` | `[ 0 X]` | array element |
| `CSRLIN` | `[ 4 ]` | `[ 0 ]` | numeric var |
| `POS` | `[ 5 ]` | `[ 0 ]` | array element |
| `FRE` | `[-1 ]` | `[ 0 ]` | array element |
| `EQV` | `[-7 ]` | `[ 5  0  3 ]` | var → three PRINT items |
| `IMP` | `[-5 ]` | `[ 5  0  3 ]` | var → three PRINT items |
| `BIN$` | `[101]` | `[]` | string array element |

`EQV`/`IMP` deserve a note: `PRINT 5 EQV 3` prints **three separate values**
because the operator is read as a variable between two literals. Nothing in the
language flags it.

`TIME` was the ninth entry in this table on the first run and is now **SUPPORTED**
(token `$CB`, `timetick` confirms the clock advances across a delay loop) — see
[`spec-basic-time.md`](spec-basic-time.md).

### MISSING — zerobas raises a syntax error (6)

Honest failures. Visible, diagnosable, not silent: `LOCATE`, `SWAP`, `TRON`,
`TROFF`, `MOTOR`, `DEF FN`/`FN`.

### The reference token bytes — measured, for all 14 (2026-07-27)

Every absent word's token is now **oracle-measured black-box** rather than read
off a table, harvested from the Layer-1 CRUNCH diff (`--layer crunch --only …`)
on the same run that produced the pin above. Layer 1 stores `1 <body>` and dumps
the reference's own tokenised line, so these bytes are what the VG-8020 *emitted*,
not what a book says it should have. They agree with the MSX2 Technical Handbook
Table 2.20 assignments the existing `kwtable.inc` locks cite; where a future
`kwtable.inc` entry lands, **this table is the lock**.

| word | reference token | shape | zerobas emits today |
|---|---|---|---|
| `LOCATE` | `$D8` | statement | `4C 4F 43 41 54 45` (verbatim) |
| `CSRLIN` | `$E8` | single-byte function | verbatim |
| `POS` | `$FF $91` | `$FF`-prefixed function | verbatim |
| `TAB(` | `$DB` | PRINT item — **token swallows the `(`** | verbatim |
| `SPC(` | `$DF` | PRINT item — **token swallows the `(`** | verbatim |
| `SWAP` | `$A4` | statement | verbatim |
| `FRE` | `$FF $8F` | `$FF`-prefixed function | verbatim |
| `TRON` | `$A2` | statement | `54 52 95` = `"TR"` + **`ON`** |
| `TROFF` | `$A3` | statement | `54 52 EB` = `"TR"` + **`OFF`** |
| `DEF FN` | `$97` `$DE` | `DEF` (have) + `FN` (absent) | `97 20 46 4E` — `DEF` + verbatim `FN` |
| `EQV` | `$F9` | binary operator | verbatim |
| `IMP` | `$FA` | binary operator | verbatim |
| `MOTOR` | `$CE` | statement | `4D 4F D9 52` = `"MO"` + **`TO`** + `"R"` |
| `BIN$` | `$FF $9D` | `$FF`-prefixed function | verbatim |

Note `TAB(`/`SPC(`: the reference emits `91 20 DB 16 29` for `PRINT TAB(5)` — one
token, then the argument, then a bare `)`. The opening paren is **part of the
keyword**, exactly as `kwtable.inc` would have to spell it.

Three rows show the tokeniser's substring behaviour on a word it does not know
(`TRON`→`TR`+`ON`, `TROFF`→`TR`+`OFF`, `MOTOR`→`MO`+`TO`+`R`). That is
**correct** — `match_kw` is attempted at every position, so this is what the
reference itself does for any non-keyword containing a keyword. It round-trips
through `LIST` unchanged. It is recorded because it looks alarming in a hex dump
and is not a defect.

### NO-ORACLE — ✅ CLOSED 2026-09-03 (D-KWORACLE), and it was blocking four findings

This section used to read: *"the probe now routes them to `National_CF-3300`,
which does not yet yield a readable SCREEN-0 capture under `omsx_repl` (a trivial
`PRINT 1+1` returns VRAM pattern garbage — likely still in the boot video mode
when the capture fires). Rather than answer from the wrong machine, the probe
reports `NO-ORACLE`. **Blocks no finding.**"*

🔴 **THE DIAGNOSIS IN THAT PARENTHESIS WAS RIGHT, AND THE CONCLUSION AFTER IT WAS
WRONG.** The CF-3300 really was still in its boot video mode — `run_cases`
defaults to `boot=8.0`, which is right for the VG-8020 and ~6 s short for the
CF-3300, and that machine also needs a `SCREEN 0` before the scrape can read
anything. Both fixes were **already in this tree**, in
`basic_probe_deffn.SIDES` (`boot=14.0`, `reset=("", "SCREEN 0", "NEW")`); the two
tables simply never met. `ref_capture` now carries per-machine boot and reset.

And it blocked four findings:

| word | was | now |
|---|---|---|
| `MKI$` | NO-ORACLE | **SUPPORTED, match** — the family CONTROL |
| `MKS$` | NO-ORACLE | **SILENT-GAP** — ref `4`, zerobas `0` |
| `MKD$` | NO-ORACLE | **SILENT-GAP** — ref `8`, zerobas `0` |
| `CVS` | NO-ORACLE | **MISSING** — ref `1`, zerobas `Type mismatch` |
| `CVD` | NO-ORACLE | **MISSING** — ref `1`, zerobas `Type mismatch` |

🎯 **THE FAMILY CONTROL IS WHAT MADE IT VISIBLE, AND ONLY IN HINDSIGHT.** `MKI$`
is in the row set precisely because it ships on **both** sides — so a
`NO-ORACLE` verdict on *it* is impossible unless the apparatus is broken. That
was sitting in the output the whole time. The summary line read
`NO-ORACLE=5  SUPPORTED=30  DIVERGENT=1`, with **no `MISSING` and no
`SILENT-GAP` count at all**, which is indistinguishable at a glance from a clean
bill of health.

⚠️ **`MKS$`/`MKD$` are `SILENT-GAP`, this probe's own "worst kind".** They are
absent from `basic/kwtable.inc` entirely, so `MKS$(1.5)` is not tokenised as a
keyword — it parses as the string **array** `MKS$(1)` and answers `0`. A silent
wrong answer, not a refusal.

The summary is now `SILENT-GAP=2  MISSING=2  DIVERGENT=1  SUPPORTED=31`.
Exactly six rows changed verdict between the blind run and this one — the five
above plus `lfiles` (crunch-only, `ABSENT` → `present`) — and every one of them
is a row routed to the second oracle, which is the bound a fix like this needs.

### Not executed — 18 words, crunch-only

Real coverage holes **in this probe**, listed in its output with reasons rather
than silently dropped: destructive (`DSKO$`, `IPL`), interactive (`AUTO`,
`INPUT$(n)`), non-terminating (`WAIT`), printer-bound with the known unplugged-
`LSTOUT` hang hazard (`LPRINT`, `LLIST`, `LPOS`, `LFILES`), disk-fixture-dependent
(`COPY`, `SET`, `ATTR$`, `DSKI$`, `LOC`), or already covered elsewhere
(`INTERVAL` → the T5 slice probe).

🔴 **THE PRINTER REASON IS REFUTED, AND IT COVERED FOUR OF THOSE WORDS**
(2026-08-06, D-EDITVERB — [`editverb-msx1-characterization.md`](editverb-msx1-characterization.md)
§1.1). openMSX's `printerport` takes a `logger` pluggable whose status is READY
unconditionally, so an `LSTOUT` poll cannot block, and the log file is a better
readout than any screen scrape. `LLIST` is now measured on **both** references
that way and implemented (`make editverb-acceptance`). `LPRINT`, `LPOS` and
`LFILES` remain unexecuted — but for the ordinary reason that they have no
`kwtable.inc` entry, NOT because they cannot be put to a reference.

🔴 **THAT LAST SENTENCE IS TRUE OF TWO OF THE THREE, NOT ALL THREE** (narrowed
2026-08-06 while scouting D-LPTVERB). `LPRINT` and `LPOS` are in the printer
group above and the refutation covers them wholly — both are now measured on
**both** references, 16 and 10 rows, in
[`lptverb-msx1-characterization.md`](lptverb-msx1-characterization.md). `LFILES`
is **not in that group**: this probe carries it among the Disk-BASIC words with
**two** reasons, `NEEDS-DISK` *and* printer-bound, and only the printer half
fell. The VG-8020 has no disk ROM, so asking it `LFILES` measures the absence of
a disk interface rather than of a language feature — the identical trap this
document already records for the `MKS$`/`MKD$`/`CVS`/`CVD` family two sections
up. ⇒ `LFILES` is measurable on the **CF-3300 only**, which is a narrower claim
than "it can be put to a reference" and has to stay narrower.

`AUTO` is
refuted too: Ctrl-STOP is a key-matrix combination (row 6 bit 1 + row 7 bit 4),
which `keymatrixdown` delivers and `BREAKX` sees. The remaining crunch-only
count is **18 minus the two now executed**; the three printer words are filed as
an open item in `TODO.md`.

**`INPUT$` is the one to watch here:** it crunches *identically* to the reference
(because `INPUT` is a keyword and `$` follows), so Layer 1 says "present" while
support is untested — the exact `INTERVAL` shape. It is tracked as open in
`TODO.md`, but this sweep has **not** confirmed its behaviour either way.

## What the sweep does not cover

The reserved-word surface only. Statement **option surfaces** are out of scope:
`SCREEN 3`, `KEY LIST`, `ON ERROR` variants, argument-form coverage of words that
*are* present. A word can be present and still be wrong in its third argument.

## Apparatus notes (the probe's own scars)

Four defects were caught by the probe's self-checks before any of them reached a
conclusion — recorded because each is a reusable trap:

1. **The probe destroyed its own anchor.** `LOCATE 10,0:PRINT"[X]"` moved the
   cursor onto the echoed command and overprinted it, so `screen_tail` could not
   find the echo → `?noecho`. Fixed to `LOCATE 10` (column only). A startup guard
   (`MAX_DIRECT_ECHO`) now rejects any direct-mode line too wide to echo on one
   row, so this cannot recur silently.
2. **Direct mode tested the wrong thing.** The reference answers `Illegal direct`
   to a direct-mode `DEF FN` — so the original row measured the direct-mode
   restriction, not the feature. Moved to stored mode.
3. **The control group failed, correctly.** `MKI$` — implemented and working in
   zerobas — came back as the *reference* erroring. That was the diskless-machine
   asymmetry above, caught only because known-good words are measured alongside
   suspected-missing ones.
4. **Verdict ordering mattered.** An early revision checked "did zerobas tokenise
   it?" *before* comparing outputs, and duly labelled `DEFSNG`/`DEFDBL`/`DEFSTR`
   as SILENT-GAP while printing two identical answers. Agreement now wins first.

The probe also fingerprints `build/*.rom` before and after each run and **aborts
the report** if they changed mid-flight — the machine XML points straight at the
project tree, so a concurrent `make` in another session silently changes the
measurement target.
