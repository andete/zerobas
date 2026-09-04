#!/usr/bin/env python3
r"""D-NAMEORD's diskless side -- the side-effect the entry named and nobody ran.

The reorder moves the `DISKSLOT_OK` check AHEAD of the new-name evaluation, so on
a machine with no drive `NAME"x"AS 5` can answer the no-disk error where a type
error would otherwise be due. The filed entry called this "unmeasured -- the
reference always has a drive".

🎯 IT IS MEASURABLE NOW. Diskless is an official build target whose oracle is the
Philips VG-8020, which has no drive either (Joost, 2026-09-03). So the question
is not "what would a driveless reference do" but "does zb-nodisk match its own
oracle" -- and that is an ordinary two-column reading.

Controls: `q.kill5` and `q.open5` are the same operand fault through verbs the
reorder did NOT touch, so a divergence in them says the fixture, not the change.

⚠️ THIS LIVES IN probes/ BECAUSE A GATE RUNS IT. It was written into scratchpad/
and wired straight to `make nameord-acceptance`, and run_gates' own selftest S6
("no emulator recipe leaves the fingerprint") went RED: the D-GATESKIP
fingerprint covers ROMs and probe/test/tool sources, NOT scratchpad, so editing
this file would not have invalidated the skip -- the battery could have skipped
the whole emulator tier while the gate's own probe had changed underneath it.
"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

SIDES = {
    "vg8020":    ("Philips_VG_8020", 8.0, ("NEW",)),
    "zb-nodisk": ("C-BIOS_MSX1_EU_REPACK_NODISK", 8.0, ("NEW",)),
}
CASES = [
    ("n.as5",    'NAME"X.DAT"AS 5',    "THE SUBJECT: new-name fault vs no-disk"),
    ("n.old5",   'NAME 5 AS"X.DAT"',   "old-name position, untouched by the reorder"),
    ("n.wf",     'NAME"A.DAT"AS"B.DAT"', "well formed: pure no-disk path"),
    ("q.kill5",  'KILL 5',             "CONTROL: same fault, verb not reordered"),
    ("q.open5",  'OPEN 5 AS #1',       "CONTROL: same fault, verb not reordered"),
    ("q.div0",   'KILL 1/0',           "CONTROL: the operand's own fault wins"),
]


def run(side, stmt):
    machine, boot, reset = SIDES[side]
    prog = ['10 ON ERROR GOTO 90', f'20 {stmt}', '30 PRINT"<0>":END',
            '90 PRINT"<";ERR;">":END', 'RUN']
    raw = omsx_repl.run_cases(machine, [("direct", list(reset) + prog)],
                              batch=False, reset=(), boot=boot, step=6.0,
                              cap_gap=10.0, timeout=300.0)[0] or ""
    m = re.findall(r"<([^<>]*)>", "".join(raw))
    return " ".join(m[-1].split()) if m else "<NO OUTPUT>"


bad = []
print(f"\n{'row':<9} {'vg8020':>9} {'zb-nodisk':>10}   statement")
for lab, st, why in CASES:
    a, b = run("vg8020", st), run("zb-nodisk", st)
    ok = a == b
    if not ok:
        bad.append(lab)
    print(f"{lab:<9} {a:>9} {b:>10}   {st:<22} {'ok' if ok else 'DIFF'}   {why}")
print(f"\nDIFF {len(bad)}/{len(CASES)}" + ("  " + " ".join(bad) if bad else ""))
sys.exit(1 if bad else 0)
