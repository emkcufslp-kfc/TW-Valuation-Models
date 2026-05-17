# APP_ARCHITECTURE_PLAN

## 文件目的
本文件用於定義 `TW Valuation Models` 整合應用的目標架構，作為後續實作前的共識基準。

本文件只處理：
- 模組邊界
- 資料流向
- 系統責任分工
- 風險與非目標

本文件不處理：
- 實作細節
- 程式碼結構定稿
- 單一模型公式改寫
- UI 視覺像素級規格

## 專案目標
建立一個台股估值整合平台，在單一 UI 中整合多個估值模型，同時保留每個模型的獨立性、原始邏輯與可單獨執行能力。

## 核心原則
- 每個模型都是獨立引擎，不合併成單一評分公式。
- 共用資料層，不共用估值邏輯。
- 平台可統一下載、清理、轉換資料，但不得任意改寫原模型判斷規則。
- 前台 UI 統一呈現，後台模型各自輸出。
- 所有使用者可見內容以繁體中文為主。

## 已確認模型清單
1. `clone value investing dashboard/buffett-stock-tw`
2. `clone value investing dashboard/第二版 2_0 by claude`
3. `IMFS_TW_Stock`
4. `TWSE aihedge/tw-buffett-quant-app`
5. `TW hybrid model/Taiwwan-stock-hybrid-model`

註：
- 實際資料夾名稱仍需依本機路徑確認。
- 現有工作筆記中部分路徑文字有編碼異常，正式實作前需先校正。

## 目標系統分層
整體系統分為三層：

1. Shared Data Layer
2. Independent Model Wrapper Layer
3. Unified UI Layer

## Layer 1: Shared Data Layer
### 角色
平台唯一的資料進出入口，負責：
- 資料下載
- 原始資料保存
- 標準化欄位轉換
- 品質檢查
- 產出各模型可讀取的輸入資料

### 主要責任
- 維護統一資料根目錄
- 保留資料來源與時間戳記
- 定義 canonical field schema
- 提供模型輸入轉接所需的中間資料
- 管理 fallback source 順序

### 建議資料分層
- `raw/`
- `normalized/`
- `model_inputs/`
- `manifests/`
- `logs/`
- `cache/`
- `backup/`

### 建議資料領域
- universe
- price
- fundamentals
- valuation
- benchmark

### 不應承擔的責任
- 不做模型分數計算
- 不決定買賣訊號
- 不替模型修正原始投資邏輯

## Layer 2: Independent Model Wrapper Layer
### 角色
每個模型都透過自己的 adapter / runner 包裝，從共用資料層取得資料，再輸出該模型原生結果。

### 主要責任
- 讀取 shared normalized data 或 model-ready data
- 對應原模型所需欄位格式
- 維持各模型原始輸出邏輯
- 回傳平台可顯示的標準化結果結構

### 建議包裝方式
每個模型至少包含以下責任元件：
- `input adapter`
- `runner`
- `result normalizer`
- `metadata descriptor`

### 模型 wrapper 必須保留的特性
- 可單獨啟用或停用
- 可獨立回報錯誤
- 可各自標示資料新鮮度
- 可各自標示 fallback 狀態

### 不應承擔的責任
- 不直接管理全平台資料下載
- 不直接修改其他模型輸出
- 不混用別的模型公式補齊本模型缺值

## Layer 3: Unified UI Layer
### 角色
提供單一使用者操作入口，整合多模型結果與資料狀態。

### 主要責任
- 顯示總覽儀表板
- 顯示模型比較結果
- 顯示單一模型明細
- 顯示資料來源與更新狀態
- 顯示警示、缺值、 fallback 與錯誤訊息

### 已確認 UI 方向
- 單一整合式 dashboard
- 首頁主區塊支援模型比較
- 每個模型有各自 detail section 或 tab
- 整體風格偏深色、專業、研究平台感

