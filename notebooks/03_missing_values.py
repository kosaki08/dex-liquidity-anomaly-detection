# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.17.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# ## 目的
#
# - Uniswap v3 サブグラフの TVL が負値や欠損値を含む原因を把握し、データ品質改善策を検討する。
#
# ## 仮説
#
# 1. TVL の負値・欠損は特定の時間帯（例：深夜帯）やイベント（Collect／Mint の未処理）に集中している。
# 2. 欠損日の分布は API サーバーのダウンタイムやオンチェーンイベント頻度に対応している。
# 3. プール属性（手数料帯・トークンペア）ごとに欠損・負値発生率に差がある。
#

# %%
# パッケージをインストール
# %pip install -qe ..

# %%
import duckdb
import japanize_matplotlib  # noqa: F401
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from itertools import combinations
from statsmodels.tsa.seasonal import STL
from scipy.stats import chisquare, chi2_contingency

# %% [markdown]
# ## 基本設定
#

# %%
plt.style.use("ggplot")

# %%
with duckdb.connect("../data/raw/etl_from_sf.duckdb", read_only=True) as con:
    df = con.execute("SELECT * FROM raw_clean_with_pool").df()
df.head()


# %%
raw_clean_with_pool = df

# %%
df.shape[0]


# %%
df[["token0_symbol", "token1_symbol"]].drop_duplicates().shape[0]


# %%
(df["tvl_usd"] < 0).mean()


# %% [markdown]
# ### データ概要サマリー
#
# | 指標               | 値                                          |
# | ------------------ | ------------------------------------------- |
# | 総行数             | 134736 行                                   |
# | 期間               | 2025-03-04 22:00:00 〜 2025-05-10 05:00:00` |
# | ユニークプール数   | 4115 件                                     |
# | トークンペア数     | 3526 種類                                   |
# | 欠損率 (`tvl_usd`) | 0                                           |
# | 負値率 (`tvl_usd`) | 2.2265764161026006e-05                      |
#
# **結論**
#
# - データは **約 13.5 万行**、**2025-03-04 22:00 〜 2025-05-10 05:00** の約 2 ヶ月分
# - プールは **4,115 件**、トークンペアは **3,526 種類**
# - TVL の **欠損率 0%**、**負値率 約 0.00223%**（約 3 件／全 134,736 行、モデル学習前に要対応）
#

# %% [markdown]
# ## 基本的なデータ変換
#

# %%
# タイムスタンプを日時に変換
raw_clean_with_pool["datetime"] = pd.to_datetime(raw_clean_with_pool["hour_ts"], unit="s")

# %%
# IDからプールアドレスとインデックスを抽出
raw_clean_with_pool["pool_address"] = raw_clean_with_pool["id"].str.split("-").str[0]
raw_clean_with_pool["block_index"] = raw_clean_with_pool["id"].str.split("-").str[1]

# %%
# fee tier ごとのプール数
fee_tier_counts = raw_clean_with_pool["fee_tier"].value_counts().reset_index()
fee_tier_counts.columns = ["fee_tier", "count"]
fee_tier_counts

# %% [markdown]
# ## プールごとのデータについて調査
#

# %%
raw_clean_with_pool.head()

# %%
# すべてのプール（負値を持つプールも持たないプールも含む）をリストアップ
all_pools = raw_clean_with_pool["pool_address"].unique()
print(f"プールの総数: {len(all_pools)}")

# 各プールごとの統計情報
all_pool_stats = (
    raw_clean_with_pool.groupby("pool_address")
    .agg(
        {
            "tvl_usd": [
                ("データ件数", "count"),
                ("負値件数", lambda x: (x < 0).sum()),
                ("負値割合", lambda x: (x < 0).sum() / len(x) if len(x) > 0 else 0),
                ("最小値", "min"),
                ("最大値", "max"),
                ("平均値", "mean"),
            ]
        }
    )
    .reset_index()
)

# 多階層カラムをフラット化
all_pool_stats.columns = ["_".join(col).strip("_") for col in all_pool_stats.columns.values]

# 負値割合でソート
sorted_pools = all_pool_stats.sort_values("tvl_usd_負値割合", ascending=False)

# %%
print("負値を持つプール（負値割合が高い順）:")
sorted_pools[sorted_pools["tvl_usd_負値割合"] > 0].tail(20)
sorted_pools[sorted_pools["tvl_usd_負値割合"] > 0].describe()

# %%
print("負値がないプール最初の10件:")
sorted_pools[sorted_pools["tvl_usd_負値割合"] == 0]

# %%
# 負値プールと非負値プールの数を確認
negative_pools = sorted_pools[sorted_pools["tvl_usd_負値割合"] > 0]
valid_pools = sorted_pools[sorted_pools["tvl_usd_負値割合"] == 0]
print(f"負値を持つプール数: {len(negative_pools)} ({len(negative_pools) / len(all_pools):.2%})")
print(f"負値のないプール数: {len(valid_pools)} ({len(valid_pools) / len(all_pools):.2%})")

# %%
# 上位TVLプールと負値プールの関係を確認
tvl_sorted = all_pool_stats.sort_values("tvl_usd_平均値", ascending=False)
print("TVL上位プール:")
tvl_sorted.head(10)[["pool_address", "tvl_usd_データ件数", "tvl_usd_負値件数", "tvl_usd_負値割合", "tvl_usd_平均値"]]

# %%
# 負値の分析
negative_tvl = raw_clean_with_pool[raw_clean_with_pool["tvl_usd"] < 0]
print(f"負のTVL値の件数: {len(negative_tvl)}")
print(f"負のTVL値を持つユニークなプールID: {negative_tvl['pool_address'].nunique()}")

