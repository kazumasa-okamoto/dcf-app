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

from src.compute_wacc import compute_cost_of_equity, compute_cost_of_debt_from_pl_bs, compute_wacc

from src.dcf import compute_dcf_valuation, compute_fair_share_price_from_bs, sensitivity_analysis_dcf

from src.visualization import plot_multiple_metrics

st.set_page_config(page_title="財務・DCF分析ダッシュボード", layout="wide")
st.title("📈 財務分析＆DCF評価ダッシュボード")

company_query = st.text_input("企業名またはティッカーを入力してください（例: Apple）")

selected_ticker = None

if company_query:
    search_results = search_ticker_by_name(company_query)

    if search_results:
        # 企業名とティッカーのリストを作成
        display_options = [f"{item['symbol']} - {item['name']}" for item in search_results]
        selected_option = st.selectbox("検索結果から選択してください：", display_options)

        # ティッカーを抽出
        if selected_option:
            selected_ticker = selected_option.split(" - ")[0]  # 例: "AAPL - Apple Inc." → "AAPL"
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
            st.session_state.ticker_cache = ticker
            st.session_state.pl_list = pl_list
            st.session_state.bs_list = bs_list
            st.session_state.returns_list = returns_list
            st.session_state.market_data_raw = market_data_raw

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
        st.dataframe(df_combined[["revenue", "operating_income", "nopat"]])

        # ROIC・利益率など
        st.subheader("収益性・効率性") 
        plot_multiple_metrics(
            df_combined,
            ["roic", "pre_tax_roic", "operating_margin", "sg_and_a_ratio"]
        )
        st.dataframe(df_combined[["roic", "pre_tax_roic", "operating_margin", "sg_and_a_ratio"]])

        # 投下資本回転日数
        st.subheader("資本効率")
        plot_multiple_metrics(
            df_combined,
            ["nwc_days", "ppe_days", "intangible_days"]
        )
        st.dataframe(df_combined[["nwc_days", "ppe_days", "intangible_days"]])

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
                    "🛠 PPE弾力性（売上高成長率に対する）", 
                    min_value=0.0, max_value=2.0, value=0.3, step=0.05, key=f"ppe_coef_{idx}"
                    )

                intangible_growth_coef = st.slider(
                    "🧠 無形固定資産弾力性（売上高成長率に対する）", 
                    min_value=0.0, max_value=2.0, value=0.3, step=0.05, key=f"intangible_coef_{idx}"
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

                    st.subheader("📄 予測BS（貸借対照表）")
                    st.dataframe(to_dataframe(extended_bs_list).round(0).T)

                    st.subheader("📄 予測CF（キャッシュフロー計算書）")
                    st.dataframe(to_dataframe(extended_cf_list).round(0).T)

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
                input_risk_free_rate = st.number_input(
                    "無リスク利子率（%）", 0.0, 10.0, 4.0, 0.1, key=f"rfr_{idx}"
                ) / 100
                input_market_risk_premium = st.number_input(
                    "市場リスクプレミアム（%）", 0.0, 10.0, 5.5, 0.1, key=f"mrp_{idx}"
                ) / 100
                growth = st.number_input(
                    "永久成長率（%）", value=2.0, step=0.1, key=f"growth_{idx}"
                ) / 100

                market_data = reconstruct_market_data(
                    market_data_raw,
                    risk_free_rate=input_risk_free_rate,
                    market_risk_premium=input_market_risk_premium
                )

                cost_of_equity = compute_cost_of_equity(market_data)
                cost_of_debt = compute_cost_of_debt_from_pl_bs(pl_list, bs_list)
                wacc = compute_wacc(cost_of_equity, cost_of_debt, bs_list, nopat_list)

                input_wacc = st.number_input(
                    "加重平均資本コスト（WACC, %）", 
                    value=wacc * 100,  # 初期値を%で表示
                    step=0.1, 
                    key=f"wacc_{idx}"
                ) / 100

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
                st.metric("理論株価", f"${result['fair_share_price']:.2f} USD")
                st.metric("現在株価", f"${result['current_market_price']:.2f} USD")

                with st.expander("詳細"):
                    st.write("**株主資本コスト:**", f"{cost_of_equity:.2%}")
                    st.write("**負債コスト:**", f"{cost_of_debt:.2%}")
                    st.write("**WACC:**", f"{input_wacc:.2%}")
                    st.write("**β:**", f"{market_data['beta']:.2f}")
                    st.write("**無リスク利子率:**", f"{market_data['risk_free_rate']:.2%}")
                    st.write("**市場リスクプレミアム:**", f"{market_data['market_risk_premium']:.2%}")

        # ===== 棒グラフで比較 =====
        st.subheader("📊 シナリオ別：企業価値 & 理論株価 比較")

        # 有効なシナリオのみ集計
        valid_results = [res for res in summary_results if res is not None]

        sns.set_theme(style="whitegrid")

        if valid_results:
            labels = [res["scenario"] for res in valid_results]
            enterprise_values = [res["enterprise_value"] / 1e9 for res in valid_results]
            fair_prices = [res["fair_share_price"] for res in valid_results]
            market_prices = [res["current_market_price"] for res in valid_results]

            df_ev = pd.DataFrame({
                "Scenario": labels,
                "Enterprise Value (B USD)": enterprise_values
            })

            fig1, ax1 = plt.subplots(figsize=(10, 5))
            sns.barplot(x="Scenario", y="Enterprise Value (B USD)", data=df_ev, ax=ax1, palette="Blues_d")
            ax1.set_title("Enterprise Value by Scenario", fontsize=14)
            ax1.set_ylabel("Enterprise Value (Billion USD)", fontsize=12)
            ax1.set_xlabel("")
            ax1.tick_params(axis='x', rotation=15)
            st.pyplot(fig1)

            df_prices = pd.DataFrame({
                "Scenario": labels * 2,
                "Price (USD)": fair_prices + market_prices,
                "Type": ["Fair Value"] * len(labels) + ["Market Price"] * len(labels)
            })

            fig2, ax2 = plt.subplots(figsize=(10, 5))
            sns.barplot(
                data=df_prices,
                x="Scenario",
                y="Price (USD)",
                hue="Type",
                palette="Set2",
                ax=ax2
            )
            ax2.set_title("Fair Value vs Market Price per Share", fontsize=14)
            ax2.set_ylabel("Price (USD)", fontsize=12)
            ax2.set_xlabel("")
            ax2.tick_params(axis='x', rotation=15)
            ax2.legend(title="")
            st.pyplot(fig2)

        else:
            st.info("Insufficient scenario results. Comparison charts are not available.")

        # ===== Sensitivity Heatmaps =====
        st.subheader("📈 シナリオ別 感応度分析（WACC × 永久成長率）")

        for res in valid_results:
            st.markdown(f"#### {res['scenario']}")

            with st.spinner("Running sensitivity analysis..."):
                matrix, wacc_list, g_list = sensitivity_analysis_dcf(
                    cf_list=res["cf_list"],
                    base_wacc=res["wacc"],
                    base_growth=res["growth"],
                    wacc_range=(-0.01, 0.01),
                    growth_range=(-0.005, 0.005),
                    wacc_steps=5,
                    growth_steps=5
                )

            heatmap_df = pd.DataFrame(
                matrix / 1e9,
                index=[f"{w*100:.2f}%" for w in wacc_list],
                columns=[f"{g*100:.2f}%" for g in g_list]
            )

            fig, ax = plt.subplots(figsize=(9, 6))
            sns.heatmap(
                heatmap_df,
                annot=True,
                fmt=".1f",
                cmap="YlGnBu",
                ax=ax,
                annot_kws={"size": 10},
                linewidths=0.5,
                cbar_kws={'label': 'Enterprise Value (B USD)'}
            )
            ax.set_xlabel("Perpetual Growth Rate (g)", fontsize=12)
            ax.set_ylabel("WACC", fontsize=12)
            ax.set_title(f"Sensitivity Heatmap: {res['scenario']}", fontsize=14)
            st.pyplot(fig)