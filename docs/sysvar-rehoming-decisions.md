<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# The RE-HOMING class — a DECISION per published name

Ten variables carried a published MSX work-area **name** (or its **semantics**)
at a **private zerobas address**. This document records, once, a decision for
each: honour the published address, or state why not.

Spec [`spec-basic-sysvar-rehoming.md`](spec-basic-sysvar-rehoming.md) (sign-off
in §9), measurement [`sysvar-msx1-coverage.md`](sysvar-msx1-coverage.md),
probe [`../probes/basic/basic_probe_sysvarsweep.py`](../probes/basic/basic_probe_sysvarsweep.py).
Reproduce every number below with:

```bash
make sysvarsweep ONLY=s1-err,s6-armed,s7-fired,s8-str4,s9-str20,s10-defint,s11-defstr,s12-scal1,s13-scal3
```

**The decision itself lives beside each equate in
[`../basic/sysvars.inc`](../basic/sysvars.inc)** — that is the deliverable. This
file is the reasoning the comments point at.

---

## 0. 🔴 The filed framing was wrong in two ways, and one of them was in the repo the whole time

The item was filed as *"8 published names at private addresses, and **nobody
decided that**"*.

**Nobody decided it for nine. For `VALTYP` somebody did** — measured it, wrote it
down, and oracle-locked it — in [`../basic/usr.asm:19`](../basic/usr.asm:19):
zerobas is integer-only, does not use MSX's DAC/`VALTYP` argument protocol, and
*"the reference … sets `VALTYP` (`$F663`) `=$02`"* was established by black-box
differential against the VG-8020
([`../probes/basic/basic_probe_usr.py`](../probes/basic/basic_probe_usr.py)).

> **So the class was never "eight undecided placements". It was "ten placements,
> some already decided somewhere the next person will not find it, and none
> decided at the equate."** That does not shrink the work — the deliverable was
> always "record it where the reader looks" — but it is the second independent
> instance, after `$F414`, of *the repo knowing something its own `sysvars.inc`
> does not say*.

And the second: **"per variable" is the wrong unit.** `ARYTAB $F6C4` is not read
alone; the published contract is the chain `TXTTAB ≤ VARTAB ≤ ARYTAB ≤ STREND`,
which this repo already sources as a set
([`../basic/docs/spec-bload-r.md:68`](../basic/docs/spec-bload-r.md:68)). Signed
off: **decide per variable, reason per group.**

⚠️ A third premise, from the brief itself, is also not binding: *"low is 23 B and
page 1 is 8 B"*. **Every honoured move below cost ZERO ROM bytes** — all access
was already through the symbol, so an `equ` change is an assembler constant, and
the post-change build reports the identical `low = 23 B / page 1 = 8 B`. Space
was a cost only for the mirroring option, which is not used.

---

## 1. What was measured, and how it could have gone wrong

Four **paired** stimulus states were added to the sweep, each pair differing in
exactly the property under test, so the reading is a **delta** and not a value
comparison — which is what makes it a *semantics* test rather than a name match.

| Pair | Payloads | Separates |
|---|---|---|
| `s6-armed` 🟢 / `s7-fired` | `ON ERROR GOTO 100` with line 20 = `STOP` vs `GOTO 99999` | **armed** state from **fired** state |
| `s8-str4` 🟢 / `s9-str20` | `STRING$(4,66)` vs `STRING$(20,67)` | an allocation **pointer** from a boundary |
| `s10-defint` 🟢 / `s11-defstr` | `DEFINT A` vs `DEFSTR A` | the type **encoding** |
| `s12-scal1` 🟢 / `s13-scal3` | one scalar vs three | a **pointer chain** step |

Ordering was non-negotiable: **all eight ran on both references at `--repeat 2`
before zerobas was run on any of them** (`--sides vg8020,cf3300`, a filter added
for exactly this, so the discipline is a mechanism and not a promise). The echo
guard ran on **every side including zerobas**, and here it is stronger than
delivery — `break in 20` vs `break in 100` names the **branch taken**, so a state
that arrived perfectly and did not trap is caught; `[ 0 ]` vs `[]` *is* the type
decision, printed.

**Apparatus controls, all fired:** `C-REPRO` (re-finds the filed `$F414` row
unaided) · `C-PRIV` 🆕 (the new private-memory segments must be shown to **move**
— pinned on `DEFTBL` between the two `DEF` states) · `C-REPRO-2` 🆕 (the table
must re-derive **both halves** of `$F414`/`$E1C5`, which the coverage doc could
only make one half of) · `C-INSTR` · the jittered volatility control.

