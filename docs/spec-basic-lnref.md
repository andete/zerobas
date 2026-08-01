<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-LNREF — the line-number REFERENCE: the arming LIST, and the 65529 SPLIT

Measurement:
[`docs/lnref-msx1-characterization.md`](lnref-msx1-characterization.md) — two
references (Philips VG-8020, National CF-3300) agreeing on **all 217** `lnr` /
`lnrx` / `lnr2` / `lnv` / `lnv2` / `lna` / `lnrd` rows, `--repeat 2`, every
payload past the echo guard on all three sides.

Neighbours whose cells this must not move: D-LNLIST
([`spec-basic-lnlist.md`](spec-basic-lnlist.md) **R-L1/R-L2/R-L3**), D-LNBLANK
([`spec-basic-lnblank.md`](spec-basic-lnblank.md) **R4/R5**), D-EXPKW
([`spec-basic-expkw.md`](spec-basic-expkw.md)), D-CNAME, D-NAMDOT.

---

## 1. ⚠️ THE TWO FILED ITEMS ARE ONE MECHANISM, AND BOTH TITLES ARE WRONG

`TODO.md` files *"`$0E` refs missing for LIST/DELETE/AUTO/RENUM/ELSE"* and
*"`20 GOTO 99999` tokenises 3 B SHORTER on zb"* as separate items. They are two
**rules of one mechanism** — line-number mode, `branch_lineno` /
`bl_acc` in [`basic/tokenise.inc`](../basic/tokenise.inc) — and each filed
description is refuted by measurement:

* **The verb list of five is wrong in both directions.** Fourteen reserved words
  arm on the reference. Three of the filed five (`DELETE`/`AUTO`/`RENUM`) have
  **no token at all** on zerobas, so their rows diverge for a second reason and
  cannot attribute anything — they are the *keyword-gap* item, not this one.
  Three verbs the item never names **do** arm: **`RETURN`**, **`ERL`**,
  `LLIST` — and the first two are tokens zerobas already emits.
* **The "3 bytes shorter" is a SPLIT, not a length.** The reference stops a
  reference at 65529 and starts a new one at the next digit; zerobas wraps at 16
  bits, silently.

🔴 **And one missing arm is a live runtime defect.** `IF 0 THEN 20 ELSE 30`
raises **`Syntax error`** on zerobas today. `if_false`
([`basic/interp.asm:1347`](../basic/interp.asm:1347)) already tests
`cp LINENO_TOKEN` after the `$A1` and jumps to `ex_goto_at`; the feature is
written, reachable, and has never fired because the crunch never produced its
`$0E`.

## 2. The rules

* **R-R1 (the arming LIST)** — crunching any of **`GOTO` `RUN` `RESTORE`
  `GOSUB` `RETURN` `LIST` `LLIST` `ELSE` `RESUME` `DELETE` `AUTO` `RENUM`
  `THEN` `ERL`** arms line-number mode (D-LNLIST **R-L1**). Every other reserved
  word leaves it as it was — which, via **R-L3**, means an alphabetic word
  *clears* it.

  🔴 **It is a LIST and it cannot be a range or a threshold.** `IF` (`$8B`) sits
  *between* four arming tokens and does not arm; `ERROR` (`$A6`) is adjacent to
  `RESUME` (`$A7`), `DEFSTR` (`$AB`) to `RENUM` (`$AA`), `TO` (`$D9`) to `THEN`
  (`$DA`), `ERR` (`$E2`) to `ERL` (`$E1`) — none of them arm. Measured over the
  whole 162-word denominator, not sampled.

  ⚠️ **`REM`, `DATA` and `CALL` are UNOBSERVABLE, not negatives.** They swallow
  or re-scan the rest of the statement on every machine, so no line number can
  follow them; the existing clear at the `match_kw` site (D-LNLIST §3) already
  covers them and this change does not touch it.

