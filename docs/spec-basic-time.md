<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# zerobas BASIC — `TIME` and `TIME=n` (the software clock pseudo-variable)

Status: **DRAFT — awaiting sign-off.** Characterization complete
(VG-8020, 2026-07-26); §7 funding is the one open decision.

`TIME` is standard MSX1 BASIC and is currently **absent from zerobas entirely** —
it is not in the keyword table, so a program writing `TIME` gets the *variable*
`TI` and reads 0 forever. That is a **silent** divergence: an `IF TIME-T<400`
loop never terminates. It was found as collateral during the T3 KEY trap slice
(`20e04b4`) and recorded as an open charter gap in
[`spec-traps-t3-key.md`](spec-traps-t3-key.md) §4.2, tracked in no other doc
until this one. It is also a standing **tax on the probe harness**: the T3 gate
rule "no probe program may use `TIME` on the zerobas side" exists only because of
this gap, and every acceptance window since has had to be sized by iteration
count instead of by elapsed jiffies.

Closing it also retires the last `TIME`-shaped caveat in
[`spec-basic-graphics-g8.md`](spec-basic-graphics-g8.md) §Q and
[`spec-traps-t4-sprite.md`](spec-traps-t4-sprite.md) §—.

---

## 1. Oracle characterization (Philips VG-8020, 2026-07-26) — measured, not assumed

All of §1 is black-box measurement against the reference: injected BASIC lines,
screen/stored-line capture, no ROM bytes read. Probe rounds 1–5 are reproduced by
`probes/basic/basic_probe_time.py` (§8).

### 1.1 Token `[PIN]`

`TIME` is a **single-byte reserved-word token `$CB`**, crunched greedily at every
position like every other keyword:

| source | crunched body bytes |
|---|---|
| `A=TIME`  | `41 EF CB` |
| `TIME=0`  | `CB EF 11` |
| `PRINT TIME` | `91 20 CB` |
| `A=TIMES` | `41 EF CB 53`  — `TIME` + verbatim `S` |
| `A=TIME$` | `41 EF CB 24`  — `TIME` + verbatim `$` |
| `A=ATIME` | `41 EF 41 CB`  — verbatim `A` + `TIME` |
| `A=TI`    | `41 EF 54 49`  — plain variable, untouched |

`$CB` is **unused in zerobas** and sits between `CALL` (`$CA`) and `KEY` (`$CC`),
consistent with the rest of the pinned table. `TIME` shares no prefix with another
entry, so its position in `kwtable.inc` is free (`match_kw` is full-keyword).

### 1.2 `TIME` as a factor (the read) `[PIN]`

`TIME` reads the **16-bit little-endian word at `JIFFY` (`$FC9E`)** as an
**unsigned 0..65535**, and yields a **float**, not an int16:

| case | reference |
|---|---|
| `POKE&HFC9F,&H30:POKE&HFC9E,0:PRINT TIME` | `12288` (= `$3000`) — it *is* `JIFFY` |
| `TIME=40000:PRINT TIME` | `40000` (an int16 would print `-25536`) |
| `TIME=65535:PRINT TIME` | `65535` |
| `TIME=40000:A%=TIME` | **Overflow (ERR 6)** — the float→int16 assignment |
| `TIME=1000:TIME=TIME+5:PRINT TIME` | `1005`/`1006` — readable in its own RHS |
| `TIME=5:PRINT FRE(0)` | unchanged vs. no assignment (`TI=5` costs 11 B) — `TIME` is **not** a variable |

**Single vs. double is not observable** and is therefore a free implementation
choice: every `TIME` value is an integer ≤ 5 digits (identical in both
renderings), and MSX BASIC performs *all* float arithmetic in double
([[float-pack-arc]]), so no operator can discriminate the operand's own type.
Measured directly: `A!*B!`, `A!*B#` and `TIME*A!` all print identically.

### 1.3 `TIME=<expr>` as a statement (the write) `[PIN]`

