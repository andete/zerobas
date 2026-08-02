<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-RETLN — `RETURN <line>`: the statement half

Spec for the TODO item *"`RETURN <line>` IS NOT IMPLEMENTED"*, filed 2026-08-01
by D-LNREF. Measurement:
[`docs/retln-msx1-characterization.md`](retln-msx1-characterization.md) — 27 rows,
both references agreeing on every one, `--repeat 2`, echo-guarded on all three
sides.

Base: `6efafed`, tree clean, low **9 B** free, main page 1 **6 B** free, sub
page 0 **3910 B** free.

---

## 1. What is actually missing

D-LNREF already made the **crunch** correct: `40 RETURN 30` stores
`<8E> <0E><1E><00>` byte-identically on all three sides. `ex_return`
([`basic/program.asm:1089`](../basic/program.asm:1089)) never advances `HL` past
the `RETURN` token, so the `$0E` sits in the token stream unread.

Unlike the four editor verbs D-KWGAP4 re-filed as blocked, `RETURN` **already has
a `stmt_table` row and a handler**. Verified at `6efafed`: `ex_return` is
dispatched from `stmt_table` ([`basic/interp.asm:214`](../basic/interp.asm:214))
and lives at `$7897`, main-ROM page 1. So this is an edit to an existing handler
— no new dispatch row, and none of the 3 B/row page-1 cost D-KWGAP4's knife K5
measured.

## 2. The rules to implement

From the characterization's §0, unchanged:

* **R-T1** — empty GOSUB stack → `ERR 3`, checked **before** the argument is
  parsed or resolved.
* **R-T2** — `$0E <line>` pops **exactly one** frame and branches to that line
  instead of resuming at the frame's saved resume point.
* **R-T3** — the target line not existing → `ERR 8`, with the frame **already
  popped**. `RETURN 0` is an ordinary failing lookup, no zero special case.
* **R-T4** — an argument that is not `$0E` and not a terminator (`<EOL>` or `:`)
  → `ERR 2`, **also with the frame already popped** (`lnrt-varp`).
* **R-T5** — every error is filed against the `RETURN`'s **own** line.

R-T3 + R-T4 + R-T5 together are the whole design: *pop the frame, then hand the
cursor to `GOTO`'s existing parser* — which branches on `$0E`, raises `ERR 2` on
anything else, and touches `CURLINE` in neither case.

### 2.1 What this does NOT change

Bare `RETURN` — the pop, the `CURLINE`/`RESUMEPTR` restore, the `RESUMEFLAG`
mid-line resume — is byte-for-byte the code that is there today, reached by
falling into it. The T1 interrupt-trap re-enable (`TRAPSVC`/`trap_return_check`)
stays first and is untouched. `set_resumeflag_ret`, the zero-cost label
`ex_resume`'s `res_setptr` jumps into, keeps its address contract.

## 3. Funding — a 160 B carve, measured, not estimated

The change needs more than the 6 B page 1 has. The carve is a **tree-wide
dead-instruction sweep** (signed off 2026-08-02; the first draft of this spec
proposed only the two files this slice edits, and the wider sweep was taken
instead):

`skip_spaces` ([`basic/interp.asm:574`](../basic/interp.asm:574)) is
`ld a,(hl) / cp ' ' / ret nz / inc hl / jr skip_spaces` — it returns **only** via
`ret nz`, so `A = (hl)` on every exit, always. Every `call skip_spaces`
immediately followed by `ld a,(hl)` therefore reloads a register that already
holds that value. There are **160** such sites across 22 files
(`basic/graphics.asm` 27 · `basic/files.asm` 26 · `basic/program.asm` 19 ·
`basic/save.asm` 15 · `basic/print.asm` 9 · `basic/screen.asm` 9 · …), each
exactly 1 dead byte.

Behaviour-neutral in both directions: `ld a,(hl)` sets no flags, so the flags
`skip_spaces` left (`NZ` from its own `cp ' '`) are preserved either way. None of
the 160 has a label between the `call` and the `ld` — the matcher requires the two
to be **adjacent lines**, and a jump target would need a label line between them —
so none is a jump target.

**Measured** (clean `make basic-reloc`):

| | low free | page 1 free |
|---|---|---|
| `6efafed` | 9 B | **6 B** |
| + the two-file carve (25 B), measured first | 9 B | 31 B |
| + the full 160 B carve | **23 B** | **149 B** |
| + `ex_return` (§4) | 23 B | **124 B** |

so the change itself is **+25 B**, exactly as specced, and both walls end far
wider than they started.

