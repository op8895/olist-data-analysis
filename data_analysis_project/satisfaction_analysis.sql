-- ============================================================
-- 项目2: 客户满意度驱动分析 (Olist 巴西电商)
-- 核心考点: CASE WHEN分层、配送延迟计算、多维聚合对比
-- ============================================================

-- 2.1 评分分布 ----------
SELECT
    review_score,
    COUNT(*) AS cnt,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS pct
FROM olist_order_reviews_dataset
GROUP BY review_score
ORDER BY review_score;


-- 2.2 配送延迟 vs 评分 (核心洞察) ----------
SELECT
    r.review_score,
    COUNT(*) AS orders,
    ROUND(AVG(JULIANDAY(o.order_delivered_customer_date) - JULIANDAY(o.order_purchase_timestamp)), 1) AS avg_delivery_days,
    ROUND(AVG((JULIANDAY(o.order_delivered_customer_date) - JULIANDAY(o.order_purchase_timestamp))
        - (JULIANDAY(o.order_estimated_delivery_date) - JULIANDAY(o.order_purchase_timestamp))), 1) AS avg_delay_days,
    ROUND(SUM(CASE WHEN JULIANDAY(o.order_delivered_customer_date) <= JULIANDAY(o.order_estimated_delivery_date)
        THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS on_time_pct
FROM olist_order_reviews_dataset r
JOIN olist_orders_dataset o ON r.order_id = o.order_id
WHERE o.order_status = 'delivered'
GROUP BY r.review_score
ORDER BY r.review_score DESC;


-- 2.3 品类满意度排名 ----------
SELECT
    COALESCE(pt.product_category_name_english, p.product_category_name) AS category,
    COUNT(DISTINCT r.order_id) AS orders,
    ROUND(AVG(r.review_score), 2) AS avg_score,
    ROUND(SUM(CASE WHEN JULIANDAY(o.order_delivered_customer_date) <= JULIANDAY(o.order_estimated_delivery_date)
        THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS on_time_pct
FROM olist_order_reviews_dataset r
JOIN olist_orders_dataset o ON r.order_id = o.order_id
JOIN olist_order_items_dataset oi ON o.order_id = oi.order_id
JOIN olist_products_dataset p ON oi.product_id = p.product_id
LEFT JOIN product_category_name_translation pt ON p.product_category_name = pt.product_category_name
WHERE o.order_status = 'delivered'
GROUP BY category
HAVING COUNT(DISTINCT r.order_id) >= 100
ORDER BY avg_score DESC;


-- 2.4 价格段 vs 评分 ----------
SELECT
    CASE
        WHEN (oi.price + oi.freight_value) < 50 THEN '<R$50'
        WHEN (oi.price + oi.freight_value) < 100 THEN 'R$50-100'
        WHEN (oi.price + oi.freight_value) < 200 THEN 'R$100-200'
        WHEN (oi.price + oi.freight_value) < 500 THEN 'R$200-500'
        WHEN (oi.price + oi.freight_value) < 1000 THEN 'R$500-1K'
        ELSE 'R$1K+'
    END AS price_range,
    COUNT(DISTINCT r.order_id) AS orders,
    ROUND(AVG(r.review_score), 2) AS avg_score,
    ROUND(AVG(oi.price + oi.freight_value), 0) AS avg_price
FROM olist_order_reviews_dataset r
JOIN olist_order_items_dataset oi ON r.order_id = oi.order_id
GROUP BY price_range
ORDER BY avg_price;


-- 2.5 准时 vs 延迟评分对比 ----------
SELECT
    CASE WHEN JULIANDAY(o.order_delivered_customer_date) <= JULIANDAY(o.order_estimated_delivery_date)
        THEN '准时' ELSE '延迟' END AS delivery_status,
    COUNT(*) AS orders,
    ROUND(AVG(r.review_score), 2) AS avg_score,
    ROUND(SUM(CASE WHEN r.review_score >= 4 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS good_rate_pct,
    ROUND(SUM(CASE WHEN r.review_score <= 2 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS bad_rate_pct
FROM olist_order_reviews_dataset r
JOIN olist_orders_dataset o ON r.order_id = o.order_id
WHERE o.order_status = 'delivered'
GROUP BY delivery_status;
