# OpenWrt 25.12.6 with NSS for NEC WG2600HP3

**Unofficial and experimental firmware.**

## Overview

- Device: NEC WG2600HP3
- SoC: Qualcomm IPQ8062
- OpenWrt: 25.12.6
- Linux kernel: 6.12.112
- Custom build with Qualcomm NSS support

## Current Status

The firmware image was successfully built on Ubuntu
on November 4, 2026.

The device was flashed with `sysupgrade` and tested on hardware, as reported
by the operator. This was not a RAM-boot test.
This does not establish full feature validation or long-term stability.

## Known Issues and Limitations

- NSS hardware offloading for IPIP6 tunnels on WG2600HP3 remains unverified (UNTESTED).
- Intermittent network connectivity issues have been observed during startup.
- Full feature validation is incomplete. Long-term stability is unverified (UNTESTED), and security testing is incomplete.

## Build Configuration

The device-specific configuration is available at:

configs/wg2600hp3-public.config

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
