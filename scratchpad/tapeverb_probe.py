#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-TAPEVERB: the three verbs D-NODISKDEN could not ask about, asked.

`SAVE`, `BLOAD` and `BSAVE` were left out of the diskless denominator for a
measured reason: with NO DISK ROM a bare `SAVE"X"` is a **CASSETTE** save, and it
WAITS ON THE TAPE MOTOR. The first cut put them in a batch, the VG-8020 never came
back, and every case after them read no fence at all -- which the scout then
flagged as nine divergences.

🎯 THE FIX IS THE RIG THIS TREE ALREADY HAS. `cassetteplayer new <path>`
mounts a BLANK recording tape (the same prologue `basic_probe_kwsweep.py`'s
`NEEDS-BLANKTAPE:` rig uses), and with a tape in the deck the cassette save
COMPLETES instead of blocking. Then the diskless reading is a reading.

⚠️ THE CONTROLS COME FIRST AND BOTH CAN FAIL. `c_frog` must answer Syntax error
(a word BASIC does not know) and `c_files` must answer ERR 5 diskless / ERR 70
with a disk -- the family control that is already pinned. If either moves, the
tape prologue has changed something else and nothing below is a verdict.
"""
import os, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = ("Philips_VG_8020", "National_CF-3300",
            "C-BIOS_MSX1_EU_REPACK_NODISK")
MACH_KW = {"National_CF-3300": dict(boot=14.0, reset=("", "SCREEN 0"))}


def blank_tape():
    fh = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    fh.close()
    os.unlink(fh.name)          # the fixture IS the absence: openMSX creates it
    return fh.name


def prog(stmt):
    b = [None, stmt, 'PRINT"<X>":END', 'PRINT"<E";ERR;">":END']
    b[0] = "ON ERROR GOTO %d" % (10 * len(b))
    return b


# 🔴 `save` AND `bload` ARE NOT HERE, AND THE REASON IS NOT THE WINDOW.
# At step=60 the VG-8020's `SAVE"ZQ"` reaches `Ok` and NEVER PRINTS THE FENCE:
# **SAVE ENDS THE RUN**, which is the very behaviour D-KWSAVEEND shipped earlier
# the same day, so a following `PRINT` is unreachable by construction. `BLOAD`
# from a tape with no matching file never returns either. Their reading has to
# come from THE TAPE -- `basic_probe_kwsweep.py`'s `NEEDS-BLANKTAPE:` rig decodes
# the recording -- not from a marker printed afterwards.
# 🎯 `bsave` DOES return, so it is measurable in this shape and is measured.
CASES = [
    ("c_frog",  prog("FROG")),
    ("c_files", prog("FILES")),
    ("bsave",   prog('BSAVE"ZQ",0,0')),
]


def main() -> int:
    rows = {}
    for mach in MACHINES:
        # 🔴 step=30, NOT 8. A cassette SAVE writes a LONG HEADER -- several
        # seconds of tone before any data -- so the verb takes ~10 s of emulated
        # time even with a tape in the deck. At step=8 the VG-8020 read no fence
        # at all and zerobas read `<X>`, which would have looked like a divergence
        # and was the capture window closing on the slower, more thorough side.
        kw = dict(batch=False, cap_gap=30.0, step=30.0,
                  prologue=("cassetteplayer new {%s}" % blank_tape(),))
        kw.update(MACH_KW.get(mach, {}))
        raws = omsx_repl.run_cases(mach, [("stored", l) for _, l in CASES], **kw)
        col = {}
        for (name, _), raw in zip(CASES, raws):
            t = " ".join("".join(raw or "").split())
            r = t.rfind("RUN")
            tail = t[r + 3:] if r >= 0 else t
            i = tail.find("<")
            j = tail.find(">", i + 1) if i >= 0 else -1
            col[name] = tail[i:j + 1] if i >= 0 and j > i else "?" + tail[:40]
        rows[mach] = col
    print("| case | VG-8020 | CF-3300 | zb NODISK | |")
    print("|---|---|---|---|---|")
    for name, _ in CASES:
        c = [rows[m][name] for m in MACHINES]
        if any(x.startswith("?") for x in c):
            flag = "⚠️ NO READING -- apparatus, not a verdict"
        else:
            flag = "" if c[0] == c[2] else "🔴 DIVERGES"
        print("| %s | %s | %s | %s | %s |" % (name, c[0], c[1], c[2], flag))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