Stores into `JIFFY`. The float→word conversion is **exactly the house
ADDRESS-DOMAIN conversion** already implemented for `POKE`/`VPOKE`/`HEX$`
(`fac_to_int_addr` → `domain_convert_core` in address mode): domain
**−32768 .. 65535**, values ≥ 32768 wrap by −65536 first, then **truncate toward
zero**; outside → **Overflow (ERR 6)**.

This was the round's one real trap. A first, tick-naive reading said "rounds"
(`TIME=1.6` → 2) and produced a self-contradictory table (`65534.6` → 65535 but
`65535.4` → 0). The confound: `JIFFY` can tick between the assignment and the
`PRINT`, and in a *batched* run that phase is **reproducible**, so repeating a case
does not average it out. Re-measured with a deliberate phase shift (a variable-length
`FOR` delay before the assignment) and the **minimum** over 8 phases — the stored
value is a lower bound of every reading — every number falls into one rule:

| assigned | stored (min over 8 phases) | via |
|---|---|---|
| `1.4` / `1.5` / `1.6` | `1` | truncate |
| `0.5` / `2.5` / `3.5` | `0` / `2` / `3` | truncate |
| `40000` | `40000` | wrap → `−25536` → truncate |
| `65534.6` | `65535` | wrap → `−1.4` → truncate → `−1` |
| `65535.4` / `65535.6` | `0` | wrap → `−0.6`/`−0.4` → truncate → `0` |
| `−1` / `−100` / `−32768` | `65535` / `65436` / `32768` | plain truncate |
| `65536` / `99999` / `−32769` / `−99999` | **ERR 6** | out of domain |

Cross-checked against `POKE` on the same machine (no interrupt race, so a clean
control): `POKE 55296.4` writes `$D801`, `POKE 55296` writes `$D800`,
`POKE −10240.4` and `POKE −10240.6` both write `$D800` — the identical
wrap-then-truncate rule. **zerobas already implements it**, and
`float-arith.asm`'s `dcc_frac_*` comment already names the very edge case
(`65534.6`) this round re-derived from the outside.

### 1.4 Error surface `[PIN]`

| statement | reference |
|---|---|
| `TIME=5` | ok |
| `TIME="A"` / `A$="X":TIME=A$` | **Type mismatch (ERR 13)** |
| `TIME=` / `TIME=:PRINT 1` | **Missing operand (ERR 24)** |
| `TIME=65536` / `TIME=99999` / `TIME=−32769` | **Overflow (ERR 6)** |
| `LET TIME=5` | **Syntax error (ERR 2)** |
| `TIME` (bare) / `TIME 5` | **Syntax error (ERR 2)** |
| `FOR TIME=1 TO 3` / `SWAP TIME,A` / `READ TIME` / `DIM TIME(3)` / `TIME(1)=5` | **Syntax error (ERR 2)** |
| `IF TIME>0 THEN …` | ok (factor) |
| `DEFINT T-Z:TIME=70000` | ERR 6 — `DEFINT` does not reach a keyword |

`TIME` is an lvalue in **exactly one** production: a statement that *starts* with
the `$CB` token. This is the same shape as G8's `VDP(n)=` / `BASE(n)=`, and the
whole ERR-2 row therefore **falls out for free** — `ex_letkw`, `ex_for`, `READ`,
`DIM` and `SWAP` all accept only a variable *name*, and a token is not one.

### 1.5 The clock itself

* Ticks with the VDP frame interrupt: **240 jiffies per 3000 empty `FOR`
  iterations** on the VG-8020 ⇒ 50 Hz PAL, and the ~4.8 s/3000-iteration
  calibration in [[traps-t3-key-slice]] is reconfirmed.
* **Wraps mod 65536 with no error**: `TIME=65500` + ~240 jiffies → `204`.
* The **rate belongs to the host BIOS/VDP**, not to BASIC. zerobas inherits
  C-BIOS's, exactly as T3 inherits its key-repeat constants. Per that slice's
  gate design point (a), the acceptance gate must test the **property** (the clock
  advances, monotonically, and wraps) **per machine**, never an equal jiffy count
  across the two machines.

---

## 2. Scope

**In:** the `$CB` token (crunch + `LIST` detokenise), `TIME` as a numeric factor,
`TIME=<numeric expr>` as a statement, and the four measured errors (13 / 24 / 6 / 2).

