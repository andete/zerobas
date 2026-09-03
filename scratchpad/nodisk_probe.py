#!/usr/bin/env python3
r"""D-NODISK — what does zerobas do with the DISK verbs when there is no disk ROM?

Joost's question, 2026-09-03: the disk-only keywords ought to live behind the
disk ROM, as on real hardware -- and "it should also be possible to ship zerobas
without a disk ROM".

🎯 THAT TURNS A DESIGN ARGUMENT INTO A MEASUREMENT. On real MSX the MAIN ROM owns
the keyword table (measured: the diskless VG-8020 crunches `MKS$` to `FF AF`) and
the DISK ROM supplies the implementation through hooks -- so a diskless machine
tokenises the verb and then raises `Illegal function call`. zerobas implements
every disk verb BASIC-side, so a diskless zerobas should ANSWER where the
reference refuses.

This probe boots `ZB_REPACK_NODISK` -- the shipped repack machine with the
disk.rom slot removed and nothing else changed -- and asks. The VG-8020 is the
oracle: it is exactly the configuration under test (an MSX1 with no disk ROM).

⚠️ THE MACHINE IS A SCRATCH EXPERIMENT, not a shipped configuration: zerobas has
no diskless build target today. What it measures is whether one would BEHAVE, not
whether one exists.
"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

SIDES = {
    "vg8020":   ("Philips_VG_8020", 8.0, ("NEW",)),           # the ORACLE
    "zb-disk":  ("C-BIOS_MSX1_EU_REPACK_DISK", 8.0, ("NEW",)),
    "zb-nodisk": ("ZB_REPACK_NODISK", 8.0, ("NEW",)),
}

CASES = [
    # 🟢 CONTROLS: plain BASIC, must be identical everywhere
    ("c.print",  'PRINT 1+1'),
    ("c.str",    'PRINT LEN("ABC")'),
    # --- the MK/CV family (D-MKSD, just shipped) --------------------------
    ("k.mks",    'PRINT LEN(MKS$(1.5))'),
    ("k.mkd",    'PRINT LEN(MKD$(1.5))'),
    ("k.cvs",    'PRINT CVS(MKS$(1.5))'),
    ("k.mki",    'PRINT LEN(MKI$(258))'),
    ("k.cvi",    'PRINT CVI(MKI$(258))'),
    # --- other disk verbs implemented BASIC-side --------------------------
    # ⚠️ ROWS THAT NEED A LIVE DISK ARE OUT. `OPEN`/`FILES`/`KILL`/`NAME` all
    # returned the fixture's `load error` on the diskless machines -- an
    # UNREADABLE cell, not a divergence, and counting it as one would have
    # inflated this finding by four rows. What stays is the surface that
    # answers WITHOUT any medium.
    ("v.dskf",   'PRINT DSKF(0)'),
    ("v.eof",    'PRINT EOF(1)'),
    ("v.lof",    'PRINT LOF(1)'),
    ("v.cvistr", 'PRINT CVI("AB")'),
    ("v.mkifld", 'PRINT ASC(MKI$(1))'),
]


def run(side, stmt):
    machine, boot, reset = SIDES[side]
    prog = ['10 ON ERROR GOTO 90', '20 PRINT"<";', f'30 {stmt};',
            '40 PRINT">":END', '90 PRINT"<ERR";ERR;">"', 'RUN']
    raw = omsx_repl.run_cases(machine, [("direct", list(reset) + prog)],
                              batch=False, reset=(), boot=boot, step=5.0,
                              cap_gap=10.0, timeout=300.0)[0] or ""
    m = re.findall(r"<([^<>]*)>", "".join(raw))
    return repr(m[-1]) if m else "<NO OUTPUT>"


sides = (sys.argv[1] if len(sys.argv) > 1
         else "vg8020,zb-disk,zb-nodisk").split(",")
res = {s: {lab: run(s, st) for lab, st in CASES} for s in sides}
w = max(len(l) for l, _ in CASES)
print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>22}" for s in sides) + "   verdict")
diff = []
for lab, _ in CASES:
    vals = [res[s][lab] for s in sides]
    # the QUESTION is vg8020 (diskless reference) vs zb-nodisk (diskless zerobas)
    if any("load error" in v or "NO OUTPUT" in v for v in vals):
        print(f"{lab:<{w}}  " + "  ".join(f"{v:>22}" for v in vals)
              + "   UNREADABLE (needs a live disk; not scored)")
        continue
    same = vals[0] == vals[-1]
    if not same:
        diff.append(lab)
    print(f"{lab:<{w}}  " + "  ".join(f"{v:>22}" for v in vals)
          + f"   {'SAME' if same else 'DIFF'}")
print(f"\nDIFF (vg8020 vs zb-nodisk): {len(diff)}/{len(CASES)}  " + " ".join(diff))
print("done")
