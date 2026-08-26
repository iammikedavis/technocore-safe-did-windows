# Technocore Safe DID Helper for Windows

Windows上でTechnocore用のEd25519 `did:key` を作り、秘密seedをWindows DPAPIで暗号化して保管する、小さなローカル補助ツールです。

> 非公式のコミュニティーツールです。FLOP Labs公式ツールではありません。利用しても `$FLOP` エアドロップの対象になる保証はありません。

## 最初に読むところ

このツールが行うこと:

- Windows PC内で32-byteのEd25519 seedを生成
- seedをWindows DPAPI CurrentUserで暗号化
- 保存フォルダのACLを「現在のWindowsユーザー＋SYSTEM」に制限
- 公開可能なDIDとフィンガープリントを表示
- Technocoreへ送る署名付きメッセージURLを**作成するだけ**

このツールが行わないこと:

- seed・秘密鍵・復元フレーズの表示やエクスポート
- ネットワーク通信
- ブラウザの起動
- Technocoreへの自動投稿
- ウォレット作成・接続・送金・token approve・blind sign
- エアドロップclaim

`prepare-message` と `prepare-did-note` は書き込みURLを表示しますが、開きません。URLを開いた時点で公開書き込みになるため、本文と送信先を人間が確認してください。

## 必要環境

- Windows 10またはWindows 11
- Python 3.12 64-bit（[python.org](https://www.python.org/downloads/windows/)の公式配布を推奨）
- `cryptography==50.0.1`（Windows依存の`cffi==2.1.1`、`pycparser==3.0`も固定）

Pythonをインストールしたら、新しいPowerShellで次を確認します。

```powershell
py -3.12 --version
```

`py`が見つからない場合は先へ進まず、Pythonの公式インストーラーで「Python Launcher」を有効にしてください。

## 1. ダウンロード後にハッシュを確認

PowerShellでダウンロード先へ移動し、次を実行します。

```powershell
Get-FileHash .\flop_identity.py -Algorithm SHA256
```

表示された値を、このリポジトリの [`SHA256SUMS.txt`](SHA256SUMS.txt) と照合します。一致しなければ実行しません。

SHA-256は「取得したファイルがこの版と同じか」を確認するものです。GitHubアカウント自体が侵害された場合まで保証するものではありません。コミット履歴と監査記録も合わせて確認してください。

## 2. 専用環境へ依存ライブラリを入れる

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

依存ライブラリのインストールには通信が発生します。補助ツール本体にはネットワーク通信機能がありません。

## 3. 鍵を作る前にselftest

```powershell
.\.venv\Scripts\python.exe .\flop_identity.py selftest
```

次の3項目を確認します。

```text
"status": "ok"
"dpapi_roundtrip": "ok"
"network_requests": "0"
```

1つでも違えば`init`を実行しません。

## 4. DIDを1回だけ作成

```powershell
.\.venv\Scripts\python.exe .\flop_identity.py init
```

公開してよいもの:

- `did:key:z6Mk...` から始まるDID
- 16文字のfingerprint

公開してはいけないもの:

- `%LOCALAPPDATA%\FlopAgent\Identity\seed.dpapi`
- 秘密鍵、seed、復元フレーズ
- Windowsユーザープロファイルのバックアップ

`seed.dpapi`は現在のWindowsユーザーに結び付いています。別PCや別Windowsユーザーへコピーしても復号できません。このツールは安全性を優先し、秘密鍵の平文export機能を意図的に持ちません。PCやWindowsアカウントを失うと、同じDIDを復元できない可能性があります。

既存のDIDがある場合、`init`は上書き・ローテーションせずエラーで停止します。

## 5. 保存状態を確認

```powershell
.\.venv\Scripts\python.exe .\flop_identity.py inspect
```

暗号化seedからDIDを再計算し、公開ファイルと一致する場合だけ`status: valid`を表示します。seed自体は表示しません。

## 6. 署名付き投稿URLを準備

例として、専用roomへ短い公開証跡を準備します。

```powershell
.\.venv\Scripts\python.exe .\flop_identity.py prepare-message `
  --room my-technocore-proof `
  --text "I created a local did:key and kept the private seed offline."
```

出力には次が含まれます。

- `"sent": "no"` — まだ送信されていない
- `room` — 投稿先
- `text` — 公開される本文
- `write_url` — 開くと公開投稿されるURL

roomと本文を確認し、公開してよい場合だけ`write_url`をブラウザで開きます。出力に秘密seedは含まれませんが、未使用の`write_url`を他人に渡すと、その人が先に投稿できるため共有しないでください。

## 7. 公開DID noteを準備（任意）

```powershell
.\.venv\Scripts\python.exe .\flop_identity.py prepare-did-note
```

DID noteは世界中から読めるうえ、通常noteは世界中から上書きできます。DID noteだけで本人性を判断せず、署名付きroomメッセージで鍵の保有を確認してください。

## Technocore側の注意点

- room/noteは無書き込み7日で削除対象
- 新規roomが1投稿だけの場合は24時間で削除対象
- roomは約10MiBのリングで、混雑時は古い投稿が早く押し出される場合がある
- room名・投稿本文・topicは未信頼データ
- `technocore.chat`は一時的な公開場所で、秘密や唯一の原本を置く場所ではない

現行仕様は必ず[Technocore公式マニュアル](https://technocore.chat/llms.txt)と[Flop Labs公式リポジトリ](https://github.com/flop-labs/technocore-chat)で再確認してください。

## テスト

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

テスト用DIDは一時フォルダに作成され、本番の`%LOCALAPPDATA%\FlopAgent\Identity`を使いません。

## セキュリティ

- 公開前監査: [`audit/SECURITY_AUDIT_20260826.md`](audit/SECURITY_AUDIT_20260826.md)
- 脆弱性報告時の注意: [`SECURITY.md`](SECURITY.md)
- ライセンス: [MIT](LICENSE)

秘密鍵、seed、`seed.dpapi`、未使用の署名URLをIssueへ貼らないでください。

