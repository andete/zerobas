<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# `PHYDIO` ($0144) — read or write physical disk sectors

> **Spec:** FINAL (2026-11-22), the core rule: review pass 5 found no new behaviour and no unpinned core
> rule, only combinations of measured rules (now [A] below) and three citations, fixed (docs/spec-method.md
> §7, the small-call stop). Six measured rounds; rounds 3-6 answer passes 1-4 (scratchpad/PHYDIO_review1.md
> to review5.md: the geometry model, the 8-bit side-and-track count, the 16-bit refusal). Measured on the VG-8020, alone and with an NMS 1200 disk interface.

## Summary

`PHYDIO` is the BIOS's door to the disk interface: it passes the call on through the hook H.PHYD
($FFA7), which a disk interface fills at start-up. With no interface the hook is a bare `RET`, and the
call changes nothing. With one, it reads (carry clear) or writes (carry set) B physical sectors of
drive A, starting at sector DE, from or to memory at HL; C is the media byte, and it names the
disk's geometry: $F9 2 sides x 9 sectors x 80 tracks, $F8 1 x 9 x 80, $FA 1 x 8 x 80, $FF 2 x 8 x 40
(the standard formats). A sector number is a place on that disk -- track = sector / (sides x sectors
per track), then side, then sector -- and a track number at or past the media's count is past the
end. The side-and-track count (sector / sectors per track) is kept in 8 bits, so some sector numbers
far past the end wrap back onto the disk ($0900 and $1200 read the boot sector with $F9); a transfer
whose last sector does not fit in 16 bits is refused before any sector. Sectors go in order across sides and tracks, and a write
takes its data from HL. B 0 starts the sector count at 0, counting down in 8 bits (after one sector it
reads $FF); how far it runs is not measured.

A good transfer returns A 0, F $42 and B 0, C $32, D 0 and E the entry F (D is the entry A or a
constant: A was 0 throughout); HL is kept. A
failure returns an error code in A with the carry set and B the sectors not transferred: 2 for a read
past the disk's last sector, 8 for a write past it (the sectors before the end are transferred first),
12 for a media byte the interface does not take ($00, $32, $80, $F0, $F7: checked before the sector,
on a read and on a write). Interrupts are off after the call.

zerobas's diskless build does the same. Its disk build places sectors by the same geometry and wraps the
same 8-bit count, but gives $FF disks 80 tracks, wraps a transfer past sector $FFFF to sector 0, answers every register differently, gives other
error codes, takes every media byte, and transfers nothing for B 0 (below).

**A third interface.** The NMS 8250's built-in drive (MSX2; rows E, scratchpad/XDSK1_nms8250.out to XDSK6_nms8250.out) moves the
same bytes and answers the same A, F and B in every case but two kinds: it refuses media byte $FF (A 12, as an
unknown byte), and the first call after start-up, a track-1 read, got track 0's sector (R-PD-FIRSTE). Its C,
DE and interrupt state after the call (ON) are its own.

## The specification

References: the Philips VG-8020's main BIOS, alone (row `N`) and with an NMS 1200 disk interface
(row `D`). Ours: the C-BIOS repack, diskless on row `N`, the disk build on `D`.

**Evidence.** **[XP rNN]**: case `NN` on row `r` -- cases 00-10 from the XDSK1 probe, run 2
([`scratchpad/XDSK1_run2.out`](../../scratchpad/XDSK1_run2.out)), cases 11-19 from XDSK2, run 1
([`scratchpad/XDSK2_run1.out`](../../scratchpad/XDSK2_run1.out)), cases 20-36 from XDSK3, run 2
([`scratchpad/XDSK3_run2.out`](../../scratchpad/XDSK3_run2.out)), cases 38-53 from XDSK4, run 1
([`scratchpad/XDSK4_run1.out`](../../scratchpad/XDSK4_run1.out)), cases 54-68 from XDSK5, run 2
([`scratchpad/XDSK5_run2.out`](../../scratchpad/XDSK5_run2.out); run 1,
[`XDSK5_run1.out`](../../scratchpad/XDSK5_run1.out), lacked case 68), cases 69-73 from XDSK6, run 1
([`scratchpad/XDSK6_run1.out`](../../scratchpad/XDSK6_run1.out)). `probes/bios/spec/xdsk1.asm` to
`xdsk6.asm` document the frame, the case tables and the 14-byte record:
- The probe is a 16 KB "AB" cartridge whose INIT only hooks H.STKE: a disk interface in a later slot is
  initialised after it, and H.STKE runs once every ROM has been. Drive A holds a fresh copy of the
  generated empty 720 KB disk (`disk/empty720.dsk`), the same image on both machines.