* **R-R2 (`ELSE` is reached by its FIRST token byte)** — `ELSE` crunches to
  `COLON,$A1`, and `branch_lineno` is handed the **first** byte emitted
  (`match_kw`, [`basic/tokenise.inc:571`](../basic/tokenise.inc:571)). So the
  test is `cp COLON`. This is safe because `branch_lineno` is reached **only**
  from the `match_kw` success path and `"ELSE"` is the **only** `kwtable.inc`
  entry whose first token byte is `COLON` (`tk_apos` writes its own `COLON`
  without going through `match_kw`). A bare `:` typed in a statement is copied
  by `tk_copy`, which *clears* the mode and never calls `branch_lineno` —
  `lnl-colsep` (`20 GOTO 1:5` → `<89> <0E><01><00>:<16>`) is the standing cell
  that says so, and knife **K3** aims there.

* **R-V (the 65529 split)** — a line-number reference takes another digit only
  while the resulting value would stay **≤ 65529**. The first digit that would
  exceed it **ends the reference without consuming it**; the mode is still armed
  (R-L2), so that digit begins a **new** reference.

  ```
  20 GOTO 99999    ->  <89> <0E><0F>'   <0E><09><00>      9999 || 9
  20 GOTO 65530    ->  <89> <0E><99><19><0E><00><00>      6553 || 0
  20 GOTO 65529    ->  <89> <0E><F9><FF>                  one reference
  ```

  Implemented as **"stop once the accumulator has reached 6553"**, which is the
  same predicate: `v*10 + d > 65529 ⟺ v ≥ 6553` for `d ≤ 9`.

  ⚠️ **65529 is the SAME constant as the leading line number's ceiling**
  (D-LNBLANK **R4**) and the **response is different**: a leading number past it
  is refused with `Syntax error`; a reference past it is split. Two rules, one
  bound — and `parse_lineno`'s saturating guard must not be copied here.

  🔴 **The test must run BEFORE the character is fetched, and `lnv2-blk30` is
  why.** `20 GOTO 6 5 5 3 0` keeps its blank on both references
  (`<0E><99><19>`␣`<0E><00><00>`). R5's blank lookahead commits to the whole run
  the moment it sees a digit past it, so a ceiling tested *on the digit* has
  already swallowed the blank and emits the two references with **no space
  between them**. Testing at the top of `bl_acc` is the only placement that
  reproduces both §2 and §2.1. Knife **K5** aims there.

* **R-E (`$0E` is a numeric term)** — `$0B` `$0C` `$0D` `$0E` are one family in
  the crunched stream: a token followed by a 2-byte little-endian value. `ev_f`
  must accept the whole family, because `ERL=<n>` puts a `$0E` inside an
  ordinary expression.

## 3. The change

### 3.1 `basic/tokenise.inc` — sub-ROM only

`basic/tokenise.inc` is `include`d by
[`sub/sub.asm:213`](../sub/sub.asm:213) and nothing else, so both tokeniser
changes are **sub-ROM page-0** changes. Measured on a clean build of HEAD that
region had **3986 B** free (⚠️ *not* the ~4008 B the project notes carry — that
figure predates a later slice, and it was re-measured here rather than quoted);
the main-ROM walls (low **9 B**, page 1 **5 B**) are not touched by this half.

| site | change |
|---|---|
| `branch_lineno` | four new tests — `LIST_TOKEN` `$93`, `COLON` (`ELSE`, R-R2), `RETURN_TOKEN` `$8E`, `ERL_TOKEN` `$E1` — appended to the existing six-`cp` chain. **+16 B** |
| `bl_acc` (top) | R-V: `DE >= 6553` → `jr bl_done`, tested **before** `ld a,(hl)`. **+12 B** |

**Measured: sub page 0 3986 → 3958 B free, NET +28 B**, exactly the two rows
above. Sub page 1 unchanged at 3339 B.

**The chain stays a chain.** A `cpir` over a 10-byte table would save ~18 B, and
it is the wrong shape here: §1.1 of the measurement says the arming set is a
**list** with non-arming neighbours on both sides of every boundary, so the ten
`cp`s *are* the rule, one line each. Sub page 0 is not the wall.

**Four arming tokens are deliberately ABSENT from the chain:** `LLIST` `$9E`,
`DELETE` `$A8`, `AUTO` `$A9`, `RENUM` `$AA`. zerobas' `match_kw` can never emit
them (no `kwtable.inc` entry), so a test for them would be logic no row can
exercise. §5 pins the trip-wire that makes the keyword-gap slice add them.

