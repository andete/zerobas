#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-GATEBLIND -- WHICH graphics-acceptance ROWS CAN ANYTHING REDDEN?

Three gate rows were found BLIND in one week, each by re-deriving it rather
than trusting it: G3's three clip rows (D-SPOKELINE), G6's horizontal
`clip_left` (D-DRAWCLAMP) and `box_bf`, which covers seven pixels in each of two
cells so not one whole byte (D-BFBYTE). Each had been green for months while
blind to the very thing it was named for. That is a pattern, so it gets
measured instead of waited for.

Method: mutate the graphics tenant, rebuild, run the WHOLE gate, and record
which rows go red. A row that NO mutation can redden is doing no work against
this battery.

⚠️ **THE BATTERY IS THE DENOMINATOR, AND IT IS HAND-LISTED.** "No mutation
reddened it" does NOT mean "blind" -- it means "blind to THIS battery". The
output is a CANDIDATE roster to re-derive by hand, exactly as the three known
ones were, not a verdict. [[a-hand-listed-denominator-is-a-scope-claim]]

ROUND 1 (2026-08-17, five mutations) hit the pixel / clamp / line / colour paths
and reddened 123 of 355 rows. Its 232-row roster was dominated by subsystems it
never touches, so ROUND 2 extends the battery into exactly those: the sprite
attribute and pattern tables, the sprite size/magnification state, the VDP
register write path and the VDP()/BASE() argument handling -- the four paths the
round-1 report named as its own blind spots. 263 of 356 reddened, 93 never.

ROUND 3 adds the dimension neither of the first two had: **THE ERROR CODE
ITSELF**. Four of round 2's fifteen surviving sprite/VDP reasons were the same
sentence -- the row asserts an error code, and every cut in the battery produced
that same code, so no cut could ever move it. A row asserting "ERR 2 on this
malformed form" is pinned only by a cut that changes the CODE. Four one-byte code
cuts cover the whole graphics error surface, resident and tenant; DRAW's entire
§5 table is one `ld a,5`, which is why phase L's 25 rows had never moved.

Two rules this apparatus learned the hard way:

* Every mutation is ONE instruction of the SAME LENGTH so that every span stays
  reachable: `check_dead_code.py` fails `make basic-reloc` on an unreachable
  span, and a tree that does not build scores nothing (K-DC3).
* 🔴 THE HASH GUARD MUST WATCH THE ROM THAT ACTUALLY MOVES. A `basic/` edit does
  not move `sub.rom` and a `sub/` edit does not move `basic-reloc.rom`; a guard
  pointed at the wrong one reports a perfect cut as "the mutation did not take".
  Every entry therefore names its own file AND its own ROM.

    python3 -u scratchpad/gate_blindness_sweep.py [--dry] [--round1|--round2|--all]
                                                 [M-... ...]
The default battery is the LATEST round; the earlier rounds' saved gate logs
are carried forward by gate_blindness_report.py instead of re-run.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(HERE, "gate_blindness.json")

SUB = os.path.join(REPO, "sub", "graphics.asm")
CIRC = os.path.join(REPO, "sub", "circleparse.asm")
MAIN = os.path.join(REPO, "basic", "graphics.asm")
ROM = {"sub": os.path.join(REPO, "build", "sub.rom"),
       "main": os.path.join(REPO, "build", "basic-reloc.rom")}

