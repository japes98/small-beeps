>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Read this whole message before starting.

Setup notes: you are in the clean folder (~/Development/<top>/clean). Privacy rule as always; never read or print tools/private-terms.local. This prompt was written by the planning conversation (spec side): no hardware facts. Everything about the hardware comes from CONTRIBUTING.md's allowed sources, starting with docs/HARDWARE-SPEC.md and docs/HARNESS.md. Every PR targets main; dependent PRs are cumulative; ONE merge order at the end. Questions at the top of your final message. Stop all work if free disk drops below 2 GB.

## 0. Start
The owner merged #141 to #146. Run the clean setup checks, archive clean-pin-answers' transcript and run tools/check-transcripts.py, add your EXPOSURE.md entry, save this prompt unedited as docs/prompts/clean-a1-packager.md.

## 1. The owner's answers to clean-pin-answers' questions
1. The build image: option (b). Don't publish the image anywhere. A release records the build's identity instead: the base image's registry digest plus the SHA-256 of the build Dockerfile and of the toolchain, and a CI release checks that identity before it builds. Update config/build-image, release.py, the workflow, RELEASING.md and TOOLCHAIN.md to match.
2. The names-only listing in overnight-1025: approved, recorded as it is (a real names-only listing, not a false positive).
Also, from the spec side's answers: the hardware package's loader files, if one is ever needed, are the JieLi SDK's own uboot.boot and ota.bin, not FM1 Open's.

## 2. Pin fwtest 0.8.0
#143's merge published fwtest 0.8.0 (it adds --package). Open the pin PR, run the firmware suite, the store tests and the ARP suite on it, and report any change in outputs. First in your merge order.

## 3. Phase A1: the .fwsc packager
Build what docs/A1-PLAN.md asks for: a tools/ packager that turns our firmware build into a .fwsc package, from HARDWARE-SPEC.md's HW-87 to HW-93 only. Note HW-91: an app inside a package runs from a different address than a raw image, so the package build needs its own link. No loader binaries go in the repository. Test it with fwtest --package in CI (a package built from our firmware boots and passes the firmware suite's main cases, and broken variants are refused as HARNESS.md says). The F-Emulator app and the web build are checked by the owner's other sessions, not you.

## 4. A dry-run release for the app
The F-Emulator app needs a real .fm1img to test its reader against.
- Make a local dry run of tag m1 with tools/release.sh (as you did before; it marks itself as a dry run) and copy the .fm1img to ~/Development/<top>/drop/releases/ (create the folder if needed).
- If ~/Development/<top>/drop/releases/stand-in.fm1img exists, run tools/fm1img.py on it and report the result (which of the seven checks pass or fail). Read only that file in drop/releases besides your own.

Finish with "done, ready to clear", Questions, and one merge order.
