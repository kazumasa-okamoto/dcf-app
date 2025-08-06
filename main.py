import streamlit as st
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd

from src.data_fetchers import fetch_income_statement, fetch_balance_sheet, fetch_cash_flow, fetch_market_data

from src.utils import to_dataframe

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

ticker = st.text_input("ティッカーを入力してください（例: AAPL）")

if ticker:
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
        st.header("📈 財務諸表予測（売上高成長率入力）")

        st.markdown("#### 売上高成長率を10年分入力してください（%単位）")

        cols = st.columns(10)
        growth_rate_list = []
        input_valid = True

        for i in range(10):
            with cols[i]:
                rate_input = st.text_input(f"{i+1}年目", "5", key=f"growth_{i}")
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
            # 空欄（None）は除外（後ろの空欄だけを対象）
            cleaned_growth_rates = [r for r in growth_rate_list if r is not None][:10]

            extended_pl_list =  forecast_pl_from_growth(pl_list, cleaned_growth_rates)
            extended_bs_list = forecast_bs_from_pl(extended_pl_list, pl_list, bs_list, returns_list)

            extended_nopat_list = compute_nopat_from_pl(extended_pl_list)
            extended_nwc_list = compute_nwc_from_bs(extended_bs_list)
            extended_cf_list = forecast_cf_from_pl_bs_nopat_nwc(extended_pl_list, extended_bs_list, extended_nopat_list, extended_nwc_list, returns_list)

            # DataFrame化して表示
            df_ext_pl = to_dataframe(extended_pl_list).round(0).T
            df_ext_bs = to_dataframe(extended_bs_list).round(0).T
            df_ext_cf = to_dataframe(extended_cf_list).round(0).T

            st.subheader("📄 予測PL（損益計算書）")
            st.dataframe(df_ext_pl)

            st.subheader("📄 予測BS（貸借対照表）")
            st.dataframe(df_ext_bs)

            st.subheader("📄 予測CF（キャッシュフロー計算書）")
            st.dataframe(df_ext_cf)

    with tab_dcf:
        st.header("💰 DCF分析結果")

        if 'extended_cf_list' not in locals():
            st.warning("先に予測財務諸表を入力してDCF分析を実行してください。")
        else:
            # Step 1: ユーザー入力
            st.subheader("📥 入力: 金融市場パラメータ")
            input_risk_free_rate = st.number_input("無リスク利子率（%）", min_value=0.0, max_value=10.0, value=4.0, step=0.1) / 100
            input_market_risk_premium = st.number_input("市場リスクプレミアム（%）", min_value=0.0, max_value=10.0, value=5.5, step=0.1) / 100

            # Step 2: Market Data 構成
            market_data = reconstruct_market_data(
                market_data_raw,
                risk_free_rate=input_risk_free_rate,
                market_risk_premium=input_market_risk_premium
            )

            # Step 3: 永久成長率入力
            default_growth = 0.02
            growth = st.number_input("永久成長率（%）", value=default_growth * 100.0, step=0.1) / 100

            # Step 4: コスト計算とDCF
            cost_of_equity = compute_cost_of_equity(market_data)
            cost_of_debt = compute_cost_of_debt_from_pl_bs(pl_list, bs_list)
            wacc = compute_wacc(cost_of_equity, cost_of_debt, bs_list, nopat_list)

            # Step 5: DCFバリュエーション
            enterprise_value = compute_dcf_valuation(extended_cf_list, wacc, growth)
            result = compute_fair_share_price_from_bs(enterprise_value, bs_list, market_data)

            # Step 6: 結果表示
            st.subheader("📊 DCF評価結果")
            st.metric("企業価値 (EV)", f"${result['enterprise_value']:,.0f}")
            st.metric("ネットデット", f"${result['net_debt']:,.0f}")
            st.metric("株主価値 (Equity Value)", f"${result['equity_value']:,.0f}")
            st.metric("理論株価", f"${result['fair_share_price']:.2f} USD")
            st.metric("現在株価", f"${result['current_market_price']:.2f} USD")

            with st.expander("🔍 詳細（WACC構成要素）"):
                st.write("**株主資本コスト**:", f"{cost_of_equity:.2%}")
                st.write("**負債コスト**:", f"{cost_of_debt:.2%}")
                st.write("**WACC**:", f"{wacc:.2%}")
                st.write("**β（ベータ）**:", f"{market_data['beta']:.2f}")
                st.write("**無リスク利子率**:", f"{market_data['risk_free_rate']:.2%}")
                st.write("**市場リスクプレミアム**:", f"{market_data['market_risk_premium']:.2%}")
            
            # Step 7: 感応度分析
            st.subheader("📈 感応度分析（WACC × 永久成長率）")

            with st.spinner("感応度分析を実行中..."):
                matrix, wacc_list, g_list = sensitivity_analysis_dcf(
                    cf_list=extended_cf_list,
                    base_wacc=wacc,
                    base_growth=growth,
                    wacc_range=(-0.01, 0.01),
                    growth_range=(-0.005, 0.005),
                    wacc_steps=5,
                    growth_steps=5
                )

            # ヒートマップを描画（英語表記 & フォーマット調整）
            heatmap_df = pd.DataFrame(
                matrix / 1e9,  # 単位を10億USD（billion）に変換
                index=[f"{w*100:.2f}%" for w in wacc_list],
                columns=[f"{g*100:.2f}%" for g in g_list]
            )

            fig, ax = plt.subplots(figsize=(10, 6))  # 図のサイズを拡大
            sns.heatmap(
                heatmap_df,
                annot=True,
                fmt=".1f",  # 小数1桁表示
                cmap="YlGnBu",
                ax=ax,
                annot_kws={"size": 10}  # 数字のフォントサイズ
            )

            ax.set_xlabel("Perpetual Growth Rate (g)", fontsize=12)
            ax.set_ylabel("WACC", fontsize=12)
            ax.set_title("Sensitivity of Enterprise Value (in Billion USD)", fontsize=14)
            ax.tick_params(labelsize=10)

            st.pyplot(fig)