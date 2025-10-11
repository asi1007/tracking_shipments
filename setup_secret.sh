#!/bin/bash
set -e

# service_account.jsonをSecret Managerに保存するスクリプト

PROJECT_ID="yiwu-automate"
SECRET_NAME="service-account-json"

echo "======================================"
echo "Secret Managerセットアップ"
echo "======================================"
echo ""

# Secret Manager APIを有効化
echo "[1/3] Secret Manager APIを有効化中..."
gcloud services enable secretmanager.googleapis.com --project=${PROJECT_ID}
echo "✓ 完了"
echo ""

# シークレットを作成（既に存在する場合はスキップ）
echo "[2/3] シークレットを作成中..."
if gcloud secrets describe ${SECRET_NAME} --project=${PROJECT_ID} > /dev/null 2>&1; then
    echo "⚠ シークレット ${SECRET_NAME} は既に存在します"
else
    gcloud secrets create ${SECRET_NAME} \
        --replication-policy="automatic" \
        --project=${PROJECT_ID}
    echo "✓ シークレット作成完了"
fi
echo ""

# シークレットにservice_account.jsonの内容を保存
echo "[3/3] service_account.jsonの内容を保存中..."
gcloud secrets versions add ${SECRET_NAME} \
    --data-file=service_account.json \
    --project=${PROJECT_ID}
echo "✓ 保存完了"
echo ""

echo "======================================"
echo "✓ Secret Managerのセットアップ完了"
echo "======================================"
echo ""
echo "次のステップ:"
echo "1. Dockerfileを修正してSecret Managerから認証情報を取得"
echo "2. Cloud Run Jobsに Secret Managerへのアクセス権限を付与"
echo ""

