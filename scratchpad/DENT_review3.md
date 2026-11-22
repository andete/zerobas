# GETDPB.md / DSKCHG.md DRAFT 3 -- review pass 3 (one test writer, 2026-11-22): CLEAN under the small-call stop

The reviewer checked every row-D reference record against both pages. Findings and answers (XDENT6 / XDENT7, run 1):
1. (CORE, NEW) what a FAILED read does to DSKCHG's count -> XE6 0-1 (drive A empty, two calls): both fail; it does
   not restart the count (the model's assumption, now measured). zerobas answers B 1 both times: its failed reads
   restart its count (D-DSKCHGTIME's text).
2. (CORE, COMBINATION) B $FF when C differs, or only when C is below the disk's byte -> XE7 0 (C $FA, above): B $FF,
   "differs"; F $B8 there against $38 below (the comparison's sign) -- R-DC-F now states both.
3. (CORE, COMBINATION) a later read answering from a kept byte -> needs a real swap: [A].
4. (EDGE) the $E5 fill alone -> [A]. Citations: R-GD-DPB now lists the measured blocks; GETDPB's F values listed;
   D-DSKCHGTIME's bound 97-144; D-GETDPBMEDIA's mechanism (a failed read too) -> fixed.
No unpinned behaviour left that a probe on this frame can reach: both pages FINAL (spec-method §7, small-call stop).
