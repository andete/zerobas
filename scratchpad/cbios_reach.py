#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-CBIOSDEAD: which C-BIOS code can the MERGED zerobas ROM still reach?

C-BIOS is open (BSD) source and the repack is ours, so this reads C-BIOS's own
sources and our built ROMs -- never the reference machines' ROMs.

THE MODEL is tools/check_dead_code.py's: every label owns a LINEAR span (its line
through the line before the next label in the same file); a span is LIVE if it is a
seed, if a live span MENTIONS its label (any identifier, not just call/jp targets),
or if a live span FALLS THROUGH into it (last code line not an unconditional
terminator, tools/check_tenant_closure.py `_is_terminator`). Fixed point.

SEEDS (conservative -- an unknown keeps code alive, never kills it):
  * every label mentioned in main.asm's fixed area (from `org $0000` to
    `ds $0200 - $`) EXCEPT on a jump-table line whose vector the merged ROM
    overlays (measured: the bytes differ between the repacked C-BIOS and
    build/zerobas-main-eu.rom);
  * the span right after every `ds $XXXX - $` pin (an address something outside
    may enter: the compat tails, the keyboard scan, the font);
  * every file's prologue (lines before its first label);
  * every C-BIOS label whose ADDRESS a zerobas build names (a `jp`/`call` back
    into C-BIOS: CBIOS_CLS, CBIOS_GICINI, CBIOS_TUPC, ...): any zerobas symbol
    whose value equals a C-BIOS label address in the code range.
Conditional assembly (IF VDP = ...) is NOT evaluated: every branch's mentions
count -- conservative again.

    python3 scratchpad/cbios_reach.py CBIOS_SRC_DIR CBIOS_LST
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from check_tenant_closure import _is_terminator  # noqa: E402

LABEL = re.compile(r"^([A-Za-z_][\w]*):")
IDENT = re.compile(r"[A-Za-z_][\w]*")
INCL = re.compile(r'^\s*include\s+"([^"]+)"', re.I)
DSPIN = re.compile(r"^\s*ds\s+\$([0-9A-Fa-f]+)\s*-\s*\$", re.I)


def strip(line: str) -> str:
    out, q = [], False
    for ch in line:
        if ch in "\"'":
            q = not q
        if ch == ";" and not q:
            break
        out.append(ch)
    return "".join(out)


def files_of(src: str, top: str) -> list[str]:
    seen: list[str] = []

    def walk(name):
        p = os.path.join(src, name)
        if not os.path.exists(p) or name in seen:
            return
        seen.append(name)
        for l in open(p, encoding="latin-1"):
            m = INCL.match(l)
            if m:
                walk(m.group(1))
    walk(top)
    return seen


def lst_syms(lst: str) -> dict[str, int]:
    out = {}
    for l in open(lst, encoding="latin-1"):
        p = l.split()
        if len(p) >= 3 and p[1] == "EQU":
            try:
                out[p[0]] = int(p[2].rstrip("Hh"), 16)
            except ValueError:
                pass
    return out


ZBEQU = re.compile(r"^(CBIOS_\w+):?\s+equ\s+\$([0-9A-Fa-f]+)", re.I)


def zb_syms() -> set[int]:
    """The addresses zerobas jumps BACK into C-BIOS through: its `CBIOS_<name> equ $XXXX`
    lines (basic/ sub/ disk/ tape/). 🔴 The first cut took EVERY zerobas symbol's value,
    and constants that happened to equal a C-BIOS label kept grpprt / mapxy / putq alive:
    an address match by number is not a reference. A literal `call $XXXX` into C-BIOS
    would be missed by this -- checked absent (grep) when D-CBIOSDEAD was written."""
    vals = set()
    for d in ("basic", "sub", "disk", "tape"):
        for dp, _, fs in os.walk(os.path.join(ROOT, d)):
            for f in fs:
                if f.endswith((".asm", ".inc")):
                    for l in open(os.path.join(dp, f), encoding="latin-1"):
                        m = ZBEQU.match(l)
                        if m:
                            vals.add(int(m.group(2), 16))
    return vals


# D-CBIOS032 (2026-11-22): a candidate base before it is merged -- CBR_REPACKED / CBR_MERGED name the two
# ROMs (the merged one may be a stand-in with only the overlaid vectors changed), CBR_CUTOFF the end of C-BIOS's
# page-0 code, CBR_NOBACK=1 drops the back-references read from the CURRENT zerobas build (another base's addresses).
REPACKED = os.environ.get("CBR_REPACKED") or os.path.join(ROOT, "build/cbios_main_msx1_eu-repacked.rom")
MERGED = os.environ.get("CBR_MERGED") or os.path.join(ROOT, "build/zerobas-main-eu.rom")
CUTOFF = int(os.environ.get("CBR_CUTOFF", "0x2781"), 16)


def overlaid_vectors() -> set[int]:
    c = open(REPACKED, "rb").read()
    m = open(MERGED, "rb").read()
    return {a for a in range(0, 0x160, 1) if m[a] == 0xC3 and c[a:a + 3] != m[a:a + 3]}


