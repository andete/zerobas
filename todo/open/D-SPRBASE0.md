- [ ] 🧩 **D-SPRBASE0 — IN SCREEN 0, ATRBAS / PATBAS READ 0 (2026-10-16)**
      🎚️ TIER 6 — CALATR / CALPAT in text mode; no title known.
      🤖 **AUTONOMOUS** — measure first.
      📏 scratchpad/calatr_probe.out rows atr / pat8 / calatr2: in SCREEN 0 (even
      after a SCREEN 2) zerobas's CALATR answers $0014 for sprite 5 where the
      VG-8020 answers $1B14 -- ATRBAS ($F928) and PATBAS ($F926) are 0 on zerobas
      and $1B00 / $3800 on the VG-8020. ➡️ Which writes them (C-BIOS's INITXT, or
      zerobas's SCREEN) -- read the cells around each SCREEN on both.
