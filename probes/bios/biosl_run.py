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
    ; @vdpfull ADDR PTR as @vdpsnap, but the whole VDP state: R#0-R#63 (as last written), S#0-S#15, the VRAM
    ;                   pointer (2 bytes) and the palette (32) -- 114 bytes, PTR += 114; a debuggable the machine
    ;                   lacks reads 0 (D-MSX2SPEC)
    ; @portlog PORT PTR ARM  every OUT to PORT (hex, e.g. 99) appends its byte at the address held in the word at
    ;                   PTR and adds 1 to it; a PTR word of 0 logs nothing (the probe arms / disarms it per case).
    ;                   The watch starts only once the CPU reaches ARM (the probe's own code, after it has written
    ;                   the PTR word): before that the word is whatever boot left there
    ; @psglog PTR ARM [SKIP]  (D-MSX2SPEC, sub-ROM BEEP) every OUT to $A1 (the PSG's data port) appends 5 bytes at the
    ;                   address held in the word at PTR, PTR += 5: the register last selected through $A0, the
    ;                   byte, and the emulated time in microseconds (24-bit, little-endian, wraps at ~16.7 s) --
    ;                   a timed trace of PSG writes. PTR word 0 logs nothing; armed at ARM as @portlog. SKIP
    ;                   (hex, optional): a 16-bit mask of registers whose writes are not logged (8000 = R15,
    ;                   which the timer interrupt's trigger read writes every frame)
    ; @plug CONN DEVICE (D-MSX2SPEC, sub-ROM NEWPAD) `plug CONN DEVICE` on BOTH machines before boot, e.g.
    ;                   `@plug joyporta mouse`; repeatable. The device is idle (no host input reaches it)
    ; @keyset ADDR LIST when the CPU reaches ADDR (hex, the probe's own RAM code, e.g. a `ret`), the debugger
    ;                   sets the keyboard matrix from the 11 bytes at LIST (hex): row r's byte, bit set = key
    ;                   pressed (keymatrixup / keymatrixdown) -- one matrix per case, set by the probe
    ; @cpusnap ADDR PTR (D-TRSPEC) when the CPU reaches ADDR (hex, the probe's own code), the debugger writes
    ;                   5 bytes at the address held in the word at PTR, PTR += 5: the active CPU (0 = Z80, 1 = R800;
    ;                   openMSX's get_active_cpu, i.e. the S1990's CPU-select bit -- hardware state, no ROM byte; 0 on
    ;                   a machine without an S1990) and the emulated time in microseconds (32-bit, little-endian,
    ;                   wraps at ~71 min). Repeatable (one breakpoint each, PTRs may be shared): two snapshots
    ;                   around a fixed loop time it
    ; @timeout SECONDS  emulated seconds to wait for DONE (default 30)
    ; @cap ADDR         DONE's address (hex, default E000): CAP = +1, KEYREADY = +$100
    ; @caplen LEN       the capture block's length (hex, default FF). D-SPECMETHOD (2026-11-17):
                        a matrix rung records more than FF bytes. KEYREADY / TAPEREADY sit at
                        CAP's +$FF..+$101, inside a longer block, so LEN > FF refuses with
                        @keys / @matrix / @tape
                        -- a rung that lets the disk ROM start moves it below HIMEM
    ; @type-ready TEXT  TEXT typed as @type-at types it ('\\r' = Enter), but once the program sets KEYREADY
                        (as @keys): a machine that boots slower loses no key (D-MSX1ON2: the NMS 8250 /
                        FS-A1WSX reached xlin's program after @type-at 4 had fired)
    ; @type-at S TEXT   TEXT typed at S emulated seconds ('\\r' = Enter) -- e.g. our
                        disk machine's date question, which the VG-8020 + NMS 1200
                        does not ask (a CF-3300 behaviour our disk target keeps)
    ; @tape             a fresh recording from boot (cassetteplayer new); when the
                        program sets TAPEREADY (+$101) to 1 the harness rewinds, plays
                        and acknowledges with 1 at +$102. On a machine WITHOUT a cassette
                        port (the turbo R: openMSX has no `cassetteplayer` there, or it
                        fails) the run goes on: nothing is recorded or played, TAPEREADY
                        is acknowledged with 2 at +$102 (a probe waiting for non-zero
                        runs its cases on), and the output says `TAPE ref/ours: no
                        cassette port (...)` (D-TRSPEC; a machine with a port: unchanged)
    ; @printer          openMSX's printer logger is plugged into the printer port; the bytes the
                        printer received are reported as `PRN ref:` / `PRN ours:` (hex) and compared
    ; @disk empty       the disk row gets drive A = a fresh copy of disk/empty720.dsk
                        (`make test-dsk`); the NODISK row has no drive
    ; @disk PATH        (D-MSX2SPEC, the BLT disk calls) drive A = a fresh copy of the image PATH ($VARS
                        expanded, e.g. $ZEROBAS_TMP/x.dsk; relative = to the repo) -- media are never
                        committed: the probe's own script builds the image
    BIOSL_KEEP_DSK=DIR  (env) after each run, the machine's drive-A image as the run left it is copied to
                        DIR/<machine>.dsk, so the files a call wrote can be read back from the host side
Rows (Joost 2026-11-10: ROM cartridges only, a NODISK row per rung):
    nodisk  Philips_VG_8020         vs  C-BIOS_MSX1_EU_REPACK_NODISK
    disk    Philips_VG_8020_NMS1200 vs  C-BIOS_MSX1_EU_REPACK_DISK
    cf3300  National_CF-3300        vs  C-BIOS_MSX1_EU_REPACK_DISK   (only on request: --row cf3300)
    msx2eu / msx2jp / msx2p   Philips NMS 8250 / Sony HB-F900 / Panasonic FS-A1WSX vs C-BIOS's own MSX2 EU / MSX2
            JP / MSX2+ JP builds (tools/install_cbios_msx2.py); --row msx2all runs the three (D-MSX2SPEC)
    turbor  Panasonic FS-A1GT vs Panasonic FS-A1ST (D-TRSPEC, only on request). C-BIOS has no turbo R build, so
            this row sets the two turbo R references against each other: "ref" = the FS-A1GT (openMSX's generic
            `turbor`), "ours" = the FS-A1ST, and a DIFF is where the two references disagree. Both boot with their
            built-in drive (drive A only with @disk). The SYS lines add `cpu=` (z80 / r800: the active CPU at the
            dump, as @cpusnap reads it), `t=` (emulated seconds), `fcb1=` (the cell $FCB1, decimal) and
            `s1990r6=` (every change of the S1990's register 6, polled each 0.1 s from 0.1 s on, as TIME:HEX);
            the @vram spans are printed whole (`VRAMn ref:` / `VRAMn ours:`), not only their differences
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
    # D-MSX2SPEC (Joost 2026-11-23): the MSX2 / MSX2+ references -- openMSX's generic machines -- against C-BIOS's
    # OWN MSX2 / MSX2+ builds from the checkout under review (tools/install_cbios_msx2.py, tag CUR). Only on request.
    "msx2eu": ("Philips_NMS_8250", "CBIOS2_CUR_MSX2_EU"),
    "msx2jp": ("Sony_HB-F900", "CBIOS2_CUR_MSX2_JP"),
    "msx2p": ("Panasonic_FS-A1WSX", "CBIOS2_CUR_MSX2P_JP"),
    # D-TRSPEC (2026-11-23): the turbo R. C-BIOS has no turbo R build, so the second machine is the OTHER turbo R
    # reference: the row's diff is a reference-vs-reference comparison (FS-A1GT = "ref", FS-A1ST = "ours").
    "turbor": ("Panasonic_FS-A1GT", "Panasonic_FS-A1ST"),
}


def settings(asm_text: str) -> dict:
    s = {"keys": None, "matrix": None, "vram": [], "timeout": 30.0, "disk": None,
         "cap": DONE, "type_at": None, "tape": False, "caplen": CAPLEN, "printer": False,
         "vdpsnap": None, "keyset": None, "type_ready": None, "vdpfull": None, "portlog": [],
         "psglog": None, "plug": [], "cpusnap": []}
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
        elif k == "type-ready":             # TEXT ('\\r' = Enter): typed once the program sets KEYREADY
            s["type_ready"] = v
        elif k == "tape":                   # record from boot; play on TAPEREADY
            s["tape"] = True
        elif k == "printer":                # plug the printer logger; report what it received
            s["printer"] = True
        elif k == "disk":                   # empty: a copy of disk/empty720.dsk
            s["disk"] = v
        elif k == "timeout":
            s[k] = float(v)
        elif k == "vdpfull":                # ADDR PTR (hex): the whole VDP state, 114 bytes (D-MSX2SPEC)
            f = v.split()
            if len(f) != 2:
                sys.exit(f"FAIL: @vdpfull wants ADDR PTR, got {v!r}")
            s["vdpfull"] = (int(f[0], 16), int(f[1], 16))
        elif k == "portlog":                # PORT PTR ARM (hex): every OUT to PORT appended at (PTR) (D-MSX2SPEC)
            f = v.split()
            if len(f) != 3:
                sys.exit(f"FAIL: @portlog wants PORT PTR ARM, got {v!r}")
            s["portlog"].append((int(f[0], 16), int(f[1], 16), int(f[2], 16)))
        elif k == "psglog":                 # PTR ARM (hex): a timed trace of PSG writes (D-MSX2SPEC)
            f = v.split()
            if len(f) not in (2, 3):
                sys.exit(f"FAIL: @psglog wants PTR ARM [SKIP], got {v!r}")
            s["psglog"] = (int(f[0], 16), int(f[1], 16), int(f[2], 16) if len(f) == 3 else 0)
        elif k == "plug":                   # CONN DEVICE: plugged before boot (D-MSX2SPEC)
            f = v.split()
            if len(f) != 2:
                sys.exit(f"FAIL: @plug wants CONN DEVICE, got {v!r}")
            s["plug"].append((f[0], f[1]))
        elif k == "cpusnap":                # ADDR PTR (hex): active CPU + emulated time, 5 bytes (D-TRSPEC)
            f = v.split()
            if len(f) != 2:
                sys.exit(f"FAIL: @cpusnap wants ADDR PTR, got {v!r}")
            s["cpusnap"].append((int(f[0], 16), int(f[1], 16)))
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
    if s["caplen"] > CAPLEN and (s["keys"] or s["type_ready"] or s["matrix"] or s["tape"]):
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


def run(machine: str, rom: str, st: dict, td: str, disk: bool = False, cpuinfo: bool = False):
    out = os.path.join(td, machine + ".txt")
    DONE, CAP, KEYREADY = st["cap"], st["cap"] + 1, st["cap"] + 0x100
    keys = ""
    if st["keys"]:
        keys = (f"  if {{$::typed == 0 && [debug read memory {KEYREADY}] == 1}} "
                f"{{ set ::typed 1; type {{{st['keys']}}} }}\n")
    if st["type_ready"]:                    # @type-at's quoting (Tcl turns \r / \b into Enter / BS), @keys' timing
        keys += (f"  if {{$::typed == 0 && [debug read memory {KEYREADY}] == 1}} "
                 f"{{ set ::typed 1; type \"{st['type_ready']}\" }}\n")
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
        # D-TRSPEC: a machine without a cassette port (the turbo R) has no working `cassetteplayer`; an uncaught
        # error stopped the whole script there and the run hung into the 600 s timeout. Caught, it is recorded
        # (::notape, the error text) and TAPEREADY is acknowledged with 2 instead of rewinding / playing
        tape = (f"set ::notape [catch {{cassetteplayer new {{{wav}}}}} ::tapeerr]\n"
                "set ::taped 0\n")
        keys += (f"  if {{$::taped == 0 && [debug read memory {DONE + 0x101}] == 1}} {{\n"
                 f"    set ::taped 1\n"
                 f"    if {{$::notape}} {{ debug write memory {DONE + 0x102} 2 }} else {{\n"
                 f"      cassetteplayer rewind; cassetteplayer play; debug write memory {DONE + 0x102} 1 }}\n  }}\n")
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
    if st["vdpfull"]:
        # R#0-R#63 (as last written), S#0-S#15, the VRAM pointer (2), the palette (32) = 114 bytes; a debuggable
        # the machine lacks (a TMS9918 has no palette and one status register) reads 0. Debugger reads: no side effect
        fa, fp = st["vdpfull"]
        snap += ("proc biosl_vdpget {d i} {\n"
                 "  if {[lsearch -exact [debug list] $d] < 0 || $i >= [debug size $d]} { return 0 }\n"
                 "  return [debug read $d $i]\n}\n"
                 "proc biosl_vdpfull {} {\n"
                 f"  set p [expr {{[debug read memory {fp}] | ([debug read memory {fp + 1}] << 8)}}]\n"
                 "  set k 0\n"
                 "  foreach {d n} {{VDP regs} 64 {VDP status regs} 16 {VRAM pointer} 2 {VDP palette} 32} {\n"
                 "    for {set i 0} {$i < $n} {incr i} {\n"
                 "      debug write memory [expr {($p + $k) & 0xFFFF}] [biosl_vdpget $d $i]; incr k\n    }\n  }\n"
                 "  set p [expr {($p + $k) & 0xFFFF}]\n"
                 f"  debug write memory {fp} [expr {{$p & 255}}]\n"
                 f"  debug write memory {fp + 1} [expr {{$p >> 8}}]\n}}\n"
                 f"debug set_bp {fa} {{}} biosl_vdpfull\n")
    for port, lp, arm in st["portlog"]:
        # every OUT to the port: its byte at (lp) and lp += 1 -- the probe owns the buffer and resets lp per case
        snap += (f"proc biosl_plog_{port:02x} {{}} {{\n"
                 f"  set p [expr {{[debug read memory {lp}] | ([debug read memory {lp + 1}] << 8)}}]\n"
                 "  if {$p == 0} { return }\n"
                 "  debug write memory $p $::wp_last_value\n"
                 "  set p [expr {($p + 1) & 0xFFFF}]\n"
                 f"  debug write memory {lp} [expr {{$p & 255}}]\n"
                 f"  debug write memory {lp + 1} [expr {{$p >> 8}}]\n}}\n"
                 # created only when the probe first reaches ARM: before it, the PTR word is whatever boot left
                 # (the NMS 8250's start-up VDP writes were logged into random RAM over the capture)
                 f"set ::plog_armed_{port:02x} 0\n"
                 f"proc biosl_plogarm_{port:02x} {{}} {{\n"
                 f"  if {{$::plog_armed_{port:02x}}} {{ return }}\n"
                 f"  set ::plog_armed_{port:02x} 1\n"
                 f"  debug watchpoint create -type write_io -address 0x{port:02x} -command biosl_plog_{port:02x}\n}}\n"
                 f"debug set_bp {arm} {{}} biosl_plogarm_{port:02x}\n")
    if st["psglog"]:
        # $A0's last byte latched; every OUT $A1: (reg, byte, time in us as 3 bytes) at (lp), lp += 5
        lp, arm, skip = st["psglog"]
        snap += ("set ::psgl_reg 0\nset ::psgl_armed 0\n"
                 "proc biosl_psgsel {} { set ::psgl_reg $::wp_last_value }\n"
                 "proc biosl_psglog {} {\n"
                 f"  set p [expr {{[debug read memory {lp}] | ([debug read memory {lp + 1}] << 8)}}]\n"
                 f"  if {{$p == 0 || ({skip} >> ($::psgl_reg & 15)) & 1}} {{ return }}\n"
                 "  set t [expr {wide([machine_info time] * 1000000) & 0xFFFFFF}]\n"
                 "  set k 0\n"
                 "  foreach b [list $::psgl_reg $::wp_last_value [expr {$t & 255}] [expr {($t >> 8) & 255}] "
                 "[expr {$t >> 16}]] {\n"
                 "    debug write memory [expr {($p + $k) & 0xFFFF}] $b; incr k\n  }\n"
                 "  set p [expr {($p + 5) & 0xFFFF}]\n"
                 f"  debug write memory {lp} [expr {{$p & 255}}]\n"
                 f"  debug write memory {lp + 1} [expr {{$p >> 8}}]\n}}\n"
                 "proc biosl_psgarm {} {\n"
                 "  if {$::psgl_armed} { return }\n  set ::psgl_armed 1\n"
                 "  debug watchpoint create -type write_io -address 0xa0 -command biosl_psgsel\n"
                 "  debug watchpoint create -type write_io -address 0xa1 -command biosl_psglog\n}\n"
                 f"debug set_bp {arm} {{}} biosl_psgarm\n")
    for ci, (ca, cp) in enumerate(st["cpusnap"]):
        # get_active_cpu (openMSX's own script) reads the S1990's CPU-select bit; "z80" where there is no S1990
        snap += (f"proc biosl_cpusnap{ci} {{}} {{\n"
                 f"  set p [expr {{[debug read memory {cp}] | ([debug read memory {cp + 1}] << 8)}}]\n"
                 "  set c [expr {[get_active_cpu] eq \"r800\" ? 1 : 0}]\n"
                 "  set t [expr {wide([machine_info time] * 1000000) & 0xFFFFFFFF}]\n"
                 "  set k 0\n"
                 "  foreach b [list $c [expr {$t & 255}] [expr {($t >> 8) & 255}] [expr {($t >> 16) & 255}] "
                 "[expr {$t >> 24}]] {\n"
                 "    debug write memory [expr {($p + $k) & 0xFFFF}] $b; incr k\n  }\n"
                 "  set p [expr {($p + 5) & 0xFFFF}]\n"
                 f"  debug write memory {cp} [expr {{$p & 255}}]\n"
                 f"  debug write memory {cp + 1} [expr {{$p >> 8}}]\n}}\n"
                 f"debug set_bp {ca} {{}} biosl_cpusnap{ci}\n")
    if st["keyset"]:
        ka, kl = st["keyset"]
        snap += ("proc biosl_keyset {} {\n"
                 "  for {set r 0} {$r < 11} {incr r} {\n"
                 "    keymatrixup $r 0xff\n"
                 f"    set m [debug read memory [expr {{{kl} + $r}}]]\n"
                 "    if {$m != 0} { keymatrixdown $r $m }\n  }\n}\n"
                 f"debug set_bp {ka} {{}} biosl_keyset\n")
    if cpuinfo:
        # D-TRSPEC: the S1990's register 6 (bit 5: 1 = Z80, bit 6: 1 = ROM mode -- as openMSX models it) sampled at
        # every poll (0.1 s of emulated time); each change is appended as TIME:VALUE. A debugger read of the device's
        # register, as for the VDP: no ROM byte, no side effect
        keys += ("  if {![catch {debug read {S1990 regs} 6} r6] && $r6 != $::r6last} {\n"
                 "    set ::r6last $r6; append ::r6hist [format { %.1f:%02X} [machine_info time] $r6]\n  }\n")
    tcl = ("set throttle off\nset ::typed 0\nset ::r6last -1\nset ::r6hist {}\n" + tape + at + snap +
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
           + ('    if {$::notape} { puts $f "TAPE no cassette port ([join [split $::tapeerr \\n] { }])" }\n'
              if st["tape"] else "") +
           '    puts $f "SYS jiffy=$j typed=$::typed scncnt=$sc newkey=$nk hkeyi,htimi=$hk' +
           (' cpu=[get_active_cpu] t=[format %.3f [machine_info time]] fcb1=[debug read memory 0xFCB1]'
            ' s1990r6=[string trim $::r6hist]' if cpuinfo else '') + '"\n' + vram +
           "    close $f\n    exit\n  }\n"
           "  after time 0.1 biosl_poll\n}\n"
           + ("after time 0.1 biosl_poll\n" if cpuinfo else "after time 1 biosl_poll\n"))
    script = os.path.join(td, machine + ".tcl")
    open(script, "w").write(tcl)
    media = []
    if disk and st["disk"]:
        src = os.path.join(REPO, "disk", "empty720.dsk")
        if st["disk"] != "empty":           # @disk PATH: an image the probe's own script built
            src = os.path.join(REPO, os.path.expandvars(st["disk"]))
            if not os.path.isfile(src):
                sys.exit(f"@disk {st['disk']}: {src} is missing")
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
    for conn, dev in st["plug"]:            # @plug: a device in a connector from boot (D-MSX2SPEC)
        plug += f"; plug {conn} {dev}"
    subprocess.run(omsx_preflight.guarded(
        [openmsx_paths.find_openmsx_binary(), "-machine", machine, "-cart", rom] + media +
        ["-command", "set renderer none; set sound_driver null" + plug, "-script", script]),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
    if media and os.environ.get("BIOSL_KEEP_DSK"):
        os.makedirs(os.environ["BIOSL_KEEP_DSK"], exist_ok=True)
        shutil.copyfile(media[1], os.path.join(os.environ["BIOSL_KEEP_DSK"], machine + ".dsk"))
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
    ap.add_argument("--row", choices=("nodisk", "disk", "both", "cf3300", "nms8250", "msx2eu", "msx2jp", "msx2p", "msx2all",
                                      "turbor"),
                    default="both")
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
        for row in ({"both": ("nodisk", "disk"), "msx2all": ("msx2eu", "msx2jp", "msx2p")}.get(a.row) or (a.row,)):
            ref_m, zb_m = ROWS[row]
            tr = row == "turbor"
            ref = run(ref_m, rom, st, td, disk=(row != "nodisk"), cpuinfo=tr)
            # C-BIOS's MSX2 / MSX2+ machines have no disk drive (Joost: "c-bios in any form doesn't have disk yet");
            # openMSX refuses -diska there, which left the side with NO READING (D-MSX2SPEC, the BLT disk calls)
            zb = run(zb_m, rom, st, td, disk=(row != "nodisk" and not row.startswith("msx2")), cpuinfo=tr)
            print(f"===== {a.rung} {row}: {ref_m} vs {zb_m} =====")
            for n, g in (("ref ", ref), ("ours", zb)):     # @tape on a machine without a cassette port (D-TRSPEC)
                if g and g.get("TAPE"):
                    print(f"  TAPE {n}: {g['TAPE']} -- nothing recorded or played; TAPEREADY acknowledged with 2")
            if tr:
                print("  (turbor: two REFERENCES -- 'ref' = FS-A1GT, 'ours' = FS-A1ST; a DIFF is where they disagree)")
            bad = [n for n, g in (("ref", ref), ("ours", zb))
                   if not g or g.get("DONE") != "165"]
            if bad:
                print(f"  NO READING: DONE never set on {', '.join(bad)} "
                      f"(ref {ref and ref.get('DONE')}, ours {zb and zb.get('DONE')})")
                rc = max(rc, 2)
                # the side that DID finish still prints its capture: D-MSX1ON2 compares an MSX2 reference's
                # reading against the VG-8020's even where C-BIOS's MSX2 build has no disk ROM to finish with
                if not (ref and zb):
                    for n, g in (("ref ", ref), ("ours", zb)):
                        if g and g.get("DONE") == "165" and g.get("CAP"):
                            print(f"  CAP {n}: {g['CAP']}")
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
            if tr:
                for i in range(len(st["vram"])):
                    print(f"  VRAM{i} ref : {ref[f'VRAM{i}']}\n  VRAM{i} ours: {zb[f'VRAM{i}']}")
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
