#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-DISKROMHOST step 4 (a), zerobas's side: which bytes of the RAM the disk ROM's INIT claims ($F195-$F37F, the
CF-3300's HIMEM after INIT up to the system area) does zerobas's DISK machine actually WRITE -- from power-on through
(run "dos") an MSX-DOS session and BASIC typed at A> with a file written, or (run "basic") Disk BASIC from a data disk
with a file written. Per address: the first write's time, the writer's page@slot and zerobas's OWN PC there (our
machine only: no reference is run by this probe). A byte nothing writes is a candidate for HOOK_SLOT; the RAM map's
gaps are not proof (tools/ram_map.py: "a delta between two names is NOT free space").

    python3 -u scratchpad/claimuse_probe.py > scratchpad/AE_claimuse_zb.out 2>&1
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_preflight  # noqa: E402
import probe_tmp  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "tools"))
import openmsx_paths  # noqa: E402

MACHINE = os.environ.get("CLAIMUSE_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
LO, HI = 0xF195, 0xF37F
RUNS = {
    "dos": (os.path.expanduser("~/Documents/msx/msx/disks/test.dsk"), 70,
            [(16, r"\r"), (21, r"DIR MSXDOS.SYS\r"), (26, r"COPY MSXDOS.SYS X.SYS\r"), (32, r"BASIC\r"),
             (44, r'OPEN"Y.TXT"FOR OUTPUT AS 1:PRINT#1,"A":CLOSE\r'), (52, r'FILES\r'), (58, r'PRINT FRE(0)\r')]),
    "basic": (os.path.join(ROOT, "disk", "test720.dsk"), 40,
              [(10, r"\r"), (16, r'OPEN"Y.TXT"FOR OUTPUT AS 1:PRINT#1,"A":CLOSE\r'), (24, r'FILES\r'),
               (30, r'PRINT FRE(0)\r')]),
}

TCL = r"""
set renderer none
set throttle off
catch { set sound_driver null }
set ::seen [dict create]
proc slotof {pg} { lassign [get_selected_slot $pg] ps ss; if {$ss eq "X"} {return "$ps"} ; return "$ps-$ss" }
proc on_w {} {
  set a $::wp_last_address
  if {![dict exists $::seen $a]} {
    set pc [reg pc]
    dict set ::seen $a [list [format %.4f [machine_info time]] "[expr {$pc >> 14}]@[slotof [expr {$pc >> 14}]]" [format %04X $pc]]
  }
}
debug set_watchpoint write_mem {LO HI} {} on_w
KEYS
after time SECS {
  set f [open $::env(LOGF) w]
  foreach a [lsort -integer [dict keys $::seen]] { puts $f "[format %04X $a] [dict get $::seen $a]" }
  close $f
  exit
}
"""


def ranges(addrs):
    out, start, prev = [], None, None
    for a in addrs:
        if start is None:
            start = prev = a
        elif a == prev + 1:
            prev = a
        else:
            out.append((start, prev))
            start = prev = a
    if start is not None:
        out.append((start, prev))
    return out


def syms():
    s = {}
    for f in ("disk.sym", "basic-reloc.sym"):
        p = os.path.join(ROOT, "build", f)
        if os.path.exists(p):
            for ln in open(p):
                parts = ln.split()
                if len(parts) >= 3 and parts[1] == "EQU":
                    s.setdefault(f, []).append((int(parts[2].rstrip("H"), 16), parts[0]))
    return {k: sorted(v) for k, v in s.items()}


def name(table, pc):
    best = None
    for a, n in table:
        if a <= pc:
            best = (a, n)
        else:
            break
    return f"{best[1]}+{pc - best[0]}" if best else "?"


def main():
    tab = syms()
    used = set()
    for run, (disk, secs, keys) in RUNS.items():
        dsk = probe_tmp.tmp(f"claimuse_{run}.dsk")
        shutil.copyfile(disk, dsk)
        keytcl = "\n".join(f'after time {t} {{ type "{k}" }}' for t, k in keys)
        tcl = probe_tmp.tmp(f"claimuse_{run}.tcl")
        open(tcl, "w").write(TCL.replace("LO", f"0x{LO:04X}").replace("HI", f"0x{HI:04X}")
                             .replace("KEYS", keytcl).replace("SECS", str(secs)))
        log = probe_tmp.tmp(f"claimuse_{run}.log")
        if os.path.exists(log):
            os.unlink(log)
        cmd = [openmsx_paths.find_openmsx_binary(), "-machine", MACHINE, "-diska", dsk, "-script", tcl]
        subprocess.run(omsx_preflight.guarded(cmd), env=dict(os.environ, LOGF=log), stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=600)
        rows = [ln.split() for ln in open(log)] if os.path.exists(log) else []
        print(f"## run {run}: {MACHINE}, {os.path.basename(disk)}, {secs} s -- {len(rows)} distinct addresses written "
              f"in ${LO:04X}-${HI:04X}")
        first = {int(r[0], 16): r for r in rows}
        used |= set(first)
        for s, e in ranges(sorted(first)):
            r = first[s]
            pc = int(r[3], 16)
            t = tab.get("disk.sym" if r[2].endswith("@3-1") else "basic-reloc.sym", [])   # the disk ROM: slot 3-1
            print(f"  ${s:04X}-${e:04X} {e - s + 1:4d} B  first {float(r[1]):8.3f} s by {r[2]} {name(t, pc)}")
    free = [a for a in range(LO, HI + 1) if a not in used]
    print(f"## never written in either run: {len(free)} B")
    for s, e in ranges(free):
        print(f"  ${s:04X}-${e:04X} {e - s + 1:4d} B")


if __name__ == "__main__":
    main()
