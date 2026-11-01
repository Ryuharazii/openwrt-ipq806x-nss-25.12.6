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

## Wi-Fi NSS redirect 実コード修正（2026-10-31 追加）

- **具体的な原因**: mac80211 NSS RX redirectの `skb_push(skb, ETH_HLEN)` 後、`nss_virt_if_tx_buf()` でエラーとなって通常処理に戻る際にデータ位置を復元していなかった。
- **コード修正実施**: 隔離ブランチ commit `309210e2e23e7eb01e6f101aa70861bbbaff5b69`、headroom不足時はNSSを呼ばず通常経路へ、NSS送信失敗時は `skb_pull(skb, ETH_HLEN)` 後に通常経路へ。成功経路は従来のまま。mac80211 `990` パッチ13ハンクの行数・オフセットを確認。
- **回帰検証**: cross auditと2つの負例を追加（`a13a3a3`, `b25a6dd`）、GitHub取得したソースで JS静的照合 **6/6 PASS**。Python実行・patch実適用・コンパイル・Wi-Fi/NSS実機計測は未完。**G3 FAILのままでビルド・書込み禁止**。
- **次の優先順位**: pinned NSS driverのpacket ownership契約とmac80211 6.18.55バックポート適合性を追加確認し、DSA/ECM/起動時タグ切替と同時にWi-Fiを検証すること。新規VLANユーザー設定不要。

## 2026-11-01 Wi-Fi NSS TX QoS線形ヘッダー検査（最新修正）

- **隔離版の実変更**: commit `2ecd8c2536a77ba2e7ad81a9e0758207b4ea45b6`。mac80211 NSS `ieee80211_xmit_nss_fixup()` が送信前の短い／非線形skbでEthernet/IPv4/IPv6ヘッダーへ無条件アクセスしないよう `skb_headlen` の長さ検査を追加。`990-mac80211-add-nss-redirect-support.patch` に保存、通常作業ブランチには未統合。
- **回帰対策**: cross_auditに正負検査（commit `36f5d845...`）、unittest異常ケース2件（`ef054fe505...`）。GitHub読戻し後、パッチ13ハンクの構造一致、JavaScriptで正常ケース1・境界検査欠落3ケースの判定を確認。**Python unittest / ARMコンパイル / Wi-Fi実機試験は未実施**。
- **未解決を維持**: 参照した公開NSSドライバ実装は固定版 `3cfb9f43` と同一と証明できない。SKB所有権・mac80211 6.18.55バックポートへの実パッチ適用、Wi-Fi NSS高速化測定、有線DSA/ECM、固定IPIP6はいずれも未完。**G3 FAIL／ビルド禁止**。先に固定版ドライバのAPI契約を照合する。

## 2026-11-01 Wi-Fi NSSを実イメージで照合（最新）

- 提供済み `WG2600HP-IPQ8064-25.12.6-NSS(20261031-134853).zip` のresolved.configとmanifestを実際に読み、無線NSS・ath10k-ct・mac80211・ファームウェア・wpadの**10/10条件PASS**。FW削除・Wi-Fi NSS無効化の2負例をローカルで検出。**Wi-Fi NSS加速実機PASSではない**。
- `mac80211 6.18.55` のLinux元ソースに、隔離版Wi-Fi NSSパッチのLinux対象**12/12ハンク文脈が一致**しメモリ上で展開できることを確認。`local-symbols`（backports由来）とOpenWrt先行パッチ適用後の実ソースはまだ未検証。コマンド `patch --dry-run` やARMコンパイルは未実施。
- 画像ゲートにWi-Fi NSS設定とファームウェアを含む5設定＋5パッケージ条件、WG2600HP専用manifest選択を追加（`1456a6a...`）。`diff-wg2600hp-nss` にath10k-ct/mac80211の明示選択追加（`60e4c60...`）。cross-auditと3負例を拡張し、GitHub再取得のソース静的照合**14/14 PASS**。追記台帳 commit `83df4691bd7e456ce7fb29fbf464225e83bee9d2`。
- **実ビルド・Wi-Fi接続・NSSパケット転送/統計値の検証は未実施、G3 FAIL維持**。有線IPv4 NSS・Wi-Fi NSS・固定IPIP6 NSSの完成目標は変更なし。ユーザーへの再アップロード要求は不要。

