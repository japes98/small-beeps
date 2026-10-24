## Plaits load test (M4b): PASS

fwtest's instructions per audio block (64 frames, 348160 of core 0's cycles), each engine at its heaviest over nine settings; voices that fit on core 0 beside the firmware at rest (1820.448 instructions a block; under the heaviest input 15521.816). Soft-float is our runtime's; hardware float is the toolchain's instructions, which fwtest runs; whether the chip has them is open (SR-5).

| # | Engine | Soft-float max | mean | voices | Hardware float max | mean | voices | Full-scale samples |
|---|---|---|---|---|---|---|---|---|
| 0 | virtual analog VCF | 1005730 | 960416 | 0 | 29150 | 28832 | 11 | 0 |
| 1 | phase distortion | 1149230 | 1097265 | 0 | 40840 | 39975 | 8 | 0 |
| 2 | six-op FM (bank 1) | 818620 | 732998 | 0 | 30550 | 27815 | 11 | 0 |
| 3 | six-op FM (bank 2) | 828930 | 746782 | 0 | 30760 | 28189 | 11 | 0 |
| 4 | six-op FM (bank 3) | 825170 | 743336 | 0 | 30510 | 27976 | 11 | 0 |
| 5 | wave terrain | 1141280 | 1026114 | 0 | 29910 | 27728 | 11 | 0 |
| 6 | string machine | 1215960 | 1128883 | 0 | 40510 | 40394 | 8 | 0 |
| 7 | chiptune | 184280 | 174173 | 1 | 10560 | 10274 | 32 | 0 |
| 8 | virtual analog | 864760 | 803400 | 0 | 32490 | 31363 | 10 | 0 |
| 9 | waveshaping | 751790 | 729523 | 0 | 19490 | 19192 | 17 | 0 |
| 10 | FM | 1122150 | 1076868 | 0 | 41400 | 41318 | 8 | 0 |
| 11 | grain | 1023190 | 870877 | 0 | 28590 | 27240 | 12 | 0 |
| 12 | additive | 1679090 | 1636538 | 0 | 45790 | 45760 | 7 | 0 |
| 13 | wavetable | 1291050 | 1271204 | 0 | 30680 | 30606 | 11 | 0 |
| 14 | chords | 1139300 | 1054855 | 0 | 35620 | 33122 | 9 | 33 |
| 15 | speech | 888940 | 487132 | 0 | 26330 | 17530 | 13 | 0 |
| 16 | swarm | 1073190 | 1043340 | 0 | 28200 | 27369 | 12 | 0 |
| 17 | noise | 1039740 | 949791 | 0 | 48390 | 47298 | 7 | 1 |
| 18 | particle | 1184630 | 1119922 | 0 | 47720 | 41850 | 7 | 0 |
| 19 | string | 1126800 | 949441 | 0 | 38540 | 35533 | 8 | 0 |
| 20 | modal | 1838260 | 1785766 | 0 | 52640 | 52585 | 6 | 23 |
| 21 | bass drum | 922440 | 867906 | 0 | 27000 | 26377 | 12 | 149 |
| 22 | snare drum | 1031790 | 967518 | 0 | 35080 | 33394 | 9 | 3 |
| 23 | hi-hat | 627640 | 609790 | 0 | 25210 | 25143 | 13 | 0 |

Two voices at once, core 0 and core 1, against one after the other on core 0:

| Engine | Float | apart | at once | speed-up |
|---|---|---|---|---|
| virtual analog VCF | soft | 1792030 | 972400 | 1.843 |
| virtual analog | soft | 1510240 | 778490 | 1.940 |
| string | soft | 1456230 | 858540 | 1.696 |
| virtual analog VCF | hardware | 56240 | 28330 | 1.985 |
| virtual analog | hardware | 60610 | 29950 | 2.024 |
| string | hardware | 73440 | 36930 | 1.989 |

| Check | Result | Detail |
|---|---|---|
| demo builds | PASS |  |
| demo build is deterministic | PASS |  |
| live demo plays without underrun (soft) | PASS | engine 7, 0 underruns while playing, peak 12656 |
| live demo plays without underrun (hw) | PASS | engine 0, 0 underruns while playing, peak 9865 |
| soft-float bit for bit (soft image) | PASS | 15 operations, 20000 cases each |
| bench completes (soft) | PASS |  |
| core 1 starts and renders (soft) | PASS |  |
| soft-float bit for bit (hw image) | PASS | 15 operations, 20000 cases each |
| bench completes (hw) | PASS |  |
| core 1 starts and renders (hw) | PASS |  |
| no NaN, infinity or bad conversion | PASS | soft-float flags {'invalid': 0, 'overflow': 0, 'convert': 0} |
| hardware float sounds the same | PASS | 24 of 24 engines' checksums equal |
