- [ ] 🧱 **D-ROMSIZE — BRING THE ROM FOOTPRINT TOWARD THE REFERENCE: ~2.2x ITS BASIC
      TODAY (Joost, 2026-10-14)**
      🎚️ BUDGET — ROM size toward the reference; the space every later tier spends.
      🤖 **AUTONOMOUS** — in Joost's order, AFTER the tape fixes (D-TAPELOAD: external
      testers are waiting on those).
      📏 [`romsize_report.md`](scratchpad/romsize_report.md) (a read-only
      measurement of our own ROMs, symbols and sources; no reference byte read):
      75 KB of content in 112 KB of ROM images; BIOS side 0.9x the reference,
      BASIC side ~2.2x, a diskless machine ~1.8x, with disk ~1.6x. No padding,
      dead code or MSX2 code to reclaim; the size is DESIGN: the float core
      (~8.9 KB), disk-BASIC verbs + FAT engine outside the disk ROM (~8.7 KB),
      graphics (~7.3 KB), the heap string engine (~5.1 KB), ~3.5-4 KB of
      deliberate duplication between code areas that cannot call each other,
      and ~1.5 KB of inter-slot glue.
      🏗️ **JOOST, 2026-10-14:** *"I think we eventually want to address 1, 2, 3 and
      4"*, then *"go ahead with that order"*. ORDER:
      (1) **disk BASIC + FAT engine into the disk ROM**, where a real MSX keeps
          them (the existing eviction plan, disk/docs/spec-diskcode-eviction.md
          -- 🔧 CORRECTED 2026-10-14: not "step 13", which finished 2026-09-21;
          what is left is step 10's S10.C / S10.D / S10.E, BSAVE-to-disk,
          DSKI$ / DSKO$ and the step-14 gate); it also removes most of the
          duplication, and costs non-disk code no speed. The disk ROM has 3.8 KB
          free, so the move has to compact on the way in.
      📏 **STATE OF STEP (1), 2026-10-14 (a read-only brief of TODO, the spec,
      the syms and git log):** DONE -- steps 1-5, 9, 11, 12, 13; S10.0, S10.A,
      S10.B in three increments (c6d03ec8, ed213e5c, ef291642: main's write
      engine deleted). LEFT -- S10.C (the INPUT side; Joost 2026-10-09 "defer to
      later", taken up WITH S10.D/E), S10.D (RANDOM: GET / PUT -- the reference's
      GET/PUT hook contract is UNMEASURED; D-CHANHOOK covered OPEN/CLOSE, the
      byte cells and EOF/LOF only), S10.E (retire main's engine globals and the
      FAT tenant's channel half), BSAVE to disk (still the sub tenant's engine
      copy), DSKI$ / DSKO$ (main low `dsk_core` + the sub dirverb tenant; the
      disk-side hook is a presence test only), the step-14 gate. Still outside
      disk.rom (label spans, approximate): main page 1 files.asm 1728 B (about
      half device-generic), field.asm 622 B, fatio-body 111 B, fat.asm stubs
      41 B, fch_* ~90 B, autoexec 43 B (spans on 2026-10-14); main low dsk_core 68 B; sub ROM a second
      FAT engine copy (fat-prim-body 1839 B; disk.rom has its own 1719 B),
      randio-body 765 B, fatprim 456 B, the BLOAD / SEQIO / BSAVE / fcbname /
      dirverb chains ~1.2 KB. The spec's own estimate for step 10: ~800 B of main.
      The spec was last edited 2026-10-06; TODO is the current record.
      ➡️ **NEXT SLICE (autonomous under the 2026-09-17 standing ruling "every disk
      command's implementation belongs in disk.rom"): DSKI$ / DSKO$ into
      disk.rom**, the verb_run way: the hook becomes hk_dski / hk_dsko, main
      keeps the gate first (a diskless machine answers ERR 5 before the parse),
      the handler parses through call-backs and does the I/O with disk.rom's own
      read_sector / write path; main loses dsk_core's post-parse half,
      dirverb_op and chan_restore_st, sub loses the dirverb tenant. Expected
      ~40-60 B of main (low + page 1, one budget), ~55 B of sub page 1 (estimates of 2026-10-14); disk.rom
      pays ~60-80 B. Risks: DSKI$ is a FUNCTION inside the evaluator (the IX
      cursor and eval call-backs re-enter mid-expression); CALSLT returns DI (the
      D-LOADDI lesson); a disk-local sector cell, not FWR_DIRSEC; design for
      D-DSKIB's prompt to follow. Witness: dskio-acceptance, nodisk-acceptance,
      a new row from D-ALIASWCELL's write probe, a knife (the body returns
      without I/O). Then S10.D (measure the GET/PUT hook first), S10.C, S10.E.
      🔬 **PRICED BEFORE BUILDING (2026-10-14 night), and the brief's estimate is
      too high.** The parse calls the evaluator (main PAGE 1): a disk.rom handler
      cannot call the low-region `eval_byte_arg` / `eval_int16_checked` /
      `req_comma` directly (CALSLT to a page-0 target leaves disk.rom in page 1,
      and the evaluator's page-1 calls would land in it), so moving the parse
      needs a new page-1 bundle call-back in main (~20 B, estimated 2026-10-14). Two shapes:
      (a) the PARSE moves too: dsk_core becomes a ~19 B verb_run-like stub + the
          ~20 B bundle, against today's ~55 B -> ~15-20 B of main saved;
      (b) only the I/O moves: main keeps gate + parse and crosses the hook a
          second time with the selector in A and the sector in BC (chan_gate's
          cg_cross touches only DE / HL, and the crossing passes A / BC -- the
          hook direction is the same CALSLT that D-XSLOTABI measured), the
          handler does `ld hl,(DSKBUF_PTR)` + read_sector / fatprim_write_sector
          (both already in disk.rom) -> ~8 B of main (dirverb_op + the
          FWR_DIRSEC poke).
      Both delete the sub-ROM dirverb tenant (~55 B of sub page 1 on 2026-10-14; its p1 table
      slot must stay -- the table is append-only, point it at a stub) and end
      D-ALIASWCELL's FWR_DIRSEC hazard by construction. ⚠️ Neither is the 40-60 B
      the brief estimated; the step-10 work (S10.D first) is where main's bytes
      are.
      🏗️ **JOOST, 2026-10-15:** *"I think the remaining disk evictions make a lot of
      sense: 1. it matches reference better 2. it creates space for other fixes 3.
      it reduces the total non-disk rom size"* -> the evictions go FIRST (they
      also fund D-BASICINT's pins).
      ✅ **D-DSKLOCAL DONE (2026-10-15): DSKI$ / DSKO$'s sector I/O runs in disk.rom.**
      Shape (b): main's dsk_core keeps the parse, crosses the hook with A = 0
      before it (the diskless ERR 5) and AGAIN after it with A = the selector and
      BC = the sector; disk.rom's new `hk_dsk` moves the sector with its own
      read_sector / fatprim_write_sector. Deleted: main's dirverb_op, the sub-ROM
      dirverb tenant (sub/dirverb.asm; table row 13 now `ret/nop/nop` so 14..
      stay put), disk.rom's now-unused `hk_present` spike, dirverb_op from the
      call-back ABI; the status comes back in A from chan_restore_st (-3 B).
      Walls: main low 46 -> 52 B, main page 1 0 -> 8 B (+14 B; 🔮 ~12 B: HIT),
      sub page 1 91 -> 141 B (+50; 🔮 ~55: HIT). The FWR_DIRSEC aliasing
      (D-ALIASWCELL) is gone by construction: the sector crosses in BC.
      📏 dskio-acceptance 5/5, nodisk-acceptance PASS, unit tests green,
      D-ALIASWCELL's write probe re-run
      ([`dsklocal_aliaswrite.out`](scratchpad/dsklocal_aliaswrite.out)): DSKI$ /
      DSKO$ with an OUTPUT file open CLEAN, as before. 🔪
      [`dsklocal_knife.py`](scratchpad/dsklocal_knife.py) ->
      [`dsklocal_knife.out`](scratchpad/dsklocal_knife.out): K-DL1 (hk_dsk's read
      cut, byte-neutral) -> dir, boot AND dsko diverge (🔮 "dir, boot": partial
      MISS -- `dsko` reads the sector with DSKI$ before writing it back, so it
      witnesses the read too). Keyword pages DSKI$ / DSKO$ and
      docs/spec-basic-dskio.md updated; examples re-run.
      📏 **S10.D's FIRST MEASUREMENT (2026-10-15): GET / PUT CROSS H.DGET, PER
      RECORD** ([`getputhook_probe.py`](scratchpad/getputhook_probe.py) ->
      [`getputhook_run.out`](scratchpad/getputhook_run.out); the D-CHANHOOK
      entry counter on every published hook slot, CF-3300, 1 record against 40):
      GET and PUT enter the SAME three cells once per record -- `$FE80` H.DGET
      (CLAIMED by the reference's disk ROM: the dedicated GET/PUT hook), `$FE4E`
      H.GETP (claimed; per channel statement, as D-CHANHOOK found) and `$FE53`
      (a bare `ret` there). OPEN ... LEN= enters H.NULO $FE5D once and the
      OPEN/CLOSE set; FIELD enters no claimed cell. The per-sector notification
      $FFCF / $FFD4 moves +2 on GET, +18 on PUT. 🔮 "OPEN once at $FE5D": HIT;
      "FIELD none": HIT; "GET and PUT each one claimed cell per record": MISS --
      they share H.DGET, alongside H.GETP and the bare $FE53. zerobas claims none
      of $FE4E / $FE80.
      📏 **S10.D's SECOND MEASUREMENT (2026-10-15): WHAT H.DGET RECEIVES -- THE
      RECORD NUMBER IS NOT EVALUATED YET** ([`dget_probe.py`](scratchpad/dget_probe.py)
      -> [`dget_run.out`](scratchpad/dget_run.out), [`dget_run2.out`](scratchpad/dget_run2.out),
      [`dget_run3.out`](scratchpad/dget_run3.out); a breakpoint on the RAM hook
      cells $FE80 / $FE4E / $FE53 on the CF-3300, logging registers, 8 stack
      words, PTRFIL, VALTYP, DAC, the BASIC FCB header and the disk FCB it points
      at -- every read guarded to >= $8000, no ROM byte, no target followed).
      Per GET / PUT the order is $FE4E -> $FE53 -> $FE80. At $FE80:
      * **channel**: HL = PTRFIL = the channel's BASIC FCB (#1 $DD6E alone; with
        MAXFILES=2, #2 is $DD6E and #1 $DC65); A = 4 = its mode byte (FCB +0);
        FCB +1..+2 = the disk FCB (+14 = LEN: $10 / $64; +16 = the file size).
      * **GET vs PUT**: A is 4 for both; the third stack word is $0013 for GET and
        $8013 for PUT (BC differs too). The second stack word is the text pointer.
      * **record number**: NOT in a register, NOT in DAC (it still holds the `#n`
        channel number at entry; `,3` shows up there only after the hook) and NOT
        in the disk FCB (+33 = 0 for `GET#1,3`). **The disk ROM evaluates `,r`
        itself.** Bare `GET#1` after `GET#1,2`: the disk FCB's random-record field
        +33 already reads 2 (0-based NEXT record) -- D-RECAUTO is that field.
      * **errors**: record 0 ("Illegal function call"), 300 and -1 (both "Input past
        end" on a 40-record file) all ENTER $FE80 first -- the disk side raises
        them. An unopened `GET#1,1` is "File not OPEN" with NO hook entered: the
        channel-open check is main's.
      🔮 Scored: "no entry for record 0 (main checks first)": MISS; "A or a stack
      word separates GET / PUT": partial HIT (the stack word, not A); "record in
      +33 or DE": MISS; "PTRFIL = the FCB": HIT; "bare GET passes record 3":
      partial HIT (+33 holds it; nothing is passed). Apparatus misses, re-run:
      MAXFILES defaults to 1, so the first `#2` cases stopped at "Bad file
      number" before any hook, and a second OPEN of the same file is "File
      already open" -- the channel case uses B.DAT.
      ➡️ **S10.D design (the brief, revised by this measurement):** main keeps the
      `#n` parse, the "File not OPEN" / mode checks, PUT SPRITE's split and the
      crossing; **`hk_dget` in disk.rom parses `,r` itself** through a call-back
      (precedent: `fname_expr` in REQUIRED_DISK_CALLBACK), raises 5 / 55 there,
      and owns D-RECAUTO, the offset, D-STRADDLE's two-pass and the size update.
      OPEN RANDOM (H_FOPEN, a new selector) and CLOSE mode 4 (H_CHCLOSE) move in
      the same slice -- S10.B's lesson: the record path cannot move unless the
      state is disk-side from OPEN. Witnesses: geteject, putdir, loc, recauto,
      dout, the diskless 59, tests/test_rand_straddle.py re-pointed at disk.rom,
      and a knife. Estimated (unmeasured): main page 1 frees ~105-120 B plus the
      record parse; the sub-ROM randio tenant (~790 B) goes; disk.rom pays
      ~450-650 B across its interior holes (the largest is ~843 B, `make basic-reloc`
      2026-10-15 -- READ IT, never this number).
      ✅ **S10.D BUILT (2026-10-15): RANDOM OPEN / GET / PUT / CLOSE RUN IN
      disk.rom.** Drafted by a subagent in its own worktree while the gates ran,
      reviewed and integrated here. Main (basic/field.asm gp_common) keeps the
      `#n` parse, 5 / 59 / 52 / 58 / 61 and PUT SPRITE's split, then crosses
      `chan_gate_bare` to H_DGET with A = 0 GET / 1 PUT, C = the channel,
      FN_RESUME = the cursor; disk.rom's `hk_dget` parses `,r` (call-back
      `eval_int16_checked`), raises 5 for record 0, takes LOC + 1 bare
      (D-RECAUTO), makes the channel live (call-back `fch_select`, AFTER the
      evaluator: `GET #1,LOF(2)`), and runs the engine. OPEN RANDOM is H_FOPEN
      selector FOPEN_SEL_RAND -> `hk_frnd`; CLOSE mode 4 joins OUTPUT at
      H_CHCLOSE. Deleted: sub/randio.asm, basic/randio-body.inc,
      basic/fld-fill-body.inc, mul16sat, fdcc_rnd, GP_MODE / GP_CHAN / GP_OLDNSEC;
      fatprim rows 15-17 retired in place. Why the BARE gate with sector I/O is
      right here: basic/files.asm chan_gate_bare's new exception note.
      📏 Walls (`make basic-reloc`, 2026-10-15): main page 1 8 -> 139 B, sub page
      1 141 -> 928 B, disk.rom 3844 -> 3149 B free (26 runs), main low unchanged.
      🔮 Scored (2026-10-15) against the estimates above: page 1 "~105-120 B plus the parse"
      -> +131: HIT; sub "~790 B" -> +787: HIT; disk.rom "~450-650 B" -> 695: MISS
      (over). The corridors S10.D's engine landed in ($5FE8, $77BB, $7793, the
      $75A5 tail) have single-digit slack before their next pin, measured
      2026-10-15 -- 🔴 BUT THOSE PINS, AND THE ONES INSIDE THE 793 B RUN AT $4910,
      ARE MOSTLY NOT REAL. A read-only room brief (2026-10-15, after S10.D) found,
      and disk/fat.asm:378-391 confirms, that $4919 .. $4C25 are FOURTEEN BARE
      `ds` POSITION ASSERTS with no code between them -- the `jp k_49xx` veneers
      went with D-FATENG (06c7574c, 2026-09-18: "position assertions survive,
      code goes") and each `k_49xx` is a lone `ret` near $7835. The drafting
      subagent's "only ~59 B of the $4910 run is free" took them for pins and was
      WRONG: the run is bounded only by the internal `fdc_di_save` ($4C29,
      net-zero). The brief classes disk.rom's pins as truly fixed (the $4010
      table, $402D, the BDOS entries the stock kernel CALLs, the FDC window
      $7F80-$7FBF), our own ABI ($7F7C, main's `ld ix,$7F7C`), VESTIGIAL (`jp` to a
      lone `ret`, reached only through RET-filled $F2xx stubs: $41FD, $4558,
      $46C8, $4E4B, $4EDE, $5FE5, $607B, $75A5, $77B8, $782B) and net-zero layout.
      Pooled to the next truly fixed pin: ~1224 B before $4FB8 (estimate).
      ➡️ NEXT (the brief's ranking, unverified beyond the fat.asm read): (a) the
      byte-identical pin cleanup -- drop the dead asserts and vestigial veneers,
      teach tools/check_disk_walls.py the pin classes (it also counts the FDC
      window as free); ✅ the 13 dead asserts deleted 2026-10-15, disk.rom
      byte-identical (pins parsed 71 -> 58, free total unchanged: the tool had
      ALREADY priced the run at 793 B -- the drafter misread the source's
      "anchor canonical address" comments, not the tool). Left of (a): the
      vestigial veneers and orphan `ret`s (bytes move: bdos-acceptance), the
      tool's pin classes; (b) BSAVE-to-disk, measured on the CF-3300 first (~130 B of
      disk.rom for ~312 B of sub page 1, estimated) -- 📏 its hook MEASURED
      2026-10-15 ([`bsave_hook_probe.py`](scratchpad/bsave_hook_probe.py) ->
      [`bsave_hook_run.out`](scratchpad/bsave_hook_run.out), CF-3300, entry
      counts on every hook slot + a guarded register log): BSAVE enters $FE5D
      exactly once (HIT), never $FE71 (HIT), no claimed cell per byte (HIT), the
      exec / `,S` forms like the plain one (HIT); a bad drive is 62 BEFORE $FE5D,
      no disk is 70 after it (HIT); trailing junk (`...,&HD0FF 5`, `,SX`) is a
      Syntax error with NO file written -- the parse completes before the open
      (predicted the opposite: MISS; check zerobas's order in the slice); its
      claimed set is not OPEN-for-OUTPUT's (MISS). The 4 KB case wrote a 0-byte
      file on the CF-3300 ($D000-$DFFF meets the disk work area there): its
      per-sector prediction is NOT scored. 🔀 Order revised the same day: S10.C
      goes FIRST -- D-WSZERO (TIER 1) needs MAIN bytes and BSAVE frees sub only;
      (c) S10.C into the pooled
      corridor; (d) S10.E. Also found: the sub tenant `t_fia_walked` (148 B, sub
      page 1) has no sender since S10.B moved APPEND.
      📏 **S10.C STEP C0 MEASURED (2026-10-15)** ([`s10c_hook_probe.py`](scratchpad/s10c_hook_probe.py)
      -> [`s10c_hook_run.out`](scratchpad/s10c_hook_run.out), CF-3300, entry
      counts per hook slot, deltas against a quiet baseline): OPEN FOR INPUT
      enters $FE4E $FE58 $FE5D $FEB2 $FEB7 (and $FE62 at its CLOSE); a missing
      file raises 53 AFTER $FE5D (no $FE4E). `LINE INPUT#` over "AB" CR LF
      enters $FE8A 4x -- ONE PER BYTE READ; `INPUT#1,X` over " 1  2 " 5x plus
      $FEAD once (the numeric item); `INPUT$(1,#1)` $FE8A 1x plus $FE8F once.
      EOF / LOF / LOC SEPARATED: EOF -> $FEA3, LOF -> $FE9E, LOC -> $FE99, each
      with $FE94 once. 🔮 "$FE8A per byte": HIT; "EOF / LOF each one of $FE9E /
      $FEA3": HIT (and LOC has its own); "53 after a crossing": HIT; the
      INPUT$(256) scaling row was MY error -- INPUT$ takes at most 255, so it
      raised 5 and is NOT scored. The design brief (session scratchpad
      `s10c_brief_summary.md`) plans `hk_chin` on $FE8A with an op in A; the
      reference uses a cell per function instead ($FE8A byte, $FE8F INPUT$,
      $FEAD numeric item, $FEA3 / $FE9E / $FE99 EOF / LOF / LOC). ➡️ C1.
      ✅ **S10.C C1 BUILT (2026-10-15): DISK INPUT CHANNELS RUN IN disk.rom.**
      Drafted by a subagent in its own worktree (build + unit tests only; the
      shared machine files' mtimes checked unchanged after it), integrated here.
      OPEN FOR INPUT -> H_FOPEN selector FOPEN_SEL_INP ($49) -> hk_finp
      (disk/fat.asm; 53 parked through hk_fapp's tail for a missing file); the
      byte reader is ONE cell, H_CHIN = $FE8A, op in A (0 byte, 2 EOF, 4 numeric
      item) -> hk_chin over the FCB row, refilled 256 B at a time with RDBLK's
      k47b2_seek + k47b2_nextbyte; EOF answers without a seek when position =
      size (else an emptied drive made INPUT# at EOF say 70, not 55); every disk
      CLOSE crosses H_CHCLOSE (an INPUT arm that writes nothing). 🔀 DIVERGENCE
      KEPT: the reference enters a cell PER FUNCTION ($FE8F INPUT$, $FEAD numeric
      item, $FEA3 EOF); ours all enter $FE8A -- one 9 B main helper serves every
      site at 2 B each, and main bytes are D-WSZERO's budget. Deleted from main:
      the resident fatio-body (111 B), the fat_open / fat_read_file_sector shims,
      df_or_loaderr, seq_call, the dead ARL_GETBYTE seed; sub: SEQIO down to the
      tape EOF, fatprim row 19 retired, fat_restage_channel gone.
      📏 Walls (`make basic-reloc`, 2026-10-15): main page 1 20 -> 171 B, low
      48 -> 57 B, sub page 1 928 -> 1240 B, disk.rom 3149 -> 2857 B free. 🔮
      Brief's estimate "page 1 +~141 B": HIT (+151). PINS: 128 B removed ahead of
      $6CF3 and 23 B ahead of $73AC, all REFILLED in place (ex_for + cont_record
      + ctl_put at the first, ex_new / end_line_end + diskslot_test at the
      second, eval_addr into $3297's old 2 B pad, each original kept as the ELSE
      arm): `make pin-check` waste 6 -> 4 B, and its budget tightened to 4.
      ⏱ SPEED, MEASURED ([`seqin_speed_probe.py`](scratchpad/seqin_speed_probe.py):
      LINE INPUT # over a 16 400 B file, TIME in frames): CF-3300 1694, C1 1677
      ([`seqin_speed_c1.out`](scratchpad/seqin_speed_c1.out)), the build before
      it 960 ([`seqin_speed_head.out`](scratchpad/seqin_speed_head.out)) -- the
      256 B refill reads each sector twice, so C1 is 1.75x slower than zerobas was
      and now ON PAR with the reference (0.99x). 🔮 "slower than before, inside
      10x": HIT. Kept: faithful speed is the charter; a sector-reuse cache would
      need invalidation on every DSKIO, RANDOM record copy and LSET.
      Tests: tests/test_seqin.py (23 rows on disk.rom: CR / LF across a refill,
      Ctrl-Z, a numeric item straddling a refill, 70 left pending, no read at
      EOF); unit tests 66/66. Open, unmeasured: VARPTR(#n)'s +6 now moves during
      reads (the reference's layout -- fcbhdr will say); `INPUT #1,A$(LOF(2))`
      now answers 55 when #2 is not INPUT (it read #2's bytes before).
      📼 All 51 (pick_martos) against the previous run: SAME 12 -> 12, none lost.
      Two titles changed WHICH failure they show, both already failing and both
      in D-WSZERO's layout-sensitive class: Formula 1 Simulator flips between
      "line 40, graphics" and "the prompt" from build to build (m9 prompt, m10
      line 40, m11 prompt); Knight Tyme, A/B'd against HEAD's build (TRANS log,
      PC values only): identical early transitions, its stack at SP $E9F0-$EA12
      -- INSIDE zerobas's window -- then HEAD's build runs game code (8389 B
      from the VG-8020) and C1's waits in ROM (14223 B). Which bytes sit under a
      stack the game overwrites decides the failure; only D-WSZERO's empty
      window fixes the class.
      🐛 Two pre-existing engine bugs fixed on the way (found by the drafting
      subagent, witnessed by new tests/test_rand_straddle.py rows and a knife that
      restored the old code): `frnd_locate` divided the file sector by sectors-
      per-cluster on the LOW BYTE only, so a record 128 KB or more into a file
      walked the wrong cluster; and D-GETEOF skipped its bound for files over
      64 KB ("recno <= 255", false since D-PUTU32), so GET past the end of such a
      file gave spaces, not 55.
      ↔️ Behaviour change, the reference's order: `GET #1,0` / `GET #1,"A"` on a
      CLOSED channel now answer 59 (the channel check is main's, before any
      hook) where they answered 5 / 13.
      (2) **the string engine** -- measure first how the VG-8020 stores and
          reclaims strings (descriptor cost, when space comes back), then a
          smaller design that matches it.
          📏 **MEASURED 2026-10-21: THE VG-8020's COLLECTOR IS QUADRATIC, OURS IS
          ~FLAT.** [`gctime_probe.py`](scratchpad/gctime_probe.py) times one
          `FRE("")` (it compacts first) in TIME ticks over N live 8-byte strings
          ([`gctime_run.out`](scratchpad/gctime_run.out)):
          | N | VG-8020, garbage between | VG-8020, none | zerobas |
          |---|---|---|---|
          | 25 | 5 | 5 | 1-2 |
          | 50 | 15 | 15 | 1-2 |
          | 100 | 52 | 54 | 1-2 |
          | 200 | 196 | 196 | 1-2 |
          | 400 | 759 | 760 | 1-2 |
          ~4x per doubling -- the classic rescan-for-the-highest-live-string shape --
          and the SAME with no garbage at all, so the reference's cost is the scan,
          not the moves: 400 strings is ~15 s per compaction there. zerobas's sorted
          single pass (strheap_gc, 959 B of the sub ROM, 282 of them the sort) does
          it inside one 20 ms tick at every N; `FRE("")` answers 6400 on both.
          🔮 "VG-8020 g.400 / g.100 ~16" HIT (14.6); "zerobas grows 4-5x" UNSCORED
          (below the tick). ➡️ So a quadratic collector -- far smaller -- would still
          be ON PAR (TIER 5's bar); the sort is bytes spent beating the reference by
          ~400x at N=400. The bytes are SUB-ROM bytes (sub page 1 has ~3.9 KB free),
          not the binding main budget.
          🏗️ **JOOST, 2026-10-21:** *"I think eventually we may want to consider wether
          we can do without sub rom, and then we may have to start compromising things
          like the collector, but as long as we have the sub rom, there is no point?"*
          -> the fast collector STAYS. Bytes saved inside the sub ROM buy nothing while
          it has room; a reference-shaped collector (and packed floats) is a question
          for a future "no sub ROM" goal -- everything in main + disk.rom, 32 KB
          diskless / 48 KB with disk against ~67 KB of content (2026-10-20) -- which is
          not ruled. So steps (2)-(4) of this item wait for that goal wherever their
          bytes are sub-ROM bytes; what pays NOW is MAIN (page 1 + the low region).
      (3) **graphics** -- the same: measure, then design.
      (4) **the float core** -- 14 digits at one per byte (18 B per number) where
          the reference packs 8 B; the largest and riskiest (every numeric
          keyword and the speed tier): a written spec before any code.
      The cheap sub-ROM table wins in the report (packed constants -600..-700 B,
      keyword table -160..-320 B, KEY defaults -90 B) Joost "cares about less".
