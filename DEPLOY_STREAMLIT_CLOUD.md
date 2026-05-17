# Streamlit Community Cloud 部署手冊

本文件說明如何把 [TW-Valuation-Models](https://github.com/emkcufslp-kfc/TW-Valuation-Models) 部署到 **Streamlit Community Cloud**，讓一般使用者能透過瀏覽器直接使用。

官方文件參考：

- [Deploy your app on Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [File organization for your Community Cloud app](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization)
- [App dependencies for your Community Cloud app](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)
- [secrets.toml reference](https://docs.streamlit.io/develop/api-reference/connections/secrets.toml)

## 目前 repo 已經準備好的部分

這個 repo 現在已經具備以下部署條件：

- 標準 Streamlit 入口：
  - [streamlit_app.py](/D:/Codex%20projects/TW%20Valuation%20models/streamlit_app.py)
- root 級設定檔：
  - [.streamlit/config.toml](/D:/Codex%20projects/TW%20Valuation%20models/.streamlit/config.toml)
- Python 依賴：
  - [requirements.txt](/D:/Codex%20projects/TW%20Valuation%20models/requirements.txt)
- Secrets 樣板：
  - [.streamlit/secrets.toml.example](/D:/Codex%20projects/TW%20Valuation%20models/.streamlit/secrets.toml.example)
- repo 已內建完整外部模型來源：
  - `_external/imfs_tw_stock`
  - `_external/tw_buffett_quant`
  - `_external/tw_hybrid_model`

## 部署步驟

### 1. 登入 Community Cloud

前往：

- [https://share.streamlit.io](https://share.streamlit.io)

用 GitHub 帳號登入，並授權 Streamlit 存取你的 GitHub repo。

### 2. 建立新 app

在 Community Cloud workspace 右上角點：

- `Create app`

然後填入：

- Repository:
  - `emkcufslp-kfc/TW-Valuation-Models`
- Branch:
  - `main`
- Main file path:
  - `streamlit_app.py`

### 3. 設定 Python 版本

依官方文件，Community Cloud 會在建立 app 時於 `Advanced settings` 讓你選擇 Python 版本。

建議：

- 優先選 `3.12`

如果未來某些依賴對 `3.12` 有相容性問題，再回頭調整。

注意：

- 根據官方文件，**部署後不能直接切換 Python 版本**，通常需要刪除 app 再重新部署。

### 4. 設定 Secrets

在 `Advanced settings` 的 `Secrets` 欄位，貼入你的 secrets 內容。

可以先從這個樣板出發：

- [.streamlit/secrets.toml.example](/D:/Codex%20projects/TW%20Valuation%20models/.streamlit/secrets.toml.example)

最小可用版本：

```toml
TVM_WORKSPACE_ROOT = "."
TVM_SHARED_DATA_ROOT = "./artifacts/shared_data"
```

一般情況下，不需要額外設定外部模型來源；repo 會直接使用內建的 `_external/`。

如果你想手動覆寫來源路徑，可再加入：

```toml
TVM_IMFS_SOURCE_ROOT = "./_external/imfs_tw_stock"
TVM_QUANT_SOURCE_ROOT = "./_external/tw_buffett_quant"
TVM_HYBRID_SOURCE_ROOT = "./_external/tw_hybrid_model"
```

## 目前最建議的公開方式

### 完整功能版

目前這個 repo 已經是完整功能版。

以下模型都會一起部署：

- `IMFS`
- `台股 Buffett Quant`
- `混合模型`

也就是說，現在直接用這個 repo 部署到 Streamlit Community Cloud，就會是完整版，而不是只有 demo 降級版。

## 部署成功後應檢查的項目

第一次部署完成後，建議人工檢查以下幾點：

1. app 是否能成功開啟首頁
2. 左側 sidebar 是否正常顯示
3. `Final AI 專區` 是否能切換
4. 任意 ticker 是否可輸入
5. 外部模型缺失時，是否顯示 `unavailable` 而不是整頁報錯
6. `2330` 是否能正常生成 `Final AI`
7. `2308` 這類非 pilot ticker 是否能至少產生基本 Final AI 結果

## 若部署失敗，先看哪裡

根據官方文件，Community Cloud 右側 logs 會顯示部署過程訊息。

優先檢查：

1. `requirements.txt` 是否有依賴安裝失敗
2. `streamlit_app.py` 是否是正確入口
3. `Secrets` 是否有格式錯誤
4. app 是否在啟動時嘗試依賴本機限定路徑
5. 缺少外部模型來源時，是否有新的未處理例外

## 目前已知限制

### 1. 完整模型已隨 repo 自包含

目前 `IMFS`、`台股 Buffett Quant`、`混合模型` 已隨 repo 內建於 `_external/`。

一般情況下不需要額外掛載外部模型來源；只有在你手動覆寫外部模型路徑，或部署環境無法讀取 repo 內容時，這三個模型才可能顯示 `unavailable`。

### 2. Final AI 的外部市場脈絡仍是動態抓取

`新聞 / 法人 / 公眾評論` 已經會即時抓，但：

- 依賴外部網站可用性
- 非 pilot ticker 的抽取品質仍可再強化

### 3. 雲端資源限制

Community Cloud 是免費服務，正式大量使用時仍可能遇到：

- 啟動較慢
- 重跑模型時間較長
- 資料抓取時延

## 建議的實際上線順序

1. 先部署完整版
2. 驗證首頁與 `Final AI 專區`
3. 驗證 `2330 / 2881 / 2603 / 2412`
4. 驗證任意 ticker 與 `Final AI` 的全流程都能成功重跑

## 一句話結論

這個 repo 現在已經足夠做：

- **免費公開完整版部署**

目前已可直接部署成 **雲端完整版全部模型**；後續重點是持續驗證資料抓取穩定性與雲端運行時間，而不是再補外部模型來源。
