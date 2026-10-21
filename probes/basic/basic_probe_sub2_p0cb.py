#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-P0CB slice A (docs/spec-sub2-p0cb.md): zerobas-sub2's PAGE-0 call back into
main, through the BIOS's RAM CLPRIM, proven on BOTH repack machines.

Injects a stub into RAM ($C000) and redirects the CPU into it. Under DI it CALSLTs
zerobas-sub2 page 0, index 2 (SUB2_IDX_P0TEST = p0cb_selftest), with HL = a work
area W ($C200) whose W+15.. holds "Q  XY",0, then halts; the halt is the capture
breakpoint. p0cb_selftest writes (sub2/p0cb.asm's header):
  W+0  A after `rst $10` from W+15 -> 'X'   (sub2's RST 10h -> main's CHRGTR)
  W+1  L after it                    -> low(W+18)
  W+2..W+9 A F B C D E H L after a p0cb to main's bare `ret` (bp_ret), entered with
           A=$5A, CF=1, BC=$1234, DE=$5678, HL=$9ABC -> every register back intact
  W+10 A, W+11 L after a p0cb to main's page-1 skip_spaces from W+16 -> 'X', low(W+18)
  W+12 IX's low byte after the `rst $10`, entered with IX=$5AA5 -> $A5
  W+13 1 if JIFFY moved under EI inside the page-0 tenant (D-SUB2EI's ROM-2 twin)
W+14 is a sentinel the stub writes AFTER the CALSLT returns: $A5 means the tenant
came back. A 12 s safety net captures anyway, so a hang FAILS cleanly.
Clean room: own ROMs, RAM cells, CALSLT (a published BIOS entry).
    python3 -u probes/basic/basic_probe_sub2_p0cb.py
"""
import os
import signal
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_preflight  # noqa: E402

OMSX = os.environ.get("OPENMSX", "/opt/homebrew/bin/openmsx")
MACHINES = ("C-BIOS_MSX1_EU_REPACK_DISK", "C-BIOS_MSX1_EU_REPACK_NODISK")
STUB, W = 0xC000, 0xC200
SUB2_P0, IDX = 0x8F, 2
ENTRY = 0x0040 + 3 * IDX
TEXT = b"Q  XY\x00"                     # at W+15


def stub() -> tuple[bytes, int]:
    b = bytes([0xF3,                                        # di
               0x21, W & 0xFF, W >> 8,                      # ld hl,W
               0xFD, 0x21, 0x00, SUB2_P0,                   # ld iy,$8F00
               0xDD, 0x21, ENTRY & 0xFF, ENTRY >> 8,        # ld ix,entry
               0xCD, 0x1C, 0x00,                            # call CALSLT
               0xF3,                                        # di
               0x3E, 0xA5,                                  # ld a,$A5
               0x32, (W + 14) & 0xFF, (W + 14) >> 8])       # ld (W+14),a
    halt = STUB + len(b)
    return b + bytes([0x76]), halt                          # halt (the capture bp)


def run(machine: str) -> list | None:
    code, halt = stub()
    fd, out = tempfile.mkstemp(suffix=".txt", prefix="p0cb_")
    os.close(fd)
    os.unlink(out)
    lines = [
        "set throttle off",
        "proc __cap {} {",
        f"  set f [open {{{out}}} w]",
        f"  binary scan [debug read_block memory {W} 16] H* h",
        "  puts $f $h",
        "  close $f",
        "  exit",
        "}",
        "after time 8.0 {",
        f"  debug write_block memory {W} [binary format H* {{{('00' * 15) + TEXT.hex()}}}]",
        f"  debug write_block memory {STUB} [binary format H* {{{code.hex()}}}]",
        f"  debug set_bp {halt} {{}} {{ __cap }}",
        f"  reg PC {STUB}",
        "}",
        "after time 12.0 { __cap }",
    ]
    fd, tcl = tempfile.mkstemp(suffix=".tcl", prefix="p0cb_")
    os.write(fd, ("\n".join(lines) + "\n").encode())
    os.close(fd)
    cmd = [OMSX, "-machine", machine, "-command",
           "set renderer none; set sound_driver null", "-script", tcl]
    try:
        proc = subprocess.Popen(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
        deadline = time.time() + 90
        while proc.poll() is None and time.time() < deadline:
            time.sleep(0.1)
        if proc.poll() is None:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            return None
    finally:
        os.unlink(tcl)
    if not os.path.exists(out):
        return None
    h = open(out).read().strip()
    os.unlink(out)
    return list(bytes.fromhex(h)) if h else None


def main() -> int:
    ok = True
    lo18 = (W + 18) & 0xFF
    want = [
        (14, 0xA5, "the tenant RETURNED (sentinel after the CALSLT)"),
        (0, ord("X"), "rst $10 -> main's CHRGTR: A = 'X'"),
        (1, lo18, "rst $10 -> main's CHRGTR: HL past the blanks"),
        (2, 0x5A, "p0cb round trip: A"),
        (4, 0x12, "p0cb round trip: B"), (5, 0x34, "p0cb round trip: C"),
        (6, 0x56, "p0cb round trip: D"), (7, 0x78, "p0cb round trip: E"),
        (8, 0x9A, "p0cb round trip: H"), (9, 0xBC, "p0cb round trip: L"),
        (10, ord("X"), "p0cb -> main page-1 skip_spaces: A = 'X'"),
        (11, lo18, "p0cb -> main page-1 skip_spaces: HL past the blanks"),
        (12, 0xA5, "rst $10 kept IX (s2_chrgtr saves it around p0cb)"),
        (13, 1, "EI inside the page-0 tenant: JIFFY moved, and it came back"),
    ]
    for m in MACHINES:
        res = run(m)
        if res is None or len(res) < 16:
            print(f"{m}: FAIL -- no capture (openMSX did not run the stub)")
            ok = False
            continue
        for off, val, what in want:
            got = res[off]
            good = got == val
            ok &= good
            print(f"{m:30s} W+{off:<2d} ${got:02X} (expect ${val:02X}) {what}: "
                  f"{'PASS' if good else 'FAIL'}")
        f = res[3]
        good = (f & 1) == 1
        ok &= good
        print(f"{m:30s} W+3  F=${f:02X} (expect CF set) p0cb round trip: carry: "
              f"{'PASS' if good else 'FAIL'}")
    print("-------------------")
    print("sub2 p0cb gate:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
