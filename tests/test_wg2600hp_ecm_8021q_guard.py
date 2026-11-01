"""Host-only guard checks; these never prove runtime NSS acceleration or ARM compilation."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent.parent
ECM = ROOT / "backports/staging/760-04-ecm-8021q-conduit-pinned-CANDIDATE.patch"
TAG = ROOT / "backports/staging/760-11-net-dsa-qca8021q-vlan-aware-vid-guard-6.12-CANDIDATE.patch"
DUAL = ROOT / "backports/staging/760-03-net-dsa-8021q-dual-cpu-vlan-isolation-6.12.patch"
NET = ROOT / "target/linux/ipq806x/base-files/etc/board.d/02_network"

def added_c(patch):
    return "\n".join(line[1:] for line in patch.splitlines()
                     if line.startswith("+") and not line.startswith("+++"))

def helper(patch):
    src = added_c(patch)
    start = src.index("static struct net_device *ecm_interface_dsa_8021q_conduit(")
    return src[start:src.index("#else", start)]

def safe_vlan_aware_gate(patch):
    fn = helper(patch)
    bridge_guard = re.search(
        r"if \(dp->bridge\) \{\s*"
        r"struct net_device \*br = dsa_port_bridge_dev_get\(dp\);\s*"
        r"if \(!br \|\| br_vlan_enabled\(br\)\)\s*"
        r"return NULL;\s*\}",
        fn)
    return bool(bridge_guard
                and fn.find("!dp->ds->tag_8021q_ctx") < bridge_guard.start()
                and bridge_guard.end() < fn.index("if (vid) {"))

class EcmVlanGuardTest(unittest.TestCase):
    def setUp(self):
        self.ecm = ECM.read_text(encoding="utf-8")

    def test_8021q_dsa_vlan_aware_refused_before_vid_selection(self):
        self.assertTrue(safe_vlan_aware_gate(self.ecm))

    def test_removed_vlan_guard_is_detected(self):
        modified = self.ecm.replace("br_vlan_enabled(br)", "false")
        self.assertFalse(safe_vlan_aware_gate(modified))

    def test_unchecked_bridge_is_detected(self):
        modified = self.ecm.replace("if (!br || br_vlan_enabled(br))",
                                    "if (!br)")
        self.assertFalse(safe_vlan_aware_gate(modified))

    def test_dsa_tag_protocol_is_required(self):
        src = helper(self.ecm)
        self.assertIn("!dsa_user_dev_check(dev)", src)
        self.assertIn("!dp->ds->tag_8021q_ctx", src)
        self.assertIn("!dp->cpu_dp || !dp->cpu_dp->conduit", src)

    def test_real_vlan_aware_tagger_not_bridge_virtual_vid(self):
        tag = TAG.read_text(encoding="utf-8")
        self.assertIn("if (br && br_vlan_enabled(br))", tag)
        self.assertIn("br_vlan_get_pvid_rcu(netdev, &vid)", tag)
        self.assertIn("vid_is_dsa_8021q", tag)

    def test_two_cpu_paths_remain_separated(self):
        dual = DUAL.read_text(encoding="utf-8")
        net = NET.read_text(encoding="utf-8")
        self.assertIn("return dp == info->dp->cpu_dp;", dual)
        self.assertIn('ucidef_set_network_device_conduit "wan" "eth0"', net)
        self.assertIn('ucidef_set_network_device_conduit "lan1" "eth1"', net)

if __name__ == "__main__":
    unittest.main()
