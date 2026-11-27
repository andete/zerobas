- [ ] **SDFSCR IS A STUB IN C-BIOS'S SUB ROM: MSX-DOS ON MSX2 / MSX2+ STARTS IN SCREEN 1, NOT FROM THE RTC (D-SDFSCR,
      from the C-BIOS session 2026-11-27).**
      🎚️ TIER 6 — MSX2 is on HOLD (Joost: "not the focus of this release"); for zerobas's MSX2 sub-ROM patch set.
      🤖 **AUTONOMOUS** when MSX2 comes off hold — black box against the Philips NMS 8250.
      WHAT: main ROM $7D2F (MSX2 builds) -> call_sdfscr -> sub-ROM $0185 SDFSCR, which in C-BIOS only prints a debug
      line, so MSX-DOS keeps the SCREEN 1 C-BIOS's boot left. The reference's SDFSCR restores screen mode, width and
      colours from RTC block 2 (SETSCR at $0189 likely shares it).
      MEASURED by C-BIOS (openMSX, MSX-DOS 1.03 without AUTOEXEC, at A>): NMS 8250 with a never-written RTC: SCRMOD 0,
      LINLEN 37, colours 15/4/4, VDP R1 $70; after BASIC `SCREEN 1:WIDTH 20:COLOR 1,15,8:SET SCREEN`: SCRMOD 1, LINLEN
      20, colours 1/15/8. C-BIOS MSX2 EU _DISK, fresh RTC: SCRMOD 1, LINLEN 29, colours 15/4/4, VDP R1 $60 -- on all 8
      MSX2 / MSX2+ _DISK configs (MSX1 fine: $7D2F names INITXT / INIT32). zerobas's own MSX2 measurement saw the same
      SCREEN 1 (scratchpad/AE_msx2host_boottrace.out: SCRMOD 1 from H.RUNC to A>); dossession passes because it types
      MODE 40 first.
      ACCEPTANCE: an SDFSCR (+ SETSCR) for C-BIOS's sub ROM restoring mode / width / colours from RTC block 2, measured
      against the NMS 8250 incl. the never-written-RTC case; sent to C-BIOS as a patch item.
