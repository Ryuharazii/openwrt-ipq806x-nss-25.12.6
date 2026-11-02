# WG2600HP / IPQ8064 / OpenWrt 25.12.6: swconfig integration

Base: Claude-managed `wg2600hp-swconfig-4729abc-build-20261101` commit `711b24a8352fb1184f6ec83f890c6bd9c8cd9887`.
This independent integration branch leaves the Claude source branch and the DSA branch untouched.

- Boot-to-network source cross-reference: WG2600HP DTS selects QCA8337 swconfig `qca,ar8327-initvals`, RGMII GMAC1 and SGMII GMAC2; board.d maps switch CPU0/eth0 to WAN physical port1 and CPU6/eth1 to LAN ports2–5. NSS device-tree common and GMAC nodes are separated in the source patch. TUNIPIP6 DT capability is present. OpenWrt 25.12.6 Linux 6.12.112 target remains unchanged. These statements refer to the source, not a new boot.
- The package source revisions of NSS GMAC, NSS driver, QCA MCS and NSS clients are kept unchanged; only their four mirror SHA256 values are made permanent, using the corrected values recorded in Claude's prior one-shot workflow. The download stage still **must** verify all four downloaded archive hashes: the corresponding claimed prior Actions run IDs were not independently accessible in this repository.
- No DSA patches, flash partitions, board switch configuration, network defaults or Wi-Fi/IPIP6 runtime code is modified.
- The earlier PR1 one-shot workflow checked out commit `4729abc6` and changed hashes only on the ephemeral CI runner, leaving the current branch unpinned. The integration workflow must compile the **integration branch's own checkout** and retain source revisions and image SHA256 in its artifact.
- Existing 25.12.5 NSS success and the 25.12.6 DSA RAM boot logs are **not** evidence of 25.12.6 swconfig boot or NSS acceleration. BootROM/U-Boot complete logs, swconfig hardware LAN/WAN test and Wi-Fi/fixed-IPIP6 NSS acceleration are **unverified**. No flash until RAM boot and complete tests.
- Rule 2 boot→communication review is **source-only** so far, not a hardware PASS. Rule 3 downstream runtime regression is **unverified**. The five execution gates cannot be declared passed merely from a successful compilation.

## Wi-Fi NSS mac80211 rebuild dependency — isolated prebuild correction

Identified a missing dependency in the swconfig mac80211 package at `package/kernel/mac80211/Makefile`: the build enables `CONFIG_PACKAGE_MAC80211_NSS_SUPPORT=y` and the Makefile uses the flag to generate `MAC80211_NSS_SUPPORT`, but `PKG_CONFIG_DEPENDS` did not contain that flag. `include/package.mk` line 126 computes the configured build stamp from `PKG_CONFIG_DEPENDS`. Changing the NSS flag in an incremental build therefore might otherwise reuse a stale configured package.

Cross-component source path reviewed before this change: LegacyImage uImage+DTB→IPQ8064 DTS→MDIO AR8216 swconfig with two RGMII/SGMII GMAC links→`02_network` switch0 CPU0/eth0 WAN, CPU6/eth1 LAN→ECM NSS frontend and Wi-Fi redirect→TUNIPIP6 capability/driver/client. No runtime claim: router BootROM/U-Boot details and latest swconfig image, ECM NSS acceleration and tunnel FW ACK remain unverified. Shell/SSH unavailable after previous reboot logs, so G2 hardware evidence incomplete.

Single code edit: add `CONFIG_PACKAGE_MAC80211_NSS_SUPPORT` to `PKG_CONFIG_DEPENDS`; preserve other entries, upstream config switch, device DTS and whole network topology. Pre-commit checks compare the full original file with the one-line insertion, require the exact token, reject a negative `_REMOVED` mutation, and verify the downstream `MAC80211_NSS_SUPPORT` config selector is unchanged. Actual OpenWrt cross-build and regression on WG2600HP are NOT RUN, so do not mark G3/G4/G5 PASS. GitHub Actions remain manual and were not started.
