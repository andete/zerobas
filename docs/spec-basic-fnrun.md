<!-- Copyright (c) 2026 Joost Yervante Damad — SPDX-License-Identifier: 0BSD -->

# `RUN` takes a string expression, and the decline it was filed under was false

**D-FNRUN, 2026-08-21**, on `main`, based on `227a1d3` (D-FNEXPR2). The last
filename verb in the family. `RUN A$` and `RUN A$+".DAT"` load and run the named
program; a bare `RUN`, `RUN :`, and `RUN <lineno>` are routed to the stored
program exactly as before. `make namspc-acceptance` **95/95 → 98/98**, deferred
5 — `n.runvar` and `n.runexpr` graduated and `n.runlinectl` 🟢 joined as a gated
control.

⚠️ **ONE REFERENCE for the disk rows** (National CF-3300). The two `t.*` token
rows and the two `n.runline*` rows have **both** references and agree.

---

## 1. The decline, and why it did not survive contact with an instrument

D-FNEXPR §2, D-FNEXPR2 §1.2 and `TODO.md` all named `RUN`'s bare-`RUN`
fallthrough as *"genuinely ambiguous with `RUN <lineno>`"* and priced it as a
probable **decline**. That is a claim about the TOKEN STREAM, and this probe has
an instrument for those — the `t.*` rows read the STORED LINE BYTES rather than
the screen:

| row | line | vg8020 | cf3300 | zb |
|---|---|---|---|---|
| `t.runnum` | `1 RUN 30` | `8a 20 0e 1e 00 00` | same | same |
| `t.runvar` | `1 RUN A$` | `8a 20 41 24 00` | same | same |

`$0E` is `LINENO_TOKEN`. [`basic/tokenise.inc`](../basic/tokenise.inc) arms
line-number mode on `RUN_TOKEN` and emits `$0E` for that form **and nothing
else**, so the two forms differ in their FIRST byte on all three machines. The
tokeniser had already done the work the decline was priced against
[[a-filed-blocker-can-name-the-wrong-obstacle]].

🔴 **And what the old dispatch did was not a refusal.** A non-quote fell to
`jp run_prog`, so `RUN A$` was not rejected — it was **eaten**, and the statement
restarted the program. Forever.

| row | statement | cf3300 | zb before | zb after |
|---|---|---|---|---|
| `n.runlit` 🟢 | `RUN"FCZ.DAT"` | `File not found` | `File not found` | `File not found` |
| `n.runvar` | `RUN A$` | `File not found` | **`<RUN SCROLLED OFF>`** | **`File not found`** ✅ |
| `n.runexpr` | `RUN A$+".DAT"` | `File not found` | **`<RUN SCROLLED OFF>`** | **`File not found`** ✅ |

🎯 **`<RUN SCROLLED OFF>` is a reading, and the fixture is what made it one.**
Both rows print a `[R]` marker before the `RUN`, so a restart loop fills the
screen and pushes the `RUN` anchor off the top. A silent infinite loop would
have read `<NO OUTPUT>` — indistinguishable from a machine that printed nothing,
which is the shape a diverging pair agrees on.

🔴 **`n.runexpr` is not decoration.** `n.runvar` alone is satisfied by "also
accept a bare string variable", which is exactly the cheap wrong fix D-FNEXPR's
`f.expr` was built to rule out at `OPEN`. One data point is not a rule.

---

## 2. The change

```
do_run:         xor  a / ld (CAS_VERIFY),a
                call skip_spaces        ; A = first non-space byte
                or   a       / jr z,dr_stored      ; bare RUN
                cp   COLON   / jr z,dr_stored      ; RUN : ...
                cp   LINENO_TOKEN / jr z,dr_stored ; RUN <lineno>
                call fname_expr         ; ...anything else is an EXPRESSION
                ld   de,dev_cas / call dev_cmp / jr z,dr_is_cas
                call parse_disk_fcb
                ld   hl,(FN_RESUME) / call pcr_noquote
                ...
dr_stored:      jp   run_prog
```

