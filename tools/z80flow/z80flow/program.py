# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Core description of WHAT to analyse. Z80-generic: no platform facts here.

A platform adapter (e.g. platform_msx) and a program adapter (e.g.
program_zerobas) fill one of these in. The analysis only ever asks it:

  * which bytes exist        -- images mapped at address ranges
  * which bytes are code     -- code_ranges (targets outside are external)
  * where to start           -- candidate roots, interrupt entries
  * what a boundary does     -- Opaque: a declared effect for an address (or a
                                range) the analysis must not, or cannot, enter:
                                far calls, inline-data calls, RAM hooks, ...
  * where a far call's target is -- far_target_regs: the register pair that
                                carries it (constant-folded per call site)
  * what to call an address  -- labels, and classify() for external targets
"""
from .decode import REAL, U


class Opaque:
    """A declared boundary.

    inputs    -- unit mask the boundary may read (liveness: these are live before it)
    preserves -- unit mask it leaves untouched (everything else is clobbered)
    inline    -- bytes of inline data after the call site that it skips
    kind      -- free-form category for the report ('far-call', 'hook', ...);
                 the core never interprets it
    noreturn  -- control never comes back to the call site
    in_ram    -- the target is RAM: its code is not in any image, so whatever
                 runs there is outside the analysis
    patch_point -- a RAM cell that exists to be patched (an extension hook)
    declared  -- the effect is stated by an adapter (False only for the
                 default made up for an undeclared external target); a
                 transfer into RAM that nothing declared is an unknown site
    exit      -- how control comes back (see analysis: level, x, k, delta)
    """

    def __init__(self, name, kind, inputs=REAL, preserves=0, inline=0, noreturn=False, note="",
                 in_ram=False, patch_point=False, declared=True, exit=None):
        self.name = name
        self.kind = kind
        self.inputs = inputs
        self.preserves = preserves
        self.inline = inline
        self.noreturn = noreturn
        self.note = note
        self.in_ram = in_ram
        self.patch_point = patch_point
        self.declared = declared
        # how it returns, as an analysis exit key (level, x, k, delta); the
        # default is a plain return past `inline` bytes
        self.exit = exit if exit is not None else (0, 0, inline, 0)


def coarse(o):
    """A boundary whose effect is assumed, not stated: it may read and clobber
    everything (an undeclared external target, a hook, CALSLT's target)."""
    return not o.declared or ((o.inputs & REAL) == REAL and (o.preserves & REAL) == 0)


# The default for a target outside the code ranges that nothing declared:
# unknown code, so it may read everything and clobber everything.
def external(name, kind, in_ram=False):
    return Opaque(name, kind, inputs=REAL, preserves=0, in_ram=in_ram, declared=False)


class FarCall:
    """An entry (CALSLT, a wrapper of it, a call-back stub) whose real target
    is chosen by registers. At each call site the analysis folds `regs` and
    asks resolve(values) for a list of global targets; a resolved site becomes
    a call of those routines (any of them), followed by `kill` (units the
    entry changes around the call) and reading `gen` (units it reads to find
    the target). FarCall.FALLBACK in the list adds the entry's own declared
    effect as one more alternative (a hook that may still be its boot `ret`).
    An unresolved site stays the entry's declared Opaque (or its code)."""

    FALLBACK = -2     # in a resolve() result: "and also the entry's own declared effect"

    def __init__(self, name, regs, resolve, kill=0, gen=0):
        self.name = name
        self.regs = regs          # e.g. ("IX", "IYH"): pairs or single units
        self.resolve = resolve    # tuple of values (see analysis) -> global addr or None
        self.kill = kill
        self.gen = gen


class Program:
    def __init__(self, name):
        self.name = name
        self.images = []          # (lo, bytes, name)
        self.code_ranges = []     # (lo, hi) inclusive
        self.roots = {}           # addr -> name (candidate roots; may be data)
        self.labels = {}          # addr -> [names] for display
        self.interrupt_entries = {}   # addr -> name; analysed with "everything live" after
        self.opaque = {}          # addr -> Opaque  (exact entry addresses)
        self.opaque_ranges = []   # (lo, hi, Opaque factory(addr) -> Opaque)
        self.declared_inline = {}  # addr -> n  (program's own claim, cross-checked)
        self.classifier = None    # addr -> category string for external targets
        self.far_call_groups = {}  # addr -> group name ('sub-ROM', 'disk', ...) for counting
        self.boundaries = set()   # addrs known to start an instruction or a datum
        self.ram_ranges = []      # (lo, hi) inclusive: writable memory (no code image)
        self.far_target_regs = {}  # addr -> pair ('IX'): a call to addr carries its real
                                   # (far) target in that register pair
        self.annotations = None   # annotate.Annotations, or None
        self.contexts = {0: "main"}   # context id -> name (see read)
        self.ctx_pages = {}       # context id -> {page: (bytes, offset, name) | "shared"}
        self.far_calls = {}       # addr -> FarCall: an entry whose real target is resolved per site
        self.notes = []

    # -- bytes -------------------------------------------------------------
    # Addresses are GLOBAL: (context << 16) | the 16-bit Z80 address. Context
    # 0 is the flat map built with add_image. A program whose code runs under
    # more than one memory map (another slot paged in) adds a context per map
    # with add_context; each 16 KB page of it either shows an image of its own
    # or is "shared" with context 0 (then its bytes, and the boundaries and
    # names declared there, are context 0's). Code is analysed per context:
    # the same bytes in two contexts are two routines, because what their
    # calls reach differs.
    def add_image(self, lo, data, name):
        self.images.append((lo, bytes(data), name))

    def add_context(self, cid, name, pages):
        """pages: {page 0..3: (bytes, offset into them, image name) or "shared"};
        a page not listed reads as nothing."""
        self.contexts[cid] = name
        self.ctx_pages[cid] = dict(pages)

    def _read0(self, a):
        for lo, data, _ in self.images:
            if lo <= a < lo + len(data):
                return data[a - lo]
        return None

    def read(self, a):
        ctx, x = a >> 16, a & 0xFFFF
        if ctx == 0:
            return self._read0(x)
        pg = self.ctx_pages.get(ctx, {}).get(x >> 14)
        if pg is None:
            return None
        if pg == "shared":
            return self._read0(x)
        data, off, _ = pg
        i = off + (x & 0x3FFF)
        return data[i] if i < len(data) else None

    def equiv(self, a):
        """The context-0 address showing the same bytes as global a, or None
        when a's page is the context's own."""
        ctx, x = a >> 16, a & 0xFFFF
        if ctx == 0:
            return a
        if self.ctx_pages.get(ctx, {}).get(x >> 14, "shared") == "shared":
            return x
        return None

    def fmt(self, a):
        ctx, x = a >> 16, a & 0xFFFF
        return f"${x:04X}" if ctx == 0 else f"{self.contexts.get(ctx, ctx)}:${x:04X}"

    def in_code(self, a):
        for lo, hi in self.code_ranges:
            if lo <= a <= hi:
                return True
        return False

    # -- names -------------------------------------------------------------
    def add_label(self, addr, name):
        self.labels.setdefault(addr, []).append(name)
        self.__dict__.pop("_byname", None)
        self.__dict__.pop("_sorted", None)

    def name_of(self, a):
        """Nearest label at or below a (same context), as name+offset; for a
        page shared with context 0, context 0's name @ this context."""
        if not hasattr(self, "_sorted"):
            self._sorted = sorted(self.labels)
        import bisect
        i = bisect.bisect_right(self._sorted, a) - 1
        if i >= 0:
            base = self._sorted[i]
            off = a - base
            if base >> 16 == a >> 16 and off <= 0x400:
                n = self.labels[base][0]
                return n if off == 0 else f"{n}+{off}"
        e = self.equiv(a)
        if e is not None and e != a:
            return f"{self.name_of(e)}@{self.contexts.get(a >> 16)}"
        return self.fmt(a)

    def exact_name(self, a):
        names = self.labels.get(a)
        if names:
            return names[0]
        e = self.equiv(a)
        if e is not None and e != a and self.labels.get(e):
            return f"{self.labels[e][0]}@{self.contexts.get(a >> 16)}"
        return self.fmt(a)

    def is_ram(self, a):
        x = a & 0xFFFF
        return any(lo <= x <= hi for lo, hi in self.ram_ranges)

    def resolve(self, text):
        """`name`, `name+N`, `name-N`, `$hex` or `0x..` -> address (None if unknown)."""
        if not hasattr(self, "_byname"):
            self._byname = {}
            for a, ns in self.labels.items():
                for n in ns:
                    self._byname.setdefault(n, a)
            for n, a in getattr(self, "byname", {}).items():
                self._byname.setdefault(n, a)
        t = text.strip()
        ctx = None
        if ":" in t:
            cn, t = t.split(":", 1)
            ids = [c for c, n in self.contexts.items() if n == cn]
            if not ids:
                return None
            ctx = ids[0]
        off = 0
        for sep in ("+", "-"):
            i = t.rfind(sep)
            if i > 0:
                try:
                    off = int(t[i + 1:], 0) * (1 if sep == "+" else -1)
                    t = t[:i]
                    break
                except ValueError:
                    pass
        if t.startswith("$"):
            base = int(t[1:], 16) | (ctx or 0) << 16
        elif t.lower().startswith("0x"):
            base = int(t, 16) | (ctx or 0) << 16
        elif ctx is not None:
            base = next((a for a, ns in self.labels.items() if a >> 16 == ctx and t in ns), None)
            if base is None:
                return None
        else:
            base = self._byname.get(t)
            if base is None:
                return None
        return base + off

    def classify(self, a):
        e = self.equiv(a)
        if e is None:
            return f"{self.contexts.get(a >> 16)}-external"
        if self.classifier:
            return self.classifier(e)
        return "external"

    def opaque_at(self, a):
        if a in self.opaque:
            return self.opaque[a]
        e = self.equiv(a)
        if e is None:
            return None
        if e in self.opaque:
            return self.opaque[e]
        for lo, hi, fac in self.opaque_ranges:
            if lo <= e <= hi:
                return fac(e)
        return None


def load_pasmo_sym(path):
    """`name  EQU 01234H` lines -> list of (name, value). Assembler format, not platform."""
    out = []
    with open(path) as f:
        for line in f:
            p = line.split()
            if len(p) >= 3 and p[1].upper() == "EQU":
                v = p[2].rstrip("Hh")
                try:
                    out.append((p[0], int(v, 16)))
                except ValueError:
                    pass
    return out


__all__ = ["FarCall", "Opaque", "Program", "coarse", "external", "load_pasmo_sym", "U"]
