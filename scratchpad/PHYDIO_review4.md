# PHYDIO.md DRAFT 4 -- review pass 4 (test writer, 2026-11-22), ANSWERED by round 6

A fresh reviewer read only the page, the five run files (XDSK5 run 2) and xdsk1-5.asm. Its findings were mostly
COMBINATIONS (other values of measured inputs); the rule pairs among them were cheap to separate, so round 6
(XDSK6_run1.out, cases 69-73, row D) measured them:

1. Unpinned:
   - (CORE, COMBINATION) media before sector on a WRITE -> case 72: C $00 at 1440 writes nothing, 12.
   - (EDGE) memory below HL on a read; good reads of 3+ sectors -> open list.
2. Rival rules:
   - (CORE) $FF track t on image track t, or 2t (double-stepping) -> case 70 ($FF sector 16 reads case 69's
     image 18): track t. The page's rule holds.
   - (CORE) "track modulo 128" or "an 8-bit side-and-track count" (equal on two-sided media) -> case 71 ($F8
     sector 1152, track 128 one-sided): PAST. The 8-bit side-and-track count; DRAFT 4's "modulo 128" was the
     two-sided special case. NEW BEHAVIOUR, the model corrected.
   - (CORE) "B 0 = 256" or an 8-bit count running on -> not separable without the B 0 write that did not finish
     in 60 s; the rule now says what case 04 shows (B $FF after one sector), D-PHYDIOB0's text too.
   - (EDGE) the sector after $FFFF: 0 or the next physical one -> case 73: NEITHER -- 2 from $FFFF is refused up
     front (A 2, B 2, nothing read): the last sector must fit 16 bits. NEW BEHAVIOUR. zerobas reads $FFFF and the
     boot sector: D-PHYDIOWRAP16.
3. Citations: case 39's content ("the pattern's second half": it is +256..+767); D-PHYDIOB0's "reads 256
   sectors" -> fixed.
4. Open-list gaps -> listed (B 0's count, the wrap with $FF / $FA, memory below HL, 3+-sector transfers).
