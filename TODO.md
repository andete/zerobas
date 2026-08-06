# zerobas roadmap

zerobas is a **clean-room reimplementation of MSX1 system software** — three
components (BASIC interpreter + cassette + disk) combined with an open BIOS (C-BIOS)
only at runtime — with **two co-equal goals**: the clean-room implementations
themselves, and the clean-provenance **documentation** of how these systems work
that the same discipline yields (see [`MISSION.md`](MISSION.md)). Scope today
is MSX1; the BASIC half targets **faithful, full MSX1 BASIC** (Phase 1 shipped the
*game-loader-stub* subset — enough to boot disk/tape game loaders — and the charter
has since been raised to full-language faithfulness, pursued in Phase 3), while tape
and disk are device-complete (read **and** write).

See [`README.md`](README.md) for the charter and the legal/provenance firewall,
[`PROVENANCE.md`](PROVENANCE.md) for the traceability rules every item below must
honour (allowed sources only; no disassembly), and
[`docs/dev-workflow.md`](docs/dev-workflow.md) for how to implement + validate one
item — do **one item per session** to keep context lean.

## Phases at a glance

| Phase | Scope | State |
|---|---|---|
| **1 — loader-stub BASIC + transports + standardization** | just enough MSX-BASIC to run `.BAS`/binary loader stubs; tape + disk read/write; standard DSKIO/`HPHYD` interfaces | **✅ closed** |
| **2 — full disk (Disk BASIC integration)** | the full file-channel verb surface (sequential + random-access + dir mgmt + `CALL FORMAT`), all oracle-validated | **✅ verb surface complete** — only the Tier-2 provider oracle (a distinct DOS-boot sub-track) + a few Phase-3-gated verbs remain |
| **3+ — full MSX1 BASIC** | floating point, full string engine, arrays, graphics, sound, … | **active charter** (raised from loader-stub) — landed: string engine, float pack, math pack, **arrays/DIM arc CONCLUDED** (through slice-4c string-scalar unification — the faithful unified variable area; no fixed variable pool remains) |

## Open — standing residuals (INDEX; this is the pickup list)

⚠️ **This section exists so a residual cannot be lost by being written up inside a
`- [x]` block.** Several of the items below were filed that way — accurate, dated,
and invisible to anyone scanning for `- [ ]`. Each line here is a **one-line
pointer**: the detail stays where the slice wrote it, at the cited line. Keep this
list short — close items, do not restate them.

Also the reason `MEMORY.md` no longer carries a copy of this list: the memory index
is loaded every session and must stay compact, so it points here instead of
duplicating (and drifting from) what is written below.

**Language / verb surface**

- [ ] `AUTO` / `RENUM` / `LLIST` / `DELETE` — **the STATEMENT half.** Tokens are
      byte-exact (D-KWGAP4, *“THE TOKEN HALF CLOSED BY”*, line 4312); nothing
      executes them. Detail: *“Editor / program management”*, line 1555.
- [ ] **No string `READ`.** Filed by D-DEFSTR — detail:
      *“ZEROBAS HAS NO STRING `READ`”*, line 4002.

**Own-design hazards carried out of closed slices**

- [ ] 🔴 **Two type-code namespaces share the value `1`** — the published `DEFTBL`
      string code and zerobas's own variable-chain string tag. D-DEFSTR fixed the
      three sites that crossed them (one was a live memory corruption) but the two
      namespaces still overlap on the numeric values, so the next site that feeds
      one into the other reintroduces the class. Collapse to ONE. Detail:
      *“`DEFTBL_STR` SHOULD BE `3`, NOT `1`”*, line 3913.

**Apparatus / gate limits (each is a stated limit, not a filed defect)**

- [ ] ⚠️ **`injector-check` is still a TEXT classifier.** A split literal passes.
      Already an open item — detail: line 4629.
- [ ] ⚠️ **An asm label named in a `tools/*.py` or `sub/` comment is immune to the
      dead-code sweep** — `check_dead_code.py`'s `external_names` scans those
      directories *including comments*, so writing a label's name in prose seeds it
      as reachable. Every slice that edits `tools/` prose must predict the seed
      counts and treat movement as a finding. Detail: lines 2228 and 2464.
- [ ] ⚠️ **Three probe page-0 entry addresses stay HARDCODED** —
      `basic_probe_subrom_boot.py` (`$0040`), `basic_probe_subrom_inttest.py`
      (`$0049`), `basic_probe_graphics_floor.py` (`$0058`). All three ARE scored;
      deriving them from `sub/equates.inc` needs its own falsification because they
      inject raw bytes into a bare machine deliberately. Detail: line 2423.
- [ ] ⚠️ **`build/disk.rom` pad-only damage is invisible ON PURPOSE** — 9543 of
      16384 bytes (58.2 %) are `$00` pad in 252 runs. Closing it needs a whole-image
      digest, which would pin the ROM against every legitimate `disk/*.asm` change.
      Re-open only with an argument that answers that. Detail: line 2418.
- [x] ✅ **`make audit-citations` was RED at HEAD and nothing ran it — CLOSED
      2026-08-06 by D-CITEJUDGE**,
      [`docs/spec-audit-citations-gate.md`](docs/spec-audit-citations-gate.md).
      Green; a step of `make basic-reloc` and of CI; denominator **49 → 116**
      files. Two of the four filed claims were wrong.
- [x] ✅ **`audit_citations.py` does not scan `docs/` — CLOSED 2026-08-06 by
      D-DOCJUDGE as a measured DECLINE + a different gate**,
      [`docs/spec-audit-citations-docs.md`](docs/spec-audit-citations-docs.md).
      Scanning `docs/` with the **vocabulary** rule was declined: the quarantined
      text contains **zero** forbidden tokens (its *remediation* is what carries
      one), so recall on every recorded breach is **0**, at a cost of **26**
      affirmative false positives over 278 files — 16 inside the three documents
      that define and record the policy. The filed *"only recorded breach"* was
      wrong (four events; ~50 sites on 2026-07-07), and **6 of those sat in
      `disk/*.asm`, files the tool already scanned** — so it was never a scope
      problem. Landed instead: **check 5**, the decoded-listing shape, repo-wide
      (692 files), which found one **live unremediated** site the 2026-07-07
      full-verify missed in a file it edited. §3.1 records what a future slice
      must produce to re-open the vocabulary widening.
- [ ] ⚠️ **Raw opcode-BYTE renderings are still uncovered** — `CD 54 54`,
      `DB A8 C9`, and the C-BIOS locator signatures in `probes/lib/latch_check.py`
      (`SIG`/`SIG2`). Check 5 keys on the *listing shape*; a hex byte run is a
      different shape and its false-positive surface is UNMEASURED (our own ROM's
      bytes appear throughout our own docs). Measure before proposing a rule —
      the same discipline that declined the vocabulary widening. Detail:
      `docs/spec-audit-citations-docs.md` §6.5.
- [ ] ⚠️ **The INLINE decoded form is measured UNDECIDABLE, and that is a standing
      hole, not a closed item** — `$0246: LD A,(…) / AND A / CALL Z,…`. Every
      threshold that catches any of it fires on the hand-reviewed prose that
      replaced it, and on 25–464 honest lines (four variants measured). The human
      full-verify is the only backstop; re-open only with a discriminator that
      scores 0 on the 156-line replacement corpus. Detail:
      `docs/spec-audit-citations-docs.md` §2.2.
- [ ] ⚠️ **Both check-5 allowlist entries need a HUMAN paper-trail confirm** —
      `probes/lib/{omsx_repl,latch_check}.py` render C-BIOS instructions.
      `allowed-sources.md` grades C-BIOS **B/Conditional** ("we don't lift its
      code/expression"), which is a judgement `docs/clean-room-audit.md` reserves
      for a human; the tool deliberately does not make it. Reasons are written in
      `tools/citations-listing-allow.txt`. Detail:
      `docs/spec-audit-citations-docs.md` §2.6.
- [ ] ⚠️ **The 7 `[REVIEW]` advisory headers are stable but unwatched** — the same
      7 files and names across 575 commits, triaged once
      (`docs/clean-room-audit.md`, 2026-07-04). Advisory is the right call, but a
      NEW one would land unnoticed in a list nobody diffs. The fix is a
      `deadcode-allow.txt`-style acknowledged list — an allowlist that must keep
      matching is a control; 7 justifications to write. Detail:
      `docs/spec-audit-citations-gate.md` §2.5.
- [ ] ⚠️ **`lof-acceptance` intermittent oracle drift — two sightings, nothing
      since.** Sighting 3 has not occurred across SIX consecutive slices
      (D-PINDATA, D-INJSINK, D-ROMJUDGE, D-DSKJUDGE, D-CITEJUDGE, D-DOCJUDGE). A third IS a finding to
      chase; capture the **whole** log (`> file 2>&1`), because sighting 1's row
      identity was lost to a `tail -6`. Detail: line 3519.

## Phase 1 — committed loader-stub target (✅ closed)

The charter (README) is deliberate: *just enough MSX-BASIC to run the `.BAS` /
binary loader stubs that boot disk and tape games — **not** full-language
compatibility.* That loader-stub target is **complete**:

1. **Loader-stub BASIC** — ✅ done.
2. **Tape transport** (read + write) — ✅ done. `BLOAD"CAS:",R`/`CLOAD`/`LOAD"CAS:"`
   load and `CSAVE`/`SAVE"CAS:"`/`BSAVE"CAS:"` save on-device (tokenised-only SAVE;
   `,A`/ASCII save is a Phase-3 language item).
3. **Disk transport** (read + write) — ✅ done (`disk.rom`; see [`disk/TODO.md`](disk/TODO.md)).
4. **Disk interface standardization ("Phase 1.5")** — ✅ done. `zerobas-BASIC` reaches
   disk files through the **standard `$4010` DSKIO sector interface** (owning the
   FAT12/dir logic loader-side); `zerobas-disk` installs the standard **`HPHYD`→DSKIO**
   hook + a real `GETDPB`, so any standard disk ROM works under zerobas-BASIC **and** a
   real BIOS can drive zerobas-disk. Host + provider + the host-side and Tier-1 provider
   oracles all pass. *(Spike note: the drive-letter loader path is pure PHYDIO/DSKIO —
   the BASIC DEVICE/expansion mechanism is never called — so the basic-side FAT is the
   necessary price of the universal sector interface, not avoidable duplication. See
   [`disk/docs/expansion-protocol.md`](disk/docs/expansion-protocol.md).)*

The one open checkbox under Phase 1.5 — the **Tier-2** provider oracle (a real
DOS/Disk-BASIC *filesystem* host, the only organic `GETDPB` consumer) — is the seam
into the next phase and is carried into **Phase 2** below. Phase 1 is otherwise
closed; the per-item done-record follows further down.

## Status today — three components, two axes

zerobas is three separately-built artifacts, combined only at runtime: `basic/` →
`basic.rom` (cartridge, slot 0 page 1); `tape/` → the zerobas-tape IPS patch
(C-BIOS page 0 cassette signal layer); `disk/` → `disk.rom` (slot 3-1).

| | Device / transport layer | Interpreter statements (basic.rom) |
|---|---|---|
| **Tape** | ✅ read **and** write signal layer (MSX1/2/2+) | ✅ `BLOAD"CAS:",R`, `CLOAD`, `LOAD"CAS:"` load on-device; `CSAVE`, `SAVE"CAS:"`, `BSAVE"CAS:"` write on-device — full read+write parity (tokenised-only SAVE, `,A`/ASCII is Phase 3) |
| **Disk** | ✅ DSKIO + FAT12 + BDOS, read **and** write (differential vs CF-3300 & MSX-DOS 1) | ✅ `BLOAD`/`LOAD`/`RUN`/`SAVE`/`BSAVE` for `"A:"` † |

† `zerobas-BASIC` reaches the disk through zerobas-disk's **private** `bdos_entry`
(published at SYSTEM vector `$F37D`), **not** the standard `$4010` DSKIO sector
interface — so a *foreign* disk ROM does not work under it, and zerobas-disk is not
reachable by real BASIC/DOS. Phase 1.5 (below) closes this by driving standard
DSKIO loader-side and installing the standard `HPHYD` hook provider-side.

Language (Phase 1, done): byte-identical tokeniser (keywords, integer / `&H` /
`&O` constants, `= + - * / \ < >`, `MOD`/`AND`/`OR`/`XOR`/`NOT`), stored
numbered-line programs (`NEW`/`RUN`/edit), control flow (`GOTO`, `GOSUB`/`RETURN`,
`FOR`/`NEXT`, `IF`/`THEN`/`ELSE`, `ON … GOTO`/`GOSUB`, `END`/`STOP`, `CONT` +
Ctrl-STOP), `DATA`/`READ`/`RESTORE`, `POKE`/`PEEK`, `PRINT`, `CLEAR`,
`DEF USR`/`USR`, screen-setup verbs (`SCREEN`/`COLOR`/`CLS`/`WIDTH`/`KEY`),
`LIST`, the memory/I-O primitives (`VPOKE`/`VPEEK`, `OUT`/`INP`, `VARPTR`),
multi-character 16-bit integer vars, minimal string vars for `PRINT`, and the
storage statements above.

## Phase 1 record — committed work (all ✅ done)

The per-item done-record for the committed loader-stub target. Kept for the
provenance / divergence trail; nothing here is outstanding.

### Tape — read + write parity with disk
- [x] **`CLOAD` / `LOAD"CAS:"` on-device load** — DONE. The hang was **not** a tape
      framing bug (oracle traces show `TAPIN` frames the `$00` run and `$0000`
      end-link fine at all bauds); it was a **link-word register clobber** in
      [`basic/cload.asm`](basic/cload.asm) `ctp_line`: `TAPIN` returns `C=0` (C is
      its bit-counter), but the old code stashed link-low in `C` across the second
      `TAPIN`, so the link word read as `$XX00` and the body-length math hung the
      loader. Fix = push/pop link-low across the second read (+ a stack-balanced
      error shim); the same latent clobber in the disk `dpl_line` was fixed too.
      `tape/` is unchanged. Verified: `basic_probe_cload_ondevice.py` ALL PASS
      (on `C-BIOS_MSX1_EU_TAPE` + `--cart`), disk LOAD/RUN + the 5 basic regression
      probes ALL PASS.
- [x] **Tape SAVE statements** — DONE. `CSAVE`/`SAVE"CAS:"` (tokenised program) and
      `BSAVE"CAS:",start,end[,exec]` (binary) write to cassette through the
      zerobas-tape **write** signal layer (`TAPOON`/`TAPOUT`/`TAPOOF`) + the cassette
      file format (`$D3`/`$D0` ×10 header block + 6-char name + data block). The disk
      `do_save`/`do_bsave` ([`basic/save.asm`](basic/save.asm)) now device-dispatch
      `"CAS:"` (non-destructive `dev_cas` peek, like the load side) to the new tape
      write path; `CSAVE` got its own oracle-locked token (`$9A`). All loop state
      lives in RAM (`TSV_*`) across every `TAPOUT` (the cassette BIOS clobbers
      everything — same discipline as `disk_putword`). Validated three ways:
      format byte-identical to `build_cas` (cas_decode), the reference VG-8020
      `CLOAD`s our recorded `.cas`, and self round-trips `CSAVE`→`CLOAD` /
      `BSAVE"CAS:"`→`BLOAD"CAS:"` (`basic_probe_tape_save.py` ALL PASS). Divergences:
      tokenised-only `SAVE"CAS:"` (`,A` ASCII → `load_error`, Phase 3); 6-char name
      truncation; bare `CSAVE` writes a 6-space name. This completes tape parity.

### Phase 1.5 — disk interface standardization (standard DSKIO + own FAT)

**Why.** On real MSX the BASIC interpreter and the disk ROM are *not* tied
together — they interoperate through **standardized** interfaces (the slot-scan +
INIT, the `$4010` DSKIO sector-I/O entry table, the `H.*` hooks), so disk
interfaces are interchangeable (plug a floppy cartridge into any MSX; swap disk
ROMs between makers). zerobas copies the *placement* faithfully (cassette in the
BIOS, disk in a slot) but swapped the BASIC↔disk *protocol* for a **private** one:
`zerobas-BASIC`'s disk verbs call zerobas-disk's `bdos_entry` via SYSTEM `$F37D`.
So only the matched pair works — a real/foreign disk ROM does **not** drop in, and
zerobas-disk is not reachable by real BASIC/DOS.

**Approach (research-spike-confirmed, 2026-06-21).** Drive the **standard `$4010`
DSKIO** sector interface and own the FAT12/dir logic loader-side. A spike on the
real **National CF-3300** Disk BASIC proved (black-box) that the drive-letter
loader path is *pure PHYDIO/DSKIO* — `BLOAD"A:"`/`SAVE"A:"` resolve the filename
internally (BPB/FAT/dir) and move bytes via `HPHYD ($FFA7)`→`DSKIO ($4010)`; the
BASIC **DEVICE/expansion mechanism is never called** for drive letters. There is
**no standard "open file by name" entry** to delegate to — a disk ROM's only
interchangeable interface is *sectors*; its filename logic is locked inside its
Disk BASIC. So the basic-side FAT is the **necessary price** of the universal
sector interface, **not** avoidable duplication. (True delegation — hosting the
disk ROM's Disk BASIC extension — is the charter-raising Phase-2 item.) Full pinned
contract: [`disk/docs/expansion-protocol.md`](disk/docs/expansion-protocol.md).

- [x] **Host side (`zerobas-BASIC`)** — DONE. The FAT12 read+write engine is ported
      loader-side into [`basic/fat.asm`](basic/fat.asm) (from `disk/disk.asm`, our own
      clean-room code) and driven through the standard **`CALSLT $4010` (DSKIO)** entry
      with the MSX2-TH register convention (A=drive, B=#sec, C=media, DE=sector, HL=buf,
      **CY=read/write**); the slot is the INIT-scan `DISKSLOT` capture, the address the
      fixed `$4010` offset (NOT `bdos_entry`/`$F37D`). The four verbs are rewired:
      `do_disk_bload` ([`basic/bload.asm`](basic/bload.asm)) + `disk_prog_load`
      ([`basic/cload.asm`](basic/cload.asm)) use `fat_io_open`/`fat_io_getbyte`;
      `do_bsave`/`do_save` ([`basic/save.asm`](basic/save.asm)) use `fat_io_create`/
      `fat_io_putbyte`/`fat_io_close`. The private `bdos_entry`/FCB path is retired from
      the loader (dead RAM/BDOS equates removed from sysvars.inc). DSKIO + the on-disk
      BPB suffice (no GETDPB on the host side). **Oracle (both disk ROMs):**
      `BLOAD"A:"`/`LOAD"A:"`/`RUN"A:"`/`SAVE"A:"`/`BSAVE"A:"` ALL PASS under
      zerobas-BASIC with (i) our own `disk.rom` AND (ii) the foreign National
      **CF-3300** disk ROM in slot 3-1 — proving the host side disk-ROM-independent
      (CF-3300 failed every verb on the old `bdos_entry` path). See basic/PROVENANCE.md
      §disk DSKIO host engine. Sources: MSX2 TH / MSX Assembly Page DSKIO contract;
      no disassembly.
- [x] **Provider side (`zerobas-disk`)** — DONE. INIT now installs the standard
      **`HPHYD ($FFA7)`→DSKIO ($4010)** hook via the `RST 30h`/`CALLF` + slot-byte
      idiom (slot byte = A on INIT entry; oracle-confirmed `$87` = slot 3-1), and
      **`GETDPB ($4016)` is real** — it builds the DPB from the on-disk BPB and is
      **field-for-field byte-identical to a black-box CF-3300 GETDPB trace** on the
      720 KB image (`f9 00 02 0f 04 01 02 01 00 02 70 0e 00 ca 02 03 07 00`).
      (`bdos_entry`/FAT/BDOS stay as the internal implementation.) End-to-end
      provider read confirmed: `CALL $FFA7` (the installed hook) crosses into our
      DSKIO and reads the boot sector byte-identically. See disk/PROVENANCE.md
      §INIT + §DPB. The DPB field encoding was the one genuinely-new clean-room item.
- [x] **Oracle — disk-ROM independence, both directions** — committed scope DONE
      (host + Tier-1 provider). The Tier-2 sub-item below is carried to **Phase 2**.
      (a) **DONE (host):**
      `BLOAD"A:"`/`LOAD"A:"`/`RUN"A:"`/`SAVE"A:"`/`BSAVE"A:"` round-trip under
      `zerobas-BASIC` with zerobas-disk **and** with the foreign National CF-3300
      disk ROM in slot 3-1 — ALL PASS on both (machines built via
      `install-openmsx-machine.py --disk-rom <ROM>`; probes `disk_probe_bload_disk.py`
      / `disk_probe_save.py` / `disk_probe_load_disk.py` / `disk_probe_run_disk.py` /
      `disk_probe_load_embedded_nul.py`). (b) **Tier 1 DONE (provider):** an
      **organic real MSX1 BIOS** drives zerobas-disk through the standard hook/DSKIO
      path. On `National_CF-3300_ZEROBASDISK` (real CF-3300 BIOS in slot 0, zerobas-disk
      in slot 3-1; built via `install-openmsx-machine.py --real-bios-disk`), the
      genuine BIOS cold-boot scan calls our INIT → installs `H.PHYD ($FFA7)=F7 87 10
      40 C9`, and a **real BIOS `PHYDIO` ($0144)** call (entry from the MSX Assembly
      Page / MSX2 TH BIOS jump table — no disassembly) routes *through* that hook into
      our DSKIO: sector 0 byte-identical to the on-disk boot sector, `CY=0`, plus a
      CY=1 write+readback round trip. The no-injected-hook property is proven two
      ways — the hook bytes are read back after a clean cold boot *before* any stub
      runs, and a breakpoint on `$FFA7` is *hit* during the BIOS PHYDIO call (the hook
      is load-bearing, not bypassed). Harness:
      `probes/disk/disk_probe_provider_phydio.py` (ALL PASS). The earlier
      injected-hook `CALL $FFA7`, HPHYD-bytes, and CF-3300 GETDPB differential checks
      still stand under it. **Tier 2** — a real *filesystem* host (DOS/Disk-BASIC,
      which alone consumes GETDPB organically) — requires DOS-boot or Disk-BASIC
      hosting = **Phase 2**. See
      [`disk/docs/provider-oracle-scope.md`](disk/docs/provider-oracle-scope.md).

**Outcome.** Both transports now sit on standard interfaces (tape uses the BIOS
cassette entries; disk uses DSKIO/`HPHYD`/`GETDPB`), and disk interoperates both
directions — the point of the whole basic/tape/disk split. The only piece not yet
exercised is the Tier-2 provider oracle, now part of Phase 2.

## Phase 2 — full disk (Disk BASIC integration) — ✅ VERB SURFACE COMPLETE

**Close-out (2026-06-22).** The Disk BASIC verb surface zerobas's current
capabilities can faithfully support is **done and oracle-validated** — sequential
file I/O (`OPEN`/`CLOSE`/`PRINT#`/`INPUT#`/`LINE INPUT#`/`INPUT$`, `MAXFILES`,
`APPEND`), `PRINT USING` (+`PRINT# USING`), file/dir management
(`FILES`/`KILL`/`NAME`/`MERGE`), position/info (`EOF`/`LOF`/`DSKF`), random-access
records (`FIELD`/`GET`/`PUT`/`LSET`/`RSET` + `MKI$`/`CVI`), and `CALL FORMAT` (both
geometries + menu). The whole stack was also proven **host-BIOS-independent** on a
real Philips VG-8020. The in-RAM halves of these verbs now also carry a fast
emulator-free regression (`make unit-test`: `test_tokenise`/`test_field`/
`test_printusing`); the sector-moving halves stay in the openMSX probes.

**Explicitly carried / deferred (not part of "complete"):**
- **Tier-2 provider oracle** (a real MSX-DOS 1 host driving zerobas-disk) — a
  distinct DOS-boot sub-track. **ACTIVE again (2026-06-23):** an earlier "walled by
  policy" call (§8.12) was retracted — it forgot that undocumented disk-ROM entries are
  characterisable by **black-box oracle** (the same discipline that nailed GETDPB), not
  only by published docs. The boot already loads+executes MSXDOS.SYS byte-perfect off
  our `bdos_entry`; the gap is one disk-ROM entry (`$4030`), now under active black-box
  characterisation (oracle built, first contract captured). **Not** writing our own
  MSX-DOS 1 — existing disks drive our clean-room reimplementation of the observed entry
  contract. See below + provider-oracle-scope.md §8.13.
- **`DSKI$` / `DSKO$`** — investigated, **deferred to Phase 3** (obscure CF-3300
  semantics + needs the Phase-3 string heap; see the item below).
- **`MKS$`/`MKD$`/`CVS`/`CVD`** (random-access float conversions) and the float-only
  `PRINT USING` specs — gated on **Phase-3 floating point**.
- **`LOC(#n)`** (unclear sequential semantics) and **`LFILES`** (printer-bound) —
  deferred; observed + documented in PROVENANCE.

A deliberate **charter raise** from loader-stub toward a faithful disk experience.
Chosen as the next phase because it *completes the storage story* the
basic/tape/disk split is built around — a self-contained, oracle-validatable slice
— rather than boiling the ocean on the full language (that stays Phase 3+). The
disk *ROM* (`disk/`) is already complete (FDC + FAT12 + BDOS, read+write,
oracle-confirmed); this phase is the **interpreter-side Disk BASIC integration**.

**Approach — spike first, then decide, then build.** Unlike Phase-1 items the
protocol isn't pinned, so step 0 is a research spike; only after it do we pick the
architecture and write code. Each step is independently oracle-validatable.

### Step 0 — file-channel protocol spike (the gate) — ✅ DONE
- [x] **Black-box the DEVICE/STATEMENT expansion + file-channel protocol** on the
      real **National CF-3300** Disk BASIC (boots to Disk BASIC; ROMs in
      `~/.openMSX/share/systemroms/`). The Phase-1.5 spike deliberately skipped this:
      it proved the *drive-letter loader* path is pure DSKIO and never touches the
      DEVICE expansion (`PROCNM $FD89` / `DEVICE $FD99` stay zero) — see
      [`disk/docs/expansion-protocol.md`](disk/docs/expansion-protocol.md) §0/§5 — but
      the *file verbs* (`OPEN`/`PRINT#`/`INPUT#`/`FILES`/…) are exactly where that
      expansion fires. Observe (clean-room: BP on documented addresses + live register
      read-out; **never read/disassemble the reference ROM**):
        1. **Dispatch** — typing `FILES` / `OPEN"A:F"…`, how control reaches the disk
           ROM's STATEMENT (`$4004`) / DEVICE (`$4006`) handler; the request-code /
           work-area (`PROCNM`, `DEVICE`, file-number) contract.
        2. **File-channel I/O** — `OPEN`→`PRINT#`/`INPUT#`→`CLOSE`: the register-level
           open-by-name, sequential read/write, and close calls; the FCB / channel
           buffer structures; how bytes flow.
- [x] **DONE** — [`disk/docs/file-channel-protocol.md`](disk/docs/file-channel-protocol.md)
      + probe `diskbasic_probe_filechannel.py`. Headline: the **file I/O verbs move
      bytes through the SAME standard DSKIO+FAT12+FCB substrate as the loader path**
      (not a separate channel protocol); they are built-in tokens (STATEMENT/DEVICE
      expansion never fires). Result: **GO, and EXTEND** (layer the verbs on the
      existing `basic/fat.asm` engine; keep `fat.asm`, don't retire it).

### Step 0b — `CALL`-dispatched commands spike — ✅ DONE
- [x] **DONE** — `diskbasic_probe_format.py` on real CF-3300: `CALL FORMAT` writes
      `PROCNM ($FD89) = "FORMAT"` (confirming STATEMENT-expansion dispatch, unlike the
      zero-PROCNM file verbs) and drives `CHOICE ($4019)` (the `Drive name?` + format-
      type menu) → `DSKFMT ($401C)`. EXTEND-vs-DELEGATE for `CALL` commands documented
      (lean EXTEND: a `CALL`/`_` parser + own `CHOICE`/`DSKFMT`); the generic STATEMENT
      dispatcher is an optional follow-on. See file-channel-protocol.md §1a.

### Step 1 — architectural fork: RESOLVED (file verbs = EXTEND)
For the **file I/O verbs** the spike resolves it: **EXTEND** over the existing
`basic/fat.asm` engine; `fat.asm` is kept, not retired. (For `CALL`-dispatched
commands the documented expansion seam exists — fork still open, gated on Step 0b.)

### Step 2 — implement the verb surface (each oracle-validated vs CF-3300)
Full DOS1-class Disk BASIC vocabulary, grouped; **[in]** = recommended Phase-2,
**[?]** = scope to confirm, **[out]** = deferred. Build smallest end-to-end path
first (`FILES`, then `OPEN`+`INPUT#`+`CLOSE`), grow outward.
- [x] **Sequential file I/O [in]** — `OPEN`, `CLOSE`, `PRINT#`, `PRINT# USING`,
      `INPUT#`, `LINE INPUT#`, `INPUT$(n,#f)`. The spike-confirmed core. **DONE** —
      every sub-item below landed + oracle-validated. (`PRINT# USING` file form: a
      format-copy overrun corrupted it until 2026-07-18 — pu_deref_body clobbered the
      A holding the length, so the ldir count became the literal's pointer-low byte;
      fixed by preserving A. CF-3300 byte-validated, `disk_probe_printusing_file.py`.
      Root cause + fix: [docs/spec-print-hash-using.md](docs/spec-print-hash-using.md).)
      - [x] **read path: `OPEN…FOR INPUT` + `INPUT#` + `LINE INPUT#` + `CLOSE`** —
            DONE (basic/files.asm). EXTEND over the fat.asm sequential reader
            (`fat_io_open`/`fat_io_getbyte`); single channel; string vars only.
            Tokens OPEN=$B0/INPUT=$85/LINE=$AF/CLOSE=$B4 oracle-locked to the
            VG-8020 crunch; `OPEN"HI.TXT"…:LINE INPUT#1,A$:CLOSE#1:PRINT A$` prints
            the file's line byte-for-byte and the **real CF-3300 prints it
            identically** (`disk_probe_fileread.py` differential). See
            basic/PROVENANCE.md §file channel — sequential read.
      - [x] **write path: `OPEN…FOR OUTPUT` + `PRINT#` + `CLOSE`** — DONE
            (basic/files.asm + the PRDEST/`pchar` redirect in basic/print.asm).
            `PRINT#` reuses the screen-PRINT item loop redirected to the channel;
            CLOSE appends the `Ctrl-Z` ($1A) text-EOF marker. Tokens oracle-locked
            (`OUTPUT`→`OUT $9C`+`PUT $B3`, `PRINT#`→$91); write→read-back round-trips
            and the on-disk `OUT.TXT` is **byte-identical to the real CF-3300**
            (`b"hello world\r\n\x1a"`, `disk_probe_filewrite.py` differential). See
            basic/PROVENANCE.md §file channel — sequential write.
      - [x] **`MAXFILES` + the multi-channel table** — DONE (basic/files.asm channel
            manager + basic/sysvars.inc FCH_CTX). Retires the single-channel limit:
            up to `FCH_CEIL`(=2) channels open at once, via a **write-back context
            cache** over the UNCHANGED fat.asm (each channel owns a saved
            [state][512-buf] block; the globals hold the active channel; switching
            saves+loads). `MAXFILES` = MAX($CD)+FILES($B7) oracle-locked; default 1;
            bare CLOSE closes all. Two OUTPUT files written **interleaved** produce
            on-disk images **byte-identical to the real CF-3300**
            (`disk_probe_maxfiles.py`). RAM-bounded ceiling (real MSX=15) documented.
            See basic/PROVENANCE.md §MAXFILES.
      - [x] **`OPEN…FOR APPEND`** — DONE (basic/fat.asm `fat_io_append` +
            basic/files.asm OPEN mode parse). Opens an existing file positioned at
            EOF; "APPEND" = APP(ascii)+END($81), already byte-identical (no new
            token). Walks the chain reusing the read primitives, primes the write
            iterator at EOF, and overwrites a trailing Ctrl-Z (CP/M text append).
            On-disk result **byte-identical to the real CF-3300**
            (`disk_probe_append.py`: create "first" + append "second" ->
            `first\r\nsecond\r\n\x1a`). See basic/PROVENANCE.md §OPEN … FOR APPEND.
      - [x] **`INPUT$(n,#f)`** — DONE (basic/strvar.asm `str_eval` INPUT$ branch).
            Reads exactly n raw bytes from channel f as a string (no delimiters;
            cursor advances by n). zerobas's first string-returning function;
            "INPUT$" = INPUT($85)+'$' (no new token). `A$=INPUT$(5,#1)` then
            `INPUT$(6,#1)` on HI.TXT yield "Hello" then " from " **byte-identical to
            the CF-3300** (`disk_probe_inputdollar.py`). STRMAX clamp + keyboard form
            (no `#`) deferred. See basic/PROVENANCE.md §INPUT$.
      - [x] **`PRINT USING`** — DONE (basic/printusing.asm). Formatted output:
            numeric `#` fields (right-justified, `%` overflow, negative sign),
            string fields (`\ \` fixed width, `!` first char, `&` whole), literal
            passthrough, and format reuse when values outrun the template. USING token
            $E4 (oracle-locked). 7 cases incl. `PRINT USING "## ";1;2;3` →
            ` 1  2  3 ` **byte-identical to the real VG-8020** (`basic_probe_printusing.py`).
            This is the COMPLETE feature for zerobas's integer domain; the float-only
            specs (`.` decimal, `^^^^`, `+`/`,`/`**`/`$$`) arrive with Phase-3 floats.
            See PROVENANCE §PRINT USING.
      - [x] **`PRINT# USING`** — DONE (basic/print.asm). The file form: after
            `PRINT #n[,]` the USING token routes into the same ex_print_using formatter
            with PRDEST=1, so the formatted bytes stream to the channel via pchar. On-
            disk round-trip byte-identical to the CF-3300 (disk_probe_printusing_file.py).
            Oracle finding: the CF-3300 (National ROM) supports only `#`/`!` PRINT USING
            fields, not `\..\`/`&` (which the VG-8020 — and zerobas — do); see PROVENANCE.
- [x] **File/dir management [in]** — `FILES`✅, `KILL`✅, `NAME…AS…`✅, `MERGE`✅ — **DONE**
      (the `LOAD`/`SAVE`/`BLOAD`/`BSAVE`/`RUN"f"` already exist from Phase 1). `LFILES`
      is printer-bound (no device in zerobas) — deferred.
      - [x] **`MERGE "name"`** — DONE (basic/files.asm `ex_merge`). Reads an ASCII
            (SAVE",A") line-numbered program file and feeds each line through the
            same `dispatch_line` (tokenise + `store_line`) path as a typed line, so
            lines insert/replace into the CURRENT program (kept, unlike LOAD). Token
            $B6 oracle-locked. Build-source-via-PRINT# + MERGE + RUN computes 123
            **identical to the CF-3300** (`disk_probe_merge.py`). ASCII-only (no
            tokenised MERGE). See basic/PROVENANCE.md §MERGE.
      - [x] **`NAME "old" AS "new"`** — DONE (basic/files.asm). Rewrites the dir
            entry's 8.3 name (no FAT change); token $D3 oracle-locked; post-rename
            disk image **byte-identical to the real CF-3300** (`disk_probe_name.py`).
            See PROVENANCE §NAME.
      - [x] **`KILL "name"`** — DONE (basic/files.asm + fat.asm `fat_delete`). Frees
            the FAT chain + marks the dir entry `$E5`; token $D4 oracle-locked; the
            post-KILL disk image is **byte-identical to the real CF-3300**
            (`disk_probe_kill.py`). Single file (no wildcard). See PROVENANCE §KILL.
      - [x] **`FILES`** — DONE (basic/files.asm). Lists the root directory by
            EXTEND over the fat.asm engine (`fat_mount` + directory walk + 8.3 field
            render); width-driven wrap via `CSRX`/`LINLEN`. Token `$B7` oracle-locked
            to the VG-8020 crunch (`basic_probe_crunch.py` case `files`); listing
            **byte-identical to the real CF-3300** at WIDTH 29 and correct at native
            width (`disk_probe_files.py` / `diskbasic_probe_files.py`); LIST detok +
            the host unit-test suite still pass. Divergence: optional `<filespec>`
            pattern parsed-past + ignored (full-dir listing only). See
            basic/PROVENANCE.md §FILES.
- [x] **File-position / info functions [in]** — `EOF`✅, `LOF`✅, `DSKF`✅ — **DONE**.
      `LOC`(deferred, unclear semantics), `VARPTR(#n)`(deferred) below.
      - [x] **`EOF(#n)` + `LOF(#n)`** — DONE (basic/expr.asm `ev_f_ff`). $FF-prefixed
            function tokens ($FF$AB / $FF$AD), oracle-locked; `PRINT LOF(1);EOF(1)`
            after OPEN = `26 0` byte-for-byte vs the real CF-3300, and EOF→-1 once
            the file is exhausted (`disk_probe_eof.py`). See PROVENANCE §EOF / LOF.
      - [x] **`DSKF(d)`** — DONE (basic/expr.asm + fat.asm `fat_count_free`). Free-
            cluster count via a sector-cached FAT scan; $FF$A6 oracle-locked;
            `PRINT DSKF(0)`=707 matches a direct FAT12 count AND the real CF-3300
            (`disk_probe_dskf.py`). See PROVENANCE §DSKF.
      - [ ] **`LOC(#n)`** — deferred: CF-3300 `LOC(1)` returns 26 (file size) both
            before and after a read; sequential-file semantics unclear, so not
            cargo-culted. **`LFILES`** — printer-bound (LPT), no device in zerobas.
            Both observed + documented in PROVENANCE §LOC / LFILES.
- [x] **Config [in]** — `MAXFILES` (sizes the channel table) — DONE; see the
      sequential-I/O sub-item above + basic/PROVENANCE.md §MAXFILES.
- [ ] **Direct sector access — INVESTIGATED, DEFERRED to Phase 3** — `DSKI$` (fn,
      $EA) / `DSKO$` (stmt, $D1). Tokens oracle-confirmed real (VG-8020 crunch), but
      NOT a clean "sector ↔ string" pair, and blocked on three counts:
      1. **Obscure semantics.** Black-box CF-3300: `A$=DSKI$(0,0)` succeeds but
         `LEN(A$)=0` — it does NOT return the sector as the string value (data goes to
         a system buffer, accessed elsewhere); and `DSKO$ 0,0,A$` is a *Syntax error*
         (the 3-arg form is wrong). The real buffer/arg model needs more CF-3300
         reverse-engineering of an arcane, rarely-used verb.
      2. **String model.** A sector is 512 B; an MSX string's length byte maxes at 255;
         zerobas's inline strings cap at STRMAX=32. Representing sector data as a string
         value needs the Phase-3 string engine (heap + real descriptors), not the
         minimal inline store.
      3. **No clean oracle.** The only disk oracle (CF-3300) shows the quirky behavior
         above; the VG-8020 is diskless so can't exercise it functionally.
      Low-value + low-use; revisit once Phase-3 strings exist. (Was assumed a thin
      DSKIO wrapper; the oracle proved otherwise — 2026-06-22.)
- [x] **Random-access files [in → sub-phase 2c]** — `FIELD`✅, `GET`✅, `PUT`✅, `LSET`✅,
      `RSET`✅ + conversion fns `CVI`✅/`MKI$`✅ — **DONE** (sub-phase 2c complete). A
      heavier, self-contained record-file feature; built + oracle-validated as its
      **own sub-phase (2c)**. The float-conversion siblings `CVS`/`CVD`/`MKS$`/`MKD$`
      await Phase-3 floats — deferred.
      - [x] **`MKI$(n)` + `CVI(s$)`** — DONE (basic/strvar.asm + basic/expr.asm). The
            integer conversion pair: MKI$ packs a 16-bit int into a 2-byte LE string
            ($FF$AE, string result, in str_eval); CVI is the inverse ($FF$A8, numeric
            result with a string arg, in ev_ff_cvi bridging IX↔HL to str_eval).
            `A$=MKI$(258)` + `C$=MKI$(CVI(A$))` write M.DAT = `\x02\x01\x02\x01\x1a`
            **byte-identical to the CF-3300** (`disk_probe_mkicvi.py`). Float siblings
            (MKS$/MKD$/CVS/CVD) need Phase-3 floats — deferred. See PROVENANCE §MKI$/CVI.
      - [x] **`FIELD` + `LSET` + `RSET` (slice 1 of 2)** — DONE (basic/field.asm +
            str_eval/clear_vars/OPEN hooks). RANDOM open (`OPEN"name" AS #n`, no FOR)
            sets up an in-RAM record buffer; FIELD partitions it into named slices (a
            side table, since zerobas stores strings inline — no MS-BASIC descriptor to
            repoint); LSET/RSET store left/right-justified + space-padded; reading a
            fielded var yields its slice (str_eval hook). Tokens oracle-locked (FIELD
            $B1 / LSET $B8 / RSET $B9). `OPEN"R.DAT" AS #1 : FIELD#1,5 AS A$,10 AS B$ :
            LSET A$="HI" : RSET B$="END" : PRINT` → `<HI   |       END>` **byte-
            identical to the CF-3300** (`disk_probe_field.py`). See PROVENANCE
            §FIELD/LSET/RSET.
      - [x] **`GET` + `PUT` (slice 2 of 2)** — DONE (basic/field.asm). Random record
            I/O: `PUT #f,N` writes the record buffer to record N (256-byte records,
            oracle-confirmed via LOF), `GET #f,N` reads it back. Composes the fat.asm
            engine unchanged — the chain walk uses a private `frnd_next` over FWBUF so
            the live record in FSECTOR_BUF survives; PUT read-modify-writes the shared
            512-byte sector (2 records/sector) and extends the cluster chain; the dir
            entry is stamped so data survives CLOSE/reopen. RANDOM open made real
            (`fat_rand_open` opens-or-creates + seeds channel state). Tokens GET $B2 /
            PUT $B3. Write 2 records → CLOSE → reopen → GET back = `<alpha|  bet>` +
            `<gamma|delta>` **byte-identical to the CF-3300** (`disk_probe_getput.py`).
            Divergences: record 1..255, bare GET/PUT default to record 1, no LEN=.
            See PROVENANCE §GET/PUT. **→ sub-phase 2c (random-access) COMPLETE** (the
            float-conversion siblings MKS$/MKD$/CVS/CVD still await Phase-3 floats).
- [x] **`CALL FORMAT`** — DONE (basic/format.asm). Writes a fresh empty 720 KB
      FAT12 filesystem on drive A, no prompts (zerobas-disk has one geometry, so its
      CHOICE offers nothing to ask). zerobas-BASIC lays the boot sector (BPB) + 2 FAT
      copies + empty root dir down ITSELF via the standard $4010 write_sector — not via
      zerobas-disk's DSKFMT stub (the Phase-1.5 "BASIC owns the filesystem" model).
      Geometry is parameterized (a GEOM_720K descriptor table) so 360 KB (CF-3300
      media $FD/720-sec/2-sec-per-FAT) is a clean later add + the CHOICE prompt. CALL
      token $CA; the device name after CALL/`_` is kept verbatim (a new tokeniser
      exception — oracle: `call format` keeps "FORMAT", not FOR+MAT). Structural BPB +
      FAT byte-identical to a CF-3300 "2 sides, double track" format, and a file
      round-trips on the fresh disk (disk_probe_format.py). Boot-code region + OEM are
      zerobas' own (documented divergence — won't copy ROM code; CF-3300 writes no
      $55AA either). See PROVENANCE §CALL FORMAT.
      - [x] **360 KB + the geometry menu** — DONE (basic/format.asm). Added a
            GEOM_360K descriptor (media $FD, 720 sectors, 2 sec/FAT) and a minimal
            `1=360k 2=720k?` prompt (read via the REPL line editor; drive + confirm
            prompts trimmed). do_format reads the chosen descriptor through FMT_DESC —
            geometry-agnostic. Both geometries' BPB + FAT head byte-identical to the
            matching CF-3300 format (360K = "2 sides", 720K = "2 sides double track"),
            and a file round-trips on each fresh disk (disk_probe_format.py).
- `CALL SYSTEM` **[out]** — exit to MSX-DOS = the DOS-boot path (Tier-2 sub-track).
- `CALL CHDRV` etc. **[out]** — Disk BASIC v2/v3 additions, beyond DOS1-class 1.0.

### Carried oracle — Tier-2 provider (DOS1; a distinct DOS-boot sub-track)
The only Phase-2 thread still genuinely open: a real **MSX-DOS 1** filesystem host
(black-box; **DOS1 is the confirmed ceiling**), the only organic `GETDPB` consumer,
driving zerobas-disk end-to-end. Per the circularity finding a real DOS only exists
once a disk ROM loads `MSXDOS.SYS`, so this is gated on building **MSX-DOS-boot
support** in zerobas-disk — a distinct sub-track from the verb surface above. **DOS2**
(Nextor / Sunrise 2.20 / the open MSX-DOS2 kernel) is a future axis, not this phase.

- [x] **Feasibility spike — DONE (2026-06-22).** Both prerequisites checked
      empirically (see [`provider-oracle-scope.md`](disk/docs/provider-oracle-scope.md)
      §7). (1) A real DOS1 system disk **exists (permanent)**:
      a local `test.dsk` boots the stock CF-3300 to
      `MSX-DOS version 1.03 … A>` (same image as the recorded BDOS oracle). (2) The
      gap is **pinned**: the *same* disk on the Tier-1 machine
      (`National_CF-3300_ZEROBASDISK`) falls through to **`MSX BASIC version 1.0`**,
      even though `H.PHYD` is installed — zerobas-disk's INIT installs the hook but
      **never reads the boot sector / chainloads the DOS**. Result: **GO**.
- [ ] **2-Tier2-a — DOS boot (steps 4–7).** Deeper than first scoped: a build attempt
      proved the boot is a **four-step environment hand-off** (MSX2 TH ch.3), not a
      one-call bridge — see [`provider-oracle-scope.md`](disk/docs/provider-oracle-scope.md) §8.
      - [x] **a1 — steps 4–5 (boot bridge). DONE + regression-gated.** `boot_disk` in
            INIT reads sector 0 → `$C000`, checks the `$EB`/`$E9` signature, and `CALL
            $C01E` CY-reset; the data-disk `RET NC` fall-through is preserved. **Now
            committed to `disk.asm`** (not reverted): regression-gated on
            `C-BIOS_MSX1_BASIC_DISK` + `test720.dsk` — `disk_probe_files` and
            `disk_probe_bload_disk` both PASS (BASIC+disk boots, byte-identical FILES,
            BLOAD `,R`/plain), and oracle-confirmed on `National_CF-3300_ZEROBASDISK` +
            a DOS disk (`$C01E` reached, `AF=$EBAC` ⇒ A=`$EB`, carry reset).
      - [ ] **a2 — step 6 (the real work): page-0 MSX-DOS environment.** Designed:
            see [`provider-oracle-scope.md`](disk/docs/provider-oracle-scope.md) §8.1
            (documented page-0 layout pinned + the step-5→7 RAM-in-page-0 delta
            traced). Order: (1) page RAM into page 0 (slot paging — the hang-prone
            part, validate in isolation); (2) lay the page-0 env per the CP/M-style
            layout (`$0000` warm-boot, `$0005`→a trampoline to our existing
            **`bdos_entry`**, `$0006-7` TPA top, `$0038` int, `$0080` DMA); (3) the
            two-phase `$C01E`. **Reuse:** `bdos_entry` (oracle-validated MSX-DOS-1 FCB
            BDOS) IS the resident BDOS — don't rebuild it. **Open Q (resolve by
            experiment, not by tracing the MS boot code):** does the boot code load
            MSXDOS.SYS via `$0005` BDOS or via direct PHYDIO sector reads?
            **(1) is VALIDATED** (§8.2): the RAM-into-page-0 slot dance works on the live
            Tier-1 machine (`$A8` page-0→slot 3 + `$FFFF` page-0 subslot→0, run from
            page 1, `di`; wrote/read `$A5` at `$0000`, ROM `$F3` restored after).
            **Open Q RESOLVED** (§8.3): the boot loads MSXDOS.SYS by **direct sector
            reads, NOT `$0005` BDOS** (the first BDOS calls come from already-relocated
            high-RAM DOS, not the boot sector) → no resident-BDOS/TPA needed.
            **Real core of step 6 found** (§8.4): with RAM in page 0, `H.PHYD`'s
            `RST 30h`/CALLF breaks (page-0 BIOS gone), so step 6 must stand up a minimal
            RAM-resident inter-slot path. **Advantage:** page 1 stays our ROM, so DSKIO
            is directly `CALL $4010`-able — next build = a tiny `$0030` CALLF shim in RAM
            page 0 + the two-phase `$C01E`, then observe whether `A>` appears.
            **First full build done + reverted** (§8.5): the DOS boot path now RUNS
            (both `$C01E` calls reached, RAM in page 0, code executes in page-0 RAM,
            screen "MSX system version 1.0" not the BASIC fall-through). Two concrete
            gaps remain: **(A) CHARACTERISED (§8.6):** a black-box trace of the *working*
            CF-3300 boot shows it **does** reach standard DSKIO (`$4010`, 5×) via a *full*
            page-0 `JP`-vector table (`$000C`/`$001C`/`$0024`/`$0030`/`$0038`). Our build
            hung at `$1418` *before* the DSKIO call because our minimal env (`$0030` shim +
            `$0038` stub) lacked a vector the boot calls. Fix: lay the fuller vector set
            (shape per TH ch.3, our own RAM targets), disk path via `$0030`→direct `CALL
            $4010` (our ROM stays in page 1). Residual: trap which vector fires at `$1418`
            in the next bridge build. **(B) RESOLVED + VALIDATED:**
            the paging hardcoded "RAM = slot 3-0" (`or $03`/`and $FC`) — broke the C-BIOS
            host; corrected to **derive the RAM slot from page 3's bits** (`$A8`/`$FFFF`
            bits 7-6 → page-0 bits). `page0_ram_in`/`page0_ram_out` are now in `disk.asm`,
            **self-tested on `C-BIOS_MSX1_BASIC_DISK`** (the previously-hanging host):
            `$0000` accepts `$A5` after RAM-in, reads `$F3` after restore, machine running
            (§8.2). Routines committed but uncalled; **step 6 wires them in next.**
            **STEP 6 BUILT + regression-green (§8.7).** The `$0030` CALLF handler (register-
            preserving → direct `CALL $4010`), the `lay_page0_env` JP-vector set
            (`$000C`/`$0014`/`$001C`/`$0024`/`$0030`/`$0038` → our own page-1 handlers),
            and the step-6/7 wiring (`di`→`page0_ram_in`→`lay_page0_env`→`scf`→step-7
            `$C01E`→ data-disk return → `page0_ram_out`→`ei`→BASIC) are in `disk.asm`.
            `disk_probe_files` + `disk_probe_bload_disk` PASS on `C-BIOS_MSX1_BASIC_DISK`
            (step 6 paging runs there: sig `$EB`, `$1E` stub `D0 C9`); `disk_probe_init`
            PASS (`bdos_entry` now `$439F`). a3 trap verified the env is laid correctly at
            step-7 entry — **but REFUTED the §8.4 inter-slot premise** (§8.7): the real
            MSX-DOS boot uses **none** of H.PHYD / DSKIO / our page-0 vectors / our ROM
            header; it expects the standard **disk WORK AREA** (`DRVTBL` + driver slot/entry)
            and, absent it, falls back to a slot scan that wedges on the expanded slot 3.
      - [ ] **a3 — SIZED by black-box differential = charter-level subsystem (§8.8).** A
            clean-room RAM differential (stock CF-3300 vs Tier-1, data disk → BASIC) shows
            the base BIOS sets only `EXPTBL`; the **disk ROM** installs `RAMAD0-3`
            (`83 00 83 83` stock vs **`FF` ours**), the `$F348` disk work-area/DRVTBL JP
            table (into high-RAM `$95xx/$DFxx`), the `$FE/$FF` DOS hook set, per-drive DPBs,
            and the device table — all absent in ours. Those targets are a **resident DOS
            kernel the stock relocates into high RAM**, i.e. the opaque proprietary code the
            clean-room rule forbids. ⇒ DOS-boot = build the disk ROM's full resident DOS
            environment, a multi-slice Phase-2+ effort that abuts the no-disassembly wall.
            **REOPENED + progressing (2026-06-22, §8.9) — §8.8 pessimism refuted.** The boot
            drives our OWN `bdos_entry`, not a rebuilt kernel. **Slice-1 DONE + committed**
            (`f1035a0`): `$F37D` is the disk system's BDOS-call JP vector (the boot `CALL`s it
            with C=$0F Open, DE=FCB "MSXDOS  SYS"); INIT had written a raw word there → the
            `$0038` wedge. INIT now publishes `$F37D` = `JP bdos_entry` (safe — Phase-1.5
            loader no longer reads it). Wedge gone; boot reaches bdos_entry/Open/fat_mount,
            finds MSXDOS.SYS. Regression-green (files+bload_disk+init on C-BIOS; bdos oracle
            PASS via `$F37E`). **Slice-3 (next):** the boot loads MSXDOS.SYS via BDOS **`$27`
            (Random Block Read)**, which `bdos_entry` doesn't implement (returns `$FF`) →
            implement it (DE=FCB, HL=rec count, start=FCB random-record `+33`, recsize `+14`,
            read into DTA), validate via a `$27` case in `disk_probe_bdos.py`, re-trap. The
            whole remaining gap to `A>` is that one BDOS function.
            **Slices 3–4 DONE; gap relocated to disk-ROM entry `$4030` (§8.10/§8.11), then
            mis-declared "walled by policy" (§8.12) — that verdict is RETRACTED (§8.13).** The
            §8.12 wall conflated *no published doc* with *no allowed method*: it forgot the
            project's core discipline, **black-box oracle observation** (how undocumented GETDPB
            was nailed byte-identical). `$4030` is the same kind of undocumented disk-ROM entry,
            characterisable as a black box on the genuine CF-3300 and reimplementable from the
            observed contract — no charter change, and **not** writing our own MSX-DOS 1.
            **Oracle built + first contract captured (2026-06-23, `probes/disk/disk_probe_dosboot_4030.py`):**
            deterministic — `$4030` returns a pointer in `HL` (`$F1C9`→`$DD0E`), preserves
            AF/BC/DE/IX/IY, writes nothing in `$F1xx`; on entry `IX` points at drive A's DPB
            (byte-identical to our CF-3300 GETDPB), confirming the disk-driver context.
            **`$4030` IMPLEMENTED + work-area characterised (§8.13-8.15).** Boot drives our
            BDOS, loads MSXDOS.SYS byte-perfect, consumes the `$4030` pointer; derailed at `$0038`.
            **RAMAD0-3 lever found + fixed (2026-06-23, §8.16; `disk_probe_dosboot_lowstore.py`).**
            §8.15's "work-area-layout" theory was REFUTED by oracle (MSXDOS makes 0 post-`$4030`
            low-storage writes; `$0038→$0C3C`, not the work area). The real lever: the Tier-1 vs
            stock differential showed page 0 = all `$FF` (unmapped slot) → `$0038` `RST 38h` wedge,
            because MSXDOS reads **RAMAD0-3 (`$F341-4`, 84×)** to re-page page-0 RAM and the disk
            ROM's INIT (ours) never set it. `set_ramad` (host-adaptive, `$FF`-gated, C-BIOS-safe)
            now sets it `83 83 83 83` = byte-identical to stock; **page-0 RAM maps and MSXDOS
            installs its BDOS (`$0005→$E106`)** — a real advance. `bdos_entry`→`$43EA`; regression
            green (init/files/bload/dskio). **Next gap PINNED (§8.17):** after RAMAD, MSXDOS.SYS's
            init does **`CALL $F368`** — a fixed disk-work-area **jump table** (`$F368-$F37C`, stock:
            `$F368→JP $DF57`, `$F36B→$DF59`, `$F36E→$DF70`, `$F371→$F327`, `$F374→$F32C`,
            `$F37D→SYSTEM`) the disk ROM builds; ours has only RAMAD + `$F37D`, so `$F368` is `$FF`
            and the call slides through `$FF` (`RST 38h`). (The apparent "interrupt storm" was a
            SYMPTOM of that slide — `int_h` clears the VDP fine, the FDC is idle; §8.16's ISR guess
            was refuted.) See §8.17.
            **`$F368` TABLE BUILT (§8.18, `disk_probe_dosboot_f368.py`).** Profile: only `$F368`
            (32×) + `$F36B` (31×) are called (IX=drive-A DPB); both are **no-ops on this 64K
            machine** (register/flag-transparent, zero mem/FDC/I/O effects — the disk system's
            RAM-segment-switch hooks, no-op without a mapper). `build_wa_table` lays `JP wa_stub`
            (a `RET`) into `$F368-$F37A` (gated like `set_ramad`; `$F37D`=SYSTEM left intact).
            `bdos_entry`→`$43FB`; regression-green. **Result — biggest advance yet:** the slide is
            gone, MSXDOS.SYS runs its init and is caught **executing inside our disk driver**
            (`PC=$431x/$436x`, `SP=$C004`) reading the directory — stack holds `"VOL_ID"`. **New gap
            (next):** a downstream **stack-corruption derail** — MSXDOS reaches `$4010` once with
            garbage args (`Cy=1`, `B=232`, `DE=$E880`) because `SP` points into ASCII data, not a
            stack. See §8.18.
            **ROOT CAUSE FOUND (§8.19) = HIGH-RAM COLLISION.** The derail is a `RST 38h` slide at
            `$8004` reached via a corrupted stack: `SP=$E6FE` points into MSXDOS.SYS's relocated
            kernel jump table at `$E700+`. MSXDOS's kernel sits at `$E1xx-$E7xx` (BDOS `$E106`),
            **overlapping our disk-ROM scratch** (`SECTOR_BUF $E2A0`, `WBUF $E560`, `GETWRK_AREA
            $E780`). The stock avoids it by reserving high RAM (`HIMEM $FC4A=$DF93`, work area
            `$DD0E`); ours never reserves, so MSXDOS relocates up into our scratch → collision.
            **Lever narrowed (§8.20): NOT HIMEM.** Stock BDOS base (`$0005`) = `$D606`, ours =
            `$E106` — differ by exactly `$1000` (4KB). Setting `HIMEM=$DF93` did NOT move the kernel
            (and regressed the boot) → reverted. MSXDOS-1 reads some other top-of-RAM source `$1000`
            higher on our host. See §8.20.
            **CONCRETE LEVER FOUND (§8.21).** A no-disk VG-8020 control confirms our disk ROM does
            **zero** high-RAM reservation (HIMEM `$F380` = the no-disk baseline; stock reserves to
            `$F1BF`/`$DF93`) — the `$1000` is the disk resident footprint we under-reserve. And the
            decisive find: **MSXDOS.SYS reads the `$F348` DRVTBL 208×** after `$4030`, but **ours is
            unbuilt/garbage**, so MSXDOS dispatches disk ops through garbage pointers → the bad jumps
            (the `$8004` slide = a garbage `$95xx`→`$80xx` driver pointer). Stock DRVTBL =
            `87 93df 0edd 95ef..95f1` = slot id | HIMEM top | `$4030` work area | driver-routine
            pointers. **Resume:** build the `$F368`-style `$F348` DRVTBL — slot `$87`, reserved-top +
            `$4030` ptr, driver pointers aimed at OUR `$4010-$401F` entries (never the stock `$95xx`
            kernel); reserve the high RAM alongside; re-trap. This is §8.8's table, now a confirmed
            live dependency — data + pointers to code we have, not a kernel to write. See §8.21.
            **DRVTBL FULLY CHARACTERISED (§8.22, probe `disk_probe_dosboot_drvtbl.py`).** Corrected
            layout: `$95` is the *low* byte — driver pointers are `$EF95/$ED95/$EB95/$F195`, evenly
            `$0200`-spaced and **all above HIMEM `$DF93` in page 3 (always-mapped RAM)**. Decisive
            write-watch: **the disk ROM builds the whole table** (every meaningful write from page 1
            `$453D-$5EAE`; MSXDOS never writes it; reader is one routine at `$0368`, hot field `+5`
            `$EF95`). The pointers are **always-mapped high-RAM trampolines** that CALSLT (slot `$87`)
            into the `$4010` BIOS — needed because under DOS page 1 is the TPA, so `$4xxx` isn't
            directly callable; this IS the `$1000` reservation's purpose. **Build spec:** in INIT,
            under the `$FF` gate — (1) reserve high RAM (lower HIMEM, claim a page-3 block); (2) build
            CALSLT trampolines there, one per driver routine, into our `$4010-$401F`; (3) write `$F348`
            = slot id | reserved-top | `$4030` ptr | trampoline addrs | sentinel. Next micro-step:
            map each trampoline → its `$401x` entry (trap the CALSLT target per pointer), then build.
            **BUILT + COMMITTED (§8.23): `build_drvtbl` in INIT (4 CALLF trampolines @`$E800` +
            the `$F348` DRVTBL), `$FF`-gated, regression-green; bdos_entry `$43FB`→`$4453`.
            VALIDATED CONSUMED** — Tier-1 MSXDOS reads our `$F348` 37× from PC `$0368` (the stock's
            reader). **But NEGATIVE: reserved-top in DRVTBL+1 does NOT move the kernel** — BDOS stays
            `$E106` (stock `$D606`); the §8.19/§8.20 `$1000` collision persists. Derail re-measured:
            the `$0038` wedge is GONE (set_ramad/`$F368`); MSXDOS now re-enables ints (idle in our
            `int_h`) but the main thread runs away to `$FFFF` (98.7% of int samples) — garbage-RET
            from the `$E106` kernel overlapping our `$E2A0-$E780` scratch. **NEXT LEVER: find MSXDOS-1's
            real top-of-RAM source** — trap the stock's kernel-base computation (where it derives
            `$D606`) for the cell/probe it reads, then set it on ours. Strong candidate: a RAM-size
            probe skewed by our ROM's page-2 `$FF` ($8000-$BFFF) vs the stock disk ROM's mapped
            content. (Trampolines built but not yet exercised; their `$401x` mapping unverified until
            the collision clears.) See §8.23.
            **KERNEL LEVER FOUND + FIXED (§8.24, probe `disk_probe_dosboot_ramtop.py`).** Black-box
            differential of the `$0006-7` BDOS-base write: stock `LD ($0006),HL`@`$D7C0` HL=`$D606`
            DE=`$DC80`; Tier-1 same routine @`$E2C0` HL=`$E106` DE=`$E780`. **Invariant DE−HL=`$067A`
            on both** ⇒ `$067A` = kernel size, **DE = kernel TOP = the `$4030` work-area pointer
            (DRVTBL+3)** — so DRVTBL+3 is the lever, NOT DRVTBL+1/HIMEM. (Real gap is `$0B00`, not the
            `$1000` §8.20 mis-arithmetic'd.) **Fix = one equate: `GETWRK_AREA $E780→$DD0E`** (stock
            value); kernel now relocates to **`$D606`, byte-identical to stock**, below our `$E29A`
            scratch. Equate-only, `bdos_entry` stays `$4453`, C-BIOS regression green. **Validated:**
            `final_bdos=c306d6`, `$FFFF`-runaway GONE, boot reads disk heavily through our driver
            (64× `$4030`, 24 open, 37 RDBLK), gets through the MSX banner. **NEXT GAP: a re-init /
            warm-boot spin** — BDOS vector re-published 6× (stock: once); DOS loads but loops before
            `A>`. Characterise what fails between publications (COMMAND.COM load/exec or a disk op
            erroring → warm-boot); trampolines now finally reachable. See §8.24.
            **SPIN ROOT-CAUSED (§8.25, probe `disk_probe_dosboot_reinit.py`).** After a clean
            publication the kernel does `CALL $50A9` (page 1) on BOTH machines (identical regs,
            identical `ppi $A8=$FF` — page-1 slot-3 RAM, NOT corruption). Stock `$50A9` = real
            MSXDOS.SYS loader (boots, publishes once); Tier-1 `$50A9` = **all zeros** → NOP-slide
            crash → warm-boot loop (publishes 6×). No real DSKIO ever fires (crash precedes the first
            sector read). **Root: MSXDOS.SYS's page-1 portion (`$4000+`) was never written to RAM
            during our DOS-boot bridge** — page 1 held our disk ROM during the load, so the upper
            sectors went to ROM / were discarded; the kernel's `$50A9` continuation is empty. The
            page-1 analog of the §8.16 page-0 RAMAD fix. **NEXT: the boot bridge must map page-1 RAM
            (not our ROM) while storing the loaded MSXDOS.SYS**, so `$50A9` holds its loader when the
            kernel calls it. See §8.25.
- [ ] **2-Tier2-b — organic GETDPB.** With DOS up, run a real DOS command (`DIR`/copy)
      and trap `$4016` to prove **real DOS code** consumes our GETDPB + DSKIO + dir/FAT
      — the organic evidence the Tier-0/1 differential could only approximate.
- [ ] **2-Tier2-c — regression.** Host-unit-test the sector-0 read + handoff setup;
      pin the `A>` screen in `disk_probe_provider_dosboot.py`.

**Charter note.** This raises the README's loader-stub charter toward "real MSX
BASIC" on the disk axis. That is the intended scope of Phase 2 — a conscious step
up, kept narrow to the disk/file story so it stays validatable.

### Phase 1 close-out — owed oracles (polish, non-blocking)
- [x] `basic_probe_clear.py` — CLEAR oracle done: the `<memory-top>` write to
      HIMEM (`$FC4A`) is byte-identical to the Philips VG-8020 reference, and all
      four syntax forms (`CLEAR`, `CLEAR n`, `CLEAR ,himem`, `CLEAR n,himem`)
      parse + continue the line. String-heap sysvars stay unmanaged by design
      (no heap in Phase 1). ALL PASS.
- [x] `USR` `DAC`/`VALTYP` calling-convention oracle done (`basic_probe_usr.py`,
      ALL PASS): the reference passes an integer USR argument in `DAC+2..3` (16-bit
      LE at offset 2 of the 8-byte DAC `$F7F6`), sets `VALTYP` (`$F663`) `=$02`, and
      leaves `HL`→DAC base; zerobas passes the argument directly in `HL` and leaves
      DAC/VALTYP untouched — the own-design integer-only divergence is now measured,
      not assumed.

Everything else for the committed target is done; the detailed done-record follows.

## Done — Phase 1 (loader-stub BASIC)

Complete and oracle-validated; kept below as the provenance / divergence record
(each item names where it lives and how it was validated). The typical loader
stub this supports: `CLEAR …,&Hxxxx : SCREEN n : BLOAD"…",R` or
`DEFUSR=&Hxxxx : BLOAD"…",R : A=USR(0)`.

### Statements
- [x] `CLEAR [strings][,himem]` — nearly every stub sets memory top before `BLOAD`
      (basic/clear.asm: full syntax parses; string-space accepted+ignored, himem
      recorded to HIMEM `$FC4A`. Oracle `basic_probe_clear.py` ALL PASS; see Phase-1 close-out above.)
- [x] `DEF USR[n]=addr` + `USR[n](x)` function — the non-`,R` jump into loaded code
      (basic/usr.asm: vectors in USRTAB `$F39A`; crunch byte-identical. USR calling
      convention is own-design integer-only — DAC/VALTYP convention now oracle-measured,
      `basic_probe_usr.py` ALL PASS; see Phase-1 close-out above.)
- [x] `CLOAD ["filename"]` — load a BASIC program from cassette; needed when a stub
      chain-loads a BASIC payload rather than a binary (complement to `BLOAD"CAS:"`)
      (basic/cload.asm: CLOAD=$9B / LOAD=$B5 crunch byte-identical; reads the $D3
      tokenised-BASIC tape image into the stored-program area at TXTBASE, relinks,
      makes it the current program. Optional filename parsed+ignored — own-design,
      no tape file catalogue. On-device functional load WORKS — the earlier
      in-harness hang was a `ctp_line` link-word register clobber (not a tape
      framing bug), now fixed; see the tape-parity section above. Validated by
      `basic_probe_cload_ondevice.py` ALL PASS, plus the reference-load format oracle.)
- [x] `LOAD "CAS:filename"` — MSX-BASIC unified tape-load form; shares cassette I/O
      path with `CLOAD` but uses the `OPEN`-style filename syntax
      (same basic/cload.asm path as CLOAD; LOAD=$B5, "CAS:" device parsed, filename
      ignored. Same zerobas-tape `$00`-run device-half blocker as CLOAD.)
- [x] `PRINT` (+ `;` `,` separators, string literals, `TAB`) — wire up the existing token
      (basic/print.asm: numeric + string-literal items, `;`/`,` zones, `?` abbrev;
      crunch byte-identical, output verified in openMSX. `TAB(`/`SPC(` + string
      vars/`CHR$` still to do — need the Phase-3 string engine.)
- [x] `ON expr GOTO/GOSUB` — `branch_lineno` extended with comma-list loop; `ex_on`/`eon_seek_nth` handler added; all 7 functional probes (A=1..N, N=0 fallthrough, N>count fallthrough) pass
- [x] `SCREEN`, `COLOR`, `CLS`, `KEY OFF`, `WIDTH` — pre-handoff screen setup (thin BIOS/VDP wrappers)
      (basic/screen.asm: thin wrappers over CHGMOD/CHGCLR/CLS/ERAFNK/DSPFNK; new `OFF`
      token $EB added; crunch byte-identical incl. all 7 verbs; 9/9 functional probes
      pass `basic_probe_screen.py`. Divergences: SCREEN's extra args evaluated+ignored;
      COLOR doesn't repaint drawn text; KEY only does OFF/ON, `KEY n,"str"`/`KEY LIST`
      error — all Phase-3 scope.)

### Expressions / variables
- [x] Multi-character variable names — single-letter only is a hard wall
      (basic/vars.asm: 2 significant chars, key store; crunch byte-identical incl.
      digit-in-name; 2-char round-trip verified in openMSX)
- [x] `/`, `\`, `MOD`, and `AND`/`OR`/`NOT`/`XOR` — address / poke math
      (basic/expr.asm: full precedence ladder; crunch byte-identical, all ops verified
      in openMSX. `/` is integer + division is unsigned — documented divergences from
      MSX signed/float arithmetic; div-by-zero → 0. `^` still deferred to Phase 3.)
- [x] `&O` / `&B` literals — `&O` octal now emitted + evaluated; `&B` descoped
      (basic/interp.asm: `tk_hex` generalised to dispatch `&H`/`&O` on a radix
      (16/8) + token ($0C/$0B) pair; `&O` crunches byte-identical to the VG-8020
      as `$0B,<value16 LE>`, full `0..&HFFFF`; `ev_f` decodes `$0B` like `$0C`;
      `detok` already rendered `&O`. Oracle showed the reference has NO `&B`
      binary token — it copies `&B…` verbatim as ASCII — so `&B` is a documented
      own-design descope (kept verbatim, byte-identical to the reference; marked
      quarantined in basic/PROVENANCE.md), not a fabricated token. Validated:
      crunch + 4 control-flow/loops/data/statements regressions ALL PASS;
      functional `&o17`→15, `&o12`→10, `&o400`→256, `&o177777`→65535 in openMSX.)
- [x] `VARPTR`, `VPOKE`/`VPEEK`/`BASE`, `INP`/`OUT` — common in pokes
      (basic/vdpio.asm: VPOKE/OUT statement handlers; basic/expr.asm: VPEEK/INP/
      VARPTR/BASE function factors. Tokens oracle-confirmed byte-identical via
      basic_probe_crunch.py: VPOKE=$C6, OUT=$9C, VPEEK=$FF$98, INP=$FF$90,
      VARPTR=$E7, BASE=$C9 (cross-checks MSX2 TH Table 2.20). VPOKE/VPEEK use
      WRTVRM $004D / RDVRM $004A; OUT/INP do raw Z80 `out (c),a` / `in a,(c)`.
      detok renders all six (table-driven, no new render code). Functional
      `basic_probe_vdpio.py` 6/6 PASS. Divergences: VARPTR returns zerobas's OWN
      variable-table value-cell address (its table layout is its own design, not
      the reference's variable-area map) — valid+writable, sufficient for loader
      pokes; BASE is descoped — argument parsed+evaluated but BASE(n) returns 0
      and sets ERRMARK (reproducing the reference's per-mode VDP table-base map
      would need a forbidden source). Both quarantined in basic/PROVENANCE.md.)
- [x] String literals / variables *enough for `PRINT`* (full string engine is Phase 3)
      (basic/strvar.asm + basic/vars.asm: a `$`-suffixed name is a string variable
      with its own minimal inline store [name0][name1][len][bytes:STRMAX=32]; LET
      assigns a `"literal"` or copies another string var (A$=B$); PRINT emits a
      string var's value, incl. alongside literals (PRINT "X=";A$). Oracle-confirmed
      `$` is part of the name — NO special string token; crunch already byte-identical
      (`a$="hi"` → `41 24 EF 22 68 69 22`). Own-design VALTYP/STRPTR value-type notion.
      6/6 functional probes pass basic_probe_strvar.py. NOT built (Phase 3): concat `+`,
      string functions (LEN/MID$/CHR$/…), string arrays/DIM, string DATA — all descoped.)

### Usability
- [x] `LIST` — display the stored program, de-tokenised
      (basic/list.asm: `ex_list` walks the line-link chain; `detok` is the reverse
      of the tokeniser — keyword (`detok_kw`/`detok_kw2`), operator, int/`&H`/`&O`,
      line-ref, string/REM/DATA verbatim, `:`ELSE / `'` folds. No new token; reuses
      `div10`/CHPUT. 8/8 functional probes pass `basic_probe_list.py` (VRAM screen
      decode); crunch + all regression probes still pass.)
- [x] ✅ **`LIST <range>` — LANDED 2026-08-02, D-LSTRNG.** `LIST n`, `LIST n-m`,
      `LIST n-`, `LIST -m` all implemented; the argument is no longer ignored.
      Spec [`docs/spec-basic-listrange.md`](docs/spec-basic-listrange.md),
      measurement
      [`docs/listrange-msx1-characterization.md`](docs/listrange-msx1-characterization.md).
      🔴 **`DELETE`'s RANGE RULES DO NOT TRANSFER, AND FIVE OF THE TWENTY MEASURED
      SHAPES WOULD HAVE BEEN WRONG IF THEY HAD BEEN ASSUMED TO.** D-DELETE
      measured, one week earlier with the same grammar and the same instrument,
      that the high end must name a stored line exactly, that a reversed range is
      ERR 5, and that an absent number is 0 on either end. LIST has **none** of
      those: `LIST 20-35` lists two lines, `LIST 30-20` lists nothing with ERR 0,
      and — sharpest — **an absent HIGH end is 65535**, so `LIST 20-` lists to the
      end of the program where `DELETE 20-` means `20-0` and raises.
      🔴 **A LATENT BUG THE FOURTH `LE_OP` EXPOSED**: the lineedit tenant selector
      read `dec a / jp nz,le_delrange` — *"anything that is not 1 is a delrange"* —
      so adding `LE_OP_LSTRANGE` would have routed `LIST` into `le_delrange` and
      **deleted the lines it was asked to print**. Now an explicit ladder.
      🔴 **`list_walk` HAS THREE CALLERS**: `ascii_save` and `cas_ascii_save` drive
      the same walk, so a `LIST` range had to be stopped from leaking into
      `SAVE",A"` (a `list_all` entry does it). Knife K6a proved a one-line
      regression there passes the dead-code gate AND the whole 34-row battery —
      the new `list 20` in `disk_probe_save_ascii.py` is the only thing that sees
      it. Cost 68 B of main page 1 (82 → **14 B free**); a fully resident design
      was measured at ~128 B and never fit. `.` excepted — its own item below.
- [x] `CONT`, Ctrl-STOP / break handling
      (basic/program.asm: the RUN loop polls BIOS `BREAKX` ($00B7) between
      statements/lines and on every FOR/NEXT iteration; a press branches to
      `do_break`, which saves the resume state and prints `break in <line>`. The
      `STOP` statement (`ex_stop`) records resume = the statement after STOP, then
      `do_break`; `CONT` (`ex_cont`) restores `CURLINE`/`RESUMEPTR` and re-enters
      the run loop via the existing `RESUMEFLAG` mid-line resume path. `CONTVALID`
      is cleared at RUN entry, on `store_line` (edit), and on `NEW`, so CONT after
      a clean/STOP-less completion or an edit gives `can't continue` (ERRMARK $C9).
      CONT token oracle-confirmed byte-identical via basic_probe_crunch.py
      (`cont`→$99, cross-checks MSX2 TH Table 2.20); BREAKX oracle-confirmed on
      C-BIOS_MSX1 (bios_probe_breakx.py — CF clear when not pressed, so no
      false-breaks). Functional `basic_probe_cont.py` 7/7 PASS on C-BIOS_MSX1:
      STOP halts, STOP→CONT resumes incl. across a line boundary, all three
      can't-continue cases, and a real Ctrl-STOP keyboard-matrix press breaking an
      infinite loop back to the REPL. Divergences: the resume-state RAM layout
      (CONTLINE/CONTPTR/CONTVALID) and lowercase `break in`/`can't continue`
      wording are own-design — zerobas's run loop is its own design, not the
      reference's CONTXT/OLDLIN sysvars — both quarantined in basic/PROVENANCE.md.)

## Phase 3+ — full MSX1 BASIC (active charter)

**Precondition solved — BASIC ROM space (the C-BIOS repack arc, ✅ 2026-07-10).** The
page-1 `basic.rom` was byte-full at 16 KB, so any Phase-3 feature would have hit a hard
wall. The repack arc ([`docs/spec-cbios-repack-tooling.md`](docs/spec-cbios-repack-tooling.md))
broke it: dropping C-BIOS's dead ROM-BASIC placeholder frees `$2812–$3FFF` in page 0,
contiguous below page 1, so the relocated BASIC grows to a **`$2812–$7FFF` ≈ 21.5 KB**
window (+37 %). Ships as one merged 32 KB main ROM
([`zerobas-main-eu.ips`](zerobas-main-eu.ips)/`.bps`, boots end to end via `make
repack-boot`) with the firewall proven in
[`docs/cbios-repack-provenance.md`](docs/cbios-repack-provenance.md). Shipping `basic.rom`
+ the page-1/tape patches are untouched (`ROM_BASE` defaults to `$4000`); the grown image
is the reloc build. Non-EU variants (br/jp) are a documented later add.

Beyond Phase 2's disk axis — the rest of "real MSX BASIC." **Charter raised
2026-07-17 from loader-stub to faithful, full MSX1 BASIC** (see the banner in
[`README.md`](README.md) and [`MISSION.md`](MISSION.md)); this section is the
**active work-face**, no longer aspirational. Several arcs have **concluded on
main** — floating point (F1+F2+F3), the string engine, arrays/`DIM`, math pack,
console `INPUT`, error handling, `SOUND`/`PLAY`/`BEEP`, D-F2-2 int-arg coercion —
each with a standing acceptance gate. The remaining unchecked items below are the
open work; the disk/file story (`OPEN`/`CLOSE`/`PRINT#`/…) already landed in
**Phase 2** above.

- [x] **Floating point** — **ARC CONCLUDED** (F1+F2+F3 all landed on main;
      `%`/`!`/`#` typed vars + `DEFINT/DEFSNG/DEFDBL/DEFSTR` shipped, commits
      a1e77d3/2a7c1ce). Standing gate `make float-acceptance`.
      ([`docs/spec-basic-float-core.md`](docs/spec-basic-float-core.md), signed off
      2026-07-11): three slices, F1 literals+PRINT → F2 arithmetic+relationals+
      signed-int migration → F3 typed variables (`%`/`!`/`#`, unsuffixed=double).
      **F1 DONE 2026-07-11** (S1–S3, commits 223da0f/506381c/…): decimal float
      literals crunch to the real `$1D` (single, 4 B) / `$1F` (double, 8 B) BCD
      tokens byte-identically vs the VG-8020 — **decimal ≥ 32768 finally correct**
      (the old `$1C` wrap divergence retired) — and PRINT renders them
      reference-identically (fixed vs `E±nn` at dec_exp ∈ [-1,14]; `E` for BOTH
      precisions on this MSX1 reference). Oracle-pinned quirks reproduced: half-up
      rounding with the single-precision NON-renormalising carry (`9999995!` →
      1000000), suffix-after-exponent left unconsumed, `1e-65` underflow-to-zero
      with mantissa retained, crunch-time `overflow` rejection (own lowercase
      wording, D-F1-1). New `basic/float.asm` + repack-gated hooks; RAM `$F01A+`;
      lean `basic.rom` byte-identical. Interim seams (documented, F2/F3 resolve):
      no float arithmetic (`flt_guard` → ERRMARK, D-F1-3); a float in an int
      context rounds half-up into the −32768..65535 ADDRESS domain, outside → 0
      silently (D-F1-2 — the range widened in F1 review after `POKE 40000,n` /
      `HEX$(65535)` regressed under a strict-int16 cap); `LET` stores the rounded
      int. Standing gate **`make float-acceptance`** (LITERALS + FORMAT halves,
      60+ cases each) + host `tests/test_float.py`; spec §9 holds the full pinned
      contract; provenance `basic/PROVENANCE.md` → "Phase 3: math float pack, F1".
      Window after F1: 1844 B page-0 + 160 B tail ≈ 2.0 KB for F2+F3 (tight; next
      repack tranche is the fallback). Still out of scope (arc §1):
      `DEFINT/DEFSNG/DEFDBL/DEFSTR`, `^` + math functions, float
      `VAL`/`STR$`/`INPUT`/`FOR`, `MKS$/MKD$/CVS/CVD`, float `PRINT USING`.
      **F2 DONE 2026-07-11** (S2+S3, commits 781348f/dee70a9): `+ - * /`, the six
      relationals, promotion, and the **D-C signed-int migration** (`/` real
      division always; `\`/`MOD` MSX-signed; div-by-zero + Overflow are real
      statement aborts, lowercase wording D-F2-1) — **reference-identical,
      167/167** differential cases (spec §10 holds the full pinned contract).
      Headline oracle findings: ALL float arithmetic is DOUBLE (single =
      storage-only); guard-digit half-up rounding; PRE-normalisation
      overflow walls; float→int conversion TRUNCATES in two exclusive-bounds
      domains (F1's half-up `flt_to_int16` corrected); `-32768\-1` → +32768
      promoted; IF truthiness float-aware (§10.4a). New `basic/float-arith.asm`
      (unpacked-BCD 14+guard core) + FPERR abort wiring; the ARITH half joined
      `make float-acceptance`. Unblocking the window took the **D5 revision**
      (tape body `$3A72`→`$09EE`, all-variant gap-1 fill — flagged for user
      review; full tape battery re-run green). Interim seams: `LET` of a float
      TRUNCATES to int16 (F3 resolves); D-F2-2 = `OUT` + unwired int-arg
      statements/functions (e.g. `PEEK(100000.)`) still on the silent eager
      conversion. **Window now FULL** (2 B page-0 + 29 B tail); F3 needs a
      space lever — see the spec's D-G addendum (multi-region image / next
      repack tranche / heap-first).
      **F3 DONE (arc CONCLUDED)** — typed numeric variables (variable-width store,
      `%`/`!`/`#` suffixes, commit a1e77d3) and `DEFINT/DEFSNG/DEFDBL/DEFSTR`
      per-letter default types (`deftbl_lookup`, commit 2a7c1ce); `LET` of a float
      now stores at the variable's declared type (the F2 int16-truncate seam
      resolved). The `^`/math-functions and D-F2-2 int-arg items in the two lines
      above **also shipped** — see their own checkboxes below. Still genuinely
      deferred: float `MKS$/MKD$/CVS/CVD`, float-only `PRINT USING` specs. Spec §11
      (typed vars); provenance `basic/PROVENANCE.md` → "Phase 3: … F3".
- [x] **Full string engine** — **ARC CONCLUDED** (every string SURFACE form landed;
      standing gate `make string-acceptance`). **core + comparison landed 2026-07-10** (the first Phase-3
      feature and its follow-on): `+` concat + `LEN ASC VAL CHR$ STR$ LEFT$ RIGHT$ MID$`,
      then the six **relational operators** on strings (`=`/`<>`/`<`/`>`/`<=`/`>=` →
      -1/0, with a statement-level `type mismatch` abort) — all in the repack build
      (own-design temp ring + STRMAX clamp, no heap/GC; integer-only VAL). Specs
      [`docs/spec-basic-string-engine.md`](docs/spec-basic-string-engine.md) +
      [`docs/spec-basic-string-compare.md`](docs/spec-basic-string-compare.md), provenance
      [`basic/PROVENANCE.md`](basic/PROVENANCE.md) → "Phase 3: string engine" / "string
      comparison", gate `make string-acceptance` (crunch + execute + compare). **String
      functions slice DONE 2026-07-10** (S1–S3, commits d96dc67/6c46d2b/…): `INSTR HEX$ OCT$
      STRING$ SPACE$` — three integration shapes ($FF-prefixed HEX$/OCT$/SPACE$; single-byte
      STRING$ $E3 / INSTR $E5); spec [`docs/spec-basic-string-functions.md`](docs/spec-basic-string-functions.md),
      provenance `basic/PROVENANCE.md` → "Phase 3: string functions"; `string-acceptance` gained
      a fourth **functions** half (the execute+oracle gate caught two bugs the unit tests
      missed). **INKEY$ slice DONE 2026-07-10** (S1–S3, commits ee65487/dcac69d/…): the first
      keyboard-reading string verb — non-blocking single sample (empty / 1-char) via published
      BIOS `CHSNS`+`CHGET`; single-byte token `$EC`; temp-ring result; spec
      [`docs/spec-basic-inkey.md`](docs/spec-basic-inkey.md), provenance `basic/PROVENANCE.md` →
      "Phase 3: INKEY$"; `string-acceptance` gained a fifth **inkey** half (the first
      keyboard-injection acceptance; the live gate caught a `PRINT INKEY$`→type-mismatch
      `exp_loop` gap). **MID$-statement slice DONE 2026-07-10** (S1–S3, commits 6d88037/c915595/…):
      the assignment form `MID$(A$,n[,m])=B$` — overwrite a substring of A$ in place (`LEN(A$)`
      invariant, truncate-to-fit); zerobas's first lvalue-into-string-var path + first
      `$FF`-token-starting-a-statement; spec [`docs/spec-basic-mid-statement.md`](docs/spec-basic-mid-statement.md),
      provenance `basic/PROVENANCE.md` → "Phase 3: MID$ statement"; `string-acceptance` gained a
      sixth **mid-stmt** half + a host unit-test (`tests/test_mid_stmt.py`). Range errors →
      `syntax error` (no "Illegal function call", documented D-3 divergence). **Unparenthesized
      `PRINT A$<5` slice DONE 2026-07-11** (S1–S3, commits c3b626e/3c2137a/…): the bare comparison
      as a top-level PRINT item now works across all three string leads (var/literal/function +
      concat) — `exp_loop`'s peek-then-reparse dispatch (`relop_peek` + the `exp_strvar`/
      `exp_maybe_strfn` gates); `PRINT A$<5` aborts with `type mismatch`, printing nothing; spec
      [`docs/spec-basic-print-unparen-compare.md`](docs/spec-basic-print-unparen-compare.md),
      provenance → "Phase 3: string comparison" PRINT-lead subsection. **Console INPUT / LINE INPUT
      slice DONE 2026-07-11** (S1–S3, commits 50c231f/d362551/…): the keyboard forms
      `INPUT ["prompt"{;|,}] var[,var…]` and `LINE INPUT ["prompt";] A$` — fills the console stub
      the file `INPUT#`/`LINE INPUT#` forms left (`jp nz,stmt_error ; console INPUT = Phase 3`); the
      biggest missing interactivity primitive. Almost entirely composition — re-points the shipped
      `read_into_strscr` splitter at a new `linebuf_getbyte` source (shares the file forms' field
      split / STRMAX clamp / STRSCR); only new code is that vector, the strict `input_num_field`
      int16 validator, the prompt/var-list driver, and the D-2 re-prompt loop. Own lowercase
      `?redo from start` / `?extra ignored` (D-2 divergence). New `basic/input.asm`; standalone gate
      `make input-acceptance` (8 cases, keyboard-driven, reference-lock + zerobas==reference) + host
      `tests/test_input.py` (29 cases); spec [`docs/spec-basic-input.md`](docs/spec-basic-input.md),
      provenance `basic/PROVENANCE.md` → "Phase 3: console INPUT / LINE INPUT". Harness fix in
      `omsx_run.py` (`type --` so a negative-number response types verbatim). **Deferred items
      since RESOLVED by the arrays arc** (2026-07-17, see the Arrays + `DIM` entry below): the
      **real heap + descriptor model** (slice-4a compacting string heap), **string arrays/`DIM`**
      (slice 3), and **STRMAX→255** (slice-4a) all landed. **Still genuinely deferred:** floats in
      `VAL`/`STR$`, `INPUT$(n)` (no-echo n-key keyboard function), numeric `INPUT#` (out of MSX1
      charter) — tracked under the **I/O** item below.
- [x] **Arrays + `DIM`** (numeric and string, multi-dimensional) — **ARC CONCLUDED 2026-07-17** (all slices 1–4c shipped; faithful unified variable area). **slice 1 DONE
      2026-07-15** (numeric arrays: `DIM`, multi-dim, subscript rvalue/lvalue, auto-
      dim-to-10, base 0, `Subscript out of range`/`Illegal function call`/`Redimensioned
      array`/`Out of memory`). Dynamic-allocator model (real MSX `ARYTAB`→ceiling
      bounded by HIMEM); the array engine is a **sub-ROM page-0 tenant** (the first
      non-leaf feature to be split glue-in-main + pure-RAM-leaf-tenant — see
      [`docs/subrom-tenant-playbook.md`](docs/subrom-tenant-playbook.md)). Gate `make
      array-acceptance` (23 cases + adversarial regression); spec
      [`docs/spec-basic-arrays.md`](docs/spec-basic-arrays.md). `OPTION BASE` dropped
      (unsupported on MSX1). **Slice 2 = `ERASE` DONE 2026-07-15** (`ERASE
      A[,B%...]`; frees arrays → revert-to-undeclared + clean re-`DIM`; two-tier
      error surface — `syntax error` for malformed/paren forms, `Illegal function
      call` for an undeclared name; type-scoped; tenant `op=ERASE` compacts the
      descriptor list). Gate now `array-acceptance` **52 cases**; spec
      [`docs/spec-basic-arrays-slice2-erase.md`](docs/spec-basic-arrays-slice2-erase.md).
      Adversarial review caught F1 (`ERASE A$` freed the numeric `A` — `$` key
      collides with default-double at type 8; fixed via `var_str_type`→type-1).
      **Slice 3 = string arrays DONE**, **slice 4a = string HEAP (compacting,
      STRMAX→255) DONE 2026-07-17**, **slice 4b = numeric SCALAR relocation
      DONE 2026-07-17** (repack build only: numeric scalars move out of the
      fixed `VARTAB $E1C0..$E240` pool into the real-MSX contiguous chain
      `program text → scalars → arrays → free → string heap`, sharing arrays'
      own insert-and-shift/`FRETOP` collision/GC-once-retry mechanism; new
      `ARYTAB` live cell; fold into the `SUBROM_IDX_ARY` tenant as new
      `ARY_OP` codes 4/5 — no new sub-ROM leaf. `make array-acceptance`
      **127/127**; net **+64 B** main-ROM delta freed; lean build untouched.
      Spec [`docs/spec-basic-arrays-slice4b-scalar-reloc.md`](docs/spec-basic-arrays-slice4b-scalar-reloc.md)).
      **Slice 4c = string-SCALAR unification DONE 2026-07-17** (commits
      6d60540 impl → eeb9a8a Makefile SUB_PARTS fix → ea26bca gate/doc):
      string scalars relocated out of the fixed `STRTAB $E240..$E268` pool into
      the SAME unified variable chain — string find/alloc IS numeric find/alloc
      with type=1 once `scv_find`/`scv_alloc` stride routes through the slice-3
      `elsize_from_type` (type 1 → 3-byte `[len][ptr]` descriptor); GC root walk
      `sg_walk_strtab` → `sg_walk_scalars` (visit type==1 at descriptor entry+3);
      `str_get_key`/`str_set_key` → thin ARY_OP 4/5 glue; edit now clears ALL
      vars (resolves the 4b interim caveat). H1 hazard (fresh string STORE shifts
      arrays → stale SOURCE descriptor, `A$=S$(0)`) fixed via a temp-descriptor-
      stack source snapshot. `make array-acceptance` **138/138**; lean byte-
      identical; 9 B low / 19 B page-1 free. Spec
      [`docs/spec-basic-arrays-slice4c-string-scalar-unification.md`](docs/spec-basic-arrays-slice4c-string-scalar-unification.md).
      **🏁 The arrays/DIM arc is CONCLUDED — the faithful unified variable area is
      reached; no fixed variable pool remains.** Two follow-ups **SHIPPED
      2026-07-17** (commit d92c3da, +75fbe2b docs; Fable-reviewed clean):
      `VARPTR(A$)` now returns the string `[len][ptr]` descriptor (was a phantom
      numeric cell — `ev_f_varptr` passes type 1 for a `$` var); INPUT/LINE
      INPUT/INPUT# now surface the scalar-chain OOM as `Out of memory` (was a
      silent `""`; reused `check_expr_errors`/`_popbc`). Gate `array-acceptance`
      **140/140** + `input-acceptance` 16/16. **Array-element VARPTR SHIPPED
      2026-07-18** (spec [`docs/spec-basic-varptr-array-element.md`](docs/spec-basic-varptr-array-element.md)):
      `VARPTR(A(i))`/`VARPTR(S$(i))` now resolve the element address (was
      "syntax error") by reusing `ary_op0_resolve` (op=0 RESOLVE, auto-dim on
      read — the same resolver `ev_f_arr` uses) in `ev_f_varptr` when a `(`
      follows the name; numeric value-field / string `[len][ptr]` descriptor
      address, deferred `Subscript out of range`/`Illegal function call`/
      `syntax error` for bad subscripts — all reference-identical (VG-8020
      black-box-characterised). Repack-only; **self-funded** (the array branch's
      +23 B net against the old block was offset by collapsing `vptr_none`'s
      duplicated `)`-tail repack-only → net **+5 B** page-1, lean byte-frozen).
      Fable review clean (ship; 6 design claims + ~30-case injection battery);
      one byte-neutral follow-up (malformed-`)` VARPTR now surfaces the checked
      deferred syntax error, not a silent 0). Gate `array-acceptance` **150/150**.
      **`INPUT#` mid-statement FP-error ordering SHIPPED 2026-07-18** (the arc's
      last remaining faithfulness candidate): a mid-statement FP error in the
      channel-number expression (e.g. `INPUT#1+0*(1/0),B$`) now aborts BEFORE
      the field is read, matching the reference's abort-before-read ordering
      (was: swallowed until the post-read `check_expr_errors`, so the field got
      consumed anyway). Fix = a new `check_fperr_only` fall-in entry point in
      `check_expr_errors` (`basic/interp.asm`) — FPERR-only, not the full
      TMISMATCH+FPERR check, since a TMISMATCH channel expr already hard-zeroes
      to channel 0 and derails through `fch_valid` to `load error` (that
      pre-existing ordering is untouched); one 3-byte `call` site in
      `basic/files.asm`'s `ex_input`/`ex_line` shared channel-eval path
      (page-1 had only 3 B free, so a 3-byte call reusing the shared checker
      was required over a 7-byte inline check). Verified non-vacuous by hand
      (pre-fix: `B$` got the file's line despite the error; post-fix: `B$`
      stays empty) — this fix governs **ordering within the statement** (abort
      before vs after the field read), orthogonal to whether the RUN then
      continues. *(Wording corrected 2026-07-18, error-handling arc: an earlier
      version of this note claimed div-by-zero/Overflow are "non-fatal, the RUN
      continues to the next statement" — that was a MISREAD of zerobas's own
      pre-D-1 continue-bug as reference behaviour. Div-by-zero and Overflow are
      **fatal** on the reference (statement abort + RUN abort → `Ok`, matching
      the F2 entry above); the whole-RUN abort is fixed separately by the
      error-handling arc's S1 D-1. This ordering fix stays correct and
      non-vacuous after D-1: it decides whether the field was consumed before
      the abort.)*
      Gates green: `unit-test` 46/46, `input-acceptance` 16/16,
      `diskbasic-acceptance` 34/34 (`INPUT#` converged), `array-acceptance`
      150/150; lean `basic.rom` byte-identical (still pinned `e21f61fe…`).
      **Two adjacent channel-eval FP-error gaps SHIPPED 2026-07-18** (error-
      handling arc, spec §5.7): (gap 1) `INPUT#99999*99999,B$` — an out-of-int-
      range channel number now raises **Overflow** (`overflow in N`) instead of
      derailing to `load error`; (gap 2) `PRINT#1+0*(1/0),"X"` — the PRINT#
      channel `eval` now surfaces a deferred **Division-by-zero** (`division by
      zero in N`), the missing sibling of the INPUT# check above. Both fold into
      one shared low-region helper `eval_chan` (`basic/float-arith.asm`) = `eval`
      + numeric-channel `fac_to_int_addr` int-coercion + `check_fperr_only`, used
      by INPUT#/LINE INPUT# (`files.asm`) and PRINT# (`print.asm`); a TMISMATCH
      channel (`INPUT#A$`) skips the coercion and still derails to `load error`
      (verified unchanged). Folding INPUT#'s `eval`+`check_fperr_only` into one
      call **freed** page-1 (net 2→5 B free; low 20→3 B). This is the *targeted*
      channel-eval coercion; the broad D-F2-2 general float→int coercion stays a
      separate future item. Gates all green (unit/input/error/string/float/math/
      array-150/diskbasic-34-lean+repack); lean byte-identical.
      **SCOPED 2026-07-19 → [docs/spec-basic-df2-2-intarg-coercion.md] (DRAFT,
      awaiting sign-off).** Surface empirically pinned: ~8 divergent arg-sites in
      two groups — Group A (address domain: OUT/PEEK/INP, the fac_to_int_addr
      template already proven by POKE/VPOKE) and Group B (byte domain 0..255 via a
      shared get_byte_arg: STRING$×2/SPACE$/ON n/WIDTH). Already-faithful: POKE/
      VPOKE/HEX$/PRINT/DIM/subscript/TAB/SPC. Blocked by page-1 0 B free (funder =
      golf then format.asm eviction). Key open question Q1 = PEEK/INP FPERR
      propagation through a deferred boundary check.
- [x] **`^`** and the math functions
      `ABS SGN INT SQR SIN COS TAN ATN LOG EXP RND FIX CINT CSNG CDBL` — **MATH PACK
      ARC CONCLUDED.** `^`/`SIN`/`COS`/`TAN`/`ATN`/`LOG`/`EXP`/`RND` shipped as the
      transcendentals slice (documented-deviation framework, spec §13.1/§14.1/§15;
      page-1 sub-ROM tenant); `ABS`/`SGN`/`INT`/`SQR`/`FIX`/`CINT`/`CSNG`/`CDBL`
      shipped with the float pack. Standing gate `make math-acceptance`. Specs
      [`docs/spec-basic-math-pack.md`](docs/spec-basic-math-pack.md) +
      [`docs/spec-basic-mathpack-slice2.md`](docs/spec-basic-mathpack-slice2.md).
- [~] **I/O** — mostly shipped. ✅ console `INPUT` + `LINE INPUT` (DONE 2026-07-11,
      see the slice log above); ✅ `PRINT USING`; ✅ `GET`/`PUT`/`EOF`/`LOF` file I/O
      (Phase 2, random-access + sequential); ✅ `INPUT$(n,#f)` channel form; ✅ full
      tape verbs. **Still open:** `INPUT$(n)` (no-echo n-key *keyboard* function),
      numeric `INPUT#` (out of MSX1 charter), `LOC(#n)` (deferred — unclear CF-3300
      semantics, see Phase 2 §File-position).
- [~] **Graphics** (TMS9918, SCREEN 2) — arc live since 2026-07-21, spec
      [`docs/spec-basic-graphics.md`](docs/spec-basic-graphics.md) + per-slice addenda.
      ✅ G1 VDP floor · ✅ G2 `PSET`/`PRESET`/`POINT` · ✅ G3 `LINE` (+`,B`/`,BF`) ·
      ✅ G4 `CIRCLE` (aspect ellipse, arcs, spokes) · ✅ G5 `PAINT` ·
      ✅ **G6 `DRAW`** (2026-07-22, [`docs/spec-basic-graphics-g6.md`](docs/spec-basic-graphics-g6.md)):
      the full MML surface (`U D L R E F G H`, abs/rel `M`, `B`/`N`, `C`/`S`/`A`,
      `X <expr$>;`, `=<expr>;`), the measured scale arithmetic and its wraps, the
      angle's relative-only rotation, the S/A state that survives `RUN`, and the
      shared-`ATRBYT` colour rule (which also retro-fits `PSET`/`LINE`/`CIRCLE`/`PAINT`).
      Gate: `make graphics-acceptance` Phases K/L/M. ·
      ✅ **G7 sprites** (2026-07-22, [`docs/spec-basic-graphics-g7.md`](docs/spec-basic-graphics-g7.md)):
      `SPRITE$(n)=` and `A$=SPRITE$(n)` (8/32-byte entries, pad/truncate, the
      `& $3FFF` index wrap), `PUT SPRITE` (the `y,x,pattern,colour` entry, the
      early-clock rule for a negative x, coordinates stored mod 256, the ×4
      pattern scaling in 16×16, and "an omitted argument keeps the byte already
      there"), `SPRITE ON|OFF|STOP` as accepted no-ops, and **`SCREEN`'s
      sprite-size argument**, which used to be evaluated and discarded — including
      the mode-set init and the size's persistence across a later bare `SCREEN`.
      Gate: Phases N/O/P. Funded by the two-carve eviction
      [`docs/spec-eviction-g7-space.md`](docs/spec-eviction-g7-space.md).
      ✅ **G8 `VDP(n)` / `BASE(n)`** (2026-07-22, [`docs/spec-basic-graphics-g8.md`](docs/spec-basic-graphics-g8.md)):
      the VDP-register pseudo-array read AND write (`VDP(0..7)` = the RAM
      mirrors, `VDP(8)` = STATFL, the write reaching the chip), plus `BASE(n)=`
      with its per-slot value grain — **including the reference's SCREEN-1/2
      off-by-one**, where a BASE write reprograms R0..R6 from the NEXT group's
      table (signed-off D8-1, poison-tested). Also **retires the descoped
      `BASE(n)` stub**: our runtime's `$F3B3` table matches the reference byte
      for byte, so the read is an honest word fetch and a documented divergence
      goes away. Gate: Phase Q (state / grammar / the JIFFY-freeze teeth check).
      Funded from inside the arc — `circ_draw`'s spokes and `elg_draw`'s
      work-area writes folded into the tenant (~144 B), no outside eviction.
      **Still open:** `SCREEN 3` (multicolor, deferred) and the sprite COLLISION
      trap (`ON SPRITE GOSUB`), which belongs to the interrupt-trap item.
      **Residual found in passing (NOT graphics), since FIXED:** malformed
      statements raised a non-trappable abort instead of the reference's
      trappable ERR 2 — see the trap-class entry under Error handling below.
- [x] **Sound** (AY-3-8910) — `SOUND`✅, `PLAY` (MML)✅, `BEEP`✅ — **ARC CONCLUDED
      2026-07-21** (all repack-only, page-1 resident, direct-PSG, VG-8020-byte-faithful).
      `SOUND`/`PLAY`+live servicer landed earlier that day (commits baf…→f6bfe76); the
      **`BEEP` close-out slice** (spec [`docs/spec-basic-audio-beep.md`](docs/spec-basic-audio-beep.md))
      lands the last verb: single-byte token `$C0`, no args, one short tone-A blip
      (period 85, fixed vol 7, ~2-frame delay, then silence + mixer wiped to default
      `$b8`). Direct-PSG not `CALL $00C0` (C-BIOS's `$00C0` is silent on our runtime).
      Restore mixer is RECONSTRUCTED from the read-back I/O bits (`(read & $C0)|$38`),
      since R7's low 6 bits don't read back — same limitation SOUND's R7 path has;
      BEEP wipes a prior `SOUND 7` value and zeroes R8. Gates: `make beep-acceptance`
      (PSG-trace differential, 4 cases), `tests/test_beep.py` (host), crunch corpus.
      Adversarial pass caught a `beep_delay`-clobbers-`C` bug the differential was
      blind to (spec §5.2). Lean byte-identical; page-1 landmine (a downstream `jr`
      out of range) fixed with a ROM_BASE-conditional `jp` in `interp.asm`.
- [x] **Input devices** — the four device readers DONE 2026-07-23 (I1 + I2); the
      `KEY(n)` / `STRIG(n) ON/OFF/STOP` interrupt-trap surfaces stay with the item
      below. Spec [`docs/spec-basic-input-devices.md`](docs/spec-basic-input-devices.md).
      ✅ **I1 `STICK(n)` / `STRIG(n)`** (2026-07-23, commit b8a6a5b): the
      eight-way direction reader (0 = centred, 1..8 clockwise, an opposing pair
      cancelling to 0) and the 0/−1 trigger, as thin wrappers over the published
      BIOS entries `GTSTCK` `$00D5` / `GTTRIG` `$00D8` — which C-BIOS implements
      for real, keyboard row-8 scan *and* PSG joystick-port path, verified to
      match the VG-8020. Two-byte `$FF`-prefixed function tokens (`$FF $A2` /
      `$FF $A3`) on the existing `ev_f_ff` dispatch, so no statement token. The
      argument rule is truncate-toward-zero → int16 (`ERR 6` outside) then the
      device-domain check (`ERR 5` outside), reusing the D-F2-2 `get_byte_arg`
      machinery. Gate `make input-devices-acceptance` (31 cases) — whose
      load-bearing phase drives openMSX's `keymatrixdown`, since the REPL
      driver's KEYBUF injection bypasses the very matrix these functions scan
      and every other phase would pass equally well against a stubbed 0. That
      required a reusable harness addition (`omsx_repl` per-case matrix holds)
      the interrupt-trap arc will want for `ON KEY`/`ON STRIG`.
      Funded by an `ev_f_ff` dispatch golf (`cpir` set test, repack-only so the
      lean ROM stays byte-frozen) plus evicting **`BEEP`** to a page-0 sub-ROM
      tenant — chosen over two larger clean carves that are PLAY-servicer halves
      running from `H.TIMI`, since a `CALSLT` in the VBLANK handler is not worth
      50 B. Page-1 free 6 B → 17 B. **Residual fixed in passing:** a missing
      argument list (`PRINT PEEK`, `PEEK 100`, and the same for
      `VPEEK`/`INP`/`EOF`/`LOF`) evaluated silently to 0 where the reference
      raises `ERR 2` — a pre-existing divergence across the whole `ev_ff_arg`
      family, now deferred through `ev_f_empty`.
      ✅ **I2 `PDL(n)` / `PAD(n)`** (2026-07-23): real `GTPDL` `$00DE` (paddle)
      and `GTPAD` `$00DB` (touch panel) in the **zerobas-tape page-0 patch**
      (decision D-I-6 — C-BIOS shipped both as debug-*printing* stubs), plus two
      thin `ev_f_ff` wrappers (`$FF $A4` / `$FF $A5`; `PDL` 1..12, `PAD` 0..7).
      GTPDL times the paddle one-shot at exactly 36 T/iteration so a centred
      openMSX paddle lands on **128** (the rate itself is pinned, not just the
      polarity); GTPAD clocks the touch panel's NEC µPD7001 serial ADC and
      latches X/Y in the standard `PADX`/`PADY` work bytes. Two documented
      quirks reproduced **bug-for-bug** (user's call): X and Y read the same
      frame (the µPD7001 address phase is unrecoverable under our oracle, D-I-7),
      and the sticky contact-latch means an empty port 2's X/Y still report the
      last contacted reading. Funded by evicting the startup header
      (`show_title`) to a sub-ROM page-1 tenant (+71 B). Gate
      `make input-devices-acceptance` now **50 cases** (Phase D = the PDL matrix
      under paddle/touchpad in each port; Phase E = the PAD matrix under
      `arkanoidpad` — found only after trying every pluggable, since `touchpad`
      reads idle headless). Residual fixed in passing: `PDL("X")` reports the
      deferred type mismatch (ERR 13) rather than its ERR-5 domain check
      preempting it. **Still open:** `KEY(n)` and `STRIG(n) ON/OFF/STOP`, which
      are interrupt-trap surfaces and belong to the item below — the reference
      *accepts* `STRIG(1)ON`, so until that arc lands zerobas raises `ERR 2`
      there (documented divergence, decision D-I-5).
- [x] **Error handling** — `ON ERROR GOTO`, `RESUME`, `ERR`/`ERL`, `ERROR n`,
      numbered error messages — **ARC CLOSED 2026-07-19** (S1→S2a→S2b + `ERROR n`
      domain 1..255 + `ERR`-reset-on-`RESUME`, all landed on main; commits
      2551d1f→3496ce5). Full `RESUME`/`RESUME NEXT`/`RESUME <line>` family, trap
      branch, `SAVSTK`/`SAVTXT`. Standing gates `make error-acceptance` +
      `make error-trap-acceptance`. Specs
      [`docs/spec-basic-error-handling.md`](docs/spec-basic-error-handling.md) +
      the S2 packets. Known boundary: `ERROR 32768` → zerobas ERR 5 vs ref ERR 6
      (the D-F2-2 int-arg seam, documented).
      **Follow-up landed 2026-07-22 — statement syntax errors are TRAPPABLE.**
      `stmt_error` printed and aborted the RUN, so an `ON ERROR GOTO` program
      never saw a malformed statement; it now raises ERR 2 through
      `raise_error`, matching the VG-8020 for the whole class (bad `FOR` lvalue,
      bad `NEXT`, `SWAP`, unknown statement, bare word, juxtaposition, dangling
      `GOTO`), with the measured exceptions `FOR A$=` → ERR 13 and `NEXT 1` →
      ERR 2 (was ERR 1). 16 gated cases in `error-trap-acceptance`. The gap had
      been mis-reported as "silently accepted" — a probe artifact, since an
      aborting case never clears the screen and the tag regex then matched the
      echoed source line; `_outcome` in the graphics probe now detects aborts.
- [x] **Interrupt traps — ✅ ARC CONCLUDED 2026-07-26, all FIVE families landed and
      gated** (T1 `STOP`, T2 `STRIG`, T3 `KEY`, T4 `SPRITE`, T5 `INTERVAL`). Detail
      per slice below; the two later ones are recorded at the end of this item.
      ⚠️ It was declared concluded once at T4 and wasn't — `INTERVAL` turned out to
      be a fifth MSX1 family dropped on a false premise (see the reopening note
      below). `ON INTERVAL/KEY/SPRITE/STOP/STRIG GOSUB` + the arming
      statements (`INTERVAL/SPRITE/STOP ON/OFF/STOP`, `KEY(n)/STRIG(n) ON/OFF/STOP`).
      Closes the input-devices **D-I-5** handoff (`STRIG(n)/KEY(n) ON/OFF/STOP` → real,
      was documented-divergence ERR 2) and the graphics **D-G7-4** handoff (`SPRITE
      ON/OFF/STOP` no-op → real + `ON SPRITE GOSUB`). **Arc spec SIGNED OFF 2026-07-24**
      ([`docs/spec-basic-interrupt-traps.md`](docs/spec-basic-interrupt-traps.md)):
      slicing **T1→T2→T3→T4** by event-source mechanism (T1 core+INTERVAL → T2 STOP+STRIG
      → T3 KEY → T4 SPRITE). Reuse story: the `ON ERROR` trap-branch is the
      GOSUB-into-handler model, the PLAY servicer's H.TIMI hook is the per-frame poll
      seam, the input-devices matrix-hold harness is the gate. Own-design `ZTRAP` table
      in free VARTAB RAM (`$E1D1`, 18×3 B + interval counter); tri-state OFF/ON/STOP + a
      4th SERVICING state, re-enable-on-RETURN via a GSP-match service stack. **Byte
      budget is the dominant risk** — measured 2 B page-1 + 19 B page-0 low free; T1
      needs a ~70 B carve (funded by a `gosub_push` golf + evicting the INTERVAL parsers
      to a page-0 sub-ROM tenant).
      ✅ **T1 STOP LANDED** 2026-07-25 (4fef347): `ON STOP GOSUB` / `STOP ON|OFF|STOP`,
      the whole reusable skeleton (`ZTRAP`, the H.TIMI `event_poll` seam, `check_traps`,
      `set_state`, the RETURN re-enable), `make stop-trap-acceptance`. Spec
      [`docs/spec-traps-t1-stop-reslice.md`](docs/spec-traps-t1-stop-reslice.md).
      ✅ **T2 STRIG LANDED** 2026-07-25: `ON STRIG GOSUB <list>` (5 positional slots) +
      `STRIG(n) ON|OFF|STOP`, the first real **device** event source (`GTTRIG` edge
      detection in the VBLANK poll). **Closes half of D-I-5.** `make
      strig-trap-acceptance` — 25 cases / 51 assertions vs the VG-8020, including
      triggers 1..4 (a PSG-latch injection; openMSX has no joystick-button command).
      One deliberate deviation: a 6th handler slot raises a trappable ERR 2 where the
      reference crashes. Spec [`docs/spec-traps-t2-strig.md`](docs/spec-traps-t2-strig.md).
      **Note:** `INTERVAL` is MSX2 and out of charter, so it is NOT part of this arc —
      T3 = KEY, T4 = SPRITE remain. Page-1 free is down to 9 B, so **T3 needs a carve.**

      ✅ **T3 KEY LANDED** 2026-07-25: `ON KEY GOSUB <list>` (10 positional slots) +
      `KEY(n) ON|OFF|STOP`. **Closes the OTHER half of D-I-5, so D-I-5 is now fully
      closed.** KEY is a **delivery** trap, not an edge trap: it fires once per BIOS
      key-delivery — the initial make and every auto-repeat — and a trapped key is
      **diverted**, removed from the input stream before anything can read it. Neither
      published ISR hook can do that (both run *before* the keyboard scan), so the event
      source is a thin 5-byte C-BIOS seam, `H_ZKEY`
      ([`cbios-repack/key-trap-hook.patch`](cbios-repack/key-trap-hook.patch)), with all
      policy in [`basic/keytrap.asm`](basic/keytrap.asm). Auto-repeat is inherited from
      the host BIOS rather than replicated. `make key-trap-acceptance` — 28 cases /
      54 assertions vs the VG-8020. Spec
      [`docs/spec-traps-t3-key.md`](docs/spec-traps-t3-key.md).
      **Funding:** the BLOAD carve (page 1 9 B → 271 B) paid the page-1 half; the
      low-region half was paid by **promotion** — 74 B of boot-time-only sub-ROM
      plumbing moved up into the freed page 1
      ([`basic/subrom-boot.asm`](basic/subrom-boot.asm)), gated by the new
      [`tools/promote_scout.py`](tools/promote_scout.py). Walls now: low region 14 B
      free, page 1 62 B free.
      **The gate found a real, older, SHARED bug:** the ON…GOTO/GOSUB crunch in
      [`basic/tokenise.inc`](basic/tokenise.inc) abandoned the list at an EMPTY slot, so
      `ON KEY GOSUB 100,,600` (and T2's `ON STRIG GOSUB ,300`) died with a syntax error.
      Fixed repack-only — the 4 bytes overrun the byte-full lean cart, which keeps it.
      ~~**T4 = SPRITE is the only slice left in this arc.**~~
      🔴 **ARC REOPENED 2026-07-26 — `INTERVAL` is a FIFTH MSX1 trap family, and it
      was dropped on a FALSE PREMISE.** The 2026-07-24 finding "`INTERVAL` is MSX2,
      absent from MSX1" measured the right thing and drew the wrong conclusion:
      `INTERVAL ON` crunches to `FF 85 45 52 FF 94` (`INT` + literal `"ER"` + `VAL`)
      on both vendor ROMs because it is **not a keyword** — it is a reserved-word
      compound, the same shape as `MAXFILES` = `MAX`+`FILES`. It *works*: on the
      VG-8020 `ON INTERVAL=n GOSUB` + `INTERVAL ON` fires 16 / 33 / 8 times for
      n = 10 / 5 / 20 over ~160 jiffies (exact 1/n), `OFF`/`STOP` give 0, and `LIST`
      round-trips to `INTERVAL ON`. **"Absent from the keyword table" ≠ "absent from
      the language" — a crunch probe answers a tokenisation question, not a support
      question.** Happy consequence: **zerobas already crunches it byte-identically**
      (it has `INT` and `VAL`), so **T5 needs no token and no `kwtable` row** — only
      the parse + the `event_poll` counter stanza, both already specified in
      [`docs/spec-basic-interrupt-traps.md`](docs/spec-basic-interrupt-traps.md)
      §5/§6 (written for INTERVAL first, then orphaned). ~~**T5 is owed a packet.**~~

      ✅ **T4 SPRITE LANDED** 2026-07-26 (`85ac5f4`, cadence gate rebuilt `47f4999`):
      `ON SPRITE GOSUB` + `SPRITE ON|OFF|STOP`. **Closes the graphics D-G7-4
      handoff.** SPRITE is a **LEVEL** trap, one fire per frame — confirmed at the
      emulator level (300 latches over 300 frames) — and D-T-4 is to read `STATFL`.
      `make sprite-trap-acceptance` **123/123**. Spec
      [`docs/spec-traps-t4-sprite.md`](docs/spec-traps-t4-sprite.md).
      **The gate was wrong four times before the implementation was wrong once.**
      The original `F_cadence` measured the MAIN LOOP, not the trap: its "1.5
      jiffies/fire divergence" was the HANDLER'S OWN COST, and a handler taking
      >1 frame starves the main program completely — so the main program cannot be
      the instrument for a feature that can starve it. Rebuilt on emulator-counted
      fires. **A gate's DENOMINATOR must be measured, never computed by the thing
      under load.**

      ✅ **T5 INTERVAL LANDED** 2026-07-26 (`26f9251`): `ON INTERVAL=n GOSUB` +
      `INTERVAL ON|OFF|STOP`, **no token and no `kwtable` row needed** (the
      reserved-word compound above). `make interval-trap-acceptance` **149/149**.
      Spec [`docs/spec-traps-t5-interval.md`](docs/spec-traps-t5-interval.md).
      ⚠️ **It landed 14 B OVER the page-1 ceiling** (`f973e1c` corrected the
      as-built figure to 265 B): the SAVE-engine carve funded `TIME` *and* T5 —
      two of three, not three. The tree stayed red until the direct-mode
      control-flow slice reclaimed the bytes (`a5a3af2`; page-1 free now **8 B**).
      The overrun had hidden behind **warm-tree** builds reporting 55 B free —
      only `rm -rf build && make basic-reloc` measures the wall.
- [x] **`TIME` / `TIME=n` — ✅ LANDED 2026-07-26** (`1addfbc`), 81 B, gate
      `make time-acceptance` **105/105 both sides**. Retires the T3-era rule that
      banned `TIME` on the zerobas side of the acceptance harness.
      **Its gate surfaced the direct-mode `FOR` defect** that became
      [`docs/spec-basic-direct-ctrl.md`](docs/spec-basic-direct-ctrl.md): the write
      group shifted phase with a `FOR` pad, seven of eight phases errored, and the
      reduction **collapsed to one sample** while still printing a number — worse
      than no reduction. It now pads with statements instead.

      *Original entry, kept for the characterization record:* the software-clock
      pseudo-variable, standard MSX1
      BASIC and **was absent from zerobas entirely**: it is not in
      [`basic/kwtable.inc`](basic/kwtable.inc), so `TIME` parses as the *variable*
      `TI` and reads 0 forever, which makes `IF TIME-T<400 GOTO` an infinite loop —
      a **silent** divergence. Found as collateral during the T3 KEY slice
      (`20e04b4`); it is also why the acceptance harness still bans `TIME` on the
      zerobas side and sizes every observation window by iteration count.
      **Characterized 2026-07-26** against the VG-8020 — 45/45 assertions,
      [`probes/basic/basic_probe_time.py`](probes/basic/basic_probe_time.py):
      single-byte token `$CB`; the read is the **unsigned** word at `JIFFY`
      (`$FC9E`) promoted to a float (`A%=TIME` at 40000 → Overflow); the write uses
      the **house address-domain conversion zerobas already has** (`fac_to_int_addr`
      — wrap by −65536 above 32767, then truncate toward zero, ERR 6 outside
      −32768..65535); errors are ERR 13 / 24 / 6 / 2; the clock wraps mod 65536 with
      no error and its *rate* belongs to the host BIOS/VDP.
      Spec [`docs/spec-basic-time.md`](docs/spec-basic-time.md) — ~~awaiting
      sign-off; the one open decision is funding (~52–75 B, pure page 1, and page
      1 has 22 B free)~~ **signed off and implemented; funded by the SAVE
      write-engine carve** (+310 B page 1).
- [x] **Direct-mode control flow — ✅ DONE 2026-07-26**, spec + as-built
      [`docs/spec-basic-direct-ctrl.md`](docs/spec-basic-direct-ctrl.md), gate
      [`make direct-ctrl-acceptance`](Makefile) **40/40** vs the VG-8020
      (probe [`probes/basic/basic_probe_direct_ctrl.py`](probes/basic/basic_probe_direct_ctrl.py),
      boot-per-case, 6 groups). `FOR`/`NEXT`, `GOSUB`/`RETURN`, `GOTO`,
      `IF..THEN <line>` and `ON..GOTO` **typed at the prompt** — an execution
      MODE that had **zero** coverage: every earlier loop/trap/graphics gate runs
      its BASIC as a stored program + `RUN`.
      Two defects, and the reported one (`FORI=1TO7:NEXT` → `out of memory`) was
      the milder: `GSP`/`FSP` had exactly one init site (`run_program`), so before
      the first `RUN` they held power-on garbage (**D-DIR-1**); and
      `dispatch_line` ran a typed line with a bare `jp exec`, which walks
      statements but never services the deferred-transfer flags, so a direct
      `GOTO`/`IF..THEN`/`ON..GOTO` was a **silent no-op** (**D-DIR-2**). Fixing
      D-DIR-1 alone would have been *worse* than the bug — a loud ERR 7 traded for
      a `FOR` body silently running zero times.
      As built: a typed line executes as a **virtual line** (`dir_line`, a 4-byte
      **ROM** header whose two words overlap so the link doubles as the `$0000`
      end marker) through the real run loop, so no direct-mode special case exists
      anywhere in the loop; `DIRECTF` is **derived** at `rp_exec` from `CURLINE`'s
      high byte, never carried, because direct mode is a property of the line
      *being run* (a typed `GOSUB` into line 10 reports `Syntax error in 10`, the
      `RETURN` back into the typed line reports a bare `Syntax error` — measured);
      and the control-stack reset moved from `run_prog` into `clear_vars`, whose
      four call sites are exactly the four the reference resets on (cold boot,
      `RUN`, `NEW`, `CLEAR` — and a frame does **not** die at the next prompt).
      **DEFERRED (D-DIR-3):** interrupt traps still do not dispatch in direct
      mode. Before this slice no trap *could* fire at the prompt, and whether the
      reference fires them there is UNMEASURED — so the conservative answer is
      gated in at one RAM load rather than changed as a side effect. Spec §6 names
      the characterization that closes it.
- [x] **`get_byte_arg`'s reject RETURNS INTO ITS CALLER — `WIDTH 300` corrupts
      the screen.** ✅ **FIXED 2026-07-28** (see the LANDED block at the end of
      this item). MEASURED 2026-07-27, found as the control while debugging
      LOCATE's error rows. `get_byte_arg` rejects with `jp raise_error`, and the
      abort chain PRINTS AND RETURNS — consuming the caller's own `call
      get_byte_arg` frame and landing back inside the caller just past the call,
      with **A = the error code**. So `ex_width` does `ld (LINLEN),a` with A=5
      and re-inits the screen: on the current build `CLS:WIDTH 300` prints **no
      error at all** and leaves the display unusable (measured against the
      reference's clean `Illegal function call`). `WIDTH 99999` (ERR 6, via
      `check_fperr_only`) does the same.
      ⚠️ Scope is wider than WIDTH: `get_byte_arg`'s other callers are
      `STRING$`, `SPACE$` and `ON n`, and each needs checking for the same
      shape — the bug is in the CALL CONVENTION, not in WIDTH.
      LOCATE does not use it for exactly this reason (basic/missing.asm
      `loc_next` inlines the two-stage check at the handler's own stack depth,
      where the same two `jp`s abort correctly). Not fixed here: the fix is
      per-caller frame discipline across four statements, each with its own
      gate, which is a slice rather than a drive-by.
      📋 **RE-MEASURED + SPEC WRITTEN 2026-07-28, awaiting sign-off (S-AD-1..5)**:
      [`docs/spec-basic-abort-depth.md`](docs/spec-basic-abort-depth.md). Two
      things in the paragraph above are now known to be wrong.
      **(a) The scope is nine sites, not four** — `ev_ff_arg`
      (basic/expr.asm) calls the same leaf for `STICK`/`STRIG`/`PDL`/`PAD`, and
      `get_vram_arg`/`fac_to_int_addr` reach the same abort for
      `VPEEK`/`PEEK`/`INP`. Measured untrapped: `PRINT STICK(9)` prints the
      error **and ` 0`**, `PRINT VPEEK(-1)` **and ` 32`**,
      `PRINT "[";SPACE$(99999);"]"` prints **`overflow` twice**,
      `PRINT "[";STRING$(-1,65);"]"` the error **plus `syntax error` twice**.
      **(b) Per-caller frame discipline is the expensive fix.** The TRAP branch
      of the same routine already solves the general case in four bytes
      (`ld sp,(SAVSTK)`, interp.asm) and the abort branch simply does not do
      it; §4 of the spec takes that instead, at +7…+14 B, repack-only.
      ⚠️ **The standing D-F2-2 gate is structurally blind to all of it** —
      `basic_probe_intarg.py`'s 36 asserted rows each arm `ON ERROR GOTO` and
      read `ERR`, which selects the trap path, i.e. the one path that unwinds
      correctly. It is green and would stay green with every defect above
      present. ⚠️ So is a right-stripped screen scrape: `SPACE$(-1)`'s junk is
      a run of *spaces*, and read as "clean" until the row was re-run
      bracket-delimited. **This slice is ordered BEFORE D-MISS-2**, whose fix
      is four more calls into this same convention.
      ✅ **LANDED 2026-07-28 — `make abort-acceptance` 23/23, falsified 6/23.**
      **Four bytes**, one instruction: `ld sp,(SAVSTK)` at the top of
      `fre_abort_low` ([`basic/arrays.asm`](basic/arrays.asm)). The estimate of
      +7…+14 B assumed the message tail had to be restructured so the reset
      could follow the print; it does not — the printing routines push and pop
      *below* the new `SP` and never touch the word *at* it, so the existing
      tail-jumps `ret` straight to the anchored address, which in **both** modes
      IS the run loop's own normal exit (`run_prog` and `dl_cmd` each store
      `SAVSTK` immediately before entering the loop). ⚠️ **The budget named the
      wrong wall**: `arrays.asm` is LOW REGION, so the 4 B came out of the low
      region's 11 B (→ **7 B free**), not page 1 (unchanged at 44 B) —
      **D-MISS-2 must budget from 7 B.** Repack-only; lean `basic.rom`
      byte-identical, `LEAN_SHA256` unmoved.
      Both open sign-off questions were answered by MEASUREMENT, not argument:
      **S-AD-2** — the `boot_first` row (an error as the very first statement
      after a cold boot) passes, so `SAVSTK` needs no boot init and the 5 B held
      in reserve were not spent. **S-AD-3** — the page-0 sub-ROM tenant rows
      pass, but the falsification shows they pass **with and without** the fix:
      `ary_engine` raises `Subscript out of range` at handler depth and was
      never part of this defect, so those rows are CONTROLS (the reset does not
      BREAK the tenant path), not evidence it repaired one.
      **The falsification is the load-bearing number**: comment the instruction
      out, rebuild from clean (low region goes back to 11 B, so it really is out
      of the image) and the gate reads **6/23** — and the six survivors are
      exactly the handler-depth rows, where the abort was already correct.
      Regressions: `make intarg-acceptance` ALL PASS, `make unit-test` 53/53,
      `make missing-acceptance` **214/214**.
      ⚠️ **`missing-acceptance` went RED first, for the right reason** — its own
      stale-marker check fired: three rows recorded as expected-divergent
      (`d2-string-neg`, `d2-string-256`, `d2-space-neg`) now AGREE with the
      reference, so the expected-divergent count drops **20 → 17**. Note what
      that does and does not mean: `STRING$`/`SPACE$` always HAD their domain
      check (`get_byte_arg`); what diverged was the abort SHAPE. **No part of
      D-MISS-2 is implemented by this slice** — the four `d2-chr-*` and the
      `LEFT$`/`RIGHT$`/`MID$` rows stay marked.
      Also newly visible in the falsified run, worse than anything in the
      original table: `PRINT "[";STRIG(9);"]"` printed **`-21821`** — the
      statement carried on with uninitialised memory as its value.
- [ ] **The prompt does not open a fresh line** — MEASURED 2026-07-27, found
      while gating `TRON`. **The reference emits a newline before its prompt
      whenever the cursor is not at column 0; zerobas prints its prompt where
      the cursor stands.** `CLS:PRINT "A";` is the whole reproducer: the
      reference paints `A` and then `Ok` on the *next* row, zerobas paints
      `Azb>` on one. No word under test is involved.
      Latent until now because almost everything zerobas prints ends with a
      newline — it took `TRON`, whose decoration deliberately emits no newline
      of its own, to leave the cursor mid-row often enough to notice. The
      `missing` probe's screen readout strips a trailing prompt on both sides
      (it already claimed to drop the prompt; it only did so for a prompt alone
      on a row), so this does not block that gate.
      ⚠️ Fixing it changes the screen output of every gate whose expectations
      were recorded against the current prompt, so it is its own slice, not a
      drive-by. Related to the screen-editor REPL item below but independent of
      it — this is one conditional CRLF, not a rewrite.
- [ ] **Screen-editor REPL** — real MSX BASIC does not use a sequential prompt
      loop; Enter reads the *current cursor line from VRAM* (not a dedicated
      input buffer), so the user can cursor-up to any visible output, edit it
      in place, and re-enter it. Needs cursor-key handling and VDP line-readback.
      Our `repl.asm` is a deliberate simplification; full replacement is Phase 3.
- [ ] **Editor / program management** — `RENUM`, `AUTO`,
      `TRON`/`TROFF`, `SWAP`, `WAIT`, `FRE`, full `CLEAR` semantics (`ERASE`
      shipped 2026-07-15 with the arrays arc, slice 2; `DELETE <range>` shipped
      2026-08-02 with D-DELETE and **`LIST <range>` the same day with D-LSTRNG**,
      `.` excepted in both — its own item below).
      ⚠️ **THE PAGE-1 WALL IS NOW 14 B**, not the 82 B D-LSTRNG started from, and
      82 B was itself the post-carve figure. Any remaining item here needs a carve
      or an eviction before it needs a design.
      (`SWAP` itself is still unimplemented — `SWAP A,B` is a syntax error here,
      where the reference swaps. Its MALFORMED forms already match, via the
      trap-class fix below.)
      **All of these are now measured, not estimated** — see the keyword sweep
      item directly below.

- [ ] **Keyword-completeness gaps — the measured remainder of MSX1 BASIC.**
      **The coverage denominator now exists** (2026-07-26,
      [`docs/kwsweep-msx1-coverage.md`](docs/kwsweep-msx1-coverage.md), probe
      [`probes/basic/basic_probe_kwsweep.py`](probes/basic/basic_probe_kwsweep.py),
      `make kwsweep`): of **162** MSX1 reserved words, **124 tokenise** and
      **34 are genuinely absent** (38 lack a `kwtable.inc` entry; 3 of those —
      `DEFSNG`/`DEFDBL`/`DEFSTR` — work anyway via `DEF_TOKEN` + literal ASCII,
      and 1 is `INTERVAL`, which needs no token).
      **Why a sweep existed at all:** `TIME` and `TAB(` were both found *by
      accident*, six days apart, with the same silent shape — the word parses as
      an ordinary variable, nothing errors, the program computes the wrong
      answer. `TAB(` was worse: it had been written down as *"Already faithful
      (NO work)"* in
      [`docs/spec-basic-df2-2-intarg-coercion.md`](docs/spec-basic-df2-2-intarg-coercion.md)
      §1.2 because `PRINT TAB(99999)` raises ERR 6 on **both** sides — for
      structurally different reasons (absent `TAB(` ⇒ `TAB` is an *array*, and
      the subscript bound-check yields the same code). **The differential passed
      and the feature did not exist.** That §1.2 claim is doc debt and is
      corrected in this commit.
      - ✅ **SILENT-GAP (was 8) — THE CLASS IS EMPTY (2026-07-27).** The worst
        class: a wrong answer with no error, a live landmine in a user program.
        All eight are now implemented and gated —
        `EQV`/`IMP` (`ef098e9`, 156/156), `TAB(`/`SPC(`/`CSRLIN`/`POS`
        (`99c0f6d`, 67/67), `FRE`/`BIN$` (`2facfc0`, 83/83) — plus `TIME`
        (`2026-07-26`), which was the ninth and which the sweep picked up with
        no edit to the probe. **No MSX1 reserved word silently computes a wrong
        answer.** That was the keyword arc's exit criterion (D-KW-3).
      - ✅ **MISSING (6) — THE CLASS IS EMPTY (2026-07-28).** All five words plus
        D-MISS-1: `LOCATE` · `TRON` · `TROFF` · `MOTOR` landed 2026-07-27, and
        **`SWAP` landed 2026-07-28** once two clone collapses funded it (+45 B
        `fat_rand_*` onto the existing `fatprim_bounce`, +41 B the five TOTAL math
        calls onto one table — neither of them SWAP's own code). Gated by
        `make missing-acceptance` at **214/214 as recorded**.
        `DEF FN`/`FN` stays out — it is an arc, not a slice (D-MC-3).
      - **NO-ORACLE (5).** `MKI$` `MKS$` `MKD$` `CVS` `CVD` — the MK/CV family
        lives in Disk BASIC, so a **diskless** VG-8020 reference measures the
        absence of a disk ROM, not of a language feature. The probe routes these
        to `National_CF-3300`, which does not yet give a readable SCREEN-0
        capture under `omsx_repl`; until it does they report `NO-ORACLE` rather
        than answering from the wrong machine. Blocks nothing —
        `MKS$`/`MKD$`/`CVS`/`CVD` are already deferred under the float pack.
      - **18 crunch-only** — destructive (`DSKO$`, `IPL`), interactive (`AUTO`,
        `INPUT$(n)`), non-terminating (`WAIT`), printer-bound with the known
        unplugged-`LSTOUT` hang hazard (`LPRINT`, `LLIST`, `LPOS`, `LFILES`),
        disk-fixture-dependent (`COPY`, `SET`, `ATTR$`, `DSKI$`, `LOC`), or
        covered elsewhere (`INTERVAL` → the T5 slice probe). These are coverage
        holes **in the probe**, listed in its output with reasons rather than
        silently dropped.
      - ⚠️ **`INPUT$` is the one to watch:** it crunches *identically* to the
        reference (`INPUT` is a keyword and `$` follows), so layer 1 says
        "present" while support is untested — the exact `INTERVAL` shape. Open
        under the **I/O** item above; the sweep has **not** settled it.
      **Scope boundary:** reserved words only. Statement *option* surfaces
      (`SCREEN 3`, `KEY LIST`, argument forms of words that *are* present) are
      not covered — a word can be present and still wrong in its third argument.
      **✅ SLICED + COSTED 2026-07-27** —
      [`docs/decision-kwgaps-slicing.md`](docs/decision-kwgaps-slicing.md),
      **awaiting sign-off** (D-KW-1..3). The sweep was **re-pinned** against a
      clean-built HEAD first (`git=e9843c4`,
      `zerobas-main-eu.rom=05f43b…`→`4ea7a2…`): **every tally unchanged**, so the
      8/6/5 finding was not an artifact of the stale over-ceiling build. All 14
      reference tokens are now **oracle-measured** from Layer 1's own crunch diff
      (table in the coverage doc) rather than read off Table 2.20.
      ⚠️ **The funding premise in the line this replaces was stale AND wrong.**
      Page 1 is no longer 14 B over — it is **375 B free** (low region 5 B) after
      the FAT tenant-shim collapse (`6f8ac0f`, +367 B: thirteen byte-identical
      34 B shims onto one shared body), which answered D-KW-1 "carve first". More importantly the item is not blocked on *funding* but on
      **placement**: `sub.rom` has **≈8 KB free** (4509 B page-0 + 3497 B page-1)
      and `kwtable.inc` entries + leaf compute already live there, so the only
      number that matters per keyword is its **main-ROM dispatch glue** —
      and `exec_stmt` is a 67-entry linear `cp`/`jp z` chain charging **5 B per
      statement token before it does anything**. Recommended first slice:
      **`EQV`/`IMP` via a table-driven logical layer** — `ev_xor`/`ev_or`/`ev_and`
      are uniform at 34 B each (measured), so one generic 5-entry layer lands both
      words for **≈ 0 net bytes**.

      ✅ **Steps 1, 2 and 4 are DONE and the exit criterion is MET** — the
      SILENT-GAP class is empty (see above). Each slice was funded by collapsing
      a clone group it was itself a member of, and each one's calibration battery
      turned up pre-existing silent divergences nobody was looking for (two per
      slice, three slices running).

      **What remains of this arc, in order:**
      - **The MISSING class (6)** — ✅ **LANDED 2026-07-27 except `SWAP`.**
        `LOCATE` · `TRON`/`TROFF` · `MOTOR` + D-MISS-1 are in and gated
        (163/163 as recorded, 20 expected-divergent, every marker carrying a
        reason). Spec, as-built costs and the two places the spec turned out to
        be WRONG:
        [`docs/spec-basic-missing-class.md`](docs/spec-basic-missing-class.md).
        ✅ **`SWAP` LANDED 2026-07-28** — 183 B (re-measured from clean; the
        split had recorded 186 B), funded by two repack-only clone collapses and
        leaving 44 B banked (SWAP + its dispatch arm + the two operand guards =
        198 B against the 242 B the carves freed). **"Flipping the flag plus one probe line is the whole
        of the wiring" was WRONG**: `SWAP_RESIDENT` guarded only two of the three
        sites the spec claimed — there was no `stmt_table` dispatch arm at all, so
        the first run had all 20 `swap` rows reporting `syntax error`,
        indistinguishable from SWAP being absent. The gate also found that SWAP
        accepted non-name operands (`SWAP A,1` → `Illegal function call` plus
        trailing output, where the reference says `Syntax error`) — fixed with an
        `is_letter` guard at the *handler's own depth*, because sw_operand is
        `call`ed and the abort chain returns into its caller (D-CUR-D).
        ✅ **CHARACTERISED 2026-07-27**,
        [`docs/missing-vg8020-characterization.md`](docs/missing-vg8020-characterization.md),
        probe [`probes/basic/basic_probe_missing.py`](probes/basic/basic_probe_missing.py),
        `make missing-characterize` (`BOOTPC=1` for the confirmation run) —
        175 cases, 8 batteries, every number boot-per-case. **SLICED + COSTED**,
        [`docs/decision-missing-class-slicing.md`](docs/decision-missing-class-slicing.md),
        **awaiting sign-off (D-MC-1..4)**.
        ✅ **D-MC-2 SIGNED OFF 2026-07-27**: D-MISS-1 folds into this slice,
        D-MISS-2 gets its own. ✅ **D-MC-4 O-1 CLOSED** before any clamp was
        written (battery `locrow`, `make missing-characterize ONLY=locrow`,
        18 rows, batched + boot-per-case identical): **`LOCATE`'s row clamps to
        the console's own bottom row**, which moves with `KEY` (reference 22 at
        `KEY ON`, 23 at `KEY OFF`; zerobas 23 in both) — **not** a literal 23 and
        **not** `CRTCNT`, which measures 24 on both machines everywhere. Also
        measured for the spec: the argument domain has **two** error stages
        (`Overflow` past int16, `Illegal function call` outside `0..255`), and
        the five tokens are pinned from the reference's own crunch
        (`LOCATE $D8`, `SWAP $A4`, `TRON $A2`, `TROFF $A3`, `MOTOR $CE`).
        📋 **SPEC WRITTEN, awaiting sign-off (S-MC-1..5)**:
        [`docs/spec-basic-missing-class.md`](docs/spec-basic-missing-class.md)
        — 300–420 B against 420 B free, proposed **repack-only** so the lean
        cart stays byte-identical, ordered cheapest-first
        (`MOTOR` → `TRON`/`TROFF` → D-MISS-1 → `LOCATE` → `SWAP`).
        ✅ **D-MC-1 SIGNED OFF + D-KW-2 LANDED 2026-07-27**: the `exec_stmt`
        dispatch table replaced the 69-entry `cp`/`jp z` chain, **page-1 free
        311 B → 420 B (+109 B)**, dispatch block 377 B → 268 B, and the
        per-token cost is now 3 B instead of 5 B. Gated by
        [`tests/test_stmt_dispatch.py`](tests/test_stmt_dispatch.py) in
        `make unit-test`: **all 121 entries** (52 lean + 69 repack) reach the
        handler the pre-refactor chain sent them to, plus the fallthrough paths.
        ⚠️ It moves the **LEAN** cart too (shared code) — `LEAN_SHA256` updated
        deliberately in the same commit, as `tools/check_reloc.py` requires, and
        lean is gated per-entry exactly like repack. **The first version of that
        gate was green and worthless** — it read its expectations from the table
        under test, and passed with `PRINT` deleted and `CLS` re-pointed; the
        fix was an expectation recovered from the pre-refactor chain in git.
        **The measurement changed the plan: the class does NOT fit.** The
        roadmap costed it as dispatch glue only, on the premise that bodies live
        in `sub.rom`; but four of the five touch interpreter-core state (cursor,
        variable table, line executor) and are real statements. Measured against
        whole-statement spans already in the tree (`ex_color` = **100 B** for the
        same 3-optional-argument parse shape, with no bound check and no clamp),
        the five come to **300–405 B + 25 B glue against 311 B free**. So
        **D-KW-2 is now a prerequisite, not an option** — exactly as this item
        predicted. Its saving is re-measured on the current tree and confirms the
        estimate: 69 entries, 345 B of chain → 223–231 B of table, **−114…−122 B**.
        Surface highlights the spec turns on: `LOCATE`'s bound is
        **`WIDTH`-relative** and all three arguments are byte-domain-then-clamped
        (`0,255` accepted, `0,256` → `Illegal function call`); `SWAP` requires
        **exact type equality** (`%`≠`!`≠`#`), and its **second** operand must
        already exist while the first may be created; `TRON` traces per **LINE**,
        never in direct mode, survives `RUN` but not `NEW`; `MOTOR` is three
        forms and everything else is `Syntax error` — and
        [`tape/tape.asm:175`](tape/tape.asm:175) **already implements `STMOTR`
        (`$00F3`)** with the matching convention, so its body is a parse and a
        `call`.
      - **`DEF FN`/`FN`** — an arc, not a slice (200–400 B): a definition table,
        argument binding, re-entrant evaluation.
      - **The `CLEAR` string-pool partition** — ✅ **LANDED 2026-07-29, 51/51
        gated, falsified.** Opened by the `BIN$`/`FRE` slice (D-BF-A(c)):
        zerobas had ONE free gap where the reference has TWO pools, and
        `CLEAR`'s string-space argument was evaluated and discarded. The six
        recorded-not-gated `FRE` rows are back in a gate.
        [`docs/spec-basic-clearpool.md`](docs/spec-basic-clearpool.md),
        [`docs/clearpool-vg8020-characterization.md`](docs/clearpool-vg8020-characterization.md),
        [`docs/decision-clearpool-funding.md`](docs/decision-clearpool-funding.md),
        `make clearpool-acceptance` (57 rows, twelve batteries). Baseline 6/51.
        FUNDED by promoting `fld_lookup` to a page-0 sub-ROM tenant
        (`sub/fldlook.asm`, index 12 — **the last page-0 index that fits before
        the fixed `$0038` vector**): page 1 3 B → 41 B free.
        ⚠️ **THREE THINGS THE SPEC DID NOT ANTICIPATE, all found by measuring.**
        (1) `FRE(n)` needed its own handler — both forms shared op 15 because
        there was one gap, and left alone `FRE(0)` reads 200 at boot (the
        probe's `ctl-fre0` CONTROL catches it). (2) **A sized pool measures the
        PEAK, and zerobas's peak was 3×**: `A$=STRING$(100,"A")` charged 300
        (the `STRING$` temp, `str_set_key`'s H1 snapshot *of that temp*, and the
        variable's body) where the reference charges 100 — and **`FRE("")` HID
        it**, because FRE GCs first, so the resting number looked right while
        `CLEAR 100 : A$=STRING$(100,"A")` raised ERR 14. Fixed by skipping the
        redundant snapshot for a source that is already a temp, and by having
        `sh_var_store` **adopt** a temp's body instead of copying it.
        (3) ERR 14 cost **one byte** — a different FPERR code, not a different
        code path. Also: **`oos-vs-oom` was measuring two claims at once** and
        was SPLIT rather than silenced; the six ungated rows are ungated for
        three different reasons and the battery names (`rep`/`share`/`arr`)
        carry which.
        The model is a **single moving boundary, not a second
        allocator** — `CLEAR 200`→`FRE(0)`=28815 and `CLEAR 4000`→25015, a
        difference of **exactly 3800**, so the pool is carved from the same RAM.
        The pools are independent: the equal-depth `FRE(0)` delta across
        `A$=STRING$(100,"A")` is **6 on the reference at both 100 and 200
        chars** (the entry only) against zerobas's 106 and 206.
        `CLEAR n` sizes the pool to exactly n; the default is 200 but a **bare
        `CLEAR` KEEPS the current size** (`CLEAR 500:CLEAR` → 500, and so do
        `NEW`/`RUN`/`CLEAR ,himem`); **`B$=A$` COPIES** the body; a dead body is
        reclaimed and a pure temp fully given back; **`Out of string space`
        (ERR 14) is real and the failed allocation is ROLLED BACK**; and
        `CLEAR -1`/`32768`/`"200"` raise IFC/Overflow/Type mismatch where
        zerobas raises **nothing**. ERR 14 is currently a **hole** in
        `err_msgtab` pointing at `err_unprintable`, exactly as ERR 24 was.
        ✅ **S-CLP-1 the carve, S-CLP-2 derive-don't-store, S-CLP-3 the 200-byte
        default, S-CLP-4 the stored literal and S-CLP-5 body sharing are all
        answered — see the spec's §7.** S-CLP-4 is the one whose ANSWER moved
        it: a stored-program literal costs the pool **nothing** (measured, and a
        25-char literal still costs nothing, so it is zero and not slack),
        because the reference points the descriptor at the program text — but
        matching that needs storing by REFERENCE, which is S-CLP-5's scope, not
        a `heap_alloc` change as the question assumed.
        ⚠️ **S-CLP-3 was the user-visible one**: the 200-byte default means
        programs that used to have ~15 KB of string space now get 200 unless
        they say otherwise. The full acceptance corpus was re-run, not just this
        slice's gate.

- [ ] 🔴 **`SAVE"CAS:name"` WRITES A TOKENISED TAPE; BOTH REFERENCES WRITE
      ASCII.** Found 2026-08-03 by D-DOTGAPS
      ([`docs/dotgaps-msx1-characterization.md`](docs/dotgaps-msx1-characterization.md)
      §3.2), while measuring which SAVE forms write `.` — the row that looked
      like a cassette-specific `.` divergence turned out to be a **format**
      divergence, and the tape says so rather than an argument: recorded to WAV
      and decoded, the VG-8020's `SAVE"CAS:E"` opens `ea ea ea …` and carries
      the program as **text**, zerobas' opens `d3 d3 d3 …`. On MSX1 `CSAVE` is
      the tokenised cassette write and `SAVE"CAS:"` is the ASCII one, `,A` or
      not. zerobas already HAS the ASCII cassette save (`SAVE"CAS:",A`, M2 of
      `spec-cas-ascii-saveload.md`), so the fix is a dispatch default in
      [`basic/save.asm`](basic/save.asm) `sav_is_cas` — but it re-specifies a
      shipped save format and **inverts an assertion in
      [`probes/basic/basic_probe_tape_save.py`](probes/basic/basic_probe_tape_save.py)**,
      whose format oracle is `build_cas_basic` (tokenised) for this very verb.
      That probe's expectation is the thing to fix first; the header comment at
      [`basic/save.asm:12`](basic/save.asm:12) documents the wrong behaviour as
      intended. **Pinned** as `csv-tok` = ` 5  0 ` in `lnblank`'s
      `KNOWN_DIVERGE`, so the day it lands the pin rots loudly.
      ⚠️ Consequence for `.`: the reference writes `.` = the last line the ASCII
      walk emitted; zerobas writes nothing there. **Fixing the format fixes the
      `.` row with no `.` change at all** — the writer is already correct.

- [ ] **`LOAD"CAS:"` ACCEPTS A TOKENISED TAPE; the reference does not return.**
      Found 2026-08-03 by D-DOTGAPS (§1.2). With only a $D3 file on the tape the
      VG-8020 printed no `Found:` and no error and sat there — it searches past
      a non-ASCII header to the end of the tape and waits. zerobas answers, via
      the 3-way header dispatch in [`basic/cload.asm`](basic/cload.asm).
      ⚠️ **NO ROW CAN CARRY THIS**: the faithful behaviour is a HANG, and a row
      that hangs one side gates nothing (the same reason `kwgz-`'s AUTO/LLIST
      rows are side-locked). Filed for the judgement call — bug-for-bug fidelity
      here costs a working feature — not for a fix.

- [ ] 🔴 **A LINE STORE IS BOUNDED BY THE CONSTANT `TXTMAX`, NOT BY HIMEM.**
      Found 2026-08-03 by D-DOTGAPS (§4.2/§6 D4). After
      `CLEAR 300,TXTTAB+1000` both references have **148** free bytes and refuse
      a 32-byte line with `Out of memory`; zerobas has **646**, stores it, and
      prints nothing — `CLEAR`'s HIMEM argument does not reach the store check
      at [`sub/lineedit.asm:115`](sub/lineedit.asm:115), which compares
      `PRGEND + size` against a fixed `$BB00`. **Pinned** as `crf-oomsay` /
      `crf-oomlst`.
      🔴 **AND IT IS WHY D-DOTGAPS' OWN RULE HAS NO EMULATOR GATE.** No typed row
      can reach the OOM path on this side, so `crf-oom` agrees at ` 20  0 ` for
      the wrong reason (a *successful* store writing the same number the
      references write on a *refusal*), and R-DOT3a′ is gated by
      [`tests/test_program.py`](tests/test_program.py) alone. Fixing this bound
      would give that rule a real row.

- [ ] 🔴 **`DIM Q(20000)` → `Out of memory`, reference says `Subscript out of
      range`.** Found 2026-07-28 as a calibration row in the D-CLP matrix
      (`oos-vs-oom`), aimed at proving `Out of string space` was distinct — the
      **sixth consecutive slice** whose calibration turned up a live defect in
      code already marked implemented. The reference bounds a dimension
      **before** it tries to allocate; zerobas allocates until it runs out, so
      the error is right only by accident of size. An ARRAYS-arc divergence,
      NOT in D-CLP's scope. Recorded in
      [`docs/clearpool-vg8020-characterization.md`](docs/clearpool-vg8020-characterization.md)
      §3 so it is not "discovered" later by a red gate. Unmeasured: where the
      reference's dimension bound actually sits.
      ⚠️ **The row that found it was carrying TWO claims and has been SPLIT**
      (D-CLP landing, 2026-07-29). `oos-vs-oom` asserted both "out of string
      space is distinct from out of memory" (D-CLP's, and true) and "which
      non-string error a huge DIM gives" (this item, and divergent). The first
      is now gated on `DIM Q(5000)`, which overruns free variable space on BOTH
      machines; **this one lives on as `oos-dim-huge` in the probe's `arr`
      battery — reported, never gated.** It was not silenced to make D-CLP
      green: it is the standing record, and it will turn from `----` to a
      gateable row the day the ARRAYS arc fixes it.
      ✅ **CHARACTERISED 2026-07-29** —
      [`docs/arrdim-vg8020-characterization.md`](docs/arrdim-vg8020-characterization.md),
      probe [`probes/basic/basic_probe_arrdim.py`](probes/basic/basic_probe_arrdim.py),
      `make arrdim-characterize` — 49 rows, eight batteries, boot-per-case.
      **Baseline 27/46 gated** (3 reported-never-gated); **all 19 divergences are
      one root cause.** The rule: **`elsize × Π(boundₖ+1) > $FFFF` ⇒ `Subscript
      out of range`, raised before any allocation.** It is a **byte** count
      (the flip moves with element width — `%` 32766/32767, `!` 16382/16383,
      `#` 8190/8191, all at 65536 B; `Q%(32767)` has 32768 elements, which fit a
      word, and still raises), it **excludes the header** (`Q%(32766)` = 65534 B
      → `Out of memory`), it is strictly **`>`** (`Q$(21844)` = 21845×3 =
      `$FFFF` exactly is ACCEPTED — the only element width in the language that
      can land on the boundary, which also pins `elsize($) = 3`), and it is on
      the **product**, position-independent (`DIM Q%(200,200)` raises with no
      dimension near a ceiling). ⚠️ **It lives in the ALLOCATOR, not in `DIM`**:
      `Q(1,1,1,1)=1` on an *undeclared* array auto-dims to 10 per dimension =
      117128 B and raises, with neither `DIM` nor a large number in the line —
      so a check written into `ex_dim` would have satisfied every other row and
      left that one silently wrong.
      📋 **SPEC WRITTEN, awaiting sign-off (S-ARR-B-1..4)**:
      [`docs/spec-basic-arrdim.md`](docs/spec-basic-arrdim.md) — **est. +4 B,
      sub-ROM only, NO CARVE**: `sub/arrays.asm` already computes the quantity
      and already detects both overflows (`ary_count_elems`,
      `ary_mul16_checked`); the two carry paths just report `ARY_ERR=4` where
      the measurement says `1`. The other three carry checks are address-space
      wraps and stay `Out of memory`. Falsification is unusually surgical: the
      two sites catch **disjoint** row sets (site A = `dim-3d` alone, site B =
      the other 18).

- [x] ✅ **`MAXDIM = 4` was a divergence, not a cap — D-ARR-C LANDED 2026-07-29,
      65/65 gated, and it GAVE BACK 31 B.** Spec
      [`docs/spec-basic-arrdim-c.md`](docs/spec-basic-arrdim-c.md), measurement
      [`docs/arrdim-c-vg8020-characterization.md`](docs/arrdim-c-vg8020-characterization.md),
      gate `make arrdim-acceptance` (73 rows; 65 gated, 8 never-gated). Found as
      a calibration row in the D-ARR-B matrix — the seventh consecutive slice
      whose calibration turns up a live defect nobody was looking for.
      **There was no cap to match**: the reference answers `ERR`=0 at 4, 8, 16,
      32, 40, 42, 44, 64, 100 and **120** subscripts (a 249-character line), and
      it stores and reads an element back through 32 of them.
      ⚠️ **`ERR`=0 IS NOT ENOUGH** — a machine that accepts the line and drops
      every subscript past its own cap reads 0 too. The `use` battery is the
      round trip the dropped dimensions cannot forge.
      ⚠️ **THE PREMISE THE SLICE WAS SPLIT ON WAS WRONG.**
      [`spec-basic-arrdim.md`](docs/spec-basic-arrdim.md) §7a split it out
      because a pointer design "rewrites `ary_resolve`'s column-major
      element-address math, where a mistake is silent memory corruption". It
      does not: `ary_parse_subs` pushes subscript 0 FIRST, so it sits at the
      HIGH address — point the tenant there and walk DOWNWARD and every consumer
      keeps visiting k=0..n-1 in today's order. `inc ix` → `dec ix`, same size,
      offset math untouched. Same correction ran through the cost: §7a estimated
      −10…−15 B and it measured **−28 B** (low region 4 B → 32 B free).
      **Removing a constraint removes more than the line that states it** — the
      cap's unwind path, its skip-to-`)` recovery, the `_kt` shim and two
      callers' publish/pop tails all went with it.
      `MAXDIM` is gone; `ARY_IDX`'s 8-byte buffer is now `ARY_IDXP` (a pointer)
      + `ARY_CUR`, freeing 4 B of RAM in a span whose own header records "no
      slack for anything more".

- [x] ✅ **D-LINEMAX — the input line AND the crunched line. LANDED 2026-07-29,
      gate `make linemax-acceptance` 60/60 typed + 3/3 `--cas`.** `LINEMAX` 96 →
      255, the crunch bounded at 314 body bytes with `Line buffer overflow`
      (ERR 25), ASCII/tape path free. `arrdim-acceptance` **73/73** (its
      `NEVER_GATED` set is now EMPTY — all 8 rows promoted), `array-acceptance`
      149/151 (standing baseline), `clearpool-acceptance` 52/52, unit-test 53/53,
      lean byte-identical. Low region **9 B free**, page 1 **6 B free**.
      🔴 **THE SPEC COUNTED TWO BUFFERS AND THERE WERE THREE.** `DETOKBUF` (LIST's
      render target) is SIZED FROM `LINEMAX` — the wave-3 detok spec derives its
      512 B as `95×5=475` and explicitly dismissed the 255-char case because "the
      source line is capped at 96 bytes" — so R-1 would have turned a second,
      previously-safe unbounded buffer into a 1270-byte write into 512. Found
      while implementing, not while specifying; **one `grep` for `LINEMAX` would
      have found it.** Now 1280 B, and FALSIFIED before trusted (revert it and
      `list-max` reads `78`, a byte of the rendered text, through `$C100`).
      ⚠️ **COST 1792 B, NOT THE 768 SIGNED OFF** — measured `FRE(0)` 15667 →
      13875. Five `array-acceptance` rows reserved `CLEAR 14000`/`15000` and died;
      re-sized with sign-off (root counts, the actual subject, untouched).
      **The suite no longer proves a ~12 KB string workload runs.**
      ⚠️ **`TOKBUF` is 576 B, not 315:** the spec's single `tk_loop` test could not
      work — `tk_str_loop`/`tk_rem_rest`/`tk_data_rest` never re-enter `tk_loop`.
      The buffer ABSORBS the worst pass and `tk_end` adjudicates once, so the
      bound is PROVABLE from `LINEMAX` rather than audited emit site by emit site.
      ⚠️ **The `corrupt` battery was not boot-isolated and its own control agreed
      for the WRONG REASON:** `reset=("NEW",)` clears the program, not `ERRCODE`,
      so `code-ctl` read back the ` 25 ` `code-over` had just raised — on BOTH
      machines, so it PASSED while measuring nothing. Alone on a fresh boot: ` 0 `.
      Also fixed: a ONE-SIDED `rem` calibration (retargeted to the `rem-254`/`-255`
      pair, which admits `LINEMAX=255` and no other value), `--only` ignoring
      comma lists, and `make linemax-characterize`/`-acceptance` NOT EXISTING
      despite the previous commit citing them.
      Superseded detail below (kept for the route it records).

- [ ] 🔴 **D-LINEMAX — the input line AND the crunched line. SPEC WRITTEN,
      MEASURED, AWAITING SIGN-OFF.** Spec
      [`docs/spec-basic-linemax.md`](docs/spec-basic-linemax.md), measurement
      [`docs/linemax-vg8020-characterization.md`](docs/linemax-vg8020-characterization.md),
      probe [`probes/basic/basic_probe_linemax.py`](probes/basic/basic_probe_linemax.py)
      (seven batteries, 61 rows + 3 cassette rows; baseline **22/53** typed).
      Split out of D-ARR-C, which measured the input-line half
      ([`docs/arrdim-c-vg8020-characterization.md`](docs/arrdim-c-vg8020-characterization.md)
      §4) and could not reach it.
      ⚠️ **IT WAS FILED UNDER THE WRONG CAUSE FOR A WHOLE SLICE**, and then
      filed at the WRONG SIZE. `cap-64`/`cap-100` were carried as "MAXDIM=4"
      rows by the D-ARR-B commit; the cap is what hid the truncation. But the
      input line turns out to be the *smaller* half:
      * **Input line — one constant.** Reference **254** characters, zerobas
        **95**, and both already agree on what truncation MEANS (drop the tail,
        keep and store the line, raise nothing). `LINEMAX` 96 → **255**.
        The one-page low-byte idiom in both readers SURVIVES — it needs a
        page-aligned base and ≤ 256 bytes, not ≤ 96 — so no reader logic
        changes, and the G3/G4/G5 aliasing argument is RETIRED rather than
        re-proved.
      * 🔴 **Crunched line — a LIVE memory-corruption defect, today, at
        `LINEMAX=96`.** The crunch expands (`0#` = 2 chars → 9 bytes) and
        `TOKBUF` (96 B) is bounded NOWHERE. A **27-character** line overruns it;
        the worst case writes **407 bytes into 96** — over `ARYTAB`, the
        error-trap block, `ZTRAP`, `POOLSIZE`, into `STRTAB` — silently, and
        after it zerobas cannot execute `B=7`. The reference refuses at 315
        body bytes with **`Line buffer overflow`, ERR 25**. This is what
        actually sizes the slice.
      ⚠️ **THE APPARATUS HAD THE ANSWER HARD-CODED, AND IT WAS A GUESS.**
      `omsx_repl.MAX_BUF` was 250 and *refused to inject anything longer*, which
      is why §4 read the reference's ceiling as 250 — the harness's cap reported
      as the machine's. Fixed to 254, measured. Also fixed: an EMPTY capture was
      being discarded, collapsing "line refused" into "the machine never got
      there".
      ⚠️ **A BYTE-COMPARISON GATE CANNOT SEE THIS.** Every `lnum` row PASSES —
      both machines crunch identical bytes and only the one with a 96-byte
      buffer is harmed. **Agreement on what was produced is not agreement on
      whether it fit**; the `corrupt` rows, which read the damage, are the ones
      with teeth.
      Decisions taken (2026-07-29): **repack-only**, because the lean cart is
      retired (below); RAM funded by lowering `TXTMAX` 768 B, chosen **by
      measuring** — the reference funds its own buffers out of the same `FRE(0)`
      pool programs live in, so that is the faithful mechanism, and the
      alternative (dropping `MAXFILES` to 1) moves AWAY from a reference that
      supports 15. Message-string placement deferred to implementation.

- [ ] **README "Limitations (this slice)" IS STALE** — pre-existing doc debt, FLAGGED
      2026-07-29 by S3 of the lean-cart retirement, which deliberately did not fix it
      (out of scope; S3 was a byte-identical mechanical edit plus its own doc sweep).
      [`README.md:291`](README.md:291) describes an early game-loader-scoped slice, not
      today's BASIC. Measured false claims: it lists **`ON … GOTO` as "still out"**
      (it is implemented — `ON_TOKEN` → `ex_on` in `stmt_table`, gated by
      `tests/test_stmt_dispatch.py`, and `tests/test_control_flow.py` exercises the
      branch), and it says **"variables are single-letter integers (`A`–`Z`); no
      strings, arrays, or multi-character names"** and "no `/`, no string ops", all of
      which predate the string engine, the float pack and the array engine.
      A warning banner is in place so a reader is not misled, but the section needs
      rewriting against the CHARTER (faithful full MSX1 BASIC), not patching
      claim-by-claim. **Check the neighbouring prose too** — the same slice-era framing
      likely leaks into the sections around it.

- [x] **`GET(RDBLK)` IS AN INTERMITTENT GATE ROW — FIX THE ANCHOR — ✅ DONE 2026-07-30.**
      [`docs/spec-rdblk-anchor-flake.md`](docs/spec-rdblk-anchor-flake.md).
      Falsification battery **14/14** · repeatability `ONLY='GET(RDBLK)'` **10/10, 0
      retries** · standing gates **54/54 · 34/34 · 12/12 · 7/7** · ROMs byte-identical
      from clean, walls unchanged (low 80 B / page 1 49 B), dead-code sweep 0/0.
      🔴 **THE FILED DIAGNOSIS WAS WRONG ABOUT WHICH CLOCK.** `--settle`/`--keys-at` are
      openMSX **emulated** time, and the anchor is a breakpoint on `done` — so the
      readout was **already sentinel-gated** and the emulated timeline is
      bit-deterministic (ours 24.137504 / stock 24.450109, identical across every run
      measured). The elapsed-seconds gate that actually remained was the **host-side
      process deadline**: `run_job_raw` SIGKILLed openMSX **silently**, and to every
      caller that is indistinguishable from "this machine ran its whole timeline and
      never reached the anchor" — an APPARATUS event laundered into a SUBJECT-shaped
      verdict. Fixed with a `after realtime` **liveness heartbeat** (wait on PROGRESS,
      not elapsed seconds; kill on stall under the untouched ceiling; report the reason
      and the stall point), a **LOGICAL (exit 2) vs APPARATUS (exit 3)** split in
      `capture`, `reverse savereplay` on a logical miss, renested timeouts (they had
      been INVERTED: 220 s per boot inside a 240 s cap for a 6-boot probe), and a
      **bounded, PRINTED** retry on the apparatus class only — never on a logical miss.
      🔴 **THE G4 CONTROL CAUGHT A DEFECT IN THE FIX ITSELF.** The stall clock started
      at `t0`, i.e. before openMSX had launched, charging 0.21–0.82 s of spawn + XML +
      ROM/symbol load to the emulator: under load a HEALTHY run was stall-killed, and it
      did **not** reproduce standalone. Shipping it would have traded one intermittent
      row for a **corpus-wide** one. The clock now starts at the FIRST BEAT.
      🟢 **BIGGEST FIND, and it came from the user challenging a recorded belief:**
      testing "is the wedge really pty exhaustion?" (it is not — 7 pty holders against a
      511 limit, and openMSX allocates none) surfaced that the preamble left
      `sound_driver sdl`, so **every headless probe boot opened a CoreAudio device and
      ACTIVELY STREAMED** — ≈200 start/stop cycles per gate run, audible on the dev
      machine, and a candidate cause of [[openmsx-coreaudio-wedge]]. `sound_driver null`
      is **measured** neutral (zero drift on both machines, byte-identical captures) and
      removes the whole class. ⚠️ Deliberately NOT `mute`/`master_volume 0` — those
      silence the noise and leave the churn.
      ⚠️ **NOT PROVEN: the original trigger.** The flake never reproduced on demand, so
      nothing shows the 2026-07-30 event would now be caught as APPARATUS; and
      `sound_driver null` removes a candidate cause, not a demonstrated one.
      Left alone (noted §7): `WARNING: Var start is never used` in `rdblk_rt.asm` — a
      documentary label for `$0100`, zero emitted bytes, probe-side.

      **Original entry, for context.** (observed
      2026-07-30 during the dead-code-gate slice, which is NOT its cause).
      [`probes/disk/disk_probe_rdblk_roundtrip.py`](probes/disk/disk_probe_rdblk_roundtrip.py)
      failed once in a full `make diskbasic-acceptance` (33/34), then **passed
      standalone AND in a full re-run on the BYTE-IDENTICAL build** — so the subject
      is innocent and the APPARATUS is the defect.
      🟢 **THE PROBE DIAGNOSED ITSELF CORRECTLY, which is why this is a fix and not an
      investigation**: it printed `*** MISALIGNED — diff NOT meaningful ***` with
      `stock reached anchor: NO (looped / never hit occurrence #1)` /
      `ours reached anchor: YES`, and its own source calls this class
      "Anchor/keys/timing problem, not a `$27` result". **It refused to report a
      memory diff between two different logical points** — exactly the discipline
      [[width-domain-slice]] and [[traps-t2-strig-slice]] ask for. The bug is only
      that it can get there at all.
      **Cause to fix:** the capture uses FIXED WALL-CLOCK injection —
      `--keys "\rRDBLK\r" --keys-at 20 --settle 40` — so whether the STOCK side
      reaches `done` depends on host timing. ⚠️ **I speculated host contention from my
      own overlapping runs and then WITHDREW it: the timestamps do not support it**
      (diskbasic ran 12:44–13:15, after any overlap). Cause is unconfirmed; what is
      certain is that the anchor is time-based and therefore not deterministic.
      **Fix direction:** gate the readout on a `done` SENTINEL rather than elapsed
      seconds — the standing lesson [[traps-t3-key-slice]] ("gate every reading on a
      `done` sentinel"), which the rest of this corpus already follows. Failing that,
      retry-on-MISALIGNED with a bounded count and REPORT the retry (a silent retry
      turns a flaky gate into an invisible one).
      ⚠️ **DO NOT "fix" this by loosening the misalignment check.** That check is the
      only reason the flake was legible instead of a fabricated 0-byte diff.
      Also noticed in passing: `WARNING: Var start is never used on line 33 of
      probes/disk/rdblk_rt.asm` — probe-side, unrelated, and NOT covered by the new
      dead-code gate (which sweeps `basic/` + `sub/`, not `probes/`).

- [x] **LAND THE TRANSITIVE DEAD-CODE SWEEP AS A TOOL — ✅ DONE 2026-07-30.**
      [`docs/spec-deadcode-gate.md`](docs/spec-deadcode-gate.md).
      [`tools/check_dead_code.py`](tools/check_dead_code.py) +
      [`tools/deadcode-allow.txt`](tools/deadcode-allow.txt), a **HARD GATE** inside
      `make basic-reloc` over **BOTH** builds (user chose the hard gate over an
      advisory report), plus `make deadcode` for the report while writing a routine
      ahead of its caller. Standing state: **main 0 dead** (1544 spans, 264 seeds),
      **sub 0 non-allowlisted** (1375 spans, 98 seeds, 1 allowlisted). R1's walls
      UNCHANGED at low 80 B / page 1 49 B, `basic-reloc.rom` byte-identical.
      🟢 **ITS FIRST FINDING AS A GATE: 24 B in `sub/graphics.asm`.**
      `gfx_border_read` was orphaned when the empirical VG-8020 PAINT bug fix replaced
      it with `gfx_paint_read`, and sat unreferenced from G5 all the way to R1 —
      **with three comments still describing it as the live border reader** (lines
      1592, 1724, 1842, all corrected). Deleted; sub page-0 content `$302A -> $3012`,
      free 4054 -> 4078 B.
      🔴 **THE ALLOWLIST IS A CONTROL, NOT A SUPPRESSION LIST — this is the design
      point.** The gate asserts every allowlist entry is STILL DETECTED AS DEAD. The
      dangerous failure for this tool is not a false red, it is **going blind and
      reporting a clean tree forever** — an over-broad seed set, a broken span model
      or a path change all look exactly like success. `fmt_menu_text` (16 B, a
      DOCUMENTED deliberate keep preserving `format-body.inc`'s pre-eviction byte
      layout) is therefore a permanent canary: if it stops reading as dead, either it
      gained a caller or the sweep broke, and both must be looked at.
      **FALSIFIED THREE WAYS**, the third being the one the review's own scratchpad
      harness lacked: (A) inject a dead routine into EACH build -> both reported,
      exit 1; (control) give each one live caller -> 0 dead, exit 0; (B) `--blind`
      (seed every label) -> prints **"0 dead" for both builds**, which reads as
      success, **and the canary fires**, exit 1. Allowlist guards each verified to
      fire: missing reason, bad build name, entry that is not actually dead. Seed
      vacuity guards: `init` must resolve, every sub entry-table seed must resolve,
      and <20 parsed tenants is a hard error.
      ⚠️ **THE GATE HANGS OFF THE `basic-reloc` PHONY TARGET, NEVER OFF THE
      `$(RELOC_SYM)` FILE RULE** — it needs both `.sym` files, and `$(SUB_ROM)`
      already depends on `$(RELOC_SYM)` through `sub/basic-resident-abi.inc`, so the
      other wiring would close the build-graph cycle the Makefile is shaped to avoid.
      Not swept: `disk/` (its own build, its own seed problem, not wall-constrained).

      **Original entry, for context.** (filed 2026-07-30 by the ROM
      REGION STRUCTURE REVIEW, which built it in a scratchpad and threw it away).
      It found **122 B** where pasmo's per-symbol warnings showed 80, and it is the
      only instrument in the tree that can see a routine that IS referenced but only
      from code that is itself dead (`div_zero`, `var_find`). Worth `tools/`, with a
      standing gate that reports the dead set — the review's whole point is that this
      finding sat unread in ~230 lines of warning noise for months.
      ⚠️ **IT MUST KEEP ALL FOUR APPARATUS FIXES**, each of which produced a confident
      wrong row while missing: (1) the terminator test must use
      `check_tenant_closure.py`'s `_is_terminator` — a naive `^(ret|jp|jr)` matches
      `jp nc,x`/`ret nz` and falsely kills fallthrough-entered routines
      (`ei_set`/`spr_set`); (2) lines before a file's first label must be attributed
      to an always-live prologue span, or references made there are invisible
      (`sp_done`); (3) closure must follow **DATA** references (`ld hl,label`,
      `dw label`), not just call/jp/jr/djnz — this is the one that read
      `keytrap.asm`'s `$0038` hook as promotable; (4) 🔴 **"dead" is PER-BUILD** — a
      body `.inc` shared by main and sub has TWO answers, and `disk_putword` was dead
      in main, live in sub, with its only caller outside `main.asm`'s include closure.
      The tool should walk BOTH builds and report per-build, and `IF SUB_BUILD` is the
      sanctioned fix for the asymmetric case. Seed on build consumers only
      (`init` + `sub/` + `tools/`): seeding on `tests/`/`probes/` too hides the whole
      `vars.asm` block, because the ported tests still name it — that seed choice is
      the difference between 16 dead spans and 4. Falsify both ways (inject a dead
      routine; then give it one live caller).
      Also worth landing beside it: the **per-include byte-extent measurement** (inject
      zero-byte labels around all 111 `include` sites, recursively) whose own control
      is that both instrumented images assemble BYTE-IDENTICAL to the shipped ROMs —
      that is what produced every size in the review, and pasmo emits no listing file.

- [x] **ROM REGION STRUCTURE REVIEW — ✅ DONE 2026-07-30, and R1 LANDED.**
      [`docs/rom-region-structure-review.md`](docs/rom-region-structure-review.md) +
      [`docs/spec-rom-region-rebalance-r1.md`](docs/spec-rom-region-rebalance-r1.md).
      **THE WALLS ARE OFF ZERO FOR THE FIRST TIME IN THE ARC: low 0 B -> 80 B free,
      page 1 7 B -> 49 B free**, `sub.rom` byte-identical (`1dbbfe2f…`). All gates
      green incl. linemax 60/60 (ERR 25's string moved).
      🔴 **THE MAIN ROM'S PAGE-1 HALF HAS NO PLACEMENT CONTRACT AT ALL.** All 13
      sub-ROM page-0 tenants — 709 routines of closure — call **ZERO** main routines,
      so nothing in page 1 is contract-forced there; all 16377 B of it is
      pressure-placed. The `$4000` contract points ONE WAY (low-region code that
      page-1 tenants and the `$0038` ISR reach must stay low). Falsification control:
      re-seeding the same script with the page-1 tenant table finds 20 main callees,
      so the zero is a result, not a broken script. Consequence: **page-1 -> low moves
      are always legal** (only the low wall blocks them); low -> page-1 needs exactly
      one check, the forced set. 165 of 424 low-region labels are forced;
      `keytrap.asm` + `sprtrap-body.inc` forced WHOLE; `input.asm` (446 B) and the
      message pool pressure-placed WHOLE.
      🔴 **DE-EVICTION IS REFUTED BY MEASUREMENT — closed, do not spend a slice on
      it.** Largest resident stub is ~42 B (`dirverb`, the only tenant with two call
      sites, i.e. the case most likely to cross) against the SMALLEST body in the tree
      at 74 B. Every one of 35 tenants is on the right side by >=35 B. It buys
      simplification at a 35-155 B main-ROM **LOSS** against a 0 B wall.
      🔴 **THE CARVE WAS 122 B, NOT 80** — a TRANSITIVE sweep found two blocks
      pasmo's per-symbol warnings cannot see: `div_de_bc`/`mod_de_bc`/`div_zero`
      (26 B; **`div_zero` IS referenced — only from the other two**) and
      `disk_putword` (16 B). Sweep falsified both ways (an injected dead routine is
      found; the same routine with one live caller is not).
      ⚠️ **"DEAD" IS PER-BUILD, AND ONLY THE BUILD CAUGHT IT.** `disk_putword` is
      dead in MAIN and live in SUB: its definition is in the shared
      `basic/sv-diskwr.inc`, its only caller in `basic/sv-bsvdisk.inc`, which ONLY
      `sub/save.asm` includes — outside `main.asm`'s walked closure, so invisible.
      Deleting it failed the assembly. Now an `IF SUB_BUILD` gate (the second in the
      tree). **Nothing in the review's own apparatus could have found this.**
      ⚠️ **THE "128 B OF FREED RAM" THIS ITEM CARRIED FORWARD DOES NOT EXIST.** The
      `$E1C0..$E240` span was already spent by three later slices, each describing
      itself as homing in "the freed VARTAB window": `ARYTAB` `$E1C0`, `DIRECTF`
      `$E1C2`, `SAVSTK` `$E1C3`+`SAVTXT`, `ZTRAP` `$E1D1..$E207`. `sysvars.inc`'s own
      comment still claimed it was free — **corrected in place**. "`VAREND` must stay"
      was stale too (nothing references it; `STRTAB` is retired). R1 freed 122 ROM
      bytes and **0 RAM bytes**.
      ⚠️ **MY APPARATUS WAS WRONG FOUR TIMES BEFORE THE ANSWER WAS RIGHT ONCE**, and
      one row was actively dangerous: a call-graph-only closure missed
      `ld hl,zkey_hook` (a DATA reference), so **`keytrap.asm` — the `$0038` keyboard
      hook — read as PRESSURE-PLACED and would have been nominated for promotion into
      page 1**, where a page-1 tenant pages it out. There is now an assert on it.
      Also: a conditional `jp nc,`/`ret nz` read as an unconditional terminator
      (falsely killed `ei_set`/`spr_set`); lines before a file's first label belonged
      to no span (falsely killed `sp_done`).
      **NEXT TIER — ✅ ANSWERED 2026-08-05 by D-PINDATA, and the answer is DON'T.**
      [`docs/spec-rom-region-promote-input.md`](docs/spec-rom-region-promote-input.md).
      Re-measured from clean, instrument controlled by ROM byte-identity:
      **`input.asm` is 458 B, not the filed 446** (it grew 12 B), page 1 holds
      **301 B**, low holds **23 B** — so the promotion is **short by 157 B**, not by
      the 439 the stale note implies.
      🔴 **AND THE PREMISE IS INVERTED.** The item's rationale is that low is "the
      binding wall". Assembling every commit that touched `basic/` since the review
      landed (31 builds, pasmo is 0.1 s) says otherwise: **low moved 3 times, page 1
      moved 20+.** Low has sat at exactly 23 B for 25 of the 31 and never went below
      9; page 1 has ranged **5 B → 311 B** and spent **six consecutive commits at
      ≤ 8 B**. Promoting `input.asm` would drive **page 1 — the wall that actually
      binds — to zero** to add 458 B to the wall that sits. Structural reason, also
      measured: only **1643 B of the low region's 6126 B is contract-forced**, so
      "low free = 23 B" measures a PACKING CHOICE, not a contract, and the split can
      be re-cut on demand. **The promotion is DECLINED, not blocked** — that outlives
      the 157 B. Re-open only against a measured low-region need.
      🔴 **THE SAFETY CHECK FOUND A LIVE BLIND SPOT IN THE GATE, NOT IN `input.asm`.**
      The review's §0.1 error 3 fix (a call-graph-only closure missed
      `ld hl,zkey_hook`, a DATA reference) reached `check_dead_code.py` and **NOT**
      `tools/check_tenant_closure.py` — the gate that decides what may SHIP and the
      review's own named feasibility oracle — nor `tools/promote_scout.py`, the scout
      that decides what to ATTEMPT. Both matched only `call|jp|jr|djnz`. Measured
      instance: `tkf_ref32767/65535/32768` (15 B of bound tables at
      [`basic/float.asm:29`](basic/float.asm:29)) are reached by `ld de,tkf_ref32768`
      in `dcc_dexp5`, inside the closure of `flt_to_int16`, a **resident-ABI export**.
      `promote_scout` graded them **`PROMOTABLE` rc 0**; relocating them into page 1
      left the old gate printing **`OK … No page-1 escapes`, rc 0**. Fixed: a data
      pass on all three walks, on two rules that are each falsified — an `equ` is a
      VALUE (dropping that rule = **63** spurious page-0 escapes) and a data edge does
      NOT propagate control flow (dropping that = **482 B / 35 labels** over-pinned).
      🔴 **K1d PREDICTED RED AND MEASURED GREEN, and the green was the finding.** The
      tenant does NOT read those bytes at runtime: `cpt_round`
      ([`sub/circleparse.asm:309`](sub/circleparse.asm:309)) only ever converts
      `ratio*256` with `ratio <= 1`, so dexp <= 3 and the dexp==5 arm is **unreachable
      from the only tenant caller**. The pin is a CLOSURE-CONTRACT pin, not a live
      fault, and the spec says so. Separated by the K1/K1e knife PAIR, which also
      localised the real reader as main-side and corrected the probe's own row labels.
      New gate `make dexp5-pin` — **16/16 vs the VG-8020 in 6.0 s**, and the 15 bytes
      had **no gate at all** before (graphics CIRCLE corpus tops at coord 80 = dexp 2).
      ⚠️ **Naming an assembler label in a `tools/*.py` comment immunises it from the
      dead-code sweep** (`external_names` scans `tools/`; the main seed count moved
      283 → 284 on a comment mentioning `dcc_dexp5`). Nothing masked here — 0 dead
      before and after — but the hazard is real and unfixed. **WIDENED by D-EVLNO
      below: `sub/` is scanned too, and the trigger there was a comment naming two
      REJECTED candidates (284 → 285).**
      ✅ **RANK 4 OPENED AND COSTED 2026-08-05 — D-EVLNO**,
      [`docs/spec-rom-region-evict-lineno.md`](docs/spec-rom-region-evict-lineno.md).
      The tier's first per-file eviction, costed by BUILDING it as §7 demanded:
      `parse_lineno` (the D-LNBLANK line-number scanner, `basic/program.asm`) is now
      sub-ROM page-1 tenant index 23 (`sub/lineno.asm`). **73 B body out, 18 B stub
      back, 55 B NET** — main page 1 **301 -> 356 B free**, low unchanged at 23 B,
      sub page 1 2411 -> 2324 B. The 73 B body is **BYTE-IDENTICAL** at its new
      address, so the move is provably verbatim.
      🔴 **THE SUB PAGE-0 ENTRY TABLE IS FULL, AND THE REVIEW'S OWN RANK-4 RULE
      CONTRADICTS THAT.** 13 rows `$0010..$0036`, **ONE spare byte** before the fixed
      `$0038` IM1 vector (`$0037` = `FF`, `$0038` = `C3 0A F1`; measured, and
      `sub/sub.asm` + `sub/equates.inc` both already said so — nothing had connected
      it to "prefer page 0"). **A 14th page-0 tenant does not fit.** So a future
      rank-4 candidate that genuinely needs to call main page 1 is BLOCKED until
      `SUBROM_ENTRY_BASE_P0` is relocated past `$0038`. This candidate did
      not need it: the body calls **nothing at all**, so it is legal on either island
      and free bytes decided nothing — the *table* did.
      ✅ **DONE 2026-08-05 — D-P0BASE**, [`docs/spec-rom-region-p0base.md`](docs/spec-rom-region-p0base.md).
      `SUBROM_ENTRY_BASE_P0` is **`$0040`**, above the vector. **Index 13 is free and
      the table has no cap.** Cost **44 B of sub page 0** (3913 -> 3869); main walls
      unchanged (low 23 B, page 1 356 B), `sub.rom` page 1 **byte-identical**,
      `basic-reloc.rom` differs in **exactly 18 bytes** (every `ld ix` low byte,
      each +`$30`), and a relocation-aware page-0 diff explains **every** differing
      byte as a 16-bit operand moved by +`$2C` — **0 unexplained**.
      🔴 **AND THE REVIEW'S STATED JUSTIFICATION FOR "PREFER PAGE 0" IS THE WRONG
      ONE.** The visibility argument (a page-0 tenant may call main page 1) is worth
      **at most 95 B**, is claimed by **zero** candidates, lands on **sub**-ROM
      space rather than main, and is structurally unreachable: 777 of 1045 main
      page-1 labels are page-0-ILLEGAL, and all 268 legal ones are leaves, because
      anything reaching into main page 1 transitively reaches `eval` (low region) or
      `pchar` -> `CHPUT` (BIOS) and becomes illegal in the same step. The rule is
      right for a **capacity** reason nobody had measured: the table filled at
      `6c72931` (2026-07-29) and sub page 0 has been **frozen at 3913 B free for the
      last 9 commits** while page 1 absorbed **1015 B** — page 0 held **63 %** of the
      sub-ROM's free space and could accept no new tenant.
      🔴 **The filed justification was wrong twice.** "Free space starts at `$003B`"
      — no: `$003B..$0040` is `sub_p0_ping`, and basing the table there would have
      overwritten the tenant every boot gate calls. "Every call site is symbolic" —
      true of `basic/*.asm` (18 sites) and **false of the harness**: three probes
      carry the entry address as a hardcoded *byte* in injected machine code.
      ⚠️ **FOUR THINGS D-P0BASE FOUND — (a)+(b) CLOSED by D-ROMJUDGE, (c) UNFIXED,
      (d) fixed in-slice:**
      (a) 🔴 **`pasmo` answers a NEGATIVE `ds` count with a WARNING and EXIT 0**,
      writing a **zero-byte** file, and the whole `make basic-reloc` gate chain then
      passes the padded result at rc 0. `tools/pad_rom.py` now refuses an EMPTY
      input, which closes the total case — but a **partially truncated** ROM would
      still be laundered, and nothing bounds that.
      ✅ **DONE 2026-08-05 — D-ROMJUDGE**,
      [`docs/spec-rom-gate-judge.md`](docs/spec-rom-gate-judge.md).
      🔴 **AND THE FILED ROUTE WAS THE WRONG ONE.** A negative `ds` never produces a
      partial file — measured three source shapes, **all 0 bytes** — so that route
      was already closed. The reachable route is a **short assembly**: comment out
      `sub/sub.asm`'s final `ds $8000 - $, $FF` and pasmo emits **30444 B**,
      `pad_rom` invented the missing **2324** and printed a line indistinguishable
      from a healthy build, `make basic-reloc` rc 0, `subrom-acceptance` PASS. Also
      **74** such `ds <fixed> - $` sites in 8 files, not "at least three" —
      **68 of them under `disk/`**. Fixed: padding is now **opt-in** (`--pad`);
      every live caller measured **exact** (sub 32768/32768, disk 16384/16384,
      sub-unguarded 32768/32768), so the rule has zero slack.
      🔴 **AND K3 FOUND THE REAL DEFECT: a refusal that leaves the bad artifact on
      disk is DEFEATED BY RUNNING `make` TWICE.** First `make` refuses and leaves
      the 30444-byte file with a fresh mtime; the second says *"up to date"* and the
      chain passes at rc 0. **Same for D-P0BASE's one-day-old empty-input refusal**
      (0-byte artifact survives its own refusal). Closed with **`.DELETE_ON_ERROR:`**
      — one line, covering every rule in the Makefile. ⇒ **ask of any new refusal:
      what does the SECOND `make` do?**
      (b) 🔴 **`tools/check_kwtable_identity.py` PRINTS ITS OWN DENOMINATOR AND DOES
      NOT JUDGE IT.** On the all-`$00` sub.rom above it reported
      `OK: … the sole source (1 B)` against **1041 B** on a healthy tree. It needs a
      lower bound on the table size, falsified by shrinking the table.
      ✅ **DONE 2026-08-05 — D-ROMJUDGE.** 🔴 **A LOWER BOUND IS THE WRONG SHAPE**:
      one flipped byte moves the reported size **UP**, 1041 → **6140 B**, and a floor
      passes that ([[one-sided-bound-passes-a-runaway]] one slice later). The match
      is **EXACT** — size **and** `sha256`, pinned at `9bfcfb9`, a control that must
      keep matching. The walk is now **bounded** (an all-`$FF` image used to die of
      an `IndexError`, not a judgement), and the **`RELOC.rom` argument, which was
      read and never used**, became a real content check: the table's bytes must
      occur **0** times in the main image and **exactly 1** in the sub image — the
      gate's own "single-copy" name, finally measured.
      ⚠️ **AND IT STILL CANNOT CLOSE (a).** The table is **1041 of 32768 bytes
      (3.2 %)** at `$2CD2`, so a truncation at 50 % **or** 99 % leaves it intact and
      it reports its healthy 1041. Measured: **5 of 6** corrupted sub.roms passed the
      whole chain at rc 0 before this. The blind window for a short `sub.rom` is
      exactly the trailing pad length, **2324 B** — below that no gate anywhere can
      see it, which is why the length question is answered in `pad_rom`.
      🔴 **(b) ALSO FOUND A LIVE FALSE NEGATIVE IN (d)'s ONE-DAY-OLD FIX**:
      `subrom-inttest` on an **entirely-`$FF`** sub-ROM reads `delta = 57` — inside
      the new `1..64` band — and **PASSED**. `DELTA_MAX` was sized from a *partial*
      pad (255); a *total* pad reads 57. Fixed by asserting the **precondition** the
      harness already had and was discarding: **which capture path fired** (`bp` =
      the tenant returned, `net` = the 12 s safety net). Falsified both ways in one
      run each. Its comment's claim that the delta *"stays 0"* on that path is also
      wrong — a runaway `rst 38h` walks the stack and lands a **stack byte** in the
      result cell.
      ✅ **DONE 2026-08-05 — D-DSKJUDGE**,
      [`docs/spec-rom-gate-diskrom.md`](docs/spec-rom-gate-diskrom.md).
      🔴 **THE GATE IS DECLINED, MEASURED — and the filed claims were RIGHT but
      pointed at the wrong risk.** "No content-reading gate at all" is true of the
      HOST side (zero tools read `build/disk.rom`'s bytes and judge them; one reads
      all 16384 and only fingerprints them, `basic_probe_kwsweep.py:433`) and
      **irrelevant**, because `install-repack-machine.py` writes its absolute path
      into slot 3-1 and **four gate families execute every byte**. Corruption ×
      gate, six images: **6 of 6 caught**, every one by at least two gates — the
      inverse of D-ROMJUDGE's sub.rom result (5 of 6 passed at rc 0). `probe` is a
      DSKIO instrument (red on a flipped `$4010`, green on a flipped `$5006`);
      `bdos-acceptance` is the deep one (the only gate that catches a displaced
      `$5006` SNEXT, and the only one that catches a 43-byte truncation of
      `conout_emit_e`). **"68 of 74 `ds` sites" is confirmed exactly and is not a
      risk**: all 68 have positive slack (min **1 B**, max 3464 B) and a pad is
      SELF-ANCHORING — a body that grows shrinks the pad, and one that overruns
      gives a negative `ds` → 0 bytes → `pad_rom` EMPTY refusal. Falsified on the
      **disk** rule specifically, each knife run **twice**: short assembly → rc 2 +
      `Deleting file build/disk.rom` both times; negative `ds` at the tightest pad
      (`$4C29`, 1 B) → `pasmo` **exit 0**, **0 bytes**, refused both times. The one
      producer-blind edit — deleting a pad LINE, which displaces `snext` `$5006` →
      `$4FBB` while `pad_rom` still reports `16384 (exact)` — is caught by
      `bdos-acceptance` (10/12, the two dir-search captures MISALIGNED). Blind
      window for a short `disk.rom` = the trailing pad = **2 B** (vs sub.rom's
      2324); the image is full to its ceiling.
      🔴 **AND THE MEASUREMENT FOUND A LIVE FALSE NEGATIVE, in a gate nobody had
      named: `make fat-error-acceptance` reports `ALL PASS 8/8` on an entirely-`$00`
      `build/disk.rom`** — and on all five other corruptions. **Red in 0 of 6.** The
      battery's expected observable is an ERROR, so a dead disk subsystem satisfies
      every row for the wrong reason, and the directory check passes too (a machine
      that cannot write cannot create `NOSUCH.DAT`). ⚠️ **The probe's own comment
      already named this class and closed one INSTANCE of it** — D-APPMISS found it
      running with no disk mounted and fixed it by mounting one; but a dead disk
      ROM, an unhooked HPHYD and a `pageenv` regression all answer `load error` too.
      Fixed with the **PRECONDITION** the harness never had: a first batched row
      `FILES"A:HI.TXT"` that must print POSITIVE text (`HI` + `TXT`, not
      "no `load error`" — a broken tail returns SILENTLY, so absence-of-error is
      what a broken build reads as). Falsified both ways: real control on all-`$00`
      → **rc 2, "NOT MEASURED (precondition failed)"**; K2 (emission + call site
      intact, only `ctl_ok` gutted) → **rc 0, ALL PASS**, reproducing the defect
      exactly. **rc 2 ≠ rc 1**: the instrument was broken, not the disposition.
      Also DELETED: `tools/build_patches.py`'s `ensure_basic_rom()` +
      `_build_page1_retired()`, unreachable since the 2026-07-29 lean retirement —
      and it **would have failed if it ran**, padding a now-22510-byte
      `basic/main.asm` to the retired lean 16384. ROM-neutral, proved by hash (all
      six `build/*.rom` byte-identical to `fd58b3a`); dead-code seeds unmoved at
      **285**/**102**.
      ✅ **DONE 2026-08-06 — D-CITEJUDGE**,
      [`docs/spec-audit-citations-gate.md`](docs/spec-audit-citations-gate.md).
      The follow-up item this slice filed, and **two of its four claims were
      wrong.** 🔴 **The gate had been red for 144 commits, turned by `6f8ac0f`
      (2026-07-27), not by `40647bd`** — measured by walking *each commit's own
      tool over its own tree* across all **761** commits of the tool's life: red
      in **268 of 761 (35 %)**, five separate reds, the longest 90 commits, and
      **every green return came from a human happening to run it**. 🔴 **Check 1's
      precision over that whole life is 0 of 4** — all four findings it has ever
      produced are the same false positive, `byte[- ]?cop` matching across the
      boundary of a *qualified* `byte` ("a 65536-byte copy", "record/byte copy
      loop", "an independent 34-byte copy", "(18-byte copy)"). Two of them were
      already "fixed" once by REWORDING the prose (`4c14006`, 2026-07-04) and the
      class came straight back. So the filed *"(i) looks like a false positive"*
      is right and its reason is wrong: the distinction is not own-code-vs-
      reference (semantic, out of a regex's reach) but **lexical**, and one
      lookbehind decides it — `(?<![\w/-])byte[- ]?cop`, 99 → 96 token hits, 2 → 0
      affirmative, all six genuine-derivation forms still caught. 🔴 **And the
      denominator was blind to its own subject: 49 of 116 shipped first-party
      asm/inc files were scanned — the whole `sub/` tree and 30 shared `.inc`
      bodies were outside it**, not deliberately but because `sub/` was created a
      week *after* the scan list was last edited, and nothing recorded it. Widened
      to 116; check 4 also picks up `probes/**/*.asm` (0 findings). 🔴 **A second
      rule defect of the same shape, found by writing the fix:** the fixed
      45-line attestation window reported 9 files as unattested that carry a
      proper `CLEAN-ROOM:` line at lines 46–78 of their own header — measure the
      header BLOCK, not a magic 45, and 9 of 24 findings vanish without editing a
      file. 15 attestations written (2 of them into the GENERATORS, since the
      `.inc` would be overwritten by the next `make`). 🔴 **The filed *"the reason
      it is not in the corpus is not recorded anywhere"* is also wrong** — it is
      recorded twice, *"run it on demand / in CI"*, and both clauses are false:
      `ci.yml` did not run it and is `workflow_dispatch`-only. Now a step of
      `make basic-reloc` (0.27 s, beside `check_dead_code.py`) and of CI. The tool
      gained the two things that separate "clean tree" from "blind instrument",
      both **exit 2** not 1: a **rule self-test** pinned to the four historical
      false positives, and a per-target **file-count floor**. K2b/K5b are the
      controls — with either removed, a fully gutted rule and a 37-file-smaller
      sweep both report **exit 0 and "clean"**. ⚠️ K4 came back GREEN first and
      had not cut (that header attests TWICE, lines 56 and 61); ⚠️ and the knife
      script's `git checkout --` cleanup **restored from HEAD and destroyed the
      slice's own uncommitted tool edits**, so three knives silently scored the
      OLD tool. ROM-neutral, proved by hash (all four `build/*.rom` byte-identical
      to `0a9bd89`); dead-code seeds unmoved at **285**/**102** despite prose added
      to three files under `tools/`.
      ⚠️ **STILL OPEN, deliberately: pad-only damage stays invisible.** 9543 of
      `disk.rom`'s 16384 bytes (**58.2 %**) are `$00` pad in 252 runs; a corruption
      confined to them is caught by nothing. Closing it needs a whole-image digest,
      which would pin the ROM against every legitimate `disk/*.asm` change — every
      `ds`-anchored ROM here is *supposed* to move when its source moves.
      (c) ⚠️ **the three probe entry addresses stay HARDCODED** —
      `basic_probe_subrom_boot.py` (`$0040`), `basic_probe_subrom_inttest.py`
      (`$0049`), `basic_probe_graphics_floor.py` (`$0058`). They inject raw bytes
      into a bare machine deliberately, so deriving them from `sub/equates.inc`
      needs its own falsification. All three ARE now scored — note that the third
      is scored by **`graphics-floor-acceptance`**, NOT `graphics-acceptance`
      (which reaches the tenant through the symbolic main stub and is blind to a
      hardcoded probe address; D-P0BASE's K4a knife failed to cut until re-aimed).
      (d) 🔴 **`subrom-inttest` had a live FALSE NEGATIVE**: its assertion was
      `delta >= 1`, and with the CALSLT pointed at `$FF` pad it read
      `delta = 255` and **PASSED**. Its docstring claimed "there is no storm-or-hang
      path that still reports delta >= 1". FIXED here (`DELTA_MAX = 64`, measured
      28/28/28, falsified both ways) — recorded because it is the sixth filed
      justification checked in this arc and the sixth found wrong.
      🔴 **`tools/carve_scout.py` HAD THE SAME BLIND SPOT D-PINDATA FIXED IN ITS TWO
      SIBLINGS**, and it was a live wrong verdict, not a theoretical one: it graded
      `basic/playsvc.asm` **`page-0-tenant CLEAN`, 0 escapes** while
      `basic/playsvc.asm:59` does `ld hl,htimi_guard` (`$3C7E`, main low region) —
      the same shape as the `ld hl,zkey_hook` reference that made the review build a
      data-aware closure in the first place. It now reuses the SHIPPED pass
      (`build_datagraph`/`data_targets`) and a direct data escape downgrades the
      verdict to CONDITIONAL, because a table can move with the cluster and a HOOK
      ADDRESS cannot. Falsified both ways: playsvc CLEAN -> CONDITIONAL, and
      `parse_lineno` CLEAN -> CLEAN (the green control), three `NOT
      page-0-evictable` sets unchanged.
      🔴 **A KNIFE CAME BACK GREEN AND THE GREEN WAS THE FINDING.**
      `check_tenant_closure --page1` cannot see a sub tenant calling a **main-only**
      page-1 label (`call new_prog`): the closure grew 522 -> 523 so the edge WAS
      walked, but `new_prog` is absent from `build/sub.sym` so it is dropped at
      classification. **The ASSEMBLER is the gate for that case** (`ERROR: Symbol
      'new_prog' is undefined`), the same division of labour as `disk_putword` in §4.1
      above, arrived at from the other side and previously unwritten. A name that
      exists on BOTH sides (`call skip_spaces`) IS caught by the walk.
      ⚠️ **RANK 4 IS NOW COSTED AND THE TIER IS THIN.** A per-label closure sweep of
      all of page 1 leaves no other candidate that is both single-entry and free of
      interrupt/gate hazard: `play_service` (217 B) runs from H.TIMI (already rejected
      in `sub/beep.asm`'s header), `fat.asm`+`field.asm` (193 B) needs 9 stubs AND
      reaches a PAGE-1 tenant, `trap_return_check` (78 B) is measured in jiffies by
      T4/T5. The structural reason will not change: every statement-shaped entry
      reaches `eval` -> the float pack, every printing path reaches `pchar` -> CHPUT.
      ⚠️ **THE DEAD-CODE SWEEP'S SEED SET MOVES ON PROSE, AND `tools/` WAS TOO NARROW
      A FILING.** `external_names` scans `sub/` too, comments included: naming
      `fatprim_bounce` and `trap_return_check` in `sub/lineno.asm`'s header — while
      explaining why they were REJECTED — seeded both, and the main seed count went
      284 -> 285. Nothing masked (0 dead before and after). Widens the D-PINDATA
      filing below; still unfixed.
      Closed as answered: the 473 B duplication tax (**457 B contract-forced**), the
      split/ABI/three-gates question (**leave them alone** — the page-0 walk's vacuous
      pass is enforcement, not absent coverage), and merging the two regions (never on
      the table — `$4000` is a hardware contract).

      **Original entry, for context.**
      ✅ **S3 IS DONE, so this is UNBLOCKED**: the source now reads with no
      `IF ROM_BASE` wrappers obscuring which region anything is in.
      🟢 **FREE CARVE ALREADY IDENTIFIED, MEASURED, AND DELIBERATELY LEFT FOR THIS
      ITEM** (S3 had to stay byte-identical, so it could not be taken there):
      [`basic/vars.asm`](basic/vars.asm)'s `var_get_key` and `var_set_key` have
      **ZERO callers** anywhere in `basic/` or `sub/`, and `var_find` is called only
      by those two. They are the retired lean build's int-only fixed-pool scalar
      store; shipped scalars live in the contiguous chain the ARY sub-ROM tenant
      manages (arrays slice-4b). Their only remaining consumer was
      `tests/test_vars.py`, which S3 ported off them. **pasmo has been printing
      `Var var_get_key is never used` all along** — the finding was sitting in the
      build log, unread, which is its own lesson about warning noise (~230 lines of
      it). `VARTAB` / `VARENTSZ` / `VARSLOTS` in `sysvars.inc` are likewise read by
      nothing; `VAREND` must STAY (cells above it are placed relative to it), and its
      128-byte span `$E1C0..$E240` is freed RAM. **Measure the ROM saving before
      assuming it is large** — these are small routines, and page 1 is the 7 B wall.
      🔴 **THE FRAMING MEASUREMENT: the main ROM is jammed shut next to 7411 B of
      unused sub-ROM.** Measured at `4cdb69b`:
      | region | free |
      |---|---|
      | main low `$2812-$3FFF` | **0 B** (hard wall) |
      | main page 1 `$4000-$7FFF` | **7 B** |
      | sub-ROM page 0 `$0000-$3FFF` | **4054 B** |
      | sub-ROM page 1 `$4000-$7FFF` | **3357 B** |
      (⚠️ the sub-ROM pads with **`$FF`**, not `$00` — `ds $4000-$,$FF` /
      `ds $8000-$,$FF` in [`sub/sub.asm`](sub/sub.asm); a trailing-**zero** scan
      reports 0 B free and is WRONG.) **The structure is not full, it is
      UNBALANCED** — 22.6% of the sub image is unused while every main-ROM slice
      is costed against a 0 B wall.
      **What is NOT on the table: merging the two main regions.** The `$4000`
      boundary is a hardware contract, not an artifact — `CALSLT` switches only the
      called page, so a sub-ROM page-1 tenant runs with main page 1 switched OUT
      (callees must be `< $4000`) and a page-0 tenant runs with main page 0 switched
      OUT (callees must be `>= $4000`); `keytrap.asm` is low-region because the
      `$0038` ISR can fire while a page-1 tenant owns page 1. All three are already
      encoded in [`tools/check_tenant_closure.py`](tools/check_tenant_closure.py)'s
      walks, which are the FEASIBILITY ORACLE for this review — not the comments.
      **What IS on the table**, in scope order:
      (1) separate **CONTRACT-FORCED** placements from **PRESSURE-PLACED** ones.
      `main.asm`'s own comments repeatedly say a file "lands in the reclaimed low
      region rather than page 1 (page 1 is otherwise full to $7FFF)" — that is
      packing pressure, not a contract, and the two classes have never been
      separated systematically;
      (2) rank candidates by **bytes freed in the constrained region per resident
      byte spent**. ⚠️ **7411 B of headroom is NOT 7411 B of relief** — every
      eviction leaves a resident trampoline, and the arc history shows cost is
      dominated by SITING, not substance (`docs/`… D-FCH S-FCH-1: 43 -> 9 -> 5 B
      for the same fix). Every eviction so far was costed ONE AT A TIME (CIRCLE
      542 B, FAT shim +367 B, D-MSGENC, D-FCH); none against a known budget;
      ⚠️ **WEIGH DE-EVICTION EQUALLY (user, 2026-07-29).** The review must run in
      BOTH directions, and the reason is not symmetry-for-its-own-sake: a small
      tenant can cost MORE resident bytes than it saves. Its resident footprint is
      trampoline + dispatch-table entry + argument marshalling, which for a small
      routine can exceed the routine itself — so **the cost curve is not monotonic
      in size, and some existing tenants may be on the WRONG SIDE of it.**
      De-evicting those FREES main-ROM bytes (the trampoline goes) while shrinking
      the tenant count, the resident-ABI import list and the closure-gate surface —
      i.e. it is the one move that buys space and simplification together.
      Treat "should this be resident?" as the question for every routine on BOTH
      sides of the slot boundary, never as a one-way eviction hunt;
      (3) interrogate the split itself — whether the sub-ROM's page-0/page-1 tenant
      partition, the resident-ABI import (`tools/gen_resident_abi.py` ->
      `sub/basic-resident-abi.inc`) and the three closure gates could be unified or
      simplified.
      Output: a spec-ready candidate table with evidence per row. **No code changes
      in the review itself.**

- [ ] **REGIONALISE THE REPACK BUILD** (filed 2026-07-29, S2 of the lean
      retirement — user answer B: "note it, revisit later"). The shipped BASIC
      patch `zerobas-main-eu.ips/.bps` is **EU-only by construction**:
      [`tools/build_repacked_cbios.py`](tools/build_repacked_cbios.py) applies
      `cbios-repack/eu-drop-statements.patch` and reads
      `derived/bin/cbios_main_msx1_eu.rom`. The retired lean splice was a page-1
      overlay and so was region-universal — `make machines` used to write a
      `_BASIC`/`_BASIC_DISK` pair for all four MSX1 C-BIOS regions (intl / BR /
      EU / JP) and now writes one EU pair. **This is a real coverage loss, on
      record rather than silently absorbed.** The `_TAPE` machines carry no BASIC
      and stay region-universal, so the tape corpus is unaffected. Judged nominal
      for now: these are C-BIOS *region* variants, not hardware the project
      targets, and the CF-3300 oracle plus every standing gate already run
      EU-only. Revisit if a BR/JP user turns up, or when the repack tooling is
      next opened. Measured: [`docs/spec-lean-retire-s2-switch.md`](docs/spec-lean-retire-s2-switch.md) §2.1.

- [x] **RETIRE THE LEAN 16 KB CART — ✅ DONE 2026-07-29 (S1 + S2 + S3).**
      [`docs/spec-lean-retire-s3-gates.md`](docs/spec-lean-retire-s3-gates.md).
      **S3 deleted all 284 `IF ROM_BASE` directives** (this entry's "311" was a grep
      count including 22 comment mentions and 7 in PROVENANCE.md), the `ROM_BASE`
      symbol, and `basic/main-reloc.asm`. `basic/main.asm` is the sole entry point and
      orgs at an unconditional `BASIC_ORG = $2812`; `$(ROM)` and its rule are gone, so
      `make build/basic.rom` no longer exists.
      ✅ **BYTE-IDENTICAL** across the whole change — `basic-reloc.rom`, `sub.rom`,
      `disk.rom` AND `zerobas-main-eu.rom`. Wall unchanged: **low 0 B, page 1 7 B.**
      🔴 **THE SUB-ROM DEFINED ITS OWN `ROM_BASE`.** `sub/sub.asm` set it to `$2812`
      and pulls in 20 shared `basic/*.inc` files, so a large share of the gates were
      evaluated TWICE. The brief scoped the edit to `basic/` and the gate to the main
      pair; **`build/sub.rom` had to join the byte-identity gate**, and falsifying that
      row (fold `sub/strheap.asm` the wrong way → `strheap_engine undefined`) is what
      proved it was instrumented rather than merely noted.
      🔴 **`make unit-test` WAS MEASURING THE RETIRED BUILD.** `msxtest.Machine`
      defaulted `rom_base=0x4000` — the lean org — so **18 of 54 test files** that
      built `basic/main.asm` without naming a base were asserting against LEAN, right
      through S2's "lean is no longer measured". Fixed the way S1 fixed probe machines:
      **`rom_base` is now MANDATORY**, named at all 74 call sites. Making it required
      found two consumers OUTSIDE `tests/` that no directory sweep would have —
      including **`probes/disk/bas_tokenise.py`, which tokenises the disk acceptance
      corpus's `.BAS` fixtures**, i.e. those fixtures were crunched by the LEAN
      tokeniser. `diskbasic-acceptance` still converges 34/34, now with the shipped one.
      8 of those tests could not just be re-pointed (they asserted on `STRTAB`, the
      fixed VARTAB pool, `[len][bytes]` descriptors, `ERRMARK` for `5/0`, or a
      sub-ROM-evicted routine) — **all 8 ported, 54/54 green.**
      🔴 **THE FALSIFICATION HARNESS WENT RED FOR THE WRONG REASON, TWICE**, both
      silently: `git checkout --` restored files to PRE-FOLD HEAD rather than to the
      folded tree, and `make build/basic-reloc.rom` is a **NO-OP FOLLOWER** target (the
      grouped-target workaround), so removing only the `.rom` left `@:` to run and the
      missing file read as "build failed". **A red falsification row reads as success**
      — the fix was a GREEN control row (comment-only edit → hash unchanged) plus making
      every row report its own reason.
      🔴 **F-R CAUGHT A SUCCESSOR THAT DOES NOT EXIST.** `basic_probe_readdata.py` was
      named from memory; the real successor is `tests/test_control_flow.py` — which this
      slice had to fix first. Retiring against a successor that was itself testing lean
      would have been a coverage loss dressed as a consolidation.
      Probes: **14 ported** to the repack machine, **6 retired** (`_data`, `_loops`,
      `_controlflow`, `_vdpio`, `_screen`, `_cload`) against verified successors. The S2
      margin hazard was **measured** (VG-8020 = 2, repack = 1) and applies only to
      VG-8020↔C-BIOS moves; no ported VRAM reader crosses that boundary, so no `_margin`
      fix was needed. The cassette corpus was ported but NOT end-to-end run (§6.1).
      Comment sweep (user chose targeted): the "388 lean mentions" figure was wrong —
      `grep -i lean` matches **"clean"**, and this tree says *clean-room* constantly.
      Real count **207**, swept to ~13 deliberate historical ones. `basic/PROVENANCE.md`
      got an APPENDED dated entry; its 7 in-history mentions are deliberately NOT
      rewritten (a provenance entry describes a date, a source comment describes the
      code beside it).
      ⚠️ **CARVE FOUND, NOT TAKEN:** `vars.asm`'s `var_get_key` / `var_set_key` have
      **ZERO callers**, and `var_find` is called only by those two — the retired build's
      int-only fixed-pool store, which pasmo has been reporting as unused all along.
      `VARTAB` / `VARENTSZ` / `VARSLOTS` are read by nothing. Left alone because S3 was
      byte-identical by contract; **folded into the ROM REGION STRUCTURE REVIEW below.**
      Lean's final hash, for the record:
      `defd6201b78bc922e3ba4db66134d2527c76ad9d81105440a6d667f12511be90` (16384 B). No
      tag, no frozen artifact — a future lean build is CHERRY-PICKED from the finished
      tree (user DIRECTION), not resurrected from that hash.

      **Original entry, for context.** It cannot be the
      charter target and has not been one for a long time: it excludes SEVEN
      whole source files (`str-engine`, `input`, `float`, `float-arith`,
      `arrays`, `keytrap`, `subromcall`) — so no strings, no `INPUT`, no floats,
      no arrays, no error codes, no KEY traps — costs **311 `IF ROM_BASE`
      gates** (`grep -rn 'IF ROM_BASE' basic/ | wc -l`; this entry said 276, it
      has drifted up by 35), and has **~68 free bytes** of its 16384. In an
      emulator both forms are equally easy to run and the repack build is
      strictly better.
      ✅ **S2 DONE 2026-07-29** — [`docs/spec-lean-retire-s2-switch.md`](docs/spec-lean-retire-s2-switch.md).
      **Lean is no longer built, shipped, or measured.** `zerobas-msx1.ips/.bps`
      are DELETED; the shipped BASIC is `zerobas-main-eu.ips/.bps` (user decision
      A1). `diskbasic-acceptance` IS the repack gate now (34/34) and
      `-repack` is an alias; `check_reloc.py`'s frozen-baseline check #4 and
      `LEAN_SHA256` are gone, **checks 1–3 and the `__MEAS_LOW_END`/
      `__MEAS_PAGE1_END` wall readout survive untouched** (falsified by
      corrupting `basic-reloc.rom` three ways, and the sym argument is now
      REQUIRED — an optional sym is how a wall readout silently stops printing).
      `make probe` runs `basic_probe_print.py --zb-machine` instead of the lean
      cart. `make all` no longer needs a C-BIOS checkout; `make release`
      regenerates the shipped pair.
      🔴 **MEASURED, and the source said otherwise:** a release machine with slot
      3-2 empty does not boot AT ALL (garbage screen, no prompt) — BASIC reaches
      its sub-ROM tenants during startup, so `--sub-rom` now defaults ON and a
      missing file is a hard error. The tenant map had read as "loses those verbs".
      ⚠️ **The lean build is now UNGATED** — `make build/basic.rom` still
      assembles for the ~20 historical `--cart` probes, but nothing asserts it.
      **S3 (next): delete the 311 `IF ROM_BASE` gates + the `ROM_BASE` machinery,
      collapse `main-reloc.asm` into `main.asm`, and port/retire that probe
      corpus.** Gate for it: `build/zerobas-main-eu.rom` byte-identical across the
      change.
      ⚠️ **S3 MUST STAY BYTE-IDENTICAL — do NOT fold any placement change into
      it.** Byte-identity is the strongest gate available for a 311-site mechanical
      edit, and moving even one routine destroys it. The structural rebalance is a
      SEPARATE item (see ROM REGION STRUCTURE REVIEW below), deliberately sequenced
      after S3 so it reads source with no `IF ROM_BASE` wrappers obscuring which
      region things are in.
      ✅ **S1 DONE 2026-07-29** — [`docs/spec-lean-retire-s1-explicit-machine.md`](docs/spec-lean-retire-s1-explicit-machine.md).
      Both gates now NAME their machine (`LEAN_MACHINE` / `REPACK_MACHINE`) and
      assert it with `--expect-build`, so the two can no longer collapse into one
      test; all 38 probe fallbacks are GONE (the machine is mandatory); the runner
      gained zerobas-side vacuity guards §3.1.3–§3.1.6. Retiring lean is now a
      two-line Makefile edit, not a hunt through 38 files. **It also found a live
      defect: [`disk_probe_format.py`](probes/disk/disk_probe_format.py) parsed
      `--machine` and threw it away, so CALL FORMAT had NEVER run on the repack
      build** — and the wiring guard passed it because the env-var name appeared
      in its source.
      ⚠️ **NOT A BLOCKER (dissolved by the DIRECTION below):**
      [`tools/check_reloc.py`](tools/check_reloc.py) proves the relocated image is
      a PURE RELOCATION by comparing the lean ROM against a frozen baseline. A
      DERIVED build needs no anti-drift proof, so this needs no replacement — but
      its other three checks and the `__MEAS_LOW_END`/`__MEAS_PAGE1_END` wall
      readout must survive, since every slice is costed against them.
      **DIRECTION (user, 2026-07-29): if a lean build is ever wanted again, CHERRY-
      PICK AND ASSEMBLE IT FROM THE FINISHED zerobas BUILD** rather than keeping a
      second build alive in parallel. This inverts the blocker above rather than
      solving it: the byte-identity baseline exists to prove a build that is
      CO-MAINTAINED never drifts, and a build that is DERIVED on demand does not
      need that proof at all — it is cut from the tree that is already gated. It
      also retires the 311 `IF ROM_BASE` gates as a *maintenance* cost rather than
      a *correctness* one, and it means findings like D-LINEMAX's lean `TOKBUF`
      overrun stop being defects-carried-forward: the derived build would inherit
      the fixed crunch, not the 96-byte one.
      Carry forward, do not fix: the lean crunch overruns `TOKBUF` via
      line-number references (`20 ONAGOTO1,1,1,…` — **57 characters** → 98 bytes
      into 96; 95 characters → 174, over the LIVE `VARTAB`; a variable set
      before it reads back 0). Measured, D-LINEMAX §2.2.

- [ ] **SLIM THE FILE-CHANNEL CONTEXT toward the reference** — ✅ **MEASURED
      2026-07-29; awaiting spec sign-off.**
      [`docs/chancost-cf3300-characterization.md`](docs/chancost-cf3300-characterization.md),
      probe [`probes/disk/diskbasic_probe_chancost.py`](probes/disk/diskbasic_probe_chancost.py)
      (boot-per-case, both machines, reference answers self-checked for drift).
      🔴 **THE ITEM'S OWN CAVEAT IS REFUTED.** It said 267 "cannot be the goal
      for a channel doing FAT12 I/O" because it came from a diskless VG-8020.
      The disk-capable **CF-3300 charges exactly the same 267 B** — linear with
      no intercept across `MAXFILES` 0/1/2/3/4/8/15, non-adjacent points on the
      same slope. **267 IS a valid target.**
      Also measured: the ceiling is **exactly 15** (not "at least"), `16`/`255`
      raise **`Illegal function call`**; the buffers are charged at **`MAXFILES`
      time, not `OPEN` time**; the **string pool is untouched** (`FRE("")`=200
      either side); and `TXTTAB`/`HIMEM` are **constant**, so the carve is
      downward from the top — `FRE(0)` counts to **SP**, which is what moves.
      **267 < 512, so the sector buffer is NOT in it** — the reference shape is
      one *shared* sector buffer plus a small per-channel block, exactly as
      hypothesized.
      **zerobas, measured the same way:** `FRE(0)` = 13875 at `MAXFILES` 0, 1
      AND 2 — **it does not move at all**, because `FCH_CTX $EA00..$EE63` is
      reserved statically whether or not a channel is open. Its 512 B per
      channel is **purely a save copy** of the single global `FSECTOR_BUF`
      (`fch_save_active`/`fch_load_ctx`, [`basic/files.asm:994`](basic/files.asm:994));
      the reference gets the same effect by treating the shared buffer as a
      **cache** — flush on switch away, re-read on switch back.
      **Sizing:** drop the save copy → at `FCH_CEIL=2` the table falls 1124 B →
      100 B (**frees 1024 B**); at `FCH_CEIL=15` (full reference parity) it is
      750 B, still **374 B less than today**.
      ⚠️ **THE ROM COST IS NOT MEASURED** — flush-and-re-read instead of memcpy
      is an unknown-size change to `files.asm` against **9 B** free low / **6 B**
      free page 1. Estimating it from reading code would be a hypothesis, not a
      measurement (D-ARR-C §7a).
      ⚠️ **FREEING PAGE 3 DOES NOT BY ITSELF RETURN PROGRAM SPACE.** `TXTMAX`
      rises only if a page-2 buffer MOVES into the freed window: `TOKBUF`
      (576 B @ `$B700`) and the input line buffer are movable; `DETOKBUF`
      (1280 B @ `$BB00`) does not fit in 1024 B. So the D-LINEMAX refund is
      **partial at best**, not the full 1792 B.
      **FORK RESOLVED (user, 2026-07-29): the fully faithful DYNAMIC mechanism**
      — carve channel blocks out of the pool at `MAXFILES` time, ceiling 15,
      nothing charged for channels a program never asks for, `FRE(0)` moves.
      Spec written: [`docs/spec-basic-filechan-alloc.md`](docs/spec-basic-filechan-alloc.md)
      (**D-FCH**), ⚠️ **awaiting sign-off — no code written.**
      Semantics + error codes now MEASURED too (characterization §9/§10):
      `MAXFILES` **CLEARs variables UNCONDITIONALLY**, even when the value does
      not change (the `sem_same` row is what pins that — the natural reading
      "clears only when it reallocates" is wrong), **closes all channels**, and
      **keeps** the `CLEAR`-set string-pool size. Codes: `MAXFILES=16` → **ERR
      5**, bad channel number → **ERR 52 `Bad file number`**, touching a closed
      channel → **ERR 59 `File not OPEN`**; zerobas raises **ERR 2** for the
      first two and returns **−1** for the third. The whole disk error block
      50–65 is mapped black-box via `ERROR n`.
      ⚠️ **`Bad file number` is NOT trappable on the reference** — with a
      handler installed the other two trap cleanly but this one prints
      `Bad file number in 30` and never reaches it. Pin it, don't "fix" it.
      ⚠️ [`basic/files.asm:332`](basic/files.asm:332) **already comments
      `bad file number`** and jumps to `stmt_error`; six sites do the same.
      ⚠️ **`err_msgtab` stops at 25** — reaching 59 densely is ~100 B against
      9 B/6 B free. S-FCH-2 offers a sparse side-table instead.
      **S-FCH-1 ✅ BUILT + GATED 2026-07-29.** The shared-cache change costs
      **5 B of main page 1, 0 B of low region — NO CARVE** (fits the existing
      6 B with 1 B spare) and frees **1024 B** of page 3 (`FCH_CTX` 1124 → 100).
      The per-channel 512 B save copy is gone: `fat_detach_channel` flushes the
      dirty partial sector in place and `fat_restage_channel` reads it back
      (both sub-ROM, rows 19/20), so `FSECTOR_BUF` is a real write-back cache.
      🔴 **THE COST WAS SITING, NOT SUBSTANCE, AND ONLY BUILDING IT SHOWED
      THAT: 43 B → 9 B → 5 B.** Resident, the detach half cost 43 B (37 over) —
      a carve scouted from that number would have been scouted for a
      requirement **8× too big**. It calls `fat_flush_data_sector`, which was
      ALREADY a sub-ROM primitive, so keeping its caller resident bought
      nothing. The last 4 B came from hoisting ONE IX guard into `fch_select`
      instead of two inside save/load.
      ⚠️ **The IX contract was a live hazard**: those routines had no CALSLT
      before and promise IX/IY survive because `EOF`/`LOF`/`INPUT$` hold their
      token cursor there.
      ⚠️ **The gate was FALSIFIED**: stubbing `fat_restage_channel` to `ret`
      makes `disk_probe_maxfiles`'s interleaved two-channel write return **B's
      bytes in A.TXT** and fail both functionally and vs the CF-3300.
      ⚠️ **Repack-only** — ungated it overran the byte-full lean cart's `$8000`
      ceiling outright; the cart keeps the memcpy path, byte-identical.
      ⚠️ **Left open:** `fch_save_active` ignores the detach's `Cy`. A channel
      switch could never fail before and now can (disk full mid-flush);
      propagating it needs a disposition at every `fch_select` caller.
      **§3.3 ✅ BUILT 2026-07-29 — THE 1024 B IS NOW SPENT, AND IT IS PROGRAM
      SPACE: `FRE(0)` 13875 → 14899** (measured). `LINEBUF` `$BA00`→`$EB00`
      (page-aligned, cursor idiom untouched), `TOKBUF` `$B700`→`$EC00`,
      `TXTMAX` `$B700`→`$BB00`. **Zero ROM cost** — address constants only, so
      page 1 stayed at 1 B free and the lean cart stayed byte-identical.
      Usability CHECKED, not assumed: `CLEAR 200 : DIM A%(7000)` (14002 B, over
      the old 13875) now succeeds with **both ends written and read back**
      (11/22), 889 B still free. A `DIM` that merely succeeds witnesses nothing.
      ⚠️ **`TXTMAX` IS NOW BOUNDED BY `DETOKBUF`, NOT BY FREE RAM** — at 1280 B
      it does not fit the 1024 B window, so `$BB00` is the stop until DETOKBUF
      is dealt with. Of D-LINEMAX's 1792 B, **1024 recovered, 768 still charged**.
      ✅ The ~12 KB string workload D-LINEMAX cost the suite is affordable again
      (the array rows' shrunken payloads were deliberately LEFT — restoring them
      is a separate call, not a silent side effect of a RAM change).
      **§3.2 ✅ BUILT + GATED 2026-07-29 — `MAXFILES` IS NOW FAITHFUL IN
      MECHANISM.** The channel table is CARVED OUT OF THE POOL at `MAXFILES`
      time, immediately below the string-pool floor
      (`min(HIMEM,TXTMAX) − POOLSIZE − MAXF×50`), so **`FRE(0)` moves −50 per
      channel** (14899 at `MAXFILES=0` → 14149 at 15), `FRE("")` stays 200,
      `OPEN` costs zero further, and **`FCH_CEIL` is 15** — the measured
      reference ceiling. `MAXFILES` now also **CLEARs variables
      unconditionally**, the `sem_same` behaviour.
      **Cost: 1 B of main page 1, 0 B of low region, NO CARVE** (measured by
      relaxing the `$8000` guard and reading `__MEAS_PAGE1_END`, then
      restoring). ⚠️ **Page 1 is now at 0 B free** (`$8000` exactly).
      🔴 **THE COST WAS SITING, A THIRD TIME.** The first build overran by 8 B
      and all 8 were `MAXFILES`' `CLEAR` — which is verbatim `ex_clear`'s own
      tail. `jp clr_done` costs the 3 bytes the `jp exec_stmt` it replaced
      already spent, so the `CLEAR` came free. The allocation itself was ~free
      because its whole arithmetic chain (`strheap_varceil` →
      `strheap_floor` → `strheap_ceiling`) was ALREADY sub-ROM.
      **DECISION (user, 2026-07-29): charge 50 B/channel, not the reference's
      267.** A zerobas block genuinely IS 50 B (shared `FSECTOR_BUF` cache), so
      it charges what it uses; padding to 267 would reserve 217 B/channel that
      nothing reads and cost a user 4005 B at `MAXFILES=15` instead of 750.
      ⚠️ **This CORRECTS spec §6**, which asked the gate to assert 267 on both
      sides — the gate asserts the MECHANISM (linear per-channel, ceiling 15,
      both sides) and reports each machine's own constant.
      ⚠️ **THE SLOPE ALONE IS A GATE THAT CAN MEASURE NOTHING, AND THIS WAS
      FALSIFIED, NOT REASONED.** With the array ceilings reverted to
      `strheap_floor` — i.e. the carve REPORTED but not RESERVED — `mf0`/`mf2`/
      `mf15` still read a flawless 14899/14799/14149 while arrays grew straight
      through the channel table. The new two-sided `dim_fits`/`dim_over` rows
      catch it (`dim_over` returned 7777 instead of `Out of memory`); its +400 B
      overshoot is sized against the 750 B of slack the bug creates.
      ⚠️ **AND ONE EXISTING ROW WAS UNMEASURABLE**: `sem_str` typed
      `PRINT A$`, and a cleared A$ (empty line) and an uncleared one (`XY`) BOTH
      score `<none>` in this probe's readout — equal on both sides, PASS
      forever. Now `PRINT LEN(A$)` (0 vs 2) with a `REM` control.
      `make chancost-characterize` is now a real GATE (non-zero on unfiled
      divergence / oracle drift / a flat ladder), 31 cases, 9 filed divergences.
      **S-FCH-2 ✅ MEASURED 2026-07-29 (built all four parts, measured each,
      kept the free one).** Full cost **45 B page 1 + 41 B low region = 86 B**
      against **0 B / 9 B free** — the ~100 B estimate was close this time.
      ✅ **ERR 5 IS LANDED AND COST EXACTLY ZERO**: `gb_illegal` is already the
      ERR 5 raiser and already in page 1, so `jp cc,gb_illegal` spends the same
      3 bytes `jp cc,stmt_error` did. `MAXFILES=16`/`255` now raise **Illegal
      function call** and `err_over` traps **ERR 5** — the gate's filed
      divergences drop **9 → 6**.
      **Breakdown (spec §5c):** ERR 5 = 0 B · ERR 59 (closed-channel EOF/LOF)
      = 8 B page 1 · ERR 52 raiser + 2 message strings + sparse table = 14 B
      page 1 + 41 B low · the sparse lookup in `raise_error` = 23 B page 1.
      ⚠️ **64 of the 86 bytes are MESSAGE DATA + A TABLE WALK** — the most
      evictable shape there is. A page-0 sub-ROM tenant could own it and stage
      the message into the **208 B still free at `$EA30..$EAFF`**, leaving a
      shim; that would cut the resident need to ~35-40 B. **MEASURE THAT BEFORE
      SCOUTING A CARVE** — this arc has three times found the cost was siting.
      ✅ **THE EVICTION IS MEASURED TOO: the carve drops 77 B -> 26 B.** The
      table, both strings and the walk move to the EXISTING string-heap tenant
      as op 19 (no new dispatch index), staging the message into page-3 RAM at
      `$EA30`; the two raisers move to the low region. Result: page 1 20 over,
      low 6 over. Moving the shim down too only trades one wall for the other --
      the total stays 26 B, so ONLY A CARVE closes it.
      ⚠️ **BOTH S-FCH-2 BUILDS ARE COST PROBES: MEASURED, NEVER RUN.** ERR 5 is
      the only part executed and gated. Before any of the rest lands: (1)
      `err_bad_filenum` forces `ONEFLG=1` to reach the abort arm and LEAVES IT
      SET -- if the REPL return does not clear it, the NEXT error force-aborts
      instead of trapping; (2) the ten repointed `jp` sites are unconditional in
      the probe, so the LEAN CART WOULD NOT ASSEMBLE -- landing needs per-site
      gating, or the lean cart retired.
      ⚠️ **THE MEASUREMENT APPARATUS WAS WRONG FIRST AND READ PLAUSIBLY (77 B).**
      Relaxing the low region's guard removes its `ds $4000 - $` pad — and that
      pad is what puts the cartridge header at `$4000`. Without it page 1 slides
      down with the low region and `__MEAS_PAGE1_END` measures BOTH walls. Pin
      the header with an explicit `org $4000`. Corrected: 45 B, not 77.
      ✅ **THE CARVE IS DONE: D-MSGENC LANDED 2026-07-29 (`9a0300d`,
      docs/spec-basic-msgenc-carve.md).** Phrase-encoding the 25 resident error
      messages took page 1 from **0 → 24 B free** and the low region from
      **9 → 68 B free**. S-FCH-2's evicted form needs 20 + 15: **funded, with
      4 B and 53 B spare.**
      ✅ **S-FCH-2 LANDED ALL-RESIDENT 2026-07-29 (spec §5d).** ERR 52 `bad file
      number` and ERR 59 `file not open` are raised and printed by the resident
      ROM. It cost **11 B of page 1 + 59 B of low**, not the 45 + 32 estimated:
      page 1 **24 → 13 B free**, low **68 → 9 B free**, lean cart byte-identical.
      No eviction, no tenant op 19, no `ERRMSG_BUF` staging, no repointed `jp`
      sites — **both §5c blockers dissolved rather than gated.** The gate goes
      31 cases / 6 filed divergences → **39 / 4**, closing `sem_zero`,
      `sem_hinum`, `sem_reopen` and `err_notopen`.
      ⚠️ **AND IT WAS NEVER A DEMOTION.** The scout ran first and returned
      **zero**: page-0 tenants reach *no* main routine at all (709 routines,
      every one sub-local — the only main-side import list in the sub-ROM is
      `sub/basic-resident-abi.inc`, eleven page-1-tenant seeds already below
      `$4000`). Nothing in page 1 is pinned there by tenancy, so the cheap move
      was to site S-FCH-2's OWN new content low and leave existing code alone.
      **A shortfall stated as "N bytes short" invites relocating N bytes; ask
      first whether the NEW content has to be where the estimate put it.**
      🔴 **BLOCKER (2) — the lean cart — was dissolved by aliasing the LABEL,
      not by gating the SITES:** `IF ROM_BASE >= $4000 : oo_fail_bfn equ
      oo_fail_syn`. All six rejects keep their existing 3-byte `jp cc,`, which in
      the lean build assembles to the exact bytes it did before. Zero sites
      gated.
      🔴 **BLOCKER (1) — "ERR 52 is not trappable" — WAS A CONFOUND, and so was
      the ONEFLG forcing built on it.** The `err_badchan` row types `MAXFILES=1`
      BETWEEN the arm and the error, and that statement suppresses the handler
      on the reference. Measured three unconfounded ways on the CF-3300:
      `OPEN…AS #2`, `OPEN…AS #0` and `EOF(1)` on a closed channel ALL trap
      (ERR 52, 52, 59). So both codes go through the shared `raise_error_hl`
      trap decision like every other code and **write `ONEFLG` nowhere**.
      Gate rows `bfn_trap`/`bfn_zero`/`fno_eof` + the `bfn_ctl` two-sided
      control now measure the CODE instead of its neighbours.

- [x] **`CLEAR`/`MAXFILES` inside a run do not suppress an armed `ON ERROR`
      handler** (reference: they do). Found 2026-07-29 while measuring S-FCH-2;
      **✅ FIXED the same day —
      [`docs/spec-basic-onelin-reset-scope.md`](docs/spec-basic-onelin-reset-scope.md).
      Net 0 BYTES** (the disarm MOVED out of `run_prog` into `vars_reset`);
      walls rebalanced low 6 → **0** B free, page 1 5 → **11** B free; lean
      byte-identical. 17 standing gate rows; three rejected builds assembled.
      **THE RULE, MEASURED (14 rows, each trigger unconfounded by an edit):** a
      handler is disarmed **exactly when the variable table is cleared** — `RUN`,
      `NEW`, `CLEAR` (direct-mode *and* in-run, so `MAXFILES`) and **every
      program EDIT**. `DIM`, string traffic, a plain direct statement, a
      `STOP`+`CONT` suspension and a `CLEAR` *before* the arm all keep it. That
      set is `vars_reset`'s five callers, 1:1 — which is why the zero lives
      there and not in `clear_vars` (a program edit never reaches `clear_vars`).
      🔴 **EVERY PREVIOUSLY-FILED ROW WAS CONFOUNDED FOR PLACEMENT** — each typed
      a program line BETWEEN the arm and the trigger, so "the EDIT disarmed it"
      and "`RUN`/`CLEAR` disarmed it" were indistinguishable. Armed LAST, with no
      edit in between: **`RUN` DOES disarm**, so this item's own warning that
      "`RUN` must not disarm" was false.
      🔴 **THE `ONELIN`-INVALIDATION-AT-RELINK MECHANISM THIS ITEM RECORDED IS
      WRONG.** It predicts that only an edit which MOVES the handler line
      disarms; the reference disarms on an **append that moves nothing**
      (`onelin_edit_append`), and on a same-length retype. The trigger is the
      EDIT, not the MOVE.
      🔴 **AND THE THREE `reset_scope_*` GATE ROWS WERE VACUOUS.** Their marker
      was the literal `R<LEAKED>`, which appears in each case's **own source
      echo**: the test read TRUE on every machine, in every build, since the day
      it landed. That is where the false "the reference DOES fire" claim in
      spec-basic-filechan-alloc.md §5d.5 came from — and that claim is what
      steered this item away from the variable-clear rule for a whole arc.
      **A wrong measurement is worse than none: it does not merely fail to
      inform, it actively STEERS.** All three now use the numeric marker and are
      oracle-locked. ⚠️ `NEW` still cannot be isolated (the retype it forces has
      already disarmed the handler) — unchanged, and now moot: `NEW` reaches
      `vars_reset` like everything else.
      Also closed: a **stale-pointer WILD BRANCH** — inserting a line before the
      erroring line moved the handler line, and zerobas followed its stale
      `ONELIN` into the moved text, reporting `syntax error in 4850`, a line that
      does not exist. Marker-wise that row AGREED with the reference while doing
      something far worse; it is now gated on the **abort line number**.
      `chancost-characterize`: 4 filed divergences → **1** (`err_badchan`,
      `mf_disarm`, `clr_disarm` all agree now).

- [x] **`CONT` that runs off the end of the program aborts with a nonexistent
      line number.** ✅ **FIXED 2026-07-29 —
      [`docs/spec-basic-cont-depth.md`](docs/spec-basic-cont-depth.md), 4 B
      (`ld sp,(SAVSTK)` at `ex_cont`), page 1 11 → 7 B free, lean
      byte-identical.** 8 standing `cont_*` rows in `abort-acceptance` (now
      31/31), **six of them "must not change"** — the fix DISCARDS a stack
      frame, so its risk is what else lived there, not whether the symptom
      goes away. Falsified twice: without the instruction `cont_falloff` is red,
      and with the one-character-different `ld (SAVSTK),sp` (anchor here rather
      than restore) it is **still** red. `10 STOP : 20 B=1 : 30 PRINT"…"` then `RUN`, `CONT` — the
      reference resumes, prints, and returns to `Ok`; zerobas prints, then
      reports `Illegal function call in 3346`. Found 2026-07-29 by D-ONELIN's
      `stop_cont` CONTROL (no `ON ERROR` anywhere — `ONELIN` is 0 throughout),
      and **verified PRE-EXISTING at `6ac2285`** against a parked pre-fix build.
      **✅ MECHANISM CHARACTERIZED 2026-07-29** (17-case battery, both machines,
      boot-per-case) — and it is the [[abort-chain-returns-into-caller]] class,
      a `ret` that only unwinds correctly at ONE depth:
      **`ex_cont` re-enters the run loop with a bare `jp rp_lp` from STATEMENT
      depth**, i.e. from inside the loop's own `call exec`, leaving a stale
      return frame beneath it. `dl_cmd` (the clean template) instead `jp rp_exec`s
      at REPL depth after `ld (SAVSTK),sp`, so ITS exit `ret` unwinds to the
      prompt. From `ex_cont`'s depth the exit `ret` lands back INSIDE the loop
      body, which then reads `ENDFLAG`:
      * exit via `END` -> `ENDFLAG`=1 -> the re-entry `ret`s again immediately.
        **Clean BY LUCK** (`x_cont_end` measured clean on both machines).
      * exit via the `$0000` link -> `ENDFLAG`=0 -> falls through to the
        next-line advance with `HL` still on the end marker -> parses garbage ->
        `Illegal function call in <the word after the marker>`.
      Controls that pin it: `x_run_tail` (plain `RUN`, clean) and `x_cont_goto`
      (a direct `GOTO` into the program, clean — dl_cmd's path is the one that
      works). ⚠️ A hypothesis that the `END` exit derails too, onto a benign
      byte, was **REFUTED by measurement**: `40 END:PRINT…` does NOT run its
      second statement after a `CONT` (`d_cont_after_end` agrees on both).
      Likely fix: `ld sp,(SAVSTK)` before the `jp rp_lp` (4 B, page 1) —
      `dl_cmd` sets `SAVSTK` for the CONT line itself, so it is fresh and is
      exactly the depth the loop's exit `ret` needs. **Not built; needs a spec
      + sign-off, and the two siblings below probably share it.**

- [x] **A stale `ONEFLG` survives the return to the REPL, so the NEXT error
      force-aborts instead of trapping.** Raised as S-FCH-2's open question by
      spec §5c; answered empirically 2026-07-29 **and ✅ FIXED the same day** —
      [`docs/spec-basic-oneflg-reset-scope.md`](docs/spec-basic-oneflg-reset-scope.md).
      **11 B (page 1 13 → 5 B free, low 9 → 6 B free), no carve, lean
      byte-identical.** The filed row was ONE of **six** divergent rows in a
      10-case battery; the fix closes all six.
      **The rule, measured both ways:** the reference clears `ONEFLG` on **any
      abort** — run-mode *and* direct-mode, even while a run is merely suspended
      — and on **any run TERMINATION** (`END`, running off the end); it does
      **NOT** clear on a `STOP`/Ctrl-STOP **SUSPENSION**, because `CONT` has to
      be able to resume *inside* the handler. Three sites: `fre_abort_low`
      (+3 B low), `ex_end` (+3 B), `rp_lp`'s `$0000`-link exit (+5 B — free,
      because `A` already holds 0 on that arm).
      🔴 **THE CHEAP FIX WAS 8 B AT ONE SITE AND IS THE WRONG FIX.** Clearing at
      the run-loop exit gated on `CONTVALID` reproduces every measured row — but
      only because zerobas's `END` leaves no CONT resume point, which is *itself*
      a divergence (see the new item below). A fix resting on a known bug
      regresses silently the day that bug is fixed. **Ask what the reference's
      RULE is, not which cheap predicate happens to fit today's rows.**
      🔴 **The over-clear guards are the load-bearing half of the gate.** Seven
      standing rows in `basic_probe_error_trap.py`; five say "must clear" and
      **two say "must NOT clear"** (`oneflg_keep`, `oneflg_suspend_resume`). A
      build with the rejected prompt-placement was assembled ON PURPOSE and
      passed all five and failed exactly those two. Each of the three sites was
      also deleted individually: **the site→row map is 1:1.**
      ⚠️ Round 1 of the battery scored a force-abort as a TRAP: the marker
      `PRINT"R<TRAP>"` matched its own **SOURCE ECHO**. Round 2's `PRINT"R<";1;">"`
      cannot collide (echo → `";1;"`, output → `1`).
      ⚠️ The first over-clear build **failed to assemble** (a 5 B insert pushed
      an unrelated `jr` out of range) **and the probe ran anyway, on the stale
      machine** — five red rows of pure noise. Chain build and probe with `&&`.

- [x] **ERR 21 `No RESUME` is never raised.** Found 2026-07-29 by the D-ONEFLG
      battery's c3b row, not aimed at; characterized 2026-07-29.
      **✅ FIXED 2026-07-31 as D-ERR21 —
      [`docs/spec-basic-err21-no-resume.md`](docs/spec-basic-err21-no-resume.md).**
      **+4 B page 1 (30 → 26 free), +57 B low region (80 → 23 free)** — both
      estimates exact to the byte, and no `jr` span broke this time.
      Gate **126/126** (`make error-trap-acceptance`, 24 new `e21_*` rows +
      `oneflg_falloff` upgraded from one zb-only row to a two-machine text
      differential), seven falsification builds.
      🔴 **THE FILED CHARACTERIZATION WAS WRONG IN TWO PLACES AND A THIRD DEFECT
      WAS HIDING BEHIND THE PLACEMENT QUESTION.**
      **(a)** The message and `ERL` name the **LAST EXECUTED LINE**, not the
      handler's — `in 110` with the handler at 100, `in 200` through
      `100 GOTO 200`. The filed `21 , 100` was taken on a program whose handler
      line WAS its last line, so the two readings were never discriminated.
      Falsification **F3 built the filed design** (`CURLINE := ONELIN`) and it
      prints `in 100` / `21 , 100` on every row — **the wrong implementation
      reproduces the filed measurement perfectly.**
      **(b)** The abort resume point is **NOT free from `ra_abort`**: `CONT`
      after this abort reprints NOTHING, so the point is the FALL-OFF position,
      not `SAVTXT`. The raiser records it itself, before it moves `CURLINE`.
      ⚠️ **F4 was caught by whole-screen occurrence COUNTS, not by the tail** —
      both tails were byte-identical to the want, because the re-printed marker
      lands after the `CONT`, outside the `RUN`-anchored tail.
      **(c)** D-ONEFLG **site C was causing a live defect nobody had measured**:
      a typed line ends by falling through `dir_line`'s own `$0000` link into
      this very exit, so a benign `PRINT 1` at a `Break in <handler>` prompt
      killed the handler context and the next `CONT` said `resume without error`.
      Deleting site C — which this slice does anyway — fixes it.
      ⚠️ `err_msgtab`'s entry 21 was a **HOLE**, not a working entry, so
      `ERROR 21` printed `unprintable error` too; wiring it is 0 B.
      🔴 **F6 CAME BACK GREEN AND THAT WAS THE FALSIFICATION'S FAULT.** It
      restored site C *after* the new `ONEFLG` test, where `A` is 0 by
      construction — a no-op. F6b restored its EFFECT on the arm that mattered
      and bit as designed. **A green falsification is a claim about the patch
      first and the code second.**
      ⚠️ `build/sub.rom` changes legitimately: the 57 B of low region shifts
      `vars_reset`, a resident-ABI address the sub-ROM links against.

- [x] **Probes streamed audio on every boot — `sound_driver null` had reached
      only ONE of 70 launch sites.** The 2026-07-30 fix landed in
      [`probes/disk/omsx_session.py`](probes/disk/omsx_session.py) alone; the
      other 69 — including [`probes/lib/omsx_repl.py`](probes/lib/omsx_repl.py),
      which EVERY BASIC acceptance gate boots through — still opened a real
      CoreAudio device and streamed. **✅ FIXED 2026-07-31, all 70.**
      **The denominator was the finding:** `renderer none` and the openMSX launch
      set coincided exactly (70 files reference `-machine`; 70 now set
      `sound_driver null`), so a single mechanical rule covered it — but nothing
      had ever counted the sites.
      **No probe needs a host sound driver, and the risky half of that is
      MEASURED, not argued:** PSG work reads the emulated chip via
      `debug read_block {PSG regs}` (`probes/lib/psgtrace.py`), and cassette
      recording writes the emulated cassette port — the same `CSAVE` produces a
      **byte-identical 128224-byte wav** under `sound_driver null` and `sdl`,
      decoding to the same tape bytes. Audio gates (sound/beep/play/play-trace)
      and the full standing suite are unchanged.
      ⚠️ NOT `mute`/`master_volume 0` — they silence the output and leave the
      driver churning. Convention now written down in
      [`probes/README.md`](probes/README.md) "Headless conventions".

- [ ] **`fre_abort_low`'s header cites a `ret z` that no longer exists.**
      [`basic/arrays.asm`](basic/arrays.asm) — "the loop's own normal exit is a
      `ret` at that same depth (rp_lp's `ret z` on the `$0000` link)". D-CONTR
      replaced that `ret z` with `jp cont_record`, and D-ERR21 put a test above
      it. The DEPTH argument still holds (`cont_record`'s `ret` is the loop's
      exit `ret`); only the citation is stale. A comment that names a specific
      instruction is a CLAIM — cf. [[msgtab-bound-drift]].

- [x] **`CONT` after a plain `END` must continue.** Found 2026-07-29 by the
      D-ONEFLG battery's c7 row, not aimed at; characterized 2026-07-29;
      **✅ FIXED 2026-07-30 as D-CONTR —
      [`docs/spec-basic-cont-record.md`](docs/spec-basic-cont-record.md).**
      **+19 B, page 1 only (49 → 30 B free); low region untouched at 80 B.**
      Gate **49/49** (`make abort-acceptance`, 18 new rows, nine of them
      must-NOT-change), six falsification builds.
      **The rule, measured 34 boots deep both ways:** the run loop records a
      resume point at **every** run stop while in RUN mode — `STOP`/Ctrl-STOP,
      `END`, an untrapped abort, and running off the `$0000` link — and in
      DIRECT mode it records **nothing and invalidates nothing**. `CONT` never
      consumes the point; only `RUN`, `NEW` and an edit clear it. One shared
      `cont_record`; only the POSITION differs per stop.
      🔴 **THE FILED TITLE WAS THE SMALLEST PART OF IT.** Three things the item
      did not know, each pinned by a discriminating row: **(a)** `END` resumes
      **MID-LINE**, after its own token — `10 END:PRINT"[9]"` + `CONT` prints
      `[9]` *then* falls through to the next line. **(b)** An **untrapped abort
      records too**, at the FAILING STATEMENT (`SAVTXT`), not the line start —
      `CONT` re-raises the identical error, and `10 PRINT"[7]":B=ASC("")` does
      **not** reprint `[7]`. The forced (ERR 22) arm records as well.
      **(c)** `do_break`'s existing direct-mode gate was **ALSO wrong**: it
      *invalidated*. The reference KEEPS a live resume point across a typed
      `STOP`/`END`/error/line. The row that justified the old gate
      (`spec-basic-direct-ctrl.md` §5) was taken **with nothing live**, where
      invalidate and do-nothing are indistinguishable — it agreed for the wrong
      reason, and it stays green under the new rule.
      🔴 **F4 REFUTED THE SPEC'S OWN PREDICTION: the per-stop re-record ABSORBS
      the `CONT` consume.** Restoring the consume turned only `cont2_thrice`
      red, not `cont2_twice`/`cont2_err_twice` — the resumed run stops again and
      re-records, so a 2-deep battery would have scored dropping the consume as
      unnecessary. **Only the 3-deep row can see it.** ([[cont-depth-slice]]'s
      "what is ABSORBING the fault", one slice later.)
      🔴 **`make unit-test` went RED and the defect was in the TEST.**
      `test_poke.py`'s ERRMARK row read RAM *after* a call that reaches
      `ld sp,(SAVSTK)` with `SAVSTK`=0 in the zeroed harness — the tail `ret`
      popped `$0000` and the CPU ran away to msxtest's 2 M-step guard, which an
      `except: pass` swallowed. Re-sampled BOTH ways on ONE build: the old point
      reads `$DB` after the preceding cases and `$3A` alone; sampling AT
      `fre_abort_low` reads `$DD` with no runaway. Now trapped there, guard
      dropped. ⚠️ **Worth sweeping for siblings — see the new item below.**
      ⚠️ The first build **failed to assemble**: the 5 B added inside the run
      loop pushed `rp_goto`'s backward `jr rp_lp` past −128 (+1 B for a `jp`,
      the byte the estimate lacked). Build and probe were chained with `&&`, so
      unlike the D-ONEFLG incident nothing ran on a stale machine.
      Also retired: `probes/basic/basic_probe_cont.py` (wired into no target,
      `NameError` since the lean retirement, and one assertion now known wrong);
      its provenance citation in `basic/PROVENANCE.md` is corrected in place.

- [x] **Sweep `tests/` for rows that read RAM AFTER a runaway.** ✅ **DONE
      2026-07-31 — the class is EMPTY (0 of 5606 calls), so the deliverable is a
      permanent harness invariant instead of N row fixes.** Spec + all
      measurements: [`docs/spec-tests-runaway-sweep.md`](docs/spec-tests-runaway-sweep.md).
      0 ROM bytes; `tests/` only.
      🔴 **THE FILED RECIPE COULD NOT MEASURE THE CLASS.** It was a grep
      (`grep -n "except" tests/*.py`), but **a runaway does not have to raise**:
      wander into `PC=$FFFF` and it hits msxtest's sentinel, so `call()` returns
      *normally* — no exception, nothing to swallow, no `except` to grep for. So
      an instrument, not a pattern match: wrap `Z80.step` + `Machine.call` and
      record min/max SP per call (nested frames propagate, so the sub-ROM bridge
      cannot hide an inner excursion). Coverage is total — `grep "\.step(\|cpu\.pc *="`
      over `tests/test_*.py` finds **0** code sites, so every instruction the
      suite runs goes through `call()`.
      **DENOMINATOR, AS-RUN:** 54 files (53 execute Z80 at all;
      `test_msgenc.py` is a pure table reader), **5606 `Machine.call()`
      invocations, 0 SP-lost, 0 unbalanced returns, 0 exceptions.** The whole
      suite lives in `SP $F326…$F380` — a 90-byte excursion, 29 KB clear of the
      RAM floor — and **every** call returns with `exit_sp` exactly `$F380`. The
      `except` pass, for the record: 3 textual hits, **0 swallowing**. Exactly
      one test traps an abort funnel: the repaired poke row.
      🔴 **A DETECTOR WHOSE GREEN STATE IS "FOUND NOTHING" IS A CLAIM** — canary:
      the pre-fix poke row rebuilt synthetically gives `min_sp=0` + the 2 M
      runaway, so the detector cuts. **And it read `ERRMARK=$DD`, the value the
      old row asserted** — the wrong apparatus still reproduces the "right"
      answer ([[err21-no-resume-slice]] F3, in the test layer).
      **The fix:** an unconditional SP-band invariant in `msxtest.Machine.call`
      (`$8000 ≤ SP ≤ sp0`) raising `StackLost(RuntimeError)` that names
      `ld sp,(SAVSTK)` and the remedy, plus **new** `tests/test_harness_guard.py`
      — knife + GREEN control + the in-situ D-CONTR case. On the real path the
      failure moved from `runaway: 2000001 steps, PC=0xe1c6` (arbitrary, a
      symptom, *worth swallowing*) to `SP=0x0000 at PC=0x3d4a, step 325` —
      **6,154× earlier, at the `ld sp` itself**. `make unit-test` **55/55**,
      18.30 s vs an 18.16 s baseline (the per-step compare is free), per-file
      breakdown identical by NAME.
      🔴 **F2 REFUTED ITS OWN PREDICTION, AND ONLY THE ORACLE-LOCK COULD SEE IT.**
      Dropping the floor to `$0000` still turned R3 red — but at `SP=$FFFE`,
      337 steps: the runaway had **pushed at `SP=0` and wrapped**, tripping the
      *ceiling* 12 steps behind the floor. Because R3 asserts `sp == 0x0000` —
      the CAUSE — that read as RED. Had it asserted merely *"`StackLost` was
      raised"*, **F2 would have read GREEN and scored the floor as unnecessary**,
      shipping an invariant that caught the class late, by a wrapped SP, pointing
      at the wrong address. F4 also came back narrower than predicted: the
      `RuntimeError` base is **not** what makes a stack loss loud (`run.py` sees
      a nonzero exit either way) — it is what keeps the *rest of the file
      measuring* (3/3 cases reached vs dying on case 0).
      *Original filing (2026-07-30 by D-CONTR, not aimed at):*
      `test_poke.py`'s ERRMARK row had been
      asserting on *whatever a byte held after 2,000,000 steps of the CPU
      executing the ROM from an arbitrary entry point*, and it agreed for its
      whole life until an unrelated 19-byte page-1 shift moved where the runaway
      landed (`$DD` → `$DB`; and `$3A` when the same case runs alone on the same
      build). Fixed there by trapping the funnel and sampling at the moment the
      row is about.
      **The class:** any `msxtest` row that (a) calls a routine which can reach
      `ld sp,(SAVSTK)` — i.e. anything reaching `fre_abort_low`, `raise_error`'s
      abort arm, or the run loop — with `SAVSTK` unset in the zeroed harness,
      and (b) reads state AFTER the call rather than at a trap, and especially
      (c) wraps the call in `try/except: pass`. **The `except: pass` is the
      smell**: it converts "the CPU ran away" into "the row passed".
      Mechanical first pass: `grep -n "except" tests/*.py` for swallowed
      guards, and `grep -n "max_steps\|RuntimeError" tests/msxtest.py` for the
      guard itself. Each hit needs the same treatment: trap the routine the row
      is really about, sample there, and drop the guard so a real runaway is
      LOUD. See [`docs/spec-basic-cont-record.md`](docs/spec-basic-cont-record.md) §5.5.

- [x] ✅ **D-LOF — `LOF(#n)` reads −1 on a freshly-created OUTPUT channel.
      LANDED 2026-07-31, +6 B main page 1, 16/16 rows, falsified F1–F3.**
      Spec [`docs/spec-basic-lof-size-field.md`](docs/spec-basic-lof-size-field.md),
      characterization [`docs/lof-cf3300-characterization.md`](docs/lof-cf3300-characterization.md),
      gate `make lof-acceptance` (new). `make chancost-characterize` is now
      **39 cases / 0 filed** — its `KNOWN_DIVERGE` allowlist is EMPTY.
      🔴 **THE −1 WAS A STALE READING, NOT A SENTINEL, AND THE ROWS THAT PROVED
      IT WERE WRITTEN TO BE ABLE TO REFUTE THE FIX.** Open a known-size file,
      `CLOSE`, then create: zerobas printed **26** and **2048** — the previous
      file's size. `fat_find` writes `FAT_FILESIZE` only when a file is FOUND, so
      no create path wrote it at all and `LOF` returned whatever the previous
      tenant of the `FCH_STATE0` span left. `$FFFF` was just the cold-boot content
      of the cell; nothing ever stored it. Had either row also printed −1 the
      whole diagnosis would have been wrong.
      🔴 **THE DENOMINATOR WAS 3 SITES, NOT 1** — `fat_io_create` (OUTPUT, and
      APPEND-of-missing which jumps into it), `fat_rand_open`'s `fro_create`
      (RANDOM-of-missing), and `frnd_update_size` (a RANDOM `PUT` must GROW it).
      Only the first costs main ROM; the other two live in a sub-only body. F1–F3
      each deleted one edit and the other two rows stayed GREEN, so all three are
      independently load-bearing — and F3's `rand_put` fell to **0**, not −1,
      which is what showed (b) and (c) were separate facts.
      🔴 **THE ROW DESIGNED TO SEPARATE THE TWO CANDIDATE RULES FAILED; A
      DENOMINATOR ROW DID IT.** "0 on a new OUTPUT channel" is predicted equally
      by "the field is zeroed at OPEN" and by "`LOF` computes from the directory".
      `exist_out` (existing 26-byte file opened FOR OUTPUT) was written to split
      them and could not — the reference truncates the directory entry at OPEN
      too, so both rules predict 0 on both instruments. `rand_put` split them:
      the reference prints **`LOF` = 256 while its directory still holds 0**.
      🔴 **THE APPARATUS WAS WRONG THREE TIMES BEFORE THE SUBJECT WAS WRONG
      ONCE.** (1) At the chancost cadence the CF-3300 DROPPED keystrokes after
      any disk-busy line — `PRINT LOF(1)` arrived as `PRO)` and earned a
      completely real `Syntax error`, reported as two reference divergences; at
      9.0 s zerobas began DOUBLING the first character instead. (2) The echo guard
      written to catch that flagged **10 of 16 rows with perfect screens**: the
      name table is 32 cells but Disk BASIC boots SCREEN 1 at `linlen=$1d` = 29,
      so long lines WRAP. (3) Slicing rows to `linlen` was wrong too — the
      reference indents SCREEN 1 by a left margin of **2**. It is right only now
      that it assumes no geometry at all. **And the version that "worked" still
      passed a mangled row**: with whitespace squeezed out, `ZBPPRINT LOF(1)`
      *contains* `PRINTLOF(1)` — **a guard against DROPPED text is not a guard
      against INSERTED text.** It is prompt-anchored now, and was falsified RED on
      both bad captures and GREEN on five clean ones before being believed.
      A `MANGLED` row is fatal with or without `--gate`: two mangled sides compare
      equal and would otherwise print `agree`.

- [x] **✅ D-APPMISS — `OPEN … FOR APPEND` on a MISSING file REFUSES (was: created
      it), −2 B.** LANDED 2026-07-31,
      [`docs/spec-basic-append-missing-refuse.md`](docs/spec-basic-append-missing-refuse.md).
      One instruction: [`basic/fat.asm`](basic/fat.asm)'s `jp c,fat_io_create` →
      `ret c`, so a `fat_find` miss falls to `do_open`'s `oo_fail` → `load_error`
      exactly as `OPEN … FOR INPUT` of a missing file already did. **Main page 1
      20 → 22 B free**, low unchanged at 23 B; dead-code 0/0 both builds.
      `lof-acceptance` **18 cases, 0 unfiled** with `append_new` AGREEING on BOTH
      instruments and its `KNOWN_DIVERGE` entry DELETED; `fat-error-acceptance`
      **8/8 + directory check**.
      🔴 **THE ERROR CLASS WAS NOT THE ONE THE ITEM ASKED ME TO CONFIRM.** The
      filed text said to confirm `oo_fail`/`load_error` yields `File not found`.
      Traced, then measured: it yields zerobas's **`load error`** — and that is
      CORRECT, because `load error` is zerobas's pinned rendering of the whole
      file/channel family (PROVENANCE §74) and is precisely what the INPUT
      sibling already raises. The right question was not "is it `File not found`"
      but **"is it the SAME class as `open-missing`"**, which is a gate row, not
      an inspection.
      🔴 **THE ROW ADDED TO PROVE THE FIX WORKED FOUND A DIFFERENT DEFECT ONE
      LAYER DOWN.** `append_new_wr` (`PRINT #1,"X"` after the refused OPEN, no
      `LOF` typed) exists because `append_new` reads the LAST error on screen and
      so reads `File not open` from its own trailing `LOF` **whatever OPEN did** —
      it would have AGREED even if OPEN had raised `syntax error`. The new row
      showed `PRINT #` into an unopened channel raises `load error` where the
      reference raises ERR 59, while `lof_closed` proves zerobas HAS a real
      trappable ERR 59. Filed below as its own item, with `ctl_prwr_closed` (the
      same `PRINT #` with NO `OPEN` typed at all) as the ATTRIBUTION control, so
      "it was already like that" is measured rather than asserted.
      🔴 **`None` MEANT TWO OPPOSITE THINGS AND THE ROW COULD NOT FAIL.** Its
      first version left `load error` unclassified, so it read `None` pre-fix
      (the write was SILENTLY ACCEPTED) *and* `None` post-fix (the write was
      REFUSED). A regression back to silent acceptance would not have moved the
      value. Fixed by adding a `LOADERR` class — reversing this spec's own §5c
      sign-off answer, which was right for `append_new` and wrong for a row that
      did not exist when the question was asked.
      🔴 **THE SECOND INSTRUMENT WAS MEASURED, PRINTED AND NEVER COMPARED.** The
      `dir` column had been in `diskbasic_probe_lof.py` since D-LOF, but the
      verdict came from the LOF value alone — so "the reference makes NO directory
      entry", the central claim here, could not fail the gate. Both columns are in
      the verdict now (`DIR_EXPECT` / `DIR_DIVERGE`). It cut immediately:
      `rand_put` has AGREEING LOF columns and separates only on `dir` (filed
      below) — a row the old single-column verdict called `agree`.
      🔴 **AND THE GATE I ADDED FOR THE CLASS WAS GREEN OVER A PROVABLY BROKEN
      SUBJECT.** `fat-error-acceptance` ran with **NO DISK IN THE DRIVE**, so all
      seven pre-existing cases failed in `fat_mount` and never reached `fat_find`
      at all — the docstring claimed the find miss, the probe measured the mount
      miss, and the two are indistinguishable by their answer (`load error`
      either way). Caught ONLY by the knife: with the fix reverted, `append-missing`
      stayed **GREEN**. It now mounts a **/tmp COPY** of `test720.dsk` — mandatory,
      because a build where APPEND still creates actually WRITES `NOSUCH.DAT` into
      the image (measured) — and parses that image afterwards, so a build that
      printed `load error` and created the entry anyway cannot pass.
      Falsification RUN, not planned: with `ret c` reverted, `append_new` and
      `append_new_wr` go RED on BOTH instruments and `append-missing` goes RED on
      BOTH, while `append_exist` (26/26), `roundtrip`, `disk_probe_append.py`'s
      byte-identical Ctrl-Z round trip and the other seven fat-error rows stay
      GREEN. The knife was verified to CUT: `fia_walk` $6361↔$6363 and page-1 free
      22↔20 B moved with it.

- [x] ✅ **`PRINT#`/`INPUT#`/`LINE INPUT#` on a channel that is NOT OPEN raise a
      trappable ERR 59, not `load error`.** LANDED 2026-07-31, D-NOTOPEN,
      [`docs/spec-basic-chan-notopen-err59.md`](docs/spec-basic-chan-notopen-err59.md).
      **−8 B, main page 1 22 → 30 B free**, low unchanged at 23 B. Found
      2026-07-31 by D-APPMISS's `append_new_wr` row, not aimed at.
      🔴 **THE DEFECT WAS A HAND-INLINED COPY OF AN EXISTING ROUTINE WITH ONE
      INSTRUCTION MISSING.** `fch_mode_class` (was `ev_chan_hasfile`,
      [`basic/expr.asm`](basic/expr.asm)) already reads `FCH_MODES[E]` and raises
      ERR 59 when it is 0 — that is how `LOF(1)` on a closed channel already
      AGREED with the reference. `ex_print` and `input_common` had each copied its
      array read inline and **omitted the `or a`**, so a not-open channel matched
      no device mode, fell into the disk arm and derailed to `load_error`. So the
      fix was to DELETE the copies and `call` the original: two hunks, no new code
      path, and 4 bytes of page 1 back at each site.
      **Trappability was in scope and is the bigger half:** `load_error` is a
      `ret`-based print path that CONTINUES the program, so an armed
      `ON ERROR GOTO` never saw it. Measured under a handler that prints `ERR`
      (where `0` means "nothing was raised", keeping trapped / not-trapped /
      nothing-happened three distinct readings): reference **59**, zerobas
      `load error`; now **59 on both**.
      🔴 **THE PLANNED KNIFE NAMED TWO WITNESSES THAT COULD NOT MOVE.** The spec
      said `ex_print` and `input_common` must shift under the falsification. Both
      labels sit BEFORE the edited bytes and are invariant either way — a knife
      that silently failed to apply would still have passed two of three "cut
      verified" checks. Only `__MEAS_PAGE1_END` ($7FE2 ↔ $7FEA) and the page-1
      free number carried the cut. ⚠️ **A cut witness must be DOWNSTREAM of the
      edit;** "the addresses moved" is evidence only when they COULD have moved.
      Falsification RUN on the verified cut: `append_new_wr`, `ctl_prwr_closed`,
      `closed_input`, `closed_lineinp`, `trap_print_closed`, `trap_input_closed`
      all RED, while `trap_lof_closed` (59/59), `lof_closed`, `ctl_syntax`,
      `append_exist` 26/26, `roundtrip` 8/8 and the three filed-divergence rows
      stayed GREEN, 0 mangled.
      Gate: `diskbasic_probe_lof.py` 18 → **26 cases**; `KNOWN_DIVERGE`'s
      `append_new_wr` + `ctl_prwr_closed` entries **DELETED, not updated**, and
      replaced by three rows for the sites deliberately LEFT (below), so the list
      stays a control that must keep matching rather than an empty box.

- [x] ✅ **`GET`/`PUT`/`FIELD`/`INPUT$(n,#f)` answer the reference on the WHOLE
      channel-mode grid, not just the not-open column.** LANDED 2026-07-31,
      D-NOTOPEN2, [`docs/spec-basic-gpfi-notopen-err59.md`](docs/spec-basic-gpfi-notopen-err59.md).
      **Net −19 B: page 1 30 → 49 B free, low UNCHANGED at 23 B.**
      Filed as "these four answer `Syntax error`, the reference answers ERR 59";
      the filed measurement was the not-open COLUMN of a grid that turned out to
      have **five** reference codes.

      | `FCH_MODES` | `GET`/`PUT` | `FIELD` | `INPUT$` |
      |---|---|---|---|
      | 0 not open | **59** | **59** | **59** |
      | 1/2/3 disk, not RANDOM | **61** | **61** | **55** |
      | 4 RANDOM | *(works)* | *(works)* | **61** |
      | 5/6 `LPT:`/`CRT:` | **58** | **5** | **55** |

      🔴 **MEASURING THE NEIGHBOUR CHANGED THE ANSWER TWICE, AND THE SECOND TIME
      WAS AFTER I HAD ALREADY COSTED THE SLICE.** Battery 1 sampled modes 0/1/2/4
      and read two new codes (61, 55); I costed the sweep against that and called
      it unaffordable. Battery 2 added modes **3/5/6** — the ones nobody had typed —
      and the answer became five codes. ⚠️ **A grid sampled at three of its seven
      rows is not a denominator**, and the rows that were missing are exactly the
      ones that carried the exceptions (`LPT:` answers **58** to `GET` but **5** to
      `FIELD`; `INPUT$` is **61** on RANDOM and **55** on everything else).
      🔴 **`FIELD` ON A SEQUENTIAL CHANNEL WAS ACCEPTED SILENTLY** — the row read
      `0`, *nothing raised*, where the reference raises 61. Nobody was looking for
      it; it is a missing check, not a wrong code, and it is the severe half.
      🔴 **"IT DOES NOT FIT" WAS A CLAIM ABOUT TODAY'S BUDGET, NOT ABOUT THE
      CHANGE.** Costed at ~86 B against 53 B free, I proposed dropping to the
      not-open column. The override was right: `tools/clone_scout.py` found the
      funding in one run, in the same file. **The carve was −107 B:**
      `oo_parse_as_chan` — the `AS [#]n` clause hand-inlined **VERBATIM at THREE**
      OPEN arms (disk, `LPT:`/`CRT:`, `CAS:`), 47 identical bytes each (−84 B) —
      and `fch_modes_ptr`, the `&FCH_MODES[ch]` index hand-inlined at **TEN** sites
      (−23 B). ⚠️ Same shape as D-NOTOPEN's defect, three times over: **when a
      fragment appears at N sites, N is never the number you first counted.**
      ⚠️ `fch_modes_ptr` uses the 8-bit page-local form deliberately — the obvious
      `add hl,de` version clobbers DE, and TWO callers read `E` after the index.
      That version assembles clean and breaks `CLOSE` on a device channel.
      Placement: ERR 55/58/61 cost 72 B, and the low region had 23 B — so
      `rerr_sparse`'s tail became `jp rerr_sparse2` (**a 0-byte change to the low
      region**) and all 72 B landed in page 1, at the tail of the LAST include
      (inserting mid-page-1 breaks dense forward `jr`s — pasmo rejects it).
      Gate: `diskbasic_probe_lof.py` 26 → **41 cases**; `KNOWN_DIVERGE`'s
      `closed_get` + `closed_field` entries **DELETED, not updated**, leaving
      **exactly one** entry (`closed_ch2`, the ERR 52 item). The two rows that earn
      their keep are `wm_lpt_get`/`wm_lpt_fld` (same channel, 58 vs 5 — a fix that
      collapsed "device → one code" goes red on exactly one) and
      `wm_rnd_inpd`/`wm_out_inpd` (61 vs 55, `INPUT$`'s two rules). Plus two GREEN
      controls, `ok_in_inpd` and `ok_rnd_get`, both `0`/`0`: without them a fix
      that raised unconditionally would have turned every other new row green.
      ⚠️ APPARATUS: battery 2's first run read the zb column as **entirely `None`**.
      `rm -rf build && make basic-reloc` rebuilds neither `build/disk.rom` nor
      `build/zerobas-main-eu.rom`, and the machine XML names both by absolute path,
      so the house-rule clean wall measurement leaves the installed machine
      dangling. Caught only by `ctl_syntax`. **Clean measure, THEN
      `make repack-machine`, THEN probe.**

- [ ] **`GET`/`PUT`/`FIELD`/`INPUT$` on a `CAS:` channel (`FCH_MODES` 7/8) are
      INFERRED, not measured.** D-NOTOPEN2 swept modes 0–6 against the CF-3300 and
      sends 7/8 down the *device* arm (CF clear, since both are >= `LPT_MODE`), i.e.
      `GET`/`PUT` → 58, `FIELD` → 5, `INPUT$` → 55, **by analogy with `LPT:`/`CRT:`
      rather than by measurement.** 🔴 That is precisely the shape that slice spent
      two batteries avoiding everywhere else, so it is filed rather than shipped
      quietly. Blocked on apparatus, not on ROM space: `diskbasic_probe_lof.py`
      mounts a disk image per case and has no way to attach a tape, so this needs a
      `disk_probe`-side (or new cassette-side) harness. ⚠️ The reference may well
      not agree with the analogy — `LPT:` itself answers **two different codes**
      (58 to `GET`, 5 to `FIELD`), which is the local evidence that device handling
      here is per-verb and not a single rule.

- [x] ✅ **A REJECTED channel number answers the reference's error class, on every
      verb.** LANDED 2026-07-31, D-BADFNUM,
      [`docs/spec-basic-badfnum-channel-class.md`](docs/spec-basic-badfnum-channel-class.md).
      **Net −14 B: page 1 49 → 63 B free, low UNCHANGED at 23 B.**
      Filed as three rows (`PRINT #2`, `INPUT #2`, `PRINT #0`) with the warning
      that they do not generalise. The warning was right and it was the smaller
      half: `fch_valid` had **NINE call sites routing to SIX dispositions**, so the
      filed rows walked 2 sites and 1 disposition. Swept as **12 channel-taking
      verbs × 6 channel classes**; **63 of the first 72 cells diverged.**

      The reference rule, measured, is ONE rule with two exceptions:

      | channel | reference | exceptions |
      |---|---|---|
      | `A$` (string) | **ERR 13** `Type mismatch` | none |
      | `#256` / `#-1` | **ERR 5** `Illegal function call` | none |
      | `#0` | **ERR 59** `File not OPEN` | `CLOSE #0` no-ops; `OPEN … AS #0` is **52** |
      | `1 … MAXF` | proceeds | |
      | `> MAXF` | **ERR 52** `Bad file number` | none |

      🔴 **THE TWO WORST CELLS WERE NOT IN THE FILED ITEM.** `EOF`/`LOF` on a
      rejected channel **raised nothing and returned a number** — `PRINT LOF(0)`
      printed ` 0`, an answer, not an error, and an armed handler never ran. And
      `CLOSE #2`/`#16`/`#256`/`#-1` **silently no-opped**. Same shape as
      D-NOTOPEN2's silently-accepted `FIELD`, one layer earlier.
      🔴 **THE SWEEP REFUTED MY OWN SAMPLE, TWICE.** Battery 1 took the last three
      classes on `PRINT#`/`GET`/`LOF`, read a uniform rule and looked settled — but
      it excluded `OPEN`, the one verb already known to differ at `#0`, and
      `OPEN … AS #256` is **ERR 5** on the reference where zerobas said 52.
      🔴 **AND THEN I MADE THE SAME MISTAKE INSIDE THE SPEC THAT ARGUES AGAINST
      IT.** The type-mismatch cells were written up as three "edge cells" rather
      than as a sixth CLASS with twelve rows. The signed-off design shipped a
      REGRESSION on them (a type mismatch hard-zeroes the channel to 0, so
      `fch_check`'s ERR 59 got there first), and the row that caught it —
      `PRINT LOF(A$)` — was in the gate **only because it already AGREED**.
      Sweeping that column found the reference uniform at `Type mismatch` and
      zerobas wrong on **8 of 12**, only two of them regressions. Cost: +7 B.
      ⚠️ **A CELL PINNED AS A CONTROL BECAUSE IT AGREES IS WHAT FINDS THE AXIS YOU
      DID NOT KNOW YOU WERE SAMPLING.**
      🔴 **A THIRD PROBE HAD ENCODED THE OLD BUG AS AN ORACLE.**
      `disk_probe_closelist.py` ran `CLOSE#1,#2,#3` at `MAXFILES=1` and its
      docstring called the out-of-range channels a "lenient no-op" — a zerobas-only
      claim with no reference column. Typed on the CF-3300: it answers **ERR 52**,
      **after flushing #1** (the directory column proves the flush; a screen
      reading would not). `5 MAXFILES=3` added, so the probe still tests the LIST
      PARSER without resting on a leniency the reference lacks. The §7 blast-radius
      grep could not have found it — the channel is only out of range if you
      already know `MAXF`.
      Fix: the nine sites (78 B) became one `fch_check` with two extra entry points
      for `CLOSE`'s and `OPEN`'s channel-0 exceptions (38 B + 35 B), and
      `fch_valid` is DELETED (−9 B). §6 also took a **0-byte** change —
      `eval_chan`'s tail `jp check_fperr_only` → `jp check_expr_errors` — whose
      independent value is proven by knife K5 and nothing else.
      Gate: NEW `probes/disk/diskbasic_probe_badfnum.py`, `make badfnum-acceptance`,
      **93 cases, 0 unfiled / 0 oracle drift / 0 mangled / 0 without an oracle
      lock.** `diskbasic_probe_lof.py`'s `closed_ch2` entry **DELETED, not
      updated**, leaving `KNOWN_DIVERGE` **EMPTY — asserted in words, not left as a
      dict with no lines in it.** Six knives RUN: K1/K2/K3/K4/K5 each red on their
      own rows with every control green (K1's four rows go red in four DIFFERENT
      ways; K5 leaves exactly the four `eval_chan` verbs green), and K0 — aimed at
      the spec's own `FCH_MODE` justification — **held**. ⚠️ K0's first cut read
      `DIR=7` on subject AND control and looked like a pass; both had fallen into
      their own handler (`RESUME without error`), so it could not separate "the
      trap fired and the write survived" from "line 20 did nothing".

- [x] ✅ **A RANDOM `PUT` stamps the on-disk directory size immediately — and the
      reference stamps it at `CLOSE`, to the SAME value.** MEASURED AND DECIDED
      2026-07-31, D-RNDDIR,
      [`docs/spec-basic-randput-dir-stamp.md`](docs/spec-basic-randput-dir-stamp.md).
      **Zero ROM bytes: apparatus + documentation, which is what the item asked
      for.** MSX-DOS 1 has no subdirectories — "the directory" throughout is the
      FAT12 **root** directory table, and the reading is the size field at offset
      28 of the file's 32-byte entry.

      🔴 **THE FILED SENTENCE WAS NOT LICENSED BY THE FILED MEASUREMENT.**
      `rand_put` exits with the channel STILL OPEN, so `ref dir = 0` only ever
      meant *"has not stamped it YET"* — **nobody had typed a `CLOSE`.** Three
      worlds reproduced that row identically (timing only / different values /
      never stamps). Four new rows separate them:

      | row | ref LOF | ref dir | zb LOF | zb dir | |
      |---|---|---|---|---|---|
      | `rnd_put_cl` | `File not open` | **256** | `File not open` | 256 | agree |
      | `rnd_put_rt` | **256** | 256 | 256 | 256 | agree |
      | `rnd_put_len` | **16** | 0 | 16 | 16 | diverges (`dir`) |
      | `rnd_put_big` | 2048 | 2048 | 2048 | 2048 | agree |

      The reference stamps at `CLOSE` with the same value, and the **round trip
      agrees**, so no BASIC program can observe the difference. It is a *when*,
      not a *what*. zerobas's `fat_rand_put` tails into `jp fat_dir_update`
      ([`basic/randio-body.inc:373`](basic/randio-body.inc:373)) and stamps on
      every `PUT`; the reference defers to `CLOSE`.
      🔴 **AND THE RULE ITSELF HAD BEEN AGREEING FOR TWO REASONS AT ONCE.** The
      characterization's `recno × reclen` rested on the single **256** — but
      `OPEN … AS #1` defaults reclen to 256, so `1 × 256 = 256` *and* a 256-byte
      sector is 256. `LEN=16` reads **16**: the formula holds, sector-granularity
      is refuted, and the number that had "confirmed" it could not tell them
      apart. `rnd_put_big` puts a 256-byte record into 2048-byte `TEST.BIN` and
      reads 2048 in all four columns — **no truncation, no data loss**. ⚠️ `max()`
      is pinned by the PAIR (`rand_put` grows 0 → 256, `rnd_put_big` does not
      shrink), by neither row alone.
      Decided per the spec's pre-committed §5(A): at a 23 B low wall a difference
      no program can observe buys no ROM bytes. `DIR_DIVERGE` therefore keeps
      `rand_put` and gains `rnd_put_len`, **rewritten from "filed, open" to
      "decided, permanent" with the round-trip rows named as the evidence** —
      the one entry in either list that is not an unbuilt item. ⚠️ Growing an
      allowlist is allowed only loudly: `rnd_put_len` is load-bearing, it is what
      shows the early stamp follows `recno × reclen` and not the sector size.
      Gate: `make lof-acceptance` **41 → 45 cases, 0 unfiled / 0 oracle drift /
      0 mangled**; `KNOWN_DIVERGE` still EMPTY. K1 CUT (a forced-wrong
      `DIR_EXPECT` reddens that row ALONE, so the `dir` column is live on the new
      rows and not merely in principle); K2 PASS (`rnd_put_cl`'s trailing
      `File not open` is the witness that the `CLOSE` actually ran — a row whose
      only reading is `dir` cannot tell "stamped 0" from "the line never
      arrived").
      ⚠️ **INTERMITTENT ORACLE DRIFT — SECOND SIGHTING 2026-08-05 (D-PINDATA
      corpus), AND THE DIAGNOSTIC WAS DESTROYED.** The run reported
      `45 cases, 0 unfiled divergence(s), 1 oracle drift(s), 0 mangled` and exited
      non-zero. **Four immediately following runs were all clean** (0 drifts,
      rc 0). Sighting 1 was `wm_app_put` (recorded 61, live `None`) during
      D-LATCH's corpus, then five clean. 🔴 **I cannot name the row this time: the
      gate was run through `| tail -6`, and the `ORACLE DRIFT (recorded …)` line
      is in the BODY.** ⇒ **a gate with a known intermittent must be captured in
      FULL, never tailed** — a rare finding has exactly one copy. Still a flake,
      still not written off; the next sighting needs the whole log.

- [ ] **UNMEASURED: a machine reset BETWEEN a RANDOM `PUT` and its `CLOSE`.**
      Filed 2026-07-31 by D-RNDDIR as the one thing its rows do not reach. In
      that window the two disks genuinely differ: the reference has stamped
      nothing and loses the write, while zerobas's root-directory entry is
      already stamped and points at a chain whose FAT state at that instant
      NOTHING HAS EXAMINED. ⚠️ Blocked on APPARATUS, not ROM space:
      `diskbasic_probe_lof.py` reads the disk image after the machine exits
      normally and has no way to cut power mid-program. It is a robustness
      question, not a parity one — and it is filed rather than argued in either
      direction, because "zerobas is more robust here" and "zerobas leaves a
      dangling entry here" are both plausible from what is known and neither has
      been typed.

- [x] ✅ **`diskbasic_probe_chancost.py` IS ECHO-GUARDED — LANDED 2026-07-31,
      39/39, falsified both ways.** Apparatus only, **0 ROM bytes**, walls
      UNCHANGED (low 23 B, page 1 63 B — no `basic/` or `sub/` file touched).
      Spec [`docs/spec-probe-chancost-echo-guard.md`](docs/spec-probe-chancost-echo-guard.md),
      results [`docs/chancost-cf3300-characterization.md`](docs/chancost-cf3300-characterization.md) §0.1.
      `echo_missing` + the per-side prompt (`""` ref / `"ZB"` zb) ported from
      [`diskbasic_probe_lof.py`](probes/disk/diskbasic_probe_lof.py), plus a
      `--line-delay` knob (default **4.5**, unchanged) so the guard can be shown
      to cut.

      🔴 **THE FILED REASON WAS THE WEAKER ONE.** The item said a mangled line
      would read as an `FRE(0)` finding. What mangling actually produces is a
      **`Syntax error`** — which is what **`ctl_syntax`, this probe's own harness
      control, is recorded as expecting.** A mangled `ctl_syntax` row reads
      `SYNTAX`, matches its oracle, compares equal across the machines and prints
      **`agree`**. ⚠️ **The control that proves the harness is typing fails toward
      "pass" when the harness stops typing** — it cannot measure its own class,
      the same shape as the filed grep in [[test-reads-ram-after-runaway]].
      Measured, not argued: K1's mangled rows land on `SYNTAX` on BOTH machines.
      🔴 **AND A MANGLED ROW WOULD HAVE PRINTED A HEADLINE.** The slope, the
      ceiling and `HEADLINE: reference charges 267 B per channel` are derived from
      the `mf*` ladder. `MANGLED` therefore **suppresses** the derivation rather
      than being reported beside it — a slope computed from a ladder that never
      received `MAXFILES=8` is a number the run never measured. Ordering is
      load-bearing twice over: `MANGLED` is checked BEFORE the oracle comparison,
      or a mangled *reference* row reports as `ORACLE DRIFT` and blames the
      CF-3300 for the typing.
      Falsified both halves. **K1 CUT** — the same three disk-touching cases at
      `--line-delay 3.1` go **3/3 MANGLED, exit 3**, reproducing D-LOF's failure
      mode inside this probe: `PRINT LOF(1)` arrives as **`RIT OF1)`** and
      `OPEN "ZQ.DAT" FOR OUTPUT AS #1` as **`PE "Q.AT FR UTUTAS#1`**, each earning
      a completely real `Syntax error`, with zerobas mangling in parallel — **both
      sides `SYNTAX`, i.e. EQUAL.** Control: the **identical command with the one
      flag removed** → exit 0, 0/0, 26/26, 23163/14799. **K2 8/8** on synthetic
      screens: a doubled-character row (`ZBPPRINT FRE(0)`) is RED (a substring
      test passes it — a guard against DROPPED text is not one against INSERTED
      text), while a clean row and a **wrapped** reference echo at margin 2 *and*
      margin 1 are GREEN, and a scrolled-off first line is RED. The wrap is
      confirmed on a REAL capture too: `err_badchan`'s 32-char line 30 wraps on
      the reference and passes.
      🔴 **AND THE NEW GATE IMMEDIATELY CAUGHT ONE MORE NON-READING WEARING A
      READING'S FACE — beyond the signed-off scope, fixed here rather than
      filed.** A full run came back `lof_new` ref = `None` → **`ORACLE DRIFT`**;
      re-run, a clean **0** on a perfect screen. The guard had not fired because
      `run_case`'s **TIMEOUT** and **NO CAPTURE** paths return BEFORE it, both
      returning `None` — the same value a clean screen with no number on it reads
      as. ⚠️ **A sentinel that also means "no reading" is not a measurement**: a
      run that never finished was being reported as the CF-3300 failing its own
      oracle, i.e. **the host blamed on the reference machine.** Both paths now
      return `TIMEOUT`/`NOCAPTURE`, handled like `MANGLED` (fatal, derivation
      suppressed) under the verdict `RUN FAILED`. **K3 CUT**: a bogus
      `ZEROBAS_BASIC_MACHINE` → `NOCAPTURE`, exit **3**; the identical command
      with the real machine → `0`, exit **0**. The 200 s deadline is left ALONE —
      which path fired is not known, and raising a timeout to fix an unattributed
      failure is a guess; the markers make the next occurrence name itself.
      ⚠️ §5 of the spec pre-committed what to do about red rows at the 4.5 s
      default. **None appeared** — the full run is clean on all 39 — so the
      cadence is unchanged and no rule was reached. The scroll-off risk flagged in
      §5.1 (ten cases type a 5-line program and then `RUN` it) did not materialise
      either; `err_badchan`'s six typed lines fit the 24-row screen.
      Gate: `make chancost-characterize` — **39 cases, 0 mangled, 0 oracle drift,
      0 unfiled divergence, `KNOWN_DIVERGE` EMPTY**, both machines per-channel and
      linear with ceiling 15, headline 267 B (ref) / 50 B (zb): **identical to the
      pre-change run**, which is the control on the change itself.

- [x] ✅ **The `MAXFILES` ARGUMENT DOMAIN — LANDED 2026-07-31, 53/53, falsified,
      NET −6 B.** Filed as "over-ceiling `MAXFILES` raises the wrong error
      class". **The filed item was already fixed** (`61e3a48` made `MAXFILES=16`
      raise ERR 5) — **and closing it on that would have shipped two live
      defects.** Spec [`docs/spec-basic-maxfiles-domain.md`](docs/spec-basic-maxfiles-domain.md),
      results [`docs/chancost-cf3300-characterization.md`](docs/chancost-cf3300-characterization.md) §11.
      Walls: page 1 **63 → 69 B**, low region **UNCHANGED at 23 B**.

      🔴 **THE FILED ROWS COULD NOT REACH THE DEFECT.** `mf16` and `mf255` both
      have a **zero high byte**, so both land on the same arm of `ex_maxfiles`'s
      domain test; `ld a,d / or a / jp nz,gb_illegal` had **never been executed
      by any test on either machine**, across 39 cases. "The class is right" had
      been concluded from two same-side samples.
      🔴 **AND THE SEVERE DEFECT WAS A SILENT ACCEPT.** `ex_maxfiles` took its
      argument through `eval`, not `get_byte_arg`; `eval`'s `flt_to_int16`
      **zeroes `DE`** for an out-of-int16 value (`basic/interp.asm`'s own header
      says so), so `MAXFILES=65536` and `=70000` arrived as `DE=0` and were
      accepted as an ordinary request for **zero channels — every file channel
      disabled, no error raised** — where the reference raises ERR 6 `Overflow`.
      🔴 **AND A SECOND DEFECT WAS INVISIBLE TO THE ROWS THAT FOUND THE FIRST.**
      `32768`/`-32769` *are* representable in 16 bits, so `DE` is non-zero and
      the old test **did** fire — with ERR 5 where the reference says ERR 6. The
      two rows that triggered the slice could not have exposed it; only the
      boundary rows could, and those were added to pin **the denominator of the
      FIX**, not of the defect. ⚠️ **Ask what a fix's own rule needs pinned, not
      just what the defect needed.**
      ⚠️ **THE PROBE WOULD HAVE SCORED THE SILENT ACCEPT AS `agree`.** `err_class`
      returns `None` for any message not in `ERR_CLASSES`, the number scan then
      also returns `None`, and `ERR_CLASSES` had **no entry for `Overflow`** —
      exactly what the reference answers here. Unclassified-error and no-number
      were the same value, so both sides read `None`, compared **equal**, and
      printed `agree`. Fixed FIRST (§0.2): `OVF`/`TM` added, an unreadable screen
      returns **`NOREAD`** and is fatal like `MANGLED`, and the derivation was
      lifted into `read_value()` so it is falsifiable without booting a machine.
      **K4 12/12** synthetic (4 RED / 8 GREEN); **K4b CUTS** — the old rule scores
      the reference-`Overflow`-vs-zerobas-silent-accept pair as `agree`. This is
      [[apparatus-is-part-of-the-measurement]] one layer *inside* where the
      previous session left it.
      ⚠️ **TWO OF MY OWN ROWS WERE WEAK AND WERE CORRECTED BEFORE THEY BECAME
      ORACLES.** `MAXFILES=1.5` read **23430 = `mf1`**, and **1 IS THE BOOT
      DEFAULT** — the cell could not separate "truncated to 1" from "the
      statement did nothing", the same hole the probe header already flags for
      `mf1`. And a fractional row read off `FRE(0)` is `COMPARE absfre`, i.e.
      *informational* — it would have gated **nothing on the machine under
      test**. Both now read out through the channel-number range (a class on
      both machines), with a paired integer control `mfd_frac_ctl`.
      **The reference's rule, measured across 14 rows and recorded BEFORE
      zerobas was run on any of them:** outside int16 → ERR 6 `Overflow`; inside
      int16 but outside `0..15` → ERR 5 (negatives included); fractional
      **TRUNCATES** (`15.9` accepted as 15, `2.5` → 2). ⚠️ The int16 boundary is
      the **RANGE −32768..32767, not the magnitude** — the asymmetry
      `get_byte_arg`'s header records for `CHR$` on the VG-8020, here **measured
      for `MAXFILES` on the CF-3300** rather than assumed to carry across verbs.
      **The fix REPLACES code:** `call eval` + five hand-inlined bytes →
      `call eval_byte_arg`, which *is* the reference rule. Nine bytes become
      three; the `FCH_CEIL` test stays because that bound is the statement's own.
      **Falsified:** reverting `basic/files.asm` alone → **4 RED, 10 GREEN**, red
      exactly `mfd_65536`/`mfd_70000`/`mfd_32768`/`mfd_n32769`, with `mfd_32767`
      and `mfd_n32768` — the *same* boundary, one step inside — staying green, so
      the knife is attributable to crossing int16. ⚠️ **The knife corrected my
      prediction**: I expected `32768` to be a silent accept too; it read `IFC`,
      and that is how the second defect got its name.
      Gate: `make chancost-characterize` — **53 cases, 0 mangled, 0 oracle drift,
      0 unfiled divergence, `KNOWN_DIVERGE` EMPTY**; every ladder reading
      byte-identical to the pre-change run, and both fractional rows held
      (`fac_to_int_strict` truncates like the reference — the live risk in
      routing the argument through a different converter). Full corpus green:
      unit 55/55, badfnum 93, lof 45, diskbasic 34/34, bdos 12/12, fat-error 8/8,
      error/stop-trap, abort 49/49, linemax 60/60, arrdim 73/73, clearpool 52/52,
      array 149/151 (standing `ifc.instr.zero`/`ifc.instr.neg`, confirmed BY NAME).

- [x] ✅ **STALE LEAN-CART CLAIMS SWEPT — 2026-07-31, docs only, 0 ROM bytes.**
      Flagged while landing D-MFDOM (`basic/PROVENANCE.md` §MAXFILES described the
      retired lean 16 KB cart as a LIVE constraint on channel-table work) and
      swept as its own item. **367 hits for `lean cart|lean 16|ROM_BASE`; 7 were
      stale; 360 were legitimate** and deliberately left alone.
      🔴 **THE SWEEP'S OWN PREMISE WAS MOSTLY WRONG, AND THE FILE SAID SO.**
      [`basic/PROVENANCE.md:3591`](basic/PROVENANCE.md:3591) carries an **explicit
      standing decision**: *"EARLIER ENTRIES IN THIS FILE ARE NOT REWRITTEN,
      DELIBERATELY … this file is a provenance log, not a description of the
      current tree."* Rewriting its 32 hits — or the 217 in dated per-slice specs,
      or the 48 in the retirement's OWN specs — would have **violated a documented
      decision** and destroyed the record of how the code got here. ⚠️ **Before
      mass-fixing a pattern, check whether the file already has a POLICY for it.**
      ⚠️ **But the same entry makes a CHECKABLE CLAIM — *"The source comments, by
      contrast, WERE swept"* — and that claim is what this item tested. It had
      SURVIVORS**: [`basic/sv-bsvcas.inc:13`](basic/sv-bsvcas.inc:13) (*"the lean
      16 KB cart **stays** byte-frozen"*), [`basic/bload.asm:71`](basic/bload.asm:71)
      (described an `ELSE` branch that no longer exists),
      [`Makefile:134`](Makefile:134) / [`Makefile:158`](Makefile:158) (*"the lean
      cart **keeps** …"*) and [`Makefile:628`](Makefile:628) (*"the lean cart
      **ships** without EQV/IMP"*, plus a `Repack-only` tag that is meaningless
      with one build). **A completeness claim in a doc is a claim, not a
      measurement.**
      ⚠️ §MAXFILES is NOT covered by the log policy even though it sits above the
      dated entry: PROVENANCE sections are **undated feature sections**, and that
      one is demonstrably LIVE-MAINTAINED (four `2026-07-31` updates). Rewritten
      as explicitly historical — which is what the policy itself prescribes.
      **Left alone on purpose:** [`README.md:213`](README.md:213) and the
      `Makefile` retirement notes (already past-tense and correct); the six
      `Makefile` SUB_PARTS entries saying *"the lean cart's inline copy"* — those
      are POSSESSIVE PROVENANCE identifying which body a `.inc` was carved from,
      not a claim the cart exists, and their staleness warning is unrelated to the
      cart and entirely current. One convention note added at the block head
      instead of six edits, so the block does not read inconsistently.
      **Verification proportionate to the change:** `make -n` parses, and
      `git diff` over `basic/` contains **zero non-comment lines** — provably
      byte-neutral, so no rebuild and no gate was run (they measure nothing about
      a comment).
      ⚠️ **Filed, not fixed:** the policy at `PROVENANCE.md:3591` says "earlier
      entries", but the file is genuinely MIXED — append-only log entries *and*
      live-maintained feature sections. That ambiguity is what made §MAXFILES
      arguable. Sharpening the policy wording is a decision for the owner, not a
      sweep.

- [x] ✅ **D-EXPBAD — A MALFORMED EXPONENT — LANDED 2026-07-31, 99/99, NET −8 B,
      falsified on five knives, and `KNOWN_DIVERGE` IS NOW EMPTY.**
      Spec [`docs/spec-basic-expbad.md`](docs/spec-basic-expbad.md), measurement
      [`docs/expbad-msx1-characterization.md`](docs/expbad-msx1-characterization.md)
      (18 rows, two oracle-lock rounds, VG-8020 and CF-3300 agree on every one).
      **Baseline 3/12 — the only three that agreed were the three controls.**
      🔴 **THE RULE IS THAT THE DIGITS ARE OPTIONAL.** The exponent grammar is
      `[EeDd] [+-]? digit*`, not `…digit+`, so there is **no failure case and no
      rollback** — which is why the fix REMOVES code. `tke_fail` and the two
      range tests that fed it are gone.
      🔴 **AND THE FILED ROWS WERE A SAMPLE, THREE WAYS** — every one of them is an
      `E` with one mantissa digit:
      * `20 A=1D` is a **DOUBLE**: the marker's PRECISION survives a failure that
        consumes no digits. No `E` row can distinguish "a marker was seen" from
        "*this* marker was seen", so a fix collapsing both to single would have
        passed all four filed rows.
      * `20 A=12345EX` is a **SINGLE**, where zerobas stored the two-byte INTEGER
        — the marker forces the literal off the int path, invisible at D=1.
      * `20 A=1E#` leaves the `#` **raw** (the suffix scan is skipped exactly as
        for a well-formed exponent), so `#` does not make it double and `%` does
        not make it integer.
      ⚠️ **The fix CREATED a cell that did not exist before it.** `20 A=1E X`
      keeps its blank and `20 A=1E -X` loses it — D-DECBLANK's cursor rule
      unchanged. Committing where the code stood (after `tkf_fetch` had already
      crossed the blank run) satisfies **every filed row** and silently eats that
      blank; only `dec-emarkblk` / `dec-esignblk` object.
      🔴 **KNIFE K2 REFUTED THE SPEC'S OWN PREDICTION**: the control it named went
      red, because clearing `has_exp` reaches the digitless case too. The real
      control is the `D` pair, making K1/K2 exact mirrors over the two flag bits.
      Corrected in the spec rather than dropped.
      **Cost: NET −8 B, all sub-ROM page 0** (4018 → 4026 B free); main page 1
      stayed at 8 B, low at 23 B, and both main ROMs came out **byte-identical**.
      It does NOT reach `branch_lineno` (`20 GOTO 1EX` keeps `EX` on both
      references) or a `DATA` body — measured, and pinned as controls.

      **As filed** (kept because the filed measurement is what the closed entry
      is measured against):
      ```
      20 A=1EX    ref -> A <EF> <1D>A<10><00><00> X     a SINGLE 1, the `E` EATEN
                  zb  -> A <EF> <12> E X                the INTEGER 1, `E` left
      20 A=1E+X   ref -> A <EF> <1D>A<10><00><00> X     the `+` eaten too
      ```
      ⚠️ **The `0` rows are why it was not D-DECBLANK**: `dec-expbad0` /
      `dec-expbadsg0` carried no blank and read identically to their blanked
      twins ([`docs/decblank-msx1-characterization.md`](docs/decblank-msx1-characterization.md) §3).
      All four were live in `make lnblank-acceptance` as `KNOWN_DIVERGE`, pinned
      to their exact bytes — and the allowlist reporting them as AGREEING is the
      message that closed them. **That allowlist is now EMPTY.**

- [x] ✅ **A BLANK DOES NOT BREAK A VARIABLE NAME — LANDED 2026-08-01,
      125/125 at `--repeat 2`, 12 B, all sub-ROM, five knives.** Filed as
      *"`&B` is not a radix on MSX1 — and zerobas half-crunches it anyway"*
      (`dec-bin`, informational, from D-DECBLANK's denominator).
      🔴 **The `&` was a RED HERRING, and one row says so positively rather than
      by argument:** `20 A=&1` reads `A<EF>&<12>` on **both** references — a digit
      directly behind the `&` is crunched there too. The filed row's real content
      is `B1 1`, in which `B1` is an ordinary **variable name**:
      ```
      20 A=B1 1  ref -> A<EF>B1 1     zb -> A<EF>B1 <12>    NO `&` ANYWHERE
      20 A=B 1   ref -> A<EF>B 1      zb -> A<EF>B <12>     a LETTER sets it too
      20 B1 1=5  ref -> B1 1<EF><16>  zb -> B1 <12><EF><16> LVALUE position
      ```
      **R-N1: a blank is COPIED but changes no tokeniser state**, so the
      in-a-name flag survives a run of blanks — `B1 1` is the identifier `B11`,
      and `20 B1 1=7` reads back through `B11` as 7 on both references.
      ⚠️ **`dec-oct` had been saying so since D-DECBLANK**: `20 A=&O1 7` crunches
      its `7` on the references too, because an octal *token* is not a name. Same
      shape as `dec-bin`, opposite reading, and the only difference is whether a
      **name** preceded the blank.
      🔴 **And the defect was bigger than one byte.** `20 A=B 1 0`: the reference
      stores the identifier `B10` verbatim; zerobas stored `B`, a blank, and **the
      single literal 10** — having lost the name it handed the run to the decimal
      scanner, which then applied D-DECBLANK's joining. Two rules compounding,
      visible in exactly one row of the battery.
      🔴 **A KNIFE FOUND A LIVE DEFECT IN THE FIX'S OWN FIRST CUT.** `tk_copy` is
      the fallthrough target of the `is_letter` test, so a `tk_blank` parked just
      before it put **every punctuation character** through a store of a register
      `match_kw` had already clobbered — and that build passed the differential
      29/31, clean *by luck*. K2 exposed it via `20 A=B$1`, a row with **no blank
      in it at all**. `nam-paren`/`nam-parenblk` were added and oracle-locked
      because of it.
      Spec [`docs/spec-basic-nameblank.md`](docs/spec-basic-nameblank.md),
      measurement [`docs/nameblank-msx1-characterization.md`](docs/nameblank-msx1-characterization.md).
      `dec-bin` and `lit-varname` are **gating** rows now, not informational.

- [x] ✅ **THE MSX WORK-AREA DENOMINATOR EXISTS — `make sysvarsweep`, LANDED
      2026-08-01.** 279 named entries over `$F380..$FFFE` (3199 B), three sides,
      `--repeat 2`, boot-per-case, jittered. NO `basic/`/`sub/` change: this
      slice ends with a LIST, by design. Spec
      [`docs/spec-basic-sysvar-denominator.md`](docs/spec-basic-sysvar-denominator.md),
      measurement [`docs/sysvar-msx1-coverage.md`](docs/sysvar-msx1-coverage.md).
      **Scoped to meaning (2)** — does a READ return the same value — signed off
      before the probe was written; (1) is unobservable except through (2) and
      (3) is not a fidelity question.
      🔴 **THE FILED ROW WAS THE SMALLEST PART, AND THE NO-ERROR CONTROL IS WHAT
      SAYS SO POSITIVELY.** 19 bytes diverge under `GOTO 99999`, and the obvious
      write-up — *"19 bytes of error state diverge"* — is wrong by ~4×:
      ```
      s1-err   DIVERGE  CSRY KBUF+1..6 BUF CONTXT CONSAV CONTYP CONLO LINTTB | ERRFLG ERRLIN ERRTXT
      s2-noerr DIVERGE  CSRY KBUF+1..2 BUF CONTXT CONSAV CONTYP CONLO LINTTB | (+TEMP/TEMP2/TEMP3)
               `A=1` RAISES NO ERROR and moves the SAME set --------^
      ```
      **Exactly THREE variables are error-specific**: `ERRFLG $F414`,
      `ERRLIN $F6B3`, `ERRTXT $F6B7`. `KBUF`/`BUF` and the `CONT` anchor
      `CONTXT`/`CONSAV`/`CONTYP`/`CONLO` are rewritten on **every direct-mode
      line** on both references and never on zerobas. The class is not "zerobas
      ignores `ERRFLG`" but *"zerobas keeps its BASIC bookkeeping in its own RAM
      window while the published addresses stay at power-on values."*
      🔴 **AND LAYER 0 FOUND EIGHT MORE, WITH NO EMULATOR AT ALL.** zerobas'
      `sysvars.inc` shares 46 names with the published map: 38 at the published
      address, **8 RE-HOMED** — `VALTYP` `FRETOP` `SAVTXT` `SAVSTK` `ONELIN`
      `ONEFLG` `ARYTAB` `DEFTBL`, all into the same freed `$E1Cx`/`$E2xx` window
      with the same "own choice" provenance. ⚠️ A **LOWER BOUND**: it matches on
      the NAME, so `ERRCODE`-vs-`ERRFLG` (different spellings) is invisible to it.
      **Measurable surface is not 3199**: 6 B VOLATILE (`SCNCNT` `REPCNT`
      `JIFFY` `INTCNT` — all clock-derived, all BIOS-owned), 311 B NO-ORACLE
      (the two references are structurally different machines), ~2626 B INERT.
      **66 named variables diverge somewhere: 45 BASIC-owned, 21 BIOS-owned.**
      At cold boot **256 B** differ where both references agree (114 BASIC-owned)
      — `USRTAB`'s ten `$475A` vectors, `CS120`/`CS240`, `ENDPRG`, `CURLIN`.
      ⚠️ **Whether `ERRFLG` should MOVE to `$F414` remains a SEPARATE design
      question** — zerobas' memory map is its own and relocating live error state
      is not a free edit. Deliberately not started.
      ⚠️ **Three apparatus defects, each caught by a control rather than by
      luck** (docs §8): the volatility control was **connected to nothing**
      (`cap_gap` is the gap AFTER the capture and this probe is boot-per-case, so
      it reported `VOLATILE=0` over the whole work area, JIFFY included, while
      looking like it worked — and had PUBLISHED a false `REPCNT` finding);
      C-INSTR failed on all three sides from the payload's **own echo** supplying
      a bracket pair; and the table parser silently dropped the 10 inline-
      commented entries, `JIFFY` among them, then mislabelled the most volatile
      byte in the work area `PADX+1`.

- [x] ✅ **THE RE-HOMING CLASS: TEN DECISIONS RECORDED, FIVE ADDRESSES HONOURED
      AT ZERO ROM COST — LANDED 2026-08-01.** Filed by the sysvar denominator as
      *"8 published names at private addresses, and NOBODY DECIDED THAT"*.
      Decisions: [`docs/sysvar-rehoming-decisions.md`](docs/sysvar-rehoming-decisions.md),
      spec [`docs/spec-basic-sysvar-rehoming.md`](docs/spec-basic-sysvar-rehoming.md),
      **recorded beside each equate in [`basic/sysvars.inc`](basic/sysvars.inc)** —
      which was the deliverable. Four paired stimulus states added to
      `make sysvarsweep` (5 → 13), oracle-locked on both references at
      `--repeat 2` **before zerobas ran on any of them** (new `--sides` filter,
      so the ordering is a mechanism and not a promise).
      🔴 **SEVEN OF THE TEN ARE MEASURABLY THE SAME VARIABLE.** Not ten designs
      placed for space — one design at a different address. `ERRFLG` `00→08`,
      `ERRLIN` `→FFFF` direct / `→20` from a stored line, `ONELIN` `→$8015`,
      `ARYTAB` byte-identical in all four direct-mode states, `DEFTBL` 25/26 B
      identical, `FRETOP` `SAME-DELTA` −4/−20; `ONEFLG` same role with a
      different sentinel.
      ✅ **HONOURED (zero ROM bytes each — every access was already symbolic, so
      an `equ` change is an assembler constant; low still 23 B, page 1 still
      8 B):** `ERRCODE`→**`ERRFLG $F414`**, `ERRLINE`→**`ERRLIN $F6B3`** (renamed
      too — the off-book spelling is *why* the static name-match could not see
      the pair that started this item; the layer now reports **43 honoured / 5
      re-homed**, was 38/8), `ONELIN $F6B9`, `ONEFLG $F6BB` (+ sentinel `1`→`$FF`,
      measured, control-flow-neutral), `DEFTBL $F6CA`.
      🔴 **MIRRORING WAS SIGNED OFF AND THEN REFUTED BY AN ALREADY-FILED ROW.**
      `POKE&HF414,0 : PRINT ERR` prints `0` on both references — `ERR` **reads**
      `$F414`, so a write-only mirror satisfies `PEEK` and **fails** `POKE`. The
      cheap way out of *"moving live error state is not a free edit"* was
      measurably insufficient, and the edit was free anyway.
      ❌ **REJECT-GROUP:** `ARYTAB` and `FRETOP` — both *SAME-VAR/SAME-DELTA* and
      still refused, because their consumers read a **chain**
      (`TXTTAB≤VARTAB≤ARYTAB≤STREND`; `FRETOP` against `MEMSIZ`/`STKTOP`) and
      zerobas has no stored `VARTAB`/`STREND`/`MEMSIZ`/`STKTOP`. Publishing one
      end of a subtraction yields a **confident wrong answer** where today a
      consumer gets `0−0` and an obviously dead reading.
      ❌ **REJECT-UNOBSERVABLE:** `VALTYP` (refs constant `$03` in all 9 states)
      and `SAVTXT` (refs pinned at `$F40F`) — 🔴 *"never moves"* here means the
      question could not be PUT, not that there is nothing to honour.
      ⏸ **DEFER:** `SAVSTK` — `NO-ORACLE` absolutely **and** `refsΔ=+0`; the
      settling measurement is named (capture INSIDE a running statement).
      🔴 **THE FILED TITLE WAS WRONG TWICE.** *"Nobody decided that"* is false for
      `VALTYP`: [`basic/usr.asm:19`](basic/usr.asm:19) already carried a
      **measured, oracle-locked** decision naming `$F663`. And *"per variable"* is
      the wrong unit — signed off as **decide per variable, reason per group**.
      🔴 **A knife on my own fix:** the new delta branch returned `DIFF-DELTA` for
      every one-sided movement, so `SAVSTK` read as *"zerobas moves it wrongly"*
      when the references never move it at all — the absolute branch had always
      said `ZB-ONLY` for that shape, and **the two branches were answering the
      same question differently**.
      🔴 **THREE OF THE APPARATUS' OWN CONTROLS WERE INVERTED BY THIS FIX, AND
      THE THIRD WAS MISSED — THE GATE CAUGHT IT, NOT THE AUTHOR.** `C-REPRO`
      (`$F414` must DIVERGE) and `C-REPRO-2` (the value must live at `$E1C5`)
      both asserted the state this slice deliberately ended, and were re-aimed at
      the new known answer — each **strictly stronger** than what it replaced,
      since the old `C-REPRO` passed whenever zerobas did *nothing at all* with
      `$F414`. **`C-PRIV` was pinned on `DEFTBL['A']` at `$F153` — an address
      this slice HONOURED away** — so it failed and voided the post-fix run,
      correctly. Re-anchored on `ARYTAB $E1C0`, chosen *because* its verdict is
      REJECT-GROUP and it therefore stays private by decision. ⚠️ The lesson was
      written down **earlier in this same slice** than the instance that proved
      it: a rule stated is not a rule applied.
      New controls, all now firing: **C-PRIV** (the private segments must be
      shown to MOVE), **C-REPRO-2**, and 🆕 **C-VACATED** — the five addresses the
      honoured variables moved OUT of must go QUIET, because a leftover store at
      an old address is a half-done relocation that every other check reports as
      green.

- [x] ✅ **`DEFTBL_STR` SHOULD BE `3`, NOT `1`.** Filed 2026-08-01 by D-REHOME,
      closed 2026-08-01 by **D-DEFSTR**
      ([`docs/spec-basic-deftbl-strcode.md`](docs/spec-basic-deftbl-strcode.md)).
      All 26 published `DEFTBL` bytes now match both references in every measured
      state. 🔴 **The filed reason was not the live hazard.** `1` was not an
      own-design sentinel colliding with the numeric *widths* `2/4/8`; it was an
      accidental collision with zerobas' **variable-chain string type tag, which
      is also `1`** — a second, own-design namespace that overlaps the published
      one on the numeric values. Three sites fed a published code straight into
      the chain, and one of them was a **live memory corruption**:
      `DEFSTR I:FOR I=1 TO 3` reached `var_store_fac` with type `1`, which is
      simultaneously the chain's string tag *and* an `ld c,a`+`ldir` byte count —
      so it allocated a real STRING entry and wrote one byte of FAC over its
      descriptor's `len`. PRINT then dumped arbitrary RAM. **The coincidence at
      `1` is what kept it quiet**, and changing the constant alone would have
      relocated the corruption into phantom `type=3` entries, not removed it.
      Every published→chain crossing is now checked (`deftbl_num_type` /
      `check_vartype_num`, low region). 16 of 18 measured rows now match both
      references, up from 12; **11 green controls held**. Cost −14 B low region,
      −3 B page 1, exactly as the spec predicted.
      🔴 And three rows that **agreed** agreed for the wrong reason: `B=S` is
      caught by `ev_rel`'s `str_eval` probe, which sits at the TOP of an operand
      only — `B=1+S` was not, and silently read 0 where both references raise
      ERR 13. Stopping at the top-level shape would have filed B1 as dead code.

- [x] ✅ **TWO ACCEPTANCE SUITES ARE STANDING-RED WITH NO EXPECTATION WRITTEN
      DOWN.** Filed 2026-08-01 by D-DEFSTR, **closed the same day by D-EXPKW** —
      [`docs/spec-basic-expkw.md`](docs/spec-basic-expkw.md), measurement
      [`docs/expkw-msx1-characterization.md`](docs/expkw-msx1-characterization.md).
      Neither suite was edited and neither was pinned: **both went green off one
      22-byte change**, because they were never two failures.
      🔴 **ALL THREE FILED CLAIMS WERE THE WRONG SUBJECT.**
      * *"`float-acceptance` → `reg.C.if_skip_over_float`, likely the `$0E`/`ELSE`
        class"* — not the `$0E` class, not `tok_skip`'s float stride (which
        strides `$1D` correctly, `basic/tokskip-body.inc:31`), not
        `if_skip_to_else`, **and not about floats**: the same line with an
        INTEGER literal breaks identically (`expk-ifelsei`, pinned as that
        battery's control and measured RED).
      * *"`logicops` → 50 rows, all `EQV`/`IMP`, both unimplemented"* — `EQV`/`IMP`
        **landed** in `ef098e9` at 156/156 (`basic/expr.asm:148`). Of the 49
        failing rows **every one contains `EQV`; not one fails on `IMP` alone.**
        `PRINT 0 EQV 0` printed three items: `0`, the variable `QV`, `0`.
      * *"two unrelated standing failures"* — **one defect.** `ELSE` and `EQV` are
        the only reserved words in the language beginning with `E`, and the
        literal scanner was eating that `E`.
      🔴 **AND IT WAS A REGRESSION, NOT A STATUS QUO.** `4b2202e` (D-EXPBAD)
      deleted the rollback on the finding *"THE DIGITS ARE OPTIONAL AND THERE IS
      NO FAILURE CASE"* — generalised from five rows (`1E`, `1E+`, `1D`, `1E#`,
      `12345EX`) **none of which puts a reserved word behind the marker.**
      ⚠️ D-DEFSTR's A/B could not have caught it: it stashed **`basic/`**, but
      `tkf_try_exponent` is in **`sub/tkfloat.asm`**. The A/B answered "not mine"
      correctly; the conclusion drawn from it — *"standing state, pin it"* — did
      not follow. **A NOT-MINE FALSIFICATION SAYS NOTHING ABOUT WHOSE IT IS.**
      Measured rule (76 rows, both references agree, oracle-locked first): an `E`
      marker is **not a marker when the next character — across blanks,
      case-folded — is `L` or `Q`**; `D` has no protected letter (26/26 eaten).
      It is a **LETTER** test, not a keyword match: `1 EQ`/`1 EL` keep the marker
      though neither is a word, `1 ERL`/`1 DIM` lose it though both are.

- [x] ✅ **`logicops-acceptance` WAS NOT IN THE DOCUMENTED CORPUS.** Filed and
      fixed 2026-08-01 by D-EXPKW. **This is the reason the regression above was
      invisible for two slices**: `make logicops-acceptance` (193 rows, ~40 s) is
      a standing gate of the same rank as `float-acceptance`, but no spec's
      "full corpus" list named it, so nothing ran it after `4b2202e`. It is a
      **required corpus member** from here on, alongside:
      `unit-test` 55/55 · dead-code gate 0/0 both builds ·
      **`lnblank-acceptance` 327/327 with `KNOWN_DIVERGE` EMPTY — note the target
      defaults to `--repeat 1`, so the corpus run is
      `make lnblank-acceptance REPEAT=2`** · **`logicops-acceptance` 193/193** ·
      `float-acceptance` (exits 0) · `array-acceptance` 149/151
      (`ifc.instr.zero`, `ifc.instr.neg` by name) · `arrdim` 73/73 ·
      `clearpool` 52/52 · `badfnum` 93 · `lof` 45 · `chancost-characterize` ·
      `diskbasic` 34/34 · `bdos` 12/12 · `fat-error` · `error-trap` ·
      `abort` 49/49 · `stop`/`strig`/`key`-trap · `linemax` 60/60 ·
      `sysvarsweep` exit 0 with all five controls green.
      ⚠️ **A GATE NOBODY RUNS IS NOT A GATE.** It was green at 193/193 when it
      landed and nothing re-read it; the suite reported its own failure honestly
      for two slices to an empty room.

- [ ] **`float-acceptance` HAS NO NAMED EXPECTED-FAILURE MECHANISM.** Filed
      2026-08-01 by D-EXPKW. The suite is green today, so this is not urgent —
      but it reports `371 PASS, 1 FAIL` and exits non-zero with **nothing naming
      the expected count**, which is exactly what made the D-EXPKW regression
      unreadable for a whole slice. `array-acceptance`'s 149/151 names
      `ifc.instr.zero`/`ifc.instr.neg`, and lnblank's `KNOWN_DIVERGE` pins each
      entry to its exact observed value so a row that silently starts passing
      breaks the gate. `float-acceptance` has neither. ⚠️ Give it the
      *control* shape, not the suppression shape.

- [ ] **ZEROBAS HAS NO STRING `READ`.** Filed 2026-08-01 by D-DEFSTR, found by
      rows aimed at the `DEFTBL_STR` sentinel. Both references read `DATA 42`
      into a `DEFSTR`'d `X` as the **string** `"42"` — `[42]`, not `[ 42 ]`, so
      the missing spaces are the tell — and `DATA AB` as `[AB]`.
      [`ex_read`](basic/program.asm:1310) consumes one letter and calls
      `read_one_value` for an int16, with **no `$` path anywhere**; `READ X$` is
      unsupported by construction, so a `DEFSTR`'d target had nowhere to go.
      D-DEFSTR turned that from **memory corruption** into a clean ERR 13, which
      is strictly closer and still divergent. These are the only 2 of D-DEFSTR's
      18 rows that do not match the references, and they are deliberately **not**
      gate rows — a row that can only ever be red is doc debt, not a gate.

- [ ] **THE TWO TYPE-CODE NAMESPACES SHOULD PROBABLY BECOME ONE.** Filed
      2026-08-01 by D-DEFSTR. The references use `3` for **both** the DEFtbl code
      and the variable-chain type byte, which makes `elsize == type` an identity
      and [`elsize_from_type`](sub/arrays.asm:845) — plus ~7 call sites —
      deletable. zerobas uses `1` in the chain with a `1 → 3` map.
      ⚠️ The chain's stored type byte is **RAM-observable**, so this needs its own
      oracle-lock on that byte before anything moves; D-REHOME measured only that
      the string scalar entry's SIZE agrees (+6 B, `ARYTAB $8003→$8009`), never
      its contents. ⚠️ Also note the entry field ORDER may differ from the
      reference's — unmeasured. A separate slice, not a ride-along.

- [x] ✅ **`20 GOTO 99999` — CLOSED BY D-LNREF 2026-08-01, and the "3 bytes"
      was a SPLIT.** Filed by D-REHOME from `s7-fired`'s `ONELIN`/`ARYTAB`
      pointers — a LENGTH, never the bytes — and its own note that this was
      "likely related" to the `$0E` item was right for the wrong reason.
      🔴 **The reference does not wrap, saturate or refuse: it SPLITS the digit
      run.** A line-number reference accumulates only while the value would stay
      **≤ 65529**, and the first digit that would exceed it starts a NEW
      reference, because the mode is still armed. `GOTO 99999` is
      `$0E,9999` `$0E,9`; `GOTO 65530` is `$0E,6553` `$0E,0`. Same constant as
      the LEADING line number's ceiling, different response.
      Both items were ONE mechanism. Spec
      [`docs/spec-basic-lnref.md`](docs/spec-basic-lnref.md) **R-V**,
      measurement [`docs/lnref-msx1-characterization.md`](docs/lnref-msx1-characterization.md) §2.

- [ ] **HOW MUCH OF THE 311-BYTE `NO-ORACLE` BUCKET IS A POINTER?** Filed
      2026-08-01 by D-REHOME. `FRETOP` sat in that bucket scored as *"no
      reading"* while all three sides agreed **perfectly** on the movement
      (−4/−20). The sweep now has a `SAME-DELTA` verdict, but it is only applied
      in the re-homing table — **the 3199-byte census still classifies every byte
      absolutely.** 🔴 `NO-ORACLE` is a verdict about the COMPARISON, not about
      the variable, and the bucket is an over-count by an unmeasured amount.
      ⚠️ A byte-wise delta pass needs a rule for what counts as a pointer PAIR;
      naive per-byte deltas on a 16-bit cell will agree by luck on the high byte.

- [ ] **zerobas' `VALTYP $E0C8` READS `$FF` AT COLD BOOT** — neither of its two
      documented values (`0` numeric / `1` string). Filed 2026-08-01 by D-REHOME
      from the new private-cell capture. Benign today (written before read at
      every eval), so this is a *hygiene* item, not a defect — but it is exactly
      the shape that becomes one when a new caller reads before writing.

- [ ] **`dir-name` — A BLANK INSIDE A NAME IS NOT READ BACK IN DIRECT MODE.**
      Surfaced 2026-08-01 by the first full `--say` pass across all three sides
      (D-CNAME ran one; nothing else does). Oracle-locked, both references agree:
      ```
      B1 1=7 : PRINT"[";B11;"]"    vg8020 -> 7    cf3300 -> 7    zb -> 0
      ```
      D-NAMBLANK's **R-N1** says a blank is copied but changes no tokeniser state,
      so `B1 1` is the identifier `B11` and the assignment must be readable back
      through it. The references do exactly that; zerobas reads **0**.
      ⚠️ **NOT caused by D-CNAME** — that change touches only `tk_call_name`,
      reachable solely from the `CALL` token dispatch and `tk_underscore`, and
      this payload has neither. Reachability argued, **not re-measured against
      HEAD**; do that first.
      🔴 **THE ROW HAS NEVER GATED ANYTHING.** `--say` rows are filtered out of
      `lnblank-acceptance` entirely, and the probe's own comment already recorded
      that it "was dormant, not green" for a *different* reason. So the whole
      `--say` surface is un-gated and this is what was hiding in it — the same
      shape as the SILENT-GAP class. **Ask what else the say pass says before
      fixing this one row.**
      ⚠️ **PARTLY ADDRESSED 2026-08-01 by D-LNREF: `make lnblank-say-acceptance`
      exists and gates `ONLY=lnrd-`.** It was added because that slice's
      load-bearing control (`lnrd-erl`) was itself sitting in this un-gated
      surface — knife K4 shows the regression it catches passing the MEMORY gate
      3/3 while the program raises `Syntax error`. The default is scoped to
      `lnrd-` precisely because THIS row is red, so a whole-surface default would
      ship a red target. **Widening that default is the fix for this item.**

- [x] ✅ **THE `CALL` DEVICE-NAME SCAN IS A RANGE TEST, NOT AN IDENTIFIER SCAN —
      LANDED 2026-08-01, 251/251 at `--repeat 2`, NET −10 B, all sub-ROM, seven
      knives.** Filed by D-LNLIST as *"the scan stops short — the reference
      reaches further"*, from three rows that were **all** written to ask a
      different question and had their digit eaten before they could ask it.
      🔴 **THE DIRECTION WAS RIGHT AND THE RULE WAS WRONG, IN BOTH DIRECTIONS.**
      The obvious rule from the filed rows — *copy identifier characters and
      blanks, drop everything else* — is refuted, and so is the narrow *"only the
      `+` is swallowed"*:
      ```
      20 CALL X+5   ref -> <CA> X5     the '+' is DROPPED
      20 CALL X;5   ref -> <CA> X;5    the ';' is KEPT and the scan RUNS ON
      20 CALL X:5   ref -> <CA> X:<16> the ':' TERMINATES
      ```
      🔴 **AND THE OPERATORS LAND ON BOTH SIDES.** `+ - * /` are dropped;
      `^ \ = < >` are kept. Nine operators split down the middle, so neither
      operator-ness nor the token byte separates them — the same interleaving
      shape D-LNLIST hit. What separates them is the **ASCII range**: once EOL,
      `:` and `(` are taken out, a character is discarded **iff `' ' < c < '0'`**.
      All fifteen characters of `$21..$2F` were walked contiguously, and every
      printable character at or above `$3B` that this harness can deliver — so
      both classes are denominators, not samples. **Three rows were structurally
      incapable of finding this**; each agrees with two different wrong rules.
      🔴 **THE FIX DELETES A SUB-ROM ROUTINE AND THE DEAD-CODE GATE FORCED IT.**
      `basic/vars.asm` is not included by `sub/sub.asm`, so the new range test
      orphaned the sub-local `is_ident_cont` clone — `make basic-reloc` failed the
      build rather than shipping 16 dead bytes. **Knife K6 is that argument turned
      into a measurement**: it restores the clone with no caller and the *build*
      goes red. NET **−10 B** (+6 loop, −16 clone), sub page 0 3998 → **4008 B**
      free; both main ROMs **byte-identical**, asserted by hash.
      ⚠️ **THE THREE `KNOWN_DIVERGE` ROWS RETIRE AND THE ALLOWLIST IS NOW EMPTY** —
      the fifth cohort to leave it that way, and not one has rotted.
      ⚠️ Three apparatus findings, each caught by a guard rather than by luck:
      `{` `|` `}` are **not deliverable** (the `}` row returned a stable,
      both-references-agreeing `<CA> X{5}` from a payload with neither brace — a
      perfect fake the echo guard killed); the echo guard's payload ceiling is the
      **display width**; and `cnm-lower` mangles **intermittently in a batch**,
      which `--repeat` cannot catch.
      Spec [`docs/spec-basic-cname.md`](docs/spec-basic-cname.md), measurement
      [`docs/cname-msx1-characterization.md`](docs/cname-msx1-characterization.md).

- [x] ✅ **A LINE-NUMBER LIST IS A MODE, NOT A LIST — LANDED 2026-08-01,
      NET +26 B, all sub-ROM, seven knives.** Filed by D-NAMDOT as *"a `.` does
      not end a line-number list"*, from the single `dot-goto` row.
      🔴 **THE FILED TITLE WAS REFUTED AND THE `.` WAS NEVER THE SUBJECT.** A
      dozen measured characters do the same thing:
      ```
      20 GOTO 1+5    ref -> <89> <0E><01><00><F1><0E><05><00>
      20 GOTO 1;5    ref -> <89> <0E><01><00>;<0E><05><00>
      20 GOTO 1.5.7  ref -> <89> <0E><01><00>.<0E><05><00>.<0E><07><00>
      ```
      After a branch keyword the reference is in a **MODE** that runs to the end
      of the **statement**: every digit run that would begin a numeric constant
      becomes `$0E,<line>` instead, whatever stands between them. Fixing it from
      the row that found it would have added `.` to a separator test and shipped
      a rule a dozen characters too narrow — **and `dot-goto` cannot tell the two
      rules apart**, because both predict its exact bytes.
      🔴 **WHAT DISARMS IT IS ALPHABETIC-vs-SYMBOLIC, AND THAT CANNOT BE TESTED
      AS A TOKEN VALUE.** `\` is `$FC` and *keeps* the mode; `MOD` is `$FB` and
      *clears* it; `PRINT` is `$91`, below both, and clears. The classes are
      interleaved, so no threshold or mask separates them — words and variable
      names clear, symbols and punctuation do not, and `:` clears.
      🔴 **THE FIX SHRINKS `branch_lineno`.** `bl_yes`' blank loop, `bl_num`'s
      comma test and `bl_list` are **deleted**: ordinary `tk_loop` already copies
      blanks, commas and punctuation, which is what they were hand-rolling. The
      empty-slot bug `bl_num`'s comment records is **dissolved** rather than
      re-fixed — `lnl-empty`/`lnl-empty2` (`ON KEY GOSUB 100,,600`,
      `ON STRIG GOSUB ,300`) match the reference byte-for-byte with the special
      case gone.
      ⚠️ **Two of my own rows were CONFOUNDED and are written up as such**:
      `lnl-colon` carries a *name* behind its colon (so it could not measure the
      colon at all — `lnl-colsep` does), and all three `CALL` rows had their
      digit eaten by the device-name scan (filed above; `lnl-callpar` got past it
      with a `(`). Seven knives, all run and reverted, each with a RED set **and**
      surviving GREEN controls.
      `dot-goto` **retired** from `KNOWN_DIVERGE` — the fourth cohort to leave it
      that way, and not one has rotted.
      Spec [`docs/spec-basic-lnlist.md`](docs/spec-basic-lnlist.md),
      measurement [`docs/lnlist-msx1-characterization.md`](docs/lnlist-msx1-characterization.md).


- [x] ✅ **`.` IS AN IDENTIFIER CHARACTER TO THE TOKENISER — LANDED 2026-08-01,
      148/148, NET −10 B, all sub-ROM.** Split out of D-NAMBLANK, which filed it
      from two rows and did not fix it. Spec
      [`docs/spec-basic-namedot.md`](docs/spec-basic-namedot.md), measurement
      [`docs/namedot-msx1-characterization.md`](docs/namedot-msx1-characterization.md).
      Two rules, both in one five-line dispatch arm:
      **R-D1** a `.` behind a LIVE name state continues the identifier;
      **R-D2** a `.` with the state DEAD begins a numeric constant **and the
      digit is OPTIONAL** — a bare `.` is the single literal 0.
      🔴 **THE FILED PRESCRIPTION WAS REFUTED BY MEASUREMENT, AND THAT WAS THE
      WHOLE SHAPE OF THE SLICE.** This item said in as many words that
      [`basic/vars.asm`](basic/vars.asm)'s run-time scan *"has to accept `.` as
      well, or the executor looks up a different variable than the tokeniser
      stored"*. **The reference does exactly that forbidden thing**: `B.5=7` and
      `A=B.5` both raise `Syntax error` (ERR=2) against a `B5=7` control reading
      ERR=0 — the crunch's identifier charset and the executor's are *different
      charsets* on MSX1. Knife **K4** made the prescribed change and turned both
      rows ERR 2 → 0, i.e. **the filed fix would have shipped a live divergence
      in the exact place the item pointed at**. So `vars.asm` was never touched,
      neither were `DEFINT`/`DEFSNG`/`DEFSTR`, `VARPTR`, `FOR` variables,
      `DIM`/array names or `INPUT`/`READ` targets, and the whole change is
      **sub-ROM only** — both main ROMs byte-identical to the parent commit,
      asserted by hash.
      🔴 **AND THE ROWS THAT FOUND R-D2 WERE WRITTEN TO BE CONTROLS.**
      `20 A=.B` and `20 .A=1` were filed as predicted-green two-sided cells and
      both refuted their own prediction: the reference stores `$1D,0,0,0,0`, so a
      `.`-led literal never needed its digit. That deleted the one-character
      lookahead instead of extending it — the correct rule was **smaller** than
      the wrong one, the D-EXPBAD shape.
      🔴 **A `<none>` READING ON BOTH REFERENCES WAS NOT AGREEMENT.** The first
      `dotd` payloads printed no closing `]` *because the behaviour under test
      aborted the statement*, so every side read `<none>` and compared EQUAL —
      the trap filed one item below. Reading the SCREEN found the `Syntax error`
      that became R-D3; the rows were re-asked through `ERR`, which prints its
      brackets whether or not the statement aborts.
      Five knives, all run and reverted: K1/K2 separate R-D1 from R-D2, **K3**
      separates R-D1 from *"a `.` is always an identifier char"* (a distinction
      neither filed row could make), K4 above, K5 shows the dot must **set** the
      name state. ⚠️ **K1 and K5 each refuted a predicted-GREEN control** —
      corrected in place, spec §7.1 — and a K1 `REFUSED` turned out to be a
      dropped keystroke that re-ran clean alone (§7.2).
      `nam-dot`/`nam-dot0` retired from `KNOWN_DIVERGE`; `dot-goto` filed above.

- [ ] **A `--say` row with no brackets cannot have a reading.**
      Found 2026-08-01 in D-NAMBLANK. `result_span_after_echo`
      ([`probes/lib/omsx_repl.py:518`](probes/lib/omsx_repl.py:518)) returns the
      text between the last `[` and its `]`, so a `SAY_ONLY` payload that prints
      no brackets reads `<none>` on **every** side — and sides that all failed
      compare EQUAL and report *agrees*. `basic_probe_lnblank.py`'s `dir-print`
      had been in that state since it was written (dormant rather than green: the
      gate filters `--say` rows out). Both its payload and the new `dir-name` are
      bracketed now and locked.
      ⚠️ **The class is not closed** — this was found in one probe by accident.
      Sweep every `SAY_ONLY`/`result_span` row in `probes/` for a payload that
      cannot produce a bracketed span, and consider making the helper *fail loudly*
      on a payload with no `[` in it rather than returning the same `None` a
      genuine abort returns. Same shape as [`chancost` NOREAD](docs/chancost-cf3300-characterization.md):
      a sentinel that also means "no reading" is not a measurement.

- [ ] **A TRAILING BLANK at end of line is not measurable through the keyboard.**
      Found 2026-07-31 in D-DECBLANK (`dec-eol` / `dec-eolctl`, both
      informational **by construction**). At `--repeat 2` the references drop a
      trailing blank and zerobas keeps it — in a `REM` tail as well as after a
      literal, and a `REM` tail is **verbatim**, so the difference is at **line
      ENTRY** (the editor), not in any scanner.
      ⚠️ But an earlier `--repeat 1` pass read the same `REM` row on zerobas
      *without* the blank, for a payload no crunch change can touch — so the cell
      is not stable enough to ground a rule, only to be filed.
      ⚠️ **The echo guard cannot referee it**: `echo_missing()` `rstrip`s every
      screen row, so a trailing blank is invisible to the guard no matter what the
      machine did with it, and a payload whose delivery cannot be verified may not
      gate. Resolving the cell needs a delivery path that bypasses the line editor
      — an ASCII `LOAD"CAS:`, the way `basic_probe_floatlit.py` reaches literals.
      Detail: [`docs/decblank-msx1-characterization.md`](docs/decblank-msx1-characterization.md) §5.

- [x] ✅ **DECIMAL LITERAL SCANNER AND EMBEDDED BLANKS — LANDED 2026-07-31,
      81/81, 39 B, all sub-ROM.** Split out of D-LNBLANK, where it was the
      *unfiled* half of the finding. Blank-transparency is **not** a property of
      the line-number scan;
      it is a property of the decimal number scanner, and the line number is one
      of its customers. Measured byte-exact on the VG-8020 **and** the CF-3300,
      which agree ([`docs/lnblank-msx1-characterization.md`](docs/lnblank-msx1-characterization.md) §1/§11 D):
      ```
      20 A=1 0     ref -> A <EF> <0F><0A>   (the single literal 10, = `A=10`)
      20 A=1 . 5   ref -> A <EF> <1D>A<15><00><00>   (1.5, across TWO blanks)
      20 A=1E 2    ref -> A <EF> <1D>C<10><00><00>   (100)
      ```
      ⚠️ **And it does NOT reach everywhere** — the bounding controls are already
      measured and must stay green: a **hex** literal does *not* skip
      (`&H1 F` → `&H1` then ` F`), nor a **string** literal (`"1 0"`), nor a
      **REM** tail, and a variable name keeps its blank (`A B` stores `A B`).
      A fix written as "make the crunch's digit fetch blank-transparent" is
      therefore **wrong**, and only the hex row says so.
      Spec [`docs/spec-basic-decblank.md`](docs/spec-basic-decblank.md),
      measurement [`docs/decblank-msx1-characterization.md`](docs/decblank-msx1-characterization.md)
      (32 new rows, four oracle-lock rounds, both machines agree on every one).
      **Baseline 9/29; the five `lit-` `KNOWN_DIVERGE` entries are RETIRED.**
      🔴 **THE FILED ROWS WERE A SAMPLE, AND THE DENOMINATOR MOVED THE FIX TWICE.**
      1. **`20 A=1 +2` KEEPS ITS BLANK** (and `1  +2` keeps both). Every row filed
         with the item put the blank *between two things that both belong to the
         number*, so none could tell "skips blanks" from "skips blanks and keeps
         the ones it did not use". The rule is **the cursor reported is one past
         the last character actually CONSUMED** — and it is *not* the line
         number's rule, which eats exactly one separator blank. "Copy
         `parse_lineno`" would have been wrong, and only a row with a NON-digit
         past the blanks says so.
      2. **A FIFTH SITE, IN THE OTHER FILE.** `20 A=. 5` is 0.5 on both
         references. That decision is taken in `tk_loop`'s `'.'` dispatch
         ([`basic/tokenise.inc`](basic/tokenise.inc)) *before* `tk_float` is
         entered, so no change inside the scanner could reach it.
      The rule also reaches further than the item said: the dot from **either**
      side, the exponent marker, its **sign**, its **own digit run**
      (`1E 2 3` = 1E23), and the type suffixes — `20 A=1 #` is a **DOUBLE** on the
      reference, i.e. the divergence was in the token's TYPE.
      **Cost: 39 B, ALL sub-ROM page 0** (4057 → 4018 B free); main page 1 stayed
      at 8 B and the low region at 23 B, and `basic-reloc.rom` came out
      **byte-identical** — the whole space worry was checkable in one hash.
      🔴 **AND THE FIRST CUT WAS CATASTROPHIC WHILE THE BUILD WAS GREEN**: `pop af`
      is how the saved cursor is discarded, but **it LOADS A**, so placed before
      the digit was extracted it fed the source pointer's high byte to the
      accumulator — `A=1` crunched to the integer **187** and `A=1E2` refused the
      line. Dead-code gate green, main ROM byte-identical, diff reads correctly.
      The first gate run caught it.
      Falsified on five knives (K1–K5), each with its own witness and each pairing
      a red row with a GREEN control.

- [x] ✅ **THE `$0E` LINE-NUMBER REFERENCE — CLOSED BY D-LNREF 2026-08-01.**
      Filed as *"missing for LIST/DELETE/AUTO/RENUM/ELSE"*.
      🔴 **THE FILED LIST WAS WRONG IN BOTH DIRECTIONS, and only a walk of all
      162 reserved words could say so.** The reference arms on **fourteen**
      words, not five. Three of the filed five (`DELETE` `AUTO` `RENUM`) have no
      zerobas token at all, so their rows diverge for a SECOND reason and can
      attribute nothing — they are the keyword-gap item below, not this one. And
      three the item never named DO arm: **`RETURN` (`$8E`)**, **`ERL` (`$E1`)**
      and `LLIST` (`$9E`) — the first two are tokens zerobas already emits, so
      they were this defect and nobody had looked at them.
      🔴 **It is a LIST, not a range or a threshold.** `IF` (`$8B`) sits
      *between* four arming tokens; `ERROR`/`RESUME`, `TO`/`THEN`, `ERR`/`ERL`,
      `RENUM`/`DEFSTR` are adjacent pairs split across the boundary.
      🔴 **And one missing arm was a LIVE RUNTIME DEFECT.** `IF 0 THEN 20 ELSE
      30` raised **`Syntax error`** — `if_false` has always tested
      `cp LINENO_TOKEN` after the `$A1`, so the feature was written, reachable,
      and had never fired.
      Landed: four arms (`LIST` `ELSE` `RETURN` `ERL`) **+28 B sub page 0**, and
      `ev_f` learned the `$0B..$0E` family at **NET −1 B on main page 1**
      (5 → 6 B free) — `ERL=<n>` puts a `$0E` inside an expression.
      Spec [`docs/spec-basic-lnref.md`](docs/spec-basic-lnref.md), measurement
      [`docs/lnref-msx1-characterization.md`](docs/lnref-msx1-characterization.md).

- [x] ✅ **`DELETE` / `AUTO` / `RENUM` / `LLIST` — THE TOKEN HALF CLOSED BY
      D-KWGAP4 2026-08-01.** Filed as *"they have no token — and whoever adds
      them must add the arming byte too."* That was right, and it was one half
      of the surface: a missing **token** and a missing **statement**. The token
      half is now byte-exact on all four verbs; the statement half is re-filed
      immediately below with its numbers.
      Landed: four equates, four `kwtable.inc` entries and four `branch_lineno`
      arms — **+48 B, ALL sub-ROM page 0** (3958 → 3910 B free), and
      `basic-reloc.rom` / `zerobas-main-eu.rom` **byte-identical**, which is the
      hard equality a sub-ROM-only change allows. Low **9 B** and page 1 **6 B**
      untouched.
      🔴 **THE SEVEN `KNOWN_DIVERGE` PINS D-LNREF SPENT ITS EMPTY ALLOWLIST ON
      FIRED EXACTLY AS DESIGNED, AND WERE DELETED RATHER THAN UPDATED.** Sixth
      cohort to retire that way, none has rotted; `lnblank-acceptance`'s
      allowlist is EMPTY again. `lna-renum3`/`-auto2`/`-delrng` also left
      `INFORMATIONAL` — their attribution argument was precisely what this
      closed.
      🔴 **ADDING A TOKEN FOR AN UNDISPATCHED STATEMENT CHANGED NOTHING AT RUN
      TIME, AND THAT WAS MEASURED ON BOTH SIDES OF THE CHANGE.** The filed
      hazard ("a token may turn a working garbage parse into a new error class")
      is real in general and empty here: all four already raised **ERR 2** by
      four *different* accidental parses (`DE`+`LET`+`E`, `AU`+`TO`,
      `RENUM` verbatim, `L`+`LIST`) and now raise it by one deliberate path
      (`es_noentry` → `stmt_error`). New batteries `kwgd` (5 rows, three sides)
      and `kwgz` (5 rows, **zerobas only** — `AUTO` is interactive and `LLIST`
      hangs an unplugged `LPTOUT`, so `SIDE_LOCK` refuses a reference).
      🔴 **AND THE ECHO GUARD HAD NEVER SEEN A `--say` PAYLOAD IN THIS PROBE.**
      `--echo` shared the measurement pass's `SAY_ONLY` filter, so
      `--echo --only lnrd-` answered *"no rows selected"* — D-LNREF's spec §6
      claim covered the 210 rows the filter left. Fixed; all seven `lnrd` rows
      now read `ECHOED` on three sides. `--echo --say` is refused (combined, the
      say pass won inside `run_side` and `main()` printed an echo-FAILURE banner
      over readings that were never echo verdicts).
      Six knives, each with a predicted RED set **and** predicted GREEN
      survivors, all matched — including two predicted-GREEN ones (K3 table
      order, K6 list-vs-range) and K5, which aims at the *justification* and
      measured the 3 B/entry figure the scope decision rests on.
      Spec [`docs/spec-basic-kwgap4.md`](docs/spec-basic-kwgap4.md), measurement
      [`docs/kwgap4-msx1-characterization.md`](docs/kwgap4-msx1-characterization.md).
      ⚠️ **`INPUT$` IS NOT ABSENT** — `20 INPUT$ 10` reads `<85>$ <0F><0A>` on
      all three sides. The reference has no distinct token either, so zerobas is
      already byte-exact and the coverage sweep's "34 genuinely absent" is one
      too many. The `INTERVAL` shape, found by D-LNREF's walk. Still open.

- [x] ✅ **`DELETE <range>` — LANDED 2026-08-02 (D-DELETE), 34/34, six knives,
      `kwgd-delete`'s pin RETIRED.** Filed 2026-08-01 by D-KWGAP4; spec
      [`docs/spec-basic-delete.md`](docs/spec-basic-delete.md), measurement
      [`docs/delete-msx1-characterization.md`](docs/delete-msx1-characterization.md).
      🔴 **THE TWO ENDS OF THE RANGE ARE NOT SYMMETRIC, AND ONLY A CONTIGUOUS
      WALK COULD SAY SO.** The HIGH end must name a stored line **exactly**; the
      LOW end need not name anything at all. `DELETE 15-30` deletes lines 20 and
      30 without complaint; `DELETE 20-35` deletes **NOTHING** and raises ERR 5 —
      the same shape with the missing number moved across the `-` (` 9  0 ` vs
      ` 15  5 `). Four more the filed one-line row could not have carried:
      * **the existence check runs BEFORE the first deletion** — `DELETE 20-35`
        leaves lines 20 *and* 30 standing, which an implementation that deleted
        as it walked could not do;
      * **a REVERSED range is a SECOND rule, not the same one.** `DELETE 30-20`
        is ERR 5 even though line 20 exists, so R-D2 passes and a machine
        deleting the empty range would read ` 15  0 ` (`dlt-rev`);
      * **a FAILED `DELETE` is a COMPLETE no-op** — variables and the `CONT`
        point both survive (`dlt-varsbad`/`dlt-contbad`). ⚠️ **No round-1 row
        could see this**: every failure row `RUN`s afterwards and `RUN` clears
        the variables itself. It took a round-2 cut;
      * **`DELETE` ENDS the line and the program.** Inside a `RUN` nothing
        further executes (`dlt-inprog`); in direct mode `DELETE 20:B=9` leaves B
        at 0 with **ERR 0** — the `:` is accepted and then abandoned, not
        rejected (`dlt-tail`, against `dlt-tailctl`'s ` 9  0 `).
      🔴 **AND `DELETE 10-65529` IS ERR 5** — the natural *"everything from line
      10 on"* idiom. Every round-1 high end that failed sat inside the program's
      span, so *"a line numbered exactly `hi` must exist"* and the far weaker
      *"`hi` must not be past the last line"* agreed on all of them;
      `dlt-hipast`/`dlt-hitop` are the round-2 rows that separate them.
      🔴 **A DEFECT IN `CONT`, NOT IN `DELETE`, AND THE ROW THAT SAYS WHOSE.**
      `dlt-cont` read ` 0  0 ` against ` 0  17 ` the first time zerobas had a
      handler. The obvious reading — "DELETE fails to invalidate CONT" — is
      refuted by its own `A` of 0, which proves the edit reset *did* run.
      `ex_cont_no` printed *can't continue* and **never set `ERRFLG`**;
      `err_msgtab` had mapped ERR 17 → `err_cont` all along. `dlt-contbare` (a
      bare `CONT`, no DELETE anywhere) is the attribution row. +5 B.
      Landed: 3 B `stmt_table` row + a **34 B** marshalling head on main page 1,
      the WHOLE verb (parse, both validations, the delete walk) as
      `LE_OP_DELRANGE` in `sub/lineedit.asm` — **194 B of sub page 1**, which had
      3339 B free. A resident parse would have cost ~88 B of page 1 against 34;
      knife K6 measured that claim rather than leaving it an estimate. Page 1
      **124 → 82 B**, low **23 B untouched**.
      ⚠️ **`.` — the CURRENT-LINE pseudo-line-number — is MEASURED and
      DECLINED**, not overlooked: `dlt-dotedit` says it is the line the editor
      **last touched** (not the highest — `dlt-dot` alone could not tell those
      apart). It is shared with `LIST`/`AUTO`/`RENUM`/`EDIT`, zerobas records
      nothing of the kind, and what `.` means after a `RUN` / an error / a `LIST`
      is unmeasured. Its own item is filed below; `dlt-dot`/`dlt-dotedit` are
      pinned so it cannot be forgotten.

- [ ] 🔴 **`AUTO` / `RENUM` / `LLIST` ARE STILL NOT EXECUTED — and the filed
      reason "none of them fits on main page 1" is STALE.** Re-filed 2026-08-01
      by D-KWGAP4, narrowed 2026-08-02 by D-DELETE. The crunch is the
      reference's byte for byte; all three are a **Syntax error** at run time.
      Measured, both references agreeing:
      ```
      10 A=1 : 20 A=2:END : RENUM 100 : GOTO 110   refs -> A=2 ERR 0   zb -> A=0 ERR 8
      ```
      `kwgd-renum` is **pinned as `KNOWN_DIVERGE`** in the say gate, so the day a
      handler lands the gate says so.
      ⚠️ **THE WALL MOVED AND THE FILED VERDICT DID NOT.** D-KWGAP4 costed four
      dispatch rows at 3 B each (its knife K5 — still the right rate) against a
      page 1 with **6 B** free, and concluded the rows alone did not fit.
      D-RETLN's 160 B dead-instruction carve took page 1 to 124 B; D-DELETE spent
      42 of those and left **82 B**. Space is no longer the reason. **Re-measure
      from a clean build before citing any byte figure written before
      2026-08-02.**
      What still blocks each one is its own body: **`RENUM`** needs a two-pass
      old→new map over every line number *and* every `$0E` reference including
      `ON..GOTO` lists; **`AUTO`** must drive the line editor (a sub-ROM page-1
      tenant) from a main-ROM statement; **`LLIST`** is cheapest — a printer sink
      exists ([`basic/print.asm:401`](basic/print.asm:401), `PRDEST=1` →
      `LPTOUT`) and `ex_list` exists, so its handler is "set the sink, jump to
      `ex_list`" — but it would inherit the filed `ex_list`-ignores-its-argument
      defect below.
      🎯 **D-DELETE is the worked precedent for all three**: the whole verb goes
      into an existing sub-ROM page-1 tenant and main pays a ~34 B marshalling
      head, with `LE_STATUS` carrying the ERR code back
      ([`docs/spec-basic-delete.md`](docs/spec-basic-delete.md) §3.1).
      ⚠️ **`AUTO` and `LLIST` CANNOT BE PUT TO A REFERENCE IN THIS HARNESS** —
      interactive line-entry and an unplugged-`LSTOUT` hang, the same reasons the
      keyword sweep already files them among its 18 crunch-only holes. `omsx_repl`
      raises `SystemExit` at its 240 s cap, so such a row does not degrade a run,
      it kills it. Whoever implements them needs a plugged printer
      ([[openmsx-printer-pluggable]]) or a different instrument first.

- [x] ✅ **D-LASTINJ — THE LAST INJECTOR COPY, AND THE SUITE NOBODY PRICED —
      LANDED 2026-08-04.** Spec
      [`docs/spec-probe-lastinj.md`](docs/spec-probe-lastinj.md),
      characterisation
      [`docs/lastinj-characterization.md`](docs/lastinj-characterization.md).
      **Apparatus only — one probe file, a new `tools/check_probe_injectors.py`,
      one Makefile target; no `basic/`, `sub/`, `disk/` or `tape/` source touched,
      no ROM rebuilt (`make -q build/zerobas-main-eu.rom` exit 0 throughout).**
      Closes the two items D-LATCH §6 filed and did not do.
      🔴 **BOTH FILED ITEMS RESTED ON A NUMBER OR A CLAIM NOBODY HAD CHECKED.**
      Item B's stated reason ("no Makefile target runs it") was FALSE — three
      structural readings falsify it without booting anything. Item A's stated
      cost (~3.5–4 h) was wrong by ~25× — the run is **8 min 58 s**. Two filed
      items, two justifications, neither measured, both wrong in the direction
      that deferred work.
      🎯 **204/204 gating rows agree**, exit 0, **zero** delivery announcements
      (stderr 0 bytes), and the guard was proven ARMED on say rows by a knife
      before that zero was read as a finding.
      🎯 **The copy was the frozen fault verbatim** — character-identical (after
      constant folding) to `latch_check.OLD_KEY`. Measured **latent, not
      harmless**: 0 of 16 slots at `$1197`, but slot 11 landed at `$119B` inside
      `chget`'s wait loop and the swallow law's precondition held **15/15**.
      🔴 **K2 says where `diskbasic-acceptance`'s sensitivity comes from.** With
      delivery mangled and only the probes' `== EXPECT` gutted, the runner reports
      `34/34`-shaped `ALL CONVERGED`, exit 0, over `records: []`. It checks an
      exit code and that `CF-3300` appeared; **all 34 registry rows inherit that**.
      🔴 **A knife of this slice's own failed to cut, and that was the finding**
      ([[knife-found-defect-in-own-fix]]): `injector-check`'s negative control
      emitted no `debug write memory` at all, so it was clean for a trivial reason
      and the "flag everything" half of its two-sided self-test was decorative.
      Rebuilt as a probe that pokes an unrelated address; both halves bite now.
      **K5's prediction was wrong in the safe direction** and is recorded as wrong
      rather than rewritten: gutting the verdict trips the frozen self-test first
      (`CANNOT JUDGE`, rc 2) instead of producing a green walk over a dirty tree.
      **Corpus:** unit 57/57 · preflight-check 0 unguarded · injector-check 0
      offenders · latch-check 9/9 · diskbasic-acceptance 34/34 ·
      lnblank-say-acceptance 204/204.

- [x] ✅ **D-LATCH — THE TRIGGER IS ONE INSTRUCTION WIDE — LANDED 2026-08-04.**
      Spec [`docs/spec-probe-latch.md`](docs/spec-probe-latch.md),
      characterisation
      [`docs/latch-trigger-characterization.md`](docs/latch-trigger-characterization.md).
      **Apparatus only — `probes/lib/omsx_repl.py`, a new
      `probes/lib/latch_check.py` and one Makefile target; no `basic/`, `sub/`,
      `disk/` or `tape/` source touched, no ROM rebuilt.** Closes D-DELIVER §9.1 /
      D-ECHO §6, the last open half of the delivery race.
      🎯 **The trigger is the instruction boundary at `$1197`** — between C-BIOS
      `chget`'s `ld hl,(GETPNT)` (`$1194`) and `ld de,(PUTPNT)`. An injector that
      moves GETPNT BACKWARDS is invisible to a CPU that latched it one
      instruction earlier, so `ld a,(hl)` reads the fresh buffer from
      `KEYBUF + N`. That is the swallow law, the alignment sensitivity, and why
      `step` "fixes" one case and not another, all from one register.
      **2039 slots across seven instrumented batches: 6 at `$1197`, 6
      mis-deliveries, none anywhere else.** Forced with a breakpoint at that
      address it mangles **every** time (4 predecessor lengths, 4 exact hits) and
      the three neighbouring boundaries deliver intact.
      🔴 **The hypothesis on file was inverted.** Nothing saves or restores a
      `GETPNT` — C-BIOS writes it in exactly three places and none of them is a
      restore. What survives the injection is a **register copy**. Right
      arithmetic, wrong object, and it would have sent the fix at a save site
      that does not exist ([[latch-trigger-is-a-register-not-a-save]]).
      🔴 **D-ECHO's "26-byte predecessor delivers clean" row was a PARTIAL
      READING.** It hits the trigger too (`HL = KEYBUF+26`); the swallow simply
      exceeds the payload, so the line arrives after garbage and the ECHO oracle
      cannot see it — the STORED oracle flags a spurious line `0`. The oracle
      that was asked was the blind one ([[readout-blind-to-its-own-subject]]).
      **Fixed at source:** `key_proc` writes at the current GETPNT and never
      moves it — immune by construction, not by alignment. Forced at `$1197`:
      100 % mangled → **0 %**. Phases O and Q2 go from 3 mis-deliveries to **0**.
      **`make latch-check` is the replacement positive control** and it is not
      optional: cross-oracle disagreement was the only live subject either
      delivery oracle had (D-ECHO §3.5), and fixing the race silences it forever
      ([[fixing-the-fault-silences-the-control]]).

- [x] ✅ **`lnblank-say-acceptance` WAS NOT RUN FOR D-LATCH — RUN 2026-08-04 BY
      D-LASTINJ, AND THE COST THAT DEFERRED IT WAS WRONG BY ~25×.**
      **204/204 gating rows agree** across `vg8020,cf3300,zb`, exit 0, and
      **zero** `MIS-ECHOED` / `MIS-DELIVERED` / `ORACLES DISAGREE` /
      `APPARATUS FAILURE` lines — stderr was **0 bytes**. No row moved, so the
      attribution path against `HEAD~1`'s injector was never needed. The D-LATCH
      injector change is priced across the last corpus member that had not seen
      it, and it costs nothing.
      🔴 **The zero was not accepted on its own.** This probe's own history is
      [[echo-guard-never-saw-say-rows]] — the `SAY_ONLY` filter once removed every
      one of these rows from the echo pass, so the guard reported zero BY
      CONSTRUCTION. With `key_proc` monkeypatched to swallow one byte per
      injection the same `--say --gate` rows produce `APPARATUS FAILURE` + five
      `MIS-ECHOED` announcements and rc 1; the identical unpatched subset is
      silent, rc 0. Knife fires, control silent, same session.
      🎯 **~3.5–4 h on file; 8 min 58 s measured**, `repack-machine` included —
      612 boot-per-case runs at ~0.9 s each. The figure predates the harness
      dropping sleep-polling and had never been re-measured. **A stale cost
      estimate is a standing argument for not running a gate**, and it won that
      argument once already: it is why D-LATCH skipped this suite. Corrected in
      [`Makefile`](Makefile) and here rather than left to be re-derived.

- [x] ⚠️ **THE SECOND LATCH WINDOW IS OPEN AND HAS NEVER BEEN OBSERVED.** A CPU
      inside C-BIOS `chget_char` (`$11A2`–`$119D`) holds an `HL` it is about to
      write back to `GETPNT`; an injection landing there advances GETPNT past the
      new payload by `HL - KEYBUF + 1`. It needs a NON-drained buffer, and the
      buffer was measured drained before **2039/2039** injections (D-LATCH) and
      490/490 (D-DELIVER) — but that is a measurement, not a proof, and it is why
      both delivery oracles stay armed after the fix
      ([`docs/spec-probe-latch.md`](docs/spec-probe-latch.md) §2.5).
      ✅ **CLOSED 2026-08-04 BY D-LATCH2**
      ([`docs/spec-probe-latch2.md`](docs/spec-probe-latch2.md),
      [`docs/latch2-window-characterization.md`](docs/latch2-window-characterization.md)).
      🔴 **THE WINDOW IS REAL AND `key_proc` WAS VULNERABLE TO IT.** Manufactured
      by breakpointing INSIDE `chget_char`, which the CPU enters **only** when
      `GETPNT != PUTPNT` — so the precondition and the force are ONE instrument,
      and the thing that made this unobservable for 2529 injections made it
      reproducible on demand. **44 of 46 predicted values hit exactly**; both
      misses were mine and both are recorded.
      🔴 **AND THREE FILED NUMBERS WERE WRONG.** (1) `$11A2`–`$119D` is not a
      range — it is `$11A3`–`$11AD`, and `$11A2` is on the SAFE side. (2)
      `HL - KEYBUF + 1` is the PRE-D-LATCH injector's swallow; the shipped one
      swallows **exactly 1, independent of k**, a number nothing on file
      predicted [[filed-justification-is-a-claim]]. (3) `latch-check`'s own
      *"~40 s"* is **2.05 s**, timed on HEAD — and that stale figure propagated
      straight into this slice's own ≈20 s estimate (measured **3.1 s** for 16
      rows) [[stale-cost-estimate-defers-gates]].
      🎯 **D-LATCH's fix OPENED a sub-window its predecessor could not reach**:
      `$11AA` (`ld hl,KEYBUF`) needs the consuming pointer to cross `KEYBUF+40`,
      which an injector that resets `GETPNT := KEYBUF` every time can never do.
      Fixed at source — `__key` will not write into a buffer the machine is
      still consuming (bounded deferral; the bound is **4× the buffer's own
      worst-case drain**, measured 10 retries / 20 ms for the maximum 39-byte
      pending line, and **10 % of `ECHO_GAP`**, past which the echo guard would
      judge a line that had not landed). `make latch-check` **16/16**, rows
      D/E/F, with THIS era's injector frozen as row D's subject
      [[fixing-the-fault-silences-the-control]] and row E scoring the deferral
      COUNT so the guard is green because it FIRED. Knives K2–K5 all cut
      (13/16 exit 1, or `CANNOT JUDGE`). New host pin `tests/test_key_drain_guard.py`
      — the D-LATCH invariant had **no** host-level test at all until now.

- [x] ⚠️ **`make injector-check` CLASSIFIES ITS OWN DETECTOR AS AN INJECTOR.**
      D-LATCH2's host test went red on it: the test emits no Tcl and boots
      nothing, but its `debug write memory` is the **needle of a regex** that
      asserts `key_proc()` does not write GETPNT, and it names the cursors
      because those are the addresses it checks. Closed for now as a fourth
      named structural exemption — the mechanism that gate provides — rather
      than by renaming the needle to slip past it, which would leave the next
      reader unable to tell evasion from innocence. **The open question is
      whether the classifier should distinguish a literal that is EMITTED from
      one that is MATCHED AGAINST**; it fails closed today, which is the right
      direction, but every future assertion-about-injectors file will need an
      exemption ([`docs/latch2-window-characterization.md`](docs/latch2-window-characterization.md) §10.1).
      ✅ **CLOSED 2026-08-05 BY D-INJSINK**
      ([`docs/spec-probe-injsink.md`](docs/spec-probe-injsink.md)).
      🔴 **BOTH filed claims were wrong, and the second one was hiding a live
      false negative.** The host test *could* be written non-evasively — the
      write format is `omsx_repl`'s to own, not the test's, and moving it to
      `omsx_repl.tcl_writes()` (a **bool**-returning predicate, so nothing can
      be composed out of it) leaves the test classifying `CLEAN` on the literal
      rule with zero residual occurrences (§2.1). Fourth filed justification
      running to be wrong [[filed-justification-is-a-claim]].
      🔴 **And "emitted vs matched against" is the wrong axis.** Measured
      (§2.3): the host test has **two** WRITE-bearing literals — the regex
      needle *and the docstring sentence beside it*. A per-literal sink
      whitelist clears the needle and not the prose, so it does not clear the
      file it was for; the all-uses rule that would clear prose is defeated by
      `return build([..., OLD_KEY])`, an ordinary probe shape. **No emit/match
      rule shipped**, and §2.3 says why in measurements rather than prose.
      🔴 **The real defect: the gate was blind across module boundaries.**
      `import latch_check; return latch_check.OLD_KEY` ships the pre-D-LATCH
      injector **verbatim** — the body `latch-check` row A requires to MANGLE —
      and the gate at `07e9c0a` scored that planted file **`ALL PASS`, 258
      files, 0 offenders, rc 0** (K3b). Closed by rule (b): naming a
      frozen-body symbol defined in another module IS the offence, no use
      analysis to fool. The registry is **generated** (5 symbols, 2 modules,
      basename-collision-free over 257 files) and **pinned** — an empty
      registry is `CANNOT JUDGE`, not a clean walk.
      🎯 **The exemption list does NOT shrink; it stops growing, and each entry
      now states a CLASS that is partly machine-checked** — `SHIPS` (1),
      `HOLDS` (2), `HANDLES` (1). A `HANDLES` file must carry no
      `debug write memory` literal of its own, and K5 shows the check bites:
      plant one back and the run is `BAD EXEMPTION`, rc 1; remove the
      validation and the identical plant scores `0 offenders`, rc 0.
      Self-test is now **four** frozen bodies, two per rule, each pair
      two-sided. Knives K1–K6 all cut, each with a GREEN control in the same
      session; **K1's prediction was wrong in its mechanism and is recorded as
      wrong** (§4bis.3). Corpus: `unit-test` **58/58** · `injector-check` 0
      offenders / 257 · `preflight-check` 0 unguarded · **`latch-check` 16/16**
      · **`diskbasic-acceptance` 34/34** · `deadcode` 0/0. `key_proc()` output
      **byte-identical** (730 B, sha `f936ab2a…`), so no probe's delivery
      alignment moved.

- [ ] ⚠️ **`injector-check` IS STILL A TEXT CLASSIFIER, and D-INJSINK narrowed
      that without closing it** ([`docs/spec-probe-injsink.md`](docs/spec-probe-injsink.md) §6).
      What passes, measured on the shipped gate rather than assumed:
      a **split literal** (`"debug write" + f" memory {G} 0"` → `CLEAN`), and any
      body that reaches the cursors by a spelling neither rule knows. Neither is
      a careless-author shape — the six real copies were all verbatim — so this
      is a stated limit, not a filed defect.
      🎯 What is NOT a hole, re-measured after the coverage note first claimed it
      was: a frozen body laundered through a local call
      (`return build([…, OLD_KEY])`) **is caught**, `HANDLES`, along with
      `import M as L`, `from M import N as K` and `from M import *`. Rule (b) is
      blunt on purpose — the offence is naming the body, not what happens to it
      afterwards.
      ⚠️ **An EXEMPT file is trusted by construction.** `HANDLES` is machine-
      checked (no write literal of its own); `SHIPS` and `HOLDS` are not, and
      cannot be — they exist to hold injector bodies. The mitigation is that
      there are three of them and each is a slice-sized decision
      [[exemption-as-a-checked-claim]].
      ⚠️ **Rule (b) resolves modules by BASENAME.** Collision-free across all 257
      files today, and measured so on every run; a future duplicate basename
      resolves to both, which is the eager direction.

- [ ] ⚠️ **THE DELIVERY GUARDS DO NOT COVER PROBES WITH THEIR OWN `build_tcl`.**
      Every `probes/disk/*` script and `basic_probe_printusing.py` build their own
      Tcl and never reach `omsx_repl._tcl`, so neither the stored-program oracle
      nor the echo oracle sees them. Not enumerated; not known to be affected.
      🔴 **D-LATCH promoted this from a COVERAGE item to a CORRECTNESS one.** A
      local copy of the pre-D-LATCH `__key` — write at `KEYBUF`, reset `GETPNT` —
      still has the race the shared injector no longer has, and still has no
      oracle that would notice.
      ✅ **The five trap probes are DONE** (`interval`, `key`, `sprite`, `strig`,
      `stop`): each held a byte-identical copy, each now calls
      `omsx_repl.key_proc()`, and all five gates were re-run green.
      ✅ **CLOSED 2026-08-04 BY D-LASTINJ**
      ([`docs/spec-probe-lastinj.md`](docs/spec-probe-lastinj.md),
      [`docs/lastinj-characterization.md`](docs/lastinj-characterization.md)).
      🔴 **AND "no Makefile target runs it" WAS FALSE.** `make diskbasic-acceptance`
      dispatches `disk_probe_getput.py` as registry row `GET/PUT`
      (`probes/disk/diskbasic_acceptance.py:81`), and a SECOND row (`OPEN(LEN=)`)
      imports its driver — so it was scored all along and sat inside D-LATCH's own
      corpus under the name `diskbasic`. The question asked was *"is there a target
      called `getput`?"*; the load-bearing question was *"is this file scored?"*
      ([[readout-blind-to-its-own-subject]] reached through a naming convention).
      Its `__inj` was **character-identical** (after constant folding) to
      `latch_check.OLD_KEY` — the body row A forces and requires to MANGLE.
      🎯 **Measured latent, not harmless:** 0 of 16 slots at the trigger, but slot
      11 landed at `$119B` INSIDE `chget`'s wait loop, and the swallow law's
      precondition held at **15/15** slots with a predecessor. Re-pointed at
      `key_proc()`; `2/2` before and after, `34/34` full gate.
      🔴 **`make injector-check` now GENERATES the list** instead of a reader
      maintaining it (`tools/check_probe_injectors.py`, spec §3.4): AST, not grep
      — a file offends when its STRING LITERALS emit `debug write memory` and it
      NAMES a type-ahead cursor. 256 files, 3 structural exemptions, fails CLOSED.
      It found the one copy that existed (exit 1) BEFORE it was allowed to report
      zero, and it scores its classifier against two frozen bodies on every run so
      that an empty walk cannot certify itself [[fixing-the-fault-silences-the-control]].
      `basic_probe_printusing.py` builds its own Tcl but injects nothing through
      KEYBUF, so it is not in this class — the new gate classifies it CLEAN
      independently.

- [x] ✅ **D-ECHO — A LINE THE MACHINE DID NOT ECHO WAS NOT DELIVERED — LANDED
      2026-08-03.** Spec [`docs/spec-probe-echo.md`](docs/spec-probe-echo.md),
      characterisation
      [`docs/echo-delivery-characterization.md`](docs/echo-delivery-characterization.md).
      **Apparatus only — `probes/lib/omsx_repl.py` and a new
      `tests/test_echo_oracle.py`; no `basic/`, `sub/`, `disk/` or `tape/` source
      touched, no ROM rebuilt.** Closes D-DELIVER §9.3: every injected line is now
      checked against what the machine ECHOED, so `direct` mode — 45 of the 53
      probe files — is guarded too, and `run_cases` re-runs a mangled case
      boot-per-case exactly as the stored oracle does.
      🎯 **Six standing corpus suites were mis-delivering a case on every run and
      were GREEN**: `logicops`, `float`, `math`, `str-domain`, `time` and
      `error-trap`, all `direct`-mode and all invisible to the stored oracle. They
      passed because `run_differential` self-heals a disagreement — the outcome
      was rescued, the cause unattributable, and a mangle leaving a plausible
      value both sides agree on was never protected at all.
      🔴 **The guard was WIRED IN AND SILENT on its first run**: `$__f` is a global
      and does not resolve inside a Tcl `proc`, so `__echo` errored and openMSX
      dropped the callback without a word — emission present, call site present,
      every slot recorded, nothing reported. The **cross-oracle `ORACLES DISAGREE`
      check** caught it, not any gate [[coverage-gate-cannot-see-a-gutted-guard]].
      🔴 **Four false-positive classes, all found by the CORPUS, not by
      inspection** — and two of them broke a green gate before they were found
      (`linemax` 60/60 → exit 2 on a payload whose `LIST` scrolls its own echo
      away; `missing` 59 fires on a payload that clears then prints). The fourth
      fired on the **reference**, which mis-delivers nothing, and was caught by
      the zero-RED control [[knife-that-reddens-nothing-is-the-finding]].
      🔴 **K6 reddened NOTHING and that was the finding**: a hard-coded screen
      margin degrades the guard to **blindness**, not to noise (`MANGLED` 1 → 0,
      zero false fires), because a margin wrong by one eats only the prompt and
      matters solely for a *wrapped* echo. The geometry therefore has no emulator
      knife; `tests/test_echo_oracle.py` is its only instrument, and exits 1 on
      four rows under that cut.
      ⚠️ **The stored-program oracle STAYS**, as a second opinion — each oracle is
      blind exactly where the other sees (spec §5), and the pair is the only
      positive control either has, since a batch of *identical* cases does not
      reproduce the race at all.

- [x] ✅ **D-DELIVER — A CASE WHOSE PROGRAM WAS NEVER STORED MAY NOT REPORT A
      VALUE — LANDED 2026-08-03.** Spec
      [`docs/spec-probe-delivery.md`](docs/spec-probe-delivery.md),
      characterisation
      [`docs/graphics-delivery-characterization.md`](docs/graphics-delivery-characterization.md).
      **Apparatus only — `probes/lib/omsx_repl.py` and nothing else; no `basic/`,
      `sub/`, `disk/` or `tape/` source touched, no ROM rebuilt.** Closes the two
      standing `graphics-acceptance` reds D-PREFLIGHT filed (§8.5) and the corpus
      question that came with them.
      **Neither row was about sprites or `BASE(n)`.** Boot-per-case, both machines
      answer identically (`ZE 5` / `ZE 5`, `ZK 6144` / `ZK 6144`). The batched
      delivery path was **losing a whole program line**: `put_pat64_16` lost
      `10 ON ERROR GOTO 40`, so its ERR 5 went UNTRAPPED and the RUN aborted with
      the machine still in SCREEN 2 — whose zeroed pattern table the SCREEN-0
      scrape reads as **960 bytes of `$00`**, i.e. `zb=None`; `rd_base_s0` lost its
      `PRINT"ZK"` line, fell through into the handler and printed the PREVIOUS
      case's `ERR`, which still held **5** from `rd_baseneg`.
      🎯 **D-PREFLIGHT's hunch that `'ZE 5'` was "the neighbouring row's answer" is
      LITERALLY TRUE — and its model was wrong.** Implementing against it would
      have aimed a fix at the readout and looked like it worked.
      **What landed:** `_tcl` emits `prog.<idx>=<line-number chain>` per stored
      case (a new `__lines` Tcl walk of the line-link chain from `TXTTAB`), read
      **before `RUN`** so a case's own `NEW` cannot erase the evidence;
      `run_cases(batch=True)` announces any mismatch on stderr and re-runs that
      case boot-per-case (the path measured immune); `run_batch` — which IS the
      boot-per-case path — has no fallback and raises `APPARATUS FAILURE` instead.
      `verify_delivery=False` is the opt-out; **no probe needs it** (measured: of
      the 8 files using `mode="stored"`, none drives line entry to refusal).
      🔴 **THE GUARD FOUND ROWS THE GATE COULD NOT.** The clean gate run announced
      **four** mis-deliveries, not two: `wr_v255fr` and the phase-M `SCREEN2:DRAW"B"`
      row had each lost their `ON ERROR GOTO 40` and **passed anyway**, being value
      rows that never raise [[gate-can-be-green-while-measuring-nothing]]. And on
      its first corpus run it fired in **`array-acceptance`** too (case 20,
      `DIM C(1,1,1,1)` lost) — this is not a graphics-probe curiosity.
      🔴 **COVERAGE IS NOT EFFICACY, AGAIN.** Knife K2 kept the `prog.N=` emission
      AND the call and only gutted the judgement: the filed reading returned
      **byte-identical** [[coverage-gate-cannot-see-a-gutted-guard]]. K1 (delete
      the emission) gave the same. K3 (detect, do not repair) turned it into an
      attributed refusal. K4 fired and repaired with all 30 verdicts unchanged. K5
      was a deliberate **zero-RED** knife on the reference and came back 0/0/0
      [[knife-that-reddens-nothing-is-the-finding]].
      🔴 **MY FIRST TWO INSTRUMENTED RUNS PROVED NOTHING** — they were clean, but I
      had not checked the fault reproduced in them. Re-run with a reproduction
      check in the same run before their result was used
      [[knife-runner-false-negatives]].
      ✅ **CORPUS DECISION: `graphics-acceptance` JOINS THE STANDING LIST** (§5, and
      [`docs/spec-basic-dotgaps.md`](docs/spec-basic-dotgaps.md) §9.2). 290 rows,
      **2 m 58 s**, on the `repack-machine` prerequisite every emulator gate
      already has. It is the only member ever red at admission; admission was
      conditional on it coming back 290/290, and it did.
      **Gates:** graphics **290/290** (was 2 FAIL; a row-by-row diff moves exactly
      those two rows and nothing else) · unit 56/56 · deadcode 0/0 ·
      preflight-check 0 unguarded · msgexact 55/55 · logicops 193/193 ·
      array 151/151 · linemax 60/60 · direct-ctrl 40/40 · diskbasic 34/34 ·
      bdos 12/12 · missing / width / string / error / error-trap / abort /
      stop-trap / arrdim / clearpool / float / input / input-devices / time /
      intarg / sound / play / beep / math ALL PASS.

- [x] ✅ **D-PREFLIGHT — A PROBE MAY NOT MEASURE A MACHINE IT CANNOT VOUCH FOR —
      LANDED 2026-08-03.** Spec
      [`docs/spec-probe-preflight.md`](docs/spec-probe-preflight.md).
      **Apparatus only — no `basic/`, `sub/`, `disk/` or `tape/` source touched,
      ROMs byte-identical throughout.** Closes the failure D-DOTGAPS §9.2
      recorded: a corpus script ran `rm -rf build && make basic-reloc` (which does
      NOT build `build/zerobas-main-eu.rom`) and then a probe by hand; openMSX
      booted against a machine XML whose absolute paths named a deleted file, and
      `msgexact --gate` reported **55 red rows including its own controls**. Second
      time this class has bitten ([[stale-machine-reads-as-unimplemented]],
      [[ips-rebuild-after-basic-change]]).
      **What landed:** [`probes/lib/omsx_preflight.py`](probes/lib/omsx_preflight.py)
      refuses (exit 2, `APPARATUS FAILURE`, names the file and the fix) before the
      first boot; 90 probe/tool files now spawn
      `omsx_preflight.guarded(argv)`;
      [`tools/check_probe_preflight.py`](tools/check_probe_preflight.py) is the
      coverage denominator (**178 spawn sites, 85 exempt by construction, 93
      required, 0 unguarded**, `make preflight-check`); `msgexact-gate` /
      `msgexact-relock` targets exist at last, both on `repack-machine`.
      **The freshness oracle is `make -q`**, not an mtime sweep: `build/disk.rom`
      depends on `disk/` only and `build/sub.rom` on `sub/` only, so the obvious
      "no ROM older than the newest file under basic/ sub/ disk/ tape/" rule would
      have **refused every ordinary BASIC slice**.
      **Reference machines are exempt STRUCTURALLY, not by name**: only ABSOLUTE
      `<filename>` paths outside every openMSX dir are checked, and
      `Philips_VG_8020` / `National_CF-3300` carry none (measured: 0 files
      checked). A name list would have been one edit from exempting the subject
      [[echo-guard-never-saw-say-rows]].
      🔴 **THE GUARD WAS WIRED IN AND FAILED OPEN, AND ITS OWN KNIFE MATRIX FOUND
      IT.** `except OSError` around the `make -q` call was too narrow: a test
      double's exception escaped `preflight` **after** a `MISSING` fault had been
      recorded and **before** it could be reported, and all 8 entry points read
      GREEN with the ROM deleted. Now `except BaseException` → "cannot judge" is a
      **fault**. A guard that cannot judge must say so (§8.1).
      🔴 **THE mtime-RACE CHECK CANNOT EXIST, AND K3 IS WHAT SAID SO.** GNU Make
      3.81 compares at **ONE-SECOND** granularity (measured: target 1 ns OLDER than
      its prerequisite → still "up to date"), so the hazard is any same-second
      pair, not the equal mtime [[make-mtime-race-skips-subrom]] records — and a
      same-second check **fires on a correct, just-built tree**, because
      `sub/basic-resident-abi.inc` is GENERATED by the build ([`Makefile:261`](Makefile:261))
      68 ms before `build/sub.rom`. Removed rather than shipped as a check that can
      only fire falsely; the race stays a knife-runner hashing problem (§8.2).
      🔴 **COVERAGE IS NOT EFFICACY.** Knife K6 gutted `guard_cmd` and
      `preflight-check` still reported **93/93 guarded, ALL PASS** while the
      incident returned verbatim. The coverage gate proves the call is *there*;
      only K1/K6 prove it *does* anything.
      🔴 **EVERY MACHINE CONFIG THIS TREE HAS EVER WRITTEN WAS INVALID XML** — one
      `--` inside an XML comment in `tools/install-repack-machine.py`, in all five
      installed `ZB_*`/`*_REPACK_*` machines. openMSX tolerates it; ElementTree
      refuses the whole file. Fixed; the preflight strips comments textually
      anyway (§5.2).
      ⚠️ **A live specimen was already installed**: `ZB_REPACK_BASE.xml` still
      points at `.claude/worktrees/brave-curie-382b17/build/*.rom`, deleted long
      ago — the 2026-07-26 traps-T5 incident, still bootable. Refused by name now.
      🔴 **FILED, NOT FIXED: `graphics-acceptance` has two standing red rows**
      (`put_pat64_16`, `rd_base_s0`) and is **in no spec's corpus list** — the
      exact shape `logicops-acceptance` was in before D-EXPKW. Attributed away
      from this slice twice: identical under `ZEROBAS_PREFLIGHT=off` **and**
      identical on the stashed pre-slice tree.
      ⚠️ **A HEURISTIC FOR "WILL THIS IMPORT RESOLVE?" IS NOT A SUBSTITUTE FOR
      RUNNING IT** — the codemod guessed from a substring, `omsx_session.py` got an
      unreachable import, and `diskbasic-acceptance` came back **30/34** for the
      import rather than the disk. `compileall` was clean and the coverage gate was
      green; only the gate found it. 34/34 after (§8.3).
      **Gates:** unit 56/56 · deadcode 0/0 · msgexact 55/55 · preflight-check
      0 unguarded · lnblank 536/536 `REPEAT=2` · lnblank-echo green · logicops
      193/193 · array 151/151 · diskbasic 34/34 · bdos 12/12 · linemax 60/60 ·
      direct-ctrl 40/40 · string/error/error-trap/abort/stop-trap/arrdim/clearpool/
      float/sound/play/beep/math/input/time/intarg ALL PASS.

- [x] ✅ **ERROR-MESSAGE CAPITALISATION — CLOSED 2026-08-02 by D-MSGEXACT**
      ([`docs/spec-basic-msgexact.md`](docs/spec-basic-msgexact.md), denominator
      [`docs/msgexact-msx1-characterization.md`](docs/msgexact-msx1-characterization.md)).
      Resolved as **reference-exact wording, tree-wide**. Page 1 **14 B → 39 B**:
      the policy was a **carve**, not a cost — the lowercase style was the only
      thing paying for two duplicated strings and `fp_runtime_error`'s two
      one-code-two-message special cases. Gate 45/45, five knives, corpus green.
      🔴 **THIS ITEM'S OWN EVIDENCE WAS WRONG IN BOTH HALVES, AND THAT IS THE
      LESSON.** (a) [`basic/arrays.asm:608`](basic/arrays.asm:608)'s claim is
      scoped to **syntax** errors and is TRUE; the same comment names Tier B as
      capitalised. The tree's inconsistency was deliberate documented policy
      (arrays §9.5), not a defect — which is why no gate ever caught it.
      (b) The two `array-acceptance` failures were **not** a message-case defect:
      D-MISS-2 folded INSTR's check into `eval_pos_arg`, whose reject path is
      `gb_illegal` → `raise_error(5)` → the capitalised string, deleting the
      lowercase route the probe still asserted. **149/151 → 151/151 with no
      `basic/` change.** A red row assumed stale is a row that measures nothing.
      🎯 The real finding was structural: [`error_acceptance.py`](probes/basic/error_acceptance.py)
      stated a policy of *not* comparing message text to the reference, so the
      **whole corpus was blind to wording** — every error class agreed
      numerically. `lst-comma` was the single visible pixel of that; it is
      retired.

- [x] ✅ **D-MSGSUB — THE 14 UNIMPLEMENTED ERROR MESSAGES, SUB-ROM-HOSTED —
      CLOSED 2026-08-02** ([`docs/spec-basic-msgsub.md`](docs/spec-basic-msgsub.md),
      denominator [`docs/msgexact-msx1-characterization.md`](docs/msgexact-msx1-characterization.md)).
      Codes 12/15/18/19/50/51/53/54/56/57/60/62/63/64 now print the reference's
      own text from sub-ROM page-1 tenant `SUBROM_IDX_ERRMSG` (`sub/errmsg.asm`),
      emitted through BIOS `CHPUT`. **`msgexact --gate` 33/49 → 50/50, zero
      holes left.** Main page 1 **39 B → 22 B**, low region **unchanged**, sub
      page 1 3067 → 2740 B.
      🎯 **THE WHOLE MAIN-SIDE COST OF THE TEXT IS ONE BYTE.** `err_subhosted` is
      a single `MSGESC_SUB` marker; the four dense `err_msgtab` holes and
      `rerr_unprintable` just point at it — five repoints, **zero bytes**. The
      +17 B is entirely the decoder arm and the dispatch stub. That is the
      mechanism the follow-on below rides.
      🎯 **THE SLICE DOES NOT REST ON "THE ABSENT CASE IS UNREACHABLE", AND IT
      SHOULD NOT HAVE.** D-MSGEXACT §4.2 argued you cannot type `ERROR 12`
      without a sub-ROM because `tokenise` is itself a tenant. **That argument
      has a hole** — a *tokenised* program can arrive from tape or disk. So
      `err_subhosted` is sited so `err_unprintable` is the very next byte, and an
      absent sub-ROM falls through to exactly what zerobas printed before.
      Knife K1 MEASURED it with a plain `POKE &HF107,0`, no rebuild.
      🔴 **TWO OF THE FIVE KNIVES LANDED ON THE SLICE ITSELF.**
      **K2** reddened nothing — and the reason was that `sub/errmsg.asm` was
      missing from the Makefile's `SUB_PARTS`, so `make` never rebuilt the
      sub-ROM. Nothing shipped wrong (clean builds force it), but the next
      incremental edit to the tenant would have silently shipped a **stale
      sub.rom** ([[makefile-subparts-stale-tenant]], met again by adding a new
      sub file). Caught only because a knife predicted RED and got green.
      **K3 refuted this spec's own headline measurement**: the `prd-*` rows were
      written into the spec AND the denominator as "the reading that settles
      CHPUT", and deleting `fre_abort_low`'s `ld (PRDEST),a` moved **neither**.
      `PRINT#` restores PRDEST at statement end, so an `ERROR n` on the next line
      never sees it set. Re-aimed at `mid-ifc` (the error raised *inside* the
      `PRINT#` argument list) the cut lands both ways — without the zero the
      screen is **empty** and the message is in the file. For the sub-hosted path
      the question is **bounded away, not measured**: `ERROR n` is a statement and
      cannot appear inside a `PRINT#`.
      ⚠️ **K5 corrected the spec too**: code 26 stays green when the sparse
      routing is reverted, because main's `Unprintable error` and the tenant's
      fallback are the same text. 26 is a control for the mechanism being
      *sound*, not *present*.
      ⚠️ **This fixes the TEXT, not the RAISERS.** No zerobas site raises any of
      the fourteen (verified by enumerating every `ld a,<n>` into `raise_error`);
      `ERROR n` is still the only way to reach them. "Should zerobas raise ERR 12
      for a direct-mode `INPUT`?" is a different question per code.

- [x] 🎯 **D-MSGMIGRATE ✅ — SIXTEEN MESSAGES MIGRATED; PAGE 1 22 B -> 311 B.**
      Done 2026-08-02, [`docs/spec-basic-msgmigrate.md`](docs/spec-basic-msgmigrate.md).
      🎯 **THE FILED CLAIM WAS REFUTED IN THE CHEAP DIRECTION.** D-MSGSUB §8 said
      five messages could not migrate because `rerr_sparse` reaches them "by its
      own `ld hl` -- a different key", and proposed a 2 B/message second selector.
      It is the SAME key: `rerr_sparse` OPENS with `ld a,(ERRFLG)`, and
      `raise_error_forced` / `ex_cont_no` / `dl_overflow` each store ERRFLG before
      loading their message. **No second selector was built.** Enumerating every
      print site is what said so, and it disagreed with the filed list in BOTH
      directions (five wrongly blocked, one wrongly cleared).
      🎯 **AND THE SELECTOR CODE ITSELF WAS DELETABLE**: once all five sparse
      messages pointed at `err_subhosted`, every arm of `rerr_sparse` and
      `rerr_sparse2` read `ld hl,err_subhosted / jp raise_error_hl` -- which is
      what `rerr_unprintable` already was. 50 B of dispatch gone, trap decision
      unchanged (`sparse-trap`, a row added mid-slice, is what measures that).
      Carve: 225 B of string + 50 B dispatch + 15 B of dead phrase table
      (`MSGESC_WITHOUT` had THREE users, not the two that were filed) + 7 B of
      collapsed branch, less 8 B for `pm_sub`'s register fence = **289 B**.
      Sub page 1 2740 -> 2428 B. `msgexact --gate` **54/54**, unit **56/56**,
      dead-code 0/0.
      🔴 **A DEFECT WAS FIXED TO GET THE LAST STRING, AND FIXING IT CARVED BYTES.**
      `dl_overflow`'s float arm stored no ERRFLG at all, so `PRINT ERR` after
      `20 A=1E99` read a stale code while its sibling arm read 25. Measured
      2026-08-02 on both refs (`fovf-lit` 6/6, zerobas 0; controls `fovf-ctl` 0
      everywhere and `fovf-arm` 6 everywhere). `TKOVF`'s own contract in
      `basic/tokenise.inc` already says "the reject reason IS the ERR code" --
      the float arm was the one arm not honouring it. Storing 6 made both arms
      symmetric, DELETED the branch, and only then was `err_overflow` migratable.
      🔴 **TWO FINDINGS IN APPARATUS, NEITHER IN THE MIGRATION.** (a) The host
      harness's page-1 sub-ROM island borrowed the caller's MEMORY but not its
      TRAPS, so a tenant's `call CHPUT` ran off the end -- invisible until
      `errmsg_tenant` became the first page-1 tenant a unit test reaches whose
      whole job is a BIOS call. (b) K1's own setup disabled its delivery path
      (`POKE &HF107,0` then typing `ERROR n` cannot tokenise), and the
      main-resident CONTROL is what said so.

- [ ] 🔴 **`err_verify` AND `brk_msg` ARE THE LAST TWO MAIN-RESIDENT MESSAGES,
      AND THEY ARE BLOCKED FOR TWO DIFFERENT REASONS.** Filed 2026-08-02 by
      D-MSGMIGRATE §6.2/§6.3, which measured both and declined both.
      * `err_verify` (8 B): `verify_error` ([`basic/cload.asm:492`](basic/cload.asm:492))
        is `ld hl,err_verify / jp print_msg` with **no `ld (ERRFLG),a`**. Adding
        one costs 5 B to save 8 -- a net 3 B not worth taking blind, because it
        also makes `PRINT ERR` read 20 after a `CLOAD?` mismatch, which is an
        **observable change with no oracle reading behind it**. ⚠️ Exactly the
        shape D-MSGMIGRATE's own §6.4 turned out to be, and there the reading
        (both refs read 6) is what made the fix correct AND free -- so TAKE THE
        READING FIRST. The CAS: harness is the cost; `Verify error` is still
        `<not-measured>` in the msgexact denominator for the same reason.
      * `brk_msg` (6 B): printed by `call print_string`, and **`print_string` has
        no escape decoder at all** -- a `MSGESC_SUB` byte there is `pchar`'d as a
        literal $06. And `Break` is not an error, so ERRFLG is stale. Two
        independent blockers; this one needs a PRINTER change, not a key.

- [ ] ⚠️ **AN INDIRECT REACHER CANNOT BE ENUMERATED BY NAMING THE CALLEE.**
      Filed 2026-08-02 by D-MSGMIGRATE §9, whose blast-radius sweep grepped for
      `jp|call|jr .*print_msg` and therefore missed a FOURTH reacher:
      `dispatch_line`'s line-number-out-of-range arm arrives by
      `jr dl_ovf_report`, a shared tail, and never names `print_msg`.
      The BUILD caught it (the label vanished with a collapsed branch), not the
      sweep. It passes a resident string so it reaches nothing sub-hosted today --
      but it would have, silently, had that string ever migrated.
      Worth a tool: resolve fall-through and shared-tail edges when enumerating
      "who can reach routine X", the same way `check_tenant_closure.py` walks a
      call graph rather than grepping for names.

- [ ] ⚠️ **A PROBE'S MESSAGE LITERAL IS EITHER AN ASSERTION OR A CLASSIFIER
      NEEDLE, AND THEY LOOK IDENTICAL.** Filed 2026-08-02 by D-MSGEXACT §6b,
      which silently broke **30 comparisons across 9 files** and every one failed
      by **agreeing**: a needle matched against an already-`.lower()`-ed screen
      string cannot match if it is capitalised, so the row reclassifies from
      `error:<phrase>` to `value` instead of going red.
      ⚠️ `badfnum` was invisible to two rounds of auditing — it has no `.lower()`
      at all; it `setdefault`s its needle into an `ERR_CLASSES` dict **imported
      from `lof`**. The gate caught it (12 oracle drifts), not the audit.
      Worth a lint: a capitalised message literal reaching a case-folded
      comparison, across module boundaries. Until then the vocabularies carry
      explicit "MUST STAY LOWERCASE" comments
      ([`basic_probe_kwsweep.py`](probes/basic/basic_probe_kwsweep.py) has the
      worked one).

- [x] ✅ **`.` — THE CURRENT-LINE PSEUDO-LINE-NUMBER — LANDED 2026-08-02
      (D-DOTLINE). Four pins RETIRED, none added; `lnblank-say-acceptance`
      108 -> 181 rows with 6 -> 2 pins; `lnblank-acceptance` 530 -> 536,
      allowlist still EMPTY. 16 corpus targets green, six knives scored.** Spec
      [`docs/spec-basic-dotline.md`](docs/spec-basic-dotline.md), measurement
      [`docs/dotline-msx1-characterization.md`](docs/dotline-msx1-characterization.md).
      Filed by D-DELETE, confirmed on a second verb by D-LSTRNG, both of which
      measured `.` and DECLINED it rather than ship a rule one verb wide.
      🔴 **THEY WERE RIGHT, AND FOR A BIGGER REASON THAN EITHER GAVE.** The four
      filed rows measured ONE writer — storing a line — and ONE argument
      position. The 77-row walk found **four writers and eleven measured
      NON-writers**, and three of the four would have been implemented WRONGLY
      from a `DELETE`- or `LIST`-shaped reading:
      * **`LIST` writes it**, to the LAST LINE IT PRINTED — not the argument,
        not either end — and a `LIST` that prints nothing writes nothing
        (`cln-listrng` 30, `cln-listbare` 40, `cln-listmiss` unchanged; the
        filed `LIST 40` row could not separate four candidate rules);
      * 🔴 **an ASCII `SAVE` WRITES IT TOO (40) and a tokenised one does not
        (20)**, because both drive the same walk.
        ⚠️ **THIS IS THE EXACT MIRROR OF THE HAZARD D-LSTRNG §3.3 HAD TO FIX IN
        THAT VERY ROUTINE** — a `LIST` range leaking into `SAVE",A"` was a
        data-loss bug — so reasoning by analogy says keep `DOT` OUT of the
        shared `list_walk` for ~16 B. The measurement says put it IN for 4 B.
        Same routine, two shared-code questions, **opposite answers**;
      * 🔴 **a DIRECT-MODE error writes NOTHING** — it does not take `ERRLIN`'s
        measured 65535 sentinel, so the two cells are written by the same event
        under different rules and the obvious shared tail (4 B cheaper) is
        wrong;
      * 🔴 **the `DELETE` VERB does not write it** even though the
        bare-line-number delete does. Two ways to remove a line, same visible
        effect on the program, different effect on `.`;
      * 🔴 **`RESUME` IS NOT A WRITER — AND THIS SLICE SHIPPED ONE BEFORE ITS
        OWN KNIFE FOUND IT.** `cln-trap` alone reads the HANDLER's line and
        would have been written up as "a trapped error records where control
        went"; `clp-trapend` (`50 END`) reads the ERRORING line, and
        `clp-onerr`/`-goto`/`-gosub` kill the rival "a line LOOKUP is the
        writer" reading. What replaced them — "a RESUME records the line it is
        IN" — was **implemented, ~12 B of page 1, and wrong**. Knife K5 cut it
        and moved **ZERO of 139 rows**: every supporting row had TWO SUFFICIENT
        CAUSES, because `RESUME NEXT` resumes into line 30 which then FALLS
        INTO line 50 again, raising ERR 22 *in line 50*. `clp-resend`
        (`30 A=A+4:END`, so line 50 is never re-entered) reads **20** on both
        references against the shipped build's 50. Withdrawn, **14 B
        recovered**; the slice costs 10 B of page 1, not 24
        [[knife-that-reddens-nothing-is-the-finding]];
      * **`NEW` does NOT reset it**, which `LIST .` is structurally blind to.
      🎯 **THE PUBLISHED WORK AREA NAMES THE VARIABLE — `DOT $F6B5`, "line
      number of last used (changed, listed, added) line"** (C-BIOS
      `systemvars.asm`, the same allowed source the sysvar denominator is
      generated from). Claimed at the published address under the published
      name for **zero ROM bytes**, D-REHOME's sixth honoured cell and the first
      that was never re-homed — it did not exist before. PUB-FREE measured
      first: zerobas' byte there read 0 in all 24 swept states.
      🎯 **AND THAT CELL IS WHY THE COLD MACHINE AND `NEW` ARE MEASURED AT ALL.**
      `LIST .` cannot ask either — on a cold machine, and after a `NEW`, the
      program is EMPTY, so nothing is listed whatever the cell holds and every
      reading compares EQUAL on every side. Every one of the 24 `clp` PEEK rows
      has a behavioural twin and **every twin agrees**, which is what makes the
      PEEK evidence about `.` and not about a byte.
      ⚠️ **AN APPARATUS FAULT OF THE FAIL-BY-AGREEING KIND, CAUGHT ONLY BY AN
      ASYMMETRY.** The first cell readout was 38 characters — inside the 40-byte
      KEYBUF cap, which is why it looked safe — but the screen's two-column
      margin pushed its closing quote onto the next row, so `_echo_idx` found no
      row carrying the command and the reader returned `<none>`, a sentinel that
      also means "no reading". It did that on vg8020 and zb but NOT cf3300,
      whose Disk BASIC lays the prompt out differently; had cf3300 wrapped too,
      all three sides would have reported THREE-WAY AGREEMENT on nothing. The
      value was on screen the whole time. **The binding constraint is COLS minus
      the margin, not the KEYBUF cap.**
      Landed **+10 B main page 1** (311 -> 301 free) and **+17 B sub page 1**;
      one resolver in `ldr_num`, the single site both `le_delrange` and
      `le_lstrange` read a line number from, so `AUTO`/`RENUM` get `.` free the
      day they are dispatched.
      ⚠️ **STILL UNMEASURED, and recorded as choices rather than readings**:
      whether an ASCII LOAD/MERGE writes `.` per line (zerobas' `cload.asm`
      reaches `store_line`, so it inherits writer (a) either way); whether an
      OOM store writes it; and the ASCII-SAVE reading is **cf3300 only** —
      `SAVE"CAS:",A` would give a second reference and needs cassette support
      this probe does not have.

- [x] ✅ **`RETURN <line>` — LANDED 2026-08-02 (D-RETLN), 27/27, four knives,
      `lnrd-return`'s pin RETIRED.** Filed 2026-08-01 by D-LNREF; spec
      [`docs/spec-basic-retln.md`](docs/spec-basic-retln.md), measurement
      [`docs/retln-msx1-characterization.md`](docs/retln-msx1-characterization.md).
      The filed one-line description was right and **incomplete in four ways**,
      and the 27-row `lnrt` walk is what found them — both references agreeing on
      every row:
      * **the empty-stack check comes FIRST**, before the argument is parsed *or*
        resolved: `RETURN B` and `RETURN 99` on an empty stack are both ERR 3,
        not ERR 2 / ERR 8 (`lnrt-nogosbad`/`-nogosund`). The filed row could not
        have said so — its line existed and its argument was well formed;
      * **both failure modes POP THE FRAME BEFORE THEY RAISE.** ERR 8 *and* ERR 2
        leave the stack empty (`lnrt-undefp`/`lnrt-varp`, which read the STACK by
        making a handler's own bare `RETURN` report on what was left);
      * **the error is filed against the `RETURN`'s own line**, not the caller's
        (`lnrt-erlund`/`-erlvar`, ERL = 40). 🔴 This is what rules out the
        cheapest implementation — reusing the existing pop, whose
        `ld (CURLINE),de` would file it against the caller. No row reading only
        "where did control go" could see it;
      * **trailing junk is ERR 2** — `RETURN B` is a syntax error, `RETURN 0` is
        an ordinary failing lookup (ERR 8, no zero special case), and `:` after a
        bare `RETURN` is a terminator (`lnrt-bcolon`).
      ⚠️ **The filed warning "it must POP the frame *and* set the resume line —
      not a GOTO with extra steps" was WRONG.** It is exactly a GOTO with a pop
      in front: `RESUMEFLAG` is never set on the branch path, and setting it
      would be the bug (the run loop consults it *before* `GOTOFLAG`).
      🔴 **And MS-BASIC's documented use for `RETURN <line>` — leaving an
      `ON ERROR` handler — DOES NOT EXIST ON MSX.** Both references read ERR 3: a
      handler is entered without a GOSUB frame, so the empty-stack rule just
      fires (`lnrt-onerr`, with `lnrt-onerrctl`'s `RESUME 70` → ` 120  0 ` as the
      control proving the instrument can read the success case).
      Landed **+25 B main page 1**, funded by a measured 160 B carve (below).
      🔴 **A REGRESSION SHIPPED IN THE FIRST IMPLEMENTATION AND THE 28-ROW BATTERY
      COULD NOT SEE IT.** `trap_return_check` destroys `HL` unconditionally, which
      was free while `ex_return`'s next act was `ld hl,(GSP)` (HL dead across the
      call); making the token cursor live across it inherits that clobber contract
      silently ([[refactor-inherits-clobber-contracts]]). Caught by
      `stop-trap-acceptance` (`C2_press_in_handler_latches`), not by any `lnrt`
      row — all 28 `RETURN` out of ordinary code, so `TRAPSVC` is 0 in every one
      and the clobber cannot fire. Fixed by moving the `push hl` above the trap
      check, at **zero byte cost**.

- [ ] **`RETURN` DOES NOT DISCARD AN OPEN `FOR`, AND ON THE REFERENCE IT DOES.**
      Filed 2026-08-02 by D-RETLN, found by the apparatus while it was testing
      something else. MS-BASIC keeps FOR and GOSUB frames on the **same** (Z80)
      stack, so `RETURN` discards the FOR entries it walks past looking for a
      GOSUB frame — with no GOSUB frame at all, that means the open `FOR`.
      zerobas keeps the two on **separate RAM stacks** (`GOSUB_STK` and the FOR
      stack), so nothing is walked past and the loop survives:
      ```
      10 ON ERROR GOTO 50 : 20 FOR I=1 TO 3:RETURN:NEXT
      30 A=A+100:END      : 50 A=A+1:RESUME NEXT
          both references -> A=102 ERR 0 I=1     zerobas -> A=103 ERR 0 I=4
      ```
      🔴 **My first attribution was "an error trap destroys the FOR frame", and
      its own control REFUTED it.** `lnrt-forerr` is the identical program with
      `ERROR 7` in place of `RETURN` and reads ` 103  0  4 ` on **all three
      sides** — an ordinary trap is not the variable, `RETURN` is. One row could
      not have separated those two rules ([[one-row-cannot-separate-two-rules]]).
      `lnrt-forret` is **pinned as `KNOWN_DIVERGE`** to zerobas' exact
      ` 103  0  4 `, with `lnrt-forerr` alongside it as the green control.
      This is architectural, not a parse bug: closing it means making `RETURN`
      (and the error unwind) aware of the FOR stack, which is its own slice.

- [ ] **135 MORE DEAD BYTES OF THE SAME SHAPE, IN 20 FILES.** Filed 2026-08-02
      by D-RETLN, which carved all 160 as its funding — this entry records the
      *shape*, because the gate that should have found it cannot.
      `skip_spaces` ([`basic/interp.asm:574`](basic/interp.asm:574)) is
      `ld a,(hl) / cp ' ' / ret nz / inc hl / jr skip_spaces` — it returns **only**
      via `ret nz`, so `A = (hl)` on every exit. Every `call skip_spaces`
      immediately followed by `ld a,(hl)` therefore reloads a register that
      already holds that value: 1 dead byte, 160 times, `basic/graphics.asm` 27 ·
      `basic/files.asm` 26 · `basic/program.asm` 19 · `basic/save.asm` 15 · …
      Measured, clean `make basic-reloc`: page 1 free **6 B → 149 B**, low
      **9 B → 23 B**.
      🔴 **THE DEAD-CODE GATE REPORTS 0 DEAD AND IS RIGHT.** These are reachable
      instructions computing a value already held — not unreachable code — so
      `deadcode-gate` is structurally blind to them, and was while 160 B sat
      there through every slice that ever said "page 1 has 6 B free". ⚠️ **Every
      byte-budget claim made before 2026-08-02 was measured against a wall that
      had 143 B of slack in it.** The open question this leaves is not the 160 B
      (they are gone) but whether a gate should exist for the *shape*: a
      redundant-load sweep is a two-line matcher, and there are certainly other
      idioms like it. That is the item.

- [ ] **`DEFINT` STORES DIFFERENT BYTES FROM THE REFERENCE.** Filed 2026-08-01
      by D-LNREF's walk. `20 DEFINT 10` reads `<AC> <0F><0A>` on both references
      and `<97>INT <0F><0A>` on zerobas — [`basic/kwtable.inc:140`](basic/kwtable.inc:140)
      emits `DEF_TOKEN` + literal `"INT"` **on purpose** so `ex_def_type` sees
      the ASCII mnemonic, and `DEFSNG`/`DEFDBL`/`DEFSTR` have no entry at all.
      Deliberate, and still a byte-level divergence a `LIST` round-trip can see.
      Reference bytes now locked: `DEFSTR $AB`, `DEFINT $AC`, `DEFSNG $AD`,
      `DEFDBL $AE`. Closing it means moving `ex_def_type` off the ASCII
      mnemonic, so it is a slice and not a table edit.

- [ ] **`LIST <line>` / `LIST <from>-<to>` STILL LIST THE WHOLE PROGRAM.**
      `ex_list` ignores its argument (a documented Phase-2 divergence). D-LNREF
      made the ARGUMENT's bytes the reference's (`<93> <0E><0A><00><F2><0E><14><00>`
      for `LIST 10-20`), so the range is now sitting there crunched and unread.
      `lnrd-list` pins that this did not make it worse (`1 0` on all three sides).

- [x] ✅ **LINE-NUMBER SCAN AND EMBEDDED BLANKS — LANDED 2026-07-31, 52/52,
      falsified on five knives.** Was 🔴 a silently wrapped line number shipping
      today. Found 2026-07-29 as a
      FAILING TWO-SIDED CONTROL in D-LINEMAX's `tok` battery — a confound there,
      a real divergence of its own. Byte-exact via the
      `("stored_line", TXTTAB)` capture:
      ```
      typed:      20 0#0#0#0#0#
      VG-8020 ->  line 200, body = 0x23 ('#') + four double literals
      zerobas ->  line 20,  body = five double literals
      ```
      The reference's line-number scan **skips the blank and keeps accumulating
      digits** (`20` + ` ` + `0` = 200); zerobas stopped at the space.
      Spec [`docs/spec-basic-lnblank.md`](docs/spec-basic-lnblank.md),
      characterization [`docs/lnblank-msx1-characterization.md`](docs/lnblank-msx1-characterization.md),
      gate `make lnblank-acceptance` (54 rows, five batteries). **Baseline 18/48.**
      **Cost: 61 B, all page 1 (69 B → 8 B free)**, low region untouched at 23 B;
      the crunch half rides the sub-ROM.
      ⚠️ **TWO ORACLES.** Every row was asked of the VG-8020 **and** the CF-3300,
      because the whole item rested on one row from one machine. They agree on
      all 54 rows byte for byte — so this is MSX-BASIC and not one ROM.
      🔴 **THE FILED TITLE WAS THE SMALLEST PART, in four directions:**
      * **`99999 REM` SILENTLY STORED LINE 34463.** The ceiling was unguarded and
        `parse_lineno` wrapped at 16 bits; both references refuse anything past
        65529 with `Syntax error` (`PRINT ERR` then reads 2; 65529 is accepted
        and leaves ERR at 0). Live *before* this slice and independent of blanks —
        but the blank fix widens its reach, so it landed here.
        ⚠️ **And the first cut of the fix did not catch it**: a ceiling tested on
        the *finished* value cannot see an accumulator that already wrapped, so
        `99999` passed a bound it was 34463 lower than. The overflow is now caught
        **where it happens** (any carry out of the `*10+digit` chain saturates to
        `$FFFF`), and knives C/D show the two halves are independent.
      * **THE BODY OFFSET HAS A RULE, and it is not the digit count.** The line
        number eats its digits plus exactly **one** blank — **none when its VALUE
        is zero**. `00 REMX` eats none and `01 REMX` eats one (same digit count,
        same leading digit); `0 0 REMX` reaches zero *through* a blank and still
        eats none. `skip_spaces` had been eating the whole run.
      * **A BLANK BEFORE AN `ON…GOTO` COMMA ENDED THE LIST**, so every later
        target crunched as a plain literal — the same failure `bl_num`'s own
        comment records for an *empty* slot, one character to the left of where
        that one was fixed. The blank rule does not explain it; `ref-oncomma`
        found it, and the fix is **two bytes cheaper** than the test it replaces.
      * **IT IS NOT THE LINE-NUMBER SCAN AT ALL** — it is the decimal *number*
        scanner (`A=1 0` → literal 10). Split out above, with the bounding
        controls (hex / string / REM / variable name) already measured.
      Sites fixed: `parse_lineno` + `dl_store`
      ([`basic/program.asm:200`](basic/program.asm:200)) and `bl_acc` + `bl_done`
      ([`basic/tokenise.inc:444`](basic/tokenise.inc:444)) — two copies of the
      same lookahead **on purpose**: they live in different ROMs (the crunch body
      is evicted to the sub-ROM), so no call could be shared. `mrg_storeline`
      ([`basic/files.asm:1593`](basic/files.asm:1593)) reaches the storage path
      through `dispatch_line` and is covered by construction.
      ⚠️ **A blank is only transparent when the run ENDS IN A DIGIT.** A greedy
      skip gives the right line number and the wrong body, which is why the scan
      looks ahead across the run before committing to it.
      ⚠️ **`num-zero` was labelled a two-sided CONTROL and it was RED.** The label
      was right about the blank rule and wrong as a claim about the row: it also
      exercises the body offset, which no rule in the spec covered when the label
      was assigned. **A control is a claim about which variables a row holds
      still**, and this one held fewer than its label said.
      ⚠️ **Apparatus: the standard echo guard would have been blind here.** The
      other probes squeeze runs of blanks so a wrapped echo still matches — and
      the blank *is* the subject, so squeezed, `2 0 REMX` and `20 REMX` are the
      same string and a dropped space reads as a clean echo. Not squeezing then
      reported `MANGLED` on **every row of both references** while the memory pass
      read them perfectly: the squeeze had been *hiding* a two-column screen
      margin, not tolerating it. `lstrip()` is no fix either (`num-lead` types a
      leading blank on purpose). The margin is now **measured per capture**.
      ⚠️ **And the `err` battery's control agreed for the wrong reason** — batched,
      it read back the `ERR 2` the previous row had just raised, because `reset`
      clears the program and not `ERRCODE`. Isolated it reads 0. That is
      [`probes/basic/basic_probe_linemax.py:276`](probes/basic/basic_probe_linemax.py:276)'s
      recorded trap, reappearing in a new probe within the hour — **and isolating
      the rows then broke them a second way**, because boot-per-case *ignores*
      `reset`, where the CF-3300's date-prompt CR lives.

- [x] ✅ **`WIDTH n`'s VALID DOMAIN — LANDED 2026-07-28, 76/76, falsified.**
      Was 🔴 FIVE silent screen-destroyers shipping today. The last residue of
      the abort-depth slice: [`docs/spec-basic-abort-depth.md`](docs/spec-basic-abort-depth.md)
      §7 deferred it in as many words — `4d35b6d` fixed how `WIDTH 300` *fails*
      and left open which `n` `WIDTH` should *accept*.
      Spec [`docs/spec-basic-width-domain.md`](docs/spec-basic-width-domain.md),
      characterization [`docs/width-vg8020-characterization.md`](docs/width-vg8020-characterization.md),
      gate `make width-acceptance` (76 rows, eight batteries). Baseline 36/62.
      **`ex_width` had no bound at all** — it ran the argument through
      `get_byte_arg` (domain 0..255) and then wrote `LINLEN` + a per-mode
      default + `CHGMOD` unconditionally. Measured on the VG-8020:
      **`SCREEN 1` accepts 1..32 and records `LINL32`; every other mode,
      GRAPHICS INCLUDED, accepts 1..40 and records `LINL40`** — so the old
      "any non-zero `SCRMOD` → `LINL32`" was wrong for `SCREEN 2`/`3`, visibly
      (`SCREEN 2:WIDTH 29:SCREEN 0` leaves the reference at 29 and zerobas at
      40). A reject writes NOTHING. Coercion truncates toward zero BEFORE the
      bound (`40.9` ok, `41.9` not), and **the domain check beats the deferred
      syntax error** (`WIDTH 41,` → ERR 5, not ERR 2) — the same ordering
      `MID$(A$,0,)` settled in D-MISS-2.
      🔴 **Two surfaces nobody had listed**, found by batteries written to cover
      the argument surface rather than to confirm the known defect — the fifth
      consecutive slice whose calibration turned up live defects in untested
      code: **`WIDTH "40"`/`WIDTH A$` must be `Type mismatch` (ERR 13)** and
      **bare `WIDTH` / `WIDTH :` / `X=1:WIDTH` must be `Missing operand`
      (ERR 24)** — zerobas silently took both as **width 0**.
      ⚠️ **THE SUBJECT UNDER TEST MOVES THE INSTRUMENT.** Every other probe
      reads the name table at a fixed 40-byte stride and `WIDTH`'s whole job is
      to change that stride, so the readout is numeric instead: capture
      `ERR` + `LINLEN`/`LINL40`/`LINL32` into variables, RESTORE
      `SCREEN 0`+`WIDTH 40`, and only then print. And **the instrument is pinned
      on every row** — unpinned, three controls that execute no `WIDTH` at all
      diverged on the boot width (37 vs 39) while their `ERR` codes agreed.
      ⚠️ These batteries **arm `ON ERROR` on purpose**, the opposite of
      `abort-acceptance`/`str-domain-acceptance`: those measure the unwind,
      which a handler hides; this measures the domain, and a trapped `ERR` read
      is the only readout that survives a statement that just destroyed the
      screen. The `unt` battery is the seam between the two gates.
      **Cost: 27 B, all page 1 (30 B → 3 B free)**, low region untouched at
      30 B, lean cart byte-identical. Cheap because `LINL40`/`LINL32` are
      ADJACENT (one `ld de` + a conditional `inc de` picks the slot and the
      bound rides the same test) and all three raisers already existed in
      page 1 — including `loc_missing`, the ERR 24 raiser `LOCATE` built.
      ⚠️ **3 B is not headroom — the next page-1 slice must open with a carve.**
      Falsified: neutering the bound reddens the two ordering rows while six
      unrelated `sx` rows survive; neutering the one-byte `inc de` reddens all
      11 `s1` rows. Standing gates re-run green: `unit-test` 53/53,
      `abort-acceptance` 23/23, `intarg-acceptance` ALL PASS,
      `str-domain-acceptance` 89/89.

- [x] ✅ **String-function ARGUMENT-DOMAIN checks — LANDED 2026-07-28, 89/89,
      falsified 51/89.** Was 🔴 SILENT wrong answers shipping today.
      Found by the MISSING-class calibration battery
      (D-MISS-2,
      [`docs/missing-vg8020-characterization.md`](docs/missing-vg8020-characterization.md)
      §8), which was not looking for it — the fourth slice running whose
      calibration turned up live defects in code that is not under test.
      `CHR$` / `LEFT$` / `RIGHT$` / `MID$` accept out-of-range arguments
      **silently and compute a wrong answer**:
      `LEN(CHR$(-1))`→`1`, `LEN(CHR$(256))`→`1`, `LEN(LEFT$("abc",-1))`→`3`,
      `LEN(MID$("abc",0))`→`3`, where the reference raises.
      Three things make this a slice rather than a one-liner:
      (a) **the family is inconsistent with itself** — `STRING$`/`SPACE$`/`ASC`
      DO check and are correct, so the mechanism exists and is reachable (the
      probe proves that with a control row before reading any other row as
      "zerobas cannot raise it"); (b) there are **TWO reference errors, not
      one** — `Illegal function call` inside byte range, but **`Overflow`**
      beyond int16 (`CHR$(32768)`, `CHR$(99999)`), raised by the argument
      coercion before the domain check runs, so an implementation that raises
      `Illegal function call` everywhere is wrong on half the domain;
      (c) **in-domain behaviour already agrees**, coercion included
      (`CHR$(65.7)`→`A`, `CHR$(64.5)`→`@`, i.e. truncation), so this is a domain
      check bolted onto correct code.
      **This is a different animal from the now-empty SILENT-GAP class** (absent
      reserved words), which is exactly why it survived it. Recommended as its
      own string-engine slice — see D-MC-2 in
      [`docs/decision-missing-class-slicing.md`](docs/decision-missing-class-slicing.md).
      ✅ **RE-MEASURED 2026-07-28 on a clean-built `73b4842`: all seven rows
      still reproduce**, boot-per-case, untrapped (`LEN(CHR$(-1))`→`1`,
      `LEN(CHR$(32768))`→`1` where the reference raises `Overflow`,
      `LEN(LEFT$("abc",-1))`→`3`, `LEN(MID$("abc",0))`→`3`).
      ⚠️ **ORDERED SECOND, behind D-CUR-D** (the abort-depth item above,
      signed off 2026-07-28): the natural implementation is four to five new
      `call get_byte_arg`s from inside the evaluator, i.e. four to five new
      members of a call convention that is measurably broken when untrapped.
      Landing that first would give the right ERR code under `ON ERROR` and
      trailing junk without it.
      ✅ **SPECCED + GATED 2026-07-28**, spec
      [`docs/spec-basic-str-domain.md`](docs/spec-basic-str-domain.md), gate
      `make str-domain-acceptance` (89 rows, six batteries). **41/89 diverge.**
      The measurement corrected this item on three counts:
      🔴 **THE FUNDING PREMISE BELOW WAS WRONG — there is nothing to fund.**
      Prototyped from clean: the low region goes **7 B → 30 B free (+23 B)** and
      page 1 **44 B → 30 B (−14 B)**. No promotion, no carve; lean cart
      byte-identical so `LEAN_SHA256` does not move. Two reasons the ≈45–50 B
      estimate missed: `get_int16_checked` already GUARDS HL so none of the
      assumed register-guard bytes exist, and `call eval` was ALREADY at every
      site — so a shared `eval_byte_arg`/`eval_pos_arg` pair in page 1 costs
      **zero bytes at the call site** and REPLACES rather than adds. The naive
      shape the estimate was costing was also built: +26 B, all low-region, a
      19 B overrun — 49 B worse on the wall that binds.
      🔴 **The `MID$` STATEMENT is a second broken surface**, not in this item:
      `MID$(A$,0)="X"` etc. give `syntax error` for seven reference errors, and
      **`MID$(A$,1,256)="X"` silently PERFORMS the assignment** while
      `MID$(A$,1,99999)="X"` silently does nothing.
      🔴 **`INSTR` is silently wrong too, and was on no list** —
      `INSTR(256,A$,"b")`→`0` where the reference raises; it hand-rolls half the
      rule (`p<1` only, no upper bound, no int16 stage). Found because S-SD-3
      was answered by RUNNING the probe instead of by argument. **Folding it in
      makes the slice 20 B CHEAPER** — its hand-rolled checks are deleted.
      Also measured: `MID$`'s position is the family's one **1-based** argument
      (1..255); the int16 gate is the RANGE −32768..32767, not `|x| ≤ 32767`
      (`CHR$(-32768)`→IFC, `CHR$(-32769)`→Overflow), and `get_byte_arg` already
      implements exactly that, proven via `STRING$(-32768,65)`.
      ⚠️ Three standing gates went red BECAUSE this closes a divergence they
      record, and all three were EDITED, not silenced: `missing-acceptance`'s 8
      stale `d2-*` markers (**XDIVERGENT's D-MISS-2 section is now EMPTY** —
      every `d2-*` row is gated), `basic_probe_mid_stmt.py`'s asserted
      divergence (now an asserted AGREEMENT, and it keeps earning its place by
      proving `A$` is unmutated by the rejected assignment), and
      `tests/test_str_fn.py`'s `INSTR(0,…)` — which the host harness
      structurally cannot model once the reject raises, exactly as D-F2-2 found
      for `SPACE$`/`STRING$`. **No host unit test can cover any row of this
      slice**; the openMSX differential is the only instrument, which is why the
      falsification below is load-bearing.
      ✅ **LANDED**: `make str-domain-acceptance` **89/89**; low region
      **7 B → 30 B free**, page 1 **44 → 30 B**, lean cart byte-identical
      (`LEAN_SHA256` unmoved); `unit-test` 53/53, `abort-acceptance` 23/23,
      `intarg-acceptance`/`string-acceptance`/`missing-acceptance` green.
      **FALSIFIED 89/89 → 51/89**: all eight call sites reverted to plain
      `call eval`, rebuilt from clean. ⚠️ **The wall does NOT move under this
      falsification** (30/30 either way) — `call eval` and `call eval_byte_arg`
      are both 3 B and the helpers stay assembled, so unlike D-CUR-D the
      "low region went back" check is NOT available as proof the code left the
      image. Every survivor is explainable: `ctl` 7/7 and `in` 23/23 survive by
      construction (in-domain rows pass with and without the checks, which is
      why they can never be the evidence and why they must be there), the
      surviving `bnd` rows are all `STRING$`/`SPACE$`, and **`ext-instr-0`/`-neg`
      PASSED in the true baseline but FAIL falsified** — the hand-rolled tests
      are deleted, so that asymmetry is what proves the call site rather than
      the deletion is doing the work.

- [ ] **Numeric → string assignment raises the wrong error** (D-MISS-1, same
      battery). `A$=1`, `A$=A`, `A$=1+1`, `A$=LEN("x")`, `LET A$=A`, `A$=A%` and
      `Q$(0)=1` all raise **`syntax error`** where the reference raises
      **`Type mismatch`** — so `ON ERROR` sees the wrong code. The numeric-lvalue
      **mirror is already correct** (`A=A$`, `A="x"`, `A=CHR$(65)`,
      `Q(0)="x"`), which localises it: the string-lvalue assignment path never
      type-checks its right-hand side and fails in the parser instead. Small and
      well-characterised. ✅ **D-MC-2 SIGNED OFF: folded into the MISSING-class
      slice** — see [`docs/spec-basic-missing-class.md`](docs/spec-basic-missing-class.md)
      §3.6 (surface) and §6.5 (the two paths to fix, `ex_let_str` and
      `ex_let_arr_str`).

## Beyond — post-MSX1 axes (out of charter, far future)

Two distinct axes past MSX1, captured so the boundaries aren't lost. **Neither is
scheduled**; both require a charter raise. They differ in *provenance*, which is the
whole point of listing them apart.

**A. Later generations — a *clone* axis (has oracles).** MSX2, MSX2+, Turbo-R.
Official ASCII BASIC shipped for these and real machines exist, so this is **today's
method with more surface**: clone-and-validate against an oracle. New ground would be
the V9938/V9958 `SCREEN 4–12` modes + blitter, MSX-DOS 2, R800 timing, and the extra
BASIC verbs each generation added. Methodologically identical to current work — just
bigger.

**B. Extension-cartridge hardware — a *greenfield* axis (no oracle).** Additive,
**own-design** BASIC support for cartridge hardware that **never had official BASIC**.
This is the project's only own-authorship corner: no reference implementation to
clone, no oracle to match — correctness is defined by our own spec + the hardware
documentation, and the rule is *additive-compatible* (new verbs / `SCREEN` numbers
above the built-in range; standard programs untouched). Provenance varies **per chip**:

- **Yamaha V9990 (E-VDP III)** — GFX9000 / Power Graph / Video9000 video cartridge.
  **Clean**: an official Yamaha datasheet exists (A; see `docs/allowed-sources.md`,
  gen `ext`). Not V99x8-register-compatible — its own P1/P2/Bx modes + I/O ports.
- **Konami SCC / SCC+** (K051649 / K052539) — wave-table sound in Konami carts
  (Snatcher, Metal Gear 2, Nemesis…). **Caveat**: *no published manufacturer
  datasheet* — the register interface is known only through community
  reverse-engineering. So support would need our **own black-box characterisation**
  of the chip (the oracle discipline applied to silicon), with community register
  maps as **C-tier corroboration only**, never an authoritative spec.
  **Two deliverables, and the document is the more lasting one:** because no
  datasheet exists, a careful black-box characterisation *produces* primary
  documentation rather than reproducing protected work — for once zerobas is
  *upstream*, a source not a sink. The result (register + waveform reference, with
  method and reproducible raw captures — the probe corpus *is* the document) would
  be an **A-grade, clean-provenance** artifact by our own scale, promoting the SCC
  from "C-tier community-RE only" to "A, our own characterisation," and a standalone
  gift to MSX preservation (emulator authors, homebrew musicians, the next
  reimplementation) **independent of whether the BASIC extension ever ships**.

(Third-party BASIC extensions exist for both — proprietary, **not** a source; design
our own from the hardware docs / our own characterisation.)

## Done — storage transports

### Disk (`disk/` → `disk.rom`, slot 3-1) — complete, read **and** write
The full FDC + FAT12 + BDOS stack, both directions, each layer
differential-confirmed against real hardware/software (strictly black-box, no
disassembly): WD2793 physical sector read **and** write vs the **National
CF-3300**, and the FCB BDOS file read **and** write (Open/SeqRead/Close +
Create/SeqWrite/Close, on a FAT12 read+write-back layer) vs real **MSX-DOS 1**.
The interpreter side lives in `basic/`: `BLOAD`/`LOAD`/`RUN`/`SAVE`/`BSAVE` for
`"A:"`, the `init_ext_roms` slot-scan ([`basic/initext.asm`](basic/initext.asm))
that boots the disk ROM, and the cross-slot BDOS calls. See
[`disk/TODO.md`](disk/TODO.md) and [`disk/PROVENANCE.md`](disk/PROVENANCE.md) for
the per-item record and the documented divergences (FCB bookkeeping fields,
directory timestamps, the intentional GETDPB stub).

### Tape (`tape/` → zerobas-tape IPS patch) — device layer complete, read **and** write
The cassette signal layer C-BIOS lacks: `TAPION`/`TAPIN`/`TAPIOF` (read) and
`TAPOON`/`TAPOUT`/`TAPOOF` (write) — FSK leader detect + auto-baud + byte framing
and the write waveform, at 1200 and 2400 baud, round-trip validated on MSX1 /
MSX2 / MSX2+. See [`tape/DESIGN.md`](tape/DESIGN.md) and
[`tape/PROVENANCE.md`](tape/PROVENANCE.md). The **interpreter** side is now at full
parity — `BLOAD"CAS:",R`, `CLOAD` and `LOAD"CAS:"` load and `CSAVE`/`SAVE"CAS:"`/
`BSAVE"CAS:"` save on-device. (The CLOAD on-device fix turned out to be a
`basic/cload.asm` link-word register clobber, not a tape change; tape SAVE writes
the `$D3`/`$D0` cassette format through `TAPOON`/`TAPOUT`/`TAPOOF`. Both are
oracle-validated — see the now-checked items in the **Remaining** section above and
`basic_probe_tape_save.py` / `basic_probe_cload_ondevice.py`.)