# %%
# UTC 時刻を JST に変換
negative_tvl.loc[:, "hour_utc"] = pd.to_datetime(negative_tvl["hour_ts"], unit="s").dt.hour
negative_tvl.loc[:, "hour_jst"] = (negative_tvl["hour_utc"] + 9) % 24

# JST 時間帯ごとの頻度集計とプロット
hourly_pattern_jst = negative_tvl.groupby("hour_jst").size()
plt.figure(figsize=(10, 4))
hourly_pattern_jst.plot(kind="bar")
plt.title("日本時間での負値の発生時間帯分布")
plt.xlabel("時間帯（日本時間）")
plt.ylabel("負値の頻度")
plt.show()


# %% [markdown]
# ### 統計検定（カイ2乗適合度）: 負 TVL が時間帯に偏るか
#
# - 帰無仮説 H₀ : 「負 TVL は 24 時間均等に発生する」
# - 有意水準 α = 0.05
#
# #### カイ2乗適合度 (χ²) について
#
# - **用途**：観測度数が「期待度数（ここでは 24 時間均等）」とどれだけズレているかを判定  
# - **前提**：カテゴリ×1 変数・十分なサンプル（期待度数≳5）
# - **選択した理由** 時間帯ごとに **数が多い/少ない** という *度数* の偏りを検証したいため  

# %%
hour_counts = negative_tvl['hour_jst'].value_counts().reindex(range(24), fill_value=0).sort_index()
expected = np.full(24, hour_counts.mean())            # “均等”が帰無仮説
chi2, p = chisquare(hour_counts, f_exp=expected)

print(f'χ² = {chi2:.2f}, p = {p:.4f}')
if p < 0.05:
    print('⇒ 時間帯に有意な偏りあり（帰無仮説棄却）')

# %% [markdown]
# ### 統計検定結果
#
# - 帰無仮説 **H₀** : 「負 TVL は 24 時間均等に発生する」
# - χ² = 21.00（df = 23）, p = 0.581  
#   **⇒ H₀ を棄却できず、時間帯による有意な偏りは確認されませんでした。**
#
# ### 時間帯別ヒストグラムより
#
# - すべて日本標準時 (JST; UTC+9) の時刻です。
# - 視覚上はいくつか山があるものの、χ²検定では **有意な偏りは出ていません**。
# - 観測期間が 2 か月弱でサンプリングとしては粗いものの、日本株・米株市場との直接的関連を示す統計的根拠も現時点ではありません
#
# - **次のステップ**
#   1. 該当時間帯のブロックチェーンイベント／サブグラフログを突合し、Collect/Mint 処理タイミングを確認
#   2. （将来偏りが確認された場合）前処理で該当時間帯にフラグを付与し、モデルの誤検出を抑制
#   3. 市場時間外のバッチ更新タイミングとの相関も合わせて分析
#

# %%
import numpy as np, pandas as pd
from itertools import combinations
from scipy.stats import chi2_contingency

# ---------------------------------------------------------------------
# 1) クロス表 (fee_tier × 負/非負)
# ---------------------------------------------------------------------
tbl = (
    df.assign(is_neg = df["tvl_usd"] < 0)
      .pivot_table(index="fee_tier",
                   values="is_neg",
                   aggfunc=[np.sum, lambda x: (~x).sum()])
)
tbl.columns = ["neg", "valid"]

# ---------------------------------------------------------------------
# 2) カイ2乗検定 & Cramér's V
# ---------------------------------------------------------------------
chi2, p, _, _ = chi2_contingency(tbl[["neg", "valid"]])
n      = tbl.values.sum()
k      = min(tbl.shape)          # 行数 or 列数の小さい方
cramer = np.sqrt(chi2 / (n * (k - 1)))

# ---------------------------------------------------------------------
# 3) Cochran–Armitage trend test (手数料 tier は順序あり)
#    ↓ “重み w” に fee_tier 値そのものを使う標準形
# ---------------------------------------------------------------------
# 行ごとの合計
ni   = tbl.sum(axis=1).values          # n_i
ai   = tbl["neg"].values               # a_i
wi   = tbl.index.astype(float).values  # 重み = 手数料 tier
N    = ni.sum()
m    = ai.sum()

# CA 統計量 (Z)
num  = ((wi - wi.mean()) * (ai - ni * m / N)).sum()
den  = np.sqrt(m * (N - m) * ((ni * (wi - wi.mean())**2).sum()) / (N * (N - 1)))
z_ca = num / den
from scipy.stats import norm
p_ca = 2 * (1 - norm.cdf(abs(z_ca)))   # 両側

# ---------------------------------------------------------------------
# 4) ペアワイズ差：z 検定 + Holm 補正
# ---------------------------------------------------------------------
from statsmodels.stats.proportion import proportions_ztest
from statsmodels.stats.multitest import multipletests

pairs, raw_p = [], []
for a, b in combinations(tbl.index, 2):
    count = np.array([tbl.loc[a,"neg"],   tbl.loc[b,"neg"]])
    nobs  = np.array([tbl.loc[a].sum(),   tbl.loc[b].sum()])
    _, p_pair = proportions_ztest(count, nobs)
    pairs.append(f"{a} vs {b}")
    raw_p.append(p_pair)

adj_p = multipletests(raw_p, method="holm")[1]
pairwise = pd.DataFrame({"pair": pairs, "p_adj(Holm)": adj_p}).sort_values("p_adj(Holm)")