# label: (what it breaks, source file, ROM that must move, old, new)
#
# ROUND 1 -- pixel / clamp / line / colour. ALREADY MEASURED against these very
# ROMs (the D-GATEBLIND commit touched no .asm), so the round-2 aggregate carries
# its five saved gate logs forward instead of re-spending 70 minutes on them.
# `--round1` re-runs them anyway.
ROUND1 = {
    "M-YBOUND": (
        "gfx_plot_cur: the on-screen y bound 192 -> 191, so the BOTTOM pixel "
        "row is never plotted", SUB, "sub",
        "                cp      192\n",
        "                cp      191\n"),
    "M-CLAMPY": (
        "gfx_clamp_coords: the Y max 191 -> 190", SUB, "sub",
        "                ld      a,191               ; max: the Y rows (b=3, b=1)\n",
        "                ld      a,190               ; MUTANT\n"),
    "M-CLAMPX": (
        "gfx_clamp_coords: the X max 255 -> 254", SUB, "sub",
        "                ld      a,255               ; max: the X rows (b=4, b=2)\n",
        "                ld      a,254               ; MUTANT\n"),
    "M-BRESERR": (
        "gfx_bres_init: the ERR seed dmaj>>1 computed on the WRONG half, so "
        "every sloped line picks a different sub-pixel phase", SUB, "sub",
        "                srl     h\n                rr      l                   ; HL = dmaj >> 1\n",
        "                srl     l\n                rr      l                   ; MUTANT\n"),
    "M-COLOUR": (
        "gfx_color_rmw: the clash decision inverted (c == bg now SETS)", SUB, "sub",
        "                jr      z,gcr_clear         ; c == bg -> clear the pixel, colour untouched\n",
        "                jr      nz,gcr_clear        ; MUTANT\n"),
}

