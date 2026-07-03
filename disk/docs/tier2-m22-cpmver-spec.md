<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 M22a — the console/misc BDOS tier's canonical page-1 entries (CPMVER divergence root-caused) — CHARACTERISATION + fix-shape spec (no asm)

**Status: CHARACTERISED (2026-07-03). CHARACTERISE + SCOPE ONLY — no asm touched, no
fix implemented; `bdosx2.asm` / `build_bdosx2_disk.py` / `disk/*.asm` all byte-unchanged.
STOP for sign-off** (per [[spec-before-implementation]] — this is a multi-entry
relocation + new-bodies milestone, not a pre-approved veneer). Extends
[tier2-bdos-remaining-spec.md](tier2-bdos-remaining-spec.md) (M22 = keys2 + `BDOSX2.COM`,
both already committed, `1d68c64`); ground truth [tier2-STATE.md](tier2-STATE.md);
shape/rigor template [tier2-bdos-fcbread-spec.md](tier2-bdos-fcbread-spec.md); fix-shape
precedents [tier2-m17-spec.md](tier2-m17-spec.md) (veneer+cell),
[tier2-m20-spec.md](tier2-m20-spec.md) (`$F306` exit-mirror semantics),
[tier2-m21-spec.md](tier2-m21-spec.md) (RC-1 byte-count collision + relocation).

## 0. TL;DR

