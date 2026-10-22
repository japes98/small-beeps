# syntax=docker/dockerfile:1.10@sha256:865e5dd094beca432e8c0a1d5e1c465db5f998dca4e439981029b3b81fb39ed5
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 japes98
#
# Build container: Debian bookworm-slim (amd64, pinned by digest), packages
# from a pinned snapshot.debian.org date, and JieLi's toolchain downloaded
# and checked against the SHA-256 recorded in docs/TOOLCHAIN.md.
# The toolchain is never committed or published; it only exists inside
# locally built images.

ARG BASE=debian:bookworm-slim@sha256:ec31d744f83f4a73447ba045aaab9409997efe5cc706eca4890c1be36cc1606a

FROM --platform=linux/amd64 ${BASE} AS fetch
ARG SNAPSHOT=20261020T000000Z
ARG TOOLCHAIN_NAME=jieli-linux-toolchains-20250324.1
ARG TOOLCHAIN_URL=https://jl-update.oss-cn-shenzhen.aliyuncs.com/jieli-linux-toolchains-20250324.1.tar.xz
ARG TOOLCHAIN_SHA256=f686586bcfb45e0f0bb27fd2b39c7a7f313cb4f0e88a66a14da621ffa8225958
RUN rm -f /etc/apt/sources.list.d/debian.sources \
 && echo "deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/${SNAPSHOT} bookworm main" > /etc/apt/sources.list \
 && apt-get -o Acquire::Retries=5 update \
 && apt-get install -y --no-install-recommends ca-certificates curl xz-utils \
 && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL --retry 5 --retry-all-errors --connect-timeout 60 -o /tmp/toolchain.tar.xz "${TOOLCHAIN_URL}" \
 && echo "${TOOLCHAIN_SHA256}  /tmp/toolchain.tar.xz" | sha256sum -c - \
 && mkdir -p /opt \
 && tar -xJf /tmp/toolchain.tar.xz -C /opt \
      "${TOOLCHAIN_NAME}/common" "${TOOLCHAIN_NAME}/pi32v2" \
 && mv "/opt/${TOOLCHAIN_NAME}" /opt/jieli \
 && rm /tmp/toolchain.tar.xz

FROM --platform=linux/amd64 ${BASE}
ARG SNAPSHOT=20261020T000000Z
RUN rm -f /etc/apt/sources.list.d/debian.sources \
 && echo "deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/${SNAPSHOT} bookworm main" > /etc/apt/sources.list \
 && apt-get -o Acquire::Retries=5 update \
 && apt-get install -y --no-install-recommends libstdc++6 zlib1g libtinfo6 \
 && rm -rf /var/lib/apt/lists/*
COPY --from=fetch /opt/jieli /opt/jieli
ENV PATH=/opt/jieli/pi32v2/bin:/opt/jieli/common/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    SOURCE_DATE_EPOCH=1767225600 \
    LC_ALL=C.UTF-8 \
    TZ=UTC
WORKDIR /src
