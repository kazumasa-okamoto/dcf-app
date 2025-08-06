import numpy as np
from copy import deepcopy
from datetime import datetime
from src.utils import (safe_divide, average_ratio, average_value, average_growth,
                       average_dividend_ratio, average_buyback_ratio,)
from src.financial_utils import compute_nopat_from_pl, compute_nwc_from_bs

def forecast_pl_from_growth(pl_list, growth_rates):
    """
    売上高成長率に基づいて将来のPLを予測し、PLリストに追加する。

     Parameters:
        pl_list (List[dict]): 過去のPL
        growth_rates (List[float]): 売上高成長率のリスト

    Returns:
        List[dict]: 予測PLを追加した新たなPLリスト

    売上高以外の項目は、直近5年の売上比や平均値から算出。
    - 売上原価：直近5年の売上高比で一定
    - 販管費および一般簡易日：直近5年の売上高比で一定
    - 減価償却費：直近5年の平均成長率で一定成長
    - 営業利益：以上から算出
    - 受取利息：直近5年平均で一定
    - 支払利息：直近5年平均で一定
    - その他営業外損益：直近5年平均で一定
    - 税金等調整前当期純利益：以上から算出
    - 法人税等：直近5年の法人税/ 税引き前利益の比率で一定
    - 親会社株主に属する当期純利益：以上から算出

    """
    # 直近5年
    recent_pl = pl_list[-5:]
    extended_pl_list = deepcopy(pl_list)
    base = extended_pl_list[-1]  # 最新年
    base_date = datetime.strptime(base["date"], "%Y-%m-%d")

    # 過去の平均比率・平均値
    cost_ratio = average_ratio(recent_pl, "cost_of_revenue", "revenue")
    sga_ratio = average_ratio(recent_pl, "sg_and_a", "revenue")
    depreciation_growth = average_growth(recent_pl, "depreciation_amortization")
    interest_income_avg = average_value(recent_pl, "interest_income")
    interest_expense_avg = average_value(recent_pl, "interest_expense")
    other_non_op_avg = average_value(recent_pl, "other_non_operating")
    tax_rate = average_ratio(recent_pl, "income_tax", "income_before_tax")

    # 初期値
    current_revenue = base["revenue"]
    current_depreciation = base.get("depreciation_amortization", 0)

    for i, growth in enumerate(growth_rates, start=1):
        current_revenue *= (1 + growth)
        current_depreciation *= (1 + depreciation_growth)
        forecast_date = base_date.replace(year=base_date.year + i)
        forecast_date_str = forecast_date.strftime("%Y-%m-%d")

        cost_of_revenue = current_revenue * cost_ratio
        sg_and_a = current_revenue * sga_ratio
        operating_income = current_revenue - cost_of_revenue - sg_and_a - current_depreciation
        income_before_tax = operating_income + interest_income_avg - interest_expense_avg + other_non_op_avg
        income_tax = income_before_tax * tax_rate
        net_income = income_before_tax - income_tax

        forecast_entry = {
            "date": forecast_date_str,
            "revenue": current_revenue,
            "cost_of_revenue": cost_of_revenue,
            "sg_and_a": sg_and_a,
            "depreciation_amortization": current_depreciation,
            "operating_income": operating_income,
            "interest_income": interest_income_avg,
            "interest_expense": interest_expense_avg,
            "other_non_operating": other_non_op_avg,
            "income_before_tax": income_before_tax,
            "income_tax": income_tax,
            "net_income": net_income,
        }

        extended_pl_list.append(forecast_entry)

    return extended_pl_list


