# Google Cloud Run Jobs デプロイ手順

## 前提条件

1. **Google Cloud CLIのインストール**
   ```bash
   # macOSの場合
   brew install --cask google-cloud-sdk
   
   # 認証
   gcloud auth login
   gcloud config set project corded-guild-461323-e1
   ```

2. **Dockerのインストール**
   ```bash
   # macOSの場合
   brew install --cask docker
   ```

3. **Container Registry APIの有効化**
   ```bash
   gcloud services enable containerregistry.googleapis.com
   gcloud services enable run.googleapis.com
   ```

## デプロイ方法

### 方法1: デプロイスクリプトを使用（推奨）

```bash
# スクリプトを実行
./deploy.sh
```

### 方法2: 手動でデプロイ

```bash
# 1. プロジェクトIDを設定
export PROJECT_ID="corded-guild-461323-e1"
export REGION="asia-northeast1"
export JOB_NAME="tracking-shipments"

# 2. Dockerイメージをビルド
docker build -t gcr.io/${PROJECT_ID}/${JOB_NAME}:latest .

# 3. Container Registryにプッシュ
docker push gcr.io/${PROJECT_ID}/${JOB_NAME}:latest

# 4. Cloud Run Jobsを作成/更新
gcloud run jobs deploy ${JOB_NAME} \
  --image gcr.io/${PROJECT_ID}/${JOB_NAME}:latest \
  --region ${REGION} \
  --max-retries 0 \
  --task-timeout 30m \
  --memory 2Gi \
  --cpu 1 \
  --set-env-vars LOG_LEVEL=INFO,HEADLESS=true
```

### 方法3: Cloud Buildを使用（CI/CD）

```bash
# Cloud Buildでビルド＆デプロイ
gcloud builds submit --config cloudbuild.yaml
```

## ジョブの実行

### 手動実行

```bash
gcloud run jobs execute tracking-shipments --region asia-northeast1
```

### スケジュール実行（Cloud Scheduler）

```bash
# Cloud Schedulerジョブを作成（例：毎日9時に実行）
gcloud scheduler jobs create http tracking-shipments-daily \
  --location asia-northeast1 \
  --schedule "0 9 * * *" \
  --uri "https://asia-northeast1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/corded-guild-461323-e1/jobs/tracking-shipments:run" \
  --http-method POST \
  --oauth-service-account-email auto-order@corded-guild-461323-e1.iam.gserviceaccount.com
```

## ログの確認

```bash
# 最新の実行ログを確認
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=tracking-shipments" \
  --limit 50 \
  --format json
```

## トラブルシューティング

### イメージのビルドに失敗する場合

```bash
# ローカルでテスト
docker build -t test-tracking .
docker run --rm test-tracking
```

### ジョブが失敗する場合

```bash
# ログを確認
gcloud run jobs logs read tracking-shipments --region asia-northeast1
```

### メモリ不足の場合

```bash
# メモリを増やす（4GB）
gcloud run jobs update tracking-shipments \
  --region asia-northeast1 \
  --memory 4Gi
```

## 環境変数の設定

デプロイ時に環境変数を設定できます：

```bash
gcloud run jobs update tracking-shipments \
  --region asia-northeast1 \
  --set-env-vars LOG_LEVEL=DEBUG,HEADLESS=true
```

## 費用について

- **実行時のみ課金**: ジョブが実行されている時間のみ
- **目安**: 2GB メモリ、1 CPU で約30分実行 = 約$0.05

## セキュリティ

- `service_account.json` はDockerイメージに含まれます
- イメージは非公開のContainer Registryに保存されます
- サービスアカウントの権限を最小限に設定することを推奨

