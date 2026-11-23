/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * USB MIDI, the device side (U3-F, clean-br17-audio14; U3-U,
 * clean-br17-u3u): a MIDI-only device on the first USB core (HW-171,
 * HW-172, HW-178, HW-86, HW-173), built only with SB_USB_MIDI: fwtest's
 * test builds (tools/seams_suite.py, case usbmidi) and, with SB_HW_U3U,
 * the unit file for the owner's flash only. No published build sets it:
 * USB stays off there until the project has its own product ID (R-USB-1).
 */

#ifndef USB_MIDI_H
#define USB_MIDI_H

#include "sb.h"

#if defined(SB_USB_MIDI)
/* The stages, in the order the device reaches them; each one's beat is
 * kept (0: not reached) and main's loop names each new one in the log. */
enum usb_stage {
    USB_ST_CABLE,       /* the cable reading showed a computer: the set-up starts */
    USB_ST_PINS_IE,     /* HW-178 step 1: the pins' input enables */
    USB_ST_PADS,        /* step 2: the pads given to USB */
    USB_ST_NRST_CLR,    /* step 3: the reset bits cleared */
    USB_ST_CON1_ZERO,   /* step 4: CON1 written 0 */
    USB_ST_PHY,         /* step 5: PHY_ON */
    USB_ST_PULLS,       /* step 6: the pulls cleared, D+'s pull-up on */
    USB_ST_NRST_SET,    /* step 7: the reset bits set */
    USB_ST_IRQS_OFF,    /* the device's interrupt enables cleared (HW-178) */
    USB_ST_POWER,       /* POWER (HW-172, HW-178) */
    USB_ST_EP0_BUF,     /* endpoint 0's DMA buffer (HW-172) */
    USB_ST_USBE,        /* INTRUSBE: reset and suspend (HW-172) */
    USB_ST_EP0_ON,      /* endpoint 0's interrupt enable (HW-172) */
    USB_ST_IRQ,         /* the controller's interrupt registered (HW-171, HW-172) */
    USB_ST_SIEIE,       /* CON0's SIEIE, last (HW-178): interrupts on */
    USB_ST_HOST_RESET,  /* the host's first bus reset */
    USB_ST_ADDRESS,     /* the address the host set, written */
    USB_ST_CONFIGURED,  /* the configuration the host set */
    USB_ST_FIRST_IN,    /* the first MIDI packet in, from the host */
    USB_ST_FIRST_OUT,   /* the first packet out, taken by the host */
    USB_ST_GIVE_UP,     /* a give-up: nothing more is written to USB */
    USB_STAGES
};

/* Why the device gave up (giveup_why). */
#define USB_WHY_NRST  1u   /* CON0's USB_NRST read clear at a port access (HW-178) */
#define USB_WHY_MACK  2u   /* CON1's bit 15 never came in USB_PORT_POLLS polls (HW-178) */
#define USB_WHY_STORM 3u   /* the controller's interrupt kept coming with no flag up */

/* The device's state (state). */
#define USB_STATE_WAIT   0u   /* waiting for the cable reading to show a computer */
#define USB_STATE_SETUP  1u   /* setting the core up */
#define USB_STATE_UP     2u   /* set up: the host's to drive */
#define USB_STATE_DEAD   3u   /* given up: nothing more written until the next power-on */

#define USB_CABLE_LOG 8u
/* The host's attempts (one from each bus reset), the last USB_ATTEMPTS:
 * the spacing in use << 8 | what it reached, its reset's beat, the beat of
 * its last step. */
#define USB_ATTEMPTS 8u
#define USB_ATT_ADDRESS    1u
#define USB_ATT_CONFIGURED 2u
#define USB_ATT_IN         4u
#define USB_ATT_OUT        8u
/* The last packets each way (try 3): in, RXCOUNT1 | RXCOUNT2 << 8 | the
 * events taken << 16 | RXCSR1 << 24; out, the IN endpoint's TXCSR1 as
 * read before the packet | its bytes << 8 | the variant << 16. */
#define USB_PKT_LOG 8u
/* How a packet goes out (tx_variant; KEY8 on the test screen): 0 the one
 * buffer as set at the configuration; 1 its address written again before
 * each packet; 2 two buffers, the address switched each packet. */
#define USB_TX_VARIANTS 3u

/* What the device did, all words: the tests read it by its symbol
 * (tools/seams_suite.py's USB_REC), the unit's records carry it whole
 * (layout 14, tools/report_decode.py's _layout14). Keep the three in step. */
