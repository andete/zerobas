; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas-sub — casmatch.asm  (cassette name-match/skip tenant)
; ===========================================================================
; cas_open_match + cas_skip_data (tape Tier-3 name-matching, basic/cload.asm),
; evicted whole into sub-ROM PAGE 1 (docs/spec-eviction-g5-space.md) to free
; main-ROM page-1 tail space for the G5 PAINT slice. Follows the landed G4-
; eviction pattern (sub/randio.asm, sub/lineedit.asm): the moved code is
; VERBATIM (shared via basic/casmatch-body.inc, included both here and at
; basic/cload.asm's own original position -- byte-
; identical there).
;
; NO MARSHALLING: cas_open_match takes no register inputs and its only
; caller-visible output is CF (matched vs not-found/tape-error) + the RAM
; cell CAS_HDRID it already sets on a match. Since subrom_call always clears
; CF on return (CALSLT's own `or a` after the call, basic/subromcall.asm),
; the CF result cannot ride back directly -- casmatch_tenant (below) converts
; it to a status byte (CM_STATUS, aliased onto the shared DISKOP_STATUS cell,
; the fatprim/dirverb/audio/lineedit precedent: one subrom_call reaches
; exactly one tenant, so the separate value namespaces never collide) that
; the resident stub (basic/cload.asm `cas_open_match`) converts back to CF.
;
; cal_refill lives HERE ONLY since D-CARVECAS (2026-09-27): it was duplicated
; (shared source via basic/cal-refill-body.inc) while main's cal_getbyte and
; cas_ascii_setup called a resident copy; both bodies are casget_tenant's now
; (below), so main dropped its copy. Its callers are all in this file:
; cas_skip_data's csd_ascii arm, cal_serve and cas_ascii_setup. TAPION/TAPIN
; (page-0 BIOS) + CAL_BUF/CAL_CNT (RAM) are the only things it touches -- no
; straddle, nothing in the resident-ABI import list needed.
;
; CLEAN-ROOM: original code, extracted verbatim from our own basic/cload.asm
; (see that file's header for the cassette file-format provenance: MSX2
; Technical Handbook cassette file format, an allowed source). The dispatch/
; marshalling glue is own-design, the fatprim/dirverb/lineedit precedent. No
; reference-ROM disassembly. See sub/PROVENANCE.md.
; ===========================================================================

; --- casmatch_tenant: the SUBROM_IDX_CASMATCH entry ------------------------
casmatch_tenant:
                call    cas_open_match
                jr      c,cmt_fail
                xor     a
                jr      cmt_store
cmt_fail:
                ld      a,1
cmt_store:
                ld      (CM_STATUS),a
                ret


; --- casget_tenant: the SUBROM_IDX_CASGET entry (D-CARVECAS) ------------------
; The cassette ASCII byte source, moved out of main page 1 to fund D-FORFLOAT:
; cal_getbyte's serve/swap/read-ahead body and cas_ascii_setup, both of which
; only ever call cal_refill -- whose sub copy is right below. In: L = the op.
;   L = 0  serve the next byte          -> A = the byte (the resident stub
;          (cal_getbyte, basic/cload.asm) answered the latched EOF already)
;   L = 1  prime data blocks 1 and 2    -> A = 0 ok, $FF block 1 unreadable
; CF cannot cross a CALSLT, so op 1's is folded into A with `sbc a,a`.
; ⚠️ The tape-timing requirements in basic/cload.asm's header hold unchanged:
; the refill still runs back-to-back with the byte that drains a buffer, and
; its state stays in RAM (CAL_*), never on the stack across TAPIN.
casget_tenant:
                ld      a,l
                or      a
                jr      z,cal_serve
                call    cas_ascii_setup
                sbc     a,a                 ; CF -> $FF, clear -> 0
                ret

; --- cal_serve: cal_getbyte's body, verbatim from basic/cload.asm ------------
; (its header, the double-buffer argument, stays with the resident stub).
cal_serve:
                ; 🏛️ D-CASFCB (2026-10-13): ONE buffer -- the channel's own (CAS_BUFP),
                ; as on the VG-8020 (scratchpad/casbuf_probe.out). The read-ahead second
                ; buffer is gone: the motor stops after every block (D-CAS4BLK), so the
                ; tape WAITS while a block's lines are crunched and nothing is lost by
                ; refilling when the buffer drains (scratchpad/casmotor_probe.out: the
                ; reference does exactly that, motor off between blocks).
                ld      hl,(CAS_BUFP)
                ld      a,(CAL_CNT)
                ld      e,a
                ld      d,0
                add     hl,de               ; HL = buffer + CAL_CNT
                ld      a,(hl)              ; A = the byte to return
                ld      b,a                 ; hold it across the bump (and any refill)
                ld      a,e
                inc     a                   ; advance position; 255 -> 0 wraps (8-bit)
                ld      (CAL_CNT),a
                jr      nz,cal_srv_ret      ; still within the buffer -> done
                ; This byte drained the buffer: refill it with the next block now
                ; (the byte must survive TAPIN, which clobbers every register).
                ld      a,b
                ld      (CAL_SAVE),a
                call    cal_refill          ; CF = no further block
                ld      a,0                 ; 🔴 NOT `xor a`: cal_refill's CF is the
                jr      nc,cal_gb_flag      ;  test here (D-PEEPHOLE)
                ld      a,2                 ; none: a TERMINAL eof for the next call
cal_gb_flag:
                ld      (CAL_NEEDFILL),a
                ld      a,(CAL_SAVE)
                ld      b,a                 ; restore the byte to return
cal_srv_ret:
                ld      a,b
                or      a                   ; CF clear = byte valid
                ret

; --- cas_ascii_setup, verbatim from basic/cload.asm (the header stays there) --
cas_ascii_setup:
                ; D-CASFCB: prime data block 1 into the channel's buffer (CAS_BUFP,
                ; set by the resident caller) -- ONE block, the reference's way.
                call    cal_refill          ; data block 1 leader + slurp 256 bytes
                ret     c                   ; block 1 unreadable -> CF
                xor     a                   ; CF clear: block 1 primed OK
                ld      (CAL_NEEDFILL),a    ; more blocks may follow (learned on drain)
                ld      (CAL_CNT),a         ; serve from position 0 (cal_refill left 0)
                ret

                include "basic/casmatch-body.inc"    ; cas_open_match..cas_skip_data
                include "basic/cal-refill-body.inc"  ; cal_refill (sub-local duplicate)
