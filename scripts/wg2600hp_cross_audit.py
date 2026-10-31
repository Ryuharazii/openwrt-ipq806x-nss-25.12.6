#!/usr/bin/env python3
"""WG2600HP (IPQ8064) cross-component, source-level network preflight.

This is a *static* audit, not a substitute for hardware RAM-boot,
IPv4 reachability, or NSS/IPIP6 acceleration tests.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
CHECKS = []


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def check(label, condition):
    result = bool(condition)
    CHECKS.append((label, result))
    print(("PASS" if result else "FAIL") + " " + label)


def node(text, pattern):
    """Extract a DTS block while respecting nested child-node braces."""
    match = re.search(pattern + r"\s*\{", text, re.M)
    if not match:
        return ""
    start = match.end() - 1
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    return ""


def scalar(text, name):
    match = re.search(r"(?m)^\s*" + re.escape(name) + r"\s*=\s*<([^>]+)>;", text)
    return match.group(1).strip() if match else None


def main():
    dts = read("target/linux/ipq806x/files-6.12/arch/arm/boot/dts/qcom/qcom-ipq8064-wg2600hp.dts")
    net = read("target/linux/ipq806x/base-files/etc/board.d/02_network")
    gmac_patch = read("target/linux/ipq806x/patches-6.12/990-0001-Add-required-entries-in-dts-files-for-NSS-support.patch")
    gmac_api = read("package/qca-nss/qca-nss-gmac/patches/02-kernel-5.15-support.patch")
    dsa_conduit = read("package/qca-nss/qca-nss-gmac/patches/09-dsa-conduit-device-tree-node.patch")
    config = read("diff-wg2600hp-nss")
    image_gate = read("scripts/wg2600hp_nss_image_gate.sh")
    image_verifier = read("scripts/wg2600hp_verify_embedded_dtb.py")
    device = read("target/linux/ipq806x/image/generic.mk")

    # 1. Catch the Linux return-value contract regression before boot.
    patches = ROOT.glob("target/linux/ipq806x/patches-6.12/*.patch")
    bad_api_patches = []
    for path in patches:
        patch = path.read_text(encoding="utf-8")
        if re.search(r"(?m)^\+\s*return i;\s*$", patch) and "of_get_phy_mode" in patch:
            bad_api_patches.append(path.name)
    check("Linux of_get_phy_mode return-value regression absent", not bad_api_patches)
    check("NSS GMAC uses the two-argument PHY-mode API",
          "+\tof_get_phy_mode(np, &gmaccfg->phy_mii_type);" in gmac_api)
    check("NSS GMAC exposes OF node for DSA conduit matching",
          "+\tnetdev->dev.of_node = pdev->dev.of_node;" in dsa_conduit)

    # 2. Follow the entire CPU link: DSA port -> GMAC -> fixed link.
    mdio = node(dts, r"&mdio0")
    sw = node(mdio, r"switch@10")
    ports = node(sw, r"ports")
    check("MDIO includes QCA8337 DSA switch",
          'compatible = "qca,qca8337";' in sw and scalar(sw, "reg") == "0x10")
    cpu_links = {0: ("gmac1", "rgmii", "eth0"), 6: ("gmac2", "sgmii", "eth1")}
    for index, (gmac, mode, ifname) in cpu_links.items():
        cpu = node(ports, r"port@" + str(index))
        mac = node(dts, r"&" + gmac)
        fixed_cpu = node(cpu, r"fixed-link")
        fixed_mac = node(mac, r"fixed-link")
        check("DSA CPU port %d -> %s (%s), 1000/full fixed link" % (index, gmac, mode),
              bool(cpu) and 'label = "cpu";' in cpu
              and "ethernet = <&" + gmac + ">;" in cpu
              and 'phy-mode = "' + mode + '";' in cpu
              and scalar(fixed_cpu, "speed") == "1000"
              and "full-duplex;" in fixed_cpu
              and 'phy-mode = "' + mode + '";' in mac
              and scalar(mac, "qcom,id") == str(1 if index == 0 else 2)
              and scalar(fixed_mac, "speed") == "1000"
              and "full-duplex;" in fixed_mac)
    # GMAC ID is independent of the DSA switch port number.
    check("DTS GMAC ID 1/2", scalar(node(dts, r"&gmac1"), "qcom,id") == "1"
          and scalar(node(dts, r"&gmac2"), "qcom,id") == "2")

    # 3. Follow all five user ports to the internal switch PHYs.
    for index, role in ((1, "wan"), (2, "lan1"), (3, "lan2"),
                        (4, "lan3"), (5, "lan4")):
        p = node(ports, r"port@" + str(index))
        phy = node(node(sw, r"mdio"), r"phy_port" + str(index) + r":\s*phy@\d+")
        check("DSA port %d %s -> internal PHY %d" % (index, role, index - 1),
              scalar(p, "reg") == str(index)
              and 'label = "' + role + '";' in p
              and 'phy-mode = "internal";' in p
              and "phy-handle = <&phy_port" + str(index) + ">;" in p
              and scalar(phy, "reg") == str(index - 1))

    # 4. Compare *applied* WG2600HP DTS additions with NSS fixed-link contract.
    target = gmac_patch.split("+++ b/arch/arm/boot/dts/qcom/qcom-ipq8064-wg2600hp.dts", 1)
    target = target[1].split("--- a/", 1)[0] if len(target) == 2 else ""
    check("WG2600HP NSS GMAC x2 configured as no external MDIO PHY",
          len(re.findall(r"(?m)^\+\s*qcom,phy-mdio-addr\s*=\s*<32>;", target)) == 2)
    check("WG2600HP NSS GMAC link polling disabled",
          len(re.findall(r"(?m)^\+\s*qcom,poll-required\s*=\s*<0>;", target)) == 2)
    check("WG2600HP GMAC registers and interrupt resources explicitly defined",
          "+ \treg = <0x37200000 0x200000>;" in target
          and "+ \treg = <0x37400000 0x200000>;" in target
          and target.count('compatible = "qcom,nss-gmac"') == 2)

    # 5. Follow DSA user-port name -> board network -> physical conduit.
    board = re.search(r"(?ms)^\s*nec,wg2600hp\)\s*\n(.*?)^\s*;;", net)
    block = board.group(1) if board else ""
    check("WG2600HP network defines four LAN DSA ports and WAN",
          'ucidef_set_interfaces_lan_wan "lan1 lan2 lan3 lan4" "wan"' in block)
    for name, conduit in (("wan", "eth0"), ("lan1", "eth1"), ("lan2", "eth1"),
                          ("lan3", "eth1"), ("lan4", "eth1")):
        check("Network %s -> %s conduit" % (name, conduit),
              'ucidef_set_network_device_conduit "%s" "%s"' % (name, conduit) in block)

    # 6. Verify the next downstream dependencies are not forgotten.
    for option in ("CONFIG_TARGET_ipq806x_generic_DEVICE_nec_wg2600hp",
                   "CONFIG_TARGET_ROOTFS_INITRAMFS",
                   "CONFIG_PACKAGE_kmod-qca-nss-gmac",
                   "CONFIG_PACKAGE_kmod-qca-nss-drv",
                   "CONFIG_PACKAGE_kmod-qca-nss-ecm-standard",
                   "CONFIG_PACKAGE_kmod-qca-nss-drv-tunipip6",
                   "CONFIG_NSS_DRV_IPV6_ENABLE",
                   "CONFIG_NSS_DRV_TUNIPIP6_ENABLE"):
        check("Build selects " + option, option + "=y" in config.splitlines())
    device_block = device.split("define Device/nec_wg2600hp\n", 1)
    device_block = device_block[1].split("\nendef", 1)[0] if len(device_block) == 2 else ""
    check("Image recipe includes GMAC, NSS, ECM, TUNIPIP6",
          all(x in device_block for x in
              ("kmod-qca-nss-gmac", "kmod-qca-nss-drv",
               "kmod-qca-nss-ecm-standard", "kmod-qca-nss-drv-tunipip6")))
    check("Firmware gate inspects embedded *built* DTB",
          "wg2600hp_verify_embedded_dtb.py" in image_gate)
    check("Built DTB gate checks DSA CPU modes and conduits",
          "checks['DSA CPU port %d mode and conduit' % port]" in image_verifier
          and "((0, 1, b'rgmii\\0'), (6, 2, b'sgmii\\0'))" in image_verifier)

    failed = [label for label, ok in CHECKS if not ok]
    print("\nSTATIC CROSS-AUDIT %s (%d/%d)" %
          ("FAIL" if failed else "PASS", len(CHECKS) - len(failed), len(CHECKS)))
    print("UNVERIFIED: DSA probe success, Ethernet link, IPv4 forwarding, "
          "NSS offload and IPIP6 acceleration require an actual RAM boot.")
    return int(bool(failed))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as exc:
        print("FAIL source audit: %s" % exc, file=sys.stderr)
        sys.exit(1)