**Out:** `SET TIME`, `TIME$`, and `INTERVAL` — all MSX2, out of charter
([[interval-is-msx2-not-msx1]]). No new RAM byte: `JIFFY` (`$FC9E`) is the whole
state, and it is already the BIOS's.

---

## 3. Design

Three edits, all reusing existing machinery. Nothing new is invented.

### 3.1 Token + table

`TIME_TOKEN equ $CB` in `sysvars.inc`; `db 4,"TIME",1,TIME_TOKEN` in
`kwtable.inc`. Since wave 3 the **sub-ROM copy of `kwtable` is the sole source**
and drives both crunch and `LIST` detokenise, so one entry buys both directions,
and it costs **zero main-ROM bytes** (sub page 0 has room to spare).

### 3.2 The read — `ev_f_time`, a 3-byte edit of `ev_f_erlfn`

`ERL` is already precisely this shape: an **unsigned** word 0..65535 that must not
print as a negative number, promoted to a float by
`widen_uint_to` + `round_and_finalize` (FAC := packed double, `FACTYP` := 8).
`ev_f_time` is `ev_f_erlfn` with `ld hl,(ERRLINE)` replaced by `ld hl,(JIFFY)`.

That also *settles* §1.2's unobservable type in the cheapest direction: double,
because the existing helper produces one.

### 3.3 The write — `ex_time_assign`, G8's assignment parse minus the index

`g8_assign` is the template, including both error checks this slice needs:
the explicit end-of-statement test that yields **ERR 24** (`g8_missing`) and
`g8_num_operand`'s `str_eval_one` → **ERR 13** on a string. The only substitution
is the conversion: G8 wants a byte, `TIME=` wants the **address domain**, so the
operand goes through `fac_to_int_addr` (checked — ERR 6 outside), then
`ld (JIFFY),de`.

### 3.4 Atomicity — `di` / `ei` around both 16-bit accesses

`ld hl,(JIFFY)` is two byte reads; the timer ISR can tick between them and hand
back a torn value (`$00FF` → `$01FF`). The same applies to the store. Two bytes
each, and the codebase already uses this idiom for exactly this reason
(`sound.asm:88` — "single write, likewise atomic vs play_service"). BASIC always
runs with interrupts enabled, so an unconditional `ei` is safe here.

*This is a correctness fix, not a fidelity claim:* a torn read is unobservable in
a differential (it is rare and non-deterministic on both sides), so it is not
gated — it is 4 bytes of insurance, and §7 should say so if bytes get tight.

### 3.5 Placement

`ev_f` (`$4CBE`) and `exec_stmt` (`$406D`) are both **main page 1**, so the two
`cp`/`jp z` dispatch pairs must be page-1 resident. `fac_to_int_addr` (`$3842`),
`widen_uint_to` (`$3BE6`) and `round_and_finalize` (`$33FA`) are all **low
region**, reachable from page 1 as ordinary calls. The bodies could in principle
be low-region, but the low region has 5 B free, so the realistic answer is: **all
of it is a page-1 need.**

---

## 4. Byte budget — ESTIMATE, and per the arc lesson a **LOWER BOUND**

Measured from the symbol table, sizing each piece by its live template:

| piece | bytes | basis |
|---|---|---|
| `ev_f` dispatch (`cp` + `jp z`) | 5 | measured shape |
| `ev_f_time` body | 17 (+2 `di`/`ei`) | `ev_f_erlfn` = **17 B**, symbol-table measured |
| `exec_stmt` dispatch | 5 | measured shape |
| `ex_time_assign` body | ~23 (+2 `di`/`ei`) | `g8_assign` minus `g8_open_paren`, plus the conversion call |
| `kwtable` entry | 0 main | sub-ROM only |
| **total, main page 1** | **~52** | |

Every byte estimate in this arc has come in low (T2 by 70 B, T3 by 106 B = 1.8×),
so plan on **52–75 B**.

**Page 1 has 22 B free** (low region 5 B), measured on the current tree by
`make basic-reloc`. ⇒ **short by roughly 30–55 B.**

---

## 5. Decisions for sign-off

