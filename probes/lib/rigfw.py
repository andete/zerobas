#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""rigfw -- drive the RP2040-Zero input rig (tools/rigfw/rigfw.ino) from a probe.

The board is a REAL USB joystick (+ mouse) whose state is set over its CDC
serial port, one command per line, each answered `OK` or `ERR: ...`. The host
-- and therefore SDL inside a headless openMSX -- sees a genuine joystick, which
is what openMSX's own Tcl can never provide (D-RIGBLOCK, D-RIGFW).

    port = rigfw.find()            # None when no board answers `id`
    rigfw.set_state(port, "upright+trig1")
    ...                            # boot openMSX with rigfw.PROLOGUE
    rigfw.set_state(port, "centre")

A STATE is `+`-joined words: at most one direction (`centre`, `up`, ...,
`downright`) and any of `trig1`, `trig2`. It is applied from a known origin --
centre, both triggers released -- so a state never inherits the last one.
`pulse` makes the named triggers PRESS AND RELEASE at ~2 Hz instead of being
held (see `Pulser`).

⚠️ THE BOARD MOVES THE HOST, NOT ONLY THE EMULATOR: whatever runs on the Mac
sees the same joystick. Joost's rule (2026-09-26): rig runs after 08:00 and not
while he is playing a game.
"""
import glob
import os
import select
import termios
import time

DIRECTIONS = ("centre", "up", "down", "left", "right",
              "upleft", "upright", "downleft", "downright")
TRIGGERS = ("trig1", "trig2")
PULSE = "pulse"
PULSE_HALF = 0.25       # seconds down, then seconds up

# 🔴 openMSX 21 HAS NO `joystick1` PLUGGABLE: a host stick reaches the MSX only
# through `msxjoystick1`, bound by `msxjoystick1_config` -- which is EMPTY on this
# install, so nothing is bound until a probe binds it. Each binding is its own
# braced element (`{joy1 -axis1}` alone is `Invalid binding: joy1`).
# `save_settings_on_exit false` comes FIRST: openMSX rewrites
# ~/.openMSX/share/settings.xml on exit, and the binding must not persist into
# every other probe's emulator.
CONFIG = ("UP {{joy1 -axis1}} DOWN {{joy1 +axis1}} LEFT {{joy1 -axis0}} "
          "RIGHT {{joy1 +axis0}} A {{joy1 button0}} B {{joy1 button1}}")
PROLOGUE = ("set save_settings_on_exit false",
            "plug joyporta msxjoystick1",
            "set msxjoystick1_config {" + CONFIG + "}")


def prologue(state: str) -> tuple[str, ...]:
    """The openMSX prologue for a run held in `state`.

    The state itself is written in (`::zb_rig_state`) so the reference cache
    keys on it -- the board is set OUTSIDE the emulator call.
    🔴 A PULSE STATE TURNS THROTTLE BACK ON. The harness runs openMSX
    `throttle off`, and a whole boot-type-RUN-capture took 1.8 s of wall time:
    a 120-FRAME wait passed in milliseconds, so the board's 2 Hz presses never
    landed inside it (a polled count read 0 transitions). Throttled, emulated
    time is wall time and the pulse is inside every wait. Held states do not need
    it -- a constant does not care about the clock."""
    _d, _t, pulse = parse_state(state)
    return PROLOGUE + (("set throttle on",) if pulse else ()) + (
        f"set ::zb_rig_state {{{state}}}",)


def parse_state(state: str) -> tuple[str, tuple[str, ...], bool]:
    """`upright+trig1` -> ("upright", ("trig1",), False); `pulse+trig1` ->
    ("centre", ("trig1",), True). Refuses anything else, and `pulse` with no
    trigger to pulse."""
    words = [w for w in state.lower().split("+") if w]
    pulse = PULSE in words
    words = [w for w in words if w != PULSE] if pulse else words
    dirs = [w for w in words if w in DIRECTIONS]
    trigs = tuple(w for w in words if w in TRIGGERS)
    if len(dirs) > 1 or len(dirs) + len(trigs) != len(words) \
            or len(set(trigs)) != len(trigs) or not words \
            or state.lower().split("+").count(PULSE) > 1 or (pulse and not trigs):
        raise ValueError(f"rigfw: not a rig state: {state!r}")
    return (dirs[0] if dirs else "centre"), trigs, pulse


def _open(port: str) -> int:
    fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    a = termios.tcgetattr(fd)
    a[3] &= ~(termios.ECHO | termios.ICANON)
    termios.tcsetattr(fd, termios.TCSANOW, a)
    return fd


def _ask(fd: int, cmd: str, timeout: float = 1.5) -> list[str]:
    """Send one command; -> the reply lines up to and including OK/ERR."""
    os.write(fd, (cmd + "\n").encode())
    buf, t0 = b"", time.time()
    while time.time() - t0 < timeout:
        r, _, _ = select.select([fd], [], [], 0.1)
        if r:
            buf += os.read(fd, 256)
            lines = buf.decode(errors="replace").replace("\r", "").split("\n")
            if any(l == "OK" or l.startswith("ERR") for l in lines):
                return [l for l in lines if l]
    return [l for l in buf.decode(errors="replace").replace("\r", "").split("\n") if l]


def find() -> str | None:
    """The serial port of a board answering `id` with `rigfw 1`, or None.

    `ZEROBAS_RIG=off` answers None without touching any port: the board-absent
    path (kwsweep's carried verdicts) is testable with the board still plugged."""
    if os.environ.get("ZEROBAS_RIG", "").lower() in ("off", "0", "no"):
        return None
    for port in sorted(glob.glob("/dev/cu.usbmodem*")):
        try:
            fd = _open(port)
        except OSError:
            continue
        try:
            if _ask(fd, "id")[-2:] == ["rigfw 1", "OK"]:
                return port
        except OSError:
            pass
        finally:
            os.close(fd)
    return None


def set_state(port: str, state: str) -> None:
    """Put the stick in `state`, from centre with both triggers released.
    Raises on any reply but OK -- a rig that silently dropped a command would
    let a row score a direction it never set."""
    direction, trigs, pulse = parse_state(state)
    cmds = [direction] + [f"{t} {'on' if t in trigs and not pulse else 'off'}"
                          for t in TRIGGERS]
    fd = _open(port)
    try:
        for c in cmds:
            reply = _ask(fd, c)
            if reply[-1:] != ["OK"]:
                raise RuntimeError(f"rigfw: {c!r} -> {reply!r}")
    finally:
        os.close(fd)


class Pulser:
    """Press and release `triggers` every PULSE_HALF seconds until stopped.

    🔴 WHY IT EXISTS: THE STRIG TRAP FIRES ON A PRESS, NOT ON A HELD BUTTON.
    `onstrig_rig` first held trigger 1 from before boot and read 0 on BOTH
    machines -- no press ever happened while the program waited, so the agreeing
    0 was the stub's value (D-RIGFW). The key-matrix rows never met this: their
    hold starts AFTER `RUN`. A pulse puts presses inside any wait window without
    knowing when the program starts. Use as a context manager around the run."""

    def __init__(self, port: str, triggers: tuple[str, ...]):
        import threading
        self.port, self.triggers = port, triggers
        self.stop = threading.Event()
        self.error: Exception | None = None
        self.presses = 0
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        try:
            fd = _open(self.port)
            try:
                while not self.stop.is_set():
                    for on in (True, False):
                        for t in self.triggers:
                            reply = _ask(fd, f"{t} {'on' if on else 'off'}")
                            if reply[-1:] != ["OK"]:
                                raise RuntimeError(f"rigfw pulse: {t} -> {reply!r}")
                        self.presses += on
                        self.stop.wait(PULSE_HALF)
            finally:
                for t in self.triggers:
                    _ask(fd, f"{t} off")
                os.close(fd)
        except Exception as e:      # surfaced by __exit__, never swallowed
            self.error = e

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.stop.set()
        self.thread.join(timeout=5)
        if self.error is not None and exc[0] is None:
            raise self.error
        return False


def selftest() -> int:
    """The state parser, device-free. Negative arms first."""
    bad = ["", "+", "up+down", "trig3", "up+trig1+trig1", "sideways", "up trig1",
           "pulse", "pulse+up", "pulse+pulse+trig1"]
    good = {"centre": ("centre", (), False),
            "upright+trig1": ("upright", ("trig1",), False),
            "trig2": ("centre", ("trig2",), False),
            "TRIG1+left": ("left", ("trig1",), False),
            "down+trig1+trig2": ("down", ("trig1", "trig2"), False),
            "pulse+trig1": ("centre", ("trig1",), True),
            "trig2+pulse+left": ("left", ("trig2",), True)}
    fails = 0
    for s in bad:
        try:
            parse_state(s)
            print(f"FAIL accepted {s!r}")
            fails += 1
        except ValueError:
            print(f"ok   refused  {s!r}")
    for s, want in good.items():
        got = parse_state(s)
        ok = got == want
        fails += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {s!r} -> {got}")
    print(f"\nrigfw selftest: {len(bad) + len(good) - fails}/{len(bad) + len(good)}")
    return 1 if fails else 0


if __name__ == "__main__":
    import sys
    sys.exit(selftest())
