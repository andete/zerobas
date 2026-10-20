# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-LOOPPROF (2026-10-20): where the Z80 T-states of ONE pass of a stored-program
loop go -- a per-instruction, per-routine profile on the HOST Z80 (tests/z80.py),
no emulator.

    python3 scratchpad/loopprof_host.py [--passes N] [--top K] [--trace]
                                        [--span lbl,lbl,...] [CASE ...]

CASES a..d are the TIER 5 queue's loops (TO 40, not 300: same code path, 1-2
digit counters; the 3-digit tail of a 300 loop costs nx_pki/nx_pack/fp_mul a
little more). --trace prints one pass's call tree; --span times labels that are
JUMPED to (not called) from arrival until SP rises above the arrival SP.
🔴 FN_FEND IS SEEDED (as cold boot's clear_usrtab does). Unseeded, it is 0 and
every scalar lookup's fn_shadow_find walks a 256-byte page: +9000 T per lookup,
which the first run of this rig reported as 63% of an empty NEXT.
tests/test_forfast.py F4 does not seed it either and reads sane numbers only
because an earlier corpus row reached raise_error, which resets it.

Every executed instruction's T-states (plain Z80 timing + 1 per M1, the MSX wait
state -- tests/test_paintcell.py `_timing`) are charged
  * EXCLUSIVE to the code LABEL containing its PC (main syms, or the sub ROM's
    syms for a step inside a sub-ROM bridge island), and to the CALL TARGET on top
    of a shadow call stack (a routine with its local labels folded in);
  * INCLUSIVE to every distinct call target on the shadow stack (main frames +
    the sub-ROM frames of a bridged call).
