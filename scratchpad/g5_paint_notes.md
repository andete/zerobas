# G5 PAINT — characterization notes (VG-8020 black box)

## Round 1 (g5_paint_char1.py) — SOLID PINS

### Grammar (C1, crunch is permissive; runtime enforces)
- `PAINT` = token `$BF`, `STEP` = `$DC` (matches G1 pins).
- Small int consts: digits 0..9 → `$11..$1A`; 10..255 → `$0F nn`.
- `PAINT(x,y)`               → `BF ( x , y )`
- `PAINT(x,y),c`             → `... , c`
- `PAINT(x,y),c,b`           → `... , c , b`
- `PAINT STEP(x,y),c,b`      → `BF _ DC ( ... )` (STEP after PAINT)
- `PAINT(x,y),,b`            → `... ) , , b`  (omitted colour = bare comma)
- `PAINT(x,y),"AB",b`        → CRUNCHES FINE (string tile stored). MSX2 form;
                                MSX1 runtime behaviour = round-2 TODO (Type mismatch?).
- `PAINT(x,y),c,b,7`         → CRUNCHES FINE (4th arg stored). Runtime TODO.
- ⇒ tokeniser needs NO work; grammar accepted generically. Enforcement is at run.

### Work area (C5) — PIN
- After `PAINT(28,28),...`: `GRPACX/Y = (28,28)` AND `GXPOS/GYPOS = (28,28)`.
  Both set to the SEED point (like PSET sets them to its point).

### Errors / edges (C6) — PINS
- `SCREEN 0` PAINT → ERR 5 ; `SCREEN 1` PAINT → ERR 5.
- colour 16 → ERR 5 ; colour −1 → ERR 5  (paint-colour range-checked 0..15).
- coord 32768 (>int16) → ERR 6 (Overflow, eval domain — same as all gfx).
- **border 16 → NO error (K).** Border value NOT range-checked (masked? round 2).
- **off-screen seed (300,300) → ERR 5** (in-int16 but off-screen).
- **off-screen seed (−5,−5)  → ERR 5.**
  ⇒ DISTINCT FROM PSET/LINE: PAINT does NOT silently no-op / clip an off-screen
    SEED — it raises ERR 5. (int16-domain coords still ERR 6 first.)

## Methodology bug in round 1 (FIX for round 2)
C2/C4 captured pattern plane and colour plane in TWO SEPARATE openMSX boots →
inconsistent snapshot (the C2 top/bottom split at exactly seed-scanline y=28 is
the tell — the two boots caught PAINT at different progress or post-states).
FIX: capture pattern+colour segments in ONE `vram_segs` call (concatenate seg
lists, split the returned hex), and settle long enough that PAINT has completed
(verify by double-capture stability).

## Round 2 — THE HARNESS TRAP (resolved 2026-07-21)
Early round-2 fill captures showed uniform colour / apparent "hangs". NOT a hang
and NOT a reference bug: **MSX PAINT is SLOW in EMULATED time**; the harness
default `step=2.5` (emulated s) fired the VRAM/screen capture MID-FILL, before
PAINT finished. Signature: "no-done" cases returned in ~0s WALL (throttle-off
runs emulated time fast) — a real wall hang would show ~timeout seconds.
FIX: give small fills `step>=30` (emulated s). Then every fill COMPLETES in ~1s
wall (`g5_budget.py`: arena+smallbox fill4 -> DONE). Colours 1 (=BAKCLR, clash
CLEARS -> ~no writes) and 15 (=border, self-terminates) completed even at
step=2.5 because they do ~zero work; 4/9/14 (actually set bits) needed the budget.
POINT() is the reliable pixel oracle (query IN SCREEN 2, stash to vars, PRINT in
SCREEN 0); the scratch VRAM effective-colour renderer had an addressing bug —
use the existing graphics-acceptance capture for the gate, POINT for char.

## Round 2 confirmed pins
- Box drawn by LINE ,B is real (POINT boxonly: border=15, interior/outside=1).
- fill15,border15: interior->15, outside untouched (clean bounded fill).
- tile$ form `PAINT(x,y),"A",15` -> ERR 13 (Type mismatch) at RUNTIME.
- 4th arg `PAINT(x,y),c,b,7` -> ERR 2 (Syntax error) at RUNTIME.
- Fill colour clash = SAME rule as PSET (c==bg nibble -> clear bit/keep colour;
  else set bit + fg=c). ⇒ PAINT can reuse the G2/G3 gfx_plot_cur primitive.

## ★ FINAL PAINT SEMANTICS (VG-8020 measured, POINT-verified) ★
1. Grammar `PAINT [STEP](x,y)[,C[,B]]`; crunch permissive; STEP=$DC.
   - tile$ `PAINT(x,y),"A",B` → ERR 13 (Type mismatch) at RUN.
   - 4th arg `PAINT(x,y),C,B,7` → ERR 2 (Syntax) at RUN.
2. Coord: STEP-rel vs absolute (like PSET); coord >int16 → ERR 6.
3. Seed off-screen (in int16 but x∉0..255 OR y∉0..191, incl. negative) → **ERR 5**
   (DISTINCT from PSET/LINE, which clip/no-op an off-screen point).
4. SCREEN 0/1 → ERR 5.
5. Paint colour C: omitted → FORCLR; C<0 or C>15 → ERR 5.
6. Border B: omitted → **= C (the paint colour)**; NOT range-checked (16 → no err,
   just a comparison value that no 0..15 pixel matches → floods).
