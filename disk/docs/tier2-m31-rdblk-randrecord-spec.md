# M31 — `$27` RDBLK un-simplification (honor random-record + count)

Status: **✅ DONE — implemented + verified 2026-07-05** (was: DRAFT → signed off → landed)
Scope decision (user, 2026-07-05): **`$27` only, as M31.** The gate-green work is a
3-part job (`$27` un-simplification + `$24` SETRND + FCB-copy CR bookkeeping); the
user scoped M31 to `$27` alone. `$24`/CR are **out of scope** here and stay tracked.

Clean-room: a completeness rewrite of OUR OWN `$27` page-1 hook `k_47B2`
([kernel.asm:1413](../kernel.asm)) to the published `_RDBLK` (27H) contract. No stock
code read; contract pinned by the public map.grauw.nl `_RDBLK` doc + a black-box
behavioural characterisation (the M31 investigation, 2026-07-05, §1).

---

## 0. What "un-simplification" means

Today `k_47B2` has a **stream-from-0** simplification: it ignores the FCB
random-record field (`FCB+33..35`), always streams the whole file from record 0 to
EOF, treats the requested count (`HL`) as "read to EOF", and uses a fixed 128-byte
record via `bdos_seqread`. M31 makes it a faithful Random Block Read: **position to
record RR, transfer up to HL records of the FCB's record size, zero-pad a final
partial record, and report the true count** — while leaving the pinned boot/TPA-loader
return contract intact.

## 1. Investigation results this spec rests on (2026-07-05, read-only, black-box)

**Q1 — routing (settled).** A running program's `$27` enters **`k_47B2`** (verified
aligned on ours + stock: SP=$DBFE, DE=IY=$DA40, HL=$0001, ret=$D88A). Our mini-BDOS
`bdos_rdblk` ([driver.asm:593](../driver.asm)) is **never** hit by a running program —
it serves only the pre-kernel boot `MSXDOS.SYS` load. ⇒ **M31 touches `k_47B2` only;
`bdos_rdblk`/`rdb_recloop_body` stay byte-identical.**

**Q2 — boot callers are RR=0 (safe).** Both loaders that reach `k_47B2` pass
**FCB+33..35 = 0** (verified RAM read at entry): boot COMMAND.COM self-load
(FCB=$DC5B, RS=1, HL=$D500) and runtime TPA load (FCB=$DA40, RS=1, HL=$C200). So
adding RR-positioning is a **provable no-op** for boot (skip = RR×RS = 0). **Note the
loaders use record size 1** — a faithful hook MUST honor RS≠128 (§3.2); at RS=1 the
loader contract HL=BC=filesize, A=1 falls out automatically (records = bytes).

**Q3 — stock user-level `$27` contract (verified; matches grauw `_RDBLK`).**

| case | RR | cnt | file | **A** | **HL** | RR after | DTA result |
|------|---:|----:|-----:|:-----:|:------:|:--------:|------------|
| (a) mid-file        | 1  | 1 | 384B | **0** | **1** | 2 | record 1 only |
| (b) EOF mid-transfer| 1  | 4 | 384B | **1** | **2** | 3 | records 1,2 |
| (b′) partial tail   | 1  | 4 | 300B | **1** | **2** | 3 | rec 1, rec 2 **zero-padded to RS** |
| (c) at EOF          | 3  | 1 | 384B | **1** | **0** | 3 (unchanged) | untouched |
| (c′) past EOF       | 10 | 1 | 384B | **1** | **0** | 10 (unchanged)| untouched |

- `A = 0` iff all `HL`-requested records delivered without EOF; `A = 1` if EOF first.
- `HL` = records actually delivered (a partial final record **counts** and is
  **zero-padded** to RS — case b′).
- `FCB+33..35` (RR) is advanced by `HL` ("adjusted to the first record not read");
  since `HL = 0` when positioned at/past EOF, RR is left unchanged there (c/c′) — the
  uniform rule `RR := RR + HL` reproduces all five rows.
- At the **user API** `BC = $0000` (BC is not a user result register); the `BC = HL`
  clause is the **`$47B2`-boundary** contract (MSXDOS.SYS's `$024A` sign branch reads
  BC) — the shared kernel wrapper passes A+HL through to the user and clobbers BC.

