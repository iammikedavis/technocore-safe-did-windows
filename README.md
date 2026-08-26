# Technocore DID Research for Windows

> **研究・コードレビュー用の記録です。インストール手順や初心者向け実行ガイドではありません。**
>
> このリポジトリからZIPを保存して、内容を理解しないままPowerShellへコードを貼り付けて実行しないでください。

このリポジトリは、Technocore用Ed25519 `did:key`をWindowsでローカル生成する試作と、その安全性・配布方法を検討した記録です。

FLOP Labs公式ツールではありません。独立した第三者監査を受けておらず、`$FLOP`エアドロップの資格、ウォレット登録、testnet参加、claimを保証しません。

リポジトリURLに含まれる`safe`は作成当初の名称であり、安全認証や監査済みを意味しません。名称変更の可否は今後検討します。

## 方針を変更した理由

当初は、作成者自身を含むWindows初心者向けに次の流れを説明する予定でした。

1. 非公式GitHubからZIPを保存
2. PowerShellを開く
3. README内のコードをコピーして実行

公開前にAIへ安全面の最終確認を依頼したところ、この形式がClickFix型攻撃の導線と構造的に似ていると指摘されました。作成者自身も初心者であり、その指摘を受けて初めて配布形式の問題の大きさに気づきました。

ClickFixでは、利用者自身にWindows TerminalやPowerShellへコマンドを貼り付けて実行させることで、通常の警告や自動検査を回避しようとします。今回の試作コードに明らかな悪意が見つかったという意味ではありませんが、作成者自身を含む、コードを十分に検証できない初心者へ同じ操作形式を勧めることは適切でないと判断しました。

