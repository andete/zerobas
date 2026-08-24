# D-HIMRANGE — predictions, written BEFORE the run (2026-08-24)

Reference rule hypothesis (from D-HIMDOM §3/§5):
  < $8000            -> ERR 5
  $8000 .. floor     -> ERR 7 (Out of memory)   [floor: program/var high-water + margin?]
  floor .. RAM top   -> accepted, HIMEM moves
  > RAM top          -> ERR 5
  >= 65536           -> ERR 6
RAM tops: VG-8020 = 62336, CF-3300 = 56951.

## (1) machine-specific upper edge — the whole point of the sweep
| row | VG-8020 | CF-3300 | agree? |
|---|---|---|---|
| u.56000 | 0 ->56000 | 0 ->56000 | AGREE |
| u.56951 | 0 ->56951 | 0 ->56951 | AGREE (== CF top; guess boundary is inclusive) |
| u.57000 | 0 ->57000 | 5 SAME | **DISAGREE** |
| u.58000 | 0 ->58000 | 5 SAME | **DISAGREE** |
| u.60000 | 0 ->60000 | 5 SAME | **DISAGREE** |
| u.62000 | 0 ->62000 | 5 SAME | **DISAGREE** |
| u.62336 | 0 ->62336 | 5 SAME | **DISAGREE** (== VG top) |
| u.62337 | 5 SAME | 5 SAME | AGREE |
| u.63000 | 5 SAME | 5 SAME | AGREE |

A DISAGREE block in [57000,62336] is the finding: the edge is per-machine
(= boot HIMEM / RAM top), NOT a constant.

## (2) current vs boot HIMEM — CAN YOU RAISE THE CEILING?
KEY ROW: t.4to6 (lower to 40000, raise to 60000).
- Hypothesis A (upper edge = LIVE HIMEM, lower-only): both refs "5 ->40000".
- Hypothesis B (upper edge = FIXED boot top, raise allowed <= top):
    VG "0 ->60000", CF "5 ->40000"  -> DISAGREE.
PRIMARY PREDICTION: Hypothesis B (raise allowed up to the fixed boot RAM top).
| row | VG-8020 | CF-3300 |
|---|---|---|
| t.4to6 | 0 ->60000 | 5 ->40000 |
| t.4to5 | 0 ->50000 | 0 ->50000 |
| t.6to4 | 0 ->40000 | 0 ->40000 |
| t.4to4 | 0 ->40000 | 0 ->40000 |
(If instead A holds: t.4to6/t.4to5 both "5 ->40000".)

## (3) ERR-7 lower edge — program-dependent, or a constant floor?
bare sweep (find where accept begins; D-HIMDOM: >32848, <40000):
- l.33000: ERR7 (guess, near floor)  [both refs]
- l.34000: accept  (LOW CONFIDENCE — floor location unknown)
- l.35000..l.39000: accept
DIM A#(1000) (double, 8008 B, high-water ~ 40777):
- p.dim38k: **ERR7 if program-dependent** (38000 < array top), else accept
- p.dim40k: ERR7 if dep (40000 < array top), else accept
- p.dim44k: accept (44000 > array top, < RAM top)
DISCRIMINATOR: p.dim38k ERR7 while bare l.38000 accepts => edge tracks allocation.

## bottom-of-RAM boundary
- b.7fff (32767): ERR 5 both (ROM side)
- b.8001 (32769): ERR 7 both (RAM side, below floor)

## zerobas (no range check yet) — expect ERR 0 / accept on EVERY row
so DIFF wherever refs agree on ERR5/ERR7: u.62337,u.63000,l.33000?,b.7fff,
p.dim* (if refs agree ERR7). The DISAGREE rows are not scored against zb.

## ============ RESULTS (run 1) — SCORED ============
Predictions vs measured:

(1) UPPER EDGE — **REFUTES D-HIMDOM'S "machine-specific" CLAIM.**
  MISS: I predicted CF refuses > 56951. It does NOT.
  Both refs ACCEPT up to 62336 ($F380) and refuse 62337. Same on BOTH machines
  despite boot HIMEM 62336 (VG) vs 56951 (CF). => the ceiling is a CONSTANT
  $F380, NOT the boot HIMEM. u.56951/u.62336 "disagreements" are just SAME-vs
  ->value artifacts (value already == boot HIMEM on one machine); both accept.

(2) CAN YOU RAISE? — HIT (hypothesis B): t.4to6 both "0 ->60000". Raising the
  ceiling back up works => the upper edge is a FIXED top, not live HIMEM.
  So zerobas does NOT need to boot-init HIMEM.

(3) ERR-7 LOWER EDGE — **REFUTES D-HIMDOM'S "program-dependent" CLAIM.**
  MISS: I predicted DIM A#(1000) pushes the floor up. It does NOT:
  p.dim38k/40k/44k all ACCEPT, identical to bare. Because CLEAR WIPES variables,
  so the array is not counted. Bare floor is between 33000 (ERR7) and 34000
  (accept) -- much tighter than D-HIMDOM's guessed (32848,40000).

