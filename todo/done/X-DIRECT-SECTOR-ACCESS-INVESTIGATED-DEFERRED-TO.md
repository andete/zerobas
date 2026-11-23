- [x] **Direct sector access — INVESTIGATED, DEFERRED to Phase 3** — `DSKI$` (fn,
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
      ✅ **SHIPPED 2026-09-11 (D-DSKIO, [`docs/spec-basic-dskio.md`](../../docs/spec-basic-dskio.md),
      `make dskio-acceptance`, 5 rows, both machines).** The three counts above
      were all wrong in the same way — they read a black box that was never
      opened. Measured on the CF-3300 with a Tcl write-watchpoint RAM dump
      ([`scratchpad/dskio_scout.py`](../../scratchpad/dskio_scout.py)): `DSKI$(d,s)`
      evaluates to the EMPTY string (its descriptor points at a ROM constant,
      $6B4F) and puts the sector in the disk ROM's buffer at **$EB95**, whose
      address is the word at **$F351** — the MSX idiom `PEEK(&HF351)+256*PEEK(&HF352)`,
      measured rather than remembered; `DSKO$ d,s` writes that buffer back
      (`POKE` the first byte, `DSKO$ 0,7`, and `FILES` lists `XEST    .BIN` —
      on the disk, read from the host side, not only on the screen). So (1) the
      semantics are not obscure, (2) no 512-byte string is ever needed, (3) the
      CF-3300 IS a clean oracle for both. Tokens from the VG-8020's own program
      text: `DSKI$` = **$EA** and `DSKO$` = **$D1**, single bytes both (the
      old note's "$FF-prefixed function" reading was the DSKF shape, not this).
      Here: `dsk_core` (low region) parses `drive` (0/1; 2.. is ERR 62 as the
      reference says) and `sector` into `FWR_DIRSEC`, gates on `H_DSKO`/`H_DSKI`
      BEFORE the parse (the diskless VG-8020 says ERR 5 to `DSKO$ 0` where the
      CF-3300 says ERR 2 — measured), then dirverb-tenant ops 4/5 move the
      sector between `(DSKBUF_PTR)` and the disk; `DSKBUF_PTR` = $F351 names
      `FSECTOR_BUF` and is written by the disk ROM's `install_basic_hooks`
      ($F34D..$F358 asked of the machine first: 12 planted bytes survived a
      two-channel/KILL/FILES/DSKF/string/DEF FN workload). `nodisk-acceptance`
      gained `k.dski`/`h.dsko` (ERR 5 on both diskless sides). Cost: main page 1
      43 → 5 B, low region 75 → 9 B (the D-PAIRCARVE budget, spent the same
      night), sub page 1 756 → 719 B, kwtable +16 B (re-pinned).
      🎯 **THE EIGHT SCOUTS' PINS LEFT `filed-row-known.txt` WHEN THE EIGHT-KEYWORDS
      ITEM CLOSED (D-COPY)** — seven re-ran clean; `dskibytes_probe` still reads
      DIFF because it PEEKs $EB00, the REFERENCE's landing address, on zerobas
      too (the buffer here is `FSECTOR_BUF`, and `$F351` says so) — the
      pointer-driven `dir`/`boot` rows of `dskio-acceptance` are the
      machine-independent reading, and they converge.
      ✅ **D-DSKNODISK CLOSED BY D-DISKERR (2026-09-11): `d.dski`/`d.dsko` read `ERR 70 AT 20` in `nodiskerr-acceptance`.** The residual as filed:
      🔴 (was) RESIDUAL, TIER 3 (D-DSKNODISK): with NO DISK IN THE DRIVE the CF-3300
      answers `ERR 70` (Disk offline) to both; here `DSKI$` raises ERR 2 (the
      `load_error` exit taken INSIDE an expression surfaces as a Syntax error)
      and `DSKO$` raises nothing.** Measured, not fixed: ERR 70 is the item
      Joost ruled to add ("add ERR 70, maybe an ERR extension mechanism in the
      Disk ROM"), and this is its first concrete customer.
      🎚️ TIER 1 — happy path: `DSKI$` `DSKO$` shipped; the no-disk face is TIER 3 (D-DSKNODISK)
      ~~🙋 NEEDS-JOOST — a call that is yours to make (charter / scope).~~ (re-marked 2026-09-10, see below)
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
      - [x] **360 KB + the geometry menu** — DONE (basic/format.asm). Added a
            GEOM_360K descriptor (media $FD, 720 sectors, 2 sec/FAT) and a minimal
            `1=360k 2=720k?` prompt (read via the REPL line editor; drive + confirm
            prompts trimmed). do_format reads the chosen descriptor through FMT_DESC —
            geometry-agnostic. Both geometries' BPB + FAT head byte-identical to the
            matching CF-3300 format (360K = "2 sides", 720K = "2 sides double track"),
            and a file round-trips on each fresh disk (disk_probe_format.py).
