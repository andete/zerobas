# D-STRLONG — the STRMAX clamp raises instead of truncating, and the error tail rejoins the fold

*2026-08-28. Subject: `sh_append` (`sub/strheap.asm`) and `str_concat_tail`
(`basic/str-engine.asm`). Filed by D-CONCATPEAK
([`docs/spec-concatpeak.md`](spec-concatpeak.md) §8) as a pre-existing
divergence found while testing a path its own rows never reach.*

**Cost: page-0 low region +2 B (68 → 70 free), page 1 −1 B (186 → 185),
sub page 0 −6 B (2335 → 2329).** The slice GIVES BACK low-region bytes: the
error tail it rewrites is shorter than the one it replaces.

**Rows: `scratchpad/strlong_probe.py`.** ⚠️ **THE DENOMINATOR GREW DURING THE
SLICE AND THE TWO READINGS ARE NOT ON THE SAME ONE.** The first run had **17
rows and 14 DIFF** (`/tmp/zerobas/sl_run1.out`); §6's diagnosis added four more,
and the final run has **20 rows and 3 DIFF** (`sl_run4.out`). The like-for-like
comparison is knife **K-SL0**, which reverts BOTH sites and re-reads the 20-row
set: it moves **13** rows, every one of them away from both references, so on
one denominator the slice is **16 DIFF → 3 of 20**. ⚠️ **7 rows do not move
under the full revert** and therefore prove nothing about the fix on their own —
which is what K-SL4 and K-SL5 exist to cover. Knives: `scratchpad/strlong_knives.py`.

---

## 1. What was filed, and it was right

    sh_append clamps a combined length over 255 to 255, and its header calls
    that "reference left-to-right truncation" -- which is exactly what both
    references do NOT do.

All four filed rows reproduced on the first run, unchanged. That is worth
saying out loud, because on this project the filing is wrong more often than
the code — four false in-source justifications were found in the two days
before this one. Here the filing held and the SOURCE COMMENT was the false
part.

## 2. The measured surface, before

| row | vg8020 | cf3300 | zerobas |
|---|---|---|---|
| `CLEAR 900:X$=STRING$(200,"A")` → `LEN(X$+X$+X$)` | `String too long` | `String too long` | **255** |
| the same → `RIGHT$(X$+X$,3)` | `String too long` | `String too long` | **`AAA`** |
| `X$=STRING$(128,"A")` → `LEN(X$+X$)` | ERR 15 | ERR 15 | **ERR 14** |
| `X$=STRING$(200,"A")` → `LEN(X$+X$)` | ERR 15 | ERR 15 | **ERR 14** |

**14 of 17 rows diverged.**

## 3. TWO DEFECTS, AND THE FILING SAID SO WITHOUT SEPARATING THEM

> D1 **silent clamp** — the pool is big enough for the truncated result, and
> zerobas returns it.
> D2 **error precedence** — the pool is not, and zerobas reports
> `Out of string space` where the reference reports `String too long`.

🎯 **THEY ARE SEPARATED BY ONE KNOB, SO THE ROW SET SWEEPS IT.** Fix a single
over-255 concatenation (`X$` of 128, so `X$+X$` is 256 — one byte over) and vary
only `CLEAR`. The reference answer is `String too long` at *every* pool size, so
whatever zerobas says is attributable to the pool and nothing else:

| `CLEAR` | zerobas, before |
|---|---|
| 200, 300 | `Out of string space` — **D2** |
| 400, 500, 600, 900 | `255` — **D1** |

The crossover lands where the mechanism predicts to the byte: `X$`'s body (128)
+ the operand-1 snapshot (128) + D-CONCATPEAK's in-place extension (127) = 383,
so 400 fits and 300 does not.

## 4. THE FIX FOR D1 IS SITED BEFORE EVERY ALLOCATION, AND THAT IS WHAT ALSO MOVES D2

`sh_append`'s very first act is `add a,c` — the combined length — and until now
the carry out of it was answered with `ld a,255`. It is now answered with
`SH_ERR = 3`, mapped by main's `sct_append_err` to `FPERR_STRLONG`
(= `FPERR_MISSOP + 1`, defined relatively because `fperr_to_err` is a DENSE
table whose codes move with the `CLEARPOOL` switch) and thence to ERR 15.

Because the test precedes `sap_try_extend` and `heap_alloc`, the raise costs no
pool and leaves R valid. **That is why four of the six D2 rows fixed themselves**:
at `CLEAR 300` the snapshot still fits, so the length is now reached and
reported before the allocation that used to fail first.

## 5. WHAT DID NOT FIX, AND WHY IT IS A DIFFERENT SITE

**3 rows still diverge** — `f.128`, `f.200`, `s.200` — and all three are one
residual: the pool is smaller than **2 × lenR**, so `str_concat_tail`'s
operand-1 snapshot exhausts it *before `sh_append` is ever entered*. The
reference never makes that copy; it compares the two lengths and raises.

⚠️ **THE DEFAULT POOL IS 200 B** (`FRE("")`, and all three sides agree on it),
which is why two of the four originally filed rows sit inside this window. It is
not an exotic corner.

