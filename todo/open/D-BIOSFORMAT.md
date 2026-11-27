- [ ] **BIOS FORMAT ($0147) ON A BASIC-LESS HOST IS REFUSED, NOT PERFORMED (D-BIOSFORMAT, filed 2026-11-27 by C-BIOS
      integration step 1).**
      🎚️ TIER 6 — every edge: a program that formats through the BIOS entry on a C-BIOS with no BASIC (MSX-DOS 1's
      own FORMAT goes through the disk ROM's $4025 and works).
      🤖 **AUTONOMOUS** — measure first.
      C-BIOS's $0147 is `call H_FORM`; zerobas's H_FORM handler needed zerobas BASIC (main's key source through
      calbak, BASIC's STREND) and CRASHED there ([AE_biosformat_knife.out](../../scratchpad/AE_biosformat_knife.out)). Since 2026-11-27 hk_format_gate refuses
      (Cy = 1) unless zerobas BASIC's marker ZB_HOST is set ([AE_biosformat1.out](../../scratchpad/AE_biosformat1.out)). fmt_dos is no target: its work area is
      the TPA from $0100, which is the CALLER when a program calls $0147.
      NEXT: on the CF-3300, call $0147 from an MSX-DOS program and from a ROM / boot program (RAM reads only): which
      dialogue, which keys, and which RAM it uses as the track buffer; then give the BASIC-less path that.
