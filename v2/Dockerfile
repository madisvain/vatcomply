# syntax=docker/dockerfile:1
# Multi-arch static binary. Build with BuildKit:
#   docker buildx build --platform linux/amd64,linux/arm64 -t vatcomply v2
#
# mimalloc is required. If the musl link fails, stop and ask; do not swap
# the allocator in this file.

FROM --platform=$BUILDPLATFORM rust:1.91.1-bookworm AS builder

ARG TARGETARCH
ARG ZIG_VERSION=0.14.1
ARG CARGO_ZIGBUILD_VERSION=0.23.4

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl pkg-config xz-utils \
    && rm -rf /var/lib/apt/lists/*

RUN set -eu; \
    case "$(dpkg --print-architecture)" in \
      amd64) zarch=x86_64 ;; \
      arm64) zarch=aarch64 ;; \
      *) echo "unsupported build arch"; exit 1 ;; \
    esac; \
    curl -fsSL "https://ziglang.org/download/${ZIG_VERSION}/zig-${zarch}-linux-${ZIG_VERSION}.tar.xz" -o /tmp/zig.tar.xz; \
    tar -C /opt -xJf /tmp/zig.tar.xz; \
    ln -s "/opt/zig-${zarch}-linux-${ZIG_VERSION}/zig" /usr/local/bin/zig; \
    rustup target add x86_64-unknown-linux-musl aarch64-unknown-linux-musl; \
    cargo install cargo-zigbuild --locked --version "${CARGO_ZIGBUILD_VERSION}"

WORKDIR /src
COPY . .
RUN set -eu; \
    case "${TARGETARCH:-amd64}" in \
      amd64) triple=x86_64-unknown-linux-musl ;; \
      arm64) triple=aarch64-unknown-linux-musl ;; \
      *) echo "unsupported TARGETARCH=${TARGETARCH}"; exit 1 ;; \
    esac; \
    cargo zigbuild --release --locked --target "${triple}"; \
    install -D "target/${triple}/release/vatcomply" /out/vatcomply

FROM scratch
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --from=builder /out/vatcomply /vatcomply
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    DATA_DIR=/data \
    PORT=8000 \
    BIND=0.0.0.0
USER 65532:65532
EXPOSE 8000
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD ["/vatcomply", "healthcheck"]
ENTRYPOINT ["/vatcomply"]