# ROUND 2 -- the sprite and VDP paths. Ordered WIDEST FIRST, so a run stopped
# early still clears as much of the round-1 roster as possible.
MUTS = {
    # --- the shared G8/G7 index grammar (resident) --------------------------
    "M-G8PAREN": (
        "g8_open_paren: the closing `)` of every VDP(n) / BASE(n) / SPRITE$(n) "
        "index read as `:` instead, so the whole shared index grammar misses",
        MAIN, "main",
        "                cp      ')'\n                jp      nz,gfx_syntax\n"
        "                inc     hl\n                ret\n",
        "                cp      ':'                 ; MUTANT\n                jp      nz,gfx_syntax\n"
        "                inc     hl\n                ret\n"),
    # --- PUT SPRITE's argument list (resident) ------------------------------
    "M-PUTCOMMA": (
        "ex_put_sprite: the comma after the plane read as `;`, so every PUT "
        "SPRITE that carries arguments is a Syntax error",
        MAIN, "main",
        "                ld      (GFX_SN),de\n                call    skip_spaces\n"
        "                cp      ','\n                jp      nz,gfx_syntax       ; `PUT SPRITE 0` -> ERR 2 (measured)\n",
        "                ld      (GFX_SN),de\n                call    skip_spaces\n"
        "                cp      ';'                 ; MUTANT\n                jp      nz,gfx_syntax       ; `PUT SPRITE 0` -> ERR 2 (measured)\n"),
    # --- SPRITE$= 's screen-mode gate (resident) ----------------------------
    "M-SPRSCR0": (
        "spr_assign: the SCREEN 0 gate INVERTED -- SPRITE$(n)= is refused in "
        "the graphics modes and accepted in SCREEN 0",
        MAIN, "main",
        "spr_assign:\n                inc     hl                  ; past the '$'\n"
        "                ld      a,(SCRMOD)\n                or      a\n"
        "                jp      z,gfx_err5          ; SPRITE$= in SCREEN 0 -> ERR 5\n",
        "spr_assign:\n                inc     hl                  ; past the '$'\n"
        "                ld      a,(SCRMOD)\n                or      a\n"
        "                jp      nz,gfx_err5         ; MUTANT\n"),
    # --- the VDP register write path (tenant) -------------------------------
    "M-VDPMIRR": (
        "g8_wrvdp: the RAM mirror written ONE REGISTER SLOT HIGH -- the chip "
        "still gets the right byte, every mirror read does not",
        SUB, "sub",
        "                ld      hl,RG0SAV\n                ld      b,0\n",
        "                ld      hl,RG0SAV+1         ; MUTANT\n                ld      b,0\n"),
    # --- the sprite size/magnification state (tenant) -----------------------
    "M-SPRSZAPL": (
        "gfx_spr_size_apply: only the MAGNIFICATION bit re-applied to VDP "
        "register 1, so SCREEN n,2 loses its 16x16 across CHGMOD",
        SUB, "sub",
        "                ld      a,(GFX_SSIZE)\n                and     $03\n",
        "                ld      a,(GFX_SSIZE)\n                and     $01                 ; MUTANT\n"),
    # --- the sprite PATTERN table address (tenant) --------------------------
    "M-SPRPBASE": (
        "gfx_spr_addr: the sprite pattern generator base 8 bytes high, so "
        "every SPRITE$ write and read is one 8x8 entry off",
        SUB, "sub",
        "                ld      de,GFX_SPAT_BASE\n",
        "                ld      de,GFX_SPAT_BASE+8  ; MUTANT\n"),
    # --- the attribute-x snapshot that brackets CHGMOD (tenant) -------------
    "M-SPRXREST": (
        "gfx_spr_xrest: the attribute entry stride 4 -> 3, so the 32 saved x "
        "bytes go back over the y/pattern/colour bytes of later planes",
        SUB, "sub",
        "                inc     hl                  ; 4 bytes per attribute entry\n"
        "                inc     hl\n                inc     hl\n                inc     hl\n"
        "                djnz    gsxr_lp\n",
        "                inc     hl                  ; 4 bytes per attribute entry\n"
        "                inc     hl\n                inc     hl\n                nop                 ; MUTANT\n"
        "                djnz    gsxr_lp\n"),
    # --- the sprite ENTRY SIZE read (tenant) --------------------------------
    "M-SPRENTSZ": (
        "gfx_spr_addr: the 16x16 bit read from RG1SAV bit 2 instead of bit 1, "
        "so every entry is 8 bytes whatever SCREEN n,2 said",
        SUB, "sub",
        "                ld      a,(RG1SAV)\n"
        "                and     $02                 ; bit 1 = 16x16 (bit 0 is magnification,\n",
        "                ld      a,(RG1SAV)\n"
        "                and     $04                 ; MUTANT (bit 0 is magnification,\n"),
    # --- the BASE(n)= reprogram (tenant) ------------------------------------
    "M-BASESHIFT": (
        "g8_wrshifted: R4 (pattern generator) divided by $1000 instead of "
        "$800",
        SUB, "sub",
        "                ld      b,11\n                ld      c,4                 ; R4 = pattern generator / $800\n",
        "                ld      b,12                ; MUTANT\n                ld      c,4                 ; R4 = pattern generator / $800\n"),
    "M-BASEGMAP": (
        "g8_gmap: SCREEN 1 reprograms from ITS OWN group instead of group 2 -- "
        "the reference's off-by-one undone",
        SUB, "sub",
        "g8_gmap:        db      0, 2, 3, 3\n",
        "g8_gmap:        db      0, 1, 3, 3\n"),
    # --- the sprite attribute VALUE rules (tenant) --------------------------
    "M-SPRECLK": (
        "gfx_spr_attr: the early-clock offset for a negative x is 31, not 32",
        SUB, "sub",
        "                add     a,32\n",
        "                add     a,31                ; MUTANT\n"),
    "M-SPRPATSC": (
        "gfx_spr_attr: the 16x16 pattern number stored as 2n instead of 4n",
        SUB, "sub",
        "                add     a,a                 ; ... and the stored byte is 4n\n"
        "                add     a,a\n",
        "                add     a,a                 ; ... and the stored byte is 4n\n"
        "                nop                         ; MUTANT\n"),
    # --- the domain bounds nothing else touches (tenant + resident) ---------
    "M-SPRPLANE": (
        "gfx_spr_attr: the PUT SPRITE plane bound 32 -> 31",
        SUB, "sub",
        "                cp      32\n                jr      nc,gfx_spr_err5     ; plane > 31 -> ERR 5\n",
        "                cp      31                  ; MUTANT\n                jr      nc,gfx_spr_err5     ; plane > 31 -> ERR 5\n"),
    "M-VDPBOUND": (
        "gfx_vdp_wr: the VDP(n)= index bound 8 -> 7, so VDP(7)= is refused",
        SUB, "sub",
        "                cp      8\n                jr      nc,g8_err5          ; 8 (read-only) and beyond -> ERR 5\n",
        "                cp      7                   ; MUTANT\n                jr      nc,g8_err5          ; 8 (read-only) and beyond -> ERR 5\n"),
    "M-BASEGRAIN": (
        "g8_grain: the NAME table grain $400 -> $80, so a name base the "
        "reference refuses is accepted",
        SUB, "sub",
        "g8_graintab:    dw      $03FF, $007F, $07FF, $007F, $07FF",
        "g8_graintab:    dw      $007F, $007F, $07FF, $007F, $07FF"),
    "M-G8RDLIM": (
        "ev_f_vdp: the VDP(n) READ domain 0..8 -> 0..7, so the status-register "
        "copy VDP(8) is refused",
        MAIN, "main",
        "                ld      a,9                 ; VDP(n): n in 0..8\n",
        "                ld      a,8                 ; MUTANT\n"),
}

