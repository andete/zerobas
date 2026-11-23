- [ ] 💽 **D-RECHOLE -- A RANDOM RECORD NEVER WRITTEN READS THE CF-3300'S STALE SECTOR BUFFER, AND
      BLANKS HERE (found 2026-11-07 by typed session S14_diskbin)**
      🎚️ TIER 6 — what an undefined read returns.
      🤖 **AUTONOMOUS** — measured; read the buffer's provenance before deciding.
      📏 [`sessions_S14_diskbin_hole.out`](scratchpad/sessions_S14_diskbin_hole.out): records 1 and 3 of a 20-byte file PUT,
      record 2 never; `GET #1,2` gives `'*-` + 5 blanks in the 8-byte field on the CF-3300
      -- 39 42 45, the LAST three bytes of BLOCK.BIN, BSAVEd just before -- and 8 blanks
      here. LEN is 8 on both (the session now reads only that). Whether to copy a stale
      buffer is a question in itself: first measure what fills the hole when nothing was
      written before (a fresh disk), and whether the sector on disk or the buffer is read.
      📏 **MEASURED 2026-11-08 on a FRESH disk** ([`rechole_fresh.ses`](scratchpad/rechole_fresh.ses), [`rechole_fresh_cf.out`](scratchpad/rechole_fresh_cf.out) /
      [`rechole_fresh_zb.out`](scratchpad/rechole_fresh_zb.out)): records 1 and 3 of an 8-byte file PUT, record 2 never; GET #1,2
      reads **255 x 8 on the CF-3300** -- live AND after CLOSE + re-open (it is on the disk)
      -- and 32 x 8 here. The fresh image's data area is $00 (tools/make_test_dsk.py), so it
      is NOT the disk sector: a record sector created past the end of the file keeps WHATEVER
      THE CF-3300's DATA BUFFER LAST HELD -- $FF since power-on here, BLOCK.BIN's last bytes
      in S14 (BSAVEd / BLOADed through the same buffer just before) -- and writes it out. That
      is the reference's buffer HISTORY, undefined from BASIC's side: reproducing it means
      mirroring every use the CF-3300 makes of that buffer, which no black-box row can pin.
      🙋 **FOR JOOST (not blocking anything):** accept this as a documented divergence --
      zerobas fills a new record sector with spaces, a defined answer where the reference
      leaves stale bytes -- or chase the reference's buffer history? Recommendation: accept.
