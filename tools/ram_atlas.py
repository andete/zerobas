#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-RAMATLAS: a MEASURED atlas of high RAM ($D000-$FFFF) -- who writes each range, at which moment, on which
machine -- rendered to docs/ram-atlas.md, so the knowledge every RAM decision rests on is a generated page and not a
reading that rots (Joost 2026-11-25: "eventually we'd have to build up even more knowledge about these ram areas").

    python3 -u tools/ram_atlas.py --run [MACHINE_TAG ...]   boot each machine / scenario, write scratchpad/ramatlas.json
    python3 tools/ram_atlas.py --render                     docs/ram-atlas.md from the JSON + tools/ram_map.py
    python3 -u tools/ram_atlas.py --check                   the gate (ramatlas-acceptance): zerobas's runs re-measured
                                                            on this build must equal the JSON's, and the page must be
                                                            what --render writes. The references' columns are not
                                                            re-run (they are facts of fixed machines).

HOW. One openMSX run per (machine, scenario) with ONE write watchpoint over the range. Per written address the run
keeps the set of (moment, writer) pairs. The MOMENT is told by RAM events only:
  0 boot      from power-on
  1 INIT      from the first write of HIMEM ($FC4A) below $F380 -- a cartridge's claim
  2 H.RUNC    from an execution of the H.RUNC hook ($FECB, RAM) while HIMEM is below $F380
  3 MSX-DOS   from the first execution of $0100 in RAM after 1 s
  4 BASIC     from the scenario's own marker -- the keystroke that hands over to (Disk) BASIC
The WRITER is the page and slot the writing code runs in ("1@3-1": page 1, slot 3-1), derived inside the callback;
the program counter itself is never recorded.

