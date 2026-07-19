<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Scope + spec — **D-F2-2 int-argument coercion** (Overflow/illegal-fn on out-of-domain args)

Status: **IN PROGRESS.** Signed off; **stage A1 (OUT) LANDED 2026-07-19** (self-funded by
tightening the sibling `do_vpoke` to the shared `check_fperr_only`, page-1 0→6 B; gated in
`make intarg-acceptance`). A1's empirical pass also CORRECTED the surface: VPOKE's domain is
the VRAM size 0..16383, not the address domain — it moves to stage B (§1.1). **A2's empirical
pass (2026-07-19, `char_a2_vpeek.py`) then (i) RESOLVED Q1 → an inline FPERR check at
`ev_ff_arg`, not the statement boundary (the ref aborts even in FOR bounds), and (ii) caught
a SECOND missing site: `VPEEK`, the read-twin of VPOKE with the identical VRAM 0..16383 domain
(§1.1).** A2 (PEEK/INP) and B (STRING$/SPACE$/ON/WIDTH + VPOKE + VPEEK) pending sign-off.
This is the scope/design doc for the last cross-cutting faithfulness residual after the
error-handling arc closed (2026-07-19). It fixes the "silent eager `flt_to_int16`" that
every int-argument statement/function *not* explicitly wired during F2 (POKE/VPOKE/HEX$/
PRINT) still uses, so out-of-domain integer arguments raise the reference's error instead
of silently coercing to a wrong value. Surface is **empirically pinned on the Philips
VG-8020** (never by reading the reference ROM — [[no-reference-rom-disasm]]).

