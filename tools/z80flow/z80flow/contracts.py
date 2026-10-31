# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Routine contracts of a zerobas build, and what changed between two builds.

    python3 -m z80flow.contracts show ZEROBAS NAME...   one routine's contract
    python3 -m z80flow.contracts dump ZEROBAS OUT.json  every routine's contract
    python3 -m z80flow.contracts diff BASE.json HEAD.json
    python3 -m z80flow.contracts diff-rev ZEROBAS REV   build REV in a scratch
                                                        tree, diff it with ZEROBAS

ZEROBAS is a zerobas tree with its build/ made (main ROM, basic-reloc.sym,
sub/sub2/disk ROMs with their .sym). The analysis is pass 2 (the whole image,
every context) with the `; z80flow:` markers of that tree's sources.

`diff` sorts every routine the two builds share (by name and context):

  broken              it changes a register it used to keep, and a caller
                      reads that register after the call on a normal path:
                      the finding to act on (exit status 1)
  broken_unwind_only  the same, but read only after an unwind (an error reset
                      or a restart through `stack-anchor ... unwind`): almost
                      always harmless, worth a look
  wider_in            it reads a register on entry it did not read before
                      (wider_in_unwind_only: only on an unwind path)
  status / exits      it became harder to analyse, or its exit shape changed
  more_clob / fewer_clob / narrower_in
                      interface changes no caller notices (confirmations)

