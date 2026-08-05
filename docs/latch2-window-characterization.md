# The second latch window — every reading, D-LATCH2

Companion to [`docs/spec-probe-latch2.md`](spec-probe-latch2.md). Everything
below was measured on `53825bf` (tree clean, `make -q build/zerobas-main-eu.rom`
exit 0, `make repack-machine` run first). Subject
`C-BIOS_MSX1_EU_REPACK_DISK`. The reference is **not driven** — see §11.

---

## 1. The map

`$009F` holds `C3 8F 11`. Forty bytes read from `$118F` on the subject machine:

```
cdc2fde5d52afaf3ed5bf8f3e72004fb7618f27ef5237dfe18200321f0fb22faf3f1d1e1c9e5d5c5
```

decoded one instruction for one against `chget` in C-BIOS's own **source**
(`~/projects/cbios/src/main.asm:1691`, pinned `v0.29-3-gb5ad9cb`). No reference
ROM was disassembled [[no-reference-rom-disasm]].

```
$11A2  chget_char    7E            ld a,(hl)          ; HL = (GETPNT)
$11A3                F5            push af
$11A4                23            inc hl
$11A5                7D            ld a,l
$11A6                FE 18         cp $18             ; low byte of KEYBUF+40
$11A8                20 03         jr nz,chget_nowrap
$11AA                21 F0 FB      ld hl,KEYBUF
$11AD  chget_nowrap  22 FA F3      ld (GETPNT),hl
$11B0                F1            pop af
$11B1                D1            pop de
$11B2                E1            pop hl
$11B3                C9            ret
```

The source carries its own note on the `cp $18`: tniASM and SjASM disagree about
`&`/`AND`, so C-BIOS hardcodes the low byte of `KEYBUF + 40`. That constant is
in the gate's signature, so the signature vouches for the **sysvar contract**
(`KEYBUF $FBF0`, `GETPNT $F3FA`) as well as for the addresses.

🔴 **The window as filed was `$11A2`–`$119D`, which is not a range** — its second
endpoint is below its first. Measured, it is **`$11A3`–`$11AD`**, and `$11A2`
is on the *safe* side (§4).

## 2. The instrument: the precondition is manufactured, not waited for

D-LATCH measured the buffer **drained before 2039/2039** injections and D-DELIVER
before 490/490, because a `step` is three orders of magnitude longer than a line
takes to consume. Waiting for a non-drained buffer is hopeless.

`chget_char` is reached only when `rst $20` said `HL != DE` at `$119B` — i.e.
**only when `GETPNT != PUTPNT`**. So a breakpoint inside it *is* the
precondition: manufacture and force are the same instrument. One atomic callback
arms `debug set_bp` and then injects a predecessor; the CPU resumes, enters
`chget_char`, and hits the breakpoint once per consumed character. A hit counter
picks the `k`-th.

⚠️ **The precondition is still read, never assumed.** `fire` records `reg pc`,
`reg hl`, `A`, `GETPNT` and `PUTPNT` before writing a byte. Every row below
carries its own proof that the buffer was non-drained *at that instant*; a row
that measured a drained buffer is scored as measuring nothing.

**Readout.** The predecessor is ten spaces, which the tokeniser skips, so the
already-consumed prefix is invisible and the payload `54321 PRINT"X"` reports its
own damage as a **line number**: swallow 0 → `54321`, 1 → `4321`, 2 → `321`,
3 → `21`, 4 → `1`, ≥5 → `''`. Read off `__lines`, the standing stored-program
oracle — no new oracle, no screen decoding. The screen is captured as a second
opinion only [[readout-blind-to-its-own-subject]].

## 3. The discovery run — not a prediction

Breakpoint `$11A3`, hit 1, the **shipped** `key_proc`:

```
pc 11A3   hl FBF4   a 32   getpnt FBF4   putpnt FBFF   chain 4321
screen:   ZB 4321 PRINT"X"
```

Eleven bytes pending, `HL == GETPNT`, and the injector D-LATCH shipped **lost the
head of the line**. Everything in §4–§7 was written into the spec before it ran.

## 4. M1 — the boundary walk, `k = 1`, both injectors

