# D-NGRAM14 / D-EXPNEG — one `fac_dbl_int16`, and the EXP special case its rows refuted

*2026-08-30. `basic/float-arith.asm` (the body), `basic/expr.asm` (two reachers
+ the EXP fix), `sub/fp_exp.asm` (the underflow alias). Probe
`scratchpad/ngram14_probe.py`, arms `scratchpad/ngram14_knives.py`.*

**Cost: −15 B** — page-0 low 107 → **112**, main page 1 351 → **361**. Sub page 1
unchanged. **Rows: 18, all pre-existing DIFFs unchanged.**

🔴 **A SECOND FIX RODE ALONG IN THIS SLICE AND WAS REVERTED IN FULL — see §4.**
The carve below is all that ships.

## 1. The carve

Four sites ended with the same eight bytes — *the result in FAC is a double;
publish it as an int16 in DE and return to my caller*:

```
                ld      a,8
                ld      (FACTYP),a
                jp      flt_to_int16
```

`evmc_dispatch` (the sub-ROM math dispatch: SQR/ATN/LOG/EXP), `evmc_exp_huge`,
`round_and_finalize`, and `^`. One body plus two `jp`s and a fallthrough.

## 2. 🔴 The cheaper siting builds and a gate refuses it

Two reachers are in `expr.asm` (page 1, 351 B free) and two in
`float-arith.asm` (page-0 low, 107 B free). Siting the body in **page 1** puts
the saving where the bytes are least scarce and costs the low region nothing —
so that is what I built first. It assembles cleanly, and `subrom-closure-check`
refuses it:

```
FAIL: page-1 escapes in the tenant's resident closure
  fac_dbl_int16 = 5153  <- called
```

`float-arith.asm`'s two sites run **inside the page-1 tenant's resident
closure**, with page 1 switched out. A `jp` into it hangs. The body has to live
in the low region, and the split inverts: **+5 B low, +10 B page 1** rather than
the other way round.

⚠️ **The direction I wanted was the direction that could not work**, and nothing
about the source at either site says so. Only the gate does.
[[a-mechanical-fix-can-break-a-different-invariant]]

## 3. One row per reacher — and two of them were already diverging

The row set gives every reacher its own row, including `round_and_finalize`,
which no *verb* reaches: it is plain float arithmetic (`1.5*3`, `1/3`). Measured
on the pre-carve tree first, so the two DIFFs below are **not** this slice's:

| row | vg8020 | cf3300 | zerobas |
|---|---|---|---|
| `r.atn` `ATN(1)` | `.78539816339745` | `.78539816339745` | `.7853981633974`**`6`** |
| `r.exphuge` `EXP(-1E38)` | `ERR 6` | `ERR 6` | **`0`** |

## 4. 🔴 D-EXPNEG: I re-opened a decision that was already made, and the gate knew

`evmc_exp_huge` answers **0** for `EXP(-huge)` where both references answer
`Overflow`, and its comment says *"not an error"*. I measured the references,
found them unanimous, mapped the domain, and removed the special case — and did
the matching thing in `sub/fp_exp.asm`, where `fexp_underflow` zeroed FAC
silently while `fexp_overflow` two lines above called `penderr_set`.

The rows all moved the way I predicted. Both knives scored exact. And
`math-acceptance` went **red**:

```
FAIL  exp(-200)                  ref: <no span>
FAIL  exp(-1000)                 ref: [ 0 ]
FAIL  10^-70.5                   ref: <no span>
FAIL  EXP correctly-rounded count 22 < floor 23
```

Its own source says why:

> `10^-70.5` — the documented §12.9-bug deviation row: **OURS correctly gives
> 0**, the **REFERENCE throws its own buggy "Overflow"** … asserted OURS=0 only,
> reference captured informationally, never asserted against (the two sides
> deliberately differ here, **by design**).

And `docs/spec-basic-mathpack-slice2.md` §12.9, 2026-07-13:

> **Informational finds:** the reference's own `EXP(-200)` throws `Overflow` (a
> full disposition **BUG in the reference** — the true answer underflows to 0,
> which zerobas [returns correctly])

**The divergence was found, adjudicated and encoded in a gate fifteen days
before I "fixed" it.** Reverted in full; `math-acceptance` is green again.

