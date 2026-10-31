# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Hand annotations: the facts static analysis cannot settle, as DATA.

Core module: Z80-generic. A program adapter points at an annotation file; the
analysis consults it per routine or per SITE (one instruction address), so one
abort path does not make a whole routine -- and every caller -- unknown.

File format: one annotation per line, `KIND WHERE ARGS...`. `#` starts a
comment. A location in another address context than the main one is written
`context:name` or `context:$hex` (e.g. `subp0:dde_tail`); an annotation on
main code also applies wherever another context shares that code's page.
The comment block directly above an annotation is its justification
and is required (an annotation without one is reported); annotation lines
directly below one another share the block above the first. WHERE and address
arguments are `name`, `name+N`, `name-N` or `$hex`.

Routine annotations (WHERE = a routine entry):
  noreturn R                  calls to R never come back (R's own returns, if
                              the tool sees any, are a reported mismatch)
  stack-effect R N            R returns with SP changed by N bytes for its
                              caller (+N: it leaves N bytes pushed; -N: it
                              consumed N bytes of the caller's frame; `var`:
                              a data-dependent amount, so callers continue at
                              an unknown depth). Checked against every return
                              the tool can follow; used where it cannot (a
                              return at an unknown depth)
  same-as-callee R T          R's contract is T's (R's body is not analysed
                              for its contract; it is still decoded)
  inline R                    analyse R inside each routine that calls or
                              jumps to it (a call pushes its return address
                              as a constant, R's `ret` comes back through it):
                              context sensitivity for a small shared
                              dispatcher, so `in=` below can tell its callers
                              apart. R's own standalone status is `inlined`

Site annotations (WHERE = an instruction address):
  abort S [reads=REGS] [unwind]
                              the path ends at S and never comes back to this
                              routine's caller (an error exit the tool cannot
                              follow). REGS: what the abort target reads
                              (default: everything, or, for a static target,
                              what that target reads). `unwind`: it abandons
                              whatever was running (see stack-anchor)
  depth S N                   the stack depth (bytes pushed since the routine's
                              entry) is N when S executes; for a conditional
                              ret / jp the assertion is for the TAKEN edge only.
                              N >= 0 also asserts the return-address slot is
                              intact. Checked where the tool knows the depth
  returns-to-callers-caller S the ret at S returns to the caller's caller
                              (sugar for `depth S -2` on a return)
  return S                    the jp (rr) at S is a return to RA+0 (the return
                              address went through memory, so the tool lost
                              it). The stack delta is depth+2 where the tool
                              knows the depth, else the routine's declared
                              stack-effect
  values S PAIR ADDR N [stride=K] [offset=O] hi=H
                              when S executes, PAIR (HL, DE, BC, IX, IY) holds
                              H*256 + one of the N bytes at ADDR+O,
                              ADDR+O+K, ... (a value picked from a table by
                              a search loop the tool does not unroll)
  call-never-returns S        the call at S never comes back to S+3 (the callee
                              can, but not from here: e.g. an error check
                              called right after the error was set). The
                              callee's other exits (to the caller's caller)
                              still count
  ld-sp S N|same              the `ld sp,...` at S leaves the depth at N (a
                              frame release: N = 0 also asserts the return
                              address is on top), or `same`: the stack was
                              moved whole, depth and contents unchanged
  targets S T1 T2 ... [in=R,..]
                              the jp (rr) / computed ret at S goes to one of
                              T1.. (on a `call`: the call reaches one of them
                              instead of its static target, e.g. code loaded
                              into RAM); each a tail jump; `external` = code
                              outside every image, e.g. user machine code in
                              RAM: a declared boundary that may read and
                              clobber everything; `reads=REGS` narrows what it
                              reads to its documented interface (it may still
                              clobber everything). Several targets/table
                              lines for one site add up (a shared dispatcher);
                              `in=` limits a line to the analysis of the named
                              routines (those whose code, inlined or not,
                              contains S). Every site kind takes `in=`
  table S ADDR N [stride=K] [offset=O] [inplace] [in=R,..]
                              as targets: N little-endian words at
                              ADDR+O, ADDR+O+K, ... (default stride 2, offset 0);
                              `inplace`: the entries themselves are the
                              targets (a table of `jp` instructions)

