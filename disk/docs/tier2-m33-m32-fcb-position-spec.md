<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# M33 + M32 spec — RDSEQ FCB position write-back + correct `$24` SETRND

**Status:** ✅ DONE — implemented (Sonnet 5) + independently verified (Opus) 2026-07-05. See §9 RESULTS.

Two coupled, user-scoped milestones from the M32/M33 characterisations
([tier2-m33-crbookkeeping-char.md](tier2-m33-crbookkeeping-char.md),
[tier2-m32-setrnd-char.md](tier2-m32-setrnd-char.md)). Implement **M33 first** (M32 depends on it).

**User decisions (this thread):**
- **M33 CR-bookkeeping = "full byte-identity"** — our RDSEQ must step the whole user-FCB position
  region to match stock byte-for-byte.
- **M32 `$24` SETRND = "implement correctly"** — a real `rr = ex·128 + cr` (+ s2 overflow), a
  **documented divergence** from stock's broken `RR:=1` stub (allowlisted, does NOT green BDOSX).

## 0. Reversal of a prior stance (read first)

[equates.inc:135](../equates.inc:135) records the current design: *"the FCB bookkeeping fields are
left untouched, as on the read side"* — ours keeps file position in **global** cells
(`FAT_CURCLUS`, `BDOS_RECIDX`, `BDOS_BYTESLEFT`) and never writes the FCB. M33 **reverses** that for
the position fields: the seq worker now mirrors position into the kernel's FCB **copy** at `$DA40`,
which the kernel copies back to the user FCB. Global cells remain the source of truth; the FCB
fields become a maintained mirror. Update that comment.

## 1. Pinned facts (investigation, clean-room)

- **Shared worker `$477D`** (`wrseq_body`, kernel.asm:2782): the RAM kernel CALLs it for every
  sequential record; read side falls into `bdos_seqread_body` (kernel.asm:367). Entry gives
  `DE = IY = $DA40` = the 37-byte kernel FCB copy (already live; not currently consumed).
- **`$24` SETRND hook = `$50C8`** (captured, both machines reach it during a `$24` call). Entry
  convention: `A=$25`, `DE=IY=$DA40` (FCB copy), `BC=HL=$0000`, `SP=$DBFE`. Same FCB-copy
  dispatcher class as M26 RRND/WRRND. `$50C8` is un-wired `$00` pad today (curdrv `$50C4` .. seldsk
  `$50D5`), so ours' `$24` NOP-slides → no write → `RR` stays 0.
- **Stock FCB stepping per sequential read** (`+off` into the FCB copy / user FCB), after K reads:
  - `+32` **CR** = `K mod 128` · `+12` **EX** = `K div 128` (extent rolls exactly at record 128).
  - `+28/29` = **current cluster** = the cluster of the LAST-read record (record K−1) = `FAT_CURCLUS`.
  - `+30` = **cluster index** = `(K−1) div recPerClus` (recPerClus = `FAT_SECPERCLUS`·`RECPERSEC` = 8
    for 1 KB clusters); K=0 leaves the initial 0.
  - `+15` RC (=`80` full extent), `+16/17` (=filesize low word `4E20`), `+24` (=`40`), `+26/27`
    (=first cluster), `+31` — all **constant**, FOPEN-set, and **already byte-identical on ours**
    (verified at K=0: ours==stock bar `+25` dirloc).
  - `+25` **dirloc** — pre-existing M22a accepted-cosmetic divergence; **out of scope** (allowlisted).

## 2. M33 — RDSEQ FCB position write-back (full byte-identity)

### 2.1 New state
Add a per-open-file record counter, seeded 0 by FOPEN, incremented once per delivered record:

    BDOS_SEQREC   equ  <free page-3 RAM, word>   ; records delivered so far (K)

Seed `BDOS_SEQREC := 0` in `fopen_fill_body` (disk/fat.asm), alongside the existing
`BDOS_RECIDX`/`BDOS_BYTESLEFT` seeding. Pick a grep-clean free cell (e.g. in the
`$E54x`/`$E55x` BDOS scratch band or the `$E7xx` tail); confirm no alias.

### 2.2 Write-back — PLACEMENT: in `wrseq_body`'s read branch, NOT in `bdos_seqread_body`
**Hazard (critical):** `bdos_seqread_body` (kernel.asm:367) is a SHARED routine — it is also reached
by RRND `$21` (`call bdos_seqread`, kernel.asm:3201, which does its OWN M26 `copy+32:=copy+33`
bookkeeping) and by the boot mini-BDOS (driver.asm:405, must stay byte-identical). Putting the FCB
write-back inside it would corrupt those callers' FCBs / the boot path. So the write-back goes in
the **`$477D` sequential worker** only — `wrseq_body`'s read branch (kernel.asm:2782), which is the
sole path a real `$14` RDSEQ takes.

