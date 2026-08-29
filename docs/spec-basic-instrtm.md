# D-INSTRTM — `INSTR` with a non-string operand said Syntax error; both references say Type mismatch

*2026-08-29. `basic/str-engine.asm` (`ev_f_instr`'s two decline tails). Probe
`scratchpad/instrtm_probe.py`, arms `scratchpad/instrtm_knives.py`.*

**Cost: +10 B of the low region** (134 → 124 B free; page 1 unchanged at 349).
**Rows: 18, DIFF 5 → 0.**

## 1. The divergence

Found by D-NGRAM11 as two rows and filed. Measuring the whole surface first
turned two into **five**:

| row | references | before | after |
|---|---|---|---|
| `INSTR("ABCDE",5)` | ERR 13 | ERR 2 | **ERR 13** |
| `INSTR(2,5,"CD")` | ERR 13 | ERR 2 | **ERR 13** |
| `INSTR(2,"ABCDE",5)` | ERR 13 | ERR 2 | **ERR 13** |
| `INSTR("ABCDE",0*(1/0)+1)` | ERR 11 | ERR 2 | **ERR 11** |
| `INSTR(2,"ABCDE",0*(1/0)+1)` | ERR 11 | ERR 2 | **ERR 11** |

## 2. 🔴 Why the tail had to be SPLIT, not retargeted

`efi_reject_p` and `efi_reject_pa` were each reached **two different ways**:

- `jr nz` — *the `,` is missing* (a genuine syntax error)
- `jr nc` — *there IS an operand and it is not a string* (a type mismatch)

Both answered `Syntax error`. Retargeting the tail would have "fixed" three rows
and broken **seven** that are already correct — which is exactly the shape
D-MIDOP measured for the `MID$` statement, where the references answer 24 / 13 /
24 across three shapes. [[a-shared-tail-is-not-a-decision]]

**So the reference surface was measured before anything was changed**, and it
splits cleanly:

| must become 13 / 11 | must stay 2 |
|---|---|
| `INSTR("ABCDE",5)` | `INSTR(5,"CD")` |
| `INSTR(2,5,"CD")` | `INSTR(A,"CD")` |
| `INSTR(2,"ABCDE",5)` | `INSTR("AB")` |
| `INSTR("ABCDE",0*(1/0)+1)` | `INSTR("AB",)` |
| `INSTR(2,"ABCDE",0*(1/0)+1)` | `INSTR("AB","CD"` · `INSTR()` · `INSTR(2,"AB")` |

`INSTR(5,"CD")` stays `Syntax error` for a reason worth naming: a numeric first
argument is the **position** `p`, so that shape is a *3-argument form with `b$`
missing* and fails on the missing-comma arm, which is untouched.

## 3. The order is the fix, again

The new tails do what D-LEFTTM's does — **evaluate the operand, then defer
`FPERR_TYPEMM`** — because `ev_f_defer` is first-error-wins, so a fault the
operand itself raises keeps the answer:

```
efi_tm_pa:
                pop     de                  ; discard [aT]
efi_tm_p:
                pop     de                  ; discard [p]
                call    eval                ; the operand, numerically
                ld      e,FPERR_TYPEMM      ; unless the operand beat us
                jp      ev_f_defer
```

The discards use **DE, not HL** — HL is the cursor, still sitting on the operand,
and `eval` needs it.

## 4. 🔴 The arm found a third discriminating row I had not predicted

K-IT2 plants the mirror-image wrong fix (arm `TYPEMM` *before* evaluating) — the
mistake D-NGRAM8 made once and D-LEFTTM's K-LT2 pins in another verb. I predicted
the two `o.pend*` rows would move. **Three did.**

| row | correct order | armed too early |
|---|---|---|
| `t.a2num` / `t.p_anum` / `t.p_bnum` | ERR 13 | **ERR 13 — unmoved** |
| `o.pend` / `o.pendp` | ERR 11 | ERR 13 |
| **`m.dangle`** (`INSTR("AB",)`) | **ERR 2** | **ERR 13** |

`m.dangle` is the sharpest of the three and it is a *malformed* shape, not a
pending-fault one. It reaches the new tail — `str_eval_next` declines on the `)`
— and in the shipped order `call eval` then fails on that `)` and defers a
**syntax** error, which first-error-wins keeps.

🎯 **So the ordering is not merely "nicer for pending faults": without it, the
split would have broken a malformed shape that was already right.** And the three
clean-expression rows cannot tell the two fixes apart at all — a row set of only
`t.*num` would have scored the wrong fix green.

## 5. Falsification

| arm | requires | measured |
|---|---|---|
| K-IT1 | restore the shared tail → the 5 closed rows return to ERR 2, the 7 others hold | **exactly those 5** |
| K-IT2 | arm `TYPEMM` before evaluating | **exactly 3** (§4) |
| `penderr-acceptance` | the standing first-error-wins gate | **61/61** |
| `tmfp-acceptance` | the type/numeric pair, 50 rows | **50/50** |

Both arms score against an **expected row set**, not against "did anything move".
