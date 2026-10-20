# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: D-DEEPEXPR (2026-10-20) -- stack room inside an expression, per site
(docs/spec-basic-deepexpr-guard.md §8.3).

Near the memory edge a deep expression overwrote the arrays or crashed where the
VG-8020 refuses with Out of memory (scratchpad/deepexpr_run.out, rows lb1-lb4).
The fix tests the stack at every place the string evaluator recurses, in front of
every expression-time string-heap op, and caps an allocation's ceiling at the live
SP. This file drives each of those pieces on the host Z80, placing the "arrays"
(CTLLIM) right under the stack the way tests/test_control_flow.py pokes the pool:

  U1  stk_room: its threshold equals stk_guard's to the byte, both sides of it;
      registers preserved; FPERR 6 only on a refusal; first-error-wins.
  U2  sh_go_g's skip contract: the tenant is NOT entered; A=6, NZ, CF clear,
      HL=STR_EMPTY, DE=0, BC kept; a caller-pushed 4th word stays balanced.
  U3  per caller: str_temp_alloc -> STR_EMPTY / DE=0 and ERR 7 (not 14); a
      snapshot publishes STR_EMPTY (never the source); INSTR and FRE("") never
      read STR_EMPTY's address as a number (P3); a string store with a fault
      pending stores nothing and raises it (P2).
  U4  the recursion arms: a 40-deep string paren, a 20-deep LEFT$ source nest and
      a string FN decline with ERR 7 deferred and NEVER take the stack below
      CTLLIM -- the property the canary rows measure on the machine.
  U5  the str_eval_plus loop: `+++"X"` is "X", `+++5` declines with the cursor on
      the first `+`, and the depth is the SAME for 1 and 100 `+`.
  U6  sp_ceil (sub ROM): min() both ways and its offset; then a real ary_alloc of
      Z#(10,10) swept upward in SP from just above the array: every SP either
      refuses (A=4) or fits with the zero-filled data intact and the stack never
      below the array's end.

