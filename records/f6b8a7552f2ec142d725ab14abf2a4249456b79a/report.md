# Test record f6b8a7552f2e

- Commit: `f6b8a7552f2ec142d725ab14abf2a4249456b79a`
- Subject: Merge pull request #177 from japes98/build/folder-cpu
- Tree: `2cc8ac20f632a221165ed6f1ee0e2023c98984f5`
- Written: 2026-10-29T12:39:51Z
- Overall: **PASS**
- CI run: https://github.com/japes98/small-beeps/actions/runs/40872043698

## Checks

| Check | Title | Requirements | Result | Seconds |
|-------|-------|--------------|--------|---------|
| C-UNIT | Unit tests of the tools | R-PROC-1, R-PROC-4, R-REC-1, R-CLEAN-3, R-CLEAN-4, R-PUB-1, R-SEP-2, R-SPEC-1, R-SPEC-3, R-AUDIT-1, R-AUDIT-2, R-AUDIT-3, R-AUDIT-4, R-AUDIT-5, R-PERF-4, R-BUILD-1, R-FM-1, R-FM-7, R-MIDI-1, R-MIDI-4, R-MIDIOUT-2, R-MIDIOUT-6, R-STORE-1, R-STORE-3, R-STORE-4, R-STORE-5, R-STORE-6, R-STORE-8, R-UI-6, R-UI-7, R-UI-8, R-PRESET-1, R-ARP-1, R-ARP-2, R-ARP-7, R-GOLD-1, R-GOLD-2, R-GOLD-3, R-REL-1, R-REL-2, R-REL-3, R-PKG-1, R-BUILD-3, R-STORE-10, R-STORE-11 | PASS | 26.9 |
| C-REUSE | reuse lint (SPDX licence and copyright on every file) | R-LIC-1, R-LIC-2 | PASS | 0.9 |
| C-COMMIT-MSG | Commit messages follow .gitmessage | R-PROC-1 | PASS | 0.0 |
| C-LOW-PROFILE | Low profile: name, description, topics, README | R-PUB-1 | PASS | 0.5 |
| C-SECRETS | No secrets in tracked files | R-PUB-2 | PASS | 10.1 |
| C-PRIVATE | No private terms in tracked files or commit messages | R-PUB-3 | PASS | 2.1 |
| C-NO-TOOLCHAIN | No toolchain parts or binaries tracked | R-REPRO-1 | PASS | 0.0 |
| C-DENY-LISTS | Claude Code deny lists never drop an entry | R-CLEAN-4, R-SEP-2 | PASS | 0.0 |
| C-TRANSCRIPTS | Archived session transcripts: banners and forbidden material | R-CLEAN-1, R-CLEAN-3, R-CLEAN-5, R-SEP-2 | PASS | 3.0 |
| C-SEP-TERMS | No emulator-only identifiers outside the spec side's folders | R-SEP-1, R-SPEC-2 | PASS | 2.6 |
| C-SPEC-LINT | docs/HARDWARE-SPEC.md: every entry has an ID, fact, sources, standing; no code; IDs kept | R-SPEC-1, R-SPEC-3 | PASS | 0.0 |
| C-CLEAN-FOLDER | A fresh clean folder has no spec-side files and denies them | R-CLEAN-1, R-SEP-2 | PASS | 56.3 |
| C-FWTEST-PIN | tools/fwtest runs an image pinned by digest | R-SEP-3, R-HARN-10 | PASS | 0.0 |
| C-SDK-PIN | Vendored SDK files match the pinned commit | R-REPRO-5, R-LIC-2 | PASS | 0.0 |
| C-PLAITS-PIN | Vendored Plaits files match the pinned upstream commits | R-REPRO-7, R-LIC-2 | PASS | 0.7 |
| C-EMU-PIN | Vendored emulator crates match the pinned upstream commit | R-REPRO-6, R-LIC-2 | PASS | 0.2 |
| C-IMAGE | Build container (pinned base, toolchain SHA-256 checked) | R-REPRO-1, R-REPRO-2 | PASS | 14.6 |
| C-BUILD-A | Build A in a fresh container (source at /mnt/small-beeps-src) | R-REPRO-3, R-BUILD-1 | PASS | 2.6 |
| C-BUILD-B | Build B in a fresh container (source at another path) | R-REPRO-3 | PASS | 2.6 |
| C-DETERMINISM | Builds A and B are byte-identical | R-REPRO-3 | PASS | 0.0 |
| C-FW-SIZE | Firmware image size (code, data, bss) from build A | R-BUILD-2 | PASS | 0.0 |
| C-FW-SUITE | Firmware in fwtest: boot, clock, tick and heartbeat timing, vector table, idle, fault and stray reports, the screen, the panel's keys, encoders, pot and LEDs, the audio output and the test instrument (tests/fw/boot.suite) | R-BOOT-1, R-BOOT-2, R-BOOT-3, R-BOOT-4, R-BOOT-5, R-CLK-1, R-IRQ-1, R-IRQ-2, R-IRQ-3, R-IRQ-4, R-LCD-1, R-LCD-2, R-LCD-3, R-LCD-4, R-LCD-5, R-LCD-6, R-KEY-1, R-KEY-2, R-KEY-3, R-ENC-1, R-ENC-2, R-POT-1, R-POT-2, R-LED-1, R-LED-2, R-LED-3, R-INPUT-1, R-INPUT-2, R-INPUT-3, R-AUD-1, R-AUD-2, R-AUD-3, R-AUD-4, R-AUD-5, R-AUD-6, R-AUD-7, R-FM-1, R-FM-3, R-FM-4, R-FM-5, R-FM-6, R-FM-8, R-FM-9, R-MIDI-1, R-MIDI-2, R-MIDI-3, R-MIDI-4, R-MIDI-5, R-MIDI-6, R-MIDI-7, R-MIDIOUT-1, R-MIDIOUT-2, R-MIDIOUT-3, R-MIDIOUT-4, R-MIDIOUT-5, R-MIDIOUT-6, R-MIDIOUT-7, R-MIDIOUT-8, R-STORE-1, R-STORE-2, R-STORE-3, R-STORE-4, R-STORE-5, R-STORE-6, R-STORE-7, R-STORE-8, R-STORE-9, R-UI-1, R-UI-2, R-UI-3, R-UI-4, R-UI-5, R-UI-6, R-UI-7, R-UI-8, R-UI-9, R-UI-10, R-UI-11, R-UI-12, R-UI-13, R-UI-14, R-ARP-7, R-GOLD-1, R-GOLD-2 | PASS | 244.4 |
| C-PRESETS | The preset bank in fwtest: each preset's reference note (clipping, DC, clicks, loudness, its category's shape), 16 voices, golden SHA-256 (tools/preset_suite.py) | R-PRESET-1, R-PRESET-2, R-PRESET-3, R-PRESET-4 | PASS | 52.5 |
| C-ARP | The arpeggiator in fwtest: each mode and rate against its model, the frames of its steps, MIDI clock in and out, MIDI out, no stuck notes, its screen, saving, under load (tools/arp_suite.py) | R-ARP-1, R-ARP-2, R-ARP-3, R-ARP-4, R-ARP-5, R-ARP-6, R-ARP-7, R-ARP-8, R-GOLD-1 | PASS | 21.2 |
| C-PACKAGE | The firmware as a .fwsc: packed from build A's package link, it boots in fwtest's package path as the raw image does in the suite's main cases, and fwtest refuses each broken package at the reader's check (tools/package_suite.py) | R-PKG-1, R-PKG-2 | PASS | 9.4 |
| C-SEAMS | Seams for firmwares built on small-beeps: the build's write-back store check, outside sources, per-folder flags, the engine seam, the platform alone, core 1's start, the runtime, the SysEx tap, raw MIDI out, the store's firmware kinds, saves cut by a power cut (tools/seams_suite.py) | R-BUILD-3, R-BUILD-4, R-BUILD-5, R-ENG-1, R-PLAT-1, R-CORE-1, R-RT-1, R-MIDI-8, R-MIDIOUT-9, R-STORE-10, R-STORE-11 | PASS | 404.0 |
| C-RELEASE | The app release from build A, made twice: byte for byte the same; release.json format 1.0; the .fm1img passes the app's checks in order (tools/release.py selftest) | R-REL-1, R-REL-2 | PASS | 0.1 |
| C-PERF | Firmware size, RAM, stack high-water and instructions per period, within budget and the 3% speed gate | R-PERF-1, R-PERF-2, R-PERF-3, R-LCD-6, R-MIDIOUT-3, R-UI-4, R-ARP-8 | PASS | 11.2 |
| C-PERF-PROBES | Deliberately slower and bigger builds fail the performance gates; a known stack use shows | R-PERF-3, R-PERF-5 | PASS | 35.3 |
| C-PLAITS-BENCH | The Plaits load test: demo builds, soft-float exact, every engine measured, clean audio | R-PLAITS-1, R-PLAITS-2, R-PLAITS-3, R-PLAITS-4 | PASS | 47.8 |
| C-HARNESS-SCOPE | The harness uses no stock-boot path (packages only through the package reader) | R-HARN-9 | PASS | 0.0 |
| C-HARNESS-IMAGES | Harness test images rebuild identically with the pinned toolchain | R-HARN-8 | PASS | 1.8 |
| C-HARNESS-IMAGE | fwtest container (pinned bases, offline build) | R-HARN-8 | PASS | 19.3 |
| C-HARNESS-IMAGE-REPRO | The fwtest container rebuilds to the same image ID (from scratch, later, from a context with other file times and owners) | R-HARN-8 | PASS | 22.8 |
| C-HARNESS-TEST | The harness's own tests (cargo test in the container) | R-HARN-1, R-HARN-2, R-HARN-3, R-HARN-4, R-HARN-5, R-HARN-6, R-HARN-7 | PASS | 5.3 |
| C-HARNESS-ISA | fwtest runs every instruction form the pinned toolchain knows for the firmware's CPU flags, or the form is a documented gap (harness/isa/known-gaps.txt) | R-HARN-14 | PASS | 317.7 |
| C-HARNESS-SUITE-A | Harness suite, run A (fresh container, tests at /mnt/harness-a) | R-HARN-1, R-HARN-2, R-HARN-3, R-HARN-4, R-HARN-5, R-HARN-7 | PASS | 1.5 |
| C-HARNESS-SUITE-B | Harness suite, run B (fresh container, tests at another path) | R-HARN-6 | PASS | 1.5 |
| C-HARNESS-DET | Harness suite runs A and B are byte-identical | R-HARN-6 | PASS | 0.0 |
| C-SPEC-EXPERIMENTS | Spec-side experiments rebuild identically and give the results the spec cites | R-SPEC-4 | PASS | 4.0 |
| C-MERGE | Signed owner merge of a pull request that passed CI | R-PROC-2 | PASS | 1.7 |
| C-RECORD-PRIVATE | No private terms in the record's own files (any that hold one are withheld, named with their SHA-256) | R-PUB-3 | PASS | 0.7 |

