"""Google Sheetsにデータを書き込むクラス"""
import logging
from typing import List, Dict
from .base import GoogleSheetsBase

logger = logging.getLogger(__name__)


class GoogleSheetsWriter(GoogleSheetsBase):
    """Google Sheetsにデータを書き込むクラス"""
    
    def write_tracking_info(self, tracking_number: str, tracking_data: List[Dict[str, str]], notes: str = ""):
        """
        trackingシートに追跡情報を書き込む
        
        Args:
            tracking_number: 追跡番号
            tracking_data: 追跡情報のリスト
            notes: 特記事項
        """
        # trackingシートを開く
        worksheet = self.spreadsheet.worksheet("tracking")
        
        # データがない場合
        if not tracking_data:
            # notesがエラーメッセージの場合は配送状況列に記載
            if notes and (notes.startswith("エラー:") or notes.startswith("データ取得エラー:") or notes.startswith("テーブルが見つかりません")):
                worksheet.append_row([tracking_number, '', '', notes, ''])
            else:
                worksheet.append_row([tracking_number, '', '', 'データなし', notes])
        else:
            # 各追跡情報を1行ずつ追加
            for i, data in enumerate(tracking_data):
                # 特記事項は最初の行のみに記載
                note_to_write = notes if i == 0 else ""
                worksheet.append_row([
                    tracking_number,
                    data['date'],
                    data['location'],
                    data['status'],
                    note_to_write
                ])

