set throttle off
set f [open "cf_slotcheck.out" w]
after time 22 {
  puts $f "A8=[format %02X [debug read ioports 0xA8]]"
  puts $f "FFFF=[format %02X [debug read memory 0xFFFF]]"
  foreach p {0 1 2 3} { puts $f "page $p selected slot: [get_selected_slot $p]" }
  puts $f "debuggables: [debug list]"
  puts $f "slotmap:\n[slotmap]"
  set rows {}
  for {set r 0} {$r < 24} {incr r} {
    set b [debug read_block VRAM [expr {0x1800 + $r*32}] 32]
    set line ""
    for {set i 0} {$i < 32} {incr i} { binary scan [string index $b $i] cu c; append line [expr {($c >= 32 && $c < 127) ? [format %c $c] : "."}] }
    puts $f "SCR $r:[string trimright $line]"
  }
  close $f; exit
}
