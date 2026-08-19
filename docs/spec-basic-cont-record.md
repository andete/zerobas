<!-- Copyright (c) 2026 Joost Yervante Damad -->
<!-- SPDX-License-Identifier: 0BSD -->

# D-CONTR — the run loop records a `CONT` resume point at **every** run stop

**Status: ✅ LANDED 2026-07-30. Signed off before implementation (§9); built,
gated 49/49, falsified against six builds.**
Filed defect: [`TODO.md`](../TODO.md) *"`CONT` after a plain `END` must continue"*
(~line 2567). The filed title understates it; the entry's own carried-forward
characterization already says so, and §2 below widens it further **by
measurement**, not by reasoning.

Sequenced AFTER [`docs/spec-basic-cont-depth.md`](spec-basic-cont-depth.md)
(D-CONTD, `CONT` re-entry depth) exactly as that spec's §7 required: D-CONTD's
`END` exit was *clean by luck*, and this slice makes both run-loop exits
reachable by `CONT` in new ways.

---

## 1. The rule to build

> **On every run stop, in RUN MODE, the interpreter records where it stopped:
> `CONTLINE := CURLINE`, `CONTPTR := the stop's own resume position`,
> `CONTVALID := 1`. In DIRECT MODE it records nothing and changes nothing.
> `CONT` NEVER consumes the resume point; only `RUN`, `NEW` and a program edit
> invalidate it.**

zerobas today records at exactly one stop — `do_break` (`STOP` / Ctrl-STOP) —
and *consumes* the point on use. Everything else answers `can't continue`.

The header comment on `ex_stop` (`basic/program.asm:721-644`) asserts the
opposite **as fact**:

> *"(END does not: it ends the run with no resume point, so CONT after END is
> "Can't CONTINUE".)"*

That claim was never measured and is **wrong**. It is doc debt: it is exactly
what a reader consults before touching this code. §6 replaces it.

---

## 2. What was MEASURED — VG-8020 differential, boot-per-case, 2026-07-30

Three rounds, 34 boots, `omsx_repl.run_case` boot-per-case, echo-anchored tail
readout, bracket-delimited values (the same apparatus as
`basic_probe_abort_depth.py`). Reference = `Philips_VG_8020`, subject =
`C-BIOS_MSX1_EU_REPACK_DISK`. Raw logs are throwaway; every row below is
promoted into the standing gate in §5, so nothing here has to be re-derived.

### 2.1 Which stops record — and where the resume point points

| case | program / keys | reference | zerobas | verdict |
|---|---|---|---|---|
| `k_ctl_stop` | `10 STOP` `20 PRINT[2]` `RUN` `CONT` | `[ 2 ]` | `[ 2 ]` | SAME (control) |
| `k_end_next` | `10 A=1` `20 END` `30 PRINT[3]` `RUN` `CONT` | `[ 3 ]` | `can't continue` | **DIFF** |
| `k_end_rest` | `10 END:PRINT[9]` `20 PRINT[2]` `RUN` `CONT` | `[ 9 ]` `[ 2 ]` | `can't continue` | **DIFF** |
| `k_falloff` | `10 A=1` `20 PRINT[2]` `RUN` `CONT` | *(silent `Ok`)* | `can't continue` | **DIFF** |
| `k_twice` | …`RUN` `CONT` `CONT` | *(silent `Ok`)* | `can't continue` | **DIFF** |
| `k_thrice` | …`RUN` `CONT` `CONT` `CONT` | *(silent `Ok`)* | `can't continue` | **DIFF** |
| `k_err` | `10 A=ASC("")` `20 PRINT[2]` `RUN` `CONT` | `Illegal function call in 10` | `can't continue` | **DIFF** |
| `k_err_mid` | `10 PRINT[7]:B=ASC("")` `20 PRINT[2]` `RUN` `CONT` | `Illegal function call in 10` **and no second `[ 7 ]`** | `can't continue` | **DIFF** |
| `k_err_twice` | `k_err` + a second `CONT` | error again | `can't continue` | **DIFF** |
| `k_err22` | `10 RESUME` `20 PRINT[2]` `RUN` `CONT` | `RESUME without error in 10` | `can't continue` | **DIFF** |
| `k_restop` | `10 STOP` `20 STOP` `30 PRINT[3]` `RUN` `CONT` `CONT` | `Break in 20` then `[ 3 ]` | same | SAME |