def main(argv):
    src, lst = argv[0], argv[1]
    syms = lst_syms(lst)
    names = set(syms)
    files = files_of(src, "main_msx1_eu.asm")
    over = overlaid_vectors()

    spans = {}          # label -> (file, [code lines])
    order = []          # (file, [label...]) in file order
    seeds = set()
    prologue_mentions = set()
    for f in files:
        labs, cur, body = [], None, []
        fixed = f == "main.asm"
        in_fixed = False
        pending_pin = False
        org = 0
        for raw in open(os.path.join(src, f), encoding="latin-1"):
            code = strip(raw).rstrip()
            lm = LABEL.match(code)
            if lm and lm.group(1) not in names:
                # a label this build does not assemble (an `IF VDP != TMS99X8` arm's): its
                # lines stay in the span before it, so a branch's `jr filvrm_cont` is not
                # read as the end of filvrm (filvrm_lp read DEAD on that, 2026-11-19)
                code = code[lm.end():]
                lm = None
            if lm:
                if cur is not None:
                    spans[cur] = (f, body)
                cur, body = lm.group(1), []
                labs.append(cur)
                if pending_pin:
                    seeds.add(cur)
                    pending_pin = False
                code = code[lm.end():]
            s = code.strip()
            if fixed and re.match(r"org\s+\$0000\b", s, re.I):
                in_fixed = True
            pin = DSPIN.match(s)
            if pin:
                org = int(pin.group(1), 16)
                pending_pin = True
                if fixed and org == 0x0200:
                    in_fixed = False
            if s and not pin and pending_pin and not lm:
                pending_pin = False if not s.lower().startswith(("ds", "org", "if", "else", "endif")) else pending_pin
            if in_fixed and s:
                ids = set(IDENT.findall(s))
                if s.lower().startswith("jp") and org in over:
                    pass                      # an overlaid vector's target: NOT a seed
                else:
                    seeds |= ids & names
            if in_fixed and s.lower().startswith("jp") and org in over:
                continue        # an overlaid vector's `jp body`: zerobas's bytes replace it,
                                # so it is no mention of `body` (the jump table sits INSIDE
                                # romid's span; the first cut kept every body alive that way)
            if s:
                if cur is None:
                    prologue_mentions |= set(IDENT.findall(s)) & names
                else:
                    body.append(s)
        if cur is not None:
            spans[cur] = (f, body)
        order.append((f, labs))
    seeds |= prologue_mentions
    zb = zb_syms()
    back = set() if os.environ.get("CBR_NOBACK") else \
        {n for n, a in syms.items() if n in spans and 0x0200 <= a < CUTOFF and a in zb}
    seeds |= back

    live = set(s for s in seeds if s in spans)
    why = {s: "seed" for s in live}
    # FALLTHROUGH follows ROM ADDRESS order, not a file's label order: the first cut took
    # "the next label in the same file", and `include "chput.asm"` at the end of chget_nowrap
    # (after its `ret`) made lptout read as fallen into. Labels at one address are one place.
    byaddr = sorted((syms[n], n) for n in spans if n in syms)
    nxt, alias = {}, {}
    for (a1, n1), (a2, n2) in zip(byaddr, byaddr[1:]):
        if a2 > a1:
            for a0, n0 in byaddr:
                if a0 == a1:
                    nxt[n0] = n2
    for a, n in byaddr:
        alias.setdefault(a, []).append(n)
    changed = True
    while changed:
        changed = False
        for n in list(live):
            f, body = spans[n]
            for l in body:
                for i in IDENT.findall(l):
                    if i in spans and i not in live:
                        live.add(i); why[i] = f"mentioned by {n}"; changed = True
            for o in alias.get(syms.get(n), []):
                if o not in live:
                    live.add(o); why[o] = f"same address as {n}"; changed = True
            last = next((l for l in reversed(body) if l and not INCL.match(l)), "")
            cond = any(re.match(r"(if|ifdef|ifndef|else|endif)\b", l, re.I) for l in body)
            if not body:
                continue        # stacked labels on one place: the alias step above covers it
                                # (pntini / scanr / scanl's shared `ret` "fell into" mapxy)
            data = all(re.match(r"(db|dw|defb|defw|defm|ds|defs)\b", l, re.I) for l in body)
            if data:
                continue        # an all-DATA span is never executed into the next label
                                # (vdp_bios's `db` "fell into" gtpdl, chput_esc_table's into
                                # lptout); a code span ending in inline data still falls
            if n in nxt and (cond or not _is_terminator(last)) and nxt[n] not in live:
                live.add(nxt[n]); why[nxt[n]] = f"fallthrough from {n}"; changed = True
    for q in argv[2:]:
        chain, k = [], q
        while k in why and len(chain) < 30:
            chain.append(f"{k} <- {why[k]}")
            if why[k] == "seed":
                break
            k = why[k].split()[-1]
        print("WHY", q, ":", " | ".join(chain) or "DEAD")
    dead = sorted((syms[n], n, spans[n][0]) for n in spans if n not in live and n in syms)
    # group consecutive dead labels into address runs
    allsorted = sorted((a, n) for n, a in syms.items() if n in spans)
    idx = {n: k for k, (a, n) in enumerate(allsorted)}
    runs, run = [], []
    for a, n, f in dead:
        if run and idx[n] == idx[run[-1][1]] + 1:
            run.append((a, n, f))
        else:
            if run:
                runs.append(run)
            run = [(a, n, f)]
    if run:
        runs.append(run)
    global ROMBYTES
    ROMBYTES = open(REPACKED, "rb").read()
    tot = 0
    print(f"overlaid vectors: {len(over)}; seeds {len(seeds)}; back-references {sorted(back)}")
    for r in runs:
        a0 = r[0][0]
        k = idx[r[-1][1]] + 1
        end = allsorted[k][0] if k < len(allsorted) else a0
        rom = ROMBYTES
        end = min(end, len(rom))
        while end > a0 and rom[end - 1] == 0:     # stop at the last code byte, not the pad
            end -= 1
        size = end - a0
        if a0 >= CUTOFF or size <= 0 or size > 0x400:
            continue
        tot += size
        print(f"  ${a0:04X}-${end - 1:04X} {size:4} B  {r[0][2]:12} {' '.join(x[1] for x in r)[:110]}")
    print(f"TOTAL dead below ${CUTOFF:04X}: {tot} B")


if __name__ == "__main__":
    main(sys.argv[1:])
