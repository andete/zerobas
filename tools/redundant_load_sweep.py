#!/usr/bin/env python3
"""Redundant-load sweep — the gate D-RETLN asked for on 2026-08-02 and did not get.

D-RETLN carved 160 dead bytes of one shape (`call skip_spaces` / `ld a,(hl)`,
where the callee already returns with A = (hl)) and filed the SHAPE as an open
item:

    "The open question this leaves is not the 160 B (they are gone) but whether
     a gate should exist for the shape: a redundant-load sweep is a two-line
     matcher, and there are certainly other idioms like it."

No gate was written. Seventeen days later D-EVSPDUP found the identical idiom at
`ev_sp` BY HAND while scouting 5 B for something else, carved 72 B from
`basic/expr.asm`, and left NINE MORE SITES in two other files — which this sweep
found on its first run. That is the argument for the gate, and it is why the
sweep FAILS rather than merely reporting.

WHAT IT PROVES, AND WHAT IT ONLY FLAGS
--------------------------------------
PROVEN contract — the tight skip loop, whose ONLY exit is a conditional `ret`
reached with A already holding the byte at the pointer:

    LABEL:  ld   a,(PTR)      ; PTR in {hl, ix+0, iy+0}
            cp   <imm>
            ret  nz|z
            inc  PTR
            jr   LABEL

For these, `call LABEL` followed immediately by `ld a,(PTR)` is DEAD: 1 B for
(hl), 3 B for (ix+0)/(iy+0). This is a gating finding.

Anything else that looks like `call X` / `ld a,(ptr)` is reported as a CANDIDATE
only — it needs a human to read X's exits. The sweep does not guess.

🔴 THE DENOMINATOR IS PRINTED, INCLUDING THE FILES IT WALKED. A sweep that
reports "clean" without saying what it swept is a scope claim, not a reading.

🔴 AND IT REPORTS THE REGION PER SITE, BECAUSE PRICING BY FILE IS WRONG.
D-LOADSWEEP priced its own 9 `ev_sp` sites as "27 B of main page 1" by looking up
ONE symbol per file (`str_eval_one`, $498F, page 1) and treating it as the file's
address. `basic/str-engine.asm` spans BOTH regions: the six sites there are in
`ev_str_arg`/`ev_f_instr`/`ev_rel_str` at $29F3-$2E8F, the LOW REGION, and the
measurement came back 18 B low + 9 B page 1. The prediction was right about the
total and wrong about every byte's home. So each site is resolved to its
ENCLOSING LABEL and that label's address, whenever build/basic-reloc.sym exists.
"""
import glob, os, re, sys

PTRS = {"hl": 1, "ix+0": 3, "iy+0": 3}     # name -> bytes of `ld a,(PTR)`

LBL   = re.compile(r'^([A-Za-z_][\w]*):')
SYMLN = re.compile(r'^(\S+)\s+EQU\s+([0-9A-Fa-f]+)H')
LOW_TOP = 0x4000          # low region below this, main page 1 at/above it
LDA   = re.compile(r'^\s+ld\s+a\s*,\s*\(\s*(hl|ix\s*\+\s*0|iy\s*\+\s*0)\s*\)\s*(?:;.*)?$', re.I)
CP    = re.compile(r'^\s+cp\s+\S', re.I)
RETCC = re.compile(r'^\s+ret\s+(nz|z|nc|c|po|pe|p|m)\s*(?:;.*)?$', re.I)
INC   = re.compile(r'^\s+inc\s+(hl|ix|iy)\s*(?:;.*)?$', re.I)
JR    = re.compile(r'^\s+jr\s+([A-Za-z_][\w]*)\s*(?:;.*)?$', re.I)
CALL  = re.compile(r'^\s+call\s+(?:(nz|z|nc|c|po|pe|p|m)\s*,\s*)?([A-Za-z_][\w]*)\s*(?:;.*)?$', re.I)


def norm(p):
    return re.sub(r'\s+', '', p).lower()


def code(lines, i):
    """index of the next non-blank, non-comment line at or after i."""
    while i < len(lines) and (not lines[i].strip() or lines[i].strip().startswith(';')):
        i += 1
    return i


REVIEWED_FILE = 'tools/redundant-load-reviewed.txt'


def load_reviewed():
    """callee -> (verdict, reason). A CONTROL, not a suppression list: the sweep
    still prints every candidate. What this buys is that a NEW candidate callee
    surfaces as `unreviewed` instead of blending into a list of already-read
    ones, and that an entry whose sites have all gone reports as stale rather
    than sitting there forever asserting nothing."""
    out = {}
    if not os.path.exists(REVIEWED_FILE):
        return out
    for l in open(REVIEWED_FILE, encoding='utf-8'):
        l = l.strip()
        if not l or l.startswith('#'):
            continue
        parts = l.split(None, 2)
        if len(parts) >= 2:
            out[parts[0]] = (parts[1], parts[2] if len(parts) > 2 else '')
    return out


def load_syms():
    for cand in ('build/basic-reloc.sym',):
        if os.path.exists(cand):
            out = {}
            for l in open(cand, encoding='utf-8', errors='replace'):
                m = SYMLN.match(l.strip())
                if m:
                    out[m.group(1)] = int(m.group(2), 16)
            return out
    return {}


def region_of(lines, i, syms):
    """Resolve line i to its enclosing label's region. '?' when unknown --
    an unknown region is reported as unknown, never guessed from the path."""
    if not syms:
        return "?", None
    for j in range(i, -1, -1):
        m = LBL.match(lines[j])
        if m and m.group(1) in syms:
            a = syms[m.group(1)]
            if a >= 0x8000:
                return "sub", a
            return ("LOW" if a < LOW_TOP else "page1"), a
    return "?", None