The first `BDOSX2.COM` run surfaced a CPMVER (`$0C`) garbage return. Root cause, pinned
black-box: **the entire console/misc BDOS tier is dispatched by the shared RAM kernel to
ELEVEN canonical page-1 disk-ROM entries, and on ours five of those collide with our own
relocated code/data while five more are un-wired `$00` pad that NOP-slides into the wrong
veneer.** This falsifies two prior architectural claims at once (the 2026-07-01 sweep's
"`$0C` returns a constant wholly inside the kernel with NO disk-ROM routine", and
[tier2-bdos-remaining-spec.md](tier2-bdos-remaining-spec.md) §4's "console block: no
page-1 code — unlikely un-wired-entry candidates"). The prior "zero page-1 entries during
`$0C`" probe result was an artifact: it was run with the degenerate range
`--range 0x4000:0x4000` (a ONE-byte watch on `$4000`), not the full page — falsify-first
paid for itself again.

- **NOT a kernel-workarea data corruption** (the briefed lead hypothesis) — REFUTED §2.2.
- **LOGIN is independently broken** (not CPMVER knock-on) — CONFIRMED §2.3.
- **Not timing/order dependent** — the entries are static ROM-layout facts §2.4.
- The damage on ours goes beyond wrong registers: the `$41EF` CPMVER call falls into our
  `callf_body`, which misparses 3 KERNEL CODE bytes as a CALLF operand and **jumps to an
  effectively arbitrary address** — by GTIME this garbage execution warm-boots the machine
  (BDOSX2 aborts back to COMMAND.COM, §4.2). The `$504E` LOGIN slide lands in our `$5058`
  SETDTA-cache veneer and **stomps `DOS_DTAPTR`** as a side effect.
- Fix shape (§6): M21a-RC-1-class — relocate three colliding blocks (`p0_env_tab`+drop the
  `callf_body` jp; `fat_find_body`; `fdc_entloop_body`+`fdc_useslot_body`) into the free
  tail (1009 B available, ~220 B needed), then wire ten 3-byte veneers at the pinned
  canonical entries to small bodies reproducing the pinned exit contracts, plus extend the
  existing `$5454` body with DIRIO's input direction. **These handlers must NOT clear
  `$F306`** — every pinned exit HL is the `H:=B,L:=A` mirror (§5.2, the M20 rule inverted).

## 1. Reproduction (verified afresh this span)

```
python3 probes/disk/build_bdosx2_disk.py --dos-disk ~/Documents/msx/msx/disks/test.dsk \
    --out /tmp/zerobas_bdosx2_char.dsk
python3 probes/disk/disk_probe_diff.py callseq --log 0x0005 --maxhits 45 \
    --keys '\rBDOSX2\r' --keys-at 22 --settle 40 --diska /tmp/zerobas_bdosx2_char.dsk
```
Alignment guard passes: **n=1..36 byte-identical** (COMMAND.COM boot + BDOSX2 load + the
`$0C` CPMVER entry itself). Divergence:

| n | call (entry state = previous call's exit) | STOCK | OURS |
|---|---|---|---|
| 37 | `$18` LOGIN (= CPMVER exit) | `A=22 B=00 HL=0022` | `A=B0 B=EF HL=EFB0` |
| 38 | `$2D` STIME (= LOGIN exit) | `A=03 B=00` | `A=00 B=4E` |
| 39 | `$2C` GTIME (= STIME exit) | `DE=3800` (D preserved), in-flight 1.1 ms | `DE=2C00`, in-flight **0.32 s** (disk-class activity) |
| 40+ | | VERIFY→VERIFY→DSKRST→CONST… | **COMMAND.COM reload flow** — BDOSX2 aborted mid-run (warm boot during/after GTIME) |

`capture --at 0x0005 --nth 4 --arm-check-val 0xcd --mem 0x0340:0x70` (both machines,
ALIGNED, anchor = the GTIME call with BDOSX2 resident — `$0102`=`$CD` read from the
assembled `.com`) confirms records 0–2 in the `regs` buffer: CPMVER, LOGIN **and STIME**
all corrupted on ours; every stock value is the `H:=B,L:=A` mirror of its own A/B.

## 2. Falsification pass on the briefed hypotheses

### 2.1 "CPMVER touches no disk-ROM code" — FALSIFIED (probe artifact)
The prior evidence was `callwatch --range 0x4000:0x4000` — that parses as lo=hi=`$4000`,
a single-byte watchpoint. Rerun correctly:
```
python3 probes/disk/disk_probe_diff.py callwatch --range 0x4000:0x7FFF --in-func 0x0c \
    --machine both --keys '\rBDOSX2\r' --keys-at 22 --settle 40 --diska /tmp/zerobas_bdosx2_char.dsk
# STOCK: 3 entries — $41EF, $41F1, $41F3 (one tiny straight-line routine)
# OURS : 12 entries — $41EF, then $5469..$5491 (callf_body_body), $6BCD, $7880 (k47b2_fcb DATA)
```
`$0C` runs page-1 code on BOTH machines. Stock runs a 3-instruction-boundary routine at
`$41EF..$41F3` and nothing else; ours enters `$41EF` and then wanders through our CALLF
handler into unrelated code/data. (Lesson recorded: `callwatch --range LO:HI` takes a
range, not `BASE:LEN` — the `LO:HI` convention differs from `readwatch`/`writewatch`'s
`BASE:LEN`. A guard for this foot-gun is proposed in §8.6.)

### 2.2 "Our boot corrupts a kernel RAM data cell" — REFUTED
No data-corruption mechanism is needed and none was found: the divergence is fully
explained by *execution* entering different page-1 code (§2.1) at byte-identical entry
state — `callseq --log 0x41EF` shows entry regs **byte-identical ours==stock**
(`A=00 B=EF DE=0080 HL=0000 ret=D88A`, §3). A cell-stomp hypothesis predicts identical
code paths reading different data; observed is the opposite (identical input, different
code). The `OWN_RAM_RANGES` cross-check is therefore moot for THIS bug (no gated
readwatch of kernel constants was needed); the one real RAM-stomp found — `DOS_DTAPTR`
via the `$504E`→`$5058` slide — is itself a *consequence* of the missing entry, not a
boot-time corruption (§4.3).

### 2.3 "LOGIN garbage is CPMVER knock-on" — REFUTED; LOGIN is independently broken
LOGIN's kernel entry is `$504E` (own CALL, `ret=D88A`, §3) and ours derails *inside that
call* regardless of CPMVER's outcome: the n=38 entry state (`A=00 B=4E` vs stock
`A=03 B=00`) is produced by LOGIN's own slide into the `$5058` SETDTA-cache veneer.
Each function in the tier fails on its own missing entry.

### 2.4 "Timing/boot-order dependent" — REFUTED
The root cause is static ROM layout (bytes at fixed page-1 addresses, §4 — verified in
`build/disk.rom`, our own artifact). No arming/order variation changes it; the same
entries misfire at whatever time the function is first called.

## 3. The pinned canonical-entry map (black-box, stock = oracle)

Method: `callwatch --in-func N` (entry-PC sets, both machines) + `callseq --log <entry>`
(caller `ret` + entry regs) + the `BDOSX2` record buffer (exit contracts, §5). A
**consistent dispatcher fingerprint corroborates every row: at entry, `B` = the entry
address's LOW byte** (the kernel's dispatch evidently carries the handler address through
`B`; observed on all eleven, never decoded). `ret=$D88A` (kernel RAM) = called directly
by the kernel dispatcher; a page-1 `ret` = stock-internal helper (NOT our ABI surface).

