#!/usr/bin/env python3
r"""D-CATUSR — does the numeric re-drive REACH the operand? Counted, not inferred.

D-CATTM left exactly one thing unmeasured, and said it decides the fix:

    whether the re-drive actually reaches the operand. THE ERROR CODE CANNOT
    TELL -- armed-and-outranked and never-evaluated both read 13. Separating
    them needs an operand with an observable SIDE EFFECT.

This is that operand. A five-byte routine at $D000

    21 10 D0   ld hl,$D010
    34         inc (hl)
    C9         ret

is POKEd in and installed with `DEFUSR`, so every evaluation of `USR(0)`
increments `$D010`. `PEEK($D010)` afterwards is a COUNT, not a verdict:

    0  the operand is never evaluated  -> a lower-priority arm CANNOT fix it
    1  evaluated exactly once          -> it can
    2  evaluated TWICE                 -> the hazard TODO.md filed is real

🎯 IT PRICES THE FILED HAZARD DIRECTLY. `TODO.md` barred a fix because evaluating
in `sct_err2` "would evaluate it TWICE -- and a string operand can contain a
`USR` call ... with side effects". This program IS that string operand.

🔴 DIRECT MODE, NOT A PROGRAM, AND THAT IS FORCED. The subject statement RAISES,
so inside a program the harness's `ON ERROR` handler reports and the run ends
before the counter can be read -- measured: every subject row came back
`ERR 13 AT 50` with no count at all. Typed at the prompt, the error prints and
the NEXT line still runs.

🟢 TWO CONTROLS, AND NEITHER IS OPTIONAL: `u.ctl` (`1+USR(0)`, no type fault)
must read 1, or a 0 elsewhere means "the USR never worked" rather than "never
evaluated"; `u.none` (`"AB"+5`, no USR at all) must read 0, or the counter is
being moved by something else in the setup.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
import omsx_repl                                                 # noqa: E402
import basic_probe_runtail as R                                  # noqa: E402

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5, reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "SCREEN 0", "NEW")),
    "zb":     dict(machine=os.environ.get("ZEROBAS_BASIC_MACHINE",
                                          "C-BIOS_MSX1_EU_REPACK_DISK"),
                   boot=8.0, step=2.5, reset=("NEW",)),
}
POKES = ['POKE-12288,33:POKE-12287,16',
         'POKE-12286,208:POKE-12285,52',
         'POKE-12284,201:DEFUSR=-12288']
COUNTER = -12272
READ = f'PRINT PEEK({COUNTER})'

CASES = [
    ("u.ctl",   POKES + [f'POKE{COUNTER},0', 'PRINT 1+USR(0)', READ]),
    ("u.cat",   POKES + [f'POKE{COUNTER},0', 'PRINT "AB"+USR(0)', READ]),
    ("u.catl",  POKES + [f'POKE{COUNTER},0', 'PRINT USR(0)+"AB"', READ]),
    ("u.none",  POKES + [f'POKE{COUNTER},0', 'PRINT "AB"+5', READ]),
    ("ctl.usr", POKES + [f'POKE{COUNTER},7', READ]),
]


def run_side(side):
    cfg = SIDES[side]
    cases = [("direct", list(cfg["reset"]) + list(lines)) for _, lines in CASES]
    caps = omsx_repl.run_cases(cfg["machine"], cases, batch=False,
                               boot=cfg["boot"], step=cfg["step"])
    return {label: R.tail_after(raw, lines[-1], "<none>")
            for (label, lines), raw in zip(CASES, caps)}


def main():
    sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
    res = {s: run_side(s) for s in sides}
    w = max(len(l) for l, _ in CASES)
    diff = []
    for label, _ in CASES:
        vals = [str(res[s].get(label)) for s in sides]
        same = len(set(vals)) == 1
        if len(sides) > 1 and not same:
            diff.append(label)
        print(f"{label:<{w}}  "
              + "  ".join(f"{s}={res[s].get(label)!r}" for s in sides)
              + ("   SAME" if same else "   DIFF"))
  # ⚠️ NOT `DIFF <n>/<m>`: `filed_row_sweep.py`'s MARKER counts a line
    # starting `DIFF ` as one more DIVERGING ROW, so a summary in that shape
    # inflates the count -- and with a colon it matches NOTHING and the sweep
    # reads the probe's pinned rows as no longer diverging. Fourth, fifth and
    # sixth instances of a class that had already bitten three times;
    # `rowshape-check` enforces it now (D-MARKERWORD).
    print(f"\n{len(diff)}/{len(CASES)} rows diverging"
          + ("  " + " ".join(diff) if diff else ""))
    print("READ u.cat AS A COUNT: 0 = never evaluated (a lower-priority arm "
          "cannot fix it); 1 = once (it can); 2 = twice (the filed hazard is real).")
    return 1 if diff else 0


if __name__ == "__main__":
    sys.exit(main())
