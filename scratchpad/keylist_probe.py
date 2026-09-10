#!/usr/bin/env python3
r"""D-KEYSCOUT2 — the three things the `KEY n,"str"` residual still calls unmeasured.

The filed item (TODO.md, `KEY n,"str"` AND `KEY LIST` ARE UNIMPLEMENTED) is
marked SCOUT-THEN-ASK and says so explicitly: *"the decision is yours; the
measuring and pricing in front of it are not"*. It then names what is missing:

  * the `n` domain          -- `KEY 0,` / `KEY 11,`
  * the truncation length   -- "15 is read off the STRIDE, not off a machine"
  * `KEY LIST` entirely

🎯 `KEY LIST` IS ALSO THE CHEAPEST WAY TO READ THE DEFAULTS. The item prices the
default strings as "~160 B of DATA ... the larger half", and on a reference
`KEY LIST` prints all ten of them as text. One row measures the verb AND hands
over the exact bytes a fix would have to ship -- instead of ten PEEK loops over
FNKSTR, which is the shape that cost the first scout three runs.

⚠️ THE LENGTH IS READ FROM A MACHINE HERE, NOT FROM THE STRIDE. `d.trunc` plants
twenty distinctive characters and lists them back; whatever survives is the
answer. A stride of 16 with a NUL terminator SUGGESTS 15, but a suggestion from a
memory map is not a measurement of a verb.
"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

SIDES = {
    "vg8020": ("Philips_VG_8020", 8.0, ("NEW",)),
    "cf3300": ("National_CF-3300", 14.0, ("", "SCREEN 0", "NEW")),
    "zb": (os.environ.get("ZEROBAS_BASIC_MACHINE",
                          "C-BIOS_MSX1_EU_REPACK_DISK"), 8.0, ("NEW",)),
}

# --- rows that print ONE value: an error code, or nothing ---------------------
ERRCASES = [
    # the `n` domain. `KEY 1,` is the control: it must be silent everywhere the
    # verb exists, so a row that errors on ALL THREE says "my program is wrong",
    # not "the domain is narrow".
    ("d.n1",   'KEY 1,"X"'),
    ("d.n0",   'KEY 0,"X"'),
    ("d.n10",  'KEY 10,"X"'),
    ("d.n11",  'KEY 11,"X"'),
    ("d.nneg", 'KEY -1,"X"'),
    ("d.empty", 'KEY 1,""'),
    ("d.ctl",  'A=1'),                      # control: no KEY at all -> 0
]

# --- rows that print the LIST ------------------------------------------------
LISTCASES = [
    ("l.cold",  []),                                    # the ten defaults
    ("l.plant", ['KEY 1,"ZQX"']),                       # one slot replaced
    ("l.trunc", ['KEY 1,"ABCDEFGHIJKLMNOPQRST"']),      # 20 chars in
    ("l.empty", ['KEY 1,""']),
]


def run_err(side, stmt):
    machine, boot, reset = SIDES[side]
    prog = ["10 ONERRORGOTO90", f"20 {stmt}", "30 E=0:GOTO 60",
            "60 SCREEN0:CLS:" + 'PRINT"<";E;">":END', "90 E=ERR:RESUME 60"]
    raw = omsx_repl.run_cases(machine, [("direct", list(reset) + prog + ["RUN"])],
                              batch=False, reset=(), boot=boot, step=5.0,
                              cap_gap=10.0, timeout=300.0)[0] or ""
    m = re.findall(r"<([^<>]*)>", "".join(raw))
    return " ".join(m[-1].split()) if m else "<NO OUTPUT>"


def run_list(side, setup):
    machine, boot, reset = SIDES[side]
    lines = list(reset) + list(setup) + ["SCREEN0:CLS:KEY LIST"]
    raw = omsx_repl.run_cases(machine, [("direct", lines)], batch=False,
                              reset=(), boot=boot, step=5.0, cap_gap=12.0,
                              timeout=300.0)[0] or ""
    txt = "".join(raw)
    # the ten strings come back one per line; keep them as a compact record
    ls = [l.rstrip() for l in txt.splitlines()]
    ls = [l for l in ls if l and not l.startswith("KEY LIST") and l != "Ok"]
    return " | ".join(ls) if ls else "<NO OUTPUT>"


# --- D-FACEPIN: the FACE, not just the row label ----------------------------
# 🔴 A FILED FACE ROTS WITHOUT THE ROW CEASING TO DIVERGE, AND NOTHING DETECTS
# THAT. `filed_row_sweep` calls a row that still diverges -- but now to a
# DIFFERENT face -- `known`, and it reads green. TODO.md records five instances.
# 🎯 Same shape as `basic_probe_nodisk.PINNED` and D-DEFERPIN: pin the VALUES,
# RED on drift in EITHER direction. ⚠️ Keyed by SIDE NAME, never by position --
# `sides` is argv here, so a positional pin would compare the wrong machine.
PINNED = {
    # measured 2026-09-10; the filing is "zerobas answers ERR 2 to every form
    # while the references accept 1..10 and raise ERR 5 outside it". 0 = accepted.
    "d.n1":    {"vg8020": "0", "cf3300": "0", "zb": "2"},
    "d.n0":    {"vg8020": "5", "cf3300": "5", "zb": "2"},
    "d.n10":   {"vg8020": "0", "cf3300": "0", "zb": "2"},
    "d.n11":   {"vg8020": "5", "cf3300": "5", "zb": "2"},
    "d.nneg":  {"vg8020": "5", "cf3300": "5", "zb": "2"},
    "d.empty": {"vg8020": "0", "cf3300": "0", "zb": "2"},
}


def main():
    sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
    w = 9
    print(f"\n--- the `n` domain and the empty string (printed value = ERR, 0 = accepted)")
    print(f"{'row':<{w}}  " + "  ".join(f"{s:>10}" for s in sides))
    seen = {}
    for lab, stmt in ERRCASES:
        vals = [run_err(s, stmt) for s in sides]
        seen[lab] = dict(zip(sides, vals))
        tag = "refs agree" if vals[0] == vals[1] else "🔴 REFS DISAGREE"
        print(f"{lab:<{w}}  " + "  ".join(f"{v:>10}" for v in vals) + f"   {tag}"
              + ("" if vals[1] == vals[2] else "   zb DIFF"))
    print(f"\n--- KEY LIST")
    for lab, setup in LISTCASES:
        for s in sides:
            print(f"{lab:<{w}}  {s:<8}  {run_list(s, setup)}")
        print()
    drift = []
    for lbl, want in PINNED.items():
        for side, want_face in want.items():
            if lbl not in seen or side not in seen[lbl]:
                continue                  # row or side not run; not a drift
            got = str(seen[lbl][side])
            if got != want_face:
                drift.append(f"{lbl}[{side}]: pinned {want_face!r}, "
                             f"measured {got!r}")
    if drift:
        print("\n\U0001f534 PINNED FACE DRIFT -- the row may still diverge, but "
              "NOT to the face this tree has filed:")
        for d in drift:
            print(f"     {d}")
        print("  Re-read the owning entry: either the behaviour moved, or the "
              "filing was wrong when it was written.")
        return 2
    print("done")


if __name__ == "__main__":
    sys.exit(main())
