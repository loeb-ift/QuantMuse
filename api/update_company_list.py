#!/usr/bin/env python3
"""
公司列表更新器

本腳本用於從可靠的數據源獲取最新的上市公司列表，
並智能地更新本地的 `companies.json` 檔案。

功能:
1. 從數據源獲取台灣所有上市公司的股票代號和名稱。
2. 讀取現有的 `companies.json` 檔案。
3. 將新獲取的列表與現有列表合併，保留手動添加的別名。
4. 將更新後的完整列表寫回 `companies.json`。
"""

import json
import sys
import twstock

def fetch_twse_stocks():
    """
    使用 'twstock' 套件獲取台灣證券交易所(TWSE)的股票列表。
    """
    print("⏳ 正在從台灣證券交易所獲取最新的公司列表...")
    try:
        # 'twstock.codes' 是一個字典，包含了所有股票的資訊
        # 我們只需要上市公司的部分 (type 為 '股票')
        # 我們需要上市公司和上櫃公司，並根據市場給予不同後綴
        stocks = {}
        for code, data in twstock.codes.items():
            if data.type == '股票':
                if data.market == '上市':
                    stocks[f"{code}.TW"] = data.name
                elif data.market == '上櫃':
                    stocks[f"{code}.TWO"] = data.name
        
        print(f"✅ 成功獲取 {len(stocks)} 家上市/上櫃公司。")
        return stocks
    except Exception as e:
        print(f"❌ 從 'twstock' 獲取資料時發生錯誤: {e}")
        return None

def update_company_file(new_stocks):
    """
    智能更新 companies.json 檔案。
    以新獲取的列表為基礎，只合併舊檔案中手動添加的別名。
    """
    old_data = {"companies": []}
    try:
        with open('companies.json', 'r', encoding='utf-8') as f:
            old_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("ℹ️ 未找到舊的 companies.json 或格式錯誤，將創建新檔案。")

    old_aliases = {company['symbol']: company.get('aliases', []) for company in old_data.get('companies', [])}

    new_companies = []
    for symbol, name in new_stocks.items():
        # 獲取舊的別名，並確保公司名稱本身也在別名列表中
        aliases = old_aliases.get(symbol, [])
        if name.lower() not in aliases:
            aliases.append(name.lower())
        
        # 移除重複的別名
        unique_aliases = sorted(list(set(aliases)))

        new_company = {
            "symbol": symbol,
            "name": name,
            "aliases": unique_aliases
        }
        new_companies.append(new_company)
        print(f"Processed: {symbol} - {name}")

    # 根據 symbol 排序，方便查看
    new_companies = sorted(new_companies, key=lambda x: x['symbol'])
    
    final_data = {"companies": new_companies}

    with open('companies.json', 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    
    print("\n🎉 `companies.json` 檔案已成功更新！")

def main():
    """主函數"""
    print("🚀 開始更新公司列表...")
    new_stocks = fetch_twse_stocks()
    if new_stocks:
        update_company_file(new_stocks)
    else:
        print("❌ 未能獲取到新的公司列表，更新終止。")
        sys.exit(1)
    print("✅ 更新流程完成。")

if __name__ == "__main__":
    main()