# SARK Cross-Compilation Guide

**Document Version:** 1.0
**Last Updated:** 2026-02-01
**Audience:** Developers building SARK components for non-native platforms

---

## Overview

This guide covers cross-compiling SARK's Rust components for:

- **FreeBSD** (OPNsense/pfSense routers)
- **ARM64/aarch64** (Raspberry Pi, ARM servers)
- **ARM32/armv7** (Older ARM devices)
- **musl libc** (Alpine Linux, static binaries)
- **Windows** (x86_64-pc-windows-gnu)

---

## Prerequisites

### Install Rust and Cross-Compilation Tools

```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# Install cross (Docker-based cross-compilation)
cargo install cross

# Or install targets manually for native cross-compilation
rustup target add x86_64-unknown-freebsd
rustup target add aarch64-unknown-linux-gnu
rustup target add armv7-unknown-linux-gnueabihf
rustup target add x86_64-unknown-linux-musl
rustup target add x86_64-pc-windows-gnu
```

---

## Method 1: Using `cross` (Recommended)

The `cross` tool uses Docker containers with pre-configured toolchains.

### Setup

```bash
# Install cross
cargo install cross

# Verify Docker is running
docker ps
```

### Build Commands

```bash
cd /path/to/sark

# FreeBSD x86_64
cross build --release --target x86_64-unknown-freebsd -p sark-opa
cross build --release --target x86_64-unknown-freebsd -p sark-cache

# Linux ARM64 (Raspberry Pi 4, ARM servers)
cross build --release --target aarch64-unknown-linux-gnu -p sark-opa

# Linux ARM32 (Raspberry Pi 2/3, older ARM)
cross build --release --target armv7-unknown-linux-gnueabihf -p sark-opa

# Linux musl (static binary, Alpine compatible)
cross build --release --target x86_64-unknown-linux-musl -p sark-opa

# Windows
cross build --release --target x86_64-pc-windows-gnu -p sark-opa
```

### Output Location

```bash
# Binaries are in target/<triple>/release/
ls target/x86_64-unknown-freebsd/release/
# libsark_opa.so, libsark_cache.so

ls target/aarch64-unknown-linux-gnu/release/
# libsark_opa.so, libsark_cache.so
```

---

## Method 2: Native Cross-Compilation

For targets without `cross` support or when Docker isn't available.

### FreeBSD from Linux

```bash
# Install FreeBSD cross-compiler
# Ubuntu/Debian:
sudo apt-get install clang lld

# Add target
rustup target add x86_64-unknown-freebsd

# Create .cargo/config.toml
mkdir -p .cargo
cat > .cargo/config.toml << 'EOF'
[target.x86_64-unknown-freebsd]
linker = "clang"
rustflags = [
    "-C", "link-arg=-fuse-ld=lld",
    "-C", "link-arg=--target=x86_64-unknown-freebsd14.0",
    "-C", "link-arg=--sysroot=/path/to/freebsd-sysroot",
]
EOF

# Build
cargo build --release --target x86_64-unknown-freebsd -p sark-opa
```

#### Getting FreeBSD Sysroot

```bash
# Download FreeBSD base system
FREEBSD_VERSION=14.0
mkdir -p /opt/freebsd-sysroot
cd /opt/freebsd-sysroot

# Download and extract base.txz
fetch https://download.freebsd.org/releases/amd64/${FREEBSD_VERSION}-RELEASE/base.txz
tar xf base.txz ./lib ./usr/lib ./usr/include

# Set sysroot path in .cargo/config.toml
```

### ARM64 from x86_64 Linux

```bash
# Install ARM64 toolchain
# Ubuntu/Debian:
sudo apt-get install gcc-aarch64-linux-gnu

# Add target
rustup target add aarch64-unknown-linux-gnu

# Configure linker
cat >> .cargo/config.toml << 'EOF'
[target.aarch64-unknown-linux-gnu]
linker = "aarch64-linux-gnu-gcc"
EOF

# Build
cargo build --release --target aarch64-unknown-linux-gnu -p sark-opa
```

