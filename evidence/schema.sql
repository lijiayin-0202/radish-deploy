-- =====================================================================
-- shop-trade 题目 01《小型电商的订单交易、发货与售前退款》
-- 文件：evidence/schema.sql
-- 用途：真实 MySQL(InnoDB) 环境的建库建表脚本，供 evidence/mysql核查记录.md
--       的核查步骤直接执行；与仓库根目录 schema.sql 的建表口径保持一致，
--       并补充了「建库」与「字段/表注释」两部分，使脚本可在空实例上一条执行完成。
--
-- 适配说明：
--   1. 技术栈要求为 Go + Gorm + MySQL(InnoDB)，故全部业务表固定
--      ENGINE=InnoDB、DEFAULT CHARSET=utf8mb4、COLLATE=utf8mb4_0900_ai_ci。
--   2. 金额字段一律 BIGINT，单位为「分」，不使用任何浮点类型。
--   3. 订单表物理名为 `order`，是 MySQL 保留字，全部语句使用反引号转义；
--      GORM 的 Order.TableName() 同样返回 "order"，两端一致。
--   4. 「订单唯一标识」在本项目中由订单号 `order`.`order_no` 承担：
--      物理主键为自增 `id`，业务唯一约束为 UNIQUE KEY uk_order_order_no(order_no)；
--      支付表通过 `payment`.`order_id` 关联订单主键，并建普通索引 idx_payment_order_id。
--   5. 并发安全依赖 InnoDB 行锁：库存扣减/释放、订单状态变更都必须命中
--      `goods`.`id` / `order`.`id` 主键（聚簇索引），条件更新未命中行时
--      RowsAffected != 1，服务层据此拒绝并发下的第二笔业务结果。
--   6. 幂等与唯一性：
--      - uk_payment_channel_effective(channel_trade_no, effective) 保证
--        同一渠道交易号不会被两个有效业务结果占用；
--      - uk_payment_dedup_key(dedup_key) 保证同一幂等键只记一次款；
--      - payment.effective 允许为 NULL，唯一索引对多个 NULL 不生效，
--        因此「重复通知 / 拒绝 / 只追加审计事件」可以无限追加而不冲突。
--   7. 终态保护：订单状态字段 status 取值为 待支付/待发货/退款审核中/退款处理中/
--      已发货/已退款/已关闭/已取消；已取消、已关闭、已退款、已发货为终态，
--      服务层以「条件更新 + RowsAffected 判定」保证终态不可回退。
--   8. 本脚本不包含任何 DROP TABLE / TRUNCATE，可重复执行（幂等）；
--      演示数据使用 ON DUPLICATE KEY UPDATE，重复执行不覆盖既有库存。
--
-- 目标环境：MySQL 8.0+ / 8.4 LTS，InnoDB，utf8mb4
-- 执行方式：mysql -uroot < evidence/schema.sql
-- =====================================================================

-- ---------------------------------------------------------------------
-- 建库：业务库 shop_trade，字符集 utf8mb4
-- ---------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS `shop_trade`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;

USE `shop_trade`;

