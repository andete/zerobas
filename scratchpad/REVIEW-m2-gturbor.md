# Goldfish review (test-writer role), 2026-11-23: docs/turbor/index.md, docs/turbor/main/CHGCPU.md, docs/turbor/main/GETCPU.md, docs/turbor/main/PCMPLY.md, docs/turbor/main/PCMREC.md

**Run-file records decoded (by hand from the hex, or read from a decoded file the page links):**
- `AE_xchgcpu_tr.out`: CAP+0..+14 (INIT and END) and records 0, 1, 3, 4, 7, 9, 18, 24, 33, 34, 35, 36, 37, 38 (A1GT; A1ST spot-checked against the DIFF list). Records 2, 5, 6, 8, 10-17, 19-23, 25-32, 39 and the `@cpusnap` µs values behind the timing table were NOT decoded.
- `AE_xgetcpu_tr.out`: all 19 records (A1GT), A1ST through the DIFF list.
- `AE_xtrboot_tr.out`: the capture (+0..+3) and both SYS lines.
- `AE_xtrdram_tr.out`: all three mode records, both machines (slot state, IN $FC-$FF, IN $FE readback, write test, tag pass).
- `AE_xpcmply_tr_decoded.out` (all 37 cases), `AE_xpcmstop_tr_decoded.out` (all 15), `AE_xpcmrec_tr_decoded.out` (all 26): read as decoded. The raw `AE_xpcmply_tr.out` and `AE_xpcmstop_tr.out` were NOT opened; for xpcmrec the raw VRAM0 lines and the start of the raw CAP were read.
- `AE_xpcmcmp_tr.out`: A1ST records 0-17 decoded for the $A4 count, HL, BC and AF; the $A4 logs themselves only for records 0, 4-7, 10, 11. The A1GT CAP line was NOT decoded (it differs only at the timing bytes in the DIFF list).
- `AE_xpcmmid_tr.out`: decoded in full.
- `AE_xpcmthr_tr.out`: SYS lines only. The CAP was NOT decoded.

## 1. Rules not pinned by any measured case

1. **PCMPLY** — The Summary states the `$00 n` code as a general rule. Every [XK] case ran from RAM, in R800 DRAM mode, at rate code 0. VRAM was deliberately kept free of $00, and there is no [XK] case from the Z80 or R800 ROM mode or at rate codes 1-3. To pin it: run `10 00 05 20` from VRAM, from the Z80, and at rate code 3, and log $A4 and the elapsed time.
2. **CHGCPU** — The register list covers AF..HL', IX, IY and the slots, but not I or the interrupt mode. The evidence suggests that CHGCPU carries I across: after CHGCPU the R800 reads I = $00, but in [XG 16] and [XG 18], where R#6 was written directly, `ld a,i` in the R800 gives I = $02 (the iff words are `0102` and `0002`). To pin it: load I and IM with distinct values on the Z80, call CHGCPU($81), and read I (and test IM) on the R800, then do the same in the other direction.
3. **PCMPLY** — "STOP (with or without CTRL) ends it": STOP alone was measured only when held from entry [XS 2]. During the sound only CTRL+STOP was pressed [XM]. To pin it: an xpcmmid run with `@matrix 7 10` (STOP alone).
4. **PCMPLY** — From the Z80, the internal switch writes $A7 = $00 and then $02, and $FCB1 ends at $02 [XP 21-25, 29, 34-36]. Every Z80 case started with $FCB1 = $02, so LED bit 7 was clear. Whether the call keeps, clears or restores bit 7 is unpinned. To pin it: run in the Z80 after CHGCPU($00) from an LED-on mode ($FCB1 = $82), then log $A7 and $FCB1.
5. **CHGCPU** — A rejected A was never run from R800 ROM mode; the rejected cases start from the Z80, plus one ($83) from DRAM [XC 39]. A start in DRAM mode without the LED bit ($02) was never run. "From each of the three start modes (with and without the LED bit)" is therefore wider than the cases. To pin it: start from $81 with A = $03, $04, $41, and from $02 with A = $00, $01, $82.
6. **PCMREC** — STOP was measured only in R800 DRAM mode [XR 18-23]. The only Z80 STOP case [XR 24] was refused for its rate code before STOP could matter. To pin it: STOP and CTRL+STOP from the Z80 and from R800 ROM mode at rate code 1, and into VRAM.
7. **PCMREC** — Entry F was $00 in every case, so the return F = $44 / $45 / $01 rule rests on one entry value. It cannot be assumed to match PCMPLY's, which depends on the entry (see 2.1). To pin it: entry F = $FF, $28 and $44 on a plain recording and on a STOP case.
8. **PCMPLY** — Entry F $FF was run only in R800 DRAM mode [XP 20], and EI entry only in DRAM [XP 19]. The Z80 path's return F and interrupt state are pinned for entry F $00 / DI only. To pin it: from the Z80 with F = $FF, and once entered EI.

