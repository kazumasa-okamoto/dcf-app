# FMPのincome-statementデータから主要PL項目を抽出してリストで返す
def reconstruct_income_statement(income_statement_data):
    pl_list = []

    for year_data in income_statement_data:
        pl = {
            "date": year_data.get("date"),
            "revenue": year_data.get("revenue"),
            "cost_of_revenue": year_data.get("costOfRevenue"),
            "sg_and_a": year_data.get("sellingGeneralAndAdministrativeExpenses"),
            "depreciation_amortization": year_data.get("depreciationAndAmortization"),
            "operating_income": year_data.get("operatingIncome"),
            "interest_income": year_data.get("interestIncome"),
            "interest_expense": year_data.get("interestExpense"),
            "other_non_operating": year_data.get("totalOtherIncomeExpensesNet"),
            "income_before_tax": year_data.get("incomeBeforeTax"),
            "income_tax": year_data.get("incomeTaxExpense"),
            "net_income": year_data.get("netIncome"),
        }
        pl_list.append(pl)
    pl_list = sorted(pl_list, key=lambda x: x["date"])
    return pl_list


# FMPのbalance-sheet-statementデータから主要BS項目を抽出してリストで返す
def reconstruct_balance_sheet(balance_sheet_data):
    bs_list = []

    for year_data in balance_sheet_data:
        bs = {
            "date": year_data.get("date"),
            "cash_and_equivalents": year_data.get("cashAndCashEquivalents"),
            "short_term_investments": year_data.get("shortTermInvestments"),
            "net_receivables": year_data.get("netReceivables"),
            "inventory": year_data.get("inventory"),
            "other_current_assets": year_data.get("otherCurrentAssets"),
            "ppe": year_data.get("propertyPlantEquipmentNet"),
            "long_term_investments": year_data.get("longTermInvestments"),
            "intangible_assets": year_data.get("intangibleAssets"),
            "other_noncurrent_assets": year_data.get("otherNonCurrentAssets"),
            "total_assets": year_data.get("totalAssets"),
            "short_term_debt": year_data.get("shortTermDebt"),
            "accounts_payable": year_data.get("accountPayables"),
            "deferred_revenue": year_data.get("deferredRevenue"),
            "other_current_liabilities": year_data.get("otherCurrentLiabilities"),
            "long_term_debt": year_data.get("longTermDebt"),
            "other_noncurrent_liabilities": year_data.get("otherNonCurrentLiabilities"),
            "total_liabilities": year_data.get("totalLiabilities"),
            "common_stock": year_data.get("commonStock"),
            "retained_earnings": year_data.get("retainedEarnings"),
            "aoci" :year_data.get("accumulatedOtherComprehensiveIncomeLoss"),
            "capital_surplus": 0.0,
            "total_equity": year_data.get("totalStockholdersEquity"),
        }
        bs_list.append(bs)
    
    bs_list = sorted(bs_list, key=lambda x: x["date"])
    return bs_list

## FMPのcashflow-satatebentデータから配当と自社株買いの情報を抽出する
def extract_returns_from_cf(cashflow_data):
    returns_list = []

    for item in cashflow_data:
        returns_list.append({
            "date": item.get("date"),
            "dividends_paid": abs(item.get("dividendsPaid")),
            "stock_buyback": abs(item.get("commonStockRepurchased"))
        })

    returns_list = sorted(returns_list, key=lambda x: x["date"])
    return returns_list


#  再構成済みPLのリストからNOPATを計算してリストで返す
def compute_nopat_from_pl(pl_list):
    nopat_list = []

    for year_data in pl_list:
        revenue = year_data.get("revenue")
        operating_income = year_data.get("operating_income")
        income_tax = year_data.get("income_tax")
        income_before_tax = year_data.get("income_before_tax")

        interest_income = year_data.get("interest_income")
        interest_expense = year_data.get("interest_expense")
        other_non_operating = year_data.get("other_non_operating")

        # 実効税率（effective tax rate）
        effective_tax_rate = income_tax / income_before_tax

        # 営業利益にかかる税金
        tax_on_operating_income = (
            income_tax
            - effective_tax_rate * interest_income
            + effective_tax_rate * interest_expense
            - effective_tax_rate * other_non_operating
        )

        # NOPAT = 営業利益 - 税金
        nopat = operating_income - tax_on_operating_income

        nopat_list.append({
            "date": year_data.get("date"),
            "revenue": revenue,
            "operating_income": operating_income,
            "income_tax": income_tax,
            "effective_tax_rate": effective_tax_rate,
            "tax_on_operating_income": tax_on_operating_income,
            "nopat": nopat
        })

    nopat_list = sorted(nopat_list, key=lambda x: x["date"])
    return nopat_list


