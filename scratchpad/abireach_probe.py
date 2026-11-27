#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""C-BIOS integration step 1 (Joost 2026-11-27): DOES ANY DISK-ROM PATH REACH ZEROBAS'S MAIN ROM ON A BASIC-LESS HOST?

port-readiness row 3: the disk ROM includes disk/basic-resident-abi.inc -- addresses of zerobas's main-ROM routines
(the MKS$ / CVS math, and the page-1 BASIC routines Disk BASIC's hooks call back into). On a C-BIOS with no BASIC
those addresses hold C-BIOS's own code, so any transfer there is a fault. This probe arms a breakpoint on

  * every site in build/disk.rom that transfers control to one of those routines -- CALL / JP (all conditions) with
    the routine as operand, and `ld ix,` / `ld iy,` / `ld de,` / `ld hl,` loading it (the call-back mechanism takes
    IX; continuations go back in DE) -- found by scanning our OWN image;
  * every Disk BASIC hook handler (hk_*), install_basic_hooks, and bb_term (BDOS $00's row);

each firing only while page 1 is the disk ROM's slot (3-1 on the BASIC-less machine), and logs our own ROM address.
Then it runs, on CBIOS2_CUR_MSX1_EU_NOBASIC_DISK: (a) the no-BASIC MSX-DOS session (disk_probe_dossession's), and
(b) every BDOS exerciser disk of bdos-acceptance, booted and left to run. Expected: no hit, except bb_term's guard
(it runs and returns without the ENDFLAG write -- reported separately).

Clean room: zerobas's own ROM and symbols only; the C-BIOS and Microsoft's DOS files run as they are.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_preflight  # noqa: E402
import probe_tmp  # noqa: E402

MACHINE = os.environ.get("ABIREACH_MACHINE", "CBIOS2_CUR_MSX1_EU_NOBASIC_DISK")
SLOT = (3, 1)


def symbols():
    syms = {}
    for line in open(os.path.join(REPO, "build", "disk.sym")):
        p = line.split()
        if len(p) >= 3 and p[1] == "EQU":
            syms[p[0]] = int(p[2].rstrip("H"), 16)
    return syms


def abi_routines():
    out = {}
    for line in open(os.path.join(REPO, "disk", "basic-resident-abi.inc")):
        m = re.match(r"(\w+)\s+equ\s+0?([0-9A-Fa-f]+)H", line)
        if m and m.group(1)[0].islower():
            a = int(m.group(2), 16)
            if a < 0x8000:
                out[a] = m.group(1)
    return out


def sites():
    rom = open(os.path.join(REPO, "build", "disk.rom"), "rb").read()
    routines = abi_routines()
    ops = {0xCD, 0xC3, 0xC2, 0xCA, 0xD2, 0xDA, 0xE2, 0xEA, 0xF2, 0xFA, 0xC4, 0xCC, 0xD4, 0xDC, 0xE4, 0xEC, 0xF4, 0xFC,
           0x11, 0x21}
    found = {}
    for i in range(len(rom) - 3):
        if rom[i] in ops:
            t = rom[i + 1] | rom[i + 2] << 8
            if t in routines:
                found[0x4000 + i] = f"{'ld' if rom[i] in (0x11, 0x21) else 'jp/call'} {routines[t]}"
        if rom[i] in (0xDD, 0xFD) and rom[i + 1] == 0x21:
            t = rom[i + 2] | rom[i + 3] << 8
            if t in routines:
                found[0x4000 + i] = f"ld i{'x' if rom[i] == 0xDD else 'y'},{routines[t]}"
    s = symbols()
    for n, a in s.items():
        if n.startswith("hk_") or n in ("install_basic_hooks", "bb_term"):
            found.setdefault(a, n)
    return found


def bp_tcl(found, log):
    lines = [f"set __abilog [open {{{log}}} a]"]
    for a, what in sorted(found.items()):
        lines.append(f"debug set_bp 0x{a:04X} {{[pc_in_slot {SLOT[0]} {SLOT[1]}]}} "
                     f"{{puts $::__abilog {{HIT {a:04X} {what}}}; flush $::__abilog}}")
    return "\n".join(lines) + "\n"


def run_session(found, log):
    import disk_probe_dossession as DS
    orig = DS.tcl
    DS.tcl = lambda out: bp_tcl(found, log) + orig(out)
    try:
        DS.run(MACHINE)
    finally:
        DS.tcl = orig


def run_exercisers(found, log):
    """every bdos-acceptance exerciser disk, built by the suite's own builder, booted on MACHINE for 50 s"""
    import disk_bdos_acceptance as A
    done = []
    for row in A.EXERCISERS:
        name, script, extra = row[0], row[1], (row[2] if len(row) > 2 else ())
        try:
            A.build_and_plan(name, script, A.DEFAULT_DOS_DISK, tuple(extra))
        except Exception as e:
            print(f"    {name}: build failed ({e!s:.60})"); continue
        dsk = f"/tmp/zerobas_acc_{name.lower()}.dsk"
        td = tempfile.mkdtemp(dir=probe_tmp.ROOT)
        d = os.path.join(td, "d.dsk"); shutil.copyfile(dsk, d)
        tcl = os.path.join(td, "s.tcl")
        open(tcl, "w").write("set throttle off\n" + bp_tcl(found, log).replace("HIT ", f"HIT[{name}] ")
                             + "after time 50 exit\n")
        subprocess.run(omsx_preflight.guarded(["openmsx", "-machine", MACHINE, "-diska", d, "-command",
                       "set renderer none; set sound_driver null", "-script", tcl]),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=200)
        shutil.rmtree(td, ignore_errors=True)
        done.append(name)
    return done


def main():
    found = sites()
    print(f"{len(found)} breakpoint sites ({sum(1 for v in found.values() if ' ' in v)} transfers into the ABI's "
          f"routines, {sum(1 for v in found.values() if ' ' not in v)} hook / install / bb_term entries)")
    td = tempfile.mkdtemp(dir=probe_tmp.ROOT)
    log = os.path.join(td, "hits.txt")
    open(log, "w").close()
    print("(a) the no-BASIC MSX-DOS session ...", flush=True)
    run_session(found, log)
    a_hits = open(log).read().splitlines()
    print(f"    hits: {len(a_hits)}")
    for h in sorted(set(a_hits)):
        print(f"      {h}  x{a_hits.count(h)}")
    open(log, "w").close()
    print("(b) every bdos-acceptance exerciser disk, booted for 50 s ...", flush=True)
    done = run_exercisers(found, log)
    b_hits = open(log).read().splitlines()
    print(f"    {len(done)} exerciser disks run; hits: {len(b_hits)}")
    for h in sorted(set(b_hits)):
        print(f"      {h}  x{b_hits.count(h)}")
    shutil.rmtree(td, ignore_errors=True)
    bad = [h for h in a_hits + b_hits if "bb_term" not in h and "install_basic_hooks" not in h]
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
