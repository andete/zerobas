#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-BIOSLADDER -- run one rung (our own ROM cartridge) on the reference and on zerobas.

    python3 -u probes/bios/biosl_run.py RUNG|--all [--row nodisk|disk|both|cf3300]

A rung is probes/bios/biosl/RUNG.asm: a 16 KB "AB" cartridge whose INIT runs the
program, writes its results to the capture block at CAP and $A5 to DONE, then loops.
Its header comment may carry the harness settings, one per line:
    ; @keys TEXT        typed into the keyboard (openMSX `type`) once the program
                        sets KEYREADY ($E100) to 1 -- after its own KILBUF, so a
                        machine that reaches INIT later loses no key
    ; @matrix ROW MASK [ROW MASK ...]  raw key-matrix presses (keymatrixdown, hex masks), all
                        held together for 0.3 s (e.g. `6 02 7 10`: CTRL + STOP)
                        at KEYREADY -- no `type` logic in between
    ; @vram ADDR:LEN    a VRAM span to compare as well (hex, e.g. 0000:3C0); repeatable
    ; @vdpsnap ADDR PTR when the CPU reaches ADDR (hex, the probe's own RAM code, e.g. a `ret`), the debugger
    ;                   writes VDP registers R#0-R#7 (as last written: hardware state, no ROM byte) at the
    ;                   address held in the word at PTR, and adds 8 to that word -- the probe's capture
    ;                   pointer, so the snapshot lands inline in its record
    ; @keyset ADDR LIST when the CPU reaches ADDR (hex, the probe's own RAM code, e.g. a `ret`), the debugger
    ;                   sets the keyboard matrix from the 11 bytes at LIST (hex): row r's byte, bit set = key
    ;                   pressed (keymatrixup / keymatrixdown) -- one matrix per case, set by the probe
    ; @timeout SECONDS  emulated seconds to wait for DONE (default 30)
    ; @cap ADDR         DONE's address (hex, default E000): CAP = +1, KEYREADY = +$100
    ; @caplen LEN       the capture block's length (hex, default FF). D-SPECMETHOD (2026-11-17):
                        a matrix rung records more than FF bytes. KEYREADY / TAPEREADY sit at
                        CAP's +$FF..+$101, inside a longer block, so LEN > FF refuses with
                        @keys / @matrix / @tape
                        -- a rung that lets the disk ROM start moves it below HIMEM
    ; @type-at S TEXT   TEXT typed at S emulated seconds ('\\r' = Enter) -- e.g. our
                        disk machine's date question, which the VG-8020 + NMS 1200
                        does not ask (a CF-3300 behaviour our disk target keeps)
    ; @tape             a fresh recording from boot (cassetteplayer new); when the
                        program sets TAPEREADY (+$101) to 1 the harness rewinds, plays
                        and acknowledges with 1 at +$102
    ; @printer          openMSX's printer logger is plugged into the printer port; the bytes the
                        printer received are reported as `PRN ref:` / `PRN ours:` (hex) and compared
    ; @disk empty       the disk row gets drive A = a fresh copy of disk/empty720.dsk
                        (`make test-dsk`); the NODISK row has no drive
Rows (Joost 2026-11-10: ROM cartridges only, a NODISK row per rung):
    nodisk  Philips_VG_8020         vs  C-BIOS_MSX1_EU_REPACK_NODISK
    disk    Philips_VG_8020_NMS1200 vs  C-BIOS_MSX1_EU_REPACK_DISK
    cf3300  National_CF-3300        vs  C-BIOS_MSX1_EU_REPACK_DISK   (only on request: --row cf3300)
The reference is the VG-8020 on both default rows (presentational splits go to it, 2026-09-04;
the CF-3300 is a Japanese MSX1, whose BIOS differs from both for reasons of its own). The
cf3300 row (Joost 2026-11-18) is for the SLOT calls: its RAM is the expanded slot 3-0, as on
zerobas's machine, where neither VG-8020 row has expanded RAM. It boots with drive A as the
disk row does.

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
    "b5sound": {
        0xE010: (0x8F, "R15 at INIT: bit 6 is the joystick-port select, left by the last "
                       "port read (VG-8020 $CF) -- I/O state, not a BIOS contract"),
        0xE001: (0x00, "R0 at INIT, disk row: $55 on the VG-8020 + NMS 1200 (a beep at its "
                       "boot, kept by GICINI) -- D-PSGINIT"),
        0xE011: (0x00, "R0 after GICINI, disk row: $55 there -- D-PSGINIT"),
    },
    "b6slots": {
        0xE00B: (0x80, "EXPTBL slot 3 expanded: ours (RAM 3-0, disk 3-1, sub 3-2), the "
                       "VG-8020's is not -- hardware, not the BIOS"),
    },
    "b8save": {
        0xA002: (0xC9, "$F37D with no disk interface: ours RET, the VG-8020 $00 -- filed "
                       "(D-F37DNODISK); a ROM checks H.PHYD first, as this one does"),
    },
    "b1text": {
        0xE002: (0x0A, "CSRY at INIT: where the boot banner left the cursor (VG-8020 "
                       "row 15, ours 10) -- presentational, a cartridge's CLS hides it"),
    },
}
ROWS = {
    "nodisk": ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"),
    "disk": ("Philips_VG_8020_NMS1200", "C-BIOS_MSX1_EU_REPACK_DISK"),
    "cf3300": ("National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK"),
    # D-DISKFORCBIOS (b) (2026-11-22): a THIRD disk interface -- the NMS 8250's built-in drive (MSX2, the
    # Philips-style FDC) -- for the disk pages' black-box rules. MSX2: a run here answers "does the rule hold on
    # another interface", not "is zerobas an MSX2"; zerobas's side is the same disk machine as the other rows.
    "nms8250": ("Philips_NMS_8250", "C-BIOS_MSX1_EU_REPACK_DISK"),
}


def settings(asm_text: str) -> dict:
    s = {"keys": None, "matrix": None, "vram": [], "timeout": 30.0, "disk": None,
         "cap": DONE, "type_at": None, "tape": False, "caplen": CAPLEN, "printer": False,
         "vdpsnap": None, "keyset": None}
    # one directive per line: `[ \t]` never crosses a newline (an argument-less @printer / @tape would
    # otherwise take the next line as its value)
    for m in re.finditer(r"^;[ \t]*@([\w-]+)(?:[ \t]+(.*?))?[ \t]*$", asm_text, re.M):
        k, v = m.group(1), (m.group(2) or "")
        if k == "keys":
            s["keys"] = v
        elif k == "matrix":                 # ROW MASK [ROW MASK ...]: raw key-matrix presses, held together
            f = v.split()
            if not f or len(f) % 2:
                sys.exit(f"FAIL: @matrix wants ROW MASK pairs, got {v!r}")
            s["matrix"] = [(int(f[i]), int(f[i + 1], 16)) for i in range(0, len(f), 2)]
        elif k == "cap":                    # DONE's address (hex); CAP = +1, KEYREADY = +$100
            s["cap"] = int(v, 16)
        elif k == "caplen":                 # the capture block's length (hex)
            s["caplen"] = int(v, 16)
        elif k == "type-at":                # SECONDS TEXT: typed at that emulated time
            t, _, txt = v.partition(" ")
            s["type_at"] = (float(t), txt)
        elif k == "tape":                   # record from boot; play on TAPEREADY
            s["tape"] = True
        elif k == "printer":                # plug the printer logger; report what it received
            s["printer"] = True
        elif k == "disk":                   # empty: a copy of disk/empty720.dsk
            s["disk"] = v
        elif k == "timeout":
            s[k] = float(v)
        elif k == "vdpsnap":                # ADDR PTR (hex)
            f = v.split()
            if len(f) != 2:
                sys.exit(f"FAIL: @vdpsnap wants ADDR PTR, got {v!r}")
            s["vdpsnap"] = (int(f[0], 16), int(f[1], 16))
        elif k == "keyset":                 # ADDR LIST (hex)
            f = v.split()
            if len(f) != 2:
                sys.exit(f"FAIL: @keyset wants ADDR LIST, got {v!r}")
            s["keyset"] = (int(f[0], 16), int(f[1], 16))
        elif k == "vram":
            a, n = v.split(":")
            s["vram"].append((int(a, 16), int(n, 16)))
    if s["caplen"] > CAPLEN and (s["keys"] or s["matrix"] or s["tape"]):
        sys.exit("FAIL: @caplen > FF overlaps KEYREADY / TAPEREADY (CAP's +$FF..+$101): a rung "
                 "with @keys / @matrix / @tape keeps the default capture length")
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


def run(machine: str, rom: str, st: dict, td: str, disk: bool = False):
    out = os.path.join(td, machine + ".txt")
    DONE, CAP, KEYREADY = st["cap"], st["cap"] + 1, st["cap"] + 0x100
    keys = ""
    if st["keys"]:
        keys = (f"  if {{$::typed == 0 && [debug read memory {KEYREADY}] == 1}} "
                f"{{ set ::typed 1; type {{{st['keys']}}} }}\n")
    if st["matrix"]:
        down = "; ".join(f"keymatrixdown {r} {mk:#x}" for r, mk in st["matrix"])
        up = "; ".join(f"keymatrixup {r} {mk:#x}" for r, mk in st["matrix"])
        keys += (f"  if {{$::typed == 0 && [debug read memory {KEYREADY}] == 1}} "
                 f"{{ set ::typed 1; {down}; after time 0.3 {{{up}}} }}\n")
    vram = ""
    for i, (va, vn) in enumerate(st["vram"]):
        vram += (f'  binary scan [debug read_block VRAM {va} {vn}] H* vr\n'
                 f'  puts $f "VRAM{i} $vr"\n')
    tape = ""
    if st["tape"]:
        wav = os.path.join(td, machine + ".wav")
        tape = (f"cassetteplayer new {{{wav}}}\n"
                "set ::taped 0\n")
        keys += (f"  if {{$::taped == 0 && [debug read memory {DONE + 0x101}] == 1}} "
                 f"{{ set ::taped 1; cassetteplayer rewind; cassetteplayer play; "
                 f"debug write memory {DONE + 0x102} 1 }}\n")
    at = ""
    if st["type_at"]:
        t, txt = st["type_at"]
        at = f'after time {t} {{type "{txt}"}}\n'
    snap = ""
    if st["vdpsnap"]:
        sa, sp = st["vdpsnap"]
        snap = ("proc biosl_vdpsnap {} {\n"
                f"  set p [expr {{[debug read memory {sp}] | ([debug read memory {sp + 1}] << 8)}}]\n"
                "  for {set i 0} {$i < 8} {incr i} {\n"
                "    debug write memory [expr {($p + $i) & 0xFFFF}] [debug read {VDP regs} $i]\n  }\n"
                "  set p [expr {($p + 8) & 0xFFFF}]\n"
                f"  debug write memory {sp} [expr {{$p & 255}}]\n"
                f"  debug write memory {sp + 1} [expr {{$p >> 8}}]\n}}\n"
                f"debug set_bp {sa} {{}} biosl_vdpsnap\n")
    if st["keyset"]:
        ka, kl = st["keyset"]
        snap += ("proc biosl_keyset {} {\n"
                 "  for {set r 0} {$r < 11} {incr r} {\n"
                 "    keymatrixup $r 0xff\n"
                 f"    set m [debug read memory [expr {{{kl} + $r}}]]\n"
                 "    if {$m != 0} { keymatrixdown $r $m }\n  }\n}\n"
                 f"debug set_bp {ka} {{}} biosl_keyset\n")
    tcl = ("set throttle off\nset ::typed 0\n" + tape + at + snap +
           "proc biosl_poll {} {\n" + keys +
           f"  if {{[debug read memory {DONE}] == 0xA5 || [machine_info time] > {st['timeout']}}} {{\n"
           f"    set f [open {{{out}}} w]\n"
           f"    puts $f \"DONE [debug read memory {DONE}]\"\n"
           f"    binary scan [debug read_block memory {CAP} {st['caplen']}] H* v\n"
           '    puts $f "CAP $v"\n'
           '    puts $f "VDPR1 [debug read {VDP regs} 1]"\n'
           '    binary scan [debug read_block memory 0xFC9E 2] H* j\n'
           '    binary scan [debug read_block memory 0xF3F6 1] H* sc\n'
           '    binary scan [debug read_block memory 0xFBE5 11] H* nk\n'
           '    binary scan [debug read_block memory 0xFD9A 10] H* hk\n'
           '    puts $f "SYS jiffy=$j typed=$::typed scncnt=$sc newkey=$nk hkeyi,htimi=$hk"\n' + vram +
           "    close $f\n    exit\n  }\n"
           "  after time 0.1 biosl_poll\n}\n"
           "after time 1 biosl_poll\n")
    script = os.path.join(td, machine + ".tcl")
    open(script, "w").write(tcl)
    media = []
    if disk and st["disk"]:
        src = os.path.join(REPO, "disk", "empty720.dsk")
        if not os.path.isfile(src):
            sys.exit("@disk empty: disk/empty720.dsk is missing -- `make test-dsk`")
        dsk = os.path.join(td, machine + ".dsk")
        shutil.copyfile(src, dsk)
        media = ["-diska", dsk]
    prn = os.path.join(td, machine + ".prn")
    plug = ""
    if st["printer"]:
        if os.path.exists(prn):
            os.remove(prn)
        plug = f"; set printerlogfilename {{{prn}}}; plug printerport logger"
    subprocess.run(omsx_preflight.guarded(
        [openmsx_paths.find_openmsx_binary(), "-machine", machine, "-cart", rom] + media +
        ["-command", "set renderer none; set sound_driver null" + plug, "-script", script]),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
    if not os.path.exists(out):
        return None
    got = {}
    for line in open(out):
        k, _, v = line.strip().partition(" ")
        got[k] = v
    if st["printer"]:
        if not os.path.exists(prn):         # the logger never wrote: no reading, not an empty print
            got["DONE"] = "no printer log"
        else:
            got["PRN"] = open(prn, "rb").read().hex()
    return got


def diff(label: str, a: bytes, b: bytes, base: int) -> list[str]:
    return [f"  {label} {base + i:04X}: ref={x:02X} ours={y:02X}"
            for i, (x, y) in enumerate(zip(a, b)) if x != y]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("rung", nargs="?")
    ap.add_argument("--all", action="store_true", help="every rung in probes/bios/biosl")
    ap.add_argument("--row", choices=("nodisk", "disk", "both", "cf3300", "nms8250"), default="both")
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
            ref = run(ref_m, rom, st, td, disk=(row != "nodisk"))
            zb = run(zb_m, rom, st, td, disk=(row != "nodisk"))
            print(f"===== {a.rung} {row}: {ref_m} vs {zb_m} =====")
            bad = [n for n, g in (("ref", ref), ("ours", zb))
                   if not g or g.get("DONE") != "165"]
            if bad:
                print(f"  NO READING: DONE never set on {', '.join(bad)} "
                      f"(ref {ref and ref.get('DONE')}, ours {zb and zb.get('DONE')})")
                rc = max(rc, 2)
                if not (ref and zb):
                    continue
            d = diff("CAP", bytes.fromhex(ref["CAP"]), bytes.fromhex(zb["CAP"]), st["cap"] + 1)
            for i, (va, _) in enumerate(st["vram"]):
                d += diff("VRAM", bytes.fromhex(ref[f"VRAM{i}"]),
                          bytes.fromhex(zb[f"VRAM{i}"]), va)
            print(f"  VDP R#1 at the dump: ref {ref.get('VDPR1')}, ours {zb.get('VDPR1')}")
            print(f"  ref : {ref.get('SYS')}\n  ours: {zb.get('SYS')}")
            def trimmed(h):                 # up to the last non-zero byte, >= 32 B
                b = bytes.fromhex(h)
                end = max(32, len(b.rstrip(b"\0")))
                return b[:end].hex()
            print(f"  CAP ref : {trimmed(ref['CAP'])}")
            print(f"  CAP ours: {trimmed(zb['CAP'])}")
            if st["printer"]:
                print(f"  PRN ref : {ref['PRN']}")
                print(f"  PRN ours: {zb['PRN']}")
                if ref["PRN"] != zb["PRN"]:
                    rc = max(rc, 1)
                    pr, pz = bytes.fromhex(ref["PRN"]), bytes.fromhex(zb["PRN"])
                    k = next((i for i in range(min(len(pr), len(pz))) if pr[i] != pz[i]), min(len(pr), len(pz)))
                    print(f"  PRN DIFF: ref {len(pr)} bytes, ours {len(pz)}; first difference at byte {k}")
            zbcap = bytes.fromhex(zb["CAP"])
            CAP = st["cap"] + 1
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
