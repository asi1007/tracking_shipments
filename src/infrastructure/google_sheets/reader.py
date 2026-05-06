"""Google Sheetsから追跡番号を読み込むクラス"""
import logging
from typing import List
from .base import GoogleSheetsBase
from .column_config import ColumnConfig

logger = logging.getLogger(__name__)


class GoogleSheetsReader(GoogleSheetsBase):
    """Google Sheetsから追跡番号を読み込むクラス"""
    
    def __init__(self, credentials_file: str, spreadsheet_id: str):
        """
        初期化
        
        Args:
            credentials_file: Google Sheets API認証情報ファイルのパス
            spreadsheet_id: スプレッドシートID
        """
        super().__init__(credentials_file, spreadsheet_id)
        self.column_config = ColumnConfig(credentials_file, spreadsheet_id)
    
    def get_tracking_numbers(self) -> List[str]:
        """
        仕入管理シートから追跡番号を取得
        
        Returns:
            追跡番号のリスト（重複なし、条件でフィルタ済み）
        """
        try:
            # 列設定を読み込み
            self.column_config.load()
            
            # 列番号を取得
            stock_status_col = self.column_config.get('在庫状態')
            tracking_number_col = self.column_config.get('追跡番号')
            
            if not stock_status_col or not tracking_number_col:
                logger.error("列設定が見つかりません（在庫状態、追跡番号）")
                return []
            
            # 0ベースのインデックスに変換
            stock_status_idx = stock_status_col - 1
            tracking_number_idx = tracking_number_col - 1
            
            logger.info(f"列設定: 在庫状態={stock_status_col}, 追跡番号={tracking_number_col}")
            
            # 利用可能なシート名を取得
            all_worksheets = self.spreadsheet.worksheets()
            sheet_names = [ws.title for ws in all_worksheets]
            logger.debug(f"利用可能なシート: {sheet_names}")
            
            # 仕入管理シートを開く（複数のパターンを試行）
            worksheet = None
            possible_names = ["仕入管理シート", "仕入管理", "Sheet1"]
            
            for name in possible_names:
                try:
                    worksheet = self.spreadsheet.worksheet(name)
                    logger.info(f"'{name}' シートを開きました")
                    break
                except:
                    continue
            
            if not worksheet:
                logger.error(f"仕入管理シートが見つかりません。利用可能なシート: {sheet_names}")
                return []
            
            # シートの全データを取得
            # 5行目から10000行目まで取得（空行を含めてすべて取得）
            # 39列目（AM列）まで取得するため、範囲を拡張
            all_data = worksheet.get('A5:AO10000')
            
            logger.debug(f"取得行数: {len(all_data)}行")
            
            tracking_numbers = []
            
            # 各行を処理
            for row in all_data:
                # 列設定に基づいてデータを取得
                stock_status = row[stock_status_idx].strip() if len(row) > stock_status_idx and row[stock_status_idx] else ""
                tracking_number = row[tracking_number_idx].strip() if len(row) > tracking_number_idx and row[tracking_number_idx] else ""
                
                # 追跡番号があり、#N/A以外の場合に取得（在庫状態は無視）
                if tracking_number and tracking_number != "#N/A":
                    tracking_numbers.append(tracking_number)
            
            # 重複を削除（順序を保持）
            unique_tracking_numbers = list(dict.fromkeys(tracking_numbers))
            logger.info(f"追跡番号を取得: {len(unique_tracking_numbers)}件（重複削除前: {len(tracking_numbers)}件）")
            
            return unique_tracking_numbers
            
        except Exception as e:
            logger.error(f"追跡番号の取得に失敗: {e}")
            return []

