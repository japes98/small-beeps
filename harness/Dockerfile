# syntax=docker/dockerfile:1.10@sha256:865e5dd094beca432e8c0a1d5e1c465db5f998dca4e439981029b3b81fb39ed5
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
#
# The fwtest container (spec side). Built by harness/ci.sh from a context of
# exactly vendor/emulator/, harness/, LICENSE and NOTICE. Both bases are
# pinned by digest (PROVENANCE P-3, P-8); the build runs offline (no
# third-party crates), at a fixed path, with no incremental state, so the
# same source gives the same fwtest binary. Lints are capped: compiler
# warnings quote source lines, and CI logs (which the firmware side can
# read) must never show the emulator's source.
#
#   build    compiles fwtest
#   test     runs the harness's own tests (cargo test)
#   runtime  the published image: Debian slim, the binary, the licences

ARG RUST=rust:1.99.0-slim-bookworm@sha256:ba81bc3eaa4422af576c0262515d96b0111a628a6ccc2c86557cf55c9a4bbee0
ARG BASE=debian:bookworm-slim@sha256:ec31d744f83f4a73447ba045aaab9409997efe5cc706eca4890c1be36cc1606a

FROM --platform=linux/amd64 ${RUST} AS build
ENV CARGO_INCREMENTAL=0 \
    SOURCE_DATE_EPOCH=1767225600 \
    RUSTFLAGS="--remap-path-prefix=/src=. -C debuginfo=0 --cap-lints=allow" \
    LC_ALL=C.UTF-8 \
    TZ=UTC
WORKDIR /src
COPY vendor/emulator vendor/emulator
COPY harness harness
RUN --network=none cd harness && cargo build --release --locked --offline \
 && sha256sum target/release/fwtest

FROM build AS test
RUN --network=none cd harness && cargo test --release --locked --offline

FROM --platform=linux/amd64 ${BASE} AS runtime
COPY --from=build /src/harness/target/release/fwtest /usr/local/bin/fwtest
COPY LICENSE /usr/share/doc/fwtest/LICENSE
COPY NOTICE /usr/share/doc/fwtest/NOTICE
COPY vendor/emulator/LICENSE /usr/share/doc/fwtest/LICENSE.emulator
LABEL org.opencontainers.image.source="https://github.com/japes98/small-beeps" \
      org.opencontainers.image.description="Test runner." \
      org.opencontainers.image.licenses="MIT"
WORKDIR /work
USER 65534:65534
ENTRYPOINT ["/usr/local/bin/fwtest"]
