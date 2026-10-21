#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-DISKRUN (2026-10-21, Joost: a disk test run like the earlier tape run): boot
every image of a disk COLLECTION on the National CF-3300 (the MSX1 disk reference)
and on zerobas's disk machine, and compare what is on screen.

Black box only. Each image is COPIED to a fresh /tmp directory first (the run writes
nothing back to the collection), booted with `-diska`, run with the throttle off,
and at each capture time the probe reads VRAM (16 KB), the VDP registers and the
PC. Nothing in an image is decoded or disassembled -- the software is RUN.
🔒 The collection's location is never written into this repo: pass it with
DISKCORPUS_DIR, or --dir. Joost, 2026-10-20: the private `my_disks` folder is NOT
test data -- this tool refuses a directory of that name.

  per image:  ref / zb  VRAM sha  screen mode  PC  ->  class
    SAME      VRAM byte-identical at the last capture
    NEAR      < 128 VRAM bytes apart (an animation phase, a clock digit)
    DIFF      both show something, far apart
    REF-BLANK the CF-3300 shows only its own boot screen state at every capture
              (MSX2-only software, an unbootable image, a data disk) -- not ours
    ZB-ONLY   zerobas shows something the CF-3300 does not (rare; read it)
    ERROR     a machine did not run

    DISKCORPUS_DIR=... python3 -u scratchpad/diskcorpus_run.py [--limit N] [--only SUBSTR]
        [--times 20,45] [--out /tmp/diskcorpus.json]
