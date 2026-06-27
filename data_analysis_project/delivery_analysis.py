"""
项目3: 履约效率分析 (Olist巴西电商)
跑法: python delivery_analysis.py
输出: delivery_chart.png
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
orders = pd.read_csv('olist_orders_dataset.csv', parse_dates=['order_purchase_timestamp','order_delivered_customer_date','order_estimated_delivery_date','order_approved_at'])
customers = pd.read_csv('olist_customers_dataset.csv')
items = pd.read_csv('olist_order_items_dataset.csv')
products = pd.read_csv('olist_products_dataset.csv')
trans = pd.read_csv('product_category_name_translation.csv')

products = products.merge(trans, on='product_category_name', how='left')
products['category_en'] = products['product_category_name_english'].fillna(products['product_category_name'])

# 只取已交付
df = orders[orders['order_status']=='delivered'].copy()
df['delivery_days'] = (df['order_delivered_customer_date'] - df['order_purchase_timestamp']).dt.days
df['estimated_days'] = (df['order_estimated_delivery_date'] - df['order_purchase_timestamp']).dt.days
df['delay_days'] = df['delivery_days'] - df['estimated_days']
df['on_time'] = df['delay_days'] <= 0
df['month'] = df['order_purchase_timestamp'].dt.to_period('M').dt.to_timestamp()

# 合并地理位置
df = df.merge(customers[['customer_id','customer_state','customer_city']], on='customer_id')

# 合并品类
df = df.merge(items[['order_id','product_id']], on='order_id')
df = df.merge(products[['product_id','category_en']], on='product_id')

print(f"已交付订单: {len(df):,}")
print(f"平均配送: {df['delivery_days'].mean():.1f}天 | 预估: {df['estimated_days'].mean():.1f}天")
print(f"准时率: {df['on_time'].mean():.0%} | 平均延迟: {df['delay_days'].mean():.1f}天")

# ========== 1. 月度履约趋势 ==========
print("\n--- 月度履约 ---")
monthly_perf = df.groupby('month').agg(
    orders=('order_id','nunique'),
    avg_delivery=('delivery_days','mean'),
    on_time_pct=('on_time','mean'),
    avg_delay=('delay_days','mean')
).sort_index()
for m, r in monthly_perf.iterrows():
    flag = '!!' if r['on_time_pct'] < 0.8 else ''
    print(f"  {m.strftime('%Y-%m')}: {r['orders']:,}单 | 配送{r['avg_delivery']:.0f}天 | 准时率{r['on_time_pct']:.0%} {flag}")

# ========== 2. 州履约排名 ==========
print("\n--- 各州履约 (订单>=100) ---")
state_perf = df.groupby('customer_state').agg(
    orders=('order_id','nunique'),
    avg_delivery=('delivery_days','mean'),
    on_time_pct=('on_time','mean'),
    avg_delay=('delay_days','mean')
).query('orders >= 100').sort_values('on_time_pct', ascending=False)

for i, (s, r) in enumerate(state_perf.head(10).iterrows()):
    print(f"  {s}: 准时率{r['on_time_pct']:.0%} | 配送{r['avg_delivery']:.0f}天 | {int(r['orders'])}单")
print("  ...")
for i, (s, r) in enumerate(state_perf.tail(5).iterrows()):
    print(f"  {s}: 准时率{r['on_time_pct']:.0%} | 配送{r['avg_delivery']:.0f}天 | {int(r['orders'])}单")

# ========== 3. 品类履约差异 ==========
print("\n--- 各品类履约 (订单>=200) ---")
cat_perf = df.groupby('category_en').agg(
    orders=('order_id','nunique'),
    avg_delivery=('delivery_days','mean'),
    on_time_pct=('on_time','mean')
).query('orders >= 200').sort_values('avg_delivery')

for i, (c, r) in enumerate(cat_perf.head(10).iterrows()):
    print(f"  {c:<30}: 配送{r['avg_delivery']:.0f}天 | 准时率{r['on_time_pct']:.0%}")
print("  ... 最慢品类:")
for i, (c, r) in enumerate(cat_perf.tail(5).iterrows()):
    print(f"  {c:<30}: 配送{r['avg_delivery']:.0f}天 | 准时率{r['on_time_pct']:.0%}")

# ========== 4. 配送天数分布 ==========
df['delivery_bucket'] = pd.cut(df['delivery_days'], bins=[0,3,7,14,21,30,60,200], labels=['0-3天','4-7天','8-14天','15-21天','22-30天','31-60天','60天+'])
print("\n--- 配送天数分布 ---")
for b, grp in df.groupby('delivery_bucket', observed=False):
    print(f"  {b}: {len(grp):,}单 ({len(grp)/len(df)*100:.1f}%) | 准时率{grp['on_time'].mean():.0%}")

# ========== 5. 差评集中在哪 ==========
reviews = pd.read_csv('olist_order_reviews_dataset.csv')
df2 = df.merge(reviews[['order_id','review_score']], on='order_id')
bad = df2[df2['review_score'] <= 2]
print(f"\n--- 差评(1-2星)履约特征 ---")
print(f"  差评准时率: {bad['on_time'].mean():.0%} (全量: {df2['on_time'].mean():.0%})")
print(f"  差评配送天数: {bad['delivery_days'].mean():.0f}天 (全量: {df2['delivery_days'].mean():.0f}天)")
print(f"  差评延迟: {bad['delay_days'].mean():.0f}天 (全量: {df2['delay_days'].mean():.0f}天)")

# ========== 6. 画图 ==========
fig, axes = plt.subplots(2, 2, figsize=(15, 11))

# 图1: 月度配送趋势
ax = axes[0, 0]
ax.plot(monthly_perf.index, monthly_perf['avg_delivery'], '-o', color='#2196F3', linewidth=2, label='实际配送天数')
ax.plot(monthly_perf.index, monthly_perf['avg_delivery']-monthly_perf['avg_delay'], '--', color='#9E9E9E', linewidth=1.5, label='预估天数')
ax2 = ax.twinx()
ax2.bar(monthly_perf.index, monthly_perf['on_time_pct']*100, alpha=0.2, color='#4CAF50', width=20)
ax2.set_ylabel('准时率 (%)', color='#4CAF50')
ax.set_title('月度配送天数 & 准时率', fontsize=14, fontweight='bold')
ax.set_ylabel('天数'); ax.legend(loc='upper left')
ax.grid(True, alpha=0.3)

# 图2: 各州准时率
ax = axes[0, 1]
sp = state_perf.sort_values('on_time_pct')
colors_state = ['#4CAF50' if v>0.85 else '#FF9800' if v>0.75 else '#E53935' for v in sp['on_time_pct']]
ax.barh(sp.index, sp['on_time_pct']*100, color=colors_state, edgecolor='white')
ax.axvline(x=df['on_time'].mean()*100, color='red', linestyle='--', label=f'均值 {df["on_time"].mean()*100:.0f}%')
ax.set_xlabel('准时率 (%)'); ax.set_title('各州准时率排名', fontsize=14, fontweight='bold')
ax.legend()

# 图3: 配送天数分布
ax = axes[1, 0]
dist = df.groupby('delivery_bucket', observed=False).size()
ax.pie(dist.values, labels=dist.index, autopct='%1.1f%%', startangle=90,
       colors=plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, len(dist))))
ax.set_title('配送天数分布', fontsize=14, fontweight='bold')

# 图4: 品类配送时间
ax = axes[1, 1]
plot_cat = cat_perf.sort_values('avg_delivery')
ax.barh(range(len(plot_cat)), plot_cat['avg_delivery'], color='#2196F3', edgecolor='white')
ax.set_yticks(range(len(plot_cat)))
ax.set_yticklabels([c.replace('_',' ').title()[:25] for c in plot_cat.index], fontsize=7)
ax.set_xlabel('平均配送天数'); ax.set_title('各品类配送天数', fontsize=14, fontweight='bold')
ax.axvline(x=df['delivery_days'].mean(), color='red', linestyle='--')

plt.tight_layout()
plt.savefig('delivery_chart.png', dpi=150, bbox_inches='tight')
print("\n[OK] delivery_chart.png 已保存")

print("\n" + "="*60)
print("[====] 结论")
print("="*60)
worst_state = state_perf['on_time_pct'].idxmin()
best_state = state_perf['on_time_pct'].idxmax()
print(f"1. 准时率最低州「{worst_state}」({state_perf.loc[worst_state,'on_time_pct']:.0%}) vs 最高「{best_state}」({state_perf.loc[best_state,'on_time_pct']:.0%})")
print(f"2. 差评订单准时率仅{bad['on_time'].mean():.0%}，延迟{bad['delay_days'].mean():.0f}天 → 配送是满意度核心杠杆")
print(f"3. {dist.index[-1]}配送占{dist.values[-1]/dist.sum()*100:.1f}%，建议优化长途物流方案")
print(f"4. 月度准时率呈{'上升' if monthly_perf['on_time_pct'].iloc[-1] > monthly_perf['on_time_pct'].iloc[0] else '下降'}趋势，运营持续{'改善' if monthly_perf['on_time_pct'].iloc[-1] > monthly_perf['on_time_pct'].iloc[0] else '恶化'}")
print("="*60)
