#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""BDOSX acceptance gate — the STANDING differential replay of the whole BDOS surface.

The BDOSX/BDOSX2/BDOSX3/BDOSX0 exercisers (disk/docs/tier2-bdos-coverage.md) each
drive a block of MSX-DOS-1 BDOS functions from a real `.COM` and were proven
0-byte-identical to stock ONCE, during the M19-M26 milestone chain. This turns
those one-shot proofs into a re-runnable gate: for every exerciser it (re)builds
the throwaway disk and replays the SAME differential the build script prints, then
asserts convergence — so "proven once" becomes "proven every release".

The build scripts are the single source of truth for the exact probe invocations
(the anchors/regions are computed from freshly-assembled symbol addresses), so this
runner does NOT duplicate them: it runs each `build_bdosx*_disk.py`, harvests the
`disk_probe_diff.py ...` command lines it emits, and executes them. Two assertion
styles, by probe mode:

  * `capture` — diffs a memory region on ours vs stock; the probe already exits 1
    on any byte-diff, so its exit code IS the gate.
  * `callseq` — compares the BDOS call sequence; the probe always exits 0, so we
    gate on its "ALIGNED, NO DIVERGENCE" verdict line.
  * `screen`  — prints both machines' screens for human comparison only (no machine
    verdict); run for the record but NOT gated (skipped unless --with-screen).

HEAVY / oracle-dependent: boots openMSX for BOTH machines per probe, so it needs
the installed oracle machines (`make machines-oracle`) and your own CF-3300
reference ROMs — exactly like the other probes under probes/README.md. Not part of
the fast emulator-free `make unit-test`. Clean-room: stock is a black box; the
exercisers + this runner are our own code, diffed against the stock oracle.

Usage:
  python3 probes/disk/disk_bdos_acceptance.py [--dos-disk test.dsk] [--only BDOSX3]
                                              [--with-screen] [--list]
Exit: 0 = every gated differential converged; 1 = a divergence / build/probe error.
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

# name -> build script; each emits the disk_probe_diff.py command(s) to replay.
EXERCISERS = [
    ("BDOSX",  "build_bdosx_disk.py"),
    ("BDOSX2", "build_bdosx2_disk.py"),
    ("BDOSX3", "build_bdosx3_disk.py"),
    ("BDOSX0", "build_bdosx0_disk.py"),
    # BDOSX4 (Tier-C case 2, disk-full onset). M34 (tier2-m34-wrseq-diskfull-spec.md)
    # made ours byte-identical to stock: disk-full at WRSEQ #1, all-01, FCLOSE 00.
    # Now a standing regression guard — no allowlist needed (0-byte-diff buffer).
    ("BDOSX4", "build_bdosx4_disk.py"),
    # BDOSX5 (Tier-C case 3, dir-full). FMAKE on a root-dir-full fixture returns
    # byte-identical to stock; standing guard (one allowlisted FOPEN-miss L byte).
    ("BDOSX5", "build_bdosx5_disk.py"),
    # BDOSX6 (Tier-C case 4, WRRND past-EOF, M36). Random write past EOF extends the
    # file size in the FCB AND the on-disk dirent (re-FOPEN confirms), byte-identical.
    ("BDOSX6", "build_bdosx6_disk.py"),
    # BDOSX7 (Tier-C case 5, FREN rename-collision, M35). Rename onto an existing name
    # is refused (A=FF), byte-identical to stock; source + dest left intact.
    ("BDOSX7", "build_bdosx7_disk.py"),
    # BDOSX8 (Item 5, spec-diskbasic-option-closure.md: WRSEQ $15 FCB position
    # write-back). FMAKE -> WRSEQ x12 (crosses a cluster boundary) -> FCLOSE; the
    # post-WRSEQ FCB position/size/first-cluster is now byte-identical to stock
    # (was stale -- the write branch had no advance, only the read branch did).
    ("BDOSX8", "build_bdosx8_disk.py"),
]

CMD_RE = re.compile(r"(python3\s+probes/disk/disk_probe_diff\.py\s+.*)$")


