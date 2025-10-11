# Python 3.11のベースイメージを使用
FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# システムパッケージの更新とPlaywright用の依存関係をインストール
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Pythonパッケージをインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwrightブラウザをインストール
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

