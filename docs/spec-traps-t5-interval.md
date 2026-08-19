<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# Spec — interrupt traps **T5: `ON INTERVAL=n GOSUB` + `INTERVAL ON|OFF|STOP`**

Status: **✅ LANDED + GATED 149/149, and it FITS as of `a5a3af2`.** D-T5-2 signed
off; D-T5-1/3/4/6 adopted as recommended; D-T5-5 answered by the structure (§6).
As-built in §4.3, §5.1 and §6.1.

⚠️ **It did not fit when it landed, and that history is the point of §4.3.** For
several commits this spec read "IMPLEMENTED AND GATED 149/149, BUT THE TREE IS
14 B OVER THE PAGE-1 CEILING — `make basic-reloc` FAILS": the slice was
behaviourally complete with a green gate on both machines while **not fitting
beside `TIME`**, because the SAVE-family carve funded two of three needs, not
three. The 14 B were reclaimed not by §4.3's recommended `ON|OFF|STOP` decode
share — **that carve is still available and unspent** — but by the direct-mode
control-flow slice ([`spec-basic-direct-ctrl.md`](spec-basic-direct-ctrl.md)
§Cost). Page-1 free is now **8 B**, low region 5 B, from a clean build.

Two things worth carrying forward: **a green gate says nothing about whether the
bytes fit**, and the overrun hid for several commits behind **warm-tree** builds
reporting 55 B free — only `rm -rf build && make basic-reloc` measures the wall.
**With T5 landed the interrupt-trap arc closes for the second time — honestly.**
The fifth and last slice of
the interrupt-trap arc, after [T1 STOP](spec-traps-t1-stop-reslice.md) ·
[T2 STRIG](spec-traps-t2-strig.md) · [T3 KEY](spec-traps-t3-key.md) ·
[T4 SPRITE](spec-traps-t4-sprite.md). Arc spec:
[spec-basic-interrupt-traps.md](spec-basic-interrupt-traps.md) — **read its §0
first**, it is the retraction that reopened the arc.

Funded by the D-FUND-1 SAVE carve —
[decision-fund-time-and-t5.md](decision-fund-time-and-t5.md), which sized ONE
carve against this slice and `TIME` together and delivered +310 B for the two.

---

## 0. Why this slice exists, and what it is NOT

On 2026-07-24 the arc recorded `INTERVAL` as MSX2-only and re-sliced around it.
That was wrong: **the measurement was right and the inference was wrong**
(arc spec §0). `INTERVAL` is a *reserved-word compound* — `INT` + the literal
bytes `"ER"` + `VAL` — so it never had a keyword-table entry to be missing from,
and it works on the VG-8020.

Three consequences shape this packet:

1. **No token, no `kwtable` row, no crunch work.** zerobas already crunches
   `INTERVAL ON` and `ON INTERVAL=10 GOSUB 100` byte-identically to the
   reference, because it already has `INT` and `VAL`. Re-verified 2026-07-26.
2. **No RAM work.** `ZTI_INTERVAL = 0`, `ZINTVAL` and `ZINTCNT` are already
   equated in [`basic/sysvars.inc:1123,844,845`](../basic/sysvars.inc) and already
   cleared by `trap_init`. They were allocated for INTERVAL as the original T1
   and never re-used.
3. **A poll stanza already existed and was deleted.** `7a91fd1` wrote it;
   `00a593a` removed it to fund T2, with a comment calling it "provably dead".
   It is recoverable verbatim, and §2.1 below is that code — **with two
   corrections that measurement, not review, produced.**

Out of scope: MSX2 `INTERVAL` granularity (there is none to defer — the MSX1
model *is* the 1/frame model).

---

## 1. Oracle characterization (Philips VG-8020, 2026-07-26)

All of §1 is black-box measurement, reproduced by
[`probes/basic/basic_probe_interval_trap.py`](../probes/basic/basic_probe_interval_trap.py).
Every reading is gated on a `done` sentinel; a program that errored out or was
still running at the deadline is a FAILURE, never a zero.

