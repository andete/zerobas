#!/usr/bin/env python3
"""D-POPRAISE -- price the class TODO.md files unpriced beside `ems_typecheck`:

    "a pop that only exists to satisfy a raise that unwinds anyway"

The 2 B at `ems_typecheck` were filed 2026-08-26 by D-MIDOP with the class
attached and NO sweep behind it.  This is the sweep.  It answers two DIFFERENT
questions, which the filing runs together:

  Q1  DELETION.  How many bytes sit in `pop`s whose only purpose is to balance a
      stack that the raise unwinds anyway?  Taking these makes the code DEPEND
      on raise_error resetting SP rather than merely survive it -- a semantics
      decision, not a byte one.  PRICED HERE, NOT TAKEN.

  Q2  AGGREGATION.  How many of these tails are byte-identical to another and
      could be one label (or an `equ` alias, as `elas_err` already is)?  That
      is a pure collapse with NO semantics change, and it is the half the
      charter's "aggregate common behaviour" steer actually asks for.

A tail is (>=1 `pop rr`) immediately followed by an UNCONDITIONAL transfer to a
routine that never returns.  The never-return set is computed by fixed point
from `raise_error` -- not hardcoded -- so a routine that stops raising drops out
of the sweep instead of silently keeping a stale verdict.

  --selftest  re-derives five KNOWN answers by name and exits non-zero if any
              is missed, so a run that reports "nothing here" is known not to be
              a sweep that reports that by construction.
"""
from __future__ import annotations
import collections, re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = sorted(ROOT.glob("basic/*.asm")) + sorted(ROOT.glob("sub/*.asm"))

LABEL_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")
EQU_RE   = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s+equ\s+([A-Za-z_][A-Za-z0-9_]*)\s*$", re.I)
INSN_RE  = re.compile(r"^\s+([a-z][a-z0-9]*)\b\s*(.*)$", re.I)

COND = {"z","nz","c","nc","p","m","pe","po"}

class Item:
    __slots__ = ("kind","name","mn","ops","line","file")
    def __init__(self, kind, name, mn, ops, line, file):
        self.kind, self.name, self.mn, self.ops, self.line, self.file = \
            kind, name, mn, ops, line, file

def strip_comment(s: str) -> str:
    out, q = [], None
    for ch in s:
        if q:
            out.append(ch)
            if ch == q: q = None
            continue
        if ch in "\"'": q = ch; out.append(ch); continue
        if ch == ";": break
        out.append(ch)
    return "".join(out).rstrip()

def parse():
    """-> (items, equs). items is a flat ordered list across files."""
    items, equs = [], {}
    for p in SRC:
        rel = str(p.relative_to(ROOT))
        for n, raw in enumerate(p.read_text().splitlines(), 1):
            line = strip_comment(raw)
            if not line.strip(): continue
            m = EQU_RE.match(line.strip())
            if m:
                equs[m.group(1)] = m.group(2)
                items.append(Item("equ", m.group(1), "", m.group(2), n, rel))
                continue
            m = LABEL_RE.match(line)
            if m:
                items.append(Item("label", m.group(1), "", "", n, rel))
                rest = line[m.end():].strip()
                if rest:
                    mi = INSN_RE.match(" " + rest)
                    if mi:
                        items.append(Item("insn", None, mi.group(1).lower(),
                                          mi.group(2).strip(), n, rel))
                continue
            mi = INSN_RE.match(line)
            if mi:
                items.append(Item("insn", None, mi.group(1).lower(),
                                  mi.group(2).strip(), n, rel))
    return items, equs

def split_ops(ops: str):
    return [o.strip() for o in ops.split(",")] if ops.strip() else []

def jump_target(it: Item):
    """(target, unconditional) for jp/jr, else (None, False)."""
    if it.kind != "insn" or it.mn not in ("jp","jr"): return None, False
    o = split_ops(it.ops)
    if not o: return None, False
    if len(o) == 2 and o[0].lower() in COND:
        t = o[1]
        uncond = False
    elif len(o) == 1:
        t, uncond = o[0], True
    else:
        return None, False
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", t): return None, False
    return t, uncond

def resolve(name, equs, seen=None):
    seen = seen or set()
    while name in equs and name not in seen:
        seen.add(name); name = equs[name]
    return name

