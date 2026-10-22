// SPDX-License-Identifier: MIT
// SPDX-FileCopyrightText: 2026 japes98
fn main() {
    fwtest::scrub_environment();
    let args: Vec<String> = std::env::args().skip(1).collect();
    std::process::exit(fwtest::main_with(&args));
}