* **D-TIME-1 — the numeric type of the read.** Unobservable (§1.2). *Rec:*
  **double**, because `ev_f_erlfn`'s existing `widen_uint_to` +
  `round_and_finalize` pair produces one and costs nothing extra. No deviation is
  being taken; there is simply nothing to be faithful *to*.
* **D-TIME-2 — `ei` after the guarded access.** *Rec:* **adopt** (§3.4), 4 B, and
  drop it first if §7's funding lands tight.
* **D-TIME-3 — ERR 24 for `TIME=` (missing operand).** The reference raises it,
  and so does zerobas's G8 path — but zerobas **silently accepts** bare `A=` and
  `POKE 100,` today (measured this round on the repack build; the reference gives
  "Missing operand" for both). That is a **pre-existing divergence wider than
  `TIME`**, and `TIME=` will not inherit a fix that does not exist. *Rec:* spend
  the ~6 B to make `TIME=` correct **at its own site** (G8 already does exactly
  this), and raise the general `A=` / `POKE 100,` gap as a separate item rather
  than widening this slice. Flagging it rather than silently matching the local
  bug is the point.
* **D-TIME-4 — funding the ~52–75 B.** The need is **pure page 1**, so a
  promotion cannot help (it moves low → page 1, and low is the emptier wall at
  5 B). The established answer is a **carve**: move a page-1 cluster into the
  sub-ROM as a tenant ([[subrom-tenant-playbook]]). This is the smallest funding
  need the arc has had. *Open — I have not yet chosen or measured a candidate,
  and per [[traps-t3-key-slice]] the unit must be picked by an
  **external-caller census**, not by file size.*

---

## 6. Gate — `make time-acceptance`

`probes/basic/basic_probe_time.py`, differential vs. the VG-8020, batched.

1. **Crunch** — the §1.1 table, byte-for-byte, via the `stored_line` capture
   (including the three shadow cases `TIMES` / `TIME$` / `ATIME`, which prove the
   greedy match did not eat a variable name), plus a `LIST` round-trip.
2. **Read** — the §1.2 rows; `POKE`-`JIFFY`-then-read pins the location, and
   `A%=TIME` at 40000 pins "not an int16".
3. **Write** — the §1.3 conversion table. **Every case runs the phase-shifted,
   min-over-8 protocol of §1.3** — a single reading of `TIME` after an assignment
   is not a measurement, and this gate must not re-import the confound that made
   two rounds agree on the wrong answer.
4. **Errors** — the §1.4 table via `ON ERROR GOTO` + trapped `ERR`.
5. **Clock** — per-machine *property* only (§1.5): advances, monotonic, wraps at
   65536. Never an equal jiffy count across machines. These three cases need a
   **40 s emulated capture step**, not the 2.5 s default: a 3000-iteration `FOR`
   is ~4.8 s on the VG-8020 and zerobas is ~7× slower. The first run of the
   committed probe returned `??` for two of the three for exactly this reason —
   it reported *unfinished*, not zero, which is the contract working
   ([[paint-slow-emulated-budget-trap]]).
6. **`done` sentinel** — every reading is gated on it. A program that did not
   finish is a FAILURE, not a zero ([[error-handling-arc]]).

Standing regression: `make basic-acceptance` + `string-acceptance` (the crunch
corpus gains a reserved word, so anything using a variable literally named `TIME`
changes meaning — a *faithful* change, but it must be seen).

---

## 7. Implementation order

1. Token + `kwtable` entry; prove crunch/`LIST` on the repack build (no
   dispatch yet — an unknown token is a clean syntax error).
2. `ev_f_time` (read) + its gate rows.
3. `ex_time_assign` (write) + the conversion and error rows.
4. `di`/`ei` (D-TIME-2).
5. Retire the "no `TIME` on the zerobas side" probe rule in
   [`spec-traps-t3-key.md`](spec-traps-t3-key.md) §4.2 and re-enable
   `TIME`-bounded observation windows in the harness.

Steps 2–4 are blocked on **D-TIME-4** (funding). Step 1 is not: measure it first,
because it is the cheapest way to learn whether the estimate in §4 is honest.
