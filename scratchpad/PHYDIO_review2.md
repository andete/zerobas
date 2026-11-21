# PHYDIO.md DRAFT 2 -- review pass 2 (test writer, 2026-11-22), ANSWERED by round 4

A fresh reviewer read only the page, XDSK1_run2 / XDSK2_run1 / XDSK3_run1 / XDSK3_run2 and xdsk1-3.asm. Its
findings, and what answered each (XDSK4_run1.out, cases 38-53, row D):

1. Unpinned (CORE unless marked):
   - non-$F9 media read only at sector 0: which IMAGE sector does $F8 sector 9 / $FF sector 8 / $FA sector 8
     reach? -> cases 38-42: by GEOMETRY ($F8 9 -> image 18, $FF 8 -> image 9, $FA 8 -> image 18). New behaviour.
   - the multi-sector order (every second sector so far was zeros) -> case 43: B 2 from 0, +512 = $F9 (the FAT).
   - a WRITE with a refused media byte -> cases 44 / 45: refused (12), nothing written.
   - "B as entered" on a refusal only with B 1 -> cases 46 / 47: B 2 and B 0 kept.
   - the $F8 bound between 10 and 720 -> case 48: 719 read.
   - (EDGE) HL on the error paths only $A400 -> cases 51-53: $8000 kept.
   - (EDGE) row N "A as entered" only with A 0 -> NOT measured (A 1 is drive B on row D); open list.
2. Rival rules:
   - "the media byte sets the SIZE" against "the end is a TRACK count, the track number 8 bits" -> case 49
     ($FF sector 700: past -- the size rule's 640, and a 40-track $FF) and case 50 ($F9 sector $1200 = track 256:
     reads the BOOT sector -- the wrap). Neither alone: the rule is a per-media TRACK count compared modulo 256.
     It explains $FFFE / $FFFF (track 56: read) and $F000 (track 85: past) too. New behaviour.
   - case 15's "reads the sectors before it" vs a repeated / other zero sector -> case 43 (order).
   - (EDGE) the B 0 write "never returned" vs "still running at the 60 s limit" -> the page now says the two
     look the same; not re-run.
3. Citations: "cases 07-10 read the pattern" (08 / 09 read sector 0), "case 23 writes 2 sectors" (it writes 1),
   the Summary's "640 for $FF and $FA" as fact, "checked before anything else", D-PHYDIOREGS' error-path F,
   the probe's 16-bit-wrap hypothesis -> all fixed in DRAFT 3.
4. Open-list gaps: $F8's exact end, the refused-media write, the non-$F9 mapping, HL / B on errors, writes to
   wrapped sectors, the drive-B claim -> answered above or listed as [A].

zerobas (row D) in round 4: the same geometry mapping and the same track wrap; $FF sector 700 is READ (80
tracks for $FF) -- D-PHYDIOGEOM; it writes with a refused media byte (D-PHYDIOMEDIA).
