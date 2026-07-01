<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 BDOS FCB-read cluster — CHARACTERISATION + SCOPING (spec pass, no asm)

**Status: CHARACTERISED (2026-07-01, Opus span). CHARACTERISE + SCOPE ONLY — no asm
touched, no fix implemented. STOP for sign-off** (per [[spec-before-implementation]]:
this is a new batch of functions, not a pre-approved veneer-class fix). Resume board:
[tier2-STATE.md](tier2-STATE.md). Fix-shape templates: [tier2-m17-spec.md](tier2-m17-spec.md)
(veneer + cell), [tier2-oi3-spec.md](tier2-oi3-spec.md) (new-routine class).

## 0. TL;DR / headline scoping call
The cluster is **reachable now** — no new trigger infrastructure is needed. A single
`--keys '\rDIR\r'` burst (Enter at the date prompt, then `DIR`+Enter at `A>`) drives
COMMAND.COM into the FCB dir-search cluster, so the harness limitation noted in the
prior sweep ("only one keystroke burst") is **NOT a blocker** — openMSX `type` plays the
whole string sequentially, and COMMAND.COM's own `DIR` builtin issues the calls. **The
BDOS-exerciser `.COM` is NOT required for this cluster** (it is still wanted for the
console tier and for `$23`/`$26`/`$27`, see §5).

**But the cluster is NOT a batch of small veneers.** Only ONE real, reachable bug exists
here, and it is BIG:

- **`$11` SFIRST / `$12` SNEXT (directory search) are un-wired kernel entries** on ours
  (`$4FB8` = SFIRST, `$5006` = SNEXT, both `$00` NOP-padding), so the kernel's CALL
  NOP-slides into the `$50A9` stub tail (`$50AD`), which returns a bogus "entry found"
  contract. Result: `DIR` finds the same phantom entry forever — ours hangs in a
  `SETDTA`/`SNEXT` loop and prints **nothing** (stock lists 41 files). This is the same
  *class* as M13/M17/M18 (un-wired `$50xx`/`$4xxx` kernel entry) but the *body* is a
  **large real directory-search routine** (stock spans 108/101 distinct page-1 PCs across
  `$4E–$78xx`), NOT a 3-byte read-a-cell veneer. **This is the one item worth a spec, and
  it is a substantial implementation, not a veneer.**
- **`$10` FCLOSE, `$14` RDSEQ, `$1A` SETDTA, `$0F` FOPEN, `$23` FSIZE, `$26` WRBLK-read,
  `$27` RDBLK**: NOT independently reachable/falsifiable by any natural COMMAND.COM builtin
  in a way that isolates THEM. `$0F`/`$1A` ARE exercised (boot + DIR) and are byte-identical
  where they appear; the rest need a purpose-built exerciser `.COM`.

**Recommendation (honest): PIVOT.** Do NOT proceed with "the FCB-read cluster" as a batch —
it isn't one. Two independent tracks fall out:
  1. **`$11`/`$12` dir-search** is a real, visible, reachable bug (DIR is broken on ours) —
     it deserves its own dedicated spec + implementation, but it is a **big routine**, not a
     veneer, so it should be scoped and signed off as its own milestone (call it **M19**),
     not lumped into a "read cluster" batch.
  2. **The rest of the cluster** (`$10/$14/$23/$26/$27`, plus the prior console tier) is
     **blocked on the BDOS-exerciser `.COM`** ([[bdos-exerciser-com-test]]) for isolated
     per-function differential testing. That tool should come **before** any attempt to
     verify/implement those functions. The ranked order was wrong: the exerciser is a
     prerequisite, not a later nicety.

## 1. Scope (as briefed) and what each function actually is
Briefed cluster: `$10` FCLOSE, `$14` RDSEQ, `$1A` SETDTA, `$11`/`$12` SFIRST/SNEXT,
`$23` FSIZE, `$0F` FOPEN (runtime re-confirm), `$26`/`$27` RDBLK/WRBLK read-direction.
Published contract source for every function below: MSX-DOS 1 BDOS call table
(map.grauw.nl MSX-DOS function list / MSX2 Technical Handbook §BDOS / MSX Datapack).