# 再構成済みのBSのリストから正味運転資本（Net Working Capital, NWC）を計算してリストで返す
def compute_nwc_from_bs(bs_list):
    nwc_list = []

    for year_data in bs_list:
        date = year_data.get("date")
        net_receivables = year_data.get("net_receivables")               # 売上債権
        inventory = year_data.get("inventory")                            # 棚卸資産
        other_current_assets = year_data.get("other_current_assets")     # その他流動資産
        accounts_payable = year_data.get("accounts_payable")
        deferred_revenue = year_data.get("deferred_revenue")
        other_current_liabilities = year_data.get("other_current_liabilities")  # その他流動負債

        nwc = (
            net_receivables +
            inventory +
            other_current_assets -
            accounts_payable -
            deferred_revenue -
            other_current_liabilities
        )

        nwc_list.append({
            "date": date,
            "net_receivables": net_receivables,
            "inventory": inventory,
            "other_current_assets": other_current_assets,
            "accounts_payable": accounts_payable,
            "deferred_revenue": deferred_revenue,
            "other_current_liabilities": other_current_liabilities,
            "nwc": nwc
        })

    nwc_list = sorted(nwc_list, key=lambda x: x["date"])
    return nwc_list


# 再構成済みのBSのリストから投下資本（Incested Capital, IC）を計算してリストで返す
def compute_invested_capital_from_bs(bs_list):
    ic_list = []

    for bs in bs_list:
        date = bs.get("date")
        short_term_debt = bs.get("short_term_debt", 0)         # 短期有利子負債
        long_term_debt = bs.get("long_term_debt", 0)           # 長期有利子負債
        total_equity = bs.get("total_equity", 0)               # 純資産（株主資本）

        invested_capital = short_term_debt + long_term_debt + total_equity

        ic_list.append({
            "date": date,
            "short_term_debt": short_term_debt,
            "long_term_debt": long_term_debt,
            "total_equity": total_equity,
            "invested_capital": invested_capital
        })

    ic_list = sorted(ic_list, key=lambda x: x["date"])
    return ic_list


# 各種財務諸表を算出してリストで返す
def compute_financial_ratios_from_pl_bs_nopat_nwc_ic(pl_list, bs_list, nopat_list, nwc_list, ic_list):
    ratios_list = []

    for pl, bs, nopat, nwc, ic in zip(pl_list, bs_list, nopat_list,  nwc_list, ic_list):
        date = pl.get("date")
        revenue = pl.get("revenue")
        operating_income = pl.get("operating_income")
        nopat= nopat.get("nopat")
        net_income = pl.get("net_income")

        cost_of_revenue = pl.get("cost_of_revenue")
        sg_and_a = pl.get("sg_and_a")

        total_assets = bs.get("total_assets")
        total_equity = bs.get("total_equity")

        invested_capital = ic.get("invested_capital")
        nwc = nwc.get("nwc")
        ppe = bs.get("ppe")
        intangible_assets = bs.get("intangible_assets")

        # その他投下資本 = 投下資本 - （正味運転資本 + 有形固定資産 + 無形固定資産）
        other_invested_capital = invested_capital - (nwc + ppe + intangible_assets)

        ratios = {
            "date": date,
            "pre_tax_roic": operating_income / invested_capital,
            "roic": nopat / invested_capital,
            "roe": net_income / total_equity,
            "roa": net_income / total_assets,
            "operating_margin": operating_income / revenue,
            "cost_ratio": cost_of_revenue / revenue,
            "sg_and_a_ratio": sg_and_a / revenue,
            "capital_turnover": revenue / invested_capital,
            "nwc_days": 365 * nwc / revenue,
            "ppe_days": 365 * ppe / revenue,
            "intangible_days": 365 * intangible_assets / revenue,
            "other_capital_days": 365 * other_invested_capital / revenue,
        }

        ratios_list.append(ratios)

    ratios_list = sorted(ratios_list, key=lambda x: x["date"])
    return ratios_list


def reconstruct_market_data(profile_data, risk_free_rate, market_risk_premium):
    item = profile_data[0]

    price = float(item.get("price"))
    beta = float(item.get("beta"))
    market_cap = float(item.get("mktCap"))

    # 発行済株式数 = 時価総額 ÷ 株価
    shares_outstanding = market_cap / price

    return {
        "price": price,
        "beta": beta,
        "risk_free_rate": risk_free_rate,
        "market_risk_premium": market_risk_premium,
        "shares_outstanding": shares_outstanding
    }