# D-ENDIFWALK — a walk that stops at `ENDIF` was hiding an 11 B dead routine

**2026-08-28.** Measures the class D-DUPSPAN filed on 2026-08-22 (§2.1), finds it
is **wider than the item names**, and takes the one consequence that is
verifiable on its own: **11 B of main page 1**, from a routine `make deadcode`
could not see.

## 1. The class is 68 pairs, and `ENDIF` is under half of it

`check_dead_code._last_code` walks a span backwards for its last code line,
skipping blanks and bare labels — but **not assembler directives**. So a span
ending on `ENDIF` gets asked "is `endif` a terminator?", and `_is_terminator`
correctly answers no, because it is not an instruction at all. The result is a
**fallthrough edge that should not exist**.

Measured over both builds ([`scratchpad/endif_walk_sweep.py`](../scratchpad/endif_walk_sweep.py)):

| build | span pairs with a last code line | ending on a DIRECTIVE |
|---|---|---|
| main | 1476 | **51** |
| sub | 1485 | **17** |

**68 total** — `endif` **32**, `if` **22**, `include` **13**, `else` **1**.
The item named `ENDIF`; the other **36** are the same defect unnamed, and
`include` turns out to be the one that mattered.

## 2. Which direction it fails in

The item says *"this one over-reported and cost nothing"*, which is true of the
D-DUPSPAN fallthrough survey it was found in — there a phantom edge only made a
collapse look more expensive than it was.

🔴 **In `check_dead_code` it fails the other way.** A phantom fallthrough edge
makes the next label *reachable*, so the failure mode is **dead code that never
gets reported** — a gate going quiet, not one crying wolf. And `make deadcode`'s
sweep also runs as a **hard gate inside `make basic-reloc`**, so anything it
cannot see is invisible to the build too.

Corrected verdicts ([`scratchpad/endif_walk_verdict.py`](../scratchpad/endif_walk_verdict.py)),
resolving `include` recursively and requiring **every arm** of an `IF/ELSE/ENDIF`
to terminate: **30 verdict changes, 18 agree, 20 undecidable**. All 30 are
phantom edges. The 20 undecidable are conditionals whose opening `IF` lies in a
*previous* span, so a per-span walk cannot see the arms — those keep their edge,
because a guessed `True` deletes a real edge while a guessed `False` only keeps a
phantom one.

## 3. What it was hiding

With only the **`include`** correction applied — the unambiguous third of the
class — the sweep reports 4 spans it previously could not:

| span | | verdict |
|---|---|---|
| `skip_to_eol` `basic/interp.asm` | 9 B page 1 | **genuinely dead in main** |
| `ste_done` `basic/interp.asm` | 2 B page 1 | **genuinely dead in main** |
| `fat_delete` `basic/fat.asm` | ? | not yet adjudicated |
| `__MEAS_SUB_P1_END` `sub/sub.asm` | — | a measurement label, reached by construction |

### 3.1 `skip_to_eol` / `ste_done` — verified, and deleted

It survived the **G4 line-editor eviction as a second copy**. `sub/lineedit.asm:738`
defines its own `skip_to_eol`/`ste_done` and holds **all eight** real callers
(`:157 :329 :566 :650 :743 :941 :1013 :1100`). Walking `basic/main.asm`'s entire
50-file closure finds **exactly one** mention of the name:

```
basic/interp.asm:1675: jr      skip_to_eol
```

— which was **inside the routine's own body**. A self-loop is not a caller.

⚠️ **This is NOT the `IF SUB_BUILD` shape** that `check_dead_code`'s header warns
about (fix 4, `disk_putword`): that is *one* definition in a shared body `.inc`,
live in the other build, where "deleting it broke the build". This is *two*
definitions in two files, and the sub build **does not include `basic/interp.asm`
at all** — checked, not assumed. So deleting main's copy takes nothing from sub.

**Measured: main page-1 free 94 B → 105 B.** Page-0 low unchanged at 39 B.

