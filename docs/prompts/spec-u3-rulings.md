Rulings:
1. (a) approved. Read JieLi's prebuilt USB library as machine code, with these conditions:
   - first confirm that the repository's Apache-2.0 license covers the prebuilt libraries, not just the source files;
   - take facts only (registers, values, order, delays), and copy no code;
   - record the provenance of each fact.

   Also say what's known about where m-bootloader's usb_midi.c got its USB set-up. If its provenance is clean, propose it as a source for my ruling; don't open it before then.
2. Agreed: any clock or PLL change gets its own ruling before a unit write.
3. (i): flash audio14 now, for the ARP fix.
4. No serial-number string.
5. audio14 approved as drafted. Send it to clean once #244 has merged.

USB product ID: in U3's outcomes, "apply for our own PID before release" should read: "our own product ID is an open question for the owner; published builds keep USB off until then."

Merges: close #243 unmerged. #244 merges when CI is green.
