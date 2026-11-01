#!/usr/bin/env python3
"""Host-only exact Linux v6.12.112 QCA8K/DSA isolated patch-chain gate.

Checks upstream files, 611-01 backport and stock 711/712 patches, then
staged 760-01/02/03/06/08/09/10/11. Not an OpenWrt full-patch-tree check,
a kernel compile, boot test, or NSS hardware proof.
"""
from pathlib import Path
import hashlib
import difflib
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
    "net/dsa/tag_brcm.c": "df0ab8215b8101fa781557c97af18aa12e8dcf66",
    "drivers/net/dsa/qca/qca8k.h": "2e4092f816f9752c5befc020812eb6eaf3825ead",
    "drivers/net/dsa/qca/qca8k-8xxx.c": "a0bb836805c6e98786771e0d303fb5c51a1385fa",
    "drivers/net/dsa/qca/qca8k-common.c": "560c74c4ac3dd44ec1f0a0967a39d61e12f2f66b",
}
PATCHES = (
    "target/linux/generic/backport-6.12/611-01-v6.17-net-dsa-tag_brcm-add-support-for-legacy-FCS-tags.patch",
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
        # Strict gate. GNU patch failures are checked via git apply in a
        # TEMPORARY source only to diagnose downstream patches. Never PASS.
        strict_failures = []
        for relative in PATCHES:
            patch_file = ROOT / relative
            if not patch_file.is_file():
                print(f"DSA_PATCH=FAIL missing {relative}", flush=True)
                return 12
            cmd = ["patch", "--directory", str(scratch), "-p1", "--batch",
                   "--forward", "--fuzz=0", "--input", str(patch_file)]
            dry = subprocess.run(cmd + ["--dry-run"],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, check=False)
            if dry.returncode == 0:
                actual = subprocess.run(cmd, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True,
                                        check=False)
                if actual.returncode:
                    print(f"DSA_PATCH=FAIL actual-apply {relative}", flush=True)
                    print(actual.stdout[-3500:], flush=True)
                    return 21
                print(f"DSA_PATCH=PASS {relative}", flush=True)
                continue
            print(f"DSA_PATCH=GNU_F0_FAIL {relative}", flush=True)
            print(dry.stdout[-1000:], flush=True)
            strict_failures.append(relative)
            targets = list(dict.fromkeys(
                line[6:] for line in patch_file.read_text(encoding="utf-8").splitlines()
                if line.startswith("+++ b/")))
            originals = {
                path: ((scratch / path).read_bytes() if (scratch / path).exists() else None)
                for path in targets
            }
            check = subprocess.run(
                ["git", "-C", str(scratch), "apply", "--check", "-p1", str(patch_file)],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
            if check.returncode:
                print(f"DSA_GIT_APPLY=FAIL {relative}", flush=True)
                print(check.stdout[-3000:], flush=True)
                return 21
            actual = subprocess.run(
                ["git", "-C", str(scratch), "apply", "-p1", str(patch_file)],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
            if actual.returncode:
                print(f"DSA_GIT_APPLY=FAIL actual {relative}", flush=True)
                print(actual.stdout[-3000:], flush=True)
                return 21
            print(f"DSA_GIT_APPLY=PASS diagnostic-only {relative}", flush=True)
            canonical = ""
            for path, before in originals.items():
                after = (scratch / path).read_text(encoding="utf-8").splitlines(keepends=True)
                old = before.decode("utf-8").splitlines(keepends=True) if before is not None else []
                if old != after:
                    canonical += "".join(difflib.unified_diff(
                        old, after,
                        fromfile="a/" + path if before is not None else "/dev/null",
                        tofile="b/" + path, n=3))
            with tempfile.TemporaryDirectory(prefix="wg2600hp-regenerated-") as old_dir:
                base = Path(old_dir)
                for path, data in originals.items():
                    if data is not None:
                        dst = base / path
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        dst.write_bytes(data)
                diff_file = base / "regenerated.patch"
                diff_file.write_text(canonical, encoding="utf-8")
                d = subprocess.run(
                    ["patch", "--directory", str(base), "-p1", "--batch", "--forward",
                     "--dry-run", "--fuzz=0", "--input", str(diff_file)],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                    check=False)
            print(f"DSA_CANONICAL_F0={'PASS' if d.returncode == 0 else 'FAIL'} {relative}", flush=True)
            if d.returncode:
                print(d.stdout[-1200:], flush=True)
            else:
                print(f"DSA_CANONICAL_PATCH_BEGIN {relative}", flush=True)
                print(canonical.rstrip("\n"), flush=True)
                print(f"DSA_CANONICAL_PATCH_END {relative}", flush=True)
        if strict_failures:
            print(f"DSA_PATCH_CHAIN=FAIL strict_fuzz0_failures={len(strict_failures)}", flush=True)
            for name in strict_failures:
                print(f"DSA_REQUIRED_FIX={name}", flush=True)
            print("DSA_SCOPE=DIAGNOSTIC_GIT_FALLBACK_ONLY NO_BUILD NO_BOOT NO_NSS_ACK", flush=True)
            return 21
        defs = re.findall(
            r"(?m)^#define\s+DSA_TAG_PROTO_([A-Z0-9_]+)_VALUE\s+(\d+)\s*$",
            (scratch / "include/net/dsa.h").read_text(encoding="utf-8"))
        numeric = {}
        for name, number in defs:
            numeric.setdefault(int(number), []).append(name)
        if any(len(names) != 1 for names in numeric.values()) or numeric.get(29) != ["BRCM_LEGACY_FCS"] or numeric.get(30) != ["QCA_8021Q"]:
            print(f"DSA_SELECTED_PROTOCOL_IDS=FAIL {numeric}", flush=True)
            return 26
        print("DSA_SELECTED_PROTOCOL_IDS=PASS ID29=BRCM_LEGACY_FCS ID30=QCA_8021Q", flush=True)
        print("DSA_PATCH_CHAIN=PASS 8 verified upstream source files, 13 patch steps", flush=True)
        print("DSA_SCOPE=SELECTED_SUBSET_ONLY NO_OPENWRT_FULL_PATCHSET NO_COMPILE NO_BOOT NO_NSS_ACK", flush=True)
        return 0

if __name__ == "__main__":
    sys.exit(run())