### 🔴 The measurement corrected the source twice, and the lattice once

1. **`DEFTBL` is not an own-design encoding.** `DEFTBL_STR equ 1` reads like a
   0/1 sentinel. Measured, zerobas' 26-byte table is **byte-identical** to both
   references — boot `08` (double) ×26, `DEFINT A` → `02` — and **exactly one
   value differs**: `DEFSTR A` gives `03` on both references and `01` here.
2. **`VALTYP` is unobservable, not merely unhonoured.** Both references hold a
   constant `03` at `$F663` in **all nine states**. Its value at any instant a
   `PEEK` could run is an artifact of the line editor, not of the stimulus. The
   same is true of `SAVTXT`, pinned at `$F40F` on every capture.
3. 🔴 **`NO-ORACLE` is a verdict about the COMPARISON, not about the variable.**
   `FRETOP` was reported `NO-ORACLE` because the two references hold different
   absolute values (`$F168` vs `$DC5F`) — their string spaces begin in different
   places. **They agree perfectly on the quantity that carries the meaning:**
   both move **−4** for a 4-byte string and **−20** for a 20-byte one. An
   absolute comparison of a pointer into machine-dependent RAM can only ever
   answer "the machines disagree", which is true and is not what was asked. A
   `SAME-DELTA` verdict was added; zerobas moves **−4 / −20** too.
   ⚠️ **D-SYSVAR's 311-byte `NO-ORACLE` bucket is re-filed on these grounds** —
   it was described there as "not measurable by this method", and that was the
   right words for the wrong reason.
4. 🔴 **A knife on the fix itself.** The first cut of the delta branch returned
   `DIFF-DELTA` for *every* one-sided movement, and `SAVSTK` showed it up: the
   references never move it here (`refsΔ=+0`) while zerobas writes a real SP
   anchor (`zbΔ=−3349`). "DIFF-DELTA" reads as *"zerobas moves it wrongly"* when
   the truth is *"the references do not move it here at all"*. The absolute
   branch had always said `ZB-ONLY` for that shape; **the two branches were
   answering the same question differently**, and the delta branch was the wrong
   one.

---

## 2. 🔴 The headline — seven of ten are measurably THE SAME VARIABLE

Not ten different designs placed for space. **The same design, at a different
address**:

| Variable | Verdict | The measurement |
|---|---|---|
| `ERRFLG` | **SAME-VAR** | `00→08` identical on all three sides, `s1-err` **and** `s7-fired` |
| `ERRLIN` | **SAME-VAR** | `0000→FFFF` direct-mode **and** `→0014` (=20) from a stored line — the 65535 convention included |
| `ONELIN` | **SAME-VAR** | `→$8015` byte-identical under `s6-armed` |
| `ARYTAB` | **SAME-VAR** | byte-identical in **all four** direct-mode states: `$8003→$800E→$8024`, `→$8009` |
| `DEFTBL` | **SAME-VAR** (25/26 B) | boot `08`×26, `DEFINT A`→`02`, on all three sides |
| `FRETOP` | **SAME-DELTA** | −4 and −20, on all three sides |
| `ONEFLG` | **SAME-ROLE** | refs `FF`, zerobas `01` — same job, different sentinel |
| `VALTYP` | **UNOBSERVABLE** | refs constant `03` across all 9 states |
| `SAVTXT` | **UNOBSERVABLE** | refs constant `$F40F` across all 9 states |
| `SAVSTK` | **NO READING** | `NO-ORACLE` absolutely, `refsΔ=+0` — the refs never move it here |

🟢 **The `s6`/`s7` control pair earned its place immediately, twice.** It is what
tells `ONELIN` (moves in **both** — armed state) apart from
`ONEFLG`/`ERRFLG`/`ERRLIN` (move in `s7` only). A single fired state would have
written all four up as "error state" — D-SYSVAR's own `s2-noerr` lesson, one
level deeper. **And it is what makes `ONELIN`'s one disagreement attributable**:
under `s7` the refs hold `$801C` and zerobas `$8019`, and the same 3-byte gap
appears in `ARYTAB` — because `20 GOTO 99999` **tokenises 3 bytes shorter on
zerobas**. The pointer is right; the text it points into differs. Without the
armed control, `ONELIN` reads `SAME-ROLE` and looks like an encoding difference.