## 2. Rules the cases could also explain with a different rule

1. **PCMPLY** — Return F bits 5 and 3. The page pairs entry F $00 → $44 [XP 0] with entry F $FF → $6C [XP 20], which reads as "bits 5/3 follow the entry F". In every [XK] case, however, entry F was $44 (from `xor a` in xpcmcmp), with bits 5/3 clear, and PCMPLY returned F = $6C. So bits 5/3 are not a copy of the entry F. They may follow entry F bit 6 / bit 2, or another entry register (A was $01 in XP 20 and $00 in XK). To separate the rules: entry F = $40, $04 and $28 with A = 0 and the other inputs as in XP 0.
2. **CHGCPU** — The accept rule. The page says "A AND $7F is 0, 1 or 2". Bits 3, 4 and 5 were never set without bit 2 or bit 6 also set ($7E, $FD, $FF), so "reject when bit 2 or bit 6 is set, or the mode is 3" fits every case too. To separate them: A = $08, $10, $20 and $88.
3. **GETCPU** — R800 flag bits 5/3 "follow the entry F". Cases 6-8 change A and F together ($FF / $FF). [XG 0-5] (A = $A7, F = $00, result bit 5 clear) rule out "bit 5 from A alone", but they do not rule out bit 3 coming from A ($A7 has bit 3 clear) or "A AND F". To separate them: A = $00 with F = $FF, and A = $FF with F = $00, in both R800 modes.
4. **GETCPU / CHGCPU** — "Only CHGCPU hands the running program across" versus "each CPU resumes exactly where it last stopped, and CHGCPU works because both CPUs stop inside it". [XG 16] is a normal record after a *direct* Z80→R800 write, because the R800 had last stopped inside case 15's setup CHGCPU($80). In [XG 17] the Z80 most likely resumed after case 16's identical OUT, and that cannot be told apart from continuing after case 17's OUT, because the probe takes every input from RAM. The second rule explains all three records; the page's rule does not explain XG 16. To separate them: increment a RAM pass counter between the direct OUT and the next instruction, or record SP / a marker per pass.
5. **CHGCPU** — $FFFD "= SP − $18 (one SP)" [A] versus "a fixed value". The evidence the page already links rules out a fixed value, but the page does not cite it. PCMPLY's internal switch from the Z80, with a deeper stack, leaves $E7D8 [XP 21-25, 29, 34-36]. At [XC INIT], after the boot's own CHGCPU calls, the cell holds $F054 (CAP+4/+5). Neither of these pins the offset against a known caller SP. To pin it: call with SP = $E000 and $D000.
6. **PCMPLY** — After an abort, "D:BC = the samples left" versus "the bytes left". [XM] played $55 data with no $00 pairs, so the two counts coincide. To separate them: CTRL+STOP pressed during a long `$00 $00` run in the data.
7. **PCMREC** — "n + 5 conversions; whether the first five are discarded or the last [A]." The $A5 log already splits them differently: four conversions with `18 08`, then n + 1 with `1C 0C` (n = 1: 4 + 2 [XR 12]; n = 16: 4 + 17 [XR 0]). A STOP held at entry ends after exactly the four `18 08` conversions [XR 18]. The data therefore fit "4 warm-up conversions + 1 extra of the storing kind" better than "5 first" or "5 last". Which of the n + 1 is dropped needs a real input.
8. **PCMREC** — "Return … DE = 0". D = E = 0 on entry in every case, so the data equally fit "DE kept". To separate them: D = E = $FE in RAM (PCMPLY keeps DE in RAM [XP 30]).

