The owner's ruling (2026-11-23): the spec side's report below (P-519) is a source for the USB loop, as HW-172 and HW-178 are. Try 4 won't be flashed. Build try 5 on try 4, following the SDK's steps exactly.

The spec side's report (P-519), relayed unedited:

The most likely common factor: the SDK turns interrupts off around every endpoint register access, from the INDEX write to the last read or write that goes with it. INDEX is shared, and USB's interrupt now runs at the engine's priority, so this is the first thing to compare. Two receive details (below) also bear on the odd counts.

	1.	A received packet's length

	•	Where the length comes from: the SDK writes INDEX with the endpoint first, then reads RXCSR1. If bit 0 (RxPktRdy) is clear, the length is 0 and nothing else is read. If it is set, the SDK reads RXCOUNT1 (index 22) as the low byte and RXCOUNT2 (index 23) as the high byte. It copies the smaller of that count and the length asked for. Nothing else is used: no EPn_CNT word, no DMA address.
	•	The receive address is written again for every packet: before copying, the SDK writes the endpoint's buffer address to EPn_RADR again. With one buffer that is the same start address each time; with two buffers it alternates.
	•	Releasing the packet: the SDK writes RXCSR = (the value read & 0xFE9B) | 0x10. By HW-172's names, that keeps RxPktRdy as read, sets FlushFIFO, and clears OverRun, SendStall, SentStall and IncompRx. Whether this write comes before or after the copy depends on a flag not decoded.

What try 5 does:

	•	Interrupts off from each INDEX write to the last access that goes with it, everywhere, including in the interrupt handler.
	•	In: write INDEX, then read RXCSR1. Only if RxPktRdy is set, take the length from RXCOUNT1/RXCOUNT2. Write EPn_RADR again before each packet, and release the packet with the SDK's write. Keep try 4's checks (code index, at most 16 events, the buffer cleared after) as a guard, and log the length alongside.
	•	Out: wait for TxPktRdy to read clear, copy into the endpoint's own buffer, csync, write EPn_TADR again, write EPn_CNT with the byte count, then write TXCSR back with 0x01 set. Make this way 0, and keep the power-on cycling with the large text, with the old ways as 1 and 2.
	•	Set-up: TXCSR 0x48, RXCSR 0x90, and MAXP as the SDK writes it.
	•	Identity: its own, 0.15.0-u3u-t5.
	•	Gaps: if a step can't be followed from the report, say which, and don't guess.
	•	For the owner's run: a plain power-on, no keys held, no test screen. Way 0 is shown in large text at power-on. The owner plugs into the Mac, plays notes both ways, then unplugs. Only if way 0 fails do they power on again for ways 1 and 2.

	•	The unit's readings: 56, 12, 60, 16, 64, 20, 68, 48 look like two runs climbing by 4, more like a position than a count. That is an interpretation, not a fact. What to compare: whether INDEX was written with interrupts off, whether the RxPktRdy check was made, and whether EPn_RADR was written again.

	2.	Handing a packet to a transmit endpoint (first core)
	1.	Poll TXCSR until bit 0 (TxPktRdy) reads clear. The SDK never writes while the previous packet is still pending.
	2.	Copy up to the endpoint's packet size into that endpoint's own DMA buffer, from the SDK's endpoint table. The DMA never points at the caller's data. Then a csync.
	3.	Write that buffer's address to EPn_TADR again for every packet (0x1C + (n−1)·8; endpoint 4 at 0x38).
	4.	Write EPn_CNT with the byte count alone (0x08 + n·4; endpoint 4 at 0x34), with interrupts off.
	5.	Only then read TXCSR (indexes 17 and 18) and write it back with 0x01 set.

Longer data goes out as packets of the endpoint's size, each through these steps.

	•	No cache call: neither the send path nor the receive path calls a cache function. The only barriers are the core's csync and ssync. The library's function named "flushfifo" is steps 4 and 5, not a cache flush.
	•	Open: the SDK puts the buffers in their own .usb_fifo section, but whether that memory is cached isn't given. So these facts don't settle whether a flush is needed.
	•	Not decoded: the branch that handles TXCSR bit 7 (IncompTx) while polling.

Endpoint set-up values (first core)

	•	TXMAXP and RXMAXP are both written 1023. The access port carries only the low byte, so the core gets 0xFF; that byte truncation is confirmed in the port's write function.
	•	At set-up, TXCSR is written 0x48 (FlushFIFO and ClrDataTog) and RXCSR 0x90 (ClrDataTog and FlushFIFO). These bear on the 64- and 28-byte packets.
