# PHYDIO.md DRAFT 3 -- review pass 3 (test writer, 2026-11-22), ANSWERED by round 5

A fresh reviewer read only the page, XDSK1_run2 / XDSK2_run1 / XDSK3_run1-2 / XDSK4_run1 and xdsk1-4.asm. Its
findings, and what answered each (XDSK5_run2.out, cases 54-68, row D):

1. Unpinned:
   - (CORE, NEW BEHAVIOUR) that a write takes its data from HL -> case 57 reads case 55's write (from $A500)
     back: +0 $F7, the pattern's second half. Pinned.
   - (CORE) 2-sector transfers across a side / track change -> cases 61 (F9 8-9: side 0 to 1), 62 (F9 17-18:
     track 0 to 1), 63 (FF 7-8): in order, each from its geometric place.
   - (CORE) "$F8 / $FA reach image 18" shown only as a zero sector -> cases 56 / 58 / 59: image 18 written
     with its own content, read back by $F8 sector 9 and $FA sector 8. And $FA is 1 x 8, not 1 x 9 (case 60).
   - (CORE) write-past B only ever 1 -> case 64: 3 from 1439 leaves B 2.
   - (EDGE) a good write entered with EI -> case 66 (interrupts off after), 67 reads it back.
2. Rival rules:
   - (CORE) the track wrap modulo 256 / modulo 128 / a signed compare -> case 65 (track 128: reads the BOOT
     sector -- not modulo 256) and case 68 (track 210: past -- not a signed compare). MODULO 128. The DRAFT 3
     rule (modulo 256) was WRONG; fixed.
   - $FA 1 x 8 vs 1 x 9 -> case 60.
   - (CORE) a refused-media write writing elsewhere -> not measured; open list.
3. Citations: the Open list's "$F8 79 in / 80 past" (measured: cases 48 / 21) and "$FA only sector 8"
   (case 35 read sector 0); R-PD-FFFF's "each the image sector its place names" for zero sectors; R-PD-WRITE
   citing case 23 (R-PD-WPAST's); R-PD-MEDIA's "with interrupts on" (the ENTRY state) -> all fixed in DRAFT 4.
4. Open-list gaps -> answered above or listed.

Also found while answering: the probes' write pattern is ($77 + n, -n), not ($77 + n, n) -- fill_pat's second
byte is the DJNZ counter, counting down. Equal sums over 512 bytes hid it until round 5 read partial slices;
the rules' model and every probe's comment are corrected.

zerobas (row D) in round 5: the same mapping, order, write source and modulo-128 wrap; its differences stay
the filed items'.
