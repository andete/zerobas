# D-WSZERO S11 — transient cells into idle published bytes: the re-verified move list (2026-10-15)

Read-only prep against today's tree (HEAD `d7daa2cc`, uncommitted S9 work in the tree; build syms of
2026-10-15 21:40 = the S9 build). Nothing in the repo was written, built or run. Instruments (all in this
directory, run with `python3 -B` from the repo root so no `__pycache__` lands in `tools/`):

| script | what it does | output |
|---|---|---|
| `census.py` | every name whose VALUE falls in each host span, per sym (`basic-reloc`, `sub`, `sub2`, `disk`), plus every source-map cell (`tools/ram_map.Map`, basic + disk, declared widths) overlapping it | `census.out` |
| `refs.py` | every reference of each guest name in basic/ sub/ sub2/ disk/, with its enclosing label | `refs_all.out` |
| `addrof.py`, `addrof_hi.py` | every `ld rr,NAME[±n]` (address-of, not deref) of a window name / a name in $F380-$FFFF, flagged when a loop / ldir / `inc hl` follows: the block-walk scan | `addrof.out`, `addrof_hi.out` |
| `sim.py` | **the dry run**: re-resolves both components' maps with the S11 equates substituted IN MEMORY, then checks every moved name lands on its target, every other name is unchanged, NO NEW OVERLAP in $E000-$FFFF, and the ram-width ratchet | `sim.out` (VERDICT OK) |
| `table.py`, `repl.py`, `freed.py`, `remain.py` | the move table, the line-by-line replacement list, the freed bytes, what remains | `table.out`, `s11_replacements.md`, `remain.out` |

**(unverified)** marks every claim not read off code/syms. `sim.py` is the S11 analogue of
`tools/ws_shift.py`'s verifier (which cannot express this move: it only rewrites literal equates by one
delta per range, and most guests are chained `X equ Y + n`).

## 0. Verdict in one screen

* **63 names move (109 B at their new homes), 4 stay-names are re-anchored, 0 new byte sharing.** Every
  guest gets bytes that no other zerobas cell uses (dry run: NEW overlaps 0, both components). So the
  "can two guests sharing a byte be live together" question is answered by construction: there is no
  sharing; the S11 changes only REMOVE existing aliases (INP_CURSOR/NUMBUF, KEYARG/WIDIG, GFX_CPHASE over
  GFX_WE_P's high byte, eight sprite cells inside PAINT's GFX_PSTK span, GFX_G8N/GFX_PPITCH), and no code
  relies on any of those aliases (each split cell is written before it is read by its own users — §2).