| func | kernel entry | entry `B` | direct-call proof | stock-internal helpers seen (not ABI) |
|---|---|---|---|---|
| `$0C` CPMVER | **`$41EF`** | `$EF` | `ret=D88A` | — |
| `$18` LOGIN | **`$504E`** | `$4E` | `ret=D88A` | — |
| `$2D` STIME | **`$55E6`** | `$E6` | `ret=D88A` | `$4130` (called `ret=$55FD`) |
| `$2C` GTIME | **`$55DB`** | `$DB` | `ret=D88A` | `$54C0` (`ret=$55E2`) → `$4179` (`ret=$54C3`) |
| `$2E` VERIFY | **`$55FF`** | `$FF` | `ret=D88A` (2 calls: E=1, E=0) | — |
| `$0D` DSKRST | **`$509F`** | `$9F` | in-func entry set + `B` fingerprint | `$402D/$45C4×2/$472D/$5FAE-$5FEE/$50A9-region` (real flush flow) |
| `$0B` CONST | **`$543C`** | `$3C` | per-poll entry set (`$543C/$543F/$5441` ×80) + `B` | `$5412/$5415` (`ret=$543F`) |
| `$01` CONIN | **`$5445`** | `$45` | `ret=D88A` | `$53A8..$53E1` (`ret=$544C`), `$5412`, `$40xx` CHPUT chain |
| `$08` INNOE | **`$544E`** | `$4E` | in-func entry set + `B` | `$541D-$542A` |
| `$07` DIRIN | **`$5462`** | `$62` | in-func entry set + `B` | wait-loop tick + `$40xx` |
| `$06` DIRIO | **`$5454`** | `$54` | in-func entry set (entered 2× = in+out) + `B` | `$5457-$5460` (direction branch) |

Repros (each rerunnable):
```
python3 probes/disk/disk_probe_diff.py callseq --log 0x41EF --maxhits 6 --arm-check-val 0xcd \
    --keys '\rBDOSX2\r' --keys-at 22 --settle 40 --diska /tmp/zerobas_bdosx2_char.dsk
#   (same for 0x504E, 0x55E6, 0x55DB, 0x55FF, 0x5445, 0x4130, 0x4179, 0x54C0, 0x5412, 0x53A8)
python3 probes/disk/disk_probe_diff.py callwatch --range 0x4000:0x7FFF --in-func 0x18 \
    --machine both --keys '\rBDOSX2\r' --keys-at 22 --settle 40 --diska /tmp/zerobas_bdosx2_char.dsk
#   (console tier needs --machine stock --keys2 'xyz' --keys2-at 32 --settle 45; ours
#    crashes at GTIME and never reaches records 7-13 until the block-B entries are fixed)
```
**Concurrency trap (M15-class, caught and excluded):** `$6022..$603A` + `$782B..$784A`
appear inside several windows but are a PER-FRAME kernel tick (`ret=$F392`, fires every
16.6 ms regardless of the BDOS function in flight) — NOT part of any handler above. They
were excluded by their `ret`/cadence, not guessed away. (Ours never runs this tick's
page-1 leg — 0 calls — an already-known design difference on the `$F392` console path,
logged as observation §8.5, not part of this bug.)

## 4. What ours does today at each entry (root cause detail)

All byte checks below are `build/disk.rom` — our OWN artifact (allowed).

