set throttle off
loadstate {/Users/joost/projects/zerobas/scratchpad/ss_diff_states/zb.oms}
set throttle off
set __f [open {/Users/joost/projects/zerobas/scratchpad/ss_r.out} w]
proc __hex_v {a l} { binary scan [debug read_block VRAM $a $l] H* h; return $h }
proc __hex_m {a l} { binary scan [debug read_block memory $a $l] H* h; return $h }
proc __file_hex {p} {
  if {[catch {set h [open $p rb]; set d [read $h]; close $h}]} { return {} }
  binary scan $d H* x; return $x
}
proc __hex_mi {p l} {
  set b [expr {[debug read memory $p] + 256*[debug read memory [expr {$p+1}]]}]
  binary scan [debug read_block memory $b $l] H* h; return $h
}
proc __hex_line {p} {
  set base [expr {[debug read memory $p] + 256*[debug read memory [expr {$p+1}]]}]
  set link [expr {[debug read memory $base] + 256*[debug read memory [expr {$base+1}]]}]
  if {$link <= $base} { return "" }
  binary scan [debug read_block memory $base [expr {$link - $base}]] H* h; return $h
}
proc __lines {p} {
  set cur [expr {[debug read memory $p] + 256*[debug read memory [expr {$p+1}]]}]
  set out {}
  for {set i 0} {$i < 128} {incr i} {
    set link [expr {[debug read memory $cur] + 256*[debug read memory [expr {$cur+1}]]}]
    if {$link == 0} { break }
    lappend out [expr {[debug read memory [expr {$cur+2}]] + 256*[debug read memory [expr {$cur+3}]]}]
    if {$link <= $cur} { break }
    set cur $link
  }
  return [join $out ,]
}
proc __echo {k} { global __f; puts $__f "echo.$k=[debug read memory 64687],[debug read memory 62384],[__hex_v 0 960]"; flush $__f }
set ::__zbdefer 0
set ::__zbforced 0
proc __key {s {tries 0}} {
  set n [string length $s]
  set g [expr {[debug read memory 62458] + 256*[debug read memory 62459]}]
  set q [expr {[debug read memory 62456] + 256*[debug read memory 62457]}]
  if {$g != $q} {
    if {$tries < 40} {
      incr ::__zbdefer
      after time 0.002 [list __key $s [expr {$tries + 1}]]
      return
    }
    incr ::__zbforced
  }
  for {set i 0} {$i < $n} {incr i} {
    set a [expr {$g + $i}]
    if {$a >= 64536} { incr a -40 }
    debug write memory $a [scan [string index $s $i] %c]
  }
  set p [expr {$g + $n}]
  if {$p >= 64536} { incr p -40 }
  debug write memory 62456 [expr {$p & 0xFF}]
  debug write memory 62457 [expr {($p >> 8) & 0xFF}]
}
proc __inj {s} { append s "\r"; __key $s }
proc __hb {} { catch {set __h [open {/Users/joost/projects/zerobas/scratchpad/ss_r.hb} w]; puts $__h [machine_info time]; close $__h}; after realtime 3 __hb }
after time 0.0 { __inj {NEW} }
after time 2.40 { __echo 0 }
after time 3.0 { __inj {10 ONERRORGOTO900} }
after time 5.40 { __echo 1 }
after time 6.0 { __inj {15 SCREEN2} }
after time 8.40 { __echo 2 }
after time 9.0 { __inj {20 CIRCLE(50,50),} }
after time 11.40 { __echo 3 }
after time 12.0 { __key {30 R=POINT(30,50):SCREEN0:CLS:PRINT"["} }
after time 14.40 { __echo 4 }
after time 15.0 { __inj {;ERR;R;"]":END} }
after time 17.40 { __echo 5 }
after time 18.0 { __key {900 R=POINT(30,50):SCREEN0:CLS:PRINT"[} }
after time 20.40 { __echo 6 }
after time 21.0 { __inj {";ERR;R;"]":END} }
after time 23.40 { __echo 7 }
after time 24.0 { __inj {RUN} }
after time 26.40 { __echo 8 }
after time 27.0 { puts $__f "case.0=[__hex_v 0 960]"; flush $__f }
after realtime 0 __hb
after time 35.0 { close $__f; exit }
after time 65.0 { catch {close $__f}; exit }
after realtime 25 { catch {set z [open {/Users/joost/projects/zerobas/scratchpad/ss_r.mark} w]; puts $z BACKSTOP25; close $z}; exit }
