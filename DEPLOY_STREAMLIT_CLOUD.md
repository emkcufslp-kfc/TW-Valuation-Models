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
- 缺少外部模型來源時的 demo 降級模式：
  - app 不會直接 crash
  - `IMFS / 台股 Buffett Quant / 混合模型` 會顯示 `unavailable`

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

如果你暫時沒有外部模型 repo，不要加也可以：

- `TVM_IMFS_SOURCE_ROOT`
- `TVM_QUANT_SOURCE_ROOT`
- `TVM_HYBRID_SOURCE_ROOT`

那 app 會進入公開 demo 降級模式。

如果你之後想補完整模型，可再加入：

```toml
TVM_IMFS_SOURCE_ROOT = "./_external/imfs_tw_stock"
TVM_QUANT_SOURCE_ROOT = "./_external/tw_buffett_quant"
TVM_HYBRID_SOURCE_ROOT = "./_external/tw_hybrid_model"
```

## 目前最建議的公開方式

### 方案 A：先上線 demo 版

這是目前最務實的做法。

效果：

- app 可以公開開啟
- `Buffett TW / Buffett 2.0 / Buffett 3.0 / Final AI` 可運作
- 缺少外部 repo 的模型會標示 `unavailable`

適合：

- 想先給使用者看
- 想先驗證 UI / 流程 / Final AI 體驗

### 方案 B：完整功能版

若要讓以下模型也完整可用：

- `IMFS`
- `台股 Buffett Quant`
- `混合模型`

則需要把它們的原始碼：

1. 一起整理進目前 repo 的 `_external/`
2. 或在雲端環境提供對應可讀路徑

否則 Community Cloud 上只能進 demo 降級模式。

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

### 1. 外部模型 repo 仍非自包含

目前公開版最大的限制仍是：

- `IMFS`
- `台股 Buffett Quant`
- `混合模型`

不是本 repo 完全自包含的一部分。

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

1. 先部署 demo 版
2. 驗證首頁與 `Final AI 專區`
3. 驗證 `2330 / 2881 / 2603 / 2412`
4. 再決定是否把外部模型完整納入 repo

## 一句話結論

這個 repo 現在已經足夠做：

- **免費公開 demo 部署**

但若要達到：

- **雲端完整版全部模型**

則還需要把外部模型來源一併整理進可部署環境。
