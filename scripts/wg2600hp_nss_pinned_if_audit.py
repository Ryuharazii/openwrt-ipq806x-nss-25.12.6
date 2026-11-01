#!/usr/bin/env python3
"""Isolated WG2600HP NSS physical IF source contract audit, no building.

Fetch the exact qca-nss-drv and qca-nss-gmac package pins, apply the
repository's package patches, and log driver IF mapping source evidence.
This is never a claim about QCA NSS firmware parsing or actual boot.
"""
from pathlib import Path
import json
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    ("drv", "qca-nss-drv", "https://git.codelinaro.org/clo/qsdk/oss/lklm/nss-drv.git", "3cfb9f43"),
    ("gmac", "qca-nss-gmac", "https://git.codelinaro.org/clo/qsdk/oss/lklm/nss-gmac.git",
     "171767947467662f2407d0cfff26dfb136c3fb4a"),
)
SYMBOLS = {
    "drv": ("nss_cmn_get_interface_number_by_dev", "subsys_dp_register", "nss_data_plane_register",
            "nss_gmac_get_netdev_by_macid", "NSS_DRV_VLAN_ENABLE"),
    "gmac": ("nss_gmac_get_netdev_by_macid", "nss_gmac_probe", "subsys_dp_register"),
}

def run_command(args, timeout=85, cwd=None):
    try:
        return subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as e:
        return type("Timeout", (), {"returncode": 124, "stdout": f"timeout: {e}"})()

def emit(s):
    print(s, flush=True)

def package_pin(name, url, pin):
    lines = (ROOT / "package/qca-nss" / name / "Makefile").read_text().splitlines()
    actual = dict((m.group(1), m.group(2)) for line in lines
                  if (m := re.match(r"^(PKG_SOURCE_URL|PKG_SOURCE_VERSION):=(.+)$", line)))
    if actual != {"PKG_SOURCE_URL": url, "PKG_SOURCE_VERSION": pin}:
        raise RuntimeError(f"PACKAGE_PIN=FAIL {name}: {actual}")
    emit(f"PACKAGE_PIN=VERIFIED {name} {pin}")

def resolve_full_commit(url, prefix):
    if len(prefix) == 40:
        return prefix
    # GitLab API resolves an abbreviated SHA without guessing a branch tip.
    project = url.removesuffix(".git").split("git.codelinaro.org/", 1)[-1]
    path = urllib.parse.quote(project, safe="")
    target = ("https://git.codelinaro.org/api/v4/projects/" + path +
              "/repository/commits/" + urllib.parse.quote(prefix, safe=""))
    try:
        req = urllib.request.Request(target, headers={"User-Agent": "WG2600HP-pinned-audit"})
        with urllib.request.urlopen(req, timeout=25) as response:
            result = json.loads(response.read().decode())
        full = result.get("id", "")
        if len(full) == 40 and full.startswith(prefix):
            emit(f"PIN_RESOLVE=PASS {prefix} {full}")
            return full
        emit(f"PIN_RESOLVE=BLOCKED {prefix} unexpected commit response")
    except Exception as e:
        emit(f"PIN_RESOLVE=BLOCKED {prefix} {type(e).__name__}: {e}")
    return None

def fetch_source(where, remote, pin):
    where.mkdir()
    run_command(["git", "init", "-q", str(where)])
    run_command(["git", "-C", str(where), "remote", "add", "origin", remote])
    # Exact full ID is used whenever available. A short fetch is only a
    # fallback; resulting SHA must still verify the source pin prefix.
    resolved = resolve_full_commit(remote, pin)
    targets = [resolved] if resolved else []
    if pin not in targets:
        targets.append(pin)
    for target in targets:
        p = run_command(["git", "-C", str(where), "-c", "http.lowSpeedLimit=100",
                         "-c", "http.lowSpeedTime=15", "fetch", "--no-tags",
                         "--depth=1", "origin", target], timeout=95)
        if p.returncode == 0:
            q = run_command(["git", "-C", str(where), "-c", "advice.detachedHead=false",
                             "checkout", "-q", "--detach", "FETCH_HEAD"])
            if q.returncode:
                emit(f"PIN_FETCH=FAIL checkout {q.stdout[-400:]}")
                return False
            actual = run_command(["git", "-C", str(where), "rev-parse", "HEAD"]).stdout.strip()
            if len(actual) != 40 or not actual.startswith(pin):
                emit(f"PIN_FETCH=FAIL wrong commit actual={actual} pin={pin}")
                return False
            emit(f"PIN_SOURCE=VERIFIED {where.name} commit={actual}")
            return True
        emit(f"PIN_FETCH_ATTEMPT=BLOCKED {where.name} {target} {p.stdout[-350:]}")
    return False

