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

## 4. D-PUSIGN — `+` and `-`, six more rows

| row | format · value | answer |
|---|---|---|
| `p.lead` | `"+##"` · 5 | ` +5` |
| `p.leadneg` | `"+##"` · −5 | ` -5` |
| `p.trail` | `"##+"` · 5 | ` 5+` |
| `p.trailneg` | `"##+"` · −5 | ` 5-` |
| `n.pos` | `"##-"` · 5 | ` 5 ` |
| `n.neg` | `"##-"` · −5 | ` 5-` |

Three transformations, not one: **prepend** `+` (leading, positive), **append**
`+` or a *space* (trailing, positive), and **move** the leading `-` to the end
(trailing, negative) — where it stays `-` even when the specifier is `+`.
`p.leadneg` needs nothing at all: `pu_fmt_int` already wrote the `-` in front.

**Sited sub-side because of space, not structure.** It is pure RAM work over
`NUMBUF` and could equally live in `basic/printusing.asm` — but that is main
page 1, which had **50 B**, and the transformation is ~60. It became
`pu_sign_tenant`, page-0 index 15, whose closure holds trivially: no main-ROM
call at all. Main side pays 18 B for the flag test and the CALSLT.

**Cost: page 1 50 → 32 B; sub page 0 1894 → 1668 B.**

### 4.1 Knife — the rows that must NOT move are the claim

```
K-PG1  drop the leading `-` removal (append without moving)
       moved p.trailneg, n.neg   —   p.trail and n.pos unchanged   PASS
```

Had the trailing *positive* rows moved too, the arm would only have been saying
"trailing signs are implemented", which the six green rows already say. The
asymmetry is what shows the negative move is its own transformation.

## 5. 🔴 The plain `#` field is itself wrong — and my controls were too narrow to see it

Found 2026-09-03 while deciding whether `.` `,` `^^^^` were three slices or one.

| row | | vg8020 | cf3300 | zb |
|---|---|---|---|---|
| `c.max` | `"#######"` · 32767 | `  32767` | `  32767` | `  32767` ✅ |
| `c.negmax` | `"#######"` · −32768 | ` -32768` | ` -32768` | ` -32768` ✅ |
| `c.over16` | `"#######"` · 1234567 | `1234567` | `1234567` | **`      0`** |
| `c.round` | `"#####"` · 1.5 | `    2` | `    2` | **`    1`** |
| `c.round2` | `"#####"` · 2.5 | `    3` | `    3` | **`    2`** |

**None of these involves a specifier.** `pu_do_number` calls `eval` for a 16-bit
`DE` and formats it with `pu_fmt_int`, so the numeric field is **integer-only and
truncating**: a value past `int16` renders as `0` — a silent wrong answer — and a
fraction is chopped where both references **round half-up** (`1.5`→2, `2.5`→3;
the int16 boundaries themselves are exact on all three).

🎯 **AND THE CONTROLS ARE WHY IT HID.** `c.hash`, `c.neg` and `c.over` all used
**small integers**. They agreed, and I read that agreement as "the plain `#`
field is already right". A control only certifies the ground it stands on, and
all three stood on the same narrow patch.

### 5.1 What that reframes

`.` `,` and `^^^^` are **not three independent slices**. Each of them needs a
value rendered as text with a decimal point, an exponent, or grouping — which the
integer path cannot produce at all. They are **one slice**: *give `PRINT USING` a
float renderer*, and that renderer fixes `c.over16`, `c.round` and `c.round2` on
the way past.

That also explains a row already on the books: `m.big` (`"##,###,###"` · 1234567)
reads ` 0,` here. It was filed as a comma-grouping gap; it is really the same
int16 truncation.

### 5.2 The shape it has to take

Page 1 is at **32 B**, so the renderer cannot live there. The route the last two
slices established works here too, one level up:

* a **sub-ROM PAGE-1 tenant** — 1586 B free — which may call the main **low
  region** by absolute address (the rule `sub/circleparse.asm` already relies on,
  and which `D-DISKABI` re-confirmed for `disk.rom`);
* `flt_fmt` (`basic/float.asm`) is low-region, so the tenant can render the value
  to text and then place the point, group, or exponentiate it;
* MSX floats are **BCD**, so rounding the rendered *text* half-up is exact — no
  binary tie-breaking to reproduce. `c.round`/`c.round2` pin the direction.
* `flt_fmt` would need adding to `sub/basic-resident-abi.inc`'s REQUIRED list —
  one entry, already ceiling-legal.

Main side then pays only a flag test and a CALSLT, as `D-PUSIGN` does.

## 6. Still open — one slice, not three

`.` `,` `^^^^`. **Nine of the divergent rows are now closed**; what remains needs
the decimal point, and `p.dot` / `n.dot` / `a.dot` stay divergent until `.` lands
— each of those combines a shipped specifier with `.`, so they will fall out of
that slice rather than needing new sign or fill work.

🔴 **PAGE 1 IS AT 32 B** (2026-09-03) and `.` is the largest of the three: it
needs rounding at a decimal position, not just placement. The scanner and any
buffer work can go sub-side as these two did, but the emitter cannot. **A page-1
carve, or moving more of `pu_do_number` sub-side, is now the prerequisite** —
not an optimisation to do afterwards.
