<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-HIMDOM — CLEAR's ceiling is an ADDRESS, not an int16, and D-CLRFIX got that wrong

Status: **✅ SHIPPED. +3 B of main page 1** (free **5 → 2 B**), on `649b548`.
A same-day correction to [D-CLRFIX](spec-basic-clrfix.md) §2(b), plus the first
full characterization of the ceiling's domain.

---

## 1. 🔴 The regression, and why the slice that caused it could not see it

D-CLRFIX replaced `clr_himem`'s bare `call eval` with `call eval_int16_checked`,
whose `get_int16_checked` stage raises **ERR 6** for `|x| > 32767`. It was
justified by one row:

    q.ovf   CLEAR 200,70000   ->  ERR 6 on the VG-8020 AND the CF-3300

**That row is rejected under both candidate rules**, so it cannot separate them:

* **(a) SIGNED int16** — legal is −32768..32767.
* **(b) the MSX ADDRESS domain** — legal is −32768..65535, which is what
  `basic/poke.asm` has always used (`eval_addr` / `fac_to_int_addr`).

And the one accepted control, `&HD000`, passes under (a) **only by accident**:
MSX BASIC reads a hex literal ≥ `&H8000` as NEGATIVE (−12288), so `|x| <= 32767`
without the value ever being small. **No row in D-CLRFIX's 26 held a decimal in
[32768, 65535]**, and that is exactly the interval the two rules disagree on:

| row | statement | VG-8020 | CF-3300 | zerobas after D-CLRFIX |
|---|---|---|---|---|
| `d.50000` | `CLEAR 200,50000` | `0 ->50000` | `0 ->50000` | 🔴 `6 SAME` |
| `d.40000` | `CLEAR 200,40000` | `0 ->40000` | `0 ->40000` | 🔴 `6 SAME` |

