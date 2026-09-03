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

## 6. ✅ D-PUNUM — the float renderer, and the `#` field is right now

`pu_num_tenant` (`sub/punum.asm`), a sub-ROM **page-1** tenant — the first
`PRINT USING` tenant that is not pure RAM. It calls the main ROM's **own**
`flt_fmt` ($305E, low region) through the generated
`sub/basic-resident-abi.inc`, so `PRINT USING` and `PRINT` cannot disagree about
what a number looks like, and a low-region shift cannot leave it calling a stale
address.

| row | was | now | ref |
|---|---|---|---|
| `c.over16` | `      0` | `1234567` | `1234567` ✅ |
| `c.round` | `    1` | `    2` | `    2` ✅ |
| `c.round2` | `    2` | `    3` | `    3` ✅ |
| `d.roundup` | ` 1.` | ` 2.` | ` 2.` ✅ |

**4 fixed, 0 broken.** The integer path stays for `FACTYP==2` — already correct
at both boundaries and cheaper — and everything else routes to the tenant.

🎯 **Rounding the rendered TEXT is exact here, and that is not a shortcut.** MSX
floats are BCD, so `flt_fmt`'s decimal output *is* the value: there is no binary
representation error to defeat and no tie-breaking to reproduce. `c.round` and
`c.round2` pin the direction as **half-up**, not banker's.

**Cost: page 1 32 → 12 B; sub page 1 1586 → 1480 B.**

### 6.1 Knife — and a scoring design fix

```
K-PN1  make the renderer TRUNCATE instead of rounding
       must-move  c.round, c.round2, d.roundup   -> yes
       must-hold  c.over16                       -> held      PASS
```

`c.over16` is the discriminator: `1234567` has no fraction, so rounding cannot
touch it — only *reaching the float path* can. Had it moved too, the arm would
merely have said "the tenant is wired up", which the four green rows already say.

⚠️ **The arm first read FAIL against an exact expected set**, because truncating
moves **every** fractional row — including the ten still waiting on `.`, which
are wrong before and after. That is the third exact-set arm this session to fail
on already-wrong rows shifting. The arm now scores the **discrimination**
(`must-move` ⊆ moved, `must-hold` ∩ moved = ∅) rather than an exact set, which is
a design fix and not a patched expectation.

## 7. Still open — and page 1 is at 12 B

`.` `,` `^^^^`. **Nine of the divergent rows are now closed**; what remains needs
the decimal point, and `p.dot` / `n.dot` / `a.dot` stay divergent until `.` lands
— each of those combines a shipped specifier with `.`, so they will fall out of
that slice rather than needing new sign or fill work.

🔴 **PAGE 1 IS AT 12 B** (2026-09-03, after D-PUNUM). That is not "tight", it is
**spent**: the next slice cannot add main-side code at all.

`.` `,` `^^^^` all now have their renderer — `pu_num_tenant` already produces the
digits and can take a decimal count, a grouping flag and an exponent form without
main-side growth, since the flags travel in `PU_FLAGS` and the result in `NUMBUF`.
What each still needs main-side is **nothing**, if the scanner sets the flag and
the tenant reads it. That is the shape to keep.

⚠️ **But anything that does need main-side bytes is blocked until page 1 is
carved.** The classic routes are recorded as exhausted (dup-span 4 B, page-0
eviction closed to printing verbs, `jp`→`jr` fully banked), so the route is more
eviction — `pu_do_number`'s pad/emit tail is the obvious candidate, and it is
pure `pchar` work.


## 9. 🔴 D-PUDOT attempted and REVERTED — what the attempt established

`.` was implemented end to end (scanner recognition + `PU_DEC`, a rewritten
renderer taking a decimal count, and the main-side routing for an integer with a
`##.##` format) and then **backed out**. The tree is unchanged apart from one
real bug the attempt exposed (§9.2).

**Why it was reverted, not debugged further:**

* the decimal path **crashed the fixture** on every `d.*`, `e.*` and `.dot` row —
  the probe read the harness's own `ERR` line back, which is what a corrupted
  return or a runaway loop looks like from outside;
* it **broke a row that was previously correct**: `d.roundup` (`"##."` · 1.5)
  went from ` 2.` to `  2`. A `.` with **zero** places still prints the point, and
  the renderer returned early on `PU_DEC == 0`;
* and it left page 1 at **2 B**. Debugging a carry-and-shift rewrite with two
  bytes of headroom is not a position to work from.

**What the attempt did establish, and it is worth keeping:**

* The main-side cost is **16 B** and lands page 1 at 2 B — measured, not
  estimated. `.` is therefore **blocked on evicting `pu_do_number`'s pad/emit
  tail**, not merely tight.
* The renderer wants the digits built **contiguously** with the point inserted
  last, so rounding is one carry walk over one array. That part of the design
  survives; the implementation of the carry/shift is what was wrong.