**Architecture reminder (the load-bearing distinction, re-confirmed this span):** there
are TWO separate BDOS surfaces in our tree and they must not be conflated —
- **`bdos_entry` (SYSTEM `$F37D` vector, `disk/driver.asm:626`)** is our OWN private
  mini-BDOS. It is called ONLY by our COMMAND.COM loader `k_47B2` (`disk/kernel.asm:379`)
  via CALSLT, to load COMMAND.COM off disk during boot. It implements a read subset
  (`$0F/$14/$10/$1A/$27` + write path) purely for that loader. **User-program / COMMAND.COM
  runtime BDOS calls do NOT go here.** So the fact that `bdos_entry` already "implements"
  `$14`/`$10`/`$1A`/`$27` does NOT mean the runtime path works — those bodies are unreachable
  from the runtime kernel.
- **The runtime BDOS** is the relocated RAM MSX-DOS-1 kernel that COMMAND.COM calls at
  `$0005`. It reaches our disk ROM ONLY through specific page-1 kernel entries (the M13/M17/
  M18 `$50xx` / `$4xxx` pattern) + the `$F368`/`$F36B` work-area hooks. **This is the surface
  every function in this cluster is really about.**

## 2. Reachability matrix (falsify-first — what the harness can actually trigger)
Method: `probes/disk/disk_probe_diff.py`, test.dsk, anchored at COMMAND.COM `$0100`,
`--keys` burst as noted. "Naturally issued" = appears in the `callseq --log 0x0005` stream.

| Func | Name | Natural trigger | Reachable NOW? | Result on ours |
|---|---|---|---|---|
| `$0F` | FOPEN | boot (n=2) + `DIR`/`TYPE` | **YES** | byte-identical where seen (boot n=2 `C=0F A=24 DE=D62F`), settled fact |
| `$1A` | SETDTA | `DIR` (n=30,32) | **YES** | byte-identical at entry (`DE=D403`/`D3DB`), aligned through n=33 |
| `$11` | SFIRST | `DIR` (n=31) | **YES** | **BROKEN** — un-wired `$4FB8`, NOP-slides to `$50A9` stub, bogus "found" |
| `$12` | SNEXT | `DIR` (n=33…) | **YES** | **BROKEN** — un-wired `$5006`, same slide; loops forever (80×) |
| `$14` | RDSEQ | `TYPE <file>` (not DIR) | PARTIAL — needs a TYPE of a real file; not isolable from FOPEN/SETDTA/FCLOSE | unverified at runtime |
| `$10` | FCLOSE | `TYPE`/program exit | PARTIAL — same as `$14` | unverified at runtime |
| `$23` | FSIZE | no COMMAND.COM builtin issues it | **NO** — needs exerciser `.COM` | unverified |
| `$27` | RDBLK | MSXDOS.SYS boot only (loader-internal), no COMMAND.COM builtin | **NO** at runtime — needs exerciser `.COM` | unverified at runtime |
| `$26` | WRBLK (read dir) | no COMMAND.COM builtin | **NO** — needs exerciser `.COM` | unverified |

**Decisive evidence for the SFIRST/SNEXT break (the one live bug):**
- `callseq --at 0x0100 --log 0x0005 --maxhits 90 --keys '\rDIR\r' --keys-at 22 --settle 60`:
  ours == stock **byte-identical for the first 33 calls** (incl. n=30 SETDTA, n=31 SFIRST,
  n=32 SETDTA, n=33 SNEXT — same C/A/B/DE/HL/ret). **FIRST DIVERGENCE at n=34.** Stock's
  n=34 is `C=02 CONOUT A=4C` (starts printing the listing — `L`, `I`, `S`, `T`…); ours' n=34
  is `C=1A SETDTA` again — ours re-enters the SETDTA→SNEXT search loop and never leaves it
  (n=34..90 = an endless `1A`/`12` alternation, `DE=005C HL=5800` each time).
- `callwatch --machine ours --in-func 0x12` (SNEXT): ours executes ONLY page-1 PCs
  `$5006`, `$50AD`, `$50B0`, `$50B4`, `$50B7` — **80× each** (the loop). `$5006` is the
  un-wired entry; `$50AD-$50B7` is the *tail of the `$50A9` stub* (its `ld de,$F1AA / ld
  ix,$F1AA / ld hl,$F359 / ret`). So ours' SNEXT returns the `$50A9` stub's contract, which
  the kernel reads as "another directory entry was found."
- `callwatch --machine ours --in-func 0x11` (SFIRST): ours executes `$4FB8` then the same
  `$50AD-$50B7` stub tail — ONCE. `$4FB8` is likewise un-wired `$00` padding.
