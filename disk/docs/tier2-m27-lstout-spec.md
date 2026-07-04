<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 M27 — the `$05` LSTOUT / DIR "82 spurious calls" oddity, root-caused

**Status: LANDED 2026-07-04.** Root cause found and fixed (the DIR-parity bug).
A second, independent, currently-harmless bug (a mid-table collision at kernel
worker slot `$5465`) was found along the way and is documented but NOT fixed
this pass — deliberately deferred (see §4).

Picked up after M26 closed full BDOS-function coverage. This item had been
carried, unexplained, since M19/M20 (first noticed while landing `DIR`'s
`GETALLOC` fix): `DIR` on our ROM issues roughly 82 spurious `BDOS C=$05`
(LSTOUT) calls that stock never makes for the same listing, confirmed
non-blocking to `DIR`'s own output (file list + footer already byte-identical)
every time it was re-examined, but never root-caused.

## 1. Root cause

The fixed page-3 DOS work-area cell **`$F23B`** — a printer-echo state flag
that's part of the disk-ROM's console contract — is **never initialized by our
ROM**. The main-BIOS RAM scan leaves it `$FF` at power-on on both machines
(BIOS writes at `$036A`/`$036D`, t=0.37s — shared, not our code). Stock's disk
ROM zeroes it exactly once during the DOS boot handoff (writer PC `$57BE`,
page-1, t≈3.8s); ours never wrote it, so it stayed `$FF` for the whole
session on ours.

COMMAND.COM's DIR line-end routine reads `[$F23B]` once per file line
(reader PC `$C660`); nonzero is read as "a list device is attached, echo
this line's CR/LF to it too" — two extra `BDOS C=$05` calls per file
(`E=$0D` then `E=$0A`, return addresses `$C66D`/`$C674`). 2 calls × 41 files
on the `test.dsk` listing = the historical 82. COMMAND.COM's own prompt-cycle
code (reader `$D01B`) also saves/suppresses/restores `$F23B` around its own
system output (`$D020`:=0 pre-STROUT, `$D02B`:=saved-value post-STROUT) —
since the "saved value" on ours was the boot-inherited `$FF`, the divergence
persisted across the whole session, not just one `DIR`.

**Falsified along the way:** the original M19-era hypothesis (an
SFIRST/SNEXT directory-attribute-byte mismatch feeding the divergence) is
disproven — poking the one real DTA byte difference (`$D412`, an M19-scoped
non-matched field) and the `$C06A` word to stock's values had zero effect on
the divergence.

**Proof of the fix, before writing any code:** `callseq --log 0x0005
--maxhits 90 --keys '\rDIR\r' ... --poke 0xF23B:0x00` (a live memory poke at
boot, no ROM change) fully re-aligns the call stream: "ALIGNED, NO DIVERGENCE
in 90 shared calls."

Investigation credit: characterised by a Fable subagent dispatch (per
[[opus-vs-sonnet-model-split]]), using `callseq`/`trace --regdump`/
`readwatch`/`writewatch` on the real `DIR` repro (`test.dsk`, no exerciser
program involved, matching `tier2-bdos-remaining-spec.md` §2 F2's original
"characterise from the existing DIR flow, no exerciser" instruction).

## 2. Fix

