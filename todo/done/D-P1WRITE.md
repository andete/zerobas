- [x] 🔴 **AN MSX-DOS PROGRAM'S WRITE FROM A BUFFER IN PAGE 1 ($4000-$7FFF) WRITES THE DISK ROM'S BYTES: COPY OF A 32 KB
      FILE "SUCCEEDS" WITH 16 KB OF IT REPLACED BY OUR ROM IMAGE (D-P1WRITE, found 2026-11-27).**
      🎚️ TIER 1 — silent data loss under MSX-DOS, every host (MSX1 too), and the C-BIOS port's first user is MSX-DOS.
      🤖 **AUTONOMOUS** — black box: the disk image after a typed COPY, the CF-3300 the reference.
      FOUND by the large-COPY row asked for under D-DISKMSX2HOST (Joost: "yes, add that row"): `COPY MSXBUNSE.ROM
      BIG.ROM` (32768 B) at A>. The CF-3300's copy is byte-identical; zerobas's prints "1 file copied" and DIR agrees,
      but 16158-16164 bytes differ, file offsets $3ED3-$7ED2 -- COMMAND.COM's buffer at RAM $4000-$7FFF, i.e. page 1
      ([AE_bigcopy32_new.out](../../scratchpad/AE_bigcopy32_new.out); the ROM BEFORE 742324436 the same, [AE_bigcopy32_old.out](../../scratchpad/AE_bigcopy32_old.out)).
      That band IS our disk ROM: 16320 of its 16384 bytes equal build/disk.rom from $4000 ("AB" header first). So the
      write path reads the caller's buffer with the disk ROM mapped in page 1; the READ path has a page-1 bounce
      (P1_BLIT, D-P1RDBLK / D-P1DOS), the write path not. A 131072 B COPY also runs > 400 s here against < 60 s on the
      CF-3300 ([AE_bigcopy_old.out](../../scratchpad/AE_bigcopy_old.out), [AE_bigcopy_new2.out](../../scratchpad/AE_bigcopy_new2.out)) -- a speed item of its own once the bytes are right.
      ACCEPTANCE: the parked row (scratchpad/bigcopy_row.patch: COPY MSXBUNSE.ROM BIG.ROM + BIG.ROM's bytes = the
      source's, on each machine) SAME on the MSX1 / MSX2 / MSX2+ hosts and the zerobas DISK machine; the old ROM on
      MSX2 must fail it (the page-1 restore of D-DISKMSX2HOST).
      ✅ **FIXED 2026-11-27:** dta_chunk (disk/kernel.asm, the one copy from the DTA that WRSEQ / WRRND / WRBLK share)
      ends in `jp P1_BLIT` instead of `ldir` + `ret` -- the same 3 bytes; the copy runs with page 1 = RAM, as the read
      side's always did. The session rows `bigcopy` / `bigdir` + the byte check (`bigbytes`: BIG.ROM = MSXBUNSE.ROM on
      each machine) 24/24 on the MSX1 C-BIOS host, the zerobas DISK machine, MSX2 EU and MSX2+ EU
      ([AE_p1w_CBIOS2_CUR_MSX1_EU_NOBASIC_DISK.out](../../scratchpad/AE_p1w_CBIOS2_CUR_MSX1_EU_NOBASIC_DISK.out), [AE_p1w_REPACK.out](../../scratchpad/AE_p1w_REPACK.out), [AE_p1w_CBIOS2_CUR_MSX2_EU_NOBASIC_DISK.out](../../scratchpad/AE_p1w_CBIOS2_CUR_MSX2_EU_NOBASIC_DISK.out), [AE_p1w_CBIOS2_CUR_MSX2P_EU_NOBASIC_DISK.out](../../scratchpad/AE_p1w_CBIOS2_CUR_MSX2P_EU_NOBASIC_DISK.out);
      🔮 24/24: HIT). Before the fix: 16 KB of the copy = our ROM image on every host ([AE_bigcopy32_old.out](../../scratchpad/AE_bigcopy32_old.out)).
      ✅ CLOSED 2026-11-27 (bf18cc51f; C-BIOS re-pinned in a1be29b -- Joost: "the ram issue is exactly what got
      fixed"). The speed, measured with the bytes right, is its own item: D-COPYSLOW (TIER 2).