Both resumes (disk and `CAS:`) take the cursor from `FN_RESUME` and enter the
option tail at `pcr_noquote`, exactly as D-FNEXPR2's five verbs do.

### 2.1 ⚠️ The `RUN <lineno>` arm is RECOGNISED, not IMPLEMENTED

Dispatching on `$0E` routes that form to `run_prog`, which **ignores the line
number and restarts from the top** — precisely what the old code did. Both
references restart AT the named line:

| row | program | vg8020 | cf3300 | zb |
|---|---|---|---|---|
| `n.runline` | `10 GOTO 40` / `20 PRINT"[B]"` / `30 END` / `40 RUN 20` | `B` | `B` | **`<Syntax error>`** |
| `n.runlinectl` 🟢 | `10 PRINT"[B]"` / `20 END` | `B` | `B` | `B` |

The row exists **so this slice cannot be read as having fixed a form it merely
learned to recognise**, and the control exists because a silent loop and a
program that printed nothing read identically — only `n.runlinectl` says the
fixture can print at all. Both stay DEFERRED and the divergence is filed.

---

## 3. Cost

| wall | at `227a1d3` | after | delta |
|---|---|---|---|
| main page 1 | 50 B | **39 B** | **−11 B** |
| page-0 low | 22 B | 22 B | 0 |
| sub page 0 | 3299 B | 3299 B | 0 |
| sub page 1 | 1624 B | 1624 B | 0 |

`sub.rom` is byte-identical (`cf712906`) — a page-1 main edit leaves the
generated resident ABI alone.

The conversion itself is **+17 B**, which is *exactly* the price D-FNEXPR2 filed
by hand against this shape. **−6 B** came back from a span the fix killed (§4),
for a net 11.

---

## 4. 🔴 The gate could not see the 6 B the fix killed, because a COMMENT was seeding it

`parse_close_run`'s head — four instructions that consume a closing `"` out of
program text — had exactly four callers, all in `do_run` and `do_load`.
D-FNEXPR2 retired three; `do_run` was the fourth. The **sub-ROM** copy was
reported as a 6 B unreachable span the moment it went dead, one commit ago. The
resident copy was not.

The reason is in the gate's own seed set
([`tools/check_dead_code.py`](../tools/check_dead_code.py)):

```python
m_seeds = {'init'} | (set(m.nodes) & external_names(['sub', 'tools']))
```

and `external_names()` scrapes **every identifier** under those trees —
*including the ones inside comments*. Its docstring calls this "deliberately
coarse: over-seeding keeps a live routine alive, which is the safe direction."
It is the safe direction for false negatives on LIVE code. It also means:

> **A main-build span is invisible to the dead-code gate for as long as its
> label's name appears in prose anywhere under `sub/` or `tools/`.**

🎯 And the prose keeping this one alive was **the comment D-FNEXPR2 wrote one
commit earlier to explain why the head had been removed from the sub-ROM copy.**
Documenting a removal is what stopped the gate asking for the same removal in
the other build.

**Falsified, not reasoned about.** Mangling those three mentions drops the main
seed count 304 → 303 and the span is reported immediately:

```
  main: 1601 spans, 303 seeds -> 1 dead (+0 allowlisted)
FAIL: [main] parse_close_run   basic/bload.asm   0x6477 PAGE1  ~6 B
```

### 4.1 The class is 24 B wide today, and it is NOT this slice's to spend

Same instrument, run over the whole main build: **254** main labels are seeded
via `sub/`+`tools/`; **6** of those are unreachable from `init`'s own closure;
**2** are named *only* in comments, never in a code column. Mangling those two
mentions reports **three** dead spans and **24 B**:

```
  [main] str_heap_alloc   basic/str-engine.asm   0x281d LOW/P0  ~21 B
  [main] sha_oom          basic/str-engine.asm   0x2832 LOW/P0   ~2 B
  [main] ex_mid_stmt      basic/str-engine.asm   0x2c09 LOW/P0   ~1 B
```

