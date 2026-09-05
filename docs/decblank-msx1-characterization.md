# D-DECBLANK — what a blank inside a *decimal literal* does, on two MSX1 machines

Companion to [`docs/spec-basic-decblank.md`](spec-basic-decblank.md), and the
sequel to [`docs/lnblank-msx1-characterization.md`](lnblank-msx1-characterization.md),
whose §11 D filed the finding this measures.

**Instrument:** `("stored_line", TXTTAB)` — the exact bytes of the stored line,
link word dropped (it is an absolute address and the CF-3300's Disk BASIC text
base is not the VG-8020's $8001). Probe
[`probes/basic/basic_probe_lnblank.py`](../probes/basic/basic_probe_lnblank.py),
`dec` battery. `make lnblank-characterize ONLY=dec`.

**Two oracles.** Every row was asked of the **Philips VG-8020** and the
**National CF-3300**, `--repeat 2` on independent boots, and **they agree on all
32 rows**. Every payload passed `make lnblank-echo` first, except the two the
guard is structurally unable to see (§5).

**Order of work.** All four rounds were oracle-locked on the references
**before** zerobas was run on any of them
([`docs/spec-basic-lnblank.md`](spec-basic-lnblank.md) §2.4: in the oracle-lock
direction a dropped keystroke is a false PASS *forever*).

---

## 0. Reading the token bytes

| byte | meaning |
|---|---|
| `<11>`…`<1A>` | the integers 0…9 |
| `<0F> n` | one-byte integer |
| `<1C> lo hi` | two-byte integer |
| `<1D> e m m m` | **single**: exponent `e` biased by 64, then BCD mantissa |
| `<1F> e m×7` | **double** |
| `<0C> lo hi` / `<0B> lo hi` | `&H` hex / `&O` octal |
| `<EF>` `<F1>` `<F2>` | `=` `+` `-` |
| `<84>` `<8F>` | `DATA` `REM` |

Worked: `<1D>A<15><00><00>` → `$41-64 = 1`, mantissa `15` → `0.15×10¹` = **1.5**.
`<1D>C<10>…` → `0.10×10³` = **100**. `<1D>?<10>…` → `0.10×10⁻¹` = **0.01**.
`<1D>X<10>…` → `0.10×10²⁴` = **1E23**. `<1D>E2v<80>` → `0.32768×10⁵` = **32768**.
`<1D>@P<00><00>` → `0.50×10⁰` = **0.5**. Every reading below decodes to the value
the source text names, which is a consistency check the raw bytes give for free.

---

## 1. Round 1 — the seams of a decimal literal

`^` = control · `*` = informational, non-gating

| row | typed | **both references** | zerobas today |
|---|---|---|---|
| `dec-ctl` ^ | `20 A=1+2` | `A<EF><12><F1><13>` | *agrees* |
| `dec-hexctl` ^ | `20 A=&H12` | `A<EF><0C><12><00>` | *agrees* |
| **`dec-trail`** | `20 A=1 +2` | `A<EF><12> <F1><13>` | *agrees* |
| **`dec-trail2`** | `20 A=1  +2` | `A<EF><12>  <F1><13>` | *agrees* |
| `dec-run2` | `20 A=1  0` | `A<EF><0F><0A>` — **10** | `A<EF><12>  <11>` |
| `dec-dotpre` | `20 A=1 .5` | `A<EF><1D>A<15><00><00>` — 1.5 | `A<EF><12> <1D>@P<00><00>` |
| `dec-dotpost` | `20 A=1. 5` | `A<EF><1D>A<15><00><00>` — 1.5 | `A<EF><1D>A<10><00><00> <16>` |
| `dec-exppre` | `20 A=1 E2` | `A<EF><1D>C<10><00><00>` — 100 | `A<EF><12> E2` |
| `dec-expsgn` | `20 A=1E- 2` | `A<EF><1D>?<10><00><00>` — 0.01 | `A<EF><12>E<F2> <13>` |
| `dec-expsgn2` | `20 A=1E -2` | `A<EF><1D>?<10><00><00>` — 0.01 | `A<EF><12>E <F2><13>` |
| `dec-sfxh` | `20 A=1 #` | `A<EF><1F>A<10><00><00><00><00><00><00>` — a **double** | `A<EF><12> #` |
| `dec-sfxp` | `20 A=1 %` | `A<EF><12>` — the `%` is **gone** | `A<EF><12> %` |
| `dec-int5` | `20 A=3 2 7 6 7` | `A<EF><1C><FF><7F>` — int 32767 | `A<EF><14> <13> <18> <17> <18>` |
| `dec-int6` | `20 A=3 2 7 6 8` | `A<EF><1D>E2v<80>` — single 32768 | `A<EF><14> <13> <18> <17> <19>` |
| `dec-mix` | `20 A=1 0E 2` | `A<EF><1D>D<10><00><00>` — 1000 | `A<EF><12> <11>E <13>` |
| `dec-neg` | `20 A=- 1` | `A<EF><F2> <12>` | *agrees* |
| `dec-oct` | `20 A=&O1 7` | `A<EF><0B><01><00> <18>` | *agrees* |
| `dec-bin` * | `20 A=&B1 1` | `A<EF>&B1 1` — **verbatim** | `A<EF>&B1 <12>` |
| `dec-data` | `20 DATA 1 0` | `<84> 1 0` | *agrees* |

### 1.1 ⚠️ `dec-trail` is the row that sizes the fix, and it AGREES

`20 A=1 +2` keeps its blank on the references, and `20 A=1  +2` keeps **both**.
So the decimal scanner is not blank-blind and does not eat a separator either —
unlike the leading line number, which eats exactly one
([`lnblank-msx1-characterization.md`](lnblank-msx1-characterization.md) §3).
Every row the TODO filed with this item puts the blank *between two things that
both belong to the number*; none of them could distinguish "skips blanks" from
"skips blanks and keeps the ones it did not use", and the two implementations
diverge on `A=1 +2` — a line far more ordinary than anything in the filed set.

These two rows agree with zerobas **today**, for a reason the fix must not
remove: stopping at the blank is accidentally right when nothing follows it.
They are the slice's must-not-move cells, and knife K4 exists to turn them red.

### 1.2 The suffix rows are not cosmetic

`1 #` is a **double** on the reference and an integer-plus-junk on zerobas —
a divergence in the token's *type*, not its spacing, propagating into every
arithmetic the line does. `1 %` is the mirror: the `%` is consumed and vanishes.

### 1.3 The classification boundary survives the join

`3 2 7 6 7` is a two-byte integer and `3 2 7 6 8` is a single, on both machines.
The int/float decision is taken on the value the blanks produced. The pair
differs by one, so neither row can agree for the wrong reason — this is the cell
D-LNBLANK's "a bound tested after a lossy step tests the wrong number" lesson
demands, asked of `tk_float` rather than assumed absent.

---

## 2. Round 2 — a false start behind each seam

Round 1 showed that the dot, the exponent marker, the exponent's sign and a type
suffix are all reachable across a blank run. That is a one-character lookahead —
and `E` is the one continuation that can turn out **not** to be one.

| row | typed | **both references** | zerobas today |
|---|---|---|---|
| `dec-expbad` | `20 A=1 EX` | `A<EF><1D>A<10><00><00>X` — single 1, **`E` eaten** | `A<EF><12> EX` |
| `dec-expbadsg` | `20 A=1 E+X` | `A<EF><1D>A<10><00><00>X` — `E` *and* `+` eaten | `A<EF><12> E<F1>X` |
| `dec-expboth` | `20 A=1 E 2` | `A<EF><1D>C<10><00><00>` — 100 | `A<EF><12> E <13>` |
| `dec-expblk` | `20 A=1E 2 3` | `A<EF><1D>X<10><00><00>` — **1E23** | `A<EF><12>E <13> <14>` |
| `dec-dotx` | `20 A=1 .X` | `A<EF><1D>A<10><00><00>X` — single 1. | `A<EF><12> .X` |
| `dec-sfxb` | `20 A=1 !` | `A<EF><1D>A<10><00><00>` — single | `A<EF><12> !` |
| `dec-eol` * | `20 A=1␣` | `A<EF><12>` | `A<EF><12>␣` — see §5 |

🔴 **`dec-expbad` says the reference does not roll a malformed exponent back at
all.** The marker is consumed, the sign with it, and its mere presence forces the
literal to single precision. That is two claims at once and only one of them is
about blanks — which is what round 3 is for.

`dec-expblk` (`1E 2 3` → 1E23) also settles that the exponent's *own* digit run
is blank-transparent, not just the mantissa's.

---

## 3. Round 3 — the same false starts with NO blank in the way

| row | typed | **both references** | zerobas today |
|---|---|---|---|
| `dec-expbad0` | `20 A=1EX` | `A<EF><1D>A<10><00><00>X` | `A<EF><12>EX` |
| `dec-expbadsg0` | `20 A=1E+X` | `A<EF><1D>A<10><00><00>X` | `A<EF><12>E<F1>X` |
| `dec-dotx0` | `20 A=1.X` | `A<EF><1D>A<10><00><00>X` | *agrees* |
| `dec-eolctl` * | `20 REMX␣` | `<8F>X` | `<8F>X` |

🔴 **The reading is byte-identical to round 2's, blank or no blank.** So the
malformed-exponent divergence is a **separate live defect** that has nothing to
do with this item — zerobas' `tkf_try_exponent` rolls the marker back and leaves
it for the ordinary tokeniser, which its own header
([`sub/tkfloat.asm:230`](../sub/tkfloat.asm:230)) records as own-design rather
than oracle-pinned. Filed as **D-EXPBAD**
([`spec-basic-decblank.md`](spec-basic-decblank.md) §5.1).

Closing this item on `dec-expbad` would have been the D-MFDOM trap exactly:
attributing to the filed defect a measurement that belongs to another one sitting
underneath it.

`dec-dotx0` is the matching control for the dot and it **agrees** — so the dot
half of round 2 is purely the blank rule, and only the exponent half is not.

---

## 4. Round 4 — the ENTRY, which is not in `tk_float` at all

| row | typed | **both references** | zerobas today |
|---|---|---|---|
| `dec-dotlead0` ^ | `20 A=.5` | `A<EF><1D>@P<00><00>` — 0.5 | *agrees* |
| `dec-dotlead` | `20 A=. 5` | `A<EF><1D>@P<00><00>` — 0.5 | `A<EF>. <16>` |

⚠️ **A literal may begin with the dot, and that decision is taken before
`tk_float` is entered.** `tk_loop`'s dispatch
([`basic/tokenise.inc:68`](../basic/tokenise.inc:68)) looks exactly one character
past the `.` and demands a digit. A blank there is a cell no change inside
`tk_float` can reach, and a slice that measured only the scanner would have
shipped a hole its own rule predicts.

---

## 5. 🔴 The trailing-blank cell is NOT MEASURABLE with this instrument

> ✅ **…AND IT IS MEASURABLE WITH A DIFFERENT ONE — 2026-09-05 (D-TRAILBLANK,
> `scratchpad/trailblank_probe.py`), built from this section's own suggestion.**
> An `$EA` ASCII program on tape, `LOAD"CAS:"`, and the readout is the tokenised
> program at TXTBASE via `debug read_block` — **bytes, not a screen, so nothing
> `rstrip`s anything.** Same payload path on all three machines; only the command
> differs (typed on the VG-8020 and zerobas; an `AUTOEXEC.BAS` on a disk for the
> CF-3300, whose date prompt hijacks the keyboard — the disk carries the command,
> never the payload).
>
> | line delivered verbatim | VG-8020 | CF-3300 | zerobas |
> |---|---|---|---|
> | `10 REM HELLO␣` | `<8F> HELLO␣` | `<8F> HELLO␣` | `<8F> HELLO␣` |
> | `20 A=1␣` | `A<EF><12>␣` | `A<EF><12>␣` | `A<EF><12>␣` |
>
> 🎯 **All three KEEP the blank, in the `REM` tail and after a literal.** Against
> the typed table below — where both references DROP it and zerobas keeps it —
> that isolates the site: the tokeniser is identical on all three, and the
> reference's own drop happens before it. **The paragraph below reasoned to
> exactly that conclusion from the verbatim-`REM` argument; it now has a
> measurement under it.**
>
> ⚠️ **It does not rescue the unstable half.** The `--repeat 1` disagreement
> recorded further down is about the TYPED path, and this run says nothing about
> it — the difference itself still needs re-establishing before anyone goes
> looking inside the editor.
>
> 🎁 And *"a payload whose delivery cannot be verified may not gate"* was true of
> the KEYBOARD path only: this delivery is verified by construction, so the two
> informational rows could become scored rows through it.


At `--repeat 2` on the final build, both rows read the same way and point away
from the scanner:

| row | typed | VG-8020 | CF-3300 | zerobas |
|---|---|---|---|---|
| `dec-eol` | `20 A=1␣` | `A<EF><12>` | `A<EF><12>` | `A<EF><12>␣` |
| `dec-eolctl` | `20 REMX␣` | `<8F>X` | `<8F>X` | `<8F>X␣` |

A `REM` tail is stored **verbatim** on every MSX, so a trailing blank there
cannot be dropped by any crunch rule — yet both references drop it. That places
the difference at **line ENTRY**, before the tokeniser: the references' editor
strips a trailing blank and zerobas' does not. Nothing here is about the number
scanner, and the fix is neutral on both rows (under R-D3 a blank run before
end-of-line is never accepted, so `dec-eol`'s zerobas reading does not move).

⚠️ **And the rows have not read the same way on every pass.** An earlier
`--repeat 1` run read `dec-eolctl` on zerobas as `<8F>X` — *without* the blank —
for a payload the fix cannot touch. Two boots of the final run agree, but two
runs of the same row have not, so the cell is **not stable enough to ground a
rule**; it is reported and filed, not concluded.

⚠️ **And the echo guard cannot referee it, by construction.** `echo_missing()`
`rstrip`s every screen row, so a trailing blank is invisible to the guard no
matter what the machine did with it — both rows come back `MANGLED` on every side
including the ones that behaved. That is an apparatus limit, not a reading:

* a payload whose delivery cannot be verified **may not gate**, so both rows are
  informational;
* the fix must be neutral here, and is: under R-D3 the blank run before
  end-of-line is never accepted, so `dec-eol`'s zerobas reading does not move.

Resolving the cell needs a delivery path that bypasses the line editor — an ASCII
`LOAD"CAS:` the way `basic_probe_floatlit.py` reaches literals. Filed.

---

## 6. Summary of the rule

1. **R-D1** a blank run is transparent when the scan *accepts* what follows it —
   at every seam: digits, the dot from either side, the exponent marker, its
   sign, its digits, and a type suffix.
2. **R-D2** a blank run the scan does not accept past is left alone, **entirely**
   — no separator blank is eaten, unlike the leading line number.
3. **R-D3** implementable form: **the cursor the scan reports is one past the
   last character it actually consumed.**
4. **R-D4** the joined value flows through int/single/double classification
   normally.
5. **R-D5** it stops at `&H`, `&O`, `&B` (which is not a radix at all), string
   literals, `REM` tails, `DATA` bodies and variable names.

Two neighbouring defects were found by the denominator and filed, not fixed:
**D-EXPBAD** (§3) and the `&B` half-crunch (§1, `dec-bin`).
