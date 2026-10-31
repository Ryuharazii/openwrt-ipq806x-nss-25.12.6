# WG2600HP (IPQ8064) OpenWrt 25.12.6 NSS — Resume here

**作業再開の唯一の入口 (2026-10-31)**。セッション移動時は最初にこの文書と [WG2600HP-EXECUTION-GATES.md](WG2600HP-EXECUTION-GATES.md) を読むこと。**以前の経緯を再説明してもらったり同一ZIPを再アップロードしてもらったりしないこと。** ユーザーが過去パッチを復元している場合も、復元完了を待って作業を一方的に中断しない。再入手できた場合は差分証拠として取り込む。

## 固定条件

- 対象は **NEC WG2600HP (IPQ8064)** のみ。WG2600HP3 (IPQ8062) を混同しない。
- OpenWrt **25.12.6**, kernel **6.12.112**。**完成要件は有線IPv4、Wi-Fi、固定IPIP6の各NSS高速化（3件）**。現在は有線IPv4 LAN→WANのNSS加速を先に成立させるが、**Wi-Fi NSSを後から思いついた追加要件として扱わない**。ath10k/mac80211のNSS redirectと完全Wi-Fiオフロードは区別し、実機で動作・効果を測定する。
- **ユーザー明示（2026-10-31）:「VLANは必要ない」**。WAN/LANでISPタグ・802.1Qサブインターフェース等の**ユーザー向けVLAN設定は不要**。新規VLAN設定を前提にしない。既存の `target/linux/ipq806x/base-files/etc/board.d/02_network` もWG2600HPに `lan1 lan2 lan3 lan4`/ `wan` を設定し、conduitはLAN→`eth1`、WAN→`eth0`。新たなユーザーVLAN設定は明示されていない。
- **内部フレーム識別とユーザー用VLANを区別すること**。QCA8337/DSAにはポート識別が必要であり、候補の `qca-8021q` はユーザーがVLANを設定することとは別の**内部タグ方式**。標準QCAヘッダのままNSS L3処理を成立させられるかも独立して検証し、8021Qの導入を無条件の前提にしない。公開IPQ5018+QCA8337事例はNSSがQCA 2バイトヘッダを解析できないと報告（https://github.com/kuncy7/openwrt-nss-edma/blob/c3po-tag-8021q/README.ipq50xx.md）しているが、**WG2600HP/IPQ8064での再現は未確認**。
- 作業ブランチ `wg2600hp-qca8021q-backport-isolated-20261031`。通常作業ブランチ `wg2600hp-nss-gmac-no-phy-20261031` へ未検証の候補をマージしない。default branchは古い参照版。
- 5条件を厳守: 開始時既存記録確認／修正前ブート～通信横断照合／修正後後続影響・回帰／ビルド前に根拠記録・問題があればビルド禁止／ビルド後実機RAM起動・IPv4とNSS加速実証。
- **正常動作の誤認禁止**: 以前のRAM版ではLAN→WAN IPv4通信PASS、NSS IPv4加速FAIL（ECM `FAIL_RULE=-2`, `lan1/br-lan/wan` NSS AE=-1、`ipv4_create_requests=0`）。固定IPIP6は未確認。
- **2026-10-26成功版原本 `0031.patch` / `9999-wg2600hp-0031-nss-dsa-ipv4-ram-tested.patch` は現在ない**。元パッチの回収を開発継続の前提としない。復元されたら追加比較する。
- **旧パッチ追跡証拠（過去セッションの記録、今の実体検証ではない）**: 2026-10-25の保存先 `/home/owner/wg2600hp-25.12.5-nss/0031-two-cpu-hpoCalVD/0031.patch`、当時記録されたSHA256 `0338bd1ec94a1428031d5ab9070dd31839db1d80ade16ea5fff842b697205906`。ECM成功パッチの過去保存先 `/home/owner/wg2600hp-25.12.5-nss/openwrt-25.12.5/package/kernel/qca-nss-ecm/patches/9999-wg2600hp-0031-nss-dsa-ipv4-ram-tested.patch`。現実の存在・内容は未確認であり、「仮想環境に発見済み」と言わない。
- **GitHub現在の実体照合**: 2026-10-31 隔離ブランチHEAD `5102a99f5482707c7eb8a16d537e69836c5766fd` のGitツリー全 **12,642エントリ**を再帰取得（`truncated=false`）し、上記 `0031.patch` と `9999-wg2600hp-0031-nss-dsa-ipv4-ram-tested.patch` の原本は**このブランチに存在しない**と確認。GitHubの他のコミット/ローカル上まで不在と断定しない。
- **2026-10-31実際に読み取ったZIP**: `WG2600HP-IPQ8064-25.12.6-NSS(20261031-132923).zip`, SHA256 `41586c4a4310af3fe5848810cf2b413bc8610bd1c9f414dce5510b456ceae929`。内容は既存25.12.6 initramfs uImage、squashfs sysupgrade、SHA256SUMS、manifest、resolved.config の5エントリ。**修正版の新規ビルドではない。再提出不要。** GitHubにはハッシュ記録のみでバイナリは保存していない。