Read off the table, the resume position is **stop-specific**, and each one is
pinned by a row that would have come out differently under the alternative:

* **`END`** → the token position **immediately after the `END` token**, i.e.
  mid-line. `k_end_rest` is the discriminator: the reference prints `[ 9 ]`
  *and then* `[ 2 ]`. Had `END` recorded "the next line", `[ 9 ]` would be
  missing; had it recorded its own token, nothing would run at all.
* **untrapped abort** → **the failing statement's own start** (`SAVTXT`), not
  the line start. `k_err_mid` is the discriminator: `[ 7 ]` does **not** print
  a second time, so the resume point is not the head of line 10.
  `k_err22` extends this to the *forced* abort arm (ERR 22).
* **fall off the `$0000` link** → the end-of-program position, i.e. a `CONT`
  resumes there, immediately re-detects end-of-program and returns to `Ok`
  **silently**, for ever (`k_falloff` / `k_twice` / `k_thrice`).
* **`STOP` / Ctrl-STOP** → the next statement to run. Unchanged; `k_restop`
  pins that the point *moves* on each new stop.

### 2.2 Direct mode does not INVALIDATE — it does NOTHING

This is the half that was not in the TODO entry, and it is why the fix is not
"add `cont_record` to three more sites and reuse `do_break`'s gate".

| case | reference | zerobas | verdict |
|---|---|---|---|
| `k_typed_keep` | `10 STOP` `20 PRINT[2]` `RUN` `PRINT[8]` `CONT` → `[ 2 ]` | `[ 2 ]` | SAME |
| `k_typed_end` | …`RUN` `END` `CONT` → `[ 2 ]` | `[ 2 ]` | SAME |
| `k_typed_err` | …`RUN` `PRINT ASC("")` `CONT` → `[ 2 ]` | `[ 2 ]` | SAME |
| `k_typed_stop` | …`RUN` `STOP` `CONT` → `[ 2 ]` | **`can't continue`** | **DIFF** |
| `k_norun` | `CONT` on a cold machine | `Can't CONTINUE` | same | SAME |
| `k_new` | `10 STOP` `20 PRINT[2]` `RUN` `NEW` `CONT` | `Can't CONTINUE` | same | SAME |
| `k_end_only` | `END` `CONT` (nothing live) | `Can't CONTINUE` | same | SAME |

🔴 **`do_break`'s existing direct-mode gate is ALSO wrong, and the reason it
looked right is an apparatus lesson.** `do_break` does
`ld a,(DIRECTF) / xor 1 / ld (CONTVALID),a` — *a typed break INVALIDATES*. The
row that justified it ([`docs/spec-basic-direct-ctrl.md`](spec-basic-direct-ctrl.md) §5,
`PRINT 1:STOP:PRINT 2` typed at the prompt → `Break`, then `CONT` →
`Can't CONTINUE`) was measured **with nothing live**, where "invalidate" and
"do nothing" are indistinguishable. `k_typed_stop` puts a live resume point
underneath it and separates them: the reference **keeps** it.

That existing row stays green under the new rule (§5.3), because with
`CONTVALID` already 0 doing nothing leaves it 0. **This is the "a case that
AGREES can agree for the WRONG REASON" lesson, found by adding the missing
denominator to a two-row question.**

### 2.3 What this session did NOT measure

* Ctrl-STOP (a key event, not typeable through this harness) at any of the new
  stops. It shares `do_break` with the `STOP` statement and is gated elsewhere
  (`basic_probe_cont.py` (g), `stop-trap-acceptance`).
* `CONT` after a resume point whose line was *shortened* rather than replaced.
  `store_line` clears `CONTVALID` for any edit, so this is out of reach.

---

## 3. The fix