### ARM32 from x86_64 Linux

```bash
# Install ARM32 toolchain
sudo apt-get install gcc-arm-linux-gnueabihf

# Add target
rustup target add armv7-unknown-linux-gnueabihf

# Configure linker
cat >> .cargo/config.toml << 'EOF'
[target.armv7-unknown-linux-gnueabihf]
linker = "arm-linux-gnueabihf-gcc"
EOF

# Build
cargo build --release --target armv7-unknown-linux-gnueabihf -p sark-opa
```

### Static musl Binaries

```bash
# Install musl toolchain
sudo apt-get install musl-tools

# Add target
rustup target add x86_64-unknown-linux-musl

# Build (statically linked, no glibc dependency)
cargo build --release --target x86_64-unknown-linux-musl -p sark-opa

# Verify static linking
file target/x86_64-unknown-linux-musl/release/libsark_opa.so
# Should show "statically linked"
```

---

## Method 3: Docker-based Build Environment

For reproducible builds and CI/CD.

### Dockerfile for FreeBSD Target

```dockerfile
# Dockerfile.freebsd
FROM rust:1.92-bookworm

# Install cross-compilation tools
RUN apt-get update && apt-get install -y \
    clang \
    lld \
    curl \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Download FreeBSD sysroot
RUN mkdir -p /opt/freebsd-sysroot && \
    cd /opt/freebsd-sysroot && \
    curl -O https://download.freebsd.org/releases/amd64/14.0-RELEASE/base.txz && \
    tar xf base.txz ./lib ./usr/lib ./usr/include && \
    rm base.txz

# Add FreeBSD target
RUN rustup target add x86_64-unknown-freebsd

# Configure cargo
RUN mkdir -p /root/.cargo && \
    echo '[target.x86_64-unknown-freebsd]' >> /root/.cargo/config.toml && \
    echo 'linker = "clang"' >> /root/.cargo/config.toml && \
    echo 'rustflags = ["-C", "link-arg=-fuse-ld=lld", "-C", "link-arg=--target=x86_64-unknown-freebsd14.0", "-C", "link-arg=--sysroot=/opt/freebsd-sysroot"]' >> /root/.cargo/config.toml

WORKDIR /src
```

```bash
# Build and use
docker build -t sark-freebsd-builder -f Dockerfile.freebsd .
docker run -v $(pwd):/src sark-freebsd-builder \
    cargo build --release --target x86_64-unknown-freebsd -p sark-opa
```

### Dockerfile for ARM64 Target

```dockerfile
# Dockerfile.arm64
FROM rust:1.92-bookworm

RUN apt-get update && apt-get install -y \
    gcc-aarch64-linux-gnu \
    && rm -rf /var/lib/apt/lists/*

RUN rustup target add aarch64-unknown-linux-gnu

RUN mkdir -p /root/.cargo && \
    echo '[target.aarch64-unknown-linux-gnu]' >> /root/.cargo/config.toml && \
    echo 'linker = "aarch64-linux-gnu-gcc"' >> /root/.cargo/config.toml

WORKDIR /src
```

---

## PyO3/Maturin Cross-Compilation

For Python extension modules, use maturin with cross-compilation.

### Setup

```bash
pip install maturin

# For cross-compilation, also install:
pip install ziglang  # Zig provides cross-compilation toolchains
```

### Using Zig as Linker (Easiest)

```bash
# Install zig
pip install ziglang

# Build for Linux ARM64
maturin build --release --target aarch64-unknown-linux-gnu --zig

# Build for Linux musl
maturin build --release --target x86_64-unknown-linux-musl --zig
```

### Maturin with Docker

