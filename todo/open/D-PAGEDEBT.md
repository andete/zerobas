- [ ] 📝 **STALE COMMENTS AND DOCS THE KEYWORD-PAGE AGENTS FOUND (D-PAGEDEBT, 2026-10-09).**
      🎚️ OTHER — docs: comments and prose that contradict a later measurement
      🤖 **AUTONOMOUS** — each is a reading; verify against the cited fix first.
      Comment-only changes leave the ROM hashes unchanged (check them).
      - `basic/str-engine.asm`: `str_fn_mid` "p<1 clamped" (now 5);
        `str_fn_space` / `str_fn_string` "clamped to STRMAX" (D-F2-2, D-SPCLAMP);
        `str_fn_string` empty fill "function error" (Syntax error, D-STRINGEMPTY);
        `ev_f_instr` p<1 "ev_f_err" (now `eval_pos_arg`).
      - `basic/screen.asm` header + `ex_key`: KEY strings / KEY LIST "unsupported",
        SCREEN click "no effect" (D-KEYSTR, D-SCRCLICK). `basic/print.asm` header:
        strings not printable. `basic/printusing.asm`: `$$` "filed, unpriced"
        (D-PUDOLLAR). `basic/graphics.asm` above `spr_extra_arg`: click / baud
        "stay ignored"; `ex_sprite` (~1063): SPRITE ON/OFF/STOP "no-ops" (T4).
      - `basic/sound.asm`: "No DI/EI guard" (ex_sound uses di/ei); BEEP's mixer
        "restored" vs basic_probe_beep.py "reset to default" — MEASURE which.
      - `basic/input.asm` header: lowercase redo wording (D-MSGEXACT).
        `basic/cload.asm`: a `CAS:` name "accepted and ignored". `basic/files.asm`
        channel Divergences block (50 B a channel, no numeric INPUT# / APPEND,
        `load_error`) and `ex_merge` "Direct statement in file" (code: stmt_error).
        `basic/deffn.asm`: the only DEF-time check (vs D-DEFFNPARAM).
        `basic/poke.asm`: "writes the low byte" (D-RAWVAL). `basic/interp.asm`
        above `ex_error`: disk codes "unprintable" (D-MSGSUB). `basic/expr.asm`
        `ev_ff_loc`: "unmeasured for LOC" (t6enum_b8 measured it).
        `disk/kernel.asm` `hk_dskf` header: the deleted `fat_count_free` stub.
      - `tools/kwforms.py` notes: DEFSNG "single is the default" (it is double,
        spec-basic-float-core §11.1 — also kwsweep.py ~2833); DATA "trimmed at the
        edges" (trailing spaces are kept, readvar b.trailsp); USR "only the
        default has a row"; VARPTR FCB header "unwritten" (D-FCBHDR); LOCATE
        cursor "IGNORED" (D-LOCCSR); KEY display "NO ROW"; SCREEN click "no cell".
        `probes/basic/basic_probe_kwsweep.py`: "WAIT has no row" (~1351), "SCREEN
        and KEY are not here yet", the `close` row's reopen note (now 54).
        `basic_probe_nodisk.py` docstring (pre-fix state); `basic_probe_str_fn.py`
        STRMAX=64; `basic_probe_fldwidth.py` "File not open" (the reference prints
        `File not OPEN`); `basic_probe_editverb.py` column 2 vs 1 (check).
      - docs: `spec-basic-lvsites.md` "Nothing implemented" (D-LVFIX shipped);
        `spec-basic-string-functions.md` §2 STRMAX clamp; `spec-basic-lrvar.md`
        LSET on the VG-8020 "Syntax error" (it is 5); `spec-basic-input.md`
        integer-only + lowercase; `spec-basic-audio-play.md` §2.2 + `spec-basic-
        playop.md` §6 (X and PLAY(n) shipped); `spec-traps-t2-strig.md` and
        `spec-basic-width-domain.md` "awaiting sign-off"; `spec-basic-malformed-
        call-syntax-error.md` "Status: CONTRACT" and lowercase `syntax error`
        (also `spec-basic-float-core.md` §10.2, `spec-basic-arrays-slice2-
        erase.md`); `spec-basic-math-pack.md` §9.4 "half-up" (CINT truncates, §9.1);
        `spec-basic-graphics-g3.md` §3.4/§4.4/§11.7 + g6 §5 "clip by masking"
        (D-SPOKELINE / D-DRAWCLAMP clamp); g4 §3.4/§11.5 negative radius "hangs"
        (D-CIRCNEGR: completes); g5 §3 "G5-align" (D-NTFLOOD); `editverb-msx1-
        characterization.md` §1.2/§7 LPRINT/LPOS/LFILES "missing"; `spec-basic-
        error-handling.md` ~437 "unprintable" (D-MSGSUB); `spec-basic-mksd.md`
        "the day before" (both 2026-09-03).
      - TODO.md: D-MKIREUSE "where CINT rounds" (CINT truncates); D-FCBSHAPE's tag
        "306 B a channel" (267 since S1+S2); D-FORFLOAT "FOR A%=1.7 starts at 2"
        vs `forfloat_after_run.out` `intinit` (1, 2, 3) — MEASURE; D-RUNLINE's
        TODO-done heading "restarts from the top" (its case was Syntax error);
        the Makefile's diskfull-acceptance comment (12 vs 24, now 12 both).
      - Contradictions that need a MEASUREMENT, not an edit: `EXP(-1E30)` (ngram14
        §5 says 6 on both; D-EXPBAND says 0 below 1E-129); `COS` beyond ~1.57E14
        (VG-8020 0, zerobas 1 — a value difference with no item); CSAVE inside a
        program (D-KWTAPE2 "ends it" vs tapetail `csaveok`); FN's `d.n4` error 7
        (2026-09-09, before D-SPMERGE); `FOR I=1 TO 0` (kwforms says the body runs
        once; unmeasured); `DSKF(0)` on a fresh copy of `disk/test720.dsk` reads
        706 on both machines today (`kwdoc_dskf.out`) where kwsweep's `dskf` note
        and D-KWDISK / D-DSKFDRV say 707 — which image, or which count, differs?
      - `basic/field.asm` header (~37-42, ~74-76): record lengths "power of two",
        records "1..255" — both gone (D-RECLENFIX, D-PUTU32). And its GET
        end-of-file test is skipped for a file over 64 KB on the strength of
        that 1..255 cap (~843): a GET past the end of such a file may read
        blanks instead of 55 — MEASURE (needs a > 64 KB random file).
      - Found by the CONCEPT pages (2026-10-09), each a reading to verify:
        `docs/spec-basic-screditor.md` §6 (CHSNS poll vs CHGET in §3 /
        `basic/repl.asm`; "ZB shares the typed row", changed by D-ZBCRLF);
        `docs/echo-delivery-characterization.md` §1 (39 columns, ZB on the typed
        row); `sub/detok.asm` header (512-B DETOKBUF, 96-char limit — now a 96-B
        window and 254); `basic/detok.inc` `dt_oct` ("&O never produced");
        `basic/tokenise.inc` ("NONE OF THE FOUR HAS A stmt_table ROW");
        `basic/sysvars.inc` (the `$B700..$BFFF` buffer map; HIMEM "record-only";
        FRETOP before "All 29"; `H_CHCLOSE ; FILES handler`);
        `basic/keytrap.asm:37` ("TRAPS_T3 = 0 … never run" — it is 1);
        `basic/traps.asm` header (`check_traps` "in a sub-ROM tenant" — resident);
        `sub/errmsg.asm` header ("codes zerobas never RAISES");
        `docs/chancost-cf3300-characterization.md` §10 / headline and
        `docs/spec-basic-filechan-alloc.md:106` ("52 not trappable" — a confound;
        "50 B a channel"); `spec-traps-t1-stop-reslice.md` §1 (INTERVAL "MSX2");
        `sub/strheap.asm` header (heap/array collision before D-CLP, DETOKBUF sort
        buffer before D-DETOKBUF S2, "GC only in heap_alloc / ary_alloc");
        Makefile `txtceil-acceptance` comment ("12 + 50*MAXFILES");
        `docs/spec-basic-addr29.md` §3/§5; `spec-basic-string-engine.md`
        (STRMAX=64); `spec-basic-clearpool.md` (TEMPTOP); `basic/vars.asm`
        header ("integer-only"); `sub/arrays.asm` header (element size, base,
        column-major vs spec-basic-arrays §2.1 row-major); basic/PROVENANCE.md
        `a=&o177777` → 65535 vs the negative-above-&H8000 rule;
        `basic/main.asm` header (`$2812` vs BASIC_ORG `$2765`); `basic/screen.asm`
        header ("owns no VDP programming", a missing
        docs/msx1-basic-bios-coupling.md); `disk/docs/expansion-protocol.md` §2
        (`$FDF9` HSETS vs H.NAME); `disk/kernel.asm` / `disk/init.asm` ("seven
        conversion hooks", ~21 now); g7 §5 vs g8 (RG1SAV high bits);
        `disk/docs/file-channel-protocol.md` §3 (FCB "carrying the 8.3 name");
        `basic/cload.asm` `do_tape_prog` ("accept either format", false since
        D-CASTYPE); `basic/casmatch-body.inc` (end of tape → `load_error`, now 19);
        `tape/docs/spec-cassette.md` Maturity note; `disk/docs/spec-diskbasic-
        verbs.md` + `diskbasic-verb-coverage.md` §1/F7 (LOC, DSKI$, DSKO$, NAME
        guard, numeric INPUT# all shipped); `spec-diskrom-kernel.md` §6.2
        (GDATE / SDATE before D-DOSDATE); `tier2-bdos-coverage.md` (WRSEQ, counts,
        LSTOUT row vs text); `tier2-STATE.md` (last updated 07-04);
        `autoexec-bas-spec.md` ("DRAFT"); TODO's 2-Tier2-a/b/c still "BLOCKED";
        `disk/disk.asm` / `disk/init.asm` headers (BASIC via `bdos_entry`).
        The OPEN keyword page vs TODO on the same-file-two-spellings item's owner.
