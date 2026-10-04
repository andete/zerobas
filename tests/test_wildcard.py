# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: 8.3 wildcard matching for FILES/KILL (option-closure Item 4), no
emulator.

Two pure pieces underpin FILES "pattern" and KILL "pattern":
  * build_83_name (bload.asm) turns a source filename into the 11-byte 8.3 field,
    now expanding '*' to fill the rest of the name/ext field with '?' (CP/M FCB
    semantics) -- so "*.BAS" -> "????????BAS", "A*.*" -> "A??????????".
  * name_cmp (basic/fat-prim-body.inc) compares an 11-byte pattern (DE) against a
    directory entry (HL), treating '?' in the pattern as "match any char"
    (Z=match).

Together they let FILES filter the listing and KILL delete every match. This
drives both directly (no disk I/O). Oracle: the documented 8.3 '*'/'?' wildcard
semantics (MSX-BASIC / CP/M FCB), never the ROM's own output.

🔴 THE TWO HALVES NOW BUILD DIFFERENT IMAGES, AND THAT IS THE POINT (D-LFILES,
2026-08-06, docs/spec-basic-lfiles.md §6). `name_cmp` had a MAIN-ROM marshalling
shim -- the Z result rode DISKOP_STATUS -- kept alive by exactly one main-side
caller, do_files's filespec filter. D-LFILES moved that walk into the sub-ROM
dirverb tenant, where `name_cmp` resolves to the sub-local primitive BODY, and the
shim died with its last caller.

⚠️ THIS FILE WAS THE CONSUMER THAT GREP DID NOT FIND. The carve's denominator was
walked over `call name_cmp` in *.asm/*.inc and came back with one hit; a HOST unit
test calling the label by NAME through msxtest's sub-ROM bridge is not a `call`
site and matched nothing ([[a-hand-listed-denominator-is-a-scope-claim]]). `make
unit-test` is what found it, which is the argument for running the whole corpus
rather than the gates a slice thinks it touched. The test now drives the body
where the body lives -- a $0000-based sub.rom image -- so it exercises the code
every real caller reaches instead of a marshalling layer that no longer exists.
"""

import os
from _tmp import tp
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine, zero  # noqa: E402

# The image under test is loaded at its ORG. Named here rather than
# defaulted: msxtest.Machine's old default was $4000, the retired lean
# cart's org, so a BASIC test that omitted it silently tested the lean
# build (docs/spec-lean-retire-s3-gates.md §5, F-U).
BASIC_BASE = 0x2765
# The sub-ROM is a flat $0000-based 32 KB image spanning BOTH pages, so a symbol
# in it is already at the address a real CALSLT would map it to (test_msgsub.py's
# note). `name_cmp` is inside the page-1 fatprim tenant, i.e. $4000+.
SUB_BASE = 0x0000

ROM = tp("zb_wildcard.rom")
SYM = tp("zb_wildcard.sym")
SUB_ROM = tp("zb_wildcard_sub.rom")
SUB_SYM = tp("zb_wildcard_sub.sym")
SRC = 0xC400   # scratch source filename buffer


def build():
    src = os.path.join(ROOT, "basic", "main.asm")
    subprocess.run(["pasmo", "--bin", src, ROM, SYM], check=True, capture_output=True)
    subprocess.run(["pasmo", "-I", "sub", "--bin", "sub/sub.asm", SUB_ROM, SUB_SYM],
                   check=True, capture_output=True, cwd=ROOT)


def run():
    build()
    m = Machine(ROM, SYM, rom_base=BASIC_BASE)
    s = m.sym
    fails = 0

    def report(label, got, want):
        nonlocal fails
        ok = got == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label:34} -> {got!r}" + ("" if ok else f"   want {want!r}"))

    NAME = s["DISK_FCB_NAME"]

    def expand(src):
        # source filename followed by the closing '"' that build_83_name stops on
        buf = src.encode("ascii") + b'"'
        m.mem[SRC:SRC + len(buf)] = buf
        cpu = m.call("build_83_name", hl=SRC)
        from msxtest import carry
        if carry(cpu):
            return "<reject>"
        return bytes(m.mem[NAME:NAME + 11]).decode("latin1")

    # build_83_name '*' expansion (and plain names unchanged)
    report("expand FILE.BAS", expand("FILE.BAS"), "FILE    BAS")
    report("expand *.BAS",    expand("*.BAS"),    "????????BAS")
    report("expand *.*",      expand("*.*"),      "???????????")   # all files
    report("expand A*.*",     expand("A*.*"),     "A??????????")
    report("expand * (CP/M literal: name wild, ext spaces)", expand("*"), "????????   ")
    report("expand FOO.B*",   expand("FOO.B*"),   "FOO     B??")
    report("expand DATA*.TX", expand("DATA*.TX"), "DATA????TX ")
    report("expand ??.BAS",   expand("??.BAS"),   "??      BAS")   # literal '?' kept

    # name_cmp wildcard matching: DE = pattern, HL = entry; Z = match.
    # ⚠️ A SECOND MACHINE, ON THE SUB IMAGE. See the module docstring: the main
    # ROM has no `name_cmp` since D-LFILES, and asserting against a shim that
    # only marshalled the result was always a weaker reading than driving the
    # body. Both buffers are RAM ($8000+), which both images address identically.
    ms = Machine(SUB_ROM, SUB_SYM, rom_base=SUB_BASE)
    PAT = 0xC500
    ENT = 0xC520

    def match(pattern, entry):
        ms.mem[PAT:PAT + 11] = pattern.encode("latin1")
        ms.mem[ENT:ENT + 11] = entry.encode("latin1")
        cpu = ms.call("name_cmp", de=PAT, hl=ENT)
        return zero(cpu)

    report("match ????????BAS vs FILE   BAS", match("????????BAS", "FILE    BAS"), True)
    report("match ????????BAS vs FILE   BIN", match("????????BAS", "FILE    BIN"), False)
    report("match A?????????? vs APPLE  TXT", match("A??????????", "APPLE   TXT"), True)
    report("match A?????????? vs BANANA TXT", match("A??????????", "BANANA  TXT"), False)
    report("match exact FILE   BAS (self)",   match("FILE    BAS", "FILE    BAS"), True)
    report("match ??????? ?BAS wild-last",    match("???????????", "ZZZZ    ZZZ"), True)
    report("match FOO     B?? vs FOO    BAK",  match("FOO     B??", "FOO     BAK"), True)
    report("match FOO     B?? vs FOO    TXT",  match("FOO     B??", "FOO     TXT"), False)

    print()
    print("ALL PASS — 8.3 '*'/'?' wildcard expansion + matching"
          if not fails else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
