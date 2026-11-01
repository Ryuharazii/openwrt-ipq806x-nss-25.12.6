#!/usr/bin/env python3
"""Host-only full OpenWrt Linux 6.12.112 patch application preflight.

This extracts the sha256-verified upstream kernel to a temporary directory,
copies base overlays, applies ALL generic backport/pending/hack and ipq806x
patches in OpenWrt's official order, then applies proposed DSA candidates.
It does NOT configure, compile, build, boot, or flash firmware.
"""
from pathlib import Path
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
VERSION = "6.12.112"
KERNEL_HASH = "164dc9d1f6c93c61a15e1f071c48379b467f2b17c469cce7223471968208ed03"
KERNEL_URL = "https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.12.112.tar.xz"
PATCH_DIRS = (
    "target/linux/generic/backport-6.12",
    "target/linux/generic/pending-6.12",
    "target/linux/generic/hack-6.12",
    "target/linux/ipq806x/patches-6.12",
)
OVERLAY_DIRS = (
    "target/linux/generic/files",
    "target/linux/generic/files-6.12",
    "target/linux/ipq806x/files",
    "target/linux/ipq806x/files-6.12",
)
STAGED = ()  # Active branch has staged candidates installed in pending-6.12

def say(message):
    print(message, flush=True)

def ensure_pin():
    p = (ROOT / "target/linux/generic/kernel-6.12").read_text(encoding="utf-8")
    if f"LINUX_VERSION-6.12 = .112" not in p or f"LINUX_KERNEL_HASH-{VERSION} = {KERNEL_HASH}" not in p:
        raise ValueError("OpenWrt kernel pin or archive hash changed")
    readme = (ROOT / "target/linux/generic/PATCHES.md").read_text(encoding="utf-8")
    expected = ("backport-*/", "pending-*/", "hack-*/")
    if any(s not in readme for s in expected):
        raise ValueError("Kernel patch order documentation has changed")

def download_verified(dst):
    h = hashlib.sha256()
    n = 0
    started = time.monotonic()
    say(f"KERNEL_ARCHIVE_FETCH=START {KERNEL_URL}")
    try:
        with urllib.request.urlopen(KERNEL_URL, timeout=40) as response, dst.open("wb") as out:
            while True:
                if time.monotonic() - started > 180:
                    raise TimeoutError("archive download exceeded 180 seconds")
                part = response.read(1024 * 1024)
                if not part:
                    break
                h.update(part)
                out.write(part)
                n += len(part)
    except Exception as e:
        say(f"KERNEL_ARCHIVE_FETCH=BLOCKED {e}")
        return False
    actual = h.hexdigest()
    if actual != KERNEL_HASH:
        say(f"KERNEL_ARCHIVE_HASH=FAIL actual={actual} expected={KERNEL_HASH} size={n}")
        return False
    say(f"KERNEL_ARCHIVE_HASH=PASS sha256={actual} bytes={n}")
    return True

def overlay(linux):
    for relative in OVERLAY_DIRS:
        source = ROOT / relative
        if not source.exists():
            continue
        if not source.is_dir():
            raise ValueError(f"unexpected overlay {relative}")
        shutil.copytree(source, linux, dirs_exist_ok=True, symlinks=True)
        say(f"OVERLAY=PASS {relative}")

def ordered_patches(directory):
    series = directory / "series"
    if series.exists():
        names = [s.split("#", 1)[0].strip() for s in series.read_text().splitlines()]
        names = [x for x in names if x]
        return [directory / x for x in names]
    return sorted(directory.glob("*.patch"))

def apply_patch(linux, patchfile, strict):
    flags = ["patch", "-f", "-p1", "-d", str(linux)]
    if strict:
        flags += ["--batch", "--forward", "--fuzz=0"]
    with patchfile.open("rb") as fd:
        p = subprocess.run(flags, stdin=fd, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, check=False)
    msg = p.stdout.decode("utf-8", errors="replace")
    return p.returncode == 0, msg

