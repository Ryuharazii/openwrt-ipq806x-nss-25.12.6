"""Positive and negative regression tests for WG2600HP source cross-audit."""
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parent.parent
FILES = (
    "scripts/wg2600hp_cross_audit.py",
    "scripts/wg2600hp_verify_embedded_dtb.py",
    "scripts/wg2600hp_nss_image_gate.sh",
    "target/linux/ipq806x/files-6.12/arch/arm/boot/dts/qcom/qcom-ipq8064-wg2600hp.dts",
    "target/linux/ipq806x/base-files/etc/board.d/02_network",
    "target/linux/ipq806x/patches-6.12/990-0001-Add-required-entries-in-dts-files-for-NSS-support.patch",
    "package/qca-nss/qca-nss-gmac/patches/02-kernel-5.15-support.patch",
    "package/qca-nss/qca-nss-gmac/patches/09-dsa-conduit-device-tree-node.patch",
    "target/linux/ipq806x/image/generic.mk",
    "diff-wg2600hp-nss",
    "package/kernel/mac80211/Makefile",
    "package/kernel/mac80211/patches/subsys/990-mac80211-add-nss-redirect-support.patch",
    "target/linux/ipq806x/base-files/usr/sbin/wg2600hp-net-audit",
)


class CrossAuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="wg2600hp-cross-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for path in FILES:
            dest = self.root / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / path, dest)

    def run_audit(self):
        return subprocess.run(
            [sys.executable, str(self.root / "scripts/wg2600hp_cross_audit.py")],
            cwd=self.root, text=True, capture_output=True, check=False
        )

    def mutate(self, path, before, after):
        filename = self.root / path
        original = filename.read_text(encoding="utf-8")
        self.assertIn(before, original)
        filename.write_text(original.replace(before, after, 1), encoding="utf-8")

    def test_current_source_passes(self):
        result = self.run_audit()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("STATIC CROSS-AUDIT PASS", result.stdout)

    def test_detects_kernel_return_value_regression(self):
        path = self.root / "target/linux/ipq806x/patches-6.12/regression.patch"
        path.write_text(
            "--- a/net/core/of_net.c\n"
            "+++ b/net/core/of_net.c\n"
            "@@ -40,7 +40,7 @@ int of_get_phy_mode(struct device_node *np)\n"
            "-\t\treturn 0;\n+\t\treturn i;\n",
            encoding="utf-8"
        )
        result = self.run_audit()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FAIL Linux of_get_phy_mode return-value regression absent",
                      result.stdout)

    def test_detects_missing_wifi_nss_build_config_dependency(self):
        self.mutate(
            "package/kernel/mac80211/Makefile",
            "CONFIG_PACKAGE_MAC80211_NSS_SUPPORT",
            "CONFIG_PACKAGE_MAC80211_NSS_SUPPORT_REMOVED",
        )
        result = self.run_audit()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "FAIL mac80211 NSS option changes package configuration stamp",
            result.stdout,
        )

    def test_detects_missing_wifi_nss_redirect_patch(self):
        self.mutate(
            "package/kernel/mac80211/patches/subsys/990-mac80211-add-nss-redirect-support.patch",
            "nss_virt_if_create_sync",
            "nss_virtual_interface_missing",
        )
        result = self.run_audit()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "FAIL mac80211 NSS virtual-interface redirect remains patched",
            result.stdout,
        )

    def test_detects_wifi_nss_skb_fallback_missing_pull(self):
        self.mutate(
            "package/kernel/mac80211/patches/subsys/990-mac80211-add-nss-redirect-support.patch",
            "skb_pull(skb, ETH_HLEN);",
            "skb_pull_removed(skb, ETH_HLEN);",
        )
        result = self.run_audit()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "FAIL Wi-Fi NSS redirect preserves skb offset after TX rejection",
            result.stdout,
        )

    def test_detects_wifi_nss_skb_headroom_guard_missing(self):
        self.mutate(
            "package/kernel/mac80211/patches/subsys/990-mac80211-add-nss-redirect-support.patch",
            "skb_headroom(skb) < ETH_HLEN",
            "skb_headroom_unchecked(skb)",
        )
        result = self.run_audit()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "FAIL Wi-Fi NSS redirect preserves skb offset after TX rejection",
            result.stdout,
        )

    def test_detects_wrong_dsa_cpu_port_mode(self):
        self.mutate(
            "target/linux/ipq806x/files-6.12/arch/arm/boot/dts/qcom/qcom-ipq8064-wg2600hp.dts",
            'ethernet = <&gmac1>;\n\t\t\t\tphy-mode = "rgmii";',
            'ethernet = <&gmac1>;\n\t\t\t\tphy-mode = "sgmii";',
        )
        result = self.run_audit()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FAIL DSA CPU port 0 -> gmac1", result.stdout)

    def test_detects_wrong_wan_conduit(self):
        path = "target/linux/ipq806x/base-files/etc/board.d/02_network"
        filename = self.root / path
        content = filename.read_text(encoding="utf-8")
        start = content.index("\tnec,wg2600hp)\n")
        before, after = content[:start], content[start:]
        self.assertIn('ucidef_set_network_device_conduit "wan" "eth0"', after)
        filename.write_text(before + after.replace(
            'ucidef_set_network_device_conduit "wan" "eth0"',
            'ucidef_set_network_device_conduit "wan" "eth1"', 1), encoding="utf-8")
        result = self.run_audit()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FAIL Network wan -> eth0 conduit", result.stdout)

    def test_detects_bad_gmac_phy_address(self):
        path = "target/linux/ipq806x/patches-6.12/990-0001-Add-required-entries-in-dts-files-for-NSS-support.patch"
        filename = self.root / path
        patch = filename.read_text(encoding="utf-8")
        start = patch.index("+++ b/arch/arm/boot/dts/qcom/qcom-ipq8064-wg2600hp.dts")
        part, rest = patch[:start], patch[start:]
        updated, replacements = re.subn(
            r"(?m)^(\+\s*qcom,phy-mdio-addr = )<32>;",
            r"\g<1><4>;", rest, count=1
        )
        self.assertEqual(replacements, 1)
        filename.write_text(part + updated, encoding="utf-8")
        result = self.run_audit()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FAIL WG2600HP NSS GMAC x2 configured as no external MDIO PHY",
                      result.stdout)


if __name__ == "__main__":
    unittest.main()
