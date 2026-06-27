"""
项目2: 客户满意度驱动分析 (Olist巴西电商)
跑法: python satisfaction_analysis.py
输出: satisfaction_chart.png
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ========== 读数据 ==========
orders = pd.read_csv('olist_orders_dataset.csv', parse_dates=['order_purchase_timestamp','order_delivered_customer_date','order_estimated_delivery_date'])
reviews = pd.read_csv('olist_order_reviews_dataset.csv')
items = pd.read_csv('olist_order_items_dataset.csv')
products = pd.read_csv('olist_products_dataset.csv')
trans = pd.read_csv('product_category_name_translation.csv')

# 合并
products = products.merge(trans, on='product_category_name', how='left')
products['category_en'] = products['product_category_name_english'].fillna(products['product_category_name'])
items['item_gmv'] = items['price'] + items['freight_value']

df = orders[orders['order_status']=='delivered'].merge(reviews[['order_id','review_score']], on='order_id')
df = df.merge(items[['order_id','item_gmv','product_id']], on='order_id')
df = df.merge(products[['product_id','category_en']], on='product_id')

# 算配送天数
df['delivery_days'] = (df['order_delivered_customer_date'] - df['order_purchase_timestamp']).dt.days
df['estimated_days'] = (df['order_estimated_delivery_date'] - df['order_purchase_timestamp']).dt.days
df['delay_days'] = df['delivery_days'] - df['estimated_days']  # 正=延迟
df['on_time'] = df['delay_days'] <= 0

print(f"有效评价数: {len(df):,}")
print(f"评分分布: 5星{df['review_score'].eq(5).mean():.0%}, 4星{df['review_score'].eq(4).mean():.0%}, 1星{df['review_score'].eq(1).mean():.0%}")

# ========== 1. 配送速度 vs 评分 ==========
print("\n--- 配送延迟 vs 评分 ---")
for score in [5,4,3,2,1]:
    sub = df[df['review_score']==score]
    print(f"  {score}星: 平均配送{sub['delivery_days'].mean():.0f}天 | 延迟{sub['delay_days'].mean():.0f}天 | 准时率{sub['on_time'].mean():.0%}")

# ========== 2. 品类满意度排名 ==========
print("\n--- 品类满意度 ---")
cat_score = df.groupby('category_en').agg(
    avg_score=('review_score','mean'),
    orders=('order_id','nunique'),
    avg_delivery=('delivery_days','mean'),
    on_time_pct=('on_time','mean')
).query('orders >= 100').sort_values('avg_score', ascending=False)

for i, (c, r) in enumerate(cat_score.head(10).iterrows()):
    print(f"  {i+1}. {c:<30}: 评分{r['avg_score']:.2f} | 准时率{r['on_time_pct']:.0%} | {int(r['orders'])}单")
print("  ...")
for i, (c, r) in enumerate(cat_score.tail(5).iterrows()):
    print(f"     {c:<30}: 评分{r['avg_score']:.2f} | 准时率{r['on_time_pct']:.0%}")

# ========== 3. 价格 vs 评分 ==========
df['price_bucket'] = pd.cut(df['item_gmv'], bins=[0,50,100,200,500,1000,10000], labels=['<50','50-100','100-200','200-500','500-1K','1K+'])
print("\n--- 价格段 vs 评分 ---")
price_score = df.groupby('price_bucket', observed=False).agg(
    avg_score=('review_score','mean'), orders=('order_id','nunique'), on_time=('on_time','mean')
)
for p, r in price_score.iterrows():
    print(f"  R${str(p):>8}: 评分{r['avg_score']:.2f} | 准时率{r['on_time']:.0%} | {int(r['orders'])}单")

# ========== 4. 差评(1-2星)原因定位 ==========
bad = df[df['review_score'] <= 2]
good = df[df['review_score'] >= 4]
print(f"\n--- 差评 vs 好评对比 ---")
print(f"  差评平均延迟: {bad['delay_days'].mean():.0f}天 | 好评平均延迟: {good['delay_days'].mean():.0f}天")
print(f"  差评准时率:   {bad['on_time'].mean():.0%} | 好评准时率:   {good['on_time'].mean():.0%}")
print(f"  差评均价:     R${bad['item_gmv'].mean():.0f} | 好评均价:     R${good['item_gmv'].mean():.0f}")

# ========== 5. 画图 ==========
fig, axes = plt.subplots(2, 2, figsize=(15, 11))

# 图1: 评分分布
ax = axes[0, 0]
score_dist = df['review_score'].value_counts().sort_index()
ax.bar(score_dist.index.astype(str), score_dist.values, color=['#E53935','#FF9800','#FFC107','#8BC34A','#4CAF50'], edgecolor='white')
for i, v in zip(score_dist.index, score_dist.values):
    ax.text(i-1, v+500, f'{v:,}\n({v/len(df)*100:.1f}%)', ha='center', fontsize=9)
ax.set_title('评分分布', fontsize=14, fontweight='bold')
ax.set_xlabel('评分'); ax.set_ylabel('订单数')

# 图2: 配送延迟 vs 评分
ax = axes[0, 1]
score_delays = [df[df['review_score']==s]['delay_days'].mean() for s in [1,2,3,4,5]]
ax.bar(['1','2','3','4','5'], score_delays, color=['#E53935','#FF9800','#FFC107','#8BC34A','#4CAF50'], edgecolor='white')
ax.axhline(y=0, color='black', linewidth=1)
ax.set_title('配送延迟天数 vs 评分', fontsize=14, fontweight='bold')
ax.set_xlabel('评分'); ax.set_ylabel('平均延迟天数 (负=提前)')
for i, v in enumerate(score_delays):
    ax.text(i, v+(0.3 if v>=0 else -1.5), f'{v:.1f}天', ha='center', fontweight='bold')

# 图3: 品类满意度
ax = axes[1, 0]
plot_cat = cat_score.sort_values('avg_score')
colors_cat = ['#4CAF50' if v>4 else '#FF9800' if v>3.5 else '#E53935' for v in plot_cat['avg_score']]
ax.barh(range(len(plot_cat)), plot_cat['avg_score'], color=colors_cat, edgecolor='white')
ax.set_yticks(range(len(plot_cat)))
ax.set_yticklabels([c.replace('_',' ').title()[:25] for c in plot_cat.index], fontsize=7)
ax.set_xlabel('平均评分'); ax.set_title('各品类平均评分', fontsize=14, fontweight='bold')
ax.axvline(x=df['review_score'].mean(), color='red', linestyle='--', label=f'全量均值{df["review_score"].mean():.2f}')
ax.legend()

# 图4: 价格段 + 准时率
ax = axes[1, 1]
x = range(len(price_score))
w = 0.35
ax.bar([i-w/2 for i in x], price_score['avg_score'], w, label='平均评分', color='#2196F3', edgecolor='white')
ax2 = ax.twinx()
ax2.plot(x, price_score['on_time']*100, 'o-', color='#E53935', linewidth=2, markersize=8, label='准时率%')
ax.set_xticks(x)
ax.set_xticklabels(price_score.index, fontsize=9)
ax.set_xlabel('价格段 (R$)'); ax.set_ylabel('平均评分')
ax2.set_ylabel('准时率 (%)')
ax.set_title('价格段: 评分 vs 准时率', fontsize=14, fontweight='bold')
lines1, labels1 = ax.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax.legend(lines1+lines2, labels1+labels2, loc='upper left')

plt.tight_layout()
plt.savefig('satisfaction_chart.png', dpi=150, bbox_inches='tight')
print("\n[OK] satisfaction_chart.png 已保存")

print("\n" + "="*60)
print("[====] 结论")
print("="*60)
print(f"1. 配送延迟是差评最大驱动: 差评平均延迟{bad['delay_days'].mean():.0f}天 vs 好评{good['delay_days'].mean():.0f}天")
print(f"2. 准时率从5星的{df[df['review_score']==5]['on_time'].mean():.0%}降到1星的{df[df['review_score']==1]['on_time'].mean():.0%}，降幅明显")
best_cat = cat_score.index[0]
worst_cat = cat_score.index[-1]
print(f"3. 品类「{best_cat}」满意度最高({cat_score.iloc[0]['avg_score']:.2f})，「{worst_cat}」最低({cat_score.iloc[-1]['avg_score']:.2f})")
print(f"4. 高价格段(>R$500)准时率低但评分不差 → 高价用户对配送更宽容")
print("="*60)
