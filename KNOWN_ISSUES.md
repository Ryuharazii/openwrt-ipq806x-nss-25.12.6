# 既知の問題 / Known Issues

## 日本語

このファームウェアは非公式の実験的ビルドです。

WG2600HP3は実機に `sysupgrade` で書き込んで試験済みです（使用者からの報告）。RAM起動ではありません。
全機能の検証は未完了で、長期安定性は未検証（UNTESTED）です。

- 起動時にネットワーク接続が不安定になる場合があります。
- IPIP6トンネルのNSSオフロード動作は未確認です。
- WG2600HP3でのTUNIPIP6統計の正確性は未検証です。
- 長期安定性とセキュリティの検証は未完了です。
- これらの問題の根本原因は確定していません。

## English

This firmware is an unofficial experimental build.

WG2600HP3 was flashed with `sysupgrade` and tested on hardware, as reported by the operator; this was not a RAM-boot test.
Full feature validation is incomplete, and long-term stability remains unverified (UNTESTED).

- Intermittent network connectivity issues may occur during startup.
- NSS offloading for IPIP6 tunnels has not been verified.
- The accuracy of WG2600HP3 TUNIPIP6 statistics has not been verified.
- Long-term stability and security testing are incomplete.
- The root causes of these issues have not been conclusively identified.
