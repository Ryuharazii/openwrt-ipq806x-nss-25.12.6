# WG2600HP DSA integration worktree — 2026-11-02

Base: 6582f1b8c15e7b024fac675a9bd5c11a831355d4

This branch applies the isolated DSA/ECM candidates to OpenWrt build inputs, without touching Claude's swconfig branch or the earlier isolated branch.

* Linux 6.12: the existing generic 760-01 tagger is retained; new 760-02/03/06/08/09/10 are installed in **ipq806x-only** kernel patches.
* ECM pinned 9acdcb05: candidate 760-04/05 are installed as 390-04/05, before the existing kernel 6.12 support patches 400/401.
* WG2600HP DTS CPU ports 0 and 6 select qca-8021q; ipq806x config adds NET_DSA_TAG_QCA_8021Q.
* The WG2600HP-specific diff config selects NSS_DRV_VLAN_ENABLE=y and kmod-qca-nss-drv-vlan-mgr=y; the VLAN Kconfig and client build definitions were restored on the source isolated branch.
* WAN→eth0 and LAN1–4→eth1 are unchanged. No UCI VLANs added.

**Verified here:** exact old-context matching for the 760-07 and 760-11 OpenWrt source hunks; staged patch file copies. This is *integration only*, not evidence that the 760-02/03/06/08/09/10 Linux and 390-04/05 ECM patches all apply without error.

**Not yet verified:** quilt kernel/ECM patch application; fixed pinned upstream ECM source compilation; NSS VLAN module and firmware compatibility; IPQ8064 DSA dual-CPU isolation; ARM build; RAM boot; IPv4 NSS flow creation; Wi-Fi NSS and fixed IPIP6 acceleration.

Do not flash. G1/G2 unresolved, G3 FAIL until all patch stack and API dependencies are resolved. No completed firmware.

## Kernel patch order: baseline source-context simulation

- The integrated Linux patch sequence tested against upstream Linux 6.12.112 was generic `711-01`, `711-02`, `711-03`, **`712`**, `760-01`, then ipq806x `760-02`, `760-03`, `760-06`, `760-08`, `760-09`, `760-10`. All **49** hunks matched and were transformed in memory using old/new unified-diff context. This is a source-context simulation, **not** the OpenWrt quilt/ARM build.
- A first simulation erroneously omitted existing `712`, incorrectly suggesting that `760-02` conflicted with `711-03`. Including `712` removes that false failure. Another snippet in `760-02` at qca8k-common.c old line 881 matched two nearby locations; this simulation selected the position nearest the declared old location. The real patch utility has not independently confirmed this placement.
- The ECM `390-04`/`390-05` patch stack has not been applied to the **exact** pinned ECM source together with `400`/`401`. No proof of kernel/ECM compile, NSS rule creation, firmware, RAM-boot or two-CPU datapath. G3 FAIL remains.