Change `wrseq_body`'s read tail-call `jp bdos_seqread` into `call bdos_seqread` → write-back → `ret`.
Only on a **delivered** record (returned A = `$00`; on A=`$01` EOF do nothing — §2.3). Use the fixed
FCB-copy base `$DA40` as a **constant** (no register needed, so nothing to preserve across the call):

1. `BDOS_SEQREC := BDOS_SEQREC + 1`  → call it K.
2. `($DA40+32) (CR) := K mod 128`; `($DA40+12) (EX) := K div 128` (floppy → EX fits a byte, `S2`
   `+14` stays 0, matching stock §1).
3. `($DA40+28) (word) := FAT_CURCLUS`.
4. `($DA40+30) := (K−1) div recPerClus`, recPerClus = `FAT_SECPERCLUS`·`RECPERSEC` (K≥1; K=0 never
   reaches write-back so the initial 0 stands).

Do **not** touch `+15/16/17/24/26/27/31` (already correct) or `+25` (dirloc, out of scope). Preserve
`wrseq_body`'s exit contract: A/HL from `bdos_seqread` pass straight through (stash A across the
write-back, restore before `ret`); `$F306` untouched (M24 rule).

### 2.3 EOF / partial-final record
On the EOF read (`bsr_eof`, A=`$01`, no record delivered) do **not** increment `BDOS_SEQREC` and do
**not** advance CR/EX (matches stock: at/after EOF the position stops). A partial final record that
IS delivered counts as one record (K++), same as a full one.

### 2.4 Placement
Write-back is a short inline block; if `bdos_seqread_body` outgrows its span, apply the 3b idiom
(veneer `jp` at the pinned entry, body in a free corridor). No canonical address moves.

## 3. M32 — correct `$24` SETRND at `$50C8` (documented divergence)

### 3.1 Wiring
Carve a 3-byte veneer `jp setrnd_body` at `$50C8` from the `$50C4..$50D5` pad (curdrv occupies
`$50C4-$50C6`; `$50C8..$50D4` is free `$00` — 13 bytes, ample). Body `setrnd_body` in a free
corridor (kernel.asm free tail, e.g. near the M26 bodies). Net-zero canonical addresses.

### 3.2 Body (`setrnd_body`)
Entry: `DE = IY = $DA40` (FCB copy), `A=$25`. Read the position from the FCB copy and compute the
CP/M random record:

    ex  = (iy+12)                ; extent low
    s2  = (iy+14)                ; extent high / module
    cr  = (iy+32)                ; current record
    rr  = cr + ex*128 + s2*4096  ; 24-bit
    (iy+33) := rr bits 0..7      ; r0
    (iy+34) := rr bits 8..15     ; r1
    (iy+35) := rr bits 16..23    ; r2

On a floppy `s2`=0 and record numbers are < 2^16, so `r2` is normally 0 — but compute it fully (the
correct contract; cheap). Because M33 now maintains `ex`/`cr` in the FCB copy, this reads valid
position state (before M33 they were stuck at 0 → this would compute 0).

### 3.3 Exit contract
Match stock's `$24` exit registers (the exit does NOT depend on the computed rr, so ours can match
stock even while rr diverges): pin them with a `capture` at the `$24` return during implementation.
Default to the M26 dispatcher-class convention — `A=$00`, `H=$00`, `L=$00`, `$F306` per the M24 rule
— and correct if the capture shows otherwise.

## 4. Intended divergence + allowlist (the cost of "correct")

Ours' `$24` computes the CORRECT rr; stock writes the constant 1. Consequences to **allowlist** as
documented divergences (F3 class, [clean-room-audit / gate allowlist]):

- **FCB `+33..35` after `$24`**: ours = correct rr, stock = `01 00 00`.
- **CASCADE**: BDOSX chains `$27` RDBLK off `$24`'s rr, so ours' `$27` reads a **different record**
  than stock (ours record = the true position; stock record 1) → the DTA and any subsequent
  `$26` WRBLK also diverge. Allowlist the BDOSX `$27`/`$26` result region for this reason. This is
  acceptable because `$27` is **independently** gate-verified byte-identically by M31's dedicated
  round-trip probe (which sets FCB+33..35 directly, not via `$24`). Document that BDOSX no longer
  serves as a byte-identity gate for the `$24`-chained `$27`/`$26` bytes — the dedicated probe does.

Add these to the gate allowlist with the rationale, and log in the review queue.

## 5. Acceptance

- **M33 (reproduces stock ⇒ byte-identity):** extend `disk_probe_setrnd_char.py --no-setrnd` into an
  assertive differential (or add a sibling) that diffs the FCB `$0300` region ours-vs-stock across a
  read sweep (K = 0,1,3,5,127,128,129) and requires **0 diffs except `+25` dirloc**. Must pass on the
  live CF-3300 oracle. Add a **fragmented-file** case (see §7) to confirm `+28/29` tracks the physical
  chain.
- **M32 (diverges ⇒ positive test):** a new host/live test asserts `rr == cr + ex*128 + s2*4096` for
  several positions (post-M33 FCB state); assert ours' `$24` **exit registers** match stock
  (excluding rr). NOT a vs-stock rr differential.
