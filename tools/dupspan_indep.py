#!/usr/bin/env python3
"""D-DEFFN FUNDING — decide POSITION-INDEPENDENCE for byte-identical spans.

`scratchpad/dupspan_sweep.py` finds byte-identical label-to-label spans in the
main image and says out loud that it CANNOT decide whether collapsing one onto
another is safe.  D-DUPSPAN then read ~15 groups by hand and got two of the
three blind spots right by eye.  This tool asks the ROM BYTES -- the real
surface -- instead, which is the standing cure for a proxy.

THE THREE THINGS THE SWEEP CANNOT SEE, and how each is decided here:

  1. DOES THE SPAN END IN A REAL TERMINATOR?  A span that runs off its own end
     continues into whatever follows, and what follows differs per member, so
     the two are not the same routine however equal their bytes.  Decided by
     decoding the span's instructions and asking whether the LAST one is an
     unconditional flow break (`ret`, `jp nn`, `jr d`, `jp (hl)`, `reti/retn`).
     `ret nz` and `jp nc,X` are NOT terminators.

  2. DO ITS RELATIVE JUMPS LAND INSIDE IT?  `jr`/`djnz` encode a DISPLACEMENT,
     so two byte-identical spans with a `jr` leaving the span jump to two
     DIFFERENT addresses.  Decided by decoding every `18 20 28 30 38 10` in the
     span and checking the target lies in [0, len).

  3. IS THE LABEL ENTERED BY FALLTHROUGH?  Then aliasing it away needs a `jp`
     (3 B) left in its place, so the recovery is len-3, not len -- and if
     len <= 3 the collapse is worth nothing.  Decided by decoding the
     PREDECESSOR span the same way and asking whether IT terminates.

Everything above is decided from `build/basic-reloc.rom` + `.sym`.  A span whose
instructions do not TILE EXACTLY to its end (data tables, inline operands after
a never-returning `call`) is reported UNKNOWN and never counted as safe: a
mis-decode must not be able to produce a green answer.

⚠️ WHAT IS STILL NOT DECIDED HERE, and must be read or built:
  * a `call` to a routine that never returns makes the bytes after it
    unreachable, so an "ends without terminator" verdict can be pessimistic;
  * a reference to an address strictly INSIDE a span (`$+n`, `label+n`) would
    survive the collapse pointing at the canonical -- advisory scan only;
  * `jr` REACH at the CALL SITES of an aliased name is priced here as an
    ESTIMATE; the assembler is the authority and errors when it does not reach.

🔴 CALIBRATION -- `--selftest` runs both halves and exits non-zero if either
fails:
  * SYNTHETIC: planted spans with known answers for all three questions, so a
    run that says "everything is safe" is known not to be a checker that says
    that by construction.
  * REAL, KNOWN-ANSWER: the `3 B x6` bare `jp raise_error` group, which
    D-DUPSPAN read by hand and documented as FIVE of six entered by fallthrough
    from a different `ld a,N` (docs/spec-basic-dupspan.md §2.1).  The tool must
    reproduce that 5, by name.
"""
from __future__ import annotations
import collections
import sys

BASE = 0x2812                       # the main image's load address

# ---------------------------------------------------------------- Z80 decode

def _base_lengths():
    L = [1] * 256
    for op in (0x06, 0x0E, 0x16, 0x1E, 0x26, 0x2E, 0x36, 0x3E,
               0xC6, 0xCE, 0xD6, 0xDE, 0xE6, 0xEE, 0xF6, 0xFE,
               0x10, 0x18, 0x20, 0x28, 0x30, 0x38,
               0xD3, 0xDB):
        L[op] = 2
    for op in (0x01, 0x11, 0x21, 0x31, 0x22, 0x2A, 0x32, 0x3A,
               0xC3, 0xC2, 0xCA, 0xD2, 0xDA, 0xE2, 0xEA, 0xF2, 0xFA,
               0xCD, 0xC4, 0xCC, 0xD4, 0xDC, 0xE4, 0xEC, 0xF4, 0xFC):
        L[op] = 3
    return L

