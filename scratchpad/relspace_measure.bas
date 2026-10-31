10 REM D-RELSPACE: spaces after a compound relop, before a string RHS
15 FOR I=1 TO 500:NEXT: REM long enough for the harness to see the run start
20 A$="A"
30 LPRINT "1";"A"<= "B"
40 LPRINT "2";"A">= "B"
50 LPRINT "3";"A"<>  "B"
60 LPRINT "4";"A"< = "B"
70 LPRINT "5";A$ <= "B"
80 LPRINT "6";"A"< "B"
90 IF A$>= "A" THEN LPRINT "7 THEN" ELSE LPRINT "7 ELSE"
100 LPRINT "END"
