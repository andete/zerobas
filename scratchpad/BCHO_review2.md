# docs/disk/CHOICE.md DRAFT 2 -- review pass 2 (test writer, 2026-11-22)

1.1 (CORE) "keeps every other register" though IX / IY / the alternates / SP are not recorded -> the claim scoped
    to AF, BC, DE (the registers recorded); the rest [A] (CALSLT takes IX / IY as inputs).
1.2 (CORE) the pointer only range-checked; a RDSLT text check suggested -> any read of the reference's bytes at
    HL is reading ROM bytes, which the clean room forbids (pass / fail included). [A], the reason kept.
2.1 - 2.3 (EDGE) zero entry values after the read, CHOICE only after MTOFF, MTOFF's C = DSKIO's C -> [A].
3.1 D-PHYDIOREGS over-listed (B and DE agree) -> "F and HL".
3.2 "MTOFF and CHOICE (the motor running)" -> CHOICE ran after MTOFF; said so.
3.3 the NMS 1200's values stated as rule content but not checked -> "recorded, not checked".
4.1 "a formatted disk" was measured -> replaced with no disk / unformatted / other media.
4.2 - 4.4 -> Open.
STOP: no measurable new behaviour -> FINAL (small-call rule, docs/spec-method.md §7).
