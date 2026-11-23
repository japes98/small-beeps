Rulings:
	1.	License finding accepted; keep section 52 and P-518. Two process notes:
	•	"first confirm" meant confirm before reading; ask next time;
	•	opening m-bootloader's README and PROVENANCE went beyond what I allowed; logged is fine, but ask first next time.
Also correct HW-178's provenance wording: the library is already machine code, so say exactly what was done (disassembled with the pinned toolchain, I assume).
	2.	Approved: add the read-only check of 0x16A00's four words to audio14, alongside U2-A, from power-off and after MIDI mode. Send the revised audio14 to clean after #244 merges.
	3.	Approved: U3-U as its own round after audio14's reading, written from HW-178, with outcomes listed ahead for my ruling. Any write to 0x16A00 or any other clock register comes to me first.
	4.	Yes: clean runs report1 whenever the build identity changes. Add it to clean's working rules.
Merges: merge clean's ba634aa3 into #244, then merge #244 when CI is green.
