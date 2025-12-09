### 1. 仮想環境作成とCrawl4AI等のインスト−ル
```shell
python -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Playwright browsers (Chromium)のインストール
pipでライブラリイインストー後、以下のcrawl4ai-setupコマンドを実行してください。
Crawl4AIが利用するplaywrightもインストールされます。
別途playwrightをインストールする場合は、 `playwright install`でインストールします。

```shell
crawl4ai-setup
```

### 3. クロールするURLリストを記述したファイルを作成します。
URLリストのファイルの拡張子は何でもよいですが、`.cfg`としたほうが、VS CODEのコメントアウトのショートアウトが使えるので便利です。

```conf
# Example

# 引越しに伴う電気・ガスのお手続き
https://www.tepco.co.jp/ep/private/moving/index-j.html
# 引越しするなら電気とガスはまとめておトク！引越し（転居）の手続きはこちら
https://www.tepco.co.jp/ep/private/moving/moving02.html
# sitemap
https://www.tepco.co.jp/ep/sitemap/
# インターネット申込可能な口座振替金融機関一覧
https://www.tepco.co.jp/ep/private/payment/payment03/webbanks.html
# 電気の料金プラン一覧
https://www.tepco.co.jp/ep/private/plan/
# プレミアム 中部エリア
https://www.tepco.co.jp/ep/private/plan/premium/chubu/index-j.html
# 夜トクプラン
https://www.tepco.co.jp/ep/private/plan/yorutoku/index-j.html
# 主な選択約款 電気の料金プラン一覧 - 料金表一覧
https://www.tepco.co.jp/ep/private/plan2/chargelist03.html
# とくとくガスプラン（静岡エリア）
https://www.tepco.co.jp/ep/gas-jiyuuka/plan/chubu/shizuoka/index-j.html
# 再エネ企業応援プラン【 東京地下鉄株式会社 】
https://www.tepco.co.jp/ep/renewable_energy/plan/list/04.html
```
### 4. 以下の環境変数を.envファイルに記載、または実行シェル環境に環境変数としてexportします。
マークダウンの出力結果に含めたくないCSSのidやclassをカンマ形式で指定します。
`id`の場合は`#`, `class`の場合は`.`をプレフィクスとして付けてください。
```conf
# Example
excluded_selector="#header, #footer, #side, #nav, .head_wrapper, .widget"
```

### 5. 第1引数にURLリストファイル、第2引数に出力先ディレクトリを指定して、simple_web_crawlを実行します。
出力先ディレクトリ配下のmdディレクトには、URLを変換した次のファイルが出力されます。
- マークダウンファイル(.md)
- メタファイル(.meta)
- HTML内のテーブルのマークダウンファイル(_unspanned_tables.md)

マークダウンファイル(.md), メタファイル(.meta)は、データベースへのロード処理にて使用します。

Crawl4AIではcolspan, rowspanを含むテーブル(ページ内に複数ある場合を含む)をキレイにマークダウンに生成できません。

このため、別途、HTML内のテーブル部分のみをpandasで整形してマークダウンに変換したHTML内のテーブルのマークダウンファイル(_unspanned_tables.md)を出力しています。

手動になりますが、きれいなマークダウンをコンテンツに含めたい場合は、出力されたマークダウンの当該部分を統合したり(リンクが含まれているケース)、置換する作業が発生します。



その他に出力先ディレクトリ直下には、参考として次のファイルが出力されます。環境変数にて出力を抑制できます。(EXCUDE_CLEANED_HTML=false, EXCUDE_JSON=false)
- clean htmlファイル(.html)
- jsonファイル(.json)

```shell
# Example
python -m simple_web_crawl tepco-ep_urls.cfg tepco-ep_unstructured_result
```
### 6. 整形したマークダウンとメタをカテゴリ毎に出力します。
md_categorizedに出力されます。
```shell
python -m tepco-ep_categorize_md
```