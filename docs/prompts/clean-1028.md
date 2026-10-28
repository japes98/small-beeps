>>> FOR THE CLEAN SESSION ONLY. First, check that .claude/small-beeps-role in this folder says "clean". If it says anything else, stop at once, read nothing further, and tell the owner this message went to the wrong session. <<<

You are the firmware-side (clean) session. The owner may not be watching; take the most reasonable reading, say which you took, and keep going. Setup notes as before (clean folder, privacy rule, no hardware facts here, PRs to main, cumulative, one merge order, questions at the top, stop below 2 GB free). A spec session may work at the same time; never open its branches.

## 0. Start
The owner merged everything through #168 and spec's #155 to #162. Clean setup checks, archive clean-1027's transcript and run tools/check-transcripts.py (review entries as needed), EXPOSURE entry, save this prompt unedited as docs/prompts/clean-1028.md.

## 1. Pin fwtest 0.9.0
#162's merge published fwtest 0.9.0 (a store into its own base register keeps the old value, SR-10). Open the pin PR, run the firmware suite, store tests and ARP suite on it, and report any change. First in your merge order.

## 2. Two more requests from a firmware built on small-beeps (don't name or describe it)
- BR-12, a save that survives a power cut (needed soon): a record rewrite is atomic. If the power goes at any moment during a save, the next start finds either the complete old payload or the complete new one, never neither and never a mix. That includes the large records from BR-9. Keep the old copy until the new one is fully written and verified (a second copy, a log, or alternating slots; your choice, with the space cost stated), and say how much the store region must grow for it. Test it with fwtest's power-cut feature at every point of a save (the flash chip's cut injection), for small and large records.
- BR-11, per-folder compiler flags: tools/build.sh options so a downstream build can give its own source folders their own compiler flags (beside --src and --leave-out), with the base's own files still built with the base's flags. Documented in BUILDING-ON-SMALL-BEEPS.md, deterministic, tested.
Each its own PR, with requirements and DESIGN-NOTES entries.

## 3. Note for the hardware phase
Add to PLAN.md's hardware-phase list: USB MIDI (class-compliant device) for firmwares built on small-beeps (BR-10), so MIDI out reaches a computer or iPad on a real unit, which has no MIDI OUT jack. Nothing to build now.

Finish with "done, ready to clear", Questions, and one merge order.
