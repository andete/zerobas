set throttle off
set __f [open {/Users/joost/projects/zerobas/scratchpad/ss_api.out} w]
after time 6.0 {
  puts $__f "t=[machine_info time]"
  # what savestate-related commands exist?
  puts $__f "help_savestate=[catch {help savestate} e]:$e"
  # settings that might control dir
  foreach s {savestate_dir} { puts $__f "setting $s = [catch {set $s} v]:$v" }
  # try a bare-name save
  puts $__f "save_named=[catch {savestate zbtest_named} e]:$e"
  # try a name with a path separator (absolute)
  puts $__f "save_pathy=[catch {savestate /Users/joost/projects/zerobas/scratchpad/zbss_pathy} e]:$e"
  # list savestates
  puts $__f "list=[catch {list_savestates} e]:$e"
  flush $__f
  close $__f
  exit
}
after realtime 15 { catch {close $__f}; exit }
