# D-FACZERO — zero kept the previous value's mantissa

**Status:** measured, fixed 2026-09-03. **Probe:** `scratchpad/mkfloat_scout.py`.
**Knives:** `scratchpad/faczero_knives.py`.

## 0. Found while asking a different question

`MKS$` / `MKD$` / `CVS` / `CVD` are missing (D-DEFERCHECK, 2026-09-03). Before
writing them, one question decides whether that slice is small or large: **is
zerobas's stored float byte-identical to the reference's?** If yes, `MKS$` is
`MKI$` with a different length. If no, it needs a format conversion — and a
string written to disk by one machine would not read back on the other.

`scratchpad/mkfloat_scout.py` asks that with `VARPTR` + `PEEK`, deliberately
**without using `MKS$`**: the verb does not exist here, so a probe built on it
could only report its own absence.

The answer was yes — and on the way it found this.

## 1. What diverged

12 of 29 rows. Both references agree with each other on every one.

| row | stimulus | refs | zb |
|---|---|---|---|
| `z.lit` | `A!=0` | `0 0 0 0` | `0 255 255 255` |
| `z.calc` / `z.mul` / `z.int` | `1-1`, `5*0`, `0%` | `0 0 0 0` | `0 255 255 255` |
| `z.arr` | `A!(1)=0` | `0 0 0 0` | `0 255 255 255` |
| `z.read` | `READ A!` / `DATA 0` | `0 0 0 0` | `0 255 255 255` |
| `z.defsng` | `DEFSNG B` / `B=0` | `0 0 0 0` | `0 255 255 255` |
| `z.dcalc` / `z.dlit` / `d.zero` | the double forms | `0`×8 | `0 255`×7 |
| **`z.reassign`** | **`A!=1.5` then `A!=0`** | `0 0 0 0` | **`0 21 0 0`** |

🎯 **`z.reassign` is the row that names the mechanism.** `21` is `1.5`'s own
mantissa byte (`s.1p5` reads `65 21 0 0`). The zero exits write the **lead byte
only** and leave the mantissa holding whatever the destination happened to
contain — `$FF` in a fresh slot, the previous value in a reused one. It is a read
of stale memory wearing the value's clothes.

## 2. Why nothing had noticed

Lead byte 0 **is** "the value is zero": `flt_out` never reads further, so every
zero printed correctly. `z.dot` (`A!=0.0`) is green even before the fix, because
a literal with a dot is crunched as a float and packs a real mantissa, while a
bare `0` is crunched as an **integer** and reaches the store through the
int→single widen. Two spellings of the same constant, two different paths, and
only one of them wrong.

⚠️ **It would not have stayed invisible.** `MKS$(0)` emits these exact bytes as a
string, which a program writes to a file. The scout that was only sizing the next
slice caught it before the verb could ship the divergence to disk.

## 3. The fix

`fac_zero_mantissa` (`basic/float-arith.asm`, 10 B) clears `FAC+1..FAC+7`;
`A` stays 0 so each caller's following `ld a,<type>` is unaffected, and `DE` is
untouched. **Two** call sites, 3 B each:

| site | file | reaches |
|---|---|---|
| `rsp_zero_ok` | `float-arith.asm` | every **single** zero |
| `raf_zero_ok` (= `cpow_x0_pos`) | `float-arith.asm` | every **double** zero, incl. `fp_*` underflow |

**There was a third, and its own knife took it out — see §6.**

**Why the packers and not the stores.** Scalars, arrays, `READ` and `DEFSNG` all
diverged, and they have different store paths — but all of them `ldir` from FAC.
Canonicalising FAC once covers all four; siting it at `var_store_fac` would have
left `z.arr` and `z.read` behind. The denominator is what chose the site.

**Cost.** Page-0 low region 79 → **63 B** free (10 B helper + two 3 B calls);
page 1 **unchanged at 269 B**.

## 4. Result

**0 DIFF / 31 rows**, three machines. Controls `z.ctl`, `z.arrctl` (a *nonzero*
into the same slot) and `i.258`/`i.neg` (the integer layout, already known to
agree) stay green, so the change is about zero and not about the slot or the
instrument.

⚠️ **`z.for` is green and says nothing.** A `FOR` loop variable exits at `1`, not
`0`, so that row never reaches the case; it is recorded as coverage of the FOR
store path only, not of zero.

## 5. Not covered

The rows read what is **stored in a variable**. FAC itself is at `$F01C` here —
zerobas's own address, not the reference's `$F7F6` — so `PEEK`ing FAC is a layout
row and not a faithfulness one. When `MKS$`/`MKD$` land they must emit the
**canonical** bytes; reading FAC directly is now safe for the three exits above,
but any new zero producer needs the same call.


## 6. Knives — and the arm that failed

`scratchpad/faczero_knives.py`, one arm per call site, each hashing the ROM so an
arm that did not build is reported INERT rather than believed.

```
base ROM b22bf5f124e6   base DIFF rows: []
K-FZ1  drop the single zero exit's call  moved 9 rows   PASS
K-FZ2  drop the double zero exit's call  moved 3 rows   PASS
K-FZ3  drop the vars.asm unset-arm call  moved <none>   FAIL
restored ROM b22bf5f124e6 (base b22bf5f124e6) OK
```

🔴 **K-FZ3 FAILED, AND THAT IS THE MOST USEFUL RESULT IN THE SET.** `z.unset` and
`z.dunset` were written *specifically* to witness that third site, and with the
call gone they still read `0 0 0 0`. The reason is that `A!=B!` on an unset `B!`
never hands FAC's bytes to the store — it **re-packs** through
`widen_rhs_operand` + `round_single_and_pack`, whose zero exit K-FZ1's site
already canonicalises.

So the third call was **3 bytes that no row could defend**, and it has been
removed. A guard whose only defence is "it seems prudent" is the thing this
project keeps catching in other people's reasoning; a knife that fails is how you
find it in your own.

⚠️ **It comes back the day a consumer reads FAC without re-packing** — and
`MKS$`/`MKD$` are exactly that consumer. Either they call `fac_zero_mantissa`
themselves or they route through the packer; whichever, the choice needs a row
that fails without it.
