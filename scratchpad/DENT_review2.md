# GETDPB.md / DSKCHG.md DRAFT 2 -- review pass 2 (one test writer, 2026-11-22), ANSWERED by XDENT4 / XDENT5

Measured (row D):
- (CORE) C unlike the disk inside the B 1 window -> XE4 1: B 1, C plays no part there.
- (CORE) B $FF only on a first call? -> XE4 2 (a later read, C $F8): B $FF. Any read compares C.
- (CORE) an 8-bit count that wraps -> XE4 5 (304 interrupts): reads. No wrap.
- (CORE) does MTOFF restart the count -> XE4 3-4 (MTOFF at 96, then DSKCHG): reads. No. (The page's XE3 9 citation
  for it was wrong: fixed.)
- (CORE) does GETDPB touch the drive -> XE5 0 (drive A EMPTY): the same block, carry clear. No.
- (CORE) does DSKCHG read, or answer from a kept byte -> XE5 1 (drive A EMPTY, first call): carry set, A 2 (not
  ready). It reads. New rules R-DC-NOTREADY / R-DC-NRREGS.
Not measurable with the probe frame's one empty 720 KB image (open lists): which on-disk byte DSKCHG compares and
fills from (boot media byte / FAT ID / BPB), a real swap, a disk of another format, an invalid C on a read, DE / HL
on entry, whether GETDPB reads HL + 0.
Citations fixed: GETDPB's evidence legend ([XE3 n]); D-DSKCHGTIME's "~150" (its bound is 97-144).