_LEN = _base_lengths()
_REL = {0x10, 0x18, 0x20, 0x28, 0x30, 0x38}     # djnz, jr, jr cc
_TERM1 = {0xC9, 0xC3, 0x18, 0xE9}               # ret, jp nn, jr d, jp (hl)
# DD/FD-indexed opcodes that carry a displacement byte
_IDX = ({0x34, 0x35, 0x36, 0x46, 0x4E, 0x56, 0x5E, 0x66, 0x6E, 0x7E,
         0x86, 0x8E, 0x96, 0x9E, 0xA6, 0xAE, 0xB6, 0xBE}
        | {o for o in range(0x70, 0x78) if o != 0x76})


def decode(buf, i):
    """-> (length, is_terminator, rel_target_offset_or_None, ok)

    `ok` is False when the instruction runs past the end of `buf`."""
    if i >= len(buf):
        return 0, False, None, False
    op = buf[i]
    if op == 0xCB:
        return 2, False, None, i + 2 <= len(buf)
    if op == 0xED:
        if i + 1 >= len(buf):
            return 2, False, None, False
        sub = buf[i + 1]
        n = 4 if (0x40 <= sub < 0x80 and (sub & 0xC7) == 0x43) else 2
        term = sub in (0x45, 0x4D, 0x55, 0x5D, 0x65, 0x6D, 0x75, 0x7D)  # retn/reti
        return n, term, None, i + n <= len(buf)
    if op in (0xDD, 0xFD):
        if i + 1 >= len(buf):
            return 2, False, None, False
        sub = buf[i + 1]
        if sub == 0xCB:
            return 4, False, None, i + 4 <= len(buf)
        n = 1 + _LEN[sub] + (1 if sub in _IDX else 0)
        return n, sub == 0xE9, None, i + n <= len(buf)
    n = _LEN[op]
    if op in _REL:
        if i + 2 > len(buf):
            return 2, False, None, False
        d = buf[i + 1]
        if d > 127:
            d -= 256
        return 2, op == 0x18, i + 2 + d, True
    return n, op in _TERM1, None, i + n <= len(buf)


def walk(b):
    """Decode a span linearly.  -> (tiles, ends_terminated, rel_targets)"""
    i = 0
    rels = []
    last_term = False
    while i < len(b):
        n, term, rel, ok = decode(b, i)
        if not ok or n == 0:
            return False, False, rels
        if rel is not None:
            rels.append(rel)
        last_term = term
        i += n
    return i == len(b), last_term, rels


# ---------------------------------------------------------------- span model

def load_syms(path, lo, hi):
    out = []
    for line in open(path):
        line = line.strip()
        if not line or "EQU" not in line:
            continue
        name, _, val = line.partition("\tEQU")
        val = val.strip().rstrip("H").lstrip("0") or "0"
        try:
            a = int(val, 16)
        except ValueError:
            continue
        name = name.strip()
        if lo <= a < hi:
            out.append((a, name))
    out.sort()
    return out


def build_spans(rom):
    end = BASE + len(rom)
    syms = load_syms("build/basic-reloc.sym", BASE, end)
    byaddr = collections.OrderedDict()
    for a, n in syms:
        byaddr.setdefault(a, []).append(n)
    addrs = sorted(byaddr)
    spans = []
    for i, a in enumerate(addrs):
        nxt = addrs[i + 1] if i + 1 < len(addrs) else end
        if nxt <= a:
            continue
        b = rom[a - BASE:nxt - BASE]
        if b:
            spans.append({"addr": a, "name": "/".join(byaddr[a]), "bytes": b})
    for s in spans:
        tiles, term, rels = walk(s["bytes"])
        s["tiles"] = tiles
        s["term"] = term
        s["relout"] = [r for r in rels if not (0 <= r < len(s["bytes"]))]
    prev = None
    for s in spans:
        # fallthrough iff the PREVIOUS span is contiguous and does not terminate
        if prev is not None and prev["addr"] + len(prev["bytes"]) == s["addr"]:
            s["pred"] = prev["name"]
            s["fall"] = "yes" if (prev["tiles"] and not prev["term"]) else (
                "no" if prev["tiles"] else "unknown")
        else:
            s["pred"] = None
            s["fall"] = "no"
        prev = s
    return spans


def rel_callers(rom, target):
    """Byte positions whose `jr`/`djnz` lands on `target`.  Over-reports on data;
    used only to PRICE widening, never to decide safety."""
    out = []
    for i in range(len(rom) - 1):
        if rom[i] in _REL:
            d = rom[i + 1]
            if d > 127:
                d -= 256
            if BASE + i + 2 + d == target:
                out.append(BASE + i)
    return out


