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

## D-CATGATE (2026-09-04) — nothing was watching this fix

D-CATFIX shipped 2026-09-01. On 2026-09-04 the `PRINT USING` arc's habit of
re-running a filed item's own rows before touching anything was applied to the
still-open concatenation entry, and both of its symptoms were gone:
`c.strfault` reads **ERR 11 on all three** (0/9 DIFF) and `u.cat` reads **1 on
all three**.

🔴 **THE OPEN ENTRY WAS A DUPLICATE, AND IT SAID 🤖 AUTONOMOUS.** Its written
design — *"`sct_err2` evaluates the operand … returns CF=1 … the count stays 1 by
construction"* — is exactly what D-CATFIX implemented. Following it would have
rewritten working code. **A written design in an open item is not evidence that
the work is outstanding.**

### The coverage was attached to the stale entry

Closing it was not free. **No probe under `probes/` carries
`"AB"+(0*(1/0)+1)` at all.** `catterm_probe` and `catusr_probe` were in
`filed_row_sweep`'s corpus *only because the open item cited them*, and that
sweep walks `- [ ]` items — so ticking the box would have removed the last thing
watching this fix.

⚠️ **AND IT WAS NOT THE `exit 0` CLASS.** Both probes already returned `rc=1` on
DIFF. The gap was the *other* filed one — **an honest `rc` that no battery
collects is not an oracle**. They needed collecting, not rewriting: promoted to
`probes/basic/` and wired as `make catterm-acceptance` / `make catusr-acceptance`.

### The mutation sweep — 4/4, and the two gates are not one gate

`scratchpad/catgate_blindness.py` undoes D-CATFIX three ways:

| mutant | plant | catterm | catusr |
|---|---|---|---|
| N1 | remove the one evaluation | **RED** | **RED** |
| N2 | arm the wrong error | **RED** | green |
| N3 | decline instead of `CF=1` | green | **RED** |
| N0 | **control:** comment-only edit | green | green, ROM byte-identical |

🎯 **N2 AND N3 REDDEN OPPOSITE GATES.** N2 changes the error code without
changing how many times the operand runs; N3 changes the count without changing
the codes. Neither probe is redundant, and that is measured rather than argued —
had one gate caught everything, the other would have been decoration.

### 🔴 N3's first plant was wrong and the code was fine

It inserted `or a` / `ret` **before** the `pop de`, which does not model
"decline instead of `CF=1`" — it models "return with an unbalanced stack", and
the rows still raised the right errors, so both gates stayed green and the arm
read FAIL. The real decline is one instruction: the `scf` that makes the return
success-shaped becomes `or a`.

That is the **third** mispredicted plant of the session (K-PC4, K-PL3, N3), and
every one of them was a fault in the arm rather than in the code under it. Twice
the must-hold list is what said so; here it was the must-move list going quiet.
