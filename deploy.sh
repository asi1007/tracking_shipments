#!/bin/bash
set -e  # エラーが発生したら即座に終了

# Google Cloud Run Jobsにデプロイするスクリプト

# 設定
PROJECT_ID="yiwu-automate"
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

# 前提条件のチェック
echo "[前提条件チェック]"

# Dockerが起動しているかチェック
if ! docker info > /dev/null 2>&1; then
    echo "✗ Dockerが起動していません。Docker Desktopを起動してください。"
    exit 1
fi
echo "✓ Docker起動確認"

# gcloudがインストールされているかチェック
if ! command -v gcloud &> /dev/null; then
    echo "✗ gcloud CLIがインストールされていません"
    exit 1
fi
echo "✓ gcloud CLI確認"

# プロジェクトが設定されているかチェック
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ "$CURRENT_PROJECT" != "$PROJECT_ID" ]; then
    echo "⚠ プロジェクトが異なります: ${CURRENT_PROJECT} → ${PROJECT_ID}"
    gcloud config set project ${PROJECT_ID}
fi
echo "✓ プロジェクト設定: ${PROJECT_ID}"
echo ""

# 実行するステップを選択
if [ "$1" = "build" ]; then
    STEPS="1"
elif [ "$1" = "push" ]; then
    STEPS="2"
elif [ "$1" = "deploy" ]; then
    STEPS="3"
else
    STEPS="123"
fi

# 1. Dockerイメージをビルド
case "$STEPS" in
    *1*)
    echo "[1/3] Dockerイメージをビルド中..."
    echo "（これには数分かかる場合があります）"
    docker build --platform linux/amd64 -t ${IMAGE_NAME}:latest . --progress=plain
        echo "✓ Dockerイメージのビルド完了"
        echo ""
        ;;
esac

# 2. Container Registryにプッシュ
case "$STEPS" in
    *2*)
        echo "[2/3] Container Registryにプッシュ中..."
        echo "（これには数分かかる場合があります）"
        
        # Docker認証設定
        gcloud auth configure-docker --quiet
        
        docker push ${IMAGE_NAME}:latest
        echo "✓ Container Registryへのプッシュ完了"
        echo ""
        ;;
esac


# 3. Cloud Run Jobsを作成/更新
case "$STEPS" in
    *3*)
        echo "[3/3] Cloud Run Jobsをデプロイ中..."
        gcloud run jobs deploy ${JOB_NAME} \
            --image ${IMAGE_NAME}:latest \
            --region ${REGION} \
            --max-retries 0 \
            --task-timeout 30m \
            --memory 2Gi \
            --cpu 1 \
            --set-env-vars LOG_LEVEL=INFO,HEADLESS=true \
            --quiet
        echo "✓ Cloud Run Jobsのデプロイ完了"
        echo ""
        ;;
esac

echo "======================================"
echo "✓ デプロイが完了しました！"
echo "======================================"
echo ""
echo "ジョブを実行するには："
echo "  gcloud run jobs execute ${JOB_NAME} --region ${REGION}"
echo ""
echo "ログを確認するには："
echo "  gcloud run jobs logs read ${JOB_NAME} --region ${REGION}"
echo ""
echo "段階的にデプロイする場合："
echo "  ./deploy.sh build   # ビルドのみ"
echo "  ./deploy.sh push    # プッシュのみ"
echo "  ./deploy.sh deploy  # デプロイのみ"
echo ""