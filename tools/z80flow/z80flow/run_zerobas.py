# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Driver: measure the zerobas main ROM, two passes, one report.

    python3 -m z80flow.run_zerobas [--zerobas ~/projects/zerobas] [--out out]

Pass 1: zerobas code only ($2781..$7FFF); everything below is an external BIOS.
Pass 2: the whole merged image ($0000..$7FFF) as ONE program; only the MSX
        boundaries (inter-slot, hooks, ISR entry, I/O) remain declared.
Reads the zerobas tree; writes only to --out.
"""
import argparse
import hashlib
import json
import os
import time
from collections import Counter

from . import platform_msx, program_zerobas as pz
from .analysis import Analysis
from .decode import REAL, U, ALLF, m, fmt_units
from .report import (annotation_section, boundary_ranking, contract_row, far_call_section, md_table,
                     render_pass, stack_conventions_section)

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
OLD_REPORTS = [("v0", os.path.join(RESULTS, "2026-10-31", "report.json")),
               ("v1", os.path.join(RESULTS, "2026-10-31-v1", "report.json")),
               ("v2", os.path.join(RESULTS, "2026-10-31-v2", "report.json"))]

MAIN_REGS = m("A", "B", "C", "D", "E", "H", "L", "IXH", "IXL", "IYH", "IYL")
SHADOW = REAL & ~(MAIN_REGS | ALLF)


def regs_to_mask(regs):
    mk = 0
    for r in regs:
        if r == "IX":
            mk |= m("IXH", "IXL")
        elif r == "IY":
            mk |= m("IYH", "IYL")
        elif r == "F":
            mk |= ALLF
        else:
            mk |= m(r)
    return mk


def compare_comments(A, comments):
    rows = []
    for name, (regs, text, where) in sorted(comments.items()):
        e = A.p.byname.get(name)
        if e is None or e not in A.frec:
            continue
        cm = regs_to_mask(regs)
        # the comments describe the normal return; an abort exit (to the
        # caller's caller) is a separate part of the contract
        inf = A.clobbers(e, (0,)) if A.frec[e]["exits"] else A.clobbers(e)
        scope = MAIN_REGS | (ALLF if "F" in regs else 0)
        im = inf & scope
        cmm = cm & scope
        if im == cmm:
            v = "agree"
        elif im & ~cmm and cmm & ~im:
            v = "differ both ways"
        elif im & ~cmm:
            v = "tool says MORE"
        else:
            v = "tool says LESS"
        rows.append({"name": name, "entry": e, "where": where, "comment": text, "status": A.status[e],
                     "comment_regs": fmt_units(cmm), "inferred_regs": fmt_units(im),
                     "inferred_full": fmt_units(inf), "extra_in_tool": fmt_units(im & ~cmm),
                     "missing_in_tool": fmt_units(cmm & ~im), "verdict": v,
                     "truncated_comment": text.rstrip().endswith(",")})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zerobas", default=os.path.expanduser("~/projects/zerobas"))
    ap.add_argument("--out", default="out")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    t0 = time.time()

    p1 = pz.build(args.zerobas, whole_image=False)
    A1 = Analysis(p1).run()
    p2 = pz.build(args.zerobas, whole_image=True)
    A2 = Analysis(p2).run()
    # what-if: every hook left as the bare RET it is at boot
    # the upper bound: every hook may run anything (a patching program chains
    # the original, so a patched hook does its boot content PLUS anything)
    p3 = pz.build(args.zerobas, whole_image=True, hooks="open")
    A3 = Analysis(p3).run()
    zr = lambda a: pz.ZEROBAS_LO <= a <= pz.ZEROBAS_HI   # noqa: E731
    rom = p1.inputs
    sha = hashlib.sha1(open(rom["rom"], "rb").read()).hexdigest()
    symsha = hashlib.sha1(open(rom["sym"], "rb").read()).hexdigest()

    # ---- pass-1 extras ---------------------------------------------------
    kinds = pz.source_label_kinds(args.zerobas)
    xc = Counter()
    data_acc = []
    code_rej = []
    for a, n in p1.roots.items():
        k = kinds.get(n, "not in basic/*.asm")
        acc = a in A1.accepted
        xc[(k, "accepted" if acc else "rejected")] += 1
        if k == "data" and acc:
            data_acc.append(n)
        if k == "code" and not acc:
            code_rej.append(n)
    data_only = set()
    other = set()
    for r, seen in A1.accepted.items():
        bucket = data_only if (p1.roots.get(r) and kinds.get(p1.roots[r]) == "data") else other
        for a, ins in seen.items():
            bucket.update(range(a, a + ins.length))
    junk_bytes = len(data_only - other)
    x1 = ["Root acceptance against the SOURCE's own label kinds (label followed by db/dw/ds = data; "
          "never used as input, only to grade the decoder's data detection):", "",
          md_table([[k, s, v] for (k, s), v in sorted(xc.items())], ["source says", "tool", "roots"]), "",
          f"Data labels the tool still accepted as code: {', '.join(sorted(data_acc)) or 'none'}. "
          f"Bytes reachable ONLY from those roots (junk decodes counted as code above): {junk_bytes}.",
          f"Code labels the tool rejected: {', '.join(sorted(code_rej)) or 'none'}."]

    comments = pz.clobber_comments(args.zerobas)
    cmp1 = compare_comments(A1, comments)
    cmp2 = compare_comments(A2, comments)
    vc1 = Counter(r["verdict"] for r in cmp1)
    vc2 = Counter(r["verdict"] for r in cmp2)
    pick = [r for r in cmp2 if r["status"] == "inferred" and not r["truncated_comment"]]
    sample = pick[:: max(1, len(pick) // 10)][:10]
    x2 = [f"{len(comments)} `Clobbers` header comments parsed in basic/*.asm; {len(cmp1)} name a routine entry.",
          "Comparison is on A..L, IX, IY (flags only when the comment names them; shadow registers ignored).", "",
          md_table([[v, vc1.get(v, 0), vc2.get(v, 0)] for v in ["agree", "tool says MORE", "tool says LESS", "differ both ways"]],
                   ["verdict", "pass 1 (BIOS external)", "pass 2 (whole image)"]), "",
          "Restricted to routines whose pass-2 status is `inferred` (the others' contracts are not trusted):", "",
          md_table([[v, Counter(r["verdict"] for r in cmp2 if r["status"] == "inferred").get(v, 0)]
                    for v in ["agree", "tool says MORE", "tool says LESS", "differ both ways"]],
                   ["verdict", "inferred routines"]), "",
          "Sample of 10 routines whose pass-2 contract is fully inferred:", "",
          md_table([[r["name"], r["where"], r["comment"], r["inferred_regs"], r["verdict"]] for r in sample],
                   ["routine", "comment at", "comment says Clobbers", "tool infers", "verdict"])]

    def contract_sample(A, names):
        rows = []
        for n in names:
            e = A.p.byname.get(n)
            if e in A.frec:
                c = contract_row(A, e)
                rows.append([n, c["status"], c["inputs"], c["clobbers"], c["outputs_used"], c["inline_skip"]])
        return md_table(rows, ["routine", "status", "inputs (live-in)", "clobbers (may write)",
                               "outputs any caller reads", "inline skip"])

    show = ["skip_spaces", "inc_skip", "skip_comma", "abs16", "neg_de", "mul16", "sr_inl1", "sc_inl1",
            "subrom_call", "sc_call", "chrgtr", "raise_error", "print_string", "eval", "fp_add"]
    x3 = [contract_sample(A1, show)]

    def common(A, scope):
        br = boundary_ranking(A, scope)
        return [("Annotations", annotation_section(A)),
                ("Stack conventions in the contracts", stack_conventions_section(A, scope)),
                ("Far calls followed into the sub-ROMs (and back)", far_call_section(A, scope)),
                ("What keeps routines `conservative-boundary`",
                 "Boundaries whose effect is ASSUMED (reads all, clobbers all), by how many in-scope "
                 "`conservative-boundary` routines reach them, and for how many each is the only one "
                 "(stating that boundary's real contract would make those exact):\n\n" +
                 md_table(br[:25], ["boundary", "routines reaching it", "only boundary for"]))]

    md1, S1 = render_pass(A1, "Pass 1 -- zerobas code only ($2781..$7FFF; BIOS external)", zr,
                          platform_msx.io_name,
                          common(A1, zr) + [("Root validation vs source", "\n".join(x1)),
                           ("Inferred contracts vs `Clobbers` comments", "\n".join(x2)),
                           ("Some inferred contracts (pass 1)", "\n".join(x3))])

    # ---- pass-2 extras ---------------------------------------------------
    trans = Counter()
    became = []
    for e in A1.frec:
        if not zr(e):
            continue
        s1 = A1.status[e]
        s2 = A2.status.get(e, "not an entry in pass 2")
        trans[(s1, s2)] += 1
        if s1 == "conservative-boundary" and s2 == "inferred":
            became.append(p1.exact_name(e))
    ext1 = [e for e in A1.frec if zr(e) and A1.status[e] == "conservative-boundary"]
    bios_only = [e for e in ext1 if A1.ext_trans[e] and all(k.startswith("bios") or k == "zerobas page-0 island"
                                                              for k in A1.ext_trans[e])]
    res2 = [e for e in bios_only if A2.status.get(e) == "inferred"]
    narrowed = 0
    for e in A1.frec:
        if zr(e) and e in A2.frec:
            i1 = A1.contract(e)["inputs"]
            i2 = A2.contract(e)["inputs"]
            if i2 != i1 and (i2 & i1) == i2:
                narrowed += 1
    y1 = [f"Zerobas routines (entries in $2781..$7FFF) by status, pass 1 -> pass 2:", "",
          md_table([[a, b, v] for (a, b), v in sorted(trans.items())], ["pass 1", "pass 2", "routines"]), "",
          f"Pass-1 `conservative-boundary` zerobas routines: {len(ext1)}; of those, {len(bios_only)} reached "
          f"ONLY BIOS / island code (no inter-slot, hook or RAM boundary); {len(res2)} of those are fully "
          f"`inferred` in pass 2. Zerobas routines whose inferred inputs got strictly narrower: {narrowed}.",
          "", "Became inferred: " + ", ".join(sorted(became)[:60])]
    isr = A2.entries and 0x0038 in A2.frec
    y2 = []
    if isr:
        c = contract_row(A2, 0x0038)
        y2 = [f"$0038 ISR: status {c['status']}, clobbers (must be none for an ISR) `{c['clobbers']}`, "
              f"boundaries reached: {', '.join(c['boundaries']) or 'none'}; reasons: "
              f"{'; '.join(r['at'] + ' ' + r['detail'] for r in c['reasons'][:4]) or '-'}"]
    bs = Counter()
    for a, ins in A2.code.items():
        if ins.kind in ("call", "rst", "jp", "jr") and ins.target is not None:
            o = A2.boundary(ins.target)
            if o is not None:
                bs[(o.kind, o.name if o.kind in ("inter-slot",) else o.kind)] += 1
    y3 = ["Boundaries that remain in the whole-image pass (all sites, C-BIOS + zerobas):", "",
          md_table([[k, n, v] for (k, n), v in bs.most_common()], ["class", "target", "sites"])]
    # how much of each pass-2 contract depends on no program patching a hook
    def ckey(A, e):
        c = A.contract(e)
        return (c["inputs"], c["clobbers"], tuple(sorted(A.frec[e]["exits"], key=repr)), A.status[e])
    A2.hook_sensitive = {e for e in A2.frec if e in A3.frec and ckey(A2, e) != ckey(A3, e)}
    hk = Counter()
    for e in A2.frec:
        ctx = "main" if not e >> 16 else "sub-ROMs"
        hk[(ctx, A2.status[e], e in A2.hook_sensitive)] += 1
    hook_rows = []
    for ctx in ("main", "sub-ROMs"):
        for st in ("inferred", "conservative-boundary"):
            hook_rows.append([ctx, st, hk.get((ctx, st, False), 0), hk.get((ctx, st, True), 0)])
    open_st = Counter(A3.status[e] for e in A3.frec if not e >> 16)
    y_hooks = ("Hook policy of this run (\"practice\"): any program may patch any hook, but besides the "
               "interrupt hooks H_KEYI / H_TIMI that is rare, so a hook is taken as its boot content (a "
               "bare `ret`) except those two, which may run anything. zerobas's own H_ZKEY ($FFCF) is "
               "followed into the `zkey_hook` zerobas installs there, and each hook disk.rom claims "
               "at INIT (its hook_tab, plus HPHYD) is followed into its disk.rom handler OR taken as "
               "the bare `ret` (a disk machine and a diskless one: both). A program that patches a hook "
               "chains the original, so a patched hook does its boot content PLUS anything: the second "
               "run below takes every hook as \"may run anything\" (the upper bound). A routine whose "
               "contract (inputs, clobbers, exits, status) differs between the two runs is "
               "**hook-sensitive**: its contract holds only while nobody patches the hooks it reaches. "
               "The report.json rows carry the flag.\n\n" +
               md_table(hook_rows, ["context", "status (practice)", "hook-independent", "hook-sensitive"]) +
               f"\n\nWith every hook open, the main context has {open_st.get('inferred', 0)} inferred and "
               f"{open_st.get('conservative-boundary', 0)} conservative-boundary routines.")

    md2, S2 = render_pass(A2, "Pass 2 -- whole merged image ($0000..$7FFF) as one program", None,
                          platform_msx.io_name,
                          common(A2, lambda a: True) + [("Hooks: policy and sensitivity", y_hooks),
                                                        ("Effect on the zerobas routines", "\n".join(y1)),
                           ("Interrupt entry", "\n".join(y2) or "n/a"),
                           ("Remaining boundaries", "\n".join(y3)),
                           ("Some inferred contracts (pass 2)", contract_sample(A2, show))])
    S2z = render_pass(A2, "x", zr)[1]

    # earlier runs, counted from their report.json routine lists (v0 / v1:
    # main ROM only; from v2 on every context is listed in pass 2)
    def counts(routines, main_only):
        return Counter(r["status"] for r in routines if not (main_only and int(r["entry"]) >> 16))
    olds = []
    for tag, path in OLD_REPORTS:
        if os.path.exists(path):
            j = json.load(open(path))
            olds.append((tag, counts(j["pass1"]["routines"], True), counts(j["pass2"]["routines"], True),
                         counts(j["pass2"]["routines"], False)))

    def unk(st):
        return st.get("unknown", 0) + st.get("unknown-via-callee", 0)

    def stat(A, main_only):
        return Counter(A.status[e] for e in A.frec if not (main_only and e >> 16))
    now = ("v3", stat(A1, True), stat(A2, True), stat(A2, False))
    runs = olds + [now]
    kinds = ["inferred", "conservative-boundary", "unknown", "unknown-via-callee", "inlined"]
    cmp_rows = []
    for k in kinds + ["unknown, direct + via callee"]:
        f = unk if k.startswith("unknown,") else (lambda c, k=k: c.get(k, 0))
        cmp_rows.append([k] + [f(r[1]) for r in runs] + [f(r[2]) for r in runs] +
                        [f(r[3]) for r in runs if r[0] not in ("v0", "v1")])
    cmp_head = (["status"] + [f"{r[0]} p1 main" for r in runs] + [f"{r[0]} p2 main" for r in runs] +
                [f"{r[0]} p2 all" for r in runs if r[0] not in ("v0", "v1")])
    ctx_rows = []
    for A, label in ((A1, "pass 1"), (A2, "pass 2")):
        for cid, cname in sorted(A.p.contexts.items()):
            st = Counter(A.status[e] for e in A.frec if e >> 16 == cid)
            ctx_rows.append([label, cname, sum(st.values())] +
                            [st.get(k, 0) for k in ["inferred", "conservative-boundary", "unknown",
                                                    "unknown-via-callee", "inlined"]])
    inputs = {}
    for k in ("sub.rom", "sub.sym", "sub2.rom", "sub2.sym", "disk.rom", "disk.sym"):
        fp = os.path.join(args.zerobas, "build", k)
        if os.path.exists(fp):
            inputs[k] = hashlib.sha1(open(fp, "rb").read()).hexdigest()
    head = [
        "# z80flow v3 measurement: zerobas main ROM, sub-ROMs and disk ROM", "",
        f"- ROM: `{rom['rom']}` ({rom['rom_len']} bytes, sha1 {sha})",
        f"- symbols: `{rom['sym']}` (sha1 {symsha})",
        "- other ROMs: " + ", ".join(f"`build/{k}` (sha1 {v})" for k, v in inputs.items()),
        f"- generated in {time.time() - t0:.1f} s by `python3 -m z80flow.run_zerobas`", "",
        "- annotations: the `; z80flow:` markers in the zerobas sources (both passes), annotations/cbios-in-zerobas.ann (pass 2 "
        f"only) -- {len(p1.annotations.entries)} / {len(p2.annotations.entries)} entries in pass 1 / 2", "",
        "Routine status per run. v0 and v1 analysed the main ROM alone; v2 added build/sub.rom and "
        "build/sub2.rom as contexts of their own and the hook policy; v3 adds build/disk.rom (and "
        "the hooks it claims). `main` counts the main-ROM context only (comparable across all runs), "
        "`all` every context. The ROMs changed between runs (sha1s above and in each report), so "
        "counts move a little for that reason too.", "",
        md_table(cmp_rows, cmp_head),
        "", "Per context (each slot mapping is analysed as its own address space):", "",
        md_table(ctx_rows, ["pass", "context", "routines", "inferred", "conservative", "unknown", "via callee",
                            "inlined"]), "",
        "Pass 2 restricted to zerobas addresses, for direct comparison with pass 1:", "",
        md_table([[k, S1["status"].get(k, 0), S2z["status"].get(k, 0)]
                  for k in ["inferred", "conservative-boundary", "unknown", "unknown-via-callee"]],
                 ["status", "pass 1", "pass 2 (zerobas part)"]), ""]
    with open(os.path.join(args.out, "report.md"), "w") as f:
        f.write("\n".join(head) + "\n" + md1 + "\n\n" + md2 + "\n")

    def dump(A, scope):
        return {
            "routines": [{k: v for k, v in contract_row(A, e).items()} for e in sorted(A.frec) if scope(e)],
            "rejected_roots": [{"root": A.p.exact_name(r), "addr": r, "reason": w} for r, (_, w) in sorted(A.rejected.items())],
        }
    J = {"inputs": {"rom": rom["rom"], "rom_sha1": sha, "sym": rom["sym"], "sym_sha1": symsha, **inputs},
         "pass1": {"summary": S1, **dump(A1, zr), "comment_comparison": cmp1},
         "pass2": {"summary": S2, "summary_zerobas_part": S2z, **dump(A2, lambda a: True),
                   "comment_comparison": cmp2,
                   "status_transitions": [{"pass1": a, "pass2": b, "n": v} for (a, b), v in trans.items()]}}
    with open(os.path.join(args.out, "report.json"), "w") as f:
        json.dump(J, f, indent=1, default=str)
    print(f"wrote {args.out}/report.md and {args.out}/report.json in {time.time() - t0:.1f} s")
    print("pass1", S1["status"], "pass2", S2["status"])


if __name__ == "__main__":
    main()
