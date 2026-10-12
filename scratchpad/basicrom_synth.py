#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BASICROM, measurement with OUR OWN cartridge: a 16 KB image built to the
published MSX cartridge header format -- `AB`, INIT / STATEMENT / DEVICE = 0,
TEXT = $8010 -- holding a program tokenised by our own crunch
(probes/disk/bas_tokenise.py), linked for TXTTAB = $8011 (the VG-8020 sets
TXTTAB = TEXT + 1, basicrom_golf.out). No third-party byte anywhere.

The cartridge goes in slot 1 from a Tcl prologue (`carta` + `reset`), the
program runs at boot, then the harness types LIST and a probe line, and the
screen is read. VG-8020 against the NODISK build.

FIRST RUN: the VG-8020's screen read as garbage -- it runs the cartridge in
SCREEN 1 (SCRMOD 1, basicrom_probe.py on this image), and the screen reader
assumed SCREEN 0. Line 5 now records SCRMOD and LINLEN, then sets SCREEN 0.

Prediction: the VG-8020 prints ZBROM 1 29, the pointers 32785 (TXTTAB $8011) and
49152 (VARTAB $C000), " 5 X", then LIST shows lines 10-40; zerobas prints none
of it and LIST is empty.
"""
import os, re, struct, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
import omsx_repl                                   # noqa: E402
import bas_tokenise                                # noqa: E402

MACHINES = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK")
TEXT = 0x8010
PROGRAM = [(5, "M=PEEK(&HFCAF):W=PEEK(&HF3B0):SCREEN 0"),
           (10, 'PRINT "ZBROM";M;W'),
           (20, "PRINT PEEK(&HF676)+256*PEEK(&HF677);PEEK(&HF6C2)+256*PEEK(&HF6C3)"),
           (30, 'A=5:B$="X":PRINT A;B$'),
           (40, "END")]


def build(path, program=PROGRAM, text=TEXT):
    img = bytearray(b"\xff" * 0x4000)
    img[0:16] = b"AB" + bytes(6) + struct.pack("<H", text) + bytes(6)
    body = bas_tokenise.make_multiline_program(program, text + 1)
    off = text - 0x8000
    img[off] = 0
    img[off + 1:off + 1 + len(body)] = body
    open(path, "wb").write(bytes(img))


def run(machine, rom, typed):
    pro = (f"carta {{{rom}}}", "reset")
    raw = omsx_repl.run_cases(machine, [("direct", typed)], batch=False,
                              reset=("",), run_gap=8.0, prologue=pro)[0] or ""
    flat = raw.replace("\n", "")
    return [flat[i:i + 40].rstrip() for i in range(0, len(flat), 40) if flat[i:i + 40].strip()]


def main():
    os.environ["ZEROBAS_REFCACHE"] = "0"
    rom = os.path.join(tempfile.mkdtemp(prefix="zb_basicrom_"), "synth.rom")
    build(rom)
    for m in MACHINES:
        rows = run(m, rom, ["LIST", "PRINT FRE(0);PEEK(&HF676)+256*PEEK(&HF677)"])
        print(f"=== {m}")
        for r in rows:
            print("   " + r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
