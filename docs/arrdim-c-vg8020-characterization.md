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

`cap-120`'s line 20 is **249 characters**, three short of the reference's own
input line. So the reference has no dimension cap anywhere a program can reach it,
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

The D-ARR-B commit filed `cap-64`/`cap-100` under "MAXDIM=4". They are not.
`LINEMAX = 96` ([`basic/sysvars.inc:760`](../basic/sysvars.inc:760)) against the
reference's 255 is a divergence of its own, already documented as an
*Input-length caveat* in
[`spec-basic-arrays-slice4a-string-heap.md`](spec-basic-arrays-slice4a-string-heap.md),
and it lands **inside this battery**.

The `line` battery measures it directly, with no array involved — `20` + padding +
`A=7`, so an intact line assigns 7 and a truncated one leaves A at its
`RUN`-cleared 0, whatever error the mangled tail produces:

| line length | 40 | 90 | 94 | 95 | 96 | 97 | 100 | 250 |
|---|---|---|---|---|---|---|---|---|
| reference | 7 | 7 | 7 | 7 | 7 | 7 | 7 | **7** |
| zerobas | 7 | 7 | 7 | **7** | **0** | 0 | 0 | 0 |

**zerobas's last intact line is 95 characters; the reference takes 250.**
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

73 rows, 55 gated, 18 reported-never-gated. All 55 gated rows pass today,
including the eight this measurement added (`auto-5d`, `auto-5d-int`, `auto-8d`,
`use-4`, `line-40`/`-90`/`-94`/`-95`) — three of which pass for the wrong reason
(§3). The 10 rows added to the never-gated set are D-ARR-C's own targets
(`cap-40`, `cap-42`, `use-8`, `use-32`) and the `LINEMAX` residue (§4).

---

Related: [[arrdim-slice]], [[clearpool-slice]], [[arrays-dim-arc]],
[[answer-signoff-questions-by-measuring]],
[[gate-can-be-green-while-measuring-nothing]], [[kwsweep-msx1-denominator]].
