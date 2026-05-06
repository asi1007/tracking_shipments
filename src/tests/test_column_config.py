"""列設定クラスのテスト"""
import pytest
from unittest.mock import Mock, patch
from infrastructure.google_sheets.column_config import ColumnConfig


class TestColumnConfig:
    """ColumnConfigのテストクラス"""
    
    def test_初期化(self):
        """初期化が正常に行われる"""
        config = ColumnConfig("service_account.json", "test_spreadsheet_id")
        assert config.credentials_file == "service_account.json"
        assert config.spreadsheet_id == "test_spreadsheet_id"
        assert config.config_sheet_name == "設定"
    
    def test_初期化_カスタムシート名(self):
        """カスタムシート名で初期化できる"""
        config = ColumnConfig("service_account.json", "test_id", "カスタム設定")
        assert config.config_sheet_name == "カスタム設定"
    
    @patch('infrastructure.google_sheets.column_config.gspread.authorize')
    @patch('infrastructure.google_sheets.column_config.ServiceAccountCredentials.from_json_keyfile_name')
    def test_load_正常(self, mock_credentials, mock_authorize):
        """設定シートから正常に読み込める"""
        # モックの設定
        mock_worksheet = Mock()
        mock_worksheet.get_all_values.return_value = [
            ['fnsku', '80', ''],
            ['asin', '4', ''],
            ['数量', '18', ''],
            ['依頼日', '33', 'ここは実際より1少なくする'],
            ['', '', ''],  # 空行
            ['invalid', 'abc', ''],  # 無効な列番号
        ]
        
        mock_spreadsheet = Mock()
        mock_spreadsheet.worksheet.return_value = mock_worksheet
        
        mock_client = Mock()
        mock_client.open_by_key.return_value = mock_spreadsheet
        
        mock_authorize.return_value = mock_client
        
        # テスト実行
        config = ColumnConfig("service_account.json", "test_id")
        config.load()
        
        # 検証
        assert config.get('fnsku') == 80
        assert config.get('asin') == 4
        assert config.get('数量') == 18
        assert config.get('依頼日') == 33
        assert config.get('invalid') is None  # 無効な行はスキップ
        assert config.get('存在しない列') is None

