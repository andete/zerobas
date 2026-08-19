<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Handoff spec-input: relocate disk-BASIC verbs `basic.rom` → `disk.rom` (role-split)

**Status: DIRECTION DECIDED (user, 2026-07-09). Spec NOT yet written.**
This is *spec input, not a green light.* The implementing session **must produce a full
implementation spec and get user sign-off before writing any code** (project rule:
spec-before-implementation). See memory `basic-rom-space-and-growth`.

## Why

- `build/basic.rom` (page-1, slot-0) is **byte-exactly full** — last non-zero byte at
  `$7FFF`, zero trailing fill. Every future `basic/*.asm` addition must reclaim space.
- Faithful home for disk-BASIC is the **disk interface ROM** (a real MSX keeps *all*
  disk-BASIC — DSKIO, FAT/directory, and the `FILES`/`KILL`/… verb extensions — in the
  disk ROM; the main BASIC ROM has no disk code).
- `build/disk.rom` (slot 3-1) is only **42 % full — ~9 KB internal slack**, laid out
  sparsely around fixed MSX-DOS-kernel pins. Usable gaps (measured on the current build):
  `$681D` 3464 B, `$5602` 2531 B, `$50E3` 708 B, `$75A8` 528 B, plus smaller. Room for the
  moved verbs.

## The decision

**Clean middle path** — split disk-BASIC by role, preserving the foreign-disk-ROM interop:

- **Keep in `basic.rom`:** the drive-letter *loader* path (`LOAD"A:"`, `BLOAD"A:"`,
  `SAVE"A:"`, `BSAVE"A:"`, `RUN"A:"`) **plus the FAT logic it needs**, so zerobas-BASIC can
  still load via *any* standard/foreign disk ROM using only sector-level `DSKIO` (the "host
  direction", `expansion-protocol.md` §1.5c — latent, not-yet-implemented, but the current
  layout keeps the door open).
- **Move to `disk.rom`:** the disk-management / non-loader verbs, dispatched via the MSX
  **`STATEMENT` expansion** mechanism (`$4004`). This is the faithful home and frees
  `basic.rom` space with **no C-BIOS page-0 change**.

(The alternative "move *all* disk-BASIC incl. `fat.asm`, ~5 KB, drop the interop" was
considered and rejected in favour of this. The page-0 C-BIOS spill in
`docs/cbios-repack-space-analysis.md` is a *separate* future tool, reserved for genuine
*interpreter* overflow — not this.)

## ⚠️ The central problem the spec MUST solve first

The seam is **not** simply "move `files.asm` + `field.asm`, keep `fat.asm`." Inventory:

- `basic/files.asm` (~1890 B): `FILES` (directory list) **and** the sequential
  `OPEN#`/`CLOSE#`/`PRINT#`/`INPUT#` channel — the latter is a **FAT file-content path**,
  layered on `fat.asm`'s `fat_io_open/getbyte/create/putbyte/close`.
- `basic/field.asm` (~1175 B): random-access `FIELD`/`LSET`/`RSET`/`GET`/`PUT` — record I/O
  on cluster chains, coupled to `files.asm`'s channel manager **and** `fat.asm`.
- Coupling count: **`files.asm` → `fat.asm` ~15 calls, `field.asm` → ~13 calls.** Moving
  these while `fat.asm` stays in `basic.rom` = ~28 cross-slot `CALLSLT`s back into BASIC —
  awkward and slow.

So the spec's first job is to **find the real seam.** Options to evaluate (with measured
byte relief for each):

1. **Split `fat.asm`** into *loader-FAT* (the `LOAD"A:"` directory/FAT walk — stays in
   BASIC for interop) vs *channel/record-FAT* (`fat_io_*` engine — moves to `disk.rom`
   with `files`/`field`). Cleanest if the engine separates cleanly.
2. **Reuse `disk/fat.asm`** — `disk.rom` already carries its own FAT layer (BDOS-side,
   1380 lines). Evaluate whether the moved verbs can bind to it instead of `basic/fat.asm`
   (avoids duplication / cross-slot callbacks).