> ⚠️ **A row with a stored program measures the program, not the variable.** The
> `ARYTAB` rows under `s6`/`s7` conflate variable-area layout with tokenised
> length; the four **direct-mode** states are the ones that isolate `ARYTAB`.
> `s6` agreeing exactly is luck, not evidence.

---

## 3. The ten decisions

All ten published addresses were verified **PUB-FREE** by measurement: zerobas'
byte at each never moved in any of the nine swept states, so neither zerobas nor
C-BIOS claims it on the repack machine.

### ✅ HONOUR — five moved, at zero ROM cost

| Variable | was | now | Observer |
|---|---|---|---|
| `ERRFLG` (was `ERRCODE`) | `$E1C5` | **`$F414`** | `ERR` |
| `ERRLIN` (was `ERRLINE`) | `$E1C6` | **`$F6B3`** | `ERL` |
| `ONELIN` | `$E1C8` | **`$F6B9`** | `PEEK`: is a handler armed, and where |
| `ONEFLG` | `$E1CA` | **`$F6BB`** | `PEEK`: am I inside a handler |
| `DEFTBL` | `$F153` | **`$F6CA`** | `PEEK`: a letter's default type |

🔴 **MIRRORING IS REFUTED FOR THE ERROR PAIR, BY AN ALREADY-FILED MEASUREMENT.**
Sign-off admitted `MIRROR` (keep the private cell, also store to the published
address) as a verdict. It does not survive contact with the row that started this
whole arc:

```
POKE&HF414,0  then PRINT ERR       vg8020 -> 0      cf3300 -> 0
```

`ERR` **reads** `$F414` on a real MSX. A write-only mirror satisfies `PEEK` and
**fails** `POKE`. Only relocation satisfies both — so the option that looked like
the cheap way out of *"moving live error state is not a free edit"* was measurably
insufficient, and the edit turned out to be free anyway.

Two further notes, both recorded at the equates:

* `ERRCODE`/`ERRLINE` were **renamed** to the published `ERRFLG`/`ERRLIN`. The
  spelling is why the static name-match could not see them — the pair that
  *started* this item was invisible to the layer that found the other eight. A
  half-honoured variable at the right address under an off-book name is the same
  defect one step smaller.
* `ONEFLG`'s **sentinel** moved `1` → `$FF` with the address. Both readers test
  it with `or a`, and the single setter was `ld a,1`, so it is zero bytes and
  control-flow-neutral. Honouring the address while publishing a value no
  reference ever holds would have been the worse half of both options.

### ❌ REJECT-GROUP — two, and the group argument is the whole reason

**`ARYTAB $F6C4`** — `SAME-VAR`, byte-identical, and *still rejected*. zerobas
has no stored `VARTAB` (derived as `(PRGEND)+2`,
[`../basic/sysvars.inc:1577`](../basic/sysvars.inc:1577)) and **no `STREND` at
all**. A consumer computes array space as `STREND − ARYTAB`; publishing a
plausible `ARYTAB` beside two power-on zeros yields a **large negative length —
a confident wrong answer** — where today it gets `0 − 0` and an obviously dead
reading. That is the `TAB(` shape one level up: a partially-honoured contract
agrees with nothing and *looks* like it works.

**`FRETOP $F69B`** — `SAME-DELTA`, exact, and rejected for the same reason with
an extra one on top: **the measurement itself shows the absolute value carries no
portable meaning.** The two references disagree ($F168 vs $DC5F). Only the
*difference* against `MEMSIZ $F672` / `STKTOP $F674` is meaningful, and zerobas
has neither.

Both are filed with the exact next step: **cost publishing the whole chain.**
Neither is a defer-by-omission — the group is the reason, and it is stated.

### ❌ REJECT-UNOBSERVABLE — two

**`VALTYP $F663`** — the references hold a constant `03` at every capture
instant in all nine states. There is nothing at that address for zerobas to be
right about at any moment a `PEEK` could observe it. The one real observer is the
`USR` calling convention, and **that decision already exists, measured**
([`../basic/usr.asm:19`](../basic/usr.asm:19)): zerobas passes the argument in
`HL` and leaves DAC/`VALTYP` untouched, a deliberate own-design divergence.
Recording it at the equate is this slice's only change for `VALTYP`.

**`SAVTXT $F6AF`** — pinned at `$F40F` on every reference capture: by the time
the machine is back at a prompt it points at the line buffer, so its live value
is not reachable by this instrument, and no BASIC-visible channel reads it.

### ⏸ DEFER — one, with the settling measurement named