Everything lands in **page 1** (`basic/interp.asm` and `basic/program.asm` are
both included after `__MEAS_LOW_END`, `basic/main.asm:118`). **The low region is
not touched at all** — the harder wall pays nothing.

### 3.0 One shared routine

New, in `basic/program.asm` beside `do_break`:

```asm
; --- cont_record: record a CONT resume point ---------------------------------
; in: HL = the resume token position, or 0 = "re-enter FRESH at CONTLINE".
;     CURLINE = the line to resume in (its link-field address).
; DIRECT MODE RECORDS NOTHING AND CHANGES NOTHING -- measured (spec §2.2,
; k_typed_stop/k_typed_end/k_typed_err/k_typed_keep). It does NOT invalidate:
; a typed line, a typed STOP, a typed END and a typed error all leave a live
; resume point alone on the reference.
cont_record:
                ld      a,(DIRECTF)
                or      a
                ret     nz
                ld      (CONTPTR),hl
                ld      hl,(CURLINE)
                ld      (CONTLINE),hl
                inc     a                   ; A is still 0 -> 1
                ld      (CONTVALID),a
                ret
```

**19 B.** `do_break`'s existing 17 B of inline body collapses into a 3 B
`call cont_record`, so the extraction itself costs **+5 B** and every further
site is 3–8 B.

### 3.1 `do_break` (`basic/program.asm`) — −14 B

Replace the six-instruction body (`ld (CONTPTR),hl` … `ld (CONTVALID),a`) with
`call cont_record`. Behaviour change: direct mode no longer clears `CONTVALID`
(§2.2, `k_typed_stop`).

### 3.2 `ex_end` (`basic/interp.asm`) — +4 B

```asm
ex_end:
                inc     hl                  ; resume AFTER the END token (k_end_rest)
                call    cont_record
                xor     a
                ld      (ONEFLG),a          ; D-ONEFLG site B -- unchanged
                inc     a
                ld      (ENDFLAG),a
                ret
```

`ex_end` is entered with `HL` on the `END` token (the dispatcher's contract,
`basic/interp.asm:242`), so `inc hl` is the measured resume position. `HL` is
dead afterwards and `A` is reloaded, so `cont_record`'s clobbers are free.

### 3.3 The `$0000`-link exit (`basic/program.asm` `rp_lp`) — +5 B

```asm
                jr      nz,rp_notend
                ld      (ONEFLG),a          ; D-ONEFLG site C -- unchanged (A=0 here)
                ld      hl,0                ; fresh-line re-entry sentinel
                jp      cont_record         ; tail call: ITS `ret` is the loop's exit
```

`CONTPTR = 0` is the "re-enter fresh" sentinel; a real resume pointer is a text
area / `TOKBUF` address and is never `$0000`. `CONTLINE` is `CURLINE`, which at
this exit is the address of the `$0000` end marker itself.

**The tail call is exactly the loop's ordinary exit `ret`,** at the same depth
as the `ret` it replaces — the depth contract D-CUR-D and D-CONTD both rest on.

### 3.4 The abort funnel (`basic/interp.asm` `ra_abort`) — +8 B

```asm
ra_abort:                                    ; the S1/S2a abort body (HL = message)
                push    hl                   ; guard the message
                ld      hl,(SAVTXT)          ; resume = the FAILING STATEMENT (k_err_mid)
                call    cont_record
                pop     hl
                jp      fre_abort_low
```

`SAVTXT` is written by `exec_stmt` at **every** statement entry
(`basic/interp.asm:163`) and is already documented as *"the ONLY clean source
since raise_error fires from arbitrary call depth"*. It is exactly the pointer
`k_err_mid` measured. No new sysvar, no new invariant.

`raise_error_forced`'s `jp fre_abort_low` (ERR 22) becomes `jp ra_abort` — the
same 3 bytes, a different target, so ERR 22 records too. **`k_err22` measured
that it must.**

The `push`/`pop` pair is balanced before the `jp`, so the abort chain's
depth-independence (D-CUR-D) is untouched; `fre_abort_low` resets `SP` from
`SAVSTK` as its own first act regardless.

