- [ ] **D-GETDPBMEDIA — GETDPB READS THE DISK AND FILLS ITS FORMAT'S DPB; THE REFERENCE BUILDS IT FROM THE MEDIA BYTE IN B**
      🎚️ TIER 6 — every edge (filed 2026-11-22).
      🤖 **AUTONOMOUS** — docs/disk/GETDPB.md R-GD-DPB / R-GD-REGS (scratchpad/XDENT1_run1.out, XDENT2_run1.out): the
      VG-8020 + NMS 1200's GETDPB ($4016) fills HL + 1 .. HL + 18 with the standard format of the media byte in B
      ($F8 $F9 $FA $FC $FD $FE $FF, each its own block; C ignored) without touching the disk, carry clear, BC 0, DE =
      HL + 19. zerobas's (disk/) fills the $F9 block -- the disk's -- for every B, with A $03, F $04, B 2, DE $0007,
      HL $A412; reading the disk also restarts DSKCHG's idle clock (DSKCHG.md R-DC-UNKNOWN, XE1 6). A media-byte
      table of 7 x 18 B in disk.rom: read `make basic-reloc` (disk free) first.
