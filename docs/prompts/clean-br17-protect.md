>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Setup notes as before (clean folder, privacy rule, no hardware facts here, PRs to main, cumulative, one merge order, questions at the top, stop below 2 GB free). A spec session is working at the same time; never open its branches.

## 0. Start
- Clean setup checks, archive the last clean transcript and run tools/check-transcripts.py, EXPOSURE entry, save this prompt unedited as docs/prompts/clean-br17-protect.md.
- #196 has merged (with your #194 and #195). Wait until the spec side's #198 has merged too (it carries your #197; check that it has). Then read:
  - HARDWARE-SPEC HW-131 (section 29: block protection on both parts) and HW-134 (section 30: the code window's `BAUD`, `CON`, width and give-back; SR-17's answer; it supersedes HW-132), with HW-9, HW-121, HW-124 and HW-128;
  - HW-133 (section 31: what the owner's unit shows; source UNIT, a fact source by the owner's ruling) and the notes on Q-7, Q-8, Q-17 and Q-22;
  - docs/SPEC-REQUESTS.md, SR-17;
  - docs/HARNESS.md, "The flash chip" (block protection, since 0.12.0) and "Versions".
- Take every fact from those.

## 1. fwtest 0.12.0
#196's merge published fwtest 0.12.0 as `ghcr.io/japes98/small-beeps@sha256:70f2c78853c3881f43a1d47b51d67c5971b60710d3f8959c0ccc99b280753b3b` (HARNESS.md, "Versions"). Open the pull request that moves `config/fwtest-image` to it, as #194 did for 0.11.0. On 0.12.0 a flash file of exactly 1 MiB and two bytes sets status registers 1 and 2; every other flash file behaves as before, so every existing case should pass unchanged. Say if one doesn't.

## 2. The store's read-back against a protected chip
Until now no fwtest chip could ignore an erase, so the store's erase read-back never failed in a test (your #193 question). Add a case to the store suite with the part test build (`SB_TEST_STORE_PART`):
- its parameters give ID `0x856014` and status 0, so the store's own protection check passes;
- the store's region holds old bytes (not a valid sector), so the save has to erase;
- the chip's status registers, from the flash file's two extra bytes, set BP0 (status 1 `0x04`: the top 64 KiB, HW-131).

Expected, as the spec side saw it run locally on main's build:
- one erase, no programs;
- the save fails with `STORE_ERR_VERIFY`;
- the region is unchanged, and so is the rest of the chip but for fwtest's image (R-STORE-1).

Add the same with BP2 (`0x10`, the top half, which also covers a region at `0x80000`), and a control with CMP and BP2 (`0x10`, `0x40`: the bottom half), where the save goes through. Say what the store's record shows in each. If the store retries the erase, say how many times; the spec side's run saw one erase.

## 3. Reading a flash.bin with its status bytes
A protected run's `flash.bin` is 1 MiB and two bytes long; fwtest keeps the two bytes so the next run stays protected (HARNESS.md). Make every tool that reads a `flash.bin` as the chip take its first 1 MiB:
- `tools/store.py`'s `Image` (it asserts 1 MiB or the region alone);
- the store suite's `region()` and `outside_writes()`;
- anything else that reads `flash.bin`: list what you changed and what needed nothing.

## 4. The comments
- `firmware/src/store.c`, the part test build's comment: fwtest's chip now shows protection when the flash file sets it. Say why the test build still takes its own status bytes: they let a case show the store's own refusal and its read-back separately.
- docs/DESIGN-NOTES.md, wherever it says fwtest's chip never shows protection.

## 5. Start3b's result
start3b reached the main loop on the owner's unit. What it showed is in HARDWARE-SPEC HW-133, now facts (source UNIT); take it from there. For the next hardware build:
- **The window's give-back.** Follow HW-134's give-back as the owner ruled it: read `CON` before the take, then write `CON` = `0x00F00000`, `CON` = 0, `BAUD` = 1, and `CON` = the value read. start3's give-back writes no `BAUD`: add it. Use the one give-back wherever the flash is taken and given back (the store's path included), and say where that is.
- **The store.** HW-133 items 2 and 3: nothing to change. Say whether the suite already covers the counter across starts.
- **Core 1.** HW-133 item 4: it doesn't run after m-bootloader's call. Don't depend on core 1 in the hardware build; say what start3 and the firmware do without it. A probe to find what it needs is welcome as a proposal only (a spec request if it needs facts the spec doesn't have).
- **The panel.** HW-133 items 5 and 6 (MASTER, KNOB1) are facts: use them. PRESETS through an ADC channel is still a note (Q-7, Q-8): show what the build reads for it, and name the channel if it can, but don't map it yet.

Finish with "done, ready to clear", Questions, one merge order.
