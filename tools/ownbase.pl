#!/usr/bin/perl
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
#
# Finds stores with write-back whose stored register is their own base
# register (clean-1027; docs/DESIGN-NOTES.md, "The write-back store
# check"): the pre-increment form [++rN=k] = rN and the post-increment
# form [rN++=k] = rN, with b[ or h[ as well, k a number or a register.
# What the chip stores then (the base's old value or its new one) is open
# (SR-10), so tools/build.sh refuses any object holding one.
#
#   objdump -d OBJECT | perl tools/ownbase.pl NAME
#
# Reads the toolchain's disassembly of one object (objdump -d shows its
# code sections only, never its constants) and prints each such store as
# NAME: SYMBOL+0xOFFSET (SECTION): INSTRUCTION. Exits 1 if it found any.
# Since BR-13 the disassembly must be made with the CPU and features the
# object was compiled for (tools/build.sh, note_cpu): an instruction the
# disassembler can't read (a float instruction, without the fprev1
# feature) is printed as NAME: SYMBOL+0xOFFSET (SECTION): unreadable, and
# makes it exit 2, since the bytes after it are misread too, and a store
# among them could be missed or made up.
use strict;
use warnings;

my $name = shift // "-";
my ($section, $symbol, $start, $bad, $unread) = ("?", "?", undef, 0, 0);
while (my $line = <STDIN>) {
    if ($line =~ /^Disassembly of section (\S+):/) {
        ($section, $symbol, $start) = ($1, "?", undef);
        next;
    }
    if ($line =~ /^(\S+):\s*$/) {
        ($symbol, $start) = ($1, undef);
        next;
    }
    if ($line =~ /^\s*([0-9a-f]+):.*<unknown instruction>/) {
        my $addr = hex($1);
        $start = $addr unless defined $start;
        printf "%s: %s+0x%x (%s): unreadable\n", $name, $symbol, $addr - $start, $section;
        $unread = 1;
        next;
    }
    next unless $line =~ /^\s*([0-9a-f]+):[^\t]*\t(.*?)\s*$/;
    my ($addr, $insn) = (hex($1), $2);
    $start = $addr unless defined $start;
    if ($insn =~ /\[(\+\+)?r(\d+)(\+\+)?=[^\]]*\]\s*=\s*r(\d+)\b/
        && (defined $1 || defined $3) && $2 == $4) {
        printf "%s: %s+0x%x (%s): %s\n", $name, $symbol, $addr - $start, $section, $insn;
        $bad = 1;
    }
}
exit($unread ? 2 : $bad);
