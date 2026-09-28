"""D-KWT2TA prototype: time a run-ENDING command by a TYPE-AHEAD end mark.

Joost, 2026-09-28: lifting the level-1 keywords is the priority, and 16 of them
(AUTO CONT DELETE LIST LLIST LOAD MERGE NEW RENUM RUN SAVE STOP CLOAD LFILES CMD
IPL) sit at T2- because kwtime cannot time them: they END or REPLACE the run, so
the row's own end-mark line never runs, and CURLIN -- the fallback -- is a
DIFFERENT event on each machine for these paths (09-24, "closed by measurement").

The idea: kwtime's case program is unchanged (interrupt-synced START mark, the
row, its end-mark line), but instead of typing `RUN` the harness injects
`RUN` + CR + `POKE&HE000,202` into KEYBUF in ONE burst. The second line waits in
the type-ahead buffer and is read only when the prompt asks for input again --
i.e. just after the command finished -- on BOTH machines, by the same BIOS
buffer. Symmetric by construction, RAM-mark timed, no ROM address observed.

What this prototype must show before it goes anywhere near kwtime:
  1. the burst is accepted (the injector writes a CR mid-line);
  2. the END mark fires AFTER the command's work, not before it (a command that
     polls the keyboard -- LIST -- might eat the waiting line);
  3. a NEGATIVE arm: the same command made deliberately slower (a longer
     program to LIST) reads longer, so the reading is the command's time.

    python3 -u scratchpad/kwt2_typeahead_probe.py
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(REPO, "probes", "lib"), os.path.join(REPO, "probes", "basic")]
import omsx_repl
import basic_probe_kwtime as kt

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
TAIL = f"POKE&H{kt.MARK_ADDR:04X},{kt.END}"

# (name, row body as kwsweep would store it, extra program lines typed BEFORE it)
CASES = [
    ("list3", "LIST", ["100 A=1", "110 B=2", "120 C=3"]),
    ("list30", "LIST", [f"{100 + i} REM {'X' * 20}" for i in range(30)]),   # NEGATIVE arm: more to list
    ("new", "NEW", ["100 A=1"]),
    ("stop", "STOP", []),
    ("end", "END", []),                 # control: END is CURLIN-timeable today
]


def lines_for(body, extra):
    base = kt.case_lines(body)          # [..., "RUN"]
    assert base[-1] == "RUN"
    # the extra program lines go in before RUN (numbered past the row's own)
    return base[:-1] + extra + ["RUN\r" + TAIL]


def main():
    out = {}
    for m in (REF, ZB):
        so = {}
        specs = [("direct", lines_for(b, x)) for _, b, x in CASES]
        omsx_repl.run_cases(m, specs, reset=(), batch=True, capture="screen", boot=8.0,
                            sentinel=(kt.MARK_ADDR, kt.END), settle_out=so)
        marks = so.get("marks", {})
        out[m] = [kt.delta(marks.get(i, [])) for i in range(len(CASES))]
    print(f"{'case':8} {'VG-8020 ms':>11} {'zerobas ms':>11} {'ratio':>7}")
    for i, (n, _, _) in enumerate(CASES):
        r, z = out[REF][i], out[ZB][i]
        ratio = f"{z / r:6.2f}" if r and z else "   --"
        f = lambda v: f"{v * 1000:10.1f}" if v is not None else "      None"
        print(f"{n:8} {f(r)} {f(z)} {ratio}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