Cell annotations (WHERE = a RAM cell):
  stack-anchor C [unwind]     C always holds an SP saved by `ld (C),sp` at a
                              routine's entry depth; its other writes move it
                              with the stack (a relocation), so a reset `ld
                              sp,(C)` lands in that routine's frame. (Without
                              other writes the tool finds this on its own.)
                              Checked: every `ld (C),sp` is at depth 0.
                              `unwind`: a reset through C abandons whatever
                              was running (an error, a restart); the
                              normal-path view (Analysis.normal_view) leaves
                              out what is read after one
"""
import re

from .decode import ALLF, REAL, U, m

ROUTINE_KINDS = {"noreturn", "stack-effect", "same-as-callee", "inline"}
SITE_KINDS = {"abort", "depth", "returns-to-callers-caller", "targets", "table", "return", "ld-sp",
              "call-never-returns", "values"}
CELL_KINDS = {"stack-anchor"}


def parse_regs(text):
    """`A,E,HL,F,IX` -> unit mask ('-' or '' -> 0)."""
    mk = 0
    for t in re.split(r"[,\s]+", text.strip()):
        if not t or t == "-":
            continue
        T = t.upper()
        if T in ("BC", "DE", "HL"):
            mk |= m(T[0], T[1])
        elif T in ("IX", "IY"):
            mk |= m(T + "H", T + "L")
        elif T == "AF":
            mk |= m("A") | ALLF
        elif T == "F":
            mk |= ALLF
        elif T == "ALL":
            mk |= REAL
        elif T in U:
            mk |= m(T)
        else:
            raise ValueError(f"unknown register {t!r}")
    return mk


class Entry:
    def __init__(self, kind, where, addr, args, why, line):
        self.kind = kind
        self.where = where
        self.addr = addr
        self.args = args
        self.why = why
        self.line = line
        self.used = set()        # routines whose analysis applied it
        self.checks = []         # (verdict 'agree'|'mismatch'|'sane', detail)
        self.value = None        # parsed argument (N, mask, target list, ...)
        self.only = None         # `in=`: routines this site annotation applies to

    def check(self, ok, detail, weak=False):
        """Record a comparison with the analysis. weak: a sanity check (the
        site is the right kind of instruction) that can fail the annotation
        but does not by itself make it `checked`."""
        v = ("mismatch" if not ok else ("sane" if weak else "agree"), detail)
        if v not in self.checks:
            self.checks.append(v)

    def verdict(self):
        if any(c[0] == "mismatch" for c in self.checks):
            return "MISMATCH"
        if any(c[0] == "agree" for c in self.checks):
            return "checked"
        return "trusted" if self.used else "unused"


class Annotations:
    def __init__(self):
        self.entries = []
        self.errors = []          # (line, message)
        self.noreturn = {}        # routine -> Entry
        self.stack_effect = {}    # routine -> Entry (value = N)
        self.same_as = {}         # routine -> Entry (value = target)
        self.abort = {}           # site -> [Entry] (value = mask or None)
        self.depth = {}           # site -> [Entry] (value = N)
        self.targets = {}         # site -> [Entry] (value = [targets]; several tables may share a site)
        self.returns = {}         # site -> [Entry]
        self.ldsp = {}            # site -> [Entry] (value = N or None for `same`)
        self.call_noret = {}      # site -> [Entry]
        self.values = {}          # site -> [Entry] (value = (pair, [16-bit values]))
        self.inline = {}          # routine -> Entry
        self.anchor = {}          # RAM cell (16-bit) -> Entry

    # An analysis may see one address under several names (the same main-ROM
    # bytes in another slot context, an inlined copy): it sets canon to map
    # them to the address the annotation file names.
    canon = staticmethod(lambda a: a)

    def r(self, table, a):
        """A routine-level annotation for routine a, or None."""
        return table.get(self.canon(a)) if a is not None else None

    def pick(self, table, a, routine):
        """The first annotation for site a that applies while analysing routine."""
        rc = None if routine is None else self.canon(routine)
        for e in table.get(self.canon(a), ()):
            if e.only is None or rc is None or rc in e.only:
                return e
        return None

    def site_targets(self, a, routine=None):
        """(entries, sorted union of targets) for a dispatch site as seen while
        analysing `routine` (None: every line), or (None, None)."""
        rc = None if routine is None else self.canon(routine)
        es = [e for e in self.targets.get(self.canon(a), ()) if rc is None or e.only is None or rc in e.only]
        if not es:
            return None, None
        ts = set()
        for e in es:
            ts.update(e.value)
        return es, sorted(ts)

    def dispatch_targets(self):
        out = set()
        for es in self.targets.values():
            for e in es:
                out.update(t for t in e.value if not is_external(t))
        return out


def load(paths, prog):
    """Parse annotation files against a Program (names resolved via its labels)."""
    A = Annotations()
    for path in paths:
        with open(path) as f:
            loads(f.read(), prog, A, path)
    return A


def loads(text, prog, A=None, source="<text>"):
    A = A if A is not None else Annotations()
    why = []
    after_ann = False
    lines = text.split("\n")
    for ln, raw in enumerate(lines, 1):
        s = raw.strip()
        if not s:
            why = []
            after_ann = False
            continue
        if s.startswith("#"):
            if after_ann:          # a comment after annotations starts a new block
                why = []
                after_ann = False
            why.append(s[1:].strip())
            continue
        after_ann = True           # annotations directly below one another share it
        body = s.split("#", 1)[0].strip()
        p = body.split()
        add(A, prog, p[0], p[1:], " ".join(why), f"{source}:{ln}")
    return A


def add(A, prog, kind, rest, why, ln):
    """One annotation `KIND WHERE ARGS` (rest = [WHERE, ARGS...]) with its
    justification, from location ln (for messages). An annotation file and
    the markers in a source (inline.py) both come here."""
    if kind not in ROUTINE_KINDS | SITE_KINDS | CELL_KINDS:
        A.errors.append((ln, f"unknown kind {kind!r}"))
        return None
    if not rest:
        A.errors.append((ln, f"{kind}: missing location"))
        return None
    addr = prog.resolve(rest[0])
    if addr is None:
        A.errors.append((ln, f"{kind}: unknown location {rest[0]!r}"))
        return None
    e = Entry(kind, rest[0], addr, rest[1:], why, ln)
    if not e.why:
        A.errors.append((ln, f"{kind} {rest[0]}: no justification comment"))
    try:
        _bind(A, e, prog)
    except (ValueError, IndexError) as x:
        A.errors.append((ln, f"{kind} {rest[0]}: {x}"))
        return None
    A.entries.append(e)
    return e


def _addr(prog, t):
    a = prog.resolve(t)
    if a is None:
        raise ValueError(f"unknown location {t!r}")
    return a


EXTERNAL = -1      # the `external` pseudo-target: code in no image, may read anything
EXT_READS = -(1 << 40)   # `external reads=REGS`: EXT_READS - mask


def is_external(t):
    return t == EXTERNAL or t <= EXT_READS


def external_reads(t):
    """The units an external target may read (REAL for a plain `external`)."""
    return REAL if t == EXTERNAL else EXT_READS - t


def _only(prog, e, args):
    rest = []
    for x in args:
        if x.startswith("in="):
            e.only = {_addr(prog, y) for y in x[3:].split(",") if y}
        else:
            rest.append(x)
    return rest


def _bind(A, e, prog):
    k, args = e.kind, e.args
    if k == "noreturn":
        A.noreturn[e.addr] = e
    elif k == "stack-effect":
        e.value = None if args[0] == "var" else int(args[0])
        A.stack_effect[e.addr] = e
    elif k == "inline":
        A.inline[e.addr] = e
    elif k == "stack-anchor":
        for x in args:
            if x != "unwind":
                raise ValueError(f"unknown argument {x!r}")
        e.value = "unwind" in args
        A.anchor[e.addr & 0xFFFF] = e
    elif k == "same-as-callee":
        e.value = _addr(prog, args[0])
        A.same_as[e.addr] = e
    elif k == "abort":
        e.value = None
        e.unwind = False
        for x in _only(prog, e, args):
            if x.startswith("reads="):
                e.value = parse_regs(x[6:])
            elif x == "unwind":
                e.unwind = True
            else:
                raise ValueError(f"unknown argument {x!r}")
        A.abort.setdefault(e.addr, []).append(e)
    elif k == "depth":
        e.value = int(_only(prog, e, args)[0])
        A.depth.setdefault(e.addr, []).append(e)
    elif k == "returns-to-callers-caller":
        _only(prog, e, args)
        e.value = -2
        A.depth.setdefault(e.addr, []).append(e)
    elif k == "return":
        _only(prog, e, args)
        A.returns.setdefault(e.addr, []).append(e)
    elif k == "values":
        args = _only(prog, e, args)
        pair = args[0].upper()
        if pair not in ("BC", "DE", "HL", "IX", "IY"):
            raise ValueError(f"not a register pair: {args[0]}")
        base = _addr(prog, args[1])
        n = int(args[2], 0)
        stride, offset, hi = 1, 0, None
        for x in args[3:]:
            if x.startswith("stride="):
                stride = int(x[7:], 0)
            elif x.startswith("offset="):
                offset = int(x[7:], 0)
            elif x.startswith("hi="):
                hi = int(x[3:].replace("$", "0x"), 0)
            else:
                raise ValueError(f"unknown argument {x!r}")
        if hi is None:
            raise ValueError("values needs hi=")
        vs = []
        for i in range(n):
            b = prog.read(base + offset + i * stride)
            if b is None:
                raise ValueError(f"table byte {i} is outside the image")
            vs.append(hi << 8 | b)
        e.value = (pair, vs)
        A.values.setdefault(e.addr, []).append(e)
    elif k == "call-never-returns":
        _only(prog, e, args)
        A.call_noret.setdefault(e.addr, []).append(e)
    elif k == "ld-sp":
        v = _only(prog, e, args)[0]
        e.value = None if v == "same" else int(v)
        A.ldsp.setdefault(e.addr, []).append(e)
    elif k == "targets":
        args = _only(prog, e, args)
        reads = None
        rest = []
        for x in args:
            if x.startswith("reads="):
                reads = parse_regs(x[6:])
            else:
                rest.append(x)
        if not rest:
            raise ValueError("no targets")
        if reads is not None and "external" not in rest:
            raise ValueError("reads= only qualifies `external`")
        ext = EXTERNAL if reads is None else EXT_READS - reads
        e.value = [ext if x == "external" else _addr(prog, x) for x in rest]
        A.targets.setdefault(e.addr, []).append(e)
    elif k == "table":
        args = _only(prog, e, args)
        base = _addr(prog, args[0])
        n = int(args[1], 0)
        stride, offset = 2, 0
        for x in args[2:]:
            if x.startswith("stride="):
                stride = int(x[7:], 0)
            elif x.startswith("offset="):
                offset = int(x[7:], 0)
            elif x == "inplace":
                pass
            else:
                raise ValueError(f"unknown argument {x!r}")
        ts = []
        ctx = base & ~0xFFFF           # table words point into the table's own context
        if "inplace" in args:          # the entries ARE the code (a table of jp's)
            e.value = [base + offset + i * stride for i in range(n)]
            A.targets.setdefault(e.addr, []).append(e)
            return
        for i in range(n):
            a = base + offset + i * stride
            lo, hi = prog.read(a), prog.read(a + 1)
            if lo is None or hi is None:
                raise ValueError(f"table entry {i} at ${a:04X} is outside the image")
            ts.append(ctx | lo | hi << 8)
        e.value = ts
        A.targets.setdefault(e.addr, []).append(e)
