#!/bin/sh
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
#
# Vendors Plaits' sound engine (Emilie Gillet's Mutable Instruments Plaits,
# MIT) for the platform load test of M4b, from the original upstream at a
# pinned commit, and checks every file against vendor/plaits/SHA256SUMS
# (PROVENANCE P-28).
#
#   tools/fetch-plaits.sh --verify   check the committed files (default, offline)
#   tools/fetch-plaits.sh --fetch    re-download them from the pinned commits
#                                    into vendor/plaits/, then verify
#
# Two repositories, both upstream's own: pichenettes/eurorack at
# EURORACK_COMMIT (plaits/ and its README, whose licence section covers
# it), and pichenettes/stmlib at STMLIB_COMMIT, the commit eurorack's
# stmlib submodule is pinned to at EURORACK_COMMIT (checked on fetch).
# The files are the ones Plaits' voice (plaits/dsp/voice.cc) and its
# tables (plaits/resources.cc) include, and their sources (with the one
# source no header names, the speech synthesiser's phoneme table); nothing of the
# hardware drivers, bootloader, test or hardware designs. They are kept
# unmodified; any change would be a patch file in vendor/plaits/patches/
# with its reason (there is none).
#
# To vendor another file: add it to a list below, run --fetch, add its hash
# to SHA256SUMS in the same commit, and log it in PROVENANCE.md.
set -eu

