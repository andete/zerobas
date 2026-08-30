# D-VALFLOAT — the plumbing for a float-capable VAL, and a night lost to sleep throttling

*2026-08-30. `sub/tkfloat.asm`, `basic/tokenise.inc`, `basic/sysvars.inc`.*

🟢 **SHIPPED — but held for an hour first, and the reason it was held turned out
to be the wrong diagnosis.**

Three batteries failed on it with `math-acceptance` refusing in 4 s and
`intarg-acceptance` in 0 s. I read that as host contention and withheld the
change, keeping the diff as a patch file. **Joost asked whether it was sleep
throttling instead, and he was right.** `pmset -g log` says:

- `Using BATT (Charge:100%)` — the machine is on battery, where macOS throttles
  and sleeps aggressively;
- `DarkWake to FullWake from Deep Idle` — it was in Deep Idle and woke on
  *keyboard activity*, not on anything the battery was doing;
- **`Total Sleep/Wakes since boot: 610`**, and `PreventUserIdleSystemSleep` held
  **only** by powerd *"while display is on"* — so once the display slept, nothing
  kept the system awake and the emulators were suspended.

🎯 **And the stall watchdog measures WALL CLOCK.** A suspended process burns wall
time without progress, which is precisely the signature it reported — *"989 s
wall, no emulated instant recorded"* — and its own message warns that a
host-clock deadline **cannot separate a frozen emulator from one starved of
CPU**. It was telling me the answer; I read "starved" and never considered
"suspended".

**`caffeinate -i make gates` → 47/47 green**, same change, same tree, one hour
later. [[apparatus-is-part-of-the-measurement]]

**Cost when applied: 65 B of sub page 0** (2203 → 2138 B free). Main regions
untouched. **Verified neutral by 59 host test files and `kwsweep`** — which is
what makes it re-appliable with confidence.

## 1. What this is, and what it is not

D-VAL's remaining 14 rows (fractions, exponents, `STR$` of a non-integer) need
`tk_float` — the tokeniser's own numeric scanner — to run over a *string body*
rather than a program line. Two things stand in the way, and this slice removes
both **without switching anything on**:

1. `tk_float` stops on a `0` byte, and a string body is not terminated.
2. `tk_float` does not `ret` — every exit is `jp tk_loop` / `jp tk_end`, back into
   the tokeniser loop it was called from.

The remaining piece — VAL actually calling it — is **not** here, for a reason
given in §4.

## 2. A bound, in the one place the source is read

🟢 **`tkf_fetch` is the only place `tk_float` reads the source.** The file's other
`ld a,(hl)` sites all read `TKDIG`, the internal digit array — an earlier draft of
D-VAL claimed seven source reads and five of those were that mistake.

⚠️ **It is a POSITION test, not a counter.** `tkf_fetch`'s own header calls the
accept/reject split "the whole rule": callers `push hl` and may `pop hl` to
**rewind** across a blank run they decided not to consume. A decrementing counter
would drift out of step with the cursor on every rejected run; comparing HL
against a stored end address cannot.

Out of bounds returns **exactly what a real `0` terminator gives** — `A = 0` and
the flags `cp ' '` leaves on it — so no caller's classification changes and no
caller needs to know the bound exists.

`TKVALEND = 0` means *unbounded*, and `tokenise` clears it on entry, so ordinary
tokenising can never see a bound even if cold-boot RAM garbage put one there.

## 3. Exits that return, at zero bytes

Every exit was already `jp tk_loop` (success) or `jp tk_end` (the `TKOVF`
reject), so re-pointing all six at `tkf_done`/`tkf_rej` **costs nothing** — the
instruction is identical, only the target changed. Those tails `ret` when
`TKVALEND` is set and otherwise jump where they always did.

🔴 **The `ret` is safe only in VAL mode, and that is why the test is on
`TKVALEND`.** In ordinary tokenising `tk_float` is reached by `jp tk_float` from
`tk_loop` and has no return address of its own.

