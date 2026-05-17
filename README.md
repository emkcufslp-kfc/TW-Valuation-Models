# TW Valuation Models

台股多模型估值平台，整合多種估值方法與一個獨立的 `Final AI` 判讀層，支援：

- `Buffett TW`
- `Buffett 2.0`
- `Buffett 3.0`
- `IMFS`
- `台股 Buffett Quant`
- `混合模型`
- `Final AI 專區`

目前專案可本地執行 Streamlit UI，並可針對任意 ticker 下載最新資料、重跑模型、更新 `Final AI` 內容。

## 目前功能

- 整合 TOP100 台股資料集建置
- 多模型估值結果生成
- `Buffett 3.0` 台灣市場適配與分類邏輯
- `Final AI` 模組：
  - 獨立 AI 估值
  - 內部模型比較
  - 新聞 / 法人 / 公眾評論整合
  - 最終估值結論、建議、風險
- UI 支援左側直接切到 `Final AI 專區`
- 支援任意 ticker 的最新資料重跑

## 環境需求

- Python `3.10+` 建議
- Windows PowerShell 已測試

主要套件在 [requirements.txt](/D:/Codex%20projects/TW%20Valuation%20models/requirements.txt)：

- `pandas`
- `numpy`
- `PyYAML`
- `streamlit`
- `scikit-learn`
- `xgboost`
- `backtrader`
- `yfinance`
- `matplotlib`

## 安裝

在專案根目錄執行：

```powershell
python -m pip install -r requirements.txt
```

如果你想把依賴裝在專案本地目錄，也可以使用：

```powershell
python -m pip install -r requirements.txt --target .deps
```

## 啟動 UI

```powershell
python -m streamlit run app.py
```

啟動後預設可在：

- [http://127.0.0.1:8501](http://127.0.0.1:8501)

## UI 使用方式

### 主頁總覽

主頁會顯示：

- 多模型卡片摘要
- 目前股價、合理價、信心度
- 各模型的個股比較

### Final AI 專區

左側 sidebar 現在有獨立入口：

- `主頁總覽`
- `Final AI 專區`
- `研究參考與附錄`

切到 `Final AI 專區` 時，系統會針對**目前選中的 ticker**：

1. 重建最新資料
2. 重跑全部模型
3. 重新抓取最新：
   - 新聞
   - 法人 / 機構來源頁
   - 公眾 / 散戶來源頁
4. 重建 `Final AI` payload

也就是說，`Final AI` 頁面不是單純讀舊快照，而是會刷新當前 ticker 的最新結果。

### 任意 ticker

左側欄可直接輸入任意代號，例如：

- `2308`
- `2454`
- `1101`
- `2881`

按下：

- `下載最新資料並生成全部模型`

系統就會用最新可取得資料重跑該 ticker 的：

- dataset
- 所有估值模型
- `Final AI`

## CLI

CLI 入口在 [tw_valuation_models/cli.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/cli.py)。

### 建立 TOP100 資料集

```powershell
python -m tw_valuation_models build-top100
```

### 生成 TOP100 全模型結果

```powershell
python -m tw_valuation_models build-results
```

### 一次跑完整流程

```powershell
python -m tw_valuation_models run-all
```

### 下載 Final Module 原始來源

```powershell
python -m tw_valuation_models fetch-final-module-sources --overwrite
```

### 建立 Final Module normalized snapshot

```powershell
python -m tw_valuation_models build-final-module-snapshot
```

### 跑 Final Module pilot

```powershell
python -m tw_valuation_models run-final-module-pilot --overwrite
```

### 建立 Final Module payload

```powershell
python -m tw_valuation_models build-final-module-payloads
```

## 主要目錄

### 原始碼

- [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py)
- [tw_valuation_models](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models)
- [tests](/D:/Codex%20projects/TW%20Valuation%20models/tests)

### 規格與設計文件

- [BUFFETT_3_0_V1_SPEC.md](/D:/Codex%20projects/TW%20Valuation%20models/BUFFETT_3_0_V1_SPEC.md)
- [IMPLEMENTATION_ROADMAP.md](/D:/Codex%20projects/TW%20Valuation%20models/IMPLEMENTATION_ROADMAP.md)
- [DATA_DOWNLOADER_BLUEPRINT.md](/D:/Codex%20projects/TW%20Valuation%20models/DATA_DOWNLOADER_BLUEPRINT.md)
- [working.md](/D:/Codex%20projects/TW%20Valuation%20models/working.md)

### 不納入 Git 的本地生成物

`.gitignore` 目前已排除：

- `artifacts/`
- `.deps/`
- `__pycache__/`
- 本地暫存 log

## 測試

完整測試：

```powershell
python -m unittest
```

常用核心測試：

```powershell
python -m unittest tests.test_app_reporting tests.test_dataset tests.test_buffett_three tests.test_final_module_data tests.test_final_module_payloads
```

編譯檢查：

```powershell
python -m compileall tw_valuation_models tests app.py
```

## 已知限制

- `新聞 / 法人 / 公眾評論` 現在已經會**每次重新抓最新來源**
- 但對任意 ticker 來說，外部評論層的結構化抽取目前仍屬**輕量版**
- 也就是：
  - 最新來源頁會刷新
  - `Final AI` 會更新
  - 但不是每個 ticker 都能像 pilot 標的那樣拿到同等深度的評論整理

目前最成熟的 `Final AI` 驗證路徑，是不同類型的代表 ticker：

- `2330`
- `2881`
- `2603`
- `2412`

## 開發備註

- 這個 repo 優先保留可重現的程式、測試與規格文件
- 本地資料、快取、下載結果與 payload 目前不直接提交到 Git
- `Final AI` 模組設計上是加在現有模型之上的判讀層，不會直接改寫既有估值公式
