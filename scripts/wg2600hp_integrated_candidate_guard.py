#!/usr/bin/env python3
"""WG2600HP IPQ8064: real assembled source input check; no kernel build."""
from pathlib import Path
import re
import sys
R = Path(__file__).resolve().parent.parent
K = (
"760-02-net-dsa-qca8k-8021q-driver-6.12-CANDIDATE.patch",
"760-03-net-dsa-8021q-dual-cpu-vlan-isolation-6.12.patch",
"760-06-net-dsa-8021q-register-error-cleanup-6.12-CANDIDATE.patch",
"760-08-net-dsa-8021q-prefix-unwind-6.12-CANDIDATE.patch",
"760-09-net-dsa-qca8k-bridge-join-unwind-6.12-CANDIDATE.patch",
"760-10-net-dsa-qca8021q-routed-cpu-bridge-vid-6.12-CANDIDATE.patch",
"760-11-net-dsa-qca8021q-vlan-aware-vid-guard-6.12-CANDIDATE.patch",
)
E = ("760-04-ecm-8021q-conduit-pinned-CANDIDATE.patch",
     "760-05-ecm-nss-vlan-dsa-guards-pinned-CANDIDATE.patch")
def ck(cond, message):
    if not cond: raise AssertionError(message)
    print("ASSEMBLED=PASS " + message)
def main():
    for n in K:
        stage = R/"backports/staging"/n
        build = R/"target/linux/generic/pending-6.12"/n
        ck(stage.is_file() and build.is_file() and stage.read_bytes()==build.read_bytes(), n)
    n="760-12-net-dsa-qca8k-vlan-rollback-CANDIDATE.patch"
    src=R/"backports/staging"/n
    dst=R/"target/linux/generic/pending-6.12"/n
    ck(src.is_file() and dst.is_file() and src.read_bytes()==dst.read_bytes(),
       "isolated PVID and VLAN rollback source candidate")
    for n in E:
        stage = R/"backports/staging"/n
        build = R/"package/qca-nss/qca-nss-ecm/patches"/n
        ck(stage.is_file() and build.is_file() and stage.read_bytes()==build.read_bytes(), n)
    cfg=(R/"target/linux/ipq806x/config-6.12").read_text()
    ck(cfg.count("CONFIG_NET_DSA_TAG_QCA_8021Q=y")==1 and
       cfg.count("CONFIG_NET_DSA_TAG_QCA=y")==1, "new tagger and legacy tagger")
    dts=(R/"target/linux/ipq806x/files-6.12/arch/arm/boot/dts/qcom/qcom-ipq8064-wg2600hp.dts").read_text()
    ck(dts.count('dsa-tag-protocol = "qca-8021q";')==2, "two CPU taggers")
    for cpu,gmac,mode in ((0,1,"rgmii"),(6,2,"sgmii")):
        m=re.search(rf"(?ms)^\s*port@{cpu}\s*\{{(.*?)^\s*\}};",dts)
        ck(bool(m) and f"ethernet = <&gmac{gmac}>;" in m.group(1) and
           f'phy-mode = "{mode}";' in m.group(1) and
           'dsa-tag-protocol = "qca-8021q";' in m.group(1) and
           "fixed-link" in m.group(1), f"CPU{cpu} GMAC{gmac} {mode} 1000/full link")
    board=(R/"target/linux/ipq806x/base-files/etc/board.d/02_network").read_text()
    ck('ucidef_set_network_device_conduit "wan" "eth0"' in board and
       'ucidef_set_network_device_conduit "lan1" "eth1"' in board, "board WAN/LAN unaltered")
    selected=(R/"diff-wg2600hp-nss").read_text()
    ck("CONFIG_NSS_DRV_WIFI_ENABLE=y" in selected and
       "CONFIG_NSS_DRV_TUNIPIP6_ENABLE=y" in selected, "Wi-Fi and IPIP6 selections retained")
    print("ASSEMBLY_SCOPE=NO_ARM_COMPILE NO_RAM_BOOT NO_NSS_CREATE_ACK")
if __name__=="__main__":
    try: main()
    except (AssertionError,OSError) as e:
        print("ASSEMBLED=FAIL",e);sys.exit(1)
