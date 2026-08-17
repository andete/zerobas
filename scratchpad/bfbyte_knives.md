# D-BFBYTE knife predictions — WRITTEN BEFORE ANY KNIFE RAN

🔴 **Lesson carried from K-DC3, one commit ago:** deleting a call or short-
circuiting a branch leaves the routine behind it unreachable, and
`check_dead_code.py` then fails `make basic-reloc` — the knifed tree builds no
ROM and scores nothing. Every knife below therefore **corrupts a value in
place**, one instruction of the same length, leaving every span reachable.

Each cut is aimed at ONE half of the change, so the halves are shown to be
independently sited rather than assumed to be.

## K-BB1 — `ld c,0` → `ld c,$FF` in `gbf_row`'s fast loop

Writes the *pattern* byte as `$FF` instead of `$00`. The colour write is
untouched.

* RED (pattern plane): `bfbyte_cell`, `bfbyte_span`, `bfbyte_teeth` —
  `bfbyte_teeth` goes red because the `PSET` then lands on a set bit instead of
  a clear one, leaving `$ff` where the reference has `$80`.
* GREEN, and this is the point: **every colour twin.** `bfbyte_cell_c`,
  `bfbyte_span_c`, `bfbyte_rev`, `bfbyte_tall`, `bfbyte_c0` — and
  `bfbyte_teeth_c` too, because with the bit already set the `PSET` restamps
  the foreground to 6 and still produces `$6f`.
* GREEN: `bfbyte_unalign`, `bfbyte_x255` (no whole byte to corrupt).

## K-BB2 — `ld a,(GFX_C)` → `ld a,(GFX_TX1)` in the fast loop

Writes the *colour* byte from the left edge instead of the colour. Same length,
same reachability. The pattern write is untouched.

* RED (colour plane): `bfbyte_cell_c` (`$00` for `$0f`), `bfbyte_span_c`
  (`$03`), `bfbyte_rev` (`$03` after the sort), `bfbyte_tall` (`$00`),
  `bfbyte_teeth_c` (`$60` for `$6f` — the cell is all background, so the `PSET`
  claims a foreground nibble over the wrong background).
* GREEN: `bfbyte_cell`, `bfbyte_span`, `bfbyte_teeth` (pattern rows).
* GREEN **by coincidence, and predicted as such**: `bfbyte_c0`. Its colour is 0
  and its `xl` is 0, so the knife writes the value it was going to write
  anyway. A row can be green because the cut is invisible to it, not because
  the cut is harmless — stating which is which in advance is the whole
  discipline.

## K-BB3 — `jr c,gbf_xsorted` → `jr nc,gbf_xsorted`

Inverts the corner sort, so forward boxes get swapped and reversed ones do not.
Either way `xl > xr` reaches `gbf_split`, which then finds no whole byte and
sends the whole run down the per-pixel path.

* RED, all nine discriminating rows: `bfbyte_cell`, `bfbyte_cell_c`,
  `bfbyte_span`, `bfbyte_span_c`, `bfbyte_rev`, `bfbyte_tall`, `bfbyte_c0`,
  `bfbyte_teeth`, `bfbyte_teeth_c` — every one reverting to the pre-fix
  `$ff`/`$f4` storage.
* GREEN: `bfbyte_unalign` (swapped or not, it has no whole byte, and
  `gfx_draw_seg` sorts internally) and `bfbyte_x255` (`xl == xr`, caught by the
  separate `jr z` which this cut does not touch).

## Not knifed here, and why

The **16-bit-ness of the split** — the `xl+7 = 262` overflow and the `fr = -1`
underflow — is falsified by `tests/test_graphics.py` instead, which drives
`gbf_split` and `gbf_shr3` directly over exactly those values (`(255,255)`,
`(249,255)`, `(0,6)`, and `gbf_shr3 262 -> 32`). That is a stronger
falsification than a knife: it is exhaustive over the boundary rather than
one sampled program, and it runs with no emulator.
