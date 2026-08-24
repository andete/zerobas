# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: the keyboard line editor `read_line` (repl.asm), no emulator.

Tier-2: CHGET is trapped to feed a scripted key sequence, CHPUT is captured to
check the echo. read_line edits keystrokes into LINEBUF (0-terminated) with
Backspace ($08) / DEL ($7F) erase and Enter ($0D) to finish; sub-$20 control
characters are ignored.

Oracle: the documented editor behaviour in repl.asm (erase-left on $08/$7F,
ignore other control chars, terminate on Enter with a CR/LF echo). The buffer
contents are the typed printable characters; the echo is those characters then
CR,LF.
"""

import os
from _tmp import tp
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

# The image under test is loaded at its ORG. Named here rather than
# defaulted: msxtest.Machine's old default was $4000, the retired lean
# cart's org, so a BASIC test that omitted it silently tested the lean
# build (docs/spec-lean-retire-s3-gates.md §5, F-U).
BASIC_BASE = 0x2812

ROM = tp("zb_repl.rom")
SYM = tp("zb_repl.sym")


def build():
    src = os.path.join(ROOT, "basic", "main.asm")
    subprocess.run(["pasmo", "--bin", src, ROM, SYM], check=True,
                   capture_output=True)


def feed(m, keys):
    """Drive read_line with a scripted key stream; return (LINEBUF bytes, echo)."""
    seq = list(keys)
    st = {"i": 0}

    def chget(mm):
        mm.cpu.a = seq[st["i"]]
        st["i"] += 1

    m.trap("CHGET", chget)
    echo = m.capture_chput()
    m.call("read_line")
    base = m.sym["LINEBUF"]
    # read LINEBUF up to its 0 terminator
    end = base
    while m.mem[end] != 0:
        end += 1
    return bytes(m.mem[base:end]), bytes(echo)


def run():
    build()
    m = Machine(ROM, SYM, rom_base=BASIC_BASE)
    fails = 0

    def case(label, keys, want_buf, want_echo=None):
        nonlocal fails
        buf, echo = feed(m, keys)
        ok = buf == want_buf and (want_echo is None or echo == want_echo)
        fails += not ok
        extra = "" if ok else f"  want buf={want_buf!r}" + (
            f" echo={want_echo!r} got echo={echo!r}" if want_echo is not None else "")
        print(f"{'PASS' if ok else 'FAIL'}  {label}: buf={buf!r}{extra}")

    # Plain line: types into LINEBUF, echoes the chars then CR/LF.
    case("type 'HELLO'", b"HELLO\r", b"HELLO", b"HELLO\r\n")

    # Backspace ($08) erases the previous char (echo: back/space/back per erase).
    case("'AB' <bs> 'C'", b"AB\x08C\r", b"AC")

    # DEL ($7F) is also erase-left (Mac Backspace via C-BIOS).
    case("'AB' <del>", b"AB\x7F\r", b"A")

    # Backspace at the start of the line is a no-op (nothing to erase).
    case("<bs> 'X'", b"\x08X\r", b"X")

    # Sub-$20 control chars (other than BS/DEL/Enter) are ignored.
    case("'A' <ctrl-A> 'B'", b"A\x01B\r", b"AB")

    # Empty line: just Enter -> empty buffer, CR/LF echo only.
    case("just Enter", b"\r", b"", b"\r\n")

    print()
    print("ALL PASS — read_line edits/echoes per the documented editor contract"
          if not fails else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
