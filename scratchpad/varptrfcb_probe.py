"""D-VARPTRFCB, step 1: what does `VARPTR(#n)` answer on the references?

Before building the form: the VALUE for an open and an unopened channel, the
spacing between channels, the error set, and what the addressed bytes hold for
a channel in each mode. Clean-room: returned values and RAM CONTENTS are
readable (work-area RAM); nothing here reads a ROM byte or follows code.

Rows, each one case (fresh boot per side, channel state is the subject):
  vals    MAXFILES=3, all closed: VARPTR(#0..#3)
  crt     OPEN"CRT:" FOR OUTPUT AS #1 -> VARPTR(#1), and 12 bytes from it
  disk    OPEN"A:ZQ.TXT" FOR OUTPUT AS #1 / INPUT AS #2 after writing
          -> VARPTR, and 12 bytes from each (CF-3300 and zerobas only)
  errs    VARPTR(#4) with MAXFILES=3; VARPTR(#-1); VARPTR(#256)
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "probes", "lib"),
                os.path.join(HERE, "..", "probes", "basic")]
import omsx_repl  # noqa: E402
import basic_probe_cassave as cs  # noqa: E402

DUMP = ('FOR I=0 TO 11:PRINT RIGHT$("0"+HEX$(PEEK(V+I)),2);:NEXT:PRINT"]"')
CASES = {
    "vals": ["MAXFILES=3",
             'PRINT"[V";VARPTR(#0);VARPTR(#1);VARPTR(#2);VARPTR(#3);"]"'],
    "crt": ["MAXFILES=3", 'OPEN"CRT:" FOR OUTPUT AS #1',
            'V=VARPTR(#1):PRINT"[C";V;"]":PRINT"[D";:' + DUMP, "CLOSE"],
    "disk": ["MAXFILES=3", 'OPEN"A:ZQ.TXT" FOR OUTPUT AS #1', 'PRINT#1,"HELLO"',
             'V=VARPTR(#1):PRINT"[O";V;"]":PRINT"[P";:' + DUMP, "CLOSE",
             'OPEN"A:ZQ.TXT" FOR INPUT AS #2',
             'V=VARPTR(#2):PRINT"[I";V;"]":PRINT"[J";:' + DUMP, "CLOSE"],
    "errs": ["MAXFILES=3", "10 ON ERROR GOTO 90",
             '90 PRINT"[E";ERR;ERL;"]":END',
             '20 A=VARPTR(#4):PRINT"[K4]":END', "RUN",
             '20 A=VARPTR(#-1):PRINT"[KM]":END', "RUN",
             '20 A=VARPTR(#256):PRINT"[KB]":END', "RUN"],
}


def main():
    sides = sys.argv[1:] or ["vg8020", "cf3300", "zb"]
    for side in sides:
        cfg = cs.SIDES[side]
        for name, lines in CASES.items():
            if name == "disk" and not cfg["diska"]:
                continue
            kw = {}
            if cfg["diska"]:
                kw["diska"] = cs.probe_tmp.tmp(f"zb_varptrfcb_{side}_{name}.dsk")
                shutil.copy(cs.TEST_DSK, kw["diska"])
            caps = omsx_repl.run_cases(cfg["machine"],
                                       [("direct", list(cfg["reset"]) + lines)],
                                       batch=False, reset=(), boot=cfg["boot"],
                                       step=cfg["step"], **kw)
            raw = caps[0] or ""
            rows = [raw[r * 40:(r + 1) * 40].rstrip() for r in range(24)]
            got = [r for r in rows if "[" in r and not r.lstrip().startswith(
                ("PRINT", "V=", "20 ", "90 "))]
            print(f"{side:7} {name:5} {got}")


if __name__ == "__main__":
    main()