What a contract covers: registers and flags, the stack, how a routine exits.
Not memory, not arithmetic: it complements the test battery, it does not
replace it.
"""
import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile

from . import program_zerobas as pz
from .analysis import Analysis
from .decode import fmt_units

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import probe_tmp                       # noqa: E402,F401 -- sets tempfile.tempdir (one temp root)


def analyse(zerobas_dir):
    p = pz.build(zerobas_dir, whole_image=True)
    A = Analysis(p).run()
    return p, A


def rows(p, A):
    V = A.normal_view()
    out = {}
    for e in A.frec:
        c = A.contract(e)
        cn = A.contract(e, V)
        name = p.exact_name(e) + " [" + p.contexts.get(e >> 16, "?") + "]"
        out[name] = {
            "status": A.status[e], "ctx": p.contexts.get(e >> 16),
            "inputs": c["inputs"], "clobbers": c["clobbers_normal"], "clobbers_all": c["clobbers"],
            "exit_live": A.L.get(e, 0), "inputs_normal": cn["inputs"], "exit_live_normal": cn["exit_live"],
            "exits": sorted(map(repr, A.frec[e]["exits"])),
            "ncall": len(A.callers_of_call.get(e, ())),
            "callers": sorted({p.exact_name(x) for x, _ in A.callers_of_call.get(e, ())} |
                              {p.exact_name(x) for x, _ in A.tailed.get(e, ())}),
        }
    return out


def annotation_rows(p):
    return [(x.kind, x.where, x.line, x.verdict()) for x in p.annotations.entries]


def dump(zerobas_dir, out):
    p, A = analyse(zerobas_dir)
    data = {"rows": rows(p, A), "errors": p.annotations.errors, "ann": annotation_rows(p)}
    with open(out, "w") as f:
        json.dump(data, f)
    return data


def _shapes(exits):
    # (level, x, k, delta): the flags an exit fixes are detail
    return sorted({repr(ast.literal_eval(k)[:4]) for k in exits})


def compare(A, B):
    """{category: [rows]} for the routines both builds have."""
    cat = {k: [] for k in ("broken", "broken_unwind_only", "wider_in", "wider_in_unwind_only", "status",
                           "exits", "more_clob", "fewer_clob", "narrower_in")}
    for n in sorted(A.keys() & B.keys()):
        x, y = A[n], B[n]
        if x["status"] != y["status"]:
            cat["status"].append((n, x["status"], y["status"]))
        if _shapes(x["exits"]) != _shapes(y["exits"]):
            cat["exits"].append((n, _shapes(x["exits"]), _shapes(y["exits"])))
        newc = y["clobbers"] & ~x["clobbers"]
        if newc:
            used = newc & y["exit_live"]
            normal = newc & y["exit_live_normal"]
            if normal and y["ncall"]:
                cat["broken"].append((n, f"now changes {fmt_units(newc)}; callers read "
                                      f"{fmt_units(normal)} after it", y["callers"][:8]))
            elif used and y["ncall"]:
                cat["broken_unwind_only"].append((n, f"now changes {fmt_units(newc)}; read only after "
                                                  f"an unwind: {fmt_units(used)}", y["callers"][:8]))
            else:
                cat["more_clob"].append((n, fmt_units(newc)))
        if x["clobbers"] & ~y["clobbers"]:
            cat["fewer_clob"].append((n, fmt_units(x["clobbers"] & ~y["clobbers"])))
        if y["inputs"] & ~x["inputs"]:
            w = y["inputs_normal"] & ~x["inputs_normal"]
            cat["wider_in" if w else "wider_in_unwind_only"].append((n, fmt_units(y["inputs"] & ~x["inputs"])))
        if x["inputs"] & ~y["inputs"]:
            cat["narrower_in"].append((n, fmt_units(x["inputs"] & ~y["inputs"])))
    return cat


def report(a, b, out=sys.stdout):
    A, B = a["rows"], b["rows"]
    cat = compare(A, B)
    print(f"{len(A.keys() & B.keys())} routines in both builds, {len(A.keys() - B.keys())} gone, "
          f"{len(B.keys() - A.keys())} new", file=out)
    for k, v in cat.items():
        print(f"  {k}: {len(v)}", file=out)
        full = k in ("broken", "broken_unwind_only", "wider_in", "wider_in_unwind_only", "status")
        for r in v if full else v[:5]:
            print("      ", *r, file=out)
        if not full and len(v) > 5:
            print(f"       ... {len(v) - 5} more", file=out)
    bad = [x for x in b["ann"] if x[-1] in ("MISMATCH", "unused")]
    for x in bad:
        print(f"  annotation {x[-1]}: {x[0]} at {x[2]}", file=out)
    for ln, msg in b["errors"]:
        print(f"  annotation error: {ln}: {msg}", file=out)
    return 1 if cat["broken"] or bad or b["errors"] else 0


def show(zerobas_dir, names):
    p, A = analyse(zerobas_dir)
    V = A.normal_view()
    for nm in names:
        hits = [e for e in A.frec if p.exact_name(e) == nm or p.exact_name(e).startswith(nm + "@")]
        if not hits:
            print(f"{nm}: no such routine")
            continue
        for e in hits:
            c, cn = A.contract(e), A.contract(e, V)
            print(f"{p.exact_name(e)} [{p.contexts.get(e >> 16)}]  {A.status[e]}")
            print(f"  reads on entry:   {fmt_units(c['inputs']) or '-'}")
            print(f"  changes:          {fmt_units(c['clobbers_normal']) or '-'}")
            print(f"  callers read after it: {fmt_units(cn['exit_live']) or '-'}"
                  f"   (incl. after an unwind: {fmt_units(A.L.get(e, 0)) or '-'})")
            ch = c["clobbers_normal"]
            print(f"  outputs callers use:    {fmt_units(cn['exit_live'] & ch) or '-'}")
            print(f"  a rewrite must keep:    {fmt_units(cn['exit_live'] & ~ch) or '-'} unchanged")
            cs = sorted({p.exact_name(x) for x, _ in A.callers_of_call.get(e, ())})
            print(f"  callers ({len(cs)}): {' '.join(cs[:20])}{' ...' if len(cs) > 20 else ''}")
    for ln, msg in p.annotations.errors:
        print(f"annotation error: {ln}: {msg}")


def build_rev(zerobas_dir, rev, cbios):
    """A scratch tree with REV's sources and their build/; returns its path."""
    d = tempfile.mkdtemp(prefix="z80flow-")
    arc = subprocess.run(["git", "-C", zerobas_dir, "archive", rev], check=True, capture_output=True).stdout
    subprocess.run(["tar", "-x", "-C", d], input=arc, check=True)
    # ROM builds only (no emulator): the argv is a literal list (tools/check_probe_preflight.py)
    r = subprocess.run(["make", "-C", d, "build/zerobas-main-eu.rom", "build/basic-reloc.sym", "build/sub.rom",
                        "build/sub2.rom", "build/disk.rom", "CBIOS=" + cbios], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"contracts: building {rev} failed:\n{r.stdout[-2000:]}{r.stderr[-2000:]}")
    return d


def main(argv):
    if len(argv) >= 2 and argv[0] == "show":
        show(argv[1], argv[2:])
        return 0
    if len(argv) == 3 and argv[0] == "dump":
        d = dump(argv[1], argv[2])
        print(f"{len(d['rows'])} routines -> {argv[2]}")
        return 0
    if len(argv) == 3 and argv[0] == "diff":
        return report(json.load(open(argv[1])), json.load(open(argv[2])))
    if len(argv) in (3, 4) and argv[0] == "diff-rev":
        cbios = argv[3] if len(argv) > 3 else os.path.expanduser("~/projects/cbios")
        base = build_rev(argv[1], argv[2], cbios)
        print(f"base {argv[2]} built in {base}", file=sys.stderr)
        try:
            a = {"rows": rows(*analyse(base))}
        finally:
            shutil.rmtree(base, ignore_errors=True)
        p, A = analyse(argv[1])
        b = {"rows": rows(p, A), "errors": p.annotations.errors, "ann": annotation_rows(p)}
        return report(a, b)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
