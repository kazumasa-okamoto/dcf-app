import streamlit as st
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd

from src.data_fetchers import  search_ticker_by_name, fetch_income_statement, fetch_balance_sheet, fetch_cash_flow, fetch_market_data

from src.utils import to_dataframe, average_growth

from src.financial_utils import(
    reconstruct_income_statement,
    reconstruct_balance_sheet,
    extract_returns_from_cf,
    compute_nopat_from_pl,
    compute_nwc_from_bs,
    compute_invested_capital_from_bs,
    compute_financial_ratios_from_pl_bs_nopat_nwc_ic,
    reconstruct_market_data
)

from src.financial_forcasting import(
    forecast_pl_from_growth,
    forecast_bs_from_pl,
    forecast_cf_from_pl_bs_nopat_nwc,
)

from src.compute_wacc import compute_cost_of_equity, compute_cost_of_debt_from_pl_bs, compute_wacc, infer_cost_of_debt_from_wacc

from src.dcf import compute_dcf_valuation, compute_fair_share_price_from_bs

from src.visualization import plot_multiple_metrics, plot_dcf_comparison_charts, plot_dcf_sensitivity_heatmaps

st.set_page_config(page_title="財務・DCF分析ダッシュボード", layout="wide")
st.title("📈 財務分析＆DCF分析ダッシュボード")

company_query = st.text_input("企業名またはティッカーを入力してください（例: Apple）")

selected_ticker = None

if company_query:
    search_results = search_ticker_by_name(company_query)

    if "search_cache" not in st.session_state or st.session_state.search_cache.get("query") != company_query:
        # 企業名とティッカーのリストを作成
        search_results = search_ticker_by_name(company_query)
        st.session_state.search_cache = {"query": company_query, "results": search_results}
    else:
        search_results = st.session_state.search_cache["results"]
    
    if search_results:
        display_options = [f"{item['symbol']} - {item['name']}" for item in search_results]
        selected_option = st.selectbox("検索結果から選択してください：", display_options)
        # ティッカーを抽出
        if selected_option:
            selected_ticker = selected_option.split(" - ")[0]
    else:
        st.warning("企業が見つかりませんでした。別のキーワードでお試しください。")

