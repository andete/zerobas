# D-ONDOM — `ON n GOTO/GOSUB`'s value domain: measured, and empty

*2026-08-30. Probe `scratchpad/ondom_probe.py`. **Measurement only — no code
change.** 15 rows, **0 DIFF**.*

## 1. Why look

`scratchpad/missop3_probe.py` covers `ON 1 GOTO` with the target list **missing**.
Nothing covered the **selector's** domain: what `n` may be, what happens when it
selects past the end of the list, and what a non-integer or out-of-range `n` does.

⚠️ **The interesting half is the half that does not raise.** `n` outside the
list's range simply falls through to the next statement — so a wrong answer here
would be **silent** (no branch, or the wrong branch), with no error code to
notice. That is the class this project ranks worst, and it is exactly the kind of
surface that had one row of coverage in `VAL`.

## 2. The result

| shape | all three sides |
|---|---|
| `ON 1 GOTO 60` · `ON 2 GOTO 40,60` | branches, correct target |
| `ON 3 GOTO 60` (past the list) · `ON 0 GOTO 60` | **falls through**, no error |
| `ON -1 GOTO 60` | ERR 5 |
| `ON 256 GOTO 60` | ERR 5 |
| `ON 32768 GOTO 60` | ERR 6 |
| `ON 0*(1/0)+1 GOTO 60` | **ERR 11** — the selector's own fault wins |
| `ON 1 GOSUB` / past-the-list `ON 5 GOSUB` | branches / falls through |

**0 DIFF of 15.** zerobas already matches a VG-8020 and a CF-3300 across the
whole surface, including the silent fall-through cases.

🎯 **And one row settles a rule worth having written down: the selector
TRUNCATES, it does not round.** `ON 1.7 GOTO 40,60` takes the **first** target on
all three machines (`ERR 8`, because line 40 does not exist in the fixture) — a
rounding selector would have taken the second. `ON 1.4 GOTO 60,40` agrees but
cannot discriminate, which is why the 1.7 row is the one that matters.

## 3. Why record an empty class

Nothing was fixed, and that is the point. This project keeps a
**CLASSES MEASURED EMPTY** list so a surface is not re-measured on a hunch, and
so the next person asking *"is `ON n` right?"* gets rows instead of an opinion.

The ordering twin (`o.pend`) is included for the same reason every slice this
week carries one: a verb can be right about its clean cases and wrong about a
pending fault, and only that row separates them. Here it is right.
