- [ ] **D-DSKIOCYL — DSKIO ON A CYLINDER PAST THE LAST ANSWERS 8 (RECORD NOT FOUND); THE CF-3300 ANSWERS 2 (NOT READY)**
      🎚️ TIER 6 — every error (a sector past the media's end; filed 2026-11-17, D-DISKCONTRACT gap 2).
      🤖 **AUTONOMOUS** — PHYDIO / DSKIO with sector 1440, 1500 or 2000 on the 720 KB disk; sector $FFFF reads fine on
      BOTH (an 8-bit cylinder wrapping in range, read as a result). Our driver maps the FDC's status faithfully; the
      fix is a cylinder range check in DSKIO (~5 B) -- the disk ROM has 0 B free, so a carve first (Joost: the disk ROM
      stays in its allotted space). Pinned in phydioerr-acceptance (rows read_far / read_1440 / read_1500), and since
      D-DISKVE in bdos-acceptance's BDOSXE allowlist (RDABS 1440's C, ours 8). (1) FORMAT -- its body is the DISK ROM's (H.FORM): only the main-BIOS
      side is in focus.

      - [x] **Two power-on work-area defaults differ: CLIKSW and CLMLST** -- 🎚️ TIER 3 —
            at the prompt after boot the VG-8020 has CLIKSW ($F3DB) = 1 (key click on) and
            CLMLST ($F3B2) = 14; zerobas 0 and 0 ([`biosmode_run2.out`](scratchpad/biosmode_run2.out), "already apart" on every
            row). Neither is an entry's answer -- BASIC's / the boot's initial state. ➡️ Which
            of our cold-start paths owns each cell, and what the CF-3300 holds.
            ✅ **FIXED (2026-11-13, D-CLMLST):** both references hold CLMLST 14 / CLIKSW 1 at
            power-on, and SCREEN / WIDTH recompute CLMLST from LINLEN (32 -> 14, 20 -> 0,
            37 / 40 -> 14) while COLOR keeps a POKEd value ([`clmlst_probe1.out`](scratchpad/clmlst_probe1.out)); INITXT
            itself does not touch it ([`clmlst_probe2.out`](scratchpad/clmlst_probe2.out)) -- so BASIC, not the BIOS. zerobas:
            boot_wa (cold start, before the cartridge scan) and scr_call (after SCREEN / WIDTH
            only), basic/catalias.asm; page 1 gained 4 B on 2026-11-13 (two call sites shortened). After:
            identical to the VG-8020 ([`clmlst_probe3.out`](scratchpad/clmlst_probe3.out); 🔮 HIT); **`make clmlst-acceptance`**
            ([`basic_probe_clmlst.py`](probes/basic/basic_probe_clmlst.py), [`clmlst_gate.out`](scratchpad/clmlst_gate.out)). The key click SOUND is not implemented
            (C-BIOS has no click code either); CLIKSW now reads as the references'.
      📏 **The VRAM-answering entries (2026-11-13):** **`make biosvram-acceptance`**
      ([`basic_probe_biosvram.py`](probes/basic/basic_probe_biosvram.py)): FILVRM, WRTVRM, LDIRVM, LDIRMV, CLRSPR, CHGCLR in SCREEN 1,
      each VRAM window seeded and read back with OUR OWN port code (never an entry under test) --
      **6 / 6 SAME** ([`biosvram_run1.out`](scratchpad/biosvram_run1.out), [`biosvram_run2.out`](scratchpad/biosvram_run2.out): the LDIRVM row's first run POKEd 258, a
      probe fault). Tape corpus after D-CLMLST: SAME 9 / NEAR 11 / RUNS? 22 / **RESET 0** --
      Demonia RESET -> RUNS?, its timing flip again ([`tapecorpus_clmlst.out`](scratchpad/tapecorpus_clmlst.out); 🔮 "no class
      worse": HIT).
      📏 **The text-output entries (2026-11-13):** **`make biostext-acceptance`**
      ([`basic_probe_biostext.py`](probes/basic/basic_probe_biostext.py), biosmode's before / after method): CHPUT with 'A' and CR / LF /
      BS / TAB / HOME / CLS / cursor-right, POSIT, CLS, ERAFNK, DSPFNK, KILBUF over the screen
      block, PUTPNT / GETPNT and LINTTB -- **13 / 13 SAME** ([`biostext_run2.out`](scratchpad/biostext_run2.out)). LINTTB is read as
      published (zero = continued row): the VG-8020 keeps $18, $17 .. and ERAFNK writes $AF to the
      last row where zerobas keeps $01 -- same meaning, a first cut compared the values
      ([`biostext_run1.out`](scratchpad/biostext_run1.out)). Tape corpus after D-GRPBASE: SAME 9 / NEAR 11 / RUNS? 21 / RESET 1
      -- Elite SAME -> RUNS?, the timing / phase flip TODO's corpus table already names it in
      ([`tapecorpus_grpbase.out`](scratchpad/tapecorpus_grpbase.out); 🔮 "no class worse": MISS by that one).

      - [x] ISCNTC / CKCNTC ($00BA / $00BD, one body): a STOP / CTRL-STOP pending -- the row
            biosregs has only reads the idle state.
            📏 **MEASURED 2026-11-12 ([`iscntc_probe.py`](scratchpad/iscntc_probe.py) -> [`iscntc_run3.out`](scratchpad/iscntc_run3.out)):** the stub
            sets INTFLG ($FC9B) itself right before the call, records it after into $D10A and
            clears it -- so a printed row means the entry RETURNED. VG-8020, both entries
            alike: INTFLG 0 -> returns, registers kept; **3 (CTRL-STOP) -> `Break in 30`, never
            returns**; **4 (STOP) -> no output in 20 s** (the published "wait for the next
            STOP"). zerobas: returns in all three, INTFLG untouched -- **4 DIVERGE**.
            🔴 Two probe faults first, both kept as cuts in the probe: INTFLG POKEd from BASIC
            broke at the POKE's own line (the VG's interpreter checks it BETWEEN statements,
            [`iscntc_run.out`](scratchpad/iscntc_run.out)), and with INTFLG still set after the call the interpreter broke
            at the USR line whatever the entry did ([`iscntc_run2.out`](scratchpad/iscntc_run2.out)).
            ➡️ **THE FIX NEEDS (each measured first):** (a) does the VG's keyboard ISR set INTFLG
            3 / 4 on CTRL-STOP / STOP, and does ours (zerobas's BASIC reads the key itself, in
            rp_break -- not INTFLG)? (b) the break through BASIC's own path, as inp_break does
            (SP := SAVSTK, do_break with SAVTXT); (c) the STOP wait: what ends it (a second
            STOP, CTRL-STOP -> break) and INTFLG after; (d) BASROM ($FBB1) != 0 -- the published
            "no break in a protected ROM BASIC". Room: C-BIOS's stub body ($15D2) is ~11 B.
            ✅ **FIXED 2026-11-12 -- `make iscntc-acceptance` 17/17 SAME.** Two more inputs measured
            first: the keyboard interrupt LATCHES INTFLG on both machines (4 STOP / 3 CTRL-STOP,
            still set ten frames after the release -- [`intflg_isr_probe.py`](scratchpad/intflg_isr_probe.py) -> [`intflg_isr_run6.out`](scratchpad/intflg_isr_run6.out); 🔮 "ours
            stays 0" MISSED: C-BIOS's ISR sets it too), and the VG-8020 does NOT end the STOP wait
            on one long press ([`iscntc_run8.out`](scratchpad/iscntc_run8.out)); BASROM != 0 returns at once with A = BASROM
            ([`iscntc_run6.out`](scratchpad/iscntc_run6.out)); A on return is INTFLG ([`iscntc_run5.out`](scratchpad/iscntc_run5.out) -- the idle path diverged too,
            hidden by biosregs' A = 0). 🔴 **And BASIC left the latch set:** `ON STOP GOSUB` + a
            press, then PEEK(&HFC9B) -- VG 0, zerobas 3 ([`intflg_left_run.out`](scratchpad/intflg_left_run.out)); a later ISCNTC would
            have broken on a press BASIC had already handled. Built: bios_iscntc (basic/biosfnk.asm,
            page 0: BASROM, INTFLG, return) and isc_slow (basic/input.asm, beside inp_break: 3 ->
            the break through inp_break, 4 -> key up by NEWKEY row 7, then INTFLG cleared and
            waited on); the jump table's $00BA / $00BD point there (basic/islands.asm,
            PATCH_RANGES); rp_break clears INTFLG. Gate: probes/basic/basic_probe_iscntc.py (the
            16 rows + `basic_left`). Knives: K1 (the front's `jp isc_slow` -> `ret`) ->
            iscntc_f3 / f4_stop RED ([`ISC_k1.out`](scratchpad/ISC_k1.out)); K2 (rp_break's clear -> `nop`s) -> basic_left
            RED ([`ISC_k2.out`](scratchpad/ISC_k2.out)). stub_scan: 9 -> 7. ⚠️ Not measured: INTFLG values other than 0 / 3 /
            4 (returned as read); a STOP pressed while BASIC runs (the run loop's pause) -- does
            the VG-8020 leave INTFLG 0 after it too?
      - [x] FNKSB ($00C9): the function-key line shown or erased by CNSDFG -- a row that changes
            the cell behind its back.
            ✅ **FIXED 2026-11-12.** Measured ([`fnksb_probe.py`](scratchpad/fnksb_probe.py) -> [`fnksb_run.out`](scratchpad/fnksb_run.out) .. [`fnksb_run4.out`](scratchpad/fnksb_run4.out)): KEY OFF +
            CNSDFG := $FF -> the VG-8020 PAINTS the key row (a KILBUF call in its place leaves it
            blank, so FNKSB did it); KEY ON + CNSDFG := 0 -> nothing (🔮 "erases": MISSED), A = 0
            (CNSDFG's value). With the flag set its registers are DSPFNK's exactly (DE $FC40, BC 0,
            A 0 -- biossweep_fnk.out's dsp0). Built: bios_fnksb (basic/biosfnk.asm, page 0):
            CNSDFG != 0 -> bios_dspfnk; $00C9 points there. biosregs-acceptance `fnksb_off_ff` /
            `fnksb_on_00`; knife K3 (the `jr bios_dspfnk` -> `ret`) -> fnksb_off_ff RED
            ([`FNK_k3.out`](scratchpad/FNK_k3.out)). stub_scan 7 -> 6.
            🎚️ **A CHOICE, RECORDED:** DSPFNK / ERAFNK / FNKSB's EXIT REGISTERS are not matched -- the
            published contract says "Registers: all", and the VG-8020's leftovers (text-mode DSPFNK
            DE $FC40 / BC 0 / A 0, ERAFNK DE $0399 / A $28) are not a contract a program can rely
            on; matching them costs page-0 bytes. The graphics-mode exits (DE / BC kept, A =
            SCRMOD) already match. 🔴 Found on the way: biosregs' `dsp0` / `era0` rows end in
            `END` before the register line, so they never compared registers -- the readout was
            blind to them; this records that the gap is deliberate now, not unseen.
      - [x] STRTMS ($0099): start PLAY's queued music (with PUTQ, LFTQ: PLAY's queues).
            🔭 **SCOPED 2026-11-12 -- NOT AN ENTRY-POINT FIX ALONE.** zerobas's PLAY fills the
            published queues (QUETAB / VOICAQ.. / MUSICF / PLYCNT, basic/sysvars.inc) but with
            its OWN packet format (sub/playparse.asm: "own-design PLAY_OP_* packet stream"),
            drained by its own servicer (basic/playsvc.asm). A machine-code program that PUTQs
            the REFERENCE's packets and calls STRTMS would feed our servicer bytes it does not
            read, so STRTMS alone (MUSICF from the non-empty queues) would play garbage.
            ➡️ Steps: (1) the reference's packet format, read from RAM after a VG-8020 `PLAY`
            (QUETAB's rings and VOICAQ.. -- work-area RAM, readable; no ROM byte); (2) decide
            -- our servicer reads the reference's format (PLAY then writes it too), or STRTMS
            translates -- probably a question for Joost once (1) is measured, since it touches
            PLAY's tested engine; (3) then STRTMS itself, measured (MUSICF / PLYCNT after it,
            and the PSG registers read through RDPSG while it plays).
            🏗️ **RULED (Joost, 2026-11-12): *"2 (a)"* -- our PLAY and its servicer switch to
            the VG-8020's packet format** (the table below), then STRTMS as measured. TIER 1.
            📏 **(1) READ 2026-11-12** ([`playq_run.out`](scratchpad/playq_run.out), VG-8020, voice A, after the PLAY had
            ended): QUETAB's voice-0 descriptor `GET PUT 00 7F 75 F9` (size 127, buffer $F975);
            the packets from VOICAQ+1 (decoded from the eight variants -- one change each):
            | MML | packet | reading |
            |---|---|---|
            | `C` | `60 19 88 01 AC` | head `(3 << 5)` + 3 bytes follow the 2 duration bytes |
            | `T200C` / `L8C` | `60 0F ..` / `60 0C ..` | byte 2 = duration (25 at T120 L4 -> 15, 12) |
            | `V10C` | `.. 8A ..` | `$80 + volume` |
            | `O5C` / `N60` | `.. 00 D6` / `.. 00 6B` | tone period, big-endian (O4 C = $01AC) |
            | `R4` | `20 19 80` | 1 byte follows: volume 0 -- a rest |
            | end of string | `FF` | |
            ⚠️ A first reading, not yet a spec: envelopes (S / M), lengths over 255 and the
            duration's high bits are not varied yet. zerobas's own stream (sub/playparse.asm
            PLAY_OP_*) differs from this.
            📏 **(1) COMPLETED 2026-11-12** ([`playq_run2.out`](scratchpad/playq_run2.out) .. [`playq_run4.out`](scratchpad/playq_run4.out), VG-8020 only -- zerobas's side
            of this probe dies on `Out of string space`, D-CATALIAS's 66-char limit). **THE
            FORMAT:** a NOTE is `[n << 5 | dur bits 12..8] [dur bits 7..0] [vol] ([M hi]
            [M lo]) [tone hi] [tone lo]`, n = the bytes after the two duration bytes (3, or 5
            with M); `T32L1C` -> `61 77` (375 ticks). **vol** = `$80 | $40 if the M bytes
            follow | $10 in envelope mode | the volume, or the shape when $10`: `V10` `8A`,
            `S8` `98`, `S0` `90`, `V0` `80` (still a note, tone sent). **M** is sent ONCE, on
            the first note after an `M` command, in either mode (`M1000C` `C8 03 E8`,
            `S0M1000CC` -> `D0 03 E8 ..` then `90` alone; but `M255C` read plain `88` -- M
            equal to the default 255 sent nothing, see (b) below); a REST before that
            note carries nothing and the M waits for the next note (`M1000R4C`). A **REST** is
            `[$20 | dur hi] [dur lo] [$80]` whatever S says (`S0R4` `20 19 80`); `N0` is a rest
            of 5 ticks (`20 05 80`, not L's length). **End** `FF`. The QUETAB descriptor is
            `PUT GET BAKFLG SIZE ADDR` (`T32L1C` still playing: `06 05`), voice B's ring at
            $F9F5, size $7F, the same format. Durations are interrupt ticks (T120 L4 = 25 on
            this 50 Hz machine). ➡️ **Open before the build:** (a) is R13 rewritten on EVERY
            envelope note (an envelope restart -- the packet has no "S changed" flag, only M's
            $40; ours restarts only on S / M, the residual docs/audio-slice3-characterization.md
            left open) -- count port $A1 writes with R13 selected through an openMSX I/O
            watch, black-box; (b) M equal to its current value: `M255C` read `88`, so "M sent"
            may mean "M changed", not "M named" -- one row (`M1000CM1000C`).
            ✅ **(b) SETTLED** ([`playq_run5.out`](scratchpad/playq_run5.out)): `M1000CM1000C` sends the period once; `M1000CM2000C`
            twice (`C8 07 D0`) -- M is sent when its VALUE CHANGES, not when it is named.
            ✅ **(a) SETTLED** ([`psgenv_probe.py`](scratchpad/psgenv_probe.py) -> [`psgenv_run.out`](scratchpad/psgenv_run.out), an openMSX watch on $A0 / $A1): the
            VG-8020 writes **R13 on EVERY envelope note** (`S0M5000CCC`: three writes, the
            envelope restarted each time), and the value written is **the packet's whole vol
            byte** (`D0`, then `90` -- the PSG keeps the low nibble: the "upper bits shifted per
            note" the old trace saw); on a note with M it writes **R13 FIRST, then R11 / R12**.
            zerobas writes R13 only when S is named, the bare shape, after R11 / R12 (🔮 HIT:
            predicted per-note on the VG-8020, once here). ➡️ The format is now specified
            end to end: (2) is the build -- sub/playparse.asm emits these packets, basic/
            playsvc.asm decodes them (R13 per envelope note, before the period); then (3)
            STRTMS.
            ✅ **(2) BUILT (2026-11-12).** The amplitude register too, first: R8 = the WHOLE vol
            byte ($93 for `V5S3C` -- the PSG keeps 5 bits; the old "$10 | volume" belief came
            from S8 at V8, which cannot tell shape from volume) before R13
            ([`psgenv_run2.out`](scratchpad/psgenv_run2.out)). The rings are PRE-increment on the VG-8020 (its first packet at
            index 1; PUT / GET = the last byte written / read). sub/playparse.asm emits the
            VG-8020's packets (note, rest `[$20|hi][lo][$80]`, end $FF), M only when its value
            changed (seeded 255), N0 a 5-tick rest; basic/playsvc.asm decodes them: R8 := the
            vol byte, then R13 := the vol byte on every envelope note, then R11 / R12, then the
            tone. sysvars.inc's PK_* rewritten. Sub page 1 had 6 B (2026-11-12): the parser was squeezed
            (pt_note_amp from ENVSH's own $80 bit, ENVDIRTY holds M's $40 directly, S queues
            nothing, the ring write pre-increments, pt_length_eq lost its last caller and went) --
            **10 B left** (2026-11-12). After:
            [`playq_run8.out`](scratchpad/playq_run8.out) **34 / 34 rows byte-identical** to the VG-8020 (🔮 HIT), [`psgenv_run3.out`](scratchpad/psgenv_run3.out) every
            R11..R13 sequence SAME; tests/test_play_parse.py ALL PASS (decoder rewritten, N0 /
            M-same / S3's $13 rows); play, play-trace, playqueue, playeq, playarr, sound, beep
            acceptance green. Gate: playqueue-acceptance gains [`playpkt_gate.bas`](scratchpad/playpkt_gate.bas) (14 rows, the
            appended bytes in hex) 14 / 14 on both targets; knife (the M-unchanged skip ->
            `nop`s) -> RED on `M1000CM1000C` ([`playpkt_knife1.out`](scratchpad/playpkt_knife1.out); `M255C` stayed SAME -- 🔮 MISSED:
            the rows run in sequence, M was 1000 by then). ➡️ (3) STRTMS.
            📏 **(3) MEASURED (2026-11-12, [`strtms_probe.py`](scratchpad/strtms_probe.py), [`plycnt_probe.py`](scratchpad/plycnt_probe.py), VG-8020):**
            PUTQ'd packets + STRTMS play **only when PLYCNT >= 1** ([`strtms_run.out`](scratchpad/strtms_run.out) -- 🔮 MISSED: I
            predicted a start); then MUSICF := 7 (all three voices), PLYCNT - 1, the note sounds
            (R0 / R1 AC / 01, R8 88) ([`strtms_run2.out`](scratchpad/strtms_run2.out)); MUSICF already set -> nothing, PLYCNT kept;
            PLYCNT 2 -> 1, and at the end of the queued statement the sync takes the next count
            (MUSICF 7 again over empty rings) ([`strtms_run3.out`](scratchpad/strtms_run3.out)). So PLYCNT counts PLAY statements
            queued and not yet started: `PLAY "C"` reads PLYCNT 0 / MUSICF **7** at once, a
            second PLAY behind a long note PLYCNT 1, two behind 2 ([`plycnt_run.out`](scratchpad/plycnt_run.out)) -- **zerobas:
            PLYCNT one higher every time (it only ever counts up) and MUSICF 1 after `PLAY "C"`**.
            **PUTQ** ($00F9, never measured before) **pre-increments** like the rings (three bytes
            at VOICAQ+1..3, PUT 3; C-BIOS's, still ours, writes at +0..2) and leaves HL = the
            descriptor, BC = the new PUT, A = the buffer's low byte, Z / C clear ([`strtms_run4.out`](scratchpad/strtms_run4.out)).
            ➡️ **THE BUILD (designed 2026-11-12):** one page-0 routine `bios_strtms`: MUSICF != 0
            -> return; PLYCNT 0 -> return; else `st_go`: PLYCNT - 1, MUSICF := 7. It is the BIOS
            entry, the servicer's sync (psv_sync becomes `jp bios_strtms`: its per-voice release
            loop and the QD_PUTBAK "waiting" flag go -- the VG-8020's BAKFLG reads 0 throughout),
            and the parser's start: at a window's end, when something was queued and MUSICF is
            0, `st_go` (pt_publish no longer starts voices one by one); at the statement's end
            PLYCNT + 1 (the early `st_go` and the late +1 net to 0 inside one DI tenant call or
            across a full-ring wait, before any sync can see it). `PLAY ""` must count and start
            nothing (the reference's MUSICF reads 0 after it). PUTQ: a page-0 replacement,
            pre-incrementing, ~38 B. Room (2026-11-12): the crt_rows pad 53 B, the low region 26 B.
            ✅ **(3) BUILT (2026-11-12).** One more reading first: the VG-8020's `PLAY "C"` puts an
            end marker on voices B and C too (their PUT 1, [`plycnt_run2.out`](scratchpad/plycnt_run2.out)) -- every voice
            takes part in every PLAY that plays anything. Built: `bios_strtms` / `st_go`
            (see the placement note below) and
            `bios_putq` (basic/biosfnk.asm, the crt_rows pad); $0099 / $00F9 patched. The servicer's
            sync is `call z,bios_strtms` -- psv_sync's per-voice release loop and the QD_PUTBAK
            "waiting" flag are gone (main page 1's pad at $6CF3 grew 83 B, read 2026-11-12). The parser: pt_fresh
            gives an unnamed or "" voice length 0 (its end marker only) and leaves the tenant at
            once when nothing plays (`PLAY ""`: no count, no start); pt_publish ends in `jp st_go`
            when it queued something and MUSICF is 0; PLYCNT + 1 at the statement's end. `st_go`
            is exported to the sub ROM through the resident ABI. After: [`strtms_run5.out`](scratchpad/strtms_run5.out) every row
            SAME but `abc_busy` (MUSICF POKEd: our servicer runs a voice the VG-8020's does not --
            no PLAY does that); [`plycnt_run3.out`](scratchpad/plycnt_run3.out) 6 / 6; [`playq_run9.out`](scratchpad/playq_run9.out) 34 / 34; the PLAY unit test
            ALL PASS (its harness plants st_go's five instructions; `PLAY ,E,` now MUSICF 7 with
            voices 0 / 2 an end marker each, PLYCNT 1 for a PLAY behind a PLAY, `PLAY ""` nothing);
            play-acceptance's self-check MUSICF rows 1 / 3 -> 7 (the VG-8020's). Gate: **`make
            strtms-acceptance`** ([`basic_probe_strtms.py`](probes/basic/basic_probe_strtms.py), 14 rows) 14 / 14 ([`strtms_gate1.out`](scratchpad/strtms_gate1.out)); knife (st_go's `dec
            (hl)` -> `nop`, ROM hash moved) -> 8 rows RED ([`strtms_knife1.out`](scratchpad/strtms_knife1.out)). stub_scan -> **0**.
            🔴 **switch-build-check went RED on the first placement** (bios_strtms + st_go in the
            low region, 26 -> 6 B: the five switch-off builds overran it). Moved: bios_strtms's
            check (13 B) into the crt_rows pad, st_go (10 B) into island 1's last 10 B
            (basic/islands.asm). Room (2026-11-12): low region 26 B (unchanged), the crt_rows pad
            53 -> 3 B, island 1 10 -> 0 B, sub page 1 -> 2 B; 7 / 7 switches assemble.
            🔴 **The full gate went RED on gicini-acceptance's CONTROL row `m.one`** (MUSICF 7,
            want 1). Not GICINI and not the model: both machines start all three voices and an
            unnamed voice drops its bit at the first service tick ([`plycnt_run5.out`](scratchpad/plycnt_run5.out) .. [`plycnt_run7.out`](scratchpad/plycnt_run7.out):
            `CLS:A=PEEK` 1 on both; gicini's exact `CLS:PRINT"[";PEEK` 1 on the VG-8020, 7 here)
            -- whether a tick lands before the PEEK is the interpreter's SPEED, and the slower
            VG-8020 always has one. The old per-voice start hid it (B / C never got a bit).
            gicini's MUSICF rows now read only the voices they name (`AND 1` / `AND 3` / all):
            36 / 36 on zerobas and on the VG-8020 (the WANT values unchanged).
            (lifted to a top-level item on 2026-11-23: **A PLAY zeroes the OTHER voices' amplitudes on the VG-8020, not here** -- ...)
      - [x] OUTDLP ($014D): LPTOUT with TAB expansion and device I/O error.
            ✅ **THE HAPPY PATH FIXED 2026-11-12.** Measured with openMSX's printer logger
            ([`outdlp_probe.py`](scratchpad/outdlp_probe.py) -> [`outdlp_run.out`](scratchpad/outdlp_run.out)): `A TAB B TAB C CR LF` -> `A` + 7 spaces + `B` + 7
            spaces + `C\r\n`, `ABC TAB D` -> 5 spaces (to column 8), LPTPOS 0 after the CR
            (🔮 HIT). C-BIOS's stub printed nothing. Built: bios_outdlp (basic/biosfnk.asm, page
            0): TAB -> spaces to the next multiple of 8 of LPTPOS; LPTPOS kept as pch_lpt keeps it.
            `make outdlp-acceptance` (probes/basic/basic_probe_outdlp.py) 2/2; knife K5 (TAB sent
            raw) -> both RED ([`ODL_k5.out`](scratchpad/ODL_k5.out)). stub_scan 5 -> 4.
            - [x] OUTDLP's FAILURE face: the published "Device I/O error" -- a printer not ready
                  plus CTRL-STOP (or what ends LPTOUT's wait), measured; ours returns LPTOUT's CF.
                  🔴 **FIRST TRY 2026-11-12, NO READING:** [`outdlp_fail_probe.py`](scratchpad/outdlp_fail_probe.py) -- no printer
                  plugged, OUTDLP and (the control) plain LPTOUT called directly, CTRL-STOP held
                  from RUN + ~3 s for 1 s and then 3 s: BOTH machines, BOTH entries, nothing after
                  `RUN` ([`outdlp_fail_run.out`](scratchpad/outdlp_fail_run.out), [`outdlp_fail_run2.out`](scratchpad/outdlp_fail_run2.out)). The control's blank says it is the
                  APPARATUS first: does a `holds` press reach a program blocked in LPTOUT's wait at
                  all (where does the press land on a `direct` case's timeline)? Settle that
                  with a row that SHOULD break -- then OUTDLP's face.
                  ✅ **SETTLED AND FIXED 2026-11-12 -- D-LPTSTOP.** The apparatus first: a `direct`
                  case's hold, and a 3 s one, broke not even `10 GOTO 10` ([`outdlp_fail_run3.out`](scratchpad/outdlp_fail_run3.out),
                  [`outdlp_fail_run4.out`](scratchpad/outdlp_fail_run4.out)); stored programs with ctrlstop_probe.py's hold (lead 0.5 s, 2 s)
                  do ([`outdlp_fail_run5.out`](scratchpad/outdlp_fail_run5.out)). Then, no printer + CTRL-STOP: the VG-8020's OUTDLP
                  says **`Device I/O error`**, its LPTOUT RETURNS (A kept), its **LPRINT says
                  `Device I/O error`** ([`outdlp_fail_run6.out`](scratchpad/outdlp_fail_run6.out)) -- and zerobas never returned from
                  any of them. 🔴 **An LPRINT with no printer hung zerobas for good**: $00A5 is
                  zerobas's own LPTOUT (tape/tape.asm), whose BUSY wait had no way out. Fixed:
                  LPTOUT polls BREAKX in the wait (CY, A kept, nothing sent); pch_lpt (LPRINT /
                  LLIST) and OUTDLP raise 19 on that CY. `make outdlp-acceptance` gains
                  lprint_noprn / outdlp_noprn / loop_control (5/5). Knives: K6 (the BREAKX poll
                  -> `nop`s) -> both no-printer rows RED (a hang); K7 (pch_lpt's `jp c`) ->
                  lprint_noprn RED, outdlp_noprn still SAME ([`LPT_k6.out`](scratchpad/LPT_k6.out), [`LPT_k7.out`](scratchpad/LPT_k7.out)). outdlp,
                  lpterrnl, lptverb, editverb, bdos, biosregs, programs, cassave, cas-ascii,
                  iscntc, sessions green.
            - [x] 🔴 **AFTER MACHINE CODE HAS SEEN A CTRL-STOP, THE VG-8020's BASIC DOES NOT
                  ALSO BREAK; ZEROBAS's DOES** (found 2026-11-12, [`outdlp_fail_fixed.out`](scratchpad/outdlp_fail_fixed.out)): a USR that
                  ✅ **CLOSED 2026-11-13:** both halves of the slice shipped -- step 1 (the INTFLG
                  latch consumer, the STOP pause on the next latch) 2026-11-12, step 2 (the latch at
                  EVERY statement boundary, 2f63dd8b) today; outdlp-acceptance's brk_midline reads
                  `Break in 20` on both machines. The history below stays as written.
                  loops on BREAKX until CTRL-STOP, or LPTOUT left by it, returns, and the
                  program goes on to its end on the VG-8020 -- zerobas breaks at the next
                  statement (`Break in 30` / `in 40`), the key still being held. The VG-8020
                  breaks on INTFLG between statements; ours polls BREAKX's LEVEL (rp_exec). To
                  measure: INTFLG right after such a BREAKX, and whether the latch is set on the
                  press EDGE or every frame (intflg_isr_run6.out cannot tell: its loop ended with
                  the key down). 🎚️ TIER 1 -- a program the reference finishes stops here.
                  📏 **MEASURED 2026-11-12 -- IT DIVERGES BOTH WAYS** ([`brkconsume_probe.py`](scratchpad/brkconsume_probe.py) ->
                  [`brkconsume_run.out`](scratchpad/brkconsume_run.out)): the USR loops on BREAKX, then waits with interrupts on
                  through the hold and the release, clearing nothing. VG-8020 **`Break in 20`**
                  (the USR line: the latch, set while the code waited, broke the program at the
                  statement boundary); zerobas `[I 0 3 3 3]` + `[C END]` -- INTFLG latched 3 and
                  STILL 3 after the release, no break, because the run loop polls BREAKX's LEVEL
                  and the key was up by then. With breakx_loop (the USR returns AT ONCE, before
                  the interrupt has latched the press): VG no break, zerobas `Break in 30`.
                  ➡️ **THE READING: the VG-8020's BASIC breaks on the INTFLG LATCH at a statement
                  boundary (and consumes it); ours on the key's level at that instant.** A
                  DESIGNED SLICE: rp_exec's BREAKX poll -> the INTFLG latch (cheaper per statement
                  too), with ON STOP's edge shadow (D-STOPEDGE), D-STOPTEAR's confirming read and
                  rp_break's INTFLG clear (D-BIOSRUNG) re-derived on it; witnesses stop-trap,
                  interval-trap, trapstmt, direct-ctrl, iscntc, outdlp, sessions, programs.
                  ⚠️ First measure whether the latch is set on the press EDGE or every frame held
                  (zerobas: 0 right after BREAKX saw the key, 3 five frames later -- the scan
                  latency, not yet the edge question).
                  📏 **EDGE, ON BOTH (2026-11-12, [`latchedge_probe.py`](scratchpad/latchedge_probe.py) -> [`latchedge_run.out`](scratchpad/latchedge_run.out)):** wait for the
                  latch, clear it, five frames held, again after the release. CTRL-STOP `3 0 0`
                  -- latched ONCE, on the press; STOP `4 0 4` -- on the press and AGAIN after the
                  release (the STOP pause's second edge?). VG-8020 and zerobas identical: the
                  interrupt side needs nothing; the slice is the run loop's consumer only.
                  🔴 **AND STOP DOES NOT PAUSE A PROGRAM HERE (2026-11-12, [`stoppause_probe.py`](scratchpad/stoppause_probe.py) ->
                  [`stoppause_run3.out`](scratchpad/stoppause_run3.out)):** a 4.5 s TIME loop, STOP held 1 s from RUN+3.5 s -- the
                  VG-8020 prints nothing (paused, waiting for the next STOP), zerobas runs on to
                  `DONE`. The everyday "freeze the listing / the game" key does nothing. (Two
                  timeline misses first, kept: a 3 s loop ended before the press, a 5 s one
                  outlasted the capture -- the press lands at RUN + step + lead.)
                  ➡️ **THE SLICE, ONE CONSUMER:** at each statement boundary, INTFLG != 0 goes
                  through the logic isc_slow already has, measured as ISCNTC: 3 -> the break
                  (rp_break's trap / real-break arms), 4 -> the pause (key up, then the next
                  latch; CTRL-STOP there -> the break). BREAKX's level poll and D-STOPTEAR's
                  confirming read retire with it; ON STOP's shadow re-derived on the latch (an
                  edge already). 🎚️ TIER 1.
                  🅿️ **BUILT AND PARKED 2026-11-12 -- [`brklatch_wip.patch`](scratchpad/brklatch_wip.patch) (re-applies to 4b6aec33).**
                  The patch: stop_pause factored out of isc_slow; rp_exec / nx_again consume
                  INTFLG (3 -> rp_break, 4 -> stop_pause) instead of BREAKX's level; the shadow
                  release, D-STOPTEAR's confirming read and rp_real_break's shadow test gone; the
                  trap arm's KILBUF at the latch; the prompt clears INTFLG; LPTOUT's CTRL-STOP abort
                  waits for the release (TWICE-read BREAKX -- one read tore >40 frames early) and
                  clears the latch. Measured with it: STOP paused a program as the VG-8020
                  (1 s hold), breakx_loop / lptout_noprn / lptout_intflg SAME, and 14 suites green
                  (stop-trap, interval-trap, trapstmt, direct-ctrl, sessions, programs, input,
                  key-trap, onerr0, iscntc, outdlp, biosregs, lpterrnl, editverb).
                  🔴 **NOT SHIPPED -- TWO OF ITS FOUNDATIONS DID NOT HOLD:** (1) LPTOUT's "wait for
                  the release" rested on lptout_upframes, whose scratch probe POKEd 22 of its 23
                  bytes (the `ret` missing); coded correctly in the gate the VG-8020 answers
                  `Break in 20` -- the press DOES reach BASIC there, and lptout_intflg's `0 0`
                  reading needs re-reading next to it. (2) The STOP pause depends on the press
                  LENGTH: a 1 s hold kept the VG-8020 paused, a 2 s one ended in `DONE` -- STOP
                  latches on the RELEASE too (`4 0 4`), so a long press may end its own pause;
                  ours, waiting on NEWKEY then clearing, behaves differently. And the per-statement
                  granularity (brkconsume: VG `in 20`, ours `in 30`) needs a break exit at
                  exec_stmt's depth, not designed yet.
                  ➡️ **BEFORE RESUMING:** the STOP pause measured against press length (0.2 / 0.5
                  / 1 / 2 s) and a SECOND press (two holds in one case -- run_cases takes one);
                  LPTOUT's CTRL-STOP face re-measured with byte-checked probes (assert len(DATA)
                  == the POKE count -- the bug that cost this); then the exec_stmt break exit.
                  📏 **THE PAUSE AGAINST PRESS LENGTH (2026-11-12, [`pauselen_probe.py`](scratchpad/pauselen_probe.py) ->
                  [`pauselen_run.out`](scratchpad/pauselen_run.out)):** a 4 s loop, STOP from RUN+3.5 s, capture RUN+4.5+h:
                  | hold | VG-8020 | zerobas |
                  |---|---|---|
                  | 0.2 s | paused (nothing) | DONE 200 |
                  | 0.5 s | DONE 200 (no pause seen) | DONE 200 |
                  | 1.0 s | paused | DONE 200 |
                  | 2.0 s | DONE **214** (paused, resumed on the release) | DONE 200 |
                  NOT MONOTONIC in the press length: STOP latches on the press AND the release
                  (`4 0 4`), and what the interpreter does depends on which of the two it samples
                  at a statement boundary -- no one-line rule fits all four, and the WIP patch's
                  (key up, then the next latch) does not reproduce it. ➡️ Next: INTFLG sampled
                  EVERY FRAME through a press on the VG-8020 while a BASIC loop runs (a POKEd
                  frame logger on the H.TIMI hook -- work-area RAM, readable), to see which
                  latches the interpreter consumes and when.
                  📏 **FIRST FRAME LOG (2026-11-12, [`framelog_probe.py`](scratchpad/framelog_probe.py) -> [`framelog_run.out`](scratchpad/framelog_run.out)):** our
                  code on H.TIMI logs INTFLG + the BASIC loop's counter each frame (the dump's
                  tail -- `F255/F0` alternating -- is unwritten RAM past the log's end, ignore
                  it). VG-8020: the hook NEVER sees INTFLG non-zero -- the interpreter consumes
                  the latch before the next frame's H.TIMI; the loop STALLS for 0.2 s and 1 s
                  holds (to the capture), NOT AT ALL for 0.5 s, 35 frames for 2 s (then
                  resumes). zerobas: INTFLG 4 appears and stays, no stall. ➡️ Next instrument:
                  log NEWKEY row 7 (the key itself) beside the counter, to line the press /
                  release frames up against the stall's start and end -- the 0.5 s row is the
                  one no rule yet explains. (The offset assert in the probe caught a `jr nc`
                  landing mid-instruction before it ran: the POKE-count lesson, applied.)
                  📏 **ROUND 2, THE KEY ITSELF -- THE RULE (2026-11-12, `framelog_probe.py --key` ->
                  [`framelog_key.out`](scratchpad/framelog_key.out)):** NEWKEY row 7 and the loop counter per frame, the pointer
                  captured (written frames only). 🔴 **APPARATUS FIRST: the "0.5 s" row never
                  pressed the key on EITHER machine, and the others were shorter than asked**
                  (1.0 s -> 24 frames down, 2.0 s -> 75) -- `hold_secs` is not honoured as written,
                  so pauselen's "0.5 s: no pause" was a non-press, and every hold-based row should
                  log the key it thinks it pressed. With the REAL press lengths the VG-8020 is
                  simple: a 24-frame press -- the loop stalls from the next frame to the end of
                  the log (the RELEASE does not resume); a 75-frame press -- stall @166..@201, the
                  program resumes 36 frames (~0.7 s) after the press **with the key still down**
                  -- the keyboard's auto-repeat delivering the "next STOP" (and probably
                  latchedge's `4 0 4` too). ➡️ **THE VG-8020's RULE: pause on a STOP latch, resume
                  on the NEXT STOP latch -- a press OR an auto-repeat; the release is not one.**
                  The parked patch's stop_pause (key up first, then a fresh latch) is wrong for a
                  long press; ISCNTC's measured rows still agree with it (single taps). Before
                  resuming: settle `hold_secs` (why "0.5" pressed nothing) and confirm the repeat
                  latch on zerobas's interrupt (C-BIOS's repeat for STOP).
                  ✅ **`hold_secs` SETTLED (2026-11-12):** run_cases counts the release from the
                  same instant as the press's LEAD, not from the press -- the key is down for
                  `hold_secs - hold_lead` (lead 0.5: 1.0 -> 0.5 s, 2.0 -> 1.5 s, 0.5 -> nothing, 0.2
                  -> released before pressed, so held for good). The four gates that pass a lead
                  (iscntc 0.5/1.0, outdlp 0.5/2.0, screditor 0.1/0.5, kwsweep `@0.5/2.0`) were
                  measured with that meaning, so it is KEPT and stated in probes/lib/omsx_repl.py,
                  and a press that would end at or before it starts now RAISES instead of reading
                  as a plausible "no effect". (kwsweep's and ctrlstop_probe's "2 s Ctrl-STOP" is
                  1.5 s.)
                  ✅ **THE REPEAT LATCH, ON ZEROBAS TOO (2026-11-12, [`repeatlatch_probe.py`](scratchpad/repeatlatch_probe.py) ->
                  [`repeatlatch_run.out`](scratchpad/repeatlatch_run.out)):** our code on H.TIMI logs INTFLG and clears it each frame
                  through a 75-frame STOP press: the press latch @158, then repeats from @194 --
                  **36 frames later, exactly the VG-8020's resume point** -- and every 3 frames to
                  the release. So the rule is complete: **pause on a STOP latch, resume on the
                  NEXT latch (press or repeat), no key-up wait.** ➡️ To resume the slice: apply
                  brklatch_wip.patch, drop stop_pause's key-up loop (sp_up), and re-measure the
                  pause rows WITH the key logged; ISCNTC's shipped wait (key up first) then
                  changes with it -- its rows are single taps and should still agree.
                  ✅ **STEP 1 SHIPPED (2026-11-12, D-BRKLATCH):** brklatch_wip.patch re-applied MINUS
                  its two unfounded parts (LPTOUT's release-wait, its gate rows), with
                  stop_pause's key-up wait dropped (the pause ends on the NEXT latch -- a press or
                  the auto-repeat). Plus **BREAKX consumes a press it sees** (bios_breakx,
                  basic/biosfnk.asm, page 0: C-BIOS's body, then STOP marked down in OLDKEY, so the
                  scan sees no new edge and latches nothing -- C-BIOS latches INTFLG only for a key
                  newly down against OLDKEY or a repeat): the VG-8020's face after LPTOUT's abort
                  (INTFLG 0, still 0 ten frames on). The pause now matches the VG-8020 FRAME BY
                  FRAME (stall @164..END vs @166..END for 10- and 25-frame presses, @164..@199 vs
                  @166..@201 for 75 -- [`BL3_pause.out`](scratchpad/BL3_pause.out)). `make outdlp-acceptance` 9/9 (+ breakx_loop,
                  lptout_noprn, stop_pause, lptout_intflg; the POKE counts asserted against the
                  bytes); knives K8 (rp_exec's stop_pause call -> nops) -> stop_pause RED
                  ([`BL3_k8.out`](scratchpad/BL3_k8.out)), K9 (the OLDKEY store -> nops) -> GREEN on 8 rows, so lptout_intflg was
                  ADDED as its witness and reads `0 3` + a break under it ([`BL3_k9_intflg.out`](scratchpad/BL3_k9_intflg.out)). 14
                  break / trap suites green. ISCNTC's wait now shares stop_pause (no key-up).
                  - [x] STEP 2: the per-STATEMENT check (brkconsume: VG `Break in 20`, ours
                        `in 30`) -- a break exit at exec_stmt's depth.
                        ✅ **SHIPPED 2026-11-13.** Its blocker was L5_files' interrupt gap, and the
                        gap was not step 2's: hk_ochk / hk_srcfind ran their mount reads masked
                        (D-FWDWIN, fixed in 8ef12e5a). With that fix and step 2 applied: no FDC
                        op masked, max gap 0.036 s ([`FW8_step2_stack.out`](scratchpad/FW8_step2_stack.out)); es_latch re-sited to
                        basic/keytrap.asm (after the pins -- from basic/input.asm it overran the
                        crt_rows pad the BIOS entries had spent); outdlp, iscntc, stop-trap,
                        interval-trap, key-trap, trapstmt, direct-ctrl, sessions, lpterrnl, onerr0,
                        input, editverb, biosregs and programs acceptance green; 7 / 7 switches.
                        Low region 26 -> 7 B (2026-11-13).
                        🅿️ **BUILT, PARKED 2026-11-12 -- [`brklatch_step2_wip.patch`](scratchpad/brklatch_step2_wip.patch) (on 8c79b9ea).**
                        es_latch (page 0, beside stop_pause) is THE consumer: 3 -> rp_break
                        (now callable: the trap arm `ret`s, the break arms drop the caller's
                        frame and `jr do_break`, as ex_stop does from a handler), 4 -> the
                        pause; rp_exec and exec_stmt both reach it -- exec_stmt through
                        `call es_bound` (latch, then traps), because inline both tests overran
                        $8000 (pasmo: "image base $8000"). Page 1 10 -> 30 B free. brkconsume
                        SAME (`Break in 20` on both); outdlp gate 10/10 with `brk_midline`;
                        knife K10 (es_bound's latch test) -> brk_midline `in 30` RED; 12 of 13
                        break / trap suites green. 🔴 **NOT SHIPPED: programs-acceptance's
                        L5_files** -- zerobas's longest frame-interrupt gap 0.285 s against the
                        CF-3300's 0.223 (D-GCDI's rule), deterministic over three runs; step 1
                        read 0.139 there (BL3_programs.out). A per-statement call shifts
                        statement timing, and a disk wait under DI moved with it -- longer than
                        a revolution, so likely a missed sector. ➡️ Find the gap's PC (the
                        asavedi_pc_probe.py way, `--min=` on the gap) before shipping.
                        📏 **FOUND (2026-11-12, `asavedi_pc_probe.py L5_files --min=0.25` with the
                        patch applied -> [`S2G_gap.out`](scratchpad/S2G_gap.out)):** 265 of the 285 ms in **disk.rom's
                        `fwd_wait`** -- the WRITE path's wait for its sector, IFF 0 throughout,
                        CURLIN 40 (L5_files' first OPEN FOR OUTPUT). Not step 2's own code: the
                        read side's waits take D-FDCDI's interrupt windows, the write side's do
                        not, so a write waits up to a revolution under DI wherever its command
                        happens to start -- step 2's one call a statement moved this one onto a
                        near-full revolution. ~~➡️ D-FWDWIN: give fwd_wait the read side's
                        windows~~ -- 🔴 **WRONG FIRST READING, corrected the same hour:** the write
                        path ALREADY opens them (fdc_write_data_body calls fdc_fdrq), and line 40
                        is PRINT #1 / #2 through hk_chout, whose entry does `ei`. The sampler's 6
                        samples in **fdc_restore** (a recalibration -- errors happened) say what
                        did: the first DRQ arrived while an interrupt was taken in a window ->
                        LOST DATA -> windowed retries up to FDC_WINMAX -> the LAST attempt waits
                        MASKED, as D-FDCDI designed, up to a revolution. Step 2's timing moved the
                        interrupt's phase onto the sector's arrival. ➡️ **D-FWDWIN, re-scoped:**
                        the window rule must not let a lost-data streak end in a masked
                        revolution -- e.g. no window once the sector is near (the index pulse /
                        a sector-ID read tells), or the masked fallback only after a real error,
                        not LOST DATA. Measure the retries first (a watchpoint on FDC_IFF's count
                        and the command register, as fdccmd_probe.py does); then re-gate step 2.
                        📏 **MEASURED -- AND THE "LOST-DATA STREAK" IS NOT CONFIRMED EITHER
                        (2026-11-12, `fdccmd_probe.py L5_files` with step 2 applied ->
                        [`FW_fdc.out`](scratchpad/FW_fdc.out)):** 134 commands, NO restore command at all (the six
                        "fdc_restore" PC samples were a routine NAME, not a recalibration -- a
                        second wrong inference from a symbol). What line 40 really does: READ
                        sector 2 (the FAT) at 25.981 s, WRITE sector 2 at 26.056 s, next command
                        26.255 s -- a ~0.2 s write: writing back the sector it just read waits for
                        it to come round again, nearly a revolution, and the sampler saw that wait
                        MASKED (IFF 0 in fwd_wait). So fdc_fdrq did not open its windows for THIS
                        write. ➡️ Next, measured not guessed: FDC_IFF and its retry count at that
                        write's entry (a watchpoint on the command register reading FDC_IFF) --
                        is the caller masked, or the window budget spent? Then the fix (and the
                        read-modify-write of one FAT sector, a revolution each time, is itself a
                        speed lever: D-BLKIOPERCALL's class).
                        ✅ **ANSWERED (2026-11-12, fdccmd_probe.py now logs FDC_IFF ($EFF7) at
                        each command -> [`FW3_fdc.out`](scratchpad/FW3_fdc.out)):** line 40's FAT READ runs with
                        FDC_IFF 01 (the caller had interrupts on: windows open); EVERY WRITE after
                        it -- FAT sectors 2 and 5, the data sector -- with **00**. The caller's
                        interrupts went off BETWEEN them: a sector op ends masked (fdc_fdrq
                        "returns masked") and DSKIO's exit does not give the caller back its IFF,
                        so the next DSKIO in the same hook captures "masked" and waits its whole
                        revolution with interrupts off. Pre-existing (step 1 has the same path;
                        step 2 only moved the phase onto a long wait). ➡️ **D-FWDWIN, THE FIX:
                        DSKIO's exit restores the caller's IFF (`ei` when FDC_IFF says it was on)**
                        -- then every consecutive sector op keeps D-FDCDI's windows. Witness:
                        programs-acceptance --gaps (L5_files) with step 2 applied, and the iff=
                        column staying 01 through line 40.
                        ⚠️ **CORRECTION, SAME DAY: fdc_io_done DOES give the caller its IFF back**
                        (disk/fat.asm fdc_io_done: `ei` when FDC_IFF != 0) -- so the interrupts go
                        off BETWEEN the read's return and the write's fdc_di_save, somewhere on
                        the write's path, not in DSKIO's exit. The stack sampler on HEAD
                        (`asavedi_pc_probe.py L5_files --min=0.12 --stack` -> [`FW4_stack.out`](scratchpad/FW4_stack.out)) shows
                        DSKIO reached through **dskio_calslt** (an inter-slot call) on line 100's
                        OPEN -- a LEAD for where a write loses its EI, NOT a finding (two
                        symbol-name inferences on this thread were already wrong). And a
                        separate puzzle there: that 0.139 s gap sits INSIDE the windowed read
                        poll (frdw_poll) with no JIFFY tick at all. ➡️ Next: the write's
                        call stack at its fdc_di_save (a PC breakpoint there logging the stack
                        and IFF), and whether frdw_poll's window takes an interrupt at all on
                        that path.
                        📏 **DONE ON HEAD (2026-11-12, fdccmd_probe.py `FDC_STACK=1`: a breakpoint
                        at our fdc_di_save logging the CPU's IFF and 12 stack words ->
                        [`FW5_stack.out`](scratchpad/FW5_stack.out)):** on HEAD (no step 2) **every write runs with
                        interrupts ON** -- all 15 `A0` commands FDC_IFF 01, the caller's IFF 1 at
                        fdc_di_save (FW3's masked writes were step 2's). The ops HEAD runs masked
                        are 9 READS, every one `fat_geom_read` inside `fat_mount`, reached from
                        the hooks **`hk_ochk` / `hk_srcfind`** with interrupts already off -- the
                        lead for HEAD's own gaps (max 0.139 s). ⚠️ And **step 2 no longer
                        assembles on HEAD** (scratchpad/brklatch_step2_wip.patch applies, but
                        an image region overruns -- `split_islands: image base $8000`: a `ds`
                        went negative; page 0's pads were spent on the BIOS entries the same
                        day). ✅ **Which region:** step 2 puts es_latch (20 B) in basic/input.asm,
                        which assembles BEFORE the crt_rows pin ($3283): that span is bounded by
                        the pin's pad (3 B since the BIOS entries, 2026-11-12), not by the low
                        region's 26 B tail after the pins -- `ds $3283 - $` went negative (es_latch
                        at $2EA7 in a scratch assembly). ➡️ Re-site es_latch in a low-region file
                        AFTER the pins (basic/keytrap.asm, line 89 of main.asm) when step 2 is
                        re-applied; then measure its masked writes with FDC_STACK, and why hk_ochk /
                        hk_srcfind reach fat_mount masked on HEAD.
                        ✅ **HEAD's half FIXED (2026-11-12):** a hook arrives through an inter-slot
                        call with interrupts OFF; hk_fmake starts with `ei`, hk_ochk and hk_srcfind
                        did not, so their fat_mount reads ran masked. Both now `ei` first (disk/
                        driver.asm, disk/kernel.asm). After ([`FW7_stack_ei.out`](scratchpad/FW7_stack_ei.out)): **0 masked FDC
                        entries** (9), L5_files' interrupt gaps **19 -> 10, max 0.139 -> 0.036 s**
                        (🔮 HIT); diskbasic, bdos, diskascii, diskfull, asavechan, savedev green.
                        ➡️ Left of D-FWDWIN: step 2's own masked writes, once es_latch is re-sited.
                        - [x] **No gate row pins "no FDC op runs masked"** -- 🎚️ TIER 2 — the
                              FDC_STACK reading is a scratch probe; a row counting `K iff=0`
                              entries over L5_files (expect 0) would catch a hook that loses its
                              `ei`.
                              ✅ **D-FDCMASKED (2026-11-14): `make fdcmasked-acceptance`**
                              (probes/disk/disk_probe_fdcmasked.py, in run_gates' list): a PC
                              breakpoint at our fdc_di_save reads the CPU's IFF over EVERY `# @DISK`
                              program of probes/programs, not L5_files alone -- 441 entries, 0
                              masked ([`FM_run1.out`](scratchpad/FM_run1.out); 🔮 HIT). A program with no entry is
                              REFUSED, not passed. KNIFED: hk_ochk's and hk_srcfind's `ei` made
                              `nop` -> L5_files 9 masked, FAIL ([`FM_knife.out`](scratchpad/FM_knife.out)) -- the 9 FW5 found.
                  (lifted to a top-level item on 2026-11-23: **lptout_upframes: two VG-8020 readings of the same bytes disagree** -- two VG-8020 ...)
            (lifted to a top-level item on 2026-11-23: **OUTDLP on a non-MSX printer: the hiragana -> katakana transform** (NTMSXP $F417 != ...)
      - [x] CALBAS ($0159): call a BASIC-interpreter address from any slot.
            ✅ **FIXED 2026-11-12.** 🔴 Worse than a stub: C-BIOS's printed `ERROR:CALLED NON
            EXISTING BASIC.` and never returned ([`calbas_run.out`](scratchpad/calbas_run.out) -- zerobas gave NO capture). The
            VG-8020 with IX = $004D (WRTVRM, the same entry in both ROMs), A = $5A, HL = $3F10:
            the cell written, HL / DE / BC / A back, IY 0 ([`calbas_probe.py`](scratchpad/calbas_probe.py)). Built: bios_calbas
            (basic/biosfnk.asm, page 0, 7 B): IYH := EXPTBL[0], `jp CALSLT`; $0159 points there.
            biosregs-acceptance `calbas` (prog() gained `ix=`); knife K4 (`jp CALSLT` -> `ret`) ->
            RED ([`CAL_k4.out`](scratchpad/CAL_k4.out)). stub_scan 6 -> 5.
      - [x] PNTINI / SCANR / SCANL ($0129 / $012C / $012F): PAINT's helpers -- main room
            (D-BIOSCONTRACT). ✅ **BUILT (2026-11-12), steps (1) and (2) of the plan below:**
            sub/paintbios.asm, ONE zerobas-sub page-1 tenant (SUBROM_IDX_PAINT 35, 164 B with its
            table row -- sub page 1 170 -> 6 B free, read from clean) behind an 18 B page-0 stub
            (basic/biosfnk.asm: the op in C, each entry's `ld c,n` swallowed by the previous
            one's `db $21`), in the pad before the crt_rows pin ($3283), which the low-region
            wall readout does not count (it still says 26 B; the pad had 89 B, then 71 -- 🔴 this
            line first said "71, now 53": the 71 was read AFTER the stub went in). The
            tenant uses the BIOS's own READC / SETC / RIGHTC / LEFTC (CALSLT keeps slot-0 page 0
            mapped) -- the cursor family fixed for SCREEN 3 the same day. Witness:
            **`make paintbios-acceptance`** ([`basic_probe_paintbios.py`](probes/basic/basic_probe_paintbios.py), 15 rows, SCREEN 2 and 3:
            HL, SCANR's DE, CLOC / CMASK, BDRATR, the painted VRAM; BC / A not compared) **15 / 15
            SAME** ([`paintbios_gate1.out`](scratchpad/paintbios_gate1.out), 🔮 HIT). Knives, the ROM hash moving each time: SCANL's step
            back off the border -> `ret z` -> RED on `l15_fill` / `b3_l_fill` (CUR) ([`paintbios_knife1.out`](scratchpad/paintbios_knife1.out);
            `l9_edge` stays SAME, it stops at the edge -- 🔮 MISSED that one row); the whole-byte
            rule cut -> RED on the three SCREEN 2 fill rows (PAT, COL), SCREEN 3 SAME
            ([`paintbios_knife2.out`](scratchpad/paintbios_knife2.out)). 🔴 **The first knife was INERT** (sub.rom's hash unmoved): the
            Makefile's sub.rom prerequisite list did not name the new file -- added; only the
            hash around the plant caught it (an inert knife reads like a blind gate).
            stub_scan: 4 -> **1** (STRTMS). ➡️ Step (3), PAINT onto the tenant, stays open below.
            (lifted to a top-level item on 2026-11-23: **SCREEN 3 leaves unused VRAM unlike the VG-8020** -- 🎚️ TIER 6 — SCREEN 3's ...)
            - [x] **The low-region wall readout does not count the pad before crt_rows** --
                  🎚️ TIER 6 — an instrument: `make basic-reloc` says "low region pin pads 0 B"
                  while 53 B (2026-11-12, after GRPPRT's stub) sit before the hand pin at $3283 (basic/float-arith.asm); D-
                  BIOSCONTRACT's stubs live there unseen by any budget.
                  ✅ **FIXED 2026-11-14 (D-ESIDXAL):** $3283 (crt_rows) and $475A (usr_fcerr) were
                  `ds` pins in the source but absent from tools/pin_plan.py's PINS, so neither was
                  checked by `make pin-check` and neither pad was counted. Both are listed now
                  (address-free head bytes); the readout shows 9 B at $3283 and 188 B at $475A on
                  2026-11-14, and pin-check reads 9 / 9 pins present. Every `ds $xxxx - $` in
                  basic/ now has a PINS row ($4000 / $8000 are the page ends).
            🎚️ **FIRST IN THE QUEUE (Joost 2026-11-12: the BIOS stubs before the rest).** 🏗️
            Joost's idea (2026-11-12): *"could the implementation of paint use parts of those
            paint bios calls to save space?"* -- THE PLAN: (1) measure the three on the VG-8020
            (SCREEN 2 and 3: a BASIC-drawn border, the cursor placed by MAPXYC, PNTINI with A =
            the border colour, SCANR / SCANL with B = the fill flag and DE = the skip count; read
            HL, DE, CLOC / CMASK, BDRATR $FCB2 -- GFX_B shares it -- and the touched VRAM);
            (2) build them as SUB-ROM tenants behind thin PAGE-0 stubs (~8 B each, as
            bios_dspfnk's subrom_call -- a BIOS entry may be called with page 1 RAM; the low
            region had 26 B free at last reading, 2026-11-12); (3) a SEPARATE slice moves PAINT
            onto the same tenants -- the classic scan / skip-count algorithm, not a call swap
            (gfx_paint_scan_row only tests its caller's [xL,xR]) -- dropping its own scanner:
            sub-ROM bytes back, and PAINT's fill order and stack use nearer the VG-8020's (its
            out-of-memory point on a complex shape). Witnesses for (3): graphics-, graphics-
            floor-acceptance and the PAINT rows.
            📏 **FIRST VG-8020 READINGS (2026-11-12, [`paintbios_probe.py`](scratchpad/paintbios_probe.py) -> [`paintbios_run.out`](scratchpad/paintbios_run.out)):**
            SCREEN 2, borders at x = 20 and 100 in colour 15, the cursor at (50,55) by MAPXYC,
            PNTINI A = 15 with ATRBYT = 4. **In SCREEN 2 PNTINI ignores A: BDRATR became 4, the
            PAINT colour** -- the SCREEN 2 rule that the boundary IS the paint colour. So these
            rows asked SCANR to stop at colour 4 while the line was 15: it ran from x = 50 PAST the
            x = 100 line, CLOC $667 / CMASK 4 (x = 101), HL 1, DE $FFCE, the line's pattern byte
            read 00 afterwards; with B = 0 the same CLOC and HL but BC $0410; SCANL HL 0, DE
            $2000, CLOC unmoved; skip 5: HL 0, DE 0, CMASK 2. zerobas: the bare `ret`s (HL = CLOC
            from MAPXYC, DE as passed). ➡️ Next run: paint colour = border colour (15), the
            natural SCREEN 2 PAINT case, before HL / DE are interpreted; then SCREEN 3 (where A
            is the border).
            📏 **ROUND 2, paint = border = 15 ([`paintbios_run2.out`](scratchpad/paintbios_run2.out), VG-8020):** SCANR fill from
            x = 50: **HL 50** (x 50..99), cursor ON the border (CLOC $667 / CMASK 8 = x 100), DE 0;
            the row's pattern changes only at the ends (`3F` x 50..55, `F8` x 96..100) -- the full
            bytes between read 00, so a whole-byte fill evidently goes to the COLOUR table (read
            it next). SCANR without fill: the same HL / cursor, no VRAM change, B $0F vs $F0.
            SCANL fill: **HL 29** (x 21..49 -- it EXCLUDES its start pixel, SCANR includes it),
            cursor on x 21 (the last painted, not the border), DE 4. ⚠️ SCANL with B = 0 changed
            VRAM exactly as with B = 1 -- the flag means something else for SCANL, or the row is
            wrong: settle before building. Skip 5 on SCANR: HL 50, DE 5 back. ➡️ Next: the colour
            table (the same bytes at $2000 + offset), SCANL's flag, the skip count's meaning
            (a SCANR across already-painted pixels), SCREEN 3.
            📏 **ROUND 3 ([`paintbios_run3.out`](scratchpad/paintbios_run3.out), VG-8020):** (1) **the whole-byte fill goes to
            the COLOUR table**: the full bytes between the ends read colour `0F` (background
            nibble = the paint colour) with the pattern left 00; the partial end bytes set
            pattern bits and become `F4` (🔮 "$F0": MISSED -- the background nibble). (2) **SCANL
            ALWAYS FILLS**: B = 0 and B = 1 give the same VRAM -- the fill switch is SCANR's
            only (classic PAINT probes with SCANR, paints with SCANL). (3) **the skip count**: a
            second SCANR from x = 50, now border-coloured, returned HL 0, DE 0 (the 5 used up)
            and the cursor at x 54 -- it steps over border-coloured pixels while DE lasts,
            finds no paintable run, stops. ➡️ Left: SCREEN 3 (PNTINI's A as the border there),
            and the registers' exact exit state (BC / A) -- then the build.
            📏 **ROUND 4, SCREEN 3 ([`paintbios_run4.out`](scratchpad/paintbios_run4.out), [`paintbios_run5.out`](scratchpad/paintbios_run5.out)):** PNTINI A = 15
            -> **BDRATR 15** (🔮 HIT: in SCREEN 3 A IS the border). The fill rows are NOT YET
            READABLE: paint 4 was SCREEN 3's own background (invisible), and with paint 9 the
            12-byte window at row 55 is still unchanged -- because MAPXYC(50,55) left the cursor at
            CLOC **$6DF** / CMASK F0, far from (50,55) by the layout I assumed
            ((y//32)*256 + (x//8)*8 + (y//4)%8). SCANR HL 4, SCANL HL 5 (blocks?). ⚠️ One of my two
            premises is wrong -- MAPXYC's coordinates in SCREEN 3, or the address formula: settle
            it first (MAPXYC alone, then CLOC / CMASK for a grid of points), then read the fill
            around CLOC, before anything is built for SCREEN 3.
            📏 **ROUND 5, SCREEN 3 IN BLOCKS (2026-11-12, [`paintbios_run6.out`](scratchpad/paintbios_run6.out), after MAPXYC's fix):**
            borders at blocks 5 and 25 of block row 13, the cursor at block 12, paint 9, PNTINI A
            15. **SCANR** fills blocks 12..24 (🔮 HIT), **HL = 13** (the count, start included),
            the cursor ends ON the border (CLOC $165 / CMASK $0F, block 25), DE back as passed (0,
            or 3 with a skip count of 3 -- no border block to step over here), BC = $0F01, A = 0.
            **SCANL** fills blocks 6..11 (start excluded, as SCREEN 2), **HL = 6**, the cursor on
            the LAST FILLED block (6, CMASK $F0), A = $F0, BC $0F01. ⚠️ **SCANR with B = 0 FILLED
            too** in SCREEN 3 (🔮 not predicted -- in SCREEN 2 B = 0 changed no VRAM). ✅
            **CONFIRMED** ([`paintbios_run7.out`](scratchpad/paintbios_run7.out), paint 7, fresh rows): B = 0 and B = 2 both fill
            blocks 12..24, BC $0F01 either way -- in SCREEN 3 SCANR ignores B. zerobas: the
            three are still bare `ret`s (nothing written).
            📏 **ROUNDS 6-8, SCREEN 2's last questions (2026-11-12, [`paintbios_run8.out`](scratchpad/paintbios_run8.out), [`paintbios_run9.out`](scratchpad/paintbios_run9.out),
            [`paintbios_run10.out`](scratchpad/paintbios_run10.out)):** paint = border = 9 (lines in 9). SCANR from x 50: the partial
            end bytes get their pattern bits SET and colour byte **paint << 4 | old background**
            ($94); every WHOLE byte between gets pattern $00 and colour byte **= the paint
            colour** ($09) -- also over a colour byte of $C4: the foreground is CLEARED, not kept.
            SCANL the same leftward (x 21..49, HL 29). Registers: SCANR HL = the count, DE as
            passed, B = the last partial byte's fill mask ($F0), C = A = $05 (a leftover, origin
            unread); SCANL DE 4, B $C0. **At the screen's edge with no border** SCANR from x 150
            stops ON x 255 (HL 106, CLOC $6FF / CMASK 1), SCANL from x 10 on x 0 (HL 10, CMASK
            $80); SCREEN 3 the same in blocks (block 63 / block 0). ➡️ The measurement is
            complete for both screens (HL, DE, CLOC / CMASK, BDRATR, VRAM; BC / A leftovers
            partly read): next is the build -- sub-ROM tenants behind page-0 stubs. 💡 A
            tenant called through CALSLT into sub page 1 keeps slot-0 page 0 mapped, so it can
            use the BIOS's own RDVRM / WRTVRM and the cursor family just fixed (READC, RIGHTC,
            LEFTC) instead of carrying its own.
            ✅ **SETTLED -- AND A NEW DIVERGENCE (2026-11-12, [`mapxyc3_probe.py`](scratchpad/mapxyc3_probe.py) ->
            [`mapxyc3_run.out`](scratchpad/mapxyc3_run.out)):** MAPXYC alone, four points. SCREEN 2: identical on both. **SCREEN 3:
            the VG-8020's MAPXYC takes BLOCK coordinates (0..63 x 0..47), not pixels** -- (8,0) ->
            $20, (0,32) -> $400, (50,55) -> $6CF / F0 (byte (x/2)*8 + (y/8)*256 + y%8, the left
            nibble for even x); zerobas maps them as SCREEN 2 pixels (0/80, 8/80, 400/80,
            637/20). So my SCREEN 3 PAINT rows passed pixels where blocks were wanted.
            - [x] **MAPXYC in SCREEN 3 takes block coordinates** (and very likely FETCHC / STOREC
                  / the moves follow the same SCREEN 3 shape) -- 🎚️ TIER 1, a main-BIOS entry off
                  the VG-8020 (the graphics-cursor family was fixed for SCREEN 2 only). Measure the
                  family in SCREEN 3 the same way, then fix. The PAINT helpers' SCREEN 3 rows wait
                  on it (re-run them in block coordinates: x 12, y 13 is about pixel (50,55)).
                  🔴 **ZEROBAS-ONLY, AND A D-CBIOS031 MISS (2026-11-12, Joost asked whether C-BIOS
                  has it):** C-BIOS 0.31's own MAPXYC (its video.asm `mapxy` / `mapxy_sc3`) DOES
                  take SCREEN 3 block coordinates -- its header says "in SCREEN 3 in blocks of 4x4
                  pixels", CMASK $F0 / $0F by X's parity. Ours is not that code:
                  cbios-repack/graphics-cursor.patch replaces the whole RIGHTC..SCANL span with
                  our own entries, measured against the VG-8020 in SCREEN 2 ONLY, and so dropped
                  upstream's SCREEN 3 arm. The 2026-11-11 rebase ruling ("READ each upstream
                  version first and adopt any optimisation or fix ours lacks") named
                  graphics-cursor and this was missed. ➡️ The span gets SCREEN 3 arms written by us
                  from the measured behaviour (C-BIOS's code is ideas only, BSD-2): MAPXYC first,
                  then FETCHC / STOREC / the moves, each measured in SCREEN 3 against the VG-8020
                  -- and re-read upstream 0.31's whole span for other arms ours lacks.
                  ✅ **DONE (2026-11-12), the whole family:** [`scr3sweep_probe.py`](scratchpad/scr3sweep_probe.py) called each entry
                  in SCREEN 3 on both machines ([`scr3sweep_run.out`](scratchpad/scr3sweep_run.out): 11 SAME, 15 not -- 🔮 predicted
                  set HIT except `dc_bot`: DOWNC has no bottom stop on the VG-8020 either, only
                  TDOWNC). The VG-8020's SCREEN 3: RIGHTC / LEFTC step one 4x4 block (CMASK $F0 <->
                  $0F, CLOC +/- 8 on the wrap, no edge clamp); TDOWNC stops at cell row 5, not $17;
                  MAPXYC as above with A = H, BC / DE kept; SETC writes ATRBYT into the nibble under
                  CMASK, A = the new byte; READC returns that nibble; NSETCX leaves the cursor PAST
                  the run (not restored, unlike SCREEN 2), HL = 0, A = CMASK. UPC / DOWNC / TUPC
                  and the inside-cell moves already agreed (same stride as SCREEN 2). F after
                  RIGHTC / LEFTC is the AND flags of the new CMASK in SCREEN 2 AND 3
                  ([`scr3sweep_run3.out`](scratchpad/scr3sweep_run3.out), never captured before). ➡️ cbios-repack/graphics-cursor.patch
                  gained SCREEN 3 arms written by us (an `is_sc3` test; RIGHTC / LEFTC rotate four
                  times, whose last carry is the wrap) and an `and a` on the moves' exit: **95 B**,
                  which C-BIOS gap 1 had as fill ($0981-$09D8, 88 B) plus 7 of island 3's 8 unused
                  bytes -- island 3 (fperr_to_err, 13 B) now starts at $09E0 (basic/islands.asm,
                  tools/build_mainrom.py ISLAND_RANGES, z80flow). **After: [`scr3sweep_run4.out`](scratchpad/scr3sweep_run4.out) 30 / 30 SAME**
                  (🔮 HIT); the 145-row biossweep ([`biossweep_sc3fix.out`](scratchpad/biossweep_sc3fix.out)) reads every SCREEN 2
                  cursor row as before. Upstream's removed notes add only that the VG-8020's
                  TUPC / TDOWNC treat MLTCGP as 0 in SCREEN 3 -- ours does too. 🔴 C-BIOS gap 1
                  is now FULL (0 B) and island 3 has 1 B spare: the PAINT helpers need room
                  elsewhere (the sub-ROM tenant plan stands). ➡️ Next: the PAINT helpers' SCREEN 3
                  rows in block coordinates (x 12, y 13).
                  - [x] **GRPPRT in SCREEN 3 is unmeasured** (it follows MAPXYC's CLOC, which now
                        means blocks there) -- 🎚️ TIER 1, one row on both machines.
                        ✅ **MEASURED AND FIXED (2026-11-12, [`grpprt3_probe.py`](scratchpad/grpprt3_probe.py)):** C-BIOS's
                        GRPPRT (upstream's too) draws in SCREEN 2 only; in SCREEN 3 zerobas drew
                        NOTHING, left GRPACX, and CR stepped 8 ([`grpprt3_run.out`](scratchpad/grpprt3_run.out)). The VG-8020's
                        BIOS entry draws in EVERY mode with the pitch from SCRMOD's bit 0 -- SCREEN 3
                        AND SCREEN 1: each font pixel a 4x4 block at (GRPACX/4, GRPACY/4), set
                        pixels in FORCLR, unset ones untouched (over $99), advance and CR 32
                        ([`grpprt3_run2.out`](scratchpad/grpprt3_run2.out) .. [`grpprt3_run4.out`](scratchpad/grpprt3_run4.out)) -- which is BASIC's own PRINT #-to-GRP:
                        tenant exactly (sub2/grpprt.asm, D-OPENGRP). ➡️ $008D now jumps to an 18 B
                        stub (basic/biosfnk.asm, the crt_rows pad, 71 -> 53 B, read 2026-11-12) that calls that tenant,
                        byte in E, registers kept. After ([`grpprt3_run5.out`](scratchpad/grpprt3_run5.out)): GRPACX / GRPACY /
                        registers SAME in SCREEN 1, 2 and 3; the glyph bytes differ only by the font
                        (C-BIOS's `A` is 70 88 88 F8 .., the VG-8020's 20 50 88 88 F8 .. -- the
                        font divergence already on file), placed on the same blocks. Gate:
                        biosregs-acceptance `grpprt1 / 2 / 3 / 3_cr` (cursor + registers) 4 / 4
                        ([`grpprt_gate1.out`](scratchpad/grpprt_gate1.out)); knife (the stub's call -> `nop`s, ROM hash moved) -> all
                        four RED ([`grpprt_knife1.out`](scratchpad/grpprt_knife1.out)). SCREEN 2's biossweep rows unchanged ([`biossweep_grpprt.out`](scratchpad/biossweep_grpprt.out),
                        the font only).

      (lifted to a top-level item on 2026-11-23: **A BASIC output file and $F37D RDRND / WRRND in one program** -- 🎚️ TIER 6 — ...)

      (lifted to a top-level item on 2026-11-23: **The NMS 1200 disk ROM beeps at boot (R0 = $55 at a cartridge's INIT); zerobas's ...)

      ✅ **CLOSED 2026-11-23.** docs/tier-status.md: 42 of 42 MSX-DOS 1 functions exercised by a gate, 0 NOT
      MEASURED; 104 of 108 BIOS calls with a direct witness, 4 RULED, 0 stubs; the disk-ROM table complete;
      tiers-md-check keeps them from drifting. The seven findings still open inside this block were lifted to
      top-level items (below), where the tier scans see them.