⚠️ **Measured and RESTORED, not deleted.** 24 B in the page-0 LOW region (which
has 22 B free) is a real carve, and `str_heap_alloc` is not a name to delete on
the strength of a hole found sideways during a different slice — the string heap
moved to a sub tenant, so a leftover main copy is *plausible* and that is not the
same as proven. Filed in `TODO.md` with this measurement and with the
falsification that produced it.

---

## 5. The knives

| knife | cut | predicted |
|---|---|---|
| **K-FR1** | `cp LINENO_TOKEN` → `cp $0D` | no SCORED row moves (`RUN <lineno>` is red on its own account); the DEFERRED `n.runline` moves `<Syntax error>` → `<Type mismatch>` |
| **K-FR2** | `do_run`'s disk `ld hl,(FN_RESUME)` → `ld hl,(STRPTR)` | `n.runlit` red; `n.runvar` / `n.runexpr` move |
| **K-FR3** | `dr_cas_close`'s `ld hl,(FN_RESUME)` → `ld hl,(STRPTR)` | `castail`'s `RUN"CAS:x"` rows red |

🔴 **K-FR1 is a knife on an arm no SCORED row pins, and it says so up front.**
`RUN <lineno>` diverges before and after, so its rows are deferred and cannot
redden. What the knife can still do is move a deferred row's VALUE, which is a
reading — a deferred row is measured, just not scored.

**Measured. Two exact, one instrument finding.**

| knife | measured |
|---|---|
| **K-FR1** | no scored row moved; `n.runline` `<Syntax error>` → **`<Type mismatch>`** ✅ EXACT |
| **K-FR2** | `n.runlit` newly **RED**; `n.runvar` + `n.runexpr` → `<load error>` ✅ EXACT |
| **K-FR3** | `cas-run-hit` `ZQ9` → `<load-failed>` and `cas-run-hit-res` with it — the right cut, reported as **NOT MEASURED** (§5.1) |

### 5.1 🔴 K-FR3 cut its target and the battery refused to score it

`cas-run-hit` is a POSITIVE CONTROL in `castail`, so the moment the knife
reddened it the probe printed `33 printed, 0 scored — NOT MEASURED (a positive
control failed)` and exited 2. **A knife is supposed to break things; a battery
that treats any control failure as a broken instrument cannot measure one.**

🎯 `basic_probe_namspc.py` already carries the right rule and is the precedent —
*"ONLY A REFERENCE CAN SAY THE APPARATUS IS BROKEN. A control that fails on `zb`
is a finding and is scored like any other row."* One probe has it, the other does
not. Filed.

⚠️ **The reading survived only because the runner reads ROWS, not `rc`.** Scoring
on the exit code would have logged rc 2 — an instrument fault — as *"the knife
did nothing"*, which is precisely how 8 of 11 knives were once mis-scored.

---

## 6. E-FR1 — the experiment, and why its result is filed rather than shipped

`n.runline`'s face is `Syntax error`, which is **not** what "ignore the operand"
produces: ignoring it should restart the program and hang silently. So the arm
was doing something extra, and rather than write that down as a plausible
diagnosis, it was tested.

**Prediction, written before the build:** `do_run`'s stored-program exit is a
plain `jp run_prog` where every file arm beside it is `jp run_prog_top`
(`ld sp,(SAVSTK)` first). If the face is D-RUNTAIL's nested-run corruption, a
0-byte swap to `run_prog_top` turns it into an honest silent restart —
`<NO OUTPUT>`. If it stays `<Syntax error>`, the diagnosis is wrong.

**Measured: `<Syntax error>` → `<NO OUTPUT>`. Confirmed.** The `Syntax error`
is D-RUNTAIL's defect A at the one arm that slice did not convert — *guarding one
instance of a class is not guarding the class*, one more time.

⚠️ **AND IT IS NOT SHIPPED.** Neither state matches the reference (`B`), so there
is no measured reason to prefer a hang over a bogus error; and the same swap
moves bare `RUN` **inside** a program, a form no row drives. It belongs with the
real fix — starting execution AT the named line — where a `10 PRINT"[R]" / 20
RUN` row can be built beside it. Filed in `TODO.md` with this reading, so the
next slice inherits a measurement instead of a hunch.

