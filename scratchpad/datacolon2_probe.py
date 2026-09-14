"""D-KWBARS spin-off: `DATA` in the EXECUTION PATH, followed by another statement.

CONTROL first (`c0`): the same READ with the DATA after END -- the shape every
existing row uses -- which must read 42 on both machines.
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

CASES = [
    ("c0_data_after_end", ['READ A:PRINT"<";A;">"', 'END', 'DATA 42']),
    ("c1_data_then_read", ['DATA 42:READ A:PRINT"<";A;">"']),
    ("c2_data_own_line",  ['DATA 42', 'READ A:PRINT"<";A;">"']),
    ("c3_data_then_print",['DATA 42:PRINT"<OK>"']),
    ("c4_data_str",       ['DATA AB:READ A$:PRINT"<";A$;">"']),
    ("c5_rem_then",       ['DATA 42:REM X', 'READ A:PRINT"<";A;">"']),
]
def run(mach):
    specs = [("stored", lines) for _, lines in CASES]
    return omsx_repl.run_cases(mach, specs, batch=True)

for mach in ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_DISK"):
    print("===", mach)
    for (name, lines), raw in zip(CASES, run(mach)):
        txt = " ".join("".join(raw or "").split())
        i = txt.rfind("RUN")
        tail = txt[i:] if i >= 0 else txt
        print(f"  {name:20} {tail[:90]!r}")