def forecast_bs_from_pl(extended_pl_list, pl_list, bs_list, returns_list):
    """
    将来のPL予測に基づいてBS（バランスシート）を拡張する。

    Parameters:
        extended_pl_list (List[dict]): 予測を含むPL（新しい年度を含む）
        pl_list (List[dict]): 実績ベースのPL（平均算出に用いる）
        bs_list (List[dict]): 実績ベースのBS
        returns_list (List[dict]): 各年度の配当金や自社株買い情報

    Returns:
        List[dict]: 拡張されたBS（extend_bs_list）

    BSの各項目は次のようにして算出
    - 現金預金：残額計算
    - 有価証券；一定
    - 売上債権：直近5年の売上高比の平均で一定
    - 棚卸資産：直近5年の売上高比の平均で一定
    - 有形固定資産：直近5年の平均成長率で一定成長
    - 無形固定資産：直近5年の平均成長率で一定成長
    - その他固定資産：一定
    - 資産合計：以上の和
    - 短期有利子負債：一定
    - 仕入れ債務：直近5年の売上高比の平均で一定
    - 繰延収益：一定
    - その他流動負債：直近5年の売上高比の平均で一定
    - 長期有利子負債：一定
    - その他固定負債；一定
    - 負債合計：以上の和
    - 資本金 変動なし
    - 自己株式：直近5年の自社株買い比率の平均から計算
    - 資本剰余金：直近5年の配当性向の平均から計算
    - その他包括利益累計額：0と仮定
    """
    # 直近5年
    recent_pl = pl_list[-5:]
    recent_bs = bs_list[-5:]
    latest_bs = recent_bs[-1]

    # 固定値・比率・成長率など
    short_term_investments = latest_bs["short_term_investments"]
    other_current_assets = latest_bs["other_current_assets"]
    long_term_investments = latest_bs["long_term_investments"]
    other_noncurrent_assets = latest_bs["other_noncurrent_assets"]
    short_term_debt = latest_bs["short_term_debt"]
    deferred_revenue = latest_bs["deferred_revenue"]
    long_term_debt = latest_bs["long_term_debt"]
    other_noncurrent_liabilities = latest_bs["other_noncurrent_liabilities"]
    common_stock = latest_bs["common_stock"]
    aoci = 0

    net_receivables_ratio = average_ratio(recent_bs, "net_receivables", "revenue", recent_pl)
    inventory_ratio = average_ratio(recent_bs, "inventory", "revenue", recent_pl)
    accounts_payable_ratio = average_ratio(recent_bs, "accounts_payable", "revenue", recent_pl)
    other_current_liabilities_ratio = average_ratio(recent_bs, "other_current_liabilities", "revenue", recent_pl)

    ppe_growth = average_growth(recent_bs, "ppe")
    intangible_growth = average_growth(recent_bs, "intangible_assets")
    dividend_ratio = average_dividend_ratio(recent_pl, returns_list)
    buyback_ratio = average_buyback_ratio(recent_pl, returns_list)

    extended_bs_list = deepcopy(bs_list)
    base_bs = bs_list[-1]
    base_date = datetime.strptime(base_bs["date"], "%Y-%m-%d")

    for i, pl in enumerate(extended_pl_list):
        if pl["date"] <= base_bs["date"]:
            continue  # すでに存在するBSより前のPLは無視

        revenue = pl.get("revenue", 0)
        net_income = pl.get("net_income", 0)
        prev_bs = extended_bs_list[-1]  # 直前のBS
        date_obj = datetime.strptime(prev_bs["date"], "%Y-%m-%d")
        date = date_obj.replace(year=date_obj.year + 1).strftime("%Y-%m-%d")

        # 資産項目
        net_receivables = revenue * net_receivables_ratio
        inventory = revenue * inventory_ratio
        accounts_payable = revenue * accounts_payable_ratio
        other_current_liabilities = revenue * other_current_liabilities_ratio
        ppe = prev_bs["ppe"] * (1 + ppe_growth)
        intangible_assets = prev_bs["intangible_assets"] * (1 + intangible_growth)

        # 純資産項目
        distributed_ratio = min(dividend_ratio + buyback_ratio, 1.0)
        retained_earnings = (prev_bs.get("retained_earnings") or 0.0) + net_income * (1 - distributed_ratio)

        non_cash_assets = (
            short_term_investments + net_receivables + inventory +
            other_current_assets + ppe + intangible_assets +
            long_term_investments + other_noncurrent_assets
        )
        total_liabilities = (
            short_term_debt + accounts_payable + other_current_liabilities +
            deferred_revenue + long_term_debt + other_noncurrent_liabilities
        )
        total_equity = common_stock + retained_earnings + aoci
        cash = total_liabilities + total_equity - non_cash_assets
        total_assets = non_cash_assets + cash

        forecast_bs = {
            "date": date,
            "cash_and_equivalents": cash,
            "short_term_investments": short_term_investments,
            "net_receivables": net_receivables,
            "inventory": inventory,
            "other_current_assets": other_current_assets,
            "long_term_investments": long_term_investments,
            "ppe": ppe,
            "intangible_assets": intangible_assets,
            "other_noncurrent_assets": other_noncurrent_assets,
            "total_assets": total_assets,
            "short_term_debt": short_term_debt,
            "accounts_payable": accounts_payable,
            "other_current_liabilities": other_current_liabilities,
            "deferred_revenue": deferred_revenue,
            "long_term_debt": long_term_debt,
            "other_noncurrent_liabilities": other_noncurrent_liabilities,
            "total_liabilities": total_liabilities,
            "common_stock": common_stock,
            "retained_earnings": retained_earnings,
            "aoci": aoci,
            "total_equity": total_equity,
        }

        extended_bs_list.append(forecast_bs)

    return extended_bs_list