### 4.1 `$41EF` CPMVER — collision with `p0_env_tab` tail + `callf_body`
Ours: `$41EF`=`$00` (the last byte of `p0_env_tab`'s `dw 0` terminator,
[pageenv.asm:63-71](../pageenv.asm)), `$41F0`=`C3 69 54` (`callf_body: jp
callf_body_body`). The kernel's CALL lands on the pad byte, NOP-slides into
`callf_body` — a handler that ([kernel.asm:185-206](../kernel.asm)) pops the return
address and reads the 3 bytes AFTER the call site as a CALLF `[slot][lo][hi]` operand,
then **jumps to that address**. Called from a plain kernel CALL, those 3 bytes are kernel
CODE, so the "target" is arbitrary: ours' `$0C` window walks `$5469-$5491`
(callf_body_body), `$6BCD`, `$7880` (`k47b2_fcb` — DATA executed as code) and eventually
rets with `A=$B0 B=$EF` (entry `B` passed through untouched; stock's routine sets
`A=$22 B=$00`).

### 4.2 `$55E6` STIME / `$55DB` GTIME / `$55FF` VERIFY — collision with relocated FDC bodies
Ours has `fdc_entloop_body` (`$55C5`) and `fdc_useslot_body` (`$55F4`) — Tier-2 3b
relocated bodies — occupying `$55C5..$5619`. All three canonical entries land mid-body:
STIME executes FDC-flavored code (95 iterations of a `$4C94` retry loop = the observed
0.32 s), returns wrong `B/C/D`; GTIME's walk (46 distinct PCs, including boot-path code)
ends in a **warm boot** — BDOSX2 is killed and COMMAND.COM reloads (the n=40+ tail in
§1). The crash is downstream garbage execution, not a separate bug
([[tier2-storms-are-downstream]] framing).

### 4.3 `$504E` LOGIN — un-wired pad, slides into the `$5058` veneer
`$504E..$5057` = `$00` → NOP-slide into `$5058: jp setdta_cache_body` (M19). Two effects:
garbage exit (`A=00 B=4E` → mirror `HL=$4E00`; stock `HL=$0003` = the 2-logical-drive
bitmap, consistent with `DRVCNT`=2), and a silent write of the current `DE` into
`DOS_DTAPTR` (`$F23D`). At this call site `DE` happens to be `$0080` (the default DTA),
so the stomp is benign-by-luck today — it would not stay benign for other callers.

### 4.4 `$509F` DSKRST — un-wired pad, slides into our `$50A9` stub: accidental contract match
`$509F..$50A8` = `$00` → slides into our real `$50A9` stub (`sub a; ld ($F242),a;
ld de,$F1AA; ld ix,$F1AA; ld hl,$F359; ret`). Stock's real `$509F` flush flow exits
`A=00 B=9F(preserved) DE=$F1AA HL=mirror=$9F00` — the stub-slide reproduces **exactly
those register values by coincidence**. Ours' DSKRST would pass the register diff today
without ever running a flush. Flagged for explicit wiring (§6.3) — pad-slide luck is
precisely what M21a-RC-1 broke later.

### 4.5 `$543C` CONST / `$5445` CONIN / `$544E` INNOE — un-wired pad, slide into `$5454`
All three are `$00` pad ending at `$5454: jp conout_body`. Each would emit a garbage
char via CONOUT (char taken from `E`) instead of polling/reading the keyboard, and
return without consuming the staged key. (Unreached today only because ours dies at
GTIME first.)

### 4.6 `$5462` DIRIN — collision with `fat_find_body`
`$5462` falls inside `fat_find_body` (`$5457..$5468`, [kernel.asm:177-183](../kernel.asm)).

### 4.7 `$5454` DIRIO — wired but body incomplete
The kernel routes BOTH `$02` CONOUT and `$06` DIRIO to `$5454`. Stock's routine branches
(`$5457-$5460` entered only in the `$06` window); our `conout_body` implements only the
output direction. DIRIO-in (`E=$FF`) on ours would print char `$FF` instead of polling.

## 5. Pinned exit contracts (the values the fix must reproduce)