def apply_package_patches(where, package):
    patchdir = ROOT / "package/qca-nss" / package / "patches"
    patches = sorted(patchdir.glob("*.patch"))
    if not patches:
        emit(f"PIN_PATCH_CHAIN=FAIL missing {package}")
        return False
    for p in patches:
        a = run_command(["patch", "-d", str(where), "-p1", "-f", "--batch",
                         "--forward", "--fuzz=0", "--input", str(p)])
        if a.returncode:
            emit(f"PIN_PATCH_CHAIN=FAIL {package} {p.name} {a.stdout[-1600:]}")
            return False
        emit(f"PIN_PATCH=PASS {package}/{p.name}")
    emit(f"PIN_PATCH_CHAIN=PASS {package} count={len(patches)}")
    return True

def print_evidence(src, category):
    # Limit evidence to distinctive source lines. Paths and line numbers are
    # from the *verified* checkout, not a public-mirror approximation.
    for sym in SYMBOLS[category]:
        matches = []
        for f in sorted(src.rglob("*")):
            if not f.is_file() or f.suffix not in (".c", ".h"):
                continue
            if f.stat().st_size > 4_000_000:
                continue
            try:
                lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for number, line in enumerate(lines, 1):
                if sym not in line:
                    continue
                if "nss_cmn_get_interface_number_by_dev" in sym and f.name != "nss_cmn.c":
                    continue
                if sym == "nss_gmac_get_netdev_by_macid" and category == "gmac" and f.suffix != ".c":
                    continue
                matches.append(f"{f.relative_to(src)}:{number}:{line.strip()[:190]}")
                if len(matches) >= 8:
                    break
            if len(matches) >= 8:
                break
        emit(f"PIN_SOURCE_SYMBOL={category}/{sym} matches={len(matches)}")
        for m in matches[:8]:
            emit("PIN_SOURCE_LINE " + m)
    if category == "drv":
        for base in ("nss_cmn.c", "nss_data_plane.c"):
            files = sorted(src.rglob(base))
            if not files:
                emit(f"PIN_MAPPING_FILE=MISSING {base}")
                continue
            lines = files[0].read_text(encoding="utf-8", errors="replace").splitlines()
            for i, line in enumerate(lines):
                if any(token in line for token in (
                    "nss_cmn_get_interface_number_by_dev(",
                    "subsys_dp_register[", "nss_gmac_get_netdev_by_macid(")):
                    lo, hi = max(0, i-2), min(len(lines), i+7)
                    emit(f"PIN_IF_MAPPING_CONTEXT {base}:{i+1}")
                    for n in range(lo, hi):
                        emit(f"PIN_IF_MAPPING_LINE {n+1}: {lines[n][:190]}")
                    # Output up to the first 4 fragments per file.
                    break

def log_pinned_path_contract(src, category):
    # Capture the actual fixed-pin control flow, not a similarly-named
    # function in a different revision or target SoC.
    specs = (
        (
            "drv",
            "nss_cmn.c",
            ("int32_t nss_cmn_get_interface_number_by_dev_and_type(",
             "int32_t nss_cmn_get_interface_number_by_dev("),
            24,
        ),
        (
            "drv",
            "nss_data_plane/nss_data_plane_gmac.c",
            ("static bool nss_data_plane_register_to_nss_gmac(",
             "nss_gmac_get_netdev_by_macid(if_num)"),
            36,
        ),
        (
            "gmac",
            "ipq806x/nss_gmac_tx_rx_offload.c",
            ("struct net_device *nss_gmac_get_netdev_by_macid(",),
            16,
        ),
    )
    for owner, relative, needles, length in specs:
        if category != owner:
            continue
        file = src / relative
        if not file.is_file():
            raise RuntimeError(f"PIN_IF_CONTRACT_FILE=MISSING {relative}")
        content = file.read_text(encoding="utf-8", errors="replace").splitlines()
        for needle in needles:
            matches = [i for i, line in enumerate(content) if needle in line]
            if len(matches) != 1:
                raise RuntimeError(f"PIN_IF_CONTRACT=FAIL {relative} {needle!r} count={len(matches)}")
            start = matches[0]
            emit(f"PIN_IF_CONTRACT_CONTEXT {relative}:{start+1} symbol={needle}")
            for i in range(start, min(len(content), start + length)):
                emit(f"PIN_IF_CONTRACT_LINE {relative}:{i+1}: {content[i][:190]}")
    emit(f"PIN_IF_CONTRACT=INSPECTED {category} source only; firmware behavior unknown")


