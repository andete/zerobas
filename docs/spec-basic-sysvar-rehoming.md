<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec — the RE-HOMING class: a recorded DECISION per published name

**Status: PROPOSED, awaiting sign-off. No `basic/` or `sub/` edit is part of this
slice until §9's questions are answered.**

Filed 2026-08-01 by D-SYSVAR as *"THE RE-HOMING CLASS: 8 PUBLISHED NAMES AT
PRIVATE ADDRESSES, AND NOBODY DECIDED THAT"* ([`../TODO.md:3384`](../TODO.md:3384)),
out of [`sysvar-msx1-coverage.md`](sysvar-msx1-coverage.md) §3.

---

## 1. Subject

zerobas' [`../basic/sysvars.inc`](../basic/sysvars.inc) shares 46 symbol names
with the published MSX work-area map: 38 at the published address, **8 re-homed**,
every one of them into the freed `VARTAB` window whose own comment reads *"own
choice — just-freed RAM"*.

| Symbol | zerobas | published | size |
|---|---|---|---:|
| `VALTYP` | [`$E0C8`](../basic/sysvars.inc:1139) | `$F663` | 1 |
| `FRETOP` | [`$E268`](../basic/sysvars.inc:1216) | `$F69B` | 2 |
| `SAVTXT` | [`$E1CF`](../basic/sysvars.inc:908) | `$F6AF` | 2 |
| `SAVSTK` | [`$E1C3`](../basic/sysvars.inc:839) | `$F6B1` | 2 |
| `ONELIN` | [`$E1C8`](../basic/sysvars.inc:852) | `$F6B9` | 2 |
| `ONEFLG` | [`$E1CA`](../basic/sysvars.inc:876) | `$F6BB` | 1 |
| `ARYTAB` | [`$E1C0`](../basic/sysvars.inc:827) | `$F6C4` | 2 |
| `DEFTBL` | [`$F153`](../basic/sysvars.inc:3223) | `$F6CA` | 26 |

Plus the pair the name-match structurally **cannot** see, because it is spelled
differently: `ERRCODE` [`$E1C5`](../basic/sysvars.inc:847) / `ERRLINE`
[`$E1C6`](../basic/sysvars.inc:849) against the published `ERRFLG $F414` /
`ERRLIN $F6B3`. **Ten variables, and the list is a lower bound.**

Every published extent matches zerobas' size exactly (1/2/2/2/2/1/2/26 B), so
size is nowhere a reason on its own — measured, not assumed.

---

## 2. ⚠️ The filed framing is a hypothesis, and reading the repo already refutes two parts of it

Five consecutive slices have had the wrong subject in the filed title, and
D-SYSVAR's own headline was a correction of *its* filed framing. This one is no
different, and the refutations cost nothing but a `grep`.

### 2.1 🔴 "NOBODY DECIDED THAT" is FALSE for `VALTYP`

[`../basic/usr.asm:19`](../basic/usr.asm:19) already carries a written,
**measured** decision about `$F663`:

> *"CALLING CONVENTION (own design …): zerobas is integer-only and has no
> floating-point DAC, so it does not use MSX-BASIC's DAC/VALTYP argument
> protocol. … The reference convention is now oracle-measured
> ([`../probes/basic/basic_probe_usr.py`](../probes/basic/basic_probe_usr.py),
> black-box differential vs Philips VG-8020): the reference passes an integer arg
> in DAC+2..3 …, **sets `VALTYP` (`$F663`) `=$02`**, and enters with HL->DAC base.
> zerobas instead passes the arg directly in HL and leaves DAC/VALTYP untouched —
> a deliberate own-design divergence."*

So for at least one of the eight the decision **exists**, is **oracle-locked**,
and names the very address. What does not exist is any trace of it *beside the
equate*, which is the only place a reader of `sysvars.inc` will look.

**The class is therefore not "eight undecided placements". It is "eight
placements, some of which have a decision recorded somewhere the next person will
not find it, and none of which has one at the equate."** That does not shrink the
work — the deliverable was already "record it once, where the next person will
find it" — but it changes what the write-up may claim, and it is the second
independent instance (after `$F414`) of *the repo knowing something its own
`sysvars.inc` does not say*.

