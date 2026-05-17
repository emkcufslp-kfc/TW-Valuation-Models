# DATA_FIELD_MAPPING

## 文件目的
本文件用於定義各模型所需資料與平台共享資料欄位之間的對應關係，目的是在不修改模型核心邏輯的前提下，先釐清：

1. 各模型需要哪些資料家族
2. 這些資料目前可能來自哪裡
3. 哪些欄位可映射到 canonical fields
4. 哪些欄位仍存在缺口或高風險

本文件是規劃文件，不代表欄位已全部驗證存在。

## 模型清單
1. `buffett-stock-tw`
2. `第二版 2_0 by claude`
3. `IMFS_TW_Stock`
4. `tw-buffett-quant-app`
5. `TW hybrid model`

## Canonical Data Families
- universe
- price
- fundamentals_annual
- fundamentals_quarterly
- fundamentals_monthly
- valuation_daily
- benchmark
- metadata

## Canonical Field Principles
- 優先定義平台共通欄位，再由 adapter 對應到模型輸入格式
- 欄位缺失時先標示，不在 mapping 階段猜測公式
- 粒度必須明確區分 daily / monthly / quarterly / annual
- 來源名稱與資料日期要能回溯

## Canonical Field Set

### Universe
- `ticker`
- `company_name`
- `market`
- `industry`
- `listing_status`
- `listing_date`

### Price
- `ticker`
- `date`
- `open`
- `high`
- `low`
- `close`
- `adjusted_close`
- `volume`
- `turnover_value`

### Fundamentals Annual / Quarterly
- `ticker`
- `report_date`
- `fiscal_year`
- `fiscal_period`
- `revenue`
- `gross_profit`
- `operating_income`
- `net_income`
- `eps`
- `bvps`
- `roe`
- `gross_margin`
- `operating_margin`
- `free_cash_flow`
- `shares_outstanding`

### Fundamentals Monthly
- `ticker`
- `month`
- `monthly_revenue`
- `monthly_revenue_yoy`
- `monthly_revenue_mom`

### Valuation Daily
- `ticker`
- `date`
- `market_cap`
- `pe_ratio`
- `pb_ratio`
- `dividend_yield`
- `price_to_sales`
- `ev_ebit`
- `ev_ebitda`

### Benchmark
- `benchmark_id`
- `date`
- `open`
- `high`
- `low`
- `close`
- `volume`

### Metadata
- `source_name`
- `data_as_of`
- `normalized_at`
- `fallback_used`
- `quality_flag`

## High-Level Model Data Characteristics

### 1. buffett-stock-tw
已知特徵：
- 主要依賴 yfinance
- 偏向本地 SQLite 流程
- 需要股價歷史、年度基本面、季度基本面

### 2. 第二版 2_0 by claude
已知特徵：
- 與 `buffett-stock-tw` 相近
- 也依賴 yfinance 與本地 SQLite 習慣
- 需要股價快照與基本面歷史

### 3. IMFS_TW_Stock
已知特徵：
- 偏官方資料優先
- 使用 TWSE OpenAPI、twstock、yfinance fallback
- 對資料來源品質與驗證較敏感

### 4. tw-buffett-quant-app
已知特徵：
- 使用 TWSE OpenAPI
- 使用 MOPS monthly revenue
- 使用 FinMind
- 使用 yfinance

### 5. TW hybrid model
已知特徵：
- 使用 yfinance
- 再 fallback 到 FinMind、TWSE
- 對 OHLCV 歷史乾淨度與時間窗一致性敏感

## Model-to-Family Mapping

| Model | Universe | Price | Fundamentals Annual | Fundamentals Quarterly | Fundamentals Monthly | Valuation Daily | Benchmark | Metadata |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| buffett-stock-tw | likely | required | required | required | optional | likely | optional | required |
| 第二版 2_0 by claude | likely | required | required | required | optional | likely | optional | required |
| IMFS_TW_Stock | required | required | required | likely | optional | required | likely | required |
| tw-buffett-quant-app | required | required | required | likely | required | required | optional | required |
| TW hybrid model | likely | required | likely | optional | optional | likely | likely | required |

註：
- `required` 代表高機率為核心依賴
- `likely` 代表從已知描述推測為重要但仍需原始碼確認
- `optional` 代表可能為輔助或非必要資料

## Model-to-Canonical Field Mapping

### buffett-stock-tw

