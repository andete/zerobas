#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-NODISKDEN: the Disk-BASIC verbs `basic_probe_nodisk.py` has never asked about.

Joost ruled 2026-09-15: *"every hook claimed on 3300 we don't presumably is a sign
of a defect or divergence."* There are TWO denominators and they should agree:

  * the CF-3300 claims **27 hook cells**; we name 14 equates, 13 of which it also
    claims, so **14 claimed cells have no name here**. Three are now identified
    (`H_LSET $FE21`, `H_RSET $FE26`, `H_FIELD $FE2B`) and every one was a real
    diskless defect. Eleven are still unidentified.
  * `basic_probe_nodisk.py` asks about **17** words; `basic/kwtable.inc`'s
    Disk-BASIC surface is ~**37**.

This probe closes the second gap. `LFILES` ran wrong for as long as it existed
because it had no row while `FILES` beside it was green, so the rule here is: a
verb that AGREES still earns its row.

⚠️ JOOST'S "PRESUMABLY" IS LOAD-BEARING AND `GET`/`PUT` ARE WHY. Both are
Disk-BASIC verbs the reference hooks, and the diskless reference answers the
channel's own ERR 59 exactly as we do -- no divergence, no gate needed. A claimed
hook MARKS A CANDIDATE; it does not guarantee a defect. So the DIVERGENCE is
measured first and the slot hunted only for the verbs that actually diverge.

\U0001f534 THREE VERBS CANNOT BE ASKED IN THIS SHAPE AT ALL. `LOAD`, `RUN"<file>"`
and `MERGE` REPLACE OR MERGE INTO THE RUNNING PROGRAM, so they destroy the probe
that asks the question -- `MERGE` already came back from the VG-8020 with no fence
at all. That is an apparatus limit and it is recorded as one, not read as a
verdict.
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = ("Philips_VG_8020", "National_CF-3300",
            "C-BIOS_MSX1_EU_REPACK_NODISK")
MACH_KW = {"National_CF-3300": dict(boot=14.0, reset=("", "SCREEN 0"))}


def prog(stmt: str) -> list[str]:
    """The trap is the LAST line, COMPUTED -- a fixed number once aimed it at the
    SUCCESS line and four cases read as agreement while nothing was measured."""
    b = [None, stmt, 'PRINT"<X>":END', 'PRINT"<E";ERR;">":END']
    b[0] = "ON ERROR GOTO %d" % (10 * len(b))
    return b


CASES = [
    ("c_frog",   prog("FROG")),                  # control: unknown word -> ERR 2
    ("c_cls",    prog("CLS")),                   # control: a verb that runs
    ("c_files",  prog("FILES")),                 # family control: pinned already
    ("close",    prog("CLOSE")),
    ("close_n",  prog("CLOSE#1")),
    # 🔴 `SAVE`, `BLOAD` and `BSAVE` ARE NOT HERE, AND THE FIRST RUN IS WHY.
    # With NO DISK ROM a bare `SAVE"X"` is a CASSETTE save -- it waits on the tape
    # motor -- so the VG-8020 never came back, and EVERY CASE AFTER IT IN THE BATCH
    # read `? color auto goto list run`: no fence, no verdict. The first cut of this
    # probe then FLAGGED ALL NINE AS DIVERGENCES, because it compared a failed
    # capture against a real one. An empty capture on one side is not a verdict, and
    # the flag logic below now says NO READING rather than inventing one.
    # These three need the tape rig or boot-per-case, not this shape.
    ("loc",      prog("PRINT LOC(1)")),
    ("maxfiles", prog("MAXFILES=2")),
    ("cvd",      prog('PRINT CVD("ABCDEFGH")')),
    ("inputn",   prog("INPUT#1,A$")),
    ("lineinp",  prog("LINE INPUT#1,A$")),
    ("printn",   prog('PRINT#1,"X"')),
]


def main() -> int:
    rows = {}
    for mach in MACHINES:
        kw = dict(batch=True, cap_gap=8.0)
        kw.update(MACH_KW.get(mach, {}))
        raws = omsx_repl.run_cases(mach, [("stored", l) for _, l in CASES], **kw)
        col = {}
        for (name, _), raw in zip(CASES, raws):
            t = " ".join("".join(raw or "").split())
            r = t.rfind("RUN")                   # the fence is in the LISTING too
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
            flag = "\u26a0\ufe0f NO READING -- apparatus, not a verdict"
        else:
            flag = "" if c[0] == c[2] else "\U0001f534 DIVERGES"
        print("| %s | %s | %s | %s | %s |" % (name, c[0], c[1], c[2], flag))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
