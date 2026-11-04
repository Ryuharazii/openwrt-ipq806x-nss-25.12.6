#!/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
F="$ROOT/feed-fixes"

apply_patch() {
    REPO="$1"
    PATCH="$2"

    if git -C "$REPO" apply --reverse --check "$PATCH" 2>/dev/null; then
        echo "ALREADY APPLIED: $(basename "$PATCH")"
    else
        git -C "$REPO" apply --check "$PATCH"
        git -C "$REPO" apply "$PATCH"
        echo "APPLIED: $(basename "$PATCH")"
    fi
}

install_patch() {
    SRC="$F/$1"
    DST="$ROOT/feeds/luci/modules/$2/patches/$3"

    if [ -e "$DST" ]; then
        cmp -s "$SRC" "$DST" || {
            echo "ERROR: Existing patch differs: $DST" >&2
            exit 1
        }
    else
        mkdir -p "$(dirname "$DST")"
        cp "$SRC" "$DST"
    fi
    echo "OK: $3"
}

apply_patch "$ROOT/feeds/packages" "$F/weechat-packages.patch"
apply_patch "$ROOT/feeds/luci" "$F/luci-app-weechat.patch"

install_patch luci-mod-network-001-enable-vht.patch luci-mod-network 001-enable-vht.patch
install_patch luci-mod-status-001-show-nss-load.patch luci-mod-status 001-show-nss-load.patch

echo "FEED FIXES COMPLETE"