def forecast_cf_from_pl_bs_nopat_nwc(extended_pl_list, extended_bs_list, extended_nopat_list, extended_nwc_list, returns_list):
    """
    将来予測されたPL・BS・NOPAT・NWCに基づき、フリー・キャッシュ・フロー（FCF）および関連するキャッシュフロー項目を算出する。
    ※ 本関数では、現金の増減（delta_cash）と整合するようにCAPEXを逆算するアプローチを取る。

    Parameters:
        extended_pl_list (List[dict]): 将来予測を含むPLリスト
        extended_bs_list (List[dict]): 将来予測を含むBSリスト
        extended_nopat_list (List[dict]): 将来予測を含むNOPATリスト（税引後営業利益）
        extended_nwc_list (List[dict]): 将来予測を含む正味運転資本（NWC）リスト
        returns_list (List[dict]): 配当金・自社株買いの実績データ

    Returns:
        List[dict]: 各年度ごとのキャッシュフロー構成項目とFCFを含むリスト

    各キャッシュフロー項目の算出方法：
    - NOPAT：税引後営業利益
    - 減価償却費：PLの "減価償却費"
    - 正味運転資本の増減（delta_nwc）：NWCの差分
    - 営業活動によるCF：NOPAT + 減価償却費 - delta_nwc
    - 投資活動によるCF：capex（逆算） + 無形資産投資 + 有価証券の変化
    - FCF（フリーキャッシュフロー）：営業CF + 投資CF
    - 非営業損益（税引後）：営業外損益 × (1 - 税率)
    - 財務CF：借入増減 - 配当 - 自社株買い
    - Net CF：営業 + 投資 + 財務 + 非営業
    - ΔCash：BSの現金増減（cash_t - cash_t-1）
    - capex は上記全体整合性から逆算
    """
    recent_returns = returns_list[-5:]
    recent_pl = extended_pl_list[-5:]
    dividend_ratio = average_dividend_ratio(recent_pl, recent_returns)
    buyback_ratio = average_buyback_ratio(recent_pl, recent_returns)

    extended_cf_list = []

    for i in range(len(extended_pl_list)):
        pl = extended_pl_list[i]
        bs = extended_bs_list[i]
        nopat_data = extended_nopat_list[i]
        nwc_data = extended_nwc_list[i]
        date = pl["date"]

        nopat = nopat_data.get("nopat", 0)
        depreciation = pl.get("depreciation_amortization", 0)

        # ΔNWC
        delta_nwc = 0
        if i > 0:
            delta_nwc = nwc_data["nwc"] - extended_nwc_list[i - 1]["nwc"]

        # 営業CF
        ocf = nopat + depreciation - delta_nwc

        # 投資CF項目（capexは後で逆算）
        intangible_investment = 0
        short_term_investment_change = 0
        long_term_investment_change = 0

        if i > 0:
            intangible_investment = bs["intangible_assets"] - extended_bs_list[i - 1]["intangible_assets"]
            short_term_investment_change = bs["short_term_investments"] - extended_bs_list[i - 1]["short_term_investments"]
            long_term_investment_change = bs["long_term_investments"] - extended_bs_list[i - 1]["long_term_investments"]

        # 非営業損益（税引後）
        interest_income = pl.get("interest_income", 0)
        interest_expense = pl.get("interest_expense", 0)
        other_non_operating = pl.get("other_non_operating", 0)
        effective_tax_rate = nopat_data.get("effective_tax_rate", 0)

        non_operating_cf = (
            interest_income * (1 - effective_tax_rate)
            - interest_expense * (1 - effective_tax_rate)
            + other_non_operating * (1 - effective_tax_rate)
        )

        # 有利子負債の増減
        delta_debt = 0
        if i > 0:
            prev_bs = extended_bs_list[i - 1]
            current_total_debt = bs.get("short_term_debt", 0) + bs.get("long_term_debt", 0)
            prev_total_debt = prev_bs.get("short_term_debt", 0) + prev_bs.get("long_term_debt", 0)
            delta_debt = current_total_debt - prev_total_debt

        # 配当・自社株買い
        if i == 0:
            dividends = buybacks = 0
        elif i < len(returns_list):
            dividends = returns_list[i].get("dividends_paid", 0)
            buybacks = returns_list[i].get("stock_buyback", 0)
        else:
            prev_net_income = extended_pl_list[i - 1].get("net_income", 0)
            dividends = prev_net_income * dividend_ratio
            buybacks = prev_net_income * buyback_ratio

        fcf_financing = delta_debt - (dividends + buybacks)

        # ΔCash（現金増減）
        delta_cash = 0
        if i > 0:
            delta_cash = bs["cash_and_equivalents"] - extended_bs_list[i - 1]["cash_and_equivalents"]

        # capexを逆算
        if i > 0:
            capex = -(
                delta_cash
                - ocf
                - fcf_financing
                - non_operating_cf
                + intangible_investment
                + short_term_investment_change
                + long_term_investment_change
            )
        else:
            capex = 0

        # 投資CF（capexを含む）
        icf = -capex - intangible_investment - short_term_investment_change - long_term_investment_change

        # FCF
        fcf = ocf + icf

        # Net CF（理論上 delta_cash に一致する）
        total_net_cf = ocf + icf + non_operating_cf + fcf_financing

        extended_cf_list.append({
            "date": date,
            "nopat": nopat,
            "depreciation": depreciation,
            "delta_nwc": delta_nwc,
            "operating_cf": ocf,
            "capex": capex,
            "intangible_investment": intangible_investment,
            "short_term_investment_change": short_term_investment_change,
            "long_term_investment_change": long_term_investment_change,
            "investing_cf": icf,
            "fcf": fcf,
            "non_operating_cf": non_operating_cf,
            "delta_debt": delta_debt,
            "dividends": dividends,
            "buybacks": buybacks,
            "financing_cf": fcf_financing,
            "net_cf": total_net_cf,
            "delta_cash": delta_cash,
            "cash_discrepancy": delta_cash - total_net_cf
        })

    return extended_cf_list