# ROUND 3 -- THE DIMENSION ROUNDS 1 AND 2 NEVER TOUCHED: THE ERROR CODE ITSELF.
# Round 2 left 15 sprite/VDP rows unreddened and four of the reasons were the same
# sentence -- the row asserts an error code, and every cut in the battery produced
# that same code. A row that asserts "ERR 2 on this malformed form" cannot be moved
# by any cut that also raises ERR 2; it moves when the CODE moves. Four one-byte
# code cuts cover the whole graphics error surface, resident and tenant, and reach
# straight into phase L (25 rows), whose entire §5 table is one `ld a,5`.
MUTS3 = {
    "M-ERR5": (
        "gfx_err5: the resident graphics Illegal function call raised as ERR 6",
        MAIN, "main",
        "gfx_err5:\n                ld      a,5                 "
        "; Illegal function call (PSET/PRESET in SCREEN 0/1)\n",
        "gfx_err5:\n                ld      a,6                 ; MUTANT\n"),
    "M-DRWERR5": (
        "gdrw_err5: the WHOLE DRAW error table raised as ERR 6 instead of ERR 5",
        SUB, "sub",
        "                ld      a,5                 ; Illegal function call (the whole §5 table\n",
        "                ld      a,6                 ; MUTANT (the whole §5 table\n"),
    "M-SYNERR": (
        "gfx_syntax: the trappable graphics Syntax error raised as ERR 3",
        MAIN, "main",
        "gfx_syntax:\n                ld      a,2\n",
        "gfx_syntax:\n                ld      a,3                 ; MUTANT\n"),
    "M-TYPERR": (
        "gfx_typeerr: Type mismatch raised as ERR 14",
        MAIN, "main",
        "                ld      a,13                ; Type mismatch",
        "                ld      a,14                ; MUTANT"),
    "M-SPRONOFF": (
        "ex_sprite: the ON/OFF/STOP decode INVERTED -- the three arming forms "
        "are Syntax errors and a bare SPRITE is accepted",
        MAIN, "main",
        "                call    onoff_decode        ; A = ZTS_OFF / ZTS_ON / ZTS_STOP\n"
        "                jp      nc,gfx_syntax       ; bare SPRITE -> ERR 2 (measured)\n",
        "                call    onoff_decode        ; A = ZTS_OFF / ZTS_ON / ZTS_STOP\n"
        "                jp      c,gfx_syntax        ; MUTANT\n"),
    "M-PUTSCR0": (
        "ex_put_sprite: its OWN SCREEN 0 gate inverted (M-SPRSCR0 cut "
        "spr_assign's, which is a different routine)",
        MAIN, "main",
        "ex_put_sprite:\n                inc     hl                  ; past the SPRITE token\n"
        "                ld      a,(SCRMOD)\n                or      a\n"
        "                jp      z,gfx_err5          ; PUT SPRITE in SCREEN 0 -> ERR 5\n",
        "ex_put_sprite:\n                inc     hl                  ; past the SPRITE token\n"
        "                ld      a,(SCRMOD)\n                or      a\n"
        "                jp      nz,gfx_err5         ; MUTANT\n"),
    "M-XRCOUNT": (
        "gfx_spr_xrest: only plane 0's attribute x restored, not 32 -- the cut "
        "K-XR1 proved nothing in the old gate could see (now init_p31_x's)",
        SUB, "sub",
        "                ld      b,32\ngsxr_lp:\n",
        "                ld      b,1                 ; MUTANT\ngsxr_lp:\n"),
}

