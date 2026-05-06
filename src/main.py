#!/usr/bin/env python3
"""
貨物追跡情報取得スクリプト
Google Sheetsから追跡番号を取得し、ブラウザで追跡情報を取得してシートに書き込む
"""

import logging
import os
from usecases.shipment_tracking_manager import ShipmentTrackingManager

# ロガーの設定（環境変数でログレベルを変更可能）
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def main():
    """エントリーポイント"""
    manager = ShipmentTrackingManager()
    manager.run()


if __name__ == "__main__":
    main()