# ---------------------------------------------------------------------
# 5) 結果表示
# ---------------------------------------------------------------------
display(tbl.style.format("{:,.0f}"))
print(f"χ² = {chi2:.2f}, p = {p:.5f}")
print(f"Cramér's V = {cramer:.3f}  ← 0.1=小, 0.3=中, 0.5=大")
print(f"Cochran–Armitage trend: Z = {z_ca:.2f}, p = {p_ca:.5f}")
display(pairwise)


# %%

# %% [markdown]
# ## TVL 負値問題の概要と対応策
#
# Uniswap v3 のサブグラフにおいて、プールごとの TVL（Total Value Locked）が負の値になる既知の不具合です。  
# 主な要因として以下が報告されています。
#
# ---
#
# ### 原因
#
# 1. **Collect イベントの未反映**  
#    流動性プロバイダーが手数料を徴収する際の Collect イベントでのトークン差し引きが正しく処理されず、負の値が発生する。
# 2. **手数料の累積誤差**  
#    サブグラフがスワップ時の手数料（0.01%～ 1%）を TVL に反映しないため、実際の残高との差分が発生し、負値となるケースがある。
# 3. **イベント処理の不整合**  
#    Swap/Mint/Burn などの順序を時系列で再現する際、内部トランザクションがログに記録されず、TVL／流動性が負に“潰れる”。
#
# ---
#
# ### 影響
#
# - 高取引量プール（例：USDC/ETH 0.05%）で報告値が実値の約 2 倍に膨らむ場合があり、データの信頼性が低下する。
# - LP 収益（APR）計算に悪影響を及ぼし、誤った投資判断を誘発する可能性がある。
#
# ---
#
# ### 対応策
#
# #### 1. 暫定対応
#
# 1. **負の TVL → 欠損値化 (NaN)**
#
#    ```python
#    df.loc[df['tvl_usd'] < 0, 'tvl_usd'] = np.nan
#    ```
#
#    - **目的**：計算エラーをモデルに学習させない
#    - **備考**：Mint 起因の一時的マイナスもここで除外
#
# 2. **欠損値の補完 (Imputation)**
#
#    ```python
#    # プールごとの時系列前方・後方補完
#    df['tvl_usd'] = df.groupby('pool_address')['tvl_usd'] \
#                      .apply(lambda s: s.ffill().bfill())
#    ```
#
#    - **目的**：連続性を保ちつつ合理的な値に置き換え
#
# 3. **データ品質フラグの付与**
#
#    ```python
#    df['tvl_error'] = df['tvl_usd'].isna().astype(int)
#    ```
#
#    - **目的**：後続モデルで「どこが補完されたか」を特徴量として利用
#
# ### 今後の改善検討事項
#
# 1. **イベント別エラー切り分け**
#
#    - Mint／Burn／Collect の各イベント原因を識別し、Mint 起因の一時的な負値にはペナルティを与えない
#    - Uncollected Fees や Collect イベントのみをエラー扱いするロジックの実装
#
# 2. **オンチェーン直接取得**
#
#    - Etherscan 等で `balanceOf(poolAddress)` を呼び出して token0/token1 残高を取得
#    - 最も正確な TVL 計算が可能
#
# 3. **代替分析プラットフォームの活用**
#
#    - Dune Analytics の公式ダッシュボードを確認する
#    - Flipside Crypto で独自 SQL を実行
#
# 4. **公式アップデートの注視**
#    - Uniswap Governance フォーラム
#    - The Graph ステータスページ
#
# ### 参考リンク
#
# - [Uniswap v3 サブグラフ Issue #74](https://github.com/Uniswap/v3-subgraph/issues/74)
#

# %% [markdown]
# ## データの欠損値を確認
#

# %%
from datetime import datetime

import pandas as pd

daily = (
    raw_clean_with_pool.assign(date=lambda df: df["datetime"].dt.date).groupby("date")["volume_usd"].sum().reset_index()
)

# 日付を適切に変換
start_date = pd.to_datetime("2025-03-05").date()
end_date = pd.to_datetime("2025-05-05").date()
# 日付のみの欠損をチェック
if isinstance(daily["date"].iloc[0], datetime):
    daily_dates = set(d.date() for d in daily["date"])
else:
    daily_dates = set(daily["date"])
# 期間内のすべての日付を生成
all_dates = pd.date_range(start=start_date, end=end_date).date
missing_dates = [d for d in all_dates if d not in daily_dates]
print("欠損している日付:")
for d in missing_dates:
    print(f"{d}")
# 元データから時間単位の欠損をチェック
print("\n時間単位の詳細:")
# datetimeの一覧を取得（元データから）
if "datetime" in raw_clean_with_pool.columns:
    # ユニークな日時を取得
    unique_timestamps = raw_clean_with_pool["datetime"].sort_values().unique()
    # 期間内のみをフィルタリング
    period_timestamps = [ts for ts in unique_timestamps if start_date <= ts.date() <= end_date]
    # 日付ごとの時間をまとめる
    date_hours = {}
    for ts in period_timestamps:
        date = ts.date()
        hour = ts.hour
        if date not in date_hours:
            date_hours[date] = []
        date_hours[date].append(hour)
    # 各日付の存在する時間を表示（欠損がある場合のみ）
    for date in sorted(date_hours.keys()):
        hours = sorted(date_hours[date])
        missing_hours = [h for h in range(24) if h not in hours]
        # 欠損がある場合のみ表示
        if missing_hours:
            print(f"{date}: データあり: {hours}, 欠損: {missing_hours}")
    # データがまったくない日付を表示
    complete_missing_dates = [d for d in missing_dates if d not in date_hours]
    if complete_missing_dates:
        print("\n完全に欠損している日付:")
        for d in complete_missing_dates:
            print(f"{d}: すべての時間帯でデータなし")