| Data Family | Canonical Fields Needed | Existing Shared Dataset Likelihood | Notes |
| --- | --- | --- | --- |
| price | `ticker,date,open,high,low,close,adjusted_close,volume` | medium | raw 個股歷史檔案可能可支援 |
| fundamentals_annual | `revenue,net_income,eps,bvps,roe` | medium | 需確認年資料是否可辨識 |
| fundamentals_quarterly | `revenue,net_income,eps,gross_margin,operating_margin` | low-medium | 目前共享資料可能不完整 |
| metadata | `source_name,data_as_of` | low | 舊資料常缺 provenance |

### 第二版 2_0 by claude

| Data Family | Canonical Fields Needed | Existing Shared Dataset Likelihood | Notes |
| --- | --- | --- | --- |
| price | `ticker,date,close,volume` | medium | 與 buffett-stock-tw 類似 |
| fundamentals_annual | `revenue,net_income,eps,bvps,roe` | medium | 需確認共享資料欄位名與粒度 |
| fundamentals_quarterly | `revenue,eps,gross_profit,operating_income` | low-medium | 需核對是否有季度層 |
| valuation_daily | `pe_ratio,pb_ratio` | low-medium | 歷史估值時序是已知風險 |

### IMFS_TW_Stock

| Data Family | Canonical Fields Needed | Existing Shared Dataset Likelihood | Notes |
| --- | --- | --- | --- |
| universe | `ticker,company_name,market,industry` | medium | company_info.csv 可能有一部分 |
| price | `ticker,date,open,high,low,close,volume` | medium | 需確認完整度與命名一致性 |
| valuation_daily | `pe_ratio,pb_ratio,dividend_yield` | medium | valuation.csv 可能有一部分 |
| metadata | `source_name,fallback_used,quality_flag` | low | 這部分大多需要新增結構 |

### tw-buffett-quant-app

| Data Family | Canonical Fields Needed | Existing Shared Dataset Likelihood | Notes |
| --- | --- | --- | --- |
| universe | `ticker,company_name,market` | medium | 需確認交易所 / 櫃買標記 |
| price | `ticker,date,close,volume` | medium | 日線資料應較容易取得 |
| fundamentals_monthly | `month,monthly_revenue,monthly_revenue_yoy` | low-medium | 月營收是關鍵檢查點 |
| fundamentals_annual | `eps,bvps,roe` | medium | 需確認時間對齊 |
| valuation_daily | `pe_ratio,pb_ratio,dividend_yield` | medium | 需確認是否為每日或快照 |

### TW hybrid model

| Data Family | Canonical Fields Needed | Existing Shared Dataset Likelihood | Notes |
| --- | --- | --- | --- |
| price | `ticker,date,open,high,low,close,adjusted_close,volume` | medium | 歷史深度與缺漏最重要 |
| fundamentals_annual | `eps,bvps,roe` | medium | 可能可由 fundamentals 檔提供 |
| valuation_daily | `pe_ratio,pb_ratio` | low-medium | 需確認歷史序列是否存在 |
| benchmark | `benchmark_id,date,close` | medium | raw 內已知有 TAIEX.csv |

## Candidate Existing Shared Files
根據目前工作筆記，已觀察到：
- `fundamentals/company_info.csv`
- `fundamentals/valuation.csv`
- `fundamentals/yfinance_fundamentals.csv`
- `raw/*.csv`
- `raw/TAIEX.csv`

## Candidate File-to-Family Mapping

| Existing File | Likely Data Family | Likely Useful Fields | Confidence | Notes |
| --- | --- | --- | --- | --- |
| `company_info.csv` | universe | ticker, company_name, market, industry | medium | 需實際盤欄位 |
| `valuation.csv` | valuation_daily | pe_ratio, pb_ratio, dividend_yield, market_cap | medium | 需確認是否只有單日快照 |
| `yfinance_fundamentals.csv` | fundamentals_annual / quarterly | eps, bvps, roe, revenue, margins | medium | 需確認 period 欄位 |
| `raw/<ticker>.csv` | price | OHLCV | medium-high | 需確認 adjusted close 與日期格式 |
| `TAIEX.csv` | benchmark | date, OHLCV / close | medium | 需確認欄位完整度 |

## First-Pass Actual Audit Findings
根據 `2026-05-15` 的實際盤點，目前可確認：

### `company_info.csv`
- header: `stock_id,name,industry,listing_date,market`
- row count: `1973`
- 可直接映射：
  - `stock_id -> ticker`
  - `name -> company_name`
  - `industry -> industry`
  - `market -> market`
- 已知缺口：
  - 缺 `listing_status`
  - `listing_date` 缺值明顯

