#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""C-BIOS-target BDOS self-consistency gate — the disk ROM's DOS layer, on C-BIOS.

WHY THIS EXISTS. The standing `bdos-acceptance` gate (disk_bdos_acceptance.py) proves
our disk ROM's whole MSX-DOS-1 BDOS surface is 0-byte-identical to the stock oracle --
but ONLY on the CF-3300 host (`National_CF-3300_ZEROBASDISK`), because a *differential*
needs a genuine stock reference to diff against, and C-BIOS has none. That left a real
blind spot: nothing exercised the disk ROM's MSX-DOS boot + BDOS calls on the actual
**C-BIOS target** (`C-BIOS_MSX1_EU_BASIC_DISK`), the machine we actually ship for. The
two-interface rule ASSUMED disk-ROM<->main-BIOS is BIOS-agnostic, so CF-3300-only was
deemed enough for the DOS layer. The `$F340` cold/warm-boot bug
(tier2-cbios-dosboot-autoexec-f340.md) falsified that assumption: a genuinely
BIOS-dependent seam (C-BIOS's `$C9` RAM fill vs the real BIOS's `$FF`) sat in the
DOS-boot path and was structurally unreachable by the CF-3300 gate. It survived until
the first close look at DOS-on-C-BIOS this session.

WHAT IT ASSERTS. There is no stock C-BIOS+DOS oracle to diff against, so this is a
SELF-CONSISTENCY gate, not a differential: it re-captures the SAME memory regions the
BDOSX exercisers already pin (the FCB/data/register-buffer evidence proven
0-byte-identical to stock on the CF-3300), once on the CF-3300 host and once on the
C-BIOS host, and asserts the two buffers are BYTE-IDENTICAL. Both runs use our OWN disk
ROM (only the host BIOS differs), so any byte that differs is a BIOS-dependent behaviour
of our DOS layer -- exactly the class `$F340` belongs to. Identical buffers = the BDOS
surface is BIOS-independent, i.e. what the CF-3300 gate proved against stock also holds
on the shipped C-BIOS target.

HOW. It reuses the build scripts as the single source of truth for the anchors/regions
(same as disk_bdos_acceptance.py): it runs each `build_bdosx*_disk.py`, harvests the
`disk_probe_diff.py capture ... --mem ...` commands, and for each region runs a one-sided
`capture --machine ours` twice -- once with the default CF-3300 host, once with
ZEROBAS_OURS_MACHINE=<C-BIOS machine> -- then compares the printed `memory ...:` buffers.
`callseq`/`screen` probes are not self-consistency-comparable this way (the boot/console
call sequence legitimately differs between BIOS hosts) and are skipped; the capture
buffers are the ROM-behaviour evidence.

The exercisers launch via AUTOEXEC.BAT (zero typed keys), which itself only fires on the
C-BIOS host BECAUSE of the `$F340` fix -- so if that fix regresses, the C-BIOS side never
reaches the anchor and the region reports MISALIGNED here (this gate is also that fix's
standing regression guard, alongside disk_probe_lstout_cbios.py).

HEAVY / oracle-dependent: boots openMSX twice per region (both hosts). Needs the installed
machines (`make machines-oracle` + the C-BIOS+disk machine from
tools/install-openmsx-machine.py) and a real MSX-DOS 1 disk (msxdos-oracle-disk). Not part
of the emulator-free `make unit-test`. Clean-room: our own ROM under two host BIOSes; no
reference code is decoded (DATA/register capture only, same class as the differential).

Usage:
  python3 probes/disk/disk_bdos_cbios_selfcheck.py [--dos-disk test.dsk]
        [--cbios-machine C-BIOS_MSX1_EU_BASIC_DISK] [--only BDOSX3] [--list]
