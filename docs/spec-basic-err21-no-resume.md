<!-- Copyright (c) 2026 Joost Yervante Damad ; SPDX-License-Identifier: 0BSD -->
# D-ERR21 — `No RESUME`: raising ERR 21, measured

**Status: ✅ LANDED 2026-07-31 — signed off, built, gated, six falsification
builds.** §4.2 and §5.1 carry the as-built numbers; the spec below is unchanged
from sign-off except where marked AS-BUILT or **AS-RUN**. Closes
[`TODO.md`](../TODO.md) ~line 2549 and defect (1) of
[`docs/spec-basic-oneflg-reset-scope.md`](spec-basic-oneflg-reset-scope.md) §7.
Builds on [`docs/spec-basic-cont-record.md`](spec-basic-cont-record.md) §4, which
designed the placement — **and which §2.1 below REFUTES on two counts.**

---

## 1. The defect

A program that runs off the **end of the program text** while still inside an
`ON ERROR` handler with no intervening `RESUME` must abort with
`No RESUME in <line>`. zerobas ends the run silently. `err_msgtab` has a *slot*
for code 21, but it points at `err_unprintable` — there is no message string and
no raiser, so `ERROR 21` also prints the wrong text.

---

## 2. The measurement — VG-8020, boot-per-case, 2026-07-31

Two rounds through [`probes/lib/omsx_repl.py`](../probes/lib/omsx_repl.py),
reference = Philips VG-8020, subject = `C-BIOS_MSX1_EU_REPACK_DISK` at `5c300c7`.
Handler is line 100 throughout; `E` is `20 B=SQR(-1)` with `10 ON ERROR GOTO 100`.

| # | shape | reference | zerobas @ `5c300c7` | |
|---|---|---|---|---|
| a1 | handler at 100, **then a line 110**, falls off | `No RESUME in 110` · ERR/ERL `21,110` | *silent* · `5,20` | ❌ |
| a2 | handler `100 GOTO 200`, 200 falls off | `No RESUME in 200` · `21,200` | *silent* · `5,20` | ❌ |
| a3 | handler `100 GOSUB 200`, 200 falls off | `No RESUME in 200` · `21,200` | *silent* · `5,20` | ❌ |
| a4 | falls off, then `CONT` | *silent `Ok`*, **nothing reprinted** | *(no abort)* | — |
| a5 | falls off, then `CONT`, `CONT` | silent, silent | *(no abort)* | — |
| a6 | falls off, then direct `RESUME` | `No RESUME in 110`, then `RESUME without error` | *silent*, then `resume without error` | ❌ text |
| a7 | `ERROR 21` (direct) | `No RESUME` | `unprintable error` | ❌ |
| a8 | `10 ERROR 21` + `RUN` | `No RESUME in 10` · `21,10` | `unprintable error in 10` · `21,10` | ❌ |
| **c1** | **suspended in handler → typed `PRINT 1` → `CONT`** | ` 1` then **`R< 5 >`** | ` 1` then **`resume without error in 110`** | ❌ |
| c2 | control: the same **without** the typed line | `R< 5 >` | `R< 5 >` | ✅ |
| c3 | control: no handler armed at all, falls off | silent · `0,0` | silent · `0,0` | ✅ |
| c4 | control: handler `END`s | silent · `5,20` | silent · `5,20` | ✅ |
| c5 | control: `100 RESUME NEXT` **paid**, then falls off | silent · `0,20` | silent · `0,20` | ✅ |

### 2.1 🔴 Two things the filed characterization had WRONG

Both were carried forward as settled, and both are refuted by measurement.

1. **The line named is the LAST EXECUTED LINE, not the handler's.** The filed
   reading — *"ERR/ERL read `21 , 100`… the HANDLER's line"* — was taken on
   `oneflg_falloff`'s program, whose **handler line IS also the last line**, so
   the two candidates were never discriminated. Rows a1/a2/a3 separate them and
   the answer is unanimous: **110, 200, 200.** [[spec-basic-cont-record]] §4's
   plan of `CURLINE := ONELIN` would have produced `in 100` on all three.
   *(A case that AGREES can agree for the wrong reason —
   [[kwsweep-msx1-denominator]].)*

