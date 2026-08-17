# Which gate rows can anything redden? A mutation sweep of graphics-acceptance

D-GATEBLIND, 2026-08-17. Not a fidelity slice — a measurement of the apparatus.

Three gate rows were found **blind** in one week, each by re-deriving it rather
than trusting its name:

* G3's three clip rows (D-SPOKELINE) — one vacuous, one geometry-degenerate,
  one banded away from the pixel it was named for.
* G6's `clip_left` (D-DRAWCLAMP) — **horizontal**, and for an axis-aligned
  segment clamping and clipping produce the same pixels.
* `box_bf` (D-BFBYTE) — spans seven pixels in each of two cells, so **not one
  whole byte** is covered, and it reads the pattern plane only.

Each had been green for months while blind to exactly the thing it was named
for. Three in a week is a pattern, so it gets measured instead of waited for.

---

## §1 Method

Mutate the graphics tenant, rebuild, run the **whole** gate, record which rows
go red. A row that no mutation can redden is doing no work against that battery.

Five mutations, each **one instruction of the same length** so every span stays
reachable — `check_dead_code.py` fails `make basic-reloc` on an unreachable
span, and a tree that does not build scores nothing (K-DC3 learned that the hard
way two commits ago):

| mutation | what it breaks | rows reddened |
|---|---|---|
| `M-COLOUR` | `gfx_color_rmw`: the clash decision inverted | **120** |
| `M-BRESERR` | `gfx_bres_init`: the `dmaj>>1` error seed computed on the wrong half | 32 |
| `M-YBOUND` | `gfx_plot_cur`: the on-screen y bound 192 → 191 | 17 |
| `M-CLAMPX` | `gfx_clamp_coords`: the X max 255 → 254 | 10 |
| `M-CLAMPY` | `gfx_clamp_coords`: the Y max 191 → 190 | 7 |

**123 of 355 rows reddened; 232 never did.**

## §2 ⚠️ The battery is the denominator, and it is hand-listed

"No mutation reddened it" does **not** mean "blind" — it means "blind to these
five", which mutate the pixel, clamp, line and colour paths only. The 232 are
dominated by subsystems this battery never touches: 35 sprite `PUT`/`SPRITE`
rows, 29 sprite-pattern rows, 57 `VDP()`/`BASE()` rows, 20 VDP-register rows,
25 `DRAW` error-surface rows, and 10 work-area rows that read `GRPACX`/`GXPOS`
as numbers rather than pixels. Those are **expected** and are not findings.

The output is a candidate roster to re-derive by hand — the way the three known
ones were found — not a verdict.
[[a-hand-listed-denominator-is-a-scope-claim]]

## §3 The method validated itself, unplanted

`clip_alloff` appears in the never-reddened roster. That is the row D-SPOKELINE
**proved** blind two days earlier: it captures the top-left band while the
clamp's one surviving pixel lights the bottom-right corner. The sweep flagged
it without being told it existed, which is the closest thing to a positive
control this measurement could have had, and it was not planted.

## §4 🔴 The new finding: `clip_noop` is blind, and provably so

Phase A carried one row for the whole off-screen-`PSET` question:

    PSET(300,100):PSET(0,192):PSET(-1,0)     read back the cell at (0,0)

The question a coverage row must answer is not *"is the cell I read blank"* but
*"is the cell I read the cell a failure would write"*. Strip the clip out of
`gfx_plot_cur` on paper and push each coordinate through `gfx_calc_addr`
([`clipnoop_proof.py`](../scratchpad/clipnoop_proof.py)):

| statement | would write | in the row's band? |
|---|---|---|
| `PSET(300,100)` | `$0C2C` | no |
| `PSET(0,192)` | `$1800` | no — **outside the 6144-byte pattern plane** |
| `PSET(-1,0)` | `$00F8` | no |

The row read addresses 0..7. **Not one of its three failure modes could land
there: it was green whether or not the clip worked, and would pass with every
clip in `gfx_plot_cur` deleted.**

Unlike the sweep, this is a *proof* rather than a candidate — it enumerates the
row's entire failure surface, three statements and three addresses, and
compares it with the band.

### 4.1 Fixed

Split into two rows that read the cell their own failure would write:

    clip_noop_x300   PSET(300,100)   read (44,100)  -> $0C2C
    clip_noop_xneg   PSET(-1,0)      read (248,0)   -> $00F8

