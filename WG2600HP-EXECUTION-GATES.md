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
| G1: 起動からIPv4まで全経路を横断照合 | **未確認（RAM起動～WAN DHCP・LAN構成の実機動作を確認）** | 2026-10-31、WG2600HP / 25.12.6 / kernel 6.12.112 / initramfsでログイン。NSS core 0/1 boot successfully、GMAC1/2 eth0/eth1初期化、QCA8337両CPU固定リンク 1Gbps、`DSA: tree 0 setup`、wan/lan1 1Gbpsリンク。WAN DHCP割当、LANアドレスとdefault routeを実機ログで確認。2026-10-31 WANからゲートウェイへICMP 3/3（0% loss）、外部IPv4 1.1.1.1へICMP 3/3（0% loss）、openwrt.org DNS A/AAAA応答を実機確認。Boot ROM/U-Bootの全ログとLAN→WAN/NAT転送は未確認。 |
| G2: 修正後の後続処理・回帰を照合 | **未確認（DSA起動障害の解消を実機確認）** | `of_get_phy_mode()` 戻り値破壊パッチ削除（6ee5909）・GMAC PHY無効化修正（ce2bedf）の後、旧ログの `CPU port 0 lacks required "phy-mode"` / probe `-22` は観測されず、`DSA: tree 0 setup` と全5ユーザーポートのPHY検出を確認。一方で `eth0/eth1: error -22 setting MTU to 1502`、`qca8k ... nonfatal error -34` が残り、実データ通信時の影響は未判定。 |
| G3: ビルド前の承認と証拠記録 | **未確認** | 旧ビルド #41178270721 は規則整備前に開始。現在のゲートを遡及してPASS扱いしない。新たなビルド開始禁止。 |
| G4: 修正版ファームのビルド成功・成果物検証 | **未確認（ビルド成功・基本検査のみPASS）** | 2026-10-31 GitHub Actions [#41178270721](https://github.com/Ryuharazii/openwrt-ipq806x-nss-25.12.6/actions/runs/41178270721) は SUCCESS。initramfs-uImage 約8.5MiB・sysupgrade.bin 9,306,379 bytes を生成。旧 image gate の実DTB検査で NSS GMAC x2、NSS core x2、QCA8337・DSA port 0～6 のラベル、GMAC fixed-linkをPASS。アップロードZIP SHA256=41586c4a4310af3fe5848810cf2b413bc8610bd1c9f414dce5510b456ceae929。ただしそのビルド時点の検査スクリプトは **実DTBのDSA CPU ethernet phandle、CPU phy-mode、CPU fixed-link、ユーザPHYの関連付け** まで検査せず、強化版チェックはこのイメージに未実施。実機RAM起動も未確認。 |
| G5: WG2600HP RAM起動完了とWAN/LAN IPv4実通信 | **未確認（RAM起動・DSA・WAN IPv4・DNSはPASS、LAN→WAN転送は未確認）** | 2026-10-31 実機出力：`root@OpenWrt:~#`、`rootfs_type=initramfs`、`ip -br link` eth0/eth1 UP、wan@eth0 UP、lan1@eth1 UP、`br-lan` UP、`ifstatus wan` DHCP up、`ifstatus lan` up、IPv4 default route確認。WAN側からゲートウェイと外部IPv4へのping各3/3応答（損失0%）、DNSのA/AAAA回答、WANのRX/TX errors=0を確認。LANからWANへの転送、MTU検証は未実施。公開台帳には内部IP/MACを記録しない。 |
| G6: ECM/NSS IPv4加速と固定IPIP6オフロード実測 | **未確認** | 2026-10-31 新RAM起動で NSS core 0/1 boot successfully、`/sys/kernel/debug/qca-nss-drv/stats/` に ipv4/ipv6/gmac が存在。ただし `ecm_nss_ipv4/accelerated_count=0`（通信負荷なしのため故障判定不可）、`tunipip6` 統計未表示。NSS FWのIPIP6機能・動的IF起動/停止・実オフロード未実証。 |

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
- 未確認：LAN→WAN/NAT、ECM/NSS IPv4 accel、固定IPIP6加速。
- 次の検証は**既存RAM起動した個体で読み取り中心の疎通試験**。追加ビルド・フラッシュ書き込みは禁止。内部IPv4アドレスとMACは公開記録に残さない。