if selected_ticker:
    st.success(f"選択されたティッカー: {selected_ticker}")
    ticker = selected_ticker 
    if "ticker_cache" not in st.session_state or st.session_state.ticker_cache != ticker:
        with st.spinner("データを取得しています..."):
            # データ取得と処理
            income_raw = fetch_income_statement(ticker)
            balance_raw = fetch_balance_sheet(ticker)
            cf_raw = fetch_cash_flow(ticker)
            market_data_raw = fetch_market_data(ticker)

            pl_list = reconstruct_income_statement(income_raw)
            bs_list = reconstruct_balance_sheet(balance_raw)
            returns_list = extract_returns_from_cf(cf_raw)

            # セッションに保存
            st.session_state.update({
                "ticker_cache": ticker,
                "income_raw": income_raw,
                "balance_raw": balance_raw,
                "cf_raw": cf_raw,
                "market_data_raw": market_data_raw,
                "pl_list": pl_list,
                "bs_list": bs_list,
                "returns_list": returns_list
            })

    # セッションから読み込み
    pl_list = st.session_state.pl_list
    bs_list = st.session_state.bs_list
    returns_list = st.session_state.returns_list
    market_data_raw = st.session_state.market_data_raw

    nopat_list = compute_nopat_from_pl(pl_list)
    nwc_list = compute_nwc_from_bs(bs_list)
    ic_list = compute_invested_capital_from_bs(bs_list)
    ratios_list = compute_financial_ratios_from_pl_bs_nopat_nwc_ic(pl_list, bs_list, nopat_list, nwc_list, ic_list)

    df_pl = to_dataframe(pl_list)
    df_bs = to_dataframe(bs_list)
    df_nopat = to_dataframe(nopat_list)
    df_nwc = to_dataframe(nwc_list)
    df_ic = to_dataframe(ic_list)
    df_ratios = to_dataframe(ratios_list)

    df_combined = df_pl \
        .join(df_bs, how="outer", rsuffix="_bs") \
        .join(df_nopat, how="outer", rsuffix="_nopat") \
        .join(df_nwc, how="outer", rsuffix="_nwc") \
        .join(df_ic, how="outer", rsuffix="_ic") \
        .join(df_ratios, how="outer", rsuffix="_ratios")

    df_combined.sort_index(inplace=True)

    # ---- タブ構成 ----  
    tab_fin, tab_forecast, tab_dcf = st.tabs(["📊 過去財務分析","📈 予測財務諸表", "💰 DCF分析"])

    with tab_fin:
        st.header("📊 過去の財務指標と推移")

        # 個別財務諸表の表示（転置）
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📄 PL（損益計算書）")
            df_pl_display = to_dataframe(pl_list).T
            st.dataframe(df_pl_display)
            
            st.subheader("📄 NOPAT")
            df_nopat_display = to_dataframe(nopat_list).T
            st.dataframe(df_nopat_display)
        
        with col2:
            st.subheader("📄 BS（貸借対照表）")
            df_bs_display = to_dataframe(bs_list).T
            st.dataframe(df_bs_display)
            
            st.subheader("📄 NWC（運転資本）")
            df_nwc_display = to_dataframe(nwc_list).T
            st.dataframe(df_nwc_display)

        st.markdown("---")

        # 売上・営業利益・NOPAT
        st.subheader("基本項目")
        plot_multiple_metrics(df_combined, ["revenue", "operating_income", "nopat"])
        print(df_combined[["revenue", "operating_income", "nopat"]].dropna(how="all"))
        st.dataframe(df_combined[["revenue", "operating_income", "nopat"]].T)

        # ROIC・利益率など
        st.subheader("収益性・効率性") 
        plot_multiple_metrics(
            df_combined,
            ["roic", "pre_tax_roic", "operating_margin", "sg_and_a_ratio"]
        )
        st.dataframe(df_combined[["roic", "pre_tax_roic", "operating_margin", "sg_and_a_ratio"]].T)

        # 投下資本回転日数
        st.subheader("資本効率")
        plot_multiple_metrics(
            df_combined,
            ["nwc_days", "ppe_days", "intangible_days"]
        )
        st.dataframe(df_combined[["nwc_days", "ppe_days", "intangible_days"]].T)

    with tab_forecast:
        st.header("📈 財務諸表予測（シナリオ別）")

        base_growth = average_growth(pl_list, "revenue") 
        scenario_growth_multipliers = [0.75, 1.0, 1.25]  # Downside / Normal / Upside
        decay_factor = 0.95  # 年ごとの減衰率

        tabs = st.tabs(["シナリオ 1（Downside）", "シナリオ 2（Normal）", "シナリオ 3（Upside）"])

        for idx, tab in enumerate(tabs):
            with tab:
                st.markdown(f"#### シナリオ {idx + 1}: 売上高成長率（%）を10年分入力")

                # 係数の入力スライダー
                ppe_growth_coef = st.slider(
                    "🛠 有形固定資産弾力性（売上高成長率に対する）", 
                    min_value=0.0, max_value=2.0, value=0.5, step=0.05, key=f"ppe_coef_{idx}"
                    )

                intangible_growth_coef = st.slider(
                    "🧠 無形固定資産弾力性（売上高成長率に対する）", 
                    min_value=0.0, max_value=2.0, value=0.5, step=0.05, key=f"intangible_coef_{idx}"
                )

                # 年ごとに減衰させた初期値リストを生成
                default_growth_rates = [
                    round(base_growth * scenario_growth_multipliers[idx] * (decay_factor ** i) * 100, 2)
                    for i in range(10)
                ]

                cols = st.columns(10)
                growth_rate_list = []
                input_valid = True

                for i in range(10):
                    with cols[i]:
                        rate_input = st.text_input(
                            f"{i+1}年目", 
                            str(default_growth_rates[i]), 
                            key=f"growth_{idx}_{i}"
                        )
                        try:
                            rate = float(rate_input) / 100
                            growth_rate_list.append(rate)
                        except ValueError:
                            growth_rate_list.append(None)
                            input_valid = False

                if not input_valid:
                    st.error("すべての成長率を数値（%）で正しく入力してください")
                elif all(rate is None or rate == 0 for rate in growth_rate_list):
                    st.warning("最低1年分の成長率を入力してください")
                else:
                    cleaned_growth_rates = [r for r in growth_rate_list if r is not None][:10]

                    extended_pl_list = forecast_pl_from_growth(pl_list, cleaned_growth_rates)
                    extended_bs_list = forecast_bs_from_pl(
                        extended_pl_list, pl_list, bs_list, returns_list,
                        ppe_growth_coef=ppe_growth_coef, intangible_growth_coef=intangible_growth_coef
                    )
                    extended_nopat_list = compute_nopat_from_pl(extended_pl_list)
                    extended_nwc_list = compute_nwc_from_bs(extended_bs_list)
                    extended_cf_list = forecast_cf_from_pl_bs_nopat_nwc(
                        extended_pl_list, extended_bs_list, extended_nopat_list, extended_nwc_list
                    )

                    st.session_state[f"cf_list_{idx}"] = extended_cf_list

                    st.subheader("📄 予測PL（損益計算書）")
                    st.dataframe(to_dataframe(extended_pl_list).round(0).T)

                    with st.expander("📘 損益計算書の詳細（予測ロジック）"):
                        st.markdown("""
                    ### 📘 予測PLの作成方法

                    この損益計算書（PL）は、**売上高成長率に基づいて将来のPLを予測**し、既存のPLリストに追加したものです。

                    #### 🧮 各項目の予測方法

                    - **売上高**：指定された成長率に従って予測
                    - **売上原価**：直近5年の売上高比率で一定
                    - **販管費（SG&A）**：直近5年の売上高比率で一定
                    - **減価償却費**：直近5年の平均成長率で一定成長
                    - **営業利益**：上記の差額から算出
                    - **受取利息・支払利息・その他営業外損益**：直近5年の平均値で一定
                    - **税引前利益**：営業利益＋営業外損益
                    - **法人税等**：直近5年の「法人税 / 税引前利益」の比率を適用
                    - **親会社株主に属する当期純利益**：税引前利益 − 法人税等
                    
                        """)

                    st.subheader("📄 予測BS（貸借対照表）")
                    st.dataframe(to_dataframe(extended_bs_list).round(0).T)

                    with st.expander("📙 貸借対照表の詳細（予測ロジック）"):
                        st.markdown("""
                    ### 📙 予測BSの作成方法

                    この貸借対照表（BS）は、**将来のPL予測に基づいて拡張**されたものです。

                    #### 🧮 各項目の予測方法

                    - **現金・預金**：残差として調整（他項目との差額）
                    - **有価証券**：一定と仮定
                    - **売上債権 / 棚卸資産**：売上高比率の5年平均を適用
                    - **有形固定資産 / 無形固定資産**：売上高成長率 × 各係数で増加
                    - **その他固定資産**：一定と仮定
                    - **資産合計**：上記項目の合計

                    - **短期有利子負債 / 長期有利子負債**：一定と仮定
                    - **仕入債務 / その他流動負債**：売上高比率の5年平均を適用
                    - **繰延収益 / その他固定負債**：一定
                    - **負債合計**：上記の合計

                    - **資本金**：変動なし
                    - **自己株式**：過去5年の自社株買い比率の平均から計算
                    - **資本剰余金**：過去5年の配当性向の平均から計算
                    - **その他包括利益累計額**：0と仮定

                        """)

                    st.subheader("📄 予測CF（キャッシュフロー計算書）")
                    st.dataframe(to_dataframe(extended_cf_list).round(0).T)

                    with st.expander("📗 キャッシュフロー計算書の詳細（予測ロジック）"):
                        st.markdown("""
                    ### 📗 予測CFの作成方法

                    このキャッシュフロー計算書（CF）は、**将来予測されたPL・BS・NOPAT・NWC** に基づいて構成されています。

                    #### 🧮 各項目の算出方法

                    - **NOPAT（税引後営業利益）**：PLに基づいて計算
                    - **減価償却費**：PL上の減価償却費をそのまま使用
                    - **正味運転資本の増減（ΔNWC）**：当年と前年のNWCの差分
                    - **営業活動によるCF**：NOPAT + 減価償却費 - ΔNWC
                    - **投資活動によるCF**：有形固定資産・無形固定資産の増減
                    - **FCF（フリーキャッシュフロー）**：営業CF + 投資CF

                        """)

    with tab_dcf:
        st.header("💰 DCF分析結果（シナリオ比較）")

        cols = st.columns(3)

        # 結果を格納するリスト
        summary_results = []

        for idx, col in enumerate(cols):
            with col:
                st.markdown(f"### シナリオ {idx + 1}")

                cf_key = f"cf_list_{idx}"
                if cf_key not in st.session_state:
                    st.warning(f"シナリオ {idx+1} の予測が未入力です。")
                    summary_results.append(None)
                    continue

                cf_list = st.session_state[cf_key]

                # 入力
                rfr = st.number_input(
                    "無リスク利子率（%）", 0.0, 10.0, 4.0, 0.1, key=f"rfr_{idx}"
                ) / 100
                mrp = st.number_input(
                    "市場リスクプレミアム（%）", 0.0, 10.0, 5.5, 0.1, key=f"mrp_{idx}"
                ) / 100
                growth = st.number_input(
                    "永久成長率（%）", value=2.0, step=0.1, key=f"growth_{idx}"
                ) / 100

                market_key = (rfr, mrp)
                if "market_data_cache" not in st.session_state:
                    st.session_state.market_data_cache = {}
                if market_key in st.session_state.market_data_cache:
                    market_data = st.session_state.market_data_cache[market_key]
                else:
                    market_data = reconstruct_market_data(market_data_raw, risk_free_rate=rfr, market_risk_premium=mrp)
                    st.session_state.market_data_cache[market_key] = market_data

                cost_key = (st.session_state.ticker_cache, rfr, mrp)
                if "cost_cache" not in st.session_state:
                    st.session_state.cost_cache = {}
                if cost_key in st.session_state.cost_cache:
                    ce, cd, wacc = st.session_state.cost_cache[cost_key]
                else:
                    ce = compute_cost_of_equity(market_data)
                    cd = compute_cost_of_debt_from_pl_bs(pl_list, bs_list)
                    wacc = compute_wacc(ce, cd, bs_list, nopat_list)
                    st.session_state.cost_cache[cost_key] = (ce, cd, wacc)

                input_wacc = st.number_input(
                    "加重平均資本コスト（WACC, %）", 
                    value=wacc * 100,  # 初期値を%で表示
                    step=0.1, 
                    key=f"wacc_{idx}"
                ) / 100

                if abs(input_wacc - wacc) > 1e-6:
                    cd = infer_cost_of_debt_from_wacc(input_wacc, ce, bs_list, nopat_list)

                enterprise_value = compute_dcf_valuation(cf_list, input_wacc, growth)
                result = compute_fair_share_price_from_bs(enterprise_value, bs_list, market_data)

                # 表示用に格納
                summary_results.append({
                    "scenario": f"Senario{idx+1}",
                    "enterprise_value": result["enterprise_value"],
                    "fair_share_price": result["fair_share_price"],
                    "current_market_price": result["current_market_price"],
                    "wacc": input_wacc,
                    "growth": growth,
                    "cf_list": cf_list
                })

                # メトリクス表示
                st.metric("企業価値", f"${result['enterprise_value']:,.0f}")
                st.metric("ネットデット", f"${result['net_debt']:,.0f}")
                st.metric("株主価値", f"${result['equity_value']:,.0f}")
                st.metric("発行済み株式数", f"{result['shares_outstanding']:,.0f}")
                st.metric("理論株価", f"${result['fair_share_price']:.2f} USD")
                st.metric("現在株価", f"${result['current_market_price']:.2f} USD")

                with st.expander("詳細"):
                    st.write("**株主資本コスト:**", f"{ce:.2%}")
                    st.write("**負債コスト:**", f"{cd:.2%}")
                    st.write("**WACC:**", f"{input_wacc:.2%}")
                    st.write("**β:**", f"{market_data['beta']:.2f}")
                    st.write("**無リスク利子率:**", f"{market_data['risk_free_rate']:.2%}")
                    st.write("**市場リスクプレミアム:**", f"{market_data['market_risk_premium']:.2%}")
        
        # 有効なシナリオのみ集計
        valid_results = [res for res in summary_results if res is not None]

        # 棒グラフで比較
        st.subheader("📊 シナリオ別：企業価値 & 理論株価 比較")

        plot_dcf_comparison_charts(valid_results)

        # 感応度分析
        st.subheader("📈 シナリオ別 感応度分析（WACC × 永久成長率）")

        plot_dcf_sensitivity_heatmaps(valid_results)

