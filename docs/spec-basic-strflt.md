# D-STRFLT — `STR$` of a non-integer, and the space no row could see

*2026-08-30. `basic/str-engine.asm` (`str_fn_str`), `basic/float.asm`
(`flt_out` split). Probe `scratchpad/strflt_probe.py`, knives
`scratchpad/strflt_knives.py`. Closes the four rows
[`docs/spec-basic-valflt.md`](docs/spec-basic-valflt.md) left standing.*

## 1. What was wrong

`str_fn_str` formatted `DE` with `pu_fmt_int` and **never looked at `FACTYP`**,
so a float argument was silently whatever int16 `flt_to_int16` had left behind:

| row | vg8020 / cf3300 | zerobas (before) |
|---|---|---|
| `STR$(1.5)` · `STR$(-1.5)` | 1.5 · -1.5 | 1 · -1 |
| `STR$(.5)` · `STR$(1E9)` · `STR$(1E-5)` | .5 · 1000000000 · 1E-05 | 0 |
| `STR$(1.234567890123#)` | 1.234567890123 | 1 |
| `VAL(STR$(1.5))` | 1.5 | 1 |

🟢 **And PRINT's own formatter was already right.** `ctl.frac`, `ctl.big` and
`ctl.small` — the same three values printed directly — are green before the fix
and after it. That is what places the defect in `STR$` rather than in the float
formatter, and it is why the fix is to **reuse** the formatter rather than write
a second one. [[a-case-that-agrees-can-agree-for-the-wrong-reason]]

## 2. 🔴 The trailing space, which no row in the value suite could see

MSX number format puts a space (or `-`) in **front** of every number, and PRINT
adds one **behind**. `STR$` keeps the leading one and drops the trailing one —
so `STR$(1.5)` is `" 1.5"`, four characters.

**The harness cannot see either of them.** It prints `"[";expr;"]"` and the
capture strips, so `" 1.5"` and `"1.5"` read identically. Every value row in
this suite is blind to the exact question the fix has to get right.

So it is pinned twice, by rows that are not blind:

| | vg8020 / cf3300 |
|---|---|
| `"<"+STR$(1.5)+">"` | `< 1.5>` |
| `"<"+STR$(-34)+">"` | `<-34>` |
| `LEN(STR$(1.5))` · `LEN(STR$(0))` · `LEN(STR$(1E9))` | 4 · 2 · 11 |

🎯 **K-SF2 is the arm that proves those rows were necessary**: it keeps PRINT's
trailing space, and **only the fence and `LEN` rows move**. If a `v.*` row had
moved, the harness would not have been stripping; if an `r.*` row had moved,
`VAL` would not have been skipping blanks. The prediction discriminates.

## 3. The shape

`flt_out` becomes a two-liner over a new `flt_fmt`, which builds `FOUTBUF` and
returns `HL` pointing at it. The split costs about **2 bytes**, because the two
`jp print_string` tails become `ret`.

⚠️ **`FOUTBUF` is safe across `STR$`'s own temp allocation**, and that was
checked rather than assumed — this is the third time in this arc that a shared
buffer looked free and was not (`TOKBUF`, `DETOKBUF`, and `FOUTBUF` itself in
D-VALFLT). Its only writers are `basic/float.asm` and the math pack via the
`SQRT_R` / `MATH_R` aliases, and neither is on `str_temp_alloc`'s path.

🔴 **The grep that found the writers listed `sub/strheap.asm` — because of a
comment I had written there an hour earlier.** An instrument that reports a file
for its prose is the same class as one that reports a table from an input it
misread. The hit was read, not counted.
[[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]]

`str_fn_str` then has two arms feeding one builder:

- **integer** — `pu_fmt_int` into `NUMBUF`, `C` = 1 leading space unless negative
  (unchanged);
- **float** — `flt_fmt`, length by scanning to the NUL, `dec b` to drop PRINT's
  trailing space, `C` = 0 because the text already carries its own sign/space.

The builder takes `HL` = source, `B` = length, `C` = leading spaces. Its one new
instruction is `ex (sp),hl`, which swaps the guarded source for the temp
descriptor in a single byte so both survive `str_temp_alloc`.

⚠️ **`NUMBUF` is 8 bytes.** Routing the float text through it — the obvious
"one source buffer" simplification — would have overrun it on
`" 1000000000"` (11) and every double. The two arms keep their own buffers.

## 4. Verification

`scratchpad/strflt_probe.py`: **0 DIFF of 27**, fences and lengths included.
`scratchpad/val_probe.py`: **0 DIFF of 97** — with this, the whole VAL/STR$
sweep closes.
`make unit-test`: ALL 59 TEST FILE(S) PASSED.

Cost: 29 B of the low region. Run `make basic-reloc` for the wall.

| knife | cut | predicted |
|---|---|---|
| K-SF1 | cut the `FACTYP` dispatch | the 15 rows that were DIFF before the fix |
| K-SF2 | keep PRINT's trailing space | **only** the 2 fences + 3 float lengths |
| K-SF3 | `flt_out` skips `flt_fmt` | **only** the 3 float controls — the inverse of K-SF1, and what says the split is a split and not a rename |