2. **The raiser does NOT get the right CONT resume point from `ra_abort`.**
   §4 of the CONT-record spec says the ERR 21 abort "gets the measured abort
   resume point **for free**" because `ra_abort` records `SAVTXT`. Row a4 says
   otherwise: after the abort, `CONT` reprints **nothing**. On the a4 program
   (`110 PRINT"R<";7;">":PRINT"R<";8;">"`) a `SAVTXT` record would resume at the
   last statement and **reprint `R< 8 >`**; a fresh-line record would reprint
   `R< 7 >` too. Neither happens — the resume point is the **fall-off position**,
   i.e. exactly the `HL = 0 / CONTLINE = the $0000 marker` record the silent arm
   already makes. So the raiser must make that record **itself**, before it moves
   `CURLINE`, and must **not** route through `ra_abort`.

### 2.2 🔴 And row c1 is a THIRD, previously unmeasured live defect

`ONEFLG` must **survive an ordinary typed line** while a run is suspended inside
a handler. D-ONEFLG's site C clears it there: a typed line ends by falling
through `dir_line`'s own `$0000` link into the very exit site C sits on
([`basic/program.asm:414`](../basic/program.asm:414) documents that path). So
today, `PRINT 1` at a `Break in 100` prompt silently kills the handler context
and the following `CONT` reports `resume without error in 110` instead of
resuming. **No existing row covers it** — `oneflg_keep` re-enters with a typed
`GOTO` (which never falls through `dir_line`) and `oneflg_suspend_resume` types
nothing at all. c1/c2 are that pair, and c1 is red on zerobas **today**.

Removing site C — which this slice does anyway — is the fix. It is safe because
the only path that reaches the exit with `ONEFLG` **set** now raises ERR 21, and
the ERR 21 abort funnels through `fre_abort_low`, i.e. **site A**, which clears
`ONEFLG` unconditionally (row a6 confirms: the direct `RESUME` after the abort
reports "without error" on both machines).

### 2.3 The rule

> **At the `$0000`-link exit of the run loop, in RUN mode, with `ONEFLG` set:
> raise ERR 21 `No RESUME`, naming the LAST STORED LINE, after recording the
> ordinary fall-off CONT resume point.**
> In DIRECT mode the same exit raises nothing and changes nothing (c1).
> With `ONEFLG` clear it is the existing silent stop (c3/c4/c5).

---

## 3. The fix

### 3.1 `basic/program.asm` — the `rp_lp` prefix (page 1)

D-ONEFLG **site C is deleted** and replaced by the test that decides the raise.
`A` is `d|e`, i.e. already 0 on this arm, which is what site C exploited; the
test clobbers it, and the store it replaces was a no-op on the surviving arm
(`ONEFLG` is 0 exactly when the branch is not taken).

```asm
                jr      nz,rp_notend
                ld      a,(ONEFLG)          ; D-ERR21 prefix, ABOVE everything
                or      a                   ; D-CONTR adds here
                jp      nz,e21_no_resume    ; still owing a RESUME -> ERR 21
                ld      hl,0                ; (D-ONEFLG site C deleted: on THIS
                jp      cont_record         ;  arm ONEFLG is already 0)
```

**+7 −3 = +4 B page 1**, before any `jr`-reach widening (§5).

### 3.2 `basic/arrays.asm` — the raiser (low region)

Home: beside `fre_abort_low`, the low-region abort tail it ends in. The low
region is the right side of the co-mapped pair — page 1 is the tighter wall
(30 B vs 80 B) and this body is a pressure-placeable leaf with no page-1
contract ([`docs/rom-region-structure-review.md`](rom-region-structure-review.md) §5).

```asm
e21_no_resume:
                ld      hl,0                ; §2.1(2): the FALL-OFF resume point,
                call    cont_record         ; recorded HERE, while CURLINE is still
                                            ; the $0000 marker -- NOT ra_abort's SAVTXT
                ld      a,(DIRECTF)
                or      a
                ret     nz                  ; §2.2 c1: a TYPED line falling through
                                            ; dir_line's own $0000 link is NOT a raise;
                                            ; exit the loop exactly as the silent arm does
                ; CURLINE := the LAST STORED LINE (§2.1(1): a1/a2/a3, NOT ONELIN)
                ld      hl,TXTBASE
                ld      b,h                 ; BC trails HL by one line
                ld      c,l
e21_walk:       ld      e,(hl)
                inc     hl
                ld      d,(hl)
                dec     hl
                ld      a,d
                or      e
                jr      z,e21_last          ; HL is the terminator; BC is the last line
                ld      b,h
                ld      c,l
                ex      de,hl
                jr      e21_walk
e21_last:       ld      (CURLINE),bc
                ld      a,21
                ld      (ERRCODE),a
                call    record_errline      ; ERL := that line (run mode, DIRECTF==0)
                ld      hl,err_no_resume
                jp      fre_abort_low       ; site A clears ONEFLG; prints " in <line>"
err_no_resume:  db      "no resume",0
```

