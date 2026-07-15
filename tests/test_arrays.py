# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: BASIC arrays slice-1, SPLIT design (repack build only),
sub/arrays.asm (the sub-ROM page-0 tenant half) + basic/sysvars.inc's
ARY_* param block.

docs/spec-basic-arrays.md §10 (the split contract). Ported from the
monolithic WIP's tests/test_arrays.py (branch arrays-slice1-wip) -- same
case shapes (ary_find stride walk, column-major offset arithmetic, bound/
negative/wrong-ndim dispositions, auto-dim, DIM/store/load round-trip),
adapted to the split ABI:

  - The engine (ary_find/ary_alloc/ary_resolve/ary_stride/ary_count_elems/
    ary_mul16_checked) now lives in sub/arrays.asm, assembled as PART OF THE
    SUB-ROM (sub/sub.asm, pasmo -I sub), not the main reloc build -- so this
    file builds sub.rom directly (mirrors msxtest.py's own _build_subrom
    helper) and drives the engine routines by label at rom_base=0 (the
    sub-ROM's own page-0 org). No subrom_call/CALSLT bridging needed here:
    these are the tenant's OWN internal routines (same register conventions
    the WIP proved), not a main-ROM call through the dispatch ABI.
  - ary_alloc/ary_resolve's error contract changed from "sets FPERR" (a
    main-ROM-only concept the tenant has no access to) to "returns A = the
    ARY_ERR code" (0 ok; 1 Subscript-oor; 2 Illegal-fn; 4 Out of memory) --
    §10.2's own numbering, distinct from the main-ROM FPERR numbers the
    glue (basic/arrays.asm ary_engine_call) maps them to.
  - ary_alloc/ary_resolve's own transient bookkeeping (formerly the WIP's
    RAM-resident ARY_SCR) is now a per-call HARDWARE STACK frame (IY-
    addressed) -- invisible to these tests (an implementation detail; the
    register/RAM contract at entry/exit is unchanged).
  - A NEW case exercises ary_engine (the tenant's actual dispatch entry,
    SUBROM_IDX_ARY) end-to-end through the ARY_OP/ARY_KEY/ARY_TYPE/
    ARY_NIDX/ARY_IDX/ARY_ADDR/ARY_ERR param block (basic/sysvars.inc §10.2)
    -- the ABI surface basic/arrays.asm's `ary_engine_call` actually drives
    via subrom_call, not exercised by the WIP (which never had a param
    block; ary_resolve/ary_alloc took register args directly).

