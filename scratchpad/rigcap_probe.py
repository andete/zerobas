#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-RIGBLOCK: what can openMSX actually DRIVE?  Ruling 4's rig, priced.

Joost ruled that `KEY`'s display forms, `PAD`'s switch and `STICK`/`STRIG`'s
joystick halves should get a RIG rather than an exemption. Three of those four
turn on one question this asks the emulator directly instead of assuming:
**which joyport devices exist, and can the port state be forced any other way?**

`tools/kwforms.py` already said the switch "cannot get a row -- openMSX offers no
host button to press" and that the joystick forms need a HOST joystick. That was
an assertion. This is the measurement, and it is worse than the assertion:

  * `plug joyporta <dev>` ACCEPTS  mouse, trackball, arkanoidpad, paddle,
    ninjatap, touchpad
  * and REFUSES  joystick1, joystick2, keyjoystick1, keyjoystick2
    -- "No such pluggable". THERE IS NO JOYSTICK IN THIS openMSX AT ALL, with or
    without a host stick, so `NEEDS-PLUG:` can never reach `STICK(1)`/`STRIG(1)`.
  * the only input-injection commands are `keymatrixdown` / `keymatrixup`, which
    is the MSX KEY MATRIX -- the half `stick_hold`/`strig_hold` already cover.
  * the `joystickports` debuggable READS (63 = every line idle, correct for an
    empty port) and **will not take a write**: `debug write` is accepted and the
    next read still says 63, because the value is recomputed from the connector.

\U0001f3af So the three forms are INSTRUMENT-BLOCKED, and this is the evidence rather
than a shrug. Re-run it against a future openMSX: if `joystick1` ever plugs, or
`joystickports` ever holds a written value, the rig becomes possible that day.
"""
import os, subprocess, sys, tempfile

DEVICES = ("joystick1", "joystick2", "keyjoystick1", "keyjoystick2",
           "mouse", "trackball", "arkanoidpad", "paddle", "ninjatap", "touchpad")


def main() -> int:
    out = os.path.join(tempfile.gettempdir(), "rigcap.txt")
    tcl = ['set f [open %s w]' % out,
           'puts $f "connectors: [plug]"']
    for d in DEVICES:
        tcl.append('if {[catch {plug joyporta %s} r]} { puts $f "%s -> NO ($r)" } '
                   'else { puts $f "%s -> OK" ; catch {unplug joyporta} }' % (d, d, d))
    tcl += ['puts $f "joystickports size: [debug size joystickports]"',
            'puts $f "joystickports read: [debug read joystickports 0]"',
            'catch {debug write joystickports 0 0xEF}',
            'puts $f "joystickports read after write: [debug read joystickports 0]"',
            'close $f', 'exit']
    # 🔴 HEADLESS AND BOUNDED (2026-09-27): this ran openMSX with the DEFAULT
    # renderer and no timeout, so the 2026-09-27 filed-row sweep opened a real
    # WINDOW on Joost's screen at night and hung until the sweep's 600 s cap --
    # the standing rule is renderer none + sound null + a subprocess timeout.
    # save_settings_on_exit off: the plug/unplug loop must not persist.
    try:
        subprocess.run(["openmsx", "-machine", "Philips_VG_8020",
                        "-command", "set save_settings_on_exit false; "
                        "set renderer none; set sound_driver null",
                        "-command", "\n".join(tcl)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=60)
    except subprocess.TimeoutExpired:
        print("openMSX did not exit within 60 s -- the query hung")
        return 1
    if not os.path.exists(out):
        print("openMSX produced nothing -- the query itself failed")
        return 1
    print(open(out).read().rstrip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