**The apparatus point that shapes the whole probe:** every observable here is a
jiffy count, and the TIME session established that *a batched harness makes a
confound REPRODUCIBLE — repetition does not average it out*. So the period is
**measured between two fires**, not counted over a window: the handler stamps
`JIFFY` at fire #1 and at fire #1+span, and the reading is `(J2−J1)/span`. A
window count carries ±1 frame of pure phase noise; the difference-of-timestamps
form carries ±1/span. The first run used span=10 everywhere and read n=5 as
`4.9` — one frame of endpoint jitter, indistinguishable from a real 4.9. Cases
that *measure* a period now widen span until the jitter is an order of magnitude
below the answer.

### 1.1 The period is exactly `n` frames `[PIN]`

| case | n | window | fires | measured period (span) |
|---|---|---|---|---|
| `A1_n1` | 1 | 120 | 125 | **0.967** (30) |
| `A2_n5` | 5 | 340 | 68 | **5.000** (60) |
| `A3_n10` | 10 | 340 | 34 | **9.967** (30) |
| `A4_n20` | 20 | 340 | 17 | **20.000** (16) |

Exact 1/n, and the window counts agree independently (340/5 = 68, 340/10 = 34,
340/20 = 17). **`n = 1` fires every frame** — the trap has no floor above one
frame, which bounds the design: the counter is a plain per-frame decrement.

### 1.2 The `n` domain is the **address domain**, and that is a finding `[PIN]`

| `n` | reference |
|---|---|
| `0` | **ERR 5** (illegal function call) |
| `255` | accepted — 2 fires in a 700-frame window, so it really is a 255-frame period and not a silent disarm |
| `256` / `32767` / `32768` / `65535` | accepted, no error |
| `−1` / `−32768` | accepted, no error |
| `2.7` | accepted, period **1.983** (span 60) ⇒ **2** — truncates toward zero |
| `65536` / `−32769` / `−65531` | **ERR 6** (overflow) |

That is **exactly** the conversion `TIME=n` needs and `POKE` already performs:
`fac_to_int_addr` → `domain_convert_core` in address mode — domain −32768..65535,
wrap by −65536 above 32767, then truncate toward zero, ERR 6 outside
([spec-basic-time.md](spec-basic-time.md) §1.3). `−65531` is the decisive case:
under a raw mod-65536 reading it would be a legal 5-frame period and fire 68
times; it raises **ERR 6** instead.

⇒ **The two threads this session funds together share a routine, not just a
wall.** T5's argument conversion is `TIME=n`'s conversion plus one zero test.

### 1.3 Arm, enable, suspend `[PIN]`

| case | reading | conclusion |
|---|---|---|
| `B_armed_not_on` — `ON INTERVAL=10 GOSUB h`, no `INTERVAL ON` | 0 fires | **arm ≠ enable** |
| `C1_off` / `C2_stop` | 0 / 0 | neither fires |
| `E_no_handler` — `INTERVAL ON` with nothing armed | no error, 0 fires | **silently accepted** |
| `G_stop_latch` — 1 fire, STOP for 300 frames (5 periods), re-`ON` | 2 in the next 60-frame window | STOP **remembers** |
| `H_off_latch` — same with `OFF` | 1 | OFF **forgets** |
| `G2_stop_release` — STOP for 3 whole periods, re-`ON`, read after **8** frames | **1** | exactly **one** event is latched, never three |
| `H2_off_release` — same with `OFF` | **0** | `OFF` clears PENDING |

`G2`/`H2` are what make this decisive: the window after re-enabling is far
shorter than one period, so anything counted there can only be a latch releasing.
The family answer (`STOP` latches one, `OFF` forgets) is **identical to T1–T4** —
no INTERVAL-specific state machinery.

### 1.4 Where the period is counted from `[PIN]`

Three cases, each a two-way discriminator:

| case | shape | reading | conclusion |
|---|---|---|---|
| `P_on_reloads` | n=300; ON, 200 fr, STOP, 200 fr, ON, 200 fr | **2** fires | the counter **keeps running while STOPped**, and latches |
| `P2_rearm_reloads` | n=300; ON, 200 fr, re-arm, 200 fr, 200 fr | **1** fire (and 0 at the 400-frame mark) | **`ON INTERVAL=n GOSUB` RELOADS** the counter |
| `H3_off_reloads` | n=100; ON 250 fr, OFF, 30 fr, ON, 60 fr | **1** fire | `OFF`/`ON` do **not** reload |
| `S3_from_fire_or_return` | n=100, handler burns ~47 fr | gap **100.0**, not 147 | the period is counted **from the FIRE**, not from `RETURN` |