else:
    print("元データに datetime 列がありません")

# %% [markdown]
# ## 時系列特性
#
# 1. 日次／週次トレンド分解（STL 分解）
# 2. 曜日・時間帯ごとの取引量（`volume_usd`）平均プロット
# 3. TVL 負値発生の時間帯ヒートマップ
#

# %%
# 日次で集計
daily = df.set_index("datetime")["volume_usd"].resample("D").sum()
res = STL(daily, period=7).fit()

fig = res.plot()
fig.set_size_inches(15, 6)
plt.tight_layout()
plt.show()


# %% [markdown]
# 図より、
#
# - **トレンド (Trend)**
#
#   - 3 月上旬（≈3×10⁸ USD）をピークに中旬以降は急激に減少し、4 月上旬にはほぼゼロに近い水準。その後は緩やかに持ち直し。
#
# - **季節性 (Seasonal)**
#
#   - 7 日サイクルでの上下動が見られるが、振幅は比較的小さく、取引量全体の変動要因としては限定的。
#
# - **残差 (Resid)**
#   - 3/8–3/10 や 4/22 周辺に大きなスパイク・ドロップが散在。
#   - → 大口スワップやサブグラフのリロードタイミングなど、一過性イベントの影響かもしれません。
#

# %% [markdown]
# ## 流動性
#

# %%
# 基本統計量の確認
print("=== liquidity の基本統計 ===")
print(raw_clean_with_pool["liquidity"].describe())
print("\n=== sqrt_price の基本統計 ===")
print(raw_clean_with_pool["sqrt_price"].describe())

# 値の範囲を確認
print(f"\nliquidity の範囲: {raw_clean_with_pool['liquidity'].min()} から {raw_clean_with_pool['liquidity'].max()}")
print(f"sqrt_price の範囲: {raw_clean_with_pool['sqrt_price'].min()} から {raw_clean_with_pool['sqrt_price'].max()}")

# 科学的表記法でスケールを把握
print(f"\nliquidity の最大値 (科学的表記): {raw_clean_with_pool['liquidity'].max():.2e}")
print(f"sqrt_price の最大値 (科学的表記): {raw_clean_with_pool['sqrt_price'].max():.2e}")


# %% [markdown]
# ## プール属性別分析
#
# - **手数料帯 (`fee_tier`)** ごとの欠損率・負値率
# - **トークンペア** 上位 10 種での異常発生頻度
#

# %%
ft = (
    df.assign(is_na=df["tvl_usd"].isna(), is_neg=df["tvl_usd"] < 0)
    .groupby("fee_tier")[["is_na", "is_neg"]]
    .mean()
    .reset_index()
)
display(ft)

# %% [markdown]
# ### fee_tier と負 TVL の独立性（カイ2乗検定）
#
# - **帰無仮説 H₀** : 「fee_tier と負 TVL 発生有無は独立である（= fee_tier 間で負値率は同じ）」
# - 有意水準 α = 0.05
#
# #### カイ2乗 “独立性” 検定とは
# - **用途** : 2 × k クロス表で 2 つのカテゴリ変数が独立かを判定  
# - **前提** : 各セルの期待度数 ≳ 5  
# - **選択理由** : fee_tier (5 水準) × 負/非負 (2 水準) の度数表で **発生率の差** を検証したいため
#

# %%
tbl = (
    df.assign(is_neg=df['tvl_usd'] < 0)
      .pivot_table(index='fee_tier', values='is_neg',
                   aggfunc=[lambda x: (~x).sum(), 'sum'])
)
tbl.columns = ['valid', 'neg']
chi2, p, _, _ = chi2_contingency(tbl[['neg', 'valid']])

print(f'χ² = {chi2:.2f}, p = {p:.4g}')

# %% [markdown]
# - **欠損値（`is_na`）**：いずれの `fee_tier` でも発生していない（すべて 0.0）
# - **負値率（`is_neg`）**：
#   - 最も高いのは **fee_tier = 500**（0.0177%）
#   - 次いで **fee_tier = 3000**（0.0017%）
#   - 手数料帯が大きくなるほど負値発生率はほぼ 0 に近づく傾向
# - **示唆**：  
#   低い手数料（0.05%）のプールほど TVL の「負値」イベントが起きやすい可能性があるため、  
#   モデル学習時にはこの属性を特徴量として入れるか、  
#   あるいは該当プールだけ別処理（補完／フラグ付与）を検討したいと考えています
#

# %%

# クロス表作成
tbl = (
    df.assign(is_neg = df["tvl_usd"] < 0)
      .pivot_table(index="fee_tier",
                   values="is_neg",
                   aggfunc=[np.sum, lambda x: (~x).sum()])
)
tbl.columns = ["neg", "valid"]

# --- χ² 検定 ---
chi2, p, _, _ = chi2_contingency(tbl[["neg", "valid"]])

# --- 効果量：Cramér’s V ---
n      = tbl.values.sum()
k      = min(tbl.shape)          # 行数 or 列数の小さい方
cramer = np.sqrt(chi2 / (n * (k - 1)))

# --- Cochran-Armitage trend test ---
trend_stat, trend_p = Table2xK(tbl[["neg", "valid"]].values).cochran_armitage()

