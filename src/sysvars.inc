; sysvars.inc — BIOS entry points and RAM scratch for zerobas.
;
; CLEAN-ROOM: every address below is traced to an allowed source (see
; PROVENANCE.md). No value is taken from any MSX-BASIC / GW-BASIC disassembly
; or from a reference ROM disassembly.

; --- Cassette BIOS entry points -------------------------------------------
; Source: MSX Assembly Page BIOS call list / MSX2 Technical Handbook,
;         cassette I/O chapter.
TAPION          equ     $00E1   ; read tape header (motor on); CF set = fail
TAPIN           equ     $00E4   ; read one byte -> A;           CF set = fail
TAPIOF          equ     $00E7   ; stop the tape motor

; --- Binary (BSAVE) file identifier ---------------------------------------
; Source: MSX2 Technical Handbook, BSAVE file format ("D0" x10 = binary).
BINARY_ID       equ     $D0

; --- RAM scratch (page-3 RAM; NOT part of the ROM image) -------------------
; Chosen to avoid the demo blob's regions ($C000 load, $E000 "JONG" marker).
; These hold the three address words read from the .cas data header.
CURPTR          equ     $E020   ; current load pointer (2 bytes)
ENDPTR          equ     $E022   ; final load address  (2 bytes)
EXECPTR         equ     $E024   ; execution address   (2 bytes)
ERRMARK         equ     $E010   ; error landmark marker byte