## 2026-11-01 Wi-Fi NSSを実バイナリで検証（最重要引継ぎ）

- ユーザー既存ZIP `WG2600HP-IPQ8064-25.12.6-NSS(20261031-134853).zip` から実uImage→内蔵XZカーネル→newc initramfsを展開し、ARM ELF `mac80211.ko` と `qca-nss-drv.ko` を直接検査。**mac80211からNSS仮想IFの4 APIがimportされ、NSS drv側は4 APIを `__ksymtab_strings` にexport**。mac80211のmodinfoにも `depends=qca-nss-drv` がある。ath10k_core/pciとQCA99X0 fw・boardも収録。実行10/10項目PASS＋依存照合PASS。実ファームのWi-Fi NSS redirect組込みを確認、**実機でWi-Fi NSS高速化成功と扱わない**。
- 実データへ異常注入して3ケース（無線fw欠落、NSS export名変更、uImage CRC破損）を想定どおりFAIL検出。検査ロジックを `scripts/wg2600hp_verify_wifi_nss_binary.py` としてGitHub隔離ブランチへ追加（`098ba94`, `cd42c3c`）、イメージゲートに接続（`0c5c9d1`）。前段ソース監査と欠落検出テストも追加（`6043cfe`, `911d531`）。
- SHA256 ZIP: `41586c4a4310af3fe5848810cf2b413bc8610bd1c9f414dce5510b456ceae929`。詳細台帳 `WG2600HP-EXECUTION-GATES.md`。
- **残作業**: Wi-Fiの2.4/5GHz接続、NSS redirectの実機カウンタ増分、NSS IPv4 ECM/DSA問題、固定IPIP6。新規修正をコンパイルしたわけではない。**G3 FAIL、新規ビルド/書き込みは未実施**。

## 2026-11-01 Wi-Fi NSSバイナリ検査：保存済みコードを本当に実行

- GitHub隔離版 `scripts/wg2600hp_verify_wifi_nss_binary.py`（実行時blob `7b4c1cf9...`）をユーザー既存ZIP `WG2600HP-IPQ8064-25.12.6-NSS(20261031-134853).zip` に対して実行、**実バイナリ11/11 PASS、正常1＋故障注入6のPythonテスト7/7 PASS**。
- アーキテクチャとカーネル版を誤検出しないよう、4つの `.ko` 全部にARM ELF32/6.12.112の検査を追加（`f234651bc5af7193099e982fbfa277e118d010c0`）、更新コードとGitHub読戻しはblob `8974cf86f50b31746d12e5e718ee8014c3d80507` で一致。更新後も実ZIPでPASS。
- synthetic XZ/newc/uImageで **Python unittest 8/8 PASS**、GitHubの `tests/test_wg2600hp_wifi_nss_binary.py`（`149ee7a`）へ保存。手動CIのpreflightへ登録（`d807fbb`）。証拠は `WG2600HP-EXECUTION-GATES.md` の2026-11-01項目。
- **完成ではない**: 新ファームのARMビルド、RAM起動、Wi-Fi NSSオフロード速度、ECM/DSA有線NSS、固定IPIP6 NSSは未解決。**G3 FAIL**。新規CIビルド・書込みは実施していない。これらの経緯は再説明不要。

## 次の作業 (ユーザーに同じ説明やファイルを求めず着手)

1. 隔離候補 `760-02` の 8021Q→QCA 失敗時のロールバックを検討し、元Linux 6.12.112の関数順、GMAC/DSA CPU0・6/port FDB/VLAN/ECMデータパスまで横断照合。
2. **追加のユーザー用VLANなし**で、既存のQCAタグ維持案と、NSSが解析可能と報告される内部8021Qタグ案を比較する。前者はNSSパケット解析とポート識別を証明すること。後者は起動時タグ変更のdown/up順序、CPU0/6両conduit、WAN DHCP、LANブリッジ、変更失敗時の回復を検証すること。未検証のタグ切替を稼働機に適用しない。
3. `760-04/05` を pinned ECM + 既存OpenWrtパッチ適用順に照合。ECMが`lan1`と`wan`から正しいNSS GMAC IFへ階層を構築すること、QCA8337の**LAN/WAN間のパケット分離**が保たれることを検証。ユーザー用VLAN設定は要求しない。
4. 残った問題を根拠付きで台帳へ記録。未解決の間 **G3 FAIL、新規ビルド不可**。解決後に隔離ビルドとRAM起動でIPv4/NSSを測定。

