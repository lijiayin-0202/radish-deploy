# 工单表 ticket_no 唯一索引 & 数据持久化验证
验证目标：校验 `ticket_no` 唯一索引约束、验证 InnoDB 数据持久化落盘

1. **首次插入工单（插入成功）**
```sql
INSERT INTO `ticket`(ticket_no, user_id, content, status, created_at)
VALUES ('TK001', 1, '订单 ORD001 未收到货，请协助核查', 'pending', NOW(3));
```
```sql
SELECT id, ticket_no, user_id, content, status, created_at
FROM `ticket` WHERE ticket_no = 'TK001';
```
执行结果（真实输出，`exit=0`）：
```
id	ticket_no	user_id	content	status	created_at
1	TK001	1	订单 ORD001 未收到货，请协助核查	pending	2026-11-12 20:15:24.672
```

2. **重复插入相同 ticket_no（唯一索引拦截）**
```sql
INSERT INTO `ticket`(ticket_no, user_id, content, status, created_at)
VALUES ('TK001', 1, '订单 ORD001 未收到货，请协助核查', 'pending', NOW(3));
```
执行结果（真实输出，`exit=1`，写入被数据库拦截）：
```
ERROR 1062 (23000) at line 1: Duplicate entry 'TK001' for key 'ticket.uk_ticket_ticket_no'
```

3. **唯一索引定义核对**
```sql
SHOW INDEX FROM `ticket` WHERE Key_name = 'uk_ticket_ticket_no';
```
执行结果（真实输出，`exit=0`）：
```
Table	Non_unique	Key_name	Seq_in_index	Column_name	Collation	Cardinality	Sub_part	Packed	Null	Index_type	Comment	Index_comment	Visible	Expression
ticket	0	uk_ticket_ticket_no	1	ticket_no	A	1	NULL	NULL		BTREE			YES	NULL
```
`Non_unique=0` 且 `Key_name=uk_ticket_ticket_no`，确认该列为 UNIQUE 索引；同一约束在 `information_schema.TABLE_CONSTRAINTS` 中登记为 `uk_ticket_ticket_no / ticket / UNIQUE`。

4. **事务回滚原子性验证**
```sql
START TRANSACTION;
INSERT INTO `ticket`(ticket_no, user_id, content, status, created_at)
VALUES ('TK001-TX', 1, '事务回滚验证工单', 'processing', NOW(3));
SELECT COUNT(*) AS rows_in_transaction FROM `ticket` WHERE ticket_no = 'TK001-TX';
ROLLBACK;
SELECT COUNT(*) AS rows_after_rollback FROM `ticket` WHERE ticket_no = 'TK001-TX';
```
执行结果（真实输出，`exit=0`）：事务内可见 1 行，`ROLLBACK` 后为 0 行，验证 InnoDB 事务的原子性。
```
rows_in_transaction
1
rows_after_rollback
0
```

5. **数据库重启后持久化校验**
```sql
-- 重启
service mysql restart
mysqladmin -uroot ping
-- 重启后查询重启前写入的工单
SELECT id, ticket_no, user_id, content, status, created_at
FROM `ticket` WHERE ticket_no = 'TK001';
-- 重启后索引仍应存在
SHOW INDEX FROM `ticket` WHERE Key_name = 'uk_ticket_ticket_no';
```
执行结果（真实输出）：`mysqld is alive`，工单行在重启后仍可查询，字段值与重启前完全一致，唯一索引同步保留。
```
$ mysqladmin ping -> mysqld is alive
id	ticket_no	user_id	content	status	created_at
1	TK001	1	订单 ORD001 未收到货，请协助核查	pending	2026-11-12 20:15:24.672
```
```
Table	Non_unique	Key_name	Seq_in_index	Column_name	Collation	Cardinality	Sub_part	Packed	Null	Index_type	Comment	Index_comment	Visible	Expression
ticket	0	uk_ticket_ticket_no	1	ticket_no	A	1	NULL	NULL		BTREE			YES	NULL
```

6. **清理验证数据**
```sql
DELETE FROM `ticket` WHERE ticket_no IN ('TK001', 'TK001-TX');
SELECT COUNT(*) AS rows_after_cleanup FROM `ticket` WHERE ticket_no IN ('TK001', 'TK001-TX');
```
执行结果（真实输出，`exit=0`）：`rows_after_cleanup = 0`，验证数据已清理，不污染演示库。

7. **验证结论**

| 验证项 | 结论 | 依据 |
| --- | --- | --- |
| `ticket_no` 唯一索引约束 | 通过 | 重复插入触发 `ERROR 1062 ... for key 'ticket.uk_ticket_ticket_no'`；`SHOW INDEX` 显示 `Non_unique=0` |
| 工单行首次写入 | 通过 | 步骤 1 `exit=0` 且回查字段值一致 |
| InnoDB 事务原子性 | 通过 | 步骤 4 事务内 1 行、回滚后 0 行 |
| 数据持久化落盘 | 通过 | 步骤 5 数据库重启后同一工单仍可查询，值一致，且唯一索引仍存在 |
| 验证数据清理 | 通过 | 步骤 6 `rows_after_cleanup = 0` |

**环境**：`MySQL 8.4.11-0ubuntu0.26.04.1`，默认引擎 `InnoDB`，服务端字符集 `utf8mb4`；业务库 `shop_trade`。
**表结构**：见 `evidence/db/ticket_schema.sql`（`ticket` 表，`ENGINE=InnoDB`、`CHARSET=utf8mb4`、`COLLATE=utf8mb4_0900_ai_ci`；字段 `ticket_no`/`user_id`/`content`/`status`/`created_at`，`status` 取值 `pending`/`processing`/`closed`）。
**复现方式**：`python -X utf8 evidence/db/ticket_table_verify.py`（真实执行，原始输出 `evidence/db/ticket_table_verify_raw.txt`）。
**口径说明**：本表为「数据库层验证辅助表」，仅用于唯一索引与持久化验证，未被任何业务代码引用；题目 01 的业务表仍为 `goods` / `order` / `payment`（见 `evidence/schema.sql`），是否纳入业务表需另行确认。

<!-- 后续 faq 表、公告（notice）表的验证文档继续复用本文件格式：一级标题「<表名> <唯一键> 唯一索引 & 数据持久化验证」→ 验证目标 → ①首次插入（插入成功）②重复插入相同<唯一键>（唯一索引拦截，报 1062）③唯一索引定义核对 SHOW INDEX ④事务回滚原子性验证 ⑤数据库重启后持久化校验 ⑥清理验证数据 SQL ⑦验证结论表格；每步均给出可执行 SQL 与真实执行输出，表结构脚本按 evidence/db/<表名>_schema.sql 单独存放。 -->