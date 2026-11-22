#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""cbios_review -- run zerobas's machine-code BIOS suite on a C-BIOS build (a release candidate under review).

The suite is everything that needs no zerobas BASIC: every BIOS spec page's rules (probes/bios/spec/*_rules.py),
re-run live on the candidate on each page's rows; the BIOS ladder (probes/bios/biosl_run.py --all); initslot; and
play_trace. The reference side stays each page's committed VG-8020 measurement; for every rule the candidate fails,
the page's probes are also run on the NMS 8250, and each differing field is classed: does the NMS 8250 (and does
zerobas) side with the VG-8020 or with the candidate?

The test machines copy zerobas's repack machines (slot layout unchanged, so every probe runs as it is): the
candidate's main + logo ROM in slot 0, RAM in 3-0, and for the disk row zerobas's own disk ROM in 3-1 (no sub ROM,
no BASIC). They are written to ~/.openMSX/share/machines as CBIOSREV_<TAG>_NODISK / _DISK and removed by `clean`.

    python3 -u tools/cbios_review.py machines --cbios ~/projects/cbios --tag rc2   # after `make` there
    python3 -u tools/cbios_review.py spec     --tag rc2 [MODULE_rules.py ...]
    python3 -u tools/cbios_review.py nms      --tag rc2        # the NMS 8250 on every page the candidate fails
    python3 -u tools/cbios_review.py fields   --tag rc2 [--detail]
    python3 -u tools/cbios_review.py ladder   --tag rc2        # biosl --all on both rows, then initslot
    python3 -u tools/cbios_review.py playtrace --tag rc2       # VG-8020 vs the candidate, scenario by scenario
    python3 -u tools/cbios_review.py all      --cbios ~/projects/cbios --tag rc2
    python3 -u tools/cbios_review.py clean    --tag rc2        # removes the two machine files

