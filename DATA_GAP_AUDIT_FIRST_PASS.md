# DATA_GAP_AUDIT_FIRST_PASS

## 文件目的
本文件是對 `D:\Claude projects\主觀看盤\data` 的第一版實際盤點結果，建立在 `DATA_GAP_AUDIT_TEMPLATE.md` 之上。

盤點日期：
- `2026-05-15`

盤點性質：
- 規劃與稽核
- 非程式實作
- 非完整逐檔深度驗證

## 稽核範圍
共享資料根目錄：
- `D:\Claude projects\主觀看盤\data`

已確認子目錄：
- `fundamentals/`
- `raw/`

## Executive Summary
第一版盤點結果顯示，目前共享資料已具備「基礎可用但尚不完整」的雛形，能支撐部分整合規劃，但還不足以直接滿足所有模型。

目前最重要的結論：
1. `raw/` 價格資料是目前最成熟的資料域。
2. `company_info.csv` 可作為 universe 基礎，但 `listing_date` 缺值不少。
3. `valuation.csv` 缺少日期欄位，因此較像「單日快照」而不是歷史估值序列。
4. `yfinance_fundamentals.csv` 缺少 `report_date` 與 `fiscal_period`，無法區分年度或季度口徑。
5. provenance、fallback、quality flag 類 metadata 目前尚未看到。

## A. 檔案層級總表

| Data Domain | File Path | Exists | Format | Row Count | Date Range | Primary Key Guess | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| universe | `fundamentals/company_info.csv` | yes | csv | 1973 | n/a | `stock_id` | PARTIAL | 有基本公司資訊，但 listing_date 並不完整 |
| valuation | `fundamentals/valuation.csv` | yes | csv | 1960 | no date column | `stock_id` | NEEDS_VALIDATION | 缺日期欄，無法當歷史 valuation series |
| fundamentals | `fundamentals/yfinance_fundamentals.csv` | yes | csv | 222 | no date column | `stock_id` | NEEDS_NORMALIZATION | 缺 report_date / fiscal_period，且覆蓋股票數偏少 |
| price | `raw/*.csv` | yes | csv | 242 files | sample shows `2015-01-05` to `2026-05-13` | `ticker + date` | OK | schema 穩定，至少前 50 檔一致 |
| benchmark | `raw/TAIEX.csv` | yes | csv | 2765 | `2015-01-05` to `2026-05-13` | `benchmark_id + date` | OK | 可作為 benchmark 起點 |

## B. 單檔案盤點結果

### 1. `fundamentals/company_info.csv`

#### File Basic Info
- File path: `D:\Claude projects\主觀看盤\data\fundamentals\company_info.csv`
- Data domain: universe
- Source system: unknown
- Layer guess: normalized-ish fundamentals side table
- Estimated row count: 1973
- Unique stock_id count: 1973
- Grain: one row per stock
- Audit status: `PARTIAL`

#### Header
- `stock_id`
- `name`
- `industry`
- `listing_date`
- `market`

#### Sample
- `{"stock_id":"1101","name":"臺灣水泥股份有限公司","industry":"水泥工業","listing_date":"","market":"TWSE"}`

#### Findings
- `stock_id` 可映射到 canonical `ticker`
- `name` 可映射到 canonical `company_name`
- `industry` 可直接映射
- `market` 可直接映射，已觀察到 `TWSE`、`TPEX`
- `listing_date` 有值但不完整

#### Data Quality Notes
- `listing_date_nonempty = 887`
- 代表 1973 筆中，超過一半沒有 `listing_date`

#### Gaps
- 缺 `listing_status`
- `listing_date` 缺值比例高
- 未見 provenance 欄位

### 2. `fundamentals/valuation.csv`

#### File Basic Info
- File path: `D:\Claude projects\主觀看盤\data\fundamentals\valuation.csv`
- Data domain: valuation
- Source system: unknown
- Layer guess: snapshot valuation table
- Estimated row count: 1960
- Unique stock_id count: 1960
- Grain: one row per stock
- Audit status: `NEEDS_VALIDATION`

#### Header
- `stock_id`
- `pe_ratio`
- `pb_ratio`
- `dividend_yield`

#### Sample
- `{"stock_id":"1101","pe_ratio":"0.0","pb_ratio":"0.83","dividend_yield":"3.21"}`

#### Findings
- 可映射到 `ticker`
- 有 `pe_ratio`、`pb_ratio`、`dividend_yield`
- 沒有 `date`
- 沒有 `market_cap`

#### Data Quality Notes
- `pe_zero_count = 1137`
- `pb_blank_count = 0`

#### Gaps
- 最大缺口是沒有日期欄位
- 無法支持歷史估值時序需求
- `pe_ratio = 0.0` 的筆數很多，需後續判斷是缺值替代、虧損公司、或來源口徑問題
- 未見來源欄位與更新時間欄位

### 3. `fundamentals/yfinance_fundamentals.csv`

#### File Basic Info
- File path: `D:\Claude projects\主觀看盤\data\fundamentals\yfinance_fundamentals.csv`
- Data domain: fundamentals
- Source system: likely yfinance
- Layer guess: snapshot fundamentals table
- Estimated row count: 222
- Unique stock_id count: 222
- Grain: one row per stock
- Audit status: `NEEDS_NORMALIZATION`

