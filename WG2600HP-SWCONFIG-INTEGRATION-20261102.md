# WG2600HP / IPQ8064 / OpenWrt 25.12.6: swconfig integration

Base: Claude-managed `wg2600hp-swconfig-4729abc-build-20261101` commit `711b24a8352fb1184f6ec83f890c6bd9c8cd9887`.
This independent integration branch leaves the Claude source branch and the DSA branch untouched.

- Boot-to-network source cross-reference: WG2600HP DTS selects QCA8337 swconfig `qca,ar8327-initvals`, RGMII GMAC1 and SGMII GMAC2; board.d maps switch CPU0/eth0 to WAN physical port1 and CPU6/eth1 to LAN ports2–5. NSS device-tree common and GMAC nodes are separated in the source patch. TUNIPIP6 DT capability is present. OpenWrt 25.12.6 Linux 6.12.112 target remains unchanged. These statements refer to the source, not a new boot.
- The package source revisions of NSS GMAC, NSS driver, QCA MCS and NSS clients are kept unchanged; only their four mirror SHA256 values are made permanent, using the corrected values recorded in Claude's prior one-shot workflow. The download stage still **must** verify all four downloaded archive hashes: the corresponding claimed prior Actions run IDs were not independently accessible in this repository.
- No DSA patches, flash partitions, board switch configuration, network defaults or Wi-Fi/IPIP6 runtime code is modified.
- The earlier PR1 one-shot workflow checked out commit `4729abc6` and changed hashes only on the ephemeral CI runner, leaving the current branch unpinned. The integration workflow must compile the **integration branch's own checkout** and retain source revisions and image SHA256 in its artifact.
- Existing 25.12.5 NSS success and the 25.12.6 DSA RAM boot logs are **not** evidence of 25.12.6 swconfig boot or NSS acceleration. BootROM/U-Boot complete logs, swconfig hardware LAN/WAN test and Wi-Fi/fixed-IPIP6 NSS acceleration are **unverified**. No flash until RAM boot and complete tests.
- Rule 2 boot→communication review is **source-only** so far, not a hardware PASS. Rule 3 downstream runtime regression is **unverified**. The five execution gates cannot be declared passed merely from a successful compilation.