Exit: 0 = every region byte-identical across hosts; 1 = a divergence / build/probe error.
"""
from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DEFAULT_DOS_DISK = os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")
DEFAULT_CBIOS = "C-BIOS_MSX1_EU_BASIC_DISK"

# Reuse the exerciser list + build->plan harvesting from the differential gate, so the
# two gates can never drift on which exercisers / anchors they cover.
sys.path.insert(0, HERE)
from disk_bdos_acceptance import EXERCISERS, build_and_plan, mode_of  # noqa: E402

# Documented BIOS-dependent bytes EXCUSED per exerciser (address -> provenance): a proven
# benign, BIOS-seeded value that is correct on both hosts. Empty for now -- the CF-3300
# gate proves these buffers are pure disk-ROM/BDOS evidence (we do not stamp dates, so even
# the date bytes are 0 on both hosts), so the expectation is a strict 0-diff. If a baseline
# surfaces a genuinely benign BIOS-seeded byte, allowlist it HERE with its cause; a diff at
# any non-listed byte is either KNOWN_OPEN (below) or a hard FAIL.
ALLOWLIST: dict[str, dict[int, str]] = {}

# KNOWN-OPEN divergences: a REAL BIOS-dependent BUG in our DOS layer, confirmed and tracked
# but not yet fixed (xfail). Unlike ALLOWLIST these are NOT excused as correct -- they are
# recorded so the gate stays committable/green-with-caveats while the fix is a separate
# milestone, WITHOUT hiding the finding. Semantics: a region whose diffs lie EXACTLY on its
# known-open set is reported XFAIL (loud, but doesn't red the build); a diff that spreads to
# ANY other byte still FAILS (the bug must not silently grow); and a known-open byte that
# STOPS diverging is reported XPASS (go fix the tracker -- the bug may be resolved).
KNOWN_OPEN: dict[str, dict[int, str]] = {
    "BDOSX2": {
        # BDOS $18 LOGIN (record 1) returns login vector 0x00FF on C-BIOS vs the
        # stock-correct 0x0003 (single-drive -> drives A+B) on CF-3300 -- 8 phantom
        # drives on the shipped target. Same class as $F340 (a value our DOS layer gets
        # right under the real BIOS, wrong under C-BIOS). Tracked:
        # disk/docs/tier2-cbios-bdos-selfcheck-spec.md §3. Fix = its own milestone.
        0x0349: "LOGIN $18 A (=login-vec lo) 03->FF on C-BIOS -- KNOWN-OPEN, see spec §3",
        0x034F: "LOGIN $18 L (=login-vec lo) 03->FF on C-BIOS -- KNOWN-OPEN, see spec §3",
    },
}

MEMLINE_RE = re.compile(r"memory\s+0x[0-9A-Fa-f]+\+\d+:\s+([0-9A-Fa-f ]+)")


def region_of(argv: list[str]) -> str | None:
    for i, a in enumerate(argv):
        if a == "--mem" and i + 1 < len(argv):
            return argv[i + 1]
    return None


def one_sided(argv: list[str]) -> list[str]:
    """Rewrite a harvested `capture ... --machine both ...` argv into a one-sided
    `--machine ours` run (so we capture a single host's buffer, no diff/alignment guard
    against stock). Drops any --expect (one-sided capture has nothing to expect)."""
    out, i = [], 0
    while i < len(argv):
        a = argv[i]
        if a == "--machine":
            out += ["--machine", "ours"]
            i += 2
            continue
        if a == "--expect":
            i += 2
            continue
        out.append(a)
        i += 1
    if "--machine" not in out:
        out += ["--machine", "ours"]
    return out


def capture_buffer(argv: list[str], host_env: dict | None) -> tuple[list[int] | None, str]:
    """Run one one-sided capture under the given host env; return (bytes, raw)."""
    env = dict(os.environ)
    if host_env:
        env.update(host_env)
    proc = subprocess.run(["python3"] + argv, cwd=ROOT, capture_output=True, text=True,
                          env=env)
    raw = proc.stdout + proc.stderr
    if "never reached occurrence" in raw or proc.returncode == 2:
        return None, raw
    m = MEMLINE_RE.search(raw)
    if not m:
        return None, raw
    return [int(x, 16) for x in m.group(1).split()], raw


def gate_region(name: str, region: str, cf: list[int] | None, cb: list[int] | None,
                cf_raw: str, cb_raw: str) -> tuple[str, str]:
    """Return (status, why) with status in {'pass','xfail','fail'}."""
    if cf is None:
        return "fail", "CF-3300 reference never reached anchor (harness/oracle issue)"
    if cb is None:
        return "fail", ("C-BIOS never reached anchor -- MSX-DOS boot / AUTOEXEC did not run "
                        "the exerciser on C-BIOS (regression of the $F340 cold-boot fix?)")
    if len(cf) != len(cb):
        return "fail", f"length mismatch CF={len(cf)} CB={len(cb)} (capture truncated)"
    base = int(region.split(":")[0], 0)
    diffs = [(base + i, cf[i], cb[i]) for i in range(len(cf)) if cf[i] != cb[i]]
    allow = ALLOWLIST.get(name, {})
    known = KNOWN_OPEN.get(name, {})
    # A hard failure is any diff that is neither a benign allowlisted byte nor a
    # tracked known-open byte -- i.e. a NEW divergence, incl. a known-open bug that spread.
    unexcused = [(a, s, o) for (a, s, o) in diffs if a not in allow and a not in known]
    if unexcused:
        shown = ", ".join(f"{a:04X}(cf={s:02X}/cb={o:02X})" for a, s, o in unexcused[:8])
        extra = f" +{len(unexcused)-8} more" if len(unexcused) > 8 else ""
        rest = len(diffs) - len(unexcused)
        return "fail", (f"{len(unexcused)} NEW byte(s) differ CF-3300 vs C-BIOS: {shown}{extra}"
                        + (f"; {rest} allowlisted/known-open" if rest else ""))
    hit_known = [a for (a, _, _) in diffs if a in known]
    # XPASS: a tracked known-open byte no longer diverges -> the bug may be fixed; nudge.
    xpassed = [a for a in known if a not in {d[0] for d in diffs}]
    if hit_known:
        reasons = "; ".join(sorted({known[a] for a in hit_known}))
        note = f" [XPASS {', '.join(f'{a:04X}' for a in xpassed)} — update tracker]" if xpassed else ""
        return "xfail", f"KNOWN-OPEN {len(hit_known)} byte(s) ({reasons}){note}"
    if diffs:                                    # only allowlisted (benign) diffs remain
        reasons = "; ".join(sorted({allow[a] for (a, _, _) in diffs}))
        return "pass", f"identical bar {len(diffs)} allowlisted BIOS-dependent byte(s) ({reasons})"
    if xpassed:                                  # known-open cleared AND no diffs at all
        return "pass", (f"byte-identical ({len(cf)} bytes) — known-open "
                        f"{', '.join(f'{a:04X}' for a in xpassed)} no longer diverges; update tracker")
    return "pass", f"byte-identical ({len(cf)} bytes)"


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", default=DEFAULT_DOS_DISK,
                    help="source MSX-DOS 1 disk the exercisers run from (default: test.dsk)")
    ap.add_argument("--cbios-machine", default=DEFAULT_CBIOS,
                    help=f"C-BIOS+disk target machine (default: {DEFAULT_CBIOS})")
    ap.add_argument("--only", action="append",
                    help="run only this exerciser (repeatable), e.g. --only BDOSX3")
    ap.add_argument("--list", action="store_true",
                    help="build + print the self-check plan without running any probe")
    args = ap.parse_args()

    if not os.path.isfile(args.dos_disk):
        print(f"DOS source disk not found: {args.dos_disk}", file=sys.stderr)
        return 1
    dos_copy = "/tmp/zerobas_sc_src.dsk"
    shutil.copyfile(args.dos_disk, dos_copy)
    cb_env = {"ZEROBAS_OURS_MACHINE": args.cbios_machine}

    wanted = {n.upper() for n in args.only} if args.only else None
    total = passed = failed = xfailed = 0
    failures = []
    xfails = []

    for name, script in EXERCISERS:
        if wanted and name not in wanted:
            continue
        print(f"\n===== {name} ({script}) =====")
        try:
            cmds, _ = build_and_plan(name, script, dos_copy)
        except RuntimeError as e:
            print(f"  BUILD-ERROR: {e}")
            failed += 1
            failures.append(f"{name}: build error")
            continue
        for argv in cmds:
            if mode_of(argv) != "capture":
                continue                      # only capture buffers are self-comparable
            region = region_of(argv)
            if not region:
                continue
            label = f"{name} {region}"
            argv1 = one_sided(argv)
            if args.list:
                print(f"  PLAN  {label}: CF-3300 vs {args.cbios_machine}")
                print(f"        {' '.join(argv1)}")
                continue
            total += 1
            cf, cf_raw = capture_buffer(argv1, None)
            cb, cb_raw = capture_buffer(argv1, cb_env)
            status, why = gate_region(name, region, cf, cb, cf_raw, cb_raw)
            tag = {"pass": "PASS", "xfail": "XFAIL", "fail": "FAIL"}[status]
            print(f"  {tag}  {label}: {why}")
            if status == "pass":
                passed += 1
            elif status == "xfail":
                xfailed += 1
                xfails.append(f"{label}: {why}")
            else:
                failed += 1
                failures.append(f"{label}: {why}")

    if args.list:
        print("\n(plan only — no probes run)")
        return 0

    print(f"\n===== C-BIOS self-consistency: {passed}/{total} regions byte-identical "
          f"CF-3300 vs {args.cbios_machine}"
          + (f", {xfailed} known-open (tracked)" if xfailed else "") + " =====")
    if xfails:
        print("KNOWN-OPEN (tracked BIOS-dependent bugs, not yet fixed — see "
              "disk/docs/tier2-cbios-bdos-selfcheck-spec.md):")
        for x in xfails:
            print(f"  ~ {x}")
    if failed:
        print("DIVERGENCE — a NEW difference on the C-BIOS target (not a tracked known-open):")
        for f in failures:
            print(f"  - {f}")
        return 1
    if xfailed:
        print("OK (with known-open) — no NEW divergence; the tracked known-open finding(s) "
              "are unchanged. Gate is green; the fix is a separate milestone.")
        return 0
    print("ALL IDENTICAL — the disk ROM's BDOS surface is BIOS-independent "
          "(C-BIOS matches the stock-validated CF-3300 byte-for-byte).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
