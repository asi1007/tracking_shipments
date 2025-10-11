# AMD64アーキテクチャを明示的に指定
FROM --platform=linux/amd64 python:3.11-bookworm

# 作業ディレクトリを設定
WORKDIR /app

# システムパッケージを更新
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Pythonパッケージをインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwrightブラウザと依存関係をインストール（AMD64用）
RUN playwright install chromium
RUN playwright install-deps chromium

# アプリケーションコードをコピー
COPY main.py .
COPY service_account.json .

# 環境変数の設定（Cloud Run Jobsでオーバーライド可能）
ENV LOG_LEVEL=INFO
ENV HEADLESS=true
ENV PYTHONUNBUFFERED=1

# スクリプトを実行
CMD ["python", "main.py"]

