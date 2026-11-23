/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * USB MIDI, the device side (U3-F, clean-br17-audio14; usb_midi.h). A
 * MIDI-only device on the first USB core: endpoint 0 answers the standard
 * requests; one MIDI streaming interface (with the audio control
 * interface USB MIDI 1.0 puts before it) has a bulk OUT endpoint (1) and
 * a bulk IN endpoint (2). The host's MIDI plays the engine through MIDI
 * in's ring, as the jack's bytes do; the firmware's own channel messages
 * (the panel's notes, ARP's) go out to the host.
 *
 * The core's byte registers are reached through CON1's port (HW-86),
 * every access spaced from the last (HW-172) and every wait for MACK
 * bounded (HW-86), in port() alone. All of the device's work is done in
 * the start-of-frame interrupt (source 8, HW-171), once a frame, so one
 * context alone uses the port and INDEX; nothing runs before the host's
 * first frame, and with no host nothing runs at all.
 *
 * Built only with SB_USB_MIDI (fwtest's test builds). With SB_HW_FM1 the
 * build stops: no unit build writes a USB register until the owner rules
 * U3-U (Q-36), and published builds keep USB off until the project has
 * its own product ID (R-USB-1).
 */

#include "usb_midi.h"

#if defined(SB_USB_MIDI)
#if defined(SB_HW_FM1)
#error "SB_USB_MIDI is for fwtest's builds only: no unit build writes a USB register (R-USB-1, Q-36)"
#endif

#include "midi.h"
#include "WL82.h"

volatile struct sb_usb_record sb_usb;

/* --- The identity (R-USB-1) ---------------------------------------------- */

/* pid.codes' vendor ID 0x1209 with its test product ID 0x0001. The test
 * PID is for private, in-house testing only: it must not be on a device
 * that is redistributed, sold or manufactured. Before a release carries
 * USB the project applies for its own product ID and uses that (R-USB-1).
 * Never the stock firmware's, M-VAVE's, m-bootloader's (1209:0002) or the
 * ROM's (4C4A:8057) IDs (HW-173). */
#define USB_VID 0x1209u
#define USB_PID 0x0001u   /* pid.codes' test PID: in-house testing only, never on a redistributed device */

/* --- The core (HW-86, HW-171, HW-172) ------------------------------------ */

#define SRC_USB_SOF  8u          /* the first core's start of frame (HW-171) */
#define PRIO_USB     1u          /* above the engine's fill (0), as the scan */

#define CON0_PHY_ON   (1u << 0)  /* HW-171's names */
#define CON0_SOFIE    (1u << 10)
#define CON0_CLR_SOF  (1u << 12)
#define CON0_LINES    (3u << 16) /* DM_SE, DP_SE: steadily 0 with a computer that is on (HW-177) */

#define PORT_RNW   (1u << 14)    /* MC_RNW (HW-86) */
#define PORT_MACK  (1u << 15)    /* MACK */

/* The byte registers by index (HW-86, HW-172). */
#define R_FADDR     0u
#define R_POWER     1u
#define R_INTRTX1   2u
#define R_INTRRX1   4u
#define R_INTRUSB   6u
#define R_INTRTX1E  7u
#define R_INTRRX1E  9u
#define R_INTRUSBE  11u
#define R_INDEX     14u
#define R_TXMAXP    16u
#define R_CSR0      17u          /* endpoint 0; TXCSR1 for the others */
#define R_TXCSR2    18u
#define R_RXMAXP    19u
#define R_RXCSR1    20u
#define R_COUNT0    22u          /* endpoint 0; RXCOUNT1 for the others */
#define R_RXCOUNT2  23u

#define INTRUSB_SUSPEND 0x01u    /* HW-172 */
#define INTRUSB_RESET   0x04u

#define CSR0_RXPKTRDY    0x01u   /* HW-172, endpoint 0 as a device */
#define CSR0_TXPKTRDY    0x02u
#define CSR0_SENTSTALL   0x04u
#define CSR0_DATAEND     0x08u
#define CSR0_SETUPEND    0x10u
#define CSR0_SENDSTALL   0x20u
#define CSR0_CLRRXPKTRDY 0x40u
#define CSR0_CLRSETUPEND 0x80u

#define TXCSR_TXPKTRDY   0x01u
#define TXCSR_CLRDATATOG 0x40u
#define TXCSR2_MODE_TX   0x20u   /* TXCSR's bit 13, the direction (HW-172), in its high byte */
#define RXCSR_RXPKTRDY   0x01u
#define RXCSR_CLRDATATOG 0x80u

/* `POWER` as the SDK writes it with `FUSB_MODE` 0, the SDK's setting
 * (HW-172). What its bits mean is not given. */
#define POWER_SDK 0x60u

#define EP_OUT 1u                /* bulk OUT: the host's MIDI */
#define EP_IN  2u                /* bulk IN: ours */
#define EP_MAX 64u

/* The spacing of accesses through CON1's port (HW-172): m-bootloader
 * found a few cycles between them made the core babble on IN, and how far
 * apart is enough is not given. 2 us (48 of the time base's 24 MHz) is
 * this side's choice, kept here alone, for U3-U to set from the unit. */
#define USB_PORT_GAP 48u
/* HW-86: every wait for MACK bounded. */
#define USB_PORT_POLLS 1000u
/* The lines' reads before connecting: 32, 50 us apart. */
#define USB_LINE_READS 32u
#define USB_LINE_GAP   1200u

/* The DMA buffers: 64-byte aligned, as the SDK keeps its own, with the 4
 * bytes past a packet the first core's receive DMA writes (HW-172). */
static volatile u8 ep0_buf[EP_MAX + 4] __attribute__((aligned(64)));
static volatile u8 rx_buf[EP_MAX + 4] __attribute__((aligned(64)));
static volatile u8 tx_buf[EP_MAX + 4] __attribute__((aligned(64)));

static u32 port_last;

static u32 port(u32 v)
{
    u32 n, r = 0;

    while (sb_now() - port_last < USB_PORT_GAP)
        ;
    JL_USB->CON1 = v;
    for (n = 0; n < USB_PORT_POLLS; n++) {
        r = JL_USB->CON1;
        if (r & PORT_MACK)
            break;
    }
    if (n == USB_PORT_POLLS)
        sb_usb.port_timeouts++;
    port_last = sb_now();
    return r & 0xFFu;
}

static void wr(u32 index, u32 v)
{
    port(index << 8 | (v & 0xFFu));
}

static u32 rd(u32 index)
{
    return port(index << 8 | PORT_RNW);
}

/* --- The descriptors ------------------------------------------------------ */

static const u8 dev_desc[18] = {
    18, 1, 0x00, 0x02,           /* USB 2.0 */
    0, 0, 0,                     /* the class is the interfaces' */
    EP_MAX,
    USB_VID & 0xFF, USB_VID >> 8,
    USB_PID & 0xFF, USB_PID >> 8, /* pid.codes' test PID: in-house testing only (above) */
    0x00, 0x01,                  /* the device's release, 1.00 */
    1, 2, 0,                     /* manufacturer, product; no serial number (the owner's ruling) */
    1,
};

#define CFG_LEN 101u
#define MS_LEN  65u
static const u8 cfg_desc[CFG_LEN] = {
    9, 2, CFG_LEN, 0, 2, 1, 0, 0x80, 50,      /* the configuration: 2 interfaces, bus powered, 100 mA */
    9, 4, 0, 0, 0, 1, 1, 0, 0,                /* interface 0: audio control */
    9, 0x24, 1, 0x00, 0x01, 9, 0, 1, 1,       /* its header: 1.00, the collection holds interface 1 */
    9, 4, 1, 0, 2, 1, 3, 0, 0,                /* interface 1: MIDI streaming, 2 endpoints */
    7, 0x24, 1, 0x00, 0x01, MS_LEN, 0,        /* its header */
    6, 0x24, 2, 1, 1, 0,                      /* MIDI IN jack 1, embedded */
    6, 0x24, 2, 2, 2, 0,                      /* MIDI IN jack 2, external */
    9, 0x24, 3, 1, 3, 1, 2, 1, 0,             /* MIDI OUT jack 3, embedded, from jack 2 */
    9, 0x24, 3, 2, 4, 1, 1, 1, 0,             /* MIDI OUT jack 4, external, from jack 1 */
    9, 5, EP_OUT, 2, EP_MAX, 0, 0, 0, 0,      /* endpoint 1 OUT, bulk */
    5, 0x25, 1, 1, 1,                         /* into embedded jack 1 */
    9, 5, 0x80 | EP_IN, 2, EP_MAX, 0, 0, 0, 0, /* endpoint 2 IN, bulk */
    5, 0x25, 1, 1, 3,                         /* from embedded jack 3 */
};

static const u8 str_lang[4] = { 4, 3, 0x09, 0x04 };   /* English (US) */
/* "small-beeps", for the manufacturer and the product (R-USB-1). */
static const u8 str_name[24] = {
    24, 3, 's', 0, 'm', 0, 'a', 0, 'l', 0, 'l', 0, '-', 0, 'b', 0, 'e', 0, 'e', 0, 'p', 0, 's', 0,
};

_Static_assert(sizeof cfg_desc == 9 + 9 + 9 + 9 + MS_LEN, "the configuration's length");

/* --- The rings -------------------------------------------------------------
 * In: the host's MIDI bytes, written by the frame's interrupt, read by the
 * engine (usb_midi_take). Out: event packets, written by the engine
 * (usb_midi_send), read by the frame's interrupt. Each index is written by
 * one side only. */
#define IN_RING  256u
#define OUT_RING 64u
static volatile u8 in_ring[IN_RING];
static volatile u32 in_head, in_tail;
static volatile u32 out_ring[OUT_RING];
static volatile u32 out_head, out_tail;

/* The bytes each code index carries (USB MIDI 1.0); 0: none. */
static const u8 cin_len[16] = { 0, 0, 2, 3, 3, 1, 2, 3, 3, 3, 3, 3, 2, 2, 3, 1 };

static void in_put(u8 b)
{
    u32 h = in_head;

    if (h - in_tail >= IN_RING) {
        sb_usb.rx_dropped++;
        return;
    }
    in_ring[h % IN_RING] = b;
    in_head = h + 1;
}

void usb_midi_take(void)
{
    u32 t = in_tail;

    while (t != in_head) {
        midi_rx_byte(in_ring[t % IN_RING]);
        t++;
    }
    in_tail = t;
}

void usb_midi_send(u32 status, u32 d1, u32 d2, u32 length)
{
    u32 h = out_head;

    if (!sb_usb.configuration)
        return;
    if (h - out_tail >= OUT_RING) {
        sb_usb.tx_dropped++;
        return;
    }
    out_ring[h % OUT_RING] = (status >> 4) | status << 8 | (d1 & 0x7Fu) << 16
                             | (length > 1 ? (d2 & 0x7Fu) << 24 : 0);
    out_head = h + 1;
}

/* --- Endpoint 0 ------------------------------------------------------------ */

static const u8 *ep0_data;
static u32 ep0_left, ep0_in;

/* The IN data stage's next packet; DataEnd on its last. */
static void ep0_send(void)
{
    u32 n = ep0_left > EP_MAX ? EP_MAX : ep0_left, i;

    for (i = 0; i < n; i++)
        ep0_buf[i] = ep0_data[i];
    ep0_data += n;
    ep0_left -= n;
    ep0_in = ep0_left != 0;
    JL_USB->EP0_CNT = n;
    wr(R_CSR0, CSR0_TXPKTRDY | (ep0_in ? 0 : CSR0_DATAEND));
}

static void ep0_reply(const u8 *data, u32 len, u32 asked)
{
    ep0_data = data;
    ep0_left = len < asked ? len : asked;
    wr(R_CSR0, CSR0_CLRRXPKTRDY);
    ep0_send();
}

static void ep0_done(void)
{
    wr(R_CSR0, CSR0_CLRRXPKTRDY | CSR0_DATAEND);
}

static void ep0_stall(void)
{
    sb_usb.stalls++;
    ep0_in = 0;
    wr(R_CSR0, CSR0_CLRRXPKTRDY | CSR0_SENDSTALL);
}

static void ep_setup(void)
{
    wr(R_INDEX, EP_OUT);
    wr(R_RXMAXP, EP_MAX);
    wr(R_INDEX, EP_IN);
    wr(R_TXMAXP, EP_MAX);
    wr(R_TXCSR2, TXCSR2_MODE_TX);
    wr(R_INDEX, 0);
    wr(R_INTRUSBE, INTRUSB_RESET | INTRUSB_SUSPEND);
    wr(R_INTRTX1E, 1u << 0 | 1u << EP_IN);
    wr(R_INTRRX1E, 1u << EP_OUT);
}

static void setup(const u8 *s)
{
    static u8 two[2];
    u32 type = s[0], req = s[1], value = s[2] | (u32)s[3] << 8, len = s[6] | (u32)s[7] << 8;

    sb_usb.setups++;
    sb_usb.last_setup[0] = s[0] | (u32)s[1] << 8 | (u32)s[2] << 16 | (u32)s[3] << 24;
    sb_usb.last_setup[1] = s[4] | (u32)s[5] << 8 | (u32)s[6] << 16 | (u32)s[7] << 24;
    if (type == 0x80 && req == 6) {                       /* GET_DESCRIPTOR */
        switch (value >> 8) {
        case 1: ep0_reply(dev_desc, sizeof dev_desc, len); return;
        case 2: ep0_reply(cfg_desc, sizeof cfg_desc, len); return;
        case 3:
            if ((value & 0xFF) == 0) { ep0_reply(str_lang, sizeof str_lang, len); return; }
            if ((value & 0xFF) <= 2) { ep0_reply(str_name, sizeof str_name, len); return; }
            break;
        }
    } else if (type == 0x00 && req == 5) {                /* SET_ADDRESS */
        ep0_done();
        /* Written once the setup is taken, as fwtest's host checks it
         * (HARNESS.md, "USB"); when the chip takes it is U3-U's. */
        sb_usb.address = value & 0x7F;
        wr(R_FADDR, value & 0x7F);
        return;
    } else if (type == 0x00 && req == 9 && value <= 1) {  /* SET_CONFIGURATION */
        ep0_done();
        sb_usb.configuration = value;
        wr(R_INDEX, EP_OUT);
        wr(R_RXCSR1, RXCSR_CLRDATATOG);
        wr(R_INDEX, EP_IN);
        wr(R_CSR0, TXCSR_CLRDATATOG);
        wr(R_INDEX, 0);
        return;
    } else if (type == 0x80 && req == 8) {                /* GET_CONFIGURATION */
        two[0] = (u8)sb_usb.configuration;
        ep0_reply(two, 1, len);
        return;
    } else if ((type & 0x9F) == 0x80 && req == 0) {       /* GET_STATUS */
        two[0] = two[1] = 0;
        ep0_reply(two, 2, len);
        return;
    } else if (type == 0x81 && req == 10) {               /* GET_INTERFACE */
        two[0] = 0;
        ep0_reply(two, 1, len);
        return;
    } else if ((type == 0x01 && req == 11 && value == 0)  /* SET_INTERFACE, alternate 0 */
               || ((type & 0x9C) == 0 && (req == 1 || req == 3))) { /* CLEAR or SET_FEATURE */
        ep0_done();
        return;
    }
    ep0_stall();
}

static void ep0(void)
{
    u8 s[8];
    u32 csr, i;

    wr(R_INDEX, 0);
    csr = rd(R_CSR0);
    if (csr & CSR0_SENTSTALL)
        wr(R_CSR0, 0);
    if (csr & CSR0_SETUPEND) {
        wr(R_CSR0, CSR0_CLRSETUPEND);
        ep0_in = 0;
    }
    if (csr & CSR0_RXPKTRDY) {
        ep0_in = 0;
        if (rd(R_COUNT0) != 8) {
            ep0_stall();
            return;
        }
        for (i = 0; i < 8; i++)
            s[i] = ep0_buf[i];
        setup(s);
    } else if (ep0_in && !(csr & CSR0_TXPKTRDY)) {
        ep0_send();
    }
}

/* --- The bulk endpoints ---------------------------------------------------- */

static void bulk_out(void)
{
    u32 n, i, k, len;

    wr(R_INDEX, EP_OUT);
    if (!(rd(R_RXCSR1) & RXCSR_RXPKTRDY))
        return;
    n = rd(R_COUNT0) | rd(R_RXCOUNT2) << 8;
    if (n > EP_MAX)
        n = EP_MAX;
    for (i = 0; i + 4 <= n; i += 4) {
        len = cin_len[rx_buf[i] & 0x0Fu];
        if (!len)
            continue;
        sb_usb.rx_events++;
        for (k = 1; k <= len; k++)
            in_put(rx_buf[i + k]);
    }
    sb_usb.rx_packets++;
    wr(R_RXCSR1, 0);                     /* the buffer free again */
}

static void bulk_in(void)
{
    u32 n = 0, t = out_tail, w;

    if (t == out_head)
        return;
    wr(R_INDEX, EP_IN);
    if (rd(R_CSR0) & TXCSR_TXPKTRDY)
        return;
    while (t != out_head && n < EP_MAX) {
        w = out_ring[t % OUT_RING];
        tx_buf[n] = (u8)w;
        tx_buf[n + 1] = (u8)(w >> 8);
        tx_buf[n + 2] = (u8)(w >> 16);
        tx_buf[n + 3] = (u8)(w >> 24);
        n += 4;
        t++;
    }
    out_tail = t;
    JL_USB->EP2_CNT = n;
    wr(R_CSR0, TXCSR_TXPKTRDY);
    sb_usb.tx_packets++;
    sb_usb.tx_events += n / 4;
}

/* --- The frame's interrupt -------------------------------------------------- */

static void usb_frame(void) __attribute__((interrupt("")));

static void usb_frame(void)
{
    u32 usb, tx;

    JL_USB->CON0 = CON0_PHY_ON | CON0_SOFIE | CON0_CLR_SOF;
    sb_usb.frames++;
    usb = rd(R_INTRUSB);
    tx = rd(R_INTRTX1);
    (void)rd(R_INTRRX1);
    if (usb & INTRUSB_RESET) {
        sb_usb.resets++;
        sb_usb.address = 0;
        sb_usb.configuration = 0;
        ep0_in = 0;
        ep_setup();
    }
    if (tx & 1u)
        ep0();
    if (sb_usb.configuration) {
        bulk_out();
        bulk_in();
    }
}

/* --- The start --------------------------------------------------------------- */

/* The core's set-up. In fwtest only what its host waits for to connect
 * (HARNESS.md, "USB"): CON0's bit 0 and `POWER` (index 1) at the SDK's
 * value (HW-172). On the unit the set-up waits for Q-36's writes (the
 * core's clock and PHY) and the owner's ruling: U3-U replaces this
 * function, and nothing else here sets the core up. */
static void usb_core_setup(void)
{
    JL_USB->CON0 = CON0_PHY_ON;
    wr(R_POWER, POWER_SDK);
}

void usb_midi_start(void)
{
    u32 i, v, t;

    /* Before connecting: CON0's bits 16 and 17, steadily 0 with a computer
     * that is on (HW-177). Logged, not acted on. */
    for (i = 0; i < USB_LINE_READS; i++) {
        v = JL_USB->CON0;
        if (!i)
            sb_usb.lines_first = v;
        sb_usb.lines_or |= v & CON0_LINES;
        if (v & CON0_LINES)
            sb_usb.lines_set++;
        sb_usb.lines_reads++;
        for (t = sb_now(); sb_now() - t < USB_LINE_GAP;)
            ;
    }
    JL_USB->EP0_ADR = (u32)ep0_buf;
    JL_USB->EP1_RADR = (u32)rx_buf;
    JL_USB->EP1_CNT = EP_MAX;
    JL_USB->EP2_TADR = (u32)tx_buf;
    port_last = sb_now();
    sb_irq_enable(SRC_USB_SOF, usb_frame, PRIO_USB);
    usb_core_setup();
    ep_setup();
    JL_USB->CON0 = CON0_PHY_ON | CON0_SOFIE;
    sb_usb.magic = USB_MIDI_MAGIC;
}
#else
typedef int usb_midi_not_built;   /* SB_USB_MIDI unset: nothing (ISO C wants a declaration) */
#endif
