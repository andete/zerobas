<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Implementation packet — Error-handling **S2b** (`ON ERROR GOTO` + trap + `RESUME`)

Status: **LANDED 2026-07-19 (main tip)** — signed off + implemented; see the AS-BUILT
section below (3 severe trap bugs caught by the lead's empirical pass, one minor
divergence deferred). This is the detailed implementation packet for
S2b, the final slice of the error-handling arc, built on top of the landed **S1**
(D-1 abort + D-2 ` in <line>`) and **S2a** (`raise_error` dispatcher + `ERR`/`ERL` +
`ERROR n`, no trapping). It refines the signed-off outline in
[spec-basic-error-handling-s2.md](spec-basic-error-handling-s2.md) §8 (the S2b bullet)
and §5.2/§5.3, with the code now measured (not estimated). Follows the S2a packet
pattern ([spec-basic-error-handling-s2a-packet.md](spec-basic-error-handling-s2a-packet.md)).

Repack-only (every byte behind `IF ROM_BASE < $4000`); the lean 16 KB `basic.rom`
must stay **byte-identical** (hash `9e723a02…`, `tools/check_reloc.py`).

**Model-split note:** this packet is the sign-off target; implementation is a Sonnet
task per [[opus-vs-sonnet-model-split]] once signed off. Its Definition of Done
**includes running the openMSX acceptance suites** ([[gate-during-implementation]]).



## AS-BUILT (2026-07-19) — LANDED on main; adversarial pass caught 3 severe bugs

S2b shipped (main tip): ON ERROR GOTO/GOTO 0, the trap branch, SAVSTK, SAVTXT capture,
the full RESUME family (RESUME/0/NEXT/<line>), scan_stmt_end as a page-1 sub-ROM leaf
tenant (SUBROM_IDX_SCANSTMT=11, quote-aware). Funded by the CALL FORMAT eviction
(spec-evict-call-format.md; page-1 17->262B). Space consumed to **1B free**, lean
byte-identical. Gates ALL GREEN: unit 46, error/error-trap/input/string/float/math
acceptance, array 150, diskbasic 34 lean+34 repack, tenant-closure (--page0 393 /
--page1 167 incl. scan_stmt_end)/kwtable/resident-abi.

**The lead's adversarial+empirical VG-8020 differential (load-bearing, the recurring
lesson again) caught THREE severe bugs the green build HID** — the trap NEVER fired
until fixed (the landed subset built green but was catastrophically broken):
1. Trap set GOTOTGT/GOTOFLAG then `jp rp_lp`, but rp_lp ignores GOTOFLAG (only rp_goto's
   post-exec arm consumes it) -> re-ran the erroring line -> forced abort. Fix: set
   CURLINE=ONELIN directly.
2. FPERR=3 (SQR/LOG illegal-fn) and FPERR=6 (array OOM) `jp`'d fre_abort_low DIRECTLY
   (an S2a message-override shortcut predating the trap) -> never trapped, while 1/0 did.
   Fix: raise_error refactored to resolve message first, then funnel ALL paths through a
   shared `raise_error_hl` trap decision (ONELIN via DE so HL=message survives).
3. RESUME 0 / RESUME <line> -> syntax error: tokeniser's branch_lineno list omitted
   RESUME -> the arg wasn't crunched to $0E. Fix: add RESUME (repack-guarded, sub-side).

**ERR-reset-on-RESUME follow-up — LANDED 2026-07-19 (was the S2b "KNOWN DEFERRED"
charter-debt item).** The empirical VG-8020 pin CORRECTED the deferred note's premise:
the reference resets **only ERR to 0 on RESUME and KEEPS ERL** (all four forms print
`0 / 20`, not `0 / 0`) — so the fix is a 1-byte cell (ERRCODE), not the word ERRLINE.
Implementation: a 4 B `xor a` / `ld (ERRCODE),a` at `ex_resume`'s trap-active head (after
the `ONEFLG!=0` check, so `ex_resume_noerr`/ERR 22 is untouched and a malformed RESUME
still forced-aborts with ONEFLG intact — both empirically re-pinned). SELF-FUNDED by three
provably-redundant `xor a` reclaims (`run_prog`, `init`, `oe_disable` — each preceded by
code that leaves A=0; repack-only, lean byte-identical): page-1 net 1->0 B free. Gated in
`basic_probe_error_trap.py`'s resume_line case (ERR->0 AND ERL kept, both machines). All
standing gates green.

