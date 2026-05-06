"""ブラウザで貨物追跡情報を取得するクラス（サイト別フェッチャーに委譲）"""
import asyncio
import logging
from typing import List, Dict, Tuple
from .kaigen_fetcher import KaigenTrackingFetcher
from .ocs_fetcher import OCSTrackingFetcher

logger = logging.getLogger(__name__)


class TrackingInfoFetcher:
    """ブラウザで貨物追跡情報を取得するクラス（サイト別フェッチャーに委譲）"""
    
    def __init__(self, max_concurrent: int = 3):
        """
        初期化
        
        Args:
            max_concurrent: 同時実行数の上限
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        # サイト別フェッチャー
        self._kaigen_fetcher = KaigenTrackingFetcher()
        self._ocs_fetcher = OCSTrackingFetcher()
    
    async def fetch_tracking_info(self, tracking_number: str, page, context) -> Tuple[List[Dict[str, str]], str, str]:
        """
        ブラウザで追跡情報を取得（非同期）
        
        Args:
            tracking_number: 追跡番号
            page: Playwrightのページオブジェクト
            context: Playwrightのブラウザコンテキスト
            
        Returns:
            (追跡情報のリスト, 特記事項, エラーメッセージ) のタプル
        """
        async with self.semaphore:  # 同時実行数を制限
            try:
                # 追跡番号のプレフィックスで振り分け（YP は従来サイト、それ以外はOCS）
                if not tracking_number:
                    return [], "", "追跡番号が空です"

                if tracking_number.upper().startswith("YP"):
                    # 従来のKaigenサイトで取得
                    return await self._kaigen_fetcher.fetch(tracking_number, page, context)
                else:
                    # OCSサイトで取得
                    return await self._ocs_fetcher.fetch(tracking_number, page, context)
            except Exception as e:
                return [], "", f"エラー: {e}"