def scan_files():
    pats = ['basic/*.asm', 'basic/*.inc', 'sub/*.asm', 'sub/*.inc',
            'disk/*.asm', 'disk/*.inc', 'tape/*.asm', 'tape/*.inc',
            'cbios-repack/*.asm', 'cbios-repack/*.inc']
    out = []
    for p in pats:
        out.extend(glob.glob(p))
    return sorted(set(out))


def main():
    files = scan_files()
    syms = load_syms()
    src = {}
    nlines = 0
    for f in files:
        src[f] = open(f, encoding='utf-8', errors='replace').read().split('\n')
        nlines += len(src[f])

    # --- pass 1: find every PROVEN tight-skip routine -------------------------
    proven = {}          # label -> (ptr, file, line)
    for f, lines in src.items():
        for i, l in enumerate(lines):
            m = LBL.match(l)
            if not m:
                continue
            j = code(lines, i + 1)
            if j >= len(lines):
                continue
            a = LDA.match(lines[j])
            if not a:
                continue
            ptr = norm(a.group(1))
            k = code(lines, j + 1)
            if k >= len(lines) or not CP.match(lines[k]):
                continue
            k2 = code(lines, k + 1)
            if k2 >= len(lines) or not RETCC.match(lines[k2]):
                continue
            k3 = code(lines, k2 + 1)
            if k3 >= len(lines):
                continue
            inc = INC.match(lines[k3])
            if not inc or not ptr.startswith(inc.group(1).lower()):
                continue
            k4 = code(lines, k3 + 1)
            if k4 >= len(lines):
                continue
            jr = JR.match(lines[k4])
            if not jr or jr.group(1) != m.group(1):
                continue
            proven[m.group(1)] = (ptr, f, i + 1)

    # --- pass 2: every call site, classified ---------------------------------
    dead, cand = [], []
    calls = 0
    for f, lines in src.items():
        for i, l in enumerate(lines):
            c = CALL.match(l)
            if not c:
                continue
            calls += 1
            cc, callee = c.group(1), c.group(2)
            j = code(lines, i + 1)
            if j >= len(lines):
                continue
            a = LDA.match(lines[j])
            if not a:
                continue
            ptr = norm(a.group(1))
            if callee in proven and proven[callee][0] == ptr and not cc:
                reg, addr = region_of(lines, i, syms)
                dead.append((f, i + 1, callee, ptr, PTRS[ptr], reg, addr))
            else:
                why = ("callee's exits unproven" if callee not in proven
                       else "conditional call" if cc
                       else f"pointer differs ({proven[callee][0]} vs {ptr})")
                cand.append((f, i + 1, callee, ptr, why))

    print(f"== denominator ==")
    print(f"   {len(files)} files, {nlines} lines, {calls} `call` sites walked")
    print(f"   {len(proven)} routine(s) with a PROVEN return-the-byte contract:")
    for k in sorted(proven):
        ptr, f, ln = proven[k]
        print(f"     {k:20s} A=({ptr:5s}) {f}:{ln}")

    reviewed = load_reviewed()
    cand_callees = sorted({c[2] for c in cand})
    unreviewed = [c for c in cand_callees if c not in reviewed]
    stale = [c for c in sorted(reviewed) if c not in cand_callees]

    print(f"\n== CANDIDATES — {len(cand)} site(s), {len(cand_callees)} callee(s) ==")
    print("   (the sweep proves only the tight-skip shape; these need a human to")
    print("    read the callee's exits, and every one below has been read)")
    for f, ln, callee, ptr, why in cand:
        v = reviewed.get(callee, ('UNREVIEWED', 'nobody has read this callee'))[0]
        print(f"   [{v:10s}] {f}:{ln}  call {callee} / ld a,({ptr})")
    if reviewed:
        print(f"\n   verdicts on file ({REVIEWED_FILE}):")
        for c in cand_callees:
            v, why2 = reviewed.get(c, ('UNREVIEWED', 'nobody has read this callee'))
            print(f"     {c:18s} {v:8s} {why2}")

    rc = 0
    if unreviewed:
        print(f"\n== 🔴 UNREVIEWED CANDIDATE CALLEE(S) (gating) ==")
        for c in unreviewed:
            print(f"   {c} — read its exits, then add a line to {REVIEWED_FILE}")
        rc = 1
    if stale:
        print(f"\n== 🔴 STALE REVIEW ENTRIES (gating) ==")
        print("   these callees are on file but no longer appear as candidates;")
        print("   an entry that asserts nothing is how this control goes blind:")
        for c in stale:
            print(f"   {c}")
        rc = 1

    print(f"\n== DEAD LOADS (gating) ==")
    if not dead:
        print("   none — every call of a proven routine already relies on the contract")
        return rc
    byc = {}
    for f, ln, callee, ptr, b, reg, addr in dead:
        byc.setdefault(callee, []).append((f, ln, b, reg, addr))
    total = sum(d[4] for d in dead)
    for callee in sorted(byc):
        rows = byc[callee]
        print(f"   {callee}: {len(rows)} site(s), {sum(r[2] for r in rows)} B")
        for f, ln, b, reg, addr in rows:
            at = f"${addr:04X}" if addr is not None else "     "
            print(f"       {f}:{ln}  ({b} B)  {reg:5s} {at}")
    perreg = {}
    for *_, b, reg, _a in dead:
        perreg[reg] = perreg.get(reg, 0) + b
    if syms:
        print("\n   by REGION (resolved per site, not per file): "
              + ", ".join(f"{k} {v} B" for k, v in sorted(perreg.items())))
    else:
        print("\n   region UNRESOLVED (no build/basic-reloc.sym) — build before pricing")
    print(f"   {len(dead)} dead load(s), {total} B — the callee already returns the value in A.")
    return 1


sys.exit(main())
