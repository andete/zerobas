<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 M26 spec — the mutation/random/absolute-I/O block (`$13 FDEL` / `$17 FREN` /
`$21 RDRND` / `$22 WRRND` / `$2F RDABS` / `$30 WRABS`)

**Status: ALL SIX FUNCTIONS LANDED 2026-07-03 — FREN (`$17`), RDABS (`$2F`),
WRABS (`$30`), FDEL (`$13`) (§6, §7, §8, §9), and RDRND (`$21`)/WRRND
(`$22`) (§10). M26 is CLOSED; full BDOS surface coverage is complete.**
Per [[spec-before-implementation]] this is a
**new-routine-class** milestone (like [tier2-m19-spec.md](tier2-m19-spec.md)),
not a self-approvable veneer-class fix: six BDOS functions, none wired at
the start, one pair (RDRND/WRRND) showing a risk shape not seen in any prior
milestone. Resume board: [tier2-STATE.md](tier2-STATE.md). This picks up the
M26 candidate first logged in
[tier2-m24-fclose-multicluster-spec.md](tier2-m24-fclose-multicluster-spec.md)
("M25 RESOLVED" §, pre-existing divergences) and characterised further in
that doc's "M26 CHARACTERISATION" section (FREN only); this spec extends
that characterisation to all six functions and proposes fix shapes.

## 1. Goal

Wire the six BDOS functions [tier2-bdos-remaining-spec.md](disk/docs/tier2-bdos-remaining-spec.md)
§5.3 groups as the "mutation + random + absolute-I/O block", exercised end to
end by `BDOSX3.COM` (`probes/disk/bdosx3.asm`) records 14-23:

| record | func | what it does |
|---|---|---|
| 14 | `$17` FREN | old `BDOSXW  TMP` at FCB+1 → new `BDOSXR  TMP` at FCB+17 (CP/M rename convention) |
| 15 | `$13` FDEL | delete the freshly-renamed `BDOSXR  TMP` |
| 16-17 | `$0F` FOPEN | reopen `BDOSX   BIN` (already working, M21a/M25) |
| 18 | `$21` RDRND | random field r0=2 (FCB+33..35, direct poke, no BDOS call) → record 2 to `rdbuf2` |
| 19 | `$22` WRRND | r0=1 → overwrite record 1 from `wrpat` |
| 20 | `$21` RDRND | r0=1 → read back what WRRND wrote (round trip) |
| 21 | `$10` FCLOSE | (already working, M24) |
| 22 | `$2F` RDABS | L=0 (drive A:) H=1 (1 sector) DE=0 (sector 0) → `absbuf`, 512 B |
| 23 | `$30` WRABS | same regs, writes `absbuf` back — deterministic, disk unchanged |

Success = BDOSX3 records 14-23 zero-diff against stock (status registers +
the renamed/deleted directory state + `rdbuf2`/`wrpat` content + `absbuf`
content), same acceptance bar as M19/M21/M24/M25.

## 2. Characterisation (falsify-first, no kernel code decoded — black-box
`callwatch --in-func <C>` per function, all runs on `/tmp/zerobas_bdosx3.dsk`,
correctly anchored `--arm-check-addr 0x0102 --arm-check-val 0x03` — BDOSX3's
own compiled-`.com` fingerprint byte, NOT reused from any other exerciser)

`grep -rn "fren\|fdel\|rdrnd\|wrrnd\|rdabs\|wrabs" disk/*.asm` → **zero hits**
for all six. No hand-written body exists for any of them; every landing
described below is either a coincidental slide into unrelated code or a
partial walk into a REAL routine written for a different function.

### 2.1 `$17` FREN — confirmed simple NOP-slide (LOW risk, straightforward fix)
`callwatch --in-func 0x17` → **one** page-1 hit, `$4392`. That address falls
mid-body inside `fdc_rd_n1`/`fdc_rd_n2` (disk/driver.asm:206-219, the
low-level FDC read-status error decoder — `fdc_rd_n1 EQU $438C` / `fdc_rd_n2
EQU $4395`), entirely unrelated to directory rename. Same signature as
M13/M19/M21/M22b's un-wired entries: the kernel's real `$17` dispatch target
in page-1 is unmapped, the CALL lands wherever that byte offset happens to
decode from our unrelated FDC code, and falls back into the kernel having
touched nothing real. **Explains BDOSX3 record 14's `A=$FC`** (a stray
status byte from the FDC decoder, not a real FREN result).

### 2.2 `$13` FDEL — dead-pad dispatch, but the pad is now a live corruption
hazard post-FREN (CONFIRMED 2026-07-03, Fable dispatch, `trace --resync` +
on-disk `$E5` forensics — 4th M26 function where the original `callwatch`-only
read needed correction)

**Original claim (superseded):** 12 page-1 hits walking the full
`fdc_rd_wait → ... → fdc_rd_n1` chain, ambiguous between a genuine
SFIRST/SNEXT-style directory scan and a coincidental slide.

**Re-derived via `trace --anchor 0x0005 --nth 18 --steps 3000 --resync
--window 600`** (n=18 = BDOSX3's FDEL call, confirmed by counting `$0005`
hits — FREN=17, RDABS=29, WRABS=30, consistent with §6/§7/§8): the kernel's
real, fixed `$13` dispatch address is **`$436C`**. Hit exactly once per
BDOSX3 run on both machines, zero times during a plain boot+DIR — safe,
FDEL-specific. The kernel does no disk I/O before this dispatch (~92
instructions of pure RAM-kernel prologue from `$0005`).

**Historical note, now moot:** at the time §2.2 was first written (before
the FREN fix landed), `$436C` was byte 18 of `fdc_read_data`'s OLD body —
so the original "12-hit chain walk" read was genuinely **hypothesis (b), a
coincidental mid-routine landing**, not a real directory scan. Landing this
milestone's FREN slice (§6, relocating `fdc_read_data` to a free tail)
changed what lives at `$436C` **out from under FDEL**: it's now 20 bytes of
`$00` dead pad followed by `k_4392: jp fren_body` — so ours currently
NOP-slides through the pad straight into **`fren_body` with FDEL's own FCB**.
Since the FCB is zero-filled by `fillfcb_named` before the FDEL call, this
means ours **renames the target directory entry's name field to 11× `$00`**
and writes that back to disk. A first name-byte of `$00` is a directory-scan
TERMINATOR (unlike `$E5`), so this doesn't just fail to delete — it makes
every directory entry AFTER the mangled one invisible to future scans, and
leaks the file's FAT chain (still fully allocated, never freed). **This is
worse than a no-op; it is active, silent corruption**, and the shape moved
one milestone later without any code change to FDEL itself — a direct
illustration of why every M26 function needs its OWN fresh `trace --resync`
regardless of what an earlier characterisation pass concluded.