# --- ペアワイズ (Tukey 風 Holm 補正) ---
pairs, raw_p = [], []
for a, b in combinations(tbl.index, 2):
    count = np.array([tbl.loc[a,"neg"],   tbl.loc[b,"neg"]])
    nobs  = np.array([tbl.loc[a].sum(),   tbl.loc[b].sum()])
    _, p_pair = proportions_ztest(count, nobs)
    pairs.append(f"{a} vs {b}")
    raw_p.append(p_pair)

adj_p = multipletests(raw_p, method="holm")[1]
pairwise = pd.DataFrame({"pair": pairs, "p_adj(Holm)": adj_p}).sort_values("p_adj(Holm)")

display(tbl.style.format("{:,.0f}"))
print(f"χ² = {chi2:.2f}, p = {p:.5f}")
print(f"Cramér's V = {cramer:.3f}  ← 0.1=小, 0.3=中, 0.5=大")
print(f"Cochran-Armitage trend: Z = {trend_stat:.2f}, p = {trend_p:.5f}")
display(pairwise)

# %%

# %% [markdown]
# ## 巨大固定小数点整数について
#

# %% [markdown]
# ### 桁数の分布を確認
#

# %%
df["liquidity_digits"] = df["liquidity"].astype(str).str.len()
df["sqrt_price_digits"] = df["sqrt_price"].astype(str).str.len()

plt.figure(figsize=(15, 6))

plt.subplot(1, 2, 1)
plt.hist(df["liquidity_digits"], bins=range(min(df["liquidity_digits"]), max(df["liquidity_digits"]) + 2))
plt.title("liquidity の桁数分布")
plt.xlabel("桁数")
plt.ylabel("頻度")

plt.subplot(1, 2, 2)
plt.hist(df["sqrt_price_digits"], bins=range(min(df["sqrt_price_digits"]), max(df["sqrt_price_digits"]) + 2))
plt.title("sqrt_price の桁数分布")
plt.xlabel("桁数")
plt.ylabel("頻度")

plt.tight_layout()
plt.show()


# %% [markdown]
# ### スケーリング係数の選定
#
# - DeFi のスマートコントラクトの慣例からスケーリング係数を推定します。
# - 多くの ERC20 トークンでは 10^18 がスケーリング係数（1 Ether = 10^18 Wei）を使用しているため、これを推定スケーリング係数の候補に追加します。
#
# #### スケーリング係数候補について
#
# - **1e6 (10⁶)**
#   - USDC や USDT のような「小数点以下 6 桁」精度のトークンに対応
# - **1e12 (10¹²)**
#   - 一部トークンが「小数点以下 12 桁」を採用するケースを想定
# - **1e18 (10¹⁸)**
#   - Ether や大多数の ERC-20 トークンが「小数点以下 18 桁」精度で発行
# - **2**⁹⁶
#   - Uniswap v3 の **Q64.96** 固定小数点表現（`sqrt_price` や `tick` 計算）で使用
# - **2**¹²⁸
#   - 固定小数点を格納する最大ビット幅としての上限候補（Ethereum の 256 ビットワードに対してビット幅余裕をみた想定）
#

# %%
# 可能なスケーリング係数のリスト
scaling_factors = [1e6, 1e12, 1e18, 2**96, 2**128]

# 各スケーリング係数でデータを変換したときの統計を確認
for factor in scaling_factors:
    print(f"\n=== スケーリング係数: {factor:.2e} ===")
    print(f"liquidity / {factor:.2e}:")
    print(df["liquidity"].divide(factor).describe())
    print(f"\nsqrt_price / {factor:.2e}:")
    print(df["sqrt_price"].divide(factor).describe())

# %% [markdown]
# 上記より、
#
# | factor                 | liquidity 25% | liquidity 50% | liquidity 75% | sqrt_price 25% | sqrt_price 50% | sqrt_price 75% |
# | ---------------------- | ------------- | ------------- | ------------- | -------------- | -------------- | -------------- |
# | 1e6                    | 3.6e11        | 1.18e15       | 3.26e16       | 7.29e19        | 1.50e21        | 4.50e23        |
# | 1e12                   | 3.6e5         | 1.18e9        | 3.26e10       | 7.29e13        | 1.50e15        | 4.50e17        |
# | **1e18**               | **0.36**      | **1.18e3**    | **3.26e4**    | **7.29e7**     | **1.50e9**     | **4.50e11**    |
# | 2<sup>96</sup> ≈7.9e28 | ≪1            | ≪1            | ≪1            | ≪1             | ≪1             | ≪1             |
# | 2<sup>128</sup>≈3.4e38 | ≪1            | ≪1            | ≪1            | ≪1             | ≪1             | ≪1             |
#
# - **1e6／1e12**
#   - 中央値・四分位が極端に大きく（10⁵ ～ 10¹⁶ 以上）、log スケールでも山が左端に張り付いてしまう。
# - **2⁹⁶／2¹²⁸**
#   - ほとんど全ての値が＜ 1 になりすぎ、分布の情報が失われる。
# - **1e18**
#   - コード内ヒストグラム（log スケール）でも山の位置が程よく中央付近（10⁰ ～ 10⁴ 程度）に現れ、裾も視認可能。
#   - 値が 0–10⁴ ～ 10¹¹ 領域に収まりつつ、ばらつきも十分残るため、
#     - 対数変換／Min–Max 正規化との相性が良い
#     - モデル学習時の数値安定性が高い
#

