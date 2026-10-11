#!/usr/bin/env python3
"""D-CASDIRECT docs + TODO, anchored on text; refuses otherwise."""
import re, sys

def sub(path, old, new):
    s = open(path).read()
    n = s.count(old)
    if n != 1:
        sys.exit(f"REFUSE {path}: anchor found {n}x: {old[:70]!r}")
    open(path, "w").write(s.replace(old, new))
    print(f"ok {path}")

FOUND = {
    "LOAD": ("- **A line with no line number in an ASCII program printed `load error`, and a\n"
             "  program went on running** (fixed 2026-10-11, D-CASDIRECT). Both references\n"
             "  print `Direct statement in file` (57) with no line number, from tape and\n"
             "  from disk, and no `ON ERROR` handler sees it: the program is already gone.\n"
             "  A BSAVE binary loaded as a program gets the same message on the CF-3300\n"
             "  ([`casdirect_after.out`](../../scratchpad/casdirect_after.out)).\n"),
    "MERGE": ("- **A line with no line number in the merged file raised `Syntax error`**\n"
              "  (fixed 2026-10-11, D-CASDIRECT), inside a program with a garbage line\n"
              "  number. Both references print `Direct statement in file` (57) with no line\n"
              "  number, from tape and from disk, and no handler sees it; the lines before\n"
              "  it stay merged ([`casdirect_after.out`](../../scratchpad/casdirect_after.out)).\n"),
}
for kw, text in FOUND.items():
    p = f"docs/keywords/{kw}.md"
    s = open(p).read()
    s2, n = re.subn(r"> \*\*Status \(2026-10-\d\d\):\*\*", "> **Status (2026-10-11):**", s, count=1)
    if n != 1:
        sys.exit(f"REFUSE {p}: status")
    open(p, "w").write(s2)
    sub(p, "## What we found, and how\n\n", "## What we found, and how\n\n" + text)
    sub(p, "- `make kwram` — the RAM-usage comparison.\n",
        "- `make casdirect-acceptance` — a line with no number in the program file,\n"
        "  tape and disk, typed and under `ON ERROR`.\n"
        "- `make kwram` — the RAM-usage comparison.\n")

T = "TODO.md"
sub(T, """      str-engine.asm's sub-ROM-absent arm, the content-fault arms above -- and""",
    """      str-engine.asm's sub-ROM-absent arm, the content-fault arms above (✅ the
      non-numbered line: D-CASDIRECT, 2026-10-11 -- at the end of this block) -- and""")
sub(T, """      K-CR3..6 (HIT). Main page 1 −21 B (41 → 20), sub page 1 +18 B (clean build, 2026-10-11).
""", """      K-CR3..6 (HIT). Main page 1 −21 B (41 → 20), sub page 1 +18 B (clean build, 2026-10-11).
""")
s = open(T).read()
anchor = """
- [x] ✅ **D-SAVETAIL"""
if s.count(anchor) != 1:
    sys.exit("REFUSE savetail anchor")
block = """      ✅ **D-CASDIRECT (2026-10-11): A LINE WITH NO LINE NUMBER IN AN ASCII PROGRAM IS
      57 `Direct statement in file`, UNTRAPPED, NO LINE -- LOAD AND MERGE, TAPE AND
      DISK, ON BOTH REFERENCES.** The content arm named above: cas_ascii_load sent
      it to `dpl_err` (`load error`, returned -- inside a program the run went ON,
      `[N 1]`), the disk `ascii_load` the same, and MERGE's shared tail `mrg_fin`
      to `stmt_error` -- 2 `Syntax error`, `in 21313` inside a program -- under a
      comment saying it gave "Direct statement in file".
      📏 [`casdirect_diag.py`](scratchpad/casdirect_diag.py): the VG-8020 (tape,
      [`casdirect_diag.out`](scratchpad/casdirect_diag.out)) and the CF-3300 (disk,
      [`casdirect_disk.out`](scratchpad/casdirect_disk.out)) both print it with no
      line and run no handler, keeping the lines before it; a BSAVE binary LOADed
      as a program says the same on the CF-3300
      ([`casdirect_bin.out`](scratchpad/casdirect_bin.out)) -- it trips the same
      reader guard. 🔮 Predicted 57 (recalled, not looked up): HIT; the disk
      faces: HIT.
      🔧 `dpl_direct` (`ld a,57` / `jp raise_error`) at all three sites; main
      page 1 23 → 18 B (clean build, 2026-10-11). A first cut also set DIRECTF
      and took `raise_error_forced`; their knives moved NOTHING (the verb has
      already left the run) and both went
      ([`casdirect_knives_run1.out`](scratchpad/casdirect_knives_run1.out)).
      Gate **`casdirect-acceptance`** ([`basic_probe_casdirect.py`](probes/basic/basic_probe_casdirect.py),
      [`casdirect_gate.out`](scratchpad/casdirect_gate.out)): dload dmerge pload
      pmerge kload kmerge kpload kpmerge kbinload, 9/9. 🔪 K-DS1 (tape LOAD arm)
      → dload pload, K-DS2 (disk LOAD arm) → kload kpload kbinload, K-DS3
      (MERGE's tail) → all four MERGE rows, tape AND disk -- each exactly.
"""
i = s.index(anchor)
s = s[:i] + "\n" + block.rstrip("\n") + s[i:]
open(T, "w").write(s)
print("ok TODO")