### 5.1 The full stock record buffer (BDOSX2 `regs` at `done`, keys2 delivered)
```
python3 probes/disk/disk_probe_diff.py capture --at 0x01F3 --arm-check-val 0xcd --machine stock \
    --mem 0x0340:0x70 --keys '\rBDOSX2\r' --keys-at 22 --keys2 'xyz' --keys2-at 32 --settle 50 \
    --diska /tmp/zerobas_bdosx2_char.dsk    # anchor $01F3 = `done` from bdosx2.sym
```
Stock reaches `done` at t=32.2 — **the keys2 mechanism works end-to-end** (all 14
records complete; `x`/`y`/`z` consumed in order). Decoded records
(`[func,A,B,C,D,E,H,L]`):

| # | call | A | B | C | D | E | H | L | reading |
|---|---|---|---|---|---|---|---|---|---|
| 0 | `$0C` CPMVER | 22 | 00 | 0C | 00 | 80 | 00 | 22 | `A=$22 B=0`; DE preserved; `HL=$0022` |
| 1 | `$18` LOGIN | 03 | 00 | 18 | 00 | 80 | 00 | 03 | `HL=$0003` = drives A:+B: bitmap |
| 2 | `$2D` STIME | 00 | 0C | 22 | 38 | 00 | 0C | 00 | `A=0` ok; `B:=H(hrs) C:=L(min)`; D/E preserved |
| 3 | `$2C` GTIME | 00 | 00 | 00 | 00 | 00 | 00 | 00 | **all-zero, deterministic** (GDATE-default-class; STIME does NOT feed it — set 12:34:56 one call earlier) |
| 4 | `$2E` VERIFY on | 01 | FF | 2E | 00 | 01 | FF | 01 | `A:=E`; B (entry `$FF`) passed through |
| 5 | `$2E` VERIFY off | 00 | FF | 2E | 00 | 00 | FF | 00 | same |
| 6 | `$0D` DSKRST | 00 | 9F | 0D | F1 | AA | 9F | 00 | `A=0`; `DE:=$F1AA` (handler side effect) |
| 7 | `$0B` CONST ready | FF | 3C | 0B | F1 | AA | 3C | FF | `A=$FF`; DE untouched (still `$F1AA`) |
| 8 | `$01` CONIN | 78 | 45 | 01 | F1 | AA | 45 | 78 | `A='x'`, echoed |
| 9 | `$07` DIRIN | 79 | 62 | 07 | F1 | AA | 62 | 79 | `A='y'`, no echo |
| 10 | `$08` INNOE | 7A | 4E | 08 | F1 | AA | 4E | 7A | `A='z'`, no echo |
| 11 | `$06` DIRIO in | 00 | 54 | 06 | F1 | FF | 54 | 00 | drained → `A=0`; E=`$FF` preserved |
| 12 | `$0B` CONST drained | 00 | 3C | 0B | F1 | FF | 3C | 00 | `A=0` |
| 13 | `$06` DIRIO out `!` | 21 | 54 | 06 | F1 | 21 | 54 | 21 | `A:=E` |

The spec's §6 GTIME-jitter worry is void: the oracle's GTIME is a constant 00:00:00 (no
seconds tolerance needed — the whole buffer must diff to zero bytes).

### 5.2 The `$F306` rule INVERTED for this tier
Every exit `HL` above equals `mirror(H:=B, L:=A)` — i.e. **none of these handlers clears
`$F306`**; the kernel's common exit path manufactures HL from the handler's A/B (M20
§11.1 mechanism). For CPMVER/LOGIN that mirror IS the documented result (`L=A`, `H=B`).
Consequence for our bodies: set A and B correctly and **leave `$F306` alone** — clearing
it (the M20 habit) would pass entry-HL through instead and FAIL the diff. The M20 STATE
rule gains a corollary: *clear `$F306` only when the handler must return a computed HL;
leave it set when the caller expects the A/B mirror.*

