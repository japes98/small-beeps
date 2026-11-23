/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * USB MIDI, the device side (U3-F, clean-br17-audio14; U3-U,
 * clean-br17-u3u; usb_midi.h). A MIDI-only device on the first USB core:
 * endpoint 0 answers the standard requests; one MIDI streaming interface
 * (with the audio control interface USB MIDI 1.0 puts before it) has a
 * bulk OUT endpoint (1) and a bulk IN endpoint (2). The host's MIDI plays
 * the engine through MIDI in's ring, as the jack's bytes do; the
 * firmware's own channel messages (the panel's notes, ARP's) go out to the
 * host.
 *
 * - When: nothing is written to USB until the cable reading shows a
 *   computer that is on, CON0 bits 16 and 17 steadily 0 (HW-177), in
 *   USB_CABLE_RUNS checks in a row, the first at the app's start and then
 *   one about every second (the owner's ruling of 2026-11-23). On the
 *   battery, with a charger or a sleeping computer nothing is written.
 * - The set-up (u3_core_setup) is HW-178's writes in HW-178's order, then
 *   the device's interrupts and POWER in HW-172's order (the owner's
 *   ruling), the controller's interrupt enable (SIEIE) last. Each write
 *   names its source; nothing else is written there, and nothing to the
 *   block at 0x16A00 or to any clock register (the owner's direction).
 *   Every change to CON0 and IO CON0 reads the word and changes only its
 *   step's bits, whatever the start left set (HW-177: either state).
 * - The core's byte registers go through CON1's port (HW-86, HW-178) in
 *   port() alone: only while CON0's USB_NRST reads set, every access
 *   spaced from the last by USB_PORT_GAP (HW-172), bit 15 polled at most
 *   USB_PORT_POLLS times (HW-178). A give-up there (or an interrupt that
 *   keeps coming with nothing to do) logs the stage and the index, turns
 *   the controller's interrupt off at the CPU, and nothing more is written
 *   to USB until the next power-on; the instrument runs on (the owner's
 *   ruling). There is no stop sequence: none has a source.
 * - The device's work is done in the controller's interrupt (source 9,
 *   HW-171), and the packets out are started from main's loop with
 *   interrupts off, so one context at a time uses the port and INDEX.
 *
 * Built only with SB_USB_MIDI: fwtest's test builds and, with SB_HW_U3U,
 * the unit file for the owner's flash only (R-USB-1, the test product
 * ID). A unit build without SB_HW_U3U stops.
 */

#include "usb_midi.h"

#if defined(SB_USB_MIDI)
#if defined(SB_HW_FM1) && !defined(SB_HW_U3U)
#error "SB_USB_MIDI on a unit is U3-U's file for the owner's flash only: build it with SB_HW_U3U (R-USB-1)"
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

/* --- The core (HW-86, HW-171, HW-172, HW-178) ----------------------------- */

#define SRC_USB_CTRL 9u          /* the first core's controller (SIE) interrupt (HW-171) */
#define PRIO_USB     1u          /* below the tick (2), above the engine's fill (0) */

/* CON0's bits by HW-171's names. */
#define C0_PHY_ON   (1u << 0)
#define C0_NRST     (1u << 2)
#define C0_TM1      (1u << 3)
#define C0_CID      (1u << 4)
#define C0_VBUS     (1u << 5)
#define C0_SIEIE    (1u << 11)
#define C0_SIE_PND  (1u << 14)
#define C0_LINES    (3u << 16)   /* DM_SE, DP_SE: steadily 0 with a computer that is on (HW-177) */

/* IO CON0's bits by HW-171's names. */
#define IO_PDOWNS   (3u << 4)    /* DPPD, DMPD */
#define IO_PUPS     (3u << 6)    /* DPPU, DMPU */
#define IO_DPPU     (1u << 6)
#define IO_DPDIE    (1u << 9)
#define IO_DMDIE    (1u << 10)
#define IO_MODE     (1u << 11)
#define IO_SR       (1u << 12)

#define PORT_RNW   (1u << 14)    /* MC_RNW (HW-86) */
#define PORT_MACK  (1u << 15)    /* MACK */

/* The byte registers by index (HW-86, HW-172). */
#define R_FADDR     0u
#define R_POWER     1u
#define R_INTRTX1   2u
#define R_INTRRX1   4u
#define R_INTRUSB   6u
#define R_INTRTX1E  7u
#define R_INTRTX2E  8u
#define R_INTRRX1E  9u
#define R_INTRRX2E  10u
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

#define TXCSR_TXPKTRDY   0x01u   /* HW-172, a transmit endpoint as a device */
#define TXCSR_UNDERRUN   0x04u
#define TXCSR_CLRDATATOG 0x40u
#define TXCSR2_MODE_TX   0x20u   /* TXCSR's bit 13, the direction, in its high byte */
#define RXCSR_RXPKTRDY   0x01u   /* HW-172, a receive endpoint as a device */
#define RXCSR_OVERRUN    0x04u
#define RXCSR_DATAERROR  0x08u
#define RXCSR_CLRDATATOG 0x80u

/* `POWER` as the SDK writes it with `FUSB_MODE` 0, the SDK's setting
 * (HW-172). What its bits mean is not given. */
#define POWER_SDK 0x60u

#define EP_OUT 1u                /* bulk OUT: the host's MIDI */
#define EP_IN  2u                /* bulk IN: ours */
#define EP_MAX 64u               /* endpoint 0's DMA buffer, EP0_SETUP_LEN (HW-171) */

/* The spacing of accesses through CON1's port, its one place (the owner's
 * ruling: generous to start with; MIDI needs little speed). HW-172:
 * m-bootloader found a few cycles between accesses made the core babble on
 * IN; how far apart is enough is not given. 10 us (240 of sb_now()'s
 * 24 MHz units); logged in every record (gap_units). */
#define USB_PORT_GAP 240u
/* HW-178: bit 15 polled up to 20 000 times. */
#define USB_PORT_POLLS 20000u
/* The cable reading: USB_LINE_READS reads USB_LINE_GAP apart (50 us) a
 * check, a check about every second, USB_CABLE_RUNS in a row steadily 0
 * before the set-up. */
#define USB_LINE_READS 32u
#define USB_LINE_GAP   1200u
#define USB_CABLE_RUNS 3u
/* Records of the cable reading's changes, at most (the rest counted). */
#define USB_CABLE_RECORDS 16u
/* The controller's interrupt taken this many times in a row with no flag
 * up: a give-up (USB_WHY_STORM). */
#define USB_STORM 1000u

/* The DMA buffers: 64-byte aligned, as the SDK keeps its own, each with
 * the 4 bytes past a packet the first core's receive DMA writes (HW-172). */
static volatile u8 ep0_buf[EP_MAX + 4] __attribute__((aligned(64)));
static volatile u8 rx_buf[EP_MAX + 4] __attribute__((aligned(64)));
static volatile u8 tx_buf[EP_MAX + 4] __attribute__((aligned(64)));

static u32 port_last, work_stage, spur_run, irq_on;
static volatile u32 in_busy, addr_pending, addr_beat;

static void stage(u32 k)
{
    if (!sb_usb.stage_beat[k])
        sb_usb.stage_beat[k] = sb_beacon.beats ? sb_beacon.beats : 1u;
    sb_usb.last_stage = k;
}

/* No more writes to USB until the next power-on: the controller's
 * interrupt off at the CPU (HW-20; not a USB write), the stage and the
 * index logged (the owner's ruling). */
static void give_up(u32 why, u32 index, u32 value)
{
    if (sb_usb.state == USB_STATE_DEAD)
        return;
    sb_usb.state = USB_STATE_DEAD;
    sb_usb.giveup_stage = work_stage;
    sb_usb.giveup_index = index;
    sb_usb.giveup_why = why;
    sb_usb.giveup_value = value;
    if (irq_on)
        sb_irq_disable(SRC_USB_CTRL);
    stage(USB_ST_GIVE_UP);
    sb_work++;                       /* main's loop logs it */
}

/* An access through CON1's port (HW-86, HW-178): while USB_NRST reads set,
 * spaced from the last, then a sync, bit 15 polled; a read's byte. */
static u32 port(u32 v)
{
    u32 n, r = 0, c0;

    if (sb_usb.state == USB_STATE_DEAD)
        return 0;
    c0 = JL_USB->CON0;
    if (!(c0 & C0_NRST)) {
        give_up(USB_WHY_NRST, v >> 8 & 0x3Fu, c0);
        return 0;
    }
    while (sb_now() - port_last < USB_PORT_GAP)
        ;
    JL_USB->CON1 = v;
    __asm__ volatile("csync" ::: "memory");
    for (n = 0; n < USB_PORT_POLLS; n++) {
        r = JL_USB->CON1;
        if (r & PORT_MACK)
            break;
    }
    port_last = sb_now();
    sb_usb.accesses++;
    if (n > sb_usb.polls_max)
        sb_usb.polls_max = n;
    if (n == USB_PORT_POLLS) {
        give_up(USB_WHY_MACK, v >> 8 & 0x3Fu, r);
        return 0;
    }
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
 * In: the host's MIDI bytes, written by the controller's interrupt, read by the
 * engine (usb_midi_take). Out: event packets, written by the engine
 * (usb_midi_send), read by main's loop and the controller's interrupt, one
 * at a time (interrupts off in main's loop). Each index is written by
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
        sb_usb.out_full++;
        return;
    }
    out_ring[h % OUT_RING] = (status >> 4) | status << 8 | (d1 & 0x7Fu) << 16
                             | (length > 1 ? (d2 & 0x7Fu) << 24 : 0);
    out_head = h + 1;
    sb_work++;                       /* main's loop starts the packet */
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

/* The address the host set. On the unit (SB_HW_U3U) written once its
 * status stage is over: at endpoint 0's next interrupt, or from main's
 * loop if none comes (a MUSB-style core takes FADDR at once, and the
 * status stage's reply must still go from address 0: general USB
 * knowledge, PROVENANCE P-99). In fwtest's test builds at once, as
 * fwtest's host checks it straight after the request (HARNESS.md, "USB"). */
static void addr_write(void)
{
    u32 a = addr_pending & 0x7Fu;

    addr_pending = 0;
    wr(R_FADDR, a);
    sb_usb.address = a;
    stage(USB_ST_ADDRESS);
    sb_work++;
}

/* After a bus reset, and before the configuration: endpoint 0's interrupt
 * alone (HW-172's device start). */
static void ep_reset(void)
{
    wr(R_INDEX, 0);
    wr(R_INTRUSBE, INTRUSB_RESET | INTRUSB_SUSPEND);
    wr(R_INTRTX1E, 1u << 0);
    wr(R_INTRRX1E, 0);
}

/* The configuration: the bulk endpoints' buffers, sizes and interrupts. */
static void ep_bulk_on(void)
{
    JL_USB->EP1_RADR = (u32)rx_buf;
    JL_USB->EP1_CNT = EP_MAX;
    JL_USB->EP2_TADR = (u32)tx_buf;
    wr(R_INDEX, EP_OUT);
    wr(R_RXMAXP, EP_MAX);
    wr(R_RXCSR1, RXCSR_CLRDATATOG);
    wr(R_INDEX, EP_IN);
    wr(R_TXMAXP, EP_MAX);
    wr(R_TXCSR2, TXCSR2_MODE_TX);
    wr(R_CSR0, TXCSR_CLRDATATOG);
    wr(R_INDEX, 0);
    wr(R_INTRTX1E, 1u << 0 | 1u << EP_IN);
    wr(R_INTRRX1E, 1u << EP_OUT);
    in_busy = 0;
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
        addr_pending = 0x80u | (value & 0x7F);
        addr_beat = sb_beacon.beats;
#if !defined(SB_HW_U3U)
        addr_write();
#endif
        return;
    } else if (type == 0x00 && req == 9 && value <= 1) {  /* SET_CONFIGURATION */
        ep0_done();
        sb_usb.configuration = value;
        if (value) {
            ep_bulk_on();
            stage(USB_ST_CONFIGURED);
            sb_work++;
        }
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

    if (addr_pending)
        addr_write();
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
    u32 n, i, k, len, csr;

    wr(R_INDEX, EP_OUT);
    csr = rd(R_RXCSR1);
    if (csr & (RXCSR_OVERRUN | RXCSR_DATAERROR))
        sb_usb.rx_overruns++;
    if (!(csr & RXCSR_RXPKTRDY))
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
    if (!sb_usb.stage_beat[USB_ST_FIRST_IN]) {
        stage(USB_ST_FIRST_IN);
        sb_work++;
    }
}

/* The next packet out, if the endpoint is free and something waits. */
static void bulk_in(void)
{
    u32 n = 0, t = out_tail, w, csr;

    if (t == out_head || in_busy || !sb_usb.configuration)
        return;
    wr(R_INDEX, EP_IN);
    csr = rd(R_CSR0);
    if (csr & TXCSR_UNDERRUN)
        sb_usb.tx_underruns++;
    if (csr & TXCSR_TXPKTRDY)
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
    in_busy = 1;
    sb_usb.tx_packets++;
    sb_usb.tx_events += n / 4;
}

/* --- The controller's interrupt (source 9, HW-171) ------------------------- */

static void usb_ctrl_irq(void) __attribute__((interrupt("")));

static void usb_ctrl_irq(void)
{
    u32 usb, tx, rx;

    if (sb_usb.state == USB_STATE_DEAD)
        return;
    sb_usb.irqs++;
    usb = rd(R_INTRUSB);
    tx = rd(R_INTRTX1);
    rx = rd(R_INTRRX1);
    if (sb_usb.state == USB_STATE_DEAD)
        return;
    if (!(usb | tx | rx)) {
        sb_usb.spurious++;
        if (++spur_run >= USB_STORM)
            give_up(USB_WHY_STORM, R_INTRUSB, JL_USB->CON0);
        return;
    }
    spur_run = 0;
    if (usb & INTRUSB_SUSPEND)
        sb_usb.suspends++;
    if (usb & INTRUSB_RESET) {
        sb_usb.resets++;
        sb_usb.address = 0;
        sb_usb.configuration = 0;
        addr_pending = 0;
        ep0_in = 0;
        in_busy = 0;
        ep_reset();
        if (!sb_usb.stage_beat[USB_ST_HOST_RESET]) {
            stage(USB_ST_HOST_RESET);
            sb_work++;
        }
    }
    if (tx & 1u)
        ep0();
    if (rx & 1u << EP_OUT)
        bulk_out();
    if (tx & 1u << EP_IN) {
        in_busy = 0;
        if (!sb_usb.stage_beat[USB_ST_FIRST_OUT]) {
            stage(USB_ST_FIRST_OUT);
            sb_work++;
        }
        bulk_in();
    }
}

/* --- The set-up -------------------------------------------------------------- */

/* A stage's write named on the step row, and, before steps 1 to 6, a
 * record, so a hang there shows in the log which write it was. From step
 * 6 (D+'s pull-up, the host sees the device) to SIEIE nothing waits. */
static void at(u32 k, const char *label, const char *step)
{
    work_stage = k;
    usb_midi_note(label, step);
}

#define IO_SET(bits)   (JL_USB_IO->CON0 = JL_USB_IO->CON0 | (bits))
#define IO_CLR(bits)   (JL_USB_IO->CON0 = JL_USB_IO->CON0 & ~(bits))
#define C0_SET(bits)   (JL_USB->CON0 = JL_USB->CON0 | (bits))
#define C0_CLR(bits)   (JL_USB->CON0 = JL_USB->CON0 & ~(bits))

/* HW-178's device start for the first core, then the device's interrupts
 * and POWER in HW-172's order (the owner's ruling of 2026-11-23), SIEIE
 * last. Every step written whatever it reads first (HW-177). */
static void u3_core_setup(void)
{
    at(USB_ST_PINS_IE, "USB step 1", "U3-U: 1 pins' input enables");
    IO_SET(IO_DMDIE);                                /* HW-178 step 1: IO CON0 bit 10 */
    IO_SET(IO_DPDIE);                                /* HW-178 step 1: then bit 9 */
    stage(USB_ST_PINS_IE);
    at(USB_ST_PADS, "USB step 2", "U3-U: 2 the pads to USB");
    IO_CLR(IO_MODE);                                 /* HW-178 step 2: IO_MODE cleared */
    IO_SET(IO_SR);                                   /* HW-178 step 2: SR set */
    stage(USB_ST_PADS);
    at(USB_ST_NRST_CLR, "USB step 3", "U3-U: 3 reset bits cleared");
    C0_CLR(C0_NRST | C0_CID | C0_VBUS | C0_SIE_PND); /* HW-178 step 3 */
    stage(USB_ST_NRST_CLR);
    at(USB_ST_CON1_ZERO, "USB step 4", "U3-U: 4 CON1 0");
    JL_USB->CON1 = 0;                                /* HW-178 step 4 */
    stage(USB_ST_CON1_ZERO);
    at(USB_ST_PHY, "USB step 5", "U3-U: 5 PHY_ON");
    C0_SET(C0_PHY_ON);                               /* HW-178 step 5 */
    stage(USB_ST_PHY);
    at(USB_ST_PULLS, "USB step 6", "U3-U: 6 the pulls, D+ pull-up");
    IO_CLR(IO_PDOWNS);                               /* HW-178 step 6: both pull-downs cleared */
    IO_CLR(IO_PUPS);                                 /* HW-178 step 6: both pull-ups cleared */
    IO_SET(IO_DPPU);                                 /* HW-178 step 6: then D+'s pull-up */
    stage(USB_ST_PULLS);
    at(USB_ST_NRST_SET, 0, "U3-U: 7 reset bits set");
    C0_SET(C0_NRST | C0_TM1 | C0_CID | C0_VBUS);     /* HW-178 step 7 */
    stage(USB_ST_NRST_SET);
    port_last = sb_now();
    at(USB_ST_IRQS_OFF, 0, "U3-U: device interrupts cleared");
    wr(R_INTRUSBE, 0);                               /* HW-178: INTRUSBE 0 */
    wr(R_INTRTX1E, 0);                               /* HW-178: every transmit enable cleared */
    wr(R_INTRTX2E, 0);
    wr(R_INTRRX1E, 0);                               /* HW-178: every receive enable cleared */
    wr(R_INTRRX2E, 0);
    stage(USB_ST_IRQS_OFF);
    at(USB_ST_POWER, 0, "U3-U: POWER");
    __asm__ volatile("cli" ::: "memory");            /* HW-178: POWER with interrupts off */
    wr(R_POWER, POWER_SDK);                          /* HW-172: 0x60 with FUSB_MODE 0 */
    __asm__ volatile("sti" ::: "memory");
    stage(USB_ST_POWER);
    at(USB_ST_EP0_BUF, 0, "U3-U: endpoint 0's buffer");
    JL_USB->EP0_ADR = (u32)ep0_buf;                  /* HW-172: one 64-byte buffer for endpoint 0, */
    JL_USB->EP1_RADR = (u32)ep0_buf;                 /* set as the receive address of endpoints 0 to 4 */
    JL_USB->EP2_RADR = (u32)ep0_buf;
    JL_USB->EP3_RADR = (u32)ep0_buf;
    JL_USB->EP4_RADR = (u32)ep0_buf;
    stage(USB_ST_EP0_BUF);
    at(USB_ST_USBE, 0, "U3-U: INTRUSBE");
    wr(R_INTRUSBE, INTRUSB_RESET | INTRUSB_SUSPEND); /* HW-172: reset and suspend */
    stage(USB_ST_USBE);
    at(USB_ST_EP0_ON, 0, "U3-U: endpoint 0's enable");
    wr(R_INTRTX1E, 1u << 0);                         /* HW-172: endpoint 0's set */
    stage(USB_ST_EP0_ON);
    if (sb_usb.state == USB_STATE_DEAD)
        return;
    at(USB_ST_IRQ, 0, "U3-U: the interrupt");
    __asm__ volatile("cli" ::: "memory");            /* ICFG's word shared with other sources */
    sb_irq_enable(SRC_USB_CTRL, usb_ctrl_irq, PRIO_USB); /* HW-172: the controller's interrupt registered */
    irq_on = 1;
    __asm__ volatile("sti" ::: "memory");
    stage(USB_ST_IRQ);
    at(USB_ST_SIEIE, 0, "U3-U: SIEIE");
    C0_SET(C0_SIEIE);                                /* HW-178: SIEIE set, last (the owner's ruling) */
    stage(USB_ST_SIEIE);
    sb_usb.state = USB_STATE_UP;
    /* Read back, with the cable reading (CON0 bits 16 and 17 in rb_con0). */
    sb_usb.rb_con0 = JL_USB->CON0;
    sb_usb.rb_con1 = JL_USB->CON1;
    sb_usb.rb_io_con0 = JL_USB_IO->CON0;
    usb_midi_note("USB set up", "U3-U: set up, waiting for the host");
}

/* --- The cable reading, main's loop ------------------------------------------ */

/* One check: USB_LINE_READS reads of CON0, 50 us apart. 1: steadily 0. */
static u32 cable_check(void)
{
    u32 i, v, t, any = 0, set = 0, first = 0;

    for (i = 0; i < USB_LINE_READS; i++) {
        v = JL_USB->CON0;
        if (!i)
            first = v;
        any |= v & C0_LINES;
        if (v & C0_LINES)
            set++;
        for (t = sb_now(); sb_now() - t < USB_LINE_GAP;)
            ;
    }
    sb_usb.lines_first = first;
    sb_usb.lines_or = any;
    sb_usb.lines_set = set;
    sb_usb.lines_reads = USB_LINE_READS;
    sb_usb.cable_checks++;
    return set ? 2u : 1u;
}

static u32 last_second, cable_records, lines_last;
static u32 logged[(USB_STAGES + 31) / 32];

static const char *const stage_label[USB_STAGES] = {
    [USB_ST_HOST_RESET] = "USB reset",
    [USB_ST_ADDRESS] = "USB address",
    [USB_ST_CONFIGURED] = "USB configured",
    [USB_ST_FIRST_IN] = "USB first in",
    [USB_ST_FIRST_OUT] = "USB first out",
    [USB_ST_GIVE_UP] = "USB give-up",
};

void usb_midi_poll(void)
{
    u32 k, c, first = !sb_usb.magic;

    if (first) {
        sb_usb.magic = USB_MIDI_MAGIC;
        sb_usb.gap_units = USB_PORT_GAP;
        sb_usb.poll_limit = USB_PORT_POLLS;
        last_second = sb_seconds;
    }
    if (sb_usb.state == USB_STATE_WAIT && (first || sb_seconds != last_second)) {
        last_second = sb_seconds;
        c = cable_check();
        sb_usb.cable_run = c == 1u ? sb_usb.cable_run + 1u : 0;
        if (c != sb_usb.cable) {
            sb_usb.cable_log[sb_usb.cable_changes % USB_CABLE_LOG] = sb_beacon.beats << 2 | c;
            sb_usb.cable_changes++;
            sb_usb.cable = c;
            if (cable_records < USB_CABLE_RECORDS) {
                cable_records++;
                usb_midi_note("USB cable", c == 1u ? "U3-U: cable reads a computer" : "U3-U: cable reads none");
            }
        }
        if (sb_usb.cable_run >= USB_CABLE_RUNS) {
            stage(USB_ST_CABLE);
            sb_usb.state = USB_STATE_SETUP;
            u3_core_setup();
        }
    } else if (sb_usb.state == USB_STATE_UP && sb_seconds != last_second) {
        /* The lines once set up: logged, not acted on. */
        last_second = sb_seconds;
        c = JL_USB->CON0 & C0_LINES;
        if (c != lines_last)
            sb_usb.lines_after++;
        lines_last = c;
    }
    if (sb_usb.state == USB_STATE_UP) {
        __asm__ volatile("cli" ::: "memory");
        /* The status stage is over within a frame or two (above). */
        if (addr_pending && sb_beacon.beats - addr_beat >= 3u) {
            sb_usb.addr_late++;
            addr_write();
        }
        bulk_in();
        __asm__ volatile("sti" ::: "memory");
    }
    for (k = USB_ST_HOST_RESET; k < USB_STAGES; k++)
        if (sb_usb.stage_beat[k] && !(logged[k / 32] >> k % 32 & 1u)) {
            logged[k / 32] |= 1u << k % 32;
            usb_midi_note(stage_label[k], stage_label[k]);
        }
}

#if !defined(SB_HW_U3U)
/* fwtest's builds: no step row, no log. */
void usb_midi_note(const char *label, const char *step)
{
    (void)label;
    (void)step;
}
#endif
#else
typedef int usb_midi_not_built;   /* SB_USB_MIDI unset: nothing (ISO C wants a declaration) */
#endif