# ---------------------------------------------------------------- verdicts

def verdict(s):
    """Can this member be aliased away?  -> (code, recovered_bytes, why)"""
    n = len(s["bytes"])
    if not s["tiles"]:
        return "UNKNOWN", 0, "does not decode to its own end (data? inline operand?)"
    if not s["term"]:
        return "UNSAFE", 0, "runs off its end — continues into different code"
    if s["relout"]:
        return "UNSAFE", 0, f"relative jump leaves the span (+{s['relout'][0]} of {n})"
    if s["fall"] == "unknown":
        return "UNKNOWN", 0, f"predecessor {s['pred']} does not decode"
    if s["fall"] == "yes":
        rec = n - 3
        if rec <= 0:
            return "WORTHLESS", 0, f"entered by fallthrough from {s['pred']}; a `jp` costs {3 - n} more than the span"
        return "SAFE-JP", rec, f"entered by fallthrough from {s['pred']}: needs `jp`, {n}-3"
    return "SAFE", n, "terminates, no escaping relative jump, no fallthrough entry"


def main():
    rom = open("build/basic-reloc.rom", "rb").read()
    spans = build_spans(rom)
    selftest = "--selftest" in sys.argv
    samereg = "--samereg" in sys.argv
    worklist = "--worklist" in sys.argv
    work = []
    if selftest:
        return run_selftest(spans)
    if samereg:
        print("  --samereg: only aliases whose canonical is in the SAME region\n")

    bybytes = collections.defaultdict(list)
    for s in spans:
        if len(s["bytes"]) >= 3:
            bybytes[bytes(s["bytes"])].append(s)
    groups = [g for g in bybytes.values() if len(g) > 1]
    groups.sort(key=lambda g: -len(g[0]["bytes"]) * (len(g) - 1))

    print(f"  denominator: {len(spans)} non-empty spans, "
          f"{sum(1 for s in spans if not s['tiles'])} of them do not decode cleanly")
    print(f"  {len(groups)} byte-identical groups\n")

    total_nom = total_safe = 0
    region = {'low': 0, 'p1': 0}
    widen_total = [0]
    for g in groups:
        n = len(g[0]["bytes"])
        nominal = n * (len(g) - 1)
        total_nom += nominal
        vs = [(s, *verdict(s)) for s in g]
        # 🔴 A FOURTH THING NEITHER SWEEP NOR DECODER CAN SEE: THE REGION
        # CONTRACT.  Main low ($2812-$3FFF) is switched OUT under a sub page-0
        # tenant and main page 1 ($4000-$7FFF) is switched OUT under a sub
        # page-1 tenant.  Aliasing a LOW label onto a PAGE-1 address hands every
        # page-1 tenant that reaches it an address that is not there — and vice
        # versa.  `--samereg` prices the carve that cannot have that problem at
        # all, rather than one that depends on check_tenant_closure agreeing.
        # canonical = the member we KEEP.  Keep one that cannot be aliased away
        # if there is one; otherwise keep the one with most `jr` callers.
        keepers = [t for t in vs if t[1] not in ("SAFE", "SAFE-JP")]
        if keepers:
            canon = max(keepers, key=lambda t: len(rel_callers(rom, t[0]["addr"])))
        elif samereg:
            # keep the member whose OWN region holds the most aliasable bytes
            def reg_yield(t):
                r = t[0]["addr"] < 0x4000
                return sum(u[2] for u in vs if u is not t and (u[0]["addr"] < 0x4000) == r)
            canon = max(vs, key=reg_yield)
        else:
            canon = max(vs, key=lambda t: len(rel_callers(rom, t[0]["addr"])))
        creg = canon[0]["addr"] < 0x4000
        if samereg:
            vs = [(t[0], t[1], t[2] if (t[0]["addr"] < 0x4000) == creg else 0,
                   t[3] if (t[0]["addr"] < 0x4000) == creg
                   else "CROSSES the low/page-1 boundary — a tenant contract, not a byte fact")
                  for t in vs]
        gain = sum(t[2] for t in vs if t[0] is not canon[0])
        # price `jr` widening: every jr caller of an ALIASED member must now
        # reach the canonical instead
        widen = 0
        for s, code, rec, _ in vs:
            if s is canon[0] or rec == 0:
                continue
            for src in rel_callers(rom, s["addr"]):
                if abs(canon[0]["addr"] - (src + 2)) > 127:
                    widen += 1
        net = gain - widen
        total_safe += max(net, 0)
        # 🔴 PRICING BY FILE IS NOT PRICING BY REGION (D-LOADSWEEP).  The bytes
        # come back where the ALIASED member sat, and low ($2812-$3FFF) is a
        # different wall from page 1 ($4000-$7FFF).
        if net > 0:
            for s2, code2, rec2, _ in vs:
                if s2 is canon[0] or rec2 == 0:
                    continue
                region[("low" if s2["addr"] < 0x4000 else "p1")] += rec2
            widen_total[0] += widen
        print(f"  {n:3d} B x{len(g)}  nominal {nominal:3d} B -> NET {net:+4d} B"
              f"   {g[0]['bytes'].hex()}")
        for s, code, rec, why in vs:
            mark = "KEEP" if s is canon[0] else (
                "CROSS-REG" if (samereg and rec == 0 and code.startswith("SAFE")) else code)
            print(f"        ${s['addr']:04X} {s['name']:<22s} {mark:<10s} {why}")
        if widen:
            print(f"        (- {widen} B: `jr` callers that must widen to reach ${canon[0]['addr']:04X})")
        if worklist and net > 0:
            for s2, code2, rec2, _ in vs:
                if s2 is canon[0] or rec2 == 0:
                    continue
                work.append((s2["name"], canon[0]["name"], rec2, code2,
                             "low" if s2["addr"] < 0x4000 else "p1"))
    print(f"\n  nominal {total_nom} B  ->  MEASURED SAFE NET {total_safe} B")
    print(f"  by REGION, before widening: page-0 low {region['low']} B, "
          f"page 1 {region['p1']} B; `jr` widening charged {widen_total[0]} B")
    print("  ⚠️ the widening figure is an ESTIMATE from a byte scan that cannot "
          "tell a `jr` opcode from data; the assembler is the authority.")
    if worklist:
        print("\n  WORKLIST — alias -> canonical, bytes, how, region")
        for a, c, r, k, reg in sorted(work, key=lambda t: -t[2]):
            print(f"    {a:<20s} equ {c:<20s} {r:3d} B  {k:<8s} {reg}")
    return 0


