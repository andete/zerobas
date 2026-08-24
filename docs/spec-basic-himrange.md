<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-HIMRANGE — CLEAR's memory-ceiling RANGE check, and two of D-HIMDOM's guesses refuted

Status: **✅ SHIPPED. +52 B of main page 1** (free **120 → 68 B**, funded by
D-JRSLICE/2's `jp`→`jr` seam). Closes the last open divergence of the
D-CLRFIX → D-HIMDOM CLEAR arc: the three-band range check
[D-HIMDOM](spec-basic-himdom.md) §5 filed but left for funding.

Measured on the VG-8020 AND the CF-3300 (`scratchpad/himdom_probe.py`, extended;
both references agree on every scored row). **zerobas: 15 DIFF → 0.**

---

## 1. The rule, as measured

`CLEAR [<string-space>][,<memory-top>]`. The `<memory-top>` argument, after the
address-domain coercion D-HIMDOM already shipped (`eval_addr`, −32768..65535):

| band | arguments (measured) | answer |
|---|---|---|
| ≥ 65536 | `65536`, `70000` | **ERR 6** (eval_addr / check_expr_errors) |
| > `$F380` (62336) | `62337`, `63000`, `65535`, `&HFFFF`, `-1` | **ERR 5** Illegal function call |
| accepted | `34000`…`62336`, `&HD000`, `&HABCD` | **ERR 0**, HIMEM moves |
| `$8000` ≤ v < floor | `32768`, `&H8050`, `33000`, `33700` | **ERR 7** Out of memory |
| < `$8000` | `0`, `1`, `&H4000`, `32767` | **ERR 5** Illegal function call |

**floor = PRGEND + POOLSIZE + 680.** It tracks the program TEXT and the requested
string space, and NOT the variables (CLEAR wipes them). See §3.

## 2. 🔴 Two of D-HIMDOM's characterization guesses were REFUTED by finer measurement

D-HIMDOM §5 filed two claims it could not test with its 15-row set. Both are
wrong, and both are the *same* trap D-CLRFIX shipped a regression into
([[two-rules-that-coincide-on-every-row-you-have]]): a claim asserted on a row
set that cannot separate the candidate rules.

### 2a. The upper edge is a CONSTANT, not machine-specific

D-HIMDOM: *"This edge is machine-specific: HIMEM boots at 62336 on the VG-8020
and 56951 on the CF-3300, so a value between them should be accepted on one
machine and refused on the other."*

**Measured (rows `u.57000`…`u.62336`): both machines ACCEPT every value up to
`$F380` = 62336 and both refuse `62337`.** The CF-3300 accepts `60000` and moves
HIMEM there, despite booting HIMEM to 56951. So the boot HIMEM is *not* the
ceiling; the ceiling is a fixed **`$F380`** (the top of BASIC-usable RAM, below
the BIOS work area) on both machines.

And `t.4to6` (`CLEAR 200,40000 : CLEAR 200,60000`) **accepts the raise on both
references** — you may raise the ceiling back up after lowering it, so the check
reads a *fixed top*, not the live HIMEM. **This is why zerobas needs no
boot-time HIMEM init** (it boots HIMEM=0 and the range check is independent of
it). The two apparent "REFERENCES DISAGREE" rows (`u.56951`, `u.62336`) are the
SAME-vs-`->value` face artifact — the value already equals that machine's boot
HIMEM, so its ceiling did not *move* — not a behavioural disagreement.

### 2b. The floor is program-text + string-space dependent, NOT variable-dependent

D-HIMDOM: *"the edge lies between 32848 and 40000 and is a property of the
current program and variables."*

Two corrections from finer rows:

* **Variables do NOT count** (rows `p.dim*`): `DIM A#(1000)` before
  `CLEAR 200,38000` leaves the answer unchanged (accepted), because CLEAR wipes
  the array before the ceiling takes effect — the check is against the
  *post-wipe* layout.
* **String space DOES count** (rows `s.big*`): `CLEAR 10000,42000` is **ERR 7**
  where `CLEAR 200,42000` is accepted. The floor rises with the requested string
  space, slope ≈ 1.
* **The bare-program floor is much tighter than filed** (rows `f.*`): between
  **33700 (ERR 7) and 33750 (accept)** for the 5-line n=200 probe program, not
  the filed (32848, 40000).

So floor = end-of-program + string-space + a fixed stack/overhead reserve — the
standard MS-BASIC `CLEAR` check, taken on the layout that survives the wipe.

## 3. As built — +52 B (basic/clear.asm `clr_himem`)

    call eval_addr              ; DE = value, FPERR=1 if >=65536
    ld   a,(FPERR) / or a / jr nz,clr_h_store   ; overflow pending -> ERR 6
    push hl                     ; guard the statement cursor
    ld   hl,CLR_HIMEM_TOP ($F380) / sbc hl,de / jr c,clr_h_ill   ; > top -> ERR 5
    ld   hl,$7FFF / sbc hl,de / jr nc,clr_h_ill                  ; < $8000 -> ERR 5
    ld   hl,(PRGEND) / add POOLSIZE / add CLR_HIMEM_MARGIN(680)  ; floor
    sbc  hl,de / jr c,clr_h_ok / jr z,clr_h_ok                   ; >= floor -> ok
    ld   a,6 (ERR 7) ...  clr_h_ill: ld a,3 (ERR 5) ...  penderr_set
    clr_h_ok: pop hl
    clr_h_store: call check_expr_errors / ld (HIMEM),de

The two error codes are the existing deferred-FPERR channel: FPERR=3 →
`fperr_to_err`[3] = ERR 5, FPERR=6 → ERR 7 (both unconditional table entries).
`penderr_set` is first-error-wins (so a pending overflow ≥65536 keeps ERR 6) and
preserves DE and the flags. The raise is deferred to `check_expr_errors` — the
same "raise BEFORE the store and the wipe" structure D-HIMDOM established, so the
26 D-CLRFIX rows and the D-HIMDOM coercion rows are all unchanged.

Constants: `CLR_HIMEM_TOP equ $F380`, `CLR_HIMEM_MARGIN equ 680` (sysvars.inc).
The margin is DERIVED, not guessed: measured floor (33700,33750], the 5-line
program's zerobas PRGEND = 32843, POOLSIZE = 200 ⇒ MARGIN ∈ (657, 707]; 680 is
the centre. It applies to any program via that program's own PRGEND.

🔴 **NOT the pool argument's `bit 7,d` sign test.** `&H9000` has bit 15 set
exactly as `-1` does yet is ACCEPTED on all three machines (it is 36864, in the
window). The domain is a RANGE, not a sign — the D-CLRFIX §5 STILL-OPEN warning.

## 4. Knives — `scratchpad/himrange_knives.py`

Four size-neutral value cuts, one per sub-rule, each moving a disjoint row set:

* **K-HR1** bypasses the whole check (`jr nz`→`jr`), re-creating the PRE-FIX
  build; its faces are **read off `scratchpad/himrange_probe.out`** (the real
  pre-fix run), so it is a standing regression detector for the slice.
* **K-HR2** removes the upper edge (`$F380`→`$FFFF`): only the > `$F380` rows move.
* **K-HR3** drops the floor (`PRGEND`→`0`): only the ERR-7 rows move.
* **K-HR4** collapses the low edge (`$7FFF`→`0`): `(0,$8000)` becomes ERR 7,
  and `d.zero` (==0) stays ERR 5 — the control that proves the cut landed.

## 5. Fixture fallout — the ERR-7 band retires two tight-ceiling squeezes

The floor GUARANTEES ≥ 678 B of headroom by design (matching the references,
which reject a ceiling that low), so **no legal ceiling can squeeze the string
chain to the ~77 B the old fixtures relied on.** `probes/basic/basic_probe_arrays.py`:

* `scalar.str.chain.oom` / `scalar.input.chain.oom` used `CLEAR 200,&H8050`
  (32848, now ERR 7). Replaced with `CLEAR 200,50000 : DIM Z(1840)` — a legal
  ceiling plus an array that consumes the room the tight ceiling used to deny.
  Same `str_set_key` scalar-chain-OOM path. (Measured: room ≈ 14899 B, DIM fit
  boundary N ≈ 1853; N=1840 fits with ~104 B margin, OOMs the last 8 of A$..Z$.)
* `gc.bugB.phantom` used `CLEAR 400,&H82C0` (33472, now ERR 7). Replaced with
  `CLEAR 400,50000`: any ceiling ≥ TXTMAX pins `C = min(HIMEM,TXTMAX) = TXTMAX =
  $BB00`, so the pool sits at [$B970,$BB00) deterministically — the phantom-root
  seed moves from `$82A0` to `$BAE0`, inside the new [FRETOP,C) window.

## 6. Gates

`scratchpad/himrange_gates.sh` (38 gates from clean), incl. `unit-test`,
`array-acceptance`, `clearpool-acceptance`, `switch-build-check`, `deadcode`,
`wall-assertion-check`, `subrom-abi-check`.
