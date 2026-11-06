#!/usr/bin/env python3
"""D-COPYWILD follow-up: what does a MULTI-MATCH wildcard COPY do on the CF-3300?

MEASURES ONLY (reference machine National_CF-3300 under openMSX). One boot per
case on a PRIVATE copy of disk/test720.dsk; the case's lines are injected into
KEYBUF (omsx_repl.key_proc), then the SCREEN is dumped repeatedly over the watch
period (so a long-running COPY is seen running, not just missed), the host-side
image is hashed on the wall clock (does the drive still WRITE?), and the image's
root directory is read back from the host at the end. At the end of the watch a
bare Enter is injected ("poke") and the screen dumped again -- separates a KEY
WAIT from a hang.

🔴 WHY THIS EXISTS: scratchpad/copywild_probe.py captured exactly `step` (8 s)
after RUN; its COPYWILD_GAP raised `cap_gap`, which is the gap AFTER the
capture and buys the case nothing (omsx_repl._tcl). So "no reading at 20-240 s"
was never measured at 20-240 s.

    python3 -u scratchpad/copymulti_probe.py [--watch 120] [--out DIR] case ...
    python3 -u scratchpad/copymulti_probe.py --list
"""
from __future__ import annotations
import argparse, hashlib, os, shutil, struct, subprocess, sys, tempfile, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl, omsx_preflight  # noqa: E402
from omsx_run import find_omsx  # noqa: E402

FIXTURE = os.path.join(REPO, "disk", "test720.dsk")
MACHINE = "National_CF-3300"
BOOT = 14.0          # CF-3300 + disk: date question at boot
STEP = 8.0           # inter-line spacing (Disk BASIC is slow to echo)
MAXD = omsx_repl.MAX_DIRECT
OBS = (2, 5, 10, 15, 20, 30, 45, 60, 90, 120, 180, 240, 300, 420, 600)
DENSE = tuple(x / 2 for x in range(1, 61)) + OBS[6:]      # every 0.5 s to 30 s, then OBS

FENCE = 'PRINT CHR$(91);"DONE]":END'
ERRL = '90 PRINT CHR$(91);"E";ERR;ERL;"]":END'
MK1 = 'OPEN "A1.TXT" FOR OUTPUT AS #1:PRINT #1,"X1":CLOSE'
MK2 = 'OPEN "A2.TXT" FOR OUTPUT AS #1:PRINT #1,"X2":CLOSE'
MK3 = 'OPEN "A3.TXT" FOR OUTPUT AS #1:PRINT #1,"X3":CLOSE'


def prog(copy, onerr=True, pre=(), post=()):
    out = ["NEW"]
    if onerr:
        out.append("10 ON ERROR GOTO 90")
    n = 20
    for p in pre:
        out.append(f"{n} {p}"); n += 10
    out.append(f"{n} {copy}"); n += 10
    for p in post:
        out.append(f"{n} {p}"); n += 10
    out.append(f"{n} {FENCE}")
    if onerr:
        out.append(ERRL)
    out.append("RUN")
    return out


