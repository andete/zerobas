#!/usr/bin/env python3
"""D-PASMO053 (Joost 2026-10-11: "make it work with pasmo 0.5.3"): drop the two
IFNDEF guards pasmo 0.5.3 rejects. The sub-ROM ABI gets ONE definition (basic/
sysvars.inc, included by both builds); GFX_UNGUARDED becomes a plain equ the
teeth build edits in a copied tree instead of `--equ`. Anchored; refuses."""
import re, sys

def sub(path, old, new, count=1):
    s = open(path).read()
    n = s.count(old)
    if n != count:
        sys.exit(f"REFUSE {path}: anchor found {n}x: {old[:60]!r}")
    open(path, "w").write(s.replace(old, new))
    print(f"ok {path}")

S = "basic/sysvars.inc"
sub(S, """; IFNDEF-guarded: sub.asm includes BOTH this and sub/equates.inc (which defines
; these first), so the guard lets the sub build reuse those and the main build
; (no equates.inc) define its own — one ABI, no double-definition.
    IFNDEF SUBROM_ENTRY_BASE_P0
SUBROM_ENTRY_BASE_P0 equ $0040""", """; THE ONE DEFINITION (D-PASMO053, 2026-10-11): both builds include this file,
; so the sub-ROM ABI lives here alone. It used to be IFNDEF-guarded against a
; second copy in sub/equates.inc -- pasmo 0.5.3 (what Debian / Ubuntu ship)
; rejects IFNDEF, and the two copies had nothing checking they agreed.
SUBROM_ENTRY_BASE_P0 equ $0040""")
sub(S, """                                ; Sole caller basic/program.asm `parse_lineno`.
    ENDIF
; EXBRSA ($FAF8)""", """                                ; Sole caller basic/program.asm `parse_lineno`.
; EXBRSA ($FAF8)""")

E = "sub/equates.inc"
s = open(E).read()
names = """SUBROM_ENTRY_BASE_P0 SUBROM_ENTRY_BASE_P1 SUBROM_IDX_TOKENISE SUBROM_IDX_DETOK
SUBROM_IDX_INTTEST SUBROM_IDX_ARY SUBROM_IDX_STRHEAP SUBROM_IDX_PU_TOFIELD SUBROM_IDX_PU_TAIL
SUBROM_IDX_FORMAT SUBROM_IDX_SCANSTMT SUBROM_IDX_FATPRIM SUBROM_IDX_DIRVERB
SUBROM_IDX_PLAY_PARSE SUBROM_IDX_LINEEDIT SUBROM_IDX_CASMATCH SUBROM_IDX_TITLE
SUBROM_IDX_FCBNAME SUBROM_IDX_ERRMSG SUBROM_IDX_PARSELN SUBROM_IDX_GRAPHICS
SUBROM_IDX_READVAL SUBROM_IDX_BEEP SUBROM_IDX_FLDLOOK SUBROM_IDX_LRSETST""".split()
gone = 0
for nm in names:
    rx = re.compile(r"^" + nm + r"\s+equ\s+[^\n]*\n", re.M)
    hits = rx.findall(s)
    if len(hits) != 1:
        sys.exit(f"REFUSE {E}: {nm} found {len(hits)}x")
    s = rx.sub(f"; ({nm}: defined in basic/sysvars.inc -- D-PASMO053)\n", s)
    gone += 1
anchor = """; --- Entry-table bases (the $4010-style fixed dispatch contract, §3c/D-5) -----"""
if s.count(anchor) != 1:
    sys.exit("REFUSE header anchor")
s = s.replace(anchor, """; 🔁 D-PASMO053 (2026-10-11): the SUBROM_* bases and indices are DEFINED ONCE, in
; basic/sysvars.inc, which this build includes too. The notes below stay beside
; where each used to be defined; SUBROM_IDX_PING alone is still defined here.
""" + anchor)
old_g = """; with `pasmo --equ GFX_UNGUARDED=1` strips the guard, so the floor gate can
; confirm it then FAILs (latch race observed) -- proving the guarded pass is a
; real result, not a test that cannot fail. NEVER shipped =1.
    IFNDEF GFX_UNGUARDED
GFX_UNGUARDED           equ     0
    ENDIF
"""
new_g = """; with GFX_UNGUARDED = 1 strips the guard, so the floor gate can confirm it then
; FAILs (latch race observed) -- proving the guarded pass is a real result, not
; a test that cannot fail. NEVER shipped =1. (D-PASMO053: the teeth build edits
; THIS line in a copy of sub/ -- it was `pasmo --equ` over an IFNDEF, neither of
; which pasmo 0.5.3 has. The Makefile refuses if the edit did not land.)
GFX_UNGUARDED           equ     0
"""
if s.count(old_g) != 1:
    sys.exit("REFUSE gfx anchor")
s = s.replace(old_g, new_g)
open(E, "w").write(s)
print(f"ok {E} ({gone} duplicates removed)")

M = "Makefile"
sub(M, """	$(PASMO) -I sub --equ GFX_UNGUARDED=1 --bin $(SUB_SRC) $(BUILD)/sub-unguarded.rom
""", """	rm -rf $(BUILD)/sub-unguarded-src && mkdir -p $(BUILD)/sub-unguarded-src
	cp -R sub/. $(BUILD)/sub-unguarded-src/
	sed -e 's/^GFX_UNGUARDED\\(  *\\)equ\\(  *\\)0$$/GFX_UNGUARDED\\1equ\\21/' sub/equates.inc \\
	  > $(BUILD)/sub-unguarded-src/equates.inc
	grep -q '^GFX_UNGUARDED  *equ  *1$$' $(BUILD)/sub-unguarded-src/equates.inc
	$(PASMO) -I $(BUILD)/sub-unguarded-src --bin $(BUILD)/sub-unguarded-src/sub.asm \\
	  $(BUILD)/sub-unguarded.rom
""")
