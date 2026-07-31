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

import os
import re
import subprocess
from z80 import Z80

_SENTINEL = 0xFFFF          # return address that marks "the routine returned"
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SUB_CACHE = {}             # process-wide cache of the assembled sub-ROM bytes

# Floor of the stack band call() owns. RAM starts at $8000 and call() puts its
# own stack at $F380, so anything below this means SP was loaded from memory
# that is NOT a stack. Measured headroom: the whole 54-file suite (5606 calls)
# lives in $F326..$F380 -- a 90-byte excursion, 29 KB clear of this floor.
# docs/spec-tests-runaway-sweep.md §2.3.
_SP_FLOOR = 0x8000


class StackLost(RuntimeError):
    """SP left the band call() owns -- the row is measuring a RUNAWAY.

    🔴 THIS EXISTS BECAUSE A GREEN ROW MEASURED A RUNAWAY FOR ITS WHOLE LIFE.
    The abort funnel does `ld sp,(SAVSTK)`, and SAVSTK is 0 in this harness's
    zeroed RAM, so the funnel's tail `ret` pops from $0000 and the CPU runs away
    through memory. test_poke.py's ERRMARK row did `try: m.call(...) except:
    pass` and then read RAM, i.e. it asserted on whatever a byte held after
    2,000,000 steps of executing the ROM from an arbitrary entry point. It
    agreed until an unrelated 19-byte page-1 shift moved where the runaway
    landed (D-CONTR, docs/spec-basic-cont-record.md §5.5).

    The 2,000,000-step guard DID fire on every one of those runs. It was
    swallowed because its message -- `runaway: 2000001 steps, PC=$e1c6` -- names
    the arbitrary landing address, i.e. the SYMPTOM. This fires at the `ld sp`
    itself, names the CAUSE, and tells the reader what to do instead.

    A subclass of RuntimeError on purpose: test_stmt_dispatch.py catches
    RuntimeError around its dispatch calls and reports it as a test failure, so
    a stack loss stays LOUD there rather than becoming an unhandled traceback.
    Deliberately unconditional -- there is no opt-out keyword. A test that
    legitimately models a real SAVSTK unwind sets SAVSTK to a plausible stack
    (>= $8000, <= the call's own SP), which passes this band as it stands.
    docs/spec-tests-runaway-sweep.md §3.1.
    """

    def __init__(self, msg, sp, pc, steps, where):
        super().__init__(msg)
        self.sp, self.pc, self.steps, self.where = sp, pc, steps, where


