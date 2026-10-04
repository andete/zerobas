# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: the keyboard line editor `read_line` (repl.asm + sub/readline.asm), no emulator.

Tier-2: CHGET is trapped to feed a scripted key sequence, CHPUT is captured to
check the echo AND applied to a fake 40x24 screen at the cursor cells (CSRY/CSRX,
the documented work area), RDVRM is trapped to read that screen back. Since
D-SCREDIT (docs/spec-basic-screditor.md) Enter reads the LOGICAL LINE under the
cursor out of VRAM -- a typo fixed with cursor-left lands in the buffer, a line
that wraps (LINTTB marks the continuation) reads back whole -- so the buffer is
what the SCREEN shows, not the keystrokes.

Oracle: the references (both agree on every gated row of screditor-acceptance);
here the fake screen models what C-BIOS's CHPUT does with each byte.
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
BASIC_BASE = 0x2765

ROM = tp("zb_repl.rom")
SYM = tp("zb_repl.sym")


def build():
    src = os.path.join(ROOT, "basic", "main.asm")
    subprocess.run(["pasmo", "--bin", src, ROM, SYM], check=True,
                   capture_output=True)


COLS, ROWS = 40, 24


def feed(m, keys):
    """Drive read_line with a scripted key stream over a fake screen; return
    (LINEBUF bytes, echo)."""
    seq = list(keys)
    st = {"i": 0}
    screen = bytearray(b" " * (COLS * ROWS))
    sym = m.sym
    # the work-area cells the tenant reads: cursor at row 1 col 1, WIDTH 40,
    # 24 rows, SCREEN 0, name table at 0, every row ends a line, no AUTO
    m.poke(sym["CSRY"], b"\x01"); m.poke(sym["CSRX"], b"\x01")
    m.poke(sym["LINLEN"], bytes([COLS])); m.poke(sym["CRTCNT"], bytes([ROWS]))
    m.poke(sym["SCRMOD"], b"\x00"); m.poke_w(sym["NAMBAS"], 0)
    m.poke(sym["LINTTB"], b"\x01" * ROWS); m.poke(sym["RL_AUTO"], b"\x00")

    def chget(mm):
        mm.cpu.a = seq[st["i"]]
        st["i"] += 1

    echo = []

    def chput(mm):
        """What C-BIOS does with the byte: move the cursor or write the screen."""
        a = mm.cpu.a
        echo.append(a)
        y, x = mm.mem[sym["CSRY"]], mm.mem[sym["CSRX"]]
        if a == 13: x = 1
        elif a == 10 or a == 0x1F: y = min(ROWS, y + 1)
        elif a == 8 or a == 0x1D: x = max(1, x - 1)
        elif a == 0x1C: x += 1
        elif a == 0x1E: y = max(1, y - 1)
        elif a >= 32:
            if x > COLS:                       # the pending wrap: a new row, marked as a continuation
                mm.mem[sym["LINTTB"] + y - 1] = 0
                y, x = y + 1, 1
            screen[(y - 1) * COLS + x - 1] = a
            x += 1
        mm.mem[sym["CSRY"]], mm.mem[sym["CSRX"]] = y, x

    def rdvrm(mm):
        mm.cpu.a = screen[mm.cpu.hl]

    def chsns(mm):
        """ZF set = nothing waiting: main's read_line polls this before each key."""
        if st["i"] < len(seq): mm.cpu.f &= ~0x40
        else: mm.cpu.f |= 0x40

    m.trap("CHGET", chget)
    m.trap("CHSNS", chsns)
    m.trap("CHPUT", chput)
    m.trap("RDVRM", rdvrm)
    m.call("read_line")
    base = m.sym["LINEBUF"]
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

    # DEL ($7F) deletes the character UNDER the cursor (D-INSMODE, Joost:
    # "Faithful DEL" -- it was erase-left, for the Mac Backspace key, since
    # June). At the end of `AB` there is nothing under the cursor: `AB` stays.
    case("'AB' <del>", b"AB\x7F\r", b"AB")

    # Backspace at the start of the line is a no-op (nothing to erase).
    case("<bs> 'X'", b"\x08X\r", b"X")

    # Sub-$20 control chars (other than BS/DEL/Enter) are ignored.
    case("'A' <ctrl-A> 'B'", b"A\x01B\r", b"AB")

    # Empty line: just Enter -> empty buffer, CR/LF echo only.
    case("just Enter", b"\r", b"", b"\r\n")

    # D-SCREDIT: a typo fixed with cursor-left is what the SCREEN shows -- A=2,
    # not A=12 (the cursor byte reaches CHPUT and the row is read back).
    case("'A=1' <left> '2'", b"A=1\x1d2\r", b"A=2", b"A=1\x1d2\r\n")

    # D-SCREDIT: a line that wraps reads back WHOLE -- the continuation mark the
    # wrap leaves in LINTTB joins the two rows into one logical line.
    case("45 chars, wrapped", b"x" * 45 + b"\r", b"x" * 45)

    print()
    print("ALL PASS — read_line edits/echoes per the documented editor contract"
          if not fails else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