* **92 window bytes are freed** ($ECF8-$F194); the other 15 old-home bytes stay covered by cells that do not
  move (GFX_PSTK $ED28-$ED33, GFX_PPITCH $ED99, GFX_WE_P's high byte $EFBE, WIDIG $F107).
* **The classification's (a′) plan had five defects; all fixed here** (§1.3): two contiguity breaks
  (LINE X1..Y2 split, CIRCLE SOCT..EU14 split), MATH_N treated as 1 B (it is a 2-B word; at $F805 it would
  overlap ARGA[0]), two hosts that are someone's planned same-job cell (FILTAB — D-FCBSHAPE; INTVAL /
  ONGSBF — S2's filed faithful-trap step) and MEMSIZ (BASIC-visible). Its shared ARG/DAC-tail words are
  replaced by exclusive bytes.
* **Dropped / deferred: 18 B** — MATH_N/MATH_SIGN/SQRT_K (S14 math frame), the detok cells DB_SKIP,
  DB_RESSKIP, DB_SP, DT_TOK, DT_TOKN, DB_RESPTR (12 B, go with DB_WIN in S14), RVDESC (3-B `ldir` unit, S12).
* **Build blockers the edit must handle** (§3.3): the assert `IF GFX_G8V + 2 > BASIC_WS_CEIL` FIRES after the
  move; `FREE-RAM $F70A..$F712` / `$F740..$F74C` claims become false (ram-claim-check); 5 ram-width pins go
  stale + GFX_PPITCH needs a width (ram-map-check); `docs/ram-map.md` must be regenerated; rule-B `; $XXXX:`
  annotations must carry the new addresses (wall-literal-check); STRPTR is in the generated disk ABI.

## 1. The hosts

### 1.1 Zerobas side — idle, re-verified today

For every host byte: **no value in any of the four syms** (`census.out`: the only names in any host span
are FAC/DAC at $F7F6 w=8, which ends $F7FD); **no equate resolving into it** (ram_map basic + disk, which
also reads disk/*.asm `equ`s); **no literal address** in basic/ sub/ sub2/ disk/ tape/tape.asm (grep of every
host address, `$` and `0..H` forms — the only hit is a comment, tape/tape.asm:44); **no block walk reaches
it** (`addrof_hi.out`: every address-of + loop/ldir site over names in $F380-$FFFF — ZTRAP's fill stops at
TRAPPEND $FC88 [basic/traps.asm:313], every FAC copy is bounded by the type to 4/8 B [basic/arrays.asm:982,
basic/expr.asm:946, basic/vars.asm:679/766, disk/kernel.asm:3981/4185, sub/strheap.asm:2910], DIVPAD's
loops stop at DIVPAD+14 = $F84C, QUETAB/VCB walks use non-negative offsets); **no interrupt-time code**
names any guest or host (basic/traps.asm, playsvc.asm, keytrap.asm, sprtrap-body.inc, subromcall.asm
htimi_guard: 0 hits; the RAM trampoline SUB_INT_RAM is 36 B = $F92D-$F950, sub_int_template..end in
basic-reloc.sym).

### 1.2 C-BIOS side, and the reference's own use (per published name/job)

C-BIOS (`~/projects/cbios/src`, + the 8 repack patches in `cbios-repack/`): **no host name is referenced
outside systemvars.asm** except comments (DAC: main.asm:1579, statements.asm:34; INTCNT: main.asm:2642
"TODO"), and **no literal host address** appears. Its only writes are boot-time: `init_ram` zero-fills
$F380-$FFFD once (main.asm:1088), and DPPAGE/ACPAGE/MODE ($FAF5/$FAF6/$FAFC) are written only under
`IF VDP != TMS99X8` (video.asm:589-593, main.asm:810-823) — not assembled in the MSX1 repack.
**AUTFLG $F6AA is READ by C-BIOS INLIN (inlin.asm:35) — not used as a host.**

"(i)" = the guest does the reference's job there; "(ii)" = exclusive with the reference's own use only by
convention (zerobas never performs the reference's job in that cell).

| host | bytes | the reference's job (published name) | zerobas today | guests (S11) | kind |
|---|---|---|---|---|---|
| H1 PARM1 $F70A-$F711 | 8 | DEF FN parameter definitions (the VG-8020 used 46 B of PARM1 for a 9-parameter double FN, s10_parm1_fill) | idle; zerobas's FN frame is at $F74C+ (S6). Declared `FREE-RAM $F70A..$F712` (sysvars.inc:4156). **Runtime fill NOT measured** (S10.0 covered $F71C-$F74C only) | GFX_X1, Y1, X2, Y2 (LINE) | (ii) |
| H2 PARM1 $F740-$F74B | 12 | same | idle, **measured** (S10.0: 0 writes on 7 rows, both builds) | GFX_SOCT, SU14, EOCT, EU14, CXC, CYC (CIRCLE) | (ii) |
| H3 TRPTBL $FC8A-$FC99 + RTYCNT $FC9A | 17 | TRPTBL entries past INTERVAL: "24 B reserved, all zeroed by RUN" (TODO.md D-RAMFOOT, trptbl_probe.out); RTYCNT "usage unknown" | ZTRAP block ends at STOPHOLD $FC89 | DRAW/CIRCLE co-routine + DRAW parse: DPTR, DEND, DCMD, DSUBN, DSUBI, DSUB(4), DSUBLEN, DREQ, DRESUME, DVAL | (ii) — reserved bytes |
| H4 $F408-$F413 | 12 | HIGH_/HEADER (tape write timing, copied by SCREEN,,,baud and read by the reference's TAPOON/TAPOUT), ASPCT1/ASPCT2 (CIRCLE default aspect), ENDPRG (RESUME NEXT fake program end, 58,0,0,0,0; the reference's SAVTXT points at it at the prompt) | idle: zerobas's tape reads only ACT_LOW $F406 / LOWLIM / WINWID (tape/tape.asm:297, basic/save.asm:578 writes 2 B) | NUMBUF (8), GFX_DTX, GFX_DTY | (ii) |
| H5 ARG tail $F84D-$F856 | 10 | ARG (16 B): the math pack's second operand / extended scratch; USR code and hooks may use it | idle (zerobas math ends at DIVPAD+14 = $F84C) | float core WSRC, FP_LHSVAL, FP_TMP_B, FP_RSIGN, MUL_ADIG, MUL_CARRY + KEYARG | (i)-ish (numeric scratch), **T-only rule** below |
| H6 MAXUPD/MINUPD $F3EC-$F3F1 | 6 | two `JP nnnn` the reference's LINE builds per statement | idle | GFX_SN, SDESC, SC (sprites) | (ii), graphics scratch |
| H7 CONLO+4 $F66E-$F671 | 4 | CHRGTR's last numeric constant, bytes 4-7 (a double constant) | idle; S5 uses CONLO+0..3 for POOLSIZE/TXTCEIL | GFX_R, GFX_ASPS (CIRCLE) | (ii) |
| H8 $F417-$F41B | 5 | NTMSXP (printer type), RAWPRT (raw printing), VLZADR/VLZDAT (VAL's temporary terminator) | idle | GFX_SPATN, GFX_G8N, GFX_VLEN | (ii) — ⚠️ NTMSXP/RAWPRT are user-settable SETTINGS on the reference; a future "honour NTMSXP" item must evict these |
| H9 $F665-$F669 | 5 | DONUM, CONTXT, CONSAV, CONTYP (crunch / CHRGTR constant bookkeeping) | idle (VRAM_FLAG is DORES $F664) | GFX_G8V, TGT_ADDR, GFX_SSIZE | (ii) |
| H10 $F954-$F958 | 5 | LFPROG/RTPROG (PAINT), MCLTAB/MCLFLG (PLAY/DRAW macro table) | idle (S7 used $F92D-$F953) | STRPTR, INP_CURSOR, GFX_SFLAGS | (ii) |
| H11 MSX1 RS2IQ $FAF5-$FAF7, $FAF9-$FB01 | 3+9 | on the MSX1 VG-8020: the RS-232 receive queue (RS2IQ $FAF5, 64 B), idle without an RS-232 interface **(unverified)**; MSX2 names DPPAGE/ACPAGE/AVCSAV, CHRCNT/ROMA/MODE/reserved, XSAVE/YSAVE | idle (zerobas uses EXBRSA $FAF8 and DRVINF $FB21-$FB22 only) | GFX_DARG, DVLEN; PU_FMTD, GFX_DDX, DFN; GFX_DTMP, DSP | (ii) — ⚠️ an RS-232 cartridge's use of RS2IQ unknown. **$FB03-$FB34 deliberately NOT used** (MSX2/RS-232 BIOS work area RSTMP..LSTMOD, DRVINF table) |
| FUNACT $F7BA-$F7BB | 2 | FN nesting counter (evaluator internal) | idle: FN_PAREA_CEIL equ $F7BA is NOT-A-CELL (sysvars.inc:4432), the FN area's exclusive top (assert sysvars.inc:4460) | GFX_DDY | (ii) |
| DIMFLG $F662 | 1 | array-lookup flag | idle (TTYPOS $F661, VALTYP $F663) | GFX_SARGN | (ii) |
| FRCNEW $F3F5 | 1 | CLOAD/CLOAD? flag | idle | GFX_CPHASE | (ii) |
| CLMLST $F3B2 | 1 | PRINT comma column width (ini 14) | idle (zerobas's comma uses its own constant) | RDV_MODE | (ii) — ⚠️ a user-settable setting on the reference |
| H13 DAC tail $F7FE-$F805 | 8 | DAC+8..15 (the reference's extended-precision math scratch) | idle: zerobas's FAC = DAC 8 B; every FAC copy bounded to 8 (§1.1); sysvars.inc:4557 "nothing addressed FAC+8.." | tk_float scan: TKNZPOS, TKDCOUNT, TKSTORED, TKFLAGS, TKPC, TKLEAD, TKVALEND(2)=FOSIGCOUNT | (i)-ish, **T-only rule** |

Spare, verified idle, unused by this plan: NLONLY $F87C, FLBMEM $FCAE, FLKINP $F6A6, PTRFLG $F6A9 (4 singles).

**The T-only rule for the math tails (H5, H13).** zerobas implements the reference's USR protocol
(argument in DAC, sysvars.inc:4535), and DAC/ARG are the reference's math scratch, which USR code and hook
code may legally use. So only guests that are (a) transient within one operation and (b) make **no out-call**
(USR, BIOS, a hook) while live go there: tk_float calls only its own tkf_* helpers plus local
`upcase`/`cmp16_bits` clones (sysvars.inc:4611-4616); the float core is pure arithmetic; KEYARG is written
immediately before the keystr tenant call (basic/screen.asm:359/436/487, subromcall.asm:155) and read once
at the tenant's entry (sub/keystr.asm:162). NUMBUF was the classification's ARG-tail-adjacent choice and is
NOT T-only in this sense — `print_string` reads it while calling CHPUT (→ H.CHPU, user hooks) — so it went
to H4 instead. DRAW/CIRCLE/sprite/PRINT USING cells are live across expression evaluation (USR possible) and
are kept out of the math tails.

Page crossings: no multi-byte guest straddles a page (TKVALEND $F804-$F805, DTMP $FAFE-$FAFF, DSP
$FB00-$FB01; the single TK cells are reached only by name — sub/tkfloat.asm:125/130). None of the 63 names
appears in a `high`/`low`/`& $FF` idiom (ws_shift's own scan over basic/ sub/ sub2/ disk/); no `ld r,$Ex`
page literal names a guest's page (S6 lesson); every NUMBUF walker uses 16-bit `inc hl`/`inc de`/`sbc hl,de`
(spot-checked: detok.inc:430-530, print.asm:410-450, printusing.asm:322-392, strheap.asm:1918-1965 and
2232-2285).

### 1.3 Where this differs from wszero_classify.md's (a′) host map, and why

1. **GFX_X1/Y1 → ARG tail, X2/Y2 → MAXUPD (split): REJECTED.** `gfx_clamp_coords` walks X1,Y1,X2,Y2 as one
   8-B run (sub/graphics.asm:4327 `ld hl,GFX_X1 ; X1,Y1,X2,Y2 -- contiguous int16s`, `ld b,4`). Kept together.
2. **GFX_SOCT/SU14 → NTMSXP, EOCT/EU14 → DONUM (split): REJECTED.** `cpt_angle_defaults` zero-fills
   SOCT..EU14 as 8 B (sub/circleparse.asm:334). Kept together. (`gwp_raw`, sub/graphics.asm:1544, compares
   the two 4-B records through two pointers — either layout works for it.)
3. **MATH_N/MATH_SIGN/SQRT_K → DAC tail $F805 as 1 B: REJECTED, DROPPED.** MATH_N is a 2-B word spanning
   SQRT_K+SQRT_ITER (sysvars.inc:5070-5075; sub/fp_exp.asm:265 `ld (MATH_N),hl`): at $F805 it covers ARGA[0]
   $F806 while fp_exp/fp_log use ARGA. It also cannot leave SQRT_ITER. → S14 with the math frame.
4. **INP_CURSOR / GFX_CPHASE / PU_FMTD sharing one ARG-tail word; TK*/FP*/MUL*/KEYARG pairs sharing the DAC
   tail (TKVALEND, 2 B, overlapping KEYARG/MATH_N's byte):** replaced by exclusive bytes — sharing is not
   needed once FUNACT and the RS2IQ bytes are counted, and the DAC/ARG tails are USR-exposed.
5. **FILTAB/NULBUF ($F860-$F863): REJECTED as a host.** D-FCBSHAPE (TODO.md:20800, ruled 2026-09-27,
   AUTONOMOUS) writes the published FILTAB (docs/spec-fcbshape.md:15,43,92).
6. **MEMSIZ ($F672-$F673): REJECTED.** BASIC-visible, tracks CLEAR's ceiling on the reference
   (probes/basic/basic_probe_clear.py:105), a re-homing candidate.
7. **INTVAL ($FCA0, WSRC) and ONGSBF ($FBD8, GFX_DRESUME): AVOIDED.** S2 filed the faithful trap layout
   (INTVAL/INTCNT/ONGSBF at their own cells, a free-running INTCNT) as a later fidelity step.
8. **NUMBUF → PARM1 $F73E: impossible now** (S10 used $F71C-$F73F). NUMBUF → H4.
9. New hosts the classification did not list: FUNACT (its pubidle method took FN_PAREA_CEIL as a cell) and
   the MSX1 RS2IQ bytes $FAF5-$FAF7 / $FAF9-$FAFD (it excluded names any C-BIOS file mentions, e.g.
   DPPAGE/MODE, which are MSX2-only code).
10. Its "remaining idle singles" list included QUEBAK — **wrong today**: PLY_LASTDUR $F971 / PLY_BUFEND $F973
    live there (census.out).

## 2. The guests — users, lifetime, aliases removed

Lifetimes are the classification's T/Tx, re-checked at the writer sites below (the writer runs at the start of
the user, before any read; nothing reads a guest across a statement boundary). Since no host byte is
shared, the only nesting that matters is a user re-entering ITSELF, which S11 does not change (each cell keeps
its identity; only its address moves).

| group | names (bytes) | users / writer-before-reader (first sites) | life |
|---|---|---|---|
| DRAW + CIRCLE co-routine | DPTR 2, DEND 2, DCMD 2, DSUBN 1, DSUBI 1, DSUB 4, DSUBLEN 1, DREQ 1, DRESUME 1, DVAL 2, DVLEN 1, DFN 1, DARG 2, DDX 2, DDY 2, DTX 2, DTY 2, DTMP 2, DSP 2 (33) | DRAW: main ex_draw writes DRESUME (basic/graphics.asm:983); the tenant writes DSP at entry (`ld (GFX_DSP),sp`, sub/graphics.asm:2969), DSUBN (2979), DCMD/DFN per command (3016/3020); CIRCLE: ex_circle writes DPTR/DRESUME (basic/graphics.asm:614/616), circleparse writes DREQ (sub/circleparse.asm:47). GFX_DSUB is a 4-B array indexed ≤+3 (sub/graphics.asm:2994/3296) | Tx (across the resident's eval of a substitution / CIRCLE argument) |
| LINE endpoints | X1, Y1, X2, Y2 (8, contiguous) | LINE: ex_line_gfx / elg_from_grpac (basic/graphics.asm:200/219); CIRCLE spokes (sub/graphics.asm:1395); read by gfx_bres_init (740), gfx_clamp_coords (4327) | Tx (X1/Y1 across the second point's eval) |
| CIRCLE | SOCT, SU14, EOCT, EU14 (8, contiguous), CXC 2, CYC 2, R 2, ASPS 2, CPHASE 1 | circleparse: cpt_angle_defaults (circleparse.asm:334), cpt_after_r (93), cpt_defaults (322), the resident cp_req_coord (basic/graphics.asm:637); CPHASE at circleparse_tenant (45) | Tx |
| sprites / SCREEN | SN 2, VLEN 1, SDESC 2, SC 2, SPATN 2, SSIZE 1, SARGN 1, SFLAGS 1 | SPRITE$ fn (spr_parse_index 1182 / gfx_spr_rpat 3904), SPRITE$= (spr_assign 1133), PUT SPRITE (ex_put_sprite 1325/1327, pspr_* 1347-1367), SCREEN (ex_screen writes SARGN, basic/screen.asm:45; spr_mode_save writes SSIZE, graphics.asm:1223) | Tx |
| G8 | G8N 2, G8V 2 | VDP()=/BASE()= (g8_assign 1509/1518), VDP()/BASE() fn (g8_fn 1413) | Tx / T |
| READ / lvalue | RDV_MODE 1, TGT_ADDR 2 | exr_lp writes RDV_MODE (basic/program.asm:2324); tgt_parse / let_ref write TGT_ADDR (str-engine.asm:197), NEXT reads TGT_ADDR+1 after its own tgt_parse (program.asm:2140) | T / Tx |
| strings / INPUT / PRINT USING | STRPTR 2, INP_CURSOR 2, PU_FMTD 2 | str_eval sets STRPTR, callers read it after (~60 sites, also disk.rom via the generated ABI); inp_readline writes INP_CURSOR (input.asm:250) before linebuf_getbyte reads it — ARL_GETBYTE is re-set before every read (S10); phf_set writes PU_FMTD (printusing.asm:226) | Tx |
| number formatting | NUMBUF 8 | PRINT pn_conv, LIST, HEX$/OCT$ (sh_hex_build/sh_oct_build), PRINT USING pu_fmt_int, detok — each writes then consumes it in one call; extent ≤ 8 incl. the terminator on every path read **(spot-checked, not exhaustive)** | T |
| tk_float | TKNZPOS, TKDCOUNT, TKSTORED, TKFLAGS, TKPC, TKLEAD (6), TKVALEND 2 = FOSIGCOUNT | zeroed at tk_float entry (sub/tkfloat.asm:45-53), TKPC/TKLEAD written before read (149/736/787); TKVALEND set by tokenise (tokenise.inc:41) or VAL (strheap.asm:2751), read by tk_float and by INPUT right after its VAL parse (input.asm:385); FOSIGCOUNT written by flt_out (float.asm:102) — the alias is KEPT (both move together) | T |
| float core + KEY | WSRC 2, FP_LHSVAL 2, FP_TMP_B 2, FP_RSIGN 1, MUL_ADIG 1, MUL_CARRY 1, KEYARG 1 | float-arith.asm (wsrc_go 1452, fpd_go 1084, raf_noround 510, signed_div/mod, fp_mul/fp_div) — within one op; KEYARG as in §1.2 | T |

**Aliases removed, and nothing relies on them:** INP_CURSOR≡NUMBUF (INP_CURSOR written by inp_readline
before any read; the split also removes a latent hazard — HEX$/OCT$ write NUMBUF and could run inside
INPUT's target parse, e.g. `INPUT A(LEN(HEX$(255)))`, **(unverified whether INPUT parses targets after
reading the line)**); KEYARG≡WIDIG[0] (KEYARG written before each tenant call); GFX_PPITCH≡GFX_G8N (PAINT
writes PPITCH in gpp_pitch_set, sub/graphics.asm:2314, before its seven readers); CPHASE over GFX_WE_P's
high byte (today's `GFX_WE_P overruns` pin — parse-time vs draw-time, **unverified** benign today, gone after
S11); the sprite cells inside GFX_PSTK's 44-B declared span.

**Interrupt-time readers: none** (§1.1). The KEY-bar repaint (`zb_chsns`, basic/islands.asm:330) is NOT
interrupt-time — it runs from CHSNS call sites incl. INKEY$ — and writes only KEYARG (exclusive byte) and the
detok cells (not moved).

**Dropped / deferred (cannot be housed exclusively, or must not move):** MATH_N/MATH_SIGN/SQRT_K (§1.3.3);
DB_SKIP, DB_RESSKIP, DB_SP, DT_TOK, DT_TOKN, DB_RESPTR (12 B — the detok render state DB_WIN's KEY-bar
coupling drags along; with DB_WIN in S14); RVDESC (3 B, `ldir` unit at str-engine.asm:191 / vars.asm:411 —
S12). Optional later homes: the 4 spare singles; $FB29-$FB34 (12 B between the DRVINF table and PRSCNT,
**provenance unverified** — not used).

## 3. The edit

### 3.1 basic/sysvars.inc — 63 moves + 4 re-anchors (exact lines: `s11_replacements.md`)

Rule: **every moved name becomes an absolute literal; every stay-name that derived from a moved name gets
its current address as a literal.** Keep each line's own width declaration; rewrite a leading `; $XXXX:`
annotation to the new address (wall-literal-check rule B compares it with the build).

| name | sysvars.inc | old expr | old | new | host |
|---|---|---|---|---|---|
| GFX_DPTR | 2206 | GFX_SFLAGS + 1 | $ED34 | $FC8A | H3 |
| GFX_DEND | 2207 | GFX_DPTR + 2 | $ED36 | $FC8C | H3 |
| GFX_DCMD | 2215 | GFX_DFSTK + 4*GFX_DFCAP | $ED59 | $FC8E | H3 |
| GFX_DSUBN | 2217 | GFX_DCMD + 2 | $ED5B | $FC90 | H3 |
| GFX_DSUBI | 2218 | GFX_DSUBN + 1 | $ED5C | $FC91 | H3 |
| GFX_DSUB | 2219 | GFX_DSUBI + 1 | $ED5D | $FC92 (4) | H3 |
| GFX_DSUBLEN | 2220 | GFX_DSUB + 4 | $ED61 | $FC96 | H3 |
| GFX_DREQ | 2221 | GFX_DSUBLEN + 1 | $ED62 | $FC97 | H3 |
| GFX_DRESUME | 2223 | GFX_DREQ + 1 | $ED63 | $FC98 | H3 |
| GFX_DVAL | 2224 | GFX_DRESUME + 1 | $ED64 | $FC99 (2) | H3 (+RTYCNT) |
| NUMBUF | 914 | $EF2D | $EF2D | $F408 (8) | H4 |
| GFX_DTX | 2238 | GFX_DDY + 2 | $ED87 | $F410 | H4 |
| GFX_DTY | 2239 | GFX_DTX + 2 | $ED89 | $F412 | H4 |
| GFX_DARG | 2235 | GFX_DFN + 1 | $ED81 | $FAF5 | H11 |
| GFX_DVLEN | 2225 | GFX_DVAL + 2 | $ED66 | $FAF7 | H11 |
| PU_FMTD | 3943 | $F08B | $F08B | $FAF9 | H11 |
| GFX_DDX | 2236 | GFX_DARG + 2 | $ED83 | $FAFB | H11 |
| GFX_DFN | 2233 | $ED80 | $ED80 | $FAFD | H11 |
| GFX_DTMP | 2240 | GFX_DTY + 2 | $ED8B | $FAFE | H11 (XSAVE) |
| GFX_DSP | 2241 | GFX_DTMP + 2 | $ED8D | $FB00 | H11 (YSAVE) |
| GFX_DDY | 2237 | GFX_DDX + 2 | $ED85 | $F7BA | FUNACT |
| GFX_X1 / Y1 / X2 / Y2 | 709-712 | $EF67/69/6B/6D | | $F70A / $F70C / $F70E / $F710 | H1 |
| GFX_SOCT / SU14 / EOCT / EU14 | 774, 777-779 | $EFB3/B5/B7/B9 | | $F740 / $F742 / $F744 / $F746 | H2 |
| GFX_CXC / CYC | 737, 738 | $EF8D / $EF8F | | $F748 / $F74A | H2 |
| GFX_R / ASPS | 739, 741 | $EF91 / $EF94 | | $F66E / $F670 | H7 |
| GFX_SN | 2257 | GFX_VBUF + 32 | $ED28 | $F3EC | H6 |
| GFX_SDESC | 2259 | GFX_VLEN + 1 | $ED2B | $F3EE | H6 |
| GFX_SC | 2261 | GFX_SDESC + 2 | $ED2D | $F3F0 | H6 |
| GFX_SPATN | 2265 | GFX_SC + 2 | $ED2F | $F417 | H8 |
| GFX_G8N | 2380 | $ED99 | $ED99 | $F419 | H8 |
| GFX_VLEN | 2258 | GFX_SN + 2 | $ED2A | $F41B | H8 |
| GFX_G8V | 2382 | GFX_G8N + 2 | $ED9B | $F665 | H9 |
| TGT_ADDR | 2338 | RDV_MODE + 1 | $ED95 | $F667 | H9 |
| GFX_SSIZE | 2266 | GFX_SPATN + 2 | $ED31 | $F669 | H9 |
| STRPTR | 1747 | $EF36 | $EF36 | $F954 | H10 |
| INP_CURSOR | 939 | NUMBUF | $EF2D | $F956 (2) | H10 |
| GFX_SFLAGS | 2270 | GFX_SARGN + 1 | $ED33 | $F958 | H10 |
| GFX_SARGN | 2268 | GFX_SSIZE + 1 | $ED32 | $F662 | DIMFLG |
| GFX_CPHASE | 816 | $EFBE | $EFBE | $F3F5 | FRCNEW |
| RDV_MODE | 2316 | RDV_ST + 1 | $ED94 | $F3B2 | CLMLST |
| TKNZPOS, TKDCOUNT, TKSTORED, TKFLAGS | 4589-4592 | $F0C6..$F0C9 | | $F7FE, $F7FF, $F800, $F801 | H13 |
| TKPC / TKLEAD | 4596 / 4598 | $F0CE / $F0D1 | | $F802 / $F803 | H13 |
| TKVALEND / FOSIGCOUNT | 4634 / 4638 | $F0D3 | | $F804 (alias kept) | H13 |
| WSRC | 4734 | $F119 | | $F84D | H5 |
| FP_LHSVAL / FP_TMP_B / FP_RSIGN | 4710 / 4712 / 4714 | $F102 / $F104 / $F106 | | $F84F / $F851 / $F853 | H5 |
| MUL_ADIG / MUL_CARRY | 4725 / 4726 | $F10D / $F10E | | $F854 / $F855 | H5 |
| KEYARG | 4715 | $F107 (alias of WIDIG) | | $F856 | H5 |
| **re-anchor** GFX_DFTOP | 2208 | GFX_DEND + 2 | $ED38 | `$ED38` | stays (S14) |
| **re-anchor** GFX_DEXP | 2226 | GFX_DVLEN + 1 | $ED67 | `$ED67` | stays (S12) |
| **re-anchor** DEFT_PTR | 2297 | GFX_DSP + 2 | $ED8F | `$ED8F` (RDV_VAL/RDV_ST/RDV_LINE follow it unchanged) | stays (S12) |
| **re-anchor** GFX_PPITCH | 2401 | GFX_G8N | $ED99 | `$ED99` **and add the width `(1)`** to its line | stays (S12) |

Untouched on purpose: GFX_DFSTK (= GFX_DFTOP + 1, follows), GFX_VBUF/GFX_CS_M1 (= GFX_PSTK), WIDIG $F107,
WSRC_TYP $F11B, RDV_VAL/RDV_ST/RDV_LINE, GFX_DFB/DSCALE/DANGLE (S8).

### 3.2 Dry run (`sim.py` → `sim.out`)

All 63 names resolve to their targets (basic; disk's generated STRPTR mirror too); **every other name in
both components is unchanged**; **NEW overlaps: 0** (basic 19 → 11 pairs: the eight sprite-in-PSTK pairs
disappear); window bytes covered 953 → 873 (+4 is WIDIG gaining its declared width once KEYARG leaves).

### 3.3 Everything else the edit must touch (each verified to be needed)

1. **Assert that will FIRE** — sysvars.inc:2405 `IF GFX_G8V + 2 > BASIC_WS_CEIL` ($F667 > $EDFD): delete,
   or replace by a host-fit guard. sysvars.inc:2402 `IF TGT_ADDR + 2 > GFX_DSCALE` becomes vacuous ($F669 vs
   $FCBC): delete. **Suggested 0-ROM replacements** (one per host, assembler-time): `GFX_DVAL+2 > $FC9B`
   (INTFLG), `GFX_DTY+2 > ERRFLG`, `GFX_DSP+2 > $FB02`, `GFX_Y2+2 > CSP`, `GFX_CYC+2 > FN_BASE`,
   `GFX_ASPS+2 > $F672` (MEMSIZ), `GFX_SC+2 > ATRBYT`, `GFX_VLEN+1 > $F41C` (CURLIN), `GFX_SSIZE+1 > POOLSIZE`,
   `GFX_SFLAGS+1 > $F959` (QUETAB), `KEYARG+1 > RNDX`, `TKVALEND+2 > ARGA`, `GFX_DDY+2 > SW_ADDR`.
2. **FREE-RAM claims that become false** (ram-claim-check fails on a name inside one): sysvars.inc:4156
   `; FREE-RAM $F70A..$F712` and sysvars.inc:4278 `; FREE-RAM $F740..$F74C` → rewrite as history
   (`; WAS FREE-RAM … — D-WSZERO S11: LINE endpoints / CIRCLE records`), like sysvars.inc:1435.
3. **tools/ram-width-allow.txt** — dry-run ratchet: 5 pins go stale (delete, the good direction):
   `basic FOSIGCOUNT/TKVALEND disputed`, `basic GFX_CPHASE overruns`, `basic GFX_WE_P overruns`,
   `basic INP_CURSOR/NUMBUF disputed`, `basic KEYARG/WIDIG disputed`; and 1 NEW widthless cell,
   `GFX_PPITCH` — fixed by the `(1)` in §3.1 (not by a pin).
4. **docs/ram-map.md** is generated and checked: `make ram-map-doc` after the edit.
5. **disk/basic-resident-abi.inc** (generated, committed) gets STRPTR $F954 from the build; disk.rom, sub,
   sub2 images change (operands only). S7 lesson: a stale mirror broke a planner run — build once before any
   verifier that reads disk sources.
6. **Prose the move falsifies** ([[a-fix-falsifies-the-justification-beside-it]]): INP_CURSOR's block
   (sysvars.inc:933-939, "Aliases NUMBUF … dead during INPUT"); KEYARG's "ALIASES WIDIG below" (4715-4719)
   and **basic/screen.asm:412-416** ("NOT into KEYARG yet: it aliases WIDIG …" — the push stays harmless,
   the reason is gone); GFX_PPITCH's "It ALIASES G8's index cell" (2383-2400); G8's "Below BASIC_WS_CEIL,
   which the guard below enforces" (2378-2379); the sprite block's "ALIASES the PAINT span stack" now true
   only of GFX_VBUF (2247-2251); TGT_ADDR/RDV_* "Same window" arguments (2300-2337); the G3/G4 window
   comments (700-830) and the `-> ends $E54F`-style trailers.
7. **tools/check_wall_literals.py --selftest** anchors its rule-B plant on the exact line
   `GFX_SPATN equ GFX_SC + 2 ; $XXXX:` (tools/check_wall_literals.py:242) — after S11 that line is a literal,
   the plant reports "anchor not unique" and the SELFTEST fails (the gate `wall-literal-check` itself does
   not run the selftest). Re-anchor the plant on a surviving chained row, e.g. `GFX_DFSTK equ GFX_DFTOP + 1
   ; $ED39:` or `RDV_VAL equ DEFT_PTR + 2 ; $ED91:`.
8. **Tests/probes**: no test or probe hard-codes a guest's OLD address (grep of 0xED../0xEF../0xF0../0xF1..
   in tests/ probes/ tools/: only `VALTYP_OLD 0xEF35` in the wszero probe and unrelated ceilings); they read
   names from the syms (test_graphics `m.addr("GFX_SOCT")`, test_input `s["INP_CURSOR"]`, test_printusing
   `m.sym["NUMBUF"]` — poisons exactly 8 B; its comment "$E0C0..$E0C7 — STRPTR/PRDEST live" is stale prose).
   Harness geometry: tests/msxtest.py keeps its stack at $F380 and shuttles [$F380,$10000) back from tenant
   islands (msxtest.py:233-255), so all new homes round-trip; test_play_parse zero-fills $F800-$FBFF before a
   PLAY parse (harmless seeding); test_tokenise's 900-B TOKBUF scan ($F41F-$F7A2) contains no cell the crunch
   writes after S11 (TK* moved to $F7FE+). **(unverified by running.)**
9. **TSV_NAME is 6 B, declared 1** (s9_plan.md §1.6; files.asm:981 `ld bc,6 ; ldir` into $EF62-$EF67).
   GFX_X1's old home $EF67 is TSV_NAME's 6th byte: after S11 ram_map will show $EF64-$EF67 as holes that are
   NOT free. Recommended in S11 (comment-only): declare TSV_NAME's extent as an explicit range
   `$EF62..$EF67` (a range is exempt from overrun demotion) — verify with ram-map-check.
10. sysvarsweep is a coverage report (exit ≠ 0 only on apparatus failure): its EXTRA count will rise in
    the states that crunch or print numbers (TK*, NUMBUF, the float core now write published bytes);
    docs/sysvar-msx1-coverage.md figures drift — doc debt, **magnitude unmeasured**. (Noticed in passing,
    not S11's: its CONTROL_PRIV pins CTLLIM at $E056, a pre-S3 address — basic_probe_sysvarsweep.py:253.)

## 4. Witness

**Why no existing row can witness S11.** Every moved cell is transient: written by its user before it is read,
so a load over its old home before the user runs is harmless today — which is why `rich`, `rich2`, `persist`,
`input` are already SAME. The defect S11 removes shows only after S15 (the window becomes program RAM and the
users would WRITE the program's bytes). So the witness is: (a) a STATIC census, (b) rows that prove the old
homes **go quiet** — the C-VACATED idea of sysvarsweep, applied to the window.

(a) **Static census**: after the build, no S11 name has a value in [TXTMAX_NODISK, $F380) in any of the four
syms (`census.py` with the host list swapped for the window, or S9b's planned `ram_map --floor-top F380`).

(b) **New wszero-acceptance rows — "vacated bytes stay $A5"**. Each: `CLEAR 100,&HE000`, BLOAD the $A5 fill
over the whole window (as `all`), run the users, then `SCREEN 0` and print the SUM of PEEKs over the
**S11-freed list** (hard-coded in the probe like sysvarsweep's VACATED; `freed.py` output, **minus $EF67** —
TSV_NAME's tail): `$ED34-$ED37, $ED59-$ED66, $ED80-$ED8E, $ED94-$ED96, $ED9A-$ED9C, $EF2D-$EF34,
$EF36-$EF37, $EF68-$EF6E, $EF8D-$EF92, $EF94-$EF95, $EFB3-$EFBA, $F08B-$F08C, $F0C6-$F0C9, $F0CE, $F0D1,
$F0D3-$F0D4, $F102-$F106, $F10D-$F10E, $F119-$F11A` (91 B → 165·91 = 15015 on the VG-8020, whose window
is untouched under `CLEAR …,&HE000`). Users chosen so every moved name is written:
* `s11gfx`: `SCREEN 2,2` (SARGN, SSIZE); `SPRITE$(0)=STRING$(32,255):A$=SPRITE$(0)` (SDESC, SN, VLEN);
  `PUT SPRITE 0,(60,60),15,0` (SN, SC, SPATN, SFLAGS); `VDP(7)=VDP(7)` (G8N, G8V); `LINE(10,10)-(60,40),15,B:
  LINE-(80,80),15` (X1..Y2); `CIRCLE(128,96),40,15,-.5,-2.5,1.4` (CXC, CYC, R, SOCT..EU14, ASPS, CPHASE,
  spokes → X1..Y2, DPTR/DREQ/DRESUME/DVAL); `B$="D3":K=4:DRAW"BM100,100S8A1NR10C15U5XB$;R=K;"` (all 19 DRAW
  cells incl. DSUB/DSUBLEN/DVLEN/DFN/DTMP/DSP).
* `s11num`: `READ X(1),B$` with DATA (RDV_MODE, TGT_ADDR); `A%=7\2:B%=-7 MOD 3` (FP_RSIGN); `C#=1#/3#`
  (fp_div: FP_LHSVAL, MUL_CARRY, FP_TMP_B); `D=1.5*2.25` (MUL_ADIG); `E=A%+1.5` (WSRC); `V=VAL("12.5E1")`
  (TK*, TKVALEND); `PRINT 1/3;123;HEX$(255);OCT$(8)` (FOSIGCOUNT, NUMBUF); `PRINT USING"##.##";V` (PU_FMTD);
  `KEY 1,"AB"` (KEYARG); string ops (STRPTR).
* `s11inp`: as `input` (typed `42` after `@WAIT40`), `INPUT A(1)` (INP_CURSOR, TK*/TKVALEND, TGT_ADDR).
* 🔮 **Predictions**: on the S9/S10 build all three DIVERGE (ZB's sum ≠ 15015, the users write the old
  homes); after S11 all three SAME. Run time: the gfx row is the long one — keep under the 40 s run gap
  (S8's POINT-scan lesson); **(unverified)**.

(c) **Knives** (one group back at its old home per knife, everything else moved; each build pin-checked):
K-WS29 DRAW 19 → `s11gfx`; K-WS30 X1..Y2 → `s11gfx`; K-WS31 CIRCLE 11 → `s11gfx`; K-WS32 sprite + G8 +
SARGN/SSIZE → `s11gfx`; K-WS33 TK*/TKVALEND/FOSIGCOUNT → `s11num` + `s11inp`; K-WS34 float core + KEYARG →
`s11num`; K-WS35 NUMBUF + INP_CURSOR (alias restored) → `s11num` + `s11inp`; K-WS36 STRPTR/TGT_ADDR/RDV_MODE/
PU_FMTD → `s11num` (+ `s11inp`). Each predicted to diverge exactly its row(s). Predicted BLIND if a user
does not run: WSRC needs a mixed int/float op that widens through widen_fac_to (`E=A%+1.5` — **unverified it
reaches wsrc_go**). A knife cannot show a crash — only the vacated-sum.

(d) **Regression rows already exercising the users after a full-window load** (they must stay SAME on the
new homes): `rich` (CIRCLE without angles → CXC/CYC/R/ASPS/CPHASE/SOCT..EU14 via cpt_angle_defaults, DPTR/
DREQ/DRESUME/DVAL; READ → RDV_MODE/TGT_ADDR; PRINT USING → PU_FMTD; PRINT ints → NUMBUF; FN float math →
float core; strings → STRPTR); `rich2` (VAL(STR$(12)) → TK*/TKVALEND/NUMBUF; SQR/SIN/RND; MID$/INSTR/SWAP);
`persist` (DRAW without substitutions, PSET); `input` (INPUT); `chan`, `valtyp` (PRINT). **No row today runs**:
sprites/PUT SPRITE/SCREEN n,size, VDP()=, DRAW substitutions and N/B prefixes, CIRCLE angles + spokes,
LINE, KEY n,"…", HEX$/OCT$, `\`/MOD, double division — the three new rows cover them. Also run the full
battery once (graphics-acceptance, subrom/sub2-acceptance, diskbasic-acceptance — STRPTR's ABI —,
nodisk-acceptance, unit tests, ram-map-check, ram-claim-check, wall-literal-check).

## 5. Sizes, and what remains in the window

* **Moved: 63 names, 109 B at the new homes; 107 B of old homes, of which 92 B are freed** (15 stay covered:
  GFX_PSTK $ED28-$ED33, GFX_PPITCH $ED99, GFX_WE_P $EFBE, WIDIG $F107). Host bytes used: 109 of the 113
  verified idle (4 singles spare). The ceiling does not move (the 10-14 lesson; S15 moves it once).
* **Left in $ECF8-$F194 after S11 (≈ 907 B of declared cells; `remain.out`, aliases counted once)**:

| next slice | bytes | what |
|---|---|---|
| S12 overlays (diskless, transient) | **340** | GFX_PSTK 44 (PAINT span stack, incl. GFX_VBUF/CS_M1/M2), PU_NUM 32, PU_DIG 32, GFX_DEXP 24, TKDIG 24 + TK rest (TKPOS/INTLEN/HAVESIG/EXP/EXPD/EXPSIGN/DEXP/SRCSAVE/OVF/LNUM ≈ 12), DIVREM 15, LHS_FAC/FACTYP 9, WIDIG 5 + MUL_I/MUL_PP/MULCAND/MULTPLR/MUL32/FP_SHIFTAMT/FP_OPMODE ≈ 13, LINE Bresenham internals GFX_MODE..YSTEP ≈ 28, CIRCLE wedge/octant scratch ≈ 36, PAINT singles ≈ 14, RL_* 7, DEFT_PTR/RDV_* 5, GFX_PPITCH 1, ISRCH 4, MIDS_DEST 2, RN/CLR/MRG/PLN/LOC/SV/OO/TSV/FMT/FILES/PLY_XSP/PLF_RA*/VS_*/MC_TYPE… |
| S14 code | **≈ 219** | DB_WIN 96, GFX_DFTOP+DFSTK 33, FOR_CUR..FOR_LINE 29, CVT 18, HORNER_G 18, MATH_A 18 (both widths undeclared in the map), + singles PU_COMMAS, PU_DEC, CVT_MODE, VARTYPE, MATH_N/SQRT_K 2, MATH_BREAK |
| S13 risky homes (SLTWRK/PROCNM, Joost's call) | 40 | SH_* string-engine ABI ≈ 17, PU_FMTLEN..PU_FLAGS 5, GFX_MODE/ASPMAJ/ARCF/SNEG/ENEG, DB_MORE/DB_RESUME/DB_CUR, WSRC_TYP, PRDEST/PRDEV, ERRMARK, INDLR_N, FCH_RDMODE, AUDIO_VMASK… |
| deferred from S11 | 15 | DB_SKIP, DB_RESSKIP, DB_SP, DT_TOK, DT_TOKN, DB_RESPTR (12; with DB_WIN), RVDESC 3 (S12) |
| stays below $F380 | 285 + 8 | disk-only 186 (FAT engine, FCH_RECLENS/RECNOS 64, COPY_*, DISK_FCB…) + Dfix 99 (FLD_TAB 96 …, made disk-only by S9); boot-only SCAN_* 6; dead/probe-only 2 |

So the diskless-used remainder that must still leave before S15 is ≈ 340 + 219 + 40 + 15 ≈ **614 B**
(S12's 340 needs per-pair overlay proofs; S14's ≈ 219 needs ROM).
