# 既知の問題 / Known Issues

## 日本語

このファームウェアは非公式の実験的ビルドです。

- 稼働中、有線LANが不規則な間隔で瞬断する現象を確認しています。原因は未確定です。
- IPIP6のNSS TUNIPIP6カウンター増加を実機で確認しました。長期安定性は未検証（UNTESTED）です。
- IPv4デフォルトルートの一時消失を確認しました。ルートは復旧しましたが、原因は未確定で問題の解消は確認できていません。
- WG2600HPのTUNIPIP6統計修正パッチ405は、ソースコード上の確認のみ完了しています。
- 長期安定性とセキュリティの検証は未完了です。
- これらの問題の根本原因は確定していません。

## English

This firmware is an unofficial experimental build.

- Intermittent wired LAN disconnections have been observed during operation. The cause is unknown.
- Increasing NSS TUNIPIP6 counters have been observed on the device. Long-term stability remains unverified (UNTESTED).
- Temporary loss of the IPv4 default route was observed. The route has recovered, but the cause is unknown and the issue remains unresolved.
- Patch 405 for WG2600HP TUNIPIP6 statistics has been reviewed at source-code level only.
- Long-term stability and security testing are incomplete.
- The root causes of these issues have not been conclusively identified.