### 3.2 `basic/expr.asm` — main ROM page 1, and it must PAY FOR ITSELF

`ev_f`'s literal dispatch ([`basic/expr.asm:505`](../basic/expr.asm:505)) has
`cp HEX_TOKEN / jp z,ev_f_word` and `cp OCT_TOKEN / jp z,ev_f_word` — **10 B**
for two members of a four-member family. Page 1 has **5 B** free, so a third
`cp/jp` pair (5 B) would consume the entire headroom and leave zero.

Collapse the two tests into the family's **range** instead:

```
                cp      OCT_TOKEN           ; $0B..$0E are all <tok>,<word LE>:
                jr      c,ev_f_notword      ;   $0B &O, $0C &H, $0D line ADDRESS,
                cp      LINENO_TOKEN+1      ;   $0E line NUMBER
                jp      c,ev_f_word
ev_f_notword:
```

**9 B replacing 10 B — net −1 B on page 1 (5 → 6 B free), and `$0E` is gained
rather than paid for.**

⚠️ **`$0D` rides along, and it is unreachable.** `LINEADDR_TOKEN` is the
post-`RUN` address form; zerobas never emits it (`sysvars.inc` is its only
mention), so no row can reach that arm. It is included because the range is the
family, and excluding it would cost bytes to express a distinction nothing can
observe.

### 3.3 What this change does NOT do

* **`RETURN <line>` stays unimplemented.** `ex_return`
  ([`basic/program.asm:1089`](../basic/program.asm:1089)) pops the frame and
  never reads its argument. After this change the argument is stored as `$0E`
  and still ignored, so `lnrd-return` **stays divergent** and is pinned (§5).
  Filed, not fixed — it is a statement feature, not a crunch rule.
* **`LIST <range>` stays a whole-program `LIST`.** `ex_list` documents ignoring
  its argument as a Phase-2 divergence. `lnrd-list` (`1 0` on all three sides
  today) is the must-not-move cell that says this change does not make it worse.
* **No keyword is added.** `DELETE`/`AUTO`/`RENUM`/`LLIST`/`DEFINT`'s single
  token stay filed.

## 4. Rows

**Divergent today, must AGREE after (39):**
`lnr-return` `lnr-list` `lnr-else` `lnr-erl` ·
`lnr2-return` `lnr2-erl` ·
`lnv-d6` `lnv-d7` `lnv-d8` `lnv-b30` `lnv-b31` `lnv-b32` `lnv-b33` `lnv-b34`
`lnv-b35` `lnv-b36` `lnv-b37` `lnv-huge` `lnv-huge2` `lnv-mega` `lnv-thenh`
`lnv-elseh` ·
`lnv2-blk30` `lnv2-listbig` `lnv2-onbig` `lnv2-erlbig` ·
`lna-listctl` `lna-listrng` `lna-listopen` `lna-listplus` `lna-listkw`
`lna-listcol` `lna-elsectl` `lna-elseb` `lna-elseplus` `lna-elsecol` ·
`ref-list` `ref-else` (their `INFORMATIONAL` marks are **retired**) ·
`lnrd-else` (say mode) — plus the `lnr`/`lnrx` rows below that stay pinned.

**MUST NOT MOVE — green on all three sides today:**
the other **133** `lnr` rows, `lnr2-goto` `lnr2-nokw`, `lnv-d1`…`lnv-d5`
`lnv-b28` `lnv-b29` `lnv-zero` `lnv-lead0` `lnv-lead00`, `lnv2-blk29`,
`lnrd-ctl` `lnrd-then` `lnrd-erlctl` `lnrd-list`, **`lnrd-erl`**, and the whole
standing `ref` / `lnl` / `dot` / `dec` / `nam` / `exp` / `cnm` corpus.

🔴 **`lnrd-erl` is the load-bearing control.** It is green *before* this change
and it is the row R-E exists for: arming `ERL` without §3.2 puts a `$0E` where
`ev_f` has no arm and this row goes red. A control that agrees today is exactly
the kind that caught the regression D-BADFNUM's signed-off design shipped.

