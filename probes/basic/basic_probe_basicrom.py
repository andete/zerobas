#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BASICROM gate: a BASIC-PROGRAM CARTRIDGE runs at boot, and a program's
`$0D` line POINTERS are followed -- against the VG-8020, on BOTH machines.
`make basicrom-acceptance`.

🏗️ OUR OWN CARTRIDGES ONLY (Joost, 2026-10-12: a third-party ROM is run, never
decompiled, never in a permanent test). Each image is built here, at run time, to
the PUBLISHED cartridge header format -- `AB`, INIT / STATEMENT / DEVICE = 0,
TEXT = $8010 -- around a program tokenised by our own crunch
(probes/disk/bas_tokenise.py), linked for TXTTAB = TEXT + 1 (the VG-8020's value).

  boot     the program's first line records SCRMOD and LINLEN (the reference runs
           a cartridge in SCREEN 1 at width 29), then prints TXTTAB and VARTAB
           (TEXT + 1 and $C000), a variable and a string; after END, LIST and a
           probe line are typed.
  lptr     every line reference in the program is a `$0D` POINTER (the form the
           reference leaves after a jump has run: the address one byte before the
           target line), not a `$0E` number: GOSUB, GOTO, IF ... THEN, ON ... GOSUB.
           zerobas raised Syntax error on the first one. (RESTORE is NOT one: the
           VG-8020 answers a RESTORE pointer with Undefined line number.)

Prediction (2026-10-12, after the fix): both SAME on both builds.
Clean room: our own images, typed BASIC, the screen.
"""
from __future__ import annotations

import os
import re
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
os.environ.setdefault("ZEROBAS_REFCACHE", "0")   # the image is built per run: no cache
import omsx_repl  # noqa: E402
import bas_tokenise  # noqa: E402

REF = "Philips_VG_8020"
OURS = ("C-BIOS_MSX1_EU_REPACK_NODISK", "C-BIOS_MSX1_EU_REPACK_DISK")
TEXT = 0x8010

BOOT = [(5, "M=PEEK(&HFCAF):W=PEEK(&HF3B0):SCREEN 0"),
        (10, 'PRINT "ZBROM";M;W'),
        (20, "PRINT PEEK(&HF676)+256*PEEK(&HF677);PEEK(&HF6C2)+256*PEEK(&HF6C3)"),
        (30, 'A=5:B$="X":PRINT A;B$'),
        (40, "END")]
LPTR = [(5, "SCREEN 0"),
        (10, "GOSUB 200"),
        (20, "GOTO 40"),
        (30, 'PRINT "NO"'),
        (40, "I=2:ON I GOSUB 210,220"),
        (50, "IF I=2 THEN 70"),
        (60, 'PRINT "NO2"'),
        (70, "PRINT D"),
        (80, "END"),
        (200, 'PRINT "A";:RETURN'),
        (210, 'PRINT "X";:RETURN'),
        (220, 'PRINT "B";:RETURN')]


def build(path, program, pointers=False):
    base = TEXT + 1
    body = bytearray(bas_tokenise.make_multiline_program(program, base))
    if pointers:
        # each line's address, then every `$0E lo hi` naming a line -> `$0D ptr`
        addr, at, lines = base, 0, {}
        while True:
            link = body[at] | body[at + 1] << 8
            if link == 0:
                break
            lines[body[at + 2] | body[at + 3] << 8] = addr
            at, addr = link - base, link
        i, done = 0, 0
        while i < len(body) - 2:
            if body[i] == 0x0E:
                n = body[i + 1] | body[i + 2] << 8
                if n in lines:
                    body[i] = 0x0D
                    body[i + 1:i + 3] = struct.pack("<H", lines[n] - 1)
                    i += 3
                    done += 1
                    continue
            i += 1
        if done != pointers:
            raise SystemExit(f"rewrote {done} line references, expected {pointers} -- "
                             "the image is not the one the case claims")
    img = bytearray(b"\xff" * 0x4000)
    img[0:16] = b"AB" + bytes(6) + struct.pack("<H", TEXT) + bytes(6)
    img[TEXT - 0x8000] = 0
    img[TEXT - 0x8000 + 1:TEXT - 0x8000 + 1 + len(body)] = body
    open(path, "wb").write(bytes(img))


def run(machine, rom, typed):
    raw = omsx_repl.run_cases(machine, [("direct", typed)], batch=False, reset=("",),
                              run_gap=8.0, prologue=(f"carta {{{rom}}}", "reset"))[0] or ""
    flat = raw.replace("\n", "")
    rows = [flat[i:i + 40].strip() for i in range(0, len(flat), 40) if flat[i:i + 40].strip()]
    # the prompt is "ZB" on zerobas by design, "Ok" on the reference: not compared
    return [r for r in rows if r not in ("Ok", "ZB") and not r.startswith("color")]


CASES = {
    "boot": (BOOT, 0, ["LIST", "PRINT PEEK(&HF676)+256*PEEK(&HF677)"]),
    # GOSUB, GOTO, ON (x2), THEN. NOT RESTORE: given a $0D the VG-8020 raises
    # "Undefined line number" (the first run of this gate) -- it never makes one
    # there, its jump-time conversion rewrites jumps only.
    "lptr": (LPTR, 5, []),
}


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="zb_basicrom_gate_")
    bad = 0
    for name, (prog, ptrs, typed) in CASES.items():
        rom = os.path.join(tmp, f"{name}.rom")
        build(rom, prog, ptrs)
        ref = run(REF, rom, typed)
        if not ref:
            print(f"{name:5s} INSTRUMENT FAULT: the VG-8020 gave no reading")
            return 2
        print(f"{name:5s} VG-8020 {ref}", flush=True)
        for m in OURS:
            got = run(m, rom, typed)
            same = got == ref
            bad += not same
            print(f"{name:5s} {m:30s} {'SAME' if same else 'DIVERGES ' + str(got)}",
                  flush=True)
    print("-------------------")
    print("basicrom gate:", "PASS" if not bad else f"FAIL ({bad})")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