**Honesty / scope caveat (important).** With `$24` SETRND still a no-op on our side
(the deferred piece), BDOSX's own RR stays **0** on our machine, so **M31 changes
nothing the BDOSX acceptance gate observes** — the gate stays RED, byte-for-byte
unchanged (that is the *expected, correct* outcome and doubles as a no-regression
check, §6.5). M31's positive proof therefore sets `FCB+33` **directly** in a probe
(bypassing our broken SETRND), exactly as the investigation exerciser did. M31 is a
**contract-completeness** milestone (faithful `$27` for any future caller + the first
brick of the eventual gate-green), not a user-visible behaviour change on-target.

## 2. Callers & the two return contracts `k_47B2` must serve

`k_47B2` is reached by three caller shapes (all via the kernel's `$D887` `$27`
dispatch); the **same body** must satisfy every one by *contract*, never by caller
identity (the stock third caller — the in-ROM MSXDOS.SYS load, ret=$5700 — has no
ours-equivalent but is covered automatically):

1. **Boot COMMAND.COM self-load** — FCB=$DC5B, RR=0, RS=1, HL huge. Needs
   HL=BC=filesize, A=1, IX=DRVA_DPB, IY=entry-DE, `$F306`=0. Falls out of the general
   contract at RR=0/RS=1/huge-count (records = bytes = filesize; EOF before huge count
   ⇒ A=1).
2. **Runtime TPA load** — FCB=$DA40, RR=0, RS=1, HL huge. Same as (1).
3. **User-level `$27`** (e.g. BDOSX) — arbitrary RR/RS/HL. Needs the §1-Q3 contract.

⇒ There is ONE unified body (§3); the loader returns are the general contract
instantiated at RR=0/RS=1/huge-HL. **No caller-type branching.**

## 3. Design — rewrite `k_47B2` to a faithful RDBLK

Reuse the existing byte-granular machinery (`rdblk_getbyte`, `RDBLK_*` cells,
`fat_open`, `fat_read_file_sector`) — the same engine `bdos_rdblk` uses — but give
`k_47B2` its **own** record loop so `bdos_rdblk`/`rdb_recloop_body` (boot path) are
untouched.

### 3.1 New/used state
- Reuse `RDBLK_REQ`/`RDBLK_RECSIZE`/`RDBLK_DONE`/`RDBLK_CNT`/`RDBLK_BUFPOS`/`RDBLK_DST`
  (`$E76C-$E777`, [init.asm:172](../init.asm)) + `BDOS_BYTESLEFT` (`$E542`) +
  `BDOS_DTA` (`$E4C0`).
- One new cell for the entry RR (needed for the `RR := RR + HL` write-back). A word
  suffices for realistic RR, but `FCB+33..35` is a 24-bit field: park **`RDBLK_RRSTART`
  `equ $E7FD`** (3 bytes, the last of the `$E7E8-$E7FF` free tail; grep-clean — the
  gap currently ends at `FAT_ALLOCHINT`=$E7FB word ⇒ $E7FD-$E7FF free). Document it as
  an RDBLK cell with per-call lifetime.

### 3.2 Body (replaces the `push de … ld a,1 / ret` span at kernel.asm:1413-1453)
1. **Save the FCB pointer** (entry DE) — needed for RR write-back AND the IY return.
2. **Record size** ← `FCB+14..15` word; `0 → 128` default (same normalisation as
   `bdos_rdblk` fat.asm rdb path). Store `RDBLK_RECSIZE`.
3. **Requested count** ← entry HL → `RDBLK_REQ`.
4. **RR start** ← `FCB+33..35` (24-bit) → `RDBLK_RRSTART`.
5. **DTA** ← `(DOS_DTAPTR)` (M19: kernel SETDTA writes only `DOS_DTAPTR`; do NOT trust
   `BDOS_DTA`) → `RDBLK_DST` and `BDOS_DTA`.
6. **Open + size**: `call fat_open`; `BDOS_BYTESLEFT ← FAT_FILESIZE` (4-byte);
   `RDBLK_BUFPOS ← 512` (force first-byte refill); `RDBLK_DONE ← 0`.