* `"##."` — a point with **no** places — is a real case and prints the point.
* A format with an **empty integer part** (`.##`, row `d.lead`) never reaches the
  renderer at all: `ptf_num` only starts a numeric field on a `#`. That is a
  separate scanner entry point.

### 9.2 The bug the attempt exposed — `sub/punum.asm` was not a build prerequisite

`make sub` reported *"nothing to be done"* after a full rewrite of the tenant,
and the sub-ROM wall did not move. **`sub/punum.asm` was never added to
`SUB_PARTS`**, so `D-PUNUM` shipped with a latent staleness bug: an edit to that
file would not have triggered a rebuild, and `build/sub.rom` would have gone
quietly stale.

The Makefile carries a memory link for exactly this shape —
`[[makefile-subparts-stale-tenant]]` — and **there is no gate for it**: nothing
in `tools/` cross-checks `SUB_PARTS` against the files `sub/sub.asm` actually
includes. That check is worth writing; it would have caught this at the moment
the file was added rather than one slice later.

⚠️ And the truncation that started the debugging was self-inflicted, for the
**second time today**: a `str.index('pu_num_tenant:')` matched the name inside
that routine's own comment header and cut the file there. Anchor on the label.

## 10. ✅ The `SUB_PARTS` gate — and it found three more

`make rom-parts-check` (`tools/check_rom_parts.py`), in the battery. It compares
each ROM's **transitive include closure** against the prerequisites its Makefile
rule actually has — the `*_PARTS` variable plus anything named on the target
line. A file in the closure but not in the prerequisites is *a rebuild that will
not happen*.

**Its first run found three more of exactly tonight's bug**, none of them mine:

| file | included by |
|---|---|
| `sub/lrsetst.asm` | `sub/sub.asm` |
| `sub/deffn.asm` | `sub/sub.asm` |
| `basic/pdfcb-body.inc` | `sub/bload.asm` |

Each is a tenant whose edits would not have triggered a rebuild. All three are
now prerequisites; `disk.rom` was already clean.

🔴 **AND THE GATE'S OWN FIRST RUN WAS WRONG, CONFIDENTLY.** It reported **63**
missing files — because it parsed the Makefile line-at-a-time and `SUB_PARTS`
spans a dozen backslash-continued lines, so it saw only the first. A plausible
table from a misread input, in the very tool whose docstring is about that
failure. Continuations are joined before anything is parsed.

Both behaviours are tested, not assumed: a degenerate parse (zero includes) exits
**2** with nothing checked, and removing two entries from `SUB_PARTS` is caught
and exits **1**.

## 11. ✅ D-PUEMIT — the pad/emit tail evicted, and `.` is unblocked

§9 established that `.` is **blocked on evicting `pu_do_number`'s pad/emit tail**,
not merely tight. That eviction is done.

**Page 1: 18 → 42 B free** (sub page 0 1668 → 1590 B). `.`'s measured main-side
cost is 16 B, so it now fits with room rather than landing at 2 B.

⚠️ **A tenant cannot call `pchar` at all**, and that is the constraint that shapes
this. `pchar` reaches `CHPUT` in the **BIOS (page 0)** and itself lives in **main
page 1** — whichever island a tenant runs on, one of those two is switched out.
So `pu_emit_tenant` **buffers** into `DETOKBUF` and the resident stub drains it
through the real `print_string`, honouring `PRDEST` so `PRINT# USING`'s file form
is untouched. That is exactly the shape `pu_to_field` has always had, and reading
*why* it was written that way is what made this eviction possible at all rather
than a crash.

The length is **measured inside the tenant** rather than marshalled in, so there
is one less thing to keep in step across the CALSLT.

### 11.1 Proof: neutral, and both arms still live

* **Behaviour-neutral** — 0 of 44 probe rows moved.
* **Both branches of the evicted body are still exercised** — 8 rows reach the
  `%` overflow arm (`c.over`, `d.over`, `e.big`, `m.basic`, `m.big`, `m.dot`,
  `m.neg`, `m.small`) and 3 reach the `*` fill arm (`a.basic`, `a.dot`, `a.neg`).

The second fact is the one that is easy to skip. "Nothing moved" is equally what
evicting **dead** code looks like, and an eviction that quietly dropped the
overflow or fill behaviour would read identically on the first fact alone.
## 12. ✅ D-PUDOT — `.`, on the second attempt

`PRINT USING"##.##";1.5` is the specifier the whole slice was built toward.
§9 records the first attempt and its revert. This is the one that shipped.

    PRINT USING"##.##";1.5     refs ` 1.50`     was ` 1`
    PRINT USING"##.";1.5       refs `  2.`      was ` 2`
    PRINT USING"####.####";3.14159  refs `   3.1416`   was `    3`

**11 rows went green.** Divergent rows on this probe: **11 of 43**, all of them
now in the two families that have no code at all (`,` and `^^^^`) plus `d.lead`.

