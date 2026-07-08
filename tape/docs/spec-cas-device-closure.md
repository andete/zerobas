<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Closure spec: CAS: & non-disk-device options — Tier 1

**Status: IMPLEMENTED + GATED (2026-07-08).** All three Tier-1 items landed and are
proven on the C-BIOS target:

- **Item 1 — `LOAD"CAS:",R`** ✅ load-and-run + hygiene. `LOAD"CAS:",R` runs the loaded
  program (witness $99); `LOAD"CAS:"` loads but does not run; junk flag → clean error.
  Gate: [basic_probe_cas_options.py](../../probes/basic/basic_probe_cas_options.py).
- **Item 2 — `CSAVE"P",speed`** ✅ honoured. `CSAVE"P",1`→1200 baud (~2400 Hz high tone),
  `CSAVE"P",2`→2400 baud (~4800 Hz); malformed → Syntax error. The speed is `eval`-ed
  (a tokenised `1`/`2` is an integer token, not ASCII). As-built departure from the
  copy-only design below: nothing in the C-BIOS + zerobas-tape stack seeds the baud
  reference tables `CS120`/`CS240` (the tape patch supplies the signal routines but has
  no cold-init hook; zerobas has no `SCREEN,,,baud`), so they read 0 and a copy has
  nothing to select — `CSAVE` therefore *seeds* them (oracle-sourced words) first. Same
  gate. (A tidier home would be seeding in the tape patch — a TAPOON seed-if-zero — but
  that is a `tape.asm` change, deferred.)
- **Item 3 — `OPEN"LPT:"/"CRT:"`** ✅ device channels. `PRINT#` routes to LPTOUT
  (printer, physically verified via the openMSX printer logger) / CHPUT (screen); no
  fat.asm context; `CLOSE#1,#2` list closes both. No-regression: `diskbasic-acceptance`
  33/33 (disk channels untouched). Gate:
  [disk_probe_open_device.py](../../probes/disk/disk_probe_open_device.py) (registered in
  `make diskbasic-acceptance` as `OPEN(LPT/CRT)`).

The design/contract sections below are retained as the as-built record. Tier 2 (tape
sequential channels, CAS: ASCII) and Tier 3 get their own spec after reassessment.

Companion to the sweep [cas-device-option-surface.md](cas-device-option-surface.md). This
spec pins the **contracts + design + gate** for the **Tier 1** items only (the signed-off
first scope: CAS: `,R`/hygiene, `CSAVE` speed, and the `LPT:`/`CRT:` OPEN channels). Tier 2
(tape sequential channels, CAS: ASCII) and Tier 3 are out of this spec; they get their own
after Tier 1 lands and we reassess.

**Clean-room basis.** Contracts below are the *published* MSX-BASIC user-syntax (MSX2
Technical Handbook; MSX-BASIC reference) plus this project's own code. No reference ROM
read ([no-reference-rom-disasm](../../README.md)). BIOS entry-point contracts (`LPTOUT`
`$00A5`, `CHPUT` `$00A2`) are from map.grauw.nl / the TH, already cited where implemented
([tape.asm:574](../tape.asm:574)).

---

## Item 1 — `LOAD"CAS:name"[,R]` load-and-run + CAS: parse hygiene

**Documented surface.** `LOAD "CAS:name"[,R]` — load a tokenised program from cassette;
with `,R`, run it after loading (standard MSX; identical to the disk and to
`BLOAD"CAS:",R`, which already honours `,R`).

**Current behaviour (the gap).** `dl_is_cas` ([cload.asm:87](../../basic/cload.asm:87))
skips past the filename to the closing quote and jumps to `do_tape_prog`, **never parsing
`,R`** — so `LOAD"CAS:x",R` loads but does not run. Asymmetric with `BLOAD"CAS:",R`
([bload.asm](../../basic/bload.asm) `is_tape` → `parse_close_run`).

**Contract to implement.**
- After the closing `"`, parse an optional `,R` exactly as the disk branch does
  (`parse_close_run` sets `RUNFLAG`; a comma followed by anything but `R` → clean
  `Syntax error`, not a silent skip — this is the hygiene half).
- `do_tape_prog` loads the program; on return, if `RUNFLAG` is set, hand off to run
  (mirror the disk tail: `disk_prog_load` → `ld a,(RUNFLAG)` → run). The load-and-run
  handoff machinery (`load_handoff` / the RUN entry) already exists and is shared.

**Design.** Reuse `parse_close_run` + the existing run handoff; do **not** invent a new
`,R` parser. `do_tape_prog` is shared by `CLOAD` and `LOAD"CAS:"` — `CLOAD` must keep its
current no-`,R` behaviour (bare `CLOAD` has no `,R` form), so the `,R` parse lives on the
`LOAD"CAS:"` branch, not inside `do_tape_prog`. Set `RUNFLAG=0` on the `CLOAD` entry.