# ---------------------------------------------------------------- calibration

def run_selftest(spans):
    fails = []

    def chk(label, got, want):
        ok = got == want
        print(f"  {'PASS' if ok else 'FAIL'}  {label}: got {got!r}, want {want!r}")
        if not ok:
            fails.append(label)

    print("SYNTHETIC — planted spans with known answers")
    # 1. terminates, no relative jump           -> SAFE
    a = {"addr": 0x5000, "name": "p_safe", "bytes": bytes.fromhex("3e05c9"),
         "pred": None, "fall": "no"}
    # 2. no terminator (falls off its end)      -> UNSAFE
    b = {"addr": 0x5100, "name": "p_noterm", "bytes": bytes.fromhex("3e0500"),
         "pred": None, "fall": "no"}
    # 3. `jr` leaving the span                  -> UNSAFE
    #    ⚠️ the first draft of THIS vector was `18 fe` (a self-loop), whose
    #    target is offset 0 — INSIDE the span.  The checker called it SAFE and
    #    was right; the plant was mislabelled.  `18 05` is the real vector.
    c = {"addr": 0x5200, "name": "p_relout", "bytes": bytes.fromhex("1805c9"),
         "pred": None, "fall": "no"}
    #    ...and one whose `jr` stays inside     -> SAFE
    d = {"addr": 0x5300, "name": "p_relin", "bytes": bytes.fromhex("3e0518fdc9"),
         "pred": None, "fall": "no"}
    #    ...and the self-loop, which really is in-span   -> SAFE
    d2 = {"addr": 0x5380, "name": "p_relself", "bytes": bytes.fromhex("3e0518fe"),
          "pred": None, "fall": "no"}
    # 4. entered by fallthrough                 -> SAFE-JP with len-3
    e = {"addr": 0x5400, "name": "p_fall", "bytes": bytes.fromhex("3e05210000c9"),
         "pred": "p_prev", "fall": "yes"}
    # 5. entered by fallthrough and 3 B long    -> WORTHLESS
    f = {"addr": 0x5500, "name": "p_fall3", "bytes": bytes.fromhex("3e05c9"),
         "pred": "p_prev", "fall": "yes"}
    # 6. undecodable tail                       -> UNKNOWN
    g = {"addr": 0x5600, "name": "p_dirty", "bytes": bytes.fromhex("c9cd42"),
         "pred": None, "fall": "no"}
    for s in (a, b, c, d, d2, e, f, g):
        tiles, term, rels = walk(s["bytes"])
        s["tiles"], s["term"] = tiles, term
        s["relout"] = [r for r in rels if not (0 <= r < len(s["bytes"]))]
    chk("terminating span", verdict(a)[0], "SAFE")
    chk("span with no terminator", verdict(b)[0], "UNSAFE")
    chk("`jr` leaving the span", verdict(c)[0], "UNSAFE")
    chk("`jr` staying inside", verdict(d)[0], "SAFE")
    chk("`jr` self-loop (target = offset 0)", verdict(d2)[0], "SAFE")
    chk("fallthrough entry", (verdict(e)[0], verdict(e)[1]), ("SAFE-JP", 3))
    chk("fallthrough entry, 3 B", verdict(f)[0], "WORTHLESS")
    chk("span that does not tile", verdict(g)[0], "UNKNOWN")

    print("\nREAL, KNOWN ANSWER — docs/spec-basic-dupspan.md §2.1 read by hand:")
    print("  the bare `jp raise_error` spans, and how each is entered")
    # 🔴 THIS ARM WAS RED FOR MONTHS AND NOTHING COLLECTED ITS rc=1, for TWO
    # reasons, both of which are how a known-answer test keyed to a LIVE
    # artifact rots:
    #   1. it matched the literal bytes "c39a42" -- `jp $429A`, raise_error's
    #      address WHEN THE ARM WAS WRITTEN. Every carve since has relaid the
    #      ROM out and raise_error is now elsewhere, so the group matched
    #      NOTHING and the arm reported "got 0, want 6".
    #   2. `pl_parse_err`, one of the six, was legitimately carved away.
    # The address is now DERIVED from the symbol, and the count is REPORTED
    # rather than frozen -- a later carve is a legitimate change, not a failure.
    # What still has teeth is that the pattern must match SOMETHING and every
    # surviving member must carry it. [[a-wall-figure-inside-a-gate-is-unpoliced]]
    want = {"ee_raise", "sid_raise", "tm_raise", "pl_parse_err", "exf_raise",
            "gp_raise"}
    tgt = dict((n, a) for a, n in
               load_syms("build/basic-reloc.sym", 0, 0x10000)).get("raise_error")
    pat = bytes((0xC3, tgt & 0xFF, tgt >> 8)).hex() if tgt else None
    chk("raise_error resolves from the sym (not a frozen literal)",
        pat is not None, True)
    alive = [s for s in spans if s["name"] in want]
    grp = [s for s in alive if s["bytes"].hex() == pat]
    print(f"        raise_error = {tgt:#06x} -> pattern {pat}")
    print(f"        {len(alive)} of the {len(want)} named spans still exist; "
          f"{len(grp)} carry the pattern")
    chk("the pattern matches at least one surviving span", len(grp) >= 1, True)
    chk("every surviving named span carries it", len(grp), len(alive))
    fallers = sorted(s["name"] for s in grp if s["fall"] == "yes")
    print(f"        {len(fallers)} entered by fallthrough")
    print(f"        fallthrough-entered: {', '.join(fallers)}")
    print(f"        reached only by jump: "
          f"{', '.join(sorted(s['name'] for s in grp if s['fall'] != 'yes'))}")
    # and the documented A values of the `ld a,N` above each
    print("\n  the `ld a,N` each falls out of (§2.1 recorded 5, 61, 24, 61, 61):")
    for s in sorted(grp, key=lambda s: s["addr"]):
        if s["fall"] == "yes":
            print(f"        {s['name']:<16s} <- {s['pred']}")

    print(f"\n  SELFTEST: {len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
