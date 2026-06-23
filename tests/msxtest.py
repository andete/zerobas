# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Host-side test harness for zerobas ROM routines — no emulator required.

Loads an assembled ROM plus the pasmo symbol file into a flat 64 KB memory,
lets a test CALL any internal routine *by label*, traps BIOS / dependency entry
points so their effects are modelled in Python, runs until the routine returns,
and exposes registers + memory for assertions.

The point: a BIOS call (CHPUT, RDVRM, DSKIO, …) or an in-ROM dependency
(fat_mount, …) becomes a Python callback. The test asserts that the routine
under test honours its side of the contract; the callback supplies the other
side. Runs in milliseconds with none of the openMSX boot/timing determinism
hazards, so it is the fast regression layer beneath the differential probes.
"""

import re
from z80 import Z80

_SENTINEL = 0xFFFF          # return address that marks "the routine returned"


def load_symbols(path):
    """Parse a pasmo symbol file ('LABEL\\tEQU 0xXXXXH') -> {name: addr}."""
    syms = {}
    pat = re.compile(r"^(\S+)\s+EQU\s+([0-9A-Fa-f]+)H", re.IGNORECASE)
    with open(path) as fh:
        for line in fh:
            m = pat.match(line.strip())
            if m:
                syms[m.group(1)] = int(m.group(2), 16)
    return syms


class Machine:
    def __init__(self, rom_path, sym_path, rom_base=0x4000):
        self.mem = bytearray(0x10000)
        with open(rom_path, "rb") as fh:
            rom = fh.read()
        self.mem[rom_base:rom_base + len(rom)] = rom
        self.sym = load_symbols(sym_path)
        self.cpu = Z80(self.mem)
        self.traps = {}                # addr -> callback(machine)

    # --- symbol / memory access ------------------------------------------
    def addr(self, name):
        return self.sym[name]

    def peek(self, a, n=1):
        return bytes(self.mem[a:a + n])

    def poke(self, a, data):
        if isinstance(data, int):
            data = bytes([data])
        self.mem[a:a + len(data)] = data

    def poke_w(self, a, v):
        self.mem[a] = v & 0xFF
        self.mem[a + 1] = (v >> 8) & 0xFF

    # --- dependency / BIOS traps -----------------------------------------
    def trap(self, name_or_addr, fn):
        """Replace a routine: when execution reaches it, run fn(self) then RET."""
        a = name_or_addr if isinstance(name_or_addr, int) else self.sym[name_or_addr]
        self.traps[a] = fn

    # --- Tier-2 conveniences: capture what a routine sends to the BIOS ----
    def capture_chput(self, name="CHPUT"):
        """Trap CHPUT and accumulate every emitted byte. Returns the list it
        appends to (read it after the call). The console BIOS contract is
        'output the char in A at the cursor' (MSX2 TH / MSX Assembly Page), so
        the byte under test is register A on each entry."""
        out = []
        self.trap(name, lambda m: out.append(m.cpu.a))
        return out

    def record(self, name, regs=("a", "bc", "de", "hl")):
        """Trap a routine and log a register snapshot on each entry (without
        modelling any effect — execution just RETs). Returns the log list.
        Use for BIOS calls whose contract is 'invoked with these args', e.g.
        CHGMOD (A=mode), WRTVRM (HL=addr, A=val)."""
        log = []
        self.trap(name, lambda m: log.append({r: getattr(m.cpu, r) for r in regs}))
        return log

    def record_out(self):
        """Capture every OUT (port,val) the routine performs. Returns the log."""
        log = []
        self.cpu.io_out = lambda port, val: log.append((port, val))
        return log

    # --- call a routine by name and run to its RET -----------------------
    def call(self, name_or_addr, max_steps=2_000_000, **regs):
        cpu = self.cpu
        for k, v in regs.items():
            setattr(cpu, k, v)
        cpu.sp = 0xF380
        cpu.push(_SENTINEL)
        cpu.pc = name_or_addr if isinstance(name_or_addr, int) else self.sym[name_or_addr]
        steps = 0
        while cpu.pc != _SENTINEL:
            fn = self.traps.get(cpu.pc)
            if fn is not None:
                fn(self)               # model the trapped routine's effect
                cpu.pc = cpu.pop()     # ...and return to the caller
                continue
            cpu.step()
            steps += 1
            if steps > max_steps:
                raise RuntimeError(f"runaway: {steps} steps, PC={cpu.pc:#06x}")
        return cpu


# convenience flag accessors for assertions
def carry(cpu):
    return bool(cpu.f & 0x01)


def zero(cpu):
    return bool(cpu.f & 0x40)
