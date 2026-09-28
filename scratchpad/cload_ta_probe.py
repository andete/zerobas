"""D-KWT2CLOAD question: does a CLOAD drop the type-ahead that follows it?

kwtime times CLOAD's rows on zerobas (11.5 s / 5.8 s) but reads NO end mark on
the VG-8020. Two candidate causes: the reference's tape load clears KEYBUF, or it
outlasts the capture window. This types, in ONE KEYBUF burst, the CLOAD then a
PRINT whose output is fenced (CHR$(91), so the typed echo cannot match), and
reads the screen. `[TA]` after the load => the type-ahead survived.

Arms, per machine:
  direct   CLOAD"ZR" + CR + PRINT            -- the command typed at the prompt
  program  10 CLOAD"ZR" / RUN + CR + PRINT   -- kwtime's shape (RUN, then mark)
  control  PRINT"x" + CR + PRINT             -- NEGATIVE: no tape, must read [TA]
"""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(__file__), "..", "probes", "lib"),
                os.path.join(os.path.dirname(__file__), "..", "probes", "basic")]
import omsx_repl  # noqa: E402
import basic_probe_kwsweep as kw  # noqa: E402

TA = 'PRINT CHR$(91)+"TA]"'
ARMS = [
    ("direct", ["NEW", 'CLOAD"ZR"\r' + TA]),
    ("program", ["NEW", '10 CLOAD"ZR"', "RUN\r" + TA]),
    ("control", ["NEW", 'PRINT"x"\r' + TA]),
]


# SET 2 (after set 1 showed the reference NEVER reaching `Ok`, even at 90 s):
# no type-ahead at all, and a longer window -- is it the burst, or the load?
ARMS2 = [
    ("plainZR", ["NEW", 'CLOAD"ZR"']),
    ("bare", ["NEW", "CLOAD"]),
    ("progZR", ["NEW", '10 CLOAD"ZR"', "RUN"]),
]


# SET 3 (after scratchpad/csavetail_probe.out: CSAVE writes the end-link then
# SEVEN $00 on the VG-8020, the CF-3300 AND zerobas): the two-file tape built
# EXACTLY as CSAVE writes it -- neither of cas_encode's builders does (16 / 0).
ARMS3 = ARMS2[:2] + [("listZR", ["NEW", 'CLOAD"ZR"', "LIST"])]
# SET 4: is the fault the SKIP, or TAPION relocking over ANY leftover tail? A
# second bare CLOAD after a first one faces the same 7 unread $00 bytes.
ARMS4 = [("cload2", ["NEW", "CLOAD", "CLOAD", "LIST"])]
# SET 5: after D-CASRELOCK, kwtime STILL had no reference reading for CLOAD on
# the faithful tape -- so set 1's type-ahead arms again, on that tape.
ARMS5 = [(n + "7", ls) for n, ls in ARMS[:2]]
# SET 6: in a PROGRAM the VG-8020 printed no Skip/Found at all -- a silent load,
# or no load? LIST says which; PRINT after the CLOAD line says whether the
# program went on running.
ARMS6 = [("progLIST", ["NEW", '10 CLOAD"ZR"', '20 PRINT CHR$(91)+"GO]"', "RUN",
                       "LIST"])]
# SET 7: kwtime's zerobas side reached line 20's END mark AFTER the CLOAD had
# replaced the program; the VG-8020 only returned to direct mode. kwtime's exact
# shape, then the mark read back.
ARMS7 = [("markback", ["NEW", "7 POKE&HE000,201", '10 CLOAD"ZR"', "20 POKE&HE000,202",
                       "RUN", 'PRINT CHR$(91);PEEK(&HE000);"]"', "LIST"])]
# SET 8: does a SUCCESSFUL `CLOAD?` let the rest of its typed line run? (The
# D-CLOADPROG fix would end the line after any successful CLOAD; a verify
# leaves the program in place, so it may not.) Memory holds exactly ZQ's
# program, so the verify matches; a mismatch control proves the compare bites.
ARMS8 = [("verifyok", ["NEW", '10 PRINT"[Z9]"', 'CLOAD?"ZQ":PRINT CHR$(91)+"V]"']),
         ("verifybad", ["NEW", '10 PRINT"[Z7]"', 'CLOAD?"ZQ":PRINT CHR$(91)+"V]"'])]


def faithful_tape() -> str:
    import tempfile
    from cas_encode import build_cas_basic_nopad
    blob = b"".join(build_cas_basic_nopad(n, prog) + bytes(7)
                    for n, prog in ((kw.TAPE_NAME, kw.TAPE_PROGRAM),
                                    (kw.TAPE_NAME2, kw.TAPE_PROGRAM2)))
    fd, path = tempfile.mkstemp(suffix=".cas", prefix="zb_cload7_")
    os.write(fd, blob)
    os.close(fd)
    return path


def main():
    arms, machines = ARMS, sys.argv[1:]
    if machines and machines[0] == "--set2":
        arms, machines = ARMS2, machines[1:]
    if machines and machines[0] == "--set3":
        arms, machines = ARMS3, machines[1:]
    if machines and machines[0] == "--set4":
        arms, machines = ARMS4, machines[1:]
    if machines and machines[0] == "--set5":      # set 1's arms, faithful tape
        arms, machines = ARMS5, machines[1:]
    if machines and machines[0] == "--set6":
        arms, machines = ARMS6, machines[1:]
    if machines and machines[0] == "--set7":
        arms, machines = ARMS7, machines[1:]
    if machines and machines[0] == "--set8":
        arms, machines = ARMS8, machines[1:]
    for machine in (machines or ["Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_DISK"]):
        extra = kw._rig_kwargs(("tape",))
        extra.pop("_tape_path", None)
        extra["capture"] = "screen"
        if arms is not ARMS:
            extra["cap_gap"] = 200.0
        if arms in (ARMS3, ARMS4, ARMS5, ARMS6, ARMS7, ARMS8):
            extra["cassette"] = faithful_tape()
        caps = omsx_repl.run_cases(machine, [("direct", ls) for _n, ls in arms],
                                   reset=(), **extra)
        for (name, _ls), cap in zip(arms, caps):
            txt = cap or ""
            tail = [l.rstrip() for l in txt.splitlines() if l.strip()][-6:]
            print(f"{machine:28} {name:8} TA={'[TA]' in txt}  tail={tail}")


if __name__ == "__main__":
    main()
