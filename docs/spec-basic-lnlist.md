<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-LNLIST — a line-number list is a MODE, not a list

Measurement:
[`docs/lnlist-msx1-characterization.md`](lnlist-msx1-characterization.md) — two
references (Philips VG-8020, National CF-3300), agreeing on **all 44** `lnl` /
`lnld` rows, `--repeat 2`, past the echo guard.

Neighbours whose cells this must not move: D-LNBLANK
([`spec-basic-lnblank.md`](spec-basic-lnblank.md) **R5**), D-NAMDOT
([`spec-basic-namedot.md`](spec-basic-namedot.md) **R-D1/R-D2**), D-NAMBLANK
(**R-N1**).

---

## 1. ⚠️ THE FILED TITLE IS REFUTED — read this before anything else

`TODO.md` files this as *"a `.` DOES NOT END A LINE-NUMBER LIST"* and points at
`bl_num`'s comma-list loop. **The `.` is not special.** `1+5`, `1;5`, `1(5)`,
`1\5`, `1=5` — a dozen measured characters — all grow a second `$0E`, and
`1.5.7` grows a third. Adding `.` to a separator test would have shipped a rule
about a dozen characters too narrow, from the one row that found it.

This is the same shape as D-NAMBLANK (filed under `&B`, which turned out inert)
and D-LNBLANK (whose filed title was the smallest part four ways). The filed row
`dot-goto` **cannot distinguish** the filed rule from the measured one — both
predict its exact bytes.

## 2. The rules

* **R-L1 (arm)** — crunching `GOTO`, `GOSUB`, `THEN`, `RESTORE`, `RUN` or
  `RESUME` arms **line-number mode**, afresh per line.
* **R-L2 (effect)** — while armed, a digit that would begin a numeric constant
  begins a **line-number reference** instead → `$0E,<value LE>`, keeping
  D-LNBLANK **R5**'s blank transparency (`GOTO 1 0` stays `$0E,000A`); and a `.`
  that would begin a numeric constant under D-NAMDOT **R-D2** is copied
  **verbatim** instead (`GOTO .5` stores the value **5**; `GOTO .` stores a bare
  `.`, not the literal 0). Everything else crunches exactly as outside the mode.
