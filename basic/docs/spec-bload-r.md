# Behavioural spec: `BLOAD"CAS:",R` — cassette binary load with handoff

Derived from **oracle observation only** (openMSX headless, Philips VG-8020,
black-box input→output capture) plus allowed public sources. No disassembly
consulted. See `CONTRIBUTING.md`.

This is the implementer-facing artefact for Phase 1 ("first light"). The
implementation lives in the BASIC project's own repo, not here.

## What was tested

A self-authored binary blob (102 bytes) was wrapped in a `.cas` BSAVE image,
inserted as a cassette, and loaded via the direct-mode line:

    BLOAD"CAS:",R

The blob writes `"JONG"` to `0xE000` and halts at a fixed landmark (`JR $` at
`0xC064`). The harness broke on the landmark and captured registers + memory.

## Observed behaviour

### 1. `.cas` BSAVE-binary block layout

A BSAVE `.cas` file consists of two logical blocks, each preceded by the 8-byte
cassette sync header:

```
[sync 8] [header block 16] [sync 8] [data block 6+N]
```

**Header block (16 bytes):**

| Offset | Length | Content                                      |
|--------|--------|----------------------------------------------|
| 0      | 10     | File-type identifier: `0xD0` repeated 10 times (= binary/BSAVE) |
| 10     | 6      | Filename, ASCII, space-padded to 6 chars      |

**Data block (6 + N bytes):**

| Offset | Length | Content                          |
|--------|--------|----------------------------------|
| 0      | 2      | Start address (little-endian)    |
| 2      | 2      | End address (little-endian)      |
| 4      | 2      | Execution address (little-endian)|
| 6      | N      | Payload bytes (N = end − start + 1) |

### 2. Load-to-memory

Bytes from the data block payload are placed **verbatim** into RAM at addresses
`start..end`. Oracle-confirmed: the 102 bytes at `0xC000..0xC065` in the capture
are byte-identical to the authored blob.

### 3. The `,R` handoff

After loading completes, `,R` causes an immediate jump to the **execution
address** from the data-block header. The blob's exec address was set to
`0xC000` (= load address); the breakpoint fired at `0xC064` (the `JR $`
landmark inside the blob), confirming control transferred and the blob
**executed**.

Register state at handoff: `A=0x47` (last byte written by the blob, `'G'`),
`SP=0xF098`.

### 4. Work-area sysvars (oracle dump)

| Sysvar  | Address  | Value (hex) | Interpretation |
|---------|----------|-------------|----------------|
| TXTTAB  | `0xF676` | `0x8001`    | Program text base — unchanged (no program loaded) |
| VARTAB  | `0xF6C2` | `0x8003`    | Variable table — same as empty program |
| ARYTAB  | `0xF6C4` | `0x8003`    | Array table — same |
| STREND  | `0xF6C6` | `0x8003`    | String end — same |
| SAVEND  | `0xF87D` | `0x0000`    | Not updated by BLOAD (uses header words directly) |
| FILNM2  | `0xF871` | `"BLOAD "` + 5× `0x00` | Filename buffer (11 bytes) |

Key observation: `BLOAD` does **not** alter the BASIC program pointers
(`TXTTAB/VARTAB/ARYTAB/STREND`). A binary load is independent of the program
storage area. `SAVEND` is not set — `BLOAD` reads start/end/exec from the file
header directly and does not persist them.

### 5. Cassette device name

The device name `"CAS:"` selects the cassette I/O path. BASIC delegates the
actual byte transfer to the cassette BIOS routines (`TAPION` `0x00E1`,
`TAPIN` `0x00E4`, `TAPIOF` `0x00E7`) via the file-I/O hooks. The interpreter's
responsibility ends at reaching the handoff.

## Provenance log

Every constant used in the `.cas` encoder and this spec:

| Item | Value | Source (allowed) | Status |
|------|-------|------------------|--------|
| Cassette sync header (8 bytes) | `1F A6 DE BA CC 13 7D 74` | MSX2 Technical Handbook, cassette I/O chapter | sourced |
| Binary file-type ID | `0xD0` × 10 | MSX2 Technical Handbook, BSAVE file format | sourced |
| Filename length | 6 chars, space-padded | MSX2 Technical Handbook | sourced |
| Data header: start/end/exec words (LE) | 3 × 16-bit LE | MSX2 Technical Handbook, BSAVE format | sourced |
| TAPION entry point | `0x00E1` | MSX2 Technical Handbook / MSX Assembly Page BIOS call list | sourced |
| TAPIN entry point | `0x00E4` | MSX2 Technical Handbook / MSX Assembly Page BIOS call list | sourced |
| TAPIOF entry point | `0x00E7` | MSX2 Technical Handbook / MSX Assembly Page BIOS call list | sourced |
| TXTTAB address | `0xF676` | MSX2 Technical Handbook sysvar map / MSX Assembly Page | sourced |
| VARTAB address | `0xF6C2` | MSX2 Technical Handbook sysvar map / MSX Assembly Page | sourced |
| ARYTAB address | `0xF6C4` | MSX2 Technical Handbook sysvar map / MSX Assembly Page | sourced |
| STREND address | `0xF6C6` | MSX2 Technical Handbook sysvar map / MSX Assembly Page | sourced |
| SAVEND address | `0xF87D` | MSX2 Technical Handbook sysvar map / MSX Assembly Page | sourced |
| FILNM2 address | `0xF871` | MSX2 Technical Handbook sysvar map / MSX Assembly Page | sourced |
| TXTTAB value after boot (`0x8001`) | oracle observation | This project's own black-box observation | sourced |
| SAVEND value after BLOAD (`0x0000`) | oracle observation | This project's own black-box observation | sourced |
| SP at handoff (`0xF098`) | oracle observation | This project's own black-box observation | sourced |

No quarantined items — all constants trace to allowed sources or oracle observation.

## Determinism

Two consecutive runs produced byte-identical captures (per `docs/openmsx-harness.md`
determinism guarantee), confirming this spec is reproducible.

## What the implementer must build (summary)

To make `BLOAD"CAS:",R` work in zerobas-BASIC:

1. **Tokenise** the direct-mode line (at minimum: recognise `BLOAD` keyword).
2. **Parse** the `"CAS:"` string argument and the `,R` option.
3. **Delegate** to the cassette BIOS via the file hooks to read the header block
   (verify `0xD0` file type) and the data block (read start/end/exec + payload).
4. **Load** payload bytes into RAM at `start..end`.
5. If `,R`: **jump** to `exec`.
