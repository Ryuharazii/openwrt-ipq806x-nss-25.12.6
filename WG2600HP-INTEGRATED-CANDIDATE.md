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

## 2026-11-01: selected G2 blocker addressed by isolated 760-12 candidate

- `qca8k_port_set_pvid()` now snapshots egress and VLAN CTRL0 registers and attempts restoration if either write fails.
- `qca8k_tag_8021q_vlan_add()` snapshots previous per-port VTU membership and VLAN egress mode, restores software PVID and attempts membership restoration on error (preserves prior existing VLAN entry).
- This is **best-effort rollback**, NOT atomic hardware transaction. MDIO failure may also prevent recovery. HW fault injection, ARM compile and runtime remain untested. G2 and G3 must not be upgraded on source proof.

## Verified CI source chain after 760-12

[GitHub Actions #41277303359](https://github.com/Ryuharazii/openwrt-ipq806x-nss-25.12.6/actions/runs/41277303359): full upstream 6.12.112 kernel unpack, all **594** active OpenWrt patches applied, DSA tag ID 29/30 unique, new rollback code found, assembly guard PASS. This is not a kernel compile, fault injection, or hardware safety proof. G1/G2 incomplete; G3 FAIL.

## 2026-11-01 ABI/compiler gate for 760-12

The isolated optional `--arm-objects` mode applies the exact sha256-pinned
Linux 6.12.112 archive + all 594 OpenWrt patches, configures multi_v7 ARM,
enables DSA/QCA8K/QCA8021Q, and compiles **only** 4 real ARM object files
(tag_qca_8021q, tag_8021q, qca8k-common, qca8k-8xxx). Checks ELF machine ARM.
It never creates a WG2600HP firmware, modifies hardware, or declares G3 PASS.

A newly added CI workflow will attempt this on the integrated isolated branch.
Prior to its actual run result, ARM compilation remains UNKNOWN.

## 2026-11-01 — compiled ARM objects PASS, add failure-model test

- Actual [Actions #41279538678](https://github.com/Ryuharazii/openwrt-ipq806x-nss-25.12.6/actions/runs/41279538678), verified completed/success. Linux6.12.112 + all594 patches compiled four real ARM ELF objects: tag_qca_8021q.o 5340B, tag_8021q.o 9024B, qca8k-common.o 21220B, qca8k-8xxx.o 33700B. No firmware linking or RAM boot.
- Separate stubbed register/VTU C harness compiles actual extracted patched qca8k C function bodies and injects failures at first and second PVID writes, new/existing VLAN registration, partial VTU add and rollback failure. Model is **not actual switch fault injection**; it only validates deterministic code-level behavior and demonstrates rollback can fail. Newly added; CI not yet confirmed.

## Validated ARM compiler and mocked C fault-injection evidence

- CI [#41279782972](https://github.com/Ryuharazii/openwrt-ipq806x-nss-25.12.6/actions/runs/41279782972) PASS at `5cde09a756e5f1eb5a33e6e860c84f0dec6d27a7`: all 594 patches applied to pinned Linux6.12.112, four real ARM DSA objects built and verified as ARM ELF, and eight modeled failure/success cases using original patched C functions pass. This **does not** prove hardware rollback or full firmware integration.
- G1 incomplete; G2 static/ARM/modeled coverage improved, hardware/unwind/offload not closed; G3 FAIL. Do not flash.

## ECM build-specific finding and source correction (2026-11-01)

The active OpenWrt ECM patch directory already contains 760-04/05; old
`scripts/wg2600hp_ecm_pinned_preflight.sh` appended both staged files
again, causing guaranteed duplicate application. Fixed to compare stage
with package and apply all 11 package patches exactly once.

The only automatic integrated CI now targets ECM ARM compilation; prior
ARM DSA and source-assembly tests are manual to avoid repeating completed
work. This does not generate or flash any firmware. ECM compilation result
must be taken from CI logs; no assumption of PASS.
