"""列設定を管理するクラス

Google Spreadsheetsの「設定」シートから列番号を読み取り、管理する
"""
import logging
from typing import Dict, Optional
import gspread
from oauth2client.service_account import ServiceAccountCredentials

logger = logging.getLogger(__name__)


class ColumnConfig:
    """列設定クラス - Googleスプレッドシートから列番号設定を読み込む"""
    
    def __init__(
        self,
        credentials_file: str,
        spreadsheet_id: str,
        config_sheet_name: str = "設定"
    ):
        """
        初期化
        
        Args:
            credentials_file: Google Sheets API認証情報ファイルのパス
            spreadsheet_id: スプレッドシートID
            config_sheet_name: 設定シート名（デフォルト: "設定"）
        """
        self.credentials_file = credentials_file
        self.spreadsheet_id = spreadsheet_id
        self.config_sheet_name = config_sheet_name
        self._client: Optional[gspread.Client] = None
        self._columns: Dict[str, int] = {}
    
    def _connect(self) -> gspread.Client:
        """Google Sheetsに接続"""
        if self._client is None:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            credentials = ServiceAccountCredentials.from_json_keyfile_name(
                self.credentials_file, scope
            )
            self._client = gspread.authorize(credentials)
            logger.debug("Google Sheetsに接続しました")
        return self._client
    
    def load(self):
        """設定シートから列番号を読み込む"""
        try:
            client = self._connect()
            spreadsheet = client.open_by_key(self.spreadsheet_id)
            worksheet = spreadsheet.worksheet(self.config_sheet_name)
            
            # すべてのデータを取得
            all_data = worksheet.get_all_values()
            
            self._columns.clear()
            
            for row in all_data:
                if len(row) < 2:
                    continue
                
                # 列名と列番号を取得
                name = row[0].strip() if row[0] else ""
                column_number_str = row[1].strip() if len(row) > 1 and row[1] else ""
                
                # 列名と列番号が両方存在する場合のみ処理
                if name and column_number_str:
                    try:
                        column_num = int(column_number_str)
                        self._columns[name] = column_num
                        logger.debug(f"列設定を読み込み: {name} = {column_num}")
                    except ValueError:
                        logger.warning(f"列設定の読み込みをスキップ: {name} (列番号が数値ではない: {column_number_str})")
                        continue
            
            logger.info(f"列設定を{len(self._columns)}件読み込みました")
            
        except Exception as e:
            logger.error(f"列設定の取得に失敗: {e}")
            raise
    
    def get(self, name: str) -> Optional[int]:
        """
        列名から列番号を取得
        
        Args:
            name: 列名
            
        Returns:
            列番号（見つからない場合はNone）
        """
        return self._columns.get(name)

