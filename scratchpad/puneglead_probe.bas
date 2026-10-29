10 REM puneglead-acceptance: negative fractions in tight fields; `+.` and `$$.` fields
20 FOR K=1 TO 300:NEXT
30 LPRINT USING "A #.## B #.## C #.## D #.## E #.##";-.5;-.004;-.996;-1.5;-0
40 LPRINT USING "F ##.## G #.## H #.#";-.5;.5;-.95
50 LPRINT USING "I **#.## J **.## K $$.## L $$#.##";-.5;-.5;-.5;-.5
60 LPRINT USING "M #.##- N +#.## O +.## P .##";-.5;-.5;-.5;-.5
70 LPRINT USING "Q #,.## R #.##^^^^ S #";-.5;-.5;-.4
80 LPRINT USING "T #.#";-.04#:LPRINT USING "U #.##";-.5!
90 LPRINT USING "V +.## W $$.## X +.# Y $$.#";.5;.5;.04;.04
100 LPRINT USING "Z +.##+ $$.##";.25;-.25
110 LPRINT USING "BA +.##+ BB +.##- BC +#.##+ BD +#.##-";-.25;-.25;-.25;-.25
120 LPRINT USING "BE +.##+ BF +#.##+ BG +#.##-";.25;.25;.25
