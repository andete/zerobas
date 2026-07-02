<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 BDOS remaining functions — CHARACTERISATION + SCOPING (spec pass, no asm)

**Status: CHARACTERISED (2026-07-02). CHARACTERISE + SCOPE ONLY — no asm touched, no
fix implemented, `bdosx.asm` not modified. STOP for sign-off** (per
[[spec-before-implementation]]: this covers new function batches AND a small harness
extension, neither pre-approved). Shape/rigor template:
[tier2-bdos-fcbread-spec.md](tier2-bdos-fcbread-spec.md). Ground truth:
[tier2-STATE.md](tier2-STATE.md); scoreboard:
[tier2-bdos-coverage.md](tier2-bdos-coverage.md); the Phase-1 tool this extends:
[tier2-bdos-exerciser-spec.md](tier2-bdos-exerciser-spec.md) + `probes/disk/bdosx.asm`.

## 0. TL;DR / headline scoping calls

1. **Every remaining 🔲 function is reachable via a BDOSX Phase-2 extension — no
   genuine walls.** No function needs real-hardware timing or unobservable kernel
   internals; nothing is destructive to a shared resource (the harness already copies
   the disk to tmp per run, [[test-disk-mutation-gotcha]] is designed in).
2. **One NEW divergence was found while verifying the console-tier trigger assumption
   (falsify-first, §3): OURS DROPS TYPE-AHEAD KEYSTROKES TYPED DURING DISK ACTIVITY;
   stock queues them.** Repro: `screen --machine both --keys '\rDIR\rDATE\r' --keys-at
   22 --settle 75` → stock executes the queued `DATE` after `DIR` (shows the date
   prompt); ours ends at a clean `A>` — the `DATE\r` chars, typed while ours' `DIR` was
   doing disk I/O, never arrived. This does NOT block the console tier (§3.3 sidesteps
   it with a second, later-timed key burst — a ~5-line harness extension), but it is a
   real, user-visible fidelity gap that gets its own follow-up item (recommend **OI-4**),
   NOT an improvised fix inside this track.
3. **The remaining functions split into four blocks with very different risk** (§4):
   a low-risk console+misc block (extend the exerciser pattern), a trivial TERM0
   micro-test, a HIGH-risk directory/FAT **mutation** block (FMAKE/WRSEQ/FREN/FDEL —
   the write-side machinery is genuinely unproven; Phase 1's WRBLK never crossed a
   cluster boundary, so FAT *allocation* has never run on ours), and two open oddities
   deliberately kept OUT of the exerciser (`$05` LSTOUT, the type-ahead loss).
4. **Recommended order confirms STATE.md's declared "console tier next"** — and adds a
   reason: the mutation block is where the next real milestone most likely lives, and a
   divergence/hang there must not gate the cheap console-tier wins. Split the exerciser
   extension into **three separate programs** (§5) so one block's derail can't corrupt
   another's evidence.

## 1. Scope — the functions, with published contracts

Everything 🔲/⚠ on [tier2-bdos-coverage.md](tier2-bdos-coverage.md). Contract source
for every row: map.grauw.nl's published MSX-DOS function reference (documents the
DOS-1-compatible subset verbatim), cross-referenceable to MSX2 Technical Handbook
§BDOS and CP/M 2.2 — the same class of source as every prior Tier-2 milestone; no
stock/kernel bytes decoded. **Snapshot-and-diff philosophy (Phase-1 §4.3): we only
need each call's *input* contract to be right; outputs are snapshotted and diffed
ours-vs-stock, never asserted against an assumed value** — so imprecision in the
published *output* wording is not load-bearing.