**Fix shape confirmed as RDABS-style (dead-pad wire, no relocation):** the
pad at `$436C` sits entirely inside the post-FREN `$435D-$4391` corridor
(disk/driver.asm), so this splits the same way RDABS split `bdos_create`'s
pad: `ds $436C - $, $00` / `k_436C: jp fdel_body` / `ds $4392 - $, $00` —
net-zero, `k_4392`/`fren_body` unaffected.

**Register contract (black-box `capture`, pristine disk, both machines
identical at entry):** `A=$21 B=$00 C=$00 DE=$DA40 HL=$03A5(user passthrough,
ignore) SP=$DBFE ret=$D88A`. Differs from RDABS/WRABS's convention in two
ways worth flagging for implementation: **no `B=<addr-low-byte>` fingerprint**
(`B=$00`, not `B=$6C`), and **`C` is NOT the function number** (`C=$00`).
The real per-call input is `DE=$DA40`, a kernel-side 37-byte scratch copy of
the FCB: drive byte + `"BDOSXR  TMP"` (11 bytes) + zero-fill (does NOT carry
the caller's own random-field/reserved bytes — don't read stale
`+32..+34` from this copy). `A=$21` was stable across both machine and disk
state in this session's testing; not required as a fix input. Exit contract
(record 15's own snapshot, stock): `A=$00 B=$00 C=$00 D=$03 E=$D0 H=$00
L=$00` — `DE=$03D0` is a kernel-internal artifact (user-FCB+32) our mirror
already reproduces; the one field `fdel_body` must actively produce is
`HL=$0000` on success (mind the M20 `$F306` rule, same as every prior M26
veneer).

**`$E5`-marker disambiguation, done as specified (on-disk forensics,
pristine images only — see "surprise" note below):** stock's post-run root
directory shows the target entry's first byte become `$E5` with the rest of
the entry (name tail, attributes, starting cluster, size) preserved, AND
**both FAT12 copies' entries for the file's cluster chain zeroed** (this
file is 2 clusters, chain 339→340 — see below). Ours shows the entry's
first 26 bytes all `$00` (the accidental rename) with the FAT chain **still
fully allocated** — confirms the corruption read above directly, not just
inferred from the trace.

**§4 non-goal assumption FALSIFIED:** the spec's "no FAT chain-freeing logic
needed, assumed single-cluster" note does NOT hold — BDOSX3's `BDOSXR  TMP`
scratch file is deliberately 1152 bytes = 2 clusters (1024 B/cluster,
chain 339→340, by design per the M24 multi-cluster test construction), and
stock zeroes BOTH FAT12 entries in BOTH on-disk FAT copies plus flushes the
directory sector. `fdel_body` therefore needs real (if small) FAT
chain-walking/freeing logic — writing `$E5` to the directory entry alone is
NOT sufficient to match stock, contrary to §4's original assumption.

**Open scope question surfaced, not yet resolved:** entry `C=$00` (not the
function number) plus the published MSX-DOS FDEL contract supporting `?`
wildcards for multi-match delete — BDOSX3 only exercises a single exact-name
delete, so whether `fdel_body` needs wildcard support or can reuse the
existing single-match `fat_find` precedent (as FREN did) is a genuine scope
call for sign-off, not something the probe evidence settles either way.

### 2.3 `$21` RDRND / `$22` WRRND — TWO separate dead-pad dispatches, whole-
file DTA-stream mutation (HIGH risk — re-characterised 2026-07-03, Fable
dispatch, `trace --resync` + `trace --regdump` — 5th M26 function where the
original `callwatch`-only read needed correction)

**Original claim (superseded):** one shared dispatch address (mirroring
M25's WRSEQ/RDSEQ `$477D` pattern), because `callwatch --in-func 0x21` and
`--in-func 0x22` produced byte-identical PC lists.

**Re-derived fresh against the post-FDEL ROM** (per the now-5-for-5 lesson:
every M26 characterisation must be re-run after each landing, since earlier
fixes move code underneath later, untouched functions):
`trace --anchor 0x0005 --nth 22 --steps 3000 --resync --window 600` (n=22 =
BDOSX3's record-18 RDRND call; n=24 = record-19 WRRND; record→n offset is
NOT linear across this milestone — 15→18, 22→29, 23→30, 18→22, 19→24 —
re-derived per function, never assumed) finds **TWO distinct real dispatch
addresses**: `$21` RDRND → **`$4788`**, `$22` WRRND → **`$4793`**. The
"byte-identical" callwatch read was a dedup artifact: both entries are pure
`$00` pad sitting in the existing `fat_find` corridor (disk/fat.asm:124-128
— `fat_find_body` at `$4782`, `ds $47B2 - $, $00` = 45 pad bytes, then
`jp k_47B2`), so both un-wired calls nop-slide through the SAME downstream
routine set (`bdos_seqread_body`/`frs_mul_body` via `k_47B2`/
`k47b2_rdloop`) and land on `callwatch`'s coarse per-address view as one
indistinguishable PC list — only `--resync` anchored separately at n=22 and
n=24 can tell the two dispatches apart. **Fix shape confirmed as RDABS-style
(dead-pad wire, no relocation needed)** — same pad corridor pattern as
FDEL's `$436C`, but this time BOTH functions' entries sit in it side by
side; the existing `jp k_47B2` at `$47B2` is unaffected either way.

**The mutation, pinned via `trace --regdump HL` plus black-box forensics**
(no inherited-register divergence at entry — HL identical across the full
~79-step kernel prologue both machines, so the corruption is entirely the
un-wired dispatch itself, not stale state carried in): the slide runs
`k_47B2`'s real body, which on EVERY RDRND/WRRND call streams the **entire
open file** (BDOSX.BIN, 384 B = 3 records) into the caller's DTA — not a
one-record advance as originally guessed. Confirmed mutated: `BDOS_DTA`
(reseeded from `DOS_DTAPTR`), `FAT_CURCLUS`/`FAT_CLUSSEC` (reset via
`fat_open`), `BDOS_BYTESLEFT`/`BDOS_RECIDX` (consumed to EOF), `SECTOR_BUF`.
At BDOSX3's `done` snapshot, 381/896 bytes of `wrpat`/`rdbuf`/`rdbuf2` are
wrong (`capture --at 0x0333 --mem 0x4d5:0x380`) — record 19's slide
overwrites `wrpat` with BDOSX.BIN's own record 0 (destroying the write
pattern the exerciser meant to write) and record 20's slide overwrites
`rdbuf2` again. No on-disk writes happen (read-only slide, unlike FDEL's
landing) — this is DTA/work-area corruption, not disk corruption. Stock's
own genuine behaviour, recovered from the same snapshot: `rdbuf2` =
`01,04,07,…` (the `wrpat` pattern) — i.e. stock's WRRND really did write
record 1 to the read-opened file and RDRND read it back, confirming WRRND
performs a real disk write MSX-DOS-1 permits even on a read-mode FCB.

**Register contracts** (`capture --at 0x4788/0x4793 --nth 1/2 --mem
0xDA40:0x25`, records 18/19/20): entry is the FDEL dispatcher class, not
RDABS's — `A=$25` (stable, not required as fix input), `B=$00` (no
addr-low fingerprint), `C=$00` (NOT the function number), `DE=$DA40`
(kernel 37-byte FCB copy), `SP=$DBFE`, ret=`$D88A`. Unlike FDEL's
zero-filled copy, **this copy carries the live random field**: copy+33..35
= r0/r1/r2, copy+32 = CR (verified: +33=`$02` at record 18, `$01` at record
19). Exit (stock, all three records identical shape): `A=$00, H=$00, L=$00`.
The one clear random-op-specific FCB side effect: **CR (user FCB+32) :=
r0's low byte** post-call (`$DA60`=`$02` after record 18, `$01` after
record 19; final user FCB `$03D0` stock=`$01`). FCB+20/21/24/25 also differ
post-call in a way not fully resolved black-box (may be stock actively
updating them per-call, or a pre-existing mirror-field gap) — flag for the
acceptance diff during implementation, not a blocker for the fix shape.

**Conversion-helper check, confirmed by grep (not assumed):**
`grep -rn "rdrnd\|wrrnd\|random" disk/*.asm` → only `bdos_rdblk`'s
documented "random record 0 only" simplification (disk/driver.asm — always
`fat_open`s to file start). No FCB+33 reader, no record→cluster/sector seek
exists anywhere in the source. The random-field → `BDOS_RECIDX` →
`FAT_CURCLUS`/`FAT_CLUSSEC` positioning conversion is genuinely new code,
confirming §3 item 5's original assumption.

**Tentative fix shape (NOT signed off — see below):** two 3-byte pad-wires
at `$4788`/`$4793` (net-zero, `k_47B2` unaffected); a new shared positioning
helper (r0 → target sector `r0>>2` / intra-sector record `r0&3`, then
`fat_open` + walk `FAT_CLUSSEC`/`fat_advance` to it, seed `BDOS_DTA`/
`BDOS_BYTESLEFT`/`BDOS_RECIDX`/`SECTOR_BUF` per `bdos_seqread`'s own refill
contract); `rdrnd_body` = position + reuse `bdos_seqread` for one record +
CR update; `wrrnd_body` = position + **new** read-modify-write logic
(`fat_read_file_sector`, overlay 128 DTA bytes at `(r0&3)*128` into
`SECTOR_BUF`, `write_sector`) + CR update — **`wrrnd_body` cannot ride
`wrseq_body`'s `BDOS_WRMODE` dispatch** (the file is read-opened, WRMODE=0)
**nor call `bdos_seqwrite` directly** (that engine is append-oriented with
a 512-byte-flush model, wrong tool for a mid-file 128-byte overlay) — so
this is a small genuinely-new body, not a thin dispatch veneer over an
existing engine, a real (if narrow) departure from §4's non-goal framing
that needs sign-off before coding.

### 2.4 `$2F` RDABS — pure $00 pad, dispatch address trace-confirmed (LOW
risk, CONFIRMED lower-effort than FREN — no relocation needed)
`callwatch --in-func 0x2f` → two hits: `$46BA` then `$7831` (= `k_46C8`).
**Re-derived FREN-style** (per §6's lesson that callwatch-only reads can be
wrong about *what* the landing address is): `trace --anchor 0x0005 --nth 29
--steps 3000 --resync --window 600` (n=29 = BDOSX3's RDABS call) confirms
`$46BA` is the kernel's own real, fixed `$2F` dispatch address — stock
executes a genuine multi-instruction body from that exact byte (incl. a
`call $4555` and a `call $F270` detour, both re-converging) until the real,
non-reconverging fork at `$46C8` (stock continues past it; ours `ret`s via
`k_46C8`). Unlike FREN, **this is corrected the OTHER direction**: the
original "61 bytes into `bdos_create`'s body" claim was wrong — byte-verified
`$4680`-`$46C7` is pure `$00` pad (no source reference or jump lands there);
`bdos_create` itself is a 3-byte `jp bdos_create_body` diversion followed
immediately by that pad. So `$46BA` needs **no relocation at all** — a 3-byte
`jp` fits cleanly in 72 bytes of dead pad, net-zero, no shared-primitive risk
like `fdc_read_data`. `capture --at 0x0333` (BDOSX3 `done`) also surfaces a
finding §2.4 originally missed: RDABS is a **silent false-success**, not a
visible garbage status — record 22's `A=$00` already matches stock's genuine
success byte-for-byte, while `absbuf` stays stale (no real sector 0 transfer
happens); a status-only check would pass this as correct. Confirmed LOWER
risk than FREN (no relocation), same fix pattern otherwise: a `read_sector`-
based veneer wired directly at `$46BA`.

### 2.5 `$30` WRABS — mid-instruction collision with `bdos_seqwrite`'s live
tail, false success status (MEDIUM risk — needs a FREN-class relocation,
not a pad-wire like RDABS)
`callwatch --in-func 0x30` → three hits, `$4720,$4724,$4727`, landing inside
`bdos_seqwrite`'s body (`$46EE`) and running straight into `bsw_ok`
(`$4727`, disk/kernel.asm:1218 area) — `bdos_seqwrite`'s own SUCCESS exit
path. **Re-derived FREN/RDABS-style** (third M26 function in a row where the
callwatch-only read needed correction): `trace --resync` (anchored at
BDOSX3's `n=30` WRABS call) confirms `$4720` is the kernel's own real, fixed
`$30` dispatch address — and it is a **mid-instruction byte**: the
displacement byte of `jr c, bsw_full` at `$471F` (disk/fat.asm), which our
code decodes as `ex af,af'`. Ours executes exactly 5 real instructions
before reaching `bsw_ok`'s bare `ret` (`ex af,af'` → `ld hl,0` → `ld
(BDOS_WRBUFLEN),hl` → `xor a` → `ret`) — the buffer-drain tail of the
512-byte-flush path, NOT a clean NOP-slide like RDABS's pad landing. This
means WRABS currently returns a **false success status** (`A=$00`, matching
stock's genuine success byte-for-byte) while writing nothing to the target
sector, AND **unconditionally zeroes `BDOS_WRBUFLEN`** — harmless in
BDOSX3 (WRABS is the last call in the program) but real corruption for any
future program interleaving WRSEQ and WRABS. (Correction to the original
claim: `bsw_ok` itself, `xor a; ret`, mutates nothing — the buffer-zeroing
happens in the two instructions immediately BEFORE `bsw_ok`, which the
mid-instruction landing also runs through.) Because the landing point sits
inside `bdos_seqwrite`'s live body rather than dead pad, fixing this needs
the same relocate-then-wire shape as FREN (not RDABS's simple pad-wire) —
confirmed safe: `bdos_seqwrite`/`bsw_*`/`wrbytes_add_recsize` have exactly
two symbolic callers (driver.asm, kernel.asm's `jp bdos_seqwrite`) and zero
external jumps into the block's middle.

## 3. Risk ranking + proposed implementation order

1. **FREN** (`$17`) — simplest, fully localised NOP-slide, no shared-state
   risk. Fix shape: a `fren_body` veneer wired at the kernel's real `$17`
   dispatch address (not yet located precisely — `callwatch` only proves
   the LANDING point, not the dispatch instruction's own address; that
   needs a `trace --window` immediately before `$4392` to find the actual
   `call`/`jp` site, same technique used for M19/M21/M22b). Reuses M19's
   `fat_find`/name-match machinery to locate the old name, mirrors 8.3 name
   fields, does not need FAT/allocation changes (rename, not resize).
2. **RDABS** (`$2F`) — CONFIRMED (2026-07-03, Fable dispatch, `trace --resync`):
   dispatch address `$46BA` is pure `$00` pad, no relocation needed (simpler
   than FREN, which needed one) — see §2.4. Straightforward `read_sector`-
   based veneer (LBA sector from DE, count from H, drive from L, target the
   FCB's DTA) — very close in shape to the low-level primitive Tier-1 DSKIO
   already implements.
3. **WRABS** (`$30`) — CONFIRMED (2026-07-03, Fable dispatch, `trace
   --resync`): dispatch address `$4720` is a mid-instruction byte inside
   `bdos_seqwrite`'s live tail (the `jr c, bsw_full` displacement), needing
   a FREN-class relocation rather than RDABS's pad-wire — see §2.5/§8.
   Mirror-write of RDABS's veneer shape (dskio, Cy=1, DTA source).
4. **FDEL** (`$13`) — CONFIRMED (2026-07-03, Fable dispatch, `trace
   --resync` + on-disk `$E5` forensics): dispatch address `$436C` is dead
   pad in the post-FREN corridor (RDABS-shape, no relocation needed) — but
   landing FREN moved what's UNDER the pad, so ours currently NOP-slides
   into `fren_body` with FDEL's own FCB, actively corrupting the target
   directory entry (renames it to an all-`$00` name, a scan terminator) and
   leaking its FAT chain. Fix reuses M19's `fat_find` to locate the entry
   (single-match, same precedent as FREN — wildcard support is an open scope
   question, see §2.2), writes `$E5` to its first byte, and — contrary to
   §4's original assumption — must also walk and free the file's FAT12
   chain in both on-disk FAT copies (confirmed 2-cluster test file, chain
   entries zeroed by stock; §4 updated below).
5. **RDRND / WRRND** (`$21`/`$22`) — LAST. RE-CHARACTERISED 2026-07-03
   (Fable dispatch, `trace --resync` + `trace --regdump`, post-FDEL ROM):
   the original "one shared dispatch" claim was a `callwatch` dedup
   artifact — there are **two** separate dead-pad dispatches, `$4788`
   (RDRND) and `$4793` (WRRND), both RDABS-shape (no relocation needed) —
   see §2.3. The mandated `trace --regdump` pass confirms the un-wired
   landing streams the ENTIRE open file into the caller's DTA on every
   call (not a one-record advance), trampling `wrpat`/`rdbuf`/`rdbuf2` at
   BDOSX3's `done` snapshot; no on-disk writes happen (work-area
   corruption only, unlike FDEL). Fix needs a genuinely new shared
   positioning helper (FCB random field r0/r1/r2 at +33..35 →
   `BDOS_RECIDX` → `FAT_CURCLUS`/`FAT_CLUSSEC`, confirmed absent anywhere
   in source by `grep`) — comparable in scope to M25's `fopen_fill_body`
   seed but for arbitrary mid-file positioning. `rdrnd_body` can then
   reuse `bdos_seqread` for the actual record transfer; `wrrnd_body`
   CANNOT reuse `wrseq_body`/`bdos_seqwrite` (wrong dispatch mode / wrong
   engine shape for a mid-file 128-byte overlay) and needs its own small
   read-modify-write body instead — a real, if narrow, departure from §4's
   "reuse the existing bodies" framing. Tentative fix shape, NOT signed
   off — see §2.3's closing paragraph.

## 4. Explicit non-goals for this spec

- ~~No FAT allocation/extension logic beyond what FDEL's delete-marker write
  needs...~~ **FALSIFIED 2026-07-03 (§2.2):** BDOSX3's scratch file is
  2 clusters, and stock zeroes both FAT12 chain entries in both on-disk FAT
  copies on delete. `fdel_body` DOES need chain-walking/freeing logic — a
  small, bounded walk (this test file is short), not general
  allocation/extension code; still no new FAT-growth logic of the kind
  OPEN/WRSEQ needed.
- No change to `bdos_seqread_body`/`bdos_seqwrite_body`/`k_47B2` themselves
  — RDRND/WRRND's fix should REUSE them (matching the M25 precedent of a
  thin dispatch veneer over the existing engine), not duplicate their logic.
- No attempt to fix all six functions in one commit. Per §3's ordering,
  each function should land as its own falsify-first micro-milestone with
  its own re-verification pass (BDOSX3 zero-diff for that record, plus the
  full standing regression suite: BDOSX/BDOSX2/BDOSX0/boot callseq/DIR
  screen/`make unit-test`/`make probe`), same discipline as M19/M21/M24/M25.

## 5. Open questions for sign-off

1. Does the proposed order (FREN → RDABS → WRABS → FDEL → RDRND/WRRND) match
   your risk tolerance, or would you rather front-load the highest-risk
   RDRND/WRRND investigation (§2.3's `trace --regdump` pass) before touching
   anything, on the theory that its answer might also inform FDEL's dir-scan
   question in §2.2?
2. OK to proceed one function at a time without a fresh sign-off per function
   (i.e. treat this spec as covering the whole block), or do you want each
   function's actual implementation to come back for its own review given
   RDRND/WRRND's shared-state risk?
3. FDEL's cluster-chain-freeing assumption (§4, first bullet) — confirm
   BDOSX3's `BDOSXR  TMP` scratch file is single-cluster before treating
   "just write `$E5`" as sufficient, or should this spec wait for that check
   before being considered final?

## 6. FREN (`$17`) — LANDED 2026-07-03

Given repeated "continue" and this being the explicitly offered lowest-risk
default (§3 item 1), proceeded with FREN alone; the other five functions in
this block are UNTOUCHED and still require the sign-off in §5.

**Refined characterisation before implementing:** `trace --resync` (anchored
at BDOSX3's call n=17, the FREN call) found the REAL fork — `$4392: ex
af,af'` diverges (stock jumps to its own real FREN body from this exact
address; ours falls through) — confirming `$4392` is genuinely the fixed
inter-slot dispatch address the kernel calls for `$17`, not merely a
coincidentally-touched address. This upgrades §2.1's risk read slightly:
`$4392` isn't dead/unrelated space, it's byte 56 of the 74-byte
`fdc_read_data` routine (disk/driver.asm) — the shared low-level FDC
sector-read primitive used by EVERY disk read on the whole ROM. Checked
before touching it: `fdc_read_data` has exactly ONE caller
(`call fdc_read_data` in `fdc_rp_attempt`, symbolic) and no external code
jumps into its middle — fully self-contained, so it relocates cleanly with
no manual call-site fixups (matching the M21a `fdc_di_save` precedent).

**Fix:** relocated the 74-byte `fdc_read_data` body verbatim to
`fdc_read_data_body` (disk/kernel.asm free tail, appended after
`wrseq_body` — the file's genuine end, not the tightly-packed
write_sector/GDATE corridor, which turned out to have no slack for a
74-byte insert and produced a real "64KB limit passed" build error on the
first attempt). `disk/driver.asm`'s `fdc_read_data` is now a 3-byte `jp
fdc_read_data_body` thunk, followed by `ds $4392 - $, $00` / `k_4392: jp
fren_body` / `ds $43A4 - $, $00` — net-zero, so `fdc_write_phys`
(the very next real routine) stays at its exact original address.

**`fren_body`** (disk/fat.asm, next to `fopen_fill_body`): reuses
`fat_mount`/`fat_find`/`write_sector` exactly as designed in §3 item 1 —
`fat_find` on the FCB's old name (+1..11) returns the matched directory
entry inside `SECTOR_BUF` with `FAT_DIRSEC` holding its sector number;
`fren_body` overwrites the entry's 11-byte name field in place with the
new name (FCB+17..27) via `ldir` and calls `write_sector` to persist it.
Not-found and I/O-error branches both clear `$F306` per the M20 rule and
return `A=$FF`/`Cy=1`.

**Verification:**
- BDOSX3 record 14's own status byte (`regs+14*8+1` = `$0446`) — the
  originally reported `A=$FC` — now reads `$00` on both stock and ours:
  **zero-diff**, confirmed by `capture --mem 0x3b0:0x125` before/after
  comparison (36 diverging bytes pre-fix → 24 post-fix, all 13 removed
  bytes clustered around `$0446`/`$044E`/`$045E`/`$3B1`/`$3BF-3D0`
  region). One byte (`$03C8` = FCB+24) newly visible in the post-fix diff
  set turned out to be the SAME already-logged FCB-mirror-field gap from
  the M25 doc (FCB+16/17/20/21/24/28/29) — confirmed by offset match, not
  a new regression; it's only visible now because FREN succeeding changes
  which real code path the downstream still-un-wired FDEL/FOPEN/RDRND take.
- Records 15+ (FDEL onward) remain diverging, as expected — those five
  functions are still un-wired per §2, untouched by this fix.
- **Tier-1 regression (critical, since `fdc_read_data` is shared by every
  disk read on the ROM):** `make probe` — DSKIO byte-identical to the
  CF-3300 reference (sectors 0 and 14), BASIC probe green, tape probe
  green. `make unit-test`: 19/19.
- Boot `callseq` (27 shared calls to `A>`): aligned, zero divergence.
- `DIR` `screen` (both machines): byte-identical, including the `41 files`
  / `375808 bytes free` / `A>.` footer and the full VRAM hex dump.
- Phase-1 BDOSX (`--mem 0x400:0x180`, RDSEQ content): 48 diverging bytes
  both before AND after this fix (byte-count identical) — confirmed via
  the git-stash/rebuild-baseline technique that this is the SAME
  already-logged pre-existing RDBLK-content gap from `$500`+ (M25 doc
  "M26 candidate" item (b)), unaffected by the FREN fix.
- BDOSX2: memory zero-diff (0 of 112 bytes); a benign `AF` flag-only
  register difference, consistent with prior BDOSX2 runs.
- BDOSX0: `callseq --log 0x0005` 43/43 shared calls aligned, no divergence.

`disk.rom` stays exactly 16384 B (no wrap warnings after moving the
insertion point to kernel.asm's genuine free tail). Changed:
disk/driver.asm (relocation thunk + veneer), disk/kernel.asm
(`fdc_read_data_body`), disk/fat.asm (`fren_body`).

## 7. RDABS (`$2F`) — LANDED 2026-07-03

Per §5's now-confirmed default order and the §2.4 re-characterisation (Fable
dispatch, `trace --resync`): `$46BA` is pure `$00` pad, no relocation
needed — simplest of the six. Fix wired directly in the pad: `disk/fat.asm`'s
`bdos_create` dispatch corridor (`bdos_create: jp bdos_create_body` / `ds
$46C8 - $, $00` / `jp k_46C8`) now splits at `$46BA`: `ds $46BA - $, $00` /
`k_46BA: jp rdabs_body` / `ds $46C8 - $, $00` — net-zero, `k_46C8` stays at
its exact address.

**Register contract pinned by black-box `capture`, not assumed:** entry
`capture --at 0x46ba --nth 1 --machine stock` (before writing any code)
showed `B=$BA` (the canonical-address-low-byte fingerprint, same convention
as the `$53A7` CONOUT worker's `B=$A7`), `C=$2F` (function number,
preserved from the caller), `DE=$0000` (start sector), `HL=$0100` (H=1
sector count, L=0 drive) — exactly BDOSX3's own `H=1 L=0 DE=0` call,
confirming registers pass through the kernel's dispatch unmolested. Exit
contract pinned from stock's own record-22 snapshot (`capture --at <done>
--mem <regs+22*8>:8`): `A=$00 B=$00 C=$01 D=$00 E=$00 H=$00 L=$00` — `C`
carries the original sector count back out (not part of the published
map.grauw.nl contract, which only documents `A`, but matched anyway since
BDOSX3's zero-diff bar covers the full register snapshot, same discipline
as M22a's VERIFY/CPMVER work).

**`rdabs_body`** (disk/fat.asm, next to `fren_ioerr`): reads via `dskio`
directly (disk/driver.asm) rather than `read_sector`, since RDABS must
honour an arbitrary sector count (`H`), not fix it at one; target buffer is
the runtime DTA (`DOS_DTAPTR`, `$F23D` — M19/M21 precedent). `dskio`
clobbers `B`/`C` internally for its own CHS bookkeeping, so the original
count is saved on the stack across the call and restored into `C` (and
zeroed into `B`) afterward, matching the pinned exit values. Error path
preserves `dskio`'s real returned error code across the `$F306` clear
(unlike `fren_ioerr`'s hardcoded-`2` precedent) — untested by BDOSX3 (record
22 always succeeds) but more correct against the published contract, at no
extra cost.

**Verification:**
- BDOSX3 record 22 (`--mem 0x3d5:0x100`, full `regs` array): baseline
  (FREN-only, pre-RDABS-fix) showed 19 diverging bytes; post-fix shows 16 —
  confirmed via the git-stash/rebuild-baseline technique that the exact 3
  removed bytes are record 22's `B`/`C`/`H` fields (the RDABS garbage this
  fix targets) and the remaining 16 are unchanged, pre-existing, already-
  logged gaps (FCB-mirror fields etc.) — zero new regressions.
- **Tier-1 regression:** `make probe` — DSKIO byte-identical to the CF-3300
  reference, BASIC probe green, tape probe green. `make unit-test`: 19/19.
- Boot `callseq --log 0x0005` (no keys, boot-to-`A>` only): 18/18 shared
  calls aligned, zero divergence.
- `DIR` `screen` (both machines): byte-identical, including the `41 files`
  / `375808 bytes free` / `A>.` footer and the full VRAM hex dump.
- BDOSX (`--mem 0x400:0x180`): zero-diff (0 of 384 bytes), register diffs
  NONE.
- BDOSX2 (`--mem 0x340:0x70`): zero-diff (0 of 112 bytes), register diffs
  NONE.
- BDOSX0: `callseq --log 0x0005` 43/43 shared calls aligned, no divergence.

`disk.rom` stays exactly 16384 B (no wrap warnings). Changed: disk/fat.asm
only (`k_46BA` veneer + `rdabs_body`/`rdabs_ioerr`).

Investigation credit: characterised by a Fable subagent dispatch (per
[[opus-vs-sonnet-model-split]], corrected after a process lapse — see
[[tier2-review-queue]] M26 Follow-up 3); implementation + verification by
Sonnet 5 direct.

## 8. WRABS (`$30`) — LANDED 2026-07-03

Per §5's confirmed order and the §2.5 re-characterisation (Fable dispatch,
`trace --resync`): `$4720` is a mid-instruction byte — the displacement of
`jr c, bsw_full` inside `bdos_seqwrite`'s live tail (disk/fat.asm) — not
dead pad like RDABS. Fixed the same way as FREN: relocated the whole
`bdos_seqwrite`/`bsw_ok`/`bsw_full`/`bsw_err`/`wrbytes_add_recsize` unit
verbatim to `bdos_seqwrite_body` (disk/kernel.asm free tail, appended after
`fdc_read_data_body`); `disk/fat.asm`'s `bdos_seqwrite` is now a 3-byte `jp
bdos_seqwrite_body` thunk. Checked safe to relocate first: exactly two
symbolic callers (`jp bdos_seqwrite` in driver.asm and kernel.asm), zero
external jumps into the block's middle — confirmed by `grep` before
touching it, same due-diligence as the FREN/`fdc_read_data` precedent. The
freed span at `$4720` is wired `k_4720: jp wrabs_body`, with `ds`-padding
recomputed automatically up to the next pinned entry (`k_477D`, WRSEQ/RDSEQ
shared, unaffected).

**`wrabs_body`** (disk/fat.asm, mirrors `rdabs_body` exactly): `dskio`
direct call with `Cy=1` (write direction) instead of `Cy=0`, source =
runtime DTA via `DOS_DTAPTR`. Entry/exit register contract pinned by
black-box `capture` (BDOSX3 record 23, H=1): identical shape to RDABS's own
pinned contract — `A=$00 B=$00 C=$01 D=$00 E=$00 H=$00 L=$00` on success,
`C` echoing the input sector count. This fix also incidentally removes the
`BDOS_WRBUFLEN`-zeroing side effect §2.5 found (the old mis-landing ran
through the buffer-drain tail unconditionally on every WRABS call) — no
separate fix needed, relocating the block away from the dispatch point
removes the fall-through entirely.

**Verification:**
- BDOSX3 record 23 (`--mem 0x3d5:0x100`, full `regs` array): baseline
  (FREN+RDABS, pre-WRABS-fix) showed 16 diverging bytes; post-fix shows 13
  — confirmed via the git-stash/rebuild-baseline technique that the exact 3
  removed bytes are record 23's `B`/`C`/`H` fields (the WRABS garbage this
  fix targets), the remaining 13 unchanged, pre-existing gaps — zero new
  regressions.
- **Tier-1 regression (critical, since `bdos_seqwrite` is the shared WRSEQ
  worker used by every sequential write on the ROM):** `make probe` — DSKIO
  byte-identical to the CF-3300 reference, BASIC probe green, tape probe
  green. `make unit-test`: 19/19.
- Boot `callseq` (no keys, boot-to-`A>` only): 18/18 shared calls aligned,
  zero divergence.
- `DIR` `screen` (both machines): byte-identical.
- BDOSX (`--mem 0x400:0x180`, exercises WRSEQ via the relocated body):
  zero-diff (0 of 384 bytes), register diffs NONE.
- BDOSX2 (`--mem 0x340:0x70`): zero-diff (0 of 112 bytes), register diffs
  NONE.
- BDOSX0: `callseq --log 0x0005` 43/43 shared calls aligned, no divergence.

`disk.rom` stays exactly 16384 B (no wrap warnings). Changed: disk/fat.asm
(thunk + `k_4720` veneer + `wrabs_body`/`wrabs_ioerr`), disk/kernel.asm
(`bdos_seqwrite_body`).

Investigation credit: characterised by a Fable subagent dispatch (per
[[opus-vs-sonnet-model-split]]); implementation + verification by Sonnet 5
direct.

## 9. FDEL (`$13`) — LANDED 2026-07-03

Per §5's confirmed order and the §2.2 re-characterisation (Fable dispatch,
`trace --resync` + on-disk `$E5` forensics): `$436C` is dead pad in the
post-FREN corridor (disk/driver.asm), same RDABS-shape dispatch as `$46BA`
— split the same way: `ds $436C - $, $00` / `k_436C: jp fdel_body` / `ds
$4392 - $, $00` (net-zero, `k_4392`/`fren_body` unaffected). Two scope
questions from §2.2 were signed off before coding: single exact-match only
(reuse `fat_find`, same as FREN — no `?` wildcard support), and the
FAT12 chain-free addition confirmed in scope despite §4's original
(falsified) non-goal assumption.

**`fdel_body`** (disk/kernel.asm free tail, appended after
`wrbytes_add_recsize` — NOT disk/fat.asm's own end): reuses `fat_mount`/
`fat_find` to locate the target by name (kernel FCB-copy pointer at DE,
name field at +1, same convention as `fren_body`), then (a) walks and
frees the file's FAT12 chain — `fat_next_cluster` to read each link before
`fat_write_fat_entry` zeroes it (every on-disk FAT copy), stopping at the
first value `>= $0FF8` (end-of-chain) — and only THEN (b) re-runs `fat_find`
to get a fresh directory-entry pointer (the chain walk clobbers `SECTOR_BUF`
via `fat_next_cluster`/`fat_write_fat_entry`, which both use it as scratch,
so re-locating after the walk is simpler and cheaper than threading a
pointer across a clobbering call) and stamps its first byte `$E5`,
persisted via `write_sector`. `IX` holds the FCB-copy pointer across every
helper call in the body — confirmed by inspection that none of
`fat_mount`/`fat_find`/`fat_next_cluster`/`fat_write_fat_entry`/
`read_sector`/`write_sector` touch it.

**Placement lesson (new this slice):** `fdel_body` first landed appended to
disk/fat.asm's own end, following the RDABS/WRABS-ioerr precedent of small
veneers living there — this built with no error but silently broke
`test_gdate.py`/`test_getdpb.py` (14 host-unit-test failures, all-zero DPB
fields). Root cause: disk.asm includes fat.asm immediately before
kernel.asm (`disk.asm`'s fixed include order), and kernel.asm has its own
tightly-packed pinned-address corridor (GDATE `$553C` etc.) with no slack
to absorb fat.asm growing past where RDABS/WRABS's small ~20-byte veneers
had left it — the same "64KB limit passed" hazard class the FREN slice hit
once already (§6), just silent this time instead of a hard build error.
Moved to disk/kernel.asm's own free tail (verified genuinely free already,
same location as `fdc_read_data_body`/`bdos_seqwrite_body`) and the
failures disappeared. **Standing rule going forward: any body added in this
milestone that's bigger than a trivial few-instruction veneer belongs in
kernel.asm's free tail, not fat.asm's end — re-run `make unit-test` after
EVERY body placement, not just after the full implementation, to catch this
class of silent corruption immediately.**

**Verification:**
- BDOSX3 record 15 (`--mem 0x44d:0x8`, single-record snapshot): zero-diff
  (0 of 8 bytes) — confirmed via the git-stash/rebuild-baseline technique
  that the pre-fix state had exactly one diverging byte here (`L`, stock
  `$00` / ours `$0A`), now fixed. Record 16 (FOPEN-post-delete, expect
  `A=$FF`) still diverges in `H`/`L` on both the pre- and post-fix builds
  with the SAME byte count — confirmed pre-existing (a FOPEN-on-not-found
  HL-contract gap, unrelated to FDEL's own correctness; `A=$FF` already
  matched stock before this fix). Full `regs` array (`--mem 0x3d5:0x100`):
  12 diverging bytes post-fix vs. 13 pre-fix, exactly record 15's `L` byte
  removed, all other pre-existing gaps unchanged.
- `make unit-test`: 19/19 (the placement bug above made this 5/19 at one
  point mid-slice — always re-run this after moving code, not just at the
  end).
- `make probe`: DSKIO byte-identical to the CF-3300 reference, BASIC probe
  green, tape probe green.
- Boot `callseq --log 0x0005` (no keys, boot-to-`A>` only): 18/18 shared
  calls aligned, zero divergence.
- `DIR` `screen` (both machines): byte-identical.
- BDOSX (`--mem 0x400:0x180`): baseline-diff confirmed the SAME 127
  diverging bytes before and after (byte-count and positions identical) —
  the pre-existing `$500+` RDBLK-content gap, unaffected by this fix.
- BDOSX2 (`--mem 0x340:0x70`, `--arm-check-val 0xcd`, needs `--keys2 'xyz'
  --keys2-at 32` per the M22 CPMVER precedent): zero-diff (0 of 112 bytes).
- BDOSX0: `callseq --log 0x0005` 43/43 shared calls aligned, no divergence.

`disk.rom` stays exactly 16384 B (no wrap warnings). Changed: disk/driver.asm
(`k_436C` veneer), disk/kernel.asm (`fdel_body`/`fdel_miss`/`fdel_ioerr`/
`fdel_relocate`/`fdel_free_loop`/`fdel_chain_ioerr`).

Investigation credit: characterised by a Fable subagent dispatch (per
[[opus-vs-sonnet-model-split]]); implementation + verification by Sonnet 5
direct.

## 10. RDRND (`$21`) / WRRND (`$22`) — LANDED 2026-07-03

Per §2.3's re-characterisation (Fable dispatch, `trace --resync` +
`trace --regdump`): two separate dead-pad dispatches, `$4788` (RDRND) and
`$4793` (WRRND), both inside the existing `fat_find` corridor pad
(disk/fat.asm) — RDABS-shape, no relocation. One scope decision was signed
off before coding: proceed with the full characterised shape, including the
genuinely-new positioning helper and WRRND's own read-modify-write body
(neither is a thin veneer over an existing engine, the one real departure
from this spec's original "reuse the existing bodies" framing).

**Scope, signed off at implementation time:** only the FCB random field's
`r0` byte (copy+33) positions the record (0..255, up to a 32640-byte file);
`r1`/`r2` (copy+34/+35) are not read. BDOSX3 only exercises `r0` ∈ {1,2};
this is the same class of narrowing as FREN's/FDEL's single-exact-match
precedent, not a generalised random-access engine.

**`rrnd_position`** (disk/kernel.asm free tail, shared by both bodies):
reseeds `BDOS_DTA` from `DOS_DTAPTR` (the recurring M19 lesson — the
kernel's real SETDTA never touches our own mini-BDOS's DTA cell), calls
`fat_open` to reset the iterator to the file's first cluster, then computes
the target sector-in-file (`r0 >> 2`) and record-in-sector (`r0 & 3`) and
walks to it by calling the existing `fat_read_file_sector` exactly
`(sector-in-file + 1)` times — reusing its own cluster-advance and sector-
address arithmetic rather than re-deriving a fast seek. `BDOS_BYTESLEFT` is
set to `FAT_FILESIZE - r0*128` (safe as a 16-bit subtraction since `r0*128`
never exceeds 32640) so a subsequent `bdos_seqread` correctly delivers a
partial final record and the right EOF behaviour. `BDOS_RECIDX` is set to
the stashed record-in-sector value. A target beyond EOF clamps
`BDOS_BYTESLEFT` to 0 (immediate-EOF shape) and a seek that runs off the
end of the chain (e.g. a WRRND asked to position past the last allocated
cluster) returns `Cy=1` — FAT growth on a random-write-past-EOF is
explicitly out of scope, same non-goal as every other M26 fix.

**`rdrnd_body`**: positions via `rrnd_position`, then calls `bdos_seqread`
verbatim for the transfer (§4 non-goal: no change to `bdos_seqread_body`
itself) — a thin veneer, as originally hoped.

**`wrrnd_body`** (the genuinely new part): **cannot** ride `wrseq_body`'s
`BDOS_WRMODE` dispatch or call `bdos_seqwrite` directly — that engine is
append-oriented (a file opened by FMAKE, 512-byte-flush model), the wrong
shape for overlaying 128 bytes mid-file into a file opened for read by
FOPEN. Instead: overlay the caller's DTA record into `SECTOR_BUF` at
`BDOS_RECIDX*128` (`rrnd_position`'s seek already loaded the right sector),
then persist via `write_sector`. Because `fat_read_file_sector` doesn't
expose the absolute sector number it just read, a small new helper
(`rrnd_sector`) mirrors the same `firstData + (cluster-2)*secPerClus +
clussec` arithmetic `frs_mul_body` already uses internally — without
modifying `frs_mul_body` itself (§4 non-goal) — using the state
`fat_read_file_sector` always leaves behind after a read: `FAT_CURCLUS`
already correctly advanced, `FAT_CLUSSEC` incremented by exactly one past
the sector just read (so `FAT_CLUSSEC - 1` safely recovers it, with no
off-by-one or cluster-boundary hazard — confirmed by reading
`fat_read_file_sector`'s own body: the increment always follows the read,
never precedes it).

Both bodies additionally reproduce the one clear random-op-specific FCB
side effect the register-contract capture surfaced: `CR` (copy+32) :=
`r0`'s value post-call — unlike FDEL's `DE=$03D0` exit artifact, this is
NOT something the kernel's own copy-back reproduces for free, so both
bodies write it explicitly.

**Verification:** BDOSX3's `done` snapshot (`--mem 0x4d5:0x380`, the
`wrpat`/`rdbuf`/`rdbuf2`/`absbuf` block) went from 381/896 bytes differing
(pre-fix, the un-wired whole-file DTA-stream corruption from §2.3) to
127/896 — isolated per-buffer (`--mem 0x4d5:0x80` `wrpat`, `--mem 0x5d5:0x80`
`rdbuf2`, `--mem 0x655:0x200` `absbuf`): all **0 of N bytes differ**. The
§2.3 FCB+20/21/24/25 "not fully resolved black-box" flag also checked out
clean: `--mem 0x465:0x18` (the `regs` snapshot array's 8-byte entries for
records 18/19/20) is **0 of 24 bytes differ** — whatever those fields do,
BDOSX3's own acceptance bar doesn't observe a gap, so this is resolved as
a non-issue for this milestone, not a deferred residual. The
remaining 127 bytes are entirely `rdbuf` (`--mem 0x555:0x80`, 127/128) —
record 12's RDSEQ round-trip content, unrelated to RDRND/WRRND and
confirmed pre-existing via the git-stash/rebuild-baseline technique (the
FDEL-only baseline ROM shows the identical 127/128 `rdbuf` diff and the
identical 381/896 whole-block diff before this fix). Full regression suite:
`make unit-test` 19/19 (checked immediately after placement, per the FDEL
placement-lesson standing rule — this slice built clean the first time,
`kernel.asm`'s free tail from the start), `make probe` all green, boot
`callseq` 18/18 aligned, BDOSX zero-diff (0 of 384 bytes, two ranges),
BDOSX2 zero-diff (0 of 112 bytes), BDOSX0 `callseq --log 0x0005` 43/43
aligned.

`disk.rom` stays exactly 16384 B (no wrap warnings). Changed: disk/fat.asm
(`k_4788`/`k_4793` pad-wires), disk/kernel.asm (`rrnd_position`/
`rrnd_sector`/`rdrnd_body`/`wrrnd_body`/`rrnd_finish`/`rrnd_eof`/
`wrrnd_ioerr`).

**This closes M26 — all six functions (FREN, RDABS, WRABS, FDEL, RDRND,
WRRND) are now landed. Full BDOS surface coverage is complete
(tier2-bdos-coverage.md: 8/8 ✅).**

Investigation credit: characterised by a Fable subagent dispatch (per
[[opus-vs-sonnet-model-split]]); implementation + verification by Sonnet 5
direct.

---

Ground truth: [tier2-STATE.md](tier2-STATE.md). Judgment-call log for this
characterisation pass: [tier2-review-queue.md](tier2-review-queue.md) (M26
entry). Design/fix-shape precedents: [tier2-m19-spec.md](tier2-m19-spec.md)
(SFIRST/SNEXT reuse), [tier2-m21-spec.md](tier2-m21-spec.md) (generic body
trusting prior-call state), [tier2-m24-fclose-multicluster-spec.md](tier2-m24-fclose-multicluster-spec.md)
+ its "M25 RESOLVED" section (shared-dispatch-by-internal-flag pattern this
spec's RDRND/WRRND proposal reuses).
