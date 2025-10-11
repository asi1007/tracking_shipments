#!/usr/bin/env python3
"""
貨物追跡情報取得スクリプト
Google Sheetsから追跡番号を取得し、ブラウザで追跡情報を取得してシートに書き込む
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from playwright.async_api import async_playwright
import asyncio
import time
import sys
import logging
import os
from typing import List, Dict, Tuple

# ロガーの設定（環境変数でログレベルを変更可能）
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
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


class GoogleSheetsReader(GoogleSheetsBase):
    """Google Sheetsから追跡番号を読み込むクラス"""
    
    def get_tracking_numbers(self) -> List[str]:
        """
        仕入管理シートから追跡番号を取得
        
        Returns:
            追跡番号のリスト（重複なし、条件でフィルタ済み）
        """
        try:
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
            
            # シートの全データを取得（G列とAC列を含む範囲）
            # 5行目から10000行目まで取得（空行を含めてすべて取得）
            all_data = worksheet.get('A5:AC10000')
            
            logger.debug(f"取得行数: {len(all_data)}行")
            
            tracking_numbers = []
            
            # 各行を処理
            for row in all_data:
                # G列（インデックス6）とAC列（インデックス28）を取得
                g_value = row[6].strip() if len(row) > 6 and row[6] else ""
                tracking_number = row[28].strip() if len(row) > 28 and row[28] else ""
                
                # #N/A や空白以外、かつ在庫管理対象外
                if tracking_number and tracking_number != "#N/A" and g_value not in ["在庫あり", "在庫なし"]:
                    tracking_numbers.append(tracking_number)
            
            # 重複を削除（順序を保持）
            unique_tracking_numbers = list(dict.fromkeys(tracking_numbers))
            logger.info(f"追跡番号を取得: {len(unique_tracking_numbers)}件（重複削除前: {len(tracking_numbers)}件）")
            
            return unique_tracking_numbers
            
        except Exception as e:
            logger.error(f"追跡番号の取得に失敗: {e}")
            return []


class TrackingInfoFetcher:
    """ブラウザで貨物追跡情報を取得するクラス"""
    
    TRACKING_URL = "https://japan-kaigen.com/download/"
    
    def __init__(self, max_concurrent: int = 3):
        """
        初期化
        
        Args:
            max_concurrent: 同時実行数の上限
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
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
                # ページに移動（初回のみ）
                if page.url != self.TRACKING_URL:
                    await page.goto(self.TRACKING_URL, wait_until="domcontentloaded")
                    await asyncio.sleep(2)
                
                # 追跡番号入力フィールドを探す（貨物追跡セクションのテキストエリア）
                try:
                    # 貨物追跡セクション（２）のテキストボックスを取得
                    input_field = page.get_by_role('textbox', name='追跡番号を入力します。スペース（又は改行）区切りで複数可。 結果は新しいタブ（ウインドウ）に表示されます。')
                    
                    if not await input_field.is_visible():
                        return [], "", "入力フィールドが見つかりません"
                    
                    # 入力フィールドをクリアして追跡番号を入力
                    await input_field.click()
                    await input_field.fill("")
                    await input_field.fill(tracking_number)
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    return [], "", f"入力フィールドの処理に失敗: {e}"
                
                # 追跡ボタンをクリック（新しいタブが開かれるのを監視）
                new_page = None
                try:
                    logger.debug(f"追跡番号 {tracking_number}: ボタンクリック準備")
                    
                    # 追跡ボタンをクリックして新しいページを待機
                    button = page.get_by_role('button', name='追跡')
                    
                    # ページが開かれるイベントを待機（タイムアウト20秒）
                    async with context.expect_event('page', timeout=20000) as event_info:
                        await button.click()
                        logger.debug(f"追跡番号 {tracking_number}: ボタンクリック完了、新しいタブ待機中...")
                    
                    # 新しいページを取得
                    new_page = await event_info.value
                    logger.debug(f"追跡番号 {tracking_number}: 新しいタブ取得完了 (URL: {new_page.url})")
                    
                    # ページが完全にロードされるまで待機
                    await new_page.wait_for_load_state('networkidle', timeout=20000)
                    logger.debug(f"追跡番号 {tracking_number}: ページロード完了")
                    
                    # テーブルが表示されるまで待機（最大10秒）
                    try:
                        await new_page.wait_for_selector('table', timeout=40000)
                        logger.debug(f"追跡番号 {tracking_number}: テーブル検出完了")
                    except:
                        # テーブルが見つからない場合でも続行（後でエラー処理）
                        logger.debug(f"追跡番号 {tracking_number}: テーブル待機タイムアウト（続行）")
                        pass
                    
                except asyncio.TimeoutError:
                    logger.warning(f"追跡番号 {tracking_number}: 新しいタブの読み込みがタイムアウト")
                    if new_page:
                        try:
                            await new_page.close()
                        except:
                            pass
                    return [], "", "新しいタブの読み込みがタイムアウトしました（20秒）"
                except Exception as e:
                    logger.warning(f"追跡番号 {tracking_number}: 新しいタブ取得エラー: {e}")
                    if new_page:
                        try:
                            await new_page.close()
                        except:
                            pass
                    return [], "", f"追跡ボタンのクリックまたは新しいタブの取得に失敗: {e}"
                
                # 新しいタブでテーブルデータを取得
                tracking_data = []
                notes = ""
                error_msg = ""
                
                try:
                    # new_pageが存在し、閉じられていないことを確認
                    if not new_page:
                        logger.warning(f"追跡番号 {tracking_number}: new_pageがNone")
                        return [], "", "新しいページが取得できませんでした"
                    
                    if new_page.is_closed():
                        logger.warning(f"追跡番号 {tracking_number}: new_pageが既に閉じられています")
                        return [], "", "新しいページが既に閉じられています"
                    
                    # ページ全体のHTMLを取得（ページが閉じられる前に）
                    page_html = await new_page.content()
                    logger.debug(f"追跡番号 {tracking_number}: HTMLコンテンツ取得完了")
                    
                    # メインテーブルを取得
                    tables = await new_page.locator('table').all()
                    
                    if len(tables) == 0:
                        error_msg = "テーブルが見つかりません（データなし）"
                    else:
                        # 最初のテーブル（メインテーブル）から処理
                        main_table = tables[0]
                        rows = await main_table.locator('tr').all()
                        
                        logger.debug(f"追跡番号 {tracking_number}: {len(rows)}行のテーブルデータ処理開始")
                        
                        # 各行を処理（データを即座に取得してリストに保存）
                        for row_idx, row in enumerate(rows):
                            try:
                                cells = await row.locator('td').all()
                                
                                # 3列あるかチェック（NO., 追跡番号, 状態）
                                if len(cells) >= 3:
                                    # 3列目（状態列）にネストされたテーブルがあるか確認
                                    nested_table = cells[2].locator('table').first
                                    
                                    try:
                                        is_visible = await nested_table.is_visible()
                                        if is_visible:
                                            # ネストされたテーブルから各行を取得
                                            nested_rows = await nested_table.locator('tr').all()
                                            
                                            for nested_row in nested_rows:
                                                nested_cells = await nested_row.locator('td').all()
                                                
                                                if len(nested_cells) >= 2:
                                                    # データを即座に取得
                                                    date = (await nested_cells[0].inner_text()).strip()
                                                    location_status = (await nested_cells[1].inner_text()).strip()
                                                    
                                                    if date and location_status:
                                                        tracking_data.append({
                                                            'date': date,
                                                            'location': location_status.split()[0] if location_status else '',
                                                            'status': location_status
                                                        })
                                    except Exception as nested_error:
                                        logger.debug(f"追跡番号 {tracking_number} 行{row_idx}: ネストテーブル解析エラー: {nested_error}")
                                
                                # 特記事項の行をチェック（2列でcolspanされている可能性）
                                if len(cells) >= 2:
                                    try:
                                        cell_text = (await cells[1].inner_text()).strip()
                                        if cell_text.startswith('特記事項'):
                                            notes = cell_text.replace('特記事項：', '').strip()
                                    except:
                                        pass
                            
                            except Exception as row_error:
                                logger.debug(f"追跡番号 {tracking_number} 行{row_idx}: 行処理エラー: {row_error}")
                                continue
                        
                        logger.debug(f"追跡番号 {tracking_number}: データ取得完了 {len(tracking_data)}件")
                        
                        # データが見つからない場合
                        if not tracking_data:
                            if '件数が見つかりません' in page_html or '該当する荷物がありません' in page_html:
                                error_msg = "該当する追跡情報が見つかりません"
                            else:
                                error_msg = "データの解析に失敗しました"
                    
                except Exception as e:
                    error_msg = f"データ取得エラー: {e}"
                    logger.debug(f"追跡番号 {tracking_number}: データ取得エラー詳細: {e}", exc_info=True)
                
                # 新しいタブを必ず閉じる
                finally:
                    if new_page and not new_page.is_closed():
                        try:
                            await new_page.close()
                        except:
                            pass
                
                if error_msg:
                    return [], "", error_msg
                
                return tracking_data, notes, ""
                
            except Exception as e:
                return [], "", f"エラー: {e}"


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