3. **Minimal move** — only the FAT-light verbs (`FILES` directory list, `KILL`, `NAME`);
   measure the actual relief (likely < the full ~3 KB).
4. If the spec concludes **move-all is the only clean option**, that reverses the
   middle-path decision (drops interop) — **escalate to the user**, do not proceed.

## Mechanism

- **Dispatch — `STATEMENT` expansion (`$4004`).** `disk/init.asm` already lays an `"AB"`
  header with a **zeroed** `STATEMENT` vector — implement the provider side there, and the
  consumer slot-walk in `basic/interp.asm` (today an unknown statement falls to
  `stmt_error`, `basic/interp.asm:688`; there is **no** slot-walk dispatcher — the "one
  gap" flagged in `basic/docs/msx1-basic-bios-coupling.md`). Protocol is pinned in
  `disk/docs/expansion-protocol.md` (headline: the drive-letter *loader* path does NOT use
  DEVICE expansion — it's `DSKIO`+FAT-in-caller; `STATEMENT` expansion is for the
  management statements). Cross-slot dispatch idiom = `CALLF`/`RST 30h` (see `disk/init.asm`
  HPHYD hook).
- **Placement in `disk.rom`** — assemble the moved verb bodies at the internal-gap ORGs
  (`$681D` etc.) with a `ds gap_end - $` guard, exactly like the tape patch's fill guard.
  Confirm gaps on a fresh `disk.rom` build before pinning addresses.

## Scope / target

- Primary deployment only: **patched C-BIOS + `basic` patch + `disk.rom` in slot 3-1**
  (user confirmed patched-C-BIOS is the feature-complete deliverable; the standalone
  cartridge stays a page-1-only subset). `disk.rom` is our own build, so its gap layout is
  ours and consistent across the `C-BIOS_MSX1_*_BASIC_DISK` machines.

## Verification — standing gates must stay green

- `make diskbasic-acceptance` **34/34**, `bdos-acceptance` **12/12**, `bdos-cbios-selfcheck`
  **10/10**, `unit-test` **38/38**.
- Exercise every moved verb end-to-end (`FILES`/`KILL`/`OPEN#`/`PRINT#`/`INPUT#`/`FIELD`/
  `GET`/`PUT`) via the `diskbasic_probe_*` harness, plus the loader path (`LOAD"A:"` etc.)
  to prove interop preservation.
- **Gotchas:** (1) rebuild the IPS + reinstall after ANY `basic/*.asm` edit — machine probes
  run the installed IPS, not `build/basic.rom` (memory `ips-rebuild-after-basic-change`);
  `--cart` probes read `build/basic.rom` directly. (2) Run ALL diskbasic cells after
  shared-parse edits (a cursor-clobber regression once surfaced only in the full suite).
  (3) Test-disk mutation: use `/tmp` copies, `git status` + restore.

## Clean-room

All new code original / from allowed sources. `STATEMENT`-expansion protocol from
`disk/docs/expansion-protocol.md` (CF-3300 black-box, no disassembly). No reference-ROM
disassembly (memory `no-reference-rom-disasm`). `disk.rom` is our own; **C-BIOS is untouched
by this work** (no page-0 change — that's the deferred, separate option).

## Key files

- From: `basic/files.asm`, `basic/field.asm`, possibly part of `basic/fat.asm`;
  `basic/interp.asm` (dispatch), `basic/main.asm` (include order).
- To: `disk/init.asm` (`STATEMENT` vector + provider dispatch), a new disk verb module,
  reuse/extend `disk/fat.asm`.
- Read first: `disk/docs/expansion-protocol.md`, `basic/docs/msx1-basic-bios-coupling.md`
  (mechanism #4), `docs/cbios-repack-space-analysis.md` (the deferred page-0 alternative),
  memory `basic-rom-space-and-growth`.

## Mandate

Write the full spec (the seam, the dispatch design, the exact verb partition + measured
byte relief, the build/IPS wiring), **get user sign-off, then implement** one committed
step at a time behind the standing gates.