REMAINING QUESTION before design: is the floor a pure CONSTANT, or does it track
PROGRAM TEXT size and STRING SPACE (n in `CLEAR n,m`)? All run-1 rows used
n=200 and a ~small program. Run 2 separates them (s.* vary n; g.* vary program).

## ============ RESULTS (run 2) ============
STRING-SPACE DEPENDENCE = CONFIRMED (floor tracks n, slope ~1):
  s.n2_42k (n=200,42000)   accept   | s.big42k (n=10000,42000) ERR7
  s.big44k (n=10000,44000) accept   | s.big33k (n=10000,33000) ERR7
  => floor(n=200) in (33000,34000]; floor(n=10000) in (42000,44000].
     delta_floor ~= delta_n (9800). floor = C + n, C in (32800,33800].
PROGRAM-PAD rows g.pad34k/38k -> <NO HIMEM> (60-line inject broke the readout).
  Re-run with fewer/longer lines.

DESIGN emerging: floor = PRGEND + POOLSIZE + MARGIN (tracks program + string
space, both faithful). MARGIN chosen so (PRGEND+MARGIN) in (32800,33800] for a
small program. Need: (a) confirm program-TEXT dependence, (b) zerobas PRGEND for
a small program, to set MARGIN from the measured reference floor (not guessed).

## ============ RESULTS (run 3) ============
NARROW FLOOR (n=200, 5-line case() program):
  f.33200/33400/33600 -> ERR7 ; f.33800/33900 -> accept (both refs).
  => floor in (33600, 33800]. (l.33000 ERR7, l.34000 accept consistent.)
  These are now DIFFERENTIAL rows: zerobas must give f.33600 ERR7, f.33800 accept.

zerobas PRGEND ($E026):  empty(2 lines 10,900)=32798 ; 8x REM200=34454.
  (TXTBASE=$8001=32769; 2-line prog = 29 B.)

g3.pad rows -> <NO HIMEM> again (long REM text floods the before/after capture);
  program-TEXT slope not directly measured, but MS-BASIC floor = end_of_prog +
  string_space + STACK_MIN is standard, and using zerobas PRGEND makes the floor
  track program text automatically.

DESIGN: floor = PRGEND + POOLSIZE + MARGIN, target floor ~33700 for the 5-line
  n=200 program. Need exact PRGEND for that program to set MARGIN.
  Upper edge (ERR5): value > $F380 (62336), CONSTANT on both machines.
  Lower edge (ERR5): value < $8000.

## ============ RESULTS (run 3b) — DESIGN LOCKED ============
Floor for the exact 5-line n=200 program: f.33700 ERR7, f.33750 accept
  => floor in (33700, 33750].
zerobas PRGEND for that exact program (CLEAR 200,33700) = 32843.
  MARGIN = floor - PRGEND - POOLSIZE = (33700,33750] - 32843 - 200 = (657, 707].
  CHOICE: MARGIN = 680 (centre) -> floor = 32843+200+680 = 33723, inside window.

FINAL RULE (both refs, all measured):
  value >= 65536        -> ERR 6   (eval_addr, already handled)
  value >  $F380(62336) -> ERR 5   (CONSTANT top, not boot HIMEM)
  value <  $8000        -> ERR 5
  $8000 <= v < floor    -> ERR 7   floor = PRGEND + POOLSIZE + 680
  floor <= v <= $F380   -> accepted, HIMEM moves

TWO-RULES-COINCIDE CHECKS (the D-CLRFIX trap):
  * "constant top vs boot HIMEM": SEPARATED by u.57000..u.62336 (both accept
    despite CF boot HIMEM 56951) and t.4to6 (raise works). -> CONSTANT top.
  * "constant floor vs program/stringspace-dependent": SEPARATED by s.big42k
    (n=10000 -> ERR7 where n=200 accepts) proving string-space dependence, and
    p.dim* (variables DON'T count, they're wiped). Program-text dependence is
    carried by PRGEND (standard MS-BASIC end-of-program+strings+stack floor).

## ============ FIXTURE REPAIR (basic_probe_arrays.py) ============
`CLEAR 200,&H8050` (=32848) is now ERR 7 (below floor) -- it can no longer set a
tight ceiling, because the floor GUARANTEES >=678 B of headroom (matching the
references, which reject &H8050). So the two chain-OOM fixtures must consume that
room another way. MEASURED (empty program, direct mode):
  room [PRGEND+2, POOLBASE) ~= 14899 B  (POOLBASE = TXTMAX-POOLSIZE = 47672).
  DIM Z(N) double fit boundary: N<=1852 fits, N>=1856 -> DIM OOMs.
  N=1840 -> array fits (~104 B margin), leaves ~18-scalar gap; of A$..Z$ the
  last 8 OOM (Z$ included). -> FIX: CLEAR 200,50000 : DIM Z(1840), keep A-Z.
  Still exercises the SAME str_set_key scalar-chain-OOM path (the region is full;
  the array just fills the room the tight ceiling used to deny).