class ShipmentTrackingManager:
    """全体を統括するマネージャークラス"""
    
    SPREADSHEET_ID = "1Dvz3cS9DRGx4woEY0NNypgLPKxLZ55a4j8778YlCFls"
    MAX_CONCURRENT = 3  # 同時実行数の上限（サーバー負荷を考慮）
    
    def __init__(self, credentials_file: str = "service_account.json"):
        """
        初期化
        
        Args:
            credentials_file: Google Sheets API認証情報ファイルのパス
        """
        self.credentials_file = credentials_file
        self.reader = GoogleSheetsReader(credentials_file, self.SPREADSHEET_ID)
        self.fetcher = TrackingInfoFetcher(self.MAX_CONCURRENT)
        self.writer = GoogleSheetsWriter(credentials_file, self.SPREADSHEET_ID)
    
    async def fetch_tracking_number(self, tracking_number: str, context, task_number: int, total: int):
        """
        1つの追跡番号の情報を取得（非同期、書き込みなし）
        
        Args:
            tracking_number: 追跡番号
            context: Playwrightのブラウザコンテキスト
            task_number: タスク番号
            total: 総タスク数
            
        Returns:
            処理結果の辞書
        """
        result = {
            'task_number': task_number,
            'total': total,
            'tracking_number': tracking_number,
            'status': 'processing',
            'tracking_data': [],
            'notes': '',
            'error': ''
        }
        
        # 新しいページを作成
        page = await context.new_page()
        
        try:
            # 追跡情報を取得
            tracking_data, notes, error = await self.fetcher.fetch_tracking_info(tracking_number, page, context)
            
            if error:
                result['status'] = 'error'
                result['error'] = error
            elif not tracking_data:
                result['status'] = 'no_data'
            else:
                result['status'] = 'success'
                result['tracking_data'] = tracking_data
                result['notes'] = notes
            
        except Exception as e:
            result['status'] = 'error'
            result['error'] = str(e)
        finally:
            # ページを閉じる
            await page.close()
        
        return result
    
    async def fetch_all_tracking_info(self, tracking_numbers: List[str]):
        """
        全追跡番号の情報を非同期で取得
        
        Args:
            tracking_numbers: 追跡番号のリスト
            
        Returns:
            全追跡結果のリスト
        """
        logger.info(f"追跡情報の取得を開始: {len(tracking_numbers)}件（同時実行数: 最大{self.MAX_CONCURRENT}件）")
        
        async with async_playwright() as p:
            # ブラウザを起動
            browser = await p.chromium.launch(headless=False)  # headless=Trueで非表示モードに変更可能
            context = await browser.new_context()
            
            # すべての追跡番号を非同期で取得
            tasks = [
                self.fetch_tracking_number(tracking_number, context, i+1, len(tracking_numbers))
                for i, tracking_number in enumerate(tracking_numbers)
            ]
            
            # 全タスクを並列実行（セマフォで同時実行数を制限）
            results = await asyncio.gather(*tasks)
            
            await browser.close()
        
        logger.info(f"追跡情報の取得が完了: {len(results)}件")
        return results
    
    def write_all_tracking_info(self, results: List[Dict]):
        """
        取得した全追跡情報をまとめて書き込み
        
        Args:
            results: 全追跡結果のリスト
        """
        logger.info(f"追跡情報の書き込みを開始: {len(results)}件")
        
        # trackingシートをクリア（または作成）
        try:
            try:
                worksheet = self.writer.spreadsheet.worksheet("tracking")
                # 既存のシートの場合、すべてクリア
                worksheet.clear()
                logger.info("trackingシートをクリアしました")
            except:
                # シートが存在しない場合は作成
                worksheet = self.writer.spreadsheet.add_worksheet(title="tracking", rows="1000", cols="10")
                logger.info("trackingシートを作成しました")
            
            # ヘッダーを設定
            worksheet.update('A1:E1', [['追跡番号', '日付', '場所', '配送状況', '特記事項']])
            logger.info("ヘッダーを設定しました")
            
        except Exception as e:
            logger.error(f"シートの準備に失敗: {e}")
            raise
        
        success_count = 0
        error_count = 0
        no_data_count = 0
        
        for result in results:
            tracking_number = result['tracking_number']
            status = result['status']
            
            try:
                if status == 'success':
                    tracking_data = result['tracking_data']
                    notes = result['notes']
                    self.writer.write_tracking_info(tracking_number, tracking_data, notes)
                    success_count += 1
                elif status == 'no_data':
                    self.writer.write_tracking_info(tracking_number, [], "")
                    no_data_count += 1
                elif status == 'error':
                    # エラーの場合もエラー情報を書き込む
                    error = result['error']
                    self.writer.write_tracking_info(tracking_number, [], error)
                    error_count += 1
            except Exception as e:
                logger.error(f"{tracking_number} の書き込みに失敗: {e}")
                error_count += 1
        
        logger.info(f"書き込み完了 - 成功: {success_count}件, データなし: {no_data_count}件, エラー: {error_count}件")
    
    def display_results(self, results: List[Dict]):
        """
        取得結果を表示
        
        Args:
            results: 全追跡結果のリスト
        """
        logger.info("=" * 80)
        logger.info("取得結果サマリー")
        logger.info("=" * 80)
        
        success_count = 0
        error_count = 0
        no_data_count = 0
        
        for result in results:
            tracking_num = result['tracking_number']
            status = result['status']
            
            if status == 'success':
                success_count += 1
                data_count = len(result['tracking_data'])
                notes = result['notes']
                log_msg = f"✓ {tracking_num}: データ {data_count}件"
                if notes:
                    log_msg += f" (特記事項: {notes})"
                logger.info(log_msg)
            elif status == 'no_data':
                no_data_count += 1
                logger.warning(f"⚠ {tracking_num}: データなし")
            elif status == 'error':
                error_count += 1
                error = result['error']
                logger.error(f"✗ {tracking_num}: {error}")
        
        logger.info("=" * 80)
        logger.info(f"集計 - 成功: {success_count}件, データなし: {no_data_count}件, エラー: {error_count}件, 合計: {len(results)}件")
        logger.info("=" * 80)
    
    def run(self):
        """メイン処理を実行"""
        logger.info("貨物追跡情報取得スクリプト - 開始")
        
        try:
            # [1/4] Google Sheetsに接続（読み込み用）
            logger.info("[1/4] Google Sheets接続中（読み込み用）")
            self.reader.connect()
            tracking_numbers = self.reader.get_tracking_numbers()
            
            if not tracking_numbers:
                logger.warning("追跡番号が見つかりませんでした。処理を終了します。")
                return
            
            # [3/4] 追跡情報を一括取得
            logger.info("[3/4] 追跡情報の取得フェーズ")
            results = asyncio.run(self.fetch_all_tracking_info(tracking_numbers))
            self.display_results(results)
            
            # [4/4] Google Sheetsに書き込み
            logger.info("[4/4] 追跡情報の書き込みフェーズ")
            self.writer.connect()
            self.write_all_tracking_info(results)
            
            logger.info("✓ すべての処理が正常に完了しました")
        except Exception as e:
            logger.error(f"処理中にエラーが発生しました: {e}", exc_info=True)
            raise


def main():
    """エントリーポイント"""
    manager = ShipmentTrackingManager()
    manager.run()


if __name__ == "__main__":
    main()