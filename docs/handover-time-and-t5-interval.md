<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# Handover — `TIME`/`TIME=n` **and** interrupt-traps **T5 `INTERVAL`**

Status: **HANDOVER BRIEF, 2026-07-26.** Two features are ready to be specced
into implementation, and they **compete for the same wall**. Deliverable of the
next session = a **funding decision** (a carve, measured and costed) plus a
signed-off **T5 packet**; then implementation. **No implementation before
sign-off** ([[spec-before-implementation]] — this brief is spec *input*, not a
green light).

Repository: `/Users/joost/projects/zerobas`, branch `main`, tree clean at
`60e0ab6`. Everything below is on main and gated green.

---

## 1. What just happened (four commits)

| commit | what |
|---|---|
| `d7cc556` | `TIME`/`TIME=n` characterized vs the VG-8020 (45/45) + [`docs/spec-basic-time.md`](spec-basic-time.md) DRAFT + [`probes/basic/basic_probe_time.py`](../probes/basic/basic_probe_time.py) |
| `7572345` | D-TIME-1 settled by measurement: `TIME` is **not** an MSX integer |
| `fa161cb` | D-TIME-1 narrowed (an over-claim of mine) + the unsigned-int alternative **costed** |
| `60e0ab6` | **RETRACTION: `INTERVAL` IS MSX1.** Trap arc reopened; [`spec-basic-interrupt-traps.md`](spec-basic-interrupt-traps.md) §0 is new |

---

## 2. Thread A — `TIME` / `TIME=n`

**Read the spec, not this summary:** [`docs/spec-basic-time.md`](spec-basic-time.md).
Characterization is **complete and gated**; §1 is all measurement.

Settled:

* Token `$CB`, single-byte, unused in zerobas. The sub-ROM `kwtable` is the sole
  source since wave 3 ⇒ one row buys crunch **and** `LIST` for **0 main-ROM bytes**.
* **Read** = `ev_f_erlfn` with `ld hl,(ERRLINE)` → `ld hl,(JIFFY)`. **17 B**,
  symbol-table measured. `ERL` is already the same unsigned-word-as-float problem.
* **Write** = the **house address-domain conversion, unchanged** (`fac_to_int_addr`
  → `domain_convert_core` mode 1, which `POKE` already calls): wrap by −65536 above
  32767, then truncate toward zero, ERR 6 outside −32768..65535.
* **Parse** = `g8_assign` (VDP/BASE) minus the parenthesised index — it already
  carries the ERR 24 missing-operand check and `str_eval_one`'s ERR 13.
* **D-TIME-1 closed** (`7572345`, `fa161cb`): float everywhere; integer is ruled out
  by measurement above 32767 and structurally below it (MSX has no unsigned VALTYP).
  The cheap `FACTYP=2` path (−11 B) is costed and rejected: it is signed, so
  `PRINT TIME` would render 40000 as −25536.

Open for sign-off: **D-TIME-2** (`di`/`ei`, 4 B), **D-TIME-3** (ERR 24 at `TIME`'s
own site — zerobas silently accepts bare `A=` today, a **pre-existing divergence
wider than `TIME`**, ~6 B to fix locally), **D-TIME-4** (funding).

**Budget: ~52–75 B, pure page 1.**

---

## 3. Thread B — T5 `INTERVAL` (newly back in charter)

**Read [`spec-basic-interrupt-traps.md`](spec-basic-interrupt-traps.md) §0 first** —
it is a retraction, and it explains why this slice exists at all.

* `INTERVAL` **is** MSX1. Measured on the VG-8020: `ON INTERVAL=n GOSUB` +
  `INTERVAL ON` fires 16 / 33 / 8 times for n = 10 / 5 / 20 over ~160 jiffies
  (exact 1/n); `OFF` / `STOP` / never-enabled → 0; `LIST` round-trips.
* It is **not a keyword** — it is a reserved-word compound `INT` + literal `"ER"` +
  `VAL` (`FF 85 45 52 FF 94`), like `MAXFILES` = `MAX`+`FILES`.
* ⇒ **zerobas already crunches it byte-identically today.** T5 needs **no token, no
  `kwtable` row, no crunch work.** Verified 2026-07-26.
* The mechanism was already specified: §5 (parse) and §6 (`event_poll` down-counter)
  were written for INTERVAL as the original slice T1, then orphaned. They were never
  wrong — re-read them rather than re-deriving.
