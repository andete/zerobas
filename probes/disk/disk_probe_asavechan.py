# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ASAVECHAN (gate: asavechan-acceptance): a disk write BESIDE an open OUTPUT
channel leaves that channel's file intact, as on the CF-3300.

    OPEN"P1.TXT"FOR OUTPUT AS#1 : PRINT#1,"AAA" : <verb> : PRINT#1,"BBB" : CLOSE#1

with <verb> each of `SAVE"Q.BAS",A`, `BSAVE"Q.BAS",&H8000,&H800F`, `SAVE"Q.BAS"`
and `BLOAD"PROG.BIN"`, each on a fresh test720 copy -- and the INPUT side:
an open HI.TXT read 5 bytes, then BLOAD or SAVE ,A, then the rest, printed. Read back from the IMAGE (bytes
the machine wrote):
  - P1.TXT's size and content must equal the CF-3300's
    (`AAA\\r\\nBBB\\r\\n` + Ctrl-Z, 11 B);
  - Q.BAS's size must equal it;
  - its content must equal it too, except BSAVE's data bytes, which are each
    machine's own RAM at &H8000 -- for BSAVE only the 7-byte header is compared.
Cluster NUMBERS are not compared. Ours flushes the channel's partial sector when
it parks it, so P1 takes cluster 9 and Q 10 where the CF-3300, which commits
lazily, has them the other way round.

🔴 Before D-ASAVECHAN, main's SAVE ,A and the BSAVE tenant streamed through the
SAME engine globals the live OUTPUT channel lives in. P1.TXT came back EMPTY
(0 B, no cluster) and its post-SAVE bytes were counted into Q.BAS (21 and 29 B
for 15 and 23). There was no error anywhere. Tokenised SAVE was already safe,
because it crosses through chan_gate. KNIFED: without the two `fch_claim` parks
the asave and bsave faces FAIL.

Exit 0 all agree; 1 a divergence; 2 the CF-3300 gave no reading.
"""
import os, re, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402
import disk_probe_wrblk_roundtrip as RT             # noqa: E402

VERBS = {"asave": 'SAVE"Q.BAS",A', "bsave": 'BSAVE"Q.BAS",&H8000,&H800F',
         "save": 'SAVE"Q.BAS"', "bload": 'BLOAD"PROG.BIN"'}
# the INPUT side: an open INPUT channel read 5 bytes, <verb>, then the rest
IN_VERBS = {"in_bload": 'BLOAD"PROG.BIN"', "in_asave": 'SAVE"Q.BAS",A'}


def prog(verb):
    return ["NEW", "10 REM HELLO", 'OPEN"P1.TXT"FOR OUTPUT AS#1', 'PRINT#1,"AAA"',
            verb, 'PRINT#1,"BBB"', "CLOSE#1"]


def prog_in(verb):
    return ["NEW", "10 REM HELLO", 'OPEN"HI.TXT"FOR INPUT AS#1', "A1$=INPUT$(5,#1)",
            verb, "A2$=INPUT$(LOF(1)-5,#1)", "CLOSE#1", 'PRINT"R";A1$;"|";A2$;"#"']


def file_of(path, stem, ext):
    ent = RT.Fat12(path).dirent(stem, ext)
    if not ent:
        return None, None
    if not ent.get("cluster"):
        return ent["size"], b""
    img = open(path, "rb").read()
    off = 14 * 512 + (ent["cluster"] - 2) * 1024   # test720: data at sector 14, 2 s/c
    return ent["size"], img[off:off + min(ent["size"], 1024)]


def main():
    got = {}
    for tag, machine in (("STOCK", RT.REF_MACHINE), ("OURS", RT.OUR_MACHINE)):
        for name, verb in VERBS.items():
            dsk = probe_tmp.tmp(f"asavechan_{name}_{tag}.dsk")
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
            omsx_repl.run_cases(machine, [("direct", prog(verb))], batch=False,
                                reset=("", "SCREEN 0"), boot=14.0, step=3.0, diska=dsk)
            p1 = file_of(dsk, "P1", "TXT")
            q = file_of(dsk, "Q", "BAS")
            got[(tag, name)] = (p1, q)
            print(f"== {tag} {name}: P1.TXT {p1[0]} B {p1[1]!r}  Q.BAS {q[0]} B")
        for name, verb in IN_VERBS.items():
            dsk = probe_tmp.tmp(f"asavechan_{name}_{tag}.dsk")
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
            raw = omsx_repl.run_cases(machine, [("direct", prog_in(verb))], batch=False,
                                      reset=("", "SCREEN 0"), boot=14.0, step=3.0,
                                      diska=dsk)[0] or ""
            # quoted text is the echoed SOURCE, never output (the echo fence)
            m = re.findall(r"\bR([^#]*)#", re.sub(r'"[^"\n]*"', "", re.sub(r"\s+", " ", raw)))
            got[(tag, name)] = m[-1] if m else None
            print(f"== {tag} {name}: read {got[(tag, name)]!r}")
    if any(got[("STOCK", n)][0][0] is None for n in VERBS):
        print("\nINSTRUMENT FAULT: the CF-3300 left no P1.TXT -- no reference")
        return 2
    bad = []
    for name in VERBS:
        (sp1, sq), (op1, oq) = got[("STOCK", name)], got[("OURS", name)]
        if sp1 != op1:
            bad.append(f"{name}: P1.TXT CF-3300 {sp1} vs ours {op1}")
        if sq[0] != oq[0]:
            bad.append(f"{name}: Q.BAS size CF-3300 {sq[0]} vs ours {oq[0]}")
        cut = 7 if name == "bsave" else None        # BSAVE's data is machine RAM
        if (sq[1] or b"")[:cut] != (oq[1] or b"")[:cut]:
            bad.append(f"{name}: Q.BAS content CF-3300 {sq[1]!r} vs ours {oq[1]!r}")
    for name in IN_VERBS:
        if got[("STOCK", name)] is None:
            print(f"\nINSTRUMENT FAULT: the CF-3300 read nothing for {name} -- no reference")
            return 2
        if got[("STOCK", name)] != got[("OURS", name)]:
            bad.append(f"{name}: read CF-3300 {got[('STOCK', name)]!r} vs ours {got[('OURS', name)]!r}")
    for b in bad:
        print("DIVERGES " + b)
    print(f"\n{'PASS' if not bad else 'FAIL'}: a disk write beside an open OUTPUT channel leaves it intact, and an INPUT one in place")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
