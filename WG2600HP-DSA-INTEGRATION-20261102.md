# WG2600HP DSA統合版（2026-11-02）現在状態

作業ブランチ: `wg2600hp-dsa-integration-20261102`（Claude担当swconfig版と分離）。

## 有効なLinux 6.12実装

- 実機C2600でDSA＋NSS高速化を報告した `gyimesibalazs/openwrt-ipq806x-nss-25.12` の `dsa-lab` を参照。
- `target/linux/generic/pending-6.12/713`（QCA8337 802.1Q、2 CPU VLAN分離）、`714-01/02`（MAC_PWR_SEL DT）、`716`（MDIO read）を有効化。
- `package/qca-nss/qca-nss-ecm/patches/402`（DSA user port→NSS conduit）、`package/qca-nss/qca-nss-gmac/patches/09/10`（MTUとGMAC親ノード）を有効化。
- 旧独自 `760-01/02/03/06/08/09/10` と `390-04/05`、旧GMAC 09は有効パッチディレクトリから外した。比較用stagingは保持。
- WG2600HP DTS CPU0→gmac1/eth0（WAN）、CPU6→gmac2/eth1（LAN）を保持、`dsa-tag-protocol = "qca-8021q"`、RGMII1電圧フラグを成功版と一致させた。**ユーザーVLAN追加なし**。
- 成功例で必要としていない `CONFIG_NSS_DRV_VLAN_ENABLE` とVLAN managerの明示選択はWG2600HP `diff`から撤回。ドライバKconfig/Makefileの選択肢は以前復活させたがデフォルト無効。
- WG2600HP `diff`はNSS GMAC/DRV/ECM、Wi-Fi NSS redirect、TUNIPIP6 module/driver、IPv6を選択。選択≠高速化成功。

## GitHub Actions結果とゲート

- [#41382021777](https://github.com/Ryuharazii/openwrt-ipq806x-nss-25.12.6/actions/runs/41382021777) は **preflight FAIL（unittest 2/16）**。ARMビルドにもファーム生成にも到達せず。
- 今回の2件は古いテスト条件の誤り。Wi-Fi依存の部分一致を完全一致へ、DSA CPU0モードテストは新しいタグ行を考慮して修正。
- Workflowのpush自動実行を解除。以後は手動dispatchのみで、ビルド前G1/G2/G3の根拠を要確認。
- **G1/G2未完、G3 FAIL、G4未達、G5/G6新ファーム未実施。** 旧RAM版はIPv4通信成立・NSS IPv4ルールCREATE=0。
- Wi-Fi NSS実機高速化、固定IPIP6のIF確保・停止解放およびNSS FW ACKは未実証。

作業履歴の詳細は `WG2600HP-EXECUTION-GATES.md`。上流成功実装の利用・自動CI成功・静的テストをWG2600HP実機の動作PASSと混同しない。
