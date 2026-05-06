"""Google Sheetsの基底クラス"""
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import sys
import logging

logger = logging.getLogger(__name__)


class GoogleSheetsBase:
    """Google Sheetsの基底クラス"""
    
    def __init__(self, credentials_file: str, spreadsheet_id: str):
        """
        初期化
        
        Args:
            credentials_file: Google Sheets API認証情報ファイルのパス
            spreadsheet_id: スプレッドシートID
        """
        self.credentials_file = credentials_file
        self.spreadsheet_id = spreadsheet_id
        self.client = None
        self.spreadsheet = None
    
    def connect(self):
        """Google Sheetsに接続"""
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            credentials = ServiceAccountCredentials.from_json_keyfile_name(
                self.credentials_file, scope
            )
            self.client = gspread.authorize(credentials)
            self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            logger.info("Google Sheetsに接続しました")
        except Exception as e:
            logger.error(f"Google Sheetsへの接続に失敗しました: {e}")
            sys.exit(1)