**18 rows, 18 predicted correctly.**

| bp | instruction | `key_proc` | `OLD_KEY` | HL (new/old) | pending |
|---|---|---|---|---|---|
| `$11A2` | `ld a,(hl)` | **`54321`** ✅ | **`54321`** ✅ | `FBF4`/`FBF0` | 11 |
| `$11A3` | `push af` | **`4321`** ✅ | **`4321`** ✅ | `FBF4`/`FBF0` | 11 |
| `$11A4` | `inc hl` | **`4321`** ✅ | **`4321`** ✅ | `FBF4`/`FBF0` | 11 |
| `$11A5` | `ld a,l` | **`4321`** ✅ | **`4321`** ✅ | `FBF5`/`FBF1` | 11 |
| `$11A6` | `cp $18` | **`4321`** ✅ | **`4321`** ✅ | `FBF5`/`FBF1` | 11 |
| `$11A8` | `jr nz` | **`4321`** ✅ | **`4321`** ✅ | `FBF5`/`FBF1` | 11 |
| `$11AD` | `ld (GETPNT),hl` | **`4321`** ✅ | **`4321`** ✅ | `FBF5`/`FBF1` | 11 |
| `$11B0` | `pop af` | **`54321`** ✅ | **`54321`** ✅ | `FBF5`/`FBF1` | 10 |
| `$11B3` | `ret` | **`54321`** ✅ | **`54321`** ✅ | `EB00` (popped) | 10 |

Three of the nine boundaries are **GREEN**, and they are the reason the other six
mean anything: a walk in which everything mangles proves only that the machine
dislikes being interrupted.

* `$11A2` is safe because `ld a,(hl)` has not run: `HL == GETPNT`, the payload
  was written *at* `GETPNT`, so the CPU reads `payload[0]` and stores `GETPNT+1`.
* `$11B0`/`$11B3` are safe because `ld (GETPNT),hl` has already run — `pending`
  drops from 11 to 10 at exactly that boundary, which is the write-back visible
  in the readout.

## 5. M2 — the swallow law: the two injectors are NOT equally wrong

`k = 4`: three predecessor characters already consumed.

| bp | `key_proc` | `OLD_KEY` |
|---|---|---|
| `$11A2` | **`54321`** ✅ swallow 0 | **`21`** ✅ swallow 3 = `k-1` |
| `$11AD` | **`4321`** ✅ swallow **1** | **`1`** ✅ swallow 4 = `k` |
| `$11B0` | **`54321`** ✅ | **`54321`** ✅ |

> **`key_proc` swallows exactly 1, independent of `k`. `OLD_KEY` swallows `k`.**

🔴 The swallow on file for this window — `HL - KEYBUF + 1` — is `OLD_KEY`'s. It
is not the shipped injector's, and no arithmetic anywhere on file predicted
**1**. A filed claim is an unverified claim, and this is the third slice running
in which one of them was load-bearing and wrong [[filed-justification-is-a-claim]].

### 5.1 M3 — the precondition, and two predictions of my own that missed

| # | predicted | measured |
|---|---|---|
| M3a | `GETPNT != PUTPNT` at every recorded hit | ✅ **28/28 non-drained**, zero exceptions |
| M3b | `PUTPNT - GETPNT == 12 - k` | ⚠️ **partial** — exact at `$11A2`–`$11AD` (11 at `k=1`, 8 at `k=4`); **`11 - k`** at `$11B0`/`$11B3` |
| M3c | `HL == GETPNT` at `$11A2`–`$11A4`, `+1` from `$11A5` | ✅ exactly |
| M3d | `A == 32` at every boundary from `$11A3` on | 🔴 **WRONG** — 32 at `$11A3`, `$11A4`, `$11A5` and again at `$11B3`; `$F5`/`$F1` (i.e. `L`) at `$11A6`, `$11A8`, `$11AD`, `$11B0` |

**M3b's miss is the mechanism, not noise.** The pending count drops by one at
precisely the boundary where `ld (GETPNT),hl` executes — the off-by-one *is* the
write-back, showing up in an independent reading.

