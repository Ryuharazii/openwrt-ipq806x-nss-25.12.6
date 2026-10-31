# WG2600HP（IPQ8064）OpenWrt 25.12.6 NSS — 作業規則・実証記録

**この文書を、新しいセッション・修正・ビルド開始時に必ず先に読む。**
対象は NEC Aterm **WG2600HP / qcom,ipq8064**。WG2600HP3 / ipq8062 は別機種であり、正常動作版は比較・検証資料に限定する。

## 絶対条件（ユーザー確定・2026-10-31）

1. **作業開始時**：前回の進捗・未解決問題・検証結果を確認する。
2. **修正前**：電源投入から通信成立まで、関連する処理を横断確認する。
3. **修正後**：後続処理への影響と回帰不具合を確認する。
4. **ビルド前**：検証結果と根拠を記録する。未解決の問題があればビルドしない。
5. **ビルド後**：RAM起動で実機検証する。IPv4通信とNSS動作を確認するまで完成と宣言しない。

各工程に合格条件を設け、証拠のないPASSを禁止する。
失敗時は原因を横断調査し、同じ失敗を防ぐ仕組みを追加する。
セッションが変わっても、この規則を継続する。

## 記録規則

- 判定は **PASS / FAIL / 未確認** の3種類。推測・コードが存在する・CIが成功しただけでは実機 PASS にしない。
- PASS には、対象コミット・機種・証拠（ソース行、ログ、DTB、テスト結果など）・日付を記載する。証拠のない項目は未確認とする。
- **横断確認の対象**：電源投入 / Boot ROM / U-Boot / カーネル起動 / DTS・実際のDTB / NSS firmware load / GMAC eth0・eth1 / QCA8337 DSA CPU port 0・6 / WAN・LAN / DHCP・IPv4 routing / 実パケット通信 / ECM・NSS offload / 固定IPIP6（最終目標）。
- 新たな修正の前に、正常動作版・現行コード・公開実装・既存実機ログを照合し、修正箇所だけでなく後続経路への影響を確認する。
- 自動実行による無駄なGitHub Actions負荷をかけない。ファームビルドは必要性・前段ゲートの証拠を確認してから**手動起動**する。
- 実機書き込みの前に、適切な安全なRAM起動確認を優先する。未検証ファームを完成品として案内しない。
- 手詰まり時は局所修正を繰り返さず、横断調査へ戻る。

## 現在の検証台帳（2026-10-31 作業開始基準）