- Each case fills the 1 KB buffer with $E5 (or, for a write, 256 pairs `$77 + n, -n` then $E5), sets A
  (always 0, drive A: another drive would ask for a disk), F (bit 0, the carry: write), B, C, DE, HL
  and the interrupt state, calls PHYDIO, and records A, F, B, C, D, E, H, L, the interrupt state
  (read twice), the buffer's 16-bit sum and its bytes +0 and +512.
- Round 1 (00-10) runs on one disk in order: case 06 writes sector 1439, so 07 and 10 read the pattern
  back from there (08 and 09 read sector 0). Round 2 (11-19) starts from a fresh copy. Case 04 (B 0) started at sector 0 in run 1, and the
  VG-8020 + NMS 1200 never returned (256 sectors read over the probe); run 2 starts it at 1439.
- Round 3 (20-36) starts from a fresh copy; case 23 (2 sectors from 1439) writes 1439 and stops at 1440,
  so 24-36 find the pattern there. Its run 1 ([`XDSK3_run1.out`](../../scratchpad/XDSK3_run1.out)) had a
  case 37, a WRITE of B 0 (256 sectors) from 1184: the VG-8020 + NMS 1200 had not returned when the 60 s
  limit ended the run (never returning and still writing look the same), so it is out.
- Round 4 (38-53) starts from a fresh copy: case 38 writes sector 9 from $A400 (the pattern) and case 39
  sector 8 from $A500 (the buffer's bytes +256 to +767: pairs 128-255, then 256 bytes $E5 -- another
  content), sector 18 stays zero -- so which IMAGE
  sector a read with $F8 / $FF / $FA reaches shows in the buffer. A case's buffer can differ from its HL
  (case 39); the record's sum is the buffer's.
- Round 5 (54-68) starts from a fresh copy and writes three different contents first: sector 9 from $A400,
  8 from $A500, 18 from $A480, so each later read names the image sector it reached (its sum and two bytes
  differ for each).
- Round 6 (69-73) starts from a fresh copy: case 69 writes sector 18 from $A480, then $FF sector 16
  (track 1) and $F8 sector 1152 (track 128 of a one-sided disk), a refused-media write past the end, and
  2 sectors from $FFFF.

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/bios/spec/xphydio_rules.py -- do not edit; `python3 tools/spec_rules.py probes/bios/spec/xphydio_rules.py --write` -->

