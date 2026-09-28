"""What does CSAVE write AFTER the program's $0000 end-link? (D-CSAVETAIL)

castail's fixture comment says both references HANG loading a tokenised file
with no trailing $00 pad ("the loader needs the pad to frame the final byte")
and that the pad-less form is "what our own CSAVE writes". If both are true, a
tape CSAVEd on zerobas never loads on a real MSX. Nothing measured the
reference's own tail: tape_save's oracle 2 loads a SYNTHESISED padded tape and
reads memory at 35 s, not the prompt.

This records `CSAVE"PC"` on each side (cassave's recorder: a fresh
`cassetteplayer new` WAV per side, decoded by cas_decode) and prints the decoded
stream from the program's REM text to the end: the bytes after the end-link are
the answer. Outputs only -- the recording is what the machine WROTE.
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "probes", "lib"),
                os.path.join(HERE, "..", "probes", "basic")]
import cas_decode  # noqa: E402
import omsx_repl  # noqa: E402
import basic_probe_cassave as cs  # noqa: E402


def main():
    for side in (sys.argv[1:] or ["vg8020", "zb", "cf3300"]):
        cfg = cs.SIDES[side]
        kw = {}
        if cfg["diska"]:
            kw["diska"] = cs.probe_tmp.tmp(f"zb_csavetail_{side}.dsk")
            import shutil
            shutil.copy(cs.TEST_DSK, kw["diska"])
        wav = os.path.join(tempfile.mkdtemp(prefix=f"zb_csavetail_{side}_"), "c.wav")
        lines = list(cfg["reset"]) + list(cs.PROG) + ['CSAVE"PC"', cs.W_SAVE,
                                                      f'PRINT"{cs.ALIVE}"']
        omsx_repl.run_cases(cfg["machine"], [("direct", lines)], batch=False,
                            reset=(), boot=cfg["boot"], step=cfg["step"],
                            prologue=(f"cassetteplayer new {{{wav}}}",), **kw)
        if not os.path.exists(wav):
            print(f"{side:7} <NO TAPE>")
            continue
        blob = bytes(cas_decode.decode_file(wav)[0])
        h = blob.find(bytes([0xD3] * 10))
        z = blob.find(b"ZQ9", h)
        tail = blob[z:] if z >= 0 else blob[-40:]
        # the end-link is the $00 $00 $00 after the last line's terminator
        end = tail.find(b"\x00\x00\x00")
        after = tail[end + 3:] if end >= 0 else b""
        print(f"{side:7} header@{h} total={len(blob)} from-ZQ9: {tail.hex(' ')}")
        print(f"{side:7} after end-link: {len(after)} byte(s), "
              f"nonzero={sum(1 for b in after if b)}")


if __name__ == "__main__":
    main()
