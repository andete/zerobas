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
