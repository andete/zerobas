#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-KOFF23 -- what ACTUALLY happens on `WIDTH 40:CLS:KEY OFF:LOCATE 5,23`.

`missing-acceptance`'s `lr-key-off-23/24/255` report `<aborted>` on zerobas since
D-SCROLLBOUND, while `lr-key-off-22` passes. Two hypotheses have already been
wrong (an `inc`/`dec` drift, then `WIDTH` resetting CRTCNT -- writing CRTCNT
absolutely did not change the symptom), so this stops hypothesising and asks the
machine what the abort IS: a trapped ERROR, a wrong value, or no output at all.
Each case reports its own outcome by name so `<no reading>` cannot be mistaken
for a refusal.
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = ("C-BIOS_MSX1_EU_REPACK_DISK", "Philips_VG_8020")


def prog(*body: str) -> list[str]:
    lines = ["ON ERROR GOTO @T"] + list(body) + ["END", 'PRINT"<Qerr";ERR;">":END']
    lines[0] = "ON ERROR GOTO %d" % (10 * len(lines))
    for l in lines:
        assert len(l) <= 34, (len(l), l)
        assert "@" not in l, l
    return lines


CASES = [
    # the failing row, split so each step can be blamed, and read AFTER a CLS so
    # the answer cannot be scrolled off by the very print that reports it
    ("q22", prog("WIDTH 40", "CLS", "KEY OFF", "LOCATE 5,22",
                 "Y=CSRLIN", "X=POS(0)", "CLS", 'PRINT"<Q";Y;X;">"')),
    ("q23", prog("WIDTH 40", "CLS", "KEY OFF", "LOCATE 5,23",
                 "Y=CSRLIN", "X=POS(0)", "CLS", 'PRINT"<Q";Y;X;">"')),
    # is it the LOCATE, or the KEY OFF before it?
    ("q23_nokey", prog("WIDTH 40", "CLS", "LOCATE 5,23",
                       "Y=CSRLIN", "X=POS(0)", "CLS", 'PRINT"<Q";Y;X;">"')),
    # what does CRTCNT actually hold at that point?
    ("q_crtcnt", prog("WIDTH 40", "CLS", "KEY OFF",
                      "C=PEEK(&HF3B1)", "CLS", 'PRINT"<Q";C;">"')),
    # and with KEY ON, for the pair
    ("q_crt_on", prog("WIDTH 40", "CLS", "KEY ON",
                      "C=PEEK(&HF3B1)", "CLS", 'PRINT"<Q";C;">"')),
]


def main() -> int:
    for mach in MACHINES:
        print("===", mach, flush=True)
        specs = [("stored", lines) for _, lines in CASES]
        try:
            raws = omsx_repl.run_cases(mach, specs, batch=False, cap_gap=12.0)
        except Exception as exc:                       # noqa: BLE001
            print(f"  🔴 APPARATUS FAILURE on {mach}: "
                  f"{str(exc).splitlines()[0][:160]}", flush=True)
            continue
        for (name, _), raw in zip(CASES, raws):
            txt = " ".join("".join(raw or "").split())
            i = txt.rfind("<Q")
            j = txt.find(">", i + 1)
            cell = txt[i:j + 1] if i >= 0 and j > i else "<no reading>"
            print(f"  {name:11} {cell!r}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
