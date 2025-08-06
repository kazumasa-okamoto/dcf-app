import numpy as np
from numpy import linspace
from copy import deepcopy


def compute_dcf_valuation(cf_list, wacc, perpetual_growth_rate):
    """
    DCF法により企業価値を算出する関数。

    Parameters:
        cf_list (List[dict]): 予測されたキャッシュフローリスト（各要素に 'fcf' を含む）
        wacc (float): 加重平均資本コスト（例：0.084）
        perpetual_growth_rate (float): 永久成長率（例：0.02）

    Returns:
        float: DCFベースの企業価値（事業価値）
    """

    # 10年間の予測分を切り取る
    cf_list = cf_list[:10]

    enterprise_value = 0.0

    # 1年目〜10年目の割引FCF
    for t, cf in enumerate(cf_list, start=1):
        fcf = cf.get("fcf", 0)
        discounted_fcf = fcf / ((1 + wacc) ** t)
        enterprise_value += discounted_fcf

    # ターミナルバリューの計算（10年目のFCFを基に）
    final_fcf = cf_list[-1].get("fcf", 0)
    terminal_value = final_fcf * (1 + perpetual_growth_rate) / (wacc - perpetual_growth_rate)
    discounted_terminal_value = terminal_value / ((1 + wacc) ** 10)

    enterprise_value += discounted_terminal_value

    return enterprise_value


def compute_fair_share_price_from_bs(enterprise_value, bs_list, market_data):
    """
    企業価値と最新BSおよび市場データから理論株価（1株あたりの価値）を算出する。

    Parameters:
        enterprise_value (float): DCF法等で求めた企業価値（Enterprise Value）
        bs_list (List[dict]): 整形済みBSデータ（昇順ソート済み）
        market_data (dict): {
            "shares_outstanding": float,
            "price": float,
            ...
        }

    Returns:
        dict: {
            "enterprise_value": float,
            "net_debt": float,
            "equity_value": float,
            "fair_share_price": float,
            "current_market_price": float
        }
    """
    if not bs_list or market_data.get("shares_outstanding", 0.0) == 0.0:
        raise ValueError("BSデータまたは株式数が不正です")

    latest_bs = bs_list[-1]
    cash = latest_bs.get("cash_and_equivalents", 0.0)
    short_term_debt = latest_bs.get("short_term_debt", 0.0)
    long_term_debt = latest_bs.get("long_term_debt", 0.0)

    interest_bearing_debt = short_term_debt + long_term_debt
    net_debt = interest_bearing_debt - cash

    equity_value = enterprise_value - net_debt
    fair_price = equity_value / market_data["shares_outstanding"]
    current_price = market_data.get("price", None)

    return {
        "enterprise_value": enterprise_value,
        "net_debt": net_debt,
        "equity_value": equity_value,
        "fair_share_price": fair_price,
        "current_market_price": current_price
    }


def sensitivity_analysis_dcf(cf_list, base_wacc, base_growth, 
                             wacc_range=(-0.01, 0.01), 
                             growth_range=(-0.005, 0.005), 
                             wacc_steps=5, growth_steps=5):
    """
    WACCと永久成長率の感応度分析を行う。

    Parameters:
        cf_list (List[dict]): 将来キャッシュフロー（各年に 'fcf' を含む）
        base_wacc (float): 中心とするWACC（例：0.08）
        base_growth (float): 中心とするg（例：0.02）
        wacc_range (Tuple[float, float]): WACCの変動範囲（±値）
        growth_range (Tuple[float, float]): gの変動範囲（±値）
        wacc_steps (int): WACCの分割数（奇数推奨）
        growth_steps (int): gの分割数（奇数推奨）

    Returns:
        Tuple[np.ndarray, List[float], List[float]]:
            - 感応度マトリクス（行: WACC, 列: g）
            - 使用されたWACCのリスト
            - 使用されたgのリスト
    """

    # 変動幅から値リストを作成
    wacc_list = linspace(base_wacc + wacc_range[0], base_wacc + wacc_range[1], wacc_steps)
    g_list = linspace(base_growth + growth_range[0], base_growth + growth_range[1], growth_steps)

    result_matrix = np.zeros((len(wacc_list), len(g_list)))

    for i, wacc in enumerate(wacc_list):
        for j, g in enumerate(g_list):
            try:
                ev = compute_dcf_valuation(deepcopy(cf_list), wacc, g)
            except ZeroDivisionError:
                ev = np.nan  # WACC == g に近い場合に無限大回避
            result_matrix[i, j] = ev

    return result_matrix, list(wacc_list), list(g_list)