`P_on_reloads` is the one that corrects the deleted stanza: under "tick only
while state == ON" the reading would be **1**, and it is 2. The counter must run
while the trap is suspended.

### 1.5 A handler that outlasts its period STARVES the main program `[PIN]`

`S_starves_main`: n=20, handler burns ~47 frames. Inter-fire gap **47.2** — one
fire per handler completion, no queueing (there is only one PENDING bit; `G2`
already showed three elapsed periods release exactly one). And `$D00A`, poked 88
by the statement *after* the wait, reads **0**: the main program **never
resumed**, over 665 emulated seconds. `S2_fast_control` — the same program with
no burn — reads gap 20.0 and `$D00A = 88`.

This follows from §1.4: the counter reloads at the fire and keeps ticking through
the handler, so with `n` below the handler's length a period has *always* elapsed
by `RETURN` and the next statement boundary dispatches again, forever. It is
faithful behaviour, not a defect — but it is a **gate hazard**, and it is how two
earlier shapes of this case captured `done=0`.

> ⚠️ **The apparatus lesson, twice paid.** Both earlier shapes waited out the
> observation window **in the main program**, in frames. A slow handler takes
> exactly that away, so no deadline was ever going to be enough. The fix was not
> a bigger deadline but a different observable: **the handler does its own
> timing and sets `done` itself**, and whether the main program resumed becomes a
> *reading* ($D00A) instead of a timeout. Generalise: *when the feature under
> test can starve the main program, the main program cannot be the instrument.*

### 1.6 The parse surface `[PIN]`

| statement | reference |
|---|---|
| `ON INTERVAL=10 GOSUB` (no line) | **accepted** — and it **CLEARS the handler** (`R_bare_disarms`: 6 fires before, 0 after) |
| …then re-arm `ON INTERVAL=10 GOSUB 800` | fires resume (`R2_rearm`: 6 / 0 / 7) **with no second `INTERVAL ON`** |
| `ON INTERVAL=10 GOSUB:POKE…,77` | accepted, the `POKE` runs — the parser stops cleanly at `:` |
| `ON INTERVAL=10 GOSUB 777` (undefined line) | **ERR 8**, raised at ARM time |
| `ON INTERVAL=10 GOTO 800` | **ERR 2** |
| `ON INTERVAL GOSUB 800` (no `=n`) | **ERR 2** |
| `INTERVAL` (bare) | **ERR 2** |
| `INTERVAL FOO` | **ERR 2** |
| `INTERVAL ON:POKE…,77` | accepted, the `POKE` runs |
| `ON INTERVAL=Q GOSUB 800` (variable) | accepted, period 7.0 for `Q=7` — `n` is a full expression |

The bare-`GOSUB` disarm is the **same behaviour T4's family sweep found for
STOP/STRIG/KEY/SPRITE**, and it is the behaviour whose absence was a shipped T1
divergence (`f302d78`). zerobas's `trap_line_link` already has the CF=0 /
`ld de,0` path for it.

### 1.7 zerobas today — the divergence being closed

Every case measured on the repack build returns **ERR 2**, `done=1`
(`A3_n10`, `D0_n0`, `B_armed_not_on`, `L_syn_noline`, `J_syn_on_goto`,
`K_syn_bare`). `ON` peeks the token after it, sees `INT` rather than `ERROR`,
falls into the `ON…GOSUB` numeric path and fails on `INT` without a `(`.
So the divergence is **honest and loud**, not silent — unlike `TIME`.

---

## 2. The model

Nothing new. T5 uses the arc's `ZTRAP` machinery unchanged: entry
`ZTI_INTERVAL = 0`, the shared state byte / PENDING / SERVICING encoding, the
service stack and the `RETURN` re-enable, `set_state`, `ct_find`, `check_traps`,
`trap_line_link`. Priority falls out for free — `check_traps` scans ascending and
INTERVAL is index 0, i.e. **highest**, exactly the arc spec §5 enum order.

**No edge shadow.** `ZTS_SHADOW` (bit 6) stays unused for INTERVAL: the event is
generated, not sampled, so there is no level to de-bounce (same as SPRITE, for a
different reason).

### 2.1 The poll stanza — the deleted code, with two measured corrections

The `7a91fd1` original, recovered verbatim:

