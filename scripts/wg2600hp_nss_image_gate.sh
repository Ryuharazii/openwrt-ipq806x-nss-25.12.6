#!/bin/sh
# WG2600HP (IPQ8064), OpenWrt 25.12.6 NSS image validation.
# Usage: ./scripts/wg2600hp_nss_image_gate.sh [build-root]
root=${1:-.}
cd "$root" || exit 1
outdir=bin/targets/ipq806x/generic
fail=0
check() {
    if "$@"; then printf 'PASS %s\n' "$*"; else printf 'FAIL %s\n' "$*"; fail=1; fi
}
option() { grep -Fqx "$1=y" .config; }
has_package() { grep -Eq "^$1[[:space:]]" "$manifest"; }

[ -f .config ] && [ -d "$outdir" ] || { echo 'FAIL missing config or output directory'; exit 1; }
for opt in \
  CONFIG_TARGET_ipq806x_generic_DEVICE_nec_wg2600hp \
  CONFIG_PACKAGE_kmod-qca-nss-gmac \
  CONFIG_PACKAGE_kmod-qca-nss-drv \
  CONFIG_PACKAGE_kmod-qca-nss-ecm-standard \
  CONFIG_PACKAGE_kmod-qca-nss-drv-tunipip6 \
  CONFIG_NSS_DRV_IPV6_ENABLE \
  CONFIG_NSS_DRV_VIRT_IF_ENABLE \
  CONFIG_TARGET_ROOTFS_INITRAMFS \
  CONFIG_NSS_DRV_TUNIPIP6_ENABLE; do
    if ! option "$opt"; then echo "FAIL config: $opt"; fail=1; fi
done
manifest=$(find "$outdir" -maxdepth 1 -type f -name '*ipq806x-generic*.manifest' -print -quit)
[ -n "$manifest" ] || { echo 'FAIL WG2600HP manifest is absent'; exit 1; }
for pkg in \
  kmod-qca-nss-gmac \
  kmod-qca-nss-drv \
  kmod-qca-nss-ecm-standard \
  kmod-qca-nss-drv-tunipip6; do
    if ! has_package "$pkg"; then echo "FAIL manifest: $pkg"; fail=1; fi
done
image=$(find "$outdir" -maxdepth 1 -type f -name '*nec_wg2600hp-*sysupgrade.bin' -print -quit)
if [ -z "$image" ]; then
    echo 'FAIL WG2600HP sysupgrade.bin is absent'
    fail=1
else
    size=$(wc -c < "$image")
    # WG2600HP firmware region in device DTS: reg=<0x860000 0x17a0000>.
    if [ "$size" -le 24772608 ]; then
        echo "PASS sysupgrade size $size <= 24772608 bytes"
    else
        echo "FAIL sysupgrade size $size > 24772608 bytes"
        fail=1
    fi
fi
# A useful RAM test image must be available as well.
initramfs=$(find "$outdir" -maxdepth 1 -type f -name '*nec_wg2600hp-initramfs*' -print -quit)
if [ -z "$initramfs" ]; then echo 'FAIL WG2600HP initramfs absent'; fail=1; fi

# Inspect the actual compiled DTB rather than trusting source text alone.
dtb=$(find build_dir -type f -name 'qcom-ipq8064-wg2600hp.dtb' -print -quit 2>/dev/null)
dtc=staging_dir/host/bin/dtc
if [ -z "$dtb" ] || [ ! -x "$dtc" ]; then
    echo 'FAIL compiled WG2600HP DTB or host dtc is absent'
    fail=1
else
    tmp=$(mktemp) || exit 1
    if "$dtc" -I dtb -O dts -o "$tmp" "$dtb" 2>/dev/null; then
        gmac=$(grep -c 'qcom,nss-gmac' "$tmp" || true)
        if [ "$gmac" -ge 2 ] && grep -q 'qcom,nss-common' "$tmp" && grep -q 'nec,wg2600hp' "$tmp"; then
            echo 'PASS DTB: WG2600HP compatible, 2 NSS GMAC, NSS common'
        else
            echo "FAIL DTB: compatible/NSS GMAC/NSS common (gmac=$gmac)"
            fail=1
        fi
    else
        echo 'FAIL DTB decompilation'
        fail=1
    fi
    rm -f "$tmp"
fi
[ "$fail" -eq 0 ] || exit 1
printf 'PASS WG2600HP NSS image gate\n'
