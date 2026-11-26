#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""Cartridge survey (Joost 2026-11-26): HOW REAL CARTRIDGES RESERVE RAM, and whether zerobas keeps it.

For each extension (openMSX's own configs; the ROMs the user placed in ~/.openMSX/share/systemroms) and for no
cartridge, the CF-3300 and zerobas's DISK machine boot with NO disk; at the BASIC prompt (25 s) the published
cells are read: HIMEM, BOTTOM, TXTTAB, MEMSIZ, STKTOP, every non-zero SLTWRK entry, DRVCNT ($F347 -- did the disk
ROM install?), and the screen's last non-blank rows. Clean room: RAM cells and the screen only; the cartridges' own
ROMs run as they are and are never read.
"""
import os, shutil, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_preflight, probe_tmp  # noqa: E402
MACHINES = (("CF", "National_CF-3300"), ("ZB", "C-BIOS_MSX1_EU_REPACK_DISK"))
EXTS = [a for a in sys.argv[1:] if not a.startswith("+")] or [None, "fmpac", "Checkmark_FM_Stereo_PAK", "Sanyo_MRS-001"]
TYPE = next((a[1:] for a in sys.argv[1:] if a.startswith("+")), "")   # `+CALL MUSIC`: typed at 30 s, read at 45 s
AT = 45 if TYPE else 40
DISK = os.path.join(REPO, "disk", "test720.dsk")


def run(machine, ext):
    td = tempfile.mkdtemp(dir=probe_tmp.ROOT)
    out = os.path.join(td, "o.txt"); dsk = os.path.join(td, "d.dsk"); shutil.copyfile(DISK, dsk)
    tcl = os.path.join(td, "s.tcl")
    open(tcl, "w").write(f"""set throttle off
proc w {{a}} {{ return [format %04X [expr {{[debug read memory $a] + 256*[debug read memory [expr {{$a+1}}]]}}]] }}
{"after time 30 {type {" + TYPE + "\\r}}" if TYPE else ""}
after time {AT} {{
  set f [open {{{out}}} w]
  set s ""
  for {{set i 0}} {{$i < 64}} {{incr i}} {{ set a [expr {{0xFD09 + 2*$i}}]
     if {{[w $a] ne "0000"}} {{ set p [expr {{$i/16}}]; set q [expr {{($i/4)%4}}]; set g [expr {{$i%4}}]; append s "$p-$q/p$g:[w $a] " }} }}
  puts $f "HIMEM=[w 0xFC4A] BOTTOM=[w 0xFC48] TXTTAB=[w 0xF676] MEMSIZ=[w 0xF672] STKTOP=[w 0xF674] DRVCNT=[debug read memory 0xF347] SLTWRK=\\[$s\\]"
  binary scan [debug read_block VRAM 0 960] H* v
  puts $f "VRAM $v"
  close $f; exit }}
""")
    # NO disk: both machines at the BASIC prompt, the disk ROM installed (a DOS disk boots MSX-DOS instead --
    # the first run, scratchpad/AE_cartsurvey1.out, read MSX-DOS's date prompt)
    cmd = ["openmsx", "-machine", machine, "-command", "set renderer none; set sound_driver null", "-script", tcl]
    if ext:
        cmd[3:3] = ["-ext", ext]
    p = subprocess.run(omsx_preflight.guarded(cmd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180, text=True)
    err = [l for l in p.stdout.splitlines() if any(k in l.lower() for k in ("error", "warning", "couldn't", "not found", "mismatch"))]
    res = "NO READING"
    if os.path.exists(out):
        L = open(out).read().splitlines()
        res = L[0]
        v = bytes.fromhex(L[1].split()[1])
        rows = [v[i:i + 40].decode("latin1") for i in range(0, 960, 40)]
        rows = [" ".join(r.split()) for r in rows if r.strip() and all(32 <= ord(c) < 127 or c == " " for c in r.strip())]
        res += f"  screen={rows[-3:]}"
    shutil.rmtree(td, ignore_errors=True)
    return res, err[:3]


for ext in EXTS:
    for side, m in MACHINES:
        r, e = run(m, ext)
        print(f"{ext or '(none)':24s} {side}: {r}" + (f"\n{'':28s}openMSX: {e}" if e else ""))
        sys.stdout.flush()