**ERROR n arg-validation follow-up — LANDED 2026-07-19 (the S2a §3(g) / §9 Q5 deferral).**
The empirical VG-8020 pin fixed the faithful domain: `ERROR n` is valid for **1..255**;
0, 256, and any out-of-range value WITHIN int16 raise **ERR 5** (illegal function call);
1..255 raise that code verbatim (`ERROR 200`->ERR 200, an unprintable-message code). So
`ex_error` now rejects the FULL evaluated value (`D<>0` -> >255/negative, or `E==0` ->
value 0) instead of blindly taking the low byte (which mishandled 0/256/-1 and e.g.
300->44). SELF-FUNDED, all repack-only, lean byte-identical: `raise_error`'s domain guard
golfed `or a`/`jr z`/`cp 24`/`jr nc`/`dec a` -> `dec a`/`cp 23`/`jr nc` (-3 B, code 0 wraps
to $FF, still caught) + the two FPERR one-code-two-message specials (`fre_arymem_oom`/
`fre_illegalfn_lc`) factored to a shared `ld (ERRCODE),a`/`record_errline`/`raise_error_hl`
tail (-5 B) fund the +8 B check; page-1 stays 0 B. **KNOWN boundary (out of scope, the
separate pre-existing D-F2-2 int-arg-coercion seam):** `|n|` that OVERFLOWS int16 (e.g.
`ERROR 32768`) -> reference ERR 6 (Overflow, raised by its int coercion) vs zerobas ERR 5;
zerobas does not overflow-check int-arg coercion for ANY statement. Gated in
`basic_probe_error_trap.py`'s error_arg differential (10 cases across the int16 domain).

**The error-handling arc is now CLOSED** — no remaining faithful-domain edges (the only
open item is the cross-cutting D-F2-2 int-coercion seam, tracked with the float pack, not
error handling).

---

## 0. What S2a already gives us (the substrate)

Verified in-tree this session:

* **`raise_error`** (basic/interp.asm:618) — the dispatcher. `in: A = MSX ERR code`.
  Records `ERRCODE`, calls `record_errline`, looks the code up in `err_msgtab`, and
  falls into `fre_abort_low` (the S1 abort body). Its header comment already marks the
  **exact seam** for S2b's trap branch: *"between the `call record_errline` below and
  the message lookup."* (interp.asm:614-616.)
* **`record_errline`** (interp.asm:648) — `ERRLINE := run? (CURLINE+2) : 65535`.
  Reused unchanged; the direct-mode 65535 sentinel is already the pinned convention.
* **`err_msgtab`** (interp.asm:676) — ERR-code-indexed (1..23) message pointer table.
  Codes **21 (No RESUME)** and **22 (RESUME without error)** are currently holes
  pointing at `err_unprintable`; S2b fills them (§8).
* **`ERRCODE`** ($E1C5, 1 B), **`ERRLINE`** ($E1C6, 2 B) — live RAM cells
  (basic/sysvars.inc:448-450). **Not** zeroed by `clear_vars` (S2a adversarial fix,
  commit 5967659): they persist across NEW/CLEAR/RUN, zeroed only at cold boot in
  `init`. See §7 — the analogous question for `ONELIN` is **open and must be pinned**.
* **`DIRECTF`** ($E1C2) — 1 direct / 0 run, set before any statement runs.
* Tokens `ERROR`=$A6 (interp statement switch already dispatches it, interp.asm:242→
  `ex_error`), `ERR`=$E2, `ERL`=$E1 (basic/kwtable.inc:296-298; equs
  sysvars.inc:835-837). The kwtable is **resident in main** (basic/kwtable.inc), NOT
  sub-side — the S2 spec §5.1's "kwtable is sub-side" note is **stale** (it moved back);
  so adding `RESUME` needs **no sub.rom rebuild**, no `SUB_PARTS` concern.
