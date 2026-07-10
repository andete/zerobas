<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec — BASIC `INKEY$` (a Phase-3 string follow-on slice)

**Status: PROPOSED — S1 (spec + sign-off), awaiting decision on §6.** User-selected
2026-07-10 as the next Phase-3 session item, from the standing string-engine deferral list
([`spec-basic-string-engine.md`](spec-basic-string-engine.md) §1 "Out of scope";
[`spec-basic-string-functions.md`](spec-basic-string-functions.md) §1 "Out of scope":
"`INKEY$` (needs the keyboard/console read path — a different subsystem)"). This document
is the *how* + *decisions*, same shape as the engine / compare / functions specs.
**Repack-only**, like the whole string engine — the lean `basic.rom` stays byte-for-byte
unchanged (every byte is gated `IF ROM_BASE < $4000`).

`INKEY$` is the **first keyboard-reading string verb**. It is tiny in code (no arguments,
no parens, at most a one-byte result) but it crosses one seam the previous string slices
never touched: the **console input path** (BIOS `CHSNS`/`CHGET`), and therefore a new
*testing* wrinkle — the acceptance half must **inject a keystroke** (§5), not just read a
screen.

## 1. Goal & scope

Add `INKEY$` so loader stubs / games that poll the keyboard non-blockingly
(`10 A$=INKEY$:IF A$="" THEN 10`) work. It sits inside the proven string machinery (the
temp-string ring, the descriptor model, the `str_eval` dispatch) — no new RAM
architecture, no floats, no heap.

**In scope (the one verb):**

| Verb | Form | Sig | Returns |
|---|---|---|---|
| `INKEY$` | `INKEY$` (no args, no parens) | ()→s | a **0- or 1-character** string: the next key waiting in the keyboard buffer, or the empty string if none |

- Reached wherever a string expression is evaluated (`PRINT INKEY$`, `A$=INKEY$`, an `IF`
  condition, a function argument like `LEN(INKEY$)`), because the hook lives in the shared
  `str_eval_one` dispatch — the same reach the other string verbs already have.

**Out of scope (deferred, consistent with the engine):**
- The `MID$` *assignment statement*, `BIN$`, `LPOS`, and every other standing engine
  deferral (`INPUT`/`LINE INPUT` keyboard *statements*, floats in VAL/STR$, the real
  heap+descriptor model, string arrays / `DIM`, `STRMAX`→255).
- Any change to the **lean** build — no string engine there; every byte of this slice is
  gated `IF ROM_BASE < $4000`.

## 2. Behaviour (the contract)

Semantics come from the **public MSX-BASIC language reference**; the exact edge-case
behaviour is **oracle-confirmed black-box on the Philips VG-8020** in S2/S3 — the values
below are the expected contract, to be *confirmed against the reference*, never assumed.

- **`INKEY$` is strictly non-blocking.** It samples the keyboard **once** and returns
  immediately:
  - **No key waiting** → the **empty string** (length 0).
  - **A key waiting** → a **1-character string** holding that key's code, and the key is
    **consumed** from the buffer (a second immediate `INKEY$` returns empty unless another
    key has arrived).
- It does **not** echo the character to the screen (unlike the REPL line editor's
  `CHGET`+`CHPUT`).
- The character is whatever the console read path delivers — an ASCII byte for printable
  keys. Control keys pass through as their control code (own-design pass-through, D-5).
- The keyboard buffer is filled by the keyboard ISR, so `INKEY$` depends on interrupts
  being enabled (they are, in the running interpreter — [`interp.asm`](../basic/interp.asm)
  keeps `ei` so the keyboard ISR runs; no change needed).

## 3. Mechanism (the implementation shape)

`INKEY$` is a single-byte reserved-word token (D-3) dispatched from `str_eval_one`
([`strvar.asm`](../basic/strvar.asm)) exactly like `STRING$` (`$E3`), gated
`IF ROM_BASE < $4000`:

```
    IF ROM_BASE < $4000
                cp      STRING_TOKEN        ; $E3 -> STRING$(n,c)
                jp      z,str_fn_string
                cp      INKEY_TOKEN         ; $EC -> INKEY$ (no args)   [token confirmed S2]
                jp      z,str_fn_inkey
    ENDIF
```

The handler `str_fn_inkey` (in [`str-engine.asm`](../basic/str-engine.asm), the reloc-only
low region) is the smallest string verb yet:

1. `inc hl` past the token (no `(`/args to parse — the cursor lands on whatever follows the
   bare verb).
2. `call CHSNS` (`$009C`, a **published BIOS entry** — no disassembly) — sets **Z** if the
   keyboard buffer is empty, **NZ** if a key is waiting. `CHSNS` is non-destructive.
3. `call str_alloc_temp` → `HL` = temp descriptor base (the same ring slot allocator
   `SPACE$`/`STRING$` use).
4. **Empty path** (Z): store length `0`, `STRPTR ← HL`, done.
   **Key path** (NZ): `call CHGET` (`$009F`, published; non-blocking here because `CHSNS`
   already reported a key) → `A` = the char; store length `1` then the byte; `STRPTR ← HL`.
5. `jp str_eval_ok` (sets `VALTYP=1`, CF set — "this is a string operand").

