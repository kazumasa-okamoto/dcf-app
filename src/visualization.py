import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from src.dcf import sensitivity_analysis_dcf

# 複数の指標を1つのグラフにプロットして表示
def plot_multiple_metrics(df_statement, metrics, title=None):
    sns.set_theme(style="whitegrid", palette="muted", font_scale=1.1)

    # プロット対象のDataFrameを整形
    df = df_statement.copy()
    df = df[metrics].dropna(axis=0, how='all')  # 全てNaNの行は削除
    df["Date"] = df.index

    # meltで長い形式に変換（Seaborn向け）
    df_melted = df.melt(id_vars="Date", var_name="Metric", value_name="Value")

    # プロット
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.lineplot(data=df_melted, x="Date", y="Value", hue="Metric", marker="o", ax=ax)

    # ラベル・タイトルの設定
    ax.set_title(title or "Financial Metrics", fontsize=14, weight="bold")
    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Value", fontsize=12)
    ax.legend(title="Metric", loc="best")
    fig.tight_layout()

    st.pyplot(fig)


# 企業価値・理論株価のシナリオ別比較グラフを表示
def plot_dcf_comparison_charts(valid_results):
    sns.set_theme(style="whitegrid")

    if not valid_results:
        st.info("Insufficient scenario results. Comparison charts are not available.")
        return

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


# シナリオ別のDCF感応度分析ヒートマップを表示
def plot_dcf_sensitivity_heatmaps(valid_results):
    sns.set_theme(style="whitegrid")

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

