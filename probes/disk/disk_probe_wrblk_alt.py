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
          "ALT2": bytes(b for f in (0x12, 0x14, 0x16, 0x18) for b in [f] * 256),
          # the READ side: both files read back alternately with RS = 1 RDBLK and
          # appended to OUT.BIN with WRBLK -- the blocks in interleaved order
          "OUT": bytes(b for f in range(0x11, 0x19) for b in [f] * 256),
          # the RDRND side: record 2k of each file (block k's fill), alternately,
          # 128 B a record, appended to OUT2.BIN
          "OUT2": bytes(b for f in range(0x11, 0x19) for b in [f] * 128)}


def assemble() -> bytes:
    com = probe_tmp.tmp("wrblk_alt.com")
    subprocess.run(["pasmo", "--bin", ASM, com, probe_tmp.tmp("wrblk_alt.sym")], check=True)
    return open(com, "rb").read()


# --seek: BIG.BIN, 32 KB, block k = 256 x k (k = 0..127) -- D-RDBLKSEEK's file
BIG = bytes(k for k in range(128) for _ in range(256))


def build(dos: str, out: str, com: bytes, big: bool = False) -> None:
    shutil.copyfile(dos, out)
    img = bytearray(open(out, "rb").read())
    fat12_add(img, "WRBLK", "COM", com)          # RT.run types WRBLK at the prompt
    if big:
        fat12_add(img, "BIG", "BIN", BIG)
    fat12_add(img, "AUTOEXEC", "BAT", b"WRBLK\r\n")
    open(out, "wb").write(img)


def run_once(machine: str, dsk: str, boot_s: int, end_s: int, timeout: float,
             phase_log: str | None = None) -> None:
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
    if phase_log:
        # --time: poll the exerciser's PHASE byte ($C000, page-3 TPA -- the
        # program's own data, never ROM) every 50 ms of EMULATED time and log
        # each change with the emulated clock.
        tcl += (f"set ph_last -1\nset ph_f [open {{{phase_log}}} w]\n"
                "proc ph_poll {} { global ph_last ph_f; "
                "set v [debug read memory 0xC000]; "
                "if {$v != $ph_last} { puts $ph_f \"$v [machine_info time] "
                "[debug read memory 0xC001]\"; "
                "if {$v == 6} { foreach b {0xC010 0xC040 0xC070} { set l {}; "
                "for {set i 0} {$i < 37} {incr i} { lappend l [debug read memory [expr {$b + $i}]] }; "
                "puts $ph_f \"FCB $b $l\" } }; "
                "flush $ph_f; set ph_last $v }; after time 0.05 ph_poll }\n"
                "after time 1 ph_poll\n")
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


def phase_times(plog: str) -> str:
    """The write and read phases' emulated durations from the PHASE log: the
    LAST 1 -> 2, 2 -> 3 and 3 -> 4 transitions (the byte holds boot garbage before
    the program first writes it)."""
    ev = [(int(v), float(at), int(e)) for v, at, e in
          (ln.split() for ln in open(plog) if ln.strip() and not ln.startswith("FCB"))]
    t, errs = {}, None
    for v, at, e in ev:
        if v in (1, 2, 3, 4, 5, 6):
            t[v] = at
        if v == 6:
            errs = e
    if not all(k in t for k in (1, 2, 3, 4)) or not t[1] < t[2] < t[3] < t[4]:
        return f"INCOMPLETE {ev[-6:]}"
    out = (f"write {t[2] - t[1]:.2f} s, RDBLK read {t[3] - t[2]:.2f} s, "
           f"RDRND read {t[4] - t[3]:.2f} s")
    if 5 in t:
        out += (f", SEEK read (32 KB) " + (f"{t[6] - t[5]:.2f} s, {errs} wrong block(s)"
                                          if 6 in t else "UNFINISHED"))
    return out


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
    # --read: also check OUT.BIN, the READ side (RDBLK $27, RS = 1, two FCBs
    # alternately). D-RDBLKMULTI (fixed 2026-10-01): ours read whichever file was
    # found LAST. The gate (`make wrblkalt-acceptance`) runs with it, and with
    # --end 150: ours takes ~72 emulated s for all three phases (--time), past
    # the default 60 s window once boot is counted (the scripted exit cut OUT.BIN's last
    # block on the first run -- an unfinished program, not a wrong one).
    ap.add_argument("--read", action="store_true")
    # --rnd: also check OUT2.BIN, the RDRND side ($21, RS = 128, two FCBs
    # alternately at record 2k). D-RDRNDMULTI (2026-10-01).
    ap.add_argument("--rnd", action="store_true")
    # --time: report each machine's EMULATED seconds for the write phase (FMAKE
    # .. FCLOSE of ALT1/ALT2) and the read phase (FOPEN .. FCLOSE of OUT.BIN),
    # from the exerciser's PHASE byte. A ratio, never a tick (T5's rule).
    ap.add_argument("--time", action="store_true")
    # --seek: put BIG.BIN (32 KB) on the disk, so the exerciser's fifth phase
    # reads it whole in 256 B RDBLKs -- D-RDBLKSEEK's row, read with --time.
    ap.add_argument("--seek", action="store_true")
    a = ap.parse_args()
    com = assemble()
    ok = True
    for tag, machine in (("OURS ", RT.OUR_MACHINE), ("STOCK", RT.REF_MACHINE)):
        dsk = probe_tmp.tmp(f"wrblk_alt_{tag.strip().lower()}.dsk")
        build(a.dos_disk, dsk, com, a.seek)
        plog = probe_tmp.tmp(f"wrblk_alt_{tag.strip().lower()}.phase") if a.time else None
        try:
            run_once(machine, dsk, a.boot, a.end, a.timeout, plog)
        except TimeoutError as e:
            print(f"  {tag} {e}")
            ok = False
            continue
        if plog:
            print(f"  {tag} phases: {phase_times(plog)}")
            for ln in open(plog):
                if ln.startswith("FCB"):
                    _, base, *bs = ln.split()
                    what = {"0xC010": "after FOPEN", "0xC040": "after block 0",
                            "0xC070": "after block 5"}[base]
                    print(f"  {tag} FCB {what:13} " + " ".join(f"{int(b):02X}" for b in bs))
        f = RT.Fat12(dsk)
        names = ["ALT1", "ALT2"] + (["OUT"] if a.read else []) + (["OUT2"] if a.rnd else [])
        for name in names:
            d, data = file_bytes(f, name)
            if d is None:
                print(f"  {tag} {name}.BIN NOT WRITTEN")
                ok = False
                continue
            chain, term = f.chain(d["cluster"])
            good = data == EXPECT[name]
            blocks = [data[i] for i in range(0, len(data), 128 if name == "OUT2" else 256)]
            print(f"  {tag} {name}.BIN size={d['size']} chain={chain} "
                  f"eoc={term >= 0xFF8} blocks={[hex(b) for b in blocks]} "
                  f"{'AS EXPECTED' if good else 'WRONG'}")
            ok = ok and good and term >= 0xFF8
    print(f"\n{'PASS' if ok else 'FAIL'}: two FCBs alternating block/random I/O "
          f"{'persist as written' if ok else 'do NOT persist as written'} on both machines")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
