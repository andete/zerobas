#!/usr/bin/env python3
r"""D-NGRAM18 — one `req_gosub` for the four trap statements that demand GOSUB.

`call skip_spaces / cp gosub_token / jp nz,trap_syntax / inc hl` -- *the word
GOSUB belongs here* -- stands at four sites, one per trap verb:

  eos_common       ON STOP GOSUB
  ex_on_interval   ON INTERVAL=n GOSUB
  ex_on_strig      ON STRIG GOSUB
  ex_on_key        ON KEY GOSUB

📏 THE DENOMINATOR: five `cp gosub_token` sites in `basic/`. Four are this exact
run; the fifth (`ON x GOTO|GOSUB`'s dispatch) branches to two different labels
and shares no destination, so it cannot share a body -- the same rule that kept
the optional-comma sites out of `req_comma`.

BOTH HALVES, ONE ROW PER SITE: `g.*` supplies GOSUB (it must be CONSUMED, or the
line number after it is misread), `b.*` omits it (it must RAISE).
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
import omsx_repl                                                 # noqa: E402
import basic_probe_runtail as R                                  # noqa: E402

SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, step=2.5,
                   reset=("NEW",), missmsg="Syntax error"),
    "cf3300": dict(machine="National_CF-3300", boot=14.0, step=4.5,
                   reset=("", "SCREEN 0", "NEW"), missmsg="Syntax error"),
    "zb":     dict(machine=os.environ.get("ZEROBAS_BASIC_MACHINE",
                                          "C-BIOS_MSX1_EU_REPACK_DISK"),
                   boot=8.0, step=2.5, reset=("NEW",), missmsg="Syntax error"),
}
# a real target line, so a GOOD row is not confounded by "Undefined line number"
TGT = '100 RETURN'

CASES = [
    ("g.key",      [TGT, 'ON KEY GOSUB 100:PRINT "ZQ1"'],           -1),
    ("b.key",      [TGT, 'ON KEY 100'],                             -1),
    ("g.stop",     [TGT, 'ON STOP GOSUB 100:PRINT "ZQ1"'],          -1),
    ("b.stop",     [TGT, 'ON STOP 100'],                            -1),
    ("g.interval", [TGT, 'ON INTERVAL=100 GOSUB 100:PRINT "ZQ1"'],  -1),
    ("b.interval", [TGT, 'ON INTERVAL=100 100'],                    -1),
    ("g.strig",    [TGT, 'ON STRIG GOSUB 100:PRINT "ZQ1"'],         -1),
    ("b.strig",    [TGT, 'ON STRIG 100'],                           -1),
    # 🔬 IS THE `b.*` ERROR EVEN FROM THIS CHECK? A crunch-time rejection and a
    # runtime one both print `Syntax error` in direct mode. If the line STORES,
    # the crunch accepted it and the error is `req_gosub`'s; if `LIST` shows
    # nothing, the tokeniser refused it and every `b.*` row is blind to this
    # helper.
    ("x.storekey", ['10 ON KEY 100', 'LIST'],                       -1),
    # 🟢 CONTROLS: the ON x GOTO/GOSUB dispatch is the FIFTH `cp gosub_token`
    # site and shares no destination -- it must not move when the four do.
    ("ctl.ongosub", [TGT, 'A=1:ON A GOSUB 100:PRINT "ZQ2"'],        -1),
    ("ctl.ongoto",  ['100 PRINT"ZQ3"', 'A=1:ON A GOTO 100'],        -1),
    ("ctl.print",   ['PRINT "ZQ4"'],                                -1),
]


def run_side(side):
    cfg = SIDES[side]
    cases = [("direct", list(cfg["reset"]) + list(lines))
             for _, lines, _ in CASES]
    caps = omsx_repl.run_cases(cfg["machine"], cases, batch=False,
                               boot=cfg["boot"], step=cfg["step"])
    return {label: R.tail_after(raw, lines[subj], cfg["missmsg"])
            for (label, lines, subj), raw in zip(CASES, caps)}


def main():
    sides = (sys.argv[1] if len(sys.argv) > 1 else "vg8020,cf3300,zb").split(",")
    res = {s: run_side(s) for s in sides}
    w = max(len(l) for l, _, _ in CASES)
    diff, noor = [], []
    for label, _, _ in CASES:
        zb = str(res["zb"].get(label)) if "zb" in res else "-"
        refs = [str(res[s].get(label)) for s in sides if s != "zb"]
        same = all(r == zb for r in refs)
        if len(set(refs)) > 1:
            noor.append(label)
        elif refs and not same:
            diff.append(label)
        tag = "NO-OR" if label in noor else ("ok" if same else "DIFF")
        print(f"{tag:<6} {label:<{w}}  "
              + "  ".join(f"{s}={res[s].get(label)!r}" for s in sides))
    print(f"\nDIFF vs references: {len(diff)}/{len(CASES) - len(noor)} scorable"
          + ("  " + " ".join(diff) if diff else ""))
    if noor:
        print(f"⚠️  {len(noor)} NO-ORACLE (the references disagree): "
              + " ".join(noor))
    return 1 if diff else 0


if __name__ == "__main__":
    sys.exit(main())
