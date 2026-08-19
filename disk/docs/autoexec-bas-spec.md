<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# `AUTOEXEC.BAS` auto-run — implementation spec

**Status:** DRAFT, awaiting sign-off. No code written yet.
**Goal:** at Disk-BASIC cold start, if `AUTOEXEC.BAS` exists on the boot disk, auto-run it —
a real MSX Disk-BASIC feature our disk ROM is missing (stock-parity gap). Doubly motivated:
it also becomes the **zero-keyboard-typing launch lever** for the `.bas`-on-disk test harness
([diskbasic-bas-harness-spec.md](diskbasic-bas-harness-spec.md)).

## 1. Public spec (clean-room provenance)

*MSX2 Technical Handbook*, Ch.3 "MSX-DOS", boot procedure — an official ASCII Corp.
publication, already an allowed source in this project (the boot-sector/boot-procedure
citations in [make_test_dsk.py](../../tools/make_test_dsk.py) / [disk/init.asm](../init.asm)
come from the same chapter). Verbatim:

> "When MSX-DOS is not invoked and DISK-BASIC starts, if a BASIC program named
> `AUTOEXEC.BAS` exists, it will be carried out."

Corroborated by Wikipedia (MSX-DOS), fms.komkon.org EasyGuide, msxblue.com disk FAQ.
The public text fixes: exact filename, fires at Disk-BASIC startup, DOS-boot precedence
(`AUTOEXEC.BAT` wins when DOS boots), absence ⇒ normal startup. Everything else below is
**black-box observed** on `National_CF-3300` (openMSX; the clean-room-legitimate complement —
inputs→outputs, no ROM decode). Repro: `scratchpad/autoexec_char.py`.

## 2. Characterized behavior (the contract to match)

| Aspect | Observed on CF-3300 | We implement |
|--------|---------------------|--------------|
| Trigger name | exactly `AUTOEXEC.BAS` (upcased 11-byte dirent `AUTOEXECBAS`); `AUTOEXEC.BAT`/`AUTO.BAS`/`AUTOEXEC.BIN` do NOT run | match the 11-byte upcased field |
| Location | any root-dir position (a *search*) | `fat_find` (already searches the root) |
| Drive | boot drive A: | our single-drive A: |
| When | after the banner, **before** the interactive `Ok` prompt | hook in cold-start `init` before `jp repl` |
| Semantics | load into the text area + **RUN** (vars cleared, program left loaded, `Ok` after it ends) | `disk_prog_load` + `run_prog` |
| Tokenised (`$FF`) file | runs | **YES (core)** |
| ASCII-saved (`,A`) file | also runs (tokenised on load) | **follow-on** (see §4) |
| Absent | no run, **no error**, normal startup | silent skip |
| Empty (0-byte) | no run, **no error** | silent skip (see §4) |
| Garbage (non-BASIC) | prints a load error, then `Ok` | our load-error path (message differs; behaviorally error-then-`Ok`) |

## 3. Design (all reused routines verified)

**Hook:** [basic/interp.asm:99](../../basic/interp.asm#L26), a single `call autoexec_run`
inserted between `call show_title` and `jp repl`. By then `clear_vars`/`new_prog`/
`init_filechan` have run and `init_ext_roms` has recorded `DISKSLOT_OK` — banner→run→`Ok`
ordering matches the oracle, and PRINT/file-channel state is initialized.

**`autoexec_run` (new, in the disk-BASIC layer — reuses everything):**
1. `ld a,(DISKSLOT_OK) / or a / ret z` — no disk ROM ⇒ silent skip (same gate
   `disk_prog_load` uses, [cload.asm:375](../../basic/cload.asm#L375)).
2. Fill the scratch FCB name ([sysvars.inc:2276](../../basic/sysvars.inc#L428),
   `DISK_FCB_NAME`, 11-byte upcased): `LDIR` a ROM constant `db "AUTOEXECBAS"`.
3. **Silent presence probe:** `call fat_mount` (`ret c` on no/bad disk) then
   `ld hl,DISK_FCB_NAME / call fat_find` ([fat.asm:159](../../basic/fat.asm#L159));
   `ret c` if not found. This is why we don't just call `disk_prog_load` — its absent
   path is `load_error` (noisy), but the oracle is silent on absent.
4. Found ⇒ `call disk_prog_load` ([cload.asm:847](../../basic/cload.asm#L373); it
   re-`fat_io_open`s — cheap, reuses the whole loader) then `call run_prog`
   ([program.asm:298](../../basic/program.asm#L155) = `clear_vars` + RUN). Fall through /
   `ret` to `jp repl`. This is the `do_run` disk pattern
   ([cload.asm:181](../../basic/cload.asm#L139)) minus the command parser.
5. Load-failure safety: `disk_prog_load`'s `load_error` prints + `ret`s; the store is still
   `new_prog`-empty so the trailing `run_prog` is a no-op → we land at `Ok`.

**BIOS-agnostic (two-interface rule):** the feature lives entirely in zerobas-BASIC (the
host) and reaches the disk only through our own FAT engine over standard `$4010` DSKIO with
`DISKSLOT` from our own INIT scan — zero main-BIOS coupling, identical on C-BIOS and CF-3300
BIOS hosts. Nothing in [disk/init.asm](../init.asm) changes.

## 4. Scope — recommended cut (needs sign-off)

- **IN (core):** tokenised `AUTOEXEC.BAS` auto-run + **silent absent** (the common case;
  every non-autoexec disk must still boot straight to `Ok`). This fully serves the harness
  (`make_test_dsk.py` writes tokenised `.bas`).
- **IN (cheap, recommended):** **silent empty-file** — a 0-byte `AUTOEXEC.BAS` should skip
  silently (one extra check: EOF-as-first-byte ⇒ empty program, no error), matching stock.
- **FOLLOW-ON (separate milestone):** **ASCII-saved `.bas` support.** Stock runs ASCII
  `AUTOEXEC.BAS`; ours rejects non-`$FF` first bytes ([cload.asm:859](../../basic/cload.asm#L384)).
  This is a *general* `LOAD` gap (tokenise-on-load) affecting `LOAD"x"`, `RUN"x"` AND autorun —
  bigger than this feature and best fixed once for all three. Track separately; not in this cut.

## 5. Test plan (acceptance)

- **Differential:** repurpose `scratchpad/autoexec_char.py` into a committed self-asserting
  probe: build a 1-file tokenised-`AUTOEXEC.BAS` disk, boot **ours** and **CF-3300**, assert
  both set the marker (ours now matches stock). Add the negative controls (absent ⇒ silent
  `Ok` both; wrong-name ⇒ no run both).
- **Cold-start context sanity:** an `AUTOEXEC.BAS` that `PRINT`s and one that `LOAD"…",R`-chains,
  to confirm the pre-REPL environment is complete.
- **Regression:** `make unit-test` green; the existing `make diskbasic-acceptance` still 23/23
  (autorun must not perturb the normal boot of the non-autoexec seed disks).
- Then this probe becomes the launch mechanism for the `.bas` SAVE/BSAVE harness (the original
  pilot), and can be wired into `make diskbasic-acceptance`.

## 6. Open decisions for sign-off

1. **Scope** — accept the §4 cut (tokenised autorun + silent absent + silent empty; ASCII as a
   tracked follow-on)? Or pull ASCII-load into this milestone (larger — a general LOAD rework)?
2. **Implementation** — on sign-off I'll implement per §3 (Sonnet, per our impl split), verify
   per §5, commit. Any objection to the interp.asm cold-start hook as the insertion point?