struct sb_usb_record {
    u32 magic;              /* USB_MIDI_MAGIC from the first poll */
    u32 gap_units;          /* the port's spacing, in sb_now() units (24 MHz) */
    u32 poll_limit;         /* the polls of CON1's bit 15 before a give-up */
    u32 state;              /* USB_STATE_* */
    u32 stage_beat[USB_STAGES];  /* each stage's beat (ms); 0: not reached */
    u32 last_stage;         /* the last stage reached */
    u32 giveup_stage;       /* the stage being worked on at a give-up */
    u32 giveup_index;       /* the byte register's index then */
    u32 giveup_why;         /* USB_WHY_* */
    u32 giveup_value;       /* CON0 (NRST) or CON1 (MACK) as read then */
    u32 lines_first;        /* the last cable check: CON0 at its first read */
    u32 lines_or;           /* CON0 bits 16 and 17 (DM_SE, DP_SE) ever set in it */
    u32 lines_set;          /* its reads with either bit set */
    u32 lines_reads;        /* its reads */
    u32 cable;              /* the last check's reading: 1 steadily 0 (a computer), 2 not */
    u32 cable_run;          /* checks in a row that read steadily 0 */
    u32 cable_checks;       /* checks made */
    u32 cable_changes;      /* changes of the reading */
    u32 cable_log[USB_CABLE_LOG];  /* the last changes: beat << 2 | reading */
    u32 lines_after;        /* once set up: CON0 bits 16 and 17 changes seen once a second (logged only) */
    u32 rb_con0;            /* read back after the set-up: CON0 */
    u32 rb_con1;            /* CON1 */
    u32 rb_io_con0;         /* IO CON0 */
    u32 irqs;               /* the controller's interrupts taken */
    u32 spurious;           /* of them, with no flag up */
    u32 resets;             /* bus resets seen */
    u32 suspends;           /* suspends seen */
    u32 setups;             /* setup packets taken */
    u32 stalls;             /* requests answered with a stall */
    u32 last_setup[2];      /* the last setup packet, as two words */
    u32 address;            /* the address the host set */
    u32 configuration;      /* the configuration the host set (0: none) */
    u32 rx_packets;         /* bulk OUT packets taken */
    u32 rx_events;          /* USB MIDI event packets in them */
    u32 rx_dropped;         /* MIDI bytes the in ring had no room for */
    u32 tx_packets;         /* bulk IN packets handed to the core */
    u32 tx_events;          /* event packets in them */
    u32 out_full;           /* event packets the out ring had no room for */
    u32 tx_underruns;       /* the IN endpoint's UnderRun seen (HW-172) */
    u32 rx_overruns;        /* the OUT endpoint's OverRun or DataError seen (HW-172) */
    u32 accesses;           /* accesses through CON1's port */
    u32 polls_max;          /* the most polls of bit 15 one access took */
    u32 addr_late;          /* FADDR written by main's loop, the status stage's interrupt not seen */
    u32 configs;            /* configurations set (one per attempt that got there) */
    u32 gap_presses;        /* presses of the test screen's spacing key */
    u32 attempt_n;          /* the host's attempts (bus resets) */
    u32 attempt[USB_ATTEMPTS][3];  /* the last attempts, by attempt_n % USB_ATTEMPTS (above) */
    u32 tx_variant;         /* how packets go out (USB_TX_VARIANTS) */
    u32 tx_done;            /* the IN endpoint's interrupts: a packet the host took */
    u32 rx_log_n;           /* packets in logged */
    u32 rx_log[USB_PKT_LOG];
    u32 tx_log_n;           /* packets out logged */
    u32 tx_log[USB_PKT_LOG];
    u32 frame_last;         /* the frame number at main's last look (once a second) */
    u32 gone_n;             /* the host's frames seen stopped */
    u32 back_n;             /* and counting again */
    u32 irq_peak;           /* the most of the controller's interrupts in one beat */
};

#define USB_MIDI_MAGIC 0x4D425355u   /* "USBM" */
#define USB_REC_WORDS (sizeof(struct sb_usb_record) / 4u)

extern volatile struct sb_usb_record sb_usb;

/* main's loop, at the app's start and each time it is woken: the cable
 * reading about once a second until it shows a computer, then the set-up;
 * once set up, the device's packets out; and each new stage named in the
 * log (usb_midi_note). */
void usb_midi_poll(void);
/* The engine (midi.c's midi_poll, once a block): the host's MIDI bytes
 * into MIDI in's ring, as the jack's. */
void usb_midi_take(void);
/* midi_out.c's midi_out_channel: the firmware's own channel message to
 * the host (the panel's notes; never MIDI thru's). */
void usb_midi_send(u32 status, u32 d1, u32 d2, u32 length);
/* A stage said on the unit's step row and, with a label, written to the
 * log (hw_audio.c, SB_HW_U3U); nothing in fwtest's builds. Main's loop
 * only: a record takes the flash. */
void usb_midi_note(const char *label, const char *step);
/* The test screen's spacing key (SB_HW_U3U): the next of the offered
 * spacings, from now on; returns it in us. */
u32 usb_midi_gap_key(void);
/* KEY8 on the test screen (SB_HW_U3U): the next way packets go out. */
u32 usb_midi_tx_key(void);
#endif

#endif
