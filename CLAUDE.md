# tracking_shipments

貨物追跡情報の自動取得バッチ。Google Sheetsから追跡番号を読み込み、Playwrightで各追跡サイト（OCS、海源など）にアクセスし、結果を `tracking` シートに書き込む。Cloud Run Jobs として動作する。

## アーキテクチャ

DDD構造（`/Users/wadaatsushi/.claude/CLAUDE.md` の「フォルダ構造指針」に準拠）。

```
src/
  main.py                                    # エントリポイント
  usecases/
    shipment_tracking_manager.py             # 全体統括（並列制御・リトライ・集計）
  infrastructure/
    google_sheets/
      base.py / reader.py / writer.py        # シート読み書き
      column_config.py                       # 列番号を「設定」シートから読み込む
    shipment_tracking/
      tracking_info_fetcher.py               # ファサード
      ocs_fetcher.py / kaigen_fetcher.py     # 各社サイトのスクレイパ
  tests/
    test_column_config.py
pytest.ini                                   # pythonpath = src
```

- 並列数: 最大3（サーバー負荷考慮、`ShipmentTrackingManager.MAX_CONCURRENT`）
- リトライ: 指数バックオフ（2/4/8秒、最大3回）
- 書き込み: `tracking` シートを clear → バッチ update（APIレート制限回避）

## 対象スプレッドシート

| 用途 | ID | URL |
|---|---|---|
| メイン | `1Dvz3cS9DRGx4woEY0NNypgLPKxLZ55a4j8778YlCFls` | https://docs.google.com/spreadsheets/d/1Dvz3cS9DRGx4woEY0NNypgLPKxLZ55a4j8778YlCFls/edit |

- 追跡番号: 30列目（AD列）から取得
- 列番号は「設定」シートで外部化（`column_config.py` が読み込み）
- 結果出力先: `tracking` シート

## 実行・デプロイ

| コマンド | 用途 |
|---|---|
| `python src/main.py` | ローカル実行（要 `service_account.json`） |
| `./deploy.sh` | Cloud Build → Artifact Registry push → Cloud Run Jobs deploy |
| `./deploy.sh build` / `push` / `deploy` | 段階的デプロイ |
| `./setup_scheduler.sh` | Cloud Scheduler でジョブ定期実行を設定 |
| `gcloud run jobs execute <JOB_NAME> --region <REGION>` | 手動実行 |

GCPプロジェクト: `yiwu-automate`

### 環境変数

| 変数 | デフォルト | 用途 |
|---|---|---|
| `LOG_LEVEL` | `INFO` | ログレベル |
| `HEADLESS` | `false` (ローカル) / `true` (Cloud Run) | Chromiumヘッドレスモード |

### コンテナ

- ベース: Python（Playwright入り）、AMD64
- 認証情報 `service_account.json` はイメージに同梱（`.gitignore` 済、コミット禁止）

## 既知の課題

- `domain/` 層が未実装（Entity / ValueObject / Repository インターフェース）。現状は infrastructure / usecases の2層のみ
- `venv/` が壊れている（パスに非ASCIIが入った状態で作られた残骸）。テスト実行は `/opt/homebrew/bin/pytest` を使う運用

## テスト

```bash
pytest                  # pytest.ini の testpaths=src/tests を自動検出
```

## ログ

`shipment_tracking_manager.py` の各 `logger.info` で `[1/4] ... [4/4]` のフェーズ進行を出力。エラー時は `exc_info=True` でスタックトレース込み。

## 関連ファイル

- `COLUMN_CONFIG.md`: `ColumnConfig` クラスの使い方
- `DEPLOY.md`: デプロイ手順詳細
- `仕様書.spec`: PyInstaller用（現在は未使用、Cloud Run Jobs構成に移行済み）
