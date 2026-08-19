# TODO staleness sweep — 2026-08-09

**Subject:** every open (`- [ ]`) residual in [`TODO.md`](../TODO.md) that asserts a
concrete, checkable behavioural divergence. **Question:** is the claim still true
today, at `e2810c6` (D-EVALCHK)?

**Why this exists.** Prioritisation is done by reading residual TITLES written by
past slices and never re-run. On 2026-08-09 three stale entries were found *by
accident* while doing something else. A pickup list that cannot be trusted makes
every ranking decision unsound, so the list was re-measured rather than re-read.

**Result:** of the **17** open items that could be put to a machine, **6 are STALE**
(the divergence they assert no longer exists) and **11 are LIVE**. Two of the live
ones no longer read the way they were filed. One non-behavioural roadmap item
(line 2904) carries a behavioural parenthetical, and that parenthetical is stale
too.

---

## 1. Enumeration — how the denominator was built, and what was excluded

A hand-listed denominator is a scope claim, so this one is mechanical.

```
python3 - <<'EOF'      # over TODO.md at e2810c6
lines = open('TODO.md').read().split('\n')
idx = [i for i, l in enumerate(lines) if l.startswith('- [ ]')]
EOF
```

**56 open items** — the same 56 the memory index records for 2026-08-09. Every one
was read and classified into exactly one bucket:

| bucket | n | disposition |
|---|---|---|
| **behavioural, measurable through the REPL harness** | **17** | measured below (§3–§4) |
| behavioural, **NOT measurable this way** | 3 | §5, with the reason |
| apparatus / gate-limit / carve price / doc debt / scope / human judgement | 36 | not re-measured — §6 says why, per class |

The 36 excluded are excluded **by kind, not by convenience**: a carve price is a
claim about a design and a wall, not about a program; an apparatus limit is a
statement about the instrument; doc debt is doc debt. None of them has the shape
"program P reads X here and Y there", which is the only shape this sweep can
falsify. They are listed by line in §6 so the exclusion is auditable.

### 1.1 The partition is machine-checked, not asserted

"Auditable" is a weaker claim than "audited", so the audit was run: the line
numbers written into §3–§6 were read back out of this document and set against
the `- [ ]` lines of `TODO.md` at `e2810c6`.

| check | result |
|---|---|
| `- [ ]` lines at `e2810c6` | **56** |
| §3–§4 measured (17) + §5 not-measurable (3) + §6 excluded (36) | **56** |
| listed line numbers that are NOT a `- [ ]` at `e2810c6` | **0** |
| open items mentioned in NO section | **0** |
| items appearing in more than one bucket | **0** |

So the three buckets are **complete and disjoint over the real file**, not over a
list retyped from one. This is the check a hand-listed denominator normally
cannot pass [[a-hand-listed-denominator-is-a-scope-claim]]: the failure mode is
not a miscount, it is an item that was never looked at and leaves no trace of
having been skipped.

Every reading quoted below was likewise checked back against the raw captures —
**131 screen readings, 9 crunched-byte rows and 1 memory read**, each present
verbatim in this document (allowing for markdown pipe-escaping). No number here
was transcribed by hand.