🔴 **M3d was simply wrong, and the correction sharpens the story.** I predicted
the delivered character sits in `A`. It does not: `push af` at `$11A3` puts it on
the **stack**, `ld a,l` at `$11A5` overwrites `A`, and `pop af` at `$11B0`
restores it — which is why `A` reads 32 again at `$11B3`. The stray leading
character therefore survives *anything* the injector does to memory. That is why
§7's fix targets the precondition and not the payload.

## 6. M4 — the wrap sub-window that D-LATCH's fix OPENED

31 spaces + CR walks `GETPNT` to `$FC14`, so the predecessor's 4th character sits
at `$FC17` and `inc hl` there takes the `ld hl,KEYBUF` path.

| row | bp | injector | predicted | measured |
|---|---|---|---|---|
| M4a | `$11AA` | `key_proc` | `4321` | ✅ **`4321`**, `HL $FC18`, `GETPNT $FC17`, `PUTPNT $FBF7` |
| M4a' | `$11AA` | `OLD_KEY` | never hit | ✅ **`hits_total 0`** — structurally unreachable |
| M4b | `$11AD` | `key_proc` | `4321` | ✅ **`4321`**, `HL $FBF0` (the KEYBUF reload) |

`OLD_KEY` resets `GETPNT := KEYBUF` on every injection and a payload is at most
39 B, so its consuming pointer can never cross `KEYBUF + 40`. **The injector
D-LATCH shipped to close the first window opened a sub-window its predecessor
could not reach.** `PUTPNT $FBF7 < GETPNT $FC17` in M4a is the non-drained
reading across the wrap.

⚠️ M4a' is recorded here and is deliberately **not** a gate row: a row whose
prediction is "zero observations" passes just as happily when the probe is
broken.

## 7. The fix, and what it costs

> **The injector may not write into a buffer the machine is still consuming.**

`__key` reads `GETPNT` and `PUTPNT`; while they differ it defers itself by
`KEY_DEFER_STEP` (2 ms emulated), up to `KEY_DEFER_MAX` (40) attempts, and only
then injects anyway. `::__zbdefer` / `::__zbforced` count the two paths.

### 7.1 F1/F2 — forced at every boundary that was fatal

**22 rows, 22 predicted correctly.**

| rows | predicted | measured |
|---|---|---|
| the 6 fatal boundaries, `k=1` | `54321` | ✅ 6/6, **3 deferrals** each |
| `$11AD` at `k=4` | `54321` | ✅ **2 deferrals** |
| the 3 safe boundaries | `54321` | ✅ 3/3 |
| the wrap sub-window (`$11AA`, `$11AD`) | `54321` | ✅ 2/2, 2 deferrals |
| **K1 ctrl** — the FROZEN pre-fix body, same session, same boundaries | `4321` | ✅ **7/7 still mangle** |
| **K1 ctrl** — the frozen body on the 3 safe boundaries | `54321` | ✅ 3/3 |

**100 % → 0 % on every fatal boundary**, and `forced = 0` throughout: the bound
was never exhausted. The K1 control is what makes that a claim rather than a
hope — the fault reproduced in the same session that shows it fixed
[[knife-runner-false-negatives]].

### 7.2 Pricing the bound — measured, not assumed

The worst case is a property of the **buffer**, not of usage: 40 circular bytes
hold at most 39 (`MAX_DIRECT` + CR).

| pending line | deferrals | emulated |
|---|---|---|
| 11 B | 3 | 6 ms |
| 20 B | 6 | 12 ms |
| **39 B — the buffer's maximum** | **10** | **20 ms** |

The first bound tried was 16 × 2 ms = 32 ms, which measurement showed was only
**1.6×** the worst case. It is 40 × 2 ms = **80 ms**: 4× the measured worst case,
and 10 % of `ECHO_GAP` (0.8 s), the point at which the echo guard dumps the
screen to judge a line — a deferral near *that* would make the echo guard judge a
line that had not landed yet.

⚠️ **The bound is load-bearing.** `omsx_repl.py:133` records a standing contract:
during a cassette LOAD/SAVE the harness keeps injecting for 10–30 emulated
seconds while the machine is not reading the keyboard, and each `__key`
overwrites what is pending. An unbounded wait would turn that documented collapse
into a hang. Exhausting the bound is not a failure mode — it injects anyway,
which is byte-for-byte what shipped for the whole D-LATCH era.

