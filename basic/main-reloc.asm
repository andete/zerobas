; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; zerobas — main-reloc.asm  (cbios-repack arc, WS-2 / S3)
; ===========================================================================
; Relocated BASIC variant: the same interpreter as main.asm, based at $2812
; instead of $4000, spanning the reclaimed page-0 low region ($2812-$3FFF) plus
; the existing page-1 image ($4000-$7FFF) — one contiguous ~21.5 KB slot-0 image.
;
; This is the entry point for the SHIPPING repack build: the merged main-ROM patch
; (zerobas-main-eu.ips/.bps, `make repack-main`) assembles the interpreter through
; this wrapper, and it is also the build that carries the repack-only string engine
; (basic/str-engine.asm, gated IF ROM_BASE < $4000). `make basic-reloc` still uses
; it to prove the relocation assembles clean with the "AB" header pinned at $4000
; (see docs/cbios-repack-ws2-audit.md). The lean production basic.rom stays 16 KB
; (default ROM_BASE=$4000) and is byte-identical regardless.
;
; All it does is pre-define ROM_BASE, then include the real source. Because the
; audit proved the interpreter is 100% label-based, this single symbol is the
; whole relocation.
;
; Clean-room: this wrapper adds NO behaviour of its own — it only sets ROM_BASE and
; includes basic/main.asm, whose clean-room discipline (nothing derived from any
; disassembly; see basic/PROVENANCE.md) governs every byte assembled here. No
; disassembly.
; ===========================================================================

ROM_BASE:       equ     $2812

                include "basic/main.asm"
