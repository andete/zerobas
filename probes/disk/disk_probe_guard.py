#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-DISKROMHOST step 4(d), scheme D: a cartridge scanned BEFORE the disk ROM claimed N bytes of RAM -- does zerobas
install and move every published number by N exactly as the CF-3300 does?

probes/disk/claimonce.asm is a test cartridge whose INIT sets HIMEM := $F380 - N once (the word at $4010, patched
here per row); N = 0 boots with no cartridge. In an external slot it is scanned before the disk ROM. Per N and per
machine, two boots:
    DOS   MSX-DOS 1 (~/Documents/msx/msx/disks/test.dsk): HIMEM at the disk ROM's H.RUNC entry (= after INIT), at
          MSX-DOS's start ($0100 in RAM), at A> together with MSX-DOS's $0006; then `BASIC` typed at A>, and in
          Disk BASIC HIMEM, FRE(0), DSKF(0), MEMSIZ, STKTOP
    DATA  a blank 720 KB disk (disk/test720.dsk): HIMEM at the H.RUNC entry, then at the prompt HIMEM, FRE(0),
          DSKF(0), MEMSIZ, STKTOP
plus, in both, DRVTBL ($FB21-$FB22: drives, slot -- installed or not) and every non-zero SLTWRK entry ($FD09-$FD88;
the disk ROM publishes its work-area base in its page-1 entry -- the CF-3300 $F1BF - N).
Slot 0-0's page-0 entry ($FD09) is ZB_HOST, zerobas BASIC's host marker "ZB": checked on its own (zerobas has it,
the CF-3300 does not) and left out of the SLTWRK comparison.
FRE and DSKF are POKEd to $A000 / $A002 by typed lines and read back from RAM ($FFFF: the statement failed -- no
Disk BASIC); openMSX's get_screen reads nothing on zerobas after BASIC at A> (a probe artefact, D-DISKROMHOST).

