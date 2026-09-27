# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
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
from _tmp import tp
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine, carry  # noqa: E402

# The image under test is loaded at its ORG. Named here rather than
# defaulted: msxtest.Machine's old default was $4000, the retired lean
# cart's org, so a BASIC test that omitted it silently tested the lean
# build (docs/spec-lean-retire-s3-gates.md §5, F-U).
BASIC_BASE = 0x2812

ROM = tp("zb_vars.rom")
SYM = tp("zb_vars.sym")

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
    m = Machine(ROM, SYM, rom_base=BASIC_BASE)
    s = m.sym

    # ⚠️ THIS TEST NO LONGER DRIVES var_set_key / var_get_key, AND THAT IS THE
    # WHOLE POINT OF THE PORT. Those two (and var_find beneath them) walk the
    # fixed 32-slot VARTAB pool, which vars.asm itself calls "the LEAN build's
    # int-only 4-byte-stride walk". On the shipped build they have ZERO callers:
    # scalars live in the contiguous chain the ARY sub-ROM tenant manages (arrays
    # slice-4b), reached through var_store_fac / var_load_fac keyed on
    # (name0, name1, TYPE). Driving the pool here asserted a store nothing writes
    # to and nothing reads from -- it only ever passed because msxtest.Machine's
    # rom_base defaulted to $4000 and this was therefore the LEAN image
    # (docs/spec-lean-retire-s3-gates.md §5, F-U). STRTAB is gone outright.
    #
    # The KEYING rules under test are unchanged, so every case below asserts the
    # same property against the store the shipped build actually uses.
    TYPE_INT = 2                  # VARTYPE: 2/4/8 = int16/single/double, 1 = string
    DEFTBL_STR = s["DEFTBL_STR"]  # the DEFtbl's STRING code (namespace P), read
                                  # from the image rather than hardcoded: it has
                                  # moved once already (1 -> 3, D-DEFSTR)

    fails = 0

    def reset_tables():
        """A fresh scalar chain.

        clear_vars deliberately does NOT wipe it -- vars.asm §13a: PRGEND may still
        be garbage when clear_vars runs at cold boot, so each caller resets the
        scalar+array region ITSELF afterwards via vars_reset. new_prog is the
        caller that establishes PRGEND and then tail-jumps to vars_reset."""
        m.poke_w(s["POOLSIZE"], 200)   # cold-boot default (interp.asm init)
        m.call("new_prog")

    def set_key(b, c, value):
        """Store `value` as an int16 scalar under key (b, c)."""
        m.poke(s["FACTYP"], 2)         # DE carries a plain int16
        m.call("var_store_fac", b=b, c=c, a=TYPE_INT, de=value)

    def get_key(b, c):
        """Read the int16 scalar under key (b, c); 0 if unset."""
        return m.call("var_load_fac", b=b, c=c, a=TYPE_INT).de

    # ==================================================================
    # Case 1: round-trip via var_set_key / var_get_key for "A" → 0x1234
    # Key: BC = (ord('A'), 0) — single-char name maps to (name0=A, name1=0)
    # as documented in vars.asm: "name1 the second name char … or 0 for a
    # single-char name".
    # Expected retrieved value: DE = 0x1234.
    # ==================================================================
    reset_tables()
    set_key(ord("A"), 0, 0x1234)
    got1 = get_key(ord("A"), 0)
    ok = (got1 == 0x1234)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  round-trip A=0x1234: got DE={got1:#06x}")

    # ==================================================================
    # Case 2: unset variable returns 0
    # var_get_key:vgk_zero sets DE=0 when var_find returns CF=0 (not found).
    # ==================================================================
    reset_tables()
    got2 = get_key(ord("Z"), 0)
    ok = (got2 == 0)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  unset var returns 0: got DE={got2:#06x}")

    # ==================================================================
    # Case 3: 2-char keying — "AB" and "ABC" resolve to the same key (B,'A','B').
    # vars.asm header: "Any 3rd+ name characters … are consumed but ignored,
    # so e.g. SCORE, SC and SCX all map to key (S,C)."
    # Set via key ('A','B'); get via name_key of "ABC": both must see 0x5678.
    # We use var_name_key to parse "ABC" → BC, then var_get_key.
    # ==================================================================
    reset_tables()
    # Set AB = 0x5678 directly by key.
    set_key(ord("A"), ord("B"), 0x5678)
    # Parse "ABC\0" with var_name_key → BC should be ('A','B'); HL advanced.
    poke_name(m, NAMEBUF, "ABC")
    cpu_k = m.call("var_name_key", hl=NAMEBUF)
    bc_abc = cpu_k.bc
    got3 = get_key((bc_abc >> 8) & 0xFF, bc_abc & 0xFF)
    ok = (got3 == 0x5678) and ((bc_abc >> 8) == ord("A")) and ((bc_abc & 0xFF) == ord("B"))
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  'AB' and 'ABC' same key "
          f"(BC={bc_abc:#06x}, DE={got3:#06x})")

    # ==================================================================
    # Case 4: "AB" and "AC" are DISTINCT keys.
    # name1 differs ('B' vs 'C'); var_find checks both name0 and name1.
    # ==================================================================
    reset_tables()
    set_key(ord("A"), ord("B"), 0x0001)
    set_key(ord("A"), ord("C"), 0x0002)
    val_ab = get_key(ord("A"), ord("B"))
    val_ac = get_key(ord("A"), ord("C"))
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
    # Case 6: clear_vars + vars_reset drop every scalar.
    #
    # ⚠️ IT TAKES BOTH CALLS, AND THAT IS THE CONTRACT, NOT A WORKAROUND.
    # clear_vars alone does NOT clear the scalar chain on the shipped build --
    # vars.asm §13a: at cold boot clear_vars runs BEFORE new_prog establishes
    # PRGEND, so wiping the chain there would write through a garbage pointer.
    # Every clear_vars caller therefore resets the region itself afterwards
    # (init -> new_prog -> vars_reset; RUN; CLEAR). Asserting clear_vars alone
    # would assert a wipe the shipped build deliberately does not do there.
    # ==================================================================
    reset_tables()
    set_key(ord("X"), 0, 0xABCD)
    set_key(ord("Y"), 0, 0x1111)
    live_x = get_key(ord("X"), 0)          # two-sided: they were really set...
    m.call("clear_vars")
    m.call("vars_reset")
    val_x = get_key(ord("X"), 0)           # ...and are really gone afterwards
    val_y = get_key(ord("Y"), 0)
    ok = (live_x == 0xABCD) and (val_x == 0) and (val_y == 0)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  clear_vars+vars_reset drops scalars "
          f"(X was {live_x:#06x}, now X={val_x}, Y={val_y})")

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
    # Case 8: for_name / for_get / for_set — the FOR frame's loop variable.
    # These were var_get/var_set, single-letter shims taking ONE upcased char in
    # A. D-FORVAR (docs/spec-basic-forvar.md §4.3/§4.5) retired the shim: both
    # references match a NEXT on the loop variable's WHOLE identity -- both
    # significant name characters AND the resolved type (row n.xtype) -- so the
    # key arrives whole in FOR_CUR and for_name is what parses it.
    #
    # 🔴 THE KEY IS [name1][name0][type], NOT [name0][name1][type]. `LD (nn),BC`
    # writes C first and var_name_key returns B = name0, so this IS the layout --
    # and it is asserted here rather than assumed, because the slice's first
    # draft put the bare-NEXT sentinel on the wrong byte and only three of 33
    # emulator rows could see it. name1 is 0 for every single-character name,
    # which is exactly why it cannot be the byte a 0 sentinel lives in.
    # ==================================================================
    def for_key(name0, name1, vtype):
        m.poke(s["FOR_CUR"], name1)
        m.poke(s["FOR_CUR"] + 1, name0)
        m.poke(s["FOR_CUR"] + 2, vtype)

    reset_tables()
    poke_name(m, NAMEBUF, "ab%=1")
    cpu_fn = m.call("for_name", hl=NAMEBUF)
    got_key = bytes(m.peek(s["FOR_CUR"], 3))
    want_key = bytes([ord("B"), ord("A"), TYPE_INT])   # name1, name0, type
    ok_fn = (got_key == want_key
             and cpu_fn.hl == NAMEBUF + 3       # past "ab%", stopped at '='
             and cpu_fn.a == TYPE_INT)
    fails += not ok_fn
    print(f"{'PASS' if ok_fn else 'FAIL'}  for_name 'ab%' → FOR_CUR="
          f"{got_key.hex()} (want {want_key.hex()}: name1,name0,type), "
          f"HL+{cpu_fn.hl - NAMEBUF}, A={cpu_fn.a}")

    # A `$` name resolves to DEFTBL_STR, and THAT is what makes `NEXT A$` match no
    # frame at all (spec §4.2). It is unit-tested here because the cell itself is
    # what carries the rule -- a screen row can only see the consequence.
    reset_tables()
    poke_name(m, NAMEBUF, "a$=1")
    cpu_fs = m.call("for_name", hl=NAMEBUF)
    ok_fs = (cpu_fs.a == DEFTBL_STR
             and m.peek(s["FOR_CUR"] + 2)[0] == DEFTBL_STR)
    fails += not ok_fs
    print(f"{'PASS' if ok_fs else 'FAIL'}  for_name 'a$' → type={cpu_fs.a} "
          f"(want DEFTBL_STR={DEFTBL_STR}, NOT 8 — a `$` name is not a double)")

    # Round-trip through the frame key, single-char name at the DEFtbl default.
    reset_tables()
    for_key(ord("A"), 0, 8)                    # clear_vars leaves every letter DOUBLE
    # D-FORFLOAT: for_set now stores the value AS eval LEFT IT -- FACTYP
    # included -- and forces int16 only for a `%` loop variable. Every value
    # below is an int literal, which eval leaves with FACTYP = 2; say so,
    # rather than inheriting whatever an earlier case left in FACTYP (the
    # first run read 0x7777 for BOTH names off a stale FAC).
    def for_set_int(de):
        m.poke(s["FACTYP"], 2)
        return m.call("for_set", de=de)

    for_set_int(0x7777)
    cpu_g = m.call("for_get")
    ok_shim = (cpu_g.de == 0x7777)
    fails += not ok_shim
    print(f"{'PASS' if ok_shim else 'FAIL'}  for_set/for_get round-trip "
          f"'A'=0x7777: DE={cpu_g.de:#06x}")

    # A 2-CHARACTER loop variable is a different cell from its first letter --
    # the whole point of the slice, and invisible to the case above.
    reset_tables()
    for_key(ord("A"), ord("B"), 8)
    for_set_int(0x1111)
    for_key(ord("A"), 0, 8)
    for_set_int(0x2222)
    for_key(ord("A"), ord("B"), 8)
    ab = m.call("for_get").de
    for_key(ord("A"), 0, 8)
    a1 = m.call("for_get").de
    ok_two = (ab == 0x1111 and a1 == 0x2222)
    fails += not ok_two
    print(f"{'PASS' if ok_two else 'FAIL'}  'AB' and 'A' are distinct loop "
          f"variables: AB={ab:#06x}, A={a1:#06x}")

    # ...and so is the same NAME at a different TYPE, which is what n.xtype says
    # the reference matches on.
    reset_tables()
    for_key(ord("A"), 0, TYPE_INT)
    for_set_int(0x0444)
    for_key(ord("A"), 0, 8)
    for_set_int(0x0555)
    for_key(ord("A"), 0, TYPE_INT)
    ai = m.call("for_get").de
    for_key(ord("A"), 0, 8)
    ad = m.call("for_get").de
    ok_typed = (ai == 0x0444 and ad == 0x0555)
    fails += not ok_typed
    print(f"{'PASS' if ok_typed else 'FAIL'}  'A%' and 'A#' are distinct loop "
          f"variables: A%={ai:#06x}, A#={ad:#06x}")

    # Cross-check: a keyed store and the frame key see the SAME cell.
    # ⚠️ var_find_typed keys on (name, TYPE), so the keyed store has to use the
    # same type or the two address different entries and the read-back is an
    # unset 0 rather than a loud failure.
    reset_tables()
    m.poke(s["FACTYP"], 2)
    m.call("var_store_fac", b=ord("A"), c=0, a=8, de=0x3333)   # 8 = DOUBLE default
    for_key(ord("A"), 0, 8)
    cpu_cross = m.call("for_get")
    ok_cross = (cpu_cross.de == 0x3333)
    fails += not ok_cross
    print(f"{'PASS' if ok_cross else 'FAIL'}  keyed store + for_get('A') interop: DE={cpu_cross.de:#06x}")

    print()
    print("ALL PASS — vars.asm scalar store + type detection" if not fails
          else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