**作業方針**: あらゆる作業停止をユーザーの指示なしに宣言しない。復元作業は並行タスク。差分や記録はGitHubへ保存して検証可能にする。結果のない「進めます」だけで終えない。

## 2026-11-01 作業再開基準（2026-11-01 実ZIP横断確認）

- 直近の修正済み隔離候補 `760-02`（commit `19b1c02`）と `760-07`（commit `356d66f`）は **未ビルド・未統合**。実際にLinux v6.12.112既存711/712パッチの後でDSA修正版のunified-diff文脈39/39が一致したが、回帰・実機合格ではない。
- 今回、11月1日ZIPの `qca-nss-tunipip6.ko` を `llvm-objdump` で実解析し、`ARPHRD_TUNNEL6` の `NETDEV_UP/NETDEV_DOWN` 分岐を確認。NSS/GMAC/tunipip6のmodule読込み設定、ECM UCI defaultsからNSS選択・S96起動への実ファイル経路も確認済み。証拠を `WG2600HP-EXECUTION-GATES.md` commit `0bf1e749ebb9f5898784c045963b9863b54e8022` に記録。
- **振り出しに戻らない**: 通信できる旧ファームの `MAC80211_NSS_SUPPORT`、`TUNIPIP6`、DTBハイフン・アンダーバー問題を再調査対象にしない。組込みは確認済み、必要なのは**有線ECM/DSA NSS IFマッピング・Wi-Fi NSS redirectの実パケット・固定IPIP6 NSS FW ACKと統計増分の証明**。
- **未通過**: 電源投入～U-Boot全ログ、隔離変更後の下流回帰、実ARMコンパイル、新RAM起動/実機高速化。**G1/G2未完了、G3 FAIL、ビルド不可**。完成宣言をしない。次は既存差分の統合前条件を網羅してから最小変更・回帰検証へ進む。ユーザーに以前の出力・ZIPの再説明を求めない。

## 2026-11-01 第21セッション追記：隔離DSA失敗復旧候補を新規保存

- `760-08-net-dsa-8021q-prefix-unwind-6.12-CANDIDATE.patch`（commit `42771824`）: tag_8021q登録途中失敗で成功済みのポートのみ逆順解放し、RX VLANフィルター登録エラーを確認。元Linux v6.12.112→760-03→760-06→760-08の**メモリ上差分再適用一致**。簡易モデル6件一致。**実カーネル未実行**。
- `760-09-net-dsa-qca8k-bridge-join-unwind-6.12-CANDIDATE.patch`（commit `bee214fa`）: DSA bridge JOIN通知失敗時のQCA8337ポートmembership復元を試行。元Linux→711-01→760-02→760-09の**メモリ上差分再適用一致**。MDIO再失敗時には残留リスク。
- **次はこれらの局所結果を全経路PASSと誤認しない**。`dsa_switch_tag_8021q_vlan_add` 複数ポート途中失敗の部分復旧、bridge joinのstandalone VLAN削除エラー、CPU0/6 WAN/LAN分離、ECM pinned 760-04/05、NSS実機を横断評価。現状 **G1/G2未確認、G3 FAIL。新ビルド/実機書込み禁止**。

## 2026-11-01 VLAN要求に関する最優先制約と横断確認

