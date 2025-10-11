# Playwright公式イメージを使用（AMD64アーキテクチャ指定）
FROM --platform=linux/amd64 mcr.microsoft.com/playwright/python:v1.48.0-jammy

# 作業ディレクトリを設定
WORKDIR /app

# Pythonパッケージをインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY main.py .
COPY service_account.json .

# 環境変数の設定（Cloud Run Jobsでオーバーライド可能）
ENV LOG_LEVEL=INFO
ENV HEADLESS=true
ENV PYTHONUNBUFFERED=1

# スクリプトを実行
CMD ["python", "main.py"]

