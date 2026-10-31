#!/usr/bin/env python3
"""Check that the WG2600HP build reuses safe caches across GitHub runners."""
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parent.parent
yaml = (root / ".github/workflows/build-wg2600hp-nss.yml").read_text()
config = (root / "diff-wg2600hp-nss").read_text().splitlines()

checks = {
    "OpenWrt developer mode and ccache selected":
        "CONFIG_DEVEL=y" in config and "CONFIG_CCACHE=y" in config,
    "caching configured for feeds and source archives":
        re.search(r"(?m)^\s+feeds\s*$", yaml) is not None
        and re.search(r"(?m)^\s+dl\s*$", yaml) is not None,
    "host tools and cross toolchain have a cache":
        "build_dir/host" in yaml and "build_dir/toolchain-*" in yaml
        and "staging_dir/host" in yaml and "staging_dir/toolchain-*" in yaml,
    "compiler outputs have a persistent bounded cache":
        "path: .ccache" in yaml and "CCACHE_MAXSIZE: 1G" in yaml,
    "source archive cache is saved after download, before compilation":
        yaml.find("Download source archives") <
        yaml.find("Save downloaded sources and feeds") <
        yaml.find("Prepare host tools and toolchain") <
        yaml.find("Build firmware"),
    "toolchain saved before risky firmware compilation":
        yaml.find("Prepare host tools and toolchain") <
        yaml.find("Save host tools and toolchain") <
        yaml.find("Build firmware"),
    "compiler cache still saved on unsuccessful firmware build":
        re.search(r"(?s)- name: Save compiler cache\n\s+if: always\(\)", yaml) is not None,
    "no full serial retry on every compiler failure":
        "make -j$(nproc) || make -j1 V=s" not in yaml,
    "new builds queue instead of cancelling a running firmware build":
        "cancel-in-progress: false" in yaml,
    "firmware output gate still executed":
        "sh scripts/wg2600hp_nss_image_gate.sh" in yaml,
    "kernel/target build directories never restored from stale cache":
        not re.search(
            r"(?m)^\s+(?:build_dir|staging_dir)/target[-/*]", yaml
        ),
    "kernel compiler uses OpenWrt ccache path":
        "KERNEL_CC?=$(TARGET_CC)" in (root / "include/kernel.mk").read_text()
        and "TARGET_CC:= ccache $(TARGET_CC)" in (root / "rules.mk").read_text(),
}
for title, ok in checks.items():
    print(("PASS " if ok else "FAIL ") + title)
success = sum(checks.values())
print("FAST-BUILD PREFLIGHT %d/%d" % (success, len(checks)))
sys.exit(0 if success == len(checks) else 1)
