#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Functional probe: does zerobas-BASIC's INIT run the disk ROM's INIT?

Background. On the combined machine (zerobas-BASIC in slot 0 page 1, zerobas-disk
in slot 3-1) C-BIOS's cold-boot cartridge scan reaches zerobas-BASIC first; its
INIT enters the REPL and never returns, so C-BIOS never scans slot 3-1 and the
disk ROM's INIT never runs -- the SYSTEM/BDOS vector is never installed.
zerobas-BASIC's INIT therefore performs the rest of that boot scan itself
(basic/initext.asm): it walks the remaining slots, finds each "AB" header, and
CALSLTs its INIT.

This probe boots the combined machine, lets it settle to the REPL, and reads the
one system location the disk ROM's INIT publishes:

  * SYSTEM  $F37D  -- BDOS entry vector; disk INIT sets it to bdos_entry ($429F).
                     C-BIOS default is a BIOS-ROM address ($31C3).

If SYSTEM carries the disk ROM's bdos_entry, the disk INIT ran -- i.e. zerobas's
slot scan reached and called it. The differential control still works: the
pre-scan ROM leaves $F37D at the C-BIOS default. Strictly an observation of
post-boot system RAM; no ROM is read or disassembled.

NOTE: this probe formerly also asserted H.PHYD ($FF3E) and H.DSKIO ($FF4B) JP
hooks. Those hooks were REMOVED from disk/disk.asm as oracle-contradicted dead
code (ref disk/PROVENANCE.md §INIT): the real CF-3300 disk ROM hooks via RST 30h
inter-slot calls at different, 5-byte-aligned addresses -- a plain JP at
$FF3E/$FF4B cannot cross slots and $FF4B is not even hook-table-aligned -- and
zerobas is a standalone BASIC that never drives the Disk-BASIC H.* chain anyway
(it reaches the file layer via the SYSTEM-vector BDOS entry + CALSLT). So the
meaningful "INIT ran and published the BDOS entry" check is SYSTEM-only.

The expected disk-ROM address comes from the zerobas-disk build's own symbol
table (`pasmo --bin disk/disk.asm out.rom syms.txt`): bdos_entry=$429F. If
disk/disk.asm changes that, update below.

Prerequisites:
  * openMSX.
  * The combined machine installed from the CURRENT zerobas tree
    (`python3 tools/install-openmsx-machine.py --disk-rom disk.rom`), so its
    slot-0 zerobas IPS reflects the INIT scan under test. Pass a different
    machine name with --machine (e.g. a temporary one) if needed.

    python3 probes/disk/disk_probe_init.py
    python3 probes/disk/disk_probe_init.py --machine zerobas_inittest
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
import signal
import subprocess
import shutil
import sys
import time
# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(
    _zbo.path.dirname(_zbo.path.abspath(__file__))), "lib"))
import omsx_preflight  # noqa: E402

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"

# Values the zerobas-disk INIT installs (from disk/disk.asm's pasmo symbols).
SYSTEM_ADDR = 0xF37D
EXP_BDOS = 0x44FF           # SYSTEM -> bdos_entry (moved $421E -> $429F when the
                            # Phase-1.5 provider HPHYD-hook install grew INIT, then
                            # $429F -> $42F6 with the Tier-2 a1/a2 boot bridge +
                            # page0 paging, then $42F6 -> $439F with the a2 step-6
                            # page-0 env, then $439F -> $43A4 when INIT changed the
                            # $F37D publish to an executable JP (a3 §8.9), then
                            # $43A4 -> $43B6 when the $4030 entry was inlined (a3 §8.13),
                            # then $43B6 -> $43EA when set_ramad was added to INIT (a3 §8.16),
                            # then $43EA -> $43FB ($F368 table, a3 §8.18); a $DF93 HIMEM
                            # reserve was tried in §8.19 then reverted — HIMEM is not the lever;
                            # then $43FB -> $4453 when build_drvtbl ($F348 DRVTBL + 4 CALLF
                            # trampolines) was added to INIT (a3 §8.22), then
                            # $4453 -> $4465 when build_resident (the $F1C9 work-area
                            # routine) was added to INIT (a3 §8.28), then
                            # $4465 -> $4472 when build_resident also fills the
                            # $F24E-$F2FD no-op segment-hook stub table (a3 §8.29), then
                            # $4472 -> $447C when build_resident builds the drive-A DPB
                            # at $F195 via GETDPB (a3 §8.30), then $447C -> $4480 when the
                            # boot bridge sets IX=$F195 before the MSXDOS.SYS handoff (§8.31),
                            # then $4480 -> $4484 when set_ramad cleared $F340 (a3 §8.33),
                            # then $4484 -> $44AD when the FDC DI-guard helpers were added
                            # before the read/write paths (a3 §8.34), then
                            # $44AD -> $44F9 when P1_BLIT got a DI guard (a3 §8.35), then
                            # $44F9 -> $44FF when fdc_di_save/fdc_io_done were added around
                            # P1_BLIT in dskio to prevent VDP IRQ clobbering blit (a3 §8.36))