def build_and_plan(name: str, script: str, dos_disk: str) -> tuple[list[list[str]], str]:
    """Run the build script; return (list of probe arg-lists, its raw output)."""
    out_dsk = f"/tmp/zerobas_acc_{name.lower()}.dsk"
    proc = subprocess.run(
        ["python3", os.path.join(HERE, script), "--dos-disk", dos_disk, "--out", out_dsk],
        cwd=ROOT, capture_output=True, text=True)
    blob = proc.stdout + proc.stderr
    if proc.returncode != 0:
        raise RuntimeError(f"{script} failed (exit {proc.returncode}):\n{blob}")
    cmds = []
    for line in blob.splitlines():
        m = CMD_RE.search(line.strip())
        if m:
            cmds.append(shlex.split(m.group(1))[1:])   # drop the leading "python3"
    if not cmds:
        raise RuntimeError(f"{script} emitted no disk_probe_diff.py commands:\n{blob}")
    return cmds, blob


def mode_of(argv: list[str]) -> str:
    for a in argv[1:]:                 # argv[0] == "probes/disk/disk_probe_diff.py"
        if not a.startswith("-"):
            return a
    return "?"


def _flag_val(argv: list[str], flag: str, default, cast):
    for i, a in enumerate(argv):
        if a == flag and i + 1 < len(argv):
            try:
                return cast(argv[i + 1])
            except ValueError:
                return default
    return default


# Documented / contract-undefined divergences, excused by EXACT address per exerciser.
# A diff at an allowlisted byte is cited-and-excused; a diff at ANY other byte still
# FAILS, and a diff region too large to fully enumerate (probe caps the per-byte dump)
# also FAILS — so the allowlist can never hide an un-inspected byte. Each entry carries
# its provenance. Addresses are tied to the current bdosx*.asm buffer layout; if an
# exerciser is re-assembled to a different layout, the moved bytes show up as UNEXCUSED
# (the gate stays honest). Root-caused 2026-07-04 (Fable write-path investigation).
ALLOWLIST = {
    "BDOSX": {
        # Same documented classes BDOSX3 already excuses (FCB base $0300 here):
        0x0314: "FCB+20 date-lo — we intentionally do NOT stamp file dates (fat.asm; PROVENANCE date/time)",
        0x0315: "FCB+21 date-hi — ditto (no date stamp)",
        0x0318: "FCB+24 devid — accepted-cosmetic (M22a dirloc class)",
        0x0319: "FCB+25 dirloc — accepted-cosmetic (M22a dirloc class)",
    },
    "BDOSX3": {
        0x03C4: "FCB+20 date-lo — we intentionally do NOT stamp file dates (fat.asm; PROVENANCE date/time)",
        0x03C5: "FCB+21 date-hi — ditto (no date stamp)",
        0x03C8: "FCB+24 devid — accepted-cosmetic (M22a dirloc class)",
        0x03C9: "FCB+25 dirloc — accepted-cosmetic (M22a dirloc class)",
        0x044C: "regs rec14 FREN($17) L — register UNDEFINED on return (contract pins A only)",
        0x045B: "regs rec16 FOPEN-miss($0F) H — register UNDEFINED on the miss path (A=FF is pinned)",
        0x045C: "regs rec16 FOPEN-miss($0F) L — ditto (undefined on miss)",
    },
    "BDOSX5": {
        # Tier-C case 3 (dir-full). The dir-full FMAKE returns (records 0/1) are
        # byte-identical to stock; the only diff is record 2's FOPEN of the name the
        # failed FMAKE couldn't create — A=FF (not-found) is pinned on both, L is the
        # undefined ancillary register (same class as BDOSX3's FOPEN-miss L above).
        0x01D6: "regs rec2 FOPEN-miss($0F) L — register UNDEFINED on the miss path (A=FF is pinned)",
    },
    "BDOSX6": {
        # Tier-C case 4 (WRRND past-EOF, M36). The size extension (in-memory FCB AND
        # the on-disk dirent, proven by the re-FOPEN size) is byte-identical to stock;
        # residuals are all documented/ancillary classes:
        0x021B: "FCB+20 date-lo — we intentionally do NOT stamp file dates (fat.asm; PROVENANCE date/time)",
        0x021C: "FCB+21 date-hi — ditto (no date stamp)",
        0x0220: "FCB+25 dirloc — accepted-cosmetic (M22a dirloc class)",
        0x023B: "regs rec1 RDRND($21) L — ancillary register (stock mirrors L:=A on EOF; contract pins A=01)",
    },
    "BDOSX7": {
        # Tier-C case 5 (FREN rename-collision, M35). The collision is now refused
        # byte-identically (record 0 A=FF; source survives; dest intact); residuals:
        0x01D1: "FCB+25 dirloc — accepted-cosmetic (M22a dirloc class)",
        0x01E3: "regs rec0 FREN($17) H — register UNDEFINED on return (contract pins A only)",
        0x01E4: "regs rec0 FREN($17) L — ditto (undefined; A=FF is pinned)",
    },
    "BDOSX8": {
        # Item 5 (WRSEQ FCB position write-back). The post-WRSEQ FCB position (+12
        # EX / +32 CR), running size (+16..19), first cluster (+26/27), current
        # cluster (+28/29) and rec-in-cluster (+30) are now byte-identical to stock
        # in BOTH the live post-FCLOSE FCB (base $01AB) AND the frozen post-WRSEQ
        # snapshot (fcbsnap $0250). The only residuals are the same documented
        # date/dirloc classes every BDOSX exerciser carries:
        0x01BF: "FCB+20 date-lo — we intentionally do NOT stamp file dates (fat.asm; PROVENANCE date/time)",
        0x01C0: "FCB+21 date-hi — ditto (no date stamp)",
        0x01C4: "FCB+25 dirloc — accepted-cosmetic (M22a dirloc class)",
        0x0264: "fcbsnap+20 date-lo — ditto (frozen post-WRSEQ copy of the FCB)",
        0x0265: "fcbsnap+21 date-hi — ditto",
        0x0269: "fcbsnap+25 dirloc — ditto (frozen post-WRSEQ copy)",
    },
}