- **ユーザーが繰り返し指定した制約**: VLANの追加を求めない。LAN/WAN既存設定を維持する。「はい」で継続するときに同じ条件を聞き直さない。直近の760-08/09を含む8021Q/DSA候補は隔離保留で、本統合・ビルド・書込みを行わない。単なる局所修正PASSを全起動・NSS高速化PASSと表現しない。
- **実際に照合した基本経路**: Linux v6.12.112 `drivers/net/dsa/qca/qca8k-8xxx.c` の `qca8k_get_tag_protocol()` は標準 `DSA_TAG_PROTO_QCA` を返す。`drivers/net/dsa/qca/qca8k-common.c` の `qca8k_update_port_member()` は `QCA8K_PORT_LOOKUP_CTRL` のポートmembershipを操作し、ブリッジjoin/leaveに使われる。つまりswitchのポート間到達可否制御はユーザー用VLANを新設せず検討できる。ただし**NSSパケット解析対応は別の課題**。
- **現状の確定した阻害**: 旧RAM版の `lan1 / br-lan / wan` のAE IF番号が-1、ECM `FAIL_RULE=-2`、NSS IPv4 CREATE要求0。原因候補を見ずにAE番号をGMACに直接書き換えるのは不可。NSSがQCAヘッダを解析できると未検証のまま決めつけない。
- **外部事例は別機種**: IPQ5018/QCA8337向けの公開実装 `kuncy7/openwrt-nss-edma/README.ipq50xx.md` は、NSSによるQCA 2バイトヘッダの解釈困難を指摘。ただしWG2600HP/IPQ8064での実証ではない。現機種向けのデータパスをクロス確認する必要がある。
- **ECM候補の適用順の事実確認**: 実packageパッチ名は `400-kernel-6.12-support.patch` と `401-kernel-6.12-drop-sysctl-sentinels.patch`。隔離 `760-04/05` は未統合・未コンパイル、正しいNSS IF・WAN/LAN分離未実証。標準ECM variantのMakefileには `ECM_INTERFACE_VLAN_ENABLE=y` があるが、それをユーザー設定へのVLAN追加根拠にしてはならない。
- **次の順序**: 既存のQCA8337二CPUポート＋GMAC eth0/eth1＋タグ無し運用可否を、旧実機通信経路、NSS FWのヘッダ受理、ECM IF解決、LAN/WAN分離と照合。切替に伴うDSA解除/復旧、PHY、起動順も確認。根拠が不足する間 G1/G2未確認・G3 FAIL、仮想フルブート未実施、ARMビルド・実機書込みなし。

## 2026-11-01 追加横断確認：既存DSA conduit構成を変更せずECM/NSS障害に集中