**~57 B low region** (47 code + 10 string).

**Why not `jp raise_error` (9 B cheaper).** `raise_error` ends in `ra_abort`,
which records `SAVTXT` — refuted by row a4 (§2.1(2)) — and it would overwrite the
correct record made three instructions earlier. The trap decision `raise_error`
adds is inert here anyway: `ONEFLG != 0` is the raise condition, so
`raise_error_hl` would force-abort every time.

**Why the walk terminates.** It follows the same link chain `find_line_bc`
walks and stops at the same `$0000` terminator, which is by construction the
cell `CURLINE` already points at. `BC` is pre-seeded with `TXTBASE`, so even an
empty program (unreachable: `RUN` clears `ONEFLG`) writes a defined value and
does not run away.

### 3.3 `basic/interp.asm` — the table entry (0 B)

`err_msgtab` entry 21 changes from `err_unprintable` to `err_no_resume`. That is
what makes rows a7/a8 (`ERROR 21`) correct as well — a second raiser, free.
Wording is house-style lowercase per D-2 (reference: `No RESUME`), matching
`resume without error`; §4 compares case-folded.

---

## 4. The gate — `e21_*`, in `make error-trap-acceptance`

**Home:** [`probes/basic/basic_probe_error_trap.py`](../probes/basic/basic_probe_error_trap.py).
**Including the CONT rows** — they cannot go in `abort-acceptance` beside the
`cont2_*` family, because that probe's stated invariant is that **not one row may
arm `ON ERROR`** ([its docstring §16](../probes/basic/basic_probe_abort_depth.py):
arming a handler selects the trap branch and silently turns the file into a copy
of a different gate). Every ERR 21 row must arm one.

Two-machine differential, boot-per-case, echo-anchored tail. Message text is
compared **case-folded** (D-2 house style), so `No RESUME in 110` and
`no resume in 110` match and a wording or LINE-NUMBER change does not.

| row | shape | holds down | must |
|---|---|---|---|
| `e21_falloff` | a1 | **the walk** (handler 100 ≠ last line 110) | raise, `in 110`, `21,110` |
| `e21_falloff_goto` | a2 | the walk, via `GOTO` | raise, `in 200`, `21,200` |
| `e21_falloff_gosub` | a3 | the walk, with a live `GOSUB` frame | raise, `in 200`, `21,200` |
| `e21_cont` | a4 | **the fall-off record, not `SAVTXT`** | `CONT` silent, **no `R< 7 >`/`R< 8 >`** |
| `e21_cont_twice` | a5 | the record is never consumed | both `CONT`s silent |
| `e21_error_n` | a7 | the `err_msgtab` entry | `no resume`, not `unprintable` |
| `e21_error_n_prog` | a8 | ditto, run mode | `no resume in 10`, `21,10` |
| `e21_typed` | **c1** | **the `DIRECTF` gate AND the site-C removal** | no raise; `CONT` reaches `R< 5 >` |
| `e21_ctl_typed` | c2 | c1's **GREEN CONTROL** | `R< 5 >` |
| `e21_ctl_nohandler` | c3 | must NOT raise | silent, `0,0` |
| `e21_ctl_end` | c4 | must NOT raise | silent, `5,20` |
| `e21_ctl_resume` | c5 | must NOT raise — the `RESUME` was **paid** | silent, `0,20` |

Plus **one upgrade**: `oneflg_falloff` becomes a full two-machine **text**
differential. It was deliberately zb-only precisely because the reference
printed `No RESUME in 100` first and zerobas printed nothing
([`spec-basic-oneflg-reset-scope.md`](spec-basic-oneflg-reset-scope.md) §5/§8.3);
that reason expires here.

**Denominator.** 12 new rows + 1 upgraded, all asserted, none exploratory. The
probe prints its own PASS/FAIL count per battery; the spec's §6 records the
as-run totals for every gate.

### 4.1 Falsification — by DELETING the code under test, each paired

Six builds, each `rm -rf build && make repack-machine && <probe>` **chained with
`&&`** (a build that fails to assemble while the probe runs anyway reads as a
behavioural finding — D-ONEFLG §5.1, D-CONTR §3.5).

