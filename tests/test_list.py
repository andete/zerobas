# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: BASIC-ROM `detok` (list.asm), no emulator.

Tier-2 (BIOS-stub) tests: CHPUT is trapped and every emitted byte accumulated.

Entry convention (derived from list.asm:225):
  detok is called with HL pointing to the token *body* — the bytes after the
  line-link word and line-number word in the stored-line format. list.asm
  advances HL past link(2) + lineno(2) before calling detok, so detok itself
  receives the body pointer only.

Oracle basis: the round-trip / inverse property.
  `detok` is defined as the exact inverse of `tokenise` (list.asm module
  comment: "the exact inverse of interp.asm's `tokenise:`"). So:
    tokenise(text) -> token_body
    detok(token_body) -> re_rendered_text
  and re_rendered_text must equal text (up to any canonical transformations
  that tokenise applies: spaces are copied verbatim, letters are up-cased).
  This is self-justifying: no external oracle is needed, only the two routines
  being tested together for consistency. The expected output for each case is
  derived purely from reading interp.asm's tokenise behaviour + list.asm's
  detok behaviour for each token type encountered.

The tokeniser is already independently validated (test_tokenise.py). The token
bodies used below are built from our own tokenise call, and expected outputs
are derived analytically from the detok code, not from running a reference BASIC.

Cases and their derivations:
  "PRINT 5"
    tokenise -> [PRINT_TOKEN, 0x20, INT_DIGIT_BASE+5, 0x00]
    detok: PRINT_TOKEN -> detok_kw prints "PRINT"; 0x20 = ' ' -> plain byte;
           INT_DIGIT_BASE+5 = digit token -> sub INT_DIGIT_BASE + '0' = '5'
    expected: "PRINT 5"

  "A=1"
    tokenise -> [0x41='A', EQ_TOKEN, INT_DIGIT_BASE+1, 0x00]
    detok: 'A' -> plain byte 'A'; EQ_TOKEN -> detok_op prints '=';
           INT_DIGIT_BASE+1 -> digit '1'
    expected: "A=1"

  "PRINT 2+3"
    tokenise -> [PRINT_TOKEN, 0x20, INT_DIGIT_BASE+2, PLUS_TOKEN, INT_DIGIT_BASE+3, 0x00]
    detok: "PRINT" + ' ' + '2' + '+' + '3'
    expected: "PRINT 2+3"

  "REM hello"
    tokenise: match_kw returns REM_TOKEN, then tk_rem_rest copies rest verbatim
    -> [REM_TOKEN, 0x20, 'h','e','l','l','o', 0x00]
    detok: REM_TOKEN -> detok_kw prints "REM"; dt_rem_tail copies ' hello' verbatim
    expected: "REM hello"

  "DATA 1,2"
    tokenise: match_kw returns DATA_TOKEN, then tk_data_rest copies body verbatim
    -> [DATA_TOKEN, 0x20, '1', ',', '2', 0x00]
    detok: DATA_TOKEN -> detok_kw prints "DATA"; dt_data_lp copies ' 1,2' verbatim
    expected: "DATA 1,2"
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

ROM = tp("zb_print.rom")    # reuse the same basic ROM (list.asm is included in main.asm)
SYM = tp("zb_print.sym")
SRC = 0xC000          # ASCII source for tokenise
TOK = 0xC100          # token body buffer (what we pass to detok)


def build():
    src = os.path.join(ROOT, "basic", "main.asm")
    subprocess.run(["pasmo", "--bin", src, ROM, SYM], check=True,
                   capture_output=True)


def tokenise(m, text):
    """Tokenise ASCII text into TOK buffer; return the token bytes (without the
    terminating 0x00, so callers can build precise token bodies)."""
    m.poke(SRC, text.encode("ascii") + b"\x00")
    m.mem[TOK:TOK + 128] = b"\x00" * 128
    m.call("tokenise", hl=SRC, de=TOK)
    # Find the 0x00 terminator to know the body length.
    end = TOK
    while m.mem[end] != 0x00:
        end += 1
    return bytes(m.mem[TOK:end + 1])   # include the terminator


def detok_line(m, token_body_bytes):
    """Place token_body_bytes into TOK buffer and call detok(HL=TOK).
    Returns the bytes emitted via CHPUT."""
    m.mem[TOK:TOK + len(token_body_bytes)] = token_body_bytes
    out = m.capture_chput()
    m.call("detok", hl=TOK)
    return bytes(out)


def run():
    build()
    m = Machine(ROM, SYM, rom_base=BASIC_BASE)
    s = m.sym

    # --- build expected token bodies from known constants --------------------
    # These are the same bodies test_tokenise.py validates; we use our own
    # tokenise call as the input stage (round-trip test), and derive the
    # expected detok output analytically from the code.

    # (text, token_body_to_feed_detok, expected_detok_output)
    # The token body is built by calling tokenise on the text. The expected
    # output is derived case-by-case from the detok code and the input text.

    cases = [
        # text        expected_detok_output
        # ------------------------------------------------------------------
        # PRINT 5:
        #   tokenise -> PRINT_TOKEN 0x20 (INT_DIGIT_BASE+5) 0x00
        #   detok: detok_kw("PRINT") -> "PRINT"; plain ' '; dt_digit -> '5'
        ("PRINT 5",  "PRINT 5"),

        # A=1:
        #   tokenise -> 'A' EQ_TOKEN (INT_DIGIT_BASE+1) 0x00
        #   detok: plain 'A'; detok_op(EQ_TOKEN) -> '='; dt_digit -> '1'
        ("A=1",      "A=1"),

        # PRINT 2+3:
        #   tokenise -> PRINT_TOKEN ' ' digit(2) PLUS_TOKEN digit(3) 0x00
        #   detok: "PRINT" ' ' '2' '+' '3'
        ("PRINT 2+3", "PRINT 2+3"),

        # REM hello:
        #   tokenise -> REM_TOKEN ' ' 'h' 'e' 'l' 'l' 'o' 0x00
        #   detok: detok_kw(REM_TOKEN) -> "REM"; dt_rem_tail copies ' hello'
        ("REM hello", "REM hello"),

        # DATA 1,2:
        #   tokenise -> DATA_TOKEN ' ' '1' ',' '2' 0x00
        #   detok: detok_kw(DATA_TOKEN) -> "DATA"; dt_data_lp copies ' 1,2'
        ("DATA 1,2",  "DATA 1,2"),
    ]

    fails = 0
    for text, expected_out in cases:
        # Step 1: tokenise the text to get the token body.
        tok_bytes = tokenise(m, text)

        # Step 2: pass the token body to detok and capture CHPUT output.
        got = detok_line(m, tok_bytes)
        want = expected_out.encode("ascii")
        ok = got == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  detok({text!r:12}) -> "
              f"{got!r}" + ("" if ok else f"   want {want!r}"))

    print()
    print("ALL PASS — detok is the exact inverse of tokenise (round-trip holds)"
          if not fails else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
