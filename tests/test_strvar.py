# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: strvar.asm — string-value layer (str_eval, print_strval) +
   the string-variable store from vars.asm (str_set_key, str_get_key).

Tier-1 (str_set_key / str_get_key / str_eval): pure RAM — no BIOS, no I/O.
Tier-2 (print_strval): CHPUT is trapped; contract "output the char in A at the
cursor" (MSX Assembly Page / MSX2 TH). We capture every emitted A value.

Oracle basis per case group:
- str_set_key / str_get_key round-trip: entry layout [name0][name1][len][bytes]
  at STRTAB; str_get_key returns HL -> len field; strvar.asm "str_get_key:
  returns HL pointing at the entry's len byte (a valid [len][bytes] descriptor)".
- str_eval literal: strvar.asm str_eval_lit "copy the literal's bytes into STRSCR
  as a [len][bytes] descriptor … advancing HL past the closing quote"; STRPTR set
  to STRSCR; VALTYP = 1; CF = 1 on success. Expected bytes = ASCII of "HELLO".
- str_eval variable path: STRPTR points into STRTAB descriptor after str_get_key;
  VALTYP = 1; CF = 1.
- print_strval: reads STRPTR (set by str_eval), emits each byte via CHPUT (MSX
  Assembly Page BIOS entry $00A2 "output the char in A"). Expected = b"HELLO".
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

# Free scratch RAM for input tokens / name strings.
TOKBUF  = 0xC100   # token/ASCII operand buffer (clear of VARTAB/STRTAB)
NAMEBUF = 0xC200   # variable-name scratch


def build():
    src = os.path.join(ROOT, "basic", "main.asm")
    subprocess.run(["pasmo", "--bin", src, ROM, SYM], check=True,
                   capture_output=True)


def poke_name(m, addr, text):
    m.poke(addr, text.encode("ascii") + b"\x00")


