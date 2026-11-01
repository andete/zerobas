1 REM @DISK
10 REM ** DISK HOUSEKEEPING - DOUBLES IN A RANDOM FILE, COPY, LFILES, DSKF **
15 KEY OFF:CLS:MAXFILES=2
20 REM 1: free space before, then five records of two doubles each
30 F0=DSKF(0):OPEN "R.DAT" AS #1 LEN=16:FIELD #1,8 AS D$,8 AS E$
40 FOR I=1 TO 5:LSET D$=MKD$(I*1.1#):LSET E$=MKD$(1#/I):PUT #1,I:NEXT:CLOSE #1
50 REM 2: read them back in reverse; MKD$ / CVD must round-trip exactly
60 OPEN "R.DAT" AS #1 LEN=16:FIELD #1,8 AS D$,8 AS E$
70 FOR I=5 TO 1 STEP -1:GET #1,I:X#=CVD(D$):Y#=CVD(E$):LPRINT "CP 1";I;X#;Y#;X#=I*1.1#:NEXT
80 LPRINT "CP 2";LOF(1);LEN(D$):CLOSE #1
90 REM 3: COPY, then the printer's directory, then what the copy cost
100 COPY "R.DAT" TO "S.DAT":LFILES:LPRINT "CP 3";F0-DSKF(0)
110 REM 4: rename, list only the data files, remove both
120 NAME "S.DAT" AS "T.DAT":LFILES "*.DAT":KILL "R.DAT":KILL "T.DAT":LPRINT "CP 4";DSKF(0)=F0
130 REM 5: the program saves itself (tokenised, which carries on) and reads its first byte back
140 SAVE "P.BAS":OPEN "P.BAS" FOR INPUT AS #1:L$=INPUT$(1,#1):LPRINT "CP 5";ASC(L$);LOF(1):CLOSE #1
150 REM 6: a missing file is trapped; RESUME NEXT carries on
160 ON ERROR GOTO 900:KILL "NONE.DAT":LPRINT "CP 7";DSKF(0)<F0
170 KILL "P.BAS":LPRINT "CP 8";DSKF(0)=F0:FILES
180 REM 9: a text SAVE ends a running program, on both machines
190 SAVE "Q.BAS",A
200 LPRINT "CP 9 NOT REACHED"
900 LPRINT "CP 6 ERR";ERR;"IN";ERL:RESUME NEXT
