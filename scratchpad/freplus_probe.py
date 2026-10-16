"""D-FREPLUS14: where do zerobas's 14 extra FRE(0) bytes (diskless) come from?
Reads the published layout pointers at start-up on both machines: HIMEM, FILTAB,
MEMSIZ (string space top), STKTOP, FRETOP, NULBUF, VARTAB / STREND, and FRE."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "probes", "lib")
                if os.path.isdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "probes"))
                else "/Users/joost/projects/zerobas/probes/lib")
import omsx_repl

CELLS = [("HIMEM", 0xFC4A), ("FILTAB", 0xF860), ("NULBUF", 0xF862), ("MEMSIZ", 0xF672),
         ("STKTOP", 0xF674), ("FRETOP", 0xF69B), ("VARTAB", 0xF6C2), ("STREND", 0xF6C6),
         ("TXTTAB", 0xF676)]
line1 = "D=0:FOR K=0 TO 4:READ A:PRINT\"[\";A;PEEK(A)+256*PEEK(A+1);\"]\":NEXT"
line2 = "FOR K=0 TO 3:READ A:PRINT\"[\";A;PEEK(A)+256*PEEK(A+1);\"]\":NEXT:PRINT\"[F\";FRE(0);\"]\""
prog = ["NEW", "10 " + line1, "20 " + line2,
        "30 DATA " + ",".join(str(a) for _n, a in CELLS), "RUN"]
for m in ("C-BIOS_MSX1_EU_REPACK_NODISK", "Philips_VG_8020"):
    scr = omsx_repl.run_cases(m, [("direct", prog)], batch=False,
                              reset=("", "SCREEN 0:WIDTH 40"), step=3.0, run_gap=15.0)[0]
    r = [scr[i:i + 40].strip() for i in range(0, len(scr), 40)] if scr else []
    vals = [x for x in r if x.startswith("[")]
    names = {str(a): n for n, a in CELLS}
    out = []
    for v in vals:
        p = v.strip("[] ").split()
        if len(p) == 2 and p[0] in names:
            out.append(f"{names[p[0]]}={int(p[1]):04X}")
        else:
            out.append(v)
    print(f"{m:30} " + " ".join(out), flush=True)
