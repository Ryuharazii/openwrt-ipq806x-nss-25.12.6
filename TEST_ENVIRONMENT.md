# テスト環境 / Test Environment

## 日本語

### 回線環境
- ISP：enひかり
- 契約サービス：v6プラス固定IP1
- ひかり電話：契約なし
- IPv4接続方式：IPv4 over IPv6（IPIP6）

### 検証状況
- 実機でIPv4・IPv6接続を確認
- 起動時に通信が不安定になる事象あり
- IPIP6のNSSオフロードは未検証
- 他のISP・回線環境では未検証

### プライバシー
固定IPアドレス、IPv6プレフィックス、
接続先アドレス、認証情報は公開しません。

## English

### Internet Connection
- ISP: enひかり (en Hikari)
- Service: v6 Plus Fixed IP 1
- Hikari Denwa: Not subscribed
- IPv4 connection: IPv4 over IPv6 (IPIP6)

### Test Status
- IPv4 and IPv6 connectivity observed on hardware
- Intermittent connectivity issues during startup
- NSS acceleration for IPIP6 remains unverified
- Other ISPs and connection environments are untested

### Privacy
Public IP addresses, IPv6 prefixes,
tunnel endpoints, and authentication
credentials are intentionally omitted.

## Disclaimer

Results apply only to the tested environment.
No compatibility or stability guarantee is provided.
