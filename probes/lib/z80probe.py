#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Tiny Z80 cartridge builder for openMSX BIOS probes.

Hand-assembles a 16K page-1 MSX cartridge: an `AB` header whose INIT runs a
payload we build from small encoder helpers, then jumps to a fixed DONE landmark
(0x7FF0) that the harness breakpoints on. Results are written into free RAM
(default 0xE000+) and read back with `omsx_run.py --mem`.

This is *our own* clean code: probes call the BIOS only through its public entry
points and observe registers/memory out -- a black-box oracle, never a
disassembly of any reference ROM. See docs/openmsx-harness.md.

Encoders cover just what the probes need; extend as required.
"""
from __future__ import annotations

INIT = 0x4010
DONE = 0x7FF0
RESULT = 0xE000   # default base of the result buffer in free RAM (page 3)


# --- encoders: each returns a list[int] of opcode bytes ---------------------
def _lohi(nn: int) -> list[int]:
    return [nn & 0xFF, (nn >> 8) & 0xFF]

def ld_a(n: int) -> list[int]:      return [0x3E, n & 0xFF]
def ld_b(n: int) -> list[int]:      return [0x06, n & 0xFF]
def ld_c(n: int) -> list[int]:      return [0x0E, n & 0xFF]
def ld_e(n: int) -> list[int]:      return [0x1E, n & 0xFF]
def ld_hl(nn: int) -> list[int]:    return [0x21] + _lohi(nn)
def ld_de(nn: int) -> list[int]:    return [0x11] + _lohi(nn)
def ld_bc(nn: int) -> list[int]:    return [0x01] + _lohi(nn)
def call(nn: int) -> list[int]:     return [0xCD] + _lohi(nn)
def sta(addr: int) -> list[int]:    return [0x32] + _lohi(addr)   # LD (addr),A
def lda(addr: int) -> list[int]:    return [0x3A] + _lohi(addr)   # LD A,(addr)
def sthl(addr: int) -> list[int]:   return [0x22] + _lohi(addr)   # LD (addr),HL
def ei() -> list[int]:              return [0xFB]
def di() -> list[int]:              return [0xF3]
def in_a(port: int) -> list[int]:   return [0xDB, port & 0xFF]   # IN A,(port)
def out_a(port: int) -> list[int]:  return [0xD3, port & 0xFF]   # OUT (port),A
def ldir() -> list[int]:            return [0xED, 0xB0]           # block copy HL->DE, BC bytes

def store_af(addr: int) -> list[int]:
    """Store F then A at addr, addr+1 (PUSH AF; POP BC; B=A,C=F)."""
    return [0xF5, 0xC1] + [0x79] + sta(addr) + [0x78] + sta(addr + 1)

def jr(dd: int) -> list[int]:       return [0x18, dd & 0xFF]
def jr_nz(dd: int) -> list[int]:    return [0x20, dd & 0xFF]

def wait_edge(port: int) -> list[int]:
    """Time one signal half-period on bit 7 of `port`, counting loop iterations.

    Caller presets B (e.g. 1) and D (the current bit-7 level, $00/$80). On exit
    B = iteration count to the next edge and D = the new level. Mirrors the BIOS
    cas_half loop so probe-measured counts match what the BIOS would see. The
    relative displacements are computed here, not hand-counted.
    """
    #  0: IN A,(port)   DB pp
    #  2: AND $80       E6 80
    #  4: CP D          BA
    #  5: JR NZ,done    20 03   -> done at offset 10
    #  7: INC B         04
    #  8: JR loop       18 F6   -> loop at offset 0
    # 10: done: LD D,A  57
    return [0xDB, port & 0xFF, 0xE6, 0x80, 0xBA, 0x20, 0x03,
            0x04, 0x18, 0xF6, 0x57]

def loop_c(body: list[int]) -> list[int]:
    """Wrap `body` in a `DEC C; JR NZ body` loop. Caller presets C (0 -> 256)."""
    tail = [0x0D] + jr_nz((-(len(body) + 3)) & 0xFF)   # DEC C ; JR NZ back to body
    return list(body) + tail


# --- cassette write-timing work area -----------------------------------------
# A real MSX BIOS lays down two reference tables and copies one into the active
# slots when the cassette baud is chosen (e.g. SCREEN ,,,baud). Bare C-BIOS has
# no BASIC and leaves this area blank, so a probe that wants to exercise our
# baud-from-the-work-area selection must set it up itself. These table *values*
# were observed on the VG-8020 oracle (a black-box RAM dump), not copied from any
# ROM; see cbios-tape PROVENANCE.md.
CS120_ADDR, CS240_ADDR, ACTIVE_ADDR = 0xF3FC, 0xF401, 0xF406
CS120_TABLE = [0x53, 0x5C, 0x26, 0x2D, 0x0F]   # 1200-baud signal lengths
CS240_TABLE = [0x25, 0x2D, 0x0E, 0x16, 0x1F]   # 2400-baud signal lengths


def setup_cas_baud(baud: int) -> list[int]:
    """Lay down the standard CS120/CS240 tables and select `baud` into the active
    LOW/HIGH/HEADER slots, mirroring a real BIOS + SCREEN ,,,baud. Clobbers all."""
    code: list[int] = []
    for base, table in ((CS120_ADDR, CS120_TABLE), (CS240_ADDR, CS240_TABLE)):
        for i, b in enumerate(table):
            code += ld_a(b) + sta(base + i)
    src = CS120_ADDR if baud == 1200 else CS240_ADDR
    code += ld_hl(src) + ld_de(ACTIVE_ADDR) + ld_bc(5) + ldir()
    return code


class Cart:
    """Accumulate a payload and allocate a result buffer, then build the ROM."""

    def __init__(self, result_base: int = RESULT):
        self.code: list[int] = []
        self.result_base = result_base
        self._next = result_base

    def emit(self, *chunks: list[int]) -> "Cart":
        for c in chunks:
            self.code += c
        return self

    def alloc(self, n: int) -> int:
        """Reserve n result bytes; return their start address."""
        a = self._next
        self._next += n
        return a

    @property
    def result_len(self) -> int:
        return self._next - self.result_base

    def build(self) -> bytes:
        rom = bytearray(b"\xff" * 0x4000)

        def w(addr: int, data: list[int]) -> None:
            off = addr - 0x4000
            rom[off:off + len(data)] = bytes(data)

        w(0x4000, [0x41, 0x42] + _lohi(INIT))      # 'AB', INIT, STMT/DEV/TEXT=0
        body = list(self.code) + [0xC3] + _lohi(DONE)   # ... ; JP DONE
        if INIT - 0x4000 + len(body) > 0x3FF0:
            raise ValueError("payload too large for 16K cart")
        w(INIT, body)
        w(DONE, [0x18, 0xFE])                        # DONE: JR $
        return bytes(rom)