### 7.3 Why a drained buffer costs nothing

On a drained buffer the guard's branch is not taken, so the emitted Tcl does
exactly what it did before plus **one extra `debug read memory`**, which costs
zero emulated time and cannot move an alignment
[[apparatus-is-part-of-the-measurement]]. The corpus in §10 is what prices that
claim, and nothing moved.

## 8. The knives

| knife | cut | predicted | measured |
|---|---|---|---|
| **K1** | the fix, forced at the fatal boundaries | `54321` | ✅ §7.1, with the frozen body still mangling in the same session |
| **K2** | drain guard **gutted** — condition evaluated, result discarded | rows E red | ✅ **13/16, exit 1**, and rows A/B/C/D/F unmoved |
| **K3** | row D handed the **fixed** injector (subject removed) | rows D red | ✅ **13/16, exit 1** |
| **K4** | `chget_char` signature set to `deadbeef` | refuses to judge | ✅ `latch-check: CANNOT JUDGE -- chget_char (0x11a2) reads '7ef5…', not the 'deadbeef' this gate was written against`, non-zero |
| **K5** | retry bound set to **0** | rows E red | ✅ **13/16, exit 1** |

K2 and K3 are the pair that matter. **K3 is the K2-shaped one**: emission, call
site and judgement all intact, only the *subject* removed — the failure a
coverage check cannot see, and the reason row D is scored rather than merely run.
**K5 proves the deferral is what delivers**, not the mere presence of the read:
a guard that looks and then injects anyway is exactly as broken as no guard.

A sixth cut was run against the **host** test rather than the gate: gutting the
same condition turns `tests/test_key_drain_guard.py` red on
`compares the two pointers`, so the invariant is pinned twice — once on the
machine, once without one.

## 9. The gate

`make latch-check`, 16 rows, **3.1 s**. Rows A/B/C are D-LATCH's, unchanged and
still 9/9. Rows D/E/F are new:

```
latch-check: chget $118F  chget_wait $1194  trigger $1197
latch-check: chget_char $11A2  window $11A3-$11AD
  PASS  D  D-LATCH injector, forced at $11A3 (push af) -> MANGLED (swallow 1, chain '4321', frozen body, no drain guard)
  PASS  D  D-LATCH injector, forced at $11AD (ld (GETPNT),hl) -> MANGLED …
  PASS  D  D-LATCH injector, forced at $11AA (ld hl,KEYBUF (wrap)) -> MANGLED …
  PASS  E  key_proc,          forced at $11A3 (push af) -> DELIVERED (swallow 0, chain '54321', 3 deferrals)
  PASS  E  key_proc,          forced at $11AD … -> DELIVERED (…, 3 deferrals)
  PASS  E  key_proc,          forced at $11AA … -> DELIVERED (…, 2 deferrals)
  PASS  F  D-LATCH injector, forced at $11B0 (pop af) -> DELIVERED …
latch-check: 16/16 rows
```

* **Row D is the anti-vacuity clause, one era later.** `GETPNT_KEY` is the
  D-LATCH injector frozen verbatim — verified character-identical to the
  `key_proc()` shipped at `53825bf` — kept because fixing a fault removes the
  only subject its gate has [[fixing-the-fault-silences-the-control]]. That is
  the trap D-LATCH walked into with the delivery oracles and the reason row A
  exists; row D is the same device for the second window.
* **Row E's `deferrals` count is the anti-vacuity clause for the guard itself**:
  green because the guard *fired*, not because the boundary was missed.
  Without it, K5 (bound 0) would have passed.
* **Row F is the far-side GREEN control** — one instruction past the store, the
  *same frozen injector* delivers. Without it, rows D would be consistent with
  "injecting into a buffer that is being consumed always breaks", which is the
  wrong conclusion and would have pointed at a different fix.

### 9.1 🔴 The gate's cost on file was stale by 13×

D-LATCH's spec §5 and characterisation §8 both say *"nine boots, ~40 s"*. Timed
today with HEAD's own `latch_check.py`, stashed clean: **2.05 s**. The
sixteen-row version is **3.1 s**.

