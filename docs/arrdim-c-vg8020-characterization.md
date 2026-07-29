<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-ARR-C — how many dimensions an array has (VG-8020 characterization)

Measurement behind [`spec-basic-arrdim-c.md`](spec-basic-arrdim-c.md). Probe
[`probes/basic/basic_probe_arrdim.py`](../probes/basic/basic_probe_arrdim.py),
`make arrdim-characterize ONLY=cap|use|auto|line`, boot-per-case, both machines.
Opened by [`spec-basic-arrdim.md`](spec-basic-arrdim.md) §7a as the split-out half
of D-ARR-B, which measured the reference to 100 subscripts and stopped.

Four batteries, measured **2026-07-29**. Two of them exist because the first two
could not answer the question, and one of *those* found that four rows in the
D-ARR-B commit were filed under the wrong cause.

---

## 1. There is no cap to match — and it holds to 120

`MAXDIM = 4` ([`basic/sysvars.inc:1544`](../basic/sysvars.inc:1544)) is a slice-1
implementation cap, recorded in [`spec-basic-arrays.md`](spec-basic-arrays.md)
§9.1 Q-9b as the disposition `>MAXDIM subscripts → Subscript out of range` —
**chosen, written down, and never measured.**

The readout is a stored `DIM` line (never anchored on) + `ON ERROR` + a short
direct `PRINT ERR`, so the subject is not limited by the 37-character echo:

| subscripts | 4 | 8 | 16 | 32 | 40 | 42 | 44 | 64 | 100 | 120 |
|---|---|---|---|---|---|---|---|---|---|---|
| reference `ERR` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **0** |
| zerobas `ERR` | 0 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 | 9 |

`cap-120`'s line 20 is **249 characters**, five short of the reference's own input
line (254 — measured later, see the §4 correction; this sentence originally said
"three short", against an input line nothing here had measured). So the reference
has no dimension cap anywhere a program can reach it,
and "raise `MAXDIM` to the reference's value" still has no value to raise it to.
`cap-4` is the battery's two-sided control.

## 2. ⚠️ `ERR = 0` does not mean the dimensions were honoured

