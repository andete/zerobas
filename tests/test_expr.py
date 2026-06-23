# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: BASIC-ROM `eval` (16-bit integer expression evaluator), no emulator.

`eval` (basic/expr.asm) is a pure Tier-1 routine for arithmetic and
relational cases; VPEEK and INP are Tier-2 (they call RDVRM / IN-instruction).

Calling convention (from expr.asm header comment + call sites in poke.asm etc.):
  IN:  HL = cursor into the crunched token stream
  OUT: DE = 16-bit result, HL advanced past the expression
  CLOBBERS: A, BC
  ERROR: ERRMARK ($E010) set to $DD on div-by-zero / expression error.

Strategy: for pure-math, relational, and logical cases we feed `tokenise` the
ASCII expression, then call `eval` on the resulting token buffer — exactly as
PRINT/POKE/LET do. For VPEEK/INP we build the token stream by hand (the $FF-
prefixed function tokens are two bytes; the argument is parenthesised).

Expected values are justified by:
  - pure arithmetic (all math results are independently derivable)
  - MSX-BASIC language contract: TRUE = -1 (0xFFFF), FALSE = 0
    (MSX2 Technical Handbook §2, integer expressions and comparisons)
  - bitwise NOT on 16-bit words: NOT 0 = 0xFFFF (ones-complement)
  - zerobas documented div-by-zero contract: result = 0, ERRMARK = 0xDD
    (expr.asm, div_zero label and surrounding comment)
  - RDVRM BIOS contract: read VRAM address in HL -> result in A
    (MSX2 Technical Handbook BIOS call list / MSX Assembly Page)
  - Z80 IN instruction contract: reads the port in BC -> result in A
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

ROM = "/tmp/zb_eval.rom"
SYM = "/tmp/zb_eval.sym"
SRC = 0xC000          # ASCII expression source (free RAM, above ROM)
TOKBUF = 0xC100       # token output buffer for tokenise
ERRMARK_ADDR = 0xE010 # ERRMARK sysvar (from sysvars.inc)


def build():
    src = os.path.join(ROOT, "basic", "main.asm")
    subprocess.run(["pasmo", "--bin", src, ROM, SYM], check=True,
                   capture_output=True)


def tokenise_expr(m, text):
    """Crunch an ASCII expression into TOKBUF; return the start address."""
    m.poke(SRC, text.encode("ascii") + b"\x00")
    m.mem[TOKBUF:TOKBUF + 64] = b"\x00" * 64
    m.call("tokenise", hl=SRC, de=TOKBUF)
    return TOKBUF


def eval_expr(m, text):
    """Tokenise an ASCII expression and evaluate it; return (de_result, errmark)."""
    # Clear ERRMARK before each call so each test is independent.
    m.mem[ERRMARK_ADDR] = 0x00
    tok = tokenise_expr(m, text)
    cpu = m.call("eval", hl=tok)
    return cpu.de, m.mem[ERRMARK_ADDR]


def eval_tokens(m, token_bytes):
    """Evaluate a pre-built token stream (list of bytes); return (de_result, errmark)."""
    m.mem[ERRMARK_ADDR] = 0x00
    m.poke(TOKBUF, bytes(token_bytes) + b"\x00")
    cpu = m.call("eval", hl=TOKBUF)
    return cpu.de, m.mem[ERRMARK_ADDR]


