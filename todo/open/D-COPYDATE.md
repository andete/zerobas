- [ ] **D-COPYDATE — A FILE COPIED UNDER MSX-DOS GETS THE CURRENT DATE ON ZEROBAS; THE CF-3300 KEEPS THE SOURCE'S**
      🎚️ TIER 3 — common errors (every COPY at A> dates its copy wrong; filed 2026-11-23 by D-DOSSESSION).
      🤖 **AUTONOMOUS** — probes/disk/disk_probe_dossession.py, HELLO.TXT dated 1990-05-05: after `COPY HELLO.TXT COPY1.TXT`
      the CF-3300's DIR shows COPY1 TXT 90-05-05, zerobas's 84-01-01 (scratchpad/AE_dossession_copydate.out). Predicted
      before the run: COMMAND.COM carries the source's date in the FCB and the reference's FCLOSE writes the FCB's date
      as it is, where zerobas's FCLOSE re-stamps the current date. docs/bdos/FILES.md lists "whether FCLOSE re-stamps
      the date" as unmeasured -- measure it there first (FCLOSE with an FCB date set by the program), then fix disk/.
      Every later D-DOSSESSION row diverged only through this line on screen; the disk after the session agreed.
