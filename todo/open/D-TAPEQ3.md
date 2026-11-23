- [ ] 🔴 **THREE TAPE CASES NOBODY COMPARED (D-TAPEQ3, found 2026-10-09 by the cassette
      concept page).**
      🎚️ TIER 6 (latent) — cassette edge cases
      🤖 **AUTONOMOUS** — measure each on the VG-8020 first.
      - End of tape with no file found and no Ctrl-STOP: zerobas's `TAPION`
        gives up after a run of silence (`CAS_FLATMAX`); the reference may wait.
      - `SCREEN ,,,2` (cassette baud): the reference copies the 2400-baud table
        into the work area (tape/docs/spec-cassette.md); zerobas checks the
        argument and ignores it — compare a following `CSAVE`'s recording.
      - File names longer than six characters: zerobas truncates; the
        references are unmeasured.

      - [x] 🐌 **D-RECSLOW: extending a random file far is ~1000x slower than the CF-3300**
        (found 2026-11-04 by D-RECBIG). 🎚️ TIER 5 — on-par speed. 🤖 **AUTONOMOUS**:
        `PUT #1,32767` on a fresh LEN=1 file: zerobas 1763 frames, the CF-3300 2; `PUT
        #1,65535` ~3550 vs 3.
        ✅ **FIXED 2026-11-05 (to ~20x; the rest is W3b).** Measured first: the PUT issued 451
        FDC commands -- per new cluster a FAT read and both copies written for the mark, again
        for the link, plus a seek before nearly each -- and the CF-3300 NONE before CLOSE
        ([`recslow_fdc_probe.py`](../../scratchpad/recslow_fdc_probe.py) -> [`recslow_fdc.out`](../../scratchpad/recslow_fdc.out)).
        frnd_locate now extends the chain with the FAT sector HELD (frl_ext, disk/kernel.asm):
        FAT_DEFER became two bits (bit 0 "this write may wait", bit 1 "FAT_MBUF dirty"),
        fat_alloc_cluster scans a dirty buffer as cached and writes it out before replacing it
        (fac_cacheinit / fac_flushdirty, disk/fat.asm), and the sector goes to both copies once
        at the end, or on failure. No state outlives the call. 16 commands
        ([`recslow_fdc_after.out`](../../scratchpad/recslow_fdc_after.out), 🔮 "~10" close); frames
        ([`recslow_time_probe.py`](../../scratchpad/recslow_time_probe.py) -> [`recslow_time.out`](../../scratchpad/recslow_time.out))
        32767: 54 vs the CF-3300's 2, 65535: 57 vs 3, LOF and the record read back identical
        (🔮 "30-60" HIT). 🔴 MY FIRST BUILD CORRUPTED THE DISK: frl_defer loaded HL with the
        flag's address between the link's `ex de,hl` and its call, so the link went to a
        garbage cluster and the "FAT sector" was written over data sectors 51 / 54. The
        emulator count only looked odd (data R/W per cluster); the HOST rig
        ([`recslow_host.py`](../../scratchpad/recslow_host.py), nothing trapped but sector I/O, its
        own FAT decode) showed the 1-cluster chain at once, and then proved the fix on a
        32-cluster chain, a chain across the FAT sector straddle at 341 (PREUSED=334) and a
        disk filling mid-extension (TOT=14: 12 clusters, 66, both copies equal). frl_alloc /
        frnd_next moved to disk/fat.asm's $46CB fill for room. ➡️ The rest: the CF-3300
        writes nothing before CLOSE (spec-diskwcache.md W3b, parked).
