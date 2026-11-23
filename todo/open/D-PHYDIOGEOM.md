- [ ] **D-PHYDIOGEOM — A $FF DISK HAS 80 TRACKS IN ZEROBAS'S DSKIO; THE REFERENCE'S HAS 40**
      🎚️ TIER 6 — every error (filed 2026-11-22).
      🤖 **AUTONOMOUS** — docs/bios/PHYDIO.md R-PD-PAST (scratchpad/XDSK4_run1.out D49): PHYDIO with media $FF,
      sector 700 (track 43 of a 2-side x 8-sector disk): the VG-8020 + NMS 1200 refuses it as past (A 2), zerobas's
      DSKIO reads it. Both place sectors by the media byte's geometry and wrap the same 8-bit side-and-track count; only the track
      count differs ($FF: 40 tracks on the reference, the standard 2DD-40 format). The fix is DSKIO's (disk/), with
      D-PHYDIOMEDIA's; disk.rom's room: read `make basic-reloc` first.
