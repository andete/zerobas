#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Tokenise readable BASIC source with OUR OWN ROM crunch — reused, not reimplemented.

Spec: disk/docs/diskbasic-bas-harness-spec.md §5.2 ("the `.bas` source ... reuses
[the] oracle-confirmed tokeniser path, so the program is authored as readable
BASIC text, not hand-assembled token bytes"). This module is the shared helper
that lets a probe author a multi-line `.bas` test program as plain text and get
back the exact bytes our ROM's `tokenise` routine (basic/interp.asm) would
produce for each line — the same routine tests/test_tokenise.py locks in as a
host unit test, and the same one a real MSX keyboard-typed line goes through.

Mechanism (tests/msxtest.py's `Machine`, the pattern tests/test_tokenise.py
uses): assemble basic/main.asm with pasmo to get a ROM image + symbol file,
load both into a flat 64 KB Python model, POKE the ASCII line (0-terminated)
into a scratch RAM address, `call("tokenise", hl=SRC, de=DST)`, and read the
token bytes back out of RAM.

END-POINTER SEMANTICS (verified empirically, not assumed — tk_end in
basic/interp.asm writes the 0x00 terminator via `ld (de),a` withOUT a following
`inc de`, then `ret`): on return, `cpu.de` is the ADDRESS OF the terminator byte
itself, not one past it. So the full token body INCLUDING its own trailing 0x00
is `mem[DST : cpu.de + 1]`. Verified against tools/make_test_dsk.py's
prog_bas_body() fixture for `POKE &HD002,123` -> the tokenise() output here is
byte-identical to that hand-built reference (see disk/docs -- confirmed in the
build log of the probe that uses this module). Do NOT scan for a 0x00
terminator instead: interior token streams legitimately contain 0x00 operand
bytes (e.g. a HEX_TOKEN's zero high byte), which a scan would truncate.

Each line is passed to `tokenise` as the statement BODY ONLY -- the line number
is NOT part of what the ROM tokeniser consumes here; the caller supplies it
separately and `wrap_basic_line` below (mirrors tools/make_test_dsk.py /
disk_probe_autoexec.py's helper of the same name) builds the in-memory
line-link record around it.
"""
from __future__ import annotations

import os
import struct
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
_TESTS = os.path.join(_ROOT, "tests")
if _TESTS not in sys.path:
    sys.path.insert(0, _TESTS)

from msxtest import Machine  # noqa: E402  (path set up above)

BASIC_BASE = 0x2812   # basic/main.asm's org
ROM_PATH = "/tmp/zerobas_basic_bastok.rom"
SYM_PATH = "/tmp/zerobas_basic_bastok.sym"
SRC_ADDR = 0xC000     # scratch: ASCII source line (free RAM in the host model)
DST_ADDR = 0xC100     # scratch: token output buffer

BASIC_DISK_ID = 0xFF  # basic/sysvars.inc: on-disk tokenised-BASIC marker byte


def build_rom(src: str | None = None) -> None:
    """Assemble basic/main.asm (pasmo) so `Tokeniser` below has a fresh ROM.

    pasmo resolves `include` paths (e.g. main.asm's `include "basic/sysvars.inc"`)
    relative to the process CWD, not to the source file -- so the assemble only
    succeeds when CWD is the repo root. Callers invoked from elsewhere (notably
    `make -C tape test`, which runs the regression with CWD=tape/) would otherwise
    get `File 'basic/sysvars.inc' not found` and a non-zero pasmo exit. Pin the
    build's CWD to `_ROOT` so this helper is CWD-independent for every probe."""
    src = src or os.path.join(_ROOT, "basic", "main.asm")
    subprocess.run(["pasmo", "--bin", src, ROM_PATH, SYM_PATH], check=True,
                   capture_output=True, cwd=_ROOT)


class Tokeniser:
    """Wraps a `Machine` loaded with our assembled ROM; `crunch()` tokenises
    one statement body at a time via the real `tokenise` label."""

    def __init__(self):
        build_rom()
        # ⚠️ $2812, and it used to be msxtest.Machine's $4000 DEFAULT -- the retired
        # lean 16 KB cart's org. This module builds basic/main.asm to get a real
        # tokeniser for the disk corpus's .BAS fixtures, so until 2026-07-29 those
        # fixtures were crunched by the LEAN tokeniser. The base is named at the call
        # site now (docs/spec-lean-retire-s3-gates.md §5, F-U).
        self.m = Machine(ROM_PATH, SYM_PATH, rom_base=BASIC_BASE)

    def crunch(self, body_text: str) -> bytes:
        """Tokenise one statement BODY (no line number) -> bytes INCLUDING the
        trailing 0x00 terminator the ROM emits."""
        m = self.m
        m.poke(SRC_ADDR, body_text.encode("ascii") + b"\x00")
        # Sentinel-fill the destination (not 0x00) so a short/garbage write is
        # visible rather than masquerading as an early terminator.
        m.mem[DST_ADDR:DST_ADDR + 256] = b"\xEE" * 256
        m.call("tokenise", hl=SRC_ADDR, de=DST_ADDR)
        end = m.cpu.de                    # address OF the terminator byte
        body = bytes(m.mem[DST_ADDR:end + 1])
        assert body and body[-1] == 0x00, (
            f"tokenise({body_text!r}) did not end in 0x00: {body.hex()}")
        return body


def wrap_basic_line(body: bytes, lineno: int, txtbase: int) -> bytes:
    """Wrap a tokenised statement body into the in-memory line-link record:
    [link:2 LE][lineno:2 LE][body incl. its own 0x00 terminator]. Mirrors
    tools/make_test_dsk.py / disk_probe_autoexec.py's `wrap_basic_line` exactly
    (the link value is a non-zero placeholder; BASIC's relink recomputes it on
    load, so any consistent non-zero choice is a don't-care)."""
    line_len = 4 + len(body)              # link(2) + lineno(2) + body
    link = txtbase + line_len
    return struct.pack("<HH", link, lineno) + body


def make_multiline_program(lines: list[tuple[int, str]], txtbase: int) -> bytes:
    """Tokenise + link MULTIPLE lines into one in-memory program image, ending
    in the final $0000 link (program-end marker). `lines` = [(lineno, body), ...]
    in program order. Each line's link is (this line's start) + its own length,
    i.e. the address of the NEXT line's link word -- the same convention
    wrap_basic_line/relink use, just threaded across lines instead of a single
    line followed directly by the end marker."""
    tk = Tokeniser()
    out = bytearray()
    addr = txtbase
    encoded = []
    for lineno, body_text in lines:
        body = tk.crunch(body_text)
        encoded.append((lineno, body))
    for lineno, body in encoded:
        line_len = 4 + len(body)
        link = addr + line_len
        out += struct.pack("<HH", link, lineno) + body
        addr += line_len
    out += struct.pack("<H", 0x0000)      # end-of-program marker
    return bytes(out)


def make_basic_file(lines: list[tuple[int, str]], txtbase: int) -> bytes:
    """A tokenised-BASIC ON-DISK file: BASIC_DISK_ID ($FF) + the line-link
    program image (basic/cload.asm's disk_prog_load contract)."""
    return bytes([BASIC_DISK_ID]) + make_multiline_program(lines, txtbase)