* **Run-loop resume vehicle** (basic/program.asm): `RESUMEFLAG`/`RESUMEPTR`
  (program.asm:209/242). `rp_lp` (line 223) checks `RESUMEFLAG`; if set, `rp_resume`
  (239) clears it and jumps to `(RESUMEPTR)` = an exact mid-line statement pointer,
  `CURLINE` already pointing at its line. Today set by `RETURN` and a continuing `NEXT`.
  **This is the reuse vehicle for `RESUME`.**
* **`ex_on`** (program.asm:1215) — `ON <expr> GOTO/GOSUB`. `ON ERROR` extends it (§5).
* **`err_msgtab` string reuse** and the `DIRECTF`/`CURLINE+2` conventions are all in
  place; S2b adds no new reporting code.

**What S2a deliberately deferred to S2b** (its header comment, interp.asm:611-615):
the **trap branch** in `raise_error`, and the **`SAVSTK`** stack anchor (S2a saved the
8 page-1 bytes by not writing it — no trap exists yet to need it).

---

## 1. Scope (locked by the S2 spec sign-off)

**In:** `ON ERROR GOTO <line>`, `ON ERROR GOTO 0`; `RESUME` / `RESUME 0`,
`RESUME NEXT`, `RESUME <line>`; the trap branch in `raise_error`; `SAVSTK`;
`ONELIN`/`ONEFLG`/`ERRRESUME`; the `RESUME` token; ERR codes **21** (No RESUME) and
**22** (RESUME without error).

**Out** (S2 spec §9 Q5): `ON ERROR RESUME NEXT` (MSX2); ERR ≥ 50 disk/FIELD codes;
`load_error` (ERR 19) unification (still its own later item, S1 §9.1); the `ERROR 0`
→ ERR 5 arg-validation polish (S2a §3(g)-deferred — fold in here **only if** free, §9).

---

## 2. Tokens

Only **`RESUME`** is un-tokenised. Black-box-pinned **$A7** ([[s2-error-token-pins]],
`resume next` → `A7 20 83`; `resume 0` → `A7 20 0E 00 00`). No prefix hazard (unlike
ERR/ERROR). `ERROR` (for `ON ERROR`) is already $A6.

* `basic/sysvars.inc`: add `RESUME_TOKEN equ $A7`.
* `basic/kwtable.inc`: add `db 6,"RESUME",1,RESUME_TOKEN` (repack-guarded region, near
  the ERROR/ERR/ERL block at :296). No ordering hazard.
* `basic/interp.asm` statement switch (~:244, in the `IF ROM_BASE<$4000` block by
  `ERROR_TOKEN`): `cp RESUME_TOKEN` / `jp z,ex_resume`.

`ON ERROR` needs **no** new token — it is `ON_TOKEN` ($95) + `ERROR_TOKEN` ($A6),
detected inside `ex_on` (§5).

---

## 3. RAM state (new cells)

Freed VARTAB window, below the live cells. Current occupancy (sysvars.inc:434-450):
`ARYTAB` $E1C0 (live), `DIRECTF` $E1C2, **$E1C3/C4 reserved for `SAVSTK`**, `ERRCODE`
$E1C5, `ERRLINE` $E1C6/C7. Next free = **$E1C8**; window is clear up to `$E240`.

| Cell | Size | Addr | Meaning | Set by |
|---|---|---|---|---|
| `SAVSTK` | 2 | $E1C3 | SP anchor for the trap unwind | `run_prog` / `dispatch_line` |
| `ONELIN` | 2 | $E1C8 | `ON ERROR` handler line's text addr; 0 = no handler | `ex_on` (ON ERROR) |
| `ONEFLG` | 1 | $E1CA | 1 = inside a handler (nested error → forced abort) | trap / `RESUME` |
| `ERRRESUME` | 4 | $E1CB | resume context: [erroring CURLINE:2][erroring stmt ptr:2] | trap capture (§4) |
| `SAVTXT` | 2 | $E1CF | current statement's text ptr (live, per-statement) | `exec_stmt` (§4) |

