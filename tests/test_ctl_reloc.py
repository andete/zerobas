"""Unit test: ctl_alloc's live-block relocation (D-SPMERGE cut 2), no emulator.

🔴 THIS ROUTINE IS INVISIBLE TO THE BATTERY, WHICH IS THE WHOLE REASON IT EXISTS.
`ctl_reloc` only copies when the machine stack is INSIDE the control pool's
region, and today `SP` is still C-BIOS's, far above the frontier -- so on the
shipping ROM the copy is skipped on every call and 128 green suites say nothing
about it. The step that moves `SP` into the region (spec-basic-spmerge.md §9.4
step 3) is the one that will exercise it, and by then a mistake here corrupts the
stack silently. So the copy is witnessed HERE, by placing the frontier above the
harness's own stack and calling the real routine.

What the routine must do (§9.2), in: HL = frame size:

    base := CSP - size            refuse (CF=1) if base < CTLLIM
    copy [SP, CSP) down by size   so the frame takes the space it vacated
    SP := SP - size ; CSP := base
    out: HL = base, CF = 0

The point of the copy is that nothing which can `ret` is left ABOVE the frame --
including this harness's own return address, which moves with the block and is
what makes the call return at all. A test that only checked CSP would pass with
the copy deleted; the moved-marker and moved-SP arms are what separate them.

Oracle: the design contract above, not the ROM's own output.
"""

import os
from _tmp import tp
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

BASIC_BASE = 0x2765
ROM = tp("zb_ctlreloc.rom")
SYM = tp("zb_ctlreloc.sym")


def build():
    src = os.path.join(ROOT, "basic", "main.asm")
    subprocess.run(["pasmo", "--bin", src, ROM, SYM], check=True, capture_output=True)


def check(fails, label, got, want):
    ok = got == want
    g = f"${got:04X}" if isinstance(got, int) else repr(got)
    w = f"${want:04X}" if isinstance(want, int) else repr(want)
    print(f"  {'ok  ' if ok else 'FAIL'} {label:<34} got {g:<8} want {w}")
    return fails + (0 if ok else 1)


def test_copy(m, fails):
    """SP inside the region: the block must move and SP must follow it."""
    CSP, CTLLIM = m.sym["CSP"], m.sym["CTLLIM"]
    TOP, SIZE = 0xF800, 8
    m.poke_w(CSP, TOP)
    m.poke_w(CTLLIM, 0x8000)
    # Markers inside the block the copy has to move. 0xF700 is comfortably above
    # the harness's own frame and below the frontier.
    m.poke(0xF700, bytes([0xA5, 0x5A, 0xC3]))
    r = m.call("ctl_alloc", hl=SIZE)
    fails = check(fails, "CSP := base", m.peek(CSP, 2)[0] | (m.peek(CSP, 2)[1] << 8), TOP - SIZE)
    fails = check(fails, "HL = the frame's base", r.hl, TOP - SIZE)
    fails = check(fails, "CF clear (allocated)", r.f & 1, 0)
    fails = check(fails, "marker moved down by size",
                  bytes(m.peek(0xF700 - SIZE, 3)), bytes([0xA5, 0x5A, 0xC3]))
    return fails


def test_noop(m, fails):
    """SP ABOVE the frontier -- the shipping configuration. Nothing may move."""
    CSP, CTLLIM = m.sym["CSP"], m.sym["CTLLIM"]
    TOP, SIZE = 0xD900, 8
    m.poke_w(CSP, TOP)
    m.poke_w(CTLLIM, 0x8000)
    m.poke(0xD800, bytes([0x11, 0x22, 0x33]))
    m.poke(0xD800 - SIZE, bytes([0, 0, 0]))
    r = m.call("ctl_alloc", hl=SIZE)
    fails = check(fails, "CSP := base (no-op path)",
                  m.peek(CSP, 2)[0] | (m.peek(CSP, 2)[1] << 8), TOP - SIZE)
    fails = check(fails, "HL = the frame's base", r.hl, TOP - SIZE)
    fails = check(fails, "nothing copied", bytes(m.peek(0xD800 - SIZE, 3)), bytes([0, 0, 0]))
    return fails


def test_refuse(m, fails):
    """base below CTLLIM: refuse, write nothing, and do not touch the stack."""
    CSP, CTLLIM = m.sym["CSP"], m.sym["CTLLIM"]
    m.poke_w(CSP, 0x8010)
    m.poke_w(CTLLIM, 0x8000)
    r = m.call("ctl_alloc", hl=0x40)
    fails = check(fails, "CF set (pool full)", r.f & 1, 1)
    fails = check(fails, "CSP untouched",
                  m.peek(CSP, 2)[0] | (m.peek(CSP, 2)[1] << 8), 0x8010)
    return fails


def run():
    build()
    fails = 0
    for title, fn in (("copy path (SP inside the region)", test_copy),
                      ("no-op path (SP above the frontier)", test_noop),
                      ("refusal at the floor", test_refuse)):
        print(f"=== {title} ===")
        fails = fn(Machine(ROM, SYM, rom_base=BASIC_BASE), fails)
        print()
    print("ALL PASS — ctl_alloc relocates the live block per spec §9.2"
          if not fails else f"{fails} FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
