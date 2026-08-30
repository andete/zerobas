#!/usr/bin/env python3
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT); sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl
ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
def probe(stmt):
    lines = ["10 ONERRORGOTO900", f"30 {stmt}", '40 PRINT"<E";ERR;">":END',
             '900 PRINT"<E";ERR;">":END', "RUN"]
    caps = omsx_repl.run_cases(ZB, [("direct", lines)], batch=False,
                               boot=8.0, step=3.0, cap_gap=8.0, timeout=200.0)
    txt = "".join(caps[0] or [])
    import re
    m = re.search(r"<E\s*([0-9]+)\s*>", txt)
    return m.group(1) if m else ("OOMtext" if "Out of memory" in txt else "?")
for s in ["CLEAR 400,&H82C0", "CLEAR 500,&H9000", "CLEAR 500,&HD000",
          "CLEAR 200,&HD000", "CLEAR 200,&HABCD"]:
    print(f"{s:24s} ERR={probe(s)}", flush=True)
