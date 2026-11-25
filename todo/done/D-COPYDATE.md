- [x] **D-COPYDATE — A FILE COPIED UNDER MSX-DOS GETS THE CURRENT DATE ON ZEROBAS; THE CF-3300 KEEPS THE SOURCE'S**
      🎚️ TIER 3 — common errors (every COPY at A> dates its copy wrong; filed 2026-11-23 by D-DOSSESSION).
      🤖 **AUTONOMOUS** — probes/disk/disk_probe_dossession.py, HELLO.TXT dated 1990-05-05: after `COPY HELLO.TXT COPY1.TXT`
      the CF-3300's DIR shows COPY1 TXT 90-05-05, zerobas's 84-01-01 (scratchpad/AE_dossession_copydate.out). Predicted
      before the run: COMMAND.COM carries the source's date in the FCB and the reference's FCLOSE writes the FCB's date
      as it is, where zerobas's FCLOSE re-stamps the current date. docs/bdos/FILES.md lists "whether FCLOSE re-stamps
      the date" as unmeasured -- measure it there first (FCLOSE with an FCB date set by the program), then fix disk/.
      Every later D-DOSSESSION row diverged only through this line on screen; the disk after the session agreed.
      ✅ FIXED 2026-11-25: measured first, as filed (probes/bios/spec/xbfile5.asm, R-BF-CLOSEDATE on
      docs/bdos/FILES.md): the CF-3300 and the VG-8020 + NMS 1200 both write the FCB's OWN date (+20) and time (+22)
      into the entry at FCLOSE of a written file; every write stamps the current date into the FCB first (a date
      poked before WRSEQ is overwritten, one poked after it reaches the entry); an unwritten FCLOSE writes no date.
      The prediction scored: FCB-date-at-close ✓, unwritten close ✓, "a write leaves a poked date" ✗ (it stamps).
      zerobas already stamped the FCB on a write; its close re-stamped the clock. disk/kernel.asm close_read now
      copies the FCB's time and date into the entry cr_chkdir has just written (FAT_MBUF at FWR_DIROFF) and writes
      it back (fdir_wrback); its three exits share one `sbc a,a` (45 -> 43 B; FCLOSE's F after a written close is
      now the references' $42 too). BASIC's own close (fat_dir_update, shared with the sub ROM) is unchanged.
      D-DOSSESSION 20 / 20 (scratchpad/AE_dossession_run4.out).
