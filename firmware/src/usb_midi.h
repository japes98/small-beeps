/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * USB MIDI, the device side (U3-F, clean-br17-audio14): a MIDI-only
 * device on the first USB core (HW-171, HW-172, HW-86, HW-173), built only
 * with SB_USB_MIDI, which fwtest's test builds set (tools/seams_suite.py,
 * case usbmidi) and no unit or published build does: USB stays off there
 * (R-USB-1) until the owner rules U3-U and the project has its own
 * product ID. With SB_HW_FM1 the build stops (usb_midi.c).
 */

#ifndef USB_MIDI_H
#define USB_MIDI_H

#include "sb.h"

#if defined(SB_USB_MIDI)
/* What the device did, for the tests (tools/seams_suite.py reads it by
 * its symbol). */
struct sb_usb_record {
    u32 magic;          /* USB_MIDI_MAGIC once started */
    u32 lines_first;    /* CON0 as first read, before connecting */
    u32 lines_or;       /* CON0 bits 16 and 17 (DM_SE, DP_SE) ever set in those reads */
    u32 lines_set;      /* reads with either bit set (0 of all: steadily 0) */
    u32 lines_reads;    /* how many reads */
    u32 frames;         /* start-of-frame interrupts taken */
    u32 resets;         /* bus resets seen */
    u32 setups;         /* setup packets taken */
    u32 stalls;         /* requests answered with a stall */
    u32 last_setup[2];  /* the last setup packet, as two words */
    u32 address;        /* the address the host set */
    u32 configuration;  /* the configuration the host set (0: none) */
    u32 rx_packets;     /* bulk OUT packets taken */
    u32 rx_events;      /* USB MIDI event packets in them */
    u32 rx_dropped;     /* MIDI bytes the in ring had no room for */
    u32 tx_packets;     /* bulk IN packets sent */
    u32 tx_events;      /* event packets in them */
    u32 out_full;     /* event packets the out ring had no room for */
    u32 port_timeouts;  /* accesses through CON1's port whose MACK never came (HW-86) */
};

#define USB_MIDI_MAGIC 0x4D425355u   /* "USBM" */

extern volatile struct sb_usb_record sb_usb;

/* main, before interrupts are on: the lines read, the core set up, the
 * device connected. */
void usb_midi_start(void);
/* The engine (midi.c's midi_poll, once a block): the host's MIDI bytes
 * into MIDI in's ring, as the jack's. */
void usb_midi_take(void);
/* midi_out.c's midi_out_channel: the firmware's own channel message to
 * the host (the panel's notes; never MIDI thru's). */
void usb_midi_send(u32 status, u32 d1, u32 d2, u32 length);
#endif

#endif
