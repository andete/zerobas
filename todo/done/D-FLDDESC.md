- [x] 🧱 **D-FLDDESC — FIELD AS THE REFERENCE DOES IT: NO TABLE, THE VARIABLE'S OWN
      DESCRIPTOR POINTS INTO THE CHANNEL'S RECORD AT BLOCK+9 (filed 2026-10-17)** —
      ✅ **BUILT 2026-10-17: main page 1 168 -> 379 B free, sub page 0 29 -> 177 B,
      sub page 1 1104 -> 1165 B, disk.rom 2857 -> 2865 B (`make basic-reloc`).**
      🎚️ BUDGET — main page 1 (D-ROMSIZE step 1) — and TIER 5 (every string-variable
      read on a disk machine stops paying fld_lookup).
      🤖 **AUTONOMOUS** — 🏗️ Joost 2026-10-17: disk.rom owns the FIELD table (diskless
      it is ERR 5), and *"if reference has a location inside the non-disk region it
      uses, we should also use that"*.
      📏 **MEASURED FIRST** ([`fieldram_probe.py`](scratchpad/fieldram_probe.py) ->
      [`fieldram_run.out`](scratchpad/fieldram_run.out); BASIC VARPTR / PEEK / FRE
      only; VARPTR is signed, so the readings show +65536): after
      `FIELD #1,2 AS A$,3 AS B$` on the CF-3300, A$'s descriptor is [2][VARPTR(#1)+9]
      and B$'s [3][VARPTR(#1)+11]; FIELD spends 0 B of FRE(0) and FRE(""); LSET keeps
      the pointer and writes the bytes there; a plain `A$="Z"` moves it to string
      space. So the reference keeps NO table: the location is the variable itself
      plus the channel's record buffer. zerobas leaves the descriptor empty (length
      0) and keeps FLD_TAB. 🔮 "0 B, into the channel block, 2 B apart": HIT.
      🧭 **DESIGN (nothing in the way, checked 2026-10-17):** the string GC already
      skips a descriptor whose pointer is outside the heap (sub/strheap.asm
      `sg_inrange`; D-LITREF's program-text pointers live with it), and a
      non-FIELDed LSET / RSET already writes in place into the target's own body at
      its own length (docs/spec-basic-lrvar.md) -- which IS a fielded store once the
      descriptor points at the record. So: FIELD writes [w][block+9+offset] into each
      variable; LSET / RSET keep only their non-FIELDed arm; fld_lookup leaves
      str_eval's variable path; FLD_TAB, FLD_DESC, fld_find / fld_add / fld_init and
      the sub FLDLOOK tenant go. ⛓️ PREREQUISITE: RANDOM's record must live at
      block+9 (today it travels through FSECTOR_BUF via t_fch_load / t_fch_save:
      S10.E's next item), so GET / PUT and FIELD agree on one buffer.
      ⚠️ Also seen: the channel block sits 265 B below HIMEM on the CF-3300 and 665 B
      on zerobas (MAXFILES=1) -- a TIER-4 RAM reading for the FCH block layout, not
      this item's.
      📏 **ROUND 2, THE ROWS THE TWO MODELS READ DIFFERENTLY** ([`flddesc_probe.py`](scratchpad/flddesc_probe.py)
      -> [`flddesc_run.out`](scratchpad/flddesc_run.out), LEN=8, A$ 2 B and B$ 3 B
      fielded): the CF-3300 reads r1 `XY  Z` (LSET / RSET), r2 `QY` (MID$ writes the
      record), r3 `XY` (GET re-reads it), r4 `XYMN` (a copy taken before LSET is its
      own), r5 `XYMN` and r6 `XYXY` (SWAP exchanges the DESCRIPTORS: C$ is fielded
      after it), r7 `  Z` (the buffer survives CLOSE), r8 `  Z` (and a re-OPEN does NOT
      clear it), r9 `  Z`. 🔮 r1-r7 and r9 as predicted: HIT; r8 was unpredicted.
      🔴 **zerobas stops at r2 with `Illegal function call in 60`**: MID$ on a fielded
      variable finds its own (empty) descriptor -- a real divergence today, and the
      descriptor model removes it by construction. These nine rows are the slice's
      gate. ⚠️ r8 also says hk_frnd's space-fill of the record at OPEN is not the
      reference's on a RE-open; what a FRESH block holds is unmeasured.
      📏 **ROUND 3, A FRESH BLOCK** (`FLDDESC_PROG=fresh` ->
      [`fldfresh_run.out`](scratchpad/fldfresh_run.out)): the CF-3300 NEVER fills the
      record -- #1 reads 159 146 and #2 255 255 right after MAXFILES (leftover RAM),
      and after CLEAR + MAXFILES an old `QQ` is still there (81 81). 🔮 "spaces": MISS.
      So hk_frnd's OPEN fill went too; f1 / f2 are leftover RAM on both machines and
      not comparable, f3 is.
      ✅ **THE SLICE.** Drafted by a subagent in its own worktree (build + unit tests
      only), integrated and measured here:
      - RANDOM's record LIVES at block+9: disk.rom's frnd_calc / GET's end fill use
        `rnd_rec` (the row's cached block); sub's t_fch_load keeps only the LOF / LOC
        mirror, t_fch_save is gone (row 21 is `fp_stash_ok`, rows keep their numbers).
      - FIELD writes `[w][block+9+offset]` into the target (scalar or element,
        `tgt_store_desc`), ERR 50 checked first; FLD_TAB, FLD_DESC, fld_find / fld_add
        / fld_init / fld_init_g / fld_clear_chan / fld_lookup, the sub page-0 FLDLOOK
        tenant (row 12 retired) and ERASE's aer_fldfix are gone; a string-variable
        read no longer consults any table.
      - LSET / RSET keep only the in-place arm; hk_lrset is its three call-backs.
      - hk_frnd no longer blanks the record (round 3).
      - Pins: the freed bytes ahead of $6CF3 / $72D4 / $73AC were refilled exactly by
        moved code (lrset_finish / lrset_store, GET / PUT's head, ex_delete, exf_comma,
        derive_directf, dir_line / run_kw, relink, trace_line); 6/6, waste 4 of 4;
        `make switch-build-check` 7/7.
      Witness: [`flddesc_run_after.out`](scratchpad/flddesc_run_after.out) r1-r9 SAME
      on both machines (r2 was `Illegal function call`);
      [`fieldram_run_after.out`](scratchpad/fieldram_run_after.out) [a] / [b] / [l]
      byte-identical offsets and lengths; [`fldfresh_run_after.out`](scratchpad/fldfresh_run_after.out)
      f3 SAME. 🔮 "r1-r7 + r9 match, r8 differs while the fill stays": HIT; after
      the fill went, r8 SAME. Knife connectedness unchanged: HIT.
      🏗️ **Joost 2026-10-17 reversed his 2026-09-27 "keep ours"** on a fielded variable
      read after its channel is closed and reused: "Match the reference" -- which the
      descriptor does for free (FIELD.md's last stated difference is closed).
      ➡️ RESIDUALS (unmeasured on the reference; none is a regression of a gated row):
      (a) `LSET A$=A$` on a fielded A$ -- the source shares the target's bytes and
      is padded before it is copied; (b) whether ERR 50 leaves the overflowing
      variable bound (ours: raised before the store); ~~(c) the row-21 crossing in
      fch_save_active is now a no-op that main still pays for~~ -- ✅ gone with S10.E
      (2026-10-19); (d) scratchpad/wszero_s9_knife.py's K-WS22 / K-WS23 cut
      code that is gone.
