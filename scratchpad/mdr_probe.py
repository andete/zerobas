"""Feasibility scouting for MOTOR / DELETE / RENUM sweep rows.

CONTROL m0: the PPI port C value with the motor untouched -- if m1 and m2 do
not differ from it and from each other, MOTOR has no observable here.
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

CASES = [
 ("m0_ctl",  ['A=INP(&HAA):PRINT"<";A;">"']),
 ("m1_on",   ['MOTOR ON:A=INP(&HAA):MOTOR OFF:PRINT"<";A;">"']),
 ("m2_off",  ['MOTOR OFF:A=INP(&HAA):PRINT"<";A;">"']),
 ("m3_tog",  ['MOTOR OFF:MOTOR:A=INP(&HAA):MOTOR OFF:PRINT"<";A;">"']),
 ("d0_del",  ['PRINT"<D1>"', 'PRINT"<D2>"', 'DELETE 20', 'PRINT"<D3>"']),
 ("r0_ren",  ['PRINT"<R1>"', 'RENUM 100', 'PRINT"<R2>"']),
]
for mach in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_DISK"):
    print("===", mach)
    specs = [("stored", l) for _, l in CASES]
    for (name, _), raw in zip(CASES, omsx_repl.run_cases(mach, specs, batch=False)):
        txt = " ".join("".join(raw or "").split())
        i = txt.rfind("RUN")
        print(f"  {name:8} {(txt[i:] if i>=0 else txt)[:110]!r}")
