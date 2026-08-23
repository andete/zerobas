# D-CIRCMISS sibling round 2 — predictions, written BEFORE the probe was run

Written 2026-08-23 on `e23e350` (D-CIRCMISS shipped), ROMs
`abfefa7f` / `490ffc49` / `a8173c25`.

Round 1 measured 4 of 9 rows. This round fixes the instrument (fill colour ==
stop-box colour, so PAINT's `B`-defaults-to-`C` always terminates; a pre-marker
on the CLEAR rows) and adds the rows round 1 did not have.

Readout `[ERR R]`, R = `POINT(50,50)` — the seed. **4 = nothing filled,
15 = filled.** CLEAR rows print `0` in R by construction.

| row | statement | pred refs | pred zb | why |
|---|---|---|---|---|
| `p.colour`  | `PAINT(50,50),`        | `24 4`  | `0 15` | 🔴 measured in round 1, expected to reproduce |
| `p.kcolour` | `PAINT(50,50),:A=1`    | `24 4`  | `0 15` | 🔴 measured in round 1 |
| `p.b`       | `PAINT(50,50),15,`     | `24 4`  | `0 15` | the B slot — refs measured `24` in round 1, zb NOT MEASURED |
| `p.kb`      | `PAINT(50,50),15,:A=1` | `24 4`  | `0 15` | ditto |
| `p.cc`      | `PAINT(50,50),,`       | `24 4`  | `0 15` | ⚠️ NEW — `,,` reaches `ep_parse_b` by the OTHER route (`ep_c_empty`). LOW CONFIDENCE: could be `2` |
| `p.kcc`     | `PAINT(50,50),,:A=1`   | `24 4`  | `0 15` | ⚠️ NEW, same |
| `p.none`    | `PAINT(50,50)`         | `0 15`  | `0 15` | 🔴 THE TRAP: no comma at all |
| `p.omit`    | `PAINT(50,50),,15`     | `0 15`  | `0 15` | 🔴 THE TRAP: C omitted BETWEEN commas (green in round 1) |
| `p.plain`   | `PAINT(50,50),15`      | `0 15`  | `0 15` | control |
| `p.ok`      | `PAINT(50,50),15,15`   | `0 15`  | `0 15` | control — round 1's version failed on ALL THREE (colour clash), so this is the instrument fix under test |
| `q.trail`   | `CLEAR 200,`           | `24 0`  | **`0 0`** | refs measured `24` in round 1; zb NOT MEASURED. If CLEAR merely completes, `0`. ⚠️ If the machine DIED, `<NO OUTPUT>` again and the RAW dump is the deliverable |
| `q.kcolon`  | `CLEAR 200,:A=1`       | `24 0`  | `0 0`  | ditto |
| `q.comma`   | `CLEAR ,200`           | `0 0`   | `0 0`  | ⚠️ NEW control: the string space omitted is LEGAL (`clr_himem`) |
| `q.ok`      | `CLEAR 200`            | `0 0`   | `0 0`  | control, green in round 1 |

**Predicted: 14 printed, 14 scored, 6 DIFF** (`p.colour` `p.kcolour` `p.b`
`p.kb` `p.cc` `p.kcc`).

⚠️ **The prediction that matters most is `p.ok` + `p.plain` + `p.none`.** If
they are still `<NO OUTPUT>`, the instrument fix is wrong and nothing else in
this table may be believed.

⚠️ **`p.cc` / `p.kcc` are the LOW-CONFIDENCE pair.** `ep_parse_b`'s own third
arm sends a THIRD comma to `ep_syntax` (ERR 2), so PAINT already distinguishes
"one field too many" from "a field left empty" — and D-LINERR measured LINE's
box slot as ERR 2 where its colour slot is 24. A `2` here would not be a
surprise; it would be the same boundary CIRCLE's `x.extra` sits on.

## Amendment, written after the zerobas-only validation and BEFORE the 3-machine run

The validation run (`scratchpad/circmiss_sib2_zb.out`, zb only, `--raw`) settled
two things and forced two new rows.

✅ **THE PAINT INSTRUMENT FIX HOLDS.** All 10 PAINT rows produce a numeric
fence, including `p.ok` / `p.plain` / `p.none`, whose round-1 versions failed on
**all three** machines. Round 1's five `<NO OUTPUT>`s were 3 parts instrument
and 2 parts something else — see below.

🔴 **AND `CLEAR 200,` WAS NEVER AN APPARATUS GAP — THAT FILING IS WRONG.**
The raw screen says zerobas raises the error, correctly and with a line number:

    <A>
    Missing operand in 30

…and `ON ERROR GOTO 900` **does not catch it**, so the fence never printed and
the row scored `<NO OUTPUT>`. Both references trapped it (round 1: `24`). So the
divergence is **the trap, not the error** — and `TODO.md`'s *"zerobas is
UNMEASURED"* must be corrected rather than left to rot.
🎯 `<NO OUTPUT>` is what an unnamed outcome looks like. `face()` now names it
(`UNTRAPPED <msg> in <line>`), which turns the hole back into a reading.

**New predictions for the two rows this raised:**

| row | program | pred refs | pred zb | why |
|---|---|---|---|---|
| `t.after` | `ONERRORGOTO900` / `CLEAR 200` / `A=1/0` | `11 0` | **`11 0`** | ⚠️ THE REAL QUESTION. If a SUCCESSFUL `CLEAR` also kills the trap, zb reads `UNTRAPPED Division by zero in 40` and the dangling comma is a symptom of a far wider rule. I predict it does NOT — `basic/clear.asm`'s header says the args are evaluated first and only then is everything wiped, so the wipe is not what loses the trap |
| `t.notrap` | the same fault with **no** `CLEAR` | `11 0` | `11 0` | the control: if this is not trapped on all three, the row set says nothing at all |

**Revised prediction for `q.trail` / `q.kcolon`:** refs `24 0`, zb
**`UNTRAPPED Missing operand in 30`** — a DIFF, and a different one from the
one filed.