def cross_compile_dsa_objects(linux):
    """Compile selected real ARM objects; never generate a firmware image."""
    import shutil
    cc = "arm-linux-gnueabihf-"
    if not shutil.which(cc + "gcc"):
        say("ARM_OBJECT=BLOCKED missing ARM cross GCC")
        return 31
    env = {**os.environ, "ARCH": "arm", "CROSS_COMPILE": cc,
           "KBUILD_BUILD_USER": "wg2600hp-audit", "KBUILD_BUILD_HOST": "isolated"}
    def make(args, label, seconds=180):
        cmd = ["make", "-C", str(linux), "-j2"] + args
        say(f"ARM_OBJECT_STEP=BEGIN {label}")
        try:
            result = subprocess.run(cmd, env=env, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True,
                                    timeout=seconds, check=False)
        except subprocess.TimeoutExpired as error:
            say(f"ARM_OBJECT_STEP=TIMEOUT {label}: {error}")
            return False
        if result.returncode:
            say(f"ARM_OBJECT_STEP=FAIL {label} code={result.returncode}")
            say(result.stdout[-18000:])
            return False
        say(f"ARM_OBJECT_STEP=PASS {label}")
        if result.stdout:
            say(result.stdout[-2800:])
        return True

    if not make(["multi_v7_defconfig"], "multi_v7_defconfig", 150):
        return 32
    cmd = [str(linux / "scripts/config")]
    enabling = ("NET_DSA", "NET_DSA_QCA8K", "NET_DSA_TAG_QCA",
                "NET_DSA_TAG_QCA_8021Q", "VLAN_8021Q", "BRIDGE",
                "NET_SWITCHDEV", "NET_DSA_TAG_8021Q")
    c = subprocess.run(cmd + [arg for item in enabling
                                for arg in ("-e", item)],
                       cwd=linux, env=env, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True, check=False)
    if c.returncode:
        say(f"ARM_OBJECT=FAIL scripts/config: {c.stdout}")
        return 33
    if not make(["olddefconfig"], "olddefconfig", 180):
        return 34
    config=(linux / ".config").read_text()
    for key in ("CONFIG_NET_DSA=y", "CONFIG_NET_DSA_QCA8K=y",
                "CONFIG_NET_DSA_TAG_QCA_8021Q=y"):
        if key not in config.splitlines():
            say(f"ARM_OBJECT=FAIL required Kconfig option unresolved: {key}")
            return 35
    say("ARM_OBJECT_KCONFIG=PASS NET_DSA, QCA8K and QCA_8021Q built-in")
    if not make(["prepare"], "ARM_prepare", 240):
        return 36
    for obj in ("net/dsa/tag_qca_8021q.o", "net/dsa/tag_8021q.o",
                "drivers/net/dsa/qca/qca8k-common.o",
                "drivers/net/dsa/qca/qca8k-8xxx.o"):
        if not make([obj], obj, 240):
            return 37
        artifact = linux / obj
        if not artifact.is_file() or artifact.stat().st_size < 2000:
            say(f"ARM_OBJECT=FAIL no object bytes {obj}")
            return 38
        readelf = subprocess.run([cc + "readelf", "-h", str(artifact)],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True,
                                 check=False)
        if readelf.returncode or "Machine:                           ARM" not in readelf.stdout:
            say(f"ARM_OBJECT=FAIL object is not ARM {obj}: {readelf.stdout[-1000:]}")
            return 39
        say(f"ARM_OBJECT=PASS {obj} size={artifact.stat().st_size} ELF_MACHINE=ARM")
    say("ARM_OBJECT_CHAIN=PASS selected 4 objects compiled for ARM, NOT LINKED, NO FW, NO BOOT")
    return 0