"""
import argparse, hashlib, json, os, shutil, signal, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_preflight  # noqa: E402

OMSX = os.environ.get("OPENMSX", shutil.which("openmsx") or "/opt/homebrew/bin/openmsx")
REF, ZB = "National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK"
EXTS = (".dsk", ".di1", ".di2", ".xsa")


def run_one(machine: str, image: str, times: list[float], typed: str | None = None) -> dict | None:
    td = tempfile.mkdtemp(prefix="dcorp_")
    ext = os.path.splitext(image)[1].lower()
    dsk = os.path.join(td, "d" + (".xsa" if ext == ".xsa" else ".dsk"))
    shutil.copy(image, dsk)
    out = os.path.join(td, "cap.txt")
    lines = ["set throttle off",
             "proc __cap {tag} {",
             f"  set f [open {{{out}}} a]",
             "  binary scan [debug read_block VRAM 0 16384] H* v",
             "  set r {}",
             "  for {set i 0} {$i < 8} {incr i} { lappend r [vdpreg $i] }",
             "  binary scan [debug read_block memory 0xF41C 2] H* cl",
             "  puts $f \"$tag [reg pc] $r $cl $v\"",
             "  close $f",
             "}"]
    for k, t in enumerate(times):
        lines.append(f"after time {t} {{ __cap T{int(t)} }}")
    end = times[-1] + 0.5
    if typed:
        # after the last capture, type a command at whatever is on screen and capture
        # again 6 s later (tag F): FILES at a BASIC prompt is the Disk BASIC check
        lines.append(f'after time {times[-1] + 0.2} {{ type "{typed}\\r" }}')
        lines.append(f"after time {times[-1] + 6.0} {{ __cap F }}")
        end = times[-1] + 6.5
    lines.append(f"after time {end} {{ exit }}")
    tcl = os.path.join(td, "s.tcl")
    open(tcl, "w").write("\n".join(lines) + "\n")
    cmd = [OMSX, "-machine", machine, "-diska", dsk, "-command",
           "set renderer none; set sound_driver null", "-script", tcl]
    try:
        proc = subprocess.Popen(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
        deadline = time.time() + 30 + times[-1] * 2
        while proc.poll() is None and time.time() < deadline:
            time.sleep(0.2)
        if proc.poll() is None:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            time.sleep(1)
            if proc.poll() is None:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        caps = {}
        if os.path.exists(out):
            for ln in open(out):
                p = ln.split()
                tag, pc, regs, cl, v = p[0], int(p[1]), [int(x) for x in p[2:10]], p[10], p[11]
                curlin = int(cl[2:4] + cl[0:2], 16)
                caps[tag] = {"pc": pc, "regs": regs, "curlin": curlin, "vram": bytes.fromhex(v)}
        return caps or None
    finally:
        shutil.rmtree(td, ignore_errors=True)


def mode_of(regs):
    m1, m2, m3 = (regs[1] >> 4) & 1, (regs[1] >> 3) & 1, (regs[0] >> 1) & 1
    return {(1, 0, 0): "S0", (0, 0, 0): "S1", (0, 0, 1): "S2", (0, 1, 0): "S3"}.get((m1, m2, m3), "?")


def screen_text(cap) -> list[str]:
    """The text rows of a SCREEN 0 / 1 capture (name table, 7-bit ASCII), blank rows
    dropped; [] for a graphics mode."""
    r, v = cap["regs"], cap["vram"]
    mode = mode_of(r)
    if mode not in ("S0", "S1"):
        return []
    nt, w = (r[2] & 0x0F) * 0x400, (40 if mode == "S0" else 32)
    rows = []
    for row in range(24):
        line = "".join(chr(b) if 32 <= b < 127 else " " for b in v[nt + row * w: nt + row * w + w])
        if line.strip():
            rows.append(line.rstrip())
    return rows


def state_of(cap) -> str:
    """RUNNING: a BASIC program is executing (the published CURLIN, $F41C, is not
    $FFFF -- both machines keep it there), or the PC is in RAM, or the screen is a
    graphics mode: the disk's own program has the machine. PROMPT: direct mode, text
    screen. 🔴 The PC alone cannot tell: a BASIC program runs in the ROM interpreter
    and waits for a key in the BIOS exactly as the prompt does (BREAKER, smoke run)."""
    if (cap["curlin"] != 0xFFFF or cap["pc"] >= 0x8000
            or mode_of(cap["regs"]) not in ("S0", "S1")):
        return "RUNNING"
    return "PROMPT"


def files_listed(cap) -> list[str]:
    """The 8.3 names a FILES listing put on screen, normalised (`NAME    .EXT`
    -> NAME.EXT), in screen order."""
    import re
    names = []
    for line in screen_text(cap):
        for m in re.finditer(r"([A-Z0-9_$#&!%'()@^{}~-]{1,8})\s*\.\s*([A-Z0-9_$#&!%'()@^{}~-]{0,3})", line):
            names.append(f"{m.group(1)}.{m.group(2)}")
    return names


def classify(ref, zb):
    if not ref or not zb:
        return "ERROR", None
    last = sorted(t for t in ref if t != "F")[-1]
    if last not in zb:
        return "ERROR", None
    sr, sz = state_of(ref[last]), state_of(zb[last])
    if sr == "RUNNING" and sz == "RUNNING":
        apart = sum(1 for x, y in zip(ref[last]["vram"], zb[last]["vram"]) if x != y)
        return "BOTH-RUN", apart
    if sr == "RUNNING":
        return "ZB-NOBOOT", None          # the reference runs the disk, we sit at a prompt
    if sz == "RUNNING":
        return "ZB-ONLY", None
    if "F" not in ref or "F" not in zb:
        return "PROMPT-NOFILES", None
    fr, fz = files_listed(ref["F"]), files_listed(zb["F"])
    if not fr and not fz:
        return "FILES-EMPTY", None
    return ("FILES-SAME" if fr == fz else "FILES-DIFF"), (len(fr), len(fz))


def summary_state(curlin, pc, mode) -> str:
    """state_of, from a stored row's summary fields instead of a capture."""
    if curlin != 0xFFFF or pc >= 0x8000 or mode not in ("S0", "S1"):
        return "RUNNING"
    return "PROMPT"


