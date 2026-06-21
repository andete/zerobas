# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""Unit test: vars.asm — integer variable store + string-type detection.

Tier-1 (pure RAM, no BIOS, no I/O): var_set_key / var_get_key work entirely
in RAM (VARTAB at $E1C0..VAREND $E240), so nothing needs to be stubbed. The
4-byte entry layout [name0][name1][value:2] and the 2-char keying rule are
asserted against the code's own comments and the sysvars.inc constants exported
into the symbol file.

Oracle basis per case group:
- Round-trip / not-found: 4-byte entry layout [name0][name1][value LE] documented
  in vars.asm header; default-0 for unset from var_get_key:vgk_zero.
- 2-char keying: vars.asm header "Names are significant to two characters (public
  MSX-BASIC language reference)"; `SCORE`, `SC`, `SCX` all key to (S,C).
- clear_vars: clears VARTAB region (zero VARSLOTS*VARENTSZ bytes) + STRTAB name0
  slots (STRSLOTS entries, STRENTSZ apart); asserted against code in clear_vars.
- var_str_type: A=1/CF=1 iff `$` suffix follows the identifier; A=0/CF=0 otherwise
  (vars.asm:var_str_type inline comment + vst_yes/pop-hl/xor-a branches).
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine, carry  # noqa: E402

ROM = "/tmp/zb_vars.rom"
SYM = "/tmp/zb_vars.sym"

# Scratch buffers for name strings placed in free RAM clear of the variable tables.
NAMEBUF = 0xC100   # small scratch for variable-name ASCII strings

def build():
    src = os.path.join(ROOT, "basic", "main.asm")
    subprocess.run(["pasmo", "--bin", src, ROM, SYM], check=True,
                   capture_output=True)


def poke_name(m, addr, text):
    """Write a NUL-terminated name string at addr."""
    m.poke(addr, text.encode("ascii") + b"\x00")


