"""D-ADDR29 DAC, the USR half (Joost ruled "DAC full ... USR then finds its
argument in DAC", 2026-09-24): what does USR RETURN on the reference, and how
does zerobas's HL convention answer the same machine code?

probes/basic/basic_probe_usr.py measured the ENTRY side: the VG-8020 puts an
integer argument at DAC+2..3 with VALTYP=2 and HL pointing at DAC; zerobas puts
it in HL. This measures the RETURN side, with hand-authored stubs POKEd at
$D000 from BASIC (opcodes from the Z80 CPU User Manual; DAC $F7F6 and VALTYP
$F663 from the MSX2 Technical Handbook work-area table):

  ret    C9                              return at once
  hl99   21 63 00 C9                     LD HL,99 : RET (touches only HL)
  dac77  21 4D 00 22 F8 F7 C9            LD HL,77 : LD (DAC+2),HL : RET
  inc    2A F8 F7 23 22 F8 F7 C9         DAC+2 := DAC+2 + 1
  flt    3E 04 32 63 F6 21 41 15 22 F6 F7 21 00 00 22 F8 F7 C9
         VALTYP := 4, DAC := 41 15 00 00 (single 1.5, MSX BCD)

Each is called as USR(5), and `ret` also as USR(1.5). Diskless pair, fresh
boot per case. Clean room: typed BASIC, hand-authored stubs, screen text.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
STUBS = {
    "ret":   [0xC9],
    "hl99":  [0x21, 0x63, 0x00, 0xC9],
    "dac77": [0x21, 0x4D, 0x00, 0x22, 0xF8, 0xF7, 0xC9],
    "inc":   [0x2A, 0xF8, 0xF7, 0x23, 0x22, 0xF8, 0xF7, 0xC9],
    "flt":   [0x3E, 0x04, 0x32, 0x63, 0xF6, 0x21, 0x41, 0x15, 0x22, 0xF6, 0xF7,
              0x21, 0x00, 0x00, 0x22, 0xF8, 0xF7, 0xC9],
}
CASES = [("ret", "5"), ("hl99", "5"), ("dac77", "5"), ("inc", "5"),
         ("flt", "5"), ("ret", "1.5")]


def line(stub, arg):
    # a loop over a hex string keeps the longest stub under the 254-char buffer
    b = STUBS[stub]
    hexs = "".join(f"{v:02X}" for v in b)
    return (f'FORI=0TO{len(b) - 1}:POKE&HD000+I,VAL("&H"+MID$("{hexs}",I*2+1,2)):NEXT:'
            f"DEFUSR=&HD000:X=USR({arg}):PRINT12345;X")


def answer(raw):
    rows = [raw[r * omsx_repl.COLS:(r + 1) * omsx_repl.COLS].strip()
            for r in range(omsx_repl.ROWS)]
    hit = [r for r in rows if r.startswith("12345 ")]
    if hit:
        return hit[-1].split(None, 1)[1]
    for r in reversed(rows):
        if "error" in r.lower() or "mismatch" in r.lower() or "illegal" in r.lower():
            return r
    return None


def main():
    specs = [("direct", [line(s, a)]) for s, a in CASES]
    got = {m: [answer(r or "") for r in
               omsx_repl.run_cases(m, specs, batch=False,
                                   reset=("", "SCREEN 0", "NEW"), boot=8.0,
                                   capture="screen")]
           for m in (REF, ZB)}
    bad = 0
    for i, (s, a) in enumerate(CASES):
        r, z = got[REF][i], got[ZB][i]
        same = r is not None and r == z
        bad += not same
        print(f"{'SAME' if same else 'DIFF'} {s:6s} USR({a:3s})  ref: {r}   zb: {z}")
    print(f"\nDIFF: {bad}/{len(CASES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
