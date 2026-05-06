#!/bin/bash
set -e

# Cloud Schedulerで3時間おきに実行するスクリプト

PROJECT_ID="yiwu-automate"
REGION="asia-northeast1"
JOB_NAME="tracking-shipments"
SCHEDULER_NAME="tracking-shipments-every-3hours"

echo "======================================"
echo "Cloud Scheduler セットアップ"
echo "======================================"
echo ""
echo "スケジュール: 3時間おき"
echo "ジョブ: ${JOB_NAME}"
echo ""

# Cloud Scheduler APIを有効化
echo "[1/2] Cloud Scheduler APIを有効化中..."
gcloud services enable cloudscheduler.googleapis.com --project=${PROJECT_ID}
echo "✓ 完了"
echo ""

# スケジューラジョブを作成
echo "[2/2] スケジューラジョブを作成中..."

# 既存のスケジューラを削除（存在する場合）
if gcloud scheduler jobs describe ${SCHEDULER_NAME} --location=${REGION} --project=${PROJECT_ID} > /dev/null 2>&1; then
    echo "⚠ 既存のスケジューラを削除します..."
    gcloud scheduler jobs delete ${SCHEDULER_NAME} \
        --location=${REGION} \
        --project=${PROJECT_ID} \
        --quiet
fi

# 新しいスケジューラジョブを作成
gcloud scheduler jobs create http ${SCHEDULER_NAME} \
    --location=${REGION} \
    --schedule="0 */3 * * *" \
    --time-zone="Asia/Tokyo" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
    --http-method=POST \
    --oauth-service-account-email=144875028915-compute@developer.gserviceaccount.com \
    --project=${PROJECT_ID}

echo "✓ スケジューラジョブ作成完了"
echo ""

echo "======================================"
echo "✓ セットアップ完了"
echo "======================================"
echo ""
echo "スケジュール: 3時間おき（0時、3時、6時、9時、12時、15時、18時、21時）"
echo "タイムゾーン: Asia/Tokyo"
echo ""
echo "スケジューラを確認："
echo "  gcloud scheduler jobs describe ${SCHEDULER_NAME} --location=${REGION}"
echo ""
echo "手動で即座に実行："
echo "  gcloud scheduler jobs run ${SCHEDULER_NAME} --location=${REGION}"
echo ""
echo "スケジューラを停止："
echo "  gcloud scheduler jobs pause ${SCHEDULER_NAME} --location=${REGION}"
echo ""
echo "スケジューラを再開："
echo "  gcloud scheduler jobs resume ${SCHEDULER_NAME} --location=${REGION}"
echo ""