### 2.2 🔴 "PER VARIABLE" is the wrong unit — the published map's consumers read GROUPS

`ARYTAB $F6C4` is not a thing a program reads. The published contract is a
**chain**: `TXTTAB $F676` ≤ `VARTAB $F6C2` ≤ `ARYTAB $F6C4` ≤ `STREND $F6C6`, and
a program that wants "bytes of array space" computes `STREND − ARYTAB`. This
repo already documents that chain as a group and sources all four addresses
together ([`../basic/docs/spec-bload-r.md:68`](../basic/docs/spec-bload-r.md:68)).

zerobas defines `TXTTAB` at its published address, `ARYTAB` re-homed, and
**`VARTAB` and `STREND` not at all** (the scalar base is *derived* as
`(PRGEND)+2`, [`../basic/sysvars.inc:1577`](../basic/sysvars.inc:1577)). So:

> 🔴 **Honouring `ARYTAB $F6C4` alone would be WORSE than leaving it at zero.**
> A consumer subtracting a power-on `STREND` of `$0000` from a now-plausible
> `ARYTAB` gets a large negative length, i.e. a *confident wrong answer*, where
> today it gets `0 − 0 = 0` and an obviously dead reading. This is the `TAB(`
> shape one level up: a partially-honoured contract agrees with nothing and
> **looks** like it works.