| # | deleted / reverted | predicted RED | predicted GREEN (the pairing) |
|---|---|---|---|
| F1 | the whole §3.1 prefix (silent exit restored) | `e21_falloff*`, `e21_cont*`, `oneflg_falloff` | all `e21_ctl_*`, `e21_error_n*` |
| F2 | **the `DIRECTF` gate only** (`ret nz`) | `e21_typed` | `e21_ctl_typed`, `e21_falloff*` |
| F3 | the walk → `CURLINE := ONELIN` (**the filed §4 design**) | `e21_falloff` (`in 100`), `_goto`, `_gosub` | every control |
| F4 | the §3.2 record → route via `jp raise_error` (`SAVTXT`) | `e21_cont` **only** | `e21_falloff*`, `e21_cont_twice`\* |
| F5 | `err_msgtab[21]` back to `err_unprintable` | `e21_error_n*`, `e21_falloff*` | the controls |
| F6 | **control build**: fix in place **+ site C restored** | `e21_typed` | `e21_ctl_typed`, everything else |

\* **F4 is the depth row.** `e21_cont_twice` may well stay GREEN under F4 (the
second `CONT` re-runs the last statement, falls off again, and by then `ONEFLG`
is 0 so it stops silently) — which is exactly [[cont-record-every-stop]]'s F4
lesson that *a re-record ABSORBS the fault*. If a shallower battery had only
`e21_cont_twice`, F4 would score the wrong record as fine. `e21_cont`'s
bracket-delimited `R< 7 >`/`R< 8 >` markers are what make it visible.

**F2 and F6 both turn `e21_typed` red, for OPPOSITE reasons** — F2 raises a
spurious `no resume`, F6 reports `resume without error in 110`. The probe prints
the observed tail on failure, so the two are distinguishable rather than merely
both-red.

### 4.2 Falsification — AS-RUN, seven builds, and THREE of the predictions above were wrong

Each build `rm -rf build && make repack-machine && <probe> --only e21`, chained
with `&&`; sources restored from a pristine copy between runs. **24 rows (12 × 2
machines) is the denominator; the "red" column is the zerobas side.**

| # | build | rows RED | vs predicted |
|---|---|---|---|
| F1 | prefix deleted | `e21_falloff{,_goto,_gosub}`, `e21_cont`, `e21_cont_twice` | ✅ as predicted; all 7 controls + both `ERROR n` rows green |
| F2 | `DIRECTF` gate deleted | `e21_typed` **only** | ✅ row, ❌ **reason** — see below |
| F3 | walk → `CURLINE := ONELIN` | the same 5 raise rows, **all reading `in 100` / `21 , 100`** | ✅ as predicted |
| F4 | record → `jp raise_error` (`SAVTXT`) | `e21_cont` **and** `e21_cont_twice` | ✅ row, ❌ **`_twice` was NOT absorbed** |
| F5 | `err_msgtab[21]` → hole | `e21_error_n`, `e21_error_n_prog` **only** | ❌ the raise rows stayed GREEN |
| F6 | site C restored after the test | **NOTHING — the falsification was BROKEN** | ❌ |
| F6b | site C's effect restored on the direct arm | `e21_typed` only | ✅ |

**🔴 F3 is the one that matters most.** `CURLINE := ONELIN` — the design
[`spec-basic-cont-record.md`](spec-basic-cont-record.md) §4 filed as settled —
produces `no resume in 100` and `ERR/ERL = 21 , 100` on **every** raise row.
Those are **exactly the values the 2026-07-29 characterization recorded and
carried forward as correct.** The wrong implementation reproduces the filed
measurement perfectly. Only a program whose handler line is *not* its last line
can tell them apart. *(A case that AGREES can agree for the WRONG REASON —
[[kwsweep-msx1-denominator]].)*

**🔴 F6 CAME BACK GREEN AND THAT WAS THE FALSIFICATION'S FAULT, NOT A FINDING.**
The patch restored `ld (ONEFLG),a` *after* the new `ONEFLG` test — where `A` is
0 by construction, so it is a genuine no-op. The original site C sat *before* the
test, and what mattered about it was that it cleared a **set** flag on the arm a
typed line takes. F6b reproduces exactly that on the raiser's direct-mode arm and
turns `e21_typed` red as designed. **A green falsification is a claim about the
patch first and about the code second** — the pairing rule
([[apparatus-is-part-of-the-measurement]]) says a red row reads as success, and
this is its mirror: a green row reads as "the code is unnecessary" when it may
just mean the knife missed.