**9 rules; 9 hold on the reference. Of the 2190 recorded outputs (each case's cursor, cells, A, table entries ...): 2190 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. PHYDIO ($0144): a physical sector read or write through the disk interface

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-PD-NODISK** With no disk interface (row N) PHYDIO returns at once: A, F, BC, DE, HL and the interrupt state as entered; the buffer is not touched. | 73 | ✓ | ✓ |
| **R-PD-READ** A read (carry clear) with an accepted media byte ($F8, $F9, $FA, $FF measured; $FF not on the NMS 8250, R-PD-MEDIA) and the sectors within the disk its GEOMETRY names ($F9 2 sides x 9 sectors x 80 tracks, $F8 1 x 9 x 80, $FA 1 x 8 x 80, $FF 2 x 8 x 40) puts sectors DE, DE + 1, ... in that order (case 43: the FAT second) into memory from HL ($A400 and $8000 measured), each from the place the geometry gives it ($F8 sector 9 is track 1: the image's sector 18; $FF sector 8 is side 1: image 9) and returns A 0, F $42, B 0, C $32, D 0 (the entry A, 0 in every case), E = the entry F, HL as entered. Cases 07 and 24 read back what cases 06 and 23 wrote. On the NMS 8250 (row E) C is $3C and DE a working value; its one exception is R-PD-FIRSTE. | 51 | ✓ | ✗ 28: XP D00, XP D01, XP D02, XP D05, XP D07, XP D08 … (+22) |
| **R-PD-WRITE** A write (carry set) of sectors within the disk writes them (cases 07 and 10 read case 06's pattern back from 1439, 57 case 55's -- taken from HL $A500 -- from 8, 67 case 66's), entered with interrupts on or off, and returns as a read does: A 0, F $42, B 0, C $32, D / E the entry A / F, HL as entered; the buffer is not changed. | 16 | ✓ | ✗ 8: XP D06, XP D38, XP D39, XP D54, XP D55, XP D56 … (+2) |
| **R-PD-PAST** A read that reaches a sector whose TRACK is at or past the media's track count -- the track from the side-and-track count sector / (sectors per track) kept in 8 BITS (sector 1440 with $F9, 720 with $F8, 700 and 1439 with $FF; $F000: 6826 = 170, track 85; $F9 3780: 420 = 164, track 82; $F8 1152: 128, track 128) -- reads the sectors before it, then stops: A 2, F $41, B = the sectors not read, C 0, D / E the entry A / F (E $5A in case 27), HL as entered ($A400, $8000). B 0 counts as 256 (case 04: one sector read from 1439, B $FF left: the count runs down from 0 in 8 bits -- how far it can run is not measured). A transfer whose last sector does not fit 16 bits is refused before any sector: 2 from $FFFF gives A 2 with B 2 (case 73), where 1 from $FFFF reads. | 26 | ✓ | ✗ 14: XP D03, XP D04, XP D10, XP D14, XP D15, XP D21 … (+8) |
| **R-PD-WPAST** A write that runs past the last sector writes the sectors before it (case 23: 2 from 1439 writes 1439 -- case 24 reads it back -- and stops at 1440; case 64, 3 from 1439, leaves B 2), then stops: A 8, F $11, B = the sectors not written, C 0, D / E the entry A / F (E $FF in case 29), HL as entered; the buffer is not changed. | 12 | ✓ | ✗ 6: XP D17, XP D23, XP D26, XP D29, XP D53, XP D64 |
| **R-PD-FFFF** A sector number past the disk whose side-and-track count WRAPS (8 bits) back onto it is NOT refused: it returns as a good read (A 0, F $42, B 0, C $32, D / E the entry A / F, HL as entered). $F9 sector $1200 (count 512 = 0) and $0900 (256 = 0) read the BOOT sector; $FFFE / $FFFF (7281 = 113: track 56, side 1) read a zero sector (which one is not separated). | 8 | ✓ | ✗ 4: XP D16, XP D30, XP D50, XP D65 |
| **R-PD-MEDIA** A media byte the interface does not take ($00, $32, $80, $F0, $F7 measured; on the NMS 8250 $FF too) refuses the call before any transfer -- before the sector check too (case 36 reading, 72 writing: $00 and sector 1440 give 12), entered with interrupts on (case 25), and for a WRITE (case 44: nothing written, case 45 reads the sector unchanged): A 12, F $89, B as entered (1, 2, 0), C 0, D / E the entry A / F (E $A4 in case 28), HL as entered; the buffer is not touched. | 32 | ✓ | ✗ 13: XP D11, XP D19, XP D25, XP D28, XP D32, XP D33 … (+7) |
| **R-PD-FIRSTE** On the NMS 8250, round 3's FIRST call after start-up -- sector 9 with C $F8, which that media byte puts on TRACK 1 -- returns A 0, F $42, B 0 as a good read, but the bytes are the disk's BOOT sector (track 0), measured twice (scratchpad/XDSK3_nms8250.out, and XDSK3_nms8250_b.out byte for byte the same); the same read later (cases 40, 58) gets track 1's sector, as on the NMS 1200. Whether every first call that needs a seek reads the wrong track is not separated (round 1 starts on track 0). | 1 | ✓ | ✓ |
| **R-PD-DI** With a disk interface, the interrupt state after the call is the INTERFACE's, whether they were on or off before it: OFF on the VG-8020's NMS 1200, ON on the NMS 8250 (row E) -- a caller cannot count on either. | 146 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

| TODO item | rules zerobas fails |
|---|---|
| **D-PHYDIOREGS** (zerobas's DSKIO returns other F, C, DE and HL: F $44 on a good transfer and $09 / $0B on an error, C and DE / HL working values) | R-PD-READ, R-PD-WRITE, R-PD-FFFF, R-PD-WPAST, R-PD-PAST |
| **D-PHYDIOPAST** (a read past the last sector returns error 8, not 2) | R-PD-PAST |
| **D-PHYDIOB0** (B 0 transfers nothing; the VG-8020's NMS 1200 reads -- one sector from 1439, then B $FF) | R-PD-PAST |
| **D-PHYDIOGEOM** ($FF disks get 80 tracks: sector 700 is read, the reference's 40-track $FF refuses it) | R-PD-PAST |
| **D-PHYDIOWRAP16** (a transfer past sector $FFFF goes on at sector 0: 2 from $FFFF reads $FFFF and the boot sector; the reference refuses it up front, A 2, B 2) | R-PD-PAST |
| **D-PHYDIOMEDIA** (media bytes $00, $32, $80, $F0, $F7 are taken -- sector 0 read -- the reference refuses them with error 12, before the sector check) | R-PD-MEDIA |

## Open (not measured)

- **[A]** Drives other than A (not tried: the probe's interface has one drive, and drive B would be the
  phantom drive asking for a disk -- an expectation, not a measurement); the media bytes other than
  those measured ($00 $32 $80 $F0 $F7 refused; $F8 $F9 $FA $FF taken); each geometry's last track
  exactly ($F8's 79 in / 80 past is measured; $FF tracks 0 and 1 in, 43 / 89 past; $FA sectors 0, 8, 9
  -- the 40 / 80 tracks for $FF / $FA rest on the formats); a write-protected disk; a disk that is not
  there; a read error.
- **[A]** The geometry for WRITES with a media byte other than $F9; writes to wrapped sector numbers;
  which zero sector $FFFE / $FFFF reach, and which side / track a wrapped count other than 0 selects
  ($0909, $0912); the 8-bit wrap with $F8 / $FF / $FA (measured wrapping with $F9; with $F8 only that
  count 128 does NOT wrap -- 8 bits or more); where
  a write refused for its media byte might have gone under another geometry (only its own sector was read
  back); memory just below HL on a read (HL was always the buffer's start).
- **[A]** A write of B 0 (256 sectors) -- not finished within 60 s (round 3 run 1): the one case that
  would show how far B 0's count runs (256, or on until the end); good transfers of 3 or more sectors;
  writes of more than one sector within the disk; writes with F other than $01 / $FF.
- **[A]** Memory at HL other than $A400, $A500 and $8000 (page 1, where the disk ROM itself sits, and
  page 0); transfers longer than 1 KB (case 15 reads 2 sectors, the whole buffer); memory past HL + 1 KB.
- **[A]** Whether D (and C, B on return) depend on the entry A or are constants (A was 0 in every case;
  A 1 is drive B); A on row N with A other than 0.
- **[A]** The 16-bit up-front refusal, measured on one read (2 from $FFFF): on a WRITE (its error code,
  and whether $FFFF is written); its scope (2 from $FFFE: the last sector $FFFF fits -- read, or refused
  as "starting past the end"); with B 0 (does the check count 256); its order against the media check.
- **[A]** IX, IY, the alternate registers and SP; the work area; the time it takes.
- **[A]** The CF-3300 (the second reference).

## Related pages

[The disk concept page](../concepts/disk.md); the BIOS calls in [the index](index.md).

## Tests that cover it

**`spec-live`** ([tools/spec_live.py](../../tools/spec_live.py), in every gate): every rule above, run live on zerobas against these cases' measured reference values. It fails if a rule fails that *Differences from the reference* does not name, or a named one holds ([docs/spec-method.md](../spec-method.md) §8).

Also the suites `tools/entry_table.py --bios` lists for $0144.
