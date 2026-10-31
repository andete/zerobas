# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Discovery, routines, stack/value tracking, liveness and inferred contracts.

Core module: Z80-generic. All platform/program knowledge arrives through a
program.Program (images, code ranges, roots, declared Opaque boundaries).

Pipeline (Analysis.run):
  1. discover   -- recursive descent from candidate roots; each root's closure
                   is validated (no invalid decode, no overlap with accepted code,
                   no fall-off the code range) and accepted greedily, most-
                   referenced first. Rejected roots are reported, not trusted.
  2. entries    -- routine entries: call/rst targets, unreferenced accepted roots,
                   interrupt entries, declared dispatch targets, and the
                   continuation after an `ld sp` (unless annotated).
  3. forward    -- per routine, an abstract interpretation of the stack:
                   depth, what each stack slot holds, and for every register
                   unit which value it holds (the routine's entry value of a
                   unit, +-n of one, a constant or a few, or the return
                   address). Iterated to a fixpoint, then replayed once on the
                   converged states to record events, exits and flows. Gives
                   the routine's EXITS: (level, x, k, delta) -- back to the
                   caller at RA+k with SP changed by delta for it, or through
                   a return address the caller pushed (level 1, "returns to the
                   caller's caller"). Callers follow every exit of a callee.
                   Every stack trick the tool cannot settle is an event.
  4. iterate    -- the callees' return offsets (and inferred noreturn) feed
                   back into discovery until stable.
  5. liveness   -- backward, per routine, as a summary (U, {class: M}): live-in
                   at entry = U | M[e] for e live where the exits of that
                   class land. A class is an exit level and the flags (carry,
                   zero) its exits leave known, so a caller that branches on
                   a returned flag reads only through its own exits. Copies and push/pop
                   slots are exact, so a saved register is not an input; a
                   frame a callee leaves pushed maps back to the registers it
                   was pushed from.
  6. contexts   -- concrete exit-liveness per routine and exit level (union over
                   its callers), which gives, per call site, which callee
                   outputs are USED.

Addresses are global (context << 16 | Z80 address; see program.Program), so a
routine in another slot mapping is a routine like any other. A FarCall entry
(CALSLT, a call-back stub) is resolved per call site when its target
registers fold to constants, and the call is followed into the target. An
`inline` routine is analysed as a copy per call site (tag bits >= 24).

Hand annotations (annotate.py) are consulted per routine or per SITE; see there.
"""
import re
from collections import defaultdict, deque

from .decode import REAL, SP, U, UNIT_NAMES, pair_units, pmask, COND_FLAG, decode, fmt_units
from .program import FarCall, Opaque, coarse, external
from .annotate import EXTERNAL, external_reads, is_external

# the boundary an `external` dispatch target stands for
ANNOTATED_EXTERNAL = Opaque("external code (annotated)", "external-annotated", in_ram=True, patch_point=True,
                            note="a declared jump into code outside every image")

NU = 30                      # real units 0..29
SLOTS = ((1 << 64) - 1) & ~((1 << 32) - 1)
MAXD = 32                    # stack slots tracked as liveness units: depth 2..32
IDENT = tuple(1 << e for e in range(NU))
R8 = {"A", "B", "C", "D", "E", "H", "L", "IXH", "IXL", "IYH", "IYL"}
PAIR_UNITS = [(U["B"], U["C"]), (U["D"], U["E"]), (U["H"], U["L"]), (U["IXH"], U["IXL"]), (U["IYH"], U["IYL"])]
ZERO_M = (0,) * NU
ANYX = "*"                   # exit class standing for every exit (an unknown path, an unknown caller)
FLAG_SPLIT = ("fC", "fZ")    # flags whose known value at an exit makes it an exit of its own
COND_UNIT = {"c": "fC", "nc": "fC", "z": "fZ", "nz": "fZ"}


def bits(x):
    while x:
        b = x & -x
        yield b.bit_length() - 1
        x ^= b


def slot_bits(d):
    return 1 << (30 + d), 1 << (31 + d)


# ---------------------------------------------------------------------------
class Analysis:
    def __init__(self, prog, max_rounds=8):
        self.p = prog
        self.icache = {}
        self.max_rounds = max_rounds
        self.log = []
        self.clone_ids = {}     # inlined call site -> copy id
        self.clone_site = {}    # copy id -> its call site
        self.far_entries = set()   # far-call targets made routine entries
        self.want_entries = set()  # dispatch targets seen from another context
        self.anchor_frame = {}     # reset continuation -> routines whose frame it lands in
        self.aL = {}               # their per-class exit-live as the last round saw it
        self.unwind_conts = set()  # continuations after an unwind (`stack-anchor C unwind`)
        self.reset_reads = True    # False: the normal-path view (see normal_view)
        if prog.annotations is not None:
            prog.annotations.canon = self.canon

    # -- decode ------------------------------------------------------------
    def instr(self, a):
        b = base(a)
        if b != a:
            # an inlined copy: the same instruction, its address and static
            # target tagged with the copy
            i = self.instr(b)
            if i is None:
                return None
            from .decode import Instr
            c = Instr(a)
            for f in Instr.__slots__:
                setattr(c, f, getattr(i, f))
            c.addr = a
            if c.target is not None:
                c.target = base(c.target) | (a & ~0xFFFFFF)
            return c
        if not self.p.in_code(a):
            return None
        i = self.icache.get(a)
        if i is None:
            # decode in the address's own context, then give its address and
            # static target back their context
            ctx = a & ~0xFFFF
            i = decode(lambda x: self.p.read(ctx | (x & 0xFFFF)), a & 0xFFFF)
            i.addr = a
            if i.target is not None:
                i.target |= ctx
            self.icache[a] = i
        return i

    def canon(self, a):
        """The address annotations name a (context 0 for a shared page)."""
        b = base(a)
        e = self.p.equiv(b)
        return b if e is None else e

    def rebase(self, ts, site):
        """Annotation targets (context-0 addresses) as seen from site: in a
        context that shares their page, that context's copy."""
        ctx = base(site) & ~0xFFFF
        out = []
        for t in ts:
            if not is_external(t) and ctx and t >> 16 == 0 and self.p.equiv(ctx | t) == t:
                t = ctx | t
            out.append(t)
        return out

    def copy_base(self, a):
        """The depth an annotation's "depth 0" (the routine entry) has at a:
        0, or inside an inlined copy the copy's entry depth."""
        return ANCHOR + 2 if a >> CLONE else 0

    def restore_ra(self, a, sl, depth):
        """A declared depth asserts the return-address slot is intact: put it
        back if the tool lost it (the copy's return value inside a copy)."""
        b = self.copy_base(a)
        if depth < b or b in sl and sl[b] is not None:
            return
        if not b:
            sl[0] = ((("ra", 0, "h"),), (("ra", 0, "l"),))
            return
        site = self.clone_site.get(a >> CLONE)
        ins = self.instr(site) if site is not None else None
        if ins is not None:
            n = site + ins.length
            sl[b] = ((("rt", n, "h", site),), (("rt", n, "l", site),))

    def want(self, ts, site):
        """rebase(), and ask for the rebased targets to become routine entries
        (each routine that reaches them gets one shared summary)."""
        out = self.rebase(ts, site)
        for t0, t in zip(ts, out):
            if t != t0 and t not in self.entries and self.p.in_code(t):
                self.want_entries.add(t)
        return out

    # -- boundaries --------------------------------------------------------
    def boundary(self, t):
        """Opaque for a target the analysis does not enter, or None if it is code."""
        o = self.p.opaque_at(t)
        if o is not None:
            return o
        if not self.p.in_code(t):
            return external(self.p.fmt(t), self.p.classify(t), in_ram=self.p.is_ram(t))
        return None

    def call_ks(self, t):
        """Where a call to t continues: the set of inline-skip offsets past the
        call (empty: it never comes back)."""
        o = self.p.opaque_at(t)
        if o is not None:
            return set() if o.noreturn else {o.inline}
        ann = self.p.annotations
        if ann and ann.r(ann.noreturn, t):
            return set()
        if not self.p.in_code(t):
            return {0}
        return set(self.ksets.get(t, {0}))

    # -- 1. discovery ------------------------------------------------------
    def closure(self, root):
        """Intra-procedural closure (jumps followed, calls not entered)."""
        seen = {}
        bad = []
        calls = set()
        jumps = set()
        ann = self.p.annotations
        work = [root]
        while work:
            a = work.pop()
            if a in seen:
                continue
            ins = self.instr(a)
            if ins is None:
                bad.append((a, "flow leaves the code range"))
                continue
            seen[a] = ins
            if ins.invalid:
                bad.append((a, ins.invalid))
                continue
            nxt = a + ins.length
            if ins.kind in ("call", "rst"):
                t = ins.target
                if self.p.in_code(t) and self.p.opaque_at(t) is None:
                    calls.add(t)
                ks = self.call_ks(t)
                for k in ks:
                    work.append(nxt + k)
                if ins.cond and ks != {0}:
                    work.append(nxt)
                continue
            if ins.kind in ("jpind", "ret") and ann and ann.site_targets(a)[1]:
                # declared dispatch targets: separate routines, derived roots
                # (seen from another context: code followed as part of this one)
                # (a table declared for main code, seen from another context, is
                # NOT followed here: discovery cannot apply its `in=` routines,
                # so it would decode tables no routine of this context reaches
                # -- the forward analysis asks for the targets it does reach)
                ts = ann.site_targets(a)[1]
                for t0, t in zip(ts, self.rebase(ts, a)):
                    if not is_external(t) and self.p.in_code(t) and self.p.opaque_at(t) is None and t == t0:
                        calls.add(t)
            if ins.kind in ("jp", "jr", "djnz"):
                t = ins.target
                if self.p.in_code(t) and self.p.opaque_at(t) is None:
                    jumps.add(t)
                    work.append(t)
            if ins.falls_through and ins.kind not in ("call", "rst"):
                work.append(nxt)
        # an instruction that straddles a declared boundary (a label the program
        # says starts SOMETHING) is a decode out of step with the source
        bnd = self.p.boundaries
        for a, ins in seen.items():
            for b in range(a + 1, a + ins.length):
                if b in bnd:
                    bad.append((a, f"instruction at ${a:04X} straddles label {self.p.exact_name(b)}"))
                    break
        # text decodes as runs of `ld r,r'`; real code never overwrites a copy's
        # destination in the very next instruction without reading it
        for a, ins in seen.items():
            if len(ins.copies) == 1 and ins.length == 1:
                dst = ins.copies[0][0]
                j = seen.get(a + 1)
                if j is not None and not j.invalid:
                    jw = j.writes | sum(1 << d for d, _ in j.copies)
                    jr = j.reads | sum(1 << s_ for _, s_ in j.copies)
                    if jw >> dst & 1 and not jr >> dst & 1:
                        bad.append((a, f"dead copy: {ins.mnem} then {j.mnem} (looks like text/data)"))
                        break
        # internal overlap check
        own = {}
        for a, ins in seen.items():
            for b in range(a, a + ins.length):
                if b in own and own[b] != a:
                    bad.append((a, f"overlaps own instruction at ${own[b]:04X}"))
                own[b] = a
        return seen, bad, calls, jumps

    def discover(self):
        p = self.p
        cands = dict(p.roots)
        for a, n in p.interrupt_entries.items():
            cands[a] = n
        closures = {}
        rejected = {}
        while True:
            for r in cands:
                if r not in closures:
                    closures[r] = self.closure(r)
            valid = [r for r in cands if not closures[r][1]]
            for r in cands:
                if closures[r][1]:
                    rejected[r] = closures[r][1][0]
            refs = defaultdict(int)
            for r in valid:
                _, _, calls, jumps = closures[r]
                for t in calls | jumps:
                    if t != r:
                        refs[t] += 1
            # conflict graph: two roots conflict when their decodes disagree on
            # where an instruction starts in some byte
            bytemap = defaultdict(dict)
            for r in valid:
                for a, ins in closures[r][0].items():
                    for b in range(a, a + ins.length):
                        bytemap[b].setdefault(a, set()).add(r)
            conf = defaultdict(set)
            where = {}
            for b, starts in bytemap.items():
                if len(starts) < 2:
                    continue
                groups = list(starts.items())
                for i in range(len(groups)):
                    for j in range(i + 1, len(groups)):
                        for r1 in groups[i][1]:
                            for r2 in groups[j][1]:
                                if r1 != r2 and r2 not in conf[r1]:
                                    conf[r1].add(r2)
                                    conf[r2].add(r1)
                                    where[(r1, r2)] = where[(r2, r1)] = b
            removed = set()
            while True:
                live = [r for r in valid if r not in removed and conf[r]]
                if not live:
                    break
                # drop the root that disagrees with the most others; among equals
                # the least referenced, then the one with the largest decode
                r = max(live, key=lambda x: (x not in p.interrupt_entries, len(conf[x]),
                                             -refs.get(x, 0), len(closures[x][0])))
                others = sorted(conf[r])
                b = where[(r, others[0])]
                rejected[r] = (b, f"decode disagrees with {len(others)} other root(s), e.g. "
                                  f"{p.exact_name(others[0])} at ${b:04X}")
                removed.add(r)
                for o in others:
                    conf[o].discard(r)
                conf[r] = set()
            accepted = {r: closures[r][0] for r in valid if r not in removed}
            nf = set()
            for r in accepted:
                for t in closures[r][2]:
                    if t not in cands:
                        nf.add(t)
            if not nf:
                break
            for t in nf:
                cands[t] = p.exact_name(t)
        for r in accepted:
            rejected.pop(r, None)
        self.closures = closures
        self.accepted = accepted
        self.rejected = rejected
        self.code = {}
        for r, seen in accepted.items():
            self.code.update(seen)
        # flow targets (to tell entries from internal labels)
        jumped = set()
        called = set()
        for a, ins in self.code.items():
            if ins.kind in ("call", "rst"):
                if self.p.in_code(ins.target) and self.p.opaque_at(ins.target) is None:
                    called.add(ins.target)
            elif ins.kind in ("jp", "jr", "djnz"):
                jumped.add(ins.target)
            if ins.falls_through and ins.kind not in ("call", "rst"):
                jumped.add(a + ins.length)
            if ins.kind in ("call", "rst"):
                for k in self.call_ks(ins.target):
                    jumped.add(a + ins.length + k)
        entries = {}
        for t in called:
            if t in self.code:
                entries[t] = "called"
        for a in p.interrupt_entries:
            if a in self.code:
                entries[a] = "interrupt"
        for a in self.far_entries:
            if a in self.code and a not in entries:
                entries[a] = "far-call target"
        if p.annotations:
            for a, ins in self.code.items():
                if ins.kind in ("jpind", "ret"):
                    ts = p.annotations.site_targets(a)[1] or ()
                    for t0, t in zip(ts, self.rebase(ts, a)):
                        # (a table declared for main code, seen from another
                        # context, is followed as code of the routine that
                        # reaches it there, not seeded as routines of its own)
                        if t == t0 and t in self.code and t not in entries:
                            entries[t] = "dispatch target"
            for e in p.annotations.same_as.values():
                if e.value in self.code and e.value not in entries:
                    entries[e.value] = "same-as target"
        for r in accepted:
            if r not in entries and r not in jumped:
                entries[r] = "root (no static reference)"
        for a, ins in self.code.items():
            # a frame reset from a constant / memory cell starts a new routine;
            # `ld sp,rr` usually carves or releases a frame of this one
            if ins.stack and ins.stack[0] == "ldsp" and ins.stack[1] not in ("HL", "IX", "IY") \
                    and not (p.annotations and a in p.annotations.ldsp):
                n = a + ins.length
                if n in self.code and n not in entries:
                    entries[n] = "continuation after ld sp"
        self.entries = entries
        self.called = called

    # -- 3. forward stack / value analysis ---------------------------------
    #
    # A value is None (unknown), ("o", u) (the routine's entry value of unit u),
    # ("od", u, n) (that value + n, 8-bit), ("o16", hu, lu, n, part) (part 'h'
    # or 'l' of the entry pair hu:lu + n), ("k", byte) (a constant) or
    # ("ra", k, part) (the return address + k).
    #
    # A routine EXIT is a key (level, x, k, delta):
    #   level 0: back to the caller, at RA+k, with SP changed by delta bytes for
    #            the caller (delta > 0: it left a frame pushed; < 0: it consumed
    #            part of the caller's frame); x = 0
    #   level 1: through a return address the CALLER pushed (or its own RA):
    #            for the caller it is as if it executed `ret` at its depth D + x
    #            (D = its depth at the call), then skipped k and changed SP by
    #            delta. x = 0 is "returns to the caller's caller".
    # Per exit the summary keeps the register values ("out") and the content
    # of any slots left pushed for the caller ("slots", caller-relative).

    def initial_state(self):
        regs = tuple(("o", u) for u in range(NU))
        slots = ((0, ((("ra", 0, "h"),), (("ra", 0, "l"),))),)
        return (0, regs, slots)

    @staticmethod
    def merge(s1, s2):
        d1, r1, sl1 = s1
        d2, r2, sl2 = s2
        conflict = False
        if d1 != d2:
            d = None
            conflict = d1 is not None and d2 is not None
        else:
            d = d1
        mv = Analysis.mergev
        # the caller slots each path touched: the union (an unknown set on
        # either side stays unknown)
        t1, t2 = dict(sl1).get(TOUCH), dict(sl2).get(TOUCH)
        touch = None
        if t1 is not None or t2 is not None:
            if (t1 is not None and not t1[0][0]) or (t2 is not None and not t2[0][0]):
                touch = ((None,), ())
            else:
                u_ = (t1[0][0][1] if t1 else frozenset()) | (t2[0][0][1] if t2 else frozenset())
                touch = ((("touch", u_),), ())
        regs = list(mv(a, b) for a, b in zip(r1, r2))
        # a register pair holding a constant on both sides keeps its 16-bit
        # values together (per-byte sets would pair every high with every low)
        for h, l_ in PAIR_UNITS:
            if regs[h] != r1[h] or regs[l_] != r1[l_]:
                v1, v2 = Analysis.pairset(r1[h], r1[l_]), Analysis.pairset(r2[h], r2[l_])
                if v1 is not None and v2 is not None and len(v1 | v2) <= Analysis.MAXKS:
                    j = frozenset(v1 | v2)
                    regs[h], regs[l_] = ("p16", j, "h"), ("p16", j, "l")
        regs = tuple(regs)
        m2 = dict(sl2)
        slots = []
        if d is not None:
            for k, v in sl1:
                w = m2.get(k)
                if w is None or len(w[0]) != len(v[0]) or len(w[1]) != len(v[1]):
                    continue
                hi = tuple(mv(a, b) for a, b in zip(v[0], w[0]))
                lo = tuple(mv(a, b) for a, b in zip(v[1], w[1]))
                if len(hi) == 1 and len(lo) == 1 and (hi != v[0] or lo != v[1]):
                    j1, j2 = Analysis.pairset(v[0][0], v[1][0]), Analysis.pairset(w[0][0], w[1][0])
                    if j1 is not None and j2 is not None and len(j1 | j2) <= Analysis.MAXKS:
                        j = frozenset(j1 | j2)
                        hi, lo = (("p16", j, "h"),), (("p16", j, "l"),)
                slots.append((k, (hi, lo)))
        slots = [kv for kv in slots if kv[0] != TOUCH]
        if touch is not None:
            slots.append((TOUCH, touch))
        return (d, regs, tuple(sorted(slots))), conflict

    MAXKS = 16

    @staticmethod
    def mergev(a, b):
        """Join of two values: equal, or a small set of constants, or unknown."""
        if a == b:
            return a
        if a is None or b is None:
            return None
        def byteset(v):
            if v[0] == "p16":
                return {x >> 8 if v[2] == "h" else x & 0xFF for x in v[1]}
            return {v[1]} if v[0] == "k" else (set(v[1]) if v[0] == "ks" else None)
        ka, kb = byteset(a), byteset(b)
        if ka is None or kb is None or len(ka | kb) > Analysis.MAXKS:
            return None
        return ("ks", frozenset(ka | kb))

    # value helpers --------------------------------------------------------
    @staticmethod
    def add8(v, n):
        if v is None:
            return None
        if v[0] == "o":
            base, e = v[1], 0
        elif v[0] == "od":
            base, e = v[1], v[2]
        elif v[0] == "k":
            return ("k", (v[1] + n) & 0xFF)
        else:
            return None
        e = (e + n) & 0xFF
        return ("o", base) if e == 0 else ("od", base, e)

    @staticmethod
    def add16(hv, lv, n):
        if hv is None or lv is None:
            return None, None
        if hv[0] in ("ra", "rt") and lv[0] == hv[0] and hv[1] == lv[1] and hv[2] == "h" and lv[2] == "l":
            return (hv[0], hv[1] + n, "h") + hv[3:], (hv[0], hv[1] + n, "l") + lv[3:]
        if hv[0] == "spd" and lv[0] == "spd" and hv[1] == lv[1] and hv[2] == "h" and lv[2] == "l":
            return ("spd", hv[1] - n, "h"), ("spd", hv[1] - n, "l")
        if hv[0] == "k" and lv[0] == "k":
            x = ((hv[1] << 8 | lv[1]) + n) & 0xFFFF
            return ("k", x >> 8), ("k", x & 0xFF)
        if hv[0] == "o" and lv[0] == "o":
            hu, lu, e = hv[1], lv[1], 0
        elif hv[0] == "o16" and lv[0] == "o16" and hv[1:4] == lv[1:4] and hv[4] == "h" and lv[4] == "l":
            hu, lu, e = hv[1], hv[2], hv[3]
        else:
            return None, None
        e = (e + n) & 0xFFFF
        if e == 0:
            return ("o", hu), ("o", lu)
        return ("o16", hu, lu, e, "h"), ("o16", hu, lu, e, "l")

    def subst(self, v, regs):
        """A callee-entry-relative value, seen from the caller (regs at the call)."""
        if v is None:
            return None
        t = v[0]
        if t == "o":
            return regs[v[1]]
        if t in ("k", "ks", "m", "p16"):
            return v
        if t == "od":
            return self.add8(regs[v[1]], v[2])
        if t == "o16":
            h, l_ = self.add16(regs[v[1]], regs[v[2]], v[3])
            return h if v[4] == "h" else l_
        return None

    @staticmethod
    def norm(v):
        """What of a value survives into a summary: entry-relative or constant."""
        return v if v is not None and v[0] in ("o", "od", "o16", "k", "ks", "m", "p16") else None

    def subst_slot(self, c, regs):
        return (tuple(self.subst(v, regs) for v in c[0]), tuple(self.subst(v, regs) for v in c[1]))

    @staticmethod
    def spd16(hv, lv):
        """The stack depth whose address a pair holds (see `add hl,sp`)."""
        if hv and lv and hv[0] == "spd" and lv[0] == "spd" and hv[1] == lv[1] and hv[2] == "h" and lv[2] == "l":
            return hv[1]
        return None

    @staticmethod
    def rt16(hv, lv):
        """The global address an inlined call's return-address pair holds."""
        if hv and lv and hv[0] == "rt" and lv[0] == "rt" and hv[1] == lv[1] and hv[2] == "h" and lv[2] == "l":
            return hv[1]
        return None

    @staticmethod
    def const16(hv, lv):
        if hv and lv and hv[0] == "k" and lv[0] == "k":
            return hv[1] << 8 | lv[1]
        return None

    @staticmethod
    def pairset(hv, lv):
        """The exact 16-bit values a pair holds, when it is a constant or a
        joint set of them (not a product of per-byte sets), else None."""
        if hv and lv and hv[0] == "k" and lv[0] == "k":
            return {hv[1] << 8 | lv[1]}
        if hv and lv and hv[0] == "p16" and lv[0] == "p16" and hv[1] == lv[1] and hv[2] == "h" and lv[2] == "l":
            return set(hv[1])
        return None

    @staticmethod
    def consts16(hv, lv):
        """The 16-bit constants a byte pair may hold (a small set), or None."""
        ps = Analysis.pairset(hv, lv)
        if ps is not None:
            return sorted(ps)
        def ks(v):
            if v is None:
                return None
            if v[0] == "p16":
                return {x >> 8 if v[2] == "h" else x & 0xFF for x in v[1]}
            return {v[1]} if v[0] == "k" else (set(v[1]) if v[0] == "ks" else None)
        h, l_ = ks(hv), ks(lv)
        if h is None or l_ is None or len(h) * len(l_) > Analysis.MAXKS:
            return None
        return sorted(x << 8 | y for x in h for y in l_)

    # callee summaries -----------------------------------------------------
    IDENT_OUT = tuple(("o", u) for u in range(NU))

    def opaque_summary(self, o):
        out = tuple(("o", u) if o.preserves >> u & 1 else None for u in range(NU))
        ex = {} if o.noreturn else {o.exit: {"out": out, "slots": {}}}
        return {"exits": ex}

    def callee_summary(self, t):
        o = self.boundary(t)
        if o is not None:
            return o, self.opaque_summary(o)
        ann = self.p.annotations
        if ann and ann.r(ann.noreturn, t):
            ann.r(ann.noreturn, t).used.add(t)
            return None, {"exits": {}}
        s = self.fsum.get(t)
        if s is None:   # optimistic for recursion / not yet analysed
            return None, {"exits": {(0, 0, 0, 0): {"out": self.IDENT_OUT, "slots": {}}}}
        return None, s

    def forward(self, entry):
        """Abstract interpretation of one routine. Returns its record."""
        p = self.p
        ann = p.annotations
        states = {entry: self.initial_state()}
        work = deque([entry])
        nodes = {}
        events = []
        exits = {}            # key -> {"out", "slots"}
        conflicts = set()
        visits = defaultdict(int)
        ev_seen = set()
        declared_se = ann.r(ann.stack_effect, entry) if ann else None
        final = False          # annotations are used / checked on converged states only

        def real_depth(a, d):
            """A depth inside an inlined copy (tracked from the anchor), as the
            depth in the routine that contains the copy: the call site's depth
            plus the copy's offset (through nested copies). None if unknown."""
            while d is not None and a >> CLONE:
                site = self.clone_site.get(a >> CLONE)
                cst = states.get(site) if site is not None else None
                if cst is None or cst[0] is None:
                    return None
                d = cst[0] + (d - ANCHOR)
                a = site
            return d

        def keep(slots):
            """At an unknown depth no slot is tracked -- except the record of
            which caller slots this path has touched."""
            return tuple((k_, v) for k_, v in (slots.items() if isinstance(slots, dict) else slots)
                         if k_ == TOUCH)

        def touch(sl, d, a=None):
            """A path takes the caller's slot at depth d (< 0): give it its
            symbolic original content, and remember the slot was touched.
            (Inside an inlined copy, a slot below the copy's own frame is the
            enclosing routine's: not tracked, an unknown site.)"""
            if a is not None and a >> CLONE:
                ev("inline-touches-caller-frame", a, "an inlined copy takes a slot below its own frame")
                return
            if d not in sl:
                sl[d] = ((("cs", d, "h"),), (("cs", d, "l"),))
            t = sl.get(TOUCH)
            old = t[0][0][1] if t and t[0][0] else frozenset()
            sl[TOUCH] = ((("touch", old | {d}),), ())
        far = {}               # site -> (far-call entry, constant targets or None)
        farres = {}            # site -> (far-call name, resolved global targets or None)

        def ev(kind, a, detail=""):
            key = (kind, base(a), detail)
            if key not in ev_seen:
                ev_seen.add(key)
                events.append(key)

        def push_succ(a, st):
            old = states.get(a)
            if old is None:
                states[a] = st
                work.append(a)
                return
            new, c = self.merge(old, st)
            if c:
                conflicts.add(a)
            if new != old:
                states[a] = new
                work.append(a)

        def ra_k(slot):
            if slot is None:
                return None
            hi, lo = slot
            if len(hi) == 1 and len(lo) == 1 and hi[0] and lo[0] and hi[0][0] == "ra" \
                    and lo[0][0] == "ra" and hi[0][1] == lo[0][1] and hi[0][2] == "h" and lo[0][2] == "l":
                return hi[0][1]
            return None

        def caller_slots(a, key, slots):
            """At an exit: the caller slots this path touched must be consumed
            by the exit (taken off the caller's stack) or put back unchanged
            (then the exit only READ them). Returns the caller-relative slots
            read, or None if one may have changed."""
            sl = dict(slots)
            t = sl.get(TOUCH)
            if t is None:
                return frozenset()
            if not t[0][0]:
                return None
            peek = set()
            for y in t[0][0][1]:
                if key[0] == 0 and key[3] is not None and key[3] <= y:
                    continue
                if key[0] == 1 and y >= key[1] - 2:
                    continue
                c = sl.get(y)
                if c is not None and all(v == ("cs", y, "h") for v in c[0]) and \
                        all(v == ("cs", y, "l") for v in c[1]):
                    peek.add(y + 2)
                    continue
                return None
            return frozenset(peek)

        def add_exit(a, key, regs, xslots, from_decl=False, slots=()):
            """Record an exit; returns its flow. An exit that leaves carry or
            zero a known constant is an exit of its own (key + (flags,)), so a
            caller that branches on the flag follows only its own path."""
            fl = tuple((n, regs[U[n]][1]) for n in FLAG_SPLIT if regs[U[n]] and regs[U[n]][0] == "k")
            if fl:
                key = key + (fl,)
            peek = caller_slots(a, key, slots)
            if peek is None:
                if declared_se is not None:
                    ev("caller-slot-declared", a, "a caller slot this path touched: covered by the "
                                                  "declared stack-effect")
                    peek = frozenset()
                else:
                    ev("caller-slot-changed", a, "returns with a slot of its caller's frame changed "
                                                 "(or not provably unchanged)")
                    peek = frozenset()
            if from_decl:
                pass        # the delta IS the declaration: nothing to compare
            elif declared_se is not None and key[0] == 0 and final and key[3] is not None:
                # (a variable delta the tool cannot see is no evidence either
                # way; a concrete one is consistent with `var` but proves
                # nothing about it)
                ok = declared_se.value is None or key[3] == declared_se.value
                declared_se.check(ok, f"{p.name_of(a)}: returns with stack delta {fmt_delta(key[3])}",
                                  weak=declared_se.value is None)
            if not from_decl and declared_se is not None and key[0] == 0 and key[3] is not None and \
                    declared_se.value is not None and key[3] != declared_se.value:
                ev("annotation-mismatch", a, f"declared stack-effect {fmt_delta(declared_se.value)}, "
                                             f"tool sees {fmt_delta(key[3])}")
            out = tuple(self.norm(v) for v in regs)
            sl = {r: (tuple(self.norm(v) for v in c[0]), tuple(self.norm(v) for v in c[1]))
                  for r, c in xslots.items()}
            old = exits.get(key)
            if old is None:
                exits[key] = {"out": out, "slots": sl, "peek": peek}
            else:
                o2 = tuple(x if x == y else None for x, y in zip(old["out"], out))
                s2 = {}
                for r, c in old["slots"].items():
                    w = sl.get(r)
                    if w is not None and len(w[0]) == len(c[0]) and len(w[1]) == len(c[1]):
                        s2[r] = (tuple(x if x == y else None for x, y in zip(c[0], w[0])),
                                 tuple(x if x == y else None for x, y in zip(c[1], w[1])))
                exits[key] = {"out": o2, "slots": s2, "peek": old["peek"] | peek}
            return ("exit", exit_class(key))

        def do_return(a, st, k_e, delta_e, slots_e, how, plain=True):
            """A transfer through the slot at depth d (a ret, or a callee's
            return landing there). Returns the liveness flow it becomes.
            plain: a ret, or a callee's ordinary return (a routine's declared
            stack effect may then stand in for an unknown depth)."""
            d, regs, slots = st
            # inside an inlined copy (tracked from the anchor), a transfer
            # through a slot at or below the copy's base is one of the
            # caller's: translate to the call site's frame
            while d is not None and ANCHOR // 2 <= d <= ANCHOR and a >> CLONE:
                site = self.clone_site.get(a >> CLONE)
                cst = states.get(site) if site is not None else None
                if cst is None or cst[0] is None:
                    d = None
                    break
                d = cst[0] + (d - ANCHOR)
                slots = tuple((kk, v) for kk, v in cst[2] if kk <= d)
                a = site
            if d is None:
                if declared_se is not None and plain and delta_e == 0:
                    if final:
                        declared_se.used.add(entry)
                    return add_exit(a, (0, 0, k_e, declared_se.value), regs, {}, from_decl=True)
                ev("ret-unknown-depth", a, how)
                return ("unknown",)
            sl = dict(slots)
            k0 = ra_k(sl.get(d))
            if k0 is not None:
                delta = None if delta_e is None else d + delta_e
                xs = {y + 2: c for y, c in sl.items() if -2 < y <= d - 2}
                for r, c in slots_e.items():
                    xs[d + r] = c
                if delta != 0:
                    ev("exit-stack-delta", a, f"{how}: returns to RA+{k0 + k_e} leaving SP {fmt_delta(delta)} "
                                              "for the caller")
                return add_exit(a, (0, 0, k0 + k_e, delta), regs, xs, slots=slots)
            if d < 0 and d % 2 == 0 and d not in sl:
                ev("exit-callers-caller", a, f"{how}: through the caller's slot {-d - 2} byte(s) above "
                                             "its call (returns to the caller's caller when 0)")
                return add_exit(a, (1, d + 2, k_e, delta_e), regs, slots_e, slots=slots)
            c = sl.get(d)
            g = self.rt16(c[0][0], c[1][0]) if c is not None and len(c[0]) == 1 and len(c[1]) == 1 else None
            if g is not None:
                site = c[0][0][3]
                # back from an inlined copy to its call site: SP moved by what
                # the copy left (its depth here vs the anchor) and by what a
                # callee returning through this slot adds; the frame below is
                # the call site's
                cst = states.get(site)
                rel = d - 2 - ANCHOR
                if cst is None or cst[0] is None or delta_e is None or rel < 0 or \
                        cst[0] + rel + delta_e < 0:
                    st2 = (None, regs, keep(cst[2]) if cst is not None else ())
                else:
                    nd = cst[0] + rel + delta_e
                    nsl = {kk: v for kk, v in cst[2] if kk <= min(cst[0], nd)}
                    # what the copy left pushed above the call site's depth
                    for y, v in slots:
                        if y != TOUCH and ANCHOR < y <= ANCHOR + rel and cst[0] + (y - ANCHOR) <= nd:
                            nsl[cst[0] + (y - ANCHOR)] = v
                    st2 = (nd, regs, tuple(sorted(nsl.items())))
                return goto_flow(a, g + k_e, st2, "inline return")
            if c is not None and len(c[0]) == 1 and len(c[1]) == 1:
                ts = self.consts16(c[0][0], c[1][0])
                if ts is not None:
                    ev("ret-jump-const", a, f"{how}: jumps to pushed constant "
                                            + "/".join(f"${t:04X}" for t in ts))
                    # popping the slot: the jump continues at depth d-2, plus
                    # whatever a callee returning through it left or took
                    if delta_e is None:
                        st2 = (None, regs, keep(slots))
                    else:
                        nd = d - 2 + delta_e
                        nsl = {kk: v for kk, v in slots if kk <= min(d - 2, nd)}
                        for r, c2 in slots_e.items():
                            nsl[d - 2 + r] = c2
                        st2 = (nd, regs, tuple(sorted(nsl.items())))
                    fl = [goto_flow(a, (t | (a & ~0xFFFF)) + k_e, st2, "push-then-ret") for t in ts]
                    return fl[0] if len(fl) == 1 else ("any", fl)
            if d == 0:
                ev("ret-computed-jump", a, how + ": slot 0 is not the return address")
            elif d > 0:
                ev("ret-push-jump", a, f"{how} with {d} byte(s) still pushed")
            else:
                ev("ret-below-frame", a, f"{how} at depth {d}")
            return ("unknown",)

        def via(a, st, t, mode, nxt=None, kill=0, hops=0, far_name=None):
            """A call (mode 'call', continuation nxt) or tail jump to t at the
            current depth. Returns the liveness flow. A far-call entry whose
            target the registers decide is resolved here when they fold (and
            its target again, if it is one too: a call-back to a hook)."""
            fc = None
            if not is_external(t) and hops < 4:
                fc = p.far_calls.get(t)
                if fc is None and p.equiv(t) is not None:
                    fc = p.far_calls.get(p.equiv(t))
            if fc is not None:
                vals = []
                for rn in fc.regs:
                    if rn in ("BC", "DE", "HL", "IX", "IY"):
                        (h_,), (l_,) = pair_units(rn)
                        vals.append(self.consts16(st[1][U[h_]], st[1][U[l_]]))
                    else:
                        vals.append(st[1][U[rn]])
                tgs = fc.resolve(tuple(vals), a)
                if final:
                    old_ = farres.get(base(a), (fc.name, frozenset()))
                    farres[base(a)] = (fc.name, None if tgs is None or old_[1] is None
                                       else old_[1] | frozenset(tgs))
                if tgs:
                    fl = [via1(a, st, t, mode, nxt, kill=kill) if tg == FarCall.FALLBACK else
                          via(a, st, tg, mode, nxt, kill=kill | fc.kill, hops=hops + 1, far_name=fc.name)
                          for tg in tgs]
                    if fc.gen:
                        fl.append(("use", fc.gen & REAL))
                    return fl[0] if len(fl) == 1 else ("any", fl)
            return via1(a, st, t, mode, nxt, kill=kill, far_name=far_name)

        def via1(a, st, t, mode, nxt=None, kill=0, far_name=None):
            d, regs, slots = st
            if is_external(t):
                rd = external_reads(t)
                o = ANNOTATED_EXTERNAL if rd == REAL else Opaque(
                    "external code (annotated, documented inputs)", "external-annotated", inputs=rd,
                    preserves=0, in_ram=True, patch_point=True)
                summ = self.opaque_summary(o)
            else:
                o, summ = self.callee_summary(t)
                if o is None and t not in self.entries and not (ann and ann.r(ann.noreturn, t)):
                    # code that is not a routine of its own (a rejected root,
                    # a jump into data): no summary to apply -- do not guess
                    ev("callee-not-analysed", a, f"{'call' if mode == 'call' else 'jump'} to "
                                                 f"{p.exact_name(t)}, which is not an analysed routine")
                    return ("unknown",)
            if o is not None and o.in_ram and not o.declared:
                ev("call-into-ram", a, f"{'call' if mode == 'call' else 'jump'} to {o.name} ({o.kind})")
            if mode == "tail" and d is None and declared_se is None and summ["exits"]:
                # (a jump at an unknown depth into code that never comes back
                # is harmless: an error exit that resets SP)
                ev("tail-unknown-depth", a, f"jump to {o.name if o else p.exact_name(t)} at an unknown depth")
            if final and t in p.far_target_regs:
                (h_,), (l_,) = pair_units(p.far_target_regs[t])
                vs = self.consts16(regs[U[h_]], regs[U[l_]])
                old_ = far.get(base(a), (t, frozenset()))
                far[base(a)] = (t, None if vs is None or old_[1] is None else old_[1] | frozenset(vs))
            res = []
            cnr = ann.pick(ann.call_noret, a, entry) if (ann and mode == "call") else None
            if cnr is not None:
                if final:
                    cnr.used.add(entry)
            for key, ex in sorted(summ["exits"].items(), key=exit_order):
                level, x, k, delta = key[:4]
                if far_name is not None and key[:4] != (0, 0, 0, 0):
                    # the far-call entry's own frame sits between: a callee
                    # that returns any other way does not land at the call
                    ev("far-callee-convention", a, f"{p.exact_name(t)} through {far_name} returns as {key}")
                    res.append((key, ("unknown",)))
                    continue
                if cnr is not None and level == 0:
                    if final:
                        cnr.check(True, "callee has a normal return; dropped at this site", weak=True)
                    continue
                regs2 = tuple(None if kill >> u & 1 else self.subst(v, regs) for u, v in enumerate(ex["out"]))
                pushed = {r: self.subst_slot(c, regs) for r, c in ex["slots"].items()}
                if mode == "call" and level == 0:
                    if d is None or delta is None:
                        st2 = (None, regs2, keep(slots))
                    else:
                        nd = d + delta
                        sl = {kk: v for kk, v in slots if kk <= min(d, nd)}
                        for r, c in pushed.items():
                            sl[d + r] = c
                        st2 = (nd, regs2, tuple(sorted(sl.items())))
                    res.append((key, after_call(a, nxt + k, st2)))
                else:
                    if mode == "tail" and level == 0:
                        rd = d
                    else:
                        cbase = d if mode == "call" else (None if d is None else d - 2)
                        rd = None if cbase is None else cbase + x
                    nsl = slots if rd is None else tuple((kk, v) for kk, v in slots if kk <= rd)
                    what = o.name if o else p.exact_name(t)
                    res.append((key, do_return(a, (rd, regs2, nsl), k, delta, pushed,
                                               f"{'call' if mode == 'call' else 'jump'} to {what}",
                                               plain=(mode == "tail" and level == 0))))
            if kill:
                res = [(key, ("kill", kill & REAL, g)) for key, g in res]
            # (the depth a callee's exits are relative to: the call site's for a
            # call, the phantom caller's -- 2 below -- for a tail jump)
            dd = d if mode == "call" or d is None else d - 2
            return ("via", o if o is not None else t, real_depth(a, dd), res)

        def internal(t):
            # (code not decoded by discovery -- a constant jump target -- is
            # decoded on the fly); an `inline` routine is part of every
            # routine that reaches it, and code inside an inlined copy stays
            # in that copy unless it leaves for another routine's entry
            b = base(t)
            if ann and ann.r(ann.inline, b) and b != entry and p.in_code(b):
                return True
            if t == entry:
                return True
            return b not in self.entries and p.in_code(b) and p.opaque_at(b) is None

        def tail_of(t):
            return base(t)

        def after_call(a, t, st):
            """The continuation of one callee exit. A conditional jump right
            after the call on a flag this exit fixes is taken here, per exit:
            the exits meet at the same address, where their states would merge
            (the jump still reads the flag)."""
            ins = self.instr(t) if internal(t) else None
            cu = COND_UNIT.get(ins.cond) if ins is not None and ins.kind in ("jp", "jr") else None
            v = st[1][U[cu]] if cu else None
            if v is None or v[0] != "k":
                return goto_flow(a, t, st, "after call")
            taken = (v[1] == 1) == (ins.cond in ("c", "z"))
            return ("any", [("use", 1 << U[cu]),
                            goto_flow(t, ins.target if taken else t + ins.length, st,
                                      "after call, flag known")])

        def goto_flow(a, t, st, edge):
            if not is_external(t) and internal(t):
                push_succ(t, st)
                return ("succ", t)
            return via(a, st, t if is_external(t) else base(t), "tail")

        def step(a):
            ins = self.code.get(a) if a == base(a) else None
            if ins is None:
                ins = self.instr(a)
                if ins is None:
                    ev("flow-off-code", a)
                    return
            st = states[a]
            d, regs, slots = st
            dann = ann.pick(ann.depth, a, entry) if ann else None
            taken_st = st          # state for a conditional ret's taken edge
            if dann is not None:
                if final:
                    dann.used.add(entry)
                dv = dann.value + self.copy_base(a)
                if d is not None and final:
                    dann.check(d == dv, f"tool sees depth {d - self.copy_base(a):+d} in {p.exact_name(entry)}")
                    if d != dv:
                        ev("annotation-mismatch", a, f"declared depth {dann.value:+d}, "
                                                     f"tool sees {d - self.copy_base(a):+d}")
                sl = dict(slots) if d is not None else dict(keep(slots))
                self.restore_ra(a, sl, dv)
                sl = {kk: v for kk, v in sl.items() if kk <= dv}
                ast = (dv, regs, tuple(sorted(sl.items())))
                if ins.cond and ins.kind in ("ret", "jp", "jr", "call"):
                    taken_st = ast
                else:
                    st = taken_st = ast
                    d, regs, slots = st
            node = {"ins": ins, "flows": [], "depth": d, "ldepth": real_depth(a, d)}
            nodes[a] = node
            # a condition on a flag the path has fixed takes one edge only;
            # each edge knows the flag from then on
            cu = COND_UNIT.get(ins.cond)
            cvv = regs[U[cu]] if cu else None
            cv = (cvv[1] == 1) == (ins.cond in ("c", "z")) if cvv and cvv[0] == "k" else None

            def on(st_, taken):
                # (a flag still holding its entry value stays that: as a
                # constant it would read as changed at the exit)
                if cu is None or st_[1][U[cu]] == ("o", U[cu]):
                    return st_
                rr = list(st_[1])
                rr[U[cu]] = ("k", int(taken == (ins.cond in ("c", "z"))))
                return (st_[0], tuple(rr), st_[2])
            nxt = a + ins.length
            flows = node["flows"]

            va = ann.pick(ann.values, a, entry) if ann else None
            if va is not None:
                if final:
                    va.used.add(entry)
                (vh,), (vl,) = pair_units(va.value[0])
                j = frozenset(va.value[1])
                rr = list(regs)
                rr[U[vh]], rr[U[vl]] = ("p16", j, "h"), ("p16", j, "l")
                regs = tuple(rr)
                st = (d, regs, slots)
                taken_st = (taken_st[0], regs, taken_st[2])
            ab = ann.pick(ann.abort, a, entry) if ann else None
            if ab is not None:
                if final:
                    ab.used.add(entry)
                t = None if ins.target is None else base(ins.target)
                if ab.value is None and t is not None and self.p.in_code(t) and self.boundary(t) is None:
                    # the abort target's whole live-in counts; it gets a
                    # record of its own (a routine entry) if it has none
                    if t not in self.entries:
                        self.want_entries.add(t)
                    flows.append(("cont", t) + (("unwind",) if ab.unwind else ()))
                else:
                    # no static target and no stated reads: anything may be read
                    flows.append(("abort", ab.value if ab.value is not None else REAL)
                                 + (("unwind",) if ab.unwind else ()))
                if ins.cond:      # only the taken edge aborts
                    flows.append(goto_flow(a, nxt, st, "fallthrough"))
                node["abort"] = True
                return

            k = ins.kind
            # register effect (copies, then writes)
            r = list(regs)
            for dst, src in ins.copies:
                r[dst] = regs[src]
            for u in bits(ins.writes & REAL):
                r[u] = None
            sl = dict(slots)
            nd = d
            stk = ins.stack
            if stk:
                op, arg = stk
                if op in ("push", "pop", "exsp"):
                    hi, lo = pair_units(arg)
                    hu = [U[x] for x in hi]
                    lu = [U[x] for x in lo]
                if op == "push":
                    if d is not None:
                        nd = d + 2
                        sl[nd] = (tuple(regs[u] for u in hu), tuple(regs[u] for u in lu))
                elif op == "pop":
                    if d is not None:
                        if d == 0:
                            ev("pop-ra", a, ins.mnem)
                        elif d < 0 or (a >> CLONE and d < self.copy_base(a)):
                            ev("pop-below-frame", a, ins.mnem)
                            touch(sl, d, a)
                        s = sl.pop(d, None)
                        if s is not None and len(s[0]) == 1 and len(s[1]) == 1 and s[1][0] and \
                                s[1][0][0] == "cs" and len(lu) != 1:
                            s = (s[0], s[1] * len(lu))
                        if s is not None and len(s[0]) == len(hu) and len(s[1]) == len(lu):
                            for u, t in zip(hu, s[0]):
                                r[u] = t
                            for u, t in zip(lu, s[1]):
                                r[u] = t
                        nd = d - 2
                elif op == "exsp":
                    if d is None:
                        # a routine declared to return with a data-dependent
                        # stack (stack-effect var) keeps its return address
                        # in place itself; that declaration covers this
                        ev("exsp-unknown-depth" if declared_se is None or declared_se.value is not None
                           else "exsp-unknown-depth-declared", a, ins.mnem)
                    else:
                        ev("exsp-ra" if d == self.copy_base(a) else
                           ("exsp-local" if d > self.copy_base(a) else "exsp-below-frame"), a, ins.mnem)
                        if d < 0 or (a >> CLONE and d < self.copy_base(a)):
                            touch(sl, d, a)
                        s = sl.get(d)
                        sl[d] = (tuple(regs[u] for u in hu), tuple(regs[u] for u in lu))
                        if s is not None and len(s[0]) == len(hu) and len(s[1]) == len(lu):
                            for u, t in zip(hu, s[0]):
                                r[u] = t
                            for u, t in zip(lu, s[1]):
                                r[u] = t
                elif op == "ldsp" and ann and ann.pick(ann.ldsp, a, entry):
                    la = ann.pick(ann.ldsp, a, entry)
                    if final:
                        la.used.add(entry)
                    if la.value is not None:
                        nd = la.value + self.copy_base(a)
                        if d is not None and final:
                            la.check(nd <= d, f"tool sees depth {d - self.copy_base(a):+d} before it")
                        sl = {kk: v for kk, v in sl.items() if kk <= nd} if d is not None else dict(keep(sl))
                        self.restore_ra(a, sl, nd)
                elif op == "ldsp" and arg in ("HL", "IX", "IY") and \
                        self.spd16(*(regs[U[x]] for x in (pair_units(arg)[0] + pair_units(arg)[1]))) is not None:
                    # SP := an address on this routine's own stack (a frame
                    # carved or released with `ld hl,+-N / add hl,sp`): a
                    # known depth
                    nd = self.spd16(*(regs[U[x]] for x in (pair_units(arg)[0] + pair_units(arg)[1])))
                    ev("ldsp-frame", a, f"{ins.mnem}: depth {'?' if d is None else f'{d:+d}'} -> {nd:+d}")
                    sl = {kk: v for kk, v in sl.items() if kk <= nd} if d is not None else dict(keep(sl))
                    if nd >= 0 and 0 not in sl and d is None:
                        sl[0] = ((("ra", 0, "h"),), (("ra", 0, "l"),))
                elif op == "ldsp":
                    # from a constant / memory cell: a frame reset, control never
                    # comes back here (the path ends); from a register: a stack
                    # switch the analysis cannot follow
                    ev("ldsp-reg" if arg in ("HL", "IX", "IY") else "ldsp-reset", a, ins.mnem)
                    if nxt in self.entries:
                        flows.append(("cont", nxt, "reset"))
                    return
                elif op == "adjsp":
                    ev("adjsp", a, ins.mnem)
                    if d is not None:
                        nd = d + arg
                        sl = {kk: v for kk, v in sl.items() if kk <= nd}
            # value tracking: inc/dec (8 and 16 bit) and constant loads
            mn = ins.mnem
            if mn in ("or a", "and a", "ld a,a"):
                r[U["A"]] = regs[U["A"]]       # A unchanged (only flags)
            elif mn.startswith("inc ") or mn.startswith("dec "):
                n = 1 if mn.startswith("inc") else -1
                o_ = mn[4:].upper()
                if o_ in ("BC", "DE", "HL", "IX", "IY"):
                    (h,), (l_,) = pair_units(o_)
                    r[U[h]], r[U[l_]] = self.add16(regs[U[h]], regs[U[l_]], n)
                elif o_ in U and o_ in R8:
                    r[U[o_]] = self.add8(regs[U[o_]], n)
            elif mn in ("add hl,sp", "add ix,sp", "add iy,sp"):
                # HL := SP + n with n a constant: the address of stack depth d - n
                pr_ = mn[4:6].upper()
                (h,), (l_,) = pair_units(pr_)
                n = self.const16(regs[U[h]], regs[U[l_]])
                if n is not None and d is not None:
                    n = n - 0x10000 if n & 0x8000 else n
                    r[U[h]], r[U[l_]] = ("spd", d - n, "h"), ("spd", d - n, "l")
            elif mn in ("xor a", "sub a"):
                r[U["A"]] = ("k", 0)
                r[U["fZ"]] = ("k", 1)
            elif mn == "add a,a":
                va = regs[U["A"]]
                r[U["A"]] = ("k", va[1] * 2 & 0xFF) if va and va[0] == "k" else None
            elif mn.startswith("ld ") and "," in mn and not stk:
                dst, src = mn[3:].split(",", 1)
                D_ = dst.upper()
                if D_ in R8 and (src == "(hl)" or (src.startswith("($") and len(src) == 7)):
                    # a byte load from a fixed address: a ROM byte is a
                    # constant; a RAM cell is the symbolic value ("m", addr)
                    g = None
                    if src == "(hl)":
                        g = self.rt16(regs[U["H"]], regs[U["L"]])
                        ca = self.const16(regs[U["H"]], regs[U["L"]]) if g is None else g & 0xFFFF
                    else:
                        ca = int(src[2:6], 16)
                    if ca is not None:
                        g = base(g if g is not None else (a & ~0xFFFF) | ca)
                        b = None if p.is_ram(g) else p.read(g)
                        if b is not None:
                            r[U[D_]] = ("k", b)
                        elif src != "(hl)":     # RAM, or nothing mapped there
                            r[U[D_]] = ("m", ca)
                if src.startswith("$") and "(" not in dst:
                    try:
                        v = int(src[1:], 16)
                    except ValueError:
                        v = None
                    if v is not None:
                        if D_ in R8 and len(src) == 3:
                            r[U[D_]] = ("k", v)
                        elif D_ in ("BC", "DE", "HL", "IX", "IY") and len(src) == 5:
                            (h,), (l_,) = pair_units(D_)
                            r[U[h]], r[U[l_]] = ("k", v >> 8), ("k", v & 0xFF)
            # carry and zero as constants where the instruction fixes them, so
            # a flag a callee returns picks the caller's branch
            if mn == "scf":
                r[U["fC"]] = ("k", 1)
            elif mn == "ccf":
                v = regs[U["fC"]]
                r[U["fC"]] = ("k", 1 - v[1]) if v and v[0] == "k" else None
            elif mn.startswith(("and ", "or ", "xor ", "sub ")):
                if not mn.startswith("sub ") or mn == "sub a":
                    r[U["fC"]] = ("k", 0)
                va = r[U["A"]]
                if va and va[0] == "k" and mn != "sub a" or mn in ("xor a", "sub a"):
                    r[U["fZ"]] = ("k", int(va[1] == 0))
            # stores to fixed RAM addresses, forwarded to later loads in this
            # routine (kept in an extra element after the NU units; any call
            # or other memory write forgets them)
            mem = dict(regs[NU]) if len(regs) > NU and regs[NU] else {}
            if k in ("call", "rst"):
                mem = {}
            elif ins.mem_w:
                mst = re.match(r"ld \(\$([0-9A-F]{4})\),(a|bc|de|hl|ix|iy)$", mn)
                if mst:
                    ma = int(mst.group(1), 16)
                    src = mst.group(2).upper()
                    if src == "A":
                        mem[ma] = regs[U["A"]]
                    else:
                        (h,), (l_,) = pair_units(src)
                        mem[ma], mem[(ma + 1) & 0xFFFF] = regs[U[l_]], regs[U[h]]
                else:
                    mem = {}
            mld = re.match(r"ld (bc|de|hl|ix|iy),\(\$([0-9A-F]{4})\)$", mn)
            if mld:
                ma = int(mld.group(2), 16)
                if p.is_ram((a & ~0xFFFF) | ma):
                    (h,), (l_,) = pair_units(mld.group(1).upper())
                    r[U[l_]] = mem.get(ma, ("m", ma))
                    r[U[h]] = mem.get((ma + 1) & 0xFFFF, ("m", (ma + 1) & 0xFFFF))
            elif mn.startswith("ld a,($") and len(mn) == 11 and int(mn[7:11], 16) in mem:
                r[U["A"]] = mem[int(mn[7:11], 16)]
            r = r[:NU] + [tuple(sorted(mem.items(), key=lambda kv: kv[0])) if mem else None]
            if nd is not None:
                sl = {kk: v for kk, v in sl.items() if kk <= nd}
            post = (nd, tuple(r), tuple(sorted(sl.items())))

            if k == "seq" or k == "halt":
                flows.append(goto_flow(a, nxt, post, "fallthrough"))
            elif k in ("jp", "jr", "djnz"):
                if cv is not False:
                    flows.append(goto_flow(a, ins.target, on(taken_st if ins.cond else post, True), k))
                if (ins.cond and cv is not True) or k == "djnz":
                    flows.append(goto_flow(a, nxt, on(post, False), "fallthrough"))
            elif k in ("call", "rst") and ann and ann.r(ann.inline, base(ins.target)):
                # an inlined call: a copy of the callee's code per call site,
                # entered with the return address pushed as a known value
                if final:
                    ann.r(ann.inline, base(ins.target)).used.add(entry)
                cid = self.clone_ids.setdefault(a, len(self.clone_ids) + 1)
                self.clone_site[cid] = a
                tc = base(ins.target) | cid << CLONE
                _, cr, _ = on(taken_st if ins.cond else post, True)
                # the copy is tracked relative to an anchor depth; its return
                # takes the caller's depth from the call site's own state
                cd, cs = ANCHOR, ()
                sl2 = dict(cs)
                sl2[cd + 2] = ((("rt", nxt, "h", a),), (("rt", nxt, "l", a),))
                push_succ(tc, (cd + 2, cr, tuple(sorted(sl2.items()))))
                flows.append(("succ", tc))
                node["inline_call"] = tc
                if ins.cond and cv is not True:
                    flows.append(goto_flow(a, nxt, on(post, False), "call not taken"))
            elif k in ("call", "rst"):
                t = base(ins.target)
                node["call"] = t
                tes, tg = ann.site_targets(a, entry) if ann else (None, None)
                if tg is not None:
                    # declared callees (a call into code no image holds)
                    for te in tes:
                        if final:
                            te.used.add(entry)
                    fl = [via(a, on(taken_st if ins.cond else post, True), t2, "call", nxt) for t2 in self.want(tg, a)]
                    if cv is not False:
                        flows.append(fl[0] if len(fl) == 1 else ("any", fl))
                elif cv is not False:
                    flows.append(via(a, on(taken_st if ins.cond else post, True), t, "call", nxt))
                if ins.cond and cv is not True:
                    node["nt_succ"] = nxt
                    flows.append(goto_flow(a, nxt, on(post, False), "call not taken"))
            elif k in ("ret", "reti", "retn"):
                tes, tg = ann.site_targets(a, entry) if ann else (None, None)
                if tg is not None:
                    for te in tes:
                        if final:
                            te.used.add(entry)
                    td, tr, ts = taken_st
                    nsl = () if td is None else tuple((kk, v) for kk, v in ts if kk <= td - 2)
                    for t in self.want(tg, a):
                        flows.append(goto_flow(a, t, (None if td is None else td - 2, tr, nsl), "computed ret"))
                elif cv is not False:
                    flows.append(do_return(a, on(taken_st, True), 0, 0, {}, ins.mnem))
                if ins.cond and cv is not True:
                    flows.append(goto_flow(a, nxt, on(post, False), "fallthrough"))
            elif k == "jpind":
                pr = ins.mnem[4:-1].upper()
                (h,), (l_,) = pair_units(pr)
                th, tl = regs[U[h]], regs[U[l_]]
                tes, tg = ann.site_targets(a, entry) if ann else (None, None)
                cvs = self.consts16(th, tl)
                rt = ann.pick(ann.returns, a, entry) if ann else None
                if rt is not None and tg is None:
                    if final:
                        rt.used.add(entry)
                    th, tl = ("ra", 0, "h"), ("ra", 0, "l")
                if tg is not None:
                    for te in tes:
                        if final:
                            te.used.add(entry)
                    for t in self.want(tg, a):
                        flows.append(goto_flow(a, t, st, "dispatch"))
                elif self.rt16(th, tl) is not None and d is not None:
                    # back from an inlined copy through a register: the same as
                    # a `ret` with that value on the stack
                    sl2 = dict(slots)
                    sl2[d + 2] = ((th,), (tl,))
                    flows.append(do_return(a, (d + 2, regs, tuple(sorted(sl2.items()))), 0, 0, {}, ins.mnem))
                elif cvs is not None:
                    ev("jpind-const", a, f"{ins.mnem} with {pr} = " + "/".join(f"${t:04X}" for t in cvs))
                    for cv in cvs:
                        flows.append(goto_flow(a, cv | (a & ~0xFFFF), st, "jp (rr) constant"))
                elif th and tl and th[0] == "ra" and tl[0] == "ra" and th[1] == tl[1] \
                        and th[2] == "h" and tl[2] == "l":
                    # a return through a register: the RA was popped, so the
                    # caller sees the depth it was pushed at (d + 2) as delta
                    if d is None:
                        if declared_se is not None:
                            if final:
                                declared_se.used.add(entry)
                            flows.append(add_exit(a, (0, 0, th[1], declared_se.value), regs, {}, from_decl=True))
                        else:
                            ev("jpind-return-unknown-depth", a, f"{ins.mnem} returns to RA+{th[1]} at an unknown depth")
                            flows.append(("unknown",))
                    else:
                        xs = {y + 2: c for y, c in sl.items() if -2 < y <= d}
                        if d + 2:
                            ev("exit-stack-delta", a, f"{ins.mnem} returns to RA+{th[1]} leaving SP {d + 2:+d} for the caller")
                        else:
                            ev("jpind-return", a, f"{ins.mnem} jumps to its own return address +{th[1]}")
                        flows.append(add_exit(a, (0, 0, th[1], d + 2), regs, xs, slots=tuple(sl.items())))
                else:
                    ev("jpind-unresolved", a, ins.mnem)
                    flows.append(("unknown",))


        capped = set()
        while work:
            a = work.popleft()
            visits[a] += 1
            if visits[a] > 64:
                capped.add(a)
                continue
            step(a)
        # the iteration saw intermediate states: record events, exits and
        # flows again from the converged states only
        events.clear()
        ev_seen.clear()
        exits.clear()
        nodes.clear()
        final = True
        for a in sorted(states):
            step(a)
        for a in capped:
            ev("analysis-cap", a)
        for c in conflicts:
            if not (ann and ann.pick(ann.depth, c, entry)):
                ev("depth-conflict", c, "paths arrive with different stack depths")
        return {"entry": entry, "nodes": nodes, "events": events, "exits": exits,
                "noreturn": not exits, "far": far, "farres": farres}

    def forward_same_as(self, entry, target):
        """The record of a routine declared `same-as-callee`: one tail jump."""
        from .decode import Instr
        node = {"ins": Instr(entry), "flows": [], "depth": 0}
        rec = {"entry": entry, "nodes": {entry: node}, "events": [], "exits": {}, "noreturn": False, "far": {}, "farres": {}}
        o, summ = self.callee_summary(target)
        res = []
        for key, ex in summ["exits"].items():
            rec["exits"][key] = {"out": tuple(self.norm(v) for v in ex["out"]), "slots": dict(ex["slots"])}
            res.append((key, ("exit", exit_class(key))))
        rec["noreturn"] = not rec["exits"]
        node["flows"].append(("via", o if o is not None else target, 0, res))
        return rec

    @staticmethod
    def flow_targets(f):
        """Routine entries a flow depends on (calls, tails), recursively."""
        if f[0] == "any":
            for g in f[1]:
                yield from Analysis.flow_targets(g)
        if f[0] == "kill":
            yield from Analysis.flow_targets(f[2])
        if f[0] == "via":
            if isinstance(f[1], int):
                yield f[1]
            for _, g in f[3]:
                yield from Analysis.flow_targets(g)

    def forward_all(self):
        """Fixpoint of forward summaries across routines (optimistic start)."""
        ann = self.p.annotations
        callers = defaultdict(set)
        work = deque(sorted(self.entries))
        inq = set(work)
        rounds = 0
        while work:
            e = work.popleft()
            inq.discard(e)
            rounds += 1
            if rounds > 50 * max(1, len(self.entries)):
                self.log.append("forward fixpoint capped")
                break
            if ann and ann.r(ann.same_as, e):
                ann.r(ann.same_as, e).used.add(e)
                rec = self.forward_same_as(e, self.rebase([ann.r(ann.same_as, e).value], e)[0])
            else:
                rec = self.forward(e)
            old = self.fsum.get(e)
            for a, n in rec["nodes"].items():
                for f in n["flows"]:
                    for t in self.flow_targets(f):
                        callers[t].add(e)
                    if f[0] == "cont":
                        callers[f[1]].add(e)
            self.frec[e] = rec
            new = {"exits": rec["exits"]}
            if old is None or old["exits"] != new["exits"]:
                self.fsum[e] = new
                for c in callers[e]:
                    if c not in inq:
                        work.append(c)
                        inq.add(c)
        self.callers = callers

    def solve_liveness(self):
        self.lsum = {}
        self.lin_in = {}
        self.aL = {}
        self.liveness_all()
        self.contexts()
        # a reset continuation's exit-live comes from its frame owners'
        # contexts, which come from liveness: iterate up from nothing live
        for _ in range(12):
            new = {c: dict(self.Lc[c]) for c in self.anchor_frame}
            if new == self.aL:
                break
            moved = {c for c in self.anchor_frame if new[c] != self.aL.get(c, {})}
            self.aL = new
            self.liveness_all({u for c in moved for u in self.cont_users.get(c, ())})
            self.contexts()
        else:
            self.log.append("stack-anchor fixpoint capped: resets taken as returning anywhere")
            self.anchor_frame = {}
            self.lsum = {}
            self.lin_in = {}
            self.liveness_all()
            self.contexts()

    def normal_view(self):
        """Liveness again, leaving out what is read after an unwind (a reset
        through a `stack-anchor C unwind` cell, an `abort ... unwind`): what
        callers rely on along paths that do not abandon what is running (an
        error, a restart). Returns {"lsum", "L",
        "L1", "sites"}; the analysis's own results are left as they were."""
        keep = (self.lsum, self.lin_in, self.L, self.L1, self.Lc, self.sites, self.aL, self.anchor_frame)
        self.reset_reads = False
        try:
            self.solve_liveness()
            view = {"lsum": self.lsum, "L": self.L, "L1": self.L1, "sites": self.sites}
        finally:
            self.reset_reads = True
            self.lsum, self.lin_in, self.L, self.L1, self.Lc, self.sites, self.aL, self.anchor_frame = keep
        return view

    def stack_anchors(self):
        """Reset continuations whose frame is known. `ld sp,(C)` lands where
        `ld (C),sp` saved SP; when every such save is at depth 0 of a routine
        R (SP at its return address) and nothing else writes C (or the
        program says its other writes are relocations: `stack-anchor C`),
        the continuation's returns are R's returns. A cell written another
        way, or saved at another depth, keeps the old answer: the
        continuation may return anywhere, everything live there."""
        ann = self.p.annotations
        saves = defaultdict(set)      # cell -> routines that save SP there (None: not at depth 0)
        other = set()                 # cell bytes written some other way
        into = defaultdict(set)       # continuation -> cells it is reset from (None: not a cell)
        self.cont_users = defaultdict(set)
        for e, rec in self.frec.items():
            for a, n in rec["nodes"].items():
                ins = n["ins"]
                w = re.match(r"ld \(\$([0-9A-F]{4})\),(\w+)$", ins.mnem)
                if w:
                    c = int(w.group(1), 16)
                    if w.group(2) == "sp":
                        saves[c].add(e if n["depth"] == 0 and not a >> CLONE else None)
                    else:
                        other.add(c)
                        if len(w.group(2)) == 2:
                            other.add((c + 1) & 0xFFFF)
                for f in n["flows"]:
                    if f[0] != "cont":
                        continue
                    self.cont_users[f[1]].add(e)
                    st = ins.stack
                    if st and st[0] == "ldsp" and st[1].startswith("("):
                        into[f[1]].add(int(st[1][2:6], 16))
                    else:
                        into[f[1]].add(None)
        self.anchor_saves = saves
        ok = set()
        for c, rs in saves.items():
            declared = ann is not None and c in ann.anchor
            if None not in rs and (declared or not ({c, (c + 1) & 0xFFFF} & other)):
                ok.add(c)
        self.anchor_frame = {}
        for t, cs in into.items():
            if cs <= ok and t in self.frec:
                self.anchor_frame[t] = set().union(*(saves[c] for c in cs))
        err = {c for c, e in (ann.anchor.items() if ann else ()) if e.value}
        self.unwind_conts = {t for t, cs in into.items() if cs and cs <= err}

    # -- 5. liveness -------------------------------------------------------
    # A liveness state is (G, {class: M}): live = G | M[e] for each unit e live
    # where the routine's exits of that class land (exit_class: level and the
    # flags it fixes; ANYX: every exit). Slot units (bits 32..63) track stack
    # slots by depth.
    def node_ops(self, n):
        """(kill, gen, conds) for the instruction itself, given its depth."""
        ins = n["ins"]
        d = n.get("ldepth", n["depth"])
        kill = ins.writes & REAL
        gen = ins.reads & REAL
        conds = []
        for dst, src in ins.copies:
            kill |= 1 << dst
            conds.append((1 << dst, 1 << src))
        stk = ins.stack
        if stk and stk[0] in ("push", "pop", "exsp") and d is not None and d % 2 == 0:
            hi, lo = pair_units(stk[1])
            hm = 0
            lm = 0
            for x in hi:
                hm |= 1 << U[x]
            for x in lo:
                lm |= 1 << U[x]
            op = stk[0]
            if op == "push" and 0 <= d and d + 2 <= MAXD:
                sh, sl = slot_bits(d + 2)
                gen &= ~(hm | lm)
                kill |= sh | sl
                conds += [(sh, hm), (sl, lm)]
            elif op == "pop" and 2 <= d <= MAXD:
                sh, sl = slot_bits(d)
                conds += [(hm, sh), (lm, sl)]
            elif op == "exsp" and 2 <= d <= MAXD:
                sh, sl = slot_bits(d)
                gen &= ~(hm | lm)
                kill |= sh | sl | hm | lm
                conds += [(hm, sh), (lm, sl), (sh, hm), (sl, lm)]
        return kill, gen, conds

    @staticmethod
    def lin(x, kill, gen, conds):
        y = (x & ~kill) | gen
        for dm, sm in conds:
            if x & dm:
                y |= sm
        return y

    def apply_ops(self, st, ops):
        kill, gen, conds = ops
        G, Ms = st
        G2 = self.lin(G, kill, gen, conds)
        if not conds:
            if not kill:
                return (G2, Ms)
            nk = ~kill
            return (G2, {c: tuple(mm & nk for mm in M) for c, M in Ms.items()})
        lin = self.lin
        return (G2, {c: tuple(lin(mm, kill, 0, conds) if mm else 0 for mm in M) for c, M in Ms.items()})

    @staticmethod
    def union(a, b):
        if a is None:
            return b
        if b is None:
            return a
        Ms = dict(a[1])
        for c, M in b[1].items():
            Ms[c] = M if c not in Ms else tuple(x | y for x, y in zip(Ms[c], M))
        return (a[0] | b[0], Ms)

    @staticmethod
    def m_of(Ms, c):
        """The map for exit class c (plus what an unknown path gives every exit)."""
        M, W = Ms.get(c), Ms.get(ANYX)
        if M is None:
            return W if W is not None else ZERO_M
        return M if W is None else tuple(x | y for x, y in zip(M, W))

    @staticmethod
    def l_of(L, c):
        """Exit-live for exit class c from a routine's per-class exit-live."""
        if c == ANYX:
            v = 0
            for x in L.values():
                v |= x
            return v
        return L.get(c, 0) | L.get(ANYX, 0)

    def summ_state(self, x):
        if not isinstance(x, int):
            return self.opaque_state(x)
        s = self.lsum.get(x)
        if s is None:
            return (0, {})
        return s

    @staticmethod
    def opaque_state(o):
        M = tuple((1 << e) if o.preserves >> e & 1 else 0 for e in range(NU))
        return (o.inputs & REAL, {exit_class(o.exit): M} if o.exit is not None else {})

    @staticmethod
    def slot_units(c):
        """Unit mask of a slot half's content (entry values), REAL if unknown."""
        mk = 0
        for v in c:
            if v is not None and v[0] in ("o", "od"):
                mk |= 1 << v[1]
            elif v is not None and v[0] == "o16":
                mk |= 1 << v[1] | 1 << v[2]
            elif v is not None and v[0] == "k":
                pass
            else:
                return REAL
        return mk

    def remap_slots(self, A, D, delta, pushed):
        """After-state of a call that changed SP by delta -> the state just after
        the callee's frame is gone, in the caller's slot numbering."""
        G, Ms = A
        if D is None or delta is None or (delta == 0 and not pushed):
            return A, 0

        def f(x):
            y = x
            for p_ in range(2, MAXD + 1, 2):
                if p_ <= min(D, D + delta):
                    continue
                sh, sl = slot_bits(p_)
                if x & (sh | sl):
                    y &= ~(sh | sl)
                    c = pushed.get(p_ - D)
                    if c is None:
                        y |= REAL
                    else:
                        if x & sh:
                            y |= self.slot_units(c[0])
                        if x & sl:
                            y |= self.slot_units(c[1])
            return y
        # (slots the callee consumed are read: consumed_slots)
        return (f(G), {c: tuple(f(mm) for mm in M) for c, M in Ms.items()}), 0

    @staticmethod
    def consumed_slots(D, key):
        """Slot units of the caller (depth D at the call) that a callee exit
        takes off the stack -- read, as far as liveness knows."""
        if D is None:
            return 0
        level, x, k, delta = key[:4]
        if level == 0:
            if delta is None or delta >= 0:
                return 0
            lo = D + delta + 2
        else:
            lo = D + x
        gen = 0
        for p_ in range(max(2, lo), min(D, MAXD) + 1, 2):
            sh, sl = slot_bits(p_)
            gen |= sh | sl
        return gen

    @staticmethod
    def through(x, MX):
        y = x & SLOTS
        for b in bits(x & REAL):
            y |= MX[b]
        return y

    def eval_flow(self, f, IN):
        k = f[0]
        if k == "kill":     # units overwritten after a callee returns
            G, Ms = self.eval_flow(f[2], IN)
            m = ~f[1]
            return (G & m, {c: tuple(x & m for x in M) for c, M in Ms.items()})
        if k == "use":
            return (f[1], {})
        if k == "any":
            out = None
            for g in f[1]:
                out = self.union(out, self.eval_flow(g, IN))
            return out
        if k == "succ":
            return IN.get(f[1], (0, {}))
        if k == "exit":
            return (0, {f[1]: IDENT})
        if k == "unknown":
            return (REAL, {ANYX: IDENT})
        if k in ("abort", "cont") and not self.reset_reads and \
                (f[-1] == "unwind" or k == "cont" and f[1] in self.unwind_conts):
            return (0, {})      # the normal-path view
        if k == "abort":
            return (f[1], {})
        if k == "cont":
            # control goes on in another routine and never comes back here:
            # everything live at its entry, with everything live at its exits
            if f[1] not in self.frec:
                return (REAL, {})
            if f[1] not in self.lsum:
                # not summarised yet: start from nothing, as for a callee (a
                # cycle through an error reset must not keep a made-up start)
                return (0, {})
            if f[1] in self.anchor_frame:
                # a reset into a known routine's frame: its returns are that
                # routine's returns
                return (self.concrete(self.lsum[f[1]], self.aL.get(f[1], {})), {})
            G, Ms = self.lsum[f[1]]
            for M in Ms.values():
                for x in M:
                    G |= x
            return (G & REAL, {})
        # via: callee summary composed with each exit's continuation
        _, t, D, res = f
        UX, MXs = self.summ_state(t)
        G = UX
        out = {}
        exits = self.callee_exits(t)
        for key, g in res:
            A = self.eval_flow(g, IN)
            MX = self.m_of(MXs, exit_class(key))
            if g[0] == "succ" and key[0] == 0:
                pushed = exits.get(key, {}).get("slots", {})
                A, _ = self.remap_slots(A, D, key[3], pushed)
            G |= self.consumed_slots(D, key)
            for r in exits.get(key, {}).get("peek", ()):      # caller slots it read and put back
                if D is not None and 2 <= D + r <= MAXD:
                    sh, sl = slot_bits(D + r)
                    G |= sh | sl
            G |= self.through(A[0], MX)
            for c, M in A[1].items():
                o = out.setdefault(c, [0] * NU)
                for e_ in range(NU):
                    if M[e_]:
                        o[e_] |= self.through(M[e_], MX)
        return (G, {c: tuple(o) for c, o in out.items()})

    def callee_exits(self, t):
        if not isinstance(t, int):
            return self.opaque_summary(t)["exits"]
        return self.fsum.get(t, {}).get("exits", {})

    def liveness_routine(self, e):
        rec = self.frec[e]
        nodes = rec["nodes"]
        order = sorted(nodes, reverse=True)
        IN = {}
        changed = True
        it = 0
        while changed and it < 100:
            changed = False
            it += 1
            for a in order:
                n = nodes[a]
                ins = n["ins"]
                out = None
                for f in n["flows"]:
                    out = self.union(out, self.eval_flow(f, IN))
                if out is None:
                    out = (0, {})
                if n.get("abort"):
                    new = out
                else:
                    new = self.apply_ops(out, self.node_ops(n))
                if ins.cond:
                    new = (new[0] | (COND_FLAG[ins.cond] & REAL), new[1])
                if IN.get(a) != new:
                    IN[a] = new
                    changed = True
        self.lin_in[e] = IN
        st = IN.get(e, (0, {}))
        return (st[0] & REAL, {c: tuple(mm & REAL for mm in M) for c, M in st[1].items()})

    def liveness_all(self, seeds=None):
        work = deque(sorted(self.entries if seeds is None else seeds))
        inq = set(work)
        n = 0
        while work:
            e = work.popleft()
            inq.discard(e)
            n += 1
            if n > 60 * max(1, len(self.entries)):
                self.log.append("liveness fixpoint capped")
                break
            s = self.liveness_routine(e)
            if self.lsum.get(e) != s:
                self.lsum[e] = s
                for c in self.callers.get(e, ()):
                    if c not in inq:
                        work.append(c)
                        inq.add(c)

    # -- 6. contexts -------------------------------------------------------
    @staticmethod
    def concrete(st, L):
        """Live units for a state, given the routine's per-class exit-live."""
        G, Ms = st
        y = G
        for c, M in Ms.items():
            for b in bits(Analysis.l_of(L, c)):
                y |= M[b]
        return y & REAL

    def contexts(self):
        L = {}      # routine -> {exit class: units live where those exits land}
        for e, why in self.entries.items():
            called = self.callers_of_call.get(e) or self.tailed.get(e)
            L[e] = {} if called else {ANYX: REAL}
            if why in ("interrupt", "root (no static reference)", "continuation after ld sp"):
                L[e] = {ANYX: REAL}
            if e in self.anchor_frame:
                L[e] = {}
        sites = {}

        def conc(f, e, IN):
            k = f[0]
            if k == "kill":
                v = conc(f[2], e, IN)
                return None if v is None else v & ~f[1]
            if k == "use":
                return None
            if k == "succ":
                return self.concrete(IN.get(f[1], (0, {})), L[e])
            if k == "exit":
                return self.l_of(L[e], f[1])
            if k == "unknown":
                return REAL
            if k in ("abort", "cont"):
                return 0
            return None

        changed = True
        it = 0
        while changed and it < 50:
            changed = False
            it += 1
            for c, owners in self.anchor_frame.items():
                v = L[c].get(ANYX, 0)
                for o in owners:
                    v |= self.l_of(L[o], ANYX) if o in L else REAL
                if v != L[c].get(ANYX, 0):
                    L[c][ANYX] = v
                    changed = True
            for e in self.entries:
                IN = self.lin_in.get(e, {})

                def walk(f, a):
                    nonlocal changed
                    if f[0] == "any":
                        for g in f[1]:
                            walk(g, a)
                        return
                    if f[0] == "kill":
                        walk(f[2], a)
                        return
                    if f[0] != "via":
                        return
                    t = f[1]
                    tot = 0
                    for key, g in f[3]:
                        if g[0] == "kill" and g[2][0] in ("via", "any"):
                            walk(g[2], a)
                            v = self.concrete(self.eval_flow(g, IN), L[e])
                        elif g[0] in ("via", "any"):
                            walk(g, a)
                            # what its callee needs is what is live before it
                            v = self.concrete(self.eval_flow(g, IN), L[e])
                        else:
                            v = conc(g, e, IN)
                        if v is None:
                            continue
                        tot |= v
                        if isinstance(t, int) and t in L:
                            c = exit_class(key)
                            cur = L[t].get(c, 0)
                            if cur | v != cur and self.l_of(L[t], c) | v != self.l_of(L[t], c):
                                L[t][c] = cur | v
                                changed = True
                    if isinstance(t, int):
                        sites[(e, a)] = (t, sites.get((e, a), (t, 0))[1] | tot)
                for a, n in self.frec[e]["nodes"].items():
                    for f in n["flows"]:
                        walk(f, a)
        self.Lc = L
        # per level, for reports: live where the normal / level-1 exits land
        self.L = {e: self.l_of({c: v for c, v in x.items() if c == ANYX or c[0] == 0}, ANYX) for e, x in L.items()}
        self.L1 = {e: self.l_of({c: v for c, v in x.items() if c == ANYX or c[0] == 1}, ANYX) for e, x in L.items()}
        self.sites = sites

    # -- driver ------------------------------------------------------------
    def ksets_from(self):
        """Per routine: the set of return offsets (level-0 k) callers continue at."""
        ann = self.p.annotations
        out = {}
        for e, rec in self.frec.items():
            ks = {key[2] for key in rec["exits"] if key[0] == 0}
            unk = any(k in self.UNKNOWN_EVENTS for k, _, _ in rec["events"])
            touched = any(k in ("exsp-ra", "pop-ra", "jpind-return", "exit-stack-delta",
                                "exit-callers-caller") for k, _, _ in rec["events"])
            if not ks and unk:
                ks = {0}        # cannot tell: assume it returns normally
            if ann and ann.r(ann.noreturn, e):
                ks = set()
            if ks != {0} or touched:
                out[e] = frozenset(ks)
        return out

    def run(self):
        self.ksets = {}
        for r in range(self.max_rounds):
            self.discover()
            self.fsum = {}
            self.frec = {}
            self.forward_all()
            newk = self.ksets_from()
            self.inferred_k = {e: (min(v) if len(v) == 1 else None) for e, v in newk.items()}
            # a program's own declaration fills in where inference cannot
            for a, n in self.p.declared_inline.items():
                if a in self.entries and (newk.get(a) is None or len(newk[a]) != 1):
                    newk[a] = frozenset({n})
            # a far call resolved into code that is not a routine entry yet
            # (reached only by jumps): make it one, so it gets a summary
            missing = set()
            for rec in self.frec.values():
                for _, vs in rec["farres"].values():
                    for t in vs or ():
                        if t >= 0 and t not in self.entries and self.p.in_code(t) and self.p.opaque_at(t) is None:
                            missing.add(t)
            missing |= {t for t in self.want_entries if t not in self.entries}
            for t in missing:
                self.p.roots.setdefault(t, self.p.exact_name(t))
                self.far_entries.add(t)
            if newk == self.ksets and not missing:
                break
            self.ksets = newk
            self.log.append(f"round {r}: return-offset map changed -> {len(newk)} stack-manipulating "
                            "callees; rediscover")
        self.rounds = r + 1
        self.kmap = {e: (min(v) if len(v) == 1 else None) for e, v in self.ksets.items()}
        self.callers_of_call = defaultdict(set)
        self.tailed = defaultdict(set)
        for e, rec in self.frec.items():
            for a, n in rec["nodes"].items():
                for f in n["flows"]:
                    if f[0] == "any":
                        for t in self.flow_targets(f):
                            self.tailed[t].add((e, a))
                        continue
                    if f[0] != "via" or not isinstance(f[1], int):
                        continue
                    if n.get("call") == f[1]:
                        self.callers_of_call[f[1]].add((e, a))
                    else:
                        self.tailed[f[1]].add((e, a))
                    for t in self.flow_targets(("via", None, None, f[3])):
                        self.tailed[t].add((e, a))
        # far calls: per site, the constant targets seen (None: not constant
        # on some path through some routine)
        self.far_resolved = {}
        for e, rec in self.frec.items():
            for a, (n, vs) in rec.get("farres", {}).items():
                old = self.far_resolved.get(a, (n, frozenset()))
                self.far_resolved[a] = (n, None if vs is None or old[1] is None else old[1] | vs)
        self.far_sites = {}
        for e, rec in self.frec.items():
            for a, (t, vs) in rec["far"].items():
                old = self.far_sites.get(a, (t, frozenset()))
                self.far_sites[a] = (t, None if vs is None or old[1] is None else old[1] | vs)
        self.stack_anchors()
        self.solve_liveness()
        self.classify_routines()
        self.check_annotations()
        return self

    # -- status ------------------------------------------------------------
    UNKNOWN_EVENTS = {
        "jpind-unresolved": "indirect jump",
        "jpind-return-unknown-depth": "returns through jp (rr) at an unknown depth",
        "ret-push-jump": "push-then-ret jump to a computed address",
        "ret-computed-jump": "ret through a replaced return address",
        "ret-below-frame": "ret below the frame at an odd offset",
        "ret-unknown-depth": "ret at unknown stack depth",
        "tail-unknown-depth": "tail jump at unknown stack depth",
        "ldsp-reg": "loads SP from a register (stack switch)",
        "call-into-ram": "calls into RAM",
        "exsp-unknown-depth": "ex (sp) at unknown depth",
        "caller-slot-changed": "returns with a slot of its caller's frame changed",
        "inline-touches-caller-frame": "an inlined copy takes a slot of the enclosing routine's frame",
        "analysis-cap": "analysis cap hit",
        "flow-off-code": "flow leaves the code",
        "annotation-mismatch": "an annotation disagrees with the analysis",
        "far-callee-convention": "a far-called routine does not return plainly",
        "callee-not-analysed": "calls or jumps to code that is not an analysed routine",
    }

    def clobbers(self, e, levels=(0, 1)):
        """Units some exit (of the given levels) may leave changed."""
        rec = self.frec.get(e)
        if rec is None:
            return REAL
        c = 0
        for key, ex in rec["exits"].items():
            if key[0] not in levels:
                continue
            for u in range(NU):
                if ex["out"][u] != ("o", u):
                    c |= 1 << u
        return c

    def stack_conventions(self, e):
        """Human description of a routine's non-plain exits."""
        out = []
        for key in sorted(self.frec[e]["exits"], key=lambda t: exit_order((t,))):
            lvl, x, k, delta = key[:4]
            if lvl == 0 and delta == 0:
                if k:
                    out.append(f"returns to RA+{k}")
                continue
            s = "returns" if lvl == 0 else ("exits to the caller's caller" if x == 0
                                            else f"exits via the caller's slot at its depth {x:+d}")
            if k:
                s += f" +{k}"
            if delta != 0:
                s += f", SP {fmt_delta(delta)}"
            out.append(s)
        return list(dict.fromkeys(out))

    def classify_routines(self):
        ann = self.p.annotations
        direct = {}
        ext = {}
        deps = defaultdict(set)

        def opq(f, acc):
            if f[0] == "any":
                for g in f[1]:
                    opq(g, acc)
            if f[0] == "kill":
                opq(f[2], acc)
            if f[0] == "via":
                if not isinstance(f[1], int) and coarse(f[1]):
                    acc.add(boundary_label(f[1]))
                for _, g in f[3]:
                    opq(g, acc)

        for e, rec in self.frec.items():
            reasons = []
            for kind, a, det in rec["events"]:
                if kind in self.UNKNOWN_EVENTS:
                    reasons.append((kind, a, det))
            if ann and ann.r(ann.noreturn, e) and rec["exits"] and not ann.r(ann.same_as, e):
                ann.r(ann.noreturn, e).check(False, f"tool sees exits {sorted(rec['exits'], key=repr)}")
                reasons.append(("annotation-mismatch", e, "declared noreturn, but the tool sees it return"))
            elif ann and ann.r(ann.noreturn, e):
                # evidence only if the tool followed every path of it
                full = not any(k in self.UNKNOWN_EVENTS for k, _, _ in rec["events"])
                ann.r(ann.noreturn, e).check(True, "no return path seen" if full else
                                             "no return path seen, but not every path was followed",
                                             weak=not full)
            if ann and ann.r(ann.inline, e):
                reasons = []     # analysed inside its callers instead
            direct[e] = reasons
            x = set()
            for a, n in rec["nodes"].items():
                for f in n["flows"]:
                    opq(f, x)
                    deps[e].update(self.flow_targets(f))
            ext[e] = x
        if ann:
            for e in self.frec:
                if ann.r(ann.inline, e):
                    continue
                for d in deps[e]:
                    if ann.r(ann.inline, d):
                        direct[e].append(("inline-not-applied", e, f"reaches {self.p.exact_name(d)} "
                                                                   "without the per-call-site copy"))
        unknown = {e for e, r in direct.items() if r}
        changed = True
        via = {}
        while changed:
            changed = False
            for e in self.frec:
                if e in unknown:
                    continue
                for d in deps[e]:
                    if d in unknown:
                        unknown.add(e)
                        via[e] = d
                        changed = True
                        break
        extt = {e: set(v) for e, v in ext.items()}
        changed = True
        while changed:
            changed = False
            for e in self.frec:
                for d in deps[e]:
                    if not extt.get(d, set()) <= extt[e]:
                        extt[e] |= extt.get(d, set())
                        changed = True
        status = {}
        for e in self.frec:
            if ann and ann.r(ann.inline, e):
                status[e] = "inlined"
            elif direct[e]:
                status[e] = "unknown"
            elif e in unknown:
                status[e] = "unknown-via-callee"
            elif extt[e]:
                status[e] = "conservative-boundary"
            else:
                status[e] = "inferred"
        self.direct = direct
        self.via = via
        self.ext_direct = ext
        self.ext_trans = extt
        self.status = status
        self.deps = deps

    def check_annotations(self):
        """Cross-checks that need the whole analysis (targets decode as code, ...)."""
        ann = self.p.annotations
        if not ann:
            return
        seen = {}

        def reaches(r, a):
            # in routine r's analysis -- in any context, any inlined copy
            if r not in seen:
                seen[r] = set()
                for e, rec in self.frec.items():
                    if self.canon(e) == r:
                        seen[r].update(self.canon(n) for n in rec["nodes"])
            return a in seen[r]
        for a, es in ann.targets.items():
            for e in es:
                bad = [t for t in e.value if not is_external(t) and t not in self.code and self.boundary(t) is None]
                if a not in self.code:
                    e.check(False, f"site ${a:04X} is not decoded code")
                elif bad:
                    e.check(False, "targets not decoded as code: " + ", ".join(f"${t:04X}" for t in bad))
                else:
                    ins = self.code[a]
                    e.check(ins.kind in ("jpind", "ret", "call"), f"site is `{ins.mnem}`", weak=True)
                    n = sum(1 for t in e.value if not is_external(t))
                    if n:
                        # (only that the list is plausible: not that the
                        # dispatch goes there)
                        e.check(True, f"all {n} target(s) decode as code", weak=True)
        for a, es in list(ann.depth.items()) + list(ann.abort.items()) + list(ann.returns.items()) + \
                list(ann.ldsp.items()) + list(ann.call_noret.items()) + list(ann.values.items()):
            for e in es:
                if a not in self.code:
                    e.check(False, f"site ${a:04X} is not decoded code")
                elif e.kind == "returns-to-callers-caller":
                    e.check(self.code[a].kind in ("ret", "jpind"), f"site is `{self.code[a].mnem}`", weak=True)
                elif e.kind == "return":
                    e.check(self.code[a].kind == "jpind", f"site is `{self.code[a].mnem}`", weak=True)
                elif e.kind == "call-never-returns":
                    e.check(self.code[a].kind in ("call", "rst"), f"site is `{self.code[a].mnem}`", weak=True)
                elif e.kind == "ld-sp":
                    st = self.code[a].stack
                    e.check(bool(st and st[0] == "ldsp"), f"site is `{self.code[a].mnem}`", weak=True)
                for r in e.only or ():
                    if not reaches(r, a):
                        e.check(False, f"in={self.p.exact_name(r)}: that routine's analysis never reaches the site")
        for a, es in ann.targets.items():
            for e in es:
                for r in e.only or ():
                    if not reaches(r, a):
                        e.check(False, f"in={self.p.exact_name(r)}: that routine's analysis never reaches the site")
        for c, e in ann.anchor.items():
            rs = self.anchor_saves.get(c, set())
            e.used.add(c)
            if not rs:
                e.check(False, f"no `ld (${c:04X}),sp` in the analysed code")
            elif None in rs:
                e.check(False, f"an `ld (${c:04X}),sp` is not at a routine's entry depth")
            else:
                e.check(True, f"{len(rs)} routine(s) save SP there, each at its entry depth: "
                        + ", ".join(sorted(self.p.exact_name(r) for r in rs)))
        for a, e in list(ann.noreturn.items()) + list(ann.stack_effect.items()) + list(ann.same_as.items()):
            if a not in self.entries:
                e.check(False, f"${a:04X} is not a routine entry")

    def contract(self, e, view=None):
        """e's contract; view: a normal_view() result to read liveness from."""
        lsum, sites, L = (self.lsum, self.sites, self.L) if view is None else \
            (view["lsum"], view["sites"], view["L"])
        U_ = lsum.get(e, (0, {}))[0]
        clob = self.clobbers(e)
        used = 0
        for (caller, a), (callee, after) in sites.items():
            if callee == e:
                used |= after & clob
        return {"inputs": U_, "clobbers": clob, "outputs_used": used,
                "clobbers_normal": self.clobbers(e, (0,)), "exit_live": L.get(e, 0)}


CLONE = 24      # bits >= 24 of an address: which inlined copy (0 = none)
ANCHOR = 1 << 20   # stack depth an inlined copy entered at an unknown depth is tracked from
TOUCH = -(1 << 30)  # slot-dict key: the caller slots (depths < 0) a path has popped or swapped


def base(a):
    """An address without its inlined-copy tag (context and Z80 address)."""
    return a & 0xFFFFFF


def boundary_label(o):
    """A name for a boundary in the report: its class for a whole class of
    external targets (BIOS entries, islands), else its own name."""
    if o.kind.startswith("bios") or "island" in o.kind:
        return o.kind
    return o.name if o.name.startswith(o.kind) else f"{o.kind} {o.name}"


def exit_class(key):
    """The liveness class of an exit: its level, and the flags it fixes."""
    return (key[0], key[4] if len(key) > 4 else ())


def exit_order(kv):
    return tuple(-1 << 20 if x is None else x for x in kv[0])


def fmt_delta(n):
    return "variable" if n is None else f"{n:+d}"


def fmt(mask):
    return fmt_units(mask)