### 3.5 `ex_cont` (`basic/program.asm`) — −4 B, and a 0-byte rewrite

```asm
                jr      z,ex_cont_no
                xor     a                    ; ← DELETE both: the reference NEVER
                ld      (CONTVALID),a        ;   consumes it (k_thrice, k_err_twice)
                ...
                ld      hl,(CONTPTR)
                ld      (RESUMEPTR),hl
                ld      a,1                  ; ← was: always resume mid-line
                ld      (RESUMEFLAG),a
```

becomes

```asm
                ld      hl,(CONTPTR)
                ld      (RESUMEPTR),hl
                ld      a,h                  ; CONTPTR==0 -> RESUMEFLAG=0 -> rp_lp
                or      l                    ; enters the line FRESH (the $0000-link
                ld      (RESUMEFLAG),a       ; re-entry); otherwise resume mid-line
```

`ld a,h / or l` is the same 2 bytes as `ld a,1`, and `RESUMEFLAG` only needs to
be non-zero — so the sentinel costs **zero bytes**.

### 3.6 Why the second `CONT` cannot loop or derail

Walked, not assumed. After a fall-off, `CONTLINE` = the `$0000` marker's
address, `CONTPTR` = 0. A `CONT`:

1. `ex_cont` → `CURLINE := CONTLINE`, `RESUMEPTR := 0`, `RESUMEFLAG := 0`,
   `ld sp,(SAVSTK)` (D-CONTD), `jp rp_lp`.
2. `rp_lp` takes the **fresh-line** path (not `rp_resume`), reads the link at
   `CURLINE` — `$0000` — and falls straight into the exit of §3.3.
3. §3.3 calls `cont_record`. `DIRECTF` is still 1 there (stale from the typed
   `CONT` line; nothing re-derived it, because `rp_exec` was never reached), so
   it records nothing and `ret`s — **which is the loop's exit `ret`, at the
   `SAVSTK` depth step 1 restored.** Silent `Ok`.

⚠️ **That stale `DIRECTF` is NOT load-bearing, and the check is the point.**
Had it been 0, `cont_record` would have written `CONTLINE := CURLINE` (the same
marker address), `CONTPTR := 0` and `CONTVALID := 1` — **byte-identical to what
is already there.** The record at this exit is *idempotent*, so the outcome is
the same under either value and a third, fourth, *n*-th `CONT` is silent
(`k_thrice`). This is the [[cont-depth-slice]] lesson applied forward: *when a
path is clean, ask what is absorbing the fault* — here, nothing is, because
there is no fault to absorb.

### 3.7 Cost

| site | Δ page 1 |
|---|---|
| `cont_record` (new routine) | **+19** |
| `do_break` inline body → `call` | **−14** |
| `ex_end` | **+4** |
| `rp_lp` `$0000`-link exit | **+5** |
| `ra_abort` (+ `raise_error_forced` retarget, 0 B) | **+8** |
| `ex_cont` — drop the consume | **−4** |
| `ex_cont` — `ld a,1` → `ld a,h / or l` | **0** |
| estimate | +18 |
| ⚠️ `rp_goto`'s `jr rp_lp` → `jp rp_lp` (see below) | **+1** |
| **AS-BUILT total** | **+19 B, page 1 only** |

⚠️ **THE FIRST BUILD FAILED TO ASSEMBLE, AND THAT IS THE GOOD OUTCOME.** The
5 B §3.3 adds inside the run loop pushed `rp_goto`'s backward `jr rp_lp` past
−128: *"ERROR: Relative jump out of range on line 462 of file
basic/program.asm"*. Widening it to `jp` costs the one byte the estimate did not
have. This is the same failure mode the D-ONEFLG entry records — there, the
build failed and **the probe ran anyway, on the stale machine**, producing five
red rows of pure noise. Here build and probe were chained with `&&`, so nothing
ran. **An estimate that omits a `jr` reach is not a measurement.**

---

## 4. How the ERR 21 sibling slots in — 🔴 **REFUTED ON BOTH COUNTS, 2026-07-31**

