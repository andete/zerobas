#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""gen_kwidx -- the detokeniser's reverse index into kwtable, GENERATED from it.

detok_kw (basic/detok.inc) turns a single-byte token back into its keyword by
walking kwtable (basic/kwtable.inc) to the FIRST entry with tlen == 1 carrying
that token: ~140 T an entry, ~half of a 150-line `SAVE ,A` (TODO, D-KWIDXCARVE).
This writes basic/kwidx.inc beside it:

  kw_ord   128 B  token $80..$FF -> the ordinal of that first entry (0-based,
                  counting EVERY entry, whatever its tlen), or $FF: no such entry
  kw_ord2  token $FF xx -> the first tlen == 2 entry's ordinal (D-KWIDX2), xx in KW2_LO..
  kw_bkt   2 B per BUCKET entries: kwtable + the byte offset of entry
                  BUCKET * k -- detok_kw starts there and skips the rest

Offsets, not addresses, so the include does not depend on where it lands. The
build switches that gate entries (`IF G6_RESIDENT` ...) are evaluated from
basic/sysvars.inc, as the assembler does. A stale index would print the wrong
keyword in LIST and SAVE ,A, so `--check` regenerates and diffs, and the static
gate runs it (kwidx-check).

    python3 tools/gen_kwidx.py            # write basic/kwidx.inc
    python3 tools/gen_kwidx.py --check    # exit 1 if it is not up to date
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KWTABLE = os.path.join(ROOT, "basic", "kwtable.inc")
SYSVARS = os.path.join(ROOT, "basic", "sysvars.inc")
OUT = os.path.join(ROOT, "basic", "kwidx.inc")
BUCKET = 16


def equates():
    raw = {}
    for line in open(SYSVARS, encoding="utf-8"):
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s+equ\s+([^;]+)", line, re.I)
        if m and m.group(1) not in raw:      # first wins, as the assembler's include order
            raw[m.group(1)] = m.group(2).strip()
    val = {}

    def ev(name, depth=0):
        if name in val:
            return val[name]
        if depth > 20 or name not in raw:
            raise KeyError(name)
        expr = raw[name]
        expr = re.sub(r"\$([0-9A-Fa-f]+)", r"0x\1", expr)
        expr = re.sub(r"\b([A-Za-z_][A-Za-z0-9_]*)\b",
                      lambda m: str(ev(m.group(1), depth + 1)) if not m.group(1).startswith("0x") else m.group(1),
                      expr)
        v = int(eval(expr, {"__builtins__": {}}))   # noqa: S307 -- our own source's arithmetic
        val[name] = v
        return v
    return ev


def entries(ev):
    """[(offset, klen, name, tokens)] in table order, the IF blocks evaluated."""
    out, off, live = [], 0, [True]
    started = False
    for line in open(KWTABLE, encoding="utf-8"):
        code = line.split(";", 1)[0].rstrip()
        if code.startswith("kwtable:"):
            started = True
            continue
        if not started or not code.strip():
            continue
        s = code.strip()
        m = re.match(r"IF\s+(\w+)$", s)
        if m:
            live.append(live[-1] and ev(m.group(1)) != 0)
            continue
        if s == "ENDIF":
            live.pop()
            continue
        if s.startswith("ELSE"):
            raise SystemExit("gen_kwidx: ELSE in kwtable.inc is not handled -- extend the parser")
        m = re.match(r'db\s+(\d+)\s*,\s*"([^"]*)"\s*,\s*(\d+)\s*,\s*(.+)$', s)
        if not m:
            if re.match(r"db\s+0$", s):
                if live[-1]:
                    return out, off + 1
                continue
            raise SystemExit(f"gen_kwidx: cannot parse kwtable line: {s!r}")
        if not live[-1]:
            continue
        klen, name, tlen = int(m.group(1)), m.group(2), int(m.group(3))
        if klen != len(name):
            raise SystemExit(f"gen_kwidx: {name!r} declares klen {klen}")
        toks = [ev(t.strip()) if not t.strip().startswith("$") else int(t.strip()[1:], 16)
                for t in m.group(4).split(",")]
        if len(toks) != tlen:
            raise SystemExit(f"gen_kwidx: {name!r} declares tlen {tlen}, has {len(toks)}")
        out.append((off, klen, name, toks))
        off += 1 + klen + 1 + tlen
    raise SystemExit("gen_kwidx: no terminating `db 0` in kwtable.inc")


def render():
    ev = equates()
    ents, size = entries(ev)
    ords = [0xFF] * 128
    for i, (_off, _kl, _name, toks) in enumerate(ents):
        if len(toks) == 1 and 0x80 <= toks[0] <= 0xFF and ords[toks[0] - 0x80] == 0xFF:
            if i > 0xFE:
                raise SystemExit("gen_kwidx: more than 255 entries -- an ordinal no longer fits a byte")
            ords[toks[0] - 0x80] = i
    bkts = [ents[k][0] for k in range(0, len(ents), BUCKET)]
    # D-KWIDX2: the two-byte $FF-prefixed tokens, by their second byte
    two = [t[1] for (_o, _k, _n, t) in ents if len(t) == 2 and t[0] == 0xFF]
    lo2, hi2 = min(two), max(two)
    ords2 = [0xFF] * (hi2 - lo2 + 1)
    for i, (_off, _kl, _name, toks) in enumerate(ents):
        if len(toks) == 2 and toks[0] == 0xFF and ords2[toks[1] - lo2] == 0xFF:
            ords2[toks[1] - lo2] = i
    lines = ["; Copyright (c) 2026 Joost Yervante Damad",
             "; SPDX-License-Identifier: 0BSD",
             "; kwidx.inc -- GENERATED by tools/gen_kwidx.py from basic/kwtable.inc; do not edit.",
             "; Clean-room: computed mechanically from this project's own basic/kwtable.inc (its",
             "; header gives the tokens' provenance: oracle-sourced, byte-identity verified) and",
             "; basic/sysvars.inc's token equates. No reference ROM byte, no disassembly.",
             f"; {len(ents)} entries, {size} B; {sum(o != 0xFF for o in ords)} single-byte tokens indexed.",
             f"KW_BUCKET       equ     {BUCKET}",
             "kw_ord:"]
    for r in range(0, 128, 16):
        lines.append("                db      " + ",".join(f"${o:02X}" for o in ords[r:r + 16])
                     + f"   ; ${0x80 + r:02X}..${0x8F + r:02X}")
    lines.append(f"KW2_LO          equ     ${lo2:02X}   ; $FF-prefixed tokens: second bytes ${lo2:02X}..${hi2:02X}")
    lines.append(f"KW2_N           equ     {len(ords2)}")
    lines.append("kw_ord2:")
    for r in range(0, len(ords2), 16):
        lines.append("                db      " + ",".join(f"${o:02X}" for o in ords2[r:r + 16])
                     + f"   ; $FF ${lo2 + r:02X}..")
    lines.append("kw_bkt:")
    for k, o in enumerate(bkts):
        lines.append(f"                dw      kwtable + {o}   ; entry {k * BUCKET}: {ents[k * BUCKET][2]}")
    return "\n".join(lines) + "\n"


def main() -> int:
    text = render()
    if "--check" in sys.argv:
        have = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if have != text:
            print("🔴 kwidx-check: basic/kwidx.inc is not what tools/gen_kwidx.py makes of "
                  "kwtable.inc -- run `python3 tools/gen_kwidx.py`")
            return 1
        print("kwidx-check: basic/kwidx.inc matches kwtable.inc")
        return 0
    open(OUT, "w", encoding="utf-8").write(text)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