Oracle basis: the reference's verdicts on these shapes are the probe rows
(scratchpad/deepexpr_probe.py); this file checks zerobas's own mechanism and its
safety property (no stack write at or below CTLLIM / the array's end), which no
reference reading can show directly.
"""

import os
import subprocess
import sys

from _tmp import tp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine, carry, zero  # noqa: E402

ROM = tp("zb_deepexpr.rom")
SYM = tp("zb_deepexpr.sym")
SUB_ROM = tp("zb_deepexpr_sub.rom")
SUB_SYM = tp("zb_deepexpr_sub.sym")
RELOC_BASE = 0x2781

SRC = 0xC000       # ASCII expression source
TOKBUF = 0xC100    # crunched-token buffer (256 B cleared per case)
SETSRC = 0xC300    # a stable [len][ptr] source descriptor
BODY = 0xC500      # the body SETSRC points at
STUB = 0xC800      # tiny RAM caller stubs
SP_SITE = 0xF380   # Machine.call's SP before it pushes the return sentinel


def build():
    subprocess.run(["pasmo", "--bin", os.path.join(ROOT, "basic", "main.asm"), ROM, SYM],
                   check=True, capture_output=True)
    subprocess.run(["pasmo", "-I", os.path.join(ROOT, "sub"), "--bin",
                    os.path.join(ROOT, "sub", "sub.asm"), SUB_ROM, SUB_SYM],
                   check=True, capture_output=True, cwd=ROOT)


def track_min_sp(m):
    """Wrap the CPU's step so every call reports the lowest SP the MAIN side
    reached (the tenant bridge runs on another core and is not counted)."""
    lo = [0x10000]
    step = m.cpu.step

    def tracked():
        step()
        if m.cpu.sp < lo[0]:
            lo[0] = m.cpu.sp
    m.cpu.step = tracked
    return lo


def run():
    build()
    m = Machine(ROM, SYM, rom_base=RELOC_BASE)
    s = m.sym
    # The string-heap scaffold test_str_engine.py uses: a program end, an empty
    # variable chain, a CLEAR 4096-sized pool, a cold heap.
    m.poke_w(s["PRGEND"], 0x9000)
    m.poke(0x9000, b"\x00\x00")
    m.poke_w(s["ARYTAB"], 0x9002)
    m.poke(0x9002, b"\x00\x00")
    m.poke_w(s["POOLSIZE"], 4096)
    m.call("heap_reset")

    R = s["STK_EVAL_RESERVE"]
    CTLLIM, FPERR, STRPTR = s["CTLLIM"], s["FPERR"], s["STRPTR"]
    TEMPPT, TEMPPOOL = s["TEMPPT"], s["TEMPPOOL"]
    STR_EMPTY = s["STR_EMPTY"]
    OOM, STROOM = s["FPERR_OOM"], s["FPERR_STROOM"]
    lo = track_min_sp(m)
    fails = 0

    def check(label, ok, detail=""):
        nonlocal fails
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f"  [{detail}]" if detail and not ok else ""))

    def fresh(ctllim):
        """A statement boundary: no pending fault, an empty temp stack, and the
        'arrays' ending at ctllim."""
        m.poke(FPERR, 0)
        m.poke(s["ERRMARK"], 0)
        m.poke_w(TEMPPT, TEMPPOOL)
        m.poke_w(CTLLIM, ctllim)
        lo[0] = 0x10000

    def tok(text):
        m.poke(SRC, text.encode("ascii") + b"\x00")
        m.mem[TOKBUF:TOKBUF + 256] = b"\x00" * 256
        m.call("tokenise", hl=SRC, de=TOKBUF)

    def desc_bytes(addr):
        n = m.mem[addr]
        p = m.mem[addr + 1] | (m.mem[addr + 2] << 8)
        return bytes(m.mem[p:p + n])

    def str_eval(text, ctllim):
        tok(text)
        fresh(ctllim)
        m.poke_w(STRPTR, 0)
        cpu = m.call("str_eval", hl=TOKBUF)
        ptr = m.mem[STRPTR] | (m.mem[STRPTR + 1] << 8)
        return cpu, ptr

    def num_eval(text, ctllim):
        tok(text)
        fresh(ctllim)
        cpu = m.call("eval", hl=TOKBUF)
        return cpu.de & 0xFFFF

    LOOSE = 0x9100          # CTLLIM far below the stack: every test passes

    # ------------------------------------------------------------------
    print("# --- U1 stk_room: stk_guard's threshold, non-dropping ---")
    # Both called from a 1-instruction RAM stub so the call site's SP is the same:
    # `call <guard>` / `ret`. stk_guard DROPS its frame on a refusal and leaves
    # through ev_f_defer, which then returns to the stub's caller -- also fine.
    def stub_call(target):
        a = s[target]
        m.poke(STUB, bytes([0xCD, a & 0xFF, a >> 8, 0xC9]))

    def threshold(target):
        """The LOWEST CTLLIM at which `target` refuses, from the stub."""
        stub_call(target)
        for c in range(SP_SITE - 200, SP_SITE - 60):
            fresh(c)
            cpu = m.call(STUB)
            if m.mem[FPERR] == OOM:
                return c, cpu
        return None, None

    t_room, _ = threshold("stk_room")
    t_guard, _ = threshold("stk_guard")
    check(f"stk_room refuses from CTLLIM ${t_room or 0:04X}, stk_guard from "
          f"${t_guard or 0:04X} -- the same byte", t_room is not None and t_room == t_guard)
    # the boundary itself, both sides, with every register watched
    stub_call("stk_room")
    for c, want_ok in ((t_room - 1, True), (t_room, False)):
        fresh(c)
        cpu = m.call(STUB, a=0x42, bc=0x9ABC, de=0x5678, hl=0x1234)
        kept = cpu.bc == 0x9ABC and cpu.de == 0x5678 and cpu.hl == 0x1234
        if want_ok:
            check("one byte above it: CF set, A/BC/DE/HL kept, FPERR 0",
                  carry(cpu) and kept and cpu.a == 0x42 and m.mem[FPERR] == 0,
                  f"CF={carry(cpu)} A={cpu.a} FPERR={m.mem[FPERR]}")
        else:
            check("at it: CF clear, A=6, BC/DE/HL kept, FPERR 6 (ERR 7)",
                  not carry(cpu) and kept and cpu.a == OOM and m.mem[FPERR] == OOM,
                  f"CF={carry(cpu)} A={cpu.a} FPERR={m.mem[FPERR]}")
    fresh(t_room)
    m.poke(FPERR, 4)
    m.call(STUB)
    check("a fault already pending (4) is kept: first error wins", m.mem[FPERR] == 4)

    # ------------------------------------------------------------------
    print("# --- U2 sh_go_g: the skip contract ---")
    entered = [0]
    sc = s["sc_call"]
    saved = m.traps.get(sc)
    m.trap("sc_call", lambda mm: entered.__setitem__(0, entered[0] + 1))
    fresh(SP_SITE)                     # nothing fits
    cpu = m.call("sh_go_g", a=3, bc=0x9ABC, de=0x5678, hl=0x1234)
    check("refused: tenant not entered, A=6 NZ CF clear, HL=STR_EMPTY DE=0 BC kept, FPERR 6",
          entered[0] == 0 and cpu.a == OOM and not zero(cpu) and not carry(cpu)
          and cpu.hl == STR_EMPTY and cpu.de == 0 and cpu.bc == 0x9ABC
          and m.mem[FPERR] == OOM,
          f"entered={entered[0]} A={cpu.a} HL={cpu.hl:#06x} DE={cpu.de:#06x} BC={cpu.bc:#06x}")
    a = s["sh_go_g"]
    # ld bc,$1111 / push bc / ld a,5 / call sh_go_g / pop bc / ret -- op 5's pushed 4th word
    m.poke(STUB, bytes([0x01, 0x11, 0x11, 0xC5, 0x3E, 0x05, 0xCD, a & 0xFF, a >> 8, 0xC1, 0xC9]))
    fresh(SP_SITE)
    cpu = m.call(STUB)
    check("refused with a caller-pushed 4th word: the caller pops its own word back",
          cpu.bc == 0x1111 and entered[0] == 0, f"BC={cpu.bc:#06x}")
    fresh(LOOSE)
    m.call("sh_go_g", a=3, hl=0)
    check("with room the tenant IS entered (once)", entered[0] == 1, f"entered={entered[0]}")
    if saved is None:
        del m.traps[sc]
    else:
        m.traps[sc] = saved

    # ------------------------------------------------------------------
    print("# --- U3 the callers' publish rules (P1-P3) ---")
    fresh(SP_SITE)
    cpu = m.call("str_temp_alloc", a=5)
    check("str_temp_alloc refused: HL=STR_EMPTY, DE=0, FPERR 6 -- ERR 7, not 14",
          cpu.hl == STR_EMPTY and cpu.de == 0 and m.mem[FPERR] == OOM
          and m.mem[FPERR] != STROOM and (m.mem[TEMPPT] | m.mem[TEMPPT + 1] << 8) == TEMPPOOL,
          f"HL={cpu.hl:#06x} DE={cpu.de:#06x} FPERR={m.mem[FPERR]}")
    m.poke(BODY, b"ABC")
    m.poke(SETSRC, bytes([3]))
    m.poke_w(SETSRC + 1, BODY)
    fresh(SP_SITE)
    m.poke_w(STRPTR, SETSRC)
    cpu = m.call("str_snapshot_to_temp")
    sp = m.mem[STRPTR] | (m.mem[STRPTR + 1] << 8)
    check("a refused snapshot publishes STR_EMPTY, never the SOURCE (P1)",
          sp == STR_EMPTY and cpu.hl == STR_EMPTY and m.mem[FPERR] == OOM,
          f"STRPTR={sp:#06x}")

    def sweep_num(text, want):
        """Every CTLLIM from tight to loose: the value is right with nothing
        pending, or ERR 7 is pending and the value is NOT STR_EMPTY's address."""
        seen_ok = seen_oom = False
        bad = []
        # D-EVALSLOPE (2026-10-20): the window reaches to SP_SITE - 40. The one
        # climber reaches its first factor ~10 B shallower than the old three
        # layers did, so at SP_SITE - 100 `VAL("12")` already had room and this
        # sweep saw no refusal at all -- a geometry that could no longer reach
        # the case it is about, not a change in the case.
        for c in range(SP_SITE - 360, SP_SITE - 40, 3):
            v = num_eval(text, c)
            e = m.mem[FPERR]
            if e == 0:
                seen_ok = True
                if v != want:
                    bad.append((c, v, e))
            elif e == OOM:
                seen_oom = True
                if v == STR_EMPTY:
                    bad.append((c, v, e))
            else:
                bad.append((c, v, e))
        return seen_ok, seen_oom, bad

    for text, want in (('INSTR("ABC","C")', 3), ('VAL("12")', 12), ('LEN("AB"+"CD")', 4)):
        ok_, oom_, bad = sweep_num(text, want)
        check(f"{text}: right with room, ERR 7 without, never {STR_EMPTY} (P3)",
              ok_ and oom_ and not bad, f"ok={ok_} oom={oom_} bad={bad[:3]}")
    fre_ref = num_eval('FRE("")', LOOSE)
    ok_, oom_, bad = sweep_num('FRE("")', fre_ref)
    check(f'FRE(""): {fre_ref} with room, 0 or ERR 7 without, never {STR_EMPTY} (P3)',
          ok_ and oom_ and not bad, f"ok={ok_} oom={oom_} bad={bad[:3]}")

    # P2: a string store with a fault pending stores nothing and raises it.
    raised = []
    m.trap("fp_runtime_error", lambda mm: raised.append(mm.mem[FPERR]))

    def set_var(value, pending):
        m.poke(BODY, value)
        m.poke(SETSRC, bytes([len(value)]))
        m.poke_w(SETSRC + 1, BODY)
        fresh(LOOSE)
        m.call("str_set_key", b=ord("K"), c=0, de=SETSRC)   # (creates K$ once)
        m.poke(FPERR, pending)
        m.poke_w(CTLLIM, LOOSE)

    def get_k():
        cpu = m.call("str_get_key", b=ord("K"), c=0)
        return desc_bytes(cpu.hl)

    m.poke(BODY, b"KEEP")
    m.poke(SETSRC, bytes([4]))
    m.poke_w(SETSRC + 1, BODY)
    fresh(LOOSE)
    m.call("str_set_key", b=ord("K"), c=0, de=SETSRC)
    check('control: K$="KEEP" stores with nothing pending', get_k() == b"KEEP" and not raised)
    m.poke(BODY, b"NEW")
    m.poke(SETSRC, bytes([3]))
    fresh(LOOSE)
    m.poke(FPERR, OOM)
    m.call("str_set_key", b=ord("K"), c=0, de=SETSRC)
    check("with ERR 7 pending, K$=\"NEW\" stores nothing and raises the 7 (P2)",
          get_k() == b"KEEP" and raised == [OOM], f"K$={get_k()!r} raised={raised}")
    del m.traps[s["fp_runtime_error"]]

    # ------------------------------------------------------------------
    print("# --- U4 the recursion arms decline, ERR 7 deferred, stack above CTLLIM ---")
    TIGHT = SP_SITE - 200      # the lb1 shape: ~200 B under the statement
    cpu, ptr = str_eval('((("X")))', LOOSE)
    check('control: ((("X"))) is "X" with room', carry(cpu) and desc_bytes(ptr) == b"X")
    deep = "(" * 40 + '"X"' + ")" * 40
    cpu, _ = str_eval(deep, TIGHT)
    check("40-deep string paren at ~200 B: CF clear, HL on the first '(', FPERR 6, "
          f"stack never below CTLLIM (lowest SP ${lo[0]:04X}, CTLLIM ${TIGHT:04X})",
          not carry(cpu) and cpu.hl == TOKBUF and m.mem[FPERR] == OOM and lo[0] > TIGHT,
          f"CF={carry(cpu)} HL={cpu.hl:#06x} FPERR={m.mem[FPERR]} lowSP={lo[0]:#06x}")
    cpu, ptr = str_eval('LEFT$(LEFT$("ABC",2),1)', LOOSE)
    check('control: LEFT$(LEFT$("ABC",2),1) is "A" with room',
          carry(cpu) and desc_bytes(ptr) == b"A", f"got {desc_bytes(ptr)!r}")
    nest = "LEFT$(" * 20 + '"ABC"' + ",3)" * 20       # row lb3's depth (SRC holds 256 B)
    cpu, _ = str_eval(nest, TIGHT)
    check("20-deep LEFT$ source nest at ~200 B: declines, FPERR 6, stack never below "
          f"CTLLIM (lowest SP ${lo[0]:04X})",
          not carry(cpu) and m.mem[FPERR] == OOM and lo[0] > TIGHT,
          f"CF={carry(cpu)} FPERR={m.mem[FPERR]} lowSP={lo[0]:#06x}")
    cpu, _ = str_eval("FNA$", SP_SITE)
    check("a string FN with no room: declines with HL on the FN token, FPERR 6",
          not carry(cpu) and cpu.hl == TOKBUF and m.mem[TOKBUF] == s["FN_TOKEN"]
          and m.mem[FPERR] == OOM, f"CF={carry(cpu)} HL={cpu.hl:#06x} FPERR={m.mem[FPERR]}")

    # ------------------------------------------------------------------
    print("# --- U5 str_eval_plus is a loop ---")
    cpu, ptr = str_eval('+++"X"', LOOSE)
    check('+++"X" is "X"', carry(cpu) and desc_bytes(ptr) == b"X")
    cpu, _ = str_eval("+++5", LOOSE)
    check("+++5 declines with HL on the FIRST '+'", not carry(cpu) and cpu.hl == TOKBUF,
          f"HL={cpu.hl:#06x}")
    str_eval('+"X"', LOOSE)
    one = lo[0]
    cpu, ptr = str_eval("+" * 100 + '"X"', LOOSE)
    check(f"the depth is the same for 1 and 100 '+' (lowest SP ${one:04X} / ${lo[0]:04X})",
          carry(cpu) and desc_bytes(ptr) == b"X" and lo[0] == one)
    cpu, ptr = str_eval("+" * 120 + '"X"', SP_SITE - 160)
    check("120 '+' at ~160 B: completes, nothing pending, stack above CTLLIM (row lb2)",
          carry(cpu) and desc_bytes(ptr) == b"X" and m.mem[FPERR] == 0
          and lo[0] > SP_SITE - 160, f"CF={carry(cpu)} FPERR={m.mem[FPERR]}")

    # ------------------------------------------------------------------
    print("# --- U6 sp_ceil: an allocation's ceiling is also the live SP ---")
    u = Machine(SUB_ROM, SUB_SYM, rom_base=0)
    t = u.sym
    RA = t["STK_ALLOC_RESERVE"]
    for hl, want in ((0xF000, 0xF000), (0xF370, SP_SITE - RA), (SP_SITE - RA, SP_SITE - RA)):
        cpu = u.call("sp_ceil", hl=hl)
        check(f"sp_ceil(${hl:04X}) = ${want:04X} (call site SP ${SP_SITE:04X} - {RA})",
              cpu.hl == want, f"got {cpu.hl:#06x}")
    # A real Z#(10,10) allocation: 121 doubles, at a fixed base just above $9002.
    ARYBASE = 0x9002
    u.poke_w(t["PRGEND"], 0x9000)
    u.poke(0x9000, b"\x00\x00")
    u.poke_w(t["HIMEM"], 0)
    u.poke_w(t["ARYTAB"], ARYBASE)
    u.poke_w(t["TEMPPT"], t["TEMPPOOL"])
    BOUNDS = 0x9F00
    data_end = ARYBASE + 6 + 2 * 2 + 121 * 8         # header + bounds + data
    ulo = track_min_sp(u)
    fit_sps, refused = [], 0
    bad = []
    for spsite in range(data_end, data_end + RA + 56):   # past the reserve, whatever it is
        u.poke(ARYBASE, b"\x00\x00")                 # no arrays yet
        u.mem[ARYBASE + 2:data_end + 2] = b"\xA5" * (data_end - ARYBASE)
        u.poke(t["ARY_NIDX"], 2)
        u.poke_w(BOUNDS + 2, 10)                      # subscript 0 at the high end
        u.poke_w(BOUNDS, 10)
        u.poke_w(t["ARY_IDXP"], BOUNDS + 2)
        u.cpu.sp = spsite
        ulo[0] = 0x10000
        cpu = u.call("ary_alloc", keep_sp=True, b=ord("Z"), c=0, a=8, ix=BOUNDS + 2)
        if carry(cpu):
            fit_sps.append(spsite)
            data = bytes(u.mem[ARYBASE + 10:data_end])
            if data != bytes(len(data)) or ulo[0] < data_end + 2:
                bad.append((spsite, ulo[0]))
        elif cpu.a == 4:
            refused += 1
        else:
            bad.append((spsite, "A=%d" % cpu.a))
    first = fit_sps[0] if fit_sps else None
    check(f"Z#(10,10) under a live SP: refused while SP-{RA} is below its end, fits "
          f"from SP ${first or 0:04X} (end ${data_end + 2:04X}); every fit leaves the data "
          "zero and the stack above the array", refused and fit_sps and not bad
          and first - RA >= data_end, f"refused={refused} fits={len(fit_sps)} bad={bad[:3]}")
    if fit_sps:
        u.poke(ARYBASE, b"\x00\x00")
        u.cpu.sp = first
        ulo[0] = 0x10000
        u.poke_w(t["ARY_IDXP"], BOUNDS + 2)
        u.call("ary_alloc", keep_sp=True, b=ord("Z"), c=0, a=8, ix=BOUNDS + 2)
        print(f"      (measured here: the tenant's deepest write was {first - ulo[0]} B "
              f"below the call site, {RA} reserved below the TEST -- spec Q10's harness half)")

    print(f"\n{'ALL PASS' if not fails else f'{fails} FAIL(S)'}")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
