# ColumnConfig クラスの使い方

Googleスプレッドシートの「設定」シートから列番号を読み取り、管理するクラスです。

## 基本的な使い方

```python
from column_config import ColumnConfig

# 初期化
config = ColumnConfig(
    credentials_file="service_account.json",
    spreadsheet_id="1Dvz3cS9DRGx4woEY0NNypgLPKxLZ55a4j8778YlCFls"
)

# Googleスプレッドシートから列設定を読み込む
config.load()

# 列番号を取得（1ベース）
fnsku_column = config.get('fnsku')  # 80
asin_column = config.get('asin')    # 4

# 存在しない列名の場合はNoneが返る
unknown = config.get('存在しない列')  # None
```

## メソッド

### `load()`
Googleスプレッドシートから列設定を読み込みます。

### `get(name: str) -> Optional[int]`
列名から列番号を取得します（1ベース）。見つからない場合はNoneを返します。

## main.py での使用例

```python
from column_config import ColumnConfig

# 列設定を初期化して読み込み
column_config = ColumnConfig(
    credentials_file="service_account.json",
    spreadsheet_id="1Dvz3cS9DRGx4woEY0NNypgLPKxLZ55a4j8778YlCFls"
)
column_config.load()

# 列番号を取得してデータにアクセス
fnsku_column = column_config.get('fnsku')
if fnsku_column:
    # 0ベースのインデックスに変換する場合
    fnsku_index = fnsku_column - 1
    fnsku_value = row[fnsku_index]
```

