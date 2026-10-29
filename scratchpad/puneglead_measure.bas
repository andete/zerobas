10 REM PRINT USING: a negative value whose integer part is 0, in tight fields
20 FOR K=1 TO 300:NEXT
30 LPRINT USING "A #.## B #.## C #.## D #.## E #.##";-.5;-.004;-.996;-1.5;-0
40 LPRINT USING "F ##.## G #.## H #.#";-.5;.5;-.95
50 LPRINT USING "I **#.## J **.## K $$.## L $$#.##";-.5;-.5;-.5;-.5
60 LPRINT USING "M #.##- N +#.## O +.## P .##";-.5;-.5;-.5;-.5
70 LPRINT USING "Q #,.## R #.##^^^^ S #";-.5;-.5;-.4
80 LPRINT USING "T #.#";-.04#:LPRINT USING "U #.##";-.5!