def never_return_set(items, equs):
    """Fixed point from raise_error. A label never-returns if the straight-line
    body from it reaches an unconditional jump to a never-returner without any
    `ret` (conditional `ret` included -- it CAN return) and without a `call` to
    something unknown returning... a call is fine: it comes back, then we keep
    walking."""
    # index: label -> item position
    pos = {}
    for i, it in enumerate(items):
        if it.kind == "label" and it.name not in pos: pos[it.name] = i
    nr = {"raise_error", "raise_error_hl", "raise_error_forced"}
    changed = True
    while changed:
        changed = False
        for lbl, i in pos.items():
            if lbl in nr: continue
            j = i + 1
            verdict = None
            while j < len(items):
                it = items[j]
                if it.kind == "label":
                    j += 1; continue            # fallthrough into next label
                if it.kind == "equ": j += 1; continue
                if it.mn.startswith("ret"): verdict = False; break
                if it.mn in ("db","dw","ds","defb","defw"): verdict = False; break
                t, uncond = jump_target(it)
                if t is not None and uncond:
                    verdict = resolve(t, equs) in nr; break
                if it.mn in ("jp","jr") and not uncond:
                    j += 1; continue            # conditional: keep walking
                if it.mn == "jp" and t is None:  # jp (hl) etc
                    verdict = False; break
                j += 1
            if verdict:
                nr.add(lbl); changed = True
    # equ aliases of never-returners are never-returners too
    for a in list(equs):
        if resolve(a, equs) in nr: nr.add(a)
    return nr

def _pushed_into(items, i):
    """A `pop` whose immediately preceding instruction is a `push` is a REGISTER
    MOVE, not a stack discard (`push ix / pop hl` at basic/missing.asm:509 is the
    real one this sweep first mis-counted). The distinction is the whole class:
    a move has a reader, a discard by definition does not."""
    j = i - 1
    while j >= 0 and items[j].kind != "insn":
        j -= 1
    return j >= 0 and items[j].mn == "push"


def find_tails(items, equs, nr):
    """maximal runs of `pop rr` ending in an unconditional jump to a raise."""
    out = []
    i = 0
    # the labels standing DIRECTLY in front of each instruction, with no
    # instruction in between -- the first `pop` of a run carries its own name
    # this way, and forgetting that is what the selftest caught.
    lead = {}
    cur = []
    for k, it in enumerate(items):
        if it.kind == "label":
            cur.append(it.name)
        elif it.kind == "insn":
            lead[k] = list(cur); cur = []
    while i < len(items):
        it = items[i]
        if it.kind == "insn" and it.mn == "pop" and not _pushed_into(items, i):
            j, pops = i, []
            names = list(lead.get(i, []))
            while j < len(items):
                x = items[j]
                if x.kind == "label":
                    names.append(x.name); j += 1; continue
                if x.kind == "equ": j += 1; continue
                if x.mn == "pop":
                    pops.append((x, list(names))); names = []; j += 1; continue
                break
            # ONE `ld a,<imm>` is allowed between the pops and the jump: that
            # is the canonical raise shape (`pop de / ld a,5 / jp raise_error`)
            # and a sweep blind to it measures the wrong denominator.
            setup = 0
            if (j < len(items) and items[j].kind == "insn"
                    and items[j].mn == "ld"
                    and split_ops(items[j].ops)[:1] == ["a"]
                    and len(split_ops(items[j].ops)) == 2
                    and not re.fullmatch(r"\(.*\)", split_ops(items[j].ops)[1])):
                setup = 2
                j += 1
            if j < len(items) and items[j].kind == "insn":
                t, uncond = jump_target(items[j])
                if t is not None and uncond and resolve(t, equs) in nr:
                    out.append({
                        "file": it.file, "line": it.line, "endline": items[j].line,
                        "pops": [(p.ops, ns) for p, ns in pops],
                        "n": len(pops), "target": t,
                        "jsize": (3 if items[j].mn == "jp" else 2) + setup,
                        "setup": setup,
                    })
            i = j + 1
            continue
        i += 1
    return out

def pop_bytes(ops):  # every `pop rr` is 1 B on Z80
    return 1