CLEAN ROOM (docs/clean-room-audit.md): on a reference only the address written, the moment and the writer's
page@slot are kept. NO VALUE IS READ -- this tool reads none on any machine, so the RAM-resident code a reference keeps
in this range (the disk ROM's work area holds some) is never seen. Classes that need values (published cells'
contents) come from the published-cell probes (scratchpad/memboot_probe.py, sysdata_diff.py), not from here.
"""
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import omsx_preflight  # noqa: E402
import openmsx_paths  # noqa: E402
import probe_tmp  # noqa: E402

LO, HI = 0xD000, 0xFFFF
JSON = os.path.join(ROOT, "scratchpad", "ramatlas.json")
DOC = os.path.join(ROOT, "docs", "ram-atlas.md")
DOSDISK = os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")
DATADISK = os.path.join(ROOT, "disk", "test720.dsk")
MOMENTS = ["boot", "INIT", "H.RUNC", "MSX-DOS", "BASIC"]

# (tag, machine, extension, is a reference)
MACHINES = [
    ("VG", "Philips_VG_8020", None, True),
    ("VGHBD", "Philips_VG_8020", "Sony_HBD-F1", True),
    ("CF", "National_CF-3300", None, True),
    ("ZBND", "C-BIOS_MSX1_EU_REPACK_NODISK", None, False),
    ("ZBD", "C-BIOS_MSX1_EU_REPACK_DISK", None, False),
]
DISKLESS = {"VG", "ZBND"}
PROG = r'10 A$=STRING$(50,65):B$=A$+A$:DIM C(20):FOR I=1 TO 20:C(I)=I:NEXT:GOSUB 30\r20 END\r30 RETURN\rRUN\r'
FILEOPS = r'OPEN"Y.TXT"FOR OUTPUT AS 1:PRINT#1,"A":CLOSE\rFILES\r'
# scenario: (disk, seconds, [(time, keys)], the time of the BASIC marker or None)
SCENARIOS = {
    "dos": (DOSDISK, 70, [(16, r"\r"), (21, r"DIR MSXDOS.SYS\r"), (26, r"COPY MSXDOS.SYS X.SYS\r"),
                          (32, r"BASIC\r"), (44, FILEOPS), (52, PROG)], 32),
    "basic": (DATADISK, 45, [(10, r"\r"), (16, FILEOPS), (24, PROG)], 10),
    "plain": (None, 30, [(10, PROG)], 8),
}


def scenarios_for(tag):
    return ["plain"] if tag in DISKLESS else ["dos", "basic"]


TCL = r"""
set renderer none
set throttle off
catch { set sound_driver null }
set ::m 0
set ::seen [dict create]
proc slotof {pg} { lassign [get_selected_slot $pg] ps ss; if {$ss eq "X"} {return "$ps"} ; return "$ps-$ss" }
proc himem {} { expr {[debug read memory 0xFC4A] + 256 * [debug read memory 0xFC4B]} }
proc on_w {} {
  set a $::wp_last_address
  set pg [expr {[reg pc] >> 14}]
  dict set ::seen "$a $::m $pg@[slotof $pg]" 1
  if {$::m == 0 && ($a == 0xFC4A || $a == 0xFC4B) && [machine_info time] > 0.5} {
    if {[himem] < 0xF380 && [himem] > 0x8000} { set ::m 1 }
  }
}
proc on_hrunc {} { if {$::m >= 1 && $::m < 2 && [himem] < 0xF380} { set ::m 2 } }
proc on_dos {} { if {$::m < 3 && [machine_info time] > 1.0} { set ::m 3 } }
debug set_watchpoint write_mem {@LO@ @HI@} {} on_w
debug set_bp 0xFECB {} on_hrunc
proc page0_is_ram {} { expr {[slotof 0] ni {0 0-0}} }    ;# the main ROM is slot 0 / 0-0 on an MSX1
debug set_bp 0x0100 {[page0_is_ram]} on_dos
@KEYS@
after time @MARK@ { set ::m 4 }
after time @SECS@ {
  set f [open $::env(LOGF) w]
  foreach k [dict keys $::seen] { puts $f $k }
  close $f
  exit
}
"""


def run_one(tag, machine, ext, scen):
    disk, secs, keys, mark = SCENARIOS[scen]
    keytcl = "\n".join(f'after time {t} {{ type "{k}" }}' for t, k in keys)
    tcl = TCL.replace("@LO@", f"0x{LO:04X}").replace("@HI@", f"0x{HI:04X}").replace("@KEYS@", keytcl)
    tcl = tcl.replace("@MARK@", str(mark if mark else secs + 1)).replace("@SECS@", str(secs))
    path = probe_tmp.tmp(f"ramatlas_{tag}_{scen}.tcl")
    open(path, "w").write(tcl)
    log = probe_tmp.tmp(f"ramatlas_{tag}_{scen}.log")
    if os.path.exists(log):
        os.unlink(log)
    cmd = [openmsx_paths.find_openmsx_binary(), "-machine", machine] + (["-ext", ext] if ext else [])
    if disk:
        dsk = probe_tmp.tmp(f"ramatlas_{tag}_{scen}.dsk")
        shutil.copyfile(disk, dsk)
        cmd += ["-diska", dsk]
    cmd += ["-script", path]
    subprocess.run(omsx_preflight.guarded(cmd), env=dict(os.environ, LOGF=log), stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=1800)
    if not os.path.exists(log):
        raise SystemExit(f"ram_atlas: NO READING from {tag} {scen} -- refusing to write a partial atlas")
    out = {}
    for ln in open(log):
        a, m, w = ln.split()
        out.setdefault(int(a), set()).add(f"{MOMENTS[int(m)]}:{w}")
    return out


def pack(run):
    """{addr: [entries]} -> [[first, last, [entries]], ...]: runs of addresses with the same entries (the JSON form)."""
    out = []
    for a in sorted(run):
        if out and out[-1][1] == a - 1 and out[-1][2] == run[a]:
            out[-1][1] = a
        else:
            out.append([a, a, run[a]])
    return out


def unpack(packed):
    return {a: e for first, last, e in packed for a in range(first, last + 1)}


def load():
    return {k: unpack(v) for k, v in json.load(open(JSON)).items()} if os.path.exists(JSON) else {}


def save(data):
    with open(JSON, "w") as f:
        json.dump({k: pack(v) for k, v in sorted(data.items())}, f, separators=(",", ":"))
        f.write("\n")


def do_run(tags):
    data = load()
    for tag, machine, ext, _ in MACHINES:
        if tags and tag not in tags:
            continue
        for scen in scenarios_for(tag):
            got = run_one(tag, machine, ext, scen)
            data[f"{tag}/{scen}"] = {a: sorted(v) for a, v in got.items()}
            print(f"{tag:6s} {scen:6s} {len(got):6d} addresses written in ${LO:04X}-${HI:04X}", flush=True)
    save(data)


def do_check():
    """Red when zerobas's writes in high RAM changed since the atlas was measured, or the page is stale: either way
    the atlas no longer describes this build -- re-run `--run ZBND ZBD` and `--render`, and READ the diff."""
    import ram_atlas_render
    data = load()
    bad = []
    for tag, machine, ext, ref in MACHINES:
        if ref:
            continue
        for scen in scenarios_for(tag):
            got = {a: sorted(v) for a, v in run_one(tag, machine, ext, scen).items()}
            old = data.get(f"{tag}/{scen}")
            if got != old:
                ga, oa = set(got), set(old or {})
                ch = sorted(a for a in ga & oa if got[a] != old[a])
                bad.append(f"{tag}/{scen}: {len(ga - oa)} address(es) newly written, {len(oa - ga)} no longer, "
                           f"{len(ch)} written at other moments / by other code"
                           + (f" -- e.g. ${sorted(ga ^ oa or set(ch))[0]:04X}" if ga ^ oa or ch else ""))
            else:
                print(f"  {tag}/{scen}: as measured ({len(got)} addresses)")
    tmp = probe_tmp.tmp("ram-atlas.md")
    ram_atlas_render.render(JSON, tmp)
    if open(tmp).read() != open(DOC).read():
        bad.append("docs/ram-atlas.md is not what --render writes from the JSON")
    for b in bad:
        print("🔴 " + b)
    print("ram-atlas: " + ("RED -- re-run `python3 -u tools/ram_atlas.py --run ZBND ZBD` and `--render`, then read the "
                           "page's diff" if bad else "the atlas describes this build"))
    return 1 if bad else 0


def main(argv):
    if "--check" in argv:
        return do_check()
    if "--run" in argv:
        do_run([a for a in argv[1:] if not a.startswith("--")])
        return 0
    if "--render" in argv:
        import ram_atlas_render
        return ram_atlas_render.render(JSON, DOC)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