```
                ld      a,(ZTRAP)           ; INTERVAL entry state byte
                and     ZTS_STATE_MASK
                cp      ZTS_ON
                jr      nz,ep_done          ; OFF / STOP / SERVICING -> do not tick
                ld      hl,(ZINTCNT)
                dec     hl
                ld      (ZINTCNT),hl
                ld      a,h
                or      l
                jr      nz,ep_done
                ld      hl,(ZINTVAL)        ; reload the period
                ld      (ZINTCNT),hl
                ld      hl,ZTRAP
                set     7,(hl)              ; PENDING
                ld      a,1
                ld      (TRAPPEND),a
```

**Correction 1 — the tick gate is wrong (§1.4 `P_on_reloads`, §1.5).** `cp
ZTS_ON` freezes the counter while the trap is STOPped and while its handler runs.
Measurement says it must run in **both** states. The test becomes "armed and not
OFF": tick whenever `ZINTVAL ≠ 0`, and latch PENDING unless the state is `OFF`
(`ZTS_OFF == 0`, so the latch guard is `and ZTS_STATE_MASK / jr z,skip`). That is
the same shape, one comparison cheaper, and it is *why* `S_starves_main` starves.

**Correction 2 — the `event_poll` fast-out must know about INTERVAL.** The
current fast-out returns when `TRAPENA == 0 && TRAPSVC == 0`
([`basic/traps.asm:64-73`](../basic/traps.asm)). `TRAPENA` counts only **ON**
traps, so with INTERVAL the sole trap and it **STOPped**, both are zero, the poll
never runs and the counter freezes — which `P_on_reloads` falsifies. The gate
grows a third term: `ld hl,(ZINTVAL) / ld a,h / or l / jr nz,ep_live` (~7 B, one
16-bit RAM read per frame on the common path).

⚠️ This is the second time this arc's *deleted* or *inherited* code was correct
in shape and wrong in a state test, and both times only a run found it. The
stanza was called "provably dead" when it was removed; it is now provably
**wrong** in two places — but only against readings that did not exist then.

### 2.2 Parse

* **`ON INTERVAL=n GOSUB <line>`** — a sibling peek in `ex_on`. INTERVAL has no
  token of its own (§0), so the peek is on the compound: after `ON` (`$95`),
  match the six bytes `FF 85 45 52 FF 94` = `INT` (`$FF $85`) + the literal `"ER"`
  + `VAL` (`$FF $94`), as recorded in arc spec §0. That is a **6-byte literal
  compare**, not a `cp` — the one place T5 costs more than T1–T4 did, all four of
  which peek a single-byte or two-byte token. Then `=<expr>` via the
  ordinary int-arg path with `fac_to_int_addr` (§1.2) plus an `or a / jp z,` for
  ERR 5, store `ZINTVAL` **and** `ZINTCNT` (§1.4 `P2`), then the shared
  `trap_line_link` for the handler line — including its CF=0 clear-the-slot path
  (§1.6).
* **`INTERVAL ON|OFF|STOP`** — a new `ex_interval`, reached by the same compound
  match at statement level, then `ld a,ZTS_… / ld hl,ZTRAP / call set_state`,
  **no seed block** (§2, no shadow). Bare `INTERVAL` and `INTERVAL FOO` fall to
  the trappable `ld a,2 / jp raise_error` (§1.6).
* ⚠️ Per [[generalisation-not-free-at-two-callers]], if the `ON INTERVAL` body
  looks shareable with `ex_on_stop`/`ex_on_sprite`, **build both and measure** —
  the last two times this arc assumed sharing was cheaper the answer was 11 B in
  the other direction and the *duplicated* variant shipped.

---

## 3. Where the poll lives — page 1, and the T3/T4 argument does NOT carry over

T3 put the KEY handler in the **low region** because its event source fires from
inside C-BIOS's keyboard scan, which can land while a sub-ROM **page-1 tenant**
owns page 1 — and `htimi_guard` skips the seam for that frame, which for KEY
leaks an undiverted keystroke (a correctness failure, not a deferral). T4
followed for the same reason.

**INTERVAL has no such hazard.** Its source is the frame itself. A frame skipped
by `htimi_guard` costs one decrement, i.e. the period runs long by the length of
the tenant call — exactly the ≤1-frame deferral `htimi_guard` was written for and
already accepted for PLAY. So the stanza belongs in **page-1 `event_poll`**,
where the deleted original was.

