# zerobas roadmap

zerobas is a **clean-room reimplementation of MSX1 system software** — three
components (BASIC interpreter + cassette + disk) combined with an open BIOS (C-BIOS)
only at runtime — with **two co-equal goals**: the clean-room implementations
themselves, and the clean-provenance **documentation** of how these systems work
that the same discipline yields (see [`MISSION.md`](MISSION.md)). Scope today
is MSX1; the BASIC half is **game-loader-scoped** (just enough to run the `.BAS` /
binary loader stubs that boot disk and tape games), while tape and disk are
device-complete (read **and** write).

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
| **3+ — full MSX1 BASIC** | floating point, full string engine, arrays, graphics, sound, … | aspirational |

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
      every sub-item below landed + oracle-validated.
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
      decode); crunch + all regression probes still pass. Divergence: only the
      no-arg whole-program form — `LIST n` / `LIST n-m` range args are Phase 3,
      a trailing argument is parsed-past + ignored.)
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

## Phase 3+ — full MSX1 BASIC (aspirational)

Beyond Phase 2's disk axis — the rest of "real MSX BASIC." Listed for reference
and to mark the natural boundaries, **not** scheduled work; the disk/file story
(`OPEN`/`CLOSE`/`PRINT#`/… and Disk BASIC delegation) has been pulled forward into
**Phase 2** above. These remain explicitly out of scope until then.

- [ ] **Floating point** — the math pack, `!`/`#`/`%` type suffixes,
      `DEFINT`/`DEFSNG`/`DEFDBL`/`DEFSTR`, and the float crunch tokens
      (decimal ≥ 32768 etc.) currently out of scope
- [ ] **Full string engine** — string variables + heap, `+` concat,
      `LEN MID$ LEFT$ RIGHT$ INSTR STR$ VAL CHR$ ASC HEX$ OCT$ STRING$ SPACE$ INKEY$`
- [ ] **Arrays + `DIM`** (numeric and string, multi-dimensional)
- [ ] **`^`** and the math functions
      `ABS SGN INT SQR SIN COS TAN ATN LOG EXP RND FIX CINT CSNG CDBL`
- [ ] **I/O** — `INPUT`, `LINE INPUT`, `INPUT$`, `PRINT USING`; file I/O
      (`OPEN CLOSE PRINT# INPUT# GET PUT EOF LOF LOC`, `MAXFILES`); full tape
      verbs (`SAVE LOAD CSAVE CLOAD MERGE BSAVE`, `MOTOR`)
- [ ] **Graphics** (TMS9918) — `SCREEN 0–3`, `LINE`, `PSET`/`PRESET`,
      `CIRCLE`, `PAINT`, `DRAW`, sprites (`GET`/`PUT`, `SPRITE$`), `VDP`
- [ ] **Sound** (AY-3-8910) — `SOUND`, `PLAY` (MML), `BEEP`
- [ ] **Input devices** — `STICK STRIG PAD PDL`, `KEY(n)`, `STRIG(n) ON/OFF/STOP`
- [ ] **Error handling** — `ON ERROR GOTO`, `RESUME`, `ERR`/`ERL`, `ERROR n`,
      numbered error messages
- [ ] **Interrupt traps** — `ON INTERVAL/KEY/SPRITE/STOP GOSUB`
- [ ] **Screen-editor REPL** — real MSX BASIC does not use a sequential prompt
      loop; Enter reads the *current cursor line from VRAM* (not a dedicated
      input buffer), so the user can cursor-up to any visible output, edit it
      in place, and re-enter it. Needs cursor-key handling and VDP line-readback.
      Our `repl.asm` is a deliberate simplification; full replacement is Phase 3.
- [ ] **Editor / program management** — full `LIST`, `DELETE`, `RENUM`, `AUTO`,
      `TRON`/`TROFF`, `SWAP`, `WAIT`, `ERASE`, `FRE`, full `CLEAR` semantics

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
