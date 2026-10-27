/* SPDX-License-Identifier: MIT */
/* SPDX-FileCopyrightText: 2026 japes98 */
/* The USB core's access port answers at once. Each access is written to
   USB_PORT (index << 8 | byte, bit 14 a read), then the port is polled for
   bit 15 (done), at most 1000 times as a firmware's own timeout would.
   Steps, each keeping the polls not answered and the word read in OUT(2k),
   OUT(2k + 1): 0 write index 11 = 0x5a; 1 read index 11; 2 write index 6
   = 0xff; 3 read index 6 (an interrupt flag); 4 read index 1 (never
   written). Then halt. */
#include "board.h"

static void access(u32 k, u32 word)
{
    u32 polls = 0u;
    USB_PORT = word;
    while ((USB_PORT & 0x8000u) == 0u && polls < 1000u) {
        polls++;
    }
    OUT(2u * k) = polls;
    OUT(2u * k + 1u) = USB_PORT;
}

int main(void)
{
    access(0u, 0x0b5au);
    access(1u, 0x4b00u);
    access(2u, 0x06ffu);
    access(3u, 0x4600u);
    access(4u, 0x4100u);
    return 0;
}
