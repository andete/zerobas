# D-PUSTAR — `PRINT USING`'s `**` asterisk fill

**Status:** shipped 2026-09-03. **Probe:** `scratchpad/pufloat_probe.py`.
**Knives:** `scratchpad/pustar_knives.py`.

The first of `PRINT USING`'s six missing format specifiers. D-PUSING found them
(header deferred to *"Phase-3 floats"*, which had arrived) and filed the item
unpriced; `scratchpad/pufloat_probe.py` then established the full contract —
**36 rows on which both references agree**, plus 3 carried as NO-ORACLE.

## 1. What `**` does, measured

| row | format · value | answer |
|---|---|---|
| `a.basic` | `"**##"` · 5 | `***5` |
| `a.neg` | `"**##"` · −5 | `**-5` |
| `a.full` | `"**##"` · 1234 | `1234` |

Two claims, not one: the asterisks are **consumed**, they still **count toward
the width** (`**##` is four wide), and the pad character becomes `*`. `a.full`
shows the width half alone — four digits in a four-wide field emit no padding at
all.

⚠️ **A lone `*` stays a literal**, as does a `*` at the end of the format. Only
the pair is a specifier.

## 2. Where the code went, and why it was affordable

Page 1 had **61 B** free when this started. It was affordable because
`basic/pu-render.inc` — the field scanner — is included **only** by
`sub/printusing.asm`: it is a sub-ROM page-0 tenant, where 1962 B were free. So
recognition and width accounting cost sub-ROM bytes, and only the pad-character
choice touches page 1.

`PU_FLAGS` already existed with bits 0 and 1 in use, so the fill flag is **bit 2**
— no new RAM cell. It is cleared per field alongside the "wrapped" bit, because
both are per-field state.

**Cost: page 1 61 → 50 B; sub page 0 1962 → 1894 B.**

## 3. Knives — 2/2, and the asymmetry is the evidence

```
K-PS1  asterisks stop counting toward the width   moved a.basic a.neg a.dot a.full  PASS
K-PS2  pad with a space again (fill ignored)      moved a.basic a.neg a.dot         PASS
```

🎯 **`a.full` is what separates the two claims.** It emits no padding, so killing
the fill cannot touch it, while killing the width makes it overflow. Had both
arms moved the same rows, one of the two claims would be unproven.

⚠️ **Round 1 predicted both sets without `a.dot` and both arms read FAIL.**
`**#.##` exercises `**` perfectly well even though its `.` half is still
unimplemented, so killing either half changes that row too. The arms were right
and the prediction was short.

## 4. Still open — five specifiers

`.` `,` `+` `-` `^^^^`, and `a.dot` (`**#.##`) stays divergent until `.` lands.
The contract for all of them is already measured in
`scratchpad/pufloat_probe.py`; what is scarce is page 1, at **50 B**.