> ⚠️ **THIS SECTION IS KEPT AS FILED AND IS WRONG IN TWO PLACES.** D-ERR21
> ([`docs/spec-basic-err21-no-resume.md`](spec-basic-err21-no-resume.md) §2.1)
> measured both:
>
> 1. **`CURLINE := ONELIN` names the wrong line.** The message and `ERL` name the
>    **LAST EXECUTED** line, not the handler's. Falsification F3 built exactly
>    this design: it prints `no resume in 100` where the reference prints
>    `in 110` / `in 200`. It looked right because the characterization it rested
>    on used a program whose handler line WAS its last line.
> 2. **The abort resume point is NOT free.** "an ERR 21 abort reaches `ra_abort`
>    …so ERR 21 gets the measured abort resume point **for free**" — it gets the
>    **wrong** one. `ra_abort` records `SAVTXT`, the failing statement; measured,
>    `CONT` after this abort reprints **nothing**, so the point is the fall-off
>    position. The raiser records it itself and does not route through
>    `ra_abort`.
>
> The one thing this section got right is the PLACEMENT: a prefix at the same
> label, testing `ONEFLG` before site C — and site C is now deleted outright.

## 4.0 (as filed)

[`TODO.md`](../TODO.md) ~line 2549 — *ERR 21 `No RESUME` is never raised* —
hooks **the same `$0000`-link exit**, and its raise condition is exactly *"the
`$0000`-link exit is reached while `ONEFLG` is set"*. After this slice that exit
reads:

```asm
                jr      nz,rp_notend
                ; ← ERR 21 GOES HERE, as a PREFIX: test ONEFLG BEFORE site C
                ;   clears it, and `jp` to the raiser instead of falling through.
                ld      (ONEFLG),a          ; D-ONEFLG site C
                ld      hl,0
                jp      cont_record
```

The raiser is a **prefix at the same label**, above every line this slice adds,
and it never falls through to the record — because an ERR 21 abort reaches
`ra_abort` (§3.4), which records `SAVTXT` like any other abort. So ERR 21 gets
the measured abort resume point **for free**, with no change to §3.3. That
ordering is also why this slice had to come first: building the raiser against
today's exit would have built it against a path about to move.

When ERR 21 lands, D-ONEFLG's site C becomes redundant with site A and its 5 B
can be reclaimed — unchanged by this slice. **(AS-LANDED: site C was deleted
outright; it was 3 B in the post-lean single build, and deleting it fixed a
third defect nobody had measured — D-ERR21 §2.2.)**

---

## 5. The gate

### 5.1 Home

New rows in
[`probes/basic/basic_probe_abort_depth.py`](../probes/basic/basic_probe_abort_depth.py)
(`make abort-acceptance`), beside D-CONTD's eight. Same reasons: two-machine
differential, boot-per-case, echo-anchored **tail** readout (a marker-only
readout cannot see "right answer, then junk"), case-folded, and the file's
standing rule — **no row may arm `ON ERROR`** — is respected by every new row.

⚠️ The abort rows (`k_err*`) raise **untrapped** errors, which is what that file
exists for.

### 5.2 Rows — 18 new, promoted verbatim from §2

Every row in §2's two tables becomes a standing row (`cont2_` prefix). Nine are
**must-NOT-change** rows:

| row | asks |
|---|---|
| `cont2_end_next` | `END` records: `CONT` runs line 30 |
| `cont2_end_rest` | the resume point is **mid-line, after the `END` token** (`[ 9 ]` **and** `[ 2 ]`) |
| `cont2_falloff` | falling off the end records: `CONT` returns silently to `Ok` |
| `cont2_twice` | a second `CONT` is silent |
| `cont2_thrice` | a third `CONT` is silent — the point is never consumed |
| `cont2_err` | an untrapped abort records: `CONT` re-raises it |
| `cont2_err_mid` | the abort's point is the **failing statement**, not the line (`[ 7 ]` must NOT reprint) |
| `cont2_err_twice` | the abort's point is stable |
| `cont2_err22` | the forced (ERR 22) abort arm records too |
| `cont2_typed_stop` | a typed `STOP` must **NOT** destroy a live resume point |
| `cont2_typed_end` | **must NOT**: a typed `END` leaves it alone |
| `cont2_typed_err` | **must NOT**: a typed error leaves it alone |
| `cont2_typed_keep` | **must NOT**: an intervening typed line leaves it alone |
| `cont2_restop` | **must NOT**: the point MOVES to each new stop |
| `cont2_ctl_stop` | CONTROL: the one stop that already worked still works |
| `cont2_norun` | **must NOT**: `CONT` on a cold machine still `can't continue` |
| `cont2_new` | **must NOT**: `NEW` still invalidates |
| `cont2_end_only` | **must NOT**: a typed `END` with nothing live still `can't continue` |

