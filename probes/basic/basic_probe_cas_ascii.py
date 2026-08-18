#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Cassette ASCII CLOAD / LOAD"CAS:" probe (M1 of spec-cas-ascii-saveload.md).

zerobas gained the ability to load an ASCII cassette program (header id $EA,
line-numbered text terminated by Ctrl-Z, in fixed 256-byte data blocks) in
addition to the tokenised ($D3) format, via a 256-byte block-buffered tape byte
source behind ascii_read_lines (basic/cload.asm cas_ascii_load/cal_getbyte/
cal_refill + the ARL_GETBYTE getbyte indirection in basic/files.asm).

Three assertions:

  1. REAL-TAPE LOAD ORACLE (a genuine third-party artifact, [[readonly-artifact-
     oracle]]).  HARDBOIL.CAS -- a real 5-line ASCII loader tape found under
     ~/Documents/msx/msx -- is loaded with LOAD"CAS:" and the tokenised image at
     TXTBASE ($8001) is asserted byte-identical to tokenising its known source
     text (via bas_tokenise, our own ROM crunch).  This proves interop with a
     tape zerobas did not produce.  (The tape is COPIED to a temp dir first;
     openMSX can write back to a mounted .cas, so the ~/Documents originals are
     never touched.)

  2. MULTI-BLOCK SYNTHETIC (>256 bytes).  A 25-line ASCII program (>256 text
     bytes => TWO 256-byte tape blocks) is built as an $EA .cas and loaded,
     asserting the full tokenised image -- this exercises the block-2 refill
     (mid-tape TAPION re-lock) that a single-block tape does not.

  3. NO REGRESSION on the tokenised path.  A tokenised ($D3) multi-line program
     still CLOADs byte-identically (the $D3 branch of the 3-way header dispatch).

Typed harness on the repack machine (C-BIOS_MSX1_EU_REPACK_DISK), which carries
the merged main ROM in slot 0 and its own <CassettePort/>, so no cartridge is
inserted. Until 2026-07-29 this ran the retired lean 16 KB cart as a `-cart` on
C-BIOS_MSX1_EU_TAPE (docs/spec-lean-retire-s3-gates.md); that rig is still
selectable with --machine C-BIOS_MSX1_EU_TAPE + --cart, and is the only mode
in which --cart means anything.
reference ROM is never read, and reading the ASCII *data* bytes of a real .cas
is not a ROM read.
"""
from __future__ import annotations

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))       # sibling probes
_PROBES = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))  # probes/
_ROOT = _os.path.dirname(_PROBES)                                       # repo root
_sys.path.insert(0, _os.path.join(_PROBES, "lib"))                     # cas codec + omsx
_sys.path.insert(0, _os.path.join(_PROBES, "disk"))                    # bas_tokenise

import argparse
import glob
import os
import shutil
import signal
import struct
import subprocess
import tempfile
import time

from cas_encode import build_cas_basic, CAS_SYNC  # noqa: E402
from bas_tokenise import Tokeniser, make_multiline_program  # noqa: E402
from omsx_run import _tcl_dquote  # noqa: E402
# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(
    _zbo.path.dirname(_zbo.path.abspath(__file__))), "lib"))
import omsx_preflight  # noqa: E402

OMSX = os.environ.get("OPENMSX") or shutil.which("openmsx") or "/opt/homebrew/bin/openmsx"
MACHINE_TAPE = "C-BIOS_MSX1_EU_TAPE"
# The zerobas side runs on the REPACK machine, which carries the merged main ROM
# in slot 0 and ships its own <CassettePort/>. It used to be MACHINE_TAPE below --
# stock C-BIOS plus the tape patch -- with the retired lean 16 KB cart inserted as
# a cartridge (RETIRE THE LEAN 16 KB CART S3, docs/spec-lean-retire-s3-gates.md).
# MACHINE_TAPE is kept because it is still a real rig: stock BIOS + open cassette
# stack, selectable via --machine / ZEROBAS_BASIC_MACHINE, and the only mode in
# which a `-cart` is passed at all.
ZB_MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE") or "C-BIOS_MSX1_EU_REPACK_DISK"
TXTBASE = 0x8001
ASCII_ID = 0xEA

# The real ASCII loader tape used as the load oracle, and its KNOWN source text
# (read off the tape's ASCII data block; reading data bytes is not a ROM read).
HARDBOIL_LINES = [
    (1, 'POKE&HFBB0,1:POKE&HFBB1,1:KEYOFF:SCREEN0:WIDTH 40:COLOR15,1,1'),
    (3, 'LOCATE14,9:PRINT"HARD BOILED'),
    (5, 'LOCATE4,18:PRINT"Copyright 1987 Methodic Solutions"'),
    (6, 'BLOAD"cas:",R'),
    (7, 'BLOAD"cas:",R'),
]


def find_hardboil() -> str | None:
    """Locate HARDBOIL.CAS under the user's MSX tape collection."""
    base = os.path.expanduser("~/Documents/msx/msx")
    for path in glob.glob(os.path.join(base, "**", "*.[cC][aA][sS]"), recursive=True):
        if os.path.basename(path).upper() == "HARDBOIL.CAS":
            return path
    return None


