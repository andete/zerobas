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

## 4. What is deliberately NOT landed yet

The `_last_code` fix itself. Applying even the `include`-only correction makes the
hard gate report `fat_delete` and `__MEAS_SUB_P1_END`, and neither is adjudicated:

* `fat_delete` is defined in **both** `basic/fat.asm:353` and
  `basic/fat-delete-body.inc:29`, and every caller is in `sub/`
  (`sub/dirverb.asm:128`, `sub/fatprim.asm:205`). That is the *shared body* shape,
  where the header's own answer is `IF SUB_BUILD` **and where deletion has broken
  the build before** — so it needs reading, not a guess.
* `__MEAS_SUB_P1_END` is a measurement label reached by construction rather than
  control flow; it became reportable only because its incoming phantom edge went.

Landing the walk fix without settling both would turn a gate that silently hides
findings into one that fails the build on two non-findings. The full correction
(the `IF`/`ELSE`/`ENDIF` arms, and the 20 undecidable cases needing file-level
rather than per-span context) is a larger change again.

**The carve does not depend on any of that** — it is verified by grepping the
build's own closure, and the assembler confirmed it by linking without the label.