def gate(name: str, mode: str, rc: int, out: str, argv: list[str]) -> tuple[bool, str]:
    """Pass/fail verdict for one probe run, by mode.

    The capture gate is DEFENSIVE against two vacuity modes found 2026-07-04:
      1. a `done`-loop anchor colliding with a boot-time address before the program
         runs (the anchor fires at t≈0.3 s, comparing identical COMMAND.COM state);
      2. `mode_capture` returning rc=0 even WITH byte diffs (it only exits non-zero
         under --expect, which the builders don't pass), so rc alone never sees a diff.
    So we parse the probe's own report: reject misalignment, reject an anchor that
    fired before the program was launched (--keys-at), and fail on ANY byte/register
    diff — never trust the exit code alone."""
    if mode == "capture":
        # rc 2 = LOGICAL miss, rc 3 = APPARATUS miss (the emulator never finished) —
        # both are MISALIGNED and neither may be read as a result. Keyed on the codes
        # as well as the text so this does not rest on wording alone.
        if "MISALIGNED" in out or rc in (2, 3):
            klass = next((l.strip() for l in out.splitlines() if "miss class:" in l), "")
            return False, ("MISALIGNED — a side never reached the anchor "
                           "(fix --arm/--nth)" + (f"  [{klass}]" if klass else ""))
        keys_at = _flag_val(argv, "--keys-at", 0.0, float)
        m = re.search(r"ALIGNED:.*?stock t=([\d.]+), ours t=([\d.]+)", out)
        anchor_t = min(float(m.group(1)), float(m.group(2))) if m else None
        if anchor_t is not None and anchor_t < keys_at:
            return False, (f"VACUOUS anchor: fired at t={anchor_t:.2f} < keys-at={keys_at} "
                           f"(boot-time collision, not the program) — arm with --arm-check-val")
        mb = re.search(r"(\d+) of \d+ bytes differ", out)
        nbytes = int(mb.group(1)) if mb else 0
        mr = re.search(r"register diffs:\s*(.+)", out)
        regs = mr.group(1).strip() if mr else "NONE"
        # The EVIDENCE is the recorded regs-BUFFER in memory (this is exactly how the
        # M24-M26 differentials established "0-byte-diff"). The live CPU registers at the
        # `done` self-loop are incidental epilogue state — AF especially is volatile and
        # differs BENIGNLY on both convergent and divergent runs — so a register-only
        # delta is NOTED, never failed. Byte diffs in the buffer are the real verdict.
        if nbytes:
            # Enumerate the per-byte diffs the probe printed and excuse ONLY the
            # exact addresses on this exerciser's allowlist. Fail-safe on truncation:
            # if the probe capped its dump (printed < total), we cannot prove the
            # unseen bytes are excusable, so the diff stands.
            printed = [int(a, 16) for a in re.findall(r"^\s*([0-9A-Fa-f]{4}): stock=", out, re.M)]
            allow = ALLOWLIST.get(name, {})
            if len(printed) < nbytes:
                return False, (f"BYTE DIFF ({nbytes} byte(s); only {len(printed)} enumerated by the "
                               f"probe — too large to allowlist-verify, treated as real; regs: {regs})")
            unexcused = [a for a in printed if a not in allow]
            if unexcused:
                shown = ", ".join(f"{a:04X}" for a in unexcused[:8])
                extra = f" (+{len(unexcused)-8} more)" if len(unexcused) > 8 else ""
                excused = nbytes - len(unexcused)
                return False, (f"BYTE DIFF ({len(unexcused)} UNEXCUSED: {shown}{extra}"
                               + (f"; {excused} allowlisted" if excused else "") + f"; regs: {regs})")
            reasons = "; ".join(sorted({allow[a] for a in printed}))
            return True, f"0-byte-diff (all {nbytes} allowlisted — {reasons})"
        note = f"; live-reg delta [{regs}] (benign epilogue)" if regs != "NONE" else ""
        tstr = f" (anchor t={anchor_t:.1f} ≥ keys-at)" if anchor_t is not None else ""
        return True, f"0-byte-diff{tstr}{note}"
    if mode == "callseq":
        if "NO DIVERGENCE" in out:
            return True, "ALIGNED, no divergence"
        m = re.search(r"FIRST DIVERGENCE.*", out)
        return False, (m.group(0) if m else "no ALIGNED verdict emitted")
    return True, "screen (not gated)"


