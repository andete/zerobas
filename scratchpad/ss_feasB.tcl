set throttle off
proc __hex_v {a l} { binary scan [debug read_block VRAM $a $l] H* h; return $h }
set __f [open {/Users/joost/projects/zerobas/scratchpad/ss_feasB.out} w]
puts $__f "boot t=[machine_info time]"
set r [catch {loadstate /Users/joost/projects/zerobas/scratchpad/zbss_pathy} err]
puts $__f "loadstate rc=$r err=$err"
puts $__f "post_load t=[machine_info time]"
puts $__f "scr_immediate=[__hex_v 0 960]"
flush $__f
set __now [machine_info time]
after time [expr {$__now + 1.0}] {
  puts $__f "at_plus1 t=[machine_info time]"
  puts $__f "scr_plus1=[__hex_v 0 960]"
  flush $__f
  close $__f
  exit
}
after realtime 15 { puts $__f "REALTIME_BACKSTOP_FIRED t=[machine_info time]"; catch {flush $__f}; catch {close $__f}; exit }