| `C` | fn | input contract (what the exerciser must set up) | blocks? |
|---|---|---|---|
| `$01` | CONIN | none; waits for a key, echoes, returns it in A | YES |
| `$06` | DIRIO | E=$FF → poll input (char or $00, no wait); E<$FF → output E | no |
| `$07` | DIRIN | none; waits for a key, no echo | YES |
| `$08` | INNOE | none; waits for a key, no echo | YES |
| `$0B` | CONST | none; A=$FF key ready / $00 not | no |
| `$0C` | CPMVER | none; returns the CP/M-2.2-compat version constant | no |
| `$00` | TERM0 | none; terminates program, warm-returns to COMMAND.COM | never returns |
| `$0D` | DSKRST | none; resets disk state, DTA→$0080 (documented side effect) | no |
| `$18` | LOGIN | none; HL = online-drive bitmap (bit 0 = A:) | no |
| `$2C` | GTIME | none; H=hours L=minutes D=seconds (E where supported) | no |
| `$2D` | STIME | H/L/D(/E) = time to set; A=$00 valid / $FF invalid | no |
| `$2E` | VERIFY | E=$00 off / ≠0 on (verify-after-write flag) | no |
| `$2F` | RDABS | DE=first sector, L=drive (0=A:), H=#sectors → DTA | no |
| `$30` | WRABS | DE=first sector, L=drive, H=#sectors from DTA | no |
| `$13` | FDEL | DE=FCB (name, wildcards allowed); A=$00/$FF | no |
| `$15` | WRSEQ | DE=opened FCB; writes one 128-B record from DTA | no |
| `$16` | FMAKE | DE=FCB (fresh name); creates the file; A=$00/$FF | no |
| `$17` | FREN | DE=FCB, old name at +1, new name in the second half (+17, published CP/M rename convention) | no |
| `$21` | RDRND | DE=opened FCB, random field r0/r1(/r2) at +33..35 set; reads one record to DTA | no |
| `$22` | WRRND | same, writes one record from DTA | no |
| `$05` | LSTOUT | E=char → printer | YES (printer-ready poll) |

## 2. Reachability matrix

"Trigger" = how a BDOSX Phase-2 program reaches it; all runs boot the standard
test.dsk-derived build disk (`build_bdosx_disk.py` pattern) and type the program name
at `A>` — the proven M21/Phase-1 flow.

| Func | Reachable via BDOSX ext? | Blocker? | Assigned block (§5) |
|---|---|---|---|
| `$0C` CPMVER | YES — bare call | none | BDOSX2 |
| `$18` LOGIN | YES — bare call | none | BDOSX2 |
| `$2D`/`$2C` STIME→GTIME | YES — set-then-get pair (same shape as the proven SDATE/GDATE pair) | seconds/centis fields advance between machines at different rates → 1 record has jitter-tolerant bytes (§6) | BDOSX2 |
| `$2E` VERIFY | YES — flag on/off pair | none (flag-EFFECT on writes deliberately NOT coupled in, §5.4 open q.) | BDOSX2 |
| `$0D` DSKRST | YES — bare call | side effect DTA→$0080; ordered after all DTA-dependent work | BDOSX2 |
| `$0B` CONST | YES — both states made deterministic (poll-until-ready; then drained-empty) | needs staged keys (§3) | BDOSX2 |
| `$01` CONIN / `$07` DIRIN / `$08` INNOE | YES — each consumes one pre-staged char; blocking is FINE (the program just waits; the emulator keeps typing) | needs staged keys delivered AFTER the program load (§3 — the type-ahead-loss finding makes the naive single-burst plan unreliable on ours) | BDOSX2 |
| `$06` DIRIO | YES — output direction + drained-input direction | same | BDOSX2 |
| `$00` TERM0 | YES — but it never returns, so it can't share a `done` self-loop anchor with other records | evidence = screen arbiter + callseq, not a buffer capture | BDOSX0 (micro-program) |
| `$16` FMAKE / `$15` WRSEQ / `$10`-close / `$17` FREN / `$13` FDEL | YES — create→write→close→rename→delete lifecycle on a scratch file | disk mutation → tmp-copy disk (already the harness default); HIGH divergence risk → isolate in own program | BDOSX3 |
| `$21` RDRND / `$22` WRRND | YES — FOPEN + poke random field (+33..35) + SETDTA, same FCB pattern as Phase 1 | none | BDOSX3 |
| `$2F` RDABS / `$30` WRABS | YES — read sector 0 to a buffer, write the SAME bytes back (disk unchanged, deterministic) | none | BDOSX3 |
| `$05` LSTOUT | **NO — deliberately excluded** | direct exercise risks an unbounded printer-ready poll (no printer attached in the probe machines; both sides could block, alignment guard just times out — no evidence gained). The open "82 spurious per-file LSTOUT during DIR" oddity is a call-stream divergence in the existing DIR flow — characterise it with `callseq`/`callwatch` on the DIR repro, a separate follow-up, no exerciser involvement | follow-up F2 (§8) |
| `$03`/`$04` AUXIN/AUXOUT | n/a (scoreboard) | — | — |

