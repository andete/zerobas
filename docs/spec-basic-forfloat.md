# D-FORFLOAT — a FOR loop that is not int16 arithmetic

Status: **DESIGN** (2026-09-27). Item: `TODO.md` D-FORFLOAT (TIER 1).
Evidence: [`scratchpad/forfloat_probe.py`](../scratchpad/forfloat_probe.py) →
[`scratchpad/forfloat_run.out`](../scratchpad/forfloat_run.out) (AGREE 4/15),
the reference's frame layout in [`docs/reference-stack-frames.md`](reference-stack-frames.md) §2.

## 1. What is wrong

`ex_for` ([`basic/program.asm`](../basic/program.asm)) evaluates the initial value,
the limit and the step with `inc_eval` and keeps only DE, the value's int16 tail.
The frame is `[name0][name1][type][limit:2][step:2][CURLINE:2][resume:2]` = 11 B,
and `ex_next` adds the step to the variable's int16 tail with `add hl,de`, then
compares with `cmp16_bits`. `for_set` stores the int16 back, tagged `FACTYP=2`, so a
double loop variable holds an int16's value. This was a recorded deferral ("D-D",
[`docs/spec-basic-forvar.md`](spec-basic-forvar.md) §5.3) that never became an open
item. Consequences, measured against the VG-8020:

| class | row | VG-8020 | zerobas |
|---|---|---|---|
| fractional STEP | `FOR A=0 TO 1 STEP .25` | 0 .25 .5 .75 1 | 0 0 0 … never ends |
| fractional init | `FOR A=.5 TO 3` | .5 1.5 2.5 | 0 1 2 3 |
| beyond int16 | `FOR A=56700 TO 56702` | 56700 56701 56702 | -8836 … |
| int16 overflow, non-`%` | `FOR A=1 TO 32767 STEP 16384` | 1 16385; A = 32769 | wraps, never ends |
| int16 overflow, `%` | `FOR A%=1 TO 32767 STEP 16384` | 1 16385, then ERR 6 | wraps, never ends |
| body makes it fractional | `FOR A=1 TO 3:A=A+.5` | 1.5 3 | 1.5 2.5 3.5 |

## 2. The reference's rule

From its frame (25 B for every type), as measured in RAM: a kind byte — `05` for
single and double, `FF` for integer — then STEP and limit as 8 B BCD. So:

* **a non-`%` loop is float arithmetic**: `var := var + step`, compared with the
  limit in BCD; the variable is loaded and stored at its own type every pass, so a
  body that changes it (`A=A+.5`) is seen by the next NEXT;
* **a `%` loop is int16 arithmetic** with the step and limit converted once at
  FOR time; an overflowing step is `Overflow` (ERR 6). zerobas's current
  conversion of a fractional step for `%` already agrees (`FOR A%=1 TO 3 STEP .5`
  runs away with A% = 1 on both, `FOR A%=1.7 TO 3` starts at 2 on both).

## 3. Design

### 3.1 One NEXT path, built from the evaluator's own operators

The evaluator already implements "add two typed values" and "compare two typed
values", each with an int16 fast path that PROMOTES to BCD on overflow and a float
path otherwise: `combine_add` and `combine_cmp`
([`basic/float-arith.asm`](../basic/float-arith.asm)), fed by the fixed-size LHS
frame protocol (`push de` / `push_lhs_frame`). NEXT becomes:

1. `for_get` — the variable at its OWN type (FAC + FACTYP, DE the int tail);
2. `push de` / `push_lhs_frame`; load the STEP slot as a factor would leave it;
   `combine_add` → the stepped value, typed;
3. `for_set` storing the result at its ACTUAL `FACTYP` (no longer forced to 2):
   `var_store_fac` coerces to the variable's type — and for a `%` variable an
   out-of-range value is its own `Overflow`, which is the reference's ERR 6 for
   free;
4. `push de` / `push_lhs_frame`; load the LIMIT slot; `combine_cmp` → the
   relation bits; the step's sign picks which one ends the loop, as now.

An int16 loop over int16 values stays on the int fast paths of both operators;
an overflow promotes, which is exactly the `edge` row's 32769.

### 3.2 The frame: typed slots, the reference's 25 B

`[name0][name1][type][limit: type + 8][step: type + 8][CURLINE:2][resume:2]` =
3 + 9 + 9 + 2 + 2 = **25 B**. A slot holds what a factor leaves: `FACTYP`, then
either the int16 (type 2) or FAC's 8 bytes. For a `%` variable the slots are
written as type 2 with today's DE conversion (§2's last bullet). A fixed size
keeps `nx_miss`'s walk (`add hl,FOR_FRAME`) unchanged. The ruled frame economy
(RULED BY JOOST 2026-09-27, *"shrink ours only"*: a frame larger than the reference's is the one to shrink) allows up to the reference's size; the
`fremops` rows will move (zerobas FOR 11 → 25, the VG-8020's own figure).

### 3.3 Where the bytes and the RAM come from

* **Main ROM**: 3 B free (2026-09-27). NEXT's new body stays in main (it is the
  hot path — `kwtime nextkw` is already 1.6× the VG-8020). FOR runs ONCE per loop,
  so its body moves to a **sub page 1 tenant** (266 B free), calling
  `inc_eval`/`for_set`/`ctl_alloc` through the generated ABI
  (`sub/basic-resident-abi.inc`, as `pu_num_tenant` calls `flt_fmt`); the main
  bytes it frees fund NEXT.
* **`FOR_CUR`** (the frame's working copy, `$E045`, 11 B, abutting `CSP` at
  `$E050`) must become 25 B. `tools/ram_map.py` lists unattributed runs
  (`$E41E..$E4F2`, `$F195..$F200`) — candidates only; `scratchpad/ramfree_probe.py`
  must confirm one before it is claimed ([[deffn-ramhunt-slice]]).

### 3.4 The price, stated before it is paid

A default-typed (double) loop variable goes through the BCD add and compare every
pass instead of an int16 add. The reference does the same, but `nextkw` will move
and must be re-measured (`make kwtime`); a slower NEXT within T2's 10× is the
ruled order (TIER 1 correctness before TIER 5 speed). A later fast path — the
frame remembering that init/limit/step were exact int16 and the variable still
holds what NEXT last stored — is a TIER 5 item, not this one.

## 4. Rows

`forfloat_probe.py`'s fifteen rows become an acceptance suite (all must agree),
plus `single`/`double` accumulation (11 passes), a negative fractional step, and
the `%` overflow's ERR 6 with its line.
