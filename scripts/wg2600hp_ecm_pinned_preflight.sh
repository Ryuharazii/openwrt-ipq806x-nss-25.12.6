#!/usr/bin/env bash
# WG2600HP IPQ8064 exact ECM source application preflight: no firmware build.
set -euo pipefail
export GIT_TERMINAL_PROMPT=0 LC_ALL=C
root="$(cd "$(dirname "$0")/.." && pwd)"
makefile="$root/package/qca-nss/qca-nss-ecm/Makefile"
patchdir="$root/package/qca-nss/qca-nss-ecm/patches"
stage="$root/backports/staging"
pin="$(sed -n 's/^PKG_SOURCE_VERSION:=//p' "$makefile")"
remote="$(sed -n 's/^PKG_SOURCE_URL:=//p' "$makefile")"
if [[ "$pin" != "9acdcb05c04ae177a79c4c34cef0487fbcedbfaa" ||
      "$remote" != "https://git.codelinaro.org/clo/qsdk/oss/lklm/qca-nss-ecm.git" ]]; then
  echo "ECM_PIN=FAIL source version/URL mismatch"
  exit 12
fi
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
src="$tmp/ecm"
mkdir "$src"
git -C "$src" init -q
git -C "$src" remote add origin "$remote"
echo "ECM_PIN_FETCH=START $pin"
if ! timeout 80s git -C "$src" -c http.lowSpeedLimit=100 -c http.lowSpeedTime=20 fetch --no-tags --depth=1 origin "$pin"; then
  echo "ECM_PIN_FETCH=BLOCKED exact upstream commit unavailable"
  exit 20
fi
git -C "$src" -c advice.detachedHead=false checkout -q --detach FETCH_HEAD
actual="$(git -C "$src" rev-parse HEAD)"
if [[ "$actual" != "$pin" ]]; then
  echo "ECM_PIN=FAIL actual=$actual"
  exit 13
fi
echo "ECM_PIN=VERIFIED $actual"
# Active OpenWrt package patches already include 760-04 and 760-05.
# Check staging identity, but apply each patch once.
for candidate in 760-04-ecm-8021q-conduit-pinned-CANDIDATE.patch 760-05-ecm-nss-vlan-dsa-guards-pinned-CANDIDATE.patch; do
  if ! cmp -s "$stage/$candidate" "$patchdir/$candidate"; then
    echo "ECM_PACKAGE_STAGE=FAIL mismatch $candidate"
    exit 23
  fi
done
patch_count="$(find "$patchdir" -maxdepth 1 -name '*.patch' -type f | wc -l)"
if [ "$patch_count" -ne 11 ]; then
  echo "ECM_PATCH_COUNT=FAIL expected=11 actual=$patch_count"
  exit 24
