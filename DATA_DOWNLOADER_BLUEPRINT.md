# DATA_DOWNLOADER_BLUEPRINT

## 文件目的
本文件定義整合平台共用資料下載器的規劃藍圖，目標是在不改動各模型核心估值邏輯的前提下，提供可重複、可追溯、可驗證的共享資料供應機制。

本文件只處理：
- 資料下載器的角色與責任
- 資料分層
- 資料來源優先順序
- fallback 規則
- 驗證與更新模式

本文件不處理：
- 實際程式實作
- 特定 API client 細節
- 模型公式
- UI 呈現

## 核心目標
- 提供整個平台唯一的共享資料入口
- 支援所有已選模型的資料需求
- 保留資料來源 provenance
- 保留 raw data 與 normalized data 的分層
- 支援主來源失敗時的備援策略
- 讓各模型可以透過 adapter 使用同一份資料基礎

## 設計原則
- Shared data，不 shared formula
- Raw data 不覆寫，normalized data 可重建
- 所有關鍵資料都要有來源標記與更新時間
- fallback 可以發生，但不可隱藏
- 缺資料時應回報不足，不得虛構值補齊
- 官方來源優先，但允許在必要時用替代來源維持可用性

## 適用資料範圍
- universe
- price
- fundamentals
- valuation
- benchmark

## 建議資料目錄結構
共用資料根目錄建議維持單一入口，例如：
- `data/raw/`
- `data/normalized/`
- `data/model_inputs/`
- `data/manifests/`
- `data/logs/`
- `data/cache/`
- `data/backup/`

## 各資料層責任

### `raw/`
用途：
- 保存最接近來源原貌的資料
- 供稽核、追溯、重建 normalized data 使用

特性：
- 不應被模型直接依賴為長期契約
- 可保留來源原始欄位命名
- 應記錄抓取日期、來源、批次資訊

### `normalized/`
用途：
- 將不同來源整併為平台通用欄位
- 提供欄位名稱、資料型別、日期格式的一致性

特性：
- 是共享資料層的主工作資料
- 應保留 canonical fields
- 應保留來源欄位對應與品質標記

### `model_inputs/`
用途：
- 針對各模型輸出接近原模型需求的輸入資料

特性：
- 允許各模型格式不同
- 不得在此層偷偷更改模型邏輯
- 僅做欄位轉接、格式重整、必要命名對應

### `manifests/`
用途：
- 保存批次更新結果
- 保存每次下載的來源、時間、覆蓋期間、檔案摘要

建議內容：
- run_id
- data_domain
- source_name
- fetch_started_at
- fetch_finished_at
- target_path
- row_count
- date_range
- status
- fallback_used
- warnings

### `logs/`
用途：
- 保存錯誤、警告、驗證摘要、執行紀錄

### `cache/`
用途：
- 暫存下載結果
- 降低重複抓取成本

### `backup/`
用途：
- 保存重要快照
- 在上游異常時作為保底資料

## Canonical Data Domains

### 1. Universe
建議 canonical fields：
- `ticker`
- `company_name`
- `market`
- `industry`
- `listing_status`
- `listing_date`

### 2. Price
建議 canonical fields：
- `ticker`
- `date`
- `open`
- `high`
- `low`
- `close`
- `adjusted_close`
- `volume`
- `turnover_value`

### 3. Fundamentals
建議 canonical fields：
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

### 4. Valuation
建議 canonical fields：
- `ticker`
- `date`
- `market_cap`
- `pe_ratio`
- `pb_ratio`
- `dividend_yield`
- `price_to_sales`
- `ev_ebit`
- `ev_ebitda`

### 5. Benchmark
建議 canonical fields：
- `benchmark_id`
- `date`
- `open`
- `high`
- `low`
- `close`
- `volume`

## 來源優先順序

### Universe
1. TWSE OpenAPI
2. TPEx public source
3. local backup snapshot

### Current valuation
1. TWSE BWIBBU_ALL
2. FinMind
3. yfinance

### Price history
1. TWSE / TPEx official source
2. FinMind
3. yfinance

### Fundamentals
1. TWSE / MOPS
2. FinMind
3. yfinance

### Benchmark
1. TWSE official source
2. yfinance

## Fallback 規則

### Price
`official -> FinMind -> yfinance`

### Valuation
`official -> FinMind -> yfinance`

### Fundamentals
`TWSE/MOPS -> FinMind -> yfinance`

### Universe
`TWSE/TPEx -> backup snapshot`

### Benchmark
`official -> yfinance`

## Fallback 使用原則
- 主來源失敗才切換
- fallback 發生時必須記錄在 manifest
- UI 與資料稽核層應能看見 fallback 狀態
- 不同來源口徑不一致時，應標示 `needs_validation`

## 正規化規則方向

### 欄位命名一致化
- 統一 ticker 欄位名稱
- 統一日期欄位格式
- 統一 OHLCV 命名
- 統一 PE/PB 等估值欄位名稱