All zeroing/init decisions for `ONELIN`/`ONEFLG` are in §7 (**must be black-box-pinned**,
not assumed). `SAVSTK`/`SAVTXT`/`ERRRESUME` need no cold-init (written before read).
Total new RAM: 11 B, all in the free window — **zero ROM-image cost for RAM**.

---

## 4. The `RESUME` context capture problem (the delicate core)

`RESUME` must re-enter the erroring **statement** (or the one after it). But zerobas's
**deferred-error discipline** means `raise_error` fires at the statement boundary from
*any* depth (FPERR realised in `check_expr_errors`, direct-print sites mid-handler) —
the erroring statement's **start** pointer is not in any register at that moment. So we
capture it continuously and read it at trap time:

* **`SAVTXT` capture.** At `exec_stmt` entry (interp.asm:109 — the per-statement
  dispatch head, reached at line start AND after every `:` via `ex_sep`), save
  `ld (SAVTXT),hl` before dispatching. This mirrors MSX's `SAVTXT`/NEWSTT. Cost: 3 B on
  the statement hot path (page-1). **This is the ONE hot-path edit** — measure it stays
  correct for multi-`:` lines (the whole point: `RESUME` on `20 X=1:Y=SQR(-1):Z=3`
  must retry the *middle* statement, not line-start).
* **Trap capture.** In `raise_error`'s trap branch (§5), before jumping to the handler:
  `ERRRESUME[0..1] := (CURLINE)`, `ERRRESUME[2..3] := (SAVTXT)`.

Why not capture at the deferred-realisation point? Because `check_expr_errors` runs
with HL mid-statement (post-`eval`), not at the statement head — unusable for retry.
`SAVTXT` is the only clean source.

**Open (§9 Q3):** confirm `SAVTXT`-at-`exec_stmt` vs. capturing at `rp_exec` (line
granularity only — would break mid-`:` `RESUME`). Recommend `exec_stmt`.

---

## 5. `raise_error` trap branch + `ON ERROR` + `RESUME`

### 5.1 The trap branch (insert at the marked seam, interp.asm ~:620)

```
raise_error:
    ld   (ERRCODE),a
    call record_errline
    ; --- S2b trap decision (NEW; the seam the S2a comment reserved) ---
    ld   hl,(ONELIN)
    ld   a,h
    or   l
    jr   z,rerr_report          ; ONELIN==0 -> no handler -> S2a report path
    ld   a,(ONEFLG)
    or   a
    jr   nz,rerr_report         ; already in a handler (no RESUME yet) -> forced abort
    ; take the trap:
    ld   sp,(SAVSTK)            ; §6: unwind any call depth to the run anchor
    ld   a,1
    ld   (ONEFLG),a
    ld   de,(CURLINE)           ; capture resume context (§4)
    ld   (ERRRESUME),de
    ld   de,(SAVTXT)
    ld   (ERRRESUME+2),de
    ld   hl,(ONELIN)
    ld   (GOTOTGT),hl           ; reuse GOTO's branch: set target + flag,
    ld   a,1                    ; then re-enter the run loop cleanly
    ld   (GOTOFLAG),a
    xor  a
    ld   (RESUMEFLAG),a
    jp   rp_lp                  ; run loop honours GOTOFLAG -> jumps to ONELIN's line
rerr_report:                    ; == S2a's original body from `ld a,(ERRCODE)` on:
    ld   a,(ERRCODE)
    ... (unchanged err_msgtab lookup -> jp fre_abort_low) ...
```

Design notes:
* **Reusing `GOTOTGT`/`GOTOFLAG` + `jp rp_lp`** (vs. `ld hl,(ONELIN)` / jump into a
  run-loop resume entry) is the cleanest: `ONELIN` stores the handler line's **link
  address** (what `find_line_bc` returns, = a `CURLINE`-shaped value), and `rp_goto`
  already does `ld (CURLINE),hl` + re-reads the token body. So the trap is exactly a
  GOTO to the handler line, after the `SAVSTK` reset — no new run-loop entry point.
  Confirm `ONELIN` stores the link addr (not the token body) so `rp_goto` is correct.