```bash
# Use maturin's Docker images for manylinux wheels
docker run --rm -v $(pwd):/io ghcr.io/pyo3/maturin \
    build --release --target aarch64-unknown-linux-gnu

# Output in target/wheels/
ls target/wheels/
# sark_rust-1.3.0-cp39-abi3-manylinux_2_28_aarch64.whl
```

### Cross-Compile for Specific Python Version

```bash
# Build for Python 3.11 on ARM64
maturin build --release \
    --target aarch64-unknown-linux-gnu \
    --interpreter python3.11 \
    --zig
```

---

## Platform-Specific Notes

### FreeBSD (OPNsense)

```bash
# OPNsense uses FreeBSD 14.x
# Target: x86_64-unknown-freebsd

# Required: Link against FreeBSD's libc
# The binary must be dynamically linked to work with FreeBSD's runtime

# Testing on OPNsense:
scp target/x86_64-unknown-freebsd/release/libsark_opa.so root@opnsense:/tmp/
ssh root@opnsense "cd /tmp && ./test_sark_opa"
```

### Raspberry Pi

```bash
# Pi 4/5 (64-bit): aarch64-unknown-linux-gnu
# Pi 2/3 (32-bit): armv7-unknown-linux-gnueabihf
# Pi Zero/1: arm-unknown-linux-gnueabihf (not commonly supported)

# For best compatibility, use musl:
cross build --release --target aarch64-unknown-linux-musl -p sark-opa
```

### Alpine Linux (musl)

```bash
# Alpine uses musl libc, not glibc
# Must compile with musl target

cross build --release --target x86_64-unknown-linux-musl -p sark-opa

# Or for ARM64 Alpine:
cross build --release --target aarch64-unknown-linux-musl -p sark-opa
```

### macOS (Apple Silicon)

```bash
# From Intel Mac to ARM Mac:
rustup target add aarch64-apple-darwin
cargo build --release --target aarch64-apple-darwin -p sark-opa

# From ARM Mac to Intel Mac:
rustup target add x86_64-apple-darwin
cargo build --release --target x86_64-apple-darwin -p sark-opa

# Universal binary (both architectures):
cargo build --release --target aarch64-apple-darwin -p sark-opa
cargo build --release --target x86_64-apple-darwin -p sark-opa
lipo -create \
    target/aarch64-apple-darwin/release/libsark_opa.dylib \
    target/x86_64-apple-darwin/release/libsark_opa.dylib \
    -output libsark_opa_universal.dylib
```

---

## Binary Size Optimization

Cross-compiled binaries can be optimized for size:

```toml
# Cargo.toml
[profile.release]
opt-level = "z"      # Optimize for size
lto = true           # Link-time optimization
codegen-units = 1    # Single codegen unit
strip = true         # Strip symbols
panic = "abort"      # Smaller panic handling
```

### Expected Sizes by Target

| Target | sark-opa | sark-cache | Combined |
|--------|----------|------------|----------|
| x86_64-linux-gnu | 320KB | 160KB | ~1.8MB |
| x86_64-linux-musl | 350KB | 180KB | ~2.0MB |
| x86_64-freebsd | 330KB | 170KB | ~1.9MB |
| aarch64-linux-gnu | 300KB | 150KB | ~1.7MB |
| armv7-linux-gnueabihf | 280KB | 140KB | ~1.6MB |

### Further Size Reduction