CASES = {
    # --- Q1/Q2: fixture vs fresh, prompt vs program vs ON ERROR program ------
    "fx_prompt_star":  ['COPY "PROG*.BAS" TO "Q*.BAS"'],
    "fx_prog_star":    prog('COPY "PROG*.BAS" TO "Q*.BAS"', onerr=False),
    "fx_onerr_star":   prog('COPY "PROG*.BAS" TO "Q*.BAS"'),
    "fr_prompt_star":  [MK1, MK2, 'COPY "A*.TXT" TO "C*.TXT"'],
    "fr_prog_star":    prog('COPY "A*.TXT" TO "C*.TXT"', onerr=False, pre=(MK1, MK2)),
    "fr_onerr_star":   prog('COPY "A*.TXT" TO "C*.TXT"', pre=(MK1, MK2)),
    # fresh files written by a PREVIOUS program run, COPY typed at the prompt after
    "fr_split":        ["NEW", "20 " + MK1, "30 " + MK2, "40 " + FENCE, "RUN",
                        'COPY "A*.TXT" TO "C*.TXT"'],
    # --- Q3: destination forms ------------------------------------------------
    "fx_prompt_plain": ['COPY "*.BAS" TO "Z.BAS"'],
    "fx_onerr_plain":  prog('COPY "*.BAS" TO "Z.BAS"'),
    "fx_prog_plain":   prog('COPY "*.BAS" TO "Z.BAS"', onerr=False),
    "fr_prompt_plain": [MK1, MK2, 'COPY "A*.TXT" TO "F.TXT"'],
    "fr_onerr_plain":  prog('COPY "A*.TXT" TO "F.TXT"', pre=(MK1, MK2)),
    "fx_prompt_quest": ['COPY "PROG?.BAS" TO "X?.BAS"'],
    "fr_prompt_quest": [MK1, MK2, 'COPY "A?.TXT" TO "D?.TXT"'],
    "fr_onerr_quest":  prog('COPY "A?.TXT" TO "D?.TXT"', pre=(MK1, MK2)),
    "fx_prompt_bin":   ['COPY "*.BIN" TO "*.BAK"'],          # 2 fixture matches
    "fx_prompt_all":   ['COPY "*.*" TO "N*.*"'],             # 6 fixture matches
    # --- Q5: count, closed-ness -----------------------------------------------
    "fr3_prompt_star": [MK1, MK2, MK3, 'COPY "A*.TXT" TO "C*.TXT"'],
    "fr_open_star":    ['OPEN "A1.TXT" FOR OUTPUT AS #1:PRINT #1,"X1"',   # #1 left OPEN
                        MK2.replace("#1", "#2"), 'COPY "A*.TXT" TO "C*.TXT"'],
    "fr_one_star":     [MK1, 'COPY "A*.TXT" TO "C*.TXT"'],   # control: one fresh match
    "fx_one_star":     ['COPY "HI.*" TO "H2.*"'],            # control: one fixture match
    # --- the LIVE-WALK hypothesis (run 1): `*.BAS` -> `Z.BAS` made Z.BAS = the LAST
    # match's bytes and THEN raised 5. If the directory walk sees the entries COPY
    # itself creates, Z.BAS is a 4th match and Z->Z is the self-copy (5, c.self).
    "sm_plain_other":  ['COPY "*.BAS" TO "Z.TXT"'],          # dest OUTSIDE the pattern
    "sm_grow":         ['COPY "*.BAS" TO "Q*.BAS"'],         # dest INSIDE the pattern
    "sm_grow_onerr":   prog('COPY "*.BAS" TO "Q*.BAS"'),
    "sm_fresh_inside": [MK1, MK2, 'COPY "*.TXT" TO "C*.TXT"'],   # HI/A1/A2 -> CI/C1/C2, then CI->CI?
    # --- run 3 ------------------------------------------------------------------
    # does a source '?' match the BLANK 5th position of PROG.BAS? Y+pos2..5 names each
    "q_blank":         ['COPY "PROG?.BAS" TO "Y????.BAS"'],
    # an UNRELATED open channel (run 2's fr_open_star read File still open)
    "open_other":      ['OPEN "ZZ.TXT" FOR OUTPUT AS #1', 'COPY "PROG*.BAS" TO "Q*.BAS"'],
    # SEPARATOR for the live-walk/self-copy explanation: free a directory slot BEFORE
    # the sources; the new Z.BAS lands there, behind the walk cursor, and is never
    # revisited -> predicted NO error. (`dest matches the pattern` would still error.)
    "sm_slot":         ['KILL "HI.TXT"', 'COPY "*.BAS" TO "Z.BAS"'],
    "sm_slot_grow":    ['KILL "HI.TXT"', 'COPY "*.BAS" TO "Q*.BAS"'],   # QROG in slot 1, QROG2/3 appended -> 5
    # copywild_probe.py's w_star program VERBATIM (readbacks included), dense-sampled
    "w_star_orig":     ["NEW", "10 ON ERROR GOTO 90",
                        '20 OPEN "A1.TXT" FOR OUTPUT AS #1:PRINT #1,"X1":CLOSE:OPEN "A2.TXT" FOR OUTPUT AS #1:PRINT #1,"X2":CLOSE',
                        '30 COPY "A*.TXT" TO "C*.TXT"',
                        '40 OPEN "C1.TXT" FOR INPUT AS #1:INPUT #1,A$:CLOSE:OPEN "C2.TXT" FOR INPUT AS #1:INPUT #1,B$:CLOSE:PRINT CHR$(91);"";A$;"|";B$;"OK]":END',
                        '90 PRINT CHR$(91);"";A$;"|";B$;ERR;ERL;"]":END', "RUN"],
}


