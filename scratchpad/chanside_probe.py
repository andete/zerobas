#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ASAVECHAN's class, the siblings: does a disk verb that reaches main's FAT
engine WITHOUT chan_gate disturb a channel open beside it?

D-ASAVECHAN found SAVE ,A and BSAVE emptying an OUTPUT channel's file. The other
verbs on main's engine globals are BLOAD (the sub-ROM bload tenant) and DSKI$
(a sub-ROM tenant). An INPUT channel mid-file is as exposed as an output one: its
read position and staged sector live in the same globals.

  output  OPEN P1 FOR OUTPUT, PRINT#1 "AAA", <verb>, PRINT#1 "BBB", CLOSE
          -> P1.TXT read back from the image
  input   OPEN HI.TXT (26 B, on test720) FOR INPUT, read 5 chars, <verb>,
          read the rest -> printed as one line `R <text> #`

    VERB=bload|dskin|asave  MODE=output|input  python3 -u scratchpad/chanside_probe.py
"""
import os, re, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402
import disk_probe_wrblk_roundtrip as RT            # noqa: E402

VERB = {"bload": 'BLOAD"PROG.BIN"', "dskin": "A$=DSKI$(0,1)",
        "asave": 'SAVE"Q.BAS",A', "nop": "REM"}[os.environ.get("VERB", "bload")]
MODE = os.environ.get("MODE", "output")
if MODE == "output":
    PROG = ["NEW", "10 REM HELLO", 'OPEN"P1.TXT"FOR OUTPUT AS#1', 'PRINT#1,"AAA"',
            VERB, 'PRINT#1,"BBB"', "CLOSE#1", 'PRINT"[E]";ERR']
else:
    PROG = ["NEW", "10 REM HELLO", 'OPEN"HI.TXT"FOR INPUT AS#1', "A1$=INPUT$(5,#1)",
            VERB, "A2$=INPUT$(LOF(1)-5,#1)", "CLOSE#1", 'PRINT"R";A1$;"|";A2$;"#"']


def main():
    for tag, machine in (("CF-3300", "National_CF-3300"),
                         ("OURS", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"))):
        dsk = probe_tmp.tmp(f"chanside_{tag}.dsk")
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
        raw = omsx_repl.run_cases(machine, [("direct", PROG)], batch=False,
                                  reset=("", "SCREEN 0"), boot=14.0, step=3.0,
                                  diska=dsk)[0] or ""
        scr = re.sub(r"\s+", " ", raw)
        print(f"== {tag} {MODE} {VERB}")
        if MODE == "output":
            img = open(dsk, "rb").read()
            ent = RT.Fat12(dsk).dirent("P1", "TXT")
            body = None
            if ent and ent.get("cluster"):
                off = 14 * 512 + (ent["cluster"] - 2) * 1024
                body = img[off:off + min(ent["size"], 64)]
            print(f"   P1.TXT {ent} -> {body!r}")
        else:
            m = re.findall(r"\bR([^#]*)#", re.sub(r'"[^"\n]*"', "", scr))
            print(f"   read: {m[-1] if m else 'NO READING'!r}")
        print(f"   screen tail: {scr[-180:]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