🔴 **`lnv-lead00` is the control that separates R-V from a digit-count rule.**
Eight digits, no split. Predicted green *from the rule*, not from its mark.

**Stays divergent, PINNED as `KNOWN_DIVERGE` (8):** `lnrx-delete` `lnrx-auto`
`lnrx-renum` `lnrx-llist` `ref-delete` `ref-auto` `ref-renum` — the four words
that arm on the reference and have no zerobas token — **plus `lnrd-return`**.
The allowlist stops being empty **on purpose**; see §5.

**Informational (24):** the remaining **20** `lnrx` rows, `lnr-defint`, and
`lna-renum3` `lna-auto2` `lna-delrng`. Their reference answer for the *argument*
is either `<0F><0A>` too or unreachable behind an absent token, so they carry
**no arming obligation this build can meet**: the only thing wrong with them is
the missing keyword, which is a different item. Pinning them would put 24 more
entries in the allowlist to say nothing about this rule.

⚠️ **`lnrx-inputs` is NOT in either list — it AGREES.** `20 INPUT$ 10` stores
`<85>$ <0F><0A>` on all three sides: `INPUT$` has no token of its own at crunch
level on the reference either, so zerobas' `INPUT` + literal `$` is already
byte-exact. One of the 25 words the coverage sweep counts as absent is absent
only from the table — the `INTERVAL` shape, found by this walk.

## 5. 🔴 The pinned rows are a TRIP-WIRE, and the empty allowlist is spent on it

`DELETE`, `AUTO`, `RENUM` and `LLIST` **arm on the reference**. zerobas cannot
arm them because it has no token, and §3.1 deliberately keeps them out of the
chain. The failure mode is obvious and silent: the keyword-gap slice adds four
`kwtable.inc` entries, every crunch row for them goes from *"no token"* to
*"token, wrong argument"*, and this defect comes back for four verbs with
nothing red.

Pinning those seven rows to zerobas' **exact current bytes** closes it. A pin
passes only while the row keeps diverging in exactly that way, so the moment a
token lands the pin stops matching, the gate goes red, and the arming byte
cannot be forgotten. `lnrd-return` is pinned for the same reason against
`ex_return`.

🔴 **AND IT EARNED ITS KEEP INSIDE THE SLICE THAT CREATED IT.** The first full
gate run after the pins went in reported

```
ALLOWLIST FAILURE -- KNOWN_DIVERGE no longer describes zerobas:
  lnrx-llist: zerobas now reads 'line 20 | L<93> <0E><0A><00>',
              filed as 'line 20 | L<93> <0F><0A>'
```

zerobas mangles `LLIST` into the variable `L` plus a **genuine `LIST` token**
(`$93`) — so the moment `branch_lineno` learned to arm on `$93`, this row's
*argument* started crunching to `$0E` too. Nothing regressed: the argument is
now the reference's and only the token is still wrong (`L` + `LIST` is a syntax
error before and after). But the value filed minutes earlier was **already
stale**, and the allowlist is what said so rather than a re-reading of the
table. It will fire a **third** time when `LLIST` gets a `kwtable.inc` entry and
the row goes fully green — which is exactly the behaviour this section is buying.

⚠️ **This ends a five-cohort streak of an EMPTY `KNOWN_DIVERGE`, and that is a
deliberate trade.** Every entry is measured, currently true, and has one named
retirement path (the keyword-gap item / `RETURN <line>`). The alternative —
leaving them informational — is the shape `TODO.md` already files as a defect
under `dir-name`: **a row that has never gated anything.**

## 6. Gates

🔴 **`make lnblank-acceptance` CANNOT SEE THE `lnrd` ROWS, AND THAT WOULD HAVE
MADE THIS SPEC'S LOAD-BEARING CONTROL THEATRE.** The probe drops every
`SAY_ONLY` row from any non-`--say` run
([`basic_probe_lnblank.py`](../probes/basic/basic_probe_lnblank.py):
`sel = [c for c in sel if args.say or c[0] not in SAY_ONLY]`), so `lnrd-erl`,
`lnrd-else` and the `lnrd-return` pin would be measured by hand and gated by
nothing — the exact shape `TODO.md` files under `dir-name` as *"the row has
never gated anything."*