7. **Position to record RR** — skip RR whole records by discarding RS bytes each,
   bounded by EOF (no multiply, no overflow): repeat RR times { repeat RS times {
   if `BDOS_BYTESLEFT == 0` → break-all (positioned at/past EOF); else `rdblk_getbyte`
   (discard A; it decrements `BDOS_BYTESLEFT` and refills) } }. (Guard `rdblk_getbyte`
   Cy=1 chain-end the same way — treat as EOF.) This positions at byte RR×RS, or at
   EOF if RR×RS ≥ filesize. *Sector-seek is a deferred optimisation — not needed;
   `$27` is not in a hot loop and files are small.*
8. **Transfer loop** (dedicated; zero-pad variant of `rdb_recloop_body`):
   - If `RDBLK_DONE == RDBLK_REQ` → **complete**, `A=0`, go to return (8a).
   - Start a record: `RDBLK_CNT ← RDBLK_RECSIZE`; track whether any byte was copied.
   - Byte loop: while `RDBLK_CNT != 0`:
     - if `BDOS_BYTESLEFT == 0`:
       - if this record is **partial** (at least one byte already copied this record)
         → **zero-pad**: write `$00` to `(RDBLK_DST)` for the remaining `RDBLK_CNT`
         bytes (advancing RDBLK_DST), `RDBLK_DONE++`, then **EOF** (`A=1`, → return).
       - else (clean record boundary, no bytes copied) → **EOF** (`A=1`, → return)
         WITHOUT counting this record.
     - else `rdblk_getbyte` → store A at `(RDBLK_DST)`, `inc RDBLK_DST`,
       `dec RDBLK_CNT`, mark "byte copied".
   - Record complete (RDBLK_CNT hit 0 with bytes): `RDBLK_DONE++`; loop to next record.
9. **Return (8a — one exit, both A values fall through here):**
   - `HL ← RDBLK_DONE`; `RR := RDBLK_RRSTART + HL`; write the 24-bit result back to the
     **FCB** `+33..35` (carry into the high byte; HL is a 16-bit add into the 24-bit
     field). *(At/past EOF HL=0 ⇒ RR unchanged, matching c/c′.)*
   - `BC ← HL` (the `$47B2`-boundary count, §1-Q3).
   - `IX ← DRVA_DPB`; `IY ← entry-DE`; `ld (\$F306),a`-clear (`xor a; ld ($F306),a`
     — M20 dispatcher-flag rule); restore `A` to the 0/1 EOF result.
   - `ret`.

**Boot instantiation check (paper):** RR=0 ⇒ skip nothing; RS=1 ⇒ each record = 1
byte; HL huge ⇒ transfer runs to EOF (BYTESLEFT→0 at a record boundary, no partial) ⇒
`RDBLK_DONE = filesize`, `A=1`; `HL=BC=filesize`; RR := 0+filesize written back
(harmless — stock also advances the copy; §6.1 boots with it live). IX/IY/`$F306` as
today. ✅ reproduces the pinned loader contract exactly.

### 3.3 Net-zero / size discipline
The rewrite GROWS `k_47B2`'s body (positioning + zero-pad + RR write-back). If it
overflows the span up to the next canonical anchor (`k_4919` at $4919), apply the
established **3b-relocation** (M24/M28/M29 pattern): keep a veneer at `$47B2`
(`jp <reloc>`) and move the body verbatim into the free kernel corridor
(`$60EC-$75A4` region used by prior relocations), so every `k_*` canonical address
stays net-zero and `disk.rom` = 16384 B. Implementer picks the placement that yields
0 `k_*` moved.

## 4. Scope
- **In:** faithful `$27` in `k_47B2` — RR positioning, RS honoring, HL count bound,
  final-partial zero-pad, `RR := RR + HL` write-back, unified return contract. 1 new
  equate (`RDBLK_RRSTART`).
- **Out (tracked, not M31):** `$24` SETRND real `$50C8` (needs its OWN black-box
  characterisation first — stock leaves RR=1 *constant*, contradicting the DOS-2 doc);
  FCB-copy CR bookkeeping in the sequential worker. These two + M31 are what green
  BDOSX; M31 alone does not (§1 caveat). `bdos_rdblk` boot path — untouched.

## 5. Clean-room provenance
Our own hook + our own file layer, streaming into the caller's DTA. Contract from the
public map.grauw.nl `_RDBLK` doc + black-box behavioural characterisation (registers,
RAM, disk artifacts; PC-trace routing). COMMAND.COM is data we copy, never
disassembled. No stock ROM code bytes read.