EURORACK_URL=https://github.com/pichenettes/eurorack
EURORACK_COMMIT=f4cfa7697095a28d292bff758beb51deb49b5a86
STMLIB_URL=https://github.com/pichenettes/stmlib
STMLIB_COMMIT=e3bd7c9cc00e4364166f9905c0509b6ffd0535ec
# Paths in eurorack, vendored under vendor/plaits/eurorack/.
EURORACK_FILES="
    README.md
    plaits/dsp/chords/chord_bank.cc
    plaits/dsp/chords/chord_bank.h
    plaits/dsp/downsampler/4x_downsampler.h
    plaits/dsp/drums/analog_bass_drum.h
    plaits/dsp/drums/analog_snare_drum.h
    plaits/dsp/drums/hi_hat.h
    plaits/dsp/drums/synthetic_bass_drum.h
    plaits/dsp/drums/synthetic_snare_drum.h
    plaits/dsp/dsp.h
    plaits/dsp/engine/additive_engine.cc
    plaits/dsp/engine/additive_engine.h
    plaits/dsp/engine/bass_drum_engine.cc
    plaits/dsp/engine/bass_drum_engine.h
    plaits/dsp/engine/chord_engine.cc
    plaits/dsp/engine/chord_engine.h
    plaits/dsp/engine/engine.h
    plaits/dsp/engine/fm_engine.cc
    plaits/dsp/engine/fm_engine.h
    plaits/dsp/engine/grain_engine.cc
    plaits/dsp/engine/grain_engine.h
    plaits/dsp/engine/hi_hat_engine.cc
    plaits/dsp/engine/hi_hat_engine.h
    plaits/dsp/engine/modal_engine.cc
    plaits/dsp/engine/modal_engine.h
    plaits/dsp/engine/noise_engine.cc
    plaits/dsp/engine/noise_engine.h
    plaits/dsp/engine/particle_engine.cc
    plaits/dsp/engine/particle_engine.h
    plaits/dsp/engine/snare_drum_engine.cc
    plaits/dsp/engine/snare_drum_engine.h
    plaits/dsp/engine/speech_engine.cc
    plaits/dsp/engine/speech_engine.h
    plaits/dsp/engine/string_engine.cc
    plaits/dsp/engine/string_engine.h
    plaits/dsp/engine/swarm_engine.cc
    plaits/dsp/engine/swarm_engine.h
    plaits/dsp/engine/virtual_analog_engine.cc
    plaits/dsp/engine/virtual_analog_engine.h
    plaits/dsp/engine/waveshaping_engine.cc
    plaits/dsp/engine/waveshaping_engine.h
    plaits/dsp/engine/wavetable_engine.cc
    plaits/dsp/engine/wavetable_engine.h
    plaits/dsp/engine2/arpeggiator.h
    plaits/dsp/engine2/chiptune_engine.cc
    plaits/dsp/engine2/chiptune_engine.h
    plaits/dsp/engine2/phase_distortion_engine.cc
    plaits/dsp/engine2/phase_distortion_engine.h
    plaits/dsp/engine2/six_op_engine.cc
    plaits/dsp/engine2/six_op_engine.h
    plaits/dsp/engine2/string_machine_engine.cc
    plaits/dsp/engine2/string_machine_engine.h
    plaits/dsp/engine2/virtual_analog_vcf_engine.cc
    plaits/dsp/engine2/virtual_analog_vcf_engine.h
    plaits/dsp/engine2/wave_terrain_engine.cc
    plaits/dsp/engine2/wave_terrain_engine.h
    plaits/dsp/envelope.h
    plaits/dsp/fm/algorithms.cc
    plaits/dsp/fm/algorithms.h
    plaits/dsp/fm/dx_units.cc
    plaits/dsp/fm/dx_units.h
    plaits/dsp/fm/envelope.h
    plaits/dsp/fm/lfo.h
    plaits/dsp/fm/operator.h
    plaits/dsp/fm/patch.h
    plaits/dsp/fm/voice.h
    plaits/dsp/fx/diffuser.h
    plaits/dsp/fx/ensemble.h
    plaits/dsp/fx/fx_engine.h
    plaits/dsp/fx/low_pass_gate.h
    plaits/dsp/fx/overdrive.h
    plaits/dsp/fx/sample_rate_reducer.h
    plaits/dsp/noise/clocked_noise.h
    plaits/dsp/noise/dust.h
    plaits/dsp/noise/particle.h
    plaits/dsp/oscillator/grainlet_oscillator.h
    plaits/dsp/oscillator/harmonic_oscillator.h
    plaits/dsp/oscillator/nes_triangle_oscillator.h
    plaits/dsp/oscillator/oscillator.h
    plaits/dsp/oscillator/sine_oscillator.h
    plaits/dsp/oscillator/string_synth_oscillator.h
    plaits/dsp/oscillator/super_square_oscillator.h
    plaits/dsp/oscillator/variable_saw_oscillator.h
    plaits/dsp/oscillator/variable_shape_oscillator.h
    plaits/dsp/oscillator/vosim_oscillator.h
    plaits/dsp/oscillator/wavetable_oscillator.h
    plaits/dsp/oscillator/z_oscillator.h
    plaits/dsp/physical_modelling/delay_line.h
    plaits/dsp/physical_modelling/modal_voice.cc
    plaits/dsp/physical_modelling/modal_voice.h
    plaits/dsp/physical_modelling/resonator.cc
    plaits/dsp/physical_modelling/resonator.h
    plaits/dsp/physical_modelling/string.cc
    plaits/dsp/physical_modelling/string.h
    plaits/dsp/physical_modelling/string_voice.cc
    plaits/dsp/physical_modelling/string_voice.h
    plaits/dsp/speech/lpc_speech_synth.cc
    plaits/dsp/speech/lpc_speech_synth.h
    plaits/dsp/speech/lpc_speech_synth_controller.cc
    plaits/dsp/speech/lpc_speech_synth_controller.h
    plaits/dsp/speech/lpc_speech_synth_phonemes.cc
    plaits/dsp/speech/lpc_speech_synth_words.cc
    plaits/dsp/speech/lpc_speech_synth_words.h
    plaits/dsp/speech/naive_speech_synth.cc
    plaits/dsp/speech/naive_speech_synth.h
    plaits/dsp/speech/sam_speech_synth.cc
    plaits/dsp/speech/sam_speech_synth.h
    plaits/dsp/voice.cc
    plaits/dsp/voice.h
    plaits/resources.cc
    plaits/resources.h
    plaits/user_data.h
"
# Paths in stmlib, vendored under vendor/plaits/stmlib/.
STMLIB_FILES="
    LICENSE
    dsp/cosine_oscillator.h
    dsp/dsp.h
    dsp/filter.h
    dsp/hysteresis_quantizer.h
    dsp/limiter.h
    dsp/parameter_interpolator.h
    dsp/polyblep.h
    dsp/rsqrt.h
    dsp/units.cc
    dsp/units.h
    stmlib.h
    system/flash_programming.h
    utils/buffer_allocator.h
    utils/dsp.h
    utils/random.cc
    utils/random.h
