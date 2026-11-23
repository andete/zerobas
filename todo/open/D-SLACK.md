- [ ] **D-SLACK — A NEW FILE'S NEVER-WRITTEN RECORDS HOLD DIFFERENT GARBAGE**
      🎚️ TIER 6 — every edge (records a program never wrote, inside or past the file's end; filed 2026-11-17).
      🤖 **AUTONOMOUS** — bdosf37d's image diff: after FDEL freed a cluster and FMAKE + WRRND rec 2 took it, the CF-3300
      leaves its stale sector BUFFER (the last sector it read, SECOND.DAT's) around the record; ours read-modify-writes
      the old sector (the deleted THIRD.DAT's text). The published content is undefined; matching it means copying
      the reference's buffer reuse. Excused by name in bdosf37d (sector 20's bytes 0..255, 384..511).
