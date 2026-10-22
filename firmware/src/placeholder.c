/*
 * SPDX-License-Identifier: MIT
 * SPDX-FileCopyrightText: 2026 japes98
 *
 * Placeholder translation unit for M0a. It only proves the build pipeline
 * (pinned container, freestanding compile, link, byte-identical double
 * build). It is not firmware and is removed when M0d adds startup code.
 */

unsigned int placeholder(unsigned int x);

unsigned int placeholder(unsigned int x)
{
    return x * 3u + 1u;
}