```bash
# Strip debug symbols (if not done by Cargo)
strip target/release/libsark_opa.so

# Compress with UPX (if available)
upx --best target/release/libsark_opa.so
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/cross-compile.yml
name: Cross-Compile

on:
  push:
    branches: [main]
  pull_request:

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        target:
          - x86_64-unknown-linux-gnu
          - x86_64-unknown-linux-musl
          - aarch64-unknown-linux-gnu
          - armv7-unknown-linux-gnueabihf

    steps:
      - uses: actions/checkout@v4

      - name: Install Rust
        uses: dtolnay/rust-toolchain@stable
        with:
          targets: ${{ matrix.target }}

      - name: Install cross
        run: cargo install cross

      - name: Build
        run: cross build --release --target ${{ matrix.target }} -p sark-opa -p sark-cache

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: sark-${{ matrix.target }}
          path: |
            target/${{ matrix.target }}/release/libsark_opa.*
            target/${{ matrix.target }}/release/libsark_cache.*

  build-freebsd:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build FreeBSD
        uses: vmactions/freebsd-vm@v1
        with:
          usesh: true
          prepare: |
            pkg install -y rust cargo
          run: |
            cargo build --release -p sark-opa -p sark-cache
            cp target/release/libsark_*.so /tmp/

      - name: Upload FreeBSD artifacts
        uses: actions/upload-artifact@v4
        with:
          name: sark-freebsd
          path: /tmp/libsark_*.so
```

### GitLab CI Example

```yaml
# .gitlab-ci.yml
stages:
  - build

.cross-compile:
  image: rust:1.92
  before_script:
    - cargo install cross
  script:
    - cross build --release --target $TARGET -p sark-opa -p sark-cache
  artifacts:
    paths:
      - target/$TARGET/release/libsark_*

build-linux-arm64:
  extends: .cross-compile
  variables:
    TARGET: aarch64-unknown-linux-gnu

build-linux-musl:
  extends: .cross-compile
  variables:
    TARGET: x86_64-unknown-linux-musl

build-freebsd:
  extends: .cross-compile
  variables:
    TARGET: x86_64-unknown-freebsd
```

---

## Troubleshooting

### "linking with cc failed"

```
error: linking with `cc` failed: exit status: 1
```

**Solution:** Install cross-compiler or configure linker in `.cargo/config.toml`:

```toml
[target.aarch64-unknown-linux-gnu]
linker = "aarch64-linux-gnu-gcc"
```

### "cannot find -lc" or "cannot find crt1.o"

**Solution:** Missing sysroot. For FreeBSD, download base.txz and extract.

### "undefined reference to `__stack_chk_fail`"

**Solution:** Stack protector mismatch. Try:

```toml
[target.x86_64-unknown-freebsd]
rustflags = ["-C", "target-feature=-crt-static"]
```

### PyO3 "Python.h not found"

**Solution:** For cross-compiling Python extensions, use maturin with `--zig` or Docker.

### Binary runs but crashes immediately

**Possible causes:**
1. Wrong libc version (glibc vs musl)
2. Missing shared libraries
3. Architecture mismatch (32-bit vs 64-bit)

**Debug:**
```bash
# Check binary info
file target/*/release/libsark_opa.so

# Check dependencies
ldd target/*/release/libsark_opa.so  # Linux
readelf -d target/*/release/libsark_opa.so

# On target system:
LD_DEBUG=libs ./your_binary
```

---

## Quick Reference

| Target | Command |
|--------|---------|
| FreeBSD x86_64 | `cross build --release --target x86_64-unknown-freebsd` |
| Linux ARM64 | `cross build --release --target aarch64-unknown-linux-gnu` |
| Linux ARM32 | `cross build --release --target armv7-unknown-linux-gnueabihf` |
| Linux musl | `cross build --release --target x86_64-unknown-linux-musl` |
| macOS ARM | `cargo build --release --target aarch64-apple-darwin` |
| Windows | `cross build --release --target x86_64-pc-windows-gnu` |

---

## See Also

- [Rust PyO3 Integration Guide](RUST_PYO3_INTEGRATION.md) - Building Python extensions
- [Embedded Deployment Guide](EMBEDDED_DEPLOYMENT.md) - Resource-constrained systems
- [Standalone Crates Guide](STANDALONE_CRATES.md) - Using components independently
- [cross documentation](https://github.com/cross-rs/cross) - Official cross docs
- [maturin documentation](https://www.maturin.rs/) - Python extension builds
- [Rust Platform Support](https://doc.rust-lang.org/nightly/rustc/platform-support.html) - All supported targets
