"""Decode scratchpad/padtrace_run.out (D-PADTRACE): each PAD(0) call's port trace
-> its uPD7001 FRAMES, each with the DI level clocked in and the 8-bit value read
off SO, MSB first. Port 1's lines, as the trace itself shows them:

  R15 (written): b0 = SCK (8D <-> 8C), b1 = DI (0 in 8D/8C frames, 1 in 8F/8E),
                 b4 = /CS (9x = deselected, 8x = selected)
  R14 (read):    b0 = pen contact (low = touched), b1 = end of conversion (the
                 busy-wait polls it), b2 = SO (the data bit), b3 = the pen SWITCH

A frame is a run of clock pulses between two deselects; the bit is the R14 read
that follows each SCK-low write.

    python3 scratchpad/padtrace_decode.py [scratchpad/padtrace_raw.txt]
"""
import collections, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def frames(trace):
    toks = trace.split()
    out, bits, di, reg15 = [], None, None, None
    pending_bit = False
    for t in toks:
        m = re.match(r"W15=([0-9A-F]{2})", t)
        if m:
            v = int(m.group(1), 16)
            if v & 0x10:                      # /CS high: a frame ends
                if bits:
                    out.append((di, bits))
                bits, pending_bit = None, False
            else:
                if bits is None:
                    bits = []
                di = (v >> 1) & 1
                pending_bit = not (v & 1)     # SCK low -> the next R14 read is a bit
            continue
        m = re.match(r"R14=([0-9A-F]{2})", t)
        if m and pending_bit and bits is not None:
            bits.append((int(m.group(1), 16) >> 2) & 1)
            pending_bit = False
    return [(d, int("".join(map(str, b)), 2) if len(b) == 8 else f"{len(b)}bits:{b}")
            for d, b in out]


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "padtrace_raw.txt")
    seen = collections.Counter()
    last = {}
    for line in open(path):
        m = re.match(r"(\d+) PAD\((\d)\) (.*)", line.rstrip("\n"))
        if not m or m.group(2) != "0":
            continue
        f = tuple(frames(m.group(3)))
        seen[f] += 1
        last[f] = int(m.group(1))
    print("PAD(0) frame sequences [(DI, value), ...], by count (last seen ms):")
    for f, n in seen.most_common():
        print(f"  {n:4}x  {list(f)}   last {last[f]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
