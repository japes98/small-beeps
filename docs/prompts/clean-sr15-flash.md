>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Setup notes as before (clean folder, privacy rule, no hardware facts here, PRs to main, cumulative, one merge order, questions at the top, stop below 2 GB free). A spec session is working at the same time; never open its branches.

## 0. Start
Clean setup checks, archive the last clean transcript and run tools/check-transcripts.py, EXPOSURE entry, save this prompt unedited as docs/prompts/clean-sr15-flash.md.

## 1. SR-15: one image for both flash parts
Units sold since autumn 2026 carry a second flash part. It answers the ID read with `0xB36014`; the owner's unit answers `0x856014`. small-beeps' saves, and those of firmwares built on the base (RevoiceDX keeps its saves at `0x80000`), must work on both.

The spec side has answered SR-15 in HARDWARE-SPEC section 27 (HW-120 to HW-124). It is in the spec side's pull request #189, which also carries your #188 and merges before this work starts (check that it has). Read section 27 with HW-76 to HW-79, HW-83, docs/SPEC-REQUESTS.md's SR-15, and docs/HARNESS.md "The flash chip". Take every fact from there. If you need one section 27 doesn't give, file a spec request that names it exactly.

What SR-15 found: for the commands the store sends, the two parts differ only in their ID. The store writes only when the ID is `STORE_PART` (`0x856014`), so on a `0xB36014` unit every save is refused (`STORE_ERR_PART`). Its other flash code already meets HW-124 items 2 and 3: only HW-121's commands, and a wait on the busy bit after every erase and every page program (SPEC-REQUESTS's SR-15 says where).

**(a) The store takes both parts.**
1. Writes when the ID is `0x856014` or `0xB36014` (HW-124 item 1), and still refuses every other ID: it reads, never writes. Keep the accepted IDs in one definition, each with its part's name and HW-120.
2. Reads back each erase (HW-124 item 4): after a sector erase and its wait, the sector reads all `0xFF` through `0x03`, or the erase counts as failed, as a failed program does now. Today an erase is checked only through the header programmed after it. Say what reading a whole sector back costs in time, and check that R-STORE-7 (no audio underrun, tick intervals) still holds with it.
3. Block protection (HW-124 item 5): at start-up, read status 1 (`0x05`) and status 2 (`0x35`) and keep them in the store's record, beside the ID. If any of BP0 to BP4 (status 1, mask `0x7C`) or CMP (status 2, mask `0x40`) is set, write nothing: refuse each save with its own result, as for an unknown part. Never write the status register; the store sends no `0x01`, `0x31` or `0x15`. Refusing whenever any bit is set is coarser than the protection table, but safe: it can't misread the table. Say if you'd rather check the table.
4. Keep the busy wait (HW-124 item 3): after every erase and every page program, the store waits on status 1's busy bit, never a fixed delay, allowing at least 12 ms for an erase and 3 ms for a program, as it does now. The erase read-back in item 2 comes after that wait, never in place of it. Tests show it: the busy test build (`SB_TEST_STORE_BUSY`) still passes. In fwtest, whose chip stays busy for the maximum times and ignores commands meanwhile (HARNESS.md "The flash chip"), the persist, wear and sweep cases still pass, so no command goes out before the wait ends.
5. Update docs/DESIGN-NOTES.md ("The part's rules") and docs/BUILDING-ON-SMALL-BEEPS.md (a firmware built on the base gets both parts and the same refusals), and add a requirement next to R-STORE-12.

**(b) Its tests.** fwtest's chip answers only `85 60 14`, and its status register never shows protection (HARNESS.md "The flash chip"; HW-83). fwtest can't be the second part, so:
- Add a test build (a define like `SB_TEST_STORE_PART`, as `SB_TEST_STORE_CUT` takes its parameters from the test's `--flash` file) whose store start-up uses an ID and two status bytes given by the test in place of what it read. Everything else runs as it does on the chip.
- With it, in fwtest:
  - with ID `0xB36014`, the persist case's save is there at the next start-up, and so is a firmware kind's payload with the test engine's region at `0x80000`, as RevoiceDX keeps its saves;
  - with `0x856014`, the same;
  - with an unknown ID (say `0xEF4014`), and with each protection bit set (one of BP0 to BP4, and CMP), each save is refused with its result, and `--flash-out`'s chip is the starting chip unchanged but for fwtest's own image (R-STORE-1).
- Without the define, the store's behaviour is unchanged. List which images change and why: the store's code changes, so the firmware's own image will.
- Don't change the harness. If a real second part in fwtest would test something these cases can't, say what, for the owner to raise as a harness request.

**Not in this change:** handing the flash from the code window to SPI0 and back on the unit (Q-22), and SPI0's clock (HW-124 item 6). The store doesn't work on a unit until Q-22 is settled, on either part.

Finish with "done, ready to clear", Questions, and one merge order.
