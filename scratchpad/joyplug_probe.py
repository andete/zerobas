#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-JOYPLUG -- RE-VERIFY the filed "no joystick pluggable" blocker.

Joost ruled 2026-09-17: *"STICK, STRIG, PAD: we should come up with a way to
test, if needed create a testing pluggable device."* The filed blocker says no
joystick is pluggable in this openMSX, that injection is the MSX key matrix only,
and that `joystickports` will not take a write. ⚠️ ITS PREMISE IS ALREADY
DOUBTFUL: openMSX **21.0** here names `msxjoystick1` / `msxjoystick2` and the
connectors `joyporta` / `joyportb` (read out of the shipped binary), so the
finding may simply have looked under an older name. Twelve blockers were
re-verified in one session and twelve were stale, so this is a re-verification
before it is a build.

THREE QUESTIONS, cheapest first:
  1. Does `plug joyporta msxjoystick1` SUCCEED? (If the pluggable does not exist
     the prologue errors and every row below is apparatus, not a reading.)
  2. With it plugged and nothing pressed, what do `STICK(1)` and `STRIG(1)` read?
     ⚠️ 0 and 0 are ALSO what a stub returns and what nothing-plugged returns, so
     this row cannot award anything -- it is here to prove the plug did not
     BREAK the reads.
  3. 🎯 THE ONE THAT MATTERS: can anything DRIVE it? `msxjoystick` takes host
     input, and this harness injects the MSX KEY MATRIX -- a different layer --
     so the honest answer may be "plugged but undrivable", which would keep the
     blocker alive for a NEW reason and point straight at Joost's "create a
     testing pluggable device".

🔴 STICK(0) IS THE KEYBOARD, NOT A JOYSTICK, and is the control: it must keep
reading the arrow-key state with a joystick plugged, or the plug has disturbed
something it should not.
🔴 AND THE FIRST CUT'S CONTROL FAILED, WHICH IS WHY THERE IS ONE: every cell read
0, including the arrow-UP row that must read 1. The cause was not the joystick --
`holds` presses at the RUN SLOT and the cases were DIRECT mode, which has no RUN.
A run whose control is flat is apparatus, not a reading, however plausible the
zeroes looked.
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

# 🎯 THE REFERENCE IS IN THIS PROBE NOW, and it changed the question. `STICK(0)`
# is the KEYBOARD direction pad and needs NO joystick at all -- so if the
# reference answers 1 with arrow-UP held and we answer 0, the divergence is ours
# and it is reachable WITHOUT any pluggable device.
MACHINES = ("C-BIOS_MSX1_EU_REPACK_DISK", "Philips_VG_8020")

# row 8 bits 4/5/6/7 are left/up/down/right on the published MSX matrix; the
# `holds` rig presses them at one emulated instant.
CASES = [
    ("j0_stick1",  ['PRINT"<J";STICK(1);">"'],      None),
    ("j1_strig1",  ['PRINT"<J";STRIG(1);">"'],      None),
    ("j2_stick0",  ['PRINT"<J";STICK(0);">"'],      None),
    # the keyboard control, arrow UP held: STICK(0) must answer 1
    ("j3_kbd_up",  ['PRINT"<J";STICK(0);">"'],      (8, 0x20)),
    # and with UP held, does the PLUGGED joystick see anything? (it should not --
    # the key matrix is not its input -- and saying so is the finding)
    ("j4_joy_up",  ['PRINT"<J";STICK(1);">"'],      (8, 0x20)),
]

PLUG = ("plug joyporta msxjoystick1",)


def main() -> int:
    for MACH in MACHINES:
      for label, prologue in (("PLUGGED", PLUG), ("UNPLUGGED", ())):
        print(f"=== {MACH}  [{label}]", flush=True)
        specs, holds = [], []
        for _, body, hold in CASES:
            # 🔴 STORED, NOT DIRECT: `holds` presses at the RUN SLOT (see
            # omsx_repl's own note), and a direct-mode case has no RUN -- the
            # first cut used "direct" and its keyboard CONTROL read 0 where it
            # must read 1, which is the control earning its place.
            specs.append(("stored", body))
            holds.append(hold)
        kw = {"prologue": prologue} if prologue else {}
        try:
            raws = omsx_repl.run_cases(MACH, specs, batch=False, cap_gap=8.0,
                                       holds=holds, **kw)
        except TypeError:
            # `holds` is indexed per case; if this build spells it differently,
            # fall back to no holds rather than guessing and say so.
            print("  ⚠️ this omsx_repl does not take `holds` here -- "
                  "running WITHOUT the key presses; j3/j4 are then vacuous",
                  flush=True)
            try:
                raws = omsx_repl.run_cases(MACH, specs, batch=False,
                                           cap_gap=8.0, **kw)
            except Exception as exc:                   # noqa: BLE001
                print(f"  🔴 APPARATUS FAILURE: {str(exc).splitlines()[0][:160]}",
                      flush=True)
                continue
        except Exception as exc:                       # noqa: BLE001
            print(f"  🔴 APPARATUS FAILURE: {str(exc).splitlines()[0][:160]}",
                  flush=True)
            continue
        for (name, _, _), raw in zip(CASES, raws):
            txt = " ".join("".join(raw or "").split())
            i = txt.rfind("<J")
            j = txt.find(">", i + 1)
            cell = txt[i:j + 1] if i >= 0 and j > i else "<no reading>"
            print(f"  {name:11} {cell!r}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
