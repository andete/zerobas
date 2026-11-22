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
    # D-CHSNSA (2026-11-16): CHSNS answers A = PUTPNT - GETPNT (low bytes) as the VG-8020;
    # 8 B shorter, padded -- nothing moves.
    os.path.join(REPO, "cbios-repack", "chsns-a.patch"),
    # D-INITKEYS (2026-11-16): INITXT / INIT32 show the function-key line (FNKSB through the
    # table), INITXT clears 40 * 24 for LINLEN 40, SCREEN 3's clear is $600 -- paid from
    # INIGRP's 6 B D-GRPBASE pad, nothing after it moves.
    os.path.join(REPO, "cbios-repack", "initkeys.patch"),
    # D-LINTTBVAL (2026-11-18): a text clear leaves LINTTB 24, 23, ..., 1 down the rows, as the
    # VG-8020 (C-BIOS: 1 in all); 3 B shorter, padded -- nothing moves.
    os.path.join(REPO, "cbios-repack", "linttb-clear.patch"),
    # D-INITEDGES (2026-11-18): INITXT / INIT32 keep only RG0SAV's bit 0 in R0, and the text clear is
    # 40 * 24 at any LINLEN, as the VG-8020; 10 B shorter, padded -- nothing moves.
    os.path.join(REPO, "cbios-repack", "initedges.patch"),
    # D-POSITCLAMP (2026-11-18): POSIT clamps H / L as the VG-8020 and does nothing in SCREEN 2 / 3,
    # paid from the dead FNKSB / ERAFNK / DSPFNK stubs (zerobas overlays all three); TOTEXT stays put.
    os.path.join(REPO, "cbios-repack", "posit-clamp.patch"),
    # D-CHGETEI (2026-11-18): CHGET returns with interrupts enabled and the flags of its `cp $18`,
    # as the VG-8020; same size -- nothing moves.
    os.path.join(REPO, "cbios-repack", "chget-ei.patch"),
    # D-CHPUTDEL (2026-11-18): CHPUT's DEL moves left as BS and blanks the cell it lands on; ESC l
    # keeps the cursor where it was (its body in POSIT's pad) -- nothing moves.
    os.path.join(REPO, "cbios-repack", "chput-del.patch"),
    # D-CHPUTKEYROW (2026-11-18): from the function-key row LF / cursor-down / ESC B / 28 / a wrap
    # move onto the last text row; 12 / ESC E / ESC j clear through $00C3 (the key line redrawn).
    # Nothing moves.
    os.path.join(REPO, "cbios-repack", "chput-keyrow.patch"),
    # D-CHPUTESCY (2026-11-18): ESC Y's row / column clamp to the last text row / LINLEN as the
    # VG-8020, through POSIT's clamp (posit_row / posit_col); same size -- nothing moves.
    os.path.join(REPO, "cbios-repack", "chput-escy.patch"),
    # D-LINTTBVAL (2026-11-18): a row CHPUT blanks gets LINTTB $AF, and ESC L's last text row $FB, as
    # the VG-8020; chput_esc_k starts 1 B earlier into its pad -- nothing else moves.
    os.path.join(REPO, "cbios-repack", "linttb-marks.patch"),
    # D-INITEDGES (2026-11-18): TOTEXT dispatches on OLDSCR through CHGMOD as the VG-8020 (0..3 that
    # screen, 4..$80 SCREEN 3, $81..$FF SCREEN 0); 7 B from POSIT's pad -- nothing else moves.
    os.path.join(REPO, "cbios-repack", "totext-dispatch.patch"),
    # D-SNSMATC / D-SNSMATPORT / D-KILBUFPTR / D-CHGCAPAF / D-JOYPORT / D-GTTRIGRANGE (2026-11-19): the
    # input calls' measured contracts (zerobas docs/bios/SNSMAT.md, KILBUF.md, CHGCAP.md, GTSTCK.md,
    # GTTRIG.md); GTTRIG's space bar keeps BC with SNSMAT's 2 B, so the labels between them move
    # down 2 (the $0144-$014C / $00D5 / $00D8 vectors follow; ISFLIO's guard in tools/build_mainrom.py too).
    os.path.join(REPO, "cbios-repack", "input-calls.patch"),
    # D-CHGSNDF / D-GETVCF (2026-11-19): CHGSND's `and a` (F $54 for A 0) and GETVC2's loop exiting on
    # its last `dec a` (F $42 / $43 for voices 1-3), as the VG-8020; same size -- 3 bytes differ.
    os.path.join(REPO, "cbios-repack", "sound-flags.patch"),
    # D-LFTQBC / D-LFTQSIZE (2026-11-19): LFTQ leaves B (put + 1) AND size, C get, and counts with that
    # masked put, as the VG-8020; 3 B longer, paid by C-BIOS's PUTQ body (dead: $00F9 is zerobas's
    # bios_putq), now a `ret` + pad, so calc_queue_address stays; PUTQ's guard follows ($17EA).
    os.path.join(REPO, "cbios-repack", "lftq-bc.patch"),
    # D-CHGMODRANGE (2026-11-19): CHGMOD takes A above 3 as the VG-8020 (4..$80 SCREEN 3, $81..$FF
    # SCREEN 0) through TOTEXT's own mapping; 2 B paid by 2 of INIGRP's NOPs, so CHGMOD .. INIGRP move
    # down 2 (CLRSPR's vector -- and its PATCH_RANGES guard -- follow: $02FD).
    os.path.join(REPO, "cbios-repack", "chgmod-range.patch"),
    # D-INITXTBAS (2026-11-19): INITXT leaves ATRBAS / PATBAS as the VG-8020; 12 NOPs, nothing moves.
    os.path.join(REPO, "cbios-repack", "initxt-bas.patch"),
    # D-INIMLTCOL (2026-11-19): SCREEN 3's clear fills BAKCLR x 16 OR BAKCLR as a byte, as the VG-8020
    # (a shift, not a rotate, and no 4-bit mask); 2 B shorter, padded -- nothing moves.
    os.path.join(REPO, "cbios-repack", "inimlt-col.patch"),
    # D-SETCCUT (2026-11-19): READC / SETC are zerobas's since D-SETCCOL (basic/main.asm), so C-BIOS's
    # readc / gcell / setc bodies are CUT (121 B), not left dead (Joost: a fully replaced body is
    # removed); their vectors become `ret`s zerobas overlays, NSETCX calls SETC through $0120. RIGHTC ..
    # the debug helpers move down 121 (TUPC $085E, TDOWNC $087C, SCALXY $089F, MAPXYC $08DD, the $0129
    # rets $08DC); `ds $0D01 - $` holds everything above, so island 3 grows to $096A-$09ED (132 B).
    os.path.join(REPO, "cbios-repack", "readc-setc-cut.patch"),
    # D-CBIOSDEAD part 1 (2026-11-19): every other body zerobas replaced whole below $0D01 is cut --
    # grpprt (with mapxy, its only caller's), scalxy, clrspr + clrspr_attr's head, and debug.asm's
    # hex printers; scratchpad/cbios_reach.py proves nothing in the merged ROM reaches them. 353 B:
    # CLS $0600, NSETCX $0692 (its overlaid call $069A), TUPC $06FD, TDOWNC $071B, the $0129 rets $0745;
    # island 3 is $0773-$09ED (635 B). Everything from $0D01 up keeps its address.
    os.path.join(REPO, "cbios-repack", "dead-bodies-video.patch"),
    # D-CBIOSDEAD part 2 (2026-11-19): the dead bodies between $0D12 and the font pad -- SYNCHR /
    # CHRGTR / OUTDO / GETYPR, INIFNK / STRTMS, LPTOUT, PINLIN / QINLIN, ISCNTC / CKCNTC, the cassette
    # stubs TAPION .. STMOTR, ISFLIO, PUTQ's ret + pad, CALBAS (381 B); scratchpad/cbios_reach.py.
    # Their vectors become `ret`, except LPTOUT's and the cassette ones, which stay `jp` (to a bare
    # `ret`) because zerobas's tape module repoints them over C-BIOS's C3. Everything from CALLF to
    # the font pad moves down (GICINI $1588, BREAKX $1510, CHPUT's TTYPOS overlay $1110); island 1 is
    # $196E-$1BBE (593 B). $0D01-$0D11 and the font keep their addresses.
    os.path.join(REPO, "cbios-repack", "dead-bodies-main.patch"),
    # D-MOVEMASK (2026-11-19): RIGHTC / LEFTC in SCREEN 3 test CMASK's bit 7, as the VG-8020, so a
    # mask that is not a block's goes to $F0 / $0F like the block masks (four rotations swapped its
    # nibbles); lr_n shrinks to `ld hl,CMASK / jp is_sc3`. +14 B: everything after rightc moves
    # (TUPC $0711, TDOWNC $072F; island 3 $0781-$09ED).
    os.path.join(REPO, "cbios-repack", "movemask.patch"),
    # D-VRAMF / D-WRTVDPC / D-CHGCLRMODE / D-CALPATF / D-SETSHADOW (2026-11-20): the VDP calls' flags
    # and edges as the VG-8020 -- RDVRM `and $FF` for the TMS wait (H set), FILVRM keeps F, LDIRMV /
    # LDIRVM end on `or a` ($44), WRTVDP keeps C (no `res 7,c`), CHGCLR's SCREEN 0 path when SCRMOD - 1
    # is negative, CALPAT `cp 8` before its add, set_base_address a plain shift, SETGRP / SETMLT's
    # RG0SAV masks. +4 B: CLS $0604, NSETCX $0696 (its overlaid call $069E), TUPC $0715, TDOWNC $0733,
    # island 3 $0785-$09ED.
    os.path.join(REPO, "cbios-repack", "vdp-calls.patch"),
    # D-SETREGS / D-INIGRPORDER (2026-11-20): the SET calls return HL past the mode's five cells,
    # A = RG6SAV, F $00, DE 0 ($7F03 for SETGRP), as the VG-8020; INIGRP fills the colour table
    # before the patterns, as GRPCGP is (not rounded to $xx00), and both INIGRP / INIMLT clear the
    # sprites last. +15 B: CLS $0614, NSETCX $06A5 (its overlaid call $06AD), TUPC $0724, TDOWNC $0742,
    # island 3 $0794-$09ED.
    os.path.join(REPO, "cbios-repack", "setregs-order.patch"),
    # D-TRGFLGISR (2026-11-20): the key scan stores TRGFLG with bits 4-7 (the joystick triggers,
    # 1 = released) set, as the VG-8020 / CF-3300 leave it idle ($F1; $F0 with space held); the
    # triggers themselves are still not read. +2 B after the ISR: island 1 $1970-$1BBE.
    os.path.join(REPO, "cbios-repack", "trgflg.patch"),
]

PINNED_TAG = "v0.31"
PRISTINE_SHA1 = "0d7f546f10ac11b3cdbf4da9941941c18aea2fef"
REPACKED_SHA1 = "3ed9a5671ed40ff84e7a5559576c3cb5301cc017"   # INITIO: GICINI before the PSG writes, 2026-11-21
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
