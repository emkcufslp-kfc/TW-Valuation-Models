# IMPLEMENTATION_ROADMAP

## 2026-05-15 Buffett 3.0 Loader Update Plan

### Immediate Objective
Upgrade the shared downloader so Buffett 3.0 can source its required inputs from official TWSE OpenAPI datasets, with company IR used only as a manual cross-check or temporary audit fallback.

### Why This Is Now The Critical Path
- The current loader in [tw_valuation_models/dataset.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/dataset.py) still depends on:
  - legacy monthly-revenue HTML scraping
  - local shared snapshot reuse
  - `yfinance` profile-style fundamentals
- That is enough for broad model demos, but not enough for Buffett 3.0 V1 because Buffett 3.0 needs auditable:
  - dividend-per-share history
  - monthly revenue trend
  - company-type-aware statements
  - official current valuation ratios

### Loader Scope For This Upgrade
1. Replace the monthly-revenue fetch path with TWSE OpenAPI `t187ap05_L`.
2. Add official current valuation snapshot ingestion from `BWIBBU_ALL`.
3. Add dividend-history ingestion from `t187ap45_L`.
4. Add statement loaders for:
   - non-financial companies via `t187ap06_L_ci` and `t187ap07_L_ci`
   - financial companies via `t187ap06_L_basi` and `t187ap07_L_basi`
5. Persist Buffett 3.0-ready outputs under `artifacts/datasets/top100/` or `artifacts/normalized/` with source metadata.
6. Extend summaries and validation so missing official fields are visible instead of silently skipped.

### Target Data Domains For Buffett 3.0
- `valuation_snapshot_current`
- `dividend_history`
- `monthly_revenue_history`
- `annual_fundamentals_official`
- `quarterly_fundamentals_official`
- `source_manifest`

### Ticker Validation Set
Use these four names as the mandatory regression set after each loader step:
1. `2330` for compounder logic
2. `2881` for financial-statement routing
3. `2603` for cyclical normalization
4. `2412` for defensive/dividend logic

### Recommended Build Sequence
1. Implement source clients and endpoint constants.
2. Replace monthly revenue with official OpenAPI ingestion.
3. Add valuation snapshot and dividend history.
4. Add official statements and financial/non-financial routing.
5. Normalize outputs into stable Buffett 3.0 tables.
6. Add validation and manifest coverage.
7. Re-run Buffett 3.0 paper checks for the four validation tickers.

### Definition Of Done For The Loader Upgrade
- Buffett 3.0 can build its core inputs without relying on `yfinance` snapshots for the four validation names.
- Monthly revenue is no longer empty when official data exists.
- Dividend-per-share history is stored in a reusable normalized table.
- Financial holdings and general companies use different statement endpoints correctly.
- Missing official fields surface as warnings in summaries and manifests.
- The next coding session can start on the Buffett 3.0 engine instead of more data-discovery work.

## 文件目的
本文件將前述規劃文件收斂成分階段執行 roadmap，讓後續從規劃進入實作時，有明確順序、完成條件與風險控管。

## 目前前提
截至 `2026-05-15`，已完成的規劃模組包括：
- architecture plan
- downloader blueprint
- field mapping
- UI content plan
- audit template
- first-pass actual data audit
- model adapter plan

## 總體策略
採取由下而上的整合順序：

1. 先穩 shared data layer
2. 再接第一個可行模型
3. 再擴充更多模型
4. 最後收斂成統一 UI 與比較體驗

## Phase 0: Planning Freeze Check

### Goal
確認規劃文件已足以支撐實作，不再有關鍵未知項目被忽略。

### Required Inputs
- `working.md`
- `APP_ARCHITECTURE_PLAN.md`
- `DATA_DOWNLOADER_BLUEPRINT.md`
- `DATA_FIELD_MAPPING.md`
- `DATA_GAP_AUDIT_FIRST_PASS.md`
- `MODEL_ADAPTER_PLAN.md`

### Exit Criteria
- 實際 shared data root 已確認
- 第一版 scope 已明確
- 第一個整合模型優先順序已決定