Rows: N = 0, 16, 300, 439, 456, 473 (the CF-3300's largest, CLAIM_NMAX) and 474 must ALL be SAME as the CF-3300
(D-CLAIM473, 2026-11-27: zerobas follows up to 473 and declines at 474 as the CF-3300 ends up doing -- at the
BASIC prompt HIMEM is the cartridge's $F380 - N, SLTWRK empty, no drive; until then it declined from 440, a KNOWN
row). Past NMAX the two 20 s readings (HIMEM and $0006 at A>) are left out: the CF-3300 is mid-decline then (HIMEM
$F1BF - N, $0006 garbage, AE_claim473_guard1.out), a transient. Instrument checks: up to NMAX the CF-3300 must
install and read HIMEM $F195 - N at its H.RUNC entry; past NMAX it must DECLINE with HIMEM $F380 - N there (the
claimer claimed exactly N), else exit 2. The 474 rows are KNOWN: the disk ROM declines as the CF-3300 does (FB21,
HIMEM at H.RUNC, SLTWRK all SAME), but zerobas BASIC then puts HIMEM back to $F380 (D-CARTCLAIM, a BASIC item), so
HIMEM@BASIC and FRE differ -- the row FAILS if anything else differs, or if it turns SAME (drop the pin then).

Clean room: typed keys in; only RAM cells out -- published work-area cells, MSX-DOS's $0006 and the two POKEd
words, read from the RAM slot RAMAD0 ($F341) names. Breakpoints sit on RAM addresses only (the H.RUNC hook $FECB,
the TPA's $0100); no PC is recorded, no ROM byte read.

    python3 -u probes/disk/disk_probe_guard.py      (gate: diskguard-acceptance)

Exit 0 when every row reads as expected, 1 a divergence, 2 no reading / an instrument fault."""
import os
import shutil
import subprocess
import sys
import tempfile

os.environ.setdefault("ZEROBAS_REFCACHE", "refs")   # zerobas measured every run; the CF-3300 served

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_preflight  # noqa: E402
import probe_refcache  # noqa: E402
import probe_tmp  # noqa: E402

OMSX = os.environ.get("OPENMSX", shutil.which("openmsx") or "/opt/homebrew/bin/openmsx")
DOS = os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")
DATA = os.path.join(ROOT, "disk", "test720.dsk")
MACHINES = (("CF", "National_CF-3300"), ("ZB", os.environ.get("DISKGUARD_ZB_MACHINE")
                                         or "C-BIOS_MSX1_EU_REPACK_DISK"))
NMAX = 473
NS = (0, 16, 300, 439, 456, NMAX, NMAX + 1)

POKES = ("POKE &HA000,255:POKE &HA001,255:POKE &HA002,255:POKE &HA003,255\r"
         "POKE &HA000,FRE(0) MOD 256:POKE &HA001,FRE(0)\\256\r"
         "POKE &HA002,DSKF(0) MOD 256:POKE &HA003,DSKF(0)\\256\r")

TCL = r"""
set f [open {@LOG@} w]
proc w16 {a} { format %04X [peek16 $a] }
proc ram8 {a} {
  set s [peek 0xF341]
  if {($s & 0x70) != 0} {
    if {$a >= 0x8000} { return [peek $a] }
    return -1
  }
  set ss [expr {($s & 0x80) ? (($s >> 2) & 3) : 0}]
  debug read {slotted memory} [expr {($s & 3) * 0x40000 + $ss * 0x10000 + $a}]
}
proc ram16 {a} {
  set lo [ram8 $a]; set hi [ram8 [expr {$a + 1}]]
  if {$lo < 0 || $hi < 0} { return "----" }
  format %04X [expr {$lo + 256 * $hi}]
}
proc sltwrk {} {
  set sw {}
  for {set a 0xFD09} {$a < 0xFD89} {incr a 2} {
    set v [peek16 $a]
    if {$v != 0} { set o [expr {$a - 0xFD09}]; lappend sw "[expr {$o/32}]-[expr {($o%32)/8}]p[expr {($o%8)/2}]:[format %04X $v]" }
  }
  return [join $sw ,]
}
set ::hr {}
debug set_bp 0xFECB {} {
  if {[llength $::hr] < 8} { lappend ::hr "[w16 0xFC4A]/[sltwrk]" }
}
set ::dos -
debug set_bp 0x0100 {[machine_info time] > 1.0 && [lindex [get_selected_slot 0] 0] != 0} {
  if {$::dos eq "-"} { set ::dos [w16 0xFC4A] }
}
proc snap {tag} {
  puts $::f "SNAP $tag HIMEM=[w16 0xFC4A] W0006=[ram16 6] FRE=[ram16 0xA000] DSKF=[ram16 0xA002] MEMSIZ=[w16 0xF672] STKTOP=[w16 0xF674] FB21=[format %02X%02X [peek 0xFB21] [peek 0xFB22]] SLTWRK=[sltwrk]"
  flush $::f
}
@KEYS@
after time @END@ {
  snap END
  puts $::f "HRUNC [join $::hr { }]"
  puts $::f "DOS $::dos"
  close $::f
  exit
}
"""


def tcl_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("[", "\\[").replace("$", "\\$") \
        .replace("\r", "\\r") + '"'


def cart(td, n):
    src = os.path.join(HERE, "claimonce.asm")
    out = os.path.join(td, "claimonce.bin")
    subprocess.run(["pasmo", "--bin", src, out], check=True, capture_output=True)
    b = bytearray(open(out, "rb").read())
    b[0x10:0x12] = n.to_bytes(2, "little")             # claim_n, $4010
    rom = os.path.join(td, f"claimonce_{n}.rom")
    open(rom, "wb").write(bytes(b) + bytes(16384 - len(b)))
    return rom


def run(machine, scen, n, td):
    log = os.path.join(td, f"log_{machine}_{scen}_{n}.txt")
    if scen == "DOS":
        keys = [("20.0", "snap A"), ("20.2", "type " + tcl_str("\rBASIC\r")),
                ("27.0", "type " + tcl_str(POKES))]
        end, src = 45, DOS
    else:
        keys = [("14.0", "type " + tcl_str("\r")), ("16.0", "type " + tcl_str(POKES))]
        end, src = 35, DATA
    script = os.path.join(td, f"s_{machine}_{scen}_{n}.tcl")
    open(script, "w").write(TCL.replace("@LOG@", log).replace("@END@", str(end)).replace(
        "@KEYS@", "\n".join(f"after time {t} {{ {k} }}" for t, k in keys)))
    dsk = os.path.join(td, f"{machine}_{scen}_{n}.dsk")
    shutil.copyfile(src, dsk)
    cmd = [OMSX, "-machine", machine, "-diska", dsk]
    if n:
        cmd += ["-cart", cart(td, n)]
    cmd += ["-command", "set renderer none; set sound_driver null", "-script", script]

    def spawn():
        p = subprocess.Popen(omsx_preflight.guarded(cmd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
        try:
            p.wait(timeout=240)
            return "OK"
        except subprocess.TimeoutExpired:
            p.kill()
            return "TIMEOUT"
    probe_refcache.cached_run(cmd, [log], spawn, media=[dsk], ok=lambda v: v != "TIMEOUT")
    if not os.path.exists(log) or "SNAP END" not in open(log).read():
        return None
    return parse(open(log).read(), scen)


def kv(line):
    return dict(x.split("=", 1) for x in line.split()[2:])


def parse(text, scen):
    snaps = {ln.split()[1]: kv(ln) for ln in text.splitlines() if ln.startswith("SNAP ")}
    hr = next((ln.split()[1:] for ln in text.splitlines() if ln.startswith("HRUNC")), [])
    dos = next((ln.split()[1] for ln in text.splitlines() if ln.startswith("DOS ")), "-")
    # the INIT moment: HIMEM at the first H.RUNC entry where it is no longer the untouched $F380
    init = next((h for h in hr if not h.startswith("F380")), "-")
    e = snaps["END"]
    r = {"installed(FB21)": e["FB21"], "HIMEM@INIT/SLTWRK": init}
    if scen == "DOS":
        a = snaps.get("A", {})
        r.update({"HIMEM@DOS": dos, "HIMEM@A>": a.get("HIMEM", "-"), "$0006@A>": a.get("W0006", "-")})
    r.update({"HIMEM@BASIC": e["HIMEM"], "FRE": int(e["FRE"], 16), "DSKF": int(e["DSKF"], 16),
              "MEMSIZ": e["MEMSIZ"], "STKTOP": e["STKTOP"], "SLTWRK": e["SLTWRK"] or "-"})
    return r


MARKER = "0-0p0:425A"


def strip_marker(r):
    """drop the ZB_HOST entry from r's SLTWRK lists; True if it was there (in every list that has entries)"""
    seen = []
    for k in ("HIMEM@INIT/SLTWRK", "SLTWRK"):
        v = r[k]
        head, sep, lst = v.rpartition("/") if "/" in v else ("", "", v)
        items = [x for x in lst.split(",") if x and x != "-"]
        seen.append(MARKER in items)
        rest = ",".join(x for x in items if x != MARKER) or ("" if sep else "-")
        r[k] = head + sep + rest
    return all(seen)


def show(r):
    return " ".join(f"{k}={v}" for k, v in r.items())


def main():
    if not os.path.isfile(DOS):
        print(f"INSTRUMENT FAULT: no MSX-DOS 1 disk at {DOS}")
        return 2
    td = tempfile.mkdtemp(dir=probe_tmp.ROOT)
    bad, fault = [], []
    try:
        for n in NS:
            for scen in ("DOS", "DATA"):
                got = {side: run(m, scen, n, td) for side, m in MACHINES}
                tag = f"N={n:<3d} {scen:4s}"
                if None in got.values():
                    fault.append(tag)
                    print(f"ROW {tag} NO-READING {[s for s, v in got.items() if v is None]}", flush=True)
                    continue
                cf, zb = got["CF"], got["ZB"]
                # ZB_HOST ($FD09 = slot 0-0's own page-0 SLTWRK entry, "ZB"): zerobas BASIC's host marker, written
                # by boot_wa (C-BIOS integration step 1, Joost 2026-11-27). Pinned, not compared: zerobas MUST carry
                # it, the CF-3300 must NOT; the rest of SLTWRK is compared as before.
                mk = {s: strip_marker(r) for s, r in (("CF", cf), ("ZB", zb))}
                if mk != {"CF": False, "ZB": True}:
                    bad.append(tag)
                    print(f"ROW {tag} MARKER    ZB_HOST {MARKER} on CF={mk['CF']} ZB={mk['ZB']} (want CF=False ZB=True)")
                # instrument: the reference installed and the claimer claimed exactly N
                want_init = f"{0xF195 - n:04X}" if n <= NMAX else f"{0xF380 - n:04X}"
                cf_on = cf["installed(FB21)"][:2] != "00" and cf["DSKF"] != 0xFFFF
                if cf_on != (n <= NMAX) or not cf["HIMEM@INIT/SLTWRK"].startswith(want_init):
                    fault.append(tag)
                    print(f"ROW {tag} INSTRUMENT FAULT: CF-3300 {show(cf)} (want HIMEM@INIT {want_init}, "
                          f"{'installed' if n <= NMAX else 'declined'})")
                    continue
                if n > NMAX:                    # the CF-3300's mid-decline transient (see the docstring)
                    for r in (cf, zb):
                        for k in ("HIMEM@DOS", "HIMEM@A>", "$0006@A>"):
                            r.pop(k, None)
                same = cf == zb
                if n > NMAX:
                    diff = sorted(k for k in cf if cf[k] != zb.get(k))
                    v = ("KNOWN" if diff and set(diff) <= {"HIMEM@BASIC", "FRE"} and zb.get("HIMEM@BASIC") == "F380"
                         else "BROKEN-PIN")
                    if v != "KNOWN":
                        bad.append(tag)
                    print(f"ROW {tag} {v:10s} CF=[{show(cf)}]\n{'':16s} ZB=[{show(zb)}]\n{'':16s} (the disk ROM "
                          f"declines as the CF-3300; zerobas BASIC restores HIMEM $F380 -- D-CARTCLAIM; differs: "
                          f"{', '.join(diff) or '-'})", flush=True)
                    continue
                if not same:
                    bad.append(tag)
                print(f"ROW {tag} {'SAME' if same else 'DIVERGES':10s} CF=[{show(cf)}]"
                      + ("" if same else "\n" + " " * 16 + " ZB=[" + show(zb) + "]  differs: "
                         + ", ".join(k for k in cf if cf[k] != zb.get(k))), flush=True)
    finally:
        shutil.rmtree(td, ignore_errors=True)
    if fault:
        print(f"\nINSTRUMENT FAULT: {', '.join(fault)}")
        return 2
    print(f"\ndiskguard: {'RED' if bad else 'GREEN'}" + (f" -- {', '.join(bad)}" if bad else
          f" ({len(NS) * 2} rows: {len(NS) * 2 - 2} SAME as the CF-3300, 2 KNOWN at N={NMAX + 1} -- D-CARTCLAIM)"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