Registers are guarded around the BIOS calls per the existing discipline (the string-eval
cursor is re-derived from the temp base, so no `HL` needs to survive `CHGET`; `str_alloc_temp`
clobbers `A`/`DE` — call it after `CHSNS`'s Z result is banked into a flag/branch, or push
the flag). Exact save/restore pinned in S2 against the working code, but the shape is: no
argument parsing, at most a 1-byte fill, one ring slot.

**New equate:** `CHSNS equ $009C` added to [`sysvars.inc`](../basic/sysvars.inc) beside the
existing `CHGET $009F` / `CHPUT $00A2`. All three are the standard MSX BIOS console entries
(MSX Assembly Page / MSX2 Technical Handbook jump table) — the same published source the
REPL's `CHGET`/`CHPUT` already cite. **No reference-ROM disassembly.**

## 4. Divergences (own-design, documented)

- **D-5 control-key pass-through.** zerobas returns whatever `CHSNS`/`CHGET` deliver,
  including control codes (e.g. Ctrl-STOP as `$03` when not trapped), without special-
  casing — mirroring the reference's "INKEY$ returns the raw code" behaviour. Any
  observed VG-8020 divergence on special keys is captured + documented in S2, not
  cargo-culted.
- **Lean build unchanged.** Every byte gated `IF ROM_BASE < $4000`; the shipping lean
  `basic.rom` stays byte-identical (verified in S3, as with every string slice).

## 5. Oracle & acceptance (the new testing wrinkle)

`INKEY$` is timing-dependent, so the acceptance is written to be **deterministic** via the
harness's keyboard-injection (`omsx_run.py --type STRING --type-delay SECS`, already used
by the crunch probe):

1. **Empty-string path** — run a program that reads `INKEY$` with **no key pending** and
   prints a marker proving it got the empty string (e.g.
   `10 IF INKEY$="" THEN PRINT "EMPTY"`). No injection needed; deterministic.
2. **1-char path** — run a bounded poll loop
   (`10 A$=INKEY$:IF A$="" THEN 10`, `20 PRINT "GOT ";A$`), then **inject a key** after a
   delay; the loop captures it and prints `GOT X`. Compared against the **real VG-8020**
   driven identically — the whole point of the oracle: same program, same injected key,
   byte-identical screen output.
3. **S2 crunch capture** — the `INKEY$` keyword's token is captured black-box on the
   VG-8020 crunch first (expected single-byte `$EC`; the `$` is part of the keyword, unlike
   `INPUT$` where `INPUT=$85` then `$`), then locked into the reloc-only kwtable — same
   procedure the other single-byte string verbs used.

**Standing gate.** `make string-acceptance` gains a **fifth half — `INKEY$`** (crunch +
execute + compare + functions + **inkey**), so the verb is regression-locked exactly like
the rest of the string engine. The emulator-free `unit-test` suite can cover the
descriptor-building logic (0-/1-byte result) if cleanly separable from the BIOS calls; the
BIOS-driven half stays in the openMSX probe (the string-functions slice showed the
execute+oracle half catches integration bugs the unit tests miss).

## 6. Decisions to sign off (S1 gate)

Recommended answers in **bold**; nothing is coded until these are accepted.

- **D-1 — Scope = `INKEY$` only** (one-verb slice). Small, self-contained, high-value for
  loader stubs / game key-polling; the natural next string item. *(Alt: bundle the `MID$`
  assignment statement too — rejected: that verb needs an lvalue-into-string-var path, a
  different and heavier subsystem; keep slices atomic.)*
- **D-2 — Non-blocking via `CHSNS` then `CHGET`.** Sample once; empty string if no key,
  1-char if a key is waiting; consume the key. The published INKEY$ contract; `CHSNS`
  (`$009C`) + `CHGET` (`$009F`) are standard BIOS entries (no disassembly).
- **D-3 — Single-byte reserved-word token** (the `$` is part of the keyword; expected
  `$EC`), dispatched from `str_eval_one` beside `STRING$`. **Confirmed black-box in S2**,
  not assumed.
- **D-4 — Result via the existing temp-string ring** (`str_alloc_temp`), a 0- or 1-byte
  descriptor. No `STRMAX` concern (≤ 1 byte). No new RAM.
- **D-5 — Control keys pass through** as their raw code (own-design; any VG-8020 special-
  key divergence documented in S2).
- **D-6 — Repack-only, lean byte-identical.** Everything gated `IF ROM_BASE < $4000`;
  ships in the merged `zerobas-main-eu.ips`/`.bps`.
- **D-7 — Acceptance = a fifth `INKEY$` half** of `make string-acceptance`, using keyboard
  injection (empty-path + injected-key-path, both differential vs VG-8020).

## 7. Plan (S1 → S3), one item per session

- **S1 (this doc)** — spec + scope + decisions → **sign-off**. No code.
- **S2** — oracle + implement: capture the `INKEY$` token black-box on the VG-8020 crunch;
  add the `CHSNS` equate + the `str_eval_one` dispatch hook + `str_fn_inkey`; lock the
  token into the reloc kwtable; unit-test the descriptor logic where separable; confirm the
  lean `basic.rom` stays byte-identical; first live run on the repack build.
- **S3** — acceptance + close-out: add the `INKEY$` half to `string_acceptance.py`
  (empty-path + injected-key-path, differential vs VG-8020); provenance entry in
  [`../basic/PROVENANCE.md`](../basic/PROVENANCE.md) → "Phase 3: INKEY$"; refresh the merged
  IPS/BPS; update `TODO.md` + memory; commit.
