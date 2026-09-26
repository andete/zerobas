"""T5 speed: where zerobas's float time goes -- SQR vs division, timed in TIME ticks.

`SQR(I)` x30 and `I/7` x300 inside one program, `TIME` read around each loop,
on the machines named on the command line (VG-8020 and the diskless zerobas).
Measured 2026-09-26: zerobas's SQR is ~4x FASTER than the VG-8020's (42 vs
173), its division ~3.9x SLOWER (637 vs 162) -- division is the lever.
Run with ZEROBAS_REFCACHE=0 (a cached answer replays, it does not time).
Usage: sqrtime_probe.py Philips_VG_8020 C-BIOS_MSX1_EU_REPACK_NODISK
"""
import sys, re
sys.path.insert(0, "/Users/joost/projects/zerobas/probes/lib")
import omsx_repl
prog = ["NEW", "10 T=TIME:FOR I=1 TO 30:X=SQR(I):NEXT:A=TIME-T", "20 T=TIME:FOR I=1 TO 300:X=I/7:NEXT:B=TIME-T",
        '30 PRINT CHR$(91);A;B;CHR$(93)', "RUN"]
for m in sys.argv[1:]:
    raw = omsx_repl.run_cases(m, [("direct", prog)], batch=False, reset=("CLS",), boot=8.0, capture="screen", run_gap=60.0)[0] or ""
    rows=[raw[i*omsx_repl.COLS:(i+1)*omsx_repl.COLS] for i in range(omsx_repl.ROWS)]
    runi=[i for i,r in enumerate(rows) if r.strip()=="RUN"]
    out="".join(rows[runi[-1]+1:]) if runi else ""
    print(m[:12], "SQR x30, I/7 x300 (ticks):", re.findall(r"\[([^\]]*)\]", out))
