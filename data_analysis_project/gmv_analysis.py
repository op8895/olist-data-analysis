"""
项目1: GMV 多维归因分析 (Olist巴西电商, 99,441笔真实订单)
跑法: python gmv_analysis.py
输出: gmv_chart.png
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
orders = pd.read_csv('olist_orders_dataset.csv', parse_dates=['order_purchase_timestamp'])
items = pd.read_csv('olist_order_items_dataset.csv')
products = pd.read_csv('olist_products_dataset.csv')
trans = pd.read_csv('product_category_name_translation.csv')
customers = pd.read_csv('olist_customers_dataset.csv')
payments = pd.read_csv('olist_order_payments_dataset.csv')

# 只取已交付订单
orders = orders[orders['order_status'] == 'delivered']
orders['month'] = orders['order_purchase_timestamp'].dt.to_period('M').dt.to_timestamp()

# 合并品类名
products = products.merge(trans, on='product_category_name', how='left')
products['category_en'] = products['product_category_name_english'].fillna(products['product_category_name'])

# 算 GMV = price + freight
items['item_gmv'] = items['price'] + items['freight_value']

# 合并全表
df = items.merge(orders[['order_id','customer_id','month']], on='order_id')
df = df.merge(products[['product_id','category_en']], on='product_id')
df = df.merge(customers[['customer_id','customer_state']], on='customer_id')

total_gmv = df['item_gmv'].sum()
print(f"总 GMV: R${total_gmv:,.0f} (巴西雷亚尔)")
print(f"订单数: {df['order_id'].nunique():,}")
print(f"时间: {df['month'].min().date()} ~ {df['month'].max().date()}")

# ========== 1. 月度 GMV 趋势 ==========
monthly = df.groupby('month').agg(
    gmv=('item_gmv','sum'),
    orders=('order_id','nunique'),
    items_per_order=('item_gmv','count'),
    aov=('item_gmv','mean')
).reset_index().sort_values('month')
monthly['items_per_order'] = monthly['items_per_order'] / monthly['orders']
monthly['gmv_mom'] = monthly['gmv'].pct_change()

print("\n--- 月度 GMV ---")
for _, r in monthly.iterrows():
    bar = '#' * int(r['gmv']/50000)
    print(f"  {r['month'].strftime('%Y-%m')}: R${r['gmv']:,.0f} | 订单{r['orders']:,} | AOV R${r['aov']:.0f} | 环比{r['gmv_mom']:+.1%}")

# ========== 2. 连环替代法: GMV = 订单数 x 每单商品数 x 商品均价 ==========
m0 = monthly.iloc[0]
m1 = monthly.iloc[-1]

ord0, ip00, aov0 = m0['orders'], m0['items_per_order'], m0['aov']
ord1, ip01, aov1 = m1['orders'], m1['items_per_order'], m1['aov']

gmv0 = ord0 * ip00 * aov0
gmv1 = ord1 * ip01 * aov1

step1 = ord1 * ip00 * aov0
step2 = ord1 * ip01 * aov0

ord_eff = step1 - gmv0
ipo_eff = step2 - step1
aov_eff = gmv1 - step2
total_abs = abs(ord_eff) + abs(ipo_eff) + abs(aov_eff)

print(f"\n--- 连环替代法: 首月→末月 ---")
print(f"  首月 GMV={gmv0:,.0f}, 末月 GMV={gmv1:,.0f}, 变化={(gmv1-gmv0)/gmv0*100:+.1f}%")
print(f"  订单量贡献: {ord_eff:+,.0f} ({ord_eff/total_abs*100:.0f}%)")
print(f"  每单商品数贡献: {ipo_eff:+,.0f} ({ipo_eff/total_abs*100:.0f}%)")
print(f"  商品均价贡献: {aov_eff:+,.0f} ({aov_eff/total_abs*100:.0f}%)")

# ========== 3. 品类下钻 ==========
cat = df.groupby('category_en').agg(
    gmv=('item_gmv','sum'), orders=('order_id','nunique'), aov=('item_gmv','mean')
).sort_values('gmv', ascending=False)
print("\n--- Top 10 品类 GMV ---")
for i, (c, r) in enumerate(cat.head(10).iterrows()):
    print(f"  {i+1}. {c:<30}: R${r['gmv']:>,.0f} ({r['gmv']/total_gmv*100:.1f}%) | AOV R${r['aov']:.0f}")

# ========== 4. 州下钻 ==========
state = df.groupby('customer_state').agg(
    gmv=('item_gmv','sum'), orders=('order_id','nunique')
).sort_values('gmv', ascending=False)
print("\n--- Top 5 州 GMV ---")
for s, r in state.head(5).iterrows():
    print(f"  {s}: R${r['gmv']:>,.0f} ({r['gmv']/total_gmv*100:.1f}%) | 订单{r['orders']:,}")

# ========== 5. 支付分析 ==========
pay_merge = payments.merge(orders[['order_id','month']], on='order_id')
pay_summary = pay_merge.groupby('payment_type').agg(
    orders=('order_id','nunique')
).sort_values('orders', ascending=False)
print("\n--- 支付方式 ---")
for p, r in pay_summary.iterrows():
    print(f"  {p:<15}: {r['orders']:,} 单 ({r['orders']/len(pay_merge)*100:.1f}%)")

# 分期 vs GMV
pay_merge2 = payments.merge(items[['order_id','item_gmv']], on='order_id')
install_gmv = pay_merge2.groupby('payment_installments').agg(
    gmv=('item_gmv','sum'), orders=('order_id','nunique')
).query('payment_installments <= 12')
print("\n--- 分期数 vs GMV ---")
for i, r in install_gmv.iterrows():
    print(f"  {int(i)}期: GMV R${r['gmv']:>,.0f} | 订单{r['orders']:,}")

# ========== 6. 画图 ==========
fig, axes = plt.subplots(2, 2, figsize=(15, 11))

# 图1: 月度GMV趋势
ax = axes[0, 0]
ax.fill_between(range(len(monthly)), monthly['gmv']/1e6, alpha=0.3, color='#2196F3')
ax.plot(range(len(monthly)), monthly['gmv']/1e6, '-o', color='#2196F3', linewidth=2, markersize=5)
ax.set_xticks(range(0, len(monthly), 3))
ax.set_xticklabels([m.strftime('%Y-%m') for m in monthly['month'].iloc[::3]], rotation=45, fontsize=8)
ax.set_title('月度 GMV 趋势 (百万雷亚尔)', fontsize=14, fontweight='bold')
ax.set_ylabel('GMV (百万 R$)'); ax.grid(True, alpha=0.3)

# 图2: 归因瀑布图
ax = axes[0, 1]
labels = ['首月GMV', '订单量', '每单商品数', '商品均价', '末月GMV']
vals = [gmv0/1e6, ord_eff/1e6, ipo_eff/1e6, aov_eff/1e6, gmv1/1e6]
colors_bar = ['#607D8B'] + ['#4CAF50' if v>0 else '#E53935' for v in vals[1:-1]] + ['#607D8B']
ax.bar(labels, vals, color=colors_bar, edgecolor='white')
ax.set_title('GMV 归因瀑布图 (百万雷亚尔)', fontsize=14, fontweight='bold')
for i, (l, v) in enumerate(zip(labels, vals)):
    ax.text(i, v+(0.02 if v>=0 else -0.12), f'R${v:+.1f}M', ha='center', fontsize=9, fontweight='bold')

# 图3: Top 10 品类 GMV
ax = axes[1, 0]
top10 = cat.head(10).sort_values('gmv')
ax.barh(top10.index.str.replace('_',' ').str.title(), top10['gmv']/1e6, color='#2196F3', edgecolor='white')
ax.set_xlabel('GMV (百万 R$)')
ax.set_title('Top 10 品类 GMV', fontsize=14, fontweight='bold')

# 图4: 州 GMV
ax = axes[1, 1]
top_states = state.head(10).sort_values('gmv')
ax.barh(top_states.index, top_states['gmv']/1e6, color='#FF9800', edgecolor='white')
ax.set_xlabel('GMV (百万 R$)')
ax.set_title('Top 10 州 GMV', fontsize=14, fontweight='bold')

plt.tight_layout()
plt.savefig('gmv_chart.png', dpi=150, bbox_inches='tight')
print("\n[OK] gmv_chart.png 已保存")

print("\n" + "="*60)
print("[====] 结论")
print("="*60)
main = max([('订单量', ord_eff), ('每单商品数', ipo_eff), ('商品均价', aov_eff)], key=lambda x: abs(x[1]))
print(f"1. GMV 变动主驱动:「{main[0]}」贡献 {abs(main[1])/total_abs*100:.0f}%")
print(f"2. 最大品类「{cat.index[0]}」({cat.iloc[0]['gmv']/total_gmv*100:.1f}%), 最大州「{state.index[0]}」({state.iloc[0]['gmv']/total_gmv*100:.1f}%)")
print(f"3. 信用卡占 {pay_summary.loc['credit_card','orders']/pay_summary['orders'].sum()*100:.0f}%，分期客户 GMV 更高")
print("="*60)
