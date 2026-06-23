#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""On-device CLOAD probe — end-to-end tokenised-BASIC tape load on zerobas.

Validates that zerobas's CLOAD verb correctly reads a tokenised BASIC program
off cassette, stores it in the program area at TXTBASE, and relinks it — using
the C-BIOS_MSX1_EU_TAPE machine (which carries the zerobas-tape IPS patch for
cassette I/O) with zerobas loaded as a cartridge.  No global machine is
reinstalled; --cart points at the worktree ROM.

THE BUG (now fixed): basic/cload.asm's `ctp_line` stashed the link-low byte in
register C, then called TAPIN again for link-high.  TAPIN ($00E4 in the
zerobas-tape patch) uses C as its 8-bit bit-counter (ld c,8 / dec c), so it
ALWAYS returns C=0.  After the second TAPIN the link word in BC was
(link_high, 0) instead of (link_high, link_low), corrupting the body-length
calculation.  The loop never landed on the $0000 end-link and CLOAD hung
indefinitely.  The same latent bug existed in `dpl_line` (disk program load),
where disk_getbyte clobbers C on every 128-byte SeqRead refill.

THE FIX: preserve link-low via push af before the second TAPIN / disk_getbyte
call; restore it with pop af / ld c,a afterward.  Each error path that now has
AF on the stack gets a dedicated shim label (ctp_link_err, dpl_link_err) that
pops AF before jumping to the error handler, keeping the stack balanced.

BEFORE/AFTER evidence: the probe accepts --before-cart to run the unfixed ROM
first (a short timed run that captures TXTBASE — if the program area is still
empty / zero the load hung) and --cart for the fixed ROM (which loads
correctly).  Pass both to see the contrast.  Pass only --cart to run the
fixed-ROM test (the normal no-regression usage).

