# NEC WG2600HP 向け OpenWrt 25.12.6 NSS

**非公式・実験的なファームウェアです。**

## 概要

- 対応機種：NEC WG2600HP
- SoC：Qualcomm IPQ8064
- OpenWrt：25.12.6
- Linuxカーネル：6.12.112
- Qualcomm NSS対応のカスタムビルド

## 現在の状況

2026年11月4日にUbuntu上でファームウェアの生成を確認しました。

実機は現在稼働中で、IPIP6のNSS TUNIPIP6カウンター増加を確認済みです（使用者からの報告）。
この確認は、全機能の検証完了や長期安定性の確認を意味しません。

## 既知の問題・未検証事項

- 起動時のネットワーク接続に不安定な事象を確認
- 稼働中の有線LAN瞬断とIPv4デフォルトルートの一時消失は未解決の既知問題。原因は未確定
- TUNIPIP6統計修正パッチ405はソースコード上の確認のみ。実機での修正効果は未検証（UNTESTED）
- 全機能の検証は未完了。長期安定性は未検証（UNTESTED）、セキュリティの検証も未完了

## ビルド設定

機種別の設定は `configs/wg2600hp-public.config` に保存しています。

## 元の開発プロジェクト

このプロジェクトは既存のOpenWrt NSS開発成果を基にしています。

元の開発者、開発履歴、謝辞については
[README.nss-original.md](README.nss-original.md) を参照してください。

## 謝辞

WG2600HPのNSS対応に向けて
[wg2600hp-openwrt-nss](https://github.com/Karin-Laboratory/wg2600hp-openwrt-nss)
を作成・公開してくださった **Karin氏（Karin-Laboratory）** に、心より感謝します。
そのご協力が、この取り組みを進める大きな支えになりました。

### AI支援

開発の検討、調査、ドキュメント作成にあたり、以下のAIアシスタントの支援を受けています。

- Choppie
- Kurorин

## 注意事項

このファームウェアはOpenWrt公式のリリースではありません。

導入には起動不能や通信障害などのリスクがあります。
安全性、安定性、動作について保証しません。

## 関連資料

- [ビルド手順](BUILDING.md)
- [既知の問題](KNOWN_ISSUES.md)

- [テスト環境](TEST_ENVIRONMENT.md)