🔴 **THE LESSON, AND IT IS NOT "READ MORE DOCS".** Measuring both references and
finding them unanimous is *not* evidence that zerobas is wrong. The charter is
faithful MSX1 BASIC **with a documented carve-out for reference bugs**, and this
project keeps those carve-outs in the accuracy gate's own source. **Before
changing a behaviour to match the references, grep the gates for the value you
are about to change** — `math-acceptance` names `exp(-1000)` and `10^-70.5`
literally, and one grep would have stopped this in the first minute.
[[a-fix-falsifies-the-justification-beside-it]]

⚠️ **A knife that scores exactly is not a licence.** K-N14B was perfect: it moved
`EXP(-175/-180/-200)` and nothing else, proving the sub-ROM tail was live and
distinct from the main-side one. A correct arm on a change that should not be
made measures precisely the wrong thing well.

## 5. What the reverted rows are still worth

The rows are **kept** — they confirm §12.9's characterisation at five more
arguments than it had:

| | vg8020 / cf3300 | zerobas |
|---|---|---|
| `EXP(-100)` | `3.72E-44` | `3.72E-44` |
| `EXP(-150)` | `ERR 6` | `0` |
| `EXP(-175)` / `EXP(-180)` / `EXP(-200)` | `ERR 6` | `0` |
| `EXP(-1E30)` / `EXP(-1E38)` | `ERR 6` | `0` |
| `EXP(1E30)` | `ERR 6` | `ERR 6` — the *real* overflow, agreed |

§12.9 recorded one argument (`EXP(-200)`). This is the whole negative tail, and
it shows the boundary is a *range* question, not a sign question: an argument
still representable returns its value on all three machines.

🎯 **And the two knives, which were built for the reverted fix, turn out to
describe the reference-bug region precisely**: K-N14B moved
`EXP(-175/-180/-200)` and **not** `EXP(-1E30)`/`EXP(-1E38)`, because those raise
from the main-side magnitude check before the sub-ROM is dispatched. So even
zerobas's *deliberate* deviation is produced by two different paths — worth
knowing the next time §12.9 is revisited.

## 6. 🔴 A wrong-type knife is invisible on a short value

K-N14A makes the shared tail publish `FACTYP=4` instead of `8`. I predicted nine
rows; **four moved** — `ATN(1)`, `1/3`, `EXP(-100)`, `EXP(100)`.

`SQR(9)`=3, `LOG(1)`=0, `EXP(0)`=1, `2^10`=1024 and `1.5*3`=4.5 render
identically whether FAC is read as single or double. The cut is real at all nine
sites; **the rows can only see it where the rendering depends on the type.** A
row set of tidy round answers would have scored this knife as inert.

## 7. 🔴 Three process failures in one iteration, all mine

* **S1 expected 2 `fexp_overflow` reachers and there are 4** — the routine
  already had two genuine overflow arms. An arm expecting 2 could only pass if
  the pre-existing sites had vanished.
* **A killed knife run left `ld a,4` planted in `basic/float-arith.asm`.** The
  runner restores through `atexit`, which does not run under `SIGTERM`, and the
  run was killed by a foreground timeout. Caught by grepping for the CUT marker
  before staging. **Grep for the marker after any interrupted knife run.**
* **I contended the battery and then broke its flake discriminator.** 17 units
  went red at 800–1000 s; the serial retry pass exists precisely to separate
  flake from real — and I ran `math-acceptance` *concurrently with it*.
  `penderr-acceptance` was called REAL and is green on a quiet machine.
  **Never run a unit while the battery's retry pass is running: that pass IS the
  instrument for deciding what is real.**

## 8. Falsification

| claim | what would refute it | result |
|---|---|---|
| the four tails were identical | the assembler, or a moved row | 18 rows, unchanged before and after |
| the collapse saves 15 B | `make basic-reloc` | +5 low, +10 page 1 |
| every site is rewired | S1 counts them in the source | 1 run (the body), 2 `jp` reachers, 1 fallthrough |
| `EXP(-huge)` should raise | the project's own adjudication | **refuted** — §12.9 calls the reference's Overflow a bug; reverted |
| the page-1 siting is cheaper | `subrom-closure-check` | refused: two reachers run with page 1 switched out |