`disk/runtime.asm`'s `dos_handoff` already has an established DOS-only
default/save/restore pattern for `$F338` (COMMAND.COM's AUTOEXEC branch) and
`$F30D`/`$F30E` (date-format config) — a data disk that returns without
booting DOS must see its own values unchanged (BIOS-agnostic), while a real
DOS boot gets defaulted values. `$F23B` fits the identical shape: save the
host's value on the stack, default it to `$00` on the DOS path, restore it on
the (data-disk) return path.

```asm
                ld      a, ($F23B)          ; save host $F23B (printer-echo state)
                push    af
                xor     a
                ld      ($F338), a          ; DOS default: $F338 = 0
                ld      ($F23B), a          ; DOS default: $F23B = 0 (no printer echo)
                ...
                call    BOOT_ENTRY          ; DOS disk JPs into MSXDOS.SYS (no return)
                pop     af                  ; data disk returned: recover host $F23B
                ld      ($F23B), a
```

A single boot-time zero is sufficient — COMMAND.COM's own save/restore
discipline keeps the cell at `0` for the rest of the session once seeded
(confirmed by the poke test re-aligning the WHOLE run, not just the first
`DIR`).

## 3. Verification

- `callseq --log 0x0005 --maxhits 260 --keys '\rDIR\r' ...`: **ALIGNED, NO
  DIVERGENCE in 260 shared calls** (was: fork at n=63, ~82 spurious calls).
- `DIR` `screen` (both machines): file list + footer byte-identical, as
  before the fix (confirms the fix didn't disturb DIR's own already-correct
  output).
- Boot `callseq` (no `DIR`): 18/18 aligned, unaffected.
- `make unit-test`: 19/19. `make probe`: all green (DSKIO, BASIC, tape).
- BDOSX (`--mem 0x300:0x180` + `--mem 0x400:0x180`): 0 of 384 bytes differ,
  both ranges (unchanged from before — this exerciser was already clean).
- BDOSX2 (`--mem 0x340:0x70`): 0 of 112 bytes differ (unchanged).
- BDOSX0: `callseq --log 0x0005` 43/43 aligned (unchanged).
- **BDOSX3 (`--mem 0x4d5:0x380`, the full `wrpat`/`rdbuf`/`rdbuf2`/`absbuf`
  block): 0 of 896 bytes differ** — this is a genuine bonus finding, not
  just "unaffected". M26 §10 had logged this exact 896-byte block as
  "127/896 differ, the remaining 127 all `rdbuf` (record 12's RDSEQ
  round-trip), confirmed pre-existing and *unrelated to RDRND/WRRND*" — true
  in the narrow sense (RDRND/WRRND didn't cause it), but it turns out to
  share this session's root cause: with `$F23B` uninitialized, COMMAND.COM's
  own prompt-cycle save/restore of that cell (reader/writer `$D01B`/
  `$D020`/`$D02B`, active on EVERY return to `A>`, not just `DIR`) was
  already active before `BDOSX3.COM` even started running, and something in
  that path corrupted state `record 12`'s RDSEQ later inherited. The exact
  causal chain from "prompt-cycle $F23B handling" to "`rdbuf` bytes wrong" was
  NOT traced in this pass (BDOSX3's own call log shows no extra `C=$05`
  calls in its own execution — the corruption predates program start, most
  likely from the boot-to-`A>` prompt's own cycle) — but the fix is verified
  empirically, reproducibly (two independent runs, both 0/896), against the
  project's own standing acceptance bar for this exerciser. **M26's "127
  pre-existing bytes, unrelated" note (tier2-m26-spec.md §10) is corrected by
  this finding — see the cross-reference added there.**

`disk.rom` stays exactly 16384 B (no wrap warnings). Changed: disk/runtime.asm
(`dos_handoff`'s save/default/restore sequence, `$F23B` added alongside the
existing `$F338` handling).

## 4. NOT fixed this pass — the `$5465` mid-table collision (deferred)

A second, independent bug was found while tracing WHERE the spurious `C=$05`
calls landed on our ROM (before the root cause above was known to be the
real fix): LSTOUT is not wired (`grep -rn -i lstout disk/*.asm` → zero hits).
When the kernel dispatches func-5, it CALLs page-1 entry **`$5465`** — the
next slot after the M22a worker-entry cluster (`$543C` CONST / `$5454`
CONOUT / `$5462` DIRIN), i.e. the kernel's real LSTOUT worker-entry address.
On our ROM this slot is squatted by `callf_body_body` (the M22a
relocated-bodies section starts immediately after the `$5462` veneer, no
pad) — it misinterprets the kernel's return address as a CALLF inline
operand and `ret`-jumps to a garbage target, which happens to land inside a
large dead-`$00` pad region and NOP-slide ~2.5 KB to an existing cross-vendor
ABI ret-stub (`$75A5`, wired `jp k_75A5`) and unwind cleanly. **Currently
harmless**: nothing legitimately calls func-5 today (the DIR-oddity fix
above removes the ONLY trigger this milestone found), so this collision has
zero observable effect — but it's a live landmine for any future code that
does reach `$5465` for real.

**Deliberately deferred, not fixed now**, for two reasons:
1. Pinning `lstout_body`'s correct return contract (A/flags on
   ready/not-ready, poll shape) needs triggering a REAL LSTOUT call on
   stock — which the project has twice now (M19-era and this pass) declined
   to do directly, since neither probe machine has a printer attached and
   an uncharacterised "wait for printer ready" poll risks an unbounded hang
   on either side (`tier2-bdos-remaining-spec.md` §2 follow-up F2).
2. **New this pass, not yet conclusive:** openMSX DOES expose a printer
   pluggable (`plug printerport simpl` + the `printerlogfilename` setting)
   that could plausibly make this safe to probe for real — the "no printer
   attached" framing from M19/M20 undersold what the emulator actually
   supports. A quick spike (poke a `CALL $0005`/self-loop stub, `C=$05
   E='X'`, watch PC over 1s of emulated time, plugged vs unplugged, on both
   machines) was **inconclusive**: PC followed an *identical* trajectory
   regardless of plug state on both machines, which could mean the poll is
   already safe without a printer, or could mean the crude register/stub
   injection isn't exercising the real poll path at all. Settling this
   needs I/O-port-level tracing (watching the actual printer-status port
   reads via the existing `iowrite`/watchpoint toolbox), not PC snapshots —
   explicitly out of scope for this pass (user sign-off: land the proven
   `$F23B` fix now, revisit the printer-pluggable angle and `$5465` in a
   future session if/when something needs to call LSTOUT for real).

**Tentative fix shape for `$5465`, if picked up later:** wire
`$5465: jp lstout_body` and shift `callf_body_body` down (it's
label-addressed, relocatable within the M22a section's slack — verify
net-zero at build, same discipline as every other M-series relocation this
project has done). `lstout_body` itself needs its own mini-spec once its
real contract is pinned.

## 5. Follow-ups

- `$5465`/`lstout_body` — see §4. Not gating anything.
- The printer-pluggable (`simpl`) angle for LSTOUT/AUXIN/AUXOUT
  characterisation — worth a dedicated investigation if MSX AUX/printer
  support is ever prioritised; logged as a technique, not yet proven.
- `tier2-m26-spec.md` §10's BDOSX3 verification note is corrected (cross-
  referenced to here) — the "127 pre-existing, unrelated" `rdbuf` gap is now
  understood to share this fix's root cause, though the exact causal chain
  from the boot-prompt's `$F23B` handling to `rdbuf`'s corrupted bytes was
  not traced in this pass.

---

Ground truth: [tier2-STATE.md](tier2-STATE.md). Judgment-call log:
[tier2-review-queue.md](tier2-review-queue.md).
