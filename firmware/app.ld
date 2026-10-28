/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * Memory layout for the raw image (docs/DESIGN-NOTES.md, M0d): since
 * clean-1027 (BR-2) the platform's layout, firmware/platform.ld, with the
 * base's instrument's records asserted where they go: the FM engine's in
 * the engine's slot, the interface's and the arpeggiator's first among
 * the engine's records.
 */

INCLUDE platform.ld

ASSERT(sb_fm == 0x01C00590, "the FM engine's record must take the engine's slot (M5)")
ASSERT(sb_ui == 0x01C00870, "the interface's record must follow the store's (M8a)")
ASSERT(sb_arp == 0x01C008D0, "the arpeggiator's record must follow the interface's (ARP)")