**Acceptance.** A driven `LOAD"CAS:",R` runs the loaded program (observable side effect,
e.g. the program prints); `LOAD"CAS:"` (no `,R`) loads and returns to the prompt;
`LOAD"CAS:",Q` → `Syntax error`. Gate cell in the tape/BASIC acceptance runner.

---

## Item 2 — `CSAVE"name"[,speed]` speed arg + stray-flag reject

**Documented surface.** `CSAVE "name"[,speed]` where `speed` = `1` (1200 baud) or `2`
(2400 baud) selects the write rate for this save (MSX-BASIC reference; the same 1200/2400
the signal layer already round-trips, [spec-cassette.md](spec-cassette.md) "dual baud").

**Current behaviour (the gap).** `do_csave` ([save.asm](../../basic/save.asm)) parses the
name then jumps straight to `tape_save_basic` — **`,speed` is not parsed**; the baud comes
solely from the active work-area word the system's `SCREEN,,,baud` set. A typed
`CSAVE"f",2` leaves `,2` unconsumed (junk → whatever the statement terminator does).

**Contract to implement.**
- Parse an optional `,speed` after the name: `1` or `2`. Absent → unchanged (baud stays
  whatever the active table holds — today's behaviour). Anything else after the name
  (`,3`, `,A`, trailing garbage) → clean `Syntax error`.
- **Honour** the digit: select 1200 (speed 1) or 2400 (speed 2) for this write session by
  writing the corresponding documented timing words into the active signal-length slots
  the write path reads — i.e. do exactly what `SCREEN,,,baud` does (copy `CS120`/`CS240`
  `$F3FC`/`$F401` → the active `LOW_`/`HIGH_`/`HEADER` slots at `$F406…`), using only the
  addresses already in [spec-cassette.md](spec-cassette.md)'s provenance log. `TAPOON`
  then reads the selected rate with no change to the signal layer.

**Design / scope note.** The honour-path is a small table copy at BASIC level (our own
code, documented addresses) — it does **not** touch `tape.asm`. If sign-off prefers to keep
Tier 1 strictly to hygiene, the fallback is *parse-and-reject-malformed only* (accept `1`/`2`
as a documented no-op, baud stays `SCREEN`-selected); that removes the silent-junk trap but
leaves speed cosmetic. **Recommendation: honour it** — the baud machinery already exists,
so cosmetic acceptance would itself be a silent-drop, the very class this arc closes.

**Acceptance.** `CSAVE"f",2` records at 2400 and round-trips via `TAPION`/`TAPIN` (reuse the
existing dual-baud round-trip harness); `CSAVE"f",1` at 1200; `CSAVE"f",3` → `Syntax
error`. Gate cell reuses the tape round-trip probe with a speed assertion.

---

## Item 3 — `OPEN"LPT:"` / `OPEN"CRT:"` device channels

**Documented surface.** `OPEN "dev:" FOR OUTPUT AS #n` opens a **character-device** channel;
`PRINT#n,…` / `PRINT#n,USING` then stream to the device. `LPT:` = printer, `CRT:` = screen
(MSX-BASIC reference device-name table). Both are output-only (INPUT from `LPT:`/`CRT:` is
an error). Their sinks already exist: `LPTOUT` `$00A5` (A = char, preserves A,
[tape.asm:574](../tape.asm:574)) and `CHPUT` `$00A2` (A = char).

**Current behaviour (the gap).** `do_open` ([files.asm:231](../../basic/files.asm:231))
calls `parse_disk_fcb` **unconditionally** — no device-prefix dispatch — so `OPEN"LPT:"`
tries to open a colon-bearing disk file and fails. There is no per-channel notion of a
device (non-disk) channel; `pchar` ([print.asm:206](../../basic/print.asm:206)) routes only
screen (`PRDEST=0` → `CHPUT`) vs disk file (`PRDEST=1` → `fat_io_putbyte`).

**Contract to implement.**
1. **Device-prefix dispatch at `do_open`.** After the opening `"`, peek (non-destructively,
   the `dev_cas`-compare pattern) for a device prefix `LPT:` / `CRT:` before falling
   through to `parse_disk_fcb`. Add `dev_lpt`/`dev_crt` name strings alongside `dev_cas`.
   (`CAS:` OPEN and `GRP:`/`COM:` are **not** in Tier 1 — an unknown `xxx:` prefix keeps
   today's behaviour: treated as a disk filename, i.e. no regression.)
2. **Per-channel device type.** Add a parallel array `FCH_DEVS[ch]` (0 = disk file,
   1 = LPT printer, 2 = CRT screen), sized `FCH_CEIL+1`, cleared in `init_filechan` and on
   MAXFILES reinit. A device channel sets `FCH_MODES[ch]=2` (OUTPUT) + `FCH_DEVS[ch]=type`.
3. **OPEN a device channel.** After dispatch: require the mode be `FOR OUTPUT` (INPUT →
   `Syntax error`/`Bad file mode`); mark the channel open as a device
   (`FCH_MODES[ch]=2`, `FCH_DEVS[ch]=type`); **skip all fat.asm I/O** (no `fch_claim`, no
   `fat_io_open`, no context block — device channels own no 512-byte buffer). `LEN=` is
   rejected on a device channel.
4. **PRINT# routing.** In the `PRINT#` selection ([print.asm:29](../../basic/print.asm:29)),
   before `fch_select`, test `FCH_DEVS[ch]`: if nonzero it is a device channel — set
   `PRDEST=1` and a new mirror `PRDEV` = the device type, and **do not** call `fch_select`
   (no context load — there is none); just set the `FCH_MODE` mirror to 2. If zero, the
   existing disk path (`fch_select`, PRDEV=0) is unchanged.
5. **`pchar` sink dispatch.** Extend the `pch_file` branch to dispatch on `PRDEV`:
   0 → `fat_io_putbyte` (disk, unchanged); 1 → `LPTOUT` (A=char); 2 → `CHPUT` (A=char).
   Keep the full register save/restore contract (LPTOUT/CHPUT preserve A, but the wrapper
   already guards everything).
6. **CLOSE a device channel.** `fch_do_close_ch` must test `FCH_DEVS[ch]` first: a device
   channel has no OUTPUT flush, no Ctrl-Z, no dir stamp — just clear `FCH_MODES[ch]`,
   `FCH_DEVS[ch]`, and the mirrors. (Today's `mode==2` branch would wrongly try
   `fat_io_putbyte`/`fat_io_close` on a printer.)

**Design rationale.** `FCH_DEVS` is deliberately a *separate* array, not an overload of
`FCH_MODES`, so the disk channel-manager (context cache, `fch_select`, EOF/LOF) stays
byte-for-byte untouched — device channels are a **bypass** layer around it, not a
modification of it. `PRDEV` mirrors the active device type so `pchar` (a hot, register-
tight, shared emit point) does a single load+branch, no table walk. This keeps the
oracle-validated fat.asm engine and the disk-file PRINT# path exactly as they are.

**Non-goals in Tier 1.** No `OPEN"CAS:"` (tape channel — Tier 2), no `INPUT#` from a device
(`LPT:`/`CRT:` are output-only anyway), no `GRP:`/`COM:` (out-of-charter), no `WIDTH LPRINT`
column tracking.

**Acceptance.** Driven on the C-BIOS target with the printer logger plugged
([openmsx-printer-pluggable](../../README.md)): `OPEN"LPT:"FOR OUTPUT AS#1 : PRINT#1,"HI" :
CLOSE#1` emits `HI\r\n` to the printer log (same sink `LPRINT` uses). `OPEN"CRT:"FOR OUTPUT
AS#1 : PRINT#1,"HI"` writes `HI` to the screen. `OPEN"LPT:"FOR INPUT` → error. A disk-file
`OPEN`/`PRINT#`/`CLOSE` still passes the existing `diskbasic-acceptance` cells unchanged
(the no-regression guard). Gate cells: a new tape/device BASIC-driven acceptance cell for
`LPT:`/`CRT:`, plus the untouched disk channel cells.

---

## Gates (all three items)

Each closed option lands a standing gate cell so it cannot silently regress — the disk arc's
lesson. Targets:

- **Item 1 / Item 2** extend the tape read/write round-trip net
  ([tape-regression.md](tape-regression.md), `make -C tape test`) — Item 1 a driven
  `LOAD"CAS:",R` run-observed cell; Item 2 a baud-asserted `CSAVE",speed"` round-trip.
- **Item 3** wants a BASIC-driven, printer-logger-backed cell. Either extend
  `diskbasic-acceptance` (it already drives OPEN/PRINT#/CLOSE on the C-BIOS-class target)
  with `LPT:`/`CRT:` cells, or stand up a small `tape-basic-acceptance` runner if the device
  surface grows in Tier 2. Decide at implementation time; the no-regression guard is that
  the **existing** disk channel cells stay green.

## Provenance

Drafted 2026-07-08 from the sweep + static read of `basic/files.asm`, `basic/print.asm`,
`basic/cload.asm`, `basic/save.asm`, and `tape/tape.asm`. Published user-syntax for the
`speed` arg and the `LPT:`/`CRT:` device-name table is the MSX-BASIC reference; BIOS
contracts are the already-cited `LPTOUT`/`CHPUT`. No reference ROM read.