### 日期與粒度標準化
- 日資料與季資料不可混用
- 年資料、季資料、月資料要有明確 period 標示
- 重要欄位需保留 `data_as_of` 或 `report_date`

### 型別標準化
- 數值欄位轉成可計算型別
- 缺值維持 null，不以字串假值替代
- 百分比與比率需明確規範單位

### Provenance 保留
每筆或每批資料應至少可追到：
- source_name
- fetch_date
- normalized_at
- fallback_used

## 驗證規則方向

### 檔案層驗證
- 檔案是否存在
- 是否可讀
- 是否為預期格式
- 是否含必要欄位

### 主鍵層驗證
- `ticker + date` 是否唯一
- `ticker + report_date + fiscal_period` 是否唯一

### 資料品質驗證
- 日期格式是否一致
- ticker 命名是否一致
- 重大欄位是否大量缺值
- 數值欄位是否混入非數值
- 是否出現明顯異常值

### 可用性驗證
- 是否足以支援指定模型
- 是否覆蓋足夠歷史期間
- 是否能 point-in-time 使用

## 更新模式

### Full Refresh
適用情境：
- 首次建立資料層
- schema 大幅調整後重建
- 發現原始資料長期污染

### Incremental Refresh
適用情境：
- 每日價格更新
- 新季度 / 新月份資料追加
- 日常維護更新

### Backfill Refresh
適用情境：
- 補齊歷史缺漏期間
- 修正特定欄位長期缺值

### Validation-Only Run
適用情境：
- 不重抓資料，只檢查目前共享資料完整度與可用性

## 建議批次流程
1. 決定目標資料域與更新模式。
2. 讀取來源設定與上次 manifest。
3. 抓取 raw data。
4. 寫入 raw snapshot。
5. 執行 normalization。
6. 執行 schema / quality validation。
7. 產生 normalized outputs。
8. 必要時產生 model_inputs。
9. 寫入 manifest 與 logs。

## 建議輸出成果
每次 downloader run 至少產出：
- raw data snapshot
- normalized data file
- manifest record
- validation summary
- warning / error logs

## 與模型層的界線
Downloader 應該：
- 提供資料
- 標記來源
- 報告缺值

Downloader 不應該：
- 產出估值結論
- 決定模型買賣訊號
- 代替模型修補估值邏輯

## 與 UI 層的界線
Downloader 對 UI 提供的不是畫面，而是狀態資訊，例如：
- 最新更新時間
- 來源名稱
- fallback 狀態
- completeness / validation 狀態

## 已知高風險項目
1. 歷史 PE/PB 可能不足，會影響區間判讀與部分估值邏輯。
2. 季度與年度基本面若未分清，會直接污染模型輸入。
3. 舊模型偏向 SQLite 流程，轉接成共享檔案時要小心主鍵與歷史資料保留。
4. official / FinMind / yfinance 同名欄位可能不同口徑。
5. TW hybrid model 對歷史價量與時間窗一致性特別敏感。

## First-Pass Audit Implications
根據 `2026-05-15` 的第一版實際盤點，目前可直接納入規劃假設的結論是：

- `company_info.csv` 可視為 universe snapshot table
- `valuation.csv` 應暫時視為 valuation snapshot table，而非 historical valuation series
- `yfinance_fundamentals.csv` 應暫時視為 fundamentals snapshot table，而非 annual / quarterly time series
- `raw/*.csv` 是目前最適合作為第一版共享資料層基底的資料域
- `TAIEX.csv` 可直接作為 benchmark 第一版輸入

## Recommended First-Pass Downloader Scope
若後續進入實作，第一版 downloader 建議優先覆蓋：

1. universe snapshot
2. price daily history
3. benchmark daily history
4. valuation snapshot
5. fundamentals snapshot

暫不建議在第一版就承諾完整覆蓋：
- historical valuation series
- quarterly fundamentals history
- monthly revenue history
- provenance-rich multi-source reconciliation

## First-Pass Normalization Priorities
1. 將 `stock_id` 正規化為 canonical `ticker`
2. 將 `raw/<ticker>.csv` 由檔名補入 `ticker`
3. 將 `Date` 正規化為 `date`
4. 為 snapshot tables 額外補入 `data_as_of`
5. 明確標示 table grain 是 `snapshot` 或 `time_series`

## 進入實作前的前置文件
1. `DATA_FIELD_MAPPING.md`
2. `DATA_GAP_AUDIT_TEMPLATE.md`
3. `APP_ARCHITECTURE_PLAN.md`

## 規劃階段的下一步
1. 依 `DATA_GAP_AUDIT_TEMPLATE.md` 實際盤點現有共享資料。
2. 將缺口回填到 `DATA_FIELD_MAPPING.md`。
3. 再決定 downloader 第一版只先覆蓋哪些資料域。
