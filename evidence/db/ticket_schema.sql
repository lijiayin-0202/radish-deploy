-- =====================================================================
-- shop-trade 题目 01 · 数据库层验证辅助表：ticket（工单表）
-- 文件：evidence/db/ticket_schema.sql
-- 用途：为 docs/db/ticket_table_verify.md 提供可执行建表脚本，
--       校验 uk_ticket_ticket_no 唯一索引约束与 InnoDB 数据持久化落盘。
--
-- 口径说明（重要）：
--   1. 本表属于「数据库层验证辅助表」，仅承载唯一索引与持久化验证，
--      未被任何业务代码（model/service/api）引用，不参与题目 01 的业务运行。
--   2. 题目 01 的业务表为 goods / order / payment（见 evidence/schema.sql）；
--      是否把 ticket / faq / notice 纳入业务表需另行确认（AGENTS.md C-02）。
--   3. 引擎、字符集与列类型与既有业务表保持一致：
--      ENGINE=InnoDB、DEFAULT CHARSET=utf8mb4、COLLATE=utf8mb4_0900_ai_ci。
--   4. 本脚本不含 DROP TABLE / TRUNCATE，可重复执行（幂等）。
--
-- 目标环境：MySQL 8.0+ / 8.4 LTS，InnoDB，utf8mb4
-- 执行方式：mysql -uroot shop_trade < evidence/db/ticket_schema.sql
-- =====================================================================

USE `shop_trade`;

CREATE TABLE IF NOT EXISTS `ticket` (
  `id`         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT              COMMENT '工单ID',
  `created_at` DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) COMMENT '创建时间',
  `updated_at` DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3) COMMENT '更新时间',
  `deleted_at` DATETIME(3)     NULL DEFAULT NULL                     COMMENT '软删除时间',
  `ticket_no`  VARCHAR(64)     NOT NULL                               COMMENT '工单号（业务唯一键）',
  `user_id`    BIGINT UNSIGNED NOT NULL                               COMMENT '工单所属用户ID',
  `content`    VARCHAR(1024)   NOT NULL                               COMMENT '工单内容',
  `status`     VARCHAR(32)     NOT NULL DEFAULT 'pending'             COMMENT '工单状态：pending/processing/closed',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_ticket_ticket_no` (`ticket_no`),
  KEY `idx_ticket_user_id` (`user_id`),
  KEY `idx_ticket_status` (`status`),
  KEY `idx_ticket_created_at` (`created_at`),
  KEY `idx_ticket_deleted_at` (`deleted_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='工单表：工单号唯一；状态 pending/processing/closed';