## 現在保存されている候補と検証

- `target/linux/generic/pending-6.12/760-01-net-dsa-qca8k-8021q-tagger-stage.patch`: staged kernel tagger。
- `backports/staging/760-02-net-dsa-qca8k-8021q-driver-6.12-CANDIDATE.patch`: QCA8K switch / management rollback 修正版、**stagingのみ**。リバースタグ切替の途中失敗復旧が不十分。
- `backports/staging/760-03-net-dsa-8021q-dual-cpu-vlan-isolation-6.12.patch`: CPU0/CPU6のVLAN分離、stagingのみ。
- `backports/staging/760-04-ecm-8021q-conduit-pinned-CANDIDATE.patch` / `760-05-ecm-nss-vlan-dsa-guards-pinned-CANDIDATE.patch`: pinned ECM `9acdcb05` 用、stagingのみ・OpenWrt固有400/401パッチ後未統合。
- 公開 Linux `gregkh/linux v6.12.112` 該当7ソースへ、既存711/712 + 新760-01/02/03を順次 **unified-diff文脈リプレイ 43/43件一致**。これはパッチ適用文脈の一致のみで**コンパイル・起動・回帰の証明ではない**。
- `tests/wg2600hp_qca8k_rollback_static.py`: 文字列・パッチハンクの静的チェックを追加済み。GitHub追加後の**実Python実行は未確認**。

## 2026-10-31 Wi-Fi NSS開発のコード証拠

- `diff-wg2600hp-nss` には `CONFIG_NSS_DRV_WIFI_ENABLE=y` と `CONFIG_PACKAGE_MAC80211_NSS_SUPPORT=y`。`package/kernel/mac80211/patches/subsys/990-mac80211-add-nss-redirect-support.patch` は `nss_virt_if_create_sync` と `nss_virt_if_tx_buf` を含む。DTSはPCIe Wi-Fi 2台と両方のNVMEMキャリブレーションを記述。**これはソース存在・ビルド選択のみの根拠で、実機Wi-Fi NSS加速PASSではない。**
- `package/kernel/mac80211/Makefile` はNSS enableの生成フラグを持つ一方、`PKG_CONFIG_DEPENDS` から `CONFIG_PACKAGE_MAC80211_NSS_SUPPORT` が抜けていた。`include/package.mk` は `PKG_CONFIG_DEPENDS` から構成スタンプを生成する。隔離ブランチ commit `be60ea7f698eb2b74e1fdd0b97a930ae2ba84eb8` で依存を追加。
- `scripts/wg2600hp_cross_audit.py` にWi-Fi NSS選択、キャッシュ再構成依存、redirectパッチ、PCIeの2無線を検査する5項目を追加。commit `c7c89303d75db9df606d7ded1b0cf72c73724aac`。`tests/test_wg2600hp_cross_audit.py` に2つの異常系を追加・修正（commits `84c46818...`, `2c07edcb2bb0cfb510420145aa01404cb9dba7c5`）。関連7ファイルをGitHub読み戻し、**11/11 JS静的照合**（2つの負例を含む）PASS。**Pythonスクリプト実行・mac80211実ビルド・無線接続・NSS redirect計測は未実施。**
- 既存5ゲートのビルド禁止を尊重。未解決の有線DSA/ECM、Wi-Fi NSS redirect起動・カウンタ測定、固定IPIP6の課題を残す。

## 次の作業 (ユーザーに同じ説明やファイルを求めず着手)

1. 隔離候補 `760-02` の 8021Q→QCA 失敗時のロールバックを検討し、元Linux 6.12.112の関数順、GMAC/DSA CPU0・6/port FDB/VLAN/ECMデータパスまで横断照合。
2. **追加のユーザー用VLANなし**で、既存のQCAタグ維持案と、NSSが解析可能と報告される内部8021Qタグ案を比較する。前者はNSSパケット解析とポート識別を証明すること。後者は起動時タグ変更のdown/up順序、CPU0/6両conduit、WAN DHCP、LANブリッジ、変更失敗時の回復を検証すること。未検証のタグ切替を稼働機に適用しない。
3. `760-04/05` を pinned ECM + 既存OpenWrtパッチ適用順に照合。ECMが`lan1`と`wan`から正しいNSS GMAC IFへ階層を構築すること、QCA8337の**LAN/WAN間のパケット分離**が保たれることを検証。ユーザー用VLAN設定は要求しない。
4. 残った問題を根拠付きで台帳へ記録。未解決の間 **G3 FAIL、新規ビルド不可**。解決後に隔離ビルドとRAM起動でIPv4/NSSを測定。

**作業方針**: あらゆる作業停止をユーザーの指示なしに宣言しない。復元作業は並行タスク。差分や記録はGitHubへ保存して検証可能にする。結果のない「進めます」だけで終えない。