def fat12_dir(img: bytes):
    bps, spc, rsv, nf, nroot, _, _, spf = struct.unpack_from("<HBHBHHBH", img, 11)
    fat = img[rsv * bps:(rsv + spf) * bps]
    root = (rsv + nf * spf) * bps
    data0 = root + nroot * 32
    out = []
    for i in range(nroot):
        e = img[root + 32 * i:root + 32 * i + 32]
        if e[0] == 0:
            break
        if e[0] == 0xE5:
            out.append((i, "<deleted> " + e[1:11].decode("latin1"), None, None, None)); continue
        if e[11] & 0x08:
            continue
        name = e[:8].decode("latin1").rstrip() + "." + e[8:11].decode("latin1").rstrip()
        clus = struct.unpack_from("<H", e, 26)[0]; size = struct.unpack_from("<I", e, 28)[0]
        data, c, seen = b"", clus, set()
        while 2 <= c < 0xFF8 and len(data) < size and c not in seen:
            seen.add(c)
            data += img[data0 + (c - 2) * spc * bps: data0 + (c - 1) * spc * bps]
            o = c * 3 // 2; v = struct.unpack_from("<H", fat, o)[0]
            c = (v >> 4) if c & 1 else (v & 0xFFF)
        out.append((i, name, size, clus, data[:size]))
    return out


def screen_text(hexs: str) -> list[str]:
    b = bytes.fromhex(hexs)
    rows = []
    for r in range(24):
        row = b[r * 40:(r + 1) * 40]
        rows.append("".join(chr(c) if 32 <= c < 127 else ("." if c else " ") for c in row).rstrip())
    return rows


def build_tcl(out, lines, watch, poke, dense=False):
    body = ["set throttle off", f"set __f [open {{{out}}} w]",
            "proc __hex_v {a l} { binary scan [debug read_block VRAM $a $l] H* h; return $h }",
            omsx_repl.key_proc(),
            'proc __inj {s} { append s "\\r"; __key $s }',
            'proc __obs {tag} { global __f; puts $__f "obs tag=$tag emu=[machine_info time] '
            'wall=[clock milliseconds] pc=[format %04X [reg pc]] scr=[__hex_v 0 960]";'
            ' if {[catch {set d [diskmanipulator dir diska]} e]} { set d "ERR:$e" };'
            ' puts $__f "dir tag=$tag [string map [list "\n" " | "] $d]"; flush $__f }']
    t = BOOT
    def emit(s):
        nonlocal t
        chunks = [s[i:i + MAXD] for i in range(0, len(s), MAXD)] or [""]
        for k, ch in enumerate(chunks):
            proc = "__inj" if k == len(chunks) - 1 else "__key"
            body.append(f"after time {t:.1f} {{ {proc} {{{ch}}} }}")
            t += STEP
    emit("")             # the date question
    emit("SCREEN 0")
    emit("CLS")
    for ln in lines[:-1]:
        emit(ln)
        body.append(f"after time {t - 0.5:.1f} {{ __obs pre }}")
    body.append(f"after time {t - 0.3:.1f} {{ __obs typed }}")
    emit(lines[-1])
    t_last = t - STEP
    body.append(f'after time {t_last:.1f} {{ puts $__f "last emu=[machine_info time] wall=[clock milliseconds]"; flush $__f }}')
    for d in (DENSE if dense else OBS):
        if d <= watch:
            body.append(f"after time {t_last + d:.1f} {{ __obs +{d} }}")
    t = t_last + watch
    body.append(f"after time {t:.1f} {{ __obs end }}")
    if poke:
        body.append(f"after time {t + 1:.1f} {{ __inj {{}} }}")
        body.append(f'after time {t + 1:.1f} {{ puts $__f "poke emu=[machine_info time] wall=[clock milliseconds]"; flush $__f }}')
        body.append(f"after time {t + 6:.1f} {{ __obs poke+5 }}")
        body.append(f"after time {t + 12:.1f} {{ __obs poke+11 }}")
        t += 13
    body.append(f"after time {t:.1f} {{ close $__f; exit }}")
    return "\n".join(body) + "\n"


def run_case(name, lines, watch, outdir, poke=True, wall_timeout=1500.0, dense=False):
    dsk = os.path.join(outdir, f"copymulti_{name}.dsk")
    shutil.copyfile(FIXTURE, dsk)
    out = os.path.join(outdir, f"copymulti_{name}.cap")
    tcl = out + ".tcl"
    if os.path.exists(out):
        os.unlink(out)
    with open(tcl, "w") as f:
        f.write(build_tcl(out, lines, watch, poke, dense))
    cmd = [find_omsx(None), "-machine", MACHINE]
    blob = omsx_repl._settings_read()
    if blob is not None:
        st = out + ".settings.xml"
        open(st, "w").write(blob)
        cmd += ["-setting", st]
    cmd += ["-diska", dsk, "-command", "set renderer none; set sound_driver null", "-script", tcl]
    err = open(out + ".err", "w")
    t0 = time.time()
    proc = subprocess.Popen(omsx_preflight.guarded(cmd), stdout=err, stderr=subprocess.STDOUT,
                            start_new_session=True)
    hashes = []      # (wall_ms, md5) whenever the host image changes
    last = None
    while proc.poll() is None:
        try:
            h = hashlib.md5(open(dsk, "rb").read()).hexdigest()
        except OSError:
            h = None
        if h != last:
            hashes.append((int(time.time() * 1000), h)); last = h
        if time.time() - t0 > wall_timeout:
            proc.terminate()
            try:
                proc.wait(30)
            except subprocess.TimeoutExpired:
                proc.kill()
            print(f"  ⚠️ wall timeout {wall_timeout}s -- emulator terminated")
            break
        time.sleep(0.2)
    err.close()
    return dsk, out, hashes, time.time() - t0