Everything lands in build/cbios_review/<TAG>/ (ignored): roms/, live_zerobas/, live_cand/, live_nms/, spec.json,
nms.json, fields.out, ladder.out, initslot.out, playtrace.out. zerobas's side needs a fresh `make repack-machine`.
CLEAN-ROOM: only the probes' own captures are read, as in spec_live.
"""
import argparse
import builtins
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "probes", "bios"))
os.chdir(ROOT)
import spec_live  # noqa: E402
import spec_rules  # noqa: E402
import biosl_run  # noqa: E402

MACHINES = os.path.expanduser("~/.openMSX/share/machines")
SPEC_DIR = os.path.join(ROOT, "probes", "bios", "spec")
SCR = os.path.join(ROOT, "scratchpad")
NMS = "Philips_NMS_8250"
CAPREF = re.compile(r"^  CAP ref : [0-9a-fA-F]+$")


def out_dir(tag):
    d = os.path.join(ROOT, "build", "cbios_review", tag)
    os.makedirs(d, exist_ok=True)
    return d


def mname(tag, row):
    return f"CBIOSREV_{tag.upper()}_{row}"


# ---- machines ---------------------------------------------------------------------------------------------------

def cmd_machines(a):
    od = out_dir(a.tag)
    rd = os.path.join(od, "roms")
    os.makedirs(rd, exist_ok=True)
    bin_ = os.path.join(os.path.expanduser(a.cbios), "derived", "bin")
    for f in ("cbios_main_msx1_eu.rom", "cbios_logo_msx1.rom"):
        shutil.copy(os.path.join(bin_, f), rd)
    shutil.copy(os.path.join(ROOT, "build", "disk.rom"), os.path.join(rd, "zerobas_disk.rom"))
    src = open(os.path.join(MACHINES, "C-BIOS_MSX1_EU_REPACK_DISK.xml")).read()
    s = src.replace(os.path.join(ROOT, "build", "zerobas-main-eu.rom"), os.path.join(rd, "cbios_main_msx1_eu.rom"))
    s = re.sub(r"<filename>[^<]*cbios_logo_msx1\.rom</filename>",
               f"<filename>{os.path.join(rd, 'cbios_logo_msx1.rom')}</filename>", s)
    s = s.replace(os.path.join(ROOT, "build", "disk.rom"), os.path.join(rd, "zerobas_disk.rom"))
    s = re.sub(r'<secondary slot="2">.*?</secondary>', '<secondary slot="2"/>', s, flags=re.S)
    s = re.sub(r"<code>[^<]*</code>", f"<code>C-BIOS review {a.tag} + zerobas disk ROM</code>", s)
    if any(os.path.join(ROOT, "build", f) in s for f in ("zerobas-main-eu.rom", "disk.rom", "sub.rom")):
        sys.exit("FAIL: a zerobas build path is left in the machine (the repack machine's layout changed?)")
    open(os.path.join(MACHINES, mname(a.tag, "DISK") + ".xml"), "w").write(s)
    n = re.sub(r'<secondary slot="1">.*?</secondary>', '<secondary slot="1"/>', s, flags=re.S)
    open(os.path.join(MACHINES, mname(a.tag, "NODISK") + ".xml"), "w").write(n)
    shas = {f: hashlib.sha256(open(os.path.join(rd, f), "rb").read()).hexdigest() for f in sorted(os.listdir(rd))}
    rev = subprocess.run(["git", "-C", os.path.expanduser(a.cbios), "log", "--oneline", "-1"],
                         capture_output=True, text=True).stdout.strip()
    json.dump({"cbios": rev, "sha256": shas}, open(os.path.join(od, "roms.json"), "w"), indent=1)
    print(f"machines {mname(a.tag, 'NODISK')} / {mname(a.tag, 'DISK')}; C-BIOS {rev}")
    for f, h in shas.items():
        print(f"  {f}  {h}")


def cmd_clean(a):
    for row in ("NODISK", "DISK"):
        p = os.path.join(MACHINES, mname(a.tag, row) + ".xml")
        if os.path.exists(p):
            os.remove(p)
            print("removed", p)


# ---- spec: every rule, live on zerobas and on the candidate ---------------------------------------------------

def modules(names):
    return [os.path.join(SPEC_DIR, n) for n in names] if names else sorted(
        os.path.join(SPEC_DIR, f) for f in os.listdir(SPEC_DIR) if f.endswith("_rules.py"))


def cmd_spec(a):
    od = out_dir(a.tag)
    sides = {"zerobas": {"nodisk": "C-BIOS_MSX1_EU_REPACK_NODISK", "disk": "C-BIOS_MSX1_EU_REPACK_DISK",
                         "cf3300": "C-BIOS_MSX1_EU_REPACK_DISK"},
             "cand": {"nodisk": mname(a.tag, "NODISK"), "disk": mname(a.tag, "DISK"),
                      "cf3300": mname(a.tag, "DISK")}}
    orig = dict(biosl_run.ROWS)
    redirect = {s: {} for s in sides}
    jp = os.path.join(od, "spec.json")
    result = json.load(open(jp)) if a.modules and os.path.exists(jp) else {}
    for path in modules(a.modules):
        _, _, files = spec_live.evaluate(path, {})
        entry = {}
        for side, rows in sides.items():
            td = os.path.join(od, "live_" + side)
            os.makedirs(td, exist_ok=True)
            for r, m in rows.items():
                biosl_run.ROWS[r] = (orig[r][0], m)
            noread = []
            for f in sorted(files):
                if f not in redirect[side]:
                    live = spec_live.live_run(f, td)
                    if live is None:
                        noread.append(os.path.basename(f))
                        continue
                    redirect[side][f] = live
            mod, fails, _ = spec_live.evaluate(path, redirect[side])
            entry[side] = {"fails": {r: bad for r, bad in fails.items() if bad}, "nrules": len(fails),
                           "noread": noread}
        biosl_run.ROWS.update(orig)
        entry["page"] = mod.PAGE
        entry["listed"] = sorted(spec_live.page_listed(mod))
        result[os.path.basename(path)] = entry
        zf, cf = set(entry["zerobas"]["fails"]), set(entry["cand"]["fails"])
        print(f"{os.path.basename(path)}: {entry['zerobas']['nrules']} rules; zerobas fails {sorted(zf)}; "
              f"candidate fails {sorted(cf)}; noread zb={entry['zerobas']['noread']} "
              f"cand={entry['cand']['noread']}", flush=True)
        json.dump(result, open(jp, "w"), indent=1)
    print("===== spec done =====")


# ---- nms: the NMS 8250's reading of every page the candidate fails -------------------------------------------

def nms_copy(run_file, od, cache):
    """The candidate's live copy of RUN_FILE with the NMS 8250's capture in the `CAP ref` (and `PRN ref`) slots."""
    td = os.path.join(od, "live_nms")
    os.makedirs(td, exist_ok=True)
    src = os.path.join(od, "live_cand", os.path.basename(run_file))
    if not os.path.exists(src):
        return None
    lines = open(src).read().splitlines(keepends=True)
    heads = [i for i, ln in enumerate(lines) if spec_live.HEADER.search(ln)]
    for n, h in enumerate(heads):
        end = heads[n + 1] if n + 1 < len(heads) else len(lines)
        asm = spec_live.HEADER.search(lines[h]).group(1)
        if asm not in cache:
            st = biosl_run.settings(open(asm).read())
            rom = biosl_run.build(asm, td)
            g = biosl_run.run(NMS, rom, st, td, disk=True)
            if not g or g.get("DONE") != "165":
                print(f"  NMS NO READING {asm} (DONE {g and g.get('DONE')}): the VG-8020's ref kept", flush=True)
                cache[asm] = None
            else:
                b = bytes.fromhex(g["CAP"])
                cache[asm] = (b[:max(32, len(b.rstrip(b'\0')))].hex(), g.get("PRN"))
        for i in range(h, end):
            if CAPREF.match(lines[i].rstrip("\n")) and cache[asm] is not None:
                lines[i] = f"  CAP ref : {cache[asm][0]}\n"
            elif lines[i].startswith("  PRN ref :") and cache[asm] and cache[asm][1] is not None:
                lines[i] = f"  PRN ref : {cache[asm][1]}\n"
    p = os.path.join(td, os.path.basename(run_file))
    open(p, "w").write("".join(lines))
    return p


def rules_on(path, redirect):
    real = builtins.open

    def op(f, *x, **k):
        p = os.path.abspath(f) if isinstance(f, str) else f
        return real(redirect[p], *x, **k) if isinstance(p, str) and p in redirect else real(f, *x, **k)
    for name in [n for n in sys.modules if n.endswith("_cases") or n.endswith("_model")]:
        del sys.modules[name]
    builtins.open = op
    try:
        mod = spec_rules.load(path)
        out, _, _ = spec_rules.run(mod)
    finally:
        builtins.open = real
    return {r.id: (bool(ref_bad), zb_bad) for r, _, ref_bad, zb_bad in out}


def cmd_nms(a):
    od = out_dir(a.tag)
    spec = json.load(open(os.path.join(od, "spec.json")))
    names = a.modules or sorted(n for n, e in spec.items() if e["cand"]["fails"])
    res, redirect, cache = {}, {}, {}
    for name in names:
        path = os.path.join(SPEC_DIR, name)
        _, _, files = spec_live.evaluate(path, {})
        ok = True
        for f in sorted(files):
            if f not in redirect:
                c = nms_copy(f, od, cache)
                if c is None:
                    ok = False
                    break
                redirect[f] = c
        if not ok:
            res[name] = "NO READING"
            continue
        r = rules_on(path, redirect)
        res[name] = {k: {"nms_fails": v[0]} for k, v in r.items()}
        print(name, {k: "NMS fails" if v[0] else "NMS holds" for k, v in r.items()}, flush=True)
        json.dump(res, open(os.path.join(od, "nms.json"), "w"), indent=1)
    print("===== nms done =====")


# ---- fields: per failing rule, who sides with whom ------------------------------------------------------------

def cases_from(path, live_dir):
    real = builtins.open

    def op(f, *x, **k):
        p = os.path.abspath(f) if isinstance(f, str) else f
        if isinstance(p, str) and p.startswith(SCR + os.sep) and p.endswith(".out"):
            alt = os.path.join(live_dir, os.path.basename(p))
            if os.path.exists(alt):
                return real(alt, *x, **k)
        return real(f, *x, **k)
    for name in [n for n in sys.modules if n.endswith("_cases") or n.endswith("_model")]:
        del sys.modules[name]
    builtins.open = op
    try:
        mod = spec_rules.load(path)
        cs = mod.cases()
    finally:
        builtins.open = real
    return mod, cs


def fmt(v):
    if isinstance(v, (bytes, bytearray)):
        return v.hex()
    if isinstance(v, int):
        return f"{v:#04x}" if v >= 0 else str(v)
    s = repr(v)
    return s if len(s) < 70 else s[:67] + "..."


def cmd_fields(a):
    od = out_dir(a.tag)
    spec = json.load(open(os.path.join(od, "spec.json")))
    for name in a.modules or sorted(n for n, e in spec.items() if e["cand"]["fails"]):
        path = os.path.join(SPEC_DIR, name)
        mod, A = cases_from(path, os.path.join(od, "live_zerobas"))
        _, B = cases_from(path, os.path.join(od, "live_cand"))
        try:
            _, C = cases_from(path, os.path.join(od, "live_nms"))
            nms = {c.id: c for c in C["ref"]} if os.path.isdir(os.path.join(od, "live_nms")) else {}
        except Exception:                                   # noqa: BLE001 -- no NMS reading for this page
            nms = {}
        vg = {c.id: c for c in A["ref"]}
        zb = {c.id: c for c in A["zb"]}
        cand = {c.id: c for c in B["zb"]}
        print(f"##### {name} ({mod.PAGE})")
        for rid, bad in spec[name]["cand"]["fails"].items():
            r = next(x for x in mod.RULES if x.id == rid)
            print(f"  == {rid}: {r.text[:300]}")
            print(f"     candidate fails {len(bad)} case(s); zerobas fails "
                  f"{len(spec[name]['zerobas']['fails'].get(rid, []))}")
            cn, cz, shown = Counter(), Counter(), 0
            for cid in bad:
                if cid not in vg or cid not in cand:
                    continue
                fv, fr = vars(vg[cid]), vars(cand[cid])
                for k in [k for k in fv if k != "id" and fv.get(k) != fr.get(k)]:
                    z = vars(zb[cid]).get(k) if cid in zb else None
                    cz["ZB=VG" if z == fv[k] else "ZB=CAND" if z == fr.get(k) else "ZB other"] += 1
                    n = vars(nms[cid]).get(k) if cid in nms else "n/a"
                    cn["NMS n/a" if cid not in nms else "NMS=VG" if n == fv[k] else
                       "NMS=CAND" if n == fr.get(k) else "NMS other"] += 1
                    if shown < (3 if a.detail else 1):
                        print(f"     e.g. {cid} {k}: VG {fmt(fv[k])} | CAND {fmt(fr.get(k))} | ZB {fmt(z)} | "
                              f"NMS {fmt(n)}")
                        shown += 1
            print(f"     fields: {dict(cz)} {dict(cn)}")


# ---- ladder, initslot, play_trace ---------------------------------------------------------------------------

def cmd_ladder(a):
    biosl_run.ROWS["nodisk"] = ("Philips_VG_8020", mname(a.tag, "NODISK"))
    biosl_run.ROWS["disk"] = ("Philips_VG_8020_NMS1200", mname(a.tag, "DISK"))
    sys.argv = ["biosl_run.py", "--all"]
    rc = biosl_run.main()
    import initslot_probe
    initslot_probe.MUST = ["Philips_VG_8020", "Philips_NMS_8250", mname(a.tag, "NODISK"), mname(a.tag, "DISK")]
    rc2 = initslot_probe.main()
    print(f"===== ladder rc={rc} initslot rc={rc2} =====")


def cmd_playtrace(a):
    r = subprocess.run([sys.executable, "-u", os.path.join(ROOT, "probes", "bios", "play_trace.py"), "--compare",
                        "Philips_VG_8020", mname(a.tag, "NODISK")])
    print(f"===== playtrace rc={r.returncode} (0: identical traces) =====")


def cmd_all(a):
    cmd_machines(a)
    a.modules = []
    for name, fn in (("spec", cmd_spec), ("nms", cmd_nms), ("fields", cmd_fields), ("ladder", cmd_ladder),
                     ("playtrace", cmd_playtrace)):
        print(f"########## {name}", flush=True)
        fn(a)


def main(argv):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("cmd", choices=["machines", "spec", "nms", "fields", "ladder", "playtrace", "all", "clean"])
    p.add_argument("modules", nargs="*", help="spec / nms / fields: *_rules.py names (default: all / the failing)")
    p.add_argument("--tag", required=True, help="a short name for this candidate, e.g. rc2")
    p.add_argument("--cbios", default="~/projects/cbios", help="the C-BIOS checkout, built (derived/bin)")
    p.add_argument("--detail", action="store_true", help="fields: three example cases per rule, not one")
    a = p.parse_args(argv)
    {"machines": cmd_machines, "spec": cmd_spec, "nms": cmd_nms, "fields": cmd_fields, "ladder": cmd_ladder,
     "playtrace": cmd_playtrace, "all": cmd_all, "clean": cmd_clean}[a.cmd](a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
