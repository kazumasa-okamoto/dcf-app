import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns

def plot_multiple_metrics(df_statement, metrics, title=None):
    """
    複数の指標を1つのグラフにプロットし、Streamlitに表示する関数。

    Parameters:
        df_statement (pd.DataFrame): インデックスに日付を持つ財務データのDataFrame
        metrics (List[str]): プロットしたい複数の指標名
        title (str, optional): グラフのタイトル

    Returns:
        None（Streamlitにグラフを表示）
    """
     # seabornスタイルを有効化
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