🎯 **The tell was written down in D-CLRFIX's own report, one line above the
defect, as reassurance.** *"`&H9000` is −28672 as a signed int16, so `|x| <=
32767` and the accepted ceiling still passes."* The next question — **then what
does a positive 50000 do?** — is the whole slice, and it was not asked.

⚠️ The knives could not have caught it either: K-CF3 narrowed the coercion
*further*, which is the wrong direction to probe a rule that was already too
narrow.

## 2. ✅ As built — +3 B

    call eval_addr           ; 3 B  the ADDRESS domain, -32768..65535
    call check_expr_errors   ; 3 B  raise BEFORE the store and the wipe
    ld   (HIMEM),de

replacing one 3-byte `call eval_int16_checked`. Main page 1 **5 B → 2 B**.

⚠️ **`eval_addr` DEFERS** — it sets `FPERR` and returns, which is why
`basic/poke.asm` tests the flag by hand — so `check_expr_errors` is a separate
call. Everything D-CLRFIX established about the *guard* (the trap survives, and
nothing is written before the raise) is unchanged and re-measured: all 26 of its
rows are byte-identical after this change.

## 3. The domain, characterized — 15 rows × 3 machines

`scratchpad/himdom_probe.py`. Face `<ERR> SAME` / `<ERR> -><himem>` — the error
code **and** whether the ceiling actually moved, read in direct mode either side
of the `RUN`. **Both references agree on every row.**

| band | arguments | references |
|---|---|---|
| ≥ 65536 | `65536`, `70000` | **ERR 6** — past the address domain |
| above the RAM top | `65535`, `&HFFFF`, `-1` | **ERR 5** |
| **accepted** | `40000`, `50000`, `&HD000` | **ERR 0**, HIMEM moves |
| in RAM, below BASIC's data | `32768`, `&H8000`, `&H8050` | **ERR 7** Out of memory |
| below `$8000` | `0`, `1`, `&H4000`, `32767` | **ERR 5** |

🎯 **`&HFFFF` and `-1` answer identically (ERR 5).** Same sixteen bits, different
surface syntax — so the rule is the VALUE, not the sign of the typed float. That
row is what retires D-CLRFIX §5's guess that the domain "is a range, not a sign":
it is a range, and now it has edges.

**zerobas: 12 DIFF → 10.** The two coercion rows close; the ten survivors are all
the *range* check (§5), which is a different rule and is filed, not guessed at.

⚠️ **Three rows moved from "rejected with the wrong code" to "accepted"**
(`65535`, `&HFFFF`, `-1`): under the too-narrow int16 rule they happened to be
refused with ERR 6 where the references say ERR 5, and the correct wider
coercion now lets them through to a range check that does not exist yet. That is
a real trade and it is stated rather than buried — **but it is still a net
improvement, 12 divergent rows down to 10**, and the coercion width is a fact
about the language where the accidental rejection was not.

## 4. 🔬 Knives — 2 of 2, and one of them has MEASURED predictions

`scratchpad/himdom_knives.py`, `scratchpad/himdom_knives.out`.

* **K-HD1** restores `eval_int16_checked` — **the exact build D-CLRFIX shipped**
  — so its predicted faces are read off `scratchpad/himdom_before.out`, a real
  run of that ROM, instead of being reasoned out. It is therefore also a
  standing detector for this precise regression. Predicted: **4** rows
  (`d.50000` `d.40000` `d.32768` `d.65535`) → `6 SAME`.
  🎯 **Note which rows are NOT in that set**: `&HD000`, `&H8000` and `&H8050`
  are hex literals ≥ `&H8000` and so read as negative, sitting inside the signed
  range untouched. That is the blind spot, made visible as a row set.
* **K-HD2** narrows to `eval_byte_checked` — the domain as small as it goes — and
  reddens **11** rows. It proves the accepted ceilings are detectors.
  ⚠️ `d.zero` and `d.one` stay green under it: **0 and 1 are inside every
  candidate domain, so they pin nothing about the width.** They are there for
  the ERR-5 low band, not for the coercion.

⚠️ **A third knife was designed and deliberately not run.** Replacing
`check_expr_errors` with a no-op would show the guard is load-bearing, but its
predicted HIMEM values are not derivable without reading `domain_convert_core`
to find what `DE` holds after a FAILED conversion. **A knife whose values I would
have to guess scores my guess, not the code.** The guard is already pinned on the
same instruction by D-CLRFIX's K-CF1.

## 5. What this does NOT fix — the RANGE check, three bands wide

zerobas accepts every value the coercion admits. The references apply a range
check on top of it, and §3 measures three distinct answers:

* **ERR 5 below `$8000`** — `0`, `1`, `&H4000`, `32767`. The boundary is exactly
  the bottom of RAM.
* **ERR 7 (Out of memory) inside RAM but below BASIC's data** — `32768`,
  `&H8050` (32848) are refused while `40000` is accepted, so the edge lies
  between 32848 and 40000 and is a property of the *current* program and
  variables, not a constant.
* **ERR 5 above the RAM top** — `65535` and friends. ⚠️ **This edge is
  machine-specific**: HIMEM boots at 62336 on the VG-8020 and **56951** on the
  CF-3300, so a value between them should be accepted on one machine and refused
  on the other. **No row here sits in that window** — that is the first thing the
  follow-up must measure, and it is what will decide whether the check reads a
  sysvar or a constant.

Filed in `TODO.md`. It is unpriced and main page 1 has 2 B, so it needs funding
before it needs a design.

⚠️ **And it interacts with this tree's own test fixtures**: `basic_probe_arrays.py`
squeezes memory with `CLEAR 200,&H8050`, which both references answer **ERR 7**.
Those rows are `zb`-only by declaration, so they are not wrong — but implementing
the ERR-7 band will break them, and they will need a ceiling inside the accepted
window instead.


## 6. Gates — 36 of 36 green

`scratchpad/himdom_gates.sh`, `scratchpad/himdom_gates.out`, from `rm -rf build`.

    GATES: 36 green, 0 red -- 36 run
    build/basic-reloc.rom 0d04f8b7 / build/sub.rom 490ffc49
    build/zerobas-main-eu.rom dd90f859

`lineerr-acceptance` 210/210, `unit-test` 59/59, `array-acceptance` 146/146,
`clearpool-acceptance` ALL PASS (62/62 gated). ⚠️ **`clearpool-acceptance` is in
the battery only because D-CLRFIX added it** — the list inherited from
D-CIRCMISS had no gate owning CLEAR, and this slice touches the same routine.

**And D-CLRFIX's own 26 rows were re-run on this build and are byte-identical**
(`scratchpad/himdom_clrfix_recheck.out`, `scratchpad/himdom_clrhimem_recheck.out`):
`q.ovf` still `6 0`, `q.trail` still `24 0`, `h.set` still `->36864`,
`h.trail`/`h.div`/`h.str`/`h.ovf` still `SAME`. **Widening the coercion did not
cost the guard.**

## 7. 🔴 The instrument re-introduced two faults fixed earlier the same day

* **The machine-specific value in the face.** Round 1 of this probe put the raw
  HIMEM in the face, and **12 of 15 rows scored "THE REFERENCES DISAGREE" while
  every ERR code agreed on every row** — HIMEM boots at 62336 on one machine and
  56951 on the other, so *leaving it alone* reads differently on the two. This
  is exactly what [D-CLRFIX](spec-basic-clrfix.md) §3.1 fixed in
  `clrfix_himem.py` hours earlier. 3 rows scored → 15.
* **The fence matched its own echo.** Round 2 read every ERR as the literal
  `";ERR;"`: the typed line `40 PRINT"<E";ERR;">"` contains `<E";ERR;">`, which
  satisfies `<E([^>]*)>` perfectly. The older probes survive the identical hazard
  with `[...]` **only because they require the captured span to be NUMERIC** — a
  guard I dropped when adding a second fence.

🎯 **A new probe does not inherit the fixes; it inherits the hazards.** Both were
caught by reading the output rather than the summary line — the first would have
reported 3 scored rows as if 3 were all there were, and the second produced a
face that was stable, plausible and entirely about the source text.