## Outputs

| File | SHA-256 |
|------|---------|
| `app-pkg.bin` | `3577c147259644c5ef83c8e6a02c88fc4c44b26b518bd5b7e9dfdfa7dfde2401` |
| `app-pkg.elf` | `7b026ceff9fb7b874c3d03b882513ddf68b0b1abd73bbcb1c9f31601c64526c2` |
| `app.bin` | `5bc12a3465ccf32e5b50fc42a7f9673483719165504c05ad42e1eb16eb7ac034` |
| `app.elf` | `0c91a3e5fdac039bbe3f83b947f9273fb7758e695185e7ad87024eb9d057ceab` |
| `app.size` | `060eeece056f6eb666a92f04c28fcf2c4a044663a8c0975db4f4b0647e25f1c5` |

## Firmware size

| Part | Bytes |
|------|-------|
| code | 55240 |
| data | 80 |
| bss | 164880 |
| image | 55320 |
| stack | 4096 |

## Performance

Overall: **PASS**. Period: audio-block-steady.

| Measure | Value |
|---------|-------|
| code | 55240 |
| data | 80 |
| bss | 164880 |
| image | 55320 |
| static_ram | 220080 |
| stack_reserved | 4096 |
| stack_high_water | 572 |
| stack_method | pattern, two stacks |
| startup_instructions | 1070916 |
| instructions | 1301356 |
| periods | 690 |
| instructions_per_period | 1886.023 |
| frame_update_us | 3.125 |
| render_us | 812.708 |
| heartbeat_update_us | 3.667 |
| run of 1250 ms | 2694782 instructions, 861 periods, ended at 1250.087 ms |
| run of 2250 ms | 3996138 instructions, 1551 periods, ended at 2250.738 ms |

