#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""End-to-end functional probe: AUTOEXEC.BAS auto-run at Disk-BASIC cold start.

Spec: disk/docs/autoexec-bas-spec.md. Public contract (MSX2 Technical Handbook,
Ch.3 MSX-DOS, boot procedure, an allowed source): "When MSX-DOS is not invoked
and DISK-BASIC starts, if a BASIC program named AUTOEXEC.BAS exists, it will be
carried out." Exercises the new `autoexec_run` routine (basic/cload.asm, called
from interp.asm's cold-start `init` between `show_title` and `jp repl`):

  * a disk ROM slot recorded -> stage "AUTOEXECBAS" at DISK_FCB_NAME;
  * fat_mount + fat_find a SILENT presence probe (no error if absent);
  * empty file (size 0) -> silent skip;
  * found & non-empty -> disk_prog_load (re-opens via fat_io_open) + run_prog.

This probe boots with ZERO typed keyboard input -- the whole point is to observe
the COLD-START behaviour, before any REPL interaction is possible. Three cases,
each built as a fresh /tmp FAT12 image (tools/make_test_dsk.py's Fat12Image):

  1. POSITIVE (ours): a disk whose only file is a tokenised AUTOEXEC.BAS =
     `10 POKE &HD005,165`. Poison $D005=$11 before boot; after settling it must
     read back $A5 (165) on our C-BIOS_MSX1_EU_BASIC_DISK machine -> the feature
     fires on cold start.
  2. DIFFERENTIAL (stock): the SAME disk booted on the real National_CF-3300
     reference must ALSO leave $D005=$A5 -- ours matches the documented stock
     behaviour (black-box; the CF-3300 ROM is never read/disassembled).
  3. NEGATIVE CONTROL (ours only): a disk with NO AUTOEXEC.BAS at all (just an
     unrelated AUTOEXEC.BIN, wrong extension) must leave $D005=$11 unperturbed --
     silent skip, no spurious run, normal boot untouched.

Strictly black-box on the reference: we build a disk per the public FAT12 spec,
boot National_CF-3300, and observe RAM. No ROM is read or disassembled.

TEST DISK SAFETY: every disk here is a FRESH /tmp image built by this probe --
the committed disk/test720.dsk is never touched.

Prerequisites (CURRENT zerobas tree):
  * `make all` (build/basic.rom under test) then
    `python3 tools/install-openmsx-machine.py --disk-rom build/disk.rom --real-bios-disk`
    (or `make machines-oracle`) so C-BIOS_MSX1_EU_BASIC_DISK reflects the build
    under test and National_CF-3300 is available (bundled openMSX machine + your
    own CF-3300 reference ROMs in ~/.openMSX/share/systemroms).

    python3 probes/disk/disk_probe_autoexec.py
"""
from __future__ import annotations

# --- zerobas probes: locate shared infra (probes/lib) + sibling probes ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_sys.path.insert(0, _os.path.join(_ROOT, "tools"))  # make_test_dsk.py (Fat12Image)

import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from make_test_dsk import Fat12Image  # noqa: E402  (path set up above)

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
ZEROBAS = _ROOT

OURS_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE")
REF_MACHINE = "National_CF-3300"          # the genuine reference, booted black-box

# --- fixture: `10 POKE &HD005,165` -----------------------------------------
# Same token encoding this project's other disk_probe_*.py fixtures use
# (tools/make_test_dsk.py prog_bas_body / disk_probe_save.py / disk_probe_run_disk.py):
#   POKE_TOKEN ' ' HEX_TOKEN <addr LE> ',' INT1_TOKEN <byte> 00
POKE_TOKEN = 0x98
HEX_TOKEN = 0x0C
INT1_TOKEN = 0x0F
TXTBASE = 0x8001

MARK_ADDR = 0xD005
MARK_BYTE = 0xA5           # 165 decimal -- the value the AUTOEXEC.BAS POKEs
POISON_BYTE = 0x11         # pre-boot poison; must survive if autorun does NOT fire


def autoexec_body() -> bytes:
    """Tokenised body for `10 POKE &HD005,165` (no embedded $00). Mirrors
    tools/make_test_dsk.py's prog_bas_body: the address is &H (HEX_TOKEN, 2
    LE bytes) and the value is a 1-byte INT1 literal (165 fits in 0..255)."""
    return bytes([
        POKE_TOKEN,                                    # POKE
        0x20,                                          # ' ' (kept verbatim)
        HEX_TOKEN, MARK_ADDR & 0xFF, MARK_ADDR >> 8,    # &HD005 (LE)
        0x2C,                                           # ',' (verbatim)
        INT1_TOKEN, MARK_BYTE,                          # 165 (1-byte INT1)
        0x00,                                           # line terminator
    ])


def wrap_basic_line(body: bytes, lineno: int = 10, txtbase: int = TXTBASE) -> bytes:
    """Wrap a line body into the in-memory line-link image (no $FF marker).
    Mirrors tools/make_test_dsk.py's wrap_basic_line exactly (link value is a
    don't-care non-zero placeholder; relink recomputes it on load)."""
    import struct
    line_len = 4 + len(body)
    link = txtbase + line_len
    line = struct.pack("<HH", link, lineno) + body
    return line + struct.pack("<H", 0x0000)


