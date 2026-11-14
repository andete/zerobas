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
    # 🔁 D-CBIOS030 (2026-11-11): REBASED ON v0.30. Nine patches retired -- 0.30 has
    # them upstream (CHANGELOG #7-#21): ins-del-keys, home-key, ctrl-keys, linttb-scroll,
    # vdp-reg7, calpat-de, bios-regs, bios-keyscan, key-repeat. ctrlstop-key and
    # crtcnt-bound were re-made against 0.30's rewritten key_ascii / ESC L / ESC M.
    os.path.join(REPO, "cbios-repack", "eu-drop-statements.patch"),
    # interrupt-traps T3: the function-key DELIVERY hook (H_ZKEY $FFCF + a
    # 5-byte call at put_key_fnk). No published MSX hook can see -- let alone
    # divert -- the current frame's KEYBUF insertion, so BASIC's KEY trap needs
    # a seam that stock C-BIOS does not have. docs/spec-traps-t3-key.md SS4.
    os.path.join(REPO, "cbios-repack", "key-trap-hook.patch"),
    # C3-CBIOS-TAIL-STRINGS: drop the two boot strings the merged machine can
    # never print (str_nocart 143 B + str_basic 30 B, both AFTER the font pin
    # and before the scan-code tables); vdp_bios ends at $2765, not $2812, and
    # BASIC_ORG (basic/main.asm) / BASIC_BASE (build_mainrom.py) follow it.
    os.path.join(REPO, "cbios-repack", "eu-drop-dead-strings.patch"),
    # D-BIOSCONTRACT (2026-11-08): the graphics-cursor span RIGHTC .. SCANL rewritten
    # as one block of the SAME length (padded to print_debug): SCALXY, GTASPC, MAPXYC,
    # SETC, STOREC, SETATR, READC and the four moves as the VG-8020; GRPPRT follows
    # MAPXYC's CLOC; the other stubs a bare `ret`. SCREEN 3 arms (D-BIOSRUNG, 2026-11-12)
    # grew it 95 B into gap 1: the C-BIOS code now ends at $09E0, where island 3 starts.
    os.path.join(REPO, "cbios-repack", "graphics-cursor.patch"),
    # CRTCNT UNDER KEY ON (2026-11-10): CHPUT's 8 reads of CRTCNT call zerobas's page-0
    # helpers at $3283 / $328D (CRTCNT + CNSDFG, the VG-8020's bound); byte-neutral.
    os.path.join(REPO, "cbios-repack", "crtcnt-bound.patch"),
    # D-CBIOS030 (2026-11-11): 0.30 moved CHKRAM into the $09D4 gap (its $0D12 keyscan
    # entry took CHKRAM's old place); this moves it in front of the font, where MSX1 has
    # room, so zerobas's cassette body has $09D4-$0D00 in one piece again.
    os.path.join(REPO, "cbios-repack", "chkram-move.patch"),
    # D-SCANBOOT (2026-11-11): 0.30 scans the keyboard from the first interrupt
    # (commit 4aa7859), so a key down during the boot logo reached the first prompt --
    # openMSX's tape autorun presses one at insertion and CLOAD's RUN was lost
    # (autorun-acceptance). Back to 0.29's start: zerobas's cold start sets SCNCNT.
    # `inc (hl)` -> `nop`, nothing moves.
    os.path.join(REPO, "cbios-repack", "scan-from-basic.patch"),
    # D-INITIO (2026-11-13): INITIO writes PSG register 15 := $CF (C-BIOS: $8F) and
    # register 11 := $0B, as the VG-8020 AND the CF-3300 do (basic_probe_initio.py).
    # The 7 bytes come from C-BIOS's INIFNK stub right behind it, dead under
    # zerobas's own $003E: nothing after it moves.
    os.path.join(REPO, "cbios-repack", "initio.patch"),
    # D-SCALXYF (2026-11-13): SCALXY answers in F as the VG-8020 does -- $41 when nothing
    # was clipped, $40 when something was (Z set, S / P/V clear, Cy = in range);
    # graphics-cursor.patch's rewrite had dropped C-BIOS's final `rrca` and left F to
    # chance. +3 B: the span ends at $09E2, into island 3 (fperr_to_err moved to main
    # page 1); PNTINI / SCANR / SCANL's C-BIOS `ret`s move 3 B (build_mainrom's guard).
    os.path.join(REPO, "cbios-repack", "scalxy-flags.patch"),
    # D-GRPBASE (2026-11-13): INIGRP / INIMLT leave NAMBAS / CGPBAS -- the text modes'
    # bases -- alone, as the VG-8020 does (basic_probe_biosmode.py); C-BIOS's own CLS for
    # SCREEN 2 / 3, which leaned on them, takes GRPCGP / MLTCGP. Padded in place: 22
    # bytes change, nothing moves.
    os.path.join(REPO, "cbios-repack", "grpbase.patch"),
    # D-LPTSTTF (2026-11-14): LPTSTT answers in F as the VG-8020 does -- ready A = $FF,
    # F = $BB; not ready A = 0, F = $42 (zerobas basic_probe_outdlp.py, lptstt_rdy).
    # `ccf / sbc a,a` gives both; 4 B shorter, padded: 7 bytes change, nothing moves.
    os.path.join(REPO, "cbios-repack", "lptstt-flags.patch"),
    # D-CNVCHRF (2026-11-14): CNVCHR's Z as the VG-8020 -- a converted graphic code NZ + C,
    # a plain / non-graphic one Z + C, the header Z + NC (C-BIOS had the first two swapped;
    # zerobas basic_probe_biosflags.py cnv_*). Same size: 8 bytes change, nothing moves.
    os.path.join(REPO, "cbios-repack", "cnvchr-flags.patch"),
    # D-GRPHEDCLS (2026-11-14): the text-mode clear (cls_text: INITXT, INIT32, CHGMOD 0 / 1,
    # a text CLS) sets GRPHED := 0 as the VG-8020 does; 4 B from INIMLT's D-GRPBASE pad, so
    # the code between that pad and cls_text moves 4 B and nothing after it moves.
    os.path.join(REPO, "cbios-repack", "grphed-cls.patch"),
    os.path.join(REPO, "cbios-repack", "initio-gicini.patch"),
    # D-TDOWNCGE (2026-11-14): TDOWNC stops at the bottom cell row OR below it, as the
    # VG-8020 in SCREEN 2 and 3 -- `jr z` -> `jr c` against the row less one; same size.
    os.path.join(REPO, "cbios-repack", "tdownc-ge.patch"),
]

PINNED_TAG = "v0.31"
PRISTINE_SHA1 = "0d7f546f10ac11b3cdbf4da9941941c18aea2fef"
REPACKED_SHA1 = "2f4bb8810338e46acc96c08ecab5435e5e82e0d0"   # D-TDOWNCGE, 2026-11-14
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
