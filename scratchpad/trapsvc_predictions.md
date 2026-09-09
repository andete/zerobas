# D-TRAPSVC — predictions, written BEFORE the matrix ran

Baseline `b8a8137`, clean build, `7942cc20` / `34bb8554` / `031184d9`.
Reading is `[B C]`: B = the trap fired at all, C = it fired in window TWO.

| row | vg8020 | cf3300 | zb | why |
|---|---|---|---|---|
| `int.ctl`     | `1 1` | `1 1` | `1 1` | handler RETURNs, nothing abandoned (MEASURED already on zb) |
| `int.one`     | `1 1` | `1 1` | `1 1` | one fire, normal RETURN, re-enabled |
| `int.resume`  | `1 0` | `1 0` | `1 0` | RESUME <line> skips the RETURN -> trap permanently dead, on ALL THREE |
| `int.resnext` | `1 1` | `1 1` | `1 1` | RESUME NEXT lands ON the RETURN -> re-enabled |
| `int.goto`    | `1 0` | `1 0` | `1 0` | plain GOTO out of the handler, same abandonment, no error involved |
| `int.six`     | `9 18` | `9 18` | `6 7` | 🔴 DIFF predicted: zerobas caps at TRAPSTK_MAX=6 -> ERR 7 |
| `gos.leak`    | `12 0` | `12 0` | `8 7` | 🔴 DIFF predicted: GOSUB_DEPTH=8 is own-design, already filed |

## Knife predictions

K-TR1 `or ZTS_ON` -> `or ZTS_SERVICING` in `trap_return_check` (the auto-resume
value): moves **{int.ctl, int.one, int.resnext}**, leaves int.resume / int.goto /
int.six / gos.leak.

K-TR2 `dec (hl)` -> `nop` (the TRAPSVC decrement): moves **{int.ctl, int.resnext}**
— the trap survives up to 6 un-decremented fires, so `int.one` (exactly ONE
fire) STAYS GREEN. That is what separates the two knives, and why `int.one`
exists.

## 2026-09-09 — re-prediction after D-CTLPOOL, written BEFORE the run

🔴 **K-TR2's ANCHOR IS GONE.** The 2026-08-23 run knifed
`                dec     (hl)                ; pop the service record` and the
2026-09-09 re-run aborted with `anchor matched 0x`: D-CTLPOOL rewrote
`trap_return_check`, the comment moved to the `ld (TSP),de` line above, and the
knife has been INERT-BY-ANCHOR ever since — it would have said so loudly, which
is the only reason this is a finding and not a silent hole
[[a-knife-can-be-inert-because-the-build-did-not-happen]].

**K-TR1 re-ran EXACT on the post-pool build**: `{int.ctl, int.one, int.resnext}`
moved, the other four held, ROM hashes moved on `basic-reloc.rom` +
`zerobas-main-eu.rom` only, and the source restored byte-identical. So the row
set still has teeth; it is the SECOND knife that needs rebuilding.

**PREDICTION for the re-anchored K-TR2** (`ld hl,TRAPSVC` / `dec (hl)` -> `nop`,
still 1 byte for 1 byte): **it moves NOTHING — the empty set.**

*Why.* Pre-pool, K-TR2 bit because an un-decremented count reached
`TRAPSTK_MAX = 6` and `ct_svc_full` raised ERR 7. `basic/traps.asm` now says in
as many words that *"ct_svc_full is retired with TRAPSTK_MAX — one arm, not
two"*. What is left of `TRAPSVC` is a single gate in `ex_return`: call
`trap_return_check` only when the count is non-zero. A count stuck non-zero
makes that call happen MORE often, never less, and the routine's first act is
the D-CTLPOOL pointer identity `TSP + TRAP_FRAME == GSP`, which declines every
call that is not the trap frame's own. So the COUNT is no longer load-bearing
for any of these seven rows; the POINTER is.

⚠️ **THE MISS I WOULD BELIEVE.** A stale `TSP` could satisfy that identity by
accident at some ordinary `RETURN`, and the routine would then pop garbage and
re-enable a trap by an index read out of it. `int.six` and `gos.leak` execute
the most ordinary RETURNs, so if anything moves I expect it to be one of those
two — not `int.ctl`/`int.resnext`, which is what the OLD prediction named.

🎯 **AND IF THE PREDICTION HOLDS, THAT IS ITSELF THE FINDING**: the calibration's
claim that *"the two knives are separated by `int.one`"* — one testing the
re-enable, the other the count — no longer describes this machine. Post-pool
there is one mechanism under these rows, not two, and a suite that still claimed
two would be one knife wearing two names.
