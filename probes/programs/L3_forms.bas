10 REM ** FORMS - DRAWING A DATA-ENTRY SCREEN WITH CONTROL CODES AND ESCAPES **
20 SCREEN 0:WIDTH 40:KEY OFF:CLS:E$=CHR$(27)
30 REM 1: a frame by ESC Y positioning
40 PRINT E$;"Y";CHR$(32+2);CHR$(32+4);"+";STRING$(30,"-");"+";
50 FOR R=3 TO 9:PRINT E$;"Y";CHR$(32+R);CHR$(32+4);"|";E$;"Y";CHR$(32+R);CHR$(32+35);"|";:NEXT
60 PRINT E$;"Y";CHR$(32+10);CHR$(32+4);"+";STRING$(30,"-");"+";
70 REM 2: labels with TAB and cursor-right moves, a field filled then backspaced
80 PRINT E$;"Y";CHR$(32+4);CHR$(32+6);"NAME";CHR$(9);":";CHR$(28);CHR$(28);"JOHNNY";CHR$(8);CHR$(8);"NY";
90 PRINT E$;"Y";CHR$(32+6);CHR$(32+6);"CITY";CHR$(9);":  GENT";CHR$(29);CHR$(29);CHR$(29);CHR$(29);"K";
100 A=POS(0):B=CSRLIN
110 REM 3: up / down moves, home, and erase to end of line
120 PRINT CHR$(30);CHR$(30);"^^";CHR$(31);CHR$(31);CHR$(31);"vv";CHR$(11);"TOP";E$;"K";
130 C=POS(0):D=CSRLIN
140 REM 4: insert and delete a line inside the frame
150 PRINT E$;"Y";CHR$(32+5);CHR$(32+0);E$;"L";"(INSERTED)";E$;"Y";CHR$(32+12);CHR$(32+0);E$;"M";
160 PRINT E$;"Y";CHR$(32+14);CHR$(32+2);"BOTTOM";E$;"J";
170 REM 5: the screen, read back
180 F=POS(0):G=CSRLIN
190 FOR Y=0 TO 15:S$="":FOR X=0 TO 39:S$=S$+CHR$(VPEEK(Y*40+X)):NEXT:LPRINT "|";S$:NEXT
200 LPRINT "CP 9";A;B;C;D;F;G
210 END