- `callwatch --machine stock --in-func 0x11 / 0x12`: stock executes a **large real routine**
  — **108 distinct page-1 PCs for SFIRST, 101 for SNEXT**, spanning `$5FE2-$603A`,
  `$6076-$608E`, `$7495-$76C5`, `$782B-$786E`, etc. (FAT/dir-sector reads + name match +
  search-position tracking), each visited a BOUNDED 1-3×. This is the machinery ours lacks.
- ROM byte check (our OWN rom, clean-room-safe): `build/disk.rom` at `$4FB8` = `00 00 00
  00 00 00 00 00`, at `$5006` = `00 00 00 00 00 00 00 00` — confirmed NOP-padding, not code.
  (`$50A9` = `97 32 42 F2 11 AA F1 DD…` = our real stub: `sub a; ld ($F242),a; ld de,$F1AA;
  ld ix,…`.)
- **Screen arbiter** (`screen --machine both --keys '\rDIR\r' --keys-at 22 --settle 60`):
  STOCK renders the full listing (`… 41 files / 375808 bytes free / A>` at ROW23); OURS shows
  `A>DIR` at ROW09 and then a **blank screen** — hung in the search loop, nothing printed.

**⇒ `DIR` is functionally BROKEN on ours** and the root cause is pinned clean-room-safe:
two un-wired kernel dir-search entries (`$4FB8` SFIRST, `$5006` SNEXT) that NOP-slide into
the `$50A9` stub instead of doing (or delegating) the real directory walk.

## 3. Root cause + proposed fix SHAPE (the one live item: `$11`/`$12`, propose as M19)
### 3.1 Root cause (pinned, clean-room — no stock/kernel code decoded)
The relocated RAM kernel, processing BDOS SFIRST (`$11`) / SNEXT (`$12`), CALLs page-1
disk-ROM entries at **`$4FB8`** (SFIRST) and **`$5006`** (SNEXT). Both are `$00` NOP-padding
on ours (our active `$50xx` code ends at the `$50A9` stub's `ret` @ `$50B7`; the `$4xxx`/
`$50xx` gaps around them are our own fill). The CALL therefore NOP-slides forward into the
`$50A9` routine's tail at `$50AD`, whose `ret` hands back `A`/`DE`/`IX`/`HL` set for the
`$50A9` CONTINUATION contract — which the SNEXT caller misreads as "directory entry found."
So the search never terminates. **Same un-wired-`$50xx`-entry class as M13 (`$50E0`), M17
(`$50D5`), M18 (`$50C4`) — but the correct body is a full directory-search routine, not a
read-one-cell veneer.**

### 3.2 Why this is NOT a simple veneer (the key scoping fact)
Stock's SFIRST/SNEXT touches 100+ distinct page-1 addresses and reads FAT + directory
sectors, matches the FCB's (possibly wildcarded) 8.3 name, writes a 32-byte found-entry
image into the DTA, and maintains search-position state across the SFIRST→SNEXT→…→exhausted
sequence. The correct fix is to IMPLEMENT that directory-search behaviour behind the `$4FB8`
/`$5006` entries — a routine on the order of our existing `fat_find` / `fat_mount` machinery,
not three bytes. We already own most of the primitives: `disk/driver.asm` has `fat_mount`,
`fat_find` (root-dir 8.3 match used by `bdos_open`), and the DPB/FAT layer. The fix REUSES
those to build an SFIRST/SNEXT pair with persistent search state.