### 5.3 Entry-state facts a body may rely on (all pinned at the entry callseqs)
`C` = the BDOS function code at every entry (preserved into the exits above except where
the handler overwrites it: STIME `C:=L`, GTIME `C:=0`); `B` = entry-address low byte
(overwritten by CPMVER/LOGIN/STIME/GTIME, passed through by VERIFY/DSKRST/console);
STIME receives the time in registers: `HL=$0C22` (12h/34m), `D=$38` (56s), `E=0`.

## 6. Proposed fix shape (M22a; for sign-off — do NOT build yet)

Class: **M21a-RC-1 (relocate colliding spans) + M17 (wire veneers) + new small bodies.**
Free tail headroom: last non-zero ROM byte `$7C0E` → **1009 pad bytes**; total new/moved
material ≈ 220 B. Net-zero throughout (all veneers consume existing `$00` pad or freed
spans; every canonical address anchored with `ds`; 3-pass object build must stay 16384 B).

### 6.1 Relocations (frees the colliding spans)
1. **`p0_env_tab` → free tail** (26 B DATA, read only by `lpe_loop` at init — position
   free), and **point its `$0030` pair directly at `callf_body_body`**, deleting the
   3-byte `callf_body` jp at `$41F0`. Frees `$41D6..$41F2`; the cramped pre-`$41FD`
   region GAINS ~29 B slack (no §7.3-class overflow risk; verify object size anyway).
2. **`fat_find_body` → free tail** (18 B). Frees `$5457..$5468` (callers reach it by
   label; it ends `jp ff_secloop`, position-free).
3. **`fdc_entloop_body` + `fdc_useslot_body` → free tail** (~87 B, `$55C5..$5619`,
   keep the pair contiguous — `fdc_entloop_body` may fall through/`jp` into its sibling;
   preserve exact fall-through structure as in the M21a relocation).