⚠️ One consequence to state rather than discover: a program that spends most of
its time inside page-1 tenants (heavy `SIN`/`COS`, sub-ROM `PLAY` parsing, disk)
will see its INTERVAL period stretch. That is a **documented deviation**, and the
gate should measure it rather than assume it is small — the T4 probe's
`T_tenant` case is the pattern (a `SIN` loop inside the observation window).

---

## 4. Byte budget — ESTIMATE, and per the arc lesson a **LOWER BOUND**

| item | region | estimate |
|---|---|---|
| poll stanza (§2.1, the recovered code + correction 1) | page 1 | ~26 B |
| `event_poll` fast-out third term (correction 2) | page 1 | ~7 B |
| `ex_interval` (`INTERVAL ON/OFF/STOP`) | page 1 | ~24 B |
| `ex_on` compound peek (6-byte literal compare, ×2 sites) | page 1 | ~20 B |
| `ON INTERVAL=` arg: `fac_to_int_addr` + ERR 5 + store both cells | page 1 | ~18 B |
| **total** | **page 1** | **~95 B** |

The arc spec §10's figure was **48 B** for the stanza alone; this packet's 95 B is
the whole slice. Every estimate in this arc has come in low — T2 by 70 B, T3 by
106 B (1.8×) *while calling itself deliberately pessimistic* — so **treat 95 B as
a lower bound and budget ~170 B**.

### 4.3 ✅ AS BUILT — 196 B, and the lower-bound rule held for the sixth time

> ✅ **RESOLVED `a5a3af2`** — the 14 B were reclaimed by the direct-mode
> control-flow slice ([`spec-basic-direct-ctrl.md`](spec-basic-direct-ctrl.md)
> §Cost), **not** by §4.4's recommended `ON|OFF|STOP` decode share, which remains
> available and unspent. Page-1 free is now 8 B from a clean build. The 265 B
> as-built figure below is unchanged and still correct — what follows is the
> record of how it was mis-measured, which is the durable lesson.

