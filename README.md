# 貨物追跡情報取得ツール（非同期版）

Google Sheetsから追跡番号を取得し、ブラウザで自動的に追跡情報を取得してシートに書き込むツールです。
**非同期処理により、複数の追跡番号を並列に取得します。**

## 機能

1. **Google Sheetsから追跡番号を取得**
   - 仕入管理のAD列（5行目から）を取得
   - G列が「在庫あり」「在庫なし」の行は除外
   - 重複した追跡番号を削除

2. **ブラウザで追跡情報を取得（非同期・並列処理）**
   - https://japan-kaigen.com/download/ にアクセス
   - 各追跡番号を入力して検索
   - テーブルから配送状況、日付、場所を取得
   - **最大3件を同時に処理して高速化**

3. **Google Sheetsに結果を書き込み**
   - trackingシートに追跡番号と取得情報を書き込み
   - フォーマット: A列=追跡番号、B列=日付、C列=場所、D列=配送状況、E列=特記事項
   - 複数の配送履歴がある場合は複数行に展開

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. Playwrightブラウザのインストール

```bash
playwright install chromium
```

### 3. Google Sheets API設定

1. `service_account.json` ファイルがプロジェクトルートにあることを確認
2. Google Sheetsでサービスアカウントのメールアドレスに共有権限を付与
   - サービスアカウント: `auto-order@corded-guild-461323-e1.iam.gserviceaccount.com`
   - 対象シート: https://docs.google.com/spreadsheets/d/1Dvz3cS9DRGx4woEY0NNypgLPKxLZ55a4j8778YlCFls/

## 使い方

### 基本的な実行

```bash
python main.py
```

### デバッグモードで実行

```bash
# 詳細なログを表示
LOG_LEVEL=DEBUG python main.py
```

### その他のログレベル

```bash
# 警告とエラーのみ表示
LOG_LEVEL=WARNING python main.py

# エラーのみ表示
LOG_LEVEL=ERROR python main.py

# 通常の実行（デフォルト）
LOG_LEVEL=INFO python main.py
```

### 実行の流れ

1. Google Sheetsに接続
2. 仕入管理シートから追跡番号を取得
3. 各追跡番号に対して（**非同期・並列処理**）：
   - ブラウザで追跡サイトにアクセス
   - 追跡番号を入力して検索
   - 結果を取得
   - trackingシートに書き込み
4. 最大3件を同時に並列処理することで高速化

### パフォーマンス

- **非同期処理**: 複数の追跡番号を並列に取得
- **同時実行数**: デフォルト3件（`main.py`の`MAX_CONCURRENT`で変更可能）
- **処理時間**: 従来の同期処理と比較して、追跡番号が多い場合は大幅に短縮

### 注意事項

- 実行中はブラウザウィンドウが開きます（確認のため）
- 非表示モードで実行したい場合は、`main.py` の以下の行を変更してください：
  ```python
  browser = p.chromium.launch(headless=True)  # headless=True に変更
  ```
- 追跡番号が多い場合は時間がかかります
- ネットワーク接続が必要です

## ファイル構成

```
tracking_shipments/
├── main.py                 # メインスクリプト
├── requirements.txt        # 依存パッケージ
├── service_account.json    # Google Sheets API認証情報（Git管理外）
├── README.md              # このファイル
├── 仕様書.spec            # 仕様書
└── .gitignore             # Git管理除外設定
```

## トラブルシューティング

### Google Sheetsに接続できない

- `service_account.json` が正しい場所にあるか確認
- サービスアカウントにシートの共有権限があるか確認

### ブラウザが起動しない

```bash
playwright install chromium
```
を再実行してください。

### 追跡情報が取得できない

- 追跡サイトのHTML構造が変更された可能性があります
- ブラウザで手動確認してください
- 必要に応じてセレクタを調整してください

## ライセンス

内部利用専用