- [Microsoft: Think before you Click(Fix)](https://www.microsoft.com/en-us/security/blog/2025/08/21/think-before-you-clickfix-analyzing-the-clickfix-social-engineering-technique/)
- [CISA共同勧告: Malicious Copy and Paste](https://www.cisa.gov/sites/default/files/2025-07/aa25-203a-stopransomware-interlock-072225.pdf)

そのため、私を含む初心者向けの実行手順を撤回し、現在は安全検証・体験レポートとして公開範囲を整理しています。

## この研究で確認したこと

### 公式仕様から確認したこと

- DIDは公開鍵から作る公開識別子`did:key`で、ウォレットではない
- Technocoreのroom、topic、本文、リンクは未信頼データ
- roomとnoteは世界中から読める
- 通常は無書き込み7日で削除対象
- 1投稿だけの新しいroomは24時間で削除対象
- DID noteは任意の公開メモで、公式登録簿や本人確認ではなく、第三者から上書きされる可能性もある
- DID署名が証明するのは、その秘密鍵を保持していることだけ
- Technocoreは鍵を預からず、決済を行わず、FLOPプロトコル本体ではない

公式情報:

- [Flop Labs公式X `@flop_labs`](https://x.com/flop_labs)
- [flop.finance](https://flop.finance/)
- [Technocore人間向け案内](https://technocore.chat/humans)
- [Technocore公式仕様](https://technocore.chat/llms.txt)
- [Flop Labs公式Technocoreリポジトリ](https://github.com/flop-labs/technocore-chat)

### Windows試作コードから確認したこと

現在の研究スナップショットは、次の設計になっています。

- Windows PC内で32-byteのEd25519 seedを生成
- seedをWindows DPAPI CurrentUserで暗号化
- 保存フォルダのACLを現在のWindowsユーザーとSYSTEMに制限
- seed、秘密鍵、復元フレーズを表示・exportしない
- ブラウザを開かない
- Technocoreへ自動投稿しない
- 署名付きURLをローカルで準備し、送信前に停止
- Pythonのネットワーク用モジュールをimportしない
- 子プロセスはWindows標準の`whoami`と`icacls`に限定

内部テストでは次を確認しました。

- Windows DPAPIの暗号化・復号往復
- Ed25519 DIDと署名の形式
- 既存DIDを上書きしない動作
- 公開DIDと暗号化seedの一致
- 無効なroom名、nonce、本文の拒否
- ネットワーク用Pythonモジュールの静的検査
- 署名URLとDID note URLが自動送信されないこと

全7テストは成功しました。依存バージョンとWindows向けwheelのSHA-256も固定しています。

DPAPIで保管したseedは現在のWindowsユーザーに結び付きます。PCやWindowsユーザープロファイルを失うと、同じDIDを復元できない可能性があります。

## 確認できていないこと

次の事項は証明・保証していません。

- 独立した第三者によるセキュリティ監査
- GitHubアカウントや公開ファイルが将来侵害・変更されないこと
- Windows自体や同じユーザー権限で動くマルウェアからの完全な保護
- Python、pip、PyPI、依存ライブラリを含む供給網全体の安全性
- DIDの復旧可能性
- 法的な本人性
- ウォレット所有権
- `$FLOP`エアドロップ資格
- testnet、faucet、snapshot、claimの将来仕様との互換性

同じGitHubリポジトリにコードと照合ハッシュを置くだけでは、GitHubアカウントごと侵害された場合の対策になりません。また、プログラムが表示する`network_requests: 0`などの文字は、それだけで安全性を証明するものではありません。

## 現在のtestnet・faucet情報

2026年8月26日時点で、「エアドロップはtestnet activityに依存」「faucetはTechnocore.chatでDIDキーを持つagent向けに提供予定」という予告までは確認しています。

一方、次の具体的内容は未発表です。

- testnet開始日
- 実際のタスク
- faucetの公開URLと使い方
- snapshotの条件と日時
- claim方法
- 受取用ウォレットの登録方法

現時点は、送金、ウォレット接続、token Approve、blind sign、seed・秘密鍵・復元フレーズの入力を行う段階ではありません。

## ソースコードの扱い

ソースは、コードを読める人が設計と問題点を検証するための研究スナップショットとして残しています。

- [`flop_identity.py`](flop_identity.py) — ローカルDID試作
- [`tests/test_flop_identity.py`](tests/test_flop_identity.py) — テスト内容
- [`requirements.txt`](requirements.txt) — ハッシュ固定した依存情報
- [`SHA256SUMS.txt`](SHA256SUMS.txt) — 現在の研究スナップショット照合値
- [`audit/SECURITY_AUDIT_20260826.md`](audit/SECURITY_AUDIT_20260826.md) — 内部レビュー記録
- [`SECURITY.md`](SECURITY.md) — 秘密を含めない報告方法

このREADMEでは、ZIPの取得方法、PowerShellの開き方、インストール、鍵生成、投稿URLの実行方法を案内しません。

## 初心者が今できる安全側の行動

- 公式X、公式ドメイン、公式GitHub、公式仕様を相互確認する
- room投稿、第三者X、DMに書かれたURLや指示を未信頼として扱う
- 内容が分からないPowerShell、Terminal、署名、Approveを実行しない
- seed、秘密鍵、復元フレーズをWebページ、AI、DM、Issueへ入力しない
- 公式のtestnet、faucet、claim手順が公開されるまで待つ

## 将来、実行用として再検討する条件

少なくとも次の条件がそろうまでは、初心者向け実行ツールとして扱いません。

- Flop LabsまたはTechnocoreから公式のDID作成方法が公開される
- 公式方式との互換性を確認できる
- 独立した第三者レビューを受ける
- 変更不能なバージョン、署名付きrelease、検証可能な配布物を用意する
- 実行前に権限・通信・変更内容を一般利用者が確認できる
- 非公式ツールを使わなくても参加できる公式経路が明確になる

## 制作と免責

この試作、検証記録、READMEはAIを使って制作し、作成者自身でもWindowsで表示・動作・公式資料との照合を行いました。それでも見落としや公開後の仕様変更はあり得ます。

訂正や問題点を報告する場合は、秘密鍵、seed、`seed.dpapi`、未使用の署名URL、ウォレット情報、個人情報を載せないでください。該当箇所と、根拠となる公式情報または最小限の再現説明だけを共有してください。