### 12.1 The model came before the assembly, and that is why it worked

§9's attempt was written straight into Z80 and crashed the fixture on every row.
The retry was written **in Python first** and checked against the eleven measured
values before a single instruction existed. Two corner cases the model settled on
paper — both of which the reverted attempt had wrong — are:

* **`##.` — a point with zero places — still prints the point** (` 2.`). The
  first attempt returned early when the place count was zero and lost it.
* **Rounding can grow the integer part**, moving the point one column right:
  `##.` with 9.5 is `10.`, `##.#` with 9.99 is `10.0`.

Those two carry-growth cases existed **only as model predictions**. They were
added to the probe as `d.grow` / `d.growfrac` and **both references confirmed
them** before the code was trusted — and they are also the only rows that can
witness knife K-PD2, so without them that arm would have been a designed no-op.

### 12.2 The design decision that removed the crash

Digits are built **contiguously**, with the decimal point **inserted last**.
Rounding is then one carry walk over one array with no point in the middle for
the carry to cross, and growth is a single `inc c` on the integer-digit count.

The other half is smaller and mattered more: **`DIGSTART` is recomputed, not
stacked**. It is `NUMBUF`, or `NUMBUF+1` when a `-` leads — cheaper to derive
than to carry, and deriving it deletes every unbalanced-stack path at once. The
reverted attempt pushed and popped it across three branches; that is what
crashed.

### 12.3 🔴 Eleven green rows hid a scanner bug that exactly one row could see

With `.` working, `n.dot` (`PRINT USING"##.##-";-1.5`) still printed `-1.50`
where both references say ` 1.50-`. The cause was in the code this slice added:
the scanner saved the field width with `push bc` and restored it with `pop bc`,
which preserves `B`, the width — **and also rewinds `C`, the scan cursor**. The
scanner then re-read the decimal `#`s instead of the character after them.

It is invisible on all eleven `d.*` rows, because a field the scanner re-enters
with no argument left simply behaves as a trailing literal. It is visible on
exactly one row in the set: the one where the character after the decimal part
is load-bearing. Counting straight into `PU_DEC` instead of borrowing `B` fixes
it, and `n.dot` went green with it — **12 rows, not 11**.

The lesson is not "use a different register". It is that **a family of rows that
all go green together can share a blind spot**, and the row that finds it is the
one whose format has something *after* the new syntax.

### 12.4 Knives — 6/6, and two of them are the interesting ones

| arm | plant | must move | must hold |
|---|---|---|---|
| K-PD1 | never round | `d.roundup` `d.grow` `d.growfrac` | `d.basic` `d.int` `c.over16` |
| K-PD2 | drop the carry's `inc c` | `d.grow` `d.growfrac` | `d.round` `d.roundup` `d.basic` |
| K-PD3 | re-plant §9's zero-places bug | `d.roundup` `d.grow` | `d.basic` `d.growfrac` |
| K-PD4 | skip the leading-zero emit | `d.leadzero` | `d.basic` `d.zero` |
| K-PD5 | stop counting places in the width | `d.basic` `d.wide` | `c.hash` `c.round` |
| K-PD6 | re-plant the §12.3 cursor rewind | `n.dot` | `d.basic` `d.wide` `d.roundup` `a.dot` `p.dot` |

**K-PD2 moved exactly `{d.grow, d.growfrac}`** and nothing else — the two rows
that were added for it. **K-PD1's must-hold is `d.basic`**: 1.5 at two places is
exact, so removing rounding must *not* touch the headline row; if it did, the arm
would only be saying "the renderer runs".

**K-PD4 answered a question the source could not.** It moves `d.leadzero`, which
means `flt_fmt` emits `.5`, not `0.5` — the leading-zero emit is load-bearing,
not defensive.

**K-PD6's must-hold list is the whole point**: five rows that exercise `.` and
cannot see the bug §12.3 describes.

### 12.5 🔴 The harness lost two runs to a plant that outlived its run

Both were killed from outside — once by `pkill`, once by a two-minute command
timeout — and **a `finally` does not survive `SIGTERM`**. Each left a plant in a
tracked source file, and the next run then read the planted file as its own
baseline: a knife measuring itself. Neither run printed anything wrong; the tell
was two live `KNIFE` markers in the tree.

The runner now writes the original to a **sidecar on disk** before planting and
restores from it at startup. The sidecar existing at all is the alarm — it means
a previous run did not finish. `atexit` and a `SIGTERM` handler cover the rest.

### 12.6 Still open

* **`d.lead`** — `.##` with an empty integer part. `ptf_num` only starts a
  numeric field on `#`, so a leading `.` is still scanned as a literal; it needs
  a second scanner entry point, not a renderer change.
* **`,`** (5 rows) and **`^^^^`** (5 rows) — no implementation yet. `^^^^`'s
  mantissa is already correct as of this slice; only the exponent is missing.