🔴 **The dead-code gate reports 0 dead and is right.** These are *reachable*
instructions computing a value already held, not unreachable code, so
`deadcode-gate` is structurally blind to them — and was, while 160 B sat there
through every slice that ever wrote "page 1 has 6 B free". ⚠️ **Every byte-budget
claim in this repo before 2026-08-02 was measured against a wall with 143 B of
slack in it**, including D-KWGAP4's "four rows are 12 B against 6 B and do not
fit". Whether a gate should exist for the *shape* is filed in `TODO.md`.

⚠️ `sub.rom` **moves** because of this carve (shared and sub-side bodies are among
the 22 files). That is the carve's doing, not `ex_return`'s — §4 is main-ROM only.
Hashes are recorded, not asserted equal.

## 4. The change — `ex_return`, `basic/program.asm`

```
ex_return:
                ld      a,(TRAPSVC)         ; unchanged: T1 trap re-enable first
                or      a
                call    nz,trap_return_check
                push    hl                  ; the token cursor, across the check
                ld      hl,(GSP)            ; R-T1: the empty-stack check comes
                ld      de,GOSUB_STK        ; FIRST -- ERR 3 beats both ERR 2
                or      a                   ; (lnrt-nogosbad) and ERR 8
                sbc     hl,de               ; (lnrt-nogosund)
                jp      z,ex_ret_under
                pop     hl
                inc     hl                  ; past the RETURN token
                call    skip_spaces         ; A = (hl)
                or      a
                jr      z,ret_frame_bare    ; <EOL> -> bare RETURN
                cp      COLON
                jr      z,ret_frame_bare    ; ':'   -> bare RETURN (lnrt-bcolon)
                ; R-T2/R-T3/R-T4: pop the frame, THEN parse the argument as a
                ; branch target. Measured: BOTH failure modes pop first
                ; (lnrt-undefp / lnrt-varp read ERR 3 from a handler's own bare
                ; RETURN), and neither touches CURLINE, so ERL reads the
                ; RETURN's own line (lnrt-erlund / lnrt-erlvar).
                push    hl
                call    ret_frame           ; GSP -= 4, contents discarded
                pop     hl
                jp      ex_goto_at          ; $0E -> branch; anything else ERR 2
ret_frame_bare:
                call    ret_frame
                ld      (CURLINE),de        ; unchanged bare-RETURN tail
                ld      (RESUMEPTR),bc
set_resumeflag_ret:                          ; unchanged (ex_resume jumps here)
                ld      a,1
                ld      (RESUMEFLAG),a
                ret
ret_frame:                                   ; the existing pop, now a subroutine:
                ld      hl,(GSP)             ; DE = saved CURLINE, BC = resume ptr
                dec     hl                   ; (body verbatim, + `ret`)
                ...
                ld      (GSP),hl
                ret
```

⚠️ **The stray stack entry on the `ex_ret_under` path is deliberate and safe.**
`jp z,ex_ret_under` leaves the pushed `HL` behind, and `ex_ret_under` →
`raise_error`. Both of that routine's exits reset `SP` from `SAVSTK` — the trap
arm does `ld sp,(SAVSTK)` ([`basic/interp.asm:829`](../basic/interp.asm:829)) and
the abort arm's `fre_abort_low` does the same as its first act. Paying a `pop hl`
there would be a byte for nothing; **the row `lnrt-leak` (§6.1) is what proves
it**, not this paragraph.

⚠️ **`ex_goto_at` re-calls `skip_spaces`.** Harmless — `HL` is already past the
blanks and `A = (hl)` is non-blank, so it returns immediately. Reusing it rather
than open-coding the `$0E` read is what makes R-T4 free: its own
`jp nz,stmt_error` **is** the `ERR 2`.

Expected cost **+25 B**, all main-ROM page 1, against the 31 B the carve bought.
`basic-reloc.rom` and `zerobas-main-eu.rom` both move (recorded as hashes, not
asserted equal); `sub.rom` must be **byte-identical** — nothing here is sub-side.

## 5. Rows and pins

* The `lnrt` battery (**27 rows**) is added to
  [`probes/basic/basic_probe_lnblank.py`](../probes/basic/basic_probe_lnblank.py)
  as SAY_ONLY, and to the say gate's default selection
  (`ONLY=lnrd-,kwgd-` → `lnrd-,kwgd-,lnrt-`). It gates 12 → **39 rows**.
* **`lnrd-return`'s `KNOWN_DIVERGE` pin RETIRES.** D-LNREF pinned it to zerobas'
  exact ` 20  0 ` precisely so the day a handler landed the gate would say so.
  It lands here, the pin stopped matching — the gate reported *"allowlisted as
  divergent but the row now AGREES — retire the entry"* — and the **entry was
  DELETED**, not edited to a new value. Seventh cohort to leave that way, none
  has rotted.
