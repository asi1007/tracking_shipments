1. google sheetで各商品の追跡番号を取得
- シート名: 仕入管理
- セル: AC列5行目から最後まで
- G列が"在庫あり"、"在庫なし"の行は両方対象外
- 重複したデータを削除

2.それぞれの追跡番号に対してブラウザで追跡番号を入力して状況を取得
- ページを開く:  https://japan-kaigen.com/download/
- 貨物追跡に追跡番号を入力 例:  YP5507437XX
- 追跡ボタンをクリック
- テーブルデータを読み込む
  (配送状況、日付、場所)

3. google sheet追跡番号と取得したデータを書き込む
- シート名:  tracking
- https://docs.google.com/spreadsheets/d/1Dvz3cS9DRGx4woEY0NNypgLPKxLZ55a4j8778YlCFls/edit?gid=19567099#gid=19567099


# ライブラリ
- playwright
- gspread