#### Header
- `stock_id`
- `market_cap`
- `roe`
- `eps`
- `revenue`
- `net_income`
- `total_equity`
- `operating_cf`
- `free_cf`

#### Sample
- `{"stock_id":"2330","market_cap":"57569036992512","roe":"0.3621","eps":"73.51","revenue":"4103903379456.0","net_income":"1908519993344.0","total_equity":"5355038700000.0","operating_cf":"2274975600000.0","free_cf":"992378400000.0"}`

#### Findings
- 可映射到一部分 annual fundamentals canonical fields
- `total_equity` 可作為 `bvps` 或更進一步衍生計算的上游欄位，但不是 `bvps`
- `free_cf` 可映射到 `free_cash_flow`
- `roe_blank_count = 0`
- `market_cap_blank_count = 0`

#### Gaps
- 沒有 `report_date`
- 沒有 `fiscal_year`
- 沒有 `fiscal_period`
- 沒有 `gross_profit`
- 沒有 `operating_income`
- 沒有 `shares_outstanding`
- 覆蓋股票數只有 222，遠低於 universe 1973

### 4. `raw/<ticker>.csv`

#### File Basic Info
- File path pattern: `D:\Claude projects\主觀看盤\data\raw\*.csv`
- Data domain: price
- Source system: unknown
- Layer guess: raw-ish price history
- File count: 242
- Non-TAIEX stock files: 241
- Audit status: `OK`

#### Observed Shared Schema
- `Date`
- `Open`
- `High`
- `Low`
- `Close`
- `Volume`

#### Sample From `0050.csv`
- Row count: 2760
- Date range: `2015-01-05` to `2026-05-13`
- First row: `{"Date":"2015-01-05","Open":"66.4","High":"66.75","Low":"66.0","Close":"66.55","Volume":"6295612.0"}`

#### Findings
- 前 50 檔抽樣 schema 一致
- 目前未見 `adjusted_close`
- 目前未見 `ticker` 欄位，ticker 來自檔名
- 對大多數價格型模型已是可用起點

#### Gaps
- 未見 `adjusted_close`
- 未見 `turnover_value`
- 檔內沒有 `ticker` 欄，後續 normalization 必須補上

### 5. `raw/TAIEX.csv`

#### File Basic Info
- File path: `D:\Claude projects\主觀看盤\data\raw\TAIEX.csv`
- Data domain: benchmark
- Estimated row count: 2765
- Date range: `2015-01-05` to `2026-05-13`
- Audit status: `OK`

#### Header
- `Date`
- `Open`
- `High`
- `Low`
- `Close`
- `Volume`

#### First Row
- `{"Date":"2015-01-05","Open":"9292.31","High":"9292.31","Low":"9182.02","Close":"9274.11","Volume":"4852267931"}`

#### Findings
- 可直接作為 benchmark 基礎資料
- schema 與個股 price files 一致，利於 normalization

## C. Canonical Field Coverage Summary

| Canonical Field Group | Coverage | Notes |
| --- | --- | --- |
| universe core | medium | `ticker/company_name/industry/market` 已有基礎 |
| price core | high | `Date/Open/High/Low/Close/Volume` 已相當穩定 |
| valuation core | low-medium | 只有 snapshot 級別 `pe/pb/dividend_yield` |
| fundamentals core | low-medium | 有部分 snapshot，但缺 period/date |
| benchmark core | medium-high | `TAIEX.csv` 可直接利用 |
| metadata / provenance | low | 幾乎未見 |

## D. Model Impact Summary

| Model | Current Support Level | Blocking Gaps |
| --- | --- | --- |
| buffett-stock-tw | partial | fundamentals 缺 period，price 缺 adjusted close |
| 第二版 2_0 by claude | partial | valuation history 與 fundamentals period 不足 |
| IMFS_TW_Stock | partial-low | provenance、validation metadata、valuation completeness 不足 |
| tw-buffett-quant-app | partial-low | 月營收資料未見，valuation 缺 date |
| TW hybrid model | partial | price 基礎可用，但 adjusted close / turnover / valuation history 待補 |

## E. Top Gaps
1. `valuation.csv` 沒有日期欄位，無法支援歷史估值序列。
2. `yfinance_fundamentals.csv` 沒有 `report_date / fiscal_year / fiscal_period`，無法區分年度與季度。
3. fundamentals 覆蓋股票數只有 222，與 universe 1973 差距大。
4. raw price 檔缺 `adjusted_close`、`turnover_value`、內嵌 `ticker` 欄位。
5. 尚未看到 monthly revenue、provenance、fallback、quality flag 結構。

## F. Recommended Next Actions
1. 先將這份盤點結果回填到 `DATA_FIELD_MAPPING.md`。
2. 定義第一版 downloader scope 只先覆蓋 `universe + price + benchmark + snapshot valuation/fundamentals`。
3. 把 `valuation.csv` 和 `yfinance_fundamentals.csv` 明確標記為 snapshot tables。
4. 下一輪再針對 monthly revenue 與歷史 valuation 缺口做來源補強規劃。

## G. Current Completion Status
以「第一版共享資料現況盤點」這個模組來說，已完成：
- 共享資料根目錄確認
- 主要檔案 inventory
- 關鍵欄位盤點
- 第一版缺口摘要
- 模型影響初判

尚未完成：
- 全部 raw 檔案逐檔稽核
- monthly revenue 實際來源盤點
- 各來源 provenance 結構設計落地
