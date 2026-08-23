#!/usr/bin/env python3
"""D-MISSOP follow-up — CIRCLE's OTHER trailing slots, and the boot banner.

Two questions this slice's own result raised and did not answer.

(a) `circle.val` (`CIRCLE(50,50),20,`) survived the ev_f_err fix because CIRCLE's
    grammar walk lives in a sub-ROM tenant (sub/circleparse.asm) that decides for
    itself that the colour is absent -- `eval` is never called, so ev_f_err can
    never see it. `cpt_at_start` and `cpt_after_aspect` have the SAME SHAPE, so
    CIRCLE probably has three more slots with the same hole. MEASURE THEM, so the
    filing carries a size instead of a guess.

(b) 🔴 THE BOOT BANNER. This slice funded itself by PROMOTING basic/title.asm
    from page 1 into the low region. Nothing in the gate battery looks at the
    banner -- every probe program starts with CLS, which wipes it. So the one
    thing the promotion could plausibly break is the one thing no gate reads.
    Row `banner` prints a fenced marker WITHOUT clearing the screen, and the
    checker asserts the startup header is still above it.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

ZB_M = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
SIDES = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW",)),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW")),
    "zb":     dict(machine=ZB_M, boot=8.0, reset=("NEW",)),
}


def case(stmt, setup="SCREEN2"):
    return ["10 ONERRORGOTO900",
            f"15 {setup}",
            f"20 {stmt}",
            '30 R=0:SCREEN0:CLS:PRINT"[";ERR;R;"]":END',
            '900 R=0:SCREEN0:CLS:PRINT"[";ERR;R;"]":END']


CASES = {
    'c.colour': case("CIRCLE(50,50),20,"),          # already measured: the known hole
    'c.start':  case("CIRCLE(50,50),20,5,"),        # start angle omitted after its comma
    'c.end':    case("CIRCLE(50,50),20,5,0.1,"),    # end angle omitted
    'c.aspect': case("CIRCLE(50,50),20,5,0.1,0.2,"),  # aspect omitted
    # the control: every slot present
    'c.ok':     case("CIRCLE(50,50),20,5,0.1,0.2,1"),
}

BR = re.compile(r"\[([^\]]*)\]")
NUM = re.compile(r"^[-0-9. ]*$")


def face(cap):
    if cap is None:
        return "<NO CAPTURE>"
    for m in BR.finditer("".join(cap)):
        if NUM.match(m.group(1)):
            return " ".join(m.group(1).split()) or "<EMPTY>"
    return "<NO OUTPUT>"


def main():
    only, sides = None, ["vg8020", "cf3300", "zb"]
    for a in sys.argv[1:]:
        if a.startswith("--sides="):
            sides = [x for x in a.split("=", 1)[1].split(",") if x in SIDES]
        else:
            only = a.split(",")

    # --- (b) the banner check: zerobas only, no CLS anywhere ----------------
    if not only or "banner" in only:
        cfg = SIDES["zb"]
        caps = omsx_repl.run_cases(
            cfg["machine"], [("direct", ['10 PRINT"[";7;0;"]"', "RUN"])],
            batch=False, boot=cfg["boot"], step=3.0, cap_gap=8.0, timeout=300.0)
        scr = caps[0] or ""
        ok = "zerobas version" in scr and "clean-room" in scr
        print(f"  banner   {'PRESENT' if ok else '🔴 GONE'}  "
              f"(marker {face(caps[0])!r})")
        if not ok:
            print("  🔴 THE PROMOTION OF basic/title.asm BROKE THE BOOT HEADER")
        if only:
            return

    labels = [l for l in CASES if not only or any(o in l for o in only)]
    faces = {}
    for s in sides:
        cfg = SIDES[s]
        faces[s] = {}
        for l in labels:
            caps = omsx_repl.run_cases(
                cfg["machine"],
                [("direct", list(cfg["reset"]) + CASES[l] + ["RUN"])],
                batch=False, boot=cfg["boot"], step=3.0, cap_gap=8.0,
                timeout=300.0)
            faces[s][l] = face(caps[0])
            print(f"  ran {s:7s} {l}", flush=True)
    print()
    W = max(len(l) for l in labels)
    ndiff = 0
    for l in labels:
        vals = {s: faces[s][l] for s in sides}
        refs = {vals[s] for s in sides if s != "zb"}
        line = f"  {l:<{W}}  " + "  ".join(f"{s}={vals[s]!r}" for s in sides)
        if not refs:
            print(line + "   (zb only)")
            continue
        if len(refs) != 1:
            note = "   ⚠️ THE REFERENCES DISAGREE — not a want"
        elif any("<NO" in v for v in vals.values()):
            note = "   .... NOT MEASURED"
        elif vals["zb"] not in refs:
            note = "   🔴 DIFF"
            ndiff += 1
        else:
            note = ""
        print(line + note)
    print(f"\nROWS: {len(labels)} printed — {ndiff} DIFF")


if __name__ == "__main__":
    main()
