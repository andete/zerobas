- [ ] **D-WRBLKGAP — WRBLK PAST THE END: THE NEW-CLUSTER SECTOR IT WRITES INTO KEEPS THE DISK'S BYTES; BOTH REFERENCES BUILD IT FROM THE DOS'S SECTOR BUFFER**
      🎚️ TIER 6 — every edge (filed 2026-11-22).
      🤖 **AUTONOMOUS** — docs/bdos/BLOCKS.md R-BK-ROUND5 (scratchpad/XBBLK5_run1.out, run2.out XK5 10 / 15): WRBLK
      1 x 1 at RR 2000 on an 896-byte file through $F37D; read back, the VG-8020 + NMS 1200 and the CF-3300 both show
      bytes 1536 .. 2000 as the file's sector 0 (the last sector transferred, as case 9 left it) with byte 2000 in
      it; zerobas shows zeros. Round 6 (R-BK-ROUND6, scratchpad/XBBLK6_run1.out, run2.out XK6 11 / 15) names
      both sides: over a deleted file's cluster, zerobas shows that file's bytes (the DISK's -- the zeros above
      were the blank image), the references the LAST sector transferred (G's sector 1, not sector 0) with the
      new byte in it. The rest of the gap agrees on all three (older bytes in allocated sectors, the disk's in a
      skipped new one). A program that writes a sparse record and reads the gap sees different garbage.
      disk/ (the write path's partial sector in a new cluster: start from the buffer, do not read the disk).
