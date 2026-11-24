U3-U try 3 on the unit (way 0, fm1-20261123-194712): connects, "USB gone"/"USB back" work, the instrument plays on. Two questions for the SDK, as before (findings to the owner first):
	1.	What does the SDK use for a received packet's length? RXCOUNT1 read 56, 12, 60, 16, 64, 20, 68, 48 for 4-byte packets.
	2.	Out: the Mac got the first message again every time, and packets of 64 and 28 bytes went out where 4 were written. How does the SDK hand a packet to the endpoint: cache flush, the count register, the order of writes?