⚠️ One item **outside** the 56 was measured anyway: the parenthetical inside line
2904 (*"`SWAP` itself is still unimplemented — `SWAP A,B` is a syntax error here,
where the reference swaps"*). It has the right shape and it is stale (§3.7).

## 2. Apparatus

* `rm -rf build && make repack-machine` from clean. **All four ROM hashes reproduce
  `e2810c6` exactly** — `basic-reloc 06a235e1`, `sub accce5a1`, `disk 2c630d3d`,
  `zerobas-main-eu a7ede5ed` — so every reading below is of the shipped tree and
  not of a stale or half-built one.
* A throwaway scratchpad driver over `probes/lib/omsx_repl.py` (`run_cases`,
  `result_span_after_echo`, `screen_tail`). **No committed probe was added** — this
  is a measurement of the list, not a new gate.
* Sides, exactly as the standing configuration:

  | side | machine | boot | step | reset | disk |
  |---|---|---|---|---|---|
  | `vg8020` | `Philips_VG_8020` | 8.0 | 2.5 | `NEW`,`CLS` | — (diskless) |
  | `cf3300` | `National_CF-3300` | 14.0 | 4.5 | ``,`SCREEN 0`,`NEW`,`CLS` | fresh /tmp copy of `disk/test720.dsk` |
  | `zb` | `C-BIOS_MSX1_EU_REPACK_DISK` | 8.0 | 2.5 | `NEW`,`CLS` | likewise |

* **Boot-per-case throughout.** Several rows resize the string pool or lower HIMEM
  (`CLEAR n,himem`), which persists and would decide the next case's reading.
* **A fresh disk image per row**, never the committed `.dsk`.
* **The VG-8020 is diskless and its refusal is not a reading.** File/disk rows
  (§4.1, §4.3, §4.5) are scored on the CF-3300 alone and are marked
  ONE-REFERENCE. Its `Syntax error` to `OPEN`/`FIELD`/`INPUT #n` is the absence of
  a disk controller and is never scored as agreement.
* **Every row has a positive control on the same fixture**, and every control was
  read on every side before any subject row was scored.
* **164 case-runs, 48 s of wall clock** for the main pass. Cheap enough that the
  cost of re-running this list is not the reason it went stale.
* **Three standing gates were RUN, not `grep`ed**, at `e2810c6` — this whole
  document exists because numbers were copied instead of measured
  ([[a-prediction-copied-into-the-result-column]]):

  | gate | reading |
  |---|---|
  | `make editverb-acceptance` | **61/61** rows across 3 sides (2 reference) |
  | `make clearpool-acceptance` | **52/52** gated, **5** reported never gated |
  | `make lvfix-acceptance` | **18/18** scored, 22 cases, 5 positive controls, **4 DEFERRED** |

### 2.1 🔴 The first pass of two rows was blind to its own subject

`d.sum1`/`d.sum` (FIELD overflow) and `f.mixctl` (`INPUT#1,A$,B$`) were first
driven as DIRECT lines with the reporting `PRINT` last. In direct mode the error
lands on a line that is **not** the last one, so `screen_tail`, anchored on the
closing `PRINT`, could not see it: the CF-3300 read ` 200  0 ` instead of
`FIELD overflow`, and zerobas read `[HI]` instead of `Syntax error`. Both would
have been scored **STALE**.

The tell was that ` 200  0 ` is *consistent with* an abort between the two field
bindings — a value that agrees with the wrong hypothesis
([[readout-blind-to-its-own-subject]]). Re-driven as a stored program with `RUN`,
where the abort is the tail, both rows read exactly as filed. The direct-mode
readings are kept in §4.1/§4.3 because they are the evidence that the readout,
not the tree, was at fault.

---

## 3. STALE — the divergence no longer exists (6 items + 1 parenthetical)

### 3.1 `LIST <line>` / `LIST <from>-<to>` still list the whole program — line 6579

Program `10 A=1 / 20 B=2 / 30 C=3 / 40 D=4`, then the LIST form, reading the screen
between the echo and the prompt.

| row | command | vg8020 | cf3300 | zb |
|---|---|---|---|---|
| `l.all` 🟢 | `LIST` | `10 A=1\|20 B=2\|30 C=3\|40 D=4` | idem | idem |
| `l.line` | `LIST 20` | `20 B=2` | `20 B=2` | **`20 B=2`** |
| `l.range` | `LIST 20-30` | `20 B=2\|30 C=3` | idem | **idem** |
| `l.from` | `LIST 30-` | `30 C=3\|40 D=4` | idem | **idem** |

**STALE.** `ex_list` does not ignore its argument; all four forms match both
references. The entry's own note — *"D-LNREF made the ARGUMENT's bytes the
reference's … so the range is now sitting there crunched and unread"* — describes
a tree that no longer exists: **D-LSTRNG shipped `LIST <range>` on 2026-08-02**
and line 2904 says so, five thousand lines further up the same file. The pin
`lnrd-list` (`1 0` on all three sides) is about the crunch and was never going to
notice.

### 3.2 `AUTO` / `RENUM` / `LLIST` are still not executed — line 5796

The entry's own program, verbatim:

| row | program | vg8020 | cf3300 | zb |
|---|---|---|---|---|
| `e.ctl` 🟢 | `10 A=1` / `20 A=2:END` / `GOTO 20` / `PRINT"[";A;ERR;"]"` | ` 2  0 ` | ` 2  0 ` | ` 2  0 ` |
| `e.renum` | …`RENUM 100` / `GOTO 110` / `PRINT"[";A;ERR;"]"` | ` 2  0 ` | ` 2  0 ` | **` 2  0 `** |
| `e.renumlst` | …`RENUM 100` / `LIST` | `100 A=1\|110 A=2:END` | idem | **idem** |

The filed reading was `zb -> A=0 ERR 8`, i.e. `RENUM` a syntax error and `GOTO 110`
landing on a line that never got renumbered. Today zerobas renumbers.

`AUTO` and `LLIST` cannot be put to a *reference* in this harness (interactive
line entry; an unplugged `LSTOUT`), so they are settled by the gate that owns
them rather than by this sweep: **`make editverb-acceptance` → 61/61 rows across 3
sides (2 reference)**, run at `e2810c6`, including the eleven `aut-` rows and the
twelve `llt-` printer rows.

**STALE — and it was already contradicted in its own file.** The closed
D-EDITVERB entry sits at the TOP of the same `TODO.md` (line ~40): *"`AUTO` /
`RENUM` / `LLIST` — the STATEMENT half, CLOSED 2026-08-06 … gated at 61/61."* The
open item and its own closure have coexisted for three days.

### 3.3 `dir-name` — a blank inside a name is not read back — line 5445

| row | program | vg8020 | cf3300 | zb |
|---|---|---|---|---|
| `n.ctl` 🟢 | `B11=7 : PRINT"[";B11;"]"` | ` 7 ` | ` 7 ` | ` 7 ` |
| `n.blank` | `B1 1=7 : PRINT"[";B11;"]"` | ` 7 ` | ` 7 ` | **` 7 `** |

Filed as `zb -> 0`. **STALE — fixed by D-NAMSPC on 2026-08-08**, whose rule is
exactly this one: a space inside a variable NAME is insignificant at *every*
reference, not just at the 9 lvalue targets. The residual predates it by a week
and was never revisited.

⚠️ The entry's second half — *"the whole `--say` surface is un-gated, ask what
else the say pass says"* — is an **apparatus** claim and is NOT closed by this
row. It is re-filed as its own item.

### 3.4 Numeric → string assignment raises the wrong error — line 6802

All seven forms the entry lists, plus the mirror it calls already-correct:

| row | program | vg8020 | cf3300 | zb |
|---|---|---|---|---|
| `q.ctl` 🟢 | `A$="x" : PRINT"[";A$;"]"` | `x` | `x` | `x` |
| `q.mirror` 🟢 | `A="x"` | `Type mismatch` | idem | idem |
| `q.lit` | `A$=1` | `Type mismatch` | idem | **`Type mismatch`** |
| `q.var` | `A=5` / `A$=A` | `Type mismatch` | idem | **idem** |
| `q.expr` | `A$=1+1` | `Type mismatch` | idem | **idem** |
| `q.len` | `A$=LEN("x")` | `Type mismatch` | idem | **idem** |
| `q.let` | `A=5` / `LET A$=A` | `Type mismatch` | idem | **idem** |
| `q.ary` | `DIM Q$(3)` / `Q$(0)=1` | `Type mismatch` | idem | **idem** |

Filed as `syntax error` on all seven. **STALE.** The entry already carried its own
closure — *"✅ D-MC-2 SIGNED OFF: folded into the MISSING-class slice"* — and the
MISSING class is recorded empty; the checkbox simply never moved.

### 3.5 `DIM Q(20000)` → `Out of memory` — line 3187

| row | program | vg8020 | cf3300 | zb |
|---|---|---|---|---|
| `dm.ctl` 🟢 | `DIM Q(10)` / `PRINT"[OK]"` | `OK` | `OK` | `OK` |
| `dm.big` | `DIM Q(20000)` | `Subscript out of range` | idem | **`Subscript out of range`** |

**STALE.** zerobas bounds the dimension before it allocates, exactly as the
references do. This is the same graduation the `clearpool` gate records: the `arr`
row `oos-dim-huge` moved from *reported-never-gated* to *gated* at `9a9a4c7`,
which is why `clearpool-acceptance` reads **52/52 (5 never gated)** and not
51/51 — see §7.

### 3.6 The prompt does not open a fresh line — line 2883

The reproducer is `CLS:PRINT "A";`. A trailing `;` leaves the cursor mid-row; the
claim is that the references break the line before their prompt and zerobas does
not. Screen rows 0–1, as scraped:

| row | program | vg8020 | cf3300 | zb |
|---|---|---|---|---|
| `p.nofresh` | `CLS:PRINT "A";` | `A` \| `Ok` | `A` \| `Ok` | **`A` \| `ZB`** |
| `p.ctl` 🟢 | `CLS:PRINT "A"` | `A` \| `Ok` | `A` \| `Ok` | `A` \| `ZB` |
| `p.long` | `CLS:PRINT "AAAAAAAAAA";` | `AAAAAAAAAA` \| `Ok` | idem | **`AAAAAAAAAA` \| `ZB`** |

Filed as *"zerobas paints `Azb>` on one row"*. It does not: the prompt is on the
next row on all three sides.

🎯 **`p.ctl` is what makes this a measurement and not a coincidence.** With the
`;` gone the cursor is already at column 0, and an *unconditional* newline would
show as a blank row between the payload and the prompt. No side has one. So both
the references and zerobas emit the newline **conditionally**, which is the
entry's own rule — the 2×2, not either row alone, is what separates "conditional"
from "always" ([[one-row-cannot-separate-two-rules]]). `p.long` exists so that a
prompt painted at the cursor could not be mistaken for a one-column scrape
offset.

**STALE.**

### 3.7 `SWAP A,B` is a syntax error here — the parenthetical at line 2904

| row | program | vg8020 | cf3300 | zb |
|---|---|---|---|---|
| `w.ctl` 🟢 | `A=1` / `B=2` / `PRINT"[";A;B;"]"` | ` 1  2 ` | ` 1  2 ` | ` 1  2 ` |
| `w.swap` | `A=1` / `B=2` / `SWAP A,B` / `PRINT"[";A;B;"]"` | ` 2  1 ` | ` 2  1 ` | **` 2  1 `** |

**STALE.** `SWAP` swaps. The control matters here: had `SWAP` errored, the `PRINT`
would still have run in direct mode and printed ` 1  2 ` — so the two dispositions
are distinguishable only because the control pins what "did nothing" looks like.

---

## 4. LIVE — still diverges (11 items)

### 4.1 `INPUT #n` parses only one target — line 715 · ONE REFERENCE

| row | program | cf3300 | zb |
|---|---|---|---|
| `f2.ctl` 🟢 | write `HI`, reopen, `INPUT#1,A$` | `HI` | `HI` |
| `f2.mixctl` | write `HI,LO`, reopen, `INPUT#1,A$,B$` | **`HILO`** | **`Syntax error in 50`** |

**LIVE**, exactly as filed. (Direct-mode first pass read `[HI]` — §2.1.)

🟢 **And a second, independent witness**: `lvfix-acceptance` carries `f.mixctl`
DEFERRED and printed `cf3300='HILO'  zb='<Syntax error>'` on the same tree in the
same session. A committed gate and a throwaway script agreeing is what says the
direct-mode `[HI]` was the readout's fault and not the tree's.

### 4.2 `VARPTR(<unset variable>)` is `Illegal function call` — line 727 · TWO REFERENCES

| row | program | vg8020 | cf3300 | zb |
|---|---|---|---|---|
| `v.ctl` 🟢 | `Q=1` / `X=VARPTR(Q)` | *(no error)* | *(no error)* | *(no error)* |
| `v.unset` | `X=VARPTR(Q)` | **`Illegal function call`** | **idem** | ***(no error)*** |

**LIVE**, exactly as filed — and corroborated by `lvfix-acceptance`, whose
`m.ctldrift` / `m.arydrift` rows are DEFERRED *on this very block* and printed
`vg8020='<Illegal function call>'  cf3300='<Illegal function call>'  zb='XYLLO'`.

### 4.3 `FIELD overflow` (ERR 50) against the record length — line 1077 · ONE REFERENCE

Over the default 256-byte RANDOM record, as a stored program:

| row | program | cf3300 | zb |
|---|---|---|---|
| `d2.sumok` 🟢 | `FIELD#1,200 AS A$,56 AS B$` (256) | ` 200  56 ` | ` 200  56 ` |
| `d2.sum1` | `FIELD#1,200 AS A$,57 AS B$` (257) | **`FIELD overflow in 20`** | ` 200  57 ` |
| `d2.sum` | `FIELD#1,200 AS A$,100 AS B$` (300) | **`FIELD overflow in 20`** | ` 200  100 ` |

**LIVE**, exactly as filed. (Direct-mode first pass — §2.1.)

### 4.4 `LOCATE`'s deferred error does not outrank its coercion — line 1138

| row | program | vg8020 | cf3300 | zb |
|---|---|---|---|---|
| `loc.defer` | `LOCATE 70000+0*(1/0),1` | **`Division by zero`** | **idem** | **`Overflow`** |
| `loc.div` 🟢 | `LOCATE 1/0,1` | `Division by zero` | idem | `Division by zero` |
| `loc.ovf` 🟢 | `LOCATE 70000,1` | `Overflow` | idem | `Overflow` |
| `loc.tm` 🟢 | `LOCATE "5",3` | `Type mismatch` | idem | `Type mismatch` |

**LIVE**, exactly as filed (and filed only yesterday, by D-EVALCHK, which fixed
the identical rule at `WIDTH` and declined the −29 B `loc_next` carve on scope).
All three controls green on all three sides.

### 4.5 `OPEN A$ AS #1` — line 1169 · ONE REFERENCE

| row | program | cf3300 | zb |
|---|---|---|---|
| `o.lit` 🟢 | `OPEN"TS.DAT"AS #1` / `CLOSE#1` / `PRINT"[OK]"` | `OK` | `OK` |
| `o.var` | `A$="TS.DAT"` / `OPEN A$ AS #1` / `CLOSE#1` / `PRINT"[OK]"` | **`OK`** | **`Syntax error in 20`** |

**LIVE**, exactly as filed, down to the line number in the message.

### 4.6 `ON ERROR GOTO 0` inside a handler must re-raise — line 1184 · 🔴 THE ZEROBAS FACE HAS CHANGED

| row | program | vg8020 | cf3300 | zb |
|---|---|---|---|---|
| `h.ctl` 🟢 | `10 ON ERROR GOTO 50` / `20 FOR A=1 TO 2` / `30 NEXT A(1)` / `40 END` / `50 PRINT"[TRAPPED]"` | `[TRAPPED]` then `No RESUME in 50` | idem | idem |
| `h.reraise` | …`50 ON ERROR GOTO 0` / `60 DIM A(3)` / `70 PRINT"[OK]"` | **`NEXT without FOR in 30`** | **idem** | **`Redimensioned array in 60`** |

**LIVE — the rule is unchanged and the reading is not.** The item records
`zb -> OK`. Today zerobas prints `Redimensioned array in 60`.

🎯 **Both readings say the same thing about the rule and different things about
the program.** The references never reach line 60; zerobas does. What changed
underneath is **D-NXARY** (2026-08-08): `NEXT A(1)` now AUTO-DIMS `A(0..10)` at
line 30, so line 60's `DIM A(3)` is a redimension. The swallow is intact — the
handler disarmed and execution continued — it now trips a *different, wrong*
error two lines later instead of running clean to `[OK]`.

⚠️ **For whoever picks this up: it is no longer a silent-swallow row.** A gate
written against the filed `OK` would fail on a tree that has not changed in the
respect being measured. `h.ctl` is the control that keeps the two apart: the trap
itself fires identically on all three sides, so the divergence is `ON ERROR
GOTO 0`'s and nothing else's.

### 4.7 `ex_let_arr_str` swallows an out-of-string-space — line 1236

| row | program | vg8020 | cf3300 | zb |
|---|---|---|---|---|
| `s.ctl` 🟢 | `CLEAR 200` / `DIM A$(5)` / `B$=STRING$(25,"A")` / `A$(1)=B$` / `PRINT"[";LEN(A$(1));"]"` | ` 25 ` | ` 25 ` | ` 25 ` |
| `s.aryoom` | `CLEAR 60` / `DIM A$(5)` / … / `A$(1)=B$` / `A$(2)=B$` / `PRINT"[OK]"` | **`Out of string space in 50`** | **idem** | **`OK`** |
| `s.scalar` 🟢 | `CLEAR 60` / `B$=STRING$(25,"A")` / `C$=B$` / `D$=B$` / `PRINT"[OK]"` | `Out of string space in 40` | idem | `Out of string space in 40` |

**LIVE**, exactly as filed, including the finding that makes it one: the SCALAR
store gets pool exhaustion right on zerobas, so this is specific to the
array-element store.

### 4.8 A line store is bounded by `TXTMAX`, not by HIMEM — line 3172

`A=PEEK(&HF676)+256*PEEK(&HF677)` then `CLEAR 300,A+1000`:

| row | reading | vg8020 | cf3300 | zb |
|---|---|---|---|---|
| `t.free` | `PRINT"[";FRE(0);"]"` | ` 148 ` | ` 148 ` | **` 646 `** |
| `t.ctl` 🟢 | store `99 REM Z`, `LIST` | `99 REM Z` | `99 REM Z` | `99 REM Z` |
| `t.oomlst` | also store a 32-byte line, `LIST` | `99 REM Z` | `99 REM Z` | **`20 REM BBBBBBBBBBBBBBBBBBBBBBBBBB` \| `99 REM Z`** |

**LIVE**, exactly as filed: 148 vs 646 free bytes, and the line the references
refuse is stored here.

### 4.9 `VALTYP $E0C8` reads `$FF` at cold boot — line 5439 · ZEROBAS-ONLY

Read as **memory**, not through BASIC: `capture=("mem_abs",[(0xE0C8,1)])` on a
case whose only line is `REM`, so no expression of ours evaluates first and writes
the cell. `E0C8 = ff`. **LIVE.** A hygiene item with no reference column by
construction — the cell is zerobas's own private one.

### 4.10 `RETURN` does not discard an open `FOR` — line 6526

| row | program | vg8020 | cf3300 | zb |
|---|---|---|---|---|
| `r.forret` | `10 ON ERROR GOTO 50` / `20 FOR I=1 TO 3:RETURN:NEXT` / `30 A=A+100:END` / `50 A=A+1:RESUME NEXT` | **` 102  0  1 `** | **idem** | **` 103  0  4 `** |
| `r.forerr` 🟢 | idem with `ERROR 7` for `RETURN` | ` 103  0  4 ` | idem | ` 103  0  4 ` |

**LIVE**, exactly as filed, control included — an ordinary trap is not the
variable, `RETURN` is.

### 4.11 `DEFINT` stores different bytes from the reference — line 6569

Read with `capture=("stored_line", TXTTAB)`; the body tokens after the 4-byte
header:

| row | typed | vg8020 | cf3300 | zb |
|---|---|---|---|---|
| `c.print` 🟢 | `20 PRINT 10` | `91 20 0f 0a 00` | idem | `91 20 0f 0a 00` |
| `c.defint` | `20 DEFINT 10` | `ac 20 0f 0a 00` | idem | **`97 49 4e 54 20 0f 0a 00`** |
| `c.defstr` | `20 DEFSTR 10` | `ab 20 0f 0a 00` | idem | **`97 53 54 52 20 31 30 00`** |

**LIVE**, exactly as filed for `DEFINT`: `$AC` vs `$97` + `"INT"`.

✅ **`DEFINT` half FIXED 2026-08-18 — D-DEFINTTOK**, pointer:
[`docs/lnref-msx1-characterization.md`](lnref-msx1-characterization.md) §4.
`20 DEFINT 10` now stores `ac 20 0f 0a 00` on zerobas too, matching `c.print`'s
own row shape above (real token, no literal ASCII tail). The `c.defint` row
above stands as taken; only its status changed. `DEFSTR` (below) is a
SEPARATE, still-open defect and was explicitly out of this fix's scope.

🔴 **And `DEFSTR` is worse than the entry says.** The item's own claim is only that
`DEFSNG`/`DEFDBL`/`DEFSTR` *"have no entry at all"* and work via `DEF_TOKEN` +
ASCII. But zerobas stores `97 "STR" 20 31 30 00` — the argument `10` survives as
**ASCII `"10"`** (`31 30`), where `DEFINT` on the same tree crunches it to the
integer literal `0f 0a`. So the divergence is two bytes wide and not one, and a
`LIST` round-trip is not the only thing that can see it. Recorded here; the
closing slice owns it.

---

## 5. NOT MEASURABLE THIS WAY — behavioural, but not by this instrument (3 items)

Stated rather than silently skipped.

* **`LOAD"CAS:"` accepts a tokenised tape — line 3162.** The faithful behaviour is
  a **HANG**: the VG-8020 searches past a non-ASCII header to the end of the tape
  and waits. `omsx_repl` raises `SystemExit` at its 240 s cap, so a row that hangs
  one side does not degrade a run, it kills it. The entry says this itself
  (*"NO ROW CAN CARRY THIS"*) and is filed for a judgement call — bug-for-bug
  fidelity costing a working feature — not for a fix. **Nothing to re-measure.**
* **`GET`/`PUT`/`FIELD`/`INPUT$` on a `CAS:` channel — line 4738.** Blocked on
  apparatus: `diskbasic_probe_lof.py` mounts a disk image per case and has no way
  to attach a tape, and no harness on either side drives both transports at once.
  It is also **not a divergence claim** — it records that modes 7/8 are INFERRED
  by analogy with `LPT:`/`CRT:` rather than measured, so there is no reading to
  falsify. Still open, still correct as filed.
* **A machine reset BETWEEN a RANDOM `PUT` and its `CLOSE` — line 4877.** Needs
  power cut mid-program; the harness reads the image after the machine exits
  normally. Filed as UNMEASURED, and it still is.

## 6. Excluded by kind — the 36 non-behavioural open items

Not re-measured, because none asserts "program P reads X here and Y there".
Listed by line as of `e2810c6` so the exclusion can be audited:

* **Apparatus / gate limits** (a stated limit of the instrument, not a defect in
  the tree): 323, 470, 632, 1314, 1321, 1338, 1343, 1386, 1394, 1401, 1458, 1468,
  5348, 5596, 5612, 6052, 6377, 6389.
  ⚠️ 5612 (*a trailing blank at end of line*) is the borderline one and it
  disqualifies itself in its own title: the cell is not stable enough to ground a
  rule and the echo guard `rstrip`s it away.
* **Carve prices / byte budgets** (a claim about a design and a wall — re-price
  from a clean build, do not re-run): 743, 6360, 6548.
* **Design / representation, no observable claim**: 1271 and 5404 (the two
  type-code namespaces — the chain's stored type byte is RAM-observable, but the
  item asks for a *collapse*, not for a reading), 3898, 4041, 5429.
* **Doc debt**: 3344, 4418.
* **Scope / sub-track / roadmap buckets**: 1833, 1924, 2116, 2119, 2899, 2904,
  2918, 3298.
  ⚠️ 2904's `SWAP` parenthetical *was* measured — §3.7 — and is stale. The bucket
  itself stays open.
  ⚠️ 3298 (D-LINEMAX) is measured already and awaiting sign-off; that is a
  decision, not a staleness question.

## 7. The `clearpool-acceptance` header was two numbers out of date

Not a residual, but the third stale figure found on 2026-08-09 and fixed in the
same commit. The `Makefile` header read *"51/51 gated rows, 6 reported-never-gated"*
and enumerated the six as `rep` (2) + `share` (3) + `arr` (1). The `arr` row is
`oos-dim-huge`, the `DIM Q(20000)` divergence of §3.5 — **graduated at `9a9a4c7`**,
and the gate has read 52/52 (5 never gated) ever since. Both the count and the
enumeration are corrected. §3.5 is the same fact measured from the other end.

The gate's own printout at `e2810c6`, which is where the corrected numbers come
from:

```
PASS  oos   oos-dim-huge   CLEAR 100:DIM Q(20000)      ref: 'Subscript out of range'
----  share hold-alias / hold-lit-prog / hold-lit-p25
----  rep   rep-fre0-200 / rep-fre0-4000

52/52 gated rows agree with the reference  (5 reported, never gated)
```

So the five are `share` (3) + `rep` (2), and the `arr` clause goes away entirely
rather than losing a digit.

## 8. What this says about the list

Six of seventeen — **35 %** — of the machine-checkable pickup list was asserting a
divergence that no longer exists, and every one of the six was fixed by a slice
that ran *after* the residual was filed and did not know it was closing it. Two
more are live but no longer read as filed, so nine of seventeen entries would have
misinformed the next reader in some way.

The three items still open in §5 and the eleven in §4 are now dated. **The pattern
is not "residuals rot"; it is "a residual is closed by a slice that was aiming at
something else, and nobody re-reads the list".** Every one of the six stale entries
was closable from evidence already inside `TODO.md` or inside a gate that runs on
every build:

**Each row below was verified to exist at `e2810c6`** — the pointer was read out
of the tree at that commit, not recalled:

| stale item | what already knew, in the tree at `e2810c6` | where | ✔ |
|---|---|---|---|
| 5796 AUTO/RENUM/LLIST | the D-EDITVERB `- [x]`, *"CLOSED 2026-08-06 … 61/61"* | same file, line ~40 | ✅ |
| 6579 `LIST <range>` | *"`LIST <range>` the same day with D-LSTRNG"* | same file, line 2904 | ✅ |
| 6802 numeric→string | *"D-MC-2 SIGNED OFF: folded into the MISSING-class slice"* | the entry's own last line | ✅ |
| 5445 blank in a name | `docs/spec-basic-namspc.md` + a `namspc-acceptance` target | the tree | ✅ |
| 3187 `DIM Q(20000)` | *"`arr` IS GONE (2026-07-29): … `oos-dim-huge` graduated into the gated `oos` battery"* | `basic_probe_clearpool.py:90` | ✅ |
| 2883 the prompt | — | only a measurement could | — |
| 2904 `SWAP` | — | only a measurement could | — |

Five of the seven were **derivable without booting an emulator**; two needed the
machine. So the cheap half of this sweep is a cross-check a slice could run at
landing time — *does anything in the pickup list name what I just shipped?* — and
the expensive half is what this document is for.

🔴 **AND THE `DIM Q(20000)` ROW IS THE SHARPEST OF THE FIVE, BECAUSE THE TREE
CONTRADICTED ITSELF ABOUT IT FOR TWO MONTHS.** `basic_probe_clearpool.py` has
said since 2026-07-29, in prose, that `arr` is gone and `oos-dim-huge` graduated
— `UNGATED = ("rep", "share")`, two buckets. The `Makefile` header six lines away
said *"6 reported-never-gated … `arr` (1)"*. One fact, two records, one of them
wrong, sitting side by side. Reading either one alone was enough to be confident
and wrong; only running the gate separates them
[[a-prediction-copied-into-the-result-column]].

🎯 **And that probe comment names this document's own conclusion, eleven days
early:** *"A never-gated bucket that outlives its reason is a gate that has
quietly stopped measuring what it claims to."* Swap "never-gated bucket" for
"open residual" and it is §8's thesis. The lesson was already written down by a
slice aiming at something else — which is, exactly, the failure mode.