def make_basic_file(body: bytes) -> bytes:
    """A tokenised-BASIC disk file: $FF marker (BASIC_DISK_ID) + the image."""
    return bytes([0xFF]) + wrap_basic_line(body)


def build_disk(with_autoexec: bool, wrong_name: bool = False,
               empty_autoexec: bool = False) -> str:
    """A fresh /tmp FAT12 image. with_autoexec=False -> no AUTOEXEC.BAS at all
    (optionally a decoy AUTOEXEC.BIN with wrong_name, still must not fire);
    empty_autoexec=True -> a 0-byte AUTOEXEC.BAS (must skip silently, no error)."""
    img = Fat12Image()
    if empty_autoexec:
        img.add_file("AUTOEXEC", "BAS", b"")        # 0-byte file, size field = 0
    elif with_autoexec:
        img.add_file("AUTOEXEC", "BAS", make_basic_file(autoexec_body()))
    elif wrong_name:
        # decoy: right stem, wrong extension -> must NOT match the 11-byte
        # "AUTOEXECBAS" field fat_find searches for.
        img.add_file("AUTOEXEC", "BIN", make_basic_file(autoexec_body()))
    fd, path = tempfile.mkstemp(suffix=".dsk", prefix="autoexec_probe_")
    os.close(fd)
    with open(path, "wb") as f:
        f.write(img.finish())
    return path