# INIT now writes $F37D as an executable JP vector (C3 <bdos_entry>), not a bare
# address word — the MSX-DOS boot CALLs $F37D and executes those bytes (a3 §8.9).


def run_machine(machine: str, out: str, boot_secs: float = 8.0,
                timeout: float = 45.0) -> dict:
    """Boot `machine`, settle to the REPL, capture the SYSTEM vector."""
    tcl = f"""set throttle off
proc __hex {{a l}} {{ binary scan [debug read_block memory $a $l] H* h; return $h }}
proc cap {{}} {{
  set f [open {{{out}}} w]
  puts $f "system=[__hex 0x{SYSTEM_ADDR:04X} 3]"
  close $f; exit
}}
after time {boot_secs} {{ cap }}
after time {boot_secs + 25} {{ cap }}
"""
    tcl_path = out + ".tcl"
    open(tcl_path, "w").write(tcl)
    if os.path.exists(out):
        os.unlink(out)
    cmd = [OMSX, "-machine", machine,
           "-command", "set renderer none; set sound_driver null", "-script", tcl_path]
    proc = subprocess.Popen(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        sys.exit(f"TIMEOUT running {machine}")
    if not os.path.exists(out):
        sys.exit(f"no capture from {machine} (machine missing? ROMs absent?)")
    d = {}
    for line in open(out):
        k, _, v = line.strip().partition("=")
        d[k] = v
    return d


def word_le(hexbytes: str, off: int = 0) -> int:
    b = bytes.fromhex(hexbytes)
    return b[off] | (b[off + 1] << 8)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=os.environ.get("ZEROBAS_BASIC_MACHINE"))
    args = ap.parse_args()
    if not args.machine:
        sys.exit("no zerobas machine: pass --machine or set $ZEROBAS_BASIC_MACHINE; there is no default,\n"
                 "one would silently pick the BUILD under test "
                 "(docs/spec-lean-retire-s1-explicit-machine.md).")

    d = run_machine(args.machine, "/tmp/disk_probe_init.txt")

    sysbytes = bytes.fromhex(d["system"])      # $F37D, $F37E, $F37F
    jp_op = sysbytes[0]                         # expect $C3 (JP)
    target = word_le(d["system"], 1)            # JP target = bdos_entry

    checks = [
        (f"SYSTEM $F37D opcode = ${jp_op:02X} (expect $C3 JP)",
         jp_op == 0xC3),
        (f"SYSTEM $F37D JP target = ${target:04X} (expect ${EXP_BDOS:04X} bdos_entry)",
         target == EXP_BDOS),
    ]
    ok = True
    for label, good in checks:
        print(f"  [{'PASS' if good else 'FAIL'}] {label}")
        ok = ok and good
    print("\n" + ("ALL PASS — disk ROM INIT ran (zerobas slot scan reached slot 3-1)"
                  if ok else
                  "FAIL — disk hooks/SYSTEM still at C-BIOS defaults: INIT did NOT run"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
