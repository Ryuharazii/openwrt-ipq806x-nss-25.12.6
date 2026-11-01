# WG2600HP (IPQ8064) 25.12.6 — source-integrated candidate

**Isolation only. Not a finished firmware. Do not flash.**

- Kernel active patch directory: existing 760-01 and new 760-02/03/06/08/09/10/11 from previously audited isolation.
- ECM active patch directory: 760-04 and 760-05 after existing pinned 400/401 patches.
- CPU port0 → GMAC1 / WAN eth0; CPU port6 → GMAC2 / LAN eth1. Enable internal qca-8021q tagger on both; no user-facing VLAN changes.
- Kernel tagger QCA_8021Q enabled; QCA retained for other devices.
- Wi-Fi and TUNIPIP6 package selections unchanged.

Prior evidence: on the **audit branch**, fixed Linux 6.12.112 kernel tree accepted all 586 OpenWrt patches followed by staged 7 DSA patches, and pinned ECM accepted 9 OpenWrt + 2 staged. This commit assembles those files **into actual OpenWrt build input directories**. It is not an ARM compilation test.

**G1:** Old WG2600HP RAM build booted Linux, NSS cores, GMAC/DSA and passed WAN DHCP, LAN→WAN ICMP/HTTPS. Full BootROM/U-Boot transcript and new tagger boot not proven.
**G2:** Source patch application passed on prior isolated source; assembled source compilation and DSA VLAN failure rollback, split CPU behavior, MTU, IPIP6/Wi-Fi regression are not proven.
**G3: FAIL.** Block firmware build pending critical prebuild safety/compile decision. Do not upgrade CI to hardware PASS.

Known unresolved: 760-08/09 explicitly acknowledge switch VLAN partial hardware write rollback can fail. FW internal tag parser handling and NSS IPv4 CREATE/ACK not proven. User network configuration is not changed. No flash or automated firmware build.
