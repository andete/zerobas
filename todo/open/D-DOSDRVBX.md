- [ ] **UNDER MSX-DOS, `DIR B:` AT A> LISTS DRIVE A WITH NO SWAP PROMPT; THE CF-3300 PROMPTS "Insert diskette for drive B:" (D-DOSDRVBX
      -- D-DOSDRVB's first residual, now shown).**
      🎚️ TIER 3 — common errors (a one-drive user typing a B: name at A>: DIR B:, COPY X B:, the same class as D-DOSDRVB).
      🤖 **AUTONOMOUS** — black box, the CF-3300 the reference; screen and FDC registers only.
      MEASURED 2026-11-28 (D-COPYSLOW Q6, [sessops_probe.py](../../scratchpad/sessops_probe.py) SESS=driveb, [AE_sessops.out](../../scratchpad/AE_sessops.out)): at A>, `DIR MSX*.*` then
      `DIR B:MSX*.*` then `DIR A:MSX*.*`. CF-3300: "Insert diskette for drive B: / and strike a key when ready", the key,
      the listing; then "Insert diskette for drive A:" the same way. zerobas: both listings at once, NO prompt either
      time. D-DOSDRVB (closed 2026-11-17) made SELDSK 1 and the DEFAULT drive prompt; its close note named this residual
      ("an FCB naming its drive EXPLICITLY under MSX-DOS -- DK_FCB_DRV stays 0 there") to be filed when something showed
      it. Likely fix site: dsel_bdos (disk/kernel.asm) taking the FCB's own drive byte when it is non-zero -- READ IT
      FIRST; bytes from the disk ROM's holes. Gate: a bdos-acceptance row (BDOSXB-style, an explicit-drive FCB).
      ALSO SEEN (same run): the CF-3300 keeps a SEPARATE FAT image per drive (B's at $DF94, A's at $E595), recorded in
      D-COPYSLOW.
