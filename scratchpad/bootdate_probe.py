#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-BOOTDATE (from D-DISKRUN, 2026-10-21): a stock disk ROM's $4022, entered by a
boot loader that could not open MSXDOS.SYS, ASKS THE DATE and then starts BASIC.
What exactly does it accept, and what does the answer set? Measured on BOTH disk
references -- the European VG-8020 with a Philips NMS 1200 interface, and the
Japanese National CF-3300 -- and zerobas beside them.

Each case boots a fresh /tmp copy of a bootable disk with no system files
(DISKCORPUS_DIR's empty.dsk; the collection's location is never written here), and
at T20 reads the screen. If the date prompt is there, it types the case's ANSWER and
reads the screen at T26 (a re-prompt shows here). Then it types `10 REM` and
`SAVE"D.BAS"`, exits, and reads D.BAS's DIRECTORY DATE STAMP out of the /tmp image
afterwards -- what the answer actually set. Black box: keys in; screen, the
work-area CURLIN and our own disk image out.
    DISKCORPUS_DIR=... python3 -u scratchpad/bootdate_probe.py [eu,jp,zb]
"""
import os, shutil, struct, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import diskcorpus_run as D

MACHINES = {"eu": ("Philips_VG_8020", ["-ext", "Philips_NMS_1200"]),
            "jp": ("National_CF-3300", []),
            "zb": ("C-BIOS_MSX1_EU_REPACK_DISK", [])}
CASES = [("valid", "1-2-90"), ("empty", ""), ("month13", "13-2-90"),
         ("feb29", "2-29-91"), ("year2digit", "3-4-5"), ("junk", "XYZ")]


def stamp(dsk, name="D       BAS"):
    b = open(dsk, "rb").read()
    start = (1 + 2 * 3) * 512
    for i in range(112):
        e = b[start + 32 * i: start + 32 * i + 32]
        if e[0] == 0:
            break
        if e[0:11].decode("latin1") == name:
            t, d = struct.unpack_from("<HH", e, 22)
            return f"{1980 + (d >> 9):04d}-{(d >> 5) & 15:02d}-{d & 31:02d}"
    return None


def run(key, answer):
    machine, extra = MACHINES[key]
    td = tempfile.mkdtemp(prefix="bootdate_")
    dsk = os.path.join(td, "w.dsk")
    shutil.copy(os.path.join(os.environ["DISKCORPUS_DIR"], "empty.dsk"), dsk)
    out = os.path.join(td, "c.txt")
    def cap(tag):
        return (f'  set f [open {{{out}}} a]\n'
                '  binary scan [debug read_block VRAM 0 16384] H* v\n'
                '  set r {}\n'
                '  for {set i 0} {$i < 8} {incr i} { lappend r [vdpreg $i] }\n'
                '  binary scan [debug read_block memory 0xF41C 2] H* cl\n'
                f'  puts $f "{tag} [reg pc] $r $cl $v"\n'
                '  close $f\n')
    tcl = ("set throttle off\n"
           "after time 20 {\n" + cap("T20") + "}\n"
           f'after time 20.5 {{ type "{answer}\\r" }}\n'
           "after time 26 {\n" + cap("T26") + '  type "10 REM\\r"\n}\n'
           'after time 28 { type "SAVE\\"D.BAS\\"\\r" }\n'
           "after time 36 {\n" + cap("T36") + "  exit\n}\n")
    open(os.path.join(td, "s.tcl"), "w").write(tcl)
    subprocess.run(["/opt/homebrew/bin/openmsx", "-machine", machine] + extra +
                   ["-diska", dsk, "-command", "set renderer none; set sound_driver null",
                    "-script", os.path.join(td, "s.tcl")],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=150)
    caps = {}
    if os.path.exists(out):
        for ln in open(out):
            p = ln.split()
            caps[p[0]] = {"pc": int(p[1]), "regs": [int(x) for x in p[2:10]],
                          "curlin": int(p[10][2:4] + p[10][0:2], 16), "vram": bytes.fromhex(p[11])}
    st = stamp(dsk)
    shutil.rmtree(td, ignore_errors=True)
    return caps, st


def main():
    keys = (sys.argv[1] if len(sys.argv) > 1 else "eu,jp,zb").split(",")
    for lab, ans in CASES:
        for k in keys:
            caps, st = run(k, ans)
            t20 = " / ".join(D.screen_text(caps["T20"])[-2:]) if "T20" in caps else "<none>"
            t26 = " / ".join(D.screen_text(caps["T26"])[-3:]) if "T26" in caps else "<none>"
            print(f"{lab:10s} {k}  answer={ans!r:12s} stamp={st}\n"
                  f"     T20: {t20}\n     T26: {t26}", flush=True)
    print("done")


if __name__ == "__main__":
    main()
