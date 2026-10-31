#!/usr/bin/env python3
"""Static regression guard for the WG2600HP isolated QCA8K candidate; no build/pass claim."""
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
p = (root / "backports/staging/760-02-net-dsa-qca8k-8021q-driver-6.12-CANDIDATE.patch").read_text()
dts = (root / "target/linux/ipq806x/files-6.12/arch/arm/boot/dts/qcom/qcom-ipq8064-wg2600hp.dts").read_text()
cfg = (root / "target/linux/ipq806x/config-6.12").read_text()
ecm = (root / "backports/staging/760-04-ecm-8021q-conduit-pinned-CANDIDATE.patch").read_text()
isolation = (root / "backports/staging/760-03-net-dsa-8021q-dual-cpu-vlan-isolation-6.12.patch").read_text()
reg_cleanup = (root / "backports/staging/760-06-net-dsa-8021q-register-error-cleanup-6.12-CANDIDATE.patch").read_text()
checks = []

def check(name, ok):
    checks.append((name, bool(ok)))
    print(("PASS" if ok else "FAIL") + ": " + name)

lines = p.splitlines()
hunk_re = re.compile(r"^@@ -(\d+),(\d+) \+(\d+),(\d+) @@")
file = None
delta = 0
count = 0
bad = []
for i, line in enumerate(lines):
    if line.startswith("--- a/"):
        file, delta = line[6:], 0
    m = hunk_re.match(line)
    if not m:
        continue
    old_start, old_count, new_start, new_count = map(int, m.groups())
    old_seen = new_seen = 0
    for follow in lines[i + 1:]:
        if follow.startswith(("@@ ", "--- a/", "--- /dev/null")) or not follow:
            break
        if follow[0] == " ":
            old_seen += 1
            new_seen += 1
        elif follow[0] == "-":
            old_seen += 1
        elif follow[0] == "+":
            new_seen += 1
        elif follow[0] != "\\":
            break
    if (old_count, new_count, new_start) != (old_seen, new_seen, old_start + delta):
        bad.append((i + 1, file, line))
    delta += new_seen - old_seen
    count += 1

check("28 patch hunks and offsets", count == 28 and not bad)
start = p.index("+static int qca8k_change_tag_protocol(")
end = p.index(" static void qca8k_setup_hol_fixup(", start)
switch = p[start:end]
qca_start = switch.index("+\tcase DSA_TAG_PROTO_QCA:")
tag_start = switch.index("+\tcase DSA_TAG_PROTO_QCA_8021Q:")
qca = switch[qca_start:tag_start]
tag = switch[tag_start:]
check("return to QCA restores CPU0 conduit",
      "qca8k_conduit_change(ds, dp->conduit," in qca and
      "netif_oper_up(dp->conduit)" in qca)
save = tag.find("saved_mgmt_conduit = priv->mgmt_conduit;")
clear = tag.find("priv->mgmt_conduit = NULL;")
disable = tag.find("qca8k_set_hdr_mode(priv, QCA8K_PORT_HDR_CTRL_NONE)")
check("save management before clearing and changing header",
      -1 < save < clear < disable)
check("header-disable failure unwinds",
      "if (ret)\n+\t\t\tgoto restore_hdr;" in tag[tag.find("qca8k_set_hdr_mode(priv, QCA8K_PORT_HDR_CTRL_NONE)"):])
check("partial VLAN enable failure unwinds VLAN before restoring headers",
      "ret = qca8k_set_tag_8021q_vlan_mode(priv, true);\n+\t\tif (ret)\n+\t\t\tgoto restore_vlan;" in tag)
check("both rollback failures logged",
      "QCA VLAN rollback failed" in tag and "QCA header rollback failed" in tag)
check("restored only after both VLAN and header rollback succeed under locks",
      "bool vlan_rollback_ok = true;" in switch and
      "vlan_rollback_ok = false;" in tag and
      "if (!rollback_ret && vlan_rollback_ok)\n+\t\tpriv->mgmt_conduit = saved_mgmt_conduit;" in tag and
      "mutex_lock(&priv->mgmt_eth_data.mutex)" in tag and
      "mutex_lock(&priv->mib_eth_data.mutex)" in tag)
check("QCA8337 CPU0/6 mappings",
      'compatible = "qca,qca8337"' in dts and
      bool(re.search(r"port@0\s*\{[^}]*ethernet = <&gmac1>", dts, re.S)) and
      bool(re.search(r"port@6\s*\{[^}]*ethernet = <&gmac2>", dts, re.S)))
check("two-CPU VLAN isolation staging", "dp == info->dp->cpu_dp" in isolation)
check("ECM mapped to assigned conduit", "return dp->cpu_dp->conduit;" in ecm)
check("registration failure unwinds partial tagger setup",
      "err_free:\n-\tkfree(ctx);\n+" in reg_cleanup and
      "+\tdsa_tag_8021q_unregister(ds);" in reg_cleanup and
      "+++ b/net/dsa/tag_8021q.c" in reg_cleanup)
check("8021Q not enabled in target", 
      "CONFIG_NET_DSA_TAG_QCA=y" in cfg and
      not re.search(r"^CONFIG_NET_DSA_TAG_QCA_8021Q=[ym]$", cfg, re.M))
failures = [name for name, ok in checks if not ok]
print(f"{len(checks) - len(failures)}/{len(checks)} static checks passed")
print("NOT TESTED: kernel apply, ARM build, reverse-switch failure recovery, RAM/IPv4/NSS")
sys.exit(1 if failures else 0)
