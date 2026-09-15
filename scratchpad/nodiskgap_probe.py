#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-NODISKGAP: `LFILES` and `FIELD` on a machine with NO DISK ROM.

`scratchpad/tokscout2.py` turned these up while measuring where a Disk-BASIC
verb's TOKEN lives. Neither is in `probes/basic/basic_probe_nodisk.py`'s row set
-- it pins `FILES`, `KILL`, `NAME`, `COPY`, `OPEN`, `DSKO$`, `DSKI$` and `DSKF`,
and these two are simply absent -- so neither is one of the 8 divergences that
target already carries.

FOUR SIDES, because "diskless" is only half the question:

  Philips_VG_8020              the DISKLESS reference
  National_CF-3300             the WITH-DISK reference -- without it there is no
                               way to tell "zerobas is wrong on the diskless
                               target" from "zerobas is wrong everywhere"
  ..._REPACK_NODISK            this tree, diskless (an OFFICIAL target)
  ..._REPACK_DISK              this tree, with its own disk ROM

CONTROLS FIRST, AND THEY MUST BE ABLE TO FAIL. `FROG`/`ZQ` are words BASIC does
not know: they must answer **ERR 2**, or "ERR 5 means a hook refused" is not a
claim about the machine at all. `CLS` must RUN. And `FILES` is the FAMILY
control: it is already pinned diskless-refusing, so if it ever reads otherwise
here, the apparatus is what changed and nothing else on the page is a verdict.

⚠️ `FIELD` IS ASKED TWICE ON PURPOSE. A BARE `FIELD` could be refused for its
SYNTAX rather than by the disk gate, and those are different findings; the
`#1,2 AS A$` form separates them.
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = ("Philips_VG_8020", "National_CF-3300",
            "C-BIOS_MSX1_EU_REPACK_NODISK", "C-BIOS_MSX1_EU_REPACK_DISK")
# the CF-3300 boots slower and into a screen mode the scrape cannot read
# (basic_probe_kwsweep.MACH_BOOT / MACH_RESET_PRE) -- without these it stores
# NOTHING and reports an apparatus failure rather than a reading.
MACH_KW = {"National_CF-3300": dict(boot=14.0, reset=("", "SCREEN 0"))}


def prog(stmt: str) -> list[str]:
    """`ON ERROR` targets the LAST line, computed -- pointing it at a fixed
    number once aimed it at the SUCCESS line, and both outcomes then printed the
    same thing while nothing had been measured."""
    b = [None, stmt, 'PRINT"<X>":END', 'PRINT"<E";ERR;">":END']
    b[0] = "ON ERROR GOTO %d" % (10 * len(b))
    return b


CASES = [
    ("c_frog",    prog("FROG")),                  # control: unknown word -> ERR 2
    ("c_zq",      prog("ZQ")),                    # control: ditto, 2 letters
    ("c_cls",     prog("CLS")),                   # control: a verb that runs
    ("c_files",   prog("FILES")),                 # FAMILY control: pinned already
    ("lfiles",    prog("LFILES")),
    ("field_bare", prog("FIELD")),
    ("field_arg", prog("FIELD#1,2 AS A$")),
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
            r = t.rfind("RUN")                    # the fence is in the LISTING too
            tail = t[r + 3:] if r >= 0 else t
            i = tail.find("<")
            j = tail.find(">", i + 1) if i >= 0 else -1
            col[name] = tail[i:j + 1] if i >= 0 and j > i else "?" + tail[:40]
        rows[mach] = col
        print("===", mach, flush=True)
        for name, _ in CASES:
            print(f"  {name:11} {col[name]!r}", flush=True)
    print()
    hdr = ["case"] + [m.replace("C-BIOS_MSX1_EU_REPACK_", "zb ") for m in MACHINES]
    print("| " + " | ".join(hdr) + " |")
    print("|" + "---|" * len(hdr))
    for name, _ in CASES:
        print("| " + " | ".join([name] + [rows[m][name] for m in MACHINES]) + " |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
