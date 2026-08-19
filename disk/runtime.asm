; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
; Part of zerobas-disk, included by disk.asm (build with `pasmo -I disk`).
; free-tail runtime: relocated templates + shared pg0_mainrom_* helpers + conout_body + int_h_body (Interface B)
; CLEAN-ROOM: every constant, address and algorithm here traces to a public source
; or a black-box oracle probe; nothing is derived from disassembly. See disk/PROVENANCE.md.

; --- shared page-0 main-ROM inter-slot helpers (CONOUT M8 + int_h A-2) ----------
; pg0_mainrom_in - save the current $A8 to PG_SV_A8 and page the main BIOS ROM into
; page 0. PORTABLE (no machine-specific hardcode): the main-ROM slot is read at runtime
; from EXPTBL[0] ($FCC1) - the standard cell holding the slot id (bit7=expanded,
; [3:2]=subslot, [1:0]=primary). Sets page-0's $A8 primary to that primary and, if the
; slot is expanded, programs its page-0 SECONDARY subslot too. Only the page-0 (and,
; transiently, page-3) $A8 fields move: page 1 (our disk ROM) keeps running this code
; and page 2 (the stack) survives, so call/ret is safe. Caller MUST be DI and MUST pair
; with pg0_mainrom_out. Clobbers A,B,C,D,E,H,L (callers save what they need).
; CLEAN-ROOM: EXPTBL/$FCC1, SLTTBL/$FCC5, the $A8 primary register and the $FFFF
; secondary protocol are documented MSX BIOS ABI (MSX2 TH ch.2/2.4); no oracle bytes.
; NOTE: on the CF-3300 EXPTBL[0]=$00 (unexpanded), so the primary path is exercised+
; validated; the expanded sub-path is spec-derived and NOT reachable here (review queue).
pg0_mainrom_in:
                in      a, ($A8)
                ld      (PG_SV_A8), a       ; save full primary-slot config (restore key)
                ld      a, (EXPTBL)         ; main-ROM slot id
                ld      c, a                ; C = slot id
                and     $03                 ; A = main-ROM primary
                ld      b, a                ; B = primary
                ld      a, (PG_SV_A8)
                and     $FC                 ; clear page-0 primary field
                or      b                   ; set page-0 primary = main-ROM primary
                out     ($A8), a            ; main-ROM primary now in page 0 (pages 1/2/3 kept)
                bit     7, c                ; main-ROM slot expanded?
                ret     z                   ; unexpanded -> primary switch is enough (CF-3300)
                ; --- expanded: select the page-0 subslot via the $FFFF/SLTTBL protocol ---
                ld      a, c
                rrca
                rrca
                and     $03                 ; A = main-ROM subslot S
                ld      e, a                ; E = S
                ld      hl, SLTTBL
                ld      a, b
                add     a, l                ; SLTTBL aligned, P<4 -> no page crossing
                ld      l, a                ; HL = &SLTTBL[P]
                ld      a, (hl)
                and     $FC                 ; clear page-0 subslot field
                or      e                   ; merge new page-0 subslot S
                ld      (hl), a             ; update the SLTTBL[P] mirror
                ld      e, a                ; E = new secondary value to write to $FFFF
                ld      a, b                ; primary P -> page-3 field
                rlca
                rlca
                rlca
                rlca
                rlca
                rlca                        ; P << 6
                ld      d, a                ; D = P in page-3 field
                ld      a, (PG_SV_A8)
                and     $3C                 ; keep pages 1/2 ; clear page-0 + page-3 fields
                or      b                   ; page-0 primary = P
                or      d                   ; page-3 primary = P (reach P's $FFFF expander)
                out     ($A8), a
                ld      a, e
                ld      ($FFFF), a          ; P's secondary: page-0 subslot = S
                ld      a, (PG_SV_A8)
                and     $FC                 ; restore page-3 (& 1/2) primaries; clear page 0
                or      b                   ; page-0 primary = P (main-ROM, now subslot S)
                out     ($A8), a
                ret

; pg0_mainrom_out - restore page 0 from PG_SV_A8 (the RAM slot's own secondary is never
; touched, so its page-0 subslot is intact). Clobbers A.
pg0_mainrom_out:
                ld      a, (PG_SV_A8)
                out     ($A8), a
                ret

; --- conout_body - the real $5454 CONOUT (M8/8.67; char-reg fix M10/§8.80) ------
; Emit the char (in E) via the main-ROM CHPUT ($00A2). Reached from the $5454 veneer
; (jp conout_body). Pages the main ROM into page 0 (pg0_mainrom_in), calls CHPUT,
; restores (pg0_mainrom_out). DI spans the window; EI on exit.
;   in:  E = char ; out: A = char, BC/DE/HL/IX/IY preserved
; CHAR REGISTER = E (not A). The $5454 CONOUT contract passes the char in E: the
; relocated MSX-DOS kernel's per-char console output (caller $D88A) loads E=char and
; leaves A=0, so reading A emitted $00/garbage for ALL COMMAND.COM-phase + A>-prompt
; output (banner/date/prompt rendered as constant tiles). The early MSXDOS.SYS sign-on
; (caller $0320) happens to pass the char in BOTH A and E, so the old A-read worked
; there and HID the bug -- the exact "early works, COMMAND fails" discriminator. E is
; the register common to BOTH callers. Black-box proven: $7922-entry callseq shows E
; spelling "MSX-DOS version 1.03" (early) and "Sun 84-01-01"/"A>" (kernel), A=0.
; CLEAN-ROOM: E=char is the MSX-DOS BDOS CONOUT (func 2) ABI convention; no oracle bytes.
;
; M22a: $5454 is ALSO the canonical BDOS $06 DIRIO entry; the kernel routes both
; funcs here (tier2-m22-cpmver-spec.md §4.7/§6.3). C holds the BDOS function code
; ONLY on calls routed through the kernel's common BDOS dispatch (ret=$D88A, the
; same discriminator §3 uses to confirm "called directly by the kernel
; dispatcher" for every other M22a entry) — DIRECT callers that reach $5454
; without going through that dispatch (COMMAND.COM's own column-padding print
; loop, or the early $0320 MSXDOS.SYS sign-on documented above) can leave
; ANYTHING in C, since it's just whatever register a caller-internal loop
; happened to be using. Self-caught in verification: checking C alone made a
; padding loop's counter passing through C=$06 misfire into the DIRIO branch on
; a plain space character, corrupting DIR's screen output (no spec section —
; a plain safety gap in the discriminator, not a contract question). So the
; return address is peeked FIRST (without disturbing the stack) and C is only
; trusted when ret==$D88A; the published DIRIO input-vs-output convention
; (E=$FF is input) is checked only after that.
; The caller's AF is pushed FIRST, before any of this touches flags: the
; original code's first instruction (`ld a,e`) never affected flags, so every
; existing caller relies on ITS OWN entry flags surviving the call untouched
; (the M8 kernel path tests them, e.g. for line-wrap bookkeeping).
conout_body:
                push    af                  ; preserve caller AF/flags BEFORE any check
                push    hl                  ; HL scratch for the return-address peek
                ld      hl, 4
                add     hl, sp              ; HL -> caller's return address (2 pushes = +4)
                ld      a, (hl)
                cp      $8A
                jr      nz, conout_not_dispatch
                inc     hl
                ld      a, (hl)
                cp      $D8
                jr      nz, conout_not_dispatch
                ; ret == $D88A: C reliably holds the BDOS func code here (§4.7).
                ld      a, c
                cp      $06
                jr      nz, conout_not_dispatch
                ld      a, e
                cp      $FF
                jr      nz, conout_not_dispatch
                pop     hl                  ; restore caller's HL
                pop     af                  ; restore caller's AF for dirio_in_body
                jp      dirio_in_body
