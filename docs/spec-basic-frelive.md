<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# FRE(0) against the live stack, per expression shape (D-FREPLUS14)

Status: **built 2026-10-17 (draft, build-only evidence: `make basic-reloc`, the
unit test [`tests/test_frelive.py`](../tests/test_frelive.py)); not yet confirmed
on the machines** — the witness is [`freshape_probe.py`](../scratchpad/freshape_probe.py)
on both, which should now read SAME on every measured row.

## The ruling

Joost, 2026-10-16: *"we have to match reference"* — `FRE(0)` must read what the
VG-8020 reads **in every expression shape**, not only at the top of a statement.
The reference counts `FRE(0)` down to the live Z80 stack pointer, so every
construct its evaluator has open when `FRE` runs costs free memory. zerobas's
`FRE(0)` is fixed against the control pool's frontier and reads the same in every
shape.

## What the reference spends (measured)

[`freshape_probe.py`](../scratchpad/freshape_probe.py) →
[`freshape_run3.out`](../scratchpad/freshape_run3.out), each reading against a
plain `A=FRE(0)` in the same program, variables created first. The cost is
**additive over what is pending** when `FRE` runs; anything already reduced
costs nothing (`FRE(0)+0` and `0+0+FRE(0)` read like one `+`).

| pending construct | bytes |
|---|---|
| an open `(` | 6 |
| unary minus, `NOT` | 6 |
| an enclosing function call (`ABS(`, `INT(`, `VAL(`, `STR$(` ...) | 10 |
| an arithmetic operator `+ - * / ^` | 8 + width of its left operand |
| a relational `= <> < > <= >=` | 10 + width of its left operand |
| an integer operator `MOD \ AND OR XOR EQV IMP` | 8 |
| a string concatenation `+` | 2 |
| an array subscript `R(` | 18 |
| a `DEF FN` call | 14 (zerobas's frame: 13) |

Width: integer 2, single 4, double 8 bytes — the left operand is kept at its own
type. And the **statement** sets a base: against a `LET` (which holds its target
variable while the right side runs), a `PRINT` and an `IF` condition read 4 bytes
more free, a `FOR` start 2 bytes less. At the top of a `LET` the VG-8020 reads 18
bytes below zerobas's fixed value, so 14 in a `PRINT`.

Not measured yet: string relationals, multi-argument functions (`MID$`'s second and
third argument, `INSTR`, `STRING$`), `ON … GOTO`, `PRINT #`, `INPUT`, `LOCATE` /
graphics argument lists, a `FRE` inside a `DEF FN` body.

## How zerobas computes it

The hot evaluator stays as it is: a running depth counter there would cost time on
every expression, and only `FRE(0)` reads it. Instead `FRE(0)` computes the
reference's depth **at the call**:

1. `ev_ff_fre`'s shared tail ([basic/expr.asm](../basic/expr.asm) `ev_fre_close`)
   calls `fre_go` ([basic/main.asm](../basic/main.asm), the image's last code, past every pin)
   where it called `sh_go` — the same 3 bytes, so nothing ahead of the pins
   moved. `fre_go` is `sh_go` untouched for `FRE("")` (op 15). For `FRE(n)`
   (op 17) it calls zerobas-sub2's page-1 tenant `frelive_tenant`
   ([sub2/frelive.asm](../sub2/frelive.asm), index 3, `SUB2_IDX_FRELIVE`) with
   **the mark** — the evaluator's cursor one past this `FRE`'s own `)` — and the
   address of a result word on its stack, and subtracts what comes back (never
   below 0; without zerobas-sub2 the word stays 0).
2. The tenant reads the statement's start from `SAVTXT` (`$F6AF`). In zerobas
   `exec_stmt` writes it at **every** statement head — line start, after each
   `:` (`ex_sep` re-enters `exec_stmt` past it), after `THEN` and after `ELSE`
   — in a program and in direct mode (the line buffer) alike, and nothing on
   the evaluator's path writes it. So it is the current statement's start in
   every case the spec asked about.
3. It identifies the statement by its first token and sets the base: a letter
   or `LET` 18, `PRINT` / `?` and `IF` 14, `FOR` 20, anything else 18 (LET's,
   unmeasured). For an assignment and `FOR` it skips the target to the first
   `=` outside a subscript.
4. It runs a shunting-yard over the **tokens**, exactly the one
   [`frelive_model.py`](../scratchpad/frelive_model.py) validated: each pending
   entry is two bytes on the Z80 stack (class and precedence, the left
   operand's type), and a running sum of their costs is kept as they are
   pushed and reduced. Operand types: a name's suffix, else `DEFTBL` (its codes
   are the widths 2/3/4/8); a constant's token (`$0B`–`$1C` integer, `$1D`
   single, `$1F` double); a function's result (integer, string, `CSNG` single,
   `ABS`/`INT`/`FIX` the argument's own, others double); `FRE` itself a
   **single** — measured: the VG-8020 reads `FRE(0)-FRE(0)` as 12 = 8 + 4
   ([binfre-vg8020-characterization.md](binfre-vg8020-characterization.md) §3.1;
   the model's double was never measured). `;`, a top-level `,`, `TO`, `STEP`,
   `THEN`, `GOTO`, `GOSUB` and `USING` start a fresh expression.
5. When the `)` at the mark closes a `FRE`, the sum still standing below it is
   the depth; the tenant returns base + depth.
6. `FRE(0)` = today's value − that. A plain `A=FRE(0)` reads today's − 18,
   `PRINT FRE(0)` today's − 14 (freplus_probe's 28618 → 28604).

`FRE("")` (the string space) does not move: no stack there.

**Degrades to the base alone** (depth 0) — never a hang, a crash or a read past
the statement: a token the grammar does not allow where it stands (a juxtaposed
`PRINT "A"(FRE(0))`), an assignment without its `=`, a scan that reaches the
statement's end or the mark without meeting the mark's `)` (a `FRE` inside a
`DEF FN` body, whose text is the `DEF` line: phase 2), and a scan that would
stack within 48 bytes of `CTLLIM` (the machine stack descends from the pool).

**Scanned by the model's rule, unmeasured:** a `FRE` in a multi-argument
function's later argument (`MID$`, `INSTR`, `STRING$`: the function stays
pending at 10), string relationals (10 + 3), `FN` calls (as a function), `TAB(`
/ `SPC(` (as one), `PRINT #`'s `#` (skipped), the `TO` / `STEP` parts of `FOR`,
and the base of every statement but `LET`, `PRINT`, `IF` and `FOR`.

## Edge cases

- Several statements on one line: `SAVTXT` is the current one's start (checked
  in the source, step 2 above; unit row `A=1:PRINT 0+FRE(0)`).
- Direct mode: `SAVTXT` points into the line buffer; the scan works the same.
- A `FRE(0)` inside a `DEF FN` body: the depth is the call site's (in the calling
  statement) plus the `FN` frame plus the depth inside the body, scanned from the
  `DEF` line. Phase 2.
- Allocation edges (`Out of memory` thresholds) keep zerobas's own reserves; this
  page changes what `FRE(0)` *reports*, as the ruling asks, not where allocations
  fail.

## Tests

Built: [`tests/test_frelive.py`](../tests/test_frelive.py) runs the tenant over
statements crunched by zerobas's own tokeniser — all 44 measured shapes, the
statement bases, binfre's `FRE(0)-FRE(0)` rows and the degrade rows. Planned:

A gate row per measured shape, the VG-8020 as the oracle, in a new
`frelive-acceptance` built from `freshape_probe.py`'s rows; knives that cut one
cost entry each (a paren, an operator class, a width) and must redden only the
rows that use it.
