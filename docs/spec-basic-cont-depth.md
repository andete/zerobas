<!-- Copyright (c) 2026 Joost Yervante Damad -->
<!-- SPDX-License-Identifier: 0BSD -->

# D-CONTD — `CONT` re-enters the run loop at the wrong stack depth

**Status: ✅ LANDED 2026-07-29. Signed off before implementation; built,
gated, falsified against two rejected builds.**
Filed defect: [`TODO.md`](../TODO.md), "`CONT` that runs off the end of the
program aborts with a nonexistent line number". One of three characterized
run-loop-exit defects; **this slice builds only this one**, and it is the
ordering prerequisite for the other two (§7).

Same class as [`docs/spec-basic-abort-depth.md`](spec-basic-abort-depth.md)
(D-CUR-D, `4d35b6d`): **a `ret` that only unwinds correctly at one depth.**

---

## 1. The defect

```
10 STOP : 20 B=1 : 30 PRINT"R<";1;">"
RUN            -> Break in 10
CONT           -> reference: R< 1 >          then Ok
                  zerobas:   R< 1 >          then `Illegal function call in 3346`
```

Line 3346 does not exist. The right answer is printed and the interpreter *then*
derails — which is why a marker-only readout scores this row as agreement, and
why it was found by a CONTROL row of the D-ONELIN battery rather than by anything
aimed at `CONT`. Verified **pre-existing at `6ac2285`** against a parked pre-fix
build, not assumed.

---

## 2. The mechanism — traced, and the `END` path is clean BY LUCK

There are two ways into the run loop, and only one of them is at the right depth:

| entry | how | depth on entry |
|---|---|---|
| `run_prog` (`RUN`) | `call`ed from `dl_run`; its exit `ret` returns to the REPL | REPL |
| `dl_cmd` (a typed line) | `ld (SAVSTK),sp` then **`jp rp_exec`** — its own comment says "unwinds to the REPL at end of line" | REPL |
| **`ex_cont`** | reached as a STATEMENT, i.e. from inside the loop's own `call exec`, then a bare **`jp rp_lp`** | **statement depth** ❌ |

So `ex_cont` starts a fresh loop iteration with a stale `call exec` return frame
underneath it. When the resumed run stops, the loop's exit `ret` does not reach
the REPL — it lands **back inside the loop body**, at the instruction after
`call exec`, which immediately reads `ENDFLAG`:

* **exit via `END`** → `ENDFLAG`=1 → `ret nz` fires again straight away and the
  second `ret` does reach the REPL. **Clean by luck** — one stray re-entry,
  absorbed by a flag that happened to still be set.
* **exit via the `$0000` link** → `ENDFLAG`=0 → falls through past `RESUMEFLAG`
  and `GOTOFLAG` to the next-line advance, with `HL` still pointing at the end
  marker. It walks a "line" out of whatever follows the program, executes it, and
  reports the failure in run mode as `Illegal function call in <the word after
  the marker>` = 3346.

### 2.1 What was measured, not reasoned

⚠️ A competing hypothesis — *the `END` exit derails too, onto a benign
terminator byte* — was **REFUTED**: `40 END:PRINT"R<";9;">"` does **not** run its
second statement after a `CONT` (`d_cont_after_end`, agrees on both machines). If
the stray re-entry resumed statement parsing at `HL`, it would have. It does not;
it re-enters at the loop's flag checks. That distinction is the whole mechanism,
and only measuring separated the two.

Controls that pin the entry, not the exit: `x_run_tail` (plain `RUN` off the same
end — clean) and `x_cont_goto` (a direct `GOTO` into the program, i.e. the
`dl_cmd` path — clean). The bug is in how `CONT` *enters*, not in the `$0000`
link itself.

---

## 3. The fix — 4 bytes, one instruction

```asm
ex_cont:
        ...
        ld      a,1
        ld      (RESUMEFLAG),a      ; resume mid-line at CONTPTR
        ld      sp,(SAVSTK)         ; D-CONTD: re-enter the loop at the depth its
        jp      rp_lp               ; exit `ret` unwinds from -- dl_cmd's anchor
```

`dl_cmd` writes `SAVSTK` for **the `CONT` line itself**, immediately before
`jp rp_exec` — so at `ex_cont` it is fresh and holds exactly the SP the loop's
exit `ret` expects. This is the same anchor `raise_error`'s trap branch already
uses (`ld sp,(SAVSTK)`), reached the same way, which is why no new sysvar and no
new invariant is introduced: the slice makes `ex_cont` obey a contract the file
already documents rather than inventing one.

* **Cost:** `ld sp,(nn)` = **4 B**, page 1 (11 B free after D-ONELIN).
  Low region untouched — it is at 0 B free.
* **Gating:** `IF ROM_BASE < $4000`. `basic/program.asm` is in BOTH builds, and
  the lean build's `dl_cmd` ends `jp exec` (statement walk only) and never writes
  `SAVSTK`, so the anchor does not exist there. `tools/check_reloc.py`'s
  byte-identity check is the gate on that, not this paragraph.
* **Discarding the rest of the typed line is CORRECT, not a side effect.**
  Resetting SP abandons `exec`'s frame, so anything after `CONT` on the typed
  line is dropped. **Measured: the reference does the same** — `CONT:PRINT…`
  prints nothing extra on either machine (`cont_rest_of_line`). Had the
  reference run it, this fix would have been wrong.
