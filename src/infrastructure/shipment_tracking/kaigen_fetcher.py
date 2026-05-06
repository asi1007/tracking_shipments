"""Kaigenサイト用フェッチャークラス"""
import asyncio
import logging
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)


class KaigenTrackingFetcher:
    """Kaigenサイト用フェッチャークラス"""
    TRACKING_URL = "https://japan-kaigen.com/download/"
    
    async def fetch(self, tracking_number: str, page, context) -> Tuple[List[Dict[str, str]], str, str]:
        """Kaigenサイトから追跡情報を取得"""
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
                
                # ページが開かれるイベントを待機（タイムアウト60秒）
                async with context.expect_event('page', timeout=60000) as event_info:
                    await button.click()
                    logger.debug(f"追跡番号 {tracking_number}: ボタンクリック完了、新しいタブ待機中...")
                
                # 新しいページを取得
                new_page = await event_info.value
                logger.debug(f"追跡番号 {tracking_number}: 新しいタブ取得完了 (URL: {new_page.url})")
                
                # ページが完全にロードされるまで待機
                await new_page.wait_for_load_state('networkidle', timeout=60000)
                logger.debug(f"追跡番号 {tracking_number}: ページロード完了")
                
                # テーブルが表示されるまで待機（最大90秒）
                try:
                    await new_page.wait_for_selector('table', timeout=90000)
                    logger.debug(f"追跡番号 {tracking_number}: テーブル検出完了")
                except:
                    # テーブルが見つからない場合でも続行（後でエラー処理）
                    logger.debug(f"追跡番号 {tracking_number}: テーブル待機タイムアウト（続行）")
                    pass
                
            except asyncio.TimeoutError:
                logger.warning(f"追跡番号 {tracking_number}: 新しいタブの読み込みがタイムアウト（60秒）")
                if new_page:
                    try:
                        await new_page.close()
                    except:
                        pass
                return [], "", "新しいタブの読み込みがタイムアウトしました（60秒）"
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