### `valuation.csv`
- header: `stock_id,pe_ratio,pb_ratio,dividend_yield`
- row count: `1960`
- 實際上是 snapshot table，不是 historical valuation table
- 已知缺口：
  - 缺 `date`
  - 缺 `market_cap`
  - `pe_ratio = 0.0` 筆數很多，需後續驗證

### `yfinance_fundamentals.csv`
- header: `stock_id,market_cap,roe,eps,revenue,net_income,total_equity,operating_cf,free_cf`
- row count: `222`
- 可映射：
  - `market_cap -> market_cap`
  - `roe -> roe`
  - `eps -> eps`
  - `revenue -> revenue`
  - `net_income -> net_income`
  - `free_cf -> free_cash_flow`
- 已知缺口：
  - 缺 `report_date`
  - 缺 `fiscal_year`
  - 缺 `fiscal_period`
  - 缺 `gross_profit`
  - 缺 `operating_income`
  - 缺 `shares_outstanding`

### `raw/<ticker>.csv`
- observed shared header: `Date,Open,High,Low,Close,Volume`
- raw csv file count: `242`
- 非 TAIEX 檔數: `241`
- sample date range from `0050.csv`: `2015-01-05` to `2026-05-13`
- 已知缺口：
  - 缺 `adjusted_close`
  - 缺 `turnover_value`
  - 檔內沒有 `ticker` 欄位，需由檔名補入

### `TAIEX.csv`
- header: `Date,Open,High,Low,Close,Volume`
- row count: `2765`
- date range: `2015-01-05` to `2026-05-13`

## Known Gap Areas
1. `valuation.csv` 無日期欄，歷史 PE/PB 序列目前不可用。
2. `yfinance_fundamentals.csv` 無 period/date 欄，年度與季度無法分層。
3. provenance / fallback / quality flag 目前未見。
4. 月營收資料是否已存在仍未知。
5. SQLite 習慣模型需要的輸入結構可能不只是一張表。
6. fundamentals 覆蓋股票數明顯低於 universe。

## Mapping Risk Register

| Risk | Impacted Models | Why It Matters | Suggested Handling |
| --- | --- | --- | --- |
| historical valuation series missing | 第 1、2、3、5 模型 | 無法做估值區間或歷史比較 | 先稽核 valuation 時序完整度 |
| quarterly vs annual ambiguity | 第 1、2、4 模型 | 會直接錯配基本面輸入 | 強制保留 fiscal_period |
| ticker naming inconsistency | 全部模型 | join 失敗與覆蓋錯誤 | 建立 canonical ticker rule |
| source provenance missing | 第 3、4、5 模型 | 難以解釋 fallback 與可信度 | manifest 與 metadata 欄位補上 |
| insufficient OHLCV history | 第 5 模型 | hybrid time window 失真 | 先確認最長歷史範圍 |

## Suggested Adapter Strategy by Model

### buffett-stock-tw / 第二版 2_0 by claude
- 優先做 price + fundamentals adapter
- 預期需要模擬原本 SQLite 可讀的資料結構
- 先不假設可直接讀 normalized 主表
- 目前最大阻塞是 fundamentals 缺 `report_date / fiscal_period`

### IMFS_TW_Stock
- 優先做 provenance 與 validation 友善的輸入結構
- source quality metadata 要比其他模型更完整

### tw-buffett-quant-app
- 優先確認月營收與估值欄位
- 可把它當成 downloader 欄位需求的重要參考模型
- 目前已知估值表只有 snapshot，月營收尚未出現在共享資料根

### TW hybrid model
- 優先確認長期 OHLCV 與 benchmark
- 第二優先才是 valuation 補齊
- price 基礎比 fundamentals/valuation 更成熟，較適合先納入第一版

## 與資料稽核模板的關係
本文件回答的是「理論上需要什麼」。

`DATA_GAP_AUDIT_TEMPLATE.md` 回答的是「實際上現在有什麼」。

兩者應一起使用：
1. 先用本文件建立模型需求視角。
2. 再用 audit template 盤點現況。
3. 最後把實際缺口回填到本文件。

## 後續回填欄位建議
之後在進行真實資料盤點時，可新增以下欄位：
- actual_file_path
- actual_source_column
- actual_grain
- completeness_status
- validated_on
- audit_notes

## 規劃階段下一步
1. 先盤點 `company_info.csv`、`valuation.csv`、`yfinance_fundamentals.csv` 的實際欄位。
2. 把盤點結果回填到本文件的 candidate mapping。
3. 再決定哪些模型可以先進第一版整合。
