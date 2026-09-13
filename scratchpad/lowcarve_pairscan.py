import io, re, sys, collections
# The low region is everything included BEFORE the page-1 boundary marker.
main = io.open("basic/main.asm", encoding="utf-8").read().split("\n")
files, seen_p1 = [], False
for ln in main:
    m = re.search(r'include\s+"([^"]+\.(?:asm|inc))"', ln)
    if m:
        files.append(m.group(1))
LOW_END = "basic/interp.asm"          # page-1 content begins around here
low = files[:files.index(LOW_END)] if LOW_END in files else files
SIZE = {"ld": 1, "inc": 1, "dec": 1, "add": 1, "or": 1, "and": 1, "xor": 1,
        "cp": 1, "push": 1, "pop": 1, "ex": 1, "ret": 1, "rrca": 1, "rlca": 1}
def norm(line):
    t = line.split(";")[0].strip()
    if not t or t.endswith(":") or t.startswith("."):
        return None
    if re.match(r"^\w+:", t):
        t = t.split(":", 1)[1].strip()
    if not t:
        return None
    p = t.split(None, 1)
    op = p[0].lower()
    if op in ("include", "equ", "db", "dw", "ds", "org", "macro", "endm", "if", "endif"):
        return None
    return (op + " " + (p[1].replace(" ", "") if len(p) > 1 else "")).strip()
pairs = collections.Counter()
where = collections.defaultdict(list)
for f in low:
    try:
        src = io.open(f, encoding="utf-8").read().split("\n")
    except OSError:
        continue
    prev = None
    prev_lbl = False
    for i, line in enumerate(src):
        lbl = bool(re.match(r"^\w+:", line))
        n = norm(line)
        if n is None:
            prev = None
            continue
        # a label between two instructions means the pair is not always adjacent
        if prev is not None and not lbl:
            pairs[(prev, n)] += 1
            where[(prev, n)].append(f"{f}:{i+1}")
        prev = n
print("low-region files scanned:", len(low))
print("top adjacent instruction pairs (count, then the pair):")
for (a, b), n in pairs.most_common(18):
    if n < 6:
        break
    print("  %3d  %-28s %-28s  e.g. %s" % (n, a, b, where[(a, b)][0]))