; M22b slice 2 (TAB expansion + $F237 logical-column bookkeeping). The per-char emit
; (conout_emit_e) is RELOCATED above the FDC hole $7FB8-$7FBF (it doesn't fit below);
; conout_tab stays HERE, below the hole (jr-reachable), and calls up. This emit tail is
; a shrink vs the old 32-byte inline CHPUT, but p0_env_tab is PINNED at its HEAD address
; $7FB7 (see its tail block) so the shrink does NOT slide its critical $0030/$0038 vector
; entries into the FDC register window -- lay_page0_env reads p0_env_tab THROUGH that
; window, so a corrupted vector there = corrupt page-0 $0038 = boot crash (root-caused
; 2026-07-04). The dispatch preamble above is byte-stable. Contract: char in E, A:=E.
conout_not_dispatch:
                pop     hl                  ; restore caller's HL; caller AF stays on the stack
                ld      a, e                ; char arrives in E ($5454 CONOUT contract)
                cp      $09                 ; TAB? -> expand to the next 8-column stop
                jr      z, conout_tab       ; conout_tab is just below (jr-reachable)
                call    conout_emit_e       ; CHPUT the char + $F237 column bookkeeping (above hole)
                pop     af                  ; restore caller AF/flags (pushed at entry)
                ld      a, e                ; return A := E (the emitted char, §5.1)
                ret
; conout_tab ($09): emit spaces to the next 8-column stop (>=1). conout_emit_e does the
; col++ per space and returns A = the new column, so the loop re-tests A & 7. The stop is
; the LOGICAL column ($F237), not the screen cursor (§5.3 col-34 = 6 spaces). Stock exits
; A=$00 (§8.1, capture at $D88A: AF=$0054, $F237=$08 after a col-1 tab). do{ emit ' ';
; col++ }while(col&7).
conout_tab:
                push    de                  ; preserve caller DE (loop clobbers E with $20)
conout_tab_loop:
                ld      e, $20              ; a space
                call    conout_emit_e       ; CHPUT ' ' + col++ ; returns A = the new column
                and     $07                 ; stop at an 8-column boundary
                jr      nz, conout_tab_loop
                pop     de                  ; restore caller DE
                pop     af                  ; restore caller AF/flags (pushed at conout_body entry)
                ld      a, 0                ; exit A := $00 (stock's post-TAB value, §8.1)
                ret

; --- dirio_in_body - the $5454/$06 DIRIO input direction (M22a) ------------------
; Non-blocking read: CHSNS ($009C) — if a key is queued, CHGET ($009F) it (no
; echo, per the published DIRIO contract) and return A=char; else A=$00. B/C/D/E
; must survive untouched (§5.3); only A changes (HL is overwritten by the
; kernel's own exit mirror regardless, §5.2, so it needs no attention here).
; CLEAN-ROOM: published DIRIO contract (map.grauw.nl) + CHSNS ($009C, the same
; documented MSX BIOS class as CHGET/CHPUT already used here); no oracle bytes.
dirio_in_body:
                push    bc
                push    de
                push    hl
                di
                call    pg0_mainrom_in
                call    $009C               ; CHSNS: A=$00 empty / nonzero ready (BIOS ABI)
                or      a
                jr      z, dirioin_empty
                call    $009F               ; CHGET: A := char (no echo, DIRIO contract)
                jr      dirioin_done
dirioin_empty:
                xor     a                   ; no key queued -> A := 0
dirioin_done:
                push    af                  ; stash result across mainrom_out (clobbers A)
                call    pg0_mainrom_out
                ei
                pop     af
                pop     hl
                pop     de
                pop     bc
                ret

; --- const_body - the $543C CONST canonical entry (M22a) -------------------------
; Non-blocking poll: CHSNS ($009C) -> A=$FF ready / A=$00 empty (the published
; CONST contract; CHSNS itself returns nonzero/zero, normalized to $FF/$00 here).
; B/C/D/E preserved.
; CLEAN-ROOM: published CONST contract (map.grauw.nl) + CHSNS; no oracle bytes.
const_body:
                push    bc
                push    de
                push    hl
                di
                call    pg0_mainrom_in
                call    $009C               ; CHSNS: A=$00 empty / nonzero ready (BIOS ABI)
                or      a
                jr      z, const_notready
                ld      a, $FF              ; MSX-DOS CONST contract: ready -> A=$FF
const_notready:
                push    af
                call    pg0_mainrom_out
                ei
                pop     af
                pop     hl
                pop     de
                pop     bc
                ret

; --- conin_body - the $5445 CONIN canonical entry (M22a) --------------------------
; Blocking read: CHGET ($009F), then echo via conout_body (E=char, its ABI) —
; the published BDOS $01 CONIN contract (read-with-echo). B/C/D preserved;
; A/E end up holding the char (conout_body's own A:=E return).
; CLEAN-ROOM: published CONIN contract (map.grauw.nl) + our own CHGET/conout_body
; primitives; no oracle bytes.
conin_body:
                push    bc
                push    de
                push    hl
                di
                call    pg0_mainrom_in
                call    $009F               ; CHGET: blocking; A := char
                push    af                  ; stash char across mainrom_out (clobbers A)
                call    pg0_mainrom_out
                ei
                pop     af                  ; A := char
                ld      e, a                ; echo via conout_body (E = char, its ABI)
                call    conout_body
                pop     hl
                pop     de
                pop     bc
                ret

; --- innoe_body / dirin_body - the $544E INNOE / $5462 DIRIN canonical entries
; (M22a) -- blocking read, NO echo (the published BDOS $08/$07 contract, as
; distinct from $01 CONIN's echo). Pinned identical at this probe's granularity
; (tier2-m22-cpmver-spec.md §6.3): dirin_body tail-jumps into innoe_body.
; B/C/D/E preserved; A := char.
; CLEAN-ROOM: published INNOE/DIRIN contracts (map.grauw.nl) + CHGET; no oracle bytes.
innoe_body:
                push    bc
                push    de
                push    hl
                di
                call    pg0_mainrom_in
                call    $009F               ; CHGET: blocking; A := char (no echo)
                push    af
                call    pg0_mainrom_out
                ei
                pop     af
                pop     hl
                pop     de
                pop     bc
                ret
dirin_body:
                jp      innoe_body

; --- cpmver_body - the $41EF CPMVER canonical entry (M22a) -----------------------
; A := $22 (the published CP/M-2.2-compatibility version constant, map.grauw.nl
; _CPMVER), B := 0. HL is overwritten by the kernel's own exit mirror regardless
; ($F306 stays set — §5.2, the M20 rule inverted for this tier).
cpmver_body:
                ld      a, $22
                ld      b, 0
                ret

; --- login_body - the $504E LOGIN canonical entry (M22a) -------------------------
; A := the online-drive bitmap (1 << DRVCNT) - 1, the published LOGIN contract
; (map.grauw.nl), derived from our OWN DRVCNT cell ($F347, =2 here) rather than
; a hardcoded constant. B := 0. Only B (the loop counter, no longer needed once
; the shift is done) is clobbered besides A/HL — C/D/E (§5.3) are never touched.
login_body:
                ld      a, (DRVCNT)         ; DRVCNT = $F347 = logical-drive count
                ld      b, a                ; B := DRVCNT (loop counter, temporarily)
                ld      hl, 1
                or      a
                jr      z, login_bits_done  ; DRVCNT=0 -> bitmap 0 (defensive)
login_shift:
                add     hl, hl
                djnz    login_shift
login_bits_done:
                dec     hl
                ld      a, l                ; A := (1<<DRVCNT)-1 (fits one byte for DRVCNT<8)
                ld      b, 0                ; B := 0 (LOGIN exit contract)
                ret

; --- stime_body - the $55E6 STIME canonical entry (M22a) -------------------------
; A := 0 (success); B := H (hours); C := L (minutes) — the published STIME
; contract's minimal valid-input path (map.grauw.nl); D/E (seconds/hundredths)
; untouched, matching the pinned oracle (§5.1 r2). Range validation (A:=$FF on
; out-of-range input) is unimplemented — the exerciser never sends invalid
; input and stock's invalid-path was never observed (§8.2 residual).
stime_body:
                xor     a
                ld      b, h
                ld      c, l
                ret

; --- gtime_body - the $55DB GTIME canonical entry (M22a) -------------------------
; A := B := C := D := E := 0 — the oracle's pinned constant 00:00:00
; (clockless-MSX1 default; deliberately NOT fed by STIME's stored value, which
; would diverge from the observed oracle, §5.1 r3).
gtime_body:
                xor     a
                ld      b, a
                ld      c, a
                ld      d, a
                ld      e, a
                ret

; --- verify_body - the $55FF VERIFY canonical entry (M22a) -----------------------
; A := E (the published VERIFY contract: echo the requested on/off flag); B
; passes through untouched (§5.3). NO-OP SETTER BY DESIGN, and this is the
; FAITHFUL choice — RESOLVED 2026-07-04 (remaining-spec §5.4, was open): stock
; MSX-DOS 1 has NO verify-after-write effect (black-box: a VERIFY-on WRABS issues
; exactly the same single $4010 DSKIO write as a VERIFY-off WRABS, zero read-back —
; probes/disk/verifyx.asm). So neither persisting E nor coupling a verify-read into
; the write path is needed; doing so would make ours LESS faithful (extra reads
; stock never does) and is pointless on the emulator target (writes cannot fail).
verify_body:
                ld      a, e
                ret

; --- dskrst_body - the $509F DSKRST canonical entry (M22a) -----------------------
; Reproduces the pinned $50A9 continuation-stub contract (A=0; (W50A9_WRKB):=0;
; DE=IX=$F1AA) by a plain tail-jump into the existing stub — replacing the
; former pad-slide "luck" (§4.4) with an explicit wired entry. HL is overwritten
; by the kernel's own exit mirror regardless ($F306 stays set), so the stub's
; own HL:=$F359 is immaterial here. Real flush semantics are unverifiable (no
; dirty buffers at these call sites) — the register contract is the observable
; surface (§8.4 residual).
dskrst_body:
                jp      w50a9_stub

; --- conin_line_body - the $50E0 CONIN line routine (M13; tier2-conin-spec.md v3) ---
; Reimplements the documented BDOS func-$0A buffered-line read, clean-room, from the
; published CHGET ($009F) contract + the CONOUT veneer (echo) + the func-$0A buffer
; layout ([DE+0]=max/[DE+1]=count/[DE+2..]=chars). Reached from the $50E0 veneer
; (jp conin_line_body). NO return register (per the M12d pin) -- the result lives in
; the buffer. One CHGET per char (PIN B: 7 calls for a 6-char + CR line): CR ends the
; line, BS backs up one char (buffer edit only), else echo via conout_body and store.
; CLEAN-ROOM: CHGET/CHPUT/func-$0A buffer are the published/cross-vendor BDOS ABI; the
; stock $50E0 routine's internals were never read (only its entry regs, black-box).
;   in:  DE = buffer base ; out: buffer filled (func-$0A layout); BC/DE/HL preserved
conin_line_body:
                push    bc
                push    hl
                ld      (CONIN_BUF), de     ; stash buffer base (pg0_mainrom_* clobbers D/E)
                ld      a, (de)
                ld      (CONIN_MAX), a      ; max length = buf[0]
                xor     a
                ld      (CONIN_COUNT), a    ; running fill count starts at 0
cinl_getchar:
                di                          ; no interrupt while the BIOS is half-mapped
                call    pg0_mainrom_in
                call    $009F               ; CHGET - wait for + return a char in A
                ld      b, a                ; B = the char (pg0_mainrom_out clobbers A)
                call    pg0_mainrom_out     ; restore page 0
                ei
                ld      a, b                ; A = the char read
                cp      $0D                 ; CR -> line done
                jr      z, cinl_done
                cp      $08                 ; BS -> edit back one char
                jr      nz, cinl_store
                ld      hl, CONIN_COUNT
                ld      a, (hl)
                or      a
                jr      z, cinl_getchar     ; nothing to erase -> ignore
                dec     (hl)
                jr      cinl_getchar        ; (buffer edit only; no un-echo)
cinl_store:
                ld      c, a                ; C = the char to store/echo
                ld      a, (CONIN_COUNT)
                ld      b, a                ; B = current fill count
                ld      a, (CONIN_MAX)
                cp      b
                jr      z, cinl_getchar     ; buffer full -> drop the char (no room)
                ld      de, (CONIN_BUF)
                inc     de
                inc     de                  ; DE -> buf[2 + count]
                ld      a, b
                ld      l, a
                ld      h, 0
                add     hl, de
                ld      (hl), c             ; store the char
                inc     b
                ld      a, b
                ld      (CONIN_COUNT), a    ; count++
                ld      e, c                ; echo via conout_body (E = char, its ABI)
                call    conout_body
                jr      cinl_getchar
cinl_done:
                ld      de, (CONIN_BUF)
                inc     de                  ; DE -> buf[1] = count
                ld      a, (CONIN_COUNT)
                ld      (de), a
                inc     de                  ; DE -> buf[2] (first char slot)
                ld      l, a
                ld      h, 0
                add     hl, de              ; HL -> buf[2 + count]
                ld      (hl), $0D           ; M16: terminate with CR immediately after the
                                             ; last stored char (buf[2] when count=0) --
                                             ; observed on stock's own buffer content;
                                             ; COMMAND.COM's date-reply parser scans from
                                             ; buf[2] for this rather than trusting count
                                             ; alone (tier2-conin-spec.md §6)
                pop     hl
                pop     bc
                ret

; --- int_h_body - the OLD page-1 $0038 handler (A-2/A-2b) — SUPERSEDED by A-3 -------
; DEAD as of A-3: $0038 no longer points here (it points at INT_H_HIRAM). Kept in place
; (net-zero, no address shift) pending removal; the live handler is int_h_hiram_tmpl
; below, relocated into always-mapped high RAM because page 1 is reclaimed for the TPA.
; A bare VDP ack is not enough: the kernel/COMMAND.COM need H.KEYI/H.TIMI/keyboard/
; JIFFY, which only the main-BIOS KEYINT runs. Stock's $0038 handler ($DDAE) inter-slot
; CALSLTs to the main-ROM KEYINT ($0038 entry -> body $0C3C, calling H.KEYI $FD9A +
; H.TIMI $FD9F) - the MSX1 standard, BIOS-agnostic. We do the same via pg0_mainrom_in:
; page the main ROM in, call $0038 (KEYINT does its own VDP ack), restore, return.
int_h_body:
                ld      (INT_SP_SAVE), sp   ; A-2b: save caller SP (no stack touch) ...
                ld      sp, INT_STK_TOP     ; ... and run on our private interrupt stack,
                                            ; so a corrupt caller SP is never marched (§8.75)
                push    af
                push    bc
                push    de
                push    hl
                di
                call    pg0_mainrom_in      ; main BIOS ROM -> page 0 (portable, EXPTBL[0])
                call    $0038               ; main-ROM KEYINT: ack + H.KEYI + H.TIMI + kb + JIFFY
                di                          ; close KEYINT's internal EI before un-mapping
                call    pg0_mainrom_out     ; restore page 0 = RAM
                pop     hl
                pop     de
                pop     bc
                pop     af
                ld      sp, (INT_SP_SAVE)   ; A-2b: restore caller SP, then the single EI
                ei
                ret

; --- int_h_hiram_tmpl - the LIVE $0038 handler, A-3 + A-5 (tier2-a5-spec.md) ------
; Relocated by a plain LDIR into INT_H_HIRAM ($DDAE) page-3 high RAM during init, so it
; survives COMMAND.COM reclaiming page 1 (wa_seg_ram). RELOCATABLE: straight-line, ONLY a
; PC-relative jr + the FIXED call $0038 (no template-relative call/jp, same rule as
; res_print_tmpl). pg0_mainrom_in/out are INLINED (their `ret z` early-out becomes `jr z`);
; all data refs ($A8/$FFFF, EXPTBL/SLTTBL, PG_SV_A8, $0038) are absolute fixed addresses that
; survive relocation. Pages the main ROM into PAGE 0 only (page 1 = the TPA is never touched),
; calls the main-BIOS KEYINT, restores, EI, RET. BIOS-agnostic (EXPTBL[0]); the expanded-slot
; path is spec-derived (CF-3300 is unexpanded). CLEAN-ROOM: our own code/address; $DDAE is an
; oracle WHERE, never stock's bytes.
;
; A-5 (tier2-a5-spec.md): runs on the CALLER's (interrupted code's) stack — the standard MSX
; interrupt convention — NOT a private stack. The A-2b private stack was a guard against an
; interrupt firing with a corrupt caller SP (the primary derail); A-3 fixed that derail, so
; the caller SP is always valid here. The 48-byte private stack was in fact TOO SMALL for the
; main-ROM KEYINT (~60 B, unbounded via H.TIMI/H.KEYI hooks): KEYINT overflowed it DOWNWARD
; into the WA_SEG trampoline laid out just below it ($E795+), corrupting the $F368/$F36B
; segment switch and hanging the COMMAND.COM handoff (harness, 2026-06-26). Caller stacks
; here (kernel $DBFA, COMMAND.COM $F513…) have ample room, so this is both correct and safe.
int_h_hiram_tmpl:
                push    af
                push    bc
                push    de
                push    hl
                di
                ; --- inlined pg0_mainrom_in (main BIOS ROM -> page 0; EXPTBL[0]) ---
                in      a, ($A8)
                ld      (PG_SV_A8), a       ; save full primary-slot config (restore key)
                ld      a, (EXPTBL)         ; main-ROM slot id
                ld      c, a
                and     $03                 ; A = main-ROM primary
                ld      b, a
                ld      a, (PG_SV_A8)
                and     $FC                 ; clear page-0 primary field
                or      b
                out     ($A8), a            ; main-ROM primary now in page 0 (pages 1/2/3 kept)
                bit     7, c                ; main-ROM slot expanded?
                jr      z, ihh_keyint       ; unexpanded (CF-3300) -> primary switch is enough
                ; --- expanded: select page-0 subslot via the $FFFF/SLTTBL protocol ---
                ld      a, c
                rrca
                rrca
                and     $03                 ; A = main-ROM subslot S
                ld      e, a
                ld      hl, SLTTBL
                ld      a, b
                add     a, l                ; SLTTBL aligned, P<4 -> no page crossing
                ld      l, a                ; HL = &SLTTBL[P]
                ld      a, (hl)
                and     $FC                 ; clear page-0 subslot field
                or      e
                ld      (hl), a             ; update the SLTTBL[P] mirror
                ld      e, a                ; E = new secondary value for $FFFF
                ld      a, b
                rlca
                rlca
                rlca
                rlca
                rlca
                rlca                        ; P << 6
                ld      d, a
                ld      a, (PG_SV_A8)
                and     $3C                 ; keep pages 1/2 ; clear page-0 + page-3 fields
                or      b                   ; page-0 primary = P
                or      d                   ; page-3 primary = P (reach P's $FFFF expander)
                out     ($A8), a
                ld      a, e
                ld      ($FFFF), a          ; P's secondary: page-0 subslot = S
                ld      a, (PG_SV_A8)
                and     $FC                 ; restore page-3 (& 1/2) primaries; clear page 0
                or      b                   ; page-0 primary = P (main-ROM, now subslot S)
                out     ($A8), a
ihh_keyint:
                call    $0038               ; main-ROM KEYINT: ack + H.KEYI + H.TIMI + kb + JIFFY
                di                          ; close KEYINT's internal EI before un-mapping
                ; --- inlined pg0_mainrom_out (restore page 0 from PG_SV_A8) ---
                ld      a, (PG_SV_A8)
                out     ($A8), a
                pop     hl
                pop     de
                pop     bc
                pop     af
                ei
                ret
int_h_hiram_end:

; --- dos_handoff — DOS-only $F338 default + the step-7 "load the system" call ---
; COMMAND.COM's startup branches on $F338 (observed: a read of $F338 at PC $C26B):
; 0 = "no AUTOEXEC -> prompt", nonzero -> the wrong path (SELDSK/loop). Stock's disk
; ROM clears $F338 at boot; ours never did. We default it to 0 just before handing to
; the boot sector's step-7 entry. $F338 is dual-purpose (a $C9 RET BASIC hook stub on
; C-BIOS vs $00 for DOS), so we SAVE the host value and RESTORE it if the call returns --
; which only a non-system / data disk does (a real DOS disk JPs into MSXDOS.SYS and never
; returns, so the 0 persists to COMMAND.COM's read). The save uses the stack: on the
; no-return DOS path the push is simply abandoned (MSXDOS.SYS resets SP). Called from
; boot_sig_ok with IX=$F195 and the page-0 env laid; replaces the inline `scf; call
; BOOT_ENTRY` there -- net-zero in that $41FD-pad-packed region. (tier2-f338-default-spec.md)
; Also defaults the date-format config cells $F30D/$F30E (M9 date slice): COMMAND.COM
; reads $F30E at PC $CDA7 to format the boot date; ours leaves them $FF
; (uninit) so the date prints malformed and the prompt loops. Stock's disk ROM defaults
; them to $F30D=01 / $F30E=00 at boot (observed black-box; clean-room, no stock bytes).
; Same DOS-only save/restore discipline as $F338, so a returning data disk leaves the
; host's cells untouched (BIOS-agnostic). (tier2-gdate-spec.md)
; Also defaults the printer-echo state cell $F23B (M27, the LSTOUT-DIR-oddity
; follow-up): the main-BIOS RAM scan leaves it $FF at power-on; stock's disk ROM
; zeroes it once during this same boot phase (black-box-pinned write at $57BE,
; t=3.8s during a real DOS boot -- disk/docs/tier2-m27-lstout-spec.md). Left at
; $FF, COMMAND.COM's own DIR line-end code (and its prompt-cycle save/restore)
; treats it as "a list device is attached" and echoes each line's CR/LF to it
; via BDOS $05 LSTOUT -- 2 extra calls per file (documented since M19/M20 as
; "82 spurious per-file LSTOUT calls during DIR", never root-caused until now).
; A single boot-time poke to $F23B (validated: `callseq --poke 0xF23B:0x00`
; fully re-aligns the call stream, "ALIGNED, NO DIVERGENCE in 90 shared calls")
; is sufficient -- COMMAND.COM's own save/restore keeps it at 0 across the
; whole session once seeded. Same DOS-only save/restore discipline as $F338.
dos_handoff:
                call    dos_clear_screen    ; OI-3: blank BASIC banner + home cursor (below)
                ld      a, ($F338)          ; save host $F338 (BASIC hook stub on C-BIOS)
                push    af
                ld      hl, ($F30D)         ; save host $F30D/$F30E (date-format config)
                push    hl
                ld      a, ($F23B)          ; save host $F23B (printer-echo state)
                push    af
                xor     a
                ld      ($F338), a          ; DOS default: $F338 = 0
                ld      ($F23B), a          ; DOS default: $F23B = 0 (no printer echo)
                ld      ($F237), a          ; DOS default: $F237 = 0 (logical console column,
                                            ;   M22b slice 2 -- seed before any output so TAB
                                            ;   expansion + $F237 parity start clean; DOS-console
                                            ;   scratch only, no host save/restore, unlike $F23B.
                                            ;   Safe: p0_env_tab is pinned, so this +3 B doesn't
                                            ;   shift it into the FDC hole)
                ld      hl, $0001
                ld      ($F30D), hl         ; DOS default: $F30D=01, $F30E=00 (date format)
                scf                         ; Cy = 1 -> step-7 "load the system" entry
                call    BOOT_ENTRY          ; DOS disk JPs into MSXDOS.SYS (no return)
                pop     af                  ; data disk returned: recover host $F23B
                ld      ($F23B), a
                pop     hl                  ; recover host values
                ld      ($F30D), hl
                pop     af                  ; recover host $F338
                ld      ($F338), a          ; restore the dual-purpose stub for BASIC
                ret

; --- dos_clear_screen - OI-3: blank the SCREEN-1 name table + home the cursor -----
; Stock's DOS boot handoff clears the leftover BASIC power-on banner before the DOS
; sign-on via a DIRECT name-table fill of spaces (characterised black-box: 0 CHPUT
; form-feeds, no mode switch -- tier2-oi3-spec.md §2), and homes the cursor (stock's
; CSRY/CSRX = $01/$01 at COMMAND.COM $0100). Ours never cleared, so it inherited BASIC's
; screen (banner ROW10-13) and printed the sign-on from CSRY=$0F -> A> at ROW23. This
; reproduces BOTH halves so ours' A> lands at ROW09 matching stock.
;   (i) FILVRM ($0056): A=byte, BC=length, HL=VRAM addr -> fill VRAM[$1800..$1AFF] with
;       $20 (768 = 32*24 SCREEN-1 name-table cells; namebase=$1800 confirmed by the
;       `screen` probe on BOTH machines). Called via the main-ROM inter-slot path
;       (pg0_mainrom_in/out) exactly as conout_body calls CHPUT: page 0 is RAM here
;       (init.asm did page0_ram_in), so we page the main BIOS ROM back in from EXPTBL[0].
;   (ii) cursor-home: CSRY ($F3DC) := 1, CSRX ($F3DD) := 1 (documented work-area sysvars).
; STAY-DI (OI-3 §5.3): the caller (init.asm) holds DI across the whole page-0-RAM handoff
; until MSXDOS.SYS is entered (init.asm:294); we restore page 0 but do NOT `ei` here, to
; avoid an interrupt firing mid-handoff while $0038 is not yet the BIOS handler.
; MUST preserve IX = $F195 (DRVA_DPB, required into MSXDOS.SYS, §8.31/M18) -- FILVRM does
; not contractually preserve IX -> push/pop guards it.
; CLEAN-ROOM: FILVRM $0056 + the $1800/768 SCREEN-1 name-table geometry + CSRY/CSRX
; $F3DC/$F3DD are all documented MSX BIOS ABI / work-area sysvars (cited, not decoded).
dos_clear_screen:
                push    ix                  ; IX=$F195 (DRVA_DPB) must survive into MSXDOS.SYS
                call    pg0_mainrom_in      ; main BIOS ROM -> page 0 (portable, EXPTBL[0])
                ld      a, $20              ; A = space
                ld      bc, $0300           ; BC = 768 = 32*24 name-table cells
                ld      hl, $1800           ; HL = SCREEN-1 name-table base
                call    $0056               ; FILVRM: VRAM[$1800..$1AFF] := $20
                call    pg0_mainrom_out     ; restore page 0 = RAM (STAY-DI: no ei)
                pop     ix
                ld      a, $01
                ld      ($F3DC), a          ; CSRY := 1 (home row, 1-based)
                ld      ($F3DD), a          ; CSRX := 1 (home col, 1-based)
                ret

; ===== M22a: relocated bodies (freed their old low-region spans for the new
; CPMVER/DIRIN/GTIME/STIME/VERIFY canonical entries) + p0_env_tab's new home ===

; fat_find_body — unchanged from its old $5457 slot (kernel.asm), relocated here
; because that slot collided with the $5462 DIRIN canonical entry
; (tier2-m22-cpmver-spec.md §4.6). Position-free: reached only by label from
; fat.asm's `fat_find: jp fat_find_body` veneer.
fat_find_body:
                ld      (FAT_NAMEPTR), hl
                ld      hl, (FAT_FIRSTROOT)
                ld      (FAT_DIRSEC), hl
                ld      hl, (FAT_ROOTSECS)
                ld      (FAT_DIRREM), hl
                jp      ff_secloop

; ===== fdc_entloop_body / fdc_useslot_body + p0_env_tab: RELOCATED OUT =========
; (2026-07-04, FDC-window P0 fix.) These three position-free blocks used to sit HERE
; in the page-1 tail. The National WD2793 FDC registers ($7FB8-$7FBF, equates.inc)
; are memory-mapped AND mirrored x8 across the WHOLE $7F80-$7FBF window, so bytes
; placed at $7F80-$7FBF read back as FDC register values, not opcodes/data. That is
; exactly where fdc_useslot_body (create's dir-slot claim, $7F8E) landed after ~M27,
; so FMAKE never persisted a directory entry -> create/write silently broke, and
; p0_env_tab's head entries ($7FB7-$7FBF) read back as register garbage. All three
; are reached only by label (fdc_entloop/fdc_useslot veneers; lay_page0_env's
; `ld hl, p0_env_tab`), so they now live in the COMMAND.COM-load free-region corridor
; (kernel.asm, between the $607B and $75A5 kernel veneers -- 0 canonical entries, no
; window). fat_find_body stays here: it ends at $7F5F, below the window. Spec:
; tier2-remediation-spec.md Phase B.
;
; ===== FDC-window guard (TRUE window $7F80-$7FBF, root-caused 2026-07-04) =========
; NOTHING -- executable OR data-read-through-the-page -- may land in $7F80-$7FBF:
; every address there aliases the WD2793 register file (the canonical 8 registers
; $7FB8-$7FBF mirrored x8). The window is now entirely dead $00 pad. The IF turns any
; below-window code that grows INTO the window into a LOUD build error (a bare
; negative `ds` only warns -> a silent empty object).
                IF ($ > $7F80)
FDC_WINDOW_INTRUSION: equ below_window_code_grew_into_the_7F80_FDC_register_window
                ENDIF
                ds      $7FD1 - $, $00      ; skip OVER the dead $7F80-$7FBF FDC window
                                            ; and pin the conout block at its $7FD1 home

; ===== M22b slice 2: conout_emit_e, ABOVE the FDC window =====================
; conout_body's stub + conout_tab (below the window) reach this by absolute call. The
; `ds` above pins it at $7FD1 -- above the window top $7FBF -- so its own instruction
; fetches never read FDC registers. The IF guard below fires loudly if it would ever
; start in/below the window. Spec: tier2-m22b-slice2-reloc-spec.md.
                IF ($ <= $7FBF)
CONOUT_EMIT_IN_HOLE: equ conout_emit_e_would_start_in_or_below_the_FDC_register_window
                ENDIF
; conout_emit_e — CHPUT the char in E via the proven M8/M10 inter-slot window, then
; maintain the logical column at $F237 (CR -> 0, LF -> unchanged, else col++). The
; column work runs INSIDE this routine's HL push/pop guard, so conout_body keeps its
; BC/DE/HL/IX/IY-preserved contract (the kernel console loop holds its string pointer
; in HL -- clobbering it derails the DOS boot). $F237 is a pinned page-1 kernel-ABI
; DATA cell shared across every output path (func-2/func-9/BUFIN-echo, §5.5); using the
; literal address keeps future --mem 0xF100:0x300 capture diffs byte-clean. CLEAN-ROOM:
; the do-while tab rule + column semantics are re-derived from OUR OWN injected TABTEST
; files' observable output + the published _CONOUT contract; no stock bytes decoded.
;   in: E=char ; out: A = the UPDATED $F237 column (NOT the char -- the TAB loop tests
;   A & 7; conout_body's normal path reloads the char via `ld a,e`); BC/DE/HL/IX/IY preserved.
conout_emit_e:
                ld      a, e                ; char arrives in E ($5454 CONOUT contract)
                ld      (CONOUT_CHAR), a    ; stash the char (A is needed for slot work)
                push    bc
                push    de
                push    hl
                di                          ; no interrupt while the BIOS is half-mapped
                call    pg0_mainrom_in
                ld      a, (CONOUT_CHAR)
                call    $00A2               ; CHPUT - emit A; preserves all registers
                call    pg0_mainrom_out     ; restore page 0
                ei
                ld      hl, $F237           ; column cell (HL saved above -> caller HL safe)
                ld      a, (CONOUT_CHAR)
                cp      $0D                 ; CR -> column := 0
                jr      z, conout_emit_cr
                cp      $0A                 ; LF -> column unchanged (BIOS CHPUT owns the row)
                jr      z, conout_emit_done
                inc     (hl)                ; printable/other -> column++ (post-increment)
                jr      conout_emit_done
conout_emit_cr:
                ld      (hl), 0             ; CR -> column := 0
conout_emit_done:
                ld      a, (hl)             ; A := the updated column (HL still $F237)
                pop     hl
                pop     de
                pop     bc
                ret

; --- pad to a full 16 KB page ($4000-$7FFF) --------------------------------
                ds      $8000 - $, $00