fi
for p in "$patchdir"/*.patch; do
  name="$(basename "$p")"
  if ! patch --directory "$src" -p1 --batch --forward --fuzz=0 --no-backup-if-mismatch \
       --input "$p" > "$tmp/patch.log" 2>&1; then
    echo "ECM_STAGED_APPLY=FAIL at $name"
    sed -n '1,85p' "$tmp/patch.log"
    exit 21
  fi
  echo "ECM_PATCH=PASS $name sha256=$(sha256sum "$p" | cut -d' ' -f1)"
done
# Record how the pinned ECM NSS IPv4 frontend populates VLAN create fields.
# Strings here are evidence of the source ABI, NOT evidence of firmware ACK.
for token in NSS_IPV4_RULE_CREATE_VLAN_VALID vlan_primary_rule vlan_secondary_rule; do
  matches="$(grep -Rn -F --include='*.c' --include='*.h' "$token" "$src/frontends/nss" | head -n 6 || true)"
  if [ -z "$matches" ]; then
    echo "ECM_IPV4_VLAN_RULE=REVIEW missing token $token"
  else
    echo "ECM_IPV4_VLAN_RULE=FOUND token=$token"
    printf '%s\n' "$matches"
  fi
done
# Strict source-level evidence: both IPv4 frontends must populate tagged
# CREATE rules. This verifies source relationships, not NSS firmware behavior.
for frontend in ecm_nss_ported_ipv4.c ecm_nss_non_ported_ipv4.c; do
  file="$src/frontends/nss/$frontend"
  for token in NSS_IPV4_RULE_CREATE_VLAN_VALID vlan_primary_rule.ingress_vlan_tag vlan_primary_rule.egress_vlan_tag; do
    if ! grep -Fq "$token" "$file"; then
      echo "ECM_IPV4_VLAN_FRONTEND=FAIL $frontend token=$token"
      exit 22
    fi
  done
  echo "ECM_IPV4_VLAN_FRONTEND=PASS $frontend create-valid-flag+ingress+egress source fields"
done
echo "ECM_IPV4_RULE_SCOPE=ABI_ONLY NOT_NSS_FW_SUPPORTED NOT_NSS_CREATE_ACK"
echo "ECM_ACTIVE_PATCH_CHAIN=PASS 11 patches applied exactly once"
if [ "$#" -eq 2 ] && [ "$1" = "--arm-kernel" ]; then
  kernel="$2"
  if [ ! -f "$kernel/include/generated/autoconf.h" ]; then
    echo "ECM_ARM=FAIL kernel has not been prepared"
    exit 31
  fi
  drv="$tmp/nss-driver"
  mkdir "$drv"
  git -C "$drv" init -q
  git -C "$drv" remote add origin https://git.codelinaro.org/clo/qsdk/oss/lklm/nss-drv.git
  echo "ECM_NSS_INCLUDE_FETCH=START pin=3cfb9f43"
  if ! timeout 90s git -C "$drv" -c http.lowSpeedLimit=100 -c http.lowSpeedTime=20 fetch --no-tags --depth=1 origin 3cfb9f43; then
    echo "ECM_NSS_INCLUDE_FETCH=BLOCKED"
    exit 32
  fi
  git -C "$drv" -c advice.detachedHead=false checkout -q --detach FETCH_HEAD
  for patchfile in "$root"/package/qca-nss/qca-nss-drv/patches/*.patch; do
    if ! patch --directory "$drv" -p1 --batch --forward --fuzz=0 --no-backup-if-mismatch --input "$patchfile" > "$tmp/driver-patch.log" 2>&1; then
      echo "ECM_NSS_DRIVER_PATCH=FAIL $(basename "$patchfile")"
      head -n 70 "$tmp/driver-patch.log"
      exit 33
    fi
  done
  echo "ECM_ARM=START pinned ECM with NSS front-end and DSA VLAN enabled"
  for obj in ecm_interface.o frontends/nss/ecm_nss_ported_ipv4.o; do
    if ! make -C "$kernel" -j2 ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- M="$src" ECM_INTERFACE_VLAN_ENABLE=y ECM_NON_PORTED_SUPPORT_ENABLE=y ECM_FRONT_END_NSS_ENABLE=y ECM_IPV6_ENABLE=y SoC=ipq806x EXTRA_CFLAGS="-I$drv/exports -I$src/exports" "$obj" > "$tmp/ecm-arm.log" 2>&1; then
      echo "ECM_ARM=FAIL $obj"
      tail -n 100 "$tmp/ecm-arm.log"
      exit 34
    fi
    if [ ! -s "$src/$obj" ]; then
      echo "ECM_ARM=FAIL object missing $obj"
      exit 35
    fi
    if ! arm-linux-gnueabihf-readelf -h "$src/$obj" | grep -q 'Machine:.*ARM'; then
      echo "ECM_ARM=FAIL wrong object target $obj"
      exit 36
    fi
    echo "ECM_ARM_OBJECT=PASS $obj"
  done
  echo "ECM_ARM_SCOPE=OBJECTS_ONLY NO_FIRMWARE NO_BOOT NO_NSS_ACK"
elif [ "$#" -eq 0 ]; then
  echo "ECM_SCOPE=SOURCE_APPLY_ONLY NO_ARM_BUILD NO_BOOT NO_NSS_ACK"
else
  echo "ECM_ARM=FAIL invalid arguments"
  exit 2
fi
