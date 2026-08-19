<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-KWGAP4 — `DELETE` / `AUTO` / `RENUM` / `LLIST`: the token AND the arm, together

Measurement:
[`docs/kwgap4-msx1-characterization.md`](kwgap4-msx1-characterization.md) — the
crunch half is D-LNREF's 162-word oracle lock
([`lnref-msx1-characterization.md`](lnref-msx1-characterization.md) §1/§4), the
run-time half is ten new rows measured here. Two references
(Philips VG-8020, National CF-3300) agreeing, `--repeat 2`, every payload past
the echo guard on every side it is allowed on.

Neighbours whose cells this must not move: D-LNREF
([`spec-basic-lnref.md`](spec-basic-lnref.md) **R-R1/R-R2/R-V**), D-LNLIST
(**R-L1/R-L2/R-L3**), D-LNBLANK (**R4/R5**), D-EXPKW, D-CNAME, D-NAMDOT.

---

## 1. The item is TWO problems and this slice closes ONE of them, completely

`TODO.md` files *"`DELETE`/`AUTO`/`RENUM`/`LLIST` have no token — and whoever
adds them must add the arming byte too."* That is exactly right, and it is one
half of the surface:

* **the CRUNCH half** — four `kwtable.inc` entries and four `branch_lineno`
  arms, after which the stored bytes are the reference's, byte for byte. **This
  slice.**
* **the STATEMENT half** — `DELETE <range>`, `AUTO <start>,<inc>`,
  `RENUM <new>,<old>,<inc>`, `LLIST`, four real MSX BASIC verbs that zerobas
  does not execute. **Filed with its numbers (§3.4), not implemented.**

🔴 **THE TWO HALVES CANNOT BE SWAPPED IN ORDER, AND THE ARM IS WHY.** All four
words **arm line-number mode on the reference**, and `branch_lineno` deliberately
carries no test for their tokens because no row could exercise one today. Adding
the `kwtable.inc` entry *alone* turns every crunch row for these four from *"no
token"* into *"token, WRONG ARGUMENT"* and brings D-LNREF's defect back for four
verbs. The seven `KNOWN_DIVERGE` pins D-LNREF spent its empty allowlist on exist
to make that impossible to do quietly (§5).

## 2. The rules