* **`ld sp,(SAVSTK)` MUST precede `jp rp_lp`** — the trap fires from arbitrary call
  depth; without the reset the run loop runs on a corrupt stack. This is the whole
  reason `SAVSTK` exists.
* Nested-error guard (`ONEFLG`≠0 → `rerr_report`) gives real-MSX behaviour: an error
  inside a handler with no intervening `RESUME` aborts with the *inner* message.

### 5.2 `SAVSTK` anchors (§6)

`ld (SAVSTK),sp` at:
* **`run_prog`** (program.asm:192, at RUN entry before the run loop) — the run anchor.
* **`dispatch_line`** direct entry (program.asm:30) — so a direct-mode `ERROR n`/error
  with a handler resets cleanly. (Direct error *without* handler stays S1-correct.)

Both are 4 B (`ld (SAVSTK),sp` = ED 73 nn nn). 8 B total, page-1 (run_prog) + page-1
(dispatch_line). Deferred from S2a precisely to spend here.

### 5.3 `ON ERROR GOTO <line>` / `GOTO 0`  (extend `ex_on`)

`ex_on` (program.asm:1215) currently does `inc hl` (past ON) then `call eval`. Insert a
peek: after `inc hl`, `call skip_spaces`; if `(hl)==ERROR_TOKEN`, branch to `ex_on_error`:

```
ex_on_error:
    inc  hl                     ; past ERROR token
    call skip_spaces
    cp   GOTO_TOKEN             ; syntax: ON ERROR *GOTO* <line>
    jp   nz,stmt_error
    inc  hl
    call eon_seek_line          ; parse the single $0E line number -> BC (reuse the
                                ;  $0E line-number read; NOT eon_seek_nth's list scan)
    ld   a,b
    or   c
    jr   z,oe_disable           ; GOTO 0 -> disable
    call find_line_bc           ; resolve to link addr
    jp   nc,ex_goto_undef       ; undefined line -> Undefined line number (ref behaviour)
    ld   (ONELIN),hl
    ret
oe_disable:
    ld   hl,0
    ld   (ONELIN),hl            ; 0 -> no handler; also re-enables normal aborts
    xor  a
    ld   (ONEFLG),a            ; GOTO 0 inside a handler clears the in-handler state
    ret
```

The single-`$0E`-line read (`eon_seek_line`) is a trivial subset of `eon_seek_nth`
(program.asm:1291) — read `$0E lo hi` → BC. May be able to reuse a shared line-number
reader (the GOTO path has one: `ex_goto` reads a `$0E` operand — reuse it).

### 5.4 `RESUME` family  (`ex_resume`, interp.asm)

```
ex_resume:
    ld   a,(ONEFLG)
    or   a
    jp   z,rerr_no_resume       ; RESUME with no active trap -> ERR 22 (via ld a,22 / raise_error)
    inc  hl                     ; past RESUME token
    call skip_spaces
    or   a                      ; end of statement (bare RESUME / RESUME <EOL>)?
    jr   z,res_same
    cp   COLON
    jr   z,res_same
    cp   NEXT_TOKEN             ; RESUME NEXT
    jr   z,res_next
    ; else RESUME <line> or RESUME 0
    call <read $0E line number -> BC>
    ld   a,b
    or   c
    jr   z,res_same             ; RESUME 0 == RESUME (retry erroring stmt)
    call find_line_bc
    jp   nc,ex_goto_undef
    ; resume at <line>'s first statement:
    xor  a
    ld   (ONEFLG),a
    ld   (CURLINE),hl           ; (hl = link addr) -- via GOTOTGT/GOTOFLAG like the trap
    ... set GOTOFLAG, jp back into run loop ...
res_same:                       ; RESUME / RESUME 0 -> re-run the erroring statement
    xor  a
    ld   (ONEFLG),a
    ld   hl,(ERRRESUME)         ; erroring CURLINE
    ld   (CURLINE),hl
    ld   hl,(ERRRESUME+2)       ; erroring statement ptr
    ld   (RESUMEPTR),hl
    ld   a,1
    ld   (RESUMEFLAG),a
    ret                         ; run loop's rp_resume jumps to (RESUMEPTR)
res_next:                       ; RESUME NEXT -> the statement AFTER the erroring one
    xor  a
    ld   (ONEFLG),a
    ld   hl,(ERRRESUME)
    ld   (CURLINE),hl
    ld   hl,(ERRRESUME+2)
    call scan_stmt_end          ; advance HL past the erroring statement (§4/§5.5)
    ...  -> RESUMEPTR = HL (next stmt) or, if EOL, advance CURLINE to next line ...
```