## 3. Citations that do not match the tables

1. **index** — The table lists PCMPLY and PCMREC as "DRAFT 0", but both pages head themselves "DRAFT 1 (2026-11-23)".
2. **CHGCPU** — Open says the accept rule "is measured on the 17 values above only". The cases hold 15 distinct A values: $00, $01, $02, $80, $81, $82 accepted, and $03, $83, $04, $05, $06, $41, $7E, $FD, $FF rejected.
3. **CHGCPU** — The boot paragraph cites "GETCPU 00 [XC INIT]". XC INIT records R#6, $FCB1, $A7, ($FFFD) and a cpusnap, not GETCPU; only [XB] has GETCPU. The same record's ($FFFD) = $F054 is not reported.
4. **CHGCPU** — "at cartridge INIT the registers hold 3, 2, 1, 0 [XD]": xtrdram reads IN $FC-$FF only after its CHGCPU($82/$81/$80), never at INIT before a call.
5. **CHGCPU** — The Summary says the boot "ends in R800 DRAM mode with the LED on". The body and [XB] show only $FCB1 bit 7 set, and the page's own Open says the LED state was not read.
6. **PCMPLY** — "FS-A1GT vs FS-A1ST: none in any output of any case … beyond timing". IN $A4 after the call differs between the models in [XP 8] (02/03), [XP 24] (01/00), [XP 35] (01/00), [XP 36] (00/01) and [XS 7, 8, 10, 11, 12]. The page never says what IN $A4 reads, although the Evidence list names it.
7. **PCMREC** — The same claim of "none in any output" conflicts with IN $A4 after the call in [XR 14] (03 / 00).
8. **PCMPLY** — The Summary says "With A = $08 and no key pressed the call plays one sample". The single OUT $A4,$80 came from a run that was not kept, and it matches the leading framing $80 that the page describes as preceding every play, not a data sample. The kept run [XS 14] has no OUT log for the hung case.
9. **PCMREC** — "(IN $A5 reads $83 before and after)": xpcmrec's record has IN $A5 only after the call (+54). "Before" is from xpcmply (+109), not from [XR].
10. **PCMREC** — [XR 24] is cited as "Z80 with A = $04 … the same" without saying that CTRL+STOP was held. That case is the only evidence that the rate-code refusal (A = 1) takes precedence over STOP (A = 2).

## 4. Gaps in the open lists

1. **CHGCPU** — Open does not list the I register or the interrupt mode across the switch. GETCPU's records show the R800's own I = $02 when CHGCPU did not do the switch (see 1.2).
2. **GETCPU** — Neither the Result nor Open mentions I = $02 in [XG 16, 18]. The run-on paragraph does not explain why [XG 16], a direct write, gave a normal record (see 2.4).
3. **PCMPLY** — Open lacks:
   - the $00 code from VRAM, from the Z80 or R800 ROM mode, and at rate codes 1-3;
   - what IN $A4 reads;
   - the Z80 path with $FCB1 bit 7 set;
   - STOP alone during the sound;
   - return F for other entry F values;
   - an abort inside a $00 run.
4. **PCMREC** — Open lacks:
   - STOP from the Z80 / R800 ROM mode / into VRAM;
   - DE on return with non-zero D / E;
   - Z80-mode time per sample ([XR 11, 16, 17] were run but not analysed);
   - what IN $A4 reads (it varies per machine);
   - the four `18 08` + n + 1 `1C 0C` split as the starting point for "which conversions are discarded";
   - the control case [XT 0], which was run but is not cited.
5. **CHGCPU** — Open lacks the rejected-A cases from R800 ROM mode and the DRAM start without the LED bit (see 1.5). It also lacks the bit-3/4/5-alone values (see 2.2): "A values not run" names neither the specific values nor the reason they matter.
6. **index** — The "Work area / found by measurement" list omits the CPU-private register state (the R800's own I) that GETCPU's records expose. It also gives no pointer to the PCMPLY-side $FFFD evidence ($E7D8) beside CHGCPU's.
