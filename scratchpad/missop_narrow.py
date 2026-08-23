#!/usr/bin/env python3
"""Apply D-MISSOP's NARROWING: move the deferred code off the shared tail.

The wide siting (at `ev_f_err`) gave ERR 24 to all EIGHT of that tail's jump
sites, and only ONE of them is the missing operand. `make lineerr-acceptance`
caught it: row `a.noclose` (`LINE (11,12-(20,21)`) hits expr.asm:807 -- a
parenthesised expression closed by ',' instead of ')' -- where both references
say Syntax error (ERR 2).

So the code moves to its OWN label, reached only from ev_f_var's `is_letter`
failure (expr.asm:556), which is the one site that means "a factor was required
and what is here cannot start one". `ev_f_err` goes back to being the silent
landmark it was for every other site.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXPR = ROOT / "basic/expr.asm"
s = EXPR.read_text()

# 1. revert ev_f_err to its original body, keeping the explanation at the new home
WIDE = """ev_f_err:
                ; D-MISSOP (docs/spec-basic-missop.md §5): a factor was REQUIRED
                ; and what is here cannot start one -- end of line, ':' , or a
                ; stray operator. Both references call that `Missing operand`
                ; (ERR 24) at EVERY such slot, measured at 16 of them; this
                ; routine used to return DE=0 with only the ERRMARK landmark, so
                ; `POKE &HE000,` COMPLETED and WROTE A ZERO.
                ; 🎯 SITED HERE, NOT AS A NEW TEST IN ev_f, BECAUSE THE
                ; REFERENCES PUT THE LINE EXACTLY WHERE ev_f ALREADY PUTS IT:
                ; an empty operand closed by ')' or ',' is `Syntax error` and
                ; reaches ev_f_empty; everything else is `Missing operand` and
                ; reaches HERE. Row poke.plus (`POKE &HE000,+` -> 24, not 2) is
                ; what decides that, and poke.paren (`,)` -> 2 on all three) is
                ; what says the other site must keep its own code.
                ; ⚠️ THE FALL-THROUGH FROM ev_f_defer IS WHY THIS IS FREE OF A
                ; BRANCH: penderr_set is SET-IF-EMPTY and preserves every
                ; register AND the flags, so a code already deferred just above
                ; (4/3/10) WINS and this call is a no-op on that path.
                ld      a,FPERR_MISSOP
                call    penderr_set
                ld      a,$DD               ; expression error marker
"""
NARROW = """ev_f_err:                                   ; the SILENT landmark, and it stays silent:
                                            ; D-MISSOP's deferred code lives at
                                            ; ev_f_missop above, reached from ONE of this
                                            ; tail's eight jump sites. See there.
                ld      a,$DD               ; expression error marker
"""
assert s.count(WIDE) == 1, "wide block not found"
s = s.replace(WIDE, NARROW, 1)

# 2. add ev_f_missop beside the other deferred-code stubs, before ev_f_empty
ANCHOR = "ev_f_empty:                                 ; D-F2-3: the empty parenthesised/argument\n"
MISSOP = """ev_f_missop:                                ; D-MISSOP (docs/spec-basic-missop.md §5/§13):
                                            ; a factor was REQUIRED and what is here cannot
                                            ; start one -- end of line, ':', or a stray
                                            ; operator. Both references call that `Missing
                                            ; operand` (ERR 24) at every such slot, measured
                                            ; at 16 of them; before this, ev_f_err returned
                                            ; DE=0 with only the ERRMARK landmark, so
                                            ; `POKE &HE000,` COMPLETED and WROTE A ZERO.
                                            ; 🔴 IT IS ITS OWN LABEL, NOT A LINE ADDED TO
                                            ; ev_f_err, AND A SHIPPED GATE IS WHY. The first
                                            ; draft sat on that shared tail -- which has
                                            ; EIGHT jump sites, only ONE of them this one.
                                            ; `make lineerr-acceptance` went 209/210: row
                                            ; a.noclose (`LINE (11,12-(20,21)`) reaches
                                            ; expr.asm's `cp ')' / jp nz,ev_f_err` for a
                                            ; parenthesised expression closed by ',', and
                                            ; BOTH references call that Syntax error (2).
                                            ; Reached only from ev_f_var's `is_letter`
                                            ; failure. Same `ld e,<code> / jr ev_f_defer`
                                            ; idiom as ev_f_tmm / ev_f_ifc above.
                ld      e,FPERR_MISSOP
                jr      ev_f_defer
"""
assert s.count(ANCHOR) == 1, "ev_f_empty anchor not found"
s = s.replace(ANCHOR, MISSOP + ANCHOR, 1)

# 3. retarget the ONE site that means "a factor was required"
SITE = """                call    is_letter           ; must start with a letter
                jr      nc,ev_f_err
"""
SITE_NEW = """                call    is_letter           ; must start with a letter
                jr      nc,ev_f_missop      ; D-MISSOP: THE missing-operand site
"""
assert s.count(SITE) == 1, "ev_f_var site not found"
s = s.replace(SITE, SITE_NEW, 1)

EXPR.write_text(s)
print("narrowed: ev_f_missop added, ev_f_err reverted, :556 retargeted")