# ROUND 4 -- the three classes round 3's §16 named, plus the five rows whose error
# SITE round 3 proved it had not found. Those five were closed at the desk, not by
# more cuts: CIRCLE's parse is a SUB-ROM TENANT with its OWN error tail
# (sub/circleparse.asm cpt_err5), and LINE has its own `elg_syntax` distinct from
# `gfx_syntax` -- two error-code sites in files the round-3 battery never opened.
MUTS4 = {
    "M-CIRCERR5": (
        "cpt_err5: the CIRCLE PARSE TENANT's own ERR 5 raised as ERR 6 -- a "
        "fourth error-code site, in a file rounds 1-3 never touched",
        CIRC, "sub",
        "cpt_err5:\n                ld      a,5\n",
        "cpt_err5:\n                ld      a,6                 ; MUTANT\n"),
    "M-LINESYN": (
        "elg_syntax: LINE's OWN Syntax error tail (not gfx_syntax) raised as ERR 3",
        MAIN, "main",
        "elg_syntax:\n                ld      a,2                 ; Syntax error (bad LINE form)\n",
        "elg_syntax:\n                ld      a,3                 ; MUTANT\n"),
    "M-GRPAC": (
        "gfx_work_area: GRPACX fed the Y value -- the last-referenced point's x "
        "is wrong for every statement that sets it",
        MAIN, "main",
        "                ld      (GRPACX),bc         ; last-referenced point X\n",
        "                ld      (GRPACX),de         ; MUTANT\n"),
    "M-PSETOFF": (
        "gfx_plot_go: an off-screen PSET RAISES ERR 5 instead of being a silent "
        "no-op -- the acceptance class needs a cut that refuses what the "
        "reference allows",
        MAIN, "main",
        "                jp      nc,exec_stmt        ; off-screen -> no plot (work area already moved)\n",
        "                jp      nc,gfx_err5         ; MUTANT\n"),
    "M-DRWSCALE": (
        "gdo_s: DRAW's scale bound tested on the LOW byte, so every S but S0 is "
        "ERR 5 (S255 included -- the accepted edge)",
        SUB, "sub",
        "                ld      a,h\n                or      a\n"
        "                jp      nz,gdrw_err5        ; S > 255 -> ERR 5 (measured: S255 ok, S256 not)\n",
        "                ld      a,l                 ; MUTANT\n                or      a\n"
        "                jp      nz,gdrw_err5        ; S > 255 -> ERR 5 (measured: S255 ok, S256 not)\n"),
    "M-GRPAC2": (
        "gfx_line_op: LINE's FINAL work-area write fed GRPACX the Y value. "
        "M-GRPAC cut the RESIDENT gfx_work_area and the grpac_* rows held, "
        "because LINE only STAGES p1 there -- the p2 write that those rows "
        "actually read moved INTO THE TENANT with G8's space carve. Right "
        "routine, later writer wins.",
        SUB, "sub",
        "                ld      hl,(GFX_X2)\n                ld      (GXPOS),hl\n"
        "                ld      (GRPACX),hl\n",
        "                ld      hl,(GFX_X2)\n                ld      (GXPOS),hl\n"
        "                ld      (GRPACY),hl         ; MUTANT\n"),
    "M-OVFCHK": (
        "gfx_eval_int16: the STRICT int16 check dropped -- every graphics "
        "argument beyond int16 truncates instead of raising ERR 6",
        MAIN, "main",
        "                jp      get_int16_checked   ; tail call: ret serves both\n",
        "                jp      fac_to_int_strict   ; MUTANT\n"),
}

