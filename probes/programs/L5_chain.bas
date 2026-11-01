1 REM @DISK
10 REM ** CHAIN - A PROGRAM THAT WRITES THE NEXT PARTS AND RUNS THEM **
20 KEY OFF:CLS:MAXFILES=1:Q$=CHR$(34)
30 REM LIST / LLIST end a running program on both machines, so they come last
40 REM 1: write part two as a text file, line by line
50 OPEN "P2.BAS" FOR OUTPUT AS #1
60 PRINT #1,"10 LPRINT ";Q$;"CP 3 PART TWO";Q$;";A;LEN(B$)"
70 PRINT #1,"20 DEFINT A:A=7:LPRINT ";Q$;"CP 4";Q$;";A*6;A/4;A\4"
80 PRINT #1,"30 FOR I=1 TO 3:B$=B$+CHR$(64+I):NEXT:LPRINT ";Q$;"CP 5 ";Q$;";B$"
90 PRINT #1,"40 RUN ";Q$;"P3.BAS";Q$
100 CLOSE #1
110 REM 2: part three prints, then merges part four into itself
120 OPEN "P3.BAS" FOR OUTPUT AS #1
130 PRINT #1,"5 LPRINT ";Q$;"CP 6 PART THREE";Q$;";FRE(0)>1000"
140 PRINT #1,"10 MERGE ";Q$;"P4.BAS";Q$
150 PRINT #1,"20 LPRINT ";Q$;"CP 7 AFTER MERGE";Q$
160 CLOSE #1
170 REM 3: part four replaces nothing and adds a line that lists the result
180 OPEN "P4.BAS" FOR OUTPUT AS #1:PRINT #1,"25 REM MERGED":PRINT #1,"30 LLIST":CLOSE #1
190 A=5:LPRINT "CP 2";A
200 RUN "P2.BAS"
210 LPRINT "CP 2 NOT REACHED"