Plus D-CONTD's existing eight and `basic_probe_direct_ctrl.py`'s typed-`STOP`
row, which are the *regression* half.

### 5.3 Falsification — AS-RUN, six separate builds

The green state of this gate is "a divergence went away", so **a red row is the
success signal** and every falsification is paired with rows that must stay
GREEN ([[apparatus-is-part-of-the-measurement]]). Each row below is a real
`rm -rf build && make basic-reloc && make abort-acceptance ONLY=cont2` over all
18 rows, so every entry carries its own denominator.

| build | went RED | score | predicted? |
|---|---|---|---|
| **F1** delete `ex_end`'s `inc hl / call cont_record` | `end_next`, `end_rest`, `twice`, `thrice` | 14/18 | ✅ exactly |
| **F2** delete the `$0000`-link record (§3.3) | `falloff`, `twice`, `thrice` | 15/18 | ✅ exactly |
| **F3** delete `ra_abort`'s record (§3.4) | `err`, `err_mid`, `err_twice`, `err22` | 14/18 | ✅ exactly |
| **F4** restore `ex_cont`'s `xor a / ld (CONTVALID),a` consume | **`thrice` ALONE** | 17/18 | ❌ **REFUTED** — see below |
| **F5** direct mode INVALIDATES instead of skipping (the old `do_break` rule) | `typed_stop`, `typed_end`, `typed_err`, `typed_keep`, **`thrice`** | 13/18 | ❌ wider than predicted |
| **F6** `ld a,1` instead of `ld a,h / or l` (§3.5) | `falloff`, `twice`, `thrice` | 15/18 | ✅ exactly |

F1/F2/F3 have **disjoint** RED sets: the site→row map is 1:1 per site, which is
the most a shared routine allows. F6 is the one-character build — with `ld a,1`
the sentinel resumes **mid-line at address 0** and the machine executes the boot
ROM as BASIC text: `syntax error in 65`.

🔴 **F4 REFUTED THIS SPEC'S OWN PREDICTION, AND THE REASON IS THE POINT.** §5.3
predicted `twice`, `thrice` *and* `err_twice` would go red with the consume
restored. Only `thrice` did. **The per-stop re-record ABSORBS the consume**: the
1st `CONT` consumes the point, but the run it resumes then *stops again* — off
the `$0000` link, or in `ra_abort` — and that stop records a fresh point, so the
2nd `CONT` works anyway. The only path where nothing re-records is the 2nd
`CONT`'s immediate re-entry past the end (§3.6: `DIRECTF` is stale-1 there, so
`cont_record` skips), which is why **`cont2_thrice` is the ONLY row in the whole
battery that can see the consume at all.** A battery that stopped at two `CONT`s
deep would have scored dropping the consume as unnecessary and left it in.

That is the [[cont-depth-slice]] lesson arriving one slice later: *when only SOME
paths misbehave, ask what is ABSORBING the fault on the others.* Here the
absorber is the very mechanism this slice adds.

🔴 **F5 shows the two behaviour changes are COUPLED.** Under invalidate-instead-
of-skip, `cont2_thrice` goes red too — because that same stale-`DIRECTF` re-entry
then *clears* `CONTVALID` instead of leaving it. So §3.6's "the stale `DIRECTF`
is not load-bearing" is true **only** because the direct-mode arm is a pure
skip. F5 also confirms §2.2's argument from the other side: `cont2_norun`,
`cont2_new` and `cont2_end_only` stay **GREEN** under the old rule — the old
rule fitted the old rows exactly, which is why it survived.

