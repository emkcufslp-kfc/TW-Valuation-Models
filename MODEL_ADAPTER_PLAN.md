# MODEL_ADAPTER_PLAN

## 文件目的
本文件定義各估值模型接入整合平台時的 adapter 規劃，目標是在不改動模型核心邏輯的前提下，明確說清楚：

1. 每個模型要吃什麼資料
2. 平台要替它補什麼格式轉接
3. 哪些風險會阻擋接入
4. 第一版整合順序應如何安排

## Adapter 設計原則
- adapter 只做資料轉接，不做估值邏輯改寫
- adapter 可以重整欄位名、日期格式、檔案結構
- adapter 不可偷偷替模型補推論公式
- adapter 必須保留模型獨立輸出
- adapter 應輸出平台共通 metadata

## 共通 Adapter 責任
每個模型 adapter 至少應處理：
- input discovery
- field mapping
- grain conversion
- file / table reshaping
- metadata injection
- result normalization

## 共通 Adapter 輸入
來自 shared data layer 的資料可能包括：
- universe snapshot
- price time series
- valuation snapshot
- fundamentals snapshot
- benchmark time series
- metadata / manifests

## 共通 Adapter 輸出
每個模型最終應能回傳平台可理解的結果結構，例如：
- `ticker`
- `model_id`
- `run_timestamp`
- `data_as_of`
- `valuation_signal`
- `fair_value_low`
- `fair_value_base`
- `fair_value_high`
- `upside_downside_pct`
- `warning_flags`
- `source_summary`

## Model 1: `buffett-stock-tw`

### Known Characteristics
- 主要依賴 yfinance
- 偏向 SQLite / local-db workflow
- 需要股價歷史與基本面歷史

### Adapter Responsibility
- 將 shared price data 轉成原模型可接受的歷史價量格式
- 將 fundamentals snapshot / future time series 整成原模型需要的欄位
- 必要時模擬 SQLite 預期的資料結構或中間視圖

### Likely Required Inputs
- price daily history
- annual fundamentals
- quarterly fundamentals
- possibly valuation snapshot

### Current Blockers
- fundamentals 尚未區分 annual / quarterly
- shared data 中尚未有明確 `report_date` / `fiscal_period`
- raw price 尚無 `adjusted_close`

### Integration Risk
- high

### Suggested Phase
- Phase 3

## Model 2: `第二版 2_0 by claude`

### Known Characteristics
- 與 `buffett-stock-tw` 接近
- 依賴 yfinance 與本地結構
- 需要股價快照與基本面歷史

### Adapter Responsibility
- 盡量重用 Model 1 adapter 的資料整備策略
- 視差異補單獨欄位映射層

### Likely Required Inputs
- price daily history
- annual fundamentals
- quarterly fundamentals
- valuation snapshot or simple comparables

### Current Blockers
- 與 Model 1 相同
- 歷史 valuation series 若有使用，現況仍不足

### Integration Risk
- high

### Suggested Phase
- Phase 3

## Model 3: `IMFS_TW_Stock`

### Known Characteristics
- official-data-first mindset
- 對資料來源品質、驗證、fallback 比較敏感
- 使用 TWSE OpenAPI、twstock、yfinance fallback

### Adapter Responsibility
- 提供 provenance-aware input
- 保留來源標記與 quality flags
- 確保 valuation 與 price 口徑一致

### Likely Required Inputs
- universe snapshot
- price daily history
- valuation snapshot / future time series
- validated metadata

### Current Blockers
- provenance / fallback metadata 尚未落地
- valuation 目前只有 snapshot
- 部分 official-first 假設可能無法由現有共享資料直接滿足

### Integration Risk
- medium-high

### Suggested Phase
- Phase 2

## Model 4: `tw-buffett-quant-app`

### Known Characteristics
- 使用 TWSE OpenAPI、MOPS monthly revenue、FinMind、yfinance
- 對 downloader 設計有參考價值

### Adapter Responsibility
- 對接 monthly revenue 與 valuation-related inputs
- 將多來源資料整理成該模型原本的期待格式

### Likely Required Inputs
- universe snapshot
- price daily history
- monthly revenue
- annual fundamentals
- valuation snapshot / history

### Current Blockers
- shared data root 目前尚未觀察到 monthly revenue
- valuation 缺 date
- fundamentals 缺 period

### Integration Risk
- medium-high

### Suggested Phase
- Phase 2 or 3

## Model 5: `TW hybrid model`

### Known Characteristics
- 對 OHLCV 歷史與時間窗品質敏感
- 依賴 yfinance，並有 FinMind、TWSE fallback

### Adapter Responsibility
- 優先保證 price time series 與 benchmark 可用
- 第二優先處理 valuation 與 fundamentals 對接

### Likely Required Inputs
- price daily history
- benchmark daily history
- valuation data
- a limited set of fundamentals

### Current Blockers
- raw price 未見 `adjusted_close`
- valuation history 不足
- 需確認 turnover / liquidity 類欄位是否必要

### Integration Risk
- medium

### Suggested Phase
- Phase 1 or 2

## Recommended Integration Order
1. `TW hybrid model`
2. `IMFS_TW_Stock`
3. `tw-buffett-quant-app`
4. `buffett-stock-tw`
5. `第二版 2_0 by claude`

## Why This Order
- `TW hybrid model` 最能利用目前相對成熟的 raw price + benchmark
- `IMFS_TW_Stock` 雖然重視 provenance，但可幫助平台早期建立 validation discipline
- `tw-buffett-quant-app` 會逼出 monthly revenue 與 multi-source downloader 需求
- 兩個 Buffett 系列模型最容易卡在 SQLite 習慣與 fundamentals period 缺口

## Shared Adapter Utilities Worth Preparing
- ticker normalizer
- date parser / formatter
- snapshot vs time-series discriminator
- file-name-to-ticker resolver
- source metadata injector
- warning flag builder

## Definition Of Done For One Adapter
一個模型 adapter 至少要滿足：
1. 可從 shared data layer 讀取輸入
2. 可完成模型執行前必要格式轉接
3. 不改動模型核心公式
4. 能輸出平台共通結果欄位
5. 能在缺資料時回報清楚 warning

## Current Conclusion
以現況資料成熟度來看，平台不應一開始就追求五個模型同時完整接入。

更穩健的做法是：
- 先做 price / benchmark 驅動較強的模型
- 再做需要更完整 fundamentals history 的模型
