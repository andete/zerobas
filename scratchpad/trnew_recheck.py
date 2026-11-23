#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-TRSPEC: re-check the turbo R findings in docs/turbor/remeasured.md with each MSX1 page's OWN executable rules
(probes/bios/spec/*_rules.py, docs/spec-method.md §3a). The rules' loaders read the committed VG-8020 run files;
here every such file is replaced, in memory, by the turbo R reading of the same probe (scratchpad/AE_trall/<probe>.out:
"ref" = FS-A1GT, "ours" = FS-A1ST), so a rule the turbo R breaks shows as FALSE on the A1GT ("GT") and as
"differ" on the A1ST ("ST"); the FS-A1WSX's reading of the same probe source (scratchpad/AE_m1on2/, msx2p row) is run
the same way ("WSX"), so a rule the MSX2+ already breaks is told apart. The loaders expect two rows (the VG-8020's N =
nodisk, D = disk): BOTH carry the one turbo R capture, so an "N" and a "D" case id are the same reading (likewise "C"
in xbsys). A rule that reads another row / run than the turbo R has (a comparison between the
VG-8020's two rows) is not a turbo R reading -- read its text before citing it.

    python3 scratchpad/trnew_recheck.py [--fields] [MODULE ...]   (--fields: also every decoded field that differs)
"""
import builtins
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "probes", "bios", "spec"))
import spec_rules  # noqa: E402

# the committed run file a loader opens -> the turbo R reading that replaces it
SUBST = {"XINP1_run3.out": "xinp1", "XSND1_run4.out": "xsnd1", "XSND1B_run1.out": "xsnd1b",
         "XTAP1_run2.out": "xtap1", "XTAP2_run1.out": "xtap2", "XTAP3_run1.out": "xtap3", "XTAP4_run1.out": "xtap4",
         "XTAP5_run1.out": "xtap5", "XINIT_fix1.out": "xinit", "XINIT3_fix1.out": "xinit3",
         "XINIT4_fix2.out": "xinit4", "XBSYS1_run1.out": "xbsys1", "XBSYS1_run2.out": "xbsys1",
         "XBSYS2_run1.out": "xbsys2", "XBSYS2_run2.out": "xbsys2", "XBSYS3_run1.out": "xbsys3",
         "XBSYS3_run2.out": "xbsys3"}
MODULES = ["xgtpdl_rules", "xgtpad_rules", "xbeep_rules", "xstmotr_rules", "xtapoon_rules", "xtapoof_rules",
           "xtapiof_rules", "xtapion_rules", "xtapin_rules", "xtapout_rules", "xinit_rules", "xbsys_rules"]
_open = builtins.open


SRC = "tr"


def fake(name):
    if SRC == "wsx":                         # the FS-A1WSX's reading of the same probe source (D-MSX1ON2), both sides
        t = _open(os.path.join(ROOT, "scratchpad", "AE_m1on2", SUBST[name] + ".out")).read()
        m = re.search(r"===== (\S+) msx2p: .*?CAP ref : (\w+)", t, re.S)
        if not m:
            sys.exit(f"FAIL: AE_m1on2/{SUBST[name]}.out holds no msx2p reading")
        p, gt = m.groups()
        st = gt
    else:
        t = _open(os.path.join(ROOT, "scratchpad", "AE_trall", SUBST[name] + ".out")).read()
        m = re.search(r"===== (\S+) turbor: .*?CAP ref : (\w+)\n  CAP ours: (\w+)", t, re.S)
        if not m:
            sys.exit(f"FAIL: AE_trall/{SUBST[name]}.out holds no turbor reading")
        p, gt, st = m.groups()
    return "".join(f"===== {p} {row}: Panasonic_FS-A1GT vs Panasonic_FS-A1ST =====\n  CAP ref : {gt}\n  CAP ours: {st}\n"
                   for row in ("nodisk", "disk"))


def opener(path, *a, **k):
    b = os.path.basename(str(path))
    if b in SUBST and os.path.dirname(os.path.abspath(str(path))) == os.path.join(ROOT, "scratchpad"):
        return io.StringIO(fake(b))
    return _open(path, *a, **k)


def evaluate(name, src):
    global SRC
    SRC = src
    mod = spec_rules.load(os.path.join(ROOT, "probes", "bios", "spec", name + ".py"))
    for m in list(sys.modules):              # the shared loaders cache their cases: load them afresh per source
        if m.endswith(("_model", "_cases")):
            del sys.modules[m]
    mod = spec_rules.load(os.path.join(ROOT, "probes", "bios", "spec", name + ".py"))
    return mod, spec_rules.run(mod)[0], mod.cases()


def fields(c):
    return {k: v for k, v in vars(c).items() if not callable(v)}


def field_diffs(name, trc, wsxc):
    """per case, the decoded fields where the A1GT differs from the A1WSX, and where the A1GT differs from the A1ST"""
    out = []
    for g, s, w in zip(trc["ref"], trc["zb"], wsxc["ref"]):
        fg, fs, fw = fields(g), fields(s), fields(w)
        dw = [f"{k} {fw[k]!r:.40}->{fg[k]!r:.40}" for k in fg if k in fw and fg[k] != fw[k]]
        ds = [f"{k} GT {fg[k]!r:.30} ST {fs[k]!r:.30}" for k in fg if k in fs and fg[k] != fs[k]]
        if dw or ds:
            out.append(f"    {g.id}: " + ("; ".join(dw) if dw else "as WSX") + (f"   || GT/ST: {'; '.join(ds)}" if ds else ""))
    return out


def main():
    builtins.open = opener
    print("# D-TRSPEC: each page's rules on the turbo R captures (scratchpad/AE_trall/) and the FS-A1WSX's (AE_m1on2/).\n"
          "# An N / D (xbsys: D / C) case pair is ONE capture, fed to both of the loader's rows.")
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    for name in [a for a in sys.argv[1:] if not a.startswith("--")] or MODULES:
        try:
            mod, tr, trc = evaluate(name, "tr")
            _, wsx, wsxc = evaluate(name, "wsx")
        except SystemExit as e:
            print(f"===== {name}: NOT DECODED -- {e}")
            continue
        print(f"===== {name} ({mod.PAGE})  [GT = FS-A1GT, ST = FS-A1ST, WSX = FS-A1WSX: the cases where the rule fails]")
        held = []
        for (r, n, rb, zbb), (_, _, wb, _) in zip(tr, wsx):
            if not (rb or zbb or wb):
                held.append(r.id)
                continue
            tag = "NEW ON TURBO R" if (rb or zbb) and not wb else "AS MSX2+" if rb == wb and zbb == wb else \
                "MSX2+ ONLY" if wb and not (rb or zbb) else "BOTH, OTHER CASES"
            print(f"  {r.id:16} {n:4} cases  {tag:17} GT {'ok' if not rb else 'FALSE ' + spec_rules.short(rb, 4)}"
                  f"  |  ST {'ok' if not zbb else 'FALSE ' + spec_rules.short(zbb, 4)}"
                  f"  |  WSX {'ok' if not wb else 'FALSE ' + spec_rules.short(wb, 4)}")
        print(f"  hold on all three: {', '.join(held) if held else '-'}")
        if "--fields" in flags:
            print("  decoded fields, A1WSX -> A1GT (and A1GT vs A1ST):")
            print("\n".join(field_diffs(name, trc, wsxc)) or "    none")


if __name__ == "__main__":
    main()