### 5.4 Standing gates — AS-RUN, not assumed

All run against the final build, sequentially, one emulator gate at a time.

| gate | result |
|---|---|
| clean `make basic-reloc` (incl. the HARD dead-code sweep) | **0 dead, both builds** |
| `make abort-acceptance` | **49/49** (31 pre-existing + 18 new) |
| `make error-trap-acceptance` (incl. `oneflg_keep` / `oneflg_suspend_resume`, which drive `CONT` through this exact path) | ALL PASS |
| `make stop-trap-acceptance` | ALL PASS |
| `make diskbasic-acceptance` | **34/34** |
| `make bdos-acceptance` | **12/12** |
| `make fat-error-acceptance` | **7/7** |
| `make linemax-acceptance` | **60/60** |
| `make arrdim-acceptance` | **73/73** |
| `make clearpool-acceptance` | **52/52** |
| `make array-acceptance` | **149/151** — the two standing `ifc.instr.zero` / `ifc.instr.neg` capitalisation rows, confirmed **BY NAME**, not by count |
| `make chancost-characterize` | **39 cases / 1 filed** (`lof_new`) |
| `make unit-test` | **54/54 — but only after §5.5** |

⚠️ Build and probe are chained with `&&` — a build that failed to assemble once
let a probe run on the stale machine and produced five red rows of pure noise
(TODO.md, D-ONEFLG). It paid off immediately here: §3.7's `jr`-out-of-range
build failed and nothing ran. `make repack-machine` after every `basic/` change.

### 5.5 🔴 `make unit-test` went RED — and the defect was in the TEST

`test_poke.py`'s *"POKE missing comma → ERRMARK=$DD"* row failed with
**`ERRMARK=$DB`**. `$DB` is `ex_goto_undef`'s landmark — a routine `POKE` cannot
reach.

The row did `try: m.call("do_poke") except: pass`, then read `ERRMARK` **after
the call**. But the abort funnel does `ld sp,(SAVSTK)`, and `SAVSTK` is 0 in
`msxtest`'s zeroed RAM, so the funnel's tail `ret` popped from `$0000` and the
CPU **ran away** until msxtest's 2,000,000-step guard fired — which the
`except` swallowed. The assertion was reading *whatever `ERRMARK` held after two
million steps of executing the ROM from an arbitrary entry point*. Shifting page
1 by 19 bytes moved where the runaway landed.

**Proven, not assumed.** Sampled BOTH ways on ONE fixed build: the old sample
point reads **`$DB`** after the four preceding `POKE` cases and **`$3A`** when
the case runs alone — it is a function of unrelated prior test state, not of the
build and certainly not of `stmt_error`. Sampling at `fre_abort_low` reads
**`$DD`**, deterministically, with no runaway at all.

Fixed by trapping `fre_abort_low` and sampling `ERRMARK` there — the one moment
the row is actually about — and dropping the `except` guard so a genuine runaway
is loud. `do_poke` and `stmt_error` were never wrong.

**This is [[apparatus-is-part-of-the-measurement]] again, in its purest form: a
green row that had agreed for the wrong reason for its whole life, and it took a
19-byte shift somewhere else in the ROM to expose it.** The class to look for is
*any* host-harness row that reads RAM after a call that can reach
`ld sp,(SAVSTK)` with `SAVSTK` unset.

---

## 6. Doc debt this slice pays

1. **`ex_stop`'s header** (`basic/program.asm:721-644`) — delete the false
   parenthetical about `END`; state the §1 rule and name this spec.
2. **`ex_cont`'s header** (`basic/program.asm:828-685`) — *"CONT consumes the
   resume point (CONTVALID -> 0) so a second bare CONT does not re-resume a run
   that has since finished"* is now wrong in both halves: it is not consumed,
   and a second bare `CONT` **does** re-resume — silently, past the end.
