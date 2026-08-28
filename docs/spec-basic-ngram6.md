# D-NGRAM6 — seven sites open-coded a helper that already existed

*2026-08-28. Seven files. Probe `scratchpad/ngram6_probe.py`, arms
`scratchpad/ngram6_knives.py`.*

**Cost: −28 B, and no new body** — low 94 → 106 B free, page 1 299 → 315 B free
(the sites live in both regions). **Rows: 13, DIFF 0/13.**

## 1. The find

    ld a,(FPERR) / or a / jp nz,fp_runtime_error        7 B, seven sites

and `check_fperr_only` (`basic/interp.asm`) **already was that routine**, with
three callers. Each site becomes `call check_fperr_only`, 3 B. The sites:
`ex_let_arr`, `fch_check_d`, `exec_stmt`, `do_poke`, `ex_on_interval`,
`ems_print`, `ex_time_assign`.

🎯 **The cheapest carve is the one that adds nothing.** The sweep priced this at
20 B because it assumes a new helper has to be written; the real figure is 28 B
because the helper is already there.

⚠️ **THE ABORT PATHS ARE NOT LITERALLY IDENTICAL, WHICH IS WHAT THE ROWS ARE
FOR.** Open-coded, a fault jumps straight to `fp_runtime_error` with the caller's
frame intact. Through the helper it reaches `cee_abort_fp`, which pops the
helper's own dead return address first — a routine written for exactly this
("discard our own dead resume addr"). Net stack identical, and `fp_runtime_error`
resets SP from `SAVSTK` regardless.

## 2. 🔴 A ROW THAT RAISED THE RIGHT ERROR THROUGH THE WRONG LAYER

`A%=99999` raises ERR 6 and looked like the witness for the `exec_stmt`
statement-boundary site. **Under K-N6A it did not move.** Its error comes from
the LET store's *own* coercion check; the boundary check never sees it.

`PRINT 1E38*1E38`, `IF 1E38*1E38 THEN A=1` and `FOR I=1 TO 1E38*1E38` all move,
so those are the real witnesses. The vacuous row is **removed rather than kept
as a spare** — an agreeing row that agrees through a different layer is the
`ev_f_err` shape all over again. [[evferr-slice]]
[[a-case-that-agrees-can-agree-for-the-wrong-reason]]

Two earlier rows were vacuous the same way and for a duller reason: `A(1)=1E10`
and `A=1E10` raise **nothing** — `1E10` is fine in the float domain and these
sites check the *integer* coercion. They read `done` on all three sides while
appearing to witness two of the seven sites.

## 3. Falsification

| arm | requires | measured |
|---|---|---|
| **S1** (static) | 0 open-coded runs left in `basic/`, and exactly **10** calls to the helper | ✅ |
| K-N6A | neuter the helper (`or a` → `xor a`) → every subject row moves; the clean-path controls hold | 8/8 moved, 5 controls held |

⚠️ **S1's EXPECTED COUNT WAS WRONG FIRST TIME — I PREDICTED 7 AND IT IS 10.**
The helper had **three callers before this slice**, so "one call per site I
touched" was never the right number. Taken from `git show HEAD:` rather than
from my arithmetic.
