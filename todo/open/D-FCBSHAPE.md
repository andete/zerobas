- [ ] 📁 **D-FCBSHAPE — ADOPT THE MSX FCB LAYOUT FOR FILE CHANNELS (39 B A CHANNEL OVER THE REFERENCE; UNLOCKS `VARPTR(#n)`)**
      🎚️ TIER 6 — re-tagged 2026-10-10 from TIER 4: the RAM half is DONE. A
      channel costs 267 B on both references and here (S1+S2, 2026-09-30; FCB #0
      2026-10-10), and `VARPTR(#n)` shipped (D-VARPTRCH). What is left is the
      INPUT / tape channel's MOVING position byte (+6), which only
      `PEEK(VARPTR(#n)+6)` can see — the long tail, not RAM. (The headline's
      "39 B a channel" and "306" are the 2026-09-16 readings.)
      🏗️ **RULED BY JOOST:** 2026-09-16 *"I think this means we need to change to
      the MSX's FCB shape"*; 2026-09-17 *"just note it, you don't need to do
      anything now"*; 2026-09-26 *"file it as a tier 4 item"* — so it is filed,
      and it was only prose inside the carve-inventory block until now (which is
      why the tier sheet showed `VARPTR` PARTIAL with NO open item naming it).
      📏 **WHAT IS MEASURED** (all in that prose block, the `VARPTR STANDS AT 1/2`
      paragraph; `scratchpad/varptrn_probe.py`, `scratchpad/fcbstride_probe.py`,
      `docs/chancost-cf3300-characterization.md` §2):
      | | reference (VG-8020 / CF-3300) | zerobas |
      |---|---|---|
      | `VARPTR(#1)` | an address (−3465 / −8850) | `Syntax error` |
      | stride #n → #n+1 | **265** = FCB: 9 header + 256 record | — (block 306) |
      | `FRE(0)` per `MAXFILES` channel | **267** (265 + 2 in a separate per-channel table) | **306** |
      | geometry | FCB array hangs DOWN from `$F380`, #1 lowest: `VARPTR(#n) = $F380 − 265·(MAXFILES − n + 1)` | — |
      At `MAXFILES=15` zerobas spends **585 B** more pool than the reference.
      💰 **THE WORK IS THE 41 BYTES, NOT THE STRIDE.** Our block is
      `[state:FCH_STATESZ 50][record:256]`; MSX's header is 9. The per-channel
      ENGINE state (cluster iterator `FAT_CURCLUS`/`FAT_CLUSSEC`, file meta, …)
      needs a home outside the FCB; then a channel costs 265 + 2 and `VARPTR(#n)`
      is `fch_ctx_addr` on the new layout, agreeing by construction.
      ⚠️ **PRICE IT WITH THE CHANNEL I/O REDESIGN** — D-FATPAGE1 (same prose
      block) found the ~317 B byte-level FAT I/O carve is the SAME layer; the two
      should be designed together, and an inter-slot call per BYTE is a TIER 2
      risk (0.156 ms each, D-XSLOTPRICE).
      📏 **STEP 1 MEASURED 2026-09-26 (loop, `scratchpad/fcbfields_probe.py` →
      `scratchpad/fcbfields_run.out`)** — PEEK at `VARPTR(#n)`, both references:
      | offset | VG-8020, `CRT:` | CF-3300, disk file | reading |
      |---|---|---|---|
      | +0 | `02` | `02` | the file MODE (2 = OUTPUT) |
      | +1..+2 | `FF 00` | `B5 DE` | disk: a POINTER (`$DEB5`) into the disk work area |
      | +4 | `FD` | `01` | the DEVICE (`$FD` CRT:, `01` drive A:) |
      | +6 | `00` (unbuffered) | `00 → 02 → 03` after `"AB"`, `"ABC"` | the BUFFER POSITION |
      | +9.. | — | `41 42 43` | the RECORD starts at +9 |
      VG-8020 `VARPTR(#1)` `$F16E`, `#2` `$F277` (= +265; `$F277`+265 = `$F380`,
      the top); CF-3300 `#1` `$DC65`, below its disk work area. The other header
      bytes read as uninitialised on `CRT:`. 🎯 **SO THE DESIGN IS PINNED:** a
      zerobas block must put mode at +0, device at +4, position at +6 and the
      record at +9; the 41 B of engine state go ELSEWHERE — which is what the
      reference's +1 pointer does on disk.
      📏 **STEP 2 MEASURED 2026-09-26 (loop, `scratchpad/filtab_probe.py` →
      `scratchpad/filtab_run.out`) — THE 2 BYTES ARE `FILTAB`'s POINTER TABLE,
      AND THE 265 + 2 = 267 HYPOTHESIS HOLDS.** The published `FILTAB`
      (`$F860`) points at a table of **MAXFILES + 1** two-byte FCB pointers —
      one per channel **including #0** (the one `LOAD`/`SAVE` use) — sitting
      directly BELOW the FCB array:
      | MAXFILES | `FILTAB` | table | FCB #0 | #1 | #2 | #3 |
      |---|---|---|---|---|---|---|
      | 1 | `$F16A` | 4 B | `$F16E` | `$F277` | | |
      | 2 | `$F05F` | 6 B | `$F065` | `$F16E` | `$F277` | |
      | 3 | `$EF54` | 8 B | `$EF5C` | `$F065` | `$F16E` | `$F277` |
      So, top-down from `$F380`: FCB #MAXFILES … FCB #1, FCB #0, then the
      pointer table, `FILTAB` pointing at it. ⚠️ Correction to the D-FCBSTRIDE
      wording above ("#1 lowest"): #1 is lowest among the USER channels; #0 sits
      below it. The formula `VARPTR(#n) = $F380 − 265·(MAXFILES − n + 1)` stands.
      🔮 Predicted "MAXFILES + 1 pointers just below the FCBs" — HIT.
      📝 **DESIGN WRITTEN 2026-09-26: `docs/spec-fcbshape.md`** — the measured
      layout, today's block (its 50 B are ALL disk-engine state; the address is
      derived in ONE place, sub op 18), the target, slices, and the walls
      (sub page 1 was 0 B free, clean build 2026-09-26 — a carve first).
      ~~🙋~~ 🏗️ **RULED BY JOOST 2026-09-27: (a), THE FIXED DISK TABLE** — the reference's
      shape; the disk build pays ~800 B of boot `FRE(0)` for it. 🤖 **AUTONOMOUS
      now** (slices S1–S3, spec §6), carve first.
      🤖 **AUTONOMOUS** — ruled by Joost 2026-09-27 (above); a carve comes first.
      Was: **NEEDS-JOOST — the disk build's engine-state home (spec §4):** (a) a
      fixed table in the disk work area behind the FCB's +1 pointer — the
      reference's shape; costs the disk build ~800 B of boot `FRE(0)` (it leads
      the CF-3300 by ~635 B today) — or (b) allocate per disk OPEN (OPEN then
      charges 61 B, not the reference's 11) or (c) size it by MAXFILES (317 B a
      channel). The diskless build is a pure +39 B a channel either way.
      🟢 **S0 SHIPPED 2026-09-29 — THE BLOCK LAYOUT MOVES INTO ONE ROM, AND IT WAS
      THE CARVE.** D-CPY18 had just opened sub page 1 (1 → 699 B). Main's
      `fch_save_active` / `fch_load_ctx` were pure copies between the engine
      globals and the block, plus two crossings into the FAT tenant, so their
      bodies moved INTO the tenant (`t_fch_save` / `t_fch_load`, selectors
      `DISKOP_SEL_FCH_SAVE` 21 / `_LOAD` 22). Main keeps 13 B shims, and
      `fch_restage` / `fch_flush_active` lost their only callers and went. A save
      still reports the FLUSH's status (Cy, A, HL carried across the copies),
      because `chan_gate`'s claimed-status logic reads it that way.
      **Main page 1 0 → 41 B; sub page 1 699 → 648 B** — both predicted (~41, ~648)
      from the instruction count ([`fcbs0_walls.out`](scratchpad/fcbs0_walls.out)).
      `diskbasic-acceptance` 34/34 converged; knife BLIND unchanged
      ([`fcbs0_knife_all.out`](scratchpad/fcbs0_knife_all.out),
      [`fcbs0_knife_fn.out`](scratchpad/fcbs0_knife_fn.out)), kwsweep SUPPORTED 952
      ([`fcbs0_kwsweep.out`](scratchpad/fcbs0_kwsweep.out)), kwtime OK 838
      ([`fcbs0_kwtime.out`](scratchpad/fcbs0_kwtime.out)). ⚠️ **Spec §6 now records a
      constraint the slices had not faced:** the DISK and NODISK machines run the
      SAME main and sub images, so the layout cannot differ per build at assembly
      time. S1 and S2 are ONE runtime design, not "diskless first".
      ➡️ **NEXT: S1+S2 together** (`docs/spec-fcbshape.md` §6): the layout in
      the tenant plus op 18's stride, the `FILTAB` table, the header fields, and
      the disk-engine state's fixed table (ruled (a)) reached through the +1
      pointer. VARPTR(#n) needs main bytes, and 41 now exist.
      📐 **DESIGNED 2026-09-29 (spec §7), from a measurement:** every machine
      accepts `CLEAR 200,&HF380`, the CF-3300 included, whose boot `HIMEM` is
      `$DE77`, below its own disk work area ([`clearmax_run.out`](scratchpad/clearmax_run.out)).
      The reference reserves that area by LOWERING `HIMEM` AT BOOT and does not
      protect it afterwards. So the disk-engine table takes the same shape for 0
      main bytes: disk.rom init lowers `HIMEM` by 800, and the table sits at the
      constant `TXTMAX − 800`. The slice is one commit; sub page 0 (9 B,
      2026-09-29) is its likely wall, so it gets priced first.
      🟢 **S1+S2 SHIPPED 2026-09-30, WITHOUT `VARPTR(#n)`.**
      - **Block and charge:** a channel block is 265 B (the reference's 9-byte
        FCB header + the 256 B record), and `MAXFILES` charges 267 a channel
        (`FCH_CTXSZ`, the 2 FILTAB bytes above the blocks). Channel 1 stays at
        the table base, because `program.asm`'s store ceiling reads it that way.
      - **Engine state:** a DISK channel's 50 B go to/from `DSK_ENGTAB` (row =
        channel number) in the FAT tenant (`fch_engrow`); device and cassette
        channels keep none.
      - **Reserve:** disk.rom's init sets `HIMEM` to the table base. Main's boot
        store keeps a HIMEM already below `TXTMAX` (the disk ROM's INIT runs
        FIRST, in the slot scan; +9 B of main page 1, measured 2026-09-30).
      - **disk.rom:** `hkk_open_check` reads a saved channel's dir position from
        the table, with no call back into main.
      - **Walls, 2026-09-30:** main page 1 12 → 3 B, sub page 1 524 → 474 B,
        disk 6522 → 6517 B ([`fcbs12_walls.out`](scratchpad/fcbs12_walls.out)).
      📏 **Measured:**
      - `chancost-characterize` reads **267 B a channel on BOTH machines**, ceiling
        15, 53 cases, 0 filed divergences ([`fcbs12_chancost.out`](scratchpad/fcbs12_chancost.out)).
        🔮 Predicted it would report a stale allowlist entry: MISS — it gates the
        mechanism, not the constant.
      - The disk machine boots with `HIMEM` `$DCE0`, and its FRE(0) is exactly 800 B
        under the diskless build's; with that program it trails the CF-3300 by
        126 B, where it used to lead by ~635 ([`fcbs12_bootfre.out`](scratchpad/fcbs12_bootfre.out)).
      - Channel switching, in and out of FOR/GOSUB, and the open-file refusals
        (54/64/65, KILL of a NON-active open file included) all agree
        ([`fcbs12_chanloop.out`](scratchpad/fcbs12_chanloop.out),
        [`fcbs12_killopen.out`](scratchpad/fcbs12_killopen.out)).
      - Whole sweep SUPPORTED 958, kwtime OK 844, knife BLIND unchanged
        ([`fcbs12_kwsweep_full.out`](scratchpad/fcbs12_kwsweep_full.out),
        [`fcbs12_kwtime.out`](scratchpad/fcbs12_kwtime.out),
        [`fcbs12_knife_all.out`](scratchpad/fcbs12_knife_all.out),
        [`fcbs12_knife_fn.out`](scratchpad/fcbs12_knife_fn.out)).
      ➡️ **LEFT:** ~~`VARPTR(#n)`~~ SHIPPED as D-VARPTRCH (below, 23 B after the
      D-ONTRAPMERGE carve). Still open, all three MEASURED on 2026-09-30:
      - ~~the FCB header FIELDS (mode +0, device +4, position +6): nothing writes
        them. `PEEK(VARPTR(#1))` after `OPEN"CRT:"` reads 2 on both references
        and 255 here.~~ ✅ **D-FCBHDR (2026-10-08): OPEN writes them.**
        [`basic_probe_fcbhdr.py`](probes/basic/basic_probe_fcbhdr.py), gate
        `fcbhdr-acceptance`, mode / device / position after OPEN, each device on
        the reference that owns it ([`fcbhdr_before.out`](scratchpad/fcbhdr_before.out)
        0/8, [`fcbhdr_after.out`](scratchpad/fcbhdr_after.out) 8/8,
        [`fcbhdr_dina.out`](scratchpad/fcbhdr_dina.out)):
        | channel | the reference | ours before |
        |---|---|---|
        | CRT: / LPT: | 2 / $FD, 2 / $FE | 255 / 255 |
        | CAS: OUTPUT / INPUT | 2 / $FF / 0, 1 / $FF / 0 | 255 / 255 / 255 |
        | disk OUTPUT, then 2 B written | 2 / 0 / 0, 2 / 0 / 2 | 255 / 255 / 0, .. / 2 |
        | disk INPUT, `A:` INPUT | 1 / 0 / 0, 1 / 1 / 0 | 255 / 255 / 255 |
        | disk APPEND (26 B file) | **2** / 0 / 26 | 255 / 255 / 26 |
        | RANDOM | 4 / 0 / 0 | 255 / 255 / 255 |
        🔮 Predicted: CRT's $FD and the MODE codes for INPUT / OUTPUT / RANDOM --
        HIT; LPT $FF and CAS $FE (SWAPPED -- MISSED), APPEND mode 8 (it is 2 --
        MISSED), the disk device 1 for a bare name (it is the drive AS TYPED, 0 --
        MISSED), the disk INPUT position 3 after three bytes (it is 2 -- MISSED,
        below). Device channels' +6 is leftover RAM there (255 here, 0 in
        fcbfields_probe.py): mode and device only.
        🔧 Both OPEN tails share `oo_hdr_tail` (basic/files.asm): the block, then
        fatprim row 23 `t_fch_hdr` (sub/fatprim.asm; slot 23 was freed by
        D-ASAVEDOUT the same day), a (mode, device) table over the FCH_MODES value;
        +6 zeroed except disk OUTPUT / APPEND, whose position disk.rom keeps. The
        parser's drive default is 0 now (`basic/pdfcb-body.inc`; nothing else reads
        it). Main page 1 112 -> 101 B, sub page 1 236 -> 177 B (2026-10-08).
        🔪 Knives ([`fcbhdr_knives.out`](scratchpad/fcbhdr_knives.out)): K-FH1 (no
        stamp) -> all 9, K-FH2 (drive default 1) -> dout/din/dapp/drnd, K-FH3 (no
        disk-OUTPUT exemption) -> dapp -- each exactly.
        ➡️ **LEFT:** the MOVING position of an INPUT channel and of a tape channel.
        The CF-3300's disk INPUT +6 reads `0 0 1 2 3 4 5` over the first six
        `INPUT$(1,1)`s and 25 after the 20-byte rest of the line -- the index of
        the last byte read; ours keeps no position in the block (the SEQIO
        tenant's read state is elsewhere), so it stays 0.
        📏 **THE RULE, MEASURED 2026-10-08 on the CF-3300** (a 300-byte file read
        one byte at a time): after k reads +6 is **(k − 1) mod 256** -- 253, 254,
        255 at k = 254..256, then 0, 1, 2 at 257..259, 43 at 300 -- and a
        following `EOF(1)` ADVANCES it (43 → 44): EOF reads one byte ahead. Ours
        reads 0 throughout. Not built: a write on every byte in the SEQIO path
        (plus EOF's look-ahead) for a value only `PEEK(VARPTR(#n)+6)` sees.
        ~~🙋 **FCB #0 IS A RAM-BUDGET QUESTION FOR JOOST, NOT A FIX:**~~ reserving it
        costs every program 267 B of `FRE(0)` (the references pay it too, inside
        their baseline) and moves every FRE row's baseline here; `VARPTR(#0)`
        is its only visible face. ~~Build it, or record ERR 59 as the divergence?~~
        ✅ **RULED (Joost, 2026-10-09): "build it".** 🤖 AUTONOMOUS now: reserve
        FCB #0 so `VARPTR(#0)` returns an address as on both references; re-pin
        every FRE row's baseline in the same commit (the 267 B is expected, not
        a regression). Do not re-ask.
      - **FCB #0** (the LOAD/SAVE channel): `VARPTR(#0)` is an address on both
        references and ERR 59 here, because this tree reserves no FCB #0.
      - the GEOMETRY: FILTAB's pointer table sits BELOW the reference's FCB array,
        so `VARPTR(#1)` shifts 265 per MAXFILES step there and 267 here.
      ✅ **FCB #0 AND THE GEOMETRY BUILT 2026-10-10.** Measured first
      ([`fcb0_probe.py`](scratchpad/fcb0_probe.py) → [`fcb0_run.out`](scratchpad/fcb0_run.out)):
      both references answer `VARPTR(#0)` at EVERY MAXFILES, 0 included (VG-8020
      −3465 at MAXFILES=0); the top block stays put as MAXFILES grows; #0 is the
      lowest block — all predicted. Built: `strheap_chantab` reserves MAXFILES + 1
      blocks always; `sh_chan_addr` lays them bottom-up as the reference does —
      the 2 B-a-channel table, then #0 .. #MAXFILES (channel n = base +
      2·(MAXF+1) + 265·n); main's store ceiling asks for channel 0 (`xor a`, −1 B)
      and `VARPTR(#n)` lets #0 past the 52 range test (+3 B). Main page 1 44 → 42 B,
      sub page 0 151 → 143 B. After: `FRE(0)` −267 at every MAXFILES on both
      builds (nodisk now 4978 under the VG-8020, disk 343 under the CF-3300 —
      [`fcb0_after.out`](scratchpad/fcb0_after.out), [`fcb0_disk.out`](scratchpad/fcb0_disk.out)).
      txtceil-acceptance's fixture went red as RULED (stored=0: its 700 B under
      the floor no longer held the channel area) and was re-pinned +267 to the
      same geometry ([`fcb0_txtceil.out`](scratchpad/fcb0_txtceil.out)). Gate
      `fcb0-acceptance` ([`basic_probe_fcb0.py`](probes/basic/basic_probe_fcb0.py),
      [`fcb0_gate.out`](scratchpad/fcb0_gate.out)): v0 / stride / geom / fre, all
      relations (bases differ by machine) — MAXFILES clears variables on BOTH
      references, so the two-step rows print both readings. 🔪
      [`fcb0_knives.out`](scratchpad/fcb0_knives.out): K-FC1 (#0 refused) → v0
      stride; K-FC2 (no table offset) → geom; K-FC3 (no #0 reserved, the old
      guard) → nothing here, BY DESIGN — the reservation is absolute free memory;
      its first cut (`inc a` removed) left MAXFILES=0 to a 256-turn djnz
      ([`fcb0_knives_r1.out`](scratchpad/fcb0_knives_r1.out)).
      🔁 **THE FULL BATTERY'S RE-PINS (as ruled), each read before believed:**
      array-acceptance's `scalar.str.chain.oom` / `scalar.input.chain.oom`
      (zerobas-only edge fixtures: at `DIM Z(1813)` the DIM itself no longer fit,
      so the chain never ran out — [`fcb0_full_arrays.out`](scratchpad/fcb0_full_arrays.out))
      → `DIM Z(1780)`, 3 B LESS room than before, 146/146
      ([`fcb0_arrays_after.out`](scratchpad/fcb0_arrays_after.out)) — these two
      rows are K-FC3's absolute-memory witness. And lnblank-say-acceptance's
      `crf-oom*` rows **changed sides**: at `CLEAR 300,A+1000` both references keep
      ~148 B and store `99 REM Z`; zerobas, now counting #0 as they do, has room
      for nothing (the line refused, the PRINT aborted —
      [`fcb0_full_lnblank.out`](scratchpad/fcb0_full_lnblank.out)). Before, the
      missing 267 B hid zerobas's extra reserve and it had MORE room than the
      references. Pinned (`crf-oomctl`, `crf-oom`, `crf-oomlst`), `crf-oomsay`
      retired (now agrees); 208/208 ([`fcb0_lnblank_after.out`](scratchpad/fcb0_lnblank_after.out)).
      The reserve is D-DIMRESERVE's 256 B stack margin (noted there).
      ([`varptrch_run.out`](scratchpad/varptrch_run.out))
