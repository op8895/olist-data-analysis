-- ============================================================
-- 项目3: 履约效率分析 (Olist 巴西电商)
-- 核心考点: 日期计算、SLA达成率、CASE WHEN分层、时间序列
-- ============================================================

-- 3.1 月度履约趋势 ----------
SELECT
    STRFTIME('%Y-%m', order_purchase_timestamp) AS month,
    COUNT(order_id) AS orders,
    ROUND(AVG(JULIANDAY(order_delivered_customer_date) - JULIANDAY(order_purchase_timestamp)), 1) AS avg_delivery_days,
    ROUND(AVG(JULIANDAY(order_estimated_delivery_date) - JULIANDAY(order_purchase_timestamp)), 1) AS avg_estimated_days,
    ROUND(SUM(CASE WHEN JULIANDAY(order_delivered_customer_date) <= JULIANDAY(order_estimated_delivery_date)
        THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS on_time_pct
FROM olist_orders_dataset
WHERE order_status = 'delivered'
GROUP BY STRFTIME('%Y-%m', order_purchase_timestamp)
ORDER BY month;


-- 3.2 各州履约排名 ----------
SELECT
    c.customer_state,
    COUNT(o.order_id) AS orders,
    ROUND(AVG(JULIANDAY(o.order_delivered_customer_date) - JULIANDAY(o.order_purchase_timestamp)), 1) AS avg_delivery_days,
    ROUND(SUM(CASE WHEN JULIANDAY(o.order_delivered_customer_date) <= JULIANDAY(o.order_estimated_delivery_date)
        THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS on_time_pct,
    ROUND(AVG((JULIANDAY(o.order_delivered_customer_date) - JULIANDAY(o.order_purchase_timestamp))
        - (JULIANDAY(o.order_estimated_delivery_date) - JULIANDAY(o.order_purchase_timestamp))), 1) AS avg_delay_days
FROM olist_orders_dataset o
JOIN olist_customers_dataset c ON o.customer_id = c.customer_id
WHERE o.order_status = 'delivered'
GROUP BY c.customer_state
HAVING COUNT(o.order_id) >= 100
ORDER BY on_time_pct DESC;


-- 3.3 各品类配送天数 ----------
SELECT
    COALESCE(pt.product_category_name_english, p.product_category_name) AS category,
    COUNT(DISTINCT o.order_id) AS orders,
    ROUND(AVG(JULIANDAY(o.order_delivered_customer_date) - JULIANDAY(o.order_purchase_timestamp)), 1) AS avg_delivery_days,
    ROUND(SUM(CASE WHEN JULIANDAY(o.order_delivered_customer_date) <= JULIANDAY(o.order_estimated_delivery_date)
        THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS on_time_pct
FROM olist_orders_dataset o
JOIN olist_order_items_dataset oi ON o.order_id = oi.order_id
JOIN olist_products_dataset p ON oi.product_id = p.product_id
LEFT JOIN product_category_name_translation pt ON p.product_category_name = pt.product_category_name
WHERE o.order_status = 'delivered'
GROUP BY category
HAVING COUNT(DISTINCT o.order_id) >= 200
ORDER BY avg_delivery_days;


-- 3.4 配送速度分层 ----------
SELECT
    CASE
        WHEN JULIANDAY(order_delivered_customer_date) - JULIANDAY(order_purchase_timestamp) <= 3 THEN '0-3天'
        WHEN JULIANDAY(order_delivered_customer_date) - JULIANDAY(order_purchase_timestamp) <= 7 THEN '4-7天'
        WHEN JULIANDAY(order_delivered_customer_date) - JULIANDAY(order_purchase_timestamp) <= 14 THEN '8-14天'
        WHEN JULIANDAY(order_delivered_customer_date) - JULIANDAY(order_purchase_timestamp) <= 21 THEN '15-21天'
        WHEN JULIANDAY(order_delivered_customer_date) - JULIANDAY(order_purchase_timestamp) <= 30 THEN '22-30天'
        ELSE '30天+'
    END AS delivery_bucket,
    COUNT(*) AS orders,
    ROUND(SUM(CASE WHEN JULIANDAY(order_delivered_customer_date) <= JULIANDAY(order_estimated_delivery_date)
        THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS on_time_pct
FROM olist_orders_dataset
WHERE order_status = 'delivered'
GROUP BY delivery_bucket
ORDER BY MIN(JULIANDAY(order_delivered_customer_date) - JULIANDAY(order_purchase_timestamp));


-- 3.5 差评订单的履约特征 ----------
SELECT
    CASE WHEN r.review_score <= 2 THEN '差评(1-2)' ELSE '好评(4-5)' END AS review_group,
    COUNT(DISTINCT o.order_id) AS orders,
    ROUND(AVG(JULIANDAY(o.order_delivered_customer_date) - JULIANDAY(o.order_purchase_timestamp)), 1) AS avg_delivery_days,
    ROUND(AVG((JULIANDAY(o.order_delivered_customer_date) - JULIANDAY(o.order_purchase_timestamp))
        - (JULIANDAY(o.order_estimated_delivery_date) - JULIANDAY(o.order_purchase_timestamp))), 1) AS avg_delay_days,
    ROUND(SUM(CASE WHEN JULIANDAY(o.order_delivered_customer_date) <= JULIANDAY(o.order_estimated_delivery_date)
        THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS on_time_pct
FROM olist_order_reviews_dataset r
JOIN olist_orders_dataset o ON r.order_id = o.order_id
WHERE o.order_status = 'delivered' AND r.review_score IN (1,2,4,5)
GROUP BY review_group;
