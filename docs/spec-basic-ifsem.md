# D-IFSEM — a false `IF` was caught by a nested `IF`'s `ELSE`

*Fixed 2026-09-02. **+27 B** on main page 1 (299 → 272 B free). 4 divergent rows
closed, 16/16 agree. Probe: [`probes/basic/basic_probe_ifsem.py`](../probes/basic/basic_probe_ifsem.py),
gated by `make ifsem-acceptance`. Knives:
[`scratchpad/ifsem_knives.py`](../scratchpad/ifsem_knives.py).*

## 1. Why `IF` was reviewed at all

Joost's standing tier: *when the 🤖 queue drains, review each statement's
implementation in full*. The queue drained this day. The worklist's thin section
was already walked, so what remained was the **"covered by an arc under another
name"** groups — with its own instruction: **verify the arc actually reads the
MECHANISM before trusting the name.**

`IF` fails that test badly:

* its claimed cover is *"interp.asm core: lineerr + unit tests"* — and `lineerr`
  is about **line entry**, not statement execution;
* `lnblank` has four ELSE rows (`expk-else`, `ref-else`, `lnr-else`,
  `lnrd-else`) but they are about how ELSE **crunches**;
* there is no `spec-basic-if.md`;
* `IF` appears across dozens of probes as **fixture scaffolding**, and
  `direct_ctrl`'s single `if_then` row was the entire execution surface.

**A statement the whole battery leans on was measured by almost nothing.**

## 2. What the read flagged, and what survived it

Two mechanism smells came out of reading `ex_if`, `if_skip_to_else` and
`tok_skip`:

* **S1 — no type check on a string condition.** Truthiness is
  `FACTYP==2 ? DE : (FAC lead byte != 0)`, and `sysvars.inc` says FACTYP is
  `2=int / 4=single / 8=double` — **there is no string value**, so a string
  condition cannot be recognised there.
  ⇒ **REFUTED, and recorded as a no-finding.** `IF A$ THEN`, `IF "" THEN` and
  `IF "X" THEN` all raise `Type mismatch` on **all three machines**: `eval`
  rejects a string condition before truthiness is ever reached.
* **S2 — dangling `ELSE`.** `if_skip_to_else` was `ld c,ELSE_TOKEN` falling into
  the shared flat `tok_skip_to`, which stops at the **first** ELSE token with no
  IF-nesting awareness. ⇒ **REAL.**

🟢 **`tok_skip` ITSELF IS SOUND AND IS NOT THE BUG** — it is quote-aware
(`tsk_str`), REM-aware, DATA-aware and carries the float-mantissa strides, i.e.
the D-DATACOLON lesson visibly applied. Recorded so nobody re-walks it on the
same suspicion.

## 3. The defect

| row | VG-8020 | CF-3300 | zerobas (before) |
|---|---|---|---|
| `B=9 : IF 0 THEN IF 1 THEN B=1 ELSE B=2` | **9** | **9** | **2** |
| `…ELSE B=2:B=B+100` | **9** | **9** | **102** |
| `B=9 : IF 0 THEN IF 1 THEN B=1 ELSE B=2 ELSE B=3` | **3** | **3** | **2** |
| `B=9 : IF 0 THEN IF 0 THEN B=1 ELSE B=2 ELSE B=3` | **3** | **3** | **2** |

A false outer `IF` fell into the **nested** `IF`'s `ELSE` and executed it — and
then carried on through the rest of the line.

## 4. 🔴 Two rules fit, and only one row separates them

The first two rows are explained equally well by:

* **R1** — *"a false `IF` ends the LINE"*; any later ELSE is dead.
* **R2** — *"the scan COUNTS NESTING"*; each nested `IF` consumes one `ELSE`, so
  an ELSE at the outer level still catches.

Both predict `9`. **`n.outerelse` is the row that separates them**, and the
references answer **3** — the outer ELSE *does* catch. **R2.** Implementing R1 on
the strength of the first two rows would have shipped a second defect, and the
rows to catch it would not have existed.

## 5. The fix

`if_skip_to_else` becomes a nesting-aware scan: count `IF_TOKEN` ($8B), and on
`ELSE_TOKEN` ($A1) either consume it against the depth or stop.

```
if_skip_to_else:
                ld      b,0                 ; nested-IF depth
ifs_lp:         ld      a,(hl)
                or      a
                ret     z                   ; end of line -> no ELSE for us
                cp      ELSE_TOKEN
                jr      z,ifs_else
                cp      IF_TOKEN
                jr      nz,ifs_step
                inc     b                   ; a nested IF claims the next ELSE
ifs_step:       call    tok_skip
                jr      ifs_lp
ifs_else:       ld      a,b
                or      a
                jr      nz,ifs_nested
                ld      a,ELSE_TOKEN        ; the caller tests A -- restore it
                ret
ifs_nested:     dec     b
                jr      ifs_step
```

🟢 **`tok_skip_to` is untouched** — `DEF FN` is its other caller (`C=COLON`) and
wants the flat scan. The token-awareness comes for free from `tok_skip`, so a
literal `"IF"`, an `IF` inside `REM`, and a `DATA` body cannot be miscounted.

## 6. Result

**16/16 rows agree** across VG-8020, CF-3300 and zerobas, from 4 DIFF. Six
controls hold throughout, including float truthiness (`IF .5`, `IF -.5` → true)
and the plain no-nesting `ELSE`, which is what says the fixture can express the
question at all.


## 7. Gated, and the gate is knifed

The rows live in `probes/basic/basic_probe_ifsem.py` and run as
`make ifsem-acceptance`, collected by `make gates` (64 of 69 acceptance targets
collected, 5 excluded with reasons). **`battery-membership-check` caught the new
target before I did** — a suite nobody runs fails silently, and it refused the
tree until the target was added to the battery list.

⚠️ **THE SCRATCHPAD COPY WAS DELETED RATHER THAN LEFT BESIDE IT.** Two copies of
one probe is the `shared-body-check` class — a file that is authoritative in
neither place and drifts in both.

Two knives, each rebuilt clean, ROM-hash guarded:

| arm | plant | gate |
|---|---|---|
| **K-IF1** | the original FLAT scan | **RED** ✅, 6 rows move |
| **K-IF2** | 🎯 the WRONG fix — *"a nested IF ends the line"* | **RED** ✅, 6 rows move |

**K-IF2 is the one worth having.** R1 fits `n.dangle` and `n.after` exactly, so a
gate built only from the rows that first showed the defect would have passed a
wrong repair. It reddens, which is what says the row set is thick enough to
reject a plausible wrong fix and not merely a missing one.

⚠️ I predicted BOTH arms' row sets wrongly — K-IF1 also moves the depth-2 rows
(obvious in hindsight: a flat scan fails at every depth), and K-IF2's set was
mis-guessed too. The arms were written to accept a superset provided the gate
still catches, which is what saved the verdict.
