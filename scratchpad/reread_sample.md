<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-REREAD — the reread sample (2026-10-30)

Joost, porting zerobas fixes into C-BIOS, found that nearly every fix came out a
few bytes smaller on a second look. The question: does the same hold for zerobas
itself? Every carve route measured so far is mechanical (`jp`→`jr`, dup spans,
promotion, instruction pairs: TODO.md's carve inventory) and sees text, not
meaning. This one reads a whole routine against its contract.

## Method

- Ten routines, picked by size from label-to-label spans in
  `build/basic-reloc.sym` (`reread_spans.out`), code only (no tables): three in
  the low region, seven in main page 1.
- Five read-only reviewers, two routines each. Each wrote the routine's contract
  (inputs, outputs and flags at every exit, callers, fall-through in and out,
  internal labels reached from elsewhere) and proposed rewrites with byte and
  T-state counts.
- Every premise a proposal leaned on was checked in the source before it was
  applied: the carry `var_str_type` returns, `ctl_alloc`'s HL, `sh_go`'s block
  layout (op 0 writes only the HL slot and ERR), the VCB layout, `fpd_pack`
  never writing D. A layout fact the code now depends on is pinned by an
  assembly-time guard (`db` of an undefined name, the house idiom).

## Result

`make basic-reloc`, before → after: low region free 1 → 13 B and its pin pad
16 → 27 B (**+23 B**); main page-1 pin pads 2028 → 2087 B (**+59 B**). **82 B
from ten routines.**

| routine | region | B | the reread |
|---|---|---|---|
| `ev_f` | page 1 | 23 | three arms reloaded A = `(ix+0)`, which `ev_sp` and the `cp` chain already leave; float size `(tok-$1B)*2`; word literal by `(ix+1)/(ix+2)` |
| `pl_voice` | page 1 | 18 | a VCB's VCXLEN/VCXPTR is a descriptor's `[len][ptr]`: one 3-byte `ldir`; the mask is 1/3/7 by `scf / rl (hl)`; E steps the slot (page $FB) and is the 3-voice cap; IY, B and C freed |
| `mid_own` | low | 11 | `sh_go` op 0 hands DE (the text body) and C (La) back unchanged: no re-read of the descriptor; `scf / sbc` folds `ret c` + `ret z` |
| `fpd_go` | low | 9 | `byte - 6*hi` = `10*hi + lo`; LA on the stack, not in a cell; FPD_SH and FPD_SLOT in one 16-bit store; `ld e,c` keeps `fpd_pack`'s untouched D |
| `check_traps` | page 1 | 7 | the record written through `ctl_alloc`'s HL (= CSP); the handler link via HL; `ct_gsfull`'s `pop de` was dead before `raise_error` re-bases SP |
| `lst_lp` | page 1 | 7 | range tests as `sbc hl,bc` (`scf` for the lower bound); `ln_div_entry` directly |
| `str_eval_one`, `exp_loop` | page 1 | 4 | `var_str_type`'s CF instead of `or a`; `str_eval_ok` moved to where the variable arm falls into it |
| `ex_let_arr_str` | low | 3 | `jr` to `ex_let_arr`'s identical exits (`ela_rterr`, `ela_done`) |
| `ex_for` | page 1 | 2 | `ld hl,(nn)`/`ld (nn),hl` where DE and HL are both dead |

No common path got slower: variables and digit constants in `ev_f` are 19 T
faster each, `lst_lp` and `pl_voice` faster per line and per voice; the
`ex_let_arr_str` exits pay 12 T each (TIER 5 is paused).

## Held back

- **The PRINT dispatch's own string classification (~53 B).** `exp_loop`
  repeats `str_eval_one`'s classification; letting `str_eval_one` decline
  instead would drop it, but it CHANGES behaviour: an operator after
  `CHR$(65)` would get the Type mismatch check, and `INPUT$` / `DSKI$` /
  `SPRITE$` items would start printing as strings. The reviewer read that today
  `PRINT INPUT$(1)` may defer a Type mismatch -- a possible live divergence,
  filed as D-PRSTRFN to measure first.
- **`ary_apply_offset_hl_sub`** (vars.asm, single caller): 2-3 B, a cross-file
  fold; left for the route proper.

## What it says

About 9% of the code read came out, and every reviewer found something. The
sample is biased upward (the largest routines carry the most history), so a
whole-ROM pass would find less per byte, but it is a different and open route
where the mechanical ones are measured shut.
