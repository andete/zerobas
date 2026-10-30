10 REM D-RESNEXTDIRECT: RESUME NEXT after an error on the LAST program line
15 FOR I=1 TO 400:NEXT:REM long enough for the runner's 0.1 s poll to see it run
20 ON ERROR GOTO 30:GOTO 40
30 LPRINT "E";ERR;ERL:RESUME NEXT
40 LPRINT "L":ERROR 5
