#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ROMSIZE step 1, BLOAD to disk.rom (2026-10-19): which error does BLOAD give for a
bad drive, an empty name and a missing file? zerobas's old sub-ROM tenant fell through
both rejects into the load with a stale 8.3 name (53, or a load of that file); the move
raises 62 / 56 like the other disk verbs. BLOAD's own answer was never measured.
Screen output only: ON ERROR prints ERR per row; a row that loads prints LOADED.
"""
import os, re, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402

ROWS = [("baddrive", 'BLOAD"Q:X.BIN"'), ("empty", 'BLOAD""'), ("missing", 'BLOAD"NOPE.BIN"'),
        ("dotonly", 'BLOAD"."'), ("drvonly", 'BLOAD"A:"')]


def prog(stmt, tag):
    return ["NEW", "10 ON ERROR GOTO 100", f'20 {stmt}:PRINT"[{tag} LOADED]":END',
            f'100 PRINT"[{tag}";ERR;"]":RESUME 110', "110 END", "RUN"]


def main():
    for label, machine in (("CF-3300", "National_CF-3300"),
                           ("OURS", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"))):
        out = []
        for tag, stmt in ROWS:
            dsk = probe_tmp.tmp(f"bloaderr_{label}_{tag}.dsk")
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
            raw = omsx_repl.run_cases(machine, [("direct", prog(stmt, tag))], batch=False,
                                      reset=("", "SCREEN 0:WIDTH 40"), boot=14.0, step=1.5,
                                      run_gap=30.0, diska=dsk)[0] or ""
            flat = raw.replace("\n", "")
            v = [x for x in re.findall(r"\[" + tag + r"([^\]\[]*)\]", flat) if '"' not in x]
            out.append(f"{tag}={v[-1].strip() if v else 'NO READING'}")
        print(f"{label:8} " + "  ".join(out), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
