#!/usr/bin/env python3
"""D-CASPRIME: close D-LOADERRRET (its last live tape arms), file D-BLDS.
Docs: OPEN, MERGE. Anchored on text; refuses otherwise."""
import re, sys

def sub(path, old, new):
    s = open(path).read()
    n = s.count(old)
    if n != 1:
        sys.exit(f"REFUSE {path}: anchor found {n}x: {old[:70]!r}")
    open(path, "w").write(s.replace(old, new))
    print(f"ok {path}")

T = "TODO.md"
sub(T, """- [ ] 🔴 **D-LOADERRRET — `load_error` PRINTS AND RETURNS; ~15 SITES STILL `jp` TO IT WHERE THE
      REFERENCE RAISES A TRAPPABLE CODE (filed 2026-10-07 from D-CHDIR / D-SAVETAIL)**""",
    """- [x] ✅ **D-LOADERRRET — `load_error` PRINTS AND RETURNS; ~15 SITES STILL `jp` TO IT WHERE THE
      REFERENCE RAISES A TRAPPABLE CODE (filed 2026-10-07 from D-CHDIR / D-SAVETAIL;
      CLOSED 2026-10-11 -- the last live arms are D-CASPRIME at the end of this block,
      the one measured residual is its own item, D-BLDS)**""")
s = open(T).read()
anchor = "\n- [x] ✅ **D-CASRBRK"
if s.count(anchor) != 1:
    sys.exit("REFUSE casrbrk anchor")
block = """      ✅ **D-CASPRIME (2026-10-11): THE LAST LIVE TAPE ARMS -- A READ THAT FAILS WHILE
      OPEN / MERGE PRIME THE FIRST DATA BLOCK IS 19.** Two `cas_ascii_setup` CF
      arms were left: OPEN "CAS:" FOR INPUT's went to `oocas_ioerr` (`load error`,
      and the run went ON) and MERGE's to `mc_ioerr` -> `disk_error`, which
      raised the STALE disk code -- **255 on the diskless machine**, in the line.
      📏 basic_probe_casrbrk's new rows (Ctrl-STOP 2 s in,
      [`casprime_before.out`](scratchpad/casprime_before.out)): `ob2` VG-8020
      `19 in 15`, ours `load error` + ran on; `mb2` VG-8020 **`19 in 65535`,
      TRAPPED** (the MERGE has left the run at `Found:`, as the tape SAVE does --
      D-CASWBRK; its search failing earlier is `19 in 20`, D-CASBRK, and a later
      block untrapped, mb8), ours `255 in 15`. 🔧 OPEN's arm -> `dpl_dio`;
      MERGE's -> `mc_found_dio` (DIRECTF 0 -> 1, then `dpl_dio`). Main page 1
      18 -> 10 B (clean build, 2026-10-11). After: 4/4 with mb8 / ib8 unchanged
      ([`casprime_after.out`](scratchpad/casprime_after.out)). 🔪
      [`casprime_knives.out`](scratchpad/casprime_knives.out): K-CP1 -> ob2,
      K-CP2 -> mb2 (255 again), K-CP3 (no DIRECTF bump) -> mb2 (`19 in 15`) --
      each exactly, predicted.
      📋 **CLOSING INVENTORY** (`grep` of every jump to the load_error family,
      2026-10-11): the disk arms (bload-body, sv-diskwr, sv-bsvdisk) reach
      `disk_error` through the tenants' status and RAISE the pending DSKIO code
      (D-DISKERR) -- `load error` only with no code pending, by design;
      `str-engine`'s sub-ROM-absent arm, by design; cload.asm 451 / 455 and
      files.asm's two `cp ASCII_ID` tests, UNREACHABLE since D-CASTYPE filters the
      search by type; cload.asm's disk "file vanished between opens" race, not
      reproducible. One arm was measured and is NOT fixed: `BLOAD"CAS:X",S` --
      D-BLDS, below.
"""
i = s.index(anchor)
s = s[:i].rstrip("\n") + "\n" + block.rstrip("\n") + "\n" + s[i:]
anchor2 = "\n- [ ] 🏗️ **D-SUB2"
if s.count(anchor2) != 1:
    sys.exit("REFUSE sub2 anchor")
item = """
- [ ] 🔍 **D-BLDS — ON TAPE, `BLOAD "CAS:X",S` TAKES `S` AS THE OFFSET EXPRESSION; OURS
      REFUSES IT WITH `load error` (measured 2026-10-11, from D-LOADERRRET's close)**
      🎚️ TIER 6 — a documented form (BLOAD's `,offset`) colliding with the
      disk-only `,S` flag: only a variable literally named S hits it.
      🤖 **AUTONOMOUS** — but priced against the binding wall: do not spend main's
      last bytes on it ahead of the tiers above.
      📏 [`blds_diag.py`](scratchpad/blds_diag.py) →
      [`blds_diag.out`](scratchpad/blds_diag.out), a 4 KB binary at &HC000: the
      VG-8020 loads `BLOAD"CAS:X",S` with S=0 at its own address and with S=16
      sixteen bytes higher -- `,S` is the offset VARIABLE there, as BSAVE's is on
      tape (D-TAPETAIL). Ours: `load error`, nothing loaded. 🔮 Predicted: HIT.
      🔧 Why it is not a two-line fix: main's `pcr_bload` (basic/bload.asm, page
      1) parses the tail BEFORE the tenant knows the device and sets VRAM_FLAG
      for `S`; the tape arm (bload-body.inc) then refuses. A device test there --
      `CAS:` on the staged name, plus the diskless bare name, which is tape too --
      is ~16-20 B of main (page 1 10 B, low 19 B on 2026-10-11).
"""
i2 = s.index(anchor2)
s = s[:i2].rstrip("\n") + "\n" + item.rstrip("\n") + "\n" + s[i2:]
open(T, "w").write(s)
print("ok TODO")

O = "docs/keywords/OPEN.md"
sub(O, "## What we found, and how\n\n", "## What we found, and how\n\n"
    "- **A tape `OPEN` broken while it read the file's first block said `load error`**\n"
    "  (fixed 2026-10-11, D-CASPRIME) and the program ran on; the VG-8020 raises\n"
    "  `Device I/O error` (19) in the line\n"
    "  ([`casprime_after.out`](../../scratchpad/casprime_after.out)).\n")
M = "docs/keywords/MERGE.md"
sub(M, "## What we found, and how\n\n", "## What we found, and how\n\n"
    "- **A tape `MERGE` broken while it read the file's first block raised error 255**\n"
    "  (fixed 2026-10-11, D-CASPRIME) -- a stale disk code, on a machine with no\n"
    "  disk. The VG-8020 raises `Device I/O error` (19) with no line number, and an\n"
    "  `ON ERROR` handler still sees it\n"
    "  ([`casprime_after.out`](../../scratchpad/casprime_after.out)).\n")