- **既存設定が存在することをGitHubで再確認**：`target/linux/ipq806x/base-files/etc/board.d/02_network` の `nec,wg2600hp)` は `wan→eth0`、`lan1/lan2/lan3/lan4→eth1` を `ucidef_set_network_device_conduit` で指定。対象DTSはQCA8337 CPU port0→GMAC1、CPU port6→GMAC2。これは**設定ソースにあることの証明**であって起動後の実際の所属確認ではない。**追加VLAN設定もネットワーク設定変更も不要とする条件を維持**。
- **起動段階の区別**：Linux v6.12.112 `net/dsa/dsa.c` の `dsa_tree_setup_cpu_ports()` は初期状態で最初のローカルCPU portを各user portに設定する。一方、既存OpenWrt 711-03は`.port_change_conduit = qca8k_port_change_master`を実装し、上記board.dの設定により起動後の再割当てを意図している。`ip -d link show dev lan1` / `... wan` の実機出力で反映確認するまでは**実機PASSとしない**。
- **既存対策の重複防止**：OpenWrt 711-02は両CPUポートへの未知フレームfloodingを有効にする既存パッチ。711-03は再割当て時のswitch接続更新を持つ。2026年8月の[RFC v2 4/6](https://lkml.iu.edu/2608.0/00861.html)は起動時の各user port→割当CPU portに応じたハードウェア初期化を提案しているが、**WG2600HPへの直接適用可否、既存711-02/03との重複と実機効果は未検証**。いきなり新たな修正を積まない。
- **ECM stagingの明確な制限**：`backports/staging/760-04-ecm-8021q-conduit-pinned-CANDIDATE.patch`は`!dp->ds->tag_8021q_ctx`ならconduit取得をNULLで終了するため、**現行QCAタガーのままではこの候補を適用してもDSA user→NSS IF解決問題を修正できない**。本統合しない。既存RAM実測の`AE IF=-1`、`FAIL_RULE=-2`、NSS CREATE=0を優先する。
- **新規外部情報との境界**：IPQ5018/QCA8337の公開事例ではQCAの2BヘッダをNSSが解析できない報告あり。ただしSoC・DPが異なり**WG2600HP/IPQ8064の実証ではない**。QCAヘッダとNSS FW処理の互換性、LAN/WAN独立性、MTU、NSSルール生成を機種固有の根拠で横断確認する必要がある。
- **このセッションの確認の種類**：GitHub実ファイル5件とLinux v6.12.112のDSAソース・公的文書の照合、出現条件7件の静的チェックのみ。**修正/ARMビルド/QEMUで電源投入から起動完了/実機RAM起動/通信・オフロード実測は未実施**。G1/G2未確認、G3 FAILを維持。次はECM pinnedの階層構築とNSS GMAC IFへ対応づける経路を、QCAタグ互換性と一体で照合する。

## 2026-11-01 NSS物理IF番号とQCAフレームを分けた横断監査

- **ソース上で確認した現状**: WG2600HPのDTS CPU0→GMAC1 / CPU6→GMAC2。 `base-files/etc/board.d/02_network` はWAN→eth0、LAN1～4→eth1を設定。現行Linux 6.12.112 `net/dsa/tag_qca.c` はEthernetフレームに独自QCAヘッダを挿入・除去し、`include/linux/dsa/tag_qca.h` の `QCA_HDR_LEN=2`。QCA8K標準taggerの現状は変更しない。
- **NSS IF解決の参照実装（同系列だが現行pinと同一性は未確認）**: 旧IPQ806x公開実装 `Getnear/R7800` の `package/qca-nss-drv/src/nss_cmn.c` `nss_cmn_get_interface_number_by_dev` は`nss_top_main.subsys_dp_register[i].ndev`と要求`net_device*`の**ポインタ一致**でIF番号を返し、一致しなければ-1。`src/nss_data_plane.c` は`nss_gmac_get_netdev_by_macid(if_num)`から物理GMACのnetdevを取得し、`subsys_dp_register[if_num].ndev = netdev`へ登録する。リンク: https://github.com/Getnear/R7800/blob/508b1eb1eff3a92f6ecf3c2c5a08ffa82065ce61/package/qca-nss-drv/src/nss_cmn.c 、https://github.com/Getnear/R7800/blob/508b1eb1eff3a92f6ecf3c2c5a08ffa82065ce61/package/qca-nss-drv/src/nss_data_plane.c 。
- **現行実装との相違の留保**: 作業版 `package/qca-nss/qca-nss-drv/Makefile` は`PKG_SOURCE_VERSION:=3cfb9f43`、GMACは`171767947467662f2407d0cfff26dfb136c3fb4a`。**この正確なpinのソース実体はこの監査で取得できていない**ので上記参照実装を「WG2600HPで実行されたコード」とは断定しない。
- **実機結果への整合性**: 既存RAM版`ecm_dump.sh`で`lan1/br-lan/wan AE IF=-1`、`FAIL_RULE=-2`、`NSS IPv4 CREATE=0`。ECM pinned `9acdcb05` がNSS IF番号を要求する直接阻害との整合は強いが、IF登録先と各フロー階層を**実機と現行pinソースで独立確認すること**。手当たり次第の番号1/2への置換は禁止。
- **第2の独立した障害仮説**: DSAの標準QCAタグ（2バイト）がNSS内部のL3解釈に対応するか未実証。他SoCの`kuncy7/openwrt-nss-edma/README.ipq50xx.md`では不対応の報告があるが、**IPQ5018の記述であり、IPQ8064の検証結果ではない**。ECM mappingを解決してもQCAタグでNSSパケット処理が成立するとは断定できない。
- **既に存在するGMAC/DSA対応**: `package/qca-nss/qca-nss-gmac/patches/09-dsa-conduit-device-tree-node.patch`が`netdev->dev.of_node = pdev->dev.of_node`を設定する。OpenWrt 711-03には`.port_change_conduit`。現行の`wan→eth0`/`lan→eth1`設定も存在するため、これらを無視して新たな別構成に置き換えない。
- **次の横断確認対象**: 現行pinの`nss_cmn_get_interface_number_by_dev`とデータプレーン登録、ECM hierarchical iface resolution、QCAヘッダのNSSファームウェア側解釈・`eth_rx_unknown_l3_protocol`実カウンター、CPU0/6のL2分離、IPv4/固定IPIP6/Wi-Fiの相互影響。追加VLAN設定を要求しない。障害が2つある可能性を踏まえ、局所変更だけでPASSにしない。
- **判定**: 今回はGitHub作業版/公式Linux6.12.112/公開NSS類似実装のソース横断照合のみ。現行pinソース直接比較・QEMU/電源投入→起動完了・ARMコンパイル・新RAM実機試験・NSS高速化の検証は未実施。G1/G2未完了、G3 FAIL。**新パッチ統合・ビルド・フラッシュなし**。