Loaded (`tests/fw/scripts/perfload.txt`, SHA-256 `5ef283c100b0de5a37b9c195b0af41b3f7c2e7af70536d897672e4a7dfefb102`): 75215535 instructions for 689 audio blocks, 109166.234 a block.

- loaded run of 1250 ms: 79363146 instructions, 861 periods, ended at 1250.000 ms
- loaded run of 2250 ms: 154578681 instructions, 1550 periods, ended at 2250.489 ms

Baseline: the record of e5a0b353ae69, the latest of f6b8a7552f2ec142d725ab14abf2a4249456b79a^1 on origin/records.

Loaded baseline: the record of e5a0b353ae69, the latest of f6b8a7552f2ec142d725ab14abf2a4249456b79a^1 on origin/records.

| Gate | Result | Detail |
|------|--------|--------|
| code | PASS | 55240 of 57344 bytes (ARP budget) |
| static_ram | PASS | 220080 of 229376 bytes (ARP budget) |
| stack_high_water | PASS | 572 of 768 bytes (ARP budget) |
| startup_instructions | PASS | 1070916 of 1572864 instructions (ARP budget) |
| steady_per_period | PASS | 1886.023 of 2048 instructions per period (ARP budget) |
| loaded_per_period | PASS | 109166.234 of 147456 instructions per period (ARP budget) |
| speed | PASS | 1886.023 steady-state instructions per period, 1886.023 before: +0.00%, within 3% |
| loaded_speed | PASS | 109166.234 loaded instructions per period, 109166.234 before: +0.00%, within 3% |