The `cap` rows read `ERR` after the `DIM` **and nothing else** — so a machine that
accepts the line and silently *ignores* every subscript past its own cap reads 0,
exactly like one that honoured all of them. That is this probe's third
agrees-for-the-wrong-reason shape in two slices (`PRINT TAB(99999)` matching while
`TAB(` did not exist; an auto-dimmed array reading 0 like a surviving one, twice
inside D-ARR-B's own matrix).

The `use` battery is the discriminator the ignored dimensions cannot forge — store
*through the full subscript list* and read it back:

| | `use-4` | `use-8` | `use-32` |
|---|---|---|---|
| reference `[ERR V]` | `[ 0  7 ]` | `[ 0  7 ]` | **`[ 0  7 ]`** |
| zerobas | `[ 0  7 ]` | `[ 9  0 ]` | `[ 9  0 ]` |

**The reference round-trips an element through 32 subscripts.** The dimensions are
real, not parsed-and-dropped. `use-4` is the two-sided control.

## 3. Auto-dim past four subscripts is the SIZE rule, not a cap

The auto-dim path is a second allocator entry ([`spec-basic-arrdim.md`](spec-basic-arrdim.md)
§1.5) and no `DIM` row reaches it. D-ARR-C makes it reachable at any subscript
count — and every one of those overflows by construction: auto-dim takes each
bound to 10, so five subscripts ask for 11⁵ = 161051 elements, and even the
narrowest element (int, 2 B) is 322102 B, past `$FFFF` with no element width able
to rescue it.

| case | reference |
|---|---|
| `Q%(1,1,1,1)=1` — 29282 B, under `$FFFF` *(control)* | `Out of memory` |
| `Q(1,1,1,1,1)=1` — 11⁵×8 | **`Subscript out of range`** |
| `Q%(1,1,1,1,1)=1` — 11⁵×2, the narrowest element | **`Subscript out of range`** |
| `Q(1,1,1,1,1,1,1,1)=1` | **`Subscript out of range`** |

So **`>4` subscripts on an undeclared array is the size error, full stop**, and a
tenant-side auto-dim bound table never needs to be longer than four entries. That
shortcut is now measured rather than reasoned.

⚠️ **All three rows already PASS — for a reason D-ARR-C deletes.** zerobas reaches
the same message through the `MAXDIM` cap in `ary_parse_subs`, never through the
allocator. They are green today over an implementation that is about to be
removed, which makes them the slice's own falsification witnesses: afterwards they
must stay green *through `aal_soor`*. **A row that agrees for the wrong reason is
not a passing row, it is an unexploded one.**

## 4. 🔴 Four rows were ungated for the wrong cause — zerobas's line ends at 95

> ⚠️ **CORRECTION, 2026-07-29 (D-LINEMAX).** Everything below about *zerobas* holds
> — 95 characters, re-measured byte-exact. **Everything below about the
> REFERENCE's ceiling does not.** This section quoted it three different ways —
> "three short of" 249 in §1, "255" in the next paragraph, and "**the reference
> takes 250**" under the table — and **none of the three was measured.** The
> `line` battery stopped at 250 because `omsx_repl.MAX_BUF` was 250, a guess
> commented "holds ~255 chars incl CR" that *refused to inject a longer line*. So
> the top row of that table is the **harness's ceiling reported as the machine's**:
> every length past it was unreachable, not accepted-and-tested.
>
> **The reference's real ceiling is 254 characters**, and past it the tail is
> dropped and the line kept — flat at 254 from 255 through 300.
> [`linemax-vg8020-characterization.md`](linemax-vg8020-characterization.md) §1;
> `MAX_BUF` is now 254, measured. Nothing here was measured *wrong*; something
> unmeasured was written down as measured — the same shape as the arrays arc's §4
> target #9.

The D-ARR-B commit filed `cap-64`/`cap-100` under "MAXDIM=4". They are not.
`LINEMAX = 96` ([`basic/sysvars.inc:760`](../basic/sysvars.inc:760)) against the
reference's 254 is a divergence of its own, already documented as an
*Input-length caveat* in
[`spec-basic-arrays-slice4a-string-heap.md`](spec-basic-arrays-slice4a-string-heap.md),
and it lands **inside this battery**.

The `line` battery measures it directly, with no array involved — `20` + padding +
`A=7`, so an intact line assigns 7 and a truncated one leaves A at its
`RUN`-cleared 0, whatever error the mangled tail produces:

| line length | 40 | 90 | 94 | 95 | 96 | 97 | 100 | 250† |
|---|---|---|---|---|---|---|---|---|
| reference | 7 | 7 | 7 | 7 | 7 | 7 | 7 | **7** |
| zerobas | 7 | 7 | 7 | **7** | **0** | 0 | 0 | 0 |

† 250 is where the HARNESS stopped, not the machine — see the correction above.

**zerobas's last intact line is 95 characters; the reference takes 254.**
`20 DIM A(0,...)` is `2n+9` characters, so **43 subscripts is zerobas's real
ceiling** and `cap-44` (97 ch) is already past it.

⚠️ **THE CAP IS WHAT HID THIS.** With `MAXDIM = 4` the parse aborts at the fifth
subscript long before the truncated tail is ever reached, so `cap-44`/`-64`/`-100`/
`-120` all read a tidy ` 9 ` that looks *exactly* like a cap row and says nothing
whatsoever about line length. Remove the cap and that mask goes with it. Measuring
this after the implementation would have meant diagnosing four freshly-red rows
and re-deriving the cause; measuring it first means knowing in advance that
**raising `MAXDIM` cannot turn them green**, because the interpreter never sees
those subscript lists at all.

Two causes, two dispositions, and the boundary between them measured rather than
computed from the equate: `cap-8`…`cap-42` and `use-8`/`use-32` are D-ARR-C's to
turn green; `cap-44`/`-64`/`-100`/`-120` and `line-96`…`line-250` stay ungated
under `LINEMAX`, which is not this slice's item.

## 5. The stack budget, measured

The pointer design ([`spec-basic-arrdim-c.md`](spec-basic-arrdim-c.md) §4) leaves
the parsed subscripts on the hardware stack, so the ceiling stops being a RAM
buffer and becomes stack headroom. C-BIOS sets **`SP = $F300`**
(`~/projects/cbios/src/main.asm:761`) and zerobas's own RAM tops out at **`$EF00`**
([`basic/sysvars.inc`](../basic/sysvars.inc)) — **1024 bytes**. The worst case a
line can express is 43 subscripts = **86 bytes**, under 9% of the headroom, on top
of `eval`'s own nesting. Measured, not assumed.

---

## 6. The matrix as it stands

**73 rows. At measurement time: 55 gated, 18 never-gated. After D-ARR-C landed:
65 gated (ALL PASS), 8 never-gated** — the `LINEMAX` residue of §4 and nothing
else. The eight rows this measurement added (`auto-5d`, `auto-5d-int`, `auto-8d`,
`use-4`, `line-40`/`-90`/`-94`/`-95`) were green from the start, three of them for
the wrong reason (§3); the ten it moved into the never-gated set were D-ARR-C's
own targets plus that residue.

⚠️ **§4's claim was confirmed by the landing, not just argued.** Before D-ARR-C,
`cap-44`/`-64`/`-100`/`-120` read ` 9 ` (Subscript out of range — the cap firing at
the fifth subscript). After it, the same four read ` 2 ` (Syntax error — the
truncated line). Same rows, same disagreement with the reference, a cause that
only became legible once the one standing in front of it was removed. That is what
"the cap is what hid it" looks like from the outside.

---

Related: [[arrdim-slice]], [[clearpool-slice]], [[arrays-dim-arc]],
[[answer-signoff-questions-by-measuring]],
[[gate-can-be-green-while-measuring-nothing]], [[kwsweep-msx1-denominator]].
