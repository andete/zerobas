; bload.asm — the BLOAD"CAS:",R tracer bullet.
;
; This is the *interpreter half* of BLOAD: it does NOT decode the cassette
; signal itself (that is the BIOS "device half" — TAPION/TAPIN). It drives the
; documented cassette BIOS contract to read a BSAVE-format binary, places the
; bytes in RAM, and performs the ,R handoff by jumping to the exec address.
;
; Derived only from cbios-basic/docs/spec-bload-r.md (this project's own
; black-box oracle observation) + the MSX2 Technical Handbook. No disassembly.
;
; For this first build the line is not tokenised: INIT *is* the BLOAD. A later
; phase adds the tokeniser / execution loop in front of this routine.

; INIT entry (cartridge header points here; lands at $4010 by construction).
init:
                ; --- open the tape and skip the file-header block's tone ---
                call    TAPION              ; sync block 1 (file header)
                jp      c,load_error

                ; --- file-header block: 10x BINARY_ID + 6-char filename ---
                ; spec-bload-r.md §1: header block is 16 bytes; byte 0 is the
                ; binary-file id. We verify the id and discard the rest.
                call    TAPIN
                jp      c,load_error
                cp      BINARY_ID           ; must be a binary (BSAVE) file
                jp      nz,load_error
                ld      b,15                ; remaining header bytes
skip_hdr:
                push    bc                  ; TAPIN trashes all regs
                call    TAPIN
                pop     bc
                jp      c,load_error
                djnz    skip_hdr

                ; --- data block: skip its tone, then read the 6-byte header --
                call    TAPION              ; sync block 2 (data)
                jp      c,load_error

                ; spec-bload-r.md §1: start(LE), end(LE), exec(LE).
                ; TAPIN trashes every register, so store each byte immediately.
                call    TAPIN
                ld      (CURPTR),a          ; start low
                call    TAPIN
                ld      (CURPTR+1),a        ; start high
                call    TAPIN
                ld      (ENDPTR),a          ; end low
                call    TAPIN
                ld      (ENDPTR+1),a        ; end high
                call    TAPIN
                ld      (EXECPTR),a         ; exec low
                call    TAPIN
                ld      (EXECPTR+1),a       ; exec high

                ; --- load loop: bytes start..end inclusive, verbatim --------
                ; spec-bload-r.md §2. State lives in RAM because TAPIN trashes
                ; all registers on every call.
load_loop:
                call    TAPIN
                jp      c,load_error
                ld      hl,(CURPTR)
                ld      (hl),a              ; store the byte
                ld      de,(ENDPTR)
                ld      a,h
                cp      d
                jr      nz,load_next        ; high bytes differ -> more to do
                ld      a,l
                cp      e
                jr      z,load_done         ; cur == end -> last byte stored
load_next:
                inc     hl
                ld      (CURPTR),hl
                jr      load_loop

load_done:
                call    TAPIOF              ; motor off

                ; --- ,R handoff: jump to the exec address -------------------
                ; spec-bload-r.md §3.
                ld      hl,(EXECPTR)
                jp      (hl)

; --- error path: stop the tape, drop a marker, halt at a fixed landmark -----
; Reached when a cassette BIOS call fails (CF set) or the file is not binary.
; Under bare C-BIOS this fires immediately: its TAPION/TAPIN are stubs that
; always set CF (see reference/cbios/src/main.asm). That is the documented gap.
load_error:
                call    TAPIOF
                ld      a,$EE
                ld      (ERRMARK),a
err_halt:
                jr      err_halt