* **26 of the 27 `lnrt` rows agree with both references** after the change, with
  no pin. The 27th is `lnrt-forret`, which is not about `RETURN <line>` at all:
  it is the FOR-frame divergence the apparatus turned up in passing (§6.1,
  characterization §5), pinned to zerobas' exact ` 103  0  4 ` with its own green
  control `lnrt-forerr` beside it and a filed retirement path in `TODO.md`.
* Say-gate pin count therefore **3 → 3**: `lnrd-return` out, `lnrt-forret` in.
  That is not a wash — the retiring pin recorded a missing STATEMENT that now
  exists, and the new one records an architectural divergence that was invisible
  before this slice's apparatus existed.
* `lnblank-acceptance` stays **521/521** — SAY_ONLY rows are outside its
  selection — and its allowlist stays **EMPTY**.

## 6. Knives — each with a predicted RED set **and** predicted GREEN survivors

Reverted against **the build each one cut**, never with `git checkout`, and
restored with `shutil.copy` + `os.utime` (never `copy2` — it preserves mtime,
`make` skips the rebuild, and the check then hashes the stale knifed ROM).

⚠️ **Run BY HAND, and §6.3 is why.** Each cut is applied to the landed source,
built, and read with a scoped `--say` run; the source is then restored from a
copy taken before the cuts (never `git checkout`, which restores HEAD — the
*unfixed* tree — and would silently revert the slice). After the last restore a
clean rebuild returns `basic-reloc.rom` to `8f7f5cd1e98d…`, the pre-knife hash,
which is what says the restores were sound.

```bash
python3 probes/basic/basic_probe_lnblank.py --say --repeat 1 --sides zb --only <the rows below>
```

| | cut | predicted RED | measured | predicted GREEN (the control) | measured |
|---|---|---|---|---|---|
| **K1** ✅ | `nop` out `jr z,ret_frame_bare` on the `COLON` test | `lnrt-bcolon` | **moved** | `lnrt-ctl`, `lnrt-line` | **held** |
| **K2** ✅ | `nop` out `call ret_frame` on the branch path | `lnrt-pop` ` 30  3 `→` 50  0 ` · `lnrt-undefp` ` 50  3 `→` 53  8 ` · `lnrt-varp` ` 50  3 `→` 53  2 ` | **all three, to exactly the predicted values** | `lnrt-line`, `lnrt-back` | **held** — the branch still works |
| **K3** ✅ | let `ld (CURLINE),de` run on the branch path | `lnrt-erlund` ` 40  8 `→` 20  8 ` · `lnrt-erlvar` ` 40  2 `→` 20  2 ` | **both, filed against the caller** | `lnrt-undef` ` 0  8 `, `lnrt-var` ` 0  2 `, `lnrt-line` ` 30  0 ` | **held, byte-identical** |
| **K5** ✅ | break the empty-stack check (`GOSUB_STK` → `GSP`) | `lnrt-nogosctl` ` 0  3 `→` 0  2 ` · `lnrt-nogosbad` ` 0  3 `→` 0  2 ` | **both** | `lnrt-ctl`, `lnrt-line` | **held** |

🎯 **K3 is the one that justifies its own rows existing.** `lnrt-undef` and
`lnrt-var` read *identically* on the correct build and on the K3 build — ` 0  8 `
and ` 0  2 ` either way. The defect is invisible to every row that reads only
where control went; only `ERL` can see it. A slice without those two rows would
have shipped K3's build believing it correct.

🎯 **K2 is the one that separates R-T2 from R-T3.** It leaves `RETURN 30`
branching to line 30 exactly as it should — `lnrt-line` and `lnrt-back` do not
move — and reddens only the three rows that read the **stack**.

### 6.1 K4 is a ROW, not a knife — `lnrt-leak`

§4's claim that the stray stack entry on the `ex_ret_under` path is harmless is a
*justification*, and a knife cannot test it: adding a `pop hl` there makes
everything stay green, which proves nothing. Two stray bytes are invisible; **400
of them are not**:

```
10 ON ERROR GOTO 50 : 20 FOR I=1 TO 200:RETURN:NEXT : 30 A=A+3:END : 50 A=A+1:RESUME NEXT
```

200 `RETURN`-without-`GOSUB` traps. If `raise_error` did not reset `SP` from
`SAVSTK`, this does not read a different number — it takes the machine down.
Oracle-locked on both references like every other row.

### 6.2 K6 — the carve is behaviour-neutral

The 160 B carve's byte effect is measured directly in §3's table; its behaviour
half is the full corpus (§7), which exercises every one of the 22 files it
touched.

### 6.3 🔴 The corpus caught a regression the 28-row battery structurally could not

