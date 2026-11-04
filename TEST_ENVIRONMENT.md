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
- 実機は現在稼働中。IPIP6のNSS TUNIPIP6カウンター増加を確認済み（使用者からの報告）
- 稼働中の有線LAN瞬断とIPv4デフォルトルートの一時消失は未解決。原因は未確定
- 全機能の検証は未完了、長期安定性は未検証（UNTESTED）
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
- The device is currently running on hardware; increasing NSS TUNIPIP6 counters for IPIP6 have been confirmed, as reported by the operator
- Intermittent wired LAN disconnections during operation and temporary loss of the IPv4 default route remain unresolved; their causes are unknown
- Full feature validation is incomplete, and long-term stability is unverified (UNTESTED)
- Other ISPs and connection environments are untested

### Privacy
Public IP addresses, IPv6 prefixes,
tunnel endpoints, and authentication
credentials are intentionally omitted.

## Disclaimer

Results apply only to the tested environment.
No compatibility or stability guarantee is provided.
