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

Successful compilation does not guarantee correct
operation of all features.

## Known Issues and Limitations

- NSS hardware offloading for IPIP6 tunnels is unverified.
- Intermittent network connectivity issues have been observed during startup.
- Long-term stability and security have not been fully evaluated.

## Build Configuration

The device-specific configuration is available at:

configs/wg2600hp.config

## Credits

This project is based on existing OpenWrt NSS development work.

The original project information, contributors,
development history, and acknowledgments are preserved in
[README.nss-original.md](README.nss-original.md).

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
