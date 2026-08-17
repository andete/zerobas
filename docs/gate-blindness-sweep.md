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
