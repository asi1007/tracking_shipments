"""全体を統括するマネージャークラス"""
import asyncio
import logging
import os
from typing import List, Dict
from playwright.async_api import async_playwright
from ..infrastructure.google_sheets.reader import GoogleSheetsReader
from ..infrastructure.google_sheets.writer import GoogleSheetsWriter
from ..infrastructure.shipment_tracking.tracking_info_fetcher import TrackingInfoFetcher

logger = logging.getLogger(__name__)


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
    
    async def fetch_tracking_number(self, tracking_number: str, context, task_number: int, total: int, max_retries: int = 3):
        """
        1つの追跡番号の情報を取得（非同期、書き込みなし、指数バックオフでリトライ）
        
        Args:
            tracking_number: 追跡番号
            context: Playwrightのブラウザコンテキスト
            task_number: タスク番号
            total: 総タスク数
            max_retries: 最大リトライ回数（デフォルト: 3）
            
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
        
        # 指数バックオフでリトライ
        for attempt in range(max_retries):
            # 新しいページを作成
            page = await context.new_page()
            
            try:
                # 追跡情報を取得
                tracking_data, notes, error = await self.fetcher.fetch_tracking_info(tracking_number, page, context)
                
                if error:
                    result['status'] = 'error'
                    result['error'] = error
                    
                    # タイムアウトエラーの場合はリトライ
                    if 'Timeout' in error or 'timeout' in error.lower():
                        if attempt < max_retries - 1:
                            wait_time = 2 ** (attempt + 1)  # 指数バックオフ: 2, 4, 8秒
                            logger.info(f"追跡番号 {tracking_number}: リトライ {attempt + 1}/{max_retries - 1} ({wait_time}秒待機)")
                            await page.close()
                            await asyncio.sleep(wait_time)
                            continue
                    
                elif not tracking_data:
                    result['status'] = 'no_data'
                else:
                    result['status'] = 'success'
                    result['tracking_data'] = tracking_data
                    result['notes'] = notes
                
                # 成功またはリトライ不要なエラーの場合は終了
                await page.close()
                break
                
            except Exception as e:
                result['status'] = 'error'
                result['error'] = str(e)
                
                # 例外の場合もリトライ
                if attempt < max_retries - 1:
                    wait_time = 2 ** (attempt + 1)  # 指数バックオフ
                    logger.info(f"追跡番号 {tracking_number}: エラー発生、リトライ {attempt + 1}/{max_retries - 1} ({wait_time}秒待機)")
                    await page.close()
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    await page.close()
                    break
        
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
            # ブラウザを起動（Cloud Run Jobs用にヘッドレスモード対応）
            headless = os.getenv('HEADLESS', 'false').lower() == 'true'
            browser = await p.chromium.launch(headless=headless)
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
        取得した全追跡情報をまとめて書き込み（バッチ処理でレート制限を回避）
        
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
            
            # すべてのデータを一つの配列に集める
            all_rows = [['追跡番号', '日付', '場所', '配送状況', '特記事項']]  # ヘッダー
            
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
                        
                        # 各追跡情報を行として追加
                        for i, data in enumerate(tracking_data):
                            note_to_write = notes if i == 0 else ""
                            all_rows.append([
                                tracking_number,
                                data['date'],
                                data['location'],
                                data['status'],
                                note_to_write
                            ])
                        success_count += 1
                        
                    elif status == 'no_data':
                        all_rows.append([tracking_number, '', '', 'データなし', ''])
                        no_data_count += 1
                        
                    elif status == 'error':
                        error = result['error']
                        all_rows.append([tracking_number, '', '', error, ''])
                        error_count += 1
                        
                except Exception as e:
                    logger.error(f"{tracking_number} のデータ準備に失敗: {e}")
                    all_rows.append([tracking_number, '', '', f'エラー: {e}', ''])
                    error_count += 1
            
            # 一度にすべてのデータを書き込む（バッチ更新）
            if len(all_rows) > 1:  # ヘッダー以外にデータがある場合
                # データの範囲を計算（行数と列数）
                num_rows = len(all_rows)
                num_cols = 5  # 追跡番号、日付、場所、配送状況、特記事項
                
                # 範囲を計算（A1から最終列・最終行まで）
                # 列番号をアルファベットに変換（A=1, B=2, ... E=5）
                end_col = chr(64 + num_cols)  # 5 → 'E'
                range_notation = f'A1:{end_col}{num_rows}'
                
                logger.info(f"バッチ更新を実行: {num_rows}行 × {num_cols}列（範囲: {range_notation}）")
                worksheet.update(range_notation, all_rows)
                logger.info("バッチ更新完了")
                logger.info(f"✓ データ書き込み完了: {range_notation}")
                logger.info(f"※ 名前付き範囲「tracking」を使用している場合は、範囲を {range_notation} に更新してください")
            
            logger.info(f"書き込み完了 - 成功: {success_count}件, データなし: {no_data_count}件, エラー: {error_count}件")
            
        except Exception as e:
            logger.error(f"シートへの書き込みに失敗: {e}")
            raise
    
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
            
            logger.info(f"取得した追跡番号: {tracking_numbers}")
            
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

