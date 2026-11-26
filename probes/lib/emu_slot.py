#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""⏱ B4 (2026-11-25, docs/gate-time-review-2026-11-25.md): ONE HOST-WIDE EMULATOR BUDGET.

The battery runs J units at once and many units bring their own pools (spec-live, ctllim, ramfree, biosregs,
lof, badfnum, kwsweep), so the early battery runs 25+ emulators on 10 cores -- the condition the stall watchdog and
the serial retry exist for. With ZEROBAS_EMU_SLOTS=N set, omsx_preflight.guarded() starts every openMSX through this
wrapper: it takes an exclusive flock on one of N slot files (waiting while all N are held) and EXECs the emulator
with that descriptor still open, so the slot is held exactly as long as the emulator runs -- same pid, so a
watchdog's kill reaches it -- and is released by the kernel when it exits, however it exits.

Unset (the default), guarded() does not use this at all.

    python3 probes/lib/emu_slot.py openmsx -machine ...        (guarded() builds this argv)
    python3 probes/lib/emu_slot.py --selftest
"""
import fcntl
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import probe_tmp  # noqa: E402  -- the one temp root

SLOT_DIR = os.path.join(probe_tmp.ROOT, "emu_slots")


def acquire(n: int) -> int:
    """an fd holding an exclusive lock on one of n slot files (blocks until one is free)"""
    os.makedirs(SLOT_DIR, exist_ok=True)
    while True:
        for i in range(n):
            fd = os.open(os.path.join(SLOT_DIR, str(i)), os.O_CREAT | os.O_RDWR, 0o644)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return fd
            except BlockingIOError:
                os.close(fd)
        time.sleep(0.02)


def selftest() -> int:
    import subprocess
    ok = True

    def arm(name, cond):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL'}  {name}")
        ok = ok and cond
    held = [acquire(2), acquire(2)]
    t = time.time()
    p = subprocess.Popen([sys.executable, __file__, sys.executable, "-c", "pass"],
                         env=dict(os.environ, ZEROBAS_EMU_SLOTS="2"))
    time.sleep(0.4)
    arm("E1 with every slot held, a launch WAITS", p.poll() is None)
    os.close(held.pop())
    p.wait(timeout=10)
    arm("E2 ...and runs as soon as one is released", p.returncode == 0 and time.time() - t >= 0.4)
    os.close(held.pop())
    r = subprocess.run([sys.executable, __file__, sys.executable, "-c", "import sys; sys.exit(7)"],
                       env=dict(os.environ, ZEROBAS_EMU_SLOTS="1"))
    arm("E3 the emulator's own exit code comes back (exec, not a child)", r.returncode == 7)
    print("selftest:", "GREEN" if ok else "RED")
    return 0 if ok else 1


def main(argv) -> int:
    if argv[:1] == ["--selftest"]:
        return selftest()
    n = int(os.environ.get("ZEROBAS_EMU_SLOTS") or 0)
    if n > 0:
        fd = acquire(n)
        os.set_inheritable(fd, True)        # held across the exec, released when the emulator exits
    os.execvp(argv[0], argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