### 3.3 Proposed fix shape (for the M19 spec — sketch only, to finalise after sign-off)
Mirror the M13/M17 wiring pattern for the entry, but with a substantial body:
- **Entries.** `jp sfirst_body` at `$4FB8`, `jp snext_body` at `$5006` (consume existing
  `$00` pad → net-zero, no address shift — verify each is 3 free bytes exactly, as with
  `$50D5`/`$50E0`). Pin each entry's black-box register contract FIRST (a `callseq --log
  0x4FB8` / `--log 0x5006` on BOTH machines: entry regs, return regs, `ret=` trampoline) —
  this is what M17/M18 did before writing the body, and it fixes the DTA pointer / FCB
  pointer / return-code convention the kernel expects.
- **Bodies (free tail).** `sfirst_body`: mount (if needed), start a root-dir scan from
  entry 0, find the first entry matching the search FCB's 8.3 pattern (with `?` wildcard per
  the published SFIRST contract), copy the 32-byte directory entry to the DTA, save the scan
  index in a new work cell (`BDOS_SRCHIDX` or similar), return the documented found/not-found
  code. `snext_body`: resume from the saved index, find the next match, same copy + return;
  when the root dir is exhausted, return the documented "no more entries" code (`A=$FF` /
  the code the black-box entry-contract pin shows stock returns) so the caller's loop ends.
  Reuse `fat_mount` + the root-dir iteration already in `fat_find`.
- **New work cell(s).** search-position index (and any mount/dir-sector cache the scan
  needs). These are our own design (like `BDOS_RECIDX`), documented in PROVENANCE.md.
- **Clean-room.** `$4FB8`/`$5006` are de-facto page-1 kernel ABI entries (same class as
  `$50D5`/`$50E0`); the register contract is pinned black-box (entry/exit regs, `ret`
  trampoline, DTA-write side effect observed via a one-sided `readwatch`/`capture` of the
  DTA region on ours after the call) — NEVER by decoding stock's routine. The 32-byte
  directory-entry image format + SFIRST/SNEXT semantics come from the published FCB /
  directory-entry contract (MSX2 TH §FCB, MSX-DOS function table), and the FAT/dir walk
  reuses our own `fat_*` layer.

**This is an M13-class *shape* but an OI-3-class *effort*** (a real new routine needing its
own reasoning + sign-off). Recommend it be its own milestone spec (**M19 — runtime
directory search**), NOT folded into a "read-cluster batch."

## 4. The functions that are NOT independently characterisable here
- **`$0F` FOPEN (runtime re-confirm):** exercised at boot n=2 (`C=0F A=24 B=00 DE=D62F
  HL=C284 ret=C24E`, ours==stock — a SETTLED fact) and again inside `DIR`/`TYPE`. Where it
  appears it is byte-identical. It is NOT independently broken. No action; already covered.
- **`$1A` SETDTA (runtime):** exercised in `DIR` (n=30, n=32), byte-identical at entry and
  in the aligned prefix (n≤33). No divergence attributable to SETDTA itself. No action.
- **`$14` RDSEQ / `$10` FCLOSE (runtime):** the only COMMAND.COM builtin that would issue
  these is `TYPE <file>` (open→seq-read loop→close). But (a) `TYPE` output can't be cleanly
  isolated from FOPEN+SETDTA+FCLOSE in one call stream, and (b) it is UNCLEAR whether `DIR`
  being broken (§3) blocks reaching a clean `TYPE` test at all. These are better tested by an
  exerciser `.COM` that calls each in isolation with a known FCB and diffs the DTA + return
  code. **Blocked on the exerciser.** (Note: our `bdos_entry` loader path DOES prove the
  read+close LOGIC works for the loader's own use — see the `disk_probe_bdos.py` oracle in
  driver.asm comments — but that is a DIFFERENT surface, §1, and does not verify the runtime
  kernel path.)
- **`$23` FSIZE, `$26` WRBLK(read), `$27` RDBLK (runtime):** no COMMAND.COM builtin issues
  these; `$27` is used only by the MSXDOS.SYS *loader* (a boot-internal path we already
  pass). Verifying/implementing the RUNTIME path for these **requires the exerciser `.COM`.**

## 5. The trigger-infrastructure finding (the honest scoping call)
- **Good news:** the "one keystroke burst" harness limit is NOT the wall the prior sweep
  feared. `--keys '\rDIR\r'` reaches the dir-search cluster today; the same trick
  (`\rTYPE X\r`, `\rA:\r`, etc.) can drive other builtins. **No new harness infra needed to
  reach anything COMMAND.COM has a builtin for.**
- **The real wall:** COMMAND.COM's builtins only exercise a SUBSET of BDOS
  (`$02/$09/$0A/$0F/$11/$12/$1A/$2A/$2B/$0E/$19`, plus `$14/$10` via `TYPE`). Functions with
  no builtin (`$23`, `$26`, `$27` at runtime, and the whole console tier `$01/$06/$07/$08/
  $0B/$0C` from the prior sweep) are **unreachable without a purpose-built exerciser `.COM`**
  that calls each BDOS function directly and lets `disk_probe_diff.py` diff the result. This
  confirms the prior sweep's suspicion and **inverts the ranked order**: the
  [[bdos-exerciser-com-test]] `.COM` is a PREREQUISITE for systematic per-function coverage,
  not a later convenience.
- Building the exerciser is itself a clean-room-safe, in-house `.COM` (our own asm calling
  the published BDOS ABI); it needs to be added to a data test disk (NOT the committed
  test.dsk — a fresh tmp/asset disk, per [[test-disk-mutation-gotcha]]). That is its own
  small tooling task and should be specced separately.

## 6. Acceptance criteria
### 6.1 For the M19 dir-search fix (when it is specced + built)
1. **Screen arbiter (primary):** `screen --machine both --keys '\rDIR\r' --keys-at 22
   --settle 60` → OURS renders the SAME directory listing as stock (41 files, `375808 bytes
   free`, `A>` ready) — no hang, no blank screen.
2. **Call-sequence parity:** `callseq --at 0x0100 --log 0x0005 --maxhits 90 --keys '\rDIR\r'
   --keys-at 22` → ours matches stock past n=33 (SNEXT returns "exhausted" so the search loop
   terminates and CONOUT of the listing begins at n=34), aligned to the return to `A>`.
3. **Entry contract pinned:** `callseq --log 0x4FB8` and `--log 0x5006` on both machines →
   ours hits each entry the same number of times as stock with the matching return-register
   contract (found vs exhausted code).
4. **Tier-1 green + size:** `make unit-test` 19/19; DSKIO/BLOAD/FILES == CF-3300; `disk.rom`
   == 16384 B; no canonical-address shift (entries consume existing `$00` pad).
5. **No regression:** the 27/27 boot BDOS parity (`--keys '\r'`) still holds; no int-storm
   (dosboot_triage OK); M13/M15/M17/M18/OI-3 repros still pass.

### 6.2 For the exerciser-`.COM` track (prerequisite for `$14/$10/$23/$26/$27` + console tier)
1. A minimal clean-room `.COM` that calls each target BDOS function with a known FCB/args and
   reports the result (to screen or a known buffer the probe reads).
2. On a fresh asset disk (not committed test.dsk); `disk_probe_diff.py` diffs each function's
   result/DTA/return-code ours vs stock.
3. Then, per function, either "byte-identical → settled" or a per-function fix spec.

## 7. Clean-room status
- SFIRST/SNEXT semantics, the FCB search-name/wildcard rules, and the 32-byte directory-entry
  image format: published MSX-DOS 1 BDOS function table + FCB/directory spec (map.grauw.nl,
  MSX2 TH §BDOS/§FCB, MSX Datapack). Cited, not decoded.
- `$4FB8`/`$5006` as the kernel's SFIRST/SNEXT page-1 CALL targets: derived from BLACK-BOX
  observation only — `callwatch --in-func` entry-PC gating + our own ROM's NOP-padding check.
  Stock's routine internals were **NOT** decoded; only its *entry PCs* (addresses, not bytes)
  and visit counts were observed, plus the ours-side stub slide. No stock CODE bytes read.
- The proposed body reuses our OWN `fat_mount`/`fat_find`/DPB layer + our own new work cells.
- `build/disk.rom` byte reads (`$4FB8`/`$5006`/`$50A9`) are reads of OUR OWN rom — allowed.
- No stock ROM / loaded-kernel CODE bytes were read to reach any conclusion in this spec.

## 8. Status / recommendation (for sign-off)
**Spec (characterisation + scoping) complete; STOP for sign-off.** Recommendation:
1. **Do NOT proceed with "the FCB-read cluster" as a batch — it is not one.** The briefed
   grouping dissolves under characterisation into (a) one big real bug and (b) a set blocked
   on new tooling.
2. **Promote `$11`/`$12` dir-search to its own milestone (M19)** and write a dedicated
   implementation spec for it (it is a substantial routine, OI-3-class effort, needs its own
   reasoning + sign-off — NOT self-approved-by-veneer-precedent). It is the highest-value
   item: `DIR` is visibly broken on ours today, it is reachable now, and the root cause is
   pinned clean-room.
3. **Build the BDOS-exerciser `.COM` BEFORE** attempting `$14/$10/$23/$26/$27` (and the prior
   console tier). The ranked order is inverted: the exerciser is a prerequisite for systematic
   per-function coverage, not a later nicety. Spec it separately as a small tooling task.
4. `$0F`/`$1A` runtime are already byte-identical where exercised — no action.
