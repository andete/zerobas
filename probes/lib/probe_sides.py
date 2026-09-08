#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""probe_sides — the machine facts, in one place, so a probe stops re-deriving them.

WHY THIS EXISTS
===============
One fact — **the Philips VG-8020 has no disk drive and no Disk BASIC** — has now
produced THREE different failures in this tree, each in a different probe, each
written by someone who knew the fact:

  1. COMPARE against it wrongly. `basic_probe_kwsweep.py`'s own header records it:
     "every MK$/CV/Disk-BASIC row was comparing 'no disk ROM' against 'disk ROM'
     and attributing the difference to zerobas". That is why NEEDS-DISK exists.
  2. SCORE it as an oracle it cannot be. D-BAREFORM (2026-09-07) published SEVEN
     divergences of which FIVE were this: KILL/NAME/FIELD/LSET/RSET, where the
     CF-3300 AGREES with zerobas.
  3. MOUNT a disk image to it. D-ARGTYPE (2026-09-08) passed `diska` for every
     side; openMSX refuses the machine rather than ignoring the image --
     "Fatal error: No disk drive A present to put image ... in." -- so every row
     on that side came back <none>.

🎯 THE FACT WAS NEVER MISSING. It lives in a comment in one probe, and every
new probe copies a SIDES dict from whatever file was open last. A comment cannot
be imported; this can.

USE
===
    import probe_sides
    SIDES = probe_sides.sides("vg8020", "cf3300", "zb")
    ...
    dsk = probe_sides.diska(side, image_path)      # None where there is no drive
    verdict = probe_sides.verdict(vg, cf, zb)      # SAME / REFS-SPLIT / DIFF

`diska()` RETURNS None rather than raising for a driveless side, so the ordinary
call shape is safe; `require_disk()` is the loud form for a probe whose rows are
meaningless without a drive.
"""
from __future__ import annotations

import os

# machine, boot seconds, reset prologue, and WHAT THE HARDWARE HAS.
# `disk` is the one that keeps being got wrong; it is not a preference.
MACHINES: dict[str, dict] = {
    "vg8020": dict(machine="Philips_VG_8020", boot=8.0, reset=("NEW",),
                   disk=False, role="reference"),
    "cf3300": dict(machine="National_CF-3300", boot=14.0,
                   reset=("", "SCREEN 0", "NEW"), disk=True, role="reference"),
    "zb": dict(machine=os.environ.get("ZEROBAS_BASIC_MACHINE",
                                      "C-BIOS_MSX1_EU_REPACK_DISK"),
               boot=10.0, reset=("NEW",), disk=True, role="subject"),
    "zb_nodisk": dict(machine="C-BIOS_MSX1_EU_REPACK_NODISK", boot=10.0,
                      reset=("NEW",), disk=False, role="subject"),
}


def sides(*names: str) -> dict[str, dict]:
    """The SIDES dict a probe passes to run_cases, keyed as the probe names them."""
    bad = [n for n in names if n not in MACHINES]
    if bad:
        raise KeyError(f"unknown side(s) {bad}; known: {sorted(MACHINES)}")
    return {n: dict(MACHINES[n]) for n in names}


def diska(side: str, image: str | None) -> str | None:
    """The `diska=` value for this side: the image, or None where there is no drive.

    🔴 THIS IS THE WHOLE POINT OF THE MODULE. Passing an image to a driveless
    machine does not degrade gracefully -- openMSX exits before it boots, and the
    probe reads <none> on every row of that side, which looks like a hung machine
    rather than a mounting mistake.
    """
    if image is None:
        return None
    return image if MACHINES[side]["disk"] else None


def require_disk(*names: str) -> None:
    """Refuse, loudly, if any named side has no drive. For probes whose rows are
    meaningless without one -- better a stopped probe than a column of <none>."""
    missing = [n for n in names if not MACHINES[n]["disk"]]
    if missing:
        raise SystemExit(
            f"\U0001f534 probe_sides: {missing} ha{'s' if len(missing) == 1 else 've'} "
            f"NO DISK DRIVE, and this probe's rows need one. Use 'cf3300' as the "
            f"reference; the VG-8020 has no vote on anything Disk BASIC.")


def verdict(vg, cf, zb) -> str:
    """SAME / REFS-SPLIT / DIFF, with the oracle rule this tree already ruled on.

    TODO.md: "zerobas ships a disk ROM => the CF-3300 is the oracle, the cassette
    machines have no vote". So when the two references disagree the row is a
    REFS-SPLIT and zerobas is NOT scored on it -- it is not a defect, and calling
    it one is how D-BAREFORM published five that were not.
    """
    if vg != cf:
        return "REFS-SPLIT"
    return "SAME" if zb == cf else "DIFF"


def _selftest() -> int:
    """Each arm is one of the three failures above, in the order they happened."""
    ok = True

    # (3) mounting to a driveless machine.
    # The path is a SENTINEL, never opened -- `diska` either returns it or None.
    # It deliberately does not look like a temp path: `make temp-root-check`
    # rightly reddened on a system-temp literal here, and pinning it would have
    # spent an exception on a string that is not a file. (The checker matches the
    # literal in COMMENTS too, so this sentence names it rather than quoting it.)
    probe = "SENTINEL-NOT-A-PATH.dsk"
    if diska("vg8020", probe) is not None:
        print("\U0001f534 arm 3 FAILED: diska() handed an image to the driveless VG-8020")
        ok = False
    if diska("cf3300", probe) != probe:
        print("\U0001f534 arm 3 FAILED: diska() withheld the image from a machine that has a drive")
        ok = False

    # (2) scoring a refs-split as a zerobas divergence -- D-BAREFORM's KILL row
    if verdict("ERR 5", "ERR 24", "ERR 24") != "REFS-SPLIT":
        print("\U0001f534 arm 2 FAILED: a references disagreement scored as something else")
        ok = False
    if verdict("ERR 24", "ERR 24", "ERR 2") != "DIFF":
        print("\U0001f534 arm 2 FAILED: a real divergence was not called one")
        ok = False
    if verdict("ERR 24", "ERR 24", "ERR 24") != "SAME":
        print("\U0001f534 arm 2 FAILED: agreement was not called agreement")
        ok = False

    # (1) using the driveless machine as the oracle for a disk row
    try:
        require_disk("cf3300", "vg8020")
        print("\U0001f534 arm 1 FAILED: require_disk accepted the driveless VG-8020")
        ok = False
    except SystemExit:
        pass

    # and the table itself must still say what the arms assume
    if MACHINES["vg8020"]["disk"] or not MACHINES["cf3300"]["disk"]:
        print("\U0001f534 TABLE FAILED: the disk flags no longer match the arms above, "
              "so every arm is vacuous")
        ok = False

    print("probe_sides selftest: " + ("✅ all arms fire" if ok else "\U0001f534 FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(_selftest())