| ゲート | 状態 | 根拠・未解決事項 |
| --- | --- | --- |
| G0: 対象・履歴・失敗事項を把握 | PASS（記録範囲） | WG2600HP / IPQ8064 / 25.12.6。旧RAM起動はログイン到達だがQCA8K DSA probe失敗。 |
| G1: 起動からIPv4まで全経路を横断照合 | **未確認（RAM起動～WAN DHCP・LAN構成の実機動作を確認）** | 2026-10-31、WG2600HP / 25.12.6 / kernel 6.12.112 / initramfsでログイン。NSS core 0/1 boot successfully、GMAC1/2 eth0/eth1初期化、QCA8337両CPU固定リンク 1Gbps、`DSA: tree 0 setup`、wan/lan1 1Gbpsリンク。WAN DHCP割当、LANアドレスとdefault routeを実機ログで確認。2026-10-31 WANからゲートウェイへICMP 3/3（0% loss）、外部IPv4 1.1.1.1へICMP 3/3（0% loss）、openwrt.org DNS A/AAAA応答を実機確認。2026-10-31 LAN側Ubuntu有線 eno1 からの経路 `via [WG2600HP LAN] dev eno1` を確認し、LANゲートウェイping 3/3、外部IPv4 1.1.1.1へのping 3/3、損失0%でLAN→WAN IPv4実パケット転送を実証。Boot ROM/U-Bootの全ログ、NSS加速、MTU処理は未確認。 |
| G2: 修正後の後続処理・回帰を照合 | **未確認（DSA起動障害の解消を実機確認）** | `of_get_phy_mode()` 戻り値破壊パッチ削除（6ee5909）・GMAC PHY無効化修正（ce2bedf）の後、旧ログの `CPU port 0 lacks required "phy-mode"` / probe `-22` は観測されず、`DSA: tree 0 setup` と全5ユーザーポートのPHY検出を確認。一方で `eth0/eth1: error -22 setting MTU to 1502`、`qca8k ... nonfatal error -34` が残り、実データ通信時の影響は未判定。 |
| G3: ビルド前の承認と証拠記録 | **未確認** | 旧ビルド #41178270721 は規則整備前に開始。現在のゲートを遡及してPASS扱いしない。新たなビルド開始禁止。 |
| G4: 修正版ファームのビルド成功・成果物検証 | **未確認（ビルド成功・基本検査のみPASS）** | 2026-10-31 GitHub Actions [#41178270721](https://github.com/Ryuharazii/openwrt-ipq806x-nss-25.12.6/actions/runs/41178270721) は SUCCESS。initramfs-uImage 約8.5MiB・sysupgrade.bin 9,306,379 bytes を生成。旧 image gate の実DTB検査で NSS GMAC x2、NSS core x2、QCA8337・DSA port 0～6 のラベル、GMAC fixed-linkをPASS。アップロードZIP SHA256=41586c4a4310af3fe5848810cf2b413bc8610bd1c9f414dce5510b456ceae929。ただしそのビルド時点の検査スクリプトは **実DTBのDSA CPU ethernet phandle、CPU phy-mode、CPU fixed-link、ユーザPHYの関連付け** まで検査せず、強化版チェックはこのイメージに未実施。実機RAM起動も未確認。 |
| G5: WG2600HP RAM起動完了とWAN/LAN IPv4実通信 | **PASS（RAM起動・DSA・WAN IPv4・DNS・LAN→WAN IPv4疎通、LAN側MTU1500）／NSS・経路全体のMTU未確認** | 2026-10-31 実機出力：`root@OpenWrt:~#`、`rootfs_type=initramfs`、`ip -br link` eth0/eth1 UP、wan@eth0 UP、lan1@eth1 UP、`br-lan` UP、`ifstatus wan` DHCP up、`ifstatus lan` up、IPv4 default route確認。WAN側からゲートウェイと外部IPv4へのping各3/3応答（損失0%）、DNSのA/AAAA回答、WANのRX/TX errors=0を確認。LAN側Ubuntu eno1の経路がWG2600HPのLAN側IPであることを確認して外部IPv4へping 3/3成功（損失0%）。Ubuntu `eno1` からWG2600HPのLANゲートウェイへDF設定、ICMP payload1472（IPv4合計1500 bytes）でping 3/3、損失0%を確認。LAN→WAN経路の1500バイト DF pingは失敗し、上流ゲートウェイから `Frag needed and DF set (mtu = 1460)` を受信。2026-10-31 Ubuntu `eno1` → WG2600HP → 1.1.1.1 のDF設定、ICMP payload1432（IPv4全長1460バイト）で3/3応答、損失0%を確認。NSS高速化、TCP/UDP転送速度は未確認。公開台帳には内部IP/MACを記録しない。 |
| G6: ECM/NSS IPv4加速と固定IPIP6オフロード実測 | **未確認** | 2026-10-31 新RAM起動で NSS core 0/1 boot successfully、`/sys/kernel/debug/qca-nss-drv/stats/` に ipv4/ipv6/gmac が存在。ただし `ecm_nss_ipv4/accelerated_count=0`（LAN→WAN ICMP通信成功後の実機値。TCP/UDP長時間転送中の計測なしで加速不能とは判断しない）。`/sys/kernel/debug/qca-nss-drv/stats/ipv4` はファイルでありディレクトリではないため、`ls ipv4/` は `Not a directory`。ECMカウンタファイル群の存在を実機で確認。`tunipip6` 統計未表示。NSS FWのIPIP6機能・動的IF起動/停止・実オフロード未実証。 |

### ゲート通過条件

- **G1合格**：上記全経路のコード・DTB・構成・物理接続を照合し、ログ根拠と未解決点を記録。実機でしか判定できない項目は「未確認」と明示。
- **G2合格**：修正の適用箇所と後続・回帰影響を具体的に検証・記録。検証のない PASS 禁止。
- **G3合格**：G1/G2の未解決問題を解消し、証拠を残してから必要なビルドのみ開始。既存進行中ビルドは成果の参考にはできるが、G1/G2合格の代用にしない。
- **G4合格**：ファーム生成成功、対象機種・ビルド設定・ハッシュ・組み込みDTB・画像形式が適切なことを証拠で確認。
- **G5合格**：WG2600HP実機のRAM起動でログイン・DSA probe・eth0/eth1・wan/lan・IPv4送受信とルートが成立するログを確認。
- **G6合格**：NSS/ECMのカウンタと速度測定を含め、IPv4と固定IPIP6の実加速を個別に証明。対象不一致や推測で補わない。

## 次回開始時の必須行動

1. この文書と直近の作業コミット・GitHub Actionsを確認する。
2. 未確認・FAILを列挙し、必要な横断調査を先に実施する。
3. 結果と証拠を本台帳へ更新してから次ゲートを判断する。
4. ゲートが満たされなければ、その先の工程を実行しない。特にビルドや実機書き込みを進めない。

## 2026-10-31 修正版RAM起動の実機所見（追加、未解決事項あり）

- PASS：WG2600HP / IPQ8064 / OpenWrt NSS 25.12.6 / kernel 6.12.112 のinitramfs起動、ユーザーシェル到達。
- PASS：NSS 2コア起動、GMAC 2基初期化、DSA QCA8337 `tree 0 setup`、WAN・LAN1物理リンク、WAN DHCP とLANアドレス・デフォルトルート設定。
- 残留ログ：DSA conduit eth0・eth1でMTU=1502設定が `-22`、ポートでMTU更新が `-34`。IPv4データ転送・最大サイズ送信への影響は**未確認**。
- PASS：WAN gatewayへのping 3/3、外部IPv4 1.1.1.1へのping 3/3、DNS応答。WANインターフェースの観測時エラー0。
- PASS：LAN側Ubuntuの有線インターフェース eno1 からWG2600HP LANを経由して外部IPv4 1.1.1.1へ ICMP 3/3、損失0%。ルーティングが `via 192.168.1.1 dev eno1` であることを確認。
- PASS：Ubuntu有線 `eno1` → WG2600HP LANゲートウェイに対して `ping -I eno1 -M do -s 1472 -c 3` 成功 3/3（IPv4全長1500バイト、損失0%、平均RTT1.091ms）。
- FAIL（経路MTU制限）：Ubuntu `eno1` からWG2600HPを経由した `ping -M do -s 1472 -c 3 1.1.1.1` は ICMP echo応答0/3。上流側のゲートウェイから `Frag needed and DF set (mtu = 1460)`、その後ローカル送信時 `Message too long`。LAN側の1500バイトpingはPASSなので、DSAエラーとの因果関係は**未確認**。
- PASS（経路MTU 1460）：Ubuntu `eno1` → WG2600HP → 1.1.1.1 の `ping -M do -s 1432 -c 3` は3/3成功、損失0%、平均RTT20.475ms。直前に全長1500バイトで上流から経路MTU1460通知あり。LAN側MTU1500の正常通信と整合。
- 未確認：DSA MTU設定エラーの最大フレーム影響、LAN→WAN TCP/UDP実転送、ECM/NSS IPv4 accel、固定IPIP6加速。
- NSS IPv4 実機診断：rootシェルでECM IPv4 accelerated_countを読んだ結果0。`stats/ipv4` は統計**ファイル**でありディレクトリではない（`ls .../ipv4/` のエラーは検査コマンド誤りであってドライバ不具合の証拠ではない）。次に統計ファイル本文とTCP/UDP転送中のカウンタ差分を取得する。
- 次の検証は**既存RAM起動した個体で読み取り中心の疎通試験**。追加ビルド・フラッシュ書き込みは禁止。内部IPv4アドレスとMACは公開記録に残さない。

## 2026-10-31 TCP負荷試験の不成立（検証上の失敗）

- Ubuntuの有線経路が `via WG2600HP LAN dev eno1` であることは確認。
- `curl` に指定した `speed.cloudflare.com/__down?bytes=...` は HTTP 403 を返し、ダウンロード本体は 0 バイト。NSS加速の有無は**未判定**とする。403応答自体の短いTCP通信はあり得るが、継続TCP転送の評価には使用しない。
- 原因は未確認のダウンロード先を検証用に指定したこと。次回は提供元の公式テストファイルを採用し、HTTP応答、転送バイト、経路を確認してからECM/NSSカウンタを比較する。

## 2026-10-31 NSS IPv4 TCP試験結果（未解決）

- LAN側UbuntuからWG2600HP経由の宛先アドレス経路を確認した上で、Hetzner HTTPS Rangeを実行。HTTP 206、8,388,608 bytesのTCPダウンロードは成功（前回のCloudflare HTTP 403は不成立として除外）。
- 実機NSS IPv4統計の報告値：`ipv4_rx_pkts=0`、`ipv4_tx_pkts=0`（common/special）、`ipv4_create_requests=0`、`ipv4_hash_hits=0`。先行測定ではECM IPv4 `accelerated_count=0`、TCP/UDP加速数も0。
- **判定：NSS IPv4オフロード未実証。原因は未確定。** ルール作成要求が0のため、ECMフロントエンド停止、ECMのフロー認識、設定、DSA→NSSインターフェースマッピング、フロー適格性を優先調査。カウンタの標本時刻とTCP転送中の同時測定は完全には示されていないため、NSS故障とは断定しない。
- ソース照合：`qca-nss-ecm.init` は `/sys/kernel/debug/ecm/front_end_ipv4_stop`、`ecm.global.acceleration_engine` を使用、`ecm_db` の接続数は `/sys/kernel/debug/ecm/ecm_db/connection_count` から確認できる。ECM起動状態と接続DBを先に検証し、原因不明の再ビルドを行わない。

## 2026-10-31 過去のNSS成功条件との横断比較（修正未適用）

- **過去の実機成功記録（25.12.5）**：WG2600HP/IPQ8064で LAN2 から128MiBファイルを5回転送し、NSS IPv4 RX bytes 908425034→1465037652、TX bytes 923331068→1488930978、`ipv4_create_requests` 216→240、`ipv4_create_invalid_interface=0` を記録。別試験で `eth0` のNSS IF=1、`eth1`=2、DSA `wan/lan2/br-lan`=-1。過去ログでは `eth0`・`eth1` ともDSAタグ方式 `qca-8021q` と報告。
- **現行25.12.6リポジトリで確認済み**：WG2600HP DTSはQCA8337のDSA CPUポート0 `gmac1/eth0` と6 `gmac2/eth1` を指定する一方、DTSに `qca-8021q` のタグ指定が見つからない。`target/linux/ipq806x/patches-6.12` の101パッチ名に過去の `999-009`～`999-011` 相当のQCA8K 8021Q/二CPUパッチは見当たらず、`990-0001/0002`にも `qca8k`/DSAタグ改変は見当たらない。
- **要確認・有力な差分**：vanilla Linux 6.12 QCA8Kドライバは原則 `DSA_TAG_PROTO_QCA` を使用し、旧 `qca-8021q` とは異なる。実機が現在 `qca` タグで稼働しているかを要確認。NSSファームウェアのレイヤ3処理やインターフェース識別に影響する**可能性**があるが、今回の `ipv4_create_requests=0` の確定原因とはまだ断言しない。
- **別の有力確認事項**：ECMパッケージの `qca-nss-ecm.init` は `front_end_ipv4_stop` と `ecm.global.acceleration_engine` を参照する。停止フラグ、ECM connection_count、GMAC phys_if/DSA tagを実機で確認する。U-Boot操作はLinux側で指示しない。
- **措置**：現行RAM試験を継続、追加ビルド・書き込み・過去のパッチの無条件移植は行わない。旧正常版との相違を検証してから最小修正を選択。

## 2026-10-31 ECM接続数1の追加実機結果

- 同じHetzner HTTPS Rangeの8,388,608-byteダウンロードは HTTP 206で成功。
- OpenWrtで毎秒測定したECMの25回目の標本として、`ecm_db/connection_count=1`、`ecm_nss_ipv4/tcp_accelerated_count=0` が報告された。**ECMの接続DBは完全なゼロ状態ではない**。
- 他の24回の標本・タイミング・このDB内接続が対象のTCP転送と一致するかは未確認。ECMが当該転送を管理したと断定しない。
- 次はECM state dumpで接続の`can_accel`、`accel_mode`、プロトコル・インターフェースを確認する（ビルド不要）。標本未照合のままDSAタグ方式を原因と決め付けない。

## 2026-10-31 ECM接続数2への増加（追加試験）

- UbuntuからのHetzner HTTPS 8,388,608-byte転送がHTTP 206で再度成功。
- OpenWrt実機の報告では `front_end_ipv4_stop=0`、`ecm_db/connection_count=2`（前の試験報告値1から増加）。
- この2件が当該TCPダウンロードの通信に対応するか、ECM/NSSのどの加速状態にあるかは**未確認**。過去に報告されたNSS IPv4統計は0のままだが、今回の転送と同時測定した新しい統計値はまだ取得していない。
- 次は `ecm_dump.sh ecm_db` の接続状態と `front_end_selection` を読んで原因を絞る。NSS/DSAやECMのコード変更は保留。

## 2026-10-31 ECM状態ダンプの呼び出し誤りと修正

- 実機で `ecm_dump.sh ecm_db` は `exit_code=2`、出力0バイト。`/sys/kernel/debug/ecm/ecm_db/state_dev_major` は存在せず、`/sys/kernel/debug/ecm/ecm_state/state_dev_major` が存在。
- リポジトリの `package/qca-nss/qca-nss-ecm/files/ecm_dump.sh` は **引数なし時に `ecm_state`** を既定使用し、指定モジュールの `state_dev_major` がないと `exit 2` となる。したがってこの試験失敗はECM状態ダンプの不正な引数指定に起因し、NSS/ECMの故障の根拠ではない。
- 次回は実機 `ecm_dump.sh`（引数なし）で `/tmp/ecm-state.txt` を取得し、加速状態を確認する。不要な再ダウンロード・ビルドは行わない。

## 2026-10-31 ECM状態ダンプで加速ルール生成失敗を特定（ソース照合済）

- **実機**：`ecm_dump.sh`（引数なし）成功、約9,863B、HTTPダウンロードを表すTCP/443 conn serial 5 が存在。`is_routed=1`、NAT実施、接続バイト数も転送実績に整合（内部IP/MACは公開台帳に載せない）。
- **実機の決定的値**：`conns.conn.5.nss_v4.ported.can_accel=1`、`conns.conn.5.nss_v4.ported.accel_mode=-2`、`driver_fail_total=0`、`classifiers.default.pr.accel=denied`。
- **ECMパッケージが指定するソースコミット** `9acdcb05c04ae177a79c4c34cef0487fbcedbfaa` と照合。該当ソース `frontends/include/ecm_front_end_types.h` 165行で `ECM_FRONT_END_ACCELERATION_MODE_FAIL_RULE = -2`（不正なルール情報による加速失敗）と定義。`frontends/nss/ecm_nss_ported_ipv4.c` 1442–1451行はルール生成失敗時に `ported_accel_bad_rule` 経由でこの状態を設定。`-1` は `FAIL_DENIED` のため、`-2` を単なるcan_accel拒否として扱ってはいけない。
- **直接の失敗条件候補**：同ファイル399–423行で、from/toインターフェース階層欠落、または先頭の `ae_interface_identifier<0` を検出するとルール生成を中止。後続のfrom/to階層で不正な複合インターフェース等も同じ失敗状態になる。**どの条件に該当したかは未確認**。
- `classifiers.default.pr.accel=denied` は通信終了時のTCP状態や双方向パケット確認条件でも発生し得る。保存した状態が `FAIL_RULE` であることから、現段階では分類器を根本原因と断定しない。
- **次のゲート**：ユーザー実機上に保存済みの `/tmp/ecm-state.txt` から serial 5の `from_interfaces` / `to_interfaces` にある `name`、`ae_interface_identifier`、`interface_count`、`nss_v4.ported` を抽出。NSSルール生成前のインターフェース識別問題を優先確認。追加TCP転送、ビルド、フラッシュ書き込みは不要。

## 2026-10-31 NSS IPv4 FAIL_RULEの発火条件を実機・対象ソース双方で特定

- **実機ECM Conn serial=5**：`from_interfaces` は `lan1` (AE=-1)、`br-lan` (AE=-1) の2段、`to_interfaces` は `wan` (AE=-1) の1段。`nss_v4.ported.can_accel=1`、`accel_mode=-2`。WAN/LAN IPv4通信自体は成功済み。
- **適用元ECMソース 9acdcb05**：`frontends/nss/ecm_nss_ported_ipv4.c` 399–423行は `from_ifaces[from_ifaces_first]` と `to_ifaces[to_ifaces_first]` の AE IF番号を調べ、どちらか負数なら `ported_accel_bad_rule` (1442–1451行) に飛ぶ。`FAIL_RULE=-2` は `frontends/include/ecm_front_end_types.h` 165行で定義。実機値は**この失敗分岐の条件に一致**。ほかの要因が同時にある可能性は残る。
- **同ECMソース**：`frontends/nss/ecm_nss_common.h` 67–82行は `nss_cmn_get_interface_number_by_dev(dev)` をそのまま呼び、`ecm_interface.c` の `ecm_interface_heirarchy_construct` は通常Ethernet (`lan1`・`wan`) で次のデバイスへの階層構築を終える。現行実機ダンプにはGMAC (`eth0/eth1`) が接続階層にない。
- **現行カーネル設定**：`target/linux/ipq806x/config-6.12` 333行 `CONFIG_NET_DSA_TAG_QCA=y`、`CONFIG_NET_DSA_QCA8K=y`、別方式の `QCA_8021Q` 構成は確認できない。QCA8337 DSAの実機構成は `wan@eth0`・`lan1@eth1`。
- **過去成功の再利用対象**（2026-10-25実機記録、現在はパッチの実体差分未取得）：WG2600HP IPQ8064 用 `package/kernel/qca-nss-ecm/patches/9999-wg2600hp-0031-nss-dsa-ipv4-ram-tested.patch` とQCA8337 2CPU/802.1Qタグの`0031`修正。旧25.12.5で128MiB転送5回、NSS IPv4 `create_requests` 216→240、正しい通信量増加・invalid_ifnum0を確認。WG2600HP3 IPQ8062のP1パッチとは区別する。
- **判断**：ECM DSAユーザーポート→NSS GMACのIF番号解決と、QCA8337のDSAタグ/VLAN分離を**一体として**比較・設計する必要がある。ユーザーポートのAE=-1を一律1/2に置き換えるだけの改変は禁止。25.12.6 Linux 6.12とのAPI/タグ機構適合、回帰・副作用を検証してから候補修正を作る。ビルド・実機書き込みは保留。
