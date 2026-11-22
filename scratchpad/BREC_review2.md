# docs/bdos/RECORDS.md DRAFT 2 -- review pass 2 (test writer, 2026-11-22): answered by XBREC3; FINAL

1. (CORE) SETRND's 1 vs the last record vs the size's high byte -> an empty file and a 6-record file: 1 both times.
   Constant. It writes +34 / +35 0 and leaves +36 (zerobas clears +36: D-SETRNDR36).
2. (CORE) RDSEQ past the end: CR left or set to the record count -> CR 10 on 6 records: A 1, CR 10 left.
3. (CORE, NEW) WRSEQ and RR -> after SETRND: RR 1 kept.
4. (CORE, NEW) FSIZE and +12 .. +32 -> on FOPEN's FCB: only +33 .. +35 written.
5. (CORE) +15 under WRSEQ / WRRND -> left (now stated).
6. Citations: "not the last record" (could not exclude it then; now excluded), R-BR-WORK's "SETRND $00" -> fixed.
7. Partial records, empty files, FCLOSE's F, a second DTA, page-1 DTAs, error paths, the stale-bytes reading -> [A].
No new reference behaviour: FINAL (small-call stop).