⚠️ **`PSET(0,192)` is deliberately not rowed.** With the clip removed it writes
`$1800`, the SCREEN 2 **name table**, outside the pattern plane — no band this
phase can express reaches it. It needs a different instrument, not a wider
band, and it is filed rather than left as a row that looks like coverage.

### 4.2 Proven live — and 🔴 the first attempt to prove it cut the wrong routine

Replacing one blind row with two rows that *ought* to see a failure is worth
nothing until a cut actually reddens them.

**K-CN1 failed to redden them, and that was a defect in the knife.** It removed
the X clip from `gfx_plot_cur` in the **sub** ROM — but `PSET` is `GFX_OP=1`,
whose off-screen rejection lives in the **main** ROM: `ex_pset` calls
`gfx_in_range` and `jp nc,exec_stmt` skips the plot, so by the time the sub-ROM
arm reads `GXPOS` the byte is "0..255 guaranteed in-range". Same class as
D-PAINTSEED's knife cutting a different routine — and here it was caught only
because rows stayed green under a cut that should have reddened them. **A green
row under a knife is a claim about the knife too.**

**K-CN2** cuts the real one — `gfx_in_range`'s x high-byte test, `or a` →
`xor a`, one byte for one byte — and is **exact against a prediction written
first**:

| row | predicted | measured |
|---|---|---|
| `clip_noop_x300` | pattern `08` at `$0C2C` | `08`/`f4` — **FAIL** |
| `clip_noop_xneg` | pattern `01` at `$00F8` | `01`/`f4` — **FAIL** |
| the 8 on-screen PSET/PRESET rows | unmoved | all **PASS** |

⚠️ The hash guard had to watch `basic-reloc.rom`, not `sub.rom`: this is a
main-ROM edit and `sub.rom` does not move. A guard pointed at the wrong ROM
would have reported "the knife did not take" for a knife that took perfectly.

And the old row would have stayed green under this very cut: both writes land
at `$0C2C` and `$00F8`, and it read addresses 0..7.

## §5 🔴 The sweep's own parser was lossy, and it was caught before it was believed

Keying rows by bare label collapses 355 gate lines into 349: `scr0_err` appears
in three phases, `colour16_err` and `after` in two, and phase Q prints
`PASS <machine> <label>` so `Philips` and `C-BIOS` were captured *as* labels.
A merged label counts as reddened if **any** instance reddens — so a genuinely
blind row hides behind a live sibling, and the aggregate reports the gate as
**better** than it is, which is the direction that matters.

Caught by checking the parser against the baseline log before trusting its
output, and repaired by re-deriving everything from the saved raw gate logs,
keyed by `(phase, label, occurrence)`. No emulator time was re-spent.

## §6 Apparatus

| file | what it does |
|---|---|
| [`gate_blindness_sweep.py`](../scratchpad/gate_blindness_sweep.py) | the five mutations, build/install/gate/restore, ROM-hash guarded |
| [`gate_blindness_report.py`](../scratchpad/gate_blindness_report.py) | the phase-aware aggregate that keeps all 355 rows |
| [`clipnoop_proof.py`](../scratchpad/clipnoop_proof.py) | the arithmetic proof, and the bands that *can* see each failure |

---

# Round 2 — the battery extended into the sprite and VDP paths

2026-08-17, same day. §2 above named its own blind spots: the 232-row roster was
dominated by four subsystems the five mutations never touch. Naming them is not
measuring them, so sixteen more mutations were written to hit exactly those —
the sprite attribute and pattern tables, the sprite size/magnification state,
the VDP register write path, and `VDP()`/`BASE()` argument handling.

## §7 The apparatus had to change first, twice

**Per-mutation file AND ROM.** Round 1 could only mutate `sub/graphics.asm` and
only hash-guarded `sub.rom`. Half the sprite/VDP surface is resident
(`basic/graphics.asm`), and 🔴 **a `basic/` edit does not move `sub.rom`** — a
guard on the wrong ROM reports a perfect cut as "the mutation did not take",
which is exactly how §4.2's K-CN1 wasted a build. Every entry now carries its own
file and its own ROM, so the hazard is structural rather than remembered.

**"Green under a mutation" is not "never measured by it".** Round 1 ran against a
355-row gate; §4.1 then split `clip_noop` into two rows. Counting those two as
"nothing could redden them" would be the same lossy direction as §5's parser bug
— it makes the gate look *better* than it is. The aggregate now prints, for every
never-reddened row, how many battery members actually contained it, and calls
out any row measured by fewer than all of them (`clip_noop_x300` /
`clip_noop_xneg`: 16 of 21 — and both are known live from K-CN2 regardless).