def run():
    try:
        ensure_pin()
    except (ValueError, OSError) as e:
        say(f"OPENWRT_PIN=FAIL {e}")
        return 12
    with tempfile.TemporaryDirectory(prefix="wg2600hp-openwrt-kernel-") as tmp:
        temp = Path(tmp)
        archive = temp / f"linux-{VERSION}.tar.xz"
        if not download_verified(archive):
            return 20
        try:
            with tarfile.open(archive, "r:xz") as t:
                # Archive is the SHA256-verified upstream kernel release.
                t.extractall(path=temp, filter="data")
        except Exception as e:
            say(f"KERNEL_ARCHIVE_EXTRACT=FAIL {e}")
            return 22
        linux = temp / f"linux-{VERSION}"
        if not (linux / "include/net/dsa.h").is_file():
            say("KERNEL_SOURCE=FAIL upstream source missing")
            return 22
        say("KERNEL_SOURCE=VERIFIED extracted complete upstream Linux tree")
        overlay(linux)
        total = 0
        fuzzy = []
        for dirname in PATCH_DIRS:
            directory = ROOT / dirname
            if not directory.is_dir():
                say(f"OPENWRT_PATCH_DIR=FAIL {dirname} missing")
                return 23
            files = ordered_patches(directory)
            say(f"OPENWRT_PATCH_DIR=BEGIN {dirname} count={len(files)}")
            for file in files:
                if not file.is_file():
                    say(f"OPENWRT_PATCH=FAIL missing {file}")
                    return 23
                if file.name.startswith("760-01-net-dsa-qca8k"):
                    # Capture pre-application state. No candidate mutation.
                    header_lines = (linux / "include/net/dsa.h").read_text(
                        encoding="utf-8").splitlines()
                    for i, line in enumerate(header_lines):
                        if "DSA_TAG_PROTO_VSC73XX_8021Q_VALUE" in line:
                            low = max(0, i - 5)
                            high = min(len(header_lines), i + 10)
                            for n in range(low, high):
                                say(f"DSA_PRE_76001_HEADER_LINE={n+1} {header_lines[n]}")
                            break
                    original = file.read_text(encoding="utf-8")
                    for root_dir in PATCH_DIRS[:2]:
                        for prior in ordered_patches(ROOT / root_dir):
                            if prior == file:
                                break
                            body = prior.read_text(encoding="utf-8", errors="replace")
                            if "include/net/dsa.h" in body:
                                say(f"DSA_76001_POSSIBLE_PREDECESSOR={prior.relative_to(ROOT)}")
                    for label, cmd in [
                        ("GIT_APPLY", ["git", "-C", str(linux), "apply", "--check", "-p1", str(file)]),
                        ("GNU_FUZZ0", ["patch", "-f", "-p1", "-d", str(linux),
                                       "--batch", "--forward", "--fuzz=0",
                                       "--dry-run", "--input", str(file)])]:
                        trial = subprocess.run(cmd, stdout=subprocess.PIPE,
                                               stderr=subprocess.STDOUT, check=False)
                        say(f"DSA_76001_AFTER_BACKPORT_{label}={'PASS' if trial.returncode == 0 else 'FAIL'}")
                        if trial.returncode:
                            say(trial.stdout.decode("utf-8", errors="replace")[-1400:])
                ok, msg = apply_patch(linux, file, strict=False)
                if not ok:
                    say(f"OPENWRT_PATCH=FAIL {file.relative_to(ROOT)}")
                    say(msg[-5000:])
                    return 24
                if re.search(r"(with fuzz|offset [+-])", msg):
                    fuzzy.append(str(file.relative_to(ROOT)))
                total += 1
            say(f"OPENWRT_PATCH_DIR=PASS {dirname} count={len(files)}")
        if total != 594:
            say(f"OPENWRT_INTEGRATED_COUNT=FAIL expected 594 got {total}")
            return 28
        say("OPENWRT_INTEGRATED_COUNT=PASS 594 kernel patches including 760-12")
        say(f"OPENWRT_BASELINE_PATCH_CHAIN=PASS applied={total} fuzz_or_offset={len(fuzzy)}")
        for f in fuzzy[:20]:
            say(f"OPENWRT_CONTEXT_ADJUSTED={f}")
        stage_ok = 0
        for relative in STAGED:
            p = ROOT / relative
            ok, msg = apply_patch(linux, p, strict=True)
            if not ok:
                say(f"DSA_STAGED_AFTER_FULL_OPENWRT=FAIL at={relative} pass={stage_ok}/{len(STAGED)}")
                say(msg[-5000:])
                return 25
            say(f"DSA_STAGED_PATCH=PASS {relative}")
            stage_ok += 1
        tag_defs = re.findall(
            r"(?m)^#define\s+DSA_TAG_PROTO_([A-Z0-9_]+)_VALUE\s+(\d+)\s*$",
            (linux / "include/net/dsa.h").read_text(encoding="utf-8"))
        ids = {}
        for label, number in tag_defs:
            ids.setdefault(int(number), []).append(label)
        duplicates = {num: names for num, names in ids.items() if len(names) > 1}
        if duplicates or ids.get(29) != ["BRCM_LEGACY_FCS"] or ids.get(30) != ["QCA_8021Q"]:
            say(f"DSA_PROTOCOL_ID_UNIQUE=FAIL id29={ids.get(29)} id30={ids.get(30)} duplicates={duplicates}")
            return 26
        say("DSA_PROTOCOL_ID_UNIQUE=PASS ID29=BRCM_LEGACY_FCS ID30=QCA_8021Q")
        qca = (linux / "drivers/net/dsa/qca/qca8k-common.c").read_text()
        required = ("qca8k_tag_8021q_vlan_snapshot(", "previous_ctrl0",
                    "previous_egress", "restore_member:", "old_member")
        if any(needle not in qca for needle in required):
            say("OPENWRT_ROLLBACK_CANDIDATE=FAIL missing source contract")
            return 29
        say("OPENWRT_ROLLBACK_CANDIDATE=SOURCE_PRESENT not hardware verified")
        say(f"DSA_STAGED_AFTER_FULL_OPENWRT=PASS {stage_ok}/{len(STAGED)}")
        if "--arm-objects" in sys.argv[1:]:
            result = cross_compile_dsa_objects(linux)
            if result:
                return result
            say("FULL_SOURCE_SCOPE=ARM_DSA_OBJECTS_ONLY NO_OPENWRT_FIRMWARE NO_BOOT NO_NSS_ACK")
        else:
            say("FULL_SOURCE_SCOPE=PATCH_APPLY_ONLY NO_KERNEL_CONFIG NO_ARM_COMPILE NO_BOOT NO_NSS_ACK")
        return 0

if __name__ == "__main__":
    sys.exit(run())