A pass = from one arrival at `ex_next` to the next (so it holds the body, the
statement dispatch, and the NEXT). Passes [skip, skip+N) are averaged; the
first passes (FOR's widen/demote, first-touch of the variable) are skipped.

What the host does NOT model (each is listed per pass in the output):
  * `subrom_call` is TRAPPED: its own body (slot load, IY, DI/EI) and the BIOS
    CALSLT round trip are not executed; the tenant's own steps ARE counted.
    Each crossing is printed with a modelled cost (SUBROM_BODY_T below), and
    a MACHINE MODEL line adds it (+ BREAKX) back; with ~63k usable T per 50 Hz
    tick it reproduces the measured zerobas ticks to +-3% (a 137, c 39, d 32).
  * every other trapped address (BREAKX, CHPUT, ...) costs 0 here.
  * hooks ($FD9A-$FFC9) are a bare RET (as the BIOS boots them); a ROM that
    hooks one on the machine (disk.rom) would add an interslot call there.
  * no interrupts: the 50 Hz ISR (C-BIOS + H.TIMI) steals cycles on the machine.
"""

import argparse
import collections
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tests"))

from _tmp import tp  # noqa: E402
import msxtest  # noqa: E402
from msxtest import Machine, _build_subrom  # noqa: E402
from z80 import Z80  # noqa: E402
from test_paintcell import _timing  # noqa: E402

ROM, SYM = tp("zb_loopprof.rom"), tp("zb_loopprof.sym")
BASIC_BASE = 0x2781
SRC, TOKB = 0xC000, 0xC100
POOL_TOP, POOL_FLOOR = 0xD000, 0x9000

# Modelled cost (T incl. the MSX M1 wait) of what the host trap SKIPS per crossing:
#  * subrom_call's own body (basic/subromcall.asm, slot present): 152 T
#  * C-BIOS CALSLT into an EXPANDED slot (the sub ROM is 3-2), page-0 target,
#    hand-counted from the C-BIOS source the repack builds from (src/slot.asm:
#    calslt + select_subslot + clprim/cl_jp in page 3 + calslt_restore +
#    restore_subslot; no repack patch touches it): 911 T
SUBROM_BODY_T = 152 + 911
# BREAKX ($00B7, C-BIOS main.asm), STOP not pressed: jp + 2 ports + ret nz = ~85 T
BREAKX_T = 85
# Usable T per 50 Hz TIME tick after the ISR, FITTED from (c)/(d)/(a)'s measured
# zerobas ticks with the two models above (61.8k / 64.5k / 63.8k): ~63k of 71 591.
USABLE_T_PER_TICK = 63000
CASES = {
    "a": ("A=I+7 body", "10 FOR I=1 TO 40:A=I+7:NEXT"),
    "b": ("A=I*7 body", "10 FOR I=1 TO 40:A=I*7:NEXT"),
    "c": ("empty I% loop", "10 FOR I%=1 TO 40:NEXT"),
    "d": ("empty default-type loop", "10 FOR I=1 TO 40:NEXT"),
}


def _colon_labels():
    """Every `name:` defined in the sources -- an EQU (a length, a token) is not
    an address, and `ev_ff_argtab_len equ $ - ...` would symbolise $0010."""
    import glob
    import re
    pat = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")
    names = set()
    for d in ("basic", "sub", "sub2"):
        for f in glob.glob(os.path.join(ROOT, d, "*.asm")) + glob.glob(os.path.join(ROOT, d, "*.inc")):
            for ln in open(f, encoding="utf-8", errors="replace"):
                mm = pat.match(ln)
                if mm:
                    names.add(mm.group(1))
    return names


LABELS = _colon_labels()


def load_code_syms(path, lo):
    """Code labels only: `name:` definitions inside the image."""
    out = []
    for name, v in msxtest.load_symbols(path).items():
        if name not in LABELS or v < lo:
            continue
        out.append((v, name))
    return sorted(out)


def label_map(syms, lo, hi):
    """addr -> label name for every address in [lo, hi)."""
    names = [None] * 0x10000
    cur, i = f"${lo:04X}?", 0
    while i < len(syms) and syms[i][0] < lo:
        cur = syms[i][1]
        i += 1
    for a in range(lo, hi):
        while i < len(syms) and syms[i][0] <= a:
            cur = syms[i][1]
            i += 1
        names[a] = cur
    return names


class Prof:
    def __init__(self):
        subprocess.run(["pasmo", "--bin", os.path.join(ROOT, "basic", "main.asm"), ROM, SYM],
                       check=True, capture_output=True)
        self.m = m = Machine(ROM, SYM, rom_base=BASIC_BASE)
        s = self.s = m.sym
        main_syms = load_code_syms(SYM, 0x0000)
        self.main_names = label_map(main_syms, 0x0000, 0x8000)
        sub_bytes, sub_sym = _build_subrom()
        sub_syms = sorted((v, n) for n, v in sub_sym.items()
                          if n in LABELS and v < 0x8000)
        self.sub_names = label_map(sub_syms, 0x0000, 0x8000)
        self.sub_bytes = sub_bytes
        self.out = []
        m.trap("BREAKX", lambda mm: setattr(mm.cpu, "f", mm.cpu.f & ~0x01))
        m.trap("CHPUT", lambda mm: self.out.append(mm.cpu.a))
        m.trap("ctl_reset", self._seed_pool)
        for cell, cold in (("CSRX", 1), ("LINLEN", 40)):
            if cell in s:
                m.poke(s[cell], cold)
        self.trap_names = {s[n]: n for n in ("BREAKX", "CHPUT", "ctl_reset", "subrom_call")}
        # wrap every trap to count it (and for subrom_call: push a sub context)
        self.on = False
        self.span_at = {}
        self.trap_count = collections.Counter()
        self.ctx = []                     # stack of (kind, shadow stack)
        self.sub_calls = collections.Counter()
        for a, fn in list(m.traps.items()):
            m.traps[a] = self._wrap_trap(a, fn)
        self.main_cpu = m.cpu
        self.main_stack = []
        self.ex_next = s["ex_next"]
        self.pass_no = -1
        self.window = (0, 0)
        self.reset_acc()
        prof = self
        orig = Z80.step

        def step(cpu):
            pc = cpu.pc
            if cpu is prof.main_cpu and pc == prof.ex_next:
                prof.pass_no += 1
                lo, hi = prof.window
                prof.on = lo <= prof.pass_no < hi
                if prof.on:
                    prof.pass_t.append(0)
            if not prof.on:
                return orig(cpu)
            sp = cpu.sp
            orig(cpu)
            t, m1 = _timing(cpu.m, pc, cpu.pc)
            t += m1
            prof.charge(cpu, pc, sp, t)
        Z80.step = step

    def _wrap_trap(self, a, fn):
        is_sub = a == self.s["subrom_call"]

        def w(mm):
            if self.on:
                self.trap_count[a] += 1
            if is_sub:
                ix = mm.cpu.ix
                kind = "p0" if ix < 0x4000 else "p1"
                b = self.sub_bytes
                tgt = b[ix + 1] | b[ix + 2] << 8 if b[ix] == 0xC3 else ix
                tname = self.sub_names[tgt] if tgt < 0x8000 else f"${tgt:04X}"
                if self.on:
                    self.sub_calls[(kind, tname)] += 1
                self.ctx.append((kind, [("SUB:" + tname, 0x10000)]))
                try:
                    fn(mm)
                finally:
                    self.ctx.pop()
            else:
                fn(mm)
        return w

    def _seed_pool(self, m):
        for cell in ("CTLTOP", "CSP", "GSP", "FSP", "TSP"):
            m.poke_w(m.addr(cell), POOL_TOP)
        m.poke_w(m.addr("CTLLIM"), POOL_FLOOR)

    def reset_acc(self):
        self.excl_label = collections.Counter()
        self.excl_routine = collections.Counter()
        self.incl = collections.Counter()
        self.calls = collections.Counter()
        self.callers = collections.Counter()
        self.trap_count = collections.Counter()
        self.sub_calls = collections.Counter()
        self.pass_t = []
        self.span_live = []
        self.span_t = collections.Counter()
        self.span_n = collections.Counter()
        self.cum = 0
        self.trace = []
        self.trace_pass = -99
        self.region = collections.Counter()

    def name(self, cpu, pc):
        if cpu is self.main_cpu:
            if pc < 0x100:
                return f"island${pc:04X}", "main"
            if pc < 0x8000:
                return self.main_names[pc], "main"
            if pc >= 0xFD9A:
                return f"hook${pc:04X}", "hook"
            return f"${pc:04X}", "ram/bios"
        
        kind = self.ctx[-1][0] if self.ctx else "?"
        if kind == "p0" or pc >= 0x4000:
            if pc < 0x8000:
                return "SUB:" + self.sub_names[pc], "sub" + kind
            return f"${pc:04X}", "ram"
        return self.main_names[pc], "main@sub-p1"

    def excl_label_snapshot(self, cpu, pc):
        return self.name(cpu, pc)[0]

    def span_step(self, cpu, pc, sp, t):
        """--span: inclusive T from reaching a label (called OR jumped to) until
        SP rises above the SP it was reached with (its own ret, or its caller's)."""
        if cpu is self.main_cpu:
            for rec in self.span_live[:]:
                if sp > rec[1]:
                    self.span_live.remove(rec)
                    self.span_t[rec[0]] += rec[2]
                    self.span_n[rec[0]] += 1
            nm = self.span_at.get(pc)
            if nm is not None:
                self.span_live.append([nm, sp, 0])
        for rec in self.span_live:
            rec[2] += t

    def charge(self, cpu, pc, sp, t):
        if self.span_at:
            self.span_step(cpu, pc, sp, t)
        if cpu is self.main_cpu:
            stack = self.main_stack
        else:
            stack = self.ctx[-1][1]
        while stack and stack[-1][1] < sp + 0 and len(stack) > 1:
            fr = stack.pop()
            if len(fr) > 2 and fr[2] is not None:
                fr[2][3] = self.cum

        lab, region = self.name(cpu, pc)
        self.excl_label[lab] += t
        self.region[region] += t
        self.excl_routine[stack[-1][0] if stack else lab] += t
        self.pass_t[-1] += t
        self.cum += t
        seen = set()
        for _, st in ((None, self.main_stack),) + tuple(self.ctx):
            for fr, *_ in st:
                if fr not in seen:
                    seen.add(fr)
                    self.incl[fr] += t
        # was it a CALL / RST (taken)?
        op = cpu.m[pc]
        tgt = None
        if op == 0xCD or (op in (0xC4, 0xCC, 0xD4, 0xDC, 0xE4, 0xEC, 0xF4, 0xFC)
                          and cpu.pc != (pc + 3) & 0xFFFF):
            tgt = cpu.pc
        elif op in (0xC7, 0xCF, 0xD7, 0xDF, 0xE7, 0xEF, 0xF7, 0xFF):
            tgt = cpu.pc
        if tgt is not None:
            if cpu is self.main_cpu and tgt in self.m.traps:
                tname = "TRAP:" + self.trap_names.get(tgt, f"${tgt:04X}")
            else:
                tname, _ = self.name(cpu, tgt)
            self.callers[(stack[-1][0] if stack else "?", tname)] += 1
            rec = None
            if self.pass_no == self.trace_pass:
                depth = sum(len(st) for _, st in ((None, self.main_stack),) + tuple(self.ctx))
                rec = [depth, tname, self.cum, None, self.excl_label_snapshot(cpu, pc)]
                self.trace.append(rec)
            stack.append((tname, cpu.sp, rec))
            self.calls[tname] += 1

    def run(self, text, skip, n):
        m, s = self.m, self.s
        self.out.clear()
        self._seed_pool(m)
        # cold boot's clear_usrtab (basic/usr.asm) sets the "no FN call" gate; the
        # harness never boots, and FN_FEND = 0 walks fn_shadow_find round a page
        m.poke(s["FN_FEND"], s["FN_PAREA"] & 0xFF)
        m.call("new_prog")
        rows = []
        for ln in text.strip().splitlines():
            no, _, body = ln.strip().partition(" ")
            rows.append((int(no), body))
        for lineno, body in rows:
            m.poke(SRC, body.encode("ascii") + b"\x00")
            m.mem[TOKB:TOKB + 192] = b"\x00" * 192
            m.call("tokenise", hl=SRC, de=TOKB)
            m.poke_w(s["SL_CEIL"], s["TXTMAX"])
            m.call("store_line", bc=lineno, hl=TOKB)
        self.reset_acc()
        self.trace_pass = skip + 2
        self.pass_no = -1
        self.window = (skip, skip + n)
        self.main_stack[:] = [("run_prog", 0x10000)]
        m.call("run_prog", max_steps=30_000_000)
        self.on = False
        self.window = (0, 0)
        return bytes(self.out).decode("latin-1")


def report(p, key, label, text, n, top, trace=False):
    out = p.run(text, skip=4, n=n)
    pt = p.pass_t
    tot = sum(pt) / len(pt)
    print(f"\n=== ({key}) {label}: `{text[3:]}` ===")
    print(f"T per pass (M1 incl.): mean {tot:.0f}, min {min(pt)}, max {max(pt)} over {len(pt)} passes"
          f"  [program printed {out.strip()!r}]")
    reg = ", ".join(f"{k} {v / n:.0f}" for k, v in p.region.most_common())
    print(f"  by region: {reg}")
    sc = sum(p.sub_calls.values()) / n
    print(f"  sub-ROM crossings per pass: {sc:g}"
          + (f"  -> + {sc * SUBROM_BODY_T:.0f} T subrom_call body + CALSLT round trip(s) not executed"
             if sc else ""))
    br = p.trap_count.get(p.s["BREAKX"], 0) / n
    mach = tot + sc * SUBROM_BODY_T + br * BREAKX_T
    p.machine_t = mach
    print(f"  MACHINE MODEL per pass: {mach:.0f} T (host {tot:.0f} + crossings + BREAKX); "
          f"-> {300 * mach / USABLE_T_PER_TICK:.0f} TIME ticks per 300 passes at "
          f"{USABLE_T_PER_TICK} usable T/tick")
    for (k, t), c in p.sub_calls.most_common():
        print(f"      {k} {t}: {c / n:g}/pass")
    traps = {p.trap_names.get(a, f"${a:04X}"): c / n for a, c in p.trap_count.items()}
    print(f"  trapped calls per pass (0 T on the host): {traps}")
    print(f"  -- top by EXCLUSIVE T, per label --")
    for nm, t in p.excl_label.most_common(top):
        print(f"      {t / n:7.0f} T {100 * t / n / tot:5.1f}%  {nm}")
    print(f"  -- top by EXCLUSIVE T, per call target (locals folded) --")
    for nm, t in p.excl_routine.most_common(top):
        print(f"      {t / n:7.0f} T {100 * t / n / tot:5.1f}%  {nm}  ({p.calls[nm] / n:g} calls/pass)")
    print(f"  -- top by INCLUSIVE T, per call target --")
    for nm, t in p.incl.most_common(top + 4):
        print(f"      {t / n:7.0f} T {100 * t / n / tot:5.1f}%  {nm}  ({p.calls[nm] / n:g} calls/pass)")
    print(f"  -- calls per pass, caller -> callee --")
    print("      " + ", ".join(f"{a}->{b} {c / n:g}" for (a, b), c in p.callers.most_common() if c / n >= 0.5))
    if p.span_t:
        print("  -- spans (inclusive from reaching the label until it returns; per pass) --")
        for nm, t in p.span_t.most_common():
            print(f"      {t / n:7.0f} T {100 * t / n / tot:5.1f}%  {nm}  ({p.span_n[nm] / n:g}x)")
    if trace:
        print("  -- call trace of one pass (inclusive T; depth-indented; 'from' = calling label) --")
        for depth, nm, t0, t1, frm in p.trace:
            inc = (t1 - t0) if t1 is not None else -1
            print(f"      {'  ' * (depth - 1)}{nm} {inc} T   (from {frm})")
    return tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--passes", type=int, default=20)
    ap.add_argument("--top", type=int, default=14)
    ap.add_argument("--span", help="comma-separated labels to time inclusively")
    ap.add_argument("--trace", action="store_true", help="print one pass's call tree")
    ap.add_argument("cases", nargs="*", default=list(CASES))
    a = ap.parse_args()
    p = Prof()
    for nm in (a.span or "").split(","):
        if nm:
            p.span_at[p.s[nm]] = nm
    res = {}
    for k in a.cases:
        label, text = CASES[k]
        report(p, k, label, text, a.passes, a.top, a.trace)
        res[k] = p.machine_t
    print("\n=== summary: modelled machine T/pass vs the measured TIME ticks per 300 passes ===")
    ticks = {"a": (70, 137), "b": (98, None), "c": (8, 39), "d": (24, 32)}
    for k, t in res.items():
        vg, zb = ticks[k]
        fit = f"implies {300 * t / zb:.0f} usable T/tick" if zb else "zb ticks not measured"
        print(f"  ({k}) model {t:6.0f} T/pass -> {300 * t / USABLE_T_PER_TICK:5.0f} ticks; measured zb "
              f"{zb if zb else '?'} ({fit}); VG-8020 {vg} ticks = ~{vg * USABLE_T_PER_TICK / 300:.0f} T/pass")


if __name__ == "__main__":
    main()