## 核心資料流
1. Upstream sources 提供原始資料。
2. Shared Data Layer 下載並保存 raw data。
3. Shared Data Layer 進行標準化與驗證。
4. Shared Data Layer 產出 model-ready inputs。
5. Independent Model Wrappers 各自讀取對應輸入。
6. 各模型輸出原生結果與必要 metadata。
7. Unified UI Layer 彙整後展示給使用者。

## 建議平台輸出標準
雖然模型邏輯不能統一，但平台顯示層應有最小共通輸出結構，例如：
- `ticker`
- `company_name`
- `model_id`
- `model_display_name`
- `run_timestamp`
- `data_as_of`
- `valuation_signal`
- `fair_value_low`
- `fair_value_base`
- `fair_value_high`
- `upside_downside_pct`
- `confidence_note`
- `source_summary`
- `warning_flags`

註：
- 非所有模型都一定能提供上述全部欄位。
- 無法提供時應允許 `null`，並在 UI 顯示「不適用」或「該模型未提供」。

## 建議模組邊界
### Platform Core
負責：
- config
- path management
- logging
- shared schemas
- exception handling

### Data Services
負責：
- source clients
- downloader orchestration
- normalization
- validation
- freshness tracking

### Model Services
負責：
- model registry
- model wrappers
- per-model execution
- result normalization

### Presentation Layer
負責：
- page routing
- widgets
- tables
- charts
- model compare cards
- source status banners

## 模型註冊概念
平台應有一個 model registry，至少記錄：
- `model_id`
- `display_name_zh_tw`
- `display_name_en`
- `description`
- `required_data_domains`
- `supports_batch_run`
- `supports_single_ticker_run`
- `output_shape_notes`
- `status`

這能讓 UI、排程、資料檢查與錯誤提示都依賴同一份模型描述。

## 錯誤與降級策略
### 資料層錯誤
- 若主來源失敗，依 fallback 規則切換。
- 若切換後成功，必須保留來源標記。
- 若全部失敗，應回報資料不足，不可 silently fabricate。

### 模型層錯誤
- 單一模型執行失敗時，不應阻斷整個平台。
- UI 應顯示該模型暫時不可用與錯誤摘要。

### UI 層錯誤
- 單一區塊異常時，其他區塊應可繼續顯示。
- 重要狀態如資料更新時間不可被隱藏。

## 非功能性要求
- 可維護性：模型與資料層解耦。
- 可追溯性：資料來源、更新時間、fallback 必須可查。
- 可擴充性：未來可新增更多模型。
- 可觀測性：每次下載、轉換、執行都可記錄。
- 國際化準備：雖以繁中為主，結構上應允許中英欄位描述。

## 明確非目標
- 不把五個模型整併成單一總分模型。
- 不先做自動交易。
- 不在規劃階段承諾即時報價串流。
- 不在資料不足時杜撰估值欄位。

## 主要風險
1. 各模型欄位需求不一致，尤其歷史 PE/PB、季度與年度口徑差異大。
2. 部分舊模型依賴 SQLite 或本地資料慣例，轉接成本較高。
3. 官方資料、FinMind、yfinance 的欄位命名與可用期間可能不一致。
4. UI 若過度抽象化，可能掩蓋模型之間本質差異。
5. 共用資料層若缺少 provenance，後續 debug 會很困難。

## 實作前建議先完成的文件
1. `DATA_DOWNLOADER_BLUEPRINT.md`
2. `DATA_FIELD_MAPPING.md`
3. `DATA_GAP_AUDIT_TEMPLATE.md`
4. `UI_CONTENT_PLAN_ZH_TW.md`

## 下一步建議
在不進入程式實作的前提下，下一個最務實的動作是：

1. 用 `DATA_GAP_AUDIT_TEMPLATE.md` 逐表盤點現有資料。
2. 回填每個模型真正缺的欄位與時間粒度。
3. 再根據缺口反推 downloader 與 adapter 的優先順序。