def cold_boot_and_read(machine: str, dsk: str, addr: int, poison: int,
                        out_path: str, timeout: float = 60.0) -> int:
    """Cold-boot `machine` with `dsk` as drive A, poisoning `addr`=`poison`
    as early as possible, then read `addr` back after settling. No typed
    input at all -- this observes the cold-start auto-run path itself."""
    # NB: the poison write must NOT happen at emulated time 0 -- openMSX hasn't
    # finished reset/RAM-mapping yet at that instant, so a t=0 `debug write`
    # can silently no-op (observed: $D005 read back $FF, neither the poison nor
    # the auto-run value, on a no-AUTOEXEC disk). Poison at t=1, well before the
    # cold-start init (and any possible auto-run) reaches the text area.
    tcl = f"""set throttle off
set renderer none
proc poison {{}} {{ debug write memory 0x{addr:04X} 0x{poison:02X} }}
after time 1 {{ poison }}
proc cap {{}} {{
  set f [open {{{out_path}}} w]
  puts $f "val=[format %02X [debug read memory 0x{addr:04X}]]"
  close $f
  exit
}}
after time 20 {{ cap }}
"""
    tcl_path = out_path + ".tcl"
    open(tcl_path, "w").write(tcl)
    if os.path.exists(out_path):
        os.unlink(out_path)
    cmd = [OMSX, "-machine", machine, "-diska", dsk, "-script", tcl_path]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        sys.exit(f"TIMEOUT cold-booting {machine} with {dsk}")
    if not os.path.exists(out_path):
        sys.exit(f"no capture from {machine} (ROMs/machine missing?)")
    d = {}
    for ln in open(out_path):
        k, _, v = ln.strip().partition("=")
        d[k] = v
    if "val" not in d:
        sys.exit(f"capture from {machine} had no 'val=' line")
    return int(d["val"], 16)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ours-machine", default=OURS_MACHINE)
    ap.add_argument("--ref-machine", default=REF_MACHINE)
    args = ap.parse_args()
    if not args.ours_machine:
        sys.exit("no zerobas machine: pass --ours-machine or set $ZEROBAS_BASIC_MACHINE; there is no\n"
                 "default, one would silently pick the BUILD under test "
                 "(docs/spec-lean-retire-s1-explicit-machine.md).")

    ok = True

    # --- 1: positive -- ours must auto-run AUTOEXEC.BAS on cold start --------
    dsk = build_disk(with_autoexec=True)
    try:
        val_ours = cold_boot_and_read(
            args.ours_machine, dsk, MARK_ADDR, POISON_BYTE, "/tmp/autoexec_ours.txt")
    finally:
        os.unlink(dsk)
    r1 = val_ours == MARK_BYTE
    ok = ok and r1
    print(f"[ours: {args.ours_machine}] AUTOEXEC.BAS present -> cold-boot auto-run")
    print(f"  [{'PASS' if r1 else 'FAIL'}] (${MARK_ADDR:04X})=${val_ours:02X} "
          f"(expect ${MARK_BYTE:02X}; poisoned ${POISON_BYTE:02X} pre-boot)")

    # --- 2: DIFFERENTIAL -- the real CF-3300 reference must ALSO auto-run ----
    dsk = build_disk(with_autoexec=True)
    try:
        val_ref = cold_boot_and_read(
            args.ref_machine, dsk, MARK_ADDR, POISON_BYTE, "/tmp/autoexec_ref.txt")
    finally:
        os.unlink(dsk)
    r2 = val_ref == MARK_BYTE
    ok = ok and r2
    print(f"\n[STOCK reference: {args.ref_machine}] AUTOEXEC.BAS present "
          f"-> cold-boot auto-run (CF-3300 differential)")
    print(f"  [{'PASS' if r2 else 'FAIL'}] (${MARK_ADDR:04X})=${val_ref:02X} "
          f"(expect ${MARK_BYTE:02X} -- ours matches the documented stock behaviour)")

    # --- 3: negative control -- no AUTOEXEC.BAS -> silent skip, no run -------
    dsk = build_disk(with_autoexec=False, wrong_name=True)
    try:
        val_neg = cold_boot_and_read(
            args.ours_machine, dsk, MARK_ADDR, POISON_BYTE, "/tmp/autoexec_neg.txt")
    finally:
        os.unlink(dsk)
    r3 = val_neg == POISON_BYTE
    ok = ok and r3
    print(f"\n[ours: {args.ours_machine}] no AUTOEXEC.BAS (decoy AUTOEXEC.BIN only) "
          f"-> normal silent boot")
    print(f"  [{'PASS' if r3 else 'FAIL'}] (${MARK_ADDR:04X})=${val_neg:02X} "
          f"(expect unperturbed poison ${POISON_BYTE:02X} -- no spurious run)")

    # --- 4: empty AUTOEXEC.BAS -> silent skip (no run, no error) -------------
    # A 0-byte AUTOEXEC.BAS: fat_find locates it but the size==0 guard in
    # autoexec_run must skip it silently (matching stock; char'd on CF-3300,
    # spec §2/§4). Without the guard, disk_prog_load would hit EOF-before-marker
    # and print a load error. Poison must survive untouched.
    dsk = build_disk(with_autoexec=False, empty_autoexec=True)
    try:
        val_empty = cold_boot_and_read(
            args.ours_machine, dsk, MARK_ADDR, POISON_BYTE, "/tmp/autoexec_empty.txt")
    finally:
        os.unlink(dsk)
    r4 = val_empty == POISON_BYTE
    ok = ok and r4
    print(f"\n[ours: {args.ours_machine}] empty (0-byte) AUTOEXEC.BAS "
          f"-> silent skip (no run, no error)")
    print(f"  [{'PASS' if r4 else 'FAIL'}] (${MARK_ADDR:04X})=${val_empty:02X} "
          f"(expect unperturbed poison ${POISON_BYTE:02X} -- empty file skipped silently)")

    print("\n" + ("ALL PASS -- AUTOEXEC.BAS auto-runs at Disk-BASIC cold start, "
                  "matching the National_CF-3300 stock reference, with no false "
                  "trigger when absent" if ok else
                  "FAIL -- see per-case results above"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
