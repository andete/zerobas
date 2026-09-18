#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FATDEP: which MAIN-ROM code depends on the FAT layer, and how?

🔴 WHY THIS IS A TOOL AND NOT A GREP. The count has been wrong THREE TIMES, each
time in a different way, and each time it was quoted into a plan:

  * spec-diskcode-eviction.md §6.1 (2026-09-17) said **25 call sites in six
    files**. Three of those six -- bload-body.inc, fat-prim-body.inc,
    fat-delete-body.inc -- are `include`d ONLY from sub/*.asm, so their sites
    bind sub-locally and pin nothing in main.
  * the correction (2026-09-18) said **13 in five files**. It dropped
    basic/files.asm entirely (6 sites) and undercounted cload.asm. It was
    relayed from a review rather than re-derived.
  * this tool says **20 in five files**, and prints the list so the next reader
    checks the rows rather than trusting the total.

So the number gets DERIVED, never quoted. `--selftest` proves the include
closure actually walks (a planted nested include is found) and that a sub-only
file is excluded.

WHAT IT MEASURES. The transitive `include` closure of basic/main.asm -- what the
MAIN ROM actually assembles -- then every reference to a FAT-layer entry from
outside the layer itself. Two classes, and the distinction is the whole point:

  VECTOR   `ld hl,fat_io_getbyte` stored into the ARL_GETBYTE RAM vector
           (basic/sysvars.inc), which three device-agnostic loops jump through
           ONCE PER BYTE. A page-1 address in another slot cannot be reached
           this way, which is why the byte cursors are resident. THIS is the
           pin -- not the call count.
  CALL     an ordinary `call`/`jp`. Moves with its verb, or becomes a call-back.

⚠️ AND THE FRAMING §6.1 GOT WRONG: these are not TAPE code depending on FAT.
They are SHARED loaders that dispatch on DEVICE, whose disk arm calls FAT. The
dispatch is three instructions (`arl_set_src`, basic/input.asm) choosing between
`fat_io_getbyte` and `cas_in_getbyte`. Reading them as a tape/disk entanglement
is what made the layer look unmovable.
"""
import os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = "basic/main.asm"

# The FAT layer's own files -- a reference from INSIDE the layer is not a
# dependency ON it.
LAYER = ("basic/fat.asm", "basic/fatio-body.inc", "basic/fatiocreate-body.inc",
         "basic/fatiow-body.inc", "basic/fat-prim-body.inc",
         "basic/fat-delete-body.inc")

ENTRIES = ("fat_io_open", "fat_io_getbyte", "fat_io_putbyte", "fat_io_create",
           "fat_io_close", "fat_io_append", "fat_find", "fat_mount", "fat_open",
           "fat_read_file_sector", "fat_flush_data_sector", "fat_count_free",
           "fat_dir_create", "fat_dir_update")
ENTRY_RE = re.compile(r"\b(%s)\b" % "|".join(ENTRIES))
INC_RE = re.compile(r'^\s*include\s+"([^"]+)"', re.I)
VECTOR_RE = re.compile(r"\bld\s+hl\s*,\s*(%s)\b" % "|".join(ENTRIES), re.I)
CALL_RE = re.compile(r"\b(call|jp)\b[^;]*?\b(%s)\b" % "|".join(ENTRIES), re.I)


def closure(root, base=None):
    """Every file the ROM at `root` actually assembles, transitively."""
    base = base or REPO
    seen, stack = [], [root]
    while stack:
        f = stack.pop(0)
        if f in seen:
            continue
        p = os.path.join(base, f)
        if not os.path.exists(p):
            continue
        seen.append(f)
        for ln in open(p, errors="replace"):
            m = INC_RE.match(ln)
            if m and m.group(1) not in seen:
                stack.append(m.group(1))
    return seen


def census(files, base=None):
    base = base or REPO
    rows = []
    for f in files:
        if f in LAYER:
            continue
        p = os.path.join(base, f)
        if not os.path.exists(p):
            continue
        for i, ln in enumerate(open(p, errors="replace"), 1):
            code = ln.split(";")[0]
            if not ENTRY_RE.search(code):
                continue
            kind = "VECTOR" if VECTOR_RE.search(code) else (
                "CALL" if CALL_RE.search(code) else None)
            if kind:
                rows.append((f, i, kind, " ".join(code.split())))
    return rows


def selftest():
    import tempfile, shutil
    d = tempfile.mkdtemp(prefix="fatdep_")
    try:
        os.makedirs(os.path.join(d, "basic"))
        os.makedirs(os.path.join(d, "sub"))
        open(os.path.join(d, "basic/main.asm"), "w").write(
            '                include "basic/mid.inc"\n')
        open(os.path.join(d, "basic/mid.inc"), "w").write(
            '                include "basic/leaf.inc"\n')
        open(os.path.join(d, "basic/leaf.inc"), "w").write(
            "                call    fat_io_open\n"
            "                ld      hl, fat_io_getbyte\n")
        # a file only SUB assembles: it must not appear
        open(os.path.join(d, "sub/only.asm"), "w").write(
            "                call    fat_mount\n")
        files = closure("basic/main.asm", d)
        ok1 = "basic/leaf.inc" in files
        print("%s S1 the include closure walks NESTED includes (found leaf)"
              % ("PASS" if ok1 else "FAIL"))
        ok2 = "sub/only.asm" not in files
        print("%s S2 a file only sub/ assembles is NOT in main's closure"
              % ("PASS" if ok2 else "FAIL"))
        rows = census(files, d)
        kinds = sorted(r[2] for r in rows)
        ok3 = kinds == ["CALL", "VECTOR"]
        print("%s S3 both classes are distinguished (got %s)"
              % ("PASS" if ok3 else "FAIL", kinds))
        return 0 if (ok1 and ok2 and ok3) else 1
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main():
    if "--selftest" in sys.argv:
        return selftest()
    files = closure(ROOT)
    rows = census(files)
    print("main.asm assembles %d file(s); %s excluded as the FAT layer itself\n"
          % (len(files), len([f for f in files if f in LAYER])))
    per = {}
    for f, i, kind, code in rows:
        per.setdefault(f, []).append((i, kind, code))
    for f in sorted(per):
        v = sum(1 for r in per[f] if r[1] == "VECTOR")
        print("%-28s %2d site(s)%s" % (f, len(per[f]),
                                       "   <- %d VECTOR" % v if v else ""))
        for i, kind, code in per[f]:
            print("    %-6s %5d  %s" % (kind, i, code))
    vec = [r for r in rows if r[2] == "VECTOR"]
    print("\nMAIN-SIDE DEPENDENCIES ON THE FAT LAYER: %d in %d file(s)"
          % (len(rows), len(per)))
    print("  VECTOR (per-byte, THE PIN): %d" % len(vec))
    print("  CALL   (moves with its verb): %d" % (len(rows) - len(vec)))
    print("\nThe VECTOR sites are the same act in three places: `ld hl,"
          "fat_io_getbyte`\nstored into ARL_GETBYTE, which three device-agnostic"
          " loops jump through once\nper byte. The CALL sites are ordinary and"
          " move with their verb.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
