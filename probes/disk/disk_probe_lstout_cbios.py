#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""End-to-end BDOS $05 LSTOUT probe on the **C-BIOS target** (not the CF-3300 oracle).

WHY THIS EXISTS. The disk ROM's BDOS $05 LSTOUT (list output) is BIOS-delegating:
its kernel func-5 worker $5465 (`lstout_body`) calls main-BIOS LPTOUT $00A5 with the
char in A, and inherits whatever the host BIOS does (the two-interface rule). On the
CF-3300 oracle $00A5 was always real, so LSTOUT was testable there and is a standing
bdos-acceptance guard. But on the actual **C-BIOS target** $00A5 was a stub, so list
output silently no-op'd and the full path could NOT be exercised end to end. As of
2026-07-07 the zerobas-tape patch supplies a real C-BIOS LPTOUT ($00A5), so the whole
chain now works on the target -- and this probe pins that:

    MSX-DOS (booted under C-BIOS + our disk ROM)
      -> LSTOUTX.COM: 5x BDOS $05 LSTOUT (E=char)
        -> disk-ROM kernel func-5 worker $5465 lstout_body (A=char)
          -> C-BIOS LPTOUT $00A5  (the zerobas-tape routine)
            -> poll $90 / latch $91 / strobe -> openMSX printer `logger`

WHAT IT ASSERTS. It boots C-BIOS_MSX1_EU_BASIC_DISK (C-BIOS + zerobas-tape[LPTOUT] +
zerobas-disk in slot 3-1) with a FAT12 DOS disk carrying LSTOUTX.COM and an openMSX
`logger` plugged into the printer port, launches LSTOUTX at the A> prompt, and
asserts the printer log contains exactly the LSTOUTX signature `LP!\r\n`
(`4C 50 21 0D 0A`) -- proving list output physically reaches the printer through our
LPTOUT. Black-box: we attach a disk, plug a printer, run a .COM, and read the bytes
the printer received. No ROM is decoded.

LAUNCHER NOTE. LSTOUTX is launched by TYPING `LSTOUTX\r` at the A> prompt. The
zero-typing AUTOEXEC.BAT launcher used elsewhere does NOT fire under the C-BIOS DOS
boot (a COMMAND.COM-under-C-BIOS quirk, tracked separately); typing is the reliable
path here. A leading `\r` lands a clean prompt first to blunt the openMSX
first-keypress-doubling window (openmsx-probing-toolbox.md §8).

PREREQUISITES.
  * openMSX with the C-BIOS_MSX1_EU_BASIC_DISK machine installed:
      python3 tools/install-openmsx-machine.py --disk-rom build/disk.rom
    (needs build/disk.rom + the freshly-built tape/zerobas-tape-msx1.ips).
  * pasmo on PATH (to assemble lstoutx.asm).
  * A real MSX-DOS 1 disk to inject LSTOUTX.COM into (the FAT12/COMMAND.COM host);
    default ~/Documents/msx/msx/disks/test.dsk (see msxdos-oracle-disk).

    python3 probes/disk/disk_probe_lstout_cbios.py
    python3 probes/disk/disk_probe_lstout_cbios.py --machine C-BIOS_MSX1_JP_BASIC_DISK
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # sibling probes
from disk_probe_bdos import fat12_add  # noqa: E402  (reuse the FAT12 injector)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OMSX = os.environ.get("OPENMSX") or "/opt/homebrew/bin/openmsx"
LSTOUTX_ASM = os.path.join(HERE, "lstoutx.asm")
DEFAULT_MACHINE = "C-BIOS_MSX1_EU_BASIC_DISK"
DEFAULT_DOS_DISK = os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")

# LSTOUTX sends 'L' 'P' '!' CR LF to the list device, each via its own BDOS $05
# call, then self-loops at `done`. That exact 5-byte stream is the assertion target.
EXPECT = b"LP!\r\n"


def assemble_lstoutx(tmp_dir: str) -> bytes:
    com = os.path.join(tmp_dir, "lstoutx.com")
    subprocess.run(["pasmo", "--bin", LSTOUTX_ASM, com], check=True)
    return open(com, "rb").read()


def build_disk(dos_src: str, com: bytes, out: str) -> None:
    img = bytearray(open(dos_src, "rb").read())
    fat12_add(img, "LSTOUTX", "COM", com)
    open(out, "wb").write(img)


def run(machine: str, disk: str, log: str, settle: float, timeout: float) -> None:
    # Boot, plug the logger, wait for the A> prompt to settle, then type the
    # command. `set renderer none` + `throttle off` = fast headless run.
    tcl = f"""set throttle off
set renderer none
set printerlogfilename {{{log}}}
catch {{ plug printerport logger }}
after time {settle} {{
  type "\\r"
  after time 1 {{
    type "LSTOUTX\\r"
    after time 4 {{ exit }}
  }}
}}
"""
    tcl_path = log + ".tcl"
    open(tcl_path, "w").write(tcl)
    if os.path.exists(log):
        os.unlink(log)
    cmd = [OMSX, "-machine", machine, "-diska", disk, "-script", tcl_path]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        sys.exit(f"TIMEOUT booting {machine}")


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=DEFAULT_MACHINE,
                    help=f"C-BIOS+disk target machine (default: {DEFAULT_MACHINE})")
    ap.add_argument("--dos-disk", default=DEFAULT_DOS_DISK,
                    help="MSX-DOS 1 disk to inject LSTOUTX.COM into (default: test.dsk)")
    ap.add_argument("--settle", type=float, default=12.0,
                    help="emulated seconds to let the C-BIOS DOS boot reach A> before typing")
    ap.add_argument("--timeout", type=float, default=90.0)
    args = ap.parse_args()

    if not os.path.isfile(args.dos_disk):
        print(f"DOS source disk not found: {args.dos_disk}", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory() as tmp:
        com = assemble_lstoutx(tmp)
        disk = os.path.join(tmp, "lstout_cbios.dsk")
        build_disk(args.dos_disk, com, disk)
        log = os.path.join(tmp, "printer.log")
        print(f"machine   : {args.machine}")
        print(f"LSTOUTX   : {len(com)} bytes, BDOS $05 x5 -> 'LP!\\r\\n'")
        run(args.machine, disk, log, args.settle, args.timeout)

        got = open(log, "rb").read() if os.path.exists(log) else b""
        print(f"printer   : {got!r}")
        if got == EXPECT:
            print("PASS  BDOS $05 LSTOUT reached the printer through C-BIOS LPTOUT "
                  f"($00A5) -- got exactly {EXPECT!r} on the C-BIOS target.")
            return 0
        if not got:
            print("FAIL  printer log is EMPTY -- LSTOUTX never printed. Either the DOS "
                  "boot/type launch failed, or C-BIOS $00A5 is a stub (tape patch not "
                  "applied to this machine).", file=sys.stderr)
        else:
            print(f"FAIL  printer got {got!r}, expected {EXPECT!r} (typo/doubling on "
                  "launch, or a partial print) -- re-run; see the launcher note.",
                  file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
