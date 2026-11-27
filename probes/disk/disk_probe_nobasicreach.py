#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""nobasic-acceptance, reach half (C-BIOS integration steps 1 + 3, Joost 2026-11-27): ON A BASIC-LESS C-BIOS HOST,
NO DISK-ROM PATH REACHES ZEROBAS'S MAIN ROM.

The disk ROM includes disk/basic-resident-abi.inc -- addresses of zerobas's main-ROM routines (the MKS$ / CVS math,
the page-1 BASIC routines Disk BASIC's hooks call back into). On a C-BIOS with no BASIC those addresses hold C-BIOS's
own code, so any transfer there is a fault. This probe arms a breakpoint on

  * every site in build/disk.rom that transfers control to one of those routines -- CALL / JP (all conditions) with
    the routine as operand, and `ld ix,` / `ld iy,` / `ld de,` / `ld hl,` loading it (the call-back mechanism takes
    IX; continuations go back in DE) -- found by scanning our OWN image;
  * every Disk BASIC hook handler (hk_*), install_basic_hooks and bb_term (BDOS $00's row);

each firing only while page 1 is the disk ROM's slot (3-1), and runs on CBIOS2_CUR_MSX1_EU_NOBASIC_DISK (installed
from tools/cbios-nobasic.pin by the make target): (a) the no-BASIC MSX-DOS session (disk_probe_dossession's), and
(b) every BDOS exerciser disk of bdos-acceptance, booted and left to run 50 s.

Verdict: GREEN when no breakpoint fires except install_basic_hooks (it installs and returns -- the hooks are never
CALLED with no BASIC) and bb_term (its guard returns without the BASIC-only writes). Witnesses, per run, or it is an
INSTRUMENT FAULT (exit 2) and never green: install_basic_hooks fired (the arm is alive, the disk ROM booted) and
bdos_entry was reached (MSX-DOS ran through our BDOS). Also refused: fewer than MIN_TRANSFERS transfer sites found
(a degenerate scan), an exerciser disk that does not build.

Clean room: zerobas's own ROM and symbols only; the C-BIOS and Microsoft's DOS files run as they are. Promoted from
scratchpad/abireach_probe.py (AE_abireach2.out: 111 sites, 2 + 29 install-only hits).
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_preflight  # noqa: E402
import probe_tmp  # noqa: E402

MACHINE = os.environ.get("NOBASICREACH_MACHINE", "CBIOS2_CUR_MSX1_EU_NOBASIC_DISK")
SLOT = (3, 1)
ENTRIES = ("install_basic_hooks", "bb_term")     # armed (with every hk_*)
ALLOWED = ("install_basic_hooks", "bb_term")     # may fire; kept apart from ENTRIES so a knife narrowing it stays armed
MIN_TRANSFERS = 40      # 72 on 2026-11-27; a scan that finds a handful has misread the image or the ABI


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
        if n.startswith("hk_") or n in ENTRIES:
            found.setdefault(a, n)
    return found, s["bdos_entry"]


def bp_tcl(found, bdos, log, tag):
    lines = [f"set __abilog [open {{{log}}} a]", "set __bdosn 0"]
    for a, what in sorted(found.items()):
        lines.append(f"debug set_bp 0x{a:04X} {{[pc_in_slot {SLOT[0]} {SLOT[1]}]}} "
                     f"{{puts $::__abilog {{HIT[{tag}] {a:04X} {what}}}; flush $::__abilog}}")
    # the witness that MSX-DOS ran through our BDOS: one line, at the first entry
    lines.append(f"debug set_bp 0x{bdos:04X} {{[pc_in_slot {SLOT[0]} {SLOT[1]}]}} "
                 f"{{if {{[incr ::__bdosn] == 1}} {{puts $::__abilog {{BDOS[{tag}]}}; flush $::__abilog}}}}")
    return "\n".join(lines) + "\n"


def run_session(found, bdos, log):
    import disk_probe_dossession as DS
    orig = DS.tcl
    DS.tcl = lambda out: bp_tcl(found, bdos, log, "SESSION") + orig(out)
    try:
        DS.run(MACHINE)
    finally:
        DS.tcl = orig
    return ["SESSION"]


def run_exercisers(found, bdos, log):
    """every bdos-acceptance exerciser disk, built by the suite's own builder, booted on MACHINE for 50 s"""
    import disk_bdos_acceptance as A
    done, broken = [], []
    for row in A.EXERCISERS:
        name, script, extra = row[0], row[1], (row[2] if len(row) > 2 else ())
        try:
            A.build_and_plan(name, script, A.DEFAULT_DOS_DISK, tuple(extra))
        except Exception as e:
            print(f"    {name}: build failed ({e!s:.60})")
            broken.append(name)
            continue
        dsk = A.acc_dsk(name)
        td = tempfile.mkdtemp(dir=probe_tmp.ROOT)
        d = os.path.join(td, "d.dsk")
        shutil.copyfile(dsk, d)
        tcl = os.path.join(td, "s.tcl")
        open(tcl, "w").write("set throttle off\n" + bp_tcl(found, bdos, log, name) + "after time 50 exit\n")
        subprocess.run(omsx_preflight.guarded(["openmsx", "-machine", MACHINE, "-diska", d, "-command",
                       "set renderer none; set sound_driver null", "-script", tcl]),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=200)
        shutil.rmtree(td, ignore_errors=True)
        done.append(name)
    return done, broken


def main():
    found, bdos = sites()
    transfers = sum(1 for v in found.values() if " " in v)
    print(f"{len(found)} breakpoint sites ({transfers} transfers into the ABI's routines, "
          f"{len(found) - transfers} hook / install / bb_term entries); witness bdos_entry {bdos:04X}; on {MACHINE}")
    if transfers < MIN_TRANSFERS:
        print(f"nobasicreach: INSTRUMENT FAULT -- only {transfers} transfer sites (< {MIN_TRANSFERS}): the scan misread")
        return 2
    td = tempfile.mkdtemp(dir=probe_tmp.ROOT)
    log = os.path.join(td, "hits.txt")
    open(log, "w").close()
    try:
        print("(a) the no-BASIC MSX-DOS session ...", flush=True)
        runs = run_session(found, bdos, log)
        print("(b) every bdos-acceptance exerciser disk, booted for 50 s ...", flush=True)
        done, broken = run_exercisers(found, bdos, log)
        runs += done
        lines = open(log).read().splitlines()
    finally:
        shutil.rmtree(td, ignore_errors=True)
    hits = [ln for ln in lines if ln.startswith("HIT[")]
    tag = lambda ln: ln[ln.index("[") + 1:ln.index("]")]  # noqa: E731
    for h in sorted(set(hits)):
        print(f"    {h}  x{hits.count(h)}")
    bad = [h for h in hits if not any(h.endswith(" " + a) for a in ALLOWED)]
    no_install = [r for r in runs if not any(tag(h) == r and h.endswith(" install_basic_hooks") for h in hits)]
    no_bdos = [r for r in runs if f"BDOS[{r}]" not in lines]
    print(f"{len(runs)} runs; {len(hits)} hits; disallowed {len(bad)}; "
          f"no install witness {no_install or '-'}; no BDOS witness {no_bdos or '-'}; unbuilt {broken or '-'}")
    if bad:
        print("nobasicreach: RED -- a disk-ROM path reached the BASIC-only side on a BASIC-less host: "
              + ", ".join(sorted(set(bad))))
        return 1
    if no_install or no_bdos or broken:
        print("nobasicreach: INSTRUMENT FAULT -- a run without its witnesses (the arm or the boot did not happen)")
        return 2
    print(f"nobasicreach: GREEN -- {len(runs)} runs, every one booted our disk ROM and reached its BDOS; "
          f"only {' / '.join(ALLOWED)} fired")
    return 0


if __name__ == "__main__":
    sys.exit(main())