* **`GOSUB`/`FOR` frames are unaffected**: they live in their own RAM stacks
  (`GSP`/`FSP`), not the Z80 stack. Measured, not assumed — `cont_gosub_live`
  (a `CONT` resumed with a live `GOSUB` frame, whose `RETURN` must still work)
  and `cont_for_live` agree on both machines today and must stay agreeing.

---

## 4. The gate — `cont_*` rows in `abort-acceptance`

Home: [`probes/basic/basic_probe_abort_depth.py`](../probes/basic/basic_probe_abort_depth.py),
not the error-trap probe. It is the same defect class, it already uses the
echo-anchored tail readout (the only readout that can see "right answer, then
garbage"), it is boot-per-case, and it already case-folds — which is what keeps
`Break` vs `break` from reading as a divergence.

⚠️ **NOT ONE OF THESE ROWS MAY ARM `ON ERROR`** — that file's standing rule. A
handler would select `raise_error`'s trap branch, which resets SP and would mask
exactly the depth bug under test.

| row | asks |
|---|---|
| `cont_falloff` | the defect: resumed run off the `$0000` link — tail must be the marker ALONE |
| `cont_end` | the lucky-clean path must STAY clean |
| `cont_after_end_stmt` | **must NOT**: `40 END:PRINT…` — the statement after `END` must not run |
| `cont_gosub_live` | **must NOT break**: a live `GOSUB` frame survives; its `RETURN` works |
| `cont_for_live` | **must NOT break**: a live `FOR` survives; `NEXT` loops |
| `cont_rest_of_line` | **must NOT**: `CONT:PRINT…` drops the rest of the typed line |
| `cont_ctl_run` | CONTROL: the same exit reached by plain `RUN` is clean |
| `cont_ctl_goto` | CONTROL: the same exit reached by a direct `GOTO` is clean |

Six of the eight are "must not change" rows. That is deliberate: the fix
*discards a stack frame*, so the risk it carries is not "does the symptom go
away" but "what else was living on that frame".

### 4.1 Falsification — AS-RUN, two builds

| build | result |
|---|---|
| **without the instruction** (the pre-fix build) | **7/8 — `cont_falloff` RED**, the other seven green. The gate moves when the code under test is removed. |
| **`ld (SAVSTK),sp`** instead of `ld sp,(SAVSTK)` — anchor *here* rather than restore | **7/8 — `cont_falloff` still RED.** The two instructions differ by one character; only one of them is the fix. Anchoring makes a trap raised *during* the resumed run unwind correctly, and does nothing at all for the exit depth. |

With the fix: **8/8**, and `make abort-acceptance` is **31/31** overall.

### 4.2 Wall accounting — AS-BUILT

| | low region | page 1 |
|---|---|---|
| after D-ONELIN (`a60f386`) | 0 B free | 11 B free |
| `ex_cont` gains `ld sp,(SAVSTK)` | — | **+4 B** |
| **AS-BUILT** | **0 B free** | **7 B free** |

Lean `basic.rom` byte-identical (`check_reloc.py`), as the `IF ROM_BASE < $4000`
gate requires.

---

## 5. Regression surface — AS-RUN

All gates in §6 were RUN, not assumed. `make abort-acceptance` **31/31**;
`make error-trap-acceptance` ALL PASS — including `oneflg_suspend_resume`, which
resumes *inside a handler* across a `STOP` and therefore drives `CONT` through
this exact path; `make stop-trap-acceptance` ALL PASS. `array-acceptance` is
149/151 on the two standing `ifc.instr.*` capitalisation rows, confirmed BY NAME.

Nothing else was living on the discarded frame — the four "must not change" rows
(`cont_after_end_stmt`, `cont_gosub_live`, `cont_for_live`, `cont_rest_of_line`)
were green before the fix and are green after it.

---

## 6. Gates

`make unit-test` · `make abort-acceptance` · `make error-trap-acceptance` ·
`make stop-trap-acceptance` · `make linemax-acceptance` · `make arrdim-acceptance` ·
`make clearpool-acceptance` · `make diskbasic-acceptance` · `make bdos-acceptance` ·
`make fat-error-acceptance` · `make chancost-characterize` (39 cases / 1 filed) ·
`make array-acceptance` (149/151, standing `ifc.instr.*` by name) ·
clean `make basic-reloc` (lean byte-identical).

---

## 7. Explicitly NOT in this slice

The two siblings, both characterized in [`TODO.md`](../TODO.md) and both left
open:

1. **ERR 21 `No RESUME` is never raised.**
2. **`CONT` after `END`/fall-off must resume** (the reference records a resume
   point after *every* run stop, not just `STOP`).

⚠️ **ORDERING.** (2) makes the `END` and fall-off exits reachable by `CONT` in
new ways, and (1) adds a raise on the `$0000`-link exit — the very path whose
depth is broken here. Building either of them first would have converted this
slice's *lucky-clean* `END` path into a live derail, and the resulting garbage
would have looked like a bug in the new feature. **This one goes first.**

---

## 8. Sign-off — ANSWERED 2026-07-29, before implementation

1. **`ld sp,(SAVSTK)` at `ex_cont`** — 4 B, page 1, gated `IF ROM_BASE < $4000`.
   ✅ Signed off. Rejected: gating it harder before building (the must-not-change
   rows were already written and already green), and making the `$0000`-link exit
   robust to any depth (larger, touches the hot run loop instead of a cold
   statement handler, and does not restore the documented one-anchor contract).

## 9. Clean-room

No reference-ROM disassembly. §2's mechanism is traced through zerobas's OWN
source; the reference appears only as black-box screen output through the
KEYBUF-injection REPL driver.