def audit_ipv4_vlan_rule_contract(source):
    # Probe the exact 3cfb9f43 NSS IPv4 message ABI, independent of
    # NSS_DRV_VLAN_ENABLE (the VLAN interface module). This is not FW proof.
    header = source / "exports/nss_ipv4.h"
    if not header.is_file():
        emit("IPV4_RULE_ABI=FAIL exact source exports/nss_ipv4.h missing")
        return False
    lines = header.read_text(encoding="utf-8", errors="replace").splitlines()
    needles = (
        "NSS_IPV4_RULE_CREATE_VLAN_VALID",
        "struct nss_ipv4_vlan_rule",
        "vlan_primary_rule",
        "vlan_secondary_rule",
        "struct nss_ipv4_rule_create_msg",
    )
    for token in needles:
        found = [(i+1, line.strip()) for i, line in enumerate(lines) if token in line]
        if not found:
            emit(f"IPV4_RULE_ABI=FAIL missing {token}")
            return False
        for line, value in found[:4]:
            emit(f"IPV4_RULE_ABI_SYMBOL=FOUND exports/nss_ipv4.h:{line} {value[:180]}")
    ipv4_sources = sorted(source.glob("nss_ipv4*.c"))
    for path in ipv4_sources:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for i, line in enumerate(lines):
            if "NSS_DRV_VLAN_ENABLE" in line or "NSS_IPV4_TX_CREATE_RULE_MSG" in line:
                emit(f"IPV4_PATH_CONTEXT {path.name}:{i+1}: {line.strip()[:170]}")
    emit("IPV4_RULE_ABI=PASS IPv4 VLAN fields present in driver ABI; FW acceptance unknown")
    return True

def audit_firmware_package_identity():
    # Metadata only: no binary disassembly/reverse engineering.
    base = ROOT / "package/qca-nss/qca-nss-drv/files/nss-firmware"
    import hashlib
    version = (base / "nss_fw_version.h").read_text(encoding="utf-8")
    readme = (base / "README.md").read_text(encoding="utf-8")
    if not all(x in version for x in ("#define NSS_FW_VERSION_MAJOR 11",
                                      "#define NSS_FW_VERSION_MINOR 4")):
        emit("NSS_FIRMWARE_MANIFEST=FAIL version metadata mismatch")
        return False
    if "Synology RT2600ac" not in readme:
        emit("NSS_FIRMWARE_MANIFEST=FAIL provenance metadata changed")
        return False
    for name in ("qca-nss0-retail.bin", "qca-nss1-retail.bin"):
        file = base / name
        if not file.is_file() or file.stat().st_size < 100000:
            emit(f"NSS_FIRMWARE_MANIFEST=FAIL missing/short {name}")
            return False
        emit(f"NSS_FIRMWARE_FILE=IDENTIFIED {name} size={file.stat().st_size} sha256={hashlib.sha256(file.read_bytes()).hexdigest()}")
    emit("NSS_FIRMWARE_MANIFEST=PASS provenance and hashes only, protocol parser capability NOT verified")
    return True

def main():
    drv_cfg = (ROOT / "package/qca-nss/qca-nss-drv/Config.in").read_text()
    wg_cfg = (ROOT / "diff-wg2600hp-nss").read_text()
    vlan_disabled = "#config NSS_DRV_VLAN_ENABLE" in drv_cfg and (
        "CONFIG_NSS_DRV_VLAN_ENABLE=y" not in wg_cfg)
    emit(f"CONFIG_NSS_DRV_VLAN_EXPOSED={'NO' if vlan_disabled else 'REVIEW'}")
    if not vlan_disabled:
        emit("NSS_VLAN_CONFIG=REVIEW unsupported assumption")
        return 12
    with tempfile.TemporaryDirectory(prefix="wg2600hp-pin-nss-") as tmp:
        for key, package, url, pin in SOURCES:
            package_pin(package, url, pin)
            path = Path(tmp) / key
            if not fetch_source(path, url, pin):
                emit(f"PIN_SOURCE_AUDIT=BLOCKED {package}")
                return 20
            if not apply_package_patches(path, package):
                emit(f"PIN_SOURCE_AUDIT=FAIL {package} patch chain")
                return 21
            print_evidence(path, key)
            log_pinned_path_contract(path, key)
            if key == "drv" and not audit_ipv4_vlan_rule_contract(path):
                return 23
    if not audit_firmware_package_identity():
        return 24
    emit("PIN_SOURCE_AUDIT=PASS exact pinned source + package patches inspected")
    emit("PIN_SOURCE_SCOPE=SOURCE_ONLY NO_FW_PARSER_PROOF NO_ARM_BUILD NO_BOOT NO_NSS_CREATE_ACK")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        emit(f"PIN_SOURCE_AUDIT=FAIL {type(error).__name__}: {error}")
        sys.exit(22)
