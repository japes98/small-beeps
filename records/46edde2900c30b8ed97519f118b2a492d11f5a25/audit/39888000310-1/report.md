# Similarity audit 46edde2900c3

- Set: full; run: https://github.com/japes98/small-beeps/actions/runs/39888000310
- JPlag 6.3.0 (sha256 `5f2c21e8b88ed771`), Java image `eclipse-temurin@sha256:dbb43d81099eec91e0800226ed2296d03146ee7857165b95112372ad0d67e87f`

- Control: raspberrypi/pico-examples at `4c3a3dc0196d`, 244 files
- The control's longest match with any target it is not related to: **35 tokens**; a pair of ours fails above **59 tokens** (margin 24).
- Control-related targets (the control matches them above 100 tokens; each judged against the control's own score there plus the margin): none
- Target files scored: 18498 (one copy per blob)

## Checks

| Check | Result | Detail |
|---|---|---|
| C-AUDIT-JPLAG | PASS | jar sha256 matches; Java image pinned by digest |
| C-AUDIT-PIN | PASS | 516 targets fetched at their pinned commit and tree; 0 unavailable |
| C-AUDIT-CONTROL | PASS | 244 control files; its longest match with an unrelated target 35 tokens; 0 of 516 targets control-related (above 100 tokens; at most 10% allowed) |
| C-AUDIT-SCORE | PASS | 0 of our file pairs above 59 tokens (the control's 35 plus 24; for a control-related target, its own score plus 24) |
| C-AUDIT-LEAK | PASS | no line of a target file (24 characters or more) in the report |

## Our top file pairs

| Our file | Target (places with this file) | Path | Licence | Longest | Max | Avg |
|---|---|---|---|---|---|---|
| src/gfx.c | Erbubar23/bubba-machine (1) | core/bm_gfx.c | gpl | 20 | 0.229 | 0.113 |
| src/gfx.c | chinotto1/unibox (3) | platform/common.c | gpl | 19 | 0.215 | 0.149 |
| src/lcd.c | DeadActive/hortator (1) | tests/motion_test.c | gpl | 19 | 0.167 | 0.103 |
| src/lcd.c | JalopyMusic/fm1-deadactive-hortator (2) | tests/motion_test.c | gpl | 19 | 0.167 | 0.105 |
| src/sb.h | theNoisery/fN-1 (1) | app/synth/engine_granular.h | other | 18 | 0.514 | 0.319 |
| src/screen.c | y6zkcqnf5r-hue/fm1-trawler (1) | tests/unit/test_model.c | gpl | 18 | 0.261 | 0.234 |
| src/gfx.c | birkmann/Ravel_FM1 (2) | firmware/app/rv_gfx.c | gpl | 18 | 0.208 | 0.086 |
| src/gfx.c | Kenneth-Rakentine/Ravel-FM1 (1) | firmware/app/rv_gfx.c | gpl | 18 | 0.208 | 0.147 |
| src/sb.h | oscillr/DUELL (1) | felucca-base/firmware/src/sense.h | gpl | 17 | 0.415 | 0.286 |
| src/sb.h | cmlarsen/fm1-rocket-os (1) | core/seq/take.h | gpl | 17 | 0.254 | 0.234 |
| src/screen.c | gospodindilly-ops/jangada (3) | tests/enc_test.c | gpl | 17 | 0.246 | 0.081 |
| src/screen.c | JalopyMusic/fm1-zednaked-jangada (2) | tests/enc_test.c | gpl | 17 | 0.246 | 0.082 |
| src/screen.c | TerkWerX/Crepuscular_Homunculus (1) | tests/test_midi_uart.c | gpl | 17 | 0.246 | 0.115 |
| src/sb.h | dsablic/sidou (1) | platform/fm1/input.h | gpl | 16 | 0.941 | 0.337 |
| src/sb.h | NOVALENTI/fm1-polyseq (1) | sequencer.h | none | 16 | 0.667 | 0.314 |
| src/sb.h | zvenson/fm1doom (1) | src/p_saveg.h | gpl | 16 | 0.571 | 0.302 |
| src/lcd.c | ChanceTheMaker/felucca-smk (3) | tests/smk37_midi_output_test.c | gpl | 16 | 0.356 | 0.201 |
| src/sb.h | ChanceTheMaker/gamedude-fm1-smk (1) | src/gb_port.h | gpl | 16 | 0.348 | 0.258 |
| src/sb.h | ChanceTheMaker/NESynth-FM1-SMK (1) | src/nes_port.h | gpl | 16 | 0.281 | 0.237 |
| src/sb.h | zvenson/fm1doom (1) | src/i_video.h | gpl | 16 | 0.205 | 0.198 |

## Our files

| File | Tokens | State |
|---|---|---|
| src/font.c | - | TOO_SMALL |
| src/gfx.c | 145 | scored |
| src/irq.c | 75 | scored |
| src/lcd.c | 115 | scored |
| src/main.c | 117 | scored |
| src/probe.c | 90 | scored |
| src/sb.h | 79 | scored |
| src/screen.c | 70 | scored |
| src/start.c | - | no match |

## Targets

| Target | Commit | Licence | Files (new) | Ours longest | Control longest | Not parsed |
|---|---|---|---|---|---|---|
| 2bbb/fm1-firmware-collection | `ba2b078cd5cc` | permissive | 0 (0) | 0 | 0 | 0 |
| 7oi/sloop-fm1 | `bb6e53f67bec` | gpl | 124 (124) | 15 | 33 | too_small 3 |
| aaasss01061997-bot/Fm-Music- | `cf01ef464cbb` | none | 0 (0) | 0 | 0 | 0 |
| abcdaniel/Felucca | `ac6bfcbd76ee` | gpl | 142 (134) | 13 | 33 | cannot_parse 1, too_small 3 |
| abcdaniel/fm1-custom-fw | `51a35ccb5d62` | none | 0 (0) | 0 | 0 | 0 |
| abcdaniel/fm1-x0x | `201e5c5c1ac0` | gpl | 85 (77) | 13 | 32 | cannot_parse 1, too_small 4 |
| abcdaniel/lunar-modulator | `64209e3c0822` | permissive | 465 (455) | 15 | 33 | cannot_parse 8, too_small 18 |
| abcdaniel/sloop-fm1 | `a1c5d68767ae` | gpl | 101 (72) | 15 | 33 | too_small 2 |
| aceyprime/zen-1 | `ec9295233ea6` | gpl | 79 (48) | 13 | 26 | cannot_parse 4, too_small 5 |
| actuallysparky/FM-1-Unholy-Union-generative-drone-firmware | `273e9b511f1f` | gpl | 176 (115) | 14 | 33 | cannot_parse 1, too_small 4 |
| adamcharleswilsonmusic-code/Fart-Machine-One | `aa95a0319151` | gpl | 58 (25) | 13 | 26 | cannot_parse 1, too_small 2 |
| adamcharleswilsonmusic-code/RAMBEAVER | `a13eb60137ac` | gpl | 0 (0) | 0 | 0 | 0 |
| adamcharleswilsonmusic-code/Trumpagotchi | `976b6e65dc96` | gpl | 71 (28) | 13 | 33 | cannot_parse 1, too_small 4 |
| adriandomc/dino-synth | `8c13a1edd096` | gpl | 126 (34) | 15 | 34 | too_small 3 |
| AETHER-ENGINEERS/fm1-emu | `84d3c3b460d9` | gpl | 32 (32) | 0 | 32 | too_small 1 |
| afta8/fm1-emu | `7196a9f45bb1` | gpl | 31 (0) | 0 | 32 | too_small 1 |
| ajsoriar/Felucca | `172753762439` | gpl | 166 (65) | 14 | 33 | cannot_parse 1, too_small 3 |
| AL-255/FM-1-RE | `ec832f281ca1` | permissive | 3 (3) | 0 | 22 | 0 |
| AlexanderSeel/TheReFmB1rth | `5e2cc6fa89cb` | none | 63 (63) | 14 | 27 | too_small 6 |
| AlexPavAi/Felucca-m-vave-fm1-firmware- | `1e838e17e170` | gpl | 67 (44) | 13 | 33 | too_small 3 |
| AlexPavAi/sloop-fm1 | `d691ba7b2d92` | gpl | 93 (38) | 15 | 33 | too_small 2 |
| amacias/octo-vave | `f97ccd4eef25` | permissive | 0 (0) | 0 | 0 | 0 |
| amalahama/sloop-SMK37 | `f2b44c219b8a` | gpl | 91 (17) | 15 | 33 | too_small 2 |
| ambientsoundartist/Felucca | `5738617968a2` | gpl | 163 (43) | 14 | 33 | cannot_parse 1, too_small 3 |
| amineferjani/Back_FM | `0af0e78f0820` | none | 0 (0) | 0 | 0 | 0 |
| andreahaku/Felucca | `727f272015da` | gpl | 123 (75) | 13 | 33 | too_small 3 |
| andreahaku/fm1-chord | `377235d9f39a` | gpl | 139 (46) | 13 | 33 | too_small 3 |
| andrerezemini/sloop-lab | `3b83f31020f5` | gpl | 118 (36) | 15 | 33 | too_small 2 |
| andrixb/OPQuencer | `b992291caa6e` | gpl | 161 (32) | 14 | 33 | cannot_parse 2, too_small 2 |
| anonymousacademe/FM-1-GrooveDeck | `20bf2de4a687` | gpl | 31 (10) | 13 | 26 | too_small 2 |
| anonymousacademe/FM-1-TripDeck | `a977f53558b7` | gpl | 36 (9) | 13 | 26 | too_small 2 |
| ant25fr/JIANT | `5300f79a2e3d` | gpl | 187 (156) | 14 | 33 | cannot_parse 8, too_small 4 |
| AntonioAltea/fmel-1 | `3a4de21bf015` | gpl | 37 (14) | 13 | 26 | cannot_parse 1, too_small 2 |
| apiel/fm1-tribe | `fd7ae3ea5968` | gpl | 129 (75) | 13 | 32 | cannot_parse 2, too_small 5 |
| arksat/melodee | `1a71d999dcf4` | gpl | 217 (199) | 14 | 33 | cannot_parse 1, too_small 8 |
| arksat/sloop-fm1 | `d3a8385f56ce` | gpl | 115 (19) | 15 | 33 | too_small 2 |
| aroum/fm1-custom-fw | `9b7e9b5cfd9b` | none | 0 (0) | 0 | 0 | 0 |
| artqcid/fm1_open | `24beff707163` | other | 124 (124) | 13 | 24 | too_small 34 |
| atachh/sloop-fm1 | `8fad1a15ff59` | gpl | 114 (0) | 15 | 33 | too_small 2 |
| awolace/IVee | `ba0658641404` | none | 0 (0) | 0 | 0 | 0 |
| babage/fm1_open | `5d3eac2573db` | other | 120 (35) | 13 | 24 | too_small 34 |
| balancechiang/fm1_alt | `b178ac43c25f` | other | 122 (13) | 13 | 24 | too_small 35 |
| barrule/fm1-emu | `7ca5b96c9e82` | gpl | 32 (0) | 0 | 32 | too_small 1 |
| Batora07/ChoralRootFM1 | `aa5875af20e3` | gpl | 213 (142) | 15 | 33 | cannot_parse 12, too_small 6 |
| bbmusichun/fm1_open | `4d266850f8a4` | other | 124 (0) | 13 | 24 | too_small 34 |
| beashoko/april-os | `6b65734fad08` | permissive | 0 (0) | 0 | 0 | 0 |
| bedwards/sloop-fm1 | `e421e4362e41` | gpl | 88 (25) | 15 | 33 | too_small 3 |
| beingsane/Felucca | `20c275e39f75` | gpl | 123 (5) | 13 | 33 | too_small 3 |
| beingsane/fm1-firmware-patcher | `4cfab6024551` | permissive | 0 (0) | 0 | 0 | 0 |
| benbadio/hera-fm1 | `76b7ee8484d2` | gpl | 85 (53) | 15 | 33 | cannot_parse 1, too_small 4 |
| benny-sparra/fm1-dx7-patch-importer | `c11ab28cbc1e` | permissive | 4 (4) | 0 | 0 | 0 |
| birkmann/Ravel_FM1 | `8d89317f92bb` | gpl | 69 (50) | 18 | 33 | cannot_parse 1, too_small 4 |
| bonszaimusic/caravel | `97022acaa6fc` | gpl | 209 (115) | 14 | 33 | cannot_parse 1, too_small 4 |
| bratta/fm1-manager | `64cad0932ae2` | none | 0 (0) | 0 | 0 | 0 |
| briwil/Felucca | `44abc098d5f6` | gpl | 137 (70) | 13 | 33 | cannot_parse 1, too_small 3 |
| bunglesociety/modular-one | `bd6e6d056656` | gpl | 78 (37) | 14 | 33 | too_small 4 |
| carlosshawplatino/Felucca | `2da8ee0f3e8a` | gpl | 163 (3) | 14 | 33 | cannot_parse 1, too_small 3 |
| cartesive/fumi-1 | `9de99261fc3c` | gpl | 67 (17) | 13 | 26 | cannot_parse 3, too_small 3 |
| catacombius/NoteSorcery | `73d6cdd6d2a0` | gpl | 138 (89) | 15 | 33 | too_small 5 |
| cdodd/felucca-vst | `91addeeb989b` | gpl | 14 (14) | 0 | 18 | too_small 2 |
| ChanceTheMaker/doom-fm1-smk | `b705a7b06e01` | gpl | 103 (87) | 14 | 26 | too_small 10 |
| ChanceTheMaker/Felucca | `1a345338f6eb` | gpl | 83 (44) | 13 | 33 | too_small 3 |
| ChanceTheMaker/felucca-smk | `9a73145a6ed6` | gpl | 281 (131) | 16 | 33 | cannot_parse 1, too_small 8 |
| ChanceTheMaker/gamedude-fm1-smk | `47d83306d7b6` | gpl | 125 (71) | 16 | 26 | too_small 9 |
| ChanceTheMaker/NESynth-FM1-SMK | `3fdbe3e6bab8` | gpl | 148 (119) | 16 | 32 | too_small 10 |
| ChanceTheMaker/sloop-fm1-sim | `3dbf57077410` | gpl | 0 (0) | 0 | 0 | 0 |
| charlesvestal/fm1-amb | `188b0a42f20a` | other | 9 (9) | 14 | 19 | 0 |
| charlesvestal/fm1-base | `865bc2f41681` | other | 48 (48) | 13 | 33 | cannot_parse 1, too_small 1 |
| charlesvestal/fm1-ctl | `e181b4a1ac15` | other | 94 (94) | 15 | 33 | too_small 38 |
| charlesvestal/fm1-fomni | `7e7547f384fe` | gpl | 50 (11) | 13 | 26 | cannot_parse 1, too_small 2 |
| charlesvestal/fm1-loom | `e88f2e00ec60` | gpl | 44 (44) | 13 | 33 | cannot_parse 4, too_small 1 |
| charlesvestal/fm1-mocky | `facab5da0add` | gpl | 40 (11) | 13 | 26 | cannot_parse 1, too_small 2 |
| charlesvestal/fm1-monk | `793710689adb` | gpl | 53 (21) | 13 | 26 | cannot_parse 1, too_small 2 |
| charlesvestal/fm1-polly | `62cd07ea7c95` | gpl | 137 (63) | 15 | 33 | cannot_parse 1, too_small 40 |
| charlesvestal/fm1-radio | `66d62558bc71` | other | 661 (661) | 13 | 35 | cannot_parse 2, too_small 187 |
| charlesvestal/fm1-reader | `2f49d91c142b` | permissive | 3 (2) | 0 | 14 | 0 |
| charlesvestal/fm1-velocity | `8f62ce0d968c` | gpl | 47 (13) | 13 | 32 | cannot_parse 1, too_small 2 |
| charlesvestal/fm1-x0x | `54194c54bb01` | gpl | 91 (19) | 13 | 32 | cannot_parse 2, too_small 4 |
| charlesvestal/melodee | `6a30eba1a789` | gpl | 178 (98) | 14 | 33 | too_small 6 |
| chinotto1/unibox | `bd184eba6857` | gpl | 70 (38) | 19 | 32 | too_small 2 |
| cicloid/awesome-fm-1 | `a7be23a05a2a` | permissive | 0 (0) | 0 | 0 | 0 |
| claudehenchoz/orbit | `dc3cd08482fa` | gpl | 134 (118) | 15 | 33 | too_small 2 |
| cmlarsen/fm1-rocket-os | `d269df962a6d` | gpl | 166 (113) | 17 | 33 | cannot_parse 3, too_small 9 |
| cmlarsen/fm1-zed | `218b8fd736fd` | gpl | 159 (16) | 14 | 33 | cannot_parse 1, too_small 3 |
| Co-oscillator/Loom-FM-1 | `a11bc8ce6ce7` | gpl | 176 (49) | 14 | 33 | cannot_parse 1, too_small 3 |
| codeine4563-netizen/fm1-pico-recovery-guia-en-espa-ol-para-uso-de-raspberry-pi-pico-rp2040- | `066f5eb1f931` | none | 0 (0) | 0 | 0 | 0 |
| colofonbrigade/hortator | `ea643d42fc2f` | permissive | 0 (0) | 0 | 0 | 0 |
| cotrino/fm1-betis-mode | `84d6ad4e8b6a` | other | 134 (14) | 13 | 24 | too_small 37 |
| CoydeLau/sloop-fm1 | `fa9ce5742f4a` | gpl | 109 (21) | 15 | 33 | too_small 2 |
| curist/fm1-clk320-probe | `e1c6d99af110` | gpl | 90 (13) | 13 | 32 | cannot_parse 2, too_small 4 |
| czietz/fm1-dx7-patch-importer | `3b69028a51f0` | permissive | 3 (0) | 0 | 0 | 0 |
| czietz/fm1-firmware-patcher | `58569017a4f9` | permissive | 0 (0) | 0 | 0 | 0 |
| czietz/fm1-read-voice | `b7c539f2ca4a` | none | 0 (0) | 0 | 0 | 0 |
| d0pe1/md-one | `70528bfb9887` | gpl | 101 (60) | 15 | 26 | too_small 10 |
| danilokosky/fm1_VA_Moog | `5238cfab4061` | other | 126 (3) | 13 | 24 | too_small 34 |
| davidozz0/clipper-smk | `42cb76ed6a49` | gpl | 167 (118) | 15 | 33 | cannot_parse 2, too_small 3 |
| davidpryan/generativefm1 | `f0d3dcdbb7d7` | gpl | 166 (20) | 14 | 33 | cannot_parse 1, too_small 3 |
| davidpryan/haunted-fm1 | `bd031d3722c5` | permissive | 22 (22) | 14 | 29 | 0 |
| davidpryan/witchbox | `4c58958716c8` | gpl | 42 (16) | 13 | 33 | too_small 2 |
| De-Pattern/Ravel_FM1 | `9e676aed0bdf` | gpl | 69 (11) | 18 | 33 | cannot_parse 1, too_small 4 |
| deabrewcontato-code/Selva1 | `68ea6cd9897c` | gpl | 138 (30) | 15 | 34 | too_small 4 |
| DeadActive/Felucca | `6ebf8fe6546d` | gpl | 206 (56) | 15 | 33 | cannot_parse 2, too_small 6 |
| DeadActive/FMDj | `10f98c0cc246` | gpl | 178 (75) | 15 | 33 | cannot_parse 2, too_small 6 |
| DeadActive/hortator | `7330f69475f0` | gpl | 192 (156) | 19 | 33 | cannot_parse 7, too_small 7 |
| Derfisfred/fm1-dx7-patch-importer | `585dd3c471ff` | permissive | 4 (0) | 0 | 0 | 0 |
| devrvega/BOP-1 | `2bb0d6b74574` | gpl | 61 (33) | 14 | 26 | cannot_parse 1, too_small 2 |
| devrvega/CRT-4 | `f302c434999e` | gpl | 71 (41) | 13 | 28 | cannot_parse 1, too_small 2 |
| devrvega/IND-1 | `fa09b621d6f4` | gpl | 48 (16) | 13 | 26 | cannot_parse 1, too_small 2 |
| devrvega/LCD-4 | `9676218821be` | gpl | 53 (21) | 13 | 26 | cannot_parse 1, too_small 2 |
| devrvega/ROM-1 | `3ffaac77790f` | gpl | 52 (25) | 13 | 31 | cannot_parse 1, too_small 2 |
| devrvega/SEQ-4 | `97c813564c3e` | gpl | 57 (28) | 13 | 28 | cannot_parse 1, too_small 2 |
| DimmKirr/core-fm1 | `eea1d0aca5fe` | gpl | 239 (67) | 14 | 33 | cannot_parse 3, too_small 18 |
| DimmKirr/setup-fm1-emulator | `94ac4ae52af0` | permissive | 0 (0) | 0 | 0 | 0 |
| Discodave-Glitch/eight-bells | `5a67521c2b6d` | permissive | 0 (0) | 0 | 0 | 0 |
| Discodave-Glitch/slipway | `34d1a6630db1` | permissive | 0 (0) | 0 | 0 | 0 |
| djStrombo/ChoralRootFM1-backup | `77c892bdc34b` | gpl | 137 (26) | 15 | 33 | too_small 3 |
| djStrombo/felucca-smk | `00197c1761d0` | gpl | 270 (30) | 16 | 33 | cannot_parse 1, too_small 7 |
| djStrombo/FM1-to-SMK37 | `dffe5d757c5c` | other | 93 (2) | 13 | 33 | too_small 3 |
| djStrombo/SMK-dee | `28ab1099dc38` | gpl | 251 (226) | 14 | 33 | cannot_parse 6, too_small 9 |
| djStrombo/SMK-zp12 | `587a8316287e` | gpl | 62 (39) | 13 | 29 | cannot_parse 1, too_small 7 |
| DLSR-S/Financial-Modelling-V1 | `a59580c4d29a` | none | 0 (0) | 0 | 0 | 0 |
| DocAtPrompt/awesome-fm-1 | `644524686b74` | permissive | 0 (0) | 0 | 0 | 0 |
| dolceglobalize/Felucca | `9cbab8c1e2d3` | gpl | 123 (30) | 13 | 33 | too_small 3 |
| domesticmouse/Felucca | `96f228c07ba7` | gpl | 163 (0) | 14 | 33 | cannot_parse 1, too_small 3 |
| doofywilsons-rgb/Tall-Horse-Firmware-Hub-Website | `c4ef43a7f2ce` | none | 0 (0) | 0 | 0 | 0 |
| doohinkus/Felucca | `863773419cad` | gpl | 166 (15) | 14 | 33 | cannot_parse 1, too_small 3 |
| dpwe/fm1-amy | `5244e5ef51da` | gpl | 94 (6) | 13 | 32 | cannot_parse 2, too_small 4 |
| drhl88/fm1-amb | `60dfbec46024` | other | 48 (16) | 13 | 26 | cannot_parse 1, too_small 2 |
| drok123/FM-Tracker | `51922dc71328` | none | 0 (0) | 0 | 0 | 0 |
| dsablic/sidou | `540b4f6088fc` | gpl | 274 (255) | 16 | 33 | too_small 24 |
| dspaudio/mc-1 | `10a2240d7f3c` | gpl | 97 (85) | 15 | 33 | too_small 3 |
| dspaudio/orbit | `c07bd1d87dcb` | gpl | 134 (14) | 15 | 33 | too_small 2 |
| dspaudio/orbit-web-emu | `533f6ca9a971` | gpl | 2 (2) | 13 | 14 | 0 |
| duncanwadsworth/fmini-1 | `f4204df32e09` | gpl | 171 (36) | 14 | 33 | cannot_parse 1, too_small 4 |
| durutti320/fm1-base | `71128a31acaf` | other | 48 (0) | 13 | 33 | cannot_parse 1, too_small 1 |
| dzwerg/analogBEAST | `1b578d927aac` | gpl | 202 (65) | 14 | 33 | cannot_parse 1, too_small 4 |
| echoe/Felucca_seq_per_track | `21fc592dab76` | gpl | 175 (41) | 14 | 33 | cannot_parse 1, too_small 3 |
| effdst/FOF | `30aa882bad0a` | gpl | 64 (44) | 13 | 29 | cannot_parse 3, too_small 2 |
| ehn96/Falua | `73fc26cf0a6c` | gpl | 98 (54) | 13 | 33 | cannot_parse 2, too_small 5 |
| ejtb76/FMLarynx | `63c086013bfe` | gpl | 29 (4) | 13 | 26 | cannot_parse 1, too_small 2 |
| eldontyrellcorp/Mini-Tone | `ed463887e577` | gpl | 170 (89) | 15 | 33 | cannot_parse 1, too_small 3 |
| Electro-Dig/function-acid-fw | `ffc9fa6f0eb6` | gpl | 37 (11) | 13 | 26 | too_small 2 |
| ELI7VH/Felucca | `66f1d2702f73` | gpl | 140 (57) | 13 | 33 | cannot_parse 1, too_small 3 |
| ELI7VH/melodee | `16daf99ea797` | gpl | 216 (138) | 14 | 33 | cannot_parse 3, too_small 7 |
| Erbubar23/bubba-machine | `50a33749aa62` | gpl | 124 (105) | 20 | 32 | too_small 8 |
| EremanSim/ChoralRootj-6 | `5b9104bc9711` | gpl | 203 (58) | 14 | 33 | cannot_parse 9, too_small 6 |
| erikdevos/glitchbox | `902868510b30` | gpl | 161 (27) | 14 | 33 | cannot_parse 2, too_small 3 |
| EthanJantz/fm1_open | `98ce13430c99` | other | 122 (0) | 13 | 24 | too_small 35 |
| etyrnal/ChoralRootFM1 | `13b0adba62b9` | gpl | 253 (139) | 15 | 34 | cannot_parse 23, too_small 8 |
| etyrnal/fm1-amb | `d9ef0a35823b` | other | 49 (6) | 13 | 26 | cannot_parse 1, too_small 2 |
| etyrnal/fm1-custom-fw | `add92d4237e2` | none | 0 (0) | 0 | 0 | 0 |
| etyrnal/MvaveFM1-Designer | `10e580eb1b2f` | permissive | 0 (0) | 0 | 0 | 0 |
| etyrnal/skiff | `c4bb2b4e9015` | gpl | 177 (123) | 14 | 33 | cannot_parse 3, too_small 2 |
| etyrnal/sloop-fm1 | `4ec1ac829fd2` | gpl | 124 (1) | 15 | 34 | too_small 3 |
| evanyerburgh/niagara-drift | `fe6d5e612c0d` | gpl | 53 (21) | 13 | 26 | cannot_parse 3, too_small 2 |
| feiyunwill/sloop-fm1 | `ba54ba5f0e7f` | gpl | 124 (0) | 15 | 34 | too_small 3 |
| felipesuarez-dev/april-os | `f2356c2f9030` | permissive | 0 (0) | 0 | 0 | 0 |
| fenderberg/fm1-nc-companion | `3b455ff449dd` | gpl | 173 (23) | 14 | 33 | cannot_parse 2, too_small 2 |
| FicusFicusov/CoralFlower | `f7a85eebbacf` | gpl | 185 (65) | 16 | 33 | cannot_parse 13, too_small 7 |
| fl164/fm1-fomni | `405ef41aef75` | gpl | 49 (5) | 13 | 26 | cannot_parse 1, too_small 2 |
| franalgaba/felucca-package-template | `8f18b9eca833` | none | 0 (0) | 0 | 0 | 0 |
| fred-tio/melodee | `ff56c867788c` | gpl | 219 (2) | 14 | 33 | cannot_parse 1, too_small 8 |
| fredster90001/sloop-fm1 | `bad8e822a6f4` | gpl | 116 (20) | 15 | 33 | too_small 2 |
| fuleo/Felucca-WebApp | `05c901d802d1` | gpl | 0 (0) | 0 | 0 | 0 |
| fuleo/fm1-guide | `161d57e1ac92` | none | 0 (0) | 0 | 0 | 0 |
| fuleo/fm1-linux-update | `fa850941dbd6` | permissive | 0 (0) | 0 | 0 | 0 |
| fvalente/GammaWave-FM1 | `d420b39cff02` | gpl | 157 (99) | 14 | 33 | cannot_parse 6, too_small 4 |
| Gadlele/Fantasma | `5351257efe55` | gpl | 168 (61) | 14 | 33 | cannot_parse 1, too_small 3 |
| gaumondp/patricktronics | `a6e5e28472fd` | gpl | 178 (29) | 14 | 33 | cannot_parse 1, too_small 6 |
| genkigenki/fm1-custom-fw | `9acc15ec0b1b` | none | 0 (0) | 0 | 0 | 0 |
| genkigenki/fm1-dub | `6a6b30786d36` | gpl | 50 (14) | 15 | 26 | cannot_parse 1, too_small 2 |
| genkigenki/fm1-fomni | `d05ba744279c` | gpl | 52 (23) | 13 | 26 | cannot_parse 1, too_small 3 |
| genkigenki/fm1-polly | `2e8a2bf9dd78` | gpl | 179 (35) | 15 | 33 | cannot_parse 2, too_small 43 |
| genkigenki/fm1-to-smk37 | `54252ffa2219` | other | 0 (0) | 0 | 0 | 0 |
| genkigenki/fm1-tracker-ketch | `87ff5794d4a5` | gpl | 71 (25) | 13 | 33 | cannot_parse 3, too_small 2 |
| genkigenki/fm1-x0x | `8af3731713ba` | gpl | 91 (16) | 13 | 32 | cannot_parse 2, too_small 5 |
| genkigenki/fmel-1 | `75ca839f6a17` | gpl | 36 (8) | 13 | 33 | too_small 2 |
| genkigenki/frodhes | `e49a49d29ac5` | gpl | 566 (380) | 15 | 33 | cannot_parse 8, too_small 14 |
| genkigenki/melodee | `84e2d97e958e` | gpl | 248 (31) | 14 | 33 | cannot_parse 6, too_small 8 |
| genkigenki/orbit | `07e3fed30e8e` | gpl | 134 (1) | 15 | 33 | too_small 2 |
| genkigenki/sloop-fm1 | `b4b61f407b72` | gpl | 154 (54) | 15 | 34 | too_small 6 |
| genkigenki/Speak37 | `81fa061b40e6` | gpl | 206 (74) | 14 | 33 | cannot_parse 3, too_small 7 |
| genkigenki/winampFM | `188124a1c7aa` | gpl | 81 (27) | 14 | 33 | too_small 2 |
| genkigenki/zen-1 | `2b4c4ade052a` | gpl | 79 (9) | 13 | 26 | cannot_parse 4, too_small 5 |
| glvno/matryoshka | `4d9ebea89222` | gpl | 59 (39) | 13 | 26 | too_small 3 |
| gonziWeb/sloop-fm1 | `79dd32bce73f` | gpl | 126 (9) | 15 | 34 | cannot_parse 1, too_small 3 |
| gospodindilly-ops/fm1-x0x | `47f8e4c4ad60` | gpl | 88 (3) | 13 | 32 | cannot_parse 2, too_small 4 |
| gospodindilly-ops/jangada | `07cce380aae0` | gpl | 124 (107) | 17 | 33 | too_small 2 |
| grant-vine/dabbl8 | `a152256f24b1` | gpl | 343 (263) | 13 | 33 | cannot_parse 1, too_small 17 |
| GraphicHealer/FeluccaSEQ | `6e2977d58079` | gpl | 162 (37) | 14 | 33 | cannot_parse 3, too_small 3 |
| GRiMMBIENT/grimm | `c597223c5c14` | gpl | 64 (0) | 13 | 29 | cannot_parse 3, too_small 2 |
| groundstation1/melodee | `1cccd6970e6e` | gpl | 248 (0) | 14 | 33 | cannot_parse 6, too_small 8 |
| groundstation1/take-taker | `8afbf0e2319d` | permissive | 1 (1) | 0 | 12 | 0 |
| Guizmoh/Kawa-Tracker-Fm1 | `047d21f6154f` | gpl | 55 (31) | 13 | 33 | too_small 3 |
| gybe808-dotcom/FeluccaWavetableOdeathMod | `2a661dc1e9a2` | none | 0 (0) | 0 | 0 | 0 |
| hericdk/fm1-quest | `0996503bfe83` | gpl | 107 (39) | 15 | 33 | too_small 2 |
| hericdk/nomanskyFM | `32e7f4c14a5e` | gpl | 85 (20) | 13 | 34 | too_small 3 |
| hericdk/winampFM | `54575a4bb81e` | gpl | 81 (7) | 14 | 33 | too_small 2 |
| Hi-Fi-Hopes/Zen-Lite | `e5112a6f0551` | gpl | 42 (18) | 13 | 32 | too_small 2 |
| hirakos999/MODELAR | `89475ca2586d` | other | 8 (8) | 13 | 32 | too_small 1 |
| hiroikezawa/brutal-fm | `d2081886152c` | gpl | 47 (23) | 14 | 26 | too_small 4 |
| HolidayMan/fm1-ios | `03b0ad3c5c50` | gpl | 9 (9) | 0 | 15 | cannot_parse 1, too_small 1 |
| hugelton/Felucca | `63f88ec18b71` | gpl | 163 (0) | 14 | 33 | cannot_parse 1, too_small 3 |
| hugelton/felucca-bsp | `33cac693903e` | other | 28 (28) | 13 | 26 | too_small 3 |
| hugelton/Felucca-Engines | `04ffe903eb87` | permissive | 11 (6) | 13 | 20 | 0 |
| hugelton/felucca-mirror | `fb9f11e6f6f5` | gpl | 0 (0) | 0 | 0 | 0 |
| hugelton/Felucca-WebApp | `b7947ad1da20` | gpl | 0 (0) | 0 | 0 | 0 |
| hunterxiong2026/fm1-felucca-editor-2026 | `937d395f36f9` | permissive | 0 (0) | 0 | 0 | 0 |
| hunterxiong2026/fm1-sloop-editor-2026 | `97a9d90e3a08` | permissive | 0 (0) | 0 | 0 | 0 |
| HyruleanHero1988/FM-1-Swap | `05250738fd90` | other | 0 (0) | 0 | 0 | 0 |
| I-am-MaxPower/drift-fm1 | `6cfac70ac312` | gpl | 52 (9) | 13 | 26 | cannot_parse 1, too_small 2 |
| ibrahim567gamal-hash/FluTour | `496d47979a36` | none | 0 (0) | 0 | 0 | 0 |
| ignis32/midimonitor_fm1 | `5458e0a2063e` | other | 59 (14) | 15 | 26 | cannot_parse 1, too_small 3 |
| ignis32/trireme_fm1 | `cc0a1efe4644` | gpl | 17 (16) | 0 | 26 | 0 |
| illuminus5/skiff | `c01fa1ed6192` | gpl | 189 (71) | 14 | 33 | cannot_parse 3, too_small 3 |
| InigoHernandez/mono2k | `030247212924` | gpl | 17 (17) | 15 | 32 | 0 |
| ioneng/fumi-1-ext | `7900e76d9fd1` | gpl | 67 (9) | 13 | 26 | cannot_parse 2, too_small 3 |
| ip2k/FM-1-RE | `c1a20d79f892` | permissive | 3 (0) | 0 | 22 | 0 |
| ip2k/lunar-modulator | `659c3aa9b88d` | permissive | 486 (87) | 15 | 33 | cannot_parse 8, too_small 18 |
| isod89/clipper-fm1 | `e69067211c46` | gpl | 158 (19) | 15 | 33 | cannot_parse 2, too_small 2 |
| isod89/sloop-fm1 | `ec9e53721cc5` | gpl | 124 (0) | 15 | 33 | too_small 3 |
| itoyohane/fm1-learning-web | `eb0a5081cdf0` | none | 0 (0) | 0 | 0 | 0 |
| izumoe/yanfei | `876d6cb4d2d4` | gpl | 200 (79) | 14 | 33 | cannot_parse 1, too_small 3 |
| jadamsowers/fm1-fimba | `0485ed0d387c` | gpl | 47 (14) | 13 | 26 | cannot_parse 1, too_small 2 |
| jahlib/sloop-fm1-go | `32946ed01d29` | gpl | 0 (0) | 0 | 0 | 0 |
| JalopyMusic/fm1-cartesive-fumi-1 | `44e050dd2ced` | gpl | 67 (10) | 13 | 26 | cannot_parse 2, too_small 3 |
| JalopyMusic/fm1-catacombius-notesorcery | `c13ac1b63f0d` | gpl | 122 (33) | 15 | 33 | too_small 4 |
| JalopyMusic/fm1-chancethemaker-felucca | `032758ad8e85` | gpl | 83 (0) | 13 | 33 | too_small 3 |
| JalopyMusic/fm1-charlesvestal-fm1-x0x | `00bff73d6f8c` | gpl | 88 (6) | 13 | 32 | cannot_parse 2, too_small 4 |
| JalopyMusic/fm1-deadactive-hortator | `2c2847e182f6` | gpl | 119 (56) | 19 | 33 | cannot_parse 3, too_small 4 |
| JalopyMusic/fm1-dspaudio-orbit | `4c119edd6081` | gpl | 127 (37) | 15 | 33 | too_small 2 |
| JalopyMusic/fm1-eli7vh-felucca | `84e8dc938a39` | gpl | 140 (2) | 13 | 33 | cannot_parse 1, too_small 3 |
| JalopyMusic/fm1-grant-vine-dabbl8 | `35266b6aaa93` | gpl | 259 (63) | 13 | 33 | cannot_parse 1, too_small 8 |
| JalopyMusic/fm1-hericdk-fm1-quest | `477069010c3a` | gpl | 97 (13) | 15 | 33 | too_small 2 |
| JalopyMusic/fm1-hugelton-felucca | `a4d7ca2e5d52` | gpl | 159 (0) | 14 | 33 | cannot_parse 1, too_small 3 |
| JalopyMusic/fm1-ip2k-lunar-modulator | `40c94300428a` | permissive | 479 (12) | 15 | 33 | cannot_parse 8, too_small 17 |
| JalopyMusic/fm1-jadamsowers-fm1-fimba | `b2b647b91bb3` | gpl | 47 (2) | 13 | 26 | cannot_parse 1, too_small 2 |
| JalopyMusic/fm1-jasonpersinger-ghoulbox-fm1-dungeon-synth | `7bc975e3e272` | gpl | 140 (55) | 13 | 33 | cannot_parse 1, too_small 3 |
| JalopyMusic/fm1-joshbartlettband-web-felucca-rainbow | `ac2609eea2dc` | gpl | 143 (12) | 13 | 33 | cannot_parse 2, too_small 3 |
| JalopyMusic/fm1-juanjiant-bit-jiant | `d3f42ae52e9e` | gpl | 138 (46) | 14 | 33 | cannot_parse 5, too_small 4 |
| JalopyMusic/fm1-milkboyg-ambii | `0afdeee1413b` | gpl | 252 (154) | 14 | 33 | too_small 9 |
| JalopyMusic/fm1-quixotic7-choralrootfm1 | `9814504f57e9` | gpl | 194 (53) | 14 | 33 | cannot_parse 3, too_small 7 |
| JalopyMusic/fm1-w0ts-optimist | `6aa01148828d` | gpl | 394 (380) | 15 | 35 | cannot_parse 9, too_small 18 |
| JalopyMusic/fm1-zednaked-jangada | `1accf9605283` | gpl | 119 (40) | 17 | 33 | too_small 2 |
| JalopyMusic/fm1-zvenson-dinghy | `929730019a9d` | gpl | 29 (1) | 13 | 26 | too_small 2 |
| JalopyMusic/fm1-zvenson-dxsloop | `17e395b878f0` | gpl | 91 (52) | 15 | 33 | cannot_parse 1, too_small 3 |
| JalopyMusic/fm1-zvenson-zp12 | `036ae8bd5d2e` | gpl | 40 (11) | 13 | 29 | cannot_parse 1, too_small 2 |
| jamesusmusic/fm1-studio-tess | `3a764d619c5f` | gpl | 268 (55) | 14 | 33 | cannot_parse 6, too_small 8 |
| jartificer/fm1-gm | `1bf76346b26f` | gpl | 53 (21) | 13 | 26 | cannot_parse 2, too_small 3 |
| jasonpersinger/ghoulbox-fm1-dungeon-synth | `f23fbc593f8a` | gpl | 177 (90) | 13 | 33 | cannot_parse 4, too_small 3 |
| jazzfolderPARLA/VintageS | `bb37ebe2769a` | gpl | 231 (83) | 14 | 33 | cannot_parse 4, too_small 8 |
| JB-Interactive/Felucca-Meow | `f21d6d69e88e` | gpl | 151 (37) | 14 | 33 | cannot_parse 1, too_small 3 |
| jbschooley/Virtual-FM-1 | `c52668953231` | gpl | 1100 (252) | 15 | 34 | cannot_parse 24, too_small 57 |
| jean80it2/fm1-x0x | `80b7d40cc946` | gpl | 81 (21) | 13 | 32 | cannot_parse 1, too_small 5 |
| jean80it2/Virtual-FM-1 | `9ff1ec6f985a` | gpl | 198 (46) | 13 | 33 | too_small 6 |
| jeymadcat-ops/SLICE64-FM-web | `c53210933fda` | none | 0 (0) | 0 | 0 | 0 |
| jmcn99/JIANT | `e2f60b3b472a` | gpl | 154 (57) | 14 | 33 | cannot_parse 6, too_small 4 |
| joakimeriksson/fm1-emu | `db8d472e62f3` | gpl | 32 (0) | 0 | 32 | too_small 1 |
| jogo-jpn/sloop-fm1 | `d315ad88c5fb` | gpl | 114 (0) | 15 | 33 | too_small 2 |
| johnskiller/driftseq | `9827a13d884c` | other | 64 (42) | 13 | 26 | cannot_parse 1, too_small 11 |
| johnskiller/Felucca | `c8eab234beb2` | gpl | 159 (0) | 14 | 33 | cannot_parse 1, too_small 3 |
| johnskiller/fm1-ctrl | `b429dd0e617a` | permissive | 49 (17) | 13 | 26 | cannot_parse 1, too_small 6 |
| johnskiller/fm1-emulator | `952c50085543` | gpl | 62 (59) | 12 | 23 | cannot_parse 2, too_small 17 |
| johnskiller/sloop-fm1 | `d2f3204f8a1c` | gpl | 114 (0) | 15 | 33 | too_small 2 |
| Jonbenderr/fm1-p6 | `8e7108bce690` | none | 0 (0) | 0 | 0 | 0 |
| joshbartlettband-web/Double-Rainbow | `3caf73c4cc5a` | gpl | 183 (14) | 14 | 33 | too_small 6 |
| joshbartlettband-web/felucca-rainbow | `0053aa8ac8ea` | gpl | 149 (24) | 13 | 33 | cannot_parse 3, too_small 4 |
| jpurcallas/fm1-emu | `61b51596d575` | gpl | 32 (0) | 0 | 32 | too_small 1 |
| jrdntnnr/DAKHMEH-FM-1 | `4db0f91b1690` | gpl | 78 (41) | 14 | 30 | cannot_parse 4, too_small 3 |
| jrdntnnr/sardab | `830bb5831fe8` | gpl | 216 (137) | 14 | 33 | cannot_parse 3, too_small 4 |
| jsmith13/fm_lab | `cf35dc26709e` | gpl | 36 (10) | 13 | 26 | too_small 3 |
| juanjiant-bit/JIANT | `dc8d025526ee` | gpl | 187 (10) | 14 | 33 | cannot_parse 8, too_small 4 |
| jukejutsu/FM2000 | `10787e18359a` | gpl | 34 (9) | 13 | 26 | too_small 2 |
| julesdg6/sloop-fm1 | `226ba29f6717` | gpl | 91 (0) | 15 | 33 | too_small 2 |
| justynroberts/fm1-finton | `8dc9edee324e` | gpl | 45 (20) | 13 | 26 | too_small 4 |
| jvitkauskas/fm1-backup | `0796a7009fc6` | none | 0 (0) | 0 | 0 | 0 |
| jvitkauskas/m-bootloader | `64b74d009e6d` | permissive | 29 (29) | 14 | 21 | too_small 1 |
| karlalex732-dotcom/RED-MASS-VAMPIRE-OS-FOR-M-VAVE-FM1 | `0fafe85aadb0` | gpl | 162 (95) | 14 | 33 | cannot_parse 1, too_small 3 |
| kdorland/Fantasma | `69acd429e062` | gpl | 168 (0) | 14 | 33 | cannot_parse 1, too_small 3 |
| Keitark/fm1-doom | `3d8a093ddadd` | gpl | 63 (63) | 12 | 24 | too_small 7 |
| Keitark/fm1-mdx | `9762d417d6f3` | gpl | 61 (61) | 0 | 27 | too_small 7 |
| Keitark/fm1-nes | `90d41c5e4807` | permissive | 102 (79) | 0 | 33 | too_small 16 |
| KelvinTTTT/Felucca | `129a4cf4e98e` | gpl | 158 (14) | 14 | 33 | cannot_parse 1, too_small 3 |
| KemstheSage/reggae-os | `89f0c8c0e858` | gpl | 171 (23) | 14 | 33 | cannot_parse 1, too_small 3 |
| Kenneth-Rakentine/Ravel-FM1 | `cc816dc9c97e` | gpl | 61 (22) | 18 | 33 | cannot_parse 1, too_small 4 |
| keremimo/melodee | `398ada1e09d8` | gpl | 280 (107) | 14 | 33 | cannot_parse 6, too_small 9 |
| keyboy250/fm1-x0x-acultur8 | `7bca4df442bd` | gpl | 135 (74) | 13 | 32 | cannot_parse 2, too_small 5 |
| kidbee85-beep/AMB-1-Evolved | `b8f0eb7f2098` | gpl | 55 (15) | 13 | 26 | cannot_parse 1, too_small 3 |
| kidbee85-beep/bunker-evolved | `c9bb0b1ac4a7` | gpl | 182 (29) | 14 | 33 | cannot_parse 1, too_small 4 |
| kidbee85-beep/cut-a-dor-release | `d9799abb84fe` | gpl | 60 (35) | 13 | 33 | cannot_parse 1, too_small 4 |
| kidbee85-beep/mutable-dreams | `52687d82c53b` | gpl | 0 (0) | 0 | 0 | 0 |
| Kiwi3p/fm1-deal-or-no-deal | `a8ffcf798967` | gpl | 52 (14) | 13 | 26 | cannot_parse 1, too_small 2 |
| klonecom/M-VAVE-FM1-LOADER--- | `7e4609784952` | none | 0 (0) | 0 | 0 | 0 |
| kmplngj/Felucca | `126da9dc2d94` | gpl | 238 (161) | 15 | 33 | cannot_parse 2, too_small 4 |
| kmplngj/Felucca-Engines | `7cf364f6c2ce` | permissive | 13 (6) | 13 | 20 | 0 |
| kmplngj/Felucca-WebApp | `a7a9dbbb95bb` | gpl | 1 (1) | 0 | 14 | 0 |
| kmplngj/m-bootloader | `df15966a4bcf` | permissive | 27 (4) | 14 | 21 | too_small 1 |
| kmplngj/m-flasher-legacy | `aeb061a03b7b` | other | 15 (15) | 0 | 20 | too_small 2 |
| konsumer/fm1-emu | `7856393bc82f` | gpl | 32 (0) | 0 | 32 | too_small 1 |
| konsumer/foma | `f39b49c492f3` | gpl | 32 (9) | 19 | 26 | too_small 2 |
| konsumer/fomajam | `6b788427e4a2` | gpl | 57 (19) | 19 | 26 | too_small 2 |
| kpalaniuk/gnomad-firmware | `3675315d9962` | gpl | 185 (104) | 15 | 33 | cannot_parse 3, too_small 11 |
| KrisGelero/fm1-loom | `c37c07af653c` | gpl | 44 (10) | 13 | 33 | cannot_parse 4, too_small 1 |
| Leeman1982/sloop-fm1 | `b77bf55e3bf8` | gpl | 124 (0) | 15 | 33 | too_small 3 |
| leomaimoni/fm1-bank-sender | `16b1b75fa251` | none | 0 (0) | 0 | 0 | 0 |
| leonardoMirabal/frodhes | `a8320e860c23` | gpl | 579 (28) | 15 | 33 | cannot_parse 10, too_small 14 |
| Leonidas0710/Felucca | `a53ecf428c29` | gpl | 163 (0) | 14 | 33 | cannot_parse 1, too_small 3 |
| LexLongcoding/ghoulbox-vst3 | `31a1d736dcb1` | gpl | 10 (10) | 0 | 19 | 0 |
| limiemohon-stack/ChoralRootFM1 | `198fc493f541` | gpl | 216 (7) | 15 | 33 | cannot_parse 12, too_small 6 |
| llozd/bytemania | `e670b35369f8` | gpl | 35 (9) | 13 | 26 | too_small 2 |
| luchak/fm1-x0x | `2e31c517ded3` | gpl | 91 (0) | 13 | 32 | cannot_parse 2, too_small 4 |
| luginf/fm1-emu | `43044b417fe1` | gpl | 31 (0) | 0 | 32 | too_small 1 |
| m-vave/fm1_open | `4c7496daac04` | other | 124 (2) | 13 | 24 | too_small 34 |
| majica99/mvave--fm11-genmus | `68e1b7cd0384` | gpl | 186 (46) | 14 | 33 | cannot_parse 8, too_small 4 |
| majica99/mvave-fm1-rebirth | `fbc8768327e4` | gpl | 123 (13) | 13 | 32 | cannot_parse 2, too_small 5 |
| manuelerdoes/oergelfm1 | `f5a4148f4a8c` | gpl | 164 (21) | 14 | 33 | cannot_parse 1, too_small 3 |
| Marcel-B/Felucca | `ac468ff32776` | gpl | 160 (15) | 14 | 33 | cannot_parse 1, too_small 3 |
| markterm/harbor | `7fd7b2810a11` | none | 0 (0) | 0 | 0 | 0 |
| math0ne/fm1-chord | `5117c27f094f` | gpl | 143 (7) | 13 | 33 | too_small 4 |
| mauricecalhoun/skiff | `a5d648132160` | gpl | 177 (0) | 14 | 33 | cannot_parse 3, too_small 2 |
| mauricecyril/fm1-to-smk37 | `d23bd32169c9` | other | 0 (0) | 0 | 0 | 0 |
| maykerache/felucca-bsp | `c4624a5b538f` | other | 30 (14) | 13 | 26 | too_small 3 |
| maykerache/Felucca-WebApp | `f35951a365f9` | gpl | 0 (0) | 0 | 0 | 0 |
| mediaworkbench/Felucca | `9be30a5f2c1a` | gpl | 182 (44) | 14 | 33 | cannot_parse 4, too_small 4 |
| megagott/launchparty-fm1 | `efa6e4e24687` | gpl | 0 (0) | 0 | 0 | 0 |
| megagott/mycelium-fm1 | `750eb125e285` | gpl | 0 (0) | 0 | 0 | 0 |
| Mello-D/JIANT | `2f0d6f50c102` | gpl | 187 (0) | 14 | 33 | cannot_parse 8, too_small 4 |
| mene311/Felucca | `d3038ca96204` | gpl | 149 (17) | 14 | 33 | cannot_parse 1, too_small 3 |
| mene311/fm1-banks | `f47b11b9035b` | other | 0 (0) | 0 | 0 | 0 |
| mene311/fm1-pulses-felucca | `1c09071e2019` | none | 0 (0) | 0 | 0 | 0 |
| mentalcells/ambwave | `c1932a5788b2` | gpl | 159 (52) | 13 | 33 | cannot_parse 1, too_small 4 |
| merthsoft/flipper-fm1-recovery | `df88b862a479` | permissive | 3 (3) | 0 | 16 | 0 |
| merthsoft/sloop-fm1 | `1ce6a8949a24` | gpl | 184 (123) | 15 | 34 | too_small 4 |
| michaeljsmalley/synthesthetic | `aa186aa866f5` | gpl | 138 (44) | 15 | 34 | cannot_parse 2, too_small 4 |
| MikeTsak/Evanders-Music-Box--FM-1-LARP-firmware | `53c32342efb4` | other | 10 (10) | 12 | 31 | too_small 1 |
| millette/Felucca | `7414269c4392` | gpl | 131 (0) | 13 | 33 | cannot_parse 1, too_small 3 |
| millette/fm1-fomni | `378dfacbf476` | gpl | 49 (5) | 13 | 26 | cannot_parse 1, too_small 2 |
| millette/fm1-x0x | `9ae360b64af9` | gpl | 85 (5) | 13 | 32 | cannot_parse 1, too_small 4 |
| MohammadMahdiYazdanshad/FM1-PROJECT | `96f808ec51b0` | none | 0 (0) | 0 | 0 | 0 |
| monch1962/felucca-engines | `65fe10466365` | permissive | 8 (1) | 13 | 20 | 0 |
| monch1962/mvave-fm1-mpe | `715d1ca97df3` | gpl | 163 (34) | 14 | 33 | cannot_parse 2, too_small 3 |
| mosurabeats/FM1--Sp12-Turbo-Build | `f4bb214451b1` | gpl | 42 (7) | 13 | 29 | cannot_parse 1, too_small 2 |
| Motheraudio/TheCove | `f3f41a79ccda` | gpl | 159 (3) | 14 | 33 | cannot_parse 1, too_small 3 |
| mpereira/felucca-server | `a5ffc0272b9b` | other | 0 (0) | 0 | 0 | 0 |
| mr-devboy/fm1-dx7-patch-importer | `581b5a5489b2` | permissive | 4 (0) | 0 | 0 | 0 |
| Mr-Roboto/fm1-x0x-rmx | `c7a633d01dca` | gpl | 111 (48) | 13 | 32 | cannot_parse 2, too_small 7 |
| mrsheez/Felucca | `13dd66517d2f` | gpl | 148 (59) | 14 | 33 | cannot_parse 2, too_small 3 |
| muffintopmusic/fm1_openknob | `c9513f6cfa73` | other | 122 (1) | 13 | 24 | too_small 35 |
| MXMP1/x-seq | `635d1534f90f` | none | 0 (0) | 0 | 0 | 0 |
| myldy20/BRKLOOP | `a1c88d1b26e5` | gpl | 125 (1) | 15 | 34 | too_small 3 |
| Nacsez/FMER | `2c7fe329ed98` | gpl | 210 (169) | 16 | 33 | too_small 30 |
| Narti-Live/fm1-fm-plaits | `2884f45c043c` | none | 0 (0) | 0 | 0 | 0 |
| NicholasPratt/Prysm | `f4f0bb458b45` | gpl | 52 (28) | 15 | 33 | too_small 3 |
| Nicodesy06/FM1-MOVE | `42fc1af2a2ab` | gpl | 126 (43) | 16 | 33 | too_small 2 |
| nilselathome/sloop-fm1-editor-regex | `31b47acb5164` | gpl | 114 (0) | 15 | 33 | too_small 2 |
| NoodleSushi/dinghy | `706403b81682` | gpl | 31 (4) | 13 | 26 | too_small 2 |
| NOVALENTI/fm1-polyseq | `b028d3f8ebb7` | none | 98 (86) | 16 | 28 | too_small 23 |
| npi3pak/fm1-gator | `92f923e0b9fe` | gpl | 171 (25) | 13 | 27 | too_small 5 |
| nullbeing/fm1-amb | `d4a211c7f450` | other | 48 (0) | 13 | 26 | cannot_parse 1, too_small 2 |
| nullbeing/fm1-custom-fw | `cb5796c24e2e` | none | 0 (0) | 0 | 0 | 0 |
| nzimas/bigorna | `cd6bd4b784cf` | gpl | 51 (37) | 13 | 26 | cannot_parse 2, too_small 3 |
| nzimas/tonitor | `a240bc182b55` | gpl | 56 (31) | 13 | 32 | cannot_parse 5, too_small 2 |
| obbymaul-mp3/3IS | `9575631bd8f0` | gpl | 188 (37) | 16 | 33 | cannot_parse 12, too_small 9 |
| ocean/estampie | `b12a484005d1` | gpl | 206 (96) | 14 | 33 | cannot_parse 4, too_small 3 |
| ocean/FM-SWITCH | `93d20704821f` | none | 0 (0) | 0 | 0 | 0 |
| ocean/fm1-site | `f876bad3ae8d` | other | 0 (0) | 0 | 0 | 0 |
| ocean/FM1Kit | `806af62318e1` | permissive | 0 (0) | 0 | 0 | 0 |
| okumurari2/maku | `fa6d95aa4c28` | gpl | 142 (50) | 13 | 33 | cannot_parse 1, too_small 3 |
| ordenador/Felucca-Engines | `c46e0086f69b` | permissive | 8 (0) | 13 | 20 | 0 |
| oscillr/DUELL | `3133625de68e` | gpl | 296 (268) | 17 | 33 | cannot_parse 7, too_small 8 |
| osmaav/melodee | `fe0cca6c7d63` | gpl | 286 (40) | 14 | 33 | cannot_parse 6, too_small 10 |
| OwenKirby/carnac-os | `6387a21932aa` | gpl | 102 (102) | 12 | 33 | cannot_parse 1, too_small 10 |
| p-orlov/Ecolucca | `ec4f12e2a5e8` | gpl | 61 (21) | 13 | 33 | too_small 3 |
| PatttF/fm-106 | `db39e046e3ef` | gpl | 81 (39) | 16 | 32 | cannot_parse 1, too_small 6 |
| pbarilla/fm1-x0x | `397c8a8a2142` | gpl | 85 (5) | 13 | 32 | cannot_parse 1, too_small 4 |
| pbarilla/fumi-1 | `ec7537fc87cc` | gpl | 67 (2) | 13 | 29 | cannot_parse 1, too_small 3 |
| pbarilla/ghoulbox-fm1-dungeon-synth | `3e642b33e342` | gpl | 174 (15) | 13 | 33 | cannot_parse 4, too_small 3 |
| pbarilla/orbit | `4d85cf8ae8b5` | gpl | 112 (43) | 15 | 33 | too_small 2 |
| pfkellogg/fm1-bonus-box | `069d0234d132` | none | 7 (7) | 0 | 0 | cannot_parse 1, too_small 3 |
| pfkellogg/fm1-sustain-footswitch | `9a5f89f04087` | none | 0 (0) | 0 | 0 | 0 |
| phc101/fm1-emu | `ecd2b0b1a865` | gpl | 32 (0) | 0 | 32 | too_small 1 |
| pianomansam/fm1-vnl | `be0653869d04` | other | 2 (1) | 13 | 0 | 0 |
| PierreArnaudGUYOT/FM1-Oktowave-Firmware | `60619dbb28e5` | gpl | 169 (27) | 14 | 33 | cannot_parse 1, too_small 3 |
| pingywon/fm1-easy-guide | `d711151ea14c` | permissive | 0 (0) | 0 | 0 | 0 |
| PistolPineapple/skiff | `69b05f618f70` | gpl | 175 (14) | 14 | 33 | cannot_parse 3, too_small 2 |
| pomegnechristianfrank-gif/site-web-FM1 | `d5f85c2f3219` | none | 0 (0) | 0 | 0 | 0 |
| Pongtrometer/jangada | `4ed8411dd681` | gpl | 122 (7) | 17 | 33 | too_small 2 |
| probonopd/fm1-emulator | `23f424d2303b` | gpl | 62 (23) | 0 | 31 | too_small 18 |
| pwalsh/felucca-bsp | `6eee4bf97346` | other | 30 (6) | 13 | 26 | too_small 3 |
| Qubestar/Saibertin-S-FM | `9c3f5a89f3d8` | none | 0 (0) | 0 | 0 | 0 |
| Quixotic7/ChoralRootFM1 | `7d97982a7db3` | gpl | 253 (11) | 15 | 34 | cannot_parse 24, too_small 8 |
| Quixotic7/FM1VST | `a528812d238a` | gpl | 209 (209) | 12 | 21 | too_small 75 |
| Quixotic7/MvaveFM1-Designer | `0ecd189b7b3a` | permissive | 0 (0) | 0 | 0 | 0 |
| Quixotic7/PurpleMonkeyFM1 | `b574e75dd1dc` | gpl | 204 (69) | 14 | 33 | cannot_parse 3, too_small 8 |
| Rastapopolix/melodee-tess | `7e1a9570bcfb` | gpl | 219 (14) | 14 | 33 | cannot_parse 1, too_small 8 |
| RayDNoper/fm1-fomnium | `d0f66357c557` | gpl | 51 (17) | 13 | 26 | cannot_parse 2, too_small 2 |
| relyt29/melodee | `01a78bdf0fb0` | gpl | 223 (4) | 14 | 33 | cannot_parse 1, too_small 8 |
| Reytian/fm1-luogu | `94a2eea78d09` | other | 25 (25) | 0 | 17 | cannot_parse 2 |
| Reytian/fm1-min1 | `14d8ddf6390c` | gpl | 49 (17) | 13 | 33 | cannot_parse 1, too_small 2 |
| Reytian/fm1-trio | `7c92b7a18184` | other | 18 (18) | 13 | 15 | 0 |
| rgrvmusic/fluyt-logue | `5f47c1687ebf` | gpl | 19 (19) | 14 | 18 | too_small 3 |
| rgrvmusic/fluyt-web | `2639ed65c5a3` | other | 5 (5) | 12 | 0 | too_small 2 |
| rgrvmusic/harbor | `80f9724a9fb5` | none | 0 (0) | 0 | 0 | 0 |
| risseraka/fm1-tracker-ketch | `d8ebe8641f4f` | gpl | 75 (37) | 13 | 33 | cannot_parse 4, too_small 3 |
| ristiisa/sloop-fm1 | `e2a9a2f72533` | gpl | 117 (60) | 15 | 33 | too_small 2 |
| rocketlaunch-io/Felucca | `27f87d10fd90` | gpl | 130 (19) | 13 | 33 | cannot_parse 1, too_small 3 |
| rondlite/felucca-rainbow-dutch | `c893b18909c7` | gpl | 149 (0) | 13 | 33 | cannot_parse 3, too_small 4 |
| ruppert/fmini-1 | `ab0f5c83d9c3` | gpl | 177 (40) | 14 | 33 | cannot_parse 1, too_small 4 |
| ruppert/organvave-1 | `2432096ca972` | gpl | 99 (73) | 13 | 33 | too_small 4 |
| RustyPawz/fm1-HYP1 | `2c6c47650349` | other | 281 (76) | 14 | 26 | cannot_parse 5, too_small 15 |
| s0fx2/YamahaDX7_to_FM-1 | `21e3e26c0add` | gpl | 0 (0) | 0 | 0 | 0 |
| Sab0tenb0y/Felucca | `df4498e8d959` | gpl | 163 (0) | 14 | 33 | cannot_parse 1, too_small 3 |
| sabliran/sloop-web-emu | `bbfd8e5b3bfc` | gpl | 2 (1) | 13 | 14 | 0 |
| Sanderat/Blight- | `08ed4a7d5c8c` | none | 0 (0) | 0 | 0 | 0 |
| sbegueria/fm1-dub | `ed4909178958` | gpl | 50 (6) | 15 | 26 | cannot_parse 1, too_small 2 |
| sceic/fm1-felucca-editor-2026 | `4ec3fe2f426a` | permissive | 0 (0) | 0 | 0 | 0 |
| schwartzworld/shifl | `79fe37dff470` | gpl | 111 (61) | 15 | 33 | too_small 2 |
| seajaysec/386-DX-FM1-KaraokeBot | `87b2e8b2b157` | gpl | 67 (47) | 13 | 26 | cannot_parse 1, too_small 2 |
| seajaysec/fm-static | `0fa627434b7a` | gpl | 0 (0) | 0 | 0 | 0 |
| seajaysec/fm1-dx7-patch-importer | `ba4593ed88f0` | permissive | 0 (0) | 0 | 0 | 0 |
| seanohollaren/fm1-doom | `bde88936a14e` | gpl | 19 (19) | 0 | 21 | too_small 3 |
| SeattleUser0/OrangeCat | `f95dcc2871f0` | gpl | 346 (127) | 15 | 33 | cannot_parse 7, too_small 10 |
| SeattleUser0/skiff | `2b350ac2bd88` | gpl | 179 (21) | 14 | 33 | cannot_parse 3, too_small 2 |
| seclorum/lunar-modulator.seclorum | `a5a096ffe77c` | permissive | 297 (92) | 15 | 33 | too_small 8 |
| severak/wolfware | `84b8cbee8aa2` | none | 0 (0) | 0 | 0 | 0 |
| shinobi/ChoralRootFM1-DOREMI | `51efe2414486` | gpl | 213 (17) | 15 | 33 | cannot_parse 12, too_small 6 |
| SikkenWorks/B1-Drawbar-Organ | `0a37b92e2d32` | gpl | 112 (93) | 14 | 34 | too_small 8 |
| SikkenWorks/BEETLE | `e8586b3bdddb` | gpl | 311 (291) | 14 | 33 | too_small 17 |
| SikkenWorks/ETCH | `a00ec8684c38` | gpl | 305 (235) | 16 | 33 | too_small 13 |
| Simant49/lunar-modulator-looper | `6c030732a060` | permissive | 227 (30) | 15 | 33 | too_small 7 |
| simonjohansson/fm1-emulator | `519a13b879d7` | gpl | 62 (0) | 0 | 31 | too_small 18 |
| sinscum/DIRGE-darksynth | `d83a4886e064` | gpl | 180 (15) | 13 | 33 | cannot_parse 5, too_small 3 |
| sirpearson/fm-1-monomachine | `527da33beb3d` | gpl | 47 (15) | 13 | 35 | cannot_parse 1, too_small 2 |
| smememe/fm1-macropad-patch | `0e6b52c247d4` | permissive | 0 (0) | 0 | 0 | 0 |
| smhgzll/sloopy-sloop-32 | `a0c1cfc8562c` | gpl | 59 (59) | 14 | 28 | cannot_parse 1, too_small 5 |
| smhulme/sloop-ios-8trk | `ec3cfc53af71` | gpl | 0 (0) | 0 | 0 | 0 |
| smhulme/sloop-web-8trk | `9974f8f67fc6` | gpl | 0 (0) | 0 | 0 | 0 |
| SpeakingColors/mwave-fm1-linux-vst | `3aac65ebb636` | gpl | 0 (0) | 0 | 0 | 0 |
| SPIKE-the-Percussionist/noiz_demons | `4fe0f1afb4d9` | gpl | 171 (12) | 14 | 33 | cannot_parse 1, too_small 3 |
| spinkham/Felucca | `7392d9c8f0fc` | gpl | 142 (10) | 13 | 33 | cannot_parse 1, too_small 3 |
| spinkham/felucca-try | `ac3ba1b58c5b` | gpl | 0 (0) | 0 | 0 | 0 |
| spinkham/Felucca-WebApp | `2e4d39178bdf` | gpl | 0 (0) | 0 | 0 | 0 |
| spinkham/fm1-emulator | `18a8ccec50e5` | gpl | 28 (6) | 13 | 26 | too_small 4 |
| Spiralfractalplugins/spiralfm1 | `6e0fd2b824fd` | gpl | 116 (110) | 15 | 33 | too_small 3 |
| stanleygurvich/FeluccaMPE | `817f5b8f3fd9` | gpl | 163 (12) | 14 | 33 | cannot_parse 1, too_small 3 |
| StephanBeutel/Virtual-FM-1 | `21605e266775` | gpl | 678 (38) | 14 | 33 | cannot_parse 3, too_small 27 |
| stevensnasdell-cmd/dock | `11db45adc55b` | gpl | 272 (68) | 14 | 33 | cannot_parse 7, too_small 9 |
| styvesgoupil/frasil | `a7313f27221f` | other | 15 (15) | 13 | 32 | 0 |
| swe24-phon/fm1-mod-ref | `134bcc46f11d` | none | 0 (0) | 0 | 0 | 0 |
| SylarPu-X/nightfall-fm1 | `3861e7a5e4fe` | gpl | 18 (18) | 12 | 32 | too_small 1 |
| synthi/fm1-1971 | `d422a998f2d9` | gpl | 220 (54) | 14 | 33 | cannot_parse 3, too_small 8 |
| synthi/fm1-ctl | `298b637e961b` | other | 139 (32) | 15 | 33 | cannot_parse 1, too_small 40 |
| synthi/grimm | `43e710d7a004` | gpl | 64 (0) | 13 | 29 | cannot_parse 3, too_small 2 |
| synthi/jangada | `6dfbc5a68e77` | gpl | 124 (6) | 17 | 33 | too_small 2 |
| synthi/melodee-tess | `3e125e7836b0` | gpl | 219 (0) | 14 | 33 | cannot_parse 1, too_small 8 |
| synthi/niagara-drift | `a319c5a558c2` | gpl | 53 (10) | 13 | 26 | cannot_parse 3, too_small 2 |
| synthi/tonitor | `964e3ec1e078` | gpl | 47 (10) | 13 | 32 | cannot_parse 3, too_small 3 |
| tank12123/FM1 | `3e5f912dc007` | none | 0 (0) | 0 | 0 | 0 |
| teekesti/harbour-hortator | `57bb903c54ae` | none | 26 (26) | 15 | 14 | too_small 1 |
| tensor-programming/fm1-t1 | `bea0fd38fbeb` | gpl | 181 (18) | 15 | 33 | cannot_parse 1, too_small 3 |
| TerkWerX/Crepuscular_Homunculus | `c55a1a5db541` | gpl | 80 (57) | 17 | 33 | too_small 3 |
| thebrodi/fm1-haave | `24e75c83e52c` | gpl | 170 (15) | 14 | 33 | cannot_parse 1, too_small 3 |
| thefriendlyhedgehog/FM-Cat1 | `820251d823eb` | gpl | 58 (21) | 13 | 26 | cannot_parse 1, too_small 2 |
| thegiantsnail/fm1-workbench-public | `e35315b7ea81` | gpl | 0 (0) | 0 | 0 | 0 |
| theNoisery/fN-1 | `1505d777590f` | other | 126 (6) | 18 | 24 | too_small 34 |
| TheShrimpBlimp/pigeon | `b18b4cbcbdbb` | gpl | 261 (161) | 14 | 33 | cannot_parse 2, too_small 11 |
| thingsapart/fm1-studio | `76372746ca85` | gpl | 37 (37) | 13 | 28 | too_small 1 |
| thingsapart/sloop-fm1 | `cb6dedcec257` | gpl | 112 (0) | 15 | 33 | too_small 2 |
| thomasgregorymarsden-code/Felucca-opx | `1ef13fed6d70` | gpl | 170 (42) | 14 | 33 | cannot_parse 1, too_small 4 |
| TonyMilton/frodhes | `159333d6e185` | gpl | 579 (13) | 15 | 33 | cannot_parse 10, too_small 14 |
| trustcoinmining/FM1-DDR3MIG-ug586 | `6318218dcdff` | none | 0 (0) | 0 | 0 | 0 |
| trustcoinmining/TCM-FMx | `d7e423cd12ef` | none | 0 (0) | 0 | 0 | 0 |
| twaroshinto/AEther | `a8802a6ca4c8` | other | 8 (8) | 13 | 30 | 0 |
| Vaayaa/rift-fw | `52562e739564` | gpl | 33 (11) | 13 | 32 | too_small 2 |
| vikramrojo/maqam-dev | `8bd7db8492cc` | gpl | 119 (34) | 15 | 33 | too_small 2 |
| vrcvs/Felucca | `3a91058d4a40` | gpl | 163 (0) | 14 | 33 | cannot_parse 1, too_small 3 |
| w0ts/fm1-emulator | `6ce95ec7b3d2` | gpl | 28 (0) | 13 | 26 | too_small 4 |
| w0ts/optimist | `8c392850ef67` | gpl | 600 (521) | 15 | 35 | cannot_parse 25, too_small 27 |
| weavejam/Felucca | `ebdb3935ad75` | gpl | 164 (8) | 14 | 33 | cannot_parse 2, too_small 3 |
| weavejam/sloop-fm1 | `1bbdc6e0bc6f` | gpl | 125 (9) | 15 | 33 | cannot_parse 1, too_small 3 |
| Wesleyx88/mvave-fm1-drone | `891da07cdfe4` | gpl | 208 (2) | 14 | 33 | cannot_parse 1, too_small 4 |
| Wesleyx88/mvave-fm1-drum | `98cb90a118ee` | gpl | 55 (2) | 13 | 29 | cannot_parse 1, too_small 5 |
| Wesleyx88/mvave-fm1-emu | `dc50f04ce0d7` | gpl | 32 (0) | 0 | 32 | too_small 1 |
| Wesleyx88/mvave-fm1-gen | `0945f5ba447b` | gpl | 50 (6) | 15 | 26 | cannot_parse 1, too_small 2 |
| Wesleyx88/mvave-fm1-legosythn | `ef98611549ac` | gpl | 650 (161) | 15 | 35 | cannot_parse 25, too_small 29 |
| Wesleyx88/mvave-fm1-mooge | `fcfaceeebb8e` | gpl | 171 (5) | 14 | 33 | cannot_parse 1, too_small 4 |
| wesmattison/snoop37 | `655458d8a5c8` | gpl | 154 (0) | 15 | 34 | too_small 6 |
| wicked-wix/felucca-bsp | `b899449bbf3a` | other | 30 (0) | 13 | 26 | too_small 3 |
| WillCMcC/kidboy-firmware | `2e400c2dfcf3` | gpl | 208 (49) | 14 | 33 | cannot_parse 1, too_small 11 |
| wochende/FM-1-Felucca-Tutor | `20c73515f99c` | none | 3 (3) | 0 | 0 | 0 |
| wonky-roger/fm1-emu | `0a59fb935708` | gpl | 32 (0) | 0 | 32 | too_small 1 |
| workeffortwaste/JIANT | `ade4e8940f74` | gpl | 146 (42) | 14 | 33 | cannot_parse 6, too_small 4 |
| Wulgaren/Araminta | `fc2b68d377bf` | gpl | 173 (120) | 14 | 33 | cannot_parse 3, too_small 3 |
| wzkxh/fork_dinghy | `91c9a78035b0` | gpl | 29 (0) | 13 | 26 | too_small 2 |
| xerydian/Felucca | `9c143148830f` | gpl | 163 (8) | 14 | 33 | cannot_parse 1, too_small 3 |
| xerydian/felucca-smk | `cc13e146f11d` | gpl | 269 (14) | 16 | 33 | cannot_parse 1, too_small 7 |
| xerydian/fm1-emu | `19177bd79914` | gpl | 32 (0) | 0 | 32 | too_small 1 |
| xerydian/fm1-to-smk37 | `6af085f17156` | other | 0 (0) | 0 | 0 | 0 |
| xerydian/hortator | `7e3415971c58` | gpl | 158 (46) | 19 | 33 | cannot_parse 3, too_small 7 |
| xerydian/lunar-modulator | `7cc70572490e` | permissive | 227 (2) | 15 | 33 | too_small 7 |
| xerydian/orbit | `b50203206a6a` | gpl | 112 (17) | 15 | 33 | too_small 3 |
| xerydian/skiff | `eec4c1011a9d` | gpl | 165 (50) | 14 | 33 | cannot_parse 3, too_small 3 |
| xerydian/zp12 | `f90efac6bb96` | gpl | 40 (6) | 13 | 29 | cannot_parse 1, too_small 2 |
| y6zkcqnf5r-hue/fm1-fm80s | `171c51fae0c4` | gpl | 110 (7) | 15 | 33 | too_small 2 |
| y6zkcqnf5r-hue/fm1-trawler | `153f4f4433f1` | gpl | 55 (55) | 18 | 20 | too_small 15 |
| zakariachowdhury/flowstate-fm1 | `39625601f030` | gpl | 130 (66) | 15 | 33 | cannot_parse 2, too_small 6 |
| zednaked/jangada | `249eb434b810` | gpl | 126 (4) | 17 | 33 | too_small 2 |
| zisonzishen/crate-fm1 | `27c13ea30938` | gpl | 53 (32) | 13 | 26 | too_small 3 |
| zisonzishen/sloop-consort | `8b24360e8278` | gpl | 0 (0) | 0 | 0 | 0 |
| zisonzishen0415-stack/sloop-consort | `af74b1bf6bed` | gpl | 0 (0) | 0 | 0 | 0 |
| zreese/felucca-rainbow | `65ee5090220d` | gpl | 149 (2) | 13 | 33 | cannot_parse 3, too_small 4 |
| zvenson/dinghy | `d44df7db09b9` | gpl | 29 (0) | 13 | 26 | too_small 2 |
| zvenson/dxsloop | `eeec0a6c1c7f` | gpl | 101 (38) | 15 | 33 | cannot_parse 1, too_small 4 |
| zvenson/fm1doom | `640bc2dbdc69` | gpl | 213 (189) | 16 | 33 | cannot_parse 1, too_small 45 |
| zvenson/zp12 | `6dc9c5cfa841` | gpl | 58 (1) | 13 | 29 | cannot_parse 1, too_small 5 |
| ZzpsS/M1n1Le55 | `36ef0a3600ff` | permissive | 55 (55) | 12 | 21 | too_small 6 |

Not scored: 262 duplicate, 2 empty, 0 unreachable. Unresolved (no repository found): Felucca Salt, Felucca 8 Patterns.

## Traceability

| Requirement | Checks | Result |
|---|---|---|
| R-AUDIT-1 | C-AUDIT-SCORE, C-AUDIT-LEAK | PASS |
| R-AUDIT-2 | C-AUDIT-PIN | PASS |
| R-AUDIT-3 | C-AUDIT-LEAK | PASS |
| R-AUDIT-4 | C-AUDIT-JPLAG, C-AUDIT-CONTROL | PASS |
| R-AUDIT-5 | C-AUDIT-SCORE | PASS |
