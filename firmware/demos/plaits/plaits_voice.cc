/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * The C++ side of the Plaits demo: holds Plaits voices and hands them our
 * parameters (plaits_voice.h). Each voice gets the 16 KiB buffer upstream's
 * own firmware gives its one voice. Modulations are left unpatched except
 * the trigger, which the keys drive, so Plaits' low-pass gate and
 * envelope shape each note as with a trigger cable patched.
 */

#include "plaits/dsp/voice.h"
#include "plaits_voice.h"

// Placement new, as <new> declares it: the slots are built in static
// storage at init, so there is no global constructor or destructor (the
// firmware runs none).
inline void *operator new(size_t, void *where) noexcept { return where; }

namespace {

const size_t kBuffer = 16384;

struct Slot {
    plaits::Voice voice;
    plaits::Patch patch;
    plaits::Modulations modulations;
    char buffer[kBuffer] __attribute__((aligned(8)));
};

char storage[PLAITS_VOICES][sizeof(Slot)] __attribute__((aligned(8)));

inline Slot &slot(unsigned v)
{
    return *reinterpret_cast<Slot *>(storage[v]);
}

}  // namespace

extern "C" void plaits_voice_init(unsigned v)
{
    Slot &s = *new (storage[v]) Slot;
    stmlib::BufferAllocator allocator(s.buffer, kBuffer);

    s.voice.Init(&allocator);
    s.patch.note = 48.0f;
    s.patch.harmonics = 0.5f;
    s.patch.timbre = 0.5f;
    s.patch.morph = 0.5f;
    s.patch.frequency_modulation_amount = 0.0f;
    s.patch.timbre_modulation_amount = 0.0f;
    s.patch.morph_modulation_amount = 0.0f;
    s.patch.engine = 0;
    s.patch.decay = 0.5f;
    s.patch.lpg_colour = 0.5f;
    s.modulations.engine = 0.0f;
    s.modulations.note = 0.0f;
    s.modulations.frequency = 0.0f;
    s.modulations.harmonics = 0.0f;
    s.modulations.timbre = 0.0f;
    s.modulations.morph = 0.0f;
    s.modulations.trigger = 0.0f;
    s.modulations.level = 0.0f;
    s.modulations.frequency_patched = false;
    s.modulations.timbre_patched = false;
    s.modulations.morph_patched = false;
    s.modulations.trigger_patched = true;
    s.modulations.level_patched = false;
}

extern "C" void plaits_voice_render(unsigned v, const struct plaits_params *p, short *out, unsigned frames)
{
    Slot &s = slot(v);

    s.patch.engine = p->engine;
    s.patch.note = p->note;
    s.patch.harmonics = p->harmonics;
    s.patch.timbre = p->timbre;
    s.patch.morph = p->morph;
    s.patch.decay = p->decay;
    s.patch.lpg_colour = p->lpg_colour;
    s.modulations.trigger = p->trigger ? 1.0f : 0.0f;
    // Voice::Frame is two shorts, out then aux: the layout out[] promises.
    s.voice.Render(s.patch, s.modulations, reinterpret_cast<plaits::Voice::Frame *>(out), frames);
}
