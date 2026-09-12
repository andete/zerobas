import sys, re
sys.path.insert(0, "/Users/joost/projects/zerobas/probes/lib")
import omsx_repl, probe_sides
cfg = probe_sides.sides("zb")["zb"]
cases = [
    ("s0.text",  ['10 SPRITE$(0)=STRING$(8,255):A=ASC(SPRITE$(0)):PRINT"[X";A;"]"', "RUN"]),
    ("s1.gfx",   ['10 SCREEN2:SPRITE$(0)=STRING$(8,255):A=ASC(SPRITE$(0)):SCREEN0:PRINT"[X";A;"]"', "RUN"]),
    ("s2.len",   ['10 SCREEN2:SPRITE$(0)=STRING$(8,255):A=LEN(SPRITE$(0)):SCREEN0:PRINT"[X";A;"]"', "RUN"]),
    ("s3.err",   ['10 SPRITE$(0)=STRING$(8,255):PRINT"[X";1;"]"', "RUN"]),
]
caps = omsx_repl.run_cases(cfg["machine"], cases, batch=False, reset=(),
                           boot=cfg["boot"], step=10.0, cap_gap=90.0, timeout=600.0)
for (tag, _), cap in zip(cases, caps):
    txt = re.sub(r"\s+", " ", cap if isinstance(cap, str) else str(cap))
    m = re.findall(r"\[X\s*(-?\d+)\s*\]", txt)
    e = re.search(r"([A-Za-z ]*error[A-Za-z ]*|Illegal function call)", txt)
    print("%-8s %-6s %s" % (tag, m[-1] if m else "NONE", e.group(1).strip() if e else ""))
