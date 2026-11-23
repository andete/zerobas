- [ ] 🔧 **D-CHANFORREF — kwsweep's `chanfor` HAS READ THE CF-3300'S FUNCTION-KEY BAR, NOT ITS VALUE,
      ON EVERY BATCH RUN OF 2026-10-07 (filed 2026-10-07)**
      🎚️ APPARATUS — a row that silently stops measuring.
      📏 Three full kwsweep runs that day (the D-OPENWILD, D-LOADTAIL and
      D-INPUTDN gates-fast) all printed `DIVERGENT chanfor` with ref
      `'|||||||||||color   auto    goto    list    run'` and ours `[C 1 2 3 10 20
      30 ]`; D-KWDIVPIN's rule judges that side unreadable and does not fail,
      so the battery stays green and the row proves NOTHING. 10-06's note
      (D-KWDIVPIN, above) saw it blank once in batch and SUPPORTED alone.
      ➡️ First: is the reference reading LIVE each run or REPLAYED from the
      refcache (a bad capture stored once would explain three identical
      readings)? Then why the reference screen shows only the key bar --
      the row's `MAXFILES=2` (a CLEAR, which may CLS) before the capture window
      is the first suspect. Fix the row or the capture, not the rule.
      🤖 **AUTONOMOUS** — the CF-3300 and the refcache settle it.
      📏 **THE REPLAY HYPOTHESIS IS REFUTED (2026-10-28).** On the then-new openMSX
      build (22.0-12, after the refcache began keying on `openmsx -v`) the kwsweep
      run read every reference value fresh -- `refcache: 0 hit, 49 miss`, and
      `chanfor` is not in the rig-carry file -- and printed the same blank
      reference screen, `'|||||||||||color auto goto list run'`. So the blank is a
      LIVE batch capture miss, reproduced on two emulator builds; the second
      suspect (the row's `MAXFILES=2` clearing the screen before the capture
      window) is now the first.