🎯 **Why it hid for so long is the whole point.** `tok_skip_to`'s span ends on
`include "basic/tokskip-body.inc"`, and that included file's real last instruction
is `jr tsk_data` — unconditional. The walk read the *directive* instead and
invented a fallthrough into `skip_to_eol`, keeping an 11 B dead routine
"reachable" for as long as it existed.

## 4. Both remaining spans adjudicated, and the walk fixed

### 4.1 `fat_delete` — the same shape again, another 5 B

`basic/fat.asm` is in the **main** closure only; `basic/fat-delete-body.inc` and
both callers (`sub/dirverb.asm:128`, `sub/fatprim.asm:205`) are in the **sub**
closure only. Main's copy is the thirteenth *uniform resident shim*
(`ld a,DISKOP_SEL_FAT_DELETE / jp fatprim_bounce`) — and it had no caller.

The twelve shims above it are called by name from `basic/files.asm`
(`call fat_io_open`, `call fat_rand_open`, …). This one is not, because **main's
KILL does not use the primitive layer at all**: `files.asm` goes
`ld a,DISKOP_SEL_KILL / call subrom_call`, and its own comment says the tenant is
*"calling `fat_delete` sub-locally"*. The shim outlived that eviction.

⚠️ **Checked rather than assumed, because a resident shim is exactly the shape
that can be reached by ADDRESS rather than by name.** It is in no resident-ABI
list and no dispatch table, and `basic/main.asm`'s whole closure contains **one**
mention of the name — the definition itself.

**Main page-1 free 105 B → 110 B.**

### 4.2 `__MEAS_SUB_P1_END` — true and useless

`__MEAS_SUB_P1_END:` is followed by `ds $8000 - $, $FF`. It exists to be **read
from the sym file** by `check_sub_walls.py`; nothing jumps to it, by design. It
was only ever kept out of the dead set by an incoming fallthrough edge, so
correcting the walk made it reportable — as a finding that is true and useless.

Fix (9): **a span whose only code line is a `ds` emits no instructions and cannot
be unreachable code.** Deliberately narrow, and proved narrow rather than
asserted — a `db` table is data a reference can genuinely go missing from and
stays reportable:

| span content | skipped? |
|---|---|
| `ds $8000 - $, $FF` | **yes** |
| `db 1,2,3` | no |
| `ds 4` + `ret` | no |
| empty | no |
| `ret` | no |

The skip **prints what it skipped**. A silently dropped finding is the shape this
gate exists to remove.

### 4.3 The walk fix, scoped

`_last_code` now resolves `include "f"` recursively to the included file's last
code line; an unresolvable include is left unchanged, keeping its edge.

⚠️ **Only `include` (13 of the 68), and that is a scope decision.** Deciding an
`IF/ELSE/ENDIF` needs every arm to terminate, and **20 of those conditionals open
in a PREVIOUS span**, where a per-span walk cannot see the arms at all. That needs
file-level context and stays open.

**Falsification:** `--blind` still exits non-zero — the allowlist canary fires, so
the sweep has not gone quiet. Both allowlist entries are still detected as dead.
`main: 0 dead`, `sub: 0 dead (+2 allowlisted)`.

## 5. Total

**16 B of main page 1** recovered from code no gate could see: 94 B → **110 B**.

## 6. What is still open

**The `IF`/`ELSE`/`ENDIF` half — 55 of the 68 pairs.** Deciding one needs every
arm to terminate, and the corrected walk marks **20 of them undecidable** because
the opening `IF` lies in a *previous* span. A per-span walk cannot see those arms;
resolving them needs file-level structure, which is a different tool than the one
this file fixed.

That half keeps its edges, and that is the safe direction: a guessed "terminates"
deletes a real edge and invents a dead-code finding, while a guessed "does not"
only keeps a phantom one and hides. Whatever it is still hiding is bounded by
those 20 spans, and they are enumerable — `scratchpad/endif_walk_verdict.py`
prints them by name.