**🔴 F2 and F6b do NOT differ in the way §4.1 predicted, and the row was
strengthened because of it.** Both show `resume without error in 110` at the
`CONT` anchor — because the spurious ERR 21 that F2 raises aborts through
`fre_abort_low`, i.e. site A, which clears `ONEFLG`, which is precisely what F6b
does directly. The tail alone cannot separate them. `e21_typed`/`e21_ctl_typed`
therefore gained a **whole-screen `absent="no resume"` check**, and the two now
read `seen=True` (F2) vs `seen=False` (F6b).

**🔴 F4 was caught by the COUNTS, not by the tail.** Both F4 rows' tails were
**byte-identical to the want** — the re-printed `R< 8 >` lands after the `CONT`,
outside the `RUN`-anchored tail. Only the whole-screen occurrence counts see it.
And `e21_cont_twice` went red too rather than being absorbed: its line 110 has a
single statement, so `SAVTXT` points at the marker itself. The absorb is still
visible in the numbers — `R< 7 >` is 2, not 3, so the *second* `CONT` printed
nothing, `ONEFLG` having been cleared by then.

**F5 falsifies less than §4.1 claimed, and correctly so.** The raiser loads
`err_no_resume` directly rather than through the table, so only the two `ERROR n`
rows depend on the `err_msgtab` entry. That makes F5 cleanly discriminating
instead of redundant.

---

## 5. Space

Clean `rm -rf build && make basic-reloc` at `5c300c7`: **page-0 low region 80 B
free, page 1 30 B free**; dead-code gate 0/0 both builds.

| | estimate |
|---|---|
| §3.1 prefix (page 1) | **+4 B** (+7 test, −3 site C) |
| §3.2 raiser + string (low) | **+57 B** |
| §3.3 table entry | 0 B |

⚠️ **A `jr` REACH IS PART OF THE COST.** D-CONTR added 5 B at this exact site and
pushed `rp_goto`'s backward `jr rp_lp` past −128, costing one unbudgeted byte
(it is a `jp` today). 4 more bytes go in above it; if another span breaks, the
widening is part of the measured cost, not an overrun.

### 5.1 AS-BUILT — the estimate was exact, and no `jr` broke

Clean `rm -rf build && make basic-reloc`: **low region 80 → 23 B free (−57),
page 1 30 → 26 B free (−4)**. Both estimates hit to the byte, and unlike D-CONTR
no `jr` span broke — `rp_goto`'s backward branch is already a `jp` (that slice
paid for it), and the 4 B added here did not push anything else past −128.
No carve, no promotion, no overrun; the §5 relocation policy was not needed.

**⚠️ `build/sub.rom` DOES change, and legitimately.** No `sub/` source was
touched, but the 57 B added to the low region shifts `vars_reset`
(`$3D6B → $3DA4`), which is a **resident-ABI address the sub-ROM links against**.
`sub/basic-resident-abi.inc` regenerates and `check_resident_abi.py` /
`check_tenant_closure.py` both pass. The "`sub.rom` must stay
`01ab5dc2…`" pin holds only for a change that touches **no** ROM source.

