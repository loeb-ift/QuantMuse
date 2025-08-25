#!/usr/bin/env python3
"""
通用股票分析器 - 完整Ollama集成流程
使用Alpha Vantage获取真实数据，Ollama进行AI分析
"""

import sys
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import argparse
import subprocess

import yfinance as yf

# 將專案根目錄添加到 sys.path，以確保可以找到 data_service
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from data_service.ai.llm_integration import LLMIntegration, OllamaProvider

# Try to import FactorCalculator, but make it optional
try:
    from data_service.factors import FactorCalculator
    FACTOR_CALCULATOR_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 警告: FactorCalculator 不可用 - {e}")
    print("   請安裝必要的依賴: pip install matplotlib pandas numpy")
    FactorCalculator = None
    FACTOR_CALCULATOR_AVAILABLE = False

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.DEBUG,  # Changed to DEBUG for troubleshooting
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def find_company_info(query, use_llm=True):
    """
    根据查询词在companies.json中查找公司信息。
    支持精确匹配和LLM模糊查找。
    """
    try:
        script_dir = os.path.dirname(__file__)
        json_path = os.path.join(script_dir, 'companies.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("❌ 错误: companies.json 文件未找到。请先运行 update_company_list.py。")
        return None, None
    except json.JSONDecodeError:
        print("❌ 错误: companies.json 文件格式不正确。")
        return None, None

    # 1. 精确匹配 (Symbol 和 Aliases)
    query_lower = query.lower()
    for company in data['companies']:
        if query_lower == company['symbol'].lower() or query_lower in [str(alias).lower() for alias in company['aliases']]:
            return company['symbol'], company['name']

    if not use_llm:
        return None, None

    # 2. 如果精确匹配失败，使用 LLM 进行模糊查找
    print(f"ℹ️ 精确匹配失败，正在启动 LLM 進行智慧查找 '{query}'...")
    try:
        llm = LLMIntegration(
            provider="ollama",
            model="gpt-oss:20b",
            base_url="http://10.227.135.98:11434"
        )
        
        # 為了優化提示長度，我們只提供 symbol 和 name
        company_list_for_prompt = [{"symbol": c["symbol"], "name": c["name"]} for c in data['companies']]

        prompt = f"""
        這是一個台灣上市櫃公司的部分列表:
        {json.dumps(company_list_for_prompt[:500], indent=2, ensure_ascii=False)}
        ... (還有更多)

        任務: 請從整個列表中，找出與使用者查詢 '{query}' 最相關的公司。
        規則:
        1. 優先考慮語意和數字上的關聯性 (例如 "104" 對應到 "一零四")。
        2. 如果找到，請只返回那家公司的'symbol'，例如 "3130.TW"。
        3. 不要返回任何解釋、引號或其他多餘的文字。
        4. 如果完全找不到任何相關的公司，請只返回 "NULL"。

        使用者的查詢是: '{query}'
        最相關的 symbol 是:
        """

        response = llm.answer_trading_question(prompt)
        llm_result = response.content.strip()

        if llm_result and llm_result != "NULL":
            print(f"✅ LLM 找到最可能的代號是: {llm_result}")
            # 用LLM返回的結果再次進行精確查找
            for company in data['companies']:
                if llm_result.upper() == company['symbol'].upper():
                    return company['symbol'], company['name']
        
        return None, None

    except Exception as e:
        print(f"❌ LLM 智慧查找失敗: {e}")
        return None, None
        print("❌ 错误: companies.json 文件未找到。")
        return None, None
    except json.JSONDecodeError:
        print("❌ 错误: companies.json 文件格式不正确。")
        return None, None

def get_stock_data(symbol, company_name):
    """获取指定公司的股票数据"""
    logger = setup_logging()
    logger.info(f"开始使用 yfinance 获取 {company_name} ({symbol}) 的股票数据...")

    try:
        # 获取过去30天的日线数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        logger.info(f"获取 {symbol} 数据: {start_date.date()} 到 {end_date.date()}")

        # 使用 yfinance 下载数据，并加入错误处理
        try:
            stock_data = yf.download(symbol, start=start_date, end=end_date, progress=False)
            print(f"--- yfinance 返回數據 (前5行) ---\n{stock_data.head()}\n---------------------------------")
            if stock_data.empty:
                # yfinance 对无效的 ticker 可能返回空 DataFrame
                raise ValueError(f"找不到股票代號 {symbol} 的數據，可能已下市或代號錯誤。")
        except Exception as e:
            logger.error(f"使用 yfinance 下载数据时出错: {e}")
            print(f"❌ 无法获取 {symbol} 的股票数据。原因: {e}")
            return None

        if stock_data is not None and not stock_data.empty:
            logger.info(f"成功获取 {len(stock_data)} 条 {company_name} 数据")
            # yfinance 返回的欄位名稱是首字母大寫的，例如 'Close', 'High', 'Low', 'Volume'
            # 我們將其轉換為小寫以匹配舊程式碼的格式
            # 同時處理欄位名稱可能是元組的情況
            stock_data.columns = [c.lower() if isinstance(c, str) else c[0].lower() for c in stock_data.columns]
            return stock_data
        else:
            logger.error(f"未能获取 {company_name} 数据")
            return None

    except Exception as e:
        logger.error(f"获取 {company_name} 数据失败: {e}")
        return None

def calculate_technical_factors(data):
    """计算技术因子"""
    logger = setup_logging()
    logger.info("开始计算技术因子...")

    if not FACTOR_CALCULATOR_AVAILABLE:
        logger.warning("FactorCalculator不可用，跳过技术因子计算")
        return None

    try:
        calculator = FactorCalculator()
        # 计算价格动量因子
        price_momentum = calculator.calculate_price_momentum(data['close'])
        # 计算成交量动量因子
        volume_momentum = calculator.calculate_volume_momentum(data['close'], data['volume'])
        # 合并因子
        factors = {**price_momentum, **volume_momentum}
        # 转换为DataFrame
        factors = pd.DataFrame([factors], index=[data.index[-1]])
        return factors
    except Exception as e:
        logger.error(f"计算技术因子失败: {e}")
        return None

def perform_ollama_analysis(stock_data, symbol, company_name, factors=None):
    """使用Ollama进行AI分析"""
    logger = setup_logging()
    logger.info(f"开始对 {company_name} 进行Ollama AI分析...")

    print("\n" + "="*60)
    print(f"🤖 Ollama AI 分析 {company_name} ({symbol})")
    print("="*60)

    try:
        # 初始化Ollama LLM集成
        llm = LLMIntegration(
            provider="ollama",
            model="gpt-oss:20b",
            base_url="http://10.227.135.98:11434"
        )

        print("✓ 已连接到Ollama AI服务")

        provider_info = llm.get_provider_info()
        print(f"✓ 模型: {provider_info['model']}")
        print(f"✓ 提供商: {provider_info['provider']}")

        # 1. 市场数据分析
        print("\n🔍 1. 市场数据分析")
        print("-" * 40)

        # 计算市场数据摘要
        latest_price = stock_data['close'].iloc[-1]
        price_change = (latest_price / stock_data['close'].iloc[0] - 1) * 100
        avg_volume = stock_data['volume'].mean()
        volatility = stock_data['close'].pct_change().std() * np.sqrt(252) * 100

        market_data_summary = {
            '最新价格': f"${latest_price:.2f}",
            '30日涨跌幅': f"{price_change:.2f}%",
            '30日平均成交量': f"{avg_volume:.0f}",
            '价格波动率': f"{volatility:.2f}%"
        }

        analysis_prompt = f"""
        任务：请使用繁體中文，分析 {company_name} ({symbol}) 的市场数据。
        规则：严格以JSON格式返回分析结果，不要包含任何Markdown或其它非JSON字符。
        
        市场数据:
        {json.dumps(market_data_summary, indent=2, ensure_ascii=False)}

        请根据以下结构返回JSON：
        {{
          "trend_analysis": "...",
          "volume_analysis": "...",
          "volatility_assessment": "...",
          "technical_insights": "...",
          "investment_suggestion": "..."
        }}
        """

        market_response_str = llm.answer_trading_question(analysis_prompt).content
        try:
            market_analysis_json = json.loads(market_response_str)
        except json.JSONDecodeError:
            logger.error(f"市场分析LLM返回的不是有效的JSON: {market_response_str}")
            market_analysis_json = {"error": "LLM response is not valid JSON", "raw_content": market_response_str}

        # 2. 技术分析
        print("\n📈 2. 技术分析")
        print("-" * 40)

        if factors is not None:
            # Convert pandas DataFrame to JSON-serializable format
            tech_factors = factors.tail(5).to_dict('records') if hasattr(factors.tail(5), 'to_dict') else []
            # Convert Timestamp objects to strings
            for factor_dict in tech_factors:
                for key, value in factor_dict.items():
                    if hasattr(value, 'isoformat'):  # Check if it's a datetime-like object
                        factor_dict[key] = value.isoformat()
            tech_prompt = f"""
            任务：基于以下技术因子数据，对 {company_name} ({symbol}) 进行技术分析。
            规则：严格以JSON格式返回分析结果，使用繁體中文，不要包含任何Markdown。

            技术因子:
            {json.dumps(tech_factors, indent=2, default=str)}

            请根据以下结构返回JSON：
            {{
              "momentum_analysis": "...",
              "volatility_assessment": "...",
              "signal_interpretation": "...",
              "trading_point_suggestion": "..."
            }}
            """
        else:
            tech_prompt = f"""
            对 {company_name} ({symbol}) 进行一般性技术分析。
            请考虑其所在行业地位、主要产品、市场竞争格局以及宏观经济因素。
            规则：严格以JSON格式返回分析结果，使用繁體中文，不要包含任何Markdown。
            请根据以下结构返回JSON：
            {{
              "general_analysis": "..."
            }}
            """

        tech_response_str = llm.answer_trading_question(tech_prompt).content
        try:
            tech_analysis_json = json.loads(tech_response_str)
        except json.JSONDecodeError:
            logger.error(f"技术分析LLM返回的不是有效的JSON: {tech_response_str}")
            tech_analysis_json = {"error": "LLM response is not valid JSON", "raw_content": tech_response_str}

        # 3. 风险评估
        print("\n⚠️ 3. 风险评估")
        print("-" * 40)

        risk_prompt = f"""
        任务：对 {company_name} ({symbol}) 股票进行风险评估。
        规则：严格以JSON格式返回分析结果，使用繁體中文，不要包含任何Markdown。

        市场数据:
        - 当前价格: ${stock_data['close'].iloc[-1]:.2f}
        - 30日波动率: {stock_data['close'].pct_change().std()*np.sqrt(252)*100:.2f}%

        请结合公司的具体情况和普遍性风险进行评估，并根据以下结构返回JSON：
        {{
          "overall_risk_level": "...",
          "main_risk_factors": [],
          "mitigation_suggestions": "...",
          "stop_loss_suggestion": "..."
        }}
        """

        risk_response_str = llm.answer_trading_question(risk_prompt).content
        try:
            risk_assessment_json = json.loads(risk_response_str)
        except json.JSONDecodeError:
            logger.error(f"风险评估LLM返回的不是有效的JSON: {risk_response_str}")
            risk_assessment_json = {"error": "LLM response is not valid JSON", "raw_content": risk_response_str}

        # 4. 投资建议
        print("\n💡 4. 投资建议")
        print("-" * 40)

        investment_prompt = f"""
        任务：基于以上所有分析，为 {company_name} ({symbol}) 提供综合投资建议。
        规则：严格以JSON格式返回分析结果，使用繁體中文，不要包含任何Markdown。

        当前股价: ${stock_data['close'].iloc[-1]:.2f}

        请综合所有信息，并根据以下结构返回JSON：
        {{
          "rating": "买入/持有/卖出",
          "target_price": "...",
          "timeline_suggestion": "...",
          "positioning_suggestion": "..."
        }}
        """

        investment_response_str = llm.answer_trading_question(investment_prompt).content
        try:
            investment_recommendation_json = json.loads(investment_response_str)
        except json.JSONDecodeError:
            logger.error(f"投资建议LLM返回的不是有效的JSON: {investment_response_str}")
            investment_recommendation_json = {"error": "LLM response is not valid JSON", "raw_content": investment_response_str}

        # 生成分析报告
        analysis_report = {
            'timestamp': datetime.now().isoformat(),
            'stock': symbol,
            'company': company_name,
            'market_analysis': market_analysis_json,
            'technical_analysis': tech_analysis_json,
            'risk_assessment': risk_assessment_json,
            'investment_recommendation': investment_recommendation_json,
            'ollama_model': llm.get_provider_info().get('model', 'gpt-oss:20b'),
            'analysis_method': 'AI-powered quantitative analysis'
        }

        return analysis_report

    except Exception as e:
        logger.error(f"Ollama分析失败: {e}")
        print(f"❌ Ollama分析失败: {e}")
        return None

def generate_analysis_report(analysis_report):
    """生成分析报告"""
    if not analysis_report:
        return

    company_name = analysis_report['company']
    symbol = analysis_report['stock']

    print("\n" + "="*80)
    print(f"📋 {company_name} ({symbol}) 股票分析报告")
    print("="*80)

    print(f"📅 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🏢 公司: {analysis_report['company']}")
    print(f"🎯 股票代码: {analysis_report['stock']}")
    print(f"🤖 AI模型: {analysis_report['ollama_model']}")

    # 在API模式下，摘要打印可以简化或移除
    print("\n📊 市场分析摘要 (JSON):")
    print(json.dumps(analysis_report.get('market_analysis'), ensure_ascii=False, indent=2))

    print("\n" + "="*80)

    # 保存报告到文件
    report_file = f"{symbol}_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_report, f, ensure_ascii=False, indent=2)

    print(f"✅ 完整分析报告已保存到: {report_file}")
    return report_file

def run_analysis(company_query):
    """
    执行完整的股票分析流程。
    :param company_query: 用户输入的公司名称、别名或代码。
    :return: 包含分析结果的字典，或在失败时返回包含错误信息的字典。
    """
    # 设置日志
    logger = setup_logging()

    try:
        # 步骤1: 查找公司信息
        logger.info(f"查找 '{company_query}' 的信息")
        symbol, company_name = find_company_info(company_query)

        if not symbol:
            # 在API模式下，我们不使用交互式输入，直接返回错误
            error_msg = f"在 'companies.json' 中找不到公司 '{company_query}'。"
            logger.error(error_msg)
            return {"error": error_msg}

        logger.info(f"公司信息找到: {company_name} ({symbol})")

        # 步骤2: 获取股票数据
        logger.info(f"获取 {company_name} 的股票数据")
        stock_data = get_stock_data(symbol, company_name)

        if stock_data is None:
            error_msg = f"无法获取 {company_name} 的数据，分析终止。"
            logger.error(error_msg)
            return {"error": error_msg}

        # 步骤3: 计算技术因子
        logger.info("计算技术因子")
        factors = calculate_technical_factors(stock_data)
        if factors is None:
            logger.warning("技术因子计算失败，将继续进行基础分析")

        # 步骤4: Ollama AI分析
        logger.info("Ollama AI深度分析")
        analysis_report = perform_ollama_analysis(stock_data, symbol, company_name, factors)

        if analysis_report is None:
            error_msg = "AI分析失败"
            logger.error(error_msg)
            return {"error": error_msg}

        # 步骤5: 生成报告文件 (在API模式下可选，但我们保留它)
        logger.info("生成分析报告")
        generate_analysis_report(analysis_report)
        
        return analysis_report

    except Exception as e:
        logger.error(f"分析过程失败: {e}", exc_info=True)
        return {"error": f"分析过程中发生意外错误: {e}"}

def main():
    """主函数，用于命令行执行。"""
    parser = argparse.ArgumentParser(description="通用股票分析器，由Ollama AI驱动。")
    parser.add_argument("--company", type=str, required=True, help="要分析的公司名称、别名或股票代码 (例如 'Apple', 'aapl', '台积电').")
    args = parser.parse_args()

    print(f"🚀 通用股票分析器 - 正在分析: {args.company}")
    print("=" * 80)
    
    result = run_analysis(args.company)

    if "error" in result:
        print(f"\n❌ 分析失败: {result['error']}")
        # 检查是否是找不到公司的特定错误，以提供更新提示
        if "找不到公司" in result['error']:
             print("   請檢查您的輸入，或執行 'python update_company_list.py' 更新列表後重試。")
        sys.exit(1)
    else:
        print(f"\n🎉 {result.get('company')} 分析完成！")
        print(f"📄 报告文件已生成。")
        print("\n🔍 分析亮点:")
        print(f"   • 使用了 {result.get('ollama_model', '未知')} 模型")
        print("   • 结合了市场数据和技术分析")
        print("   • 提供了风险评估和投资建议")
        sys.exit(0)

if __name__ == "__main__":
    main()