def run():
    build()
    m = Machine(ROM, SYM)
    s = m.sym

    VARTAB   = s["VARTAB"]
    VAREND   = s["VAREND"]
    VARENTSZ = s["VARENTSZ"]      # 4
    VARSLOTS = s["VARSLOTS"]      # 32
    STRTAB   = s["STRTAB"]
    STRENTSZ = s["STRENTSZ"]      # 35
    STRSLOTS = s["STRSLOTS"]      # 8

    fails = 0

    # ------------------------------------------------------------------
    # Helper: reset variable tables before each group.
    # ------------------------------------------------------------------
    def reset_tables():
        # Zero VARTAB (numeric): all name0 bytes become 0 → empty slots.
        m.poke(VARTAB, bytes(VARSLOTS * VARENTSZ))
        # Zero STRTAB name0 of every slot (STRENTSZ apart).
        for i in range(STRSLOTS):
            m.poke(STRTAB + i * STRENTSZ, 0)

    # ==================================================================
    # Case 1: round-trip via var_set_key / var_get_key for "A" → 0x1234
    # Key: BC = (ord('A'), 0) — single-char name maps to (name0=A, name1=0)
    # as documented in vars.asm: "name1 the second name char … or 0 for a
    # single-char name".
    # Expected retrieved value: DE = 0x1234.
    # ==================================================================
    reset_tables()
    m.call("var_set_key", b=ord("A"), c=0, de=0x1234)
    cpu = m.call("var_get_key", b=ord("A"), c=0)
    ok = (cpu.de == 0x1234)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  round-trip A=0x1234: got DE={cpu.de:#06x}")

    # ==================================================================
    # Case 2: unset variable returns 0
    # var_get_key:vgk_zero sets DE=0 when var_find returns CF=0 (not found).
    # ==================================================================
    reset_tables()
    cpu = m.call("var_get_key", b=ord("Z"), c=0)
    ok = (cpu.de == 0)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  unset var returns 0: got DE={cpu.de:#06x}")

    # ==================================================================
    # Case 3: 2-char keying — "AB" and "ABC" resolve to the same key (B,'A','B').
    # vars.asm header: "Any 3rd+ name characters … are consumed but ignored,
    # so e.g. SCORE, SC and SCX all map to key (S,C)."
    # Set via key ('A','B'); get via name_key of "ABC": both must see 0x5678.
    # We use var_name_key to parse "ABC" → BC, then var_get_key.
    # ==================================================================
    reset_tables()
    # Set AB = 0x5678 directly by key.
    m.call("var_set_key", b=ord("A"), c=ord("B"), de=0x5678)
    # Parse "ABC\0" with var_name_key → BC should be ('A','B'); HL advanced.
    poke_name(m, NAMEBUF, "ABC")
    cpu_k = m.call("var_name_key", hl=NAMEBUF)
    bc_abc = cpu_k.bc
    cpu = m.call("var_get_key", b=(bc_abc >> 8) & 0xFF, c=bc_abc & 0xFF)
    ok = (cpu.de == 0x5678) and ((bc_abc >> 8) == ord("A")) and ((bc_abc & 0xFF) == ord("B"))
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  'AB' and 'ABC' same key "
          f"(BC={bc_abc:#06x}, DE={cpu.de:#06x})")

    # ==================================================================
    # Case 4: "AB" and "AC" are DISTINCT keys.
    # name1 differs ('B' vs 'C'); var_find checks both name0 and name1.
    # ==================================================================
    reset_tables()
    m.call("var_set_key", b=ord("A"), c=ord("B"), de=0x0001)
    m.call("var_set_key", b=ord("A"), c=ord("C"), de=0x0002)
    # Note: m.call() returns the same cpu object each time; capture .de immediately
    # before making another call that would overwrite the shared register state.
    val_ab = m.call("var_get_key", b=ord("A"), c=ord("B")).de
    val_ac = m.call("var_get_key", b=ord("A"), c=ord("C")).de
    ok = (val_ab == 0x0001) and (val_ac == 0x0002)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  'AB'=1 and 'AC'=2 are distinct "
          f"(AB={val_ab}, AC={val_ac})")

    # ==================================================================
    # Case 5: var_name_key — "A" (single char) produces BC=(A,0); "AB" → (A,B).
    # Oracle: var_name_key header "B = name0 (upcased), C = name1 … or 0 for
    # a single-char name".
    # ==================================================================
    poke_name(m, NAMEBUF, "A")
    cpu_a = m.call("var_name_key", hl=NAMEBUF)
    ok_a = ((cpu_a.bc >> 8) == ord("A")) and ((cpu_a.bc & 0xFF) == 0)
    fails += not ok_a
    print(f"{'PASS' if ok_a else 'FAIL'}  var_name_key 'A' → BC={cpu_a.bc:#06x} "
          f"(want {(ord('A')<<8):#06x})")

    poke_name(m, NAMEBUF, "AB")
    cpu_ab2 = m.call("var_name_key", hl=NAMEBUF)
    ok_ab = ((cpu_ab2.bc >> 8) == ord("A")) and ((cpu_ab2.bc & 0xFF) == ord("B"))
    fails += not ok_ab
    print(f"{'PASS' if ok_ab else 'FAIL'}  var_name_key 'AB' → BC={cpu_ab2.bc:#06x} "
          f"(want {(ord('A')<<8|ord('B')):#06x})")

    # ==================================================================
    # Case 6: clear_vars resets the numeric table and string-slot name0 bytes.
    # After storing variables, clear_vars should zero VARTAB..VAREND and
    # zero name0 of every STRTAB slot.
    # Oracle: clear_vars code zeros VARSLOTS*VARENTSZ bytes starting at VARTAB
    # and then steps STRENTSZ bytes per slot setting name0=0.
    # ==================================================================
    reset_tables()
    m.call("var_set_key", b=ord("X"), c=0, de=0xABCD)
    m.call("var_set_key", b=ord("Y"), c=0, de=0x1111)
    # Also dirty a STRTAB name0 slot manually.
    m.poke(STRTAB, ord("A"))
    m.call("clear_vars")
    # After clear, var_get_key for X and Y must return 0.
    # Note: m.call() returns the shared cpu object; capture .de before the next call.
    val_x = m.call("var_get_key", b=ord("X"), c=0).de
    val_y = m.call("var_get_key", b=ord("Y"), c=0).de
    # STRTAB slot 0 name0 must be 0 (freed).
    strtab_name0 = m.mem[STRTAB]
    ok = (val_x == 0) and (val_y == 0) and (strtab_name0 == 0)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  clear_vars resets tables "
          f"(X={val_x}, Y={val_y}, STRTAB[0].name0={strtab_name0})")

    # Also verify that the first byte of VARTAB is 0 (name0 cleared).
    vt_name0 = m.mem[VARTAB]
    ok2 = (vt_name0 == 0)
    fails += not ok2
    print(f"{'PASS' if ok2 else 'FAIL'}  clear_vars VARTAB[0]=0 (got {vt_name0})")

    # ==================================================================
    # Case 7: var_str_type — '$'-suffixed name → A=1, CF=1.
    # Plain name → A=0, CF=0. HL is NOT advanced by var_str_type.
    # Oracle: var_str_type code comment "A = 1 if a `$` suffix follows …
    # CF = the A==1 condition is also reflected".
    # ==================================================================
    # String variable name "A$"
    poke_name(m, NAMEBUF, "A$")
    cpu_s = m.call("var_str_type", hl=NAMEBUF)
    ok_str = (cpu_s.a == 1) and carry(cpu_s)
    fails += not ok_str
    print(f"{'PASS' if ok_str else 'FAIL'}  var_str_type 'A$' → A={cpu_s.a}, CF={int(carry(cpu_s))}")

    # Integer variable name "A" (no $)
    poke_name(m, NAMEBUF, "A")
    cpu_i = m.call("var_str_type", hl=NAMEBUF)
    ok_int = (cpu_i.a == 0) and not carry(cpu_i)
    fails += not ok_int
    print(f"{'PASS' if ok_int else 'FAIL'}  var_str_type 'A' → A={cpu_i.a}, CF={int(carry(cpu_i))}")

    # Multi-char string variable "AB$"
    poke_name(m, NAMEBUF, "AB$")
    cpu_abs = m.call("var_str_type", hl=NAMEBUF)
    ok_abs = (cpu_abs.a == 1) and carry(cpu_abs)
    fails += not ok_abs
    print(f"{'PASS' if ok_abs else 'FAIL'}  var_str_type 'AB$' → A={cpu_abs.a}, CF={int(carry(cpu_abs))}")

    # ==================================================================
    # Case 8: var_get / var_set single-letter shims (used by FOR/READ).
    # Contract: A = single-letter name; DE = value for set. Maps to key
    # (upcase(A), 0), interoperable with var_set_key/var_get_key.
    # Oracle: var_get/var_set header "A = name (one char). Map to key
    # (upcased name, 0) — identical to the key a 1-char name produces via
    # var_name_key, so single-letter variables set here are fully interoperable".
    # ==================================================================
    reset_tables()
    m.call("var_set", a=ord("a"), de=0x7777)   # lowercase 'a' → upcased to 'A'
    cpu_g = m.call("var_get", a=ord("A"))
    ok_shim = (cpu_g.de == 0x7777)
    fails += not ok_shim
    print(f"{'PASS' if ok_shim else 'FAIL'}  var_set/var_get shim 'a'→'A'=0x7777: DE={cpu_g.de:#06x}")

    # Cross-check: var_set_key (B='A', C=0) and var_get (A='A') see the same cell.
    reset_tables()
    m.call("var_set_key", b=ord("A"), c=0, de=0x3333)
    cpu_cross = m.call("var_get", a=ord("A"))
    ok_cross = (cpu_cross.de == 0x3333)
    fails += not ok_cross
    print(f"{'PASS' if ok_cross else 'FAIL'}  var_set_key(A,0)+var_get('A') interop: DE={cpu_cross.de:#06x}")

    print()
    print("ALL PASS — vars.asm integer store + type detection" if not fails
          else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
