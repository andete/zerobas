#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BIOSLADDER -- run one rung (our own ROM cartridge) on the reference and on zerobas.

    python3 -u probes/bios/biosl_run.py RUNG|--all [--row nodisk|disk|both]

A rung is probes/bios/biosl/RUNG.asm: a 16 KB "AB" cartridge whose INIT runs the
program, writes its results to the capture block at CAP and $A5 to DONE, then loops.
Its header comment may carry the harness settings, one per line:
    ; @keys TEXT        typed into the keyboard (openMSX `type`) once the program
                        sets KEYREADY ($E100) to 1 -- after its own KILBUF, so a
                        machine that reaches INIT later loses no key
    ; @matrix ROW MASK  a raw key-matrix press (keymatrixdown, hex mask) for 0.3 s
                        at KEYREADY -- no `type` logic in between
    ; @vram ADDR:LEN    a VRAM span to compare as well (hex, e.g. 0000:3C0)
    ; @timeout SECONDS  emulated seconds to wait for DONE (default 30)
Rows (Joost 2026-11-10: ROM cartridges only, a NODISK row per rung):
    nodisk  Philips_VG_8020         vs  C-BIOS_MSX1_EU_REPACK_NODISK
    disk    Philips_VG_8020_NMS1200 vs  C-BIOS_MSX1_EU_REPACK_DISK
The reference is the VG-8020 on both rows (presentational splits go to it, 2026-09-04;
the CF-3300 is a Japanese MSX1, whose BIOS differs from both for reasons of its own).

CLEAN-ROOM: only OUR program's RAM (the capture block) and VRAM are read back through
the emulator's debugger -- never a ROM byte. Exit 0: every row identical; 1: a
divergence; 2: a machine gave no reading (DONE never set: say which).
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "tools"))
import omsx_preflight  # noqa: E402
import openmsx_paths  # noqa: E402

HERE = os.path.join(REPO, "probes", "bios", "biosl")
DONE, CAP, CAPLEN, KEYREADY = 0xE000, 0xE001, 0xFF, 0xE100
# Excused bytes, per rung, on both rows: address -> (OUR pinned value, why). A byte
# here is excused only while ours still reads the pinned value -- the reference's is
# free -- so a fix (or a regression) of ours shows up as a diff again.
ALLOW = {
    "b1text": {
        0xE002: (0x0A, "CSRY at INIT: where the boot banner left the cursor (VG-8020 "
                       "row 15, ours 10) -- presentational, a cartridge's CLS hides it"),
        0xE014: (0x17, "CRTCNT after DSPFNK: ours 23, the VG-8020 24 -- TODO.md "
                       "'CRTCNT UNDER KEY ON', filed TIER 1 (the scroll bound)"),
    },
}
ROWS = {
    "nodisk": ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"),
    "disk": ("Philips_VG_8020_NMS1200", "C-BIOS_MSX1_EU_REPACK_DISK"),
}


def settings(asm_text: str) -> dict:
    s = {"keys": None, "matrix": None, "vram": None, "timeout": 30.0}
    for m in re.finditer(r"^;\s*@([\w-]+)\s+(.*?)\s*$", asm_text, re.M):
        k, v = m.group(1), m.group(2)
        if k == "keys":
            s["keys"] = v
        elif k == "matrix":                 # ROW MASK: a raw key-matrix press
            r, mk = v.split()
            s["matrix"] = (int(r), int(mk, 16))
        elif k == "timeout":
            s[k] = float(v)
        elif k == "vram":
            a, n = v.split(":")
            s["vram"] = (int(a, 16), int(n, 16))
    return s


def asm_path(rung: str) -> str:
    """A rung name (probes/bios/biosl/RUNG.asm) or a path to an .asm (a diagnostic)."""
    return rung if rung.endswith(".asm") else os.path.join(HERE, rung + ".asm")


def build(rung: str, td: str) -> str:
    asm = asm_path(rung)
    rom = os.path.join(td, os.path.basename(asm)[:-4] + ".rom")
    subprocess.run(["pasmo", "--bin", asm, rom], check=True,
                   stdout=subprocess.DEVNULL)
    blob = open(rom, "rb").read()
    if len(blob) > 0x4000 or blob[:2] != b"AB":
        sys.exit(f"{rung}: not a <= 16 KB AB cartridge ({len(blob)} B)")
    open(rom, "wb").write(blob + b"\xff" * (0x4000 - len(blob)))
    return rom


