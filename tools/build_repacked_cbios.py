#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause

"""Build the repacked C-BIOS main ROM reproducibly (cbios-repack arc, WS-3 / S4).

Applies our tracked BSD-2-Clause patches (cbios-repack/*.patch, in PATCHES order) to a PINNED
C-BIOS source tag in a throwaway git worktree, rebuilds, and verifies the result's
sha1. No C-BIOS bytes live in the zerobas repo (decision D1) -- the patch is a
description of edits to BSD source, applied to the user's own checkout at build time.

Using a worktree at the pinned tag (not whatever the checkout currently has checked
out) makes the output deterministic regardless of the checkout's branch state.

    python3 tools/build_repacked_cbios.py [--cbios ~/projects/cbios] [-o OUT.rom]
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

# --- zerobas: the openMSX preflight guard (probes/lib) ---
import os as _zbo, sys as _zbs  # noqa: E402
_zbs.path.insert(0, _zbo.path.join(_zbo.path.dirname(
    _zbo.path.dirname(_zbo.path.abspath(__file__))), "probes", "lib"))
import omsx_preflight  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Applied IN ORDER; each is a tracked BSD-2-Clause description of edits to BSD C-BIOS
# source, never a copy of its bytes (decision D1). See cbios-repack/README.md.
PATCHES = [
    # D-CBIOS032 (2026-11-22): the repack is REBASED on C-BIOS fff98e8 (d23d87b + C-BIOS's own KEY(n) ON trap) (prepare-0.33, "Boot: drop the keys typed
    # during the logo"): 0.32's tape, function-key line, INLIN editor, music player, CHRGTR ... plus the fixes
    # zerobas proved (CLRSPR, PUTQ, TUPC / TDOWNC, the boot KILBUF). Of the 39 v0.31 patches only the LAYOUT ones
    # are carried, re-ported; every behaviour patch is retired because d23d87b passes the spec pages
    # (scratchpad/AE_cbiosd23_vs_zerobas.out). The tape overlay (tape/tape.asm) is gone with them.
    #
    # The cartridge statements (CALL ...) go: zerobas's BASIC is the only BASIC.
    os.path.join(REPO, "cbios-repack", "eu-drop-statements.patch"),
    # str_basic / str_nocart never print on the merged machine (the boot scan reaches zerobas's BASIC first):
    # 173 B after the font, so BASIC starts that much lower.
    os.path.join(REPO, "cbios-repack", "eu-drop-dead-strings.patch"),
    # (D-KEYTRAPREF's key-trap-bios.patch is RETIRED: C-BIOS took the function-key trap as fff98e8, the base.)
    # D-CBIOSDEAD on d23d87b: the bodies zerobas overlays (SYNCHR / CHRGTR / GETYPR / OUTDO, ISCNTC / CKCNTC,
    # ISFLIO, CALBAS) and dead data (the US GRAPH / CODE scan tables nothing reads, the debug hex printers):
    # 200 B after the font, ~130 B more in the pads the islands use (scratchpad/cbios_reach.py).
    os.path.join(REPO, "cbios-repack", "dead-bodies-main.patch"),
    # D-GRPHEDCLS2: drawing the function-key line ends a pending graphic header (GRPHED := 0), as the VG-8020:
    # 4 B at DSPFNK's entry, which the text-mode calls reach when they redraw the line.
    os.path.join(REPO, "cbios-repack", "grphed-keyline.patch"),
    # Register leftovers the VG-8020 keeps (biosregs-acceptance): INLIN / PINLIN / QINLIN return A = $0D after
    # Enter (+2 B), and DSPFNK / ERAFNK in SCREEN 2 and up keep HL (fnk_span drops its return with `inc sp` x2, +1 B).
    os.path.join(REPO, "cbios-repack", "regs-leftovers.patch"),
]

PINNED_TAG = "fff98e8"   # C-BIOS prepare-0.33 (not master; kept fast-forward only): d23d87b + the KEY(n) ON trap
PRISTINE_SHA1 = "3fc2c7ec71648cba490f7bd7d01a795c6890f270"
REPACKED_SHA1 = "32d04b86e2244c247a7ebae9c187f00be71bf7e0"   # fff98e8 + 5 layout / leftover patches (D-CBIOS032), 2026-11-22
ROM_REL = os.path.join("derived", "bin", "cbios_main_msx1_eu.rom")


def run(cmd, **kw):
    print("  " + " ".join(str(c) for c in cmd))
    subprocess.run(omsx_preflight.guarded(cmd), check=True, **kw)


def sha1(path: str) -> str:
    return hashlib.sha1(open(path, "rb").read()).hexdigest()


def build(cbios: str, out: str, pristine: str | None = None) -> None:
    cbios = os.path.abspath(os.path.expanduser(cbios))
    if not os.path.isdir(os.path.join(cbios, ".git")):
        sys.exit(f"error: {cbios} is not a git checkout of C-BIOS "
                 f"(pass --cbios <path>).")
    work = tempfile.mkdtemp(prefix="cbios-repack-")
    try:
        run(["git", "-C", cbios, "worktree", "add", "-q", "--detach", work, PINNED_TAG])
        try:
            for patch in PATCHES:
                run(["git", "-C", work, "apply", patch])
            run(["make", "-s", "-C", work, ROM_REL])
            built = os.path.join(work, ROM_REL)
            got = sha1(built)
            if got != REPACKED_SHA1:
                sys.exit(f"error: repacked ROM sha1 {got}\n"
                         f"       expected      {REPACKED_SHA1}\n"
                         f"       (is the checkout on the pinned tag {PINNED_TAG}?)")
            os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
            shutil.copyfile(built, out)
            # D-CBIOSSYM (2026-11-22): the repacked build's symbol table (pasmo writes it as derived/lst/*.lst) goes
            # next to the ROM, so the merge (tools/build_mainrom.py) and BASIC's C-BIOS addresses read the labels
            # instead of pinning bytes -- what makes tracking C-BIOS's latest commits cheap (D-CBIOS032).
            sym_src = os.path.join(work, "derived", "lst", os.path.basename(ROM_REL)[:-4] + ".lst")
            shutil.copyfile(sym_src, os.path.splitext(out)[0] + ".sym")
            print(f"OK: repacked C-BIOS -> {out}  (sha1 {got})")
            if pristine is not None:
                # Also emit the pristine stock from the same tag (the diff target /
                # BPS CRC source), so the whole main-ROM build is source-reproducible.
                run(["git", "-C", work, "checkout", "-q", "--", "."])
                run(["make", "-s", "-C", work, "clean"])
                run(["make", "-s", "-C", work, ROM_REL])
                pgot = sha1(os.path.join(work, ROM_REL))
                if pgot != PRISTINE_SHA1:
                    sys.exit(f"error: pristine ROM sha1 {pgot} != {PRISTINE_SHA1}")
                shutil.copyfile(os.path.join(work, ROM_REL), pristine)
                print(f"OK: pristine C-BIOS -> {pristine}  (sha1 {pgot})")
        finally:
            run(["git", "-C", cbios, "worktree", "remove", "--force", work])
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cbios", default="~/projects/cbios",
                    help="path to the C-BIOS git checkout (default ~/projects/cbios)")
    ap.add_argument("-o", "--out",
                    default=os.path.join(REPO, "build", "cbios_main_msx1_eu-repacked.rom"),
                    help="output path for the repacked ROM")
    ap.add_argument("--pristine",
                    help="also emit the pristine stock ROM from the same tag to this path")
    args = ap.parse_args()
    build(args.cbios, args.out, args.pristine)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
