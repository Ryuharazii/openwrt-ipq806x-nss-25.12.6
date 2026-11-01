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
for p in "$patchdir"/*.patch \
  "$stage/760-04-ecm-8021q-conduit-pinned-CANDIDATE.patch" \
  "$stage/760-05-ecm-nss-vlan-dsa-guards-pinned-CANDIDATE.patch"; do
  name="$(basename "$p")"
  if ! patch --directory "$src" -p1 --batch --forward --fuzz=0 --no-backup-if-mismatch \
       --input "$p" > "$tmp/patch.log" 2>&1; then
    echo "ECM_STAGED_APPLY=FAIL at $name"
    sed -n '1,85p' "$tmp/patch.log"
    exit 21
  fi
  echo "ECM_PATCH=PASS $name sha256=$(sha256sum "$p" | cut -d' ' -f1)"
done
echo "ECM_STAGED_APPLY=PASS exact source + OpenWrt patch order + staged 760-04/05"
echo "ECM_SCOPE=SOURCE_APPLY_ONLY NO_ARM_BUILD NO_BOOT NO_NSS_ACK"