**No function in scope is blocked by real-hardware timing, shared-resource
destruction, or unobservable kernel internals.** The only structural blocker found is
keystroke *delivery timing* — next section.

## 3. The console-tier trigger mechanism — assumption verified, and a real finding

### 3.1 What was assumed vs what is actually true
The plan's assumption: "openMSX `type` queues into the keyboard buffer regardless of
what's executing, so one pre-staged burst satisfies mid-program blocking reads."
Verified in parts:

- **Mechanism (confirmed from our own harness + BIOS contract):** `--keys` is injected
  once via openMSX `type` at emulated time `--keys-at` (`probes/disk/omsx_session.py`
  `run_job_raw`, the `after time {…} {type "…"}` line). `type` drives the emulated
  key matrix; the BIOS KEYINT ISR moves presses into the KEYBUF ring buffer (published
  sysvar, MSX Assembly Page), which CHGET/CHSNS consume later. Nothing about this
  depends on what the Z80 is executing — **provided KEYINT actually runs while the
  chars are being typed.**
- **Queue-across-phases (already proven in practice):** every `'\rBDOSX\r'` /
  `'\rDIR\r'` repro types the command chars while COMMAND.COM is still busy with the
  date entry, and they are consumed later at the `A>` BUFIN — type-ahead across
  consumer phases works on BOTH machines for non-disk foreground work.
- **The failure case (NEW, found by falsify-first probe this pass):**
  `screen --machine both --keys '\rDIR\rDATE\r' --keys-at 22 --settle 75 --diska
  ~/Documents/msx/msx/disks/test.dsk` → **STOCK** finishes DIR, then executes the
  queued `DATE` (`A>DATE` / `Current date is Sun 84-01-01` / `Enter new date:` on
  screen). **OURS** finishes DIR byte-identically but ends at a **clean `A>` — the
  `DATE\r` chars are gone**, not queued, not echoed. The chars were typed while ours'
  `DIR` was mid disk activity. (A first `'\rDIR\rDIR\r'` probe was run and discarded
  as a non-discriminator — one and two DIRs leave the same final frame.)

### 3.2 What the finding means (bounded — no root-cause claim yet)
Ours loses type-ahead typed during disk-heavy foreground work; stock does not.
Consistent hypothesis (NOT proven, do not treat as settled): our disk-ROM read paths
hold DI across long spans (whole multi-sector operations), so KEYINT misses entire
press windows; stock's kernel re-enables interrupts between sectors. Falsification
path for the follow-up: the [[openmsx-probing-toolbox]] `z80.acceptIRQ` probe /
KEYINT-count differential gated on the DIR window. **This is a real, user-visible
fidelity divergence** (type-ahead during DIR is normal MSX-DOS behaviour) and should
be logged as its own open item (**OI-4**) — it is explicitly NOT fixed by, and NOT a
blocker for, this spec's exerciser work.

