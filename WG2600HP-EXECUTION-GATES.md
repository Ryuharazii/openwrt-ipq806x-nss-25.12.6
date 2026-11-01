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
| G3: ビルド前の承認と証拠記録 | **FAIL（証拠記録済み／ビルド不可）** | 2026-10-31の現行作業ブランチに対するビルド前検証記録を末尾に追記。G1の起動全経路照合とG2の変更後回帰が未完了。旧ビルド #41178270721 の成功を新規修正版PASSとみなさず、新たなビルドは禁止。 |
| G4: 修正版ファームのビルド成功・成果物検証 | **未確認（ビルド成功・基本検査のみPASS）** | 2026-10-31 GitHub Actions [#41178270721](https://github.com/Ryuharazii/openwrt-ipq806x-nss-25.12.6/actions/runs/41178270721) は SUCCESS。initramfs-uImage 約8.5MiB・sysupgrade.bin 9,306,379 bytes を生成。旧 image gate の実DTB検査で NSS GMAC x2、NSS core x2、QCA8337・DSA port 0～6 のラベル、GMAC fixed-linkをPASS。アップロードZIP SHA256=41586c4a4310af3fe5848810cf2b413bc8610bd1c9f414dce5510b456ceae929。ただしそのビルド時点の検査スクリプトは **実DTBのDSA CPU ethernet phandle、CPU phy-mode、CPU fixed-link、ユーザPHYの関連付け** まで検査せず、強化版チェックはこのイメージに未実施。実機RAM起動も未確認。 |
| G5: WG2600HP RAM起動完了とWAN/LAN IPv4実通信 | **PASS（RAM起動・DSA・WAN IPv4・DNS・LAN→WAN IPv4疎通、LAN側MTU1500）／NSS・経路全体のMTU未確認** | 2026-10-31 実機出力：`root@OpenWrt:~#`、`rootfs_type=initramfs`、`ip -br link` eth0/eth1 UP、wan@eth0 UP、lan1@eth1 UP、`br-lan` UP、`ifstatus wan` DHCP up、`ifstatus lan` up、IPv4 default route確認。WAN側からゲートウェイと外部IPv4へのping各3/3応答（損失0%）、DNSのA/AAAA回答、WANのRX/TX errors=0を確認。LAN側Ubuntu eno1の経路がWG2600HPのLAN側IPであることを確認して外部IPv4へping 3/3成功（損失0%）。Ubuntu `eno1` からWG2600HPのLANゲートウェイへDF設定、ICMP payload1472（IPv4合計1500 bytes）でping 3/3、損失0%を確認。LAN→WAN経路の1500バイト DF pingは失敗し、上流ゲートウェイから `Frag needed and DF set (mtu = 1460)` を受信。2026-10-31 Ubuntu `eno1` → WG2600HP → 1.1.1.1 のDF設定、ICMP payload1432（IPv4全長1460バイト）で3/3応答、損失0%を確認。NSS高速化、TCP/UDP転送速度は未確認。公開台帳には内部IP/MACを記録しない。 |
| G6: ECM/NSS IPv4加速と固定IPIP6オフロード実測 | **FAIL（現行RAM版 IPv4 NSS高速化）／未確認（固定IPIP6）** | 実機LAN→WAN HTTPS HTTP 206/8MiB成功。ECM conn serial5ではFROM=lan1→br-lan、TO=wan、全AE IF=-1、`can_accel=1`、`accel_mode=-2 (FAIL_RULE)`。NSS IPv4 create_requests=0、RX/TX=0。適用元ECMソース（9acdcb05）では負のAE IF番号でルール生成を中止するため、これが直接の阻害条件と一致。追加でQCA8K標準タグ方式と8021Qタグの差分もある。固定IPIP6の実オフロードは未確認。別紙 `WG2600HP-NSS-IPv4-DSA-PORT-AUDIT.md` 参照。 |

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

## 2026-10-31 ビルド前検証結果の確定記録

対象：NEC WG2600HP (IPQ8064)、OpenWrt 25.12.6、Linux 6.12.112。現行ブランチ wg2600hp-nss-gmac-no-phy-20261031、検証起点HEAD 66c3f2ac109f55b1c274f1d30351f88d2c260ea1。WG2600HP3は別機種として混同しない。現時点で修正・新規ビルドは行っていない。

| 経路・検証対象 | 判定 | 記録済み証拠と残件 |
| --- | --- | --- |
| 電源投入→Boot ROM→U-Boot | **未確認** | Boot ROM/U-Bootの全ログは未取得。過去のRAM起動成功はブート全経路の照合完了を意味しない。 |
| Linux起動→NSS 2コア→GMAC→QCA8337 DSA初期化 | **旧RAM版でPASS／新修正版未確認** | 本台帳G1・G5の実機記録にinitramfsログイン、NSSコア2基、GMAC2基、DSA tree 0 setupを記載。 |
| DTS→GMAC→DSA CPU0・6→WAN/LAN | **ソース照合済み／後続整合未確認** | target/linux/ipq806x/files-6.12/arch/arm/boot/dts/qcom/qcom-ipq8064-wg2600hp.dts 157–216行：CPU0→gmac1 (eth0)、CPU6→gmac2 (eth1)、WAN port1、LAN port2–5。247–277行：GMAC1 id1、GMAC2 id2、fixed-link。既存RAM版ログのwan@eth0/lan1@eth1と一致。 |
| QCA8K DSAタグ・2 CPUポート・FDB/VLAN | **未確認（互換性）** | target/linux/ipq806x/config-6.12 331–333行：QCA8K/DSA_TAG_QCA有効。既存pending-6.12/711-02は両CPUへのフラッド、711-03はconduit変更を扱う。公開6.18の802.1Q移植候補は素の6.12.112で33ハンク中7不一致（実OpenWrtソースへの適用試験ではない）。LAN/WAN分離と旧タグ方式との適合は未証明。 |
| ECM起動・NSSドライバ設定 | **ソース照合済み／加速はFAIL** | package/qca-nss/qca-nss-ecm/files/qca-nss-ecm.init 24–31・55–57行：NSSフロントエンド選択・起動。diff-wg2600hp-nss 9–19行：NSS GMAC・DRV・ECM standard・TUNIPIP6有効。設定の存在は加速の実証ではない。 |
| LAN→WAN IPv4通信 | **旧RAM版でPASS** | G5と本台帳TCP試験：WAN DHCP、外部疎通、HTTP 206/8,388,608 bytesを確認。ただしDSA MTU 1502設定時の-22/-34残留と後続影響は未確認。 |
| ECM→NSS IPv4ルール生成 | **旧RAM版でFAIL** | 実機ECM serial5：FROM lan1(-1)→br-lan(-1)、TO wan(-1)、can_accel=1、accel_mode=-2 (FAIL_RULE)、NSS ipv4_create_requests=0、RX/TX=0。ECMソース9acdcb05の frontends/nss/ecm_nss_ported_ipv4.c 399–423行は負のAE IF番号で作成を中断、1442–1451行はFAIL_RULEへ。WG2600HP-NSS-IPv4-DSA-PORT-AUDIT.mdに根拠を保存済み。別の阻害条件の併存は未排除。 |
| 固定IPIP6 NSSオフロード | **未確認** | TUNIPIP6有効化設定はあるがFW対応、IF確保・解放、実機加速は未証明。 |
| 修正後の後続処理・回帰 | **未実施** | QCA8K/ECM修正パッチ未適用。CPU0/CPU6、VLAN、FDB、DHCP、MTU、NSS create/ACK、IPIP6停止解放は修正版で未試験。 |

**規則4のビルド前判定：FAIL。** この記録を残すこととビルド許可は別。規則2の電源投入から通信までの横断確認は未合格、規則3の修正後回帰は未実施。旧25.12.5成功パッチ0031とECM 9999の原本も未取得であり、Linux6.12適合を証明できない。したがって新規ビルド・sysupgrade・完成宣言は禁止。既存CI成功を代用しない。

## 2026-10-31 隔離バックポート rollback 修正・静的回帰判定

**対象・変更範囲**: WG2600HP / IPQ8064 / OpenWrt 25.12.6 / Linux 6.12.112。作業対象は `wg2600hp-qca8021q-backport-isolated-20261031` の **staging patch 760-02のみ**。既存 `wg2600hp-nss-gmac-no-phy-20261031` およびデフォルトブランチ、稼働RAM版には未適用。

**差分証拠**:
- commit `814dbd9a6ce8b8239d499a93a07c0dfe2630fd76`: `760-02-net-dsa-qca8k-8021q-driver-6.12-CANDIDATE.patch` の QCA→8021Q 失敗後 `mgmt_conduit` 復旧、header/VLAN rollback エラー出力、8021Q→QCA 成功時の CPU0 管理 conduit 再設定を追加。
- commit `5b0e9ee0f048efc11e5cd78cc05bed53c57588d3`: 上記拡張に合わせて以後3ハンクの new-file start offsets を更新。変更後 patch Git blob `22fd18a04dbb1b5bb4664a1ddab6f58f95e26fd6`。
- commit `08ca8ae5fcac073ff447402f733ccda6f78aa936`: 再検査用 `tests/wg2600hp_qca8k_rollback_static.py` を追加（後続CI実行は未確認、保存のみ）。

**このセッションで実施した読取検証（限定的PASS）**:
- 28/28 unified diff hunks の old/new 行数・前後ハンク offset 一致。
- `760-02` の QCAタグへ戻す成功経路で、CPU0 の conduit 状態更新呼出がある。
- QCA→8021Q の途中失敗で保存した `mgmt_conduit` を復旧し、失敗した header rollback の場合は Ethernet管理を復旧扱いしない。
- VLAN/header rollback 失敗ログの有無、`mgmt_eth_data` と `mib_eth_data` のロックを照合。
- DTS QCA8337 CPU0→gmac1・CPU6→gmac2、dual-CPU VLAN候補の CPU割当、ECM候補の conduit 解決、現行 `CONFIG_NET_DSA_TAG_QCA=y` と新tagger未有効を横断照合。
- 上記10件は **GitHubから取得した文字列に対する静的検査10/10** であり、追加した Python 検査スクリプトを Python 実行したとの主張ではない。

**未解決・FAIL判定を維持**:
1. 旧25.12.5 WG2600HP成功原本 `0031.patch` と ECM `9999-wg2600hp-0031-nss-dsa-ipv4-ram-tested.patch` の本文未取得。
2. `760-02` の 8021Q→QCA 切替途中で register/PVID操作が失敗した場合の完全な巻戻しが未実装。rollback関数自体の書き込み失敗や複数CPUポートの部分更新も未解決。
3. `760-01` tagger、`760-02/03` switch/dual-CPU、`760-04/05` ECM の統合適用・Linux 6.12.112への patch dry-run・ARMコンパイル・データパス/FDB/VLAN回帰未確認。staging のまま。
4. 電源投入→Boot ROM→U-Boot 全ログ照合、修正版RAM起動、IPv4/NSSオフロード、固定IPIP6実加速はいずれも未確認。

**G1: 未確認、G2: 未確認、G3: FAIL（ビルド禁止）、G4: 未確認、G5: 既存RAM版IPv4 PASSのみ、G6: 既存RAM版NSS IPv4 FAIL／固定IPIP6未確認。** この作業ではファームビルド、GitHub Actions起動、sysupgrade、実機書き込みは実施していない。静的チェックの成功を完成宣言へ昇格させない。

## 2026-10-31 Linux 6.12.112 ソースに対する QCA8K 43ハンク実文脈リプレイ

対象: **WG2600HP/IPQ8064専用の隔離ブランチ** `wg2600hp-qca8021q-backport-isolated-20261031`、基準 HEAD `7d32c0329710bc4aaade9c6dae7fe31d79e3a6bb`。旧25.12.5成功パッチ原本はユーザー側で削除済みであり、入手不能として扱う。旧成果物の再提出は前提条件にしない。

**検証手法**: 公開 `gregkh/linux` タグ **v6.12.112** の該当ソース7ファイルをGitHub経由で取得。実在するunified diffを解釈してold/contextを正確に照合し、新内容をメモリ上に順次適用。OpenWrt既存 `711-01` / `711-02` / `711-03` / `712` の後に、隔離 `760-01` / `760-02` / `760-03` の順で試験（`760-01`は既にpending-6.12、残りはstaging）。前後80行以内の位置ずれを許容し、**内容一致**しない箇所はFAIL。確認したハンクのみカウントし、コンパイラ・OpenWrt最終kernelツリーは使っていない。

| 範囲 | 期待/一致 | 判定 |
| --- | ---: | --- |
| OpenWrt既存 711-01/02/03/712 | 9/9 | PASS（文脈一致のみ） |
| 760-01 新QCA8021Q tagger | 5/5 | PASS（文脈一致のみ） |
| 760-02 QCA8K switch / FDB / VLAN / rollback | 28/28 | PASS（文脈一致のみ） |
| 760-03 2CPU VLAN membership | 1/1 | PASS（文脈一致のみ） |
| **総計** | **43/43** | **PASS（文脈一致のみ）** |

**起動時の有効化に関する新規未解決**: 現行 `target/linux/ipq806x/config-6.12` は `CONFIG_NET_DSA_TAG_QCA=y`、`CONFIG_NET_DSA_TAG_QCA_8021Q` 有効設定なし。 `qca8k_get_tag_protocol` は従来QCAが既定であり、追加候補は `change_tag_protocol` を提供するが、自動切替を保証しない。標準DSAは conduit の `/sys/class/net/<conduit>/dsa/tagging` 経由で、conduitとDSA user portsをdownにしてから切替可能。**起動処理の順序・CPU0/CPU6両conduit・LAN/WAN・失敗時復旧の整合を設計、実装、検証すること。** 対象実機へ切替コマンドはまだ実行していない。

**他の未解決**: 760-04/05 ECMのOpenWrt 400/401適用後のソース互換・ARMビルド、taggerの実コンパイル、GMAC/DMA/MTU 1502(-22)/port(-34)、双方向bridge/FDB、ECM CREATE/ACK、固定IPIP6、8021Q→QCA reverse-error復旧、実機RAM試験。

**ゲート**: G1 未確認（追加横断確認必要）、G2 未確認（回帰証拠不足）、**G3 FAIL／新規ファームビルド禁止**、G4 未確認、G5 旧RAM版のみIPv4 PASS、G6 旧RAM版NSS IPv4 FAIL・固定IPIP6未確認。**43/43の文字列リプレイをpatch --dry-run PASSやARMビルドPASSと呼ばない。** GitHub Actions起動、ビルド、フラッシュは今回実施していない。

## 2026-10-31 QCA8K VLAN 途中失敗のロールバック修正と再発防止

- **原因（コード上で確認）**: 隔離 staging `760-02` の `qca8k_change_tag_protocol()` で `qca8k_set_tag_8021q_vlan_mode(priv, true)` が途中ポートで失敗すると、`restore_hdr` に直接ジャンプし `qca8k_set_tag_8021q_vlan_mode(priv, false)` を飛ばしていた。先行ポートのVLAN設定が中途半端に残る可能性がある。
- **対処**: commit `f1888a9cf2c7eb80f619c17a9ecdc4214a7b4959` にて該当分岐を `goto restore_vlan` へ修正。Git blob `c7e306d496241d3d8d2a7f49c37625365b33002d`。変更は隔離stagingのみ。
- **再発防止**: `tests/wg2600hp_qca8k_rollback_static.py` に途中失敗→`restore_vlan` を必須とする回帰アサーションを追加（commits `5ac7dfce3d7aa27aac634a81c41115d780814a10`, `4080050fddfb4775e438483b7fd3ef1aab8e1b47`）。
- **修正後の読取検査**: GitHubから再取得した実パッチとDTS、ECM、dual-CPU候補、kernel設定で **11/11 項目 PASS（静的文字列照合）**。28/28 unified diffハンク行数・オフセットPASS。追加したPythonスクリプト自体の実行、patchツール適用、コンパイル、HW回帰は**未実施**。
- **残リスク**: 巻戻し処理自体のハードウェア書込み失敗、8021Q→QCA逆方向切替途中の復旧不備、ECMとの統合、起動時タグ選択、WAN/LAN分離とRAM試験は未解決。
- **G3判定: FAIL（ビルド禁止維持）**。新ファーム生成なし。旧RAM版のIPv4通信成功を今回修正のPASSに流用しない。

## 2026-10-31 追加修正: QCA8K VLAN巻戻し失敗時の管理通信保護

- **コード上の問題を確認**: staging `760-02` の `restore_vlan` でVLAN巻戻しに失敗しても、後続 `restore_hdr` が成功すれば `priv->mgmt_conduit` を復旧していた。ハードウェアVLAN構成が部分更新された状態でEthernet管理アクセスを再開するおそれがある。
- **修正**: commit `a3d8bd36bc824053378ff6d2ff03e7433e1470f0`。`bool vlan_rollback_ok = true` を導入し、巻戻し失敗時はfalse。管理conduitは**VLAN巻戻し成功 AND header巻戻し成功**のときだけ復帰。失敗時はMDIO専用アクセスを維持。Linux 6.12.112対象の隔離stagingだけを修正し、ビルド対象へはマージしていない。
- **再発防止**: commit `b866f7e4d42d1b063fdf754d121d4be8f935c676`、`tests/wg2600hp_qca8k_rollback_static.py` で両条件を静的チェック。GitHub再取得の6ファイルに対するJS静的照合を実行し **13/13 項目PASS**（QCA8K 28/28 unified-diffハンク個数・行数・offset確認を含む）。**Pythonスクリプトは未実行**。patch実適用、ARMコンパイル、実機回帰は未実施。成功報告は静的照合に限定。
- **影響範囲/未解決**: 正常復帰では両成功条件ともtrueで従来通りCPU0 Ethernet管理を復旧。片方でも失敗すれば管理conduitを復旧しない（別経路MDIOは必要）。8021Q→QCA逆方向切替途中の失敗、部分的PVID更新、FW/GMAC/MTU、ECM階層/IF解決、LAN/WANの実パケット分離は未検証。
- **必須ゲート**: G1の全起動シーケンス未完、G2の実ソース・回帰未完、**G3 FAILでビルド禁止維持**。既存RAMイメージのIPv4転送成功・NSS高速化失敗という状態は変わらず。ユーザー向けVLAN追加はなし。

## 2026-10-31 DSA tag_8021q登録失敗時の残存ポインタ修正（隔離）

- **確認した実コード**: Linux **v6.12.112** の `net/dsa/tag_8021q.c`、`dsa_tag_8021q_register()` は `ds->tag_8021q_ctx = ctx` のあと `dsa_tag_8021q_setup()` を呼ぶが、失敗時 `err_free: kfree(ctx)` のみで `ds->tag_8021q_ctx` をNULLへ戻さず、以前の成功ポートのVLANとフィルタを片付けない。切替候補 `760-02` の登録失敗→復旧経路で参照切れが生じる。
- **対処**: 隔離ブランチ `backports/staging/760-06-net-dsa-8021q-register-error-cleanup-6.12-CANDIDATE.patch` を追加。commit `95d275b6ce490d3641aadfdd75082bee04980a1d`。失敗時の `kfree(ctx)` を既存の `dsa_tag_8021q_unregister(ds)` に変更し、setup途中のユーザーポートの削除、コンテキスト解放・NULL化に集約する。関数プロトタイプは `include/linux/dsa/8021q.h` に既存。
- **検証**: v6.12.112元ソースへ既存760-03のunified-diff文脈を**JSで完全一致照合してメモリ上で再構築**、その結果に対し新760-06のunified-diffも**文脈一致**（`@@ -443,9 +443,12 @@`）。GitHubへコミット後読み戻して、既存760-02の28/28ハンクを含む**16/16のJS静的文字列・ハンク構造チェックPASS**。テスト追記: commit `914e7383924ff34c250c40978301185620d6ec66`。
- **未検証を明示**: kernelの実パッチ適用（`patch --dry-run`を含む）・Python回帰テスト実行・ARMコンパイル・失敗注入・実機RAM起動・ネットワーク回帰は **未実施**。unregister処理自体のHW書き込み失敗は依然として残りうる。8021Q→QCA逆方向切替失敗、ECMのOpenWrt 400/401との統合、起動時タグ選択、Wi-Fi NSS redirectと固定IPIP6は未解決。
- **ゲート**: G3 **FAIL**（未統合候補のみ、ビルド禁止維持）。稼働版と通常作業ブランチは変更なし。追加のユーザー用VLAN設定なし。

## 2026-10-31 Wi-Fi NSS redirect再構成の欠落を修正（隔離）

- **発見した具体的不整合**: `package/kernel/mac80211/Makefile` は `config-$(CONFIG_PACKAGE_MAC80211_NSS_SUPPORT) += MAC80211_NSS_SUPPORT` を使用するが、`PKG_CONFIG_DEPENDS` に同じ設定が未登録。`include/package.mk` の `STAMP_CONFIGURED` は `confvar,$(PKG_CONFIG_DEPENDS)` で決まり、NSS redirect設定の変更時に構成キャッシュが再生成されない可能性がある。
- **実装修正**: 隔離ブランチ commit `be60ea7f698eb2b74e1fdd0b97a930ae2ba84eb8` で `PKG_CONFIG_DEPENDS` に `CONFIG_PACKAGE_MAC80211_NSS_SUPPORT` を追加。適用先は `package/kernel/mac80211/Makefile` のみ。この変更は無線NSSの新規機能を実装するものではなく、既存のNSS redirectをビルド構成へ正しく伝えるためのもの。
- **確認根拠**: 現行 `diff-wg2600hp-nss` に `CONFIG_NSS_DRV_WIFI_ENABLE=y` / `CONFIG_PACKAGE_MAC80211_NSS_SUPPORT=y`、mac80211 `990` パッチに `nss_virt_if_create_sync` と `nss_virt_if_tx_buf`、WG2600HP DTSにPCIe Wi-Fi2台とNVMEM校正情報。既存 `scripts/wg2600hp_cross_audit.py` に5つのチェックを加え、`tests/test_wg2600hp_cross_audit.py` に2件の異常系回帰テストを追加。GitHub読み戻し7ファイルの **JS静的チェック11/11 PASS**（うち異常系2件）。Pythonテストは実行していない。
- **影響と残リスク**: Wi-Fi mac80211の設定キャッシュの更新条件だけを拡張。無線実機接続、ath10k fwのロード、ECM、NSS redirectの統計値、同時有線通信は未計測。Wi-Fi完全オフロード対応を示すものではない。回帰確認は静的のみ。
- **ゲート**: G1/G2に未確認事項あり、**G3 FAIL**を維持し通常ビルド・書込みは実行しない。ユーザー向けVLAN追加なし。

## 2026-10-31 Wi-Fi NSS redirect送信拒否時のskb復旧

- **修正前に照合したデータパス**: WG2600HP PCIe ath10k → mac80211 RX `netif_rx_nss` → `nss_virt_if_tx_buf` → NSS。非対応パケット・NSS無効・インターフェース異常で `nss_virt_if_tx_buf` がエラーを返す経路を公開QCA NSSドライバ `nss_virt_if.c` のソースで確認。mac80211 `990-mac80211-add-nss-redirect-support.patch` はNSS転送直前に `skb_push(skb, ETH_HLEN)` でヘッダーを広げるが、エラー時に戻さず通常スタックへ渡していた。通常処理のフレーム境界を破壊する可能性。
- **実際の修正**: 隔離ブランチの `package/kernel/mac80211/patches/subsys/990-mac80211-add-nss-redirect-support.patch` を commit `309210e2e23e7eb01e6f101aa70861bbbaff5b69` で更新。`skb_headroom(skb) < ETH_HLEN` なら従来スタックへ直接渡す。NSS送信エラー時に `skb_pull(skb, ETH_HLEN)` でデータ位置を戻す。NSS送信成功時の処理は変更なし。
- **回帰検知**: `scripts/wg2600hp_cross_audit.py` にヘッダー復旧・headroom検査を追加（commit `a13a3a3c50fec5457d4d32f8b099776958427296`）、`tests/test_wg2600hp_cross_audit.py` にそれぞれを欠落させた2つの異常系テスト（commit `b25a6ddd1c055ba8bcce43b2953194f927615ac2`）。GitHubから実際の3ファイルを読み直し、**patch hunk 13件の行数と前後offset一致／不変条件・負例の合計6/6 JS静的検査PASS**。この結果はソース構造検査であり、動作試験を意味しない。
- **未解決**: pinned NSSドライバ版での全エラーパスのパケット所有権、実コンパイル、Wi-Fi通信への影響、Wi-Fi NSS統計の増分、有線ECM/DSA/固定IPIP6、実機RAM試験は未確認。**G3 FAIL、ビルド禁止・書込み禁止維持**。ユーザー用VLAN設定を増やさない。

## 2026-11-01 Wi-Fi NSS QoS送信ヘッダーの境界検査

- **元ソースと実コードを横断確認**: `mac80211/patches/subsys/990-mac80211-add-nss-redirect-support.patch` の `ieee80211_xmit_nss_fixup()` は `ieee80211_subif_start_xmit_8023()` が `skb->len < ETH_HLEN` を判定する**前**に呼び出され、Ethernet/IPv4/IPv6ヘッダーを境界検査なしで参照していた。短い・非線形のskbで不正参照し得る。`CPTCFG_MAC80211_NSS_SUPPORT` が有効な場合のみ到達する分岐。
- **修正を隔離ブランチに実保存**: commit `2ecd8c2536a77ba2e7ad81a9e0758207b4ea45b6`。Ethernet最小線形長 `skb_headlen(skb) >= ETH_HLEN` を先に確認。IPv4は `ETH_HLEN + sizeof(struct iphdr)`、IPv6は `ETH_HLEN + sizeof(struct ipv6hdr)` の線形長を満たす場合にだけQoSを読み取る。正常で十分な長さのパケットのQoS処理は変更しない。
- **再発検出の追加**: `scripts/wg2600hp_cross_audit.py` に各読み取りより前の境界検査を確認するチェックを追加（commit `36f5d84540b5de3518c8f12a4a116a67f3eed306`）、`tests/test_wg2600hp_cross_audit.py` にEthernet/IPv6検査の欠落を検出する負例を追加（commit `ef054fe505270e15425fbef6e0039413ff00345b`）。GitHubから再取得したmac80211パッチ13/13ハンクの行数/オフセット一致、JSで正常ケースとEthernet/IPv4/IPv6境界検査を消した3負例を評価し **正常1件PASS、負例3件を正しくFAIL**。これはソース構造の限定的検証。Pythonテストの実行、patchの実適用、ARMビルド、実機Wi-Fiテストは未実施。
- **NSSドライバ契約確認**: 別公開リビジョンの `nss_virt_if_tx_buf()` から `nss_core_send_packet()` まで確認。送信拒否の場合はSKBを解放せずエラーを返す経路が存在し、以前追加した `skb_pull` によるエラー時スタック復帰と整合する。ただし実際のビルドが固定している `qca-nss-drv 3cfb9f43` の完全なソース・DMA失敗経路・全エラーパスは未照合であり所有権の最終判定は保留。
- **ゲート**: G3は引き続き **FAIL**。現行通常ブランチと書き込み対象ファームには未導入。Wi-Fi NSSの実機高速化、LAN/WANのNSS IPv4、固定IPIP6はいずれも未達成。ユーザー用VLAN追加不要。

## 2026-11-01 Wi-Fi NSS実イメージ照合とbackports適合性監査

- **前回の修正の実ソース照合**: mac80211パッチ `990-mac80211-add-nss-redirect-support.patch` のうち Linuxファイルに対する12ハンクは、`gregkh/linux` の **v6.18.55** タグの Kconfig/ieee80211_i.h/iface.c/rx.c/tx.c 実ソースに **全12ハンクの旧コード文脈が一意一致**。JavaScriptのメモリ内unified-diff展開で12/12適用相当を確認。残る13番目の `local-symbols` はLinuxツリーには存在せず、backports生成アーカイブを直接取得できなかったため未検証。これは `patch --dry-run`、OpenWrt前段パッチ適用後ソース、ARMコンパイルのPASSではない。
- **過去の実ビルドZIPを再活用**: 会話に既存添付の `WG2600HP-IPQ8064-25.12.6-NSS(20261031-134853).zip` の `wg2600hp-resolved.config` とWG2600HP専用manifestを実際に展開せずに読み取り検査したところ、NSS Wi-Fi設定2件、mac80211/ath10kドライバ設定2件、QCA99x0ファームウェア設定1件、無線/ファームウェア/AP 5パッケージが **10/10 PASS**。擬似的にfirmwareを削除／Wi-Fi NSSフラグ無効化した2ケースはそれぞれ不合格となることをローカルPythonで確認。実機Wi-Fi起動やNSS加速を意味しない。
- **コード変更**: image gate `scripts/wg2600hp_nss_image_gate.sh` のconfigとmanifest確認にWi-Fi 5+5条件を追加、WG2600HP以外のmanifestを誤選択する曖昧なglobを修正（commit `1456a6a048177a64fcca224ad80799f1989a5119`）。ターゲットのデフォルトに暗黙依存していた `kmod-ath10k-ct` と `kmod-mac80211` を `diff-wg2600hp-nss` に明記（commit `60e4c608d555a0d39c5e22a5b28d4c3014ecc1f3`）。既存ビルドのresolved.config/manifestには両方収録済みであり、新規ドライバへの変更ではない。
- **回帰検出**: cross-auditにimage-gate3件と明示的Wi-Fiドライバ選択2件の検査を追加（commits `c029c282ed815d8980a4a2749155c777124e09c2`, `9c6843c055ae45271f3453882b72bf9873674bb9`）。unittestで無線FW欠落・他機種manifest選択・ath10k選択欠落の計3負例を追加（commits `f07d9bc7ab14d961ad898cc9f4a8223e223850f0`, `84f02ffd95c52ab81327ed9debc84c561ce17eba`）。GitHubから再取得した関連ファイルへのJS静的検査 **14/14 PASS**。`sh -n`・Python unittest・OpenWrt image gateのフル実行・ARMコンパイルは今回未実施。
- **未解決・ゲート**: pinned NSS 3cfb9f43 の全エラーパス所有権、backports 6.18.55 tar自体とOpenWrtパッチ適用順、Wi-Fi起動/NSS統計、ECM/DSAのIPv4高速化、固定IPIP6の寿命管理・FW対応、RAMブート検証は未完。**G3 FAIL**のまま。隔離ブランチのみ更新し通常ファームを変更しない。

## 2026-11-01 実RAMイメージのWi-Fi NSS ELF連携検査（実行済）

- **検証対象**: 既存ユーザー提供 `WG2600HP-IPQ8064-25.12.6-NSS(20261031-134853).zip`（SHA256 `41586c4a4310af3fe5848810cf2b413bc8610bd1c9f414dce5510b456ceae929`）内の `openwrt-nss-25.12.6-ipq806x-generic-nec_wg2600hp-initramfs-uImage`（SHA256 `1375ecfff27f118ffc1a152b37e8a8a145e11a6ef8e4d3edd110e0b3d0410eac`）。実uImageをバイト解析しカーネル内XZを解凍、newc initramfs 1356エントリを追跡、**実ビルド成果物**の `mac80211.ko` と `qca-nss-drv.ko` を取り出して `readelf` で照合。
- **実行結果（10/10）**: ARM ELF `mac80211.ko`, `qca-nss-drv.ko`, `ath10k_core.ko`, `ath10k_pci.ko` の4ファイルが存在、QCA99X0 `firmware-5.bin` と `board-2.bin` が存在。`mac80211.ko` が `nss_virt_if_create_sync`, `nss_virt_if_destroy_sync`, `nss_virt_if_register`, `nss_virt_if_tx_buf` の4つを未定義外部シンボルとして参照し、`qca-nss-drv.ko` の `__ksymtab_strings` に対応する公開シンボルがある。さらに `.modinfo` の `depends=cfg80211,qca-nss-drv,compat` を確認（追加1件）。**Wi-Fi NSS redirectの実バイナリ実装・インターフェース依存が成立することを確認**。実機上で機能する/高速化する証明ではない。
- **異常系試験3件も実行**: 既存ファームの取り出し結果からWi-Fiファームウェアを1件除外するとFAIL、NSSドライババイナリ中の `nss_virt_if_tx_buf` シンボル名を改変するとFAIL、uImage末尾データを破損させるとCRC FAIL。いずれも期待通り。
- **自動ゲートへ反映**: 新規 `scripts/wg2600hp_verify_wifi_nss_binary.py`（commits `098ba94da7ee0d122af13ea9c886b9002943cd16`、`cd42c3cd1b3f01fa56ffd80f5ee3e0a26564632e`）を隔離ブランチに登録。`scripts/wg2600hp_nss_image_gate.sh` に組込み（`0c5c9d1bb93e40150cedb5c13edaf393fbb1dad6`）。cross_audit・回帰に検査組込み必須条件を追加（`6043cfefc7b6de20feac06f592a1d184376459ee`、`911d531b0d60eb5bae355ac4c986cbc89718b0cc`）。
- **限界**: ローカルでは同等アルゴリズムのPython版を実行して陽性/陰性テストPASS。GitHubへ登録した正確なファイル内容は再取得・記述を照合済みだが、**隔離ブランチのスクリプトをCIで実行したわけではない**。既存の10/31イメージは新しいmac80211修正を含まない。Wi-Fi接続、NSSカウンタ/スループット、IPv4 DSA/ECM、固定IPIP6は依然未確認。G3 **FAIL**で新規ビルド・書き込みは未実施。

## 2026-11-01 Wi-Fi NSS ELFゲート実行・ARM ABI検査を追加

- **対象を固定**: WG2600HP (IPQ8064) / OpenWrt 25.12.6 / Linux **6.12.112**。過去に作成したGitHub隔離ブランチ版 `scripts/wg2600hp_verify_wifi_nss_binary.py` を現在の会話にマウント済みの実ZIP `WG2600HP-IPQ8064-25.12.6-NSS(20261031-134853).zip` に対して**今回実行**。Git blob SHA `7b4c1cf9b51c1717ade41f51cfa6347101e4ff88` がGitHub取得版とローカルファイルで一致した。
- **実行した陽性試験**: 実uImage内の4モジュール・2無線FW、`mac80211.ko`から`qca-nss-drv.ko`への依存宣言、4つのNSS import/export対応を読込み **11/11 PASS**。異常注入6件（ペイロードCRC破損、uImage size破損、Wi-Fi FW欠落、NSS import欠落、NSS export欠落、依存宣言欠落）と正常検査を組み合わせ、**Python unittest 7/7 PASS**。これは従来の静的文字列チェックではなく実ZIPに対するPythonテスト実行結果。
- **誤判定防止の修正**: 旧検査スクリプトはELFモジュール存在のみを検査し、他アーキテクチャ／不一致カーネル版の `.ko` を拒否できなかった。commit `f234651bc5af7193099e982fbfa277e118d010c0` で全4モジュールに `readelf -h` の **ARM/ELF32** と `.modinfo` の **vermagic=6.12.112** の照合を追加。4モジュールとも実ZIPでPASS。変更後のGit blob SHA `8974cf86f50b31746d12e5e718ee8014c3d80507` がローカル実行版とGitHub版で一致し、同じ実ZIPを再検査してPASS。
- **独立した回帰テストをGitHubへ保存**: `tests/test_wg2600hp_wifi_nss_binary.py`（commit `149ee7a688be3fa0b4be0815298a15943c44c0a8`）は小さなnewc/XZ/uImageを合成するので実ファーム不要。正常ARM ELF、ZIP選択、CRC不良、Wi-Fi FW欠落、NSS公開API欠落、NSS module dependency欠落、ARMアーキテクチャ相違、vermagic相違の **Python unittest 8/8 PASS**。ローカルテストとGitHub読戻しはblob SHA `af9cf3a1d6e6e16286f7be03ed19eb8436f111e8` で一致。
- **CIへの結線**: 手動起動ワークフロー `.github/workflows/build-wg2600hp-nss.yml` の静的preflight工程に上記unittestの実行を追加（commit `d807fbbda22ad068e14a677ad39464a4dd2d6527`）。GitHub Actions自体は起動していないため **CIでのテスト実行は未確認**。
- **残る合格条件**: 新mac80211ソース・NSSドライバ・DSA/ECM統合の実コンパイル、RAM起動、2.4GHz/5GHzの接続、Wi-Fi NSS統計・速度、IPv4 NSS、固定IPIP6 NSSはいずれも **未確認/未達成**。**G3 FAILを維持**。隔離ブランチのテストのみ更新し、完成ファームや書込み許可と扱わない。

## 2026-11-01 実ファーム・固定IPIP6/Wi-Fi経路の再監査（本セッション）

- **対象ZIPの同一性確認**: ユーザー提供 `WG2600HP-IPQ8064-25.12.6-NSS(20261101-002842).zip` は SHA256 `41586c4a4310af3fe5848810cf2b413bc8610bd1c9f414dce5510b456ceae929`。10月31日の既存ビルドと同一であり、**新規修正版の完成ファームではない**。ZIP内uImageはサイズ・CRCを検証し、XZからinitramfsを展開して実ARM ELFを読んだ。
- **固定IPIP6・実バイナリ確認**: `lib/modules/6.12.112/qca-nss-tunipip6.ko`（22,984 bytes）は `depends=qca-nss-drv,ip6_tunnel`。ARM ELFの未定義参照に `register_netdevice_notifier` / `unregister_netdevice_notifier`、`nss_dynamic_interface_alloc_node` / `dealloc_node`、`nss_register_tunipip6_if` / `unregister_tunipip6_if`、`nss_tunipip6_tx_sync` が存在。逆アセンブルで `nss_tunipip6_init_module` の `register_netdevice_notifier` 呼出し、`nss_tunipip6_dev_event` の `nss_connmgr_tunipip6_destroy_interface` 呼出しも確認。**『起動・停止呼び出し元が存在しない』という過去の一般的主張は、このビルドには当てはまらない**。実機のトンネル種別、作成・破棄成功、FW ACK、統計増分は**未確認**。
- **Wi-Fi実バイナリ確認**: `mac80211.ko` が `nss_virt_if_create_sync` / `destroy_sync` / `register` / `tx_buf` を参照し、`depends=cfg80211,qca-nss-drv,compat`。NSS redirectへの結線はコンパイル済みだが、Wi-Fi送受信のNSSオフロード動作・効果は**未確認**。
- **DSA横断照合**: Linux `v6.12.112` の `net/dsa/dsa.c` はCPUポート毎に `dsa-tag-protocol` を参照し、2 CPUポートのタグ方式を一致させる。隔離版DTSではCPU0/6とも未指定、`config-6.12` もQCA_8021Q未選択。両CPUへの指定とKconfig選択を **隔離のみ** `backports/staging/760-07-wg2600hp-qca8021q-dts-config-CANDIDATE.patch` として記録（commit `356d66f8569b8f5f84c5a88592983f5f6e32b113`）。6条件静的確認PASS、GitHub読戻し一致。**現行ビルドには未適用**。
- **重大な未解決回帰**: `760-02` の `qca8k_change_tag_protocol()` は QCA_8021Q→QCA 復帰時、`dsa_tag_8021q_unregister()` と状態変更を先行させた後の `qca8k_set_tag_8021q_vlan_mode` / PVID / header書込失敗をそのまま返し、元のVLAN・ヘッダー設定へ復帰しない。Linux `v6.12.112 net/dsa/dsa.c` の `dsa_tree_change_tag_proto()` はエラー時に旧taggerへ戻す通知を行うため、**DSA状態とQCA8337実ハード状態が食い違う危険**。さらに `760-06` のpartial-register rollbackは未試験。 **G2未確認・G3 FAIL、staging候補の適用/ビルド/フラッシュ禁止を維持**。
- 既存動作済みの有線IPv4通信は引き続き比較基準。**完成要件は有線IPv4・Wi-Fi・固定IPIP6のNSS高速化の実機証明**。検証していない項目にPASSを付けない。

## 2026-11-01 隔離DSAの復帰時ロールバック修正と連続パッチ文脈検証

- **コード修正実施（隔離のみ）**: `backports/staging/760-02-net-dsa-qca8k-8021q-driver-6.12-CANDIDATE.patch`（commit `19b1c020169839dc249b203a1fa75ac348deadc7`）。QCA_8021Q→QCA復帰時に、VLAN contextの破棄をすべての失敗し得るVLAN mode/PVID/header書込の後に移動し、それ以前に失敗した場合は8021Q header/VLAN mode/各port PVIDの復元を試みる。逆方向のQCA→QCA_8021Q失敗時にも元PVIDへの復元を追加。成功・復旧が保証されたと主張せず、各rollback再失敗は `dev_err` で記録。
- **実際に再取得したLinux v6.12.112ソースで確認**: `qca8k.h`、`qca8k-8xxx.c`、`qca8k-common.c` への既存 `711-01`（3/3）、`711-02`（1/1）、`711-03`（2/2）、`712`（3/3）に続いて、修正版 `760-02`（28/28）の **37/37 unified-diff文脈が順次一致**（ソースをメモリ上で更新した静的検証）。GitHub新blob `1428da306d27b101a9f40733c99e8cba72a8b9fd` を読み戻し一致。
- `net/dsa/tag_8021q.c` の Linux v6.12.112 基準に `760-03` と `760-06` を順次適用する文脈検証は **2/2一致**。合計39/39パッチ文脈一致。ただし `760-06` の未初期化portへの teardown／部分失敗時のhardware rollbackに問題がないかは未解決。
- **未確認（G2/G3）**: 実コンパイル、MDIO書込失敗時の全ポート回復、2 CPUポートのフレーム分離、pinned ECM `760-04/05` のOpenWrt適用順、Wi-Fi NSS/固定IPIP6/NSS IPv4実機オフロード。**G3 FAIL・新規ファームビルドは実行しない。**

## 2026-11-01 実DTB機能宣言の直接照合

- 同じZIP内の ARM uImage バイト位置 8,819,232、FDT version 17、DTB全長 36,855 bytes の実FDTを解析（ヘッダーの長さ・文字列表・構造トークンを照合）。
- `/soc/nss-common` ノードが存在。NSS0 `/soc/nss@40000000` に `qcom,tunipip6-enabled`、`qcom,wlanredirect-enabled`、`qcom,wlan-dataplane-offload-enabled` の**各ブールプロパティ**が存在する。NSS1は別の機能群を担当。該当プロパティの `_` / `-` 誤記はこの実DTBでは検出されない。
- 以上は**旧ビルドの設定・バイナリの存在確認のみ**。実機の固定IPIP6/Wi-FiのNSSオフロード成功は未実証であり、完成ではない。実機NSS rule/offloadカウンタ増分までG6未確認を維持。

## 2026-11-01 実ZIPの起動時処理と固定IPIP6 notifier を再照合（作業再開）

- **原本・実測**: 11/01アップロード `WG2600HP-IPQ8064-25.12.6-NSS(20261101-002842).zip` SHA256 `41586c4a4310af3fe5848810cf2b413bc8610bd1c9f414dce5510b456ceae929`。uImage→XZ→newc initramfs（1356件）を実際に再展開し、`qca-nss-tunipip6.ko` ELF32 ARM, 22,984 bytes, `vermagic=6.12.112`, `depends=qca-nss-drv,ip6_tunnel` を読み取った。
- **固定IPIP6の実コード呼出し元**: `llvm-objdump -dr` で `nss_tunipip6_dev_event` を確認。netdev型 `ARPHRD_TUNNEL6 (=0x301)` のみを受け付け、`NETDEV_UP (=1)` は作成処理へ、`NETDEV_DOWN (=2)` は `nss_connmgr_tunipip6_destroy_interface` へ分岐。`nss_tunipip6_init_module` が `of_find_node_by_name` を行い、通常モードで `register_netdevice_notifier` を呼ぶ。コードの存在は**実機成功の証拠ではない**。なおこのmoduleは `enable_custom` boolを持ち、初期値0時は自動notifier登録経路が存在する。
- **起動時モジュール・ECM初期化の実ファイル**: initramfsの `etc/modules.d/31-qca-nss-gmac` → `32-qca-nss-drv` → `60-qca-nss-drv-tunipip6` の各ファイル内容を読み取った。ECM初期UCI値は `auto` だが、収録されている `etc/uci-defaults/99-wg2600hp-nss-ecm` が対象機種で `ecm.global.acceleration_engine='nss'` に設定し、`/etc/init.d/qca-nss-ecm` をenableする。 `etc/rc.d/S96wg2600hp-nss-ecm` へのシンボリックリンクも収録。ただし **UCI defaults実行時刻・ECM起動成功・トンネルIF生成/ACKは新規実機ログ未取得**。
- **横断確認範囲**: Linux側のRAMイメージから起動用ファイルとNSS呼出し関係まで照合した。**電源投入/Boot ROM/U-Bootの一連の実機ログは未取得**。旧RAM起動→WAN DHCP→LAN→WAN IPv4疎通は既存G5ログPASS。ECM `FAIL_RULE=-2` / DSA AE IF `-1` は既存G6 FAIL。Wi-Fiと固定IPIP6の実機NSS統計増分は未確認。したがって **G1全経路未確認、G2未確認、G3 FAIL** を維持し、ビルド/書込みなし。
- **次の焦点**: 既知の旧ZIPを再検査し続けず、ECM/DSAの隔離候補の安全性と起動経路・後続影響を満たしてから統合。既存の `wg2600hp-net-audit` はboard_name照合を含む読み取り専用の検証スクリプト。Ubuntuでの誤実行を実機の証拠に数えない。

## 2026-11-01 隔離DSA失敗時復旧の実体修正候補（760-08/09、ビルド禁止継続）

- **実際に作成・GitHub読戻し確認した隔離ファイル**:
  - `backports/staging/760-08-net-dsa-8021q-prefix-unwind-6.12-CANDIDATE.patch` — commit `42771824aa8c10bb378dd9122810ab34129f4b28`、blob `d51eb5823fb3171b948f4e6ff95dc1e269d0622e`。
  - `backports/staging/760-09-net-dsa-qca8k-bridge-join-unwind-6.12-CANDIDATE.patch` — commit `bee214fa1e4cae287bf8ad8f9747d0fd068686f6`、blob `e23075ff3a73fecf4a564f5c085078fcc85da713`。
- **760-08 根拠**: Linux v6.12.112 `net/dsa/tag_8021q.c` に既存隔離760-03→760-06をメモリ上で適用した後、追加3ハンクを再適用して予想ソースと完全一致。初期化失敗時に成功済みポートのみ逆順解放、conduit `vlan_vid_add()` 失敗時に当該ポートのVLANを解放、失敗した登録contextをNULLに戻して解放。簡易状態モデルは6/6一致（**実カーネル実行テストではない**）。
- **760-09 根拠**: Linux v6.12.112 `qca8k-common.c` に実OpenWrt 711-01（1ハンク）→隔離760-02（16ハンク）をメモリ上適用し、追加1ハンクを再適用して予想ソースと完全一致。失敗した `qca8k_port_bridge_join()` で `qca8k_update_port_member(..., false)` を試行し、復旧エラーはログ化。Linux `dsa_port_bridge_join()` はJOIN通知失敗時にLEAVE通知を発しないためドライバ側復旧が必要。
- **未解決**: `dsa_switch_tag_8021q_vlan_add()` はCPU/ユーザーポートに対する複数hardware writeの途中失敗を完全に巻き戻さない。 `dsa_tag_8021q_bridge_join()` は旧standalone VLAN削除エラーを確認しない。MDIO/VTUエラー時のhardware rollback、CPU0/6分離・FDB/洪水制御・DHCP・MTU・ECM AE IF階層、Wi-Fi NSS/固定IPIP6 FW ACKは実機で未実証。差分一致・簡易モデルを起動試験PASSとは扱わない。
- **判定**: G1/G2未確認、G3 FAIL。760-08/09は**stagingの候補ファイルのみ**であり `target/linux/generic/pending-6.12` への本統合、ARMビルド、QEMU/実機起動、フラッシュはいずれも行っていない。旧ZIPの再検査を繰り返さず、残るbroadcast VLAN部分復旧とデータパスを横断照合する。
