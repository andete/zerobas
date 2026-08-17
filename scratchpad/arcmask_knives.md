# D-ARCMASK implementation knives — predictions written BEFORE running

Each knife deletes one load-bearing part of the shipped implementation,
predicts the exact failure, runs the cheapest gate that can see it, and
restores. The unit suite carries most of the teeth (emulator-free); two
knives are also scored against the emulator oracle.

## K-AM1 — delete P1 (the 6-digit round)

Edit: in `sub/circleparse.asm` `cpt_boundary_prep`, replace the whole P1
block with a jump to `cbp_mul` (digits left untouched).

Prediction, written first:
- `tests/test_graphics.py`: the two single-precision teeth fail —
  `1.5707963` marshals to `(1,16383)` instead of `(2,0)` (trunc keeps it
  under pi/2); the `1.5707999` carry teeth fails the `oc == 2` half. The
  BOUNDARY_PREP oracle rows for `1.5707963`/`1.5707963267949` fail too
  (oracle says `(2,0)`). Every other row green.
- Emulator (if run): exactly ONE row of the verify set changes —
  `ctl_card_r95` reads 134 px `e3e10d24` (zerobas-before's plane) vs ref
  135 px `7babb12d`. All other rows stay byte-identical.

## K-AM2 — delete the M floor correction

Edit: in `sub/graphics.asm` `gfx_circ_wedge_prep`, skip the
`2*M*M <= r*r` compare-and-decrement (jump from after `ld (GFX_M),hl`
straight to `gwp_mok`).

Prediction, written first:
- `tests/test_graphics.py`: the M battery fails at EXACTLY r=1393 (M=985
  vs 984), r=2209 (M=1563 vs 1562), r=3025 (M=2140 vs 2139) — three of the
  410 corrected radii — and at no other listed radius. The captured-arc
  integrations stay green (radii 15/20 are not in the 410).
- No emulator run needed: the corpus radii are all clean, which is exactly
  why the correction needed the exhaustive host check to be found at all.

## K-AM3 — remove the odd-octant flip

Edit: in `sub/graphics.asm` `gfx_circ_keep`, make the parity test
unconditional even (`pos = qx` always: replace `bit 0,c / jr z,gck_norm`
+ the subtract with a plain fall-through).

Prediction, written first:
- `tests/test_graphics.py`: all six captured-arc integration rows fail
  (the float knife measured 52/54 -> 11/54 for the same cut), the KEEP
  battery fails on its odd-octant rows, the near-cardinal sweep rows
  fail. The M battery and marshalling stay green (they never touch keep).

## K-AM4 — spoke endpoint back to a nudged ray (regression knife)

Not run as an edit (the QTAB machinery is deleted); instead the unit rows
pin it: `spoke vec theta=0.01 r=15 -> (15,0)` fails if anyone reintroduces
a nudge, and `theta=1.57 r=400 -> (1,-400)` fails under the QTAB 255-cap.
