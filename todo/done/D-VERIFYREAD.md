- [x] 🐛 **VERIFY ON DOES NOTHING ON ZEROBAS; THE CF-3300 READS BACK EVERY SECTOR IT WRITES (D-VERIFYREAD, found
      2026-11-26 by D-DISKCONTRACT gap 12).**
      🎚️ TIER 6 — every edge: VERIFY is off unless a program or the user turns it on, and a good disk reads back the same.
      🤖 **AUTONOMOUS** — the probe and its gate exist; the fix needs disk-ROM room first.
      MEASURED (`make verifyread-acceptance`, probes/disk/disk_probe_verify.py, scratchpad/AE_verify1.out /
      AE_verify2.out): at A>, `COPY HELLO.TXT V1.TXT` under VERIFY OFF and again under VERIFY ON, a write watchpoint on
      the WD2793 command register ($7FB8) logging every command. The CF-3300 adds 9 READs to its 9 WRITEs -- each
      written sector read back, a multi-sector write followed by a run of reads (`WWW` then `RRR`); zerobas's stream is
      identical with VERIFY off or on (+0). The gate pins both exact values (CF +9, ZB +0) and turns red if either moves.
      NOT MEASURED: what the CF-3300 does when the read-back FAILS or differs (an error code? which?) -- needs a disk
      that writes but reads back wrong, which openMSX cannot easily stage.
      FIX DIRECTION: in the disk ROM's DSKIO write path, when the BDOS VERIFY flag is set, re-read the sectors just
      written (to a scratch buffer, or with a read that only checks CRC) and turn a failed read into the write's error.
      The disk ROM has ~0 B usable (docs/disk/port-readiness.md row 5): carve first.
      ✅ **FIXED 2026-11-26.** No RAM cell holds the VERIFY state on either machine in $C000-$FFFF (scratchpad/
      verifyflag_find.py, [AE_verifyflag.out](../../scratchpad/AE_verifyflag.out): only the typed line's bytes move), so zerobas keeps its own: VERIFY_F ($F1C5,
      the INIT-private block; INIT clears it, verify_body -- moved in front of $75A5 -- stores E). disk/kernel.asm
      dskio_verify, called by DSKIO's write loop after each sector: VERIFY on -> the sector read back into $4000..,
      this ROM's own page during DSKIO (the stores are dropped; no buffer touched), its error the write's. +~40 B.
      The gate now scores the VERDICT -- "every written sector read back" -- not the raw count: zerobas's COPY writes 6
      sectors where the CF-3300's writes 9 (D-WCACHE), and both read back all of theirs ([AE_verify3.out](../../scratchpad/AE_verify3.out) ->
      [AE_verify4.out](../../scratchpad/AE_verify4.out); the old ZB +0 reads "none" and fails). Left: the order (CF WWW RRR per multi-sector write,
      zerobas W R per sector) and a FAILING read-back's code on the CF-3300 -- not measured.
