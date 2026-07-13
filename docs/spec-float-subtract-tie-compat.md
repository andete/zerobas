<!-- Provenance: black-box VG-8020 characterization (own probes, this session) + our own source. No ROM disassembly ([[no-reference-rom-disasm]]). Part of the bug-for-bug arithmetic-compat track ([[bug-for-bug-compat-over-accuracy]]). -->
# Mini-spec — subtraction guard-tie rounding, bug-for-bug reference-compat (DRAFT)

**Status: ✅ APPROVED (user 2026-07-13) + IMPLEMENTED (commit `fe0d99c`).** All gates
green. Sibling of the division bug-compat track (docs/spec-basic-math-pack.md §10.3);
this one is **cleanly characterized and small**, division is not — independent changes.

> **Correction (post-implementation):** the whole float engine (`float.asm`,
> `float-arith.asm`, `str-engine.asm`, …) is wrapped `IF ROM_BASE < $4000` in
> [basic/main.asm:54](../basic/main.asm:54) — it is **repack-only**; the lean 16 KB cart
> has no float arithmetic at all. So this fix ships in the **repack build only**, the lean
> `basic.rom` is **provably unaffected**, and `LEAN_SHA256` did **not** change (§3 below
> is corrected accordingly — the earlier "ships in lean / re-baseline lean SHA" wording
> was wrong).

## 1. The divergence (characterized black-box, VG-8020 vs zerobas repack)

At the **exact guard-digit tie** (15th significant digit exactly 5, nothing below),
addition and subtraction round **differently on the reference**, and the rule keys on
the **effective operation** (operand-sign relationship after fp_sub's sign flip), not
the surface `+`/`-` token:

| Expr | Operands | Effective op | Reference | zerobas (now) |
|---|---|---|---|---|
| `1+5E-14` | like signs | **add** | `1.0000000000001` (away from 0) | `1.0000000000001` ✅ |
| `-1-5E-14` | like signs | **add** | `-1.0000000000001` (away from 0) | `-1.0000000000001` ✅ |
| `2-5E-14` | opposite signs | **subtract** | `1.9999999999999` (toward 0) | `2` ❌ |
| `5E-14-2` | opposite signs | **subtract** | `-1.9999999999999` (toward 0) | `-2` ❌ |
| `8.5-5E-14` | opposite | subtract | `8.4999999999999` | `8.5` ❌ |

Confirmed it is **tie-only** (both machines already agree away from the tie):
`2-4E-14` (guard 6) → `2` on **both** (ties-up region); `2-6E-14` (guard 4) →
`1.9999999999999` on **both** (below-tie). So the *only* difference is the tie
direction for effective subtraction.

**Locked rule.** Effective **addition** (like-sign combine): guard-tie rounds
**away from zero** (half-up) — matches today. Effective **subtraction** (opposite-sign
combine, incl. every `fp_sub`): guard-tie rounds **toward zero** (truncate the tie);
guard 6–9 still round up, guard 0–4 still down. Multiply is half-up on both machines
(agent-confirmed) → unchanged. Division is handled on its own track.

## 2. Why our build diverges

`fp_sub` = flip ARGB sign then `jp fp_add` ([float-arith.asm:616](../basic/float-arith.asm:616)),
so effective subtraction is the **opposite-sign** branch `fpa_diffsign`
([float-arith.asm:561](../basic/float-arith.asm:561)). All its exits merge into
`fpa_done` → `round_and_finalize`, whose guard round is a blanket half-up
(`ld a,(ARGA_DIG+14); cp 5; jr c,noround; …inc` — [float-arith.asm:362](../basic/float-arith.asm:362)).
So effective-subtract ties wrongly round away from zero, identical to add.

## 3. Proposed change (minimal; shared tail stays byte-identical)

Do **not** touch `round_and_finalize` (shared by add/sub/mul/div/single-coerce — a
change there has blast radius and would perturb mul/div). Instead give the
**diffsign path its own finalize** that pre-nudges the exact tie toward zero, then
falls into the unchanged shared tail:

```
; effective-subtraction finalize: guard-tie (==5) rounds toward zero, else half-up
fpa_sub_finalize:
        ld   a,(ARGA+FPNUM_DIG+14)
        cp   5
        jp   nz,round_and_finalize   ; 0-4 -> down, 6-9 -> up (shared tail, unchanged)
        dec  a                       ; exact tie: 5 -> 4 so the half-up tail drops it
        ld   (ARGA+FPNUM_DIG+14),a
        jp   round_and_finalize
```

Re-target the **three diffsign exits** (`fpa_zero_result`-via-`jr c`,
the `k=0` `jr z,fpa_done`, and the post-shift `jr fpa_done` at
[float-arith.asm:588](../basic/float-arith.asm:588)/[:595](../basic/float-arith.asm:595)/[:606](../basic/float-arith.asm:606))
from `fpa_done` to `fpa_sub_finalize`. The **same-sign** add exits (line 558/560)
keep going to `fpa_done` (= `round_and_finalize`) untouched → add ties stay half-up.
`fpa_zero_result` routing through the new tail is harmless (all-zero, guard 0, no tie).

- **Correctness of the 5→4 trick:** we carry a single guard digit (index 14); guard==5
  is the exact tie. Setting it to 4 makes the unchanged `cp 5` half-up drop it → toward
  zero. Guard 6–9 and 0–4 bypass the `dec` → identical to before. Exactly reproduces
  the observed reference behaviour on every tie case in §1.
- **Cost (as built):** +15 bytes in the diffsign branch (the 2 live `jr` re-targets are
  byte-neutral; the `fpa_sub_finalize` stub is the only growth — `LD A,(nn)`+`CP 5`+
  `JP NZ`+`DEC A`+`LD (nn),A`+`JP` = 15 B, fully localized to the fpa region). **Repack-only**
  (`float-arith.asm` is `IF ROM_BASE < $4000`) → ships in the merged main ROM; **lean
  `basic.rom` unaffected, `LEAN_SHA256` unchanged** (verified). Repack page-0 low region
  5075→5090 B, page-1 free unchanged.

## 4. Gate (closes a float-acceptance blind spot)

`float-acceptance` is green today **only because its matrix has no effective-subtract
guard-tie** (same class of blind spot as division). Add to the float differential
(`float_arith` half of `make float-acceptance`, batched omsx_repl):
- Effective-subtract ties, both result signs: `2-5E-14`, `5E-14-2`, `8.5-5E-14`,
  `100-5E-12`, and a `+`-token effective subtract (`2+(-5E-14)`).
- Effective-add ties (must stay away-from-zero, regression guard): `1+5E-14`,
  `-1-5E-14`, `2-(-5E-14)` (a `-` token that is an effective ADD → `2.0000000000001`).
- Near-tie both sides (regression guard, must be unchanged): guard-4 and guard-6
  variants (`2-4E-14`, `2-6E-14`).
All asserted **==reference** (this is now bug-for-bug identity, no divergence table).
Standing gates stay green; **Fable review** of the change.

## 5. Sign-off — ✅ ALL RESOLVED (user 2026-07-13), implemented `fe0d99c`

1. **Scope:** effective-subtract tie only; multiply untouched (half-up both); division on
   its own track; `round_and_finalize` byte-identical. ✅
2. **Robustness caveat (accepted):** the rule is fit to *exact* single-guard ties (all
   that's observable at 14-digit PRINT and all our representation carries). A sub-guard
   sticky bit is invisible to us *and* to the reference at this precision; the 5→4 rule
   reproduces every observable case. Faithful-to-observable. ✅
3. **Model split:** characterization Fable-solo; implementation Sonnet on this signed-off
   spec. ✅