**New target `make lnblank-say-acceptance`** runs `--gate --say`, defaulting to
`ONLY=lnrd-`, and joins the corpus. It is the **first gated `--say` surface in
this probe**; the rest of it (`err`/`dir`/`dotd`/`lnld`/`cnmd`) stays un-gated
and stays filed, because `dir-name`'s known divergence lives there and fixing it
is a different item. Selecting a wider `ONLY=` is how the next slice widens it.

Full corpus, after the change:
`make unit-test` 55/55 · dead-code gate 0/0 both builds ·
**`lnblank-acceptance` `REPEAT=2` — 518/518 gating rows agree** across all three
sides (up from 327 rows before this slice's four new batteries), 7 of them
allowlisted and pinned; the only divergent rows reported are the 24
informational ones ·
**`lnblank-say-acceptance` `REPEAT=2` — 7/7**, 1 pinned ·
`lnblank-echo` "every gating payload typed verbatim on every side" (all **210**
new rows `ECHOED` on all three sides) ·
`logicops-acceptance` **193/193** · `float-acceptance` **ALL PASS** ·
`array-acceptance` **149/151** (`ifc.instr.zero`, `ifc.instr.neg` — confirmed by
name, the case-only wording artifact) ·
`arrdim` **73/73** · `clearpool` **52/52** · `badfnum` **93 cases, 0 unfiled
divergence** · `lof` **45 cases, 0 drift** · `chancost-characterize` **53 cases,
0 filed divergences** · `diskbasic` **34/34** · `bdos` **12/12** ·
`fat-error` **8/8 ALL PASS** · `error-trap` **ALL PASS** · `abort` **49/49** ·
`stop-trap` / `strig-trap` / `key-trap` **ALL PASS** · `linemax` **60/60** ·
`sysvarsweep` **apparatus OK**, C-REPRO / C-PRIV / C-REPRO-2 / C-VACATED all
green.

🎯 **`sysvarsweep` independently confirms the `GOTO 99999` item closed** — it is
the instrument that filed it. See
[`lnref-msx1-characterization.md`](lnref-msx1-characterization.md) §3.1:
`ONELIN` under `s7-fired` now reads `refs=0000->1c80  zb=0000->1c80`, where
D-REHOME measured `$801C` vs `$8019`.

⚠️ **`strig-trap` and `key-trap` are the gates that PARSE `$0E`**, and R-V can
now hand `ON KEY GOSUB` more list slots than the user wrote (`lnv2-onbig`). They
are named here for the same reason D-LNLIST named them.

⚠️ **`float-acceptance` and `logicops-acceptance` are named because this touches
`ev_f`.** A tokeniser regression sat unread for two slices because
`logicops-acceptance` was absent from every spec's list (D-EXPKW); `ev_f` is the
common path of every numeric literal in the language.

**Split assertion — RECORDED, not asserted equal.** §3.2 is a main-ROM change,
so both main images move on purpose:

| image | HEAD | after |
|---|---|---|
| `build/basic-reloc.rom` | `e045379a…` | `cdefd69f…` |
| `build/sub.rom` | — | `e55db76d…` |
| `build/zerobas-main-eu.rom` | — | `2a752347…` |

**Walls: low region 9 B free → 9 B (untouched); main page 1 5 B → 6 B (NET −1 B,
it PAID for itself); sub page 0 3986 B → 3958 B (+28 B).** `zerobas-main-eu.ips`
and `.bps` are regenerated by `make basic-reloc` and move with the ROM.

## 7. Knives — each with a predicted RED set **and** predicted GREEN survivors

### 7.0 ⚠️ Apparatus: the first knife runner REVERTED THE SLICE, not the knife

The first cut of the runner ended with `git checkout basic/tokenise.inc`. That
restores the file to **HEAD** — the knife *and* D-LNREF's own change — so the
"reverted" tree silently went back to being the unfixed one. It was caught by
`grep -c "D-LNREF" basic/tokenise.inc` reading **0**, and the change was
reapplied and rebuilt to a **byte-identical** `basic-reloc.rom`
(`cdefd69f…`), which is what says nothing was lost.

🔴 **A knife must be reverted against the BUILD IT CUT, never against HEAD.** The
runner now restores from a copy of the pre-knife sources taken before the first
cut, and each knife's log ends with a restore that is verified by rebuilding. The
same hazard is the reason D-EXPKW's "not mine" A/B was wrong: an A/B whose
baseline is not the thing you think it is measures nothing
([`not-mine-falsification-says-nothing`] in the project memory).


| # | cut | predicted RED | predicted GREEN survivors |
|---|---|---|---|
| **K1** ✅ | drop the `LIST_TOKEN` test | **matched:** `lnr-list` `lna-listctl` `lna-listrng` `lna-listopen` `lna-listplus` `lna-listkw` `lna-listcol` `lnv2-listbig` `ref-list` | `lnr-else` `lnr-return` `lnr-erl` `ref-else` `lna-else*` — three independent arms untouched |
| **K2** ✅ | drop the `RETURN_TOKEN` test | **matched:** `lnr-return` `lnr2-return`, and nothing else | `lnr-list` `lnr-erl` `lnr-else` `ref-list`. ⚠️ `lnrd-return` **cannot witness K2** — it is divergent either way, because `RETURN <line>` is unimplemented (§3.3). A pinned row is not a knife target |
| **K3** ✅ | make `tk_copy`'s `:` **arm** instead of clear, leaving `branch_lineno`'s test in place | **matched:** `lnl-colsep` `lna-listcol` `lna-elsecol` — a TYPED `:` arms | `lnr-else` `lna-elsectl` `ref-else` (`ELSE`'s `:` comes from `match_kw`, not `tk_copy`) and `lnl-colon` `lnl-colctl` `lnr2-nokw` (a NAME behind the colon disarms on its own — D-LNLIST §7.2) |
| **K4** ✅ | drop §3.2's `$0E` arm, keep the `ERL` arming | **matched, and it is the sharpest cut in the set:** the memory gate reads **3/3 GREEN** (`lnr-erl` `lnr2-erl` `lnv2-erlbig` — the stored bytes are still exactly the reference's) while **`lnrd-erl`** goes `1 21` → **`0 2`**, a Syntax error | everything else in both gates |
| **K5** ✅ | test R-V on the digit instead of at the top of `bl_acc` | **matched — `lnv2-blk30` ALONE, 50/51**, and the whole difference is the blank: ref `<0E><99><19>`␣`<0E><00><00>` vs knifed `<0E><99><19><0E><00><00>` | every other `lnv`/`lnv2`/`num` row. The placement argument, isolated to the one row in the corpus that can see it |
| **K6** ✅ | R-V bound `6553` → `6554` | **matched:** `lnv-b30` `lnv-b31` `lnv-b32` `lnv-b33` `lnv-b34` `lnv-b35` `lnv-b36` `lnv-b37` `lnv2-blk30` — nine, and exactly the values that reach 6553 | `lnv-b28` `lnv-b29` `lnv-huge` `lnv-huge2` `lnv-mega` `lnv-d6`…`d8` `lnv2-blk29`, **and every `num-` row** — the LEADING number's ceiling is a different constant (`LINENO_CEIL`) and does not move |
| **K7** ✅ | R-V bound `6553` → `6552` | **matched:** `lnv-b28` `lnv-b29` `lnv-mega` `lnv2-blk29` — every value that reaches the accumulator's **last legal** state | `lnv-b30`…`lnv-b37` `lnv-huge` `lnv-huge2` `lnv-d6`…`d8` `lnv2-blk30`, all already past the bound either way. **K6 and K7's RED sets are DISJOINT**, so the constant is bracketed from both sides and neither knife could be passing for the other's reason |

⚠️ **K3 was RE-AIMED before it ran, and the correction is the finding.** As first
written it moved the `COLON` test *out of* `branch_lineno` and into `tk_copy` —
which would have reddened `lnr-else` as well, because `ELSE`'s colon is emitted
by `match_kw` and never passes through `tk_copy` at all. A knife that reddens
the row it was supposed to leave standing measures the feature, not the
placement. The cut that runs **adds** an arm to `tk_copy` and leaves
`branch_lineno` alone, which is the only form that isolates R-R2's *placement*.
