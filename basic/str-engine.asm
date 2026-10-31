; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; str-engine.asm — the string expression engine (repack build only).
; ===========================================================================
; This file is assembled into the reclaimed page-0 low region ($2812-$3FFF). The
; minimal string-VALUE layer it builds on is basic/strvar.asm.
; See docs/spec-basic-arrays-slice4a-string-heap.md and basic/PROVENANCE.md.
;
; REVISED arrays slice-4a (docs/spec-basic-arrays-slice4a-string-heap.md):
; every string descriptor everywhere is now a uniform 3-byte [len:1][ptr:2]
; triple; `ptr` -> a body in the string HEAP (a compacting allocator in the
; sub-ROM tenant, sub/strheap.asm) OR somewhere stable outside it (a token-
; stream literal, STRSCR, STR_EMPTY, a channel's record for a FIELDed variable
; -- D-FLDDESC, 2026-10-17; FLD_DESC until then). The old fixed N=3 STRTMP ring
; + STRCAT_R global accumulator are GONE, replaced by a temp-descriptor STACK
; (§6) whose entries own real heap bodies; the concat spine (§7) evaluates
; every operand into an owned temp BEFORE allocating the final result once,
; which structurally eliminates the STRCAT_R re-entrancy bug (retiring
; spec-basic-string-concat-nesting-fix.md).
;
; Clean-room: original code. Concatenation SEMANTICS (left-to-right,
; truncate the combined length) are from the public MSX-BASIC language
; reference; the temp-descriptor stack, the heap descriptor layout, and the
; GC are zerobas's own design (sub/strheap.asm's own header has the full
; provenance/deviation notes). No disassembly.
; ===========================================================================

; ===========================================================================
; String-heap glue (main-ROM side, spec §9/§10): the thin wrapper around the
; SUBROM_IDX_STRHEAP tenant (heap_alloc/GC live there, sub/strheap.asm) plus
; the temp-descriptor stack (§6) built on top of it. Every string-producing
; routine below (concat, the S4 functions) is built on str_temp_alloc /
; str_snapshot_to_temp.
; ===========================================================================

; ixsp_paren_req (D-PAIRCARVE2, basic/expr.asm) -- `(` is REQUIRED: Z returns as
; the open-coded pair did; NZ discards this helper's own return address and jumps
; to ev_f_empty, whose deferred error returns ONE FRAME FURTHER OUT. 💰 MOVED HERE
; 2026-09-30 by D-INPQUOTE: page 1 was 7 B short and this region had 9 B spare;
; the two share one budget, and a low-region routine is visible to every caller.
ixsp_paren_req:
                call    ixsp_paren
ixsp_unwind:                                ; C4 shared tail (2026-10-03): expr.asm's
                ret     z                   ; evsp_close jumps here after its `cp ')'`
                inc     sp                  ; -- same frame discard, same deferred
                inc     sp                  ; error, one copy (low: visible to both)
                jp      ev_f_empty

