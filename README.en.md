# OpenWrt 25.12.6 with NSS for NEC WG2600HP

**Unofficial and experimental firmware.**

## Overview

- Device: NEC WG2600HP
- SoC: Qualcomm IPQ8064
- OpenWrt: 25.12.6
- Linux kernel: 6.12.112
- Custom build with Qualcomm NSS support

## Current Status

The firmware image was successfully built on Ubuntu
on November 4, 2026.

The device is currently running on hardware, and increasing NSS TUNIPIP6
counters for IPIP6 have been confirmed, as reported by the operator.
This does not establish full feature validation or long-term stability.

## Known Issues and Limitations

- Intermittent network connectivity issues have been observed during startup.
- Intermittent wired LAN disconnections during operation and temporary loss of the IPv4 default route remain unresolved known issues; their causes are unknown.
- TUNIPIP6 statistics patch 405 has been reviewed at source-code level only; its effect on hardware remains unverified (UNTESTED).
- Full feature validation is incomplete. Long-term stability is unverified (UNTESTED), and security testing is incomplete.

## Build Configuration

The device-specific configuration is available at:

configs/wg2600hp-public.config

## Credits

This project is based on existing OpenWrt NSS development work.

The original project information, contributors,
development history, and acknowledgments are preserved in
[README.nss-original.md](README.nss-original.md).

## Acknowledgements for the NEC Aterm work

Special thanks to **Karin (Karin-Laboratory)** for creating and publishing
[wg2600hp-openwrt-nss](https://github.com/Karin-Laboratory/wg2600hp-openwrt-nss)
to support WG2600HP NSS development. Their help has been an important part of
moving this effort forward.

### AI assistance

The NEC Aterm work has received assistance with development planning, research,
and documentation from:

- Choppie
- Kurorин

## Disclaimer

This firmware is not an official OpenWrt release.

Installing it may cause network failures or render
the device unbootable.

No warranty is provided regarding safety,
stability, performance, or functionality.

**Use at your own risk.**

## Documentation

- [Build instructions](BUILDING.md)
- [Known issues](KNOWN_ISSUES.md)

- [Test environment](TEST_ENVIRONMENT.md)
