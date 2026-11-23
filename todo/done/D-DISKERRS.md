- [x] ✅ **DISK BASIC'S ERROR SURFACE: 32 OF 126 CASES DIVERGE FROM THE CF-3300,
      AND FOUR OF THEM LOSE DATA SILENTLY (D-DISKERRS, found 2026-09-27 by T6
      batch 8; CLOSED 2026-10-07 -- every row fixed or split off, see the end).**
      🎚️ TIER 3 — common errors: a KILL, NAME or re-OPEN that the reference
      refuses goes through here, and reading past the end of a file returns
      nothing where the reference says Input past end.
      🤖 **AUTONOMOUS** — every row is measured; split off an item per shape
      as each is fixed.
      📏 [`scratchpad/t6enum_b8_zb.out`](../../scratchpad/t6enum_b8_zb.out): every case
      booted ALONE on both machines (a private disk image each). 94 agree; of
      the 32 that do not, two are `RUN 99` / `RUN 1,2`, which the reference
      cannot report to an ON ERROR handler (RUN disarms it). The rest,
      reference → zerobas:
      • **accepted where the reference refuses, and it can lose data:**
        ~~`KILL` of an OPEN file (64 → ok)~~, ~~`NAME` onto an EXISTING file (65 →
        ok)~~, ~~re-`OPEN` of a busy channel (54 → ok)~~ (D-OPENBUSY), ~~any `Q:` drive — OPEN,
        KILL, SAVE, RUN (62 → ok; `FILES "Q:*.*"` 62 → 53)~~.
        ✅ **D-DRVNAME (2026-09-28):** a drive past B: raises 62 now.
        `parse_disk_fcb` rejected it with `bl_load_error`, which PRINTS AND
        RETURNS from inside the parser, so the caller went on with drive A: and
        `OPEN "Q:F.TXT"` made the file on A:. It goes to `pdf_baddrive` (62,
        page 1, bound per build like D-FSPEC's `pdf_badname`; the BLOAD tenant
        keeps its unmeasured answer). [`scratchpad/drvname_probe.py`](../../scratchpad/drvname_probe.py):
        before [`drvname_run.out`](../../scratchpad/drvname_run.out), after
        [`drvname_after_run.out`](../../scratchpad/drvname_after_run.out) — C: .. H:
        and Q: agree at 62. ⚠️ **B: still differs, and it is not an error:**
        the CF-3300 treats B: as its PHANTOM drive and waits for a disk; zerobas
        uses A:. A prompt, not a code — noted, not chased.
        ✅ **D-NAMEEXIST (2026-09-28):** `hk_name` (disk.rom) looks the NEW name
        up first and refuses with 65, saving and restoring FWR_DIRSEC/DIROFF
        around that lookup because they are exactly where the rename stamps.
        [`scratchpad/nameexist_probe.py`](../../scratchpad/nameexist_probe.py) →
        [`nameexist_run.out`](../../scratchpad/nameexist_run.out): exists 65, the
        ordinary rename still reads `HI` from the new name with the old one
        gone, and not-found 53 — all agree. Its message had never been needed:
        `Unprintable error in 40` until sub/errmsg.asm gained ERR 65's row.
        Five batch-8 rows restored with them; **FILES and NAME reach T6 → 104**.
        🔮 Predicted 103 (FILES only) — NAME was wrongly assumed blocked by
        `NAME "A.TXT"` (53 there, 2 here): T6 needs ONE agreeing row per (form,
        code), and 53 already has one (`NAME "NOSUCH.TXT" AS …`).
        ✅ **D-KILLOPEN (2026-09-28):** `hk_kill` (disk.rom) refuses a file that
        is OPEN with 64 before deleting anything — every disk mode (OUTPUT,
        INPUT, APPEND, RANDOM), the live channel or a saved one, and through a
        wildcard, all measured against the CF-3300:
        [`scratchpad/killopen_probe.py`](../../scratchpad/killopen_probe.py) → before
        [`killopen_run.out`](../../scratchpad/killopen_run.out) /
        [`killopen_run2.out`](../../scratchpad/killopen_run2.out), after
        [`killopen_after_run.out`](../../scratchpad/killopen_after_run.out). Zero main
        bytes. Row `t8killdeletefile64`; **KILL reaches T6 → 105.**
        🔴 **THE FIRST BUILD REFUSED CORRECTLY AND STILL READ `ERR 0 ERL 0`**
        (D-ERRKEEP): with a file open, `chan_gate`'s restore re-stages the live
        channel after the hook, and every successful sector read writes
        `DISKOP_ERR = 0` — so the 64 was gone before `disk_error` read it, and
        `load_error` printed and carried on. NAME's 65 had the same hole
        (`n_open`: 65 there, ERR 0 here) and D-NAMEEXIST's probe could not see
        it, because no file was open in it. KILL and NAME now end in
        `hk_claim_status`, which on status 2 leaves NO channel live: chan_gate
        saved it before crossing, so the restore is deferred to the channel's
        next `fch_select` rather than skipped (`k_after`: write, refused, write,
        read back `ABCD` on both). Row `t8namerenameopen` guards it.
        🔮 Round 1 put three cases on `#2` without `MAXFILES=2`: all read 52 on
        BOTH machines — agreeing for the wrong reason; re-asked in round 2.
        ⚠️ **THE HOLE IS A CLASS, AND ONLY TWO HOOKS ARE OUT OF IT (D-ERRKEEP2).**
        Every other disk.rom hook that reports status 2 with a code in
        `DISKOP_ERR` — COPY, FILES, DSKF, the LOAD/SAVE/BSAVE handlers — loses that
        code the same way whenever a file is OPEN (a `Disk offline` or a write
        protect then prints as a load error and the program continues). Each ends
        in its own `ld (DISKOP_STATUS),a / scf / ret`; routing each through
        `hk_claim_status` is the disk-side fix, per hook, with a row that opens a
        file first. 🎚️ TIER 3. 🤖 AUTONOMOUS.
        ✅ **PARTLY DONE 2026-09-28:** `hk_claim_status` is keyed on a pending
        DISKOP_ERR now (every hook's encoding), and KILL, NAME, COPY and SAVE end
        in it (`wp_save` agrees at 68 with a file open). LOAD / MERGE / ASCII LOAD
        (`hk_dpload`, `hk_aopen`, `hk_agetb`) and DSKF still end on their own.
        🔬 **THEIR WITNESS IS NOT REACHABLE IN EMULATION (measured 2026-09-29).** The
        hole needs a READ failure inside the file being loaded while the open file's
        own sector still reads. openMSX reads every in-range sector of an intact
        image, and an ejected disk fails the channel's re-stage too. A crafted image
        with a first cluster PAST THE VOLUME ([`errkeep3_probe.py`](../../scratchpad/errkeep3_probe.py)
        → [`errkeep3_run.out`](../../scratchpad/errkeep3_run.out)) does not reach it either:
        zerobas's FAT walk ends the chain there and never reads (filed as D-BADCLUSTER).
        So these three stay on their own ending until a witness exists — routing them
        through `hk_claim_status` blind is a change no row could check.
        ✅ **D-NOASTO (2026-09-29): `NAME "A.TXT"` 53 → 2 AND `COPY "A.TXT"` 53 → 5 ARE
        ONE ORDER, AND BOTH AGREE NOW.** With no `AS` / `TO` the CF-3300 looks the
        SOURCE up first: missing is 53, present is the verb's own refusal — NAME 2,
        COPY 5 ([`noasto_run.out`](../../scratchpad/noasto_run.out); the present-file NAME
        case was unmeasured until then and predicted 2, hit). `hk_name` / `hk_copy`
        (disk.rom) now mount and look the source up on that path. 🔴 **THE DISK
        ROM'S TAIL WAS FULL:** the first build came out EMPTY — the region after
        `runtime.asm` had reached the ROM's end — so D-COPYWILD's `hkc_resolve` moved
        into the `$5602..$5FE4` fill (above `ds $5FE5 - $`, which shifts nothing),
        and `check_disk_walls` now reads the largest hole 2399 B there. **The disk
        ROM's free space is INTERIOR holes; anything new in the tail must displace
        into one.** After ([`noasto_after.out`](../../scratchpad/noasto_after.out)): the four
        cases and the wildcard COPY cases all agree. Guard rows `t8namenoasmiss` /
        `t8copynotomiss` (kwsweep, SUPPORTED); knife = HEAD's kernel.asm (disk ROM
        `cf40cbbb` → `6af04b37`, restored) turns both DIVERGENT
        ([`noasto_knife.out`](../../scratchpad/noasto_knife.out)).
      ✅ **D-OPENBUSY (2026-09-29): re-`OPEN` of a busy channel is 54 now.**
      `oo_parse_as_chan` — the "AS [#]n" clause every OPEN form shares (disk,
      LPT:/CRT:, CAS:) — checks `FCH_MODES[ch]` after the number is validated and
      before any file work, and fails through a new `oo_fail_e` tail (the
      `oo_fail_ifc` cleanup with the code in E). +16 B of main page 1, funded by
      D-DSKFLOCAL's 13 and D-DSKFRANGE's 4 (page 1 was 1 B after, 2026-09-29).
      Rows `t8openoutput54` (PROVES-T6:54) and the control `t8openreuse` (CLOSE,
      then the same channel opens again) SUPPORTED against the CF-3300
      ([`openbusy_kwsweep.out`](../../scratchpad/openbusy_kwsweep.out)); knife = HEAD's
      files.asm (main ROM `bd9e17c1` → `745ef2f8`, restored) turns the 54 row
      DIVERGENT — `File already open in 20` there, nothing here — while the
      control stays green ([`openbusy_knife.out`](../../scratchpad/openbusy_knife.out)).
      ~~➡️ **Still open from this line:** the SAME FILE on a second channel (54 on
      the CF-3300 even FOR INPUT, `o_same2` / `o_samein2`) — that needs a name
      compare against the open channels, which `hkk_open_check` already does in
      disk.rom; main has no bytes left to cross to it.~~
      ~~➡️ **OPEN's half is still open, and wider than filed:** round 2 found the
        CF-3300 also refuses a SECOND open of the same FILE on another channel
        with 54 (`o_same2`, and `o_samein2` even FOR INPUT); zerobas accepts
        both. OPEN is main code, and main was 3 B free on 2026-09-28.~~
      ✅ **D-OPENSAME (2026-09-29): the same file on a second channel is 54 now.**
      Unblocked by D-FCBSHAPE S0's 41 B of main page 1. Measured first, round 5 of
      `killopen_probe.py` ([`opensame_before.out`](../../scratchpad/opensame_before.out)):
      the CF-3300 refuses in EVERY mode — OUTPUT, INPUT, RANDOM, APPEND-then-INPUT
      — accepts a different file and the same file after CLOSE, and the refused
      OPEN leaves #1 writing (`Q1Q2 54`). All 7 predicted, all hit. OPEN now asks
      disk.rom before it claims the channel: a new `FOPEN_SEL_OCHK` ($4F) arm in
      `hk_dpload` runs `hkk_open_check` (the walk KILL/NAME/COPY already use — rule
      3), through the full gate because it reads directory sectors into the live
      channel's buffer. It shares OPEN-BUSY's `ld e,54` tail (`oo_fail_54`). Main
      page 1 41 → 29 B, disk.rom 6542 → 6522 B
      ([`opensame_walls.out`](../../scratchpad/opensame_walls.out)). After: 7/7 agree
      ([`opensame_after.out`](../../scratchpad/opensame_after.out)). Guard row
      `t8opensame54` (trapped, `[S 54 ]` on both; it restores MAXFILES=1 after its
      PRINT) SUPPORTED ([`opensame_kwsweep.out`](../../scratchpad/opensame_kwsweep.out));
      knife = HEAD's files.asm + kernel.asm (ROM hashes checked both ways) turns it
      DIVERGENT while `t8openreuse` stays green
      ([`opensame_knife.out`](../../scratchpad/opensame_knife.out)). Whole sweep SUPPORTED
      953 ([`opensame_kwsweep_full.out`](../../scratchpad/opensame_kwsweep_full.out)),
      kwtime OK 839, the new row 0.42× ([`opensame_kwtime.out`](../../scratchpad/opensame_kwtime.out)),
      knife BLIND unchanged ([`opensame_knife_all.out`](../../scratchpad/opensame_knife_all.out),
      [`opensame_knife_fn.out`](../../scratchpad/opensame_knife_fn.out)). 🔴 Its first cut said
      `ON ERROR GOTO 60` and BOTH machines read `Undefined line number` — SUPPORTED
      for the wrong reason; `as_stored` packs statements into ≤34-char lines, so
      the handler is line 40.
      ⚠️ Not asked: a WILDCARD name (`OPEN "A*.TXT"`, 56 on the CF-3300)
      while a matching file is open. Since D-OPENWILD (2026-10-07) ours refuses the
      wildcard BEFORE this check and answers 56; the CF-3300's order is unmeasured.
      ✅ **D-EOFMODE (2026-09-30): `EOF` on a channel opened the other way is 61 now**
      (OUTPUT, APPEND and RANDOM alike); batch 8 re-measured the same day leaves 12
      real rows, listed below ([`t6enum_b8_0930.out`](../../scratchpad/t6enum_b8_0930.out)).
      • **the common error paths:** `INPUT #` / `INPUT$(n,#)` past the end
        (55 → ok) — ➡️ **now its own TIER 1 item, D-SEQEOF (below): it is not
        just a missing code, zerobas reads the Ctrl-Z end marker as DATA and the
        textbook `IF EOF(1)` loop reads one line too many** — `EOF` / `INPUT #` /
        `PRINT #` on a channel opened the other way (61 / 52 → ok).
      • **wrong code:** ~~`OPEN "A*.TXT"` 56 → 53~~ (D-OPENWILD); `LEN="A"` 13 → 5; bare `LEN`
        2 → 5; ~~`NAME "A.TXT"` 53 → 2; `COPY "A.TXT"` 53 → 5~~ (D-NOASTO); `GET`/`PUT #1,"A"`
        13 → 5; `BLOAD "X.BIN",Q` 53 → ok.
      • **wrong LINE:** BSAVE's `"A"` faults report **line 30** instead of 20.
      • **extra arguments accepted:** `LOAD …,Q`, `RUN "A",5`, a fifth BSAVE
        argument (2 → ok); `INPUT$(0)` / `INPUT$(256)` (5 → ok).
      • **no reading at all:** `SAVE "X.BAS",B` and `SAVE "X.BAS",A,1` —
        nothing on zerobas's screen.
      Their kwsweep rows are NOT in the battery (each would be DIVERGENT, and
      in batch mode a wrong one poisons its neighbours); the denominator in
      `tools/kwerrset.py` still holds them, so OPEN, KILL, NAME, FILES, EOF,
      LOAD, SAVE, BSAVE, GET #, PUT #, INPUT # and INPUT$ stay T6-.
      📏 **RE-MEASURED 2026-10-06 — 15 DIVERGE, NOT 32**
      ([`t6enum_b8_zb_1006.out`](../../scratchpad/t6enum_b8_zb_1006.out), every case
      booted alone on both machines; the list above is 09-27's). 🎯 Predicted
      ~12 -- near, a miss by 3. Reference → ours:
      • ✅ **channel direction (2) -- FIXED THE SAME DAY as D-CHDIR (below):**
        `INPUT #` on an OUTPUT channel and `PRINT #` on an INPUT one 52 → no
        error (ours printed `load error` past the trap).
      • ✅ **wrong code (6) -- ALL FIXED:** ✅ `OPEN "A*.TXT"` 56 → 53 (D-OPENWILD,
        below); ✅ `OPEN … AS 1,2`
        2 → 53 (D-OPENEND, below -- a regression from S10.B increment 2 that
        kwsweep's gate could not fail on: D-KWDIVPIN); ✅ `LEN="A"` 13 → 5, bare
        `LEN` 2 → 5, `GET`/`PUT #1,"A"` 13 → 5 (D-RECLENERR, below).
      • **extra arguments accepted (5):** ✅ `LOAD "X.BAS",Q`, `RUN "A",5` 2 → ok
        (D-LOADTAIL, below); `BLOAD "X.BIN",Q` 53 → ok -- NOT a wrong code
        but a missing feature, filed as D-BLOADOFS (below); ✅ `INPUT$(0)` /
        `INPUT$(256)` 5 → ok (D-INPUTDN, below).
      • ✅ **no reading at all (2) -- FIXED THE SAME DAY as D-SAVETAIL (below):**
        `SAVE "X.BAS",B`, `SAVE "X.BAS",A,1` (2 on the CF-3300; ours `load error`).
      ✅ **CLOSED 2026-10-07 ON A WHOLE RE-MEASURE**
      ([`t6enum_b8_zb_1007.out`](../../scratchpad/t6enum_b8_zb_1007.out), every case
      booted alone): 4 of 116 diverge. `RUN 99` / `RUN 1,2` are the two the
      reference cannot report (RUN disarms ON ERROR); `BLOAD "X.BIN",Q` is a
      missing FEATURE, filed as D-BLOADOFS; and `A$=INPUT$("A")` 13 → 5 was a
      regression of D-INPUTDN's FIRST fix, caught HERE before any gate ran and
      fixed in the same commit (its gate row `con_str`). 🎯 Predicted 3 -- the
      fourth was mine.