def build_ascii_cas(name: str, source_lines: list[str]) -> bytes:
    """Build an $EA ASCII cassette image: header block (SYNC + 10x $EA + 6-char
    name) then fixed 256-byte data blocks of `<line>\\r\\n...` + Ctrl-Z EOF, each
    block padded to 256 with $1A (the spec-faithful producer padding, §0.1)."""
    body = b"".join(ln.encode("ascii") + b"\r\n" for ln in source_lines)
    body += bytes([0x1A])
    pad = ((len(body) + 255) // 256) * 256
    body = body.ljust(pad, b"\x1A")
    buf = bytearray()
    buf += CAS_SYNC
    buf += bytes([ASCII_ID] * 10)
    buf += name[:6].ljust(6).encode("ascii")
    for off in range(0, len(body), 256):
        buf += CAS_SYNC
        buf += body[off:off + 256]
    return bytes(buf)


def load_capture_txt(cart: str, cas_path: str, nbytes: int, verb: str,
                     cap_time: float = 35.0, timeout: float = 120.0) -> str | None:
    """Mount `cas_path`, type `verb` + ENTER, capture `nbytes` from TXTBASE as hex."""
    out = tempfile.mktemp(suffix=".txt", prefix="casascii_")
    tcl = f"""set throttle off
set renderer none
set sound_driver null
proc __hex {{a n}} {{ binary scan [debug read_block {{memory}} $a $n] H* h; return $h }}
after time 6 {{ type {_tcl_dquote(verb)} }}
after time 8 {{ type {_tcl_dquote(chr(13))} }}
proc __cap {{}} {{
  set f [open {{{out}}} w]
  puts $f "txt=[__hex 0x{TXTBASE:04X} {nbytes}]"
  close $f
  exit
}}
after time {cap_time} {{ __cap }}
"""
    tcl_path = out + ".tcl"
    open(tcl_path, "w").write(tcl)
    if os.path.exists(out):
        os.unlink(out)
    cmd = [OMSX, "-machine", ZB_MACHINE]
    cmd += (["-cart", cart] if ZB_MACHINE == MACHINE_TAPE else [])
    cmd += [
           "-cassetteplayer", cas_path, "-script", tcl_path]
    proc = subprocess.Popen(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        time.sleep(0.1)
    if proc.poll() is None:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    if os.path.exists(out):
        for ln in open(out):
            k, _, v = ln.strip().partition("=")
            if k == "txt":
                return v
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cart", default=None,
                    help="only used with the %s rig" % MACHINE_TAPE)
    args = ap.parse_args()

    ok = True
    tmp = tempfile.mkdtemp(prefix="casascii_")

    # --- Assertion 1: real-tape load oracle (HARDBOIL.CAS) ----------------------
    print("Assertion 1 — real-tape ASCII load oracle (HARDBOIL.CAS):")
    src = find_hardboil()
    if src is None:
        print("  [SKIP] HARDBOIL.CAS not found under ~/Documents/msx/msx")
    else:
        # COPY to temp first -- never let openMSX write back to ~/Documents.
        cas = os.path.join(tmp, "HARDBOIL.CAS")
        shutil.copy(src, cas)
        expect = make_multiline_program(HARDBOIL_LINES, TXTBASE)
        got = load_capture_txt(args.cart, cas, len(expect) + 8, 'LOAD"CAS:"')
        c1 = got is not None and got.startswith(expect.hex())
        ok &= c1
        print(f"  [{'PASS' if c1 else 'FAIL'}] LOAD\"CAS:\" of a real 5-line ASCII "
              f"tape matches the tokenised image")
        if not c1:
            print(f"        expect: {expect.hex()}")
            print(f"        got:    {got}")

    # --- Assertion 2: multi-block synthetic (>256 bytes, 2 tape blocks) --------
    print("Assertion 2 — multi-block ASCII load (>256 bytes -> 2 tape blocks):")
    big_lines = [(n, f"PRINT{n}") for n in range(10, 260, 10)]     # 25 lines
    big_src = [f"{n} PRINT{n}" for n, _ in big_lines]
    text_len = sum(len(s) + 2 for s in big_src) + 1               # +CRLF each +Ctrl-Z
    cas = os.path.join(tmp, "big.cas")
    open(cas, "wb").write(build_ascii_cas("BIG", big_src))
    expect = make_multiline_program(big_lines, TXTBASE)
    got = load_capture_txt(args.cart, cas, len(expect) + 8, 'LOAD"CAS:"',
                           cap_time=45.0)
    c2 = got is not None and got.startswith(expect.hex())
    ok &= c2
    print(f"  [{'PASS' if c2 else 'FAIL'}] {len(big_lines)}-line ({text_len}-byte, "
          f"{(text_len + 255) // 256} blocks) ASCII program loads byte-identical")
    if not c2:
        print(f"        expect: {expect.hex()}")
        print(f"        got:    {got}")

    # --- Assertion 3: tokenised path still loads (no regression on $D3) --------
    print("Assertion 3 — tokenised CLOAD still loads (no $D3-path regression):")
    tok_lines = [(10, "PRINT1"), (20, "PRINT2"), (30, "PRINT3")]
    prog = make_multiline_program(tok_lines, TXTBASE)
    cas = os.path.join(tmp, "tok.cas")
    open(cas, "wb").write(build_cas_basic("TOK", prog))
    got = load_capture_txt(args.cart, cas, len(prog) + 4, "CLOAD")
    c3 = got is not None and got.startswith(prog.hex())
    ok &= c3
    print(f"  [{'PASS' if c3 else 'FAIL'}] tokenised 3-line CLOAD unchanged")
    if not c3:
        print(f"        expect: {prog.hex()}")
        print(f"        got:    {got}")

    # --- Assertion 4: 4-block ASCII load (>768 bytes -> 4 tape blocks), with -----
    # lines dense enough to genuinely exercise the read-ahead margin -------------
    # A minimal-baud-agnostic "PRINTn"-style synthetic (assertion 2's shape) does
    # NOT reproduce the bug this guards: uniform short lines tokenise fast enough
    # that even a single-buffer refill-on-drain keeps up. The regression this
    # caught (docs/spec-cas-ascii-saveload.md) needed REAL program-shaped lines --
    # nested parens, IF/AND/OR, multi-statement colons -- whose tokenise cost is
    # high enough that a block boundary landing mid-line (or mid-CRLF) lets the
    # tape's own real-time playback outrun a too-shallow read-ahead.
    #
    # This is not an invented worst case: it is modelled directly on the ACTUAL
    # 21-line, 867-byte, 4-block program that surfaced the bug (a small MSX1
    # Snake game -- the parens/AND/colon-dense IF lines below are its own,
    # verbatim), which genuinely truncated after line 50 with no read-ahead at
    # all and after line 110 under a single-buffer refill-on-drain (one block's
    # tokenise cost late). (One line of the original, `DEFINT A-Z`, is left out
    # here: it hits an unrelated, pre-existing tokeniser discrepancy between the
    # bas_tokenise oracle and the runtime -- a separate bug, not this one -- so
    # keeping it out of this assertion's content keeps a FAIL here unambiguous.)
    # Deliberately denser synthetics (packing maximal complexity into every one
    # of 20 lines, ~1300 bytes / 6 blocks) can still outrun even this double
    # buffer -- that is a real, separate robustness ceiling (arbitrarily heavy
    # tokenise work will always eventually outrun a FIXED read-ahead depth), not
    # a regression of the bug this test guards. Keeping this assertion at the
    # bug's own reported density, rather than an open-ended harder one, is what
    # makes it a faithful regression guard instead of a moving target.
    print("Assertion 4 — 4-block ASCII load (>768 bytes, real-program density):")
    complex_lines = [
        (10, 'SCREEN0:WIDTH40:KEYOFF:DIMBX(255),BY(255)'),
        (20, 'FORI=0TO39:VPOKEI,35:VPOKE920+I,35:NEXT'),
        (30, 'FORI=1TO22:VPOKEI*40,35:VPOKEI*40+39,35:NEXT'),
        (40, 'X=20:Y=12:DX=1:DY=0:H=0:T=0:VPOKEY*40+X,79:BX(0)=X:BY(0)=Y'),
        (50, 'GOSUB200'),
        (60, 'S=STICK(0):IFSTHENGOSUB300'),
        (70, 'NX=X+DX:NY=Y+DY:C=VPEEK(NY*40+NX)'),
        (80, 'IFC=42THENG=1ELSEIFC=32THENG=0ELSE500'),
        (90, 'X=NX:Y=NY:VPOKEY*40+X,79:H=(H+1)AND255:BX(H)=X:BY(H)=Y'),
        (100, 'IFGTHENGOSUB200:GOTO60'),
        (110, 'VPOKEBY(T)*40+BX(T),32:T=(T+1)AND255:GOTO60'),
        (200, 'FX=INT(RND(1)*38)+1:FY=INT(RND(1)*22)+1:IFVPEEK(FY*40+FX)<>32THEN200'),
        (210, 'VPOKEFY*40+FX,42:RETURN'),
        (300, 'ONSGOTO310,320,320,320,330,340,340,340'),
        (310, 'QX=0:QY=-1:GOTO350'),
        (320, 'QX=1:QY=0:GOTO350'),
        (330, 'QX=0:QY=1:GOTO350'),
        (340, 'QX=-1:QY=0'),
        (350, 'IF(H<>T)AND(QX=-DX)AND(QY=-DY)THENRETURN'),
        (360, 'DX=QX:DY=QY:RETURN'),
        (500, 'LOCATE15,11:PRINT"GAME OVER":END'),
    ]
    complex_src = [f"{n} {s}" for n, s in complex_lines]
    ctext_len = sum(len(s) + 2 for s in complex_src) + 1           # +CRLF each +Ctrl-Z
    cblocks = (ctext_len + 255) // 256
    cas = os.path.join(tmp, "complex4.cas")
    open(cas, "wb").write(build_ascii_cas("CPLX4", complex_src))
    expect = make_multiline_program(complex_lines, TXTBASE)
    got = load_capture_txt(args.cart, cas, len(expect) + 8, 'LOAD"CAS:"',
                           cap_time=60.0)
    c4 = got is not None and got.startswith(expect.hex())
    ok &= c4
    print(f"  [{'PASS' if c4 else 'FAIL'}] {len(complex_lines)}-line ({ctext_len}-byte, "
          f"{cblocks} blocks) ASCII program loads byte-identical")
    if cblocks < 4:
        print(f"        WARNING: only {cblocks} blocks -- widen complex_lines so this "
              f"stays a >=4-block (>768 byte) case")
    if not c4:
        print(f"        expect: {expect.hex()}")
        print(f"        got:    {got}")

    shutil.rmtree(tmp, ignore_errors=True)
    print("CAS-ASCII:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