* **R-L3 (disarm)** — cleared by anything **alphabetic** — a reserved *word*
  (`AND` `OR` `MOD` `PRINT` `ABS` …) or a variable *name* — by the two symbols
  that expand to word tokens (`?`, `_`), and by the statement separator **`:`**.
  Symbolic operators (`> = < + - * / ^ \`), punctuation (`, ; # ( ) .`), string
  literals and blanks leave it **armed**.

🔴 **R-L3's boundary is not a token value and cannot be tested as one.** `\` is
`$FC` and keeps the mode; `MOD` is `$FB` and clears it. `$F1..$F5` keep; `$F6`
`AND` clears; `$91` `PRINT` is below all of them and clears. The classes are
interleaved — the discriminator is *spelled with letters* vs *spelled with a
symbol*.

## 3. The change — `basic/tokenise.inc` only, sub-ROM only

`basic/tokenise.inc` is `include`d by [`sub/sub.asm:262`](../sub/sub.asm:262) and
nothing else, so this is a **sub-ROM-only** change: sub page 0 has 4024 B free.
Main-ROM walls (low 23 B, page 1 8 B) are not touched, and §6 asserts that by
hash.

**State.** `TKLNUM` — one byte at **`$E013`**, in the free `$E013..$E015` gap
below `INDLR_N` (`FCH_MODES` vacated it for `$EA00`, see
[`basic/sysvars.inc`](../basic/sysvars.inc)). Same aliasing argument as
`TKNAME`/`TKRADIX`/`TKRTOK`: a line's whole tokenise pass completes before any of
its tokens execute.

**`branch_lineno` SHRINKS.** Under R-L2 the ordinary `tk_loop` already copies the
blanks, commas and punctuation that `bl_yes`/`bl_list` were hand-walking, so the
blank-copy loop, the comma test and the list-continuation loop are **deleted**.
What remains is the digit accumulator (`bl_acc`…`bl_done`, D-LNBLANK R5 intact),
re-entered from `tk_loop` and returning there.

| site | change |
|---|---|
| `tokenise:` | clear `TKLNUM` alongside `TKNAME`/`TKOVF` |
| `tk_loop` digit arm | `TKLNUM` live → `jp bl_num` instead of `jp tk_float` |
| `tk_nondigit` `.` arm | `TKLNUM` live → `jp tk_copy` instead of `jp tk_float` (R-L2) |
| `match_kw` success | clear `TKLNUM` (`push af` / `pop af` — A carries the token byte) |
| `branch_lineno` / `bl_yes` | the six `cp`s remain; `bl_yes` becomes *set `TKLNUM`, ret* |
| `tk_copy_up` | clear `TKLNUM` (a name letter) |
| `tk_print_q` | clear `TKLNUM` (`?` → `$91`) |
| `tk_underscore` | clear `TKLNUM` (`_` → CALL) — see §4 |
| `tk_copy` | clear `TKLNUM` when the copied character is `:` |
| `bl_num` | entered from `tk_loop`; the digit gate, comma test and `bl_list` deleted; `bl_done` ends `jp tk_loop` |

**Measured +26 B net** in the sub-ROM (hooks against the deleted list-walking),
from the uniform address shift of every symbol downstream of the tokeniser.

⚠️ **The `match_kw` clear goes at the MATCH SITE, not inside `branch_lineno`.**
`REM`, `DATA` and `CALL` are dispatched *before* `branch_lineno` is called
([`basic/tokenise.inc`](../basic/tokenise.inc) `tk_nondot`), so a clear inside
`branch_lineno` would leave the mode armed through `CALL` and move `lnl-callpar` —
a cell that is green on all three sides today. Knife **K3** aims at exactly this.

⚠️ **`tk_copy`'s new `:` test must not clobber `A`.** `tk_copy` is the
**fallthrough** target of the `is_letter` test, and D-NAMBLANK's K2 is the
standing record of what a careless store there costs (a build that read 29/31
green *by luck*). The test goes **after** the copy, on the character already in
`A`, and the clear reloads nothing.

## 4. Scope — `CALL`/`_`, measured after the first sign-off

**`CALL` and `_` clear the mode. MEASURED, not assumed.**

Three rows tried and failed first: `lnl-under`, `lnl-call` and `lnl-callp` all
had their digit eaten by the CALL device-name scan before it could reach a
numeric path — the reference stores `_X 5` and `<CA> X5`, keeping the digit as
**verbatim ASCII**, and for `CALL X+5` it dropped the `+` outright. Three rows,
three times the same confound.

The way past it was a different **terminator**, not a different operator: `(`
ends an extended statement's name, and round 3 pins that `(` on its own leaves
the mode *armed* (`lnl-paren`). So:

```
lnl-callpar^   20 IF A THEN CALL X(5)   <8B> A <DA> <CA> X(<16>)
lnl-underpar^  20 IF A THEN _X(5)       <8B> A <DA> _X(<16>)
```

`<16>`, not `$0E,0005` — the `CALL` token cleared it. Both references, both rows,
`--repeat 2`. zerobas already agrees, so these are two-sided controls **and** the
cells that pin *where* the clear belongs: `CALL` bypasses `branch_lineno`
entirely, so a clear placed inside it would leave `lnl-callpar` armed. Knife
**K3** aims there.

**The CALL device-name divergence is a SEPARATE defect** — zerobas' name scan
stops where the reference's does not — and it earns its own `TODO.md` item with
these bytes attached. Folding it in here would be the
[D-MFDOM](maxfiles-domain-slice.md) trap. Likewise `LIST`/`DELETE`/`AUTO`/
`RENUM`/`ELSE`, already filed.

## 5. Rows

**Divergent today, must agree after (27):** `lnl-plus` `lnl-minus` `lnl-star`
`lnl-semi` `lnl-hash` `lnl-paren` `lnl-three` `lnl-colon` `lnl-blkl` `lnl-blkr`
`lnl-blk2` `lnl-lead` `lnl-bare` `lnl-gosub` `lnl-then` `lnl-restore` `lnl-run`
`lnl-resume` `lnl-on1` `lnl-on2` `lnl-qtail` `lnl-slash` `lnl-pow` `lnl-idiv`
`lnl-eq` `lnl-lt` `lnl-gt` — **plus `dot-goto`**, whose `KNOWN_DIVERGE` entry is
**retired** (the gate goes red until it is deleted; that is the mechanism).

**MUST NOT MOVE — green on all three sides today (19 in this battery):**
`lnl-ctl` `lnl-nokw` `lnl-colctl` `lnl-alpha` `lnl-thenpr` `lnl-kw` `lnl-fnkw`
`lnl-name` `lnl-namemid` `lnl-colsep` `lnl-or` `lnl-mod` `lnl-quest` `lnl-apos`
`lnl-hex` `lnl-empty` `lnl-empty2` `lnl-callpar` `lnl-underpar`.
**Plus the whole `ref` battery** (`ref-ctl` `ref-sp` `ref-goto` `ref-gosub`
`ref-then` `ref-restore` `ref-run` `ref-resume` `ref-onlist` `ref-oncomma`),
D-NAMDOT's `dot-*` rows and D-DECBLANK's `dec-dot*` cohort.

**Stays divergent, filed separately:** `lnl-under` `lnl-call` `lnl-callp` (the
CALL name scan, §4) — pinned as `KNOWN_DIVERGE` so they cannot rot.
`ref-list`/`ref-delete`/`ref-auto`/`ref-renum`/`ref-else` stay informational.

⚠️ **`lnl-empty` / `lnl-empty2` are the trap-parser guard.** `ON KEY GOSUB` and
`ON STRIG GOSUB` walk the crunched list looking for `$0E`; `bl_num`'s own comment
records the parsers running off the end of their list when the count was wrong.
This change deletes the empty-slot special case that comment describes — the
ordinary `tk_loop` copy handles `,,` now — so those two rows and the `traps`
gates are what say the deletion was safe.

## 6. Gates

`make lnblank-acceptance` — three sides, `--repeat 2`: **195/195 gating rows
agree**, 3 of them allowlisted as `KNOWN_DIVERGE` (the CALL device-name rows, §4)
and pinned to zerobas' exact **pre-fix** bytes, so they also witness that
this change did not move them. Up from **163/193** before the fix, with
`dot-goto` retired from the allowlist — the gate reported it as
*"allowlisted as divergent but the row now AGREES — retire the entry"*, which is
the mechanism working, not a failure.

✅ **Superseded 2026-08-01 by D-CNAME** ([`spec-basic-cname.md`](spec-basic-cname.md)):
the three CALL device-name rows were retired the same way — the allowlist
reported all three as AGREEING — and the gate now reads **251/251 with an EMPTY
allowlist**. ⚠️ The rule those rows suggested was refuted: the scan discards
`$21..$2F`, **keeps** `; < = > ? @ [ \ ] ^ _ ` ~` verbatim, and ends only at
EOL / `:` / `(`.

Full corpus after the change, all run: `unit-test` **ALL 55 PASSED** ·
`badfnum` **93 cases, 0 unfiled divergence** · `lof` **45 cases, 0 drift** ·
`chancost-characterize` · `diskbasic` **34/34** · `bdos` **12/12** ·
`fat-error` **ALL PASS** · `error-trap` **ALL PASS** · `abort` **49/49** ·
`stop-trap` **ALL PASS** · `linemax` **60/60** · `arrdim` **73/73** ·
`clearpool` **52/52** · `array` **149/151** (the two standing rows confirmed
**by name**: `ifc.instr.zero`, `ifc.instr.neg` — the case-only wording artifact).

⚠️ **The trap gates are the ones that read `$0E`, and they were run:**
`strig-trap-acceptance` and `key-trap-acceptance` both **ALL PASS**. This change
deletes the empty-slot special case `bl_num`'s comment records, so those two
gates plus `lnl-empty`/`lnl-empty2` are what say the deletion was safe rather
than merely green-looking.

**Split assertion — VERIFIED.** `build/basic-reloc.rom` is still
`1d270536f1bd26acbe947f2da7af93fce51d6c6f2d69d36391d1c9e59c51d9c7` and
`build/zerobas-main-eu.rom` still
`90403dbb1022c5caa241c2b965f0abe2327788279150b8c5a299f7420142a91e` —
byte-identical to HEAD. Only `build/sub.rom` moved: **net +26 B**, measured as
the uniform shift of the 607 symbols downstream of the tokeniser (`bl_list`
removed, `TKLNUM` added). Dead-code gate **0 dead in both builds**.

## 7. Knives — seven, ALL RUN and reverted, each with a RED set **and**
surviving GREEN controls

Every knife changed a constant or removed one clear; none orphaned a block (the
hard dead-code gate read **0 dead in both builds** on all seven). Scoped
`SIDES=vg8020,zb`.

| # | cut | RED (measured) | GREEN survivors |
|---|---|---|---|
| **K1** | `bl_yes` arms with `0` — no mode at all | **52 rows**: the whole `ref` battery, every `lnl` row carrying a branch keyword, `dot-goto`, and `dec-eref` | `lnl-nokw`, the `dot-*`/`dec-dot*`/`nam-*` cohorts, and the three allowlisted CALL rows **still matching their pinned values** |
| **K2** | `tk_copy`'s `cp COLON` → `cp ';'` | `lnl-colsep`, and `lnl-semi` **inverted** (its `;` now clears) | `lnl-hash` `lnl-paren` — and see below |
| **K3** | drop the `match_kw` clear | `lnl-thenpr` `lnl-kw` `lnl-fnkw` `lnl-or` `lnl-mod` `lnl-callpar` | `lnl-name` `lnl-namemid` `lnl-quest` `lnl-underpar` — cleared elsewhere |
| **K4** | drop the `tk_copy_up` clear | `lnl-name` `lnl-namemid` | `lnl-alpha` — `1X5`'s `5` continues the **name**, so the name state wins whatever the mode says |
| **K5** | drop the `tk_print_q` clear | `lnl-quest` alone | `lnl-thenpr` — the spelled-out `PRINT` clears via `match_kw` |
| **K6** | drop R-L2's `.` suppression | `lnl-lead` `lnl-bare` `lnl-three` `dot-goto` | `lnl-plus` `lnl-semi` — the mode still runs, only the `.` arm changed |
| **K7** | drop the `tk_underscore` clear | `lnl-underpar` alone | `lnl-callpar` — the spelled-out `CALL` clears via `match_kw` |

K3–K7 matched their predictions **exactly**. Two did not, and both corrections
are findings rather than bookkeeping:

### 7.1 K1's RED set is WIDER than this spec first claimed

It was written as *"the 27 rows and the whole `ref` battery"*. With the mode never
armed, the **first** number after a branch keyword loses its `$0E` too, so rows
listed here as MUST-NOT-MOVE (`lnl-ctl` `lnl-colctl` `lnl-kw` `lnl-or` `lnl-mod`
`lnl-empty` `lnl-empty2` `lnl-alpha` …) go red as well — they are must-not-move
against *this change*, not against deleting the whole feature. `dec-eref`
(`20 GOTO 1EX`, a `dec` row that happens to carry a branch keyword) went red for
the same reason and is a free extra witness that the cut removed the feature and
not a corner of it.

### 7.2 🔴 K2 INDEPENDENTLY REPRODUCED THE `lnl-colon` CONFOUND

K2 was predicted to redden `lnl-colon` and `lnl-colctl` along with `lnl-colsep`.
**It did not** — both stayed green with the colon clear broken. That is not a
wrong fix; it is the same confound §2 of the characterization already records,
arriving a second time by a different route: their payloads are
`GOTO 1.5:A=7` / `GOTO 1:A=7`, and the `A` behind the colon is a **name**, which
disarms the mode on its own. The two rows cannot measure `:` no matter what is
done to the colon test, and `lnl-colsep` (`20 GOTO 1:5`) is the only row in the
probe that can.

⚠️ **A knife is a THIRD rule** ([[knife-is-a-third-rule]]): a `^` row moving under
one is usually a wrong prediction, not a broken fix. The genuinely alarming case
is a knife reddening a row whose payload **does not contain the subject at all**
— that is a defect report about the fix itself. None of the seven did.