## 6. Verification — RESULTS (all passed; 2026-07-05, Opus)
1. **COMMAND.COM boot regression — THE gate.** ✅ `make bdos-acceptance` boots real
   MSX-DOS-1 and runs the BDOSX exercisers, which requires BOTH `k_47B2` paths — the
   boot COMMAND.COM self-load AND the runtime typed-command TPA load. BDOSX ran to
   completion (produced its capture regions) on the M31 ROM with the RR write-back
   live ⇒ the rewritten body boots + loads programs correctly. BDOSX2/BDOSX3/BDOSX0
   all still PASS.
2. **RDBLK random-record round-trip (positive proof).** ✅ New committed probe
   `probes/disk/disk_probe_rdblk_roundtrip.py` + `rdblk_rt.asm` exerciser. All cases
   **BYTE-IDENTICAL ours == National_CF-3300** (DTA + return snapshot res_a/hl/bc/rr,
   576 B compared each): **(a)** mid-file RR=1 → record 1 delivered; **(bp)** RR=1
   cnt=4 on a 300 B file → EOF mid-transfer, final record zero-padded; **(c)** RR=3
   (at EOF) → 0 records, DTA untouched, RR unchanged. Sets `FCB+33..35` directly
   (bypassing our no-op SETRND) after a proven BDOSX-style preamble (FOPEN → RDSEQ×2 →
   SETRND → set RS → set RR). The capture window is the DTA + result cells, EXCLUDING
   the raw FCB — FCB+32 (CR bookkeeping, deferred) and FCB+25 (dirloc, M22a
   accepted-cosmetic) diverge for reasons OUTSIDE `$27`; the RR write-back is proven
   via res_rr (a post-call snapshot of FCB+33..35).
3. **Host unit test.** ✅ `tests/test_rdblk_randrecord.py`; `make unit-test` = 31/31.
   Covers a/b/b′/c/c′ + the boot instantiation, RS∈{1,64,128,0→128}, at/past-EOF,
   asserting return A/HL/BC + zero-pad + `FCB+33..35 := RR+HL` write-back.
4. **`bdos_rdblk` untouched.** ✅ `git diff disk/driver.asm` empty — the boot
   MSXDOS.SYS path (`bdos_rdblk`/`rdb_recloop_body`) is byte-identical.
5. **Acceptance gate — CONVERGED, not unchanged (my §6.5 prediction was WRONG; honest
   correction).** ⚠️→✅ I predicted "gate byte-for-byte unchanged (RR stays 0 ⇒ `$27`
   still reads from 0)". Reality: the gate **converged** — BDOSX `0x0300` dropped
   **11 → 8** unexcused bytes (`0369/036E/036F` now MATCH stock; `0321` 01→02, toward
   stock's 03). Cause: M31's **RR write-back** advances FCB+33..35 observably even when
   RR starts at 0, so BDOSX's post-`$27` FCB state partially matches stock now. This is
   the GOOD direction (more faithful `$27`); **no byte regressed**, `0x0400` unchanged
   (a separate non-`$27` residual), gate still 4/6 (BDOSX honestly RED pending the
   deferred `$24` SETRND + CR bookkeeping). The premise that greening BDOSX needs those
   two (not `$27` alone) stands (§1 caveat).
6. **Tier-1.** ✅ `disk.rom` = 16384 B. Net-zero canonical: all **28 `ds`-anchor
   addresses identical**, each still a `jp` opcode at its pinned address; the 25
   changed bytes are `jp`-**operand** shifts (the relocated bodies moved uniformly in
   the free corridor — the M24/M28/M29 relocation signature), not entry-point moves.
   `fac_found`… n/a; 3b-relocation used (veneer `jp k47b2_body` at `$47B2`, body in the
   `$75A5`-terminated free corridor). FDC window `$7F80-$7FBF` all-zero. `make
   unit-test` 31/31.

## 7. Implementation note
Signed-off spec → Sonnet 5 (model split), Opus verifies + commits. Est. one routine
rewrite in kernel.asm (+ 3b-relocation if needed) + 1 equate + 1 probe + 1 exerciser
+ 1 host test. Shared kernel, `fat_*`, `bdos_rdblk`, both FAT free sites: untouched.