## Phase 1: Shared Data Layer Skeleton

### Goal
建立最小可運作的共享資料骨架，不碰模型公式。

### Scope
- path config
- canonical schema constants
- raw -> normalized 的最小轉換
- universe / price / benchmark / snapshot tables 的讀寫規則

### Recommended First-Pass Coverage
- `company_info.csv`
- `valuation.csv`
- `yfinance_fundamentals.csv`
- `raw/*.csv`
- `raw/TAIEX.csv`

### Exit Criteria
- 能穩定讀取共享資料根目錄
- 能輸出 normalized universe table
- 能輸出 normalized price table
- 能輸出 normalized benchmark table
- 能標示 valuation/fundamentals 是 snapshot tables

## Phase 2: Validation And Metadata Layer

### Goal
讓資料層不只是能讀，還能知道可不可信、缺了什麼。

### Scope
- completeness checks
- grain checks
- schema validation
- fallback metadata placeholders
- manifests / logs 結構

### Exit Criteria
- 能對每個資料域產出 validation summary
- 能對 snapshot / time-series 做明確標示
- 能清楚回報缺欄位與缺日期問題

## Phase 3: First Model Integration

### Goal
先整合一個最有機會成功的模型，打通端到端流程。

### Recommended First Model
- `TW hybrid model`

### Why
- 目前 raw price 與 benchmark 是最成熟資料域
- 這個模型對 price history 的依賴高，與現況匹配較好

### Exit Criteria
- 單一模型可以透過 shared data layer 取得輸入
- adapter 能運作
- 模型結果可被平台統一結構接收

## Phase 4: Second / Third Model Expansion

### Recommended Order
1. `IMFS_TW_Stock`
2. `tw-buffett-quant-app`

### Goal
把資料來源品質、validation、以及 monthly revenue 缺口真正逼出來。

### Exit Criteria
- 至少三個模型可以獨立執行
- 不同模型失敗時不互相阻塞
- UI 能顯示 per-model status

## Phase 5: Buffett-Series Adapters

### Target Models
- `buffett-stock-tw`
- `第二版 2_0 by claude`

### Goal
處理 SQLite-style 習慣與 fundamentals history 缺口。

### Major Risks
- annual / quarterly period 不清
- 原模型可能假設本地 DB 型態
- valuation / fundamentals history 可能仍不足

### Exit Criteria
- 兩個 Buffett 系列模型至少可在受控資料條件下執行
- 缺資料時有清楚 warning，不 silently fail

## Phase 6: Unified UI Integration

### Goal
把多模型結果收斂成同一個使用體驗。

### Scope
- dashboard overview
- model comparison table
- per-model detail page / tab
- data status view
- system explanation view

### Exit Criteria
- 使用者可以輸入 ticker 並看到多模型結果
- 可清楚看到資料日期、資料來源、模型狀態
- 可清楚分辨不同模型並列結果，而不是被強行合併

## Phase 7: Hardening

### Goal
讓平台從可跑提升到可維護。

### Scope
- better logging
- better warnings
- fallback visibility
- test coverage
- regression checks

### Exit Criteria
- 關鍵資料缺口有明確顯示
- 關鍵模型路徑有最小測試保障
- 文檔與實作沒有明顯分裂

## Non-Negotiable Rules During Implementation
- 不改動模型核心估值公式
- 不把多模型壓成單一總分
- 不隱藏 fallback
- 不在資料不足時偽造 historical fields

## Current Recommendation
如果下一步真的開始寫程式，最穩的切入點不是 UI，而是：

1. shared data normalization skeleton
2. validation summary structure
3. first model adapter for `TW hybrid model`

## Definition Of Planning Completion
若以「規劃階段是否已足以進入第一版實作」來看，目前已接近完成。

剩餘仍建議在實作前再補一次確認的只有：
1. monthly revenue 是否真的不在 shared root
2. valuation snapshot 的來源與更新日期如何補 metadata
3. Buffett 系列模型對 SQLite 的依賴到底有多深
