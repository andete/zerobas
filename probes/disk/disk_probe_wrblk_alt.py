#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""S10.A's proof -- TWO FCBs written ALTERNATELY with BDOS $26 WRBLK persist as if
each had been written alone, on ours and on the stock CF-3300.

disk/docs/spec-diskcode-eviction.md §6.6bc: step 10 makes each BASIC disk
channel a record-size-1 MSX-DOS FCB moved by 256 B block transfers (S10.0,
measured). That needs the kernel's canonical WRBLK to hold NO state between
calls on different FCBs. Its header says it re-mounts, re-finds and re-positions
from the FCB every call; this proves it on the persisted artifact, which is the
only place a write can be checked (the BDOSX RAM gate is blind to disk writes --
disk_probe_wrblk_roundtrip.py's header).

The exerciser is probes/disk/wrblk_alt.asm: FMAKE ALT1/ALT2, RS = 1, four rounds
of 256 B WRBLKs alternating between them with fill bytes 11h..18h, FCLOSE both.
The verdict compares SIZE and CONTENT, followed through each file's own FAT
chain -- NOT cluster numbers: the stock allocator is tail-relative and ours is
lowest-free, an accepted cosmetic divergence (roundtrip's del_realloc case), and
two files growing in turn are exactly where the numbers interleave differently.

  ZEROBAS_BASIC_MACHINE=C-BIOS_MSX1_EU_REPACK_DISK \\
      python3 probes/disk/disk_probe_wrblk_alt.py
Exit 0 when both machines produce the expected two files; 1 otherwise.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

HERE_ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE_)
from disk_probe_bdos import fat12_add  # noqa: E402
import disk_probe_wrblk_roundtrip as RT  # noqa: E402  -- Fat12, the DOS disk
sys.path.insert(0, os.path.join(os.path.dirname(HERE_), "lib"))
import probe_tmp  # noqa: E402  -- the one temp root (temp-root-check)

HERE = os.path.dirname(os.path.abspath(__file__))
ASM = os.path.join(HERE, "wrblk_alt.asm")
EXPECT = {"ALT1": bytes(b for f in (0x11, 0x13, 0x15, 0x17) for b in [f] * 256),
          "ALT2": bytes(b for f in (0x12, 0x14, 0x16, 0x18) for b in [f] * 256)}


def assemble() -> bytes:
    com = probe_tmp.tmp("wrblk_alt.com")
    subprocess.run(["pasmo", "--bin", ASM, com, probe_tmp.tmp("wrblk_alt.sym")], check=True)
    return open(com, "rb").read()


def build(dos: str, out: str, com: bytes) -> None:
    shutil.copyfile(dos, out)
    img = bytearray(open(out, "rb").read())
    fat12_add(img, "WRBLK", "COM", com)          # RT.run types WRBLK at the prompt
    fat12_add(img, "AUTOEXEC", "BAT", b"WRBLK\r\n")
    open(out, "wb").write(img)


def run_once(machine: str, dsk: str, boot_s: int, end_s: int, timeout: float) -> None:
    """Run WRBLK.COM exactly ONCE per machine.

    🔴 NOT RT.run, AND WHY: RT.run types `WRBLK` every 6 s on top of AUTOEXEC,
    because its exerciser (FOPEN) is idempotent under re-runs. This one starts
    with FMAKE, which TRUNCATES. A re-run cut off by the scripted exit, after
    the truncation and before FCLOSE, leaves both files EMPTY. The first cut read
    exactly that (ours empty, then stock empty in a variant), and it looked like
    a WRBLK defect. The CF-3300 honours AUTOEXEC.BAT and C-BIOS's DOS boot does
    not (RT.run's own note), so stock gets AUTOEXEC only and ours one typed
    command."""
    import signal, subprocess as sp, time
    typed = "" if machine == RT.REF_MACHINE else f'after time {boot_s} {{ type "WRBLK\\r" }}\n'
    tcl = f"set throttle off\n{typed}after time {end_s} {{ exit }}\n"
    tcl_path = dsk + ".tcl"
    open(tcl_path, "w").write(tcl)
    cmd = [RT.OMSX, "-machine", machine, "-diska", dsk,
           "-command", "set renderer none; set sound_driver null", "-script", tcl_path]
    proc = sp.Popen(RT.omsx_preflight.guarded(cmd), stdout=sp.DEVNULL,
                    stderr=sp.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.2)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)   # our own child only
        raise TimeoutError(f"TIMEOUT running {machine}")


def file_bytes(f: "RT.Fat12", name: str):
    d = f.dirent(name, "BIN")
    if d is None or d["cluster"] < 2:
        return None, None
    chain, term = f.chain(d["cluster"])
    data = b"".join(f.cluster_bytes(c) for c in chain)[: d["size"]]
    return d, data


def main() -> int:
    if not RT.OUR_MACHINE:
        sys.exit("no zerobas machine: set $ZEROBAS_BASIC_MACHINE (no default, as roundtrip)")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dos-disk", default=RT.DEFAULT_DOS)
    ap.add_argument("--boot", type=int, default=14)
    ap.add_argument("--end", type=int, default=60)
    ap.add_argument("--timeout", type=float, default=120)
    a = ap.parse_args()
    com = assemble()
    ok = True
    for tag, machine in (("OURS ", RT.OUR_MACHINE), ("STOCK", RT.REF_MACHINE)):
        dsk = probe_tmp.tmp(f"wrblk_alt_{tag.strip().lower()}.dsk")
        build(a.dos_disk, dsk, com)
        try:
            run_once(machine, dsk, a.boot, a.end, a.timeout)
        except TimeoutError as e:
            print(f"  {tag} {e}")
            ok = False
            continue
        f = RT.Fat12(dsk)
        for name in ("ALT1", "ALT2"):
            d, data = file_bytes(f, name)
            if d is None:
                print(f"  {tag} {name}.BIN NOT WRITTEN")
                ok = False
                continue
            chain, term = f.chain(d["cluster"])
            good = data == EXPECT[name]
            blocks = [data[i] for i in range(0, len(data), 256)]
            print(f"  {tag} {name}.BIN size={d['size']} chain={chain} "
                  f"eoc={term >= 0xFF8} blocks={[hex(b) for b in blocks]} "
                  f"{'AS EXPECTED' if good else 'WRONG'}")
            ok = ok and good and term >= 0xFF8
    print(f"\n{'PASS' if ok else 'FAIL'}: two FCBs alternating WRBLK "
          f"{'persist as written' if ok else 'do NOT persist as written'} on both machines")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