def run():
    build()
    m = Machine(ROM, SYM)
    s = m.sym

    # Convenience: token constants from the symbol file, so if sysvars.inc changes
    # the test stays in sync.
    PLUS   = s["PLUS_TOKEN"]      # $F1
    MINUS  = s["MINUS_TOKEN"]     # $F2
    STAR   = s["STAR_TOKEN"]      # $F3
    EQ     = s["EQ_TOKEN"]        # $EF
    GT     = s["GT_TOKEN"]        # $EE
    LT     = s["LT_TOKEN"]        # $F0
    AND    = s["AND_TOKEN"]       # $F6
    OR     = s["OR_TOKEN"]        # $F7
    XOR    = s["XOR_TOKEN"]       # $F8
    NOT    = s["NOT_TOKEN"]       # $E0
    IDIV   = s["IDIV_TOKEN"]      # $FC
    DIV    = s["DIV_TOKEN"]       # $F4
    MOD    = s["MOD_TOKEN"]       # $FB
    DIG    = s["INT_DIGIT_BASE"]  # $11; DIG+n = digit n (0..9)
    INT1   = s["INT1_TOKEN"]      # $0F; followed by 1 byte
    INT2   = s["INT2_TOKEN"]      # $1C; followed by 2 bytes LE
    HEX    = s["HEX_TOKEN"]       # $0C; followed by 2 bytes LE
    OCT    = s["OCT_TOKEN"]       # $0B; followed by 2 bytes LE
    VPEEK  = s["VPEEK_TOKEN"]     # $98
    INP    = s["INP_TOKEN"]       # $90
    FFPFX  = s["PEEK_PREFIX"]     # $FF (function-token prefix)
    ERRMARK_VAL = 0xDD            # zerobas documented error marker (expr.asm div_zero)
    TRUE16 = 0xFFFF               # MSX-BASIC truth value = -1 unsigned 16-bit

    cases = []  # (description, got, want, errmark_got, errmark_want)

    # -------------------------------------------------------------------------
    # Group 1: Arithmetic & precedence
    # Oracle basis: pure mathematics.
    # -------------------------------------------------------------------------
    for text, want in [
        ("2+3*4",     14),   # * binds tighter: 2 + (3*4) = 14
        ("(2+3)*4",   20),   # grouping: 5 * 4 = 20
        ("10-3-2",     5),   # left-associative: (10-3)-2 = 5
    ]:
        got, em = eval_expr(m, text)
        cases.append((text, got, want, em, 0))

    # 7\2 = 3: integer divide (floor quotient, unsigned, per expr.asm ev_idiv comment)
    # Oracle: 7 / 2 = 3 remainder 1; zerobas uses unsigned 16-bit integer divide.
    got, em = eval_expr(m, r"7\2")
    cases.append((r"7\2", got, 3, em, 0))

    # 7 MOD 3 = 1: remainder (pure math)
    got, em = eval_expr(m, "7 MOD 3")
    cases.append(("7 MOD 3", got, 1, em, 0))

    # -------------------------------------------------------------------------
    # Group 2: Unary minus
    # Oracle: two's-complement 16-bit negation: -N = 65536 - N.
    # -------------------------------------------------------------------------
    # -5: 0 - 5 = 65531 = 0xFFFB
    got, em = eval_expr(m, "-5")
    cases.append(("-5", got, 0xFFFB, em, 0))

    # 3 * (-2): unary minus in factor position (ev_f_neg, then mul16)
    # 3 * (0 - 2) = 3 * 65534 mod 65536 = 196602 mod 65536 = 65530 = 0xFFFA = -6
    got, em = eval_expr(m, "3*-2")
    cases.append(("3*-2", got, 0xFFFA, em, 0))

    # -------------------------------------------------------------------------
    # Group 3: Hex/octal literals
    # Oracle: numeric identity (&HFF = 255, &H10 = 16, &O17 octal = 15 decimal).
    # -------------------------------------------------------------------------
    got, em = eval_expr(m, "&HFF")
    cases.append(("&HFF",  got, 255, em, 0))

    got, em = eval_expr(m, "&H10")
    cases.append(("&H10",  got, 16, em, 0))

    # &O17: octal 17 = 1*8 + 7 = 15 (pure math)
    got, em = eval_expr(m, "&O17")
    cases.append(("&O17",  got, 15, em, 0))

    # -------------------------------------------------------------------------
    # Group 4: Signed 16-bit comparisons
    # Oracle: MSX-BASIC language contract — TRUE = -1 (0xFFFF), FALSE = 0
    # (MSX2 Technical Handbook §2, integer comparisons). Signed compare because
    # cmp16_bits uses SBC HL,DE and tests S ^ V (signed less-than).
    # -------------------------------------------------------------------------
    for text, want in [
        ("5>3",    TRUE16),   # 5 greater than 3 -> true
        ("3>5",    0),        # 3 not greater than 5 -> false
        ("5=5",    TRUE16),   # equal -> true
        ("5<3",    0),        # 5 not less than 3 -> false
        ("5<=5",   TRUE16),   # 5 <= 5 -> true (combined LT|EQ tokens)
        ("5>=3",   TRUE16),   # 5 >= 3 -> true
        ("5<>5",   0),        # 5 <> 5 -> false (not-equal via LT|GT bits)
        ("-1<0",   TRUE16),   # signed: -1 (0xFFFF) < 0 -> true (proves signed compare)
    ]:
        got, em = eval_expr(m, text)
        cases.append((text, got, want, em, 0))

    # -------------------------------------------------------------------------
    # Group 5: Logical / bitwise operators on -1/0 operands
    # Oracle: bitwise NOT/AND/OR/XOR on 16-bit words; with -1=0xFFFF and 0=0x0000
    # these are also the logical operators on truth values.
    # NOT 0 = ones-complement of 0x0000 = 0xFFFF = -1  (pure bitwise)
    # -------------------------------------------------------------------------
    got, em = eval_expr(m, "NOT 0")
    cases.append(("NOT 0", got, TRUE16, em, 0))

    # (1=1) AND (2=2): TRUE AND TRUE = 0xFFFF AND 0xFFFF = 0xFFFF
    got, em = eval_expr(m, "(1=1)AND(2=2)")
    cases.append(("(1=1)AND(2=2)", got, TRUE16, em, 0))

    # (1=1) OR (1=2): TRUE OR FALSE = 0xFFFF OR 0x0000 = 0xFFFF
    got, em = eval_expr(m, "(1=1)OR(1=2)")
    cases.append(("(1=1)OR(1=2)", got, TRUE16, em, 0))

    # (1=1) XOR (1=1): TRUE XOR TRUE = 0xFFFF XOR 0xFFFF = 0x0000 = false
    got, em = eval_expr(m, "(1=1)XOR(1=1)")
    cases.append(("(1=1)XOR(1=1)", got, 0, em, 0))

    # -------------------------------------------------------------------------
    # Group 6: Division by zero
    # Oracle: zerobas documented contract (expr.asm, div_zero label):
    #   "Division by zero yields 0 and sets ERRMARK (no crash)"
    #   ERRMARK = $DD (same $DD as ev_f_err)
    # -------------------------------------------------------------------------
    got, em = eval_expr(m, "5/0")
    cases.append(("5/0 result=0",   got, 0,           em, ERRMARK_VAL))
    # Verify ERRMARK separately for clarity.
    cases.append(("5/0 ERRMARK",    em,  ERRMARK_VAL, 0,  0))

    # -------------------------------------------------------------------------
    # Group 7: VPEEK (Tier-2) — stub RDVRM
    # RDVRM BIOS contract (MSX2 Technical Handbook / MSX Assembly Page):
    #   IN: HL = VRAM address
    #   OUT: A = byte read from VRAM
    # expr.asm ev_ff_vpeek: EX DE,HL; CALL RDVRM; E = A; D = 0.
    # Token stream for VPEEK(&H1234):
    #   $FF $98 '(' $0C $34 $12 ')' $00
    # -------------------------------------------------------------------------
    rdvrm_calls = []
    def stub_rdvrm(machine):
        # Record the HL passed to RDVRM, then return 0x5A in A.
        rdvrm_calls.append(machine.cpu.hl)
        machine.cpu.a = 0x5A
    m.trap("RDVRM", stub_rdvrm)

    # Build VPEEK(&H1234) token stream by hand:
    #   FFPFX VPEEK_TOKEN '(' HEX_TOKEN <0x34> <0x12> ')' terminator
    vpeek_toks = [FFPFX, VPEEK, ord('('), HEX, 0x34, 0x12, ord(')')]
    got, em = eval_tokens(m, vpeek_toks)
    # Verify result = 0x5A (the stub returned value, zero-extended to 16 bits)
    # Oracle: VPEEK yields 0..255 (expr.asm: D=0, E=A); stub returns 0x5A.
    cases.append(("VPEEK(&H1234) result", got, 0x5A, em, 0))
    # Verify RDVRM was called with HL = 0x1234
    vpeek_hl_ok = (len(rdvrm_calls) == 1 and rdvrm_calls[0] == 0x1234)
    cases.append(("VPEEK RDVRM HL=0x1234", int(vpeek_hl_ok), 1, 0, 0))

    # -------------------------------------------------------------------------
    # Group 8: INP (Tier-2) — stub the Z80 IN instruction via cpu.io_in
    # INP(port) contract (MSX-BASIC language reference): read one byte from
    # Z80 I/O port. expr.asm ev_ff_inp: BC = DE (port), IN A,(C), E = A, D = 0.
    # The Z80 core uses cpu.io_in(port) -> byte for IN A,(C).
    # Oracle: INP yields 0..255; stub returns 0x5A; port = &HAB = 171.
    # Token stream for INP(&HAB):
    #   $FF $90 '(' $0C $AB $00 ')' $00
    # -------------------------------------------------------------------------
    inp_calls = []
    def stub_io_in(port):
        inp_calls.append(port)
        return 0x5A
    m.cpu.io_in = stub_io_in

    # INP(&HAB): port = 0x00AB (low byte 0xAB, high byte 0x00)
    inp_toks = [FFPFX, INP, ord('('), HEX, 0xAB, 0x00, ord(')')]
    got, em = eval_tokens(m, inp_toks)
    cases.append(("INP(&HAB) result", got, 0x5A, em, 0))
    # Verify the port number: ev_ff_inp does BC = DE, then IN A,(C).
    # The Z80 core calls io_in(port) where port is the full 16-bit BC value.
    # BC = 0x00AB so port = 0x00AB = 171.
    inp_port_ok = (len(inp_calls) == 1 and inp_calls[0] == 0x00AB)
    cases.append(("INP port=0x00AB", int(inp_port_ok), 1, 0, 0))

    # -------------------------------------------------------------------------
    # Print results
    # -------------------------------------------------------------------------
    fails = 0
    for desc, got, want, em_got, em_want in cases:
        # For ERRMARK sub-rows (em_want=0 means "don't check em separately")
        # we already folded em into the 'got' / 'want' columns where needed.
        val_ok = (got == want)
        # For div-by-zero rows, also check ERRMARK:
        em_ok = (em_got == em_want) if em_want != 0 else True
        ok = val_ok and em_ok
        fails += not ok
        tag = "PASS" if ok else "FAIL"
        extra = ""
        if not val_ok:
            extra = f"  want {want:#06x} got {got:#06x}"
        if not em_ok:
            extra += f"  ERRMARK want {em_want:#04x} got {em_got:#04x}"
        print(f"{tag}  {desc!r}{extra}")

    print()
    if not fails:
        print("ALL PASS — eval matches arithmetic/relational/logical/BIOS contracts")
    else:
        print(f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