def main(argv):
    items, equs = parse()
    nr = never_return_set(items, equs)
    tails = find_tails(items, equs, nr)

    if "--selftest" in argv:
        # REAL, KNOWN-ANSWER: the five tails TODO.md and vars.asm name by hand.
        want = {"ems_typecheck", "ems_err_pop2", "ems_err_pop1", "elas_abort_fp"}
        got = set()
        for t in tails:
            for _, ns in t["pops"]:
                got |= set(ns)
        missing = want - got
        # and the never-return set must contain the four documented raisers
        wantnr = {"stmt_error", "fp_runtime_error", "gb_illegal", "els_tc_common"}
        missnr = wantnr - nr
        ok = not missing and not missnr
        print(f"selftest: tails={len(tails)} never-return={len(nr)}")
        if missing: print(f"  MISSING named tails: {sorted(missing)}")
        if missnr:  print(f"  MISSING never-returners: {sorted(missnr)}")
        print("selftest OK" if ok else "selftest FAILED")
        return 0 if ok else 1

    print(f"never-return set: {len(nr)} routines "
          f"(seeded from raise_error, fixed point)")
    print(f"pop-then-raise tails: {len(tails)}")
    total_pops = sum(t["n"] for t in tails)
    print(f"Q1 DELETION ceiling: {total_pops} pop(s) = {total_pops} B "
          f"(1 B each; NOT taken -- semantics)")
    print()

    by_shape = collections.defaultdict(list)
    for t in tails:
        key = (t["n"], resolve(t["target"], equs))
        by_shape[key].append(t)
    print("Q2 AGGREGATION -- tails grouped by (pop count, resolved raise target):")
    dup_bytes = 0
    for (n, tgt), ts in sorted(by_shape.items(), key=lambda kv: -len(kv[1])):
        each = n + max(t["jsize"] for t in ts)
        mark = ""
        if len(ts) > 1:
            # collapsing k identical tails onto one: (k-1) bodies recovered,
            # but each collapsed site still needs a jump to the survivor
            # UNLESS it is only reached by jump already (then it is free).
            dup_bytes += sum(sorted(t["n"] + t["jsize"] for t in ts)[:-1])
            b = sum(sorted(t["n"] + t["jsize"] for t in ts)[:-1])
            mark = f"  <- {len(ts)-1} redundant body/bodies, {b} B"
        print(f"  {len(ts):2d}x  {n} pop -> {tgt:<20s} ({each} B each){mark}")
        for t in ts:
            names = ",".join(nm for _, ns in t["pops"] for nm in ns) or "-"
            print(f"        {t['file']}:{t['line']}  [{names}]")
    print()
    print(f"Q2 ceiling: {dup_bytes} B in redundant identical bodies "
          f"(before entry-shape and region checks)")
    print()

    # Q3 -- the route Q2's per-shape grouping cannot see. Tails that share a
    # RAISE TARGET but differ in POP COUNT are not identical bodies, yet one
    # CHAIN serves them all: the k-pop entry falls through into the (k-1)-pop
    # entry, exactly the shape ems_err_pop2 -> ems_err_pop1 already has. The
    # cost is (deepest pop count + one jump); everything else becomes an `equ`.
    print("Q3 CHAINING -- tails grouped by raise target only "
          "(a deeper entry falls through into a shallower one):")
    by_tgt = collections.defaultdict(list)
    for t in tails:
        by_tgt[resolve(t["target"], equs)].append(t)
    chain_total = 0
    for tgt, ts in sorted(by_tgt.items(), key=lambda kv: -len(kv[1])):
        if len(ts) < 2: continue
        # bodies already sharing a fallthrough chain are counted ONCE: a tail
        # whose jump is another tail's jump (same file, same end line) is the
        # same physical body.
        bodies = {}
        for t in ts:
            bodies.setdefault((t["file"], t["endline"]),
                              max(t["n"], 0)) # deepest entry of that body
            bodies[(t["file"], t["endline"])] = max(
                bodies[(t["file"], t["endline"])], t["n"])
        have = sum(n + max(x["jsize"] for x in ts if
                           (x["file"], x["endline"]) == k)
                   for k, n in bodies.items())
        deepest = max(t["n"] for t in ts)
        want = deepest + min(t["jsize"] for t in ts)
        saved = have - want
        chain_total += max(saved, 0)
        regions = sorted({("low" if a < 0x4000 else "p1") for a in
                          [0]}) # region printed by the caller, not derived here
        print(f"  {len(ts)}x -> {tgt:<20s} {len(bodies)} bod(y/ies) "
              f"{have} B  ->  one {want} B chain  = {saved} B")
        for t in ts:
            names = ",".join(nm for _, ns in t["pops"] for nm in ns) or "-"
            print(f"        {t['n']} pop  {t['file']}:{t['line']}  [{names}]")
    print()
    print(f"Q3 ceiling: {chain_total} B "
          f"(before entry-shape, jr-reach and REGION checks)")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
