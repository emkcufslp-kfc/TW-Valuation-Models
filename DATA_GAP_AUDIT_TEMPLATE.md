# DATA_GAP_AUDIT_TEMPLATE

## 文件目的
本模板用於逐表、逐欄位盤點目前共享資料目錄的可用性與缺口，目標是回答三件事：

1. 現有資料到底有哪些欄位
2. 哪些欄位可直接支援各模型
3. 哪些欄位仍缺少、口徑不一致、或需要額外清理

本模板僅做稽核規劃，不做下載或實作。

## 稽核範圍
建議先盤點下列資料根目錄：
- `D:\Claude projects\主觀看盤\data`

若實際路徑存在編碼異常或名稱不同，請先以本機真實路徑為準。

## 稽核原則
- 先看「實際檔案與欄位」，不要先假設資料已完整。
- 同一資料域要區分 raw、normalized、model input。
- 每個缺口都盡量標明是「完全缺失」還是「可由替代欄位轉換」。
- 每個欄位都要標記來源、日期粒度、主鍵、與是否可 point-in-time 使用。

## 稽核輸出建議
每張表或每個檔案至少回答：
- 檔案存在嗎
- 欄位有哪些
- 主鍵是什麼
- 日期欄位是什麼
- 資料覆蓋期間到哪天
- 缺哪些欄位
- 哪些模型會受影響

## 稽核狀態標籤建議
- `OK`
- `PARTIAL`
- `MISSING`
- `NEEDS_NORMALIZATION`
- `NEEDS_VALIDATION`
- `UNKNOWN`

## A. 檔案層級總表

| Data Domain | File Path | Exists | Format | Row Count | Date Range | Primary Key Guess | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| price |  |  |  |  |  |  |  |  |
| fundamentals |  |  |  |  |  |  |  |  |
| valuation |  |  |  |  |  |  |  |  |
| benchmark |  |  |  |  |  |  |  |  |
| universe |  |  |  |  |  |  |  |  |

### 欄位說明
- `Exists`: 檔案是否存在
- `Format`: csv / parquet / sqlite / json / other
- `Primary Key Guess`: 例如 `ticker + date`
- `Status`: 使用上方狀態標籤

## B. 單一檔案欄位稽核模板

### File Basic Info
- File path:
- Data domain:
- Source system:
- Raw / normalized / model_input:
- Estimated row count:
- Earliest date:
- Latest date:
- Unique key:
- Grain:
- Audit status:

### Column Inventory

| Column Name | Data Type Guess | Sample Meaning | Nullable | Example Value | Canonical Field Mapping | Needed By Models | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |

### Data Quality Checks
- 是否有重複鍵值：
- 是否有日期格式不一致：
- 是否有 ticker 命名不一致：
- 是否有數值欄位混入字串：
- 是否有單位不一致：
- 是否有空值比例過高欄位：
- 是否可確認資料來源：

### Gaps / Issues
- 缺失欄位：
- 欄位名稱不一致：
- 粒度不一致：
- 時間覆蓋不足：
- 無法 point-in-time 使用：
- 來源可信度待確認：

### Model Impact
- 影響模型：
- 影響程度：
- 可否用替代欄位暫補：
- 是否必須回源重抓：

## C. Canonical Field Checklist
以下欄位可作為盤點時的共用檢查清單。

### Universe

| Canonical Field | Exists | Source Column | File | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| ticker |  |  |  |  |  |
| company_name |  |  |  |  |  |
| market |  |  |  |  |  |
| industry |  |  |  |  |  |
| listing_status |  |  |  |  |  |
| listing_date |  |  |  |  |  |

### Price / OHLCV

| Canonical Field | Exists | Source Column | File | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| ticker |  |  |  |  |  |
| date |  |  |  |  |  |
| open |  |  |  |  |  |
| high |  |  |  |  |  |
| low |  |  |  |  |  |
| close |  |  |  |  |  |
| adjusted_close |  |  |  |  |  |
| volume |  |  |  |  |  |
| turnover_value |  |  |  |  |  |

### Fundamentals