### 3.3 Consequence for the BDOSX2 design (the sidestep)
Console chars must NOT ride the same burst as the command name: they would be typed
right after `BDOSX2\r`, i.e. exactly during the program's disk load — the window
where ours drops keys. **Sidestep: a SECOND, later-timed burst.** `run_job_raw` /
`disk_probe_diff.py` grow an optional `--keys2` / `--keys2-at` (one more `after time
{…} {type "…"}` line + argparse plumbing, ~5 lines; default off, so every existing
repro is byte-unchanged — this is "extend the ONE harness", not a fork). Run shape:
`--keys '\rBDOSX2\r' --keys-at 22 --keys2 'xyz' --keys2-at 32`. By t≈32 s the load is
long done on both machines and BDOSX2 is spinning in a CONST poll (BDOS calls only, no
disk I/O), so the chars land in an idle-KEYINT window and queue identically on both
sides. The program's first console record is a **CONST poll-until-ready loop**, which
doubles as the delivery smoke test: if chars are ever lost even at idle, ours (or
both) never reaches `done` and the alignment guard fails loudly — no silent garbage.

## 4. Grouping + per-function risk

Risk calibration facts used below: (a) the console funcs are dispatched by the shared
RAM kernel and bottom out at CHGET/CHSNS/`$5454` CONOUT — all proven byte-identical —
and the 2026-07-01 sweep pinned that no page-1 disk-ROM code is involved (`$0C` is
kernel-internal, constant); (b) BUT "architecturally expected to ride proven
primitives" has been wrong before — and the clock group is the cautionary tale: GDATE
`$2A` needed a real page-1 handler at canonical `$553C` in OUR rom
(`disk/kernel.asm:287`) while SDATE `$2B` needed nothing — so within one "group",
per-function page-1 entries can go either way; (c) Phase 1's WRBLK "write" extended
BDOSX.BIN from 384 to 512 bytes — **inside its already-allocated 1024-B cluster**, so
FAT allocation, dir-entry creation, and dir-entry rewrite have NEVER run through the
runtime kernel on ours.

