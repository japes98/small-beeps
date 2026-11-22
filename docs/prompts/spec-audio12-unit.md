audio12b (#241) worked on the unit. Record the results with audio13's prompt. Backup: ~/Documents/M-Flasher/backups/fm1-20261122-150817.bin. Results:
- SEL's instrument start: every stage logged in order (synth, ALNK0, L2, R2, route, panel), with sound.
- The sweep: in Bell, A1–A10 each had a longest fill of 982–1 018 µs with 8 voices, of 2 902 µs; nothing clipped, no late halves. fwtest gave 142–146 µs, so fwtest's fill time doesn't predict the unit's.
- The algorithms sounded different to the owner, so G is confirmed.
- Stops worked; MASTER was smooth, with no raw jumps.
- ARP was not tried.
- The audio12 hang was a packing error (built for fwtest's address); the packer now refuses that.

Write audio13 for clean and send it once ruled:
1. D5 as ruled: power-on goes straight to the instrument; HOME held at power-on gives the test screen.
2. U2 as ruled:
   - U2-A and U2-B. A key marks each cable-state change in the log, and the large area shows the state letter and whether anything changed. U2-A runs before the audio path starts.
   - U2-C on its own key, off at start-up.
   - Read-only: no USB register write, no pin change.
3. ARP check in the run steps, with its step timing logged.
4. Rulings ahead: list the likely outcomes and next steps for the owner to rule before clean starts.

Later rounds: D8 (levels), the store (saving patches), and the fwtest harness change.
