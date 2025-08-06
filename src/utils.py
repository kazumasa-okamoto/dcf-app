import pandas as pd
import numpy as np

# 財務諸表のリストをDataFlameに変換
def to_dataframe(statement_list):
    df = pd.DataFrame(statement_list)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)
        df.sort_index(inplace=True)
    return df


# 0除算防止
def safe_divide(a, b):
    return a / b if b else 0


# 平均の比率を計算する関数
def average_ratio(data_list, numerator_key, denominator_key, denominator_reference_list=None):
    if denominator_reference_list is None:
        denominator_reference_list = data_list

    values = []
    for i in range(min(len(data_list), len(denominator_reference_list))):
        numerator = data_list[i].get(numerator_key, 0)
        denominator = denominator_reference_list[i].get(denominator_key, 1)
        if denominator:
            values.append(safe_divide(numerator, denominator))

    return np.mean(values) if values else 0


# 平均の値を計算する関数
def average_value(data_list, key):
    values = [x.get(key) for x in data_list if x.get(key) is not None]
    return np.mean(values) if values else 0


# 平均の成長率を計算する関数
def average_growth(data_list, key):
    vals = [x.get(key) for x in sorted(data_list, key=lambda x: x["date"])]
    vals = [v for v in vals if v is not None]
    growths = [
        safe_divide(vals[i + 1] - vals[i], vals[i])
        for i in range(len(vals) - 1) if vals[i] != 0
    ]
    return np.mean(growths) if growths else 0


# 平均の配当性向を計算する関数
def average_dividend_ratio(pl_list, returns_list):
    values = [
        safe_divide(r.get("dividends_paid", 0), p.get("net_income", 1))
        for r, p in zip(returns_list, pl_list)
        if r.get("dividends_paid") is not None and p.get("net_income")
    ]
    return np.mean(values) if values else 0


# 平均の自社株買い比率を計算する関数
def average_buyback_ratio(pl_list, returns_list):
    values = [
        safe_divide(r.get("stock_buyback", 0), p.get("net_income", 1))
        for r, p in zip(returns_list, pl_list)
        if r.get("stock_buyback") is not None and p.get("net_income")
    ]
    return np.mean(values) if values else 0

