#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-DISKROMHOST step 4(d): does the disk ROM's INIT guard decline when a cartridge claimed RAM before it?

probes/disk/claimer.asm is a test cartridge whose INIT lowers HIMEM by 16 bytes, as a cartridge with its own work
area does; in an external slot it is scanned BEFORE the disk ROM. Each machine boots with and without it, a blank
720 KB disk in drive A, and reads at the prompt: the drive count ($FB21, published), HIMEM ($FC4A, published) and
DSKF(0) (does Disk BASIC answer?).

Expected (the guard, Joost 2026-11-25 "guard first"): zerobas's DISK machine WITH the claimer declines -- drive count
0, HIMEM the claimer's $F370, DSKF not a disk statement -- and WITHOUT it boots as always; the CF-3300 works in both
(its work area is addressed from the base it claimed: the later step for zerobas).

Clean room: typed BASIC in, the screen out; only published cells.

    python3 -u probes/disk/disk_probe_guard.py      (gate: diskguard-acceptance)

Exit 0 when every row reads as expected, 1 otherwise."""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl  # noqa: E402
import probe_tmp  # noqa: E402

LINES = ["PRINT PEEK(&HFB21)", "PRINT HEX$(PEEK(&HFC4A)+256*PEEK(&HFC4B))", "PRINT DSKF(0)"]
MACHINES = (("zb", "C-BIOS_MSX1_EU_REPACK_DISK"), ("cf", "National_CF-3300"))


def cart():
    src = os.path.join(HERE, "claimer.asm")
    out = probe_tmp.tmp("claimer.bin")
    subprocess.run(["pasmo", "--bin", src, out], check=True, capture_output=True)
    b = open(out, "rb").read()
    rom = probe_tmp.tmp("claimer.rom")
    open(rom, "wb").write(b + bytes(16384 - len(b)))
    return rom


def rows(raw):
    if raw is None:
        return ["<NO OUTPUT>"]
    raw = raw.replace("\r", "").replace("\n", "")
    return [r.strip() for r in (raw[i:i + 40] for i in range(0, len(raw), 40)) if r.strip()]


def main():
    rom = cart()
    dsk = probe_tmp.tmp("guard.dsk")
    got = {}
    shutil.copyfile(os.path.join(ROOT, "disk", "test720.dsk"), dsk)
    for who, m in MACHINES:
        for label, c in (("no cartridge", None), ("with the claimer", rom)):
            raw = omsx_repl.run_cases(m, [("direct", ["CLS"] + LINES)], batch=False, cart=c, diska=dsk,
                                     reset=("", "SCREEN 0"), boot=14.0)  # "": the CF-3300's date question
            r = rows(raw[0])
            print(f"{who} {label:17s} " + " | ".join(r), flush=True)
            got[(who, c is not None)] = r
    bad = []
    for (who, claimed), r in got.items():
        drives = r[r.index("PRINT PEEK(&HFB21)") + 1] if "PRINT PEEK(&HFB21)" in r else None
        declined = who == "zb" and claimed           # only zerobas + the claimer declines (the guard)
        want = "0" if declined else "2"
        dskf_ok = any(x == "706" for x in r)
        if drives != want or dskf_ok == declined:
            bad.append(f"{who} {'with' if claimed else 'without'} the claimer: drives {drives!r} (want {want}), "
                       f"DSKF answered {dskf_ok}")
    for b in bad:
        print("FAIL", b)
    print("diskguard:", "RED" if bad else "GREEN")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
