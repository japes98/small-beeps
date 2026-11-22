audio12 on the unit, no key held: it stops on the first boot screen (the blue and green bars, which the owner says always appear first and are normally followed by a brief white bar and the next screen). It never gets past it. No sound. Holding HOME at power-on gives the same result. The backup is ~/Documents/M-Flasher/backups/fm1-20261122-135138.bin. Its app area is audio12 exactly, but the log has no 0.12.0-hw3v record: it still ends at audio11's #503. So the hang is after core 1's screen and before hw_a12_instrument's first record: the HOME read, fm_init, hw_a9_synth_key or hw_audio_start, or something the test screen's path set up that the instrument path skips. #240 is not to merge; the owner is going back to audio11.

Owner's ruling for audio12b, on top of #240:
1. Power-on goes to the test screen, as in audio11. The instrument start moves behind a test-screen key, until it has worked on the unit.
2. The instrument start writes a log record before each stage (synth key, audio start, L2, R2, route, panel), with the step row showing the stage, so a hang names itself.
3. Find the hang: compare what audio11's test-screen path sets up before its first record with what the instrument path does. Say how fwtest passed it, and add a seams case that would have caught it.
4. Keep S, G/G2 and D6 as built. The sweep runs from the test screen as planned.
