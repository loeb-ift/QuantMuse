#!/usr/bin/env python3
"""
股票分析 API 伺服器

使用 FastAPI 框架，提供一個可以被外部服務（如 n8n）呼叫的 API 端點。
"""

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import sys
import argparse

# 導入我們重構後的核心分析函數
from stock_analyzer import run_analysis

app = FastAPI(
    title="智慧股票分析 API",
    description="一個由 Ollama LLM 驅動的股票分析 API，可供 n8n 等外部工具呼叫。",
    version="1.0.0",
)

class CompanyQuery(BaseModel):
    company: str

@app.post("/analyze", summary="分析指定公司")
async def analyze_stock(query: CompanyQuery):
    """
    接收一個公司名稱或代號，執行完整的分析流程，並返回 JSON 格式的報告。

    - **company**: 要查詢的公司名稱、代號或別名 (例如 "台積電", "2330.TW", "tsmc").
    """
    print(f"接收到 API 請求，分析目標: {query.company}")
    
    # 呼叫核心分析邏輯
    result = run_analysis(query.company)

    if "error" in result:
        # 如果分析過程中出現錯誤，返回 404 或 500 錯誤
        if "找不到公司" in result["error"]:
            raise HTTPException(status_code=404, detail=result["error"])
        else:
            raise HTTPException(status_code=500, detail=result["error"])
    
    return result

@app.post("/update-list", summary="更新公司列表")
async def update_list():
    """
    觸發執行 `update_company_list.py` 腳本，以獲取最新的公司列表。
    """
    print("接收到更新公司列表的 API 請求...")
    try:
        # 使用 subprocess 在背景執行更新腳本
        script_dir = os.path.dirname(__file__)
        update_script_path = os.path.join(script_dir, "update_company_list.py")
        process = subprocess.Popen(
            [sys.executable, update_script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            error_message = stderr.decode('utf-8')
            print(f"更新腳本執行失敗: {error_message}")
            raise HTTPException(status_code=500, detail=f"更新腳本執行失敗: {error_message}")

        success_message = stdout.decode('utf-8')
        print(f"更新腳本執行成功: {success_message}")
        return {"status": "success", "message": "公司列表更新成功。", "output": success_message}

    except Exception as e:
        print(f"觸發更新時發生錯誤: {e}")
        raise HTTPException(status_code=500, detail=f"觸發更新時發生意外錯誤: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="股票分析 API 伺服器")
    parser.add_argument("--port", type=int, default=8000, help="指定伺服器運行的埠號")
    args = parser.parse_args()

    print("啟動 FastAPI 伺服器...")
    print(f"API 文件位於 http://127.0.0.1:{args.port}/docs")
    uvicorn.run(app, host="0.0.0.0", port=args.port)