-- ---------------------------------------------------------------------
-- 商品库存表：可售 available_stock 与预扣占用 occupied_stock 分离守恒
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `goods` (
  `id`              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT          COMMENT '商品ID',
  `created_at`      DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  `updated_at`      DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
  `deleted_at`      DATETIME(3)     NULL DEFAULT NULL                 COMMENT '软删除时间',
  `goods_no`        VARCHAR(64)     NOT NULL                           COMMENT '商品编号（业务唯一键）',
  `name`            VARCHAR(128)    NOT NULL                           COMMENT '商品名称',
  `unit_price`      BIGINT          NOT NULL                           COMMENT '单价，单位分；下单时快照到订单',
  `available_stock` INT             NOT NULL DEFAULT 0                 COMMENT '可售数量',
  `occupied_stock`  INT             NOT NULL DEFAULT 0                 COMMENT '预扣占用数量（待支付订单占用）',
  `status`          VARCHAR(32)     NOT NULL                           COMMENT '商品状态：在售/下架',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_goods_goods_no` (`goods_no`),
  KEY `idx_goods_status` (`status`),
  KEY `idx_goods_available_stock` (`available_stock`),
  KEY `idx_goods_deleted_at` (`deleted_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='商品与库存表：可售/占用分离，下单扣减可售并增加占用，超时关单与退款恢复库存';

-- ---------------------------------------------------------------------
-- 订单表：一单仅一种商品；保存下单时的商品与价格快照
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `order` (
  `id`                       BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '订单主键',
  `created_at`               DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  `updated_at`               DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
  `deleted_at`               DATETIME(3)     NULL DEFAULT NULL    COMMENT '软删除时间',
  `order_no`                 VARCHAR(64)     NOT NULL            COMMENT '订单号（业务唯一键）',
  `buyer_id`                 BIGINT UNSIGNED NOT NULL            COMMENT '买家ID',
  `goods_id`                 BIGINT UNSIGNED NOT NULL            COMMENT '单一商品ID',
  `goods_no`                 VARCHAR(64)     NOT NULL            COMMENT '下单时商品编号快照',
  `goods_name`               VARCHAR(128)    NOT NULL            COMMENT '下单时商品名称快照',
  `quantity`                 INT             NOT NULL            COMMENT '数量，仅允许 1 或 2',
  `unit_price`               BIGINT          NOT NULL            COMMENT '下单时单价快照，单位分',
  `total_amount`             BIGINT          NOT NULL            COMMENT '应付金额快照，单位分',
  `status`                   VARCHAR(32)     NOT NULL            COMMENT '订单状态：待支付/待发货/退款审核中/退款处理中/已发货/已退款/已关闭/已取消',
  `expires_at`               DATETIME(3)     NOT NULL            COMMENT '服务端判定的支付到期时间（下单后10分钟）',
  `paid_at`                  DATETIME(3)     NULL DEFAULT NULL    COMMENT '支付成功时间',
  `closed_at`                DATETIME(3)     NULL DEFAULT NULL    COMMENT '超时关闭时间',
  `cancelled_at`             DATETIME(3)     NULL DEFAULT NULL    COMMENT '主动取消时间',
  `refund_kind`              VARCHAR(32)     NOT NULL DEFAULT '' COMMENT '退款类型：正常售前/迟到支付',
  `refund_reason`            VARCHAR(512)    NOT NULL DEFAULT '' COMMENT '退款申请原因',
  `refund_apply_at`          DATETIME(3)     NULL DEFAULT NULL    COMMENT '退款申请时间',
  `refund_audit_at`          DATETIME(3)     NULL DEFAULT NULL    COMMENT '退款审核时间',
  `refund_auditor_id`        BIGINT UNSIGNED NOT NULL DEFAULT 0  COMMENT '审核客服ID',
  `refund_audit_remark`      VARCHAR(512)    NOT NULL DEFAULT '' COMMENT '审核/核实原因',
  `refund_state`             VARCHAR(32)     NOT NULL DEFAULT '' COMMENT '退款处理子状态',
  `refund_retry_count`       INT             NOT NULL DEFAULT 0  COMMENT '渠道退款失败后的重试次数',
  `refund_channel_trade_no`  VARCHAR(128)    NULL DEFAULT NULL    COMMENT '退款渠道交易号',
  `refunded_at`              DATETIME(3)     NULL DEFAULT NULL    COMMENT '退款成功时间',
  `stock_restored`           TINYINT(1)      NOT NULL DEFAULT 0  COMMENT '正常售前退款是否已恢复库存（保证只恢复一次）',
  `late_payment_refunded`    TINYINT(1)      NOT NULL DEFAULT 0  COMMENT '迟到支付退款是否完成',
  `shipment_carrier`         VARCHAR(128)    NOT NULL DEFAULT '' COMMENT '承运方',
  `shipment_tracking_no`     VARCHAR(128)    NOT NULL DEFAULT '' COMMENT '运单号',
  `shipped_at`               DATETIME(3)     NULL DEFAULT NULL    COMMENT '发货登记时间',
  `shipment_registered_by`   BIGINT UNSIGNED NOT NULL DEFAULT 0  COMMENT '仓库登记人ID',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_order_order_no` (`order_no`),
  KEY `idx_order_refund_channel_trade_no` (`refund_channel_trade_no`),
  KEY `idx_order_buyer_status` (`buyer_id`, `status`),
  KEY `idx_order_goods_id` (`goods_id`),
  KEY `idx_order_status` (`status`),
  KEY `idx_order_status_expires` (`status`, `expires_at`),
  KEY `idx_order_deleted_at` (`deleted_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='订单表：一单一种商品，保存下单时价格快照；终态不可回退，超时关单释放占用';

-- ---------------------------------------------------------------------
-- 支付/退款/审计事件表：只追加，无业务 UPDATE / DELETE 入口
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `payment` (
  `id`                    BIGINT UNSIGNED NOT NULL AUTO_INCREMENT  COMMENT '事件ID',
  `created_at`            DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  `updated_at`            DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
  `deleted_at`            DATETIME(3)     NULL DEFAULT NULL     COMMENT '软删除时间',
  `order_id`              BIGINT UNSIGNED NOT NULL DEFAULT 0      COMMENT '关联订单主键 order.id',
  `order_no`              VARCHAR(64)     NOT NULL DEFAULT ''    COMMENT '关联订单号快照',
  `channel_trade_no`      VARCHAR(128)    NOT NULL               COMMENT '渠道交易号（模拟支付渠道）',
  `dedup_key`             VARCHAR(191)    NULL DEFAULT NULL     COMMENT '幂等键：同一笔有效业务结果只允许一条',
  `effective`             TINYINT(1)      NULL DEFAULT NULL     COMMENT '是否有效业务结果：1=有效；NULL=审计/拒绝/重复留痕（可多条）',
  `event_type`            VARCHAR(64)     NOT NULL               COMMENT '事件类型：支付通知/退款回调/异常支付/审计',
  `result`                VARCHAR(64)     NOT NULL               COMMENT '处理结果',
  `amount`                BIGINT          NOT NULL DEFAULT 0     COMMENT '金额，单位分',
  `signature_valid`       TINYINT(1)      NOT NULL DEFAULT 1     COMMENT '验签是否通过',
  `failure_code`          VARCHAR(16)     NULL DEFAULT NULL     COMMENT 'M-xx 失败原因编号',
  `failure_reason`        VARCHAR(512)    NOT NULL DEFAULT ''    COMMENT '中文失败/拒绝原因',
  `order_status_snapshot` VARCHAR(32)     NOT NULL DEFAULT ''    COMMENT '事件发生时订单状态快照',
  `need_refund`           TINYINT(1)      NOT NULL DEFAULT 0     COMMENT '是否需要客服发起退款（迟到支付）',
  `restored_stock`        TINYINT(1)      NOT NULL DEFAULT 0     COMMENT '本事件是否恢复库存',
  `related_event_id`      BIGINT UNSIGNED NOT NULL DEFAULT 0     COMMENT '关联异常事件ID',
  `operator_id`           BIGINT UNSIGNED NOT NULL DEFAULT 0     COMMENT '操作人ID',
  `occurred_at`           DATETIME(3)     NOT NULL               COMMENT '事件发生时间',
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='支付/退款/异常支付与只追加审计流水表；unique 仅约束有效业务结果，审计事件可重复追加';

-- ---------------------------------------------------------------------
-- 固定演示数据：活动商品单价 10000 分、初始可售 5 件（题面既定）
-- 重复执行不覆盖既有库存（ON DUPLICATE KEY UPDATE 只回写 goods_no）
-- ---------------------------------------------------------------------
INSERT INTO `goods`
  (`goods_no`, `name`, `unit_price`, `available_stock`, `occupied_stock`, `status`, `created_at`, `updated_at`)
VALUES
  ('GOODS-ACT-001', '活动商品', 10000, 5, 0, '在售', NOW(3), NOW(3)),
  ('GOODS-DEMO-002', '演示商品', 10000, 2, 0, '在售', NOW(3), NOW(3))
ON DUPLICATE KEY UPDATE `goods_no` = VALUES(`goods_no`);