# %% [markdown]
# #### カーネル密度度推定（KDE）でスケーリング係数 1e18, 1e12 の分布を確認
#
# KDE (Kernel Density Estimation) は、ヒストグラムのようにデータをビンに区切る代わりに、カーネル関数（ガウス関数など）を各データ点に重ね合わせて滑らかな確率密度関数を推定します。
#
# - **メリット**：ビン幅に依存せず、分布の山や裾の形状を直感的に比較できる
# - **用途**：複数のデータセットを重ねて分布の違いを可視化したいときに有効
#

# %%
# 文字列から数値型へ変換
raw_clean_with_pool["liquidity_numeric"] = pd.to_numeric(raw_clean_with_pool["liquidity"], errors="coerce")
raw_clean_with_pool["sqrt_price_numeric"] = pd.to_numeric(raw_clean_with_pool["sqrt_price"], errors="coerce")

# 元データ準備
liq = raw_clean_with_pool["liquidity_numeric"].dropna()
liq = liq[liq > 0]
spr = raw_clean_with_pool["sqrt_price_numeric"].dropna()
spr = spr[spr > 0]

factors = [1e12, 1e18]
colors = ["C0", "C1"]

plt.figure(figsize=(8, 4))
for f, c in zip(factors, colors):
    sns.kdeplot(liq / f, log_scale=True, label=f"{int(f):e}", color=c)
    q1, med, q3 = (liq / f).quantile([0.25, 0.5, 0.75])
    plt.axvline(med, color=c, ls="--")
    plt.text(med, plt.ylim()[1] * 0.8, f"med={med:.1f}", color=c)

plt.title("liquidity の分布比較 (log scale, KDE)")
plt.xlabel("liquidity / factor")
plt.ylabel("density")
plt.legend(title="factor")
plt.tight_layout()
plt.show()


# %% [markdown]
# 上図について、
#
# - **青線 (factor=1e18, 推奨)**：
#   - 中央値はおよそ `1.2×10³`、分布の山も裾も適切に追えるレンジ
#   - モデル学習前の対数変換・正規化との相性が良い
# - **赤線 (factor=1e12)**：
#   - 中央値はおよそ `1.2×10⁹`、非常に大きな値に寄ってしまい、
#   - モデル入力後に他特徴量とのスケール差が目立ちやすい
#
# 1e18 でスケーリングすることで、
#
# - 値のばらつきを十分に残しつつ
# - 入力レンジが適度にコンパクト
#
# #### スケーリング係数の選定
#
# 1e18 のみ「log 軸上で分布山が見やすく」「外れ値の裾も適度に残る」ため、スケーリング係数として `1e18` を採用します。
#

# %% [markdown]
# ### スケーリング後の分布
#

# %%
# 上記よりスケーリング係数を1e18として設定
estimated_factor = 1e18

# %%
from scipy import stats

# スケーリング
raw_clean_with_pool["liquidity_scaled"] = raw_clean_with_pool["liquidity_numeric"] / estimated_factor
raw_clean_with_pool["sqrt_price_scaled"] = raw_clean_with_pool["sqrt_price_numeric"] / estimated_factor

desc = raw_clean_with_pool["liquidity_scaled"].agg(["mean", "median", "std"])
skew, kurt = (
    stats.skew(raw_clean_with_pool["liquidity_scaled"]),
    stats.kurtosis(raw_clean_with_pool["liquidity_scaled"]),
)
summary = {"mean": desc["mean"], "median": desc["median"], "std": desc["std"], "skewness": skew, "kurtosis": kurt}
summary

# %%
qs = raw_clean_with_pool["liquidity_scaled"].quantile([0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99])
qs

# %%
# スケーリング後の分布を確認
plt.figure(figsize=(15, 6))

plt.subplot(1, 2, 1)
plt.hist(raw_clean_with_pool["liquidity_scaled"], bins=50)
plt.title("スケーリング後のliquidity分布")
plt.xlabel("liquidity (スケール済)")
plt.ylabel("頻度")

plt.subplot(1, 2, 2)
plt.hist(raw_clean_with_pool["sqrt_price_scaled"], bins=50)
plt.title("スケーリング後のsqrt_price分布")
plt.xlabel("sqrt_price (スケール済)")
plt.ylabel("頻度")

plt.tight_layout()
plt.show()

# %% [markdown]
# 図より、
#
# - **極端な右裾**
#
#   - `liquidity_scaled` はほとんどの値が 0〜1×10¹⁶ に集中し、ごく一部の巨大な値（外れ値）が分布を引き延ばしている。
#   - `sqrt_price_scaled` も同様に、低スケール領域に集中しつつ、非常に大きな値が存在する。
#
# - **問題点**
#
#   - このままではヒストグラム／モデル両方で外れ値の影響が過大になる。
#   - 分布の偏りが大きいため、線形スケーリングのままでは相対的な違いが見えづらい。
#
# - **次のステップ**
#   1. **対数変換**（`np.log`）を適用し、分布の歪みを緩和する。
#   2. 変換後のヒストグラムで再度分布を確認し、外れ値の影響が抑えられているかを評価する。
#
# #### 対数変換に `np.log` を適用する理由
#
# - **スケール圧縮**
#   - 固定小数点からスケーリングしたあとの値は 10^16 ～ 10^30 といった非常に広いレンジに広がっており、そのままでは外れ値がヒストグラムやモデルを支配してしまいます。
# - **分布の歪度緩和**
#   - 対数を取ることで右に長い裾が縮まり、分布が比較的対称に近づきます。これにより、平均や分散などの統計量が外れ値に強くなり、学習アルゴリズムの安定性が向上します。
# - **乗法的関係の加法的表現**
#   - 多くの金融データでは変化率が本質的な情報なので、対数変換によって「比率変化」を「差分」として扱えるようになり、異常検知やモデルの解釈がしやすくなります。
#
# > ※もしゼロ値が残っている場合は `np.log1p`（`log(1+x)`）を使うことでゼロを安全に扱えますが、今回は事前に小さな正の値でクリップしているため、`np.log` 良いと考えています。
#