# Predictions written BEFORE the run (scored in docs/gate-blindness-sweep.md).
# A row NOT listed here that reddens is as interesting as one listed that does
# not: the whole point of the exercise is which rows can move at all.
PREDICT = {
    "M-G8PAREN":   "every VDP()/BASE()/SPRITE$() index -> ERR 2: most of Q1, Q2 "
                   "and the SPRITE$ half of N/P; Q3 ie_off too (VDP(1) never "
                   "clears the IE bit). PUT SPRITE's own (x,y) is parse_coord, "
                   "NOT this routine, so the attr_* rows should NOT move.",
    "M-PUTCOMMA":  "every PUT SPRITE that carries arguments -> ERR 2: all of N's "
                   "attr_* rows and O's put_* rows except put_bare/put_comma, "
                   "which are ERR 2 on both sides already.",
    "M-SPRSCR0":   "N's pattern rows and P's SPRITE$ rows; O spr_scr0_wr, "
                   "spr_scr1_wr, spr_n255, spr_numeric, spr_noparen, spr_noeq. "
                   "spr_n256/spr_n_neg should NOT move -- ERR 5 either way.",
    "M-VDPMIRR":   "every Q1 row that compares registers (17), plus Q2's "
                   "read-back rows rd_vdp1 / wr_vfrac / wr_vnegfrac / "
                   "wr_v255fr / g_self / g_mid_stmt / g_if_stmt.",
    "M-SPRSZAPL":  "the 16x16 rows N pat_16_*/read_16/attr_16_*, O "
                   "put_pat64_16, P size_persist/size_persist0/"
                   "size_mag3. size_mag and size_back should NOT move. "
                   "🔴 put_pat63_16 WAS LISTED HERE AND CANNOT MOVE (corrected "
                   "2026-09-05): pattern 63 is in range under BOTH the 8x8 and "
                   "the 16x16 rule, so it is accepted either way and the row "
                   "compares only the error outcome. M-SPRPATSC's own "
                   "prediction said so in this same dict -- two predictions "
                   "contradicted each other about one row and neither was "
                   "read against the other. put_pat64_16 is the discriminator: "
                   "64 is out of range at 16x16 and in range at 8x8, so it "
                   "reads ERR 5 vs accepted (measured).",
    "M-SPRPBASE":  "every N pattern row (pat_8_*, pat_16_*, read_*), P "
                   "pat_survives, cls_keeps, size_persist. The attr_* rows read "
                   "the ATTRIBUTE table and should NOT move.",
    "M-SPRXREST":  "P init_planes, init_forclr, cls_keeps (the table is read "
                   "after a mode set). N's attr_* rows overwrite all four bytes "
                   "of plane 0 and should mostly survive.",
    "M-SPRENTSZ":  "N pat_16_full/pat_16_short/pat_16_wrap/read_16, P "
                   "size_persist/size_persist0/size_mag3. size_back and "
                   "size_mag should NOT move (entry is 8 either way).",
    "M-BASESHIFT": "ONLY the SCREEN 0 reprograms -- s0_name, s0_satr, s0_spat, "
                   "s0_desync. Groups 2 and 3 hold pattern base $0000, and "
                   "0>>11 == 0>>12, so their R4 is unchanged.",
    "M-BASEGMAP":  "Q1 s1_name, s1_satr, s1_poison.",
    "M-SPRECLK":   "N attr_neg_x, attr_neg_x32, attr_work. attr_ec_clear should "
                   "NOT move -- its second statement re-writes a positive x.",
    "M-SPRPATSC":  "N attr_16_pat1, attr_16_pat63. O put_pat63_16 should NOT "
                   "move: accepted either way.",
    "M-SPRPLANE":  "O put_plane31 only.",
    "M-VDPBOUND":  "Q1 vdp_r7 only.",
    "M-BASEGRAIN": "Q2 b_name_80 only (b_name_ok / b_name_odd are the controls "
                   "and should NOT move).",
    "M-G8RDLIM":   "Q2 rd_vdp8 only.",
    # --- round 3: the error code itself -----------------------------------
    "M-ERR5":      "every row asserting an ERR 5 raised by the RESIDENT graphics "
                   "surface: B pset_scr0_err, D bf_scr0/scr0_err, F scr0_err and "
                   "the aspect/colour domain rows, G rneg_err, J's scr0/scr1 and "
                   "colour rows, L screen0/screen1, O put_scr0. NOT the tenant's "
                   "own ERR 5s (spr_tenant re-raises GFX_RES, a different byte).",
    "M-DRWERR5":   "most of phase L: badletter, bare_s/a/c/m, angle4, colour16, "
                   "colour_neg, scale256, count_big, m_missing, eq_nosemi, "
                   "x_nosemi, lead_semi, dbl_semi, comma_sep, junk, empty, "
                   "bare_b. The ACCEPTED edges (scale255ok, scale0, offscreen) "
                   "must NOT move, and screen0/screen1/numeric belong to the "
                   "resident tails, not this one.",
    "M-SYNERR":    "the ERR 2 assertions from gfx_syntax: O put_bare, put_comma, "
                   "put_5args, put_trailing, put_halfxy, spr_bare; Q2 rd_nopar; "
                   "D badsuffix, nodash.",
    "M-TYPERR":    "J tile_str_err and L numeric (the others -- O spr_numeric, "
                   "Q2 g_str_* -- are already reddened by round 2).",
    "M-SPRONOFF":  "O spr_on, spr_off, spr_stop, spr_on_s0 (all four are "
                   "accepted no-ops on the reference) and spr_bare.",
    "M-PUTSCR0":   "O put_scr0. put_scr1 and the attr_* rows move too but round "
                   "2 already reddened them.",
    # --- round 4: the three named classes + the two unfound sites ----------
    "M-CIRCERR5":  "G rneg_err, F aspect_neg_err, F colour16_err -- the three "
                   "rows M-ERR5 proved were NOT raised by gfx_err5. Plus any "
                   "other CIRCLE domain row, though most are already red.",
    "M-LINESYN":   "D badsuffix and D nodash -- the two rows M-SYNERR proved "
                   "were NOT raised by gfx_syntax.",
    "M-GRPAC":     "the WORK-AREA class: D grpac_line, D grpac_box, F "
                   "grpac_step, and phase R's w_line_*/w_box_*/w_bf_*/"
                   "w_step_after (STEP resolves against GRPAC). The w_draw_* "
                   "rows go through gdrw's own cursor and may hold.",
    "M-PSETOFF":   "B pset_offscr_ok. ⚠️ The three A/clip_noop_* rows should NOT "
                   "move: an untrapped ERR 5 aborts before the hold loop, but "
                   "the cells they read stay blank either way -- which is the "
                   "whole point of those rows.",
    "M-DRWSCALE":  "L scale255ok and L scale0 (both end with DRAW\"S4\", now "
                   "ERR 5), plus every K/C row carrying an S command "
                   "(scale_s2, scale_s8, clampD_scaled).",
    "M-GRPAC2":    "the LINE/BOX half of the WORK-AREA class: D grpac_line, D "
                   "grpac_box, R w_line_off, w_line_neg, w_line_on, w_box_off, "
                   "w_bf_on, w_bf_topleft, and F grpac_step if CIRCLE's spokes "
                   "route through gfx_line_op.",
    "M-OVFCHK":    "the ERR 6 class: B pset_ovf_err, D ovf_end, F ovf_centre, "
                   "F ovf_radius, J ovf_err. ⚠️ FPERR is left SET, so a batched "
                   "phase may cascade the way M-VDPMIRR did -- if the count is "
                   "far above 5, that is the reason, not the targeting.",
    "M-XRCOUNT":   "P init_p31_x only -- K-XR1 measured exactly this, and the "
                   "cut is now a permanent battery member so the row cannot go "
                   "quietly blind again.",
}