## Plaits load test (M4b): PASS

fwtest's instructions per audio block (64 frames, 348160 of core 0's cycles), each engine at its heaviest over nine settings; voices that fit on core 0 beside the firmware at rest (1886.023 instructions a block; under the heaviest input 109166.234). Soft-float is our runtime's; hardware float is the toolchain's instructions, which fwtest runs; whether the chip has them is open (SR-5).

| # | Engine | Soft-float max | mean | voices | Hardware float max | mean | voices | Full-scale samples |
|---|---|---|---|---|---|---|---|---|
| 0 | virtual analog VCF | 1005720 | 960417 | 0 | 29150 | 28833 | 11 | 0 |
| 1 | phase distortion | 1149220 | 1097263 | 0 | 40840 | 39974 | 8 | 0 |
| 2 | six-op FM (bank 1) | 818620 | 732996 | 0 | 30560 | 27814 | 11 | 0 |
| 3 | six-op FM (bank 2) | 828940 | 746783 | 0 | 30760 | 28188 | 11 | 0 |
| 4 | six-op FM (bank 3) | 825170 | 743337 | 0 | 30510 | 27975 | 11 | 0 |
| 5 | wave terrain | 1141270 | 1026113 | 0 | 29900 | 27727 | 11 | 0 |
| 6 | string machine | 1215960 | 1128884 | 0 | 40500 | 40395 | 8 | 0 |
| 7 | chiptune | 184280 | 174173 | 1 | 10560 | 10273 | 32 | 0 |
| 8 | virtual analog | 864770 | 803401 | 0 | 32490 | 31364 | 10 | 0 |
| 9 | waveshaping | 751780 | 729522 | 0 | 19500 | 19192 | 17 | 0 |
| 10 | FM | 1122140 | 1076868 | 0 | 41400 | 41319 | 8 | 0 |
| 11 | grain | 1023190 | 870878 | 0 | 28580 | 27239 | 12 | 0 |
| 12 | additive | 1679090 | 1636539 | 0 | 45790 | 45759 | 7 | 0 |
| 13 | wavetable | 1291050 | 1271206 | 0 | 30680 | 30605 | 11 | 0 |
| 14 | chords | 1139300 | 1054855 | 0 | 35620 | 33122 | 9 | 33 |
| 15 | speech | 888940 | 487133 | 0 | 26340 | 17532 | 13 | 0 |
| 16 | swarm | 1073190 | 1043340 | 0 | 28210 | 27369 | 12 | 0 |
| 17 | noise | 1039730 | 949790 | 0 | 48380 | 47297 | 7 | 1 |
| 18 | particle | 1184630 | 1119922 | 0 | 47720 | 41848 | 7 | 0 |
| 19 | string | 1126790 | 949440 | 0 | 38530 | 35533 | 8 | 0 |
| 20 | modal | 1838250 | 1785765 | 0 | 52640 | 52586 | 6 | 23 |
| 21 | bass drum | 922440 | 867906 | 0 | 27000 | 26378 | 12 | 149 |
| 22 | snare drum | 1031790 | 967518 | 0 | 35080 | 33394 | 9 | 3 |
| 23 | hi-hat | 627630 | 609789 | 0 | 25220 | 25141 | 13 | 0 |

