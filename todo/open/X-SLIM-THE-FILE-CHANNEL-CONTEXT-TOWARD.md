- [ ] **SLIM THE FILE-CHANNEL CONTEXT toward the reference** — ✅ **MEASURED
      2026-07-29; awaiting spec sign-off.**
      [`docs/chancost-cf3300-characterization.md`](../../docs/chancost-cf3300-characterization.md),
      probe [`probes/disk/diskbasic_probe_chancost.py`](../../probes/disk/diskbasic_probe_chancost.py)
      (boot-per-case, both machines, reference answers self-checked for drift).
      🔴 **THE ITEM'S OWN CAVEAT IS REFUTED.** It said 267 "cannot be the goal
      for a channel doing FAT12 I/O" because it came from a diskless VG-8020.
      The disk-capable **CF-3300 charges exactly the same 267 B** — linear with
      no intercept across `MAXFILES` 0/1/2/3/4/8/15, non-adjacent points on the
      same slope. **267 IS a valid target.**
      Also measured: the ceiling is **exactly 15** (not "at least"), `16`/`255`
      raise **`Illegal function call`**; the buffers are charged at **`MAXFILES`
      time, not `OPEN` time**; the **string pool is untouched** (`FRE("")`=200
      either side); and `TXTTAB`/`HIMEM` are **constant**, so the carve is
      downward from the top — `FRE(0)` counts to **SP**, which is what moves.
      **267 < 512, so the sector buffer is NOT in it** — the reference shape is
      one *shared* sector buffer plus a small per-channel block, exactly as
      hypothesized.
      **zerobas, measured the same way:** `FRE(0)` = 13875 at `MAXFILES` 0, 1
      AND 2 — **it does not move at all**, because `FCH_CTX $EA00..$EE63` is
      reserved statically whether or not a channel is open. Its 512 B per
      channel is **purely a save copy** of the single global `FSECTOR_BUF`
      (`fch_save_active`/`fch_load_ctx`, [`basic/files.asm:914`](../../basic/files.asm:914));
      the reference gets the same effect by treating the shared buffer as a
      **cache** — flush on switch away, re-read on switch back.
      **Sizing:** drop the save copy → at `FCH_CEIL=2` the table falls 1124 B →
      100 B (**frees 1024 B**); at `FCH_CEIL=15` (full reference parity) it is
      750 B, still **374 B less than today**.
      ⚠️ **THE ROM COST IS NOT MEASURED** — flush-and-re-read instead of memcpy
      is an unknown-size change to `files.asm` against the **9 B** free low /
      **6 B** free page 1 of 2026-07-29. Estimating it from reading code would be a hypothesis, not a
      measurement (D-ARR-C §7a).
      ⚠️ **THOSE TWO FIGURES ARE STALE — 5 B low / 64 B page 1 at `b51bbbb`
      (2026-08-19)**; they stand as taken for their date. 🎯 **The caveat itself
      is UNCHANGED and is the live blocker:** the ROM cost is still not measured,
      so this is not a decline the wall can lift in either direction — and note
      the LOW region went the other way (9 B → **5 B**), which is where a
      `files.asm` change is most likely to land.
      [`docs/repricing-page1-2026-08-19.md`](../../docs/repricing-page1-2026-08-19.md)
      §4.
      ⚠️ **FREEING PAGE 3 DOES NOT BY ITSELF RETURN PROGRAM SPACE.** `TXTMAX`
      rises only if a page-2 buffer MOVES into the freed window: `TOKBUF`
      (576 B @ `$B700`) and the input line buffer are movable; `DETOKBUF`
      (1280 B @ `$BB00`) does not fit in 1024 B. So the D-LINEMAX refund is
      **partial at best**, not the full 1792 B.
      **FORK RESOLVED (user, 2026-07-29): the fully faithful DYNAMIC mechanism**
      — carve channel blocks out of the pool at `MAXFILES` time, ceiling 15,
      nothing charged for channels a program never asks for, `FRE(0)` moves.
      Spec written: [`docs/spec-basic-filechan-alloc.md`](../../docs/spec-basic-filechan-alloc.md)
      (**D-FCH**), ⚠️ **awaiting sign-off — no code written.**
      Semantics + error codes now MEASURED too (characterization §9/§10):
      `MAXFILES` **CLEARs variables UNCONDITIONALLY**, even when the value does
      not change (the `sem_same` row is what pins that — the natural reading
      "clears only when it reallocates" is wrong), **closes all channels**, and
      **keeps** the `CLEAR`-set string-pool size. Codes: `MAXFILES=16` → **ERR
      5**, bad channel number → **ERR 52 `Bad file number`**, touching a closed
      channel → **ERR 59 `File not OPEN`**; zerobas raises **ERR 2** for the
      first two and returns **−1** for the third. The whole disk error block
      50–65 is mapped black-box via `ERROR n`.
      ⚠️ **`Bad file number` is NOT trappable on the reference** — with a
      handler installed the other two trap cleanly but this one prints
      `Bad file number in 30` and never reaches it. Pin it, don't "fix" it.
      ⚠️ [`basic/files.asm:332`](../../basic/files.asm:332) **already comments
      `bad file number`** and jumps to `stmt_error`; six sites do the same.
      ⚠️ **`err_msgtab` stops at 25** — reaching 59 densely is ~100 B against
      9 B/6 B free. S-FCH-2 offers a sparse side-table instead.
      **S-FCH-1 ✅ BUILT + GATED 2026-07-29.** The shared-cache change costs
      **5 B of main page 1, 0 B of low region — NO CARVE** (fits the existing
      6 B with 1 B spare) and frees **1024 B** of page 3 (`FCH_CTX` 1124 → 100).
      The per-channel 512 B save copy is gone: `fat_detach_channel` flushes the
      dirty partial sector in place and `fat_restage_channel` reads it back
      (both sub-ROM, rows 19/20), so `FSECTOR_BUF` is a real write-back cache.
      🔴 **THE COST WAS SITING, NOT SUBSTANCE, AND ONLY BUILDING IT SHOWED
      THAT: 43 B → 9 B → 5 B.** Resident, the detach half cost 43 B (37 over) —
      a carve scouted from that number would have been scouted for a
      requirement **8× too big**. It calls `fat_flush_data_sector`, which was
      ALREADY a sub-ROM primitive, so keeping its caller resident bought
      nothing. The last 4 B came from hoisting ONE IX guard into `fch_select`
      instead of two inside save/load.
      ⚠️ **The IX contract was a live hazard**: those routines had no CALSLT
      before and promise IX/IY survive because `EOF`/`LOF`/`INPUT$` hold their
      token cursor there.
      ⚠️ **The gate was FALSIFIED**: stubbing `fat_restage_channel` to `ret`
      makes `disk_probe_maxfiles`'s interleaved two-channel write return **B's
      bytes in A.TXT** and fail both functionally and vs the CF-3300.
      ⚠️ **Repack-only** — ungated it overran the byte-full lean cart's `$8000`
      ceiling outright; the cart keeps the memcpy path, byte-identical.
      ⚠️ **Left open:** `fch_save_active` ignores the detach's `Cy`. A channel
      switch could never fail before and now can (disk full mid-flush);
      propagating it needs a disposition at every `fch_select` caller.
      **§3.3 ✅ BUILT 2026-07-29 — THE 1024 B IS NOW SPENT, AND IT IS PROGRAM
      SPACE: `FRE(0)` 13875 → 14899** (measured). `LINEBUF` `$BA00`→`$EB00`
      (page-aligned, cursor idiom untouched), `TOKBUF` `$B700`→`$EC00`,
      `TXTMAX` `$B700`→`$BB00`. **Zero ROM cost** — address constants only, so
      page 1 stayed at the 1 B free it had on 2026-07-29 and the lean cart
      stayed byte-identical.
      Usability CHECKED, not assumed: `CLEAR 200 : DIM A%(7000)` (14002 B, over
      the old 13875) now succeeds with **both ends written and read back**
      (11/22), 889 B still free. A `DIM` that merely succeeds witnesses nothing.
