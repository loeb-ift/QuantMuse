# 智慧股票分析 API

這是一個由 Ollama 大型語言模型驅動的智慧股票分析 API 服務。它能夠接收公司名稱或股票代號，自動獲取市場數據，並利用 AI 進行深入的市場、技術、風險和投資建議分析。

此 API 設計為可被外部工作流自動化工具（如 n8n）輕鬆整合。

## 專案架構

本專案包含以下四個核心檔案，全部位於 `api/` 目錄下：

-   `api_server.py`:
    -   **職責**: API 伺服器的進入點。
    -   **技術**: 使用 FastAPI 框架建立網路服務。
    -   **功能**: 提供 `/analyze` 和 `/update-list` 兩個端點，處理 HTTP 請求，並呼叫後端分析邏輯。

-   `stock_analyzer.py`:
    -   **職責**: 核心分析邏輯模組。
    -   **功能**: 包含從公司查找、數據獲取、技術因子計算到呼叫 LLM 進行分析的完整流程。其核心功能被封裝在 `run_analysis` 函式中，供 `api_server.py` 導入和呼叫。

-   `update_company_list.py`:
    -   **職責**: 公司數據庫的維護工具。
    -   **技術**: 使用 `twstock` 套件。
    -   **功能**: 從台灣證券交易所獲取所有上市 (`.TW`) 和上櫃 (`.TWO`) 公司的最新列表，並智能地更新 `companies.json`。

-   `companies.json`:
    -   **職責**: 本地的公司資料庫。
    -   **功能**: 儲存所有公司的股票代號、名稱和別名。`update_company_list.py` 負責更新此檔案，`stock_analyzer.py` 則依賴此檔案進行公司查找。

## 安裝與設定

本專案的所有 Python 依賴都已在 `requirements.txt` 中定義。請使用以下命令進行安裝：

```bash
pip install -r requirements.txt
```

## 使用方法

### 1. 更新公司列表 (建議初次使用時執行)

在終端機中，進入 `api` 目錄，然後執行：
```bash
python update_company_list.py
```
這將會生成或更新 `companies.json` 檔案，確保您的公司數據是最新的。

### 2. 啟動 API 伺服器

您可以指定埠號來啟動伺服器。

**使用預設埠號 (8000):**
```bash
python api_server.py
```

**使用自訂埠號 (例如 9999):**
```bash
python api_server.py --port 9999
```
伺服器啟動後，您可以在瀏覽器中打開 `http://127.0.0.1:<您的埠號>/docs` 來查看並使用自動生成的互動式 API 文件。

### 3. 呼叫 API

#### 端點: `POST /analyze`

此端點用於對指定公司進行分析。

**Curl 示範:**
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/analyze' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "company": "台積電"
}'
```

**請求 Body:**
```json
{
  "company": "要分析的公司名稱、代號或別名"
}
```

**成功回應 (200 OK):**
API 會返回一個包含完整分析報告的 JSON 物件。所有由 AI 生成的內容都將是結構化的 JSON。

**失敗回應:**
-   **404 Not Found**: 如果在 `companies.json` 中找不到指定的公司。
-   **500 Internal Server Error**: 如果在分析過程中發生其他錯誤（例如，數據獲取失敗、AI 模型無回應等）。

#### 端點: `POST /update-list`

此端點用於觸發公司列表的更新。

**Curl 示範:**
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/update-list' \
  -H 'accept: application/json' \
  -d ''
```

**成功回應 (200 OK):**
```json
{
  "status": "success",
  "message": "公司列表更新成功。",
  "output": "更新腳本的日誌輸出..."
}