def sh(cmd, log):
    with open(log, "w") as f:
        return subprocess.run(cmd, shell=True, cwd=REPO, stdout=f,
                              stderr=subprocess.STDOUT).returncode


def romhash(which):
    return hashlib.sha256(open(ROM[which], "rb").read()).hexdigest()[:8]


def build():
    """Both ROMs: `basic-reloc` runs the dead-code check and prints the walls,
    `repack-machine` rebuilds the sub/disk ROMs and installs the machine."""
    return (sh("make basic-reloc", "/tmp/mut_build.log")
            or sh("make repack-machine", "/tmp/mut_inst.log"))


def main() -> int:
    table = dict(MUTS4)
    if "--round1" in sys.argv:
        table = dict(ROUND1)
    elif "--round2" in sys.argv:
        table = dict(MUTS)
    elif "--round3" in sys.argv:
        table = dict(MUTS3)
    elif "--all" in sys.argv:
        table = {**ROUND1, **MUTS, **MUTS3, **MUTS4}
    want = [k for k in sys.argv[1:] if k in table] or list(table)

    print("=== D-GATEBLIND: which gate rows can a mutation redden? ===\n")
    src = {}
    ok = True
    for k in want:
        desc, path, rom, old, new = table[k]
        n = open(path).read().count(old)
        src[path] = None
        flag = "" if n == 1 else f"  🔴 SITE MATCHES {n} TIMES"
        print(f"  {k:12} [{os.path.relpath(path, REPO)} -> {rom}.rom] {desc}{flag}")
        print(f"               predict: {PREDICT.get(k, '(none written)')}")
        ok &= n == 1
    print(f"\n  battery size: {len(want)} mutations "
          f"(the DENOMINATOR -- see the module docstring)")
    if not ok:
        print("\n🔴 at least one site is not unique -- fix it before running")
        return 2
    if "--dry" in sys.argv:
        return 0

    for p in src:
        src[p] = open(p).read()
    base = {r: romhash(r) for r in ROM}
    print(f"\nunknifed  " + "  ".join(f"{r}.rom={h}" for r, h in base.items()))

    reddened, ran = {}, []
    try:
        for name in want:
            desc, path, rom, old, new = table[name]
            print(f"\n########## {name}")
            open(path, "w").write(src[path].replace(old, new, 1))
            if build():
                print("  🔴 MUTANT DOES NOT BUILD -- scores nothing")
                open(path, "w").write(src[path])
                build()
                continue
            h = romhash(rom)
            if h == base[rom]:
                print(f"  🔴 {rom}.rom HASH UNCHANGED ({h}) -- "
                      f"THE MUTATION DID NOT TAKE")
                open(path, "w").write(src[path])
                build()
                continue
            print(f"  {rom}.rom {base[rom]} -> {h}; running the gate...")
            log = f"/tmp/mut_{name}_gate.log"
            sh("make graphics-acceptance", log)
            ran.append(name)
            open(path, "w").write(src[path])
            with open(log, errors="replace") as f:
                red = sum(1 for l in f if l.startswith("  FAIL"))
            print(f"  RED rows (raw line count) {red}  -> {log}")
    finally:
        for p, text in src.items():
            open(p, "w").write(text)
        build()
        now = {r: romhash(r) for r in ROM}
        print("\nrestored  " + "  ".join(f"{r}.rom={h}" for r, h in now.items())
              + ("  OK" if now == base else "  🔴 RESTORE FAILED"))

    with open(os.path.join(HERE, "gate_blindness_round2.json"), "w") as f:
        json.dump(dict(battery=ran, predict={k: PREDICT.get(k) for k in ran}), f,
                  indent=1)
    print(f"\nran {len(ran)}/{len(want)}. Now aggregate WITHOUT re-spending "
          f"emulator time:\n  python3 -u scratchpad/gate_blindness_report.py "
          f"<baseline.log> /tmp/mut_*_gate.log")
    return 0


if __name__ == "__main__":
    sys.exit(main())
