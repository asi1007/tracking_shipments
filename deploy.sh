#!/bin/bash

# Google Cloud Run Jobsにデプロイするスクリプト

# 設定
PROJECT_ID="corded-guild-461323-e1"
REGION="asia-northeast1"
JOB_NAME="tracking-shipments"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${JOB_NAME}"

echo "======================================"
echo "Google Cloud Run Jobs デプロイ"
echo "======================================"
echo ""
echo "プロジェクト: ${PROJECT_ID}"
echo "リージョン: ${REGION}"
echo "ジョブ名: ${JOB_NAME}"
echo ""

# 1. Dockerイメージをビルド
echo "[1/3] Dockerイメージをビルド中..."
docker build -t ${IMAGE_NAME}:latest .

if [ $? -ne 0 ]; then
    echo "✗ Dockerイメージのビルドに失敗しました"
    exit 1
fi
echo "✓ Dockerイメージのビルド完了"
echo ""

# 2. Container Registryにプッシュ
echo "[2/3] Container Registryにプッシュ中..."
docker push ${IMAGE_NAME}:latest

if [ $? -ne 0 ]; then
    echo "✗ Container Registryへのプッシュに失敗しました"
    exit 1
fi
echo "✓ Container Registryへのプッシュ完了"
echo ""

# 3. Cloud Run Jobsを作成/更新
echo "[3/3] Cloud Run Jobsをデプロイ中..."
gcloud run jobs deploy ${JOB_NAME} \
    --image ${IMAGE_NAME}:latest \
    --region ${REGION} \
    --max-retries 0 \
    --task-timeout 30m \
    --memory 2Gi \
    --cpu 1 \
    --set-env-vars LOG_LEVEL=INFO

if [ $? -ne 0 ]; then
    echo "✗ Cloud Run Jobsのデプロイに失敗しました"
    exit 1
fi
echo "✓ Cloud Run Jobsのデプロイ完了"
echo ""

echo "======================================"
echo "✓ デプロイが完了しました！"
echo "======================================"
echo ""
echo "ジョブを実行するには："
echo "gcloud run jobs execute ${JOB_NAME} --region ${REGION}"
echo ""

