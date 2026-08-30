# D-VALFLT — `VAL` stops being its own number parser and calls the tokeniser's

*2026-08-30. `sub/strheap.asm` (`sh_val_parse`), `basic/str-engine.asm`
(`ev_ff_val`). Probe `scratchpad/val_probe.py`; knives
`scratchpad/valflt_knives.py`. Builds on
[`docs/spec-basic-valfloat.md`](docs/spec-basic-valfloat.md) (the plumbing) and
[`docs/spec-basic-pcttrunc.md`](docs/spec-basic-pcttrunc.md) (the three crunch
defects that had to be fixed first).*

## 1. What was wrong

`VAL` read a leading, optionally signed **decimal integer** and stopped. That is
wrong for every fraction, every exponent, every embedded blank, and every value
past int16 — the last of which **wrapped silently**:

| row | vg8020 / cf3300 | zerobas (before) |
|---|---|---|
| `VAL("1.5")` · `VAL(".5")` | 1.5 · .5 | 1 · 0 |
| `VAL("1E3")` · `VAL("1E-3")` · `VAL("1D3")` | 1000 · 1E-03 · 1000 | 1 |
| `VAL("1 2")` · `VAL("1 . 5")` · `VAL("1 E 3")` | 12 · 1.5 · 1000 | 1 |
| `VAL(" - 12")` · `VAL("-          12")` | -12 | 0 |
| `VAL("40000")` · `VAL("-40000")` | 40000 · -40000 | **-25536** · **25536** |
| `VAL("1E99")` | `Overflow` | 1 |

⚠️ **And `VAL` never raises on junk**, so every one of these is a number that is
quietly not the reference's number. That is the class this project ranks worst.

## 2. The fix is not to write a parser

All of it is already written, correct and oracle-pinned, in `tk_float` — the
tokeniser's own numeric scanner. VAL calls it instead of growing a second copy
that would drift. D-VALFLOAT had already landed the two things that made that
possible without switching anything on: a **source bound** (`TKVALEND`, a
position test, because callers rewind across blank runs) and **exits that
`ret`** in VAL mode.

What is added here is the caller.

## 3. 🟢 The scratch goes on the stack

The emitted token needs at most 9 bytes (`DBL_TOKEN` + 8). Three shared RAM
buffers were examined across this arc and **all three turned out to be owned** —
`TOKBUF` (direct-mode lines execute from it), `DETOKBUF` (`PRINT USING` drains
it), `FOUTBUF` (four math-pack files write it). The question dissolves at `SP`:

```
                ld      hl,-10
                add     hl,sp
                ld      sp,hl               ; 10 bytes of scratch AT SP
```

It cannot alias anything. `tk_float`'s own pushes go **below** SP and an
interrupt lands below those, so nothing can reach it.

⚠️ **And it is decoded BEFORE it is released.** Once SP moves back up the bytes
are above SP, where the next interrupt overwrites them.

## 4. How a float gets back to the main ROM

`FAC` is already shared RAM, so the tenant writes the token's value bytes there,
sets `FACTYP` (4/8), and returns that same 4/8 in `SH_LEN` as the marker (0 =
"the answer is the integer in `SH_PTR`"). The glue then ends exactly where a
float **literal** ends — `flt_to_int16`, `ev_f_float`'s own tail — so every int
consumer downstream keeps working and VAL's result has the literal's type.

**The sign is applied tenant-side**, because `tk_float` never sees one: the
tokeniser emits a leading `-` as an operator. On an integer that is a negate; on
a float it is bit 7 of the lead byte, **with value 0 exempt** — the same rule as
`flt_neg`, which cannot be called from a page-0 tenant.

## 5. What is deliberately NOT routed through the crunch

`&H` / `&O` / `&B` keep D-VALBASE's own scan. `tk_float` does not know the base
literals, and the references' answers for them (`&HFFFF` → -1, `&H1FFFF` →
`Overflow`, `&HZZ` → 0, `&` → `Syntax error`) are already measured and shipped.
The `&` test still runs **before** the sign test, which is what makes `-&H10`
answer 0 for free.

## 6. Verification

`scratchpad/val_probe.py`, 97 rows over a VG-8020, a CF-3300 and zerobas:
**29 DIFF -> 4**, and all four survivors are `STR$` of a non-integer, a
different routine (`str_fn_str`, which formats `DE` with `pu_fmt_int` and never
looks at `FACTYP`). **Every `VAL` row is green**, base literals included.

`make unit-test`: ALL 59 TEST FILE(S) PASSED — `test_float.py` drives `tk_float`
on bare literals to exact token bytes, so the plumbing is proven statically as
well as differentially.

Cost: **101 B of sub page 0**, **7 B of the low region**, main page 1 untouched.
Run `make basic-reloc` for the current walls; never quote one from a document.

### The four arms (`scratchpad/valflt_knives.py`), all exact

| knife | cut | moved / predicted |
|---|---|---|
| K-VF1 | `TKVALEND` = body **start**, so every scan is instantly out of range | **42 / 42** |
| K-VF2 | drop the float sign flip | **3 / 3** — and `VAL("-34")`, `VAL(" - 12")`, `VAL("-          12")` did **not** move: they are negative *integers* and take the other arm |
| K-VF3 | drop the `TKOVF` -> `SH_ERR` route | **4 / 4** |
| K-VF4 | restore the `tcr_ovf` frame leak | **3 / 3** |

🎯 **K-VF4 IS THE ARM THE PREVIOUS COMMIT PROMISED AND COULD NOT WITNESS**, and
its prediction is discriminating rather than blanket: `VAL("1E99")`,
`VAL("1D99")` and `VAL("1E-99")` break because their overflow is raised from
inside `tkf_calc_and_round`, one frame deep — while **`VAL("40000.5%")` does
not**, because `tkf_check_percent` refuses at `tk_float`'s own frame level and
was already correct. A blanket "all four overflow rows" would have passed for
the wrong reason. [[a-guard-witnessed-only-by-a-deferred-error]]

⚠️ K-VF1's 42 rows are also the answer to *"which rows actually reach the
crunch?"* — the ones that do not are `VAL("")`, `VAL("ABC")`, `VAL("-")`,
`VAL(".")`, `VAL("0.07%")` (all already 0) and every `&` literal (the base scan
never reads `TKVALEND`). That set is the control, and it was named before the
run, not read off it.