🔬 **The route is measured, not guessed, and it is NOT cheap.** The snapshot is
unconditional because operand 2's evaluation can clobber the shared `RVDESC`.
But only the *descriptor* is at risk, never the body: a var slot and a temp slot
are both stable, and a literal's `RVDESC.ptr` points into the token stream,
which nothing moves. So the check could be hoisted above the snapshot by saving
operand 1's 3-byte descriptor rather than copying its body — a restructure of
the concat spine, with its own peak consequences. **Filed, not taken here.**

## 6. 🔴 THE FIX EXPOSED A DEFECT THAT WAS NEVER ABOUT LENGTH

With D1 fixed, `LEN(X$+X$+X$)` returned **`Type mismatch`** — a NEW wrong
answer, and the run said so before anything was committed.

`sct_append_err` returned to the caller with `HL` just past the operand that
FAILED. Any `+ term` still to its right was left in the text, and the caller
re-drove it as a numeric continuation. So the statement reported the type of the
leftover fragment instead of the error that actually happened.

🎯 **IT WAS NEVER SPECIFIC TO THE NEW ERROR CODE, AND THE PROBE PROVES IT
RATHER THAN ASSERTING IT.** Row `x.oom3` reaches the identical tail through a
plain pool OOM (`SH_ERR = 1`) on code that predates this slice entirely:

| row | vg8020 | cf3300 | zerobas, D1 fixed only |
|---|---|---|---|
| `x.oom2` `CLEAR 250:X$=STRING$(100,"A")` → `LEN(X$+X$)` | `Out of string space` | idem | `Out of string space` |
| `x.oom3` the same → `LEN(X$+X$+X$)` | `Out of string space` | idem | **`Type mismatch`** |

Nothing pending: correct. One term pending: wrong. **Pre-existing, and only
reachable-in-practice because D1's fix made the first append fail where it used
to succeed.**

**The fix is to rejoin the fold, not to leave it.** `penderr_set` is already
first-error-wins, so the remaining terms may be consumed — and appended, and
fail again — without changing what is reported, and the normal exit publishes R
and the final cursor exactly as on the success path. That deletes the tail's own
`STRPTR` store, its `scf` and its `ret`, which is where the low region's +2 B
comes from.

## 7. FALSIFICATION

Five knives, `scratchpad/strlong_knives.py`, each restoring every file it
touched via `try/finally` AND `atexit` (D-KNIFEGUARD).

| knife | cut | must move |
|---|---|---|
| K-SL1 | put the clamp back (`sub/strheap.asm`) | the over-STRMAX rows → 255 / `AAA` |
| K-SL2 | `FPERR_STRLONG` → `FPERR_STROOM` (`str-engine.asm`) | those rows → ERR 14 |
| K-SL3 | `db 15` → `db 14` (`interp.asm`) | the same, via a DIFFERENT site — proves the dense slot is the one indexed |
| K-SL5 | put the old `ret` back in the error tail | exactly the 4 pending-term rows → `Type mismatch`; the 3 with nothing pending must NOT move |
| K-SL4 | raise at ≥ 255 instead of > 255 | exactly `e.255` and `e.255x3` |

Measured (`/tmp/zerobas/sl_knives.out`, `sl_knives2.out`): K-SL1/2/3 move **10**
rows each, K-SL5 moves **exactly the 4 predicted** (`f.len3`, `x.long4`,
`x.longtail`, `x.oom3`) and leaves `f.right`, `x.oom2` and `e.256` alone, K-SL4
moves **exactly `e.255` and `e.255x3`**. K-SL2 and K-SL3 produce the SAME visible
movement from two different files — that is the point, not a redundancy: each
says its own site is load-bearing, and K-SL3 in particular is what says
`FPERR_MISSOP + 1` lands on the slot it is meant to.

🔴 **K-SL4 IS THE ONE THAT SCORES THE GREEN ROWS.** `e.255` and `e.255x3` are
legal 255-byte concatenations, green *before and after* the fix, so on their own
they prove nothing — a fix that raised one byte early would score perfect
everywhere else. K-SL5's split does the same job for §6: a knife that reddened
*all* the rows would not distinguish the pending-term tail from the raise.

## 8. THE APPARATUS FAULTS THIS SLICE FOUND IN ITSELF

- 🔴 **The echo fence only looked at zerobas.** A `v.assign` row put the failing
  concatenation in a SETUP line — which errors on all three sides, so the
  harness echoed the typed line and the row was NO READING anywhere. The fence
  now inspects every side, and the row is dropped rather than kept as a
  meaningless `SAME`. [[an-unnamed-outcome-reads-as-no-outcome]]
- 🔴 **The D1/D2 classifier had no arm for the FIXED state.** Every post-fix row
  printed `?`. A readout blind to its own subject, in the readout written to
  watch that subject change. [[readout-blind-to-its-own-subject]]
- 🔴 **THE KNIFE RUNNER HARDCODED THE ROW PREFIXES** — `("f","s","e","v","d")` —
  and §6 added an `x.*` family. It then read **16 of 20 rows** and scored K-SL5
  as moving ONE row where it moves FOUR, while its verdict line still said
  *"every claim has a live arm"*. 🎯 **The arm was live and the report was
  wrong**, which is the worse of the two failures: a dead arm announces itself,
  an understated one does not. A row set is a DENOMINATOR — the reader now
  matches the row shape instead of a list somebody has to remember to update.
  [[readout-blind-to-its-own-subject]] [[a-case-that-agrees-can-agree-for-the-wrong-reason]]