* **R-K1 (the four entries)** — `DELETE` `AUTO` `RENUM` `LLIST` are reserved
  words crunching to the single statement tokens **`$A8` `$A9` `$AA` `$9E`**
  (oracle-locked, [`lnref-msx1-characterization.md`](lnref-msx1-characterization.md) §4).

  ⚠️ **Table position is free for all four, and that was WALKED, not assumed.**
  `match_kw` stops at the first entry that matches and does no longest-match and
  no word-boundary check — the reason `DEFINT` must precede `DEF`. All **137**
  existing entries were checked in both directions: none is a prefix of any of
  the four, and none of the four is a prefix of an existing entry
  ([characterization §2](kwgap4-msx1-characterization.md#2--the-four-words-collide-with-nothing-in-either-direction)).
  The near-misses stay near-misses: `DEF` diverges from `DELETE` at char 3,
  `REM` from `RENUM` at char 3, `LIST` from `LLIST` at char 2 — which is also
  exactly why today's mangles are `DE`+`LET`+`E`, `AU`+`TO` and `L`+`LIST`.

* **R-K2 (the four arms)** — crunching any of the four **arms line-number mode**,
  joining the fourteen-word list D-LNREF measured (**R-R1**). This is not a new
  rule; it is the four members of R-R1's list that R-R1 could not yet express.

  🔴 **It stays a `cp` chain and does NOT become a range, even though `$A7..$AA`
  now looks like one.** `RESUME` `DELETE` `AUTO` `RENUM` really are four
  consecutive arming tokens, and a two-test range would replace 16 B with 8 B.
  It is refused: D-LNREF measured the arming set over the whole 162-word
  denominator and found it is a **LIST** with a non-arming neighbour on at least
  one side of every boundary (`ERROR $A6` below `RESUME $A7`, `DEFSTR $AB` above
  `RENUM $AA`, `IF $8B` sitting *between* four arming tokens). A range here would
  express a rule the walk refutes, and would silently arm any byte later added
  in the span. **Sub page 0 is not the wall** (§3.3); the 8 B buy nothing.

* **R-K3 (the statement stays undispatched, and the class is MEASURED)** — none
  of the four gets a `stmt_table` row, so `exec_stmt`'s table search falls
  through to `es_noentry`, whose `is_letter` test fails on a `$80`-range token
  and lands on `stmt_error` → **ERR 2, Syntax error**.

  🔴 **All four already read ERR 2 today, by four DIFFERENT accidental parses,
  and that had to be measured rather than reasoned** (characterization §3.3).
  The hazard the TODO item named — a token turning a working garbage parse into
  a new error class — is real in general and **empty for these four**. The
  `kwgz` battery is the before/after that says so.

## 3. The change

### 3.1 `basic/sysvars.inc` — four equates, **0 B**

`DELETE_TOKEN $A8`, `AUTO_TOKEN $A9`, `RENUM_TOKEN $AA`, `LLIST_TOKEN $9E`,
sited with the other statement tokens. None of the four bytes is currently
equated to anything in either namespace, so there is no `TRON`/`STICK`-style
collision to keep apart ([[two-namespaces-sharing-a-value]]).

### 3.2 `basic/kwtable.inc` — four entries, **+32 B**, sub-ROM page 0

```
db      6,"DELETE",1,DELETE_TOKEN     ; 9 B
db      4,"AUTO",1,AUTO_TOKEN         ; 7 B
db      5,"RENUM",1,RENUM_TOKEN       ; 8 B
db      5,"LLIST",1,LLIST_TOKEN       ; 8 B
```

⚠️ **This is a SUB-ROM change and the main ROM must not move a byte.**
`kwtable.inc` is `include`d by [`sub/sub.asm:299`](../sub/sub.asm:299) **and
nothing else** — the resident copy was dropped in the sub-ROM arc's wave 3, and
`tools/check_kwtable_identity.py` asserts single-copy on every build. Both
directions are data-driven off that one table (`match_kw` crunches, `detok_kw`
detokenises), so the four entries also fix the `LIST` round-trip for free.

### 3.3 `basic/tokenise.inc` — four arms, **+16 B**, sub-ROM page 0

Four `cp`/`jr z,bl_yes` pairs appended to `branch_lineno`'s existing ten-test
chain, replacing the comment that says they are deliberately absent.

**Total sub page 0: 3958 B free → 3910 B, NET +48 B.** Main ROM low **9 B** and
main page 1 **6 B** are **untouched** — asserted by hashing
`build/basic-reloc.rom` before and after (§6).

### 3.4 What this change does NOT do

* **The four STATEMENTS stay unimplemented, and the numbers are why.**
  `stmt_table` is at **`$40AF` — main ROM page 1**, at 3 B per entry. **Four
  dispatch rows are 12 B against 6 B free**: the table rows alone do not fit,
  before one byte of handler.

  🎯 **Knife K5 MEASURED that 3 B rather than leaving it computed.** Adding one
  `stmt_table` row took main page 1 from **6 B free to 3 B**. The scope decision
  therefore rests on a reading, not on counting bytes in a table layout — and
  the same knife showed the row changes no behaviour, which is R-K3. Low (9 B) is co-mapped with page 1 and therefore
  coupled, so it is not relief. `RENUM` needs a two-pass old→new map over every
  line number *and* every `$0E` reference including `ON..GOTO` lists; `AUTO` must
  drive the line editor, a sub-ROM page-1 tenant, from a main-ROM statement;
  `LLIST` is the cheapest (a printer sink exists at
  [`basic/print.asm:401`](../basic/print.asm:401)) and would still inherit the
  filed `ex_list`-ignores-its-argument defect. **Each is a slice, none is a table
  edit.** `kwgd-delete` and `kwgd-renum` are pinned so the day one lands, the
  gate says so.
* **`LIST <range>` is not touched.** `lnrd-list` is the must-not-move cell.
* **`RETURN <line>` and the other 20 tokenless words stay filed.** (`DEFINT`'s
  bytes, named here alongside them at the time this spec was written, are FIXED
  separately — D-DEFINTTOK, 2026-08-18, and the other three verbs the next day,
  D-DEFTYPETOK; `lnref-msx1-characterization.md` §4;
  its `lnr-defint` probe row graduated out of `basic_probe_lnblank.py`'s
  `INFORMATIONAL` set the same way `lnrx-lprint`/`-lpos`/`-lfiles` did below.
  The K3/K4 knife log further down this file is a historical measurement and is
  left as recorded — but note before re-running K4 that `$AB` is no longer a
  spare byte: D-DEFTYPETOK made it `DEFSTR_TOKEN`, so that cut now collides with
  a live token rather than an unused one.) `lnrx-lprint` and `lnrx-wait` are named in §4 as the controls that say
  four entries were added and not five.

## 4. Rows

**Divergent today, must AGREE after (10):**

| row | typed | both references | zerobas today |
|---|---|---|---|
| `lnrx-delete` | `20 DELETE 10` | `<A8> <0E><0A><00>` | `DE<88>E 10` |
| `lnrx-auto` | `20 AUTO 10` | `<A9> <0E><0A><00>` | `AU<D9> <0F><0A>` |
| `lnrx-renum` | `20 RENUM 10` | `<AA> <0E><0A><00>` | `RENUM 10` |
| `lnrx-llist` | `20 LLIST 10` | `<9E> <0E><0A><00>` | `L<93> <0E><0A><00>` |
| `ref-delete` | `20 DELETE 1 0` | `<A8> <0E><0A><00>` | `DE<88>E 1 0` |
| `ref-auto` | `20 AUTO 1 0` | `<A9> <0E><0A><00>` | `AU<D9> <0F><0A>` |
| `ref-renum` | `20 RENUM 1 0` | `<AA> <0E><0A><00>` | `RENUM 1 0` |
| `lna-delrng` | `20 DELETE 10-20` | `<A8> <0E><0A><00><F2><0E><14><00>` | `DE<88>E 10<F2><0F><14>` |
| `lna-auto2` | `20 AUTO 10,5` | `<A9> <0E><0A><00>,<0E><05><00>` | `AU<D9> <0F><0A>,<16>` |
| `lna-renum3` | `20 RENUM 10,20,30` | `<AA> <0E><0A><00>,<0E><14><00>,<0E><1E><00>` | `RENUM 10,<0F><14>,<0F><1E>` |

The first seven **retire their `KNOWN_DIVERGE` pins**; the last three **leave
`INFORMATIONAL`** and become ordinary gating rows — their attribution argument
(*"they would still diverge with the `$0E` arm perfect"*) is exactly what this
slice removes.

🔴 **`ref-*` carry a SECOND rule and they are the reason the argument is not
half-fixed.** They type `1 0` — a blank *inside* the number — so they only agree
if D-LNBLANK **R5**'s blank rule runs *inside* the newly armed mode. A row that
agreed on `10` and diverged on `1 0` would say the arm landed and the mode did
not reach the digit scan.

**New, three-sided, say mode (5):** `kwgd-ctl` `kwgd-delctl` `kwgd-renctl` are
green before and after; **`kwgd-delete` (` 1  0 ` vs ` 2  2 `) and `kwgd-renum`
(` 2  0 ` vs ` 0  8 `) stay divergent and are PINNED** — they are the STATEMENT
half, and the pin is what makes §3.4's "filed, not fixed" a measurement.

**New, zerobas-side only, NO GATE (5):** `kwgz-ctl` `kwgz-delete` `kwgz-auto`
`kwgz-renum` `kwgz-llist`. `AUTO` and `LLIST` hang a reference (§5.1), so these
carry no oracle lock and gate nothing; they are the before/after of R-K3 and
they say so out loud.

**MUST NOT MOVE — and three of them are load-bearing:**

* 🔴 **`lnrx-lprint` (`20 LPRINT 10` → zb `L<91> <0F><0A>`) is the control for the
  `LLIST` entry.** It is the *identical shape* — a stray `L` plus a genuine
  keyword token — and `LPRINT` does **not** arm on the reference. If the `LLIST`
  entry were matched at the wrong position, or if a fifth entry crept in, this
  row moves. It must **still diverge**, in exactly the way it does today.
* 🔴 **`lnrx-wait` (`20 WAIT 10` → zb `WAIT 10` verbatim) is the control for the
  `RENUM` entry** — the other tokenless word that stores its name verbatim. It
  must still diverge; agreement here would mean entries were added that this
  spec does not authorise.
* **`lnrd-list`** — `ex_list` still ignores its argument; ` 1  0 ` on all three
  sides, before and after.
* the other **133** `lnr` rows, `lnr-list` (`LIST` still arms), all `lnv`/`lnv2`
  rows (R-V untouched), `lnl`, and the whole standing `ref`/`dot`/`dec`/`nam`/
  `exp`/`cnm` corpus.

**Still informational after:** the `INFORMATIONAL` set holds **24** labels, of
which **23 are reported divergent** by the gate (`num-tab` is in the set and
agrees). Of the 24, **21 are this surface's** — the 20 remaining `lnrx` rows plus
`lnr-defint`; the other three (`num-tab`, `dec-eol`, `dec-eolctl`) belong to
earlier slices. Down from 24 on this surface: `lna-renum3`/`-auto2`/`-delrng`
left. 🔴 **`lnrx-lprint` and `lnrx-wait` are both in the reported-divergent list,
which is where they have to be** — see the must-not-move rows above.

## 5. The pins: seven retire, two arrive, and the allowlist goes back to EMPTY

D-LNREF spent a five-cohort empty `KNOWN_DIVERGE` to buy a trip-wire against
exactly this slice. It fires as designed: the moment the four tokens land, the
seven pinned rows stop diverging in the pinned way and the gate goes red until
the entries are **deleted**.

⚠️ **They are DELETED, not edited.** Editing a pin to match the new value is how
an allowlist rots; deleting it is the retirement the pin was bought for. This is
the **sixth** cohort to leave that way (five `lit-`, four `dec-expbad*`, two
`nam-dot`, one `dot-goto`, three `lnl-`, now seven `lnrx`/`ref`), and none has
rotted.

**`lnblank-acceptance`'s allowlist returns to EMPTY.** The two new pins
(`kwgd-delete`, `kwgd-renum`) live in the **say** gate beside `lnrd-return`, each
with one named retirement path: implement the statement.

### 5.1 The side lock is part of the measurement

`kwgz-auto` and `kwgz-llist` cannot be put to a reference: `AUTO` enters
interactive line-entry, `LLIST` drives an unplugged `LPTOUT`, and `omsx_repl`
raises `SystemExit` at its 240 s cap — one such row does not degrade a run, it
kills it. Both are already `crunch-only` in the keyword sweep for these reasons.

`SIDE_LOCK` names them zerobas-only in the probe itself. A run that names them
explicitly with the wrong sides **fails** with the reason; a broad run
(`lnblank-echo`, which sees every row) **skips them with a printed notice**.
Silently dropping them would have let `--sides vg8020,cf3300,zb --only kwgz-`
read as a clean run.

## 6. Gates

Full corpus, **run after the change — every line below is a reading**:

`make unit-test` **55/55** · dead-code gate **0 dead both builds** (main 1572
spans/265 seeds, sub 1384/98, +1 allowlisted and still verified dead) ·
**`lnblank-acceptance` `REPEAT=2` — 521/521** (518 + the three `lna` rows that
left `INFORMATIONAL`), **allowlist EMPTY**, 23 informational rows reported ·
**`lnblank-say-acceptance` `REPEAT=2` — 12/12** (`ONLY` widened from `lnrd-` to
`lnrd-,kwgd-`), 3 pinned ·
**`lnblank-echo` — "every gating payload typed verbatim on every side", and it
covers the `--say` payloads for the FIRST time** (characterization §5): all 7
`lnrd`, 5 `kwgd` and the `err`/`dir`/`dotd`/`lnld`/`cnmd` rows read `ECHOED` on
all three sides; the 5 `kwgz` rows are skipped with the printed side-lock notice;
the only `MANGLED` rows are the three pre-existing informational ones
(`num-tab`'s literal TAB, `dec-eol`/`dec-eolctl`'s trailing blank — the machine
transforms them, which is a reading, not a fault) ·
`logicops-acceptance` **193/193** · `float-acceptance` **ALL PASS** ·
`array-acceptance` **149/151** (`ifc.instr.zero`, `ifc.instr.neg` — confirmed by
name, the case-only wording artifact) ·
`arrdim` **73/73** · `clearpool` **52/52** · `badfnum` **93 cases, 0 drift, 0
unfiled divergence** · `lof` **45 cases, 0 drift** · `chancost-characterize`
**53 cases, 0 filed divergences** · `diskbasic` **34/34** · `bdos` **12/12** ·
`fat-error` **8/8** · `error-trap` **ALL PASS** · `abort` **49/49** ·
`stop-trap` / `strig-trap` / `key-trap` **ALL PASS** · `linemax` **60/60** ·
`sysvarsweep` **exit 0, apparatus OK**, C-REPRO / C-PRIV / C-REPRO-2 / C-VACATED
all green.

⚠️ **Standing and NOT caused by this slice:** `tools/audit_citations.py` still
reports its 2 gating findings (`basic/fat.asm`, `basic/missing.asm`) — verified
unchanged against HEAD.

⚠️ **`strig-trap` and `key-trap` are named for D-LNLIST's reason** — they are the
gates that PARSE `$0E`, and this slice adds three more verbs that can produce
one.

**Split assertion — the main ROM is BYTE-IDENTICAL, ASSERTED not recorded.** This
is a sub-ROM-only change, so unlike D-LNREF there is a hard equality here, and it
held on a clean `rm -rf build` rebuild:

| image | HEAD `cb6ae68` | after | verdict |
|---|---|---|---|
| `build/basic-reloc.rom` | `23068e7a…` | `23068e7a…` | ✅ **IDENTICAL** |
| `build/zerobas-main-eu.rom` | `1866a835…` | `1866a835…` | ✅ **IDENTICAL** |
| `build/sub.rom` | `cc67d0e4…` | `8199b931…` | moves, **+48 B** |

**Walls: low 9 B → 9 B; main page 1 6 B → 6 B; sub page 0 3958 B → 3910 B.**
`kwtable` grew 1009 → 1041 B and `tools/check_kwtable_identity.py` still reports
it single-copy with the sub-ROM as sole source.

⚠️ **`zerobas-main-eu.ips`/`.bps` are unchanged too**, since the merged main ROM
is — the shipped BASIC deliverable does not move for this slice.

## 7. Knives — each with a predicted RED set **and** predicted GREEN survivors

⚠️ **Reverted against the BUILD EACH ONE CUT, never `git checkout`** — that
restores HEAD, which is the *unfixed* tree, and silently reverts the slice
([`spec-basic-lnref.md`](spec-basic-lnref.md) §7.0). The runner copies the
pre-knife sources first and verifies each restore by rebuilding to a
byte-identical ROM.

### 7.0 🔴 The runner's OWN restore check was broken, in both directions

Two apparatus faults, both in the verification rather than in the cuts, and both
worth recording because each one *looked like* a result:

* **Every restore reported `RESTORE FAILED`, and every restore was fine.**
  `shutil.copy2` **preserves mtime**, so a restored source looked *older* than
  `build/sub.rom`, `make` skipped the rebuild, and the check compared the stale
  **knifed** ROM against the pre-knife hash. Six false alarms in a row. The cuts
  themselves were unaffected — writing a knife touches the file, so those builds
  were real — but a verification that cannot see its own subject verifies
  nothing. Fixed (`copy` + `os.utime`), and the tree was then rebuilt from clean
  to the exact pre-knife `sub.rom` (`8199b931…`) with both main ROMs
  byte-identical to HEAD, which is what actually says the restores were sound.
* **K5's landing check watched the wrong ROM.** K5 cuts `basic/interp.asm`, a
  **main-ROM** file, so `sub.rom` is unchanged *by design* — and the runner's
  "did the cut land?" guard hashes `sub.rom` only. It reported
  `APPARATUS FAILURE: the knifed ROM is IDENTICAL`. K5 was re-run with the
  landing check on `basic-reloc.rom`, where the cut is visible.

⚠️ **The second one is the dangerous shape.** A green K5 whose cut had silently
not landed would have "confirmed" R-K3 while measuring nothing — the
[[gate-can-be-green-while-measuring-nothing]] pattern, arriving through a guard
that was itself pointed at the wrong artifact.

Gating denominator for K1–K4/K6 is **13** rows (16 selected, minus the three
standing informational ones — `lnr-defint`, `lnrx-lprint`, `lnrx-wait`); for K5
it is the 12-row say gate.

| # | cut | predicted RED | measured | predicted GREEN survivors |
|---|---|---|---|---|
| **K1** ✅ | drop the `DELETE_TOKEN` arm, keep its `kwtable` entry | `lnrx-delete` `ref-delete` `lna-delrng` — the token lands, the argument does not | **matched exactly, 10/13**, all three reading `<A8> <0F><0A>` (and `lna-delrng` `<A8> <0F><0A><F2><0F><14>`) | `lnrx-auto` `lnrx-renum` `lnrx-llist` and their `ref`/`lna` rows: three independent arms untouched. 🔴 **This is the precise failure the seven pins were bought to catch — token right, argument wrong — reproduced on demand** |
| **K2** ✅ | drop the `LLIST` `kwtable` entry, keep its arm | `lnrx-llist` only | **matched, 12/13** — and it falls back to *exactly* the pre-slice mangle `L<93> <0E><0A><00>`, the value the pin carried | `lnrx-lprint` stays divergent in its current way (`L<91> <0F><0A>`, unchanged), `lnrx-delete`/`-auto`/`-renum` stay green. Isolates entry from arm in the one row whose argument is already accidentally right |
| **K3** ✅ | place the `LLIST` entry **before** `LIST` instead of after | *neither* — predicted **no RED at all** | **matched, 13/13** | every row, both ways. ⚠️ A predicted-GREEN knife is worth running only because the DEFINT/DEF note proves order is *sometimes* load-bearing; this is where the two cases are told apart, and R-K1's "order is free" is a measurement rather than a reading of `match_kw` |
| **K4** ✅ | `RENUM_TOKEN` `$AA` → `$AB` (`DEFSTR`'s byte) | `lnrx-renum` `ref-renum` `lna-renum3` | **matched exactly, 10/13**, all three emitting `<AB>` | `lnr-defint` **did not move** (`<97>INT <0F><0A>`) — `DEFINT` emits `DEF_TOKEN`+`"INT"` and never `$AB`, so the `DEF`-family collision this knife aims at is a *detokeniser* hazard, not a crunch one. Brackets R-K1's value from a neighbour that is spoken for |
| **K5** ✅ | add a `stmt_table` row for `DELETE_TOKEN` → `stmt_error` | *nothing* — R-K3 says the fall-through already lands there | **matched: 12/12 say gate, 3 pinned, and `kwgz` unchanged** — identical to the unknifed build | ⚠️ **This knife aims at the JUSTIFICATION, not the code.** Had anything moved, R-K3's account of `es_noentry` would be wrong and "ERR 2 before and after" would have been luck. ⚠️ It is a MAIN-ROM cut, so `sub.rom` is unchanged *by design* — the landing check is `basic-reloc.rom` changing, and the first run's sub-only guard fired a false alarm on exactly that |
| **K6** ✅ | collapse `$A7..$AA` into the range test R-K2 refuses | *nothing in this corpus* | **matched, 13/13** | ⚠️ **The green result is the finding.** This corpus cannot tell a list from a range here, so the chain is kept on the 162-word WALK's evidence and not on a red row — and a range would silently arm any byte later added inside the span |

---

## 8. Sign-off — answered 2026-08-01

1. **Tokens only, statements filed** (§3.4) — **agreed**. Four dispatch rows are
   12 B against 6 B free on main page 1, before any handler; knife K5 measured
   the 3 B/row directly.
2. **The `kwgz` battery gates nothing and says so** (§5.1) — **agreed**. The
   alternative was no run-time reading at all for `AUTO`/`LLIST`.
3. **`lnblank-say-acceptance`'s default widens to `lnrd-,kwgd-`** (§6) —
   **agreed**, putting the two new pins under a gate rather than leaving them
   dormant.
