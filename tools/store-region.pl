#!/usr/bin/perl
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
#
# Checks where a link put the store's region (clean-store-region;
# docs/DESIGN-NOTES.md, "Each firmware chooses its own store region";
# R-STORE-12). firmware/platform.ld takes the region from the symbol pair
# STORE_BASE and STORE_SIZE (chip offsets), today's three sectors at
# 0xFC000 unless a firmware's own linker script sets them first;
# tools/build.sh runs this on every link it makes.
#
#   nm ELF | perl tools/store-region.pl NAME
#
# Reads the link's symbols (sb_store_base and sb_store_size, the region;
# __data_load, __data_start and __data_end, where the image ends) and
# refuses, each with what is wrong and what would fit, a region that:
#   - doesn't start on a sector boundary, or isn't whole sectors;
#   - is smaller than the store's minimum, 3 sectors, or larger than the
#     most it keeps track of, STORE_SECTORS_MAX (store.h);
#   - overlaps the image (window address 0x02000000 + n is chip offset
#     0x4000 + n, HW-5, HW-91), or the boot area below it;
#   - crosses the end of the app area: 0x94000, the stock layout's (HW-80;
#     HW-87 to HW-93 give the area's start, 0x4000, and its length as a
#     package's area head has it, not a fixed end: SR-11), or lies in the
#     stock layout past it: the VM region, the Bluetooth sector, the stock
#     firmware's user patch region (0xEA000 to 0xFBFFF), which the base
#     leaves untouched, or the per-unit last sector (HW-80).
# So a region lies either in the app area after the image, or in the
# stock layout's unused region, 0xFC000 to 0xFEFFF. Prints the region on
# success; exits 1, after every problem found, if any.
use strict;
use warnings;

my $SECTOR = 0x1000;
my $MIN_SECTORS = 3;
my $MAX_SECTORS = 128;
my $WINDOW = 0x02000000;
my $AREA = 0x4000;
my $AREA_END = 0x94000;
my ($UNUSED, $UNUSED_END) = (0xFC000, 0xFF000);
my @STOCK = (
    [0x94000, 0xE9000, "the stock firmware's VM region (its settings, and where an update stages its loader)"],
    [0xE9000, 0xEA000, "the Bluetooth sector"],
    [0xEA000, 0xFC000, "the stock firmware's user patch region, which the base leaves untouched"],
    [0xFF000, 0x100000, "the chip's last sector, the per-unit key that must never be erased"],
);

my $name = shift // "-";
my %sym;
while (my $line = <STDIN>) {
    $sym{$2} = hex($1) if $line =~ /^([0-9a-fA-F]+)\s+\S\s+(\S+)\s*$/;
}
for my $s (qw(sb_store_base sb_store_size __data_load __data_start __data_end)) {
    die "$name: no symbol $s (a link with firmware/platform.ld?)\n" unless defined $sym{$s};
}
my ($base, $size) = ($sym{sb_store_base}, $sym{sb_store_size});
my $end = $base + $size;
my $image_end = $AREA + $sym{__data_load} - $WINDOW + $sym{__data_end} - $sym{__data_start};
my $after = ($image_end + $SECTOR - 1) & ~($SECTOR - 1);
my $sectors = int($size / $SECTOR);

sub hx { sprintf "0x%X", $_[0] }
sub span { sprintf "0x%X to 0x%X", $_[0], $_[1] - 1 }

# Where a region of n sectors would fit.
sub fits {
    my ($n) = @_;
    my $bytes = $n * $SECTOR;
    my $room = $after < $AREA_END ? int(($AREA_END - $after) / $SECTOR) : 0;
    my @where;
    if ($n >= $MIN_SECTORS && $n <= $MAX_SECTORS && $after + $bytes <= $AREA_END) {
        push @where, sprintf("a region of %d sectors fits in the app area after the image, from %s to %s at the latest",
                             $n, hx($after), hx($AREA_END - $bytes));
    } else {
        push @where, sprintf("the app area after the image (%s) holds %d sectors at most",
                             $room ? span($after, $AREA_END) : "none", $room > $MAX_SECTORS ? $MAX_SECTORS : $room);
    }
    push @where, sprintf("the unused region %s holds 3 (the default, STORE_BASE %s, STORE_SIZE 0x3000)",
                         span($UNUSED, $UNUSED_END), hx($UNUSED));
    return join("; ", @where);
}

my @bad;
my $want = $sectors < $MIN_SECTORS ? $MIN_SECTORS : $sectors > $MAX_SECTORS ? $MAX_SECTORS : ($sectors || $MIN_SECTORS);
if ($base % $SECTOR) {
    push @bad, sprintf("STORE_BASE %s is not on a 4 KiB sector boundary: %s or %s would be",
                       hx($base), hx($base & ~($SECTOR - 1)), hx(($base | ($SECTOR - 1)) + 1));
}
if ($size % $SECTOR) {
    push @bad, sprintf("STORE_SIZE %s is not a whole number of 4 KiB sectors: %s or %s would be",
                       hx($size), hx($size & ~($SECTOR - 1)), hx(($size | ($SECTOR - 1)) + 1));
}
if ($sectors < $MIN_SECTORS) {
    push @bad, sprintf("STORE_SIZE %s is %d sectors; the store needs %d at least (0x%X)",
                       hx($size), $sectors, $MIN_SECTORS, $MIN_SECTORS * $SECTOR);
} elsif ($sectors > $MAX_SECTORS) {
    push @bad, sprintf("STORE_SIZE %s is %d sectors; the store keeps track of %d at most (0x%X, STORE_SECTORS_MAX)",
                       hx($size), $sectors, $MAX_SECTORS, $MAX_SECTORS * $SECTOR);
}
if ($size) {
    if ($base < $AREA) {
        push @bad, sprintf("the region (%s) begins in the boot area (0x0 to 0x3FFF), which the chip boots from",
                           span($base, $end));
    }
    if ($base < $image_end && $end > $AREA) {
        push @bad, sprintf("the region (%s) overlaps the image, which ends at chip offset %s: start it at %s or later",
                           span($base, $end), hx($image_end - 1), hx($after));
    }
    if ($base < $AREA_END && $end > $AREA_END) {
        push @bad, sprintf("the region (%s) crosses the end of the app area at %s (HW-80's stock layout; SR-11)",
                           span($base, $end), hx($AREA_END));
    }
    for my $r (@STOCK) {
        my ($lo, $hi, $what) = @$r;
        if ($base < $hi && $end > $lo) {
            push @bad, sprintf("the region (%s) overlaps %s, %s (HW-80)", span($base, $end), $what, span($lo, $hi));
        }
    }
    if ($end > 0x100000) {
        push @bad, sprintf("the region (%s) runs past the end of the 1 MiB chip", span($base, $end));
    }
}
if (@bad) {
    print "$name: store region: $_\n" for @bad;
    print "$name: store region: where it would fit: ", fits($want), "\n";
    exit 1;
}
printf "%s: store region %s, %d sectors (the image ends at %s)\n", $name, span($base, $end), $sectors,
    hx($image_end - 1);
exit 0;
