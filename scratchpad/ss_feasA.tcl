set throttle off
proc __hex_v {a l} { binary scan [debug read_block VRAM $a $l] H* h; return $h }
set __f [open {/Users/joost/projects/zerobas/scratchpad/ss_feasA.out} w]
# at t=8 (ready prompt), report time, save a state to a file, then dump screen
after time 8.0 {
  puts $__f "phase=save t=[machine_info time]"
  set r [catch {savestate -f /Users/joost/projects/zerobas/scratchpad/ss_state.oms} err]
  puts $__f "savestate rc=$r err=$err"
  puts $__f "post_save t=[machine_info time]"
  puts $__f "scr=[__hex_v 0 960]"
  flush $__f
}
after time 8.2 { close $__f; exit }
