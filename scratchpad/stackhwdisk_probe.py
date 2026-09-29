"""D-DIMRESERVE, the measurement its NEXT names: how deep does a STATEMENT's own
machine stack go below the pool frontier CSP -- for the verbs stackhw_probe.py
never ran?

stackhw_probe.py measured on the DISKLESS machine: non-expression statements read
129-156 B (the probe's own loop and an interrupt included), expressions far more
-- but the evaluator has its own guard now (STK_EVAL_RESERVE, D-STACKFLOOR), so
what CTL_STACK_MARGIN must hold is a statement's NON-expression stack. The
deepest candidates were never measured: the DISK verbs, which CALSLT into
disk.rom and the sub-ROM FAT tenant and walk directories and chains there.

Same painting method (see stackhw_probe.py), on C-BIOS_MSX1_EU_REPACK_DISK with a
private copy of disk/test720.dsk per case. A case's SETUP runs at line 15, BEFORE
the band is painted, so creating its fixture file cannot read as depth. LOAD,
MERGE and RUN are left out: they replace the program that reads the answer.

    python3 -u scratchpad/stackhwdisk_probe.py [case ...]
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import omsx_repl, t6enum_probe as t

ZB = "C-BIOS_MSX1_EU_REPACK_DISK"
BAND = 1500
MK = 'OPEN"K.TXT" FOR OUTPUT AS #1:PRINT #1,"HELLO":CLOSE'
WORK = [
    # (key, setup at line 15 or "", the measured statement at line 30)
    ("idle",     "",  "A=1"),
    ("openout",  "",  'OPEN"S.TXT" FOR OUTPUT AS #1:PRINT #1,"HELLO":CLOSE'),
    ("inputf",   MK,  'OPEN"K.TXT" FOR INPUT AS #1:INPUT #1,A$:CLOSE'),
    ("append",   MK,  'OPEN"K.TXT" FOR APPEND AS #1:PRINT #1,"MORE":CLOSE'),
    ("chanfns",  MK,  'OPEN"K.TXT" FOR INPUT AS #1:A=LOF(1)+LOC(1)+EOF(1):A$=INPUT$(2,#1):CLOSE'),
    ("twochan",  MK,  'MAXFILES=2:OPEN"K.TXT" FOR INPUT AS #1:OPEN"T.TXT" FOR OUTPUT AS #2:INPUT #1,A$:PRINT #2,A$:CLOSE'),
    ("random",   "",  'OPEN"R.DAT" AS #1 LEN=32:FIELD #1,32 AS F$:LSET F$="X":PUT #1,1:GET #1,1:CLOSE'),
    ("save",     "",  'SAVE"P.BAS"'),
    ("saveasc",  "",  'SAVE"Q.BAS",A'),
    ("bsvbld",   "",  'BSAVE"B.BIN",&HC000,&HC0FF:BLOAD"B.BIN"'),
    ("files",    MK,  'FILES'),
    ("kill",     MK,  'KILL"K.TXT"'),
    ("name",     MK,  'NAME"K.TXT" AS "N.TXT"'),
    ("copy",     MK,  'COPY"K.TXT" TO "C.TXT"'),
    ("dskf",     "",  'A=DSKF(0)'),
    ("dski",     "",  'A$=DSKI$(0,0)'),
    ("nofile",   "",  'OPEN"NOSUCH.TXT" FOR INPUT AS #1'),   # the error path, trapped
    ("killopen", MK,  'OPEN"K.TXT" FOR INPUT AS #1:KILL"K.TXT"'),  # 64, trapped
]


def prog(setup, stmt):
    # the walk is an int16 loop over C% = CSP - 65536 (stackhw_probe.py says why)
    lines = ["NEW", f"10 C=PEEK(&HE050)+256*PEEK(&HE051):C%=C-65536:L%=C%-{BAND}:H%=C%-48"]
    if setup:
        lines.append(f"15 {setup}")
    lines += ["20 ON ERROR GOTO 50:FOR A%=L% TO H%:POKE A%,&HA5:NEXT",
              f"30 {stmt}",
              "40 M%=H%+1:FOR A%=L% TO H%:IF PEEK(A%)<>&HA5 THEN IF A%<M% THEN M%=A%",
              "45 NEXT:SCREEN 0:PRINT CHR$(91);C%-M%;E;CHR$(93):END",
              "50 E=ERR:RESUME 40", "RUN"]
    return lines


def main():
    only = sys.argv[1:] or [k for k, _s, _t in WORK]
    print(f"zerobas (DISK) machine-stack depth below CSP (bytes; 48 = nothing reached "
          f"the band, {BAND} = AT LEAST the band); second number = ERR if trapped:")
    for k, setup, stmt in WORK:
        if k not in only:
            continue
        raw = omsx_repl.run_cases(ZB, [("direct", prog(setup, stmt))], batch=False,
                                  reset=("CLS",), boot=8.0, step=3.0, run_gap=90.0,
                                  capture="screen", diska=t._disk_image())[0] or ""
        m = re.findall(r"\[\s*(-?\d+)\s+(-?\d+)\s*\]", raw)
        v = f"{m[-1][0]:>6} {m[-1][1]:>3}" if m else "NO READING"
        print(f"  {k:9} {v:>10}   {stmt[:64]}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
