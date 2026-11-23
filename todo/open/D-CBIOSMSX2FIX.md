- [ ] **D-CBIOSMSX2FIX — FIX C-BIOS'S MSX2 / MSX2+ SUB-ROM WHERE D-MSX2SPEC MEASURED IT WRONG -- POSTPONED**
      🎚️ TIER 6 — POSTPONED (Joost 2026-11-23): "since we don't do MSX2 and MSX2+ and turbor yet, those should be
      postponed". Pick up when zerobas takes on MSX2 / MSX2+ (and turbo R for its own).
      ⛔ BLOCKED: postponed until zerobas takes on MSX2 / MSX2+ (Joost). Then, the way the MSX1 fixes went: patches against C-BIOS's MSX2 / MSX2+ sources built in a /tmp
      worktree, installed as their own openMSX machines (tools/install_cbios_msx2.py --tag FIX), each re-measured with
      the D-MSX2SPEC probes until it matches the HB-F900 / NMS 8250 / FS-A1WSX, then offered to C-BIOS. The C-BIOS
      session has the list with a HOLD on it (inbox 2026-11-23-zerobas-msx2-subrom-findings.md): do not let it start
      on them first. The wrong results, each on its docs/msx2 page's "Differences": REDCLK's block selection, TRIGHT /
      TLEFTC / DSPFNK / DOGRPH / SCANR / SCANL no-ops, NVBXLN's figure, BLTMV's last dot, GRPPRT's CR and wrap, CLS's
      fill bytes, CHGCLR's masks, WRTVDP's R#9 and R#25-27 copies, SETPAG's R#6, SCREEN 2 as multicolour (SETC /
      SCALXY / RIGHTC / LEFTC / TDOWNC), the sub-ROM NRDVRM / NWRVRM page rule in SCREEN 0-4, interrupts after CHGMOD
      / INIT* / CLS.
