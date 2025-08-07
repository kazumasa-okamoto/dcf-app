def compute_cost_of_equity(market_data):
    """
    市場データから株主資本コスト（CAPM）を計算

    Parameters:
        market_data (dict): {
            "risk_free_rate": float,
            "market_risk_premium": float,
            "beta": float
        }

    Returns:
        float: 株主資本コスト
    """
    r_f = market_data["risk_free_rate"]
    risk_premium = market_data["market_risk_premium"]
    beta = market_data["beta"]

    return r_f + beta * risk_premium

def compute_cost_of_debt_from_pl_bs(pl_list, bs_list, years=5):
    """
    直近n年間（デフォルトは5年間）のPLとBSのデータから、
    平均的な負債コスト（Cost of Debt）を推定する。

    Parameters:
        pl_list (List[dict]): 整形済み損益計算書（PL）データ（昇順にソートされていること）
        bs_list (List[dict]): 整形済み貸借対照表（BS）データ（昇順にソートされていること）
        years (int): 集計対象の年数（デフォルトは5年）

    Returns:
        float: 負債コスト（小数、例：0.045）
    """
    # 両リストの長さに基づいて対象期間を決定
    n = min(len(pl_list), len(bs_list), years)
    if n == 0:
        raise ValueError("PLまたはBSに有効なデータが存在しません")

    total_interest_expense = 0.0
    total_debt = 0.0
    count = 0

    for pl, bs in zip(pl_list[-n:], bs_list[-n:]):
        interest_expense = pl.get("interest_expense")
        short_term_debt = bs.get("short_term_debt")
        long_term_debt = bs.get("long_term_debt")

        # データが完全に揃っている年度のみ集計
        if (
            interest_expense is not None and
            short_term_debt is not None and
            long_term_debt is not None and
            (short_term_debt + long_term_debt) > 0
        ):
            total_interest_expense += interest_expense
            total_debt += short_term_debt + long_term_debt
            count += 1

    if count == 0 or total_debt == 0:
        raise ValueError("直近の有効な有利子負債データが存在しません")

    return total_interest_expense / total_debt


def compute_wacc(cost_of_equity, cost_of_debt, bs_list, nopat_list, years=5):
    """
    株主資本コスト、負債コスト、BSとNOPATからWACCを計算する。

    Parameters:
        cost_of_equity (float): 株主資本コスト（例：0.106）
        cost_of_debt (float): 負債コスト（例：0.038）
        bs_list (List[dict]): 整形済みBSデータ（昇順ソート）
        nopat_list (List[dict]): NOPATデータ（昇順ソート）
        years (int): 実効税率の平均計算に使う年数（デフォルト5）

    Returns:
        float: 加重平均資本コスト（WACC、小数）
    """
    # 最新のBSから資本構成を取得
    latest_bs = bs_list[-1]
    equity = latest_bs.get("total_equity", 0.0)
    short_term_debt = latest_bs.get("short_term_debt", 0.0)
    long_term_debt = latest_bs.get("long_term_debt", 0.0)
    debt = short_term_debt + long_term_debt

    if equity + debt == 0:
        raise ValueError("資本構成の合計がゼロです")

    # 直近years年の実効税率平均を計算（有効値のみ）
    valid_tax_rates = [
        x["effective_tax_rate"]
        for x in nopat_list[-years:]
        if x.get("effective_tax_rate") is not None and x["effective_tax_rate"] >= 0
    ]
    if not valid_tax_rates:
        raise ValueError("有効な実効税率データがありません")

    avg_tax_rate = sum(valid_tax_rates) / len(valid_tax_rates)

    # WACC 計算
    total_capital = equity + debt
    wacc = (
        (equity / total_capital) * cost_of_equity +
        (debt / total_capital) * cost_of_debt * (1 - avg_tax_rate)
    )
    return wacc


def infer_cost_of_debt_from_wacc(wacc, cost_of_equity, bs_list, nopat_list, years=5):
    """
    与えられたWACCと株主資本コストから負債コストを逆算する。

    Parameters:
        wacc (float): 加重平均資本コスト（小数、例：0.08）
        cost_of_equity (float): 株主資本コスト（小数、例：0.10）
        bs_list (List[dict]): 整形済みバランスシートデータ（昇順ソート）
        nopat_list (List[dict]): NOPATデータ（昇順ソート）
        years (int): 実効税率の平均に使う年数（デフォルト5）

    Returns:
        float: 負債コスト（小数、例：0.038）
    """
    latest_bs = bs_list[-1]
    equity = latest_bs.get("total_equity", 0.0)
    short_term_debt = latest_bs.get("short_term_debt", 0.0)
    long_term_debt = latest_bs.get("long_term_debt", 0.0)
    debt = short_term_debt + long_term_debt

    if equity + debt == 0:
        raise ValueError("資本構成の合計がゼロです")

    total_capital = equity + debt
    equity_weight = equity / total_capital
    debt_weight = debt / total_capital

    # 実効税率の平均
    valid_tax_rates = [
        x["effective_tax_rate"]
        for x in nopat_list[-years:]
        if x.get("effective_tax_rate") is not None and x["effective_tax_rate"] >= 0
    ]
    if not valid_tax_rates:
        raise ValueError("有効な実効税率データがありません")
    avg_tax_rate = sum(valid_tax_rates) / len(valid_tax_rates)

    # 負債コストの逆算
    numerator = wacc - (equity_weight * cost_of_equity)
    denominator = debt_weight * (1 - avg_tax_rate)

    if denominator == 0:
        raise ZeroDivisionError("負債比率または税率によって除算が不可能です")

    cost_of_debt = numerator / denominator
    return cost_of_debt

