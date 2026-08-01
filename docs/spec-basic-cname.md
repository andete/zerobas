# D-CNAME — the `CALL` device-name scan is a RANGE test, not an identifier scan

*Spec. Measurement: [`docs/cname-msx1-characterization.md`](cname-msx1-characterization.md).
Filed by D-LNLIST ([`docs/spec-basic-lnlist.md`](spec-basic-lnlist.md) §4), which
hit it three times and deliberately did not fix it.*

**Status: LANDED 2026-08-01.** `lnblank-acceptance` **251/251** at `--repeat 2`
across `vg8020`/`cf3300`/`zb`, 0 `UNSTABLE`, **allowlist EMPTY**. **NET −10 B, all
sub-ROM page 0** (3998 → 4008 B free); both main ROMs **byte-identical** to the
parent commit, asserted by hash. Seven knives run and reverted (§7).

---

## 1. The rules

> **R-C1 (terminate)** — the device-name scan ends at **end of line**, at **`:`**
> (`$3A`) or at **`(`** (`$28`). Nothing else ends it. The terminator is left in
> place for the ordinary crunch, which is why `CALL X(5)` stores the `(` and
> crunches the `5`, and why `CALL X:PRINT 5` has a second statement at all.
>
> **R-C2 (discard)** — inside the scan a character in **`$21`..`$2F`** is
> **discarded**: not stored, and the scan continues past it. Fourteen characters
> (`$28` is R-C1's `(`), walked contiguously — the range is a denominator.
>
> **R-C3 (store)** — every other character is **stored**: `a`..`z` upcased,
> everything else verbatim, **including the blank** (`$20`). No keyword crunch,
> no numeric crunch, no length bound.

Equivalently, once end-of-line, `:` and `(` are taken out: **a character is
discarded iff `' ' < c < '0'`.**

`_` takes the identical scan (characterization §5), and `_` itself (`$5F`) is an
ordinary *stored* character inside one — it is only the CALL abbreviation at the
point where a statement begins.

---

## 2. ⚠️ The filed framing is REFUTED — twice over

`TODO.md` states the scan *"stops short — the reference reaches further"* and
gives two facts: the blank is crossed, and the `+` is *"dropped outright"*. Both
readings are correct. **The rule they suggest is not.**

The obvious rule from those two rows — *copy identifier characters and blanks,
drop everything else* (rule **S**) — is **refuted**: `; < = > ? @ [ \ ] ^ _`
`` ` `` `~` are all **kept**, verbatim, and the scan runs on past them. The
narrower rule *only `+` is swallowed* (rule **P**) is refuted the other way:
thirteen more characters are dropped.

🔴 **AND THE OPERATORS LAND ON BOTH SIDES.** `+ - * /` are dropped; `^ \ = < >`
are kept. Nine operators, split down the middle, so no property of *operator-ness*
or of the token byte explains it — the same interleaving shape D-LNLIST hit,
where `\` (`$FC`) kept the mode and `MOD` (`$FB`) cleared it. What separates them
is the **ASCII range**, which only a contiguous walk could show. **Three rows
could not have found this rule, and each of the three agrees with S and with P.**

This is the fourth consecutive slice where the filed title named the wrong
subject (D-NAMBLANK under `&B`, D-LNBLANK, D-LNLIST under `.`), and the second
where the *direction* was right and the *rule* was wrong.

---

## 3. The change

[`basic/tokenise.inc:302`](../basic/tokenise.inc:302). `tk_call_name` and
`tcn_name` collapse into **one loop** — the two-phase "blanks first, then a name"
shape was itself the bug, since blanks are not a prologue but an ordinary stored
character (`cnm-blk2`, `cnm-twoword`).

```
tk_call_name:
                ld      a,(hl)
                or      a
                jp      z,tk_loop           ; R-C1: EOL (tk_loop reaches tk_end)
                cp      COLON               ; R-C1
                jp      z,tk_loop
                cp      '('                 ; R-C1
                jp      z,tk_loop
                cp      ' '                 ; R-C3: the blank is STORED
                jr      z,tcn_store
                cp      '0'                 ; R-C2: $21..$2F is DISCARDED
                jr      c,tcn_skip
tcn_store:
                call    upcase              ; R-C3: letters up, the rest verbatim
                ld      (de),a
                inc     de
tcn_skip:
                inc     hl
                jr      tk_call_name
```

**31 bytes, replacing 25.** Four properties that have to hold:

1. **`upcase` is safe on every stored character.** It touches `$61`..`$7A` only
   (`sub/tkfloat.asm:756`), so `` ` `` (`$60`) and `~` (`$7E`) pass through
   unchanged — which is what `cnm-bq` and `cnm-tilde` measured.
2. **EOL must be tested first.** `$00` is below `'0'`, so without the `or a` it
   would take the R-C2 skip path and `inc hl` would run **past the terminator**.
3. **`TKNAME` is not touched**, exactly as today. It is cleared at the top of
   `tk_loop` before the `CALL` token is matched and the scan never re-enters
   `tk_loop`, so the `5` after a `(` or `:` still begins a numeric constant —
   which is what `cnm-par` and `cnm-colon` require.
4. **No new label is parked in front of an existing one.** `tcn_store` and
   `tcn_skip` are interior to the rewritten block and both are reached by
   fallthrough *from within it*. This is the D-NAMBLANK K2 check, on a build that
   read 29/31 green *by luck* ([[knife-found-defect-in-own-fix]]).

### 3.1 🔴 The change DELETES a sub-ROM routine, and the dead-code gate forces it

The new loop no longer calls `is_ident_cont`. **`basic/vars.asm` is not included
by `sub/sub.asm`**, so [`basic/tokenise.inc:312`](../basic/tokenise.inc:312) is
the *only* caller of the sub-local clone at
[`sub/sub.asm:278`](../sub/sub.asm:278) — removing the call orphans it, and
`make basic-reloc`'s hard dead-code gate (0 dead, **both** builds) fails the
build rather than shipping it. The clone and its `siic_no` tail are **deleted**:
16 bytes.

`is_letter` **stays**: [`tokenise.inc:195`](../basic/tokenise.inc:195) (`tk_notkw`)
still calls it, so deleting its only *other* caller does not orphan it. The main
ROM's `is_ident_cont` in [`basic/vars.asm:48`](../basic/vars.asm:48) keeps all
three of its callers and is **not touched**.

**NET −10 bytes** (+6 for the loop, −16 for the clone), **all sub-ROM page 0**.

### 3.2 Scope — sub-ROM only, asserted by hash

`basic/tokenise.inc` is included by [`sub/sub.asm:209`](../sub/sub.asm:209) and
nothing else, and the second edit is inside `sub/sub.asm` itself. So both main
ROMs must come out **byte-identical** to HEAD:

* `build/basic-reloc.rom` = `1d270536f1bd26acbe947f2da7af93fce51d6c6f2d69d36391d1c9e59c51d9c7`
* `build/zerobas-main-eu.rom` = `90403dbb1022c5caa241c2b965f0abe2327788279150b8c5a299f7420142a91e`

(both verified against HEAD `2055d7e` before any edit). The main ROM's 23 B low /
8 B page-1 walls are not in play. The byte delta is read from the **uniform
address shift of the symbols downstream of the tokeniser in `build/sub.sym`** —
the `$FF`-tail scan of `sub.rom` is insensitive and did not move at all across
D-LNLIST's +26 B.

---

## 4. ⚠️ Two decisions to sign off

**(a) `CALL X,1` stops being two things.** Today `,` is copied and the `1`
crunches (`<CA> X,<12>`); under R-C2 it becomes the single name `X1`. That is
what both references do, and this project's charter is bug-for-bug fidelity
([[bug-for-bug-compat-over-accuracy]]) — but it means an extended statement can
**never** take bare comma-separated arguments, only parenthesised ones. zerobas'
only handler is `CALL FORMAT`, which takes none, and
[`basic/format.asm:58`](../basic/format.asm:58) `exc_skip` already discards
everything to `:`/EOL. **Recommendation: implement R-C2 as measured.** The
alternative — implementing R-C1/R-C3 and skipping R-C2 — would ship a rule
narrower than its denominator and leave 14 rows red.

**(b) The three `KNOWN_DIVERGE` entries retire.** `lnl-under`, `lnl-call` and
`lnl-callp` all come to agree under these rules, so `lnblank-acceptance` goes
**RED** and the entries must be **deleted**. That is the mechanism working — the
fifth cohort to leave the allowlist that way, and none of the previous four has
rotted. ⚠️ They are also pinned *pre-fix*, so until they are deleted they are the
cells asserting this change moved exactly what it claimed and nothing earlier.

**Not folded in, deliberately:** the missing `$0E` refs for
LIST/DELETE/AUTO/RENUM/ELSE (`ref-list` … `ref-else`, still informational), the
`--say`-rows-without-brackets sweep, and the trailing-blank-at-EOL question. All
are separate TODO items and none shares a code site with this one.

---

## 5. Rows

**Must move — 36 red today** (all `cnm`, zerobas column measured at `--repeat 2`
after the references were locked):

* the drop class (14): `cnm-plus` `cnm-minus` `cnm-star` `cnm-slash` `cnm-comma`
  `cnm-dot` `cnm-hash` `cnm-dollar` `cnm-pct` `cnm-excl` `cnm-amp` `cnm-apos`
  `cnm-rpar` `cnm-quote`
* the keep class (12): `cnm-pow` `cnm-idiv` `cnm-eq` `cnm-lt` `cnm-gt` `cnm-semi`
  `cnm-at` `cnm-quest` `cnm-lbrk` `cnm-rbrk` `cnm-bq` `cnm-tilde`
* blanks (3): `cnm-blk` `cnm-blk2` `cnm-blkpre`
* composed (3): `cnm-lowplus` `cnm-plpar` `cnm-mix`
* `_` parity (4): `cnm-uplus` `cnm-uminus` `cnm-usemi` `cnm-ublk`

…plus the three `KNOWN_DIVERGE` rows `lnl-under`, `lnl-call`, `lnl-callp`, which
turn green and are retired (§4b).

**Must NOT move — green on all three sides today:**

* the `cnm` controls: `cnm-ctl` `cnm-par` `cnm-thenctl` `cnm-noblk` **`cnm-format`**
  `cnm-uctl` `cnm-upar`, and the rows that already agree — `cnm-colon`
  `cnm-colstmt` `cnm-twoword` `cnm-digit1` `cnm-lower` `cnm-lowmix` `cnm-kw`
  `cnm-kwmid` `cnm-long` `cnm-under` `cnm-ucolon` `cnm-ulow` `cnm-ucolstmt`
* **`lnl-callpar` and `lnl-underpar`** — the two cells that pin that `CALL`/`_`
  disarm line-number mode. A scan that swallowed the `(` destroys that reading.
* the whole `lnl` mode battery, the `ref` battery, D-NAMDOT's `dot-*`,
  D-DECBLANK's `dec-dot*`, and every `num`/`body`/`lit`/`exp`/`nam` row.
* the say rows: `cnmd-ctl` `cnmd-blk` `cnmd-plus` (ERR **2** on all three sides)
  and `cnmd-colstmt`/`cnmd-colctl` (`A`=**7**, ERR **0**).

⚠️ **`cnm-under` (`20 CALL X_5`) is green today BY LUCK and must stay green for a
different reason.** zerobas currently *terminates* at the `_`, whereupon
`tk_notkw` dispatches it to `tk_underscore`, which copies it and re-enters
`tk_call_name` — arriving at the same bytes by a completely different route.
Under R-C3 the scan simply stores it. A row that agrees can agree for the wrong
reason, and this is one.

---

## 6. Gates

* `make lnblank-acceptance` at `--repeat 2`, three sides — **251/251, up from
  195/195**: exactly the 56 new `cnm` rows, 0 `UNSTABLE`, 0 `NOCAPTURE`. The
  5 `cnmd` rows are `--say` and stay outside the measurement pass (the say
  battery goes 15 → 20). `KNOWN_DIVERGE` goes **3 → 0** and the allowlist is now
  **EMPTY** — `lnl-under`, `lnl-call` and `lnl-callp` were reported as AGREEING
  and the gate stayed red until the entries were deleted.
  ⚠️ The `DIVERGENT` block still lists `dec-eol`, `dec-eolctl`, `ref-list`,
  `ref-delete`, `ref-auto`, `ref-renum` and `ref-else`. All seven are
  **INFORMATIONAL and pre-existing** — the missing `$0E` refs and the
  trailing-blank artifact, both separate filed items — and none moved.
* **The split assert** — both main ROM hashes byte-identical to §3.2.
* `make basic-reloc` from a **clean** `build/`: hard dead-code gate 0 dead on
  both builds (§3.1 is exactly what it is there to catch).
* Full corpus: `unit-test` 55/55 · `badfnum` 93 · `lof` 45 ·
  `chancost-characterize` · **`diskbasic` 34/34** · **`bdos` 12/12** ·
  **`fat-error`** · `error-trap` · `abort` 49/49 · `stop-trap` · `strig-trap` ·
  `key-trap` · `linemax` 60/60 · `arrdim` 73/73 · `clearpool` 52/52 ·
  `array` 149/151 (`ifc.instr.zero`, `ifc.instr.neg` by name).
  ⚠️ **`CALL` reaches the disk layer**, so `diskbasic`/`bdos`/`fat-error` are run,
  not assumed — `CALL FORMAT` is the one live handler on the target.

---

## 7. Knives — seven, RUN and reverted, each keeping the code REACHABLE

An orphaned block fails the dead-code gate and measures nothing, so every knife
changes one instruction (K6 restores one routine, on purpose). Scoped
`SIDES=vg8020,zb ONLY=cnm` — `ONLY=cnm,lnl` for K3 and K7 — since the two
references agree on every row in this probe.

| | cut | RED (measured) | GREEN half that survived |
|---|---|---|---|
| **K1** | `cp '0'` → `cp ' '+1` (R-C2 off: nothing is discarded) | 36/56. The 14 drop rows + `cnm-lowplus` `cnm-plpar` `cnm-mix` + `cnm-uplus` `cnm-uminus` | all 12 keep rows, every blank row, every terminator row, all 7 controls |
| **K2** | `jr z,tcn_store` → `jr z,tcn_skip` (R-C3's blank clause off) | 9/56 — **47 rows**, including the control **`cnm-format`** | exactly 9: `cnm-noblk` and the eight `_` rows that carry no blank |
| **K3** | `cp '('` → `cp '{'` (R-C1 narrowed; `(` falls into R-C2 and is discarded) | 6, exactly as predicted: `cnm-par` `cnm-plpar` `cnm-mix` `cnm-upar` **`lnl-callpar` `lnl-underpar`** | `cnm-colon` `cnm-colstmt` and the whole drop/keep walk |
| **K4** | `cp COLON` → `cp $7F` | 4, as predicted: `cnm-colon` `cnm-colstmt` `cnm-ucolon` `cnm-ucolstmt` | `cnm-par` `cnm-plpar` `cnm-mix` and the walk |
| **K5** | `call upcase` → three `nop`s | 4, exactly as predicted: `cnm-lower` `cnm-lowmix` `cnm-lowplus` `cnm-ulow` | all 52 rows typed in upper case |
| **K6** | 🔴 **aimed at my own justification** — restore `is_ident_cont` to `sub/sub.asm` with the new loop in place, i.e. with no caller | **the BUILD.** `check_dead_code.py` names `is_ident_cont` (~14 B) and `siic_no` dead; `make basic-reloc` exits 1 | — no row half; §3.1's deletion is **forced by the gate**, not argued |
| **K7** | `or a` → `cp 1` (the EOL test defeated) | **the MACHINE.** `20 CALL X` is `NOCAPTURE` — the scan runs past the `$00` and never stops | `20 CALL X(5)` reads correctly, alone |

### 7.1 🔴 K2's first prediction was wrong by a factor of seven — corrected before it ran

This spec originally predicted K2 would redden seven rows (the blank-bearing
payloads). It reddens **47**, because *every* `20 CALL …` row carries the blank
between `CALL` and the name — that blank is `$20` in the shipped
`call format` oracle. The nine survivors are precisely the payloads with no blank
inside the scan: `cnm-noblk` (`20 CALLX5`) and the eight `_` rows. The corrected
prediction matched the measurement exactly.

⚠️ **`cnm-format` is a control and K2 was predicted to redden it anyway.** That is
not a contradiction — a `^` mark means two-sided between the *candidate rules*,
and a knife is a third rule ([[knife-is-a-third-rule]]). Predicting it is what
made K2 capable of being wrong.

### 7.2 🔴 K7 could not have a green half in the form it was first run

Batched, K7 returned `NOCAPTURE` for **every** zerobas row — including
`cnm-par` and `cnm-colon`, which K7 cannot reach. That is not a reading: a hung
machine and a broken harness are the same value
([[chancost-noread-guard]]), and one dead machine destroys every later row in the
same boot.

Re-run on **isolated single rows** it separates cleanly:

```
cnm-par   20 CALL X(5)   vg8020 <CA> X(<16>)   zb <CA> X(<16>)    <- GREEN
cnm-ctl   20 CALL X      vg8020 <CA> X         zb NOCAPTURE       <- RED
```

So the corruption is **per payload**, and §3's property 2 is measured rather than
argued: a scan whose terminator is `(` is untouched, and a scan that must stop at
end-of-line runs away and takes the machine with it. The batched form is recorded
here rather than dropped, because "every row NOCAPTURE" is exactly the shape that
would otherwise be written up as a knife result.

### 7.3 ⚠️ `cnm-lower` reddened under two knives that cannot touch it

`cnm-lower` (`20 CALL abc`) read `REFUSED (empty program)` from zerobas under
**K1** and **K4**. Neither can reach it: its payload contains no character in
`$21..$2F` and no `:`. It had already done the same thing once, on the
**unknifed** build, in the pre-fix zerobas pass — and read `<CA> ABC` when re-run
alone (characterization §3). Under **K5** it produced an ordinary reading and
reddened for the genuine reason (upcase off).

It is a **batched-delivery artifact, not a knife result**, and it is listed in
neither knife's red set above. ⚠️ It is also intermittent rather than
deterministic, so `--repeat` cannot catch it — see §8.

⚠️ A knife that reddened a row whose payload contains **no `CALL` and no `_`**
would be a defect report about the fix, not a knife result — the D-NAMBLANK K2
shape. The `num`/`body`/`lit`/`dec`/`exp`/`nam`/`dot` batteries are what would say
so, and none of them moved under any of the seven.
