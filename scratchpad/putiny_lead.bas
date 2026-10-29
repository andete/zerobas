10 REM PRINT USING: a negative fraction in a field with no room for "-0"
20 FOR K=1 TO 300:NEXT
30 LPRINT USING "A #.# B #.## C ##.# D #.#";-.04;-.5;-.5;.5
40 LPRINT USING "E #.# F +.# G #.#-";-.5;-.5;-.5
