# D-N8ARM — two knife files whose arms had stopped testing anything

*2026-08-29. `scratchpad/ngram7_knives.py`, `ngram8_knives.py`,
`ngram9_knives.py`, `ngram6_knives.py`, `ngram8_probe.py`, `knife_guard.py`,
`tools/run_gates.py`. **No ROM change** — every finding here is about the
apparatus, and two of them retired filed carve candidates.*

Picked up two TODO residuals that shared a shape: *"the knife moves 0 rows with
the ROM provably changed, so the code may be removable."* **Both were wrong, and
for different reasons.** Neither was a thin row set; one was a row-geometry hole
and one was a second cause of green.

## 1. `str_target_parse`'s deferred-fault bail — DECLINED (§4 of spec-basic-ngram9)

Filed as a 9 B carve on the strength of K-N9B, which nopped
`jp nz,fp_runtime_error` and moved nothing. **Don't nop the jump — retarget it:**

| row | HEAD | retargeted | nopped |
|---|---|---|---|
| `s.mid.sub` | `ERR 11 AT 30` | **`ERR 13 AT 30`** | `ERR 11 AT 30` |

The bail is reached and taken. The nop's zero came from `ex_mid_stmt`'s next act
— `eval_pos_arg` → `get_int16_checked`, ending `jp check_fperr_only` — re-raising
the pending fault **inside the same statement**, not from `exec_stmt`'s boundary
as the note claimed. That is why even the line number never moved. And the cover
is MID$'s alone: `inpc_line` and `inp_readvar` reach `check_expr_errors` only
after `read_line`/`read_into_strscr` and `tgt_store_str`. Full detail and the
price correction (**3 B, not 9** — D-NGRAM9 had already merged the three sites)
are in [`spec-basic-ngram9.md`](spec-basic-ngram9.md) §4.

## 2. `str_arg_snap`'s snapshot — DECLINED, and the row set was the problem

K-N8B neuters `call str_snapshot_arg` and was recorded as an **expected null**:
zero rows, ROM provably changed, read as *"the cut reached the artifact and
reddened nothing"*. The probe had 17 rows and **every one printed the function's
RESULT**. Nothing read the **source** back, so in-place truncation of the source
— precisely the damage the snapshot prevents — could not appear at all:
`LEFT$(A$,2)` returns `AB` whether or not it wrecked `A$` getting there.

Three rows of the form `C$+"/"+A$` close it:

| row | all three sides | K-N8B applied |
|---|---|---|
| `s.left.src` | `AB/ABCDE` | **moves** |
| `s.right.src` | `DE/ABCDE` | **moves** |
| `s.mid.src` | `BC/ABCDE` | **moves** |

**The snapshot is load-bearing; the ~4 B candidate is declined.**
[[a-coverage-row-whose-geometry-cannot-reach-the-case]]

## 3. 🔴 K-N8A had been cutting a string that was not in the source

`ngram8_knives.py`'s other arm looked for `jp nc,type_mismatch_error`. The
shipped shape is `jp nc,sas_decline` — the `pop af` fix landed **after** the arm
was written and the file was never re-run against the final source. It has
printed `KNIFE BROKEN` ever since.

Its stated claim was false too: *"exactly the three `.bad` rows must return to
ERR 2 — the divergence this slice closed."* D-NGRAM8 closed no such thing.
`.bad` reads ERR 2 on this tree **today** and the divergence is filed open. The
arm was describing **D-NGRAM9's** fix, written into **D-NGRAM8's** file.
[[a-justification-parenthesis-is-an-unrun-claim]]

It is now the arm the slice actually earned: drop `sas_decline`'s `pop af` and
the three `.pend` rows must move — the frame-depth bug that cost a red gate.

## 4. 🔴 A repair to the instrument broke a gate that reads it

Sweeping all seven `ngram*_knives.py` S1 arms for pattern elements that no longer
occur anywhere in the tree found **2 of 7 stale** — and what staleness costs
turned out to be decided by an unrelated design choice:

| file | expects | stale element | consequence |
|---|---|---|---|
| `ngram8` | **0** open-coded runs | `jp nc,str_eval_no` | **VACUOUS** — matched nothing, reported 0, passed |
| `ngram7` | **1** (the body itself) | `ld ix,… + 3*…` | **RED** — loud, in a log nobody re-ran |

`ngram7`'s element was written to match the **output of a buggy normaliser**:
`ngram_sweep.py`'s key normalisation carried a doubled backslash (`r'\\s+'`) so
it never stripped whitespace. Repairing that regex on 2026-08-28 silently
invalidated the pattern.

⚠️ **D-NGRAM7 had already added a control for exactly this class** — and it
checked only `PAT[0]`, so a stale element in any later position sailed through.
`knife_guard.pattern_alive()` now checks **every** element and names the stale
ones; arms K7/K8/K9 cover it, K9 being the later-position case the old control
missed. Element presence is *necessary, not sufficient* (the elements can each
exist while the sequence does not) — it is the cheap half, and the half that was
missing.

🎯 And `ngram8`'s expectation was itself part of the bug. Repaired, the pattern
matches **1** run — `str_arg_snap`'s own body, the surviving copy. The arm now
wants 1, so a re-open-coded site shows up as 2.

## 5. The skip's premise, which nothing had checked

`gates`' emulator-tier skip is proved against a fingerprint over
`probes/`, `tests/`, `tools/` + the `Makefile`. That is a proof **only while
every script an emulator unit runs lives in those trees** — and `scratchpad/` is
tracked here on purpose. The premise holds (0 of 23 recipes reach outside it),
but it was true-when-someone-looked rather than checked. It is now re-derived at
every skip, with an unreadable recipe refusing rather than passing. Detail in
[`spec-gateskip.md`](spec-gateskip.md) §3.1.

## 6. Falsification

| arm | requires | measured |
|---|---|---|
| K-N9B | retarget the bail → `s.mid.sub` moves ERR 11 → ERR 13 | **exactly that 1** |
| K-N9C | nop the bail → asserted **0**, cause named | **0** |
| K-N8A | drop `pop af` → the three `.pend` rows move | **exactly those 3** |
| K-N8B | neuter the snapshot → the three `.src` rows move | **exactly those 3** |
| `knife_guard --selftest` | K7/K8/K9 on `pattern_alive` | ✅ |
| `run_gates --selftest` | 6 arms incl. a stray-path plant and a matcher control | ✅ |

🟢 **Every arm in all four files now scores against an EXPECTED ROW SET**, not
against "did anything move". A count is what let two wrong arms sit unread.
