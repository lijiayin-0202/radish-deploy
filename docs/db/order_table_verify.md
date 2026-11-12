# 订单表 order_no 唯一索引 & 数据持久化验证
验证目标：校验 `order_no` 唯一索引约束、验证 InnoDB 数据持久化落盘

1. **首次插入订单（插入成功）**
```sql
INSERT INTO `order`(order_no, buyer_id, goods_id, goods_no, goods_name, quantity, unit_price, total_amount, status, expires_at)
VALUES ('ORD001', 1, 1, 'G001', '测试商品', 1, 9900, 9900, 'pending', '2026-12-31 23:59:59');
```
```sql
SELECT id, order_no, buyer_id, goods_id, goods_no, goods_name, quantity, unit_price, total_amount, status, expires_at
FROM `order` WHERE order_no = 'ORD001';
```
执行结果（真实输出，`exit=0`）：
```
id	order_no	buyer_id	goods_id	goods_no	goods_name	quantity	unit_price	total_amount	status	expires_at
19	ORD001	1	1	G001	测试商品	1	9900	9900	pending	2026-12-31 23:59:59.000
```

2. **重复插入相同 order_no（唯一索引拦截）**
```sql
INSERT INTO `order`(order_no, buyer_id, goods_id, goods_no, goods_name, quantity, unit_price, total_amount, status, expires_at)
VALUES ('ORD001', 1, 1, 'G001', '测试商品', 1, 9900, 9900, 'pending', '2026-12-31 23:59:59');
```
执行结果（真实输出，`exit=1`，写入被数据库拦截）：
```
ERROR 1062 (23000) at line 1: Duplicate entry 'ORD001' for key 'order.uk_order_order_no'
```

3. **唯一索引定义核对**
```sql
SHOW INDEX FROM `order` WHERE Key_name = 'uk_order_order_no';
```
执行结果（真实输出，`exit=0`）：
```
Table	Non_unique	Key_name	Seq_in_index	Column_name	Collation	Cardinality	Sub_part	Packed	Null	Index_type	Comment	Index_comment	Visible	Expression
order	0	uk_order_order_no	1	order_no	A	0	NULL	NULL		BTREE			YES	NULL
```
`Non_unique=0` 且 `Key_name=uk_order_order_no`，确认该列为 UNIQUE 索引；同一约束在 `information_schema.TABLE_CONSTRAINTS` 中登记为 `uk_order_order_no / order / UNIQUE`。

4. **事务回滚后不落盘（InnoDB 事务性）**
```sql
START TRANSACTION;
INSERT INTO `order`(order_no, buyer_id, goods_id, goods_no, goods_name, quantity, unit_price, total_amount, status, expires_at)
VALUES ('ORD001-TX', 1, 1, 'G001', '测试商品', 1, 9900, 9900, 'pending', '2026-12-31 23:59:59');
SELECT COUNT(*) AS rows_in_transaction FROM `order` WHERE order_no = 'ORD001-TX';
ROLLBACK;
SELECT COUNT(*) AS rows_after_rollback FROM `order` WHERE order_no = 'ORD001-TX';
```
执行结果（真实输出，`exit=0`）：事务内可见 1 行，`ROLLBACK` 后为 0 行，验证 InnoDB 事务的原子性。
```
rows_in_transaction
1
rows_after_rollback
0
```

5. **数据库重启后数据持久化校验**
```sql
-- 重启
service mysql restart
mysqladmin -uroot ping
-- 重启后查询重启前写入的订单
SELECT id, order_no, buyer_id, goods_no, quantity, unit_price, total_amount, status, expires_at, created_at
FROM `order` WHERE order_no = 'ORD001';
```
执行结果（真实输出）：`mysqld is alive`，订单行在重启后仍可查询，字段值与重启前完全一致。
```
$ mysqladmin ping -> mysqld is alive
id	order_no	buyer_id	goods_no	quantity	unit_price	total_amount	status	expires_at	created_at
19	ORD001	1	G001	1	9900	9900	pending	2026-12-31 23:59:59.000	2026-11-12 19:58:16.470
```

6. **清理验证数据**
```sql
DELETE FROM `order` WHERE order_no IN ('ORD001', 'ORD001-TX');
SELECT COUNT(*) AS rows_after_cleanup FROM `order` WHERE order_no IN ('ORD001', 'ORD001-TX');
```
执行结果（真实输出，`exit=0`）：`rows_after_cleanup = 0`，验证数据已清理，不污染演示库。

7. **验证结论**

| 验证项 | 结论 | 依据 |
| --- | --- | --- |
| `order_no` 唯一索引约束 | 通过 | 重复插入触发 `ERROR 1062 ... for key 'order.uk_order_order_no'`；`SHOW INDEX` 显示 `Non_unique=0` |
| 订单行首次写入 | 通过 | 步骤 1 `exit=0` 且回查字段值一致 |
| InnoDB 事务原子性 | 通过 | 步骤 4 事务内 1 行、回滚后 0 行 |
| 数据持久化落盘 | 通过 | 步骤 5 数据库重启后同一订单仍可查询，值一致 |
| 验证数据清理 | 通过 | 步骤 6 `rows_after_cleanup = 0` |

**环境**：`MySQL 8.4.11-0ubuntu0.26.04.1`，默认引擎 `InnoDB`，服务端字符集 `utf8mb4`；业务库 `shop_trade`。
**复现方式**：`python -X utf8 evidence/db/order_table_verify.py`（真实执行，原始输出 `evidence/db/order_table_verify_raw.txt`）。
**说明**：`status` 列在库中为 `VARCHAR(32)`，本文沿用模板示例值 `pending`；业务状态取值（待支付/待发货/退款审核中/退款处理中/已发货/已退款/已关闭/已取消）见 `evidence/schema.sql` 的字段注释。

<!-- 后续 ticket / faq / notice 表验证文档沿用本文件的统一格式：一级标题「<表名> <唯一键> 唯一索引 & 数据持久化验证」→ 验证目标 → 编号步骤（首次插入 / 重复插入触发唯一约束 / 唯一索引定义核对 / 事务回滚 / 重启后持久化 / 清理 / 验证结论表格），每步均给出可执行 SQL 与真实输出。 -->