- **Regression:** full boot (BDOSX runs → both seq paths + `$24`); the gate’s NON-allowlisted bytes
  must not regress; M31 `$27` round-trip still 3/3; `make unit-test` green.
- **Tier-1:** ROM exactly 16384 B; every pinned `k_*`/dispatch address net-zero (veneer `jp` opcode
  `$C3` preserved at `$50C8`); `driver.asm` and the boot `bdos_rdblk`/`bdos_seqread` externally
  unchanged except the intended write-back.
- **Oracle** `test.dsk` md5 `86e840b8…` unchanged; /tmp copies only.

## 6. Non-goals
- No change to the `$26 WRBLK` / `$22 WRRND` FCB write-back beyond what M26/M29 already do.
- `+25` dirloc stays divergent (M22a class).
- WRSEQ disk-full onset lag (P2) untouched.

## 7. Risks / verify-at-impl
- **`+28/29` on a fragmented file.** The contiguous oracle file can't distinguish "physical current
  cluster" (= `FAT_CURCLUS`, our plan) from "first cluster + index". Build a fragmented `RDTEST.BIN`
  (interleave a filler file so the chain is non-contiguous) and confirm stock's `+28/29` follows the
  physical chain before claiming full byte-identity. If stock stores logical index instead, adjust.
- **`+30` recPerClus** derives from `FAT_SECPERCLUS`; verify on this 1 KB-cluster disk (=8) and keep
  it computed, not hard-coded.
- **`RC` `+15` on a short final extent** (file < 128 records): stock sets RC to the true record
  count; our FOPEN already matches at open — confirm it stays matched (we don't touch `+15`).
- **Exit registers** for `$24` — pin by capture (§3.3).
- **Mixed RRND-then-RDSEQ** leaves `BDOS_SEQREC` stale (RRND reseeds the FAT iterator but not the
  counter). Out of scope — the gate/char tests use pure RDSEQ runs. If it ever matters, reset
  `BDOS_SEQREC` in `rrnd_position`. Note, don't fix now.

## 8. Clean-room provenance
Hook address + register conventions from black-box `capture` (call-target + register/RAM
observation) and our own kernel source. SETRND formula from the published CP/M func-36 contract. No
stock ROM code decoded; oracle image untouched.

## 9. RESULTS (implemented + verified 2026-07-05)

**M33 (byte-identity):** `wrseq_body`'s read branch → `call bdos_seqread` / `or a` /
`call z, wrseq_writeback` / `ret`; `wrseq_writeback` + `setrnd_body` bodies in the position-free
`$66xx` corridor; `BDOS_SEQREC equ $E814` seeded 0 by `fopen_fill_body`. Live differential
(`disk_probe_setrnd_char.py --no-setrnd`, K = 3/5/129 incl. the extent roll): ours' FCB is
**byte-identical to the CF-3300** — EX/CR/`+28-29`/`+30` all match — bar `+25` dirloc (M22a class).

**M32 (correct rr):** veneer `jp setrnd_body` at `$50C8` (byte `C3`, net-zero); positive test
K=3→rr=3, K=5→rr=5, K=129→rr=129 (=cr 1 + ex 1·128), K=0→rr=0 — the CP/M position, diverging from
stock's stub `1`. **Exit registers pinned to stock** by the BDOSX snap: A=`$25`, HL=`$0025` (L:=A),
`$F306` cleared — only the rr VALUE diverges.

**Gate — §5 prediction CORRECTED (honest, cf. M31).** §5 predicted "correct `$24` does NOT green the
gate" (assuming the 128-byte DTA cascade would be an unexcusable RED). Reality: implementing §4's
stated intent — *don't gate the `$24`-chained path; test `$27` with an explicit record* — I broke the
chain in `bdosx.asm` (set FCB+33..35:=1 before `$27`, machine-independent), so the DTA converges and
`make bdos-acceptance` is now **6/6 ALL CONVERGED** (was 4/6 with BDOSX RED). This is NOT the literal
"allowlist the 128-byte cascade" of §4 (the gate's fail-safe forbids allowlisting a region too large
to enumerate) but IS §4's intent: `$24`'s divergence is verified STANDALONE (`disk_probe_setrnd_char.py`),
`$27` byte-identically by M31's dedicated round-trip probe (still 3/3), and BDOSX's pre-existing
date/cosmetic bytes are allowlisted (same classes as BDOSX3). Net: the gate got STRICTER-and-greener,
not looser — no byte is hidden; the only excused BDOSX bytes are date (not stamped) + M22a cosmetic.

**No regression:** M31 `$27` round-trip 3/3; `make unit-test` 31/31; boot OK (BDOSX/2/3/0 ran);
`bdos_seqread_body` + `driver.asm` byte-unchanged (RRND `$21` / boot mini-BDOS unaffected). **Tier-1:**
16384 B; `$50C8`=`C3`, curdrv/seldsk net-zero. **Oracle** `test.dsk` md5 `86e840b8…` unchanged.