⚠️ **A literal-text replace caught one short.** Retargeting by exact string
matched 5 of 6 `jp tk_loop`; the sixth hit in the original grep was a *comment*.
Verified after the fact by grepping for any surviving exit — the two that remain
are inside the new tails themselves. A missed exit would have dropped VAL into
the tokeniser loop.

## 4a. 🟢 The destination question dissolves — put it on the STACK

The activation needs ~9 bytes for the token `tk_float` emits, and §4 below records
the search for them ending in a third shared-buffer ownership question. **That
search was the wrong shape.** The scratch is written and read entirely within
`sh_val_parse`'s own call, so it does not need to be RAM anyone else can see:

```
                ld      hl,-10
                add     hl,sp
                ld      sp,hl               ; 10 bytes of scratch AT SP
                ex      de,hl               ; DE = the emit destination
                …  call tk_float  …
                ld      hl,10
                add     hl,sp
                ld      sp,hl               ; released
```

🎯 **It cannot alias anything, so there is no ownership question to get wrong.**
`tk_float`'s own pushes go *below* SP and never touch the scratch above it. Ten
bytes of stack in a tenant is nothing.

**And the float value still reaches the main ROM without shared scratch**, because
`FAC` is already shared: the sub-ROM copies the token's value bytes into `FAC`,
sets `FACTYP` (4 or 8), and returns a "float in FAC" marker. The glue then calls
`flt_to_int16` (`basic/float.asm:384`) for the `DE` that `ev_f`'s int consumers
still expect — exactly what `ev_f_float` does for a literal.

⚠️ **Remaining work, named honestly:** the sign. A leading `-` is easy to apply to
an integer result and fiddlier on a float (flip the sign bit in the lead byte),
and `tk_float` never sees a sign because the tokeniser emits it as an operator.
That, and the `TKOVF` reject path's VAL-mode answer, are what is left.

## 4. The search that led there — three shared buffers, all owned

The scan needs a **destination** for the token bytes (~9: one token byte plus at
most 8 value bytes). `FOUTBUF` looked ideal — 24 bytes, and `flt_out`-only by the
same argument that freed `TKVALEND` — but it is **not** `flt_out`-only:
`basic/program.asm` and four math-pack files (`fp_sqrt`, `fp_atan`, `fp_pow`,
`fp_exp`) also write it.

That is the third shared-buffer ownership question in this arc, after `TOKBUF`
(direct-mode lines execute from it) and `DETOKBUF` (`PRINT USING` drains it).
Each of the first two turned out to be a real hazard, so this one gets checked
rather than assumed. **Naming it and stopping is the point of landing the
plumbing inert.**

## 5. Verification

| check | result |
|---|---|
| 59 host test files, incl. `test_float.py` (drives `tk_float` on bare literals to exact token bytes) and `test_tokenise.py` | **all pass** |
| `kwsweep` | green |
| every real exit retargeted | verified by grep, after the replace came up one short |
| full battery | **47/47 green** under `caffeinate -i` (3 flakes, all green on serial retry) |

The host tests are what make this *re-appliable* with confidence: they exercise
the changed code **statically**, so the invasive half is proven neutral without
an emulator. What is missing is only the battery, and the patch reproduces the
work exactly.

## 6. 🔴 RUN EVERY BATTERY UNDER `caffeinate`

```
caffeinate -i make gates
```

Nothing to install — `caffeinate` ships with macOS, and `-i` prevents idle system
sleep for the command's lifetime. Without it, an unattended battery on battery
power is racing the display timeout, and **the failure does not look like sleep**:
it looks like emulators stalling and preflights refusing, i.e. exactly like a
contended host. Two batteries were thrown away and one correct change was
withdrawn before this was understood.

⚠️ **The tell to remember:** refusals in **0–4 seconds** are not contention.
Contention makes things slow; a 0-second refusal means the preflight lost a race
against work that never got scheduled at all.

Next: answer §4's question — where the ~9-byte destination lives — before wiring
VAL to `tk_float`.
