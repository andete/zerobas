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

1. ~~**Split `fat.asm`**~~ **STRUCK 2026-09-15 AS A LEVER** — measured, not argued:
   the whole of `basic/fat.asm` is **124 B** of main page 1, so the best case for a
   SPLIT of it is under that. See
   [`spec-diskbasic-relocation-seam.md`](spec-diskbasic-relocation-seam.md) §5.
2. ~~**Reuse `disk/fat.asm`**~~ **STRUCK 2026-09-15, same measurement, same cap.**
   Worth doing only alongside a real move, never as the move itself.
   🔴 **AND THE COUPLING COUNT ABOVE IS REFUTED.** "~15 calls" and "~13 calls"
   were estimates; the measured figures are **`files`→`fat` 3 edges and
   `field`→`fat` 3** — six, not ~28. Relocation is not a FAT problem at all; it is
   an INTERPRETER-coupling problem, at **140 outbound edges**.
3. **Minimal move** — only the FAT-light verbs. 🟢 **PRICED AT 256 B AND
   APPROVED BY JOOST 2026-09-15** (`COPY`, `FILES`/`LFILES`, `KILL`, `NAME`); the
   relief is indeed far under the hoped ~3 KB, because the bulk of `files.asm` is
   the CHANNEL machinery (975 B), not the directory verbs.
4. If the spec concludes **move-all is the only clean option**, that reverses the
   middle-path decision (drops interop) — **escalate to the user**, do not proceed.

🟢 **AND THE WHOLE MECHANISM QUESTION MOVED ON AGAIN, 2026-09-15.** The
correction below (hooks, not `$4004`) is right and stands, but it is not the whole
picture: D-CFEVAL measured that the reference's disk-ROM handler **CALLS BACK into
main BASIC across slots** to evaluate its own arguments. The architecture that
follows from that has its own spec —
[`spec-diskbasic-hook-rearchitecture.md`](spec-diskbasic-hook-rearchitecture.md) —
which Joost directed and which supersedes this document's relocation plan.

## Mechanism

- 🔴 **DISPATCH IS THE *HOOK TABLE*, NOT `$4004` — MEASURED 2026-09-15 AND THE
  PARAGRAPH BELOW IS KEPT ONLY TO SAY WHAT IT REPLACED.** `+0004 STATEMENT` is the
  **`CALL`-statement** expansion handler (`disk/docs/expansion-protocol.md` §1's own
  header table), i.e. the route for `CALL <name>` / `_<name>` — not for a tokenised
  keyword like `FILES`. Two of this tree's documents disagreed and the spec carried
  the wrong half.
  **The measurement** ([`scratchpad/tokscout2.py`](../../scratchpad/tokscout2.py)):
  run each verb as a bare statement on a machine with NO disk ROM. Controls `FROG`
  and `ZQ` — words BASIC does not know — answer **Syntax error**; `FILES`, `KILL`,
  `NAME`, `COPY` answer **Illegal function call**. A word whose handler refuses is
  tokenised, so **the TOKEN and its `stmt_table` entry live in the MAIN BASIC ROM
  and cannot move. Only the BODY can.**
  **What actually reaches the disk ROM is the standard MSX hook**: `H_NAME $FDF9`,
  `H_KILL $FDFE`, `H_COPY $FE08`, `H_FILE $FE7B` (`basic/sysvars.inc`), claimed by
  `disk/kernel.asm` and called through by `chan_gate` (`basic/files.asm:84`), which
  raises ERR 5 when the cell is an unclaimed bare `ret` — exactly the diskless
  reading above. **Today the hook is only a PRESENCE TEST (`hk_present`) with the
  body still in main page 1**, so the move is: point the hook at the real body in
  `disk.rom`, delete the main-side body. **No consumer slot-walk, and no new
  interpreter code at all.**
  🟢 **AND THIS IS WHY THE MOVE DOES NOT COST THE FOREIGN-DISK-ROM INTEROP.** A
  hook is claimed by whichever disk ROM is present: a foreign ROM patches the same
  five bytes with its own `F7 <slot> <lo> <hi> C9` and the verb reaches ITS body.
  Interop is preserved by construction. (An earlier draft of the seam spec claimed
  the opposite; Joost asked *"aren't those supposed to work via hooks?"* and the
  claim was withdrawn.)
  📌 The hook-cell census is black-box and repeatable
  ([`scratchpad/hookscan_probe.py`](../../scratchpad/hookscan_probe.py),
  [`scratchpad/hookid_probe.py`](../../scratchpad/hookid_probe.py)): the CF-3300
  claims **27 cells**, and un-claiming one with `POKE <cell>,201` names its owner
  by which verb starts refusing.
- ~~**Dispatch — `STATEMENT` expansion (`$4004`).**~~ **SUPERSEDED, see above.** The
  original text follows for the paper trail: *`disk/init.asm` already lays an `"AB"`
  header with a zeroed `STATEMENT` vector — implement the provider side there, and the
  consumer slot-walk in `basic/interp.asm`.* The `"AB"` header and its zeroed vector are
  real; what is wrong is that these five verbs would ever be dispatched through it.
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