Provenance anchor: `basic/PROVENANCE.md` §3077 ("D-F2-2: OUT's port/value … every OTHER
int-argument statement not explicitly named above is the same residue — deferred, not a
correctness bug within F2's stated scope"). Related landed sibling: the channel-eval
`eval_chan` coercion (INPUT#/PRINT# channel numbers, spec-basic-error-handling.md §5.7) and
the `ERROR n` 1..255 validation (2026-07-19) — both are the same "wire a checked coercion"
move at one site; this doc generalises it to the remaining surface.

---

## 1. The empirically-pinned surface

Every case below: `10 ON ERROR GOTO 100 / 20 <stmt with out-of-domain arg> / 30 …:END /
100 …ERR…` on VG-8020 (ref) vs the repack (zb). Result = the trapped `ERR`, or `cont`
(no error, silently continued). Probe: `scratchpad/char_intarg.py` (to be promoted to a
gated differential, §7).

### 1.1 Divergent sites (ref raises, zb silently continues)

**Group A — ADDRESS domain** (`fac_to_int_addr`: valid −32768..65535 wrap-then-truncate;
Overflow ERR 6 only beyond). This is the SAME domain POKE/VPOKE already use.

| Site | Code | `arg=40000` | `arg=99999` | `arg=-1` | zb today |
|---|---|---|---|---|---|
| `OUT p,v` (both args) | `basic/vdpio.asm` `do_out` | cont | **ERR 6** | cont | cont (silent) |
| `PEEK(a)` | `basic/expr.asm` (ev PEEK) | cont | **ERR 6** | cont | cont (silent) |
| `INP(p)` | `basic/expr.asm` (ev INP) | cont | **ERR 6** | cont | cont (silent) |

**Group B — RANGE-checked** (int16-coerce → Overflow ERR 6 if `|x|>32767`; then range-check
to the site's valid max → illegal function call ERR 5 outside). The GETBYT pattern, with a
per-site upper bound (0..255 for the byte sites, 0..16383 for VPOKE's VRAM address).

| Site | Code | valid max | `=max+1` | `=32768` | `=-1` | zb today |
|---|---|---|---|---|---|---|
| `STRING$(n,…)` count | `basic/str-engine.asm` `str_fn_string` | 255 | ERR 5 | ERR 6 | ERR 5 | cont |
| `STRING$(n,c)` char-code | `str_fn_string` | 255 | ERR 5 | ERR 6 | ERR 5 | cont |
| `SPACE$(n)` | `str-engine.asm` `str_fn_space` | 255 | ERR 5 | ERR 6 | ERR 5 | cont |
| `ON n GOTO/GOSUB` | `basic/program.asm` `ex_on` | 255 | ERR 5 | ERR 6 | ERR 5 | cont |
| `WIDTH n` | `basic/screen.asm` `ex_width` | 255 | ERR 5 | ERR 6 | ERR 5 | cont |
| **`VPOKE addr`** | `basic/vdpio.asm` `do_vpoke` | **16383** | ERR 5 | ERR 6 | ERR 5 | **cont (WRONG)** |
| **`VPEEK(addr)`** | `basic/expr.asm` `ev_ff_vpeek` | **16383** | ERR 5 | ERR 6 | ERR 5 | **cont (MISSING)** |

**VPEEK correction (found by the A2 empirical pass 2026-07-19, `scratchpad/char_a2_vpeek.py`):**
VPEEK was **absent from the draft surface entirely** — the read-twin of VPOKE, and the second
VPOKE-class omission the empirical discipline has caught. The VG-8020 domain sweep is byte-for-byte
identical to VPOKE's: `VPEEK(16383)`=cont, `VPEEK(16384)`=**ERR 5**, `VPEEK(32768)`/`(40000)`/
`(99999)`=**ERR 6**, `VPEEK(-1)`=**ERR 5**. So VPEEK is a Group-B VRAM site (int16-coerce → ERR 6
if `|x|>32767`, then 0..16383 range-check → ERR 5 outside), NOT the address domain PEEK/INP use. It
is a *function* though (Q1 propagation applies), so it lands with VPOKE on the shared VRAM leaf
(stage B) but reuses A2's inline-abort-at-the-function mechanism (§3.1).

`ON 0 GOTO` = cont on BOTH (0 is the valid "no branch" selector, not an error).

**VPOKE correction (found by the A1 empirical pass 2026-07-19):** VPOKE was wired during F2
to `fac_to_int_addr` (address domain 0..65535) and previously assumed "already faithful"
(only `VPOKE 99999`→ERR 6 had been checked, which the too-wide domain happens to get right).
But the reference restricts VPOKE's address to the **VRAM size 0..16383** — `VPOKE 16384..
32767`→**ERR 5**, `>32767`→**ERR 6**, `-1`→**ERR 5**. So VPOKE is a Group-B site (int16 +
0..16383 range-check), NOT an address-domain one. The A1 `do_vpoke` tidy (§3.1) left this
pre-existing domain behaviour-equivalent (still too wide); the fix belongs to stage B.

### 1.2 Already faithful (NO work — regression-guard only)

POKE addr/val, HEX$, PRINT (F2-wired, full address domain — POKE `40000`/`-1`/`65535` all
cont, `99999`→ERR 6, confirmed); `DIM A(n)`, array subscripts, `TAB(n)`, `SPC(n)` (raise
ERR 6 on 99999). These prove the fix templates already ship. (**VPOKE was mistakenly here
in the draft — it is a Group-B site, see above.**)

### 1.3 Out of scope

* Statements zerobas does not implement: `WAIT`, `LOCATE`, integer-typed `FOR I%` loop var
  (each currently `syntax error` — a *feature-absence* matter, not a coercion one).
* `FOR`/`STEP` bounds with a **float** loop variable: the bound is legitimately a float
  (no coercion) — `FOR I=1 TO 99999` = cont on both. Correct as-is.
* The int16→float PRINT widening (`ERL`, ABS(-32768), …) — already handled (F3/S2a).

---

## 2. Current zerobas mechanism (why it silently coerces)

`eval` returns `DE` = the value run through **`flt_to_int16`** (`basic/float.asm:379`):
out-of-int16 → **DE = 0, no FPERR**. So any `call eval` + use-`DE`/`E` site silently
accepts a wrong value. The checked alternatives already exist and are used by the wired
sites:

* **`fac_to_int_addr`** (`float-arith.asm:1268` / helper `eval_addr`) — address domain
  −32768..65535, wrap-then-truncate, **FPERR=1 (Overflow) outside**. Group A wants this.
* **`fac_to_int_strict`** (`float-arith.asm:1251`) — strict int16 −32768..32767, **FPERR=1
  outside**. The int16 layer of Group B.

The wired template (POKE, `basic/poke.asm:18`): `call eval_addr` (replaces `call eval`,
byte-neutral) then ONCE per statement `ld a,(FPERR) / or a / jp nz,fp_runtime_error`.
`fp_runtime_error` maps FPERR 1 → ERR 6 via `fperr_to_err` (interp.asm) and aborts/traps
through the landed S1/S2a/S2b funnel.

---

## 3. Design

### 3.1 Group A (address domain) — `eval_addr` + FPERR check

* **`OUT p,v`** (`do_out`, a *statement*): mirror POKE exactly — both `call eval` →
  `call eval_addr` (repack-gated, lean keeps `eval`), one `FPERR` check before the `OUT`.
  Lowest risk; the template is proven.
* **`PEEK(a)` / `INP(p)`** (*functions*): swap their coercion (`flt_to_int16` →
  `fac_to_int_addr`) so an out-of-domain arg sets FPERR **at the function**, then an
  **INLINE FPERR check at `ev_ff_arg`** (`expr.asm`, the shared PEEK/VPEEK/INP parse point)
  aborts immediately via `fp_runtime_error`.
  **Q1 RESOLVED 2026-07-19 (`scratchpad/char_a2_vpeek.py`) — inline, NOT the boundary path.**
  Two empirical facts settle it: (a) the FPERR model is sound for propagation — `exec_stmt`
  (interp.asm:130) clears FPERR once per statement, float ops only ever *set* it (sticky, no
  mid-expression unwind, interp.asm:508), so `A=PEEK(99999)+1` carries the flag to a boundary.
  BUT (b) the reference aborts at the function in **every** consuming context, including ones
  that run **no** `check_expr_errors`: `FOR I=PEEK(99999) TO 1` and `FOR I=1 TO PEEK(99999)`
  both → **ERR 6** on VG-8020 (FOR bounds skip the check per [[empty-expr-syntax-error]]'s
  landmine). The boundary path structurally cannot reproduce those, so it is **rejected**. An
  inline check at `ev_ff_arg` reproduces the ref in all contexts (LET/PRINT/IF/POKE-addr/FOR/
  nested `PEEK(PEEK(…))`/array-subscript — all pinned → ERR 6) with **one** check covering
  PEEK+INP+VPEEK, since all three share that parse point. Raising from inside `eval` is safe
  now that the error arc's `raise_error`/SAVSTK unwinds from arbitrary call depth (the F2-era
  reason the boundary model existed no longer binds; `ev_f_err` already aborts from here).
  Cost: the inline check is **not** byte-neutral (unlike A1's statement-site swaps) — needs a
  small funder (§5).

### 3.2 Group B (byte domain) — int16 overflow + 0..255 guard

zerobas currently does **neither** layer (STRING$(256) = cont). Faithful = coerce int16
(Overflow ERR 6 outside), then `0..255` range-check (illegal fn ERR 5 outside). A shared
leaf, `get_byte_arg` (working name):

```
get_byte_arg:            ; in: FAC/DE = evaluated numeric; out: A = byte 0..255
        call fac_to_int_strict   ; DE = int16, FPERR=1 if |x|>32767
        ld   a,(FPERR)
        or   a
        jp   nz,fp_runtime_error ; -> ERR 6 Overflow
        ld   a,d
        or   a
        jr   nz,gba_illegal      ; high byte set -> >255 -> illegal fn
        ld   a,e
        ret                      ; 0..255 OK (E)
gba_illegal:
        ld   a,5
        jp   raise_error         ; ERR 5 illegal function call
```

Each of `str_fn_string` (×2 args), `str_fn_space`, `ex_on`, `ex_width` routes its arg
through `get_byte_arg` instead of the silent low-byte read. **OPEN QUESTION Q2 (page
visibility):** `fac_to_int_strict`/`raise_error` are page-0/page-1 **main**; STRING$/SPACE$
live partly in **sub-ROM string tenants** (`str-engine.asm` SUBROM_IDX_STRHEAP family).
`get_byte_arg` must sit where each caller can reach it — likely **main-resident**, with the
sub-side callers marshalling the arg out to main (the shape-C pattern already used for the
string tenants). Confirm each Group-B caller's page before siting the leaf.

### 3.3 Shared vs per-site

Group A = 3 sites, one proven template, ~byte-neutral swaps + a couple FPERR checks.
Group B = 5 arg-sites through one shared `get_byte_arg` leaf. Total NEW code ≈ **40–70 B**
(leaf + per-site glue) — a real page-1 cost against **0 B free** (§5).

---

## 4. Staging (each stage independently gated + lead-verified)

1. **A1 — `OUT`** ✅ **LANDED 2026-07-19.** Mirrored the POKE `eval_addr` template + one
   `check_fperr_only` (both port/value are the address domain; FPERR sticky across the two
   `eval_addr`s → one end-check catches either). **Self-funded** by tightening the sibling
   `do_vpoke`: it used a 10 B inline FPERR check + a stack-balancing `pop bc` because its
   address was still on the stack; popping the address *before* the check (as `do_out` now
   does) makes the site SP-clean so it reuses the shared `check_fperr_only` (−7 B; +1 B for
   OUT → page-1 0→6 B). Lean byte-identical. Gate: `make intarg-acceptance`.
2. **A2 — `PEEK`/`INP`** (functions, ADDRESS domain). Q1 RESOLVED (§3.1): swap the coercion to
   `fac_to_int_addr` + an **inline** FPERR check at `ev_ff_arg`. This also builds the shared
   inline-abort choke point that VPEEK reuses in B. Needs a small funder (not byte-neutral).
3. **B — `get_byte_arg`-style range-check + STRING$/SPACE$/ON/WIDTH (0..255) + VPOKE
   (0..16383) + VPEEK (0..16383)** (the int16-overflow + per-site range-check leaf; Q2
   page-visibility). VPOKE (statement) and **VPEEK (function)** both join here (§1.1
   corrections) on a shared VRAM leaf — same shape, a 16383 bound instead of 255. VPEEK routes
   its VRAM check through the `ev_ff_arg` inline-abort point A2 introduces.

Order rationale: A1 validates the address-domain move end-to-end at a statement site (no
propagation question); A2 resolves the function-propagation question on a small surface; B
is the largest and gated on the shared leaf. Land + gate + adversarial-pin each stage.

---

## 5. Space budget & funder (the blocker)

**A2+VPEEK MEASURED 2026-07-19 (implemented on `ev_ff_arg`, then reverted pending a funder):
the checked-coercion block is 39 B; page-1 had 6 B free → `__MEAS_PAGE1_END` $7FFA→$8021, a
33 B overrun past the $8000 ceiling.** The block is already golfed hard: shared `push bc`
selector guard, both overflow gates reuse the existing `check_fperr_only` helper (3 B/site,
the OUT/eval_chan pattern), VPEEK's VRAM range = `ld a,d / and $C0` (top-two-bits). The ~33 B
is irreducible new function (checked coercion for 3 functions across 2 domains). **Funder
NEEDED — this stage nets +33 B, unlike A1 (self-funded +1).** Note: both paved evictions
(PRINT USING 2026-07-18 +217 B; CALL FORMAT for S2b) are already SPENT — the S2a/S2b/ERROR-n
landings consumed page-1 back to 6 B. The only recorded reserve left is `format.asm`'s
value-render/deref paths (`pu_do_number`/`pu_do_string`/`pu_fmt_int`/`INT2DEC`) deliberately
left resident by the printusing as-built (§0 of [docs/spec-evict-printusing.md]) — the code
that has "bitten us ~12×", so a HIGH-regression-risk eviction.

**Page-1 = 6 B free** (post the 2026-07-19 ERROR-n landing; `tools/check_reloc.py`). The
arc needs a funder before any stage that nets positive:

* **Lever 1 — golf** (proven this session): the ERROR-n slice self-funded via a raise_error
  guard golf + FPERR-special-case factoring. Re-measure remaining error-path dups/folds;
  likely thin now.
* **Lever 2 — `format.asm` render-engine eviction to a sub-ROM tenant** — the flagged
  reserve (S2 packet §8 lever 2; the CALL FORMAT eviction that funded S2b is the paved
  pattern, [docs/spec-evict-call-format.md]). Highest-yield, proven.
* Group A alone may fit in golf (mostly byte-neutral swaps); Group B almost certainly needs
  Lever 2. **Decide the funder per stage after measuring the stage's real delta.**

Lean 16 KB stays byte-identical throughout (every byte repack-gated, like all Phase-3 work).

---

## 6. Faithfulness / open decisions (sign-off)

1. **Q1 — PEEK/INP FPERR propagation** (§3.1). ✅ **RESOLVED 2026-07-19 → inline check at
   `ev_ff_arg`.** The ref aborts at the function in every context incl. FOR bounds (which run
   no `check_expr_errors`), so the cheap boundary path is rejected; a single inline check at
   the shared PEEK/VPEEK/INP parse point reproduces it and also serves VPEEK (stage B). The
   empirical pass ALSO surfaced VPEEK as a missing Group-B VRAM site (§1.1). Sign-off needed:
   inline path confirmed, and whether VPEEK folds into A2 or stays in stage B with VPOKE.
2. **Q2 — Group-B leaf siting** (§3.2) vs the sub-ROM string tenants' page.
3. **Scope confirm:** all 8 arg-sites (this doc), or a subset (e.g. Group A only) first.
4. **Funder:** golf-first per stage, `format.asm` eviction held as the reserve — confirm.
5. **`ON n` upper bound:** pinned 0..255 (0 = no-branch). Confirm no higher valid selector
   (real MSX `ON` indexes a line list; >list-length just falls through — verify vs the
   0..255 illegal-fn wall we pinned, which may be `ON`'s own separate rule).

---

## 7. Acceptance & gates

* Promote `scratchpad/char_intarg.py` → `probes/basic/basic_probe_intarg.py`, a VG-8020
  differential over all sites × {in-domain, boundary, over-int16, negative}, gated
  `make intarg-acceptance`. Include the §1.2 already-faithful sites as regression guards.
* Standing gates that MUST stay green (this touches eval consumers + the shared error
  funnel + string/screen/vdp verbs): `unit-test`, `array-acceptance` (150), `string`/
  `input`/`float`/`math`/`error`/`error-trap`-acceptance, `diskbasic` (34 lean + 34
  repack), lean `basic.rom` byte-identity.
* **Adversarial + empirical pass mandatory per stage** ([[error-handling-arc]] recurring
  lesson): a green build hid catastrophic register/order bugs every prior slice; Q1 is
  exactly that class.

---

## 8. Clean-room

Original code; the int-argument error semantics (Overflow vs Illegal function call, and
each site's valid domain) are **black-box behaviour** pinned on the VG-8020, cross-checked
against the published MSX-BASIC language-reference error numbering (allowed-source L110).
No reference-ROM disassembly. To record in `basic/PROVENANCE.md` per stage on landing.
