# Similarity audit 4128c4ce2303

- Set: full; run: https://github.com/japes98/small-beeps/actions/runs/40443965822
- JPlag 6.3.0 (sha256 `5f2c21e8b88ed771`), Java image `eclipse-temurin@sha256:dbb43d81099eec91e0800226ed2296d03146ee7857165b95112372ad0d67e87f`

- Control: raspberrypi/pico-examples at `4c3a3dc0196d`, 244 files
- The control's longest match with any target it is not related to: **35 tokens**; a pair of ours fails above **59 tokens** (margin 24).
- Control-related targets (the control matches them above 100 tokens; each judged against the control's own score there plus the margin): none
- Target files scored: 20902 (one copy per blob)
- Base code (JPlag and the text check leave out what is in it): `vendor/jieli-sdk/include_lib`, 2 files; `vendor/plaits`, 127 files, checksums verified, only for `firmware/demos/plaits/`
- A pass of its own for our files under firmware/demos/plaits/ (12): the control's longest match there 24 tokens, so a pair fails above **48 tokens**

## Checks

| Check | Result | Detail |
|---|---|---|
| C-AUDIT-JPLAG | PASS | jar sha256 matches; Java image pinned by digest |
| C-AUDIT-BASE | PASS | our files outside firmware/demos/plaits/ (29): base code vendor/jieli-sdk/include_lib (2 files); our files under firmware/demos/plaits/ (12): base code vendor/jieli-sdk/include_lib (2 files) and vendor/plaits (127 files, checksums verified) |
| C-AUDIT-PIN | PASS | 597 targets fetched at their pinned commit and tree; 1 unavailable |
| C-AUDIT-CONTROL | PASS | 244 control files; its longest match with an unrelated target 35 tokens; 0 of 597 targets control-related (above 100 tokens; at most 10% allowed) |
| C-AUDIT-SCORE | PASS | 0 of our file pairs above 59 tokens (the control's 35 plus 24; for a control-related target, its own score plus 24); our files under firmware/demos/plaits/: above 48 tokens (the control's 24 under that base code plus 24) |
| C-AUDIT-TEXT | PASS | 10 of our files JPlag could not score or matched with nothing (demos/plaits/plaits_voice.h, demos/plaits/include/plaits_pre.h, demos/plaits/include/stddef.h, src/audio.h, src/font.c, src/input.h, src/midi.h, src/midi_out.h, src/store.h, src/ui.h), compared as text with 20902 target files; 0 pairs an exact copy or at or above 0.50 of 24-character pieces |
| C-AUDIT-LEAK | PASS | no line of a target file (24 characters or more) in the report |

## Our top file pairs

| Our file | Target (places with this file) | Path | Licence | Longest | Max | Avg |
|---|---|---|---|---|---|---|
| src/fm.c | bunglesociety/modular-one (1) | tests/m1_tour.c | gpl | 47 | 0.118 | 0.100 |
| src/fm.c | Guizmoh/Kawa-Tracker-Fm1 (1) | source/firmware/src/kawa_data.c | gpl | 47 | 0.086 | 0.044 |
| src/fm.c | JalopyMusic/fm1-deadactive-hortator (2) | firmware/src/pages.c | gpl | 46 | 0.217 | 0.121 |
| src/fm.c | DeadActive/hortator (2) | firmware/src/pages.c | gpl | 46 | 0.206 | 0.120 |
| src/fm.c | dspaudio/mc-1 (1) | tests/presets_012.h | gpl | 46 | 0.167 | 0.112 |
| src/input.c | rgrvmusic/fluyt-logue (1) | tools/check_rows_microkorg2.c | gpl | 46 | 0.120 | 0.116 |
| src/fm.c | TerkWerX/Crepuscular_Homunculus (1) | firmware/gen/terkinstein_presets.h | gpl | 46 | 0.111 | 0.096 |
| src/fm.c | DeadActive/hortator (1) | tests/b2trx_test.c | gpl | 46 | 0.084 | 0.076 |
| src/fm.c | DeadActive/hortator (1) | tests/ktrx_test.c | gpl | 46 | 0.084 | 0.076 |
| src/fm.c | DeadActive/hortator (1) | tests/sdtrx_test.c | gpl | 46 | 0.084 | 0.075 |
| src/fm.c | devrvega/SEQ-4 (1) | firmware/src/seq/s4_music.c | gpl | 46 | 0.084 | 0.066 |
| src/fm.c | hiroikezawa/brutal-fm (1) | firmware/brutal/bfm_ui.c | gpl | 46 | 0.084 | 0.040 |
| src/fm.c | illuminus5/skiff (1) | firmware/src/params.c | gpl | 46 | 0.084 | 0.062 |
| src/fm.c | SeattleUser0/OrangeCat (1) | firmware/src/braids/pb_dig_d.h | gpl | 46 | 0.084 | 0.065 |
| src/fm.c | thomasgregorymarsden-code/Felucca-opx (1) | firmware/src/eng_opx.c | gpl | 46 | 0.084 | 0.034 |
| src/fm.c | adamcharleswilsonmusic-code/Fart-Machine-One (7) | firmware/src/dsp/om_data.h | gpl | 45 | 0.536 | 0.143 |
| src/fm.c | SikkenWorks/ETCH (1) | firmware/fm1-native/native_help_chapters.h | gpl | 45 | 0.424 | 0.138 |
| src/fm.c | ip2k/lunar-modulator (2) | firmware/display/panel_probe.c | permissive | 45 | 0.278 | 0.127 |
| src/fm.c | DimmKirr/core-fm1 (1) | firmware/src/audio/engines/fm6/fm6_fmlab.c | gpl | 45 | 0.228 | 0.121 |
| src/fm.c | JalopyMusic/fm1-juanjiant-bit-jiant (1) | firmware/src/menu_items.c | gpl | 45 | 0.152 | 0.107 |

## Our files

| File | Tokens | State |
|---|---|---|
| demos/plaits/bench.c | 231 | scored |
| demos/plaits/plaits_demo.c | 94 | scored |
| demos/plaits/plaits_voice.cc | 73 | scored |
| demos/plaits/plaits_voice.h | - | no match |
| demos/plaits/sftest.c | 110 | scored |
| demos/plaits/include/inttypes.h | 24 | scored |
| demos/plaits/include/math.h | 19 | scored |
| demos/plaits/include/plaits_pre.h | - | not scorable by JPlag: fewer tokens than JPlag's minimum match of 12 (TOO_SMALL); compared by the text check instead |
| demos/plaits/include/stddef.h | - | not scorable by JPlag: fewer tokens than JPlag's minimum match of 12 (TOO_SMALL); compared by the text check instead |
| demos/plaits/runtime/cxx.cc | 28 | scored |
| demos/plaits/runtime/mem.c | 56 | scored |
| demos/plaits/runtime/softfloat.c | 471 | scored |
| src/arp.c | 503 | scored |
| src/arp.h | 44 | scored |
| src/audio.c | 52 | scored |
| src/audio.h | - | no match |
| src/fm.c | 547 | scored |
| src/fm.h | 65 | scored |
| src/fm_play.c | 2075 | scored |
| src/font.c | - | not scorable by JPlag: fewer tokens than JPlag's minimum match of 12 (TOO_SMALL); compared by the text check instead |
| src/gfx.c | 200 | scored |
| src/input.c | 384 | scored |
| src/input.h | - | no match |
| src/irq.c | 75 | scored |
| src/lcd.c | 144 | scored |
| src/main.c | 167 | scored |
| src/midi.c | 299 | scored |
| src/midi.h | - | no match |
| src/midi_out.c | 203 | scored |
| src/midi_out.h | - | no match |
| src/patches.c | 23 | scored |
| src/probe.c | 134 | scored |
| src/saving.c | 209 | scored |
| src/sb.h | 115 | scored |
| src/screen.c | 75 | scored |
| src/spectrum.c | 185 | scored |
| src/start.c | 20 | scored |
| src/store.c | 539 | scored |
| src/store.h | - | no match |
| src/ui.h | - | no match |
| src/views.c | 1685 | scored |

## The text check (our files JPlag cannot score)

Each is compared with every target file, one per blob: the share of its normalised text's 24-character pieces found in the target file (containment), and whether the bytes are the same (exact). A pair fails at 0.50 or above, or when exact.

| Our file | Target (places with this file) | Path | Licence | Containment | Exact |
|---|---|---|---|---|---|
| demos/plaits/plaits_voice.h | dsablic/sidou (1) | app/thump_out.h | gpl | 0.091 | no |
| demos/plaits/plaits_voice.h | dsablic/sidou (1) | core/player/song_ctl.h | gpl | 0.080 | no |
| demos/plaits/plaits_voice.h | dsablic/sidou (1) | core/sid/sid.h | gpl | 0.080 | no |
| demos/plaits/plaits_voice.h | abcdaniel/lunar-modulator (3) | engines/state/fm1_num.h | permissive | 0.077 | no |
| demos/plaits/plaits_voice.h | AveyCole/FM1-Field (2) | app/third_party/pvaac/pvmp4audiodecoder_api.h | other | 0.077 | no |
| demos/plaits/plaits_voice.h | dsablic/sidou (1) | app/panel.h | gpl | 0.077 | no |
| demos/plaits/plaits_voice.h | dsablic/sidou (1) | app/screen.h | gpl | 0.077 | no |
| demos/plaits/plaits_voice.h | dsablic/sidou (1) | app/settings.h | gpl | 0.077 | no |
| demos/plaits/plaits_voice.h | dsablic/sidou (1) | core/fx/fx_slots.h | gpl | 0.077 | no |
| demos/plaits/plaits_voice.h | Erbubar23/bubba-machine (1) | core/bm_fm.h | gpl | 0.077 | no |
| demos/plaits/plaits_voice.h | NicholasPratt/Prysm (1) | plugin/core/prysm_core.h | gpl | 0.077 | no |
| demos/plaits/plaits_voice.h | tensor-programming/fm1-t1 (1) | firmware/src/torso_t1.h | gpl | 0.077 | no |
| demos/plaits/plaits_voice.h | abcdaniel/lunar-modulator (3) | engines/include/fm1_meta.h | permissive | 0.074 | no |
| demos/plaits/plaits_voice.h | abcdaniel/lunar-modulator (3) | engines/include/fm1_mfx_host.h | permissive | 0.074 | no |
| demos/plaits/plaits_voice.h | abcdaniel/lunar-modulator (1) | engines/include/fm1_mod.h | permissive | 0.074 | no |
| demos/plaits/plaits_voice.h | abcdaniel/lunar-modulator (2) | engines/include/fm1_seq.h | permissive | 0.074 | no |
| demos/plaits/plaits_voice.h | abcdaniel/lunar-modulator (1) | engines/include/fm1_tele.h | permissive | 0.074 | no |
| demos/plaits/plaits_voice.h | abcdaniel/lunar-modulator (3) | engines/midi_fx/fm1_arp.h | permissive | 0.074 | no |
| demos/plaits/plaits_voice.h | abcdaniel/lunar-modulator (1) | engines/mod/fm1_mp.h | permissive | 0.074 | no |
| demos/plaits/plaits_voice.h | abcdaniel/lunar-modulator (4) | engines/mod/mod_mi.h | permissive | 0.074 | no |

## Targets

| Target | Commit | Licence | Files (new) | Ours longest | Control longest | Not parsed |
|---|---|---|---|---|---|---|
| 2bbb/fm1-firmware-collection | `8ba398c87a31` | permissive | 0 (0) | 0 | 0 | 0 |
| 2bbb/glitchbox | `093d57670d9b` | gpl | 167 (167) | 45 | 33 | 0 |
| 3x-x5/anatomy-fm1 | `4839e5c30228` | none | 0 (0) | 0 | 0 | 0 |
| 7oi/sloop-fm1 | `bb6e53f67bec` | gpl | 124 (116) | 42 | 33 | 0 |
| aaasss01061997-bot/Fm-Music- | `cf01ef464cbb` | none | 0 (0) | 0 | 0 | 0 |
| abcdaniel/Felucca | `ac6bfcbd76ee` | gpl | 142 (96) | 45 | 33 | 0 |
| abcdaniel/fm1-custom-fw | `51a35ccb5d62` | none | 0 (0) | 0 | 0 | 0 |
| abcdaniel/fm1-x0x | `201e5c5c1ac0` | gpl | 85 (77) | 42 | 32 | 0 |
| abcdaniel/lunar-modulator | `64209e3c0822` | permissive | 465 (455) | 42 | 33 | 0 |
| abcdaniel/sloop-fm1 | `a1c5d68767ae` | gpl | 101 (72) | 42 | 33 | 0 |
| aceyprime/zen-1 | `ec9295233ea6` | gpl | 79 (48) | 26 | 26 | 0 |
| actuallysparky/FM-1-Unholy-Union-generative-drone-firmware | `273e9b511f1f` | gpl | 176 (87) | 45 | 33 | 0 |
| adamcharleswilsonmusic-code/Fart-Machine-One | `5e49a216c18c` | gpl | 58 (25) | 45 | 26 | 0 |
| adamcharleswilsonmusic-code/RAMBEAVER | `a13eb60137ac` | gpl | 0 (0) | 0 | 0 | 0 |
| adamcharleswilsonmusic-code/Trumpagotchi | `976b6e65dc96` | gpl | 71 (29) | 45 | 33 | 0 |
| admali777/fm1-sloop-ui | `ec9e53721cc5` | gpl | 124 (0) | 42 | 33 | 0 |
| adriandomc/dino-synth | `8c13a1edd096` | gpl | 126 (34) | 42 | 34 | 0 |
| AETHER-ENGINEERS/fm1-emu | `84d3c3b460d9` | gpl | 32 (32) | 28 | 32 | 0 |
| afta8/fm1-emu | `7196a9f45bb1` | gpl | 31 (0) | 28 | 32 | 0 |
| ajsoriar/Felucca | `172753762439` | gpl | 166 (35) | 45 | 33 | 0 |
| AL-255/FM-1-RE | `ec832f281ca1` | permissive | 3 (3) | 17 | 22 | 0 |
| AlexanderSeel/fm1-emu_win | `932968f43329` | gpl | 32 (2) | 28 | 32 | 0 |
| AlexanderSeel/TheReFmB1rth | `5e2cc6fa89cb` | none | 63 (63) | 21 | 27 | 0 |
| AlexPavAi/Felucca-m-vave-fm1-firmware- | `1e838e17e170` | gpl | 67 (44) | 42 | 33 | 0 |
| AlexPavAi/sloop-fm1 | `d691ba7b2d92` | gpl | 93 (38) | 42 | 33 | 0 |
| amacias/octo-vave | `375f500115a7` | permissive | 0 (0) | 0 | 0 | 0 |
| amalahama/sloop-SMK37 | `f2b44c219b8a` | gpl | 91 (17) | 42 | 33 | 0 |
| ambientsoundartist/Felucca | `5738617968a2` | gpl | 163 (12) | 45 | 33 | 0 |
| amineferjani/Back_FM | `0af0e78f0820` | none | 0 (0) | 0 | 0 | 0 |
| andreahaku/Felucca | `727f272015da` | gpl | 123 (75) | 45 | 33 | 0 |
| andreahaku/fm1-chord | `377235d9f39a` | gpl | 139 (46) | 45 | 33 | 0 |
| andrerezemini/fm1-cartridge | `d7659e4f8535` | gpl | 335 (189) | 45 | 34 | 0 |
| andrerezemini/sloop-lab | `3b83f31020f5` | gpl | 118 (36) | 42 | 33 | 0 |
| andrixb/OPQuencer | `b992291caa6e` | gpl | 161 (32) | 45 | 33 | 0 |
| anonymousacademe/FM-1-GrooveDeck | `20bf2de4a687` | gpl | 31 (10) | 26 | 26 | 0 |
| anonymousacademe/FM-1-TripDeck | `a977f53558b7` | gpl | 36 (9) | 34 | 26 | 0 |
| ant25fr/JIANT | `5300f79a2e3d` | gpl | 187 (156) | 42 | 33 | 0 |
| AntonioAltea/fmel-1 | `3a4de21bf015` | gpl | 37 (14) | 26 | 26 | 0 |
| apiel/fm1-tribe | `29664b28c9d8` | gpl | 132 (78) | 42 | 32 | 0 |
| arksat/melodee | `1a71d999dcf4` | gpl | 217 (198) | 42 | 33 | 0 |
| arksat/sloop-fm1 | `d3a8385f56ce` | gpl | 115 (19) | 42 | 33 | 0 |
| aroum/fm1-custom-fw | `8b24193a1904` | none | 0 (0) | 0 | 0 | 0 |
| artqcid/fm1_open | `24beff707163` | other | 124 (124) | 45 | 24 | 0 |
| atachh/sloop-fm1 | `8fad1a15ff59` | gpl | 114 (0) | 42 | 33 | 0 |
| AveyCole/FM1-Field | `88bf7d4307bb` | other | 758 (758) | 44 | 35 | 0 |
| awolace/IVee | `ba0658641404` | none | 0 (0) | 0 | 0 | 0 |
| babage/fm1_open | `5d3eac2573db` | other | 120 (35) | 45 | 24 | 0 |
| babage/JIANT | `b66729d38a2e` | gpl | 187 (11) | 42 | 33 | 0 |
| balancechiang/fm1-midi-converter | `3cd6c1fb29b3` | gpl | 0 (0) | 0 | 0 | 0 |
| balancechiang/fm1_alt | `b178ac43c25f` | other | 122 (13) | 45 | 24 | 0 |
| barrule/fm1-emu | `7ca5b96c9e82` | gpl | 32 (0) | 28 | 32 | 0 |
| Batora07/ChoralRootFM1 | `aa5875af20e3` | gpl | 213 (142) | 45 | 33 | 0 |
| bbmusichun/fm1_open | `4d266850f8a4` | other | 124 (0) | 45 | 24 | 0 |
| beashoko/april-os | `6b65734fad08` | permissive | 0 (0) | 0 | 0 | 0 |
| bedwards/sloop-fm1 | `e421e4362e41` | gpl | 88 (25) | 42 | 33 | 0 |
| beingsane/Felucca | `20c275e39f75` | gpl | 123 (5) | 45 | 33 | 0 |
| beingsane/fm1-firmware-patcher | `4cfab6024551` | permissive | 0 (0) | 0 | 0 | 0 |
| beingsane/fm1-loom | `97d6726022a0` | gpl | 44 (44) | 44 | 33 | 0 |
| benbadio/hera-fm1 | `76b7ee8484d2` | gpl | 85 (53) | 42 | 33 | 0 |
| benny-sparra/fm1-dx7-patch-importer | `458b151102d2` | permissive | 4 (4) | 0 | 0 | 0 |
| birkmann/fm1-dub | `ed4909178958` | gpl | 50 (18) | 34 | 26 | 0 |
| birkmann/Ravel_FM1 | `8d89317f92bb` | gpl | 69 (50) | 40 | 33 | 0 |
| bitedits/fm1-emu | `c1c045fc067d` | gpl | 32 (0) | 28 | 32 | 0 |
| bonszaimusic/caravel | `97022acaa6fc` | gpl | 209 (115) | 45 | 33 | 0 |
| bratta/fm1-manager | `64cad0932ae2` | none | 0 (0) | 0 | 0 | 0 |
| briwil/Felucca | `44abc098d5f6` | gpl | 137 (70) | 45 | 33 | 0 |
| bunglesociety/modular-one | `bd6e6d056656` | gpl | 78 (37) | 47 | 33 | 0 |
| burn-again/Felucca-Sog | `e3788eee038e` | gpl | 165 (20) | 45 | 33 | 0 |
| carlosshawplatino/Felucca | `2da8ee0f3e8a` | gpl | 163 (3) | 45 | 33 | 0 |
| cartesive/fumi-1 | `6a20fa387cf6` | gpl | 67 (17) | 27 | 26 | 0 |
| catacombius/NoteSorcery | `73d6cdd6d2a0` | gpl | 138 (89) | 42 | 33 | 0 |
| CDMGaming/TILT-FM | `618a4889f66d` | gpl | 164 (27) | 45 | 33 | 0 |
| cdodd/felucca-vst | `91addeeb989b` | gpl | 14 (14) | 25 | 18 | 0 |
| ChanceTheMaker/doom-fm1-smk | `b705a7b06e01` | gpl | 103 (87) | 26 | 26 | 0 |
| ChanceTheMaker/Felucca | `1a345338f6eb` | gpl | 83 (44) | 42 | 33 | 0 |
| ChanceTheMaker/felucca-smk | `9a73145a6ed6` | gpl | 281 (129) | 45 | 33 | 0 |
| ChanceTheMaker/gamedude-fm1-smk | `09fe97f82cf7` | gpl | 125 (71) | 26 | 26 | 0 |
| ChanceTheMaker/NESynth-FM1-SMK | `25c7b7ed6da1` | gpl | 148 (119) | 26 | 32 | 0 |
| ChanceTheMaker/sloop-fm1-sim | `3dbf57077410` | gpl | 0 (0) | 0 | 0 | 0 |
| charlesvestal/fm1-amb | `188b0a42f20a` | other | 9 (9) | 34 | 19 | 0 |
| charlesvestal/fm1-base | `aa2b3bc8f790` | other | 49 (2) | 24 | 33 | 0 |
| charlesvestal/fm1-ctl | `e181b4a1ac15` | other | 94 (94) | 42 | 33 | 0 |
| charlesvestal/fm1-fomni | `7e7547f384fe` | gpl | 50 (10) | 45 | 26 | 0 |
| charlesvestal/fm1-loom | `534a5201c41a` | gpl | 46 (24) | 44 | 33 | 0 |
| charlesvestal/fm1-mocky | `facab5da0add` | gpl | 40 (11) | 22 | 26 | 0 |
| charlesvestal/fm1-monk | `793710689adb` | gpl | 53 (21) | 32 | 26 | 0 |
| charlesvestal/fm1-polly | `62cd07ea7c95` | gpl | 137 (63) | 42 | 33 | 0 |
| charlesvestal/fm1-radio | `c9113b5eceb9` | other | 665 (7) | 26 | 35 | 0 |
| charlesvestal/fm1-reader | `2f49d91c142b` | permissive | 3 (2) | 18 | 14 | 0 |
| charlesvestal/fm1-velocity | `8f62ce0d968c` | gpl | 47 (13) | 22 | 32 | 0 |
| charlesvestal/fm1-x0x | `54194c54bb01` | gpl | 91 (19) | 42 | 32 | 0 |
| charlesvestal/melodee | `6a30eba1a789` | gpl | 178 (98) | 42 | 33 | 0 |
| chasebrey-ops/dinghy | `d44df7db09b9` | gpl | 29 (2) | 26 | 26 | 0 |
| chinotto1/unibox | `bd184eba6857` | gpl | 70 (38) | 35 | 32 | 0 |
| chmess/fm1-keyboard-academy | `315af1a06e5a` | other | 130 (10) | 45 | 32 | 0 |
| cicloid/awesome-fm-1 | `81d31a7611df` | permissive | 0 (0) | 0 | 0 | 0 |
| claudehenchoz/orbit | `dc3cd08482fa` | gpl | 134 (118) | 42 | 33 | 0 |
| cmlarsen/fm1-rocket-os | `d269df962a6d` | gpl | 166 (113) | 42 | 33 | 0 |
| cmlarsen/fm1-zed | `218b8fd736fd` | gpl | 159 (16) | 45 | 33 | 0 |
| Co-oscillator/Loom-FM-1 | `a11bc8ce6ce7` | gpl | 176 (49) | 45 | 33 | 0 |
| codeine4563-netizen/fm1-pico-recovery-guia-en-espa-ol-para-uso-de-raspberry-pi-pico-rp2040- | `066f5eb1f931` | none | 0 (0) | 0 | 0 | 0 |
| colofonbrigade/hortator | `ea643d42fc2f` | permissive | 0 (0) | 0 | 0 | 0 |
| cotrino/fm1-betis-mode | `84d6ad4e8b6a` | other | 134 (14) | 45 | 24 | 0 |
| cotrino/fm1-cofrade | `a508afafacfb` | other | 126 (3) | 45 | 24 | 0 |
| CoydeLau/sloop-fm1 | `fa9ce5742f4a` | gpl | 109 (19) | 42 | 33 | 0 |
| curist/fm1-clk320-probe | `50aa741b11ba` | gpl | 91 (15) | 42 | 32 | 0 |
| czietz/fm1-dx7-patch-importer | `3b69028a51f0` | permissive | 3 (0) | 0 | 0 | 0 |
| czietz/fm1-firmware-patcher | `58569017a4f9` | permissive | 0 (0) | 0 | 0 | 0 |
| czietz/fm1-read-voice | `b7c539f2ca4a` | none | 0 (0) | 0 | 0 | 0 |
| d0pe1/md-one | `6db198515da0` | gpl | 109 (68) | 42 | 26 | 0 |
| danilokosky/fm1_VA_Moog | `5238cfab4061` | other | 126 (3) | 45 | 24 | 0 |
| DarkHelmet67/fm1-insert-coin | `7588e7425b99` | gpl | 47 (32) | 26 | 26 | 0 |
| davidozz0/clipper-smk | `42cb76ed6a49` | gpl | 167 (79) | 43 | 33 | 0 |
| davidozz0/fmini-smk | `ab0f5c83d9c3` | gpl | 177 (45) | 45 | 33 | 0 |
| davidpryan/generativefm1 | `f0d3dcdbb7d7` | gpl | 166 (20) | 45 | 33 | 0 |
| davidpryan/haunted-fm1 | `bd031d3722c5` | permissive | 22 (22) | 30 | 29 | 0 |
| davidpryan/witchbox | `4c58958716c8` | gpl | 42 (16) | 28 | 33 | 0 |
| De-Pattern/Ravel_FM1 | `30222a222fa4` | gpl | 70 (23) | 40 | 33 | 0 |
| deabrewcontato-code/Selva1 | `68ea6cd9897c` | gpl | 138 (29) | 42 | 34 | 0 |
| DeadActive/Felucca | `6ebf8fe6546d` | gpl | 206 (56) | 45 | 33 | 0 |
| DeadActive/FMDj | `10f98c0cc246` | gpl | 178 (75) | 45 | 33 | 0 |
| DeadActive/hortator | `2d7a0b19f5c3` | gpl | 195 (160) | 46 | 33 | 0 |
| DeadActive/skiff | `c01fa1ed6192` | gpl | 189 (146) | 45 | 33 | 0 |
| Derfisfred/fm1-dx7-patch-importer | `585dd3c471ff` | permissive | 4 (0) | 0 | 0 | 0 |
| devrvega/BOP-1 | `2bb0d6b74574` | gpl | 61 (33) | 34 | 26 | 0 |
| devrvega/CRT-4 | `f302c434999e` | gpl | 71 (41) | 45 | 28 | 0 |
| devrvega/IND-1 | `fa09b621d6f4` | gpl | 48 (16) | 34 | 26 | 0 |
| devrvega/LCD-4 | `9676218821be` | gpl | 53 (21) | 29 | 26 | 0 |
| devrvega/ROM-1 | `3ffaac77790f` | gpl | 52 (25) | 25 | 31 | 0 |
| devrvega/SEQ-4 | `97c813564c3e` | gpl | 57 (28) | 46 | 28 | 0 |
| DimmKirr/core-fm1 | `9d6e82f7b721` | gpl | 1387 (956) | 45 | 35 | 0 |
| DimmKirr/setup-fm1-emulator | `5b20b0257228` | permissive | 0 (0) | 0 | 0 | 0 |
| DimmKirr/setup-fm1-toolchain | `e94bbde88481` | permissive | 0 (0) | 0 | 0 | 0 |
| Discodave-Glitch/eight-bells | `a36785b2bdae` | permissive | 0 (0) | 0 | 0 | 0 |
| Discodave-Glitch/slipway | `34d1a6630db1` | permissive | 0 (0) | 0 | 0 | 0 |
| djStrombo/ChoralRootFM1-backup | `77c892bdc34b` | gpl | 137 (26) | 42 | 33 | 0 |
| djStrombo/felucca-smk | `00197c1761d0` | gpl | 270 (30) | 45 | 33 | 0 |
| djStrombo/FM1-to-SMK37 | `dffe5d757c5c` | other | 93 (2) | 42 | 33 | 0 |
| djStrombo/SMK-dee | `28ab1099dc38` | gpl | 251 (96) | 42 | 33 | 0 |
| djStrombo/SMK-zp12 | `587a8316287e` | gpl | 62 (39) | 26 | 29 | 0 |
| DLSR-S/Financial-Modelling-V1 | `a59580c4d29a` | none | 0 (0) | 0 | 0 | 0 |
| DocAtPrompt/awesome-fm-1 | `644524686b74` | permissive | 0 (0) | 0 | 0 | 0 |
| dolceglobalize/Felucca | `9cbab8c1e2d3` | gpl | 123 (30) | 45 | 33 | 0 |
| domesticmouse/Felucca | `96f228c07ba7` | gpl | 163 (0) | 45 | 33 | 0 |
| doofywilsons-rgb/Tall-Horse-Firmware-Hub-Website | `c4ef43a7f2ce` | none | 0 (0) | 0 | 0 | 0 |
| doohinkus/Felucca | `5bad1cb6fc8a` | gpl | 163 (16) | 45 | 33 | 0 |
| doohinkus/Felucca-Engines | `2bb5a5a118d9` | permissive | 15 (10) | 35 | 20 | 0 |
| doug-parks/furybox | `caeff7626006` | gpl | 165 (16) | 45 | 33 | 0 |
| dpwe/fm1-amy | `5244e5ef51da` | gpl | 94 (6) | 42 | 32 | 0 |
| dreamsofbacon/lsdj-burrito | `24dfff43b3fe` | gpl | 0 (0) | 0 | 0 | 0 |
| dreamsofbacon/lsdj-burrito-src | `f3fc16c68820` | gpl | 138 (20) | 26 | 26 | 0 |
| drhl88/fm1-amb | `60dfbec46024` | other | 48 (13) | 34 | 26 | 0 |
| drok123/FM-Tracker | `51922dc71328` | none | 0 (0) | 0 | 0 | 0 |
| dsablic/fm1-custom-fw | `9b7e9b5cfd9b` | none | 0 (0) | 0 | 0 | 0 |
| dsablic/sidou | `6d86587db8d3` | gpl | 288 (267) | 42 | 33 | 0 |
| dspaudio/mc-1 | `10a2240d7f3c` | gpl | 97 (85) | 46 | 33 | 0 |
| dspaudio/orbit | `c07bd1d87dcb` | gpl | 134 (14) | 42 | 33 | 0 |
| dspaudio/orbit-web-emu | `533f6ca9a971` | gpl | 2 (2) | 17 | 14 | 0 |
| duncanwadsworth/fmini-1 | `f4204df32e09` | gpl | 171 (31) | 45 | 33 | 0 |
| durutti320/felucca-bsp | `33cac693903e` | other | 28 (9) | 19 | 26 | 0 |
| durutti320/fm1-base | `71128a31acaf` | other | 48 (13) | 24 | 33 | 0 |
| durutti320/fm1-loom | `e88f2e00ec60` | gpl | 44 (7) | 44 | 33 | 0 |
| dzwerg/analogBEAST | `beef99b68d1c` | gpl | 209 (72) | 45 | 33 | 0 |
| easyhard007/Felucca-RDX | `00dc20e1444d` | gpl | 182 (57) | 45 | 33 | 0 |
| echoe/Felucca_seq_per_track | `21fc592dab76` | gpl | 175 (35) | 45 | 33 | 0 |
| effdst/FOF | `30aa882bad0a` | gpl | 64 (44) | 42 | 29 | 0 |
| egorgam/fm1-neverhood | `265798dc2c76` | permissive | 21 (21) | 25 | 21 | 0 |
| ehn96/Falua | `73fc26cf0a6c` | gpl | 98 (53) | 42 | 33 | 0 |
| ejtb76/FMLarynx | `63c086013bfe` | gpl | 29 (4) | 26 | 26 | 0 |
| eldontyrellcorp/Mini-Tone | `3327369b445d` | gpl | 176 (101) | 45 | 33 | 0 |
| Electro-Dig/function-acid-fw | `96333e35f780` | gpl | 40 (14) | 38 | 28 | 0 |
| ELI7VH/Felucca | `66f1d2702f73` | gpl | 140 (57) | 45 | 33 | 0 |
| ELI7VH/melodee | `16daf99ea797` | gpl | 216 (138) | 42 | 33 | 0 |
| emilystgeist/fiendbox | `f23fbc593f8a` | gpl | 177 (105) | 45 | 33 | 0 |
| Erbubar23/bubba-machine | `038020e1da72` | gpl | 131 (112) | 44 | 32 | 0 |
| EremanSim/ChoralRootj-6 | `5b9104bc9711` | gpl | 203 (58) | 45 | 33 | 0 |
| erikdevos/glitchbox | `902868510b30` | gpl | 161 (25) | 45 | 33 | 0 |
| EthanJantz/fm1_open | `98ce13430c99` | other | 122 (0) | 45 | 24 | 0 |
| etyrnal/ChoralRootFM1 | `13b0adba62b9` | gpl | 253 (139) | 45 | 34 | 0 |
| etyrnal/fm1-amb | `d9ef0a35823b` | other | 49 (6) | 34 | 26 | 0 |
| etyrnal/fm1-custom-fw | `add92d4237e2` | none | 0 (0) | 0 | 0 | 0 |
| etyrnal/MvaveFM1-Designer | `10e580eb1b2f` | permissive | 0 (0) | 0 | 0 | 0 |
| etyrnal/skiff | `c4bb2b4e9015` | gpl | 177 (50) | 45 | 33 | 0 |
| etyrnal/sloop-fm1 | `4ec1ac829fd2` | gpl | 124 (0) | 42 | 34 | 0 |
| evanyerburgh/niagara-drift | `7697c404ffa1` | gpl | 53 (21) | 29 | 26 | 0 |
| fantasmoslam/dinobox-fm1 | `e4dd949ff56b` | gpl | 188 (76) | 45 | 33 | 0 |
| FBNFRTG/drift-fm1 | `8ec7ba709302` | gpl | 115 (28) | 45 | 33 | 0 |
| feiyunwill/sloop-fm1 | `ba54ba5f0e7f` | gpl | 124 (0) | 42 | 34 | 0 |
| felipesuarez-dev/april-os | `f2356c2f9030` | permissive | 0 (0) | 0 | 0 | 0 |
| fenderberg/fm1-nc-companion | `9fb62359b137` | gpl | 190 (49) | 45 | 33 | 0 |
| FicusFicusov/CoralFlower | `f7a85eebbacf` | gpl | 185 (65) | 45 | 33 | 0 |
| fl164/fm1-fomni | `405ef41aef75` | gpl | 49 (5) | 45 | 26 | 0 |
| ForrestPanda/backbeat | `1e73c9d2073b` | gpl | 87 (59) | 45 | 33 | 0 |
| franalgaba/felucca-package-template | `8f18b9eca833` | none | 0 (0) | 0 | 0 | 0 |
| fred-tio/melodee | `ff56c867788c` | gpl | 219 (2) | 42 | 33 | 0 |
| fredster90001/sloop-fm1 | `3cc126ab7b8f` | gpl | 126 (22) | 42 | 33 | 0 |
| fuleo/Felucca-WebApp | `05c901d802d1` | gpl | 0 (0) | 0 | 0 | 0 |
| fuleo/fm1-guide | `161d57e1ac92` | none | 0 (0) | 0 | 0 | 0 |
| fuleo/fm1-linux-update | `fa850941dbd6` | permissive | 0 (0) | 0 | 0 | 0 |
| fvalente/GammaWave-FM1 | `ff61ba1783f0` | gpl | 157 (98) | 45 | 33 | 0 |
| Gadlele/Fantasma | `5351257efe55` | gpl | 168 (61) | 45 | 33 | 0 |
| gaumondp/patricktronics | `a6e5e28472fd` | gpl | 178 (29) | 45 | 33 | 0 |
| genkigenki/fm1-custom-fw | `9acc15ec0b1b` | none | 0 (0) | 0 | 0 | 0 |
| genkigenki/fm1-dub | `6a6b30786d36` | gpl | 50 (6) | 34 | 26 | 0 |
| genkigenki/fm1-fomni | `d05ba744279c` | gpl | 52 (22) | 45 | 26 | 0 |
| genkigenki/fm1-polly | `2e8a2bf9dd78` | gpl | 179 (35) | 42 | 33 | 0 |
| genkigenki/fm1-to-smk37 | `54252ffa2219` | other | 0 (0) | 0 | 0 | 0 |
| genkigenki/fm1-tracker-ketch | `87ff5794d4a5` | gpl | 71 (24) | 45 | 33 | 0 |
| genkigenki/fm1-x0x | `8af3731713ba` | gpl | 91 (16) | 42 | 32 | 0 |
| genkigenki/fmel-1 | `75ca839f6a17` | gpl | 36 (8) | 28 | 33 | 0 |
| genkigenki/frodhes | `e49a49d29ac5` | gpl | 566 (380) | 45 | 33 | 0 |
| genkigenki/melodee | `84e2d97e958e` | gpl | 248 (24) | 42 | 33 | 0 |
| genkigenki/orbit | `07e3fed30e8e` | gpl | 134 (1) | 42 | 33 | 0 |
| genkigenki/sloop-fm1 | `259c7bb02780` | gpl | 156 (56) | 42 | 34 | 0 |
| genkigenki/Speak37 | `81fa061b40e6` | gpl | 206 (73) | 45 | 33 | 0 |
| genkigenki/winampFM | `188124a1c7aa` | gpl | 81 (27) | 42 | 33 | 0 |
| genkigenki/zen-1 | `2b4c4ade052a` | gpl | 79 (9) | 26 | 26 | 0 |
| glvno/matryoshka | `739085df5187` | gpl | 65 (47) | 28 | 33 | 0 |
| gonziWeb/sloop-fm1 | `79dd32bce73f` | gpl | 126 (9) | 42 | 34 | 0 |
| gospodindilly-ops/fm1-x0x | `47f8e4c4ad60` | gpl | 88 (3) | 42 | 32 | 0 |
| gospodindilly-ops/jangada | `07cce380aae0` | gpl | 124 (107) | 42 | 33 | 0 |
| grant-vine/dabbl8 | `a152256f24b1` | gpl | 343 (263) | 45 | 33 | 0 |
| GraphicHealer/FeluccaSEQ | `6e2977d58079` | gpl | 162 (37) | 45 | 33 | 0 |
| GRiMMBIENT/grimm | `c597223c5c14` | gpl | 64 (0) | 42 | 29 | 0 |
| groundstation1/melodee | `1cccd6970e6e` | gpl | 248 (0) | 42 | 33 | 0 |
| groundstation1/take-taker | `8afbf0e2319d` | permissive | 1 (1) | 0 | 12 | 0 |
| Guizmoh/K-WABASS-Sub-for-FM1 | `d62bb7887145` | gpl | 41 (17) | 43 | 33 | 0 |
| Guizmoh/Kawa-Tracker-Fm1 | `047d21f6154f` | gpl | 55 (28) | 47 | 33 | 0 |
| gybe808-dotcom/FeluccaWavetableOdeathMod | `2a661dc1e9a2` | none | 0 (0) | 0 | 0 | 0 |
| hericdk/fm1-quest | `0996503bfe83` | gpl | 107 (39) | 42 | 33 | 0 |
| hericdk/nomanskyFM | `32e7f4c14a5e` | gpl | 85 (20) | 42 | 34 | 0 |
| hericdk/winampFM | `54575a4bb81e` | gpl | 81 (7) | 43 | 33 | 0 |
| Hi-Fi-Hopes/Zen-Lite | `e5112a6f0551` | gpl | 42 (18) | 43 | 32 | 0 |
| highdrone/fm1-flipper-recovery | `91615fcda62d` | permissive | 3 (3) | 16 | 16 | 0 |
| hirakos999/MODELAR | `89475ca2586d` | other | 8 (8) | 28 | 32 | 0 |
| hiroikezawa/brutal-fm | `d2081886152c` | gpl | 47 (23) | 46 | 26 | 0 |
| HolidayMan/fm1-android | `be7a89a2833c` | gpl | 17 (17) | 17 | 15 | 0 |
| HolidayMan/fm1-ios | `d2c5a6b76246` | gpl | 21 (8) | 17 | 15 | 0 |
| hugelton/Felucca | `63f88ec18b71` | gpl | 163 (0) | 45 | 33 | 0 |
| hugelton/felucca-bsp | `d6b8f771795b` | other | 32 (0) | 44 | 26 | 0 |
| hugelton/Felucca-Engines | `04ffe903eb87` | permissive | 11 (1) | 35 | 20 | 0 |
| hugelton/felucca-mirror | `fb9f11e6f6f5` | gpl | 0 (0) | 0 | 0 | 0 |
| hugelton/Felucca-WebApp | `b7947ad1da20` | gpl | 0 (0) | 0 | 0 | 0 |
| hunterxiong2026/fm1-felucca-editor-2026 | `937d395f36f9` | permissive | 0 (0) | 0 | 0 | 0 |
| hunterxiong2026/fm1-sloop-editor-2026 | `97a9d90e3a08` | permissive | 0 (0) | 0 | 0 | 0 |
| HyruleanHero1988/FM-1-Swap | `98a2519a4c8e` | other | 0 (0) | 0 | 0 | 0 |
| I-am-MaxPower/drift-fm1 | `6cfac70ac312` | gpl | 52 (9) | 45 | 26 | 0 |
| ibrahim567gamal-hash/FluTour | `496d47979a36` | none | 0 (0) | 0 | 0 | 0 |
| ignis32/midimonitor_fm1 | `5458e0a2063e` | other | 59 (14) | 24 | 26 | 0 |
| ignis32/trireme_fm1 | `cc0a1efe4644` | gpl | 17 (16) | 28 | 26 | 0 |
| illuminus5/skiff | `b03d98acd8c6` | gpl | 193 (106) | 46 | 34 | 0 |
| ImpossibleKnot/bongo-cat-studio | `ae080a7efe7e` | gpl | 184 (25) | 45 | 33 | 0 |
| InigoHernandez/demake-synth | `54d9e2a8e185` | gpl | 46 (26) | 42 | 26 | 0 |
| InigoHernandez/mono2k | `90f0d2e825e3` | gpl | 57 (27) | 28 | 32 | 0 |
| ioneng/fumi-1-ext | `7900e76d9fd1` | gpl | 67 (12) | 27 | 26 | 0 |
| ip2k/FM-1-RE | `c1a20d79f892` | permissive | 3 (0) | 17 | 22 | 0 |
| ip2k/lunar-modulator | `3c6c0a7df452` | permissive | 489 (90) | 45 | 33 | 0 |
| isod89/clipper-fm1 | `e69067211c46` | gpl | 158 (15) | 43 | 33 | 0 |
| isod89/sloop-fm1 | `d89364253b79` | gpl | 124 (4) | 42 | 33 | 0 |
| itoyohane/fm1-learning-web | `eb0a5081cdf0` | none | 0 (0) | 0 | 0 | 0 |
| izumoe/yanfei | `876d6cb4d2d4` | gpl | 200 (79) | 45 | 33 | 0 |
| jadamsowers/fm1-fimba | `0485ed0d387c` | gpl | 47 (14) | 42 | 26 | 0 |
| jahlib/sloop-fm1-go | `3da836340b31` | gpl | 0 (0) | 0 | 0 | 0 |
| JalopyMusic/fm1-cartesive-fumi-1 | `44e050dd2ced` | gpl | 67 (10) | 26 | 26 | 0 |
| JalopyMusic/fm1-catacombius-notesorcery | `c13ac1b63f0d` | gpl | 122 (33) | 42 | 33 | 0 |
| JalopyMusic/fm1-chancethemaker-felucca | `032758ad8e85` | gpl | 83 (0) | 42 | 33 | 0 |
| JalopyMusic/fm1-charlesvestal-fm1-x0x | `00bff73d6f8c` | gpl | 88 (6) | 42 | 32 | 0 |
| JalopyMusic/fm1-deadactive-hortator | `2c2847e182f6` | gpl | 119 (59) | 46 | 33 | 0 |
| JalopyMusic/fm1-dspaudio-orbit | `4c119edd6081` | gpl | 127 (37) | 42 | 33 | 0 |
| JalopyMusic/fm1-eli7vh-felucca | `84e8dc938a39` | gpl | 140 (2) | 45 | 33 | 0 |
| JalopyMusic/fm1-grant-vine-dabbl8 | `35266b6aaa93` | gpl | 259 (63) | 45 | 33 | 0 |
| JalopyMusic/fm1-hericdk-fm1-quest | `477069010c3a` | gpl | 97 (13) | 42 | 33 | 0 |
| JalopyMusic/fm1-hugelton-felucca | `a4d7ca2e5d52` | gpl | 159 (0) | 45 | 33 | 0 |
| JalopyMusic/fm1-ip2k-lunar-modulator | `40c94300428a` | permissive | 479 (12) | 45 | 33 | 0 |
| JalopyMusic/fm1-jadamsowers-fm1-fimba | `b2b647b91bb3` | gpl | 47 (2) | 42 | 26 | 0 |
| JalopyMusic/fm1-jasonpersinger-ghoulbox-fm1-dungeon-synth | `7bc975e3e272` | gpl | 140 (40) | 45 | 33 | 0 |
| JalopyMusic/fm1-joshbartlettband-web-felucca-rainbow | `ac2609eea2dc` | gpl | 143 (12) | 45 | 33 | 0 |
| JalopyMusic/fm1-juanjiant-bit-jiant | `d3f42ae52e9e` | gpl | 138 (46) | 45 | 33 | 0 |
| JalopyMusic/fm1-konsumer-fm1buddy | `bd8a397008d5` | gpl | 45 (45) | 21 | 31 | 0 |
| JalopyMusic/fm1-milkboyg-ambii | `0afdeee1413b` | gpl | 252 (154) | 42 | 33 | 0 |
| JalopyMusic/fm1-quixotic7-choralrootfm1 | `9814504f57e9` | gpl | 194 (53) | 45 | 33 | 0 |
| JalopyMusic/fm1-w0ts-optimist | `6aa01148828d` | gpl | 394 (291) | 44 | 35 | 0 |
| JalopyMusic/fm1-zednaked-jangada | `1accf9605283` | gpl | 119 (40) | 42 | 33 | 0 |
| JalopyMusic/fm1-zvenson-dinghy | `929730019a9d` | gpl | 29 (0) | 26 | 26 | 0 |
| JalopyMusic/fm1-zvenson-dxsloop | `17e395b878f0` | gpl | 91 (51) | 42 | 33 | 0 |
| JalopyMusic/fm1-zvenson-zp12 | `036ae8bd5d2e` | gpl | 40 (11) | 26 | 29 | 0 |
| jamesusmusic/fm1-studio-tess | `3a764d619c5f` | gpl | 268 (55) | 42 | 33 | 0 |
| jartificer/fm1-gm | `5436092deac6` | gpl | 53 (21) | 24 | 26 | 0 |
| jasonbot/fm1-grid | `644c68bf3a97` | gpl | 0 (0) | 0 | 0 | 0 |
| jasonpersinger/ghoulbox-fm1-dungeon-synth | `9f2b9a22e456` | gpl | 183 (28) | 45 | 33 | 0 |
| jazzfolderPARLA/VintageS | `bb37ebe2769a` | gpl | 231 (83) | 42 | 33 | 0 |
| JB-Interactive/Felucca-Meow | `f21d6d69e88e` | gpl | 151 (37) | 45 | 33 | 0 |
| jbschooley/Virtual-FM-1 | `c52668953231` | gpl | 1100 (247) | 45 | 34 | 0 |
| jean80it2/fm1-x0x | `80b7d40cc946` | gpl | 81 (21) | 42 | 32 | 0 |
| jean80it2/Virtual-FM-1 | `9ff1ec6f985a` | gpl | 198 (46) | 45 | 33 | 0 |
| jeymadcat-ops/SLICE64-FM-web | `c53210933fda` | none | 0 (0) | 0 | 0 | 0 |
| jguillenconesa-coder/Wave-FM-1-plugin | `f2f364cfd8df` | permissive | 2 (2) | 0 | 0 | 0 |
| jmcn99/JIANT | `e2f60b3b472a` | gpl | 154 (59) | 42 | 33 | 0 |
| joakimeriksson/fm1-dock | `24c0da085c4b` | gpl | 98 (68) | 45 | 33 | 0 |
| joakimeriksson/fm1-emu | `51ca41af6734` | gpl | 32 (0) | 28 | 32 | 0 |
| joakimeriksson/scintilla-fm1 | `9ca06cec1685` | gpl | 52 (21) | 28 | 28 | 0 |
| jogo-jpn/sloop-fm1 | `d315ad88c5fb` | gpl | 114 (0) | 42 | 33 | 0 |
| johnskiller/driftseq | `1ce92672be15` | other | 64 (43) | 33 | 26 | 0 |
| johnskiller/Felucca | `c8eab234beb2` | gpl | 159 (0) | 45 | 33 | 0 |
| johnskiller/fm1-ctrl | `92cc34e01eea` | other | 5 (5) | 14 | 14 | 0 |
| johnskiller/fm1-emulator | `952c50085543` | gpl | 62 (59) | 24 | 23 | 0 |
| johnskiller/sloop-fm1 | `d2f3204f8a1c` | gpl | 114 (0) | 42 | 33 | 0 |
| Jonbenderr/fm1-p6 | `8e7108bce690` | none | 0 (0) | 0 | 0 | 0 |
| Joolo09/zombie-fm1-web | `fc9ee4737733` | permissive | 141 (30) | 46 | 33 | 0 |
| joshbartlettband-web/album-fm1 | `2647b5ecf3cc` | permissive | 8 (8) | 25 | 32 | 0 |
| joshbartlettband-web/Double-Rainbow | `f615412bf7e3` | gpl | 183 (14) | 42 | 33 | 0 |
| joshbartlettband-web/felucca-rainbow | `0baf362731c6` | gpl | 149 (24) | 45 | 33 | 0 |
| jpurcallas/fm1-emu | `61b51596d575` | gpl | 32 (0) | 28 | 32 | 0 |
| jrdntnnr/DAKHMEH-FM-1 | `c0abede38958` | gpl | 80 (46) | 42 | 30 | 0 |
| jrdntnnr/sardab | `830bb5831fe8` | gpl | 216 (137) | 45 | 33 | 0 |
| jsmith13/fm_lab | `cf35dc26709e` | gpl | 36 (0) | 28 | 26 | 0 |
| jsopdebeeck/fm1-delrio | `039b0510d2dd` | other | 8 (8) | 42 | 21 | 0 |
| juanjiant-bit/JIANT | `92048b29a307` | gpl | 187 (0) | 42 | 33 | 0 |
| jukejutsu/FM2000 | `10787e18359a` | gpl | 34 (9) | 28 | 26 | 0 |
| julesdg6/sloop-fm1 | `226ba29f6717` | gpl | 91 (0) | 42 | 33 | 0 |
| junkaiman/FM-SWITCH | `8871da90367d` | none | 0 (0) | 0 | 0 | 0 |
| Juris3D/fm1-emu | `db8d472e62f3` | gpl | 32 (0) | 28 | 32 | 0 |
| justynroberts/fm1-finton | `8dc9edee324e` | gpl | 45 (20) | 37 | 26 | 0 |
| jvitkauskas/fm1-backup | `0796a7009fc6` | none | 0 (0) | 0 | 0 | 0 |
| jvitkauskas/m-bootloader | `64b74d009e6d` | permissive | 29 (29) | 26 | 21 | 0 |
| karlalex732-dotcom/RED-MASS-VAMPIRE-OS-FOR-M-VAVE-FM1 | `0fafe85aadb0` | gpl | 162 (95) | 45 | 33 | 0 |
| Kayman18/genAMB | `8a90f125022b` | none | 0 (0) | 0 | 0 | 0 |
| kdorland/Fantasma | `69acd429e062` | gpl | 168 (0) | 45 | 33 | 0 |
| Keitark/fm1-doom | `3d8a093ddadd` | gpl | 63 (63) | 26 | 24 | 0 |
| Keitark/fm1-mdx | `9762d417d6f3` | gpl | 61 (61) | 26 | 27 | 0 |
| Keitark/fm1-nes | `90d41c5e4807` | permissive | 102 (79) | 26 | 33 | 0 |
| KelvinTTTT/Felucca | `129a4cf4e98e` | gpl | 158 (14) | 45 | 33 | 0 |
| KemstheSage/reggae-os | `dfe50b268998` | gpl | 175 (29) | 45 | 33 | 0 |
| Kenneth-Rakentine/Ravel-FM1 | `cc816dc9c97e` | gpl | 61 (22) | 42 | 33 | 0 |
| keremimo/fm1-base | `6c0b47e4bfc5` | other | 48 (1) | 24 | 33 | 0 |
| keremimo/melodee | `398ada1e09d8` | gpl | 280 (0) | 42 | 33 | 0 |
| keremimo/saadet | `cb520e79ac22` | other | 181 (137) | 45 | 33 | 0 |
| kesi03/fm1-emu | `cf42d19a78b8` | gpl | 32 (0) | 28 | 32 | 0 |
| keyboy250/fm1-x0x-acultur8 | `7bca4df442bd` | gpl | 135 (74) | 42 | 32 | 0 |
| kidbee85-beep/AMB-1-Evolved | `b8f0eb7f2098` | gpl | 55 (15) | 42 | 26 | 0 |
| kidbee85-beep/bunker-evolved | `c9bb0b1ac4a7` | gpl | 182 (29) | 45 | 33 | 0 |
| kidbee85-beep/cut-a-dor-release | `d9799abb84fe` | gpl | 60 (35) | 29 | 33 | 0 |
| kidbee85-beep/mutable-dreams | `04cf468420f4` | gpl | 0 (0) | 0 | 0 | 0 |
| Kiwi3p/fm1-deal-or-no-deal | `a8ffcf798967` | gpl | 52 (14) | 22 | 26 | 0 |
| klonecom/M-VAVE-FM1-LOADER--- | `7e4609784952` | none | 0 (0) | 0 | 0 | 0 |
| kmplngj/Felucca | `2579e55791df` | gpl | 249 (178) | 45 | 33 | 0 |
| kmplngj/Felucca-Engines | `7cf364f6c2ce` | permissive | 13 (6) | 35 | 20 | 0 |
| kmplngj/Felucca-WebApp | `a881cb73ae66` | gpl | 1 (1) | 26 | 14 | 0 |
| kmplngj/m-bootloader | `df15966a4bcf` | permissive | 27 (4) | 26 | 21 | 0 |
| kmplngj/m-flasher-legacy | `aeb061a03b7b` | other | not fetched: could not fetch the pinned commit | | | |
| konsumer/fm1-emu | `7856393bc82f` | gpl | 32 (0) | 28 | 32 | 0 |
| konsumer/fm1buddy | `f49ed130899f` | gpl | 52 (28) | 23 | 31 | 0 |
| konsumer/foma | `58e1e25df47c` | gpl | 90 (14) | 26 | 26 | 0 |
| konsumer/fomajam | `16991c7a439d` | gpl | 58 (20) | 35 | 26 | 0 |
| kpalaniuk/gnomad-firmware | `3675315d9962` | gpl | 185 (104) | 45 | 33 | 0 |
| KrisGelero/fm1-loom | `c37c07af653c` | gpl | 44 (10) | 44 | 33 | 0 |
| Leeman1982/sloop-fm1 | `b77bf55e3bf8` | gpl | 124 (0) | 42 | 33 | 0 |
| leomaimoni/fm1-bank-sender | `16b1b75fa251` | none | 0 (0) | 0 | 0 | 0 |
| leonardoMirabal/frodhes | `a8320e860c23` | gpl | 579 (28) | 45 | 33 | 0 |
| Leonidas0710/Felucca | `a53ecf428c29` | gpl | 163 (0) | 45 | 33 | 0 |
| LexLongcoding/ghoulbox-vst3 | `31a1d736dcb1` | gpl | 10 (10) | 25 | 19 | 0 |
| limiemohon-stack/ChoralRootFM1 | `198fc493f541` | gpl | 216 (7) | 45 | 33 | 0 |
| llozd/bytemania | `e670b35369f8` | gpl | 35 (9) | 42 | 26 | 0 |
| luchak/felucca-bsp | `4bd6d0bc07c4` | other | 30 (0) | 44 | 26 | 0 |
| luchak/fm1-x0x | `2e31c517ded3` | gpl | 91 (0) | 42 | 32 | 0 |
| luginf/fm1-emu | `43044b417fe1` | gpl | 31 (0) | 28 | 32 | 0 |
| Luisnvb/fm1-shed | `7ca92305c798` | other | 142 (19) | 45 | 24 | 0 |
| Luisnvb/shed-web | `5c94ac3864a0` | other | 0 (0) | 0 | 0 | 0 |
| LXXero/oplbox | `664a8bdb3f65` | gpl | 45 (19) | 26 | 28 | 0 |
| m-vave/fm1_open | `4c7496daac04` | other | 124 (0) | 45 | 24 | 0 |
| majica99/mvave--fm11-genmus | `68e1b7cd0384` | gpl | 186 (46) | 42 | 33 | 0 |
| majica99/mvave-fm1-rebirth | `fbc8768327e4` | gpl | 123 (15) | 42 | 32 | 0 |
| manuelerdoes/oergelfm1 | `f5a4148f4a8c` | gpl | 164 (21) | 45 | 33 | 0 |
| Marcel-B/Felucca | `ac468ff32776` | gpl | 160 (15) | 45 | 33 | 0 |
| MarcoCasanova00/JIANT-tekno-rework | `7ca82f66b8a6` | gpl | 187 (8) | 42 | 33 | 0 |
| markterm/harbor | `7fd7b2810a11` | none | 0 (0) | 0 | 0 | 0 |
| math0ne/fm1-chord | `5117c27f094f` | gpl | 143 (7) | 45 | 33 | 0 |
| mauricecalhoun/skiff | `a5d648132160` | gpl | 177 (0) | 45 | 33 | 0 |
| mauricecyril/fm1-to-smk37 | `d23bd32169c9` | other | 0 (0) | 0 | 0 | 0 |
| maykerache/felucca-bsp | `c4624a5b538f` | other | 30 (14) | 20 | 26 | 0 |
| maykerache/Felucca-WebApp | `f35951a365f9` | gpl | 0 (0) | 0 | 0 | 0 |
| mediaworkbench/Felucca | `9be30a5f2c1a` | gpl | 182 (44) | 45 | 33 | 0 |
| megagott/launchparty-fm1 | `efa6e4e24687` | gpl | 0 (0) | 0 | 0 | 0 |
| megagott/mycelium-fm1 | `750eb125e285` | gpl | 0 (0) | 0 | 0 | 0 |
| Mello-D/JIANT | `2f0d6f50c102` | gpl | 187 (0) | 42 | 33 | 0 |
| mene311/Felucca | `d3038ca96204` | gpl | 149 (17) | 45 | 33 | 0 |
| mene311/fm1-banks | `f47b11b9035b` | other | 0 (0) | 0 | 0 | 0 |
| mene311/fm1-pulses-felucca | `1c09071e2019` | none | 0 (0) | 0 | 0 | 0 |
| mentalcells/ambwave | `c1932a5788b2` | gpl | 159 (52) | 45 | 33 | 0 |
| merthsoft/flipper-fm1-recovery | `df88b862a479` | permissive | 3 (0) | 16 | 16 | 0 |
| merthsoft/sloop-fm1 | `76eae6d6322c` | gpl | 230 (186) | 42 | 34 | 0 |
| mgrolandi/fm1-mediacion | `5e9864294c66` | none | 0 (0) | 0 | 0 | 0 |
| michaeljsmalley/synthesthetic | `52565e26c34f` | gpl | 138 (45) | 42 | 34 | 0 |
| MikeTsak/Evanders-Music-Box--FM-1-LARP-firmware | `53c32342efb4` | other | 10 (10) | 29 | 31 | 0 |
| millette/Felucca | `7414269c4392` | gpl | 131 (0) | 45 | 33 | 0 |
| millette/fm1-fomni | `378dfacbf476` | gpl | 49 (5) | 45 | 26 | 0 |
| millette/fm1-x0x | `9ae360b64af9` | gpl | 85 (5) | 42 | 32 | 0 |
| MohammadMahdiYazdanshad/FM1-PROJECT | `96f808ec51b0` | none | 0 (0) | 0 | 0 | 0 |
| monch1962/felucca-engines | `65fe10466365` | permissive | 8 (1) | 35 | 20 | 0 |
| monch1962/mvave-fm1-mpe | `2aaeae37eef5` | gpl | 163 (35) | 45 | 33 | 0 |
| moocowblue/fm1-loom-editor | `f5501d77562f` | gpl | 0 (0) | 0 | 0 | 0 |
| mosurabeats/FM1--Sp12-Turbo-Build | `f4bb214451b1` | gpl | 42 (7) | 26 | 29 | 0 |
| Motheraudio/TheCove | `f3f41a79ccda` | gpl | 159 (3) | 45 | 33 | 0 |
| mpereira/felucca-server | `a5ffc0272b9b` | other | 0 (0) | 0 | 0 | 0 |
| mr-devboy/fm1-dx7-patch-importer | `581b5a5489b2` | permissive | 4 (0) | 0 | 0 | 0 |
| Mr-Roboto/fm1-x0x-rmx | `c7a633d01dca` | gpl | 111 (48) | 43 | 32 | 0 |
| mrsheez/Felucca | `13dd66517d2f` | gpl | 148 (59) | 45 | 33 | 0 |
| muffintopmusic/fm1_openknob | `c9513f6cfa73` | other | 122 (1) | 45 | 24 | 0 |
| MXMP1/x-seq | `635d1534f90f` | none | 0 (0) | 0 | 0 | 0 |
| myldy20/BRKLOOP | `f9aaaa776232` | gpl | 125 (1) | 42 | 34 | 0 |
| Nacsez/FMER | `f096a3b5f0b5` | gpl | 214 (173) | 42 | 33 | 0 |
| Narti-Live/fm1-fm-plaits | `2884f45c043c` | none | 0 (0) | 0 | 0 | 0 |
| NicholasPratt/Prysm | `48de4e27dbd1` | gpl | 53 (29) | 26 | 33 | 0 |
| Nicodesy06/FM1-MOVE | `42fc1af2a2ab` | gpl | 126 (43) | 42 | 33 | 0 |
| nilselathome/sloop-fm1-editor-regex | `31b47acb5164` | gpl | 114 (0) | 42 | 33 | 0 |
| nokill-pedal-co/pocket-six | `a6e0d13da05b` | none | 0 (0) | 0 | 0 | 0 |
| NoodleSushi/dinghy | `706403b81682` | gpl | 31 (4) | 26 | 26 | 0 |
| NorfolkHacker/acid-fm | `061b4dc1c926` | gpl | 184 (42) | 42 | 33 | 0 |
| NOVALENTI/fm1-polyseq | `b028d3f8ebb7` | none | 98 (86) | 42 | 28 | 0 |
| npi3pak/fm1-gator | `92f923e0b9fe` | gpl | 171 (25) | 28 | 27 | 0 |
| nullbeing/fm1-amb | `d4a211c7f450` | other | 48 (0) | 34 | 26 | 0 |
| nullbeing/fm1-custom-fw | `cb5796c24e2e` | none | 0 (0) | 0 | 0 | 0 |
| nvhhh/JIANT | `6a346961f02b` | gpl | 190 (15) | 42 | 33 | 0 |
| nzimas/bigorna | `d4fd1894596f` | gpl | 51 (37) | 28 | 26 | 0 |
| nzimas/tonitor | `f51bd68313f0` | gpl | 58 (32) | 45 | 32 | 0 |
| obbymaul-mp3/3IS | `fc9743f16225` | gpl | 190 (29) | 45 | 33 | 0 |
| ocean/estampie | `a5eb02a96b3f` | gpl | 206 (96) | 45 | 33 | 0 |
| ocean/FM-SWITCH | `b7de29dafc35` | none | 0 (0) | 0 | 0 | 0 |
| ocean/fm1-site | `3d46f19e94f7` | other | 0 (0) | 0 | 0 | 0 |
| ocean/FM1Kit | `280901c52ccd` | permissive | 0 (0) | 0 | 0 | 0 |
| okumurari2/maku | `fa6d95aa4c28` | gpl | 142 (50) | 45 | 33 | 0 |
| OllieNicklinUK/switchblade | `9d0752714a93` | gpl | 158 (114) | 42 | 33 | 0 |
| oMauNaProducer/5-Lab | `e6b0883214ac` | gpl | 165 (18) | 45 | 33 | 0 |
| ordenador/Felucca-Engines | `c46e0086f69b` | permissive | 8 (0) | 35 | 20 | 0 |
| oscillr/DUELL | `654a89e24266` | gpl | 296 (268) | 45 | 33 | 0 |
| osmaav/fm1-to-smk37 | `e45acd7d1723` | other | 0 (0) | 0 | 0 | 0 |
| OwenKirby/carnac-os | `6387a21932aa` | gpl | 102 (102) | 30 | 33 | 0 |
| p-orlov/Ecolucca | `ec4f12e2a5e8` | gpl | 61 (21) | 42 | 33 | 0 |
| PatttF/fm-106 | `db59d585bffb` | gpl | 81 (38) | 42 | 32 | 0 |
| pbarilla/fm1-x0x | `397c8a8a2142` | gpl | 85 (5) | 42 | 32 | 0 |
| pbarilla/fumi-1 | `ec7537fc87cc` | gpl | 67 (2) | 26 | 29 | 0 |
| pbarilla/ghoulbox-fm1-dungeon-synth | `3e642b33e342` | gpl | 174 (15) | 45 | 33 | 0 |
| pbarilla/orbit | `4d85cf8ae8b5` | gpl | 112 (43) | 42 | 33 | 0 |
| pedronogueiranunes/sloop-fm1 | `7d911ea74f7c` | gpl | 125 (6) | 42 | 33 | 0 |
| pfkellogg/fm1-bonus-box | `069d0234d132` | none | 7 (7) | 0 | 0 | 0 |
| pfkellogg/fm1-sustain-footswitch | `9a5f89f04087` | none | 0 (0) | 0 | 0 | 0 |
| phc101/fm1-emu | `ecd2b0b1a865` | gpl | 32 (0) | 28 | 32 | 0 |
| pianomansam/fm1-vnl | `559bee12171c` | other | 27 (27) | 28 | 21 | 0 |
| PierreArnaudGUYOT/FM1-Oktowave-Firmware | `60619dbb28e5` | gpl | 169 (27) | 45 | 33 | 0 |
| pingywon/fm1-easy-guide | `d711151ea14c` | permissive | 0 (0) | 0 | 0 | 0 |
| PistolPineapple/skiff | `69b05f618f70` | gpl | 175 (14) | 45 | 33 | 0 |
| poiw-org/fm1-registrations | `9398c8a0f77a` | none | 0 (0) | 0 | 0 | 0 |
| pomegnechristianfrank-gif/site-web-FM1 | `d5f85c2f3219` | none | 0 (0) | 0 | 0 | 0 |
| Pongtrometer/jangada | `4ed8411dd681` | gpl | 122 (7) | 42 | 33 | 0 |
| probonopd/fm1-emulator | `23f424d2303b` | gpl | 62 (23) | 24 | 31 | 0 |
| pwalsh/felucca-bsp | `6eee4bf97346` | other | 30 (6) | 20 | 26 | 0 |
| Qubestar/Saibertin-S-FM | `9c3f5a89f3d8` | none | 0 (0) | 0 | 0 | 0 |
| Quixotic7/ChoralRootFM1 | `7d97982a7db3` | gpl | 253 (11) | 45 | 34 | 0 |
| Quixotic7/FM1VST | `ff82f9ae8544` | gpl | 214 (214) | 29 | 21 | 0 |
| Quixotic7/MvaveFM1-Designer | `0ecd189b7b3a` | permissive | 0 (0) | 0 | 0 | 0 |
| Quixotic7/PurpleMonkeyFM1 | `b574e75dd1dc` | gpl | 204 (69) | 45 | 33 | 0 |
| r7819smith-oss/slowmorph | `575cdc2946b4` | gpl | 0 (0) | 0 | 0 | 0 |
| Rastapopolix/melodee-tess | `72eba500063d` | gpl | 406 (189) | 42 | 33 | 0 |
| RayDNoper/fm1-fomnium | `44d6a1296a05` | gpl | 51 (17) | 43 | 26 | 0 |
| relyt29/melodee | `01a78bdf0fb0` | gpl | 223 (4) | 42 | 33 | 0 |
| Reytian/fm1-luogu | `7fd506a83c6f` | other | 25 (25) | 29 | 17 | 0 |
| Reytian/fm1-min1 | `14d8ddf6390c` | gpl | 49 (17) | 45 | 33 | 0 |
| Reytian/fm1-trio | `7c92b7a18184` | other | 18 (18) | 22 | 15 | 0 |
| rgrvmusic/fluyt-logue | `5f47c1687ebf` | gpl | 19 (19) | 46 | 18 | 0 |
| rgrvmusic/fluyt-web | `2639ed65c5a3` | other | 5 (5) | 12 | 0 | 0 |
| rgrvmusic/harbor | `80f9724a9fb5` | none | 0 (0) | 0 | 0 | 0 |
| risseraka/fm1-tracker-ketch | `d8ebe8641f4f` | gpl | 75 (37) | 45 | 33 | 0 |
| ristiisa/sloop-fm1 | `e2a9a2f72533` | gpl | 117 (60) | 42 | 33 | 0 |
| rocketlaunch-io/Felucca | `27f87d10fd90` | gpl | 130 (19) | 45 | 33 | 0 |
| rondlite/felucca-rainbow-dutch | `04a86b44a26e` | gpl | 149 (1) | 45 | 33 | 0 |
| ruppert/fmini-1 | `53946ae20760` | gpl | 177 (2) | 45 | 33 | 0 |
| ruppert/organvave-1 | `1ce1a37afd00` | gpl | 100 (74) | 42 | 33 | 0 |
| RustyPawz/fm1-HYP1 | `57c456db6182` | other | 281 (77) | 42 | 26 | 0 |
| s0fx2/YamahaDX7_to_FM-1 | `21e3e26c0add` | gpl | 0 (0) | 0 | 0 | 0 |
| Sab0tenb0y/Felucca | `df4498e8d959` | gpl | 163 (0) | 45 | 33 | 0 |
| sabliran/sloop-web-emu | `bbfd8e5b3bfc` | gpl | 2 (1) | 17 | 14 | 0 |
| Sanderat/Blight- | `08ed4a7d5c8c` | none | 0 (0) | 0 | 0 | 0 |
| sbegueria/fm1-dub | `e6fe7b8f8f31` | gpl | 51 (9) | 42 | 26 | 0 |
| sceic/fm1-felucca-editor-2026 | `4ec3fe2f426a` | permissive | 0 (0) | 0 | 0 | 0 |
| schwartzworld/shifl | `79fe37dff470` | gpl | 111 (61) | 42 | 33 | 0 |
| seajaysec/386-DX-FM1-KaraokeBot | `87b2e8b2b157` | gpl | 67 (47) | 28 | 26 | 0 |
| seajaysec/fm-static | `4ec334bba5c9` | gpl | 0 (0) | 0 | 0 | 0 |
| seajaysec/fm1-dx7-patch-importer | `ba4593ed88f0` | permissive | 0 (0) | 0 | 0 | 0 |
| seanohollaren/fm1-doom | `bde88936a14e` | gpl | 19 (19) | 26 | 21 | 0 |
| SeattleUser0/OrangeCat | `19271b03707c` | gpl | 350 (150) | 46 | 33 | 0 |
| SeattleUser0/skiff | `2b350ac2bd88` | gpl | 179 (21) | 45 | 33 | 0 |
| seclorum/fm1buddy.seclorum | `8b0844bef1a9` | gpl | 29 (29) | 19 | 31 | 0 |
| seclorum/lunar-modulator.seclorum | `a5a096ffe77c` | permissive | 297 (92) | 42 | 33 | 0 |
| severak/wolfware | `84b8cbee8aa2` | none | 0 (0) | 0 | 0 | 0 |
| shinobi/ChoralRootFM1-DOREMI | `51efe2414486` | gpl | 213 (17) | 45 | 33 | 0 |
| SikkenWorks/B1-Drawbar-Organ | `82f01627ce46` | gpl | 117 (98) | 26 | 34 | 0 |
| SikkenWorks/BEETLE | `a075544a6740` | gpl | 318 (298) | 29 | 33 | 0 |
| SikkenWorks/ETCH | `a00ec8684c38` | gpl | 305 (235) | 45 | 33 | 0 |
| Simant49/lunar-modulator-looper | `6c030732a060` | permissive | 227 (30) | 42 | 33 | 0 |
| simonjohansson/fm1-emulator | `519a13b879d7` | gpl | 62 (0) | 24 | 31 | 0 |
| sirpearson/fm-1-monomachine | `527da33beb3d` | gpl | 47 (15) | 28 | 35 | 0 |
| slothpallas/mope-1 | `7c6490359acb` | gpl | 49 (16) | 43 | 33 | 0 |
| smememe/fm1-macropad-patch | `0e6b52c247d4` | permissive | 0 (0) | 0 | 0 | 0 |
| smhgzll/sloopy-sloop-32 | `a0c1cfc8562c` | gpl | 59 (59) | 25 | 28 | 0 |
| smhulme/sloop-ios-8trk | `ec3cfc53af71` | gpl | 0 (0) | 0 | 0 | 0 |
| smhulme/sloop-web-8trk | `9974f8f67fc6` | gpl | 0 (0) | 0 | 0 | 0 |
| SpeakingColors/mwave-fm1-linux-vst | `3aac65ebb636` | gpl | 0 (0) | 0 | 0 | 0 |
| SPIKE-the-Percussionist/noiz_demons | `4fe0f1afb4d9` | gpl | 171 (12) | 45 | 33 | 0 |
| spinkham/Felucca | `7392d9c8f0fc` | gpl | 142 (10) | 45 | 33 | 0 |
| spinkham/felucca-try | `ac3ba1b58c5b` | gpl | 0 (0) | 0 | 0 | 0 |
| spinkham/Felucca-WebApp | `2e4d39178bdf` | gpl | 0 (0) | 0 | 0 | 0 |
| spinkham/fm1-emulator | `18a8ccec50e5` | gpl | 28 (6) | 26 | 26 | 0 |
| Spiralfractalplugins/spiralfm1 | `6e0fd2b824fd` | gpl | 116 (110) | 42 | 33 | 0 |
| stanleygurvich/FeluccaMPE | `817f5b8f3fd9` | gpl | 163 (12) | 45 | 33 | 0 |
| StephanBeutel/Virtual-FM-1 | `21605e266775` | gpl | 678 (38) | 45 | 33 | 0 |
| stevensnasdell-cmd/dock | `11db45adc55b` | gpl | 272 (68) | 42 | 33 | 0 |
| styvesgoupil/fm1-base | `ced944368d99` | other | 48 (6) | 24 | 33 | 0 |
| styvesgoupil/frasil | `a850ef11a2d7` | other | 16 (16) | 26 | 32 | 0 |
| swe24-phon/fm1-mod-ref | `134bcc46f11d` | none | 0 (0) | 0 | 0 | 0 |
| swe24-phon/mvave-fm1-testbed-mob | `e8adbf45b0b3` | other | 0 (0) | 0 | 0 | 0 |
| SylarPu-X/nightfall-fm1 | `3861e7a5e4fe` | gpl | 18 (18) | 28 | 32 | 0 |
| synthi/fm1-1971 | `d422a998f2d9` | gpl | 220 (54) | 42 | 33 | 0 |
| synthi/fm1-ctl | `298b637e961b` | other | 139 (32) | 42 | 33 | 0 |
| synthi/fm1-ios | `03b0ad3c5c50` | gpl | 9 (2) | 15 | 15 | 0 |
| synthi/grimm | `43e710d7a004` | gpl | 64 (0) | 42 | 29 | 0 |
| synthi/jangada | `6dfbc5a68e77` | gpl | 124 (6) | 42 | 33 | 0 |
| synthi/niagara-drift | `a319c5a558c2` | gpl | 53 (11) | 29 | 26 | 0 |
| synthi/tonitor | `a240bc182b55` | gpl | 56 (19) | 28 | 32 | 0 |
| tank12123/FM1 | `3e5f912dc007` | none | 0 (0) | 0 | 0 | 0 |
| teekesti/harbour-hortator | `57bb903c54ae` | none | 26 (26) | 23 | 14 | 0 |
| tensor-programming/fm1-t1 | `bea0fd38fbeb` | gpl | 181 (18) | 45 | 33 | 0 |
| TerkWerX/Crepuscular_Homunculus | `c55a1a5db541` | gpl | 80 (57) | 46 | 33 | 0 |
| thebrodi/fm1-haave | `24e75c83e52c` | gpl | 170 (15) | 45 | 33 | 0 |
| thefriendlyhedgehog/FM-Cat1 | `820251d823eb` | gpl | 58 (21) | 26 | 26 | 0 |
| thegiantsnail/fm1-workbench-public | `e35315b7ea81` | gpl | 0 (0) | 0 | 0 | 0 |
| theNoisery/fN-1 | `91268d9b5761` | other | 128 (9) | 45 | 24 | 0 |
| TheShrimpBlimp/awesome-fm-1 | `a7be23a05a2a` | permissive | 0 (0) | 0 | 0 | 0 |
| TheShrimpBlimp/pigeon | `b18b4cbcbdbb` | gpl | 261 (161) | 45 | 33 | 0 |
| thingsapart/fm1-studio | `76372746ca85` | gpl | 37 (37) | 16 | 28 | 0 |
| thingsapart/sloop-fm1 | `cb6dedcec257` | gpl | 112 (0) | 42 | 33 | 0 |
| thomasgregorymarsden-code/Felucca-opx | `1286a8c78b0f` | gpl | 170 (42) | 46 | 33 | 0 |
| TomPtherapy/moogi | `d97c5bec9460` | gpl | 179 (16) | 45 | 33 | 0 |
| TonyMilton/frodhes | `159333d6e185` | gpl | 579 (13) | 45 | 33 | 0 |
| TruBitTech/Felucca | `c13541bd456f` | gpl | 171 (9) | 45 | 33 | 0 |
| TruBitTech/pinhead | `dfa4100dcc6e` | none | 9 (9) | 17 | 15 | 0 |
| trustcoinmining/FM1-DDR3MIG-ug586 | `6318218dcdff` | none | 0 (0) | 0 | 0 | 0 |
| trustcoinmining/TCM-FMx | `d7e423cd12ef` | none | 0 (0) | 0 | 0 | 0 |
| twaroshinto/AEther | `a8802a6ca4c8` | other | 8 (8) | 42 | 30 | 0 |
| TwistedGenetics/DREADNOUGHT | `6f3a9963c0bb` | gpl | 67 (56) | 43 | 19 | 0 |
| Umbrien/fm1-android | `71abbe198731` | gpl | 18 (8) | 17 | 15 | 0 |
| unclewayback/coracle | `3d34c1b9f35e` | gpl | 71 (44) | 26 | 30 | 0 |
| Vaayaa/rift-fw | `52562e739564` | gpl | 33 (11) | 26 | 32 | 0 |
| vikramrojo/maqam-dev | `8bd7db8492cc` | gpl | 119 (34) | 42 | 33 | 0 |
| vrcvs/Felucca | `3a91058d4a40` | gpl | 163 (0) | 45 | 33 | 0 |
| w0ts/fm1-emulator | `6ce95ec7b3d2` | gpl | 28 (0) | 26 | 26 | 0 |
| w0ts/optimist | `abb61a92c8f5` | gpl | 718 (488) | 43 | 35 | 0 |
| weavejam/Felucca | `c0746da976c3` | gpl | 164 (8) | 45 | 33 | 0 |
| weavejam/fm1_open | `9b6b28f62c07` | other | 125 (4) | 45 | 24 | 0 |
| weavejam/sloop-fm1 | `9744741ff444` | gpl | 125 (9) | 42 | 33 | 0 |
| Wesleyx88/mvave-fm1-drone | `891da07cdfe4` | gpl | 208 (2) | 45 | 33 | 0 |
| Wesleyx88/mvave-fm1-drum | `98cb90a118ee` | gpl | 55 (2) | 26 | 29 | 0 |
| Wesleyx88/mvave-fm1-emu | `dc50f04ce0d7` | gpl | 32 (0) | 28 | 32 | 0 |
| Wesleyx88/mvave-fm1-gen | `0945f5ba447b` | gpl | 50 (6) | 34 | 26 | 0 |
| Wesleyx88/mvave-fm1-legosythn | `ef98611549ac` | gpl | 650 (2) | 42 | 35 | 0 |
| Wesleyx88/mvave-fm1-mooge | `fcfaceeebb8e` | gpl | 171 (5) | 45 | 33 | 0 |
| wesmattison/snoop37 | `655458d8a5c8` | gpl | 154 (7) | 42 | 34 | 0 |
| wicked-wix/felucca-bsp | `b899449bbf3a` | other | 30 (0) | 20 | 26 | 0 |
| WillCMcC/kidboy-firmware | `2e400c2dfcf3` | gpl | 208 (49) | 45 | 33 | 0 |
| wochende/FM-1-Felucca-Tutor | `20c73515f99c` | none | 3 (3) | 0 | 0 | 0 |
| wonky-roger/fm1-emu | `0a59fb935708` | gpl | 32 (0) | 28 | 32 | 0 |
| workeffortwaste/JIANT | `ade4e8940f74` | gpl | 146 (43) | 45 | 33 | 0 |
| Wulgaren/Araminta | `e1d49121e38e` | gpl | 173 (120) | 43 | 33 | 0 |
| wzkxh/fork_dinghy | `91c9a78035b0` | gpl | 29 (0) | 26 | 26 | 0 |
| Xanacognition/XANOISE | `55bece156815` | gpl | 187 (0) | 42 | 33 | 0 |
| xerydian/Felucca | `9c143148830f` | gpl | 163 (8) | 45 | 33 | 0 |
| xerydian/felucca-smk | `cc13e146f11d` | gpl | 269 (14) | 45 | 33 | 0 |
| xerydian/fm1-emu | `19177bd79914` | gpl | 32 (0) | 28 | 32 | 0 |
| xerydian/fm1-to-smk37 | `6af085f17156` | other | 0 (0) | 0 | 0 | 0 |
| xerydian/hortator | `7e3415971c58` | gpl | 158 (46) | 46 | 33 | 0 |
| xerydian/lunar-modulator | `7cc70572490e` | permissive | 227 (2) | 42 | 33 | 0 |
| xerydian/orbit | `b50203206a6a` | gpl | 112 (17) | 42 | 33 | 0 |
| xerydian/skiff | `eec4c1011a9d` | gpl | 165 (50) | 45 | 33 | 0 |
| xerydian/zp12 | `f90efac6bb96` | gpl | 40 (6) | 26 | 29 | 0 |
| xoxoaudiolabs/FM-1-Companion | `8fbee8c3ddc6` | gpl | 0 (0) | 0 | 0 | 0 |
| y6zkcqnf5r-hue/fm1-fm80s | `171c51fae0c4` | gpl | 110 (7) | 42 | 33 | 0 |
| y6zkcqnf5r-hue/fm1-trawler | `153f4f4433f1` | gpl | 55 (55) | 42 | 20 | 0 |
| yentzee/My-Name-is-Mod | `85a5132ea17e` | gpl | 0 (0) | 0 | 0 | 0 |
| zakariachowdhury/flowstate-fm1 | `39625601f030` | gpl | 130 (66) | 42 | 33 | 0 |
| zednaked/jangada | `249eb434b810` | gpl | 126 (4) | 42 | 33 | 0 |
| zisonzishen/crate-fm1 | `27c13ea30938` | gpl | 53 (32) | 26 | 26 | 0 |
| zisonzishen/sloop-consort | `8b24360e8278` | gpl | 0 (0) | 0 | 0 | 0 |
| zisonzishen0415-stack/sloop-consort | `af74b1bf6bed` | gpl | 0 (0) | 0 | 0 | 0 |
| zreese/felucca-rainbow | `65ee5090220d` | gpl | 149 (2) | 45 | 33 | 0 |
| zvenson/dinghy | `22acb9165ebc` | gpl | 40 (0) | 26 | 26 | 0 |
| zvenson/dxsloop | `eeec0a6c1c7f` | gpl | 101 (38) | 42 | 33 | 0 |
| zvenson/fm1doom | `640bc2dbdc69` | gpl | 213 (189) | 40 | 33 | 0 |
| zvenson/zp12 | `7b8b97586ef8` | gpl | 60 (6) | 26 | 29 | 0 |
| ZzpsS/M1n1Le55 | `36ef0a3600ff` | permissive | 55 (55) | 27 | 21 | 0 |

Not scored: 288 duplicate, 2 empty, 2 unreachable. Unresolved (no repository found): Felucca Salt, Felucca 8 Patterns.

## Traceability

| Requirement | Checks | Result |
|---|---|---|
| R-AUDIT-1 | C-AUDIT-SCORE, C-AUDIT-LEAK, C-AUDIT-TEXT | PASS |
| R-AUDIT-2 | C-AUDIT-PIN | PASS |
| R-AUDIT-3 | C-AUDIT-LEAK | PASS |
| R-AUDIT-4 | C-AUDIT-JPLAG, C-AUDIT-CONTROL, C-AUDIT-BASE | PASS |
| R-AUDIT-5 | C-AUDIT-SCORE, C-AUDIT-TEXT | PASS |
