#!/usr/bin/env python3
"""WG2600HP IPQ8064: isolate the DTS/Kconfig 760-07 selection candidate.

Validates candidate application on copied board config and device tree.
Does not touch repository config or user VLANs; no ARM build or actual boot.
"""
from pathlib import Path
import difflib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
CONFIG = "target/linux/ipq806x/config-6.12"
DTS = "target/linux/ipq806x/files-6.12/arch/arm/boot/dts/qcom/qcom-ipq8064-wg2600hp.dts"
PATCH = "backports/staging/760-07-wg2600hp-qca8021q-dts-config-CANDIDATE.patch"
TAGGER = "target/linux/generic/pending-6.12/760-01-net-dsa-qca8k-8021q-tagger-stage.patch"

def node(text, name):
    m = re.search(r"(?m)\bport@" + str(name) + r"\s*\{", text)
    if not m:
        return ""
    depth = 0
    for i in range(m.end()-1, len(text)):
        if text[i] == "{":
            depth += 1
        if text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[m.start():i+1]
    return ""

def run():
    patch = (ROOT / PATCH).read_text(encoding="utf-8")
    target_paths = re.findall(r"(?m)^\+\+\+ b/([^\n]+)$", patch)
    if target_paths != [CONFIG, DTS]:
        print(f"DTS_CONFIG_SCOPE=FAIL unexpected targets {target_paths}", flush=True)
        return 12
    baseline_cfg = (ROOT / CONFIG).read_text(encoding="utf-8")
    baseline_dt = (ROOT / DTS).read_text(encoding="utf-8")
    if "CONFIG_NET_DSA_TAG_QCA_8021Q=y" in baseline_cfg or "dsa-tag-protocol" in baseline_dt:
        print("DTS_CONFIG_BASELINE=FAIL candidate unexpectedly active", flush=True)
        return 13
    tagger = (ROOT / TAGGER).read_text(encoding="utf-8")
    if '+#define QCA_8021Q_NAME "qca-8021q"' not in tagger:
        print("DTS_CONFIG_TAGGER=FAIL unmatched tagger name", flush=True)
        return 14
    with tempfile.TemporaryDirectory(prefix="wg2600hp-dts-config-") as d:
        dest = Path(d)
        for path in (CONFIG, DTS):
            target = dest / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, target)
        p = subprocess.run(["patch", "--directory", str(dest), "-p1",
                            "--batch", "--forward", "--fuzz=0",
                            "--input", str(ROOT / PATCH)],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, check=False)
        if p.returncode:
            print("DTS_CONFIG_76007_APPLY=FAIL", flush=True)
            print(p.stdout[-2000:], flush=True)
            # The working copy may have partially-applied files. Recreate a
            # fresh exact baseline and check that git apply can reproduce the
            # intended code change. Never upgrade GNU failure to PASS.
            with tempfile.TemporaryDirectory(prefix="wg2600hp-dts-canonical-") as t:
                base = Path(t)
                for path in (CONFIG, DTS):
                    dst = base / path
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(ROOT / path, dst)
                gitcheck = subprocess.run(
                    ["git", "-C", str(base), "apply", "--check", "-p1", str(ROOT / PATCH)],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, check=False)
                print(f"DTS_CONFIG_GIT_APPLY_CHECK={'PASS' if gitcheck.returncode == 0 else 'FAIL'}", flush=True)
                if gitcheck.returncode == 0:
                    applied = subprocess.run(
                        ["git", "-C", str(base), "apply", "-p1", str(ROOT / PATCH)],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, check=False)
                    if applied.returncode == 0:
                        canon = ""
                        for path, old in ((CONFIG, baseline_cfg), (DTS, baseline_dt)):
                            new = (base / path).read_text(encoding="utf-8")
                            canon += "".join(difflib.unified_diff(
                                old.splitlines(keepends=True),
                                new.splitlines(keepends=True),
                                fromfile="a/" + path, tofile="b/" + path, n=3))
                        canonical_file = base / "canonical.patch"
                        canonical_file.write_text(canon, encoding="utf-8")
                        # Reload the exact source for a GNU dry-run, no mutation.
                        for path in (CONFIG, DTS):
                            shutil.copyfile(ROOT / path, base / path)
                        dry = subprocess.run(
                            ["patch", "--directory", str(base), "-p1", "--batch",
                             "--forward", "--fuzz=0", "--dry-run",
                             "--input", str(canonical_file)],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, check=False)
                        print(f"DTS_CONFIG_CANONICAL_GNU_F0={'PASS' if dry.returncode == 0 else 'FAIL'}", flush=True)
                        if dry.returncode == 0:
                            print("DTS_CONFIG_CANONICAL_PATCH_BEGIN", flush=True)
                            print(canon.rstrip("\n"), flush=True)
                            print("DTS_CONFIG_CANONICAL_PATCH_END", flush=True)
                        else:
                            print(dry.stdout[-1500:], flush=True)
                    else:
                        print(f"DTS_CONFIG_GIT_APPLY=FAIL {applied.stdout[-800:]}", flush=True)
                else:
                    print(gitcheck.stdout[-1500:], flush=True)
            return 21
        cfg = (dest / CONFIG).read_text(encoding="utf-8")
        dt = (dest / DTS).read_text(encoding="utf-8")
    if not re.search(r"(?m)^CONFIG_NET_DSA_TAG_QCA_8021Q=y$", cfg):
        print("DTS_CONFIG=FAIL QCA 8021q tagger disabled", flush=True)
        return 22
    if not re.search(r"(?m)^CONFIG_NET_DSA_TAG_QCA=y$", cfg):
        print("DTS_CONFIG=FAIL standard QCA tagger missing", flush=True)
        return 22
    if dt.count('dsa-tag-protocol = "qca-8021q";') != 2:
        print("DTS_CONFIG=FAIL CPU-port tags not exactly two", flush=True)
        return 23
    for port, gmac, mode in ((0, "gmac1", "rgmii"), (6, "gmac2", "sgmii")):
        n = node(dt, port)
        if not n or f'ethernet = <&{gmac}>;' not in n or (
                'dsa-tag-protocol = "qca-8021q";' not in n or
                f'phy-mode = "{mode}";' not in n):
            print(f"DTS_CONFIG_CPU_PORT=FAIL port={port} gmac={gmac}", flush=True)
            return 24
        print(f"DTS_CONFIG_CPU_PORT=PASS port={port} {gmac} {mode}", flush=True)
    print("DTS_CONFIG_76007_APPLY=PASS strict fuzz0, isolated copy", flush=True)
    print("DTS_CONFIG_SCOPE=STAGING_ONLY NO_BOARD_CONFIG_CHANGE NO_ARM_BUILD NO_BOOT NO_NSS_ACK", flush=True)
    return 0

if __name__ == "__main__":
    sys.exit(run())
