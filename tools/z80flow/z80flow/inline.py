# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Annotations written in the assembly source, next to the code they describe.

A marker is a comment `; z80flow: KIND ARGS` (the kinds and arguments of
annotate.py, without the WHERE: the marker's line is the WHERE). It goes

  - on an instruction's line: the site is that instruction;
  - on a comment-only line: the site is the next line below that is not a
    comment (an instruction, or a label for a routine annotation);
  - on an `equ` line, for a cell annotation (`stack-anchor`): the cell is the
    name that line defines.

Its justification is the comment block directly above the line (comment-only
lines; other markers are skipped) plus any text before `z80flow:` in the
marker's own comment; it is required, as in an annotation file.

Where a marker lands: the nearest label above it in the same file, plus the
sizes of the instructions in between, decoded from the built image. Every
instruction from the label to the site must decode as the mnemonic its source
line names, and nothing that emits bytes some other way (db / ds / an include
/ IF) may sit in between -- otherwise the marker is an error ("put a label
closer"), never a guess. So a marker cannot silently drift onto other code:
it moves with its line.

A source file included in several images (zerobas: main, the sub-ROMs, the
disk ROM) has its markers applied in each image that defines the label; a
name in the arguments is qualified with the context of the image it is
resolved in (`subp0:name`) when it is that image's own code.

Assembler: pasmo syntax (labels at column 0, `;` comments, `include "x"`).
"""
import os
import re

from . import annotate
from .decode import decode

MARK = re.compile(r"\bz80flow:")

MNEMONICS = set("""
adc add and bit call ccf cp cpd cpdr cpi cpir cpl daa dec di djnz ei ex exx
halt im in inc ind indr ini inir jp jr ld ldd lddr ldi ldir neg nop or otdr
otir out outd outi pop push res ret reti retn rl rla rlc rlca rld rr rra rrc
rrca rrd rst sbc scf set sla sll sra srl sub xor
""".split())


class Image:
    """One assembled image: its top source, include dirs, symbols, and how a
    16-bit address of it maps to an analysis context."""

    def __init__(self, name, top, incdirs, syms, ctx_of, ctx_name, own=None):
        self.name = name
        self.top = top                  # path relative to the source root
        self.incdirs = incdirs          # extra include dirs, relative to the root
        self.syms = syms                # name -> value
        self.ctx_of = ctx_of            # value -> context id, or None (not code of this image)
        self.ctx_name = ctx_name        # context id -> prefix ('' for the main context)
        self.own = own or (lambda n, v: True)   # is name n (= v) this image's own code?


def split_comment(line):
    """(code, comment) of a pasmo line; a `;` inside quotes is not a comment."""
    q = None
    for i, c in enumerate(line):
        if q:
            if c == q:
                q = None
        elif c in "\"'":
            # `af'` is a register, not a quote
            if c == "'" and line[max(0, i - 2):i].lower() == "af":
                continue
            q = c
        elif c == ";":
            return line[:i], line[i + 1:]
    return line, None


def parse_code(code):
    """(label, first word lower-case, rest) of a code part."""
    label = None
    s = code
    if s and not s[0].isspace():
        m = re.match(r"([A-Za-z_.][\w.]*):?", s)
        if m:
            label = m.group(1)
            s = s[m.end():]
    t = s.split(None, 1)
    if not t:
        return label, None, ""
    return label, t[0].lower(), t[1].strip() if len(t) > 1 else ""


def _read_file(root, rel):
    try:
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None


def includes(root, img, read=_read_file):
    """The image's source files, in include order (paths relative to root)."""
    out, seen = [], set()

    def visit(rel):
        if rel in seen:
            return
        seen.add(rel)
        out.append(rel)
        text = read(root, rel)
        if text is None:
            return
        for raw in text.split("\n"):
            code, _ = split_comment(raw)
            _, w, rest = parse_code(code)
            if w == "include":
                f = rest.strip().strip("\"'")
                for d in [os.path.dirname(rel)] + list(img.incdirs) + [""]:
                    cand = os.path.normpath(os.path.join(d, f))
                    if read(root, cand) is not None:
                        visit(cand)
                        break
    visit(img.top)
    return out


def markers(text):
    """Markers of one comment: [(kind, [args])]; several on one line are
    separated by `z80flow:` again."""
    parts = MARK.split(text)[1:]
    out = []
    for p in parts:
        t = p.split()
        if t:
            out.append((t[0], t[1:]))
    return out


def why_before(comment):
    """Comment text before the first `z80flow:` (the marker's own words)."""
    return MARK.split(comment, 1)[0].strip(" \t;-:")


class FileScan:
    """Markers of one file, with the anchor (label, instruction lines) of each."""

    def __init__(self, path, text):
        self.path = path
        self.items = []         # (line, anchor label, [(line, mnemonic)] to the site, kinds, why, equ-name)
        self.errors = []
        lines = text.split("\n")
        anchor = None           # (label, [(line, mnemonic)]) or None after an opaque line
        block = []              # comment-only lines directly above
        waiting = []            # markers on comment-only lines, for the next code line
        for ln, raw in enumerate(lines, 1):
            code, com = split_comment(raw)
            label, w, rest = parse_code(code)
            is_code = label is not None or w is not None
            if not is_code:
                if com is None or not com.strip():
                    if waiting:
                        self.errors.append((f"{path}:{waiting[0][0]}", "marker with no code line below it"))
                        waiting = []
                    block = []
                    continue
                ms = markers(com)
                if ms:
                    why = " ".join(block + [why_before(com)]).strip()
                    if not why and waiting and waiting[-1][0] == ln - 1:
                        why = waiting[-1][2]    # markers directly below one another share it
                    waiting.append((ln, ms, why))
                    block = []
                else:
                    block.append(com.strip())
                continue
            equ = None
            if w == "equ" or (rest.lower().startswith("equ ") and label is None):
                equ = label
            elif label is not None:
                anchor = (label, [])
            if w is not None and w != "equ":
                if w in MNEMONICS:
                    if anchor is not None:
                        anchor[1].append((ln, w))
                else:           # db / ds / include / IF / anything else: lose the anchor
                    anchor = None
            here = []
            for wl, ms, why in waiting:
                here.append((wl, ms, why))
            waiting = []
            if com is not None and markers(com):
                here.append((ln, markers(com), " ".join(block + [why_before(com)]).strip()))
            for wl, ms, why in here:
                if equ is not None:
                    self.items.append((wl, None, None, ms, why, equ))
                elif anchor is None:
                    self.errors.append((f"{path}:{wl}", "no label above this marker in reach "
                                        "(a db/ds/include/IF sits in between): put a label closer"))
                else:
                    # the instruction lines from the anchor up to and including the site
                    # (a label-only line: the site is the next instruction)
                    self.items.append((wl, anchor[0], list(anchor[1]), ms, why, None))
            block = []


def _qualify(tok, img, prog):
    """A bare name (or name+N) that is this image's own code -> ctx:name."""
    m_ = re.fullmatch(r"([A-Za-z_.][\w.]*)([+-]\d+)?", tok)
    if not m_ or tok.lower() == "external":
        return tok
    v = img.syms.get(m_.group(1))
    if v is None or not img.own(m_.group(1), v):
        return tok
    c = img.ctx_of(v)
    if c is None or not img.ctx_name(c):
        return tok
    return f"{img.ctx_name(c)}:{tok}"


def _qual_args(args, img, prog):
    out = []
    for a in args:
        if "=" in a:
            k, v = a.split("=", 1)
            if k == "in":
                out.append("in=" + ",".join(_qualify(x, img, prog) for x in v.split(",")))
            else:
                out.append(a)
        else:
            out.append(_qualify(a, img, prog))
    return out


def resolve(root, images, prog, A, read=_read_file):
    """Find every marker in the images' sources and add it to Annotations A."""
    scans = {}
    seen = set()            # (kind, address, args): a cell or shared file seen from several images
    found = {}              # (path, line) -> resolved in some image
    for img in images:
        for rel in includes(root, img, read):
            if rel not in scans:
                text = read(root, rel)
                if text is None:
                    continue
                scans[rel] = FileScan(rel, text) if MARK.search(text) else None
            fs = scans[rel]
            if fs is None:
                continue
            for wl, label, ilines, ms, why, equ in fs.items:
                key = (rel, wl)
                found.setdefault(key, False)
                if equ is not None:
                    where = equ
                    if equ not in img.syms:
                        continue
                    addr = prog.resolve(where)
                else:
                    v = img.syms.get(label)
                    c = None if v is None else img.ctx_of(v)
                    if c is None:
                        continue
                    off, err = _walk(prog, c, v, ilines, rel)
                    if err:
                        A.errors.append((f"{rel}:{wl}", err))
                        found[key] = True
                        continue
                    pre = (img.ctx_name(c) + ":") if img.ctx_name(c) else ""
                    addr = c << 16 | (v + off)
                    where = pre + label + (f"+{off}" if off else "")
                    if prog.resolve(where) != addr:     # a name the analysis does not label
                        where = f"{pre}${v + off:04X}"
                if addr is None:
                    continue
                found[key] = True
                for kind, args in ms:
                    qa = _qual_args(args, img, prog)
                    k = (kind, addr, tuple(qa))
                    if k in seen:
                        continue
                    seen.add(k)
                    annotate.add(A, prog, kind, [where] + qa, why, f"{rel}:{wl}")
    for fs in scans.values():
        if fs is not None:
            A.errors.extend(fs.errors)
    for (rel, wl), ok in sorted(found.items()):
        if not ok:
            A.errors.append((f"{rel}:{wl}", "marker in no analysed image (its label is in no symbol table)"))
    return A


def _walk(prog, ctx, v, ilines, rel):
    """Offset of the last instruction line's address from the label at v, each
    decoded instruction checked against its source mnemonic. ilines: the
    instruction lines from the label to the site; the site is the last one,
    or, when the marker's line had no instruction yet, the next one -- which
    the scan has already appended."""
    def read(a):
        return prog.read(ctx << 16 | a)
    a = v
    for i, (ln, w) in enumerate(ilines):
        ins = decode(read, a)
        got = ins.mnem.split()[0].lower() if ins.mnem else "?"
        if got != w:
            return None, (f"{rel}:{ln}: the image has `{ins.mnem}` where the source says `{w}` "
                          f"(source and build out of step, or a construct the scan does not follow)")
        if i == len(ilines) - 1:
            return a - v, None
        a += ins.length
    return 0, None
