# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: the sub-ROM bridge lets a tenant write into the CALLER's stack frame
(D-WSZERO S16.0, scratchpad/shblk_plan.md §4).

On the machine a CALSLT tenant runs on the caller's own Z80 stack, so anything the
caller keeps above its SP -- the string-heap parameter block that S16 moves onto the
stack, or any pointer into a caller frame -- is the same RAM to both. The flat harness
(tests/msxtest.py `_install_subrom_bridge`) used to run a page-0 tenant on a PRIVATE
stack starting at $F380 and copy back everything EXCEPT [$F300,$F380): a tenant write
into that band was dropped with no error. This row makes the drop visible.

The case: the caller sits at SP = $F360 and keeps a 3-byte descriptor slot at $F370,
above its SP, i.e. in its own frame. String-heap op 12 (VAR_STORE: copy a source
descriptor's body into the heap and write the new descriptor to DEST) is run with
DEST = $F370. A faithful bridge leaves [5][ptr] there, ptr -> "HELLO" in the heap.
"""

import os
import subprocess
import sys

from _tmp import tp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

ROM = tp("zb_bridgestack.rom")
SYM = tp("zb_bridgestack.sym")
RELOC_BASE = 0x2781
SETSRC = 0xC300     # source descriptor [len][ptr]
BODY = 0xC500       # its body
CALLER_SP = 0xF360  # the caller's stack pointer at the call
DEST = 0xF370       # a slot in the caller's own frame, above its SP


def run():
    subprocess.run(["pasmo", "--bin", os.path.join(ROOT, "basic", "main.asm"), ROM, SYM],
                   check=True, capture_output=True)
    m = Machine(ROM, SYM, rom_base=RELOC_BASE)
    s = m.sym
    # the heap setup of tests/test_str_engine.py (see its comments)
    m.poke_w(s["PRGEND"], 0x9000)
    m.poke(0x9000, b"\x00\x00")
    m.poke_w(s["ARYTAB"], 0x9002)
    m.poke(0x9002, b"\x00\x00")
    m.poke_w(s["POOLSIZE"], 4096)
    m.call("heap_reset")

    m.poke(BODY, b"HELLO")
    m.poke(SETSRC, bytes([5]))
    m.poke_w(SETSRC + 1, BODY)
    m.poke(DEST, b"\x00\x00\x00")
    # D-WSZERO S16: the op's arguments travel in sh_go's stack block (HL = the
    # source, DE = the destination), which is itself in the caller's frame
    m.cpu.sp = CALLER_SP
    m.call("sh_go", keep_sp=True, a=12, hl=SETSRC, de=DEST)
    err = m.cpu.a

    fails = 0
    dlen = m.mem[DEST]
    ptr = m.mem[DEST + 1] | (m.mem[DEST + 2] << 8)
    body = bytes(m.mem[ptr:ptr + dlen]) if dlen else b""
    ok = dlen == 5 and body == b"HELLO" and ptr != BODY and err == 0
    print(f"  {'PASS' if ok else 'FAIL'}  op 12 into the caller's frame at ${DEST:04X}: "
          f"len={dlen} ptr=${ptr:04X} body={body!r} ERR={err}")
    fails += not ok
    return fails


if __name__ == "__main__":
    f = run()
    print("FAIL" if f else "PASS")
    sys.exit(1 if f else 0)
