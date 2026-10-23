<!--
SPDX-License-Identifier: MIT
SPDX-FileCopyrightText: 2026 japes98
-->

# Upstream report: SPI1 `CON` bits can be set but never cleared

For the owner to file with `joakimeriksson/fm1-emu` and to apply in the
F-Emulator app. Spec side only; not filed by a session. Found in session
SR-3 (2026-10-23) against commit `43ed5580064885e93bc8d20be931ae950d10cd4f`;
our copy carries the fix as `vendor/emulator/patches/0002-spi1-con-writes-replace.patch`.

## What goes wrong

A 32-bit write to SPI1's `CON` (0x11D00) is merged into the stored value
instead of replacing it (`crates/fm1-soc/src/lib.rs`, `spi1_write`, the
`0x11d00` arm):

```rust
let stored = self.sfr_get(addr);
self.sfr_set(addr, (stored & !0x4000) | (value & !0x4000));
```

So a bit, once written 1, can never be cleared by a later write. After any
write with bit 13 (transfer-done interrupt enable), every later SPI1
transfer, by DMA (`CNT`) or a single byte (`BUF`), raises IRQ 16, even after
`CON` has been written with bit 13 clear; and reading `CON` shows bits the
program cleared. Firmware that turns the interrupt off for polled transfers
(or acknowledges with `CON = 0x4000`, expecting that to drop the enable)
takes interrupts it didn't ask for.

On the chip `CON` is an ordinary read/write register: the JieLi AC79 SDK
clears its bits with ordinary writes (for example
`apps/common/example/peripheral/spi/spi_slave/spi_nomask_interrupt.c`,
`JL_SPI->CON &= ~(BIT(10) | BIT(11) | BIT(2))`).

## Reproduction

Raw image, board FM-1, a handler on IRQ 16 that counts and acknowledges
with `CON |= 0x4000`, the source enabled in `ICFG` and interrupts on, PC8
high:

| Step | Writes | Expected | Observed (before the fix) |
|------|--------|----------|---------------------------|
| 1 | `CON = 0x2000`; `ADR = buf`; `CNT = 2` | 1 interrupt; `CON` reads `0xA000` | 1; `0xA000` |
| 2 | `CON = 0`; `CNT = 2` | no interrupt; `CON` reads `0x8000` | 1 more; `0xA000` |
| 3 | `BUF = 0` | no interrupt | 1 more |

## The fix

Store what was written, less the bit-14 strobe:

```diff
-                let stored = self.sfr_get(addr);
-                self.sfr_set(addr, (stored & !0x4000) | (value & !0x4000));
+                self.sfr_set(addr, value & !0x4000);
```

Bit 14 still clears the pending flag (the lines above it are unchanged).
The crate's own tests still pass with it.