## §8 The sixteen, and what each reddened

Baseline re-measured from clean the same day: **356 PASS / 0 FAIL**,
`basic-reloc 8e5391b3`, `sub aeed6276`. Every mutation one instruction of the
same length; all sixteen built, all sixteen moved their ROM, and the tree
restored to both original hashes.

| mutation | what it breaks | rows |
|---|---|---|
| `M-G8PAREN` | `g8_open_paren`: the closing `)` of every `VDP(n)`/`BASE(n)`/`SPRITE$(n)` index read as `:` | **91** |
| `M-VDPMIRR` | `g8_wrvdp`: the RAM mirror written one register slot high | **68** |
| `M-PUTCOMMA` | `ex_put_sprite`: the comma after the plane read as `;` | 34 |
| `M-SPRSCR0` | `spr_assign`: the SCREEN 0 gate inverted | 20 |
| `M-SPRPBASE` | `gfx_spr_addr`: the pattern generator base 8 bytes high | 13 |
| `M-SPRSZAPL` | `gfx_spr_size_apply`: only the magnification bit re-applied to R1 | 10 |
| `M-SPRENTSZ` | `gfx_spr_addr`: the 16×16 bit read from `RG1SAV` bit 2, not bit 1 | 7 |
| `M-BASESHIFT` | `g8_wrshifted`: R4 divided by `$1000` instead of `$800` | 4 |
| `M-BASEGMAP` | `g8_gmap`: SCREEN 1 reprograms from its own group, not group 2 | 3 |
| `M-SPRECLK` | `gfx_spr_attr`: the early-clock offset for a negative x is 31 | 3 |
| `M-SPRPATSC` | `gfx_spr_attr`: the 16×16 pattern number stored as 2n, not 4n | 2 |
| `M-SPRXREST` | `gfx_spr_xrest`: the attribute entry stride 4 → 3 | 2 |
| `M-SPRPLANE` | `gfx_spr_attr`: the `PUT SPRITE` plane bound 32 → 31 | 1 |
| `M-VDPBOUND` | `gfx_vdp_wr`: the `VDP(n)=` index bound 8 → 7 | 1 |
| `M-BASEGRAIN` | `g8_grain`: the name table grain `$400` → `$80` | 1 |
| `M-G8RDLIM` | `ev_f_vdp`: the `VDP(n)` read domain 0..8 → 0..7 | 1 |

**Battery of 21 (both rounds): 263 of 356 rows reddened, 93 never.** The four
targeted phases went from **155 never-reddened rows to 15**:

| phase | round 1 | round 2 |
|---|---|---|
| N — sprite tables | 29 | **0** |
| O — sprite errors + accepted edges | 35 | 11 |
| P — table init, CLS, persistent size | 10 | 1 |
| Q1 — VDP/BASE state + R0..R6 | 20 | **0** |
| Q2 — VDP/BASE reads, domains, grammar | 57 | 1 |
| Q3 — does `VDP(n)=` reach the chip | 4 | 2 |

Everything outside them is untouched at 78 rows, and honestly so: this battery
never mutates the `DRAW` error surface (phase L, 25 rows), the work area
(phase R, 10) or the PAINT/CIRCLE error tails. **The denominator is still
hand-listed** — it is just a longer hand.

## §9 The predictions, scored — ten exact, and the two misses

A prediction per mutation was written into the sweep script before the run.

**Ten exact at the row level**: `M-SPRSCR0` (20 rows, including that
`spr_n256`/`spr_n_neg` would *not* move because ERR 5 comes out either way),
`M-SPRENTSZ` (7), `M-BASESHIFT` (4), `M-BASEGMAP` (3), `M-SPRECLK` (3),
`M-SPRPATSC` (2), `M-SPRPLANE`, `M-VDPBOUND`, `M-BASEGRAIN`, `M-G8RDLIM` (1 each).

`M-BASESHIFT` is the one worth keeping: predicted to move **only** the four
SCREEN 0 rows, because groups 2 and 3 hold pattern base `$0000` and `0>>11` is
`0>>12`. A reprogram mutation that reddens 4 of 20 state rows looks like a weak
cut until the arithmetic says 4 is the whole answer.

Three over-predictions by exactly one row, each instructive:

* `pat_8_empty` survives `M-SPRPBASE`: `SPRITE$(0)=""` writes eight zeros, and
  the shifted base leaves the read cell at 0 as well.
* `put_pat63_16` survives `M-SPRSZAPL`: phase O compares the **error outcome**,
  and 63 is accepted under both the 8×8 and 16×16 rules. The *value* divergence
  is real and lands in phase N — which did redden.
* `cls_keeps` survives `M-SPRXREST`.

🔴 **The big miss: `M-VDPMIRR`, predicted ~24 rows, measured 68.** `RG0SAV+1` for
register 0 *is* `RG1SAV`, so one `VDP(0)=2` poisons the screen-mode and
sprite-size mirror — and **phase Q2 is batched**, so a single early case's poison
desynchronised 44 later ones. Per-row attribution inside a batched phase is not
clean when the mutation corrupts shared state; the count is real, the *targeting*
claim is not.

🔴 **`M-G8PAREN` reddened `Q3/C-BIOS/control`, which I predicted would hold.**
Q3's control exists to prove the emulator is alive when the subject case freezes
TIME — but its restore line is `VDP(1)=VDP(1)OR32`, **the very statement the
subject uses**. A cut to the VDP grammar takes the control down with the subject,
so the pair cannot distinguish "the chip write failed" from "the VDP statement
broke". Filed, not fixed here.

## §10 The roster has a floor: two rows no mutation can ever redden

`Q3/Philips/control` and `Q3/Philips/ie_off` run on the **reference** machine.
No mutation of our ROM can move them, in this battery or any future one — and
that is precisely their job: they are the rig's liveness check on the oracle
side. A never-reddened roster can never reach zero, and reading these two as
candidates would be a category error.

## §11 `PSET(0,192)` is rowed at last — and 🔴 the filed blocker named the wrong obstacle

§4.1 left the third statement of the old `clip_noop` unrowed and filed it as
needing "a raw-VRAM-segment capture at `$1800`, a mechanism phase A does not have
today". That blocker was wrong, and wrong in the way this project keeps
re-learning: it named an obstacle from the wrong routine.
[[a-filed-blocker-can-name-the-wrong-obstacle]]

`band_segs()` **is** clamped to the 6144-byte pattern plane — but it is phases
C/D/E's instrument (LINE / CIRCLE / DRAW bands). **Phase A never calls it.** Every
phase-A row captures two explicit one-byte segments, `paddr(x,y)` and
`paddr(x,y) + $2000`, and `paddr(0,192)` is 6144 = `$1800` **exactly**. The
capture shape could reach the cell from the day it was written.

What was actually missing is smaller, and it is the same question the slice turns
on — *what would a failure WRITE?* `$1800`'s colour-half cell is `$3800`, the
**sprite pattern generator**, whose byte 0 is whatever the BIOS left. And
`gfx_color_rmw` **clears** the pixel, writing no colour byte at all, when the plot
colour equals the colour byte's low nibble:

| `colour[$3800]` | bg nibble | rmw | `pattern[$1800]` | `colour[$3800]` |
|---|---|---|---|---|
| `$00` / `$04` / `$F4` | 0 / 4 / 4 | SET | `$80` | `$F0` / `$F4` / `$F4` |
| `$0F` / `$FF` / `$1F` | 15 | **CLEAR** | `$00` | unchanged |