**Crucial subtlety — `ex_resume` returns into the run loop, it does not itself jump.**
`RESUME`/`RESUME NEXT` are statements executed *inside the handler*, which the run loop
called via `call exec`. Setting `RESUMEFLAG`+`RESUMEPTR` (+`CURLINE`) and doing a plain
`ret` lets `exec` return to `rp_exec`, whose post-`exec` check sees `RESUMEFLAG` and
loops to `rp_resume` → jumps to `(RESUMEPTR)`. **No `SAVSTK` reset needed on the RESUME
path** — the handler ran at the SAVSTK-clean depth already (the trap reset it before
entering the handler), so `exec`'s normal `ret` unwinds correctly. Verify: the handler
must not have left junk on the stack (GOSUB inside a handler without RETURN would — a
real-MSX-shared caveat, out of scope to guard).

For `RESUME <line>` the handler-return is the same shape, but via `GOTOFLAG`/`GOTOTGT`
(a line branch, no mid-line ptr) rather than `RESUMEFLAG`.

### 5.5 `scan_stmt_end` (RESUME NEXT's statement-advance) — **new code, quote-aware**

No reusable scanner exists (`ex_data`'s `exd_lp` scans to `:`/EOL but is **not**
quote-aware). `RESUME NEXT` must advance from the erroring statement's start to the next
statement:
* skip a quoted string literal on `$22` (to the closing `$22` or EOL) so a `:` inside
  `PRINT "a:b"` is not a false separator;
* `REM`/`DATA`/`ELSE`/`'` tokens consume to EOL (→ next line);
* stop at `$3A` (`COLON`) → next statement is `HL+1` on the same line (`RESUMEPTR`);
* stop at `$00` (EOL) → advance `CURLINE` to the link (next line), normal `RESUMEFLAG=0`
  fall-through.

Estimated ~25-35 B. **This is the single biggest new leaf in S2b and the main space
risk** (§8). Options if space-blocked: (a) a minimal non-quote-aware scan matching
`exd_lp` (documented deviation: a `:` inside a string literal on the erroring line
mis-resumes — rare, but a faithfulness gap), or (b) tenant `scan_stmt_end` sub-side.
**Recommend the full quote-aware scan in main** if the §8 reclaim covers it; else flag
the deviation for a decision.

---

## 6. `SAVSTK` correctness

Covered inline in §5.1/§5.2. The invariant: **the trap path is the only consumer**;
`ld sp,(SAVSTK)` runs exactly once per trap, immediately before re-entering the run
loop at the handler line. The abort path (`rerr_report`) and the RESUME path do **not**
touch SP (S1's `ENDFLAG` unwind and `exec`'s normal `ret` respectively stay correct).
This is strictly additive to the proven S1/S2a paths — a key safety property for the
[[error-handling-arc]] RECURRING LESSON (don't perturb the proven abort funnel).

---

## 7. `ONELIN`/`ONEFLG` reset scope — **MUST black-box-pin (do not assume)**

The S2 spec §4 says *"Cold boot + clear_vars zero ONELIN/ONEFLG/ERRCODE/ERRLINE (so
ON ERROR state does not survive NEW/RUN)."* **That §4 claim is already partly
falsified:** the S2a adversarial pass (commit 5967659) proved `ERRCODE`/`ERRLINE`
persist across NEW/CLEAR/RUN (cold-boot-zero only), and moved their zero out of
`clear_vars` into `init`. So the analogous claim for `ONELIN`/`ONEFLG` is **suspect and
must be empirically pinned on the VG-8020**, not taken from the spec:

* Does `RUN` clear the `ON ERROR` handler? (GW/MSX: **RUN does re-arm from scratch** —
  a fresh RUN starts with no handler. Likely `ONELIN:=0` at `run_prog`.)
