# D-PLAYCORNER — a wrapped MML number aliases into range, and `M`'s domain had two unmeasured edges

*2026-08-31. `sub/playparse.asm` (`pt_number`, `pt_cmd_env_per`),
`basic/sysvars.inc` (`PLY_NUMOVF`). Probe `scratchpad/playcorner_probe.py`,
10 rows × 3 machines: **5 DIFF → 0**. Follows [spec-basic-musicf.md](spec-basic-musicf.md) —
these are the three corners that review filed as unmeasured.*

## 1. Measured first

Accept vs reject, read through `PLAY(1)` after an `L1` (~7.5 s) note — long
enough that "accepted" is a stable `-1` against the harness pacing:

| row | | VG-8020 | CF-3300 | zerobas |
|---|---|---|---|---|
| `w.ok` | `T32L1C` | −1 | −1 | −1 ✅ |
| `w.twrap` | `T65568…` | ERR 5 | ERR 5 | **−1** 🔴 |
| `w.owrap` | `O65537…` | ERR 5 | ERR 5 | **−1** 🔴 |
| `w.vwrap` | `V65551…` | ERR 5 | ERR 5 | **−1** 🔴 |
| `c.cflat` | `O1L1C-` | −1 | −1 | −1 ✅ |
| `c.bsharp` | `O8L1B#` | −1 | −1 | −1 ✅ |
| `m.zero` | `M0…` | ERR 5 | ERR 5 | **−1** 🔴 |
| `m.max` | `M65535…` | −1 | −1 | −1 ✅ |
| `m.wrap` | `M65600…` | ERR 5 | ERR 5 | **−1** 🔴 |
| `ctl.bad` | `T31L1C` | ERR 5 | ERR 5 | ERR 5 ✅ |

Four real divergences, one mechanism: `pt_number` accumulated in 16 bits and a
wrapped literal **aliased into range** — `T65568` became `T32` and *passed* the
range check. Plus `M0`, accepted here, ERR 5 on both references.

The clamp rows (`c.*`) **agree** at the accept/reject level, so the edge
accidental clamp survives as-is. Whether the reference plays the *same pitch*
as the clamp is still open — that needs a PSG-trace row, not a screen read —
and stays filed.

## 2. `m.max` / `m.wrap` decided the fix's shape before it was written

Two candidate fixes for the wrap: **saturate** to `$FFFF`, or **reject**. For
the 8-bit commands they are indistinguishable (every range check rejects
`$FFFF`); for `M` — a 16-bit domain — they differ, and the rows decided it:
`M65535` is *legal* on both references while `M65600` is *rejected*, so a
saturated `$FFFF` must not be accepted as 65535. Reject-on-wrap it is.

## 3. The fix

- `pt_number` clears **`PLY_NUMOVF`** per literal, tests overflow *before* each
  multiply step (`10v+d > 65535` iff `v > 6553`, or `v = 6553` and `d ≥ 6` —
  65530+5 is still exact), latches on trigger, and **saturates the result to
  `$FFFF` at exit**. Every 8-bit caller (`T/O/V/L/N/S`, `pt_length`) rejects
  that through its *existing* `ld a,h / or a` check — zero call-site changes.
- `pt_cmd_env_per` reads the latch itself (a saturated `$FFFF` is
  indistinguishable from legitimate `M65535`) and additionally rejects 0.
- `PLY_NUMOVF` is the byte formerly declared as `PLY_NUM` — a "decimal
  number-literal accumulator" that **nothing referenced** (the accumulator
  rides HL). No new RAM.

## 4. After

10/10 SAME · `scratchpad/musicf_probe.py` still 5/5 · `make play-acceptance`
and `make play-trace-acceptance` re-run green · full battery.
