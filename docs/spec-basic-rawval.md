# D-RAWVAL — POKE, VPOKE and OUT gave their second argument the ADDRESS domain, so it wrapped

*2026-09-08. `basic/poke.asm` (`do_poke`), `basic/vdpio.asm` (`do_vpoke`,
`do_out`). Probe `scratchpad/rawval_probe.py`, 13 rows × 3 machines:
**6 DIFF → 0**. **Byte-neutral** (page 1 2 B and low 1 B, before and after).
The raw-I/O trio off [review-tier-worklist.md](review-tier-worklist.md), which
named it first and said why: "the coercion SURFACE is gated, the port/address
MECHANISM never reviewed".*

## 1. The surface was gated on the wrong argument

`intarg-acceptance` had eleven rows for these three verbs and **every one was
about the first argument** — `poke_addr_ovf`, `poke_neg`, `vpoke_vram`,
`vpoke_ill`, `vpoke_neg`, `wait_port_ovf` … The second argument had no row
anywhere, and all three handlers treated it identically:

```
                call    eval_addr           ; the ADDRESS domain: 0..65535, wraps
                ...
                call    check_fperr_only    ; ERR 6 only beyond ±32767
                ld      a,e                 ; <- the LOW BYTE, silently
```

`eval_addr` is the right domain for an *address*, where wrapping is the
reference's own rule (`POKE -1,0` is a gated `cont`). It is the wrong domain for
a *byte*. So the value wrapped instead of raising.

## 2. The rows

Each row primes the target with 65 first, so a raise leaves 65 and only a write
changes it — the witness separates "refused" from "wrote something", which an
`ERR` column alone cannot.

| row | | VG-8020 | CF-3300 | zerobas before |
|---|---|---|---|---|
| `p.256` | `POKE x,256` | ERR 5, 65 | ERR 5, 65 | **ERR 0, wrote 0** 🔴 |
| `p.neg` | `POKE x,-1` | ERR 5, 65 | ERR 5, 65 | **ERR 0, wrote 255** 🔴 |
| `v.256` | `VPOKE x,256` | ERR 5, 65 | ERR 5, 65 | **ERR 0, wrote 0** 🔴 |
| `v.neg` | `VPOKE x,-1` | ERR 5, 65 | ERR 5, 65 | **ERR 0, wrote 255** 🔴 |
| `o.256` | `OUT 0,256` | ERR 5 | ERR 5 | **ERR 0** 🔴 |
| `o.neg` | `OUT 0,-1` | ERR 5 | ERR 5 | **ERR 0** 🔴 |
| `p.255` | `POKE x,255` | ERR 0, 255 | ERR 0, 255 | ERR 0, 255 ✅ |
| `p.ctl` / `v.ctl` | `POKE x,42` / `VPOKE x,42` | 42 | 42 | 42 ✅ |

The predicted wrap values — **0** for 256 and **255** for −1 — came out exactly,
which is what makes `ld a,e` the confirmed mechanism rather than a plausible one.

## 3. Two rows that exist to stop the tidy version of this fix

**The PORT is not a byte.** It would read as an oversight that `OUT`'s port is
still `eval_addr` after its value moved. Measured:

| row | | VG-8020 | CF-3300 |
|---|---|---|---|
| `x.port` | `OUT 256,0` | **ERR 0** | **ERR 0** |
| `x.pneg` | `OUT -1,0` | **ERR 0** | **ERR 0** |

The port wraps where the value raises. Applying one domain to both arguments
would be tidier and would be a regression.

**Overflow beats domain.** The fix moves the value onto `eval_byte_checked`,
which raises at the point of evaluation, where the old code surfaced the
*address*'s overflow afterwards. No existing row could see a change here,
because every one of them pairs a bad address with a **legal** value:

| row | | VG-8020 | CF-3300 | zerobas |
|---|---|---|---|---|
| `x.both` | `POKE 99999,256` | ERR 6 | ERR 6 | ERR 6 ✅ |

`eval_byte_checked`'s int16 stage runs `check_fperr_only` on the sticky `FPERR`
before the byte stage, so ERR 6 still wins. Measured before the fix and after.

## 4. The fix

One symbol at three sites: the **value** argument calls `eval_byte_checked`
instead of `eval_addr`. Both are three bytes, so the change is byte-neutral —
which mattered, because main page 1 had 2 B free and the low region 1 B, and all
three mechanical carve routes were measured shut the same evening (D-CARVEOUT).

`eval_byte_checked` already existed and is what `STRING$`'s char code uses —
`STRING$(5,256)` was a gated ERR 5 row throughout. **So `STRING$`'s byte was
checked and `POKE`'s was not, in one tree.** That asymmetry, visible in the
source alone, is what the review found; the rows only confirmed it.

Ten rows added to `probes/basic/basic_probe_intarg.py`, six of which were RED
before the fix and four of which are the regression guards of §3.