def rerun_zb(a, names, times) -> int:
    """--reuse-ref: zerobas only, classified against the previous run's reference
    summary (state from CURLIN / PC / mode, FILES from its listing)."""
    prev = {r["image"]: r for r in json.load(open(a.reuse_ref))["results"]}
    want = {c for c in a.classes.split(",") if c}
    rows, tally = [], {}
    for i, n in enumerate(names, 1):
        old = prev.get(n)
        if old is None or (want and old["class"] not in want):
            continue
        zb = run_one(ZB, os.path.join(a.dir, n), times, typed="FILES")
        last = sorted(t for t in (zb or {}) if t != "F")[-1] if zb else None
        if not zb or last is None:
            cls = "ERROR"
        else:
            sr = summary_state(old["ref_curlin"], old["ref_pc"], old["ref_mode"])
            sz = state_of(zb[last])
            if sr == "RUNNING" and sz == "RUNNING":
                cls = "BOTH-RUN"
            elif sr == "RUNNING":
                cls = "ZB-NOBOOT"
            elif sz == "RUNNING":
                cls = "ZB-ONLY"
            else:
                fr, fz = old["ref_files"] or [], files_listed(zb["F"]) if "F" in zb else []
                cls = ("FILES-EMPTY" if not fr and not fz
                       else "FILES-SAME" if fr == fz else "FILES-DIFF")
        tally[cls] = tally.get(cls, 0) + 1
        row = {"image": n, "class": cls, "was": old["class"],
               "zb_mode": mode_of(zb[last]["regs"]) if last else None,
               "zb_pc": zb[last]["pc"] if last else None,
               "zb_curlin": zb[last]["curlin"] if last else None,
               "zb_files": files_listed(zb["F"]) if zb and "F" in zb else None,
               "zb_text": screen_text(zb[last]) if last else None}
        rows.append(row)
        print(f"[{i:3d}/{len(names)}] {old['class']:10s} -> {cls:10s} zb {row['zb_mode']} "
              f"pc={row['zb_pc']!s:>5s} curlin={row['zb_curlin']!s:>5s}  {n}", flush=True)
        json.dump({"times": times, "reuse_ref": a.reuse_ref, "results": rows, "tally": tally},
                  open(a.out, "w"), indent=1)
    print("TALLY", json.dumps(tally, sort_keys=True))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.environ.get("DISKCORPUS_DIR"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="")
    ap.add_argument("--times", default="20,45")
    ap.add_argument("--out", default="/tmp/diskcorpus.json")
    ap.add_argument("--resume", action="store_true", help="keep --out's rows, run the rest")
    ap.add_argument("--reuse-ref", metavar="PREV_JSON",
                    help="run ZEROBAS ONLY, against the reference rows a previous --out holds "
                         "(the reference does not change between zerobas fixes)")
    ap.add_argument("--classes", default="",
                    help="with --reuse-ref: only the images whose PREVIOUS class is in this "
                         "comma list (e.g. ZB-NOBOOT,ZB-ONLY,FILES-DIFF,FILES-EMPTY)")
    a = ap.parse_args()
    if not a.dir or not os.path.isdir(a.dir):
        sys.exit("give the collection with DISKCORPUS_DIR or --dir")
    if os.path.basename(os.path.normpath(a.dir)).lower() == "my_disks":
        sys.exit("REFUSED: my_disks is private, not test data (Joost, 2026-10-20)")
    times = [float(x) for x in a.times.split(",")]
    names = sorted(n for n in os.listdir(a.dir) if os.path.splitext(n)[1].lower() in EXTS
                   and os.path.isfile(os.path.join(a.dir, n))   # a DIRECTORY named *.dsk
                   and a.only.lower() in n.lower())             # exists in the wild
    if a.limit:
        names = names[:a.limit]
    results, tally = [], {}
    if a.reuse_ref:
        return rerun_zb(a, names, times)
    if a.resume and os.path.exists(a.out):
        prev = json.load(open(a.out))
        results = prev["results"]
        for r in results:
            tally[r["class"]] = tally.get(r["class"], 0) + 1
    done = {r["image"] for r in results}
    for i, n in enumerate(names, 1):
        if n in done:
            continue
        img = os.path.join(a.dir, n)
        ref = run_one(REF, img, times, typed="FILES")
        zb = run_one(ZB, img, times, typed="FILES")
        cls, apart = classify(ref, zb)
        tally[cls] = tally.get(cls, 0) + 1
        last = sorted(t for t in ref if t != "F")[-1] if ref else None
        row = {"image": n, "class": cls, "apart": apart,
               "ref_mode": mode_of(ref[last]["regs"]) if ref else None,
               "zb_mode": mode_of(zb[last]["regs"]) if zb and last in zb else None,
               "ref_pc": ref[last]["pc"] if ref else None,
               "zb_pc": zb[last]["pc"] if zb and last in zb else None,
               "ref_curlin": ref[last]["curlin"] if ref else None,
               "zb_curlin": zb[last]["curlin"] if zb and last in zb else None,
               "ref_sha": hashlib.sha1(ref[last]["vram"]).hexdigest()[:10] if ref else None,
               "zb_sha": hashlib.sha1(zb[last]["vram"]).hexdigest()[:10] if zb and last in zb else None,
               "ref_files": files_listed(ref["F"]) if ref and "F" in ref else None,
               "zb_files": files_listed(zb["F"]) if zb and "F" in zb else None,
               "ref_text": screen_text(ref[last]) if ref else None,
               "zb_text": screen_text(zb[last]) if zb and last in zb else None}
        results.append(row)
        print(f"[{i:3d}/{len(names)}] {cls:9s} {str(apart):>6s}  ref {row['ref_mode']} "
              f"pc={row['ref_pc']!s:>5s}  zb {row['zb_mode']} pc={row['zb_pc']!s:>5s}  {n}",
              flush=True)
        json.dump({"times": times, "results": results, "tally": tally}, open(a.out, "w"), indent=1)
    print("TALLY", json.dumps(tally, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