def run_probe(argv: list[str]) -> tuple[int, str]:
    proc = subprocess.run(["python3"] + argv, cwd=ROOT, capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dos-disk", default=DEFAULT_DOS_DISK,
                    help="source MSX-DOS 1 disk the exercisers run from (default: test.dsk)")
    ap.add_argument("--only", action="append",
                    help="run only this exerciser (repeatable), e.g. --only BDOSX3")
    ap.add_argument("--with-screen", action="store_true",
                    help="also run the (non-gated) screen probes")
    ap.add_argument("--list", action="store_true",
                    help="build + print the replay plan without running any probe")
    args = ap.parse_args()

    if not os.path.isfile(args.dos_disk):
        print(f"DOS source disk not found: {args.dos_disk}", file=sys.stderr)
        return 1
    # work off a /tmp copy of the DOS source so the committed oracle can't mutate.
    dos_copy = "/tmp/zerobas_acc_src.dsk"
    shutil.copyfile(args.dos_disk, dos_copy)

    wanted = {n.upper() for n in args.only} if args.only else None
    total = passed = failed = skipped = 0
    failures = []

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
            mode = mode_of(argv)
            region = next((argv[i + 1] for i, a in enumerate(argv) if a == "--mem"), "")
            label = f"{name} {mode}" + (f" {region}" if region else "")
            if mode == "screen" and not args.with_screen:
                print(f"  SKIP  {label} (screen; not gated — use --with-screen)")
                skipped += 1
                continue
            if args.list:
                print(f"  PLAN  {label}: {' '.join(argv)}")
                continue
            total += 1
            rc, out = run_probe(argv)
            ok, why = gate(name, mode, rc, out, argv)
            print(f"  {'PASS' if ok else 'FAIL'}  {label}: {why}")
            if ok:
                passed += 1
            else:
                failed += 1
                failures.append(f"{label}: {why}")
                tail = "\n".join(out.splitlines()[-12:])
                print(f"    --- probe tail ---\n{tail}")

    if args.list:
        print("\n(plan only — no probes run)")
        return 0

    print(f"\n===== BDOSX acceptance: {passed}/{total} gated differentials converged "
          f"({skipped} screen skipped) =====")
    if failed:
        print("DIVERGENCE — the BDOS surface no longer matches stock:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ALL CONVERGED — the BDOS surface still matches the stock oracle byte-for-byte.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
