"""OCSサイト用フェッチャークラス"""
import asyncio
import logging
import re
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)


class OCSTrackingFetcher:
    """OCSサイト用フェッチャークラス"""
    TRACKING_URL_OCS = "https://www2.ocsworldwide.net/ExpTracking/cwbCheck.html"
    
    async def fetch(self, tracking_number: str, page, context) -> Tuple[List[Dict[str, str]], str, str]:
        """
        OCS Worldwideの貨物状況照会から追跡情報を取得
        参考: https://www2.ocsworldwide.net/ExpTracking/cwbCheck.html
        """
        try:
            # tracking_dataを最初に初期化
            tracking_data: List[Dict[str, str]] = []
            
            # OCSは数字のみ（ハイフン除去）。数字以外はそのまま試行し、失敗時にエラー返却
            awb = ''.join(ch for ch in tracking_number if ch.isdigit()) or tracking_number

            if page.url != self.TRACKING_URL_OCS:
                await page.goto(self.TRACKING_URL_OCS, wait_until="domcontentloaded")
                await asyncio.sleep(2)

            # 入力ボックス取得（実際のHTMLはname='cwbno'（小文字）、id='cwbno'（小文字））
            input_field = None
            target_frame = None
            # セレクタリスト（大文字小文字両方を試行）
            selectors = [
                "input[name='cwbno']",  # 小文字（実際のHTML）
                "input[name='cwbNo']",  # 大文字小文字混在
                "#cwbno",  # 小文字のID
                "#cwbNo",  # 大文字小文字混在のID
                "input[id='cwbno']",
                "input[id='cwbNo']",
                "input[type='tel']",  # type=tel（実際のHTML）
                "input[type='text']"
            ]
            
            # メインページで探索
            for sel in selectors:
                try:
                    el = page.locator(sel).first
                    count = await el.count()
                    if count > 0:
                        is_visible = await el.is_visible()
                        if is_visible:
                            input_field = el
                            target_frame = None
                            logger.debug(f"OCS: 入力フィールド発見 (メインページ): {sel}")
                            break
                except:
                    continue
            
            # iframe内も探索
            if input_field is None:
                for fr in page.frames:
                    try:
                        for sel in selectors:
                            try:
                                el = fr.locator(sel).first
                                count = await el.count()
                                if count > 0:
                                    is_visible = await el.is_visible()
                                    if is_visible:
                                        input_field = el
                                        target_frame = fr
                                        logger.debug(f"OCS: 入力フィールド発見 (iframe): {sel}")
                                        break
                            except:
                                continue
                        if input_field:
                            break
                    except:
                        continue

            if input_field is None:
                # ロール検索のフォールバック
                try:
                    candidate = page.get_by_role('textbox')
                    if await candidate.is_visible():
                        input_field = candidate
                        target_frame = None
                except:
                    pass

            if input_field is None:
                # デバッグ: ページのHTML構造を確認
                try:
                    logger.debug(f"OCS: ページURL: {page.url}")
                    # すべてのinput要素を確認
                    all_inputs = await page.locator('input').all()
                    logger.debug(f"OCS: 検出されたinput要素数: {len(all_inputs)}")
                    for i, inp in enumerate(all_inputs[:10]):  # 最初の10個
                        try:
                            name_attr = await inp.get_attribute('name')
                            id_attr = await inp.get_attribute('id')
                            type_attr = await inp.get_attribute('type')
                            placeholder = await inp.get_attribute('placeholder')
                            logger.debug(f"OCS: input[{i}] - name={name_attr}, id={id_attr}, type={type_attr}, placeholder={placeholder}")
                        except:
                            pass
                    # iframe内も確認
                    logger.debug(f"OCS: iframe数: {len(page.frames)}")
                    for idx, fr in enumerate(page.frames):
                        try:
                            frame_inputs = await fr.locator('input').all()
                            logger.debug(f"OCS: iframe[{idx}] - input要素数: {len(frame_inputs)}")
                            for i, inp in enumerate(frame_inputs[:5]):
                                try:
                                    name_attr = await inp.get_attribute('name')
                                    id_attr = await inp.get_attribute('id')
                                    logger.debug(f"OCS: iframe[{idx}] input[{i}] - name={name_attr}, id={id_attr}")
                                except:
                                    pass
                        except:
                            pass
                except Exception as e:
                    logger.debug(f"OCS: デバッグ情報取得エラー: {e}")
                return [], "", "OCS: 入力フィールドが見つかりません"

            await input_field.click()
            await input_field.fill("")
            await input_field.fill(awb)
            await asyncio.sleep(0.3)
            
            # Enterキーで送信を試す（検索ボタンの代替）- 一旦無効化して検索ボタンクリックに統一
            submitted = False

            # フォームを探してsubmitする方法を試す（Enterキーが失敗した場合のみ）
            if not submitted:
                try:
                    # 入力フィールドの親フォームを探す
                    form_element = None
                    if target_frame:
                        try:
                            form_element = await input_field.locator("xpath=ancestor::form").first
                            if await form_element.count() > 0:
                                await form_element.evaluate("form => form.submit()")
                                submitted = True
                                logger.debug("OCS: フォームをsubmit (iframe)")
                        except:
                            pass
                    else:
                        try:
                            form_element = await input_field.locator("xpath=ancestor::form").first
                            if await form_element.count() > 0:
                                await form_element.evaluate("form => form.submit()")
                                submitted = True
                                logger.debug("OCS: フォームをsubmit (メインページ)")
                        except:
                            pass
                except Exception as e:
                    logger.debug(f"OCS: フォームsubmitエラー: {e}")

            # フォームsubmitが失敗した場合は、検索ボタンをクリック（Enterキーとsubmitも失敗した場合）
            if not submitted:
                clicked = False
                def locate_btn(selector: str):
                    return (target_frame.locator(selector).first if target_frame else page.locator(selector).first)
                # 個別検索用のボタン（#ocs-num-submit）を優先的に探す
                for btn_sel in [
                    "#ocs-num-submit",  # 個別検索用ボタン（優先）
                    "button#ocs-num-submit",
                    "form[action*='cwbCheck'] button#ocs-num-submit",
                    "form[action*='cwbCheck'] button:has-text('検索する')",
                    "button:has-text('検索する')",
                    "input[type='submit']",
                    "button[type='submit']"
                ]:
                    btn = locate_btn(btn_sel)
                    if await btn.count() > 0:
                        try:
                            url_before = page.url
                            # 新しいウィンドウ（佐川など）を待つ
                            new_page = None
                            try:
                                async with context.expect_event('page', timeout=3000) as popup_info:  # 3秒待機（短縮）
                                    await btn.click()
                                new_page = await popup_info.value
                                clicked = True
                                logger.debug(f"OCS: 検索ボタンクリック ({btn_sel}) → 新規タブ検出: {new_page.url}")
                                
                                # 佐川の「詳細表示」テーブルから抽出（URL遷移待機を含む）
                                await self._parse_sagawa_detail_page(new_page, tracking_data)
                                try:
                                    await new_page.close()
                                except:
                                    pass
                                if tracking_data:  # データが取得できた場合のみbreak
                                    break
                            except Exception:
                                # 新規タブが開かれない場合は通常クリック（OCSサイト内に結果が表示される）
                                await btn.click()
                                clicked = True
                                logger.debug(f"OCS: 検索ボタンクリック ({btn_sel}, URL before: {url_before}) → 同一ページで結果表示")
                                break
                        except:
                            continue
                if not clicked:
                    try:
                        # 個別検索用ボタンをIDで直接指定
                        if target_frame:
                            try:
                                btn = target_frame.locator("#ocs-num-submit").first
                                if await btn.count() > 0:
                                    url_before = target_frame.url
                                    # 新規タブ待機
                                    new_page = None
                                    try:
                                        async with context.expect_event('page', timeout=3000) as popup_info:
                                            await btn.click()
                                        new_page = await popup_info.value
                                        clicked = True
                                        logger.debug(f"OCS: 個別検索ボタンクリック (iframe) → 新規タブ: {new_page.url}")
                                        # 新規タブからデータを取得
                                        await self._parse_sagawa_detail_page(new_page, tracking_data)
                                        try:
                                            await new_page.close()
                                        except:
                                            pass
                                    except:
                                        await btn.click()
                                        clicked = True
                                        logger.debug(f"OCS: 個別検索ボタンクリック (iframe) → 同一ページで結果表示")
                            except:
                                pass
                            # データが取得できた場合は処理を継続
                            if tracking_data:
                                clicked = True
                        if not clicked:
                            btn = page.locator("#ocs-num-submit").first
                            if await btn.count() > 0:
                                url_before = page.url
                                # 新規タブ待機
                                new_page = None
                                try:
                                    async with context.expect_event('page', timeout=3000) as popup_info:
                                        await btn.click()
                                    new_page = await popup_info.value
                                    clicked = True
                                    logger.debug(f"OCS: 個別検索ボタンクリック (メインページ) → 新規タブ: {new_page.url}")
                                    # 新規タブからデータを取得
                                    await self._parse_sagawa_detail_page(new_page, tracking_data)
                                    try:
                                        await new_page.close()
                                    except:
                                        pass
                                except:
                                    await btn.click()
                                    clicked = True
                                    logger.debug(f"OCS: 個別検索ボタンクリック (メインページ) → 同一ページで結果表示")
                    except Exception as e:
                        logger.debug(f"OCS: 検索ボタンクリックエラー: {e}")
                    
                    # データが取得できた場合は処理を継続（メインページでの処理へ）
                    if tracking_data:
                        clicked = True  # 既にクリック済みとして処理を継続

                if not clicked:
                    return [], "", "OCS: 検索ボタンが見つかりません"
            
            # クリック後に少し待機して、検索が実行されているか確認
            await asyncio.sleep(5)  # より長く待機
            
            # 検索が実行されているか確認（エラーメッセージや結果の有無を確認）
            try:
                page_text = await page.locator('body').inner_text()
                # エラーメッセージの確認
                if '見つかりません' in page_text or 'エラー' in page_text or 'error' in page_text.lower():
                    logger.debug(f"OCS: エラーメッセージを検出: {page_text[:500]}")
                # 検索結果が表示されているか確認
                if '詳細表示' in page_text or '⇒' in page_text or '↑' in page_text:
                    logger.debug("OCS: 検索結果が表示されている可能性あり")
            except:
                pass

            # 結果待機（検索結果が表示されるまで待機）
            try:
                # URLの変化を待つ（検索結果ページに遷移する場合）
                try:
                    await page.wait_for_function(
                        "document.readyState === 'complete'",
                        timeout=10000
                    )
                    current_url = page.url
                    logger.debug(f"OCS: 検索後のURL: {current_url}")
                except:
                    pass
                
                # 検索結果が表示されるまで待機（「詳細表示」や結果テーブルが出現するまで）
                max_wait = 30  # 最大30秒待機（JavaScriptでの動的表示を考慮）
                waited = 0
                result_appeared = False
                
                while waited < max_wait:
                    # 「詳細表示」テキストの出現を確認
                    try:
                        detail_elements = await page.locator("*:has-text('詳細表示')").all()
                        if len(detail_elements) > 0:
                            logger.debug("OCS: 詳細表示セクションが出現")
                            result_appeared = True
                            break
                    except:
                        pass
                    
                    # 「⇒」や「↑」の出現を確認
                    try:
                        arrow_elements = await page.locator("*:has-text('⇒'), *:has-text('↑')").all()
                        if len(arrow_elements) > 0:
                            logger.debug("OCS: 矢印記号が出現")
                            result_appeared = True
                            break
                    except:
                        pass
                    
                    # テーブルの出現を確認
                    try:
                        tables = await page.locator('table').all()
                        if len(tables) > 0:
                            # テーブルにデータがあるか確認
                            for table in tables:
                                rows = await table.locator('tr').all()
                                if len(rows) > 1:  # ヘッダー以外にデータ行がある
                                    logger.debug(f"OCS: データを含むテーブルが出現 (行数: {len(rows)})")
                                    result_appeared = True
                                    break
                            if result_appeared:
                                break
                    except:
                        pass
                    
                    await asyncio.sleep(1)  # 1秒ごとにチェック
                    waited += 1
                
                await page.wait_for_load_state('networkidle', timeout=60000)
                # 結果が表示されるまで少し待機（JavaScriptでの動的表示を考慮）
                await asyncio.sleep(5)
            except:
                pass
            
            # デバッグ: ページのテキスト内容とHTML構造を確認
            try:
                body_text = await page.locator('body').inner_text()
                logger.debug(f"OCS: ページテキスト（最初の3000文字）: {body_text[:3000]}")
                
                # HTMLの一部を取得（検索結果が含まれる可能性のある部分）
                page_html = await page.content()
                # 「詳細表示」を含む部分を抽出
                if '詳細表示' in page_html:
                    detail_match = re.search(r'詳細表示.*?詳細表示', page_html, re.DOTALL)
                    if detail_match:
                        logger.debug(f"OCS: 詳細表示部分のHTML（最初の1000文字）: {detail_match.group()[:1000]}")
                
                # iframeの内容も確認
                for idx, frame in enumerate(page.frames):
                    if frame != page.main_frame:
                        try:
                            frame_text = await frame.locator('body').inner_text()
                            if frame_text and len(frame_text.strip()) > 50:
                                logger.debug(f"OCS: iframe[{idx}] テキスト（最初の1000文字）: {frame_text[:1000]}")
                        except:
                            pass
            except Exception as e:
                logger.debug(f"OCS: デバッグ情報取得エラー: {e}")
            
            # 既に新規タブでtracking_dataが取れていればここで返す
            if tracking_data:
                return tracking_data, "", ""

            # 結果のテーブル探索（同一ページに出る場合）

            # OCSの詳細ページ（配送状況/日時/場所/メモの表）を優先的に解析
            if not tracking_data:
                try:
                    parsed = await self._parse_ocs_detail_in_page(page)
                    if parsed:
                        tracking_data.extend(parsed)
                        return tracking_data, "", ""
                except Exception as e:
                    logger.debug(f"OCS: OCS詳細表解析エラー: {e}", exc_info=True)

            # まずtableが出るケース
            tables = await page.locator('table').all()
            if len(tables) > 0:
                # それっぽいヘッダのあるテーブルを選定（簡易）
                target = tables[0]
                rows = await target.locator('tr').all()
                for r in rows:
                    cells = await r.locator('td,th').all()
                    if len(cells) >= 2:
                        try:
                            c0 = (await cells[0].inner_text()).strip()
                            c1 = (await cells[1].inner_text()).strip()
                            c2 = (await cells[2].inner_text()).strip() if len(cells) > 2 else ""
                            # 典型: 日付/場所/ステータス になるように整形
                            date = c0
                            location = c1
                            status = c2 or c1
                            if date or status:
                                tracking_data.append({'date': date, 'location': location, 'status': status})
                        except:
                            continue

            # テーブルから取れなければ、「詳細表示」配下の行をDOM/テキスト両面で解析
            page_html = await page.content()
            if not tracking_data:
                try:
                    # 日付パターン: 2025年09月24日 または 2025年09月24日 09:49
                    date_re = re.compile(r'(\d{4}年\d{2}月\d{2}日(?:\s*\d{2}:\d{2})?)')
                    
                    # 「詳細表示」セクションを特定して抽出
                    detail_section = None
                    for sel in [
                        "*:has-text('詳細表示')",
                        "div:has-text('詳細表示')",
                        "section:has-text('詳細表示')",
                        "*[class*='detail']",
                        "*[id*='detail']"
                    ]:
                        try:
                            el = page.locator(sel).first
                            if await el.count() > 0:
                                detail_section = el
                                logger.debug(f"OCS: 詳細表示セクション発見: {sel}")
                                break
                        except:
                            continue
                    
                    # 詳細表示セクション内のすべてのテキストを取得
                    candidate_lines = []
                    if detail_section:
                        try:
                            section_text = await detail_section.inner_text()
                            for line in section_text.splitlines():
                                s = line.strip()
                                if s:
                                    candidate_lines.append(s)
                        except:
                            pass
                    
                    # セクションが見つからない場合は、ページ全体から「⇒」や「↑」で始まる行を探す
                    if not candidate_lines:
                        # まず「⇒」や「↑」を含む要素を直接探す
                        for arrow_char in ['⇒', '↑']:
                            try:
                                arrow_elements = await page.locator(f'*:has-text("{arrow_char}")').all()
                                for el in arrow_elements:
                                    try:
                                        text = (await el.inner_text()).strip()
                                        for line in text.splitlines():
                                            s = line.strip()
                                            if s and (s.startswith('⇒') or s.startswith('↑')):
                                                if s not in candidate_lines:
                                                    candidate_lines.append(s)
                                    except:
                                        continue
                            except:
                                pass
                            
                            # それでも見つからない場合は、すべての要素から抽出
                            if not candidate_lines:
                                all_elements = await page.locator('*').all()
                                seen_texts = set()
                                for el in all_elements:
                                    try:
                                        text = (await el.inner_text()).strip()
                                        if text and text not in seen_texts:
                                            seen_texts.add(text)
                                            # 「⇒」や「↑」で始まる行、または日付を含む行を取得
                                            for line in text.splitlines():
                                                s = line.strip()
                                                if s and (s.startswith('⇒') or s.startswith('↑') or date_re.search(s)):
                                                    if s not in candidate_lines:
                                                        candidate_lines.append(s)
                                    except:
                                        continue
                    
                    # HTMLからも抽出（フォールバック）
                    if not candidate_lines:
                        normalized = page_html.replace('\r', '\n')
                        text_only = re.sub(r'<[^>]+>', '\n', normalized)
                        for raw in text_only.split('\n'):
                            s = raw.strip()
                            if s and (s.startswith('⇒') or s.startswith('↑') or date_re.search(s)):
                                if s not in candidate_lines:
                                    candidate_lines.append(s)
                    
                    logger.debug(f"OCS: 抽出した候補行数: {len(candidate_lines)}")
                    
                    def append_parsed_line(line: str):
                        # 記号を除去
                        clean_line = line.lstrip('⇒').lstrip('↑').strip()
                        
                        # 日付を抽出
                        m = date_re.search(clean_line)
                        if m:
                            date = m.group(1).strip()
                            tail = clean_line[m.end():].strip()
                            
                            # 営業所名を抽出
                            location = ''
                            loc_match = re.search(r'(.+?営業所)', tail)
                            if loc_match:
                                location = loc_match.group(1)
                            
                            tracking_data.append({
                                'date': date,
                                'location': location,
                                'status': tail
                            })
                            logger.debug(f"OCS: データ追加 - date={date}, location={location}, status={tail[:50]}")
                        else:
                            # 日付がない場合はstatusのみ
                            if clean_line:
                                tracking_data.append({
                                    'date': '',
                                    'location': '',
                                    'status': clean_line
                                })
                    
                    # 候補行を処理
                    for line in candidate_lines:
                        append_parsed_line(line)
                    
                except Exception as e:
                    logger.debug(f"OCS: データ抽出エラー: {e}", exc_info=True)

            if not tracking_data:
                # エラーメッセージや検索結果なしメッセージの検出
                page_text_lower = page_html.lower()
                if any(keyword in page_text_lower for keyword in ['見つかりません', 'not found', '該当する', '検索結果がありません', 'データがありません']):
                    return [], "", "OCS: 該当する追跡情報が見つかりません"
                # 検索が実行されたか確認（検索ボタンをクリックした後、ページが変化していない場合は検索が実行されていない可能性）
                # 入力フィールドの値が空でない場合、検索が実行されているはず
                try:
                    input_value = await input_field.input_value()
                    if input_value and input_value.strip() == awb:
                        # 入力値は残っているが結果が表示されていない = 検索結果なしまたはエラー
                        return [], "", "OCS: 検索結果が表示されませんでした（追跡番号が無効またはデータなしの可能性）"
                except:
                    pass
                # それでも無ければ解析失敗
                return [], "", "OCS: データの解析に失敗しました（検索結果が表示されませんでした）"

            return tracking_data, "", ""
        except Exception as e:
            return [], "", f"OCS: エラー: {e}"

    async def _parse_sagawa_detail_page(self, new_page, tracking_data: List[Dict[str, str]]):
        """佐川急便の詳細表示ページからデータを抽出"""
        try:
            logger.debug(f"OCS: _parse_sagawa_detail_page開始 - URL: {new_page.url}")
            # about:blankから実際のURLに遷移するまで待機（最大10秒）
            max_wait = 10
            waited = 0
            sagawa_detected = False
            while waited < max_wait:
                try:
                    current_url = new_page.url
                    if current_url and current_url != 'about:blank':
                        logger.debug(f"OCS: 新規タブのURL遷移: {current_url}")
                        if 'sagawa' in current_url.lower() or '荷物' in current_url or 'sg-hldgs' in current_url.lower():
                            logger.debug(f"OCS: 新規タブのURL遷移完了（佐川）: {current_url}")
                            sagawa_detected = True
                            break
                        # 佐川でない場合でも、URLが遷移していれば処理を続行
                        if 'ocsworldwide' not in current_url.lower():
                            logger.debug(f"OCS: 新規タブのURL遷移完了（その他）: {current_url}")
                            break
                except:
                    pass
                await asyncio.sleep(0.5)
                waited += 0.5
            
            # ページが完全にロードされるまで待機
            try:
                await new_page.wait_for_load_state('domcontentloaded', timeout=30000)
                await asyncio.sleep(2)  # 追加待機
            except:
                pass
            
            # 佐川のサイトの場合のみ「詳細表示」を探す
            if sagawa_detected or 'sagawa' in new_page.url.lower():
                row = new_page.locator("tr:has(td:has-text('詳細表示'))").first
                if await row.count() > 0:
                    detail_td = row.locator('td').nth(1)
                    # inner_textを使う方が安全（HTMLタグが除去される）
                    detail_text = await detail_td.inner_text()
                    logger.debug(f"OCS: 詳細表示テキスト: {detail_text[:500]}")
                    
                    # 改行で分割（<br>が改行に変換されている）
                    lines = detail_text.split('\n')
                    date_re = re.compile(r'(\d{4}年\d{2}月\d{2}日(?:\s*\d{2}:\d{2})?)')
                    
                    for line in lines:
                        # 記号を除去してクリーンアップ
                        clean_line = line.strip().lstrip('⇒').lstrip('↑').strip()
                        if not clean_line:
                            continue
                        
                        # HTMLタグを除去（念のため）
                        clean_line = re.sub(r'<[^>]+>', '', clean_line)
                        
                        m = date_re.search(clean_line)
                        if m:
                            date = m.group(1).strip()
                            tail = clean_line[m.end():].strip()
                        else:
                            date = ''
                            tail = clean_line
                        
                        # 営業所名抽出（任意）
                        loc = ''
                        loc_m = re.search(r'(..営業所)', tail)
                        if loc_m:
                            loc = loc_m.group(1)
                        
                        # 有効なデータのみ追加
                        if date or tail:
                            tracking_data.append({'date': date, 'location': loc, 'status': tail})
                    
                    logger.debug(f"OCS: 新規タブから{len(tracking_data)}件のデータを取得")
            else:
                # 佐川でない場合は、このページでは処理しない（メインページで処理）
                logger.debug(f"OCS: 新規タブは佐川サイトではないため、メインページで処理を継続")
        except Exception as parse_err:
            logger.debug(f"OCS: 新規タブ解析エラー: {parse_err}", exc_info=True)

    async def _parse_ocs_detail_in_page(self, page) -> List[Dict[str, str]]:
        """OCSサイト内に結果が表示されるケースのテーブルを解析
        期待する表ヘッダ: 配送状況 / 日時 / 場所 / メモ
        日時は曜日+日付(18Aug2025)+時刻(08:20)が別要素で配置されるため、結合する
        """
        results: List[Dict[str, str]] = []
        try:
            # 「検索結果」配下の2つ目の大きな表に「配送状況」見出しの表がある想定
            tables = await page.locator('table').all()
            if not tables:
                return results

            # ヘッダー行に「配送状況」「日時」「場所」「メモ」があるテーブルを探す
            candidate_tables = []
            for t in tables:
                try:
                    headers = await t.locator('tbody#chart_header tr').first.locator('td,th').all()
                    header_texts = [(await h.inner_text()).strip() for h in headers] if headers else []
                    if any('配送状況' in h for h in header_texts) and any('日時' in h for h in header_texts):
                        candidate_tables.append(t)
                except:
                    continue

            if not candidate_tables:
                return results

            target = candidate_tables[-1]  # 詳細側のテーブルを優先
            body_rows = await target.locator("tbody#chart tr").all()

            for r in body_rows:
                try:
                    tds = await r.locator('td').all()
                    if len(tds) < 4:
                        continue
                    # 配送状況
                    status_input = tds[0].locator('input').first
                    status = (await status_input.get_attribute('value')) if await status_input.count() > 0 else (await tds[0].inner_text()).strip()

                    # 日時（曜日/日付/時刻がdiv内に別々にある）
                    # 例: 18Aug2025 と 08:20 を取得して結合
                    date_text = ''
                    try:
                        # tds[1] 内のテキストから日付部分と時刻部分を抽出
                        raw = (await tds[1].inner_text()).replace('\u00a0', ' ').strip()
                        # 簡易抽出: 英語月表記を含む日付と時刻パターン
                        # 18Aug2025 と 08:20 を拾って結合
                        date_part = ''
                        time_part = ''
                        m_date = re.search(r'\b\d{1,2}[A-Za-z]{3}\d{4}\b', raw)
                        if m_date:
                            date_part = m_date.group(0)
                        m_time = re.search(r'\b\d{1,2}:\d{2}\b', raw)
                        if m_time:
                            time_part = m_time.group(0)
                        date_text = f"{date_part} {time_part}".strip()
                    except:
                        date_text = (await tds[1].inner_text()).strip()

                    # 場所
                    loc_input = tds[2].locator('input').first
                    location = (await loc_input.get_attribute('value')) if await loc_input.count() > 0 else (await tds[2].inner_text()).strip()

                    # メモ（不要ならstatusに含めたままでも良いが、そのまま保持）
                    memo_input = tds[3].locator('input').first
                    memo = (await memo_input.get_attribute('value')) if await memo_input.count() > 0 else (await tds[3].inner_text()).strip()

                    # status欄が空でメモに日本語ステータスが入るケースへのフォールバック
                    final_status = status.strip() if status and status.strip() else memo.strip()

                    if date_text or final_status:
                        results.append({
                            'date': date_text,
                            'location': location.strip(),
                            'status': final_status
                        })
                except:
                    continue

            return results
        except Exception as e:
            logger.debug(f"OCS: OCS表解析中エラー: {e}", exc_info=True)
            return results