With `FORCLR` 15, a `$3800` whose low nibble happened to be 15 would make an
unclipped `PSET(0,192)` clear an already-0 pattern bit and touch nothing —
**both captured cells unchanged, the new row exactly as blind as the one it
replaces.** Whether the row worked would have been decided by a byte of a sprite
table nobody wrote. So the row pins its pre-state with `SPRITE$(0)=STRING$(8,0)`
(a BASIC statement, not a VPOKE — phase A's own rule), which zeroes
`$3800..$3807` on both machines and also removes the second hazard: the two
BIOSes need not agree on a sprite table neither has been asked to fill.

    clip_noop_y192   SPRITE$(0)=STRING$(8,0):PSET(0,192)   reads $1800 / $3800

**K-Y192, exact against a prediction written first.** `gfx_in_range`'s `cp 192` →
`cp 193` (main ROM — `PSET` is `GFX_OP=1` and the tenant's `gfx_plot` has no range
test at all, so the resident test *is* the whole clip):

| row | predicted | measured |
|---|---|---|
| `clip_noop_y192` | pattern `80` at `$1800`, colour `F0` at `$3800` | `80`/`f0` — **FAIL** |
| the other 10 phase-A rows | unmoved | all **PASS** |

Unknifed both cells read `00`/`00` on both machines, which is also the oracle
this row was predicted to have.

## §12 🔴 The new finding: an entire *parameter* was pinned by nothing

Round 2 left phase P with exactly one never-reddened row, `init_p31`, and
re-deriving it found something wider than a row.

`gfx_spr_xsave` / `gfx_spr_xrest` bracket CHGMOD to put **32** attribute x bytes
back, because C-BIOS's mode set zeroes them where the reference measurably leaves
them alone (D-G7-3). A restore is only *observable* where x was **non-zero before
the mode set** — and the only gate row that ever set one was `init_planes`, on
**plane 0**. Every other row reads an x byte that is 0 whether the restore ran or
not. `init_p31` reads plane 31's entry after a bare `COLOR15,1,1:SCREEN2`, so its
x is 0 from boot: the clip_noop shape exactly — *a cell that cannot hold the
failure.*

So the claim is not "one row is weak" but **"the loop's count is unpinned"**, and
that is falsifiable in one cut. `ld b,32` → `ld b,1` restores plane 0 and nothing
else, and the **whole** gate runs, because a phase-P-only run would say nothing
about the other nineteen phases:

| row set | predicted | measured |
|---|---|---|
| `init_p31_x` (new) | FAIL, zb x=0 vs ref x=77 | `209 77 31 15` vs `209 0 31 15` — **FAIL** |
| all 357 others, incl. `init_p31`, `init_planes` | unmoved | **PASS** |

**358 rows, exactly one red.** Thirty-one of the thirty-two restores could be
deleted and the entire pre-existing gate stayed green. The repair is a row that
sets a non-zero x on the *last* plane and then re-enters the mode:

    init_p31_x   COLOR15,1,1:SCREEN2:PUT SPRITE 31,(77,20),4,1:SCREEN2

`init_p31` is **kept as it stands**, not rewritten: it still pins the mode-set
init of plane 31 (y=209, pattern=plane, colour=FORCLR), which is real coverage of
a BIOS delta. It was only ever blind to the x half, and the twin now covers that.

⚠️ Note what the sweep did **not** do here. It flagged `init_p31` as a candidate
and stopped; the mutation that would have reddened it (`ld b,32`) was not in the
battery, and `M-SPRXREST`'s stride cut writes only as far as `$1B5E`, 30 bytes
short of plane 31's entry. **The battery pointed at the row; only the hand proof
knew what was wrong with it.** That is the division of labour §2 asked for.

## §13 Where the gate stands

**Gate 358 PASS / 0 FAIL** (356 + `clip_noop_y192` + `init_p31_x`), ROMs
unchanged at `basic-reloc 8e5391b3` / `sub aeed6276` — both findings this round
are apparatus, not tenant: **no ROM byte moved, and no wall was spent.**

Roster after 21 mutations: **93 of 356 never reddened** (down from 232 of 355),
of which the sprite/VDP phases hold 15. Each of those 15 has a named reason, and
none of them is "nobody looked":

* **O, 5 rows** (`put_5args`, `put_bare`, `put_comma`, `put_halfxy`,
  `put_trailing`) assert **ERR 2 on a malformed form**. Every cut in this battery
  pushed *toward* ERR 2, so none of them can move these; reddening them needs a
  mutation that makes a malformed form **accepted**.
* **O, 2 rows** (`put_scr0`, `spr_on_s0`): the SCREEN-0 gate in `ex_put_sprite`
  and `ex_sprite` was never cut — `M-SPRSCR0` cut `spr_assign`'s.
* **O, 4 rows** (`spr_bare`, `spr_on`, `spr_off`, `spr_stop`): the ON/OFF/STOP
  decode was never cut.
* **Q2, 1 row** (`rd_nopar`, `A=VDP 0`): `M-G8PAREN` cut the **closing** paren
  test; the opening one is untouched.
* **P, 1 row** (`init_p31`): §12 — blind to the x half, kept for the init half.
* **Q3, 2 rows**: §10, the reference-side floor.

The 78 rows outside the sprite/VDP phases are round 1's roster unchanged, and
the next battery has an obvious shape: the `DRAW` error surface (phase L, 25
rows), the work area (phase R, 10), and the PAINT/CIRCLE/LINE error tails.
