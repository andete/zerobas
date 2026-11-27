- [ ] **THE DISK ROM ON C-BIOS'S OTHER HOSTS: MSX1 JP / BR / INTERNATIONAL, MSX2 AND MSX2+ -- UNMEASURED (D-DISKMSX2HOST,
      queued 2026-11-27).**
      🎚️ TIER 1 — the disk ROM for C-BIOS: Joost (2026-11-27) wants "a with and without variant of each existing
      cbios"; only C-BIOS MSX1 EU is gated (`make nobasic-acceptance`). Asked whether to measure the rest: "yes".
      🤖 **AUTONOMOUS** — zerobas-side only: machines built from the pinned C-BIOS ROM copies in the openMSX share
      (`tools/install_cbios_msx2.py`), never a C-BIOS build or change (memory no-cbios-work-only-the-inbox).
      WHAT: for each C-BIOS config family, a NOBASIC_DISK machine with build/disk.rom in its free subslot, then the
      no-BASIC MSX-DOS session (disk_probe_dossession) and the reach proof (disk_probe_nobasicreach) on it:
        - MSX1 JP / BR / international: slot 3 plain RAM -> expanded, disk in 3-1 (as EU). Locale differs (JP: INIT32
          at $7D2F, keyboard, date order).
        - MSX2 (x4): 3-0 sub ROM, 3-2 mapper -> disk in 3-1.
        - MSX2+ (x4): 3-0 sub, 3-1 music, 3-2 mapper -> disk in 3-3 (never gated).
      The pin (tools/cbios-nobasic.pin) then covers every ROM those machines use. Findings go to the C-BIOS inbox
      (diskport-02 lists the variants) and, when zerobas's, to items here.
      ACCEPTANCE: each variant boots MSX-DOS 1 to A> and the session reads as on the CF-3300 (or the difference is
      filed and pinned); the reach proof GREEN; the measured variants gated (battery, or daily sweeps if slow).