🔴 **CORRECTED, and the correction is the point: 265 B, and the tree WAS 14 B OVER
the ceiling.** `check_reloc` on a CLEAN build: reloc size **22524** against the
22510 B that `$2812–$7FFF` holds. A clean build at the parent commit (`1addfbc`,
`TIME` landed, T5 not) measures **251 B free**, so T5 costs **265 B** — **2.8×**
the 95 B estimate, and 95 B more than the 170 B "budget on the lower bound"
figure. Low region untouched at 5 B (§3's page-1 argument held).

⚠️ **AND THE INCREMENTAL BUILDS LIED ABOUT IT ALL THE WAY.** `make basic-reloc`
reported 64 B free, then 55 B, while the same sources built from scratch overrun.
Every intermediate figure in this section's first draft (196 B, "55 B left") came
from a stale `build/` tree. **Only `rm -rf build && make basic-reloc` measures the
wall** — an incremental one can report headroom that a clean build does not have,
which is precisely the failure mode a byte-budget gate exists to prevent.
The arc's standing rule "MEASURE byte budgets before declaring a wall" needs the
corollary: *measure them from clean.*

Open: reclaim ≥14 B. The identified candidates, cheapest first —
**(a)** share the `ON|OFF|STOP` token decode and the `ld a,ZTS_*` triple between
`ex_interval` and `ex_stop` (they are token-for-token identical; ~14 B net, no
behaviour change, needs a `stop-trap-acceptance` re-run);
**(b)** route `ex_time_assign`'s ERR 2 to the existing `trap_syntax` (~3 B);
**(c)** D-TIME-2's `di`/`ei` guards (8 B) — pre-authorised by
[spec-basic-time.md](spec-basic-time.md) §5 as the first thing to drop if funding
lands tight, at the cost of a real (if unobservable) torn-access guard;
**(d)** a second carve. (a)+(b) is the recommendation: it gives the margin back
without giving up anything measured.

Where the 101 B over the estimate went, honestly:

| item | est | as built |
|---|---|---|
| poll stanza + fast-out term | 33 | ~44 — the fast-out had to be A-ONLY (§2.1) |
| `ex_interval` | 24 | ~46 — including the TRAPPEND re-raise (§4.2) |
| `ex_on` peek + `iv_match` + the 5-byte table | 20 | ~34 |
| `ON INTERVAL=` argument | 18 | ~30 |
| the second call site (`ex_ff_stmt`) | **0 — forgotten** | ~8 |

The last row is the honest one: the estimate costed *one* compound peek and there
are **two**, because `INTERVAL ON` is a statement and `ON INTERVAL` is a clause.
That is the shape of every underestimate in this arc — not a mis-priced item, a
missing one.

**Funding held comfortably**: the D-FUND-1 carve delivered +310 B, `TIME` took 81
and T5 took 196, leaving **55 B**. One carve did fund both, as §4 argued.

Both threads of this session are page-1 needs against **22 B free**. Funding is
the shared carve in [decision-fund-time-and-t5.md](decision-fund-time-and-t5.md),
sized against `TIME` **and** T5 together.

---

## 5. Gate — `make interval-trap-acceptance`

Built from §1's cases, asserting against the recorded reference values.
`probes/basic/basic_probe_interval_trap.py` already carries all of them and today
runs in reporting mode.

Split, following T3/T4:

* **equality differential** (machine-independent): every error code (`D0`=5,
  `D9`/`D11`/`D13`=6, `M`=8, `J`/`K`/`N`/`O`=2), every no-fire case
  (`B`,`C1`,`C2`,`E`), the release counts (`G2`=1, `H2`=0), the parse-stops-clean
  aux values (`Q`,`Q2`=77).
* **per-machine predicates** (fire counts are a function of how many frames fit
  in a window, and the two machines run BASIC ~7× apart): the measured **period**
  (`A1`..`A4`, `D7`, `S2`, `S3`) asserted against `n` with a tolerance of
  ±(1/span + 5 %), and the shape assertions for `R`/`R2` (fires → silent →
  fires again).
* **`S_starves_main` is a reading, not a timeout**: assert `done==1`,
  `gap ≈ handler length`, and `$D00A == 0`; `S2_fast_control` is its
  discriminating control and must read `$D00A == 88`.
* Add a **`T_tenant`** case per §3 before the gate is called complete.

Standing requirements, inherited: RAM sentinels only, every reading gated on
`done`, the counter saturates at 250, no string building, windows bounded by a
JIFFY delta and not by an iteration count. Once `TIME` lands (Thread A) the
"no `TIME` on the zerobas side" rule retires and these windows can be written the
natural way.

### 5.1 ✅ AS BUILT — `make interval-trap-acceptance`, 149 assertions, ALL PASS

Both machines, 42 cases. Beyond §4.2's defect, three cases had to be **re-sized
for the slow side**, and the reason is the same in each: the case's premise was
"the handler is cheap relative to the period", which is true on the VG-8020 and
false on a build that runs BASIC ~3× slower.

* **`A1_n1`** — at one fire per frame the handler *is* the frame, so the main
  program never resumes and a window-based case captures `done=0`. Rebuilt on
  the handler-sets-`done` shape (§1.5's own lesson, arriving uninvited) and
  asserted per-machine as "never faster than its period": reference 1.0,
  zerobas handler-limited above it.
* **`D7_nfrac`** — the truncate-vs-round question at n=2.7 is unanswerable on the
  slow side, where the measured gap is handler-limited (2.3). Moved to **20.7**:
  20 against 21, five per cent apart, measurable on both.
* **`S3_from_fire_or_return`** — its ~58-frame burn costs ~174 frames on the
  repack build, so n=100 did not fit and the slow side starved. n=**300** fits on
  both and the question is unchanged.

And the tolerance was tightened from `1/span + 5%` to `1/span + 2%`: at n=20 the
5 % term is ±1.0, **wide enough to accept 21 when the answer is 20** — i.e. wide
enough to accept rounding when the finding is truncation. *A tolerance that
cannot reject the rival hypothesis is not a tolerance.*

⚠️ **One apparatus fault cost a whole round and is worth naming: a STALE
MACHINE.** A mass of 32 cases came back `ERR 2` — the exact signature of
`INTERVAL` not existing — after an unrelated detour had repointed
`C-BIOS_MSX1_EU_REPACK_DISK` at a worktree ROM that was then deleted. The probe
names its machine by NAME and cannot see which ROM that name resolves to, so a
correct implementation read as completely unimplemented. **After any
`install-*-machine.py` detour, reinstall before trusting a reading** — this is
[[ips-rebuild-after-basic-change]]'s hazard in the other direction: not a stale
ROM behind a fresh machine, but a stale machine in front of a fresh ROM.

---

## 6. Decisions — all resolved

**D-T5-1 — the tick gate.** Adopt correction 1 (§2.1): tick whenever
`ZINTVAL ≠ 0`; latch PENDING unless the state is OFF. *Recommended* — it is what
`P_on_reloads`, `H3_off_reloads` and `S_starves_main` measure, and it is one
comparison cheaper than the deleted original.

**D-T5-2 — the fast-out third term. ✅ DECIDED 2026-07-26: PAY IT.** ~7 B and one
16-bit RAM read per frame on the common no-trap path, so the counter runs while
STOPped (§2.1 correction 2). The alternative — freezing the counter while
suspended — would have been a measurable divergence for ~7 B.

**D-T5-3 — `n` conversion.** Share `fac_to_int_addr` → `domain_convert_core`
(address mode) with `TIME=n` (§1.2), plus a zero test for ERR 5. *Recommended;*
this is the second consumer that makes the shared conversion worth its bytes, and
it argues for landing **`TIME` first** so T5 inherits a proven path.

**D-T5-4 — the page-1 poll and its stretch.** Put the stanza in page-1
`event_poll` (§3) and record the tenant-window stretch as a **documented
deviation**, measured by a `T_tenant` gate case rather than asserted to be small.

**D-T5-5 — parse sharing. ✅ ANSWERED BY THE STRUCTURE, not by a bake-off.**
`ON INTERVAL=n GOSUB` shares `ex_on_stop`'s tail from the line-reference onward
(a new `eos_line` label — **zero bytes**, since the store and the clear-the-slot
path are identical), and shares nothing before it, because everything before it
*is* the `=n` argument that STOP does not have. There was no fork to measure:
the shared part had no per-caller cost and the unshared part had no counterpart.
Both variants were built for D-T4's version of this question; here the answer
fell out of where the two grammars actually diverge.

**D-T5-6 — order.** `TIME` first (it is fully specced, its steps are small and
independent, and D-T5-3 rides on it), then T5. Both after the §4 carve.

---

### 6.1 🔴 THE ONE REAL DEFECT THE GATE FOUND — a latch that could never release

Three cases failed on the first honest run, all the same shape and all in the
STOP family: `G_stop_latch` (ref 2, zb 1), `P_on_reloads` (2/1),
`G2_stop_release` (1/0). zerobas latched the elapsed period correctly and then
**never released it**.

The bug is not in the latch and not in the state machine — both were right. It is
that **`check_traps` CLEARS `TRAPPEND` whenever it finds nothing firable**, and a
STOPped entry is not firable. So `event_poll` latches PENDING, raises TRAPPEND,
the dispatcher looks, finds nothing, and switches itself off; `INTERVAL ON` then
restores the state but the dispatcher has already been told to stop asking.

**T1–T4 never hit this because their event sources re-latch every frame while
ON**, which re-raises TRAPPEND on its own. INTERVAL's latch is a **one-shot** —
§1.3 `G2` measures three elapsed periods releasing exactly one — so it is the
first trap in the arc that has to re-raise TRAPPEND at the arming statement.
Ten bytes in `ex_interval`, guarded on `bit 7` so OFF (which clears PENDING) does
nothing. Counted in §4.3's `ex_interval` row.

*Generalise:* a one-shot latch and a level-sampled one need different wake-up
plumbing, and the difference is invisible until a case suspends the trap for
longer than one period and then re-enables it. That case existed only because §1.3
was written to distinguish "STOP remembers" from "OFF forgets".

---

## 7. Implementation order (after sign-off + funding)

1. `ex_on` compound peek + `ex_on_interval` (arm, `=n`, `trap_line_link`).
2. `ex_interval` (`ON`/`OFF`/`STOP`) via `set_state`.
3. The `event_poll` stanza + fast-out term (§2.1).
4. Fix the two stale comments in [`basic/traps.asm`](../basic/traps.asm) that
   still assert "INTERVAL is an MSX2 statement, out of charter" and cite the
   retracted memory.
5. Gate: `make interval-trap-acceptance`, then update
   [spec-basic-interrupt-traps.md](spec-basic-interrupt-traps.md) §0 and the arc
   status line — with T5 landed the arc closes for the second time, honestly.
