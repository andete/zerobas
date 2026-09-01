# D-CATFIX — the concat decline becomes the reference's single pass, and the count is 1 by construction

*2026-09-01. `basic/str-engine.asm` (`sct_err2`). Probes: `catterm_probe` (9
rows), `cattrail_probe` (4 rows, new), `catusr_probe` (5 rows, side-effect
COUNTER). **−21 B low region** (127 → 106). Closes the arc D-STRTM filed,
D-CATTM narrowed, D-CATUSR counted, and D-CATTM3 answered.*

## 1. The mechanism, recapped from D-CATTM3

`sct_err2` (a `+` committed the expression to concatenation, but the operand is
not a string form) used to arm a deferred TM and **decline** (NC). The driver
then re-drove the text numerically — and the D-NUMSTR factor defers on a string
literal **without consuming it**, so the re-driven expression ended at the
quote and the operand was evaluated **zero** times: `"AB"+(0*(1/0)+1)` read 13
where both references say 11, and `catusr`'s counter read 0 against the
references' 1. The reverted eval-in-place fix counted 2 because the decline
path was re-entered.

## 2. Measured before writing (cattrail, new rows)

| row | | VG-8020 | CF-3300 | zerobas |
|---|---|---|---|---|
| `t.vartrail` | `PRINT A$+` | ERR 24 | ERR 24 | **13** 🔴 |
| `t.littrail` | `PRINT "AB"+` | ERR 24 | ERR 24 | **13** 🔴 |
| `t.colon` | `PRINT "AB"+:C=9` | ERR 24 | ERR 24 | **13** 🔴 |
| `p.leak` | `PRINT "AB"+5` output | ERR 13, no `AB` | same | same ✅ |

A **missing** operand after `+` is ERR 24 (the D-MISSOP "slot ends where a
value was needed" rule) — three more divergences the old shape owned. And
`p.leak` pinned the constraint the fix must keep: the item must **not** print
before the error.

## 3. The fix: never decline

`sct_err2` now mirrors the reference's single pass:

- operand slot **ended** (EOL/`:`) → `penderr_set(FPERR_MISSOP)` — ERR 24;
- otherwise **evaluate the operand once** (`call eval` — its own fault lands in
  FPERR first), then `penderr_set(10)` — first-error-wins keeps the operand's
  code, so DZ beats the type conclusion exactly as the reference's evaluation
  order produces;
- return **CF=1 with R (the partial result) as the value** — the driver never
  re-drives, so the count is 1 *by construction, not by precedence*.

Two design points that came from reading, not guessing:

- **FPERR, not TMISMATCH**: `ems_print` checks `check_fperr_only` *before*
  emitting the item, so arming through `penderr_set` is what keeps `AB` off
  the screen for `PRINT "AB"+5`. `type_mismatch_set` is gone from this site.
- **No `check_expr_errors` precedence change** — the D-TMFP measured rows are
  untouched, because matching the reference's *evaluation order* makes the
  existing first-error-wins produce the right code.

## 4. After

| probe | before | after |
|---|---|---|
| `catterm` (9 rows) | 1 DIFF (`c.strfault` 13) | **0 — reads 11** |
| `cattrail` (4 rows) | 3 DIFF | **0 — ERR 24s** |
| `catusr` (counter) | `u.cat` = 0 | **1 — the references' count** |

`tools/filed-row-known.txt`: the two pinned rows leave the set per its own
rule (a known row that stops diverging is the CVI shape and must not linger).
Full battery green — string/penderr/tmfp/stmtpend acceptances all exercise
this path.

## 5. The arc's lesson

Four slices (D-STRTM → D-CATTM → D-CATUSR → D-CATTM3 → here), and the fix
itself was ~15 bytes. Everything expensive was establishing **which single
pass the reference runs**: half the original claim was stale, the stated
hazard was about a fix nobody needed, the count had to be measured with a side
effect because two mechanisms produce the same error code, and the paradox
dissolved only when the unconsumed quote was read off the factor. The bytes
were never the hard part.