def _build_subrom():
    """Assemble sub/sub.asm once per process -> (full 32 KB bytes, symbols). The
    sub-ROM's own file layout already matches its two-page CALSLT contract: page-0
    tenants (the dispatch table + the WHOLE evicted tokeniser and its duplicated
    keyword table, wave 2, ...) sit at file/address $0000-$3FFF, page-1 tenants
    (fp_sqrt, fatprim_tenant, lineedit_tenant, ...) sit at $4000-$7FFF -- exactly
    where a real page-0 or page-1 CALSLT would map them into CPU space. Callers
    slice the piece they need (see _install_subrom_bridge)."""
    if "bytes" not in _SUB_CACHE:
        rom = "/tmp/msxtest_sub.rom"
        sym = "/tmp/msxtest_sub.sym"
        subprocess.run(["pasmo", "-I", "sub", "--bin", "sub/sub.asm", rom, sym],
                       check=True, capture_output=True, cwd=_ROOT)
        with open(rom, "rb") as fh:
            _SUB_CACHE["bytes"] = fh.read()
        _SUB_CACHE["sym"] = load_symbols(sym)
    return _SUB_CACHE["bytes"], _SUB_CACHE["sym"]


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
    # ⚠️ rom_base IS MANDATORY, AND IT USED TO DEFAULT TO $4000.
    # $4000 was the lean 16 KB page-1-only cartridge's org. Every test that built
    # basic/main.asm without passing rom_base — 18 of the 54 files — was therefore
    # assembling and asserting against the LEAN build, right through S2, which had
    # declared lean "no longer measured". The files that passed RELOC_BASE=$2812
    # explicitly were the ones testing the shipped image.
    #
    # A default is how that happened, so there is no default any more: the base is
    # named at the CALL SITE, the same fix S1 applied to probe machines
    # ([[lean-retire-s1-explicit-machine]]). Three legitimate values — $2812 the
    # BASIC image, $4000 the disk ROM, $0000 the sub ROM — and nothing to silently
    # pick the wrong one. docs/spec-lean-retire-s3-gates.md §5, F-U.
    def __init__(self, rom_path, sym_path, rom_base):
        self.mem = bytearray(0x10000)
        with open(rom_path, "rb") as fh:
            rom = fh.read()
        self.mem[rom_base:rom_base + len(rom)] = rom
        self.sym = load_symbols(sym_path)
        self.cpu = Z80(self.mem)
        self.traps = {}                # addr -> callback(machine)
        if "subrom_call" in self.sym:
            self._install_subrom_bridge()

    def _install_subrom_bridge(self):
        """Bridge the sub-ROM dispatch the flat harness can't page (subrom S2b).
        On the real machine `subrom_call` does a CALSLT into ONE sub-ROM page,
        chosen by whether IX is a page-0 ($0010+) or page-1 ($4010+) entry-table
        address (sub/equates.inc SUBROM_ENTRY_BASE_P0/P1). The flat host harness
        can't page, so each direction gets its own bridge machine, run separately
        so the tenant's own low memory/stack never collides with the caller's:

          * PAGE 0 (IX < $4000): the sub-ROM's page-0 tenants sit at $0000-$3FFF,
            the SAME low addresses the caller's own (real-machine page-0)
            interpreter/stack occupy -- must run in a bare machine loaded with
            ONLY the sub-ROM's page-0 half, never the caller's bytes.
          * PAGE 1 (IX >= $4000): the sub-ROM's page-1 tenants sit at $4000-$7FFF
            and (spec: docs/spec-eviction-g4-space.md §4, tools/check_tenant_
            closure.py --page1) may call back into the CALLER's own low region /
            BIOS (< $4000, which STAYS mapped while only page 1 switches -- e.g.
            sub/lineedit.asm's `call vars_reset`). So the page-1 bridge starts
            from a COPY of the caller's ENTIRE image (giving it that low region
            for free) and overlays ONLY $4000-$7FFF with the sub-ROM's page-1
            bytes -- mirroring a real page-1 CALSLT exactly (page 0 unchanged,
            page 1 swapped to the sub-ROM).

        Both directions shuttle only RAM ($8000+): the tenant reads its args and
        writes its results in page-2/3 RAM, the same in both slots on the real
        machine. Copy that RAM in, run, copy back only the below-stack range the
        tenant may have written. Transparent to every test that tokenises a
        numeric literal (page 0) or reaches a page-1 tenant like fatprim/
        lineedit through a resident shim."""
        sub_bytes, _ = _build_subrom()
        sub0 = object.__new__(Machine)         # bare Machine, page-0 half only
        sub0.mem = bytearray(0x10000)
        sub0.mem[0:0x4000] = sub_bytes[0:0x4000]
        sub0.sym = {}
        sub0.cpu = Z80(sub0.mem)
        sub0.traps = {}
        RAM_LO, STACK = 0x8000, 0xF300         # shuttle $8000..stack; leave stacks private

        def bridge(mach):
            cpu = mach.cpu
            if cpu.ix < 0x4000:
                sub0.mem[RAM_LO:0x10000] = mach.mem[RAM_LO:0x10000]  # args/scratch in
                sub0.call(cpu.ix, hl=cpu.hl, de=cpu.de)               # own stack + low mem
                mach.mem[RAM_LO:STACK] = sub0.mem[RAM_LO:STACK]       # results back
                res = sub0.cpu
            else:
                sub1 = object.__new__(Machine)     # page-1 half over the CALLER's own image
                sub1.mem = bytearray(mach.mem)     # low region/BIOS + RAM, all borrowed
                sub1.mem[0x4000:0x8000] = sub_bytes[0x4000:0x8000]    # page 1 -> sub-ROM
                sub1.sym = {}
                sub1.cpu = Z80(sub1.mem)
                sub1.traps = {}
                sub1.call(cpu.ix, hl=cpu.hl, de=cpu.de)
                mach.mem[RAM_LO:STACK] = sub1.mem[RAM_LO:STACK]       # results back
                res = sub1.cpu
            cpu.hl, cpu.de, cpu.a = res.hl, res.de, res.a
            cpu.f &= ~0x01                     # CF=0: dispatch completed (never "absent" here)

        self.trap("subrom_call", bridge)

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
    def call(self, name_or_addr, max_steps=2_000_000, keep_sp=False, **regs):
        cpu = self.cpu
        for k, v in regs.items():
            setattr(cpu, k, v)
        if not keep_sp:
            cpu.sp = 0xF380     # keep_sp=True: reuse the caller's stack (nested run,
        sp0 = cpu.sp            #   e.g. the subrom bridge) so it doesn't stomp it
        cpu.push(_SENTINEL)     # sp0 = the frame this call owns; SP may never rise
        cpu.pc = name_or_addr if isinstance(name_or_addr, int) else self.sym[name_or_addr]
        entry = name_or_addr if isinstance(name_or_addr, str) else f"{name_or_addr:#06x}"
        steps = 0
        while cpu.pc != _SENTINEL:
            fn = self.traps.get(cpu.pc)
            if fn is not None:
                fn(self)               # model the trapped routine's effect
                cpu.pc = cpu.pop()     # ...and return to the caller
                if not _SP_FLOOR <= cpu.sp <= sp0:
                    self._stack_lost(sp0, steps, entry, "the trap return")
                continue
            cpu.step()
            steps += 1
            # THE STACK-BAND INVARIANT. One range compare per step; see StackLost.
            if not _SP_FLOOR <= cpu.sp <= sp0:
                self._stack_lost(sp0, steps, entry, f"step {steps}")
            if steps > max_steps:
                raise RuntimeError(f"runaway: {steps} steps, PC={cpu.pc:#06x}")
        return cpu

    def _stack_lost(self, sp0, steps, entry, where):
        """Report a band violation naming the CAUSE and the fix (see StackLost)."""
        cpu = self.cpu
        raise StackLost(
            f"SP left the harness stack band [{_SP_FLOOR:#06x},{sp0:#06x}]: "
            f"SP={cpu.sp:#06x} at PC={cpu.pc:#06x}, {where} of call({entry!r}).\n"
            "  The routine loaded SP from memory that is not a stack -- almost "
            "always `ld sp,(SAVSTK)`\n  with SAVSTK=0 in this harness's zeroed "
            "RAM, i.e. the error-abort funnel. From here the CPU\n  RUNS AWAY, so "
            "anything this row reads AFTER the call measures the runaway and not "
            "the\n  routine under test. Fix the TEST, not the ROM: trap the funnel "
            "(fre_abort_low /\n  raise_error) and sample the state THERE, at the "
            "moment the row is actually about.\n"
            "  See docs/spec-tests-runaway-sweep.md and tests/test_harness_guard.py.",
            cpu.sp, cpu.pc, steps, where)


# convenience flag accessors for assertions
def carry(cpu):
    return bool(cpu.f & 0x01)


def zero(cpu):
    return bool(cpu.f & 0x40)