| Canonical Field | Exists | Source Column | File | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| ticker |  |  |  |  |  |
| report_date |  |  |  |  |  |
| fiscal_year |  |  |  |  |  |
| fiscal_period |  |  |  |  |  |
| revenue |  |  |  |  |  |
| gross_profit |  |  |  |  |  |
| operating_income |  |  |  |  |  |
| net_income |  |  |  |  |  |
| eps |  |  |  |  |  |
| bvps |  |  |  |  |  |
| roe |  |  |  |  |  |
| operating_margin |  |  |  |  |  |
| gross_margin |  |  |  |  |  |
| free_cash_flow |  |  |  |  |  |
| shares_outstanding |  |  |  |  |  |

### Valuation

| Canonical Field | Exists | Source Column | File | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| ticker |  |  |  |  |  |
| date |  |  |  |  |  |
| market_cap |  |  |  |  |  |
| pe_ratio |  |  |  |  |  |
| pb_ratio |  |  |  |  |  |
| dividend_yield |  |  |  |  |  |
| price_to_sales |  |  |  |  |  |
| ev_ebit |  |  |  |  |  |
| ev_ebitda |  |  |  |  |  |

### Benchmark

| Canonical Field | Exists | Source Column | File | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| benchmark_id |  |  |  |  |  |
| date |  |  |  |  |  |
| open |  |  |  |  |  |
| high |  |  |  |  |  |
| low |  |  |  |  |  |
| close |  |  |  |  |  |
| volume |  |  |  |  |  |

## D. Model-Specific Requirement Audit
這一段用來從「模型需求」反查「資料是否足夠」。

| Model | Required Data Family | Required Field | Existing Source | Gap Type | Severity | Action Needed | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| buffett-stock-tw | fundamentals |  |  |  |  |  |  |
| buffett-stock-tw | price |  |  |  |  |  |  |
| 第二版 2_0 by claude | fundamentals |  |  |  |  |  |  |
| IMFS_TW_Stock | valuation |  |  |  |  |  |  |
| tw-buffett-quant-app | revenue |  |  |  |  |  |  |
| TW hybrid model | OHLCV |  |  |  |  |  |  |

### Gap Type 建議值
- `missing_file`
- `missing_column`
- `wrong_grain`
- `wrong_frequency`
- `wrong_naming`
- `insufficient_history`
- `quality_risk`
- `provenance_missing`

### Severity 建議值
- `high`
- `medium`
- `low`

## E. 常見高風險缺口清單
以下項目應優先確認，因為在目前工作筆記中已知風險較高：

| Risk Item | Why It Matters | Checked | Result | Notes |
| --- | --- | --- | --- | --- |
| 歷史 PE/PB 時序是否完整 | 多模型估值比較可能依賴歷史估值區間 |  |  |  |
| 季度 / 年度基本面是否分開且可辨識 | 不同模型可能要求不同 period 粒度 |  |  |  |
| EPS / BVPS / ROE 欄位是否同口徑 | 若口徑混亂會直接影響估值結果 |  |  |  |
| OHLCV 是否覆蓋足夠歷史區間 | hybrid 類模型對時間窗很敏感 |  |  |  |
| ticker 命名是否一致 | 整合時最常造成 join 失敗 |  |  |  |
| 是否保留資料來源欄位 | 追查 fallback 與可信度時必要 |  |  |  |

## F. 稽核結論模板

### Overall Summary
- 已盤點檔案數：
- 已盤點資料域：
- 可直接使用資料：
- 需正規化資料：
- 明確缺失資料：
- 待人工確認項目：

### Top Gaps
1. 
2. 
3. 

### Recommended Next Actions
1. 優先補齊：
2. 優先正規化：
3. 優先驗證：

## G. 建議實際執行順序
1. 先做檔案清單總表。
2. 再做每個主要 csv 的欄位盤點。
3. 先盤 `company_info.csv`、`valuation.csv`、`yfinance_fundamentals.csv`。
4. 再抽樣盤點 `raw` 內個股歷史價量檔案與 `TAIEX.csv`。
5. 最後用 model-specific audit 反推哪些缺口最影響整合。
