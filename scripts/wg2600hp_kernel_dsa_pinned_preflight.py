#!/usr/bin/env python3
"""Host-only exact Linux v6.12.112 QCA8K/DSA isolated patch-chain gate.

Checks the selected upstream files, stock OpenWrt 711/712 patches, then
staged 760-01/02/03/06/08/09/10/11. Not an OpenWrt full-patch-tree check,
a kernel compile, boot test, or NSS hardware proof.
"""
from pathlib import Path
import hashlib
import subprocess
import sys
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://raw.githubusercontent.com/gregkh/linux/v6.12.112/"
UPSTREAM_BLOBS = {
    "include/net/dsa.h": "a1f730d9f01b82f7f04ca365d1a6b22a96bd3521",
    "net/dsa/Kconfig": "2dfe9063613feb3251f3ec9f96adc87d2e0cd47a",
    "net/dsa/Makefile": "555c07cfeb71285b1904bb5ffa0ec8702c1267f8",
    "net/dsa/tag_8021q.c": "53e03fd8071b4a27117d4cb0c1bdc0a103eeed92",
    "drivers/net/dsa/qca/qca8k.h": "2e4092f816f9752c5befc020812eb6eaf3825ead",
    "drivers/net/dsa/qca/qca8k-8xxx.c": "a0bb836805c6e98786771e0d303fb5c51a1385fa",
    "drivers/net/dsa/qca/qca8k-common.c": "560c74c4ac3dd44ec1f0a0967a39d61e12f2f66b",
}
PATCHES = (
    "target/linux/generic/pending-6.12/711-01-net-dsa-qca8k-implement-lag_fdb_add-del-ops.patch",
    "target/linux/generic/pending-6.12/711-02-net-dsa-qca8k-enable-flooding-to-both-CPU-port.patch",
    "target/linux/generic/pending-6.12/711-03-net-dsa-qca8k-add-support-for-port_change_master.patch",
    "target/linux/generic/pending-6.12/712-net-dsa-qca8k-enable-assisted-learning-on-CPU-port.patch",
    "target/linux/generic/pending-6.12/760-01-net-dsa-qca8k-8021q-tagger-stage.patch",
    "backports/staging/760-02-net-dsa-qca8k-8021q-driver-6.12-CANDIDATE.patch",
    "backports/staging/760-03-net-dsa-8021q-dual-cpu-vlan-isolation-6.12.patch",
    "backports/staging/760-06-net-dsa-8021q-register-error-cleanup-6.12-CANDIDATE.patch",
    "backports/staging/760-08-net-dsa-8021q-prefix-unwind-6.12-CANDIDATE.patch",
    "backports/staging/760-09-net-dsa-qca8k-bridge-join-unwind-6.12-CANDIDATE.patch",
    "backports/staging/760-10-net-dsa-qca8021q-routed-cpu-bridge-vid-6.12-CANDIDATE.patch",
    "backports/staging/760-11-net-dsa-qca8021q-vlan-aware-vid-guard-6.12-CANDIDATE.patch",
)

def git_blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def run():
    with tempfile.TemporaryDirectory(prefix="wg2600hp-linux-dsa-") as td:
        scratch = Path(td)
        for name, expected in UPSTREAM_BLOBS.items():
            url = BASE + name
            try:
                with urllib.request.urlopen(url, timeout=25) as response:
                    data = response.read()
            except Exception as exc:
                print(f"DSA_SOURCE_FETCH=BLOCKED {name}: {exc}", flush=True)
                return 20
            actual = git_blob_sha(data)
            if actual != expected:
                print(f"DSA_SOURCE_INTEGRITY=FAIL {name} expected={expected} actual={actual}", flush=True)
                return 13
            f = scratch / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(data)
            print(f"DSA_SOURCE=VERIFIED {name} git_blob={actual}", flush=True)
        for relative in PATCHES:
            patch_file = ROOT / relative
            if not patch_file.is_file():
                print(f"DSA_PATCH=FAIL missing {relative}", flush=True)
                return 12
            result = subprocess.run(
                ["patch", "--directory", str(scratch), "-p1", "--batch", "--forward",
                 "--fuzz=0", "--no-backup-if-mismatch", "--input", str(patch_file)],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False,
            )
            if result.returncode:
                print(f"DSA_PATCH=FAIL {relative}", flush=True)
                print(result.stdout[-6000:], flush=True)
                return 21
            print(f"DSA_PATCH=PASS {relative}", flush=True)
        print("DSA_PATCH_CHAIN=PASS 7 verified upstream source files, 12 patch steps", flush=True)
        print("DSA_SCOPE=SELECTED_SUBSET_ONLY NO_OPENWRT_FULL_PATCHSET NO_COMPILE NO_BOOT NO_NSS_ACK", flush=True)
        return 0

if __name__ == "__main__":
    sys.exit(run())