Two voices at once, core 0 and core 1, against one after the other on core 0:

| Engine | Float | apart | at once | speed-up |
|---|---|---|---|---|
| virtual analog VCF | soft | 1792030 | 972400 | 1.843 |
| virtual analog | soft | 1510230 | 778490 | 1.940 |
| string | soft | 1456230 | 858550 | 1.696 |
| virtual analog VCF | hardware | 56240 | 28320 | 1.986 |
| virtual analog | hardware | 60610 | 29950 | 2.024 |
| string | hardware | 73430 | 36920 | 1.989 |

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

## Traceability

| Requirement | Checks | Result |
|-------------|--------|--------|
| R-PROC-1 | C-UNIT, C-COMMIT-MSG | PASS |
| R-PROC-2 | C-MERGE | PASS |
| R-PROC-3 | - | not machine-checked (review) |
| R-PROC-4 | C-UNIT | PASS |
| R-REC-1 | C-UNIT | PASS |
| R-REC-2 | - | not machine-checked (records.yml, ots-upgrade.yml) |
| R-REPRO-1 | C-NO-TOOLCHAIN, C-IMAGE | PASS |
| R-REPRO-2 | C-IMAGE | PASS |
| R-REPRO-3 | C-BUILD-A, C-BUILD-B, C-DETERMINISM | PASS |
| R-REPRO-4 | - | not machine-checked (review (run by hand; result in the PR)) |
| R-REPRO-5 | C-SDK-PIN | PASS |
| R-REPRO-6 | C-EMU-PIN | PASS |
| R-REPRO-7 | C-PLAITS-PIN | PASS |
| R-BUILD-1 | C-UNIT, C-BUILD-A | PASS |
| R-BUILD-2 | C-FW-SIZE | PASS |
| R-BUILD-3 | C-UNIT, C-SEAMS | PASS |
| R-BUILD-4 | C-SEAMS | PASS |
| R-BUILD-5 | C-SEAMS | PASS |
| R-ENG-1 | C-SEAMS | PASS |
| R-PLAT-1 | C-SEAMS | PASS |
| R-CORE-1 | C-SEAMS | PASS |
| R-RT-1 | C-SEAMS | PASS |
| R-LIC-1 | C-REUSE | PASS |
| R-LIC-2 | C-REUSE, C-SDK-PIN, C-PLAITS-PIN, C-EMU-PIN | PASS |
| R-PUB-1 | C-UNIT, C-LOW-PROFILE | PASS |
| R-PUB-2 | C-SECRETS | PASS |
| R-PUB-3 | C-PRIVATE, C-RECORD-PRIVATE | PASS |
| R-CLEAN-1 | C-TRANSCRIPTS, C-CLEAN-FOLDER | PASS |
| R-CLEAN-2 | - | not machine-checked (review) |
| R-CLEAN-3 | C-UNIT, C-TRANSCRIPTS | PASS |
| R-CLEAN-4 | C-UNIT, C-DENY-LISTS | PASS |
| R-CLEAN-5 | C-TRANSCRIPTS | PASS |
| R-SEP-1 | C-SEP-TERMS | PASS |
| R-SEP-2 | C-UNIT, C-DENY-LISTS, C-TRANSCRIPTS, C-CLEAN-FOLDER | PASS |
| R-SEP-3 | C-FWTEST-PIN | PASS |
| R-HARN-1 | C-HARNESS-TEST, C-HARNESS-SUITE-A | PASS |
| R-HARN-2 | C-HARNESS-TEST, C-HARNESS-SUITE-A | PASS |
| R-HARN-3 | C-HARNESS-TEST, C-HARNESS-SUITE-A | PASS |
| R-HARN-4 | C-HARNESS-TEST, C-HARNESS-SUITE-A | PASS |
| R-HARN-5 | C-HARNESS-TEST, C-HARNESS-SUITE-A | PASS |
| R-HARN-6 | C-HARNESS-TEST, C-HARNESS-SUITE-B, C-HARNESS-DET | PASS |
| R-HARN-7 | C-HARNESS-TEST, C-HARNESS-SUITE-A | PASS |
| R-HARN-8 | C-HARNESS-IMAGES, C-HARNESS-IMAGE, C-HARNESS-IMAGE-REPRO | PASS |
| R-HARN-9 | C-HARNESS-SCOPE | PASS |
| R-HARN-10 | C-FWTEST-PIN | PASS |
| R-HARN-11 | - | not machine-checked (C-HARNESS-TEST, C-SPEC-EXPERIMENTS) |
| R-HARN-12 | - | not machine-checked (C-HARNESS-TEST) |
| R-HARN-13 | - | not machine-checked (C-HARNESS-TEST, C-HARNESS-SUITE-A) |
| R-HARN-14 | C-HARNESS-ISA | PASS |
| R-SPEC-1 | C-UNIT, C-SPEC-LINT | PASS |
| R-SPEC-2 | C-SEP-TERMS | PASS |
| R-SPEC-3 | C-UNIT, C-SPEC-LINT | PASS |
| R-SPEC-4 | C-SPEC-EXPERIMENTS | PASS |
| R-BOOT-1 | C-FW-SUITE | PASS |
| R-BOOT-2 | C-FW-SUITE | PASS |
| R-BOOT-3 | C-FW-SUITE | PASS |
| R-BOOT-4 | C-FW-SUITE | PASS |
| R-BOOT-5 | C-FW-SUITE | PASS |
| R-CLK-1 | C-FW-SUITE | PASS |
| R-IRQ-1 | C-FW-SUITE | PASS |
| R-IRQ-2 | C-FW-SUITE | PASS |
| R-IRQ-3 | C-FW-SUITE | PASS |
| R-IRQ-4 | C-FW-SUITE | PASS |
| R-IRQ-5 | - | not machine-checked (planned (SR-1)) |
| R-LCD-1 | C-FW-SUITE | PASS |
| R-LCD-2 | C-FW-SUITE | PASS |
| R-LCD-3 | C-FW-SUITE | PASS |
| R-LCD-4 | C-FW-SUITE | PASS |
| R-LCD-5 | C-FW-SUITE | PASS |
| R-LCD-6 | C-FW-SUITE, C-PERF | PASS |
| R-KEY-1 | C-FW-SUITE | PASS |
| R-KEY-2 | C-FW-SUITE | PASS |
| R-KEY-3 | C-FW-SUITE | PASS |
| R-ENC-1 | C-FW-SUITE | PASS |
| R-ENC-2 | C-FW-SUITE | PASS |
| R-POT-1 | C-FW-SUITE | PASS |
| R-POT-2 | C-FW-SUITE | PASS |
| R-LED-1 | C-FW-SUITE | PASS |
| R-LED-2 | C-FW-SUITE | PASS |
| R-LED-3 | C-FW-SUITE | PASS |
| R-INPUT-1 | C-FW-SUITE | PASS |
| R-INPUT-2 | C-FW-SUITE | PASS |
| R-INPUT-3 | C-FW-SUITE | PASS |
| R-AUD-1 | C-FW-SUITE | PASS |
| R-AUD-2 | C-FW-SUITE | PASS |
| R-AUD-3 | C-FW-SUITE | PASS |
| R-AUD-4 | C-FW-SUITE | PASS |
| R-AUD-5 | C-FW-SUITE | PASS |
| R-AUD-6 | C-FW-SUITE | PASS |
| R-AUD-7 | C-FW-SUITE | PASS |
| R-FM-1 | C-UNIT, C-FW-SUITE | PASS |
| R-FM-2 | - | not machine-checked (review; C-FW-SUITE (R-FM-8)) |
| R-FM-3 | C-FW-SUITE | PASS |
| R-FM-4 | C-FW-SUITE | PASS |
| R-FM-5 | C-FW-SUITE | PASS |
| R-FM-6 | C-FW-SUITE | PASS |
| R-FM-7 | C-UNIT | PASS |
| R-FM-8 | C-FW-SUITE | PASS |
| R-FM-9 | C-FW-SUITE | PASS |
| R-MIDI-1 | C-UNIT, C-FW-SUITE | PASS |
| R-MIDI-2 | C-FW-SUITE | PASS |
| R-MIDI-3 | C-FW-SUITE | PASS |
| R-MIDI-4 | C-UNIT, C-FW-SUITE | PASS |
| R-MIDI-5 | C-FW-SUITE | PASS |
| R-MIDI-6 | C-FW-SUITE | PASS |
| R-MIDI-7 | C-FW-SUITE | PASS |
| R-MIDI-8 | C-SEAMS | PASS |
| R-MIDIOUT-1 | C-FW-SUITE | PASS |
| R-MIDIOUT-2 | C-UNIT, C-FW-SUITE | PASS |
| R-MIDIOUT-3 | C-FW-SUITE, C-PERF | PASS |
| R-MIDIOUT-4 | C-FW-SUITE | PASS |
| R-MIDIOUT-5 | C-FW-SUITE | PASS |
| R-MIDIOUT-6 | C-UNIT, C-FW-SUITE | PASS |
| R-MIDIOUT-7 | C-FW-SUITE | PASS |
| R-MIDIOUT-8 | C-FW-SUITE | PASS |
| R-MIDIOUT-9 | C-SEAMS | PASS |
| R-STORE-1 | C-UNIT, C-FW-SUITE | PASS |
| R-STORE-2 | C-FW-SUITE | PASS |
| R-STORE-3 | C-UNIT, C-FW-SUITE | PASS |
| R-STORE-4 | C-UNIT, C-FW-SUITE | PASS |
| R-STORE-5 | C-UNIT, C-FW-SUITE | PASS |
| R-STORE-6 | C-UNIT, C-FW-SUITE | PASS |
| R-STORE-7 | C-FW-SUITE | PASS |
| R-STORE-8 | C-UNIT, C-FW-SUITE | PASS |
| R-STORE-9 | C-FW-SUITE | PASS |
| R-STORE-10 | C-UNIT, C-SEAMS | PASS |
| R-STORE-11 | C-UNIT, C-SEAMS | PASS |
| R-STORE-12 | - | not machine-checked (C-UNIT, C-SEAMS) |
| R-UI-1 | C-FW-SUITE | PASS |
| R-UI-2 | C-FW-SUITE | PASS |
| R-UI-3 | C-FW-SUITE | PASS |
| R-UI-4 | C-FW-SUITE, C-PERF | PASS |
| R-UI-5 | C-FW-SUITE | PASS |
| R-UI-6 | C-UNIT, C-FW-SUITE | PASS |
| R-UI-7 | C-UNIT, C-FW-SUITE | PASS |
| R-UI-8 | C-UNIT, C-FW-SUITE | PASS |
| R-UI-9 | C-FW-SUITE | PASS |
| R-UI-10 | C-FW-SUITE | PASS |
| R-UI-11 | C-FW-SUITE | PASS |
| R-UI-12 | C-FW-SUITE | PASS |
| R-UI-13 | C-FW-SUITE | PASS |
| R-UI-14 | C-FW-SUITE | PASS |
| R-PRESET-1 | C-UNIT, C-PRESETS | PASS |
| R-PRESET-2 | C-PRESETS | PASS |
| R-PRESET-3 | C-PRESETS | PASS |
| R-PRESET-4 | C-PRESETS | PASS |
| R-ARP-1 | C-UNIT, C-ARP | PASS |
| R-ARP-2 | C-UNIT, C-ARP | PASS |
| R-ARP-3 | C-ARP | PASS |
| R-ARP-4 | C-ARP | PASS |
| R-ARP-5 | C-ARP | PASS |
| R-ARP-6 | C-ARP | PASS |
| R-ARP-7 | C-UNIT, C-FW-SUITE, C-ARP | PASS |
| R-ARP-8 | C-ARP, C-PERF | PASS |
| R-GOLD-1 | C-UNIT, C-FW-SUITE, C-ARP | PASS |
| R-GOLD-2 | C-UNIT, C-FW-SUITE | PASS |
| R-GOLD-3 | C-UNIT | PASS |
| R-REL-1 | C-UNIT, C-RELEASE | PASS |
| R-REL-2 | C-UNIT, C-RELEASE | PASS |
| R-REL-3 | C-UNIT | PASS |
| R-PKG-1 | C-UNIT, C-PACKAGE | PASS |
| R-PKG-2 | C-PACKAGE | PASS |
| R-AUDIT-1 | C-UNIT | PASS |
| R-AUDIT-2 | C-UNIT | PASS |
| R-AUDIT-3 | C-UNIT | PASS |
| R-AUDIT-4 | C-UNIT | PASS |
| R-AUDIT-5 | C-UNIT | PASS |
| R-AUDIT-6 | - | not machine-checked (review; C-TRANSCRIPTS (no transcript outside `sessions/clean/` and `sessions/spec/`)) |
| R-PERF-1 | C-PERF | PASS |
| R-PERF-2 | C-PERF | PASS |
| R-PERF-3 | C-PERF, C-PERF-PROBES | PASS |
| R-PERF-4 | C-UNIT | PASS |
| R-PERF-5 | C-PERF-PROBES | PASS |
| R-PLAITS-1 | C-PLAITS-BENCH | PASS |
| R-PLAITS-2 | C-PLAITS-BENCH | PASS |
| R-PLAITS-3 | C-PLAITS-BENCH | PASS |
| R-PLAITS-4 | C-PLAITS-BENCH | PASS |