Oracle basis: docs/spec-basic-arrays.md §4.1 (VG-8020 black-box capture) for
every semantic; §9.2/§10.3 for the own-design descriptor layout (never ROM
disassembly -- the byte layout is zerobas's own choice, like VARTAB/STRTAB).
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine, carry  # noqa: E402

ROM = "/tmp/zb_arrays_sub.rom"
SYM = "/tmp/zb_arrays_sub.sym"

# Scratch program-text area for these tests: PRGEND is pointed at a fixed
# scratch address (well inside RAM, clear of any other structure) so ARYBASE
# (= PRGEND+2) is a fixed, known address -- same convention the WIP used.
PROG_END_ADDR = 0x9000
ARYBASE = PROG_END_ADDR + 2


def build():
    src = os.path.join(ROOT, "sub", "sub.asm")
    subprocess.run(["pasmo", "-I", os.path.join(ROOT, "sub"), "--bin", src, ROM, SYM],
                    check=True, capture_output=True, cwd=ROOT)


def make_machine():
    m = Machine(ROM, SYM, rom_base=0)
    s = m.sym
    # PRGEND -> PROG_END_ADDR; the 2-byte $0000 terminator lives there (the
    # program.asm line-link convention: PRGEND addresses the end-of-program
    # marker word).
    m.poke_w(s["PRGEND"], PROG_END_ADDR)
    m.poke(PROG_END_ADDR, b"\x00\x00")
    # HIMEM=0 -> the ceiling defaults to TXTMAX (never CLEAR'd, the common
    # case for these low-level tests).
    m.poke_w(s["HIMEM"], 0)
    # "no arrays" sentinel at ARYBASE.
    m.poke(ARYBASE, b"\x00\x00")
    return m


def descriptor_bytes(name0, name1, dtype, bounds):
    """Build one own-design array descriptor (§9.2/§10.3): [name0][name1]
    [type][ndim][stride:2][bounds...][zero data]. Returns (bytes, stride)."""
    ndim = len(bounds)
    count = 1
    for b in bounds:
        count *= (b + 1)
    data_bytes = count * dtype
    stride = 6 + 2 * ndim + data_bytes
    body = bytearray()
    body.append(name0)
    body.append(name1)
    body.append(dtype)
    body.append(ndim)
    body.append(stride & 0xFF)
    body.append((stride >> 8) & 0xFF)
    for b in bounds:
        body.append(b & 0xFF)
        body.append((b >> 8) & 0xFF)
    body.extend(bytes(data_bytes))
    assert len(body) == stride
    return bytes(body), stride


def run():
    build()
    m = Machine(ROM, SYM, rom_base=0)  # just to read symbols cheaply
    s = m.sym
    fails = 0

    # ==================================================================
    # Case 1: ary_find stride walk over two back-to-back descriptors.
    # Oracle: sub/arrays.asm ary_find header -- "CF set + HL=descriptor
    # base if found; CF clear + HL=terminator/tail slot if not found",
    # walking by each descriptor's own cached stride field (§9.2).
    # ==================================================================
    m = make_machine()
    # Descriptor 1: "A" (single, type=4), 1-D, bound0=4 (5 elements).
    desc1, stride1 = descriptor_bytes(ord("A"), 0, 4, [4])
    m.poke(ARYBASE, desc1)
    # Descriptor 2: "B" (int, type=2), 1-D, bound0=2 (3 elements).
    desc2_addr = ARYBASE + stride1
    desc2, stride2 = descriptor_bytes(ord("B"), 0, 2, [2])
    m.poke(desc2_addr, desc2)
    term_addr = desc2_addr + stride2
    m.poke(term_addr, b"\x00\x00")

    cpu = m.call("ary_find", b=ord("B"), c=0, a=2)
    ok_found = carry(cpu) and (cpu.hl == desc2_addr)
    fails += not ok_found
    print(f"{'PASS' if ok_found else 'FAIL'} ary_find locates 'B' (int) at "
          f"desc2 (HL={cpu.hl:#06x}, want {desc2_addr:#06x}, CF={carry(cpu)})")

    cpu = m.call("ary_find", b=ord("A"), c=0, a=4)
    ok_found2 = carry(cpu) and (cpu.hl == ARYBASE)
    fails += not ok_found2
    print(f"{'PASS' if ok_found2 else 'FAIL'} ary_find locates 'A' (single) "
          f"at ARYBASE (HL={cpu.hl:#06x}, want {ARYBASE:#06x})")

    # 'A' as an INT (type=2) is a DISTINCT array from 'A' single (§4.1 #7,
    # type is part of the key) -- must NOT be found.
    cpu = m.call("ary_find", b=ord("A"), c=0, a=2)
    ok_distinct = (not carry(cpu)) and (cpu.hl == term_addr)
    fails += not ok_distinct
    print(f"{'PASS' if ok_distinct else 'FAIL'} ary_find: 'A' int is NOT "
          f"'A' single (CF={carry(cpu)}, HL={cpu.hl:#06x}, want "
          f"not-found at terminator {term_addr:#06x})")

    cpu = m.call("ary_find", b=ord("Z"), c=0, a=2)
    ok_notfound = (not carry(cpu)) and (cpu.hl == term_addr)
    fails += not ok_notfound
    print(f"{'PASS' if ok_notfound else 'FAIL'} ary_find: absent key -> "
          f"CF clear, HL=terminator ({cpu.hl:#06x}, want {term_addr:#06x})")

    # ==================================================================
    # Case 2: column-major offset arithmetic, a 2-D DIM(2,3) array.
    # Oracle: spec §9.2 off(i0,i1) = i0 + (b0+1)*i1; data_start =
    # desc_base + 6 + 2*ndim (the cached-stride header, own design).
    # ==================================================================
    m = make_machine()
    BOUNDS_BUF = 0x9200  # scratch: ndim int16 LE bounds for ary_alloc's IX input
    m.poke_w(BOUNDS_BUF + 0, 2)   # bound0 = 2
    m.poke_w(BOUNDS_BUF + 2, 3)   # bound1 = 3
    m.poke(s["ARY_NIDX"], 2)
    cpu = m.call("ary_alloc", b=ord("C"), c=0, a=2, ix=BOUNDS_BUF)
    ok_alloc = carry(cpu)
    fails += not ok_alloc
    desc_base = cpu.hl
    print(f"{'PASS' if ok_alloc else 'FAIL'} ary_alloc creates DIM C(2,3) "
          f"(CF={carry(cpu)}, desc={desc_base:#06x})")

    data_start = desc_base + 6 + 2 * 2  # header(6) + ndim(2)*2 bounds bytes

    def resolve(i, j):
        m.poke(s["ARY_NIDX"], 2)
        m.poke_w(s["ARY_IDX"] + 0, i & 0xFFFF)
        m.poke_w(s["ARY_IDX"] + 2, j & 0xFFFF)
        return m.call("ary_resolve", b=ord("C"), c=0, a=2)

    # (0,0) -> off=0
    cpu = resolve(0, 0)
    want = data_start + 0 * 2
    ok = (cpu.hl == want) and (cpu.a == 0)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'} C(0,0) -> {cpu.hl:#06x} (want {want:#06x})")

    # (1,0) -> off=1
    cpu = resolve(1, 0)
    want = data_start + 1 * 2
    ok = (cpu.hl == want) and (cpu.a == 0)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'} C(1,0) -> {cpu.hl:#06x} (want {want:#06x})")

    # (0,1) -> off=(2+1)*1=3
    cpu = resolve(0, 1)
    want = data_start + 3 * 2
    ok = (cpu.hl == want) and (cpu.a == 0)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'} C(0,1) -> {cpu.hl:#06x} (want {want:#06x})")

    # (2,3) -> off = 2 + 3*3 = 11 (last valid element, both at their bound --
    # inclusive upper, §4.1 #3)
    cpu = resolve(2, 3)
    want = data_start + 11 * 2
    ok = (cpu.hl == want) and (cpu.a == 0)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'} C(2,3) (at both bounds) -> {cpu.hl:#06x} "
          f"(want {want:#06x})")

    # ==================================================================
    # Case 3: bound / negative / wrong-ndim dispositions (§4.1 #3/#8/#9).
    # ARY_ERR codes (§10.2): 1 Subscript-oor, 2 Illegal-fn (negative).
    # ==================================================================
    cpu = resolve(3, 0)  # i=3 > bound0=2 -> Subscript out of range
    ok = cpu.a == 1
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'} C(3,0) over bound0 -> A=1 (subscript "
          f"oor) (got {cpu.a})")

    cpu = resolve(0, 4)  # j=4 > bound1=3 -> Subscript out of range
    ok = cpu.a == 1
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'} C(0,4) over bound1 -> A=1 (got {cpu.a})")

    cpu = resolve(-1, 0)  # negative subscript -> Illegal function call
    ok = cpu.a == 2
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'} C(-1,0) negative -> A=2 (illegal fn) "
          f"(got {cpu.a})")

    # wrong dimension count (1 subscript on a 2-D array) -> Subscript o.o.r.
    m.poke(s["ARY_NIDX"], 1)
    m.poke_w(s["ARY_IDX"] + 0, 0)
    cpu = m.call("ary_resolve", b=ord("C"), c=0, a=2)
    ok = cpu.a == 1
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'} C(0) wrong ndim -> A=1 (got {cpu.a})")

    # ==================================================================
    # Case 4: auto-dim on first reference (§4.1 #1: undeclared array ->
    # bound 10 per dimension) + DIM/store round-trip via ary_alloc/ary_find.
    # ==================================================================
    m = make_machine()
    # Auto-dim: reference D(5) with no prior DIM -- ary_resolve creates it
    # with ndim=1, bound0=10.
    m.poke(s["ARY_NIDX"], 1)
    m.poke_w(s["ARY_IDX"] + 0, 5)
    cpu = m.call("ary_resolve", b=ord("D"), c=0, a=2)
    ok_auto = cpu.a == 0
    fails += not ok_auto
    print(f"{'PASS' if ok_auto else 'FAIL'} D(5) auto-dims cleanly (A={cpu.a})")

    # D(11) on the SAME (now-autodimmed-to-10) array -> Subscript o.o.r.
    m.poke(s["ARY_NIDX"], 1)
    m.poke_w(s["ARY_IDX"] + 0, 11)
    cpu = m.call("ary_resolve", b=ord("D"), c=0, a=2)
    ok_autobound = cpu.a == 1
    fails += not ok_autobound
    print(f"{'PASS' if ok_autobound else 'FAIL'} D(11) over auto-dim bound "
          f"10 -> A=1 (got {cpu.a})")

    # DIM E(3) as type 4 (single); confirm ary_find now sees it as existing.
    BOUNDS_BUF = 0x9200
    m.poke_w(BOUNDS_BUF, 3)
    m.poke(s["ARY_NIDX"], 1)
    cpu = m.call("ary_alloc", b=ord("E"), c=0, a=4, ix=BOUNDS_BUF)
    ok_alloc_e = carry(cpu)
    fails += not ok_alloc_e
    print(f"{'PASS' if ok_alloc_e else 'FAIL'} ary_alloc DIM E(3) single "
          f"(CF={carry(cpu)})")

    cpu = m.call("ary_find", b=ord("E"), c=0, a=4)
    ok_e_exists = carry(cpu)
    fails += not ok_e_exists
    print(f"{'PASS' if ok_e_exists else 'FAIL'} ary_find sees the newly "
          f"DIM'd E(3) (CF={carry(cpu)})")

    # ==================================================================
    # Case 5: OOM disposition -- an allocation whose data would cross the
    # ceiling (min(HIMEM,TXTMAX)) returns CF clear + A=4 (§10.2), NOT FPERR
    # (the tenant has no such concept -- that mapping is main-ROM glue's
    # job, basic/arrays.asm ary_engine_call).
    # ==================================================================
    m = make_machine()
    # Lower HIMEM to just above ARYBASE so even a modest array overflows.
    m.poke_w(s["HIMEM"], ARYBASE + 8)
    BOUNDS_BUF = 0x9200
    m.poke_w(BOUNDS_BUF, 1000)   # bound0=1000 -> 1001 elements * 8B (double) way over
    m.poke(s["ARY_NIDX"], 1)
    cpu = m.call("ary_alloc", b=ord("F"), c=0, a=8, ix=BOUNDS_BUF)
    ok_oom = (not carry(cpu)) and (cpu.a == 4)
    fails += not ok_oom
    print(f"{'PASS' if ok_oom else 'FAIL'} ary_alloc OOM under a tight "
          f"HIMEM ceiling -> CF clear, A=4 (CF={carry(cpu)}, A={cpu.a})")

    # ==================================================================
    # Case 6: ary_engine, the tenant's ACTUAL dispatch entry (SUBROM_IDX_ARY)
    # -- the ABI surface basic/arrays.asm's ary_engine_call drives via
    # subrom_call, exercised here through the ARY_OP..ARY_ERR param block
    # directly (§10.2). op=1 DIM: allocate, then redim-check a repeat.
    # op=0 RESOLVE: read the just-DIM'd array's element address.
    # ==================================================================
    m = make_machine()

    def set_key(name0, name1=0):
        # ARY_KEY is a plain 16-bit BC round-trip cell (§10.2): main writes it
        # via `ld (ARY_KEY),bc` with B=name0/C=name1 (var_name_key's own
        # convention), which Z80's `LD (nn),BC` stores as [C][B] (low=C,
        # high=B) -- i.e. word = name1 | (name0<<8). The tenant reads it back
        # via the matching `ld bc,(ARY_KEY)`, so the two are self-consistent
        # regardless of byte order -- but a manual poke must reproduce the
        # SAME word `ld (ARY_KEY),bc` would have written.
        m.poke_w(s["ARY_KEY"], name1 | (name0 << 8))

    # DIM G(4) as type 2 (int).
    set_key(ord("G"))
    m.poke(s["ARY_TYPE"], 2)
    m.poke(s["ARY_NIDX"], 1)
    m.poke_w(s["ARY_IDX"] + 0, 4)
    m.poke(s["ARY_OP"], 1)         # op = DIM
    m.call("ary_engine")
    ok_dim = m.peek(s["ARY_ERR"])[0] == 0
    fails += not ok_dim
    print(f"{'PASS' if ok_dim else 'FAIL'} ary_engine op=DIM: G(4) declares "
          f"cleanly (ARY_ERR={m.peek(s['ARY_ERR'])[0]})")

    # Re-DIM of the same array -> ARY_ERR=3 (Redimensioned array, §4.1 #4).
    m.poke(s["ARY_OP"], 1)
    m.call("ary_engine")
    ok_redim = m.peek(s["ARY_ERR"])[0] == 3
    fails += not ok_redim
    print(f"{'PASS' if ok_redim else 'FAIL'} ary_engine op=DIM: re-DIM G(4) "
          f"-> ARY_ERR=3 (got {m.peek(s['ARY_ERR'])[0]})")

    # RESOLVE G(2): should hit the already-DIM'd descriptor (no auto-dim),
    # returning a real ARY_ADDR and ARY_ERR=0.
    m.poke(s["ARY_NIDX"], 1)
    m.poke_w(s["ARY_IDX"] + 0, 2)
    m.poke(s["ARY_OP"], 0)         # op = RESOLVE
    m.call("ary_engine")
    err = m.peek(s["ARY_ERR"])[0]
    addr = m.peek(s["ARY_ADDR"] + 0)[0] | (m.peek(s["ARY_ADDR"] + 1)[0] << 8)
    ok_resolve = (err == 0) and (ARYBASE <= addr)
    fails += not ok_resolve
    print(f"{'PASS' if ok_resolve else 'FAIL'} ary_engine op=RESOLVE: G(2) "
          f"-> ARY_ERR=0, ARY_ADDR={addr:#06x} (err={err})")

    # RESOLVE G(9): out of range (bound0=4) -> ARY_ERR=1.
    m.poke(s["ARY_NIDX"], 1)
    m.poke_w(s["ARY_IDX"] + 0, 9)
    m.poke(s["ARY_OP"], 0)
    m.call("ary_engine")
    err2 = m.peek(s["ARY_ERR"])[0]
    ok_oob = err2 == 1
    fails += not ok_oob
    print(f"{'PASS' if ok_oob else 'FAIL'} ary_engine op=RESOLVE: G(9) over "
          f"bound -> ARY_ERR=1 (got {err2})")

    # A DIFFERENT undeclared array via op=RESOLVE auto-dims (bound 10).
    set_key(ord("H"))
    m.poke(s["ARY_TYPE"], 2)
    m.poke(s["ARY_NIDX"], 1)
    m.poke_w(s["ARY_IDX"] + 0, 7)
    m.poke(s["ARY_OP"], 0)
    m.call("ary_engine")
    err3 = m.peek(s["ARY_ERR"])[0]
    ok_autoh = err3 == 0
    fails += not ok_autoh
    print(f"{'PASS' if ok_autoh else 'FAIL'} ary_engine op=RESOLVE: H(7) "
          f"(undeclared) auto-dims cleanly (err={err3})")

    # ==================================================================
    # Case 7: ERASE (slice 2, docs/spec-basic-arrays-slice2-erase.md §4.2).
    # aeng_erase (op=2): ary_find, then compact the descriptor list by
    # sliding every following descriptor + the $0000 terminator down over
    # the erased one (the moved terminator IS the fix-up -- no stored
    # ARYEND). not-found -> ARY_ERR=2; type is part of the key. Descriptors
    # are hand-built (descriptor_bytes) with a distinct 16-bit marker in
    # element 0 so a surviving neighbour's DATA (not just its header) is
    # asserted intact after the LDIR compaction.
    # ==================================================================
    def peek_w(mm, a):
        b = mm.peek(a, 2)
        return b[0] | (b[1] << 8)

    def build_three(mm):
        """Three back-to-back int arrays A/B/C (each 1-D bound0=2, type 2),
        distinct element-0 markers. Returns the common stride."""
        dA, st = descriptor_bytes(ord("A"), 0, 2, [2])
        dB, _ = descriptor_bytes(ord("B"), 0, 2, [2])
        dC, _ = descriptor_bytes(ord("C"), 0, 2, [2])
        mm.poke(ARYBASE + 0 * st, dA)
        mm.poke(ARYBASE + 1 * st, dB)
        mm.poke(ARYBASE + 2 * st, dC)
        mm.poke(ARYBASE + 3 * st, b"\x00\x00")   # terminator
        mm.poke_w(ARYBASE + 0 * st + 8, 0xAAAA)   # A.elem0 (data starts at desc+8)
        mm.poke_w(ARYBASE + 1 * st + 8, 0xBBBB)   # B.elem0
        mm.poke_w(ARYBASE + 2 * st + 8, 0xCCCC)   # C.elem0
        return st

    def erase(mm, name0, dtype):
        mm.poke_w(s["ARY_KEY"], (name0 << 8))     # name1 = 0
        mm.poke(s["ARY_TYPE"], dtype)
        mm.poke(s["ARY_OP"], 2)                   # op = ERASE
        mm.call("ary_engine")
        return mm.peek(s["ARY_ERR"])[0]

    # -- erase the MIDDLE of three: A stays, C slides down over B --------
    m = make_machine()
    st = build_three(m)
    err = erase(m, ord("B"), 2)
    a_ok = (m.peek(ARYBASE)[0] == ord("A")) and (peek_w(m, ARYBASE + 8) == 0xAAAA)
    c_slid = (m.peek(ARYBASE + st)[0] == ord("C")) and (peek_w(m, ARYBASE + st + 8) == 0xCCCC)
    term_ok = peek_w(m, ARYBASE + 2 * st) == 0    # terminator moved down by one stride
    ok = (err == 0) and a_ok and c_slid and term_ok
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'} ERASE middle: B freed, A intact@base, C+data "
          f"slid down, term relocated (err={err}, A={a_ok}, C={c_slid}, term={term_ok})")

    # -- erase the LAST of three: A,B stay, terminator lands after B -----
    m = make_machine()
    st = build_three(m)
    err = erase(m, ord("C"), 2)
    ab_ok = (m.peek(ARYBASE)[0] == ord("A") and peek_w(m, ARYBASE + 8) == 0xAAAA
             and m.peek(ARYBASE + st)[0] == ord("B") and peek_w(m, ARYBASE + st + 8) == 0xBBBB)
    term_ok = peek_w(m, ARYBASE + 2 * st) == 0
    ok = (err == 0) and ab_ok and term_ok
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'} ERASE last: C freed, A/B+data intact, term "
          f"after B (err={err}, AB={ab_ok}, term={term_ok})")

    # -- erase the ONLY array: terminator lands at ARYBASE (no-arrays) ---
    m = make_machine()
    dA, st = descriptor_bytes(ord("A"), 0, 2, [2])
    m.poke(ARYBASE, dA)
    m.poke(ARYBASE + st, b"\x00\x00")
    err = erase(m, ord("A"), 2)
    ok = (err == 0) and (peek_w(m, ARYBASE) == 0)  # ARYBASE now the $0000 sentinel
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'} ERASE only: A freed, terminator at ARYBASE "
          f"= no-arrays state (err={err}, term@base={peek_w(m, ARYBASE):#06x})")

    # -- not-found -> ARY_ERR=2, descriptors untouched ------------------
    m = make_machine()
    st = build_three(m)
    err = erase(m, ord("Z"), 2)
    untouched = (m.peek(ARYBASE)[0] == ord("A")
                 and m.peek(ARYBASE + 2 * st)[0] == ord("C")
                 and peek_w(m, ARYBASE + 3 * st) == 0)
    ok = (err == 2) and untouched
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'} ERASE absent 'Z' -> ARY_ERR=2, list untouched "
          f"(err={err}, untouched={untouched})")

    # -- type-scoped key: ERASE A as type 8 does NOT match the int 'A' --
    m = make_machine()
    st = build_three(m)           # A/B/C are all type 2 (int)
    err = erase(m, ord("A"), 8)   # ask to erase the DOUBLE 'A' (distinct key)
    a_intact = (m.peek(ARYBASE)[0] == ord("A") and m.peek(ARYBASE + 2)[0] == 2
                and peek_w(m, ARYBASE + 8) == 0xAAAA)
    ok = (err == 2) and a_intact
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'} ERASE type-scoped: A#(double) misses A%(int) "
          f"-> ARY_ERR=2, int A intact (err={err}, intact={a_intact})")

    # -- F1 regression: a STRING-typed key (type 1) never matches a -----
    # numeric descriptor. A default bare `A` is stored as type 8 (double);
    # ex_erase forces a `$` name to type 1, so ary_find must NOT match --
    # else `ERASE A$` would destructively free the numeric `A` (the F1 bug).
    m = make_machine()
    dA, st = descriptor_bytes(ord("A"), 0, 8, [2])   # 'A' as DOUBLE (default bare)
    m.poke(ARYBASE, dA)
    m.poke(ARYBASE + st, b"\x00\x00")
    m.poke_w(ARYBASE + 8, 0x1234)                    # A.elem0 marker (double field low word)
    err = erase(m, ord("A"), 1)                      # string-typed key (type 1)
    a_intact = (m.peek(ARYBASE)[0] == ord("A") and m.peek(ARYBASE + 2)[0] == 8
                and peek_w(m, ARYBASE + 8) == 0x1234)
    ok = (err == 2) and a_intact
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'} ERASE F1: string key (type 1) misses numeric "
          f"A (type 8) -> ARY_ERR=2, A intact (err={err}, intact={a_intact})")

    print()
    print("ALL PASS -- arrays slice-1+2 split (sub/arrays.asm)" if not fails
          else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
