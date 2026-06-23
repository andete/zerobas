#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""CLOAD / LOAD"CAS:" oracle probe — cassette tokenised-BASIC program load.

zerobas's CLOAD and LOAD"CAS:" read a *tokenised BASIC program* off cassette into
the stored-program area (the line-link area RUN / LIST walk) and make it the
current program — the complement to BLOAD"CAS:",R (which loads a binary image).

This probe validates the feature two ways, both against the real Philips VG-8020:

  1. CRUNCH (zerobas vs reference, byte-identical): the load keywords must crunch
     to the reference's exact token bytes. We feed `cload`, `cload"name"`,
     `load"cas:name"`, `load` and `load"cas:"` and compare zerobas's TOKBUF to the
     reference's KBUF. Oracle: CLOAD -> $9B, LOAD -> $B5 (single-byte statement
     tokens, the quoted filename kept verbatim — cross-checks MSX2 TH Table 2.20).

  2. FORMAT/LOAD (reference oracle): we build a tokenised-BASIC .cas (a real
     two-block $D3 image), feed it to the reference's OWN built-in CLOAD, and dump
     its text area (TXTBASE $8001). If the reference loads our synthetic tape to
     the expected line-link image, the .cas format is correct AND a faithful
     loader (zerobas's) that reads the same byte stream produces that same image.

ON-ZEROBAS FUNCTIONAL LOAD: an on-device CLOAD on zerobas is now exercised by
the companion probe basic_probe_cload_ondevice.py, which uses the
C-BIOS_MSX1_EU_TAPE machine (zerobas-tape patch) with zerobas loaded as a
cartridge.  The original claim here — that TAPIN "cannot frame a run of
consecutive $00 bytes" — was incorrect.  The actual defect was a register-clobber
in basic/cload.asm's `ctp_line`: TAPIN uses C as its 8-bit bit-counter and always
returns C=0, but the old code stashed link-low in C before calling TAPIN a second
time for link-high.  The result was BC = (link_high, 0) instead of
(link_high, link_low), corrupting the body-length calculation so the load loop
never landed on the $0000 end-link.  The fix (push af / pop af / ld c,a) is in
basic/cload.asm and is verified by basic_probe_cload_ondevice.py (ALL PASS).
The same latent clobber in `dpl_line` (disk program load) was fixed simultaneously.
The zerobas-tape device half is correct and was never the source of the bug.

The functional landmark is a cassette tape load, so this MUST run on
Philips_VG_8020 (C-BIOS does not service tape). See the memory note
"Probe machine = Philips".

Clean-room: this only *constructs inputs and observes outputs*. No disassembly;
the reference ROM is a black box. The tokenised-program image is built from
zerobas's own oracle-sourced crunch rules. See the clean-room firewall (CONTRIBUTING.md).
"""
from __future__ import annotations

# --- zerobas probes: locate shared infra (probes/lib) + sibling probes ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # sibling probes
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib"))  # shared infra

import os
import subprocess
import sys
import tempfile


from cas_encode import build_cas_basic  # noqa: E402

OMSX_RUN = os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "lib", "omsx_run.py")
MACHINE = "Philips_VG_8020"

# zerobas + reference sysvars (TXTTAB and its post-boot $8001 value are shared).
TXTBASE = 0x8001   # stored-program text base
TXTTAB = 0xF676    # sysvar: pointer to the BASIC text base
TAPION = 0x00E1    # cassette: read tape header (crunch-probe landmark)
KBUF = 0xF41F      # reference crunch buffer
TOKBUF = 0xE160    # zerobas crunch buffer
DUMPLEN = 48


def build_program() -> bytes:
    """A two-line tokenised program image: `10 A=5` and `20 B=7`.

    Each line: [link:2 LE][lineno:2 LE][tokens...][00]; the program ends in a
    $0000 link word. Tokens use zerobas's own oracle-sourced crunch:
      A=5  -> 41 EF 16   ('A', '=' $EF, digit 5 -> $11+5 = $16)
      B=7  -> 42 EF 18   ('B', '=' $EF, digit 7 -> $11+7 = $18)
    The saved links are the genuine absolute addresses a real CSAVE writes (from
    TXTBASE), so the tape bytes match a real VG-8020 CSAVE recording byte-for-byte
    (we deliberately avoid $FFFF placeholder links: the FSK framing mangles
    all-ones bytes and a real CSAVE never emits them).
    """
    lines = [
        (10, bytes([0x41, 0xEF, 0x16])),   # 10 A=5
        (20, bytes([0x42, 0xEF, 0x18])),   # 20 B=7
    ]
    prog = bytearray()
    addr = TXTBASE
    sizes = [2 + 2 + len(body) + 1 for _, body in lines]
    for (lineno, body), size in zip(lines, sizes):
        nxt = addr + size
        prog += nxt.to_bytes(2, "little")
        prog += lineno.to_bytes(2, "little")
        prog += body
        prog += b"\x00"
        addr = nxt
    prog += b"\x00\x00"                     # end-of-program link word
    return bytes(prog)


# ---- 1. crunch (byte-identical tokenisation) --------------------------------

def crunch_dump(machine, cart, full_line, addr, separate_enter):
    """Break at TAPION mid-`bload"cas:",r`, return the crunch buffer bytes."""
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="cl_crunch_")
    os.close(out_fd)
    cmd = [sys.executable, OMSX_RUN, "--machine", machine]
    if cart:
        cmd += ["--cart", cart]
    cmd += ["--cassette", CRUNCH_CAS]
    if separate_enter:
        cmd += ["--type", full_line, "--type-delay", "8",
                "--type", "\r", "--type-delay", "12"]
    else:
        cmd += ["--type", full_line + "\r", "--type-delay", "5"]
    cmd += ["--bp", hex(TAPION), "--reg", "PC",
            "--mem", f"memory:0x{addr:04X}:{DUMPLEN}",
            "--out", out_path, "--timeout", "30"]
    subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cap = ""
    if os.path.exists(out_path):
        with open(out_path) as f:
            cap = f.read()
        os.unlink(out_path)
    if f"reg.PC=0x{TAPION:04X}" not in cap:
        return None
    key = f"mem.memory:0x{addr:04X}:{DUMPLEN}="
    for cl in cap.splitlines():
        if cl.startswith(key):
            return bytes.fromhex(cl[len(key):])
    return None


def crunched(buf):
    """The crunched line up to and including its terminator (BLOAD token $CF
    leads in CRUNCH_ONLY mode; the first $00 at/after it is the terminator)."""
    if buf is None or 0xCF not in buf:
        return None
    i = buf.index(0xCF)
    if 0 not in buf[i:]:
        return None
    z = i + buf[i:].index(0)
    return buf[:z + 1]


def crunch_check(cart, body):
    full = f'bload"cas:",r:{body}'   # bload leads; body crunched but never run
    ref = crunched(crunch_dump(MACHINE, None, full, KBUF, separate_enter=False))
    zb = crunched(crunch_dump(MACHINE, cart, full, TOKBUF, separate_enter=True))
    same = ref is not None and zb is not None and ref == zb
    print(f"{'PASS' if same else 'FAIL'}  crunch {body!r}")
    print(f"        ref: {' '.join(f'{b:02X}' for b in ref) if ref else '<no TAPION>'}")
    if not same:
        print(f"        zb : {' '.join(f'{b:02X}' for b in zb) if zb else '<no TAPION>'}")
    return same


# ---- 2. reference loads our synthetic .cas to the expected image ------------

def expected_image(program):
    """Program image as it must appear at TXTBASE after a correct load+relink."""
    lines, i = [], 0
    while int.from_bytes(program[i:i + 2], "little") != 0:
        lineno = int.from_bytes(program[i + 2:i + 4], "little")
        j = i + 4
        while program[j] != 0:
            j += 1
        lines.append((lineno, program[i + 4:j]))
        i = j + 1
    out, addr = bytearray(), TXTBASE
    placed = []
    for lineno, body in lines:
        size = 2 + 2 + len(body) + 1
        placed.append((lineno, body, addr + size))
        addr += size
    for lineno, body, nxt in placed:
        out += nxt.to_bytes(2, "little") + lineno.to_bytes(2, "little") + body + b"\x00"
    out += b"\x00\x00"
    return bytes(out)


def ref_load_check(program):
    cas = build_cas_basic("PROG", program)
    cas_fd, cas_path = tempfile.mkstemp(suffix=".cas", prefix="cload_ref_")
    os.write(cas_fd, cas)
    os.close(cas_fd)
    out_fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="cload_refcap_")
    os.close(out_fd)
    want = expected_image(program)
    cmd = [sys.executable, OMSX_RUN, "--machine", MACHINE, "--cassette", cas_path,
           "--type", "cload\r", "--type-delay", "5", "--time", "30",
           "--mem", f"memory:0x{TXTBASE:04X}:{len(want)}",
           "--out", out_path, "--timeout", "75"]
    subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cap = ""
    if os.path.exists(out_path):
        with open(out_path) as f:
            cap = f.read()
        os.unlink(out_path)
    os.unlink(cas_path)
    key = f"mem.memory:0x{TXTBASE:04X}:{len(want)}="
    got = None
    for line in cap.splitlines():
        if line.startswith(key):
            got = bytes.fromhex(line[len(key):])
    ok = got == want
    print(f"{'PASS' if ok else 'FAIL'}  reference CLOAD loads .cas -> expected image")
    print(f"        want: {want.hex(' ')}")
    print(f"        got : {got.hex(' ') if got else '<no dump>'}")
    return ok


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--machine", default=MACHINE)
    ap.add_argument("--cart", required=True, help="zerobas basic.rom")
    args = ap.parse_args()
    globals()["MACHINE"] = args.machine

    # Shared crunch tape: a tiny freeze blob the bload landmark hands off to.
    global CRUNCH_CAS
    cas = build_cas_basic  # noqa: F841  (keep import live)
    from cas_encode import build_cas
    c = build_cas("TOK", 0xC000, 0xC000, bytes([0x18, 0xFE]))
    cfd, CRUNCH_CAS = tempfile.mkstemp(suffix=".cas", prefix="cl_crunchcas_")
    os.write(cfd, c)
    os.close(cfd)

    ok = True
    print("== crunch: CLOAD/LOAD tokens byte-identical to the VG-8020 ==")
    for body in ["cload", 'cload"name"', 'load"cas:name"', "load", 'load"cas:"']:
        ok &= crunch_check(args.cart, body)
    print("\n== format: reference VG-8020 loads our tokenised-BASIC .cas ==")
    ok &= ref_load_check(build_program())

    os.unlink(CRUNCH_CAS)
    print("\nALL PASS" if ok else "\nSOME FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