* The landed T1–T4 skeleton (`ZTRAP`, the `H.TIMI` `event_poll` seam, `check_traps`,
  `RETURN` re-enable) is reused wholesale. `ZINTVAL`/`ZINTCNT` are already equated.

**Budget: the arc spec's §10 estimate was 48 B resident page-1 for the `event_poll`
stanza, plus a sub-ROM-tenant parse surface (off-budget). Treat 48 B as a LOWER
BOUND** — every estimate in this arc came in low (T2 by 70 B, T3 by 106 B = 1.8×).

**Owed: a signed-off T5 packet**, in the style of
[T2](spec-traps-t2-strig.md) / [T3](spec-traps-t3-key.md) / [T4](spec-traps-t4-sprite.md).
Characterization is *partly* done (the §0 table); a packet should add at minimum:
the `n` domain and its errors, `n=0`, re-arming after `RETURN`, `ON INTERVAL` with
no line (cf. T1's `f302d78` — a missing line **clears** the handler), interaction
with `STOP`/servicing, and whether the period counts from arm or from the last fire.

---

## 4. The coupling — this is the actual first task

**Both threads are page-1 needs, and page 1 has 22 B free** (low region 5 B).
Measured on the current tree by `make basic-reloc`.

* `TIME` ≈ 52–75 B · T5 ≈ 48 B+ ⇒ together **~100–125 B+**, all page 1.
* **Promotion cannot help.** It moves low → page 1, and low is the *emptier* wall
  ([[promotion-funds-low-region]] — the walls are coupled and low is at 5 B).
* ⇒ the lever is a **carve** ([[subrom-tenant-playbook]]): a page-1 cluster moved
  into the sub-ROM as a tenant.

**Recommendation: size ONE carve against BOTH needs, not two carves.** Funding them
separately repeats the T3 experience of paying the measure-and-classify cost twice.

Two hard-won rules for whoever picks the candidate:

1. **Choose the unit FIRST, by an external-caller census — not by file size.** The
   BLOAD carve gave three answers 3× apart (470 B "the file" / 149 B "the closure" /
   **381 B "the verb minus the shared service routines squatting in it"** — the
   correct one). `tools/carve_scout.py` reports the first two only.
   ([[traps-t3-key-slice]])
2. **The closure walk must continue THROUGH main page 1**, not stop at it — the slot
   config persists across that call ([[carve-scout-walk-through-page1]]). And never
   promote anything touching `$A8`/`CALSLT` on a bare scout verdict.

Also note the T3 finding that no *large* self-contained page-1 cluster remains: a
sweep of every `ex_*`/`do_*`/`cas_*`/`fat_*` page-1 entry for exclusive size found
nothing above 49 B. So the carve will be a **verb-with-shared-infrastructure**
shape, like BLOAD was.

---

## 5. Suggested order

1. **Fund first.** Pick + measure one carve covering ~125 B of page 1. Report the
   *measured* number with the tripwires lifted, not an estimate.
2. **Land `TIME`** — it is fully specced and its steps are small and independent.
   Spec §7 step 1 (token + `kwtable` row) is **not** blocked on funding and is the
   cheapest honesty check on the §4 estimate; do it first either way.
3. **Write + sign off the T5 packet**, then land it.
4. On landing `TIME`: **retire the harness rule "no probe program may use `TIME` on
   the zerobas side"** ([`spec-traps-t3-key.md`](spec-traps-t3-key.md) §4.2) and
   restore `TIME`-bounded observation windows — every gate since T3 has been sizing
   windows by iteration count because of this gap.

---

## 6. Two apparatus rules this pair of sessions added

Both are already enforced in `basic_probe_time.py`; carry them into the T5 gate.

* **A batched harness makes a confound REPRODUCIBLE — repetition does not average
  it out.** `JIFFY` ticks between `TIME=x` and the `PRINT TIME` reading it back, and
  in a batched run the phase is deterministic: 4/4 identical readings looked like
  solid evidence and were wrong. Fix = **deliberate phase shifts reduced by MIN**.
  This matters directly for T5, whose every observable is a jiffy count.
* **Marker-pair scraping needs an empty-span guard.** A case that errors mid-`PRINT`
  leaves its leading `#` on screen before the handler prints its own pair (`## 6 #`),
  so a naive *last*-span regex returns the **empty first pair** and a real ERR 6
  renders as a blank column. `_last()` takes the last **non-empty** span.

And the one from `60e0ab6`, which is the reason Thread B exists:
**"absent from the keyword table" ≠ "absent from the language."** A crunch probe
answers a *tokenisation* question; only running the feature answers a *support*
question.
