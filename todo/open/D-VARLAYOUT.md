- [ ] 🐛 **A VARIABLE'S ENTRY IS [name0][name1][type][value] ON ZEROBAS, [type][name0][name1][value] ON THE VG-8020
      (D-VARLAYOUT, found 2026-11-25 by D-KWSPEC's errors region, the DEF-type unit).**
      🎚️ TIER 6 — every edge: VARPTR(v) and the value's own bytes agree on both machines; only a program that PEEKs
      BEFORE the value -- `PEEK(VARPTR(v)-3)` for the type, the published MSX entry layout -- reads a different byte
      (the name's first letter here, the type code there).
      🤖 **AUTONOMOUS** — [`kdeftype.py`](../../probes/basic/spec/kdeftype.py) ->
      [`KDT_run1.out`](../../scratchpad/KDT_run1.out): R-INT-ENTRY / R-SNG-ENTRY / R-DBL-ENTRY / R-STR-ENTRY fail on
      zerobas on every case that reads a type (the reference: 2 / 3 / 4 / 8; zerobas: 65 `A`, 66 `B`, ...). The
      order is zerobas's own throughout (basic/varfind.asm, basic/program.asm's `[name0][name1][type]` key, the FOR
      frame's 3-byte compare, sub/arrays.asm's walk), so a fix is every variable walk at once -- price it before
      starting. Not measured: the ARRAY entry's header (the reference's: type, two name bytes, then the size).
