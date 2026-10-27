#!/usr/bin/env python3
"""D-FILESNOEXT: how FILES lists a name with no extension (CF-3300 vs zerobas).

Found by scratchpad/dskib_probe.py (`Q` there, `Q       .` here). Three files saved
from BASIC -- two without an extension, one with a one-letter one -- then FILES; the
rows are printed RAW with spaces as `~`, so the field width is visible.

    python3 -u scratchpad/filesnoext_probe.py
"""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(REPO, "probes", "lib")]
import omsx_repl  # noqa: E402
import probe_tmp  # noqa: E402

LINES = ['NEW', '10 REM', 'SAVE"Q"', 'SAVE"R"', 'SAVE"S.A"', 'CLS:FILES']


def main():
    for side, m in (("CF", "National_CF-3300"), ("ZB", "C-BIOS_MSX1_EU_REPACK_DISK")):
        dsk = probe_tmp.tmp(f"filesnoext_{side}.dsk")
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
        scr = omsx_repl.run_cases(m, [("direct", LINES)], batch=False, diska=dsk, boot=14.0,
                                  reset=("", "SCREEN 0:WIDTH 40"), step=4.0, run_gap=8.0)[0]
        rows = [scr[i:i + 40] for i in range(0, len(scr or ""), 40)][:-1]
        for r in rows[:6]:
            if r.strip():
                print(f"{side} |{r.rstrip().replace(' ', '~')}|", flush=True)


if __name__ == "__main__":
    main()