; (arga_dig_iszero lives in basic/float-arith.asm, past the $3297 pin, since
; D-EVALSLOPE's typed-frame step: its 6 B make room for pop_lhs_and_probe's growth
; in front of that pin, basic/input.asm -- tools/pin_plan.py's exact fill.)

; --- sh_go: run string-heap op A on a Z80-STACK PARAMETER BLOCK (D-WSZERO S16) --
; The tenant's arguments and results used to live in an 18-byte RAM block
; (SH_OP..SH_ERR) inside the memory a diskless program owns. The reference keeps
; no such block -- its string engine passes its operands in registers and on the
; stack -- so zerobas's goes on the stack too, for the length of one op:
;   in : A = the op; HL / DE / BC = the three argument words (per op: the block
;        layout and each op's slots are at sub/strheap.asm's SHB_* equates), L =
;        the length for the ops that take one. Ops 5 and 9 also take a 4th word
;        (START / COUNT) that the caller pushes right before `call sh_go`.
;   out: A = the ERR slot (or CMP's bits), Z iff 0, CF = 0; HL / DE / BC = the
;        three words as the tenant left them -- its results, or the caller's own
;        values where the op writes none (so an op that writes no BC keeps it).
; The block is pushed here, its address rides to the tenant in HL (subrom_call
; and CALSLT pass HL), and the tenant addresses it through IY. Clobbers IX, IY.
; Raises (sc_call) only if the sub ROM is absent.
; 🧭 D-DEEPEXPR (2026-10-20): every EXPRESSION-time op now enters through
; `sh_go_g` (basic/main.asm, at the low region's end past the $3297 pin), which
; tests the stack first and on a refusal publishes only STR_EMPTY / DE = 0. The
; raw entry here keeps its statement-time users, whose depth STK_EDGE_RESERVE
; covers: MID$()= and mid_own, INPUT's inp_val, ctl_reset, fch_ctx_addr's
; statement callers.
sh_go:
                push    bc                  ; blk+6
                push    de                  ; blk+4
                push    hl                  ; blk+2
                ld      h,a
                push    hl                  ; blk+0 = L, blk+1 = the op
                ld      hl,0
                add     hl,sp               ; HL = the block
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_STRHEAP
                call    sc_call
                pop     af                  ; A = blk+1: ERR (the tenant overwrote the op)
                pop     hl
                pop     de
                pop     bc
                or      a                   ; Z iff ERR = 0, CF = 0
                ret

; --- ctl_alloc / ctl_reset: the CONTROL POOL's two main-ROM entry points ----
; D-CTLPOOL (docs/spec-basic-trapsvc.md §11-§16). Both are thin wrappers over
; the strheap tenant, which is where the collision floor lives (ARYEND+2 is
; found by walking the array chain -- sub-ROM knowledge). They sit HERE, beside
; `call_strheap`, for the same reason the other thirteen wrappers do: the tenant
; dispatch is one shared tail and main page 1 has no room to inline it three
; times.
;
;   ctl_alloc   IN  HL = frame size.  OUT  CF=0 -> HL = the frame's base (CSP
;               already advanced).  CF=1 -> pool full, NOTHING written; the
;               caller raises ERR 7 through gosub_stk_over. Clobbers DE.
;               🔴 IT TOUCHES NO SLOT. Every push goes through here and
;               `FOR I=1 TO 1000:GOSUB 100:NEXT` pushes a thousand times, so the
;               collision floor is READ from CTLLIM rather than derived -- the
;               sub ROM keeps that cell current (strheap_ctllim).
;               🎯 ONE CHECK REPLACING THREE -- the GOSUB_DEPTH, FOR_DEPTH and
;               TRAPSTK_MAX bound tests are all gone; "the frame collided with
;               the variable area" is now the only way to be full.
;   ctl_reset   empties the pool and re-derives CTLTOP. Called from clear_vars
;               only (cold boot / RUN / NEW / CLEAR).
;
; Clobbers A, IX (call_strheap's) plus DE.
ctl_alloc:
                ex      de,hl               ; DE = the frame size
                ld      hl,(CSP)
                or      a
                sbc     hl,de               ; HL = the frame's base
                ret     c                   ; CSP wrapped -> refuse, CF=1 (an
                                            ; uninitialised pool, CSP=0, cannot push)
                ld      bc,(CTLLIM)         ; the variable region's first free byte
                ; 🔴 AND THE FLOOR NEEDS A MARGIN NOW THAT `SP` IS IN HERE. Before the
                ; merge the only thing below the frontier was nothing at all, so
                ; `base >= CTLLIM` was the whole test. Now the MACHINE STACK lives
                ; below it: the evaluator descends from `CSP` on every expression, so
                ; a frontier resting exactly on `CTLLIM` puts the next expression
                ; INSIDE the arrays.
                ; MEASURED without this (ctllim-acceptance): `l.ary` drove the pool to
                ; 2515 frames and reported 18 CORRUPTED CELLS, and `l.ctl`/`l.scal`
                ; printed NOTHING AT ALL -- the stack had reached the interpreter's own
                ; state and taken the machine with it. The suite read that as "CTLLIM
                ; stale-LOW", which is what this corruption looks like from outside;
                ; the floor is correct and the reservation was missing.
                ; The margin is folded into the floor: BC = CTLLIM + CTL_FRAME_MARGIN
                ; (D-STACKFLOOR: a frame's own margin, bigger than DIM's, sysvars.inc),
                ; one page, so `inc b`. No wrap: CTLLIM < $FF00 whenever CSP is live
                ; (sh_ctl_reset writes both; CSP = 0 refuses at the `ret c` above).
    IF CTL_FRAME_MARGIN != 256
                db      CTL_ALLOC_INC_B_ASSUMES_A_ONE_PAGE_MARGIN
    ENDIF
                inc     b
                sbc     hl,bc               ; (CF is clear from the ret above)
                ret     c                   ; base < floor + margin -> pool full, CF=1
                add     hl,bc               ; HL = the base again. `add` back rather
                                            ; than push/pop -- the relocation this
                                            ; tail-jumps to moves the stack out from
                                            ; under itself, so nothing of ours may be
                                            ; sitting on it.
                ld      (CSP),hl            ; the frontier IS the frame's base
                jp      ctl_reloc           ; -> main page 1, which has the room; a
                                            ; TAIL jump, so its `ret` goes to OUR
                                            ; caller and no extra word rides the stack
; --- pdf_badname: a structurally malformed 8.3 filename -> ERR 56 ----------
; D-FSPEC. `parse_disk_fcb` used `jp bl_load_error` here, and load_error PRINTS
; AND RETURNS -- from inside the parser, so the `ret` landed in the CALLER and
; do_files walked the directory anyway, printing TWO messages. Both references
; RAISE `Bad file name` and stop, uniformly across KILL/LOAD/SAVE/OPEN/FILES.
; 🟢 The message already ships (sub/errmsg.asm em_bad_filename; err_msgtab[56] is
; the err_subhosted marker), so this is five bytes and no new string.
; ⚠️ SITED IN THE LOW REGION ON PURPOSE. `parse_disk_fcb` lives in main page 1,
; the scarcer of the two co-mapped walls (6 B free vs 14 on 2026-09-04); a
; five-byte leaf should not spend page-1 space it cannot spare.
pdf_badname:
                ld      a,56
                jp      raise_error
; desc_in_text -- D-LITREF (2026-10-07): Z iff the descriptor at HL has a length
; and its bytes lie below VARTAB -- the program text, the only body with a length
; that lives there (mid_own below uses the same rule). On the VG-8020 such a
; string costs the string space nothing when it is assigned: a program literal,
; or a variable that already points at the text (`copyvar`: READ B$ : A$=B$ reads
; FRE 200) -- the rule is WHERE the bytes are, not what kind of operand it was.
;   in: HL = a descriptor. Clobbers A, DE, HL.
desc_in_text:
                ld      a,(hl)
                or      a
                jr      z,dit_no            ; "" is never stored by reference
                inc     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = the body
                ld      hl,(VARTAB)
                scf
                sbc     hl,de               ; CF iff body >= VARTAB
                jr      c,dit_no
                xor     a                   ; Z: the program text
                ret
dit_no:
                or      1                   ; NZ
                ret

; --- let_ref: a scalar string LET's whole store (D-LITREF, D-LETNEWFIRST) -----
; in:  HL = the target's ENTRY (ex_let_str created-or-found it BEFORE the right
;      side, D-LETNEWFIRST), (STRPTR) = the RHS descriptor.
; out: the target holds the RHS; an error is pending in FPERR (no room for the
;      copy, or the snapshot's overflow), raised by the caller's fp_stmt_done.
; A RHS whose bytes lie in the program text is stored BY REFERENCE: the VG-8020
; charges `A$="<40 chars>"` in a program nothing (FRE 200, ours was 160), and 9
; of them into A$() ran out of string space here only
; (probes/basic/basic_probe_litref.py). Same mechanism as tgt_store_ref.
; Anything else is COPIED by str_set_at below.
; 🧮 D-LETNEWFIRST (2026-10-19): this took the KEY and looked the target up
; again -- tgt_store_desc's var_alloc_or_find on the by-reference arm, str_set_key's
; on the copy arm -- after the right side. The entry now arrives in HL from the
; one lookup ex_let_str made before it, so neither arm looks anything up. Same
; 33 B as before, in front of the $3297 pin.
let_ref:
                inc     hl
                inc     hl
                inc     hl                  ; HL = the target's descriptor (entry+3)
                push    hl                  ; [dest]
                ld      hl,(STRPTR)
                push    hl                  ; [dest][the RHS]
                call    desc_in_text        ; Z: the bytes are in the program text
                pop     hl                  ; HL = the RHS descriptor
                pop     de                  ; DE = the target's descriptor
                jr      nz,str_set_at       ; anywhere else -> a copy
                ld      bc,3
                ldir                        ; the target := the RHS descriptor itself
                ret
; --- str_set_at: DE = a target descriptor, (STRPTR) = the source -> a copy ---
; str_set_key's store (basic/vars.asm) without its lookup: the H1 snapshot first,
; exactly as there -- it is what keeps an RVDESC / array-element source a fixed,
; GC-rooted descriptor across sh_var_store's own heap_alloc (and its GC) -- then
; the shared tail ssk_store with DE = dest, HL = the snapshot, [SAVED_TEMPPT].
; The target is an existing entry's descriptor, which neither a GC nor an array
; shift moves (ex_let's header has the argument).
str_set_at:
                ld      hl,(TEMPPT)
                push    hl                  ; [SAVED_TEMPPT] -- str_set_key's exact restore
                push    de                  ; [dest] across the snapshot (CALSLT)
    IF CLEARPOOL
                call    str_snapshot_keep   ; HL = the source, as str_set_key takes it
    ELSE
                call    str_snapshot_to_temp
    ENDIF
                pop     de                  ; DE = dest              [SAVED_TEMPPT]
                jp      ssk_store           ; op 12, release the snapshot, return

; --- ary_let_ref: the array LET's twin (D-LITREF) ----------------------------
; in:  (STRPTR) = the RHS, (ARY_ADDR) = the element's descriptor. HL preserved.
; out: Z -- the element := the RHS descriptor itself, no heap body; NZ -- copy.
ary_let_ref:
                push    hl
                ld      hl,(STRPTR)
                call    desc_in_text
                jr      nz,alr_no
                ld      hl,(STRPTR)
                ld      de,(ARY_ADDR)
                ld      bc,3
                ldir
                xor     a
alr_no:
                pop     hl
                ret

; nodisk_dev -- D-NODISKVERBS (2026-10-07): ON A DISKLESS MACHINE THE CASSETTE IS
; THE DEFAULT DEVICE, and a drive name is `Bad file name`. Measured on the VG-8020
; with no disk: `SAVE "X"` / `BSAVE "X",..` save to tape, `OPEN "X" FOR OUTPUT`
; opens it (D-NODISKOPEN's discriminator), and LOAD / MERGE / BLOAD / RUN / SAVE /
; BSAVE / OPEN of `"A:X"` are 56 (probes/basic/basic_probe_nodiskverbs.py).
;   in : HL = the staged name, past any device prefix the caller matched
;   out: NZ -- a disk is present: the caller's disk arm (HL unchanged);
;        Z  -- no disk, a device-less name: the caller's CASSETTE arm;
;        a name with a `:` anywhere (no disk) RAISES 56 and does not return.
nodisk_dev:
                call    diskslot_test
                ret     nz
                jp      ndd_scan            ; D-NODEV: the scan is past the $3297 pin
                                            ; (basic/main.asm, low region's end)
; pdf_baddrive -- a drive past B: -> ERR 62 `Bad drive name` (D-DRVNAME; the full
; story is at its old site in basic/files.asm). Moved here 2026-09-28 (D-NEWARG).
pdf_baddrive:
                ld      a,62
                jp      raise_error

ctl_reset:
                ; 🔴 THIS MUST SURVIVE BEING CALLED BEFORE THE SUB ROM EXISTS.
                ; `clear_vars` reaches it at init line 28, and `init_ext_roms` --
                ; which DISCOVERS the sub-ROM slot -- does not run until line 134.
                ; Going through `call_strheap` there takes subrom_absent_error and
                ; the machine never reaches BASIC: measured, and the same trap
                ; interp.asm already records for `show_title`. So this dispatches
                ; RAW and tolerates CF, and interp.asm calls it again once the scan
                ; has run.
                ; ⚠️ CSP := 0 FIRST, because a pool that is not live must say so:
                ; strheap_varceil's min(varceil, CSP) stands down on a zero CSP,
                ; and ctl_alloc's wrap test refuses every push. Power-on RAM here
                ; reads $FF (D-VALTYP), which would do neither.
                ld      hl,0
                ld      (CSP),hl
                ; 🔴 `cp 1`, NOT `or a`. SUBSLOT_OK is only zeroed INSIDE
                ; init_ext_roms, and clear_vars reaches here a hundred lines
                ; earlier -- so at cold boot the cell is power-on RAM, which reads
                ; $FF on this machine (D-VALTYP, docs/valtyp-coldram-notes.md §1).
                ; subrom_call's own `or a` guard therefore does NOT fire on
                ; garbage: it CALSLTs into a wild slot and the machine boots to a
                ; screen of pattern-table noise. No caller had ever dispatched the
                ; sub ROM this early, so the trap was latent until this arc.
                ; Testing for the value the scan actually WRITES is what makes
                ; garbage read as absent.
                ld      a,(SUBSLOT_OK)
                cp      1
                ret     nz                  ; not recorded yet -- CSP=0 stands
                ld      a,20                ; op 20 (CTL_RESET); SUBSLOT_OK = 1 above, so
                jp      sh_go               ; sh_go's absent-raise cannot fire

; --- penderr_set: FIRST-ERROR-WINS, AS A PROPERTY OF THE WRITE --------------
; (D-PENDERR, docs/spec-basic-penderr.md §4.) FPERR is the interpreter's single
; PENDING-ERROR CODE cell: a deferred fault records its code here and the
; statement boundary reports it. The reference raises EAGERLY -- the first fault
; aborts on the spot and the second never happens (D-TMFP, spec-basic-tmfp.md
; §2, measured on both machines) -- so of two faults pending in one statement the
; FIRST one is what must be reported. zerobas cannot raise eagerly (eval has no
; mid-expression unwind), so it emulates with this sticky cell.
;
; 🎯 THAT RULE IS ENFORCED HERE, ONCE, INSTEAD OF AT EVERY READER. Before this
; slice it was a house rule stated in comments and implemented ad-hoc at exactly
; two of the twenty-four writers (ev_f_defer in expr.asm, sfr_argok below); every
; other writer was a bare `ld (FPERR),a`, i.e. LAST-error-wins, and the type
; fault was kept safe from them only by living in a SEPARATE cell (TMISMATCH)
; that every reader had to test first. Collapsing the two cells is only sound
; once the write itself is set-if-empty -- otherwise `WIDTH (A$<5)+0*(1/0)`
; loses its type-mismatch code to fp_div's clobber (spec §3.2).
;
; in:  A = the deferred-error code (1..11, interp.asm's fperr_to_err domain).
; out: FPERR := A iff FPERR was still 0; otherwise the pending code is kept.
; ⚠️ PRESERVES EVERY REGISTER **AND THE FLAGS**, which is what makes it a
; drop-in for the bare `ld (FPERR),a` it replaces -- 3 bytes for 3 bytes at all
; twenty-three sites. The trailing `pop af` restores the CALLER's F (pushed on
; entry), not the `or a` this routine performs, so sites that carry flags across
; the store are unaffected: arrays.asm's ary_engine_call tail documents in prose
; that its NZ survives the write, and str-engine's sct_ae_set does `scf` after it.
penderr_set:
                push    af                  ; [the code + the CALLER's flags]
                call    fperr_test          ; D-FPCARVE: -1 B
                jr      nz,pes_pending      ; a fault is already pending: it happened
                                            ; FIRST, and first-error-wins keeps it
                pop     af                  ; A = the code again, F = the caller's
                ld      (FPERR),a
                ret
pes_pending:
                pop     af
                ret

; --- str_heap_oom_error: raise "Out of memory" (FPERR=6 — the SAME code ----
; arrays' own OOM uses; the shared fre_msgtab entry, no new message).
str_heap_oom_error:
                ld      a,FPERR_STROOM
                jr      raise_now
; raise_now: A = an FPERR code -> raise it AT ONCE, but a code already pending
; wins (first-error-wins, as penderr_set). D-DEFERRSTUDY: the immediate
; counterpart of `call penderr_set`. 🎯 VALTYP ($F663) is what machine code in
; H.ERRO reads at the error, and it is the type of whatever the REFERENCE last
; evaluated -- measured per fault (scratchpad/herro_run2.out): 8 after `/`,
; SQR / LOG and (-x)^frac, 3 after ASC(""), 2 after `\` and 0^-1. So the
; entries above raise_now set it first: raise_now8 (E = 8) and raise_now_t (E =
; the type) (D-ERRVALTYP).
raise_now8:
                ld      e,8                 ; the double the reference leaves
raise_now_t:
                ld      hl,FACTYP
                ld      (hl),e              ; VALTYP as the reference has it
raise_now:
                call    penderr_set
                jp      fp_runtime_error

; err_too_complex: fre_msgtab entry 9's string (interp.asm). MSX-authentic
; wording (the reference raises exactly this when its own temp-descriptor
; stack fills, §6/§11) — homed here (low region), not interp.asm's page 1
; (no slack there), same placement discipline as err_subscript et al
; (basic/arrays.asm).
; C5-LOW (2026-10-12): err_too_complex is GONE from main -- ERR 16's text is
; sub-hosted (sub/errmsg.asm em_too_complex); err_msgtab's row 16 points at
; err_subhosted, its only reader.

; --- err_out_of_str: the ERR 14 message (D-CLP) -----------------------------
; err_msgtab listed 14 as a HOLE pointing at "unprintable error", exactly as it
; listed 24 before LOCATE needed it. Homed HERE (low region) and not beside the
; table for the same reason err_too_complex and LOCATE's err_missing_operand are:
; bytes inserted next to err_msgtab push page 1's dense forward `jr`s out of
; reach (basic/missing.asm:70).
; C5-LOW (2026-10-12): err_out_of_str is GONE too -- ERR 14 is sub-hosted
; (em_out_of_str) on BOTH switch settings, so CLEARPOOL=0's old
; `Unprintable error` hole for ERR 14 closes with it.

; ===========================================================================
; Shared low-region helpers (arrays slice-4a). Homed HERE (the reclaimed low
; region) rather than in their page-1 callers because page 1 is byte-full;
; page 1 reaches them by ordinary in-slot call (page 1 <-> low region are the
; main ROM's co-mapped slot-0 pages). NOT reachable from a page-0 sub-ROM
; tenant — but every caller is main-ROM page-1/low code, never a tenant.
; ===========================================================================

; --- heap_reset: reset the string heap + temp-descriptor stack to EMPTY -----
; FRETOP := C = min(HIMEM,TXTMAX); TEMPTOP := TEMPBASE. Called by clear_vars
; (vars.asm) at init/NEW/RUN/CLEAR — the single "variables wiped" hook (§2/§6).
; D-CLP: this routine deliberately does NOT derive the pool boundary. S-CLP-2
; first had it store POOLBASE here, on the reasoning "RAM is not the scarce
; resource, ROM is" -- but the ROM that is scarce is THIS one (the low region,
; 30 B free), while the sub-ROM has ~3.4 KB. So the boundary is computed
; SUB-SIDE instead, as min(HIMEM,TXTMAX) - POOLSIZE, from two published sysvars
; plus the size CLEAR recorded. That costs the low region ZERO bytes.
; 🔴 THE JUSTIFICATION THAT USED TO FOLLOW IS ABOUT A STATEMENT THAT DOES NOT
; EXIST, AND IS INVERTED RATHER THAN DELETED (D-CLRFIX, 2026-08-23). It said the
; sub-side derivation "still makes `CLEAR ,himem` keep its size (characterization
; §2.8): that form moves the ceiling and never touches POOLSIZE, so re-deriving
; picks the change up for free." **`CLEAR ,himem` is a Syntax error on the
; VG-8020 AND the CF-3300** (rows q.comma / z.hd000, docs/spec-basic-clrfix.md),
; and §2.8's reference readings are VACUOUS -- the statement never ran. THE
; DESIGN IS UNAFFECTED and is still right for its own reason (the low region is
; the scarce ROM and the sub-ROM is not); what is gone is a benefit it never
; delivered, to a form the language does not have.
; Clobbers A,B,C,H,L (unchanged).
heap_reset:
                ld      hl,(HIMEM)
                ld      a,h
                or      l
                jr      z,hr_txtmax
                push    hl
                ld      bc,(TXTCEIL)        ; D-RAMCEIL: boot's ceiling, not the constant
                or      a
                sbc     hl,bc
                pop     hl
                jr      c,hr_have           ; HIMEM<TXTCEIL -> ceiling=HIMEM
hr_txtmax:
                ld      hl,(TXTCEIL)
hr_have:
                ld      (FRETOP),hl         ; HL = C, the ceiling
                ld      hl,TEMPPOOL         ; empty pool: TEMPPT at its base
                ld      (TEMPPT),hl
                ret

; --- pu_deref_body: HL = a [len:1][ptr:2] descriptor address (its len byte
; already consumed by the caller if needed) -> HL = its CURRENT body address
; (dereferences the ptr tail). The single shared "[len][ptr] -> bytes" reader
; for every page-1 string consumer (print_strval, PRINT USING string fields,
; LSET/RSET, CVI). Preserves EVERY register except HL (the returned body ptr).
; The A-preservation is load-bearing: ex_print_using's format copy keeps the
; format length in A across this call and uses it as the ldir count; an earlier
; A-clobber here let the copy count become the literal's pointer-low byte, so the
; format overran into the token stream and PRINT# USING wrote garbage to the file
; (screen PRINT USING only escaped it by luck of the literal's address). See
; docs/spec-print-hash-using.md.
pu_deref_body:
                push    af                  ; keep the caller's A (the format length)
                inc     hl
                ld      a,(hl)              ; ptr-lo
                inc     hl
                ld      h,(hl)              ; ptr-hi
                ld      l,a                 ; HL = body
                pop     af
                ret

; --- mk_rvdesc: A = len, HL = body address -> RVDESC := [len][ptr(=body)];
; returns HL = RVDESC. The shared "wrap a fixed RAM buffer as a [len][ptr]
; rvalue descriptor" builder (STRSCR producers; FLD_DESC's went with D-FLDDESC). Safe as ONE shared
; RVDESC cell only because each producer's value is consumed immediately
; (copied into a heap temp / a var's heap body) before the next string sub-
; expression reuses it. Clobbers A? no — preserves A. Clobbers nothing but the
; RVDESC cell + HL.
mk_rvdesc:
                ld      (RVDESC),a          ; RVDESC.len
                ld      (RVDESC+1),hl       ; RVDESC.ptr = body
                ld      hl,RVDESC
                ret

; --- strscr_desc: wrap the CURRENT STRSCR byte buffer as a [len][ptr] rvalue
; descriptor in RVDESC (RVDESC.len=(STRSCR), RVDESC.ptr=STRSCR+1). Used by
; every producer that fills STRSCR directly (MKI$/INPUT$/read_into_strscr
; callers). out: HL = RVDESC. Clobbers A.
strscr_desc:
                ld      a,(STRSCR)
                ld      hl,STRSCR+1
                jr      mk_rvdesc

; --- str_eval_plus (D-UPSTR): a leading `+` on a string operand -------------
; Unary plus is the IDENTITY, measured on both references: `B$=+A$` reads `X`
; and `B$=+"X"` reads `X`, where this ROM answered Type mismatch. The numeric
; half (D-UNARYPLUS, basic/expr.asm `ev_f_pos`) does not serve these rows at
; all -- a string RHS never reaches the numeric factor decoder; `ex_let_str`
; asks `str_eval_one`, which dispatches on the FIRST BYTE.
;
; 🔴 IT MUST NOT ADVANCE HL WHEN IT DECLINES, AND THAT IS WHY THIS IS SEVEN
; BYTES RATHER THAN ONE. `str_eval_one` is used as a DETECTOR as well as an
; evaluator -- basic/graphics.asm's PAINT colour arm (`call str_eval_one` /
; `jp c,gfx_typeerr` / `call gfx_eval_int16`), basic/time.asm and
; `str_concat_tail` below all carry on parsing FROM HL after a decline. So the
; obvious shape (`inc hl` and fall back into str_eval_one, mirroring
; `ev_f_pos`'s loop) would hand every one of them a cursor moved past a `+`
; they had not consumed. `PAINT(x,y),+1` happens to give the same answer either
; way, which is exactly what makes it the wrong thing to reason from
; [[two-rules-that-coincide-on-every-row-you-have]].
;
; ~~⚠️ Consequently this RECURSES where the numeric arm loops: `++A$` costs one
; frame per `+`. That is a real asymmetry with `ev_f_pos` and it is deliberate --
; the loop shape cannot restore the cursor.~~
; 🔴 D-DEEPEXPR (2026-10-20): THAT RECURSION WAS A MEMORY-SAFETY HOLE, and the
; premise under it was wrong. It ran with NO stack test, 2 B per `+`, inside
; ev_rel's string probe -- BEFORE any stk_guard of the statement -- so `B=` + 120
; unary `+` + `1` with ~200 B left wrote return addresses into the arrays and the
; machine read NO OUTPUT where the VG-8020 completes (scratchpad/deepexpr_run.out,
; row lb2). A loop CAN restore the cursor: it saves the FIRST `+` once and puts it
; back on a decline. So the body is now a loop at constant depth -- what the
; numeric arm (`ev_f_pos`, `jp ev_f`) already costs -- and it MOVED to
; basic/main.asm, at the low region's end past the $3297 pin, because the loop
; is 7 B longer and this file sits in FRONT of that pin (its 7 B here refill the
; R3 test in str_arg_open and INSTR's P3 below, exactly).

; --- str_eval_lit (repack): a '"'-quoted literal -> a [len][ptr] rvalue -----
; descriptor over the literal's bytes IN PLACE in the tokenised line (§3:
; zero-copy — a literal is never mutated, so RVDESC.ptr points straight at
; the token stream; its ptr sits outside [FRETOP,C) so it is never a GC
; root). Entered with HL on the opening quote; advances HL past the closing
; quote. Homed in the low region (page 1 full); str_eval_one (strvar.asm)
; reaches it by jp. Joins str_eval_ok (page 1) on success. Clobbers A,B,DE,HL.
str_eval_lit:
                inc     hl                  ; past the opening quote; HL = literal[0]
                push    hl                  ; save the literal start
                ld      b,0                 ; B = length so far (clamped to STRMAX=255)
sel_lp:
                ld      a,(hl)
                or      a
                jr      z,sel_close         ; unterminated -> stop (treat EOL as end)
                cp      '"'
                jr      z,sel_close_q
                ld      a,b
                cp      STRMAX
                jr      nc,sel_skip         ; full: stop counting (scan on to the quote)
                inc     b
sel_skip:
                inc     hl
                jr      sel_lp
sel_close_q:
                inc     hl                  ; past the closing quote
sel_close:
                ; HL = cursor past the operand
                ld      a,b                 ; A = length
                pop     de                  ; DE = literal start (RVDESC.ptr target)
                push    hl                  ; guard the advanced cursor
                ex      de,hl               ; HL = literal start (mk_rvdesc's body)
                call    mk_rvdesc           ; RVDESC := [len][ptr]; HL = RVDESC
                ; 🎯 D-PUBTAIL: THE CANONICAL "PUBLISH HL AS THE RESULT
                ; DESCRIPTOR" TAIL. Five sites ended with these three instructions
                ; verbatim; this one KEEPS them and the other four `jp` here, so the
                ; shared body costs no new bytes -- an existing tail given a name.
                ; ⚠️ THE PROTOCOL IS THE PART TO CHECK, NOT THE BYTES. Every site
                ; arrives with HL = the descriptor and EXACTLY ONE saved cursor on top
                ; of the stack, which this `pop hl` takes. A site with a different
                ; stack depth would return to the WRONG PLACE and no size or
                ; byte-identity check would say so, which is why all five were read
                ; before this landed.
str_pub_ok:
                ld      (STRPTR),hl
                jp      sfi_done            ; pop hl (cursor past the operand), then
                                            ; str_eval_ok -- C4 shared tail (2026-10-03)

; --- print_strval (repack): emit the [len][ptr] descriptor at STRPTR via -----
; pchar (screen or file per PRDEST). Homed in the low region (page 1 full);
; print.asm / printusing reach it by in-slot call. Clobbers A, B, HL.
print_strval:
                ld      hl,(STRPTR)
                ld      b,(hl)              ; B = length
                ld      a,b
                or      a
                ret     z                   ; empty string -> nothing to print
                call    pu_deref_body       ; HL = body
psv_lp:
                ld      a,(hl)
                rst     $18                 ; screen or file (PRDEST); preserves all
                inc     hl
                djnz    psv_lp
                ret

; --- lpt_flush (D-LPTVERB R-LP16): end a partial PRINTER line ----------------
; If the printer head is mid-line, send CR/LF and return it to column 0. Called
; from `repl` on every return to command level -- the measured rule is that a
; partial line is flushed THERE and not at the end of the statement
; (docs/lptverb-msx1-characterization.md §2.9: `LPRINT"A";` then a SEPARATE
; `PRINT LPOS(0)` reads 0, while the same two on ONE line read 3).
;
; ⚠️ HOMED IN THE LOW REGION FOR PRESSURE, exactly like print_strval above, and
; this slice is where that stopped being optional: inline in `repl` the block cost
; ~20 B of main page 1 and the image OVERRAN $8000 by ~9 B. Page 1 and the low
; region are co-mapped slot-0 pages, so a leaf moves between them freely and the
; two walls are coupled (basic/main.asm, docs/rom-region-structure-review.md §5);
; `repl` reaches it by in-slot call for 3 B.
;
; ⚠️ CALLS LPTOUT DIRECTLY, NOT pchar, on purpose: it must not depend on the sink
; cells, because `repl` clears PRDEST immediately afterwards and the flush has to
; work whatever the last statement left behind.
lpt_flush:
                ld      a,(LPTPOS)
                or      a
                ret     z                   ; already at column 0 -> nothing to end
                ld      a,13
                call    LPTOUT
                ld      a,10
                call    LPTOUT
                xor     a
                ld      (LPTPOS),a
                ret

; --- curlin_pub / curlin_direct: publish CURLIN ($F41C) -- D-CURLIN ----------
; 🏗️ Joost, 2026-09-24: zerobas maintains the reference's published current-line
; cell. `curlin_pub` IN: A = DIRECTF (1 direct / 0 program), from derive_directf;
; `curlin_direct` is the prompt's entry. CURLIN = $FFFF in direct mode, else the
; line NUMBER at CURLINE+2 (CURLINE points at the line's link field). Lives in
; the LOW region beside lpt_flush for the same reason: page 1 had no room.
; Clobbers A, HL.
curlin_pub:
                or      a
                jr      nz,curlin_direct
                ld      hl,(CURLINE)
                inc     hl
                inc     hl                  ; -> the line number
                ld      a,(hl)
                inc     hl
                ld      h,(hl)
                ld      l,a
                jr      curlin_store
curlin_direct:
                ld      hl,$FFFF
curlin_store:
                ld      (CURLIN),hl
                ret
; skipsp_test -- skip spaces at (HL); A = the first non-space char, Z iff it is the
; terminator. PROMOTED here from basic/program.asm by D-OKSTORE (2026-09-24): the
; low region and main page 1 are ONE budget (include order decides the region),
; and this 5 B body filled the low region's last 5 B so page 1 could fund the
; prompt protocol. Callers are unchanged (a `call` either way).
skipsp_test:
                call    skip_spaces
                or      a
                ret


; --- str_temp_alloc: A=length(0..255) -> push a temp-descriptor-stack ------
; entry owning a FRESH heap body of that length (§6/§7). Thin main-ROM glue
; for the string-heap tenant's TEMP_ALLOC op (the canonical shape: stage the
; SH_* param block, `call call_strheap`, read SH_ERR) — the
; actual push+alloc mechanics moved to the sub-ROM (sub/strheap.asm
; she_temp_alloc/sh_temp_push_alloc) once this low region ran out of room
; for them; see the tenant's own header for the shape-C rationale (§9). out:
; HL = the new temp-stack descriptor address; DE = the heap body address to
; fill (0 if length 0). On ANY failure (temp-stack overflow -> FPERR=9
; "String formula too complex"; heap OOM -> FPERR=6 "Out of memory") sets
; FPERR and returns a NEUTRALISED len-0/ptr-0 entry instead of aborting here
; — matches the established deferred-error discipline (D-F2-1/ev_f_empty):
; every str_eval() caller already checks FPERR at the statement boundary, so
; the caller can keep going structurally and the abort still happens before
; any bad value is ever consumed. Clobbers A, DE, IX.
str_temp_alloc:
                ld      l,a                 ; blk+0 = the length
                ld      a,3
                call    sh_go_g             ; op 3 (TEMP_ALLOC): HL = the slot, DE =
                                            ; (D-DEEPEXPR: the guarded gateway -- a
                                            ; skip lands in the OOM arm below with
                                            ; HL = STR_EMPTY, and ret_de0's DE = 0)
                ret     z                   ; its body; A = ERR (Z: ok)
                cp      2
                jr      z,sta_overflow
                ld      a,FPERR_STROOM
                call    penderr_set         ; the heap-OOM code (sysvars.inc):
                                            ; ERR 14 with the partition on, ERR 7
                                            ; without. The tenant still hands back
                                            ; a valid (neutralised) slot in HL here.
                jp      ret_de0
sta_overflow:
                ld      a,9
                call    penderr_set         ; "String formula too complex"
                ld      hl,STR_EMPTY        ; no slot was reserved -- STR_EMPTY is
                                            ; always a safe, never-a-GC-root fallback
                jp      ret_de0

; --- str_snapshot_to_temp: STRPTR -> some source descriptor (anywhere) -----
; push a NEW temp-stack entry OWNING a fresh heap-copied body, and repoint
; STRPTR at it. The general "snapshot an rvalue so it survives a later alloc/
; GC and so a shared mutable scratch (STRSCR) can't be clobbered by
; evaluating the next sub-expression" primitive — replaces the old
; str_dup_temp (ring-slot copy); SAME calling convention (out: HL = temp,
; STRPTR = temp), so every caller below is unchanged beyond the rename. Thin
; main-ROM glue for the tenant's SNAPSHOT op (same shape-C move as
; str_temp_alloc above; the copy itself happens tenant-side, she_snapshot).
; Clobbers A, DE, IX.
    IF CLEARPOOL
; --- str_snapshot_keep (D-CLP): the same primitive, but a source that is -----
; ALREADY a temp-stack entry is returned AS-IS instead of being copied. Only
; basic/vars.asm str_set_key uses it, and only because the pool made the
; difference visible: str_set_key's H1 snapshot exists to keep an ARRAY-ELEMENT
; or RVDESC descriptor from going stale across the target alloc's region shift +
; collision GC, and a temp entry was never exposed to either hazard (fixed
; address, enumerated GC root) -- its own header already said so. Before the
; partition the redundant copy landed in a ~15 KB gap and cost nothing visible;
; with `CLEAR n` it was a second full charge against the user's pool.
; 4 bytes of low region, all of it this entry head: the tail is shared.
str_snapshot_keep:
                ld      a,16                ; op = 16 (SNAPSHOT-UNLESS-TEMP)
                jr      sst_op
    ENDIF
; --- str_snapshot_arg (D-POOLCAP): what a STRING FUNCTION's first argument ---
; should use. LEFT$/RIGHT$/MID$ snapshot their source and then TRUNCATE IT IN
; PLACE, so they need an OWNED body -- but a source that is already an owned temp
; is one, and copying it is the "second full charge against the user's pool" that
; str_snapshot_keep's own header describes. D-CLP converted str_set_key and left
; these three; the cost was measured 2026-08-28:
;
;     LEN(LEFT$(X$+X$,0)) with 24 B live    references: works at CLEAR 70
;                                           zerobas:    needs CLEAR 120
;
; -- a 40 B temp charged twice. Slicing a VARIABLE was green on every side at
; CLEAR 70, which is what says the source's KIND is the variable at issue.
; An alias rather than an IF at each of the three call sites: the non-CLEARPOOL
; build has no str_snapshot_keep to call, and `switch-build-check` flips that
; switch. Zero bytes either way -- it is the same `call`, to a different label.
    IF CLEARPOOL
str_snapshot_arg equ str_snapshot_keep
    ELSE
str_snapshot_arg equ str_snapshot_to_temp
    ENDIF
; --- str_snapshot_slice (D-SLICEOOM): LEFT$/RIGHT$/MID$'s source only -------
; op 21 keeps a SCALAR variable as-is (the slice then allocates just its result,
; sub/strheap.asm she_slice_new) and otherwise is op 16. Concat and compare keep
; str_snapshot_arg. 4 bytes of low region.
    IF CLEARPOOL
str_snapshot_slice:
                ld      a,21                ; op = 21 (a slice's source)
                jr      sst_op
    ELSE
str_snapshot_slice equ str_snapshot_to_temp
    ENDIF

str_snapshot_to_temp:
                ld      a,4                 ; op = 4 (SNAPSHOT)
sst_op:
                ld      hl,(STRPTR)         ; source descriptor address (stable)
                call    sh_go_g             ; HL = the owned slot, A = ERR. D-DEEPEXPR:
                                            ; guarded -- a skip publishes STR_EMPTY
                                            ; below, never the SOURCE (P1)
                jr      z,sst_ok
                cp      2
                jr      z,sst_overflow
                ld      a,FPERR_STROOM
                call    penderr_set         ; heap OOM (sysvars.inc)
                ; ...and FALLS THROUGH sst_ok into sh_publish (D-CARVE2; the `jr`
                ; here was to the very next instruction: -2 B, GA-CROSS-ROMSCAN)
sst_ok:
                ; 🎯 D-CARVE2: the canonical "publish SH_PTR as the result" tail.
                ; Reached by fallthrough from sst_ok (and from the heap-OOM arm
                ; above it) AND by jp from the string-space-overflow arm, which
                ; differs only in the `penderr_set` it runs FIRST -- the decision
                ; stays with them.
sh_publish:                                 ; HL = the result descriptor (sh_go's)
                ld      (STRPTR),hl
                ret
sst_overflow:
                ld      a,9
                call    penderr_set         ; "String formula too complex"
                ld      hl,STR_EMPTY
                ld      (STRPTR),hl
                ret

; ===========================================================================
; Concat spine (§7): a running-ACCUMULATOR fold. Operand 1 becomes an owned
; temp R; each subsequent operand is appended onto R IN PLACE (sub-ROM op=2,
; sh_append). This is robust to an operand whose OWN evaluation pushes
; intermediate temps (a function operand, e.g. STR$(7), or the nested-concat
; case "A"+MID$("XY"+"Z",1,2)+"B") -- each operand is fully evaluated and
; appended before the next, so there is no "contiguous last-N temps"
; assumption to break. There is no shared mutable global accumulator (R is a
; per-expression temp), so the old STRCAT_R re-entrancy bug cannot recur
; (retires spec-basic-string-concat-nesting-fix.md).
; ===========================================================================

; --- str_concat_tail: fold trailing `+ operand` terms into R ---------------
; Entered by str_eval (basic/strvar.asm) AFTER operand 1: HL = cursor just
; past operand 1, STRPTR -> operand 1's descriptor, VALTYP = 1. If the next
; non-space token is '+', make operand 1 an owned temp R, then for each
; `+ operand`: evaluate it and append it onto R in place (op=2). The result
; is R. Otherwise leave STRPTR at operand 1 unchanged (single operand -- the
; zero-copy fast path). out: STRPTR -> result, VALTYP = 1, HL past the whole
; expression, CF set. CF clear if a trailing operand is malformed. Clobbers
; A, BC, DE, HL, IX (the sub-op stubs CALSLT).
str_concat_tail:
                push    hl                  ; save cursor (operand-1 end)
                call    skip_spaces         ; HL -> next non-space
                cp      PLUS_TOKEN          ; '+' ($F1) ?
                jr      z,sct_go
                pop     hl                  ; no concat -> restore exact cursor
                scf
                ret
sct_go:
                pop     bc                  ; HL already @ '+' (skip_spaces result)
                push    hl                  ; save cursor (@ '+')
                call    str_snapshot_arg    ; operand 1 -> owned temp R; HL=R, STRPTR=R
                                            ; (R must be a temp we can modify in place --
                                            ; never a var slot. 🔁 D-TEMPPOL 2026-09-25:
                                            ; an op1 that is ALREADY a temp is owned by
                                            ; this expression alone and IS R. It used to
                                            ; be copied -- "one extra harmless temp" --
                                            ; and that extra temp per level is what made
                                            ; zerobas hold TWO descriptors per pending
                                            ; `MID$(..)+(..)` level where the reference
                                            ; holds one (scratchpad/tempst_probe.py).)
                ex      (sp),hl             ; [R]; HL = cursor (@ '+')
sct_loop:
                rst    $10                ; past the '+'
                call    str_eval_one        ; STRPTR -> operand, HL = ADVANCED cursor, CF
                jr      nc,sct_err2         ; malformed operand -> clean [R]
                push    hl                  ; [R][advanced cursor] (save the ADVANCED
                                            ; cursor -- past the operand, not its start)
                ; append R += operand(STRPTR), in place
                pop     bc                  ; BC = advanced cursor   [R]
                pop     de                  ; DE = R (the stable temp slot, modified
                push    de                  ; in place)              [R]
                push    bc                  ; [R][cursor]
                ld      hl,(STRPTR)         ; HL = the operand (any stable descriptor)
                ld      a,2
                call    sh_go_g             ; op 2 (APPEND): A = ERR (D-DEEPEXPR:
                                            ; a skip's 6 maps to STRLONG below and
                                            ; loses to the 7 already pending; R
                                            ; is untouched)
                jr      nz,sct_append_err   ; heap OOM / overflow -> [R][cursor]
sct_cont:
                pop     hl                  ; HL = cursor            [R]
                call    skip_spaces
                cp      PLUS_TOKEN
                jr      z,sct_loop          ; another '+': HL @ '+', [R] on stack
                ; no more terms -> result = R
                pop     de                  ; DE = R                 [ ]
                ex      de,hl               ; HL = R, DE = cursor
                ld      (STRPTR),hl         ; STRPTR = R (the result)
                ex      de,hl               ; HL = cursor
                scf
                ret
sct_err2:
                ; D-CATFIX (2026-09-01, supersedes the BUG C NC-decline that stood
                ; here). A '+' committed this expression to string concatenation
                ; and the operand is not a string form. The old shape armed a
                ; deferred TM and returned NC, and the driver's numeric re-drive
                ; then ENDED AT THE UNCONSUMED QUOTE (the D-NUMSTR factor defers
                ; without consuming a literal), so the operand was evaluated ZERO
                ; times -- `"AB"+(0*(1/0)+1)` read 13 where both references say
                ; 11, and catusr's counter read 0 against the references' 1. The
                ; reference is SINGLE-PASS: it evaluates the operand during its
                ; one drive, so the operand's own fault fires before any type
                ; conclusion. Mirror that here and never decline:
                ;   * operand slot ENDED (EOL/':') -> Missing operand, ERR 24 --
                ;     measured on both references for `A$+`, `"AB"+` and
                ;     `"AB"+:...` (scratchpad/cattrail_probe.py), the D-MISSOP
                ;     "slot ends where a value was needed" rule;
                ;   * otherwise EVALUATE THE OPERAND ONCE (its fault, if any,
                ;     lands in FPERR first), then arm type mismatch through
                ;     penderr_set, whose first-error-wins keeps the operand's
                ;     own code -- and, unlike TMISMATCH, FPERR is what
                ;     ems_print's check_fperr_only reads BEFORE emitting the
                ;     item, so `PRINT "AB"+5` raises without leaking `AB`;
                ;   * return CF=1 with R (the partial result) as the value, so
                ;     the driver NEVER re-drives -- one evaluation by
                ;     construction, not by precedence.
                ld      a,(hl)              ; decline left HL at the operand start
                or      a
                jr      z,se2_miss          ; `A$+` at end of line
                cp      COLON
                jr      z,se2_miss          ; `A$+:...`
                call    eval                ; the ONE evaluation; HL advances past
                                            ; the operand ([R] stays under eval's
                                            ; own frame, untouched)
                ld      a,10                ; type mismatch, unless the operand's
                jr      se2_arm             ; own fault already holds FPERR
se2_miss:
                ld      a,FPERR_MISSOP      ; ERR 24
se2_arm:
                call    penderr_set         ; first-error-wins
                pop     de                  ; DE = R                 [ ]
                ld      (STRPTR),de         ; the partial result IS the value
                scf                         ; success-shaped: no re-drive
                ret
sct_append_err:
                ; SH_ERR = 1 (heap OOM), 2 (temp overflow) or 3 (D-STRLONG: the
                ; combined length is over STRMAX). Result = R (the partial
                ; accumulator, still valid -- sh_append raises the length case
                ; BEFORE it touches R or the heap); set FPERR so the statement-
                ; boundary check aborts before the value is consumed.
                ;
                ; 🔴 THIS TAIL USED TO `ret` HERE, AND THAT LEFT ANY `+ term`
                ; STILL TO ITS RIGHT UNPARSED (D-STRLONG, spec §6). HL is the
                ; cursor just past the operand that FAILED, so `LEN(X$+X$+X$)`
                ; came back to the caller with `+X$` still in the text; the
                ; caller re-drove it as a NUMERIC continuation and the statement
                ; reported `Type mismatch` instead of the error that actually
                ; happened. It was never specific to SH_ERR=3 -- probe row
                ; `x.oom3` reproduces it through a plain pool OOM (SH_ERR=1), on
                ; code that predates this slice entirely.
                ; 🎯 THE FIX IS TO REJOIN THE FOLD, NOT TO LEAVE IT. penderr_set
                ; is FIRST-ERROR-WINS (above), so the remaining terms may be
                ; consumed, appended and even fail again without changing what
                ; is reported -- and the normal exit at sct_cont publishes R and
                ; the final cursor exactly as it does on the success path. That
                ; also deletes this tail's own STRPTR store and `scf`/`ret`.
                cp      2                   ; A = ERR (sh_go's); `ld` does not touch flags, so both
                                            ; branches below read THIS compare
                ld      a,FPERR_STROOM      ; SH_ERR=1 -> heap OOM (sysvars.inc)
                jr      c,sct_ae_set
                ld      a,9                 ; SH_ERR=2 -> "String formula too complex"
                jr      z,sct_ae_set
                ld      a,FPERR_STRLONG     ; SH_ERR=3 -> ERR 15 "String too long"
sct_ae_set:
                call    penderr_set
                jr      sct_cont            ; consume whatever is still pending

; ===========================================================================
; S4 — the core string VERBS (repack build only): LEN/ASC/VAL (string->number)
; and CHR$/STR$/LEFT$/RIGHT$/MID$ (->string). Their keyword tokens are already
; crunched + LIST-detokenised (kwtable.inc, S3); these are the handlers.
;
; Clean-room: original code. The verb SEMANTICS (1-based MID$, LEFT$/RIGHT$ head/
; tail clamps, ASC "" = error, VAL's leading-parse, STR$'s leading blank for
; non-negatives) are from the public MSX-BASIC language reference. CHR$'s 0..255
; domain and VAL's float parse follow the reference as measured (D-MISS-2,
; D-VALFLOAT) -- the old "CHR$ takes the low byte" and "integer-only VAL"
; divergences are gone. Results transiting the heap-backed temp-descriptor
; stack (§6/§7) is zerobas's own design. No disassembly.
; ===========================================================================

; --- helpers ---------------------------------------------------------------

; str_min_bc: A = min(A, BC), treating A as a 0..255 length and BC as a 0..65535
; requested count. Used to clamp a LEFT$/RIGHT$/MID$ count to the bytes available.
; Preserves BC, DE, HL. Clobbers A + flags. Unchanged from pre-4a (a pure
; length compare, no descriptor-format dependency).
str_min_bc:
                inc     b
                dec     b                   ; test B (high byte of the count)
                ret     nz                  ; count >= 256 -> min is the length (A<=STRMAX)
                cp      c                   ; length - count(low)
                ret     c                   ; length < count -> length is the min (A)
                ld      a,c                 ; else the count is the min
                ret

; str_temp_slice: in the temp descriptor at BC, keep E bytes starting at
; offset D (0-based) of its CURRENT body, moving them to the front of that
; SAME body (already uniquely owned — no realloc needed, slicing only
; shrinks/moves within memory we already own) and setting the descriptor's
; length to E. Used by LEFT$ (start 0 -> pure truncation), RIGHT$ and MID$.
; Pre-validated so that start+count <= length and count <= STRMAX. in:
; BC = temp descriptor address, D = start, E = count. Clobbers A, BC, DE, HL.
; Thin main-ROM glue for the string-heap tenant's SLICE op (mirrors
; str_temp_alloc) — the byte-move mechanics moved to the sub-ROM
; (sub/strheap.asm she_slice) once this low region ran out of room for
; them; SAME calling convention (BC=temp descriptor, D=start, E=count), so
; every caller (str_fn_left/right/mid) is unchanged. Clobbers A, BC, DE, IX.
str_temp_slice:
                ld      h,b
                ld      l,c                 ; HL = the temp descriptor (blk+2)
                ld      c,d
                ld      b,e
                push    bc                  ; blk+10 = start, blk+11 = count
                ld      a,5
                call    sh_go_g             ; op 5 (SLICE). D-DEEPEXPR: a skip leaves
                                            ; the temp unsliced and still valid; the
                                            ; pushed 4th word is ours to pop either way
                pop     bc
                ret

; --- LEN/ASC/VAL: string-argument functions in the NUMERIC evaluator -------
; Reached from ev_f_ff (basic/expr.asm) via `jp ev_ff_strnum` on an unrecognised
; $FF selector.
; Entered with IX on the function selector byte. Each returns its numeric result in
; DE (the factor convention), IX advanced past the call.
ev_ff_strnum:
                cp      LEN_TOKEN           ; $92 -> LEN(a$)
                jr      z,ev_ff_len
                cp      ASC_TOKEN           ; $95 -> ASC(a$)
                jr      z,ev_ff_asc
                cp      VAL_TOKEN           ; $94 -> VAL(a$)
                jr      z,ev_ff_val
                ; a $FF string-only token (LEFT$/RIGHT$/MID$ = $81/$82/$83, etc.)
                ; used where a NUMERIC factor is required. BUG C (Fable
                ; 2026-07-17): the old bare `jp ev_f_err` set only ERRMARK (which
                ; check_expr_errors does NOT inspect) and did NOT advance IX, so
                ; once ev_rel's fixed probe re-drives `LEFT$("AB")` numerically the
                ; PRINT item loop spun forever emitting " 0". A DEFERRED fault it
                ; must stay -- but D-LEFTTM changes WHICH fault, and WHEN.
                ;
                ; D-LEFTTM (docs/spec-basic-lefttm.md): `PRINT LEFT$(5,2)` answered
                ; ERR 2 where both references answer ERR 13. This was `jp ev_f_empty`
                ; -- FPERR=4 "syntax error", armed WITHOUT LOOKING AT THE ARGUMENT.
                ; 🎯 THE REFERENCE RULE IS "EVALUATE THE ARGUMENT AND REPORT WHAT IT
                ; RAISES; ONLY A CLEAN EXPRESSION IS A TYPE MISMATCH." So evaluate
                ; FIRST, then defer TYPEMM -- ev_f_defer is already first-error-wins,
                ; so a fault the argument raised keeps the answer and this one is
                ; dropped. `PRINT LEFT$(0*(1/0)+1)` is Division by zero, not 13.
                ; 🔴 AND THAT ORDER IS THE WHOLE FIX. D-NGRAM8 tried a deferred
                ; type_mismatch_set in str_arg_snap and it measured WRONG for exactly
                ; the mirror-image reason: at that instant the argument has NOT been
                ; evaluated, so the mismatch armed FIRST and BLOCKED the real fault.
                ; Same code, same mechanism, opposite side of the evaluation.
                call    ixsp_paren         ; D-IXSP
                jr      nz,evff_strnum_tm   ; malformed: no argument to evaluate
                inc     ix
                call    ev_e                ; the argument, numerically -- it arms its
                                            ; OWN fault first if it has one
evff_strnum_tm:
                ld      e,FPERR_TYPEMM      ; -> ERR 13, unless the argument beat us
                jp      ev_f_defer

; ev_str_arg: parse "( <string-expr> )" from the IX token stream, leaving STRPTR ->
; the argument's descriptor and IX past ')'. Mirrors ev_ff_cvi's IX<->HL
; bridge. On a syntax/type error it does not return — it `jp ev_f_err` like every
; other factor error. Entered with IX on the function selector byte. UNCHANGED
; from pre-4a (format-agnostic — it only ever hands off to str_eval).
ev_str_arg:
                call    ixsp_paren_req     ; D-IXSP
                call    ixsp                ; D-IXSP
                ; empty string-argument (LEN()/ASC()/VAL(), or a trailing ','):
                ; the same missing-operand syntax error as ev_f's ')'/',' gate
                ; (D-F2-3). Route to ev_f_empty so FPERR=4 is set on THIS eval --
                ; then the PRINT/LET driver's check_expr_errors aborts before the
                ; caller's stale-STRPTR read can print a garbage length/byte
                ; (spec-basic-empty-expr-syntax-error.md).
                cp      ')'
                jr      z,esa_empty         ; Z still set: the jp below takes it
                cp      ','
esa_empty:
                jp      z,ev_f_empty
                call    str_eval_ix            ; STRPTR -> desc; HL advanced; CF=ok
                ; BUG C class (Fable 2026-07-17): a NON-string arg -- LEN(5), or a
                ; NESTED malformed string fn LEN(LEFT$("AB")) whose str_eval CALSLT'd
                ; then exited NC -- used to `jp ev_f_err` (ERRMARK only, un-advanced
                ; IX): the caller then read a STALE STRPTR as the answer and dropped
                ; the statement tail. Defer via ev_f_tmm so the driver's check_expr_errors
                ; aborts (garbage IX/STRPTR then can't matter). ev_f_tmm's first-error-wins
                ; SPLITS the two: LEN(5) (FPERR clean, genuinely numeric) -> FPERR=10
                ; "type mismatch" (ref); LEN(LEFT$("AB")) (inner fn already set FPERR=4)
                ; -> keeps "syntax error". (2026-07-17: was ev_f_empty -> always "syntax".)
                jr      nc,esa_tmm          ; D-STRTM: evaluate FIRST, then defer
                push    hl
                pop     ix                  ; IX = cursor past the string operand
                call    evsp_close          ; D-EVSPCLOSE
                inc     ix
                jp      esa_release_int     ; D-TEMPPOL: pop the consumed arg temp,
                                            ; then flt_int_result -- LEN/ASC/VAL return
                                            ; ints even when a float is nested in the
                                            ; string arg (float.asm F1; clobbers A only,
                                            ; then ret to the caller)
; --- D-STRTM: a NON-string argument is a type mismatch, but the operand's OWN
; fault outranks it (docs/spec-basic-strtm.md). This was a bare `jp nc,ev_f_tmm`
; -- armed WITHOUT LOOKING AT THE OPERAND -- and the comment above reasoned that
; first-error-wins would split LEN(5) from LEN(LEFT$("AB")). It does, but ONLY
; when the inner thing already set FPERR. `LEN(0*(1/0)+1)` sets nothing: str_eval
; declines without evaluating, the mismatch arms first, and the division by zero
; is never raised. Both references answer Division by zero.
; 🎯 SAME FIX AS D-LEFTTM AND D-INSTRTM, AND FOR THE THIRD TIME THE FIX IS THE
; ORDER: evaluate the operand, THEN defer -- ev_f_defer is first-error-wins, so a
; fault the operand raises keeps the answer.
; 🟢 AND THERE IS NO DOUBLE EVALUATION HERE, which is what makes it safe:
; ev_str_arg is already ON the numeric evaluator's path, so nothing re-drives the
; operand afterwards. (sct_err2's mirror of this bug does NOT have that property
; -- it returns NC and the caller re-drives -- which is why that one is filed
; rather than fixed here.)
; HL is the cursor, still on the operand; `eval` takes it there and preserves IX.
esa_tmm:
                call    eval                ; the operand, numerically -- it arms its
                                            ; OWN fault first if it has one
                jp      ev_f_tmm            ; -> ERR 13, unless the operand beat us
ev_ff_len:
                call    ev_str_arg          ; STRPTR -> desc
                ld      hl,(STRPTR)
                ld      e,(hl)              ; DE = descriptor length byte (still
                ld      d,0                 ; offset 0 in the new format — unchanged)
                ret
ev_ff_asc:
                call    ev_str_arg
                ld      hl,(STRPTR)
                ld      a,(hl)              ; length
                or      a
                jr      z,asc_empty         ; ASC("") -> Illegal function call, at once
                inc     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = ptr (the body address)
                ld      a,(de)              ; first byte of the body
                jp      ev_ret_e            ; D-RETTAIL: DE = A (0..255)
asc_empty:
                ld      a,3                 ; FPERR 3, and VALTYP 3 (a string was the
                ld      e,a                 ; last thing evaluated: herro_run2.out)
                jp      raise_now_t
; ✅ D-AMPB (2026-10-09): `&B` BINARY. Both references crunch `&B101` as the
; typed characters (no token -- basic/PROVENANCE.md "&O / &B"), and the
; VG-8020 then READS them when the line runs: `PRINT &B101` 5,
; `&B1111111111111111` -1, `&b101` 5, a bare `&B` 0, and the number stops at the
; first byte that is not 0/1 (`PRINT &B12` prints 1 and 2); a seventeenth
; significant digit is Overflow (scratchpad/ampb_run2.out). zerobas called all
; of it Syntax error. `&` + anything else keeps today's path (`&X1` is 2 on
; both). Sited here, beside VAL, in the LOW region: main page 1 had
; 53 B and this is 37 (the dispatch in ev_f_nonlet is 5).
evnl_amp:
                ld      a,(ix+1)
                cp      'B'                 ; (the crunch uppercases `&b`: knife
                                            ; K-AB3 showed a case fold here was dead)
                jp      nz,evnl_miss        ; not &B: as before (expr.asm)
                inc     ix                  ; on the B
                ld      de,0
evnl_blp:
                inc     ix
                ld      a,(ix+0)
                sub     '0'
                cp      2
                ret     nc                  ; DE = the value, IX past the digits
                ex      de,hl
                add     hl,hl               ; a 1 shifted out of bit 15 ->
                ex      de,hl
                jr      c,evnl_bovf         ; Overflow, as on the VG-8020
                or      e
                ld      e,a
                jr      evnl_blp
evnl_bovf:
                ld      a,1                 ; Overflow at once, VALTYP 8 as on the
                jp      raise_now8          ; VG-8020 (D-DEFERRSTUDY family 2)
ev_ff_val:
                call    ev_str_arg          ; STRPTR -> the string-arg descriptor;
                                            ; IX advanced past ')'
                ; VAL's leading-number parse (floats via tk_float, D-VALFLOAT)
                ; moved to the sub-ROM tenant (sub/strheap.asm sh_val_parse,
                ; op=13) — pure-RAM parse of (STRPTR)'s body, page-1/low both
                ; byte-full. Thin glue mirrors str_temp_alloc.
                ld      a,13                ; op 13 (VAL_PARSE)
                push    ix                  ; the CALSLT in sh_go clobbers IX -- guard
                call    sh_go_g             ; the token cursor ev_f needs back. A = ERR,
                                            ; (D-DEEPEXPR: a skip's A = 6 -> E = 4 below,
                                            ; which loses to the 7 already pending)
                pop     ix                  ; DE = the int, C = the type
                ; D-VALBASE: the base-literal scan can REFUSE, and VAL's usual
                ; "never raises, returns 0" does not cover it -- both references
                ; answer `Syntax error` for `VAL("&")` and `VAL("&17")` ('&' not
                ; followed by H/O/B) and `Overflow` for `VAL("&H1FFFF")`.
                ; SH_ERR 4 -> FPERR 4 (syntax), 5 -> FPERR 1 (overflow -> ERR 6).
                ; 🟢 Deferred through ev_f_defer like every other factor refusal,
                ; so first-error-wins still lets an operand's own fault outrank
                ; this one.
                jr      nz,evv_refuse       ; (`pop ix` kept sh_go's flags)
                ; D-VALFLT: the type is 0 when the answer is the integer in DE,
                ; and otherwise the FACTYP (4/8) of a value the tenant has already
                ; placed in FAC. The float arm then ends exactly where a float
                ; LITERAL's does -- ev_f_float's own tail -- so every int consumer
                ; downstream keeps working and the type is the literal's type.
                ld      a,c
                or      a
                jp      nz,flt_to_int16     ; DE = the rounded int16; FAC/FACTYP stand
                ret                         ; DE = the parsed integer value
evv_refuse:
                cp      5                   ; SH_ERR 4 -> syntax error, at once
                jp      nz,ev_f_empty       ; (D-DEFERRSTUDY family 3)
                ld      a,1                 ; SH_ERR 5 -> overflow, AT ONCE as on the
                jp      raise_now           ; VG-8020 (D-DEFERRSTUDY family 2)

; --- str_arg_snap: evaluate a string argument and OWN it (D-NGRAM8) ---------
; LEFT$, RIGHT$ and MID$ all open the same way: evaluate the source expression,
; decline if it is not a string, then snapshot it into a temp we own before the
; count argument is evaluated (that evaluation can push temps of its own). 3
; identical runs -> one body plus three 3 B calls.
;   in:  HL = cursor at the source expression.
;   out: STRPTR -> an OWNED temp, HL = the cursor just past the expression --
;        exactly as the open-coded form left them, so each caller's following
;        `ld a,(hl)` reads the same byte.
; ⚠️ THE DECLINE IS A KNOWN DIVERGENCE AND IT IS DELIBERATELY LEFT ALONE HERE.
; `LEFT$(5,2)` answers ERR 2 where both references answer ERR 13, because
; str_eval_no DECLINES and the evaluator re-drives the whole thing numerically.
; 🔴 BOTH OBVIOUS FIXES ARE WRONG, MEASURED: a direct `jp type_mismatch_error`
; overrides a fault that is already pending, and a DEFERRED `type_mismatch_set`
; here is worse -- at this instant the argument has NOT been evaluated yet, so
; nothing is pending, the type mismatch is armed FIRST, and first-error-wins
; then BLOCKS the real fault the numeric re-drive raises. penderr-acceptance row
; `o.pt.left` (`Q2$=LEFT$(0*(1/0)+1)`) caught both. The reference evaluates the
; expression and reports what IT raises; only a clean expression is a type
; mismatch. That is a change to what happens AFTER the decline, not here.
; Filed in TODO.md.
str_arg_snap:
                call    str_eval            ; STRPTR -> source; HL advanced; CF=ok
                jr      nc,sas_decline
                push    hl                  ; save the cursor across the snapshot
                call    str_snapshot_slice  ; STRPTR -> an OWNED temp, or a kept
                                            ; SCALAR (D-SLICEOOM); HL = it
                pop     hl
                ret
sas_decline:
                ; 🔴 THE DECLINE IS THE PART A CALL BREAKS, AND IT COST A RED GATE.
                ; Open-coded, `jp nc,str_eval_no` ran in the VERB's frame, so
                ; str_eval_no's `ret` declined out of LEFT$/RIGHT$/MID$ entirely.
                ; Behind a `call` it runs one frame deeper and that `ret` lands
                ; back INSIDE the verb, just after the call -- the decline stops
                ; declining and the verb carries on. penderr-acceptance row
                ; `o.pt.left` caught it (zb answered 2 where the references
                ; answer 11). Discarding our own return address restores the
                ; original stack shape exactly. +4 B, and not optional.
                ; [[a-shared-tail-is-not-a-decision]]
                ; 🎯 D-ARGOPEN ADDS A SECOND FRAME, AND THEREFORE A SECOND POP.
                ; str_arg_snap's three call sites are now ONE -- str_arg_open, the
                ; shared prologue below -- so the decline is two frames deep, not
                ; one, and discarding a single return address would land
                ; str_eval_no's `ret` back INSIDE str_arg_open. That is the very
                ; failure this routine's comment describes, one level up.
                ; ⚠️ THE SECOND POP IS CORRECT ONLY WHILE str_arg_snap HAS EXACTLY
                ; ONE CALLER. Arm S1 in scratchpad/argopen_knives.py counts them;
                ; a fourth verb calling it directly would need its own shape.
                ; 🎯 AND THIS ONE IS WITNESSED WHERE str_arg_open's BAIL IS NOT:
                ; a DECLINE is not an error. The caller retries the operand
                ; numerically and that retry is visible (`LEFT$(5,2)` -> ERR 13),
                ; whereas a deferred error's report resets SP and erases the
                ; damage. K-AO1 moves rows; the pop it replaced moved none.
                pop     af                  ; discard str_arg_snap's return address
                pop     af                  ; ...and str_arg_open's
                jp      str_eval_no         ; now declines out of the VERB, as before

; --- CHR$/STR$/LEFT$/RIGHT$/MID$: string-VALUED $FF functions ---------------
; Reached from str_eval_maybe_mki (basic/strvar.asm) via `jp str_func_ff` on a
; non-MKI$ $FF token (repack build only). Entered with HL on the selector byte, A = that byte, and
; a string context wanting a value. On success each pushes its result as a new
; temp-descriptor-stack entry, points STRPTR at it, and joins str_eval_ok
; (VALTYP=1, CF set, HL past the call). A malformed call or a non-string $FF
; token falls to str_eval_no (CF clear) so the caller treats it as "not a
; string operand" (an error, or — in the numeric/PRINT path — a retry as a
; numeric factor). Dispatch shell UNCHANGED from pre-4a.
str_func_ff:                                ; A = (HL): the sole caller's cp chain
                                            ; (str_eval_maybe_mki) leaves it there
                cp      CHRD_TOKEN          ; $96 -> CHR$
                jr      z,str_fn_chr
                cp      STRD_TOKEN          ; $93 -> STR$
                jr      z,str_fn_str
                cp      LEFTD_TOKEN         ; $81 -> LEFT$
                jp      z,str_fn_left
                cp      RIGHTD_TOKEN        ; $82 -> RIGHT$
                jp      z,str_fn_right
                cp      MIDD_TOKEN          ; $83 -> MID$
                jp      z,str_fn_mid
                cp      HEXD_TOKEN          ; $9B -> HEX$
                jp      z,str_fn_hex
                cp      OCTD_TOKEN          ; $9A -> OCT$
                jp      z,str_fn_oct
                cp      BIND_TOKEN          ; $9D -> BIN$
                jp      z,str_fn_bin
                cp      SPACED_TOKEN        ; $99 -> SPACE$
                jp      z,str_fn_space
                dec     hl                  ; restore HL to the $FF prefix
                or      a                   ; = str_eval_no inlined: CF clear -> not a
                ret                         ; string operand (A = token, NZ, as before)

; CHR$(n): a 1-byte string of the character code n, which is 0..255 (D-MISS-2).
; This used to be documented as an own-design leniency that "takes E" — it was
; not lenient, it was a SILENT WRONG ANSWER: CHR$(-1)/CHR$(256) both built a
; 1-byte string where the reference raises Illegal function call, and
; CHR$(32768) where it raises Overflow. eval_byte_arg is both stages.
; In-domain behaviour is unchanged, coercion included: the reference truncates
; toward zero BEFORE checking, so CHR$(255.9) and CHR$(-0.5) are legal.
str_fn_chr:
                call    inc_skip_paren     ; D-FNSPACE: past the name AND any
                                            ; spaces before '(' — both references
                                            ; accept `LEFT$ ("AB",1)`
                jr      nz,str_arg_empty
                inc     hl
                call    eval_byte_arg       ; DE = n, 0..255 (or aborts); HL advanced
                ld      a,(hl)
                cp      ')'
                jr      nz,str_arg_empty
                inc     hl                  ; HL past ')'
                push    hl                  ; guard cursor across the temp write
                ld      l,1                 ; length 1 (the FILL op, as SPACE$ /
                                            ; STRING$); E = the char = the fill byte
                ld      a,8                 ; op = 8 (FILL)
                jp      shx_op_tail         ; drives it, publishes

; STR$(n): the decimal text of n. Leading blank for non-negative n (MSX format);
; the '-' for a negative is emitted by pu_fmt_int. Reuses print.asm's div10 via
; pu_fmt_int (NUMBUF = "[-]digits",0, B = digit count) — no perturbation of the
; existing PRINT/USING paths (they keep their own entry points).
str_fn_str:
                call    inc_skip_paren     ; D-FNSPACE: past the name AND any
                                            ; spaces before '(' — both references
                                            ; accept `LEFT$ ("AB",1)`
                jr      nz,str_arg_empty
                call    inc_eval            ; DE = n
                ld      a,(hl)
                cp      ')'
                jr      nz,str_arg_empty
                inc     hl                  ; HL past ')'
                push    hl                  ; guard cursor                       [CURSOR]
                ; --- D-STRFLT: STR$ OF A NON-INTEGER --------------------------
                ; This formatted DE with pu_fmt_int and never looked at FACTYP,
                ; so a float argument was silently the int16 flt_to_int16 left
                ; behind: `STR$(1.5)` -> "1", `STR$(.5)` -> "0",
                ; `STR$(1E9)` -> "0", `STR$(1.234567890123#)` -> "1".
                ; 🟢 PRINT's own formatter was already right (the ctl.* rows in
                ; scratchpad/strflt_probe.py are green), so the defect is HERE and
                ; the fix is to reuse it rather than to write a second one.
                call    factyp_is2         ; §9.4: dispatch after eval, exactly as
                                           ; print.asm's exp_num does
                jr      nz,sfs_float
                ld      c,0                 ; C = leading-space count
                bit     7,d                 ; sign of n
                jr      nz,sfs_conv         ; negative -> no leading space
                inc     c                   ; non-negative -> one leading space
sfs_conv:
                call    pu_fmt_int          ; NUMBUF="[-]digits",0; B=digit count; C preserved
                ld      hl,NUMBUF           ; HL = the source text
                jr      sfs_build
                ; --- the float arm: flt_fmt's text, MINUS PRINT's trailing space
                ; ⚠️ THE TRAILING SPACE IS THE WHOLE DIFFERENCE BETWEEN PRINT AND
                ; STR$, and no row in the value suite could see it -- the harness
                ; prints `"[";expr;"]"` and the capture strips, so ` 1.5` and
                ; `1.5` read the same. It is pinned twice in strflt_probe.py: a
                ; `"<"+...+">"` fence (` < 1.5>` on both references) and LEN
                ; (`LEN(STR$(1.5))` = 4, `LEN(STR$(0))` = 2).
                ; The LEADING space/sign is kept, because flt_fmt writes it and
                ; both references keep it -- which is why C is 0 on this arm.
sfs_float:
                call    flt_fmt             ; HL = FOUTBUF, NUL-terminated
                ld      b,255               ; -> B = length INCLUDING the trailing
sfs_flen:                                   ;    space (first `inc b` makes it 0)
                inc     b
                ld      a,(hl)
                inc     hl
                or      a
                jr      nz,sfs_flen
                dec     b                   ; drop it
                ld      c,0                 ; the text carries its own sign/space
                ld      hl,FOUTBUF
sfs_build:                                  ; HL = source, B = length, C = leading spaces
                ld      a,c
                add     a,b                 ; total length
                push    hl                  ; guard the SOURCE               [CURSOR][SRC]
                push    bc                  ; guard B(len),C(leadspace)  [CURSOR][SRC][BC]
                call    str_temp_alloc      ; A=total -> HL=temp desc, DE=body (or 0)
                pop     bc                  ; B=len, C=leadspace             [CURSOR][SRC]
                ex      (sp),hl             ; HL = source; temp desc guarded [CURSOR][TDESC]
                ld      a,d
                or      e
                jr      z,sfs_finish        ; failure -> DE=0, nothing to fill
                ld      a,c
                or      a
                jr      z,sfs_cp
                ld      a,' '
                ld      (de),a
                inc     de
sfs_cp:
                ld      a,(hl)
                ld      (de),a
                inc     hl
                inc     de
                djnz    sfs_cp              ; B = source length (>=1)
sfs_finish:
                pop     hl                  ; HL = temp desc addr                    [CURSOR]
                                            ; restore cursor                            [ ]
                jp      str_pub_ok          ; D-PUBTAIL (-4 B, low region)

; LEFT$(a$,n): the first min(n,len) bytes. Snapshot the source into an owned
; temp, then truncate in place.
; str_arg_empty: an empty string-function first argument (LEFT$()/RIGHT$()/MID$(),
; or a leading ','). Raise the deferred "syntax error" (D-F2-3) like ev_f's ')'/','
; gate, then take the ordinary str_eval_no "not a string operand" exit -- the PRINT/
; LET driver's FPERR check (ems_print / check_expr_errors) then aborts the statement.
; 🎯 D-PENDERR: THIS SITE'S CLOBBER IS WHAT D-TMFP FILED AS THE `r.hex` RESIDUAL
; (spec-basic-tmfp.md §8, defect 2) -- `ld a,4` / `ld (FPERR),a` UNCONDITIONALLY,
; over the top of a pending Division-by-zero. It needed no guard of its own here:
; routing the write through penderr_set fixed it with the same three bytes every
; other writer spends. ⚠️ Defect 1 (the cursor not landing on the closing `)`
; after a string-compare mismatch, which is what sends `HEX$(...)` down this exit
; at all) is UNTOUCHED -- see spec-basic-penderr.md §8.
str_arg_empty:
                ld      a,4
str_arg_err:                                ; A = the code: STRING$'s empty x$ (3) joins
                call    penderr_set
                jp      str_eval_no
; --- str_arg_open: the prologue LEFT$ / RIGHT$ / MID$ all share (D-ARGOPEN) --
; 16 instructions, open-coded three times: the `(` test, both empty-argument
; tests, str_arg_snap, the `,` test, and the temp-address capture. Only what
; FOLLOWS differs -- LEFT$/RIGHT$ evaluate a 0-based count (eval_byte_arg), MID$
; a 1-based position (eval_pos_arg).
;   in:  HL = cursor ON the function's selector byte.
;   out: BC = the owned temp's descriptor address, STRPTR -> it, HL = cursor just
;        past the ',' -- exactly what each open-coded copy produced. Does not
;        return on a malformed call.
; 🔴 THE RANKING SEES TWO SITES, NOT THREE. `str_fn_mid` spells the same four
; exits with `jp` where the other two use `jr`, so the spans are not
; byte-identical and `ngram_sweep` reports a 2-site run. Grep the IDIOM, then
; check the jump form. [[grep-the-idiom-beats-the-clone-ranking]]
; 🔴 AND THE BAIL IS THE WHOLE DESIGN, NOT A DETAIL. str_arg_empty ends
; `jp str_eval_no`, which declines out of the VERB by returning to the verb's
; caller -- so behind a `call` it would run one frame deeper and that `ret` would
; land back inside this helper. [[factoring-a-run-into-a-helper]]
; 🎯 SO THE BAIL IS NOT TAKEN HERE AT ALL: this returns CF CLEAR and each caller
; does its own `jp nc,str_arg_empty`, at the frame depth the open-coded copies
; had. 6 bytes more than discarding the return address with `pop af` -- and the
; 6 bytes buy a guard that a ROW CAN SEE.
; ⚠️ THE `pop af` SHAPE WAS WRITTEN FIRST, AND ITS KNIFE MOVED ZERO ROWS. Not
; because it was wrong, but because it is UNWITNESSABLE: this bail's only outcome
; is a DEFERRED error, and every path that reports one resets SP, so the frame
; damage is erased before any row reads anything.
; [[a-guard-witnessed-only-by-a-deferred-error]]
; Contrast sas_decline below, whose pop IS witnessed -- a DECLINE is not an
; error; the caller RETRIES the operand numerically, and that retry is visible.
; 🔴 D-DEEPEXPR R3 (2026-10-20): A SOURCE NEST HAD NO STACK TEST. A LEFT$/RIGHT$/
; MID$ source is a string expression, so `LEFT$(LEFT$(...` recurses through here
; (str_arg_snap -> str_eval -> str_eval_one -> str_func_ff -> back), 8 B per level,
; and the count argument -- `eval`, which is guarded -- only runs AFTER the inner
; level returns. 20 nested LEFT$ with ~200 B left read NO OUTPUT where the VG-8020
; answers Out of memory (scratchpad/deepexpr_run.out, row lb3). So each level asks
; stk_room first (basic/main.asm: stk_guard's threshold, non-dropping) and a
; refusal is the malformed-call exit every caller already takes: CF clear -> its
; `jr nc,str_arg_empty` -> FPERR 4 (which LOSES to the 6 stk_room deferred,
; first-error-wins) -> str_eval_no. +5 B, +129 T per LEFT$/RIGHT$/MID$ (each
; already costs a snapshot and a slice, well over 1500 T).
str_arg_open:
                call    stk_room            ; D-DEEPEXPR R3: room for one more level?
                ret     nc                  ; no -> ERR 7 deferred, CF clear: malformed
                call    inc_skip_paren     ; D-FNSPACE: past the name AND any
                                            ; spaces before '(' — both references
                                            ; accept `LEFT$ ("AB",1)`
                jr      nz,sao_empty
                inc     hl
                ld      a,(hl)              ; empty first arg -> deferred syntax error
                cp      ')'
                ret     z                   ; Z from an equal cp => CF clear: malformed
                cp      ','
                ret     z                   ; (same: CF clear)
                call    str_arg_snap        ; STRPTR -> an OWNED temp; HL = cursor
                call    skip_comma          ; D-FNSPACE: Z iff ',' — and it
                                            ; SKIPS SPACES first, which a bare
                                            ; `ld a,(hl)` did not. BYTE-NEUTRAL:
                                            ; 3 B for 3 B.
                jr      nz,sao_empty
                inc     hl
                ld      bc,(STRPTR)         ; BC = temp addr (ld rr,(nn) leaves flags)
                scf                         ; CF set = a well-formed call
                ret
sao_empty:
                or      a                   ; CF clear -> the caller raises, in ITS frame
                ret

str_fn_left:
                call    str_arg_open        ; BC = temp addr; HL past the ','
                jr      nc,str_arg_empty    ; malformed -> raise HERE, not one frame in
                push    bc                  ; save it across the numeric eval
                call    eval_byte_arg       ; DE = n, 0..255 (D-MISS-2; or aborts)
                pop     bc                  ; BC = temp addr
                ld      a,(hl)
                cp      ')'
                jr      nz,str_arg_empty
                inc     hl                  ; HL = cursor past ')'
                push    hl                  ; save cursor
                call    str_lr_count        ; HL = temp, E = count (D-SAVECOLON carve)
                ld      d,0                 ; D = start = 0 (LEFT$ -> pure truncation)
                ld      b,h
                ld      c,l                 ; BC = temp addr
                ; 🎯 D-CARVE2: the canonical "slice into a temp and publish" tail,
                ; shared by three MID$/RIGHT$-family arms. Contract: BC = the
                ; source, D = the length, one saved cursor on the stack.
str_slice_done:
                call    str_temp_slice
                jp      sfi_done            ; pop hl (restore cursor), then
                                            ; str_eval_ok -- C4 shared tail (2026-10-03)

; RIGHT$(a$,n): the last min(n,len) bytes. Snapshot, then slice from (len-count).
str_fn_right:
                call    str_arg_open        ; BC = temp addr; HL past the ','
                jr      nc,str_arg_empty    ; malformed -> raise HERE, not one frame in
                push    bc
                call    eval_byte_arg       ; DE = n, 0..255 (D-MISS-2; or aborts)
                pop     bc
                ld      a,(hl)
                cp      ')'
                jr      nz,str_arg_empty
                inc     hl
                push    hl
                call    str_lr_count        ; HL = temp, E = count (D-SAVECOLON carve)
                ld      a,(hl)              ; templen (HL still = temp base)
                sub     e                   ; A = start = templen - count
                ld      d,a                 ; D = start
                ld      b,h
                ld      c,l                 ; BC = temp addr
                jr      str_slice_done      ; D-CARVE2 (-4 B, low region)

; str_lr_count -- the clamp LEFT$ and RIGHT$ both ran verbatim (D-SAVECOLON carve,
; 2026-09-28, -5 B low region; scratchpad/ngram_sweep.py --main ranked the pair).
;   in : BC = the temp copy [len][bytes], DE = n (the requested count)
;   out: HL = temp, (STRPTR) = temp, E = min(templen, n). Clobbers A, BC.
; 🔴 ONLY THIS MIDDLE SPAN IS SHARED, AND THAT IS THE WHOLE CONSTRAINT. The prefix
; before it is just as identical, but its `jr nc/nz,str_arg_empty` exits reach
; str_eval_no, a DEFERRED error that RETURNS to the evaluator -- a helper's return
; address (or a selector flag parked on the stack) would be left under it. This
; span starts after both sites' own `push hl` and has no exit, so a call is exact.
str_lr_count:
                ld      l,c
                ld      h,b                 ; HL = temp addr (kept through the clamp)
                ld      (STRPTR),hl         ; STRPTR = temp (eval may have moved it)
                ld      a,(bc)              ; A = templen
                ld      b,d
                ld      c,e                 ; BC = n (the requested count)
                call    str_min_bc          ; A = min(templen, n) ; preserves HL=temp
                ld      e,a                 ; E = count
                ret

; MID$(a$,p[,n]): count bytes from 1-based position p (or to end if n omitted).
; p<1 is clamped to the start; p>len yields "". Snapshot, then slice.
str_fn_mid:
                call    str_arg_open        ; BC = temp addr; HL past the ','
                jr      nc,str_arg_empty    ; malformed -> raise HERE, not one frame in
                push    bc                  ; [temp]
                call    eval_pos_arg        ; DE = p, 1..255 (D-MISS-2; or aborts).
                                            ; p is the family's one 1-BASED argument:
                                            ; MID$("abc",0) raises where 255 does not.
                push    de                  ; [temp][p]
                call    skip_comma          ; D-FNSPACE: Z iff ',' — and it
                                            ; SKIPS SPACES first, which a bare
                                            ; `ld a,(hl)` did not. BYTE-NEUTRAL:
                                            ; 3 B for 3 B.
                jr      z,sfm_haveN
                ld      de,$FFFF            ; n omitted -> "to end" (clamps to avail)
                jr      sfm_close
sfm_haveN:
                ; ⚠️ the count is checked HERE and not at sfm_close: the 2-arg
                ; form synthesises DE=$FFFF ("to end") below, and $FFFF is not a
                ; legal count — checking it would reject every MID$(a$,p).
                ; (eval_byte_arg reads FAC, not DE, so it cannot see a synthetic
                ; value anyway.)
                inc     hl
                call    eval_byte_arg       ; DE = n, 0..255 (D-MISS-2; or aborts)
sfm_close:
                ld      a,(hl)
                cp      ')'
                jr      nz,sfm_reject2      ; unbalance-safe: pop [temp][p] first
                inc     hl                  ; HL = cursor past ')'
                ld      b,d
                ld      c,e                 ; BC = requested count (n or $FFFF)
                pop     de                  ; DE = p           stack: [temp]
                ld      a,d
                or      e
                jr      z,sfm_start         ; p==0 -> start 0 (DE already 0)
                dec     de                  ; DE = p-1 (desired 0-based start)
sfm_start:
                ex      (sp),hl             ; HL = temp addr; stack top := cursor
                ld      a,(hl)              ; A = templen
                push    hl                  ; [cursor][temp]
                ld      h,a                 ; H = templen (scratch)
                ld      a,d
                or      a
                jr      nz,sfm_clampmax     ; start high byte set -> beyond end
                ld      a,e
                cp      h                   ; start(low) - templen
                jr      c,sfm_starthave     ; start < templen
sfm_clampmax:
                ld      a,h                 ; start = templen (avail becomes 0 -> "")
sfm_starthave:
                ld      d,a                 ; D = clamped start (0..templen)
                ld      a,h                 ; templen
                sub     d                   ; A = avail = templen - start
                call    str_min_bc          ; A = count = min(avail, requested)
                ld      e,a                 ; E = count
                pop     bc                  ; BC = temp addr    stack: [cursor]
                ld      l,c
                ld      h,b
                ld      (STRPTR),hl         ; STRPTR = temp (before the slice clobbers BC)
                jr      str_slice_done      ; D-CARVE2 (-4 B, low region)
sfm_reject2:
                pop     bc                  ; discard p
                pop     bc                  ; discard temp
                jp      str_arg_empty       ; 🎯 D-MIDEXTRA (2026-10-27): Syntax error,
                                            ; deferred -- `MID$("AB",1,1,1)` is 2 on the
                                            ; VG-8020; str_eval_no alone declined, and the
                                            ; caller read the decline as Type mismatch
                                            ; (scratchpad/midextra_run.out)

; ===========================================================================
; MID$ STATEMENT (repack build only): MID$(A$,n[,m])=B$ -- overwrite a substring
; of A$ in place, per docs/spec-basic-mid-statement.md. The FUNCTION MID$(a$,p,n)
; (read) is str_fn_mid above; this is the ASSIGNMENT statement, dispatched from
; exec_stmt (basic/interp.asm) when a statement begins with the MID$ function token
; $FF $83 (the only $FF function that starts a statement).
;
; Contract (§2, oracle-locked black-box on the VG-8020): LEN(A$) NEVER changes; the
; replaced count k = min(m|Lb, Lb, La-n+1); bytes outside [n, n+k) are untouched.
; n<1 / n>255 / n>La / m<0 / m>255 all raise Illegal function call, and anything
; past int16 raises Overflow (D-MISS-2, docs/spec-basic-str-domain.md §3).
;
; ⚠️ This header used to say those were `stmt_error` ("syntax error") because
; "zerobas has no Illegal function call, D-3". That stopped being true long ago
; -- ASC("") raises it, and it is reachable from evaluator depth -- and the stale
; note is precisely why this path funnelled SEVEN distinct reference errors into
; one wrong one. Two of them were not even errors: MID$(A$,1,256)="X" performed
; the assignment and MID$(A$,1,99999)="X" silently did nothing.
; Target is any string variable REFERENCE -- a plain $-suffixed name OR an array
; element with a full subscript list (D-LVFIX, docs/spec-basic-lvsites.md;
; measured on BOTH references, docs/lvsites-msx1-characterization.md m.ary).
; FIELDed lvalues are still deferred, and that half is DECLINED WITH NUMBERS
; rather than merely unpriced -- spec §7 (the FIELDed-READ hook is a third site,
; on str_eval_arr, which nobody had listed). Reuses var_str_type/tgt_parse (LHS),
; tgt_desc (the in-place descriptor, or the element's ARYTAB-relative offset),
; eval (n/m), str_eval (RHS). Clean-room: original code; SEMANTICS from the
; public MSX-BASIC ref. No disassembly.
;
; The dest descriptor address is stashed in MIDS_DEST so the token cursor stays in
; HL through the whole arg parse. ⚠️ MIDS_DEST does NOT alias NUMBUF -- this header
; said it did until D-LVFIX; arrays slice-4a rehomed it to TMISMATCH+1 precisely
; because HEX$/OCT$ moved their digit build INTO NUMBUF (basic/sysvars.inc).
; Entered with HL ON THE SELECTOR BYTE, i.e. past the $FF (PEEK_PREFIX) prefix
; -- program.asm's ex_ff_stmt has already consumed it and fetched the selector
; to dispatch STRIG/INTERVAL, so re-consuming it here would be a second `inc hl`
; nothing reaches. D-SEEDPROSE removed that head (1 B) after the dead-code gate
; learned to read the code column: its only remaining caller was a unit test,
; and tests/ is deliberately not a seed for this gate. Clobbers A, BC, DE, HL.
;
; Arrays slice-4a REVISION: A$/B$ are now [len:1][ptr:2] descriptors, not inline
; [len][bytes]. The write target is A$'s CURRENT body (dereferenced from MIDS_DEST,
; +n-1 for the 1-based position) — MID$ overwrites bytes IN PLACE inside A$'s own
; already-owned heap body (its length never changes, so no realloc is ever needed).
ex_mid_stmt:                                ; (traps T2) entered with HL already on
                                            ; the selector byte, from program.asm's
                                            ; ex_ff_stmt
                ld      a,(hl)
                cp      MIDD_TOKEN          ; must be MID$ ($83); any other $FF here is
                jp      nz,stmt_error       ; not a statement
                call    inc_skip_paren     ; D-FNSPACE: past the name AND any
                                            ; spaces before '(' — both references
                                            ; accept `LEFT$ ("AB",1)`
                jp      nz,stmt_error
                inc     hl                  ; HL -> target var name
                call    req_letter          ; D-MIDEXTRA: a target that is not a NAME
                                            ; is Syntax error -- `MID$(5,1)="X"` is 2
                                            ; on the VG-8020, a numeric NAME 13 (below)
                call    str_target_parse    ; string-var target: type-check, parse,
                                            ; raise -- D-NGRAM9
                ; D-LVFIX (docs/spec-basic-lvsites.md §4.2): the target is any
                ; string variable REFERENCE, array element included -- measured
                ; on BOTH references (docs/lvsites-msx1-characterization.md,
                ; m.ary), which is the one row of that document with two.
                push    hl                  ; [cursor] guard across the lookup
                call    tgt_desc            ; HL -> dest descriptor (STRTAB / STR_EMPTY),
                                            ; or the ARYTAB-RELATIVE OFFSET of the
                                            ; element (§5.1 -- an array target must
                                            ; survive the arg parse's VARPTR)
                ld      (MIDS_DEST),hl      ; stash dest; cursor kept on the stack
                pop     hl                  ; HL = cursor
                call    req_comma           ; ',' required and consumed, spaces skipped
                                            ; first (D-FNSPACE); none -> ERR 2. C5-lite
                                            ; (space plan B-12): this was req_comma's
                                            ; own body, open-coded.
                call    eval_pos_arg        ; DE = n, 1..255 (D-MISS-2; or aborts)
                push    de                  ; [n]
                call    skip_comma          ; D-FNSPACE: Z iff ',' — and it
                                            ; SKIPS SPACES first, which a bare
                                            ; `ld a,(hl)` did not. BYTE-NEUTRAL:
                                            ; 3 B for 3 B.
                ld      e,$FF               ; m omitted -> cap $00FF (D = n's high
                                            ; byte = 0; any D>0 also caps at avail)
                jr      nz,ems_close        ; (ld keeps skip_comma's Z)
                inc     hl
                call    eval_byte_arg       ; DE = m, 0..255 (D-MISS-2; or aborts).
                                            ; Replaces a hand-rolled `bit 7,d` that
                                            ; caught m<0 only, reported it as
                                            ; `syntax error`, and let m=256 through
                                            ; -- MID$(A$,1,256)="X" SILENTLY performed
                                            ; the assignment.
ems_close:
                push    de                  ; [n][m]
                ld      a,(hl)
                cp      ')'
                jr      nz,ems_err_pop2
                ; 🔴 D-MIDSPACE: `call skip_spaces`, NOT `ld a,(hl)`. This was the
                ; ONE separator in ex_mid_stmt with nothing skipping spaces ahead
                ; of it, so `MID$(A$,2) ="X"` — a space before the `=` — read $20,
                ; missed EQ_TOKEN and raised ERR 2 where BOTH references perform
                ; the assignment (measured: refs A$=AXCDE, here A$=ABCDE + ERR 2).
                ; 🎯 THE OTHER FOUR SEPARATORS ARE FINE AND THE READ SAID OTHERWISE.
                ; Their `cp ','`/`cp ')'` are equally bare, and I predicted all of
                ; them would fail; they pass, because `str_target_parse` and `eval`
                ; each leave HL past trailing spaces. The rows found the one site
                ; that had no such guard in front of it, which reading the source
                ; alone got wrong in both directions.
                rst    $10                 ; past ')' AND any spaces (D-INCSKIP)
                cp      EQ_TOKEN            ; '=' crunches to $EF
                jr      nz,ems_err_pop2
                call    str_eval_next       ; D-NGRAM11: past '=', STRPTR -> RHS
                                            ; B$; HL = post-B$ cursor, CF=ok
                ; D-MIDOP (docs/spec-basic-midop.md): NOT a blanket Syntax error.
                ; `jr nc,ems_err_pop2` was the same SHARED TAIL D-PUSING split in
                ; ex_print_using -- str_eval declines both for "there is nothing
                ; here" and for "there is something and it is not a string" -- and
                ; the references answer 24 / 13 / 24 across the three shapes:
                ;   MID$(A$,2)=        -> 24   MID$(A$,2)=:  -> 24
                ;   MID$(A$,2)=5       -> 13   MID$(A$,2)=+  -> 24
                ; 🔴 AND THAT LAST ROW IS WHY THIS IS A DELEGATION AND NOT AN
                ; EOL TEST. D-PUSING's shape (`or a / cp COLON` ahead of str_eval)
                ; gets `+` WRONG: it is neither end-of-line nor ':', so it would
                ; fall through to the type-mismatch arm and answer 13 where both
                ; references say 24. The discriminator is not "is there a byte"
                ; but "can a FACTOR start here", which is ev_f's question.
                ; 🎯 SO ASK THE ROUTINE THAT ALREADY ANSWERS IT. els_tc_common
                ; (basic/missing.asm, D-MISS-1) clears ERRMARK, evaluates the
                ; operand NUMERICALLY and lets check_expr_errors decide: a
                ; deferred FPERR aborts with its own code (24 for a missing
                ; factor, via ev_f_missop), a clean parse means a real numeric
                ; RHS -> ERR 13, and the $DD landmark means nothing parsed ->
                ; ERR 2. It is what already makes `A$=` and `A$=+` read 24, and
                ; files.asm:724 records that a THIRD entry point costs nothing:
                ; each caller pops its own saved words and enters the tail.
                ; ~~`jp nc` here cost +1 B over the `jr`~~ 🟢 D-CARVE6
                ; (2026-09-08): it IS the `jr` now. The extra byte was paid
                ; because the target was out of reach when this landed; later
                ; carves moved the low region under it and brought it back in.
                ; Route D RENEWS -- that is this line, twice.
                jr      nc,ems_typecheck
                ; --- compute + copy. HL = the continue cursor (keep it). ---
                ; n<1/n>255 and the La>=n check, the avail/cap derivation, the
                ; final k=min(cap,Lb), and the actual byte-overwrite ALL moved
                ; to the sub-ROM tenant (sub/strheap.asm sh_mid_store, op=9,
                ; SH_ERR=3 signals the range error) — shape-C follow-up, this
                ; low region ran out of room for the arithmetic too.
                pop     de                  ; DE = m           stack: [n]
                ex      (sp),hl             ; HL = n, stack: [cursor] (guarded
                                            ; across the call)
                push    hl                  ; [cursor][n]: n (full 16-bit; sub-side range-
                                            ; checks 1..255 itself)
                push    de                  ; [cursor][n][m]
                ld      hl,(STRPTR)
                push    hl                  ; [cursor][n][m][B$]: read FIRST, as before
                call    tgt_desc_fix        ; HL = the stashed dest, corrected for any
                                            ; ARYTAB move the arg parse caused (§5.1);
                                            ; a scalar target comes back verbatim
                push    hl                  ; [cursor][n][m][B$][A$]
                call    mid_own             ; D-READREF: a body in the program text is
                                            ; copied into the heap first
                pop     de                  ; DE = A$ (blk+4)
                pop     hl                  ; HL = B$ (blk+2)
                pop     bc                  ; BC = m (blk+6)         [cursor][n]
                ld      a,9
                call    sh_go               ; op = 9 (MID_STORE); n is blk+10
                pop     bc                  ; drop n                 [cursor]
                jp      z,pop_exec          ; ERR 0: HL = continue cursor; op 9 writes
                                            ; only 0 / 3 (sh_go: Z iff 0), so the range
                                            ; error (n<1/n>255/n>La) falls into
ems_range:
                ; The only range error the tenant still reports is n > LEN(A$)
                ; (n<1 / n>255 are now rejected by eval_pos_arg before the tenant
                ; is called). The reference raises Illegal function call for it --
                ; measured, MID$(A$,4)="X" and MID$(A$,255)="X" on a 3-char A$ --
                ; not the `syntax error` the D-3 note above assumed was forced.
                pop     hl                  ; discard the guarded cursor -> stack balanced
                jp      gb_illegal          ; Illegal function call (ld a,5 / jp
; mid_own -- D-READREF (2026-10-07): A$'s body must be the HEAP's before MID$
; writes into it. A READ string points at the DATA text (basic/vars.asm
; tgt_store_ref), and on the VG-8020 a MID$ into one does NOT reach the program --
; a re-READ gives the old bytes and LIST shows them (probes/basic/
; basic_probe_readref.py `mid` / `list`). Nothing else with a length points below
; VARTAB, so a body there is copied into a fresh heap body (op 0) and A$ repointed;
; a heap body or a FIELD buffer is written in place as before. No room is 14 (the
; VG-8020's `midoom`: `Out of string space in 16`, the MID$ line).
;   in: HL = A$'s descriptor. Clobbers A, BC, DE, HL, IX, IY.
mid_own:
                ld      c,(hl)              ; C = La
                inc     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = A$'s body, HL = A$+2 (D-WSZERO S16:
                                            ; it rides the stack across the nested op 0)
                ld      a,c
                or      a
                ret     z
                push    hl                  ; [A$+2]
                ld      hl,(VARTAB)
                scf
                sbc     hl,de               ; CF iff body >= VARTAB
                pop     hl                  ; HL = A$+2 (pop keeps the flags)
                ret     c                   ; at/above VARTAB: owned
                push    hl                  ; [A$+2]
                ld      l,c                 ; blk+0 = La
                xor     a                   ; op 0 (ALLOC): HL = the fresh body
                call    sh_go               ; DE (the text body) and C (La) come back
                                            ; as passed: op 0 writes only PTR / ERR
                ex      de,hl               ; HL = the text body, DE = the fresh one
                ex      (sp),hl             ; HL = A$+2, [text body] (flags kept)
                jr      nz,mo_oom
                ld      (hl),d
                dec     hl
                ld      (hl),e              ; A$ -> its own heap copy
                pop     hl                  ; HL = the text body
                ld      b,0                 ; BC = La
                ldir
                ret
mo_oom:
                pop     hl                  ; discard the text body -> stack balanced
                ld      a,14                ; Out of string space
                jp      raise_error         ; resets SP
                                            ; raise_error: interp.asm's tail, C4 2026-10-03)
; D-MIDOP: the MID$ entry to D-MISS-1's shared numeric-RHS typecheck. It pops
; [n][m] and enters els_tc_common at statement-handler depth, exactly as
; els_typecheck pops its dest key and elas_typecheck pops [OFFSET].
; ⚠️ THE POPS ARE KEPT DELIBERATELY, AND TWO RECORDS DISAGREE ABOUT WHETHER THEY
; ARE NEEDED. files.asm:732 says raise_error's own `ld sp,(SAVSTK)` discards
; whatever is left, and the code agrees -- the trap arm resets SP at
; interp.asm:1022 and the abort arm through fre_abort_low (interp.asm:1731,
; citing 4d35b6d / docs/spec-basic-abort-depth.md). The
; abort-chain-returns-into-caller note says the opposite, and it predates that
; fix. Popping is correct under BOTH readings and costs 2 B, so this does not
; bet a stack on which record is current; the discrepancy is FILED rather than
; resolved here.
ems_typecheck:
                pop     de                  ; discard m
                pop     de                  ; discard n
                jp      els_tc_common       ; -> 24 / 13 / 2, decided by eval
ems_err_pop2:
                pop     de                  ; discard m
ems_err_pop1:
                pop     de                  ; discard n
                jp      stmt_error

; ===========================================================================
; string-functions S2 (repack build only): HEX$/OCT$/SPACE$ (Group A, $FF-
; prefixed) + STRING$ ($E3, Group B) + INSTR ($E5, Group C) — the five verbs of
; docs/spec-basic-string-functions.md. Group A mirrors CHR$/STR$ above (reached
; via str_func_ff); Group B/C are single-byte reserved-word tokens dispatched
; from str_eval (basic/strvar.asm) and ev_f (basic/expr.asm) respectively.
;
; Clean-room: original code. Verb SEMANTICS (unsigned-16 HEX$/OCT$ text, STRING$
; numeric-code-vs-string-first-byte dual form, INSTR 1-based search) are from the
; public MSX-BASIC language reference, oracle-locked black-box on the Philips
; VG-8020 (S2 gate). The STRMAX clamp / negative-length error (D-3) are zerobas's
; own design, consistent with the rest of the engine. No disassembly.
; ===========================================================================

; --- str_fn_hex / str_fn_oct / str_fn_bin: the RADIX-TEXT family -------------
; HEX$(n) / OCT$(n) / BIN$(n) -> text of n viewed as an UNSIGNED 16-bit value,
; base 16 / 8 / 2, no leading zeros, always >=1 digit (D-2: HEX$(0)="0",
; HEX$(-1)="FFFF"). The digit builds live in the sub-ROM tenant
; (sub/strheap.asm sh_hex_build/sh_oct_build/sh_bin_build, ops 6/7/14) —
; shape-C move, this low region ran out of room for them; only the argument
; PARSE (which needs `eval`) stays main-side. Thin glue mirrors str_temp_alloc.
;
; ONE BODY, THREE ENTRY STUBS (docs/spec-basic-binfre.md §3). These were two
; near-identical 43 B / 38 B copies, and the 5-byte difference between them WAS
; D-BF-2 — str_fn_oct was str_fn_hex minus the checked conversion. A third copy
; for BIN$ could not fit: they are low-region, and the low region had 7 B free.
; Collapsing pays for BIN$ out of its own family AND writes the two argument
; checks once for all three instead of three times (or, as before, once and not
; at all).
;
; The op byte is the only parameter, carried in C across `eval` on the stack —
; NOT in SH_OP, which a nested string operation inside the argument would
; clobber (`HEX$(LEN(A$))`).
str_fn_hex:
                ld      c,6                 ; op = 6 (HEX_BUILD)
                jr      str_fn_radix
str_fn_oct:
                ld      c,7                 ; op = 7 (OCT_BUILD)
                jr      str_fn_radix
str_fn_bin:
                ld      c,14                ; op = 14 (BIN_BUILD; 8 is sh_fill)
str_fn_radix:                               ; C = the build op (rst $10 keeps it)
                call    inc_skip_paren     ; D-FNSPACE: past the name AND any
                                            ; spaces before '(' — both references
                                            ; accept `LEFT$ ("AB",1)`
                jp      nz,str_arg_empty
                inc     hl
                push    bc                  ; [op] across eval
                call    eval_addr           ; DE = n: the ADDRESS domain, CHECKED
                                            ; (FPERR on overflow) — overrides eval's
                                            ; silent DE when n was a float.
                                            ; D-BF-2: OCT$ never had this, so
                                            ; OCT$(65536) silently printed OCT$(0).
                ; D-BF-1 stood HERE and is GONE with D-PENDERR (-17 B, low region).
                ; It promoted a deferred TMISMATCH into FPERR=10 -- "an argument error
                ; is EITHER flag, and a deferred TMISMATCH alone is invisible to the
                ; PRINT item driver, which checks only FPERR" (`PRINT HEX$("A")`
                ; printed a silent 0 while `X=HEX$("A")` said "type mismatch") -- and
                ; it hand-rolled first-error-wins around the promotion.
                ; 🎯 THAT WAS THE MERGE, WRITTEN OUT AT ONE CALLER. The mapping it
                ; encoded (TMISMATCH == FPERR 10) is now the only representation there
                ; is, and the guard it hand-rolled is penderr_set's contract, so both
                ; halves are the normal case and neither costs a byte here.
                ld      a,(hl)
                cp      ')'
                jp      nz,sfg_reject1      ; pops [op], then str_arg_empty
                inc     hl                  ; HL past ')'
                ex      (sp),hl             ; [cursor]; L = the op
                ld      a,l                 ; op = 6 HEX / 7 OCT / 14 BIN
                ld      b,d
                ld      c,e                 ; BC = the number (blk+6)
                ; ...and FALLS THROUGH into shx_op_tail (the `jr` here was to the
                ; very next instruction: -2 B, GA-CROSS-ROMSCAN)

; --- shx_op_tail / shx_tail: the sub-ROM string-op RESULT tail (D-NGRAM4) ---
; Four verbs ended with the identical 10 B run -- CHR$ (str_fn_chr),
; HEX$/OCT$/BIN$ (str_fn_radix), SPACE$ (str_fn_space) and STRING$ (sfg_close):
; 🔴 NAMED FROM THE ENCLOSING LABEL, NOT FROM NEARBY COMMENTS. The first version
; of this list read "SPACE$ (:733)" because the sweep reports LINE NUMBERS and I
; read the verb off the surrounding prose. :733 is CHR$. The mistake was caught
; by a knife: K-N4B moved five rows and none of them was the one I thought
; covered that site -- because CHR$ had NO ROW AT ALL.
;     call call_strheap / call shx_finish / pop hl / jp str_eval_ok
; and THREE of them set SH_OP immediately before it, so `shx_op_tail` is a 3 B
; second ENTRY rather than a second body -- the same shape D-NGRAM3 found at the
; lineedit sites. 49 B of sites becomes a 13 B body plus four 3 B jumps: -24 B.
;   in:  shx_op_tail -- A = the op code.  shx_tail -- SH_OP already set.
;        Each caller has pushed its own cursor guard; the `pop hl` here restores
;        it, exactly as the open-coded form did (the fourth site guards with
;        `push ix` and pops it into HL -- byte-identical, and deliberate).
;   out: never returns -- str_eval_ok owns the exit.
; 🔬 The four sites were enumerated at INSTRUCTION level and checked for an
; INTERIOR LABEL (none): one of them carries comment lines inside the run, so a
; line-adjacent grep sees three.
shx_op_tail:
shx_tail:
                call    sh_go_g             ; HL = the slot, A = ERR (D-DEEPEXPR: a skip
                                            ; publishes STR_EMPTY through shx_finish)
                call    shx_finish
                jr      sfi_done            ; pop hl (the caller's cursor guard), then
                                            ; str_eval_ok -- C4 shared tail (2026-10-03)

; shx_finish: shared HEX_BUILD/OCT_BUILD result tail. Reads SH_ERR/SH_PTR
; (set by either op), maps SH_ERR=2 (temp-descriptor stack full) to FPERR=9
; and STR_EMPTY, else publishes SH_PTR as the new STRPTR (SH_ERR=1, heap OOM,
; is honoured too — FPERR=6 — though a <=6-byte alloc essentially never hits
; it). Clobbers A, HL.
shx_finish:                                 ; A = ERR and Z from sh_go, HL = the slot
                jp      z,shxf_ok           ; D-DUPSPAN2: widened from `jr` --
                cp      2                   ; the alias targets are in sst_*'s
                jp      z,shxf_overflow     ; span, out of `jr` reach from here
                ld      a,FPERR_STROOM
                call    penderr_set         ; heap OOM (sysvars.inc)
                jp      sh_publish          ; D-CARVE2 (-4 B, low region)
; D-DUPSPAN2: an ALIAS, not a second copy -- byte-identical to sst_ok,
; and POSITION-INDEPENDENT by tools/dupspan_indep.py (terminates, no
; escaping relative jump, not entered by fallthrough, same ROM region).
; The NAME and every call site survive; un-alias here for a distinct face.
shxf_ok         equ     sst_ok
; D-DUPSPAN2: an ALIAS, not a second copy -- byte-identical to sst_overflow,
; and POSITION-INDEPENDENT by tools/dupspan_indep.py (terminates, no
; escaping relative jump, not entered by fallthrough, same ROM region).
; The NAME and every call site survive; un-alias here for a distinct face.
shxf_overflow   equ     sst_overflow

; str_fn_space: SPACE$(n) -> n space ($20) bytes, clamped to STRMAX (D-3); a
; negative n is a function error (own-design, mirrors ASC ""). The clamp reuses
; str_min_bc (A=STRMAX ceiling, BC=n), exactly like LEFT$/RIGHT$/MID$'s count clamp.
; Length is known upfront -> allocate once, fill directly.
str_fn_space:
                call    inc_skip_paren     ; D-FNSPACE: past the name AND any
                                            ; spaces before '(' — both references
                                            ; accept `LEFT$ ("AB",1)`
                jp      nz,str_arg_empty
                call    inc_eval            ; DE = n; HL advanced
                ld      a,(hl)
                cp      ')'
                jp      nz,str_arg_empty
                inc     hl                  ; HL past ')'
                push    hl                  ; guard cursor (across call_strheap below)
                call    get_byte_arg        ; D-F2-2 stage B: SPACE$ count is a byte 0..255
                                            ; (>int16 ERR 6, 256.. ERR 5, negative ERR 5) —
                                            ; replaces the old clamp-to-STRMAX + D-3 negative
                                            ; check (STRMAX=255 == the byte ceiling, so an
                                            ; in-range count is unchanged). A = fill count.
                ld      l,a                 ; blk+0 = the count
                ld      e,' '               ; blk+4 = the fill byte
                ld      a,8                 ; op = 8 (FILL) -- shape-C follow-up:
                                            ; the fill loop moved to the sub-ROM
                                            ; tenant (sub/strheap.asm sh_fill),
                                            ; this low region ran out of room
                jr      shx_op_tail

; str_fn_inkey: INKEY$ -> a 0- or 1-character string. Samples the keyboard ONCE,
; strictly non-blocking (D-2): CHSNS ($009C) reports Z = buffer empty / NZ = a key
; waits; on a key, CHGET ($009F) consumes it (non-blocking here because CHSNS just
; saw it). No arguments/parens to parse -- HL just steps past the INKEY_TOKEN.
; Control keys pass through as their raw code (D-5, own-design). Entered from
; str_eval_one (basic/strvar.asm) with HL ON the INKEY_TOKEN ($EC).
str_fn_inkey:
                inc     hl                  ; past the INKEY_TOKEN; no args to parse
                push    hl                  ; guard cursor                            [CURSOR]
                call    zb_chsns            ; Z = keyboard buffer empty (D-KEYSHIFT)
                jr      z,sfi_empty
                call    CHGET               ; A = the waiting key
                push    af                  ; guard key byte                            [CURSOR][KEY]
                ld      a,1
                call    str_temp_alloc      ; -> HL=temp desc, DE=body(1B, or 0 on fail)
                ld      (STRPTR),hl
                ld      a,d
                or      e
                jr      z,sfi_nowrite       ; failure -> DE=0
                pop     af                  ; A = key byte                              [CURSOR]
                ld      (de),a
                jr      sfi_done
sfi_nowrite:
                pop     af                  ; discard the guarded key byte (balance)     [CURSOR]
sfi_done:                                   ; C4 shared tail (2026-10-03): str_pub_ok,
                pop     hl                  ; restore cursor                                [ ]
                jp      str_eval_ok         ; str_slice_done, shx_tail and graphics.asm's
sfi_empty:                                  ; spr_rd_done end here too (one copy)
                xor     a
                call    str_temp_alloc      ; A=0 -> HL=temp desc(len0,ptr0), DE=0
                                            ; restore cursor                                [ ]
                jp      str_pub_ok          ; D-PUBTAIL (-4 B, low region)

; str_fn_string: STRING$(n,c) / STRING$(n,x$) -> n copies of a single fill
; byte, clamped to STRMAX (D-3). The fill byte is resolved by PROBING the 2nd
; argument's type (D-4, the established str_eval-CF pattern): a string x$
; contributes its first byte (empty x$ is Illegal function call, AFTER the `)`
; test -- D-STRINGEMPTY); otherwise it is re-parsed numerically via `eval` and the low
; byte is the character code. Entered from str_eval_one (basic/strvar.asm) with
; HL ON the STRING_TOKEN byte itself ($E3) -- a single-byte reserved-word
; token (Group B), unlike the $FF-prefixed Group A verbs above. Length known
; upfront -> allocate once, fill directly.
str_fn_string:
                call    inc_skip_paren     ; D-FNSPACE: past the name AND any
                                            ; spaces before '(' — both references
                                            ; accept `LEFT$ ("AB",1)`
                jp      nz,str_arg_empty    ; BUG C class (Fable 2026-07-17): STRING$ is a
                                            ; SINGLE-byte token ($E3) -> its malformed re-
                                            ; drive never reaches ev_ff_strnum's deferred
                                            ; error, so a bare str_eval_no INFINITE-LOOPED
                                            ; (screen fills with " 0"). Defer FPERR=4 here.
                inc     hl
                call    eval_byte_arg       ; D-F2-2 stage B: STRING$ count is a byte 0..255
                                            ; (>int16 ERR 6, 256.. ERR 5, negative ERR 5) —
                                            ; replaces the clamp + D-3 negative hang-fix
                                            ; (STRMAX=255 == byte ceiling). A = fill count.
                push    af                  ; guard the count                  [count]
                call    skip_comma          ; D-FNSPACE: Z iff ',' — and it
                                            ; SKIPS SPACES first, which a bare
                                            ; `ld a,(hl)` did not. BYTE-NEUTRAL:
                                            ; 3 B for 3 B.
                jr      nz,sfg_reject1      ; unbalance-safe: pop [count] first
                inc     hl
                ; --- resolve the fill byte: probe for a string 2nd arg (D-4) ---
                call    str_eval            ; CF set -> string 2nd arg; STRPTR->desc
                jr      c,sfg_str2
                ; numeric 2nd arg: re-parse via eval, CHECK the byte domain (D-F2-2 stage B)
                call    eval_byte_arg       ; A = E = char code 0..255 (256.. ERR 5, >int16
                                            ; ERR 6); HL advanced past it
sfg_close:                                  ; E = fill byte, HL = cursor       [count]
                ld      a,(hl)
                cp      ')'
                jr      nz,sfg_reject1      ; unbalance-safe: pop [count] first
                inc     hl                  ; HL = cursor, past ')'
                ex      (sp),hl             ; [cursor]; H = the count (pushed as A)
                ld      l,h                 ; blk+0 = the count (sh_go puts the op in H)
                ld      a,8                 ; op = 8 (FILL) -- shape-C follow-up
                                            ; (same move as SPACE$ above)
                jp      shx_tail
sfg_reject1:
                pop     af                  ; discard [count] (or str_fn_radix's [op])
                jp      str_arg_empty       ; BUG C class: defer FPERR=4 (missing ',' / ')')
                                            ; -- STRING$ single-byte token would else hang
sfg_str2:
                push    hl                  ; guard the str_eval-advanced cursor across
                                            ; the descriptor dereference (which uses HL)
                ld      hl,(STRPTR)
                ld      a,(hl)              ; length of the string operand
                or      a
                jr      z,sfg_str2_empty    ; empty x$ -> error (mirrors ASC "")
                inc     hl
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = ptr (body address)
                ld      a,(de)              ; fill byte (first byte of x$)
                ld      e,a                 ; blk+4 = the fill byte
                pop     hl                  ; HL = cursor (restored)
                jr      sfg_close
sfg_str2_empty:
                ; 🎯 D-STRINGEMPTY (2026-10-27): an empty x$ is Illegal function
                ; call on the VG-8020, not Syntax error -- but a missing `)` still
                ; wins: `STRING$(2,""` is 2 there, `STRING$(2,"")` and
                ; `STRING$(2,"")X` are 5 (scratchpad/stringempty_run.out). So the
                ; `)` is tested first, as sfg_close does, and FPERR 3 deferred.
                pop     hl                  ; HL = cursor (restored)
                ld      a,(hl)
                cp      ')'
                jr      nz,sfg_reject1      ; no `)`: Syntax error wins
                pop     af                  ; discard [count]
                ld      a,3                 ; Illegal function call (deferred)
                jp      str_arg_err         ; penderr_set, then str_eval_no

; ev_f_instr: INSTR([p,]a$,b$) -> 1-based position of b$ within a$, searching
; from position p (default 1); 0 if not found. Entered from ev_f (basic/expr.asm)
; with IX on the INSTR_TOKEN byte ($E5, single-byte reserved word -- Group C).
; Bridges IX<->HL exactly like ev_str_arg/ev_ff_cvi.
;
; The optional leading numeric p is distinguished from the two-argument form by
; PROBING the first argument's type via str_eval (D-5): CF set -> it IS a$ (the
; two-arg form; p defaults to 1); CF clear -> it's the numeric p (reparse via
; `eval`, then read ',' then str_eval for a$).
;
; Both a$ and b$ are snapshotted (str_snapshot_ro: a scalar variable or an owned
; temp is used as it is, D-CATCOPY; anything else is copied) right after parsing, so evaluating the second string can't clobber
; the first via STRSCR or the token stream -- the same snapshot-then-operate
; discipline the substring verbs and ev_rel_str's LHS snapshot use. p<1 is a
; function error (ev_f_err); the search itself (empty b$ / p past LEN(a$)) is
; instr_search's contract below.
;
; IX/IY are repurposed as the two temp-descriptor pointers (aT/bT) for
; instr_search once parsing is complete -- the real token cursor is safe in HL
; by then, and is bridged back into IX only right before the return, so ev_f's
; "IX = cursor advanced past the call" convention still holds.
ev_f_instr:
                call    ixsp_paren_req     ; D-IXSP
                                           ; BUG C class: INSTR without '(' -> deferred
                                            ; syntax error (was silent ev_f_err)
                call    ixsp                ; D-IXSP
                call    str_eval_ix            ; CF set -> a$ (2-arg form); STRPTR->desc
                jr      c,efi_have_a
                ; --- not a string: the leading numeric p (3-arg form) ---
                call    eval_pos_arg        ; DE = p, 1..255 (D-MISS-2; or aborts)
                push    de                  ; guard p                             [p]
                call    skip_comma
                jp      nz,ev_f_empty       ; 3-arg form missing ',': ev_f_empty RAISES
                                            ; (D-DEFERRSTUDY family 3) and raise_error
                                            ; re-bases SP, so [p] needs no discard.
                                            ; 🔴 If ev_f_empty ever defers again, the
                                            ; three INSTR sites that jump to it with
                                            ; words pushed break (D-REREAD batch 6).
                call    str_eval_next       ; D-NGRAM11: past ',', STRPTR -> a$;
                                            ; HL advanced; CF=ok
                jr      nc,efi_tm_p         ; D-INSTRTM: a$ present but NOT a string
                jr      efi_dup_a
; --- D-INSTRTM: an operand that is NOT A STRING is a TYPE MISMATCH ----------
; (docs/spec-basic-instrtm.md.) These two tails used to be reached BOTH by the
; `jr nz` that means "the ',' is missing" and by the `jr nc` that means "there IS
; an operand and it is not a string", and both answered `Syntax error`. Both
; references answer 13 for the second and 2 for the first, so the tail had to be
; SPLIT -- retargeting it would have broken five malformed shapes that are
; correct today. [[a-shared-tail-is-not-a-decision]]
; 🎯 AND THE RAISE COMES AFTER THE OPERAND IS EVALUATED, which is the whole
; lesson of D-LEFTTM: `ev_f_defer` is first-error-wins, so a fault the operand
; itself raises keeps the answer and this one is dropped.
; `INSTR("ABCDE",0*(1/0)+1)` is Division by zero on both references, not 13.
; Arming it BEFORE the evaluation is the mistake D-NGRAM8 made, and D-LEFTTM's
; K-LT2 pins it.
; ⚠️ The discards use DE, not HL: HL is the cursor, still ON the operand, and
; `eval` needs it.
efi_tm_pa:
                pop     de                  ; discard [p]                         [aT]
efi_tm_p:
                pop     de                  ; discard [aT] (or [p], from efi_tm_p) [ ]
                call    eval                ; the operand, numerically -- it arms its
                                            ; OWN fault first if it has one
                ld      e,FPERR_TYPEMM      ; -> ERR 13, unless the operand beat us
                jp      ev_f_defer
efi_have_a:
                ld      de,1                ; default p = 1 (two-arg form)
                push    de                  ; guard p                             [p]
efi_dup_a:
                push    hl                  ; guard cursor (past a$)              [p][cursor]
                call    str_snapshot_ro     ; HL = aT (a$ snapshot); STRPTR=aT.
                                            ; D-CATCOPY: a scalar or an owned temp is
                                            ; used as it is, not copied: INSTR only
                                            ; reads it (basic/strvar.asm).
                pop     de                  ; DE = cursor                         [p]
                ex      (sp),hl             ; HL = p; top := aT                   [aT]
                push    hl                  ;                                     [aT][p]
                ex      de,hl               ; HL = cursor (restored)
                call    skip_comma          ; D-FNSPACE: Z iff ',' — and it
                                            ; SKIPS SPACES first, which a bare
                                            ; `ld a,(hl)` did not. BYTE-NEUTRAL:
                                            ; 3 B for 3 B.
                jp      nz,ev_f_empty       ; malformed (raises; SP re-based, see above)
                call    str_eval_next       ; D-NGRAM11: past ',', STRPTR -> b$;
                                            ; HL advanced; CF=ok
                jr      nc,efi_tm_pa        ; D-INSTRTM: b$ present but NOT a string
                push    hl                  ; guard cursor (past b$)              [p][aT][cursor]
                call    str_snapshot_ro     ; HL = bT (b$ snapshot); STRPTR=bT
                                            ; (D-CATCOPY, as a$ above)
                ex      (sp),hl             ; HL=cursor(restored); top:=bT        [aT][p][bT]
                ld      a,(hl)
                cp      ')'
                jp      nz,ev_f_empty       ; missing ')' (raises; SP re-based, see above)
                inc     hl                  ; HL = cursor, past ')'
                ; --- everything parsed: search ---
                pop     de                  ; DE = bT                             [aT][p]
                pop     bc                  ; BC = p                              [aT]
                ; D-MISS-2: the two hand-rolled p<1 tests that stood here (a
                ; `bit 7,b` and an `or c`, each with its own IX-restore dance and
                ; `jp ev_f_ifc`) are GONE -- eval_pos_arg above subsumes both and
                ; adds the two stages they never had. They were half a rule:
                ; INSTR(256,a$,b$) sailed past them and returned 0, a silent
                ; "not found" where the reference raises, and INSTR(99999,...)
                ; reported Illegal function call where it raises Overflow.
                ; Deleting them is why folding INSTR into this slice made it 20 B
                ; CHEAPER rather than more expensive.
efi_p_ok:
                ; Thin main-ROM glue for the string-heap tenant's
                ; INSTR_SEARCH op (mirrors str_temp_alloc) — the search body
                ; (now dereferencing aT/bT's [len:1][ptr:2] to find their
                ; CURRENT bodies, was inline-bodied) moved to the sub-ROM
                ; (sub/strheap.asm sh_instr_search) once this low region ran
                ; out of room for it.
                ex      (sp),hl             ; HL = aT; top := the real cursor     [cursor]
                                            ; (DE = bT, BC = p)
                ld      a,11
                call    sh_go_g             ; op = 11 (INSTR_SEARCH): HL = the result
                ; 🎯 D-DEEPEXPR P3 (2026-10-20): a SKIPPED search must read 0, not
                ; STR_EMPTY's address -- `ex de,hl` would hand back 18648, a
                ; plausible position, with ERR 7 pending behind it. The skip leaves
                ; DE = 0 already, so it only has to step over the exchange. +2 B.
                jr      nz,efi_skipped      ; (the op itself never reports an ERR)
                ex      de,hl               ; DE = result (1-based match / 0)
efi_skipped:
                pop     ix                  ; IX = cursor (bridge back to ev_f's convention)
                jp      flt_int_result      ; INSTR returns an int even when a float rode
                                            ; in via p or a nested STR$ arg (float.asm F1;
                                            ; clobbers A only, then ret to the caller)

; --- ems_print / ems_fallback: PRINT's string-item tails (basic/print.asm) -----
; exps_print and exps_fallback land here. ems_print prints the string str_eval
; just read (the operand start is still pushed); ems_fallback hands a declined
; item to exp_num with the cursor str_eval restored. (exp_maybe_strfn, PRINT's
; separate entry for $FF / STRING$ / INKEY$ items, went in D-PRSTRFN: every item
; now enters through exp_strvar.)
ems_print:
                pop     de                  ; drop the saved operand-start (balances the
                                             ;  push above; str_eval already clobbers DE)
                call    check_fperr_only    ; D-F2-1: e.g. print hex$(65536.) -- the
                                            ; overflow happens inside str_eval's HEX$
                                            ; argument conversion (fac_to_int_addr)
                push    hl                  ; print_strval clobbers HL (token cursor)
                call    print_strval_rel    ; D-TEMPPOL: print, then pop the item's temp
                pop     hl
                jp      exp_loop
ems_fallback:
                pop     hl                  ; balance the operand-start push (str_func_ff
                                             ;  restores HL to the $FF on failure, so this
                                             ;  is the same cursor exp_num sees un-gated)
                jp      exp_num

; ===========================================================================
; string-compare S2 (repack build only): the six relational operators on two
; string operands (spec-basic-string-compare.md). Reused spine: ev_rel (expr.asm)
; already factors a comparison into "requested bits" (relop_bit + the compound-
; form merge) AND'd against an "actual bit" (1=less/2=equal/4=greater) from the
; two operands -- today cmp16_bits. This substitutes ONE thing: an UNSIGNED-BYTE
; string comparator (str_cmp_bits) producing that same 1/2/4 encoding, plus a
; type-mismatch signal (D-2) when a string meets a non-string.
;
; Clean-room: original code. Comparison SEMANTICS (unsigned byte-by-byte,
; shorter-is-less, case-sensitive, §2 D-3) are the standard MSX-BASIC string-
; ordering contract (public language reference), oracle-locked black-box on the
; Philips VG-8020 (probes/basic/basic_probe_str_cmp.py) -- not assumed. The
; relation-bit encoding is zerobas's own (matches cmp16_bits, expr.asm). No
; disassembly.
; ===========================================================================

; --- relop_peek: is A a relational-operator token? --------------------------
; UNCHANGED from pre-4a — a straight range test over the established relop
; token equates (basic/sysvars.inc); no descriptor-format dependency.
; in: A = the current token byte (caller peeks via `ld a,(hl)`; not consumed).
; out: ZF=1 iff A is one of the three contiguous relop tokens GT_TOKEN ($EE) /
;      EQ_TOKEN ($EF) / LT_TOKEN ($F0). ZF=0 otherwise. Does not touch
;      HL/DE/BC/IX -- only A and flags.
relop_peek:
                sub     GT_TOKEN            ; A -= $EE (0/1/2 for the three relops)
                cp      3                   ; CF=1 iff A(orig)-$EE < 3, i.e. in range
                jr      c,rp_yes
                or      1                   ; not in range -> force A nonzero -> ZF=0
                ret
rp_yes:
                cp      a                   ; in range -> force ZF=1
                ret

; --- str_cmp_bits: UNSIGNED byte-by-byte compare of two descriptors --------
; in: HL = lhs descriptor, DE = rhs descriptor.
; out: A = 1 (lhs<rhs) / 2 (equal) / 4 (lhs>rhs) -- the same encoding cmp16_bits
;      (expr.asm) produces for the numeric path, so the caller's `and c` (requested
;      vs actual) is unchanged. Compares corresponding bytes by raw unsigned value;
;      at the first differing byte the smaller byte's string is less (spec §2.1);
;      if all shared bytes match, the SHORTER string is less (§2.2); same length +
;      all bytes equal -> equal (§2.3). Case-sensitive: no folding (§2.4).
; Preserves BC (the caller keeps its requested-bits register in C across the call).
; Clobbers DE, HL, IX, flags.
;
; Thin main-ROM glue for the string-heap tenant's CMP op (mirrors
; str_temp_alloc) — the byte-compare mechanics (now dereferencing each
; descriptor's [len:1][ptr:2] to find the CURRENT body, was inline
; [len][bytes]) moved to the sub-ROM (sub/strheap.asm sh_cmp_bits) once this
; low region ran out of room for it.
str_cmp_bits:
                ld      a,10                ; op = 10 (CMP): HL = lhs, DE = rhs. The
                jp      sh_go_g             ; bits come back in A; BC (the caller's C,
                                            ; the requested bits) comes back untouched:
                                            ; op 10 writes no blk+6 (D-WSZERO S16).
                                            ; D-DEEPEXPR: guarded -- a skip's A = 6
                                            ; reads as -1/0 at the caller's `and c`,
                                            ; with ERR 7 pending; no consumer raises
                                            ; on a relational value (P3)

; --- type_mismatch_set: D-2's comparator-level signal ------------------------
; UNCHANGED from pre-4a. A string on one side of a relational and a non-string
; on the other (or a bare string LHS with no relop at all) -- sets ERRMARK
; (the generic expression-error landmark, ev_f_err's convention) plus the
; distinct TMISMATCH marker, and yields 0 (false). This does NOT abort the
; line itself: ev_rel has no mid-expression unwind, so the real abort happens
; at the STATEMENT boundary, once eval() returns, via the repack-gated
; post-eval check in ex_if / the numeric-assignment / PRINT-item drivers
; jumping to type_mismatch_error (interp.asm).
;
; --- D-TMFP: OF TWO PENDING FAULTS, THE ONE THAT HAPPENED FIRST IS REPORTED --
; (docs/spec-basic-tmfp.md.) A type fault and a numeric fault can BOTH be
; pending at the statement boundary, and which one the reference reports is
; decided by nothing more than WHICH HAPPENED FIRST -- because the reference
; raises EAGERLY, so the first fault aborts on the spot and the second never
; occurs at all (measured on both references, spec §1):
;
;   WIDTH (A$<5)+0*(1/0)     type first     -> ERR 13
;   WIDTH 0*(1/0)+(A$<5)     numeric first  -> ERR 11
;   WIDTH 0*SQR(-1)+(A$<5)   numeric first  -> ERR  5   (a DIFFERENT code, which
;                                                        is what makes it ORDER
;                                                        and not "div-zero wins")
;
; zerobas cannot raise eagerly -- ev_rel has no mid-expression unwind, which is
; this routine's whole reason to exist -- so it emulates with two sticky flags
; read at the statement boundary. A STATIC test order in those readers can only
; ever approximate a rule about time, and it approximated it wrongly in one
; direction: D-EVALCHK §5.1 froze TMISMATCH-first on the first row above and
; D-LOCARG then measured the second and third and could not fix them, because
; no static order satisfies both.
;
; 🎯 THE ORDER IS RECORDED WHERE IT IS KNOWN, WHICH IS HERE. This is the type
; fault's ONLY writer, and exec_stmt (interp.asm) clears the pending-error cell at
; every statement boundary, so a non-zero FPERR at THIS instant means the numeric
; fault came first. It wins, and the type fault simply does not arm.
;
; --- D-PENDERR: AND THE TYPE FAULT IS NOT A SECOND CONCEPT ------------------
; (docs/spec-basic-penderr.md.) D-TMFP wrote the guard below against a SEPARATE
; 1-byte flag, TMISMATCH ($E3E5), that fourteen readers had to test ahead of
; FPERR. That flag was only ever a boolean shorthand for ONE FPERR value --
; sfr_argok (above) already promoted it to `FPERR := 10` by hand, and
; fperr_to_err's entry 10 is the same ERR 13 type_mismatch_error raises. So the
; cell is gone and this routine writes the code straight into FPERR, set-if-empty:
; the readers collapse to a single test (-56 B) and the guard below IS that
; set-if-empty write, spelled out rather than delegated to penderr_set only
; because both of this routine's published register contracts differ per path
; (see the `A = 1` note below; delegating costs the same 3 bytes and would make
; both exits identical, which is a change nobody measured).
;
; ⚠️ THE MERGE IS ONLY SOUND BECAUSE EVERY OTHER WRITER IS SET-IF-EMPTY TOO.
; While the type fault lived in its own cell it was structurally immune to the
; two dozen bare `ld (FPERR),a` clobbers; in one cell it is not. penderr_set
; (top of this file) is what pays for that, once -- 17 rows of
; make penderr-acceptance depend on it (spec §3.2).
; 🔴 NOT, HOWEVER, THIS ROUTINE'S OWN ROWS, WHICH IS NOT WHAT THE DESIGN SAID.
; The argument for penderr_set was that `WIDTH (A$<5)+0*(1/0)` would otherwise
; lose its ERR 13 to fp_div's `ld a,2`. Knife K-PE2 deletes set-if-empty
; outright and that row STAYS at 13: after a deferred TYPE fault zerobas never
; raises a second fault from the rest of the expression, so there is no clobber
; to prevent here. The rows that need the write rule are the numeric-vs-numeric
; pairs, the HEX$/OCT$/STR$ family and the widened readers -- see spec §3.2. The
; guard above is still correct and still required; only its reason moved.
;
; ⚠️ THE HARD 0 IS PART OF THE CONTRACT ON BOTH PATHS, so it is hoisted above the
; guard: FIELD (field.asm) and eval_chan (float-arith.asm) both rely on a
; type-mismatched expression yielding 0, whether or not it armed the flag.
;
; 🔴 AND SO IS `A = 1`, WHICH IS NOT WHAT THIS ROUTINE'S OWN HEADER SAID. The
; header promised only "DE = 0; ret. Clobbers A", but str_cat's sct_err2 (above,
; the `A$+5` path) does `call type_mismatch_set` / `or a` / `ret` and its comment
; names the value out loud -- "A=1 -> CF clear (malformed operand)". The FIRST
; draft of this guard returned early with A = FPERR's value instead of 1, and the
; gate caught it on one row out of fifty: `Q2$=HEX$(0*(1/0)+(Q$<5))` turned from
; the wrong ERR 13 into a wrong ERR 2, because a string FUNCTION ARGUMENT that
; both faults inside its parentheses re-drives through the concatenation path,
; and a stray A left the cursor probe reading a malformed operand. STR$ and OCT$
; did it too; each fault ALONE did not. So `ld a,1` is hoisted above the `ret nz`
; and both exits publish it (docs/spec-basic-tmfp.md §4.3).
; out: DE = 0; A = 1; ret.
type_mismatch_set:
                ld      de,0                ; the D-2 contract's hard 0 -- yielded
                                            ; on BOTH paths below
                call    fperr_test          ; D-FPCARVE: -1 B
                ld      a,1                 ; ⚠️ A=1 ON BOTH PATHS -- see below; `ld a,n`
                                            ; does not touch the flags, so the `ret nz`
                                            ; still tests FPERR
                ret     nz                  ; D-TMFP: a numeric fault is ALREADY
                                            ; pending, so it happened FIRST and is
                                            ; the one the reference reports -- leave
                                            ; the cell alone and let every reader
                                            ; surface that one instead
                ld      a,FPERR_TYPEMM      ; D-PENDERR: the type fault IS a pending-
                ld      (FPERR),a           ; error code (fperr_to_err 10 -> ERR 13),
                                            ; not a second flag. Written direct, not
                                            ; via penderr_set: FPERR is provably 0 on
                                            ; this path (the `ret nz` above tested it).
                jp      errmark_expr        ; expression-error marker (ev_f_err convention)

; --- ev_rel_str: the string-compare path of ev_rel --------------------------
; Reached from expr.asm's ev_rel (a near-zero-byte gated hook there) when the LHS
; of a relational probes as a string operand (str_eval succeeded). Entered with
; HL = cursor past the LHS operand, STRPTR -> the LHS descriptor.
; 🔁 D-EVALSLOPE (2026-10-20): ev_rel is gone; the one climber (expr.asm cl_str)
; now CALLS this, and both exits come back to that call -- the D-2 arm's `ret`
; directly, the success tail through flt_int_result's own `ret` (D-REREAD batch 6:
; 9 B, all in front of the $3297 pin).
;
; Snapshots the LHS into an OWNED temp (str_snapshot_to_temp — was str_dup_temp
; pre-4a, same calling convention) so evaluating the RHS can't clobber it via
; STRSCR or a later alloc/GC (e.g. two literal operands would otherwise BOTH
; land on the shared RVDESC/STRSCR scratch and the second overwrites the
; first before the compare — the same discipline the substring verbs use).
; Reads the relop token(s) with the EXISTING relop_bit + compound-form merge
; (<=/>=/<> fall out unchanged), evaluates the RHS via str_eval, then compares
; with str_cmp_bits and joins the numeric path's convention (`and c` -> -1/0).
;
; A bare string LHS with no following relop, or a non-string RHS (`A$ < 5`), is
; D-2's type mismatch -> type_mismatch_set (yields 0, ERRMARK+TMISMATCH set).
; out: DE = -1/0; ret. Clobbers A, BC, DE, HL (like the numeric ev_rel body).
; Slice-4a: str_snapshot_to_temp / str_eval / str_cmp_bits are now sub-ROM
; op stubs that CALSLT -> they CLOBBER IX (and every register). The old
; str_dup_temp / cmp16-style callees were LOCAL and preserved IX, so this
; routine used to keep the token cursor in IX across them. Now the cursor is
; carried on the STACK and reloaded into IX only for the relop reads / the
; final ev_rel "IX = advanced cursor" return contract.
ev_rel_str:
                ; HL = cursor past the LHS operand, STRPTR = LHS descriptor.
                push    hl                  ; [cursor] (snapshot's CALSLT clobbers HL/IX)
                call    str_snapshot_arg    ; STRPTR -> LHS snapshot temp; HL = LHS temp
                                            ; 🔁 D-TEMPPOL part 2: an LHS that is ALREADY
                                            ; a temp is kept, not copied (D-CLP's rule:
                                            ; a temp is a fixed-address GC root, safe
                                            ; across the RHS). The copy was the second
                                            ; descriptor per compare the probe measured.
                pop     ix                  ; IX = cursor (for the relop reads)
                push    hl                  ; [LHStemp] (HL is dead until str_eval_ix)
                call    ev_sp
                call    relop_bit
                jr      nc,ers_mismatch     ; bare string LHS, no relop -> D-2 ([LHStemp])
                ld      c,b                 ; C = requested relation bits
                call    ixsp                ; D-IXSP
                call    relop_bit           ; a second relop? (<=, >=, <>)
                jr      nc,ers_rhs
                ld      a,c
                or      b
                ld      c,a                 ; merge the two relation bits
                call    ixsp                ; D-RELSPACE: past the second relop AND the
                                            ; spaces after it. A bare `inc ix` stood
                                            ; here, and str_eval_ix does not skip, so
                                            ; `"A"<= "B"` was a Type mismatch where the
                                            ; VG-8020 answers -1 (relspace_run.out).
                                            ; The one-character path already skipped:
                                            ; its ixsp above runs before relop_bit.
                                            ; (The numeric path's `inc ix` is fine: its
                                            ; operand parse skips spaces itself.)
ers_rhs:
                push    ix                  ; [LHStemp][cursor]
                push    bc                  ; [LHStemp][cursor][bits]
                call    str_eval_ix            ; STRPTR -> RHS desc; HL advanced; clobbers IX
                pop     bc                  ; C = bits            [LHStemp][cursor]
                jr      nc,ers_rhs_mismatch ; RHS not a string -> D-2 (`A$ < 5`)
                ; HL = new cursor (past RHS). STRPTR = RHS descriptor.
                pop     de                  ; drop the old cursor  [LHStemp]
                ex      (sp),hl             ; HL = LHS temp addr   [newcursor] (str_cmp_bits
                                            ; CALSLT clobbers IX)
                ld      de,(STRPTR)         ; DE = RHS descriptor addr
                call    str_cmp_bits        ; A = actual bit (1/2/4); preserves BC (C=reqbits)
                pop     ix                  ; IX = newcursor (ev_rel's "advanced cursor")
                and     c                   ; intersect requested with actual
                add     a,$FF               ; CF iff any requested bit matched
                sbc     a,a                 ; $FF true / 0 false
                ld      e,a
                ld      d,a                 ; DE = -1 / 0
                ; A string comparison's result is a NUMBER, so a chain that starts
                ; with strings continues in the numeric loop: `"A" = "A" = -1` is
                ; `("A" = "A") = -1` = -1 (MEASURED). The tail call returns to
                ; expr.asm's cl_str (D-EVALSLOPE), which goes on at the relational
                ; level and looser; cl_after_rel's ev_sp rewrites A and F first.
                jp      flt_int_result      ; the -1/0 result is an int even when a float
                                            ; rode in via a nested STR$ operand (float.asm
                                            ; F1; clobbers A only, preserves IX)
ers_rhs_mismatch:
                pop     ix                  ; BUG C lesser: RESTORE the cursor (the RHS
                                            ; str_eval CALSLT trashed IX) instead of
                                            ; discarding it -> type_mismatch_set returns
                                            ; with a coherent cursor, not garbage. [LHStemp]
ers_mismatch:
                pop     hl                  ; discard [LHStemp] (bare-LHS entry: IX already
                                            ; = cursor from the relop reads above)
                jr      type_mismatch_set

; --- DSKO$ d,s — write the sector buffer to sector s (D-DSKIO) ---------------
; docs/spec-basic-dskio.md. The parse and the tenant call are dsk_core below,
; shared with DSKI$ (basic/strvar.asm). Both stubs sit in the low region because
; page 1 had 43 B; the two regions share one budget.
ex_dsko:
                inc     hl                  ; HL -> bytes after the DSKO$ token
                ld      a,DISKOP_SEL_DSKO
                ld      de,H_DSKO
                call    dsk_core
                jp      exec_stmt

; 🧭 D-DISKVERB3 (2026-09-15): `copy_parse` AND `fname_fcb` ARE GONE FROM HERE.
; COPY's parse half moved into disk.rom with the rest of the verb (hk_copy), and
; fname_fcb -- `call fname_expr` / `jp pdfcb_resume` -- went with it: KILL and
; NAME stopped routing through it when their own bodies moved, so COPY was its
; last caller. The two page-1 halves stay exactly where they were and are now
; reached as CALL-BACK targets from disk.rom (REQUIRED_DISK_CALLBACK).
; 💰 This is the first disk verb whose saving lands in the LOW REGION, which
; stood at 0 B free.

; --- dsk_core: the shared half of DSKO$ d,s and DSKI$(d,s) (D-DSKIO) -----------
; docs/spec-basic-dskio.md §3. In: A = the selector (DISKOP_SEL_DSKO / _DSKI),
; DE = the hook cell (H_DSKO / H_DSKI), HL = the cursor at `d`. Out: HL = the
; cursor after `s`.
; 🔁 D-DISKREST slice 3 (2026-10-20): THE PARSE RUNS IN disk.rom TOO, and the
; hook is crossed ONCE (the body says how); the paragraph below is how D-DSKLOCAL
; left it, kept for its measurements.
; 🧭 D-DSKLOCAL (2026-10-15, D-ROMSIZE step 1): THE SECTOR I/O RUNS IN disk.rom
; (hk_dsk). The hook is crossed TWICE. First with A = 0, BEFORE the parse: the
; diskless VG-8020 answers ERR 5 to `DSKO$ 0` where the CF-3300 answers ERR 2, so
; an unclaimed cell must refuse before any argument is read (and an argument may
; itself run a disk verb, `DSKO$ 0,LOF(1)`, which is why the selector is parked on
; the stack). Then, parsed, with A = the selector and BC = the sector: hk_dsk
; moves one sector between (DSKBUF_PTR) and the disk with disk.rom's own DSKIO.
; `drive` is a byte -- 0 and 1 both name the one drive; 2.. is `Bad drive name`
; (ERR 62), measured on the reference with DSKI$(3,0).
; It used to poke the sector into FWR_DIRSEC and run the sub-ROM dirverb tenant;
; FWR_DIRSEC is also an open OUTPUT channel's directory pointer, which is what
; D-ALIASWCELL (2026-09-23) had to restore around. The sector crosses in BC now,
; so nothing the channel owns is touched. 🗑️ S10.E (2026-10-19): and the restore
; after the I/O (chan_restore_st) is gone -- no channel stages anything in main
; any more, and its last job, the LOF / LOC mirror, is disk.rom's FCB read now.
dsk_core:
                ; 🧭 D-DISKREST slice 3 (2026-10-20): ONE crossing, and the PARSE is
                ; disk.rom's (hk_dsk), as on the CF-3300 -- the diskless VG-8020's
                ; ERR 5 for `DSKO$ 0` (the CF-3300: 2) is still an unclaimed cell
                ; refusing BEFORE any argument is read. The selector crosses in A,
                ; the cursor in BC; the handler hands the cursor after `s` back in
                ; HL. IX is the evaluator's cursor when DSKI$ runs inside an
                ; expression, and the CALLF clobbers it.
                push    ix
                ld      b,h
                ld      c,l                 ; BC = the cursor at `d`
                ex      de,hl               ; HL = the hook cell
                call    chan_gate_bare      ; unclaimed -> ERR 5, trappable
                ei                          ; a CALLF returns with interrupts OFF
                pop     ix
                ld      a,(DISKOP_STATUS)   ; hk_dsk's disposition
                or      a
                ret     z                   ; HL = the cursor after `s`
                jp      disk_error          ; DSKIO error -> its code (D-DISKERR)

; 🎯 PROMOTED HERE FROM basic/interp.asm (page 1) BY D-STACKFLOOR, 2026-09-27: the
; evaluator's stack guard needed 3 B more than page 1 had, while the low region
; had 9 free after D-CARVERC. The two share ONE budget and include order alone
; decides the region ([[carve-routes-measured-shut]]); req_comma has no relative
; jump and nothing falls into it, so the move is byte-neutral and position-free.
; --- req_comma: the argument separator this statement REQUIRES ---------------
; D-NGRAM17. `call skip_spaces / cp ',' / jp nz,stmt_error / inc hl` -- *a comma
; belongs here* -- stood open-coded at four sites, one per verb: FIELD
; (exf_havech), INPUT# (inp_readvar), SWAP (ex_swap) and SOUND (ex_sound).
; 9 B each.
;
; 🔴 THE FAMILY IS BIGGER THAN THE COLLAPSIBLE SET, and the difference is WHERE
; THEY JUMP. `basic/` has 72 `cp ','` sites; enumerated at instruction level they
; group by destination -- 4 to `stmt_error` (the comma is REQUIRED: these), 3 to
; `exec_stmt` (an OPTIONAL comma that simply ends the statement) and a tail of
; two-site groups each branching to its own local label. Only a shared
; DESTINATION can share a body; a caller's own decline target is what keeps it at
; the call site (the D-NGRAM11 rule).
;
; ⚠️ The extra return address costs nothing on the failing path: `stmt_error`
; never returns and both its arms reset SP -- the same fact `req_letter` above
; rests on. On the succeeding path the `inc hl` is INSIDE the helper, so the
; comma is consumed exactly once; `g.*` rows read the argument AFTER it to say so
; (scratchpad/reqcomma_probe.py).
req_comma:
                call    skip_comma
                jp      nz,stmt_error       ; no comma: the statement aborts
                inc     hl                  ; consume it
                ret