That figure is not idle. **My own §5.7 predicted ≈20 s for 15 rows** — inherited
straight from the stale per-boot number, and wrong by 6×, while writing a slice
that cites [[stale-cost-estimate-defers-gates]]. The lesson is not "re-measure
before skipping a gate", it is that a stale figure propagates into every estimate
that trusts it, including the ones written by someone who knows better.

## 10. Corpus

Sequential, no two emulator gates at once, all exit 0, and **zero `MIS-ECHOED`,
`MIS-DELIVERED`, `ORACLES DISAGREE` or `APPARATUS FAILURE` lines anywhere**:

`unit-test` **58/58** (57 + the new file) · `preflight-check` 0 unguarded ·
`injector-check` 0 offenders / 257 files · `deadcode` 0/0 · **`latch-check`
16/16** · `graphics-acceptance` **PASS** (290) · `direct-ctrl` **40/40** ·
`diskbasic-acceptance` **34/34** · `input` ALL PASS · `input-devices` **50/50** ·
`linemax` **60/60** + `CAS=1` **3/3** (the cassette rows, i.e. the one documented
non-drained path) · `lnblank-acceptance` `REPEAT=2` **536/536, allowlist empty** ·
`string` · `error` · `float` · `math` · `missing` · `width` · `array` 151/151 ·
`time`. **No ROM rebuilt; `make -q build/zerobas-main-eu.rom` exit 0 throughout.**

### 10.1 The corpus found a false positive in a *different* gate

`make injector-check` went **red on `tests/test_key_drain_guard.py`** — the host
test added by this slice. It emits no Tcl and boots nothing: its
`debug write memory` is the **needle of a regex** asserting that `key_proc()`
does *not* write `GETPNT`, and it names the cursors because those are the
addresses it checks. **A gate that detects injectors classifies its own detector
as one.** Fixed as a fourth named structural exemption, in the mechanism that
gate already provides — not by renaming the needle to slip past it, which would
have left the next reader unable to tell evasion from innocence. Same class, and
found the same way, as D-ECHO's four
[[echo-guard-false-positives-found-by-corpus]].

🔴 **CLOSED 2026-08-05 BY D-INJSINK** ([`docs/spec-probe-injsink.md`](spec-probe-injsink.md)),
**and both claims above were wrong.** The exemption was not forced — the write
format belongs to `omsx_repl`, and naming its `tcl_writes()` predicate leaves
this test `CLEAN` on the literal rule. And "emitted vs matched against" is the
wrong axis: the test's *docstring* is a WRITE-bearing literal too, so a sink
whitelist does not clear it. What the false positive was hiding is a false
negative — `import latch_check; return latch_check.OLD_KEY` shipped the
pre-D-LATCH injector verbatim past this gate, `ALL PASS`, rc 0.

### 10.2 `lof-acceptance` did not drift

D-LATCH recorded one unreproduced `ORACLE DRIFT` (`wm_app_put`, recorded 61, live
`None`) and D-LASTINJ did not run the suite. Run here: **45 cases, 0 unfiled
divergences, 0 oracle drifts, 0 mangled, exit 0** — a fifth consecutive clean
run. Still a flake, still not written off.

## 11. Open

* **The reference is an outcome control only.** Locating `chget_char` in a
  Philips VG-8020 needs a disassembly this project does not do
  [[no-reference-rom-disasm]]. The guard shipped here is portable *because* it
  reads two published sysvars rather than testing a PC range — a PC test would
  have been subject-only by construction.
* **The residual, stated exactly.** The window needs a non-drained buffer; the
  guard defers while non-drained; the bound is 4× the buffer's own worst-case
  drain. What survives is: a machine still non-drained after 80 ms — i.e. one
  that is *not consuming*, and therefore not inside `chget_char` — whose final
  attempt nonetheless lands in an 11-byte window. That is not zero, and it is not
  reachable by the states the tape contract describes.
* **Both delivery oracles now have no standing reason tied to *this* window.**
  D-LATCH kept them armed explicitly because §2.5 was open; it is closed. They
  stay armed anyway, and §12 of the spec says on what grounds.
