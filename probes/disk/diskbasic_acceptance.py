#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Disk-BASIC acceptance gate — the STANDING differential replay of the Disk-BASIC
verb surface. The BASIC-side counterpart of disk_bdos_acceptance.py.

Spec: disk/docs/diskbasic-acceptance-spec.md · scoreboard: disk/docs/diskbasic-verb-coverage.md

Unlike the BDOS gate (whose .COM exercisers need build-script command harvesting +
an address allowlist), every Disk-BASIC differential probe is a STANDALONE script
whose process exit code IS its verdict: each `disk_probe_*.py` does
`raise SystemExit(main())`, and `main()` boots the zerobas machine AND the CF-3300
reference (or, for the program loaders, compares against a real FAT12 artifact),
returning 0 on convergence / non-zero on divergence. So this runner is a thin
registry-driven subprocess dispatcher — no harvesting, no allowlist, no verdict
parsing. It runs each probe, gates on exit code, and prints an N/N scoreboard.

Two oracle styles, both dispatched identically (they differ only in what they compare
the zerobas side AGAINST; the zerobas machine itself is one --machine for the whole run):
  * live     — differential vs a running National_CF-3300 black box.
  * artifact — round-tripped against a real stock FAT12 image, read per public spec.

VACUITY GUARDS (the BDOS-gate lesson — a gate that can't go red is not a gate):
  1. The runner NEVER passes --no-ref; a probe with no oracle can't diverge. Any
     registry entry carrying --no-ref is rejected at startup.
  2. For a `live` probe, the run output MUST show the CF-3300 differential actually
     ran (the reference machine name appears in the probe's report); if it doesn't,
     the cell FAILS as VACUOUS even on exit 0.
  Guards 1+2 protect the ORACLE side. Guards 3-5 are the ZEROBAS-side analogue
  (docs/spec-lean-retire-s1-explicit-machine.md): the machine must RESOLVE, must be
  a zerobas machine at all, and must be the BUILD THE CALLER INTENDED (--expect-build).
  Guard 5 is what keeps `diskbasic-acceptance` and `-repack` from silently becoming
  the same test: point both at one machine and one of them dies instead of both
  printing 34/34.

HEAVY / oracle-dependent: boots openMSX (one or both machines) per probe, so it
needs the installed oracle machines (`make machines-oracle`), the seed FAT12 image
(`make test-dsk`), and your own CF-3300 reference ROMs — exactly like the other
probes under probes/README.md. NOT part of the emulator-free `make unit-test`.
Clean-room: stock is a black box; the probes + this runner are our own code.

Usage:
  python3 probes/disk/diskbasic_acceptance.py --machine M --expect-build lean|repack
                                              [--only FIELD] [--list] [--timeout S]
Exit: 0 = every gated probe converged; 1 = a divergence / probe error / vacuity.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import openmsx_paths  # noqa: E402  (shared share/user dir discovery)

TEST_DSK = os.path.join(ROOT, "disk", "test720.dsk")
DSK_COPY = "/tmp/zerobas_dbacc.dsk"          # /tmp copy so the committed image can't mutate
# live-oracle vacuity markers: a `live` probe MUST print evidence its CF-3300
# reference actually ran. Probes name it differently ("CF-3300 differential" vs
# "STOCK ran"), so accept any; matched case-insensitively.
REF_MARKERS = ("cf-3300", "stock")

# label -> (probe script, extra args, style). Extra args are almost always empty;
# the zerobas machine comes from --machine via the child env, never from a probe
# default (no probe has one any more). The set is the ✅ rows of
# disk/docs/diskbasic-verb-coverage.md §2 (kept in sync with that scoreboard).
REGISTRY = [
    # --- live CF-3300 differentials ---------------------------------------------
    ("FILES",          "disk_probe_files.py",           [], "live"),
    ("KILL",           "disk_probe_kill.py",            [], "live"),
    ("NAME",           "disk_probe_name.py",            [], "live"),
    ("MAXFILES",       "disk_probe_maxfiles.py",        [], "live"),
    ("MERGE",          "disk_probe_merge.py",           [], "live"),
    ("FIELD/LSET/RSET","disk_probe_field.py",           [], "live"),
    ("GET/PUT",        "disk_probe_getput.py",          [], "live"),
    ("GET(RDBLK)",     "disk_probe_rdblk_roundtrip.py", [], "live"),
    ("PUT(WRBLK)",     "disk_probe_wrblk_roundtrip.py", [], "live"),
    ("MKI$/CVI",       "disk_probe_mkicvi.py",          [], "live"),
    ("EOF/LOF",        "disk_probe_eof.py",             [], "live"),
    ("DSKF",           "disk_probe_dskf.py",            [], "live"),
    ("PRINT#",         "disk_probe_filewrite.py",       [], "live"),
    ("PRINT#-append",  "disk_probe_append.py",          [], "live"),
    ("INPUT#",         "disk_probe_fileread.py",        [], "live"),
    ("PRINT#-USING",   "disk_probe_printusing_file.py", [], "live"),
    ("INPUT$",         "disk_probe_inputdollar.py",     [], "live"),
    # CALL FORMAT is a STRUCTURAL self-check (asserts the formatted BPB/FAT bytes vs
    # the FAT12 spec), not a live CF-3300 differential — hence "artifact", no ref marker.
    ("CALL FORMAT",    "disk_probe_format.py",          [], "artifact"),
    # --- read-only FAT12-artifact oracle ----------------------------------------
    ("SAVE/BSAVE",     "disk_probe_save.py",            [], "artifact"),
    ("SAVE(ASCII)",    "disk_probe_save_ascii.py",      [], "live"),
    ("BSAVE(.bas)",    "disk_probe_save_bas.py",        [], "live"),
    ("LOAD",           "disk_probe_load_disk.py",       [], "artifact"),
    ("LOAD(NUL)",      "disk_probe_load_embedded_nul.py",[], "artifact"),
    ("LOAD(ASCII)",    "disk_probe_load_ascii.py",      [], "live"),
    ("RUN\"file\"",    "disk_probe_run_disk.py",        [], "artifact"),
    ("BLOAD",          "disk_probe_bload_disk.py",      [], "artifact"),
    ("AUTOEXEC",       "disk_probe_autoexec.py",        [], "live"),
    # --- option-surface closure (spec-diskbasic-option-closure.md items 1+2) ------
    # BSAVE",S"/BLOAD",S" VRAM round-trip is a CF-3300 differential (live). The
    # option-parse hygiene cell is an OURS-ONLY behavioural assert (our load_error
    # model diverges from stock's Syntax-error halt), judged by exit code (artifact).
    ("BSAVE/BLOAD(VRAM)","disk_probe_vram_saveload.py",  [], "live"),
    ("OPTION(hygiene)", "disk_probe_option_hygiene.py",  [], "artifact"),
    # OPEN..AS #n LEN=r random record size (item 3). LEN=128 -> 4 records per
    # 512-byte sector; a 4-record round-trip is byte-identical to CF-3300 (live).
    ("OPEN(LEN=)",     "disk_probe_openlen.py",         [], "live"),
    # Item 4: FILES/KILL 8.3 '*'/'?' wildcards + CLOSE channel list. FILES/KILL
    # wildcards are CF-3300 differentials (live); CLOSE-list is a keyboard-free
    # functional self-check (AUTOEXEC .bas + offline FAT12 + done witness).
    ("FILES(wild)",    "disk_probe_files_wildcard.py",  [], "live"),
    ("KILL(wild)",     "disk_probe_kill_wildcard.py",   [], "live"),
    ("CLOSE(list)",    "disk_probe_closelist.py",       [], "artifact"),
    # CAS:/device option-closure Tier 1, Item 3: OPEN"LPT:"/"CRT:" device channels
    # route PRINT# to the printer (LPTOUT)/screen (CHPUT). Keyboard-free AUTOEXEC.BAS
    # + printer logger; asserts the LP! line physically reaches the printer log.
    ("OPEN(LPT/CRT)",  "disk_probe_open_device.py",     [], "artifact"),
]


def _check_registry() -> None:
    """Vacuity guard 1: reject any entry that would skip the oracle."""
    for label, script, extra, _style in REGISTRY:
        if "--no-ref" in extra:
            sys.exit(f"registry error: {label} ({script}) carries --no-ref — a probe "
                     f"with no oracle cannot diverge (vacuity guard §3.1.1)")
        if not os.path.isfile(os.path.join(HERE, script)):
            sys.exit(f"registry error: {label}: missing probe {script}")


def _check_machine_wiring() -> None:
    """Vacuity guard §3.1.6: every probe that boots a zerobas-BASIC machine must honour
    ZEROBAS_BASIC_MACHINE (its --machine/OURS_MACHINE default reads it), or it would pick
    its OWN build regardless of what this run was told to test — false coverage for
    whichever gate it lands in. So refuse to run unless each registry probe either
    references ZEROBAS_BASIC_MACHINE, or delegates to disk_probe_diff / omsx_session (those
    boot the National_CF-3300 disk-ROM machine — build-invariant w.r.t. the BASIC build,
    correctly NOT overridden). A newly-added probe that forgets the env wrap fails here.

    Used to run only when the env var was set, i.e. only on the repack gate; both gates
    now name their machine, so it runs on BOTH."""
    ENV = "ZEROBAS_BASIC_MACHINE"
    DISK_ROM_DELEGATORS = ("disk_probe_diff", "omsx_session")
    offenders = []
    for label, script, _extra, _style in REGISTRY:
        src = open(os.path.join(HERE, script), encoding="utf-8", errors="replace").read()
        if ENV in src or any(d in src for d in DISK_ROM_DELEGATORS):
            continue
        offenders.append(f"{label} ({script})")
    if offenders:
        sys.exit("machine wiring error: these probes do not read ZEROBAS_BASIC_MACHINE, "
                 "so they would pick their own build instead of the one under test "
                 "(false coverage):\n  - "
                 + "\n  - ".join(offenders)
                 + f"\nRead their zerobas machine from os.environ.get('{ENV}') "
                   f"(vacuity guard §3.1.6).")


# --- zerobas-side machine provenance (vacuity guards 3-5) ---------------------
# The artifacts that IDENTIFY a zerobas machine config. A lean machine boots stock
# C-BIOS with build/basic.rom spliced in as a page-1 IPS patch; a repack machine either
# points slot 0 straight at the merged main ROM (the dev machine that
# tools/install-repack-machine.py writes) or applies the merged ROM as an IPS to
# openMSX's own stock C-BIOS EU (the RELEASE machine that
# tools/install-openmsx-machine.py writes). Nothing else in the tree writes any of these
# references, so the config alone says which BUILD the machine runs.
#
# ⚠️ LEAN_MARK IS DELIBERATELY KEPT after the lean build's retirement (S2,
# docs/spec-lean-retire-s2-switch.md). Nothing passes --expect-build lean any more, and
# zerobas-msx1.ips is deleted from the tree -- but any dev box that ran `make machines`
# before 2026-07-29 still has *_BASIC_DISK configs naming it. Dropping the lean branch
# would reclassify those as "unknown" and lose the one thing worth saying about them:
# that they are the RETIRED build. This is the guard that PROVES lean retired; deleting
# it because lean retired is the mistake.
LEAN_MARK    = os.path.join(ROOT, "zerobas-msx1.ips")              # <ips> patch entry
REPACK_MARKS = (os.path.join(ROOT, "build", "zerobas-main-eu.rom"),  # slot-0 <filename>
                os.path.join(ROOT, "zerobas-main-eu.ips"))          # <ips> patch entry


def _machine_xml(machine: str) -> str:
    """Resolve <machine>.xml the way openMSX itself does: user dir first, then share.
    Guard §3.1.3 — a machine that does not resolve is a ~2h TIMEOUT cascade otherwise
    (openMSX dies instantly, but each probe only learns via its own --timeout)."""
    searched = []
    for base in (os.path.join(openmsx_paths.find_user(), "share"),
                 openmsx_paths.find_share()):
        d = os.path.join(base, "machines")
        searched.append(d)
        cand = os.path.join(d, f"{machine}.xml")
        if os.path.isfile(cand):
            return cand
    sys.exit(f"machine error: openMSX machine {machine!r} does not resolve — no "
             f"{machine}.xml in any of:\n  - " + "\n  - ".join(searched)
             + "\nInstall it (`make machines` / `make repack-machine`) or fix "
               "$ZEROBAS_BASIC_MACHINE (vacuity guard §3.1.3).")


def _check_machine_provenance(machine: str, expect: str) -> None:
    """Guards §3.1.4 + §3.1.5: the machine must BE a zerobas machine, and must be the
    BUILD the caller asked for.

    §3.1.4 catches "pointed at stock C-BIOS": every probe then reports nothing and the
    run reads as a mass functional failure rather than as a wiring error.
    §3.1.5 catches a gate measuring a build its caller did not name. It was written for
    the lean/repack pair, where repointing one gate would have made both the SAME test,
    both still printing 34/34 with the lean column silently gone. Lean is now retired and
    only the repack gate remains — so what §3.1.5 catches today is a STALE lean machine
    left on a dev box by a pre-2026-07-29 `make machines`, which would otherwise boot a
    build the project no longer ships.

    Deliberately NOT a timestamp check: an mtime guard would fire on byte-correct
    machines (measured for the lean pair in S1 §1.3(b)). Freshness is Make's job — the
    gate depends on `repack-machine`, which rebuilds the merged ROM from source."""
    xml = _machine_xml(machine)
    text = open(xml, encoding="utf-8", errors="replace").read()

    refs = re.findall(r"<(?:filename|ips|bps)>([^<]+)</(?:filename|ips|bps)>", text)
    abs_refs = {os.path.abspath(r) for r in refs}
    kind = ("lean"   if LEAN_MARK in abs_refs else
            "repack" if abs_refs & set(REPACK_MARKS) else
            "unknown")

    if kind == "unknown":
        sys.exit(f"machine error: {machine!r} ({xml}) references NO zerobas artifact "
                 f"— it is not a zerobas machine, so every probe would boot a BASIC "
                 f"we did not build.\nExpected one of:\n  - "
                 + "\n  - ".join([f"{LEAN_MARK} (lean, RETIRED)"]
                                 + [f"{m} (repack)" for m in REPACK_MARKS])
                 + "\n(vacuity guard §3.1.4).")

    # A config naming a deleted build/ artifact boots into an unrelated-looking failure.
    missing = [r for r in refs
               if os.path.abspath(r).startswith(ROOT + os.sep) and not os.path.isfile(r)]
    if missing:
        sys.exit(f"machine error: {machine!r} ({xml}) references repo artifacts that do "
                 f"not exist:\n  - " + "\n  - ".join(missing)
                 + "\nRebuild them (`make all` / `make repack-machine`) (guard §3.1.4).")

    if kind != expect:
        extra = ("\nThe LEAN build is RETIRED (docs/spec-lean-retire-s2-switch.md) — this "
                 "is a stale machine from a `make machines` run before 2026-07-29. "
                 "Re-run `make machines`." if kind == "lean" else
                 "\nThe lean and repack gates must not collapse into the same test — one "
                 "of them would vanish while both still printed N/N.")
        sys.exit(f"machine error: --expect-build {expect}, but {machine!r} ({xml}) is a "
                 f"{kind.upper()} machine." + extra + " (vacuity guard §3.1.5).")

    print(f"[runner] zerobas machine: {machine}  build={kind}  ({xml})")


def run_probe(script: str, extra: list[str], env: dict, timeout: float) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            ["python3", os.path.join(HERE, script), *extra],
            cwd=ROOT, capture_output=True, text=True, env=env, timeout=timeout)
        return proc.returncode, proc.stdout + proc.stderr
    except subprocess.TimeoutExpired as e:
        return 124, (e.output or "") + f"\n[runner] TIMEOUT after {timeout:.0f}s"


def gate(style: str, rc: int, out: str) -> tuple[bool, str]:
    """Pass/fail for one probe. Exit code is the verdict; live probes also get the
    oracle-ran vacuity check (guard §3.1.2)."""
    if rc != 0:
        # surface the probe's own last verdict line if present
        fail = next((l for l in reversed(out.splitlines())
                     if "FAIL" in l or "DIVERG" in l or "TIMEOUT" in l), None)
        return False, (fail.strip() if fail else f"exit {rc}")
    if style == "live" and not any(mk in out.lower() for mk in REF_MARKERS):
        return False, ("VACUOUS — exit 0 but no oracle evidence in output "
                       "(reference/stock differential never ran)")
    return True, "converged"


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", action="append",
                    help="run only this verb label or probe stem (repeatable)")
    ap.add_argument("--list", action="store_true",
                    help="print the registry/plan without running any probe")
    ap.add_argument("--timeout", type=float, default=240.0,
                    help="per-probe timeout in seconds (default 240)")
    ap.add_argument("--machine", default=os.environ.get("ZEROBAS_BASIC_MACHINE"),
                    help="zerobas machine the whole corpus boots (default "
                         "$ZEROBAS_BASIC_MACHINE). There is NO built-in default: the "
                         "caller states which build is under test.")
    ap.add_argument("--expect-build", choices=("lean", "repack"),
                    help="assert --machine really IS this build (vacuity guard §3.1.5)")
    args = ap.parse_args()

    _check_registry()
    _check_machine_wiring()

    if args.list:
        print("Disk-BASIC acceptance registry:")
        for label, script, extra, style in REGISTRY:
            print(f"  [{style:8}] {label:16} -> {script} {' '.join(extra)}".rstrip())
        print(f"\n{len(REGISTRY)} probes (plan only — nothing run)")
        return 0

    if not args.machine:
        sys.exit("no zerobas machine selected: pass --machine or set "
                 "$ZEROBAS_BASIC_MACHINE. There is deliberately no default — a "
                 "hardcoded one silently decides which BUILD this gate measures "
                 "(docs/spec-lean-retire-s1-explicit-machine.md).")
    if not args.expect_build:
        sys.exit(f"--expect-build is required: state whether {args.machine!r} is the "
                 f"'lean' or the 'repack' build, so the two gates cannot silently "
                 f"collapse into the same test (vacuity guard §3.1.5).")
    _check_machine_provenance(args.machine, args.expect_build)

    # /tmp copy so the artifact probes can't mutate the committed seed image.
    # The machine goes into the CHILD env: every probe reads it, none defaults.
    env = dict(os.environ)
    env["ZEROBAS_BASIC_MACHINE"] = args.machine
    if os.path.isfile(TEST_DSK):
        shutil.copyfile(TEST_DSK, DSK_COPY)
        env["DISK_DSK"] = DSK_COPY
    else:
        print(f"WARNING: seed image {TEST_DSK} missing (run `make test-dsk`) — "
              f"artifact probes may fail", file=sys.stderr)

    # --only is repeatable AND comma-splittable. It used to be append-only, so
    # `--only 'GET(RDBLK),PUT(WRBLK)'` matched no label at all and the run went
    # green on an EMPTY selection (see the vacuity guard below, which is what
    # caught it). Splitting here also lets the Makefile's ONLY= pass a list.
    wanted = ({w.strip().upper() for spec in args.only for w in spec.split(",")
               if w.strip()} if args.only else None)
    passed = failed = 0
    failures = []
    selected = []

    for label, script, extra, style in REGISTRY:
        stem = script[:-3]
        if wanted and label.upper() not in wanted and stem.upper() not in wanted:
            continue
        selected.append(label.upper())
        selected.append(stem.upper())
        rc, out = run_probe(script, extra, env, args.timeout)
        ok, why = gate(style, rc, out)
        print(f"  {'PASS' if ok else 'FAIL'}  [{style:8}] {label:16} {why}")
        if ok:
            passed += 1
        else:
            failed += 1
            failures.append(f"{label} ({script}): {why}")
            print("    --- probe tail ---\n" +
                  "\n".join("    " + l for l in out.splitlines()[-12:]))

    total = passed + failed

    # --- VACUITY GUARD: a gate's DENOMINATOR must be measured, never assumed ---
    # This runner used to print "ALL CONVERGED" on a 0/0 tally, so a mistyped or
    # comma-joined --only produced a GREEN gate that ran nothing. That is the
    # zero-denominator trap the trap-arc slices kept hitting; found for real on
    # 2026-07-28 while regression-testing the fat_rand_* carve.
    if total == 0:
        print("\nVACUOUS RUN — no probe was selected, so this run proves NOTHING.")
        if wanted:
            unmatched = sorted(w for w in wanted if w not in set(selected))
            print(f"  --only matched no registry entry: {', '.join(unmatched)}")
            print("  run with --list to see the valid labels and probe stems.")
        return 2
    if wanted:
        unmatched = sorted(w for w in wanted if w not in set(selected))
        if unmatched:
            print(f"\nUNMATCHED --only selector(s): {', '.join(unmatched)} — "
                  f"refusing to report a partial selection as a result.")
            return 2

    # disk-mutation guard: the committed seed must be untouched (test-disk-mutation-gotcha).
    dirty = subprocess.run(["git", "status", "--porcelain", "disk/test720.dsk"],
                           cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if dirty:
        print(f"\nWARNING: {TEST_DSK} was modified by the run — restore with "
              f"`git checkout -- disk/test720.dsk`")

    print(f"\n===== Disk-BASIC acceptance: {passed}/{total} verbs converged =====")
    if failed:
        print("DIVERGENCE — the Disk-BASIC verb surface no longer matches the oracle:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ALL CONVERGED — the Disk-BASIC verb surface still matches the oracle.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