* Does `NEW` clear it? (Almost certainly yes.)
* Does `CLEAR` clear it? (Needs pinning — `CLEAR` resets variables; MSX behaviour for
  the trap vector specifically must be observed.)
* Cold-boot: 0 (no handler).

**Probe (add to the acceptance harness):** set `ON ERROR GOTO 100`, then `RUN`/`NEW`/
`CLEAR`, then trigger an error and observe whether the handler fires or the program
aborts — on both VG-8020 and repack. Pin each hook's behaviour before choosing where
`ONELIN`/`ONEFLG` are zeroed (`run_prog` vs `clear_vars` vs `init`). **This is the S2b
analogue of the exact faithfulness bug the S2a adversarial pass caught — treat it as
load-bearing.**

Working hypothesis (to be confirmed, not implemented blind): `ONELIN`/`ONEFLG`:=0 at
`run_prog` (RUN re-arms) and `init` (cold); leave `clear_vars` alone.

---

## 8. Space budget & reclaim plan

**Measured now:** page-1 **17 B** free, low region **3 B** (`tools/check_reloc.py`).

Rough S2b additions (page-1 unless noted):
| item | est. |
|---|---|
| `RESUME` kwtable entry | +8 B |
| statement-switch `cp RESUME_TOKEN`/`jp` | +5 B |
| `SAVTXT` capture at `exec_stmt` | +3 B |
| `SAVSTK` saves ×2 (run_prog, dispatch_line) | +8 B |
| `raise_error` trap branch | +~28 B |
| `ex_on_error` | +~22 B |
| `ex_resume` (all four forms) | +~45 B |
| `scan_stmt_end` (quote-aware) | +~30 B |
| ERR 21/22 msgtab wiring + 2 strings | strings go **low region**; ptrs in-table (free) |
| **total (page-1)** | **≈ 150 B** ≫ 17 B free |

So S2b **does not self-fund** — as the S2 spec §7 predicted. Levers, in order:

1. **String-dedup + site reclaim (main).** The S1/S2a passes have already harvested the
   easy dups ("out of memory"×3, "illegal function call"×2, "syntax error"). Re-measure
   remaining per-region dups (the standing discipline: MEASURE before walling
   [[error-handling-arc]]). Likely thin now.
2. **Further PRINT-USING / format.asm eviction to sub-ROM.** The PRINT-USING format
   scanners were evicted (c3fc2d8) to free the 217 B that funded S2a; the **render
   engine** (`format.asm`) is the flagged reserve (S2 packet note). Evicting more of it
   is the most-proven lever (same tenant playbook, already paved).
3. **Sub-ROM tenant for the S2b leaves.** `scan_stmt_end`, the `ex_resume` body, and
   `ex_on_error` are natural page-0/1 tenants — the glue (`ld a,n`+`jp`/`call`,
   statement-switch dispatch) stays in main, the leaves go sub-side
   ([[subrom-tenant-playbook]]). The tokens are main-resident (§2), so no kwtable move.
   Caveat from [[math-pack-subrom-tenant]]: **A is not preserved across CALSLT**; the
   RESUME leaves pass/return via RAM cells (`ERRRESUME`/`RESUMEPTR`), which suits a
   tenant well. The trap branch itself should stay **main-resident** (it's on the proven
   `raise_error` path and touches SP — do not route SP manipulation through CALSLT).

**Recommended plan:** measure lever 1 first (cheap); fund the ~40-50 B of main-resident
glue (trap branch + SAVSTK + SAVTXT + dispatch) from it if possible; put the bulkier
leaves (`ex_resume` + `scan_stmt_end` + `ex_on_error`, ~95 B) behind a **sub-ROM tenant**
(lever 3), reclaiming from lever 2 only if the glue still doesn't fit. **Decide after
measuring** — this is the one real architectural fork for sign-off (§9 Q1).

Lean 16 KB stays byte-identical regardless (all repack-only).

---

## 9. Open decisions (sign-off)