**Overrun policy (sign-off Q2).** Low is the harder wall historically but page 1
is the tighter one today, and the two are co-mapped so a body can move between
them. If low overruns, move the §3.2 body to page 1 and re-measure; if page 1
overruns, the §3.1 prefix is the only page-1 content and it cannot shrink — then
promote a pressure-placed page-1 leaf per the R1 playbook. **Do not shave §3.2
into `jp raise_error` + a `SAVTXT` hack to buy 9 B** (§3.2's "why not").

---

## 6. Regression surface — AS-RUN 2026-07-31, all green

`make error-trap-acceptance` (home) — **126 rows, ALL PASS. Denominator: 101
before this slice, +24 new `e21_*` rows, +1 from `oneflg_falloff` going from one
zb-only row to a two-machine differential.** Then:

`make unit-test` (54/54) ·
`make abort-acceptance` (49/49 — the `cont2_*` family shares `cont_record`) ·
`make stop-trap-acceptance` · `make diskbasic-acceptance` (34/34) ·
`make bdos-acceptance` (12/12) · `make fat-error-acceptance` (7/7) ·
`make linemax-acceptance` (60/60) · `make arrdim-acceptance` (73/73) ·
`make clearpool-acceptance` (52/52) · `make array-acceptance` (149/151 — the two
standing rows confirmed **BY NAME**: `ifc.instr.zero` and `ifc.instr.neg`, both
capitalisation-only) · `make chancost-characterize` (39 cases, 1 filed
divergence) · clean `make basic-reloc` (**HARD dead-code gate: main 0 dead /
sub 0 dead +1 allowlisted** — `e21_no_resume` is reached only by a `jp` from
page 1, so a mistake there would show up as a dead span rather than silently).

**As-run:** unit 54/54 · error-trap 126/126 · abort 49/49 · stop-trap 16/16 ·
diskbasic 34/34 · bdos 12/12 · fat-error 7/7 · linemax 60/60 · arrdim 73/73 ·
clearpool 52/52 · array 149/151 (the two standing rows above) · chancost 39/1.

See §5.1 on why `build/sub.rom` legitimately changes despite no `sub/` edit.

---

## 7. Docs this slice must update

* [`docs/spec-basic-oneflg-reset-scope.md`](spec-basic-oneflg-reset-scope.md) —
  site C removed (§4), its gate row re-attributed (§5), §7.1 closed, and §2's
  c3b row gains the ERR 21 text.
* [`docs/spec-basic-cont-record.md`](spec-basic-cont-record.md) §4 — **marked
  REFUTED on both counts** (§2.1 here), not silently deleted.
* [`docs/spec-basic-error-handling.md`](spec-basic-error-handling.md) §203 —
  code 21 moves from "S2 (RESUME machinery)" to landed.
* [`docs/spec-basic-error-handling-s2b-packet.md`](spec-basic-error-handling-s2b-packet.md)
  §96 — code 21 is no longer a hole.
* [`TODO.md`](../TODO.md) ~2549 — closed, with §2.1/§2.2's three corrections.

---

## 8. Newly filed, NOT fixed here (one TODO item per session)

1. **`probes/lib/omsx_repl.py` streams audio on every boot.** The
   `sound_driver null` fix from [[probe-audio-churn-sound-driver-null]] landed in
   [`probes/disk/omsx_session.py:133`](../probes/disk/omsx_session.py:133) only;
   the REPL driver — which every BASIC acceptance gate uses — still passes only
   `set renderer none`. Same defect, different layer. *(Ask at WHICH LAYER a
   lesson already applies — [[rdblk-anchor-flake-host-clock]].)*
2. **`fre_abort_low`'s header comment is stale**
   ([`basic/arrays.asm:111`](../basic/arrays.asm:111)): "the loop's own normal
   exit is a `ret` at that same depth (rp_lp's `ret z` on the `$0000` link)" —
   D-CONTR replaced that `ret z` with `jp cont_record`. Depth-identical, so the
   argument still holds; the citation does not.

---

## 9. Sign-off — ANSWERED 2026-07-31

All four answered as recommended.

1. **The walk (23 B) vs a `PREVLINE` sysvar** (11 B ROM of which 4 in the hot
   fall-through arm, + 2 B RAM). Spec picks the **walk**: no new sysvar, no
   per-line cost, nothing in the tighter page-1 wall, and it terminates on the
   same invariant `find_line_bc` already relies on. → **the WALK.**
2. **Overrun policy** — §5. → **move the body between the co-mapped pages;
   never shave into the `SAVTXT` hack.**
3. **`e21_typed` (§2.2 c1) is a THIRD defect** found by asking where the raiser
   must be gated. → **fix it here**, by deleting site C: one coherent change,
   3 B reclaimed, and the F2/F6 falsification pair.
4. **Wording** → **`no resume`** (house-style lowercase, D-2); the gate compares
   case-folded, so only capitalisation is exempt from the differential.

---

## 10. Clean-room

Every fact in §2 is black-box observed behaviour of a Philips VG-8020 under the
published-sysvar KEYBUF driver — an allowed source
([`docs/allowed-sources.md`](allowed-sources.md)), the same oracle-capture basis
as the rest of the error-handling arc. No reference ROM was disassembled and no
reference sysvar layout was consulted: `ONEFLG`, `CURLINE`, `CONTLINE` and
`SAVTXT` are zerobas's own cells at its own addresses, and the §3 structure —
a prefix at zerobas's own `rp_lp`, a link walk, `fre_abort_low` — is own code
chosen to reproduce the measured rows, not a mirror of the reference's internal
structure. §2.3 is a description of what the machine does, derived from the 13
cases in §2 and from the four that discriminate between candidate rules
(a1, a2, a4, c1). Message wording is house style (D-2), deliberately NOT the
reference's capitalisation.
