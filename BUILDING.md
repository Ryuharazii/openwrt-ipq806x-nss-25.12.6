# ビルド手順 / Build Instructions

## 日本語

対象機種：NEC WG2600HP3

確認済みビルド環境：Ubuntu 26.04.1 LTS

1. Ubuntuにビルド依存パッケージをインストールする。

```bash
sudo apt update
sudo apt install -y build-essential clang bison flex gawk   gcc-multilib g++-multilib gettext git libncurses-dev   libssl-dev liblzma-dev python3 python3-setuptools   rsync subversion swig unzip zlib1g-dev file wget   bzip2 pkg-config meson ninja-build zstd
```
2. 以下を実行する。

    git clone -b wg2600hp3-nss-25.12.6-release https://github.com/Ryuharazii/openwrt-ipq806x-nss-25.12.6.git
    cd openwrt-ipq806x-nss-25.12.6
    ./scripts/feeds update -a
    ./scripts/feeds install -a
    cp configs/wg2600hp3.config .config
    make defconfig
    make -j8

完成ファームウェアは bin/targets/ipq806x/generic/ に生成されます。

注意：この手順による新規クローンからの再現性は未検証です。
設定生成時にWeeChat関連の依存関係エラーが発生する場合があります。

## English

Target device: NEC WG2600HP3

Build environment used: Ubuntu 26.04.1 LTS

1. Install the build dependencies using the apt commands above.
2. Run the commands shown in the Japanese section above.

Firmware images are generated in bin/targets/ipq806x/generic/.

Note: Reproducibility from a fresh clone has not yet been verified.
WeeChat-related Kconfig dependency errors may occur.

## Warning

This is experimental, unofficial firmware.
Build success does not guarantee safe operation.
