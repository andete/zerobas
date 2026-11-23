- [ ] **D-DSKFMTREGS — DSKFMT RETURNS OTHER WORKING REGISTERS THAN THE CF-3300'S (THE DISKS ARE THE SAME)**
      🎚️ TIER 6 — every edge (filed 2026-11-22).
      🤖 **AUTONOMOUS** — docs/disk/DSKFMT.md R-DF-OKREGS / R-DF-BADF (scratchpad/XDFMT1_run2.out, the CF-3300 row):
      both format the same four disks (choices 1-4: $FC $FD $F8 $F9) and refuse 0 / 5 the same way (A 12, carry, B
      $20, E = choice - 1, HL kept, nothing written). The CF-3300 returns F $42, C $3C, DE $0049, HL $9020 after a
      format and F $3B / $93 on a refusal; zerobas F $44, C $05, DE $0000 / $0100, HL $000E, and F $89 / $49. Working
      values; fix only if a program is found reading them.
