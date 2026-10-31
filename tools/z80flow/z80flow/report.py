# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Report machinery (core): turns an Analysis into counts, site lists and JSON.

Platform/program-specific sections are passed in by the caller as ready-made
markdown; this module only knows about the generic categories.
"""
from collections import Counter, defaultdict

from .analysis import NU, ZERO_M
from .decode import REAL, fmt_units

N_SITES = 20

STACK_KINDS = [
    ("exsp-local", "ex (sp),rr on a slot this routine pushed (tracked exactly)"),
    ("exsp-ra", "ex (sp),rr on the return address"),
    ("exsp-below-frame", "ex (sp),rr below the routine's frame"),
    ("ldsp-frame", "ld sp,rr to an address on the routine's own stack (a frame carved or released)"),
    ("exsp-below-frame-consumed", "ex (sp),rr below the frame on a slot every return consumes (harmless)"),
    ("pop-below-frame-consumed", "pop below the frame of a slot every return consumes (harmless)"),
    ("pop-below-frame-declared", "pop below the frame, covered by a declared stack-effect"),
    ("exsp-below-frame-declared", "ex (sp),rr below the frame, covered by a declared stack-effect"),
    ("exsp-unknown-depth", "ex (sp),rr at an unknown depth"),
    ("exsp-unknown-depth-declared", "ex (sp),rr at an unknown depth in a routine declared `stack-effect var`"),
    ("pop-ra", "pop of the return address"),
    ("pop-below-frame", "pop below the frame of a slot not every return consumes (unknown)"),
    ("ldsp-reset", "ld sp from a constant/cell (frame reset; path ends)"),
    ("ldsp-reg", "ld sp,rr (stack switch)"),
    ("adjsp", "inc sp / dec sp"),
    ("exit-stack-delta", "return that leaves SP changed for the caller (inferred stack effect)"),
    ("exit-callers-caller", "return through the caller's slot (to the caller's caller)"),
    ("ret-jump-const", "push-then-ret to a constant address (followed)"),
    ("jpind-const", "jp (rr) with a constant rr (followed)"),
    ("jpind-return-unknown-depth", "jp (rr) to its own return address at an unknown depth"),
    ("ret-push-jump", "ret with bytes still pushed, to a computed address"),
    ("ret-computed-jump", "ret through a replaced return-address slot"),
    ("ret-below-frame", "ret below the frame at an odd offset"),
    ("ret-unknown-depth", "ret at an unknown depth"),
    ("tail-unknown-depth", "tail jump at an unknown depth"),
    ("depth-conflict", "paths join with different stack depths (informational: the "
                       "unknown depth only matters where it is used, and those uses are listed)"),
    ("annotation-mismatch", "an annotation disagrees with what the tool sees"),
]


def unique_events(A):
    """kind -> {addr: (detail, [routine entries])}"""
    out = defaultdict(dict)
    for e, rec in A.frec.items():
        for k, a, d in rec["events"]:
            slot = out[k].setdefault(a, [d, []])
            slot[1].append(e)
    return out


def boundary_sites(A):
    """Every call/jump/rst in decoded code whose target is not analysed code."""
    rows = []
    for a, ins in sorted(A.code.items()):
        if ins.kind not in ("call", "rst", "jp", "jr", "djnz") or ins.target is None:
            continue
        t = ins.target
        o = A.boundary(t)
        if o is None:
            continue
        rows.append({"site": a, "target": t, "kind": ins.kind, "mnem": ins.mnem,
                     "class": o.kind, "name": o.name, "in_ram": o.in_ram, "patch_point": o.patch_point})
    return rows


def contract_row(A, e):
    c = A.contract(e)
    rec = A.frec[e]
    return {
        "entry": e, "name": A.p.exact_name(e), "why": A.entries.get(e),
        "status": A.status[e],
        "reasons": [{"kind": k, "at": A.p.name_of(a), "addr": a, "detail": d} for k, a, d in A.direct[e]],
        "via": A.p.exact_name(A.via[e]) if e in A.via else None,
        "boundaries": sorted(A.ext_trans.get(e, ())),
        "inline_skip": A.kmap.get(e, 0), "noreturn": rec["noreturn"],
        "stack_conventions": A.stack_conventions(e),
        "hook_sensitive": (e in A.hook_sensitive) if hasattr(A, "hook_sensitive") else None,
        "body_instrs": len(rec["nodes"]),
        "call_sites": len(A.callers_of_call.get(e, ())),
        "tail_sites": len(A.tailed.get(e, ())),
        "inputs": fmt_units(c["inputs"]), "clobbers": fmt_units(c["clobbers"]),
        "clobbers_normal_return": fmt_units(c["clobbers_normal"]),
        "outputs_used": (fmt_units(c["outputs_used"]) if (A.callers_of_call.get(e) or A.tailed.get(e))
                         else "(no static callers)"),
        "inputs_mask": c["inputs"], "clobbers_mask": c["clobbers"], "outputs_used_mask": c["outputs_used"],
    }


def root_causes(A):
    direct = {e for e, r in A.direct.items() if r}
    cause = Counter()
    for e, st in A.status.items():
        if st != "unknown-via-callee":
            continue
        seen = set()
        stack = [e]
        found = set()
        while stack:
            x = stack.pop()
            for d in A.deps[x]:
                if d in seen:
                    continue
                seen.add(d)
                if d in direct:
                    found.add(d)
                else:
                    stack.append(d)
        for f in found:
            cause[f] += 1
    return cause


def annotation_leverage(A, scope):
    cause = root_causes(A)
    direct = [e for e in A.direct if A.direct[e]]
    ranked = sorted(direct, key=lambda e: (-cause.get(e, 0), e))
    out = []
    for n in [0, 1, 3, 5, 10, 20, 40, len(ranked)]:
        if n > len(ranked):
            continue
        fixed = set(ranked[:n])
        unk = set(direct) - fixed
        changed = True
        while changed:
            changed = False
            for e in A.frec:
                if e not in unk and any(d in unk for d in A.deps[e]):
                    unk.add(e)
                    changed = True
        out.append((n, sum(1 for e in unk if scope(e))))
    return out


def summarize(A, in_scope=None):
    """Numbers for one pass. in_scope(addr) restricts routine/site counts (e.g. to zerobas code)."""
    p = A.p
    scope = in_scope or (lambda a: True)
    code_bytes = set()
    for a, ins in A.code.items():
        if scope(a):
            code_bytes.update(range(a, a + ins.length))
    span = sum(hi - lo + 1 for lo, hi in p.code_ranges)
    ents = [e for e in A.entries if scope(e)]
    st = Counter(A.status[e] for e in ents)
    ev = unique_events(A)
    S = {
        "candidate_roots": len(p.roots) + len(p.interrupt_entries),
        "accepted_roots": len(A.accepted), "rejected_roots": len(A.rejected),
        "instructions": sum(1 for a in A.code if scope(a)),
        "bytes_covered": len(code_bytes),
        "code_range_bytes": span,
        "routines": len(ents),
        "routine_kinds": dict(Counter(A.entries[e] for e in ents)),
        "status": dict(st),
        "rounds": A.rounds,
        "stack_events": {k: sum(1 for a in ev.get(k, {}) if scope(a)) for k, _ in STACK_KINDS},
    }
    jp = [(a, i) for a, i in A.code.items() if i.kind == "jpind" and scope(a)]
    resolved = set(ev.get("jpind-return", {})) | set(ev.get("jpind-const", {})) | \
        {a for a in ev.get("exit-stack-delta", {}) if A.code.get(a) and A.code[a].kind == "jpind"} | \
        ({a for a in A.p.annotations.targets} if A.p.annotations else set())
    S["indirect_jumps"] = {"total": len(jp), "resolved": sum(1 for a, _ in jp if a in resolved),
                           "unresolved": sum(1 for a, _ in jp if a not in resolved)}
    rst = Counter(i.target for a, i in A.code.items() if i.kind == "rst" and scope(a))
    S["rst"] = {f"${k:02X}": v for k, v in sorted(rst.items())}
    bs = [r for r in boundary_sites(A) if scope(r["site"])]
    S["boundary_sites_by_class"] = dict(Counter(r["class"] for r in bs))
    S["boundary_sites_total"] = len(bs)
    smc = [e for e in ents if A.inferred_k.get(e) is not None or e in A.kmap]
    S["stack_manipulating_callees"] = len([e for e in ents if e in A.kmap])
    S["inline_data_callees"] = len([e for e in ents if A.kmap.get(e)])
    S["inline_data_call_sites"] = sum(len(A.callers_of_call.get(e, ())) for e in ents if A.kmap.get(e))
    io = [(a, i) for a, i in A.code.items() if i.io and scope(a)]
    S["io_instructions"] = len(io)
    return S


def md_table(rows, head):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in rows:
        out.append("| " + " | ".join(str(x).replace("|", "\\|") for x in r) + " |")
    return "\n".join(out)


def render_pass(A, title, in_scope=None, io_name=None, extra=()):
    p = A.p
    scope = in_scope or (lambda a: True)
    S = summarize(A, in_scope)
    ev = unique_events(A)
    L = [f"## {title}", ""]
    for n in p.notes:
        L.append(f"- {n}")
    L.append("")
    L.append("### Totals")
    L.append("")
    L.append(md_table([
        ["candidate roots (symbols in range + declared entries)", S["candidate_roots"]],
        ["roots accepted as code (incl. derived call targets)", S["accepted_roots"]],
        ["roots rejected (bad decode, see below)", S["rejected_roots"]],
        ["routines (entries)", S["routines"]],
        ["instructions decoded", S["instructions"]],
        ["bytes covered by decoded instructions", f"{S['bytes_covered']} of {S['code_range_bytes']} in the code ranges"],
        ["discovery rounds (inline-skip feedback)", S["rounds"]],
    ], ["what", "count"]))
    L.append("")
    L.append("Routine entries by kind: " + ", ".join(f"{k}: {v}" for k, v in S["routine_kinds"].items()))
    L.append("")
    L.append("### Rejected roots")
    L.append("")
    rows = [[p.exact_name(r), f"${r:04X}", why] for r, (a, why) in sorted(A.rejected.items())]
    L.append(md_table(rows[:40], ["root", "addr", "reason"]) if rows else "none")
    L.append("")

    # (a) indirect jumps
    L.append("### (a) Indirect jumps `jp (hl)` / `jp (ix)` / `jp (iy)`")
    L.append("")
    ij = S["indirect_jumps"]
    L.append(f"{ij['total']} sites: {ij['resolved']} resolved (a return through the routine's own return "
             f"address, a constant, or declared targets), {ij['unresolved']} unresolved.")
    L.append("")
    rows = []
    for a, ins in sorted(A.code.items()):
        if ins.kind == "jpind" and scope(a):
            ann = A.p.annotations
            res = ("return" if a in ev.get("jpind-return", {}) else
                   "return, stack changed" if a in ev.get("exit-stack-delta", {}) else
                   "constant" if a in ev.get("jpind-const", {}) else
                   f"declared: {len(ann.site_targets(a)[1])} target(s)" if ann and a in ann.targets else
                   "UNRESOLVED")
            rows.append([p.name_of(a), f"${a:04X}", ins.mnem, res])
    L.append(md_table(rows[:N_SITES], ["site", "addr", "insn", "resolution"]))
    L.append("")

    # (b) stack-manipulating callees
    L.append("### (b) Stack-manipulating callees (touch their own return address)")
    L.append("")
    rows = []
    for e in sorted(A.kmap):
        if not scope(e) or e not in A.frec:
            continue
        inf = A.inferred_k.get(e, "n/a")
        dec = p.declared_inline.get(e, "-")
        rows.append([p.exact_name(e), f"${e:04X}", "?" if inf is None else inf, dec,
                     len(A.callers_of_call.get(e, ())), A.status[e]])
    L.append(f"{len(rows)} routines touch their return address (pop it, `ex (sp)` it, or return through it). "
             f"Of these, {S['inline_data_callees']} skip inline data after the call (inferred skip > 0), "
             f"with {S['inline_data_call_sites']} call sites. `?` = the inference could not settle the skip.")
    L.append("")
    rows.sort(key=lambda r: (-(r[2] not in (0, '?')), -r[4]))
    L.append(md_table(rows[:N_SITES], ["callee", "addr", "inferred skip", "declared skip", "call sites", "status"]))
    L.append("")

    # (c) stack tricks
    L.append("### (c) Stack tricks (unique sites)")
    L.append("")
    rows = []
    for k, desc in STACK_KINDS:
        n = S["stack_events"].get(k, 0)
        if n:
            rows.append([k, desc, n])
    L.append(md_table(rows, ["kind", "meaning", "sites"]))
    L.append("")
    for k, desc in STACK_KINDS:
        sites = [(a, v) for a, v in sorted(ev.get(k, {}).items()) if scope(a)]
        if not sites:
            continue
        L.append(f"<details><summary>{k}: {len(sites)} sites</summary>\n")
        L.append(md_table([[p.name_of(a), f"${a:04X}", v[0], ", ".join(sorted({p.exact_name(x) for x in v[1]})[:3])]
                           for a, v in sites[:N_SITES]], ["site", "addr", "detail", "in routine(s)"]))
        L.append("\n</details>\n")

    # (d)/(e) boundaries
    L.append("### (d)+(e) Control transfers leaving the analysed code")
    L.append("")
    bs = [r for r in boundary_sites(A) if scope(r["site"])]
    byc = Counter(r["class"] for r in bs)
    rows = []
    for c, n in byc.most_common():
        tg = Counter(r["name"] for r in bs if r["class"] == c)
        rows.append([c, n, len(tg), ", ".join(f"{t}×{m}" for t, m in tg.most_common(6))])
    L.append(md_table(rows, ["target class", "sites", "distinct targets", "top targets"]))
    L.append("")
    ram = [r for r in bs if r["in_ram"]]
    L.append(f"(e) Transfers into RAM: {len(ram)} sites "
             f"({sum(1 for r in ram if r['patch_point'])} to declared patch points (hooks), "
             f"{sum(1 for r in ram if not r['patch_point'])} to other RAM). "
             "Self-modifying code is not detected beyond this.")
    L.append("")
    L.append(md_table([[p.name_of(r["site"]), f"${r['site']:04X}", r["mnem"], r["class"]] for r in ram[:N_SITES]],
                      ["site", "addr", "insn", "class"]) if ram else "")
    L.append("")
    L.append("<details><summary>first sites of every class</summary>\n")
    for c, n in byc.most_common():
        L.append(f"**{c}**\n")
        L.append(md_table([[p.name_of(r["site"]), f"${r['site']:04X}", r["mnem"], r["name"]]
                           for r in bs if r["class"] == c][:N_SITES], ["site", "addr", "insn", "target"]))
        L.append("")
    L.append("</details>\n")

    # (f) rst
    L.append("### (f) RST vectors used")
    L.append("")
    L.append(", ".join(f"rst {k}: {v}" for k, v in S["rst"].items()) or "none")
    L.append("")

    if io_name:
        io = Counter(io_name(i.io[1]) + f" ({i.io[0]})" for a, i in A.code.items() if i.io and scope(a))
        L.append("### I/O instructions")
        L.append("")
        L.append(f"{S['io_instructions']} sites: " + ", ".join(f"{k}×{v}" for k, v in io.most_common()))
        L.append("")

    # status
    L.append("### Contract status")
    L.append("")
    L.append(md_table([[k, v] for k, v in sorted(S["status"].items())], ["status", "routines"]))
    L.append("")
    L.append("- **inferred**: every path decoded, every stack effect tracked, no boundary reached.")
    L.append("- **conservative-boundary**: as inferred, but it reaches a declared or external boundary "
             "whose effect is assumed (reads all / clobbers all unless declared).")
    L.append("- **unknown**: the routine itself has an unresolved site (reasons listed).")
    L.append("- **unknown-via-callee**: it calls or tail-jumps into an unknown routine.")
    L.append("")
    cause = root_causes(A)
    L.append("Directly-unknown routines ranked by how many other routines they make unknown:")
    L.append("")
    rows = []
    for e in sorted([e for e in A.direct if A.direct[e] and scope(e)], key=lambda e: -cause.get(e, 0)):
        r = A.direct[e]
        kinds = Counter(k for k, _, _ in r)
        rows.append([p.exact_name(e), cause.get(e, 0), ", ".join(f"{k}×{v}" for k, v in kinds.items()),
                     f"{p.name_of(r[0][1])}: {r[0][2]}"])
    L.append(md_table(rows[:30], ["routine", "poisons", "reasons", "first site"]))
    L.append("")
    lev = annotation_leverage(A, scope)
    L.append("Annotation leverage: if the top-N directly-unknown routines (ranked as above) each got a "
             "hand-written contract, how many routines in scope would still be unknown (direct or via callee):")
    L.append("")
    L.append(md_table([[n, u] for n, u in lev], ["N annotated", "still unknown"]))
    L.append("")
    for t, body in extra:
        L.append(f"### {t}")
        L.append("")
        L.append(body)
        L.append("")
    return "\n".join(L), S


def annotation_section(A):
    """Every annotation: where it applies, whether the tool could check it."""
    ann = A.p.annotations
    if ann is None:
        return "No annotation file."
    L = []
    vc = Counter(e.verdict() for e in ann.entries)
    L.append(f"{len(ann.entries)} annotations: " + ", ".join(f"{k} {v}" for k, v in sorted(vc.items())) +
             ". `checked`: the tool compared it with something it sees and it agrees (a declared "
             "depth or a concrete stack effect matches what the tool computes on paths it follows; "
             "a noreturn routine has no return on paths it followed completely) -- evidence, not "
             "proof; `trusted`: used, but nothing to compare it with beyond sanity checks (the site "
             "is the right kind of instruction, a table's targets decode as code, a `var` effect is "
             "consistent) -- these rest on the "
             "justification alone and are the ones to re-read after a source change; `unused`: never "
             "applied (stale, or outside this pass); `MISMATCH`: contradicts the analysis. "
             "`routines`: how many routines' analyses applied it.")
    L.append("")
    rows = []
    for e in ann.entries:
        det = "; ".join(d for _, d in e.checks)[:90]
        rows.append([e.kind, e.where + (f" (in={','.join(A.p.exact_name(x) for x in sorted(e.only))})" if e.only else ""),
                     " ".join(a for a in e.args if not a.startswith("in="))[:60], e.verdict(), len(e.used), det])
    L.append(md_table(rows, ["kind", "where", "args", "verdict", "routines", "check"]))
    if ann.errors:
        L.append("")
        L.append("Annotation file errors: " + "; ".join(f"{ln}: {m}" for ln, m in ann.errors))
    return "\n".join(L)


def stack_conventions_section(A, scope):
    rows = []
    for e in sorted(A.frec):
        if not scope(e):
            continue
        conv = A.stack_conventions(e)
        if conv:
            ann = A.p.annotations
            src = "declared" if ann and e in ann.stack_effect else "inferred"
            rows.append([A.p.exact_name(e), "; ".join(conv), src, len(A.callers_of_call.get(e, ())),
                         len(A.tailed.get(e, ()))])
    head = (f"{len(rows)} routines return in a way a contract must state (not a plain `ret` to RA+0 with "
            "the caller's stack untouched). `inferred` = the tool followed every path; `declared` = a "
            "`stack-effect` annotation stands in where it could not.")
    return head + "\n\n" + (md_table(rows, ["routine", "convention", "source", "call sites", "tail sites"])
                            if rows else "none")


def boundary_ranking(A, scope):
    """Coarse boundaries (assumed reads-all / clobbers-all) by how many in-scope
    routines reach them, and for how many each is the ONLY one."""
    reach = Counter()
    only = Counter()
    for e, st in A.status.items():
        if not scope(e) or st != "conservative-boundary":
            continue
        bs = A.ext_trans.get(e, set())
        for b in bs:
            reach[b] += 1
        if len(bs) == 1:
            only[next(iter(bs))] += 1
    rows = [[b, n, only.get(b, 0)] for b, n in reach.most_common()]
    return rows


def far_call_section(A, scope):
    """Far-call entries (CALSLT, call-back stubs) per call site: resolved into
    the routine they reach, or left as the entry's assumed effect."""
    sites = {a: v for a, v in A.far_resolved.items() if scope(a)}
    if not sites:
        return "none"
    res = {a: v for a, v in sites.items() if v[1]}
    L = [f"{len(sites)} call sites into a far-call entry ({', '.join(sorted({v[0] for v in sites.values()}))}); "
         f"{len(res)} resolved -- the target register folds to a constant (IX from `ld ix,nn`, an inline "
         "index byte read from the ROM, the slot from its RAM cell), so the call is followed into the "
         f"routine it reaches -- and {len(sites) - len(res)} left as the entry's assumed effect."]
    L.append("")
    tg = Counter()
    for a, (n, vs) in res.items():
        for v in vs:
            if v < 0:
                tg[(n, "(the hook's own boot content)", "-")] += 1
            else:
                tg[(n, A.p.exact_name(v), A.p.contexts.get(v >> 16, "?"))] += 1
    L.append(f"<details><summary>{len(tg)} distinct targets</summary>\n")
    L.append(md_table([[n, t, c, k] for (n, t, c), k in sorted(tg.items(), key=lambda x: (-x[1], x[0]))],
                      ["entry", "resolved target", "context", "sites"]))
    L.append("\n</details>\n")
    unres = sorted(a for a, v in sites.items() if not v[1])
    if unres:
        L.append("Not resolved: " + ", ".join(f"{A.p.name_of(a)} ({sites[a][0]})" for a in unres))
    return "\n".join(L)