`trap_return_check` ([`basic/traps.asm:400`](../basic/traps.asm:400)) **destroys
`HL` unconditionally** — `ld l,a / ld h,0 / add hl,hl / …`. Before this slice
that was free: `ex_return`'s very next act was `ld hl,(GSP)`, so `HL` was dead
across the call. Making the token cursor live across it is exactly the clobber
contract a refactor inherits without being told
([[refactor-inherits-clobber-contracts]]).

The first implementation put `push hl` **after** the trap check, so on the
`TRAPSVC ≠ 0` path it saved garbage and then parsed the argument out of it.
`make stop-trap-acceptance` failed on `C2_press_in_handler_latches`
(`flag=1`, reference `2`). Moving the `push` above the check fixes it at **zero
byte cost** — page-1 free is 124 B either way.

⚠️ **No `lnrt` row could have caught this, and that is the lesson.** All 28
`RETURN` out of ordinary code, so `TRAPSVC` is 0 in every one of them and the
clobber never fires. The battery was built around the *argument*; the defect was
in the *register contract on a path the argument never reaches*. A slice that had
trusted its own purpose-built battery and skipped the corpus would have shipped
it — which is why the corpus is run in full for any `basic/` change rather than
scoped to what the change "obviously" touches.

### 6.4 🔴 The knife RUNNER produced false negatives on every cut after the first

Recorded because it is the third fault in this family (after D-KWGAP4's two,
[`spec-basic-kwgap4.md`](spec-basic-kwgap4.md) §7.0) and the most dangerous
shape yet: **it reported the change as unfalsifiable and the change was fine.**

A first version scored `moved` by iterating the *knifed* gate's rows, so a gate
that returned nothing at all produced an empty `moved` set — indistinguishable
from "the knife changed nothing". Fixed to iterate the union and to hard-fail on
a missing row. It then still reported K2, K3 and K5 as moving **nothing**, with
all rows present and the knifed ROM verified different from the baseline.

Re-running the identical cuts by hand moved **every** predicted row, to the exact
predicted values. The runner was deleted rather than shipped: a falsification
tool that reports "your knives prove nothing" when the knives in fact prove
everything is worse than no tool, because the honest response to it is to weaken
the claim. ⚠️ **The general lesson is the one that keeps recurring here — an
apparatus that fails toward "nothing to see" cannot gate.** The root cause was
not identified within the slice; that is stated rather than papered over.

## 7. Gates — measured on the shipped bytes

⚠️ **Re-run in full after the §6.3 fix.** The first pass gated the pre-fix ROM;
the `push hl` move changed `basic-reloc.rom`, so every suite below was run again
against the bytes that actually ship. A clean rebuild reproduces them exactly:

| artifact | sha256 |
|---|---|
| `build/basic-reloc.rom` | `555ecbb6efa966d6…` |
| `build/zerobas-main-eu.rom` | `5d65784c0f3ad5d6…` |
| `build/sub.rom` | `7808021121263b1a…` |

Walls: low **23 B** free (was 9), main page 1 **124 B** free (was 6).

| gate | result |
|---|---|
| `unit-test` | **55/55** |
| dead-code, both builds | **0 dead**, allowlist canary still verified |
| `lnblank-acceptance` `REPEAT=2` | **521/521**, allowlist **EMPTY** |
| `lnblank-say-acceptance` | **40/40**, 3 pinned |
| `lnblank-echo` | every gating payload verbatim on every side |
| `logicops-acceptance` | **193/193** |
| `float-acceptance` | exit 0 |
| `array-acceptance` | **149/151** — `ifc.instr.zero`, `ifc.instr.neg`, the only two FAILs in the log |
| `arrdim` / `clearpool` | **73/73** / **52/52** |
| `badfnum` / `lof` / `chancost-characterize` | **93** / **45** / **53** |
| `linemax-acceptance` | **60/60** |
| `error-trap-acceptance` | exit 0 |
| `abort-acceptance` | **49/49** |
| `stop-` / `strig-` / `key-trap-acceptance` | **ALL PASS** (`stop-trap` is what caught §6.3) |
| `diskbasic` / `bdos` / `fat-error` | **34/34** / **12/12** / **8/8** |
| `sysvarsweep` | exit 0, controls green, `C-REPRO-2` still `00->08` |

⚠️ `abort-acceptance` and `error-trap-acceptance` are named in the corpus because
`RETURN` touches the GOSUB frame and the mid-line resume path the abort chain
returns into ([[abort-chain-returns-into-caller]]) — and because the carve
touches `basic/interp.asm`'s own error sites.

Standing and **not** caused by this work: `tools/audit_citations.py` reports 2
gating findings in `basic/fat.asm` and `basic/missing.asm`.
