#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-DISKRUN mb.dsk (gate: boot5e10-acceptance): a boot code that CALLs the disk
ROM's fixed $5E10 starts BASIC and runs AUTOEXEC.BAS, with no date question, as on
the VG-8020 + Philips NMS 1200 (Joost ruled 2026-10-27: "Start BASIC (NMS 1200)";
mb.dsk does this, scratchpad/mbtime_run.out). zerobas pins $5E10 to basent_body.

Our OWN disk: a copy of disk/test720.dsk whose boot code at $1E is `CALL $5E10 /
RET`, plus an ASCII AUTOEXEC.BAS `10 PRINT "AX";5`. It boots on both machines and
the screen is read at T15: the line `AX 5` must be there, and no date prompt.
Prints `ROW boot5e10 EU=[...] ZB=[...] <SAME|DIVERGES>`; exit 0 agree, 1 a
divergence, 2 the reference gave no reading. Black box: our own code and file in,
the screen out.
"""
import os, shutil, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import omsx_preflight                               # noqa: E402
from disk_probe_bdos import fat12_add               # noqa: E402  (reuse)
import diskcorpus_run as D                          # noqa: E402  (screen_text)

CODE = bytes([0xCD, 0x10, 0x5E,                     # CALL $5E10
              0xC9])                                # RET (the CF-3300 never returns)
MACHINES = {"EU": ("Philips_VG_8020", ["-ext", "Philips_NMS_1200"]),
            "ZB": ("C-BIOS_MSX1_EU_REPACK_DISK", [])}


def image(dst):
    shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dst)
    img = bytearray(open(dst, "rb").read())
    img[0x1E:0x1E + len(CODE)] = CODE
    fat12_add(img, "AUTOEXEC", "BAS", b'10 PRINT "AX";5\r\n\x1a')
    open(dst, "wb").write(img)


def run(key):
    machine, extra = MACHINES[key]
    td = tempfile.mkdtemp(prefix="b5e10_")
    dsk = os.path.join(td, "b.dsk")
    image(dsk)
    out = os.path.join(td, "c.txt")
    tcl = ["set throttle off", "after time 15 {", f"  set f [open {{{out}}} a]",
           "  binary scan [debug read_block VRAM 0 16384] H* v",
           "  set r {}", "  for {set i 0} {$i < 8} {incr i} { lappend r [vdpreg $i] }",
           "  binary scan [debug read_block memory 0xF41C 2] H* cl",
           '  puts $f "T15 [reg pc] $r $cl $v"', "  close $f", "  exit", "}"]
    open(os.path.join(td, "s.tcl"), "w").write("\n".join(tcl) + "\n")
    subprocess.run(omsx_preflight.guarded(["/opt/homebrew/bin/openmsx", "-machine", machine] + extra +
                   ["-diska", dsk, "-command", "set renderer none; set sound_driver null",
                    "-script", os.path.join(td, "s.tcl")]),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    txt = None
    if os.path.exists(out):
        p = open(out).read().split()
        cap = {"pc": int(p[1]), "regs": [int(x) for x in p[2:10]],
               "curlin": int(p[10][2:4] + p[10][0:2], 16), "vram": bytes.fromhex(p[11])}
        rows = [x.strip() for x in D.screen_text(cap) if x.strip()]
        ax = [x for x in rows if x.startswith("AX")]
        date = any("date" in x.lower() for x in rows)
        txt = f"{ax[0] if ax else 'no AX'}{' DATE-PROMPT' if date else ''}"
    shutil.rmtree(td, ignore_errors=True)
    return txt


def main():
    got = {k: run(k) for k in MACHINES}
    if got["EU"] is None:
        print(f"ROW boot5e10 EU=<none> ZB=[{got['ZB']}] NO-REFERENCE")
        return 2
    v = "SAME" if got["EU"] == got["ZB"] else "DIVERGES"
    print(f"ROW boot5e10 EU=[{got['EU']}] ZB=[{got['ZB']}] {v}")
    return 0 if v == "SAME" else 1


if __name__ == "__main__":
    sys.exit(main())