def run(machine: str, rom: str, st: dict, td: str):
    out = os.path.join(td, machine + ".txt")
    keys = ""
    if st["keys"]:
        keys = (f"  if {{$::typed == 0 && [debug read memory {KEYREADY}] == 1}} "
                f"{{ set ::typed 1; type {{{st['keys']}}} }}\n")
    if st["matrix"]:
        r, mk = st["matrix"]
        keys += (f"  if {{$::typed == 0 && [debug read memory {KEYREADY}] == 1}} "
                 f"{{ set ::typed 1; keymatrixdown {r} {mk:#x}; "
                 f"after time 0.3 {{keymatrixup {r} {mk:#x}}} }}\n")
    vram = ""
    if st["vram"]:
        a, n = st["vram"]
        vram = f'  binary scan [debug read_block VRAM {a} {n}] H* vr\n  puts $f "VRAM $vr"\n'
    tcl = ("set throttle off\nset ::typed 0\n"
           "proc biosl_poll {} {\n" + keys +
           f"  if {{[debug read memory {DONE}] == 0xA5 || [machine_info time] > {st['timeout']}}} {{\n"
           f"    set f [open {{{out}}} w]\n"
           f"    puts $f \"DONE [debug read memory {DONE}]\"\n"
           f"    binary scan [debug read_block memory {CAP} {CAPLEN}] H* v\n"
           '    puts $f "CAP $v"\n'
           '    puts $f "VDPR1 [debug read {VDP regs} 1]"\n'
           '    binary scan [debug read_block memory 0xFC9E 2] H* j\n'
           '    binary scan [debug read_block memory 0xF3F8 4] H* kp\n'
           '    binary scan [debug read_block memory 0xF3F6 1] H* sc\n'
           '    binary scan [debug read_block memory 0xFBE5 11] H* nk\n'
           '    binary scan [debug read_block memory 0xFD9A 10] H* hk\n'
           '    puts $f "SYS jiffy=$j putpnt,getpnt=$kp typed=$::typed scncnt=$sc newkey=$nk hkeyi,htimi=$hk"\n' + vram +
           "    close $f\n    exit\n  }\n"
           "  after time 0.1 biosl_poll\n}\n"
           "after time 1 biosl_poll\n")
    script = os.path.join(td, machine + ".tcl")
    open(script, "w").write(tcl)
    subprocess.run(omsx_preflight.guarded(
        [openmsx_paths.find_openmsx_binary(), "-machine", machine, "-cart", rom,
         "-command", "set renderer none; set sound_driver null", "-script", script]),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
    if not os.path.exists(out):
        return None
    got = {}
    for line in open(out):
        k, _, v = line.strip().partition(" ")
        got[k] = v
    return got


def diff(label: str, a: bytes, b: bytes, base: int) -> list[str]:
    return [f"  {label} {base + i:04X}: ref={x:02X} ours={y:02X}"
            for i, (x, y) in enumerate(zip(a, b)) if x != y]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("rung", nargs="?")
    ap.add_argument("--all", action="store_true", help="every rung in probes/bios/biosl")
    ap.add_argument("--row", choices=("nodisk", "disk", "both"), default="both")
    a = ap.parse_args()
    if a.all:
        rungs = sorted(f[:-4] for f in os.listdir(HERE) if f.endswith(".asm"))
    elif a.rung:
        rungs = [a.rung]
    else:
        ap.error("a RUNG or --all")
    rc = 0
    for rung in rungs:
        rc = max(rc, one(rung, a.row))
    print(f"===== biosl: {'ALL SAME (allowlisted bytes excused)' if rc == 0 else 'DIVERGENCE' if rc == 1 else 'NO READING'} =====")
    return rc


def one(rung: str, rows: str) -> int:
    class A:
        pass
    a = A()
    a.rung, a.row = rung, rows
    st = settings(open(asm_path(a.rung)).read())
    allow = ALLOW.get(os.path.basename(a.rung).removesuffix(".asm"), {})
    rc = 0
    td = tempfile.mkdtemp(prefix="biosl_")
    try:
        rom = build(a.rung, td)
        for row in (("nodisk", "disk") if a.row == "both" else (a.row,)):
            ref_m, zb_m = ROWS[row]
            ref, zb = run(ref_m, rom, st, td), run(zb_m, rom, st, td)
            print(f"===== {a.rung} {row}: {ref_m} vs {zb_m} =====")
            bad = [n for n, g in (("ref", ref), ("ours", zb))
                   if not g or g.get("DONE") != "165"]
            if bad:
                print(f"  NO READING: DONE never set on {', '.join(bad)} "
                      f"(ref {ref and ref.get('DONE')}, ours {zb and zb.get('DONE')})")
                rc = max(rc, 2)
                if not (ref and zb):
                    continue
            d = diff("CAP", bytes.fromhex(ref["CAP"]), bytes.fromhex(zb["CAP"]), CAP)
            if st["vram"]:
                d += diff("VRAM", bytes.fromhex(ref["VRAM"]), bytes.fromhex(zb["VRAM"]),
                          st["vram"][0])
            print(f"  VDP R#1 at the dump: ref {ref.get('VDPR1')}, ours {zb.get('VDPR1')}")
            print(f"  ref : {ref.get('SYS')}\n  ours: {zb.get('SYS')}")
            print(f"  CAP ref : {ref['CAP'][:64]}")
            print(f"  CAP ours: {zb['CAP'][:64]}")
            zbcap = bytes.fromhex(zb["CAP"])
            unexcused, excused = [], []
            for line in d:
                addr = int(line.split()[1].rstrip(":"), 16)
                pin = allow.get(addr) if line.lstrip().startswith("CAP") else None
                if pin and zbcap[addr - CAP] == pin[0]:
                    excused.append(f"{line}  (excused: {pin[1]})")
                else:
                    unexcused.append(line)
            for e in excused:
                print(e)
            if unexcused:
                rc = max(rc, 1)
                print(f"  DIFF ({len(unexcused)} unexcused byte(s)):")
                print("\n".join(unexcused[:80]))
            else:
                print(f"  SAME ({len(excused)} allowlisted)")
    finally:
        shutil.rmtree(td, ignore_errors=True)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
