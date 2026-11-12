-- shop-trade 题目 01：仅创建 goods、order、payment 三张业务表。
-- 金额字段一律 BIGINT，单位为「分」；不使用浮点数。
-- 所有业务表使用 MySQL(InnoDB)：ENGINE=InnoDB、DEFAULT CHARSET=utf8mb4。
-- order 是 MySQL 保留字，必须使用反引号。

CREATE TABLE IF NOT EXISTS `goods` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  `deleted_at` DATETIME(3) NULL DEFAULT NULL,
  `goods_no` VARCHAR(64) NOT NULL,
  `name` VARCHAR(128) NOT NULL,
  `unit_price` BIGINT NOT NULL,
  `available_stock` INT NOT NULL DEFAULT 0,
  `occupied_stock` INT NOT NULL DEFAULT 0,
  `status` VARCHAR(32) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_goods_goods_no` (`goods_no`),
  KEY `idx_goods_status` (`status`),
  KEY `idx_goods_available_stock` (`available_stock`),
  KEY `idx_goods_deleted_at` (`deleted_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 并发风险点：下单与释放库存必须按 goods.id 主键命中聚簇索引并加 InnoDB 行锁；
-- 若更新条件未命中索引，InnoDB 可能扩大锁范围甚至升级为表锁，引发超卖风险。

CREATE TABLE IF NOT EXISTS `order` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  `deleted_at` DATETIME(3) NULL DEFAULT NULL,
  `order_no` VARCHAR(64) NOT NULL,
  `buyer_id` BIGINT UNSIGNED NOT NULL,
  `goods_id` BIGINT UNSIGNED NOT NULL,
  `goods_no` VARCHAR(64) NOT NULL,
  `goods_name` VARCHAR(128) NOT NULL,
  `quantity` INT NOT NULL,
  `unit_price` BIGINT NOT NULL,
  `total_amount` BIGINT NOT NULL,
  `status` VARCHAR(32) NOT NULL,
  `expires_at` DATETIME(3) NOT NULL,
  `paid_at` DATETIME(3) NULL DEFAULT NULL,
  `closed_at` DATETIME(3) NULL DEFAULT NULL,
  `cancelled_at` DATETIME(3) NULL DEFAULT NULL,
  `refund_kind` VARCHAR(32) NOT NULL DEFAULT '',
  `refund_reason` VARCHAR(512) NOT NULL DEFAULT '',
  `refund_apply_at` DATETIME(3) NULL DEFAULT NULL,
  `refund_audit_at` DATETIME(3) NULL DEFAULT NULL,
  `refund_auditor_id` BIGINT UNSIGNED NOT NULL DEFAULT 0,
  `refund_audit_remark` VARCHAR(512) NOT NULL DEFAULT '',
  `refund_state` VARCHAR(32) NOT NULL DEFAULT '',
  `refund_retry_count` INT NOT NULL DEFAULT 0,
  `refund_channel_trade_no` VARCHAR(128) NULL DEFAULT NULL,
  `refunded_at` DATETIME(3) NULL DEFAULT NULL,
  `stock_restored` TINYINT(1) NOT NULL DEFAULT 0,
  `late_payment_refunded` TINYINT(1) NOT NULL DEFAULT 0,
  `shipment_carrier` VARCHAR(128) NOT NULL DEFAULT '',
  `shipment_tracking_no` VARCHAR(128) NOT NULL DEFAULT '',
  `shipped_at` DATETIME(3) NULL DEFAULT NULL,
  `shipment_registered_by` BIGINT UNSIGNED NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_order_order_no` (`order_no`),
  KEY `idx_order_refund_channel_trade_no` (`refund_channel_trade_no`),
  KEY `idx_order_buyer_status` (`buyer_id`, `status`),
  KEY `idx_order_goods_id` (`goods_id`),
  KEY `idx_order_status` (`status`),
  KEY `idx_order_status_expires` (`status`, `expires_at`),
  KEY `idx_order_deleted_at` (`deleted_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 并发风险点：订单状态变更必须按 order.id 主键命中聚簇索引并加 InnoDB 行锁；
-- 超时扫描依赖 idx_order_status_expires(status, expires_at)，否则全表扫描会扩大锁范围。
-- 终态已取消/已关闭/已退款/已发货不可回退；重复关闭不得多释放库存。

CREATE TABLE IF NOT EXISTS `payment` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `created_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  `deleted_at` DATETIME(3) NULL DEFAULT NULL,
  `order_id` BIGINT UNSIGNED NOT NULL DEFAULT 0,
  `order_no` VARCHAR(64) NOT NULL DEFAULT '',
  `channel_trade_no` VARCHAR(128) NOT NULL,
  `dedup_key` VARCHAR(191) NULL DEFAULT NULL,
  `effective` TINYINT(1) NULL DEFAULT NULL,
  `event_type` VARCHAR(64) NOT NULL,
  `result` VARCHAR(64) NOT NULL,
  `amount` BIGINT NOT NULL DEFAULT 0,
  `signature_valid` TINYINT(1) NOT NULL DEFAULT 1,
  `failure_code` VARCHAR(16) NULL DEFAULT NULL,
  `failure_reason` VARCHAR(512) NOT NULL DEFAULT '',
  `order_status_snapshot` VARCHAR(32) NOT NULL DEFAULT '',
  `need_refund` TINYINT(1) NOT NULL DEFAULT 0,
  `restored_stock` TINYINT(1) NOT NULL DEFAULT 0,
  `related_event_id` BIGINT UNSIGNED NOT NULL DEFAULT 0,
  `operator_id` BIGINT UNSIGNED NOT NULL DEFAULT 0,
  `occurred_at` DATETIME(3) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_payment_dedup_key` (`dedup_key`),
  UNIQUE KEY `uk_payment_channel_effective` (`channel_trade_no`, `effective`),
  KEY `idx_payment_order_id` (`order_id`),
  KEY `idx_payment_order_no` (`order_no`),
  KEY `idx_payment_event_type` (`event_type`),
  KEY `idx_payment_result` (`result`),
  KEY `idx_payment_related_event_id` (`related_event_id`),
  KEY `idx_payment_occurred_at` (`occurred_at`),
  KEY `idx_payment_deleted_at` (`deleted_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- payment 表在本轮 3 表范围内同时承载：有效收款/退款记录、支付通知处理结果、
-- 异常支付待处理记录、迟到支付退款流水和只追加审计事件。
-- effective = 1 的记录参与 uk_payment_channel_effective 渠道交易号唯一约束；
-- effective IS NULL 的记录用于重复通知/拒绝/审计留痕，MySQL 唯一索引允许多个 NULL，因此可只追加。
-- 本表不提供 UPDATE / DELETE 业务入口，异常记录不能通过直接改写订单状态消失。

-- 固定演示数据：活动商品单价 10000 分，初始可售 5 件；重复执行不覆盖已有库存。
INSERT INTO `goods`
  (`goods_no`, `name`, `unit_price`, `available_stock`, `occupied_stock`, `status`, `created_at`, `updated_at`)
VALUES
  ('GOODS-ACT-001', '活动商品', 10000, 5, 0, '在售', NOW(3), NOW(3)),
  ('GOODS-DEMO-002', '演示商品', 10000, 2, 0, '在售', NOW(3), NOW(3))
ON DUPLICATE KEY UPDATE `goods_no` = VALUES(`goods_no`);