3. **`do_break`'s direct-mode comment** (`basic/program.asm:607-532`) — the
   measurement it cites is real but does not support "invalidate"; §2.2.
4. **`docs/spec-basic-direct-ctrl.md` §5** — add a pointer: the typed-break rule
   is *"records nothing"*, not *"invalidates"*.
5. **[`probes/basic/basic_probe_cont.py`](../probes/basic/basic_probe_cont.py)** —
   ⚠️ **found broken during this spec**: it is wired into **no** make target, its
   `run(cart, …)` calls reference a `cart` global that the lean-cart retirement
   deleted (an instant `NameError`), and its case (e) asserts *"CONT after a
   STOP-less RUN → can't continue"*, which §2 measures as a **divergence**. It
   cannot be left as-is. See sign-off Q3.

---

## 7. Wall accounting — baseline AS-MEASURED, cost AS-ESTIMATED

| | low region | page 1 |
|---|---|---|
| clean baseline at `0b7cbed` (`rm -rf build && make basic-reloc`) | **80 B free** | **49 B free** |
| §3.7 estimate | — | −18 B |
| the `jr` → `jp` the estimate lacked | — | −1 B |
| **AS-BUILT** (clean `rm -rf build && make basic-reloc`) | **80 B free** | **30 B free** |

No carve, no promotion, no eviction needed. The low region — the harder wall,
co-mapped with page 1 — is untouched, and `build/sub.rom` is **byte-identical**
to the baseline (`01ab5dc2…`), as a main-only slice requires.

---

## 8. Explicitly NOT in this slice

* **ERR 21 `No RESUME`** — its own TODO item. §4 shows where it slots in.
* Ctrl-STOP at the new stops (§2.3) — unmeasurable through this harness.
* `lof_new`, the README "Limitations" staleness, the line-number/embedded-blank
  scan — unrelated open items.

---

## 9. Sign-off — ANSWERED 2026-07-30, before implementation

1. **Include the abort sites (§3.4, +8 B) in this slice, or file them
   separately?** → ✅ **INCLUDE.** The item's own carried-forward rule is *"the
   run loop records where it stopped, ALWAYS"*, an abort is a run stop, four
   measured rows (`k_err`, `k_err_mid`, `k_err_twice`, `k_err22`) diverge on it,
   and it reuses the same routine and the already-maintained `SAVTXT` anchor.
   *Rejected:* filing them separately — the new gate would have enshrined four
   rows as known-divergent and the next reader would re-derive this same
   characterization.

2. **Fix `do_break`'s direct-mode arm from "invalidate" to "do nothing"
   (§2.2/§3.1) in this slice?** → ✅ **YES.** 0 additional bytes (it falls out
   of sharing `cont_record`), `k_typed_stop` measures it, and keeping the old
   behaviour would need `cont_record` to carry two arms — *more* bytes, not
   fewer. It overturns wording in a landed spec (§6.4), so it was called out
   rather than slipped in.

3. **What to do about `probes/basic/basic_probe_cont.py` (§6.5)?** →
   ✅ **RETIRE it** (delete). Every behaviour it claims is now gated by
   `abort-acceptance` rows that actually run, except its Ctrl-STOP key-press
   case (g), which `stop-trap-acceptance` covers.
   *Rejected:* repairing + wiring it in (more apparatus, overlapping coverage),
   and leaving it (rot, with a now-wrong assertion in it).

4. **`CONTPTR = 0` as the "fresh-line re-entry" sentinel (§3.3/§3.5)** — 0
   bytes, and `$0000` is unreachable as a real token pointer. ✅ Signed off.
   *Rejected:* a separate flag byte (a new sysvar + writes at two sites), and
   making the `$0000`-link exit record the *previous* line's tail (needs a
   backwards walk the loop does not keep).

---

## 10. Clean-room

No reference-ROM disassembly. Every rule in §1 and §2 comes from black-box
screen output through the KEYBUF-injection REPL driver against a stock
`Philips_VG_8020` in openMSX; §3's mechanism is traced through zerobas's own
source. See the clean-room firewall in [`CONTRIBUTING.md`](../CONTRIBUTING.md).
