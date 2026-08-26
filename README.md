# Technocore Safe DID Helper for Windows

Windows上でTechnocore用のEd25519 `did:key` を作り、秘密seedをWindows DPAPIで暗号化して保管する、小さなローカル補助ツールです。

> 非公式のコミュニティーツールです。FLOP Labs公式ツールではありません。利用しても `$FLOP` エアドロップの対象になる保証はありません。

## 初心者はここから（Windows 10 / 11）

ここでは、**どこを押すか・どこからコピーするか・何が出たら次へ進めるか**を順番に説明します。

### A. ZIPを保存して展開する

1. このGitHubページ上部の緑色の **Code** を押す
2. 開いた白いメニューの一番下にある **Download ZIP** を押す
3. エクスプローラーの **ダウンロード** を開く
4. 保存されたZIPを右クリックして **すべて展開** を押す
5. 次の画面でも **展開** を押す
6. 展開された黄色いフォルダを開く
7. 同じ名前のフォルダがもう1つ入っていたら、それも開く

`flop_identity.py`、`README.md`、`requirements`、`SECURITY.md`が見えたら、正しいフォルダです。ファイルはまだ開きません。

### B. そのフォルダからPowerShellを開く

1. キーボードの `Ctrl` を押したまま `L` を1回押す
2. フォルダ上部のアドレスが青く選ばれたことを確認する
3. 何も消さず、そのまま `powershell` と入力する
4. `Enter` を1回押す

右上の検索欄には入力しません。

青い画面または黒い画面が別ウィンドウで開き、行の先頭に`PS C:\...\technocore-safe-did-windows-main>`のような表示があれば成功です。この表示自体はコピーしません。

### C. コードをコピーする場所

コピー元は、**いま読んでいるこのGitHubページ**です。フォルダ内の`README.md`を開く必要はありません。

下の①〜⑧には、灰色のコード欄が1つずつあります。各コード欄の右端にある **紙が2枚重なったボタン**を押すと、その1行だけがコピーされます。

毎回、次の同じ操作をします。

1. GitHubで、実行する番号のコピーボタンを押す
2. PowerShellのウィンドウをクリックする
3. `Ctrl`を押したまま`V`を1回押す
4. GitHubと同じ1行が貼られたことを確認する
5. `Enter`を1回押す
6. `PS C:\...>`が再表示されるまで待つ
7. GitHubへ戻り、次の番号のコピーボタンを押す

**①〜⑧をまとめてコピーしません。必ず番号ごとに1行ずつ進めます。** 赤いエラー、`False`、入力を求める質問が出た場合は、次の番号へ進みません。

### ① Python 3.12を確認

右端のコピーボタンを押し、PowerShellへ貼ってEnterします。

```powershell
py -3.12 --version
```

`Python 3.12.x`と表示された場合だけ②へ進みます。

`py`が見つからない場合はそこで止め、[python.orgのWindows向け公式ページ](https://www.python.org/downloads/windows/)からPython 3.12 64-bitを導入します。インストール画面では **Python Launcher** を有効にし、完了後にPowerShellを開き直します。

### ② 正しい照合番号をPowerShellへ覚えさせる

```powershell
$expected = "9CDD6D1608DB3755FB249088F098B3A7916974470C6D4A107A14F521BAF03D06"
```

何も表示されず、`PS C:\...>`が戻れば③へ進みます。

### ③ ダウンロードした本体が公開版と一致するか確認

```powershell
(Get-FileHash .\flop_identity.py).Hash -eq $expected
```

`True`と表示された場合だけ④へ進みます。`False`なら補助ツールを実行しません。

### ④ この作業専用のPython環境を作る

```powershell
py -3.12 -m venv .venv
```

文字が表示されなくても、`PS C:\...>`が戻れば⑤へ進みます。

### ⑤ 専用環境内のpipを更新

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

文字が流れている間はPowerShellを閉じません。`PS C:\...>`が戻れば⑥へ進みます。

### ⑥ 必要な依存ライブラリを入れる

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

⑤と⑥では、固定した依存ライブラリを取得するため通信します。`PS C:\...>`が戻れば⑦へ進みます。

### ⑦ 鍵を作る前にselftest

```powershell
.\.venv\Scripts\python.exe .\flop_identity.py selftest
```

表示の中に次の3項目がすべてあることを確認します。下の3項目は確認用で、PowerShellへ貼りません。

- `"status": "ok"`
- `"dpapi_roundtrip": "ok"`
- `"network_requests": "0"`

1つでも違う場合は⑧へ進みません。

### ⑧ DIDを1回だけ作る

```powershell
.\.venv\Scripts\python.exe .\flop_identity.py init
```

公開してよいもの:

- `did:key:z6Mk...`から始まるDID
- 16文字のfingerprint

公開しないもの:

- `%LOCALAPPDATA%\FlopAgent\Identity\seed.dpapi`
- 秘密鍵、seed、復元フレーズ
- Windowsユーザープロファイルのバックアップ

すでにDIDがある場合、⑧は上書きせずエラーで停止します。削除や作り直しはせず、下の「5. 保存状態を確認」の`inspect`を実行してください。

---

ここから下は、ツールの動作・追加コマンド・Technocore側の注意点を詳しく知りたい方向けです。

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