## Environment

```json
{
  "build_image_id": "sha256:6726ffd961763c887070f3bea1aae3d3460da1be05b68908dd78eff314bef1f1",
  "build_image_tag": "small-beeps-build:2f1adc7009fddc03",
  "claude_configs": {
    "clean.json": "7577a4fc70762a34a55887a7a96eb18842cf056d9a82b207306b4231223ad7a0",
    "handmade-settings.json": "a557bd84008372ff9d3e24cd648df9986d76a05928d9f50b5d3e60975bf29b32",
    "handmade-spec-settings.json": "daa6c52d7e54c363b17ebace836c3019a6c4a9551f9d8af7b9175f88459ce27d",
    "spec.json": "84a7e56cfaa514639a55cf17627338970f1627738543c02999da9cf1d0f947bc"
  },
  "docker": "client 28.0.4 server 28.0.4",
  "dockerfile": {
    "base": "debian:bookworm-slim@sha256:ec31d744f83f4a73447ba045aaab9409997efe5cc706eca4890c1be36cc1606a",
    "dockerfile_frontend": "docker/dockerfile:1.10@sha256:865e5dd094beca432e8c0a1d5e1c465db5f998dca4e439981029b3b81fb39ed5",
    "snapshot": "20261020T000000Z",
    "source_date_epoch": "1767225600",
    "toolchain_name": "jieli-linux-toolchains-20250324.1",
    "toolchain_sha256": "f686586bcfb45e0f0bb27fd2b39c7a7f313cb4f0e88a66a14da621ffa8225958",
    "toolchain_url": "https://jl-update.oss-cn-shenzhen.aliyuncs.com/jieli-linux-toolchains-20250324.1.tar.xz"
  },
  "emulator_commit": "43ed5580064885e93bc8d20be931ae950d10cd4f",
  "fwtest_image": "ghcr.io/japes98/small-beeps@sha256:ba10d209195877efeb796e45ac134238e43b0d0eb2a551094eb55da740b8f78b",
  "git": "git version 2.56.0",
  "github": {
    "GITHUB_EVENT_NAME": "push",
    "GITHUB_REF": "refs/heads/main",
    "GITHUB_REPOSITORY": "japes98/small-beeps",
    "GITHUB_RUN_ATTEMPT": "1",
    "GITHUB_RUN_ID": "40872043698",
    "GITHUB_SHA": "f6b8a7552f2ec142d725ab14abf2a4249456b79a",
    "GITHUB_WORKFLOW": "records",
    "ImageOS": "ubuntu24",
    "ImageVersion": "20261026.354.1",
    "RUNNER_ARCH": "X64",
    "RUNNER_OS": "Linux"
  },
  "harness_image_tag": "small-beeps-fwtest:588cb83846027bc6",
  "host": "Linux 7.0.0-1017-azure x86_64",
  "python": "3.12.15",
  "reuse": "reuse, version 6.2.0",
  "sdk_commit": "5fa84a9b2f723a5e9337ad79dc2ad741fc98fe2d",
  "sdk_sha256sums": "49ddeb5feab02203f64e14f581808fc8e84d9af858953dd76b8602c906a95fa6"
}
```