def run():
    build()
    m = Machine(ROM, SYM)
    s = m.sym

    STRTAB   = s["STRTAB"]
    STRENTSZ = s["STRENTSZ"]   # 35 = 3 header + 32 bytes
    STRMAX   = s["STRMAX"]     # 32
    STRSLOTS = s["STRSLOTS"]   # 8
    STRSCR   = s["STRSCR"]     # scratch descriptor for literals
    STRPTR   = s["STRPTR"]     # pointer word -> active descriptor
    VALTYP   = s["VALTYP"]     # 0=numeric, 1=string

    fails = 0

    # Helper: clear STRTAB slot name0 bytes so each test starts fresh.
    def reset_strtab():
        for i in range(STRSLOTS):
            m.poke(STRTAB + i * STRENTSZ, 0)

    # ==================================================================
    # Case 1: str_set_key / str_get_key round-trip for key ('A','$'→0).
    # The `$` suffix selects the string store (caller's job); the key
    # itself is (name0='A', name1=0) for a single-char name (same 2-char
    # rule as numeric variables). We build a [len][bytes] source descriptor
    # in RAM and drive str_set_key with DE = ptr to that descriptor.
    # Oracle: strvar.asm "str_get_key: returns HL pointing at the entry's
    # len byte (a valid [len][bytes] descriptor)".
    # ==================================================================
    reset_strtab()
    HELLO = b"HELLO"
    # Build source descriptor at TOKBUF: [5]["HELLO"]
    m.poke(TOKBUF, bytes([len(HELLO)]) + HELLO)
    # str_set_key: BC = key ('A', 0); DE = TOKBUF (source descriptor).
    m.call("str_set_key", b=ord("A"), c=0, de=TOKBUF)
    # str_get_key: BC = key → HL = [len][bytes] in STRTAB.
    cpu = m.call("str_get_key", b=ord("A"), c=0)
    desc_addr = cpu.hl
    got_len   = m.mem[desc_addr]
    got_bytes = bytes(m.mem[desc_addr + 1 : desc_addr + 1 + got_len])
    ok = (got_len == len(HELLO)) and (got_bytes == HELLO)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  str_set/get_key 'A'='HELLO': "
          f"len={got_len}, bytes={got_bytes!r}")

    # ==================================================================
    # Case 2: str_get_key for an unset key returns STR_EMPTY (len=0).
    # Oracle: strvar.asm "sgk_empty: ld hl,STR_EMPTY — len-0 descriptor".
    # ==================================================================
    reset_strtab()
    cpu_empty = m.call("str_get_key", b=ord("Z"), c=0)
    desc_empty = cpu_empty.hl
    empty_len  = m.mem[desc_empty]
    ok_empty = (empty_len == 0)
    fails += not ok_empty
    print(f"{'PASS' if ok_empty else 'FAIL'}  str_get_key unset → empty descriptor "
          f"(len={empty_len}, HL={desc_empty:#06x}, STR_EMPTY={s['STR_EMPTY']:#06x})")

    # ==================================================================
    # Case 3: str_set_key clamps long strings to STRMAX bytes.
    # Oracle: strvar.asm "Length is clamped to STRMAX (own-design truncation)".
    # STRMAX = 32.
    # ==================================================================
    reset_strtab()
    LONG = b"X" * (STRMAX + 10)   # 42 bytes > STRMAX
    m.poke(TOKBUF, bytes([len(LONG)]) + LONG)
    m.call("str_set_key", b=ord("B"), c=0, de=TOKBUF)
    cpu_c = m.call("str_get_key", b=ord("B"), c=0)
    clamped_len = m.mem[cpu_c.hl]
    ok_clamp = (clamped_len == STRMAX)
    fails += not ok_clamp
    print(f"{'PASS' if ok_clamp else 'FAIL'}  str_set_key clamps to STRMAX={STRMAX}: "
          f"stored len={clamped_len}")

    # ==================================================================
    # Case 4: str_eval of a quoted literal "HELLO".
    # We place the operand `"HELLO"` as ASCII in TOKBUF (including quotes).
    # str_eval_lit reads past the opening '"', copies bytes into STRSCR as a
    # [len][bytes] descriptor, and sets STRPTR = STRSCR, VALTYP = 1, CF = 1.
    # Oracle: strvar.asm str_eval_lit inline comments + STRSCR/STRPTR/VALTYP sysvars.
    # Expected: STRSCR[0] = 5, STRSCR[1..5] = b"HELLO".
    # ==================================================================
    # Clear VALTYP and STRPTR first.
    m.poke(VALTYP, 0)
    m.poke_w(STRPTR, 0)
    m.poke(STRSCR, bytes(1 + STRMAX))    # clear scratch
    lit_text = b'"HELLO"\x00'            # NUL-terminated operand
    m.poke(TOKBUF, lit_text)
    cpu_ev = m.call("str_eval", hl=TOKBUF)
    val_valtyp = m.mem[VALTYP]
    val_strptr = m.mem[STRPTR] | (m.mem[STRPTR + 1] << 8)
    desc_len   = m.mem[val_strptr]
    desc_bytes = bytes(m.mem[val_strptr + 1 : val_strptr + 1 + desc_len])
    ok_eval = (carry(cpu_ev) and val_valtyp == 1
               and val_strptr == STRSCR
               and desc_len == 5 and desc_bytes == b"HELLO")
    fails += not ok_eval
    print(f"{'PASS' if ok_eval else 'FAIL'}  str_eval '\"HELLO\"': CF={int(carry(cpu_ev))}, "
          f"VALTYP={val_valtyp}, STRPTR={val_strptr:#06x}(STRSCR={STRSCR:#06x}), "
          f"len={desc_len}, bytes={desc_bytes!r}")

    # ==================================================================
    # Case 5: str_eval of a string variable (A$) after str_set_key.
    # We store "WORLD" under key ('A',0), then point str_eval at "A$\0".
    # str_eval detects is_letter+var_str_type → calls var_name_key (BC=key)
    # → str_get_key (HL→descriptor in STRTAB) → STRPTR = that addr, VALTYP=1.
    # Oracle: strvar.asm str_eval variable path inline comments.
    # ==================================================================
    reset_strtab()
    WORLD = b"WORLD"
    m.poke(TOKBUF, bytes([len(WORLD)]) + WORLD)
    m.call("str_set_key", b=ord("A"), c=0, de=TOKBUF)

    m.poke(VALTYP, 0)
    m.poke_w(STRPTR, 0)
    poke_name(m, NAMEBUF, "A$")
    cpu_vev = m.call("str_eval", hl=NAMEBUF)
    val_valtyp2 = m.mem[VALTYP]
    val_strptr2 = m.mem[STRPTR] | (m.mem[STRPTR + 1] << 8)
    desc_len2   = m.mem[val_strptr2]
    desc_bytes2 = bytes(m.mem[val_strptr2 + 1 : val_strptr2 + 1 + desc_len2])
    ok_vev = (carry(cpu_vev) and val_valtyp2 == 1
              and desc_len2 == len(WORLD) and desc_bytes2 == WORLD)
    fails += not ok_vev
    print(f"{'PASS' if ok_vev else 'FAIL'}  str_eval A$='WORLD': CF={int(carry(cpu_vev))}, "
          f"VALTYP={val_valtyp2}, len={desc_len2}, bytes={desc_bytes2!r}")

    # ==================================================================
    # Case 6: str_eval of a non-string operand returns CF=0.
    # A numeric name ("A" without $) → var_str_type returns 0 → str_eval_no
    # → CF clear, VALTYP untouched. Oracle: strvar.asm str_eval_no "CF clear
    # -> not a string operand".
    # ==================================================================
    m.poke(VALTYP, 0)
    poke_name(m, NAMEBUF, "A")
    cpu_no = m.call("str_eval", hl=NAMEBUF)
    ok_no = not carry(cpu_no) and m.mem[VALTYP] == 0
    fails += not ok_no
    print(f"{'PASS' if ok_no else 'FAIL'}  str_eval non-string 'A': CF={int(carry(cpu_no))}, "
          f"VALTYP={m.mem[VALTYP]}")

    # ==================================================================
    # Case 7: print_strval emits the bytes of a literal "HELLO" via CHPUT.
    # Tier-2: CHPUT is trapped; contract is "output the char in A at the
    # cursor" (MSX Assembly Page BIOS call list / MSX2 Technical Handbook).
    # We use str_eval to load STRPTR, then call print_strval.
    # Oracle: CHPUT entry $00A2; print_strval code "call CHPUT" per byte.
    # Expected captured bytes = b"HELLO" (ASCII 72 69 76 76 79).
    # ==================================================================
    m.poke(VALTYP, 0)
    m.poke_w(STRPTR, 0)
    m.poke(STRSCR, bytes(1 + STRMAX))
    lit_text2 = b'"HELLO"\x00'
    m.poke(TOKBUF, lit_text2)
    m.call("str_eval", hl=TOKBUF)     # sets STRPTR -> STRSCR descriptor

    out = m.capture_chput()           # trap CHPUT before calling print_strval
    m.call("print_strval")
    ok_print = bytes(out) == b"HELLO"
    fails += not ok_print
    print(f"{'PASS' if ok_print else 'FAIL'}  print_strval emits b'HELLO': "
          f"got {bytes(out)!r}")

    # ==================================================================
    # Case 8: print_strval with an empty string emits nothing.
    # Oracle: print_strval "ld a,b / or a / ret z" — zero-length → early return.
    # ==================================================================
    # Point STRPTR at a zero-length descriptor.
    m.poke(TOKBUF, bytes([0]))       # [len=0]
    m.poke_w(STRPTR, TOKBUF)

    out2 = m.capture_chput()
    m.call("print_strval")
    ok_empty_p = (len(out2) == 0)
    fails += not ok_empty_p
    print(f"{'PASS' if ok_empty_p else 'FAIL'}  print_strval empty string emits nothing "
          f"(got {out2!r})")

    # ==================================================================
    # Case 9: two distinct string variables (A$ and B$) don't alias.
    # Same 2-char keying rule; (A,0) ≠ (B,0).
    # ==================================================================
    reset_strtab()
    m.poke(TOKBUF, bytes([5]) + b"HELLO")
    m.call("str_set_key", b=ord("A"), c=0, de=TOKBUF)
    m.poke(TOKBUF, bytes([5]) + b"WORLD")
    m.call("str_set_key", b=ord("B"), c=0, de=TOKBUF)

    # Note: m.call() returns the shared cpu object; capture .hl before the next call.
    hl_a9 = m.call("str_get_key", b=ord("A"), c=0).hl
    hl_b9 = m.call("str_get_key", b=ord("B"), c=0).hl
    la = m.mem[hl_a9]; ba = bytes(m.mem[hl_a9+1:hl_a9+1+la])
    lb = m.mem[hl_b9]; bb = bytes(m.mem[hl_b9+1:hl_b9+1+lb])
    ok_two = (ba == b"HELLO") and (bb == b"WORLD")
    fails += not ok_two
    print(f"{'PASS' if ok_two else 'FAIL'}  A$='HELLO', B$='WORLD' distinct: "
          f"A$={ba!r}, B$={bb!r}")

    print()
    print("ALL PASS — strvar.asm string-value layer" if not fails
          else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