The same applies to the error trio (`ERRFLG`/`ERRLIN`/`ERRTXT` — `ERR`, `ERL`
and `RESUME`'s text pointer), the trap set (`ONELIN`/`ONEFLG`/`SAVTXT`/`SAVSTK`),
the string-space set (`FRETOP`/`STKTOP $F674`/`MEMSIZ $F672`) and the type pair
(`VALTYP`/`DEFTBL`, both of which encode the same four-value float type code).

**This spec therefore decides per variable but REASONS per contract group**, and
a decision that would break a group is not admissible.

### 2.3 ⚠️ A third premise is wrong, and it is in the brief

*"Low is 23 B and page 1 is 8 B"* is quoted as the constraint. It is not the
binding one for this class. `SAVSTK equ $E1C3` → `SAVSTK equ $F6B1` is an
**assembler-constant change**: if every access goes through the symbol, the ROM
cost is **zero bytes**. The real constraints are (a) does anything else own the
published address on the repack machine, (b) do the semantics match, (c) does the
published address survive zerobas' own cold-boot and reset paths. Space is a cost
only for the *mirroring* option (§4), never for a pure re-home.

---

## 3. SCOPE — what a DECISION is required to contain

Inherited unchanged from [`spec-basic-sysvar-denominator.md`](spec-basic-sysvar-denominator.md)
§2, signed off: **"uses" means meaning (2), does a READ of that address return
the same value.** Meanings (1) write-parity and (3) internal dependence stay out.

A decision that says only "keep it where it is" is not a decision, it is the
status quo with a comment. Each of the ten gets **four fields, in this order**,
and the first three are inputs the fourth is not allowed to contradict:

| Field | Answered by |
|---|---|
| **SEMANTICS** — is the published variable the same variable? | 🔬 measurement (§5), never by the shared name |
| **OBSERVER** — what would read the published address, concretely? | named channel or *none*; "a program might `PEEK` it" is not an observer |
| **COST** — re-home / mirror / not possible | ROM bytes, measured from a build |
| **DECISION** — HONOUR · MIRROR · REJECT(reason) · DEFER(what would settle it) | must cite the three above |

⚠️ **A shared NAME is not shared SEMANTICS**, and this is the field most likely
to be filled in by reasoning. It must not be. zerobas' `SAVSTK` is documented as
an SP anchor for the trap unwind; whether the published `SAVSTK` holds that is a
question nobody has asked, and §5 is where it gets asked of the references
themselves.

---

## 4. The decision lattice

| Verdict | Meaning | Admissible when |
|---|---|---|
| **HONOUR** | change the `equ` to the published address | semantics match, the published address is free, the whole group can move |
| **MIRROR** | keep the private cell, *also* store to the published address | semantics match but the private cell cannot move (page-0/low-region reach, reset ordering) |
| **REJECT-SEMANTICS** | the published variable is a different variable | the encoding or the role differs and honouring the address would publish a plausible wrong value |
| **REJECT-GROUP** | honouring it alone breaks a contract its consumers read as a set | §2.2 |
| **REJECT-CONFLICT** | the published address is not zerobas' to write | C-BIOS or the disk ROM owns it on the repack machine |
| **DEFER** | states what single measurement would settle it | never a resting place without that sentence |

🔴 **MIRROR is the option the filed item did not consider, and it is why "moving
live error state is not a free edit" does not settle anything.** Mirroring does
not move live state: `raise_error` keeps writing `ERRCODE $E1C5` and adds a store
to `$F414`. It costs ROM bytes and creates a two-copy invariant — both real, both
*measurable* — but the argument that killed relocation does not reach it.

⚠️ **MIRROR is admissible only for a WHOLE GROUP.** A mirrored `ARYTAB` beside an
unmirrored `STREND` is §2.2's confident wrong answer with extra steps.

---

## 5. What must be MEASURED before any of this is filled in

### 5.1 The instrument gap, and it is a real one

[`../probes/basic/basic_probe_sysvarsweep.py`](../probes/basic/basic_probe_sysvarsweep.py)
sweeps `$F380..$FFFE`. **Every zerobas private address in §1 is BELOW that span**
(`$E0C8`, `$E1C0..$E1D1`, `$E268`, `$F153`). So the existing sweep can see that
zerobas leaves the *published* address at its power-on value, and **cannot see
zerobas' side of the re-homing at all**. It can say "not honoured"; it cannot say
"and here is the same value, 1440 bytes lower".

That is exactly the cost §2 of the coverage doc states rather than hides, and
closing it is this slice's apparatus work: **capture zerobas' private cells in
the same `mem_abs` read**, as extra segments —
`($E0C8,1) ($E1C0,18) ($E268,2) ($F153,26)`, 47 B — so the published and the
private cell are read by one instrument, at one instant, per side.

### 5.2 New stimulus states — designed to MOVE a specific group

The dynamic denominator covers 5 stimuli against a 279-entry static one; the
brief's cheap extension and this slice's need are the same states. Every one is
**paired with a control that differs in exactly the property under test.**

| State | Payload | Group | 🟢 pairs with | Screen evidence |
|---|---|---|---|---|
| `s6-armed` 🟢 | `10 ON ERROR GOTO 100` / `20 STOP` / `100 STOP` / `RUN` | trap | `s7` | `break in 20` |
| `s7-fired` | `10 ON ERROR GOTO 100` / `20 GOTO 99999` / `100 STOP` / `RUN` | trap + error | `s6` | `break in 100` |
| `s8-str4` 🟢 | `A$=STRING$(4,66):PRINT A$` | string heap | `s9` | `BBBB` |
| `s9-str20` | `A$=STRING$(20,67):PRINT A$` | string heap | `s8` | 20 × `C` |
| `s10-defint` 🟢 | `DEFINT A:PRINT"[";A;"]"` | type | `s11` | `[ 0 ]` |
| `s11-defstr` | `DEFSTR A:PRINT"[";A;"]"` | type | `s10` | `[]` |
| `s12-scal1` 🟢 | `A=1:PRINT"[";A;"]"` | pointer chain | `s13` | `[ 1 ]` |
| `s13-scal3` | `A=1:B=2:C=3:PRINT"[";C;"]"` | pointer chain | `s12` | `[ 3 ]` |

Each pair is a **delta measurement**, which is what makes it a semantics test
rather than a value comparison:

* `s6`/`s7` — the *only* difference is whether the trap fires. `ONELIN` must move
  in **both** (armed), `ONEFLG`/`ERRFLG`/`ERRLIN` in `s7` only. A variable that
  moves in both is not error state — this is D-SYSVAR's own `s2-noerr` lesson
  applied one level deeper, and it is what tells `ONELIN` apart from `ONEFLG`.
* `s8`/`s9` — 16 bytes of string. If published `FRETOP` differs by 16 between
  them it is an **allocation pointer**; if it does not move it is a boundary, and
  zerobas' `FRETOP` (documented as *"heap low boundary … grows DOWN as strings
  alloc"*) is then either the same variable or the opposite one. **The name
  cannot answer this and the delta can.**
* `s10`/`s11` — the published `DEFTBL` is documented as a **float type code**
  (`2` int / `3` string / `4` single / `8` double); zerobas' is a 0/1 sentinel
  (`DEFTBL_STR equ 1`). The pair reads the actual byte for the same declaration
  on all three sides. 🟢 And its evidence is *diagnostic*, not merely delivery:
  `[ 0 ]` vs `[]` is the type decision itself showing on screen.
* `s12`/`s13` — two extra scalars. The published `ARYTAB`/`STREND` must both move
  up by one scalar entry each; zerobas' `ARYTAB $E1C0` must move by its own entry
  size. Whether the *sizes* agree is a separate question and is not asked here.

### 5.3 The re-homing table — the report the decision is written from

A new pass printing, per variable × state, one row: the refs' bytes at the
**published** address, zerobas' bytes at the **published** address, and zerobas'
bytes at its **private** address — each as `base → current`. Verdict per cell:

| | Meaning |
|---|---|
| `SAME-VAR` | zb's **private** value equals the refs' **published** value ⇒ the same variable at the wrong address — the re-homing case proper |
| `SAME-ROLE` | both move under the same stimulus, values differ ⇒ same job, different encoding/representation |
| `REF-ONLY` | the refs move it, zerobas' private cell does not ⇒ **not the same variable** |
| `ZB-ONLY` | zerobas' private cell moves, the refs' published one does not |
| `INERT` | neither moves ⇒ **this stimulus does not test this variable** (a non-result, never a pass) |
| `PUB-FREE` | zerobas' byte at the published address never moves in any state ⇒ the address is available |

⚠️ **`PUB-FREE` shipped as a COLUMN, not a verdict.** Every row prints
`zb@pub=base->cur`, and "never moved in any of the nine states" was read off that
column for all ten before any address was honoured. It is *not* a standing
assertion in the probe, and saying so matters: for the five that were rejected it
remains an observation only. For the five that were honoured the standing
assertion exists in the opposite direction — **`C-VACATED`**, which requires the
addresses they moved *out* of to stay inert.

---

## 6. Controls — all four of the standing ones, and one new

1. **Oracle-lock first.** Every new state runs on **both references at
   `--repeat 2` before zerobas is run on it**, and the reference readings are
   written down before zerobas' are looked at. The sweep prints all three sides
   at once, so this needs a `--sides` filter; without it the discipline is a
   promise rather than a mechanism. A mangle in the oracle-lock direction is a
   false PASS forever — and here the risk is sharper than usual, because the
   *decision* is being derived from what the references do.
2. **Echo guard on EVERY side**, zerobas included. A memory dump cannot tell "the
   byte did not move" from "the stimulus never arrived", and an undelivered line
   yields a perfect silent three-way agreement that fails **toward "pass"**. Note
   the guards in §5.2 are stronger than delivery: `break in 20` vs `break in 100`
   verifies the *branch taken*, so a state that delivered but did not trap is
   caught too.
3. **Every red paired with a green control** — §5.2 is built entirely of pairs.
4. **A control must be able to MOVE ITS OWN SUBJECT.** D-SYSVAR's volatility
   control was wired to `cap_gap`, which moves nothing, and published a false
   `REPCNT` finding while reporting `VOLATILE=0` over the whole work area. The
   jitter is on `boot` and stays there; the new segments inherit it.
5. 🆕 **C-PRIV — the private segments must be shown to be READ.** The new
   `mem_abs` segments are a new instrument, and a segment list that is silently
   mis-ordered or dropped would render every private cell as a plausible constant.
   Pin it: `DEFTBL`'s private cell `$F153` must **change between `s10-defint` and
   `s11-defstr` on zerobas**, from a declaration whose effect is independently
   visible on the screen guard (`[ 0 ]` vs `[]`). A private segment that cannot
   be shown to move is not a reading.

---

## 7. Falsifiability

> **C-REPRO-2.** The re-homing table must **independently re-derive `$F414`**:
> `ERRFLG` `REF-ONLY` at the published address under `s7-fired`, and `SAME-VAR`
> against zerobas' private `ERRCODE $E1C5` — i.e. it must find both halves of the
> statement the coverage doc could only make one half of. If it does not, the
> new pass is broken, not the finding.

The existing `C-REPRO` and `C-INSTR` stay exactly as they are.

---

## 8. Deliverables — ✅ DELIVERED, and what the outcome was

**Outcome: five HONOURED at zero ROM cost, two REJECT-GROUP, two
REJECT-UNOBSERVABLE, one DEFER** —
[`sysvar-rehoming-decisions.md`](sysvar-rehoming-decisions.md) is the record, and
the decisions are at the equates. The build after the change reports the
identical `low = 23 B / page 1 = 8 B`, dead-code `0/0`, so §2.3's claim that space
was never the binding constraint is measured rather than argued.

🔴 **THREE of the apparatus' own controls were INVERTED by the fix, and deleting
them would have been the wrong answer.** `C-REPRO` asserted `$F414` DIVERGE
(refs `08`, zb `00`) and `C-REPRO-2` asserted the value lived at `$E1C5`
instead — both describe a state this slice deliberately ended. Each was re-aimed
at the *new* known answer (`HONOURED`, `08`/`08`; and "zerobas tracks the
published cell"), which is **strictly stronger than what it replaced**: the old
`C-REPRO` passed whenever zerobas did nothing at all with `$F414`, and the new one
fails the moment the honouring regresses. A positive control that a fix makes
obsolete is a control that has to be re-pointed, not retired.

> 🔴 **And the third one was MISSED — the run caught it, not the author.**
> `C-PRIV` pinned the private segments' liveness on `DEFTBL['A']` at `$F153`,
> and `DEFTBL` is one of the five addresses this slice **honoured**. On the
> post-fix build `$F153` is ordinary unused RAM reading `$FF` in both states, so
> `C-PRIV` failed and voided the run — **correctly**. Two controls were re-aimed
> deliberately and the third was overlooked, because it was being thought of as
> *"the DEFTBL cell"* rather than as *"a cell that must still be private"*.
> It is now anchored on `ARYTAB $E1C0` — chosen precisely **because its verdict
> is REJECT-GROUP**, so it stays private by decision and no future honouring can
> pull the rug out again.
>
> ⚠️ The lesson had already been written down *in this same slice* before the
> instance that proved it was found. A rule stated is not a rule applied; the
> only thing that caught it was running the gate.

🆕 **C-VACATED** was added for the failure mode nothing else here can see: a
half-completed relocation leaves a **stale store at the old address**, and the
published cell would look perfectly honoured while dead RAM is written by code
nobody knows still exists. The five vacated cells must be inert on every side in
every state.

### Original list

1. `probes/basic/basic_probe_sysvarsweep.py` — private segments, 8 new states,
   the re-homing table, `--sides`, `C-PRIV`, `C-REPRO-2`.
2. `docs/sysvar-rehoming-decisions.md` — the ten decisions, four fields each.
3. [`../basic/sysvars.inc`](../basic/sysvars.inc) — **the decision recorded at
   each equate**, one short block, pointing at (2). This is the deliverable the
   item actually asked for; everything else exists to make it true.
4. `TODO.md` — the item closed with its measurement, and whatever it files.
5. Whatever `basic/`/`sub/` change a HONOUR or MIRROR verdict implies — **and if
   there is none, that is a result, not a failure**, provided each rejection
   names its reason from §4.

⚠️ Any change under `basic/` — **including a comment-only one** — requires the
full corpus. A comment-only change additionally gets the stronger check
available to it: the assembled ROM must be **byte-identical** to `2e00cd9`'s.

---

## 9. Sign-off — ✅ GRANTED 2026-08-01

**Q-A — the unit of decision. ✅ REASON PER GROUP.** Each of the ten is decided
on its own, but a verdict that would break a contract group (pointer chain, error
trio, trap set, type pair) is **inadmissible**. `REJECT-GROUP` stands in §4.

**Q-B — is MIRROR admissible? ✅ YES — cost it, then decide.** MIRROR joins
HONOUR/REJECT in the lattice, admissible only for a whole group, and its ROM cost
must be **measured from a build** before it is proposed. The slice may therefore
end in a real `basic/` change, with the full corpus.

Not requested, because §3 inherits them already signed off: the scope (meaning 2)
and the denominator source.

---

## 10. 🔒 The ORACLE-LOCK pass — reference semantics, pinned before zerobas ran

`make sysvarsweep SIDES=vg8020,cf3300 ONLY=s6-armed,…,s13-scal3`, `--repeat 2`,
echo guard OK on both sides for all 9 states, C-INSTR OK on both. **These
readings were written down before zerobas was run on any of these states**, which
is the whole point of §6.1 — the decisions below are derived from them.

| Variable | What the references do | Semantics verdict |
|---|---|---|
| `VALTYP $F663` | `03` at boot, **never moves in any of the 8 states** | a **transient**, not observable at a prompt |
| `ERRFLG $F414` | `00 → 08` under `s7-fired` **only** | the ERR code, confirmed |
| `ERRLIN $F6B3` | `0000 → 1400` = **20**, the erroring line, `s7` only | `ERL`, confirmed |
| `ONELIN $F6B9` | `→ $8015` (`s6`) and `→ $801C` (`s7`) — **moves in BOTH** | the **armed handler** pointer, confirmed |
| `ONEFLG $F6BB` | `00 → FF` under `s7` only | 🔴 **`$FF`, not `1`** |
| `SAVTXT $F6AF` | `$F40F`, **never moves** | a transient, back at the line buffer by the prompt |
| `SAVSTK $F6B1` | `$F09E` vs `$DB95`, never moves — **NO-ORACLE** | not measurable by this method |
| `FRETOP $F69B` | **−4 under `s8`, −20 under `s9`, on BOTH machines** | 🔴 the **allocation pointer**, confirmed |
| `ARYTAB $F6C4` | `$8003` → steps up once per scalar; `$8003→$800E→$8024` | end-of-scalars pointer, confirmed |
| `DEFTBL $F6CA` | boot = 26 × `08` (**double**); `DEFINT A`→`02`, `DEFSTR A`→`03` | a **float type code**, confirmed |

🔴 **The `s6`/`s7` pair earned its place immediately.** `ONELIN` moves in *both*
— so it is **armed** state — while `ONEFLG`/`ERRFLG`/`ERRLIN` move in `s7` only.
A single fired state would have reported all four as "error state", which is
D-SYSVAR's own `s2-noerr` lesson one level deeper. And the `$801C − $8015 = 7`
gap between the two `ONELIN` values is exactly how much longer `20 GOTO 99999` is
than `20 STOP`: the pointer tracks the **program layout**, which is a stronger
confirmation than either value alone.

🔴 **And the pair found a defect in the verdict lattice it was run under.**
`FRETOP` is reported `NO-ORACLE` — the two references hold different absolute
values ($F168 vs $DC5F) because their string spaces start in different places.
**They nevertheless agree perfectly on the quantity that carries the meaning:**
both move **−4** for a 4-byte string and **−20** for a 20-byte one. A byte-wise
absolute comparison *cannot* read a pointer into machine-dependent RAM and can
only ever answer `NO-ORACLE`.

> ⚠️ **`NO-ORACLE` is a verdict about the COMPARISON, not about the variable.**
> D-SYSVAR's 311-byte `NO-ORACLE` bucket is described there as "not measurable by
> this method", and that was the right words for the wrong reason: for
> pointer-valued variables the method, not the machines, is what fails to agree.
> §5.3 gains a **Δ column** for exactly this, and the bucket is re-filed.

⚠️ **Two variables cannot be read at a prompt at all**, and saying so is part of
the measurement: `VALTYP` and `SAVTXT` are refreshed on the way back to the
command line, so their value at every capture instant is an artifact of the line
editor, not of the stimulus. **They are not `INERT`, they are UNOBSERVABLE by
this instrument** — a distinction the report must make, because "never moves"
reads like "nothing to honour" and here it means the opposite.