| Block | Funcs | Structural shape | Risk | Un-wired-entry candidate? |
|---|---|---|---|---|
| **A: console** | `$0C $0B $01 $07 $08 $06` | trivial Phase-1-pattern records + the §3.3 keys2 mechanism | **LOW** | unlikely (sweep-pinned: no page-1 code) — but this run is exactly the direct verification the sweep couldn't do |
| **B: misc non-destructive** | `$18 $2D $2C $2E $0D` | trivial records; STIME→GTIME is the proven SDATE/GDATE pair-shape | **LOW–MEDIUM** | GTIME/STIME: plausible `$553C`-class canonical page-1 entries (GDATE precedent); LOGIN/DSKRST: plausible `$50D5`-class drive-table/flush entries. If any diverges → expect an M17-class veneer or M20-class `$F306` symptom (LOGIN returns HL — remember the `$F306` rule FIRST if a correct-looking HL doesn't survive) |
| **C: mutation + random + absolute** | `$16 $15 $17 $13 $21 $22 $2F $30` | new lifecycle sequencing (create→write-past-a-cluster→close→rename→delete), random-field FCB setup, DTA sector buffers | **HIGH** for `$16/$15/$17/$13` (dir-write + FAT-allocate machinery unproven — the M19/M21-class "big body behind an un-wired entry" pattern is the base expectation, possibly the next real milestone); **MEDIUM** for `$21/$22` (likely shares the proven RDBLK/WRBLK machinery); **MEDIUM-LOW** for `$2F/$30` (bottom out at the proven `$4010` DSKIO, but the kernel path to it is unexercised) | yes — assume at least one real divergence here; the exerciser's job is to LOCALISE it to a record, then STOP for a milestone spec (M13→M21 shape), not improvise |
| **D: termination** | `$00` | 4-instruction micro-program; warm-boot evidence via screen arbiter | **LOW–MEDIUM** | the warm-return path may re-load COMMAND.COM via `$47B2` — now generic (M21b), so this doubles as a free M21b regression |

## 5. Proposed design — BDOSX Phase 2 as THREE programs + one micro harness extension

Why three programs, not one extended `bdosx.asm`: (i) a block-C divergence (likely)
must not corrupt block-A/B evidence — separate runs, separate buffers, separate
alignment guards; (ii) only block A needs the keys2 mechanism — block C stays fully
deterministic with zero console input; (iii) TERM0 never returns, so it cannot share
a `done` self-loop anchor at all. `bdosx.asm` (Phase 1) is left byte-untouched — its
capture repros stay valid regression anchors. All three new programs copy Phase 1's
proven skeleton verbatim: `fillfcb`, IX-indexed `snap`, 8-byte `[func,A,B,C,D,E,H,L]`
records, `done: jr done` anchor with `--arm-check-val` gating on each program's own
third byte (values read from each assembled binary, never hand-guessed).

### 5.0 Harness extension (prerequisite, ~5 lines)
`omsx_session.run_job_raw` + `disk_probe_diff.py` common args: optional `--keys2` /
`--keys2-at` → a second `after time … { type "…" }` inject. Default off; zero change
to existing repros. (Rejected alternatives: padding the single burst with sacrificial
chars — survivor count is nondeterministic; `type_via_keybuf` — pokes BIOS RAM
directly, a heavier-handed injection than needed and a change of observation class.)

### 5.1 `BDOSX2.COM` — console + misc (blocks A+B), 14 records
Same layout convention as Phase 1: code from `$0100`; `fcb` unused; `regs` at `$0340`
(14 × 8 = 112 B); no data buffer. Exact addresses finalised from the `.sym`.

| # | call | setup / expected shape |
|---|---|---|
| 0 | `$0C` CPMVER | bare; snapshot (HL is the interesting field) |
| 1 | `$18` LOGIN | bare; HL = drive bitmap (single-drive ⇒ bit 0) |
| 2 | `$2D` STIME | H=12 L=34 D=56 (E=0); A=$00 expected |
| 3 | `$2C` GTIME | immediately after; expect 12:34:56 — D/E are the jitter-tolerant bytes (§6) |
| 4 | `$2E` VERIFY on | E=1 |
| 5 | `$2E` VERIFY off | E=0 (leave default state) |
| 6 | `$0D` DSKRST | bare; last misc record (its DTA→$0080 side effect then can't perturb anything) |
| 7 | `$0B` CONST | **poll loop until A≠0** — snapshot the final (ready) call; doubles as the keys2 delivery smoke (§3.3). Poll iteration counts differ ours-vs-stock — irrelevant, only the final call is recorded (note: `callseq --log 0x0005` alignment is NOT expected across the poll window; the buffer capture is the evidence) |
| 8 | `$01` CONIN | consumes staged char 1 (`x`), echoes — screen-visible |
| 9 | `$07` DIRIN | consumes char 2 (`y`), no echo |
| 10 | `$08` INNOE | consumes char 3 (`z`), no echo |
| 11 | `$06` DIRIO in | E=$FF with the queue now drained → A=$00 deterministic |
| 12 | `$0B` CONST | drained → A=$00 deterministic |
| 13 | `$06` DIRIO out | E=`!` → emits `!` — screen-visible |

Staged chars are plain letters only (no control chars — CONIN's ^C/^S abort paths are
deliberately out of scope). Both CONST states and both DIRIO directions are covered
deterministically by the drain-then-poll ordering; no record depends on a race.

### 5.2 `BDOSX0.COM` — TERM0 micro-program
`ld c,0` / `call $0005` (+ a trap `jr $` that must never be reached). Evidence is NOT
a buffer capture (nothing survives to anchor): (i) `callseq --log 0x0005` shows the
`C=00` call aligned ours==stock; (ii) `screen --machine both` shows both machines back
at a live `A>` prompt after termination — which also regression-tests the M21b generic
COMMAND.COM re-entry path for free.

### 5.3 `BDOSX3.COM` — mutation + random + absolute I/O (block C), ~24 records
Runs with NO console input (`--keys '\rBDOSX3\r'` only). Disk = the standard throwaway
copy (builder adds `BDOSX3.COM` + `BDOSX.BIN`; `git status` clean-check after, per the
established gotcha). Provisional layout: `fcb` `$0300`; `regs` `$0340` (up to 32
records, → `$043F`); buffers from `$0480`: `wrpat` 128 B (deterministic pattern,
`byte[i]=(i*3+1)&$FF`), `rdbuf` 128 B, `rdbuf2` 128 B, `absbuf` 512 B (→ `$07FF`).

| # | call | setup / point |
|---|---|---|
| 0 | `$16` FMAKE | fresh FCB `BDOSXW  TMP` — **directory-entry creation, never run on ours** |
| 1–9 | `$15` WRSEQ ×9 | SETDTA→`wrpat` once; 9 × 128 B = 1152 B > one 1024-B cluster ⇒ **forces a second-cluster FAT allocation** — the never-run machinery, by design |
| 10 | `$10` FCLOSE | dir-entry size/date rewrite |
| 11 | `$0F` FOPEN | reopen `BDOSXW  TMP` |
| 12 | `$14` RDSEQ | SETDTA→`rdbuf`; readback record 0 ⇒ round-trip content proof |
| 13 | `$10` FCLOSE | |
| 14 | `$17` FREN | old `BDOSXW  TMP` at +1, new `BDOSXR  TMP` at +17 |
| 15 | `$13` FDEL | fresh FCB `BDOSXR  TMP` |
| 16 | `$0F` FOPEN | `BDOSXR  TMP` post-delete → expect A=$FF (negative check) |
| 17 | `$0F` FOPEN | `BDOSX   BIN` (the Phase-1 384-B file, resident on the disk) |
| 18 | `$21` RDRND | random field r0=2 (direct stores, no BDOS); SETDTA→`rdbuf2`; delivers record 2 |
| 19 | `$22` WRRND | r0=1; SETDTA→`wrpat`; overwrites record 1 |
| 20 | `$21` RDRND | r0=1; SETDTA→`rdbuf2`; reads back what WRRND wrote (round trip) |
| 21 | `$10` FCLOSE | |
| 22 | `$2F` RDABS | SETDTA→`absbuf`; L=0 H=1 DE=0 → boot sector, 512 B snapshot |
| 23 | `$30` WRABS | same regs, writes `absbuf` back to sector 0 unchanged — deterministic, disk state preserved |

VERIFY(`$2E`)-on during the write sequence was considered and deferred (open
question, §5.4): it would exercise the verify-after-write read path but couples a
possible VERIFY divergence into every write record — run the block with the default
flag first; a VERIFY-on variant is a one-line rerun later if wanted.

### 5.4 Open questions (do not block sign-off)
- Exact buffer addresses per program — from each `.sym` at implementation (Phase-1
  precedent; the M15 §7.3 no-hand-guessed-addresses lesson).
- Whether 9 WRSEQ records is exactly enough to cross the cluster boundary on the
  actual test.dsk geometry (2 sectors/cluster read from the BPB at build time —
  builder asserts it, bumps the count if geometry differs).
- `--keys2-at` value (32 s provisional) — tune so both machines are demonstrably
  poll-idle; the CONST-poll smoke catches a wrong value loudly.
- VERIFY-on write variant (above).

## 6. Acceptance criteria
1. **Harness:** `--keys2/--keys2-at` lands with default-off semantics; all documented
   STATE.md repros (27/27 boot callseq, DIR screen, Phase-1 BDOSX captures) re-run
   byte-unchanged with no `--keys2` supplied.
2. **BDOSX2:** `capture --at <done> --arm-check-val <byte3> --keys '\rBDOSX2\r'
   --keys-at 22 --keys2 'xyz' --keys2-at 32 --settle 50 --machine both --mem
   0x0340:0x70` → alignment guard passes on BOTH machines (= all six console funcs +
   misc block ran to completion, and keys2 delivery worked); byte diff of `regs`
   either **zero** (→ scoreboard rows `$01/$06/$07/$08/$0B/$0C/$0D/$18/$2E` to ✅) or
   a **localised record divergence** = the next milestone's starting evidence.
   Exception: the GTIME record's D/E bytes tolerate ±1 s skew (documented, expected —
   the soft clock advances during differently-timed boots); every other byte must be
   identical. `screen --machine both` (same keys) → the `x` echo and `!` output
   render identically.
3. **BDOSX0:** `callseq --log 0x0005` shows the final `C=00` call aligned; `screen
   --machine both` → both sides back at a live `A>`.
4. **BDOSX3:** `capture --at <done> … --mem 0x0300:0x140` + `--mem 0x0480:0x380` →
   alignment guard passes (the whole mutation lifecycle completes on ours — itself the
   headline result if it does); byte diff zero (→ rows `$13/$15/$16/$17/$21/$22/$2F/
   $30` to ✅) or localised. **On the first divergent/hanging record: STOP, write that
   milestone's spec** (M13→M21 discipline) — do not patch-and-rerun inside the tool
   session.
5. **Invariants:** no `disk.rom` change (this whole spec is test tooling); `make
   unit-test` untouched at 19/19; committed `test.dsk` unmodified (`git status`
   clean); Phase-1 `bdosx.asm` byte-unchanged.
6. **Scoreboard:** [tier2-bdos-coverage.md](tier2-bdos-coverage.md) updated per row
   with the run evidence, per its "mark only what a probe has shown" rule.

## 7. Clean-room status
- All BDOS input/output contracts: map.grauw.nl published MSX-DOS function reference
  (DOS-1-compatible subset), MSX2 TH §BDOS, CP/M 2.2 equivalents — cited, not decoded;
  and the diff philosophy (§1) never asserts undocumented outputs, it compares ours to
  the oracle black-box.
- FCB layout incl. random field +33..35 and the rename second-name convention:
  published CP/M/MSX2-TH material already in `disk/PROVENANCE.md` §FCB layout.
- KEYBUF/KEYINT/CHGET/CHSNS behaviour: published BIOS contract (MSX Assembly Page /
  MSX2 TH); the §3 finding is a pure black-box screen-arbiter observation on both
  machines — no stock code read.
- The three `.COM` programs are 100 % own code extending our own Phase-1 source;
  built with the existing `build_bdosx_disk.py`/`fat12_add` machinery.
- No stock ROM / MSXDOS.SYS / COMMAND.COM bytes read, dumped, or decoded anywhere in
  this pass; the two probes run were `screen` arbiter runs (VRAM render, allowed
  observation class).

## 8. Recommendation / order (for sign-off)
1. **M22 — keys2 harness extension + `BDOSX2` (console + misc).** Confirms STATE.md's
   declared console-tier priority; lowest risk; validates the delivery mechanism the
   rest depends on; closes up to 9 scoreboard rows in one run.
2. **M23 — `BDOSX0` TERM0 micro-test.** Trivial; can ride the M22 session.
3. **M24 — `BDOSX3` (mutation + random + absolute).** Highest risk, run LAST and
   expect it to surface the next real milestone (dir-write/FAT-allocate machinery has
   never executed on ours). Its purpose is to localise, then stop for a spec.
4. **Follow-up F1 (OI-4) — type-ahead loss during disk activity** (§3): log as an
   open divergence item in STATE.md/review-queue now; characterise later via the
   acceptIRQ/KEYINT differential. Real fidelity gap, not blocking, not to be
   improvised.
5. **Follow-up F2 — the `$05` LSTOUT ×82 DIR oddity:** stays OUT of the exerciser
   (printer-poll hang risk, and it's a DIR-flow call-stream divergence anyway);
   characterise from the existing DIR `callseq`/`callwatch` evidence when a milestone
   next touches that area — unchanged from STATE.md's standing note.
