# RigSherpa Image Build System

Build flashable SD card / NVMe images for each supported vehicle using
[CustomPiOS](https://github.com/guysoft/CustomPiOS) on top of Raspberry Pi OS
Lite (arm64, bookworm).

## Prerequisites

- Docker (recommended) **or** Debian/Ubuntu x86_64 host with `qemu-user-static`
- GPG key pair for image & knowledge-pack signing
- Cloudflare R2 credentials (for upload)

## Quick Start

```bash
# 1.  Clone CustomPiOS (one-time)
cd build && git clone https://github.com/guysoft/CustomPiOS.git

# 2.  Build an image for one vehicle
./build-image.sh fzj80          # produces build/output/rigsherpa-fzj80-<version>.img.gz

# 3.  Sign + checksum
./sign-release.sh build/output/rigsherpa-fzj80-*.img.gz

# 4.  Upload to R2
./upload-release.sh build/output/rigsherpa-fzj80-*
```

## Directory Layout

```
build/
├── README.md              ← you are here
├── build-image.sh         ← top-level build driver
├── sign-release.sh        ← GPG sign + SHA256
├── upload-release.sh      ← push to Cloudflare R2
├── config                 ← build-time variables per vehicle
│   ├── base.conf          ← shared defaults
│   └── fzj80.conf         ← FZJ80-specific overrides
├── modules/
│   └── rigsherpa/          ← CustomPiOS module
│       ├── config         ← module config (variables)
│       ├── filesystem/    ← files copied verbatim into the image
│       └── chroot_script  ← runs inside the image at build time
└── output/                ← build artifacts land here
```

## Adding a New Vehicle

1. Author `config/vehicles/<type>.yaml` (specs, common issues, mods)
2. Author `config/vehicles/<type>_keywords.yaml` (RAG routing keywords)
3. Build the knowledge pack: `tools/kb_builder/build_pack.sh <type>`
4. Add `build/config/<type>.conf` with `VEHICLE_TYPE=<type>`
5. Run `./build-image.sh <type>`
