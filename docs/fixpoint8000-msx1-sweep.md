# The `$8000` fixed point — a tree-wide sweep of every 16-bit negate and signed shift

**Slice D-NEG8K, 2026-08-11.** Picks up the residual filed by D-DSCALE
(`TODO.md`, "NOTHING SWEEPS THE `$8000` FIXED POINT AT THE OTHER SIGNED-16
DIVIDES") after `gdrw_scale` was found reading a `$8000` product as −32768
where both references read +32768.

**The deliverable is the denominator.** A fix, if any, is priced only after
every site has an answer to two questions in writing: *is `$8000` reachable at
this input*, and *what does the reference answer there*. "Unreachable" was an
assumption at all of them before this sweep.

---

## §1 The hazard, stated once

`$8000` is the sole fixed point of two's-complement 16-bit negation:
`−$8000 = $8000`. Every routine that extracts a magnitude by negating, then
consumes that magnitude, is either

* **correct** — because it consumes the magnitude as an **unsigned** 16-bit
  number, where `$8000` legitimately means 32768; or
* **wrong** — because it consumes it as a **signed** number, or re-applies a
  sign to a value that was never made positive.

`gdrw_scale` was the second kind: it negated, then shifted, then negated again,
so the final negate flipped a magnitude the first negate had failed to make
positive. Everything below is classified by which kind it is.

A second, distinct question rides along at the arithmetic operators: when the
true result of an integer operation **is** +32768, the int16 domain cannot hold
it, and MSX BASIC's answer is to **promote the result to a double** rather than
wrap. `docs/spec-basic-float-core.md` §10.4 pins that for `\`
(`-32768\-1` → `32768`). Whether every operator that can produce +32768 does the
same is the open half of this sweep.

---

## §2 The denominator, machine-produced

Scanner: `scratchpad/negscan.py` (kept — re-runnable). It normalises every
`.asm` line in the tree (strips comments and labels, lowercases, collapses
whitespace), then matches consecutive-instruction patterns. Nothing is
hand-listed.

    TOTAL asm files                                     97      51 301 lines
      with >= 1 candidate site                          18      20 954 lines
      with ZERO candidate sites (scanned, no match)     79      30 347 lines

The 79 files the scan walked and found nothing in include every large one it is
tempting to assume was skipped: `basic/program.asm` (2705), `basic/str-engine.asm`
(1754), `basic/interp.asm` (1728), `basic/files.asm` (1637), `sub/arrays.asm`
(1501), `basic/graphics.asm` (1213), `sub/lineedit.asm` (1174),
`basic/arrays.asm` (1107), `basic/vars.asm` (1095), `basic/cload.asm` (1017).
They are in the denominator as **measured zeroes**, not as omissions.

`probes/` and `scratchpad/` `.asm` files are inside the 97 (they contain no
matches); they are not shipped ROM either way.

### Patterns and their totals

| pattern | shape | hits |
|---|---|---|
| `NEG16-cpl` | `ld a,h / cpl / ld h,a / ld a,l / cpl / ld l,a / inc hl` | 1 |
| `NEG16-sub-hl` | `xor a / sub l / ld l,a / sbc a,a / sub h / ld h,a` | 4 |
| `NEG16-sub-bc` | same over BC | 1 |
| `NEG16-sub-de` | same over DE | 1 |
| `NEG16-sub-hl2de` | `xor a / sub l / ld e,a / ld a,0 / sbc a,h / ld d,a` | 2 |
| `NEG16-zero-de` | `ld hl,0 / [or a] / sbc hl,de` | 6 |
| **negate subtotal** | | **15** |
| `SHR16-srl-h` | `srl h / rr l` | 14 |
| `SHR16-sra-h` | `sra h / rr l` | 3 |
| `SHR16-srl-d` | `srl d / rr e` | 8 |
| `SHR16-srl-b` | `srl b / rr c` | 0 |
| **shift subtotal** | | **25** |
| `NEG8-neg` | `neg` (8-bit; fixed point `$80`, out of scope — §6) | 3 |

### The scanner's own false-negative rate, measured

`NEG16-zero-de` is the one pattern that could plausibly miss a site: it requires
`ld hl,0`, an optional `or a`, then `sbc hl,rr` as **consecutive** instructions,
and a negate written with anything in between would slip past. Re-run loosely —
*any* `sbc hl,de`/`sbc hl,bc` with a `ld hl,0` anywhere in the preceding **four**
instructions — the tree yields **exactly the same 6 sites, no more**. The strict
pattern has a measured false-negative rate of **zero** on this class, so the
"15 negate sites" figure is not an artefact of how tightly the regex was written.

---

## §3 The shift half: 25 sites, 21 of them unsigned by subject

A shift only participates in the hazard if the value being shifted came from a
negation. Every shift in the tree was read; the subject of each is named below.

### 3.1 Shifts whose subject is not a signed quantity at all — 21 sites

| site | subject | `$8000` reachable? | verdict |
|---|---|---|---|
| `sub/graphics.asm:3335` | `g8_wrshifted`: VRAM base address `>> B` for a VDP register | no — VRAM addresses are `$0000..$3FFF` | not a candidate; no negate feeds it |
| `sub/playparse.asm:504` | `PLAY` dotted-note addend, seeded from `12000/tl` (always positive) | no | not a candidate |
| `sub/tkfloat.asm:781` | `srl b` — digit count `PC/2`, 8-bit | n/a | not a 16-bit shift |
| `tape/tape.asm:488` | tape amplitude `7*sum/16`, sum of unsigned samples | no | not a candidate |
| `disk/fat.asm:213, 362` | `cluster >> 1` (FAT12 `cluster*3/2`) | no — cluster numbers are unsigned | not a candidate |
| `disk/fat.asm:1165` | `ceil(filesize/128)` record count | no | not a candidate |
| `disk/kernel.asm:475, 1820, 2371` | `cluster >> 1` | no | not a candidate |
| `disk/kernel.asm:778` | 32-bit `DE:HL >>= 7` file size | no | not a candidate |
| `disk/kernel.asm:1041` | `cluster >> 1` | no | not a candidate |
| `disk/kernel.asm:1329` | `(target_size+511) >> 9` sector count | no | not a candidate |
| `disk/kernel.asm:1662, 1998` | `K >> 7` record count | no | not a candidate |
| `disk/kernel.asm:2467, 2478` | `BDOS_SRCHIDX >> 4` directory sector offset | no | not a candidate |
| `basic/fat.asm:303`, `disk/driver.asm:40,111`, `disk/fat.asm:222,371`, `disk/kernel.asm:484,1236,1764-7,1829,2380,2727,3121-2` | 8-bit `srl a` / `srl b`, unsigned | n/a | not 16-bit |

**Every disk, tape and FAT shift in the tree is on a genuinely unsigned
quantity and none of them is preceded by a negate.** That is the answer to
"and the float pack's shift sequences" for the storage half: the class is empty.

### 3.2 Shifts fed by a negate — 4 sites

| site | routine | fed by | verdict |
|---|---|---|---|
| `sub/graphics.asm:2582/2584` | `gdrw_sc_pos` | `gdrw_negate_hl` (the `$8000` arm added by D-DSCALE) | **fixed, 2026-08-11** |
| `sub/graphics.asm:2593/2595` | `gdrw_sc_neg` | `gdrw_negate_hl` | **fixed, 2026-08-11** |
| `sub/graphics.asm:649` | `gfx_bres_init` | `gfx_abs16` | §4.1 — reachable, **correct** (unsigned consumer) |
| `sub/fp_pow.asm:159` | `fpw_lp` | *nothing* — `MATH_N` is built from decimal digits | §4.4 — reachable, **correct by construction** |

### 3.3 The only `sra` in the tree

`sub/fp_exp.asm:327/329/331` — `HL := n8 >> 3` **arithmetic**. An arithmetic
right shift has no fixed-point problem: at `$8000` it yields `$F000` = −4096,
and −32768/8 = −4096 exactly, so floor and truncate-toward-zero agree. **Not a
candidate.** Worth recording that this is the one place in 51 301 lines where
the signed shift was written as a signed shift.

---

## §4 The negate half: 15 sites

### 4.1 `gfx_abs16` (`sub/graphics.asm:736`) — 6 consumers, all unsigned

`gfx_abs16($8000)` returns `HL=$8000, A=$FF`. This is **already asserted** as
the expected answer by an existing host unit-test row
(`tests/test_graphics.py` `ABS_CASES`, `(-0x8000, 0x8000, 0xFF)`), so the
contract is deliberate, not accidental.

| consumer | uses the magnitude as | `$8000` reachable? | verdict |
|---|---|---|---|
| `gfx_bres_init:592/599` → `GFX_DMAJ/DMIN`, `GFX_CNT`, `GFX_ERR` | unsigned: `srl h/rr l` is logical, `CNT` counts down by `dec hl` + `or`-zero test, and the steep test compares with `sbc hl,de` + **CF** (unsigned) | **yes** — `LINE(-32768,0)-(0,0)` gives `dx = $8000` | **correct**: 32768 steps, `ERR = $4000` |
| `gfx_box_fill:815` → `GFX_FILLCNT = \|dy\|+1` | unsigned countdown | yes, same route via `,BF` | **correct**: 32769 rows |
| `gfx_circ_scale:1368` | `gfx_mul16u` (unsigned), then a re-negate | **no** — bounded domain, `\|v\| <= 255` (§4.2 of the G4 spec) | out of domain |
| `gfx_cross_ge0:1463/1467/1475/1479` | `gfx_mul16u`, magnitudes compared with `sbc`+CF (unsigned) | **no** — same bounded domain | out of domain |

The `LINE` route is reachable **and slow**: 32768 masked plot steps.
`probes/basic/basic_probe_graphics.py:188-191` says so in as many words and
deliberately chose a one-pixel span (`LINE(-32768,0)-(-32767,0)`) to stay off
that edge — so the `dmaj = $8000` case is *knowingly* untested at the probe
layer. It is cheap at the **host unit-test layer**, which calls
`gfx_bres_init` directly with no emulator and no drawing (§7).

### 4.2 The other graphics negates

| site | routine | `$8000` reachable? | verdict |
|---|---|---|---|
| `sub/graphics.asm:1099` | `gfx_circ_bvec_nudge` — applies a sign to a rounded magnitude | no — magnitude is `round(r*QTAB/256)`, `r <= 255` | out of domain |
| `sub/graphics.asm:1166` | `gcbv_y` — screen convention `Vy = -(sin component)` | no — same bound | out of domain |
| `sub/graphics.asm:1381` | `gfx_circ_scale`'s re-negate | no — same bound | out of domain |
| `sub/graphics.asm:1551/1559` | `gfx_neg16_bc` / `gfx_neg16_de` | callers are the circle/arc vectors, same bound | out of domain |
| `sub/graphics.asm:2535` | `gdrw_negate_hl` | **yes** — this is the D-DSCALE site | **fixed** |

⚠️ The four "out of domain" verdicts above all rest on the **same** stated
bound — `r <= 255`, written in the `gfx_circ_scale` header as
"Bounded-domain: `|v|*ASPS` assumed `<=65535` (true for `|v|<=255`…)". That is
one assumption doing four rows' work, and it is an *overflow* bound, not a
`$8000` bound. `CIRCLE(0,0),32768` is already a probe row
(`basic_probe_graphics.py:278`, `ovf_radius`) so the domain is enforced
somewhere; this sweep did not re-derive where. **Filed as a residual, not
closed.**

### 4.3 `abs16` (`basic/float-arith.asm:1598`) — the int-arithmetic magnitude

`abs16($8000)` returns `HL=$8000, A=$80`, same fixed point. Four callers, and
**three of them already have an explicit `$8000` escape**:

| caller | operation | `$8000` reachable? | reference | verdict |
|---|---|---|---|---|
| `widen_int_to:1426` | int16 → FPNUM | yes | — | **correct**: `widen_uint_to` reads the magnitude **unsigned**, sign applied separately, so `$8000` widens to −32768 |
| `combine_mul:1722/1726` | `*` | yes (`-32768*-1`) | promotes | **correct**: sign-dependent bound (32767 positive / **32768** negative) over a full 32-bit unsigned product, overflow → `fp_mul` |
| `sdivmod_mag:1995/2000` ← `signed_div_de_bc` | `\` | yes (`-32768\-1`) | `32768` (spec §10.4, pinned) | **correct**: explicit `DE == $8000 && sign positive → widen_uint_to(32768) → round_and_finalize` |
| `sdivmod_mag` ← `signed_mod_de_bc` | `MOD` | remainder magnitude can never be 32768 | — | **unreachable, by the remainder bound** |

`evmc_abs` (`basic/expr.asm:1479`) is a fifth member of the family and carries
the **same** escape verbatim for `ABS(-32768%)` → `32768`.

**So the tree contains the `$8000` promotion, written out three times, at `*`,
`\` and `ABS`.**

### 4.4 The `widen_uint_to` magnitude sites — correct *because* the widen is unsigned

| site | routine | `$8000` reachable? | verdict |
|---|---|---|---|
| `sub/fp_exp.asm:299` | `DE := \|n8\|`, then `widen_uint_to`, then the sign poked to `$80` | if `n8 = $8000` | **correct**: `$8000` widens **unsigned** to 32768, sign negative → −32768, the original value |
| `sub/fp_log.asm:260` | `DE := \|e'\|`, identical shape | if `e' = $8000` | **correct**, same reason |
| `sub/fp_pow.asm:159` | `MATH_N` halved by a **logical** shift | **yes** — `combine_pow` sets `n := \|y\|` as a **uint16, 32768 representable**, built by `dig_to_word` from decimal digits with **no negation at all** | **correct by construction**; `(-1)^-32768` = 1 is pinned in the `combine_pow` header, `(-1)^32768` is Illegal function call |

`combine_pow`'s asymmetric bound (32767 if `y>=0`, **32768** if `y<0`) is the
fourth place in the tree that knows about `$8000`.

### 4.5 The decimal-conversion negates — magnitude consumed unsigned

| site | routine | `$8000` reachable? | verdict |
|---|---|---|---|
| `basic/print.asm:368` | `print_number`: `HL = -value = magnitude`, then `div10` | **yes**, `PRINT` of any int16 | **correct**: `div10` is unsigned, `$8000` → "32768" behind a `'-'` → `-32768` |
| `basic/printusing.asm:252` | `pu_fmt_int`, same shape, same `div10` | yes | **correct**, same reason |
| `basic/input.asm:373` | `INPUT` numeric-field parse: `DE = 0 - DE` | only if the field's digits reached 32768 | **correct**: negating an unsigned 32768 gives exactly `$8000` = −32768 |
| `sub/strheap.asm:2131` | `VAL`-family int parse: `HL = -DE` | same | **correct**, same reason |

These four are the reverse direction: a *positive* 32768 magnitude negated
*into* `$8000`, which is the one place the fixed point is the right answer.

### 4.6 The one negate with no `$8000` guard — `ev_f_neg`

`basic/expr.asm:738`, unary minus:

```
ev_f_neg:
                inc     ix
                call    ev_pw
                ld      hl,0
                or      a
                sbc     hl,de               ; HL = 0 - operand
                ex      de,hl
                ld      a,(FACTYP)
                cp      2
                jr      z,evfn_ret          ; int -> return DE as-is
                call    flt_neg
evfn_ret:       ret
```

At operand `$8000` this returns `$8000` with `FACTYP=2`, so `PRINT` renders
−32768. The true value is **+32768**, which does not fit int16 — precisely the
case `\`, `*`, `^` and `ABS` all promote to a double.

`sbc hl,de` **already sets P/V on signed 16-bit overflow** — `combine_add` /
`combine_sub` four hundred lines away test exactly that flag from exactly that
instruction (`jp po,caddsub_ok`). Here the flag is produced and never read.

Reachability, three independent routes, all one direct-mode line:

* `-cint(-32768)` — `CINT` yields int16 `$8000`
* `A%=-32768 : PRINT -A%`
* `-(-32768\1)` — `\` yields `$8000` with the sign already negative

And the internal inconsistency that makes its own control: `0-cint(-32768)`
goes through `combine_sub`, whose `sbc hl,de` overflows, so it **promotes**.
Two spellings of the same value, two different answers, inside one ROM.

**Reference answer: unknown before this slice.** Nothing in the tree pins unary
minus at `$8000`; `probes/basic/basic_probe_float_arith.py` carries
`-32768-1`, `-32768*2`, `-32768\-1` and `-32768-32768`, and no unary-minus row
at the fixed point. That reading is §5.

---

## §5 What was measured

### 5.1 Predictions, written before the run

Nine rows added to `probes/basic/basic_probe_float_arith.py` (the gate that
owns unary minus — its own docstring says so). One expected divergence per
route, each with a control that must stay green.

| row | expression | zerobas predicted | reference predicted | why it is in the set |
|---|---|---|---|---|
| R1 | `-cint(-32768)` | `-32768` | `32768` | the defect: unary minus over an int16 `$8000` |
| R2 | `-(-32768\1)` | `-32768` | `32768` | second route to `$8000` — no `CINT` involved |
| C1 | `0-cint(-32768)` | `32768` | `32768` | **the control that indicts R1**: same value, `combine_sub`'s P/V test, promotes |
| C2 | `cint(-32768)` | `-32768` | `-32768` | the operand itself — proves `CINT` reaches `$8000` at all |
| C3 | `-32768\1` | `-32768` | `-32768` | R2's operand — proves `\` yields `$8000` |
| C4 | `-cint(-32767)` | `32767` | `32767` | one below the fixed point: unary minus is otherwise fine |
| C5 | `-cint(32767)` | `-32767` | `-32767` | the other side of zero |
| C6 | `abs(cint(-32768))` | `32768` | `32768` | the sibling that already escapes (§4.3) |
| C7 | `-cdbl(-32768)` | `32768` | `32768` | isolates the fault to the **int** path — the float arm is `flt_neg` |

If R1/R2 come back green, the reference does **not** promote unary minus, the
tree is right, and the sweep closes with every site accounted for and no fix.
That outcome is worth the same as a defect: it converts eleven "unreachable"
assumptions and one "unmeasured" into readings.

### 5.2 Round 1 — the defect confirmed, and the control refuted its own prediction

`make float-acceptance ONLY=32768`, repack build, walls 14 / 73 / 3604 / 1483,
ROMs `04100bfe / 3740108c / 2c630d3d / 6addbc28` (= HEAD `1ab2cf5`).

| row | expression | reference | zerobas | predicted zb | predicted ref | |
|---|---|---|---|---|---|---|
| R1 | `-cint(-32768)` | `32768` | `-32768` | `-32768` ✔ | `32768` ✔ | **RED, as predicted** |
| R2 | `-(-32768\1)` | `32768` | `-32768` | `-32768` ✔ | `32768` ✔ | **RED, as predicted** |
| C1 | `0-cint(-32768)` | **`-32768`** | **`32768`** | `32768` ✔ | `32768` ✘ | **RED — 🔴 THE CONTROL DIVERGED, THE OTHER WAY** |
| C2 | `cint(-32768)` | `-32768` | = | ✔ | ✔ | green |
| C3 | `-32768\1` | `-32768` | = | ✔ | ✔ | green |
| C6 | `abs(cint(-32768))` | `32768` | = | ✔ | ✔ | green |
| C7 | `-cdbl(-32768)` | `32768` | = | ✔ | ✔ | green |
| — | `-32768-1` | `-32769` | = | — | — | green (pre-existing) |
| — | `-32768*2` | `-65536` | = | — | — | green (pre-existing) |
| — | `-32768\-1` | `32768` | = | — | — | green (pre-existing) |

**7/9 value predictions exact; the miss is the one that matters.** C1 was
written as the control that would *indict* R1 — "the same value, spelled as a
binary subtract, promotes; therefore unary minus should too". It does not. The
reference prints `-32768` for `0-cint(-32768)` and `32768` for
`-cint(-32768)`, and **zerobas has both of them backwards**:

* `ev_f_neg` fails to promote where the reference does;
* `combine_sub` promotes where the reference does not.

So this is not one defect with a control, it is **two defects that happen to
sit either side of the same fixed point** — and the second one would never have
been looked for. It was found the same way `gdrw_scale` was: by a row written
to be green.

The coherent reading is that the reference does not compute `a-b` as a signed
subtract at all; it computes `a + neg16(b)`, and `neg16($8000) = $8000`, so the
overflow is invisible to it. Under that hypothesis the divergence is **not**
confined to `a=0` — it should hold for every `a`. Round 2 decides that, because
a model fitted to one input is exactly what D-DSCALE was burned by.

### 5.3 Round 2/3 — how far the subtract divergence reaches

The hypothesis was H1: *the reference computes `a-b` as `a + neg16(b)`, so with
`b = $8000` the overflow is invisible for every `a`, not just `a=0`.*

| row | expression | reference | zerobas | H1 predicted ref | |
|---|---|---|---|---|---|
| D1 | `1-cint(-32768)` | `-32767` | `32769` | `-32767` ✔ | RED |
| D2 | `32767-cint(-32768)` | `-1` | `65535` | `-1` ✔ | RED |
| D3 | `0-(-32768\1)` | `-32768` | `32768` | `-32768` ✔ | RED — the producer does not matter |
| D5 | `100-cint(-32768)` | `-32668` | `32868` | `-32668` ✔ | RED |
| D4 | `-1-cint(-32768)` | `32767` | `32767` | `-32769` ✘ | green |
| D6 | `(-32768\1)-(-32768\1)` | `0` | `0` | `-65536` ✘ | green |
| C8 | `1-cint(-32767)` | `32768` | `32768` | — | green — subtract DOES promote normally |
| C11 | `0+cint(-32768)` | `-32768` | `-32768` | — | green |
| C12 | `cint(-32768)-1` | `-32769` | `-32769` | — | green — `$8000` on the **LHS** promotes |
| C13 | `32767-cint(-32767)` | `65534` | `65534` | — | green — a big overflow still promotes |
| D7 | `(-32768\1)+(-32768\1)` | `-65536` | `-65536` | — | green — **`+` is not exempt** |

🔴 **Two of the four discriminators were VACUOUS, and my predictions for both
were wrong for the same reason.** `-1-(-32768)` = 32767 and `$8000-$8000` = 0
**do not overflow at all** — they fit int16 — so no promotion decision is ever
reached and neither row can say anything about the rule. I predicted `-32769`
and `-65536` for them by pushing them through H1's *model* of the reference
instead of computing the actual subtraction. That is D-DSCALE's lesson landing
again inside the slice that was written to apply it: **the model had a blast
radius, and I extrapolated past it a second time.** The four rows that do
overflow (`a` = 0, 1, 100, 32767) are the whole evidence base.

### 5.4 The measured rule

> **`a - b` over two int16 operands, with `b == $8000` and the true result
> outside int16, WRAPS mod 65536 and stays type INT — the reference never
> promotes it.** For every other `b` it promotes on signed overflow as
> `docs/spec-basic-float-core.md` §10.4 already documents. `$8000` on the
> **LHS** is not exempt (`cint(-32768)-1` → `-32769`, promoted), and `+` is not
> exempt (`(-32768\1)+(-32768\1)` → `-65536`, promoted).
>
> **Unary minus is the opposite:** `-x` at `x == $8000` **promotes** to the
> double `+32768`, joining `ABS(-32768%)`, `-32768\-1` and `-32768*-1`.

Both readings say the same thing about the reference's shape: binary `-`
negates its RHS and adds, so `$8000` slips through; unary minus does not go
through that path and has its own int16-domain escape. **zerobas had both of
them backwards.**

---

## §5A The fix

Two edits, in two different ROM regions.

### Fix A — `basic/expr.asm`, `ev_f_neg` (page 1, **+6 B**)

`sbc hl,de` already sets P/V for exactly one int16 operand — `$8000` — and the
flag was produced and never read. The arm reuses `evmc_abs`'s promote tail,
which is now labelled `evabs_esc` (the same escape, at the second operator that
can produce +32768 — three copies existed, this makes it a shared leaf rather
than a fourth). `push af`/`pop af` carries P/V across the `FACTYP` read, because
`cp 2` overwrites it with parity.

### Fix B — `basic/float-arith.asm`, `caddsub_int_check` (low region, **+9 B**)

`sbc hl,de` has **already computed the wrapped value** the reference prints, so
the entire quirk is a *suppressed promotion* — no arithmetic changes. The guard
is 9 B because `A` still holds `FP_OPMODE` at that point (nothing between its
load and the check touches `A`), so the operation-mode test costs 3 B, not 6.

### Price, predicted then measured

| wall | before | predicted | measured | |
|---|---|---|---|---|
| page-0 low | 14 B | 5 B | **5 B** | ✔ |
| page 1 | 73 B | 67 B | **67 B** | ✔ |
| sub page 0 | 3604 B | 3604 B | **3604 B** | ✔ |
| sub page 1 | 1483 B | 1483 B | **1483 B** | ✔ |
| `disk.rom` | `2c630d3d` | unchanged | **`2c630d3d`** | ✔ |
| `sub.rom` | `3740108c` | unchanged | **`c2292117`** | ✘ |

🔴 **The `sub.rom` prediction MISSED, and the reason is structural.** The sub
ROM's tenants link against resident main-ROM routines *by address*; Fix B
inserted 9 B into the page-0 **low region**, which moves every resident symbol
after it, so the sub ROM's ABI references move with them. **A low-region
insertion is never sub-ROM-neutral** — only a page-1-only edit (Fix A alone)
would have been.

The mechanism is visible in the regenerated `sub/basic-resident-abi.inc`, and
it is exactly two symbols, each by exactly the 9 B Fix B inserted:

```
-widen_uint_to equ 03BE3H          -vars_reset equ 03DB1H
+widen_uint_to equ 03BECH          +vars_reset equ 03DBAH
```

K-N4 confirms it from the other side: reverting the insertion restores
`sub.rom` to `3740108c` byte for byte.

---

## §5B Knives

Runner: `scratchpad/knives.py` (throwaway, not committed). Subject is the probe
invoked directly, scoped `--only 32768`; every cut asserts its site occurs
**exactly once**; restore is in a `finally`; a report without its tally line is
an abort, not "nothing moved".

K-N1..K-N3 are **byte-neutral** — each swaps one opcode for another of the same
length, so the fix's bytes stay resident and only the decision dies. K-N4 is a
true revert and must rebuild the pre-slice ROMs byte for byte.

### Predictions, written before the run

| knife | cut | predicted RED | predicted ROM |
|---|---|---|---|
| K-N1 | `ret po` → `ret` in `ev_f_neg` (`$E0`→`$C9`) | R1, R2 | moves; not pre-slice |
| K-N2 | `xor $80` → `xor $00` in `caddsub_int_check` | C1, D1, D2, D3, D5 | moves; not pre-slice |
| K-N3 | `jr z,caddsub_ovf` → `jr c,…` (never taken after `or a`) | **D7 only** | moves; not pre-slice |
| K-N4 | both edits reverted to `HEAD:` | R1, R2, C1, D1, D2, D3, D5 | **`04100bfe`/`3740108c`/`6addbc28`**, walls 14 / 73 |

**K-N3 exists to price my own bytes.** It kills the operation-mode test so the
`$8000` suppression applies to `+` as well. If it reddens nothing, those 3 B are
dead weight and Fix B should be 6 B, not 9 B.

### Results — **4/4 EXACT**

| knife | rc | rows moved | predicted | | ROM |
|---|---|---|---|---|---|
| K-N1 | 1 | 2 — R1, R2 | 2 | **EXACT** | `d1c7fc72`, walls 5 / 67 |
| K-N2 | 1 | 5 — C1, D1, D2, D3, D5 | 5 | **EXACT** | `27daf52f`, walls 5 / 67 |
| K-N3 | 1 | 1 — D7 | 1 | **EXACT** | `79c8e21c`, walls 5 / 67 |
| K-N4 | 1 | 7 — all of the above bar D7 | 7 | **EXACT** | **`04100bfe` / `3740108c` / `6addbc28`, walls 14 / 73** |

* **K-N1 and K-N2 move DISJOINT row sets** — the two fixes are orthogonal; each
  reddens only its own defect's rows and neither covers for the other.
* **K-N3 reddened exactly one row.** The 3 B operation-mode test is load-bearing:
  without it the `$8000` suppression leaks onto `+` and `(-32768\1)+(-32768\1)`
  wraps to 0 instead of promoting to `-65536`. Fix B cannot be 6 B.
* 🎯 **K-N4 rebuilt the pre-slice ROMs byte for byte** — `basic-reloc 04100bfe`,
  `sub 3740108c`, `zerobas-main-eu 6addbc28`, walls back to 14 / 73. The
  cheapest proof available that the slice is exactly these two edits and
  nothing else, and it independently confirms the `sub.rom` finding above:
  reverting the low-region insertion restores the sub ROM's hash exactly,
  because the only thing that moved it was the resident-symbol shift.

Baseline before the knives: 23 rows, probe rc=0, walls 5 / 67. Restored and
rebuilt afterwards to `8e5391b3` / walls 5 / 67.

---

## §5C Host-layer rows for the one reachable-but-unmeasured site

`gfx_bres_init` at `dmaj = $8000` (§4.1) is reachable from
`LINE(-32768,0)-(0,0)` but costs 32768 masked plot steps, which is why
`basic_probe_graphics.py` picks a one-pixel span there. At the emulator-free
layer it costs one call and draws nothing, so three rows now assert the half
that makes `gfx_abs16($8000) = $8000` **correct** rather than a defect — that
every consumer reads it as unsigned:

    gfx_bres_init (-32768,0)-(0,0) -> dmaj/dmin/cnt/err=(32768,0,32768,16384) steep=0
    gfx_bres_init (0,0)-(-32768,0) -> dmaj/dmin/cnt/err=(32768,0,32768,16384) steep=0
    gfx_bres_init (0,-32768)-(0,0) -> dmaj/dmin/cnt/err=(32768,0,32768,16384) steep=1

🔴 The third row's expectation was written with **DMAJ and DMIN inverted** and
the test refuted it. The source says "steep (y-major): DMAJ=ady, DMIN=adx
(swap)" on the line above the code; the prediction was made from the shape of
the other two rows instead of from the site. Same fault as §5.3's vacuous
discriminators, in miniature, twice in one slice.

`make unit-test`: **59/59 files pass** (was 59; the rows land inside the
existing `test_graphics.py`).

---

## §6 Explicitly out of scope, named rather than omitted

* **8-bit `neg`, 3 sites** — `basic/float-arith.asm:621` (`fp_add`'s alignment
  shift amount, range 1..126), `sub/fp_rnd.asm:424`, `disk/driver.asm:540`.
  The 8-bit fixed point is `$80` = −128, a different value; none of the three
  subjects can reach it (the first is bounded by the ±63 dexp range). Listed so
  the next reader does not have to re-derive that they were considered.
* **32-bit quantities** — only one exists (`disk/kernel.asm:778`, a file size)
  and it is unsigned.
* **`probes/` and `scratchpad/` `.asm`** — inside the 97 files scanned, zero
  matches, not shipped.