# %%
# ヒストグラムで分布を確認（対数スケール）
plt.figure(figsize=(15, 6))

plt.subplot(1, 2, 1)
# null値や負値を除外して対数変換
valid_liquidity = raw_clean_with_pool["liquidity_numeric"].dropna()
valid_liquidity = valid_liquidity[valid_liquidity > 0]
plt.hist(np.log10(valid_liquidity), bins=50)
plt.title("liquidity の分布 (log10スケール)")
plt.xlabel("log10(liquidity)")
plt.ylabel("頻度")

plt.subplot(1, 2, 2)
# null値や負値を除外して対数変換
valid_sqrt_price = raw_clean_with_pool["sqrt_price_numeric"].dropna()
valid_sqrt_price = valid_sqrt_price[valid_sqrt_price > 0]
plt.hist(np.log10(valid_sqrt_price), bins=50)
plt.title("sqrt_price の分布 (log10スケール)")
plt.xlabel("log10(sqrt_price)")
plt.ylabel("頻度")

plt.tight_layout()
plt.show()

# 桁数の分布を確認（文字列長を使用）
raw_clean_with_pool["liquidity_digits"] = raw_clean_with_pool["liquidity"].astype(str).str.len()
raw_clean_with_pool["sqrt_price_digits"] = raw_clean_with_pool["sqrt_price"].astype(str).str.len()

plt.figure(figsize=(15, 6))

plt.subplot(1, 2, 1)
plt.hist(
    raw_clean_with_pool["liquidity_digits"],
    bins=range(min(raw_clean_with_pool["liquidity_digits"]), max(raw_clean_with_pool["liquidity_digits"]) + 2),
)
plt.title("対数変換後の liquidity の桁数分布")
plt.xlabel("桁数")
plt.ylabel("頻度")

plt.subplot(1, 2, 2)
plt.hist(
    raw_clean_with_pool["sqrt_price_digits"],
    bins=range(min(raw_clean_with_pool["sqrt_price_digits"]), max(raw_clean_with_pool["sqrt_price_digits"]) + 2),
)
plt.title("対数変換後の sqrt_price の桁数分布")
plt.xlabel("桁数")
plt.ylabel("頻度")

plt.tight_layout()
plt.show()

# %% [markdown]
# 図より、
#
# - **log10(liquidity)**
#
#   - 主に **15–25** の範囲に分布し、特に **20–22** 付近に二峰性のピークあり
#   - 右裾が長く、大きい値が極端に散在している
#
# - **log10(sqrt_price)**
#
#   - 主に **22–30** の範囲に集中し、小さなモード（≈25）と大きなモード（≈28）が見られる
#   - liquidity 同様、右裾にアウトライヤーあり
#
# - **桁数分布**
#   - `liquidity` は主に **20–23 桁**、
#   - `sqrt_price` は主に **21–23 桁** に集中
#   - 一部 30 桁を超える極端な値も存在
#
# ⇒ いずれも極端に右に裾が長いため、**対数変換**で分布を圧縮し、歪度を緩和するのが有効だと考えています。
#
# ---
#
# 次に下記の手順で実際に対数変換 → 正規化を行います。
#
# 1. **小さな正値 (ε = 1e–10) でクリップ** → 0 以下の値を排除
# 2. `np.log` による対数変換 → `liquidity_log`, `sqrt_price_log`
# 3. Min–Max 正規化 → `[0,1]` 範囲にスケール（`liquidity_norm`, `sqrt_price_norm`）
#
# この後のセルで、変換後の分布を再度確認します。
#

# %% [markdown]
# ### Min-Max 正規化で[0,1]範囲に収める
#

# %%
# 偏りに対応するための対数変換
# 0またはそれ以下の値を小さな正の値に置き換えて対数変換可能にする
epsilon = 1e-10
raw_clean_with_pool["liquidity_log"] = np.log(raw_clean_with_pool["liquidity_scaled"].clip(lower=epsilon))
raw_clean_with_pool["sqrt_price_log"] = np.log(raw_clean_with_pool["sqrt_price_scaled"].clip(lower=epsilon))

# より均一な分布に調整
raw_clean_with_pool["liquidity_norm"] = (
    raw_clean_with_pool["liquidity_log"] - raw_clean_with_pool["liquidity_log"].min()
) / (raw_clean_with_pool["liquidity_log"].max() - raw_clean_with_pool["liquidity_log"].min())
raw_clean_with_pool["sqrt_price_norm"] = (
    raw_clean_with_pool["sqrt_price_log"] - raw_clean_with_pool["sqrt_price_log"].min()
) / (raw_clean_with_pool["sqrt_price_log"].max() - raw_clean_with_pool["sqrt_price_log"].min())

# 正規化後の分布確認
plt.figure(figsize=(15, 6))

plt.subplot(1, 2, 1)
plt.hist(raw_clean_with_pool["liquidity_norm"], bins=50)
plt.title("正規化後のliquidity分布")
plt.xlabel("normalized liquidity")
plt.ylabel("頻度")

plt.subplot(1, 2, 2)
plt.hist(raw_clean_with_pool["sqrt_price_norm"], bins=50)
plt.title("正規化後のsqrt_price分布")
plt.xlabel("normalized sqrt_price")
plt.ylabel("頻度")

