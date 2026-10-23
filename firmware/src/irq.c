/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * Interrupts: our own vector table, which sources are enabled, and the
 * one way out when something goes wrong: report and halt.
 */

#include "sb.h"
#include "WL82.h"

/* HW-18: the handler of source n is the word at __vectors + 4n (app.ld). */
_Static_assert(sizeof(unsigned short) == 2, "a stub is 2 bytes");
extern volatile u32 __vectors[];
#define SOURCES 128

/* crt0.S: one 2-byte stub per source, in source order. */
extern const unsigned short sb_irq_stubs[];

/* HW-19 and the SDK's hwi.h (P-16): sources 0 to 2 are the debug,
 * exception and system-call sources, the CPU's own faults: their stubs
 * report a fault rather than a stray interrupt. */
#define SRC_EXCEPTION   1u
#define SRC_LAST_FAULT  2u

/* HW-20: 4 bits a source in ICFG00-ICFG31, bit 0 enable, bits 1-3 the
 * priority (higher wins). The exception source is enabled here; main
 * enables the others it handles (DESIGN-NOTES.md, M1 and M2). */
#define PRIO_FAULT  7u
#define ICFG_BITS(src, prio)  ((1u | (prio) << 1) << 4 * ((src) % 8))
#define ICFG_WORDS  32

/* HW-21: the master enable in the core register icfg. */
#define ICFG_MASTER (1u << 8)

void sb_irq_unexpected(u32 source, u32 reti) __attribute__((noreturn));

void sb_irq_init(void)
{
    volatile u32 *icfg = &q32DSP(0)->ICFG00;
    u32 n;

    for (n = 0; n < SOURCES; n++)
        __vectors[n] = (u32)&sb_irq_stubs[n];

    /* Every word written, so nothing a loader left enabled stays so. */
    _Static_assert(SRC_EXCEPTION / 8 == 0, "in ICFG00");
    icfg[0] = ICFG_BITS(SRC_EXCEPTION, PRIO_FAULT);
    for (n = 1; n < ICFG_WORDS; n++)
        icfg[n] = 0;
}

/* Installs a handler for a source and enables it at a priority (0 to 7),
 * before interrupts are turned on. */
void sb_irq_enable(u32 source, void (*handler)(void), u32 priority)
{
    volatile u32 *icfg = &q32DSP(0)->ICFG00;

    __vectors[source] = (u32)handler;
    icfg[source / 8] = (icfg[source / 8] & ~(0xFu << 4 * (source % 8))) | ICFG_BITS(source, priority);
}

/* HW-21: both gates, icfg's bit 8 and sti. */
void sb_irq_on(void)
{
    u32 cfg;

    __asm__ volatile("%0 = icfg" : "=r"(cfg));
    cfg |= ICFG_MASTER;
    __asm__ volatile("icfg = %0" :: "r"(cfg));
    __asm__ volatile("sti");
}

/* From crt0.S's stubs: an interrupt with no handler of its own. */
void sb_irq_unexpected(u32 source, u32 reti)
{
    sb_halt(source <= SRC_LAST_FAULT ? SB_HALT_FAULT : SB_HALT_STRAY, source, reti);
}

static const char reasons[3][5] = { "stray", "fault", "stack" };
static const char hex[16] = "0123456789abcdef";

/* Records why in the beacon, writes one console line, "HALT <reason>
 * <source in hex> ", and stops: interrupts off and a jump to itself,
 * which fwtest reports as a halt (docs/HARNESS.md). Nothing is resumed. */
void sb_halt(u32 reason, u32 source, u32 reti)
{
    char line[16] = "HALT ..... 000 \n";
    u32 i;

    __asm__ volatile("cli");
    sb_beacon.halt_source = source;
    sb_beacon.halt_reti = reti;
    sb_beacon.halt_reason = reason;
    for (i = 0; i < 5; i++)
        line[5 + i] = reasons[reason - 1][i];
    line[11] = hex[source >> 8 & 0xF];
    line[12] = hex[source >> 4 & 0xF];
    line[13] = hex[source & 0xF];
    sb_console_write(line, sizeof line / 4);
    for (;;)
        ;
}