7. FILL = 4-connected flood from seed, each pixel painted with the G2 colour-clash
   RMW (c==bg nibble → clear bit/keep colour; else set bit + fg=c). Border test =
   effective pixel colour == B → stop (LIVE, reads post-clash colour).
8. ⇒ SCREEN-2 consequence (measured, robust across thin box AND 8px group-aligned
   arena — both proven-enclosing via a fill15 control that stayed bounded):
     • **C == B → BOUNDED** connected region (painted pixels read back as B → self-limit).
     • **C != B → FLOODS THE ENTIRE SCREEN** with C, clipped to 0..255 × 0..191
       (adjacent border pixels' 8-group foreground is overwritten to C → border eaten
       → fill escapes; reaches far corner (200,150)). No wrap, no error.
   The final bitmap is TRAVERSAL-ORDER-INDEPENDENT (bounded set OR whole screen) →
   the ROM may use ANY correct flood algorithm and still be byte-faithful. Big win
   vs G3/G4 (there the exact Bresenham/midpoint order was load-bearing).
9. Work area after PAINT: GRPACX/Y = GXPOS/GYPOS = the SEED (x,y).
10. Defaults verified: `PAINT(x,y)` → C=FORCLR, B=C ; `PAINT(x,y),,B` → C=FORCLR.

## D3 stack-overflow (measured 2026-07-21)
Reference PAINT stack grows DOWN from STKTOP (Z80 stack, near HIMEM). Overflow is
HARD to hit: box + ~73 full-height parallel channels (comb step3) completes at
normal HIMEM AND down to himem=$8800. Only at **himem=$8500** (pathologically
tight) does `PAINT(126,170),15,15` raise **"Out of memory in 60" = ERR 7**.
(CLEAR resets ON ERROR, so it surfaced as the direct message.)
⇒ D3 PIN: **PAINT stack overflow → ERR 7 (Out of memory)**. Realistic fills never
overflow → size our fixed span stack generously (target >=128 spans); overflow →
ERR 7. `g5_overflow3.py`.

## Implementation shape (implied)
- Tenant GFX_OP=5: scanline flood fill, segment stack in own-design PAINT scratch
  RAM (LINEBUF region, like G3), EI-between-segments / DI-per-pixel-RMW; reuses
  gfx_plot_cur (paint) + gfx_point (effective-colour border test). NO new pixel math.
- Resident ex_paint: parse (STEP)(x,y),C,B ; STEP/abs ; off-screen seed → ERR 5 ;
  SCREEN 0/1 → ERR 5 ; C range 0..15 → ERR 5 ; defaults C=FORCLR, B=C ; set
  GRPAC/GXPOS=seed ; marshal seed+C+B ; one subrom_call.
- Acceptance (tractable): bounded cases (C==B closed region → exact POINT bitmap)
  + flood cases (C!=B → sample several points all == C) + error cases. Compare
  EFFECTIVE colour (POINT), not raw planes (bit-vs-bg is unobservable/impl-free).
- BUDGET: big emulated step (>=30s) so PAINT completes before capture.

## SPACE ANALYSIS (task 3)
- Fresh tail: `__MEAS_PAGE1_END=$7FB0` → **80 B free** in the page-1 tail.
- Resident cost is ONLY ex_paint (flood-fill engine is a sub-ROM tenant, ~7 KB free
  there; GFX_B marshalling cell + PAINT segment stack are RAM, not ROM).
- ex_pset+ex_preset+gfx_plot_stmt = $5B0C-$5AD9 = 51 B (setup+coord+one color arg).
- ex_paint est. **~130–150 B**: SCREEN2-check + parse_coord + off-screen-seed→ERR5 +
  colour parse w/ 0..15 range→ERR5 (stricter than PSET's `and $0F`) + border parse
  (default=C) + `,,B` empty-colour form + 4th-arg→ERR2 reject + GRPAC/GXPOS=seed +
  GFX_OP=5 marshal. ⇒ **overrun ~50–70 B** — same wall as G4 but MUCH smaller
  (ex_circle was 883 B / overran 808 B; ex_paint is a fraction of that).
- DRY lever (measured, not yet applied): the optional-",c" colour parse is
  inline-DUPLICATED in ex_pset (l.50–64) AND ex_circle/circ_c (l.396–409, incl. the
  `,,` empty-field handling). Factor a shared "parse optional colour field (default
  in A, range-check flag)" leaf → shrinks ex_pset AND ex_circle AND serves ex_paint.
  Likely frees the ~50–70 B WITHOUT an eviction. Fallback: a small self-contained
  eviction (G4 precedent). DECISION: DRY-first; measure ex_paint empirically during
  impl before declaring an eviction need (recurring lesson: measure, don't guess).

## Round 2 TODO (DONE — kept for history)
1. Single-boot dual-plane capture of a bounded fill (box in colour A, PAINT
   interior colour B, border=A). Read the TRUE consistent result.
2. Boundary-colour semantics: what "pixel colour" does the border test compare
   against on SCREEN 2 (effective fg/bg via the attribute byte)? Fill LEAK when
   border != drawn colour.
3. Colour-clash interaction: a fill spanning multiple 8-pixel groups; a group
   that holds BOTH border-colour and fill-colour pixels (unavoidable clash).
4. Concave / U-shaped region (does it wrap around? scanline-seed correctness).
5. border=16 actual effect; tile$ runtime; 4th-arg runtime.
6. Host-fit an exact flood-fill model to captured bitmaps → committed oracle
   (g5_paint_fit.py + g5_pointsets.json), teeth-proven.