Machine: C-BIOS_MSX1_EU_TAPE (carries zerobas-tape IPS; no global reinstall).
Clean-room: inputs/outputs only; no disassembly.
See the clean-room firewall (CONTRIBUTING.md).
"""
from __future__ import annotations

# --- zerobas probes: locate shared infra (probes/lib) + sibling probes ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra

import os
import signal
import subprocess
import shutil
import sys
import tempfile
import time


from cas_encode import build_cas_basic  # noqa: E402
from omsx_run import _tcl_dquote       # noqa: E402

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
if not (os.path.sep in OMSX and os.path.isfile(OMSX)):
    OMSX = "openmsx"

MACHINE = "C-BIOS_MSX1_EU_TAPE"

# Program-area sysvars (zerobas + MSX BASIC shared).
TXTBASE = 0x8001   # stored-program text base (oracle: TXTTAB value after boot)
TXTTAB  = 0xF676   # sysvar: pointer to the BASIC text base


def build_program() -> bytes:
    """A three-line tokenised program image.

    Lines:
      10 A=5    ->  41 EF 16  ('A', EQ $EF, digit-5 $16)
      20 B=7    ->  42 EF 18  ('B', EQ $EF, digit-7 $18)
      30 A=A+B  ->  41 EF 41 F1 42  ('A', EQ, 'A', PLUS $F1, 'B')

    Each line: [link:2 LE][lineno:2 LE][tokens...][00].
    The saved links are absolute addresses starting at TXTBASE (the same layout
    a real CSAVE writes), so the tape bytes match a real save byte-for-byte.
    The program ends with a $0000 link word.

    Tokens sourced from zerobas oracle-confirmed crunch rules
    (basic_probe_crunch.py / sysvars.inc): EQ=$EF, PLUS=$F1,
    digit n -> $11+n.
    """
    lines = [
        (10, bytes([0x41, 0xEF, 0x16])),         # 10 A=5
        (20, bytes([0x42, 0xEF, 0x18])),         # 20 B=7
        (30, bytes([0x41, 0xEF, 0x41, 0xF1, 0x42])),  # 30 A=A+B
    ]
    prog = bytearray()
    addr = TXTBASE
    for lineno, body in lines:
        nxt = addr + 2 + 2 + len(body) + 1  # link+lineno+body+NUL
        prog += nxt.to_bytes(2, "little")
        prog += lineno.to_bytes(2, "little")
        prog += body
        prog += b"\x00"
        addr = nxt
    prog += b"\x00\x00"   # $0000 end-of-program link word
    return bytes(prog)


def expected_image(program: bytes) -> bytes:
    """Recompute the relinked image from the raw program bytes.

    After CLOAD the saved (absolute) links are rewritten by zerobas's `relink`
    routine so that every link pointer is correct for TXTBASE on this machine.
    This function computes what those relinked bytes should look like — the same
    calculation `expected_image` in basic_probe_cload.py performs.
    """
    lines, i = [], 0
    while int.from_bytes(program[i:i + 2], "little") != 0:
        lineno = int.from_bytes(program[i + 2:i + 4], "little")
        j = i + 4
        while program[j] != 0:
            j += 1
        lines.append((lineno, program[i + 4:j]))
        i = j + 1
    out, addr = bytearray(), TXTBASE
    for lineno, body in lines:
        size = 2 + 2 + len(body) + 1
        nxt = addr + size
        out += nxt.to_bytes(2, "little")
        out += lineno.to_bytes(2, "little")
        out += body
        out += b"\x00"
        addr = nxt
    out += b"\x00\x00"
    return bytes(out)


def run_cload(cart: str, cas_path: str, dump_len: int,
              cap_time: float = 30.0, timeout: float = 75.0) -> bytes | None:
    """Boot openMSX with MACHINE + cart + cassette, type CLOAD, wait cap_time.

    Returns the bytes at TXTBASE (length dump_len) if captured, else None.
    A captured all-zero block means the load did not complete (hung).
    """
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="cload_od_")
    os.close(out_fd)

    # Type CLOAD after the zerobas prompt has appeared (~6 s emulated).
    type_cmd = _tcl_dquote("cload")
    enter_cmd = _tcl_dquote("\r")

    tcl_lines = [
        "set throttle off",
        "proc __hex {dbg addr len} {",
        "  binary scan [debug read_block $dbg $addr $len] H* h; return $h",
        "}",
        f"after time 6 {{ type {type_cmd} }}",
        f"after time 8 {{ type {enter_cmd} }}",
        "proc __cap {} {",
        f"  set f [open {{{os.path.abspath(out_path)}}} w]",
        f'  puts $f "mem.0x{TXTBASE:04X}=[__hex {{memory}} {TXTBASE} {dump_len}]"',
        "  close $f",
        "  exit",
        "}",
        f"after time {cap_time} {{ __cap }}",
    ]
    tcl = "\n".join(tcl_lines) + "\n"

    fd, tcl_path = tempfile.mkstemp(suffix=".tcl", prefix="cload_od_")
    os.write(fd, tcl.encode())
    os.close(fd)

    cmd = [OMSX, "-machine", MACHINE, "-cart", cart,
           "-cassetteplayer", cas_path,
           "-command", "set renderer none", "-script", tcl_path]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
        deadline = time.time() + timeout
        while proc.poll() is None and time.time() < deadline:
            time.sleep(0.1)
        if proc.poll() is None:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    finally:
        os.unlink(tcl_path)

    result = None
    if os.path.exists(out_path):
        with open(out_path) as f:
            for line in f:
                key = f"mem.0x{TXTBASE:04X}="
                if line.startswith(key):
                    result = bytes.fromhex(line[len(key):].strip())
        os.unlink(out_path)
    return result


def check(label: str, cond: bool, detail: str = "") -> bool:
    tag = "PASS" if cond else "FAIL"
    print(f"{tag}  {label}" + (f"  {detail}" if detail else ""))
    return cond


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cart", required=True,
                    help="fixed zerobas basic.rom (with the ctp_line/dpl_line fix)")
    ap.add_argument("--before-cart",
                    help="unfixed zerobas basic.rom (to demonstrate the hang; "
                         "optional — pass to show before/after contrast)")
    args = ap.parse_args()

    program = build_program()
    want = expected_image(program)
    dump_len = len(want)

    # Build the .cas once; share it across test cases.
    cas = build_cas_basic("PROG", program)
    cas_fd, cas_path = tempfile.mkstemp(suffix=".cas", prefix="cload_od_")
    os.write(cas_fd, cas)
    os.close(cas_fd)

    ok = True

    try:
        # ---- BEFORE: demonstrate the register-clobber corruption (optional) --
        if args.before_cart:
            print(f"== BEFORE fix: unfixed ROM ({args.before_cart}) ==")
            print("   (C clobbered by TAPIN: link-low $09 -> $00; first link "
                  "corrupted to $8000 instead of $8009)")
            got_before = run_cload(args.before_cart, cas_path, dump_len,
                                   cap_time=30.0, timeout=75.0)
            # The bug: TAPIN clobbers C, so link-low=$09 becomes $00.
            # The loaded image (if anything loads) has a wrong first link word
            # ($8000 instead of $8009) and/or wrong body layout. Either the
            # data is corrupt or the load hangs entirely. Both are proof of
            # the bug. PASS here means the before-ROM does NOT produce the
            # correct image (i.e. the bug is observable).
            before_corrupt = (got_before is None or got_before != want)
            ok &= check(
                "BEFORE fix: CLOAD produces corrupt/wrong image (C-clobber bug)",
                before_corrupt,
                f"got: {got_before.hex(' ') if got_before else '<no capture>'}"
                f"\n        want: {want.hex(' ')}")
            print()

        # ---- AFTER: fixed ROM loads the program correctly --------------------
        print(f"== AFTER fix: fixed ROM ({args.cart}) ==")
        got_after = run_cload(args.cart, cas_path, dump_len,
                              cap_time=30.0, timeout=75.0)

        loaded = got_after is not None and got_after == want
        ok &= check(
            "AFTER fix: CLOAD loads program; TXTBASE matches expected image",
            loaded,
            f"\n        want: {want.hex(' ')}"
            f"\n        got : {got_after.hex(' ') if got_after else '<no capture>'}")

        # Extra sanity: the first link word must be non-zero (program not empty)
        if got_after is not None:
            first_link = int.from_bytes(got_after[:2], "little")
            ok &= check(
                "First link word is non-zero (program area populated)",
                first_link != 0,
                f"link=0x{first_link:04X}")

            # The last two bytes must be the $0000 end-of-program word.
            end_link = int.from_bytes(got_after[-2:], "little")
            ok &= check(
                "Last two bytes are $0000 (end-of-program link)",
                end_link == 0,
                f"end=0x{end_link:04X}")

    finally:
        os.unlink(cas_path)

    print("\nALL PASS" if ok else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