def report(name, lines, dsk, out, hashes, wall, verbose):
    print(f"\n=== {name} ===")
    for ln in lines:
        print(f"  > {ln}")
    recs = open(out).read().splitlines() if os.path.exists(out) else []
    last_wall = None
    fixture_dir = {n for _, n, *_ in fat12_dir(open(FIXTURE, "rb").read())}
    prev_rows = None
    prev_dir = None
    for rec in recs:
        if rec.startswith("last "):
            last_wall = int(rec.split("wall=")[1].split()[0])
            print(f"  -- last line injected at emu {rec.split('emu=')[1].split()[0]}")
            continue
        if rec.startswith("poke "):
            print(f"  -- Enter injected at emu {rec.split('emu=')[1].split()[0]}")
            continue
        if rec.startswith("dir "):
            d = rec.split(" ", 2)[2]
            if d != prev_dir:
                ents = [e.split() for e in d.split("|") if e.strip()]
                names = [f"{e[0]}:{e[-1]}" for e in ents if len(e) >= 3 and "." in e[0]]
                print(f"      dir({rec.split()[1][4:]}): {len(names)} entries: {' '.join(names)}" if names else f"      dir: {d[:160]}")
                prev_dir = d
            continue
        if not rec.startswith("obs "):
            continue
        kv = dict(p.split("=", 1) for p in rec[4:].split(" ", 4))
        rows = screen_text(kv["scr"])
        nz = [f"{i:2}|{r}" for i, r in enumerate(rows) if r]
        changed = rows != prev_rows
        prev_rows = rows
        wr = ""
        if last_wall is not None:
            w = int(kv["wall"])
            n_writes = sum(1 for (hw, _) in hashes if last_wall <= hw <= w)
            wr = f" image-changes-since-last-line={n_writes}"
        print(f"  [{kv['tag']:>7}] emu={float(kv['emu']):7.1f} pc={kv['pc']}{wr}"
              f" {'(screen unchanged)' if not changed and kv['tag'] not in ('pre', 'typed') else ''}")
        if (changed or verbose) and kv["tag"] not in ("pre",):
            for r in nz[-14:]:
                print("      " + r)
    img = open(dsk, "rb").read()
    print("  -- root directory after the run (host read of the image):")
    for i, n, size, clus, data in fat12_dir(img):
        if size is None:
            print(f"     #{i:2} {n}")
            continue
        tag = "" if n in fixture_dir else "  <-- NEW"
        shown = data[:24] if data is not None else b""
        print(f"     #{i:2} {n:14} {size:5} B clus={clus:<4} {shown!r}{tag}")
    print(f"  -- host image changed {len(hashes) - 1} times; wall {wall:.0f}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", type=float, default=120.0, help="emulated seconds to watch after the last line")
    ap.add_argument("--out", default=os.path.join(tempfile.gettempdir(), "copymulti"))
    ap.add_argument("--no-poke", action="store_true")
    ap.add_argument("--dense", action="store_true", help="observe every 0.5 s for the first 30 s")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("-v", action="store_true")
    ap.add_argument("--machine", default="National_CF-3300", help="D-COPYALL: e.g. C-BIOS_MSX1_EU_REPACK_DISK for zerobas")
    ap.add_argument("cases", nargs="*")
    a = ap.parse_args()
    globals()["MACHINE"] = a.machine
    if a.list:
        for k, v in CASES.items():
            print(f"{k:16} {v}")
        return 0
    os.makedirs(a.out, exist_ok=True)
    for name in a.cases or list(CASES):
        lines = CASES[name]
        print(f"\n##### running {name} (watch {a.watch:.0f} s) ...", flush=True)
        dsk, out, hashes, wall = run_case(name, lines, a.watch, a.out, poke=not a.no_poke, dense=a.dense)
        report(name, lines, dsk, out, hashes, wall, a.v)
    return 0


if __name__ == "__main__":
    sys.exit(main())
