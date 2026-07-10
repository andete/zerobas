; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas — main-reloc.asm  (cbios-repack arc, WS-2 / S3)
; ===========================================================================
; Relocated BASIC variant: the same interpreter as main.asm, based at $2812
; instead of $4000, spanning the reclaimed page-0 low region ($2812-$3FFF) plus
; the existing page-1 image ($4000-$7FFF) — one contiguous ~21.5 KB slot-0 image.
;
; This is a PROOF/STAGING artifact, NOT a shipping deliverable: it is deliberately
; kept out of `make all`. It exists so `make basic-reloc` can prove the relocation
; assembles clean with the "AB" header still pinned at $4000 (see
; docs/cbios-repack-ws2-audit.md). Wiring the relocated image into the merged
; main-ROM patch is WS-3 (S4); until then the production basic.rom stays 16 KB.
;
; All it does is pre-define ROM_BASE, then include the real source. Because the
; audit proved the interpreter is 100% label-based, this single symbol is the
; whole relocation.
; ===========================================================================

ROM_BASE:       equ     $2812

                include "basic/main.asm"
