#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""fixture-integrity-check — the generated disk images must still be what the
generator produces.

🔴 WHY (D-FIXTUREPOLL, 2026-09-01). `disk/test720.dsk` is UNTRACKED and
GENERATED: commit `e7c5eab` removed it from git precisely to kill "the openMSX
write-back hazard on a committed image". The hazard did not go away -- it just
stopped being visible. A probe wrote a zero-byte `TS.DAT` into the local copy
(attr `$00`, where every generated file is `$20`), and:

  * `namspc-acceptance` went RED on a POSITIVE CONTROL and refused to measure --
    correctly, and nobody saw it, because the battery does not collect it;
  * D-FILESROT then "repaired" two frozen constants BY RE-MEASURING THE CF-3300
    AGAINST THE POLLUTED DISK, and froze `TS      .DAT` into both.

🎯 RE-MEASURING IS NOT ENOUGH IF THE THING MEASURED IS CONTAMINATED. "Re-measure,
never edit the constant into agreement" is the right rule and was followed to the
letter; it cannot see a bad input.

🔴 AND `make test-dsk` CANNOT CATCH IT: make is timestamp-driven, and a polluted
image is NEWER than its generator, so the rule is satisfied and nothing rebuilds.
The only way to know is to regenerate and compare, which is what this does --
hermetically, into a temp dir, never touching the working fixture.

Compares the DIRECTORY (name + attribute byte), not the whole image: sector
layout can legitimately differ (a boot stub rebuild), while a file appearing,
vanishing or changing attributes is always pollution.

Exit: 0 clean, 1 the fixture differs from a fresh generation, 2 the INSTRUMENT
could not measure.

    python3 tools/check_fixture_integrity.py [--selftest]
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import probe_tmp                       # noqa: E402,F401 -- sets tempfile.tempdir

FIXTURES = [("disk/test720.dsk", "tools/make_test_dsk.py")]


def directory(path: str) -> list[tuple[str, int]] | None:
    """[(8.3 name, attr), ...] of a FAT12 image's root, or None if unreadable."""
    try:
        d = open(path, "rb").read()
    except OSError:
        return None
    if len(d) < 1024:
        return None
    res = d[0x0E] | (d[0x0F] << 8)
    nfat = d[0x10]
    spf = d[0x16] | (d[0x17] << 8)
    nroot = d[0x11] | (d[0x12] << 8)
    if not (res and nfat and spf and nroot):
        return None
    root = (res + nfat * spf) * 512
    out = []
    for i in range(nroot):
        e = d[root + i * 32: root + i * 32 + 32]
        if len(e) < 32 or e[0] == 0x00:
            break
        if e[0] == 0xE5 or (e[11] & 0x08):        # deleted / volume label
            continue
        out.append((e[0:11].decode("latin1"), e[11]))
    return out


def check(root=ROOT) -> int:
    rc = 0
    for rel, gen in FIXTURES:
        live = os.path.join(root, rel)
        if not os.path.exists(live):
            print(f"   {rel}: absent — nothing to check (`make test-dsk` builds it)")
            continue
        work = tempfile.mkdtemp(prefix="fixture-")
        try:
            fresh = os.path.join(work, os.path.basename(rel))
            p = subprocess.run([sys.executable, os.path.join(root, gen), fresh],
                               capture_output=True, text=True, cwd=root)
            if p.returncode != 0:
                print(f"INSTRUMENT: {gen} failed, so {rel} is UNMEASURED:\n"
                      + (p.stdout + p.stderr)[-1500:])
                return 2
            a, b = directory(live), directory(fresh)
            if a is None or b is None:
                print(f"INSTRUMENT: could not read a FAT12 root from "
                      f"{'the working fixture' if a is None else 'the regeneration'}")
                return 2
            if a == b:
                print(f"   {rel}: {len(a)} entr(y/ies), identical to a fresh "
                      f"generation")
                continue
            extra = [x for x in a if x not in b]
            missing = [x for x in b if x not in a]
            print(f"🔴 {rel} IS NOT WHAT THE GENERATOR PRODUCES — it has been "
                  f"written into (openMSX write-back, or a probe using it as "
                  f"scratch). Every disk probe reads this image, so its answers "
                  f"are about a fixture nobody described:")
            for n, at in extra:
                print(f"     EXTRA   {n!r} attr=${at:02X}")
            for n, at in missing:
                print(f"     MISSING {n!r} attr=${at:02X}")
            print(f"     → `rm {rel} && make test-dsk` (it is generated and "
                  f"untracked; `make test-dsk` alone will NOT rebuild it, "
                  f"because make only compares timestamps).")
            rc = 1
        finally:
            shutil.rmtree(work, ignore_errors=True)
    if rc == 0:
        print("fixture-integrity: every generated disk image matches its generator.")
    return rc


def selftest() -> int:
    ok = True

    def arm(name, cond):
        nonlocal ok
        print(f"{'PASS' if cond else '🔴 FAIL'}  {name}")
        ok = ok and bool(cond)

    arm("S1 the live tree is clean", check() == 0)
    tmp = tempfile.mkdtemp(prefix="fixself-")
    os.makedirs(os.path.join(tmp, "disk"), exist_ok=True)
    os.makedirs(os.path.join(tmp, "tools"), exist_ok=True)
    shutil.copy(os.path.join(ROOT, "tools", "make_test_dsk.py"),
                os.path.join(tmp, "tools", "make_test_dsk.py"))
    live = os.path.join(tmp, "disk", "test720.dsk")
    subprocess.run([sys.executable, os.path.join(tmp, "tools", "make_test_dsk.py"),
                    live], capture_output=True, cwd=tmp)
    arm("S2 a freshly generated fixture is clean (the control)", check(tmp) == 0)
    # plant the exact pollution that was found: one extra directory entry
    d = bytearray(open(live, "rb").read())
    res, nfat = d[0x0E] | (d[0x0F] << 8), d[0x10]
    spf = d[0x16] | (d[0x17] << 8)
    root = (res + nfat * spf) * 512
    slot = root
    while d[slot] != 0x00:
        slot += 32
    d[slot:slot + 11] = b"TS      DAT"
    d[slot + 11] = 0x00
    open(live, "wb").write(bytes(d))
    arm("S3 an extra directory entry goes RED", check(tmp) == 1)
    arm("S4 ...and the report is not fooled into calling it MISSING",
        directory(live) is not None and len(directory(live)) == 6)
    shutil.rmtree(tmp, ignore_errors=True)
    print("selftest:", "GREEN" if ok else "🔴 RED")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    raise SystemExit(check())