plt.tight_layout()
plt.show()

# %% [markdown]
# 図より、
#
# - **0–1 に収まった**
#
#   - 両変数とも Min–Max 正規化によって必ず [0,1] の範囲に収まり、モデル入力のスケールが統一できた。
#
# - **特徴的なピーク**
#
#   - **normalized liquidity**：およそ **0.4–0.6** の範囲に高さのピークが見られ、複数モード（プール種別や流動性帯ごとの違い）が残存している。
#   - **normalized sqrt_price**：主に **0.4–0.5** に集中し、対数変換前の右裾の長い偏りが緩和されている。
#
# - **分布のバランス向上**
#
#   - 正規化後は極端な外れ値の影響が抑制され、全体的に平滑なヒストグラムになっているため、回帰や異常検知モデルなどで「値のスケール差による歪み」を軽減できる。
#
# - **次のステップ**
#   - 正規化後のデータを使って、Isolation Forest 等による異常検知モデルを学習し、“どのプールでいつ異常が起きるか” を定量的に捉えるフェーズに進みます。
#

# %%

# %% [markdown]
# ### 巨大固定小数点整数の問題と対応策
#
# Uniswap v3 における liquidity と sqrt_price 値は、ブロックチェーン上で精度を保持するために非常に大きな整数として表現されており、そのままでは分析や計算の支障となる可能性があります。
#
# ---
#
# #### 原因
#
# 1. **固定小数点数形式の採用**  
#    Solidity 等のスマートコントラクト言語では浮動小数点数をサポートしていないため、高精度計算のために値を大きな整数に変換して格納している。
# 2. **大きなスケーリング係数**  
#    典型的には 10^18（ETH の Wei 単位と同じ）や 2^96 などの巨大な係数でスケールアップして格納。
# 3. **精度保持の要求**  
#    AMM（自動マーケットメーカー）では価格計算の精度が重要なため、丸め誤差を最小化する特殊な数値表現が採用されている。
#
# ---
#
# #### 問題の特性
#
# 分析の結果、以下の特徴が確認されました：
#
# 1. **巨大な桁数**
#
#    - liquidity は主に 20-23 桁（10^20〜10^23）
#    - sqrt_price は主に 20-22 桁（10^20〜10^22）
#    - 一部の値は 10^30 を超える桁数
#
# 2. **分布の特徴**
#    - liquidity は log10 スケールで 20 と 25 付近に二峰性分布
#    - sqrt_price は log10 スケールで 25-30 の範囲に集中
#
# これらの特性は、イーサリアムのスマートコントラクトにおける標準的な固定小数点表現と一致しています。
#
# ---
#
# #### 影響
#
# - 通常の DOUBLE 型へのキャストでは精度損失が発生し、値が不正確になる。
# - 分析時に極端に大きい数値のため、相対比較や可視化が困難になる。
# - 数値計算（特に乗算）時にオーバーフローのリスクがある。
#
# ---
#
# #### 対応策
#
# ##### 1. スケーリング
#
# - 分布分析により、liquidity は 20-23 桁、sqrt_price は 20-22 桁に集中していることを確認
# - 対数スケール変換で実際の値の分布を検証し、10^18 が最適なスケーリング係数と判断
# - DuckDB で DECIMAL(38,0) 型を使用し、POWER(10, 18) で除算することで精度を保持しつつスケーリング
#
# ##### 2. データ検証と異常値処理
#
# - 変換前後の値の相関係数を確認し、情報損失がないことを検証
# - スケーリング後も極端な値が存在する場合は、分位数に基づく異常値検出を実施
# - 異常値フラグを追加し、モデルに情報として提供
#
# #### 今後の改善検討事項
#
# 1. **追加での変換の検討**
#
#    - 対数変換による正規化 `np.log1p(scaled_value)`
#    - 分位点に基づく正規化 `(x - x.min()) / (x.max() - x.min())`
#
# 2. **プロトコル・プール特性に基づく調整**
#
#    - Uniswap v3 と Sushiswap で異なるスケーリング係数の可能性
#    - 特定のプールタイプ（安定コイン等）に対する特殊処理
#
# 3. **機械学習前処理パイプラインへの統合**
#    - スケーリングと特徴量エンジニアリングの自動化
#    - スケーリングハイパーパラメータのチューニング
#
# ### 参考資料
#
# - [Uniswap v3 Core ホワイトペーパー](https://uniswap.org/whitepaper-v3.pdf)
# - [Uniswap v3 Math in Solidity](https://github.com/Uniswap/v3-core/blob/main/contracts/libraries/FullMath.sol)
#

# %%

# %% [markdown]
# ## 相関・多変量分析
#
# - `volume_usd`, `tvl_usd`, `liquidity_scaled`, `sqrt_price_scaled` の相関ヒートマップ
# - 主要指標ペアプロット（サンプル 5,000 件）
#

# %%
corr = df[["volume_usd", "tvl_usd", "liquidity_scaled", "sqrt_price_scaled"]].corr()
sns.heatmap(corr, annot=True, fmt=".2f")
plt.show()

# %% [markdown]
# - **`volume_usd` と `tvl_usd`** は **中程度の正相関** (ρ≈0.39)
#   - → 取引量が多いプールほど TVL も高い傾向。
# - **`liquidity_scaled` と他指標**、および **`sqrt_price_scaled` と他指標** はほぼ **無相関** (ρ≈0)
#   - → これらは独立した特徴量としてモデルに入れても重複情報が少ないと考えています
#

# %%