**`SAVSTK $F6B1`** — `NO-ORACLE` on absolute value (`$F09E` vs `$DB95`, two
different stack tops) **and** `refsΔ=+0` under every stimulus, so the delta
route does not rescue it either. It is not "different"; it is **unmeasured**.

> **What would settle it:** a stimulus that makes the reference *write* `SAVSTK`
> at a moment the capture can see — i.e. a capture taken **inside** a running
> statement rather than at a prompt (the `holds`/breakpoint mechanism
> `basic_probe_bload.py` already uses), not another direct-mode line.

---

## 4. Verified after the change

`make sysvarsweep`, all three sides, `--repeat 2`, **exit 0 — all five apparatus
controls green** (`C-INSTR`, `C-REPRO`, `C-PRIV`, `C-REPRO-2`, `C-VACATED`):

```
ERRFLG  pub=$F414  HONOURED   s1-err     SAME-VAR  refs=00->08  zb@pub=00->08
                              s7-fired   SAME-VAR  refs=00->08  zb@pub=00->08
ERRLIN  pub=$F6B3  HONOURED   s1-err     SAME-VAR  refs=0000->ffff  zb@pub=0000->ffff
                              s7-fired   SAME-VAR  refs=0000->1400  zb@pub=0000->1400
ONELIN  pub=$F6B9  HONOURED   s6-armed   SAME-VAR  refs=0000->1580  zb@pub=0000->1580
ONEFLG  pub=$F6BB  HONOURED   s7-fired   SAME-VAR  refs=00->ff      zb@pub=00->ff
DEFTBL  pub=$F6CA  HONOURED   s10-defint SAME-VAR  (26 B byte-identical)
C-VACATED: $E1C5 $E1C6 $E1C8 $E1CA $F153 — all QUIET
```

`ONEFLG` moved from `SAME-ROLE` to **`SAME-VAR`** — the sentinel change is what
did that. `ONELIN` under `s7-fired` remains `SAME-ROLE` for the tokenisation
reason in §2, and `DEFTBL` under `s11-defstr` for the `01`/`03` reason in §3;
both are filed below rather than papered over.

**Corpus after the change, all green:** `unit-test` 55/55 · `abort-acceptance`
49/49 · `linemax-acceptance` 60/60 · `lnblank-acceptance` **251/251 at
`--repeat 2` with the allowlist still EMPTY** · `array-acceptance` 149/151 (the
two standing rows, confirmed **by name**: `ifc.instr.zero`, `ifc.instr.neg`) ·
`badfnum` · `lof` · `chancost` · `diskbasic` · `bdos` · `fat-error` ·
`error-trap` · `stop`/`strig`/`key`-trap · `arrdim` · `clearpool`.
Build: **low 23 B, page 1 8 B — unchanged** — and dead-code `0/0` in both builds.

---

## 5. Filed by this slice

* 🔴 **`20 GOTO 99999` tokenises 3 bytes shorter on zerobas than on both
  references** — found as a side effect of the `ONELIN`/`ARYTAB` `s7` rows, which
  were aimed at something else entirely. Neither variable is at fault.
* **`DEFTBL_STR` should be `3`, not `1`** — both references store `03` for a
  `DEFSTR`'d letter. Deliberately **not** bundled with the address move: it
  changes a type-dispatch constant that is also a value *width* on the numeric
  side, and deserves its own knives.
* **D-SYSVAR's 311-byte `NO-ORACLE` bucket is re-filed** — for pointer-valued
  cells it is the method, not the machines, that fails to agree (§1.3).
* **The ownership generator matches COMMENTS.** `build_owner` rated `VALTYP`
  *BIOS-owned* because C-BIOS's `main.asm:1580` mentions it — in the header
  comment of `GETYPR`, whose body is a **stub that prints a debug string**. Had
  that verdict been taken at face value it would have been a reason to reject
  `VALTYP` for the wrong cause. The generator is labelled a generator everywhere
  it appears, and this is the first measured instance of it being wrong.
* **zerobas' private `VALTYP $E0C8` reads `$FF` at cold boot**, which is neither
  of its two documented values (`0` numeric / `1` string). Benign today (written
  before read), but it is not initialised.
* **`ERRTXT $F6B7`** has no zerobas counterpart as a stored cell (the resume text
  pointer lives in `ERRRESUME[2..3]`). Outside the observable error group
  (`ERR`/`ERL`), so untouched — and now stated rather than absent.
* The `$E1C5..$E1CB` bytes freed by the four moves are **not reclaimed**;
  `DIRECTF`, `SAVSTK`, `ERRRESUME` and `SAVTXT` still surround them.