1. **Space lever (the real fork).** Recommend: main-resident trap branch + `SAVSTK` +
   `SAVTXT` + dispatch glue (funded by string/site reclaim, lever 1); `ex_resume` +
   `scan_stmt_end` + `ex_on_error` as a **sub-ROM tenant** (lever 3); `format.asm`
   eviction (lever 2) held as reserve. Confirm, or prefer an all-main plan gated on a
   bigger `format.asm` eviction.
2. **`scan_stmt_end` quote-awareness.** Recommend the **full quote-aware** scan (faithful
   `RESUME NEXT` across `PRINT "a:b"`). Accept the ~30 B, or take the minimal `exd_lp`-
   style scan with a **documented deviation** for `:`-in-string?
3. **`SAVTXT` capture point.** Recommend `exec_stmt` entry (per-statement, correct for
   mid-`:` RESUME). Confirm (vs. `rp_exec` line-granularity, which is cheaper but breaks
   mid-line RESUME).
4. **`ONELIN`/`ONEFLG` reset scope — pin empirically first (§7).** Confirm the packet
   treats this as a black-box pin (NOT the stale S2 spec §4 assumption), with the probe
   added to the acceptance harness. This is the load-bearing faithfulness item.
5. **Fold `ERROR 0`→ERR 5 arg-validation (S2a §3(g) deferral) into S2b?** Cheap (a
   0/≥table-size → `ld a,5` before `raise_error` in `ex_error`). Recommend **yes** if
   free; else keep deferred.

---

## 10. Acceptance & gates

New probe `basic_probe_error_trap.py` (repack + VG-8020 differential; observable-var +
screen). Oracle = the S1 §3 / S2 §6 transcript, plus:

* trap fires; `ERR`/`ERL` correct inside the handler (`TRAP 5  20`).
* `RESUME` (retry the erroring statement — observe it re-runs), `RESUME 0` (== RESUME),
  `RESUME NEXT` (skip), `RESUME <line>`.
* `RESUME NEXT` across a **mid-`:`-line** error (resumes the *next statement on the same
  line*, then the next line) — exercises `SAVTXT` + `scan_stmt_end`.
* `RESUME NEXT` where the erroring statement is the **last on its line** (→ next line).
* nested error in handler (no RESUME) → forced abort with the **inner** message.
* `ON ERROR GOTO 0` disables → falls back to the S1 abort (` in N`).
* `ON ERROR GOTO <undefined>` → `Undefined line number` at definition.
* `RESUME` with no active trap → `RESUME without error` (ERR 22).
* **§7 reset-scope cases:** `ON ERROR GOTO` then RUN/NEW/CLEAR then error — handler
  fires or aborts, matching VG-8020 (the load-bearing faithfulness pin).
* `ERROR n` for a representative code still prints the right message (S2a regression).

**Standing gates that must stay green** (S2b touches the shared error path, the run
loop's hot statement dispatch, and the tokeniser): `unit-test`, `array-acceptance` (150),
`input`/`string`/`float`/`math`-acceptance, `diskbasic-acceptance` (34 lean + 34 repack),
the tape battery, `repack-boot`, **lean `basic.rom` byte-identity**, and the S1/S2a
`error-acceptance` families A/B/C (untrapped abort + ` in N` + ERR/ERL persistence must
be unchanged when no handler is set). **DoD includes RUNNING these** (not just building
green — [[gate-during-implementation]]).

**Adversarial + empirical pass is mandatory** ([[error-handling-arc]] RECURRING LESSON,
~13×): after green, do a boot-per-case VG-8020 differential of the trap/RESUME/reset-
scope behaviour — the register/alloc/init-order class of bug (exactly what §7 guards) is
invisible to static reasoning and the green suite.

---

## 11. Clean-room

Original code; statement/function semantics + ERR-code numbering (21/22) from the
published MSX-BASIC language reference (allowed-source L110, grade B); the `RESUME`
token byte oracle-locked by black-box crunch on the VG-8020 ([[s2-error-token-pins]],
[[no-reference-rom-disasm]]); the `ON ERROR`/`RESUME`/reset-scope behaviour is black-box
behaviour capture. To record in `basic/PROVENANCE.md` on landing: "Phase 3: error
handling S2b — ON ERROR GOTO + trap branch + SAVSTK + RESUME family".
