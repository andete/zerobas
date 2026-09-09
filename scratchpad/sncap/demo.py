#!/usr/bin/env python3
"""The session's finding, as real MSX BASIC, on both references and on zerobas.

D-SNCAP2's failure detector fired once, on deffn's `o.clearwipe3`, and the
reason is an ordinary BASIC fact worth seeing on its own: `CLEAR` resets the
`ON ERROR` handler. Row A traps and reaches its `END`; row B is the same
program with a bare `CLEAR` in front of the fault, and the trap is gone.
"""
import sys, os
sys.path.insert(0, "probes/lib")
import omsx_repl, probe_signal

A = ["10 ON ERROR GOTO 100", "20 X=FNZ(1)",
     '30 PRINT"[NOFAULT]":END',
     '100 PRINT"[TRAPPED ERR";ERR;"]":END']
B = ["10 ON ERROR GOTO 100", "15 CLEAR", "20 X=FNZ(1)",
     '30 PRINT"[NOFAULT]":END',
     '100 PRINT"[TRAPPED ERR";ERR;"]":END']

MACH = [("vg8020", "Philips_VG_8020", 8.0, 2.5, ("NEW", "CLS")),
        ("cf3300", "National_CF-3300", 14.0, 4.5, ("", "SCREEN 0", "NEW", "CLS")),
        ("zb", os.environ.get("ZEROBAS_BASIC_MACHINE",
                              "C-BIOS_MSX1_EU_REPACK_DISK"), 8.0, 2.5,
         ("NEW", "CLS"))]

print("CLEAR resets the ON ERROR handler — 3 machines, boot-per-case\n")
print("  A  10 ON ERROR GOTO 100 : 20 X=FNZ(1)            -> trapped")
print("  B  10 ON ERROR GOTO 100 : 15 CLEAR : 20 X=FNZ(1) -> NOT trapped\n")
print(f"  {'':10} {'A: value':<20} {'A: signal':<11} "
      f"{'B: value':<34} {'B: signal'}")
for name, machine, boot, step, reset in MACH:
    row = []
    for lines in (A, B):
        so: dict = {}
        marked = probe_signal.mark_ends(lines)
        kw = {}
        if name != "vg8020":
            import tempfile, shutil
            d = os.path.join(tempfile.gettempdir(), f"zb_demo_{name}.dsk")
            shutil.copy("disk/test720.dsk", d)
            kw["diska"] = d
        cap = omsx_repl.run_cases(machine, [("direct", list(reset) + marked
                                            + ["RUN"])], batch=False,
                                  boot=boot, step=step,
                                  **kw, **probe_signal.kwargs(so))[0]
        # 🔴 `result_span` ALONE READS THE TYPED LINE BACK. Row B never reaches
        # its PRINT, so the last `[` on the screen is the ECHO of line 100 and a
        # plain span returns `TRAPPED ERR";ERR;"` -- source text posing as a
        # value ([[trapsvc-echo-fence]]). `result_span_after_echo` is what
        # exists for this: it looks only AFTER the echoed `RUN`.
        v = omsx_repl.result_span_after_echo(cap, "RUN")
        if v is None:                       # nothing printed -> what DID it say?
            t = omsx_repl.screen_tail(cap, "RUN")
            v = f"<untrapped: {t}>" if t else "<nothing>"
        row += [v if v.startswith("<") else repr(v),
                "on signal" if so.get("sentinel") else "NEVER"]
    print(f"  {name:10} {row[0]:<20} {row[1]:<11} {row[2]:<34} {row[3]}")
