#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""pin_plan -- plan (and later gate) code bytes PINNED at fixed addresses in the
main BASIC image (D-BASICINT, Joost 2026-10-15: three undocumented BASIC-ROM
entry points that tape games call must exist at the SAME addresses).

A pin is placed by inserting, at some source point P whose address is b,

        ds      PIN - $         ; the pad -- MUST stay ~0
        <pin bytes>             ; at PIN exactly

so everything after P moves up by (PIN - b) + len. Joost's constraint: "We have
to be careful that we do not create growing holes by pinning addresses." The pad
absorbs EVERY size change of the code between the region start and P, in BOTH
directions -- shrink that code and the hole grows silently; grow it past the pin
and the `ds` goes negative. Hence the two modes:

  PLAN (default). For each pin: the split points b <= PIN where the instruction
  ending at b is an UNCONDITIONAL transfer (nothing falls through into the pad),
  ranked by gap = PIN - b, with the source file:line to insert after; a "jr
  bridge" fallback (`jr` over the pin from any instruction boundary); and REFILL
  candidates -- self-contained chunks that could be moved into the pad.

  --check. The gate: on a BUILT image, verify the expected bytes sit at each pin.
  Exit 1 when one does not; exit 2 when the built ROM is not what the current
  sources assemble to (stale build). The pad directly in front of each pin is
  REPORTED, split into FREE bytes (`ds`/org gap) and `jr` BRIDGE bytes; it is no
  longer a failure (Joost 2026-10-20: "I don't think we have to fill holes before
  pins exactly every time, but we do need to consider them free space we probably
  want to use again eventually"). --budget N restores the old limit on the total.

  --holes. The same measurement as two `measure:` lines for `make basic-reloc`'s
  wall readout -- free bytes in front of the pins, per region and per hole -- so a
  pad is counted as free space instead of disappearing behind a pin.

WHERE THE INSTRUCTION BOUNDARIES COME FROM. `pasmo -d` prints, for every pass,
a listing of every emitted item: `ADDR:HEX<TAB>MNEMONIC`, `ADDR:<TAB>label X`,
`DEFB/DEFW/DEFS of N bytes`, INCLUDE / End of INCLUDE nesting, and the source
text of lines skipped by a false IF (prefixed `-`). The LAST pass is the one
whose bytes are emitted, so the boundaries are the assembler's own -- exact, and
code vs data is known from the source directive, not guessed. The binary pasmo
writes alongside is compared byte-for-byte with the listing's addresses. Nothing
here disassembles anything but zerobas's own sources.

The one thing the listing does NOT print is a source line number per item; this
tool recovers it by aligning each included file's lines against that file's
items in order (labels, mnemonics, skipped `-` lines). The coverage of that
alignment is printed; an unmapped item falls back to its label's line.

HAZARDS CHECKED per split point: a 1-byte `db <opcode>` skip trick just before
the transfer that would SWALLOW it (then execution falls through after all);
`jr`/`djnz` whose span crosses P and would overflow +/-128 once P grows by
gap+len; labels inside [b, PIN+len) (they move -- harmless for `jp`/`call`, the
jr check covers the rest); a file that sub/, sub2/ or disk/ ALSO include (a pad
there would be assembled into that ROM too). NOT checked: the tree's own
`if ... db ERROR_NAME endif` layout assertions -- a re-assembly runs them.

    python3 tools/pin_plan.py                      # plan for the PINS table
    python3 tools/pin_plan.py --pin 0x3297:E1C9    # plan one ad-hoc pin
    python3 tools/pin_plan.py --check [--rom build/basic-reloc.rom] [--budget N]
    python3 tools/pin_plan.py --holes [--rom build/basic-reloc.rom]
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import probe_tmp                       # noqa: E402,F401 -- sets tempfile.tempdir [[one-temp-root]]

# ---------------------------------------------------------------------------
# THE PIN LIST. expect = exact bytes, or "jp" (C3 + a target inside the main
# image; `target` names the symbol it must reach once the slice exists).
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Pin:
    addr: int
    length: int
    expect: object          # bytes | "jp"
    target: str | None
    note: str


PINS = [
    Pin(0x3297, 2, bytes([0xE1, 0xC9]), None, "D-BASICINT pop hl / ret"),
    Pin(0x6CF3, 3, "jp", "lh_back", "D-BASICINT BLOAD,R continuation: jp lh_back"),
    # $73AC IS the RUN entry's body (basic/field.asm basicint_run), not a `jp` to
    # it: the 8 bytes checked are its address-free head -- ld hl,(VARTAB $F6C2) /
    # dec hl / dec hl / ld (PRGEND $F6E8),hl; the `jp run_prog_top` after them moves.
    # $72D4 / $72E9 are the D-BASICINT2 tape bodies (basic/field.asm): the 6 bytes
    # checked are their address-free head -- push bc / push de / push hl / call
    # TAPIN ($00E4) or TAPION ($00E1); the `jp c,dpl_dio` after them moves.
    Pin(0x72D4, 6, bytes.fromhex("C5D5E5CDE400"), None, "D-BASICINT2 tape byte read: TAPIN, ERR 19"),
    Pin(0x72E9, 6, bytes.fromhex("C5D5E5CDE100"), None, "D-BASICINT2 tape start: TAPION, ERR 19"),
    Pin(0x73AC, 8, bytes.fromhex("2AC2F62B2B22E8F6"), None,
        "D-BASICINT RUN entry: PRGEND := VARTAB - 2, then run_prog_top"),
    Pin(0x73E5, 3, "jp", "basicint_play", "D-AVTAK PLAY body: jp basicint_play (call pl_args, return)"),
]

SRC = "basic/main.asm"
BASE, TOP = 0x2781, 0x8000
REGIONS = (("low", 0x2781, 0x4000, "__MEAS_LOW_END"),
           ("page1", 0x4000, 0x8000, "__MEAS_PAGE1_END"))
SHARING_TREES = ("sub", "sub2", "disk")

# ---------------------------------------------------------------------------
# Z80 helpers (only for OUR bytes: transfer opcodes and the db-skip check)
# ---------------------------------------------------------------------------
JR_OPS = {0x18, 0x20, 0x28, 0x30, 0x38, 0x10}      # jr, jr cc, djnz


def is_uncond_transfer(b: bytes) -> bool:
    if not b:
        return False
    o = b[0]
    if o in (0xC9, 0xC3, 0x18, 0xE9):               # ret, jp nn, jr e, jp (hl)
        return True
    if o in (0xDD, 0xFD) and len(b) >= 2 and b[1] == 0xE9:   # jp (ix)/(iy)
        return True
    if o == 0xED and len(b) >= 2 and b[1] in (0x45, 0x4D):   # retn, reti
        return True
    return False


def z80_len(o: int, o2: int = 0) -> int:
    """Length of an instruction starting with opcode o (conservative for DD/FD)."""
    if o == 0xCB:
        return 2
    if o == 0xED:
        return 4 if o2 in (0x43, 0x4B, 0x53, 0x5B, 0x63, 0x6B, 0x73, 0x7B) else 2
    if o in (0xDD, 0xFD):
        return 4
    if o in (0x01, 0x11, 0x21, 0x31, 0x22, 0x2A, 0x32, 0x3A) or \
            (o & 0xC7) in (0xC2, 0xC4) or o in (0xC3, 0xCD):
        return 3
    if (o & 0xC7) == 0x06 or (o & 0xC7) == 0xC6 or o in JR_OPS or o in (0xD3, 0xDB):
        return 2
    return 1


# ---------------------------------------------------------------------------
# The listing
# ---------------------------------------------------------------------------
@dataclass
class Item:
    kind: str               # label instr data include endinc skip dir other
    file: str
    inst: int               # which inclusion of `file` this item belongs to
    text: str
    addr: int | None = None
    hexb: bytes = b""
    size: int = 0
    line: int | None = None  # 1-based source line, once aligned
    name: str = ""


ADDR_RE = re.compile(r"^([0-9A-F]{4}):([0-9A-F]*)\s*(.*)$")


def run_pasmo(tmpdir: str) -> tuple[list[str], bytes]:
    full = os.path.join(tmpdir, "full.bin")
    sym = os.path.join(tmpdir, "full.sym")
    p = subprocess.run(["pasmo", "-d", "--bin", SRC, full, sym], cwd=ROOT,
                       capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"pin_plan: pasmo -d failed (rc {p.returncode}):\n{p.stderr[-2000:]}")
    return p.stdout.splitlines(), open(full, "rb").read()


def last_pass(lines: list[str]) -> list[str]:
    first = next(i for i, ln in enumerate(lines) if not ln.startswith("WARNING"))
    starts = [i for i, ln in enumerate(lines) if ln == lines[first]]
    out = lines[starts[-1]:]
    if len(starts) < 2:
        sys.exit("pin_plan: could not find pass boundaries in the pasmo -d listing")
    return out


def parse_listing(lines: list[str]) -> list[Item]:
    stack = [SRC]
    seen: dict[str, int] = {SRC: 0}
    insts = [0]
    items: list[Item] = []
    cur: Item | None = None
    for ln in lines:
        if ln.startswith("WARNING"):
            continue
        m = ADDR_RE.match(ln)
        f, k = stack[-1], insts[-1]
        if m:
            addr = int(m.group(1), 16)
            hx, rest = m.group(2), m.group(3).strip()
            if rest.startswith("label "):
                items.append(Item("label", f, k, rest, addr, name=rest[6:].strip()))
                continue
            if rest == "":
                continue                      # continuation of a DEFB/DEFS dump
            kind = "data" if re.match(r"DEF[BWSM]\b", rest) else "instr"
            cur = Item(kind, f, k, rest, addr, bytes.fromhex(hx))
            items.append(cur)
            continue
        s = ln.strip()
        if s.startswith("INCLUDE "):
            path = s[8:].strip().strip('"')
            items.append(Item("include", f, k, s, name=path))
            seen[path] = seen.get(path, -1) + 1
            stack.append(path)
            insts.append(seen[path])
        elif s == "End of INCLUDE":
            stack.pop()
            insts.pop()
        elif ln.startswith("-"):
            items.append(Item("skip", f, k, ln[1:].strip()))
        elif re.match(r"(IF|ELSE|ENDIF|ORG)\b", s):
            items.append(Item("dir", f, k, s))
        elif s:
            items.append(Item("other", f, k, s))
    return items


def size_items(items: list[Item], full: bytes) -> list[Item]:
    """Byte items inside the relocated image, in address order, sized by the
    next item's address (exact for DEFB/DEFS whose dump the listing truncates)."""
    image_base = TOP - len(full)
    byte_items = [it for it in items if it.kind in ("instr", "data") and it.addr is not None
                  and BASE <= it.addr < TOP]
    # stop at the first backwards jump in address (the islands' org at the end)
    out: list[Item] = []
    for it in byte_items:
        if out and it.addr < out[-1].addr:
            break
        out.append(it)
    for a, b in zip(out, out[1:]):
        a.size = b.addr - a.addr
    out[-1].size = TOP - out[-1].addr if out[-1].kind == "data" else len(out[-1].hexb)
    bad = 0
    for it in out:
        if it.kind == "instr" and len(it.hexb) != it.size:
            bad += 1
        img = full[it.addr - image_base: it.addr - image_base + len(it.hexb)]
        if it.hexb and img != it.hexb[:len(img)]:
            sys.exit(f"pin_plan: listing bytes at ${it.addr:04X} disagree with pasmo's binary")
    if bad:
        print(f"note: {bad} instruction(s) whose listed length != address delta "
              f"(org/ds between them)")
    return out


# ---------------------------------------------------------------------------
# Source-line alignment
# ---------------------------------------------------------------------------
OPMAP = {"DB": "DEFB", "DEFM": "DEFB", "DM": "DEFB", "DW": "DEFW", "DS": "DEFS"}
DIRECTIVES = {"IF", "ELSE", "ENDIF", "ORG", "INCLUDE", "EQU", "DEFL", "END", "PUBLIC"}


def strip_comment(s: str) -> str:
    q = None
    for i, c in enumerate(s):
        if q:
            if c == q:
                q = None
        elif c in "\"'":
            # af' is not a quote
            if c == "'" and i > 0 and s[i - 1].isalpha():
                continue
            q = c
        elif c == ";":
            return s[:i]
    return s


def src_keys(raw: str) -> list[tuple[str, str]]:
    s = strip_comment(raw).rstrip()
    if not s.strip():
        return []
    keys = []
    m = re.match(r"^([A-Za-z_.@?$][\w.@?$]*):", s)
    if m:
        keys.append(("label", m.group(1)))
        s = s[m.end():]
    elif s[0] not in " \t":
        w = re.match(r"^([A-Za-z_.@?$][\w.@?$]*)\s*(.*)$", s)
        if w and w.group(2).split()[:1] and w.group(2).split()[0].upper() in ("EQU", "DEFL"):
            return [("other", "")]
        if w and w.group(1).upper() not in OPMAP and not re.match(r"[A-Za-z]+$", w.group(1)):
            keys.append(("label", w.group(1)))
            s = w.group(2)
    s = s.strip()
    if s:
        word = re.match(r"[A-Za-z]+", s)
        w = word.group(0).upper() if word else ""
        if w in ("EQU", "DEFL"):
            return [("other", "")]
        w = OPMAP.get(w, w)
        if w in ("IF", "ELSE", "ENDIF", "ORG"):
            keys.append(("dir", w))
        elif w == "INCLUDE":
            keys.append(("include", ""))
        else:
            keys.append(("op", w))
    return keys


def item_key(it: Item) -> tuple[str, str]:
    if it.kind == "label":
        return ("label", it.name)
    if it.kind in ("instr", "data"):
        return ("op", re.match(r"[A-Z]+", it.text).group(0))
    if it.kind == "dir":
        return ("dir", re.match(r"[A-Z]+", it.text).group(0))
    if it.kind == "include":
        return ("include", "")
    return (it.kind, it.text)


def align_sources(items: list[Item]) -> tuple[int, int]:
    groups: dict[tuple[str, int], list[Item]] = {}
    for it in items:
        if it.kind in ("other",):
            continue
        groups.setdefault((it.file, it.inst), []).append(it)
    mapped = total = 0
    for (f, _k), its in groups.items():
        try:
            lines = open(os.path.join(ROOT, f), encoding="utf-8", errors="replace").read().splitlines()
        except OSError:
            continue
        p = 0
        WIN = 8
        for ln_no, raw in enumerate(lines, 1):
            if p >= len(its):
                break
            # skipped lines (false IF) match by their verbatim text
            st = raw.strip()
            if its[p].kind == "skip" or any(x.kind == "skip" for x in its[p:p + 2]):
                hit = next((j for j in range(p, min(p + WIN, len(its)))
                            if its[j].kind == "skip" and its[j].text == st), None)
                if hit is not None:
                    its[hit].line = ln_no
                    p = hit + 1
                    continue
            for key in src_keys(raw):
                if key[0] == "other":
                    continue
                hit = next((j for j in range(p, min(p + WIN, len(its)))
                            if item_key(its[j]) == key), None)
                if hit is not None:
                    its[hit].line = ln_no
                    p = hit + 1
        for it in its:
            if it.kind in ("instr", "data") and it.addr is not None and BASE <= it.addr < TOP:
                total += 1
                mapped += it.line is not None
    return mapped, total


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
@dataclass
class Image:
    items: list[Item]                 # every listing item (labels included)
    code: list[Item]                  # byte items, address order
    full: bytes
    labels: dict[int, list[Item]] = field(default_factory=dict)
    sym: dict[str, int] = field(default_factory=dict)
    idx_of: dict[int, int] = field(default_factory=dict)    # addr -> index in code
    falls_out: list[bool] = field(default_factory=list)
    swallowed: list[bool] = field(default_factory=list)
    shared: dict[str, list[str]] = field(default_factory=dict)
    abi: set[str] = field(default_factory=set)      # names a sub/disk ROM calls back

    def byte(self, a: int) -> int:
        return self.full[a - (TOP - len(self.full))]


def load_image() -> Image:
    with tempfile.TemporaryDirectory() as td:
        lines, full = run_pasmo(td)
    items = parse_listing(last_pass(lines))
    code = size_items(items, full)
    im = Image(items, code, full)
    for it in items:
        if it.kind == "label" and it.addr is not None and BASE <= it.addr <= TOP:
            im.sym.setdefault(it.name, it.addr)     # $8000: __MEAS_PAGE1_END
            if it.addr < TOP:
                im.labels.setdefault(it.addr, []).append(it)
    im.idx_of = {it.addr: i for i, it in enumerate(code)}
    # swallow: a 1-byte-ish `db <opcode>` whose decoded length runs INTO this item
    for i, it in enumerate(code):
        sw = False
        for j in range(max(0, i - 3), i):
            d = code[j]
            if d.kind == "data" and d.text.startswith("DEFB") and d.size <= 2:
                o = im.byte(d.addr)
                o2 = im.byte(d.addr + 1) if d.addr + 1 < TOP else 0
                if d.addr + z80_len(o, o2) > it.addr:
                    sw = True
        im.swallowed.append(sw)
    # falls_out[i]: can execution continue from item i into item i+1?
    prev = True
    for i, it in enumerate(code):
        if it.kind == "instr":
            prev = not (is_uncond_transfer(it.hexb) and not im.swallowed[i])
        # data inherits: a table after a transfer is never executed; inline data
        # after a call/db-skip is
        im.falls_out.append(prev)
    for f in ("sub/basic-resident-abi.inc", "disk/basic-resident-abi.inc"):
        try:
            txt = open(os.path.join(ROOT, f), encoding="utf-8").read()
        except OSError:
            continue
        im.abi |= set(re.findall(r"^(\w+)\s+equ\b", txt, re.M | re.I))
    for t in SHARING_TREES:
        for dp, _dn, fns in os.walk(os.path.join(ROOT, t)):
            for fn in fns:
                if not fn.endswith((".asm", ".inc")):
                    continue
                txt = open(os.path.join(dp, fn), encoding="utf-8", errors="replace").read()
                for m in re.finditer(r'^\s*include\s+"(?:\.\./)?(basic/[^"]+)"', txt, re.M | re.I):
                    im.shared.setdefault(m.group(1), []).append(os.path.relpath(os.path.join(dp, fn), ROOT))
    return im


def region_of(a: int):
    for r in REGIONS:
        if r[1] <= a < r[2]:
            return r
    return None


def region_free(im: Image, r) -> int | None:
    a = im.sym.get(r[3])
    return None if a is None else r[2] - a


def where(im: Image, a: int) -> str:
    best = None
    for la in sorted(im.labels):
        if la <= a:
            best = la
        else:
            break
    if best is None:
        return f"${a:04X}"
    names = [x.name for x in im.labels[best]]
    off = a - best
    return f"{names[-1]}+{off}" if off else names[-1]


def loc(it: Item) -> str:
    return f"{it.file}:{it.line}" if it.line else f"{it.file}:?"


def jr_target(it: Item) -> int | None:
    if it.kind == "instr" and it.hexb and it.hexb[0] in JR_OPS and len(it.hexb) == 2:
        d = it.hexb[1]
        return it.addr + 2 + (d - 256 if d > 127 else d)
    return None


def jr_overflows(im: Image, p: int, grow: int) -> list[str]:
    """jr/djnz spanning the insertion point p that no longer reach after +grow."""
    bad = []
    for it in im.code:
        t = jr_target(it)
        if t is None:
            continue
        src, dst = it.addr, t
        if src < p <= dst:
            disp = dst + grow - (src + 2)
        elif dst < p <= src:
            disp = dst - (src + grow + 2)
        else:
            continue
        if not -128 <= disp <= 127:
            bad.append(f"{where(im, src)}->{where(im, dst)} (${src:04X}, new disp {disp})")
    return bad


@dataclass
class Split:
    b: int
    gap: int
    item: Item
    labels_inside: list[str]
    jr_bad: list[str]
    shared: list[str]
    warn: list[str]


def splits_for(im: Image, pin: Pin, shift=None, limit=6, scan=2048) -> list[Split]:
    """Transfer-ended split points b <= PIN in the pin's region, smallest gap first.
    `shift(a)` maps a current address to its address after earlier pins."""
    shift = shift or (lambda a: a)
    r = region_of(pin.addr)
    out = []
    for i, it in enumerate(im.code):
        if it.addr < r[1] or it.addr >= r[2]:
            continue
        if it.kind != "instr" or not is_uncond_transfer(it.hexb) or im.swallowed[i]:
            continue
        b = shift(it.addr) + it.size
        if b > pin.addr or pin.addr - b > scan:
            continue
        gap = pin.addr - b
        cur_b = it.addr + it.size
        inside = [x.name for a in sorted(im.labels) if cur_b <= a < cur_b + gap + pin.length
                  for x in im.labels[a]]
        warn = []
        nxt = im.code[i + 1] if i + 1 < len(im.code) else None
        if nxt is not None and nxt.kind == "instr" and nxt.hexb[:1] == b"\xC3" and it.hexb[:1] == b"\xC3":
            warn.append("between two `jp nn` -- a jp vector table? check it is not indexed")
        if nxt is not None and nxt.kind == "data" and nxt.addr not in im.labels:
            warn.append("followed by unlabelled data -- inline data, check")
        sh = im.shared.get(it.file, [])
        out.append(Split(b, gap, it, inside, jr_overflows(im, cur_b, gap + pin.length), sh, warn))
    out.sort(key=lambda s: s.gap)
    return out[:limit]


def bridge_for(im: Image, pin: Pin, shift=None) -> tuple[int, Item] | None:
    """Fallback: `jr PIN+len` from any instruction boundary b <= PIN-2 inside
    code (not inside a data run, not swallowed). waste = PIN - b (pad + jr)."""
    shift = shift or (lambda a: a)
    best = None
    for i, it in enumerate(im.code):
        if it.kind != "instr" or im.swallowed[i]:
            continue
        b = shift(it.addr) + it.size
        if b > pin.addr - 2:
            continue
        nxt = im.code[i + 1] if i + 1 < len(im.code) else None
        if nxt is None or nxt.kind != "instr":
            continue
        if best is None or b > best[0]:
            best = (b, it)
    return best


@dataclass
class Chunk:
    start: int
    end: int
    kind: str
    first: Item
    jr_links: int
    names: list[str]


def chunks(im: Image) -> list[Chunk]:
    """Self-contained movable units: they start at a label nothing falls into
    and end where nothing falls out of. Inner labels move with them."""
    bounds = []
    for i, it in enumerate(im.code):
        if i == 0:
            continue
        if it.addr in im.labels and not im.falls_out[i - 1]:
            bounds.append(i)
    out = []
    for a, b in zip(bounds, bounds[1:] + [len(im.code)]):
        its = im.code[a:b]
        if region_of(its[0].addr) != region_of(its[-1].addr):
            continue
        if its[-1].kind == "data" and its[-1].text.startswith("DEFS"):
            its = its[:-1]                     # the region's wall pad
            if not its:
                continue
        if im.falls_out[a + len(its) - 1]:
            continue                           # last item falls into the next
        s, e = its[0].addr, its[-1].addr + its[-1].size
        names = [x.name for ad in sorted(im.labels) if s <= ad < e for x in im.labels[ad]]
        if any(n.startswith("__MEAS") for n in names) or s == 0x4000:
            continue                           # wall labels / the "AB" header
        links = 0
        for it in im.code:
            t = jr_target(it)
            if t is not None and ((s <= it.addr < e) != (s <= t < e)):
                links += 1
        kind = "code" if any(x.kind == "instr" for x in its) else "data"
        out.append(Chunk(s, e, kind, its[0], links, names))
    return out


def refills(im: Image, pin: Pin, split: Split, all_chunks: list[Chunk]):
    """Chunks that could be MOVED INTO the pad. Only chunks AFTER P (same region)
    or in the OTHER region reduce it: moving a chunk from before P just grows
    `ds PIN-$` by the same amount."""
    r = region_of(pin.addr)
    p_cur = split.item.addr + split.item.size
    same, other = [], []
    for c in all_chunks:
        sz = c.end - c.start
        if sz > split.gap or c.jr_links:
            continue
        rc = region_of(c.start)
        if rc == r and c.start >= p_cur + split.gap:   # past the code the pad moves
            same.append(c)
        elif rc != r:
            other.append(c)
    key = lambda c: -(c.end - c.start)
    return sorted(same, key=key), sorted(other, key=key)


def exact_fill(cands: list[Chunk], gap: int):
    """Fewest chunks whose sizes sum to exactly gap (else the closest below)."""
    best: dict[int, list[int]] = {0: []}
    for i, c in enumerate(cands[:300]):
        sz = c.end - c.start
        for s in sorted(best, reverse=True):
            t = s + sz
            if t <= gap and (t not in best or len(best[t]) > len(best[s]) + 1):
                best[t] = best[s] + [i]
    top = max(best)
    return top, [cands[i] for i in best[top]]


# ---------------------------------------------------------------------------
# PLAN
# ---------------------------------------------------------------------------
def fmt_chunk(c: Chunk, im: Image) -> str:
    extra = f" (+{len(c.names) - 1} inner labels)" if len(c.names) > 1 else ""
    abi = [n for n in c.names if n in im.abi]
    tag = f"  [resident ABI: {', '.join(abi)}]" if abi else ""
    lab = im.labels.get(c.start, [c.first])[0]
    return f"{c.end - c.start:4d} B  {c.kind:4s} ${c.start:04X} {c.names[0]}{extra}  {loc(lab)}{tag}"


def covering(im: Image, a: int) -> Item | None:
    for it in im.code:
        if it.addr <= a < it.addr + it.size:
            return it
    return None


def plan(im: Image, pins: list[Pin], top: int) -> int:
    mapped, total = align_sources(im.items)
    print(f"boundaries: pasmo -d last pass, {len(im.code)} byte items "
          f"(${im.code[0].addr:04X}-${im.code[-1].addr + im.code[-1].size:04X}); "
          f"source lines aligned for {mapped}/{total} ({100 * mapped / max(total, 1):.1f}%)")
    for r in REGIONS:
        print(f"region {r[0]:5s} ${r[1]:04X}-${r[2] - 1:04X}: free {region_free(im, r)} B "
              f"({r[3]})")
    allc = chunks(im)
    print(f"movable chunks (label-started, no fall-in/out): {len(allc)}, "
          f"{sum(1 for c in allc if not c.jr_links)} with no jr link across their edge")
    best_by_pin = {}
    for pin in pins:
        r = region_of(pin.addr)
        print()
        print(f"=== PIN ${pin.addr:04X} len {pin.length} [{r[0]}] -- {pin.note}")
        cov = covering(im, pin.addr)
        if cov is not None:
            on_b = "on an item boundary" if cov.addr == pin.addr else f"INSIDE an item starting ${cov.addr:04X}"
            print(f"  now: {where(im, pin.addr)}, {on_b}: {cov.kind} `{cov.text}` ({loc(cov)})")
            if cov.kind == "data":
                print(f"  NOTE: PIN falls in a data run -- the split must come before the table")
        sp = splits_for(im, pin, limit=top)
        if not sp:
            print("  NO transfer-ended split point in this region before the pin -- INFEASIBLE w/o bridge")
        print(f"  split points (instruction ending at b is an unconditional transfer), smallest gap first:")
        for s in sp:
            flags = []
            if s.labels_inside:
                flags.append(f"{len(s.labels_inside)} label(s) move: {', '.join(s.labels_inside[:4])}"
                             f"{' ...' if len(s.labels_inside) > 4 else ''}")
            if s.jr_bad:
                flags.append(f"JR OVERFLOW x{len(s.jr_bad)}: {s.jr_bad[0]}")
            if s.shared:
                flags.append(f"FILE SHARED with {', '.join(sorted(set(s.shared)))}")
            flags += s.warn
            print(f"    b=${s.b:04X} gap {s.gap:4d} B  after `{s.item.text}` @ {where(im, s.item.addr)}"
                  f"  insert after {loc(s.item)}")
            for f in flags:
                print(f"        - {f}")
        br = bridge_for(im, pin)
        if br:
            b, it = br
            print(f"  jr-bridge fallback (`jr pin_end` / `ds PIN-$` / pin, mid-routine): b=${b:04X} after "
                  f"`{it.text}` @ {where(im, it.addr)} ({loc(it)}): jr 2 + pad {pin.addr - 2 - b} "
                  f"= waste {pin.addr - b} B")
        if sp:
            s0 = sp[0]
            best_by_pin[pin] = s0
            same, other = refills(im, pin, s0, allc)
            print(f"  refill for the best gap ({s0.gap} B) -- chunks AFTER the pin, same region, no jr links:")
            for c in same[:top]:
                print(f"    {fmt_chunk(c, im)}")
            if not same:
                print("    (none)")
            got, combo = exact_fill(same, s0.gap)
            if combo:
                print(f"    best fill from these: {got}/{s0.gap} B with {len(combo)} chunk(s): "
                      f"{', '.join(c.names[0] for c in combo)}")
            mv = ("PROMOTION (low->page 1): check `promote_scout.py --labels`"
                  if r[0] == "page1" else
                  "DEMOTION (page 1->low): page-0 sub-ROM tenants see main page 1 but NOT the low "
                  "region -- check every caller")
            print(f"  cross-region refill ({mv}):")
            for c in other[:top]:
                print(f"    {fmt_chunk(c, im)}")
            got, combo = exact_fill(other, s0.gap)
            if combo:
                print(f"    best fill from these: {got}/{s0.gap} B with {len(combo)} chunk(s): "
                      f"{', '.join(c.names[0] for c in combo)}")
    # ---- combined: earlier pins shift later ones in the same region
    print()
    print("=== COMBINED (pins applied in address order, pads unfilled)")
    inserted: list[tuple[int, int]] = []          # (current insertion addr, grow)

    def shift(a):
        # a pad only moves code in ITS region: the low region ends in
        # `ds $4000-$`, which absorbs the growth before page 1
        return a + sum(g for p, g in inserted if a >= p and region_of(a) == region_of(p))
    for r in REGIONS:
        rp = sorted((p for p in pins if region_of(p.addr) == r), key=lambda p: p.addr)
        if not rp:
            continue
        cost = 0
        for pin in rp:
            sp = splits_for(im, pin, shift=shift, limit=1)
            if not sp:
                print(f"  ${pin.addr:04X}: no split after earlier pins -- INFEASIBLE as planned")
                continue
            s = sp[0]
            grow = s.gap + pin.length
            cost += grow
            print(f"  ${pin.addr:04X}: b=${s.b:04X} gap {s.gap} B after {where(im, s.item.addr)} "
                  f"({loc(s.item)}); grows the stream by {grow} B")
            inserted.append((s.item.addr + s.item.size, grow))
        free = region_free(im, r)
        print(f"  region {r[0]}: if every pad is refilled exactly, the cost is the pin bytes alone: "
              f"{sum(p.length for p in rp)} B")
        verdict = "fits" if free is not None and cost <= free else \
            f"OVERFLOWS by {cost - (free or 0)} B -- needs a carve (or refills) first"
        print(f"  region {r[0]}: pins cost {cost} B unfilled "
              f"(of which {sum(p.length for p in rp)} B are pin bytes); free {free} B -> {verdict}")
    return 0


# ---------------------------------------------------------------------------
# CHECK
# ---------------------------------------------------------------------------
def check(im: Image, pins: list[Pin], rom_path: str, budget: int | None,
          holes: bool = False) -> int:
    rom = open(rom_path, "rb").read()
    want = im.full[BASE - (TOP - len(im.full)):]
    if rom != want:
        diff = next(i for i in range(min(len(rom), len(want))) if rom[i] != want[i]) \
            if len(rom) == len(want) else 0
        print(f"pin_plan --check: STALE: {rom_path} != what {SRC} assembles to now "
              f"(first difference ${BASE + diff:04X}) -- run `make basic-reloc`")
        return 2
    sym_by_addr = {}
    for n, a in im.sym.items():
        sym_by_addr.setdefault(a, n)
    fails, waste, free_tot, rows = 0, 0, 0, []
    for pin in pins:
        got = rom[pin.addr - BASE: pin.addr - BASE + pin.length]
        ok, what = True, got.hex(" ").upper()
        if isinstance(pin.expect, bytes):
            ok = got == pin.expect
            exp = pin.expect.hex(" ").upper()
        else:
            tgt = got[1] | got[2] << 8 if len(got) == 3 else -1
            ok = got[:1] == b"\xC3" and BASE <= tgt < TOP
            if ok and pin.target:
                ok = im.sym.get(pin.target) == tgt
            exp = f"C3 -> {pin.target or 'a main-image address'}"
            if got[:1] == b"\xC3":
                what += f" (jp ${tgt:04X} {sym_by_addr.get(tgt, '?')})"
        # pad directly in front of the pin: address gaps + DEFS items + a jr bridge
        before = [it for it in im.code if it.addr < pin.addr]
        pad, bridge, j = 0, 0, len(before) - 1
        end = pin.addr
        while j >= 0:
            it = before[j]
            itend = it.addr + it.size
            if itend < end:
                pad += end - itend
            if it.kind == "data" and it.text.startswith("DEFS"):
                pad += it.size
                end = it.addr
                j -= 1
                continue
            # a jr bridge over the pin; `>=` because a body pin (checked by its head
            # bytes only) is longer than pin.length -- any forward jr from right
            # before the pin that lands past its start is skipping it.
            if it.kind == "instr" and it.hexb[:1] == b"\x18" and (jr_target(it) or 0) >= pin.addr + pin.length:
                bridge = 2
            break
        waste += pad + bridge
        free_tot += pad
        rows.append((pin.addr, pad))
        st = "OK  " if ok else "FAIL"
        fails += not ok
        if not holes:
            print(f"  {st} ${pin.addr:04X}: {what:30s} want {exp}; in front: {pad} B free"
                  f"{f' + {bridge} B jr bridge' if bridge else ''}  -- {pin.note}")
    if holes:
        # the wall readout's view: free bytes per region, each hole named, so a pad
        # is counted as free space and its fragmentation stays visible
        for name, lo, hi in (("low region", 0, BASE), ("page-1", BASE, TOP)):
            hs = [(a, n) for a, n in rows if lo <= a < hi and n]
            print(f"    measure: {name + ' pin pads':23s}= {sum(n for _, n in hs)} B free "
                  f"in front of pins ({', '.join(f'{n} B at ${a:04X}' for a, n in hs) or 'none'})")
        if fails:
            print(f"FAIL: {fails} pin(s) wrong -- run `make pin-check`", file=sys.stderr)
        return 1 if fails else 0
    verdict = "OK" if not fails and (budget is None or waste <= budget) else "FAIL"
    print(f"pin_plan --check: {verdict}: {len(pins) - fails}/{len(pins)} pins present; "
          f"{free_tot} B free in front of them (free space -- refill when convenient), "
          f"{waste - free_tot} B of jr bridge"
          + (f"; total {waste} B against --budget {budget} B" if budget is not None else ""))
    return 0 if verdict == "OK" else 1


def parse_pin(s: str) -> Pin:
    m = re.match(r"^(?:0x|\$)?([0-9A-Fa-f]{4}):(jp(?::(\w+))?|[0-9A-Fa-f]+)$", s)
    if not m:
        sys.exit(f"pin_plan: bad --pin {s!r} (want ADDR:HEXBYTES or ADDR:jp[:SYMBOL])")
    a = int(m.group(1), 16)
    if m.group(2).startswith("jp"):
        return Pin(a, 3, "jp", m.group(3), "ad-hoc jp pin")
    b = bytes.fromhex(m.group(2))
    return Pin(a, len(b), b, None, "ad-hoc pin")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--pin", action="append", help="ADDR:HEXBYTES or ADDR:jp[:SYM] (replaces the table)")
    ap.add_argument("--check", action="store_true", help="gate a built image")
    ap.add_argument("--rom", default=os.path.join(ROOT, "build", "basic-reloc.rom"))
    ap.add_argument("--holes", action="store_true", help="wall-readout lines: free bytes in front of the pins")
    ap.add_argument("--budget", type=int, default=None, help="max total pad + bridge in B (--check; default: no limit)")
    ap.add_argument("--top", type=int, default=5, help="candidates per list (plan)")
    a = ap.parse_args()
    pins = [parse_pin(p) for p in a.pin] if a.pin else PINS
    for p in pins:
        if region_of(p.addr) is None or region_of(p.addr + p.length - 1) != region_of(p.addr):
            sys.exit(f"pin_plan: ${p.addr:04X} len {p.length} is not inside one main region")
    im = load_image()
    if a.check or a.holes:
        return check(im, pins, a.rom, a.budget, holes=a.holes)
    return plan(im, pins, a.top)


if __name__ == "__main__":
    raise SystemExit(main())
