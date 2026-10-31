# WG2600HP IPQ8064 — NSS IPv4/DSA移植監査（2026-10-31）

対象: OpenWrt NSS 25.12.6 / Linux 6.12.112 / WG2600HP (IPQ8064)。**WG2600HP3は対象外**。

## 実機で確定した状態
- LAN→WAN HTTPS: HTTP 206 / 8,388,608 bytes（通信 PASS）。
- `ecm_dump.sh`のTCP/443接続: `nss_v4.ported.can_accel=1`、`accel_mode=-2`（FAIL_RULE）。
- FROM階層: `lan1 (AE=-1)` → `br-lan (AE=-1)`。TO階層: `wan (AE=-1)`。
- NSS IPv4 `ipv4_create_requests=0`、RX/TXパケット=0。**現行RAM版のNSS IPv4加速はFAIL**。固定IPIP6は未確認。

## ルール生成前の失敗条件（ソースと実機一致）
ECMソースコミット `9acdcb05c04ae177a79c4c34cef0487fbcedbfaa`:
- `frontends/nss/ecm_nss_ported_ipv4.c:399–423`：from/to階層先頭のNSS AE IF番号が負数なら `ported_accel_bad_rule` へ。
- 同ファイル `1442–1451`：`ECM_FRONT_END_ACCELERATION_MODE_FAIL_RULE` を設定。NSSへのCREATEを発行しない。
- `frontends/include/ecm_front_end_types.h:165`：FAIL_RULE=-2。
- `frontends/nss/ecm_nss_common.h:67–82`：`nss_cmn_get_interface_number_by_dev` に委譲。
- `ecm_interface.c`：通常EthernetのDSAユーザーポートはGMACまで階層を展開せず、実機接続階層に `eth0/eth1` が現れない。

したがって、現行RAM版は **ECMからNSSへのインターフェース対応付け不足** が確実なルール生成阻害要因。

## QCA8Kのタグ方式も未対応
- Linux v6.12.112 `drivers/net/dsa/qca/qca8k-8xxx.c:1756–1760` の `qca8k_get_tag_protocol()` は `DSA_TAG_PROTO_QCA` 固定。現行 `target/linux/ipq806x/config-6.12` は `CONFIG_NET_DSA_TAG_QCA=y`。
- 現行DTS: QCA8337 CPU port0→GMAC1/eth0（WAN側）、port6→GMAC2/eth1（LAN側）。
- **単純にAE番号-1をGMAC番号1/2へ書き換えるだけでは不十分**。QCAヘッダの互換性と、WAN/LANのVLAN分離・正しいCPU conduit選択も保証する必要がある。
- 現行OpenWrtには既に `target/linux/generic/pending-6.12/711-01/02/03`・`712` のQCA8K LAG/2CPU/flood/learning修正がある。旧版の対応をそのまま重複適用しない。

## 成功版との比較
- WG2600HP **25.12.5** 成功時、GMAC `eth0=1`、`eth1=2`、DSA論理IFは-1。NSS IPv4 create requests 216→240、128MiB×5回の転送時に実RX/TX増加、invalid interface=0を確認。
- 旧 `0031.patch` は `include/net/dsa.h`、`net/dsa/tag_8021q.c`、`qca8k-8xxx.c`、`qca8k-common.c` の4ファイル変更、記録上SHA256 `0338bd1ec94a1428031d5ab9070dd31839db1d80ade16ea5fff842b697205906`。旧ECM `9999-wg2600hp-0031-nss-dsa-ipv4-ram-tested.patch` も成功実装の候補。
- **これら旧パッチの原本は現GitHub作業ツリーに存在せず、この環境でも実体未取得。25.12.6への移植済みとは主張しない。**

## 公開実装との照合・非互換判定
参考: `kuncy7/openwrt-nss-edma` の `target/linux/generic/pending-6.18/761-net-dsa-qca8k-add-802.1Q-VLAN-based-tag-driver.patch`（IPQ5018・Linux6.18向け、39,670B）。QCA8K標準QCAヘッダを802.1Qタグへ変更し、tagger/VID/bridge/FDB/CPUポート処理を包括する。
Linux **v6.12.112** の素のソースと旧文脈で静的比較: **6ファイル33ハンク中26一致、7不一致**。不一致: `include/net/dsa.h` 2、`qca8k-8xxx.c` 2、`qca8k-common.c` 3。新規taggerファイルは別集計。**直接適用不可／移植要**。この試験はOpenWrtパッチ適用後ソースでのpatch dry-run・ビルドではない。

## 修正完了の合格条件
1. Linux6.12向けQCA8K `qca-8021q`タグ・VID/FDB・CPU port0/6・bridgeを横断整合し、標準QCAタグ使用機種への回帰を防止。
2. ECMのDSA user→適切なNSS phys/virtual IF解決を実装し、NSSルールのMAC/VLAN/MTU/両方向IF番号を検証。番号の単純置換を禁止。
3. 実ソースへのpatch適用・ARM実ビルドとDSA VLAN/NSSパケット経路の静的検証を通し、初めてRAM起動試験。
4. RAMでIPv4 NAT、NSS create要求/ACK、RX/TXカウンタ増加、双方向LAN/WAN分離、MTU1460の回帰検証。
5. 固定IPIP6 NSS動的IF起動/停止は別途実証。**NSS実証までsysupgrade禁止**。

検証不足のまま追加ビルド・フラッシュ書き込みは行わない。
