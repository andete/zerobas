#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Build the repacked C-BIOS main ROM reproducibly (cbios-repack arc, WS-3 / S4).

Applies our tracked 0BSD patches (cbios-repack/*.patch, in PATCHES order) to a PINNED
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
# Applied IN ORDER; each is a tracked 0BSD description of edits to BSD C-BIOS
# source, never a copy of its bytes (decision D1). See cbios-repack/README.md.
PATCHES = [
    os.path.join(REPO, "cbios-repack", "eu-drop-statements.patch"),
    # interrupt-traps T3: the function-key DELIVERY hook (H_ZKEY $FFCF + a
    # 5-byte call at put_key_fnk). No published MSX hook can see -- let alone
    # divert -- the current frame's KEYBUF insertion, so BASIC's KEY trap needs
    # a seam that stock C-BIOS does not have. docs/spec-traps-t3-key.md SS4.
    os.path.join(REPO, "cbios-repack", "key-trap-hook.patch"),
]

PINNED_TAG = "v0.29-3-gb5ad9cb"
PRISTINE_SHA1 = "baf2e9c69252fd9b350b488d89c71887b9d05eec"
REPACKED_SHA1 = "557aed9352cf8367eabb9a3cc081c83252579ab9"
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
