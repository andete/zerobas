"""Where does the FUNCTION-KEY LINE live in VRAM, and does KEY OFF blank it?

CONTROL: k0 scans with KEY ON and the string assigned -- it must find 'Z'
somewhere.  k1 repeats with KEY OFF: the same offsets must be blank.
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

CASES = [
 ("k0_on",  ['KEY 1,"ZZQ"', 'S=-1:E=-1:FOR I=800 TO 1023',
             'IF VPEEK(I)=90 THEN E=I:IF S<0 THEN S=I', 'NEXT',
             'PRINT"<";S;E;">"']),
 ("k1_off", ['KEY 1,"ZZQ":KEY OFF', 'S=-1:E=-1:FOR I=800 TO 1023',
             'IF VPEEK(I)=90 THEN E=I:IF S<0 THEN S=I', 'NEXT',
             'PRINT"<";S;E;">"']),
 ("k2_w",   ['PRINT"<";PEEK(&HF3AE);PEEK(&HF3B0);PEEK(&HF3B1);">"']),
]
for mach in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_DISK"):
    print("===", mach)
    specs = [("stored", l) for _, l in CASES]
    for (name, _), raw in zip(CASES, omsx_repl.run_cases(mach, specs, batch=False)):
        txt = " ".join("".join(raw or "").split())
        i = txt.rfind("RUN")
        print(f"  {name:8} {(txt[i:] if i>=0 else txt)[:110]!r}")
