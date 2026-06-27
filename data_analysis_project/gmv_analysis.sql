-- ============================================================
-- 项目1: GMV 多维归因分析 (Olist 巴西电商, 99,441笔真实订单)
-- 核心考点: 窗口函数 LAG/RANK、连环替代法、多维下钻、占比分析
-- ============================================================

-- 1.1 月度 GMV + 环比 ----------
WITH monthly AS (
    SELECT
        STRFTIME('%Y-%m', o.order_purchase_timestamp) AS month,
        COUNT(DISTINCT o.order_id) AS orders,
        ROUND(SUM(oi.price + oi.freight_value), 2) AS gmv,
        ROUND(AVG(oi.price + oi.freight_value), 2) AS aov
    FROM olist_orders_dataset o
    JOIN olist_order_items_dataset oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY STRFTIME('%Y-%m', o.order_purchase_timestamp)
)
SELECT
    month, orders, gmv, aov,
    ROUND((gmv - LAG(gmv) OVER w) * 100.0 / LAG(gmv) OVER w, 2) AS gmv_mom_pct,
    SUM(gmv) OVER w AS cumulative_gmv
FROM monthly
WINDOW w AS (ORDER BY month)
ORDER BY month;


-- 1.2 连环替代法: GMV = 订单数 x 每单商品数 x 商品均价 ----------
WITH monthly_detail AS (
    SELECT
        STRFTIME('%Y-%m', o.order_purchase_timestamp) AS month,
        COUNT(DISTINCT o.order_id) * 1.0 AS orders,
        COUNT(oi.order_item_id) * 1.0 AS items,
        ROUND(SUM(oi.price + oi.freight_value), 2) AS gmv
    FROM olist_orders_dataset o
    JOIN olist_order_items_dataset oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY STRFTIME('%Y-%m', o.order_purchase_timestamp)
),
with_lag AS (
    SELECT *, LAG(gmv) OVER w AS prev_gmv, LAG(orders) OVER w AS prev_orders,
           LAG(items) OVER w AS prev_items
    FROM monthly_detail
    WINDOW w AS (ORDER BY month)
)
SELECT
    month,
    ROUND(gmv, 0) AS gmv, ROUND(prev_gmv, 0) AS prev_gmv,
    ROUND((gmv - prev_gmv) * 100.0 / prev_gmv, 2) AS gmv_change_pct,
    -- 订单量贡献: (当期订单-上期订单) * 上期单均价
    ROUND((orders - prev_orders) * (prev_gmv / prev_orders), 0) AS order_cnt_effect,
    -- AOV贡献: 当期订单 * (当期AOV - 上期AOV)
    ROUND(orders * ((gmv/orders) - (prev_gmv/prev_orders)), 0) AS aov_effect
FROM with_lag
WHERE prev_gmv IS NOT NULL
ORDER BY month;


-- 1.3 品类 GMV 排名 ----------
SELECT
    COALESCE(pt.product_category_name_english, p.product_category_name) AS category,
    COUNT(DISTINCT oi.order_id) AS orders,
    ROUND(SUM(oi.price + oi.freight_value), 0) AS gmv,
    ROUND(SUM(oi.price + oi.freight_value) * 100.0 /
        (SELECT SUM(price + freight_value) FROM olist_order_items_dataset), 2) AS gmv_share_pct,
    RANK() OVER (ORDER BY SUM(oi.price + oi.freight_value) DESC) AS rank
FROM olist_order_items_dataset oi
JOIN olist_products_dataset p ON oi.product_id = p.product_id
LEFT JOIN product_category_name_translation pt ON p.product_category_name = pt.product_category_name
GROUP BY category
ORDER BY gmv DESC
LIMIT 10;


-- 1.4 各州 GMV ----------
SELECT
    c.customer_state,
    COUNT(DISTINCT o.order_id) AS orders,
    ROUND(SUM(oi.price + oi.freight_value), 0) AS gmv,
    ROUND(SUM(oi.price + oi.freight_value) * 100.0 /
        (SELECT SUM(price + freight_value) FROM olist_order_items_dataset), 2) AS gmv_share_pct
FROM olist_orders_dataset o
JOIN olist_order_items_dataset oi ON o.order_id = oi.order_id
JOIN olist_customers_dataset c ON o.customer_id = c.customer_id
WHERE o.order_status = 'delivered'
GROUP BY c.customer_state
ORDER BY gmv DESC;


-- 1.5 支付方式 + 分期数 GMV ----------
SELECT
    p.payment_type,
    COUNT(DISTINCT p.order_id) AS orders,
    ROUND(AVG(p.payment_installments), 1) AS avg_installments,
    ROUND(SUM(oi.price + oi.freight_value), 0) AS gmv
FROM olist_order_payments_dataset p
JOIN olist_order_items_dataset oi ON p.order_id = oi.order_id
GROUP BY p.payment_type
ORDER BY gmv DESC;


-- 1.6 Top 客户贡献集中度 ----------
WITH customer_gmv AS (
    SELECT
        o.customer_id,
        SUM(oi.price + oi.freight_value) AS total_gmv,
        RANK() OVER (ORDER BY SUM(oi.price + oi.freight_value) DESC) AS rn,
        COUNT(*) OVER () AS total_customers
    FROM olist_orders_dataset o
    JOIN olist_order_items_dataset oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY o.customer_id
)
SELECT 'Top 10%' AS segment,
    ROUND(SUM(total_gmv) * 100.0 / (SELECT SUM(price+freight_value) FROM olist_order_items_dataset), 2) AS gmv_share
FROM customer_gmv WHERE rn <= total_customers * 0.1
UNION ALL
SELECT 'Top 20%',
    ROUND(SUM(total_gmv) * 100.0 / (SELECT SUM(price+freight_value) FROM olist_order_items_dataset), 2)
FROM customer_gmv WHERE rn <= total_customers * 0.2;
