#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Open-stack BLOAD regression: zerobas + stock C-BIOS + the cbios-tape patch
load a tape end-to-end, with NO copyrighted VG-8020 ROM anywhere.

Pipeline (all open / clean-room):

  1. A write cart (built here with the shared z80probe harness) lays our BSAVE
     blob onto a tape via the cbios-tape *write* path (TAPOON/TAPOUT) at 1200
     baud, recorded to a .wav by `omsx_run --record`.
  2. zerobas (clean-room BASIC) tokenises and executes `BLOAD"CAS:",R`.
  3. The cbios-tape *read* path (TAPION/TAPIN) reads both blocks back, and the
     `,R` handoff jumps into the loaded code, which writes "JONG" at 0xE000.

We assert the blob loaded (0xC000 bytes), no error (ERRMARK clear), the marker
("JONG"), and PC at the landmark (handoff ran).

Prerequisite: the `C-BIOS_tape` openMSX machine (stock C-BIOS v0.29 + the
cbios-tape IPS applied on load). Build the patch in the cbios-tape repo first.

Why a WAV and not a .cas: openMSX synthesizes .cas audio at 3744 baud, outside
the cbios-tape read path's tuned 1200/2400 range, so a .cas does not lock yet
(see docs/finding-openmsx-cas-3744-baud.md). A 1200-baud recording is squarely
in range, so this exercises the real open-stack read path today. When the read
path gains 3744-baud support, a .cas BLOAD (basic_probe_bload.py --machine
C-BIOS_tape) should pass too.

Clean-room: this drives only public BIOS entry points and treats the cbios-tape
patch as a black box; nothing in cbios-tape is read or modified here.
"""
from __future__ import annotations

# --- zerobas probes: locate shared infra (probes/lib) + sibling probes ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra

import argparse
import os
import subprocess
import sys
import tempfile


import z80probe as Z  # noqa: E402
from basic_probe_bload import build_blob, LOAD_ADDR, LANDMARK  # noqa: E402

OMSX_RUN = os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib", "omsx_run.py")
MACHINE = "C-BIOS_tape"

# cassette write-path BIOS entry points (driven via z80probe).
TAPOON, TAPOUT, TAPOOF = 0x00EA, 0x00ED, 0x00F0


def build_write_cart(baud: int = 1200) -> bytes:
    """A cart that writes our blob as a BSAVE tape file: a header block
    (0xD0 x10 + 6-char name) then a data block (start/end/exec LE + payload).
    exec = LOAD_ADDR so the ,R handoff runs the blob from its entry point."""
    blob = build_blob()
    end = LOAD_ADDR + len(blob) - 1
    exec_addr = LOAD_ADDR
    header = [0xD0] * 10 + [ord(c) for c in "JONG  "]
    data = [LOAD_ADDR & 0xFF, LOAD_ADDR >> 8,
            end & 0xFF, end >> 8,
            exec_addr & 0xFF, exec_addr >> 8] + list(blob)

    c = Z.Cart()
    c.emit(Z.di())
    c.emit(Z.setup_cas_baud(baud))            # lay down the 1200/2400 timing tables
    c.emit(Z.ld_a(0xFF), Z.call(TAPOON))      # long leader
    for b in header:
        c.emit(Z.ld_a(b), Z.call(TAPOUT))
    c.emit(Z.call(TAPOOF))
    c.emit(Z.ld_a(0x00), Z.call(TAPOON))      # short leader
    for b in data:
        c.emit(Z.ld_a(b), Z.call(TAPOUT))
    c.emit(Z.call(TAPOOF))
    return c.build()


def omsx(args_list, timeout=120):
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="openstack_")
    os.close(out_fd)
    rc = subprocess.call([sys.executable, OMSX_RUN, *args_list,
                          "--out", out_path, "--timeout", str(timeout)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cap = ""
    if os.path.exists(out_path):
        with open(out_path) as f:
            cap = f.read()
        os.unlink(out_path)
    return rc, cap


def memval(cap, key):
    for line in cap.splitlines():
        if line.startswith(key):
            return line.split("=", 1)[1]
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=MACHINE,
                    help=f"openMSX machine (default {MACHINE})")
    ap.add_argument("--cart", required=True, help="zerobas basic.rom")
    ap.add_argument("--baud", type=int, choices=(1200, 2400), default=1200)
    args = ap.parse_args()

    # 1) write our blob to a WAV via the open write path.
    wrom_fd, wrom = tempfile.mkstemp(suffix=".rom", prefix="openstack_w_")
    os.write(wrom_fd, build_write_cart(args.baud))
    os.close(wrom_fd)
    wav = tempfile.mktemp(suffix=".wav", prefix="openstack_")
    rc, _ = omsx(["--machine", args.machine, "--cart", wrom,
                  "--record", wav, "--bp", hex(Z.DONE), "--reg", "PC"])
    os.unlink(wrom)
    if not (os.path.exists(wav) and os.path.getsize(wav) > 0):
        print(f"FAIL  could not record WAV (machine {args.machine} present?)")
        return 1

    # 2+3) BLOAD that WAV with zerobas; the ,R handoff runs the blob.
    rc, cap = omsx([
        "--machine", args.machine, "--cart", args.cart, "--cassette", wav,
        "--type", 'bload"cas:",r', "--type-delay", "6",
        "--type", "\r", "--type-delay", "10",
        "--bp", hex(LANDMARK), "--reg", "PC",
        "--mem", "memory:0xE000:4",        # JONG marker
        "--mem", "memory:0xE010:1",        # ERRMARK ($EE on load error)
        "--mem", "memory:0xC000:8",        # loaded blob prologue
    ])
    if os.path.exists(wav):
        os.unlink(wav)

    blob8 = (build_blob()[:8]).hex()
    jong = memval(cap, "mem.memory:0xE000:4=")
    err = memval(cap, "mem.memory:0xE010:1=")
    c000 = memval(cap, "mem.memory:0xC000:8=")
    pc_ok = f"reg.PC=0x{LANDMARK:04X}" in cap

    ok = (jong == "4a4f4e47" and pc_ok and err == "ff" and c000 == blob8)
    print(f"{'PASS' if ok else 'FAIL'}  open-stack BLOAD (zerobas + C-BIOS + cbios-tape, {args.baud} baud WAV)")
    print(f"        blob@C000 : {c000}  (expect {blob8})")
    print(f"        ERRMARK   : {err}  (ff = no error)")
    print(f"        JONG@E000 : {jong}  (expect 4a4f4e47)")
    print(f"        PC@landmark 0x{LANDMARK:04X}: {pc_ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
