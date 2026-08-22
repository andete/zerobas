; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; deffn.asm -- D-DEFFNEV: DEF FN's PARSE, as a PAGE-0 sub-ROM tenant
; (SUBROM_IDX_DEFFN). docs/spec-basic-deffnev.md.
;
; 🔴 THIS FILE IS A SIZING STUB AND NOTHING ELSE. It exists so the SHIPPING main
; ROM can be assembled and its wall READ, which is the one question the funding
; arithmetic turns on: how many bytes does evicting the parse actually give
; back? (docs/deffn-impl-2026-08-22.md §7 estimated ~110 B and said, in the
; slice's own words, that it needed the same treatment the impl gave the first
; draft: BUILD IT AND READ THE WALL.)
;
; ⚠️ WHAT IT DOES NOT DO: parse anything. Every entry answers "request 0, raise
; FN_TYP" with ERR 18, so a build carrying this tenant makes every `FN...` call
; answer `Undefined user function` and `make deffn-acceptance` fails 69 rows BY
; CONSTRUCTION. A wall reading taken against it is a statement about the MAIN
; ROM's size and about nothing else -- exactly the standing rule that a
; scaffolded build is a different machine
; ([[a-scaffolded-build-is-a-different-machine]]).
;
; The real tenant owes, and none of it is written here:
;   * the name resolve and the ERR 18 that outranks every other fault
;   * the two lists walked together, and the delimiter agreement that IS the
;     arity rule (ERR 2 at `FNA(1,2)`, `FNA(1)` and `DEF FNA(B(1))=`)
;   * fn_slot: the shadow-slot header, FN_SLOTP/FN_FEND growth, and the ceiling
;     ERR 5 that is a division and not a rule
;   * both directions of ERR 13, which is why one `evaluate` request serves both
;     the actuals and the body
;   * the $FFFF-keyed result slot the coercion rides
; and sub-side clones of `var_name_key` + `deftbl_lookup`, because -- MEASURED
; this session -- NO page-0 tenant in this tree calls main page 1 by absolute
; address, and there is no import mechanism for it: `sub/basic-resident-abi.inc`
; is generated for PAGE-1 tenants calling main's LOW region, and asserts every
; symbol is below the low ceiling. `sub/deftype.asm` clones `skip_spaces`
; sub-locally for exactly this reason. That clone is free (sub page 0 has 3 KB)
; but it is WORK, and the impl doc's "~46 B of new tenant glue" did not have it.
;
; Clean-room: original code.

deffn_tenant:
                ld      a,18                ; Undefined user function
                ld      (FN_TYP),a
                xor     a                   ; request 0 = raise FN_TYP
                ret
