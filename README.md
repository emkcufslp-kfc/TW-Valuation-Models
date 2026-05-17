# TW Valuation Models

台股多模型估值平台，整合多套估值邏輯與 `Final AI` 最終評論模組，提供：

- `Buffett TW`
- `Buffett 2.0`
- `Buffett 3.0`
- `IMFS`
- `台股 Buffett Quant`
- `混合模型`
- `Final AI 專區`

目前系統支援：

- TOP100 資料集建置
- 任意 ticker 即時重跑
- 最新資料下載與模型刷新
- `Final AI` 的新聞 / 法人 / 公眾評論整合
- 本地 Streamlit UI

## 主要功能

- 產生多模型估值比較
- 顯示各模型的合理價、價值差距與信心度
- 針對目前選中 ticker 即時重跑資料與模型
- 在 `Final AI 專區` 提供：
  - 獨立 AI 估值
  - 內部模型比較
  - 新聞摘要
  - 法人 vs 公眾觀點
  - 最終結論與風險

## 安裝需求

- Python `3.10+`
- Windows PowerShell 或其他可執行 Python 的終端

主要套件定義於 [requirements.txt](/D:/Codex%20projects/TW%20Valuation%20models/requirements.txt)：

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

```powershell
python -m pip install -r requirements.txt
```

如果想把依賴安裝到 repo 內本地資料夾：

```powershell
python -m pip install -r requirements.txt --target .deps
```

## 啟動本地 UI

```powershell
python -m streamlit run app.py
```

或使用為 Streamlit Community Cloud 準備的標準入口：

```powershell
python -m streamlit run streamlit_app.py
```

啟動後預設可從瀏覽器開啟：

- [http://127.0.0.1:8501](http://127.0.0.1:8501)

## 免費公開部署

這個專案目前的免費公開部署首選是 **Streamlit Community Cloud**：

- [Deploy your app](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [Share your app publicly](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app)

### 建議的部署入口

在 Streamlit Community Cloud 建議使用：

- `streamlit_app.py`

它是 repo 內的標準入口包裝檔，會啟動主應用程式。

### 雲端環境變數

如果部署環境不是本機，建議至少設定：

- `TVM_WORKSPACE_ROOT`
- `TVM_SHARED_DATA_ROOT`

外部模型來源現在已經隨 repo 內建；若未額外設定，系統會直接使用 repo 相對路徑：

- `_external/imfs_tw_stock`
- `_external/tw_buffett_quant`
- `_external/tw_hybrid_model`

你可以參考 [.streamlit/secrets.toml.example](/D:/Codex%20projects/TW%20Valuation%20models/.streamlit/secrets.toml.example) 準備部署用設定。

### 完整部署預設

目前 repo 已內建：

- `IMFS`
- `台股 Buffett Quant`
- `混合模型`

因此在正常情況下，Streamlit Community Cloud 會直接跑完整版本，不需要再另外掛載三個外部模型 repo。

只有在你手動覆寫下列環境變數，而且路徑指向錯誤位置時，這三個模型才可能回退成 `unavailable`：

- `TVM_IMFS_SOURCE_ROOT`
- `TVM_QUANT_SOURCE_ROOT`
- `TVM_HYBRID_SOURCE_ROOT`

## UI 使用方式

### 主頁總覽

主頁會顯示：

- 各模型快照
- 估值摘要與資料批次
- 目前 ticker 的模型明細

### Final AI 專區

左側 sidebar 提供獨立入口：

- `主頁總覽`
- `Final AI 專區`
- `研究參考與附錄`

切入 `Final AI 專區` 時，系統會針對**目前選中的 ticker**：

1. 下載最新資料
2. 重跑全部估值模型
3. 重新抓取最新市場脈絡：
   - 新聞
   - 法人 / 機構來源
   - 公眾 / 散戶來源
4. 更新 `Final AI` payload

### 任意 ticker

左側欄可以直接輸入任意 ticker，例如：

- `2308`
- `2454`
- `1101`
- `2881`

然後執行：

- `下載最新資料並生成全部模型`

系統會為該 ticker 建立：

- dataset
- 全模型結果
- `Final AI`

## CLI

CLI 入口位於 [tw_valuation_models/cli.py](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models/cli.py)。

### 建立 TOP100 資料集

```powershell
python -m tw_valuation_models build-top100
```

### 產生 TOP100 模型結果

```powershell
python -m tw_valuation_models build-results
```

### 一次執行全部流程

```powershell
python -m tw_valuation_models run-all
```

### 抓取 Final Module 外部來源

```powershell
python -m tw_valuation_models fetch-final-module-sources --overwrite
```

### 建立 Final Module normalized snapshot

```powershell
python -m tw_valuation_models build-final-module-snapshot
```

### 執行 Final Module pilot

```powershell
python -m tw_valuation_models run-final-module-pilot --overwrite
```

### 建立 Final Module payload

```powershell
python -m tw_valuation_models build-final-module-payloads
```

## 專案結構

### 主要程式

- [app.py](/D:/Codex%20projects/TW%20Valuation%20models/app.py)
- [streamlit_app.py](/D:/Codex%20projects/TW%20Valuation%20models/streamlit_app.py)
- [tw_valuation_models](/D:/Codex%20projects/TW%20Valuation%20models/tw_valuation_models)
- [tests](/D:/Codex%20projects/TW%20Valuation%20models/tests)

### 規格與工作紀錄

- [BUFFETT_3_0_V1_SPEC.md](/D:/Codex%20projects/TW%20Valuation%20models/BUFFETT_3_0_V1_SPEC.md)
- [IMPLEMENTATION_ROADMAP.md](/D:/Codex%20projects/TW%20Valuation%20models/IMPLEMENTATION_ROADMAP.md)
- [DATA_DOWNLOADER_BLUEPRINT.md](/D:/Codex%20projects/TW%20Valuation%20models/DATA_DOWNLOADER_BLUEPRINT.md)
- [working.md](/D:/Codex%20projects/TW%20Valuation%20models/working.md)

## 測試

執行全部單元測試：

```powershell
python -m unittest
```

執行較常用的核心測試：

```powershell
python -m unittest tests.test_app_reporting tests.test_dataset tests.test_buffett_three tests.test_final_module_data tests.test_final_module_payloads
```

檢查可編譯性：

```powershell
python -m compileall tw_valuation_models tests app.py streamlit_app.py
```

## 已知限制

- `新聞 / 法人 / 公眾評論` 目前已是即時更新，但對非 pilot ticker 的抽取深度仍可再強化
- `IMFS / 台股 Buffett Quant / 混合模型` 已隨 repo 內建；若這三個模型顯示 `unavailable`，通常代表部署環境讀取 `_external/` 失敗或被手動覆寫到錯誤路徑
- `Final AI` 的市場脈絡品質目前在下列 ticker 最成熟：
  - `2330`
  - `2881`
  - `2603`
  - `2412`

## Git 注意事項

- `.gitignore` 目前排除：
  - `artifacts/`
  - `.deps/`
  - `__pycache__/`
  - 暫存 log
- 若重新抓取資料或重建 payload，通常不需要把產物直接提交到 Git
