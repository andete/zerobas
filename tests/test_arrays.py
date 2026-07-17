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
    # Arrays slice-4b (docs/spec-basic-arrays-slice4b-scalar-reloc.md §2/Q3):
    # ARYTAB is now the STORED live cell every array-anchor site (ary_find/
    # ary_alloc/strheap_aryend/sg_walk_arrays) reads instead of deriving
    # (PRGEND)+2 -- these tests exercise the ARRAY engine only (an always-
    # empty scalar region), so ARYTAB == ARYBASE throughout.
    m.poke_w(s["ARYTAB"], ARYBASE)
    # "no arrays" sentinel at ARYBASE.
    m.poke(ARYBASE, b"\x00\x00")
    # TEMPTOP = TEMPBASE (empty temp-descriptor stack): a fresh Machine
    # zero-inits ALL RAM, so an unpoked TEMPTOP=0 makes strheap_gc's own
    # root walk (sg_walk_temps) scan every 3-byte stride from $0000 up to
    # TEMPBASE ($E3E1) as a bogus "live" entry -- ~19000 wasted visits,
    # occasionally enough to blow the harness's step budget (a genuine
    # pre-existing gap: ANY ary_alloc call here forces a strheap_gc, since
    # FRETOP is deliberately left at 0 below so the OOM cases can pick up a
    # later HIMEM override via the GC-triggered ceiling recompute, §Case 5).
    # Seeding TEMPTOP to its real cold-boot value (heap_reset's own
    # contract) makes that walk a same-address no-op, matching what a real
    # CLEAR/NEW/RUN would have left behind before any of these entry points
    # ever run. FRETOP is intentionally NOT seeded here (stays 0) -- see the
    # Case 5 OOM comment below for why.
    m.poke_w(s["TEMPTOP"], s["TEMPBASE"])
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
    # Case 5b: terminator-wrap guard (regression, fixed 2026-07-16). If
    # data_end lands EXACTLY on $FFFE/$FFFF, the 2-byte terminator reservation
    # wraps candidate_end to $0000/$0001, which then SLIPS the ceiling sbc
    # (it is compared against the WRAPPED value) -- the old two unchecked
    # `inc hl` (16-bit INC sets no carry) accepted the alloc and let the
    # descriptor write + zero-fill corrupt top-of-RAM instead of raising OOM.
    # Fix: reserve the terminator with a carry-checked `add hl,2 / jp c`. With
    # HIMEM=0 the ceiling is TXTMAX, and the wrapped $0000/$0001 candidate is
    # below ANY ceiling, so ONLY this guard -- not the ceiling -- can catch it
    # (revert the fix and this case returns CF set / A=0, a wrapped alloc).
    # data_end = TAIL + header(6+2*ndim=8) + data_bytes(1 elem * elsize 2) =
    # TAIL + 10, so TAIL=$FFF4 -> data_end=$FFFE (PRGEND=$FFF2); TAIL=$FFF5 ->
    # $FFFF. Pre-existing slice-1 alloc bug; 65-B string elements widened the
    # window (Fable slice-3 adversarial review).
    # ==================================================================
    for prgend, dend in ((0xFFF2, 0xFFFE), (0xFFF3, 0xFFFF)):
        m = make_machine()
        arybase = prgend + 2
        m.poke_w(s["PRGEND"], prgend)
        m.poke_w(s["ARYTAB"], arybase)  # re-anchor ARYTAB with PRGEND (§Q3)
        m.poke_w(s["HIMEM"], 0)        # ceiling = TXTMAX (wrapped candidate slips it)
        m.poke_w(arybase, 0)           # empty array region: $0000 terminator at TAIL
        BOUNDS_BUF = 0x9200
        m.poke_w(BOUNDS_BUF, 0)        # bound0=0 -> 1 element
        m.poke(s["ARY_NIDX"], 1)
        cpu = m.call("ary_alloc", b=ord("W"), c=0, a=2, ix=BOUNDS_BUF)
        ok_wrap = (not carry(cpu)) and (cpu.a == 4)
        fails += not ok_wrap
        print(f"{'PASS' if ok_wrap else 'FAIL'} ary_alloc terminator-wrap "
              f"(data_end={dend:#06x}) -> OOM not corruption "
              f"(CF={carry(cpu)}, A={cpu.a})")

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

    # ==================================================================
    # Case 8: Arrays slice-4b (docs/spec-basic-arrays-slice4b-scalar-
    # reloc.md) -- numeric SCALAR relocation: the insert-and-shift
    # mechanism (§3a) + the FRETOP collision/GC-once-retry math (§3a step
    # 3/4), exercised through ary_engine's ACTUAL dispatch entry (ARY_OP=4
    # SCALAR_FIND / 5 SCALAR_ALLOC, Q4) -- the SAME ABI surface vars.asm's
    # var_find_typed/var_alloc_or_find glue drives via ary_engine_call.
    # Non-vacuous: reverting the collision-BEFORE-move ordering (moving the
    # array block unconditionally, THEN checking FRETOP) turns case 8e
    # green-but-CORRUPTING instead of a clean OOM -- caught by the
    # "ARYTAB unchanged" assertion there, not just CF/ARY_ERR=4.
    # ==================================================================
    def scalar_find(name0, dtype, name1=0):
        set_key(name0, name1)
        m.poke(s["ARY_TYPE"], dtype)
        m.poke(s["ARY_OP"], 4)             # op = SCALAR_FIND
        m.call("ary_engine")
        return peek_w(m, s["ARY_ADDR"]), m.peek(s["ARY_ERR"])[0]

    def scalar_alloc(name0, dtype, name1=0):
        set_key(name0, name1)
        m.poke(s["ARY_TYPE"], dtype)
        m.poke(s["ARY_OP"], 5)             # op = SCALAR_ALLOC
        m.call("ary_engine")
        return peek_w(m, s["ARY_ADDR"]), m.peek(s["ARY_ERR"])[0]

    # -- 8a: find on an empty scalar region -> not-found (ARY_ADDR=0) -----
    m = make_machine()
    addr, err = scalar_find(ord("X"), 8)
    ok = (addr == 0) and (err == 0)
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'} SCALAR_FIND on empty region: not "
          f"found (ARY_ADDR={addr:#06x}, ARY_ERR={err})")

    # -- 8b: alloc creates the entry at the scalar base, zero-filled; -----
    # ARYTAB advances by stride (type+3=11 for a double); a second find
    # sees the SAME entry unchanged (no re-insert on a hit).
    m = make_machine()
    addr, err = scalar_alloc(ord("X"), 8)      # double, stride 11
    ok_new = (addr == ARYBASE) and (err == 0)
    fails += not ok_new
    print(f"{'PASS' if ok_new else 'FAIL'} SCALAR_ALLOC 'X#' creates at "
          f"ARYBASE (addr={addr:#06x}, err={err})")
    entry = m.peek(addr, 11)
    ok_entry = (entry[0] == ord("X") and entry[1] == 0 and entry[2] == 8
                and entry[3:] == bytes(8))
    fails += not ok_entry
    print(f"{'PASS' if ok_entry else 'FAIL'} 'X#' entry = "
          f"[name0][name1][type][value:8=0] ({entry.hex()})")
    new_arytab = peek_w(m, s["ARYTAB"])
    ok_arytab = new_arytab == ARYBASE + 11
    fails += not ok_arytab
    print(f"{'PASS' if ok_arytab else 'FAIL'} ARYTAB advanced by stride 11 "
          f"({new_arytab:#06x}, want {ARYBASE + 11:#06x})")
    addr2, err2 = scalar_find(ord("X"), 8)
    ok_refind = (addr2 == ARYBASE) and (err2 == 0)
    fails += not ok_refind
    print(f"{'PASS' if ok_refind else 'FAIL'} re-find 'X#' unchanged "
          f"(addr={addr2:#06x})")

    # -- 8c: insert-and-shift -- an EXISTING array survives a scalar's -----
    # insertion (CONTENT, not just its new address -- the standing 4a
    # lesson applied to 4b). Array 'A' (int, 1-D bound0=2) sits at ARYBASE;
    # a scalar 'Z%' (stride 5) must shift the WHOLE array block up by 5 and
    # leave its element-0 marker intact.
    m = make_machine()
    dA, stA = descriptor_bytes(ord("A"), 0, 2, [2])
    m.poke(ARYBASE, dA)
    m.poke_w(ARYBASE + stA, 0)             # array-region terminator
    m.poke_w(ARYBASE + 8, 0xBEEF)          # elem0 marker (data starts at +8)
    addr_z, err_z = scalar_alloc(ord("Z"), 2)   # int, stride 5
    ok_z = (addr_z == ARYBASE) and (err_z == 0)
    fails += not ok_z
    print(f"{'PASS' if ok_z else 'FAIL'} SCALAR_ALLOC 'Z%' inserted at the "
          f"old ARYBASE (addr={addr_z:#06x}, err={err_z})")
    new_base = peek_w(m, s["ARYTAB"])
    ok_shift = new_base == ARYBASE + 5
    fails += not ok_shift
    print(f"{'PASS' if ok_shift else 'FAIL'} ARYTAB (array base) shifted by "
          f"stride 5 ({new_base:#06x}, want {ARYBASE + 5:#06x})")
    a_name0 = m.peek(new_base)[0]
    a_elem0 = peek_w(m, new_base + 8)
    ok_content = (a_name0 == ord("A")) and (a_elem0 == 0xBEEF)
    fails += not ok_content
    print(f"{'PASS' if ok_content else 'FAIL'} array 'A' CONTENT survived "
          f"the shift (name0={chr(a_name0)}, elem0={a_elem0:#06x}, want beef)")
    # ary_find must now see 'A' at its NEW (shifted) address.
    cpu = m.call("ary_find", b=ord("A"), c=0, a=2)
    ok_find = carry(cpu) and (cpu.hl == new_base)
    fails += not ok_find
    print(f"{'PASS' if ok_find else 'FAIL'} ary_find locates shifted 'A' at "
          f"{cpu.hl:#06x} (want {new_base:#06x})")

    # -- 8d: FRETOP collision -> GC-once -> success (§3a steps 3-4) --------
    # A tight FRETOP collides with the FIRST attempt; strheap_gc recomputes
    # it from the (loose) ceiling min(HIMEM,TXTMAX) and the retry succeeds.
    m = make_machine()
    m.poke_w(s["HIMEM"], 0)                # ceiling after GC = TXTMAX
    m.poke_w(s["FRETOP"], ARYBASE + 8)      # tight: collides with 'Y#' (11 B)
    addr_y, err_y = scalar_alloc(ord("Y"), 8)
    ok_gc = (addr_y == ARYBASE) and (err_y == 0)
    fails += not ok_gc
    print(f"{'PASS' if ok_gc else 'FAIL'} SCALAR_ALLOC 'Y#' collides once, "
          f"GCs, retries, succeeds (addr={addr_y:#06x}, err={err_y})")
    ok_fretop = peek_w(m, s["FRETOP"]) == s["TXTMAX"]
    fails += not ok_fretop
    print(f"{'PASS' if ok_fretop else 'FAIL'} FRETOP recomputed to TXTMAX "
          f"by the retry GC ({peek_w(m, s['FRETOP']):#06x})")

    # -- 8e: genuine OOM -- even after the GC-retry, still no room. --------
    # NON-VACUOUS proof: asserts CF clear + ARY_ERR=4 AND that ARYTAB did
    # NOT move -- nothing was written or shifted (the collision-check-
    # before-move ordering, §3a step 3).
    m = make_machine()
    m.poke_w(s["HIMEM"], ARYBASE + 4)      # tight even after the GC recompute
    m.poke_w(s["FRETOP"], ARYBASE + 4)     # tight from the start too
    before = peek_w(m, s["ARYTAB"])
    addr_oom, err_oom = scalar_alloc(ord("Q"), 8)
    ok_oom = (addr_oom == 0) and (err_oom == 4)
    fails += not ok_oom
    print(f"{'PASS' if ok_oom else 'FAIL'} SCALAR_ALLOC 'Q#' exhausts the "
          f"chain -> ARY_ERR=4 (addr={addr_oom:#06x}, err={err_oom})")
    after = peek_w(m, s["ARYTAB"])
    ok_notouch = after == before
    fails += not ok_notouch
    print(f"{'PASS' if ok_notouch else 'FAIL'} OOM left ARYTAB UNTOUCHED "
          f"(before={before:#06x}, after={after:#06x})")

    # ==================================================================
    # Case 9: Arrays slice-4c (docs/spec-basic-arrays-slice4c-string-
    # scalar-unification.md §3a/§3b) -- the elsize_from_type-driven scalar
    # stride (scv_alloc/scv_find, sub/arrays.asm) and the sg_walk_scalars
    # GC-root descriptor offset (sub/strheap.asm). Non-vacuous: reverting
    # either the STRIDE substitution (back to raw "type+3", giving a
    # type=1 entry stride 4 instead of 6) or the sg_walk_scalars visit
    # offset (entry+3 -> entry+2) turns the assertions below RED.
    # ==================================================================

    # -- 9a: SCALAR_ALLOC of a STRING scalar (type=1) strides by ----------
    # elsize_from_type(1)+3 = 6, NOT raw type+3 = 4; the fresh entry's
    # 3-byte value field ([len][ptr]) is zero-filled in FULL (not just 1
    # byte, which is what a reverted "B=type" zero-fill count would leave).
    m = make_machine()
    addr_s, err_s = scalar_alloc(ord("S"), 1)          # string, elsize 3
    ok_s = (addr_s == ARYBASE) and (err_s == 0)
    fails += not ok_s
    print(f"{'PASS' if ok_s else 'FAIL'} SCALAR_ALLOC 'S$' (type=1) creates "
          f"at ARYBASE (addr={addr_s:#06x}, err={err_s})")
    entry_s = m.peek(addr_s, 6)
    ok_entry_s = (entry_s[0] == ord("S") and entry_s[1] == 0
                  and entry_s[2] == 1 and entry_s[3:] == bytes(3))
    fails += not ok_entry_s
    print(f"{'PASS' if ok_entry_s else 'FAIL'} 'S$' entry = "
          f"[name0][name1][type=1][len=0][ptr=0] fully zero-filled 3 B "
          f"({entry_s.hex()})")
    arytab_s = peek_w(m, s["ARYTAB"])
    ok_stride6 = arytab_s == ARYBASE + 6
    fails += not ok_stride6
    print(f"{'PASS' if ok_stride6 else 'FAIL'} ARYTAB advanced by "
          f"elsize_from_type(1)+3=6, NOT raw type+3=4 "
          f"({arytab_s:#06x}, want {ARYBASE + 6:#06x})")

    # -- 9b: scv_find's skip walk (scvf_skip) over a STRING entry uses the -
    # SAME elsize-driven stride -- a second (numeric) scalar allocated
    # after a string one must land 6 bytes past it, and both must
    # re-SCALAR_FIND at their correct (distinct) addresses afterward.
    m = make_machine()
    scalar_alloc(ord("S"), 1)                          # 'S$' at ARYBASE, stride 6
    addr_n, err_n = scalar_alloc(ord("N"), 8)           # 'N#' double, stride 11
    ok_n_addr = (addr_n == ARYBASE + 6) and (err_n == 0)
    fails += not ok_n_addr
    print(f"{'PASS' if ok_n_addr else 'FAIL'} SCALAR_ALLOC 'N#' lands at "
          f"ARYBASE+6 (past the 6-byte string entry), not ARYBASE+4 "
          f"(addr={addr_n:#06x}, want {ARYBASE + 6:#06x})")
    addr_s2, err_s2 = scalar_find(ord("S"), 1)
    ok_refind_s = (addr_s2 == ARYBASE) and (err_s2 == 0)
    fails += not ok_refind_s
    print(f"{'PASS' if ok_refind_s else 'FAIL'} re-SCALAR_FIND 'S$' still "
          f"at ARYBASE (addr={addr_s2:#06x})")
    addr_n2, err_n2 = scalar_find(ord("N"), 8)
    ok_refind_n = (addr_n2 == ARYBASE + 6) and (err_n2 == 0)
    fails += not ok_refind_n
    print(f"{'PASS' if ok_refind_n else 'FAIL'} SCALAR_FIND 'N#' locates "
          f"it past the string entry's 6-byte stride (addr={addr_n2:#06x}, "
          f"want {ARYBASE + 6:#06x}) -- proves scvf_skip's own walk used "
          f"elsize_from_type, not raw type+3")

    # -- 9c: sg_walk_scalars (sub/strheap.asm) visits a string scalar's ---
    # descriptor at entry+3 (past [name0][name1][type]), NOT entry+2 (the
    # old STRTAB-slot offset). Built directly against sg_walk_scalars
    # (skipping strheap_gc's sort/compaction machinery, which is out of
    # scope here): a hand-built chain of [numeric 'N#'][string 'S$'], with
    # 'S$'.ptr deliberately placed INSIDE the [OLD_FRETOP,CEIL) window and
    # its OWN [len][ptr] bytes chosen so that reading them ONE BYTE EARLY
    # (the entry+2 regression, which would treat the type byte as "len"
    # and the true [len][ptr_lo] pair as a bogus 2-byte "ptr") lands
    # OUTSIDE that window -- so the MODE=0 (count) root tally is 1 with
    # the correct +3 offset and 0 under a +2 regression: non-vacuous.
    m = make_machine()
    FRAME = 0x9500                      # scratch IX frame (mirrors strheap_gc's
                                        # own 22-byte layout, §"Own scratch
                                        # frame" strheap.asm:393-396); only the
                                        # fields sg_walk_scalars/sg_visit's
                                        # MODE=0 path touch are seeded
    OLD_FRETOP = 0xE000
    CEIL = 0xF000
    STR_PTR = 0xE500                    # inside [OLD_FRETOP,CEIL) -- a real
                                        # heap body is never dereferenced by
                                        # MODE=0 (sg_inrange only range-checks
                                        # the ptr value, per its own header)
    m.poke_w(FRAME + 0, OLD_FRETOP)     # +0 OLD_FRETOP
    m.poke_w(FRAME + 2, CEIL)           # +2 CEIL
    m.poke_w(FRAME + 4, 0)              # +4 N (count) = 0
    m.poke(FRAME + 20, 0)               # +20 MODE = 0 (count)
    entry_n = bytes([ord("N"), 0, 8]) + bytes(8)    # [name0][name1][type=8][val:8=0]
    entry_str = bytes([ord("S"), 0, 1, 5,
                        STR_PTR & 0xFF, (STR_PTR >> 8) & 0xFF])  # [S][0][1][len=5][ptr]
    m.poke(ARYBASE, entry_n)                        # 11 B numeric entry
    m.poke(ARYBASE + 11, entry_str)                 # 6 B string entry
    m.poke_w(s["ARYTAB"], ARYBASE + 11 + 6)          # scalar-region end
    m.call("sg_walk_scalars", ix=FRAME)
    count = peek_w(m, FRAME + 4)
    ok_walk = count == 1
    fails += not ok_walk
    print(f"{'PASS' if ok_walk else 'FAIL'} sg_walk_scalars visits exactly "
          f"1 root (the string entry's descriptor at entry+3) -- N={count}, "
          f"want 1 (a +3->+2 offset regression reads the TYPE byte as "
          f"[len] and the true [len][ptr_lo] as a bogus out-of-range ptr, "
          f"which sg_inrange rejects -> N would read 0)")

    print()
    print("ALL PASS -- arrays slice-1+2+4b+4c split (sub/arrays.asm)" if not fails
          else f"{fails} CASE(S) FAILED")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