### 6.2 Veneers (3-byte `jp` each, at the pinned canonical addresses)
`$41EF`→cpmver, `$504E`→login, `$509F`→dskrst, `$543C`→const, `$5445`→conin,
`$544E`→innoe, `$5462`→dirin, `$55DB`→gtime, `$55E6`→stime, `$55FF`→verify.
(`$41EF` may instead hold the 5-byte CPMVER body inline — it fits the freed span exactly;
implementer's choice, veneer+tail-body is the uniform default.) `$5454` stays.

### 6.3 Bodies (free tail; reproduce §5.1, leave `$F306` set)
- **cpmver_body**: `A:=$22, B:=0, ret` — published CP/M-2.2-compat version constant
  (map.grauw.nl `_CPMVER`), independently confirmed by the observed oracle exit.
- **login_body**: `B:=0; A:= (1<<DRVCNT)-1` from our own `DRVCNT` (`$F347`, =2 → `$03`)
  — the published online-drive bitmap, derived from our own cell, not a constant.
- **stime_body**: `A:=0; B:=H; C:=L; ret` (D/E untouched). Range validation (H<24,L<60,
  D<60 → else `A:=$FF` per the published contract) optional; the exerciser never sends
  invalid input, and stock's invalid-path is unobserved — implement the minimal valid
  path, note the gap (§8.2).
- **gtime_body**: `A:=0; B:=0; C:=0; D:=0; E:=0; ret` — the oracle's pinned constant
  00:00:00 (clockless-MSX1 behavior, GDATE-default-class; deliberately NOT backed by a
  time cell — persisting STIME's value would DIVERGE from the oracle, §5.1 r3).
- **verify_body**: `A:=E; ret` (B passes through). Optionally store E in an own cell for
  a future verify-after-write path (out of scope, remaining-spec §5.4).
- **dskrst_body**: explicit body reproducing the already-matching stub contract
  (`A:=0; ($F242):=0; DE:=$F1AA; IX:=$F1AA; HL:=$F359; ret` — i.e. `jp` to our `$50A9`
  stub body is acceptable), replacing the accidental pad-slide with a wired entry.
  Whether stock's DSKRST also resets `DOS_DTAPTR` to `$0080` (the documented side
  effect) is UNVERIFIABLE on ours until the tier runs — acceptance item §7.4.
- **const_body**: CHSNS-class poll via our proven inter-slot primitives → `A:=$FF`/`$00`
  (KEYBUF non-empty/empty; same observation class as `conin_line_body`'s CHGET use).
- **conin_body**: CHGET (blocking) → echo via `conout_body` (char in E per the `$5454`
  contract) → `A:=char`. **innoe_body / dirin_body**: CHGET, no echo, `A:=char`
  (per the published `$07`/`$08` distinction from `$01`; any DIRIN/INNOE behavioral
  difference is invisible at this probe's granularity — both pinned identical here).
- **dirio extension** (the `$5454` body): on entry with `C==$06` and `E==$FF` → input
  direction: if a key is queued, CHGET-no-echo → `A:=char`, else `A:=0`; otherwise
  output `E` as today and `A:=E`. Discriminating on `C` (still the func code at entry,
  §5.3) protects the `$02` CONOUT path for a legitimate `E=$FF` glyph. **Build-time
  falsify step: capture `$5454` entry regs during `$02` vs `$06` on stock first** to
  confirm `C` survives to the entry on the `$02` path too.

### 6.4 Suggested build order (falsify-first inside the milestone)
Land in two slices so a console-tier surprise cannot mask the block-B win:
**M22a-1 (block B):** relocations 6.1.1+6.1.3 + CPMVER/LOGIN/STIME/GTIME/VERIFY/DSKRST →
rerun the §1 callseq: expect alignment through n=42 (DSKRST) and records 0-6 zero-diff.
**M22a-2 (console):** relocation 6.1.2 + CONST/CONIN/INNOE/DIRIN + the DIRIO branch →
full 14-record zero-diff (§7.1). If any single record still diverges, STOP per the
standing rule — its evidence is already localised to one function.

## 7. Acceptance criteria (for the eventual fix)
1. **Primary:** the M22 capture (`capture --at 0x01F3 --arm-check-val 0xcd --machine both
   --mem 0x0340:0x70 --keys '\rBDOSX2\r' --keys-at 22 --keys2 'xyz' --keys2-at 32
   --settle 50`) → alignment guard passes on BOTH machines (ours reaches `done` — no
   warm-boot crash) and the 112-byte buffer diffs to **zero** (no jitter exception
   needed, §5.1). `screen --machine both` (same keys) → identical frames (`x` echo + `!`
   visible on both).
2. **Callseq:** §1's repro extends to full alignment (all 14 BDOSX2 calls + trailing
   CONST polls aligned; poll iteration counts may differ per remaining-spec §5.1 note).
3. **No regression:** 27/27 boot BDOS parity (`--keys '\r'`); DIR screen byte-identical
   (M19/M20); Phase-1 `BDOSX\r` 47-call run + buffer diffs unchanged (M21); `make
   unit-test` 19/19; `make probe` green; `disk.rom` == 16384 B, 3-pass object; the
   relocated `fdc_*`/`fat_find` callers verified by the existing Tier-1 FDC/dir probes.
   CALLF still works: the boot's H.PHYD path exercises `callf_body_body` on every DSKIO
   — any relocation slip fails the boot loudly.
4. **DSKRST side effect:** after the fix, `capture` `$F23D` (and `$F242`) at the record-7
   anchor on both machines — pins whether the kernel or the handler resets the DTA to
   `$0080`, closing §6.3's open point.
5. **Docs:** [tier2-bdos-coverage.md](tier2-bdos-coverage.md) rows
   `$01/$06/$07/$08/$0B/$0C/$0D/$18/$2C/$2D/$2E` updated only per run evidence; STATE.md
   correction: the 2026-07-01 sweep's "`$0C` kernel-internal, no disk-ROM routine" claim
   is superseded by §3 (and the sweep's "UNTESTABLE-HERE ⇒ expected to ride proven
   primitives" caveat is retired — it was tested, and it didn't).

## 8. Residuals / open questions (none block sign-off)
1. **`$4130/$4179/$54C0/$5412/$53A8/$541D-$542A`** — stock-internal helpers; our bodies
   deliberately do NOT reproduce them (we implement contracts, not call graphs). If a
   future probe shows the kernel calling one DIRECTLY in another flow, pin it then.
   **SUPERSEDED for `$53A8`'s neighbour, `$53A7`** (this list named the wrong address by
   one byte): `$53A7` turned out to be a real canonical entry — the kernel CALLs it
   directly for every BDOS `$02` CONOUT char — un-wired on ours and previously reached
   only via a pre-M22a NOP-slide accident that this milestone's `$543C` CONST veneer
   broke (DIR screen corruption). Characterised and fixed in
   [tier2-m22b-conout53a7-spec.md](tier2-m22b-conout53a7-spec.md) (M22b slice 1).
   `$53A8`/`$5412`/`$541D-$542A` themselves remain stock-internal, unpinned.
2. **STIME invalid-input path** (`A=$FF`) unobserved — optional range check, note in
   PROVENANCE if implemented from the published contract only.
3. **VERIFY nonzero-E normalization** unobserved (only E∈{0,1} probed).
4. **DSKRST's real flush semantics** — ours will have no dirty buffers to flush at these
   call sites; the register contract + §7.4's DTA check are the observable surface.
5. **The per-frame `$F392`→`$782B`/`$6022` page-1 tick** exists on stock only (ours: 0
   calls). Pre-existing, unrelated to this bug (console output already byte-identical),
   noted for completeness — do not chase inside M22.
6. **Harness foot-gun:** `callwatch --range` is `LO:HI` while `readwatch`/`writewatch`
   take `BASE:LEN`; the degenerate `0x4000:0x4000` call that produced the false "no
   page-1 code" finding is exactly this confusion. Proposal (harness, one line): reject
   `hi <= lo` in `mode_callwatch` with a hint. Separate tiny commit, not part of the fix.
7. The pre-divergence `A=FF` vs `A=00` at n=33 (SETDTA entry during the BDOSX2 load) is
   outside the alignment keyset and predates this bug — unchanged from Phase-1 runs; not
   investigated here.

## 9. Clean-room status
- **No stock ROM / MSXDOS.SYS / COMMAND.COM code bytes read or decoded anywhere in this
  pass.** Stock-side evidence is exclusively: entry PCs + visit counts (`callwatch`),
  caller return addresses + register values (`callseq`/`capture`), and DATA memory (the
  BDOSX2 `regs` buffer at `$0340`, our own program's output). The one routine-shape
  statement made (§2.1 "3 instruction boundaries at `$41EF..$41F3`") is a PC-gap
  observation, not a decode.
- Function semantics (CPMVER constant, LOGIN bitmap, STIME/GTIME registers, VERIFY flag,
  DSKRST DTA reset, CONST/CONIN/DIRIN/INNOE/DIRIO): published MSX-DOS function reference
  (map.grauw.nl, DOS-1-compatible subset) + MSX2 TH §BDOS + CP/M 2.2 — same sources as
  every prior milestone; outputs are additionally pinned by black-box oracle snapshots
  (§5.1), never asserted from the docs alone.
- The canonical entries (`$41EF` … `$5462`) are de-facto page-1 kernel-ABI addresses —
  the same class as `$4010`/`$5454`/`$50D5`/`$505D` (spec-diskrom-kernel.md §1.3);
  pinned by call-target observation only.
- Ours-side byte checks (`build/disk.rom`, `disk/*.asm`) are our own artifacts.
- Proposed bodies reuse OUR own primitives (`conout_body`, CHGET/CHSNS inter-slot path,
  `DRVCNT`, the `$50A9` stub body) — no stock algorithm reproduced.

## 10. Impact on the M22 recommendation (headline for sign-off)
The remaining-spec's "block A+B = LOW risk, unlikely page-1 involvement" assessment is
**overturned**: this tier is the single largest un-wired canonical-entry cluster found
since M13 — 10 missing/misassigned entries + 1 incomplete body, spanning three collision
relocations. **Recommendation: fix this as M22a (two slices, §6.4) BEFORE any further
BDOSX2/BDOSX0/BDOSX3 work** — the exerciser cannot even run to completion on ours today
(warm-boot crash at GTIME), so no other console/misc record is verifiable until block B
lands. BDOSX0 (TERM0) and BDOSX3 (mutation tier) sequencing is otherwise unchanged.
STOP: awaiting sign-off on §6; no asm has been touched.