"

ROOT=$(cd "$(dirname "$0")/.." && pwd)
DEST="$ROOT/vendor/plaits"
SUMS="$DEST/SHA256SUMS"

sha256() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1
    else shasum -a 256 "$1" | cut -d' ' -f1; fi
}

listed() {
    for f in $EURORACK_FILES; do echo "eurorack/$f"; done
    for f in $STMLIB_FILES; do echo "stmlib/$f"; done
}

verify() {
    status=0
    # Every listed file must exist with the recorded hash...
    while read -r want path; do
        [ -n "$want" ] || continue
        if [ ! -f "$DEST/$path" ]; then
            echo "MISSING $path"; status=1; continue
        fi
        got=$(sha256 "$DEST/$path")
        if [ "$got" = "$want" ]; then echo "OK      $path"
        else echo "CHANGED $path ($got, want $want)"; status=1; fi
    done < "$SUMS"
    # ...nothing else may be vendored under its paths...
    for f in $(cd "$DEST" && find eurorack stmlib -type f | LC_ALL=C sort); do
        if ! awk -v p="$f" '$2 == p { found = 1 } END { exit !found }' "$SUMS"; then
            echo "UNLISTED $f"; status=1
        fi
    done
    # ...and every file in the lists has a hash.
    for f in $(listed); do
        if ! awk -v p="$f" '$2 == p { found = 1 } END { exit !found }' "$SUMS"; then
            echo "NO HASH  $f (listed but not in SHA256SUMS)"; status=1
        fi
    done
    if [ $status -eq 0 ]; then echo "Plaits files match eurorack $EURORACK_COMMIT and stmlib $STMLIB_COMMIT"; fi
    return $status
}

# One upstream repository at one commit, sparse and blob-less, in a scratch
# folder. Clean folders turn git's lazy fetching off (CONTRIBUTING.md); it
# is turned back on for these scratch clones of upstream only, command by
# command, never exported, so this repository's own commands never fetch.
checkout() { # url commit dir files...
    url=$1 commit=$2 dir=$3; shift 3
    git -C "$dir" init -q
    git -C "$dir" remote add origin "$url"
    git -C "$dir" fetch -q --depth 1 --filter=blob:none origin "$commit"
    # shellcheck disable=SC2046
    git -C "$dir" sparse-checkout set --no-cone $(for f in "$@"; do printf '/%s ' "$f"; done)
    GIT_NO_LAZY_FETCH=0 git -C "$dir" -c advice.detachedHead=false checkout -q FETCH_HEAD
    got=$(git -C "$dir" rev-parse HEAD)
    [ "$got" = "$commit" ] || { echo "fetched $got from $url, want $commit"; exit 1; }
}

fetch() {
    work=$(mktemp -d)
    trap 'rm -rf "$work"' EXIT
    mkdir "$work/eurorack" "$work/stmlib"
    # shellcheck disable=SC2086
    checkout "$EURORACK_URL" "$EURORACK_COMMIT" "$work/eurorack" $EURORACK_FILES
    pin=$(git -C "$work/eurorack" ls-tree HEAD stmlib | awk '$2 == "commit" { print $3 }')
    [ "$pin" = "$STMLIB_COMMIT" ] || { echo "eurorack pins stmlib at $pin, want $STMLIB_COMMIT"; exit 1; }
    # shellcheck disable=SC2086
    checkout "$STMLIB_URL" "$STMLIB_COMMIT" "$work/stmlib" $STMLIB_FILES
    rm -rf "$DEST/eurorack" "$DEST/stmlib"
    for f in $(listed); do
        mkdir -p "$DEST/$(dirname "$f")"
        cp "$work/$f" "$DEST/$f"
    done
    verify
}

case "${1:---verify}" in
    --verify) verify ;;
    --fetch) fetch ;;
    *) echo "usage: $0 [--verify|--fetch]" >&2; exit 2 ;;
esac
